import json
from pathlib import Path
from typing import Any

from scripts.kbo_schedule_import.dto import NormalizedKboGame


def load_normalized_kbo_schedule_file(file_path: Path) -> list[NormalizedKboGame]:
    """정규화된 KBO 일정 JSON 파일을 import DTO 목록으로 읽습니다."""

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    games = payload.get("games")

    if not isinstance(games, list):
        raise ValueError("정규화 일정 파일에는 games 배열이 필요합니다.")

    return [_parse_game(item) for item in games]


def _parse_game(item: Any) -> NormalizedKboGame:
    if not isinstance(item, dict):
        raise ValueError("games 배열의 항목은 객체여야 합니다.")

    return NormalizedKboGame.from_mapping(item)
