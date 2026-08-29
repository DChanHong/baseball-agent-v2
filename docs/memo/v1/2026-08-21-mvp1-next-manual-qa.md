# MVP1 다음 작업: 수동 QA

> 작성일: 2026-08-21
> 목적: MVP1 개발 완료 후 남은 수동 검증 작업을 기록한다.

## 현재 상태

MVP1 개발 항목은 모두 완료됐다. 남은 작업은 수동 QA 하나뿐이다.

## 검증 시나리오

### 대표 질문 6개

```text
오늘 롯데 경기 있어?
사직구장 주소 알려줘
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

### follow-up 질문 3개 (경기 조회 후 이어서)

```text
롯데 오늘 경기 알려줘 → 어디서 해?
롯데 오늘 경기 알려줘 → 몇 시야?
롯데 오늘 경기 알려줘 → 상대가 누구야?
```

## 확인 기준

- Tool routing이 기대 Tool로 연결된다.
- Tool card가 running → completed 또는 failed로 갱신된다.
- assistant 답변이 Tool 결과와 충돌하지 않는다.
- 에러가 발생해도 user message가 유지되고 재시도 경로가 보인다.
- follow-up 질문에서 `selected_game` context가 유지된다.

## 준비 사항

QA 전에 로컬 환경이 정상인지 확인한다.

```bash
# 터미널 1: Supabase
supabase start
supabase status

# 터미널 2: FastAPI
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000

# 터미널 3: Next.js
cd frontend
pnpm dev
```

`kbo_games` 테이블에 오늘 날짜 기준 데이터가 있는지 확인한다. 비어 있으면 일정 import 스크립트를 먼저 실행한다.
