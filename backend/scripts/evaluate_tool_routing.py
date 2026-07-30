from __future__ import annotations

# LLM Tool Router 오프라인 평가 케이스를 실행하고 결과 JSON을 저장한다.
# 사용자 메시지가 기대한 Agent Tool로 라우팅되는지 측정할 때 사용한다.

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.routing_schemas import (
    ToolRoutingDecision,
    ToolRoutingUserContext,
)
from app.agent.routing_service import ToolRoutingService
from app.core.config import get_settings

DEFAULT_DATASET_PATH = (
    REPOSITORY_ROOT / "data/evaluation/tool_routing/find_kbo_game_cases.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    REPOSITORY_ROOT / "data/evaluation/runs/tool_routing/find_kbo_game"
)
DEFAULT_PROMPT_VERSION = "few-shot-v1"


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    id: str
    message: str
    user_context: ToolRoutingUserContext
    expected: ToolRoutingDecision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate LLM tool routing for find_kbo_game.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the JSONL routing evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the evaluation run JSON should be saved.",
    )
    parser.add_argument(
        "--prompt-version",
        default=DEFAULT_PROMPT_VERSION,
        help="Prompt version label to store with the run result.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of cases to evaluate.",
    )
    return parser.parse_args()


def load_cases(dataset_path: Path, limit: int | None = None) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []

    with dataset_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped_line = line.strip()
            if not stripped_line:
                continue

            payload = json.loads(stripped_line)
            try:
                case = EvaluationCase(
                    id=payload["id"],
                    message=payload["input"],
                    user_context=ToolRoutingUserContext.model_validate(
                        payload["user_context"]
                    ),
                    expected=ToolRoutingDecision.model_validate(payload["expected"]),
                )
            except Exception as exc:
                raise ValueError(
                    f"Invalid evaluation case at line {line_number}: {dataset_path}"
                ) from exc

            cases.append(case)
            if limit is not None and len(cases) >= limit:
                break

    return cases


async def evaluate_cases(
    service: ToolRoutingService,
    cases: list[EvaluationCase],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for case in cases:
        try:
            actual = await service.execute(case.message, case.user_context)
            error = None
        except Exception as exc:  # noqa: BLE001
            actual = None
            error = f"{type(exc).__name__}: {exc}"

        results.append(
            {
                "id": case.id,
                "input": case.message,
                "user_context": case.user_context.model_dump(mode="json"),
                "expected": case.expected.model_dump(mode="json"),
                "actual": actual.model_dump(mode="json") if actual else None,
                "matches": _compare_decisions(case.expected, actual),
                "error": error,
            }
        )

    return results


def _compare_decisions(
    expected: ToolRoutingDecision,
    actual: ToolRoutingDecision | None,
) -> dict[str, bool]:
    if actual is None:
        return {
            "is_in_scope": False,
            "should_call_tool": False,
            "tool_name": False,
            "team_id": False,
            "date": False,
            "date_range": False,
            "clarification": False,
            "unsupported": False,
        }

    expected_args = expected.args
    actual_args = actual.args

    return {
        "is_in_scope": expected.is_in_scope == actual.is_in_scope,
        "should_call_tool": expected.should_call_tool == actual.should_call_tool,
        "tool_name": expected.tool_name == actual.tool_name,
        "team_id": _arg_value(expected_args, "team_id") == _arg_value(actual_args, "team_id"),
        "date": _arg_value(expected_args, "date") == _arg_value(actual_args, "date"),
        "date_range": (
            _arg_value(expected_args, "date_from") == _arg_value(actual_args, "date_from")
            and _arg_value(expected_args, "date_to") == _arg_value(actual_args, "date_to")
        ),
        "clarification": (
            expected.needs_clarification == actual.needs_clarification
            and expected.clarification_reason == actual.clarification_reason
        ),
        "unsupported": expected.unsupported_reason == actual.unsupported_reason,
    }


def _arg_value(args: Any, key: str) -> Any:
    if args is None:
        return None
    return getattr(args, key)


def build_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    match_keys = [
        "is_in_scope",
        "should_call_tool",
        "tool_name",
        "team_id",
        "date",
        "date_range",
        "clarification",
        "unsupported",
    ]
    exact_failed_case_ids = [
        result["id"]
        for result in results
        if not all(result["matches"].values()) or result["error"] is not None
    ]

    metrics: dict[str, Any] = {
        "total": total,
        "failed_case_ids": exact_failed_case_ids,
    }

    for key in match_keys:
        passed = sum(1 for result in results if result["matches"][key])
        metrics[f"{key}_accuracy"] = _safe_accuracy(passed, total)

    exact_matches = sum(
        1
        for result in results
        if all(result["matches"].values()) and result["error"] is None
    )
    metrics["exact_match_accuracy"] = _safe_accuracy(exact_matches, total)

    return metrics


def _safe_accuracy(passed: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(passed / total, 4)


def save_run_result(
    output_dir: Path,
    *,
    dataset_path: Path,
    model: str,
    prompt_version: str,
    run_timestamp: datetime,
    metrics: dict[str, Any],
    results: list[dict[str, Any]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_for_filename = run_timestamp.strftime("%Y-%m-%d_%H%M%S")
    output_path = output_dir / f"{timestamp_for_filename}_{model}_{prompt_version}.json"
    payload = {
        "dataset_path": str(dataset_path),
        "model": model,
        "prompt_version": prompt_version,
        "run_timestamp": run_timestamp.isoformat(),
        "metrics": metrics,
        "results": results,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def print_metrics(metrics: dict[str, Any], output_path: Path) -> None:
    print(f"total={metrics['total']}")
    print(f"is_in_scope_accuracy={metrics['is_in_scope_accuracy']}")
    print(f"should_call_tool_accuracy={metrics['should_call_tool_accuracy']}")
    print(f"tool_name_accuracy={metrics['tool_name_accuracy']}")
    print(f"team_id_accuracy={metrics['team_id_accuracy']}")
    print(f"date_accuracy={metrics['date_accuracy']}")
    print(f"date_range_accuracy={metrics['date_range_accuracy']}")
    print(f"clarification_accuracy={metrics['clarification_accuracy']}")
    print(f"unsupported_accuracy={metrics['unsupported_accuracy']}")
    print(f"exact_match_accuracy={metrics['exact_match_accuracy']}")
    print(f"failed_case_ids={','.join(metrics['failed_case_ids']) or '-'}")
    print(f"output_path={output_path}")


async def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.resolve()
    output_dir = args.output_dir.resolve()
    settings = get_settings()

    cases = load_cases(dataset_path, args.limit)
    service = ToolRoutingService(model=settings.openai_model)
    results = await evaluate_cases(service, cases)
    metrics = build_metrics(results)
    run_timestamp = datetime.now(UTC)
    output_path = save_run_result(
        output_dir,
        dataset_path=dataset_path,
        model=settings.openai_model,
        prompt_version=args.prompt_version,
        run_timestamp=run_timestamp,
        metrics=metrics,
        results=results,
    )
    print_metrics(metrics, output_path)


if __name__ == "__main__":
    asyncio.run(main())
