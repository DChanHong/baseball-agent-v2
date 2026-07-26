# New Baseball Agent 리빌드 로드맵

> Python과 FastAPI를 기초부터 익히면서, 근거를 제시하는 RAG 기반 AI Agent 백엔드와 실제 사용 가능한 프론트엔드를 완성하는 포트폴리오 프로젝트

## 1. 이 문서의 목적

기존 `my-baseball-agent`의 기획, 구현 설계, Tool 계약, 데이터 생성 기준, Observability, 보안, Fine-tuning 자료를 분석해 새 프로젝트를 처음부터 다시 만드는 순서를 정의한다.

이번 리빌드는 기존 코드를 옮기는 작업이 아니다. 각 단계에서 Python과 FastAPI의 핵심 개념을 직접 구현하고, 일반 백엔드 기능 위에 RAG와 Agent를 한 층씩 추가한다. 최종 결과는 다음 질문에 코드와 문서로 답할 수 있어야 한다.

- 왜 이 문제에 일반 API, RAG, Agent를 각각 사용했는가?
- LLM이 없어도 동작해야 하는 결정론적 로직은 무엇인가?
- Agent가 어떤 근거와 Tool을 사용해 답했는가?
- 실패, 보안 공격, 잘못된 검색 결과를 어떻게 다루는가?
- 테스트와 평가로 개선을 어떻게 증명하는가?
- 사용자가 실제로 쓸 수 있는 화면과 배포 환경이 있는가?

## 2. 프로젝트 목표와 성공 기준

### 2.1 학습 목표

1. Python 문법, 타입 힌트, 예외 처리, 모듈화, 비동기 I/O를 실제 프로젝트에서 사용한다.
2. FastAPI의 라우팅, 의존성 주입, Pydantic 검증, 미들웨어, 예외 처리, OpenAPI, 테스트를 익힌다.
3. 데이터 수집·정규화·저장·조회 파이프라인을 만든다.
4. 검색 품질을 측정할 수 있는 RAG를 구현한다.
5. Tool 계약과 상태 전이를 갖춘 AI Agent를 구현한다.
6. 관측성, 평가, 보안, 배포까지 포함한 서비스 운영 흐름을 경험한다.
7. 프론트엔드에서 스트리밍 채팅과 Agent 실행 과정을 이해하기 쉽게 보여준다.

### 2.2 제품 목표

KBO 직관 초심자와 원정 팬이 한 대화 안에서 다음 정보를 얻도록 한다.

- 경기 일정 검색과 경기 선택
- 구장 기본 정보와 돔 여부 확인
- 날씨를 반영한 좌석 추천
- 응원 팀, 예산, 시야, 편의성에 따른 좌석 비교
- 공식 출처가 포함된 예매 안내
- 원정 이동 시 주의사항과 준비 가이드
- 정보가 부족하거나 오래된 경우 명확한 추가 질문과 한계 안내

### 2.3 MVP 완료 조건

- `POST /api/v1/chat`에서 단일·복합 요청을 처리한다.
- 일정 조회, 구장 조회, 날씨 조회, 지식 검색, 좌석 점수화 Tool이 분리되어 있다.
- 답변에 사용한 출처와 데이터 기준 시점을 표시한다.
- 같은 질문의 핵심 사실은 LLM 표현이 달라도 일관된다.
- 필수 입력 부족, 경기 없음, 외부 API 실패, 검색 결과 없음에 대한 fallback이 있다.
- 핵심 도메인 로직과 API에 자동 테스트가 있다.
- 요청별 Tool 순서, 지연 시간, 오류, 토큰 사용량을 추적할 수 있다.
- 웹 UI에서 대화, 출처, 추천 이유, 오류 상태를 확인할 수 있다.
- Docker 기반으로 로컬 실행할 수 있고 공개 데모 또는 배포 가이드가 있다.

## 3. 기존 프로젝트에서 가져갈 것과 바꿀 것

### 3.1 유지할 핵심 기획

- 일정처럼 정확한 구조화 데이터는 RAG가 아니라 정형 조회로 처리한다.
- 좌석, 예매, 동선 문서는 RAG로 근거를 검색한다.
- 좌석 순위 계산은 LLM의 감이 아니라 규칙 기반 점수화 Tool로 처리한다.
- Agent는 모든 일을 직접 하지 않고 필요한 Tool과 실행 순서를 선택한다.
- 날짜, 팀, 출발지 등 필수 정보가 없으면 추측하지 않고 되묻는다.
- 날씨 예보 범위 밖의 경기는 오류가 아니라 `preference_based` 정책으로 전환한다.
- Tool 실패, 반복 호출, 최대 실행 시간, 최대 단계 수에 종료 조건을 둔다.
- Observation과 출처를 남겨 답변 과정을 재현할 수 있게 한다.
- 입력 검증, 프롬프트 인젝션 방어, 로그 마스킹을 기능 개발과 함께 다룬다.

