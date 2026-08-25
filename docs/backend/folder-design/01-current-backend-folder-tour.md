# 현재 Backend 폴더별 역할

> 라벨: `REFERENCE`  
> 대상: `backend/`의 현재 구현  
> 전제: 기존 `folder-design.md`는 설계 원칙 문서이고, 이 문서는 지금 코드 읽기용 지도다.

## 1. 최상위 구조

```text
backend/
├── app/
├── scripts/
├── tests/
├── logs/
├── pyproject.toml
├── uv.lock
├── requirements.txt
├── requirements-dev.txt
├── .env
└── .env.example
```

| 경로 | 역할 |
|---|---|
| `app/` | FastAPI 애플리케이션 본체 |
| `scripts/` | 데이터 import, chunk 생성, embedding, 평가용 실행 스크립트 |
| `tests/` | pytest 기반 API/service/agent 테스트 |
| `logs/api-responses/` | 로컬 API 응답 로깅 결과. 학습 시 세부 내용은 보통 보지 않아도 된다. |
| `pyproject.toml` | Python 프로젝트 메타데이터와 의존성 정의 |
| `uv.lock` | uv가 고정한 dependency lock file |
| `requirements*.txt` | 기존 pip 호환 의존성 파일 |
| `.env.example` | 공유 가능한 환경변수 예시 |
| `.env` | 로컬 secret 포함 가능. 문서화하거나 커밋하지 않는다. |

## 2. `app/` 개요

```text
backend/app/
├── main.py
├── api/
├── core/
├── domains/
├── agent/
└── shared/
```

| 경로 | 역할 |
|---|---|
| `main.py` | FastAPI app 생성, middleware 등록, root router 연결, health endpoint 정의 |
| `api/` | API version router와 요청 단위 dependency 조립 |
| `core/` | 환경변수, DB engine/session, LLM client, logging, middleware 같은 공통 인프라 |
| `domains/` | auth/baseball/chat/conversation 등 도메인별 기능 구현 |
| `agent/` | LLM routing, LangGraph workflow, tool registry/executor, 답변 생성 |
| `shared/` | 여러 도메인에서 공유할 코드 자리. 현재는 비어 있는 패키지에 가깝다. |

## 3. `app/main.py`

`main.py`는 서버 bootstrap이다.

주요 책임:

- `configure_logging()`으로 logging 설정
- `get_settings()`로 환경변수 로드
- `FastAPI(...)` app 생성
- CORS middleware 등록
- API response logging middleware 등록
- `api_router` 연결
- `/health`, `/health/db` endpoint 제공

중요한 흐름:

```text
app = FastAPI(...)
app.add_middleware(...)
app.include_router(api_router)
```

`/health/db`는 `Depends(get_db_session)`으로 DB session을 받고 `select 1`에 해당하는 `text("select 1")`을 실행한다.

## 4. `app/api/`

```text
app/api/
├── router.py
├── dependencies.py
└── v1/
    └── router.py
```

### `router.py`

전체 API prefix를 만든다.

```text
api_router
-> v1_router를 /api/v1 아래에 include
```

### `v1/router.py`

도메인별 router를 하나로 합친다.

현재 포함된 router:

- `auth_router`
- `chat_router`
- `baseball_router`
- `conversation_router`

### `dependencies.py`

이 프로젝트에서 매우 중요한 파일이다. FastAPI의 `Depends`로 사용할 service/handler 조립 함수들이 모여 있다.

예:

```text
get_list_kbo_games_service(session)
-> SqlAlchemyKboGameRepository(session)
-> ListKboGamesService(repository)
```

Node.js 관점으로 보면 요청 단위 factory 또는 가벼운 DI container에 가깝다.

주의할 점:

- service는 직접 DB session을 만들지 않는다.
- router는 repository를 직접 만들지 않는다.
- `dependencies.py`가 현재 구현체 선택을 담당한다.
- 테스트에서는 이 dependency 또는 service 내부 dependency를 대체하기 쉽다.

## 5. `app/core/`

