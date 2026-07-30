from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import asyncpg
from openai import AsyncOpenAI


DEFAULT_CHUNKS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "stadium_guide"
    / "embedded_input"
    / "stadium_guide_chunks.jsonl"
)
DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed stadium guide chunks and upsert them into local Supabase pgvector tables."
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS_PATH,
        help="Input chunk JSONL path.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Environment file containing OPENAI_API_KEY and DATABASE_URL.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding API batch size.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and print summary without calling OpenAI or writing to DB.",
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


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        chunk = json.loads(line)
        validate_chunk(chunk, line_number)
        chunks.append(chunk)
    return chunks


def validate_chunk(chunk: dict[str, Any], line_number: int) -> None:
    required_fields = [
        "chunk_id",
        "document_id",
        "chunk_index",
        "document_type",
        "stadium_id",
        "team_id",
        "title",
        "as_of",
        "trust_level",
        "review_status",
        "source_ids",
        "source_urls",
        "embedding_model",
        "embedding_dimensions",
        "embedding_text",
        "content",
        "content_hash",
        "metadata",
    ]
    missing = [field for field in required_fields if field not in chunk]
    if missing:
        raise ValueError(f"Line {line_number} is missing required fields: {missing}")

    if chunk["embedding_dimensions"] != 1536:
        raise ValueError(
            f"Line {line_number} has unsupported embedding_dimensions: "
            f"{chunk['embedding_dimensions']}"
        )


def db_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(chunk.get("metadata") or {})
    metadata.pop("source_file", None)
    return metadata


def vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


async def embed_chunks(
    client: AsyncOpenAI,
    chunks: list[dict[str, Any]],
    batch_size: int,
) -> list[list[float]]:
    if not chunks:
        return []

    model = chunks[0]["embedding_model"]
    embeddings: list[list[float]] = []

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        response = await client.embeddings.create(
            model=model,
            input=[chunk["embedding_text"] for chunk in batch],
        )
        embeddings.extend(item.embedding for item in response.data)

    return embeddings


async def upsert_chunks(
    connection: asyncpg.Connection,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> None:
    async with connection.transaction():
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            metadata = db_metadata(chunk)
            await connection.execute(
                """
                insert into public.rag_documents (
                  document_id,
                  document_type,
                  stadium_id,
                  team_id,
                  title,
                  as_of,
                  trust_level,
                  review_status,
                  source_ids,
                  source_urls,
                  content_hash,
                  metadata
                )
                values (
                  $1, $2, $3, $4, $5, $6::date, $7, $8, $9, $10, $11, $12::jsonb
                )
                on conflict (document_id) do update
                set
                  document_type = excluded.document_type,
                  stadium_id = excluded.stadium_id,
                  team_id = excluded.team_id,
                  title = excluded.title,
                  as_of = excluded.as_of,
                  trust_level = excluded.trust_level,
                  review_status = excluded.review_status,
                  source_ids = excluded.source_ids,
                  source_urls = excluded.source_urls,
                  content_hash = excluded.content_hash,
                  metadata = excluded.metadata,
                  updated_at = now()
                """,
                chunk["document_id"],
                chunk["document_type"],
                chunk["stadium_id"],
                chunk["team_id"],
                chunk["title"],
                parse_date(chunk["as_of"]),
                chunk["trust_level"],
                chunk["review_status"],
                chunk["source_ids"],
                chunk["source_urls"],
                chunk["content_hash"],
                json.dumps(metadata, ensure_ascii=False),
            )

            await connection.execute(
                """
                insert into public.rag_chunks (
                  chunk_id,
                  document_id,
                  chunk_index,
                  stadium_id,
                  team_id,
                  document_type,
                  title,
                  chunk_text,
                  content,
                  embedding,
                  embedding_model,
                  embedding_dimensions,
                  as_of,
                  trust_level,
                  review_status,
                  source_ids,
                  source_urls,
                  content_hash,
                  metadata
                )
                values (
                  $1, $2, $3, $4, $5, $6, $7, $8, $9,
                  $10::extensions.vector,
                  $11, $12, $13::date, $14, $15, $16, $17, $18, $19::jsonb
                )
                on conflict (chunk_id) do update
                set
                  document_id = excluded.document_id,
                  chunk_index = excluded.chunk_index,
                  stadium_id = excluded.stadium_id,
                  team_id = excluded.team_id,
                  document_type = excluded.document_type,
                  title = excluded.title,
                  chunk_text = excluded.chunk_text,
                  content = excluded.content,
                  embedding = excluded.embedding,
                  embedding_model = excluded.embedding_model,
                  embedding_dimensions = excluded.embedding_dimensions,
                  as_of = excluded.as_of,
                  trust_level = excluded.trust_level,
                  review_status = excluded.review_status,
                  source_ids = excluded.source_ids,
                  source_urls = excluded.source_urls,
                  content_hash = excluded.content_hash,
                  metadata = excluded.metadata,
                  updated_at = now()
                """,
                chunk["chunk_id"],
                chunk["document_id"],
                chunk["chunk_index"],
                chunk["stadium_id"],
                chunk["team_id"],
                chunk["document_type"],
                chunk["title"],
                chunk["embedding_text"],
                chunk["content"],
                vector_literal(embedding),
                chunk["embedding_model"],
                chunk["embedding_dimensions"],
                parse_date(chunk["as_of"]),
                chunk["trust_level"],
                chunk["review_status"],
                chunk["source_ids"],
                chunk["source_urls"],
                chunk["content_hash"],
                json.dumps(metadata, ensure_ascii=False),
            )


async def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)

    chunks = load_chunks(args.chunks)
    print(f"Loaded {len(chunks)} chunks from {args.chunks}")

    if args.dry_run:
        for chunk in chunks:
            print(
                chunk["chunk_id"],
                chunk["document_type"],
                chunk["embedding_model"],
                chunk["embedding_dimensions"],
            )
        return

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required.")

    client = AsyncOpenAI(api_key=openai_api_key)
    embeddings = await embed_chunks(client, chunks, args.batch_size)

    connection = await asyncpg.connect(normalize_database_url(database_url))
    try:
        await upsert_chunks(connection, chunks, embeddings)
    finally:
        await connection.close()

    print(f"Upserted {len(chunks)} chunks into rag_documents/rag_chunks")


if __name__ == "__main__":
    asyncio.run(main())
