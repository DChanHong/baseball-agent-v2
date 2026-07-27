# Baseball Agent Frontend 폴더 구조 설계

> 상태: 초안 확정  
> 구조 원칙: Next.js App Router + FSD-inspired layers + typed API contracts + UI state/server state 분리

## 1. 설계 목적

프론트엔드는 KBO 직관 초심자와 원정 팬이 한 화면에서 Agent와 대화하고, Tool 실행 결과를 야구 도메인에 맞는 카드 UI로 확인하는 웹 클라이언트다.

이 프로젝트의 프론트엔드는 단순 채팅창이 아니라 다음 정보를 신뢰할 수 있게 보여주는 화면을 목표로 한다.

- 경기 일정과 후보 경기 선택
- 구장 정보와 돔 여부
- 날씨 기반 준비와 좌석 판단
- 좌석 추천 비교와 점수 근거
- 예매 안내와 공식 출처
- 원정 동선과 주의사항
- Agent Tool 진행 상태, 출처, 기준 시점, 한계

핵심 목표는 다음과 같다.

- Next.js App Router의 라우팅 영역과 기능 단위 UI 영역을 분리한다.
- 채팅, 로그인, 프로필, 출처 패널, Tool 결과 UI를 FSD 기준으로 배치한다.
- 서버에서 온 데이터는 Zod schema로 검증하고 TypeScript 타입을 schema에서 파생한다.
- Jotai는 화면 안의 UI 상태만 담당하고 React Query는 서버 상태를 담당한다.
- Agent 내부 추론 원문은 노출하지 않고 안전한 진행 상태와 Observation 결과만 UI에 표현한다.
- 기능이 늘어날 때 `shared`가 비대해지지 않도록 도메인 의미가 있는 코드는 `entities` 또는 `features`로 올린다.

## 2. 최상위 모노레포 구조

```text
baseball-agent-v2/
├── backend/
├── frontend/
├── supabase/
├── docs/
│   ├── backend/
│   ├── frontend/
│   └── roadmap/
└── README.md
```

### 2.1 프론트엔드 위치

프론트엔드는 루트의 `frontend/`에 독립된 Next.js 프로젝트로 둔다.

```text
frontend/
├── src/
├── public/
├── docs/
├── package.json
├── pnpm-lock.yaml
├── next.config.ts
├── tsconfig.json
└── README.md
```

| 경로 | 책임 |
|---|---|
| `frontend/src/` | 애플리케이션 소스 코드 |
| `frontend/public/` | 정적 asset |
| `frontend/docs/` | 프론트엔드 내부 의사결정 문서 |
| `frontend/package.json` | 실행 script와 패키지 의존성 |
| `frontend/pnpm-lock.yaml` | pnpm lockfile |
| `frontend/next.config.ts` | Next.js 설정 |
| `frontend/tsconfig.json` | TypeScript 설정 |
| `docs/frontend/` | 저장소 전체 기준의 프론트엔드 설계 문서 |

## 3. 기술 스택

| 항목 | 선택 | 책임 |
|---|---|---|
| Framework | Next.js App Router | 라우팅, 빌드, 배포, SSR 경계 |
| Language | TypeScript | 컴포넌트 props, API 응답, 도메인 타입 |
| Package manager | pnpm | 의존성 설치와 lockfile 관리 |
| Styling | styled-components | 컴포넌트 단위 스타일과 theme |
| Client state | Jotai | 모달, drawer, 입력값, 선택 상태 |
| Server state | TanStack React Query | API 조회, mutation, cache, retry |
| Validation | Zod | API 응답과 Tool 결과 런타임 검증 |
| Animation | framer-motion | 랜딩 채팅 UI의 제안 패널과 작은 전환 |
| Icons | lucide-react | 버튼과 상태 아이콘 |
| Virtualization | TanStack React Virtual | 긴 채팅 메시지 목록 최적화 |

`npm install` 대신 다음 명령을 사용한다.

```bash
pnpm install
pnpm add <package>
pnpm add -D <package>
```

## 4. 현재 프론트엔드 구조

