# LangGraph Routing Test Handoff

> 작성일: 2026-08-14
> 목적: LangChain/LangGraph 1차 도입 변경 이력과 다음 세션에서 이어서 검증할 테스트 방법을 기록한다.

## 1. 이번 변경 목적

`docs/planning/003-langchain-langgraph-adoption-plan.md`의 1차 PoC 범위를 구현했다.

핵심 목표:

- 기존 FastAPI/SSE/chat DB contract는 유지한다.
- `ChatStreamService` 내부의 route/tool/answer 흐름을 LangGraph workflow로 분리한다.
- `find_kbo_game` 단일 결과를 agent working memory의 `selected_game`으로 저장한다.
- 같은 `conversation_id`의 다음 턴에서 "어디서 경기하는거지?" 같은 후속 질문을 직전 경기 context로 답한다.
- `ToolRoutingService`는 OpenAI SDK 직접 structured parse 대신 LangChain structured output chain으로 전환한다.

## 2. 추가된 파일

### `backend/app/agent/state.py`

Agent working memory와 LangGraph state 타입을 추가했다.

주요 내용:

- `SelectedGameContext`
  - `find_kbo_game` 결과 중 다음 턴에 필요한 경기 정보만 보관한다.
  - `game_id`, `game_date`, `start_time`, 팀 정보, `stadium_id`, `stadium_name`, `game_status`를 담는다.
- `AgentConversationContext`
  - 대화 메시지 전체가 아니라 agent가 다음 턴 이해에 필요한 구조화 context를 담는다.
  - `selected_game`, `selected_stadium_id`, `selected_stadium_name`, `selected_team_id`, `last_tool_name`을 가진다.
  - `to_routing_context()`로 LLM router 입력용 compact context로 변환한다.
- `BaseballAgentInput`, `BaseballAgentOutput`
  - `ChatStreamService`와 graph 사이의 입출력 계약이다.
- `BaseballAgentState`
  - LangGraph node들이 공유하는 state channel이다.

### `backend/app/agent/graph.py`

LangGraph workflow를 추가했다.

Graph node:

```text
START
-> route
-> prepare_tool 또는 answer_generate
-> tool_execute
-> state_update
-> answer_generate
-> END
```

주요 동작:

- `route`
  - 이미 `selected_game`이 있고 사용자가 경기 장소를 묻는 후속 질문이면 tool/LLM 호출 없이 direct answer 경로로 보낸다.
  - 그 외에는 `ToolRoutingService`를 호출한다.
- `prepare_tool`
  - 기존 SSE contract에 필요한 `tool_call_id`, `tool_input`을 만든다.
- `tool_execute`
  - 기존 `AgentToolExecutor`를 재사용한다.
  - 성공/실패 payload shape은 기존 `chat_messages.metadata.tool_results`와 호환되게 유지한다.
- `state_update`
  - `find_kbo_game` 단일 결과를 `selected_game`으로 승격한다.
- `answer_generate`
  - direct context answer 또는 기존 tool summary answer를 만든다.

Graph는 SSE를 직접 알지 않고, `AgentGraphEvent`만 내보낸다. SSE 변환은 `ChatStreamService`가 담당한다.

### `backend/app/agent/answering.py`

기존 `ChatStreamService` 안에 있던 답변 요약 로직을 agent 계층으로 이동했다.

주요 내용:

- `build_assistant_content()`
  - clarification, unsupported, tool 실패, tool summary 답변을 생성한다.
- `promote_context_from_tool_payload()`
  - `find_kbo_game` 결과가 정확히 1건이면 `SelectedGameContext`로 승격한다.
- `can_answer_selected_game_place()`
  - "어디서", "장소", "구장", "경기장" 등 후속 장소 질문을 감지한다.
- `build_selected_game_place_answer()`
  - 저장된 `selected_game.stadium_name`으로 자연어 답변을 만든다.

### `backend/tests/api/test_tool_routing_service.py`

LangChain chain 주입 테스트를 추가했다.

검증 내용:

- 실제 OpenAI 호출 없이 fake chain의 `ainvoke()` 결과를 받는다.
- dict 응답을 `ToolRoutingDecision`으로 검증한다.
- `ToolRoutingService`가 LangChain structured chain 경로를 사용한다는 계약을 고정한다.

## 3. 편집된 파일

### `backend/app/agent/prompts.py`

라우팅 프롬프트에 conversation context 정책을 추가했다.

추가된 의미:

