# RF Runs Viewer

Vite + React SPA for browsing Research Foundry runs.

## Modes

### Mode A — Static (default)

Pre-exported run data served from `public/data/`.  No backend required.  Used
for the default deployment on agentic-nuc (`http://10.42.10.76:3030`).

Build and serve:

```sh
pnpm build
pnpm preview          # or: vite preview
```

### Mode B — Live Loopback API

Fetches live data from a running `rf serve` instance.  Activated by setting
`VITE_RUNS_FRONTEND_LOOPBACK_API=true` at build time.

Start the backend:

```sh
rf serve                         # loopback, port 7432, no auth
rf serve --port 7432             # explicit (same as default)
```

Build the frontend pointed at it:

```sh
VITE_RUNS_FRONTEND_LOOPBACK_API=true pnpm build
pnpm preview
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_RUNS_FRONTEND_LOOPBACK_API` | No | `false` | Set to `"true"` to enable loopback mode (Mode B). |
| `VITE_RUNS_LOOPBACK_API_BASE` | No | `http://127.0.0.1:7432/api` | Override the loopback API base URL. Use the LAN address when `rf serve` is exposed on `0.0.0.0`. |
| `VITE_RUNS_LOOPBACK_API_TOKEN` | Conditional | _(unset)_ | Shared-secret token for `rf serve --auth-mode token`. Injected at Vite build time; omit the env var entirely when `auth_mode=none`. **Never commit this value.** |

### Loopback mode examples

**Default loopback (same machine):**

```sh
VITE_RUNS_FRONTEND_LOOPBACK_API=true \
  pnpm build
# Uses http://127.0.0.1:7432/api
```

**LAN exposure (agentic-nuc, auth_mode=token):**

```sh
# On the server — start with LAN bind and token auth:
RF_SERVE_TOKEN=<secret> rf serve \
  --bind-host 0.0.0.0 \
  --auth-mode token

# Build the SPA pointed at the LAN address:
VITE_RUNS_FRONTEND_LOOPBACK_API=true \
VITE_RUNS_LOOPBACK_API_BASE=http://10.42.10.76:7432/api \
VITE_RUNS_LOOPBACK_API_TOKEN=<secret> \
  pnpm build
```

**Custom port:**

```sh
rf serve --port 9000

VITE_RUNS_FRONTEND_LOOPBACK_API=true \
VITE_RUNS_LOOPBACK_API_BASE=http://127.0.0.1:9000/api \
  pnpm build
```

## Port

`rf serve` defaults to port **7432**.  This avoids collisions with:

- MeatyWiki Portal API: `8765`
- IntentTree API: `8032`
- SkillMeat API: `8080`
- Research Foundry runs-viewer SPA: `3030`

## Development

```sh
pnpm install
pnpm dev       # Vite dev server (static mode)
pnpm test      # Vitest unit tests
pnpm e2e       # Playwright end-to-end tests
```
