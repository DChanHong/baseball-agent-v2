# 라이브러리 없이 만든 야구 Agent에서 LangChain과 LangGraph를 도입하려는 이유

> 상태: 초안
> 작성일: 2026-08-13
> 주제: baseball-agent-v2 백엔드가 직접 구현한 Tool 기반 채팅 구조를 넘어, context와 LLM 도구 활용을 위해 LangChain/LangGraph를 검토하게 된 과정

## 시작점

KBO 직관 도우미 서비스 `baseball-agent-v2`는 처음부터 LangChain이나 LangGraph를 사용하지 않았다.

일부러 가장 기본적인 구조부터 직접 만들었다.

```text
FastAPI controller
ChatStreamService
ToolRoutingService
AgentToolExecutor
domain service / repository / tool handler
Supabase/Postgres conversation/message 저장
SSE streaming
Next.js frontend
```

처음에는 이 선택이 좋았다. Agent 라이브러리를 먼저 붙이면 편해 보이지만, 실제로 어떤 책임이 필요한지 모른 채 추상화부터 가져오게 된다. 반대로 직접 만들면 요청이 들어와서, 어떤 Tool이 선택되고, Tool 결과가 어떻게 프론트로 흘러가며, 메시지가 어디에 저장되는지 눈으로 확인할 수 있다.

이 프로젝트에서는 먼저 다음 Tool들을 직접 구성했다.

```text
find_kbo_game
get_stadium_info
get_weather_context
search_stadium_guide
search_ticketing_guide
search_baseball_knowledge
```

경기 일정은 정형 DB 조회로 처리했고, 구장 가이드와 예매 가이드, 야구 지식은 pgvector 기반 RAG 검색으로 처리했다. 여기까지 오면 "LLM이 Tool을 잘 고르게 하고, Tool 결과를 프론트에 카드로 보여주는" 1차 Agent 백엔드는 어느 정도 만들어진다.

하지만 그 다음 문제가 나타났다.

## 문제는 Tool 개수가 아니라 context였다

대표적인 대화는 이렇다.

```text
User: 롯데 오늘 야구 일정 알려줘
Assistant: 오늘 롯데 경기 일정을 안내
User: 어디서 경기하는거지?
```

사람에게는 너무 자연스러운 질문이다. "어디서"는 직전 질문의 "롯데 오늘 경기"를 가리킨다.

그런데 현재 구조에서 routing input은 대체로 이런 정보만 가진다.

```text
message
favorite_team_id
today
timezone
```

직전 Tool result에서 나온 `stadium_id`, `stadium_name`, `game_date`, `home_team_id`, `away_team_id`는 assistant message metadata에 저장되지만, 다음 턴의 작업 기억으로 구조화되어 있지는 않다.

그래서 "어디서 경기하는거지?"라는 질문이 들어왔을 때 선택지는 애매해진다.

```text
1. chat_messages DB를 조회해서 이전 메시지와 Tool result를 프롬프트에 넣는다.
2. prompt 안에서 LLM이 알아서 직전 경기 context를 찾게 한다.
3. 서비스 코드 곳곳에서 이전 Tool result를 직접 파싱한다.
```

이 방식은 빨리 만들 수는 있다. 하지만 오래 가기 어렵다.

DB는 영구 히스토리와 화면 렌더링의 기준이어야 한다. 매 요청마다 메시지 DB를 뒤져서 "현재 사용자가 말하는 그 경기"를 추론하는 책임까지 맡기면, prompt와 service 코드가 같이 복잡해진다.

이 시점에서 필요한 것은 단순한 대화 로그가 아니라, Agent가 다음 턴에서 사용할 수 있는 working context다.

## LangChain과 LangGraph를 다시 보게 된 이유

처음에는 라이브러리 없이 직접 만드는 편이 좋았다. 하지만 이제는 필요한 추상화가 선명해졌다.

LangChain은 LLM 애플리케이션의 부품을 정리하는 데 적합하다.

```text
ChatModel wrapper
PromptTemplate
structured output
embedding
retriever
RAG chain
answer generation chain
```

현재 프로젝트에도 이미 이 역할들이 있다. 다만 직접 OpenAI SDK를 호출하고, prompt 문자열을 만들고, Pydantic schema로 routing decision을 받고 있다. 이것을 LangChain으로 옮기면 LLM 호출, prompt, structured output, RAG context formatting을 더 일관된 단위로 관리할 수 있다.

반면 LangGraph는 흐름과 상태를 다루기에 적합하다.

```text
state
node
edge
conditional edge
checkpointer
thread_id
```

야구 직관 도우미에는 이 구조가 잘 맞는다.

```text
receive user message
-> load context
-> route
-> execute tool
-> update selected_game / selected_stadium
-> generate answer
-> persist message
-> stream event
```

즉 LangChain은 부품이고, LangGraph는 흐름 제어판이다.

## DB와 memory를 분리하기

