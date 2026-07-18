---
title: "Implementation Plan: Runs Writeback — Approve & Dispatch (v1)"
schema_version: 2
doc_type: implementation_plan
it_schema: 1
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: "runs-writeback-approve-dispatch"
feature_version: "v1"
tier: 2
prd_ref: docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md
plan_ref: null
scope: "Add a governed write path (new API endpoint + runs-viewer UI action) that lets an operator approve a run and dispatch it to MeatyWiki/SkillMeat/CCDash from the viewer, by orchestrating the existing build_bundle/council_review/writeback chain behind a mandatory governance gate, RBAC-ready auth, and full per-invocation audit."
effort_estimate: "~14 pts (Tier 2)"
architecture_summary: "One new service-layer orchestration function composing existing build_bundle/council_review/guard_check/dispatch primitives with per-target isolation; one new RBAC-gated, audited API route; one new runs-viewer UI action on the existing Writeback tab. No new tables, no schema migrations, no export-schema changes."
related_documents:
  - docs/project_plans/feature_contracts/features/runs-writeback-review-view.md
  - docs/project_plans/design-specs/runs-writeback-preview.md
  - docs/project_plans/PRDs/features/runs-frontend-v1.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/human-briefs/runs-writeback-approve-dispatch.md
references:
  user_docs: []
  context: []
  specs:
    - .claude/specs/changelog-spec.md
  related_prds:
    - docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md
spike_ref: null
adr_refs: []
deferred_items_spec_refs: []
findings_doc_ref: null
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: null
contributors: []
priority: high
risk_level: high
category: "product-planning"
tags: [implementation, planning, phases, tasks, writeback, governance, rbac, runs-viewer]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/writeback.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/services/audit_service.py
  - src/research_foundry/api/routers/writeback.py
  - src/research_foundry/api/auth/rbac.py
  - frontend/runs-viewer/src/api/client.ts
  - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
  - CHANGELOG.md
planning_maturity: in_progress
open_questions: []
decisions:
  - decision: "D1 — council_review() runs automatically on every invocation (implicit run_council=true), never conditionally skipped."
    rationale: "Resolves PRD OQ-1. council_review() re-derives deterministically from verification and is cheap; always-run is simpler and more auditable than a stale-result-reuse path."
    status: locked
  - decision: "D2 — Concurrency guard is a lightweight advisory lock (a short-TTL .dispatch.lock file per run), not a hard 409-reject or a distributed lock."
    rationale: "Resolves PRD OQ-2/FR-14. Matches Risk R2's own accepted mitigation; today's deployment is single-operator LAN, so distributed-lock infrastructure would be over-engineering. Both racing attempts still each produce an audit row, so the race stays fully visible after the fact."
    status: locked
  - decision: "D3 — New route lives in a new file, api/routers/writeback.py, not appended into runs.py."
    rationale: "Follows agent_jobs.py's file-per-concern precedent explicitly named in the PRD; keeps runs.py's established GET-heavy scope from growing into a second unrelated mutation surface."
    status: locked
  - decision: "D4 — The orchestration function calls the per-target render primitives directly (_render_meatywiki, _render_skillbom, telemetry.emit_ccdash_event) rather than calling the monolithic writeback(), to get per-target try/except isolation without changing writeback()'s existing CLI-facing behavior."
    rationale: "writeback()'s existing loop has no per-target isolation (PRD §2) and FR-13 already established that CLI behavior must stay byte-identical (FR-13 constraint reused here as FR-13-of-this-PRD)."
    status: locked
decision_gates: []
success_metrics:
  - "An operator can approve a completed run for writeback and see per-target (MeatyWiki/SkillMeat/CCDash) dispatch outcomes without leaving the runs-viewer, in a single action."
  - "100% of approve+dispatch invocations produce exactly one audit_event row (mutation_type=writeback), regardless of outcome (success/partial/blocked/failure)."
  - "0 approve+dispatch invocations bypass the governance guard_check() gate — verified by test, not just code review."
contributors_note: null
scores: {}
acceptance_criteria:
  - "POST /api/runs/{run_id}/writeback/approve orchestrates build_bundle -> council_review -> guard_check -> per-target dispatch in that order, gated by require_role(owner, admin)."
  - "A blocking guard_check() result aborts before any target is attempted and writes zero files under writebacks/."
  - "Exactly one audit_event row (mutation_type=writeback) is written per invocation across all four outcome classes: success, partial, blocked, unexpected exception."
  - "runs-viewer Writeback tab gains an Approve & Dispatch action that renders per-target outcomes without regressing FR-13's read-only preview cards."
