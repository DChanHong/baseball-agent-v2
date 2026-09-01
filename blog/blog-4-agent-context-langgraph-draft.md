# [AI Agent] LangGraph 도입: Tool보다 먼저 정리해야 했던 Context

## 개요

KBO Mate는 처음부터 LangGraph로 만든 Agent가 아니었습니다.

먼저 FastAPI, Tool Router, Tool Handler, SSE, Supabase 저장 구조를 직접 만들고 나서, 대화가 이어질 때 필요한 context 문제가 드러났습니다.

이번 글에서는 KBO Mate에 LangGraph를 전면 도입하지 않고, `selected_game` 중심의 Compact Context를 처리하기 위해 작게 도입한 과정을 정리해보겠습니다.

## 1. 시작점

초기 KBO Mate 백엔드는 Agent 프레임워크 없이 직접 구성했습니다.

당시 구조는 다음과 같았습니다.

```text
FastAPI controller
ChatStreamService
ToolRoutingService
AgentToolExecutor
domain service / repository / tool handler
Supabase PostgreSQL conversation/message 저장
SSE streaming
Next.js frontend
```

Tool도 직접 연결했습니다.

```text
find_kbo_game
get_stadium_info
get_weather_context
search_stadium_guide
search_ticketing_guide
search_baseball_knowledge
```

이 구조는 MVP 초반에는 충분했습니다.

사용자 메시지가 들어오면 routing을 하고, 필요한 Tool을 실행하고, Tool 결과를 SSE event로 프론트엔드에 전달할 수 있었습니다.

하지만 Tool 개수가 늘어난 뒤에 더 중요한 문제가 보였습니다.

## 2. 문제는 Tool 개수가 아니라 Context였습니다

대표적인 대화는 다음과 같습니다.

```text
User: 롯데 오늘 야구 일정 알려줘
Assistant: 오늘 롯데 경기 일정을 안내
User: 어디서 경기하는거지?
```

사람에게는 자연스러운 후속 질문입니다.

`어디서`는 직전 질문에서 조회한 롯데 경기를 가리킵니다.

그런데 첫 구현에서 routing input은 주로 현재 메시지와 사용자 기본 정보 중심이었습니다.

```text
message
favorite_team_id
today
timezone
```

직전 Tool 결과에는 경기장, 경기일, 홈팀, 원정팀 정보가 있었지만, 다음 턴에서 바로 사용할 수 있는 working context로 정리되어 있지는 않았습니다.

그래서 후속 질문을 처리하려면 선택지가 애매해졌습니다.

```text
이전 chat_messages를 다시 읽어 LLM에게 넣는다.

assistant message metadata 안의 Tool result를 서비스 코드에서 직접 파싱한다.

프롬프트 안에서 LLM이 직전 경기 정보를 알아서 찾게 한다.
```

모두 가능은 하지만, MVP 구조가 빨리 복잡해질 수 있었습니다.

이 시점에서 필요했던 것은 전체 대화 로그가 아니라, 다음 턴의 routing과 답변에 실제로 필요한 작은 context였습니다.

## 3. Compact Context 설계

현재 코드에서 Agent working memory는 `AgentConversationContext`로 정의했습니다.

핵심 schema는 다음과 같습니다.

```text
selected_game
selected_stadium_id
selected_stadium_name
selected_team_id
last_tool_name
```

`selected_game` 안에는 다음 값만 저장합니다.

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

이 context는 일반 message history와 역할이 다릅니다.

```text
chat_messages
→ 사용자가 실제로 본 대화, assistant 답변, Tool 결과 metadata를 저장합니다.

chat_conversations.metadata.agent_context
→ 다음 request에서 복원할 compact working memory를 저장합니다.

LangGraph State
→ 한 번의 Agent 실행 중 routing, Tool 실행, context update, answer generation에 사용합니다.
```

즉, DB에 대화 전체를 저장하되, 다음 턴의 판단에는 compact context만 넘기는 구조입니다.

## 4. 왜 Tool 결과 전체를 저장하지 않았나

`find_kbo_game` 결과 전체를 memory에 저장할 수도 있었습니다.