```text
frontend/src/
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   ├── page.tsx
│   ├── providers.tsx
│   └── styled-components-registry.tsx
├── views/
│   └── chat/
│       ├── index.ts
│       └── ui/
│           └── chat-page.tsx
├── widgets/
│   ├── app-header/
│   │   └── ui/
│   │       └── app-header.tsx
│   ├── chat/
│   │   └── ui/
│   │       └── chat-panel.tsx
│   └── source-drawer/
│       ├── model/
│       │   └── source-drawer.atom.ts
│       └── ui/
│           └── source-drawer.tsx
├── features/
│   ├── auth/
│   │   ├── model/
│   │   │   └── auth-modal.atom.ts
│   │   └── ui/
│   │       └── login-modal.tsx
│   ├── profile/
│   │   ├── model/
│   │   │   └── profile-modal.atom.ts
│   │   └── ui/
│   │       └── profile-modal.tsx
│   └── send-message/
│       ├── model/
│       │   └── chat-input.atom.ts
│       └── ui/
│           └── chat-composer.tsx
├── entities/
│   ├── citation/
│   │   └── model/
│   │       └── types.ts
│   ├── game/
│   │   └── model/
│   │       └── types.ts
│   ├── message/
│   │   ├── model/
│   │   │   └── types.ts
│   │   └── ui/
│   │       └── message-bubble.tsx
│   ├── seat/
│   │   └── model/
│   │       └── types.ts
│   └── tool-result/
│       ├── model/
│       │   └── types.ts
│       └── ui/
│           └── tool-result-card.tsx
└── shared/
    ├── api/
    │   └── tool-envelope.schema.ts
    ├── config/
    ├── lib/
    │   ├── query/
    │   │   └── create-query-client.ts
    │   └── zod/
    │       ├── index.ts
    │       └── parse.ts
    ├── model/
    ├── styles/
    │   ├── global-style.ts
    │   ├── styled.d.ts
    │   └── theme.ts
    ├── types/
    └── ui/
        ├── button/
        │   ├── button.tsx
        │   └── index.ts
        └── modal/
            ├── index.ts
            └── modal.tsx
```

## 5. FSD 레이어 정의

이 프로젝트는 Feature-Sliced Design을 그대로 엄격하게 복제하지 않고, Next.js App Router와 충돌하지 않도록 조정한 FSD-inspired 구조를 사용한다.

### 5.1 `app`

```text
src/app/
├── layout.tsx
├── page.tsx
├── providers.tsx
└── styled-components-registry.tsx
```

`app`은 Next.js 예약 라우팅 영역이다.

책임:

- Next.js route entry
- root layout
- metadata
- 전역 provider 조립
- styled-components SSR registry
- 전역 CSS import

`app`에는 구체적인 도메인 UI나 비즈니스 상태를 넣지 않는다.

```text
허용:
app/page.tsx → views/chat

금지:
app/page.tsx 안에 채팅 UI 전체 구현
app/layout.tsx 안에 개별 feature atom 선언
```

### 5.2 `views`

```text
src/views/
└── chat/
```

FSD의 page layer 역할을 한다. Next.js는 `src/pages`를 Pages Router로 해석하므로 이 프로젝트에서는 `pages` 대신 `views`라는 이름을 사용한다.

책임:

- 한 화면의 큰 레이아웃 조립
- route에서 사용할 page component export
- modal, widget, drawer 배치

현재는 채팅 원페이지 서비스이므로 `views/chat`만 존재한다.

### 5.3 `widgets`

```text
src/widgets/
├── app-header/
├── chat/
└── source-drawer/
```

여러 feature와 entity를 조합한 화면 블록이다.

책임:

- 앱 헤더
- 채팅 랜딩 패널
- 메시지 리스트 영역
- 출처 drawer
- 향후 Tool trace timeline

Widget은 사용자 행동을 직접 처리할 수 있지만, 재사용 가능한 작은 명령은 `features`로 분리한다.

### 5.4 `features`

```text
src/features/
├── auth/
├── profile/
└── send-message/
```

사용자가 수행하는 액션 단위다.

책임:

- 로그인 모달 열기와 입력
- 프로필 선호 설정
- 채팅 메시지 입력과 전송
- 경기 후보 선택
- 추천 결과 저장
- 스트리밍 중단과 재시도

