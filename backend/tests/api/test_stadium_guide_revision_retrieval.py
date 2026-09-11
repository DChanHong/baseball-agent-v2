from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.domains.baseball.tool.rag_config import STADIUM_GUIDE_RAG_CONFIG
from app.domains.baseball.tool.search_stadium_guide.retriever import (
    PgVectorStadiumGuideRetriever,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
)


class FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> FakeMappings:
        return FakeMappings(self._rows)


class FakeSession:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.statement: Any = None
        self.parameters: dict[str, Any] | None = None

    async def execute(self, statement: Any, parameters: dict[str, Any]) -> FakeResult:
        self.statement = statement
        self.parameters = parameters
        return FakeResult(self._rows)


@pytest.mark.asyncio
async def test_retriever_filters_active_revisions_and_includes_common_documents():
    session = FakeSession(
        [
            {
                "chunk_id": "KBO_common_stadium_bag_policy_r0001_chunk_000",
                "document_id": "KBO_common_stadium_bag_policy_r0001",
                "document_type": "stadium_bag_policy",
                "stadium_id": None,
                "team_id": None,
                "title": "KBO 공통 반입 정책",
                "content": "KBO 공통 안전 정책입니다.",
                "source_urls": ["https://example.com/kbo-safe"],
                "as_of": date(2026, 9, 10),
                "trust_level": "official",
                "review_status": "approved",
                "metadata": {},
                "distance": 0.1,
            }
        ]
    )
    retriever = PgVectorStadiumGuideRetriever(session)  # type: ignore[arg-type]

    items = await retriever.search(
        query_embedding=[0.1, 0.2, 0.3],
        stadium_id="gocheok",
        document_types=("stadium_bag_policy",),
    )

    statement = str(session.statement)
    assert "join public.rag_documents as documents" in statement
    assert "documents.is_active" in statement
    assert "documents.logical_document_id is not null" in statement
    assert "chunks.review_status = 'approved'" in statement
    assert "documents.legacy_unreviewed" in statement
    assert "chunks.stadium_id is null" in statement
    assert statement.index("(chunks.stadium_id = :stadium_id) desc") < statement.index(
        "chunks.embedding <=> cast(:query_embedding as extensions.vector)",
        statement.index("order by"),
    )
    assert session.parameters is not None
    assert session.parameters["stadium_id"] == "GOCHEOK"
    assert items[0].stadium_id is None


def test_stadium_guide_schema_and_config_support_new_document_types():
    new_types = {
        "stadium_food_guide",
        "stadium_entry_guide",
        "stadium_accessibility_guide",
    }

    assert new_types.issubset(set(STADIUM_GUIDE_RAG_CONFIG.document_types))

    tool_input = SearchStadiumGuideToolInput(
        stadium_id="gocheok",
        query="고척돔에 외부 음식을 가져가도 돼?",
        guide_types=[
            "stadium_food_guide",
            "stadium_entry_guide",
            "stadium_accessibility_guide",
        ],
    )

    assert tool_input.guide_types == [
        "stadium_food_guide",
        "stadium_entry_guide",
        "stadium_accessibility_guide",
    ]
