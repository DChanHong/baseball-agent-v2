# KBO 경기 일정 수집 전략과 DB 정의

> 라벨: `REFERENCE`  
> 범위: `find_kbo_game` 구현에 필요한 KBO 경기 일정, 경기 상태, 팀, 구장 데이터
> 기준: 개인 프로젝트 개발 검증 우선. 공개 또는 수익화 전에는 KBO 데이터 사용 조건을 별도로 확인한다.

## 1. 목적

`find_kbo_game`은 사용자가 팀과 날짜 또는 기간을 입력했을 때 내부 DB에서 경기 일정을 조회한다.

이 Tool은 KBO 사이트를 실시간으로 직접 호출하지 않는다.

```text
KBO 일정 수집 작업
→ raw 응답 저장
→ 정규화
→ Supabase PostgreSQL upsert
→ find_kbo_game은 Supabase만 조회
```

## 2. 현재 확인한 수집 방식

KBO 경기일정/결과 페이지는 화면 로딩 후 내부 HTTP 요청으로 일정 데이터를 가져온다.

```text
POST https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList
```

요청 파라미터:

```text
leId=1
srIdList=0,9,6
seasonId=2026
gameMonth=07
teamId=
```

이 방식은 Puppeteer, Playwright 같은 브라우저 자동화가 아니다.

```text
브라우저 실행 없음
DOM 렌더링 없음
JavaScript 실행 없음
HTTP 요청 직접 호출
```

응답은 완전한 도메인 JSON이 아니라 KBO 표 렌더링용 JSON이다. 경기 정보, 링크, 스코어는 `Text` 필드의 HTML 조각 안에 들어있으므로 정규화 파서가 필요하다.

## 3. 2026년 샘플 수집 결과

검증 파일:

```text
data/raw/kbo/2026/*.json
data/processed/kbo_schedule_2026_normalized.json
```

2026년 기준 수집 결과:

```json
{
  "count": 675,
  "date_min": "2026-03-28",
  "date_max": "2026-09-06",
  "status_counts": {
    "completed": 470,
    "cancelled": 21,
    "scheduled": 184
  },
  "missing_team_id": 0,
  "missing_stadium_id": 0,
  "missing_source_game_id": 175
}
```

월별 건수:

| 월 | 건수 |
|---|---:|
| 01 | 0 |
| 02 | 0 |
| 03 | 15 |
| 04 | 130 |
| 05 | 135 |
| 06 | 125 |
| 07 | 110 |
| 08 | 130 |
| 09 | 30 |
| 10 | 0 |
| 11 | 0 |
| 12 | 0 |

확인된 비고 값:

| 원본 비고 | 내부 처리 |
|---|---|
| `-` | 특이사항 없음 |
| `우천취소` | `cancelled`, `status_reason = "우천취소"` |
| `그라운드사정` | 추가 확인 필요. 우선 `cancelled` 또는 `unknown` 후보 |

## 4. 저장 원칙

크롤링 데이터를 전부 컬럼으로 쪼개지 않는다.

서비스 조회에 필요한 정규화 필드는 컬럼으로 저장하고, 원본 응답 전체는 JSONB로 보관한다.

```text
raw 응답 전체
→ kbo_schedule_raw_snapshots.response_json

서비스 조회 필드
→ kbo_games 컬럼

상태 변경 이력
→ kbo_game_status_history
```

이렇게 하면 원본 구조가 바뀌거나 정규화 규칙을 고쳐야 할 때 raw snapshot에서 다시 처리할 수 있다.

## 5. Supabase 테이블

### 5.1 kbo_teams

KBO 팀과 팀 별칭 정규화를 담당한다.

