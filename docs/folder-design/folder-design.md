# New Baseball Agent 폴더 구조 설계

> 상태: 확정  
> 구조 원칙: 모노레포 + 도메인 중심 패키지 + Controller/Service/Domain/Infrastructure 계층 분리

## 1. 설계 목적

이 프로젝트는 Python과 FastAPI를 학습하면서 KBO 직관 가이드 AI Agent 서비스를 구축하는 모노레포다.

백엔드는 스프링 프로젝트에서 익숙한 Controller, Service, Domain, Infrastructure 역할을 FastAPI에 맞게 적용한다. 단, 자바·스프링의 구조를 그대로 복제하지 않고 Python의 작은 모듈과 명시적 의존성 주입을 활용한다.

핵심 목표는 다음과 같다.

- HTTP, 유스케이스, 도메인 규칙, 저장 기술의 책임을 분리한다.
- 도메인 규칙이 FastAPI, SQLAlchemy, Supabase, LangChain에 의존하지 않게 한다.
- 기능이 늘어날 때 기술별 폴더가 아니라 도메인별로 확장한다.
- 처음부터 모든 빈 폴더를 만들지 않고 개발 단계에 맞춰 추가한다.
- Supabase PostgreSQL과 pgvector의 구현 세부사항을 Infrastructure 계층에 격리한다.
- Agent는 여러 도메인을 조율하므로 개별 도메인 밖에 둔다.

## 2. 최상위 모노레포 구조

프로젝트 디렉터리 이름은 `new-baseball-agent`를 기준으로 설명한다. 현재 작업공간의 실제 디렉터리명이 다르다면 내부 구조만 동일하게 적용한다.

```text
new-baseball-agent/
├── backend/
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── data/
│   ├── raw/
│   ├── normalized/
│   └── fixtures/
├── scripts/
├── docs/
│   ├── adr/
│   ├── architecture/
│   ├── evaluation/
│   └── learning/
├── .github/
│   └── workflows/
│       └── backend-ci.yml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

프론트엔드 개발 단계가 시작되면 루트에 추가한다.

```text
new-baseball-agent/
├── frontend/
├── backend/
├── supabase/
├── data/
├── scripts/
└── docs/
```

### 2.1 루트 디렉터리 책임

| 경로 | 책임 |
|---|---|
| `backend/` | FastAPI 애플리케이션과 백엔드 테스트 |
| `frontend/` | 추후 추가할 웹 클라이언트 |
| `supabase/` | PostgreSQL schema migration, RLS, SQL 함수, seed |
| `data/raw/` | 수정하지 않는 원본 수집 데이터 |
| `data/normalized/` | 애플리케이션 schema에 맞게 정규화한 데이터 |
| `data/fixtures/` | 로컬 개발과 테스트용 소규모 고정 데이터 |
| `scripts/` | 수집, 정규화, import, embedding, 평가 작업 |
| `docs/adr/` | 중요한 기술 결정과 변경 이유 |
| `docs/architecture/` | 시스템·데이터·실행 흐름 설계 |
| `docs/evaluation/` | RAG 및 Agent 평가셋과 결과 |
| `docs/learning/` | 단계별 학습 기록 |
| `.github/workflows/` | lint, type check, test, build 자동화 |

## 3. 백엔드 최종 구조

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── dependencies.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   ├── error_handlers.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   └── security.py
│   ├── domains/
│   │   ├── __init__.py
│   │   ├── baseball/
│   │   │   ├── __init__.py
│   │   │   ├── controller/
│   │   │   ├── service/
│   │   │   ├── domain/
│   │   │   └── infrastructure/
│   │   ├── recommendation/
│   │   │   ├── __init__.py
│   │   │   ├── controller/
│   │   │   ├── service/
│   │   │   ├── domain/
│   │   │   └── infrastructure/
│   │   ├── knowledge/
│   │   │   ├── __init__.py
│   │   │   ├── controller/
│   │   │   ├── service/
│   │   │   ├── domain/
│   │   │   └── infrastructure/
│   │   └── conversation/
│   │       ├── __init__.py
│   │       ├── controller/
│   │       ├── service/
│   │       ├── domain/
│   │       └── infrastructure/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── intent_router.py
│   │   ├── state.py
│   │   ├── registry.py
│   │   ├── policies.py
│   │   └── tools/
│   └── shared/
│       ├── __init__.py
│       ├── schemas/
│       ├── protocols/
│       ├── types/
│       └── utils/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── api/
├── .env.example
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── README.md
```