execution_mode: unassigned
agent_title: "API + UI write path for run writeback approval and dispatch"
agent_summary: "Wire guard_check() into a new approve_and_dispatch() orchestration function, expose it via a governed POST route with per-invocation audit + identity threading, and add the corresponding Approve & Dispatch action to the runs-viewer Writeback tab."
agent_context: "Follow POST /agent-jobs (api/routers/agent_jobs.py) as the direct precedent for RBAC gating, governance_rejected error mapping, and audit_service wiring. Do not modify writeback(), council_review(), or build_bundle()'s existing signatures or CLI-facing behavior — this feature composes them, it does not change them."
wave_plan:
  serialization_barriers: []
  phases:
    - id: P1
      depends_on: []
      isolation: worktree
      parallelizable: true
      owner_skills: []
      entry_criteria:
        - "PRD accepted; services/writeback.py, services/governance.py, services/audit_service.py read and understood at the call-site level (paths already cited in PRD Key Code References)."
      exit_criteria:
        - "approve_and_dispatch() exists, is unit-testable in isolation from any HTTP layer, and its request/response DTO shape is locked for Phase 2/3 to build against."
      files_affected:
        - src/research_foundry/services/writeback.py
    - id: P2
      depends_on: [P1]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      entry_criteria:
        - "P1's approve_and_dispatch() signature and return shape are locked (TASK-1.1 design review complete)."
      exit_criteria:
        - "POST /api/runs/{run_id}/writeback/approve is RBAC-gated, audited for all outcome classes, and rbac.py's classification docstring is updated."
      files_affected:
        - src/research_foundry/api/routers/writeback.py
        - src/research_foundry/api/auth/rbac.py
    - id: P3
      depends_on: [P1]
      isolation: shared
      parallelizable: true
      owner_skills: [frontend-design]
      entry_criteria:
        - "P1's response DTO shape is locked (does not require P2's route to be live to begin UI shell + client typing)."
      exit_criteria:
        - "Approve & Dispatch button, confirmation dialog, and per-target outcome rendering exist on the Writeback tab; FR-13's read-only preview cards are unchanged."
      files_affected:
        - frontend/runs-viewer/src/api/client.ts
        - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
    - id: P4
      depends_on: [P2, P3]
      isolation: shared
      parallelizable: false
      files_affected:
        - CHANGELOG.md
      entry_criteria:
        - "P2's live route and P3's UI action both exist and can be exercised end-to-end."
      exit_criteria:
        - "Full validation suite green; karen feature-end gate passed; CHANGELOG entry present under [Unreleased]."
  waves:
    - [P1]
    - [P2, P3]
    - [P4]
---

# Implementation Plan: Runs Writeback — Approve & Dispatch (v1)

**Plan ID**: `IMPL-2026-07-18-RUNS-WRITEBACK-APPROVE-DISPATCH`
**Date**: 2026-07-18
**Author**: implementation-planner (Sonnet 5)
**Human Brief**: `docs/project_plans/human-briefs/runs-writeback-approve-dispatch.md`
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md`
- **FR-13 Feature Contract** (read-only foundation this builds on): `docs/project_plans/feature_contracts/features/runs-writeback-review-view.md`

**Complexity**: Medium (M) — 4 phases, cross-stack (Python service + API + React), `risk_level: high` (Mode D external side-effects + first-ever identity/audit threading)
**Total Estimated Effort**: ~14 pts
**Target Timeline**: 1–1.5 weeks

> **Estimation Sanity Check**: See Human Brief §2 at `docs/project_plans/human-briefs/runs-writeback-approve-dispatch.md`.
> Bottom-up: P1 ~4 pts + P2 ~3.75 pts + P3 ~2.75 pts + P4 ~3.25 pts ≈ 13.75 pts, rounds to ~14 pts.
> Anchors to the PRD's own WBAD-001..004 backlog (10–14 pts) and to FR-13 (~5–6 pts, read-only half of
> this same surface) — the ~2.3x delta over FR-13 is justified by RBAC/audit/governance wiring FR-13
> never needed.

## Executive Summary

FR-13 gave the runs-viewer a read-only view of writeback candidates and governance verdicts; this
plan adds the write path. Phase 1 builds a single new orchestration function that composes the
existing `build_bundle` → `council_review` → `guard_check` → dispatch chain with per-target failure
isolation (none of these are modified). Phase 2 exposes it as a governed, audited API route following
`POST /agent-jobs`'s exact precedent. Phase 3 adds the "Approve & Dispatch" action to the existing
Writeback tab. Phase 4 closes with the full RBAC/governance/audit test matrix, a CHANGELOG entry, and
the mandatory Tier 2 `karen` end-of-feature gate. No new tables, no schema migrations, no export-schema
(`run.json`) changes.

## Implementation Strategy

### Architecture Sequence

This feature follows the layered pattern established by `POST /agent-jobs`, adapted for a
service-composition (not new-persistence) feature:

1. **Service Orchestration Layer** — new `approve_and_dispatch()` function composing existing services
2. **API Layer** — thin router: RBAC dependency, request/response DTOs, `governance_rejected` error mapping, audit call
3. **UI Layer** — typed client binding + Approve & Dispatch action on the existing Writeback tab
4. **Testing & Hardening Layer** — full RBAC/governance/isolation/idempotency/audit test matrix, CHANGELOG, karen gate

No Database, Repository, or Deployment layers are needed — this feature introduces zero new persisted
state and is inert (additive, unreachable) until the new route is explicitly invoked, so no feature
flag is required (PRD §7).

### Parallel Work Opportunities

- **P2 (API layer) and P3 (frontend UI) both depend only on P1** and can run in the same wave. P3's
  typed client binding and dialog UI can be built against the response DTO shape locked in TASK-1.1's
  design review without waiting for P2's live route — but P3's end-to-end integration testing
  (TASK-4.5) still gates on P2 being live.
- Do not squash-merge P3 ahead of P2 if the two diverge on the response DTO shape mid-flight;
  reconcile via P2's review checkpoint (TASK-2.5) first.

### Critical Path

```
P1 (orchestration function, locks DTO shape)
  |
  +--> P2 (API: RBAC + audit + governance gate) --+
  |                                                 |
  +--> P3 (UI: Approve & Dispatch action) ---------+--> P4 (tests, hardening, docs, karen gate)