### 3.2 리빌드에서 개선할 구조

기존 구현은 학습용 MVP로는 유효하지만 `app/tools.py`와 `app/agent_loop.py`가 매우 커서 책임 분리와 단위 테스트가 어렵다. 새 프로젝트에서는 다음을 처음부터 분리한다.

- API 계층: HTTP 요청·응답과 인증/검증
- Application 계층: 유스케이스와 orchestration
- Domain 계층: 경기, 구장, 좌석, 추천 정책
- Infrastructure 계층: DB, 외부 API, Vector Store, LLM
- Agent 계층: 상태, 라우팅, Tool 실행, 종료 정책

또한 다음 항목을 개선한다.

- 프로세스 메모리 세션 → Redis 또는 DB 기반 세션
- 단일 동기 `/chat` → 비동기 처리와 SSE 스트리밍
- 로컬 JSON 직접 순회 → Repository 인터페이스와 DB 조회
- 로컬 FAISS 단독 의존 → 교체 가능한 Vector Store 어댑터
- 자유로운 Agent 호출 → 결정론적 라우터 + 제한된 Agent 상태 그래프
- 수동 trace 확인 → 골든셋 기반 자동 평가
- 단순 화면 → 근거, Tool 진행 상태, 추천 비교가 보이는 포트폴리오 UI

## 4. 범위와 우선순위

### 4.1 Must-have

- KBO 일정 검색
- 경기 후보 선택과 세션 유지
- 구장 정보 조회
- 날씨 context 생성과 예보 범위 정책
- RAG 기반 좌석 근거 검색
- 규칙 기반 좌석 점수화
- 예매 가이드
- Tool 기반 Agent orchestration
- 출처가 포함된 답변
- 테스트, 관측성, 보안 기본선
- 반응형 웹 UI와 배포

### 4.2 Should-have

- 원정 동선 가이드
- SSE 기반 답변 스트리밍
- 사용자 선호 저장
- 관리자용 데이터/인덱스 상태 화면
- 검색 및 Agent 평가 대시보드
- 대화 공유 또는 결과 카드 저장

### 4.3 Later

- 실시간 교통·막차 API
- 실시간 예매 오픈/잔여석
- 선수·라인업·관전 포인트
- 먹거리·주변 장소 추천
- 로그인과 소셜 인증
- 멀티 Agent
- Fine-tuning

Fine-tuning은 초기에 사용하지 않는다. 먼저 평가 데이터로 routing 일관성 문제를 확인하고, 프롬프트·규칙·상태 그래프로 해결되지 않는 반복적 분류 문제가 측정될 때만 검토한다.

## 5. 목표 아키텍처

```text
Web Client
  └─ REST / SSE
      └─ FastAPI API
          ├─ Chat Use Case
          │   └─ Agent Orchestrator
          │       ├─ Intent Router
          │       ├─ Session State
          │       ├─ Tool Registry
          │       └─ Stop / Fallback Policy
          ├─ Schedule Use Case
          ├─ Recommendation Use Case
          └─ Admin / Health Use Case
              ├─ PostgreSQL Repositories
              ├─ Redis Session Store
              ├─ Vector Store
              ├─ Weather Provider
              ├─ LLM / Embedding Provider
              └─ Tracing / Metrics
```

### 5.1 확정 기술 스택

기술은 학습 과정 중 하나씩 도입하며, 한 번에 모두 설치하지 않는다.

- Backend: Python 3.13, FastAPI, Pydantic v2, Uvicorn
- Dependency/quality: `uv`, Ruff, mypy 또는 pyright, pre-commit
- Database/RAG: Supabase PostgreSQL + pgvector
- DB access: SQLAlchemy 2.x async + asyncpg
- Schema migration: Supabase CLI SQL migrations
- Session/cache: Redis
- Embedding: OpenAI `text-embedding-3-small`, 1536 dimensions
- Vector search: cosine distance, exact search baseline 후 HNSW
- Agent: 1차는 직접 작성한 orchestration, 2차는 LangGraph 비교 적용
- Test: pytest, pytest-asyncio, HTTPX, respx, Testcontainers 선택
- Frontend: Next.js + TypeScript 또는 React + Vite
- UI: Tailwind CSS, 접근 가능한 component library
- Observability: 구조화 로그, OpenTelemetry, LangSmith 선택 연동
- Delivery: Docker Compose, GitHub Actions, backend/frontend 배포

