# Backend 학습 로드맵

> 라벨: `REFERENCE`  
> 대상: `backend/`  
> 목적: Python/FastAPI 문법에 익숙하지 않아도 현재 백엔드 구조를 단계별로 읽을 수 있게 한다.  
> 추천 방식: 이 문서를 먼저 읽고, 각 단계의 파일을 IDE에서 열어 실제 코드 흐름을 따라간다.

## 1. 한 문장으로 보는 backend

이 백엔드는 FastAPI로 HTTP API를 열고, SQLAlchemy async로 Supabase PostgreSQL을 조회/저장하며, LangChain/LangGraph/OpenAI를 이용해 KBO 직관 도우미 채팅 Agent를 실행한다.

큰 흐름은 다음과 같다.

```text
Frontend
-> FastAPI router
-> dependency 조립
-> service/use case
-> repository 또는 agent/tool
-> PostgreSQL, OpenAI, KMA API
-> response 또는 SSE stream
```

## 2. 먼저 잡아야 할 mental model

Node.js 경험이 있다면 다음처럼 대응해서 보면 된다.

| 이 프로젝트의 Python/FastAPI | Node.js에서 비슷한 역할 |
|---|---|
| `app/main.py` | Express/Nest 서버 bootstrap |
| `APIRouter` | Express router, Nest controller module |
| `Depends(...)` | 요청 단위 dependency injection |
| `controller/router.py` | HTTP endpoint handler |
| `controller/schemas.py` | request/response validation schema |
| `service/services.py` | use case service |
| `service/dto.py` | service 입출력 타입 |
| `domain/entities.py` | 순수 domain object |
| `domain/repositories.py` | repository interface 또는 protocol |
| `infrastructure/models.py` | ORM table model |
| `infrastructure/repositories.py` | DB repository implementation |
| `agent/` | LLM routing/workflow orchestration |
| `scripts/` | batch/import/evaluation script |
| `tests/` | pytest 테스트 |

## 3. 추천 학습 순서

### Step 1. 실행 진입점과 API 라우팅

먼저 FastAPI 애플리케이션이 어떻게 만들어지는지 본다.

읽을 파일:

- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/api/v1/router.py`
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`

확인할 질문:

- `FastAPI(...)` 객체는 어디에서 만들어지는가?
- `/api/v1` prefix는 어디에서 붙는가?
- `auth`, `chat`, `games`, `conversations` router는 어디에서 합쳐지는가?
- `.env` 값은 어떤 방식으로 `Settings` 객체가 되는가?
- DB session은 요청마다 어떻게 생성되고 닫히는가?

### Step 2. 가장 단순한 도메인 흐름

`games` 조회는 구조를 배우기 가장 좋다. 인증/스트리밍/LLM이 없고 Controller-Service-Repository 흐름이 명확하다.

읽을 파일:

- `backend/app/domains/baseball/controller/router.py`
- `backend/app/domains/baseball/controller/schemas.py`
- `backend/app/domains/baseball/service/dto.py`
- `backend/app/domains/baseball/service/services.py`
- `backend/app/domains/baseball/domain/entities.py`
- `backend/app/domains/baseball/domain/enums.py`
- `backend/app/domains/baseball/domain/repositories.py`
- `backend/app/domains/baseball/infrastructure/models.py`
- `backend/app/domains/baseball/infrastructure/mappers.py`
- `backend/app/domains/baseball/infrastructure/repositories.py`

따라갈 흐름:

```text
GET /api/v1/games
-> list_kbo_games()
-> ListKboGamesQuery
-> ListKboGamesService.execute()
-> SqlAlchemyKboGameRepository.list_games()
-> KboGameModel
-> KboGameMapper.to_domain()
-> KboGameResultDto
-> KboGameResponse
```

### Step 3. 인증과 사용자 context

인증은 Supabase Auth와 backend cookie session이 섞여 있어 Step 2보다 어렵다.

읽을 파일:

- `backend/app/domains/auth/controller/router.py`
- `backend/app/domains/auth/controller/schemas.py`
- `backend/app/domains/auth/service/services.py`
- `backend/app/domains/auth/service/dto.py`
- `backend/app/domains/auth/infrastructure/supabase_auth_client.py`
- `backend/app/domains/auth/infrastructure/repositories.py`
- `backend/app/api/dependencies.py`의 `get_current_auth_user()`

확인할 질문:

- Google OAuth 시작과 callback은 어떤 endpoint가 담당하는가?
- access token과 refresh token은 어디에 저장되는가?
- `/auth/me`는 어떤 service를 통해 현재 사용자를 찾는가?
- `get_current_auth_user()`는 왜 공통 dependency로 분리되어 있는가?

### Step 4. 대화방과 메시지 저장

대화 목록/메시지 목록은 권한 확인과 repository 패턴을 배우기 좋다.

읽을 파일:

- `backend/app/domains/conversation/controller/router.py`
- `backend/app/domains/conversation/controller/schemas.py`
- `backend/app/domains/conversation/service/dto.py`
- `backend/app/domains/conversation/service/services.py`
- `backend/app/domains/conversation/domain/entities.py`
- `backend/app/domains/conversation/domain/enums.py`
- `backend/app/domains/conversation/domain/exceptions.py`
- `backend/app/domains/conversation/infrastructure/models.py`
- `backend/app/domains/conversation/infrastructure/mappers.py`
- `backend/app/domains/conversation/infrastructure/repositories.py`

확인할 질문:

- 대화방 목록은 어떤 사용자 기준으로 필터링되는가?
- 대화방 메시지를 읽기 전에 소유권을 어떻게 확인하는가?
- domain exception은 controller에서 어떤 HTTP status로 바뀌는가?

### Step 5. 채팅 스트리밍과 Agent

이 프로젝트의 핵심이다. 다만 한 번에 모두 이해하려고 하면 어렵기 때문에 event 흐름부터 본다.

읽을 파일:

- `backend/app/domains/chat/controller/router.py`
- `backend/app/domains/chat/controller/schemas.py`
- `backend/app/domains/chat/service/sse.py`
- `backend/app/domains/chat/service/services.py`
- `backend/app/agent/graph.py`
- `backend/app/agent/state.py`
- `backend/app/agent/routing_service.py`
- `backend/app/agent/routing_schemas.py`
- `backend/app/agent/tool_registry.py`
- `backend/app/agent/tool_executor.py`
- `backend/app/agent/answering.py`

따라갈 흐름:

```text
POST /api/v1/chat
-> StreamingResponse
-> ChatStreamService.stream()
-> user message 저장
-> assistant placeholder 저장
-> BaseballAgentGraph.astream()
-> route
-> prepare_tool
-> tool_execute
-> state_update
-> answer_generate
-> assistant.delta / assistant.completed / done SSE event
```

### Step 6. Baseball tool과 RAG

Agent가 선택한 tool이 실제 데이터를 어떻게 가져오는지 본다.

읽을 폴더:

- `backend/app/domains/baseball/tool/find_kbo_game/`
- `backend/app/domains/baseball/tool/get_stadium_info/`
- `backend/app/domains/baseball/tool/get_weather_context/`
- `backend/app/domains/baseball/tool/search_stadium_guide/`
- `backend/app/domains/baseball/tool/search_ticketing_guide/`
- `backend/app/domains/baseball/tool/search_baseball_knowledge/`
- `backend/app/domains/baseball/tool/rag_config.py`

확인할 질문:

- 각 tool의 `schemas.py`는 routing args와 어떤 차이가 있는가?
- `handler.py`는 service/retriever/client 중 무엇을 호출하는가?
- RAG tool은 embedding query와 pgvector 검색을 어디에서 수행하는가?
- weather tool은 외부 KMA API 호출 실패를 어떻게 결과에 반영하는가?

### Step 7. scripts와 tests

마지막으로 운영성 작업과 검증 코드를 본다.

읽을 폴더:

- `backend/scripts/`
- `backend/scripts/kbo_schedule_import/`
- `backend/scripts/baseball_knowledge/`
- `backend/tests/api/`

확인할 질문:

- API 서버 코드와 batch script 코드는 어떤 경계를 갖는가?
- `pytest` 테스트에서 service나 LLM chain을 어떻게 fake/mock 처리하는가?
- routing prompt나 SSE contract처럼 깨지면 안 되는 계약은 어떤 테스트로 보호되는가?

## 4. 하루 단위 학습 계획

### Day 1. FastAPI와 계층 구조

- `main.py`, `api/router.py`, `api/v1/router.py` 읽기
- `core/config.py`, `core/database.py` 읽기
- `GET /games` 흐름을 controller부터 repository까지 따라가기

목표:

- `APIRouter`, `Depends`, `Annotated`, `async def`, Pydantic schema의 역할을 설명할 수 있다.

### Day 2. DB와 domain model

- `baseball/infrastructure/models.py`에서 SQLAlchemy 문법 보기
- `baseball/infrastructure/repositories.py`에서 `select(...)`, `where(...)`, `session.execute(...)` 보기
- `baseball/domain/entities.py`와 `service/dto.py`의 `dataclass` 비교하기

목표:

- ORM model, domain entity, response schema를 구분할 수 있다.

### Day 3. Auth와 conversation

- `auth` router/service 읽기
- `get_current_auth_user()` dependency 읽기
- `conversation` service에서 소유권 확인 흐름 읽기

목표:

- 인증된 사용자 context가 endpoint/service로 전달되는 흐름을 설명할 수 있다.

### Day 4. Chat stream

- `chat/controller/router.py`의 `StreamingResponse` 읽기
- `chat/service/sse.py`와 `chat/controller/schemas.py`에서 SSE event 형식 보기
- `ChatStreamService._stream_inner()`를 위에서 아래로 읽기

목표:

- 하나의 사용자 메시지가 DB 저장, agent 실행, stream event로 이어지는 흐름을 설명할 수 있다.

### Day 5. Agent와 tool

- `agent/graph.py`에서 LangGraph node/edge 읽기
- `routing_service.py`에서 LangChain structured output 읽기
- `tool_registry.py`, `tool_executor.py`에서 tool dispatch 구조 읽기
- baseball tool 중 하나를 골라 `handler.py`부터 결과 schema까지 따라가기

목표:

- LLM이 직접 모든 일을 하는 것이 아니라 routing decision을 만들고 backend tool이 실행된다는 구조를 설명할 수 있다.

## 5. 읽을 때 주의할 점

- `__pycache__`, `.venv`, `.pytest_cache`, `.ruff_cache`, `logs/api-responses`는 학습 대상에서 제외해도 된다.
- `.env`는 실제 secret이 있을 수 있으므로 내용을 복사하거나 문서화하지 않는다.
- DB migration, seed, reset 같은 작업은 이 저장소 규칙상 사용자 확인 후 실행한다.
- 처음에는 모든 타입 문법을 완벽히 이해하려고 하지 말고, 요청 흐름을 먼저 잡는다.
