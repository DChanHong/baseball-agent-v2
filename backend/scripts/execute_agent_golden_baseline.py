"""Explicit one-pass authenticated ASGI/DB baseline with a shared USD ceiling.

No work occurs on import. --execute acknowledges the configured run; every paid
request goes through EvaluationResources. Only newly created synthetic account data
is written/deleted. Raw synthetic artifacts stay in the supplied temporary directory.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import secrets
import sys
from contextlib import aclosing
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.agent_evaluation_api import collect_api_case, prepare_api_fixture
from scripts.agent_evaluation_runtime import (
    EvaluationResources,
    EvaluationRuntime,
    current_evaluation_case,
)
from scripts.run_agent_golden_evaluation import (
    Capture,
    GenerationCapture,
    content_hash,
    graph_input,
    metric_plan,
    summarize,
)
from scripts.validate_agent_golden_dataset import validate_dataset


def save_private(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)


class TraceCollector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.rows = []

    def emit(self, record):
        message = record.getMessage()
        if message.startswith("agent_trace "):
            value = json.loads(message[len("agent_trace ") :])
            value.pop("trace_id", None)
            self.rows.append({"case_id": current_evaluation_case.get(), **value})


class CapturingGraph:
    def __init__(self, graph, case, observer, store, dataset_hash):
        self.graph = graph
        self.case = case
        self.observer = observer
        self.store = store
        self.dataset_hash = dataset_hash

    async def astream(self, actual):
        expected = graph_input(self.case)
        if (
            actual.user_message != expected.user_message
            or actual.favorite_team_id != expected.favorite_team_id
            or actual.context != expected.context
        ):
            raise ValueError("API fixture differs from fixed case")
        # Explicit adapter: preserve the authored 2026-10-14 case date on a live API.
        actual = actual.model_copy(update={"today": expected.today})
        row = {
            "case_id": self.case.case_id,
            "dataset_sha256": self.dataset_hash,
            "status": "error",
            "reason_code": "missing_completed_event",
            "duration_ms": 0,
        }
        started = perf_counter()
        try:
            async with aclosing(self.graph.astream(actual)) as stream:
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
                        row["retrieval_items"] = (payload.get("result") or {}).get(
                            "items", []
                        )
                    if event.kind == "completed" and event.output is not None:
                        row.update(
                            status="completed",
                            reason_code=None,
                            response_origin=event.output.answer_source,
                            final_response=event.output.answer,
                        )
                    yield event
        finally:
            row.update(
                duration_ms=round((perf_counter() - started) * 1000, 3),
                generation_evidence=self.observer.evidence,
                model_response=self.observer.model_response,
            )
            self.store[self.case.case_id] = Capture.model_validate(row)


def executor(session, resources):
    from app.agent.tool_executor import AgentToolExecutor
    from app.api.dependencies import (
        get_find_kbo_game_tool_handler,
        get_stadium_info_tool_handler,
        get_weather_context_tool_handler,
    )
    from app.domains.baseball.tool.rag_config import (
        BASEBALL_KNOWLEDGE_RAG_CONFIG,
        STADIUM_GUIDE_RAG_CONFIG,
        TICKETING_GUIDE_RAG_CONFIG,
    )
    from app.domains.baseball.tool.search_baseball_knowledge.handler import (
        SearchBaseballKnowledgeToolHandler,
    )
    from app.domains.baseball.tool.search_baseball_knowledge.retriever import (
        PgVectorBaseballKnowledgeRetriever,
    )
    from app.domains.baseball.tool.search_stadium_guide.handler import (
        SearchStadiumGuideToolHandler,
    )
    from app.domains.baseball.tool.search_stadium_guide.retriever import (
        PgVectorStadiumGuideRetriever,
    )
    from app.domains.baseball.tool.search_ticketing_guide.handler import (
        SearchTicketingGuideToolHandler,
    )

    return AgentToolExecutor(
        find_kbo_game_handler=get_find_kbo_game_tool_handler(session),
        get_stadium_info_handler=get_stadium_info_tool_handler(session),
        get_weather_context_handler=get_weather_context_tool_handler(),
        search_stadium_guide_handler=SearchStadiumGuideToolHandler(
            openai_client=resources.embedding_client,
            retriever=PgVectorStadiumGuideRetriever(session),
            retrieval_config=STADIUM_GUIDE_RAG_CONFIG,
        ),
        search_ticketing_guide_handler=SearchTicketingGuideToolHandler(
            openai_client=resources.embedding_client,
            retriever=PgVectorStadiumGuideRetriever(session),
            retrieval_config=TICKETING_GUIDE_RAG_CONFIG,
        ),
        search_baseball_knowledge_handler=SearchBaseballKnowledgeToolHandler(
            openai_client=resources.embedding_client,
            retriever=PgVectorBaseballKnowledgeRetriever(session),
            retrieval_config=BASEBALL_KNOWLEDGE_RAG_CONFIG,
        ),
    )


async def score_plan(plan, metrics, resources, timeout):
    result = {}
    for name, entry in plan.items():
        row = {"value": None, "duration_ms": 0}
        if entry["status"] == "excluded":
            row.update(status="excluded", reason_code=entry["reason_code"])
        elif resources.budget.stopped:
            row.update(status="not_run", reason_code="budget_stopped")
        else:
            started = perf_counter()
            try:
                async with asyncio.timeout(timeout):
                    scored = await metrics[name].ascore(**entry["kwargs"])
                if (
                    isinstance(scored.value, bool)
                    or not isinstance(scored.value, int | float)
                    or not math.isfinite(scored.value)
                ):
                    row.update(status="error", reason_code="undefined_score")
                else:
                    row.update(
                        status="scored", reason_code=None, value=float(scored.value)
                    )
            except TimeoutError:
                row.update(status="error", reason_code="judge_timeout")
            except Exception:  # noqa: BLE001 - content-free per-metric isolation
                row.update(
                    status="error",
                    reason_code="budget_stopped"
                    if resources.budget.stopped
                    else "judge_error",
                )
            row["duration_ms"] = round((perf_counter() - started) * 1000, 3)
        result[name] = row
    return result


async def execute(args):
    from dotenv import load_dotenv

    for key in ("APP_DEBUG", "API_RESPONSE_LOGGING_ENABLED", "RAGAS_ONLINE_ENABLED"):
        os.environ[key] = "false"
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    load_dotenv(ROOT / "backend/.env", override=False)
    config_data = json.loads(args.config.read_text())
    config_data.update(
        live_execution_enabled=True,
        database_write_authorized=True,
        authentication_mode="dedicated_synthetic_account",
        split=args.split,
    )
    config = EvaluationRuntime.model_validate(config_data)
    dataset = validate_dataset(
        json.loads((ROOT / config.dataset_path).read_text()),
        production_snapshot_path=Path(
            "/private/tmp/baseball-golden-production-db-snapshot.json"
        ),
    )
    snapshot = json.loads(
        Path("/private/tmp/baseball-golden-production-db-snapshot.json").read_text()
    )
    documents = {d["document_id"]: d for d in snapshot["documents"]}
    chunks = {c["chunk_id"]: c for c in snapshot["chunks"]}
    for expected in dataset.production_corpus_snapshot.manifest["documents"]:
        if any(
            documents[expected["document_id"]].get(key) != value
            for key, value in expected.items()
        ):
            raise ValueError("runtime document snapshot drift")
    for expected in dataset.production_corpus_snapshot.manifest["chunks"]:
        actual = chunks[expected["chunk_id"]]
        for key, value in expected.items():
            observed = (
                content_hash(actual["metadata"])
                if key == "metadata_sha256"
                else content_hash(actual["source_urls"])
                if key == "source_urls_sha256"
                else hashlib.sha256(actual["content"].encode()).hexdigest()
                if key == "observed_content_sha256"
                else actual.get(key)
            )
            if observed != value:
                raise ValueError("runtime chunk snapshot drift")
    raw_dir = args.raw_dir.resolve()
    if not raw_dir.is_relative_to(Path("/private/tmp")):
        raise ValueError("raw artifacts must be temporary")
    if (raw_dir / "captures.json").exists() or args.output.exists():
        raise ValueError("run output already exists; do not repeat paid cases")
    raw_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    from sqlalchemy import text

    from app.agent.graph import BaseballAgentGraph
    from app.api.dependencies import get_chat_stream_service
    from app.core.config import get_settings
    from app.core.database import async_session_factory, engine, get_db_session
    from app.domains.auth.infrastructure.repositories import (
        SqlAlchemyUserProfileRepository,
    )
    from app.domains.chat.service.services import ChatStreamService
    from app.domains.conversation.infrastructure.repositories import (
        SqlAlchemyConversationRepository,
        SqlAlchemyMessageRepository,
    )
    from app.main import app

    s = get_settings()
    if s.ragas_online_enabled or s.api_response_logging_enabled or s.app_debug:
        raise ValueError("unsafe evaluation process flags")
    if s.supabase_url != "https://ztopdfbdvspzatbrcwif.supabase.co":
        raise ValueError("unexpected production target")
    # Suppress provider/raw exception logs; collect content-free agent stages only.
    logging.getLogger().setLevel(logging.CRITICAL)
    for name in logging.Logger.manager.loggerDict:
        if name != "app.core.agent_trace":
            logging.getLogger(name).setLevel(logging.CRITICAL)
    traces = TraceCollector()
    trace_logger = logging.getLogger("app.core.agent_trace")
    trace_logger.setLevel(logging.INFO)
    trace_logger.handlers = [traces]
    trace_logger.propagate = False
    resources = EvaluationResources(config, api_key=s.openai_api_key)
    store = {}
    api_checks = {}
    metric_results = {}
    active = [dataset.cases[0]]
    profile_id = None
    auth_id = None
    cleanup = {
        "synthetic_conversations_deleted": 0,
        "synthetic_profile_deleted": False,
        "synthetic_auth_deleted": False,
    }
    started = datetime.now(UTC).isoformat()
    auth_headers = {
        "apikey": s.supabase_service_role_key,
        "Authorization": "Bearer " + s.supabase_service_role_key,
    }

    db_dependency = Depends(get_db_session)

    async def make_service(request: Request, session=db_dependency):
        case = active[0]
        if case is None:
            raise ValueError("no selected evaluation case")
        observer = GenerationCapture()
        graph = BaseballAgentGraph(
            tool_routing_service=resources.routing_service(),
            tool_executor=executor(session, resources),
            answer_generation_service=resources.answer_service(observer),
        )
        return ChatStreamService(
            conversation_repository=SqlAlchemyConversationRepository(session),
            message_repository=SqlAlchemyMessageRepository(session),
            agent_graph=CapturingGraph(
                graph, case, observer, store, dataset.content_sha256
            ),
            session=session,
            online_evaluator=None,
        )

    app.dependency_overrides[get_chat_stream_service] = make_service
    report = {}
    try:
        async with httpx.AsyncClient(base_url=s.supabase_url, timeout=20) as auth:
            suffix = uuid4().hex
            email = f"golden-{suffix}@example.invalid"
            password = secrets.token_urlsafe(32)
            response = await auth.post(
                "/auth/v1/admin/users",
                headers=auth_headers,
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"synthetic_evaluation": True},
                },
            )
            if response.status_code not in (200, 201):
                raise RuntimeError("synthetic_auth_create_failed")
            auth_id = UUID(response.json()["id"])
            async with async_session_factory() as session:
                profile = await SqlAlchemyUserProfileRepository(session).create(
                    auth_user_id=auth_id,
                    nickname="eval_" + suffix[:16],
                    encrypted_email=None,
                )
                profile_id = profile.id
                await session.commit()
            response = await auth.post(
                "/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": s.supabase_anon_key},
                json={"email": email, "password": password},
            )
            if response.status_code != 200:
                raise RuntimeError("synthetic_login_failed")
            token = response.json()["access_token"]
            del password
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:4000",
            timeout=config.turn_timeout_seconds,
        ) as client:
            # Confirm unauthenticated rejection via the actual auth dependency.
            unauth = await client.post(
                "/api/v1/chat", json={"message": "합성 인증 검사"}
            )
            report["unauthenticated_http_status"] = unauth.status_code
            if unauth.status_code != 401:
                raise RuntimeError("authentication_boundary_failed")
            client.cookies.set(s.auth_access_cookie_name, token)
            del token
            me = await client.get("/api/v1/auth/me")
            if me.status_code != 200 or me.json()["user"]["id"] != str(profile_id):
                raise RuntimeError("dedicated_profile_identity_mismatch")
            for case in dataset.cases:
                if args.split != "all" and case.split != args.split:
                    continue
                if not case.final_review.exploratory_candidate:
                    continue
                if resources.budget.stopped:
                    break
                active[0] = case
                current_evaluation_case.set(case.case_id)
                patch = await client.patch(
                    "/api/v1/auth/me",
                    json={"favoriteTeam": case.input.favorite_team_id},
                )
                if patch.status_code != 200:
                    raise RuntimeError("synthetic_profile_fixture_failed")
                fixture = await prepare_api_fixture(
                    client,
                    case,
                    runtime_today=case.input.today,
                    database_write_authorized=True,
                    dedicated_synthetic_account=True,
                )
                api_checks[case.case_id] = (
                    await collect_api_case(
                        client,
                        case,
                        fixture=fixture,
                        timeout_seconds=config.turn_timeout_seconds,
                    )
                ).model_dump()
                save_private(
                    raw_dir / "captures.json",
                    {
                        key: value.model_dump(mode="json")
                        for key, value in store.items()
                    },
                )
                save_private(raw_dir / "usage.json", resources.budget.observations)
                print(
                    json.dumps(
                        {
                            "phase": "capture",
                            "case_id": case.case_id,
                            "api_status": api_checks[case.case_id]["status"],
                            "graph_status": store[case.case_id].status
                            if case.case_id in store
                            else None,
                            "origin": store[case.case_id].response_origin
                            if case.case_id in store
                            else None,
                            "provider_requests": len(resources.budget.observations),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            metrics = resources.metrics()
            for case in dataset.cases:
                if case.case_id not in store:
                    continue
                current_evaluation_case.set(case.case_id)
                metric_results[case.case_id] = await score_plan(
                    metric_plan(case, store[case.case_id]),
                    metrics,
                    resources,
                    config.judge_timeout_seconds,
                )
                save_private(raw_dir / "metrics.json", metric_results)
                save_private(raw_dir / "usage.json", resources.budget.observations)
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
        app.dependency_overrides.pop(get_chat_stream_service, None)
        # Only resources created for this run are eligible for cleanup.
        if profile_id is not None:
            async with async_session_factory() as session:
                deleted = await session.execute(
                    text(
                        "delete from public.chat_conversations where user_profile_id=:profile_id returning id"
                    ),
                    {"profile_id": profile_id},
                )
                cleanup["synthetic_conversations_deleted"] = len(deleted.all())
                await session.execute(
                    text(
                        "delete from public.user_profiles where id=:profile_id and auth_user_id=:auth_id"
                    ),
                    {"profile_id": profile_id, "auth_id": auth_id},
                )
                await session.commit()
                cleanup["synthetic_profile_deleted"] = True
        if auth_id is not None:
            async with httpx.AsyncClient(base_url=s.supabase_url, timeout=20) as auth:
                result = await auth.delete(
                    f"/auth/v1/admin/users/{auth_id}", headers=auth_headers
                )
                cleanup["synthetic_auth_deleted"] = result.status_code in (200, 204)
        summary = summarize(
            dataset,
            list(store.values()),
            split=args.split,
            not_run_reason="budget_stopped"
            if resources.budget.stopped
            else "capture_not_supplied",
        )
        for row in summary["results"]:
            key = row["case_id"]
            if key in api_checks:
                row.update(
                    sse_completion=api_checks[key]["sse_completion"],
                    persistence=api_checks[key]["persistence"],
                    api_status=api_checks[key]["status"],
                    api_reason_code=api_checks[key]["reason_code"],
                )
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
        ledger = Path(config.ledger_path)
        if not ledger.is_absolute():
            ledger = ROOT / ledger
        ledger_state = json.loads(ledger.read_text()) if ledger.exists() else None
        summary.update(
            mode="authenticated_asgi_fixed_context_baseline",
            execution_scope="actual_auth_sse_db_in_process_asgi_not_browser",
            service_baseline=True,
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
            fixed_case_date_override="2026-10-14",
            cleanup=cleanup,
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
            preflight=report,
        )
        code_paths = (
            [
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
            for p in sorted(set(code_paths))
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        save_private(raw_dir / "api_checks.json", api_checks)
        await resources.aclose()
        await engine.dispose()
        print(
            json.dumps(
                {
                    "phase": "finished",
                    "captured": len(store),
                    "provider_requests": len(resources.budget.observations),
                    "observed_usage_cost_upper_usd": summary[
                        "observed_usage_cost_upper_usd"
                    ],
                    "budget_reserved_usd": ledger_state["reserved_microusd"] / 1_000_000
                    if ledger_state
                    else 0,
                    "cleanup": cleanup,
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
        parser.error("explicit --execute required for authorized paid/DB execution")
    try:
        asyncio.run(execute(args))
    except Exception as exc:  # noqa: BLE001 - never expose credentials or raw provider errors
        print(
            json.dumps(
                {
                    "fatal_error_type": type(exc).__name__,
                    "message": "execution stopped; inspect content-free summary and budget; no automatic retry",
                }
            ),
            flush=True,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
