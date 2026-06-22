---
title: "Implementation Plan: Runs Viewer \u2014 Live Loopback API + Gated LAN Exposure"
schema_version: 2
doc_type: implementation_plan
status: completed
created: '2026-06-22'
updated: '2026-06-22'
feature_slug: runs-loopback-api
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
plan_ref: null
scope: Add rf serve read-only FastAPI API serving the runs-viewer SPA from disk with
  loopback-first auth and gated LAN exposure via shared-secret token.
effort_estimate: 13 pts
architecture_summary: "FastAPI app factory wired to existing export_service core;\
  \ 5 read endpoints matching client.ts contract; middleware stack (CORS \u2192 optional\
  \ token auth \u2192 optional IP allowlist); Typer CLI command; optional [serve]\
  \ extra in pyproject.toml."
related_documents:
- docs/project_plans/PRDs/features/runs-loopback-api-v1.md
- docs/project_plans/design-specs/runs-loopback-api.md
- docs/project_plans/design-specs/runs-auth-lan.md
- docs/dev/architecture/adr-runs-read-path.md
- docs/dev/architecture/rf-run-export-schema.md
- frontend/runs-viewer/src/api/client.ts
- .claude/worknotes/runs-loopback-api/decisions-block.md
references:
  user_docs: []
  context: []
  specs: []
  related_prds:
  - docs/project_plans/PRDs/features/runs-frontend-v1.md
spike_ref: null
adr_refs:
- docs/dev/architecture/adr-runs-read-path.md
deferred_items_spec_refs:
- docs/project_plans/design-specs/runs-auth-lan.md
- docs/project_plans/design-specs/runs-loopback-api.md
findings_doc_ref: .claude/findings/runs-loopback-api-findings.md
charter_ref: null
changelog_ref: CHANGELOG.md
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: medium
risk_level: medium
category: features
tags:
- implementation
- api
- runs-viewer
- loopback
- fastapi
- auth
- lan
milestone: null
commit_refs:
- 33b6bcf
pr_refs: []
files_affected:
- src/research_foundry/api/__init__.py
- src/research_foundry/api/app.py
- src/research_foundry/api/routers/runs.py
- src/research_foundry/api/middleware/auth.py
- src/research_foundry/api/middleware/allowlist.py
- src/research_foundry/cli_commands.py
- src/research_foundry/config.py
- pyproject.toml
- frontend/runs-viewer/src/api/client.ts
- tests/test_serve_api.py
- tests/test_serve_auth.py
- tests/test_serve_cli.py
- systemd/rf-serve.service
- docs/dev/architecture/adr-runs-read-path.md
- CHANGELOG.md
wave_plan:
  serialization_barriers:
  - src/research_foundry/config.py
  - frontend/runs-viewer/src/api/client.ts
  phases:
  - id: P1
    depends_on: []
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - src/research_foundry/api/__init__.py
    - src/research_foundry/api/app.py
    - src/research_foundry/cli_commands.py
    - pyproject.toml
  - id: P2
    depends_on:
    - P1
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - src/research_foundry/api/routers/runs.py
  - id: P3
    depends_on:
    - P1
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - src/research_foundry/config.py
  - id: P4
    depends_on:
    - P2
    - P3
    isolation: worktree
    parallelizable: false
    owner_skills: []
    files_affected:
    - src/research_foundry/api/middleware/auth.py
    - src/research_foundry/api/middleware/allowlist.py
    - src/research_foundry/api/app.py
  - id: P5
    depends_on:
    - P4
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - frontend/runs-viewer/src/api/client.ts
  - id: P6
    depends_on:
    - P5
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - tests/test_serve_api.py
    - tests/test_serve_auth.py
    - tests/test_serve_cli.py
  - id: P7
    depends_on:
    - P6
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - systemd/rf-serve.service
    - docs/dev/architecture/adr-runs-read-path.md
    - docs/project_plans/design-specs/runs-loopback-api.md
    - docs/project_plans/design-specs/runs-auth-lan.md
    - CHANGELOG.md
  waves:
  - - P1
  - - P2
    - P3
  - - P4
  - - P5
  - - P6
  - - P7
---

# Implementation Plan: Runs Viewer — Live Loopback API + Gated LAN Exposure

