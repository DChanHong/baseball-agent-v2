from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from scripts.agent_evaluation_api import (
    ApiFixture,
    collect_api_case,
    prepare_api_fixture,
)
from scripts.agent_evaluation_runtime import (
    BudgetStopped,
    BudgetTransport,
    EvaluationRuntime,
    RunBudget,
)
from scripts.run_agent_golden_evaluation import DEFAULT_DATASET, content_hash
from scripts.validate_agent_golden_dataset import validate_dataset

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "data/chat/evaluation/configs/agent_golden_baseline_v1.json"


@pytest.fixture
def config(tmp_path):
    original = EvaluationRuntime.model_validate_json(CONFIG.read_text())
    # Temporary mock ledger only, bypassing deployment path constraint deliberately.
    return original.model_copy(
        update={
            "ledger_path": str(tmp_path / "budget.json"),
            "live_execution_enabled": True,
            "database_write_authorized": True,
            "authentication_mode": "dedicated_synthetic_account",
        }
    )


@pytest.fixture
def target():
    return validate_dataset(json.loads(DEFAULT_DATASET.read_text())).cases[0]


def fixture(target):
    return ApiFixture(
        target.case_id,
        UUID(int=100),
        target.input.today,
        target.input.favorite_team_id,
        content_hash(target.input.conversation_context),
    )


def test_config_is_2_5_dollars_disabled_and_requires_auth_write_approval():
    data = json.loads(CONFIG.read_text())
    parsed = EvaluationRuntime.model_validate(data)
    assert parsed.budget_usd == 2.5 and not parsed.live_execution_enabled
    data["live_execution_enabled"] = True
    with pytest.raises(ValidationError):
        EvaluationRuntime.model_validate(data)
    data["budget_usd"] = 3
    with pytest.raises(ValidationError):
        EvaluationRuntime.model_validate(data)


def test_shared_limit_survives_restart_and_is_not_reset_when_stopped(config):
    first = RunBudget(config)
    assert first.reserve(2_000_000)
    second = RunBudget(config)
    assert second.reserve(250_000)
    assert not first.reserve(300_000)
    assert not RunBudget(config).reserve(1)
    saved = json.loads(Path(config.ledger_path).read_text())
    assert (
        saved["reserved_microusd"] == 2_250_000
        and saved["requests"] == 2
        and saved["stopped"]
    )
    assert Path(config.ledger_path).stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_atomic_shared_reservations(config):
    budgets = [RunBudget(config) for _ in range(10)]
    values = await asyncio.gather(
        *(asyncio.to_thread(b.reserve, 500_000) for b in budgets)
    )
    assert sum(values) == 5
    assert (
        json.loads(Path(config.ledger_path).read_text())["reserved_microusd"]
        == 2_500_000
    )


@pytest.mark.asyncio
async def test_guard_reserves_every_stage_and_keeps_network_failure(config):
    calls = []

    def respond(request):
        calls.append(request.url.path)
        if len(calls) == 3:
            raise httpx.ConnectError("PRIVATE", request=request)
        return httpx.Response(200, json={"synthetic": True})

    budget = RunBudget(config)
    async with httpx.AsyncClient(
        transport=BudgetTransport(
            budget, output_cap=4096, inner=httpx.MockTransport(respond)
        )
    ) as client:
        for model, path, fields in [
            (
                "gpt-5-mini",
                "chat/completions",
                {
                    "messages": [{"role": "user", "content": "合成"}],
                    "max_completion_tokens": 2048,
                },
            ),
            ("text-embedding-3-small", "embeddings", {"input": "public synthetic"}),
            (
                "gpt-4o-mini-2024-07-18",
                "chat/completions",
                {
                    "messages": [{"role": "user", "content": "PUBLIC"}],
                    "max_tokens": 1024,
                },
            ),
        ]:
            try:
                await client.post(
                    "https://api.openai.com/v1/" + path, json={"model": model, **fields}
                )
            except httpx.ConnectError:
                pass
    state = json.loads(Path(config.ledger_path).read_text())
    assert state["requests"] == 3 and state["reserved_microusd"] > 0
    assert calls == ["/v1/chat/completions", "/v1/embeddings", "/v1/chat/completions"]
    assert "PRIVATE" not in Path(config.ledger_path).read_text()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"max_tokens": None},
        {"max_tokens": 5000},
        {"model": "unpriced-model"},
        {"messages": [{"role": "user", "content": [{"type": "image_url"}]}]},
        {"service_tier": "flex"},
    ],
)
async def test_unbudgeted_requests_never_reach_provider(config, change):
    calls = []
    transport = BudgetTransport(
        RunBudget(config),
        output_cap=2048,
        inner=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(200)),
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(BudgetStopped):
            await client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-5-mini",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": "PUBLIC"}],
                    **change,
                },
            )
    assert not calls


