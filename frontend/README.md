# Baseball Agent Frontend

Next.js App Router 기반의 야구 특화 Agent 채팅 UI입니다. 현재 단계에서는 FSD-inspired 폴더 구조, styled-components SSR, Jotai, TanStack React Query, TanStack Virtual 의존성, 로그인/프로필 모달, 출처 패널, Tool 결과 카드의 기본 골격을 제공합니다.

## Stack

- Next.js 16
- React 19
- TypeScript
- pnpm
- styled-components
- Jotai
- TanStack React Query
- TanStack React Virtual

## Commands

```bash
pnpm dev
pnpm lint
pnpm typecheck
pnpm build
pnpm format
```

## Local Development

```bash
pnpm dev --hostname 127.0.0.1 --port 3001
```

Then open http://127.0.0.1:3001.

## Architecture

This project uses `src/views` as the FSD page layer because Next.js reserves `src/app` for App Router and treats `src/pages` as Pages Router routes.

See `docs/stack-decisions.md` for the stack rationale and state ownership rules.
