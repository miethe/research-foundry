---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: "BRIEF-runs-loopback-api"
title: "Runs Viewer — Live Loopback API + Gated LAN Exposure — Human Brief"
status: draft
category: human-briefs

feature_slug: runs-loopback-api
feature_family: runs-loopback-api
feature_version: v1

prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/design-specs/runs-loopback-api.md
  - docs/project_plans/design-specs/runs-auth-lan.md
  - docs/dev/architecture/adr-runs-read-path.md
  - .claude/worknotes/runs-loopback-api/decisions-block.md
  - docs/project_plans/PRDs/features/runs-frontend-v1.md

owner: nick
contributors: []

audience: [humans]

priority: medium
confidence: 0.87

created: 2026-06-22
updated: 2026-06-22
target_release: ""

tags: [human-brief, runs-viewer, loopback-api, fastapi, auth, lan]
---

# Runs Viewer — Live Loopback API + Gated LAN Exposure — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-06-22

---

## 1. Context Pointers

One-line pointers. Do not restate content.

- **PRD**: `docs/project_plans/PRDs/features/runs-loopback-api-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md`
- **Design Specs**: `docs/project_plans/design-specs/runs-loopback-api.md` (OQ-6); `docs/project_plans/design-specs/runs-auth-lan.md` (OQ-4) — both promoted in P7
- **Decisions Block**: `.claude/worknotes/runs-loopback-api/decisions-block.md` — authoritative phase boundaries, agent routing, risk hotspots
- **Parent PRD**: `docs/project_plans/PRDs/features/runs-frontend-v1.md` — origin of OQ-6 and OQ-4 deferral
- **ADR**: `docs/dev/architecture/adr-runs-read-path.md` — updated in P7 to record dual-mode read path
- **SPIKEs**: None — framework (FastAPI) and auth posture (loopback-first + token) were resolved by operator decision before planning; no SPIKE required.
- **Related Briefs**: `docs/project_plans/human-briefs/runs-frontend.md` (parent feature)

---

## 2. Estimation Sanity Check

**Bottom-up total**: 13 pts
**Top-down anchor**: `runs-frontend-v1` export service (P1) at ~2 pts for the export core; Search Router CLI addition (`rf search`) at ~2 pts for a new Typer command. This plan bundles both patterns at ~13 pts.
**Reconciliation**: Bottom-up and top-down agree within 10%. The plan does NOT compress the two-area bundle (loopback API + auth gating) into a rounded "Medium" price — each area was estimated independently.

### H1 — Noun-Counting Rule

Zero new database tables. The API reads from existing on-disk run artifacts via `export_service`. H1 does not apply. This is the primary reason the estimate is on the lower end for a 7-phase feature.

### H2 — Dual-Implementation Multiplier

Not applicable. There is no repository layer with local/enterprise splits. The API wraps a single `export_service` module that already handles the sensitivity gate.

### H3 — Algorithmic Service Flag

Not flagged. All 5 endpoints are mechanical routing operations: call `export_service`, return result. The only non-trivial logic is `hmac.compare_digest` (constant-time token comparison), which is a stdlib call — not an algorithmic service.

### H4 — Bundle-vs-Sum Check

Two bundled capability areas — both previously deferred from `runs-frontend-v1`:

| Capability Area | Independent Estimate | Notes |
|-----------------|---------------------|-------|
| Loopback API (P1+P2+P3+P5) | 7.5 pts | App factory (2), 5 endpoints (3), config wiring (1.5), FE seam (1) |
| Auth & LAN gating (P4) | 2.5 pts | Fail-closed bind + token middleware + IP allowlist + threat model |
| Testing (P6) | 2 pts | Covers both areas; not compressible without losing coverage |
| Deploy & Docs (P7) | 1 pt | systemd + ADR + CHANGELOG + two spec promotions |
| **Σ** | **13 pts** | Plan total equals Σ exactly; no compression applied |

Bundling the two deferred specs (OQ-6 + OQ-4) is correct because the auth surface only matters if there is a live server to protect. Designing them separately would produce two plans with a hard dependency anyway.

### H5 — Anchor Reference

**Anchor 1**: `runs-frontend-v1` export service (P1) — `export_service.export_run` + `list_runs` — ~2 pts for the service layer. This plan's P2 (5 read endpoints reusing that core) anchors at 3 pts: +1 pt for 5 endpoints vs the service's internal API, justified by the endpoint-shape contract discipline (must match TS types exactly).

**Anchor 2**: Search Router MVP (`rf search` CLI addition, commit `d119993`) — a new Typer command with a service backing it — ~2 pts. P1 (app factory + `rf serve` command + extras packaging) anchors at 2 pts. P1 is slightly more complex (CORS middleware, optional extras guard) but stays at 2 pts because the FastAPI factory is lighter than the Search Router's source-acquisition pipeline.

**Estimate delta vs anchors**: Both anchors are within ±20%. No delta justification required.