`recommendation`, `knowledge`, `conversation`, `agent`는 해당 기능을 개발할 때 추가한다. 최초 프로젝트 설정 단계에서 빈 패키지로 미리 만들지 않는다.

## 4. 도메인 내부 표준 구조

`baseball` 도메인을 기준으로 모든 비즈니스 도메인은 다음 구조를 사용한다.

```text
domains/baseball/
├── __init__.py
├── controller/
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
├── service/
│   ├── __init__.py
│   ├── services.py
│   └── dto.py
├── domain/
│   ├── __init__.py
│   ├── entities.py
│   ├── repositories.py
│   ├── services.py
│   ├── policies.py
│   ├── enums.py
│   └── exceptions.py
└── infrastructure/
    ├── __init__.py
    ├── models.py
    ├── repositories.py
    └── mappers.py
```

파일이 지나치게 커지면 의미 단위로 나눈다. 예를 들어 `services.py`를 처음부터 여러 파일로 쪼개지 않고, 유스케이스가 충분히 늘었을 때 `find_games.py`, `get_game.py`처럼 분리한다.

## 5. 스프링 구조와의 대응

| FastAPI 구조 | 스프링 역할 | 책임 |
|---|---|---|
| `controller/router.py` | `@RestController` | Endpoint와 HTTP 흐름 |
| `controller/schemas.py` | Request/Response DTO | 외부 API 계약 |
| `service/services.py` | `@Service` | 사용자 유스케이스 |
| `service/dto.py` | Command, Query, Result DTO | 내부 유스케이스 계약 |
| `domain/entities.py` | Domain Entity | 핵심 상태와 불변 조건 |
| `domain/repositories.py` | Repository interface | 저장소 추상화 |
| `domain/services.py` | Domain Service | 단일 Entity에 속하지 않는 규칙 |
| `domain/policies.py` | Policy | 선택·판단·점수 계산 |
| `infrastructure/models.py` | JPA Entity | SQLAlchemy ORM Model |
| `infrastructure/repositories.py` | Repository 구현체 | PostgreSQL 조회·저장 |
| `infrastructure/mappers.py` | Entity Mapper | ORM과 Domain 변환 |

## 6. Controller 계층

```text
controller/
├── router.py
└── schemas.py
```

### 6.1 책임

- HTTP 요청 수신
- Pydantic 입력 검증
- HTTP Schema를 Service DTO로 변환
- 의존성이 주입된 Service 호출
- Service 결과를 Response Schema로 변환
- HTTP 상태 코드와 Header 결정

Controller에는 다음 로직을 넣지 않는다.

- SQL 실행
- 좌석 점수 계산
- 팀 이름 정규화
- 외부 API 직접 호출
- embedding 생성
- 복잡한 비즈니스 조건 처리

### 6.2 `router.py` 예시

```python
from fastapi import APIRouter, Depends

from .schemas import GameResponse, SearchGamesRequest

router = APIRouter()


@router.get("/games", response_model=list[GameResponse])
async def get_games(
    request: SearchGamesRequest = Depends(),
    service: "FindGamesService" = Depends(),
) -> list[GameResponse]:
    result = await service.execute(request.to_query())
    return [GameResponse.from_dto(item) for item in result]
```

실제 Service 의존성 생성은 `app/api/dependencies.py`에서 관리한다. Service 클래스 자체에 FastAPI `Depends`를 직접 넣지 않는다.

### 6.3 `schemas.py` 예시

