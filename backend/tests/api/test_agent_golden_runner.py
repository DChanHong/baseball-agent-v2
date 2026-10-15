from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.agent.answer_generation_service import AnswerGenerationService
from app.agent.graph import BaseballAgentGraph
from app.agent.routing_schemas import ToolRoutingDecision
from scripts.run_agent_golden_evaluation import (
    DEFAULT_DATASET,
    Capture,
    collect_graph_case,
    graph_input,
    main,
    metric_plan,
    rank_metrics,
    summarize,
)
from scripts.validate_agent_golden_dataset import validate_dataset


@pytest.fixture
def dataset():
    return validate_dataset(json.loads(DEFAULT_DATASET.read_text()))


def case(dataset, suffix="guide_001"):
    return next(c for c in dataset.cases if c.case_id == "golden_" + suffix)


def capture(dataset, target, **changes):
    data = {
        "case_id": target.case_id,
        "dataset_sha256": dataset.content_sha256,
        "status": "completed",
        "duration_ms": 1,
        "observed_tool": target.expected.tool_name,
        "observed_input": target.expected.filter_constraints,
        "tool_status": "completed",
        "response_origin": "llm",
        "model_response": "MODEL ONLY",
        "final_response": "FINAL NOTICE",
        "retrieval_items": [{"chunk_id": "synthetic", "content": "FULL PUBLIC BODY"}],
        "generation_evidence": [
            {
                "ref": "E1",
                "kind": "retrieved_document",
                "payload": {"content": "BOUNDED PUBLIC BODY"},
            }
        ],
    }
    data.update(changes)
    return Capture(**data)


def test_all_50_inputs_preserve_question_and_compact_context(dataset):
    for target in dataset.cases:
        prepared = graph_input(target)
        assert prepared.user_message == target.input.question
        assert prepared.favorite_team_id == target.input.favorite_team_id
        assert prepared.context.to_routing_context().model_dump(
            mode="json", exclude_none=True
        ) == {
            k: v for k, v in target.input.conversation_context.items() if v is not None
        }
    prepared = graph_input(case(dataset, "mixed_003"))
    assert prepared.context.selected_game.start_time.hour == 18
    assert prepared.context.selected_game.start_time.minute == 30
    assert prepared.context.selected_game.game_id.int == 3


def test_metric_inputs_distinguish_retrieval_generation_and_final_answer(dataset):
    target = case(dataset)
    plan = metric_plan(target, capture(dataset, target))
    assert plan["faithfulness"]["kwargs"]["response"] == "MODEL ONLY"
    assert "BOUNDED PUBLIC BODY" in str(plan["faithfulness"])
    assert "FULL PUBLIC BODY" not in str(plan["faithfulness"])
    assert "FULL PUBLIC BODY" in str(plan["context_recall"])
    assert "FINAL NOTICE" not in str(plan)
    assert (
        json.loads(plan["answer_relevancy"]["kwargs"]["user_input"])["question"]
        == target.input.question
    )


@pytest.mark.parametrize(
    "suffix,reason",
    [
        ("ticket_009", "source_review_pending"),
        ("mixed_005", "multi_tool_adapter_pending"),
        ("scope_005", "non_rag_case"),
    ],
)
def test_exclusion_policy_no_fabricated_score(dataset, suffix, reason):
    target = case(dataset, suffix)
    plan = metric_plan(target, capture(dataset, target))
    assert all(m["reason_code"] == reason for m in plan.values())


def test_fallback_keeps_retrieval_metrics_and_missing_capture_is_explicit(dataset):
    target = case(dataset)
    plan = metric_plan(
        target,
        capture(dataset, target, response_origin="fallback", model_response=None),
    )
    assert plan["faithfulness"]["reason_code"] == "non_llm_response"
    assert plan["context_recall"]["status"] == "ready"
    plan = metric_plan(target, capture(dataset, target, model_response=None))
    assert all(m["reason_code"] == "model_capture_missing" for m in plan.values())


def test_empty_retrieval_rank_is_zero_only_with_known_core_labels(dataset):
    target = case(dataset, "guide_003")
    row = rank_metrics(
        target, capture(dataset, target, retrieval_items=[]), dataset, k=3
    )
    assert row["status"] == "computed"
    assert row["recall"] == row["mrr"] == row["ndcg"] == 0
    missing = case(dataset, "knowledge_005")
    row = rank_metrics(
        missing, capture(dataset, missing, retrieval_items=[]), dataset, k=5
    )
    assert row["reason_code"] == "no_core_evidence_after_filter"
    assert row["recall"] is None


