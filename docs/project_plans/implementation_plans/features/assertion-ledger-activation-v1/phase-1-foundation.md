---
title: "Phase 1: Write-Path Foundation & WKSP-304 Scoping Contract"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-15
phase: P1
phase_title: "Write-path foundation & WKSP-304 scoping contract"
feature_slug: assertion-ledger-activation
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
entry_criteria: ["PRD approved", "decisions block reviewed"]
exit_criteria: ["isolation tests green", "senior-code-reviewer Mode E sign-off", "DI-1 scoping enumeration reviewed"]
delegation_mode: D
---

# Phase 1: Write-Path Foundation & WKSP-304 Scoping Contract

**Mode: D -- High-Risk Change.** This phase establishes the workspace-write safety substrate every other write-touching phase (P2, P3, P4) depends on. No auto-merge; diffs reviewed before merge/deploy.

**Duration**: ~2-3 days
**Dependencies**: None (wave 1, parallelizable with P5)
**Assigned Subagent(s)**: python-backend-engineer (primary), senior-code-reviewer (Mode E, secondary)
**Model default**: sonnet | **Effort default**: extended

[<- Back to parent plan](../assertion-ledger-activation-v1.md)

## Overview

Establishes and verifies the workspace-scoped assertion write invariants: a shared contract proving any new write is confined to its `assertion_registry_workspace_id` and fails closed without one. This phase produces **no user-facing behavior change** -- it is pure safety substrate. P2, P3, and P4 all call the helper this phase produces; none of them may bypass it by calling `AssertionRegistry.ingest()` / `AssertionMaterializer.materialize_run()` directly.

## R-P3 Check (integration ownership)

Single owner specialty (python-backend-engineer) builds; senior-code-reviewer is a Mode E reviewer, not a co-builder with overlapping `files_affected`. **R-P3 does not trigger** -- no `integration_owner` declaration needed for this phase.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P1-01 | Confirm default-workspace resolution (OQ-3) | Inspect the WKSP-304 `identity=None` short-circuit pattern (`src/research_foundry/api/routers/runs.py:240-265,289-291`) and `FoundryConfig` to determine the canonical `assertion_registry_workspace_id` a single-operator deployment resolves to. Document the resolution rule (not a new mechanism -- confirm/adapt the existing one). | Resolution rule documented inline in the P1 module docstring or a short note in this phase file's Findings section; DF-002 closed without needing a standalone design-spec, or escalated if genuinely ambiguous. | 0.5 pt | python-backend-engineer | sonnet | adaptive | None |
| P1-02 | Shared workspace-resolution + fail-closed helper | Implement `services/assertion_workspace.py::resolve_or_deny()` (or equivalently named): every new write call site (P2, P3, P4) calls this before `AssertionRegistry.ingest()` / `AssertionMaterializer.materialize_run()`. Returns a typed denial (mirrors the WKSP-304 404-not-403 pattern) when `assertion_registry_workspace_id` is absent -- never a silent no-op. | target_surfaces: [src/research_foundry/services/assertion_workspace.py, src/research_foundry/services/assertion_registry.py, src/research_foundry/services/assertion_materialization.py]. propagation_contract: every write call site added by P2/P3/P4 imports and calls this helper before any registry/materializer write. resilience: absent workspace id -> zero writes, typed denial object returned, never an exception that looks like an unrelated failure. visual_evidence_required: false. verified_by: [P1-03]. | 1 pt | python-backend-engineer | sonnet | extended | P1-01 |
| P1-03 | Isolation regression test harness | Parametrized test suite (`tests/unit/test_assertion_workspace_isolation.py`) proving: (a) a write with a workspace id lands scoped only to that workspace; (b) a write attempt with no workspace id performs zero writes and returns the typed denial from P1-02; (c) a cross-workspace read/write attempt is rejected. Designed as a **shared fixture** reusable by P2's, P3's, and P4's own test suites (do not duplicate the fixture per phase). | AC-1 target_surfaces: [src/research_foundry/services/assertion_rollout.py, src/research_foundry/services/source_cards.py, src/research_foundry/services/run_launch.py, src/research_foundry/services/assertion_registry.py]. propagation_contract: every write call site added by P2/P3/P4 resolves workspace id via P1-02 before writing. resilience: absent id -> zero writes, typed denial (never silent no-op). visual_evidence_required: false. verified_by: [P1-03, P2 backfill test, P3 forward-write test, P6 DI-1 audit] (this is AC-1's primary verification anchor; P2/P3/P6 reuse this fixture rather than re-deriving it). | 1 pt | python-backend-engineer | sonnet | extended | P1-02 |
| P1-04 | Mode E review of the isolation-contract diff | senior-code-reviewer reviews the full P1 diff (P1-02, P1-03) before P2/P3/P4 branch from it. Read-only review -- no edits. Mode: E -- Reviewer. | Review recommendation posted; no unresolved High-severity findings before P2/P3/P4 start. | 0.5 pt | senior-code-reviewer | sonnet | adaptive | P1-03 |

