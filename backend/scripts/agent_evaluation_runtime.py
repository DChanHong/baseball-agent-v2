"""Explicit evaluation configuration and a shared request-level budget guard."""

from __future__ import annotations

import asyncio
import fcntl
import json
import math
import os
from contextvars import ContextVar
from pathlib import Path
from time import perf_counter
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

current_evaluation_case: ContextVar[str | None] = ContextVar(
    "current_evaluation_case", default=None
)


class ModelPrice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_usd_per_million: float = Field(gt=0, allow_inf_nan=False)
    output_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    source_url: str


class EvaluationRuntime(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=r"^[a-z0-9_-]+$")
    budget_usd: float = Field(gt=0, le=2.5, allow_inf_nan=False)
    budget_authorized: Literal[True] = True
    live_execution_enabled: bool = False
    execution_scope: Literal["authenticated_api", "readonly_agent_graph"] = (
        "authenticated_api"
    )
    api_base_url: Literal["http://127.0.0.1:4000"]
    dataset_path: str
    split: Literal["development", "held_out", "all"]
    attempts_per_case: Literal[1] = 1
    concurrency: Literal[1] = 1
    online_evaluation_enabled: Literal[False] = False
    api_response_logging_enabled: Literal[False] = False
    provider_retries: Literal[0] = 0
    judge_retries: Literal[0] = 0
    routing_model: Literal["gpt-5-mini"]
    answer_model: Literal["gpt-5-mini"]
    answer_reasoning_effort: Literal["low"]
    knowledge_answer_reasoning_effort: Literal["medium"]
    answer_timeout_seconds: Literal[15] = 15
    provider_timeout_seconds: Literal[30] = 30
    turn_timeout_seconds: Literal[60] = 60
    judge_timeout_seconds: Literal[30] = 30
    judge_model: Literal["gpt-4o-mini-2024-07-18"]
    embedding_model: Literal["text-embedding-3-small"]
    routing_max_output_tokens: int = Field(gt=0, le=2048)
    answer_max_output_tokens: int = Field(gt=0, le=4096)
    judge_max_output_tokens: int = Field(gt=0, le=2048)
    max_provider_requests: int = Field(gt=0, le=1024)
    max_request_bytes: int = Field(gt=0, le=128000)
    ledger_path: str
    prices_checked_at: str
    prices: dict[str, ModelPrice]
    database_write_authorized: bool = False
    authentication_mode: Literal[
        "dedicated_synthetic_account_not_configured", "dedicated_synthetic_account"
    ]
    fixture_policy: Literal["original_last_turn_fixed_compact_context"]

    @model_validator(mode="after")
    def complete_prices(self):
        if (
            self.live_execution_enabled
            and self.execution_scope == "authenticated_api"
            and (
                not self.database_write_authorized
                or self.authentication_mode != "dedicated_synthetic_account"
            )
        ):
            raise ValueError(
                "live API execution requires approved DB target and dedicated account"
            )
        if set(self.prices) != {
            self.routing_model,
            self.judge_model,
            self.embedding_model,
        }:
            raise ValueError("price model set mismatch")
        ledger = (Path(__file__).resolve().parents[2] / self.ledger_path).resolve()
        root = Path(__file__).resolve().parents[2] / "backend/logs/evaluation"
        if not ledger.is_relative_to(root):
            raise ValueError(
                "budget ledger must live in ignored backend/logs/evaluation"
            )
        return self


class BudgetStopped(RuntimeError):
    pass


class RunBudget:
    """One immutable limit per run; reservations survive restart/failure/cancellation.

    Do not refund failed requests: provider acceptance may be unknown. Ledger stores
    counts/reservations only. Missing usage is not a measured zero cost.
    """

    def __init__(self, config: EvaluationRuntime):
        self.config = config
        self.stopped = False
        self.observations: list[dict] = []

    def reserve(self, amount_microusd: int) -> bool:
        if type(amount_microusd) is not int or amount_microusd <= 0:
            raise ValueError("reservation must be positive integer")
        path = Path(__file__).resolve().parents[2] / self.config.ledger_path
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            raw = f.read()
            limit = math.floor(self.config.budget_usd * 1_000_000)
            state = (
                json.loads(raw)
                if raw
                else {
                    "run_id": self.config.run_id,
                    "limit_microusd": limit,
                    "reserved_microusd": 0,
                    "requests": 0,
                    "stopped": False,
                }
            )
            if (
                state.get("run_id") != self.config.run_id
                or state.get("limit_microusd") != limit
            ):
                raise ValueError("budget ledger identity/limit mismatch")
            if any(
                type(state.get(k)) is not int or state[k] < 0
                for k in ("requests", "reserved_microusd")
            ):
                raise ValueError("invalid budget ledger")
            if type(state.get("stopped")) is not bool:
                raise ValueError("invalid stopped state")
            allowed = (
                not state["stopped"]
                and state["reserved_microusd"] + amount_microusd <= limit
                and state["requests"] < self.config.max_provider_requests
            )
            if allowed:
                state["reserved_microusd"] += amount_microusd
                state["requests"] += 1
            else:
                state["stopped"] = self.stopped = True
            f.seek(0)
            f.write(json.dumps(state))
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
            return allowed


