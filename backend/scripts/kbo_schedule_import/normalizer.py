from __future__ import annotations

import html
import re
from datetime import date, datetime, time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.domains.baseball.domain.enums import KboGameStatus
from scripts.kbo_schedule_import.client import KBO_SCHEDULE_PAGE_URL
from scripts.kbo_schedule_import.dto import NormalizedKboGame

SOURCE_NAME = "KBO Schedule.asmx/GetScheduleList"
KST_OFFSET = "+09:00"

TEAM_ID_BY_NAME = {
    "LG": "LG",
    "두산": "DOOSAN",
    "키움": "KIWOOM",
    "SSG": "SSG",
    "KIA": "KIA",
    "삼성": "SAMSUNG",
    "롯데": "LOTTE",
    "NC": "NC",
    "한화": "HANWHA",
    "KT": "KT",
}

STADIUM_ID_BY_NAME = {
    "잠실": "JAMSIL",
    "고척": "GOCHEOK",
    "문학": "MUNHAK",
    "광주": "GWANGJU",
    "대구": "DAEGU",
    "사직": "SAJIK",
    "창원": "CHANGWON",
    "대전": "DAEJEON",
    "수원": "SUWON",
    "포항": "POHANG",
}

DATE_PATTERN = re.compile(r"(?P<month>\d{2})\.(?P<day>\d{2})")
TIME_PATTERN = re.compile(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})")
GAME_ID_PATTERN = re.compile(r"gameId=([^&'\"]+)")


def normalize_kbo_schedule_payload(
    payload: dict[str, Any],
    *,
    season_year: int,
    collected_at: datetime,
) -> list[NormalizedKboGame]:
    """Convert a KBO schedule table payload into normalized game DTOs."""

    response_payload = _extract_response_payload(payload)
    rows = response_payload.get("rows")
    if not isinstance(rows, list):
        raise TypeError("KBO schedule payload must include rows.")

    current_game_date: date | None = None
    games: list[NormalizedKboGame] = []

    for raw_row in rows:
        cells = _extract_cells(raw_row)
        if not cells:
            continue

        day_cell = _find_cell_by_class(cells, "day")
        if day_cell is not None:
            current_game_date = _parse_game_date(
                _cell_text(day_cell),
                season_year=season_year,
            )

        if current_game_date is None:
            raise ValueError("KBO schedule row appeared before a day cell.")

        time_cell = _find_cell_by_class(cells, "time")
        play_cell = _find_cell_by_class(cells, "play")
        relay_cell = _find_cell_by_class(cells, "relay")
        if time_cell is None or play_cell is None:
            continue

        start_time = _parse_start_time(_cell_text(time_cell))
        teams_and_scores = _parse_play_cell(_cell_text(play_cell))
        stadium_name = _parse_stadium_name(cells)
        note = _parse_note(cells)
        relay_label = _plain_text(_cell_text(relay_cell)) if relay_cell else ""
        source_game_id = _parse_game_id(_cell_text(relay_cell)) if relay_cell else None

        games.append(
            NormalizedKboGame(
                source=SOURCE_NAME,
                source_url=KBO_SCHEDULE_PAGE_URL,
                collected_at=collected_at,
                source_game_id=source_game_id,
                game_date=current_game_date,
                start_time=start_time,
                starts_at=_build_starts_at(current_game_date, start_time),
                away_team_name=teams_and_scores.away_team_name,
                away_team_id=_team_id(teams_and_scores.away_team_name),
                home_team_name=teams_and_scores.home_team_name,
                home_team_id=_team_id(teams_and_scores.home_team_name),
                away_score=teams_and_scores.away_score,
                home_score=teams_and_scores.home_score,
                stadium_name=stadium_name,
                stadium_id=_stadium_id(stadium_name),
                game_status=_map_game_status(
                    relay_label=relay_label,
                    note=note,
                    away_score=teams_and_scores.away_score,
                    home_score=teams_and_scores.home_score,
                ),
                status_reason=None if note == "-" else note,
            )
        )

    return games


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)


class _PlayCellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.span_texts: list[str] = []
        self._in_span = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "span":
            self._in_span = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._in_span = False

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if self._in_span and stripped:
            self.span_texts.append(stripped)


