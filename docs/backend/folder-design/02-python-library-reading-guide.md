# Python 문법과 라이브러리 읽기 가이드

> 대상: `backend/`를 읽을 때 자주 만나는 Python 문법과 라이브러리  
> 목적: 코드를 읽다가 막히는 지점을 줄이는 것

## 1. 프로젝트 의존성 한눈에 보기

`backend/pyproject.toml` 기준 주요 dependency는 다음과 같다.

| 라이브러리 | 이 프로젝트에서의 역할 |
|---|---|
| `fastapi` | HTTP API framework |
| `uvicorn[standard]` | FastAPI app을 실행하는 ASGI server |
| `pydantic-settings` | `.env`와 환경변수를 typed settings 객체로 로드 |
| `sqlalchemy[asyncio]` | PostgreSQL async ORM/query |
| `asyncpg` | SQLAlchemy가 사용하는 PostgreSQL async driver |
| `httpx` | async HTTP client. Supabase/KMA 같은 외부 API 호출에 사용 |
| `openai` | OpenAI API client |
| `langchain` | LLM prompt/chain 구성 |
| `langchain-openai` | LangChain에서 OpenAI chat model 사용 |
| `langgraph` | Agent workflow graph 구성 |
| `pdfplumber` | 야구 규칙 PDF 등 문서 처리 script에서 사용 |
| `pytest` | 테스트 runner |
| `pytest-asyncio` | async 테스트 지원 |
| `ruff` | lint/format 검사 |
| `mypy` | 정적 타입 검사 |

## 2. Python 파일과 package 기본

Python에서 폴더가 package처럼 import되려면 보통 `__init__.py`가 있다.

예:

```text
app/domains/baseball/service/services.py
```

이 파일은 코드에서 이렇게 import된다.

```python
from app.domains.baseball.service.services import ListKboGamesService
```

읽는 법:

- `app`은 `backend/app` 폴더다.
- `domains.baseball.service`는 하위 폴더 경로다.
- 마지막 `services`는 `services.py` 파일이다.
- `ListKboGamesService`는 그 파일 안의 class다.

## 3. 타입 힌트 읽기

### `str | None`

```python
team_id: str | None
```

문자열이거나 `None`일 수 있다는 뜻이다. TypeScript의 `string | null`과 비슷하다.

### `list[KboGameResultDto]`

```python
async def execute(...) -> list[KboGameResultDto]:
```

`KboGameResultDto` 객체들의 list를 반환한다는 뜻이다.

### `Annotated[..., Depends(...)]`

```python
ListKboGamesServiceDependency = Annotated[
    ListKboGamesService,
    Depends(get_list_kbo_games_service),
]
```

FastAPI dependency injection 문법이다.

뜻:

- endpoint parameter 타입은 `ListKboGamesService`
- 실제 값은 `get_list_kbo_games_service()`를 호출해 만든다
- 그 함수가 필요로 하는 다른 dependency도 FastAPI가 이어서 해결한다

### `Literal[...]`

```python
KboTeamId = Literal["LG", "DOOSAN", "KIWOOM"]
```

정해진 문자열 값만 허용한다. TypeScript string literal union과 비슷하다.

### `Self`

```python
@classmethod
def from_entity(cls, game: KboGame) -> Self:
```

현재 class 자신을 반환한다는 타입 힌트다.

## 4. `async` / `await`

이 백엔드는 DB, HTTP, LLM 호출이 대부분 async다.

```python
async def list_kbo_games(...):
    results = await service.execute(query)
```

읽는 법:

- `async def`: 비동기 함수
- `await`: 비동기 작업이 끝날 때까지 기다린다
- DB query, HTTP call, OpenAI call, stream generator에서 자주 나온다

주의:

- `async def` 안에서 async 함수를 호출할 때는 보통 `await`가 필요하다.
- `await`를 빠뜨리면 실제 결과가 아니라 coroutine 객체가 남는다.

## 5. `dataclass`

도메인 entity와 service DTO에서 자주 보인다.

```python
@dataclass(frozen=True, slots=True)
class KboGame:
    id: UUID
    game_date: date
```

의미:

- 생성자와 필드 저장 코드를 자동으로 만든다.
- `frozen=True`는 생성 후 값을 바꾸지 못하게 한다.
- `slots=True`는 객체를 더 가볍게 만들고 임의 속성 추가를 막는다.

이 프로젝트에서는 순수 domain object나 내부 DTO에 많이 쓴다.

## 6. Pydantic `BaseModel`

API schema, LLM structured output, tool input/output에서 자주 보인다.

```python
class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1)
```

역할:

- 입력값 validation
- JSON serialization/deserialization
- OpenAPI schema 생성
- LLM structured output schema로 사용

자주 보는 메서드:

| 메서드 | 역할 |
|---|---|
| `model_validate(value)` | dict 또는 다른 객체를 Pydantic model로 검증/변환 |
| `model_dump()` | Python dict로 변환 |
| `model_dump_json()` | JSON string으로 변환 |

## 7. Pydantic `Field`

```python
query: str = Field(min_length=1)
top_k: int = Field(default=5, ge=1, le=10)
```

필드 validation rule과 설명을 붙인다.

주요 옵션:

- `default`: 기본값
- `min_length`: 문자열 최소 길이
- `ge`: greater than or equal
- `le`: less than or equal
- `description`: schema 설명. LLM structured output에서도 중요하다.

## 8. Pydantic validator

```python
@model_validator(mode="after")
def validate_date_shape(self) -> FindKboGameRoutingArgs:
    ...
    return self
```

필드 하나가 아니라 여러 필드 조합을 검증한다.

예:

