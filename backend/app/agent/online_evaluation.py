"""Sampled, bounded, post-response Faithfulness evaluation without content storage."""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import math
import os
import random
from contextvars import Context
from datetime import date, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from openai import AsyncOpenAI

from app.agent.answer_schemas import AnswerEvaluationInput

logger = logging.getLogger(__name__)
JUDGE_MODEL = "gpt-4o-mini-2024-07-18"
MAX_OUTPUT_TOKENS = 1024
RAG_TOOLS = {
    "search_stadium_guide",
    "search_ticketing_guide",
    "search_baseball_knowledge",
}


class EvaluationBudgetExceeded(Exception):
    """An evaluation request was refused before contacting the provider."""


class EvaluationBudgetUnavailable(Exception):
    """The ledger cannot safely authorize a request."""


class DailyEvaluationBudget:
    """Conservative reservations shared across processes on one persistent volume.

    A failed/incomplete call keeps its reservation. No content or identity is written.
    Corruption/IO failure fails closed; restarting cannot reset the current day's spend.
    """

    def __init__(self, path: Path, daily_limit_usd: float) -> None:
        self.path = path
        self.limit_microusd = math.floor(daily_limit_usd * 1_000_000)

    def reserve(self, amount_microusd: int, *, day: str | None = None) -> bool:
        if amount_microusd <= 0:
            raise ValueError("reservation must be positive")
        today = day or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as ledger:
            fcntl.flock(ledger, fcntl.LOCK_EX)
            raw = ledger.read()
            state = json.loads(raw) if raw else {"day": today, "reserved_microusd": 0}
            saved_day = state["day"]
            reserved = state["reserved_microusd"]
            if (
                not isinstance(saved_day, str)
                or type(reserved) is not int
                or reserved < 0
            ):
                raise ValueError("invalid budget ledger")
            date.fromisoformat(saved_day)
            if saved_day > today:
                return False
            if saved_day < today:
                reserved = 0
            if reserved + amount_microusd > self.limit_microusd:
                return False
            ledger.seek(0)
            ledger.write(
                json.dumps(
                    {"day": today, "reserved_microusd": reserved + amount_microusd}
                )
            )
            ledger.truncate()
            ledger.flush()
            os.fsync(ledger.fileno())
            return True


class BudgetedJudgeTransport(httpx.AsyncBaseTransport):
    """Reserve an upper estimate immediately before each actual HTTP request."""

    def __init__(
        self,
        budget: DailyEvaluationBudget,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.budget = budget
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)
        self.requests = 0
        self.stop_reason: str | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Locked model/prices, endpoint, output size and no provider/Instructor retries.
        body = json.loads(request.content)
        if (
            request.url.host != "api.openai.com"
            or request.url.path != "/v1/chat/completions"
            or body.get("model") != JUDGE_MODEL
            or body.get("max_tokens") != MAX_OUTPUT_TOKENS
            or self.requests >= 2
            or len(request.content) > 128_000
        ):
            self.stop_reason = "budget_or_request_limit"
            raise EvaluationBudgetExceeded
        # USD per million tokens: input .15/output .60. Body bytes overestimate input
        # tokens; 1024 extra input tokens cover chat framing. No discount assumption.
        reservation = math.ceil(
            (len(request.content) + 1024) * 0.15 + MAX_OUTPUT_TOKENS * 0.60
        )
        try:
            allowed = await asyncio.to_thread(self.budget.reserve, reservation)
        except (OSError, ValueError, KeyError, TypeError):
            self.stop_reason = "budget_unavailable"
            raise EvaluationBudgetUnavailable from None
        if not allowed:
            self.stop_reason = "budget_or_request_limit"
            raise EvaluationBudgetExceeded
        self.requests += 1
        return await self.inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self.inner.aclose()