```text
app/core/
├── api_response_logging.py
├── config.py
├── database.py
├── llm.py
└── logging.py
```

| 파일 | 역할 |
|---|---|
| `config.py` | `.env`를 `Settings` 객체로 읽는다. `pydantic-settings` 사용. |
| `database.py` | SQLAlchemy async engine, session factory, `get_db_session()` 정의 |
| `llm.py` | OpenAI client 생성 |
| `logging.py` | Python logging 기본 설정 |
| `api_response_logging.py` | 로컬 API 응답을 파일로 남기는 middleware |

### `config.py`

`Settings(BaseSettings)` 클래스의 필드명이 환경변수 이름과 연결된다.

예:

```python
database_url: str
openai_api_key: str
openai_model: str = "gpt-5-mini"
```

`.env`에 `DATABASE_URL=...`이 있으면 `settings.database_url`로 읽힌다. `case_sensitive=False`라서 대소문자 차이는 허용된다.

`get_settings()`에는 `@lru_cache`가 붙어 있어 한 번 만든 settings 객체를 재사용한다.

### `database.py`

비동기 DB 접근의 중심이다.

핵심 객체:

- `Base`: 모든 ORM model이 상속하는 공통 base
- `engine`: DB 연결 pool을 관리하는 SQLAlchemy async engine
- `async_session_factory`: 요청마다 `AsyncSession`을 만드는 factory
- `get_db_session()`: FastAPI dependency로 쓰는 async generator

## 6. `app/domains/`

```text
app/domains/
├── auth/
├── baseball/
├── chat/
└── conversation/
```

도메인 폴더는 기능의 책임 경계다. 같은 기술을 쓰더라도 도메인이 다르면 폴더를 나눈다.

공통 패턴:

```text
domain-name/
├── controller/
├── service/
├── domain/
└── infrastructure/
```

단, `chat`은 현재 별도 `domain/`, `infrastructure/` 없이 streaming use case 중심으로 구성되어 있다. `baseball`에는 agent가 실행할 `tool/` 폴더가 추가로 있다.

## 7. `domains/baseball/`

```text
baseball/
├── controller/
├── service/
├── domain/
├── infrastructure/
└── tool/
```

### `controller/`

HTTP endpoint와 API schema.

현재 주요 endpoint:

```text
GET /api/v1/games
```

역할:

- query parameter를 받는다.
- Pydantic/FastAPI 검증을 적용한다.
- service DTO로 변환한다.
- service 결과를 response schema로 바꾼다.

### `service/`

사용자 유스케이스.

현재 대표 service:

- `ListKboGamesService`

역할:

- 입력 query를 받아 repository 호출
- logging
- domain entity를 service result DTO로 변환

### `domain/`

순수한 야구 도메인 타입.

대표 파일:

- `entities.py`: `KboGame` dataclass
- `enums.py`: `KboGameStatus`
- `repositories.py`: repository 추상 타입

원칙:

- FastAPI를 import하지 않는다.
- SQLAlchemy를 import하지 않는다.
- OpenAI/LangChain을 import하지 않는다.

### `infrastructure/`

DB 구현 세부사항.

대표 파일:

- `models.py`: SQLAlchemy ORM model
- `repositories.py`: SQLAlchemy query 구현
- `mappers.py`: ORM model과 domain entity 변환

### `tool/`

Agent가 호출할 backend tool 구현.

현재 tool:

- `find_kbo_game`
- `get_stadium_info`
- `get_weather_context`
- `search_stadium_guide`
- `search_ticketing_guide`
- `search_baseball_knowledge`

각 tool은 보통 다음 구조를 가진다.

```text
tool-name/
├── handler.py
└── schemas.py
```

RAG tool은 `retriever.py`가 추가된다. 외부 API tool은 client 파일이 추가될 수 있다.

## 8. `domains/auth/`

```text
auth/
├── controller/
├── service/
├── domain/
└── infrastructure/
```

역할:

- Google OAuth 시작
- Supabase OAuth callback 처리
- HttpOnly cookie 기반 session 관리
- 현재 사용자 조회
- profile update

주요 endpoint:

