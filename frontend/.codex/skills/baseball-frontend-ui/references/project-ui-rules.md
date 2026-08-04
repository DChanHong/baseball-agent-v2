# 프로젝트 UI 규칙

## 제품 성격

이 프론트엔드는 한 화면에서 쓰는 KBO 직관 도우미다. 사용자는 경기 일정, 구장, 날씨, 좌석, 예매, 이동, 출처 근거를 빠르고 믿을 수 있게 확인해야 한다. 훑어보기, 비교하기, 반복 사용하기에 좋은 UI를 설계한다.

## 시각 방향

- 현재 palette는 field green, paper background, white panel, red accent, blue info, amber warning을 기반으로 유지한다.
- background, foreground, muted text, panel, border, radius, primary/accent/info/warning 색상은 `theme.ts` token을 사용한다.
- 같은 시각 결정이 여러 component에서 반복될 때만 새 theme token을 추가한다.
- compact layout, 분명한 hierarchy, 절제된 surface를 선호한다.
- 흔한 AI gradient, 보라색 위주의 theme, 과한 장식 card, 가독성을 낮추는 visual effect는 피한다.

## 레이아웃

- Mobile first로 설계한다. 375px 폭에서 가로 스크롤이 없어야 한다.
- tool card, icon, status chip, composer action, modal control처럼 반복되는 UI에는 안정적인 크기 제약을 둔다.
- card는 message, tool result, modal, 반복 item처럼 개별 artifact를 나타낼 때 사용한다. page section을 floating card처럼 감싸지 않는다.
- chat input은 접근 가능한 위치에 유지하고, fixed dock 때문에 content가 가려지지 않게 한다.

## 컴포넌트 소유 경계

- `app`: route entry, root layout, metadata, providers, styled-components registry.
- `views`: page-level composition.
- `widgets`: chat panel, header, source drawer 같은 조합된 UI block.
- `features`: send-message, auth, profile 같은 user action과 flow-specific state.
- `entities`: message, game, seat, citation, tool result 같은 domain object.
- `shared`: generic primitive, style, schema, config, reusable library.

project-domain 의미가 없는 component만 `shared`로 옮긴다. domain object를 렌더링하거나 모델링하면 `entities`에 둔다. feature-specific state는 `shared`에 두지 않는다.

## 상태와 데이터

- Jotai는 modal open, drawer open, selected item, input draft 같은 local UI state를 맡는다.
- TanStack Query는 fetched data, mutation, cache, retry, invalidation 같은 server state를 맡는다.
- Streaming state는 dedicated hook 또는 feature model에 둘 수 있고, 완료된 message를 durable state로 합친다.
- Tool result component는 typed data를 받고 SSE transport detail을 몰라야 한다.
- payload shape이 변할 수 있는 API boundary에서는 zod schema를 사용한다.

## Chat UX

- user message, assistant message, streaming assistant content, tool progress를 구분된 상태로 보여준다.
- hidden reasoning이나 chain-of-thought는 노출하지 않는다. 대신 안전한 progress label, observation, source title, 기준 날짜, 한계를 보여준다.
- empty state는 active chat state보다 표현력이 있어도 되지만, composer로 바로 이어져야 한다.
- error state는 무엇이 실패했는지 설명하고 가능한 경우 retry/resend 경로를 남긴다.

## Tool Cards

Tool card는 evidence-forward여야 한다.

- title과 lucide icon
- running/completed/failed status
- 짧은 summary
- 유용할 때 compact grid로 key field 표시
- 가능한 경우 evidence snippet, source name, timestamp, source URL 표시
- data가 있는 척하지 않는 명확한 failed state

새 card pattern을 만들기 전에 `ToolCardShell`과 기존 card utility를 먼저 사용한다.

## 접근성과 상호작용

- semantic button/link를 사용한다.
- icon-only control에는 accessible name을 준다.
- focus state는 보이게 유지한다.
- 주요 interactive control은 가능한 44px 이상의 tap target을 가진다.
- hover에만 의존하지 않는다.
- metadata가 아니라면 body text는 최소 14px로 유지한다. 중요한 본문을 작게 만들지 않는다.
- 한국어 가독성을 위해 line-height는 1.45-1.65 정도를 사용한다.
- motion은 entering, updating, loading, completing 상태를 명확히 할 때만 사용한다. 짧게 유지하고 reduced motion을 존중한다.

## 검증

코드 변경 뒤 `frontend/`에서 실행한다.

```bash
pnpm lint
pnpm typecheck
```

시각 변경이라면 가능할 때 앱도 실행한다.

```bash
pnpm dev
```

375px 전후의 mobile 폭과 1180-1440px 전후의 desktop 폭을 확인한다.

성능 관련 변경이라면 `vercel-react-best-practices.md`를 기준으로 waterfall, bundle, data fetching, re-render 관점도 함께 확인한다.
