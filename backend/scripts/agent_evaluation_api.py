"""Authenticated chat SSE and scoped message re-read checks for synthetic fixtures.

Functions require an explicitly injected authenticated client. Import/CLI makes no
network or DB calls. Fixture creation is a DB write; don't invoke until authorized.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict

from scripts.run_agent_golden_evaluation import content_hash, graph_input
from scripts.validate_agent_golden_dataset import Case


@dataclass
class ApiFixture:
    case_id: str
    conversation_id: UUID
    today: date
    favorite_team_id: str | None
    context_sha256: str


class ApiCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    status: str
    reason_code: str | None = None
    sse_completion: str = "not_checked"
    persistence: str = "not_checked"
    authentication: str = "not_checked"
    model_capture: str = "not_available_from_public_sse"
    # Identity and message text stay only in memory, not in this durable check object.


def fixture_matches(case: Case, fixture: ApiFixture) -> bool:
    return (
        fixture.case_id == case.case_id
        and fixture.today == case.input.today
        and fixture.favorite_team_id == case.input.favorite_team_id
        and fixture.context_sha256 == content_hash(case.input.conversation_context)
    )


async def prepare_api_fixture(
    client: httpx.AsyncClient,
    case: Case,
    *,
    runtime_today: date,
    database_write_authorized: bool = False,
    dedicated_synthetic_account: bool = False,
) -> ApiFixture:
    """Create only a new synthetic conversation; never modify a user's profile.

    Verify the dedicated account's favorite team. If different, caller must arrange
    that fixture separately. Original question/date/context must remain unchanged.
    """
    if not database_write_authorized or not dedicated_synthetic_account:
        raise ValueError(
            "approved write target and dedicated synthetic account required"
        )
    if runtime_today != case.input.today:
        raise ValueError("server date differs from fixed dataset")
    auth = await client.get("/api/v1/auth/me")
    if auth.status_code != 200:
        raise ValueError("authentication unavailable")
    favorite = auth.json()["user"]["favoriteTeam"]
    if favorite != case.input.favorite_team_id:
        raise ValueError("favorite team fixture mismatch")
    context = graph_input(case).context.model_dump(mode="json", exclude_none=True)
    response = await client.post(
        "/api/v1/conversations",
        json={
            "title": "synthetic golden evaluation",
            "metadata": {"agent_context": context},
        },
    )
    if response.status_code != 200:
        raise ValueError("fixture creation failed")
    body = response.json()
    if body.get("metadata", {}).get("agent_context") != context:
        raise ValueError("saved fixture context mismatch")
    return ApiFixture(
        case.case_id,
        UUID(body["id"]),
        runtime_today,
        favorite,
        content_hash(case.input.conversation_context),
    )


async def collect_api_case(
    client: httpx.AsyncClient,
    case: Case,
    *,
    fixture: ApiFixture,
    timeout_seconds: float = 60,
) -> ApiCheck:
    """One HTTP turn; require assistant.completed + matching done, then scoped re-read.

    No retry, no whole-user conversation listing, no public SSE -> model reconstruction.
    Actual RAGAS capture must come from the internal observer for THIS SAME request.
    """
    result = ApiCheck(case_id=case.case_id, status="not_run")
    if not fixture_matches(case, fixture):
        result.reason_code = "fixture_mismatch"
        return result
    final = None
    message_id = None
    done = False
    failed = False
    delta = ""
    event = None
    data = []

    def dispatch():
        nonlocal final, message_id, done, failed, delta
        if not data:
            return
        payload = json.loads("\n".join(data))
        if event == "stream.failed":
            failed = True
        elif event == "assistant.delta":
            delta += payload["delta"]
        elif event == "assistant.completed":
            if final is not None:
                raise ValueError("duplicate completed")
            final = payload["content"]
            message_id = UUID(payload["message_id"])
        elif event == "done":
            if (
                done
                or final is None
                or UUID(payload["conversation_id"]) != fixture.conversation_id
            ):
                raise ValueError("invalid done")
            done = True

    try:
        async with asyncio.timeout(timeout_seconds):
            async with client.stream(
                "POST",
                "/api/v1/chat",
                json={
                    "conversation_id": str(fixture.conversation_id),
                    "message": case.input.question,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code == 401:
                    result.status = "error"
                    result.authentication = "failed"
                    result.reason_code = "unauthenticated"
                    return result
                if response.status_code != 200:
                    result.status = "error"
                    result.reason_code = "chat_http_error"
                    return result
                result.authentication = "passed"
                if not response.headers.get("content-type", "").startswith(
                    "text/event-stream"
                ):
                    raise ValueError("wrong stream content type")
                async for line in response.aiter_lines():
                    if not line:
                        dispatch()
                        event = None
                        data = []
                    elif line.startswith("event:"):
                        event = line[6:].lstrip()
                    elif line.startswith("data:"):
                        data.append(line[5:].lstrip())
                if data:
                    dispatch()
            if failed or not done or final is None:
                result.status = "error"
                result.sse_completion = "failed"
                result.reason_code = "incomplete_or_failed_sse"
                return result
            if delta != final:
                result.status = "error"
                result.sse_completion = "failed"
                result.reason_code = "delta_completed_mismatch"
                return result
            result.sse_completion = "passed"
            response = await client.get(
                f"/api/v1/conversations/{fixture.conversation_id}/messages",
                params={"limit": 200, "offset": 0},
            )
            if response.status_code != 200:
                result.status = "error"
                result.persistence = "failed"
                result.reason_code = "message_reread_failed"
                return result
            messages = response.json()["messages"]
            matches = [
                m
                for m in messages
                if m.get("id") == str(message_id) and m.get("role") == "assistant"
            ]
            user_matches = [
                m
                for m in messages
                if m.get("role") == "user"
                and m.get("content") == case.input.question
                and m.get("status") == "completed"
            ]
            if (
                len(matches) != 1
                or matches[0].get("content") != final
                or matches[0].get("status") != "completed"
                or not user_matches
            ):
                result.status = "error"
                result.persistence = "failed"
                result.reason_code = "persisted_message_mismatch"
                return result
            result.status = "completed"
            result.persistence = "passed"
    except TimeoutError:
        result.status = "timeout"
        result.reason_code = "api_timeout"
    except (ValueError, KeyError, TypeError, httpx.HTTPError):
        result.status = "error"
        result.reason_code = "api_contract_or_transport_error"
    return result
