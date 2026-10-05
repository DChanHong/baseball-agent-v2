"""Freeze public RAG evidence once, then compare answer models without DB writes."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

import app.agent.answer_generation_service as answer_module
import app.core.agent_trace as trace_module
from app.agent.answer_generation_service import (
    AnswerContractError,
    AnswerGenerationService,
    build_grounded_answer_request,
)
from app.api.dependencies import (
    get_search_baseball_knowledge_tool_handler,
    get_search_stadium_guide_tool_handler,
    get_search_ticketing_guide_tool_handler,
)
from app.core.database import async_session_factory, engine
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    SearchBaseballKnowledgeToolInput,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
)
from app.domains.baseball.tool.search_ticketing_guide.schemas import (
    SearchTicketingGuideToolInput,
)


async def prepare(path: Path) -> None:
    specs = [
        ("double_play", "병살이 뭐야?", "search_baseball_knowledge"),
        ("balk", "보크가 뭐야?", "search_baseball_knowledge"),
        (
            "sajik_ticket",
            "사직야구장 롯데 경기 예매 어디서 해?",
            "search_ticketing_guide",
        ),
        ("sajik_parking", "사직야구장 주차는 어떻게 해?", "search_stadium_guide"),
    ]
    cases = []
    engine.echo = False
    async with async_session_factory() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))
        for case_id, question, tool in specs:
            if tool == "search_baseball_knowledge":
                result = await get_search_baseball_knowledge_tool_handler(
                    session
                ).execute(SearchBaseballKnowledgeToolInput(query=question))
            elif tool == "search_ticketing_guide":
                result = await get_search_ticketing_guide_tool_handler(session).execute(
                    SearchTicketingGuideToolInput(query=question, stadium_id="SAJIK")
                )
            else:
                result = await get_search_stadium_guide_tool_handler(session).execute(
                    SearchStadiumGuideToolInput(
                        query=question,
                        stadium_id="SAJIK",
                        guide_types=["stadium_transport_guide"],
                    )
                )
            cases.append(
                {
                    "case_id": case_id,
                    "input": question,
                    "evidence_origin": "public_production_rag",
                    "tool_payload": {
                        "name": tool,
                        "status": "completed",
                        "result": result.model_dump(mode="json"),
                    },
                    "tool_limitations": list(result.limitations),
                }
            )
        await session.rollback()
    await engine.dispose()
    cases.append(
        {
            "case_id": "no_source",
            "input": "사직야구장 VIP 라운지에 반려동물 동반 가능해?",
            "evidence_origin": "synthetic_empty_tool_result",
            "tool_payload": {
                "name": "search_stadium_guide",
                "status": "completed",
                "result": {"items": [], "answerable": False},
            },
            "tool_limitations": ["no_relevant_stadium_guide_found"],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at": datetime.now(UTC).isoformat(),
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(
        json.dumps(
            {"prepared_cases": len(cases), "dataset": str(path)}, ensure_ascii=False
        ),
        flush=True,
    )


async def compare(args: argparse.Namespace) -> None:
    cases = json.loads(args.dataset.read_text())["cases"]
    prompt_sha256 = hashlib.sha256(
        (ROOT / "app/agent/prompt_assets/answer_generation_policy.md").read_bytes()
    ).hexdigest()
    compact_metadata = answer_module._compact_rag_metadata
    original_emit_trace = trace_module.emit_trace
    actual_models = {model: model for model in args.models}
    efforts = {}
    if args.reasoning_efforts:
        actual_models = {
            f"{model}:{effort}": model
            for model in args.models
            for effort in args.reasoning_efforts
        }
        efforts = {label: label.rsplit(":", 1)[1] for label in actual_models}
        args.models = list(actual_models)
    if args.compare_metadata:
        actual_models = {
            f"{model}:{variant}": model
            for model in args.models
            for variant in ("original_metadata", "compact_metadata")
        }
        args.models = list(actual_models)
    services = {
        label: AnswerGenerationService(
            model=model,
            timeout_seconds=args.timeout,
            reasoning_effort=efforts.get(label),
        )
        for label, model in actual_models.items()
    }
    rows = []
    review = []
    started_at = datetime.now(UTC).isoformat()
    for repetition in range(args.repeats):
        for case in cases:
            for model in (
                args.models if repetition % 2 == 0 else list(reversed(args.models))
            ):
                answer_module._compact_rag_metadata = (
                    (lambda metadata: dict(metadata))
                    if args.compare_metadata and model.endswith(":original_metadata")
                    else compact_metadata
                )
                request = build_grounded_answer_request(
                    message=case["input"],
                    tool_payload=case["tool_payload"],
                    tool_limitations=case["tool_limitations"],
                )
                digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
                row = {
                    "case_id": case["case_id"],
                    "model": model,
                    "actual_model": actual_models[model],
                    "reasoning_effort": efforts.get(model),
                    "repetition": repetition + 1,
                    "input_sha256": digest,
                    "input_chars": len(request.model_dump_json()),
                    "status": "failed",
                }
                started = perf_counter()
                events = []
                trace_module.emit_trace = (
                    lambda trace_id, event, captured=events, **fields: captured.append(
                        {"event": event, **fields}
                    )
                )
                try:
                    with trace_module.trace_scope("synthetic-benchmark"):
                        draft = await services[model].execute(
                            message=case["input"],
                            tool_payload=case["tool_payload"],
                            tool_limitations=case["tool_limitations"],
                        )
                    row.update(
                        status="validated",
                        answerability=draft.answerability,
                        used_evidence_refs=draft.used_evidence_refs,
                        acknowledged_limitations=draft.acknowledged_limitations,
                        answer_chars=len(draft.answer),
                    )
                    review.append(
                        {
                            "case_id": case["case_id"],
                            "model": model,
                            "repetition": repetition + 1,
                            "answer": draft.answer,
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - record every failed benchmark call without exception text
                    row["failure_reason"] = (
                        exc.code
                        if isinstance(exc, AnswerContractError)
                        else type(exc).__name__
                    )
                row["duration_ms"] = round((perf_counter() - started) * 1000, 3)
                for event in events:
                    if event["event"] == "answer_llm.started":
                        row["reasoning_effort"] = event.get("reasoning_effort")
                    if event["event"] == "answer_validation.completed":
                        row["source_notice_added"] = event.get(
                            "source_notice_added", False
                        )
                row["token_usage"] = {
                    key: value
                    for event in events
                    if event["event"] == "answer_llm.completed"
                    for key, value in event.items()
                    if key
                    in {
                        "input_tokens",
                        "output_tokens",
                        "total_tokens",
                        "reasoning_tokens",
                        "cached_input_tokens",
                    }
                }
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
                write_results(args, started_at, rows, review, prompt_sha256)
    answer_module._compact_rag_metadata = compact_metadata
    trace_module.emit_trace = original_emit_trace


def write_results(
    args: argparse.Namespace,
    started_at: str,
    rows: list,
    review: list,
    prompt_sha256: str,
) -> None:
    summary = {}
    for model in args.models:
        subset = [r for r in rows if r["model"] == model]
        if not subset:
            continue
        durations = [r["duration_ms"] for r in subset]
        summary[model] = {
            "count": len(subset),
            "validated": sum(r["status"] == "validated" for r in subset),
            "median_ms": round(statistics.median(durations), 3),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "timeouts": sum(r.get("failure_reason") == "TimeoutError" for r in subset),
            "manual_quality_review": "pending",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "started_at": started_at,
                "scope": "answer_only_fixed_evidence",
                "dataset": str(args.dataset.resolve().relative_to(ROOT.parent)),
                "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                "prompt_sha256": prompt_sha256,
                "timeout_seconds": args.timeout,
                "repeats": args.repeats,
                "summary": summary,
                "results": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    # Only synthetic evaluation answers, temporarily retained for human review.
    args.review_output.write_text(json.dumps(review, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Read-only public RAG collection; calls embedding API",
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=["gpt-5-mini", "gpt-4.1-mini"])
    parser.add_argument("--compare-metadata", action="store_true")
    parser.add_argument(
        "--reasoning-efforts", nargs="+", choices=["minimal", "low", "medium", "high"]
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--review-output",
        type=Path,
        default=Path("/private/tmp/baseball-answer-model-review.json"),
    )
    args = parser.parse_args()
    if args.compare_metadata and args.reasoning_efforts:
        parser.error("Compare one intervention at a time")
    logging.disable(logging.CRITICAL)
    if not args.prepare and args.output is None:
        parser.error("--output is required for comparison")
    asyncio.run(prepare(args.dataset) if args.prepare else compare(args))
