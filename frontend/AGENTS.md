<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Baseball Agent Frontend 규칙

- 목적: KBO 직관용 chat assistant 웹 클라이언트. 경기, 구장, 날씨, 좌석, 예매, 출처 정보를 대화와 tool card로 보여준다.
- 구조: Next.js App Router + FSD-inspired layers. 자세한 구조는 `../docs/frontend/folder-design.md`, 스택 결정은 `docs/stack-decisions.md`를 읽는다.
- 상세 UI/성능 기준은 `.codex/skills/baseball-frontend-ui/SKILL.md`와 `references/` 문서를 필요할 때만 읽는다.
- TypeScript 또는 React 코드를 바꿨다면 이 폴더에서 `pnpm lint`, `pnpm typecheck`로 검증한다.