```

P1 is the hard gate: nothing else can be built against a real contract until TASK-1.1's design review
locks the orchestration function's signature and response shape.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| 1 | Backend Orchestration | 4 pts | python-backend-engineer, backend-architect | sonnet | Mode D risk; isolation: worktree; design review gates the DTO shape |
| 2 | API Layer — Auth, Audit, Governance Gate | 3.75 pts | python-backend-engineer, backend-architect | sonnet | Mode D risk; isolation: worktree; mandatory review checkpoint (RBAC/audit surface) |
| 3 | UI Layer — Approve & Dispatch | 2.75 pts | ui-engineer-enhanced, frontend-developer | sonnet | Parallel to P2; runs against locked P1 DTO shape |
| 4 | Tests, Hardening & Docs | 3.25 pts | python-backend-engineer, ui-engineer-enhanced, changelog-generator, task-completion-validator, karen | sonnet (impl), haiku (changelog), opus (karen) | Mandatory karen end-of-feature gate (Tier 2) |
| **Total** | — | **~13.75 pts (~14 pts)** | — | — | See Human Brief §2 for full H1–H6 rationale |

**Model column conventions**: Claude-only phases list the Claude model directly; `opus` appears only
for the mandatory `karen` gate task in Phase 4.

## Deferred Items & In-Flight Findings Policy

### Deferred Items

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-------------------|
| DI-WBAD-1 | backlog | UI dispatch of `intenttree`/`arc`/`notebooklm` targets is out of scope (PRD §7) — these are live-push targets with different retry/idempotency semantics than the 3 default local-file targets. | 3-target UI pattern has run in production for a period and an operator requests the opt-in targets in the viewer. | `docs/project_plans/design-specs/runs-writeback-opt-in-targets-ui.md` |
| DI-WBAD-2 | backlog | Automated rollback/undo of a completed dispatch is out of scope (PRD Risk R3) — the existing overwrite-idempotent re-render already gives a manual remediation path. | Manual remediation proves insufficient at higher dispatch volume, or a target becomes a live push where overwrite-idempotency no longer holds. | `docs/project_plans/design-specs/writeback-dispatch-rollback.md` |
| DI-WBAD-3 | dependency-blocked | Hard distributed lock for concurrent approve+dispatch is deferred in favor of D2's lightweight advisory lock — today's deployment is single-operator LAN. | Multi-tenant OIDC ships and real concurrent-operator collisions are observed (not merely theoretically possible). | `docs/project_plans/design-specs/writeback-dispatch-distributed-lock.md` |

DOC-006 (Phase 4) authors all three specs at `maturity: idea` (research/trigger-condition still
pending) with `prd_ref` set to this plan's parent PRD.

### In-Flight Findings

Findings doc is NOT pre-created (lazy-creation rule). If a load-bearing plan/reality mismatch surfaces
during execution, create `.claude/findings/runs-writeback-approve-dispatch-findings.md`, set
`findings_doc_ref` in this plan's frontmatter, and append the path to `related_documents`.

### Quality Gate

Phase 4 (DOC-006 + DOC-007) cannot be sealed until all three deferred items above have a design-spec
path in `deferred_items_spec_refs`, and — if `findings_doc_ref` is populated — the findings doc is
finalized (`draft` → `accepted`).

---

## Rollback & Mitigation — Mode D External-Side-Effect Risk

This feature's dispatch step writes real files into shared, out-of-band-consumed workspace mirrors
(`meatywiki/sources/`, `skillmeat/skillboms/`, `ccdash/events/`) — not sandboxed test fixtures. Treat
Phase 1/2 as Mode D (High-Risk Change) territory for anything touching the actual dispatch call path
in a shared environment, per `.claude/rules/delegation-modes.md`.

**Mitigations already designed in (do not re-derive):**
- **Idempotent overwrite, not append** (PRD FR-9, reused from existing `writeback()` ID-determinism):
  re-running dispatch for the same run overwrites the same candidate/mirror files rather than creating
  duplicates. This is the primary rollback mechanism — if a dispatch is wrong, re-run with corrected
  content rather than attempting to "undo" a write.
- **Governance gate runs first** (FR-3): a blocking `guard_check()` result means **zero files are
  written** for that invocation — the failure mode is "nothing happened," not "partial garbage was
  written," for the single most common risk case (secret leakage, key-profile mismatch).
- **Per-target isolation** (FR-7, D4): a failure in one target (e.g., disk I/O error rendering
  meatywiki) does not corrupt or block the other two targets, and the response reports exactly which
  target failed — no silent partial-success masquerading as full success.

**Explicit non-mitigations (accepted, do not build in this feature):**
- No automated rollback/undo of a completed dispatch (DI-WBAD-2 — deferred, manual remediation only).
- No hard distributed lock against concurrent dispatch (DI-WBAD-3 — deferred, advisory lock only per D2).

**Rollout guardrail for execution**: Phase 1 and Phase 2 tasks should be developed and initially
validated against a disposable/test run (not a real production run with meaningful workspace-mirror
consumers) until TASK-4.1–TASK-4.4's test matrix is green. Do not manually invoke the new endpoint
against a real operator-relied-upon run until Phase 4's audit-row and per-target-isolation tests pass.

**If a bad dispatch reaches a shared workspace mirror despite the above**: the manual remediation path
is to correct the run's content, re-invoke approve+dispatch (overwrite takes effect immediately), and
manually delete/replace the stale mirror file only if the target system's out-of-band consumer already
ingested the bad version before the overwrite landed. This manual path should be documented in Phase
4's docs update (DOC-003) since it's the only recovery mechanism this feature ships with.

---

## Phase Breakdown

**Column conventions** (apply to every phase task table below):
- `Estimate` — story points. `Model` — `sonnet` | `haiku` | `opus`. `Effort` — `adaptive` | `extended` (Claude only; this plan uses Claude models exclusively).

### Phase 1: Backend Orchestration

**Duration**: ~2 days
**Dependencies**: None
**Isolation**: worktree (Mode D — external side-effects, dispatch path)
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|-------|--------|--------------|
| ORC-001 | Design review — orchestration contract | Lock: (a) module location for `approve_and_dispatch()` (extend `services/writeback.py` per D4, not `writeback()` itself); (b) request/response DTO shape (bundle_id, verified, council_decision, reviewer_notes, required_fix, guard result, per-target status[], overall_status); (c) D1 (always-run council) and D2 (advisory lock) applied concretely. | Written decision note (inline docstring or brief comment block) records the locked DTO shape; python-backend-engineer and Phase 2/3 owners can build against it without further design questions. | 0.5 pts | backend-architect | sonnet | extended | None |
| ORC-002 | Implement `approve_and_dispatch()` orchestration | Compose `build_bundle(run_id, verify=True)` -> `council_review(...)` (always run, D1) -> `guard_check()` via `load_run_context(run_id, writeback_targets=...)` -> per-target dispatch. Guard check MUST execute before any target dispatch call. | PRD Functional Acceptance rows 1-2: guard_check() runs before dispatch; a block/require_approval result aborts with zero files written under `writebacks/`. Verified by a call-order assertion, not code review alone. | 1.5 pts | python-backend-engineer | sonnet | adaptive | ORC-001 |
| ORC-003 | Per-target isolated dispatch (D4) | Call `_render_meatywiki`, `_render_skillbom`, `telemetry.emit_ccdash_event` directly (not the monolithic `writeback()`), each independently try/except-wrapped, in the existing fixed order (ccdash->meatywiki->skillmeat). Collect per-target `success`/`failed`/`skipped` status. | PRD FR-7: one target's exception does not prevent the other two from being attempted; response includes explicit per-target status. `writeback()`'s own CLI-facing behavior is unchanged (FR-13-of-this-PRD). | 1 pt | python-backend-engineer | sonnet | adaptive | ORC-002 |
| ORC-004 | Populate `approved_by`/`approval_timestamp` | On a successful (non-blocked) invocation, populate `evidence_bundle.governance.approved_by` and `approval_timestamp` from the resolved identity (passed in by the caller — Phase 2 supplies it) and `now_iso()`. | PRD FR-10: both previously-always-`None` fields are populated on success. | 0.5 pts | python-backend-engineer | sonnet | adaptive | ORC-002 |
| ORC-005 | Advisory lock (D2, FR-14) | Add a short-TTL `.dispatch.lock` file per run around the orchestration call; a lock held by another in-flight invocation does not corrupt partial state (accept last-write-wins after TTL expiry — no hard reject). | PRD FR-14 (Should) satisfied via the simplest option that prevents corrupted partial state; both racing attempts still each independently produce an audit row once Phase 2 wires audit (verified in Phase 4). | 0.5 pts | python-backend-engineer | sonnet | adaptive | ORC-003 |
| VAL-1 | Phase 1 validator gate | Review ORC-001..005 against Phase 1 Quality Gates below; run unit tests for `approve_and_dispatch()` in isolation from any HTTP layer (mock `load_run_context`/`council_review`/target renders as needed). | Pass/fail verdict recorded; must pass before Phase 2/3 begin implementation (though Phase 2/3 design work against the locked DTO may start once ORC-001 lands). | 0.5 pts | task-completion-validator | sonnet | adaptive | ORC-001..005 |

**Phase 1 Quality Gates** (maps to PRD §11):
- [ ] `guard_check()` call happens before any target-dispatch call (Technical Acceptance row 3)
- [ ] A blocking guard result writes zero files under `writebacks/` (Functional Acceptance row 2)
- [ ] Per-target isolation: one target's forced failure does not prevent the other two (Functional Acceptance row 6)
- [ ] `approved_by`/`approval_timestamp` populated on success (Functional Acceptance row 4)
- [ ] Re-invocation for the same `run_id` overwrites, not duplicates (Functional Acceptance row 7)
- [ ] `writeback()`, `council_review()`, `build_bundle()` signatures and CLI-facing behavior unchanged

---

### Phase 2: API Layer — Auth, Audit, Governance Gate

**Duration**: ~2 days
**Dependencies**: Phase 1 (ORC-001 DTO shape locked)
**Isolation**: worktree (Mode D — first-ever identity/audit threading, RBAC surface)
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|-------|--------|--------------|
| API-001 | New route file + RBAC gate | Create `api/routers/writeback.py` (D3) with `POST /api/runs/{run_id}/writeback/approve`, gated by `Depends(require_role("owner", "admin"))` exactly as `POST /agent-jobs`. Register router in `api/app.py`. | PRD FR-4: route honors `auth.rbac_enforcement` (`auto`/`disabled`/`enabled`) identically to `POST /agent-jobs`/`POST /api/runs`. | 1 pt | python-backend-engineer | sonnet | adaptive | ORC-001 |
| API-002 | `governance_rejected` error mapping | Map `guard_check()` block/require_approval results to the existing `governance_rejected` error body shape (422 for block, 400 for require_approval), matching `POST /agent-jobs`'s exact envelope. | PRD FR-3, Technical Acceptance row 2: same error shape as the existing precedent, no new envelope invented. | 0.5 pts | python-backend-engineer | sonnet | adaptive | API-001 |
| API-003 | Audit wiring for all outcome classes | Call `audit_service.record_event(mutation_type="writeback", ...)` for every outcome: success, partial (some targets failed), blocked (governance rejected), and unexpected exception — wrapping the orchestration call so no path (including non-`RFError` exceptions) is left unaudited. | PRD FR-5: exactly one audit row per invocation across all four outcome classes — the single highest-risk task in this plan (Human Brief §6). | 1.5 pts | python-backend-engineer | sonnet | adaptive | API-001 |
| API-004 | Identity -> `actor_user_id` threading | Resolve `request.state.identity` and thread its `user_id` into the `AuditEvent.actor_user_id` when present; leave `None` (not an error) when absent (loopback/no-auth mode). Pass resolved identity into ORC-004's `approved_by` population. | PRD FR-6: first route in the codebase to actually use identity for `actor_user_id`, not just resolve it and discard it. | 0.5 pts | python-backend-engineer | sonnet | adaptive | API-003 |
| API-005 | Update `rbac.py` classification docstring | Update the existing docstring in `api/auth/rbac.py` that currently classifies `rf writeback` as a "single-operator-trust, CLI-only" surface with no gated HTTP path — no longer true after this feature. | PRD Functional Acceptance (rbac.py bullet) and Documentation Acceptance row 2. | 0.25 pts | python-backend-engineer | sonnet | adaptive | API-001 |
| API-006 | OpenAPI docs + review checkpoint | Add docstrings/response models so the new route documents cleanly in OpenAPI; mandatory design review of the RBAC/audit/governance surface before Phase 4 hardening begins (PRD's own suggested checkpoint given `risk_level: high`). | Route appears correctly in `/openapi.json` with documented request/response schema; backend-architect sign-off recorded. | 0.5 pts | backend-architect | sonnet | extended | API-001..004 |
| VAL-2 | Phase 2 validator gate | Review API-001..006 against Phase 2 Quality Gates below. | Pass/fail verdict recorded; must pass before Phase 4 integration tests begin. | 0.5 pts | task-completion-validator | sonnet | adaptive | API-001..006 |

**Phase 2 Quality Gates** (maps to PRD §11):
- [ ] Route gated by `require_role("owner", "admin")`, honoring `auth.rbac_enforcement` (Functional Acceptance row 1)
- [ ] `governance_rejected` error shape matches `POST /agent-jobs` exactly (Technical Acceptance row 2)
- [ ] Exactly one audit row per invocation across success/partial/blocked/exception (Functional Acceptance row 5)
- [ ] `actor_user_id` populated when identity resolves, `None` when it does not (Functional Acceptance row 6)
- [ ] `rbac.py` docstring updated (Documentation Acceptance row 2)

---

### Phase 3: UI Layer — Approve & Dispatch

**Duration**: ~1.5 days
**Dependencies**: Phase 1 (ORC-001 DTO shape locked); full integration testing gates on Phase 2
**Isolation**: shared
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|-------|--------|--------------|
| UI-001 | Typed POST client binding | Add a typed POST binding in `frontend/runs-viewer/src/api/client.ts` for the new endpoint, using the DTO shape locked in ORC-001. First non-GET binding in this file. | Binding compiles under `tsc -p tsconfig.app.json --noEmit`; request/response types match the locked backend DTO shape. | 0.5 pts | frontend-developer | sonnet | adaptive | ORC-001 |
| UI-002 | Approve & Dispatch button + confirmation dialog | Add the action to the Writeback tab in `RunDetailWorkspace.tsx`, visible only when the run has a report and is not currently mid-dispatch (in-flight state). Dialog confirms before calling the endpoint (this is a real external-workspace mutation). | PRD FR-11: action visible under the stated conditions; confirmation gate present before dispatch fires. | 1 pt | ui-engineer-enhanced | sonnet | adaptive | UI-001 |
| UI-003 | Per-target outcome rendering | Render per-target (meatywiki/skillmeat/ccdash) `success`/`failed`/`skipped` status inline after a response. Handle a response missing/partial fields defensively (new backend fields — R-P2: FE must not crash on an absent target-status entry or a null `guard` result). | PRD FR-8, FR-12 (partial): outcomes render per-target; missing-field cases degrade gracefully rather than crashing the tab. | 0.75 pts | ui-engineer-enhanced | sonnet | adaptive | UI-002 |
| UI-004 | `governance_rejected` vs. generic-error messaging | Distinguish a `governance_rejected` response (by response shape/status code, not string-matching error text) from a generic 500/network failure in the UI messaging. Confirm FR-13's existing read-only preview cards and governance panel remain unchanged (regression guard). | PRD FR-12: operator can visually tell "blocked by policy" from "something broke." No new mutation affordance beyond the single approve+dispatch action added to the diff (Risk R7 guard). | 0.5 pts | frontend-developer | sonnet | adaptive | UI-003 |
| VAL-3 | Phase 3 validator gate | Review UI-001..004 against Phase 3 Quality Gates below. | Pass/fail verdict recorded. | 0.5 pts | task-completion-validator | sonnet | adaptive | UI-001..004 |

**Phase 3 Quality Gates** (maps to PRD §11):
- [ ] Action visible only when run has a report and is not mid-dispatch (Functional Acceptance row 11)
- [ ] Confirmation dialog gates the actual dispatch call
- [ ] Per-target outcomes render; missing/partial response fields do not crash the tab (R-P2)
- [ ] `governance_rejected` distinguished from generic error by shape, not string-matching
- [ ] FR-13 read-only preview cards and governance panel unchanged (Functional Acceptance row 13)
- [ ] No new UI affordance to directly edit `reviewer_notes`/`required_fix`/`approved_for_writeback` (Functional Acceptance row 14 / Risk R7)

---

### Phase 4: Tests, Hardening & Docs

**Duration**: ~1.5 days
**Dependencies**: Phase 2 and Phase 3 both complete
**Isolation**: shared
**Assigned Subagent(s)**: python-backend-engineer, ui-engineer-enhanced, changelog-generator, task-completion-validator, karen

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|-------|--------|--------------|
| TEST-001 | RBAC on/off matrix | Integration tests: `auth.rbac_enforcement` = `disabled` vs `enabled`, with and without a resolved identity. | PRD Quality Acceptance row 1 (RBAC portion). | 0.5 pts | python-backend-engineer | sonnet | adaptive | API-006, UI-004 |
| TEST-002 | Governance block/require_approval/pass + ordering | Integration tests: each of the 3 `guard_check()` outcomes; assert `guard_check()` is called before any target-dispatch call (ordering assertion, not just code inspection). | PRD Technical Acceptance row 3; Quality Acceptance row 1 (governance portion). | 0.5 pts | python-backend-engineer | sonnet | adaptive | TEST-001 |
| TEST-003 | Per-target isolation + idempotent re-invocation | Integration tests: forced failure in one target does not block the others; two real sequential calls for the same `run_id` overwrite (assert stable IDs across both calls, not just ID-generation-in-isolation). | PRD Quality Acceptance row 1 (isolation + idempotency portions); Human Brief §7 "watch for" item. | 0.5 pts | python-backend-engineer | sonnet | adaptive | TEST-002 |
| TEST-004 | Audit-row-per-outcome (all 4 classes) | Integration tests: success, partial, blocked, and unexpected-exception paths each produce exactly one `audit_event` row; `actor_user_id` present when identity resolves, `None` when it does not. | PRD Quality Acceptance row 1 (audit portion) — highest-value assertion per Human Brief §6. | 0.5 pts | python-backend-engineer | sonnet | adaptive | TEST-003 |
| TEST-005 | Frontend tests | Vitest coverage: action visibility conditions, confirmation dialog, success/partial/blocked rendering, and FR-13's existing read-only-invariant tests still pass unmodified (regression guard). | PRD Quality Acceptance row 2. | 0.75 pts | ui-engineer-enhanced | sonnet | adaptive | TEST-004 |
| TEST-006 | Runtime smoke (R-P4) | Manual/automated smoke pass against every `target_surfaces` entry from Phase 3: `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` (Writeback tab, Approve & Dispatch action end-to-end against a live local run) and `frontend/runs-viewer/src/api/client.ts` (typed binding against the real route). | Both target surfaces exercised end-to-end against the running API; no console errors; per-target outcomes render correctly for a real dispatch. | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | TEST-005 |
| TEST-007 | Full validation suite | Run: `pnpm --dir frontend/runs-viewer exec tsc -p tsconfig.app.json --noEmit`, `pnpm --dir frontend/runs-viewer lint`, `pnpm --dir frontend/runs-viewer test`, `pnpm --dir frontend/runs-viewer build`, `./.venv/bin/python -m pytest` (project venv, changed backend modules), `flake8 --select=E9,F63,F7,F82` on changed files. | PRD Quality Acceptance rows 3-4: all commands pass clean. | 0.25 pts | python-backend-engineer | sonnet | adaptive | TEST-006 |
| DOC-001 | CHANGELOG entry | Add `[Unreleased]` entry per `.claude/specs/changelog-spec.md`: new approve+dispatch endpoint + viewer action. | PRD Documentation Acceptance row 1; `changelog_ref` frontmatter set to `CHANGELOG.md`. | 0.25 pts | changelog-generator | haiku | adaptive | TEST-007 |
| DOC-006 | Author design specs for deferred items | Author 3 design_specs (DI-WBAD-1/2/3 above) at `maturity: idea`, `prd_ref` set to this plan's parent PRD; append paths to `deferred_items_spec_refs`. | All 3 deferred items have a design_spec path in frontmatter. | 1 pt | documentation-writer | sonnet | adaptive | TEST-007 |
| VAL-4 | Phase 4 validator gate | Review TEST-001..007 and DOC-001/006 against Phase 4 Quality Gates below. | Pass/fail verdict recorded; must pass before the karen feature-end gate. | 0.5 pts | task-completion-validator | sonnet | adaptive | TEST-001..007, DOC-001, DOC-006 |
| KAREN-1 | Karen feature-end gate (mandatory, Tier 2) | End-to-end reality check: verify every PRD §11 acceptance-criteria bullet is actually met (not just marked complete), verify the Mode D rollback/mitigation section above holds, verify no scope creep beyond the single approve+dispatch action (Risk R7). | Pass/fail verdict recorded per `.claude/skills/dev-execution/validation/completion-criteria.md`; feature is not complete until this passes. | 0.5 pts | karen | opus | adaptive | VAL-4 |

**Phase 4 Quality Gates** (maps to PRD §11 Quality/Documentation Acceptance):
- [ ] RBAC on/off matrix passes
- [ ] Governance block/require_approval/pass + ordering assertion passes
- [ ] Per-target isolation + idempotent re-invocation passes
- [ ] Audit-row-per-outcome (all 4 classes) passes, including `actor_user_id` present/absent cases
- [ ] Frontend tests pass, including FR-13 regression guard
- [ ] Runtime smoke (R-P4) passes against both target surfaces
- [ ] Full validation suite (tsc/lint/vitest/build/pytest/flake8) green
- [ ] CHANGELOG `[Unreleased]` entry present
- [ ] All 3 deferred items have design_spec paths (or documented N/A — not applicable here, all 3 are real)
- [ ] `karen` feature-end gate passed

---

## Wrap-Up: Feature Guide & PR

Triggered automatically after Phase 4 is sealed (all quality gates + karen pass). Delegate to
`documentation-writer` (haiku) to create `.claude/worknotes/runs-writeback-approve-dispatch/feature-guide.md`
per the standard feature-guide frontmatter and section set (What Was Built / Architecture Overview /
How to Test / Test Coverage Summary / Known Limitations). Commit the feature guide, then open the PR
with a summary derived from this plan's Executive Summary and the CHANGELOG entry from DOC-001.

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|----------------------|
| Mode D external-side-effect writes to shared workspace mirrors (see dedicated section above) | High | Medium | Governance-gate-first ordering, per-target isolation, idempotent overwrite; test against disposable runs until Phase 4 passes |
| First-ever `actor_user_id` audit threading has no precedent to copy exactly | Medium | Medium | TEST-004 explicitly asserts both the present and absent cases; API-004 is scoped as its own task rather than folded silently into API-003 |
| Governance-gate tightening changes prior CLI-permissive behavior (PRD Risk R6) | Medium | Medium | Explicitly documented as intentional in Phase 1/2 Quality Gates and the Human Brief §6, so it is not mistaken for a regression during review |
| Scope creep toward UI-editable `reviewer_notes`/`required_fix` (PRD Risk R7) | Medium | Medium | Explicit Phase 3 Quality Gate + karen gate checks the diff for any affordance beyond the single approve+dispatch action |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|----------------------|
| P2/P3 diverge on the response DTO shape mid-flight | Medium | Low | ORC-001's design review locks the shape before P2/P3 begin; API-006's review checkpoint catches drift before Phase 4 |
| Advisory lock (D2) proves insufficient once concurrency increases | Low | Low | Explicitly deferred as DI-WBAD-3 with a named promotion trigger (multi-tenant OIDC + observed collisions) |

---

## Resource Requirements

### Team Composition
- Backend (python-backend-engineer): Phases 1, 2, 4 (tests)
- Backend architecture review (backend-architect): Phase 1 (ORC-001), Phase 2 (API-006) — checkpoint only, not full-phase
- Frontend (ui-engineer-enhanced, frontend-developer): Phase 3, Phase 4 (FE tests + smoke)
- Docs (changelog-generator, documentation-writer): Phase 4
- Mandatory gates: task-completion-validator (every phase), karen (feature end)

### Skill Requirements
- Python, FastAPI, Pydantic DTOs, existing RF service-layer conventions
- TypeScript/React, React Query (if used elsewhere in runs-viewer), Vitest
- Familiarity with `POST /agent-jobs` as the direct architectural precedent

---

## Success Metrics

Carried from PRD §4:
- CLI commands needed to approve+dispatch a run from the viewer: 3 (terminal) -> 1 (API call / UI click)
- Governance-gate coverage on the dispatch path: 0% (not wired) -> 100% (every invocation)
- Audit rows per approve+dispatch invocation: n/a -> exactly 1, every outcome

---

**Progress Tracking:**

See `.claude/progress/runs-writeback-approve-dispatch/phase-N-progress.md` (created via `artifact-tracking` skill before execution begins).

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-18