### H6 — Hidden Plumbing Budget

~1.5 pts folded into P1/P3:
- P1: CORS middleware wiring, optional import guard, extras packaging
- P3: Config defaults validation, port deconfliction, FE env-var flag documentation

This is approximately 12% of the 13-pt total — slightly below the 15–20% guideline, but justified because there are no database migrations, no DTOs, no RLS policies, and no OpenAPI schema regeneration (FastAPI auto-generates it). The "plumbing" surface is genuinely smaller than a typical DB-backed feature.

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 → P2 → P4 → P5 → P6 → P7

P3 (config wiring) is on a parallel rail: P1 → P3 → P4. P3 gates P4 because auth middleware consumes the `viewer.auth_mode` and `viewer.auth_token_env` config keys. P2 and P3 can execute concurrently in wave 2 — they touch disjoint files (`api/routers/runs.py` vs `config.py`).

**Parallel opportunities**:
- Wave 2: P2 ∥ P3 (safe — no shared files)
- P4 backend and P5 are NOT safe to parallelize: `client.ts` auth-header implementation depends on the exact contract defined in P4-SEAM

**Merge order**: P4 uses an isolated worktree (Mode D-adjacent, network-exposure surface). Squash-merge P4 branch into the integration target before starting P5. The `karen` checkpoint at P4 exit is the gating event.

