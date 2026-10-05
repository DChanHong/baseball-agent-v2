"""Offline input planning and injectable scoring for synthetic RAG evaluation.

No DB access, environment-file loading, or API calls on import / CLI execution.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RAGAS_VERSION = "0.4.3"
ADAPTER_VERSION = "ragas-input-v1"
RAG_TOOLS = {
    "search_baseball_knowledge",
    "search_stadium_guide",
    "search_ticketing_guide",
}
METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


class EvaluationSample(BaseModel):
    """Capture actual generation evidence, never reconstruct it from full retrieval."""

    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1)
    synthetic: Literal[True]
    user_input: str = Field(min_length=1)
    expected_tool: str
    observed_tool: str | None
    response_origin: Literal["llm", "fallback", "template", "contextual_direct"]
    model_response: str | None = None
    retrieval_items: list[dict[str, Any]]
    generation_evidence: list[dict[str, Any]]
    reference: str | None = None
    reference_status: Literal["needs_review", "approved"] = "needs_review"
    reference_sources: list[str] = Field(default_factory=list)
    reference_reviewed_at: str | None = None
    reference_reviewer: str | None = None
    empty_evidence_policy_case: bool = False

    @model_validator(mode="after")
    def require_reference_review(self) -> EvaluationSample:
        if self.reference_status == "approved" and not all(
            (
                self.reference and self.reference.strip(),
                self.reference_sources,
                self.reference_reviewed_at,
                self.reference_reviewer,
            )
        ):
            raise ValueError("approved reference requires text and review provenance")
        for item in self.retrieval_items:
            if not isinstance(item.get("content"), str) or not item["content"].strip():
                raise ValueError("retrieval items require nonempty public content")
        for item in self.generation_evidence:
            if item.get("kind") not in {"retrieved_document", "tool_result"}:
                raise ValueError("invalid generation evidence kind")
            payload = item.get("payload")
            if not isinstance(payload, dict):
                raise ValueError("generation evidence requires a payload")  # noqa: TRY004 - Pydantic validation error
            if item["kind"] == "retrieved_document" and (
                not isinstance(payload.get("content"), str)
                or not payload["content"].strip()
            ):
                raise ValueError("retrieved evidence requires nonempty public content")
        return self


def serialize_context(item: dict[str, Any]) -> str:
    """Preserve public content/domain context; IDs/scores aren't domain facts."""
    keys = (
        "title",
        "content",
        "metadata",
        "source_urls",
        "as_of",
        "trust_level",
        "review_status",
        "content_truncated",
    )
    return json.dumps(
        {key: item[key] for key in keys if key in item},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def prepare_metric_inputs(sample: EvaluationSample) -> dict[str, dict[str, Any]]:
    """A plan contains either ascore kwargs or an explicit exclusion reason."""
    retrieval = [serialize_context(item) for item in sample.retrieval_items]
    evidence = [
        serialize_context(item["payload"])
        for item in sample.generation_evidence
        if item.get("kind") == "retrieved_document"
        and isinstance(item.get("payload"), dict)
    ]
    plan: dict[str, dict[str, Any]] = {}
    common = None
    if sample.expected_tool not in RAG_TOOLS:
        common = "non_rag_case"
    elif sample.observed_tool != sample.expected_tool:
        common = "routing_mismatch"
    elif sample.empty_evidence_policy_case:
        common = "empty_evidence_policy_case"
    for name in METRIC_NAMES:
        reason = common
        kwargs: dict[str, Any] = {"user_input": sample.user_input}
        if name in {"faithfulness", "answer_relevancy"}:
            if reason is None:
                if sample.response_origin != "llm":
                    reason = "non_llm_response"
                elif not sample.model_response or not sample.model_response.strip():
                    reason = "missing_model_response"
                elif name == "faithfulness" and not evidence:
                    reason = "empty_generation_evidence"
            kwargs["response"] = sample.model_response
            if name == "faithfulness":
                kwargs["retrieved_contexts"] = evidence
        else:
            if reason is None:
                if not retrieval:
                    reason = "empty_retrieval"
                elif not sample.reference or not sample.reference.strip():
                    reason = "missing_reference"
                elif sample.reference_status != "approved":
                    reason = "reference_not_approved"
            kwargs.update(reference=sample.reference, retrieved_contexts=retrieval)
        plan[name] = (
            {"status": "excluded", "reason_code": reason}
            if reason
            else {"status": "ready", "kwargs": kwargs}
        )
    return plan


def build_metrics(*, llm: Any, embeddings: Any) -> dict[str, Any]:
    """Inject explicitly configured judge resources; don't load app credentials."""
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    from importlib.metadata import version

    if version("ragas") != RAGAS_VERSION:
        raise RuntimeError("install the locked evaluation dependency group")
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(
            llm=llm, embeddings=embeddings, strictness=3
        ),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }


async def score_sample(
    sample: EvaluationSample, *, metrics: dict[str, Any], timeout_seconds: float = 30
) -> dict[str, dict[str, Any]]:
    """Explicit invocation only; sequential calls, no runner-level retry."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    results: dict[str, dict[str, Any]] = {}
    for name, entry in prepare_metric_inputs(sample).items():
        if entry["status"] == "excluded":
            results[name] = {**entry, "value": None, "duration_ms": 0}
            continue
        started = perf_counter()
        row: dict[str, Any] = {"status": "error", "value": None, "reason_code": None}
        try:
            async with asyncio.timeout(timeout_seconds):
                result = await metrics[name].ascore(**entry["kwargs"])
            if (
                isinstance(result.value, bool)
                or not isinstance(result.value, (int, float))
                or not math.isfinite(result.value)
            ):
                row["reason_code"] = "undefined_score"
            else:
                row.update(status="scored", value=float(result.value))
        except TimeoutError:
            row["reason_code"] = "judge_timeout"
        except Exception:  # noqa: BLE001 - isolate each judge failure without saving text
            row["reason_code"] = "judge_error"
        row["duration_ms"] = round((perf_counter() - started) * 1000, 3)
        results[name] = row
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate synthetic JSONL inputs without API calls"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("output must not overwrite input")
    samples = [
        EvaluationSample.model_validate_json(line)
        for line in args.input.read_text().splitlines()
        if line.strip()
    ]
    ids = [sample.case_id for sample in samples]
    if not samples or len(ids) != len(set(ids)):
        parser.error("input must contain samples with unique case IDs")
    rows = []
    for sample in samples:
        rows.append(
            {
                "case_id": sample.case_id,
                "routing_match": sample.expected_tool == sample.observed_tool,
                "metrics": {
                    name: {
                        "status": entry["status"],
                        "reason_code": entry.get("reason_code"),
                    }
                    for name, entry in prepare_metric_inputs(sample).items()
                },
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "offline_input_validation",
                "ragas_version": RAGAS_VERSION,
                "adapter_version": ADAPTER_VERSION,
                "dataset_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                "results": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"Validated {len(rows)} samples; no API calls")


if __name__ == "__main__":
    main()
