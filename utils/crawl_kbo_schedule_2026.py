import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from inspect_kbo_schedule_sample import normalize


ENDPOINT = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
SOURCE_URL = "https://www.koreabaseball.com/Schedule/Schedule.aspx"
YEAR = 2026


def fetch_month(month: int) -> dict:
    payload = urllib.parse.urlencode(
        {
            "leId": "1",
            "srIdList": "0,9,6",
            "seasonId": str(YEAR),
            "gameMonth": f"{month:02d}",
            "teamId": "",
        }
    ).encode()
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": SOURCE_URL,
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8-sig")
    return json.loads(body)


def main() -> None:
    raw_dir = Path(f"new-baseball/data/raw/kbo/{YEAR}")
    processed_path = Path(f"new-baseball/data/processed/kbo_schedule_{YEAR}_normalized.json")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    all_games: list[dict] = []
    month_summary: list[dict] = []

    for month in range(1, 13):
        raw_path = raw_dir / f"{month:02d}.json"
        if raw_path.exists():
            raw = json.loads(raw_path.read_text(encoding="utf-8-sig"))
        else:
            raw = fetch_month(month)
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

        games = normalize(raw)
        all_games.extend(games)
        month_summary.append(
            {
                "month": f"{month:02d}",
                "raw_rows": len(raw.get("rows", [])),
                "normalized_count": len(games),
            }
        )
        print(
            json.dumps(
                month_summary[-1],
                ensure_ascii=False,
            )
        )
        time.sleep(0.5)

    result = {
        "query": {
            "seasonId": str(YEAR),
            "srIdList": "0,9,6",
        },
        "month_summary": month_summary,
        "normalized_count": len(all_games),
        "games": all_games,
    }
    processed_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    status_counts = Counter(game["game_status"] for game in all_games)
    print(
        json.dumps(
            {
                "normalized_count": len(all_games),
                "status_counts": dict(status_counts),
                "output": str(processed_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