하지만 그렇게 하지 않았습니다.

Tool 결과 전체를 계속 남기면 다음 문제가 생길 수 있기 때문입니다.

```text
불필요한 context가 계속 커진다.

이전 Tool 결과의 세부 정보가 다음 질문에 과하게 영향을 줄 수 있다.

RAG 검색 결과처럼 일회성 근거에 가까운 정보가 다음 턴에서 사실처럼 재사용될 수 있다.

여러 경기 결과가 나온 경우 어떤 경기를 사용해야 하는지 더 애매해진다.
```

그래서 현재 구현에서는 `find_kbo_game`이 성공했고, 결과가 정확히 1개일 때만 `selected_game`으로 승격합니다.

반대로 다음 경우에는 `selected_game`을 새로 만들지 않습니다.

```text
Tool 실행이 실패한 경우

find_kbo_game이 아닌 Tool인 경우

find_kbo_game 결과가 0개인 경우

find_kbo_game 결과가 여러 개인 경우
```

이 경우에는 필요하면 `last_tool_name` 정도만 갱신합니다.

RAG 결과를 memory로 승격하지 않은 이유도 같습니다. 구장 안내나 야구 지식 검색 결과는 답변 근거로는 중요하지만, 다음 턴의 사용자 의도를 고정할 정도의 상태는 아니라고 봤습니다.

## 5. LangGraph를 작게 도입한 이유

LangGraph를 도입한 이유는 Agent를 더 화려하게 만들기 위해서가 아니었습니다.

요청 하나가 들어왔을 때 다음 흐름을 명확한 node로 나누고 싶었습니다.

```text
route
→ prepare_tool
→ tool_execute
→ state_update
→ answer_generate
```

현재 그래프 흐름은 다음과 같습니다.

```text
START
→ route
→ 조건 분기
  → prepare_tool
  → tool_execute
  → state_update
  → answer_generate
→ END
```

Tool을 호출하지 않아도 되는 경우에는 바로 답변 생성으로 갑니다.

```text
START
→ route
→ answer_generate
→ END
```

이 구조가 필요한 이유는 상태 변경 지점을 분리하기 위해서였습니다.

Tool 실행과 context 업데이트가 같은 곳에 섞이면, 어떤 Tool 결과가 memory로 승격됐는지 추적하기 어려워집니다. 그래서 `tool_execute`와 `state_update`를 나눴습니다.

## 6. 저장과 복원

현재 구현에서는 LangGraph checkpointer를 별도로 사용하지 않습니다.

대신 기존 대화 DB를 그대로 유지하면서, conversation metadata에 compact context를 저장합니다.

요청이 들어올 때는 다음 흐름으로 복원합니다.

```text
chat_conversations.metadata.agent_context 읽기
→ AgentConversationContext로 validate
→ BaseballAgentInput.context에 주입
→ routing 시 conversation_context로 전달
```

응답이 끝나면 다시 저장합니다.

```text
graph_output.context
→ assistant_message.metadata.agent_context 저장
→ chat_conversations.metadata.agent_context 저장
```

metadata가 없거나 validation에 실패하면 빈 `AgentConversationContext`로 시작합니다.

이 선택은 PoC 범위를 작게 유지하기 위한 것이었습니다. 대화 저장은 이미 Supabase PostgreSQL에 있었기 때문에, MVP 단계에서 LangGraph checkpointer까지 별도로 도입할 필요는 크지 않았습니다.

## 7. 후속 질문 처리

Compact Context가 있으면 다음 질문을 DB message history 전체 없이 처리할 수 있습니다.

예를 들어 직전 `find_kbo_game` 결과가 하나였고, context에 다음 값이 저장되어 있다고 가정합니다.

```text
selected_team_id = LOTTE
selected_stadium_id = DAEJEON
selected_stadium_name = 대전 한화생명 볼파크

selected_game.game_date = 2026-07-28
selected_game.start_time = 18:30:00
selected_game.away_team_id = LOTTE
selected_game.home_team_id = HANWHA
selected_game.away_team_name = 롯데
selected_game.home_team_name = 한화
selected_game.game_status = scheduled
```