def test_rank_identity_duplicate_and_body_drift(dataset):
    target = case(dataset, "guide_003")
    label = next(
        l
        for l in target.retrieval_ground_truth.production_relevance_review.chunks
        if l.relevance_grade == 2 and l.passes_expected_filter
    )
    fixture = dataset.model_copy(deep=True)
    body = "PUBLIC FIXTURE ONLY"
    manifest = next(
        i
        for i in fixture.production_corpus_snapshot.manifest["chunks"]
        if i["chunk_id"] == label.chunk_id
    )
    manifest["observed_content_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    item = {"chunk_id": label.chunk_id, "content": body}
    row = rank_metrics(
        target, capture(dataset, target, retrieval_items=[item]), fixture, k=3
    )
    assert row["mrr"] == 1
    assert row["scope"] == "bounded_expected_filter_pool"
    row = rank_metrics(
        target, capture(dataset, target, retrieval_items=[item, item]), fixture, k=3
    )
    assert row["reason_code"] == "duplicate_retrieved_chunk"
    row = rank_metrics(
        target,
        capture(dataset, target, retrieval_items=[{**item, "content": "changed"}]),
        fixture,
        k=3,
    )
    assert row["reason_code"] == "retrieved_body_snapshot_mismatch"
    row = rank_metrics(target, capture(dataset, target), dataset, k=3)
    assert row["reason_code"] == "unlabeled_or_filter_ineligible_chunk"


def test_summary_keeps_all_selected_cases_and_omits_content(dataset):
    target = case(dataset)
    row = capture(dataset, target)
    summary = summarize(dataset, [row], split="all")
    assert summary["case_count"] == 50
    assert summary["captured_count"] == 1
    assert sum(r["status"] == "not_run" for r in summary["results"]) == 49
    assert summary["ragas_executed"] is False
    assert summary["results"][0]["question_resolution"] == "not_judged"
    assert summary["results"][0]["metrics"]["faithfulness"]["value"] is None
    assert summary["results"][0]["cost_usd"] is None
    text = json.dumps(summary)
    for secret in [
        "MODEL ONLY",
        "FINAL NOTICE",
        "FULL PUBLIC BODY",
        "BOUNDED PUBLIC BODY",
    ]:
        assert secret not in text
    with pytest.raises(ValueError, match="duplicate"):
        summarize(dataset, [row, row])
    with pytest.raises(ValueError, match="hash"):
        summarize(dataset, [row.model_copy(update={"dataset_sha256": "wrong"})])
    with pytest.raises(ValueError, match="unselected"):
        summarize(dataset, [capture(dataset, case(dataset, "ticket_009"))])


class ToolResult(BaseModel):
    items: list[dict]
    answerable: bool = True
    limitations: list[str] = []


def graph_factory(observer, *, fail_answer=False, fail_tool=False):
    decision = ToolRoutingDecision.model_validate(
        {
            "is_in_scope": True,
            "should_call_tool": True,
            "tool_name": "search_stadium_guide",
            "args": {
                "stadium_id": "GOCHEOK",
                "query": "고척 음식",
                "team_id": None,
                "guide_types": None,
            },
            "needs_clarification": False,
            "clarification_reason": None,
            "unsupported_reason": None,
        }
    )
    route = SimpleNamespace(execute=AsyncMock(return_value=decision))
    items = [
        {
            "chunk_id": str(i),
            "content": "PUBLIC BODY " + ("x" * 6100),
            "review_status": "needs_review",
            "as_of": "2026-10-14",
        }
        for i in range(5)
    ]
    executor = SimpleNamespace(execute=AsyncMock(return_value=ToolResult(items=items)))
    if fail_tool:
        executor.execute.side_effect = ValueError("DO NOT SAVE SECRET")
    chain = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={
                "answerability": "fully_answerable",
                "answer": "MODEL ONLY",
                "used_evidence_refs": ["E1"],
                "acknowledged_limitations": [],
            }
        )
    )
    if fail_answer:
        chain.ainvoke.side_effect = ValueError("DO NOT SAVE SECRET")
    answer = AnswerGenerationService(
        chain=chain, model="test-model", evaluation_observer=observer.observe
    )
    return BaseballAgentGraph(
        tool_routing_service=route,
        tool_executor=executor,
        answer_generation_service=answer,
    )


