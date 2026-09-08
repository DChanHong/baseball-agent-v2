from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_PATH = (
    REPOSITORY_ROOT / "data/chat/evaluation/cases/chat_mvp_cases.jsonl"
)
DEFAULT_CANDIDATES_PATH = (
    REPOSITORY_ROOT
    / "data/chat/evaluation/candidates/manual_chat_qa_candidates.jsonl"
)
DEFAULT_RUNS_DIR = REPOSITORY_ROOT / "data/chat/evaluation/runs/manual"

ToolName = Literal[
    "find_kbo_game",
    "get_stadium_info",
    "get_weather_context",
    "search_ticketing_guide",
    "search_stadium_guide",
    "search_baseball_knowledge",
]
ResultStatus = Literal["passed", "ambiguous", "failed", "not_run"]


class ChatCaseContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    auth_status: Literal["authenticated"]
    favorite_team_id: str | None
    today: date
    timezone: Literal["Asia/Seoul"]


class ChatCaseExpected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_in_scope: bool
    should_call_tool: bool
    tool_name: ToolName | None
    tool_input: dict[str, Any] | None
    answer_policy: list[str]
    required_sources: list[str]
    forbidden_claims: list[str]
    ui_expectations: list[str]

    @model_validator(mode="after")
    def validate_tool_contract(self) -> ChatCaseExpected:
        if self.should_call_tool and (
            self.tool_name is None or self.tool_input is None
        ):
            raise ValueError("tool_name and tool_input are required for a tool call")
        if not self.should_call_tool and (
            self.tool_name is not None or self.tool_input is not None
        ):
            raise ValueError("tool_name and tool_input must be null without a tool call")
        return self


class ChatEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    case_id: str = Field(min_length=1)
    category: Literal[
        "game_schedule",
        "stadium_info",
        "weather",
        "ticketing",
        "stadium_guide",
        "baseball_knowledge",
        "follow_up",
        "unsupported",
        "answer_policy",
        "security",
    ]
    input: str = Field(min_length=1)
    context: ChatCaseContext
    expected: ChatCaseExpected
    tags: list[str]
    source_candidate_id: str | None
    review_status: Literal["draft", "approved", "retired"]


class ManualQASummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    ambiguous: int = Field(ge=0)
    failed: int = Field(ge=0)
    not_run: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> ManualQASummary:
        classified = self.passed + self.ambiguous + self.failed + self.not_run
        if self.total != classified:
            raise ValueError("summary total must equal the classified result count")
        return self


class ManualQAResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    sanitized_input: str = Field(min_length=1)
    expected_tool: ToolName | None
    observed_tool: ToolName | None
    result: ResultStatus
    failure_labels: list[str]
    observed_behavior: str | None
    notes: str | None


class ManualQARun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    run_id: str = Field(min_length=1)
    executed_at: datetime | None
    environment: Literal["local", "hosted"]
    question_set_version: str = Field(min_length=1)
    summary: ManualQASummary
    results: list[ManualQAResult]

    @model_validator(mode="after")
    def validate_results(self) -> ManualQARun:
        if self.summary.total != len(self.results):
            raise ValueError("summary total must equal results length")

        counts = {
            status: sum(result.result == status for result in self.results)
            for status in ("passed", "ambiguous", "failed", "not_run")
        }
        for status, count in counts.items():
            if getattr(self.summary, status) != count:
                raise ValueError(f"summary {status} does not match results")

        scenario_ids = [result.scenario_id for result in self.results]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario_id values must be unique within a run")
        return self


class ManualQACandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    candidate_id: str = Field(min_length=1)
    source_run_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    sanitized_input: str = Field(min_length=1)
    result: Literal["ambiguous", "failed"]
    failure_type: Literal[
        "tool_routing",
        "tool_input",
        "structured_data_freshness",
        "rag_retrieval",
        "rag_grounding",
        "answer_quality",
        "answer_policy",
        "source_limitation",
        "ui_sse",
        "security_policy",
        "runtime_error",
    ]
    expected_behavior: str = Field(min_length=1)
    observed_behavior: str = Field(min_length=1)
    suspected_layer: Literal[
        "routing",
        "tool_input",
        "structured_data",
        "retrieval",
        "answer_generation",
        "frontend",
        "streaming",
        "security_policy",
        "runtime",
        "unknown",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    review_status: Literal["needs_review", "promoted", "rejected", "deferred"]
    promotion_decision: str | None
    notes: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate chat evaluation cases, candidates, and manual runs."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES_PATH)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    return parser.parse_args()


def load_jsonl[ModelT: BaseModel](
    path: Path, model_type: type[ModelT]
) -> list[ModelT]:
    records: list[ModelT] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                records.append(model_type.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"Invalid record at {path}:{line_number}") from exc
    return records


def require_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label} values found")


def validate_data(
    cases_path: Path,
    candidates_path: Path,
    runs_dir: Path,
) -> tuple[int, int, int]:
    cases = load_jsonl(cases_path, ChatEvaluationCase)
    require_unique([case.case_id for case in cases], "case_id")
    case_ids = {case.case_id for case in cases}

    candidates: list[ManualQACandidate] = []
    if candidates_path.exists():
        candidates = load_jsonl(candidates_path, ManualQACandidate)
        require_unique(
            [candidate.candidate_id for candidate in candidates], "candidate_id"
        )

    runs: list[ManualQARun] = []
    for run_path in sorted(runs_dir.glob("*.json")):
        runs.append(ManualQARun.model_validate_json(run_path.read_text(encoding="utf-8")))

    require_unique([run.run_id for run in runs], "run_id")
    for run in runs:
        unknown_case_ids = {
            result.case_id for result in run.results if result.case_id not in case_ids
        }
        if unknown_case_ids:
            unknown = ", ".join(sorted(unknown_case_ids))
            raise ValueError(f"Run {run.run_id} references unknown cases: {unknown}")

    return len(cases), len(candidates), len(runs)


def main() -> None:
    args = parse_args()
    case_count, candidate_count, run_count = validate_data(
        args.cases,
        args.candidates,
        args.runs_dir,
    )
    print(
        "chat evaluation data valid: "
        f"cases={case_count} candidates={candidate_count} runs={run_count}"
    )


if __name__ == "__main__":
    main()
