---
title: "Phase 6: Testing & Documentation Finalization"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
phase: P6
phase_title: "Testing & Documentation Finalization"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
integration_owner: python-backend-engineer
entry_criteria:
  - "P2, P3, P4, P5 all sealed (all phase-level reviewer gates passed, including P4's Mode D sign-off)."
exit_criteria:
  - "Full suite green."
  - "karen end-of-feature review passed."
  - "CHANGELOG [Unreleased] entry present."
---

# Phase 6: Testing & Documentation Finalization

[← Back to main plan](../public-multiuser-release-activation-v1.md)

**Estimate**: 6 pts
**Dependencies**: P2, P3, P4, P5 all sealed (`batch_5` — final wave)
**Assigned Subagent(s)**: `python-backend-engineer` (backend/E2E), `ui-engineer` (UI tests), `documentation-writer`, `changelog-generator`
**Model**: sonnet throughout (haiku hard-errors in this environment — do not dispatch docs tasks on haiku despite the template's default) | **Effort**: adaptive
**Mode**: E — Reviewer (for the `karen` end-of-feature pass); standard delegation for all authoring tasks.

## Overview

Cross-phase test coverage assembly, CHANGELOG, and doc updates. This phase is deliberately lean on "hidden plumbing" (see main plan's Estimation Sanity Check, H6) because most plumbing — DTOs, audit wiring, gate wiring — was priced directly into P2–P4. This phase's job is closing the loop: proving the whole feature works end-to-end, and making sure every doc surface a future operator or agent would consult reflects the new reality.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|---------------|
| ACT-601 | Unit + integration test suite (cross-phase) | Assemble/finalize full coverage per PRD §11 Quality Acceptance: deployment-mode resolver (all preset/override combos), token issue/verify/revoke/expire, PAT role-ceiling re-check, agent-job identity binding — cross-phase integration pass verifying AC-4 (missing/expired token resilience) end-to-end across the full request path. | §11 Quality Acceptance unit+integration bullets all green. | 2 pts | python-backend-engineer | sonnet | adaptive | P2, P3, P4 sealed |
| ACT-602 | [SEAM] E2E smoke: admin UI issue→revoke round-trip | R-P4 runtime-smoke task (this plan has `.tsx` files in scope): full E2E — issue a service account and a PAT via the live admin UI, verify token works, revoke, verify token now rejected — against a live API with `deployment_mode=multi_user`. Seam task (R-P3) between backend (P2/P3) and frontend (P5) test ownership. | AC-1 and AC-2 verified end-to-end in a real browser session, not just unit-mocked. | 1 pt | python-backend-engineer + ui-engineer | sonnet | adaptive | ACT-601, P5 sealed |
| ACT-603 | Update CHANGELOG | Add `[Unreleased]` entry per `.claude/specs/changelog-spec.md`: deployment-mode presets, service accounts, PATs, DI-1 gate. `changelog_required: true` on this plan makes this task mandatory. | Entry exists under `[Unreleased]` with correct categorization; `changelog_ref` set to `CHANGELOG.md`. | 0.5 pts | changelog-generator | sonnet | adaptive | ACT-601 |
| ACT-604 | Docs: config reference + admin API + SERVICE_CONTRACT.md | Document `deployment_mode`, `auth.di1_audit_acknowledged`, `agents.default_service_account_id` in the `foundry.yaml` reference docs; add admin API endpoint docs (issue/list/revoke/rotate, both principal types) alongside the existing `admin.py` docstring contract; confirm `SERVICE_CONTRACT.md` §14/§17/§18 DI-1 references (updated in P4 ACT-401) are consistent and complete. | All three doc surfaces updated and cross-checked against the shipped code. | 1 pt | documentation-writer | sonnet | adaptive | ACT-601, P4 (ACT-401) |
| ACT-605 | `rf` skill currency note | The `rf serve --mode` CLI surface change (ACT-102) is a CLI-surface change per the "rf skills currency pass" pattern — add/update the relevant currency note so agents consulting `rf`-CLI-facing skill docs see the new flag. | `rf serve --mode` documented wherever the project's `rf` CLI surface is indexed for agent consumption. | 0.5 pts | documentation-writer | sonnet | adaptive | ACT-101, ACT-102 |
| ACT-606 | Deferred-items design specs (DOC-006) | Author design specs for all 3 deferred items per the main plan's Deferred Items Triage Table: DF-001 (OIDC adapter live implementation, `maturity: idea` — direction genuinely unknown, needs procurement first), DF-002 (Postgres migration of `rbac.db`, `maturity: idea`), DF-003 (service-account fine-grained scoping, `maturity: shaping` — direction is reasonably clear: extend the existing role model, not invent a new permission matrix). Set `prd_ref` on each to this feature's PRD; append all 3 paths to this plan's `deferred_items_spec_refs`. | All 3 design specs authored and linked; `deferred_items_spec_refs` populated. | 0.75 pts | documentation-writer | sonnet | adaptive | All impl phases |
| ACT-607 | Plan frontmatter + findings-doc finalize | Set this plan's `status: completed`, populate `commit_refs`/`files_affected`/`updated`; if `findings_doc_ref` is non-null (any in-flight findings occurred), advance its `status` from `draft` → `accepted` and set `promoted_to`. Skip the findings half with "N/A — no findings captured" if `findings_doc_ref` remained null. | Plan frontmatter complete per lifecycle spec; findings doc finalized or N/A documented. | 0.25 pts | documentation-writer | sonnet | adaptive | ACT-603, ACT-604, ACT-605, ACT-606 |
| REV-P6-001 | Reviewer gate: karen end-of-feature | Mode E final review across the full feature — all 6 phases, all reviewer gates, Mode D sign-off record, deferred-items triage completeness. | karen approves; this is the last gate before the plan can be marked `completed`. | gate | karen | opus | adaptive | ACT-602, ACT-607 |
| REV-P6-002 | Reviewer gate: task-completion-validator | Standard phase-completion review of P6 specifically. | Validator confirms §11 Quality/Documentation Acceptance fully satisfied. | gate | task-completion-validator | sonnet | adaptive | REV-P6-001 |

**Phase point subtotal**: 6 pts (reviewer-gate rows excluded).

## Structured Acceptance Criteria

#### AC coverage cross-check (not a new AC — verification index)
This phase's `verified_by` obligations from earlier phases:
- AC-1 (Phase 5) → ACT-602
- AC-2 (Phase 2) → ACT-601 (cross-phase integration pass), ACT-602 (E2E)
- AC-3 (Phase 1/4) → already fully verified in Phase 4 (ACT-404); no re-verification task needed here
- AC-4 (Phase 2, R-P2 guard) → ACT-601
- AC-5 (Phase 2, R-P2 guard) → verified in Phase 2 (ACT-205); no re-verification task needed here
- R-P1 guard (Phase 3, `require_role` sweep) → ACT-601

## Quality Gates

- [ ] §11 Quality Acceptance unit+integration bullets all green.
- [ ] E2E issue→revoke round trip passes against a live API (ACT-602).
- [ ] CHANGELOG `[Unreleased]` section contains an entry matching this feature (mandatory — `changelog_required: true`).
- [ ] `foundry.yaml` reference, admin API docs, `SERVICE_CONTRACT.md` DI-1 references all current.
- [ ] `rf` skill currency note reflects the `--mode` CLI flag.
- [ ] All 3 deferred items (DF-001, DF-002, DF-003) have design-spec paths in `deferred_items_spec_refs`.
- [ ] Findings doc finalized (`status: accepted`) if populated, or `findings_doc_ref` remains `null`.
- [ ] Plan frontmatter complete (`status: completed`, `commit_refs`, `files_affected`, `updated`).
- [ ] `karen` end-of-feature pass (REV-P6-001) — do not mark the plan `completed` without this.
- [ ] `task-completion-validator` pass (REV-P6-002).

## Key Files & Integration Points

- `CHANGELOG.md` — `[Unreleased]` entry (ACT-603).
- `docs/projects/research-foundry/SERVICE_CONTRACT.md` (769 lines) — consistency check against P4's updates (ACT-604).
- `docs/project_plans/design-specs/oidc-adapter-live-implementation.md`, `.../rbac-db-postgres-migration.md`, `.../service-account-fine-grained-scoping.md` (new, ACT-606).
- Wrap-Up step (per implementation-plan-template.md, triggered automatically after this phase seals): feature guide at `.claude/worknotes/public-multiuser-release-activation/feature-guide.md`, then PR.

## Integration Owner

**`python-backend-engineer`** is the declared `integration_owner` for ACT-602 (R-P3): the E2E round-trip spans both backend (P2/P3 endpoints) and frontend (P5 panels) test ownership, with `ui-engineer` as the co-owner for the browser-side assertions.

---

[← Phase 5](./phase-5-admin-ui.md) | [← Back to main plan](../public-multiuser-release-activation-v1.md)
