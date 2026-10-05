from __future__ import annotations

import asyncio
import logging
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, ValidationError

from app.agent.answer_schemas import (
    AnswerEvidence,
    GroundedAnswerDraft,
    GroundedAnswerRequest,
)
from app.core.agent_trace import trace_stage
from app.core.config import get_settings

logger = logging.getLogger(__name__)

ANSWER_GENERATION_POLICY_PATH = (
    Path(__file__).with_name("prompt_assets") / "answer_generation_policy.md"
)
_MAX_RAG_EVIDENCE_ITEMS = 3
_MAX_EVIDENCE_CONTENT_CHARS = 6000
_FAST_ANSWER_TOOLS = {"search_ticketing_guide", "search_stadium_guide"}


AnswerValidationCode = Literal[
    "answer_schema_invalid", "unknown_evidence_refs", "unknown_limitation_codes"
]


class AnswerContractError(ValueError):
    """Stable validation reason without copying model-generated values into logs."""

    def __init__(self, code: AnswerValidationCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class AnswerGenerationService:
    """Generate a grounded final answer from bounded tool evidence."""

    def __init__(
        self,
        chain: Any | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        if chain is not None and model is not None:
            self._model = model
            self._chain = chain
            self._timeout_seconds = timeout_seconds or 15.0
            self._reasoning_effort = reasoning_effort
            self._conservative_chain = None
            return

        settings = get_settings()
        self._model = model or settings.openai_answer_model or settings.openai_model
        self._reasoning_effort = (
            reasoning_effort or settings.openai_answer_reasoning_effort
        )
        if not self._model.startswith("gpt-5"):
            self._reasoning_effort = None
        self._timeout_seconds = (
            timeout_seconds or settings.openai_answer_timeout_seconds
        )
        self._chain = chain or _build_answer_generation_chain(
            model=self._model,
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            reasoning_effort=self._reasoning_effort,
        )
        self._conservative_chain = None
        if (
            chain is None
            and reasoning_effort is None
            and self._reasoning_effort in {"low", "minimal"}
        ):
            self._conservative_chain = _build_answer_generation_chain(
                model=self._model,
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout_seconds,
                reasoning_effort="medium",
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
        chain = self._chain
        effective_effort = self._reasoning_effort
        if (
            self._conservative_chain is not None
            and request.tool_name not in _FAST_ANSWER_TOOLS
        ):
            chain = self._conservative_chain
            effective_effort = "medium"

        try:
            with trace_stage(
                "answer_llm",
                model=self._model,
                timeout_seconds=self._timeout_seconds,
                reasoning_effort=effective_effort,
                input_chars=len(request.model_dump_json()),
            ) as llm_details:
                async with asyncio.timeout(self._timeout_seconds):
                    response = await chain.ainvoke(
                        {"request": request.model_dump_json()}
                    )
                llm_details.update(_answer_usage_details(response))
        except ValidationError:
            raise AnswerContractError(
                "answer_schema_invalid", "answer schema invalid"
            ) from None
        except Exception:
            logger.exception("answer generation failed model=%s", self._model)
            raise

        with trace_stage(
            "answer_validation",
            evidence_count=len(request.evidence),
            allowed_limitation_count=len(request.allowed_limitations),
        ) as details:
            try:
                draft = _validate_answer_response(response, request)
                draft, notice_added = _finalize_source_notice(draft, request)
                details["source_notice_added"] = notice_added
            except AnswerContractError as exc:
                details["error_code"] = exc.code
                raise

        logger.info(
            "answer generation completed model=%s answerability=%s evidence_refs=%s",
            self._model,
            draft.answerability,
            draft.used_evidence_refs,
        )
        return draft


def _validate_answer_response(
    response: Any,
    request: GroundedAnswerRequest,
) -> GroundedAnswerDraft:
    if isinstance(response, dict) and "parsed" in response and "raw" in response:
        if response.get("parsing_error") is not None or response["parsed"] is None:
            raise AnswerContractError("answer_schema_invalid", "answer schema invalid")
        response = response["parsed"]
    try:
        draft = (
            response
            if isinstance(response, GroundedAnswerDraft)
            else GroundedAnswerDraft.model_validate(response)
        )
    except ValidationError:
        raise AnswerContractError(
            "answer_schema_invalid", "answer schema invalid"
        ) from None
    allowed_refs = {item.ref for item in request.evidence}
    if set(draft.used_evidence_refs) - allowed_refs:
        raise AnswerContractError(
            "unknown_evidence_refs", "answer referenced unknown evidence"
        )
    if set(draft.acknowledged_limitations) - set(request.allowed_limitations):
        raise AnswerContractError(
            "unknown_limitation_codes", "answer acknowledged unknown limitations"
        )
    return draft


def _finalize_source_notice(
    draft: GroundedAnswerDraft, request: GroundedAnswerRequest
) -> tuple[GroundedAnswerDraft, bool]:
    reviewed = [
        e
        for e in request.evidence
        if e.ref in draft.used_evidence_refs
        and e.payload.get("review_status") == "needs_review"
    ]
    if not reviewed:
        return draft, False
    dates = set()
    for evidence in reviewed:
        value = evidence.payload.get("as_of")
        if isinstance(value, str):
            try:
                dates.add(date.fromisoformat(value).isoformat())
            except ValueError:
                pass
    prefix = f"자료 기준일: {', '.join(sorted(dates))}. " if dates else ""
    notice = (
        prefix + "제공 자료는 추가 검수가 필요하므로 공식 출처에서 재확인해 주세요."
    )
    data = draft.model_dump()
    data["answer"] = f"{draft.answer}\n\n{notice}"
    data["acknowledged_limitations"] = list(
        dict.fromkeys([*draft.acknowledged_limitations, "needs_review"])
    )
    try:
        return GroundedAnswerDraft.model_validate(data), True
    except ValidationError:
        raise AnswerContractError(
            "answer_schema_invalid", "answer schema invalid"
        ) from None


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

    request = GroundedAnswerRequest(
        user_message=message,
        tool_name=tool_name,
        evidence=_build_evidence(result),
        limitations=list(dict.fromkeys(tool_limitations)),
        allowed_limitations=[],
    )
    request.allowed_limitations = sorted(_allowed_limitations(request))
    return request


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
    metadata = bounded.get("metadata")
    if isinstance(metadata, dict):
        bounded["metadata"] = _compact_rag_metadata(metadata)
    content = bounded.get("content")
    if isinstance(content, str) and len(content) > _MAX_EVIDENCE_CONTENT_CHARS:
        bounded["content"] = content[:_MAX_EVIDENCE_CONTENT_CHARS]
        bounded["content_truncated"] = True
    return bounded


def _compact_rag_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Omit indexing hints; preserve source context and all domain-specific facts."""
    indexing_keys = {
        "audience",
        "language",
        "topic_id",
        "knowledge_type",
        "search_keywords",
        "example_questions",
    }
    return {key: value for key, value in metadata.items() if key not in indexing_keys}


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
    reasoning_effort: str | None = None,
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
        reasoning_effort=reasoning_effort,
    )
    return prompt | chat_model.with_structured_output(
        GroundedAnswerDraft,
        method="json_schema",
        strict=True,
        include_raw=True,
    )


def _answer_usage_details(response: Any) -> dict[str, int]:
    """Log an allowlist of token counters, never message or provider metadata."""
    if not isinstance(response, dict):
        return {}
    usage = getattr(response.get("raw"), "usage_metadata", None)
    if not isinstance(usage, dict):
        return {}
    counters = {
        name: usage.get(name)
        for name in ("input_tokens", "output_tokens", "total_tokens")
    }
    for group, name, target in (
        ("output_token_details", "reasoning", "reasoning_tokens"),
        ("input_token_details", "cache_read", "cached_input_tokens"),
    ):
        details = usage.get(group)
        if isinstance(details, dict):
            counters[target] = details.get(name)
    return {
        key: value
        for key, value in counters.items()
        if type(value) is int and value >= 0
    }