중요한 결정은 기존 DB를 버리지 않는 것이다.

기존 Supabase/Postgres는 계속 source of truth로 둔다.

```text
chat_messages
= 사용자가 실제로 본 대화, assistant 답변, Tool 결과 metadata, 감사 로그

chat_conversations
= 대화방 정보, 제목, 요약, metadata, 소유권

LangGraph state
= 다음 질문을 이해하기 위한 Agent working memory
```

예를 들어 첫 질문에서 `find_kbo_game`이 실행되어 다음 결과를 얻었다고 하자.

```text
롯데 vs 두산
2026-08-13
18:30
사직야구장
```

이 결과는 메시지 metadata에도 저장된다. 하지만 동시에 graph state에는 더 작고 명확한 형태로 저장한다.

```text
selected_team_id = LOTTE
selected_stadium_id = SAJIK
selected_stadium_name = 사직야구장
selected_game.game_date = 2026-08-13
selected_game.start_time = 18:30
selected_game.home_team_id = LOTTE
selected_game.away_team_id = DOOSAN
```

그러면 다음 질문이 들어왔을 때 전체 메시지 로그를 다시 해석할 필요가 줄어든다.

```text
User: 어디서 경기하는거지?
Assistant: 오늘 롯데 경기는 사직야구장에서 열립니다.
```

이것이 이번 도입의 핵심이다.

## 1차 목표를 작게 잡기

처음부터 모든 Agent 흐름을 LangGraph로 갈아엎지는 않는다.

1차 목표는 아래 하나다.

```text
User: 롯데 오늘 야구 일정 알려줘
-> find_kbo_game 실행
-> selected_game 저장

User: 어디서 경기하는거지?
-> selected_game.stadium_name 참조
-> 자연스럽게 답변
```

이 작은 시나리오로 검증할 수 있는 것이 많다.

```text
conversation_id를 LangGraph thread_id로 매핑할 수 있는가
Tool result를 graph state로 승격할 수 있는가
기존 SSE event contract를 유지할 수 있는가
기존 AgentToolExecutor와 Tool handler를 재사용할 수 있는가
DB 메시지 전체 조회 없이 follow-up 질문을 처리할 수 있는가
```

이 1차가 되면 확장은 자연스럽다.

```text
User: 비 와?
-> selected_game.stadium_id + selected_game.game_date로 get_weather_context

User: 예매는 어디서 해?
-> selected_stadium_id / selected_team_id로 search_ticketing_guide

User: 좌석 추천해줘
-> selected_stadium_id로 search_stadium_guide

User: 몇 시 경기야?
-> selected_game.start_time으로 직접 답변
```

## 지금 구조에서 살릴 것

이번 도입은 리팩터링을 위한 리팩터링이 아니다.

살릴 것은 살린다.

```text
FastAPI controller
auth
Supabase/Postgres schema
conversation/message 저장
SSE event contract
domain service
repository
Tool handler
AgentToolExecutor
frontend Tool card
```

특히 Tool handler는 이미 도메인 서비스와 잘 분리되어 있다. LangGraph의 `tool_execute` node는 기존 `AgentToolExecutor.execute(decision)`을 그대로 호출하면 된다.

처음부터 LangChain generic agent로 모든 Tool을 넘기지 않는 이유도 여기에 있다. 이 서비스는 운영 가능한 명시적 흐름이 중요하다. 어떤 질문에서 어떤 Tool을 호출하고, 어떤 state가 업데이트되며, 어떤 이벤트가 프론트로 나가는지 직접 볼 수 있어야 한다.

## 앞으로의 설계 방향

도입 방향은 다음과 같다.

```text
LangChain
= LLM 호출, prompt, structured output, retriever, answer generation chain

LangGraph
= route -> tool execute -> state update -> answer generation workflow

기존 DB
= 영구 대화 기록과 화면 렌더링의 source of truth

Graph state
= follow-up 질문 처리를 위한 working memory
```

가장 중요한 기준은 "라이브러리를 쓰는 것"이 아니라 "책임이 더 선명해지는가"다.

처음에는 직접 구현했다. 그래서 Agent 백엔드에 어떤 부품이 필요한지 알게 됐다.

이제는 context, structured output, RAG chain, workflow state가 필요하다. 그래서 LangChain과 LangGraph를 도입한다.

이 순서가 마음에 든다. 추상화로 시작하지 않고, 필요가 생긴 뒤 추상화를 들여오는 방식이기 때문이다.

## 다음 작업

```text
1. BaseballAgentState 초안 작성
2. selected_game context 모델 정의
3. BaseballAgentGraph skeleton 추가
4. 기존 ChatStreamService에서 graph 실행만 호출하도록 경계 정리
5. "롯데 오늘 경기 -> 어디서 경기하는거지?" 시나리오 테스트 추가
6. 이후 LangChain structured routing chain으로 점진 이전
```

