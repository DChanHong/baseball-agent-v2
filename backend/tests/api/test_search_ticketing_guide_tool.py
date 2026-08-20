from __future__ import annotations

from datetime import date

import pytest

from app.domains.baseball.tool.rag_config import RagRetrievalConfig
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
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def create(self, *, model: str, input: str):
        self.calls.append({"model": model, "input": input})
        return FakeEmbeddingResponse()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddings()


class FakeRetriever:
    def __init__(self, items: list[StadiumGuideSearchItem]) -> None:
        self.items = items
        self.calls: list[dict[str, object]] = []

    async def search(
        self,
        *,
        query_embedding,
        stadium_id,
        document_types,
        guide_types=None,
        top_k=5,
        relevance_threshold=0.65,
    ):
        self.calls.append(
            {
                "query_embedding": query_embedding,
                "stadium_id": stadium_id,
                "document_types": document_types,
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
    openai_client = FakeOpenAIClient()
    handler = SearchTicketingGuideToolHandler(
        openai_client=openai_client,
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
    assert retriever.calls[0]["document_types"] == ("stadium_ticketing_guide",)
    assert retriever.calls[0]["guide_types"] == ["stadium_ticketing_guide"]
    assert retriever.calls[0]["top_k"] == 3
    assert retriever.calls[0]["relevance_threshold"] == 0.65
    assert openai_client.embeddings.calls[0]["model"] == "text-embedding-3-small"
    assert "ticket_inventory_not_supported" in result.limitations
    assert "official_ticketing_source_should_be_checked" in result.limitations


@pytest.mark.asyncio
async def test_search_ticketing_guide_uses_injected_retrieval_config():
    retriever = FakeRetriever(items=[ticketing_item()])
    openai_client = FakeOpenAIClient()
    handler = SearchTicketingGuideToolHandler(
        openai_client=openai_client,
        retriever=retriever,
        retrieval_config=RagRetrievalConfig(
            embedding_model="test-embedding-model",
            default_top_k=2,
            max_top_k=4,
            relevance_threshold=0.42,
            document_types=("custom_ticketing_type",),
        ),
    )

    await handler.execute(
        SearchTicketingGuideToolInput(
            stadium_id="SAJIK",
            team_id=None,
            query="사직 예매 어디서 해?",
            top_k=9,
        )
    )

    assert openai_client.embeddings.calls[0]["model"] == "test-embedding-model"
    assert retriever.calls[0]["document_types"] == ("custom_ticketing_type",)
    assert retriever.calls[0]["guide_types"] == ["custom_ticketing_type"]
    assert retriever.calls[0]["top_k"] == 4
    assert retriever.calls[0]["relevance_threshold"] == 0.42


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
