from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StadiumGuideType = Literal[
    "stadium_bag_policy",
    "stadium_facility_guide",
    "stadium_seat_guide",
    "stadium_ticketing_guide",
    "stadium_transport_guide",
]


class SearchStadiumGuideToolInput(BaseModel):
    """LLM이 구장 안내 RAG 문서를 검색할 때 사용하는 tool 입력입니다."""

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
        description="User question to search against stadium guide chunks.",
    )
    guide_types: list[StadiumGuideType] | None = Field(
        default=None,
        description="Optional document type filters. Omit when the user question spans multiple guide types.",
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

    @field_validator("guide_types")
    @classmethod
    def normalize_guide_types(
        cls,
        value: list[StadiumGuideType] | None,
    ) -> list[StadiumGuideType] | None:
        if value is None:
            return None

        deduplicated = list(dict.fromkeys(value))
        if not deduplicated:
            raise ValueError("guide_types cannot be empty")
        return deduplicated


class StadiumGuideSearchItem(BaseModel):
    """구장 안내 RAG 검색 결과 단일 항목입니다."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    document_type: StadiumGuideType
    stadium_id: str
    team_id: str | None
    title: str
    content: str
    similarity: float = Field(ge=0.0, le=1.0)
    distance: float = Field(ge=0.0)
    source_urls: list[str]
    as_of: Date
    trust_level: Literal["official", "verified", "curated"]
    review_status: Literal["needs_review", "approved", "rejected"]
    metadata: dict[str, object]


class SearchStadiumGuideToolResult(BaseModel):
    """LLM에 돌려줄 구장 안내 RAG tool 결과입니다."""

    model_config = ConfigDict(extra="forbid")

    stadium_id: str
    team_id: str | None
    query: str
    answerable: bool
    items: list[StadiumGuideSearchItem]
    limitations: list[
        Literal[
            "no_relevant_stadium_guide_found",
            "stadium_guide_may_be_outdated",
        ]
    ]
