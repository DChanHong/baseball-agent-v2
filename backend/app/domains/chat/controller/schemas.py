from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ToolName = Literal[
    "find_kbo_game",
    "get_stadium_info",
    "search_stadium_guide",
    "search_ticketing_guide",
    "search_baseball_knowledge",
    "get_weather_context",
]

ToolStreamStatus = Literal["running", "completed", "failed"]


class ChatStreamRequest(BaseModel):
    """Streaming chat HTTP request schema."""

    model_config = ConfigDict(extra="forbid")

    guest_id: UUID
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatStreamMessage(BaseModel):
    """Message payload emitted through chat stream events."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    role: Literal["user", "assistant"]
    content: str
    sequence_no: int
    created_at: datetime


class StreamError(BaseModel):
    """Stable error payload for stream events."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ConversationCreatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    created: bool


class MessageCreatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: ChatStreamMessage


class ToolStartedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    name: ToolName
    status: Literal["running"]
    input: dict[str, Any]


class ToolCompletedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    name: ToolName
    status: Literal["completed"]
    input: dict[str, Any]
    result: dict[str, Any]
    error: None = None


class ToolFailedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    name: ToolName
    status: Literal["failed"]
    input: dict[str, Any]
    result: None = None
    error: StreamError


class AssistantDeltaEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    delta: str


class AssistantCompletedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    content: str
    sources: list[dict[str, Any]]
    limitations: list[str]


class ConversationUpdatedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str | None
    last_message_at: datetime | None


class ConversationUpdatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation: ConversationUpdatedSummary


class DoneEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID


class StreamFailedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: StreamError
