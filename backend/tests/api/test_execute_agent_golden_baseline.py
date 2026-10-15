from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts.execute_agent_golden_baseline import CapturingGraph, score_plan
from scripts.run_agent_golden_evaluation import (
    DEFAULT_DATASET,
    GenerationCapture,
    graph_input,
)
from scripts.validate_agent_golden_dataset import validate_dataset


@pytest.mark.asyncio
async def test_same_api_turn_capture_preserves_fixture_date_and_original_answer():
    dataset = validate_dataset(json.loads(DEFAULT_DATASET.read_text()))
    case = dataset.cases[0]
    seen = []

    class Graph:
        async def astream(self, actual):
            seen.append(actual)
            yield SimpleNamespace(
                kind="completed",
                output=SimpleNamespace(answer_source="llm", answer="FINAL WITH NOTICE"),
            )

    observer = GenerationCapture(model_response="MODEL BEFORE NOTICE", evidence=[])
    store = {}
    graph = CapturingGraph(Graph(), case, observer, store, dataset.content_sha256)
    actual = graph_input(case).model_copy(update={"today": date(2026, 10, 15)})
    events = [event async for event in graph.astream(actual)]
    assert len(events) == 1
    assert seen[0].today == case.input.today
    assert store[case.case_id].model_response == "MODEL BEFORE NOTICE"
    assert store[case.case_id].final_response == "FINAL WITH NOTICE"


@pytest.mark.asyncio
async def test_scorer_does_not_call_excluded_or_budget_stopped_metrics():
    resources = SimpleNamespace(budget=SimpleNamespace(stopped=True))
    plan = {
        "faithfulness": {"status": "ready", "kwargs": {}},
        "context_recall": {"status": "excluded", "reason_code": "missing_reference"},
    }
    metric = SimpleNamespace(ascore=AsyncMock())
    result = await score_plan(plan, {"faithfulness": metric}, resources, 1)
    metric.ascore.assert_not_called()
    assert result["faithfulness"]["reason_code"] == "budget_stopped"
    assert result["context_recall"]["value"] is None