@pytest.mark.asyncio
async def test_disabled_run_and_corrupt_ledger_fail_before_network(config):
    for value in [config.model_copy(update={"live_execution_enabled": False}), config]:
        Path(config.ledger_path).write_text("corrupt")
        calls = []
        async with httpx.AsyncClient(
            transport=BudgetTransport(
                RunBudget(value),
                output_cap=2048,
                inner=httpx.MockTransport(
                    lambda r, calls=calls: calls.append(r) or httpx.Response(200)
                ),
            )
        ) as client:
            with pytest.raises(BudgetStopped):
                await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json={
                        "model": "gpt-5-mini",
                        "max_tokens": 2048,
                        "messages": [{"role": "user", "content": "PUBLIC"}],
                    },
                )
        assert not calls


def stream_body(
    conversation_id,
    *,
    final="PUBLIC ANSWER",
    delta="PUBLIC ANSWER",
    done=True,
    failed=False,
):
    rows = [
        ("assistant.delta", {"message_id": str(UUID(int=200)), "delta": delta}),
        ("assistant.completed", {"message_id": str(UUID(int=200)), "content": final}),
    ]
    if failed:
        rows.append(("stream.failed", {"error": {"message": "PRIVATE"}}))
    if done:
        rows.append(("done", {"conversation_id": str(conversation_id)}))
    return "".join(
        "event: " + name + "\ndata: " + json.dumps(body) + "\n\n" for name, body in rows
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,reason",
    [
        ("valid", None),
        ("401", "unauthenticated"),
        ("truncated", "incomplete_or_failed_sse"),
        ("failed", "incomplete_or_failed_sse"),
        ("delta", "delta_completed_mismatch"),
        ("saved_mismatch", "persisted_message_mismatch"),
        ("wrong_conversation", "api_contract_or_transport_error"),
    ],
)
async def test_api_sse_and_scoped_persistence(target, mode, reason):
    f = fixture(target)
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "POST":
            assert json.loads(request.content)["message"] == target.input.question
            if mode == "401":
                return httpx.Response(401)
            body = stream_body(
                UUID(int=101) if mode == "wrong_conversation" else f.conversation_id,
                done=mode != "truncated",
                failed=mode == "failed",
                delta="different" if mode == "delta" else "PUBLIC ANSWER",
            )
            return httpx.Response(
                200, text=body, headers={"content-type": "text/event-stream"}
            )
        assert str(f.conversation_id) in request.url.path
        return httpx.Response(
            200,
            json={
                "messages": [
                    {
                        "id": str(UUID(int=199)),
                        "role": "user",
                        "content": target.input.question,
                        "status": "completed",
                    },
                    {
                        "id": str(UUID(int=200)),
                        "role": "assistant",
                        "content": "different"
                        if mode == "saved_mismatch"
                        else "PUBLIC ANSWER",
                        "status": "completed",
                    },
                ]
            },
        )

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:4000", transport=httpx.MockTransport(handle)
    ) as client:
        result = await collect_api_case(client, target, fixture=f)
    assert result.reason_code == reason
    if mode == "valid":
        assert (
            result.status == "completed"
            and result.sse_completion == result.persistence == "passed"
        )
    else:
        assert result.status == "error"
    assert len(requests) == (2 if mode in {"valid", "saved_mismatch"} else 1)
    assert (
        "PUBLIC ANSWER" not in result.model_dump_json()
        and str(f.conversation_id) not in result.model_dump_json()
    )
    assert result.model_capture == "not_available_from_public_sse"