- `user_context.conversation_context.selected_game`이 있으면 후속 질문에서 직전 경기 context를 우선 사용한다.
- "거기", "그 경기", "어디서", "몇 시" 유형의 질문에서 `selected_game`의 구장/날짜/시간을 활용한다.

### `backend/app/agent/routing_schemas.py`

라우터 입력 schema를 확장했다.

추가된 모델:

- `SelectedGameRoutingContext`
- `ToolRoutingConversationContext`

변경된 모델:

- `ToolRoutingUserContext.conversation_context`
  - 기본값은 `None`이다.
  - 기존 평가 데이터와 호출부가 이 필드를 생략해도 깨지지 않는다.

### `backend/app/agent/routing_service.py`

OpenAI SDK 직접 호출에서 LangChain structured output chain으로 전환했다.

기존:

```text
AsyncOpenAI.responses.parse(..., text_format=ToolRoutingDecision)
```

변경 후:

```text
ChatPromptTemplate
| ChatOpenAI.with_structured_output(ToolRoutingDecision, method="json_schema", strict=True)
```

추가 고려:

- 테스트에서 fake chain을 주입할 수 있다.
- fake chain + model이 같이 주입되면 settings를 읽지 않아서 환경변수 없이 단위 테스트가 가능하다.

### `backend/app/domains/chat/service/services.py`

가장 큰 리팩터링 대상이다.

변경 전 역할:

```text
conversation/message 생성
ToolRoutingService 호출
AgentToolExecutor 호출
assistant summary 생성
assistant message 저장
SSE event emit
```

변경 후 역할:

```text
conversation/message 생성
conversation.metadata.agent_context 복원
BaseballAgentGraph 실행
Graph event를 기존 SSE event로 변환
assistant message 저장
conversation.metadata.agent_context 저장
conversation.updated/done emit
```

유지한 contract:

- `conversation.created`
- `message.created`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `assistant.delta`
- `assistant.completed`
- `conversation.updated`
- `done`
- assistant message metadata의 `routing_decision`, `tool_results`, `limitations`

추가된 metadata:

```json
{
  "agent_context": {
    "selected_game": "...",
    "selected_stadium_id": "...",
    "selected_stadium_name": "...",
    "selected_team_id": null,
    "last_tool_name": "find_kbo_game"
  }
}
```

### `backend/tests/api/test_chat_auth_owner.py`

기존 fake routing/tool executor를 graph 흐름에 맞게 보강했다.

추가된 핵심 테스트:

```text
롯데 오늘 야구 일정 알려줘
-> find_kbo_game 실행
-> 단일 경기 결과를 selected_game으로 저장

어디서 경기하는거지?
-> 같은 conversation_id 사용
-> tool.started가 다시 나오지 않음
-> tool executor 호출 수가 증가하지 않음
-> assistant 답변에 stadium_name 포함
```

이 테스트가 1차 PoC의 핵심 회귀 방지 장치다.

### `backend/pyproject.toml`

LangChain/LangGraph 의존성을 추가했다.

추가된 dependency:

```text
langchain
langgraph
langchain-openai
```

### `backend/uv.lock`

`uv add` 결과로 lockfile이 갱신되었다.

주요 추가 패키지:

- `langchain`
- `langchain-core`
- `langchain-openai`
- `langgraph`
- `langgraph-checkpoint`
- `langgraph-prebuilt`
- `langgraph-sdk`
- `langsmith`
- `tiktoken`
- 기타 하위 의존성

## 4. 다음 세션에서 기본 검증 방법

### 4.1 수정 범위 lint

프로젝트 루트에서 실행한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2
backend/.venv/bin/ruff check \
  backend/app/agent \
  backend/app/domains/chat/service/services.py \
  backend/tests/api/test_chat_auth_owner.py \
  backend/tests/api/test_tool_routing_service.py
