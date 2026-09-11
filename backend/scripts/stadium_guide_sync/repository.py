from __future__ import annotations

import json
from pathlib import Path

import asyncpg

from .schemas import (
    ActiveDocument,
    CandidateRecord,
    CandidateStatus,
    ChangeOperation,
)


def _json_object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        if isinstance(decoded, dict):
            return decoded
    return {}


class StadiumGuideSyncRepository:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self._connection = connection

    async def start_run(self, run_id: str, scope: dict[str, object], source_count: int) -> None:
        await self._connection.execute(
            """
            insert into public.stadium_guide_sync_runs (run_id, scope, status, source_count)
            values ($1, $2::jsonb, 'running', $3)
            """,
            run_id,
            json.dumps(scope, ensure_ascii=False),
            source_count,
        )

    async def latest_source_check(self, source_id: str) -> asyncpg.Record | None:
        return await self._connection.fetchrow(
            """
            select result_status, raw_content_hash, normalized_text_hash,
                   raw_file_path, consecutive_missing_count
            from public.stadium_guide_source_checks
            where source_id = $1
            order by collected_at desc
            limit 1
            """,
            source_id,
        )

    async def record_source_check(
        self,
        *,
        run_id: str,
        source_id: str,
        source_url: str,
        result_status: str,
        collector_type: str,
        parser_name: str,
        raw_content_hash: str | None = None,
        normalized_text_hash: str | None = None,
        raw_file_path: Path | str | None = None,
        http_status: int | None = None,
        consecutive_missing_count: int = 0,
        error_code: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        await self._connection.execute(
            """
            insert into public.stadium_guide_source_checks (
              run_id, source_id, source_url, result_status, raw_content_hash,
              normalized_text_hash, raw_file_path, http_status, collector_type,
              parser_name, consecutive_missing_count, error_code, metadata
            ) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb)
            """,
            run_id,
            source_id,
            source_url,
            result_status,
            raw_content_hash,
            normalized_text_hash,
            str(raw_file_path) if raw_file_path else None,
            http_status,
            collector_type,
            parser_name,
            consecutive_missing_count,
            error_code,
            json.dumps(metadata or {}, ensure_ascii=False),
        )

    async def find_open_candidate(
        self,
        logical_document_id: str,
        source_fingerprint: str,
    ) -> asyncpg.Record | None:
        return await self._connection.fetchrow(
            """
            select candidate_id, operation
            from public.stadium_guide_change_candidates
            where logical_document_id = $1
              and status in ('pending', 'approved', 'applied_local', 'ready_for_production')
              and diff_summary ->> 'source_fingerprint' = $2
            order by created_at desc
            limit 1
            """,
            logical_document_id,
            source_fingerprint,
        )

    async def active_document(self, logical_document_id: str) -> ActiveDocument | None:
        row = await self._connection.fetchrow(
            """
            select d.document_id, d.logical_document_id, d.revision_number,
                   d.content_hash, d.title, d.metadata,
                   coalesce(c.content, '') as content
            from public.rag_documents d
            left join lateral (
              select content from public.rag_chunks
              where document_id = d.document_id
              order by chunk_index limit 1
            ) c on true
            where d.logical_document_id = $1 and d.is_active
            """,
            logical_document_id,
        )
        if not row:
            return None
        payload = dict(row)
        payload["metadata"] = _json_object(payload.get("metadata"))
        return ActiveDocument.model_validate(payload)

    async def list_candidates(
        self,
        *,
        status: CandidateStatus | None = None,
        limit: int = 50,
    ) -> list[CandidateRecord]:
        rows = await self._connection.fetch(
            """
            select c.*, ''::text as previous_content
            from public.stadium_guide_change_candidates c
            where ($1::text is null or c.status = $1)
            order by c.created_at desc
            limit $2
            """,
            status.value if status else None,
            limit,
        )
        return [self._candidate_from_row(row) for row in rows]

    async def candidate(self, candidate_id: str) -> CandidateRecord | None:
        row = await self._connection.fetchrow(
            """
            select c.*, coalesce(chunks.content, '') as previous_content
            from public.stadium_guide_change_candidates c
            left join lateral (
              select content
              from public.rag_chunks
              where document_id = c.previous_revision_id
              order by chunk_index
              limit 1
            ) chunks on true
            where c.candidate_id = $1
            """,
            candidate_id,
        )
        return self._candidate_from_row(row) if row else None

    async def latest_source_checks(
        self,
        source_ids: list[str],
    ) -> list[dict[str, object]]:
        if not source_ids:
            return []
        rows = await self._connection.fetch(
            """
            select distinct on (source_id)
              source_id, source_url, result_status, raw_file_path,
              normalized_text_hash, parser_name, collected_at
            from public.stadium_guide_source_checks
            where source_id = any($1::text[])
            order by source_id, collected_at desc
            """,
            source_ids,
        )
        return [dict(row) for row in rows]

    async def review_candidate(
        self,
        *,
        candidate_id: str,
        decision: CandidateStatus,
        review_note: str | None = None,
    ) -> CandidateRecord:
        if decision not in {CandidateStatus.APPROVED, CandidateStatus.REJECTED}:
            raise ValueError("decision must be approved or rejected")
        if decision == CandidateStatus.REJECTED and not (review_note or "").strip():
            raise ValueError("a rejection reason is required")
        async with self._connection.transaction():
            row = await self._connection.fetchrow(
                """
                select status from public.stadium_guide_change_candidates
                where candidate_id = $1
                for update
                """,
                candidate_id,
            )
            if not row:
                raise ValueError(f"candidate not found: {candidate_id}")
            current = CandidateStatus(row["status"])
            if current == decision:
                existing = await self.candidate(candidate_id)
                assert existing is not None
                return existing
            if current != CandidateStatus.PENDING:
                raise ValueError(
                    f"candidate in {current.value} cannot be reviewed as {decision.value}"
                )
            await self._connection.execute(
                """
                update public.stadium_guide_change_candidates
                set status = $2, reviewed_at = now(), review_note = $3
                where candidate_id = $1
                """,
                candidate_id,
                decision.value,
                review_note,
            )
        reviewed = await self.candidate(candidate_id)
        assert reviewed is not None
        return reviewed

    async def apply_candidate_revision(
        self,
        *,
        candidate_id: str,
        embedding_text: str | None,
        embedding_vector: str | None,
        source_urls: list[str],
        embedding_model: str = "text-embedding-3-small",
        embedding_dimensions: int = 1536,
    ) -> tuple[str, bool]:
        async with self._connection.transaction():
            row = await self._connection.fetchrow(
                """
                select * from public.stadium_guide_change_candidates
                where candidate_id = $1
                for update
                """,
                candidate_id,
            )
            if not row:
                raise ValueError(f"candidate not found: {candidate_id}")
            status = CandidateStatus(row["status"])
            operation = ChangeOperation(row["operation"])
            revision_id = row["candidate_revision_id"] or row["previous_revision_id"]
            if status in {
                CandidateStatus.APPLIED_LOCAL,
                CandidateStatus.EVALUATION_FAILED,
                CandidateStatus.READY_FOR_PRODUCTION,
                CandidateStatus.PROMOTED,
            }:
                if not revision_id:
                    raise ValueError("applied candidate has no revision id")
                return str(revision_id), True
            if status != CandidateStatus.APPROVED:
                raise ValueError(
                    f"candidate must be approved before apply-local: {status.value}"
                )

            active = await self._connection.fetchrow(
                """
                select document_id, content_hash
                from public.rag_documents
                where logical_document_id = $1 and is_active
                for update
                """,
                row["logical_document_id"],
            )
            expected_previous = row["previous_revision_id"]
            if expected_previous is None and active is not None:
                raise ValueError("CREATE candidate conflicts with a new active revision")
            if expected_previous is not None:
                if active is None or active["document_id"] != expected_previous:
                    raise ValueError("active revision changed after candidate generation")
                if active["content_hash"] != row["previous_content_hash"]:
                    raise ValueError("active content hash changed after candidate generation")

            if operation == ChangeOperation.DELETE_CANDIDATE:
                if active is None:
                    raise ValueError("DELETE_CANDIDATE has no active revision")
                await self._connection.execute(
                    """
                    update public.rag_documents
                    set is_active = false, deactivated_at = now()
                    where document_id = $1
                    """,
                    active["document_id"],
                )
                revision_id = str(active["document_id"])
                action = "deactivate"
            else:
                if not embedding_text or not embedding_vector:
                    raise ValueError("embedding is required for this operation")
                payload = _json_object(row["candidate_payload"])
                revision_id = str(payload.get("revision_id") or "")
                if not revision_id or revision_id != row["candidate_revision_id"]:
                    raise ValueError("candidate revision identity is inconsistent")
                if payload.get("content_hash") != row["candidate_content_hash"]:
                    raise ValueError("candidate content hash is inconsistent")
                if active is not None:
                    await self._connection.execute(
                        """
                        update public.rag_documents
                        set is_active = false, deactivated_at = now()
                        where document_id = $1
                        """,
                        active["document_id"],
                    )
                metadata = _json_object(payload.get("metadata"))
                await self._connection.execute(
                    """
                    insert into public.rag_documents (
                      document_id, document_type, stadium_id, team_id, title,
                      as_of, trust_level, review_status, source_ids, source_urls,
                      content_hash, metadata, logical_document_id, revision_number,
                      is_active, activated_at, deactivated_at, legacy_unreviewed
                    ) values (
                      $1,$2,$3,$4,$5,$6::date,$7,'approved',$8,$9,$10,$11::jsonb,
                      $12,$13,true,now(),null,false
                    )
                    """,
                    revision_id,
                    payload["document_type"],
                    payload.get("stadium_id"),
                    payload.get("team_id"),
                    payload["title"],
                    payload["as_of"],
                    payload["trust_level"],
                    list(payload.get("sources") or []),
                    source_urls,
                    payload["content_hash"],
                    json.dumps(metadata, ensure_ascii=False),
                    row["logical_document_id"],
                    payload["revision_number"],
                )
                await self._connection.execute(
                    """
                    insert into public.rag_chunks (
                      chunk_id, document_id, chunk_index, stadium_id, team_id,
                      document_type, title, chunk_text, content, embedding,
                      embedding_model, embedding_dimensions, as_of, trust_level,
                      review_status, source_ids, source_urls, content_hash, metadata
                    ) values (
                      $1,$2,0,$3,$4,$5,$6,$7,$8,$9::extensions.vector,$10,$11,
                      $12::date,$13,'approved',$14,$15,$16,$17::jsonb
                    )
                    """,
                    f"{revision_id}_chunk_000",
                    revision_id,
                    payload.get("stadium_id"),
                    payload.get("team_id"),
                    payload["document_type"],
                    payload["title"],
                    embedding_text,
                    payload["content"],
                    embedding_vector,
                    embedding_model,
                    embedding_dimensions,
                    payload["as_of"],
                    payload["trust_level"],
                    list(payload.get("sources") or []),
                    source_urls,
                    payload["content_hash"],
                    json.dumps(metadata, ensure_ascii=False),
                )
                action = "promote"

            await self._connection.execute(
                """
                insert into public.stadium_guide_deployments (
                  candidate_id, revision_id, target, action,
                  previous_active_revision_id, status, metadata
                ) values ($1,$2,'local',$3,$4,'completed',$5::jsonb)
                on conflict (candidate_id, revision_id, target, action) do nothing
                """,
                candidate_id,
                revision_id,
                action,
                row["previous_revision_id"],
                json.dumps(
                    {
                        "embedding_model": embedding_model,
                        "embedding_dimensions": embedding_dimensions,
                    },
                    ensure_ascii=False,
                ),
            )
            await self._connection.execute(
                """
                update public.stadium_guide_change_candidates
                set status = 'applied_local'
                where candidate_id = $1
                """,
                candidate_id,
            )
            return revision_id, False

    async def finalize_evaluation(
        self,
        *,
        candidate_id: str,
        revision_id: str,
        evaluation_run_id: str,
        passed: bool,
        summary: dict[str, object],
    ) -> CandidateRecord:
        status = (
            CandidateStatus.READY_FOR_PRODUCTION
            if passed
            else CandidateStatus.EVALUATION_FAILED
        )
        async with self._connection.transaction():
            await self._connection.execute(
                """
                update public.stadium_guide_change_candidates
                set status = $2, review_note = concat_ws(E'\n', review_note, $3)
                where candidate_id = $1
                  and status in ('applied_local', 'evaluation_failed')
                """,
                candidate_id,
                status.value,
                f"evaluation {evaluation_run_id}: {'passed' if passed else 'failed'}",
            )
            await self._connection.execute(
                """
                update public.stadium_guide_deployments
                set evaluation_run_id = $3,
                    metadata = metadata || $4::jsonb
                where candidate_id = $1 and revision_id = $2 and target = 'local'
                """,
                candidate_id,
                revision_id,
                evaluation_run_id,
                json.dumps({"evaluation": summary}, ensure_ascii=False),
            )
        candidate = await self.candidate(candidate_id)
        if not candidate:
            raise ValueError(f"candidate not found: {candidate_id}")
        return candidate

    @staticmethod
    def _candidate_from_row(row: asyncpg.Record) -> CandidateRecord:
        payload = dict(row)
        payload["candidate_payload"] = _json_object(payload.get("candidate_payload"))
        payload["diff_summary"] = _json_object(payload.get("diff_summary"))
        payload["source_ids"] = list(payload.get("source_ids") or [])
        return CandidateRecord.model_validate(payload)

    async def create_candidate(
        self,
        *,
        candidate_id: str,
        run_id: str,
        logical_document_id: str,
        operation: ChangeOperation,
        previous: ActiveDocument | None,
        candidate_revision_id: str | None,
        candidate_content_hash: str | None,
        candidate_payload: dict[str, object],
        diff_summary: dict[str, object],
        source_ids: list[str],
    ) -> bool:
        result = await self._connection.execute(
            """
            insert into public.stadium_guide_change_candidates (
              candidate_id, run_id, logical_document_id, operation,
              previous_revision_id, candidate_revision_id, previous_content_hash,
              candidate_content_hash, candidate_payload, diff_summary, source_ids
            ) values ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb,$11)
            on conflict do nothing
            """,
            candidate_id,
            run_id,
            logical_document_id,
            operation.value,
            previous.document_id if previous else None,
            candidate_revision_id,
            previous.content_hash if previous else None,
            candidate_content_hash,
            json.dumps(candidate_payload, ensure_ascii=False),
            json.dumps(diff_summary, ensure_ascii=False),
            source_ids,
        )
        return result == "INSERT 0 1"

    async def finish_run(self, run_id: str, counts: dict[str, int]) -> None:
        status = "completed_with_failures" if counts["failure"] else "completed"
        await self._connection.execute(
            """
            update public.stadium_guide_sync_runs set
              status=$2, create_count=$3, update_count=$4, unchanged_count=$5,
              delete_candidate_count=$6, manual_required_count=$7, failure_count=$8,
              finished_at=now(), updated_at=now()
            where run_id=$1
            """,
            run_id,
            status,
            counts["create"],
            counts["update"],
            counts["unchanged"],
            counts["delete_candidate"],
            counts["manual_required"],
            counts["failure"],
        )
