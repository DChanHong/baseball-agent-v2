"""Paid agent-core/RAGAS baseline; PostgreSQL SELECT only, no Auth/chat writes.

Shares the authorized ledger with API runs. Fixed synthetic input IDs never reach
persistence. A distinct scope records authentication/SSE/storage as not checked.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.agent_evaluation_runtime import (
    EvaluationResources,
    EvaluationRuntime,
    current_evaluation_case,
)
from scripts.execute_agent_golden_baseline import (
    TraceCollector,
    executor,
    save_private,
    score_plan,
)
from scripts.run_agent_golden_evaluation import (
    collect_graph_case,
    metric_plan,
    summarize,
)
from scripts.validate_agent_golden_dataset import validate_dataset


async def execute(args):
    from dotenv import load_dotenv

    for key in ("APP_DEBUG", "API_RESPONSE_LOGGING_ENABLED", "RAGAS_ONLINE_ENABLED"):
        os.environ[key] = "false"
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    load_dotenv(ROOT / "backend/.env", override=False)
    config_data = json.loads(args.config.read_text())
    config_data.update(
        live_execution_enabled=True,
        execution_scope="readonly_agent_graph",
        database_write_authorized=False,
        authentication_mode="dedicated_synthetic_account_not_configured",
        split=args.split,
    )
    config = EvaluationRuntime.model_validate(config_data)
    dataset = validate_dataset(
        json.loads((ROOT / config.dataset_path).read_text()),
        production_snapshot_path=Path(
            "/private/tmp/baseball-golden-production-db-snapshot.json"
        ),
    )
    if args.output.exists() or (args.raw_dir / "captures.json").exists():
        raise ValueError("existing run artifacts; no automatic paid rerun")
    if not args.raw_dir.resolve().is_relative_to(Path("/private/tmp")):
        raise ValueError("raw artifacts must be temporary")
    from sqlalchemy import text

    from app.agent.graph import BaseballAgentGraph
    from app.core.config import get_settings
    from app.core.database import async_session_factory, engine

    settings = get_settings()
    if (
        settings.openai_model != config.routing_model
        or (settings.openai_answer_model or settings.openai_model)
        != config.answer_model
    ):
        raise ValueError("runtime model drift")
    logging.getLogger().setLevel(logging.CRITICAL)
    for name in logging.Logger.manager.loggerDict:
        if name != "app.core.agent_trace":
            logging.getLogger(name).setLevel(logging.CRITICAL)
    traces = TraceCollector()
    logger = logging.getLogger("app.core.agent_trace")
    logger.setLevel(logging.INFO)
    logger.handlers = [traces]
    logger.propagate = False
    resources = EvaluationResources(config, api_key=settings.openai_api_key)
    captures = []
    metric_results = {}
    started = datetime.now(UTC).isoformat()
    try:
        for case in dataset.cases:
            if args.split != "all" and case.split != args.split:
                continue
            if not case.final_review.exploratory_candidate:
                continue
            if resources.budget.stopped:
                break
            current_evaluation_case.set(case.case_id)
            async with async_session_factory() as session:
                await session.execute(text("SET TRANSACTION READ ONLY"))
                readonly = await session.scalar(
                    text("select current_setting('transaction_read_only')")
                )
                if readonly != "on":
                    raise RuntimeError("readonly transaction not enforced")

                def factory(observer):
                    return BaseballAgentGraph(
                        tool_routing_service=resources.routing_service(),
                        tool_executor=executor(session, resources),
                        answer_generation_service=resources.answer_service(observer),
                    )

                captured = await collect_graph_case(
                    case,
                    dataset_sha256=dataset.content_sha256,
                    graph_factory=factory,
                    timeout_seconds=config.turn_timeout_seconds,
                )
                captures.append(captured)
                await session.rollback()
            save_private(
                args.raw_dir / "captures.json",
                {c.case_id: c.model_dump(mode="json") for c in captures},
            )
            save_private(args.raw_dir / "usage.json", resources.budget.observations)
            print(
                json.dumps(
                    {
                        "phase": "capture",
                        "case_id": case.case_id,
                        "graph_status": captured.status,
                        "origin": captured.response_origin,
                        "provider_requests": len(resources.budget.observations),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        metrics = resources.metrics()
        by_id = {c.case_id: c for c in captures}
        for case in dataset.cases:
            if case.case_id not in by_id:
                continue
            current_evaluation_case.set(case.case_id)
            metric_results[case.case_id] = await score_plan(
                metric_plan(case, by_id[case.case_id]),
                metrics,
                resources,
                config.judge_timeout_seconds,
            )
            save_private(args.raw_dir / "metrics.json", metric_results)
            save_private(args.raw_dir / "usage.json", resources.budget.observations)
            print(
                json.dumps(
                    {
                        "phase": "judge",
                        "case_id": case.case_id,
                        "statuses": {
                            k: v["status"]
                            for k, v in metric_results[case.case_id].items()
                        },
                        "provider_requests": len(resources.budget.observations),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    finally:
        summary = summarize(
            dataset,
            captures,
            split=args.split,
            not_run_reason="budget_stopped"
            if resources.budget.stopped
            else "capture_not_supplied",
        )
        for row in summary["results"]:
            key = row["case_id"]
            if key in metric_results:
                row["metrics"] = metric_results[key]
            usage = [u for u in resources.budget.observations if u["case_id"] == key]
            row["provider_usage"] = usage
            row["observed_usage_cost_upper_usd"] = round(
                sum(u["usage_cost_upper_usd"] or 0 for u in usage), 8
            )
            row["usage_missing_request_count"] = sum(
                u["usage_cost_upper_usd"] is None for u in usage
            )
            row["stage_traces"] = [t for t in traces.rows if t["case_id"] == key]
        ledger = ROOT / config.ledger_path
        ledger_state = json.loads(ledger.read_text()) if ledger.exists() else None
        summary.update(
            mode="readonly_agent_core_baseline",
            execution_scope="actual_agent_graph_live_pgvector_no_auth_sse_persistence",
            service_baseline=bool(captures),
            human_reviewed=False,
            ragas_executed=any(
                v["status"] == "scored"
                for c in metric_results.values()
                for v in c.values()
            ),
            run_started_at=started,
            run_finished_at=datetime.now(UTC).isoformat(),
            run_date="2026-10-15",
            runtime_corpus_verified=True,
            runtime_code_revision=dataset.code_revision,
            working_tree_dirty=True,
            runtime_model_configuration=config.model_dump(mode="json"),
            budget_ledger=ledger_state,
            observed_usage_cost_upper_usd=round(
                sum(
                    u["usage_cost_upper_usd"] or 0
                    for u in resources.budget.observations
                ),
                8,
            ),
            usage_missing_request_count=sum(
                u["usage_cost_upper_usd"] is None for u in resources.budget.observations
            ),
            provider_request_count=len(resources.budget.observations),
            database_writes=0,
            authentication="not_checked",
            sse_completion="not_checked",
            persistence="not_checked",
        )
        paths = (
            [
                "backend/scripts/execute_agent_golden_readonly.py",
                "backend/scripts/execute_agent_golden_baseline.py",
                "backend/scripts/agent_evaluation_runtime.py",
                "backend/scripts/run_agent_golden_evaluation.py",
            ]
            + [
                str(p.relative_to(ROOT))
                for p in (ROOT / "backend/app/agent").rglob("*.py")
            ]
            + [
                str(p.relative_to(ROOT))
                for p in (ROOT / "backend/app/agent/prompt_assets").glob("*.md")
            ]
        )
        summary["runtime_code_artifact_hashes"] = {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in sorted(set(paths))
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        await resources.aclose()
        await engine.dispose()
        print(
            json.dumps(
                {
                    "phase": "finished",
                    "captured": len(captures),
                    "provider_requests": len(resources.budget.observations),
                    "observed_usage_cost_upper_usd": summary[
                        "observed_usage_cost_upper_usd"
                    ],
                    "budget_reserved_usd": ledger_state["reserved_microusd"] / 1_000_000
                    if ledger_state
                    else 0,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--split", choices=["development", "held_out", "all"], default="development"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("explicit --execute required for authorized paid evaluation")
    try:
        asyncio.run(execute(args))
    except Exception as exc:  # noqa: BLE001 - no raw provider/credential exceptions
        print(
            json.dumps(
                {
                    "fatal_error_type": type(exc).__name__,
                    "message": "stopped without automatic retry; inspect content-free summary/budget",
                }
            ),
            flush=True,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