Feature는 필요한 entity 타입을 사용할 수 있다. 단, 다른 feature 내부 구현에 직접 의존하지 않는다.

```text
허용:
features/send-message → entities/message/model

금지:
features/send-message → features/profile/ui
```

### 5.5 `entities`

```text
src/entities/
├── citation/
├── game/
├── message/
├── seat/
└── tool-result/
```

프론트엔드가 이해하는 도메인 개념이다.

책임:

- 도메인별 Zod schema
- schema에서 파생한 TypeScript 타입
- 도메인별 작은 UI
- 서버 응답을 화면에서 표현하기 위한 표시 모델

Entity에는 API 호출 로직을 넣지 않는다. API 호출은 `shared/api` 또는 feature별 api 파일에서 시작하고, 응답 검증은 entity schema를 사용한다.

### 5.6 `shared`

```text
src/shared/
├── api/
├── config/
├── lib/
├── model/
├── styles/
├── types/
└── ui/
```

프로젝트 전체에서 재사용 가능한 기술적 기반이다.

허용 예:

- `Button`, `Modal` 같은 범용 UI
- React Query client 생성
- Zod parse helper
- theme와 global style
- 공통 Tool envelope schema
- API base URL 설정

금지 예:

- 좌석 추천 카드의 상세 렌더링
- 경기 후보 선택 정책
- 야구 팀 별칭 변환
- 채팅 전송 유스케이스
- Agent Tool별 UI 분기

`shared`가 커지면 먼저 `entities` 또는 `features`로 옮길 수 있는지 검토한다.

## 6. Next.js App Router와 FSD의 충돌 회피

Next.js에는 예약 폴더가 있다.

| 폴더 | Next.js 의미 | 프로젝트 규칙 |
|---|---|---|
| `src/app` | App Router | 라우팅과 provider 전용 |
| `src/pages` | Pages Router | 사용하지 않음 |
| `src/components` | 예약은 아니지만 관용적 공용 폴더 | 사용하지 않음 |

shadcn 스타일의 예제는 보통 `/components/ui`를 사용하지만, 이 프로젝트는 `shared/ui`를 공통 UI 위치로 사용한다.

```text
shadcn 예제의 /components/ui/button
→ 이 프로젝트의 src/shared/ui/button
```

Tailwind CSS도 현재 사용하지 않는다. 프론트엔드 스타일 기준은 `styled-components`와 `shared/styles/theme.ts`다.

## 7. 상태 관리 원칙

### 7.1 Jotai

Jotai는 클라이언트 UI 상태만 담당한다.

현재 atom:

| Atom | 위치 | 책임 |
|---|---|---|
| `isLoginModalOpenAtom` | `features/auth/model` | 로그인 모달 열림 상태 |
| `isProfileModalOpenAtom` | `features/profile/model` | 프로필 모달 열림 상태 |
| `chatInputAtom` | `features/send-message/model` | 채팅 입력값 |
| `isSourceDrawerOpenAtom` | `widgets/source-drawer/model` | 출처 drawer 열림 상태 |

허용 예:

- 모달 열림 여부
- drawer 열림 여부
- 선택된 추천 카테고리
- 입력창 draft
- 현재 사용자가 선택한 경기 후보 ID

금지 예:

- 서버에서 조회한 대화 목록 전체
- 경기 일정 API 응답
- 프로필 저장 결과
- Tool 실행 완료 결과 cache

### 7.2 TanStack React Query

React Query는 서버 상태를 담당한다.

향후 대상:

- 대화 목록 조회
- 특정 conversation 메시지 조회
- 경기 후보 조회
- 좌석 추천 API 호출
- 프로필 저장 mutation
- 일반 REST 기반 fallback 호출

SSE 스트리밍 자체는 React Query만으로 처리하지 않는다. 별도 streaming hook에서 이벤트를 수신하고, 완료된 메시지를 React Query cache에 반영한다.

```text
SSE event
→ useChatStream hook
→ streaming local state
→ message.completed
→ React Query cache update
```

## 8. Zod와 타입 계약

프론트엔드 타입은 가능하면 Zod schema에서 파생한다.

