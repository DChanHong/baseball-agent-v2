from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StadiumWeatherGrid:
    stadium_id: str
    stadium_name: str
    nx: int
    ny: int
    is_dome: bool


# KMA 5km grid coordinates derived from stadium latitude/longitude.
STADIUM_WEATHER_GRIDS: dict[str, StadiumWeatherGrid] = {
    "SAJIK": StadiumWeatherGrid("SAJIK", "부산 사직 야구장", 98, 76, False),
    "GOCHEOK": StadiumWeatherGrid("GOCHEOK", "고척스카이돔", 58, 125, True),
    "MUNHAK": StadiumWeatherGrid("MUNHAK", "인천 SSG 랜더스필드", 55, 124, False),
    "GWANGJU": StadiumWeatherGrid("GWANGJU", "광주-기아 챔피언스 필드", 59, 75, False),
    "DAEGU": StadiumWeatherGrid("DAEGU", "대구 삼성 라이온즈 파크", 90, 90, False),
    "SUWON": StadiumWeatherGrid("SUWON", "수원 KT 위즈파크", 60, 121, False),
    "DAEJEON": StadiumWeatherGrid("DAEJEON", "대전 한화생명 볼파크", 68, 100, False),
    "JAMSIL": StadiumWeatherGrid("JAMSIL", "서울종합운동장 야구장", 61, 126, False),
    "CHANGWON": StadiumWeatherGrid("CHANGWON", "창원 NC 파크", 89, 76, False),
}


def get_stadium_weather_grid(stadium_id: str) -> StadiumWeatherGrid | None:
    return STADIUM_WEATHER_GRIDS.get(stadium_id.strip().upper())
