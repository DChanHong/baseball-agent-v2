# LangChain / LangGraph Adoption Plan

> 상태: 초안
> 작성일: 2026-08-13
> 목적: baseball-agent-v2 백엔드에 LangChain과 LangGraph를 점진적으로 도입하기 위한 범위와 순서 정의

## 1. 배경

현재 baseball-agent-v2 백엔드는 FastAPI 기반 SSE 채팅 흐름과 도메인 Tool handler를 직접 조립해서 동작한다.

현재 주요 구성:

```text
FastAPI controller
ChatStreamService
ToolRoutingService
AgentToolExecutor
domain service / repository / tool handler
Supabase/Postgres conversation/message 저장
Next.js App Router frontend
```

현재 지원 Tool:

```text
find_kbo_game
get_stadium_info
get_weather_context
search_stadium_guide
search_ticketing_guide
search_baseball_knowledge
```

지금 구조의 장점은 Tool handler와 도메인 서비스가 비교적 명확히 분리되어 있다는 점이다. 반면 대화가 이어질 때 필요한 agent working context가 없다.

대표 문제:

```text
User: 롯데 오늘 야구 일정 알려줘
Assistant: 경기 일정 안내
User: 어디서 경기하는거지?
Expected: 직전 find_kbo_game 결과의 stadium을 참조
Current risk: 이전 경기 조회 결과를 안정적으로 참조하지 못함
```

메시지 DB를 매 요청마다 조회해서 이전 대화와 Tool result를 프롬프트에 직접 넣는 방식은 임시 해결은 될 수 있지만, prompt와 service 책임이 쉽게 지저분해진다. 따라서 대화 히스토리 저장소와 agent working memory의 책임을 분리한다.

## 2. 도입 판단

LangChain과 LangGraph를 둘 다 도입한다.

도입 이유:

```text
1. 실제 서비스 목적상 후속 질문 context 처리가 필요하다.
2. LangChain은 LLM 호출, prompt, structured output, retriever, RAG chain 정리에 적합하다.
3. LangGraph는 route -> tool execute -> state update -> answer generation 흐름 제어에 적합하다.
4. 학습과 포트폴리오 목적상 두 라이브러리의 책임을 분리해 적용하는 경험이 의미 있다.
5. generic agent를 통째로 쓰지 않고 명시적인 graph node/state로 운영 가능한 구조를 만들 수 있다.
```

## 3. 책임 분리

### 3.1 LangChain 책임

LangChain은 LLM application 부품 레이어로 사용한다.

적용 후보:

```text
ChatModel wrapper
ChatPromptTemplate
structured output
answer generation chain
embedding adapter
retriever adapter
RAG context formatting
tool input schema validation
```

현재 `ToolRoutingService`는 OpenAI SDK의 structured output을 직접 사용하고 있다. 이 부분은 LangChain의 structured output 기반 chain으로 점진적으로 옮길 수 있다.

RAG Tool은 이미 OpenAI embedding과 pgvector retriever를 직접 사용한다. 초기에는 handler를 유지하고, 이후 LangChain retriever adapter를 붙일지 평가한다.

### 3.2 LangGraph 책임

LangGraph는 agent workflow와 thread state 레이어로 사용한다.

적용 후보:

```text
conversation_id 기반 thread_id 매핑
turn state 관리
selected_game / selected_stadium / selected_team 저장
route node
tool_execute node
state_update node
answer_generation node
validation 또는 fallback node
```

LangGraph의 핵심 목적은 chat_messages 전체를 매번 prompt에 넣지 않고도, 다음 턴에서 필요한 작업 기억을 구조화해서 유지하는 것이다.

## 4. DB와 Graph State 책임

기존 Supabase/Postgres DB는 계속 source of truth로 둔다.

```text
chat_conversations
= 대화방 영속 정보, title, summary, metadata, 소유권

chat_messages
= 화면 렌더링, 감사 로그, user/assistant/tool 결과 이력

LangGraph state/checkpointer
= 다음 질문 이해를 위한 agent working memory
```

`conversation_id`는 LangGraph `thread_id`로 매핑한다.

주의할 점:

```text
1. LangGraph state를 유일한 영속 저장소로 보지 않는다.
2. 프론트가 의존하는 SSE event contract는 유지한다.
3. chat_messages.metadata에 routing_decision/tool_results를 계속 저장한다.
4. Graph state는 selected context를 빠르게 복원하기 위한 보조 상태로 다룬다.
```

## 5. 1차 PoC 범위

1차 목표는 아래 시나리오 하나를 안정적으로 해결하는 것이다.

```text
Turn 1
User: 롯데 오늘 야구 일정 알려줘
System: find_kbo_game 실행
State: selected_game / selected_stadium 저장

Turn 2
User: 어디서 경기하는거지?
System: 직전 selected_game.stadium_name 참조
Assistant: 경기 장소를 자연어로 답변
```

1차 PoC에서 검증할 것:

```text
conversation_id -> thread_id 매핑이 자연스럽게 동작하는가
find_kbo_game result를 selected_game state로 승격할 수 있는가
후속 질문에서 메시지 DB 전체 조회 없이 selected_game을 참조할 수 있는가
기존 SSE event contract를 유지할 수 있는가
기존 AgentToolExecutor와 Tool handler를 재사용할 수 있는가
```