**Plan ID**: `IMPL-2026-06-22-RUNS-LOOPBACK-API`
**Date**: 2026-06-22
**Author**: Claude Sonnet 4.6 (implementation-planner)
**Human Brief**: `docs/project_plans/human-briefs/runs-loopback-api.md`
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/runs-loopback-api-v1.md`
- **Decisions Block**: `.claude/worknotes/runs-loopback-api/decisions-block.md`
- **ADR**: `docs/dev/architecture/adr-runs-read-path.md`
- **Export Schema**: `docs/dev/architecture/rf-run-export-schema.md`
- **Design Specs (to promote)**: `docs/project_plans/design-specs/runs-loopback-api.md`, `docs/project_plans/design-specs/runs-auth-lan.md`

**Complexity**: Medium (13 pts, Tier 2 boundary)
**Total Estimated Effort**: 13 story points
**Target Timeline**: ~2 weeks (sequential critical path; P2/P3 parallel in wave 2)

---

## Executive Summary

Add a read-only FastAPI HTTP server (`rf serve`) that serves the runs-viewer SPA's five live endpoints from disk, routing all data through the existing `export_service` sensitivity gate. The server binds to loopback (`127.0.0.1:7432`) by default with no auth; LAN exposure on `0.0.0.0` is a gated opt-in that fails closed if a shared-secret token is absent. The SPA's already-built dual-mode `client.ts` activates without component changes — only `VITE_RUNS_FRONTEND_LOOPBACK_API=true` is required. Implementation follows the critical path P1→P2/P3→P4→P5→P6→P7 with P4 using an isolated worktree for the security-sensitive auth middleware.

---

## Implementation Strategy

### Architecture Sequence

This feature does not follow the standard DB→Repository→Service→API→UI layering because there is no new database layer — it wraps an existing service core. The sequence is:

1. **API Foundation (P1)** — FastAPI app factory + CORS + `rf serve` Typer command + `[serve]` optional extra
2. **Read Endpoints (P2)** ∥ **Config Wiring (P3)** — 5 read endpoints wrapping `export_service`; `viewer.*` config keys
3. **Auth & LAN Gating (P4)** — Token middleware, fail-closed bind, IP allowlist, threat model (isolated worktree)
4. **Frontend Integration (P5)** — `client.ts` auth-header wiring; env-config docs; seam verification
5. **Testing (P6)** — Endpoint contract, sensitivity parity, auth, fail-closed, CLI tests
6. **Deploy & Docs (P7)** — systemd unit, ADR, README, CHANGELOG, spec promotion

### Parallel Work Opportunities

- **Wave 2**: P2 (api/routers/runs.py) and P3 (config.py) are disjoint files and can execute concurrently after P1 lands.
- **P4 backend** and **P5 prep reading** are NOT safe to parallelize — FE needs the auth-header contract finalized in P4 before client.ts is touched.

### Critical Path

P1 → P2 → P4 → P5 → P6 → P7

P3 is on a parallel rail (P1→P3→P4); it gates P4 but not P2.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model | Notes |
|-------|-------|----------|--------------------|-------|-------|
| P1 | API Foundation | 2 pts | python-backend-engineer | sonnet/adaptive | App factory + Typer command + extras packaging |
| P2 | Read Endpoints | 3 pts | python-backend-engineer | sonnet/adaptive | 5 endpoints via export_service; parallel with P3 |
| P3 | Config & Flag Wiring | 1.5 pts | python-backend-engineer | sonnet/adaptive | viewer.* config keys; parallel with P2 |
| P4 | Auth & LAN (gated) | 2.5 pts | python-backend-engineer + senior-code-reviewer | sonnet/extended | Security surface; isolated worktree; karen checkpoint |
| P5 | Frontend Integration | 1 pt | ui-engineer | sonnet/adaptive | client.ts auth-header only; seam verification |
| P6 | Tests | 2 pts | python-backend-engineer | sonnet/adaptive | TestClient + CliRunner; all auth/sensitivity paths |
| P7 | Deploy & Docs | 1 pt | documentation-writer + python-backend-engineer | haiku/adaptive + sonnet/adaptive | ADR/CHANGELOG/specs (haiku); systemd unit (sonnet) |
| **Total** | — | **13 pts** | — | — | — |

> Estimation rationale lives in the Human Brief `docs/project_plans/human-briefs/runs-loopback-api.md` §2.

### Estimation Sanity Check

**Noun count (H1)**: 0 new database tables → H1 does not apply. No new CRUD domain nouns.

**Dual-impl multiplier (H2)**: Not applicable — no repository layer; wraps existing `export_service`.

**Algorithmic flag (H3)**: Not flagged. The API is mechanical routing; no dependency resolution, graph traversal, or ranking logic. Token comparison is constant-time (stdlib `hmac.compare_digest`), not algorithmic.

**Bundle decomposition (H4)**: Two bundled capability areas — loopback API (OQ-6) and gated LAN auth (OQ-4):

| Area | Independent Estimate | Notes |
|------|---------------------|-------|
| Loopback API (P1+P2+P3+P5) | 7.5 pts | App factory, 5 endpoints, config, FE seam |
| Auth & LAN gating (P4) | 2.5 pts | Middleware + fail-closed + allowlist + threat model |
| Testing (P6) | 2 pts | Covers both areas; not compressible |
| Deploy & Docs (P7) | 1 pt | systemd + ADR + CHANGELOG + spec promotion |
| **Σ** | **13 pts** | Plan total = Σ; no compression applied |

**Anchor (H5)**: `runs-frontend-v1` export service (P1) — the `export_run`/`list_runs` core this API wraps — cost ~2 pts for the service layer alone, anchoring P2 at 3 pts for 5 endpoints that reuse it. The Search Router CLI addition (`rf search`) anchors P1's Typer command at 2 pts. This plan's delta vs anchor: within ±20%; justified by the security surface in P4 (no analog in either anchor).

**Plumbing budget (H6)**: ~1.5 pts folded into P1/P3 (CORS middleware, `[serve]` extras packaging, config defaults, DI injection, FE env-var flag documentation). Approximately 12% of subtotal — within the 15–20% guideline.

**Bottom-up total**: 13 pts
**Top-down intuition**: 12–14 pts
**Locked estimate**: 13 pts (agrees)

---

## Deferred Items & In-Flight Findings Policy

### Deferred Items

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-----------------|
| DEF-01 | scope-cut | mTLS auth mode: requires certificate provisioning infrastructure absent on agentic-nuc; disproportionate to operator threat model | Promoted when agentic-nuc gets a certificate authority or operator requests mutual-TLS setup | `docs/project_plans/design-specs/runs-auth-lan.md` (annotate in-file; DOC-006 promotes the spec) |
| DEF-02 | scope-cut | SSH-tunnel auth mode: token-over-loopback covers the threat adequately for v1; SSH plumbing in the server is out of scope | Promoted when operator uses agentic-nuc from an untrusted network where SSH-tunnel is preferred over exposed token | `docs/project_plans/design-specs/runs-auth-lan.md` (same spec; annotate deferred section) |
| DEF-03 | scope-cut | Filesystem-watch hot-reload cache: per-request disk reads are correct and simple at operator scale; inotify/watchdog dep + invalidation bugs not worth v1 | Promoted when run corpus exceeds ~500 runs or operator reports visible latency from per-request reads | `docs/project_plans/design-specs/runs-loopback-api.md` (annotate deferred v2 section) |

**DOC-006 tasks for each deferred item are specified in Phase P7 below.**

### In-Flight Findings

Findings doc is NOT pre-created. Create `.claude/findings/runs-loopback-api-findings.md` only on first real in-execution discovery. Set `findings_doc_ref` in frontmatter on creation.

### Quality Gate

P7 cannot be sealed until:
- All three deferred items (DEF-01, DEF-02, DEF-03) have their design-spec annotation tasks completed and the spec paths are recorded in `deferred_items_spec_refs`.
- If `findings_doc_ref` is populated, the findings doc is finalized and advanced to `accepted`.

---

## Phase Breakdown

**Column conventions**:
- `Estimate` — Task size in story points.
- `Model` — Assigned Claude model: `sonnet` | `haiku`.
- `Effort` — Reasoning budget: `adaptive` (default) | `extended` (P4 security tasks only).

---

### Phase P1: API Foundation

**Duration**: ~1 day
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer (primary)
**Wave**: 1

Reference patterns:
- Mirror `cli_commands.py` `run_export` Typer command structure.
- CORS middleware: allow `http://localhost:*` and `http://127.0.0.1:*` by default (configurable).
- Optional import guard: `try: import fastapi; import uvicorn; except ImportError: raise ImportError("fastapi and uvicorn are required. Install with: pip install 'research-foundry[serve]'")`.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P1-001 | pyproject.toml `[serve]` extra | Add `fastapi>=0.111`, `uvicorn[standard]>=0.29` as optional `[serve]` extra in `pyproject.toml`. Add import guard in `api/__init__.py` that raises a clear install error if missing. | `pip install research-foundry` (no extra) succeeds; `import research_foundry` does not import fastapi/uvicorn; `rf serve` without extra prints install hint. | 0.5 pts | python-backend-engineer | sonnet | adaptive | None |
| P1-002 | FastAPI app factory | Create `src/research_foundry/api/app.py` with `create_app(config: FoundryConfig) -> FastAPI` factory. Wire CORS middleware (default origins: `localhost:*`, `127.0.0.1:*`; configurable). Include a `GET /health` probe returning `{"status": "ok"}`. Register the runs router (stub OK; populated in P2). | `rf serve` boots; `GET /health` returns 200 `{"status":"ok"}`; CORS preflight from SPA origin returns `Access-Control-Allow-Origin` header. | 0.75 pts | python-backend-engineer | sonnet | adaptive | P1-001 |
| P1-003 | `rf serve` Typer command | Add `serve` command to `cli_commands.py` (or a new `cli_serve.py` registered in the main CLI). Accepts: `--port` (default `7432`), `--bind-host` (default `127.0.0.1`), `--auth-mode` (`none`\|`token`, default `none`), `--sensitivity-threshold` (default from config or `public`). Calls `uvicorn.run(create_app(config), host=bind_host, port=port)`. Fail-closed bind check (P4 implements middleware; P1 wires the pre-bind validation stub). | `rf serve --help` lists all flags; `rf serve` starts uvicorn on 127.0.0.1:7432; `--port 9000` overrides port. | 0.75 pts | python-backend-engineer | sonnet | adaptive | P1-002 |

