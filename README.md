# KBO Mate (baseball-agent-v2)

KBO Mate는 KBO 직관 준비를 돕는 RAG 기반 AI Agent MVP입니다. 사용자가 채팅으로 경기 일정, 구장 정보, 예매, 좌석, 준비물, 야구 규칙을 물어보면 FastAPI 백엔드가 질문 의도를 라우팅하고, 필요한 Tool 또는 RAG 검색 결과를 Next.js 프론트엔드에 스트리밍합니다.

- 서비스 주소: https://kbo-mate.dev-hong.it.kr
- API Health: https://api.kbo-mate.dev-hong.it.kr/health
- GitHub: https://github.com/DChanHong/baseball-agent-v2

## 개발 목적

RAG 기반 AI Agent를 직접 설계하고, FastAPI 백엔드부터 사용자용 Next.js 프론트엔드까지 연결한 MVP 서비스를 구현하는 것이 목표였습니다.

단순히 LLM에 질문을 보내는 챗봇이 아니라, 정확해야 하는 경기 일정과 구장 기본 정보는 정형 DB에서 조회하고, 설명과 출처가 필요한 구장 가이드/예매/야구 지식은 RAG로 검색하도록 분리했습니다. 이 구조를 통해 포트폴리오에서 Agent 라우팅, Tool 실행, Vector Search, SSE 스트리밍, 사용자 화면까지 end-to-end로 설명할 수 있게 만들었습니다.

## 주요 기능

- 로그인 사용자 기반 AI 채팅
- LangGraph 기반 Agent 실행 흐름
- LLM structured output 기반 Tool 라우팅
- 경기 일정 조회: 팀, 날짜, 기간 기준 KBO 경기 검색
- 구장 기본 정보 조회: 주소, 홈팀, 돔 여부, 지역 정보
- 구장 날씨 조회: KBO 구장 기준 단기예보와 직관 주의 수준 제공
- 구장 가이드 RAG: 좌석, 교통, 주차, 반입 정책, 편의시설 검색
- 예매 안내 RAG: 구단/구장별 예매처, 예매 방법, 현장 발권, 취소 안내 검색
- 야구 지식 RAG: 야구 규칙, 자주 나오는 플레이, 최신 KBO 규정 검색
- SSE 기반 스트리밍 응답과 Tool 실행 이벤트
- 프론트엔드 Tool 결과 카드 렌더링
- 대화 context 저장: 단일 경기 조회 후 "어디서 해?", "몇 시야?" 같은 후속 질문 처리

## 기술 스택

### Backend

- Python 3.13
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy Async
- asyncpg
- LangChain
- LangGraph
- OpenAI SDK
- Uvicorn

### Frontend

- Next.js App Router
- React 19
- TypeScript
- styled-components
- Jotai
- TanStack React Query
- TanStack Virtual
- Framer Motion
- lucide-react
- pnpm

### Database / Infra

- Supabase PostgreSQL
- Supabase Auth
- pgvector
- Vercel: frontend 배포
- Render: backend API 배포
- 공공데이터포털 기상청 단기예보 API

## 사용한 LLM과 Vector DB

- LLM: OpenAI `gpt-5-mini`
- Embedding Model: OpenAI `text-embedding-3-small`
- Vector DB: Supabase PostgreSQL + `pgvector`
- Vector Dimension: 1536

## 데이터 출처

데이터는 도메인별로 `data/` 아래에서 원천, 정규화 결과, 평가 케이스를 분리해 관리했습니다.

- KBO 경기 일정: KBO 공식 일정 데이터를 수집해 정규화
- 구장 가이드: KBO 및 각 구단/지자체 공식 안내, 구장 공식 페이지 기반 수집
- 야구 지식: 공식야구규칙, KBO 리그 규정, 자주 나오는 플레이/판정 설명
- 날씨: 기상청 단기예보 API

## Agent / RAG 처리 흐름

```text
사용자 메시지 입력
→ FastAPI /api/v1/chat SSE 요청
→ 로그인 세션과 대화 context 확인
→ LangGraph Agent 시작
→ ToolRoutingService가 LLM structured output으로 의도 분류
→ 필요한 Tool 선택
→ AgentToolExecutor가 도메인 Tool Handler 실행
→ 정형 DB 조회 또는 RAG 검색
→ Tool 결과를 SSE 이벤트로 프론트엔드에 전송
→ assistant 답변 생성
→ conversation metadata에 다음 턴용 context 저장
```

RAG Tool은 사용자 질문을 embedding한 뒤 `rag_chunks` 테이블에서 pgvector 유사도 검색을 수행합니다. 검색 결과에는 chunk 내용뿐 아니라 출처 URL, 기준 시점, 신뢰 등급, 한계 사항을 포함해 답변에서 근거와 제약을 함께 다룰 수 있게 했습니다.

## 직접 해결한 핵심 문제

- 정확한 정보와 설명형 정보를 분리해 일정/구장 기본값은 정형 DB, 좌석/예매/규칙 설명은 RAG로 처리했습니다.
- LLM이 모든 질문에 바로 답하지 않도록 Tool 라우팅 정책과 Pydantic schema를 설계했습니다.
- LangGraph로 `route -> prepare_tool -> tool_execute -> state_update -> answer_generate` 흐름을 명시적으로 구성했습니다.
- Tool 실행 상태를 SSE 이벤트로 내려 프론트엔드에서 "어떤 도구가 실행됐는지"를 카드 형태로 보여줄 수 있게 했습니다.
- 직전 경기 조회 결과를 compact context로 저장해 후속 질문에서 전체 메시지 이력을 다시 주입하지 않아도 자연스럽게 이어지도록 만들었습니다.
- RAG 문서에는 공식 출처, 기준 시점, review status, limitation을 함께 저장해 출처 기반 답변과 검색 평가가 가능하도록 구성했습니다.

## 프로젝트 구조

```text
backend/   FastAPI API, Agent routing, LangGraph workflow, Tool handler
frontend/  Next.js App Router 기반 채팅 UI
supabase/  PostgreSQL migration, seed, pgvector schema
data/      KBO schedule, stadium guide, baseball knowledge 데이터
docs/      기획, 설계, RAG/embedding 계획, 작업 메모
utils/     데이터 수집과 검증 보조 스크립트
```

## 로컬 실행

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 4000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

프론트엔드는 기본적으로 http://127.0.0.1:3001 에서 실행됩니다.

## 환경 변수

루트와 백엔드의 `.env.example`을 기준으로 값을 설정합니다.

주요 환경 변수:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `KMA_SERVICE_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

## 향후 계획

- 운영 환경 smoke test 자동화
- RAG 검색 품질 평가 케이스 확대
- 좌석 추천 Tool 고도화
- 지도 API 기반 이동 경로 안내 추가
- 실시간 티켓 잔여석 연동 검토
- 관측성, 에러 추적, CI/CD 강화
