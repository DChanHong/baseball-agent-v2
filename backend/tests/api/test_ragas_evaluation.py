from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from scripts.ragas_evaluation import (
    METRIC_NAMES,
    EvaluationSample,
    build_metrics,
    main,
    prepare_metric_inputs,
    score_sample,
)


def sample(**changes):
    data = {
        "case_id": "synthetic_001",
        "synthetic": True,
        "user_input": "테스트 질문",
        "expected_tool": "search_stadium_guide",
        "observed_tool": "search_stadium_guide",
        "response_origin": "llm",
        "model_response": "테스트 답변",
        "retrieval_items": [
            {"content": "FULL", "chunk_id": "a"},
            {"content": "SECOND"},
        ],
        "generation_evidence": [
            {
                "ref": "E1",
                "kind": "retrieved_document",
                "payload": {"content": "BOUNDED", "content_truncated": True},
            }
        ],
        "reference": "검수된 합성 사실",
        "reference_status": "approved",
        "reference_sources": ["https://example.org/public"],
        "reference_reviewed_at": "2026-10-05",
        "reference_reviewer": "test",
    }
    data.update(changes)
    return EvaluationSample.model_validate(data)


def test_metrics_receive_distinct_actual_contexts():
    plan = prepare_metric_inputs(sample())
    faith = plan["faithfulness"]["kwargs"]
    precision = plan["context_precision"]["kwargs"]
    assert "BOUNDED" in faith["retrieved_contexts"][0]
    assert "FULL" not in str(faith)
    assert [json.loads(v)["content"] for v in precision["retrieved_contexts"]] == [
        "FULL",
        "SECOND",
    ]
    assert "retrieved_contexts" not in plan["answer_relevancy"]["kwargs"]


def test_reference_review_is_required_and_not_used_for_answer_metrics():
    plan = prepare_metric_inputs(sample(reference_status="needs_review"))
    assert plan["faithfulness"]["status"] == "ready"
    assert plan["context_recall"]["reason_code"] == "reference_not_approved"
    with pytest.raises(ValidationError):
        sample(reference_reviewer=None)
    with pytest.raises(ValidationError):
        sample(synthetic=False)


def test_empty_policy_is_excluded_without_fabricated_scores():
    plan = prepare_metric_inputs(
        sample(
            empty_evidence_policy_case=True, retrieval_items=[], generation_evidence=[]
        )
    )
    assert all(v["reason_code"] == "empty_evidence_policy_case" for v in plan.values())


def test_empty_tool_result_is_not_a_retrieved_document():
    plan = prepare_metric_inputs(
        sample(
            retrieval_items=[],
            generation_evidence=[
                {"ref": "E1", "kind": "tool_result", "payload": {"items": []}}
            ],
        )
    )
    assert plan["faithfulness"]["reason_code"] == "empty_generation_evidence"
    assert plan["context_precision"]["reason_code"] == "empty_retrieval"


def test_generation_failure_preserves_retrieval_evaluation():
    plan = prepare_metric_inputs(
        sample(response_origin="fallback", model_response=None)
    )
    assert plan["faithfulness"]["reason_code"] == "non_llm_response"
    assert plan["context_recall"]["status"] == "ready"
    mismatch = prepare_metric_inputs(sample(observed_tool="get_stadium_info"))
    assert all(v["reason_code"] == "routing_mismatch" for v in mismatch.values())


@pytest.mark.asyncio
async def test_judge_error_timeout_nonfinite_and_negative_scores_are_distinct():
    async def slow(**kwargs):
        await asyncio.sleep(1)

    scorers = {
        name: SimpleNamespace(ascore=AsyncMock(return_value=SimpleNamespace(value=0.5)))
        for name in METRIC_NAMES
    }
    scorers["faithfulness"].ascore.side_effect = ValueError("secret judge output")
    scorers["answer_relevancy"].ascore.return_value.value = -0.1
    scorers["context_precision"].ascore.return_value.value = float("nan")
    scorers["context_recall"].ascore.side_effect = slow
    result = await score_sample(sample(), metrics=scorers, timeout_seconds=0.01)
    assert result["faithfulness"]["reason_code"] == "judge_error"
    assert result["answer_relevancy"]["value"] == -0.1
    assert result["context_precision"]["reason_code"] == "undefined_score"
    assert result["context_recall"]["reason_code"] == "judge_timeout"
    assert "secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_excluded_metrics_make_no_judge_calls():
    result = await score_sample(sample(empty_evidence_policy_case=True), metrics={})
    assert all(
        v["status"] == "excluded" and v["value"] is None for v in result.values()
    )


def test_cli_saves_no_question_answer_or_context(tmp_path, monkeypatch):
    source = tmp_path / "input.jsonl"
    output = tmp_path / "summary.json"
    source.write_text(sample().model_dump_json() + "\n")
    monkeypatch.setattr(
        "sys.argv",
        ["ragas_evaluation", "--input", str(source), "--output", str(output)],
    )
    main()
    result = json.loads(output.read_text())
    assert result["mode"] == "offline_input_validation"
    assert result["results"][0]["metrics"]["faithfulness"]["status"] == "ready"
    assert "BOUNDED" not in output.read_text()
    assert "테스트 답변" not in output.read_text()


def test_installed_ragas_factory_and_signatures_without_network(monkeypatch):
    monkeypatch.setenv("RAGAS_DO_NOT_TRACK", "true")
    pytest.importorskip("ragas")
    from openai import AsyncOpenAI
    from ragas.embeddings.base import embedding_factory
    from ragas.llms import llm_factory

    client = AsyncOpenAI(api_key="synthetic-not-a-real-key", max_retries=0)
    llm = llm_factory("gpt-4o-mini", client=client)
    embeddings = embedding_factory(
        "openai", model="text-embedding-3-small", client=client
    )
    metrics = build_metrics(llm=llm, embeddings=embeddings)
    plan = prepare_metric_inputs(sample())
    for name, metric in metrics.items():
        inspect.signature(metric.ascore).bind(**plan[name]["kwargs"])
    assert metrics["answer_relevancy"].strictness == 3


def test_malformed_context_is_rejected_instead_of_scored():
    with pytest.raises(ValidationError):
        sample(retrieval_items=[{}])
    with pytest.raises(ValidationError):
        sample(generation_evidence=[{"kind": "retrieved_document", "payload": {}}])


@pytest.mark.asyncio
async def test_zero_is_a_real_score_and_invalid_timeout_is_rejected():
    scorers = {
        name: SimpleNamespace(ascore=AsyncMock(return_value=SimpleNamespace(value=0)))
        for name in METRIC_NAMES
    }
    result = await score_sample(sample(), metrics=scorers)
    assert all(
        row["status"] == "scored" and row["value"] == 0 for row in result.values()
    )
    with pytest.raises(ValueError):
        await score_sample(sample(), metrics=scorers, timeout_seconds=float("nan"))
