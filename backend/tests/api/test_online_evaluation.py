from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import httpx
import pytest

from app.agent import online_evaluation as module
from app.agent.answer_schemas import AnswerEvaluationInput
from app.agent.online_evaluation import (
    JUDGE_MODEL,
    MAX_OUTPUT_TOKENS,
    BudgetedJudgeTransport,
    DailyEvaluationBudget,
    EvaluationBudgetExceeded,
    OnlineFaithfulnessEvaluator,
)


def item(**updates):
    data = {
        "user_input": "PRIVATE_QUESTION",
        "response": "PRIVATE_ANSWER",
        "tool_name": "search_stadium_guide",
        "contexts": ["PRIVATE_CONTEXT"],
    }
    data.update(updates)
    return AnswerEvaluationInput(**data)


def evaluator(tmp_path, **updates):
    args = {
        "api_key": "synthetic-not-a-real-key",
        "enabled": True,
        "sample_rate": 1,
        "daily_budget": DailyEvaluationBudget(tmp_path / "budget.json", 0.1),
    }
    args.update(updates)
    return OnlineFaithfulnessEvaluator(**args)


def test_budget_is_shared_atomic_and_survives_restart(tmp_path):
    path = tmp_path / "budget.json"
    budgets = [DailyEvaluationBudget(path, 0.0001) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = list(
            pool.map(lambda n: budgets[n % 2].reserve(20, day="2026-10-05"), range(20))
        )
    assert sum(accepted) == 5
    assert not DailyEvaluationBudget(path, 0.0001).reserve(1, day="2026-10-05")
    assert budgets[0].reserve(20, day="2026-10-06")
    assert not budgets[0].reserve(1, day="2026-10-05")
    assert json.loads(path.read_text()) == {
        "day": "2026-10-06",
        "reserved_microusd": 20,
    }


def test_corrupt_budget_fails_closed(tmp_path):
    path = tmp_path / "budget.json"
    path.write_text("{broken")
    with pytest.raises(ValueError):
        DailyEvaluationBudget(path, 0.1).reserve(1)
    assert path.read_text() == "{broken"


@pytest.mark.asyncio
async def test_transport_stops_before_network_when_budget_exhausted(tmp_path):
    called = []
    transport = BudgetedJudgeTransport(
        DailyEvaluationBudget(tmp_path / "budget.json", 0),
        httpx.MockTransport(lambda request: called.append(request)),
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(EvaluationBudgetExceeded):
            await client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": JUDGE_MODEL,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                },
            )
    assert not called


@pytest.mark.asyncio
async def test_failed_http_call_keeps_reservation_and_two_request_limit(tmp_path):
    path = tmp_path / "budget.json"
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(500, json={"error": {"message": "PRIVATE"}})

    transport = BudgetedJudgeTransport(
        DailyEvaluationBudget(path, 0.1), httpx.MockTransport(handle)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        for _ in range(2):
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": JUDGE_MODEL,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                },
            )
            assert response.status_code == 500
        with pytest.raises(EvaluationBudgetExceeded):
            await client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": JUDGE_MODEL,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                },
            )
    assert len(calls) == 2
    assert json.loads(path.read_text())["reserved_microusd"] > 0
    assert "PRIVATE" not in path.read_text()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,rate,tool",
    [
        (False, 1, "search_stadium_guide"),
        (True, 0, "search_stadium_guide"),
        (True, 1, "get_weather_context"),
    ],
)
async def test_disabled_unsampled_and_non_rag_make_no_calls(
    tmp_path, monkeypatch, enabled, rate, tool
):
    scorer = AsyncMock(return_value=1)
    monkeypatch.setattr(module, "evaluate_faithfulness", scorer)
    worker = evaluator(tmp_path, enabled=enabled, sample_rate=rate)
    worker.submit(item(tool_name=tool))
    await asyncio.sleep(0)
    await worker.close()
    scorer.assert_not_called()


@pytest.mark.asyncio
async def test_one_inflight_job_and_private_logs(tmp_path, monkeypatch, caplog):
    started, finish = asyncio.Event(), asyncio.Event()

    async def score(*args, **kwargs):
        started.set()
        await finish.wait()
        return 1

    monkeypatch.setattr(module, "evaluate_faithfulness", score)
    caplog.set_level("INFO", logger=module.__name__)
    worker = evaluator(tmp_path)
    worker.submit(item())
    await started.wait()
    worker.submit(item())
    finish.set()
    await asyncio.gather(*list(worker._tasks))
    await worker.close()
    assert '"score": 1' in caplog.text
    assert "worker_busy" in caplog.text
    assert "PRIVATE" not in caplog.text
    assert not worker._tasks


