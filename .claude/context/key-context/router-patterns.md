# FastAPI Router Patterns — Research Foundry

**Scope**: The RF read-only loopback API at `src/research_foundry/api/`

## App factory (`api/app.py`)

`create_app(config: FoundryConfig) → FastAPI` wires:
- **CORS** (outermost) — localhost origins by default; configurable via `viewer.cors_origins`
- **IP allowlist** (optional) — `IPAllowlistMiddleware` when `viewer.allowlist` is non-empty
- **Token auth** (optional) — `TokenAuthMiddleware` when `viewer.auth_mode == "token"`
- `/health` — always unauthenticated liveness probe
- `/data/governance.json` — governance config snapshot
- `/api` prefix → `routers/runs.py`

## Runs router (`api/routers/runs.py`)

All endpoints are **GET-only**; data routed through `export_service` (R1 invariant):

| Endpoint | Returns |
|----------|---------|
| `GET /api/runs` | `list_runs(paths)` — array of run summaries |
| `GET /api/runs/{run_id}` | `export_run(paths, run_id)` — full denormalized export |
| `GET /api/runs/{run_id}/claims` | Claims array from the export |
| `GET /api/runs/{run_id}/sources/{sc_id}` | Single resolved source card |

Dependency injection: `get_paths()` resolves `FoundryPaths` from `FoundryConfig.load()`.

## Middleware

- **`middleware/auth.py`** — `TokenAuthMiddleware`: reads expected token from env var at request time; uses `hmac.compare_digest` (constant-time). `/health` always exempt. Fail-closed: missing env var → 401.
- **`middleware/allowlist.py`** — `IPAllowlistMiddleware`: frozenset membership check on `request.client.host`; rejects with 403.

## Search Router MCP

`services/search_router/mcp_server.py` exposes `run_search` / `extract_urls` as MCP tools (optional `mcp` SDK dependency; lazy import).
