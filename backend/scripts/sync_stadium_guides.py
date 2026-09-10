from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import asyncpg

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.stadium_guide_sync.llm import OpenAICandidateGenerator
from scripts.stadium_guide_sync.registry import load_registry, select_sources
from scripts.stadium_guide_sync.repository import StadiumGuideSyncRepository
from scripts.stadium_guide_sync.schemas import SUPPORTED_DOCUMENT_TYPES
from scripts.stadium_guide_sync.service import StadiumGuideSyncService

DEFAULT_REGISTRY = REPOSITORY_ROOT / "data" / "stadium_guide" / "sources.json"
DEFAULT_RAW_ROOT = REPOSITORY_ROOT / "data" / "stadium_guide" / "raw"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_database_url(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def is_local_database_url(value: str) -> bool:
    host = urlparse(normalize_database_url(value)).hostname
    return host in {"127.0.0.1", "localhost", "::1"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect registered stadium sources and create review candidates."
    )
    parser.add_argument("--env-file", type=Path, default=BACKEND_ROOT / ".env")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect")
    target = collect.add_mutually_exclusive_group(required=True)
    target.add_argument("--stadium-id")
    target.add_argument("--source-id")
    target.add_argument("--all", action="store_true")
    collect.add_argument(
        "--document-type",
        choices=sorted(SUPPORTED_DOCUMENT_TYPES),
    )
    return parser.parse_args()


async def run_collect(args: argparse.Namespace) -> None:
    load_env_file(args.env_file.resolve())
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")
    if not is_local_database_url(database_url):
        raise SystemExit(
            "collect stores review candidates in the local DB only; "
            "set DATABASE_URL to a localhost Supabase URL"
        )

    registry = load_registry(args.registry.resolve())
    sources = select_sources(
        registry,
        stadium_id=args.stadium_id,
        source_id=args.source_id,
        document_type=args.document_type,
        include_all=args.all,
    )
    if not sources:
        raise SystemExit("No enabled sources matched the requested scope.")

    scope = {
        "stadium_id": args.stadium_id,
        "source_id": args.source_id,
        "all": args.all,
        "document_type": args.document_type,
    }
    connection = await asyncpg.connect(normalize_database_url(database_url))
    try:
        repository = StadiumGuideSyncRepository(connection)
        generator = OpenAICandidateGenerator(
            api_key=api_key,
            model=os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
            timeout_seconds=float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "60")),
        )
        service = StadiumGuideSyncService(
            repository=repository,
            generator=generator,
            raw_root=DEFAULT_RAW_ROOT,
            repository_root=REPOSITORY_ROOT,
        )
        result = await service.run(
            sources=sources,
            scope=scope,
            requested_document_type=args.document_type,
        )
    finally:
        await connection.close()

    print(f"run_id={result.run_id}")
    print(f"source_count={result.source_count}")
    for key, value in result.counts.items():
        print(f"{key}={value}")
    print(
        "candidate_ids="
        + (",".join(result.candidate_ids) if result.candidate_ids else "-")
    )


async def main() -> None:
    args = parse_args()
    if args.command == "collect":
        await run_collect(args)


if __name__ == "__main__":
    asyncio.run(main())
