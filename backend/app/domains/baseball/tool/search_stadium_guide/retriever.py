from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.baseball.tool.search_stadium_guide.schemas import (
    StadiumGuideSearchItem,
    StadiumGuideType,
)


def vector_literal(embedding: Sequence[float]) -> str:
    """Return a pgvector literal for a query embedding."""

    return "[" + ",".join(str(value) for value in embedding) + "]"


class PgVectorStadiumGuideRetriever:
    """Supabase pgvector 기반 구장 안내 chunk 검색기입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        *,
        query_embedding: Sequence[float],
        stadium_id: str,
        document_types: Sequence[str],
        guide_types: Sequence[StadiumGuideType] | None = None,
        top_k: int = 5,
        relevance_threshold: float = 0.65,
    ) -> list[StadiumGuideSearchItem]:
        """stadium_id와 선택적 document_type filter로 관련 구장 안내 chunk를 검색합니다."""

        normalized_stadium_id = stadium_id.strip().upper()
        normalized_document_types = list(dict.fromkeys(document_types))
        normalized_guide_types = list(dict.fromkeys(guide_types or []))
        statement = text(
            """
            select
              chunks.chunk_id,
              chunks.document_id,
              chunks.document_type,
              chunks.stadium_id,
              chunks.team_id,
              chunks.title,
              chunks.content,
              chunks.source_urls,
              chunks.as_of,
              chunks.trust_level,
              chunks.review_status,
              chunks.metadata,
              chunks.embedding <=> cast(:query_embedding as extensions.vector) as distance
            from public.rag_chunks as chunks
            join public.rag_documents as documents
              on documents.document_id = chunks.document_id
            where (
                chunks.stadium_id = :stadium_id
                or chunks.stadium_id is null
              )
              and documents.is_active
              and documents.logical_document_id is not null
              and (
                chunks.review_status = 'approved'
                or documents.legacy_unreviewed
              )
              and chunks.embedding is not null
              and chunks.document_type = any(:document_types)
              and (
                cardinality(:guide_types) = 0
                or chunks.document_type = any(:guide_types)
              )
            order by
              (chunks.stadium_id = :stadium_id) desc nulls last,
              chunks.embedding <=> cast(:query_embedding as extensions.vector)
            limit :top_k
            """
        ).bindparams(
            bindparam("document_types", type_=ARRAY(Text())),
            bindparam("guide_types", type_=ARRAY(Text())),
        )

        result = await self._session.execute(
            statement,
            {
                "query_embedding": vector_literal(query_embedding),
                "stadium_id": normalized_stadium_id,
                "document_types": normalized_document_types,
                "guide_types": normalized_guide_types,
                "top_k": top_k,
            },
        )

        rows = result.mappings().all()
        return [
            self._to_item(row, relevance_threshold)
            for row in rows
            if float(row["distance"]) <= relevance_threshold
        ]

    def _to_item(
        self,
        row: Any,
        relevance_threshold: float,
    ) -> StadiumGuideSearchItem:
        distance = float(row["distance"])
        similarity = max(0.0, min(1.0, 1.0 - (distance / relevance_threshold)))

        return StadiumGuideSearchItem(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            document_type=row["document_type"],
            stadium_id=row["stadium_id"],
            team_id=row["team_id"],
            title=row["title"],
            content=row["content"],
            similarity=similarity,
            distance=distance,
            source_urls=list(row["source_urls"] or []),
            as_of=row["as_of"],
            trust_level=row["trust_level"],
            review_status=row["review_status"],
            metadata=dict(row["metadata"] or {}),
        )