```sql
create table public.kbo_teams (
  id text primary key,
  name_ko text not null,
  name_en text,
  short_name text not null,
  aliases text[] not null default '{}',
  home_stadium_id text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

초기 팀 ID:

| id | short_name | aliases 예시 |
|---|---|---|
| `LG` | LG | `LG`, `엘지`, `LG 트윈스` |
| `DOOSAN` | 두산 | `두산`, `두산 베어스` |
| `KIWOOM` | 키움 | `키움`, `키움 히어로즈` |
| `SSG` | SSG | `SSG`, `쓱`, `SSG 랜더스` |
| `KIA` | KIA | `KIA`, `기아`, `KIA 타이거즈` |
| `SAMSUNG` | 삼성 | `삼성`, `삼성 라이온즈` |
| `LOTTE` | 롯데 | `롯데`, `롯데 자이언츠` |
| `NC` | NC | `NC`, `엔씨`, `NC 다이노스` |
| `HANWHA` | 한화 | `한화`, `한화 이글스` |
| `KT` | KT | `KT`, `케이티`, `KT 위즈` |

### 5.2 kbo_stadiums

구장 표기와 홈 구단 관계를 관리한다.

```sql
create table public.kbo_stadiums (
  id text primary key,
  name_ko text not null,
  short_name text not null,
  aliases text[] not null default '{}',
  city text,
  home_team_id text references public.kbo_teams(id),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

초기 구장 ID:

| id | short_name | 비고 |
|---|---|---|
| `JAMSIL` | 잠실 | LG, 두산 홈 |
| `GOCHEOK` | 고척 | 키움 홈 |
| `MUNHAK` | 문학 | SSG 홈 |
| `GWANGJU` | 광주 | KIA 홈 |
| `DAEGU` | 대구 | 삼성 홈 |
| `SAJIK` | 사직 | 롯데 홈 |
| `CHANGWON` | 창원 | NC 홈 |
| `DAEJEON` | 대전 | 한화 홈 |
| `SUWON` | 수원 | KT 홈 |
| `POHANG` | 포항 | 삼성 제2구장 성격 |

### 5.3 kbo_games

Agent가 조회하는 핵심 경기 테이블이다.

```sql
create table public.kbo_games (
  id uuid primary key default gen_random_uuid(),

  season_year integer not null,

  source_game_id text,
  internal_game_key text not null unique,

  game_date date not null,
  start_time time,
  starts_at timestamptz,

  away_team_id text not null references public.kbo_teams(id),
  home_team_id text not null references public.kbo_teams(id),
  stadium_id text not null references public.kbo_stadiums(id),

  away_team_name text not null,
  home_team_name text not null,
  stadium_name text not null,

  game_status text not null,
  status_reason text,

  away_score integer,
  home_score integer,

  source_name text not null default 'KBO',
  source_url text not null,
  source_collected_at timestamptz not null,

  raw_snapshot_id uuid,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  check (game_status in (
    'scheduled',
    'in_progress',
    'completed',
    'cancelled',
    'postponed',
    'unknown'
  ))
);
```

인덱스:

```sql
create index idx_kbo_games_date
on public.kbo_games (game_date);

create index idx_kbo_games_home_team_date
on public.kbo_games (home_team_id, game_date);

create index idx_kbo_games_away_team_date
on public.kbo_games (away_team_id, game_date);

create index idx_kbo_games_status_starts_at
on public.kbo_games (game_status, starts_at);

create index idx_kbo_games_source_game_id
on public.kbo_games (source_game_id)
where source_game_id is not null;
```

### 5.4 kbo_schedule_raw_snapshots

KBO 응답 원본을 보관한다.

```sql
create table public.kbo_schedule_raw_snapshots (
  id uuid primary key default gen_random_uuid(),

  season_year integer not null,
  game_month integer not null,

  source_name text not null default 'KBO',
  source_url text not null,
  endpoint text not null,
  request_params jsonb not null,
  response_json jsonb not null,

  response_hash text,
  collected_at timestamptz not null default now(),

  created_at timestamptz not null default now()
);
```

인덱스:

```sql
create index idx_kbo_schedule_raw_snapshots_year_month
on public.kbo_schedule_raw_snapshots (season_year, game_month, collected_at desc);

create index idx_kbo_schedule_raw_snapshots_hash
on public.kbo_schedule_raw_snapshots (response_hash);
```

### 5.5 kbo_game_status_history

경기 상태와 스코어 변경 이력을 남긴다.

```sql
create table public.kbo_game_status_history (
  id uuid primary key default gen_random_uuid(),

  game_id uuid not null references public.kbo_games(id) on delete cascade,

  previous_status text,
  new_status text not null,

  previous_reason text,
  new_reason text,

  previous_away_score integer,
  previous_home_score integer,
  new_away_score integer,
  new_home_score integer,

  raw_snapshot_id uuid references public.kbo_schedule_raw_snapshots(id),

  changed_at timestamptz not null default now()
);
```

## 6. 내부 경기 키 정책

KBO `gameId`는 예정 경기 일부 또는 취소 경기에서 없을 수 있다. 따라서 서비스 내부에서는 항상 `internal_game_key`를 생성한다.

기본 형식:

```text
YYYYMMDD_AWAY_HOME_STADIUM
```

예:

```text
20260708_NC_HANWHA_DAEJEON
```

더블헤더 또는 같은 날짜 같은 팀 조합 중복이 발견되면 다음 형식으로 확장한다.

```text
YYYYMMDD_AWAY_HOME_STADIUM_STARTTIME_SEQUENCE
```

## 7. Upsert 정책

`kbo_games` 저장 기준은 `internal_game_key`다.

```text
insert:
  internal_game_key가 없으면 새 경기 생성

update:
  internal_game_key가 이미 있으면 상태, 스코어, 시작 시각, source_collected_at 갱신
```

`source_game_id`는 보조 식별자다. 값이 있으면 저장하지만 nullable이므로 단독 upsert 기준으로 사용하지 않는다.

상태 또는 스코어가 바뀌면 `kbo_game_status_history`에 변경 이력을 남긴다.

## 8. 상태 매핑 규칙

초기 매핑:

| 원본 신호 | 내부 상태 | 보조 필드 |
|---|---|---|
| `프리뷰`, 스코어 없음 | `scheduled` | |
| `리뷰`, 스코어 있음 | `completed` | |
| `우천취소` | `cancelled` | `status_reason = "우천취소"` |
| `그라운드사정` | `unknown` | `status_reason = "그라운드사정"` |
| 파싱 불가 | `unknown` | 원본 텍스트 보존 |

`그라운드사정`은 취소인지 연기인지 추가 샘플을 보고 확정한다. 처음 구현에서는 `unknown`으로 저장하고 Agent 응답에서 원본 사유를 함께 보여준다.

## 9. 크론 수집 정책

### 9.1 시즌 전체 동기화

목적:

```text
전체 시즌 일정 보정
신규 편성 또는 변경 반영
```

주기:

```text
매일 새벽 1회
```

범위:

```text
해당 시즌 월별 전체 수집
개인 프로젝트에서는 03~09월만 우선 수집해도 충분함
```

### 9.2 당일 정오 확인

목적:

```text
당일 경기 취소, 구장, 시작 시각 변경 조기 확인
```

주기:

```text
매일 12:00 Asia/Seoul
```

처리:

```text
오늘 날짜가 포함된 월 재수집
오늘 경기만 upsert 결과 확인
```

### 9.3 경기 시작 5분 전 확인

목적:

```text
Agent가 사용자의 직관 질문에 답하기 전에 최신 상태 확인
```

주기:

```text
scheduled 상태의 오늘 경기 starts_at - 5분
```

처리:

```text
해당 경기 월 재수집
scheduled, cancelled, postponed, unknown 상태 반영
```

### 9.4 경기 중과 종료 확인

목적:

```text
진행 중, 완료, 우천 중단 또는 취소 상태 반영
```

초기 개인 프로젝트 기준:

```text
경기 시작 후 30분 간격으로 오늘 경기 월 재수집
오늘 모든 경기가 completed 또는 cancelled가 되면 빈번한 확인 중단
```

## 10. find_kbo_game 조회 정책

`find_kbo_game`은 `kbo_games`만 조회한다.

입력:

```text
team_id
date 또는 date_from/date_to
```

조회 조건:

```text
where game_date between :date_from and :date_to
and (:team_id in (home_team_id, away_team_id))
```

응답에는 다음을 포함한다.

```text
경기 날짜와 시작 시각
홈팀과 원정팀
구장
경기 상태
취소 또는 특이 사유
출처
수집 시각
최신성 제한
```

## 11. 최신성 정책

경기 당일 데이터는 취소와 시간 변경 가능성이 있으므로 `source_collected_at`을 응답에 포함한다.

초기 기준:

| 조건 | Tool 상태 |
|---|---|
| DB 조회 성공, 결과 있음 | `success` |
| DB 조회 성공, 결과 없음 | `no_result` |
| 저장된 데이터가 있으나 당일 기준 30분 이상 오래됨 | `stale_data` |
| 크롤러 장애로 최신 확인 실패 | 기존 데이터 반환 + `limitations = ["latest_not_verified"]` |
| DB 장애 | `source_unavailable` |

## 12. 구현 순서

1. Supabase migration으로 `kbo_teams`, `kbo_stadiums`, `kbo_games`, `kbo_schedule_raw_snapshots`, `kbo_game_status_history` 생성
2. 팀과 구장 seed 작성
3. 크롤러 CLI를 `year`, `month` 인자를 받도록 정리
4. raw snapshot 저장 구현
5. 정규화 및 `kbo_games` upsert 구현
6. 상태 변경 감지와 history insert 구현
7. `find_kbo_game` repository와 service 구현
8. 크론 또는 APScheduler 연결
9. 정상, 경기 없음, 취소, stale 데이터 테스트 작성

## 13. 아직 열어둘 항목

아래 항목은 구현 중 샘플을 더 보고 확정한다.

```text
그라운드사정의 최종 상태 매핑
더블헤더 key 확장 필요 여부
in_progress 원본 신호
포스트시즌 포함 여부
raw snapshot 중복 저장을 언제 hash 기반으로 줄일지
```
