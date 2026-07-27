# Frontend Stack Decisions

## Scope

The frontend starts as a single-page chat application for a baseball-specific agent. Login and profile settings are modal flows. Agent tool results are rendered as structured chat cards instead of plain text whenever possible.

## Decisions

| Area            | Choice                 | Why                                                                                                                               |
| --------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Framework       | Next.js App Router     | Good fit for deployment, streaming-ready UI, metadata, route handlers, and a portfolio-grade React architecture.                  |
| Language        | TypeScript             | Tool results, chat messages, citations, and recommendation cards need stable contracts.                                           |
| Package manager | pnpm                   | Fast installs, strict dependency handling, and clean future workspace support.                                                    |
| Styling         | styled-components      | Keeps component styling close to FSD feature boundaries and supports a custom baseball-agent design system.                       |
| Client state    | Jotai                  | Small UI state such as modals, source drawer, selected game, and input draft can stay atomic and local.                           |
| Server state    | TanStack React Query   | API data, conversation history, profile mutations, retries, and cache invalidation should not live in client UI atoms.            |
| Long lists      | TanStack React Virtual | Chat history and tool-heavy messages can become expensive; the message list is structured so virtualization can be added cleanly. |
| Architecture    | FSD-inspired layers    | Widgets, features, entities, and shared code make tool-result UI easier to evolve by domain.                                      |

## FSD Folder Note

Next.js reserves `src/app` for routing and also treats `src/pages` as Pages Router routes. To avoid router conflicts, this project uses `src/views` for the FSD page layer.

```text
src/
├── app/       # Next.js routing and app-level providers
├── views/     # FSD page layer, renamed to avoid Next.js pages router conflict
├── widgets/   # composed UI blocks such as chat panel, header, source drawer
├── features/  # user actions such as auth, profile, send-message, select-game
├── entities/  # domain UI and types such as message, game, seat, citation
└── shared/    # reusable api, config, styles, types, ui, lib
```

## State Ownership

- Jotai owns UI state only.
- React Query owns data fetched from the backend.
- Streaming events will use a dedicated hook, then reconcile completed messages into React Query cache.
- Tool result components should receive typed data and avoid knowing transport details.
