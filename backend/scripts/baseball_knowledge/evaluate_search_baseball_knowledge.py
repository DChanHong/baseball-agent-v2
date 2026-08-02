from __future__ import annotations

# search_baseball_knowledge Tool을 실제 OpenAI embedding과 로컬 pgvector DB로 실행해
# 대표 질문별 Top-1/Top-3 topic hit와 출력 계약을 검증한다.
import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.domains.baseball.tool.search_baseball_knowledge.handler import (
    DEFAULT_EMBEDDING_MODEL,
    SearchBaseballKnowledgeToolHandler,
)
from app.domains.baseball.tool.search_baseball_knowledge.retriever import (
    DEFAULT_RELEVANCE_THRESHOLD,
    PgVectorBaseballKnowledgeRetriever,
)
from app.domains.baseball.tool.search_baseball_knowledge.schemas import (
    BaseballKnowledgeType,
    SearchBaseballKnowledgeToolInput,
    SearchBaseballKnowledgeToolResult,
)

DEFAULT_DATASET_PATH = (
    REPOSITORY_ROOT
    / "data/baseball_knowledge/evaluation/cases/search_baseball_knowledge_cases.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    REPOSITORY_ROOT
    / "data/baseball_knowledge/evaluation/runs/tool/search_baseball_knowledge"
)


@dataclass(frozen=True, slots=True)
class ExpectedToolResult:
    answerable: bool
    top1_topic_ids: list[str]
    top3_topic_ids: list[str]
    top1_document_type: BaseballKnowledgeType | None
    required_source_urls: bool


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    id: str
    tool_input: SearchBaseballKnowledgeToolInput
    expected: ExpectedToolResult
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate search_baseball_knowledge tool retrieval quality.",
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
                    tool_input=SearchBaseballKnowledgeToolInput.model_validate(
                        payload["input"]
                    ),
                    expected=ExpectedToolResult(
                        answerable=expected_payload["answerable"],
                        top1_topic_ids=expected_payload["top1_topic_ids"],
                        top3_topic_ids=expected_payload["top3_topic_ids"],
                        top1_document_type=expected_payload["top1_document_type"],
                        required_source_urls=expected_payload["required_source_urls"],
                    ),
                    note=payload.get("note", ""),
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
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            handler = SearchBaseballKnowledgeToolHandler(
                openai_client=openai_client,
                retriever=PgVectorBaseballKnowledgeRetriever(session),
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
                            "top1_topic_ids": case.expected.top1_topic_ids,
                            "top3_topic_ids": case.expected.top3_topic_ids,
                            "top1_document_type": case.expected.top1_document_type,
                            "required_source_urls": case.expected.required_source_urls,
                        },
                        "actual": _actual_payload(actual),
                        "matches": compare_result(case.expected, actual),
                        "error": error,
                        "note": case.note,
                    }
                )
    finally:
        await engine.dispose()

    return results


def _actual_payload(
    actual: SearchBaseballKnowledgeToolResult | None,
) -> dict[str, Any] | None:
    if actual is None:
        return None

    payload = actual.model_dump(mode="json")
    payload["items"] = [
        {
            "rank": index + 1,
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document_type": item["document_type"],
            "title": item["title"],
            "topic_id": item["metadata"].get("topic_id"),
            "similarity": item["similarity"],
            "distance": item["distance"],
            "source_urls": item["source_urls"],
            "as_of": item["as_of"],
            "trust_level": item["trust_level"],
            "review_status": item["review_status"],
        }
        for index, item in enumerate(payload["items"])
    ]
    return payload


def compare_result(
    expected: ExpectedToolResult,
    actual: SearchBaseballKnowledgeToolResult | None,
) -> dict[str, bool]:
    if actual is None:
        return {
            "answerable": False,
            "top1_topic": False,
            "top3_topic": False,
            "top1_document_type": False,
            "source_urls": False,
            "no_rejected_results": False,
        }

    top1 = actual.items[0] if actual.items else None
    top1_topic_id = str(top1.metadata.get("topic_id")) if top1 else None
    top3_topic_ids = [
        str(item.metadata.get("topic_id"))
        for item in actual.items[:3]
        if item.metadata.get("topic_id") is not None
    ]
    top1_document_type = top1.document_type if top1 else None
    source_urls_ok = (
        all(item.source_urls for item in actual.items)
        if expected.required_source_urls
        else True
    )

    return {
        "answerable": actual.answerable == expected.answerable,
        "top1_topic": top1_topic_id in expected.top1_topic_ids,
        "top3_topic": any(
            topic_id in expected.top3_topic_ids for topic_id in top3_topic_ids
        ),
        "top1_document_type": top1_document_type == expected.top1_document_type,
        "source_urls": source_urls_ok,
        "no_rejected_results": all(
            item.review_status != "rejected" for item in actual.items
        ),
    }


def build_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    match_keys = [
        "answerable",
        "top1_topic",
        "top3_topic",
        "top1_document_type",
        "source_urls",
        "no_rejected_results",
    ]
    failed_case_ids = [
        result["id"]
        for result in results
        if result["error"] is not None or not all(result["matches"].values())
    ]

    metrics: dict[str, Any] = {
        "total": total,
        "passed": total - len(failed_case_ids),
        "failed_case_ids": failed_case_ids,
        "exact_match_accuracy": _safe_accuracy(total - len(failed_case_ids), total),
    }

    for key in match_keys:
        passed = sum(1 for result in results if result["matches"][key])
        metrics[f"{key}_accuracy"] = _safe_accuracy(passed, total)

    return metrics


def _safe_accuracy(passed: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(passed / total, 4)


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
        / f"{timestamp_for_filename}_{DEFAULT_EMBEDDING_MODEL}_tool-baseline.json"
    )
    payload = {
        "dataset_path": str(dataset_path),
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "relevance_threshold": DEFAULT_RELEVANCE_THRESHOLD,
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
    print(f"exact_match_accuracy={metrics['exact_match_accuracy']}")
    print(f"top1_topic_accuracy={metrics['top1_topic_accuracy']}")
    print(f"top3_topic_accuracy={metrics['top3_topic_accuracy']}")
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
