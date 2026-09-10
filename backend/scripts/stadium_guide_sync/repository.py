from __future__ import annotations

import json
from pathlib import Path

import asyncpg

from .schemas import ActiveDocument, ChangeOperation


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
        return ActiveDocument.model_validate(dict(row)) if row else None

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
