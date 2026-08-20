from __future__ import annotations

from datetime import date

import pytest
from pydantic import BaseModel

from app.agent.routing_schemas import FindKboGameRoutingArgs, ToolRoutingDecision
from app.agent.tool_executor import AgentToolExecutor
from app.agent.tool_registry import AGENT_TOOL_SPECS, get_routing_tool_cards
from app.domains.baseball.tool.find_kbo_game.schemas import FindKboGameToolInput

EXPECTED_TOOL_NAMES = {
    "find_kbo_game",
    "get_stadium_info",
    "search_stadium_guide",
    "search_ticketing_guide",
    "search_baseball_knowledge",
    "get_weather_context",
}


class FakeToolResult(BaseModel):
    ok: bool = True


class RecordingHandler:
    def __init__(self) -> None:
        self.inputs: list[BaseModel] = []

    async def execute(self, tool_input: BaseModel) -> FakeToolResult:
        self.inputs.append(tool_input)
        return FakeToolResult()


def _executor_with_handlers(
    handlers: dict[str, RecordingHandler],
) -> AgentToolExecutor:
    return AgentToolExecutor(
        find_kbo_game_handler=handlers.get(
            "find_kbo_game",
            RecordingHandler(),
        ),
        get_stadium_info_handler=handlers.get(
            "get_stadium_info",
            RecordingHandler(),
        ),
        search_stadium_guide_handler=handlers.get(
            "search_stadium_guide",
            RecordingHandler(),
        ),
        search_ticketing_guide_handler=handlers.get(
            "search_ticketing_guide",
            RecordingHandler(),
        ),
        search_baseball_knowledge_handler=handlers.get(
            "search_baseball_knowledge",
            RecordingHandler(),
        ),
        get_weather_context_handler=handlers.get(
            "get_weather_context",
            RecordingHandler(),
        ),
    )


def test_agent_tool_registry_covers_enabled_tools() -> None:
    assert set(AGENT_TOOL_SPECS) == EXPECTED_TOOL_NAMES
    assert [spec.name for spec in AGENT_TOOL_SPECS.values()] == list(AGENT_TOOL_SPECS)
    assert len(get_routing_tool_cards()) == len(EXPECTED_TOOL_NAMES)

    for tool_name, spec in AGENT_TOOL_SPECS.items():
        assert tool_name in spec.routing_card
        assert spec.display_label
        assert issubclass(spec.routing_args_type, BaseModel)
        assert issubclass(spec.tool_input_type, BaseModel)


@pytest.mark.asyncio
async def test_agent_tool_executor_uses_registry_spec_for_handler_and_input_type() -> None:
    find_kbo_game_handler = RecordingHandler()
    executor = _executor_with_handlers({"find_kbo_game": find_kbo_game_handler})

    result = await executor.execute(
        ToolRoutingDecision(
            is_in_scope=True,
            should_call_tool=True,
            tool_name="find_kbo_game",
            args=FindKboGameRoutingArgs(
                team_id="LOTTE",
                date=date(2026, 8, 14),
                date_from=None,
                date_to=None,
            ),
            needs_clarification=False,
            clarification_reason=None,
            unsupported_reason=None,
            direct_answer_intent=None,
        )
    )

    assert result.ok is True
    assert len(find_kbo_game_handler.inputs) == 1
    assert isinstance(find_kbo_game_handler.inputs[0], FindKboGameToolInput)
    assert find_kbo_game_handler.inputs[0].team_id == "LOTTE"