def _build_faithfulness(client: AsyncOpenAI) -> Any:
    # Disable analytics before the first lazy RAGAS import. Keep provider internals
    # silent, including schema/retry errors which can contain a user's answer.
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    for prefix in ("ragas", "instructor", "openai", "httpx", "httpcore"):
        logging.getLogger(prefix).setLevel(logging.CRITICAL)
        for name, instance in logging.Logger.manager.loggerDict.copy().items():
            if name.startswith(prefix + ".") and isinstance(instance, logging.Logger):
                instance.setLevel(logging.CRITICAL)
    from importlib.metadata import version

    if version("ragas") != "0.4.3":
        raise RuntimeError("unsupported_ragas_version")
    from ragas.llms import llm_factory
    from ragas.metrics.collections import Faithfulness

    llm = llm_factory(
        JUDGE_MODEL,
        client=client,
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS,
        max_retries=0,
    )
    return Faithfulness(llm=llm)


async def evaluate_faithfulness(
    item: AnswerEvaluationInput,
    *,
    api_key: str,
    budget: DailyEvaluationBudget,
) -> float:
    transport = BudgetedJudgeTransport(budget)
    try:
        async with (
            httpx.AsyncClient(transport=transport) as http,
            AsyncOpenAI(
                api_key=api_key, timeout=20, max_retries=0, http_client=http
            ) as client,
        ):
            metric = await asyncio.to_thread(_build_faithfulness, client)
            result = await metric.ascore(
                user_input=item.user_input,
                response=item.response,
                retrieved_contexts=item.contexts,
            )
    except Exception:
        if transport.stop_reason == "budget_unavailable":
            raise EvaluationBudgetUnavailable from None
        if transport.stop_reason is not None:
            raise EvaluationBudgetExceeded from None
        raise
    value = result.value
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError("undefined_score")
    return float(value)


class OnlineFaithfulnessEvaluator:
    """Best-effort sampling; one in-flight job, no durable queue or raw transcripts."""

    def __init__(
        self,
        *,
        api_key: str,
        enabled: bool,
        sample_rate: float,
        daily_budget: DailyEvaluationBudget,
        timeout_seconds: float = 45,
    ) -> None:
        self.api_key = api_key
        self.enabled = enabled
        self.sample_rate = sample_rate
        self.budget = daily_budget
        self.timeout_seconds = timeout_seconds
        self._tasks: set[asyncio.Task[None]] = set()
        self._closed = False

    def submit(self, item: AnswerEvaluationInput) -> None:
        if not self.enabled or self._closed or self.budget.limit_microusd == 0:
            return
        if (
            item.tool_name not in RAG_TOOLS
            or not item.contexts
            or not item.response.strip()
        ):
            return
        if random.random() >= self.sample_rate:
            return
        if self._tasks:
            self._log(
                status="excluded", score=None, error_code="worker_busy", duration_ms=0
            )
            return
        task = asyncio.create_task(self._run(item), context=Context())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, item: AnswerEvaluationInput) -> None:
        started = perf_counter()
        score = None
        status, error_code = "error", None
        try:
            async with asyncio.timeout(self.timeout_seconds):
                score = await evaluate_faithfulness(
                    item, api_key=self.api_key, budget=self.budget
                )
            status = "scored"
        except asyncio.CancelledError:
            error_code = "shutdown_cancelled"
        except TimeoutError:
            error_code = "judge_timeout"
        except EvaluationBudgetExceeded:
            status, error_code = "excluded", "budget_or_request_limit"
        except EvaluationBudgetUnavailable:
            error_code = "budget_unavailable"
        except Exception:  # noqa: BLE001 - never log judge exceptions or raw output
            error_code = "judge_error"
        finally:
            # No prompt, response, contexts, refs, user/conversation IDs, or exception text.
            self._log(
                status=status,
                score=score,
                error_code=error_code,
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )

    @staticmethod
    def _log(**fields: Any) -> None:
        logger.info("ragas_online %s", json.dumps({"metric": "faithfulness", **fields}))

    async def close(self) -> None:
        self._closed = True
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
