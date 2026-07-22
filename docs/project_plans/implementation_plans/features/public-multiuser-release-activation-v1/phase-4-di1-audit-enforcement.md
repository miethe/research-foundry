---
title: "Phase 4: DI-1 Audit + Enforcement Flip"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
phase: P4
phase_title: "DI-1 Audit + Enforcement Flip"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
integration_owner: python-backend-engineer
entry_criteria:
  - "P1 (ACT-101) landed — ACT-401/ACT-402 only need the gate stub; ACT-403 additionally needs P2+P3 sealed."
exit_criteria:
  - "Mode D human sign-off on audit scope-boundary statement obtained."
  - "Audit artifact status: accepted."
  - "karen milestone review passed."
  - "task-completion-validator pass."
---

# Phase 4: DI-1 Audit + Enforcement Flip

[← Back to main plan](../public-multiuser-release-activation-v1.md)

**Estimate**: 13 pts
**Dependencies**: P1 (ACT-101/102) for ACT-401/ACT-402; P2+P3 additionally for ACT-403. Runs **parallel to P2** (`batch_2`/`batch_3`), converges with P5 in `batch_4`.
**Assigned Subagent(s)**: `codebase-explorer` (enumeration/backward-trace, dispatched with `model="sonnet"` — haiku hard-errors in this environment) → `python-backend-engineer` (remediation)
**Model**: sonnet (extended for audit enumeration; adaptive for remediation/gate-wiring) | **Effort**: extended (ACT-401), adaptive (ACT-402/403/404)
**Mode**: **D — High-Risk Change** for the audit-acceptance step specifically (ACT-406). All other tasks in this phase run under standard delegation; only the final `status: accepted` transition is gated.

## Overview

