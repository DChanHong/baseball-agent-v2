from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.baseball.tool.search_stadium_guide.schemas import (
    StadiumGuideSearchItem,
)


class SearchTicketingGuideToolInput(BaseModel):
    """LLM이 구장/팀 예매 안내 문서를 검색할 때 사용하는 tool 입력입니다."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: str = Field(
        min_length=1,
        description="KBO stadium id used as a required metadata filter. Example: SAJIK.",
    )
    team_id: str | None = Field(
        default=None,
        description="Optional KBO team id used as context. Example: LOTTE.",
    )
    query: str = Field(
        min_length=1,
        description="User question to search against ticketing guide chunks.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to return.",
    )

    @field_validator("stadium_id", "team_id")
    @classmethod
    def normalize_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("identifier cannot be blank")
        return normalized

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized


class SearchTicketingGuideToolResult(BaseModel):
    """LLM에 돌려줄 예매 안내 RAG tool 결과입니다."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: str
    team_id: str | None
    query: str
    answerable: bool
    items: list[StadiumGuideSearchItem]
    limitations: list[
        str
    ] = Field(
        description=(
            "Known limits such as no result, possibly outdated policy, "
            "no realtime inventory, or official ticketing source required."
        )
    )
