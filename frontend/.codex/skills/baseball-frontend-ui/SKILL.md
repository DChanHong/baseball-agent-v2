---
name: baseball-frontend-ui
description: Baseball Agent frontend UI를 설계, 구현, 리뷰할 때 사용한다. frontend/의 Next.js App Router, React, styled-components, FSD-inspired 구조, chat UX, streaming assistant state, source/citation drawer, tool-result card, responsive layout, accessibility, visual polish, Claude-to-Codex UI/UX skill 변환 작업에 사용한다.
---

# Baseball Frontend UI

## 개요

이 스킬은 KBO Baseball Agent 프론트엔드가 MVP 채팅 화면에서 신뢰할 수 있는 직관 도우미로 확장될 때, UI 방향과 코드 구조가 흔들리지 않도록 돕는다. 마케팅 페이지처럼 꾸미기보다 반복 사용에 편한 실용적이고 빠르게 훑을 수 있는 UI를 우선한다.

## 먼저 읽을 것

UI 변경 전에는 필요한 범위만 작게 읽는다.

- `frontend/AGENTS.md`
- `frontend/package.json`
- `frontend/src/shared/styles/theme.ts`
- `frontend/src/shared/styles/global-style.ts`
- 작업 대상과 관련된 `frontend/src/views`, `frontend/src/widgets`, `frontend/src/features`, `frontend/src/entities`, `frontend/src/shared` 하위 파일

조금이라도 의미 있는 UI 구현/리뷰라면 `references/project-ui-rules.md`를 읽는다. Claude용 UI/UX Pro Max 지침을 가져오거나 변환할 때만 `references/claude-to-codex-notes.md`를 읽는다.

## 작업 흐름

1. 작업 표면을 식별한다: chat page, composer, message bubble, tool-result card, modal, drawer, header, shared primitive.
2. FSD-inspired 소유 경계를 지킨다. 도메인 의미가 분명할 때만 코드를 더 상위 레이어로 옮긴다.
3. 기존 의존성을 먼저 사용한다: Next.js App Router, TypeScript, styled-components, Jotai, TanStack Query, zod, framer-motion, lucide-react.
4. 새 색상, radius, shadow, spacing을 추가하기 전에 기존 theme token을 먼저 적용한다.
5. tool 출력은 신뢰 가능하게 만든다. 가능한 경우 출처, 기준 시점, loading/failure 상태, 한계를 보여준다.
6. 모바일/데스크톱 폭에서 반응형을 확인한다. 가로 스크롤, 잘린 컨트롤, 겹치는 텍스트가 없어야 한다.
7. TypeScript 또는 React 코드를 바꿨다면 `frontend/`에서 `pnpm lint`, `pnpm typecheck`를 실행한다.

## 디자인 방향

이 제품은 landing page가 아니라 스포츠 유틸리티 채팅 앱으로 본다. UI/UX Pro Max 분류 중 이 프로젝트에 맞는 방향은 다음이다.

- Content-first utility UI
- Minimalism / Swiss-style structure
- tool card에는 data-dense dashboard 패턴
- 신뢰와 가독성을 위한 절제된 표면감
- 상태를 명확히 설명하는 micro-interaction만 사용

장식용 gradient, 흔한 AI 보라색 테마, emoji icon, 과한 marketing hero, card 안의 card, feature component 안의 raw hex 난립, 상태를 설명하지 못하는 motion은 피한다.

## 구현 규칙

- route entry와 provider는 `src/app`에 둔다.
- 화면 조립은 `src/views`에 둔다.
- 조합된 화면 블록은 `src/widgets`에 둔다.
- 사용자 action과 flow-specific state는 `src/features`에 둔다.
- 도메인 UI와 도메인 type은 `src/entities`에 둔다.
- 재사용 primitive, schema, style token, generic helper는 `src/shared`에 둔다.
- Jotai는 UI state만 맡긴다. API cache, retry, invalidation이 필요하면 React Query를 사용한다.
- 모호한 tool data를 렌더링하기 전에는 zod schema로 backend payload를 검증한다.
- button, status, tool-card affordance에는 lucide-react icon을 우선 사용한다.
- token으로 공유해야 할 값이 아니라면 styled-components는 component와 가깝게 둔다.

## 전달 전 체크리스트

- loading, empty, success, failure 상태가 표현되어 있다.
- keyboard focus가 보이고 control에 accessible name이 있다.
- 가능한 interactive target은 44px 이상이다.
- text는 안정적인 container 제약 안에서 줄바꿈되며 겹치지 않는다.
- tool card는 요약만 보여주지 않고 근거와 출처를 노출한다.
- 새 token을 의도적으로 추가한 경우가 아니라면 color는 `theme.ts`에서 온다.
- animation은 reduced-motion 기대를 존중하고 짧은 상태 전환에만 사용한다.
- `pnpm lint`, `pnpm typecheck`를 실행했거나 실행하지 못한 이유를 보고한다.

## 참조 문서

- `references/project-ui-rules.md`: 프로젝트 전용 UI, FSD, 접근성, 카드 설계 규칙.
- `references/claude-to-codex-notes.md`: Claude용 UI/UX Pro Max 지침을 Codex에 맞게 바꾸는 방법.
