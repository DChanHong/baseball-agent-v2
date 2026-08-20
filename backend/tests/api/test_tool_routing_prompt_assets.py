from __future__ import annotations

from typing import get_args

from app.agent.prompts import (
    build_tool_routing_system_prompt,
    load_tool_routing_few_shot_examples,
    load_tool_routing_policy_prompt,
)
from app.agent.routing_schemas import (
    DirectAnswerIntent,
    ToolRoutingDecision,
    ToolRoutingRequest,
)


def test_tool_routing_policy_prompt_documents_direct_answers() -> None:
    policy_prompt = load_tool_routing_policy_prompt()

    assert "direct_answer_intent" in policy_prompt
    assert "conversation_context" in policy_prompt


def test_tool_routing_few_shots_validate_against_routing_schema() -> None:
    examples = load_tool_routing_few_shot_examples()

    assert examples
    assert all(isinstance(example.request, ToolRoutingRequest) for example in examples)
    assert all(isinstance(example.decision, ToolRoutingDecision) for example in examples)


def test_tool_routing_few_shots_cover_direct_answer_intents() -> None:
    examples = load_tool_routing_few_shot_examples()

    direct_answer_intents = {
        example.decision.direct_answer_intent
        for example in examples
        if example.decision.direct_answer_intent is not None
    }

    assert direct_answer_intents == set(get_args(DirectAnswerIntent))


def test_tool_routing_system_prompt_includes_tool_cards_and_examples() -> None:
    system_prompt = build_tool_routing_system_prompt()

    assert "도구명: find_kbo_game" in system_prompt
    assert "도구명: search_stadium_guide" in system_prompt
    assert '"direct_answer_intent":"selected_game_place"' in system_prompt
    assert '"tool_name":"get_weather_context"' in system_prompt