```python
from datetime import date, datetime

from pydantic import BaseModel, Field


class SearchGamesRequest(BaseModel):
    game_date: date | None = None
    team_name: str | None = Field(default=None, min_length=1)


class GameResponse(BaseModel):
    id: str
    home_team_name: str
    away_team_name: str
    stadium_name: str
    starts_at: datetime
```

초기에는 `schemas.py` 하나로 시작한다. HTTP Schema가 많아지면 다음처럼 분리한다.

```text
controller/
├── router.py
├── requests.py
└── responses.py
```

## 7. Service 계층

```text
service/
├── services.py
└── dto.py
```

### 7.1 책임

Service는 하나의 사용자 요청을 끝까지 수행하는 유스케이스다.

```text
Service DTO
→ Domain Service 또는 Policy
→ Repository interface
→ 결과 DTO
```

Service가 담당할 수 있는 작업:

- 여러 Repository 조회 순서 조율
- 도메인 정책 호출
- transaction 경계 지정
- 외부 Provider 호출 순서 결정
- 다른 도메인의 공개 Service 호출
- 결과 DTO 조립

Service에는 HTTP Request/Response Schema와 FastAPI 객체를 전달하지 않는다.

### 7.2 `services.py` 예시

```python
class FindGamesService:
    def __init__(
        self,
        game_repository: "GameRepository",
        team_normalizer: "TeamNameNormalizer",
    ) -> None:
        self._game_repository = game_repository
        self._team_normalizer = team_normalizer

    async def execute(
        self,
        query: "SearchGamesQuery",
    ) -> list["GameResultDto"]:
        team_id = None

        if query.team_name:
            team_id = self._team_normalizer.normalize(query.team_name)

        games = await self._game_repository.find_games(
            game_date=query.game_date,
            team_id=team_id,
        )

        return [GameResultDto.from_entity(game) for game in games]
```

### 7.3 `dto.py` 예시

```python
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SearchGamesQuery:
    game_date: date | None
    team_name: str | None


@dataclass(frozen=True)
class GameResultDto:
    id: str
    home_team_id: str
    away_team_id: str
    stadium_id: str
    starts_at: datetime
```

두 계약은 분리한다.

```text
controller/schemas.py = 외부 HTTP 계약
service/dto.py        = 내부 유스케이스 계약
```

## 8. Domain 계층

```text
domain/
├── entities.py
├── repositories.py
├── services.py
├── policies.py
├── enums.py
└── exceptions.py
```

Domain은 핵심 비즈니스 개념과 규칙을 담당한다.

### 8.1 Entity

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Team:
    id: str
    name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Stadium:
    id: str
    name: str
    home_team_id: str
    is_dome: bool


@dataclass(frozen=True)
class Game:
    id: str
    home_team_id: str
    away_team_id: str
    stadium_id: str
    starts_at: datetime
```

### 8.2 Repository interface

```python
from datetime import date
from typing import Protocol


class GameRepository(Protocol):
    async def find_games(
        self,
        *,
        game_date: date | None = None,
        team_id: str | None = None,
        stadium_id: str | None = None,
    ) -> list["Game"]:
        ...

    async def find_by_id(self, game_id: str) -> "Game | None":
        ...
```

Repository interface에는 SQLAlchemy, SQL, Supabase Client 코드를 넣지 않는다.

### 8.3 Domain Service

단일 Entity에 자연스럽게 속하지 않는 도메인 규칙을 구현한다.

```python
class TeamNameNormalizer:
    def normalize(self, value: str) -> str:
        ...
```

### 8.4 Policy

명시적인 선택, 판단, 점수화 규칙을 구현한다.

```python
class GameSelectionPolicy:
    def select(self, games: list["Game"]) -> "Game":
        ...


class SeatScorePolicy:
    def calculate(
        self,
        seat: "SeatSection",
        preference: "UserPreference",
        weather: "WeatherContext",
    ) -> "SeatScore":
        ...
```

### 8.5 Enum과 예외

```python
from enum import StrEnum


class GameStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"
```

```python
class BaseballDomainError(Exception):
    pass


class GameNotFoundError(BaseballDomainError):
    pass


class UnsupportedTeamNameError(BaseballDomainError):
    pass