class BudgetTransport(httpx.AsyncBaseTransport):
    """Gate EVERY actual OpenAI request, shared across routing/answer/embedding/judge.

    This guard doesn't mutate output caps or silently change SDK request policy.
    Configure clients with explicit caps, zero retries, this transport and standard tier.
    Bytes+framing conservatively reserve text input, including structured schema overhead.
    """

    def __init__(
        self,
        budget: RunBudget,
        *,
        output_cap: int,
        inner: httpx.AsyncBaseTransport | None = None,
    ):
        self.budget = budget
        self.output_cap = output_cap
        if type(output_cap) is not int or not 0 < output_cap <= max(
            budget.config.routing_max_output_tokens,
            budget.config.answer_max_output_tokens,
            budget.config.judge_max_output_tokens,
        ):
            raise ValueError("invalid transport output cap")
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)
        self.stop_reason = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            body = json.loads(request.content)
            if not isinstance(body, dict):
                raise TypeError("invalid request body")
            if self.budget.stopped:
                raise ValueError("budget already stopped")
            config = self.budget.config
            if not config.live_execution_enabled:
                raise ValueError("live execution disabled")
            model = body.get("model")
            if (
                request.method != "POST"
                or request.url.host != "api.openai.com"
                or request.url.path not in {"/v1/chat/completions", "/v1/embeddings"}
            ):
                raise ValueError("unsupported endpoint")
            if (
                len(request.content) > config.max_request_bytes
                or model not in config.prices
                or body.get("service_tier", "default") != "default"
            ):
                raise ValueError("unbudgeted request")
            price = config.prices[model]
            if request.url.path == "/v1/embeddings":
                if model != config.embedding_model or not isinstance(
                    body.get("input"), str | list
                ):
                    raise ValueError("unsupported embedding")
                if isinstance(body["input"], list) and not all(
                    isinstance(v, str) for v in body["input"]
                ):
                    raise ValueError("only text input supported")
                output_tokens = 0
            else:
                if model == config.embedding_model:
                    raise ValueError("wrong endpoint")
                output_tokens = body.get(
                    "max_completion_tokens", body.get("max_tokens")
                )
                if (
                    type(output_tokens) is not int
                    or not 0 < output_tokens <= self.output_cap
                ):
                    raise ValueError("explicit output cap required")
                # Reject image/audio/tool APIs whose token cost isn't bounded by body bytes.
                if len(body.get("messages", [])) > 64 or not all(
                    isinstance(m.get("content"), str | type(None))
                    for m in body.get("messages", [])
                ):
                    raise ValueError("only text messages supported")
            reservation = math.ceil(
                (len(request.content) + 1024) * price.input_usd_per_million
                + output_tokens * price.output_usd_per_million
            )
            allowed = await asyncio.to_thread(self.budget.reserve, reservation)
        except (ValueError, TypeError, KeyError, OSError):
            self.budget.stopped = True
            self.stop_reason = "budget_or_request_unavailable"
            raise BudgetStopped(self.stop_reason) from None
        if not allowed:
            self.stop_reason = "budget_or_request_limit"
            raise BudgetStopped(self.stop_reason)
        started = perf_counter()
        observation = {
            "case_id": current_evaluation_case.get(),
            "model": model,
            "reserved_microusd": reservation,
            "input_tokens": None,
            "output_tokens": None,
            "usage_cost_upper_usd": None,
            "status": "transport_error",
        }
        try:
            response = await self.inner.handle_async_request(request)
            await response.aread()
            observation["http_status"] = response.status_code
            observation["status"] = "response_received"
            try:
                usage = response.json().get("usage", {})
                incoming = usage.get("prompt_tokens", usage.get("input_tokens"))
                outgoing = usage.get(
                    "completion_tokens",
                    usage.get(
                        "output_tokens",
                        0 if request.url.path.endswith("embeddings") else None,
                    ),
                )
                if type(incoming) is int and type(outgoing) is int:
                    observation.update(
                        input_tokens=incoming,
                        output_tokens=outgoing,
                        usage_cost_upper_usd=(
                            incoming * price.input_usd_per_million
                            + outgoing * price.output_usd_per_million
                        )
                        / 1_000_000,
                    )
            except (ValueError, AttributeError, TypeError):
                pass
            return response
        finally:
            observation["duration_ms"] = round((perf_counter() - started) * 1000, 3)
            self.budget.observations.append(observation)

    async def aclose(self):
        await self.inner.aclose()


