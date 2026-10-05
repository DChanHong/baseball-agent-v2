from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from app.agent.answer_generation_service import AnswerGenerationService
from app.agent.answer_schemas import GroundedAnswerDraft
from app.agent.graph import BaseballAgentGraph
from app.agent.routing_schemas import ToolRoutingDecision
from app.agent.state import AgentConversationContext, BaseballAgentInput
from app.core.agent_trace import trace_stage
from app.domains.baseball.tool.search_baseball_knowledge.handler import (
    SearchBaseballKnowledgeToolHandler,
)
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    BaseballKnowledgeSearchItem,
    SearchBaseballKnowledgeToolInput,
)

SECRET = "synthetic-private-content"


class Router:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def execute(self, **kwargs: Any) -> ToolRoutingDecision:
        await asyncio.sleep(0)
        if self.mode == "route_failure":
            raise ValueError(SECRET)
        use_tool = self.mode != "direct"
        return ToolRoutingDecision.model_validate(
            {
                "is_in_scope": True,
                "should_call_tool": use_tool,
                "tool_name": "search_baseball_knowledge" if use_tool else None,
                "args": {"query": SECRET, "knowledge_types": None}
                if use_tool
                else None,
                "needs_clarification": False,
                "clarification_reason": None,
                "unsupported_reason": None,
            }
        )


class Embeddings:
    async def create(self, **kwargs: Any) -> Any:
        await asyncio.sleep(0)
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1])])


class Retriever:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def search(self, **kwargs: Any) -> list[BaseballKnowledgeSearchItem]:
        await asyncio.sleep(0)
        if self.mode == "tool_failure":
            raise RuntimeError(SECRET)
        if self.mode == "empty":
            return []
        return [
            BaseballKnowledgeSearchItem(
                chunk_id="rule_001",
                document_id="doc_001",
                document_type="baseball_rule",
                title=SECRET,
                content=SECRET,
                similarity=0.8,
                distance=0.1,
                source_urls=["https://example.com"],
                as_of=date(2026, 10, 5),
                trust_level="official",
                review_status="approved",
                metadata={},
            )
        ]


class Executor:
    def __init__(self, mode: str) -> None:
        self.handler = SearchBaseballKnowledgeToolHandler(
            openai_client=SimpleNamespace(embeddings=Embeddings()),  # type: ignore[arg-type]
            retriever=Retriever(mode),  # type: ignore[arg-type]
        )

    async def execute(self, decision: ToolRoutingDecision) -> Any:
        return await self.handler.execute(
            SearchBaseballKnowledgeToolInput(query=SECRET)
        )


class AnswerChain:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def ainvoke(self, payload: Any) -> Any:
        if self.mode == "timeout":
            await asyncio.sleep(60)
        refs = [] if self.mode == "empty" else ["E1"]
        if self.mode == "bad_ref":
            refs = ["E99"]
        if self.mode == "chain_schema":
            return GroundedAnswerDraft.model_validate({"answer": SECRET})
        if self.mode == "bad_schema":
            return {"answer": SECRET}
        return {
            "answerability": "insufficient_source" if not refs else "fully_answerable",
            "answer": SECRET,
            "used_evidence_refs": refs,
            "acknowledged_limitations": [SECRET]
            if self.mode == "bad_limitation"
            else [],
        }


def graph(mode: str) -> BaseballAgentGraph:
    return BaseballAgentGraph(
        tool_routing_service=Router(mode),  # type: ignore[arg-type]
        tool_executor=Executor(mode),  # type: ignore[arg-type]
        answer_generation_service=AnswerGenerationService(
            chain=AnswerChain(mode),
            model="test",
            timeout_seconds=0.01,
        ),
    )


async def run(mode: str) -> list[Any]:
    return [
        event
        async for event in graph(mode).astream(
            BaseballAgentInput(
                conversation_id=uuid4(),
                user_profile_id=uuid4(),
                user_message=SECRET,
                today=date(2026, 10, 5),
                timezone="Asia/Seoul",
                favorite_team_id=None,
                context=AgentConversationContext(),
            )
        )
    ]