```ts
export const gameSummarySchema = z.object({
  id: z.string().min(1),
  date: z.string().min(1),
  homeTeam: z.string().min(1),
  awayTeam: z.string().min(1),
  stadiumName: z.string().min(1),
});

export type GameSummary = z.infer<typeof gameSummarySchema>;
```

현재 schema:

| Schema | 위치 | 책임 |
|---|---|---|
| `chatMessageSchema` | `entities/message/model/types.ts` | 채팅 메시지 |
| `toolResultSchema` | `entities/tool-result/model/types.ts` | Agent Tool 결과 표시 모델 |
| `gameSummarySchema` | `entities/game/model/types.ts` | 경기 요약 |
| `seatScoreSummarySchema` | `entities/seat/model/types.ts` | 좌석 점수 요약 |
| `citationSchema` | `entities/citation/model/types.ts` | 출처 |
| `createToolEnvelopeSchema` | `shared/api/tool-envelope.schema.ts` | 백엔드 Tool envelope |

API 응답을 받을 때는 `parseWithSchema` 또는 `safeParseWithSchema`를 사용한다.

```ts
const parsed = parseWithSchema(chatMessageSchema, responseJson);
```

## 9. Agent Tool UI 배치 규칙

Agent Tool 결과는 채팅 말풍선 안에 일반 텍스트로만 넣지 않고, Tool 종류에 맞는 UI로 렌더링한다.

초기 Tool과 권장 UI:

| Tool | Entity/Widget | UI |
|---|---|---|
| `find_kbo_game` | `entities/game` | 경기 후보 선택 카드 |
| `get_stadium_info` | `entities/stadium` | 구장 정보 카드 |
| `get_weather_context` | `entities/weather` | 날씨 context 카드 |
| `search_baseball_knowledge` | `entities/citation` | 근거 요약과 출처 |
| `score_seat_candidates` | `entities/seat` | 좌석 추천 비교 카드 |
| `get_ticketing_guide` | `features/ticketing-guide` 또는 `entities/ticketing` | 예매 안내 카드 |
| `get_logistics_guide` | `features/logistics-guide` 또는 `entities/logistics` | 원정 동선 카드 |

분기 기준:

```text
Tool result schema
→ entities/tool-result
→ Tool별 specialized card
→ message bubble 안에서 렌더링
```

`tool-result-card.tsx`가 커지면 다음처럼 분리한다.

```text
entities/tool-result/ui/
├── tool-result-card.tsx
├── game-candidates-card.tsx
├── weather-context-card.tsx
├── seat-score-card.tsx
└── citation-list-card.tsx
```

## 10. API 계층 설계

초기에는 `shared/api`에 공통 fetcher와 envelope schema를 둔다.

```text
shared/api/
├── client.ts
├── endpoints.ts
├── tool-envelope.schema.ts
└── errors.ts
```

기능이 늘어나면 feature 또는 entity 근처에 query hook을 둔다.

```text
features/send-message/api/
├── send-message.ts
└── use-send-message.ts

entities/game/api/
├── get-games.ts
└── use-games-query.ts
```

규칙:

- fetcher는 `shared/api`에 둔다.
- endpoint별 Zod 검증은 응답 모델을 소유한 entity schema를 사용한다.
- React Query hook은 사용자 행동에 가까우면 `features`, 순수 조회면 `entities`에 둔다.
- API 응답 타입을 손으로 중복 작성하지 않는다.

## 11. 스타일 구조

```text
shared/styles/
├── global-style.ts
├── styled.d.ts
└── theme.ts
```

| 파일 | 책임 |
|---|---|
| `theme.ts` | color, radius, shadow, layout token |
| `styled.d.ts` | styled-components DefaultTheme 타입 확장 |
| `global-style.ts` | body, reset, 기본 폰트, 전역 element 스타일 |

규칙:

- 색상과 radius는 가능한 한 `theme`에서 가져온다.
- 페이지 전체 배경과 레이아웃은 `views` 또는 `widgets`에서 정의한다.
- 반복 가능한 버튼, 모달 같은 UI는 `shared/ui`로 올린다.
- 도메인별 카드 스타일은 해당 entity 또는 widget에 둔다.
- Tailwind className은 사용하지 않는다.