@pytest.mark.asyncio
async def test_fixture_mismatch_sends_no_question(target):
    f = replace(fixture(target), favorite_team_id="NC")
    calls = []
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:4000",
        transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(200)),
    ) as client:
        result = await collect_api_case(client, target, fixture=f)
        with pytest.raises(ValueError):
            await prepare_api_fixture(client, target, runtime_today=target.input.today)
    assert result.reason_code == "fixture_mismatch" and not calls


@pytest.mark.asyncio
async def test_explicit_fixture_writes_only_new_context_not_profile(target):
    calls = []

    def handle(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"user": {"favoriteTeam": None}})
        body = json.loads(request.content)
        return httpx.Response(
            200, json={"id": str(UUID(int=100)), "metadata": body["metadata"]}
        )

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:4000", transport=httpx.MockTransport(handle)
    ) as client:
        f = await prepare_api_fixture(
            client,
            target,
            runtime_today=target.input.today,
            database_write_authorized=True,
            dedicated_synthetic_account=True,
        )
    assert f.case_id == target.case_id
    assert [r.method for r in calls] == ["GET", "POST"]
    assert calls[-1].url.path == "/api/v1/conversations"


@pytest.mark.asyncio
async def test_budgeted_sdk_clients_wire_actual_routing_answer_and_embedding(
    config, monkeypatch
):
    from datetime import date
    from types import SimpleNamespace

    import app.agent.answer_generation_service as answer_module
    import app.agent.routing_service as routing_module
    import scripts.agent_evaluation_runtime as module
    from app.agent.routing_schemas import ToolRoutingUserContext
    from scripts.run_agent_golden_evaluation import GenerationCapture

    bodies = []

    def handle(request):
        body = json.loads(request.content)
        bodies.append(body)
        if request.url.path.endswith("embeddings"):
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [
                        {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}
                    ],
                    "model": "text-embedding-3-small",
                    "usage": {"prompt_tokens": 2, "total_tokens": 2},
                },
            )
        if body["response_format"]["json_schema"]["name"] == "ToolRoutingDecision":
            value = {
                "is_in_scope": True,
                "should_call_tool": False,
                "tool_name": None,
                "args": None,
                "needs_clarification": False,
                "clarification_reason": None,
                "unsupported_reason": None,
                "direct_answer_intent": None,
            }
        else:
            value = {
                "answerability": "fully_answerable",
                "answer": "PUBLIC ANSWER",
                "used_evidence_refs": ["E1"],
                "acknowledged_limitations": [],
            }
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(value)},
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            },
        )

    original = BudgetTransport
    monkeypatch.setattr(
        module,
        "BudgetTransport",
        lambda budget, output_cap: original(
            budget, output_cap=output_cap, inner=httpx.MockTransport(handle)
        ),
    )
    settings = SimpleNamespace(
        openai_api_key="synthetic-not-real",
        openai_model="gpt-5-mini",
        openai_answer_model="gpt-5-mini",
        openai_answer_reasoning_effort="low",
        openai_answer_timeout_seconds=15,
        openai_timeout_seconds=30,
    )
    monkeypatch.setattr(routing_module, "get_settings", lambda: settings)
    monkeypatch.setattr(answer_module, "get_settings", lambda: settings)
    resources = module.EvaluationResources(config, api_key="synthetic-not-real")
    observer = GenerationCapture()
    try:
        await resources.routing_service().execute(
            message="PUBLIC QUESTION",
            user_context=ToolRoutingUserContext(
                auth_status="authenticated",
                favorite_team_id=None,
                today=date(2026, 10, 14),
                timezone="Asia/Seoul",
                conversation_context={},
            ),
        )
        await resources.answer_service(observer).execute(
            message="PUBLIC QUESTION",
            tool_payload={
                "name": "search_stadium_guide",
                "status": "completed",
                "result": {"items": [{"content": "PUBLIC SOURCE"}]},
            },
            tool_limitations=[],
        )
        await resources.embedding_client.embeddings.create(
            model="text-embedding-3-small", input="PUBLIC QUESTION"
        )
        assert len(resources.metrics()) == 4
    finally:
        await resources.aclose()
    assert len(bodies) == 3
    assert bodies[0]["max_completion_tokens"] == 2048
    assert bodies[1]["max_completion_tokens"] == 4096
    assert observer.model_response == "PUBLIC ANSWER"
    assert json.loads(Path(config.ledger_path).read_text())["requests"] == 3
