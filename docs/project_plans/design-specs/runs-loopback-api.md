---
title: "Design Spec: Runs Viewer — Live Loopback API (OQ-6 / FR-11)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: promoted
created: 2026-06-19
updated: 2026-06-22
prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
feature_slug: runs-frontend
deferred_from: runs-frontend-v1
deferred_item_id: OQ-6
category: scope-cut
owner: nick
related_docs:
  - docs/dev/architecture/adr-runs-read-path.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/design-specs/runs-auth-lan.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
---

# Design Spec: Runs Viewer — Live Loopback API (OQ-6 / FR-11)

> **Maturity: promoted** (June 2026) — Design and implementation complete. The loopback API (`rf serve`) is now a supported feature shipped in `runs-loopback-api-v1`. See the PRD and implementation plan for execution details.

---

## Implementation Summary

| Field | Value |
|-------|-------|
| **Promoted from** | `runs-frontend-v1` (Phase 5, deferred as OQ-6) |
| **Promoted to** | `runs-loopback-api-v1` (Phase P7, June 2026) |
| **Status** | Shipped and integrated with the runs-viewer SPA |
| **PRD** | `docs/project_plans/PRDs/features/runs-loopback-api-v1.md` |
| **Implementation plan** | `docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md` |

---

## Flag Status

The SPA fetch client is structured behind a **`RUNS_FRONTEND_LOOPBACK_API`**
environment variable (set at build time). When the flag is unset (default), the
SPA loads `run.json` files from a static directory. When the flag is set to a
base URL (e.g. `http://localhost:7432`), the same React Query hooks route
requests to the live API instead.

This means the component layer is **already decoupled** from the read path.
Implementing the loopback API requires:
1. A Python `rf serve` command (or `rf run serve`) that reads from disk on
   demand and applies the same sensitivity gate as the export service.
2. Client-layer wiring in `frontend/runs-viewer/src/api/` to switch from
   static-file URLs to `${RUNS_FRONTEND_LOOPBACK_API}/runs/…`.
3. No component-level changes.

---

## Implementation (v1.0)

### API Surface

Minimal REST API for the runs viewer's data needs:

| Endpoint | Method | Purpose | Response Shape |
|----------|--------|---------|-----------------|
| `/api/runs` | GET | Index all runs | `RFRunSummary[]` (same as `rf run list --json`) |
| `/api/runs/{run_id}` | GET | Full run export | `RFRunExport` (same as `run.json`) |
| `/api/runs/{run_id}/claims` | GET | Claim ledger for run | `Claim[]` |
| `/api/runs/{run_id}/sources/{source_card_id}` | GET | Resolve a source card | `RFResolvedSource \| null` |
| `/data/governance.json` | GET | Governance config snapshot | `GovernanceConfig` |
| `/health` | GET | Liveness probe | `{"status": "ok"}` |

No mutation endpoints — read-only invariant preserved.

### Sensitivity Gate

Same threshold model as the export service. The API applies redaction at the response-serialization layer, not in the client. All responses route through `export_service.export_run()` or `export_service.list_runs()` — no raw file reads.

### Process Model

- `rf serve --port PORT [--bind-host HOST] [--auth-mode auth-mode]` as a long-running foreground process
- Optional `[serve]` extra in `pyproject.toml`: `pip install research-foundry[serve]` for FastAPI and Uvicorn
- `systemd/rf-serve.service` provided for deployment on `agentic-nuc`
- Default port: `7432` (deconflicts from MeatyWiki `8765`)

### Hot-Reload Strategy

v1.0 uses simple per-request disk reads (no caching). Correct and operationally transparent at current scale. Filesystem-watch hot-reload caching deferred to v2 (see Deferred section).

### Auth & LAN Exposure

Coordinated with design spec `runs-auth-lan.md` (promoted v1.0):
- Loopback-only by default (`127.0.0.1:7432`, no auth)
- LAN exposure to `0.0.0.0` is opt-in: `--bind-host 0.0.0.0 --auth-mode token` with `RF_SERVE_TOKEN` env var
- Fail-closed bind check: server exits non-zero if `bind_host=0.0.0.0` but no token configured
- IP allowlist: optional `viewer.allowlist` config key

### Flag Wiring

`VITE_RUNS_FRONTEND_LOOPBACK_API` (set at SPA build time) controls read path:
- Unset (default): SPA loads from static `run.json` files
- `true`: SPA loads from live API at `VITE_RUNS_LOOPBACK_API_BASE` (default: `http://127.0.0.1:7432/api`)
- Static export and live API co-exist — operator can use either or both

---

## Deferred (v2)

### DEF-03: Filesystem-Watch Hot-Reload Cache

**Rationale**: v1.0 reads disk on every request. For large run corpora (500+ runs), this scales linearly and may show latency. Filesystem-watch invalidation (inotify/watchdog) adds a dependency and invalidation bugs; not justified v1.

**Promotion trigger**: Run corpus exceeds ~500 runs **or** operator observes visible per-request latency (>1s on typical hardware).

**Implementation sketch**: Wrap `export_service` responses in a caching layer; invalidate on filesystem change events from the run directory.
