from __future__ import annotations

from datetime import date

import pytest
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    StadiumGuideSearchItem,
)
from app.domains.baseball.tool.search_ticketing_guide.handler import (
    SearchTicketingGuideToolHandler,
)
from app.domains.baseball.tool.search_ticketing_guide.schemas import (
    SearchTicketingGuideToolInput,
)


class FakeEmbeddingResponse:
    def __init__(self) -> None:
        self.data = [type("EmbeddingData", (), {"embedding": [0.1, 0.2, 0.3]})()]


class FakeEmbeddings:
    async def create(self, *, model: str, input: str):
        return FakeEmbeddingResponse()


class FakeOpenAIClient:
    embeddings = FakeEmbeddings()


class FakeRetriever:
    def __init__(self, items: list[StadiumGuideSearchItem]) -> None:
        self.items = items
        self.calls: list[dict[str, object]] = []

    async def search(
        self,
        *,
        query_embedding,
        stadium_id,
        guide_types=None,
        top_k=5,
        relevance_threshold=0.65,
    ):
        self.calls.append(
            {
                "query_embedding": query_embedding,
                "stadium_id": stadium_id,
                "guide_types": guide_types,
                "top_k": top_k,
                "relevance_threshold": relevance_threshold,
            }
        )
        return self.items


def ticketing_item() -> StadiumGuideSearchItem:
    return StadiumGuideSearchItem(
        chunk_id="chunk_1",
        document_id="doc_1",
        document_type="stadium_ticketing_guide",
        stadium_id="SAJIK",
        team_id="LOTTE",
        title="사직 예매 안내",
        content="롯데 자이언츠 홈경기 예매는 공식 예매처에서 진행합니다.",
        similarity=0.9,
        distance=0.1,
        source_urls=["https://example.com/ticketing"],
        as_of=date(2026, 7, 29),
        trust_level="official",
        review_status="approved",
        metadata={},
    )


@pytest.mark.asyncio
async def test_search_ticketing_guide_filters_ticketing_document_type():
    retriever = FakeRetriever(items=[ticketing_item()])
    handler = SearchTicketingGuideToolHandler(
        openai_client=FakeOpenAIClient(),
        retriever=retriever,
    )

    result = await handler.execute(
        SearchTicketingGuideToolInput(
            stadium_id="sajik",
            team_id="lotte",
            query="사직 예매 어디서 해?",
            top_k=3,
        )
    )

    assert result.answerable is True
    assert result.stadium_id == "SAJIK"
    assert result.team_id == "LOTTE"
    assert result.items[0].document_type == "stadium_ticketing_guide"
    assert retriever.calls[0]["guide_types"] == ["stadium_ticketing_guide"]
    assert retriever.calls[0]["top_k"] == 3
    assert "ticket_inventory_not_supported" in result.limitations
    assert "official_ticketing_source_should_be_checked" in result.limitations


@pytest.mark.asyncio
async def test_search_ticketing_guide_returns_no_result_limitation():
    retriever = FakeRetriever(items=[])
    handler = SearchTicketingGuideToolHandler(
        openai_client=FakeOpenAIClient(),
        retriever=retriever,
    )

    result = await handler.execute(
        SearchTicketingGuideToolInput(
            stadium_id="SAJIK",
            team_id=None,
            query="사직 티켓 취소 가능해?",
        )
    )

    assert result.answerable is False
    assert result.items == []
    assert "no_relevant_ticketing_guide_found" in result.limitations
