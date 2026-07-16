---
title: "Phase 3-4: Forward Write Driver & Reuse Reachability"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-15
phase: P3-P4
phase_title: "Forward write driver; reuse reachability"
feature_slug: assertion-ledger-activation
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
entry_criteria: ["P1 shared workspace-resolution helper merged", "P3 additionally requires P1.5 extraction/ingest contract fix merged"]
exit_criteria: ["P3: forward-write integration test green, flag-off regression green, karen security sign-off", "P4: reuse decision invocable via CLI/HTTP, governed-deny path tested"]
delegation_mode: D
---

# Phase 3: Forward Write Driver & Phase 4: Reuse Reachability

Both phases are individually small (3 pts each) and share the "wire an existing entry point to an existing decision service" shape. **Phase 3 depends on P1 AND P1.5** (see below); Phase 4 depends only on P1. Per the parent plan's wave plan, **P3 and P4 do not run in the same wave** -- P3 shares `src/research_foundry/cli_commands.py` with P2 (a declared serialization barrier) and additionally hard-depends on P1.5, so it is pushed to wave 3, while P4 runs alongside P2 in wave 2.

[<- Back to parent plan](../assertion-ledger-activation-v1.md)

---

## Phase 3: Forward Write Driver (3 pts) -- Mode D

**Mode: D -- High-Risk Change.** Workspace-write surface; no auto-merge; diffs reviewed before merge/deploy.

**Duration**: ~2 days
**Dependencies**: P1, **P1.5 (extraction/ingest contract fix -- hard-blocking, per the P2-01 SPIKE)**
**Assigned Subagent(s)**: python-backend-engineer (primary), karen (security milestone)
**Model default**: sonnet | **Effort default**: adaptive

### P1.5 Dependency (added per the P2-01 SPIKE verdict)