LangChain이나 LangGraph는 FastAPI와 도메인 로직을 익힌 뒤 도입한다. 초기 단계에서는 프레임워크가 숨기는 Tool 호출과 상태 변화를 직접 구현해 본다.

Supabase pgvector의 상세 schema, 검색 함수, 권한, 재색인 결정은 [`adr/001-supabase-pgvector.md`](adr/001-supabase-pgvector.md)를 단일 기준으로 사용한다.

### 5.2 백엔드 디렉터리 초안

```text
new-baseball/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── application/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   ├── agent/
│   │   ├── rag/
│   │   ├── core/
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   └── evals/
│   └── pyproject.toml
├── frontend/
├── data/
│   ├── raw/
│   ├── normalized/
│   └── fixtures/
├── scripts/
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── docs/
├── docker-compose.yml
└── README.md
```

## 6. 핵심 도메인과 API 설계

### 6.1 도메인 모델

- `Team`: 표준 팀 ID, 이름, 별칭
- `Stadium`: 위치, 홈 팀, 돔 여부, 좌표, 날씨 격자
- `Game`: 날짜, 시간, 홈/원정 팀, 구장, 상태
- `SeatSection`: 구역, 가격, 시야, 응원 성향, 지붕/그늘, 편의시설
- `WeatherContext`: 예보 수준, 신뢰도, 위험 플래그, 추천 모드
- `Recommendation`: 후보, 점수 내역, 추천 이유, 데이터 한계
- `SourceDocument`: 출처 URL, 수집 시각, 신뢰 등급, 유효 기간
- `ConversationState`: 후보 경기, 선택 경기, 사용자 선호, 완료한 단계

### 6.2 Tool 계약

모든 Tool은 공통 envelope을 사용한다.

```json
{
  "ok": true,
  "status": "found",
  "data": {},
  "error": null,
  "meta": {
    "source": "structured_db",
    "as_of": "2026-07-26",
    "limitations": []
  }
}
```

초기 Tool 목록:

1. `find_kbo_game`
2. `get_stadium_info`
3. `get_weather_context`
4. `search_baseball_knowledge`
5. `score_seat_candidates`
6. `get_ticketing_guide`
7. `get_logistics_guide`

각 Tool에는 입력 Pydantic 모델, 출력 모델, timeout, retry 가능 여부, 오류 코드, fallback, 로그 정책을 문서화한다.

### 6.3 API 초안

- `GET /health/live`: 프로세스 생존 확인
- `GET /health/ready`: DB, Redis, Vector Store 준비 상태
- `GET /api/v1/games`: 날짜·팀·구장으로 일정 검색
- `GET /api/v1/stadiums/{stadium_id}`: 구장 정보
- `POST /api/v1/recommendations/seats`: 결정론적 좌석 추천
- `POST /api/v1/chat`: 일반 채팅 응답
- `POST /api/v1/chat/stream`: SSE Agent 실행 스트림
- `GET /api/v1/conversations/{id}`: 세션 상태와 대화 조회
- `POST /api/v1/admin/indexes/rebuild`: 보호된 embedding 재색인
- `GET /api/v1/admin/indexes/status`: 인덱스 상태 확인

AI 기능 이전에 `/games`, `/stadiums`, `/recommendations/seats`를 먼저 완성한다. 그래야 Agent가 검증된 API/유스케이스를 Tool로 재사용할 수 있다.

## 7. 단계별 실행 로드맵

기간은 주당 8~12시간 학습을 가정한 기준이며, 진도보다 단계별 완료 조건을 우선한다.

### 7.0 단계별 학습 문서 운영

각 구현 단계는 코드만 작성하지 않고 별도 학습 문서로 남긴다. 문서에는 `학습 목표 → 핵심 개념 → 직접 구현 → 실행 명령 → 테스트 → 오류와 해결 → 회고`를 기록한다.

| Step | 문서 | 핵심 결과 |
|---|---|---|
| 00 | `00-roadmap.md` | 전체 범위와 학습 순서 |
| 01 | `01-python-project-setup.md` | Python 환경, 패키지, 품질 도구 |
| 02 | `02-fastapi-basics.md` | 기본 FastAPI와 OpenAPI |
| 03 | `03-api-schema-and-validation.md` | Pydantic schema와 오류 응답 |
| 04 | `04-static-data-loader.md` | 일정·구장·팀 별칭 로더 |
| 05 | `05-tool-contracts.md` | 공통 Tool 계약과 오류 코드 |
| 06 | `06-agentless-workflow.md` | Agent 없는 고정 Workflow |
| 07 | `07-langchain-agent.md` | LangChain Tool과 AgentExecutor |
| 08 | `08-rag-index.md` | Supabase pgvector RAG와 검색 평가 |
| 09 | `09-persistence-and-session.md` | DB·Redis·대화 상태 |
| 10 | `10-observability.md` | trace, latency, 비용, 평가 |
| 11 | `11-security.md` | 입력·Tool·RAG·로그 보안 |
| 12 | `12-frontend.md` | 채팅·추천·출처 UI |
| 13 | `13-deployment.md` | Docker, CI/CD, 배포 |
| 14 | `14-portfolio-polish.md` | README, 다이어그램, 데모 |

