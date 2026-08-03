from __future__ import annotations

from pydantic import BaseModel

from app.agent.routing_schemas import (
    FindKboGameRoutingArgs,
    GetStadiumInfoRoutingArgs,
    GetWeatherContextRoutingArgs,
    SearchBaseballKnowledgeRoutingArgs,
    SearchStadiumGuideRoutingArgs,
    SearchTicketingGuideRoutingArgs,
    ToolRoutingDecision,
)
from app.domains.baseball.tool.find_kbo_game.handler import FindKboGameToolHandler
from app.domains.baseball.tool.find_kbo_game.schemas import FindKboGameToolInput
from app.domains.baseball.tool.get_stadium_info.handler import GetStadiumInfoToolHandler
from app.domains.baseball.tool.get_stadium_info.schemas import GetStadiumInfoToolInput
from app.domains.baseball.tool.get_weather_context.handler import (
    GetWeatherContextToolHandler,
)
from app.domains.baseball.tool.get_weather_context.schemas import (
    GetWeatherContextToolInput,
)
from app.domains.baseball.tool.search_baseball_knowledge.handler import (
    SearchBaseballKnowledgeToolHandler,
)
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    SearchBaseballKnowledgeToolInput,
)
from app.domains.baseball.tool.search_stadium_guide.handler import (
    SearchStadiumGuideToolHandler,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
)
from app.domains.baseball.tool.search_ticketing_guide.handler import (
    SearchTicketingGuideToolHandler,
)
from app.domains.baseball.tool.search_ticketing_guide.schemas import (
    SearchTicketingGuideToolInput,
)


class AgentToolExecutor:
    """Routing decision을 실제 backend tool handler 호출로 변환합니다."""

    def __init__(
        self,
        *,
        find_kbo_game_handler: FindKboGameToolHandler,
        get_stadium_info_handler: GetStadiumInfoToolHandler,
        search_stadium_guide_handler: SearchStadiumGuideToolHandler,
        search_ticketing_guide_handler: SearchTicketingGuideToolHandler,
        search_baseball_knowledge_handler: SearchBaseballKnowledgeToolHandler,
        get_weather_context_handler: GetWeatherContextToolHandler,
    ) -> None:
        self._find_kbo_game_handler = find_kbo_game_handler
        self._get_stadium_info_handler = get_stadium_info_handler
        self._search_stadium_guide_handler = search_stadium_guide_handler
        self._search_ticketing_guide_handler = search_ticketing_guide_handler
        self._search_baseball_knowledge_handler = search_baseball_knowledge_handler
        self._get_weather_context_handler = get_weather_context_handler

    async def execute(self, decision: ToolRoutingDecision) -> BaseModel:
        """선택된 Tool을 실행하고 해당 Tool의 Pydantic 결과 모델을 반환합니다."""

        if not decision.should_call_tool or decision.tool_name is None:
            raise ValueError("Tool execution requires should_call_tool=true")

        if decision.tool_name == "find_kbo_game":
            if not isinstance(decision.args, FindKboGameRoutingArgs):
                raise ValueError("find_kbo_game requires FindKboGameRoutingArgs")

            return await self._find_kbo_game_handler.execute(
                FindKboGameToolInput.model_validate(
                    decision.args.model_dump(mode="json")
                )
            )

        if decision.tool_name == "get_stadium_info":
            if not isinstance(decision.args, GetStadiumInfoRoutingArgs):
                raise ValueError("get_stadium_info requires GetStadiumInfoRoutingArgs")

            return await self._get_stadium_info_handler.execute(
                GetStadiumInfoToolInput.model_validate(
                    decision.args.model_dump(mode="json")
                )
            )

        if decision.tool_name == "search_stadium_guide":
            if not isinstance(decision.args, SearchStadiumGuideRoutingArgs):
                raise ValueError(
                    "search_stadium_guide requires SearchStadiumGuideRoutingArgs"
                )

            return await self._search_stadium_guide_handler.execute(
                SearchStadiumGuideToolInput.model_validate(
                    decision.args.model_dump(mode="json")
                )
            )

        if decision.tool_name == "search_baseball_knowledge":
            if not isinstance(decision.args, SearchBaseballKnowledgeRoutingArgs):
                raise ValueError(
                    "search_baseball_knowledge requires "
                    "SearchBaseballKnowledgeRoutingArgs"
                )

            return await self._search_baseball_knowledge_handler.execute(
                SearchBaseballKnowledgeToolInput.model_validate(
                    decision.args.model_dump(mode="json")
                )
            )

        if decision.tool_name == "search_ticketing_guide":
            if not isinstance(decision.args, SearchTicketingGuideRoutingArgs):
                raise ValueError(
                    "search_ticketing_guide requires SearchTicketingGuideRoutingArgs"
                )

            return await self._search_ticketing_guide_handler.execute(
                SearchTicketingGuideToolInput.model_validate(
                    decision.args.model_dump(mode="json")
                )
            )

        if decision.tool_name == "get_weather_context":
            if not isinstance(decision.args, GetWeatherContextRoutingArgs):
                raise ValueError(
                    "get_weather_context requires GetWeatherContextRoutingArgs"
                )

            return await self._get_weather_context_handler.execute(
                GetWeatherContextToolInput.model_validate(
                    decision.args.model_dump(mode="json")
                )
            )

        raise ValueError(f"Unsupported tool_name: {decision.tool_name}")
