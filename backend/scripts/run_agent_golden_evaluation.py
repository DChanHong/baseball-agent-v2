"""Golden candidate planning, injected graph collection and offline metric planning.

CLI never loads .env, connects to a DB or calls a paid API. Runtime graph dependencies
are explicitly injected through collect_graph_case; API/SSE/persistence need a separate
integration run. Full synthetic captures are temporary; durable summaries omit text.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ragas_evaluation import (
    METRIC_NAMES,
    EvaluationSample,
    prepare_metric_inputs,
)
from scripts.validate_agent_golden_dataset import Case, Dataset, validate_dataset

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "data/chat/evaluation/cases/agent_golden_candidates_v1.json"
ADAPTER_VERSION = "golden-graph-capture-v1"


def content_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


class Capture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    synthetic: Literal[True] = True
    adapter_version: Literal["golden-graph-capture-v1"] = ADAPTER_VERSION
    case_id: str
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_scope: Literal["in_process_agent_graph"] = "in_process_agent_graph"
    status: Literal["completed", "timeout", "error"]
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    observed_tool: str | None = None
    observed_input: dict[str, Any] = Field(default_factory=dict)
    tool_status: str | None = None
    response_origin: Literal["llm", "fallback", "template", "contextual_direct"] = (
        "template"
    )
    model_response: str | None = None
    final_response: str | None = None
    retrieval_items: list[dict[str, Any]] = Field(default_factory=list)
    generation_evidence: list[dict[str, Any]] = Field(default_factory=list)
    reason_code: (
        Literal["turn_timeout", "graph_error", "missing_completed_event"] | None
    ) = None


@dataclass
class GenerationCapture:
    """Observe actual request/model answer before source notice, including failures."""

    evidence: list[dict[str, Any]] = field(default_factory=list)
    model_response: str | None = None

    def observe(self, request: Any, model_response: str | None) -> None:
        self.evidence = [e.model_dump(mode="json") for e in request.evidence]
        self.model_response = model_response


def graph_input(case: Case):
    from app.agent.state import AgentConversationContext, BaseballAgentInput

    context = dict(case.input.conversation_context)
    if context.get("selected_game"):
        context["selected_game"] = {
            **context["selected_game"],
            "game_id": str(UUID(int=3)),
        }
    # History isn't consumed by the production graph; use explicit compact memory.
    return BaseballAgentInput(
        conversation_id=UUID(int=1),
        user_profile_id=UUID(int=2),
        user_message=case.input.question,
        today=case.input.today,
        timezone=case.input.timezone,
        favorite_team_id=case.input.favorite_team_id,
        context=AgentConversationContext.model_validate(context),
    )


async def collect_graph_case(
    case: Case,
    *,
    dataset_sha256: str,
    graph_factory: Callable[[GenerationCapture], Any],
    timeout_seconds: float = 60,
) -> Capture:
    """Factory must wire GenerationCapture.observe into AnswerGenerationService.

    The caller owns runtime resources and authorization/budget. No online evaluator
    is constructed here. One original last-turn invocation, no retries or history replay.
    """
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout must be positive and finite")
    observer = GenerationCapture()
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "dataset_sha256": dataset_sha256,
        "status": "error",
        "duration_ms": 0,
    }
    started = perf_counter()
    stream = None
    try:
        async with asyncio.timeout(timeout_seconds):
            graph = graph_factory(observer)
            stream = graph.astream(graph_input(case))
            async for event in stream:
                if event.kind == "tool.started":
                    row.update(
                        observed_tool=event.tool_name,
                        observed_input=event.tool_input or {},
                        tool_status="running",
                    )
                if event.kind in {"tool.completed", "tool.failed"}:
                    payload = event.tool_payload or {}
                    row["tool_status"] = payload.get("status")
                    result = payload.get("result") or {}
                    row["retrieval_items"] = result.get("items", [])
                if event.kind == "completed" and event.output is not None:
                    output = event.output
                    row.update(
                        status="completed",
                        response_origin=output.answer_source,
                        final_response=output.answer,
                    )
                    if output.routing_decision.should_call_tool:
                        row["observed_tool"] = output.routing_decision.tool_name
            if row["status"] != "completed":
                row["reason_code"] = "missing_completed_event"
    except TimeoutError:
        row.update(status="timeout", reason_code="turn_timeout")
    except Exception:  # noqa: BLE001 - never persist exceptions/secrets
        row.update(status="error", reason_code="graph_error")
    finally:
        if stream is not None:
            await stream.aclose()
    row.update(
        duration_ms=round((perf_counter() - started) * 1000, 3),
        generation_evidence=observer.evidence,
        model_response=observer.model_response,
    )
    return Capture.model_validate(row)


async def collect_graph_dataset(
    dataset: Dataset,
    *,
    graph_factory: Callable[[GenerationCapture], Any],
    split: Literal["development", "held_out", "all"] = "development",
    timeout_seconds: float = 60,
    stop_requested: Callable[[], bool] | None = None,
) -> list[Capture]:
    """Collect once per selected reviewed case; failed turns aren't retried.

    Caller owns dependencies, cleanup, paid budget and runtime corpus verification.
    Source-blocked cases remain not_run in summary.
    """
    captures = []
    for case in dataset.cases:
        if stop_requested is not None and stop_requested():
            break
        if (
            split != "all" and case.split != split
        ) or not case.final_review.exploratory_candidate:
            continue
        captures.append(
            await collect_graph_case(
                case,
                dataset_sha256=dataset.content_sha256,
                graph_factory=graph_factory,
                timeout_seconds=timeout_seconds,
            )
        )
    return captures


def excluded_metrics(reason: str) -> dict[str, Any]:
    return {
        name: {"status": "excluded", "reason_code": reason, "value": None}
        for name in METRIC_NAMES
    }


def metric_plan(case: Case, capture: Capture) -> dict[str, Any]:
    if case.final_review.status == "source_blocked":
        return excluded_metrics("source_review_pending")
    if case.evaluation.metric_policy == "pending_multi_tool_adapter":
        return excluded_metrics("multi_tool_adapter_pending")
    if capture.status != "completed":
        return excluded_metrics("turn_not_completed")
    if capture.response_origin == "llm" and capture.model_response is None:
        return excluded_metrics("model_capture_missing")
    # Explicit evaluation context scope; original question is never rewritten for routing.
    evaluation_input = json.dumps(
        {
            "question": case.input.question,
            "today": case.input.today.isoformat(),
            "favorite_team_id": case.input.favorite_team_id,
            "conversation_context": case.input.conversation_context,
            "scope": "original_last_turn_with_fixed_compact_context",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    sample = EvaluationSample(
        case_id=case.case_id,
        synthetic=True,
        user_input=evaluation_input,
        expected_tool=case.expected.tool_name or "none",
        observed_tool=capture.observed_tool,
        response_origin=capture.response_origin,
        model_response=capture.model_response,
        retrieval_items=capture.retrieval_items,
        generation_evidence=capture.generation_evidence,
        reference=case.expected.reference_answer,
        # Existing adapter accepts reviewed agent provenance; no human approval claim.
        reference_status="approved"
        if case.expected.reference_answer
        else "needs_review",
        reference_sources=[e.source_id for e in case.evidence],
        reference_reviewed_at=case.final_review.reviewed_at.isoformat(),
        reference_reviewer="agent_reviewed_candidate_not_human",
    )
    return prepare_metric_inputs(sample)


def rank_metrics(
    case: Case, capture: Capture, dataset: Dataset, *, k: int
) -> dict[str, Any]:
    """Bounded eligible-pool diagnostics, not global corpus Recall."""
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")
    reason = None
    review = case.retrieval_ground_truth.production_relevance_review
    labels = {
        c.chunk_id: c.relevance_grade for c in review.chunks if c.passes_expected_filter
    }
    items = capture.retrieval_items
    chunk_ids = [i.get("chunk_id") for i in items]
    manifest = {
        i["chunk_id"]: i for i in dataset.production_corpus_snapshot.manifest["chunks"]
    }
    if case.final_review.status == "source_blocked":
        reason = "source_review_pending"
    elif case.evaluation.metric_policy == "pending_multi_tool_adapter":
        reason = "multi_tool_adapter_pending"
    elif review.status == "not_applicable":
        reason = "non_rag_case"
    elif capture.observed_tool != case.expected.tool_name:
        reason = "routing_mismatch"
    elif capture.tool_status != "completed":
        reason = "retrieval_not_completed"
    elif len(set(chunk_ids)) != len(chunk_ids):
        reason = "duplicate_retrieved_chunk"
    elif any(i not in labels for i in chunk_ids):
        reason = "unlabeled_or_filter_ineligible_chunk"
    elif any(
        hashlib.sha256(i.get("content", "").encode()).hexdigest()
        != manifest[i["chunk_id"]]["observed_content_sha256"]
        for i in items
    ):
        reason = "retrieved_body_snapshot_mismatch"
    elif not any(grade == 2 for grade in labels.values()):
        reason = "no_core_evidence_after_filter"
    if reason:
        return {
            "status": "excluded",
            "reason_code": reason,
            "recall": None,
            "mrr": None,
            "ndcg": None,
        }
    ranked = [labels[i] for i in chunk_ids[:k]]
    core_count = sum(g == 2 for g in labels.values())
    dcg = sum((2**g - 1) / math.log2(index + 2) for index, g in enumerate(ranked))
    ideal = sum(
        (2**g - 1) / math.log2(index + 2)
        for index, g in enumerate(sorted(labels.values(), reverse=True)[:k])
    )
    return {
        "status": "computed",
        "reason_code": None,
        "recall": sum(g == 2 for g in ranked) / core_count,
        "mrr": next((1 / (index + 1) for index, g in enumerate(ranked) if g == 2), 0.0),
        "ndcg": dcg / ideal if ideal else None,
        "scope": "bounded_expected_filter_pool",
        "core_grade": 2,
        "available_core_chunks": core_count,
        "returned_chunks": len(items),
        "snapshot_check": "returned_bodies_only_not_entire_runtime_corpus",
    }


def summarize(
    dataset: Dataset,
    captures: list[Capture],
    *,
    split: str = "development",
    not_run_reason: Literal[
        "capture_not_supplied", "budget_stopped"
    ] = "capture_not_supplied",
) -> dict[str, Any]:
    cases = [c for c in dataset.cases if split == "all" or c.split == split]
    capture_map = {c.case_id: c for c in captures}
    if len(capture_map) != len(captures):
        raise ValueError("duplicate captures")
    if set(capture_map) - {c.case_id for c in cases}:
        raise ValueError("unknown or unselected case capture")
    if any(c.dataset_sha256 != dataset.content_sha256 for c in captures):
        raise ValueError("capture dataset hash mismatch")
    rows = []
    for case in cases:
        capture = capture_map.get(case.case_id)
        base = {
            "case_id": case.case_id,
            "category": case.category,
            "split": case.split,
            "human_reviewed": False,
            "corpus_coverage": case.retrieval_ground_truth.production_relevance_review.corpus_coverage,
            "filtered_coverage": case.retrieval_ground_truth.production_relevance_review.filtered_coverage,
            "question_resolution": "not_judged",
            "sse_completion": "not_checked",
            "persistence": "not_checked",
            "cost_usd": None,
            "usage": None,
        }
        if capture is None:
            reason = (
                "source_review_pending"
                if case.final_review.status == "source_blocked"
                else not_run_reason
            )
            base.update(
                status="not_run",
                reason_code=reason,
                metrics=excluded_metrics(reason),
                ranks={str(k): {"status": "not_run"} for k in (3, 5)},
            )
        else:
            plan = metric_plan(case, capture)
            base.update(
                status=capture.status,
                reason_code=capture.reason_code,
                duration_ms=capture.duration_ms,
                observed_tool=capture.observed_tool,
                tool_status=capture.tool_status,
                tool_routing_match=capture.observed_tool == case.expected.tool_name,
                filter_match=all(
                    capture.observed_input.get(key) == value
                    for key, value in case.expected.filter_constraints.items()
                ),
                response_origin=capture.response_origin,
                model_response_sha256=content_hash(capture.model_response)
                if capture.model_response is not None
                else None,
                final_response_sha256=content_hash(capture.final_response)
                if capture.final_response is not None
                else None,
                retrieval_sha256=content_hash(capture.retrieval_items),
                generation_evidence_sha256=content_hash(capture.generation_evidence),
                metrics={
                    name: {
                        "status": "not_run"
                        if entry["status"] == "ready"
                        else "excluded",
                        "input_ready": entry["status"] == "ready",
                        "reason_code": "judge_not_invoked"
                        if entry["status"] == "ready"
                        else entry["reason_code"],
                        "value": None,
                    }
                    for name, entry in plan.items()
                },
                ranks={
                    str(k): rank_metrics(case, capture, dataset, k=k) for k in (3, 5)
                },
            )
        rows.append(base)
    return {
        "schema_version": 1,
        "mode": "offline_capture_summary",
        "adapter_version": ADAPTER_VERSION,
        "service_baseline": False,
        "human_reviewed": False,
        "dataset_version": dataset.dataset_version,
        "dataset_sha256": dataset.content_sha256,
        "corpus_snapshot_sha256": dataset.production_corpus_snapshot.sha256,
        "dataset_code_revision": dataset.code_revision,
        "runtime_corpus_verified": False,
        "runtime_code_revision": None,
        "runtime_model_configuration": None,
        "execution_scope": "in_process_agent_graph_not_authenticated_http",
        "split_selection": split,
        "history_policy": "fixed_compact_context_only_no_prior_turn_replay",
        "ragas_executed": False,
        "case_count": len(rows),
        "captured_count": len(captures),
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--captures",
        type=Path,
        help="temporary synthetic Capture JSONL; omit for no-call planning",
    )
    parser.add_argument(
        "--split", choices=["development", "held_out", "all"], default="development"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--write-capture-schema", action="store_true")
    args = parser.parse_args()
    if args.output.resolve() in {
        args.dataset.resolve(),
        *([args.captures.resolve()] if args.captures else []),
    }:
        parser.error("output must not overwrite inputs")
    dataset = validate_dataset(json.loads(args.dataset.read_text()))
    captures = (
        [
            Capture.model_validate_json(line)
            for line in args.captures.read_text().splitlines()
            if line.strip()
        ]
        if args.captures
        else []
    )
    summary = summarize(dataset, captures, split=args.split)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if args.write_capture_schema:
        schema = Capture.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        (
            ROOT / "data/chat/evaluation/schemas/agent_golden_capture.schema.json"
        ).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n")
    print(
        f"Prepared {summary['case_count']} cases, captured={len(captures)}; no API/DB/judge calls"
    )


if __name__ == "__main__":
    main()
