from __future__ import annotations

import re
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import cast

from .parser import ParseError, parse_collected_source
from .repository import StadiumGuideSyncRepository
from .schemas import CandidateRecord, CollectedSource, SourceRegistry


def content_diff(previous: str, candidate: str) -> str:
    def sentences(value: str) -> list[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?。])\s+|\n+", value)
            if sentence.strip()
        ]

    lines = unified_diff(
        sentences(previous),
        sentences(candidate),
        fromfile="previous",
        tofile="candidate",
        lineterm="",
    )
    return "\n".join(lines) or "(content unchanged)"


async def candidate_detail(
    *,
    repository: StadiumGuideSyncRepository,
    registry: SourceRegistry,
    repository_root: Path,
    candidate_id: str,
) -> dict[str, object]:
    candidate = await repository.candidate(candidate_id)
    if not candidate:
        raise ValueError(f"candidate not found: {candidate_id}")
    payload = candidate.candidate_payload
    candidate_content = str(payload.get("content") or "")
    source_index = {source.source_id: source for source in registry.sources}
    checks = {
        str(check["source_id"]): check
        for check in await repository.source_checks_for_run(
            candidate.run_id, candidate.source_ids
        )
    }
    sources: list[dict[str, object]] = []
    for source_id in candidate.source_ids:
        source = source_index.get(source_id)
        check = checks.get(source_id)
        evidence = ""
        evidence_error = None
        if source and check and check.get("raw_file_path"):
            raw_path = repository_root / str(check["raw_file_path"])
            try:
                body = raw_path.read_text(encoding="utf-8")
                collected = CollectedSource(
                    source=source,
                    collected_at=cast(datetime, check["collected_at"]),
                    body=body,
                    status_code=200,
                    collector_type="review",
                )
                evidence = parse_collected_source(collected)
            except (OSError, UnicodeError, ParseError) as exc:
                evidence_error = str(exc)
        sources.append(
            {
                "source_id": source_id,
                "title": source.title if source else None,
                "url": source.url if source else check.get("source_url") if check else None,
                "collected_at": (
                    cast(datetime, check["collected_at"]).isoformat()
                    if check
                    else None
                ),
                "normalized_text_hash": (
                    check.get("normalized_text_hash") if check else None
                ),
                "evidence": evidence,
                "evidence_error": evidence_error,
            }
        )
    return {
        "candidate": candidate,
        "payload": payload,
        "diff": content_diff(candidate.previous_content, candidate_content),
        "sources": sources,
    }


def format_candidate_list(candidates: list[CandidateRecord]) -> str:
    if not candidates:
        return "No candidates found."
    header = "candidate_id | operation | status | logical_document_id | created_at"
    rows = [header]
    rows.extend(
        f"{candidate.candidate_id} | {candidate.operation.value} | "
        f"{candidate.status.value} | {candidate.logical_document_id} | "
        f"{candidate.created_at.isoformat()}"
        for candidate in candidates
    )
    return "\n".join(rows)


def format_candidate_detail(detail: dict[str, object]) -> str:
    candidate = detail["candidate"]
    assert isinstance(candidate, CandidateRecord)
    payload = detail["payload"]
    assert isinstance(payload, dict)
    metadata = payload.get("metadata") or {}
    lines = [
        f"candidate_id: {candidate.candidate_id}",
        f"logical_document_id: {candidate.logical_document_id}",
        f"operation: {candidate.operation.value}",
        f"status: {candidate.status.value}",
        f"previous_revision_id: {candidate.previous_revision_id or '-'}",
        f"candidate_revision_id: {candidate.candidate_revision_id or '-'}",
        f"previous_content_hash: {candidate.previous_content_hash or '-'}",
        f"candidate_content_hash: {candidate.candidate_content_hash or '-'}",
        f"as_of: {payload.get('as_of') or '-'}",
        f"review_note: {candidate.review_note or '-'}",
        "",
        "[previous content]",
        candidate.previous_content or "(none)",
        "",
        "[candidate content]",
        str(payload.get("content") or "(none)"),
        "",
        "[limitations]",
    ]
    limitations = metadata.get("limitations", []) if isinstance(metadata, dict) else []
    lines.extend(f"- {item}" for item in limitations)
    if not limitations:
        lines.append("(none)")
    lines.extend(["", "[diff]", str(detail["diff"]), "", "[sources]"])
    sources = detail["sources"]
    assert isinstance(sources, list)
    for source in sources:
        assert isinstance(source, dict)
        lines.extend(
            [
                f"source_id: {source['source_id']}",
                f"title: {source['title'] or '-'}",
                f"url: {source['url'] or '-'}",
                f"collected_at: {source['collected_at'] or '-'}",
                f"normalized_text_hash: {source['normalized_text_hash'] or '-'}",
                "evidence:",
                str(source["evidence"] or source["evidence_error"] or "(unavailable)"),
                "",
            ]
        )
    return "\n".join(lines).rstrip()
