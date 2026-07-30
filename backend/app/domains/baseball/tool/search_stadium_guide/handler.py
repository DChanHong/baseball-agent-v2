import logging

from openai import AsyncOpenAI

from app.domains.baseball.tool.search_stadium_guide.retriever import (
    DEFAULT_RELEVANCE_THRESHOLD,
    PgVectorStadiumGuideRetriever,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
    SearchStadiumGuideToolResult,
)

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class SearchStadiumGuideToolHandler:
    """LLM의 search_stadium_guide tool 호출을 처리합니다."""

    def __init__(
        self,
        *,
        openai_client: AsyncOpenAI,
        retriever: PgVectorStadiumGuideRetriever,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> None:
        self._openai_client = openai_client
        self._retriever = retriever
        self._embedding_model = embedding_model
        self._relevance_threshold = relevance_threshold

    async def execute(
        self,
        tool_input: SearchStadiumGuideToolInput,
    ) -> SearchStadiumGuideToolResult:
        """사용자 질문을 embedding한 뒤 구장 안내 RAG chunk를 검색합니다."""

        logger.info(
            "search_stadium_guide tool started stadium_id=%s team_id=%s guide_types=%s top_k=%d",
            tool_input.stadium_id,
            tool_input.team_id,
            tool_input.guide_types,
            tool_input.top_k,
        )

        try:
            query_embedding = await self._embed_query(tool_input.query)
            items = await self._retriever.search(
                query_embedding=query_embedding,
                stadium_id=tool_input.stadium_id,
                guide_types=tool_input.guide_types,
                top_k=tool_input.top_k,
                relevance_threshold=self._relevance_threshold,
            )
        except Exception:
            logger.exception("search_stadium_guide tool failed")
            raise

        limitations = []
        if not items:
            limitations.append("no_relevant_stadium_guide_found")

        logger.info(
            "search_stadium_guide tool completed stadium_id=%s count=%d answerable=%s",
            tool_input.stadium_id,
            len(items),
            bool(items),
        )

        return SearchStadiumGuideToolResult(
            stadium_id=tool_input.stadium_id,
            team_id=tool_input.team_id,
            query=tool_input.query,
            answerable=bool(items),
            items=items,
            limitations=limitations,
        )

    async def _embed_query(self, query: str) -> list[float]:
        response = await self._openai_client.embeddings.create(
            model=self._embedding_model,
            input=query,
        )
        return response.data[0].embedding
