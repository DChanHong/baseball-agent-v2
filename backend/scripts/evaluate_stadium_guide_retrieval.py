from __future__ import annotations

# 구장 가이드 RAG 검색 평가셋을 실행하고 Top-1/Top-3 hit 결과를 JSON으로 저장한다.
# 질문도 같은 embedding 모델로 변환한 뒤 pgvector에서 stadium_id filter로 검색한다.

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
from openai import AsyncOpenAI


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_CASES_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "stadium_guide"
    / "evaluation"
    / "cases"
    / "sajik_search_cases.jsonl"
)
DEFAULT_OUTPUT_DIR = (
    REPOSITORY_ROOT / "data" / "stadium_guide" / "evaluation" / "runs"
)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_TOP_K = 3
DEFAULT_RELEVANCE_THRESHOLD = 0.65


def log(message: str) -> None:
    print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate stadium guide pgvector retrieval quality."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="Input retrieval evaluation JSONL path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the run result JSON will be written.",
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="OpenAI embedding model used for query embeddings.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of chunks to retrieve per query.",
    )
    parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=DEFAULT_RELEVANCE_THRESHOLD,
        help="Distance threshold used to mark whether the top result is relevant enough.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Environment file containing OPENAI_API_KEY and DATABASE_URL.",
    )
    parser.add_argument(
        "--run-name",
        default="baseline",
        help="Human-readable run name used in the output filename.",
    )
    parser.add_argument(
        "--db-timeout",
        type=float,
        default=10.0,
        help="Database connection timeout in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate cases and print summary without calling OpenAI or DB.",
    )
    return parser.parse_args()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def normalize_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def mask_database_url(database_url: str) -> str:
    normalized_url = normalize_database_url(database_url)
    parsed = urlsplit(normalized_url)
    if not parsed.password:
        return normalized_url

    username = parsed.username or ""
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{username}:***@{hostname}{port}"
    return urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )


def vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        validate_case(case, line_number)
        cases.append(case)
    return cases


def validate_case(case: dict[str, Any], line_number: int) -> None:
    required_fields = [
        "id",
        "query",
        "stadium_id",
        "expected_document_type",
        "case_type",
        "note",
    ]
    missing = [field for field in required_fields if field not in case]
    if missing:
        raise ValueError(f"Line {line_number} is missing required fields: {missing}")

    if case["case_type"] not in {"positive", "negative"}:
        raise ValueError(f"Line {line_number} has invalid case_type: {case['case_type']}")


async def embed_queries(
    client: AsyncOpenAI,
    cases: list[dict[str, Any]],
    embedding_model: str,
) -> list[list[float]]:
    log(
        "OpenAI embedding 요청 시작: "
        f"model={embedding_model}, query_count={len(cases)}"
    )
    response = await client.embeddings.create(
        model=embedding_model,
        input=[case["query"] for case in cases],
    )
    embeddings = [item.embedding for item in response.data]
    dimensions = len(embeddings[0]) if embeddings else 0
    log(
        "OpenAI embedding 응답 완료: "
        f"embedding_count={len(embeddings)}, dimensions={dimensions}"
    )
    return embeddings


async def search_chunks(
    connection: asyncpg.Connection,
    query_embedding: list[float],
    stadium_id: str,
    top_k: int,
) -> list[dict[str, Any]]:
    rows = await connection.fetch(
        """
        select
          chunk_id,
          document_id,
          document_type,
          stadium_id,
          team_id,
          title,
          source_urls,
          as_of,
          trust_level,
          review_status,
          embedding <=> $1::extensions.vector as distance
        from public.rag_chunks
        where stadium_id = $2
          and embedding is not null
        order by embedding <=> $1::extensions.vector
        limit $3
        """,
        vector_literal(query_embedding),
        stadium_id,
        top_k,
    )
    return [dict(row) for row in rows]


async def connect_database(database_url: str, timeout: float) -> asyncpg.Connection:
    log(
        "DB 연결 시도: "
        f"url={mask_database_url(database_url)}, timeout={timeout}s"
    )
    try:
        connection = await asyncpg.connect(
            normalize_database_url(database_url),
            timeout=timeout,
            ssl=False,
        )
        await connection.execute("select 1")
        log("DB 연결 확인 완료: select 1")
        return connection
    except TimeoutError as exc:
        raise RuntimeError(
            "로컬 Supabase PostgreSQL 연결 시간이 초과되었습니다. "
            "Supabase가 실행 중인지 확인하고, 필요하면 `supabase stop` 후 "
            "`supabase start`로 재시작한 뒤 다시 실행하세요."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "로컬 Supabase PostgreSQL에 연결할 수 없습니다. "
            "`supabase start` 상태와 DATABASE_URL의 host/port를 확인하세요."
        ) from exc


