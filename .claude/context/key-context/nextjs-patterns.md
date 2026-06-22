# runs-viewer (Vite SPA) Patterns

> **Note**: Research Foundry does NOT use Next.js. The frontend is a Vite + React 18 SPA.

## Location

`frontend/runs-viewer/` — standard Vite project with React plugin.

## Source layout

```
src/
├── main.tsx            # Vite entry
├── app/               # App.tsx, AppShell, routes, providers
├── api/
│   ├── client.ts      # Dual-mode GET client (static fixtures OR loopback fetch)
│   └── queryClient.ts # React Query instance
├── components/        # Feature-grouped: RunList/, RunDetail/, ClaimLedger/,
│                      #   LineageGraph/, TrustPanel/, SourceCard/, ReportOverlay/, etc.
├── hooks/             # useRunList, useRunDetail, useClaimLedger, useSourceCard
├── screens/           # Page-level components (RunList, RunDetail, Swarm, Library …)
├── lib/               # Utilities (format, runs, viewerSettings, auditStateMachine)
├── types/rf/          # Generated TS types mirroring Python schemas
└── styles/            # Plain CSS (tokens.css + per-feature sheets)
```

## API client (`api/client.ts`)

- **Static mode** (default): fetches `public/data/index.json` + per-run `run.json`
- **Loopback mode**: enabled by `VITE_RUNS_FRONTEND_LOOPBACK_API=true`; fetches from `rf serve` (port 7432)
- Auth: sends `Authorization: Bearer <token>` only when `VITE_RUNS_LOOPBACK_API_TOKEN` is set

## Key conventions

- No SSR, no server components — pure client-side React
- CSS class prefix: `rv-` (runs-viewer) / `it-` (shared tokens)
- Tests: Vitest under `src/test/`