**Cross-feature coupling**:
- Depends on `runs-frontend-v1` being merged (it is — `export_service` and the `client.ts` dual-mode seam are already shipped)
- Search Router (`d119993`) adds no coupling — it uses a separate CLI command and separate service

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | Decisions Block §7 | Package `fastapi`/`uvicorn` as `[serve]` optional extra vs core dependency | Resolved | Operator decision: optional `[serve]` extra; `rf serve` raises install error if missing |
| OQ-2 | Decisions Block §7 | Confirm default serve port (deconflict from MeatyWiki's 8765) | Resolved | Port `7432` selected; P3-002 verifies vs SERVICES.md |
| OQ-3 | Decisions Block §7 | Hot-reload model: per-request disk reads vs fs-watch cache | Resolved | Per-request reads for v1; fs-watch deferred to v2 (DEF-03) |
| OQ-4 | Decisions Block §7 | Shared-secret token provisioning mechanism | Resolved | Token in env var named by `viewer.auth_token_env` (default: `RF_SERVE_TOKEN`); never inline in `foundry.yaml` |
| OQ-5 | Decisions Block §7 | `GET /data/governance.json` source: FoundryConfig.governance block vs generated file | Resolved in P2-006 | Inspect `prebuild-static-data.mjs` + `fetchGovernanceConfig()` to confirm; replicate parity; AC in P2-006 |
| OQ-C | PRD §13 | Default env-var name for shared-secret token | Resolved | `RF_SERVE_TOKEN` |
| OQ-D | PRD §13 | `GET /data/governance.json` source confirmation | Resolved in P2-006 | See OQ-5 above |
| OQ-E | PRD §13 | CORS allowed origins for LAN deployment | Resolved in P3-001 | Default `*` in loopback; configurable via `viewer.cors_origins` |

All OQs are resolved before implementation begins. No open questions remain.

---

## 5. Deferred Items Rationale

Three items were explicitly deferred to v2. Each has a design-spec annotation task in P7 (DOC-005 and DOC-006).

- **mTLS auth mode (DEF-01)**: Requires certificate provisioning infrastructure (CA, cert rotation, mTLS termination) not present on `agentic-nuc`. The operator threat model — a single-user node on a home LAN — is adequately served by the shared-secret token over loopback or within the trusted LAN. mTLS adds significant operational overhead for marginal security gain in this context. Promote when operator places `agentic-nuc` on an untrusted network or requests mutual-TLS explicitly.

- **SSH-tunnel auth mode (DEF-02)**: An SSH-tunnel transport mode (e.g., `ssh -L 7432:localhost:7432 agentic-nuc`) would let the operator avoid any token entirely by treating the SSH channel as the auth layer. This is operationally elegant but requires the server to be "SSH-tunnel-aware" (or just document that operators can use SSH-tunnel alongside the existing loopback mode). Deferred because token-over-loopback achieves the JTBD; SSH-tunnel is a usability enhancement, not a security requirement. Promote when operator requests it.

- **Filesystem-watch hot-reload cache (DEF-03)**: Per-request disk reads are correct and simple at operator scale (single user, interactive browsing of 10–100 runs). The `watchdog`/`inotify` dependency and cache invalidation logic introduce real complexity for a workload that doesn't need it. Promote when run corpus exceeds ~500 runs or operator reports measurable latency.

---

## 6. Risk Narrative

**R1 — Sensitivity-gate bypass (HIGH)**: The most consequential correctness risk. If any endpoint reads raw run artifact files directly (instead of routing through `export_service`), it bypasses `resolve_threshold()` and leaks governed content (work-sensitive claims, personal data). The invariant is structural: the API layer must never call `open()` on run files. This is enforced by code review at P2 exit and a dedicated parity test (TEST-006) that is a P6 hard gate. Watch for: any `json.load(open(...))` in `api/routers/runs.py`.

**R2 — LAN exposure without auth (HIGH)**: The fail-closed bind (P4-001) is the primary countermeasure. If implementation shortcuts the fail-closed check (e.g., falls back to binding on `0.0.0.0` with `auth_mode=none` instead of refusing), the full run corpus is exposed to anyone on the LAN. Watch for: missing `sys.exit(1)` before `uvicorn.run()` in the `bind_host=0.0.0.0` path. The `karen` checkpoint at P4 exit is specifically for this.

**R3 — Endpoint-shape drift from client.ts (MEDIUM)**: The original design spec named 2 endpoints; `client.ts` actually calls 5. The P2 task table enumerates all 5 with explicit client.ts function names and approximate line numbers. Watch for: any endpoint that's implemented but not mapped to its `client.ts` caller (the runtime smoke in P5-002 catches this).

**R4 — Port collision (LOW-MEDIUM)**: P3-002 explicitly checks `agentic-node/SERVICES.md` for `7432` before committing. Low risk but worth the 10-minute check.

**R5 — Dep footprint (LOW)**: The `[serve]` extra pattern is already used in the project. TEST-010 (core footprint isolation) is a P6 hard gate. Low operational risk.

---

## 7. What to Watch For

- **P2 sensitivity invariant**: Review the `api/routers/runs.py` diff specifically for any direct file I/O. There should be zero `open()` calls. All data flows through `export_service.export_run()` or `export_service.list_runs()`.

- **P4 token logging**: Verify no log line captures the token value. Common slip: `logger.debug(f"Received token: {token}")` in the middleware. Check P4's diff carefully.

- **P4-SEAM handoff to P5**: The ui-engineer implementing P5 will read the contract comment in `middleware/auth.py` and `client.ts`. If the contract is ambiguous (e.g., empty-string token vs. missing header), the FE implementation will be wrong. Verify P4-SEAM is unambiguous before P5 begins.

- **P2-006 governance.json shape**: The `fetchGovernanceConfig()` TS type and the `prebuild-static-data.mjs` output need to be compared before implementing `GET /data/governance.json`. A shape mismatch here will break the SPA's governance chip. The P2-006 AC explicitly requires inspecting both sources.

- **karen checkpoint scope**: The `karen` checkpoint at P4 exit should review: fail-closed bind logic, token middleware, IP allowlist, threat model completeness, and the P4-SEAM contract. It is NOT a full feature review (that happens at feature end).

- **Port 7432 in SERVICES.md**: There is a small but real chance 7432 is already allocated. P3-002 handles this, but be prepared to update all references (config.py, client.ts default, CLI help, README) if a conflict is found.

---

## 8. Expected Success Behaviors

Observable outcomes a human orchestrator can verify after shipping:

- [ ] `rf serve` appears in `rf --help` output with `--port`, `--bind-host`, `--auth-mode`, `--sensitivity-threshold` flags
- [ ] `rf serve` (no flags) starts without error and `curl http://127.0.0.1:7432/health` returns `{"status": "ok"}`
- [ ] `curl http://127.0.0.1:7432/api/runs` returns a JSON array (empty array if no runs, not 404)
- [ ] SPA built with `VITE_RUNS_FRONTEND_LOOPBACK_API=true VITE_RUNS_LOOPBACK_API_BASE=http://127.0.0.1:7432/api` loads run list from live server
- [ ] `rf serve --bind-host 0.0.0.0 --auth-mode none` exits with non-zero status and a clear error before any port is opened (verify: `ss -tnlp | grep 7432` shows nothing after the command)
- [ ] `RF_SERVE_TOKEN=mytoken rf serve --bind-host 0.0.0.0 --auth-mode token` starts; `curl -H "Authorization: Bearer wrongtoken" http://localhost:7432/api/runs` returns 401
- [ ] `pip install research-foundry` (no extra) succeeds; `python -c "import research_foundry"` works without error; `python -c "import fastapi"` fails
- [ ] `CHANGELOG.md [Unreleased]` contains `rf serve` under `Added`
- [ ] `docs/project_plans/design-specs/runs-loopback-api.md` and `runs-auth-lan.md` both show `maturity: promoted`
- [ ] `docs/dev/architecture/adr-runs-read-path.md` documents both read paths (static export + loopback API)
- [ ] `systemd/rf-serve.service` file exists and passes `systemd-analyze verify`

---

## 9. Running Log

- [2026-06-22] Brief created. All OQs resolved. Plan at 13 pts, 7 phases. Deferred items: DEF-01 (mTLS), DEF-02 (SSH-tunnel), DEF-03 (fs-watch cache). karen checkpoint scheduled at P4 exit.