@pytest.mark.asyncio
async def test_judge_exception_timeout_and_shutdown_are_isolated(
    tmp_path, monkeypatch, caplog
):
    caplog.set_level("INFO", logger=module.__name__)
    monkeypatch.setattr(
        module,
        "evaluate_faithfulness",
        AsyncMock(side_effect=ValueError("PRIVATE_JUDGE")),
    )
    worker = evaluator(tmp_path)
    worker.submit(item())
    await asyncio.gather(*list(worker._tasks))
    assert "judge_error" in caplog.text and "PRIVATE_JUDGE" not in caplog.text

    async def wait(*args, **kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(module, "evaluate_faithfulness", wait)
    worker.timeout_seconds = 0.01
    worker.submit(item())
    await asyncio.gather(*list(worker._tasks))
    assert "judge_timeout" in caplog.text
    worker.timeout_seconds = 60
    worker.submit(item())
    await asyncio.sleep(0)
    await worker.close()
    assert "shutdown_cancelled" in caplog.text
    assert not worker._tasks


@pytest.mark.asyncio
async def test_actual_ragas_and_openai_path_uses_bounded_mock_http(
    tmp_path, monkeypatch
):
    calls = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        payload = (
            {"statements": ["PRIVATE_ANSWER"]}
            if len(calls) == 1
            else {
                "statements": [
                    {"statement": "PRIVATE_ANSWER", "reason": "supported", "verdict": 1}
                ]
            }
        )
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": JUDGE_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(payload),
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            },
        )

    real = BudgetedJudgeTransport
    monkeypatch.setattr(
        module,
        "BudgetedJudgeTransport",
        lambda budget: real(budget, httpx.MockTransport(handle)),
    )
    path = tmp_path / "budget.json"
    score = await module.evaluate_faithfulness(
        item(),
        api_key="synthetic-not-a-real-key",
        budget=DailyEvaluationBudget(path, 0.1),
    )
    assert score == 1
    assert len(calls) == 2
    assert all(call["max_tokens"] == 1024 for call in calls)
    assert "PRIVATE" not in path.read_text()


@pytest.mark.asyncio
async def test_budget_rejection_survives_sdk_instructor_wrapping(tmp_path, monkeypatch):
    real = BudgetedJudgeTransport
    monkeypatch.setattr(
        module,
        "BudgetedJudgeTransport",
        lambda budget: real(
            budget,
            httpx.MockTransport(lambda _: pytest.fail("network must not execute")),
        ),
    )
    with pytest.raises(EvaluationBudgetExceeded):
        await module.evaluate_faithfulness(
            item(),
            api_key="synthetic-not-a-real-key",
            budget=DailyEvaluationBudget(tmp_path / "budget.json", 0),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("draw,expected_calls", [(0.049, 1), (0.05, 0)])
async def test_five_percent_sampling_boundary(
    tmp_path, monkeypatch, draw, expected_calls
):
    scorer = AsyncMock(return_value=1)
    monkeypatch.setattr(module, "evaluate_faithfulness", scorer)
    monkeypatch.setattr(module.random, "random", lambda: draw)
    worker = evaluator(tmp_path, sample_rate=0.05)
    worker.submit(item())
    await asyncio.gather(*list(worker._tasks))
    await worker.close()
    assert scorer.call_count == expected_calls


@pytest.mark.asyncio
async def test_malformed_judge_output_is_not_retried_or_logged(
    tmp_path, monkeypatch, caplog
):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": JUDGE_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "PRIVATE_INVALID_OUTPUT",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            },
        )

    real = BudgetedJudgeTransport
    monkeypatch.setattr(
        module,
        "BudgetedJudgeTransport",
        lambda budget: real(budget, httpx.MockTransport(handle)),
    )
    caplog.set_level("DEBUG")
    worker = evaluator(tmp_path)
    worker.submit(item())
    await asyncio.gather(*list(worker._tasks))
    await worker.close()
    assert len(calls) == 1
    assert "PRIVATE" not in caplog.text
    assert "judge_error" in caplog.text
