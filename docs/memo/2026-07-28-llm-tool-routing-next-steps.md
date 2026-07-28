# LLM Tool Routing 다음 작업 메모

> 작성일: 2026-07-28  
> 목적: 새 세션에서 `gpt-5-mini` 기반 tool routing 평가와 채팅 LLM 연결 작업을 이어가기 위한 현재 상태 정리

## 1. 현재 완료된 작업

### 1.1 KBO 경기일정 DB와 조회 API

완료 커밋:

```text
030e453 feat: add kbo schedule import pipeline
bc138a6 feat: add kbo game lookup api
```

확인된 상태:

```text
supabase db reset: 성공
kbo_teams: 10
kbo_stadiums: 10
kbo_games: 675
min(game_date): 2026-03-28
max(game_date): 2026-09-06
```

조회 API:

```text
GET /api/v1/games
```

예:

```text
GET /api/v1/games?team_id=LOTTE&date_from=2026-07-01&date_to=2026-07-31
GET /api/v1/games?team_id=LG&date=2026-03-28
```

### 1.2 OpenAI client와 find_kbo_game tool handler

완료 커밋:

```text
349bd12 feat: add openai client and kbo game tool
```

주요 파일:

```text
backend/app/core/llm.py
backend/app/domains/baseball/tool/find_kbo_game/schemas.py
backend/app/domains/baseball/tool/find_kbo_game/handler.py
```

OpenAI 모델 기본값:

```text
OPENAI_MODEL=gpt-5-mini
```

OpenAI 연결 확인 명령:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend

uv run python - <<'PY'
import asyncio

from app.core.config import get_settings
from app.core.llm import get_openai_client


async def main() -> None:
    settings = get_settings()
    client = get_openai_client()

    response = await client.responses.create(
        model=settings.openai_model,
        input="Say only: ok",
    )

    print(response.output_text)


asyncio.run(main())
PY
```

### 1.3 로깅 정책과 구현

완료 커밋:

```text
96ca830 chore: add backend logging policy
```

주요 파일:

```text
backend/app/core/logging.py
docs/backend/policy/logging-policy.md
```

로깅 원칙:

- Python 표준 `logging` 사용
- API key, prompt 전문, 사용자 메시지 전문, tool result 전체 payload는 로그에 남기지 않음
- 유스케이스 시작/완료, tool 호출 시작/완료/실패, 조회 조건과 결과 개수 중심으로 기록

### 1.4 채팅 진입과 경기일정 조회 정책

완료 커밋:

```text
b7ae853 docs: add conversation entry policy
```

정책 문서:

```text
docs/backend/policy/conversation-entry-policy.md
```

확정 정책 요약:

1. 로그인은 채팅 시작 시 필수다.
2. 팀 선택은 선택 사항이다.
3. 팀을 선택하지 않아도 자유 질문은 가능하다.
4. 팀이 필요한 일정 질문에서 팀 정보가 없으면 되묻는다.
5. 팀 선택 유저는 `favorite_team_id`를 기본 `team_id`로 사용한다.
6. 질문에 명시된 팀은 `favorite_team_id`보다 우선한다.
7. 경기일정 조회 tool은 일정/경기 상태 의도일 때만 호출한다.
8. 야구 외 질문은 정중히 거절한다.

### 1.5 Evaluation 데이터셋 구조

이번 커밋 예정:

```text
data/evaluation/
```

추가된 구조:

```text
data/evaluation/
├── README.md
├── answer_quality/
│   └── README.md
├── runs/
│   └── README.md
└── tool_routing/
    ├── README.md
    ├── find_kbo_game_cases.jsonl
    └── schemas/
        └── find_kbo_game_case.schema.json
```

초기 데이터셋:

```text
data/evaluation/tool_routing/find_kbo_game_cases.jsonl
```

검증 결과:

```text
cases: 20
tool_calls: 10
clarifications: 2
out_of_scope: 2
unsupported: 5
```

## 2. 다음 작업 우선순위

### 2.1 Tool routing 출력 스키마 정의

LLM이 최종 답변을 생성하기 전, 먼저 tool routing 판단만 구조화해서 반환하도록 만든다.

예상 출력:

```json
{
  "is_in_scope": true,
  "should_call_tool": true,
  "tool_name": "find_kbo_game",
  "args": {
    "team_id": "LOTTE",
    "date": "2026-07-28",
    "date_from": null,
    "date_to": null
  },
  "needs_clarification": false,
  "clarification_reason": null,
  "unsupported_reason": null
}
```

추천 파일:

```text
backend/app/domains/conversation/agent/
├── __init__.py
├── prompts.py
├── routing_schemas.py
└── routing_service.py
```

### 2.2 Baseline prompt 작성

정책 문서 기준으로 `gpt-5-mini`에게 다음을 판단하게 한다.

- 야구/KBO 서비스 범위 안인지
- `find_kbo_game` 호출이 필요한지
- `team_id`, `date`, `date_from`, `date_to`
- 되묻기가 필요한지
- 현재 tool로 처리 어려운 질문인지

기법:

```text
Zero-shot baseline + Structured Outputs
```

Few-shot은 baseline 평가 후 추가한다.

### 2.3 Evaluation script 작성

추천 파일:

```text
backend/scripts/evaluate_tool_routing.py
```

역할:

1. `data/evaluation/tool_routing/find_kbo_game_cases.jsonl` 로드
2. 각 케이스를 `gpt-5-mini` routing service에 입력
3. expected와 actual 비교
4. metrics 출력
5. 결과를 `data/evaluation/runs/tool_routing/find_kbo_game/` 아래 저장

초기 metrics:

```text
total
is_in_scope_accuracy
should_call_tool_accuracy
tool_name_accuracy
team_id_accuracy
date_accuracy
date_range_accuracy
clarification_accuracy
unsupported_accuracy
failed_case_ids
```

### 2.4 LangChain 도입은 보류

현재 판단:

```text
LangChain은 나중에 도입한다.
```

이유:

- 현재 우선순위는 tool routing 판단과 파라미터 추출 평가
- OpenAI SDK 직접 사용이 디버깅하기 쉬움
- tool이 늘고 RAG/retriever/memory/trace가 필요해질 때 LangChain으로 migration

## 3. 참고 정책과 문서

```text
docs/backend/policy/conversation-entry-policy.md
docs/backend/policy/logging-policy.md
docs/backend/folder-design/folder-design.md
docs/planning/game-schedule/001-data-collection-and-db.md
```

## 4. 주의사항

- `.env`는 커밋하지 않는다.
- OpenAI API key는 로그에 남기지 않는다.
- tool routing 평가에서는 최종 자연어 답변 품질을 평가하지 않는다.
- 먼저 tool 호출 여부와 파라미터 추출만 분리 평가한다.
- KBO 경기일정은 RAG가 아니라 정형 DB 조회 tool로 처리한다.
- RAG는 구장 가이드, 좌석, 응원, 교통, 음식, 직관 팁 같은 비정형 문서에 적용한다.
