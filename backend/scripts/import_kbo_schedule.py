from __future__ import annotations

# 정규화된 KBO 일정 JSON을 로컬 Supabase `kbo_games` 테이블에 적재한다.
# 일정 raw 데이터를 수집하고 normalized JSON을 만든 뒤 실행하는 스크립트다.

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.kbo_schedule_import.key_builder import build_kbo_game_upsert_rows  # noqa: E402
from scripts.kbo_schedule_import.loader import load_normalized_kbo_schedule_file  # noqa: E402
from scripts.kbo_schedule_import.service import upsert_all_kbo_games_from_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import normalized KBO schedule JSON into kbo_games.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to data/processed/kbo_schedule_<year>_normalized.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the file and print the planned row count without writing to DB.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    file_path = args.file.resolve()

    if args.dry_run:
        games = load_normalized_kbo_schedule_file(file_path)
        rows = build_kbo_game_upsert_rows(games)
        print(f"file={file_path}")
        print(f"parsed_games={len(games)}")
        print(f"upsert_rows={len(rows)}")
        print(f"first_internal_game_key={rows[0].internal_game_key if rows else '-'}")
        return

    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        try:
            result = await upsert_all_kbo_games_from_file(
                session,
                file_path=file_path,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    print(f"file={result.file_path}")
    print(f"total={result.total_count}")
    print(f"inserted={result.inserted_count}")
    print(f"updated={result.updated_count}")
    print(f"unchanged={result.unchanged_count}")
    print(f"status_history={result.status_history_count}")


if __name__ == "__main__":
    asyncio.run(main())