문서 번호는 실제 작업 순서를 뜻한다. 한 Step의 완료 조건과 테스트를 통과하기 전에는 다음 Step의 프레임워크를 성급히 도입하지 않는다.

### Phase 0. 기준선 만들기 — 2~3일

목표: 기존 자료를 참고 자료로 고정하고 새 프로젝트의 범위를 명확히 한다.

작업:

- 기존 프로젝트의 정상/실패 대표 요청을 골든 케이스로 추출한다.
- 기존 데이터를 복사하기 전에 데이터 출처, 수집 시각, 라이선스, 필드 의미를 기록한다.
- ADR(Architecture Decision Record) 템플릿을 만든다.
- 새 저장소 구조, Python 버전, 패키지 관리 방식을 결정한다.
- `.env.example`, `.gitignore`, Makefile 또는 task runner를 만든다.

산출물:

- `docs/product-requirements.md`
- `docs/architecture.md`
- `docs/adr/`
- `docs/evaluation/golden-cases.jsonl`

완료 조건:

- 지원 기능과 제외 기능을 한 문장으로 설명할 수 있다.
- 정상, 정보 부족, 경기 없음, 외부 API 실패 케이스가 최소 2개씩 있다.

### Phase 1. Python 기초와 도메인 코어 — 1주

목표: 프레임워크 없이 핵심 로직을 테스트 가능하게 만든다.

학습:

- 함수, 클래스, dataclass와 Pydantic의 차이
- 타입 힌트, Protocol, Generic의 기초
- 파일 I/O, JSON, datetime, timezone
- 사용자 정의 예외와 오류 코드
- pytest fixture, parameterize

구현:

- 팀 별칭 정규화
- 날짜·팀·구장 기반 일정 필터
- 구장 매핑
- 좌석 후보 점수화
- 예보 가능 기간에 따른 추천 모드 정책

완료 조건:

- LLM과 FastAPI 없이 CLI 또는 테스트에서 일정 검색과 좌석 점수화가 동작한다.
- 도메인 테스트가 외부 네트워크 없이 통과한다.
- 점수 계산 근거가 후보별 세부 점수로 반환된다.

### Phase 2. FastAPI 기본 서비스 — 1주

목표: 도메인 코어를 REST API로 안전하게 노출한다.

학습:

- ASGI와 `async`/`await`
- router, dependency injection, lifespan
- Pydantic request/response schema
- exception handler, middleware, CORS
- OpenAPI와 HTTP 상태 코드
- HTTPX를 이용한 API 테스트

구현:

- application factory와 설정 객체
- `/health/live`, `/health/ready`
- `/games`, `/stadiums/{id}`, `/recommendations/seats`
- 공통 오류 응답
- request ID, 구조화 로그, 요청 시간 측정

완료 조건:

- Swagger UI에서 API를 실행할 수 있다.
- validation error, not found, provider error가 구분된다.
- 라우터 테스트와 유스케이스 테스트가 분리되어 있다.

### Phase 3. 데이터베이스와 데이터 파이프라인 — 1~2주

목표: JSON 기반 데이터를 정규화하고 재현 가능한 적재 흐름을 만든다.

학습:

- 관계형 모델링, transaction, index
- SQLAlchemy async session과 repository pattern
- Supabase CLI SQL migration
- idempotent import와 upsert
- 크롤링 데이터 검증

구현:

- Team, Stadium, Game, SeatSection, Source 테이블
- Repository 인터페이스와 SQLAlchemy 구현
- Supabase local 개발 환경과 migration 작성
- 기존 2026 일정·구장·좌석 데이터 import script
- 원본 → 정규화 → 검증 → 적재 단계 분리
- 중복, 누락, 잘못된 팀/구장 참조 검증 리포트

완료 조건:

- `supabase db reset`과 import 명령으로 빈 DB를 재구축할 수 있다.
- 같은 데이터를 두 번 적재해도 중복되지 않는다.
- API가 JSON 파일 대신 Repository를 사용한다.

### Phase 4. 외부 Provider와 실패 처리 — 1주

목표: 날씨와 같은 외부 의존성을 교체·테스트 가능하게 만든다.

학습:

