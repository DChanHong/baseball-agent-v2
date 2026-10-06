from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)


class AnswerEvidence(BaseModel):
    """One bounded evidence item supplied to final answer generation."""

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(pattern=r"^E[1-9][0-9]*$")
    kind: Literal["tool_result", "retrieved_document"]
    payload: dict[str, Any]


class GroundedAnswerRequest(BaseModel):
    """Validated input passed to the final-answer LLM."""

    model_config = ConfigDict(extra="forbid")

    user_message: str = Field(min_length=1, max_length=4000)
    tool_name: str = Field(min_length=1)
    evidence: list[AnswerEvidence] = Field(min_length=1, max_length=3)
    limitations: list[str]
    allowed_limitations: list[str] = Field(
        description="Complete server-computed list of allowed limitation codes."
    )


class AnswerEvaluationInput(BaseModel):
    """Ephemeral judge input; never part of model output, SSE, or stored metadata."""

    user_input: str
    response: str
    tool_name: str
    contexts: list[str]


class GroundedAnswerDraft(BaseModel):
    """Structured final answer returned by the LLM."""

    model_config = ConfigDict(extra="forbid")
    _evaluation_input: AnswerEvaluationInput | None = PrivateAttr(default=None)

    answerability: Literal[
        "fully_answerable", "partially_answerable", "insufficient_source"
    ]
    answer: str = Field(min_length=1, max_length=2400)
    used_evidence_refs: list[str]
    acknowledged_limitations: list[str] = Field(
        description=(
            "Select exact codes only from input allowed_limitations. "
            "Do not invent or paraphrase codes. Use [] when none apply."
        )
    )

    @field_validator("used_evidence_refs")
    @classmethod
    def deduplicate_evidence_refs(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def require_evidence_for_supported_answer(self) -> GroundedAnswerDraft:
        if (
            self.answerability in {"fully_answerable", "partially_answerable"}
            and not self.used_evidence_refs
        ):
            raise ValueError(
                "a supported answer must reference at least one evidence item"
            )
        return self
