# Agent/RAG Hardcoding Cleanup Next Steps

> 작성일: 2026-08-20
> 목적: LangGraph/RAG PoC 이후 하드코딩 축소 작업의 완료 범위와 남은 보완 작업을 기록한다.

## 1. 이번 세션 완료 범위

사용자 지적:

```text
단기적인 방법으로 키워드를 하드코딩하는 것보다, 장기적으로 RAG 프로젝트에 맞는 구조가 중요하다.
현재 세팅에서 이런 하드코딩식으로 들어간 것들이 다른 곳에도 있는지 전체적으로 검토하고 개선한다.
```

이에 따라 아래 4개 범위를 우선 정리했다.

### 1차: direct answer intent routing

커밋:

```text
6186fa7 Add direct answer intent routing
```

핵심:

- 후속 질문 판별을 `graph.py` 또는 `answering.py`의 한국어 키워드 조건문으로 처리하지 않도록 정리했다.
- `ToolRoutingDecision.direct_answer_intent`를 추가했다.
- 라우터가 `selected_game_place`, `selected_game_time`, `selected_game_opponent`, `selected_game_home_away`, `selected_game_status`를 구조적으로 반환한다.
- tool 재호출 없이 `conversation_context.selected_game`에서 답할 수 있는 흐름을 스키마 기반으로 만들었다.

### 2차: RAG retrieval config 분리

커밋:

```text
10b404c Extract RAG retrieval configuration
```

핵심:

- `backend/app/domains/baseball/tool/rag_config.py`를 추가했다.
- embedding model, top_k, similarity_threshold, document_types를 도구별 config로 분리했다.
- RAG handler/retriever에 흩어진 문서 타입 필터와 검색 파라미터 하드코딩을 줄였다.

### 3차: agent tool registry 도입

커밋:

```text
7de0d63 Introduce agent tool registry
```

핵심:

- `backend/app/agent/tool_registry.py`를 추가했다.
- 라우팅 카드, executor handler, input schema, display label을 하나의 registry로 묶었다.
- `tool_executor.py`의 tool_name별 if-chain 의존을 줄였다.
- 새 도구를 추가할 때 routing card와 executor mapping이 따로 어긋날 가능성을 낮췄다.

### 4차: routing prompt assets 분리

커밋:

```text
e5cac61 Extract routing prompt assets
```

핵심:

- 라우팅 정책 프롬프트를 `backend/app/agent/prompt_assets/tool_routing_policy.md`로 분리했다.
- few-shot 예시를 `backend/app/agent/prompt_assets/tool_routing_few_shots.jsonl`로 분리했다.
- `backend/app/agent/prompts.py`는 자산 로딩, schema validation, system prompt 조립만 담당하게 했다.
- `tests/api/test_tool_routing_prompt_assets.py`를 추가해 few-shot이 `ToolRoutingRequest`, `ToolRoutingDecision` 스키마와 맞는지 검증한다.

검증:

```bash
cd backend
uv run ruff check app/agent/prompts.py tests/api/test_tool_routing_prompt_assets.py
uv run pytest tests/api
```

결과:

```text
39 passed, 3 warnings
```

## 2. 현재 상태 요약

현재 구조는 이전보다 다음 점이 좋아졌다.

- 후속 질문 판별이 로컬 키워드 if-chain이 아니라 LLM router의 structured decision으로 이동했다.
- RAG 검색 설정이 도구 코드에서 분리되어 조정 가능해졌다.
- agent tool 목록과 실행 매핑이 registry 중심으로 정리됐다.
- 라우팅 프롬프트와 few-shot이 코드 상수에서 분리되어 데이터처럼 관리 가능해졌다.
- 2026-08-20 재검토 기준으로 LangGraph 1차 PoC, backend SSE contract, frontend SSE stream 연결, Tool card upsert, conversation list sidebar는 구현되어 있다.