그러면 routing 단계에서 다음과 같은 direct answer intent를 만들 수 있습니다.

```text
어디서 경기하는거지?
→ selected_game_place

몇 시야?
→ selected_game_time

상대가 누구야?
→ selected_game_opponent

홈 경기야?
→ selected_game_home_away

오늘 취소됐어?
→ selected_game_status
```

이 경우 Tool을 다시 호출하지 않고, `answer_generate` 단계에서 context 기반 답변을 만듭니다.

즉, 현재 Compact Context의 1차 목적은 복잡한 장기 기억이 아니라, 직전 경기 조회에 대한 후속 질문을 안정적으로 처리하는 것입니다.

## 8. SSE 계약 유지

LangGraph를 도입하면서도 기존 SSE event 계약은 유지했습니다.

그래프 내부 event는 서비스 계층에서 SSE event로 변환됩니다.

현재 흐름에서 중요한 event는 다음과 같습니다.

```text
tool.started
tool.completed
tool.failed
assistant.delta
assistant.completed
conversation.updated
done
```

Tool 실행 중 예외가 발생하면 Graph 전체를 바로 중단하지 않습니다.

현재 구조에서는 `tool_execute`에서 예외를 잡고 `tool.failed` payload를 만든 뒤, 이후 `answer_generate`까지 진행합니다.

사용자에게는 내부 exception을 그대로 던지는 대신 다음과 같은 실패 답변을 만들 수 있습니다.

```text
도구 실행 중 문제가 생겨서 정확한 결과를 가져오지 못했습니다. 잠시 뒤 다시 시도해 주세요.
```

이 판단은 사용자 경험을 위해서였습니다.

기술적으로 Tool이 실패했더라도 채팅 스트림 전체가 갑자기 끊기면 사용자는 상황을 이해하기 어렵습니다. 실패도 하나의 Agent 상태로 보고, 프론트엔드가 `tool.failed` 카드를 보여준 뒤 assistant 답변까지 받을 수 있게 했습니다.

## 9. 현재 한계

현재 구현은 의도적으로 작습니다.

아직 다음 기능은 들어가 있지 않습니다.

```text
LangGraph checkpointer 기반 영속 memory

여러 경기 후보를 selected_candidates로 저장하는 구조

selected_game을 이용해 get_weather_context 입력을 자동 보강하는 흐름

selected_stadium_id / selected_team_id를 이용해 ticketing 또는 stadium guide Tool 입력을 자동 보강하는 흐름

Tool retry

동일 Tool 반복 방지

장기 사용자 memory
```

또한 현재 graph는 여러 Tool을 반복 호출하는 agentic loop가 아닙니다.

한 request에서 routing 결과에 따라 최대 하나의 Tool을 실행하고, 이후 answer generation으로 끝나는 구조입니다.

이 제한은 MVP 단계에서는 장점이었습니다. 어떤 질문에서 어떤 Tool이 호출되고, 어떤 context가 업데이트되는지 예측 가능해야 했기 때문입니다.

## 10. 정리

이번 작업에서 LangGraph를 도입한 이유는 "Agent 프레임워크를 쓰기 위해서"가 아니었습니다.

직접 만든 Tool 기반 구조에서 후속 질문 context 문제가 드러났고, 그 문제를 작게 풀기 위해 Graph State와 node 흐름을 도입했습니다.

현재 구조에서 핵심은 다음과 같습니다.

```text
DB message history는 대화 기록으로 유지한다.

Compact Context는 다음 턴의 판단에 필요한 상태만 저장한다.

Tool 결과 전체를 memory로 남기지 않는다.

find_kbo_game 단일 결과만 selected_game으로 승격한다.

LangGraph는 route / tool_execute / state_update / answer_generate 흐름을 분리한다.

Tool 실패도 Graph 상태로 다루고, 답변 생성까지 이어간다.
```

결국 이 작업의 핵심은 더 많은 기억을 넣는 것이 아니라, 다음 질문에 필요한 기억만 남기는 것이었습니다.

Agent에서 context는 많을수록 좋은 값이 아니라, 다음 판단을 안정적으로 만드는 만큼만 선별되어야 한다고 봤습니다.
