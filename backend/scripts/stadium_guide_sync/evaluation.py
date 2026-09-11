from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import asyncpg
from openai import AsyncOpenAI


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    run_id: str
    passed: bool
    output_path: Path
    summary: dict[str, object]


class CandidateEvaluator(Protocol):
    async def evaluate(
        self,
        *,
        stadium_id: str | None,
        document_type: str,
    ) -> EvaluationResult: ...


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


def load_cases(path: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        required = {"id", "query", "stadium_id", "expected_document_type", "case_type"}
        missing = required - set(value)
        if missing:
            raise ValueError(f"line {line_number} is missing: {sorted(missing)}")
        cases.append(value)
    return cases


def summarize(results: list[dict[str, object]]) -> dict[str, object]:
    positive = [result for result in results if result["case_type"] == "positive"]
    negative = [result for result in results if result["case_type"] == "negative"]
    return {
        "total_cases": len(results),
        "positive_cases": len(positive),
        "negative_cases": len(negative),
        "top1_hits": sum(bool(result["top1_hit"]) for result in positive),
        "top3_hits": sum(bool(result["top3_hit"]) for result in positive),
        "failed_top1_case_ids": [
            result["id"] for result in positive if not result["top1_hit"]
        ],
        "failed_top3_case_ids": [
            result["id"] for result in positive if not result["top3_hit"]
        ],
        "negative_cases_over_threshold": [
            result["id"]
            for result in negative
            if result["top_result_is_relevant"]
        ],
    }


def _summary_ids(summary: dict[str, object], key: str) -> set[str]:
    values = summary[key]
    if not isinstance(values, list):
        raise TypeError(f"evaluation summary {key} must be a list")
    return {str(value) for value in values}


class PgVectorCandidateEvaluator:
    def __init__(
        self,
        *,
        connection: asyncpg.Connection,
        client: AsyncOpenAI,
        cases_root: Path,
        output_root: Path,
        embedding_model: str = "text-embedding-3-small",
        relevance_threshold: float = 0.65,
    ) -> None:
        self._connection = connection
        self._client = client
        self._cases_root = cases_root
        self._output_root = output_root
        self._embedding_model = embedding_model
        self._relevance_threshold = relevance_threshold

    async def evaluate(
        self,
        *,
        stadium_id: str | None,
        document_type: str,
    ) -> EvaluationResult:
        target_cases = [
            case
            for case in load_cases(self._cases_root / "gocheok_food_search_cases.jsonl")
            if case["expected_document_type"] == document_type
        ]
        regression_cases = load_cases(self._cases_root / "sajik_search_cases.jsonl")
        cases = target_cases + regression_cases
        if not target_cases:
            raise ValueError(f"no target evaluation cases for {document_type}")
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=[str(case["query"]) for case in cases],
        )
        embeddings = [item.embedding for item in response.data]
        results: list[dict[str, object]] = []
        for case, embedding in zip(cases, embeddings, strict=True):
            rows = await self._search(
                query_embedding=embedding,
                stadium_id=str(case["stadium_id"]),
            )
            retrieved_types = [row["document_type"] for row in rows]
            top_distance = float(rows[0]["distance"]) if rows else None
            relevant = bool(
                top_distance is not None
                and top_distance <= self._relevance_threshold
            )
            top_result_metadata_complete = bool(
                rows and rows[0]["source_urls"] and rows[0]["as_of"]
            )
            is_positive = case["case_type"] == "positive"
            expected = case["expected_document_type"]
            results.append(
                {
                    **case,
                    "top1_hit": (
                        bool(retrieved_types and retrieved_types[0] == expected)
                        if is_positive
                        else None
                    ),
                    "top3_hit": (
                        expected in retrieved_types[:3] if is_positive else None
                    ),
                    "top_distance": top_distance,
                    "top_result_is_relevant": relevant,
                    "top_result_metadata_complete": top_result_metadata_complete,
                    "results": [
                        {
                            **dict(row),
                            "as_of": row["as_of"].isoformat(),
                            "distance": float(row["distance"]),
                        }
                        for row in rows
                    ],
                }
            )

        target_ids = {str(case["id"]) for case in target_cases}
        target_results = [result for result in results if result["id"] in target_ids]
        regression_results = [result for result in results if result["id"] not in target_ids]
        target_summary = summarize(target_results)
        regression_summary = summarize(regression_results)
        target_passed = (
            not target_summary["failed_top1_case_ids"]
            and not target_summary["failed_top3_case_ids"]
            and all(
                bool(result["top_result_metadata_complete"])
                for result in target_results
            )
        )
        regression_passed = (
            _summary_ids(regression_summary, "failed_top1_case_ids")
            <= {"sajik_011"}
            and not regression_summary["failed_top3_case_ids"]
            and _summary_ids(regression_summary, "negative_cases_over_threshold")
            <= {"sajik_008"}
        )
        passed = bool(target_passed and regression_passed)
        run_id = (
            f"SGE_{datetime.now(UTC):%Y%m%dT%H%M%S}_"
            f"{document_type}_{uuid4().hex[:8]}"
        )
        summary: dict[str, object] = {
            "passed": passed,
            "target": target_summary,
            "regression": regression_summary,
            "evaluated_stadium_id": stadium_id,
            "evaluated_document_type": document_type,
            "target_cases_missing_source_or_as_of": [
                result["id"]
                for result in target_results
                if not result["top_result_metadata_complete"]
            ],
        }
        output = {
            "run_id": run_id,
            "embedding_model": self._embedding_model,
            "relevance_threshold": self._relevance_threshold,
            "summary": summary,
            "cases": results,
        }
        self._output_root.mkdir(parents=True, exist_ok=True)
        path = self._output_root / f"{run_id}.json"
        path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return EvaluationResult(
            run_id=run_id,
            passed=passed,
            output_path=path,
            summary=summary,
        )

    async def _search(
        self,
        *,
        query_embedding: list[float],
        stadium_id: str,
    ) -> list[asyncpg.Record]:
        return list(
            await self._connection.fetch(
                """
                select
                  c.chunk_id, c.document_id, c.document_type, c.stadium_id,
                  c.title, c.source_ids, c.source_urls, c.as_of,
                  c.review_status,
                  c.embedding <=> $1::extensions.vector as distance
                from public.rag_chunks c
                join public.rag_documents d on d.document_id = c.document_id
                where (c.stadium_id = $2 or c.stadium_id is null)
                  and d.is_active
                  and d.logical_document_id is not null
                  and (c.review_status = 'approved' or d.legacy_unreviewed)
                  and c.embedding is not null
                order by (c.stadium_id = $2) desc nulls last,
                         c.embedding <=> $1::extensions.vector
                limit 3
                """,
                vector_literal(query_embedding),
                stadium_id,
            )
        )