다만 1차 MVP 완료 판정 기준으로는 대화 복원, source drawer 실제 데이터 연결, 남은 문서의 authenticated-first 기준 정렬, 수동 QA가 아직 남아 있다. "RAG 프로젝트답게 운영된다"라고 보기에는 평가와 데이터 품질 관리도 더 필요하다.

## 3. 1차 MVP 완료까지 남은 작업

### 1순위: MVP 인증 정책 정렬

현재 계획 문서는 authenticated-first 기준으로 업데이트했다. 다만 backend/frontend 보조 문서 일부는 guest-first 기준 설명이 남아 있을 수 있다.

작업 후보:

- `docs/backend/local-development-commands.md`, `docs/frontend/mvp-chat-ux-plan.md`도 같은 기준으로 후속 정리한다.
- guest-first를 다시 도입할지 여부는 MVP1 이후 확장으로 분리한다.

완료 기준:

- planning 문서에서 `guest_id` 필수 흐름과 현재 로그인 필수 흐름이 충돌하지 않는다.
- `/api/v1/chat`의 현재 인증 요구사항이 명확히 적혀 있다.

### 2순위: 대화 이어가기 완성

현재 conversation list sidebar는 있지만, sidebar의 선택 상태가 `ChatPanel`의 `conversationId`와 message state로 이어지는 흐름은 남아 있다.

작업 후보:

- sidebar active conversation state를 `ChatPanel`과 공유한다.
- 기존 conversation 선택 시 해당 conversation의 messages를 조회해 렌더링한다.
- 이를 위해 `GET /api/v1/conversations/{conversation_id}/messages` 또는 동등한 메시지 복원 API를 추가한다.
- 새 채팅 버튼이 현재 `conversationId`와 message list를 초기화하도록 연결한다.

완료 기준:

- 사용자가 sidebar에서 이전 대화를 클릭하면 기존 메시지가 표시된다.
- 이어서 질문하면 같은 `conversation_id`로 `/api/v1/chat` 요청이 나간다.
- 새 채팅을 누르면 빈 채팅 화면에서 새 conversation을 시작한다.

### 3순위: Source Drawer 실제 데이터 연결

현재 source drawer는 UI placeholder이고, Tool result card에는 일부 근거가 표시된다.

작업 후보:

- `assistant.completed.sources` 또는 Tool result의 source/as_of/limitations를 drawer state로 모은다.
- RAG Tool 결과는 문서 제목, 출처 URL, 기준 시점, limitation을 drawer에 표시한다.
- 정형 Tool 결과는 source_name/source_url/source_collected_at이 있으면 같이 표시한다.

완료 기준:

- 대표 RAG 질문에서 drawer를 열면 실제 출처와 기준 시점을 확인할 수 있다.
- 결과 없음 또는 외부 API 한계가 limitation으로 표시된다.

### 4순위: MVP 수동 QA

대표 질문:

```text
오늘 롯데 경기 있어?
사직구장 주소 알려줘
오늘 사직 비 와?
사직 예매 어디서 해?
고척돔 음식물 반입 가능해?
보크가 뭐야?
```

follow-up 질문:

```text
롯데 오늘 경기 알려줘 -> 어디서 해?
롯데 오늘 경기 알려줘 -> 몇 시야?
롯데 오늘 경기 알려줘 -> 상대가 누구야?
```

완료 기준:

- Tool routing이 기대 Tool로 연결된다.
- Tool card가 running -> completed 또는 failed로 갱신된다.
- assistant 답변이 Tool 결과와 충돌하지 않는다.
- 에러가 발생해도 user message가 유지되고 재시도 경로가 보인다.

## 4. 남은 보완 작업 후보

### 5차 추천: RAG/라우팅 평가 기반선 구축

가장 먼저 추천하는 다음 작업이다.

목표:

- 프롬프트, retrieval config, chunk, document type을 바꿨을 때 품질이 좋아졌는지 숫자와 실패 케이스로 판단할 수 있게 한다.

작업 후보:

- `data/kbo_schedule/evaluation/cases/find_kbo_game_cases.jsonl`에 direct answer intent 기대값을 반영한다.
- `backend/scripts/evaluate_tool_routing.py`가 `direct_answer_intent`까지 비교하도록 업데이트한다.
- `data/stadium_guide/evaluation/cases/`에 전체 구장 기준 검색 평가셋을 확장한다.
- `data/baseball_knowledge/evaluation/cases/`에 야구 규칙/상식/최신 KBO 규정 케이스를 확장한다.
- 평가 결과 JSON에 top_k, threshold, embedding_model, prompt asset version 정보를 남긴다.

완료 기준:

- 라우팅 평가 스크립트가 현재 schema로 통과한다.
- RAG 검색 평가가 Top-1/Top-3 hit, no-result, wrong-document 사례를 저장한다.
- 이후 prompt/RAG config 변경 전후 비교가 가능하다.

### 6차 후보: 답변 품질 개선

목표:

- 도구 결과를 사용자에게 더 자연스럽고 직관적인 한국어로 보여준다.

작업 후보:

- `scheduled`, `cancelled`, `postponed`, `completed` 같은 상태 값을 사용자 표시용 한국어로 변환한다.
- 단일 경기 결과는 "오늘 롯데는 18:00 사직에서 NC와 경기 예정입니다."처럼 한 문장에 핵심을 담는다.
- RAG 답변에서 근거 문서가 없을 때는 확신을 낮추고 공식 확인 필요성을 명확히 말한다.

대상 후보:

- `backend/app/agent/answering.py`
- `backend/app/agent/graph.py`
- `backend/tests/api/test_chat_auth_owner.py`

### 7차 후보: conversation context 정책 고도화

목표:

- 여러 경기, 새 팀/새 날짜 질문, 순번 참조를 안정적으로 처리한다.

정해야 할 것:

- 여러 경기 결과가 나왔을 때 `selected_game`을 저장할지, 저장하지 않을지.
- "첫 번째 경기", "두 번째 경기" 같은 선택 발화를 지원할지.
- 새 팀/새 날짜 조회가 들어왔을 때 이전 selected context를 언제 폐기할지.
- `selected_stadium`, `selected_team`, `selected_game` 간 우선순위를 어떻게 둘지.

### 8차 후보: 로컬 seed/개발 데이터 안정화

목표:

- 수동 QA 전에 DB가 비어 있어서 결과가 어긋나는 문제를 줄인다.

작업 후보:

- 개발용 README에 일정 import 명령을 명확히 추가한다.
- `kbo_games`가 비어 있을 때 개발 환경에서 경고 로그를 남긴다.
- `supabase db reset` 이후 schedule import를 쉽게 재실행할 수 있는 helper command를 문서화한다.

주의:

- DB seed, migration, reset 변경은 별도 확인을 받고 진행한다.

## 5. 다음 세션 시작 추천 순서

1. `git status --short`로 작업 트리가 깨끗한지 확인한다.
2. 1차 MVP를 먼저 닫는다면 sidebar conversation 선택과 message 복원 흐름부터 구현한다.
3. 이어서 Source Drawer에 실제 source/limitation 데이터를 연결한다.
4. 대표 질문 6개와 follow-up 질문 3개를 수동 QA한다.
5. RAG/라우팅 평가로 넘어간다면 `backend/scripts/evaluate_tool_routing.py`와 `data/kbo_schedule/evaluation/cases/find_kbo_game_cases.jsonl`를 읽는다.
6. 현재 `ToolRoutingDecision` schema와 evaluation expected shape 차이를 확인한다.
7. 평가 케이스에 `direct_answer_intent`를 추가한다.
8. 평가 스크립트가 새 필드를 비교하도록 수정한다.
9. `uv run pytest tests/api`로 회귀를 확인한다.

## 6. 참고 커밋

```text
e5cac61 Extract routing prompt assets
7de0d63 Introduce agent tool registry
10b404c Extract RAG retrieval configuration
6186fa7 Add direct answer intent routing
```
