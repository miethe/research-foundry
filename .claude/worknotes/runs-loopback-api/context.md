---
type: context
doc_type: context
prd: runs-loopback-api
feature_slug: runs-loopback-api
title: Runs Loopback API - Development Context
status: active
created: '2026-06-22'
updated: '2026-06-22'
prd_ref: docs/project_plans/PRDs/features/runs-loopback-api-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
decisions_ref: .claude/worknotes/runs-loopback-api/decisions-block.md
human_brief_ref: docs/project_plans/human-briefs/runs-loopback-api.md
critical_notes_count: 3
implementation_decisions_count: 4
active_gotchas_count: 3
agent_contributors: []
agents: []
---

# Runs Loopback API - Development Context

**Status**: Pending (implementation not started)
**Created**: 2026-06-22
**Last Updated**: 2026-06-22

> **Purpose**: Shared worknotes for all AI agents working on runs-loopback-api. Key decisions, watch items, and orientation for executors picking up any phase.

---

## Quick Reference

| Item | Value |
|------|-------|
| PRD | `docs/project_plans/PRDs/features/runs-loopback-api-v1.md` |
| Implementation Plan | `docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md` |
| Decisions Block | `.claude/worknotes/runs-loopback-api/decisions-block.md` |
| Human Brief | `docs/project_plans/human-briefs/runs-loopback-api.md` |
| Progress Files | `.claude/progress/runs-loopback-api/phase-{1..7}-progress.md` |
| Client Contract | `frontend/runs-viewer/src/api/client.ts` |
| ADR | `docs/dev/architecture/adr-runs-read-path.md` |
| Export Schema | `docs/dev/architecture/rf-run-export-schema.md` |

---

## Feature Orientation

**What this feature does**: Adds `rf serve` — a read-only FastAPI HTTP server that serves the runs-viewer SPA's 5 live endpoints from disk. Data routes through the existing `export_service` sensitivity gate. Binds to loopback by default (`127.0.0.1:7432`); LAN exposure on `0.0.0.0` is a gated opt-in requiring a shared-secret token.

**Bundled specs (OQ-6 + OQ-4)**: Two capability areas shipped together:
1. **Loopback API (OQ-6)**: FastAPI app factory + 5 read endpoints + `rf serve` CLI (P1, P2, P3, P5)
2. **Gated LAN auth (OQ-4)**: Fail-closed bind + token middleware + IP allowlist + threat model (P4)

**Wave structure**:
- Wave 1: P1 (foundation)
- Wave 2: P2 + P3 in parallel (endpoints + config)
- Wave 3: P4 (auth, isolated worktree)
- Wave 4: P5 (frontend integration)
- Wave 5: P6 (tests)
- Wave 6: P7 (deploy + docs)

---

## Locked Decisions

### Decision 1: FastAPI + uvicorn as optional [serve] extra

**Decision**: Use FastAPI + uvicorn (standard extras). Ship as optional `[serve]` extra in `pyproject.toml` to keep the core `research_foundry` footprint zero-dependency-growth.

**Why**: Avoids polluting the core dependency graph for operators who do not use the API. FastAPI was already in the design spec; uvicorn is the natural pairing.

**How to apply**: Import guard in `api/__init__.py` raises a clear error if fastapi/uvicorn missing. TEST-010 validates this invariant.

**Ref**: `docs/project_plans/design-specs/runs-loopback-api.md`

### Decision 2: Loopback-first, gated token for LAN

**Decision**: Default bind is `127.0.0.1:7432` with `auth_mode=none`. LAN exposure on `0.0.0.0` is only allowed with `auth_mode=token` AND a configured token. Fail-closed: if both conditions aren't met the server exits before binding.

**Why**: The threat model (P4-004) identifies unauthenticated LAN exposure as the highest-risk failure mode. Fail-closed is the safest default for an operator-grade server.

**How to apply**: Pre-bind validation in P4-001 (not in uvicorn config). Token compared with `hmac.compare_digest` (constant-time). Token lives in env var named by `viewer.auth_token_env` — never inline in `foundry.yaml`.

**Ref**: `docs/project_plans/design-specs/runs-auth-lan.md`, `.claude/worknotes/runs-loopback-api/decisions-block.md`

---

## High-Severity Watch Items

### Watch-1: Sensitivity-gate parity (Risk R1)

**What**: All 5 API endpoints MUST route responses through `export_service.export_run()` or `export_service.list_runs()`. The API layer must never read raw run artifact files or re-implement serialization.

**Why it matters**: Bypassing `export_service` bypasses the sensitivity gate, potentially leaking `work_sensitive` or `restricted` data through the API.

**How to verify**: TEST-006 is the dedicated parity test — it compares API output against direct `export_service` call on the same fixture. This is a **phase P6 hard gate**: P7 cannot begin until TEST-006 passes.

**Phases at risk**: P2 (any of P2-001 through P2-005 that read files directly instead of via export_service).

### Watch-2: Fail-closed LAN binding (Risk R2)

**What**: The `rf serve` command must exit non-zero BEFORE opening any port if `bind_host=0.0.0.0` without token auth configured.

**Why it matters**: A server that opens a LAN port without auth is an unauthenticated data exposure on the homelab network.

**How to verify**: TEST-008 (CliRunner fail-closed bind) is a **phase P6 hard gate**. P4 also has a `karen` checkpoint before P5 begins.

**Phases at risk**: P4-001 (pre-bind validation) and the CLI wiring in P1-003 (stub) — ensure the stub does not silently succeed where the real gate should fire.

### Watch-3: 5-vs-2 endpoint contract (Risk R3)

**What**: The plan enumerates exactly 5 client.ts-mapped endpoints. Any drift between what P2 implements and what client.ts expects causes runtime failures in the SPA.

**Why it matters**: The SPA's `client.ts` functions call specific URL patterns. A mismatch (e.g., wrong prefix, missing endpoint, wrong response shape) produces 404s or JSON parse errors in the viewer.

**How to verify**: P2 task table enumerates all 5 endpoints with explicit client.ts line references. P5-002 runtime smoke exercises all 5 call paths. TEST-001 through TEST-004 cover shape contracts.

**Endpoint mapping for executors**:
| Endpoint | client.ts function | line |
|----------|--------------------|------|
| `GET /api/runs` | `fetchRunList()` | ~109 |
| `GET /api/runs/{run_id}` | `fetchRunDetail()` | ~126 |
| `GET /api/runs/{run_id}/claims` | `fetchClaimLedger()` | ~175 |
| `GET /api/runs/{run_id}/sources/{source_card_id}` | `fetchSourceCard()` | ~197 |
| `GET /data/governance.json` | `fetchGovernanceConfig()` | ~158 |

---

## Deferred Items (do not implement in v1)

| ID | Item | Design Spec Annotation Target |
|----|------|-------------------------------|
| DEF-01 | mTLS auth mode | `docs/project_plans/design-specs/runs-auth-lan.md` §Deferred (v2) |
| DEF-02 | SSH-tunnel auth mode | `docs/project_plans/design-specs/runs-auth-lan.md` §Deferred (v2) |
| DEF-03 | Filesystem-watch hot-reload cache | `docs/project_plans/design-specs/runs-loopback-api.md` §Deferred (v2) |

P7 cannot be sealed until all three have their design-spec annotation tasks (DOC-005, DOC-006) completed.

---

## Implementation Decisions

> Fill in as agents make decisions during execution

---

## Gotchas & Observations

> Fill in as agents discover issues during execution

---

## Agent Handoff Notes

> Fill in as phases complete
