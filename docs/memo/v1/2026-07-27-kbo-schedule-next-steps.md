# KBO Schedule Import 다음 작업 메모

> 작성일: 2026-07-27  
> 목적: 새 세션에서 KBO 경기 일정 DB 적재와 `find_kbo_game` 구현을 이어가기 위한 현재 상태 정리

## 1. 현재 완료된 작업

### 1.1 프론트엔드

이미 커밋 완료:

```text
0d6bf0c feat: scaffold baseball agent frontend
6fd907e docs: add frontend folder design
```

완료 내용:

- `frontend/` Next.js + TypeScript + pnpm 프로젝트 생성
- styled-components, Jotai, React Query, Zod 기본 세팅
- 랜딩형 채팅 UI 적용
- 로그인 모달, 프로필 모달, 출처 drawer 기본 UI
- FSD-inspired 구조 문서 작성

### 1.2 KBO 일정 수집/DB 계획

관련 문서:

```text
docs/planning/game-schedule/001-data-collection-and-db.md
```

핵심 결정:

- `find_kbo_game`은 KBO 사이트를 실시간 호출하지 않는다.
- 일정은 RAG가 아니라 정형 DB 조회로 처리한다.
- raw snapshot DB 저장은 현재 범위에서 제외했다.
- 원본 raw 파일은 `data/raw/`에 있고, DB에는 서비스 조회에 필요한 정규화 데이터만 넣는다.

### 1.3 KBO schedule migration, seed, import script

이미 커밋 완료:

```text
030e453 feat: add kbo schedule import pipeline
```

추가된 주요 파일:

```text
supabase/migrations/20260727165538_create_kbo_schedule_tables.sql
supabase/seed.sql
supabase/seeds/001_kbo_teams.sql
supabase/seeds/002_kbo_stadiums_minimal.sql
supabase/seeds/003_kbo_team_home_stadiums.sql

backend/app/domains/baseball/domain/enums.py
backend/app/domains/baseball/infrastructure/models.py

backend/scripts/import_kbo_schedule.py
backend/scripts/kbo_schedule_import/
```

생성 테이블:

```text
kbo_teams
kbo_stadiums
kbo_games
kbo_game_status_history
```

raw snapshot 관련 테이블과 컬럼은 만들지 않는다.

## 2. 현재 데이터 파일

전체 정규화 데이터:

```text
data/processed/kbo_schedule_2026_normalized.json
```

확인된 건수:

```text
games = 675
unique internal_game_key = 675
date_min = 2026-03-28
date_max = 2026-09-06
```

dry-run 확인 명령:

```bash
cd backend
python3 scripts/import_kbo_schedule.py \
  --file ../data/processed/kbo_schedule_2026_normalized.json \
  --dry-run
```

확인된 출력:

```text
parsed_games=675
upsert_rows=675
first_internal_game_key=20260328_KT_LG_JAMSIL
```

## 3. 다음 세션에서 바로 해야 할 작업

### 3.1 DB 적용 환경 확인

현재 로컬에는 `supabase` CLI가 없어서 migration/seed 실제 적용 검증은 못 했다.

확인 명령:

```bash
supabase --version
psql --version
```

현재 확인된 상태:

```text
supabase: command not found
psql: 설치되어 있음
```

다음 세션에서는 둘 중 하나로 진행한다.

#### 선택지 A. Supabase CLI 사용

```bash
supabase start
supabase db reset
```

#### 선택지 B. psql 직접 적용

`DATABASE_URL`이 준비되어 있다면 migration과 seed를 직접 적용한다.

```bash
psql "$DATABASE_URL" -f supabase/migrations/20260726040522_create_chat_conversations.sql
psql "$DATABASE_URL" -f supabase/migrations/20260726040726_create_chat_messages.sql
psql "$DATABASE_URL" -f supabase/migrations/20260726041011_create_chat_indexes.sql
psql "$DATABASE_URL" -f supabase/migrations/20260727165538_create_kbo_schedule_tables.sql
psql "$DATABASE_URL" -f supabase/seed.sql
```

주의:

- `supabase/seed.sql`은 `\i ./seeds/...`를 사용하므로 실행 위치가 `supabase/` 기준이어야 할 수 있다.
- psql 직접 실행 시 다음처럼 실행하는 편이 안전할 수 있다.

