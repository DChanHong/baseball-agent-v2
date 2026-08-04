# Vercel React Best Practices 적용 메모

## 목적

이 문서는 Vercel Engineering의 `vercel-react-best-practices` / `react-best-practices` skill을 Baseball Agent frontend에 맞게 압축한 참조 문서다. 원문은 React/Next.js 성능 최적화 규칙을 우선순위별로 정리한 agent용 guide다.

원문 전체를 복사하지 않는다. 이 프로젝트에서는 UI 품질 스킬을 가볍게 유지하고, 성능 리뷰가 필요한 경우 아래 우선순위만 적용한다.

## 언제 읽을 것

- React component를 새로 만들거나 크게 refactor할 때
- chat streaming, message list, tool card rendering, source drawer처럼 자주 갱신되는 UI를 바꿀 때
- data fetching, route/page 구성, Server Component/Client Component 경계를 바꿀 때
- bundle size, lazy loading, dynamic import, icon import, third-party library 사용을 바꿀 때
- 성능 리뷰 또는 PR review를 요청받았을 때

## 이 프로젝트의 기본 해석

- 이 앱은 Next.js App Router 기반이지만 현재 주요 화면은 client interaction이 많은 chat UI다.
- 성능 최적화는 UX 신뢰성을 깨지 않는 범위에서 적용한다. loading/error/evidence 상태가 사라지면 안 된다.
- 새 dependency를 추가하는 최적화보다 기존 구조에서 waterfall, bundle, render 낭비를 줄이는 것을 우선한다.
- TanStack Query를 이미 사용하므로 client fetching dedup은 SWR 도입보다 React Query cache/query key/retry 설계를 우선 검토한다.
- `lucide-react`를 사용할 때는 프로젝트 설정과 번들 결과를 고려한다. 필요한 경우 Next config의 `optimizePackageImports` 또는 직접 import 전략을 검토한다.

## 성능 리뷰 우선순위

1. Waterfall 제거
   - 독립적인 async 작업은 동시에 시작하고 `Promise.all`로 기다린다.
   - cheap sync guard가 실패하면 async 작업을 시작하지 않는다.
   - 필요한 branch 안으로 `await`를 미룬다.
   - route handler/server action에서는 promise를 일찍 시작하고 늦게 await한다.

2. Bundle size 줄이기
   - barrel import가 큰 library를 불필요하게 끌어오는지 확인한다.
   - 무거운 component, modal, drawer, chart, editor는 실제 사용 시점에 load할 수 있는지 본다.
   - analytics/logging 같은 third-party script는 critical path 뒤로 미룬다.
   - 사용자의 hover/focus 등 intent가 보이면 preload할 수 있는지 검토한다.

3. Server-side performance
   - Server Component에서 client로 넘기는 props를 최소화한다.
   - request별 mutable module state를 만들지 않는다.
   - 같은 request 안에서 반복되는 비싼 작업은 `React.cache()` 같은 per-request dedup 가능성을 검토한다.
   - nested data fetching은 가능한 병렬화한다.

4. Client-side data fetching
   - React Query query key가 안정적인지 확인한다.
   - 같은 데이터를 여러 component가 중복 요청하지 않는지 확인한다.
   - `localStorage` 데이터는 version을 두고 최소화한다.
   - global event listener는 중복 등록하지 않고 cleanup한다.
   - scroll/touch listener는 필요한 경우 passive listener를 고려한다.

5. Re-render 줄이기
   - render 중 계산 가능한 derived state를 `useEffect + useState`로 다시 만들지 않는다.
   - 단순 primitive 계산에는 `useMemo`를 남발하지 않는다.
   - expensive calculation이나 큰 list transform은 의존성을 좁혀 memoization을 검토한다.
   - component 안에서 component를 정의하지 않는다. 필요한 값은 props로 전달한다.
   - state update는 이전 state에 의존하면 functional setState를 사용한다.
   - expensive initial state는 `useState(() => initialValue)`로 lazy init한다.
   - input 반응성을 해치는 non-urgent update는 `startTransition` 또는 `useDeferredValue`를 검토한다.
   - 자주 바뀌지만 렌더링에 필요 없는 값은 `useRef`로 둔다.

6. Rendering performance
   - 긴 message list는 virtualization 또는 `content-visibility`를 검토한다.
   - static JSX는 component 밖으로 빼도 되는지 본다.
   - 조건부 렌더링은 `condition ? <A /> : null`처럼 명시한다. `0 && <A />` 노출을 피한다.
   - hydration mismatch는 구조적으로 없애고, 정말 예상 가능한 mismatch에만 suppress를 사용한다.
   - motion은 SVG 자체보다 wrapper를 움직이는 쪽이 안전한 경우가 많다.

7. JavaScript hot path
   - 같은 array에 `filter/map/find`를 여러 번 도는 경우 한 번의 loop나 `Map`/`Set`으로 줄일 수 있는지 본다.
   - 반복 lookup은 `Map` 또는 `Set`으로 바꿀 수 있는지 본다.
   - 정렬이 필요 없는 min/max는 sort 대신 loop를 쓴다.
   - non-critical work는 `requestIdleCallback` 또는 scheduling을 검토한다.

## 코드 리뷰 때 남길 말의 형태

성능 지적은 추상적으로 하지 않는다. 다음 네 가지를 짧게 포함한다.

- 어떤 category인지: waterfall, bundle, server, client fetching, re-render, rendering, JS hot path
- 어떤 파일/컴포넌트에서 발생하는지
- 사용자에게 어떤 영향이 있는지: waiting time, jank, input delay, bundle 증가, repeated work
- 이 프로젝트 구조에서 가장 작은 수정은 무엇인지

## 원문 참조

- Vercel blog: `https://vercel.com/blog/introducing-react-best-practices`
- Skill source: `https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/react-best-practices/SKILL.md`
- Full guide: `https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/react-best-practices/AGENTS.md`