```

검증 중인 내용:

- 새 agent graph/state/answering/routing service 코드의 import, style, lint 오류 여부
- graph 리팩터링이 들어간 `ChatStreamService`의 정적 품질
- 이번 변경으로 추가/수정된 테스트 파일의 lint 상태

주의:

- `backend/.venv/bin/ruff check backend/app backend/tests` 전체를 돌리면 기존 파일의 import order 이슈가 함께 잡힐 수 있다.
- 이번 변경 범위만 확인하려면 위 명령을 우선 사용한다.

### 4.2 전체 backend test

테스트 collection 단계에서 settings가 필요하므로 임시 환경변수를 넣어서 실행한다.

```bash
cd /Users/hong/Desktop/baseball-agent-v2
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres \
OPENAI_API_KEY=test \
backend/.venv/bin/python -m pytest backend/tests
```

현재 확인된 결과:

```text
25 passed, 3 warnings
```

검증 중인 내용:

- 기존 auth/profile/chat/weather/RAG tool API 테스트 회귀 여부
- LangGraph 도입 후 기존 SSE contract 테스트 유지 여부
- `selected_game` follow-up 시나리오 통과 여부
- LangChain routing service fake chain 주입 계약 통과 여부

현재 경고:

- FastAPI/TestClient 관련 deprecation warning
- cookie per-request 설정 관련 deprecation warning

이번 변경과 직접 관련된 실패는 아니다.

### 4.3 핵심 PoC 테스트만 빠르게 실행

```bash
cd /Users/hong/Desktop/baseball-agent-v2
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres \
OPENAI_API_KEY=test \
backend/.venv/bin/python -m pytest \
  backend/tests/api/test_chat_auth_owner.py \
  backend/tests/api/test_tool_routing_service.py
```

검증 중인 내용:

- 로그인 사용자 profile id 기준 chat message 저장이 유지되는지
- 첫 턴 tool 결과가 `conversation.metadata.agent_context.selected_game`으로 저장되는지
- 두 번째 턴 장소 질문이 tool 재호출 없이 selected_game으로 답하는지
- `ToolRoutingService`가 LangChain structured chain 결과를 `ToolRoutingDecision`으로 처리하는지

## 5. 수동 동작 테스트 시나리오

아래는 실제 서버/프론트에서 확인할 때의 기준 시나리오다.

### 5.1 준비

로컬 Supabase와 backend/frontend가 필요하다.

Supabase를 새로 시작해야 한다면 DB 작업에 해당하므로 사용자 확인 후 진행한다.

Backend:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 4000
```

Frontend:

```bash
cd /Users/hong/Desktop/baseball-agent-v2/frontend
pnpm dev
```

### 5.2 브라우저 시나리오

같은 채팅방에서 순서대로 입력한다.

```text
롯데 오늘 야구 일정 알려줘
```

기대:

- `tool.started`가 한 번 발생한다.
- `tool.completed`가 한 번 발생한다.
- assistant 답변은 기존처럼 "경기 일정을 조회했습니다..." 계열이어도 된다.
- assistant message metadata 또는 conversation metadata에 `agent_context.selected_game`이 저장된다.

이어서 같은 채팅방에 입력한다.

```text
어디서 경기하는거지?
```

기대:

- 새 `tool.started`가 발생하지 않는다.
- assistant 답변에 직전 경기의 `stadium_name`이 포함된다.
- 기존 메시지 목록/SSE rendering이 깨지지 않는다.

### 5.3 확인하고 싶은 내부 상태

DB 또는 로그로 확인할 수 있다면 다음을 보면 된다.

```text
chat_conversations.metadata.agent_context.selected_game
chat_messages.metadata.agent_context.selected_game
chat_messages.metadata.routing_decision
chat_messages.metadata.tool_results
```

핵심은 `chat_messages` 전체 히스토리를 prompt에 넣지 않고도 `conversation.metadata.agent_context`로 다음 턴 context를 복원하는 것이다.

## 6. 아직 하지 않은 일

이번 구현에서 의도적으로 제외한 것:

- LangGraph Postgres checkpointer 도입
- checkpointer용 DB migration 추가
- LangChain 기반 answer generation chain 도입
- RAG retriever를 LangChain Retriever adapter로 감싸기
- 여러 경기 후보인 경우 `selected_candidates` 관리
- "비 와?", "예매는 어디서 해?", "좌석 추천해줘" 같은 후속 tool 확장

다음 단계 추천:

1. 현재 PoC를 실제 브라우저/SSE로 수동 검증한다.
2. `selected_game` 후속 질문 유형을 "몇 시 경기야?"까지 확장한다.
3. 여러 경기 조회 결과에 대한 clarification 정책을 추가한다.
4. 그 다음에 LangGraph Postgres checkpointer 또는 별도 `agent_context` 저장 테이블을 검토한다.

## 7. 주의사항

- 현재 working memory는 LangGraph checkpointer가 아니라 `chat_conversations.metadata.agent_context`에 저장한다.
- DB migration 없이 PoC를 끝내기 위한 선택이다.
- 서버 재시작 후에도 conversation metadata가 DB에 저장되어 있으면 context 복원은 가능하다.
- 다만 LangGraph native checkpoint history, replay, interrupt 같은 기능은 아직 사용하지 않는다.
- Postgres checkpointer를 붙이려면 DB schema 변경 또는 checkpointer setup이 필요하므로 별도 승인 후 진행한다.