- `date`와 `date_from/date_to`를 동시에 쓰면 안 된다.
- `date_from`이 `date_to`보다 늦으면 안 된다.
- `stadium_id`와 `team_id` 중 하나는 있어야 한다.

## 9. FastAPI 핵심 문법

### `APIRouter`

```python
router = APIRouter(
    prefix="/games",
    tags=["Games"],
)
```

이 router에 정의한 endpoint 앞에 `/games`가 붙는다.

`app/api/v1/router.py`에서 이 router가 `/api/v1` 아래에 붙으므로 최종 경로는 다음과 같다.

```text
/api/v1/games
```

### Endpoint decorator

```python
@router.get("", response_model=list[KboGameResponse])
async def list_kbo_games(...):
```

HTTP GET endpoint를 정의한다.

### `Query`

```python
team_id: Annotated[str | None, Query(min_length=1)] = None
date_: Annotated[date | None, Query(alias="date")] = None
```

query parameter validation과 alias를 정의한다.

`date_`처럼 변수명 뒤에 underscore가 붙는 이유는 Python built-in이나 import 이름과 충돌을 피하기 위해서다. 외부 API에서는 `alias="date"` 덕분에 `?date=2026-08-24`로 받는다.

### `HTTPException`

```python
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail=str(exc),
)
```

FastAPI에서 특정 HTTP error response를 즉시 반환할 때 사용한다.

## 10. SQLAlchemy async ORM

### ORM model

```python
class KboGameModel(Base):
    __tablename__ = "kbo_games"
    id: Mapped[UUID] = mapped_column(...)
```

DB table과 Python class를 연결한다.

읽는 법:

- `__tablename__`: table 이름
- `__table_args__`: schema 등 table 옵션
- `Mapped[T]`: column이 Python에서 어떤 타입으로 보이는지
- `mapped_column(...)`: DB column 설정

### Query

```python
statement = select(KboGameModel)
statement = statement.where(KboGameModel.game_date >= date_from)
result = await self._session.execute(statement)
models = result.scalars().all()
```

뜻:

- `select(KboGameModel)`: `select * from kbo_games`에 가까운 query 시작
- `where(...)`: 조건 추가
- `await session.execute(statement)`: DB 실행
- `scalars().all()`: ORM model list 꺼내기

### Transaction

```python
await self._session.commit()
await self._session.rollback()
```

DB 변경을 확정하거나 되돌린다.

이 프로젝트에서는 조회 service보다 생성/수정 service와 chat stream service에서 transaction 처리가 중요하다.

## 11. `httpx`

외부 HTTP API를 async로 호출할 때 쓴다.

주로 볼 위치:

- `auth/infrastructure/supabase_auth_client.py`
- `baseball/tool/get_weather_context/kma_client.py`

읽을 때 확인할 것:

- client timeout이 있는가?
- status code 실패를 어떻게 처리하는가?
- 외부 응답 dict를 내부 DTO/schema로 어떻게 바꾸는가?

## 12. LangChain

`agent/routing_service.py`에서 사용한다.

핵심 코드 흐름:

```python
prompt = ChatPromptTemplate.from_messages(...)
chat_model = ChatOpenAI(...)
chain = prompt | chat_model.with_structured_output(...)
response = await chain.ainvoke(...)
```

읽는 법:

- prompt template에 system/human message를 넣는다.
- `ChatOpenAI`가 실제 OpenAI chat model 호출 객체다.
- `with_structured_output(ToolRoutingDecision, ...)`는 모델 응답을 Pydantic schema에 맞게 받겠다는 뜻이다.
- `prompt | model`은 LangChain의 pipe composition 문법이다.

## 13. LangGraph

`agent/graph.py`에서 사용한다.

이 프로젝트의 graph node:

```text
route
prepare_tool
tool_execute
state_update
answer_generate
```

edge:

```text
START -> route
route -> prepare_tool 또는 answer_generate
prepare_tool -> tool_execute
tool_execute -> state_update
state_update -> answer_generate
answer_generate -> END
```

읽는 법:

- node는 async method다.
- 각 node는 state 일부를 dict로 반환한다.
- LangGraph가 반환 dict를 기존 state에 합친다.
- `astream(..., stream_mode="updates")`는 node별 update를 streaming한다.

## 14. SSE

채팅 endpoint는 JSON 하나를 반환하지 않고 Server-Sent Events를 흘려보낸다.

```python
return StreamingResponse(
    service.stream(...),
    media_type="text/event-stream",
)
```

SSE payload는 대략 다음 형태다.

```text
event: assistant.delta
data: {"message_id": "...", "delta": "..."}
```

관련 파일:

- `domains/chat/service/sse.py`
- `domains/chat/controller/schemas.py`
- `domains/chat/service/services.py`

## 15. pytest

테스트는 `backend/tests/api/`에 있다.

자주 볼 패턴:

- async test
- fake service/fake chain
- FastAPI test client
- Pydantic model validation
- SSE event contract 검증

실행 명령은 `docs/backend/local-development-commands.md`를 따른다. DB나 migration이 필요한 명령은 저장소 규칙상 실행 전에 사용자 확인이 필요하다.

## 16. 읽다가 자주 헷갈리는 이름 구분

| 이름 | 의미 |
|---|---|
| `schema` | 주로 HTTP request/response 또는 tool input/output의 Pydantic 모델 |
| `dto` | service 계층의 내부 입출력 데이터 |
| `entity` | domain 계층의 순수 객체 |
| `model` | 보통 SQLAlchemy ORM table model |
| `repository` | 저장소 접근 추상화 또는 구현체 |
| `handler` | agent tool 하나를 실행하는 객체 |
| `service` | use case 실행 객체 |
| `router` | HTTP endpoint 묶음 |
| `dependency` | FastAPI가 endpoint 호출 전에 만들어 주는 객체 |

