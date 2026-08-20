from __future__ import annotations

from pydantic import BaseModel

from app.agent.routing_schemas import ToolRoutingDecision
from app.agent.tool_registry import get_agent_tool_spec
from app.domains.baseball.tool.find_kbo_game.handler import FindKboGameToolHandler
from app.domains.baseball.tool.get_stadium_info.handler import GetStadiumInfoToolHandler
from app.domains.baseball.tool.get_weather_context.handler import (
    GetWeatherContextToolHandler,
)
from app.domains.baseball.tool.search_baseball_knowledge.handler import (
    SearchBaseballKnowledgeToolHandler,
)
from app.domains.baseball.tool.search_stadium_guide.handler import (
    SearchStadiumGuideToolHandler,
)
from app.domains.baseball.tool.search_ticketing_guide.handler import (
    SearchTicketingGuideToolHandler,
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

        spec = get_agent_tool_spec(decision.tool_name)
        if spec is None:
            raise ValueError(f"Unsupported tool_name: {decision.tool_name}")

        if not isinstance(decision.args, spec.routing_args_type):
            raise TypeError(
                f"{decision.tool_name} requires {spec.routing_args_type.__name__}"
            )

        handler = getattr(self, spec.executor_handler_attr)
        tool_input = spec.tool_input_type.model_validate(
            decision.args.model_dump(mode="json")
        )
        return await handler.execute(tool_input)