- HTTP client timeout, retry, circuit breaker 개념
- 비동기 I/O와 connection pooling
- adapter와 dependency override
- cache와 stale data 정책

구현:

- `WeatherProvider` Protocol
- 실제 Provider와 Fake Provider
- timeout, 제한된 retry, 오류 변환
- 돔구장, 예보 범위 밖, API 장애 fallback
- Redis cache 또는 초기에는 in-memory TTL cache

완료 조건:

- 네트워크 실패 테스트가 실제 네트워크 없이 재현된다.
- 응답에 `forecast_level`, `forecast_reliability`, `recommendation_mode`가 포함된다.
- fallback 사용 여부와 이유가 추적된다.

### Phase 5. Tool 계약과 Agent 없는 Workflow — 1주

목표: LLM 없이도 전체 핵심 기능이 동작하게 만들고, Agent가 따라야 할 정답 흐름을 확보한다.

구현:

- 모든 Tool에 Pydantic 입력·출력 모델을 적용한다.
- `{ok, status, data, error, meta}` 공통 반환 구조를 적용한다.
- raw exception을 API나 Tool 결과에 직접 노출하지 않는다.
- 아직 pgvector를 붙이지 않은 `search_baseball_knowledge`는 정적 문서 필터 또는 Fake Retriever로 구현한다.
- 좌석, 예매, 동선의 고정 Workflow를 application service로 만든다.

고정 Workflow:

```text
좌석 추천
find_kbo_game
  → get_stadium_info
  → get_weather_context
  → search_baseball_knowledge
  → score_seat_candidates

예매 안내
find_kbo_game
  → get_stadium_info
  → get_ticketing_guide

원정 동선
find_kbo_game
  → get_stadium_info
  → get_logistics_guide
```

완료 조건:

- 세 Workflow가 LLM API key 없이 동작한다.
- 앞 단계가 실패하면 의존하는 후속 Tool을 호출하지 않는다.
- 정상 Tool 순서와 실패 분기가 테스트로 고정되어 있다.
- 같은 Tool 함수를 REST API와 이후 Agent가 함께 재사용할 수 있다.

### Phase 6. LangChain Agent baseline — 1주

목표: 검증된 Tool을 LangChain에 등록하고, Agent가 필요한 Tool을 선택하도록 만든다.

학습:

- Workflow, RAG, Agent의 경계
- Tool calling과 structured output
- Tool description과 system prompt의 역할
- AgentExecutor의 중간 단계와 종료 조건
- deterministic routing과 LLM routing의 trade-off

권장 진행:

1. 규칙 기반 intent router와 고정 Workflow 결과를 baseline으로 둔다.
2. 검증된 함수를 LangChain Structured Tool로 등록한다.
3. system prompt와 Tool description을 작성한다.
4. AgentExecutor에 최대 반복, 시간 제한, parsing error 정책을 적용한다.
5. 고정 Workflow의 Tool 순서와 Agent 실행 결과를 비교한다.
6. 상태 전이가 복잡해진 뒤 LangGraph 적용 여부를 ADR로 결정한다.

대표 흐름:

```text
좌석 추천
find_kbo_game
  → get_stadium_info
  → get_weather_context
  → search_baseball_knowledge
  → score_seat_candidates
  → grounded answer
```

종료 정책 초기값:

- 최대 Tool 단계: 8
- 동일 Tool + 동일 인자 연속 허용: 1회, 두 번째 반복 시 중단
- 전체 Tool 실패: 2회에서 중단
- 요청 시간 제한: 환경별 설정
- 필수 입력 부족: Tool을 호출하지 않고 clarification

완료 조건:

- 단일 intent와 복합 intent 골든 케이스가 통과한다.
- Agent 답변 없이도 Tool trace만 보고 실행을 재현할 수 있다.
- Tool 결과에 없는 사실을 확정적으로 답하지 않는다.
- 동일 호출 반복과 timeout 테스트가 있다.

### Phase 7. Supabase pgvector 연결과 검색 평가 — 1~2주

목표: 정적/Fake Retriever를 Supabase PostgreSQL + pgvector 검색으로 교체하고, “검색됨”이 아니라 “관련 근거가 검색됨”을 측정한다.

학습:

- embedding, chunking, PostgreSQL metadata filter, top-k
- dense retrieval의 한계
- 검색 평가 지표: Hit Rate, Recall@k, MRR
- 생성 평가와 검색 평가의 분리

구현 순서:

1. 좌석, 예매, 동선 문서의 출처와 유효 기간을 정리한다.
2. 문서 유형별 chunk 전략을 정의한다.
3. `rag_documents`, `rag_chunks` migration과 OpenAI embedding 적재 script를 작성한다.
4. metadata에 `stadium_id`, `team_id`, `doc_type`, `source_url`, `as_of`, `trust_level`을 저장한다.
5. cosine search SQL 함수 `match_rag_chunks`와 `PgVectorRetriever` adapter를 구현한다.
6. query normalization과 metadata pre-filter를 적용한다.
7. 검색 결과에 score, 출처, 데이터 한계를 반환한다.
8. exact search로 골든 검색 baseline을 측정한 뒤 HNSW를 적용한다.

주의:

- 일정과 가격 같은 정형 사실은 DB/JSON lookup을 우선한다.
- 검색 문서 안의 지시문은 데이터일 뿐 명령으로 취급하지 않는다.
- 출처가 불명확하거나 오래된 문서는 답변에서 한계를 표시한다.

완료 조건:

- local Supabase schema와 seed를 명령으로 재생성할 수 있다.
- embedding import/reindex를 idempotent하게 실행할 수 있다.
- 최소 30개의 검색 평가 질의가 있다.
- 문서 유형별 Recall@k baseline을 기록한다.
- 검색 결과에 `source_type`, `source_file` 또는 `source_url`, `data_limitations`가 있다.
- pgvector 연결 전후에도 Tool 계약과 고정 Workflow 테스트가 유지된다.
- HNSW 적용 전후 Recall@k와 latency 차이가 기록된다.

### Phase 8. 대화 상태와 스트리밍 — 1주

목표: 여러 턴에 걸친 경기 선택과 실행 진행 상황을 안정적으로 제공한다.

구현:

- Redis 기반 conversation state
- 후보 경기 → 사용자 선택 → 선택 경기 저장
- 세션 TTL과 삭제 정책
- SSE 이벤트 설계

SSE 이벤트 예:

- `message.started`
- `tool.started`
- `tool.completed`
- `citation.added`
- `message.delta`
- `message.completed`
- `error`

완료 조건:

- “다음 주 롯데 경기” → “두 번째 경기” → “좌석 추천” 흐름이 이어진다.
- 서버 재시작 후에도 설정된 TTL 안에서는 세션이 유지된다.
- 클라이언트 연결 종료 시 불필요한 작업이 취소된다.

### Phase 9. 프론트엔드 MVP — 1~2주

목표: Agent의 가치와 신뢰 근거가 화면에서 드러나게 한다.

핵심 화면:

- 랜딩/서비스 소개
- 채팅
- 경기 후보 선택 카드
- 좌석 추천 비교 카드
- 출처 drawer 또는 근거 패널
- 설정: 응원 팀, 예산, 선호
- 오류, 재시도, 빈 상태

UX 원칙:

- Tool의 내부 thought는 노출하지 않는다.
- 대신 “경기 확인 중”, “날씨 조회 중”, “좌석 근거 검색 중” 같은 안전한 진행 상태를 보여준다.
- 추천 카드에는 총점뿐 아니라 가격, 응원, 시야, 날씨 적합성 이유를 보여준다.
- 실시간 정보가 아닐 경우 기준 시점을 명확히 표시한다.
- 모바일 화면과 키보드 접근성을 확인한다.

완료 조건:

- 새 사용자가 예시 질문 없이도 첫 질문을 시작할 수 있다.
- 스트리밍 중 취소, 재시도, 오류 복구가 가능하다.
- 출처 링크와 데이터 기준 시점이 보인다.
- Lighthouse 접근성·성능 결과를 문서에 기록한다.

### Phase 10. 품질, 평가, 관측성 — 1주

목표: 느낌이 아닌 수치와 trace로 품질을 설명한다.

테스트 피라미드:

- Unit: 정규화, 정책, 점수화, 상태 전이
- Integration: DB, Redis, Vector Store, Provider adapter
- Contract: Tool 입출력 schema
- API: 정상·오류 HTTP 흐름
- Eval: routing, retrieval, groundedness, tool completeness
- E2E: 대표 사용자 여정

관측 항목:

- request/trace/session ID
- intent와 Tool 실행 순서
- Tool별 latency와 오류 코드
- retrieval 문서 ID와 score
- fallback과 stop reason
- 모델, prompt version, token, 비용
- 전체 응답 시간과 첫 토큰 시간

평가셋:

- 정상 일정 조회
- 경기 후보가 여러 개인 요청
- 날짜·팀 누락
- 경기 없음
- 좌석 추천
- 예매 + 동선 복합 요청
- 예보 범위 밖
- 날씨 Provider 실패
- RAG 결과 없음
- 같은 Tool 반복 유도
- 프롬프트 인젝션
- 출처와 모순되는 질문

완료 조건:

- CI에서 unit, integration, contract, eval smoke가 실행된다.
- baseline과 개선 후 결과를 같은 dataset으로 비교한다.
- 실패 trace 하나를 골라 원인과 개선 과정을 문서화한다.

