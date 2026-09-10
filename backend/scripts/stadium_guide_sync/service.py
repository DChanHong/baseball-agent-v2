from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from openai import OpenAIError

from .classifier import classify_change
from .collector import CollectionError, collector_for
from .llm import CandidateGenerator
from .parser import ParseError, parse_collected_source
from .raw_storage import save_raw_snapshot, sha256_text
from .repository import StadiumGuideSyncRepository
from .schemas import ChangeOperation, ParsedSource, SourceDefinition

COUNT_KEYS = (
    "create",
    "update",
    "unchanged",
    "delete_candidate",
    "manual_required",
    "failure",
)


@dataclass(slots=True)
class SyncResult:
    run_id: str
    source_count: int
    counts: dict[str, int] = field(
        default_factory=lambda: {key: 0 for key in COUNT_KEYS}
    )
    candidate_ids: list[str] = field(default_factory=list)


def build_embedding_text(payload: dict[str, object]) -> str:
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    keywords = metadata.get("search_keywords", [])
    lines = [
        f"제목: {payload['title']}",
        f"문서유형: {payload['document_type']}",
        f"구장: {payload['stadium_id']}",
        f"팀: {payload.get('team_id') or '공통'}",
    ]
    if metadata.get("topic_summary"):
        lines.append(f"핵심주제: {metadata['topic_summary']}")
    if keywords:
        lines.append(f"검색키워드: {', '.join(str(value) for value in keywords)}")
    return "\n".join(lines + ["본문:", str(payload["content"])])


def source_fingerprint(parsed_sources: list[ParsedSource]) -> str:
    items = sorted(
        (item.collected.source.source_id, item.text_hash) for item in parsed_sources
    )
    return sha256_text(
        json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    )