def records(caplog: Any) -> list[dict[str, Any]]:
    return [
        json.loads(record.getMessage().removeprefix("agent_trace "))
        for record in caplog.records
        if record.name == "app.core.agent_trace"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,source,reason",
    [
        ("normal", "llm", None),
        ("empty", "llm", None),
        ("timeout", "fallback", "TimeoutError"),
        ("tool_failure", "fallback", "tool_execution_failed"),
        ("direct", "template", None),
        ("bad_limitation", "fallback", "unknown_limitation_codes"),
        ("bad_ref", "fallback", "unknown_evidence_refs"),
        ("bad_schema", "fallback", "answer_schema_invalid"),
        ("chain_schema", "fallback", "answer_schema_invalid"),
    ],
)
async def test_turn_trace_connects_stages_and_distinguishes_fallback(
    caplog: Any,
    mode: str,
    source: str,
    reason: str | None,
) -> None:
    caplog.set_level(logging.INFO, logger="app.core.agent_trace")
    events = await run(mode)
    output = events[-1].output
    logs = records(caplog)
    assert {record["trace_id"] for record in logs} == {output.trace_id}
    assert logs[0]["event"] == "turn.started"
    assert logs[-1]["event"] == "turn.completed"
    assert logs[-1]["answer_source"] == output.answer_source == source
    assert logs[-1]["fallback_reason"] == output.fallback_reason == reason
    assert SECRET not in json.dumps(logs)
    assert all(record["duration_ms"] >= 0 for record in logs if "duration_ms" in record)
    names = [record["event"] for record in logs]
    assert "route.completed" in names and "answer.completed" in names
    if mode == "timeout":
        assert "answer_llm.failed" in names
        assert (
            next(r for r in logs if r["event"] == "answer_llm.failed")["error_type"]
            == "TimeoutError"
        )
    if mode == "chain_schema":
        assert "answer_llm.failed" in names
        assert "answer_validation.started" not in names
    if mode.startswith("bad_"):
        validation = next(r for r in logs if r["event"] == "answer_validation.failed")
        assert validation["error_code"] == reason
        assert output.answer_generation is None
    if mode == "direct":
        assert "tool.started" not in names
    elif mode == "tool_failure":
        assert "retrieval.failed" in names and "tool.failed" in names
        assert (
            next(r for r in logs if r["event"] == "tool.failed")["error_type"]
            == "RuntimeError"
        )
    else:
        retrieval = next(r for r in logs if r["event"] == "retrieval.completed")
        assert retrieval["chunk_ids"] == ([] if mode == "empty" else ["rule_001"])
        assert retrieval["answerable"] == (mode != "empty")
        assert "embedding.completed" in names
    assert [event.kind for event in events] == (
        ["completed"]
        if mode == "direct"
        else [
            "tool.started",
            "tool.failed" if mode == "tool_failure" else "tool.completed",
            "completed",
        ]
    )


@pytest.mark.asyncio
async def test_routing_failure_closes_trace_without_exception_text(caplog: Any) -> None:
    caplog.set_level(logging.INFO, logger="app.core.agent_trace")
    with pytest.raises(ValueError):
        await run("route_failure")
    logs = records(caplog)
    assert [r["event"] for r in logs] == [
        "turn.started",
        "route.started",
        "route.failed",
        "turn.failed",
    ]
    assert logs[-1]["error_type"] == "ValueError"
    assert SECRET not in json.dumps(logs)


@pytest.mark.asyncio
async def test_concurrent_turns_keep_trace_context_isolated(caplog: Any) -> None:
    caplog.set_level(logging.INFO, logger="app.core.agent_trace")
    outputs = await asyncio.gather(run("normal"), run("timeout"))
    ids = {events[-1].output.trace_id for events in outputs}
    assert len(ids) == 2
    for trace_id in ids:
        logs = [r for r in records(caplog) if r["trace_id"] == trace_id]
        assert sum(r["event"] == "retrieval.completed" for r in logs) == 1
        assert logs[0]["event"] == "turn.started"
        assert logs[-1]["event"] == "turn.completed"
    before = len(records(caplog))
    with trace_stage("outside"):
        pass
    assert len(records(caplog)) == before


@pytest.mark.asyncio
async def test_consumer_close_records_interrupted_turn(caplog: Any) -> None:
    caplog.set_level(logging.INFO, logger="app.core.agent_trace")
    stream = graph("normal").astream(
        BaseballAgentInput(
            conversation_id=uuid4(),
            user_profile_id=uuid4(),
            user_message=SECRET,
            today=date(2026, 10, 5),
            timezone="Asia/Seoul",
            favorite_team_id=None,
            context=AgentConversationContext(),
        )
    )
    assert (await anext(stream)).kind == "tool.started"
    await stream.aclose()
    assert records(caplog)[-1]["event"] == "turn.interrupted"
