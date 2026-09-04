import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.domains.baseball.domain.enums import KboGameStatus
from scripts.kbo_schedule_import.client import (
    KboScheduleRequest,
    unwrap_kbo_schedule_response,
)
from scripts.kbo_schedule_import.normalizer import (
    normalize_kbo_schedule_payload,
)
from scripts.kbo_schedule_import.raw_storage import (
    save_raw_schedule_response,
)

KST = ZoneInfo("Asia/Seoul")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_normalize_kbo_schedule_payload_parses_completed_and_rowspan_dates() -> None:
    payload = json.loads(
        (REPOSITORY_ROOT / "data/kbo_schedule/raw/2026/07.json").read_text(
            encoding="utf-8"
        )
    )
    collected_at = datetime(2026, 7, 27, 14, 27, tzinfo=KST)

    games = normalize_kbo_schedule_payload(
        payload,
        season_year=2026,
        collected_at=collected_at,
    )

    assert len(games) == 110
    assert games[0].game_date.isoformat() == "2026-07-01"
    assert games[0].start_time.isoformat(timespec="minutes") == "18:30"
    assert games[0].starts_at is not None
    assert games[0].starts_at.isoformat() == "2026-07-01T18:30:00+09:00"
    assert games[0].away_team_id == "LOTTE"
    assert games[0].home_team_id == "DOOSAN"
    assert games[0].away_score == 5
    assert games[0].home_score == 2
    assert games[0].game_status == KboGameStatus.COMPLETED
    assert games[0].source_game_id == "20260701LTOB0"

    assert games[1].game_date.isoformat() == "2026-07-01"
    assert games[1].away_team_id == "SSG"
    assert games[1].home_team_id == "KIA"


def test_normalize_kbo_schedule_payload_maps_cancelled_note() -> None:
    payload = json.loads(
        (REPOSITORY_ROOT / "data/kbo_schedule/raw/2026/07.json").read_text(
            encoding="utf-8"
        )
    )
    collected_at = datetime(2026, 7, 27, 14, 27, tzinfo=KST)

    games = normalize_kbo_schedule_payload(
        payload,
        season_year=2026,
        collected_at=collected_at,
    )
    cancelled_game = next(game for game in games if game.status_reason == "우천취소")

    assert cancelled_game.game_status == KboGameStatus.CANCELLED
    assert cancelled_game.away_score is None
    assert cancelled_game.home_score is None
    assert cancelled_game.source_game_id is None


def test_normalize_kbo_schedule_payload_accepts_saved_raw_wrapper() -> None:
    payload = {
        "response_json": json.loads(
            (REPOSITORY_ROOT / "data/kbo_schedule/raw/2026/09.json").read_text(
                encoding="utf-8"
            )
        )
    }
    collected_at = datetime(2026, 9, 4, 12, 0, tzinfo=KST)

    games = normalize_kbo_schedule_payload(
        payload,
        season_year=2026,
        collected_at=collected_at,
    )

    assert len(games) == 30
    assert games[0].game_date.isoformat() == "2026-09-01"
    assert games[0].game_status == KboGameStatus.SCHEDULED


def test_save_raw_schedule_response_writes_month_file(tmp_path: Path) -> None:
    request = KboScheduleRequest(season_year=2026, month=9)
    collected_at = datetime(2026, 9, 4, 12, 0, tzinfo=KST)

    saved = save_raw_schedule_response(
        raw_root=tmp_path,
        request=request,
        collected_at=collected_at,
        response_json={"rows": []},
    )

    assert saved.file_path == tmp_path / "2026" / "09.json"
    saved_payload = json.loads(saved.file_path.read_text(encoding="utf-8"))
    assert saved_payload["request_params"]["seasonId"] == "2026"
    assert saved_payload["request_params"]["gameMonth"] == "09"
    assert saved_payload["collected_at"] == "2026-09-04T12:00:00+09:00"
    assert saved_payload["response_json"] == {"rows": []}


def test_unwrap_kbo_schedule_response_accepts_asmx_string_wrapper() -> None:
    payload = unwrap_kbo_schedule_response({"d": json.dumps({"rows": []})})

    assert payload == {"rows": []}