@pytest.mark.asyncio
async def test_actual_graph_collects_original_results_and_observed_bounded_request(
    dataset,
):
    target = case(dataset)
    row = await collect_graph_case(
        target, dataset_sha256=dataset.content_sha256, graph_factory=graph_factory
    )
    assert row.status == "completed"
    assert len(row.retrieval_items) == 5
    assert len(row.generation_evidence) == 3
    assert len(row.generation_evidence[0]["payload"]["content"]) == 6000
    assert row.model_response == "MODEL ONLY"
    assert row.final_response.startswith("MODEL ONLY\n\n자료 기준일")
    assert "user_profile_id" not in row.model_dump()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["answer", "tool"])
async def test_actual_graph_failure_preserves_available_evidence(dataset, failure):
    target = case(dataset)
    row = await collect_graph_case(
        target,
        dataset_sha256=dataset.content_sha256,
        graph_factory=lambda observer: graph_factory(
            observer, fail_answer=failure == "answer", fail_tool=failure == "tool"
        ),
    )
    assert row.status == "completed" and row.response_origin == "fallback"
    assert row.model_response is None
    assert len(row.retrieval_items) == (5 if failure == "answer" else 0)
    assert len(row.generation_evidence) == (3 if failure == "answer" else 0)
    assert "DO NOT SAVE SECRET" not in row.model_dump_json()


@pytest.mark.asyncio
async def test_timeout_retains_partial_retrieval_and_does_not_retry(dataset):
    counter = []

    async def stream(_):
        counter.append(1)
        yield SimpleNamespace(
            kind="tool.completed",
            tool_payload={
                "status": "completed",
                "result": {"items": [{"content": "PUBLIC"}]},
            },
        )
        await asyncio.sleep(10)

    row = await collect_graph_case(
        case(dataset),
        dataset_sha256=dataset.content_sha256,
        graph_factory=lambda _: SimpleNamespace(astream=stream),
        timeout_seconds=0.01,
    )
    assert row.status == "timeout" and row.reason_code == "turn_timeout"
    assert row.retrieval_items == [{"content": "PUBLIC"}]
    assert counter == [1]


def test_cli_default_development_does_not_call_runtime(dataset, tmp_path, monkeypatch):
    out = tmp_path / "summary.json"
    monkeypatch.setattr("sys.argv", ["runner", "--output", str(out)])
    main()
    result = json.loads(out.read_text())
    assert result["case_count"] == 35 and result["captured_count"] == 0
    assert result["split_selection"] == "development"
    assert all(r["status"] == "not_run" for r in result["results"])


@pytest.mark.asyncio
async def test_collection_split_and_source_block_do_not_disappear(dataset, monkeypatch):
    from scripts.run_agent_golden_evaluation import collect_graph_dataset

    seen = []

    async def fake_collect(target, **kwargs):
        seen.append(target.case_id)
        return capture(dataset, target, status="error", reason_code="graph_error")

    monkeypatch.setattr(
        "scripts.run_agent_golden_evaluation.collect_graph_case", fake_collect
    )
    rows = await collect_graph_dataset(dataset, graph_factory=lambda _: None)
    assert len(rows) == 35 and len(set(seen)) == 35
    seen.clear()
    rows = await collect_graph_dataset(
        dataset, graph_factory=lambda _: None, split="all"
    )
    assert len(rows) == 49 and "golden_ticket_009" not in seen
    summary = summarize(dataset, rows, split="all")
    assert len(summary["results"]) == 50
    blocked = next(r for r in summary["results"] if r["case_id"] == "golden_ticket_009")
    assert (
        blocked["status"] == "not_run"
        and blocked["reason_code"] == "source_review_pending"
    )


@pytest.mark.asyncio
async def test_fixed_followup_runs_actual_contextual_direct_graph(dataset):
    target = case(dataset, "mixed_003")
    decision = ToolRoutingDecision.model_validate(
        {
            "is_in_scope": True,
            "should_call_tool": False,
            "tool_name": None,
            "args": None,
            "needs_clarification": False,
            "clarification_reason": None,
            "unsupported_reason": None,
            "direct_answer_intent": "selected_game_time",
        }
    )
    executor = SimpleNamespace(execute=AsyncMock())
    factory = lambda _: BaseballAgentGraph(
        tool_routing_service=SimpleNamespace(execute=AsyncMock(return_value=decision)),
        tool_executor=executor,
    )
    row = await collect_graph_case(
        target, dataset_sha256=dataset.content_sha256, graph_factory=factory
    )
    assert row.status == "completed" and row.response_origin == "contextual_direct"
    assert "18" in row.final_response and "30" in row.final_response
    executor.execute.assert_not_called()
    assert all(
        m["reason_code"] == "non_rag_case" for m in metric_plan(target, row).values()
    )
