# KBO 전체 일정 갱신 Command

## 목적

KBO 공식 일정 API에서 시즌 전체 월별 데이터를 다시 수집하고 `kbo_games`에
upsert한다. 경기 상태 또는 스코어가 달라지면 `kbo_game_status_history`에 변경
이력을 남긴다.

## 사전 확인

1. 로컬 또는 운영 중 어느 DB를 변경할지 사용자에게 명시하고 확인받는다.
2. 운영 DB 작업이면 project ref가 운영 Supabase project와 일치하는지 확인한다.
3. `--dry-run`도 `data/kbo_schedule/raw/<year>/*.json`을 갱신한다는 점을 알린다.

## 전체 시즌 dry-run

DB에는 쓰지 않고 API 호출, raw 저장, 정규화, upsert row 생성을 검증한다.

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/backend

for month in {1..12}; do
  uv run python scripts/sync_kbo_schedule.py \
    --season-year 2026 \
    --month "$month" \
    --dry-run || break
done
```

## 전체 시즌 DB 반영

DB 대상 확인과 사용자 승인이 끝난 뒤에만 `--dry-run` 없이 실행한다.

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/backend

for month in {1..12}; do
  uv run python scripts/sync_kbo_schedule.py \
    --season-year 2026 \
    --month "$month" || break
done
```

## 당일 경기 DB 반영

```bash
cd /Users/root1/Desktop/agent-rebuild/new-baseball/backend
uv run python scripts/sync_kbo_schedule.py --today
```

## 성공 판정

각 월 실행 결과에 다음 항목이 출력되어야 한다.

```text
mode=month
dry_run=false
parsed_games=<count>
target_games=<count>
upsert_rows=<count>
inserted=<count>
updated=<count>
unchanged=<count>
status_history=<count>
```

`|| break` 때문에 실패한 월에서 전체 실행이 중단된다. 오류를 해결한 뒤 같은
명령을 재실행해도 `internal_game_key` 기준 upsert이므로 동일 경기가 중복 생성되지
않는다.

## 작업 종료 확인

1. 월별 `inserted`, `updated`, `unchanged`, `status_history`를 합산해 보고한다.
2. 중단된 월이나 파싱 0건이 예상 밖인 월이 있는지 확인한다.
3. `git status --short`로 raw snapshot 변경사항을 확인한다.
4. 운영 DB를 사용했다면 `backend/.env`의 `DATABASE_URL`을 로컬 주소로 복구한다.
5. 비밀번호, 전체 DB URL, API key는 결과 보고에 포함하지 않는다.
