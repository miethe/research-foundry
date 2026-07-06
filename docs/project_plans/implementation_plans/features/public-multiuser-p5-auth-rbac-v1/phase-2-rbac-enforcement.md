---
title: "Phase 2: RBAC Enforcement (5-Role, Server-Side)"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: "v1"
phase: 2
phase_title: "RBAC Enforcement (5-Role, Server-Side)"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.1 identity contract frozen (AuthIdentity Protocol + local_static merged)"
exit_criteria:
  - "Non-role mutation attempt returns 403 across all 4 target_surfaces"
  - "route-sweep seam task RBAC-901 passes"
  - "Human gate #2 signed off"
  - "task-completion-validator sign-off"
related_documents:
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: backend-architect
ui_touched: false
target_surfaces:
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/api/routers/agent_jobs.py
seam_tasks:
  - RBAC-901
owner: python-backend-engineer
contributors:
  - backend-architect
priority: high
risk_level: high
category: "product-planning"
tags: [phase-plan, implementation, rbac, security, auth, mode-d]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/api/auth/provider.py
  - src/research_foundry/api/auth/rbac.py
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/api/routers/agent_jobs.py
---

# Phase 2: RBAC Enforcement (5-Role, Server-Side)

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: 3-4 days
**Effort**: 6 story points
**Dependencies**: Phase 1 (P5.1 — Auth-provider port + local_static + durable RBAC store) complete
**Team Members**: python-backend-engineer (primary), backend-architect (secondary, integration_owner)

---

> **MODE: D — High-Risk Change. MUST-STAY.** This phase is a Mode-D high-risk change per
> `.claude/rules/delegation-modes.md`: no ICA Sonnet 4.6 offload, no Codex delegation for
> implementation. RBAC-enforcement correctness is an explicit public-release blocking control
> (decisions block §3, Risk 2 — "Server-side RBAC gaps / UI-only enforcement leak", severity
> **high**). Model routing for this entire phase is `sonnet` / effort `extended`, Claude
> subscription only (decisions block §6).

---

## Phase Overview

This phase ships server-side, role-based access control (RBAC) over Research Foundry's mutation
surface. It defines the 5-role capability matrix (owner, admin, researcher, reviewer, viewer) and
implements it as a **single shared FastAPI dependency**, `require_role(...)`, applied per-route —
not per-route decorators. This is a **locked decision** (formerly Open Question OQ-A in the
decisions block, closed 2026-07-06): a single shared dependency was chosen over decorators for
R-P1 target_surfaces enumeration uniformity and testability, and is not to be re-opened in this
phase or in review.