### Phase 11. 보안과 운영 준비 — 1주

목표: 공개 배포에 필요한 최소 보안선과 운영 절차를 만든다.

구현:

- 입력 길이, 형식, 허용 필드 검증
- rate limit과 요청 크기 제한
- secret 환경변수 관리
- CORS allowlist와 보안 헤더
- Tool 인자 allowlist
- URL/파일 Tool 추가 시 SSRF·경로 traversal 방지
- prompt injection 및 시스템 프롬프트 추출 거절 정책
- RAG 문서 신뢰 등급과 인덱싱 검증
- 로그와 trace의 토큰, 이메일, 주소 등 마스킹
- 관리자 endpoint 인증
- dependency 및 container 취약점 검사

테스트:

- Promptfoo 또는 자체 security eval
- 정상 질문이 과도하게 차단되지 않는 회귀 테스트
- 공격 문구가 포함된 RAG 문서 테스트

완료 조건:

- 위협 모델 문서가 있다.
- 최소 10개 공격 케이스와 정상 회귀 케이스가 CI에서 실행된다.
- 공개 응답과 로그에 secret 또는 내부 프롬프트가 나타나지 않는다.

### Phase 12. 배포와 포트폴리오 마감 — 1주

목표: 다른 사람이 설치·실행·평가할 수 있는 결과물을 만든다.

구현:

- backend, frontend Dockerfile
- 로컬 Docker Compose
- production 환경변수와 migration 절차
- GitHub Actions: lint, type check, test, build
- staging/production 배포
- demo data seed
- 장애 시 rollback과 인덱스 재생성 절차

포트폴리오 산출물:

- 문제 정의와 타깃 사용자
- 시스템 아키텍처 다이어그램
- 일반 API/RAG/Agent 역할 분리 설명
- 대표 Agent trace
- RAG 평가 결과
- 실패 사례와 개선 전후 비교
- 보안 설계
- 실행 GIF 또는 짧은 데모 영상
- API 문서와 로컬 실행 방법
- 기술 선택 ADR

완료 조건:

- 새로운 환경에서 README만 보고 실행할 수 있다.
- 공개 URL 또는 재현 가능한 로컬 데모가 있다.
- 핵심 사용자 여정 E2E가 배포 환경에서 통과한다.

## 8. 권장 학습 순서

모든 개념을 선행 학습한 뒤 개발하지 않는다. 각 Phase에서 필요한 만큼 배우고 바로 코드와 테스트로 확인한다.

1. Python 타입과 테스트
2. FastAPI 요청·응답과 의존성 주입
3. SQL과 Repository
4. 비동기 외부 API
5. Tool 계약과 Agent 없는 Workflow
6. structured output과 LangChain Tool calling
7. embedding과 Vector Search
8. SSE와 프론트엔드 상태 관리
9. 관측성·평가·보안
10. Docker·CI/CD·배포

각 학습 주제는 다음 형식으로 기록한다.

```text
개념 → 작은 실험 → 실제 기능 적용 → 테스트 → 배운 점/실패 기록
```

## 9. 테스트 및 평가 목표

초기 수치는 baseline을 측정한 후 조정한다.

- 도메인 unit test: 핵심 정책 branch 중심
- API schema contract: 100% 자동 검증
- 검색 평가: Recall@5, MRR 기록
- routing 평가: intent 및 required Tool sequence 정확도 기록
- Tool completeness: 필수 Tool 누락률 기록
- groundedness: 인용 근거로 확인 가능한 핵심 주장 비율 기록
- latency: p50/p95와 Tool/LLM 구간 분리
- 비용: 요청 유형별 평균 token과 추정 비용
- security: 공격 차단률과 정상 질문 오탐률 동시 기록

중요한 원칙은 “목표 숫자를 먼저 예쁘게 정하기”보다 같은 평가셋으로 변경 전후를 재현하는 것이다.

## 10. 데이터 관리 원칙

- `data/raw`는 수정하지 않는 원본으로 보관한다.
- 정규화 결과에는 schema version을 둔다.
- 모든 문서에 source, collected_at, valid_from/to 또는 as_of를 기록한다.
- 일정·구장 ID는 서비스 전체에서 동일한 canonical ID를 사용한다.
- 크롤러와 importer를 분리한다.
- 데이터 적재는 idempotent하게 만든다.
- 개인정보, API key, 내부 trace 원문은 학습·평가 데이터에 넣지 않는다.
- 기존 데이터는 출처와 사용 가능 여부를 확인한 뒤 가져온다.

## 11. Agent 설계 원칙