def main() -> None:
    import argparse
    from hashlib import sha256

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="read model/flag readiness only; never print credentials",
    )
    parser.add_argument("--write-schema", action="store_true")
    args = parser.parse_args()
    config = EvaluationRuntime.model_validate_json(args.config.read_text())
    report = {
        "config_valid": True,
        "config_sha256": sha256(args.config.read_bytes()).hexdigest(),
        "budget_usd": config.budget_usd,
        "live_execution_enabled": config.live_execution_enabled,
        "requests_sent": 0,
        "database_write_authorized": config.database_write_authorized,
        "authentication_mode": config.authentication_mode,
        "runtime_ready": False,
    }
    if args.check_env:
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from urllib.parse import urlparse

        from app.core.config import Settings

        try:
            settings = Settings(_env_file=Path(__file__).resolve().parents[1] / ".env")
        except ValidationError:
            print(
                json.dumps(
                    {
                        **report,
                        "environment_available": False,
                        "reason_code": "environment_configuration_invalid",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        report["environment"] = {
            "provider_key_configured": bool(settings.openai_api_key),
            "db_target_kind": "local"
            if urlparse(settings.database_url).hostname
            in {"localhost", "127.0.0.1", "::1"}
            else "remote",
            "routing_model_matches": settings.openai_model == config.routing_model,
            "answer_model_matches": (
                settings.openai_answer_model or settings.openai_model
            )
            == config.answer_model,
            "online_evaluation_needs_override": settings.ragas_online_enabled,
            "api_response_logging_needs_override": settings.api_response_logging_enabled,
        }
    if args.write_schema:
        schema = EvaluationRuntime.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        (
            Path(__file__).resolve().parents[2]
            / "data/chat/evaluation/schemas/agent_evaluation_runtime.schema.json"
        ).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


class EvaluationResources:
    """Explicit clients/services sharing one ledger; no network on construction.

    Enter/exit owns HTTP clients. Actual calls still require the approved runtime.
    Handlers must receive embedding_client, not the application's cached default.
    """

    def __init__(self, config: EvaluationRuntime, *, api_key: str):
        from openai import AsyncOpenAI

        self.config = config
        self.budget = RunBudget(config)
        self.routing_http = httpx.AsyncClient(
            transport=BudgetTransport(
                self.budget, output_cap=config.routing_max_output_tokens
            )
        )
        self.answer_http = httpx.AsyncClient(
            transport=BudgetTransport(
                self.budget, output_cap=config.answer_max_output_tokens
            )
        )
        self.embedding_http = httpx.AsyncClient(
            transport=BudgetTransport(
                self.budget, output_cap=config.judge_max_output_tokens
            )
        )
        self.judge_http = httpx.AsyncClient(
            transport=BudgetTransport(
                self.budget, output_cap=config.judge_max_output_tokens
            )
        )
        self.embedding_client = AsyncOpenAI(
            api_key=api_key,
            http_client=self.embedding_http,
            max_retries=0,
            timeout=config.provider_timeout_seconds,
        )
        self.judge_client = AsyncOpenAI(
            api_key=api_key,
            http_client=self.judge_http,
            max_retries=0,
            timeout=config.judge_timeout_seconds,
        )

    def routing_service(self):
        from app.agent.routing_service import ToolRoutingService

        return ToolRoutingService(
            model=self.config.routing_model,
            http_async_client=self.routing_http,
            max_output_tokens=self.config.routing_max_output_tokens,
            max_retries=0,
        )

    def answer_service(self, observer):
        from app.agent.answer_generation_service import AnswerGenerationService

        return AnswerGenerationService(
            model=self.config.answer_model,
            timeout_seconds=self.config.answer_timeout_seconds,
            evaluation_observer=observer.observe,
            http_async_client=self.answer_http,
            max_output_tokens=self.config.answer_max_output_tokens,
            max_retries=0,
        )

    async def aclose(self):
        for client in (
            self.routing_http,
            self.answer_http,
            self.embedding_http,
            self.judge_http,
        ):
            await client.aclose()

    def metrics(self):
        """Explicit judge construction, using the same budget as generation."""
        import os

        os.environ["RAGAS_DO_NOT_TRACK"] = "true"
        from ragas.embeddings.base import embedding_factory
        from ragas.llms import llm_factory

        from scripts.ragas_evaluation import build_metrics

        llm = llm_factory(
            self.config.judge_model,
            client=self.judge_client,
            temperature=0,
            max_tokens=self.config.judge_max_output_tokens,
            max_retries=0,
        )
        embeddings = embedding_factory(
            "openai", model=self.config.embedding_model, client=self.embedding_client
        )
        return build_metrics(llm=llm, embeddings=embeddings)


if __name__ == "__main__":
    main()