## 12. 의존성 방향

허용 방향:

```text
app
  ↓
views
  ↓
widgets
  ↓
features
  ↓
entities
  ↓
shared
```

실제 import는 필요한 만큼만 허용한다.

```text
views → widgets, features
widgets → features, entities, shared
features → entities, shared
entities → shared
shared → 외부 라이브러리
```

금지 방향:

```text
shared → entities
entities → features
features → widgets
widgets → views
views → app
```

예외:

- `app`은 Next.js entry이므로 `views`를 import할 수 있다.
- `providers.tsx`는 외부 provider와 shared 설정을 조립할 수 있다.

## 13. 테스트 구조

프론트엔드 테스트를 도입하면 다음 구조를 사용한다.

```text
frontend/
├── src/
└── tests/
    ├── unit/
    │   ├── entities/
    │   └── features/
    ├── integration/
    │   ├── api/
    │   └── chat/
    └── e2e/
        └── chat.spec.ts
```

| 테스트 | 대상 | 도구 후보 |
|---|---|---|
| Unit | Zod schema, pure helper, atom 초기값 | Vitest |
| Component | Button, Modal, Tool card | Testing Library |
| Integration | React Query hook, API parsing | MSW |
| E2E | 채팅 입력, 제안 선택, 모달, 출처 drawer | Playwright |

초기에는 `typecheck`, `lint`, `build`를 기본 품질선으로 유지한다.

```bash
pnpm typecheck
pnpm lint
pnpm build
```

## 14. 지금 생성한 최소 구조

현재 생성한 최소 구조는 다음 목적을 만족한다.

- Next.js App Router 앱이 실행된다.
- styled-components SSR 설정이 있다.
- Jotai와 React Query provider가 조립되어 있다.
- Zod 기반 entity schema가 있다.
- 랜딩형 채팅 화면이 있다.
- 로그인 모달과 프로필 모달이 있다.
- 출처 drawer가 있다.
- Tool 결과 카드의 기본 표시 모델이 있다.

아직 만들지 않은 것:

- 실제 백엔드 API client
- SSE streaming hook
- 대화 메시지 저장과 조회 hook
- 경기 후보 선택 카드
- 좌석 추천 상세 카드
- 구장/날씨/예매/동선 specialized Tool 카드
- 테스트 도구 설정
- 인증 provider 연동

빈 폴더나 추상화를 더 만들기보다, 실제 기능을 연결하는 시점에 필요한 단위로 추가한다.

## 15. 단계별 디렉터리 확장

| 개발 단계 | 추가 경로 |
|---|---|
| 채팅 API 연결 | `features/send-message/api`, `shared/api/client.ts` |
| SSE 스트리밍 | `features/chat-stream`, `widgets/tool-progress` |
| 경기 후보 선택 | `features/select-game`, `entities/game/ui` |
| 좌석 추천 상세 | `entities/seat/ui`, `widgets/seat-recommendation` |
| 출처 표시 고도화 | `entities/citation/ui`, `widgets/source-drawer` |
| 사용자 선호 저장 | `features/profile/api`, `entities/user-preference` |
| 테스트 도입 | `frontend/tests`, `vitest.config.ts`, `playwright.config.ts` |
| 배포 준비 | `frontend/Dockerfile`, `.github/workflows/frontend-ci.yml` |

## 16. 최종 확정 요약

```text
Frontend
├── Next.js App Router
│   └── src/app
├── FSD-inspired layers
│   ├── views
│   ├── widgets
│   ├── features
│   ├── entities
│   └── shared
├── State
│   ├── Jotai: UI state
│   └── React Query: server state
├── Contracts
│   └── Zod schema → TypeScript type
└── UI
    └── styled-components + shared theme
```

최종 의존성 원칙:

```text
Next route → View → Widget → Feature → Entity → Shared
Frontend API client → FastAPI
API response → Zod schema → React Query cache → UI
SSE stream → safe event model → message/tool UI
```

이 구조를 프론트엔드 폴더와 의존성의 기준으로 사용한다. 구조를 크게 변경해야 할 때는 `docs/adr/` 또는 `docs/frontend/`에 변경 이유와 영향을 먼저 기록한다.