This phase closes the exact gap the WKSP-304 AAR flagged: a prior "100% coverage" claim on workspace-scoping was later found incomplete (two Mode-D leaks discovered post-hoc). This phase enumerates **every** function/route that reads or writes workspace-scoped rows repo-wide — not feature-scoped like the prior assertion-ledger audit — remediates findings, and wires a two-part fail-closed gate (operator acknowledgment flag + machine-checkable artifact status) into the `deployment_mode_validate()` stub P1 shipped. **No agent may self-certify this audit as `accepted`** — that transition requires an explicit human response.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|---------------|
| ACT-401 | DI-1 full-surface audit | Repo-wide backward-trace from every `AuthIdentity`/`workspace_id` construction site to its `resolve_workspace_isolation_enforced()`/`require_workspace_scope()` call, extending the assertion-ledger DI-1-scoped audit's method (per PRD §13 Prior Art) across catalog, builder/report-drafts, agent-jobs, admin, and sharing surfaces. Produce `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` (`status: draft` initially) with a complete surface inventory table. Remediate any findings (including any recurrence of the two prior leaks: `create_draft_from_run`/`create_draft_from_collection`, `catalog_service.get_item`). | FR-14 satisfied; audit artifact exists with a complete, cross-checked surface inventory (row count vs. grep-derived surface count); all findings remediated in code. | 8 pts | codebase-explorer (enumeration) → python-backend-engineer (remediation) | sonnet | extended | P1 (ACT-101) |
| ACT-402 | [SEAM] DI-1 gate wiring | Add `auth.di1_audit_acknowledged: bool` config flag (default `false`); extend `deployment_mode_validate()` (P1's stub) with condition (d): both the operator ack flag AND the audit artifact's frontmatter `status: accepted` (resolves OQ-3's path confirmation) must hold. This is the seam task (R-P3) bridging `codebase-explorer`'s audit output (an artifact status) with `python-backend-engineer`'s gate code. | FR-4 (full), FR-13 satisfied; gate raises `ValueError` if either half of the two-part check is missing — neither a stale doc nor an unread flag alone satisfies it. | 2 pts | python-backend-engineer | sonnet | adaptive | P1 (ACT-102 stub) |
| ACT-403 | Sharing/sensitivity regression pass | Re-verify §18 public-sharing/publish-preview gates and report-body sensitivity fail-closed checks under `deployment_mode=multi_user` with a real Clerk/local_static human session — regression, not new logic (carried from gap-closure human brief §2). | FR-18 satisfied; all existing gates still hold with enforcement flipped on. | 2 pts | python-backend-engineer | sonnet | adaptive | P2 sealed, P3 sealed |
| ACT-404 | Startup fail-closed gate test suite | Unit test suite covering AC-3 in full: all four FR-4 conditions independently (each unmet condition alone triggers refusal, with a specific message), plus the missing-artifact-file edge case (treated identically to `status != accepted`, never "assume passed"). | AC-3 fully green (all 4 conditions + missing-file case). | 1 pt | python-backend-engineer | sonnet | adaptive | ACT-402 |
| ACT-406 | **Mode D: Human sign-off on audit scope-boundary** | Present the audit's scope-boundary statement (what was enumerated, what was explicitly excluded and why, cross-check methodology) to a human reviewer. **No agent transitions the artifact's `status` to `accepted` — the executing agent stops after producing the draft and the scope-boundary statement, and awaits explicit human approval.** | Human reviewer explicitly approves; artifact `status: accepted` set only after that approval is recorded. Silence is treated as a blocker, never as a pass. | gate (human) | human (no agent delegate) | n/a | n/a | ACT-401 |
| REV-P4-001 | Reviewer gate: karen milestone | Mode E review of the audit methodology, remediation completeness, and gate-wiring correctness — runs alongside/after ACT-406, not a substitute for it. | karen approves; does not itself authorize `status: accepted` (that is ACT-406's human step). | gate | karen | opus | adaptive | ACT-401, ACT-402, ACT-403, ACT-404 |
| REV-P4-002 | Reviewer gate: task-completion-validator | Standard phase-completion review. | Validator confirms FR-4, FR-13, FR-14, FR-18 satisfied. | gate | task-completion-validator | sonnet | adaptive | ACT-406, REV-P4-001 |

**Phase point subtotal**: 13 pts (reviewer/human-gate rows excluded).

## Structured Acceptance Criteria

#### AC-3 (full): `multi_user` startup gate is fail-closed on every one of its four conditions independently
*(Reproduced from PRD §11; P1 delivers (a)–(c), this phase completes (d) and the full verification.)*
- target_surfaces:
    - src/research_foundry/config.py
    - src/research_foundry/api/app.py
- propagation_contract: >
    `Config.deployment_mode_validate()` is called at API app startup and by `rf serve`; it evaluates
    all four FR-4 conditions and raises `ValueError` naming every unmet condition (not just the
    first).
- resilience: >
    If the DI-1 audit artifact file is missing entirely (not just `status != accepted`), the gate
    treats this identically to an unaccepted audit (fail-closed, not "assume passed" or "assume
    file doesn't apply").
- visual_evidence_required: false
- verified_by:
    - ACT-404

## The Mode D Gate — Mechanics

Per `.claude/rules/delegation-modes.md` Mode D ("High-Risk Change... await explicit human approval before any production changes... no code writes without user sign-off"), this phase's boundary is precisely: **ACT-401 through ACT-404 may proceed under standard delegation (exploration, remediation code, test authoring) — but the single act of setting the audit artifact's `status` field to `accepted` is reserved for a human.**

1. `codebase-explorer` + `python-backend-engineer` complete ACT-401, producing the audit artifact at `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` with `status: draft` and a scope-boundary statement section.
2. `karen` (REV-P4-001) reviews methodology and remediation completeness — this is a quality review, not the sign-off itself.
3. **ACT-406 is the sign-off gate**: the scope-boundary statement is surfaced to the human (Nick); the agent stops and waits. No agent-initiated `status: accepted` transition is permitted.
4. Only after explicit human approval is recorded does `status: accepted` get set — by the human directly or by an agent acting on an unambiguous, explicit instruction to do so (not inferred from silence, a partial response, or a "looks good" without the word accept/approve).
5. ACT-402's runtime gate reads this `status` field at every `multi_user` startup — so until step 4 completes, `multi_user` **cannot start**, by construction.

This directly closes the WKSP-304 AAR failure mode: a prior "100% coverage" self-certification on this exact surface was later found incomplete two separate times. No repeat is structurally possible here because the artifact-status half of the gate cannot be satisfied by agent action alone.

## Quality Gates

- [ ] Audit artifact exists with complete, cross-checked surface inventory (row count vs. grep-derived count).
- [ ] All findings (including recurrence of the two prior known leaks) remediated in code.
- [ ] Two-part gate (`auth.di1_audit_acknowledged` + artifact `status: accepted`) wired and both required independently.
- [ ] AC-3 fully green (all 4 conditions + missing-artifact edge case).
- [ ] Sharing/publish-preview + sensitivity regression green under `multi_user` with a live session (ACT-403).
- [ ] **Mode D human sign-off recorded before `status: accepted`.**
- [ ] `karen` milestone pass (REV-P4-001).
- [ ] `task-completion-validator` pass (REV-P4-002).

## Key Files & Integration Points

- `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` (new artifact) — the audit itself.
- `docs/projects/research-foundry/SERVICE_CONTRACT.md` (769 lines, §14/§17/§18) — DI-1 references updated to point at the completed artifact.
- `src/research_foundry/config.py` — condition (d) added to `deployment_mode_validate()`.
- Remediation touches whatever leak sites ACT-401 finds — likely candidates per PRD context: `catalog_service.py`, `builder_service.py`, `agent_jobs.py` router (same surfaces as the two known prior leaks).
- `frontend/runs-viewer` E2E session (ACT-403) — needs a live Clerk/local_static human session against a `multi_user`-configured instance.

## Integration Owner

**`python-backend-engineer`** is the declared `integration_owner` (R-P3): ≥2 owner specialties (`codebase-explorer` enumeration, `python-backend-engineer` remediation + gate wiring) with overlapping surface (the audit artifact feeds directly into the gate code). ACT-402 is the dedicated seam task.

---

[← Phase 3](./phase-3-admin-api.md) | [← Back to main plan](../public-multiuser-release-activation-v1.md) | [Next: Phase 5 →](./phase-5-admin-ui.md)
