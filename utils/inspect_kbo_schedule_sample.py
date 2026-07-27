import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)


def html_text(value: str | None) -> str:
    parser = TextParser()
    parser.feed(value or "")
    return " ".join(parser.parts)


def span_values(value: str | None) -> list[str]:
    return re.findall(r"<span(?: [^>]*)?>(.*?)</span>", value or "")


def query_value(value: str | None, key: str) -> str | None:
    match = re.search(r"[?&]" + re.escape(key) + r"=([^&\"']+)", value or "")
    return match.group(1) if match else None


TEAM_IDS = {
    "롯데": "LOTTE",
    "두산": "DOOSAN",
    "SSG": "SSG",
    "KIA": "KIA",
    "삼성": "SAMSUNG",
    "NC": "NC",
    "KT": "KT",
    "한화": "HANWHA",
    "LG": "LG",
    "키움": "KIWOOM",
}

STADIUM_IDS = {
    "잠실": "JAMSIL",
    "광주": "GWANGJU",
    "창원": "CHANGWON",
    "대전": "DAEJEON",
    "고척": "GOCHEOK",
    "대구": "DAEGU",
    "문학": "MUNHAK",
    "사직": "SAJIK",
    "수원": "SUWON",
    "포항": "POHANG",
}


def infer_status(relay_label: str, note: str, scores: list[int]) -> str:
    if "취소" in note or "취소" in relay_label:
        return "cancelled"
    if "프리뷰" in relay_label or not scores:
        return "scheduled"
    if relay_label == "리뷰" or len(scores) >= 2:
        return "completed"
    return "unknown"


def normalize(raw: dict) -> list[dict]:
    current_date: str | None = None
    games: list[dict] = []

    for item in raw.get("rows", []):
        cells = item.get("row", [])
        if not cells:
            continue

        index = 0
        if cells[0].get("Class") == "day":
            match = re.search(r"(\d{2})\.(\d{2})", html_text(cells[0].get("Text")))
            if match:
                current_date = f"2026-{match.group(1)}-{match.group(2)}"
            index = 1

        if current_date is None or len(cells) <= index + 1:
            continue

        time_cell = cells[index]
        play_cell = cells[index + 1]
        relay_cell = cells[index + 2] if len(cells) > index + 2 else {"Text": ""}
        stadium_cell = cells[index + 6] if len(cells) > index + 6 else {"Text": ""}
        note_cell = cells[index + 7] if len(cells) > index + 7 else {"Text": ""}

        play_html = play_cell.get("Text") or ""
        names = [
            value
            for value in span_values(play_html)
            if value != "vs" and not re.fullmatch(r"\d+", value)
        ]
        scores = [
            int(value)
            for value in span_values(play_html)
            if re.fullmatch(r"\d+", value)
        ]
        relay_label = html_text(relay_cell.get("Text"))
        note = html_text(note_cell.get("Text"))
        stadium_name = html_text(stadium_cell.get("Text"))

        games.append(
            {
                "source": "KBO Schedule.asmx/GetScheduleList dev sample",
                "source_url": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
                "collected_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
                "game_id": query_value(relay_cell.get("Text"), "gameId"),
                "game_date": current_date,
                "start_time": html_text(time_cell.get("Text")),
                "away_team_name": names[0] if len(names) > 0 else None,
                "away_team_id": TEAM_IDS.get(names[0]) if len(names) > 0 else None,
                "home_team_name": names[-1] if len(names) > 1 else None,
                "home_team_id": TEAM_IDS.get(names[-1]) if len(names) > 1 else None,
                "away_score": scores[0] if len(scores) >= 2 else None,
                "home_score": scores[1] if len(scores) >= 2 else None,
                "stadium_name": stadium_name,
                "stadium_id": STADIUM_IDS.get(stadium_name),
                "game_status": infer_status(relay_label, note, scores),
                "relay_label": relay_label,
                "note": note,
            }
        )

    return games


def main() -> None:
    raw_path = Path("new-baseball/data/raw/kbo_schedule_2026_07_raw.json")
    out_path = Path("new-baseball/data/processed/kbo_schedule_2026_07_normalized_sample.json")

    raw = json.loads(raw_path.read_text(encoding="utf-8-sig"))
    games = normalize(raw)
    result = {
        "query": {
            "seasonId": "2026",
            "gameMonth": "07",
            "srIdList": "0,9,6",
        },
        "raw_rows": len(raw.get("rows", [])),
        "normalized_count": len(games),
        "games": games,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "raw_rows": result["raw_rows"],
                "normalized_count": result["normalized_count"],
                "output": str(out_path),
                "first_3_games": games[:3],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
