from __future__ import annotations

from datetime import date

import pytest

from app.domains.baseball.tool.rag_config import RagRetrievalConfig
from app.domains.baseball.tool.search_baseball_knowledge.handler import (
    SearchBaseballKnowledgeToolHandler,
)
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    BaseballKnowledgeSearchItem,
    SearchBaseballKnowledgeToolInput,
)
from app.domains.baseball.tool.search_stadium_guide.handler import (
    SearchStadiumGuideToolHandler,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
    StadiumGuideSearchItem,
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


class FakeStadiumRetriever:
    def __init__(self) -> None:
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
        return [_stadium_item()]


class FakeBaseballKnowledgeRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(
        self,
        *,
        query_embedding,
        document_types,
        knowledge_types=None,
        top_k=5,
        relevance_threshold=0.82,
    ):
        self.calls.append(
            {
                "query_embedding": query_embedding,
                "document_types": document_types,
                "knowledge_types": knowledge_types,
                "top_k": top_k,
                "relevance_threshold": relevance_threshold,
            }
        )
        return [_baseball_knowledge_item()]


def _stadium_item() -> StadiumGuideSearchItem:
    return StadiumGuideSearchItem(
        chunk_id="chunk_1",
        document_id="doc_1",
        document_type="stadium_transport_guide",
        stadium_id="SAJIK",
        team_id="LOTTE",
        title="사직 교통 안내",
        content="사직야구장은 지하철과 버스로 방문할 수 있습니다.",
        similarity=0.9,
        distance=0.1,
        source_urls=["https://example.com/stadium"],
        as_of=date(2026, 7, 29),
        trust_level="official",
        review_status="approved",
        metadata={},
    )


def _baseball_knowledge_item() -> BaseballKnowledgeSearchItem:
    return BaseballKnowledgeSearchItem(
        chunk_id="chunk_1",
        document_id="doc_1",
        document_type="baseball_rule",
        title="야구 기본 규칙",
        content="야구는 득점이 많은 팀이 승리합니다.",
        similarity=0.9,
        distance=0.1,
        source_urls=["https://example.com/rule"],
        as_of=date(2026, 7, 29),
        trust_level="official",
        review_status="approved",
        metadata={},
    )


@pytest.mark.asyncio
async def test_search_stadium_guide_uses_retrieval_config():
    openai_client = FakeOpenAIClient()
    retriever = FakeStadiumRetriever()
    handler = SearchStadiumGuideToolHandler(
        openai_client=openai_client,
        retriever=retriever,
        retrieval_config=RagRetrievalConfig(
            embedding_model="test-stadium-embedding",
            default_top_k=2,
            max_top_k=4,
            relevance_threshold=0.41,
            document_types=("stadium_transport_guide",),
        ),
    )

    await handler.execute(
        SearchStadiumGuideToolInput(
            stadium_id="SAJIK",
            team_id="LOTTE",
            query="사직 주차 알려줘",
            guide_types=["stadium_transport_guide"],
            top_k=8,
        )
    )

    assert openai_client.embeddings.calls[0]["model"] == "test-stadium-embedding"
    assert retriever.calls[0]["document_types"] == ("stadium_transport_guide",)
    assert retriever.calls[0]["guide_types"] == ["stadium_transport_guide"]
    assert retriever.calls[0]["top_k"] == 4
    assert retriever.calls[0]["relevance_threshold"] == 0.41


@pytest.mark.asyncio
async def test_search_baseball_knowledge_uses_retrieval_config():
    openai_client = FakeOpenAIClient()
    retriever = FakeBaseballKnowledgeRetriever()
    handler = SearchBaseballKnowledgeToolHandler(
        openai_client=openai_client,
        retriever=retriever,
        retrieval_config=RagRetrievalConfig(
            embedding_model="test-knowledge-embedding",
            default_top_k=2,
            max_top_k=3,
            relevance_threshold=0.77,
            document_types=("baseball_rule",),
        ),
    )

    await handler.execute(
        SearchBaseballKnowledgeToolInput(
            query="야구는 어떻게 이겨?",
            knowledge_types=["baseball_rule"],
            top_k=9,
        )
    )

    assert openai_client.embeddings.calls[0]["model"] == "test-knowledge-embedding"
    assert retriever.calls[0]["document_types"] == ("baseball_rule",)
    assert retriever.calls[0]["knowledge_types"] == ["baseball_rule"]
    assert retriever.calls[0]["top_k"] == 3
    assert retriever.calls[0]["relevance_threshold"] == 0.77
