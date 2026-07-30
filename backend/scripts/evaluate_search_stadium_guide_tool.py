from __future__ import annotations

# search_stadium_guide Tool을 실제 OpenAI embedding과 로컬 pgvector DB로 실행해
# 대표 질문별 출력 계약과 검색 품질을 검증한다.
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

from app.core.database import async_session_factory
from app.core.llm import get_openai_client
from app.domains.baseball.tool.search_stadium_guide.handler import (
    DEFAULT_EMBEDDING_MODEL,
    SearchStadiumGuideToolHandler,
)
from app.domains.baseball.tool.search_stadium_guide.retriever import (
    PgVectorStadiumGuideRetriever,
)
from app.domains.baseball.tool.search_stadium_guide.schemas import (
    SearchStadiumGuideToolInput,
    StadiumGuideType,
)

DEFAULT_DATASET_PATH = (
    REPOSITORY_ROOT
    / "data/stadium_guide/evaluation/cases/search_stadium_guide_tool_cases.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    REPOSITORY_ROOT
    / "data/stadium_guide/evaluation/runs/tool/search_stadium_guide"
)


@dataclass(frozen=True, slots=True)
class ExpectedToolResult:
    answerable: bool
    top1_document_type: StadiumGuideType | None
    required_source_urls: bool


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    id: str
    tool_input: SearchStadiumGuideToolInput
    expected: ExpectedToolResult


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate search_stadium_guide tool with representative questions.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the JSONL tool evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the evaluation run JSON should be saved.",
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
                expected_payload = payload["expected"]
                case = EvaluationCase(
                    id=payload["id"],
                    tool_input=SearchStadiumGuideToolInput.model_validate(
                        payload["input"]
                    ),
                    expected=ExpectedToolResult(
                        answerable=expected_payload["answerable"],
                        top1_document_type=expected_payload["top1_document_type"],
                        required_source_urls=expected_payload["required_source_urls"],
                    ),
                )
            except Exception as exc:
                raise ValueError(
                    f"Invalid evaluation case at line {line_number}: {dataset_path}"
                ) from exc

            cases.append(case)
            if limit is not None and len(cases) >= limit:
                break

    return cases


async def evaluate_cases(cases: list[EvaluationCase]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    openai_client = get_openai_client()

    async with async_session_factory() as session:
        handler = SearchStadiumGuideToolHandler(
            openai_client=openai_client,
            retriever=PgVectorStadiumGuideRetriever(session),
        )

        for case in cases:
            try:
                actual = await handler.execute(case.tool_input)
                error = None
            except Exception as exc:  # noqa: BLE001
                actual = None
                error = f"{type(exc).__name__}: {exc}"

            results.append(
                {
                    "id": case.id,
                    "input": case.tool_input.model_dump(mode="json"),
                    "expected": {
                        "answerable": case.expected.answerable,
                        "top1_document_type": case.expected.top1_document_type,
                        "required_source_urls": case.expected.required_source_urls,
                    },
                    "actual": actual.model_dump(mode="json") if actual else None,
                    "matches": compare_result(case.expected, actual),
                    "error": error,
                }
            )

    return results


def compare_result(
    expected: ExpectedToolResult,
    actual: Any,
) -> dict[str, bool]:
    if actual is None:
        return {
            "answerable": False,
            "top1_document_type": False,
            "source_urls": False,
            "no_rejected_results": False,
        }

    top1_document_type = actual.items[0].document_type if actual.items else None
    source_urls_ok = (
        all(item.source_urls for item in actual.items)
        if expected.required_source_urls
        else True
    )

    return {
        "answerable": actual.answerable == expected.answerable,
        "top1_document_type": top1_document_type == expected.top1_document_type,
        "source_urls": source_urls_ok,
        "no_rejected_results": all(
            item.review_status != "rejected" for item in actual.items
        ),
    }


def build_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    failed_case_ids = [
        result["id"]
        for result in results
        if result["error"] is not None or not all(result["matches"].values())
    ]

    return {
        "total": total,
        "passed": total - len(failed_case_ids),
        "failed_case_ids": failed_case_ids,
        "pass_rate": round((total - len(failed_case_ids)) / total, 4)
        if total
        else 0.0,
    }


def save_run_result(
    output_dir: Path,
    *,
    dataset_path: Path,
    run_timestamp: datetime,
    metrics: dict[str, Any],
    results: list[dict[str, Any]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_for_filename = run_timestamp.strftime("%Y-%m-%d_%H%M%S")
    output_path = (
        output_dir
        / f"{timestamp_for_filename}_{DEFAULT_EMBEDDING_MODEL}_representative.json"
    )
    payload = {
        "dataset_path": str(dataset_path),
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
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
    print(f"passed={metrics['passed']}")
    print(f"pass_rate={metrics['pass_rate']}")
    print(f"failed_case_ids={','.join(metrics['failed_case_ids']) or '-'}")
    print(f"output_path={output_path}")


async def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.resolve()
    output_dir = args.output_dir.resolve()

    cases = load_cases(dataset_path, args.limit)
    results = await evaluate_cases(cases)
    metrics = build_metrics(results)
    output_path = save_run_result(
        output_dir,
        dataset_path=dataset_path,
        run_timestamp=datetime.now(UTC),
        metrics=metrics,
        results=results,
    )
    print_metrics(metrics, output_path)


if __name__ == "__main__":
    asyncio.run(main())
