from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from openai import AsyncOpenAI

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.stadium_guide_sync.application import LocalCandidateApplier, OpenAIEmbedder
from scripts.stadium_guide_sync.evaluation import PgVectorCandidateEvaluator
from scripts.stadium_guide_sync.llm import OpenAICandidateGenerator
from scripts.stadium_guide_sync.production import ProductionPromotionService
from scripts.stadium_guide_sync.registry import load_registry, select_sources
from scripts.stadium_guide_sync.repository import StadiumGuideSyncRepository
from scripts.stadium_guide_sync.review import (
    candidate_detail,
    format_candidate_detail,
    format_candidate_list,
)
from scripts.stadium_guide_sync.schemas import SUPPORTED_DOCUMENT_TYPES, CandidateStatus
from scripts.stadium_guide_sync.service import StadiumGuideSyncService

DEFAULT_REGISTRY = REPOSITORY_ROOT / "data" / "stadium_guide" / "sources.json"
DEFAULT_RAW_ROOT = REPOSITORY_ROOT / "data" / "stadium_guide" / "raw"
DEFAULT_CASES_ROOT = REPOSITORY_ROOT / "data/stadium_guide/evaluation/cases"
DEFAULT_RUNS_ROOT = REPOSITORY_ROOT / "data/stadium_guide/evaluation/runs/candidate"


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
    candidates = subparsers.add_parser("candidates")
    candidate_commands = candidates.add_subparsers(
        dest="candidate_command", required=True
    )
    candidate_list = candidate_commands.add_parser("list")
    candidate_list.add_argument(
        "--status", choices=[status.value for status in CandidateStatus]
    )
    candidate_list.add_argument("--limit", type=int, default=50)
    candidate_show = candidate_commands.add_parser("show")
    candidate_show.add_argument("candidate_id")
    candidate_approve = candidate_commands.add_parser("approve")
    candidate_approve.add_argument("candidate_id")
    candidate_approve.add_argument("--note")
    candidate_reject = candidate_commands.add_parser("reject")
    candidate_reject.add_argument("candidate_id")
    candidate_reject.add_argument("--reason", required=True)
    apply_local = subparsers.add_parser("apply-local")
    apply_local.add_argument("candidate_id")
    promote_production = subparsers.add_parser("promote-production")
    promote_production.add_argument("candidate_id")
    rollback_production = subparsers.add_parser("rollback-production")
    rollback_production.add_argument("--logical-document-id", required=True)
    rollback_production.add_argument("--revision-id", required=True)
    return parser.parse_args()


def local_database_url(args: argparse.Namespace) -> str:
    load_env_file(args.env_file.resolve())
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required.")
    if not is_local_database_url(database_url):
        raise SystemExit(
            f"{args.command} uses the local DB only; "
            "set DATABASE_URL to a localhost Supabase URL"
        )
    return normalize_database_url(database_url)


def production_database_url(args: argparse.Namespace) -> str:
    load_env_file(args.env_file.resolve())
    database_url = os.environ.get("PROD_DATABASE_URL")
    if not database_url:
        raise SystemExit("PROD_DATABASE_URL is required.")
    if is_local_database_url(database_url):
        raise SystemExit(f"{args.command} requires a non-local PROD_DATABASE_URL")
    return normalize_database_url(database_url)


async def run_collect(args: argparse.Namespace) -> None:
    database_url = local_database_url(args)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")

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
    connection = await asyncpg.connect(database_url)
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


async def run_candidates(args: argparse.Namespace) -> None:
    database_url = local_database_url(args)
    registry = load_registry(args.registry.resolve())
    connection = await asyncpg.connect(database_url)
    try:
        repository = StadiumGuideSyncRepository(connection)
        if args.candidate_command == "list":
            status = CandidateStatus(args.status) if args.status else None
            rows = await repository.list_candidates(status=status, limit=args.limit)
            print(format_candidate_list(rows))
        elif args.candidate_command == "show":
            detail = await candidate_detail(
                repository=repository,
                registry=registry,
                repository_root=REPOSITORY_ROOT,
                candidate_id=args.candidate_id,
            )
            print(format_candidate_detail(detail))
        else:
            decision = (
                CandidateStatus.APPROVED
                if args.candidate_command == "approve"
                else CandidateStatus.REJECTED
            )
            note = args.note if decision == CandidateStatus.APPROVED else args.reason
            candidate = await repository.review_candidate(
                candidate_id=args.candidate_id,
                decision=decision,
                review_note=note,
            )
            print(f"candidate_id={candidate.candidate_id}")
            print(f"status={candidate.status.value}")
    finally:
        await connection.close()


async def run_apply_local(args: argparse.Namespace) -> None:
    database_url = local_database_url(args)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")
    registry = load_registry(args.registry.resolve())
    client = AsyncOpenAI(api_key=api_key)
    connection = await asyncpg.connect(database_url)
    try:
        repository = StadiumGuideSyncRepository(connection)
        evaluator = PgVectorCandidateEvaluator(
            connection=connection,
            client=client,
            cases_root=DEFAULT_CASES_ROOT,
            output_root=DEFAULT_RUNS_ROOT,
        )
        result = await LocalCandidateApplier(
            repository=repository,
            registry=registry,
            embedder=OpenAIEmbedder(client),
            evaluator=evaluator,
        ).apply(args.candidate_id)
    finally:
        await connection.close()
        await client.close()
    print(f"candidate_id={result.candidate_id}")
    print(f"revision_id={result.revision_id}")
    print(f"status={result.status.value}")
    print(f"already_applied={str(result.already_applied).lower()}")
    if result.evaluation:
        print(f"evaluation_run_id={result.evaluation.run_id}")
        print(f"evaluation_passed={str(result.evaluation.passed).lower()}")
        print(f"evaluation_output={result.evaluation.output_path}")


async def run_promote_production(args: argparse.Namespace) -> None:
    local_url = local_database_url(args)
    production_url = production_database_url(args)
    local = await asyncpg.connect(local_url)
    production = await asyncpg.connect(production_url, statement_cache_size=0)
    try:
        result = await ProductionPromotionService(
            local_connection=local,
            production_connection=production,
        ).promote(args.candidate_id)
    finally:
        await production.close()
        await local.close()
    print(f"candidate_id={result.candidate_id}")
    print(f"revision_id={result.revision_id}")
    print(f"logical_document_id={result.logical_document_id}")
    print(
        "previous_active_revision_id="
        f"{result.previous_active_revision_id or '-'}"
    )
    print(f"already_promoted={str(result.already_promoted).lower()}")


async def run_rollback_production(args: argparse.Namespace) -> None:
    production_url = production_database_url(args)
    production = await asyncpg.connect(production_url, statement_cache_size=0)
    try:
        result = await ProductionPromotionService(
            local_connection=production,
            production_connection=production,
        ).rollback(
            logical_document_id=args.logical_document_id,
            revision_id=args.revision_id,
        )
    finally:
        await production.close()
    print(f"logical_document_id={result.logical_document_id}")
    print(f"revision_id={result.revision_id}")
    print(
        "previous_active_revision_id="
        f"{result.previous_active_revision_id or '-'}"
    )
    print(f"already_active={str(result.already_active).lower()}")


async def main() -> None:
    args = parse_args()
    if args.command == "collect":
        await run_collect(args)
    elif args.command == "candidates":
        await run_candidates(args)
    elif args.command == "apply-local":
        await run_apply_local(args)
    elif args.command == "promote-production":
        await run_promote_production(args)
    elif args.command == "rollback-production":
        await run_rollback_production(args)


if __name__ == "__main__":
    asyncio.run(main())
