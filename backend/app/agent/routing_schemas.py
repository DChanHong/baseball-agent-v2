from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

KboTeamId = Literal[
    "LG",
    "DOOSAN",
    "KIWOOM",
    "SSG",
    "KIA",
    "SAMSUNG",
    "LOTTE",
    "NC",
    "HANWHA",
    "KT",
]

KboStadiumId = Literal[
    "SAJIK",
    "GOCHEOK",
    "MUNHAK",
    "GWANGJU",
    "DAEGU",
    "SUWON",
    "DAEJEON",
    "JAMSIL",
    "CHANGWON",
]

StadiumGuideType = Literal[
    "stadium_bag_policy",
    "stadium_facility_guide",
    "stadium_seat_guide",
    "stadium_ticketing_guide",
    "stadium_transport_guide",
]


class ToolRoutingUserContext(BaseModel):
    """User context available to the routing model."""

    model_config = ConfigDict(extra="forbid")

    auth_status: Literal["authenticated"]
    favorite_team_id: KboTeamId | None
    today: Date
    timezone: str = Field(description="IANA timezone name. Example: Asia/Seoul.")


class ToolRoutingRequest(BaseModel):
    """Input for deciding whether a conversation turn needs a tool."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    user_context: ToolRoutingUserContext


class FindKboGameRoutingArgs(BaseModel):
    """Arguments for the find_kbo_game routing decision."""

    model_config = ConfigDict(extra="forbid")

    team_id: KboTeamId | None
    date: Date | None = Field(
        description="Single game date. Mutually exclusive with date_from/date_to."
    )
    date_from: Date | None = Field(description="Start date for a range lookup.")
    date_to: Date | None = Field(description="End date for a range lookup.")

    @model_validator(mode="after")
    def validate_date_shape(self) -> FindKboGameRoutingArgs:
        if self.date is not None and (
            self.date_from is not None or self.date_to is not None
        ):
            raise ValueError("date cannot be used with date_from/date_to")

        if (self.date_from is None) != (self.date_to is None):
            raise ValueError("date_from and date_to must be provided together")

        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from must be before or equal to date_to")

        return self


class SearchStadiumGuideRoutingArgs(BaseModel):
    """Arguments for the search_stadium_guide routing decision."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: KboStadiumId = Field(
        description="KBO home stadium id used as the required metadata filter."
    )
    team_id: KboTeamId | None = Field(
        description="Optional KBO team id when the question includes a team context."
    )
    query: str = Field(
        min_length=1,
        description="Original user question to search against stadium guide chunks.",
    )
    guide_types: list[StadiumGuideType] | None = Field(
        description="Optional document type filters. Null when the question is broad."
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to return.",
    )


class ToolRoutingDecision(BaseModel):
    """Structured decision returned by the LLM before final answer generation."""

    model_config = ConfigDict(extra="forbid")

    is_in_scope: bool = Field(
        description="Whether the user request is within the KBO baseball service scope."
    )
    should_call_tool: bool = Field(
        description="Whether the system should call a backend tool before answering."
    )
    tool_name: Literal["find_kbo_game", "search_stadium_guide"] | None = Field(
        description="Tool to call. Null when should_call_tool is false."
    )
    args: FindKboGameRoutingArgs | SearchStadiumGuideRoutingArgs | None = Field(
        description="Tool arguments. Null when should_call_tool is false."
    )
    needs_clarification: bool = Field(
        description="Whether the assistant should ask a clarification question."
    )
    clarification_reason: (
        Literal[
            "team_required_for_schedule_lookup",
            "stadium_required_for_stadium_guide_search",
        ]
        | None
    )
    unsupported_reason: (
        Literal[
            "out_of_scope",
            "weather_or_realtime_cancellation_prediction_required",
            "ticket_inventory_tool_required",
            "opponent_team_filter_not_supported_yet",
        ]
        | None
    )

    @model_validator(mode="after")
    def validate_decision_shape(self) -> ToolRoutingDecision:
        if self.should_call_tool:
            if self.tool_name not in {"find_kbo_game", "search_stadium_guide"}:
                raise ValueError("tool_name must be a supported tool when calling a tool")
            if self.args is None:
                raise ValueError("args are required when calling a tool")
            if self.tool_name == "find_kbo_game" and not isinstance(
                self.args, FindKboGameRoutingArgs
            ):
                raise ValueError("args must match find_kbo_game")
            if self.tool_name == "search_stadium_guide" and not isinstance(
                self.args, SearchStadiumGuideRoutingArgs
            ):
                raise ValueError("args must match search_stadium_guide")
            if self.needs_clarification:
                raise ValueError("tool calls cannot also require clarification")
            if self.unsupported_reason is not None:
                raise ValueError("tool calls cannot have unsupported_reason")
        else:
            if self.tool_name is not None:
                raise ValueError("tool_name must be null when not calling a tool")
            if self.args is not None:
                raise ValueError("args must be null when not calling a tool")

        if self.needs_clarification and self.clarification_reason is None:
            raise ValueError("clarification_reason is required for clarification")

        if not self.needs_clarification and self.clarification_reason is not None:
            raise ValueError("clarification_reason must be null without clarification")

        if not self.is_in_scope and self.unsupported_reason != "out_of_scope":
            raise ValueError("out-of-scope requests require unsupported_reason=out_of_scope")

        return self
