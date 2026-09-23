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

### Canonical-claim merge review

The Claim Audit Workbench's canonical-claim merge-review section (grouping
sibling claims under a shared `persistent_references.canonical_claim_id`) is
gated behind `VITE_RF_CANONICAL_CLAIMS_ENABLED=true` at build time — see
`src/lib/canonicalClaimsFlag.ts`. Default (unset/anything other than
`"true"`) is **disabled** (fail-closed): the section is absent, not a
disabled/empty control. Independent of Mode A/B above; combine with either.

```sh
VITE_RF_CANONICAL_CLAIMS_ENABLED=true pnpm build
```

Start the backend:

```sh
rf serve                         # loopback, port 7432, no auth
rf serve --port 7432             # explicit (same as default)
```

Build the frontend in live-proxy mode, then serve it from the same process:

```sh
VITE_RUNS_FRONTEND_LOOPBACK_API=true pnpm build
RUNS_VIEWER_API_URL=http://127.0.0.1:7432 \
RUNS_VIEWER_API_TOKEN=<server-only-read-token> pnpm preview
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_RUNS_FRONTEND_LOOPBACK_API` | No | `false` | Set to `"true"` to enable loopback mode (Mode B). |
| `VITE_RUNS_LOOPBACK_API_BASE` | No | `/api` | Explicit API URL for local development only. Leave unset for a LAN deployment so browser fetches stay same-origin. |
| `RUNS_VIEWER_API_URL` | No | `http://127.0.0.1:7432` | Runtime API origin used only by the Vite dev/preview proxy. |
| `RUNS_VIEWER_API_TOKEN` | Conditional | _(unset)_ | Runtime read-scoped credential added by the Vite proxy. It is never a `VITE_*` variable and is never embedded in the SPA. **Never commit this value.** |
| `VITE_RF_CANONICAL_CLAIMS_ENABLED` | No | `false` | Set to `"true"` to enable the canonical-claim merge-review section in the Claim Audit Workbench (`src/lib/canonicalClaimsFlag.ts`). Fail-closed default: absent, not disabled. |

### Deploy-flag wiring (agentic-node bootstrap)

`VITE_RUNS_FRONTEND_LOOPBACK_API` is not set by hand at deploy time — the
agentic-node bootstrap script (`agentic_meta_dev/infra/agentic-node/bootstrap-agentic-node.sh`,
outside this repo) reads its own `RF_UI_LOOPBACK` toggle (default `true`) and
must translate it into `VITE_RUNS_FRONTEND_LOOPBACK_API=true` on the build and
`RUNS_VIEWER_API_URL` plus `RUNS_VIEWER_API_TOKEN` on the preview-server process.
It must no longer pass `VITE_RUNS_LOOPBACK_API_TOKEN`. `VITE_RF_CANONICAL_CLAIMS_ENABLED`
follows the same convention: this repo lands the Vite-side env var and its
consumer (`canonicalClaimsFlag.ts`, this file); the bootstrap-side mirror —
translating a `RF_CANONICAL_CLAIMS` (or equivalent) toggle into
`VITE_RF_CANONICAL_CLAIMS_ENABLED=true` alongside the existing `RF_UI_LOOPBACK`
block in `bootstrap-agentic-node.sh` — is a **cross-repo follow-up**, not yet
landed as of assertion-ledger-activation-v1 P5 (that script lives in the
separate `agentic_meta_dev` repo, out of scope for this repo's worktree). To be
tracked and closed out in P6-05 (CHANGELOG + docs phase), not this phase.

### Loopback mode examples

**Default loopback (same machine):**

```sh
VITE_RUNS_FRONTEND_LOOPBACK_API=true \
  pnpm build
# Uses the viewer's same-origin /api proxy.
```

**LAN exposure (agentic-nuc, auth_mode=token):**

```sh
# On the server — start with LAN bind and token auth:
RF_SERVE_TOKEN=<secret> rf serve \
  --bind-host 0.0.0.0 \
  --auth-mode token

# Build the SPA to request its same-origin /api path (no token is passed here):
VITE_RUNS_FRONTEND_LOOPBACK_API=true \
  pnpm build

# Start the LAN viewer on :3030. The Vite process, not the browser, holds the
# read-scoped credential and proxies /api to the loopback RF server.
RUNS_VIEWER_API_URL=http://127.0.0.1:7432 \
RUNS_VIEWER_API_TOKEN=<server-only-read-token> \
  pnpm preview
```

**Custom port:**

```sh
rf serve --port 9000

VITE_RUNS_FRONTEND_LOOPBACK_API=true \
  pnpm build

RUNS_VIEWER_API_URL=http://127.0.0.1:9000 pnpm preview
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