def evaluate_case(
    case: dict[str, Any],
    results: list[dict[str, Any]],
    relevance_threshold: float,
) -> dict[str, Any]:
    expected = case["expected_document_type"]
    retrieved_types = [result["document_type"] for result in results]
    top_distance = float(results[0]["distance"]) if results else None
    top_result_is_relevant = (
        top_distance is not None and top_distance <= relevance_threshold
    )

    if case["case_type"] == "negative":
        top1_hit = None
        top3_hit = None
    else:
        top1_hit = bool(retrieved_types and retrieved_types[0] == expected)
        top3_hit = expected in retrieved_types[:3]

    return {
        "id": case["id"],
        "query": case["query"],
        "case_type": case["case_type"],
        "stadium_id": case["stadium_id"],
        "expected_document_type": expected,
        "top1_hit": top1_hit,
        "top3_hit": top3_hit,
        "top_distance": top_distance,
        "relevance_threshold": relevance_threshold,
        "top_result_is_relevant": top_result_is_relevant,
        "retrieved_document_types": retrieved_types,
        "results": [
            {
                "rank": index + 1,
                "chunk_id": result["chunk_id"],
                "document_id": result["document_id"],
                "document_type": result["document_type"],
                "title": result["title"],
                "distance": float(result["distance"]),
                "source_urls": result["source_urls"],
                "as_of": result["as_of"].isoformat(),
                "trust_level": result["trust_level"],
                "review_status": result["review_status"],
            }
            for index, result in enumerate(results)
        ],
        "note": case["note"],
    }


def summarize(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    positive_results = [
        result for result in case_results if result["case_type"] == "positive"
    ]
    total_positive = len(positive_results)
    top1_hits = sum(1 for result in positive_results if result["top1_hit"])
    top3_hits = sum(1 for result in positive_results if result["top3_hit"])
    negative_results = [
        result for result in case_results if result["case_type"] == "negative"
    ]

    return {
        "total_cases": len(case_results),
        "positive_cases": total_positive,
        "negative_cases": len(negative_results),
        "top1_hits": top1_hits,
        "top3_hits": top3_hits,
        "top1_accuracy": top1_hits / total_positive if total_positive else None,
        "top3_accuracy": top3_hits / total_positive if total_positive else None,
        "negative_cases_over_threshold": [
            result["id"]
            for result in negative_results
            if result["top_result_is_relevant"]
        ],
        "failed_top1_case_ids": [
            result["id"] for result in positive_results if not result["top1_hit"]
        ],
        "failed_top3_case_ids": [
            result["id"] for result in positive_results if not result["top3_hit"]
        ],
    }


def output_path(
    output_dir: Path,
    run_name: str,
    embedding_model: str,
    cases_path: Path,
) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    safe_model = embedding_model.replace("/", "-")
    safe_dataset = cases_path.stem
    return output_dir / f"{timestamp}_{safe_dataset}_{safe_model}_{run_name}.json"


async def main() -> None:
    args = parse_args()
    log(f"env 파일 로드 시도: {args.env_file}")
    load_env_file(args.env_file)

    cases = load_cases(args.cases)
    log(f"Loaded {len(cases)} cases from {args.cases}")

    if args.dry_run:
        for case in cases:
            log(f"{case['id']} {case['case_type']} {case['expected_document_type']}")
        return

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")
    log("OPENAI_API_KEY 확인 완료: 값은 로그에 출력하지 않습니다.")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required.")
    log(f"DATABASE_URL 확인 완료: {mask_database_url(database_url)}")

    log(
        "OpenAI client 객체 생성 준비: "
        f"model={args.embedding_model}"
    )
    client = AsyncOpenAI(api_key=openai_api_key)
    log(
        "OpenAI client 객체 생성 완료: "
        "이 단계는 네트워크 호출이 아니며, 실제 호출은 embedding 요청에서 발생합니다."
    )

    try:
        connection = await connect_database(database_url, args.db_timeout)
    except RuntimeError as exc:
        print(f"DB 연결 실패: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc

    try:
        query_embeddings = await embed_queries(client, cases, args.embedding_model)

        case_results = []
        for index, (case, query_embedding) in enumerate(
            zip(cases, query_embeddings, strict=True),
            start=1,
        ):
            log(
                f"\n[{index}/{len(cases)}] 질문: {case['query']}\n"
                f"기대 문서: {case['expected_document_type']}"
            )
            results = await search_chunks(
                connection=connection,
                query_embedding=query_embedding,
                stadium_id=case["stadium_id"],
                top_k=args.top_k,
            )
            case_result = evaluate_case(case, results, args.relevance_threshold)
            case_results.append(case_result)

            for result in case_result["results"]:
                log(
                    f"  {result['rank']}. {result['document_type']} "
                    f"distance={result['distance']:.6f} "
                    f"title={result['title']}"
                )

            log(
                f"결과: top1={case_result['top1_hit']} "
                f"top3={case_result['top3_hit']} "
                f"relevant={case_result['top_result_is_relevant']}"
            )
    finally:
        await connection.close()

    summary = summarize(case_results)
    run_result = {
        "dataset_path": str(args.cases),
        "embedding_model": args.embedding_model,
        "top_k": args.top_k,
        "relevance_threshold": args.relevance_threshold,
        "run_name": args.run_name,
        "run_timestamp": datetime.now(UTC).isoformat(),
        "summary": summary,
        "cases": case_results,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = output_path(args.output_dir, args.run_name, args.embedding_model, args.cases)
    path.write_text(
        json.dumps(run_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    log(f"Wrote run result to {path}")
    log(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
