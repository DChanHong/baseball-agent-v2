from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.validate_chat_evaluation_data import (
    DEFAULT_CANDIDATES_PATH,
    DEFAULT_CASES_PATH,
    DEFAULT_RUNS_DIR,
    ChatCaseExpected,
    ManualQARun,
    validate_data,
)


def test_repository_chat_evaluation_data_is_valid() -> None:
    case_count, candidate_count, run_count = validate_data(
        DEFAULT_CASES_PATH,
        DEFAULT_CANDIDATES_PATH,
        DEFAULT_RUNS_DIR,
    )

    assert case_count >= 30
    assert candidate_count >= 0
    assert run_count >= 1


def test_expected_tool_fields_must_match_should_call_tool() -> None:
    with pytest.raises(ValidationError):
        ChatCaseExpected.model_validate(
            {
                "is_in_scope": True,
                "should_call_tool": False,
                "tool_name": "find_kbo_game",
                "tool_input": {"team_id": "LOTTE"},
                "answer_policy": [],
                "required_sources": [],
                "forbidden_claims": [],
                "ui_expectations": ["assistant.completed"],
            }
        )


def test_manual_run_summary_must_match_results() -> None:
    with pytest.raises(ValidationError):
        ManualQARun.model_validate(
            {
                "schema_version": 1,
                "run_id": "invalid-run",
                "executed_at": None,
                "environment": "local",
                "question_set_version": "test",
                "summary": {
                    "total": 1,
                    "passed": 1,
                    "ambiguous": 0,
                    "failed": 0,
                    "not_run": 0,
                },
                "results": [
                    {
                        "scenario_id": "scenario-1",
                        "case_id": "chat_game_001",
                        "category": "game_schedule",
                        "sanitized_input": "오늘 롯데 경기 있어?",
                        "expected_tool": "find_kbo_game",
                        "observed_tool": None,
                        "result": "not_run",
                        "failure_labels": [],
                        "observed_behavior": None,
                        "notes": None,
                    }
                ],
            }
        )
