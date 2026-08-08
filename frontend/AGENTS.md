<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Baseball Agent Frontend 규칙

- 이 frontend는 KBO 직관용 chat assistant이지 marketing site가 아니다. 장식보다 compact하고 신뢰 가능한 evidence-forward UI를 우선한다.
- `../docs/frontend/folder-design.md`, `docs/stack-decisions.md`에 정리된 FSD-inspired 구조를 따른다: `app`, `views`, `widgets`, `features`, `entities`, `shared`.
- component-local color, radius, shadow 값을 새로 넣기 전에 `styled-components`와 `src/shared/styles/theme.ts` token을 먼저 사용한다.
- Jotai는 local UI state에, TanStack Query는 server state에 사용한다. domain UI component는 transport detail을 몰라야 한다.
- agent tool output은 typed source-aware card로 렌더링한다. 가능한 경우 running, completed, failed, empty, evidence 상태를 보여준다.
- UI control과 status에는 특별한 이유가 없으면 emoji나 custom inline SVG 대신 `lucide-react` icon을 사용한다.
- TypeScript 또는 React 코드를 바꿨다면 이 폴더에서 `pnpm lint`, `pnpm typecheck`로 검증한다.
- 더 깊은 UI/UX 작업에는 가능하면 project Codex skill인 `.codex/skills/baseball-frontend-ui`를 사용한다.