```

### 8.6 Domain에서 참조하지 않는 기술

- FastAPI
- HTTP Request/Response
- Pydantic API Schema
- SQLAlchemy
- Supabase
- Redis
- HTTPX
- OpenAI
- LangChain 또는 LangGraph

## 9. Infrastructure 계층

```text
infrastructure/
├── models.py
├── repositories.py
└── mappers.py
```

### 9.1 책임

- SQLAlchemy ORM Model
- Domain Repository interface 구현
- Supabase PostgreSQL 접근
- ORM Model과 Domain Entity 변환
- 외부 API Provider 구현
- pgvector Retriever 구현

### 9.2 SQLAlchemy Model 예시

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column


class GameModel(Base):
    __tablename__ = "games"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    home_team_id: Mapped[str]
    away_team_id: Mapped[str]
    stadium_id: Mapped[str]
    starts_at: Mapped[datetime]
```

### 9.3 Repository 구현 예시

```python
class SqlAlchemyGameRepository:
    def __init__(self, session: "AsyncSession") -> None:
        self._session = session

    async def find_games(
        self,
        *,
        game_date=None,
        team_id=None,
        stadium_id=None,
    ) -> list["Game"]:
        ...
```

### 9.4 Mapper 예시

```python
class GameMapper:
    @staticmethod
    def to_domain(model: GameModel) -> Game:
        return Game(
            id=str(model.id),
            home_team_id=model.home_team_id,
            away_team_id=model.away_team_id,
            stadium_id=model.stadium_id,
            starts_at=model.starts_at,
        )
```

데이터 흐름은 다음과 같다.

```text
Supabase PostgreSQL
→ SQLAlchemy Model
→ Mapper
→ Domain Entity
→ Service DTO
→ Response Schema
```

## 10. Core

```text
app/core/
├── config.py
├── database.py
├── exceptions.py
├── error_handlers.py
├── logging.py
├── middleware.py
└── security.py
```

스프링의 global/config 영역과 유사하나, 비즈니스 규칙은 포함하지 않는다.

| 파일 | 책임 |
|---|---|
| `config.py` | 환경변수와 Settings |
| `database.py` | SQLAlchemy Engine, AsyncSession, transaction 기반 |
| `exceptions.py` | 애플리케이션 공통 예외 |
| `error_handlers.py` | FastAPI Exception Handler |
| `logging.py` | 구조화 로그 설정 |
| `middleware.py` | Request ID, 요청 시간 측정 |
| `security.py` | 인증과 관리자 API 보호 |

도메인별 오류는 각 도메인의 `domain/exceptions.py`에 둔다. `core/exceptions.py`에는 설정 실패나 외부 시스템 공통 오류처럼 도메인에 속하지 않는 오류만 둔다.

## 11. Shared

```text
app/shared/
├── schemas/
├── protocols/
├── types/
└── utils/
```

스프링의 common 패키지와 비슷하지만 공통 코드 저장소처럼 사용하지 않는다.

허용 예:

- 공통 오류 응답
- 페이지네이션
- 범용 Protocol
- 공통 식별자 타입
- 비즈니스 의미가 없는 작은 유틸리티

금지 예:

- 좌석 점수 계산
- 팀 정규화
- 경기 선택 규칙
- RAG 검색 정책
- Agent 실행 정책

`shared`가 계속 커진다면 실제로 어느 도메인에 속해야 하는지 다시 검토한다.

## 12. 도메인별 책임

### 12.1 Baseball

`domains/baseball/`은 다음을 담당한다.

- 팀 정보
- 팀 별칭 정규화
- 구장 정보
- 경기 일정
- 날짜·팀·구장 기준 경기 검색
- 홈 팀·원정 팀 판별
- 경기 상태

초기에는 `Team`, `Stadium`, `Game`을 하나의 Baseball 도메인에 포함한다.

### 12.2 Recommendation

`domains/recommendation/`은 다음을 담당한다.

- 좌석 구역
- 좌석 가격
- 사용자 선호
- 날씨 적합성
- 좌석 점수
- 추천 순위와 추천 사유