1. 정확한 조회는 DB와 일반 함수가 담당한다.
2. 계산 가능한 판단은 규칙과 점수 함수가 담당한다.
3. RAG는 비정형 지식과 출처 제공에 사용한다.
4. Agent는 순서 결정, 추가 질문, 실패 후 대안 선택에 사용한다.
5. LLM 출력은 Pydantic schema로 검증한다.
6. Tool은 최소 권한만 가지며 임의 네트워크·파일 접근을 허용하지 않는다.
7. Agent 내부 추론 원문 대신 안전한 실행 이벤트와 observation을 저장한다.
8. fallback은 성공처럼 숨기지 않고 응답과 trace에 표시한다.
9. 답변은 사용한 데이터의 기준 시점과 한계를 포함한다.
10. 멀티 Agent는 단일 Agent의 병목이 측정된 이후에만 도입한다.

## 12. 포트폴리오에서 강조할 이야기

기능 개수보다 다음 문제 해결 과정을 보여주는 편이 중요하다.

- 거대한 `tools.py` 중심 MVP를 계층형 구조로 리빌드한 이유
- 일정은 DB, 좌석 문서는 RAG, 추천 순위는 규칙, 흐름 결정은 Agent로 나눈 기준
- Agent 호출을 줄여 latency와 비용을 개선한 과정
- 검색 평가셋으로 chunking 또는 filter를 개선한 결과
- Provider 장애와 정보 부족을 fallback으로 처리한 설계
- 출처와 기준 시점을 UI에 노출해 신뢰도를 높인 방식
- 프롬프트 인젝션과 로그 유출을 테스트한 방법
- 실패 trace를 분석해 구조를 개선한 사례

## 13. 첫 2주 실행 체크리스트

### 첫째 주

- [ ] `new-baseball` 프로젝트 구조 생성
- [ ] `uv`와 `pyproject.toml` 설정
- [ ] Ruff, type checker, pytest 설정
- [ ] Team, Stadium, Game, SeatSection 모델 작성
- [ ] 팀 별칭 정규화 구현
- [ ] 일정 검색 구현
- [ ] 좌석 점수화 구현
- [ ] unit test 작성
- [ ] 첫 ADR 작성

### 둘째 주

- [ ] FastAPI application factory 작성
- [ ] settings와 환경변수 검증
- [ ] health endpoint 구현
- [ ] games/stadiums/recommendations router 구현
- [ ] 공통 오류 응답 작성
- [ ] request ID와 구조화 로그 추가
- [ ] HTTPX API test 작성
- [ ] OpenAPI 예시와 README 실행 방법 작성

## 14. Definition of Done

기능 하나는 다음 조건을 모두 만족해야 완료로 본다.

- 요구사항과 범위가 문서화되어 있다.
- 입력·출력 schema가 있다.
- 정상, 경계, 실패 테스트가 있다.
- 외부 의존성은 timeout과 오류 변환이 있다.
- 로그에 request/trace ID가 남는다.
- 민감정보가 로그와 응답에 노출되지 않는다.
- 사용자에게 데이터 출처와 한계를 알린다.
- README 또는 관련 문서가 갱신되어 있다.
- CI에서 lint, type check, test가 통과한다.

## 15. 최종 마일스톤 요약

| 마일스톤 | 결과물 | 핵심 학습 |
|---|---|---|
| M1 도메인 코어 | 일정 검색·좌석 점수화 라이브러리 | Python, 타입, pytest |
| M2 REST API | 일반 야구 정보 API | FastAPI, Pydantic, HTTP |
| M3 데이터 계층 | Supabase PostgreSQL과 재현 가능한 importer | SQLAlchemy, Supabase migration |
| M4 Provider | 날씨 API와 fallback | async I/O, adapter |
| M5 Workflow | 공통 Tool 계약과 고정 실행 흐름 | orchestration, failure policy |
| M6 Agent | LangChain 기반 제한적 Tool 선택 | Tool calling, AgentExecutor |
| M7 RAG | Supabase pgvector 검색과 검색 평가 | embedding, SQL/RPC, HNSW |
| M8 Web App | 스트리밍 채팅과 추천 UI | React/Next.js, SSE |
| M9 Production | 평가·보안·관측·배포 | 운영 품질, CI/CD |

---

이 로드맵의 핵심 순서는 **Python 도메인 로직 → FastAPI API → 정적 데이터·외부 Provider → Tool 계약 → Agent 없는 고정 Workflow → LangChain Agent → Supabase pgvector RAG → 프론트엔드 → 평가·보안·배포**다. 이 순서를 지키면 Agent 프레임워크가 내부 동작을 가리는 문제를 줄이고, 각 계층을 직접 설명할 수 있는 포트폴리오를 만들 수 있다.
