from collections import Counter

from scripts.kbo_schedule_import.dto import KboGameUpsertRow, NormalizedKboGame


def build_internal_game_key(game: NormalizedKboGame) -> str:
    """단일 경기의 기본 internal_game_key를 생성합니다."""

    return game.base_internal_game_key()


def build_kbo_game_upsert_rows(games: list[NormalizedKboGame]) -> list[KboGameUpsertRow]:
    """
    경기 목록에 upsert key를 부여합니다.

    같은 날짜, 팀, 구장 조합이 중복되면 시작 시각과 순번을 붙여 더블헤더를 구분합니다.
    """

    base_keys = [build_internal_game_key(game) for game in games]
    base_key_counts = Counter(base_keys)
    seen: Counter[str] = Counter()
    rows: list[KboGameUpsertRow] = []

    for game, base_key in zip(games, base_keys, strict=True):
        seen[base_key] += 1

        if base_key_counts[base_key] == 1:
            internal_game_key = base_key
        else:
            start_time_part = game.start_time.strftime("%H%M") if game.start_time else "NO_TIME"
            internal_game_key = f"{base_key}_{start_time_part}_{seen[base_key]}"

        rows.append(
            KboGameUpsertRow(
                game=game,
                internal_game_key=internal_game_key,
            )
        )

    return rows