class StadiumGuideSyncService:
    def __init__(
        self,
        *,
        repository: StadiumGuideSyncRepository,
        generator: CandidateGenerator,
        raw_root: Path,
        repository_root: Path,
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._raw_root = raw_root
        self._repository_root = repository_root

    async def run(
        self,
        *,
        sources: list[SourceDefinition],
        scope: dict[str, object],
        requested_document_type: str | None = None,
    ) -> SyncResult:
        run_id = f"SGR_{datetime.now(UTC):%Y%m%dT%H%M%S}_{uuid4().hex[:8]}"
        result = SyncResult(run_id=run_id, source_count=len(sources))
        await self._repository.start_run(run_id, scope, len(sources))
        parsed_sources: list[ParsedSource] = []

        for source in sources:
            latest = await self._repository.latest_source_check(source.source_id)
            try:
                collected = await collector_for(source).collect(source)
                parsed_text = parse_collected_source(collected)
                parsed = ParsedSource(
                    collected=collected,
                    text=parsed_text,
                    raw_hash=sha256_text(collected.body),
                    text_hash=sha256_text(parsed_text),
                )
                is_unchanged = bool(
                    latest and latest["normalized_text_hash"] == parsed.text_hash
                )
                if is_unchanged and latest["raw_file_path"]:
                    parsed = ParsedSource(
                        collected=parsed.collected,
                        text=parsed.text,
                        raw_hash=parsed.raw_hash,
                        text_hash=parsed.text_hash,
                        raw_file_path=self._repository_root / latest["raw_file_path"],
                    )
                else:
                    parsed = save_raw_snapshot(self._raw_root, parsed)
                parsed_sources.append(parsed)
                raw_path = parsed.raw_file_path
                if raw_path:
                    try:
                        raw_path = raw_path.relative_to(self._repository_root)
                    except ValueError:
                        pass
                await self._repository.record_source_check(
                    run_id=run_id,
                    source_id=source.source_id,
                    source_url=source.url,
                    result_status="unchanged" if is_unchanged else "collected",
                    collector_type=str(collected.collector_type),
                    parser_name=source.parser_name,
                    raw_content_hash=parsed.raw_hash,
                    normalized_text_hash=parsed.text_hash,
                    raw_file_path=raw_path,
                    http_status=collected.status_code,
                )
            except ParseError as exc:
                missing_count = (
                    int(latest["consecutive_missing_count"]) + 1 if latest else 1
                )
                await self._repository.record_source_check(
                    run_id=run_id,
                    source_id=source.source_id,
                    source_url=source.url,
                    result_status="content_missing",
                    collector_type=str(source.collector_type),
                    parser_name=source.parser_name,
                    consecutive_missing_count=missing_count,
                    error_code=exc.code,
                )
                delete_created = False
                if missing_count >= 2:
                    stadium_id = (
                        source.stadium_ids[0] if source.stadium_ids else None
                    )
                    for document_type in source.document_types:
                        if (
                            requested_document_type
                            and document_type != requested_document_type
                        ):
                            continue
                        logical_id = (
                            f"{stadium_id or 'KBO_common'}_{document_type}"
                        )
                        active = await self._repository.active_document(logical_id)
                        if not active:
                            continue
                        candidate_id = (
                            f"SGC_{datetime.now(UTC):%Y%m%dT%H%M%S}_"
                            f"{uuid4().hex[:10]}"
                        )
                        created = await self._repository.create_candidate(
                            candidate_id=candidate_id,
                            run_id=run_id,
                            logical_document_id=logical_id,
                            operation=ChangeOperation.DELETE_CANDIDATE,
                            previous=active,
                            candidate_revision_id=None,
                            candidate_content_hash=None,
                            candidate_payload={},
                            diff_summary={
                                "reason": "official source content missing twice",
                                "source_id": source.source_id,
                                "consecutive_missing_count": missing_count,
                            },
                            source_ids=[source.source_id],
                        )
                        if created:
                            result.candidate_ids.append(candidate_id)
                            result.counts["delete_candidate"] += 1
                            delete_created = True
                if not delete_created:
                    result.counts["manual_required"] += 1
            except CollectionError as exc:
                is_manual = exc.code == "BROWSER_ADAPTER_UNAVAILABLE"
                await self._repository.record_source_check(
                    run_id=run_id,
                    source_id=source.source_id,
                    source_url=source.url,
                    result_status="manual_required" if is_manual else "collection_failed",
                    collector_type=str(source.collector_type),
                    parser_name=source.parser_name,
                    http_status=exc.status_code,
                    error_code=exc.code,
                )
                result.counts["manual_required" if is_manual else "failure"] += 1

        groups: dict[tuple[str | None, str | None, str], list[ParsedSource]] = {}
        for parsed in parsed_sources:
            source = parsed.collected.source
            stadium_id = source.stadium_ids[0] if source.stadium_ids else None
            team_id = source.team_ids[0] if source.team_ids else None
            for document_type in source.document_types:
                if requested_document_type and document_type != requested_document_type:
                    continue
                groups.setdefault((stadium_id, team_id, document_type), []).append(parsed)

        for (stadium_id, team_id, document_type), group in groups.items():
            logical_id = f"{stadium_id or 'KBO_common'}_{document_type}"
            fingerprint = source_fingerprint(group)
            existing = await self._repository.find_open_candidate(
                logical_id, fingerprint
            )
            if existing:
                result.candidate_ids.append(str(existing["candidate_id"]))
                result.counts[str(existing["operation"]).lower()] += 1
                continue
            active = await self._repository.active_document(logical_id)
            try:
                draft = await self._generator.generate(
                    logical_document_id=logical_id,
                    document_type=document_type,
                    stadium_id=stadium_id,
                    team_id=team_id,
                    sources=[
                        (item.collected.source, item.text) for item in group
                    ],
                    active=active,
                )
            except (OpenAIError, RuntimeError, ValueError):
                result.counts["manual_required"] += 1
                continue

            revision_number = active.revision_number + 1 if active else 1
            revision_id = f"{logical_id}_r{revision_number:04d}"
            payload: dict[str, object] = {
                "schema_version": "2.0.0",
                "logical_document_id": logical_id,
                "revision_id": revision_id,
                "revision_number": revision_number,
                "document_type": document_type,
                "stadium_id": stadium_id,
                "team_id": team_id,
                "title": draft.title,
                "as_of": draft.as_of.isoformat(),
                "trust_level": "official",
                "review_status": "needs_review",
                "sources": [
                    item.collected.source.source_id for item in group
                ],
                "content": draft.content,
                "metadata": {
                    "topic_summary": draft.topic_summary,
                    "search_keywords": draft.search_keywords,
                    "limitations": draft.limitations,
                    "embedding_model": "text-embedding-3-small",
                },
            }
            content_hash = sha256_text(build_embedding_text(payload))
            payload["content_hash"] = content_hash
            operation = classify_change(active, content_hash)
            if operation == ChangeOperation.UNCHANGED:
                result.counts["unchanged"] += 1
                continue

            candidate_key = sha256_text(f"{logical_id}:{content_hash}")[:10]
            candidate_id = (
                f"SGC_{datetime.now(UTC):%Y%m%dT%H%M%S}_{candidate_key}"
            )
            created = await self._repository.create_candidate(
                candidate_id=candidate_id,
                run_id=run_id,
                logical_document_id=logical_id,
                operation=operation,
                previous=active,
                candidate_revision_id=revision_id,
                candidate_content_hash=content_hash,
                candidate_payload=payload,
                diff_summary={
                    "source_fingerprint": fingerprint,
                    "source_text_hashes": {
                        item.collected.source.source_id: item.text_hash
                        for item in group
                    },
                    "previous_title": active.title if active else None,
                    "candidate_title": draft.title,
                },
                source_ids=[
                    item.collected.source.source_id for item in group
                ],
            )
            if created:
                result.candidate_ids.append(candidate_id)
            result.counts[operation.value.lower()] += 1

        await self._repository.finish_run(run_id, result.counts)
        return result
