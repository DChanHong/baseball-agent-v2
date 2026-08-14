from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agent.answering import (
    build_assistant_content,
    build_selected_game_place_answer,
    can_answer_selected_game_place,
    promote_context_from_tool_payload,
)
from app.agent.routing_schemas import ToolRoutingDecision, ToolRoutingUserContext
from app.agent.routing_service import ToolRoutingService
from app.agent.state import (
    BaseballAgentInput,
    BaseballAgentOutput,
    BaseballAgentState,
)
from app.agent.tool_executor import AgentToolExecutor

logger = logging.getLogger(__name__)

AgentGraphEventKind = Literal[
    "tool.started",
    "tool.completed",
    "tool.failed",
    "completed",
]


class AgentGraphEvent(BaseModel):
    """Domain event emitted by the graph and adapted to SSE by chat service."""

    kind: AgentGraphEventKind
    output: BaseballAgentOutput | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_payload: dict[str, Any] | None = None


class BaseballAgentGraph:
    """LangGraph workflow for one KBO assistant turn."""

    def __init__(
        self,
        *,
        tool_routing_service: ToolRoutingService,
        tool_executor: AgentToolExecutor,
    ) -> None:
        self._tool_routing_service = tool_routing_service
        self._tool_executor = tool_executor
        self._graph = self._compile_graph()

    async def astream(
        self,
        graph_input: BaseballAgentInput,
    ) -> AsyncIterator[AgentGraphEvent]:
        initial_state: BaseballAgentState = {
            "conversation_id": graph_input.conversation_id,
            "user_profile_id": graph_input.user_profile_id,
            "user_message": graph_input.user_message,
            "today": graph_input.today,
            "timezone": graph_input.timezone,
            "favorite_team_id": graph_input.favorite_team_id,
            "context": graph_input.context,
        }

        async for update in self._graph.astream(initial_state, stream_mode="updates"):
            if "prepare_tool" in update:
                state_update = update["prepare_tool"]
                yield AgentGraphEvent(
                    kind="tool.started",
                    tool_call_id=state_update["tool_call_id"],
                    tool_name=state_update["routing_decision"].tool_name,
                    tool_input=state_update["tool_input"],
                )
            elif "tool_execute" in update:
                state_update = update["tool_execute"]
                tool_payload = state_update.get("tool_payload")
                if isinstance(tool_payload, dict) and tool_payload.get("status") == "failed":
                    yield AgentGraphEvent(
                        kind="tool.failed",
                        tool_call_id=tool_payload.get("tool_call_id"),
                        tool_name=tool_payload.get("name"),
                        tool_input=tool_payload.get("input"),
                        tool_payload=tool_payload,
                    )
                elif isinstance(tool_payload, dict):
                    yield AgentGraphEvent(
                        kind="tool.completed",
                        tool_call_id=tool_payload.get("tool_call_id"),
                        tool_name=tool_payload.get("name"),
                        tool_input=tool_payload.get("input"),
                        tool_payload=tool_payload,
                    )
            elif "answer_generate" in update:
                state_update = update["answer_generate"]
                yield AgentGraphEvent(
                    kind="completed",
                    output=BaseballAgentOutput(
                        routing_decision=state_update["routing_decision"],
                        tool_payload=state_update.get("tool_payload"),
                        tool_limitations=state_update.get("tool_limitations", []),
                        context=state_update["context"],
                        answer=state_update["answer"],
                    ),
                )

    def _compile_graph(self):
        graph = StateGraph(BaseballAgentState)
        graph.add_node("route", self._route)
        graph.add_node("prepare_tool", self._prepare_tool)
        graph.add_node("tool_execute", self._tool_execute)
        graph.add_node("state_update", self._state_update)
        graph.add_node("answer_generate", self._answer_generate)

        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route",
            _next_after_route,
            {
                "prepare_tool": "prepare_tool",
                "answer_generate": "answer_generate",
            },
        )
        graph.add_edge("prepare_tool", "tool_execute")
        graph.add_edge("tool_execute", "state_update")
        graph.add_edge("state_update", "answer_generate")
        graph.add_edge("answer_generate", END)
        return graph.compile()

    async def _route(self, state: BaseballAgentState) -> dict[str, Any]:
        context = state["context"]
        if can_answer_selected_game_place(
            message=state["user_message"],
            context=context,
        ):
            return {
                "routing_decision": _direct_answer_decision(),
                "answer_mode": "contextual_direct",
            }

        decision = await self._tool_routing_service.execute(
            message=state["user_message"],
            user_context=ToolRoutingUserContext(
                auth_status="authenticated",
                favorite_team_id=state["favorite_team_id"],
                today=state["today"],
                timezone=state["timezone"],
                conversation_context=context.to_routing_context(),
            ),
        )
        return {"routing_decision": decision, "answer_mode": "routed"}

    async def _prepare_tool(self, state: BaseballAgentState) -> dict[str, Any]:
        decision = state["routing_decision"]
        return {
            "routing_decision": decision,
            "tool_call_id": f"tool_{uuid4().hex[:12]}",
            "tool_input": _tool_input_payload(decision),
        }

    async def _tool_execute(self, state: BaseballAgentState) -> dict[str, Any]:
        decision = state["routing_decision"]
        tool_call_id = state["tool_call_id"]
        tool_input = state["tool_input"]

        try:
            result = await self._tool_executor.execute(decision)
        except Exception as exc:
            logger.exception("tool execution failed tool_name=%s", decision.tool_name)
            return {
                "tool_payload": {
                    "tool_call_id": tool_call_id,
                    "name": decision.tool_name,
                    "status": "failed",
                    "input": tool_input,
                    "result": None,
                    "error": {"code": "tool_execution_failed", "message": str(exc)},
                },
                "tool_limitations": [],
            }

        result_payload = _model_payload(result)
        return {
            "tool_payload": {
                "tool_call_id": tool_call_id,
                "name": decision.tool_name,
                "status": "completed",
                "input": tool_input,
                "result": result_payload,
                "error": None,
            },
            "tool_limitations": _extract_limitations(result_payload),
        }

    async def _state_update(self, state: BaseballAgentState) -> dict[str, Any]:
        return {
            "context": promote_context_from_tool_payload(
                context=state["context"],
                tool_payload=state.get("tool_payload"),
            )
        }

    async def _answer_generate(self, state: BaseballAgentState) -> dict[str, Any]:
        context = state["context"]
        if state.get("answer_mode") == "contextual_direct" and context.selected_game:
            answer = build_selected_game_place_answer(context.selected_game)
        else:
            answer = build_assistant_content(
                message=state["user_message"],
                decision=state["routing_decision"],
                tool_payload=state.get("tool_payload"),
            )

        return {
            "routing_decision": state["routing_decision"],
            "tool_payload": state.get("tool_payload"),
            "tool_limitations": state.get("tool_limitations", []),
            "context": context,
            "answer": answer,
        }


def _next_after_route(state: BaseballAgentState) -> str:
    decision = state["routing_decision"]
    if decision.should_call_tool and decision.tool_name is not None:
        return "prepare_tool"
    return "answer_generate"


def _direct_answer_decision() -> ToolRoutingDecision:
    return ToolRoutingDecision(
        is_in_scope=True,
        should_call_tool=False,
        tool_name=None,
        args=None,
        needs_clarification=False,
        clarification_reason=None,
        unsupported_reason=None,
    )


def _tool_input_payload(decision: ToolRoutingDecision) -> dict[str, Any]:
    if decision.args is None:
        return {}
    return decision.args.model_dump(mode="json")


def _model_payload(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _extract_limitations(payload: dict[str, Any]) -> list[str]:
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        return []
    return [item for item in limitations if isinstance(item, str)]
