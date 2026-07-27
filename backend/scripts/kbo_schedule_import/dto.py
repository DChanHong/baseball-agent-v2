from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

from app.domains.baseball.domain.enums import KboGameStatus

KST_OFFSET = "+09:00"


@dataclass(frozen=True, slots=True)
class NormalizedKboGame:
    """정규화된 KBO 일정 파일의 단일 경기입니다."""

    source: str
    source_url: str
    collected_at: datetime
    source_game_id: str | None
    game_date: date
    start_time: time | None
    starts_at: datetime | None
    away_team_name: str
    away_team_id: str
    home_team_name: str
    home_team_id: str
    away_score: int | None
    home_score: int | None
    stadium_name: str
    stadium_id: str
    game_status: KboGameStatus
    status_reason: str | None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "NormalizedKboGame":
        """정규화 JSON row를 import용 DTO로 변환합니다."""

        game_date = date.fromisoformat(_required_str(data, "game_date"))
        start_time = _parse_optional_time(data.get("start_time"))

        return cls(
            source=_required_str(data, "source"),
            source_url=_required_str(data, "source_url"),
            collected_at=_parse_datetime(_required_str(data, "collected_at")),
            source_game_id=_optional_non_blank(data.get("game_id")),
            game_date=game_date,
            start_time=start_time,
            starts_at=_build_starts_at(game_date, start_time),
            away_team_name=_required_str(data, "away_team_name"),
            away_team_id=_required_str(data, "away_team_id"),
            home_team_name=_required_str(data, "home_team_name"),
            home_team_id=_required_str(data, "home_team_id"),
            away_score=_parse_optional_int(data.get("away_score")),
            home_score=_parse_optional_int(data.get("home_score")),
            stadium_name=_required_str(data, "stadium_name"),
            stadium_id=_required_str(data, "stadium_id"),
            game_status=KboGameStatus(_required_str(data, "game_status")),
            status_reason=_normalize_status_reason(data.get("note")),
        )

    def base_internal_game_key(self) -> str:
        """더블헤더가 아닌 일반 경기의 기본 upsert key를 만듭니다."""

        return "_".join(
            [
                self.game_date.strftime("%Y%m%d"),
                self.away_team_id,
                self.home_team_id,
                self.stadium_id,
            ]
        )


@dataclass(frozen=True, slots=True)
class KboGameUpsertRow:
    """DB upsert에 사용할 경기 row입니다."""

    game: NormalizedKboGame
    internal_game_key: str


@dataclass(frozen=True, slots=True)
class ImportKboScheduleResult:
    """KBO 일정 import 결과 요약입니다."""

    file_path: Path
    total_count: int
    inserted_count: int
    updated_count: int
    unchanged_count: int
    status_history_count: int


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}는 비어 있을 수 없습니다.")

    return value.strip()


def _optional_non_blank(value: Any) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("문자열 또는 null이 필요합니다.")

    stripped = value.strip()
    return stripped or None


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, int):
        if value < 0:
            raise ValueError("점수는 0 이상이어야 합니다.")
        return value

    raise ValueError("점수는 정수 또는 null이어야 합니다.")


def _parse_optional_time(value: Any) -> time | None:
    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        return None

    return time.fromisoformat(value.strip())


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed


def _build_starts_at(game_date: date, start_time: time | None) -> datetime | None:
    if start_time is None:
        return None

    return datetime.fromisoformat(
        f"{game_date.isoformat()}T{start_time.isoformat()}{KST_OFFSET}"
    )


def _normalize_status_reason(value: Any) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("note는 문자열 또는 null이어야 합니다.")

    stripped = value.strip()

    if not stripped or stripped == "-":
        return None

    return stripped