핵심 점수 계산은 LLM이 아닌 `recommendation/domain/policies.py`의 결정론적 정책으로 구현한다.

### 12.3 Knowledge

`domains/knowledge/`는 RAG 단계에서 추가하며 다음을 담당한다.

- 원본 지식 문서
- 문서 청크
- 검색 조건과 검색 결과
- 출처, 신뢰 등급, 기준 시점
- embedding version
- Retriever interface

Supabase pgvector 관련 SQLAlchemy Model, 검색 SQL 함수 호출, Retriever 구현은 `knowledge/infrastructure/`에 둔다. 실제 table, pgvector extension, SQL 검색 함수, RLS migration은 루트 `supabase/migrations/`에서 관리한다.

### 12.4 Conversation

`domains/conversation/`은 대화 상태 개발 단계에서 추가하며 다음을 담당한다.

- Conversation과 Message
- 후보 경기와 선택 경기
- 사용자 선호 snapshot
- 세션 수명
- 대화 조회와 저장

Redis 또는 PostgreSQL 구현은 `conversation/infrastructure/`에 둔다.

## 13. Agent 위치와 책임

Agent는 Baseball, Recommendation, Knowledge, Conversation을 조율하므로 특정 비즈니스 도메인 내부에 넣지 않는다.

```text
app/agent/
├── orchestrator.py
├── intent_router.py
├── state.py
├── registry.py
├── policies.py
└── tools/
```

| 파일 | 책임 |
|---|---|
| `orchestrator.py` | plan, execute, observe, answer 흐름 |
| `intent_router.py` | 요청 intent와 필요한 기능 분류 |
| `state.py` | Agent 실행 상태 |
| `registry.py` | Tool 등록과 조회 |
| `policies.py` | 반복, timeout, 실패, 종료 정책 |
| `tools/` | 기존 Service를 Agent Tool 계약으로 감싸는 adapter |

Agent Tool 안에 도메인 로직을 다시 구현하지 않는다.

```text
Agent Tool
→ Domain Service
→ Domain Policy/Repository
```

## 14. API Router 연결

최상위 API Router는 도메인의 Controller Router를 조합한다.

```python
# app/api/v1/router.py

from fastapi import APIRouter

from app.domains.baseball.controller.router import router as baseball_router
from app.domains.recommendation.controller.router import (
    router as recommendation_router,
)

router = APIRouter()

router.include_router(
    baseball_router,
    prefix="/baseball",
    tags=["Baseball"],
)
router.include_router(
    recommendation_router,
    prefix="/recommendations",
    tags=["Recommendations"],
)
```

```python
# app/api/router.py

from fastapi import APIRouter

from app.api.v1.router import router as v1_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/api/v1")
```

```python
# app/main.py

from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(title="New Baseball Agent")
app.include_router(api_router)
```

## 15. 의존성 조립

FastAPI 의존성은 `app/api/dependencies.py`에서 조립한다.

```text
Request
→ AsyncSession
→ Repository 구현체
→ Domain Service/Policy
→ Application Service
→ Controller
```

예시:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


def get_find_games_service(
    session: AsyncSession = Depends(get_session),
) -> FindGamesService:
    repository = SqlAlchemyGameRepository(session)
    normalizer = TeamNameNormalizer()
    return FindGamesService(repository, normalizer)
```

규모가 커지기 전에는 별도의 DI container를 도입하지 않는다.

## 16. 의존성 방향

### 16.1 허용 방향

```text
Controller
    ↓
Service
    ↓
Domain

Infrastructure
    → Domain Repository/Provider interface
```

실제 요청 흐름:

```text
HTTP Request
→ Controller Schema
→ Controller
→ Service DTO
→ Service
→ Domain Policy
→ Repository interface
→ SQLAlchemy Repository
→ Supabase PostgreSQL
```

### 16.2 금지 방향

```text
Domain → FastAPI
Domain → Pydantic API Schema
Domain → SQLAlchemy
Domain → Supabase
Domain → Redis
Domain → OpenAI
Domain → LangChain
Domain → 다른 도메인의 Infrastructure
```

모듈 간 호출은 상대 도메인의 Service 계층을 통해 처리한다.

```text
허용:
recommendation/service → baseball/service