`require_role(...)` reads role membership from `request.state.identity` (the `AuthIdentity`
established in Phase 1 by the resolved `AuthProvider`). Enforcement is **server-side only** — UI
affordance hiding (e.g., `AppShell.tsx`'s disabled-nav pattern) is never a substitute and never
satisfies this phase's exit gate (PRD FR-6, NFR Security, Mode-D gate 2 / AC-GATE-2).

### Goals

- Define an explicit 5-role × permission capability matrix (owner/admin/researcher/reviewer/viewer).
- Implement `require_role(...)` as a single shared FastAPI dependency (locked design, not decorators).
- Apply `require_role(...)` to every mutation route in the 4 enumerated `target_surfaces` below.
- Prove enforcement holistically via a mandatory route-sweep seam task (RBAC-901).
- Record the forward-compat contract for P4's `agent_jobs.py` (not yet landed) without gating this
  phase's exit on that file's existence.
- Record the `roles`-array resilience contract (RBAC-900) that Phase 8's frontend work consumes.

### Architecture Focus

- **Layer**: API (routers) + a new cross-cutting auth-support module (`api/auth/rbac.py`).
- **Patterns**: Single shared FastAPI dependency (`Depends(require_role(...))`), mirroring the
  existing `AuthProvider` Protocol+registry idiom from Phase 1 rather than introducing a second
  authorization shape. Enforcement reads `request.state.identity`, never re-derives identity.
- **Standards**: Fail-closed by default (PRD NFR Reliability — an ambiguous auth state, missing
  role, or unresolved workspace scope denies rather than allows). Consistent HTTPException
  envelopes: 403 for "authenticated but under-privileged", 404 where the existing no-existence-leak
  convention applies (landmine #4 — do not introduce a new leak pattern in this phase).

### Concrete `target_surfaces` (R-P1 — no "across"/"all routes"/"everywhere" language)

This phase's mutation-route enforcement scope is **exactly these 4 files** — no other router is
in scope for this phase:

1. `src/research_foundry/api/routers/catalog.py`
2. `src/research_foundry/api/routers/reports.py` — **this router also fronts
   `src/research_foundry/services/builder_service.py` mutations.** `builder_service.py` is a
   *service*, not a separate router; its `create_draft`/`update_draft` mutations are only reachable
   through `reports.py`'s route handlers, so gating `reports.py` routes is how builder mutations
   get covered. No separate `require_role` wiring is needed inside `builder_service.py` itself —
   the dependency lives at the router layer.
3. `src/research_foundry/api/routers/runs.py`
4. `src/research_foundry/api/routers/agent_jobs.py` — **does NOT exist yet in this worktree.** It
   lands in Phase 4 of the sibling `public-multiuser-p4-agents-v1` plan. Until P4 lands, this
   `target_surface` is **N/A / not yet applicable** for this phase's enforcement work. When P4
   lands, `agent_jobs.py` mutation routes **MUST** carry the same `require_role` dependency as the
   other 3 surfaces (see RBAC-005). **This phase's exit is not gated on P4 existing.**

---

## Phase Acceptance Criteria (structured, AC-schema format)

Per `.claude/skills/planning/references/ac-schema.md`, structured for FR-6 / cross-referencing
PRD AC-1's format and `verified_by` linkage.

#### AC RBAC-P2.1: Every mutation route in the 4 target_surfaces rejects an under-privileged identity
- target_surfaces:
    - src/research_foundry/api/routers/catalog.py
    - src/research_foundry/api/routers/reports.py
    - src/research_foundry/api/routers/runs.py
    - src/research_foundry/api/routers/agent_jobs.py  # N/A until P4 lands — see note above
- propagation_contract: >
    Each mutation route (POST/PUT/PATCH/DELETE) depends on `require_role(*allowed_roles)` from
    `api/auth/rbac.py`. The dependency reads `request.state.identity.roles` (set by Phase 1's
    `AuthProvider` middleware), checks membership against the route's declared allowed-roles set
    from the capability matrix (RBAC-001), and raises `HTTPException(403)` on failure before the
    route handler body executes. `agent_jobs.py` is a forward-compat entry only until P4 lands.
- resilience: >
    An identity with no matching role, an identity with an empty/missing `roles` array, and a
    request with no resolved identity at all (`auth_mode=none` aside) are all treated identically:
    denied. Ambiguous or unresolved workspace/role state fails closed, never open (PRD NFR
    Reliability).
- visual_evidence_required: false
- verified_by:
    - RBAC-901

#### AC RBAC-900: FE handles missing/least-privilege `roles` array (R-P2, backend contract)
- target_surfaces:
    - frontend/runs-viewer/src/auth/AuthContext.tsx
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: >
    This phase (P5.2) is the first to populate `AuthIdentity.roles` with real role-check semantics
    server-side; per R-P2, the implicit FE resilience AC for this new/consequential field is
    recorded here at the point of origin. **Backend responsibility in this phase**: guarantee the
    identity payload always serializes `roles` as a list (default `[]`, never `null`/omitted) and
    that `require_role(...)` treats an empty list as zero permissions. **FE implementation is
    Phase 8's job** (`public-multiuser-p5-auth-rbac-v1/phase-8-*.md`) — that phase file references
    this exact task ID (`RBAC-900`) rather than renumbering it.
- resilience: >
    A missing or empty `roles` array on an `AuthIdentity` payload is treated as least-privilege
    (viewer-equivalent) on both sides of the contract — never as an error, and never as a
    privilege escalation to a higher role by default. Matches PRD §11 "Additional acceptance
    criteria" list verbatim.
- visual_evidence_required: false
- verified_by:
    - RBAC-900-backend-contract-test (this phase)
    - frontend-auth-context-runtime-smoke (Phase 8, per PRD AC-5 `verified_by`)

---

## Task Breakdown

### Epic: 5-Role RBAC Enforcement

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|---------------------|-------|--------|--------------|
| RBAC-001 | Capability matrix design | Design the 5-role × permission capability matrix (owner/admin/researcher/reviewer/viewer) | Matrix reviewed and approved by backend-architect; covers catalog/report/builder/run/agent-job mutation types | 1 pt | backend-architect, python-backend-engineer | sonnet | extended | None |
| RBAC-002 | `require_role(...)` shared dependency | Implement the single shared FastAPI dependency (locked design — not per-route decorators) in new `api/auth/rbac.py` | Dependency callable with `*allowed_roles`; unit-tested against all 5 roles × allow/deny matrix | 1.5 pt | python-backend-engineer | sonnet | extended | RBAC-001 |
| RBAC-003 | Apply to `catalog.py` | Gate every mutation route in `catalog.py` with `require_role(...)` per the capability matrix | 403 on under-privileged role; unit test per mutation route | 1 pt | python-backend-engineer | sonnet | extended | RBAC-002 |
| RBAC-004 | Apply to `reports.py` (+ `builder_service.py` mutations) | Gate every mutation route in `reports.py`, covering the `builder_service.py` mutations it fronts | 403 on under-privileged role for report/builder mutations; unit test per mutation route | 1 pt | python-backend-engineer | sonnet | extended | RBAC-002 |
| RBAC-005 | Apply to `runs.py` + `agent_jobs.py` forward-compat note | Audit `runs.py` for any mutation (non-GET) routes and gate them; document the `agent_jobs.py` N/A-until-P4 contract in code comment + this phase file | 403 on under-privileged role for any `runs.py` mutation route found; forward-compat contract documented for P4 to consume | 0.5 pt | python-backend-engineer | sonnet | extended | RBAC-002 |
| RBAC-900 | AC: FE handles missing/least-privilege roles array | Backend-side contract task (R-P2): guarantee `AuthIdentity.roles` always serializes as a list (default `[]`), never null/omitted; add a contract test. FE implementation lands in Phase 8. | Serialization contract test green; Phase 8 phase file references this exact ID | 0.5 pt | python-backend-engineer | sonnet | extended | RBAC-001 |
| RBAC-901 | Seam verification: route-sweep — every mutation route across the 4 target_surfaces above carries a `require_role` dependency | Enumerate every mutation (POST/PUT/PATCH/DELETE) route in the 4 `target_surfaces`; assert each carries a `require_role(...)` dependency (or is documented N/A for `agent_jobs.py` pre-P4). This is the `rbac-route-sweep-test` referenced by PRD AC-1's `verified_by`. | Sweep test enumerates 100% of mutation routes in the 3 existing surfaces + explicit N/A marker for `agent_jobs.py`; 0 ungated mutation routes found | 0.5 pt | python-backend-engineer, backend-architect | sonnet | extended | RBAC-003, RBAC-004, RBAC-005 |

**Total**: 6 pts

**Model Selection Guidance**: This entire phase is `sonnet` / effort `extended` per decisions block
§6, MUST-stay on the Claude subscription (no ICA Sonnet 4.6, no Codex) — Mode-D classification per
Risk 2 (server-side RBAC gaps are a public-release blocker).

---

## Detailed Task Specifications

### Task RBAC-001: Capability matrix design

**Estimate**: 1 point
**Assigned Subagent(s)**: backend-architect, python-backend-engineer
**Model**: sonnet
**Effort**: extended
**Dependencies**: None
**started**: null
**completed**: null
**verified_by**: [RBAC-901]
**evidence**: []

**Description**:
Design an explicit permission matrix for the 5 roles (owner, admin, researcher, reviewer, viewer)
against the mutation types this phase governs: catalog create/update/delete, report/draft
create/update, report publish/share (composes with P5.6/D13 fail-closed checks — do not
re-implement those gates here, only gate role eligibility to invoke them), workspace member/role
management (owner/admin only), and a forward-compat row for agent-job launch (P4, not yet
implemented). Document the matrix as a table in `api/auth/rbac.py`'s module docstring and in this
phase file's Notes section once finalized.

**Acceptance Criteria**:
- [ ] All 5 roles have an explicit row; no role is implicitly "everything" or "nothing" by omission.
- [ ] Every mutation type from FR-6's scope (catalog, report/builder) has an explicit column.
- [ ] Matrix reviewed and approved by backend-architect (integration_owner) before RBAC-002 starts.
- [ ] `agent_jobs.py` forward-compat row included and marked N/A-until-P4, not silently dropped.

**Implementation Notes**:
- Owner and admin are both full-access on workspace content; the owner/admin distinction matters
  for workspace-level actions (ownership transfer, workspace deletion) that are largely out of this
  phase's scope (workspace isolation itself is P5.3) — keep this matrix scoped to mutation-route
  gating, not full workspace-lifecycle authorization.
- Reviewer is read + accept/reject-artifact only — no create/update on catalog or drafts.
- Viewer has zero mutation permissions — this is the baseline "missing/empty roles" resilience
  target used by RBAC-900.

**Files Involved**:
- `src/research_foundry/api/auth/rbac.py` — new module; matrix lives in a `ROLE_PERMISSIONS` constant.

---

### Task RBAC-002: `require_role(...)` shared dependency

**Estimate**: 1.5 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: extended
**Dependencies**: RBAC-001
**started**: null
**completed**: null
**verified_by**: [RBAC-901]
**evidence**: []

**Description**:
Implement `require_role(*allowed_roles: str) -> Callable` in `src/research_foundry/api/auth/rbac.py`
as a **single shared FastAPI dependency factory** (locked design, formerly OQ-A — do not implement
as per-route decorators). The returned dependency reads `request.state.identity` (an `AuthIdentity`
from Phase 1's `AuthProvider`), checks `identity.roles` against `allowed_roles` per the
`ROLE_PERMISSIONS` matrix from RBAC-001, and raises a consistent `HTTPException(403, ...)` on
denial. Treats a missing/empty `roles` array as zero permissions (feeds RBAC-900's resilience
contract).

**Acceptance Criteria**:
- [ ] `require_role(...)` is a single reusable dependency factory, not duplicated per-router logic.
- [ ] Unit-tested against all 5 roles × representative allow/deny cases from the matrix.
- [ ] Missing/empty `roles` array denies (never raises an unhandled error, never grants access).
- [ ] No route/RBAC code branches on `AuthProvider` identity (PRD FR-5 invariant preserved — RBAC
      logic is provider-agnostic, operating only on the resolved `AuthIdentity`).

**Implementation Notes**:
- Mirror the `adapters/base.py` Protocol+registry idiom's spirit (composable, no bespoke shape) even
  though RBAC itself is a dependency, not an adapter.
- 403 (not 404) is the correct response for "authenticated but under-privileged" — reserve 404 for
  the existing no-existence-leak convention (workspace-scoped record visibility is P5.3's job, not
  this phase's).

**Files Involved**:
- `src/research_foundry/api/auth/rbac.py` - `require_role()` dependency factory + `ROLE_PERMISSIONS`.
- `src/research_foundry/api/auth/provider.py` - read-only reference to `AuthIdentity` shape (owned
  by Phase 1; do not modify its contract here).

---

### Task RBAC-003: Apply to `catalog.py`

**Estimate**: 1 point
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: extended
**Dependencies**: RBAC-002
**started**: null
**completed**: null
**verified_by**: [RBAC-901]
**evidence**: []

**Description**:
Add `Depends(require_role(...))` to every mutation (POST/PUT/PATCH/DELETE) route in
`src/research_foundry/api/routers/catalog.py`, selecting the allowed-roles set per route from the
RBAC-001 matrix (e.g., catalog create/update likely owner/admin/researcher; catalog delete likely
owner/admin only).

**Acceptance Criteria**:
- [ ] Every mutation route in `catalog.py` carries a `require_role(...)` dependency.
- [ ] A per-route unit test asserts 403 for at least one under-privileged role and 200/expected
      success for at least one permitted role.
- [ ] No read-only (GET) route in `catalog.py` is altered by this task (RBAC governs mutations;
      read-path workspace scoping is P5.3's job).

**Implementation Notes**:
- Reference the finalized matrix from RBAC-001; do not invent ad hoc role sets per route.

**Files Involved**:
- `src/research_foundry/api/routers/catalog.py` - add `require_role(...)` to each mutation route.

---

### Task RBAC-004: Apply to `reports.py` (+ `builder_service.py` mutations)

**Estimate**: 1 point
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: extended
**Dependencies**: RBAC-002
**started**: null
**completed**: null
**verified_by**: [RBAC-901]
**evidence**: []

**Description**:
Add `Depends(require_role(...))` to every mutation route in
`src/research_foundry/api/routers/reports.py`, including the routes that front
`src/research_foundry/services/builder_service.py`'s `create_draft`/`update_draft` mutations.
`builder_service.py` itself is a service (no direct route surface) — the dependency is wired at the
`reports.py` router layer only; do not add a parallel enforcement mechanism inside
`builder_service.py`.

**Acceptance Criteria**:
- [ ] Every mutation route in `reports.py` carries a `require_role(...)` dependency, including
      routes that call into `builder_service.py`'s `create_draft`/`update_draft`.
- [ ] `publish_preview` and any sharing-flow route remain functionally unchanged by D13's fail-closed
      sensitivity checks — this task adds role eligibility gating *in addition to*, not instead of,
      those existing checks (composes with P5.6, does not replace it).
- [ ] A per-route unit test asserts 403 for at least one under-privileged role and success for at
      least one permitted role.

**Implementation Notes**:
- Reviewer role: read + accept/reject-artifact, not draft create/update — verify the matrix
  distinguishes these route-level actions correctly.

**Files Involved**:
- `src/research_foundry/api/routers/reports.py` - add `require_role(...)` to each mutation route.
- `src/research_foundry/services/builder_service.py` - no direct changes expected; confirm no
  bypass path exists that skips the router-layer dependency (e.g., no second HTTP-reachable entry
  point into `create_draft`/`update_draft`).

---

### Task RBAC-005: Apply to `runs.py` + `agent_jobs.py` forward-compat note

**Estimate**: 0.5 point
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: extended
**Dependencies**: RBAC-002
**started**: null
**completed**: null
**verified_by**: [RBAC-901]
**evidence**: []

**Description**:
Audit `src/research_foundry/api/routers/runs.py` for any mutation (non-GET) routes and gate each
with `require_role(...)`. Per PRD §2 code-truth confirmation, `runs.py`'s documented endpoints
(`/runs/{id}`, `/claims`, `/sources/{id}`) are currently read-only (GET) and are governed by the
**existence-gate** work in P5.7 (FR-13), not by this phase's role-gating — if the audit confirms no
mutation routes exist in `runs.py` today, document that finding explicitly rather than silently
skipping it. Separately, add a code comment in `api/auth/rbac.py` (or a new
`src/research_foundry/api/routers/agent_jobs.py`-adjacent doc note) recording the forward-compat
contract: **when P4 lands, `agent_jobs.py` mutation routes MUST carry the same `require_role`
dependency; until then this target_surface is N/A / not yet applicable.**

**Acceptance Criteria**:
- [ ] Any mutation route discovered in `runs.py` carries `require_role(...)`; if none exist, this
      is documented as an explicit finding (not a silent no-op).
- [ ] A forward-compat contract note for `agent_jobs.py` exists in the codebase (comment/docstring)
      referencing this phase and RBAC-901, so P4's implementer finds it without re-deriving intent.
- [ ] This task does not implement existence-gate parity (FR-13) — that is explicitly P5.7's scope.

**Implementation Notes**:
- Do not conflate "no mutation routes found in runs.py" with "this task is complete without
  investigation" — the audit itself is the deliverable if no mutations exist.

**Files Involved**:
- `src/research_foundry/api/routers/runs.py` - audit + gate any mutation routes found.
- `src/research_foundry/api/auth/rbac.py` - forward-compat contract note for `agent_jobs.py`.

---

### Task RBAC-900: AC — FE handles missing/least-privilege roles array

**Estimate**: 0.5 point
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: extended
**Dependencies**: RBAC-001
**started**: null
**completed**: null
**verified_by**: [RBAC-901]
**evidence**: []

**Description**:
Per R-P2 (every new/consequential backend field introduces an implicit "FE handles missing X" AC),
this task records and backend-verifies the resilience contract for `AuthIdentity.roles`: the field
must always serialize as a list (default `[]`, never `null`/omitted), and any consumer (including
`require_role(...)` itself) must treat an empty list as least-privilege/viewer-equivalent — never
as an error, never as a privilege escalation. **This task's scope is the backend contract and its
test; the FE rendering behavior itself is implemented in Phase 8**
(`public-multiuser-p5-auth-rbac-v1/phase-8-*.md`), which references this exact task ID (`RBAC-900`)
rather than minting a new one.

**Acceptance Criteria**:
- [ ] `AuthIdentity.roles` serialization is contract-tested: absent/empty input on the identity
      resolution path always yields `roles: []` in the outbound payload, never `null` or a missing
      key.
- [ ] `require_role(...)` (RBAC-002) demonstrably denies for an empty `roles` list (already covered
      by RBAC-002's own tests; this task cross-references, does not duplicate).
- [ ] Phase 8's phase file (frontend) is confirmed (at plan-assembly time) to reference `RBAC-900`
      by this exact ID.

**Implementation Notes**:
- This is a coordination/contract task, not a full frontend implementation — keep its footprint to
  the backend serialization contract test.

**Files Involved**:
- `src/research_foundry/api/auth/provider.py` - confirm `AuthIdentity.roles` default/serialization.
- `frontend/runs-viewer/src/auth/AuthContext.tsx` - not modified in this phase (ui_touched: false);
  listed here only as the AC's target_surface per the AC schema — implementation is Phase 8's.

---

### Task RBAC-901: Seam verification — route-sweep

**Estimate**: 0.5 point
**Assigned Subagent(s)**: python-backend-engineer, backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: RBAC-003, RBAC-004, RBAC-005
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
Seam verification: route-sweep — every mutation route across the 4 target_surfaces above carries a
`require_role` dependency. This task is the concrete implementation of the `rbac-route-sweep-test`
referenced by PRD AC-1's `verified_by` field, and is this phase's mandatory seam task per R-P3 (2
owner specialties — python-backend-engineer + backend-architect — share `files_affected` with
Phase 1 via `api/auth/provider.py` and with Phase 4/P5.4 via the Clerk-adjacent role-mapping
surface). Programmatically enumerate every mutation route in `catalog.py`, `reports.py`, and
`runs.py`; assert each carries a `require_role(...)` dependency in its FastAPI route definition.
Assert `agent_jobs.py` is explicitly and machine-readably marked N/A (not silently absent from the
sweep's coverage report).

**Acceptance Criteria**:
- [ ] Sweep enumerates 100% of mutation (POST/PUT/PATCH/DELETE) routes in `catalog.py`, `reports.py`,
      and `runs.py`.
- [ ] 0 mutation routes found without a `require_role(...)` dependency in the 3 existing surfaces.
- [ ] `agent_jobs.py` appears in the sweep's report as an explicit N/A-until-P4 entry, not omitted.
- [ ] backend-architect (integration_owner) signs off on the sweep's completeness before Human
      Gate #2 is requested.

**Implementation Notes**:
- This is the seam task referenced in phase frontmatter (`seam_tasks: [RBAC-901]`) — do not mark
  this phase complete until this task's `verified_by` chain is populated and its own findings are
  clean.
- Prefer an automated route-introspection test (walk `app.routes`, filter by HTTP method, assert
  dependency presence) over a manually-maintained checklist — manual checklists rot as routes are
  added.

**Files Involved**:
- `src/research_foundry/api/routers/catalog.py` - swept, not modified.
- `src/research_foundry/api/routers/reports.py` - swept, not modified.
- `src/research_foundry/api/routers/runs.py` - swept, not modified.
- `src/research_foundry/api/routers/agent_jobs.py` - N/A entry, file does not exist yet.
- New test file (e.g. `tests/unit/test_rbac_route_sweep.py`) implementing the sweep assertion.

---

## Human Gate #2

**This phase cannot be considered exited, and the RBAC surface it implements cannot be exposed on
any public or shared-LAN deployment, until a human has explicitly signed off that server-side RBAC
— not UI hiding — enforces catalog, report, and (when applicable) agent-job visibility and
mutation eligibility.**

- **Gate**: Human Gate #2 (RBAC-before-exposure sign-off), per decisions block §1 (P5.2 Exit Gate)
  and PRD Mode-D gate 2 / AC-GATE-2 ("Explicit sign-off that server-side RBAC (not UI hiding)
  enforces catalog visibility, obtained before any public/LAN exposure of this phase's work").
- **Preconditions for requesting sign-off**:
  - RBAC-901 (route-sweep) is green with 0 ungated mutation routes across the 3 existing
    `target_surfaces`.
  - `task-completion-validator` has reviewed this phase's diff and Completion Report.
  - The capability matrix (RBAC-001) and its enforcement (RBAC-002 through RBAC-005) are the
    reviewer's basis for sign-off — not a description of intended behavior, but a route-sweep
    result showing it is actually true.
- **Blocking scope**: blocks **public/shared exposure** of this phase's work, not raw task
  completion tracking. A phase can be internally "done" (all tasks checked, tests green) while
  still awaiting this human sign-off before the surface it governs is exposed beyond the operator's
  own trusted context.
- **Sign-off record**: capture the human approver, date, and scope of approval in this phase file's
  `commit_refs`/Notes section once granted (do not proceed to public exposure without it).

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: Every mutation route in `catalog.py`, `reports.py`, and `runs.py` carries a
      `require_role(...)` dependency; `agent_jobs.py` carries the documented N/A-until-P4 note.
- [ ] **Testing**: Route-sweep (RBAC-901) green; per-route unit tests for RBAC-003/004/005; the
      RBAC-900 backend serialization contract test green.
- [ ] **Performance**: Role-check overhead is negligible (in-process list membership check against
      an already-resolved `AuthIdentity` — no new I/O or network round-trip introduced).
- [ ] **Security**: Enforcement is server-side only over `request.state.identity` — no route relies
      on client-supplied role claims or UI-only hiding (Mode-D gate 2 / Risk 2 mitigation).
- [ ] **Documentation**: `ROLE_PERMISSIONS` capability matrix documented in `api/auth/rbac.py`'s
      module docstring; `agent_jobs.py` forward-compat contract documented for P4's implementer.
- [ ] **Code Quality**: `flake8`/`mypy` clean on all modified/added files; no duplicated per-router
      role-check logic (single shared dependency, per locked design decision).
- [ ] **Architecture**: `require_role(...)` is the single shared FastAPI dependency, not per-route
      decorators (locked decision, formerly OQ-A) — reviewer should reject any per-route decorator
      pattern found in the diff.
- [ ] **Seam verification** (`integration_owner: backend-architect`): RBAC-901 is completed and its
      `verified_by`/evidence are populated (R-P3).
- [ ] **Runtime smoke**: N/A this phase (`ui_touched: false` — no `*.tsx` files in
      `files_affected`; R-P4's UI-smoke requirement does not apply here. RBAC-900's FE-facing smoke
      is Phase 8's responsibility).
- [ ] **Human Gate #2**: signed off per the section above — blocks public/LAN exposure specifically,
      tracked separately from raw task completion.
- [ ] **task-completion-validator**: sign-off obtained per Tier-3 reviewer gate policy.

---

## Integration Points

### External Systems

- None — this phase has no external-system integration; it is purely an internal cross-cutting
  authorization layer over existing routers.

### Internal Systems

- **Phase 1 (`api/auth/provider.py`)**: this phase reads `request.state.identity` established by
  Phase 1's `AuthProvider` middleware; it does not modify Phase 1's `AuthIdentity` contract.
- **Phase 3 (workspace isolation)**: this phase's role gating is orthogonal to but composes with
  Phase 3's workspace-scoping — a request can pass RBAC (right role) and still be denied by Phase
  3's workspace-scoping (wrong workspace). Do not conflate the two: RBAC-003/004/005 gate role
  eligibility only.
- **Phase 4 (Clerk adapter)**: shares the role-mapping surface conceptually (Clerk Organizations
  roles map 1:1 onto this phase's 5-role matrix) — `backend-architect` (integration_owner) is
  responsible for confirming Phase 4's Clerk role-mapping does not diverge from RBAC-001's matrix.
- **Phase 6 (sharing/publish gates)**: reuses this phase's role-eligibility gating in addition to
  (not instead of) D13's fail-closed sensitivity checks on `publish_preview`.
- **Phase 7 (deferred sensitivity / FU-4)**: existence-gate parity on `runs.py`'s GET endpoints is
  explicitly out of scope here (RBAC-005 note) — do not duplicate that work in this phase.
- **Phase 8 (frontend auth-context)**: consumes RBAC-900's backend contract; references task ID
  `RBAC-900` verbatim rather than renumbering.
- **Sibling P4 plan (`public-multiuser-p4-agents-v1`)**: `agent_jobs.py` (Phase 4 of that plan) must
  carry `require_role(...)` when it lands, per the forward-compat note in RBAC-005.

---

## Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `src/research_foundry/api/auth/rbac.py` (new) | `ROLE_PERMISSIONS` matrix + `require_role(...)` dependency factory | python-backend-engineer, backend-architect |
| `src/research_foundry/api/auth/provider.py` | Read-only reference to `AuthIdentity` shape (owned by Phase 1) | python-backend-engineer |
| `src/research_foundry/api/routers/catalog.py` | Apply `require_role(...)` to mutation routes | python-backend-engineer |
| `src/research_foundry/api/routers/reports.py` | Apply `require_role(...)` to mutation routes (fronts `builder_service.py`) | python-backend-engineer |
| `src/research_foundry/services/builder_service.py` | Confirmed no bypass path around router-layer gating | python-backend-engineer |
| `src/research_foundry/api/routers/runs.py` | Audit for mutation routes; gate any found | python-backend-engineer |
| `src/research_foundry/api/routers/agent_jobs.py` (N/A, not yet created) | Forward-compat contract note only | python-backend-engineer |
| `tests/unit/test_rbac_route_sweep.py` (new) | RBAC-901 route-sweep assertion | python-backend-engineer |

---

## Testing Strategy

### Unit Tests

- Capability-matrix unit tests: all 5 roles × representative allow/deny cases (RBAC-001/RBAC-002).
- Per-route tests for each mutation route in `catalog.py` and `reports.py`: 403 for one
  under-privileged role, success for one permitted role (RBAC-003/RBAC-004).
- `runs.py` audit test/finding (RBAC-005): either "N mutation routes found, all gated" or "0
  mutation routes found, documented".
- RBAC-900 backend contract test: `AuthIdentity.roles` serializes as `[]` (never null/omitted) when
  absent; `require_role(...)` denies for an empty list.

### Integration Tests

- Route-sweep integration test (RBAC-901): walks the live FastAPI `app.routes`, filters
  POST/PUT/PATCH/DELETE handlers in the 3 existing `target_surfaces`, asserts a `require_role(...)`
  dependency is present on each. Reports `agent_jobs.py` as an explicit N/A line item.

### E2E Tests (if applicable)

- None in this phase — E2E RBAC coverage is Phase 9's scope (`p5-auth-rbac.spec.ts`, static + live
  modes, per PRD AC-4).

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Server-side RBAC gaps / UI-only enforcement leak (decisions block §3, Risk 2) | High | R-P1 enumerated `target_surfaces` (this phase file); per-route role-assertion tests; mandatory RBAC-901 route-sweep; Human Gate #2 before any exposure; Codex adversarial pass scheduled in Phase 9. |
| `agent_jobs.py` N/A note gets silently forgotten and P4 ships an ungated router | Medium | Forward-compat contract explicitly documented in code (RBAC-005) and in this phase file; RBAC-901's sweep report includes `agent_jobs.py` as a tracked N/A line, not an omission, making its future absence-of-gating visible when P4 lands. |
| RBAC-900's backend/frontend split (contract here, implementation Phase 8) causes the two phases to drift on the exact ID or contract wording | Low | Task ID `RBAC-900` is fixed verbatim across both phase files by explicit instruction; this phase file's RBAC-900 description states the split explicitly. |
| `require_role(...)` implemented as per-route decorators instead of the locked shared-dependency design (re-opening closed OQ-A) | Medium | Locked decision restated at the top of this phase file and in RBAC-002's task description; `task-completion-validator` should reject a decorator-based diff. |

---

## Success Metrics

- **Completion**: All 7 tasks (RBAC-001 through RBAC-005, RBAC-900, RBAC-901) checked off.
- **Quality**: All Quality Gates passed, including Human Gate #2.
- **Coverage**: 0 mutation routes in `catalog.py`/`reports.py`/`runs.py` found ungated by RBAC-901's
  sweep; `agent_jobs.py` carries an explicit, discoverable N/A note.
- **Testing**: 100% of mutation routes in the 3 existing `target_surfaces` covered by a per-route
  RBAC unit test; RBAC-900's backend contract test green.

---

## Notes

### Implementation Approach

Build the capability matrix and shared dependency first (RBAC-001, RBAC-002) before touching any
router — this avoids re-deriving role sets ad hoc per router and keeps the enforcement mechanism
uniform across all 3 existing `target_surfaces`, which is exactly what RBAC-901's sweep verifies.

### Gotchas

- **Do not re-open OQ-A**: the shared-dependency-vs-decorator question is locked. A decorator-based
  implementation, even if functionally equivalent, fails this phase's architecture Quality Gate.
- **Do not conflate RBAC with workspace isolation**: a request can have the right role and still be
  denied by Phase 3's workspace scoping. RBAC-003/004/005 only gate role eligibility.
- **`runs.py` may have zero mutation routes today** — if so, RBAC-005's deliverable is the
  documented audit finding, not invented gating work.
- **`builder_service.py` has no direct route surface** — do not add a second enforcement mechanism
  inside the service layer; the router-layer dependency on `reports.py` is sufficient and is the
  locked design.

### Learnings

*(populate during execution)*

### Findings Captured This Phase

- [ ] No new findings this phase (default)
- OR
- **Discoveries**: [brief summary + link to findings doc entry]
- **Plan / Reality Mismatches**: [...]
- **Bugs / Gotchas**: [file:line or commit ref]
- **Schema / Data Gaps**: [...]

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
