---
schema_version: 2
doc_type: phase_plan
title: "WKSP-304 Phase 4: Enforcing Flip + Deny Paths"
status: draft
created: 2026-07-08
phase: "P4"
phase_title: "The atomic arming step — Mode D core"
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
feature_slug: wksp-304-workspace-isolation-enforcement
entry_criteria:
  - "HARD GATE — MUST NOT START until Phase 3's TASK-3.6 100%-coverage checklist has signed off and task-completion-validator has reviewed it. This is the non-negotiable P3-to-P4 ordering invariant (decisions block D4; Risk 1, severity high)."
  - "Starting P4 with any unscoped AC-2 method causes a self-inflicted false-deny outage on a legitimate same-workspace read AND masks real leaks behind a false sense of enforcement. There is no partial-credit path here — the gate is binary."
exit_criteria:
  - "With flag enabled, cross-workspace access denied (404 read, list-omit, mutation-deny)"
  - "With identity=None, fully functional and behaviorally unchanged"
  - "Advisory mode unchanged from pre-Phase-4 behavior"
  - "task-completion-validator passes the fail-closed invariants (D3 ordering proof) before Phase 5 begins"
---

# Phase 4: Enforcing Flip + Deny Paths

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 3](./phase-3-query-layer-scoping.md)

**Duration**: ~1 day
**Dependencies**: Phase 3 complete AND TASK-3.6 signed off (see `entry_criteria` above — repeated deliberately, this is the plan's most important gate)
**Assigned Subagent(s)**: `backend-architect` (primary — owns deny-path wiring + D3 ordering proof), `python-backend-engineer` (secondary)

This is the single atomic "arm it" step. Everything built in P1-P3 is inert; this phase is where `allowed=False` becomes a real, consumed signal for the first time.

**Verifies**: AC-3 (Deny path), AC-5 (Mutation deny), and re-confirms AC-6 (single-operator fallback) at the point where it is most at risk — target_surfaces: `src/research_foundry/api/auth/scope.py`, and the 3 services (deny-path consumption).

---

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|-------------|-------|--------|---------------|
| TASK-4.1 | Flip `require_workspace_scope` to enforcing + D3 ordering proof | Flip the deny path: when `workspace_isolation_enforcement` resolves to enforcing AND `identity.workspace_id != record.workspace_id`, return `allowed=False` (today it always returns `True`). Construct the function so the `identity is None -> WorkspaceScopeResult(allowed=True, reason="single_operator_trust")` short-circuit is the literal first statement, evaluated before any flag read — not a reorderable runtime branch, but structurally first in the function body. A record with `workspace_id is None` is treated as a mismatch (deny) under enforcement, never defaulted to allowed. | `allowed=False` is returned for every enforcing-mode mismatch; the short-circuit for `identity is None` is provably first in execution order (code inspection + a test that would fail if the order were swapped); `workspace_id is None` denies. | 0.5 pt | backend-architect | sonnet | extended | Phase 3 TASK-3.6 signed off |
| TASK-4.2 | Wire 404-on-read + list-omit deny consumption | In the 3 services, consume the `allowed=False` signal from TASK-4.1: single-record read methods raise/propagate a not-found condition (surfaced as HTTP 404 via the router's existing `HTTPException` handling — no new error envelope). List methods rely on the Phase-3 query-layer predicate (now armed) to exclude the mismatched row — never a post-fetch filter. Resolves **OQ-1**: the 404 is silent to the caller (no existence-leaking signal); a structured audit-log entry is emitted server-side distinct from the existing advisory WARNING. | Cross-workspace read denies with 404, no distinguishing header/body signal to the caller; list results exclude mismatched rows via the query layer; a server-side audit log entry is emitted on every enforcing-mode denial. | 0.5 pt | backend-architect | sonnet | extended | TASK-4.1 |
| TASK-4.3 | Wire mutation-deny paths (AC-5) | Update/delete operations in the 3 in-scope routers (`catalog.py`, `agent_jobs.py`, `reports.py`) first resolve the target record's `workspace_id` via the now-scoped `get_item`/`get_draft`/`get_job` (TASK-4.1/4.2's deny path) before applying the mutation. A cross-workspace target denies with the same 404 semantics as a read, before any write executes. | No mutation SQL executes against a record whose workspace has not been verified — verified via a mock/spy test asserting zero UPDATE/DELETE calls for a cross-workspace target. | 0.3 pt | python-backend-engineer | sonnet | adaptive | TASK-4.2 |
| TASK-4.4 | (Optional, non-blocking) Deny-event telemetry | Resolves **OQ-2**: add a structured metric/telemetry increment on each enforcing-mode denial, distinct from the audit log entry in TASK-4.2, for security-monitoring/intrusion-detection purposes. Non-blocking — does not gate Phase 5; may be folded into TASK-4.2's audit-log change if trivial, or dropped if it introduces new dependencies. | If implemented: a denial increments a named counter/emits a structured event distinguishable from advisory-mode logging. If dropped: documented as an explicit non-blocking scope decision in the Phase 4 completion note. | 0.2 pt | backend-architect | sonnet | adaptive | TASK-4.2 |

**Phase 4 total**: 1.5 pts (matches decisions block §4 estimation anchor; TASK-4.4 is optional and absorbed within this budget).

---

## Quality Gates

- [ ] `identity is None` short-circuit is provably evaluated before any enforcement-flag read (D3 — Critical severity, no partial credit).
- [ ] Cross-workspace read denies with 404, silent to the caller (OQ-1 resolved: silent + server-side audit log).
- [ ] Cross-workspace list results exclude mismatched rows via the query layer (not post-fetch).
- [ ] Mutation endpoints verify target workspace before any write executes; zero-write test passes.
- [ ] Advisory mode (flag not enforcing) is behaviorally unchanged from pre-Phase-4 state.
- [ ] `task-completion-validator` reviews and passes the fail-closed invariants (this is an explicit, named gate per decisions block §1 — not folded into a generic phase-end pass).

## Key Files and Integration Points

- `src/research_foundry/api/auth/scope.py` — the enforcement gate itself.
- `src/research_foundry/services/catalog_service.py`, `builder_service.py`, `agent_job_service.py` — deny-path consumption (same files Phase 3 touched; sequential, not concurrent, so no serialization-barrier conflict).
- `src/research_foundry/api/routers/catalog.py`, `agent_jobs.py`, `reports.py` — mutation call sites (TASK-4.3); no new router code beyond the pre-mutation resolve-then-check pattern — 404 surfacing itself uses existing `HTTPException` handling.

---

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 3](./phase-3-query-layer-scoping.md) | [Next: Phase 5](./phase-5-regression-matrix.md)
