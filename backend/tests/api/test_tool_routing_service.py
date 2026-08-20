from __future__ import annotations

from datetime import date

import pytest

from app.agent.routing_schemas import ToolRoutingDecision, ToolRoutingUserContext
from app.agent.routing_service import ToolRoutingService


class FakeRoutingChain:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.inputs: list[dict[str, str]] = []

    async def ainvoke(self, chain_input: dict[str, str]) -> dict[str, object]:
        self.inputs.append(chain_input)
        return self.response


@pytest.mark.asyncio
async def test_tool_routing_service_uses_langchain_structured_chain() -> None:
    chain = FakeRoutingChain(
        {
            "is_in_scope": True,
            "should_call_tool": False,
            "tool_name": None,
            "args": None,
            "needs_clarification": True,
            "clarification_reason": "team_required_for_schedule_lookup",
            "unsupported_reason": None,
        }
    )
    service = ToolRoutingService(chain=chain, model="test-model")

    decision = await service.execute(
        message="오늘 경기 있어?",
        user_context=ToolRoutingUserContext(
            auth_status="authenticated",
            favorite_team_id=None,
            today=date(2026, 8, 14),
            timezone="Asia/Seoul",
        ),
    )

    assert isinstance(decision, ToolRoutingDecision)
    assert decision.needs_clarification is True
    assert chain.inputs[0]["request"]