**Phase P1 Quality Gates:**
- [ ] `pip install research-foundry` (no extra) does not import fastapi or uvicorn
- [ ] `rf serve` starts and `GET /health` returns 200
- [ ] CORS allows SPA origin in loopback mode
- [ ] `rf serve --help` shows all flags with correct defaults

---

### Phase P2: Read Endpoints

**Duration**: ~1.5 days
**Dependencies**: P1 complete
**Assigned Subagent(s)**: python-backend-engineer (primary)
**Wave**: 2 (parallel with P3)

**Critical invariant (Risk R1)**: ALL data responses MUST route through `export_service.export_run(paths, run_id)` or `export_service.list_runs(paths)`. The API layer must never read raw run artifact files directly or re-implement serialization. Violations bypass the sensitivity gate.

**Endpoint-to-client.ts mapping** (R-P1 compliance — target_surfaces enumerated):

| Endpoint | client.ts function | client.ts approx. line | TS return type |
|----------|--------------------|------------------------|----------------|
| `GET /api/runs` | `fetchRunList()` | ~109 | `RFRunSummary[]` |
| `GET /api/runs/{run_id}` | `fetchRunDetail()` | ~126 | `RFRunExport` |
| `GET /api/runs/{run_id}/claims` | `fetchClaimLedger()` | ~175 | `RFRunExport["claims"]` |
| `GET /api/runs/{run_id}/sources/{source_card_id}` | `fetchSourceCard()` | ~197 | `RFResolvedSource \| null` |
| `GET /data/governance.json` | `fetchGovernanceConfig()` | ~158 | `GovernanceConfig` |

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P2-001 | Runs router scaffold | Create `src/research_foundry/api/routers/runs.py`. Define a FastAPI `APIRouter` with prefix `/api`. Inject `FoundryPaths` via a dependency function that reads config. Wire router into `create_app()`. | Router registered; `GET /api/runs` returns 200 with an empty list when no runs exist; router visible in `/openapi.json`. | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-003 |
| P2-002 | `GET /api/runs` | Implement `GET /api/runs` calling `export_service.list_runs(paths)`. Returns `RFRunSummary[]` (same shape as `client.ts` `fetchRunList` expects). Sensitivity threshold from config/CLI flag. | Response is a JSON array; each item matches `RFRunSummary` fields; sensitivity filter applied; empty array (not 404) when no runs. | 0.5 pts | python-backend-engineer | sonnet | adaptive | P2-001 |
| P2-003 | `GET /api/runs/{run_id}` | Implement `GET /api/runs/{run_id}` calling `export_service.export_run(paths, run_id)`. Returns `RFRunExport`. 404 with structured `{"detail": "run not found"}` if run_id absent. | Response matches `RFRunExport` shape; missing run → HTTP 404 with structured body; sensitivity gate applied. FE resilience: missing optional fields (`tags`, `summary`) return `null`, not 500. | 0.75 pts | python-backend-engineer | sonnet | adaptive | P2-002 |
| P2-004 | `GET /api/runs/{run_id}/claims` | Implement `GET /api/runs/{run_id}/claims` returning `export_run(paths, run_id)["claims"]` array. Apply same sensitivity filter as parent run endpoint. 404 propagated from `export_run`. | Returns claims array; each claim's `quote`/`summary` redacted per threshold; 404 on unknown run; empty array (not null) when run has no claims. FE resilience: missing `evidence_strength` field handled gracefully (null fallback). | 0.5 pts | python-backend-engineer | sonnet | adaptive | P2-003 |
| P2-005 | `GET /api/runs/{run_id}/sources/{source_card_id}` | Implement `GET /api/runs/{run_id}/sources/{source_card_id}`. Scan `export_run(paths, run_id)["claims"]` for the first claim whose `sources` array contains a source matching `source_card_id`. Return the matching `RFResolvedSource`. 404 if not found. | Returns `RFResolvedSource` when source exists; HTTP 404 when source absent; HTTP 404 propagated when run absent. FE resilience: missing `url` or `access_date` fields on the source object returned as `null`. | 0.5 pts | python-backend-engineer | sonnet | adaptive | P2-004 |
| P2-006 | `GET /data/governance.json` | Implement `GET /data/governance.json`. Inspect `prebuild-static-data.mjs` output shape and `fetchGovernanceConfig()` in `client.ts` to confirm the exact `GovernanceConfig` fields. Return `FoundryConfig.governance` snapshot serialized to match that shape. | Response matches `GovernanceConfig` TS type exactly; fields match what `prebuild-static-data.mjs` would produce for the same config; no 500 on missing optional governance fields. | 0.25 pts | python-backend-engineer | sonnet | adaptive | P2-001 |

