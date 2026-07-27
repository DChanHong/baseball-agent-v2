from pathlib import Path
from typing import TYPE_CHECKING

from scripts.kbo_schedule_import.dto import ImportKboScheduleResult
from scripts.kbo_schedule_import.key_builder import build_kbo_game_upsert_rows
from scripts.kbo_schedule_import.loader import load_normalized_kbo_schedule_file

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_all_kbo_games_from_file(
    session: "AsyncSession",
    *,
    file_path: Path,
) -> ImportKboScheduleResult:
    """정규화된 전체 KBO 일정 파일을 DB에 upsert합니다."""

    from scripts.kbo_schedule_import.repository import (
        SqlAlchemyKboScheduleImportRepository,
    )

    games = load_normalized_kbo_schedule_file(file_path)
    rows = build_kbo_game_upsert_rows(games)
    repository = SqlAlchemyKboScheduleImportRepository(session)
    result = await repository.upsert_games(rows)

    return ImportKboScheduleResult(
        file_path=file_path,
        total_count=len(rows),
        inserted_count=result.inserted_count,
        updated_count=result.updated_count,
        unchanged_count=result.unchanged_count,
        status_history_count=result.status_history_count,
    )