**Phase 1 total: 3 pts.**

## AC Mapping

- **AC-1** (New writes are workspace-confined and fail closed without a workspace id) -- primary verification anchor is **P1-03**; reused (not re-derived) by P2's backfill test, P3's forward-write test, and P6's DI-1 audit.

## R-P2 Check (implicit "FE handles missing X" AC)

This phase introduces no new backend *response* field consumed by any frontend surface -- `assertion_workspace.py` is an internal service-layer helper with no API-visible shape. **R-P2 does not trigger.**

## Quality Gates

- [ ] `tests/unit/test_assertion_workspace_isolation.py` green (all three scenarios: scoped write, absent-id denial, cross-workspace rejection).
- [ ] `task-completion-validator` passes P1 (Tier 3 mandatory per-phase gate).
- [ ] `senior-code-reviewer` (Mode E) has reviewed the isolation-contract diff with no unresolved High findings.
- [ ] DI-1 scoping enumeration for this phase's own surface reviewed (this phase adds no writes itself, but its contract is what P6's full DI-1-scoped audit later checks P2/P3/P4 against -- confirm the contract's denial path is itself testable/auditable).
- [ ] OQ-3 (DF-002) resolved inline via P1-01, or escalated.

## Key Files & Integration Points

- `src/research_foundry/services/assertion_workspace.py` (new)
- `src/research_foundry/services/assertion_registry.py` (no behavior change from this phase -- P2 is the first caller of its write path)
- `src/research_foundry/services/assertion_materialization.py` (no behavior change from **this** phase -- see note below)
- `tests/unit/test_assertion_workspace_isolation.py` (new)
- Cross-reference: WKSP-304 confinement/fail-closed pattern (`docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md`) -- match its `identity=None` short-circuit and 404-not-403 denial shape structurally; do not invent a new denial contract.
- **Cross-reference (added per the P2-01 SPIKE, 2026-07-15)**: `assertion_materialization.py` DOES change behavior in this plan -- via the new, parallel **Phase 1.5** (`../assertion-ledger-activation-v1/phase-1-5-extraction-contract-fix.md`), which fixes the extraction/ingest contract's paraphrase-vs-quote defect. P1 and P1.5 run in the same wave (wave 1) but do not conflict: this phase does not itself edit that file, only references it.

## Findings (P1-01 resolution slot)

**Resolution rule (closes OQ-3 / DF-002)**: a single-operator Research Foundry deployment resolves `assertion_registry_workspace_id` to the literal string `"default"`.

Evidence:

1. `api/auth/scope.py::require_workspace_scope` treats `identity is None` (single-operator-trust — no auth middleware configured) as "no workspace context to compare" and returns before any workspace_id lookup runs. It never invents a workspace_id itself; that resolution is the *caller's* job (routers extract `identity` before the scope check ever runs).
2. Where this codebase needs a fixed sentinel for the single-operator / pre-multi-tenant baseline, it consistently uses the literal string `"default"`: `services/workspace_migration_service.py` defaults `target_workspace_id: str = "default"` on every backfill/dry-run/rollback dataclass (WKSP-301/302), and `api/auth/adapters/clerk.py` falls back to `payload.get("org_id") or "default"`. `AuthIdentity.workspace_id`'s own docstring names this same convention ("Single-tenant deployments may use a fixed sentinel (e.g. `"default"`)").

No new mechanism was added — this confirms/adapts the existing convention. `assertion_workspace.py::resolve_or_deny()` does not perform this resolution itself (it has no per-request `AuthIdentity` to inspect, unlike `scope.py`); it only enforces the fail-closed contract on whatever value the call site already produced. **P2/P3's future CLI/HTTP entry points are responsible for passing the literal `"default"` string as `assertion_registry_workspace_id` in a single-operator deployment** before calling `resolve_or_deny()`. Full resolution narrative lives in the new module's docstring (`src/research_foundry/services/assertion_workspace.py`).

DF-002 is closed inline; no standalone design-spec was needed — the ambiguity resolved cleanly to an existing, already-adopted convention.
