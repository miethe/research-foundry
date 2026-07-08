---
schema_version: 2
doc_type: phase_plan
title: "WKSP-304 Phase 6: Docs / CHANGELOG / Runbook"
status: draft
created: 2026-07-08
phase: "P6"
phase_title: "Documentation finalization + final regression sign-off"
prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
feature_slug: wksp-304-workspace-isolation-enforcement
entry_criteria: ["Phase 5 mandatory task-completion-validator gate passed"]
exit_criteria:
  - "CHANGELOG [Unreleased] entry lands, correctly categorized"
  - "workspace-migration-runbook.md updated with enforcement section"
  - "config.py docstring parity with the RBAC flag"
  - "Final regression sign-off (TASK-6.1) re-confirms AC-6 through the doc-only changes in this phase"
  - "karen end-of-feature review passes"
---

# Phase 6: Docs / CHANGELOG / Runbook

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 5](./phase-5-regression-matrix.md)

**Duration**: ~0.5 day
**Dependencies**: Phase 5's mandatory `task-completion-validator` gate passed
**Assigned Subagent(s)**: `documentation-writer` (haiku, docs), `changelog-generator` (haiku, CHANGELOG); `python-backend-engineer` (sonnet, TASK-6.1 final regression sign-off only)

---

## Task Table

| Task ID | Task Name | Description | Verifies AC | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|--------------|----------|-------------|-------|--------|---------------|
| TASK-6.1 | Final regression sign-off (AC-6 closing confirmation) | Run the complete pre-existing + Phase 5 test suites one final time with `workspace_isolation_enforcement=enabled` globally, after the docstring-only changes in TASK-6.4 land — confirming the doc pass introduced zero behavioral delta and AC-6 (single-operator fallback) still holds unmodified. This is the plan's closing "break it if you dare" re-confirmation, immediately preceding `karen`'s end-of-feature review. | AC-6 | 0.1 pt | python-backend-engineer | sonnet | adaptive | TASK-6.4 |
| TASK-6.2 | Update CHANGELOG | Add an `[Unreleased]` entry per `.claude/specs/changelog-spec.md` categorization rules, describing the advisory-to-enforcing flip and the new `workspace_isolation_enforcement` config flag. Set `changelog_ref: CHANGELOG.md` in the parent plan's frontmatter. | — | 0.1 pt | changelog-generator | haiku | adaptive | All prior phases |
| TASK-6.3 | Update `workspace-migration-runbook.md` | Add an enforcement section: how `auto\|enabled\|disabled` resolves, the loopback-guard fail-closed behavior, and operator guidance for dry-running `auto` before hard-cutting to `enabled` in a shared-store multi-tenant deployment. | — | 0.15 pt | documentation-writer | haiku | adaptive | All prior phases |
| TASK-6.4 | `config.py` docstring parity | Bring the new flag's docstring depth to parity with `auth.rbac_enforcement`'s existing docstring — spell out the semantics of each enum value (`auto`/`enabled`/`disabled`) and the two fail-closed invariants. Docstring-only change; no logic touched. | — | 0.1 pt | documentation-writer | haiku | adaptive | All prior phases |
| TASK-6.5 | Finalize plan frontmatter | Set `status: completed`, populate `commit_refs`, `files_affected` (final list), `updated`; confirm `deferred_items_spec_refs: []` and `findings_doc_ref` reflect final state (N/A unless a finding was captured during execution). | — | 0.05 pt | documentation-writer | haiku | adaptive | TASK-6.1 through TASK-6.4 |

**Phase 6 total**: 0.5 pt (matches decisions block §4 estimation anchor).

---

## Quality Gates

- [ ] CHANGELOG `[Unreleased]` section contains an entry matching this feature (required — `changelog_required: true`).
- [ ] `workspace-migration-runbook.md` reflects enforcement availability and the `auto|enabled|disabled` operator decision.
- [ ] `config.py` docstring depth matches the RBAC flag's docstring.
- [ ] TASK-6.1 final regression sign-off passes with zero test modifications.
- [ ] Plan frontmatter finalized (`status`, `commit_refs`, `files_affected`, `updated`).
- [ ] `deferred_items_spec_refs` / `findings_doc_ref` reflect final state (both remain empty/null per this plan's "N/A — no deferred items" policy, unless an in-flight finding was captured — see parent plan's Deferred Items & In-Flight Findings Policy).
- [ ] **`karen` end-of-feature review passes** — required for this Tier 2, `risk_level: high` feature before the feature is considered complete.

## Key Files and Integration Points

- `CHANGELOG.md`
- `docs/dev/architecture/workspace-migration-runbook.md`
- `src/research_foundry/config.py` (docstring only in this phase)

## Wrap-Up

After this phase's gates pass and `karen` signs off, proceed to the parent plan's **Wrap-Up: Feature Guide & PR** section (feature guide at `.claude/worknotes/wksp-304-workspace-isolation-enforcement/feature-guide.md`, then `gh pr create`).

---

[Back to parent plan](../wksp-304-workspace-isolation-enforcement-v1.md) | [Previous: Phase 5](./phase-5-regression-matrix.md)