- `GET /api/v1/auth/google`
- `GET /api/v1/auth/callback`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `PATCH /api/v1/auth/me`

읽을 때 핵심:

- router는 cookie를 읽고 쓴다.
- service는 Supabase Auth client와 user profile repository를 사용한다.
- infrastructure는 Supabase HTTP 호출과 DB profile 조회/저장을 담당한다.

## 9. `domains/conversation/`

```text
conversation/
├── controller/
├── service/
├── domain/
└── infrastructure/
```

역할:

- 대화방 생성
- 로그인 사용자의 대화방 목록 조회
- 대화방 메시지 목록 조회
- 대화방 소유권 확인

주요 endpoint:

- `GET /api/v1/conversations`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}/messages`

읽을 때 핵심:

- `current_user.id`가 `user_profile_id`로 전달된다.
- 메시지 목록 조회 전에 대화방 소유권을 확인한다.
- `ConversationNotFoundError`, `ConversationAccessDeniedError`가 HTTP 404/403으로 바뀐다.

## 10. `domains/chat/`

```text
chat/
├── controller/
└── service/
```

역할:

- 사용자 메시지 한 턴을 처리한다.
- 대화방과 메시지를 DB에 저장한다.
- Agent graph를 실행한다.
- tool 실행 상태와 assistant 답변을 SSE로 streaming한다.

주요 endpoint:

```text
POST /api/v1/chat
```

핵심 파일:

- `controller/router.py`: `StreamingResponse` 반환
- `controller/schemas.py`: SSE event payload 모델
- `service/sse.py`: SSE 문자열 encoding
- `service/services.py`: chat turn orchestration

## 11. `app/agent/`

```text
agent/
├── answering.py
├── graph.py
├── prompts.py
├── routing_schemas.py
├── routing_service.py
├── state.py
├── tool_cards.py
├── tool_executor.py
├── tool_registry.py
└── prompt_assets/
```

역할:

- 사용자 질문이 어떤 tool을 필요로 하는지 판단한다.
- LangGraph로 한 턴 workflow를 실행한다.
- routing 결과를 실제 backend tool handler 호출로 변환한다.
- tool 결과를 assistant 답변으로 변환한다.
- 이전 turn에서 선택된 경기/구장 context를 관리한다.

핵심 흐름:

```text
routing_service.py
-> ToolRoutingDecision
-> graph.py
-> tool_executor.py
-> baseball/tool/*/handler.py
-> answering.py
```

`prompt_assets/`는 routing prompt 정책과 few-shot 예시를 담는다.

## 12. `scripts/`

```text
scripts/
├── import_kbo_schedule.py
├── kbo_schedule_import/
├── generate_stadium_guide_chunks.py
├── embed_stadium_guide_chunks.py
├── evaluate_stadium_guide_retrieval.py
├── evaluate_search_stadium_guide_tool.py
├── evaluate_tool_routing.py
└── baseball_knowledge/
```

역할:

- KBO schedule import
- stadium guide chunk 생성
- baseball knowledge PDF page 추출/chunk 생성
- embedding 저장
- RAG/tool routing 평가

주의:

- API 요청 처리 코드가 아니다.
- DB import/embedding 작업은 데이터 상태를 바꿀 수 있으므로 실행 전 확인이 필요하다.
- 학습할 때는 먼저 파일 구조와 DTO/service/repository 분리를 읽는 정도로 충분하다.

## 13. `tests/`

```text
tests/
└── api/
```

현재 테스트는 `tests/api/`에 모여 있다.

대표 테스트 주제:

- auth redirect/profile update
- chat stream contract
- chat owner authorization
- conversation list
- tool registry
- tool routing service
- RAG retrieval config
- weather/ticketing tool
- API response logging

읽을 때 핵심:

- 외부 API나 LLM을 실제 호출하지 않도록 fake/mock을 어떻게 넣는지 본다.
- SSE event 이름과 payload contract가 어떻게 검증되는지 본다.
- domain/service 계층이 깨졌을 때 어떤 테스트가 실패할지 상상해본다.