class _ParsedPlayCell:
    def __init__(
        self,
        *,
        away_team_name: str,
        home_team_name: str,
        away_score: int | None,
        home_score: int | None,
    ) -> None:
        self.away_team_name = away_team_name
        self.home_team_name = home_team_name
        self.away_score = away_score
        self.home_score = home_score


def _extract_response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response_json = payload.get("response_json")
    if isinstance(response_json, dict):
        return response_json
    return payload


def _extract_cells(raw_row: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_row, dict):
        raise TypeError("KBO schedule row must be an object.")

    cells = raw_row.get("row")
    if not isinstance(cells, list):
        raise TypeError("KBO schedule row must include row cells.")

    return [cell for cell in cells if isinstance(cell, dict)]


def _find_cell_by_class(
    cells: list[dict[str, Any]],
    class_name: str,
) -> dict[str, Any] | None:
    return next((cell for cell in cells if cell.get("Class") == class_name), None)


def _cell_text(cell: dict[str, Any] | None) -> str:
    if cell is None:
        return ""
    value = cell.get("Text")
    return value if isinstance(value, str) else ""


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(value))
    return " ".join(parser.parts).strip()


def _parse_game_date(value: str, *, season_year: int) -> date:
    match = DATE_PATTERN.search(_plain_text(value))
    if match is None:
        raise ValueError(f"Cannot parse KBO game date: {value}")
    return date(season_year, int(match.group("month")), int(match.group("day")))


def _parse_start_time(value: str) -> time | None:
    match = TIME_PATTERN.search(_plain_text(value))
    if match is None:
        return None
    return time(int(match.group("hour")), int(match.group("minute")))


def _build_starts_at(game_date: date, start_time: time | None) -> datetime | None:
    if start_time is None:
        return None

    return datetime.fromisoformat(
        f"{game_date.isoformat()}T{start_time.isoformat()}{KST_OFFSET}"
    )


def _parse_play_cell(value: str) -> _ParsedPlayCell:
    parser = _PlayCellParser()
    parser.feed(html.unescape(value))
    parts = parser.span_texts

    if len(parts) == 3 and parts[1] == "vs":
        return _ParsedPlayCell(
            away_team_name=parts[0],
            home_team_name=parts[2],
            away_score=None,
            home_score=None,
        )

    if len(parts) == 5 and parts[2] == "vs":
        return _ParsedPlayCell(
            away_team_name=parts[0],
            away_score=_parse_score(parts[1]),
            home_score=_parse_score(parts[3]),
            home_team_name=parts[4],
        )

    raise ValueError(f"Cannot parse KBO play cell: {value}")


def _parse_score(value: str) -> int:
    if not value.isdigit():
        raise ValueError(f"Cannot parse KBO score: {value}")
    return int(value)


def _parse_game_id(value: str) -> str | None:
    match = GAME_ID_PATTERN.search(value)
    if match is None:
        parsed = urlparse(html.unescape(value))
        query = parse_qs(parsed.query)
        game_ids = query.get("gameId")
        return game_ids[0] if game_ids else None
    return match.group(1)


def _parse_stadium_name(cells: list[dict[str, Any]]) -> str:
    values = [_plain_text(_cell_text(cell)) for cell in cells]
    for value in values:
        if value in STADIUM_ID_BY_NAME:
            return value
    raise ValueError(f"Cannot find KBO stadium cell: {values}")


def _parse_note(cells: list[dict[str, Any]]) -> str:
    values = [_plain_text(_cell_text(cell)) for cell in cells]
    for value in reversed(values):
        if value in {"-", "우천취소", "그라운드사정"}:
            return value
    return "-"


def _team_id(team_name: str) -> str:
    try:
        return TEAM_ID_BY_NAME[team_name]
    except KeyError as exc:
        raise ValueError(f"Unknown KBO team name: {team_name}") from exc


def _stadium_id(stadium_name: str) -> str:
    try:
        return STADIUM_ID_BY_NAME[stadium_name]
    except KeyError as exc:
        raise ValueError(f"Unknown KBO stadium name: {stadium_name}") from exc


def _map_game_status(
    *,
    relay_label: str,
    note: str,
    away_score: int | None,
    home_score: int | None,
) -> KboGameStatus:
    if note == "우천취소":
        return KboGameStatus.CANCELLED

    if away_score is not None and home_score is not None:
        return KboGameStatus.COMPLETED

    if "리뷰" in relay_label:
        return KboGameStatus.COMPLETED

    return KboGameStatus.SCHEDULED
