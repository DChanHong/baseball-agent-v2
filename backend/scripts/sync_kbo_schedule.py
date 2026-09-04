from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.kbo_schedule_import.client import (
    KboScheduleClient,
    KboScheduleRequest,
)
from scripts.kbo_schedule_import.key_builder import (
    build_kbo_game_upsert_rows,
)
from scripts.kbo_schedule_import.normalizer import (
    normalize_kbo_schedule_payload,
)
from scripts.kbo_schedule_import.raw_storage import (
    save_raw_schedule_response,
)
from scripts.kbo_schedule_import.repository import (
    SqlAlchemyKboScheduleImportRepository,
)

KST = ZoneInfo("Asia/Seoul")
DEFAULT_RAW_ROOT = REPOSITORY_ROOT / "data" / "kbo_schedule" / "raw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync KBO schedule data from the official schedule API.",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--today",
        action="store_true",
        help="Sync only games scheduled for today in Asia/Seoul.",
    )
    target.add_argument(
        "--season-year",
        type=int,
        help="KBO season year to sync. Must be used with --month.",
    )
    parser.add_argument(
        "--month",
        type=int,
        choices=range(1, 13),
        metavar="1-12",
        help="KBO schedule month to sync.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch, save raw data, and normalize without writing to the DB.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="Root directory for saved raw KBO schedule responses.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    today = datetime.now(KST).date()

    if args.today:
        season_year = today.year
        month = today.month
        mode = "today"
    else:
        if args.month is None:
            raise SystemExit("--month is required when --season-year is used.")
        season_year = args.season_year
        month = args.month
        mode = "month"

    if season_year is None:
        raise SystemExit("--season-year is required.")

    collected_at = datetime.now(KST)
    request = KboScheduleRequest(season_year=season_year, month=month)
    response_json = await KboScheduleClient().fetch_month(request)
    saved_raw = save_raw_schedule_response(
        raw_root=args.raw_root.resolve(),
        request=request,
        collected_at=collected_at,
        response_json=response_json,
    )

    games = normalize_kbo_schedule_payload(
        saved_raw.payload,
        season_year=season_year,
        collected_at=collected_at,
    )
    target_games = (
        [game for game in games if game.game_date == today] if args.today else games
    )
    rows = build_kbo_game_upsert_rows(target_games)

    print(f"mode={mode}")
    print(f"season_year={season_year}")
    print(f"month={month:02d}")
    print(f"dry_run={str(args.dry_run).lower()}")
    print(f"raw_file={saved_raw.file_path}")
    print(f"parsed_games={len(games)}")
    print(f"target_games={len(target_games)}")
    print(f"upsert_rows={len(rows)}")
    print(f"first_internal_game_key={rows[0].internal_game_key if rows else '-'}")

    if args.dry_run:
        return

    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        try:
            repository = SqlAlchemyKboScheduleImportRepository(session)
            result = await repository.upsert_games(rows)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    print(f"inserted={result.inserted_count}")
    print(f"updated={result.updated_count}")
    print(f"unchanged={result.unchanged_count}")
    print(f"status_history={result.status_history_count}")


if __name__ == "__main__":
    asyncio.run(main())
