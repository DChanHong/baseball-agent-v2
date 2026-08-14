from __future__ import annotations

from datetime import date as Date
from datetime import time as Time
from typing import Any, Literal, TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.agent.routing_schemas import (
    ToolRoutingConversationContext,
    ToolRoutingDecision,
)


class SelectedGameContext(BaseModel):
    """A compact game context promoted from tool results for follow-up turns."""

    model_config = ConfigDict(extra="forbid")

    game_id: UUID
    game_date: Date
    start_time: Time | None
    away_team_id: str
    home_team_id: str
    away_team_name: str
    home_team_name: str
    stadium_id: str
    stadium_name: str
    game_status: str


class AgentConversationContext(BaseModel):
    """Working memory persisted separately from chat message history."""

    model_config = ConfigDict(extra="forbid")

    selected_game: SelectedGameContext | None = None
    selected_stadium_id: str | None = None
    selected_stadium_name: str | None = None
    selected_team_id: str | None = None
    last_tool_name: str | None = None

    def to_routing_context(self) -> ToolRoutingConversationContext:
        selected_game = None
        if self.selected_game is not None:
            selected_game = self.selected_game.model_dump(
                mode="python",
                exclude={"game_id"},
            )

        return ToolRoutingConversationContext.model_validate(
            {
                "selected_game": selected_game,
                "selected_stadium_id": self.selected_stadium_id,
                "selected_stadium_name": self.selected_stadium_name,
                "selected_team_id": self.selected_team_id,
                "last_tool_name": self.last_tool_name,
            }
        )


class BaseballAgentInput(BaseModel):
    """Input for one graph turn."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    user_profile_id: UUID
    user_message: str
    today: Date
    timezone: str
    favorite_team_id: str | None
    context: AgentConversationContext


class BaseballAgentOutput(BaseModel):
    """Final graph result consumed by the chat stream service."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    routing_decision: ToolRoutingDecision
    tool_payload: dict[str, Any] | None
    tool_limitations: list[str]
    context: AgentConversationContext
    answer: str


class BaseballAgentState(TypedDict, total=False):
    """LangGraph state channels for one chat turn."""

    conversation_id: UUID
    user_profile_id: UUID
    user_message: str
    today: Date
    timezone: str
    favorite_team_id: str | None
    context: AgentConversationContext
    routing_decision: ToolRoutingDecision
    tool_call_id: str
    tool_input: dict[str, Any]
    tool_payload: dict[str, Any] | None
    tool_limitations: list[str]
    answer: str
    answer_mode: Literal["contextual_direct", "routed"]