금지:
recommendation/domain → baseball/infrastructure/models.py
recommendation/infrastructure → baseball/infrastructure/repositories.py
```

도메인 간 직접 호출이 계속 증가하면 상위 orchestration Service 또는 Agent 계층으로 조합 책임을 올린다.

## 17. 테스트 구조

```text
backend/tests/
├── conftest.py
├── unit/
│   ├── baseball/
│   └── recommendation/
├── integration/
│   ├── repositories/
│   ├── providers/
│   └── pgvector/
├── contract/
│   ├── tools/
│   └── schemas/
└── api/
    ├── test_health.py
    ├── test_games.py
    └── test_recommendations.py
```

| 테스트 | 대상 | 외부 시스템 |
|---|---|---|
| Unit | Entity, Policy, Service | 사용하지 않음 |
| Integration | SQLAlchemy Repository, pgvector, Provider | local Supabase 또는 Fake server |
| Contract | Tool 및 Schema 계약 | 최소화 |
| API | Router, validation, error mapping | dependency override 사용 |

## 18. 지금 생성할 최소 구조

프로젝트 설정과 Baseball 도메인의 첫 기능을 구현할 때는 다음 구조만 만든다.

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── dependencies.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   └── error_handlers.py
│   ├── domains/
│   │   ├── __init__.py
│   │   └── baseball/
│   │       ├── __init__.py
│   │       ├── controller/
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   └── schemas.py
│   │       ├── service/
│   │       │   ├── __init__.py
│   │       │   ├── services.py
│   │       │   └── dto.py
│   │       ├── domain/
│   │       │   ├── __init__.py
│   │       │   ├── entities.py
│   │       │   ├── repositories.py
│   │       │   └── exceptions.py
│   │       └── infrastructure/
│   │           ├── __init__.py
│   │           ├── models.py
│   │           ├── repositories.py
│   │           └── mappers.py
│   └── shared/
│       └── __init__.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── api/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

최소 구조에는 다음을 아직 만들지 않는다.

- `recommendation/`
- `knowledge/`
- `conversation/`
- `agent/`
- 사용하지 않는 `shared` 하위 폴더
- 빈 `policies.py`, `services.py`, `enums.py`

필요해진 시점에 추가해 빈 구조와 불필요한 추상화를 피한다.

## 19. 단계별 디렉터리 확장

| 개발 단계 | 추가 경로 |
|---|---|
| 프로젝트 설정 | `backend/app/api`, `core`, `domains/baseball` |
| 좌석 추천 | `domains/recommendation` |
| Tool 계약과 Workflow | 각 도메인 Service 및 Tool adapter |
| LangChain Agent | `app/agent` |
| Supabase pgvector RAG | `domains/knowledge`, `supabase/migrations` |
| 대화 상태 | `domains/conversation` |
| 프론트엔드 | 루트 `frontend` |
| CI/CD | `.github/workflows` |

## 20. 최종 확정 요약

```text
Monorepo
├── backend
│   └── FastAPI
│       ├── api
│       ├── core
│       ├── domains
│       │   ├── baseball
│       │   │   ├── controller
│       │   │   ├── service
│       │   │   ├── domain
│       │   │   └── infrastructure
│       │   ├── recommendation
│       │   ├── knowledge
│       │   └── conversation
│       ├── agent
│       └── shared
├── supabase
├── data
├── scripts
├── docs
└── frontend
```

최종 의존성 원칙:

```text
Controller → Service → Domain
Infrastructure → Domain interface
Agent Tool → Service
Frontend → FastAPI
FastAPI Infrastructure → Supabase PostgreSQL/pgvector
```

이 구조를 프로젝트의 폴더 및 의존성 기준으로 사용한다. 구조를 변경해야 할 때는 먼저 `docs/adr/`에 변경 이유와 영향을 기록한다.
