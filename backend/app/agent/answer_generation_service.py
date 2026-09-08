from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.agent.answer_schemas import (
    AnswerEvidence,
    GroundedAnswerDraft,
    GroundedAnswerRequest,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

ANSWER_GENERATION_POLICY_PATH = (
    Path(__file__).with_name("prompt_assets") / "answer_generation_policy.md"
)
_MAX_RAG_EVIDENCE_ITEMS = 3
_MAX_EVIDENCE_CONTENT_CHARS = 6000


class AnswerGenerationService:
    """Generate a grounded final answer from bounded tool evidence."""

    def __init__(
        self,
        chain: Any | None = None,
        model: str | None = None,
    ) -> None:
        if chain is not None and model is not None:
            self._model = model
            self._chain = chain
            return

        settings = get_settings()
        self._model = model or settings.openai_model
        self._chain = chain or _build_answer_generation_chain(
            model=self._model,
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
        )

    async def execute(
        self,
        *,
        message: str,
        tool_payload: dict[str, Any],
        tool_limitations: list[str],
    ) -> GroundedAnswerDraft:
        request = build_grounded_answer_request(
            message=message,
            tool_payload=tool_payload,
            tool_limitations=tool_limitations,
        )
        logger.info(
            "answer generation started model=%s tool_name=%s evidence_count=%d",
            self._model,
            request.tool_name,
            len(request.evidence),
        )

        try:
            response = await self._chain.ainvoke({"request": request.model_dump_json()})
        except Exception:
            logger.exception("answer generation failed model=%s", self._model)
            raise

        draft = (
            response
            if isinstance(response, GroundedAnswerDraft)
            else GroundedAnswerDraft.model_validate(response)
        )
        allowed_refs = {item.ref for item in request.evidence}
        unknown_refs = set(draft.used_evidence_refs) - allowed_refs
        if unknown_refs:
            raise ValueError(
                f"answer referenced unknown evidence: {sorted(unknown_refs)}"
            )

        allowed_limitations = _allowed_limitations(request)
        unknown_limitations = set(draft.acknowledged_limitations) - allowed_limitations
        if unknown_limitations:
            raise ValueError(
                "answer acknowledged unknown limitations: "
                f"{sorted(unknown_limitations)}"
            )

        logger.info(
            "answer generation completed model=%s answerability=%s evidence_refs=%s",
            self._model,
            draft.answerability,
            draft.used_evidence_refs,
        )
        return draft


def build_grounded_answer_request(
    *,
    message: str,
    tool_payload: dict[str, Any],
    tool_limitations: list[str],
) -> GroundedAnswerRequest:
    tool_name = tool_payload.get("name")
    result = tool_payload.get("result")
    if tool_payload.get("status") != "completed":
        raise ValueError("answer generation requires a completed tool payload")
    if not isinstance(tool_name, str) or not isinstance(result, dict):
        raise TypeError("answer generation requires a valid tool result")

    return GroundedAnswerRequest(
        user_message=message,
        tool_name=tool_name,
        evidence=_build_evidence(result),
        limitations=list(dict.fromkeys(tool_limitations)),
    )


def _build_evidence(result: dict[str, Any]) -> list[AnswerEvidence]:
    items = result.get("items")
    if isinstance(items, list) and items:
        evidence = []
        for index, item in enumerate(items[:_MAX_RAG_EVIDENCE_ITEMS], start=1):
            if not isinstance(item, dict):
                continue
            evidence.append(
                AnswerEvidence(
                    ref=f"E{index}",
                    kind="retrieved_document",
                    payload=_bounded_rag_item(item),
                )
            )
        if evidence:
            return evidence

    return [
        AnswerEvidence(
            ref="E1",
            kind="tool_result",
            payload=result,
        )
    ]


def _bounded_rag_item(item: dict[str, Any]) -> dict[str, Any]:
    bounded = {
        key: value
        for key, value in item.items()
        if key
        in {
            "chunk_id",
            "document_id",
            "document_type",
            "stadium_id",
            "team_id",
            "title",
            "content",
            "source_urls",
            "as_of",
            "trust_level",
            "review_status",
            "metadata",
        }
    }
    content = bounded.get("content")
    if isinstance(content, str) and len(content) > _MAX_EVIDENCE_CONTENT_CHARS:
        bounded["content"] = content[:_MAX_EVIDENCE_CONTENT_CHARS]
        bounded["content_truncated"] = True
    return bounded


def _allowed_limitations(request: GroundedAnswerRequest) -> set[str]:
    allowed = set(request.limitations)
    for evidence in request.evidence:
        review_status = evidence.payload.get("review_status")
        if review_status == "needs_review":
            allowed.add("needs_review")

        metadata = evidence.payload.get("metadata")
        if isinstance(metadata, dict):
            metadata_limitations = metadata.get("limitations")
            if isinstance(metadata_limitations, list):
                allowed.update(
                    item for item in metadata_limitations if isinstance(item, str)
                )

        if evidence.payload.get("content_truncated") is True:
            allowed.add("content_truncated")
    return allowed


@lru_cache
def load_answer_generation_policy_prompt() -> str:
    return ANSWER_GENERATION_POLICY_PATH.read_text(encoding="utf-8").strip()


def _build_answer_generation_chain(
    *,
    model: str,
    api_key: str,
    timeout: float,
):
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=load_answer_generation_policy_prompt()),
            ("human", "{request}"),
        ]
    )
    chat_model = ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        timeout=timeout,
    )
    return prompt | chat_model.with_structured_output(
        GroundedAnswerDraft,
        method="json_schema",
        strict=True,
    )
