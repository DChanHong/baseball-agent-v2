from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.baseball.infrastructure.models import (
    KboGameModel,
    KboGameStatusHistoryModel,
)
from scripts.kbo_schedule_import.dto import KboGameUpsertRow


@dataclass(frozen=True, slots=True)
class KboScheduleUpsertResult:
    """KBO 일정 upsert 결과입니다."""

    inserted_count: int
    updated_count: int
    unchanged_count: int
    status_history_count: int


class SqlAlchemyKboScheduleImportRepository:
    """정규화된 KBO 일정을 PostgreSQL에 upsert하는 script용 Repository입니다."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_games(
        self,
        rows: list[KboGameUpsertRow],
    ) -> KboScheduleUpsertResult:
        """internal_game_key 기준으로 KBO 경기 일정을 upsert합니다."""

        if not rows:
            return KboScheduleUpsertResult(
                inserted_count=0,
                updated_count=0,
                unchanged_count=0,
                status_history_count=0,
            )

        existing_games = await self._find_existing_games(rows)
        inserted_count = 0
        updated_count = 0
        unchanged_count = 0
        status_history_count = 0

        for row in rows:
            payload = self._build_game_payload(row)
            existing_game = existing_games.get(row.internal_game_key)
            has_existing_game = existing_game is not None
            has_tracked_change = (
                self._has_status_or_score_change(existing_game, payload)
                if existing_game is not None
                else False
            )
            has_any_change = (
                self._has_any_change(existing_game, payload)
                if existing_game is not None
                else True
            )

            upsert_statement = (
                insert(KboGameModel)
                .values(**payload)
                .on_conflict_do_update(
                    index_elements=[KboGameModel.internal_game_key],
                    set_={
                        "season_year": payload["season_year"],
                        "source_game_id": payload["source_game_id"],
                        "game_date": payload["game_date"],
                        "start_time": payload["start_time"],
                        "starts_at": payload["starts_at"],
                        "away_team_id": payload["away_team_id"],
                        "home_team_id": payload["home_team_id"],
                        "stadium_id": payload["stadium_id"],
                        "away_team_name": payload["away_team_name"],
                        "home_team_name": payload["home_team_name"],
                        "stadium_name": payload["stadium_name"],
                        "game_status": payload["game_status"],
                        "status_reason": payload["status_reason"],
                        "away_score": payload["away_score"],
                        "home_score": payload["home_score"],
                        "source_name": payload["source_name"],
                        "source_url": payload["source_url"],
                        "source_collected_at": payload["source_collected_at"],
                    },
                )
                .returning(KboGameModel.id)
            )

            result = await self._session.execute(upsert_statement)
            game_id = result.scalar_one()

            if has_existing_game:
                updated_count += 1
            else:
                inserted_count += 1

            if has_existing_game and not has_any_change:
                unchanged_count += 1

            if existing_game is not None and has_tracked_change:
                self._session.add(
                    KboGameStatusHistoryModel(
                        game_id=game_id,
                        previous_status=existing_game.game_status,
                        new_status=payload["game_status"],
                        previous_reason=existing_game.status_reason,
                        new_reason=payload["status_reason"],
                        previous_away_score=existing_game.away_score,
                        previous_home_score=existing_game.home_score,
                        new_away_score=payload["away_score"],
                        new_home_score=payload["home_score"],
                    )
                )
                status_history_count += 1

        await self._session.flush()

        return KboScheduleUpsertResult(
            inserted_count=inserted_count,
            updated_count=updated_count,
            unchanged_count=unchanged_count,
            status_history_count=status_history_count,
        )

    async def _find_existing_games(
        self,
        rows: list[KboGameUpsertRow],
    ) -> dict[str, KboGameModel]:
        keys = [row.internal_game_key for row in rows]

        statement = select(KboGameModel).where(KboGameModel.internal_game_key.in_(keys))
        result = await self._session.execute(statement)
        models = result.scalars().all()

        return {model.internal_game_key: model for model in models}

    @staticmethod
    def _build_game_payload(row: KboGameUpsertRow) -> dict[str, Any]:
        game = row.game

        return {
            "season_year": game.game_date.year,
            "source_game_id": game.source_game_id,
            "internal_game_key": row.internal_game_key,
            "game_date": game.game_date,
            "start_time": game.start_time,
            "starts_at": game.starts_at,
            "away_team_id": game.away_team_id,
            "home_team_id": game.home_team_id,
            "stadium_id": game.stadium_id,
            "away_team_name": game.away_team_name,
            "home_team_name": game.home_team_name,
            "stadium_name": game.stadium_name,
            "game_status": game.game_status.value,
            "status_reason": game.status_reason,
            "away_score": game.away_score,
            "home_score": game.home_score,
            "source_name": game.source,
            "source_url": game.source_url,
            "source_collected_at": game.collected_at,
        }

    @staticmethod
    def _has_status_or_score_change(
        existing_game: KboGameModel,
        payload: dict[str, Any],
    ) -> bool:
        return any(
            [
                existing_game.game_status != payload["game_status"],
                existing_game.status_reason != payload["status_reason"],
                existing_game.away_score != payload["away_score"],
                existing_game.home_score != payload["home_score"],
            ]
        )

    @staticmethod
    def _has_any_change(
        existing_game: KboGameModel,
        payload: dict[str, Any],
    ) -> bool:
        compared_fields = [
            "season_year",
            "source_game_id",
            "game_date",
            "start_time",
            "starts_at",
            "away_team_id",
            "home_team_id",
            "stadium_id",
            "away_team_name",
            "home_team_name",
            "stadium_name",
            "game_status",
            "status_reason",
            "away_score",
            "home_score",
            "source_name",
            "source_url",
            "source_collected_at",
        ]

        return any(
            getattr(existing_game, field) != payload[field]
            for field in compared_fields
        )