## 6. 1차 Graph State 초안

초기 state는 작게 시작한다.

```text
conversation_id
user_id 또는 user_profile_id
user_message
today
timezone
favorite_team_id

routing_decision
tool_name
tool_input
tool_result
limitations

selected_team_id
selected_game
selected_stadium_id
selected_stadium_name
last_tool_name

answer
```

`selected_game` 후보 필드:

```text
game_id
game_date
start_time
away_team_id
home_team_id
away_team_name
home_team_name
stadium_id
stadium_name
game_status
```

## 7. 기존 코드 재사용 방안

### 7.1 ChatStreamService

초기에는 SSE/DB shell로 유지한다.

역할:

```text
conversation 생성 또는 조회
user message 저장
assistant placeholder 저장
BaseballAgentGraph 실행
Graph event를 기존 SSE event로 변환
assistant message 저장
conversation 갱신
```

### 7.2 ToolRoutingService

초기에는 그대로 재사용할 수 있다.

이후 변경 방향:

```text
ToolRoutingUserContext에 conversation_context 추가
OpenAI SDK 직접 호출을 LangChain structured output chain으로 교체
follow-up intent와 context resolution 정책 추가
```

### 7.3 AgentToolExecutor

그대로 재사용한다.

LangGraph `tool_execute` node에서 현재 `AgentToolExecutor.execute(decision)`을 호출하고, 결과를 graph state에 저장한다.

### 7.4 RAG Tool

초기에는 기존 handler 유지.

이후 변경 방향:

```text
embedding 호출을 LangChain Embeddings로 감싸기
pgvector retriever를 LangChain Retriever adapter로 감싸기
검색 결과 context formatting을 LangChain chain으로 분리
answer generation chain에서 citation/limitations 반영
```

## 8. 단계별 도입 순서

### Step 1. State 모델 정의

`BaseballAgentState`와 `SelectedGameContext`를 정의한다.

완료 기준:

```text
find_kbo_game result에서 selected_game을 만들 수 있다.
state serialization 기준이 정해져 있다.
```

### Step 2. Graph skeleton 추가

`BaseballAgentGraph`를 만들고 현재 흐름을 node로 나눈다.

초기 node:

```text
prepare_context
route
tool_execute
state_update
answer_generate
```

완료 기준:

```text
기존 단일 질문 동작이 깨지지 않는다.
기존 SSE event 순서가 유지된다.
```

### Step 3. 1차 follow-up context 처리

`find_kbo_game` 결과를 `selected_game`으로 저장하고, "어디서 경기하는거지?" 유형의 질문에서 이를 사용한다.

완료 기준:

```text
롯데 오늘 경기 -> 어디서 경기하는거지 시나리오가 통과한다.
message DB 전체를 prompt에 주입하지 않는다.
```

### Step 4. LangChain routing chain 도입

현재 routing prompt와 Pydantic schema를 LangChain structured output chain으로 이전한다.

완료 기준:

```text
기존 routing 평가셋 결과가 유지되거나 개선된다.
ToolRoutingDecision schema contract가 유지된다.
```

### Step 5. LangChain answer generation chain 도입

현재 `_build_assistant_content`의 템플릿 요약을 LLM 기반 답변 생성 chain으로 교체한다.

완료 기준:

```text
Tool result에 근거한 자연어 답변을 생성한다.
출처와 limitation을 답변에 반영한다.
Tool result에 없는 정보는 추측하지 않는다.
```

### Step 6. 후속 Tool 확장

1차 selected_game context를 기반으로 후속 질문을 확장한다.

확장 시나리오:

```text
User: 비 와?
-> selected_game.stadium_id + selected_game.game_date로 get_weather_context

User: 예매는 어디서 해?
-> selected_stadium_id / selected_team_id로 search_ticketing_guide

User: 좌석 추천해줘
-> selected_stadium_id로 search_stadium_guide

User: 몇 시 경기야?
-> selected_game.start_time 직접 답변
```

### Step 7. ambiguous context 처리

여러 경기가 조회되거나 context가 충돌하는 경우를 처리한다.

예:

```text
이번 주 롯데 일정 보여줘
-> 여러 경기 selected_candidates 저장

거기 비 와?
-> 어느 경기/구장을 말하는지 clarification
```

## 9. 리스크와 주의점

```text
1. LangGraph checkpointer와 기존 DB의 책임이 겹치면 디버깅이 어려워진다.
2. generic agent로 가면 현재 명시적 Tool contract의 장점이 약해진다.
3. answer generation을 너무 빨리 LLM에 맡기면 프론트 card와 답변 내용이 불일치할 수 있다.
4. streaming token과 graph event를 동시에 다루면 SSE contract가 흔들릴 수 있다.
5. LangChain/LangGraph 버전 변화에 따른 API 안정성을 확인해야 한다.
```

## 10. 우선 결론

도입 방향은 다음과 같다.

```text
LangChain은 LLM/RAG/tool schema 부품 레이어로 사용한다.
LangGraph는 conversation context와 agent workflow 레이어로 사용한다.
기존 FastAPI, auth, DB schema, domain services, tool handlers, frontend SSE event contract는 유지한다.
1차 PoC는 selected_game follow-up 시나리오로 작게 검증한다.
```