```bash
cd supabase
psql "$DATABASE_URL" -f seed.sql
```

### 3.2 실제 전체 데이터 import

DB migration과 seed 적용 후 실행한다.

```bash
cd backend
python3 scripts/import_kbo_schedule.py \
  --file ../data/processed/kbo_schedule_2026_normalized.json
```

첫 실행 기대값:

```text
total=675
inserted=675
updated=0
unchanged=0
status_history=0
```

두 번째 실행 기대값:

```text
total=675
inserted=0
updated=675
unchanged=675
status_history=0
```

현재 import repository는 `on conflict do update`를 사용하므로 기존 row는 updated로 카운트된다. 실제 변경 없는 row의 update 자체를 피하고 싶다면 나중에 `where` 조건을 추가해 최적화한다.

### 3.3 DB row 확인 쿼리

```sql
select count(*) from public.kbo_games;

select game_status, count(*)
from public.kbo_games
group by game_status
order by game_status;

select min(game_date), max(game_date)
from public.kbo_games;

select *
from public.kbo_games
order by game_date, start_time
limit 5;
```

기대값:

```text
count = 675
min(game_date) = 2026-03-28
max(game_date) = 2026-09-06
```

## 4. 그 다음 구현 단계

DB 적재가 확인되면 `find_kbo_game` 조회 기능을 만든다.

추천 endpoint:

```text
GET /api/v1/games?team_id=LOTTE&date_from=2026-07-01&date_to=2026-07-31
```

추가할 구조:

```text
backend/app/domains/baseball/
├── controller/
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
├── service/
│   ├── __init__.py
│   ├── dto.py
│   └── services.py
├── domain/
│   ├── entities.py
│   ├── repositories.py
│   └── exceptions.py
└── infrastructure/
    ├── mappers.py
    └── repositories.py
```

`conversation` 도메인의 구조를 참고한다.

```text
backend/app/domains/conversation/
```

주의:

- import script 전용 코드는 `domains/baseball/service`에 넣지 않는다.
- `backend/scripts/kbo_schedule_import/`에 유지한다.
- `domains/baseball`에는 API/Tool에서 재사용할 도메인 조회 로직만 둔다.

## 5. find_kbo_game 완료 기준

최소 완료 기준:

- `team_id`, `date`, `date_from/date_to`로 경기 조회 가능
- 홈/원정 어느 쪽이든 팀이 포함되면 조회
- 경기 없음 응답 구분
- 취소/unknown 상태와 `status_reason` 반환
- `source_name`, `source_url`, `source_collected_at` 반환
- stale 여부 판단은 이후 단계에서 추가 가능

예상 조회 조건:

```sql
where game_date between :date_from and :date_to
and (
  :team_id is null
  or home_team_id = :team_id
  or away_team_id = :team_id
)
order by game_date, start_time nulls last, home_team_id
```

## 6. 이후 크론 작업 메모

전체 import가 성공한 뒤 당일 경기 업데이트용 함수를 만든다.

예상 함수:

```python
async def sync_today_kbo_games(...)
```

역할:

- Asia/Seoul 기준 오늘 날짜 확인
- 오늘이 속한 월의 KBO 일정 재수집
- 오늘 경기만 정규화
- 기존 `kbo_games` upsert 로직 재사용
- 상태/스코어 변경 시 `kbo_game_status_history` 기록

초기 cron 정책:

```text
매 1시간마다 당일 경기 상태 업데이트
```

이 함수는 API 도메인이 아니라 script/worker/cron 영역에 둔다.

## 7. 검증 관련 주의사항

현재 시스템 Python에는 다음 패키지가 없어서 일부 검증은 못 했다.

```text
sqlalchemy
pytest
ruff
```

실행 실패했던 명령:

```bash
python3 -m ruff check ...
python3 -m pytest ...
```

대신 확인한 검증:

```bash
python3 -m compileall backend/app/domains/baseball backend/scripts

cd backend
python3 scripts/import_kbo_schedule.py \
  --file ../data/processed/kbo_schedule_2026_normalized.json \
  --dry-run
```

## 8. 현재 git 상태 기준

마지막 커밋:

```text
030e453 feat: add kbo schedule import pipeline
```

이 메모 파일은 아직 커밋하지 않았다면 별도 docs 커밋으로 남기면 된다.
