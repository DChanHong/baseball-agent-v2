from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import asyncpg

from .schemas import CandidateStatus, ChangeOperation

REQUIRED_REVISION_COLUMNS = {
    "is_active",
    "legacy_unreviewed",
    "logical_document_id",
    "revision_number",
}
LEGACY_REVISION_OFFSET = 1_000_000


@dataclass(frozen=True, slots=True)
class PromotionResult:
    candidate_id: str
    revision_id: str
    logical_document_id: str
    previous_active_revision_id: str | None
    already_promoted: bool


@dataclass(frozen=True, slots=True)
class RollbackResult:
    logical_document_id: str
    revision_id: str
    previous_active_revision_id: str | None
    already_active: bool


class ProductionSchemaError(RuntimeError):
    pass


class ProductionPromotionService:
    def __init__(
        self,
        *,
        local_connection: asyncpg.Connection,
        production_connection: asyncpg.Connection,
    ) -> None:
        self._local = local_connection
        self._production = production_connection

    async def promote(self, candidate_id: str) -> PromotionResult:
        await self._assert_production_schema()
        candidate = await self._load_candidate(candidate_id)
        operation = ChangeOperation(str(candidate["operation"]))
        if operation == ChangeOperation.DELETE_CANDIDATE:
            result = await self._promote_deactivation(candidate)
        else:
            bundle = await self._load_revision_bundle(candidate)
            result = await self._promote_revision(candidate, bundle)
        await self._mark_local_promoted(candidate_id)
        return result

    async def rollback(
        self,
        *,
        logical_document_id: str,
        revision_id: str,
    ) -> RollbackResult:
        await self._assert_production_schema()
        async with self._production.transaction():
            await self._production.execute(
                "select pg_advisory_xact_lock(hashtext($1))",
                logical_document_id,
            )
            target = await self._production.fetchrow(
                """
                select document_id, review_status, legacy_unreviewed, is_active
                from public.rag_documents
                where logical_document_id = $1 and document_id = $2
                for update
                """,
                logical_document_id,
                revision_id,
            )
            if not target:
                raise ValueError(f"rollback revision not found: {revision_id}")
            if target["review_status"] != "approved" and not target["legacy_unreviewed"]:
                raise ValueError("rollback revision is neither approved nor legacy")
            current = await self._production.fetchrow(
                """
                select document_id
                from public.rag_documents
                where logical_document_id = $1 and is_active
                for update
                """,
                logical_document_id,
            )
            if target["is_active"]:
                return RollbackResult(
                    logical_document_id=logical_document_id,
                    revision_id=revision_id,
                    previous_active_revision_id=revision_id,
                    already_active=True,
                )
            previous_id = str(current["document_id"]) if current else None
            if current:
                await self._production.execute(
                    """
                    update public.rag_documents
                    set is_active = false, deactivated_at = now()
                    where document_id = $1
                    """,
                    previous_id,
                )
            await self._production.execute(
                """
                update public.rag_documents
                set is_active = true, activated_at = now(), deactivated_at = null
                where document_id = $1
                """,
                revision_id,
            )
            rollback_key = f"rollback:{previous_id or 'none'}:{revision_id}"
            await self._production.execute(
                """
                insert into public.stadium_guide_deployments (
                  candidate_id, revision_id, target, action,
                  previous_active_revision_id, status, metadata
                ) values ($1,$2,'production','rollback',$3,'completed',$4::jsonb)
                on conflict (candidate_id, revision_id, target, action) do nothing
                """,
                rollback_key,
                revision_id,
                previous_id,
                json.dumps(
                    {"logical_document_id": logical_document_id},
                    ensure_ascii=False,
                ),
            )
            return RollbackResult(
                logical_document_id=logical_document_id,
                revision_id=revision_id,
                previous_active_revision_id=previous_id,
                already_active=False,
            )

    async def _assert_production_schema(self) -> None:
        rows = await self._production.fetch(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public'
              and table_name = 'rag_documents'
              and column_name = any($1::text[])
            """,
            sorted(REQUIRED_REVISION_COLUMNS),
        )
        available = {str(row["column_name"]) for row in rows}
        missing = REQUIRED_REVISION_COLUMNS - available
        if missing:
            joined = ", ".join(sorted(missing))
            raise ProductionSchemaError(
                f"production revision migration is required; missing: {joined}"
            )

    async def _load_candidate(self, candidate_id: str) -> asyncpg.Record:
        row = await self._local.fetchrow(
            """
            select *
            from public.stadium_guide_change_candidates
            where candidate_id = $1
            """,
            candidate_id,
        )
        if not row:
            raise ValueError(f"candidate not found in local DB: {candidate_id}")
        status = CandidateStatus(str(row["status"]))
        if status not in {
            CandidateStatus.READY_FOR_PRODUCTION,
            CandidateStatus.PROMOTED,
        }:
            raise ValueError(
                f"candidate must be ready_for_production: {status.value}"
            )
        return row

    async def _load_revision_bundle(
        self,
        candidate: asyncpg.Record,
    ) -> asyncpg.Record:
        revision_id = str(candidate["candidate_revision_id"] or "")
        if not revision_id:
            raise ValueError("candidate has no revision to promote")
        row = await self._local.fetchrow(
            """
            select
              d.document_id, d.document_type, d.stadium_id, d.team_id,
              d.title, d.as_of, d.trust_level, d.review_status,
              d.source_ids, d.source_urls, d.content_hash, d.metadata,
              d.logical_document_id, d.revision_number,
              c.chunk_id, c.chunk_index, c.chunk_text, c.content,
              c.embedding::text as embedding, c.embedding_model,
              c.embedding_dimensions, c.metadata as chunk_metadata,
              dep.evaluation_run_id, dep.metadata as deployment_metadata
            from public.rag_documents d
            join public.rag_chunks c on c.document_id = d.document_id
            join public.stadium_guide_deployments dep
              on dep.candidate_id = $1
             and dep.revision_id = d.document_id
             and dep.target = 'local'
             and dep.action = 'promote'
             and dep.status = 'completed'
            where d.document_id = $2
              and d.is_active
            """,
            candidate["candidate_id"],
            revision_id,
        )
        if not row:
            raise ValueError("locally applied revision bundle was not found")
        if row["review_status"] != "approved":
            raise ValueError("local revision is not approved")
        if row["content_hash"] != candidate["candidate_content_hash"]:
            raise ValueError("local revision content hash differs from candidate")
        if row["logical_document_id"] != candidate["logical_document_id"]:
            raise ValueError("local revision logical ID differs from candidate")
        if row["chunk_index"] != 0 or not row["embedding"]:
            raise ValueError("local revision must have one embedded chunk at index 0")
        deployment_metadata = _json_object(row["deployment_metadata"])
        evaluation = _json_object(deployment_metadata.get("evaluation"))
        if not row["evaluation_run_id"] or evaluation.get("passed") is not True:
            raise ValueError("local revision has no passing evaluation")
        return row

    async def _mark_local_promoted(self, candidate_id: str) -> None:
        await self._local.execute(
            """
            update public.stadium_guide_change_candidates
            set status = 'promoted', updated_at = now()
            where candidate_id = $1
              and status in ('ready_for_production', 'promoted')
            """,
            candidate_id,
        )

    async def _promote_revision(
        self,
        candidate: asyncpg.Record,
        bundle: asyncpg.Record,
    ) -> PromotionResult:
        candidate_id = str(candidate["candidate_id"])
        revision_id = str(bundle["document_id"])
        logical_id = str(bundle["logical_document_id"])
        async with self._production.transaction():
            await self._production.execute(
                "select pg_advisory_xact_lock(hashtext($1))",
                logical_id,
            )
            completed = await self._production.fetchrow(
                """
                select deployment_id, previous_active_revision_id
                from public.stadium_guide_deployments
                where candidate_id = $1
                  and revision_id = $2
                  and target = 'production'
                  and action = 'promote'
                  and status = 'completed'
                """,
                candidate_id,
                revision_id,
            )
            existing = await self._production.fetchrow(
                """
                select document_id, content_hash, is_active
                from public.rag_documents
                where document_id = $1
                for update
                """,
                revision_id,
            )
            if completed:
                if (
                    not existing
                    or existing["content_hash"] != bundle["content_hash"]
                    or not existing["is_active"]
                ):
                    raise ValueError(
                        "completed production deployment does not match active revision"
                    )
                return PromotionResult(
                    candidate_id=candidate_id,
                    revision_id=revision_id,
                    logical_document_id=logical_id,
                    previous_active_revision_id=completed[
                        "previous_active_revision_id"
                    ],
                    already_promoted=True,
                )

            current = await self._production.fetchrow(
                """
                select document_id
                from public.rag_documents
                where logical_document_id = $1 and is_active
                for update
                """,
                logical_id,
            )
            previous_id = str(current["document_id"]) if current else None
            if existing and existing["content_hash"] != bundle["content_hash"]:
                raise ValueError("production revision ID has a different content hash")

            if not existing:
                collision = await self._production.fetchrow(
                    """
                    select document_id, legacy_unreviewed
                    from public.rag_documents
                    where logical_document_id = $1 and revision_number = $2
                    for update
                    """,
                    logical_id,
                    bundle["revision_number"],
                )
                if collision:
                    if not collision["legacy_unreviewed"]:
                        raise ValueError(
                            "production revision number belongs to a reviewed document"
                        )
                    reserved_number = await self._production.fetchval(
                        """
                        select coalesce(max(revision_number), 0) + $2
                        from public.rag_documents
                        where logical_document_id = $1
                        """,
                        logical_id,
                        LEGACY_REVISION_OFFSET,
                    )
                    await self._production.execute(
                        """
                        update public.rag_documents
                        set revision_number = $2
                        where document_id = $1
                        """,
                        collision["document_id"],
                        reserved_number,
                    )

            if current and previous_id != revision_id:
                await self._production.execute(
                    """
                    update public.rag_documents
                    set is_active = false, deactivated_at = now()
                    where document_id = $1
                    """,
                    previous_id,
                )

            if existing:
                await self._production.execute(
                    """
                    update public.rag_documents
                    set is_active = true, activated_at = now(), deactivated_at = null
                    where document_id = $1
                    """,
                    revision_id,
                )
            else:
                await self._insert_revision(bundle)

            await self._record_production_deployment(
                candidate_id=candidate_id,
                revision_id=revision_id,
                action="promote",
                previous_active_revision_id=previous_id,
                evaluation_run_id=str(bundle["evaluation_run_id"]),
                metadata={
                    "content_hash": str(bundle["content_hash"]),
                    "embedding_model": str(bundle["embedding_model"]),
                    "embedding_dimensions": int(bundle["embedding_dimensions"]),
                    "local_evaluation": _json_object(
                        bundle["deployment_metadata"]
                    ).get("evaluation", {}),
                },
            )
            return PromotionResult(
                candidate_id=candidate_id,
                revision_id=revision_id,
                logical_document_id=logical_id,
                previous_active_revision_id=previous_id,
                already_promoted=False,
            )

    async def _insert_revision(self, bundle: asyncpg.Record) -> None:
        await self._production.execute(
            """
            insert into public.rag_documents (
              document_id, document_type, stadium_id, team_id, title,
              as_of, trust_level, review_status, source_ids, source_urls,
              content_hash, metadata, logical_document_id, revision_number,
              is_active, activated_at, deactivated_at, legacy_unreviewed
            ) values (
              $1,$2,$3,$4,$5,$6,$7,'approved',$8,$9,$10,$11::jsonb,
              $12,$13,true,now(),null,false
            )
            """,
            bundle["document_id"],
            bundle["document_type"],
            bundle["stadium_id"],
            bundle["team_id"],
            bundle["title"],
            bundle["as_of"],
            bundle["trust_level"],
            bundle["source_ids"],
            bundle["source_urls"],
            bundle["content_hash"],
            json.dumps(_json_object(bundle["metadata"]), ensure_ascii=False),
            bundle["logical_document_id"],
            bundle["revision_number"],
        )
        await self._production.execute(
            """
            insert into public.rag_chunks (
              chunk_id, document_id, chunk_index, stadium_id, team_id,
              document_type, title, chunk_text, content, embedding,
              embedding_model, embedding_dimensions, as_of, trust_level,
              review_status, source_ids, source_urls, content_hash, metadata
            ) values (
              $1,$2,$3,$4,$5,$6,$7,$8,$9,$10::extensions.vector,
              $11,$12,$13,$14,'approved',$15,$16,$17,$18::jsonb
            )
            """,
            bundle["chunk_id"],
            bundle["document_id"],
            bundle["chunk_index"],
            bundle["stadium_id"],
            bundle["team_id"],
            bundle["document_type"],
            bundle["title"],
            bundle["chunk_text"],
            bundle["content"],
            bundle["embedding"],
            bundle["embedding_model"],
            bundle["embedding_dimensions"],
            bundle["as_of"],
            bundle["trust_level"],
            bundle["source_ids"],
            bundle["source_urls"],
            bundle["content_hash"],
            json.dumps(_json_object(bundle["chunk_metadata"]), ensure_ascii=False),
        )

    async def _record_production_deployment(
        self,
        *,
        candidate_id: str,
        revision_id: str,
        action: str,
        previous_active_revision_id: str | None,
        evaluation_run_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        await self._production.execute(
            """
            insert into public.stadium_guide_deployments (
              candidate_id, revision_id, target, action, evaluation_run_id,
              previous_active_revision_id, status, metadata
            ) values ($1,$2,'production',$3,$4,$5,'completed',$6::jsonb)
            on conflict (candidate_id, revision_id, target, action) do nothing
            """,
            candidate_id,
            revision_id,
            action,
            evaluation_run_id,
            previous_active_revision_id,
            json.dumps(metadata, ensure_ascii=False),
        )

    async def _promote_deactivation(
        self,
        candidate: asyncpg.Record,
    ) -> PromotionResult:
        candidate_id = str(candidate["candidate_id"])
        logical_id = str(candidate["logical_document_id"])
        revision_id = str(candidate["previous_revision_id"] or "")
        if not revision_id:
            raise ValueError("DELETE_CANDIDATE has no previous revision")
        async with self._production.transaction():
            await self._production.execute(
                "select pg_advisory_xact_lock(hashtext($1))",
                logical_id,
            )
            completed = await self._production.fetchrow(
                """
                select revision_id, previous_active_revision_id
                from public.stadium_guide_deployments
                where candidate_id = $1
                  and target = 'production' and action = 'deactivate'
                  and status = 'completed'
                """,
                candidate_id,
            )
            if completed:
                return PromotionResult(
                    candidate_id=candidate_id,
                    revision_id=str(completed["revision_id"]),
                    logical_document_id=logical_id,
                    previous_active_revision_id=completed[
                        "previous_active_revision_id"
                    ],
                    already_promoted=True,
                )
            active = await self._production.fetchrow(
                """
                select document_id, content_hash
                from public.rag_documents
                where logical_document_id = $1 and is_active
                for update
                """,
                logical_id,
            )
            if not active:
                raise ValueError("production document is already inactive or missing")
            if (
                candidate["previous_content_hash"]
                and active["content_hash"] != candidate["previous_content_hash"]
            ):
                raise ValueError("production active content differs from delete candidate")
            production_revision_id = str(active["document_id"])
            await self._production.execute(
                """
                update public.rag_documents
                set is_active = false, deactivated_at = now()
                where document_id = $1
                """,
                production_revision_id,
            )
            await self._record_production_deployment(
                candidate_id=candidate_id,
                revision_id=production_revision_id,
                action="deactivate",
                previous_active_revision_id=production_revision_id,
                evaluation_run_id=None,
                metadata={"logical_document_id": logical_id},
            )
            return PromotionResult(
                candidate_id=candidate_id,
                revision_id=production_revision_id,
                logical_document_id=logical_id,
                previous_active_revision_id=production_revision_id,
                already_promoted=False,
            )


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    return dict(value) if isinstance(value, dict) else {}