The P2-01 SPIKE (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`) found that `source_cards.ingest_source()` -- the exact function this phase wires -- carries two defects that, unfixed, cap forward-write yield near **0%** regardless of anything this phase does: (1a) the extraction pipeline stores a paraphrase, not the verbatim quote the materializer's exact-match gate requires; (1b) `ingest_source()` never segments passages, so a short quote can never bind via `find_exact_passages()`. Phase 1.5 fixes both. **This phase must not start before Phase 1.5 lands** -- otherwise it wires a workspace id into a call that would still abstain almost universally, reproducing this feature's own stated anti-goal (a silent no-op) for the forward path. Once Phase 1.5's contract fix is in place, this phase's original scope is unchanged: wiring `assertion_registry_workspace_id` into `ingest_source()` remains the small step it always was.

### OQ-2 Resolution (carried from parent plan decisions)

The forward write driver wires **`rf ingest`**, the Typer CLI command at `src/research_foundry/cli_commands.py:316-337`. It is the only caller of `source_cards.ingest_source()` outside that service's own module, and is the command real runs (including discovery-swarm carder agents, per this project's Path-B swarm execution pattern) already invoke. No `POST /api/runs` ingest call or separate discovery-swarm-specific ingest path exists to wire instead.

### R-P3 Check

Single owner specialty (python-backend-engineer). **R-P3 does not trigger** for Phase 3.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P3-01 | Wire `rf ingest` to pass workspace id | Modify the `ingest` command (`cli_commands.py:316-337`) to resolve `assertion_registry_workspace_id` via P1-02's helper and pass it plus `ledger_write_allowed` into `svc.ingest_source(...)`. No change to the command's existing `locator`/`run`/`source_type`/`sensitivity`/`title`/`fetch` arguments. | AC-4 target_surfaces: [src/research_foundry/services/source_cards.py, src/research_foundry/services/assertion_rollout.py]. propagation_contract: a real run launched via `rf ingest` passes `assertion_registry_workspace_id` into `ingest_source`, increasing the workspace ledger's assertion count. resilience: degraded or content-less sources (`ingest_source`'s existing gate conditions) still produce no write and no error escalation. visual_evidence_required: false. verified_by: [P3-03]. | 1.5 pts | python-backend-engineer | sonnet | adaptive | P1-03, **P1.5 merged** |
| P3-02 | Flag-off regression test | Full `rf ingest` run with `ledger_write_enabled=false` in `foundry.yaml` produces artifacts byte-identical to the pre-feature baseline (claim ledger, export, catalog data). Mirrors the AAR's A2 fix approach: assert the flag actually reaches its runtime consumer, don't just assume the inverse of flag-on. Also confirms P1.5's contract fix itself introduces no flag-off behavior change (reuses P1.5-03's regression coverage rather than re-deriving it). | AC-2 target_surfaces: [src/research_foundry/services/source_cards.py, src/research_foundry/services/assertion_rollout.py]. propagation_contract: with the flag false, ingest path and all produced artifacts are byte-identical to today. resilience: flag-off is the tested default in the regression suite, not an assumed inverse. visual_evidence_required: false. verified_by: [P3-02] (self-referential). | 1 pt | python-backend-engineer | sonnet | adaptive | P3-01 |
| P3-03 | Forward-write integration test | A fresh run's `rf ingest` call with the flag on increases the workspace ledger's assertion count **with at least one assertion bound to a verbatim quote** (proving P1.5's fix actually reaches this entry point, not just a unit-level guarantee); verify against P1-03's shared isolation fixture (reuse, do not re-derive). | AC-4, AC-8 (see P3-01, P1.5); also contributes to AC-1's `verified_by` list. | 0.5 pt | python-backend-engineer | sonnet | adaptive | P3-01 |

**Phase 3 total: 3 pts.** (Unchanged by the P2-01 SPIKE -- the SPIKE's finding is a new *dependency*, not new *scope*: this phase was already just "wire the workspace id.")

### Karen Security Milestone (exit gate)

After P3-03: **karen** reviews the P3 diff. Third of the plan's four security milestones (P1.5, P2, P3, P6).

### R-P2 Check

`ledger_write_allowed` is an internal parameter threaded through `ingest_source`, not a new API-visible response field. **R-P2 does not trigger.**

### Quality Gates

- [ ] P1.5 (extraction/ingest contract fix) merged and its karen sign-off recorded before this phase starts.
- [ ] Flag-off regression test green.
- [ ] Forward-write integration test green, including >=1 verbatim-quote-bound assertion (not just a count increase).
- [ ] `task-completion-validator` passes P3.
- [ ] **karen** security sign-off recorded.

### Key Files

`src/research_foundry/services/source_cards.py`, `src/research_foundry/cli_commands.py` (serialization barrier with P2 -- resolved by wave sequencing), `tests/unit/test_source_cards_ingest.py` (new).

---

## Phase 4: Reuse Reachability (3 pts) -- Mode D

**Mode: D -- High-Risk Change.** Widens the run-launch validation surface; no auto-merge; diffs reviewed before merge/deploy.

**Duration**: ~2-3 days
**Dependencies**: P1
**Assigned Subagent(s)**: python-backend-engineer (primary), api-designer (secondary, seam)
**Model default**: sonnet | **Effort default**: adaptive

### R-P3 Check -- TRIGGERED

Two owner specialties (`python-backend-engineer`, `api-designer`) with overlapping `files_affected` (`api/routers/runs.py`, `run_launch.py`). **`integration_owner: python-backend-engineer`** declared for this phase. Seam task: **P4-02**.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P4-01 | Add reuse fields to `LaunchRunRequest` | Add `reuse_assertion`, `reuse_workspace_id`, `required_reuse_edition_id`, `required_extraction_contract` to `LaunchRunRequest` in `src/research_foundry/api/routers/runs.py`; regenerate the OpenAPI schema. No new validation logic beyond type/presence -- authorization lives in P4-02's wiring to the existing governed path. | Fields present in the OpenAPI schema with correct types; absent-by-default (optional fields, no behavior change when omitted). | 1 pt | api-designer | sonnet | adaptive | P1-03 |
| P4-02 | Seam: wire reuse fields to existing decision services | `run_launch.py` routes populated reuse fields through the existing `assertion_reuse`/`assertion_impact` decision services -- **no new policy logic**. Returns allow/deny/refresh + reason. This is the R-P3 seam task: confirms P4-01's OpenAPI contract (field names/types) and this service-layer wiring agree byte-for-byte. Unauthorized or cross-workspace reuse targets are denied via the existing `block_authoritative_reuse` path, not a new ad hoc check. | AC-5 target_surfaces: [src/research_foundry/api/routers/runs.py, src/research_foundry/services/run_launch.py]. propagation_contract: `LaunchRunRequest` routes through `assertion_reuse` evaluation, returns allow/deny/refresh + reason. resilience: reuse fields absent -> run launch behaves exactly as today (no reuse evaluation attempted); cross-workspace/unauthorized target -> denied via `block_authoritative_reuse`. visual_evidence_required: false. verified_by: [P4-03]. | 1.5 pts | python-backend-engineer | sonnet | adaptive | P4-01 |
| P4-03 | Reuse reachability test | Invoke via CLI/HTTP for at least one allow scenario and the denied path. Reuse fields absent -> run launch behaves exactly as today (no reuse evaluation attempted, confirmed by test, not assumption). | AC-5 (see P4-02); this task IS AC-5's `verified_by` anchor. | 0.5 pt | python-backend-engineer | sonnet | adaptive | P4-02 |

**Phase 4 total: 3 pts.**

### R-P2 Check

Reuse fields are new *request* fields on `LaunchRunRequest`, not new *response* fields a frontend must handle-missing for. The response shape (allow/deny/refresh + reason) is new but is not yet consumed by any runs-viewer surface in this plan's scope (P5 activates the merge-review UI, which is a separate response contract already built by v1). **R-P2 does not trigger** for P4's own fields; if a future phase surfaces the reuse decision in the UI, that phase must add the corresponding FE-resilience AC at that time.

### Quality Gates

- [ ] OpenAPI schema regenerated and includes the four new fields.
- [ ] Reuse allow-path test green.
- [ ] Reuse denied-path test green (via existing `block_authoritative_reuse`).
- [ ] Fields-absent regression test green (run launch unchanged when reuse fields omitted).
- [ ] `task-completion-validator` passes P4.

### Key Files

`src/research_foundry/api/routers/runs.py`, `src/research_foundry/services/run_launch.py`, `tests/integration/test_run_launch_reuse.py` (new).
