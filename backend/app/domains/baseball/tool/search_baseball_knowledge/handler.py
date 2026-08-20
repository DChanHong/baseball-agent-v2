import logging

from openai import AsyncOpenAI

from app.domains.baseball.tool.rag_config import (
    BASEBALL_KNOWLEDGE_RAG_CONFIG,
    RagRetrievalConfig,
)
from app.domains.baseball.tool.search_baseball_knowledge.retriever import (
    PgVectorBaseballKnowledgeRetriever,
)
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    SearchBaseballKnowledgeToolInput,
    SearchBaseballKnowledgeToolResult,
)

logger = logging.getLogger(__name__)

WEATHER_CANCELLATION_TOPIC_IDS = {
    "basic_rule_regular_game",
    "basic_rule_suspended_game",
    "latest_rule_weather_cancel",
    "latest_rule_no_game_suspended",
    "latest_rule_game_authority",
}


class SearchBaseballKnowledgeToolHandler:
    """LLM의 search_baseball_knowledge tool 호출을 처리합니다."""

    def __init__(
        self,
        *,
        openai_client: AsyncOpenAI,
        retriever: PgVectorBaseballKnowledgeRetriever,
        retrieval_config: RagRetrievalConfig = BASEBALL_KNOWLEDGE_RAG_CONFIG,
    ) -> None:
        self._openai_client = openai_client
        self._retriever = retriever
        self._retrieval_config = retrieval_config

    async def execute(
        self,
        tool_input: SearchBaseballKnowledgeToolInput,
    ) -> SearchBaseballKnowledgeToolResult:
        """사용자 질문을 embedding한 뒤 야구 지식 RAG chunk를 검색합니다."""

        logger.info(
            "search_baseball_knowledge tool started knowledge_types=%s top_k=%d",
            tool_input.knowledge_types,
            tool_input.top_k,
        )

        try:
            query_embedding = await self._embed_query(tool_input.query)
            items = await self._retriever.search(
                query_embedding=query_embedding,
                document_types=self._retrieval_config.document_types,
                knowledge_types=tool_input.knowledge_types,
                top_k=self._retrieval_config.effective_top_k(tool_input.top_k),
                relevance_threshold=self._retrieval_config.relevance_threshold,
            )
        except Exception:
            logger.exception("search_baseball_knowledge tool failed")
            raise

        limitations = []
        if not items:
            limitations.append("no_relevant_baseball_knowledge_found")
        if any(
            item.metadata.get("topic_id") in WEATHER_CANCELLATION_TOPIC_IDS
            for item in items
        ):
            limitations.append("not_official_game_cancellation_decision")

        logger.info(
            "search_baseball_knowledge tool completed count=%d answerable=%s",
            len(items),
            bool(items),
        )

        return SearchBaseballKnowledgeToolResult(
            query=tool_input.query,
            answerable=bool(items),
            items=items,
            limitations=limitations,
        )

    async def _embed_query(self, query: str) -> list[float]:
        response = await self._openai_client.embeddings.create(
            model=self._retrieval_config.embedding_model,
            input=query,
        )
        return response.data[0].embedding
