from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    BaseballKnowledgeSearchItem,
    BaseballKnowledgeType,
)


def vector_literal(embedding: Sequence[float]) -> str:
    """Return a pgvector literal for a query embedding."""

    return "[" + ",".join(str(value) for value in embedding) + "]"


class PgVectorBaseballKnowledgeRetriever:
    """Supabase pgvector 기반 야구 지식 chunk 검색기입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        *,
        query_embedding: Sequence[float],
        document_types: Sequence[str],
        knowledge_types: Sequence[BaseballKnowledgeType] | None = None,
        top_k: int = 5,
        relevance_threshold: float = 0.82,
    ) -> list[BaseballKnowledgeSearchItem]:
        """선택적 document_type filter로 관련 야구 지식 chunk를 검색합니다."""

        normalized_document_types = list(dict.fromkeys(document_types))
        normalized_knowledge_types = list(dict.fromkeys(knowledge_types or []))
        statement = text(
            """
            select
              chunk_id,
              document_id,
              document_type,
              title,
              content,
              source_urls,
              as_of,
              trust_level,
              review_status,
              metadata,
              embedding <=> cast(:query_embedding as extensions.vector) as distance
            from public.rag_chunks
            where stadium_id is null
              and team_id is null
              and embedding is not null
              and review_status != 'rejected'
              and document_type = any(:document_types)
              and (
                cardinality(:knowledge_types) = 0
                or document_type = any(:knowledge_types)
              )
            order by embedding <=> cast(:query_embedding as extensions.vector)
            limit :top_k
            """
        ).bindparams(
            bindparam("document_types", type_=ARRAY(Text())),
            bindparam("knowledge_types", type_=ARRAY(Text())),
        )

        result = await self._session.execute(
            statement,
            {
                "query_embedding": vector_literal(query_embedding),
                "document_types": normalized_document_types,
                "knowledge_types": normalized_knowledge_types,
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
    ) -> BaseballKnowledgeSearchItem:
        distance = float(row["distance"])
        similarity = max(0.0, min(1.0, 1.0 - (distance / relevance_threshold)))

        return BaseballKnowledgeSearchItem(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            document_type=row["document_type"],
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