**Phase P2 Quality Gates:**
- [ ] All 5 endpoints return correct JSON shape matching `client.ts` TypeScript types
- [ ] Missing/unknown run_id returns HTTP 404 with structured body on all applicable endpoints
- [ ] Sensitivity gate applied (verified by inspection; dedicated test in P6)
- [ ] `GET /api/runs` returns empty array, not 404, when run corpus is empty
- [ ] FE missing-field resilience ACs verified for P2-003, P2-004, P2-005

---

### Phase P3: Config & Flag Wiring

**Duration**: ~0.5 day
**Dependencies**: P1 complete
**Assigned Subagent(s)**: python-backend-engineer (primary)
**Wave**: 2 (parallel with P2)

Reference: `src/research_foundry/config.py` `FoundryConfig.viewer` dict — extend with new keys using the existing dict-access pattern. Do NOT change the dict-access style.

OQ-2 resolved: Default port is `7432` (deconflicts from MeatyWiki's `8765`).
OQ-4 resolved: Token lives in an env var named by `viewer.auth_token_env` (default env var name: `RF_SERVE_TOKEN`). Token MUST NOT be inline in `foundry.yaml`.
OQ-5 resolved: `GET /data/governance.json` reads from `FoundryConfig.governance` block (see P2-006 AC).

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-001 | `viewer.*` config keys | Extend `FoundryConfig.viewer` in `config.py` with: `bind_host` (default `"127.0.0.1"`), `serve_port` (default `7432`), `auth_mode` (default `"none"`, enum `none\|token`), `auth_token_env` (default `"RF_SERVE_TOKEN"`), `allowlist` (default `[]`), `cors_origins` (default `["*"]` in loopback, configurable). Validate: `auth_mode` must be `none` or `token`; `allowlist` must be a list of strings. | `foundry.yaml` with `viewer: {serve_port: 9000}` applies the override; invalid `auth_mode` value raises `ConfigValidationError` with clear message; all defaults apply when keys absent. | 0.75 pts | python-backend-engineer | sonnet | adaptive | P1-002 |
| P3-002 | Port deconfliction doc + CLI help | Update `rf serve --help` to show `--port` default `7432` and note the MeatyWiki conflict. Add a comment in `config.py` near `serve_port` citing the deconfliction rationale. Verify `7432` is not in `agentic_meta_dev/infra/agentic-node/SERVICES.md`. | CLI help shows `--port 7432` as default; config comment cites MeatyWiki conflict; SERVICES.md check confirms 7432 is free (if collision found, choose next available and update all references). | 0.25 pts | python-backend-engineer | sonnet | adaptive | P3-001 |
| P3-003 | FE env-var semantics finalized | Update `frontend/runs-viewer/src/api/client.ts` loopback base URL default from `http://127.0.0.1:8765/api` → `http://127.0.0.1:7432/api`. Document `VITE_RUNS_FRONTEND_LOOPBACK_API`, `VITE_RUNS_LOOPBACK_API_BASE`, and `VITE_RUNS_LOOPBACK_API_TOKEN` in `frontend/runs-viewer/README.md` (or equivalent env-config doc). | `client.ts` loopback base URL default is `7432`; env vars documented with examples; `loopbackGet` signature unchanged. | 0.5 pts | python-backend-engineer | sonnet | adaptive | P3-001 |

**Phase P3 Quality Gates:**
- [ ] All five `viewer.*` config keys parse correctly with defaults
- [ ] Invalid `auth_mode` value raises a clear validation error
- [ ] `rf serve` CLI help shows `--port 7432` default
- [ ] `client.ts` loopback base URL default updated to `7432`
- [ ] FE env vars documented

---

### Phase P4: Auth & LAN (Gated)

**Duration**: ~1.5 days
**Dependencies**: P2 and P3 complete
**Assigned Subagent(s)**: python-backend-engineer (primary), senior-code-reviewer (mandatory secondary pass)
**Wave**: 3 — ISOLATED WORKTREE (Mode D-adjacent: network-exposure surface)
**Reviewer checkpoint**: `karen` checkpoint after this phase passes before P5 begins.

**Integration owner for P4/P5 cross-owner seam**: python-backend-engineer owns the auth-header propagation contract (P4 defines `Authorization: Bearer <token>` header; P5 wires it in `client.ts`). The seam task P4-SEAM documents this contract explicitly.

**Security invariants (must hold at this phase's exit gate)**:
- `bind_host=0.0.0.0` without `auth_mode=token` + configured token → server exits non-zero BEFORE binding
- Token comparison uses `hmac.compare_digest` exclusively
- No token logging (not in stdout, not in error messages, not in stack traces)
- IP allowlist (when non-empty) blocks unmatched IPs with HTTP 403

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-001 | Fail-closed bind gating | Implement pre-bind validation in `rf serve` command. Before calling `uvicorn.run()`: if `bind_host == "0.0.0.0"` and `auth_mode != "token"` → print clear error and `sys.exit(1)`. If `auth_mode == "token"` and token env var not set → print "RF_SERVE_TOKEN not set; refusing to bind on 0.0.0.0" and `sys.exit(1)`. | `rf serve --bind-host 0.0.0.0 --auth-mode none` exits non-zero before binding (no port is opened); `rf serve --bind-host 0.0.0.0 --auth-mode token` with token unset exits non-zero; loopback `rf serve` with `auth_mode=none` starts normally. | 0.75 pts | python-backend-engineer | sonnet | extended | P3-001 |
| P4-002 | Token auth middleware | Implement `src/research_foundry/api/middleware/auth.py` as a Starlette middleware. When `auth_mode == "token"`: extract `Authorization: Bearer <token>` from request; compare to configured token using `hmac.compare_digest`; return HTTP 401 if missing or invalid. Skip check for `GET /health` (liveness probe must remain unauthenticated). When `auth_mode == "none"`: middleware is a no-op pass-through (do not add it to the app in that case). | Valid token → request passes; missing header → 401; invalid token → 401; `GET /health` always returns 200 regardless of auth_mode; `hmac.compare_digest` used (verified by code review). No token value in any log line or exception message. | 1 pt | python-backend-engineer | sonnet | extended | P4-001 |
| P4-003 | IP allowlist middleware | Implement `src/research_foundry/api/middleware/allowlist.py`. When `viewer.allowlist` is non-empty: extract client IP from `request.client.host`; if not in allowlist → HTTP 403 with `{"detail": "IP not in allowlist"}`. When allowlist is empty or absent → no-op. Wire into `create_app()` after CORS and before auth. | Non-empty allowlist blocks unlisted IP with HTTP 403; empty allowlist allows all IPs; allowlist middleware applied before auth middleware. | 0.5 pts | python-backend-engineer | sonnet | extended | P4-002 |
| P4-004 | Written threat model | Add a `## Threat Model` section to `docs/dev/architecture/adr-runs-read-path.md` (or a standalone `docs/dev/architecture/runs-serve-threat-model.md` if the ADR is already long). Document: unauthenticated LAN exposure → countermeasure; token timing attack → `hmac.compare_digest`; IP bypass → allowlist; token in config file → env-var-only policy; `auth_mode=none` on 0.0.0.0 → fail-closed. | Threat model section exists with all 5 threats documented; linked from ADR. | 0.25 pts | python-backend-engineer | sonnet | adaptive | P4-003 |
| P4-SEAM | Auth-header propagation contract (seam task) | Define and document the exact contract for P5: `loopbackGet()` in `client.ts` MUST send `Authorization: Bearer ${token}` when `VITE_RUNS_LOOPBACK_API_TOKEN` is set (non-empty). Token value injected at Vite build time. No token → header omitted (not sent as empty string). Write this contract as a comment block at the top of `api/middleware/auth.py` and as a note in `client.ts` `loopbackGet`. integration_owner: python-backend-engineer. | Contract comment exists in both files; P5 implementer can implement FE-side without ambiguity; no circular dependency. | 0 pts (zero-cost documentation task) | python-backend-engineer | sonnet | adaptive | P4-002 |

**Phase P4 Quality Gates:**
- [ ] `rf serve --bind-host 0.0.0.0 --auth-mode none` exits non-zero before binding
- [ ] `rf serve --bind-host 0.0.0.0 --auth-mode token` with token unset exits non-zero
- [ ] Valid token → 200; missing/invalid token → 401; `GET /health` always 200
- [ ] IP allowlist blocks non-listed IPs with 403
- [ ] `hmac.compare_digest` used for token comparison (senior-code-reviewer verified)
- [ ] No token value appears in any log line or exception message
- [ ] Threat model written and linked from ADR
- [ ] Auth-header propagation contract documented (P4-SEAM)
- [ ] karen checkpoint passed

---

### Phase P5: Frontend Integration

**Duration**: ~0.5 day
**Dependencies**: P4 complete (auth contract defined in P4-SEAM)
**Assigned Subagent(s)**: ui-engineer (primary)
**Wave**: 4
**integration_owner**: python-backend-engineer (defined in P4-SEAM)

**Scope**: `frontend/runs-viewer/src/api/client.ts` only. No component changes. No new SPA routes. The dual-mode seam (`VITE_RUNS_FRONTEND_LOOPBACK_API`) was built in `runs-frontend-v1` and is already functional for static-data mode.

**Target surfaces for R-P3/R-P4 (runtime smoke, AC-7):**
- `client.ts::fetchRunList()` → `GET /api/runs`
- `client.ts::fetchRunDetail()` → `GET /api/runs/{run_id}`
- `client.ts::fetchClaimLedger()` → `GET /api/runs/{run_id}/claims`
- `client.ts::fetchSourceCard()` → `GET /api/runs/{run_id}/sources/{source_card_id}`
- `client.ts::fetchGovernanceConfig()` → `GET /data/governance.json`

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P5-001 | `loopbackGet` auth-header wiring | In `client.ts`, update `loopbackGet()` to inject `Authorization: Bearer ${VITE_RUNS_LOOPBACK_API_TOKEN}` header when the env var is set and non-empty. When env var is absent or empty, omit the header entirely (no empty `Authorization` header). Follow the contract from P4-SEAM exactly. | `loopbackGet` sends auth header when `VITE_RUNS_LOOPBACK_API_TOKEN` is set; header omitted when not set; no other functions in `client.ts` changed. FE resilience: if server returns 401, `loopbackGet` surfaces the error (does not swallow it). | 0.5 pts | ui-engineer | sonnet | adaptive | P4-SEAM |
| P5-002 | Runtime smoke & env-config docs | Manually (or via Playwright smoke script) verify the SPA built with `VITE_RUNS_FRONTEND_LOOPBACK_API=true` and `VITE_RUNS_LOOPBACK_API_BASE=http://127.0.0.1:7432/api` loads runs from the live API. Confirm all 5 endpoint call paths are exercised. Update `frontend/runs-viewer/README.md` with env-var configuration instructions for loopback and LAN modes. | SPA loads run list from live API in loopback mode; all 5 `client.ts` call paths triggered (confirmed by server access log or breakpoint); env vars documented with loopback and LAN examples. | 0.5 pts | ui-engineer | sonnet | adaptive | P5-001 |

**Phase P5 Quality Gates:**
- [ ] SPA loads run list from live API (`VITE_RUNS_FRONTEND_LOOPBACK_API=true`)
- [ ] All 5 client.ts endpoint call paths exercise successfully against live server (runtime smoke — R-P4)
- [ ] Auth header present in `loopbackGet` when `VITE_RUNS_LOOPBACK_API_TOKEN` set
- [ ] Auth header absent when token env var not set
- [ ] 401 from server surfaces as error (not silently swallowed)
- [ ] Env-config docs updated in `frontend/runs-viewer/README.md`

---

### Phase P6: Tests

**Duration**: ~1 day
**Dependencies**: P5 complete
**Assigned Subagent(s)**: python-backend-engineer (primary)
**Wave**: 5

Reference test pattern: `tests/test_cli_governance.py` (CliRunner + TestClient).
Run tests under venv: `./.venv/bin/python -m pytest tests/test_serve_*.py` (per project memory).

**Risk-to-test mapping** (from decisions block §3):
- R1 (sensitivity bypass) → TEST-006 (parity test)
- R2 (network exposure) → TEST-003 (fail-closed bind) + TEST-004 (token auth)
- R3 (endpoint-shape drift) → TEST-001 through TEST-005 (contract tests)
- R4 (port collision) → TEST-007 (config validation)
- R5 (dep footprint) → TEST-008 (extra isolation)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| TEST-001 | `GET /api/runs` contract test | TestClient test with a fixture run corpus. Verify response is `list`, each item has required `RFRunSummary` fields, empty corpus returns `[]`. | Test green; covers empty and non-empty corpus. | 0.2 pts | python-backend-engineer | sonnet | adaptive | P5-002 |
| TEST-002 | `GET /api/runs/{run_id}` contract test | TestClient test: known run_id → 200 + `RFRunExport` shape; unknown run_id → 404 + `{"detail": "..."}`. | Test green; 404 body is structured JSON. | 0.2 pts | python-backend-engineer | sonnet | adaptive | P5-002 |
| TEST-003 | `GET /api/runs/{run_id}/claims` + sources tests | TestClient tests for `/claims` (non-empty + empty array) and `/sources/{id}` (found + 404). | Tests green; redacted fields verified in claims response. | 0.2 pts | python-backend-engineer | sonnet | adaptive | P5-002 |
| TEST-004 | `GET /data/governance.json` contract test | TestClient test: response matches `GovernanceConfig` shape; no 500 on minimal config. | Test green. | 0.1 pts | python-backend-engineer | sonnet | adaptive | P5-002 |
| TEST-005 | `GET /health` test | TestClient test: always returns 200 regardless of auth_mode (loopback + token). | Test green for both auth modes. | 0.1 pts | python-backend-engineer | sonnet | adaptive | P5-002 |
| TEST-006 | Sensitivity-gate parity test | Fixture: a run containing a claim with `sensitivity: work_sensitive`. Threshold `public`. Verify `GET /api/runs/{run_id}` response has `quote` and `summary` as `"[redacted:sensitivity]"`. Verify parity with direct `export_service.export_run()` call on the same fixture. | Parity assertion passes; redacted fields match exactly between API and direct export_service call. | 0.4 pts | python-backend-engineer | sonnet | adaptive | TEST-002 |
| TEST-007 | Auth tests: token middleware | TestClient with `auth_mode=token`: valid Bearer → 200; missing header → 401; invalid token → 401; `GET /health` → 200. Verify `hmac.compare_digest` path is exercised (inspect source or use coverage). | All branches green; `GET /health` bypasses auth. | 0.4 pts | python-backend-engineer | sonnet | adaptive | TEST-005 |
| TEST-008 | Fail-closed bind tests | CliRunner test: `rf serve --bind-host 0.0.0.0 --auth-mode none` → exits non-zero; `--auth-mode token` with token env unset → exits non-zero; `--auth-mode token` with token set → would start (stub uvicorn call). | Both failure cases exit non-zero; success case stubs uvicorn.run. | 0.2 pts | python-backend-engineer | sonnet | adaptive | TEST-007 |
| TEST-009 | IP allowlist test | TestClient with non-empty allowlist: request from unlisted IP → 403; request from listed IP → 200. | Test green. | 0.1 pts | python-backend-engineer | sonnet | adaptive | TEST-008 |
| TEST-010 | Core footprint isolation test | In CI or local: `pip install research-foundry` (no extra); `python -c "import research_foundry; print('ok')"` succeeds; `python -c "import fastapi"` fails. | Both assertions pass. | 0.1 pts | python-backend-engineer | sonnet | adaptive | TEST-001 |

**Phase P6 Quality Gates:**
- [ ] All TEST-001 through TEST-010 green under `.venv/bin/python -m pytest`
- [ ] Sensitivity-gate parity test (TEST-006) passes — this is the most critical correctness gate
- [ ] Auth fail-closed bind test (TEST-008) passes
- [ ] Core footprint isolation test (TEST-010) passes
- [ ] `hmac.compare_digest` usage confirmed (TEST-007)

---

### Phase P7: Deploy & Docs

**Duration**: ~0.5 day
**Dependencies**: P6 complete
**Assigned Subagent(s)**: documentation-writer (haiku, primary for ADR/CHANGELOG/specs); python-backend-engineer (sonnet, for systemd unit)
**Wave**: 6

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| DOC-001 | CHANGELOG `[Unreleased]` entry | Add entries under `[Unreleased]` in `CHANGELOG.md`: `Added: rf serve command — read-only FastAPI server for runs-viewer live data (loopback mode, default port 7432)`; `Added: Loopback API mode — SPA can now read live runs without static export`; `Added: Gated LAN exposure — rf serve --bind-host 0.0.0.0 requires --auth-mode token and a configured token; fails closed without one`. Follow Keep A Changelog format. Set `changelog_ref: CHANGELOG.md` in plan frontmatter. | Three `Added` entries under `[Unreleased]`; no `Released` date set; `changelog_ref` frontmatter updated. | 0.2 pts | changelog-generator | haiku | adaptive | P6 quality gates |
| DOC-002 | ADR update | Update `docs/dev/architecture/adr-runs-read-path.md` to record the dual-mode read path: (1) static export via `rf run export --json` (v1 path, unchanged), (2) live loopback API via `rf serve` (this feature). Link to this PRD and the threat model from P4-004. | ADR records both read paths; threat model linked; ADR status updated to `amended` if applicable. | 0.2 pts | documentation-writer | haiku | adaptive | P4-004 |
| DOC-003 | README / CLI docs | Update project `README.md` (or CLI help doc) with `rf serve` usage: basic loopback mode, LAN mode with token, env vars table, port defaults, note on MeatyWiki conflict. | README includes `rf serve` section with loopback and LAN examples; port default `7432` documented; env vars table present. | 0.2 pts | documentation-writer | haiku | adaptive | DOC-001 |
| DOC-004 | systemd unit file | Author `systemd/rf-serve.service` (or equivalent path). Unit runs `rf serve` as the agentic-nuc user with `RUNS_FRONTEND_LOOPBACK_API=true` and `RF_SERVE_TOKEN` sourced from an environment file. Include `Restart=on-failure`, `RestartSec=5`. | Unit file syntactically valid (`systemd-analyze verify`); environment file pattern documented; not auto-enabled (operator enables manually). | 0.2 pts | python-backend-engineer | sonnet | adaptive | DOC-003 |
| DOC-005 | Design-spec promotion: `runs-loopback-api.md` | Update `docs/project_plans/design-specs/runs-loopback-api.md`: set `maturity: promoted`, `prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md`. Annotate the deferred item DEF-03 (fs-watch hot-reload) in a `## Deferred (v2)` section. Append spec path to `deferred_items_spec_refs` in this plan's frontmatter. | `maturity: promoted`, `prd_ref` set, deferred fs-watch annotated; `deferred_items_spec_refs` updated. | 0.1 pts | documentation-writer | haiku | adaptive | DOC-001 |
| DOC-006 | Design-spec promotion: `runs-auth-lan.md` + deferred auth modes | Update `docs/project_plans/design-specs/runs-auth-lan.md`: set `maturity: promoted`, `prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md`. Annotate deferred items DEF-01 (mTLS) and DEF-02 (SSH-tunnel) in a `## Deferred (v2)` section with rationale and promotion trigger. Append spec path to `deferred_items_spec_refs` in this plan's frontmatter. | `maturity: promoted`, `prd_ref` set; mTLS and SSH-tunnel deferred sections annotated with rationale and promotion condition; `deferred_items_spec_refs` updated. | 0.1 pts | documentation-writer | haiku | adaptive | DOC-001 |
| DOC-007 | Plan frontmatter finalization | Set `status: completed`, populate `commit_refs`, `files_affected`, `deferred_items_spec_refs` (three design spec paths), `updated` date in this plan's frontmatter. | Plan frontmatter reflects completed state; all three deferred spec refs present. | 0.1 pts | documentation-writer | haiku | adaptive | DOC-005, DOC-006 |

**Phase P7 Quality Gates:**
- [ ] CHANGELOG `[Unreleased]` has all three `Added` entries
- [ ] ADR records dual-mode read path and links threat model
- [ ] README documents `rf serve` usage with examples
- [ ] systemd unit file authored and syntactically valid
- [ ] Both design specs promoted (`maturity: promoted`, `prd_ref` set)
- [ ] Both specs have `## Deferred (v2)` sections with annotated deferred items
- [ ] `deferred_items_spec_refs` in plan frontmatter has three paths (two auth-lan deferred modes + loopback spec)
- [ ] Plan frontmatter finalized

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| Sensitivity-gate bypass (R1) | High | Low | FR-3 / NFR-2: all responses route through `export_service`; TEST-006 dedicated parity test is a phase P6 hard gate |
| LAN exposure without auth (R2) | High | Low | Fail-closed bind in P4-001; TEST-008 is a P6 hard gate; `karen` checkpoint at P4 exit |
| Endpoint-shape drift from client.ts (R3) | Medium | Low | P2 task table enumerates all 5 endpoints and client.ts call sites explicitly; runtime smoke in P5-002 |
| Port collision with MeatyWiki (R4) | Low–Medium | Low | Default port `7432` confirmed; P3-002 SERVICES.md check; CLI help documents the default |
| Dep footprint growth (R5) | Low | Low | Optional `[serve]` extra in P1-001; TEST-010 isolation test in P6 is a hard gate |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| P4 security surface expands scope | Medium | Low | P4 is isolated worktree; scope boundary is middleware-only; no new data layer |
| `karen` checkpoint at P4 triggers rework | Medium | Medium | P4 tasks are well-bounded; rework likely limited to token comparison or bind logic |
| P3-002 SERVICES.md reveals port 7432 conflict | Low | Very Low | Contingency: choose 7433 and update all references in one P3 pass |

---

## Success Metrics

### Delivery Metrics

- All 7 phases sealed with quality gates green
- 13 pts ± 2 pts actual
- P4 `karen` checkpoint passed without rework loops

### Technical Metrics

- `pytest` green under venv for all TEST-* tasks
- Sensitivity-gate parity test (TEST-006) passes
- Fail-closed bind tests (TEST-008) pass
- Core footprint isolation test (TEST-010) passes
- `hmac.compare_digest` used in token comparison (code-reviewed)

### Operational Metrics

- `rf serve` documented in README with loopback and LAN examples
- systemd unit file authored for agentic-nuc deployment
- Both design specs promoted with deferred-item annotations

---

## Post-Implementation

- Monitor `rf serve` error logs on agentic-nuc for unexpected 500s after first real deployment
- Watch for port `7432` conflicts if new services are added to `agentic-node/SERVICES.md`
- Trigger DEF-03 (fs-watch cache) promotion if run corpus exceeds ~500 runs or operator reports latency

---

## Wrap-Up: Feature Guide & PR

After P7 is sealed:

1. Delegate `documentation-writer` (haiku) to create `.claude/worknotes/runs-loopback-api/feature-guide.md`.
2. Open PR with: `rf serve: read-only loopback API + gated LAN exposure` as title; bullets from Executive Summary and CHANGELOG entries.

---

**Progress Tracking:** `.claude/progress/runs-loopback-api/` (created when implementation begins)

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-06-22
