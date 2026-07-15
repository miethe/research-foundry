---
schema_version: 2
doc_type: phase_plan
title: "Phase 9 (P8): Documentation and Private Rollout"
status: review
created: 2026-07-12
updated: 2026-07-15
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 9
phase_id: P8
phase_title: Documentation and Private Rollout
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P7 validator and Karen milestone reviews passed.
  - Private-beta workspace and operator authorization are explicit.
exit_criteria:
  - Docs, CHANGELOG, feature flags, migration/backfill, rollback, monitoring, and private-beta health evidence pass.
  - Shared-index and public-rights work remains deferred in design specs.
related_documents:
  - docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md
spike_ref: null
integration_owner: lead-pm
ui_touched: false
target_surfaces: []
seam_tasks: [P8-004]
owner: lead-pm
contributors: [documentation-writer, changelog-generator, DevOps, python-backend-engineer]
priority: high
risk_level: high
files_affected:
  - docs/user/
  - docs/dev/architecture/
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md
  - README.md
  - CHANGELOG.md
  - src/research_foundry/config.py
  - tests/
---

# Phase 9 (P8): Documentation and Private Rollout

**Effort:** 8 points
**Dependencies:** P7 approved. No public or production deployment authority is inferred.

## Outcome

Make the private pilot operable, reversible, measurable, and understandable. Keep reuse and canonical claims independently gated after ledger-write enablement.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P8-001 | Flags, migration, rollback, monitoring [H6] | Wire three flags, produce idempotent migration/backfill and disable/rollback runbook, emit safe health/economics metrics, and rehearse receipts. | 2 pts | DevOps, python-backend-engineer | sonnet | adaptive | P7 |
| P8-002 | User/dev docs and CHANGELOG [H6] | Document assertion/canonical-claim/inference semantics, packets, denial reasons, review, correction, private boundary, operator commands, and `[Unreleased]` entry. | 1 pt | documentation-writer, changelog-generator | haiku | adaptive | P8-001 |
| DOC-006 | Deferred design specs [H6] | Author shared-index isolation and public-rights/promotion design specs, include deal-killers and future SPIKE gates, then append both created paths to the root plan's `deferred_items_spec_refs`; implement none of that scope. | 1 pt | documentation-writer, backend-architect | sonnet | adaptive | P7 |
| P8-004 | Private-beta rollout and health | Enable only in an authorized private workspace, keep automated reuse/canonical claims off until their receipts permit, run health/rollback checks, and prepare evidence for reviewer closeout. | 2 pts | DevOps, lead-pm | sonnet | adaptive | P8-001, P8-002 |
| P8-005 | Operational closure | Reconcile docs, architecture inventory, generated artifacts, test evidence, feature-guide handoff, and reviewer finding dispositions. | 2 pts | lead-pm, documentation-writer | sonnet | extended | DOC-006, P8-004 |

## Structured acceptance

#### AC P8-ROLLOUT: Private beta is independently gated and reversible
- target_surfaces:
  - `src/research_foundry/config.py`
  - `docs/dev/architecture/assertion-ledger-contract.md`
  - `docs/user/assertion-ledger.md`
  - `CHANGELOG.md`
- propagation_contract: Configuration exposes separate ledger-write, automated-reuse, and canonical-claim controls; docs/runbooks name their prerequisites; rollout receipts record actual states and health.
- resilience: Missing configuration defaults each capability off; failed health, migration, isolation, or rollback checks disable reuse and preserve canonical run evidence.
- visual_evidence_required: false
- verified_by: [P8-004, P8-005]

## File ownership

- `DevOps` owns flags, health checks, monitoring, and rollout/rollback receipts.
- `documentation-writer` owns user/dev docs and both deferred design specs.
- `changelog-generator` owns the `[Unreleased]` entry.
- `lead-pm` owns cross-artifact closeout; `P8-004` is the rollout seam.

## Private rollout sequence

1. Start with three flags off and run migration dry-run plus rollback rehearsal.
2. Enable ledger writes in one authorized private workspace; verify existing run output remains canonical.
3. Enable read/search UI only after scoped health checks pass.
4. Enable automated reuse only when replay, provenance, lifecycle, and isolation receipts are attached.
5. Enable canonical claims only for a `go` merge verdict; otherwise preserve assertion-only mode.
6. Observe agreed private-beta window, then pass health evidence to final reviewers.

## Quality and review gates

- [ ] Documentation explains semantics, denial states, correction flow, private scope, and recovery.
- [ ] CHANGELOG `[Unreleased]` records the user-facing capability.
- [ ] Deferred specs exist without shipping shared/public behavior.
- [ ] Feature flags default off and rollback preserves ledger/run evidence.
- [ ] Private-beta health metrics contain no sensitive passage text.
- [ ] `task-completion-validator` passes P8.
- [ ] Karen final review resolves or explicitly rejects each actionable finding with evidence.

## Validation

- Validate docs links, CLI/API examples, config defaults, and CHANGELOG placement.
- Run migration/backfill dry-run, private enablement smoke, disable/rollback, and health queries.
- Confirm no public corpus, shared index, external writeback, or broad production deployment occurred.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
