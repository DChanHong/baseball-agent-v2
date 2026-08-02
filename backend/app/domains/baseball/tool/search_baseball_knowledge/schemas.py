from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BaseballKnowledgeType = Literal[
    "baseball_rule",
    "common_play",
    "latest_kbo_rule",
]


class SearchBaseballKnowledgeToolInput(BaseModel):
    """LLM이 야구 규칙/플레이/최신 KBO 규정 RAG 문서를 검색할 때 사용하는 tool 입력입니다."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=1,
        description="User question to search against baseball knowledge chunks.",
    )
    knowledge_types: list[BaseballKnowledgeType] | None = Field(
        default=None,
        description="Optional document type filters. Omit when the question is broad.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to return.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized

    @field_validator("knowledge_types")
    @classmethod
    def normalize_knowledge_types(
        cls,
        value: list[BaseballKnowledgeType] | None,
    ) -> list[BaseballKnowledgeType] | None:
        if value is None:
            return None

        deduplicated = list(dict.fromkeys(value))
        if not deduplicated:
            raise ValueError("knowledge_types cannot be empty")
        return deduplicated


class BaseballKnowledgeSearchItem(BaseModel):
    """야구 지식 RAG 검색 결과 단일 항목입니다."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    document_type: BaseballKnowledgeType
    title: str
    content: str
    similarity: float = Field(ge=0.0, le=1.0)
    distance: float = Field(ge=0.0)
    source_urls: list[str]
    as_of: Date
    trust_level: Literal["official", "verified", "curated"]
    review_status: Literal["needs_review", "approved", "rejected"]
    metadata: dict[str, object]


class SearchBaseballKnowledgeToolResult(BaseModel):
    """LLM에 돌려줄 야구 지식 RAG tool 결과입니다."""

    model_config = ConfigDict(extra="forbid")

    query: str
    answerable: bool
    items: list[BaseballKnowledgeSearchItem]
    limitations: list[
        Literal[
            "no_relevant_baseball_knowledge_found",
            "baseball_knowledge_may_be_outdated",
            "not_official_game_cancellation_decision",
        ]
    ]
