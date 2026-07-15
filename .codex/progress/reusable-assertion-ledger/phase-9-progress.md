---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-9-docs-private-rollout.md
execution_model: sequential
phase: 9
title: P8 Documentation and Private Rollout Readiness
status: pending
completion_estimate: completed_repository_readiness_private_rollout_not_executed
created: '2026-07-15T00:00:00Z'
started: '2026-07-15T00:00:00Z'
updated: '2026-07-15T03:00:00Z'
completed: '2026-07-15T03:00:00Z'
commit_refs:
- 9cf7e6b8f12cb16d8f755eb50bf8be0d513c0ee1
- 26e8f77afc2f8fb079f8e49cf2f760844a51214d
pr_refs: []
overall_progress: 80
total_tasks: 6
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
owners:
- codex-p8-writer
contributors: []
model_usage:
  primary: gpt-5
  external: []
tasks:
- id: P8-001
  description: Default-off controls, fail-closed consumer dependencies, and privacy-safe
    local readiness receipts.
  status: completed
  assigned_to:
  - codex-p8-writer
  dependencies:
  - P7-REVIEW
  estimated_effort: 2 pts
  priority: critical
  acceptance_criteria:
  - AC-P8-ROLLOUT
  started: '2026-07-15T00:00:00Z'
  completed: '2026-07-15T00:00:00Z'
  verified_by:
  - codex-p8-writer
  evidence:
  - foundry.yaml
  - src/research_foundry/config.py
  - src/research_foundry/services/assertion_rollout.py
  - scripts/assertion_ledger_readiness.py
  - tests/unit/test_assertion_rollout.py
- id: P8-002
  description: User, developer, and operator documentation plus Unreleased changelog
    entry.
  status: completed
  assigned_to:
  - codex-p8-writer
  dependencies:
  - P8-001
  estimated_effort: 1 pt
  priority: high
  acceptance_criteria:
  - AC-P8-ROLLOUT
  started: '2026-07-15T00:00:00Z'
  completed: '2026-07-15T00:00:00Z'
  verified_by:
  - codex-p8-writer
  evidence:
  - docs/user/assertion-ledger.md
  - docs/dev/architecture/assertion-ledger-contract.md
  - docs/dev/architecture/runbooks/assertion-ledger-readiness.md
  - README.md
  - CHANGELOG.md
- id: DOC-006
  description: Deferred shared-index and public-rights design specs with future SPIKE
    gates and root-plan references.
  status: completed
  assigned_to:
  - codex-p8-writer
  dependencies:
  - P7-REVIEW
  estimated_effort: 1 pt
  priority: high
  acceptance_criteria:
  - AC-P8-ROLLOUT
  started: '2026-07-15T00:00:00Z'
  completed: '2026-07-15T00:00:00Z'
  verified_by:
  - codex-p8-writer
  evidence:
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
- id: P8-004
  description: Authorized private-beta rollout and health observation.
  status: not_executed_owner_data_absent
  assigned_to:
  - private-workspace-owner
  dependencies:
  - P8-001
  - P8-002
  reason: No authorized private workspace, private data, observation window, or rollout
    authority was supplied.
- id: P8-005
  description: Repository-owned reconciliation of docs, inventory, tests, deferred-spec
    references, and review handoff.
  status: completed
  assigned_to:
  - codex-p8-writer
  dependencies:
  - DOC-006
  - P8-004
  estimated_effort: 2 pts
  priority: high
  acceptance_criteria:
  - AC-P8-ROLLOUT
  started: '2026-07-15T00:00:00Z'
  completed: '2026-07-15T00:00:00Z'
  verified_by:
  - codex-p8-writer
  evidence:
  - .codex/progress/reusable-assertion-ledger/phase-9-progress.md
  - docs/dev/architecture/artifact-type-reference.md
  - tests/unit/test_assertion_rollout.py
- id: P8-REVIEW
  description: Independent exact-tree review is required before metadata closeout.
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies:
  - P8-001
  - P8-002
  - DOC-006
  - P8-005
  estimated_effort: review gate
  priority: critical
  acceptance_criteria:
  - AC-P8-ROLLOUT
  completed: '2026-07-15T03:00:00Z'
  verified_by:
  - Terra-Tier-3
  - Sol-final-high-risk-review
  evidence:
  - review: Terra Tier-3 APPROVE after correction at 9cf7e6b8f12cb16d8f755eb50bf8be0d513c0ee1
      / 26e8f77afc2f8fb079f8e49cf2f760844a51214d
  - review: Sol final high-risk feature review APPROVE at 9cf7e6b8 / 26e8f77a
  - review: 9cf7e6b8f12cb16d8f755eb50bf8be0d513c0ee1/26e8f77afc2f8fb079f8e49cf2f760844a51214d
  started: '2026-07-15T02:59:00Z'
parallelization:
  batch_1:
  - P8-001
  - DOC-006
  batch_2:
  - P8-002
  - P8-005
  batch_3:
  - P8-REVIEW
  critical_path:
  - P8-001
  - P8-002
  - P8-005
  - P8-REVIEW
  estimated_total_time: repository readiness plus independent review
blockers: []
success_criteria:
- id: AC-P8-ROLLOUT
  description: Default-off configuration, safe local receipts, recovery documentation,
    and deferred shared/public scope are reviewable without a private rollout claim.
  status: completed_repository_readiness_private_rollout_not_executed
  private_rollout: not_executed_owner_data_absent
runtime_boundary:
  phase_8_exact_approval:
    commit: f5ce6ae004b7a83970320e4ec6f992cb1e8ed68a
    tree: d6f3fe1ad01b53907aab6ad949941fe0a62f7673
    verdict: Terra Tier-3 APPROVE
  phase_9_exact_approval:
    commit: 9cf7e6b8f12cb16d8f755eb50bf8be0d513c0ee1
    tree: 26e8f77afc2f8fb079f8e49cf2f760844a51214d
    verdict: Terra Tier-3 APPROVE after correction; Sol final high-risk feature review
      APPROVE
  prohibited:
  - push
  - deploy
  - release
  - private_rollout
  - external_writeback
  - shared_index
  - public_promotion
progress: 83
---

# Reusable Assertion Ledger — Phase 9 (P8): Review-State Readiness

Repository-owned readiness is being implemented on this branch. Private rollout
remains `not_executed_owner_data_absent`; it is not a passing rollout result and
does not authorize any feature flag, private-corpus health check, or external
writeback. Phase 8 metadata and root-plan/PRD completion remain untouched.

## Repository evidence

- P8-001: `foundry.assertion_ledger` defines three literal-true, default-off
  controls; `assertion_rollout.py` and `assertion_ledger_readiness.py` provide
  idempotent dry-run and disable/rollback rehearsal receipts with aggregate-only
  metrics. The run-launch reuse consumer and source-card registry seam fail
  closed against the resolved controls.
- P8-002: user guide, architecture contract, runbook, README link, artifact
  inventory, and `[Unreleased]` changelog entry document semantics, recovery,
  denial/correction states, and private limits.
- DOC-006: shared-index and public-rights/promotion scope is deferred in two
  design specs linked by the root plan; neither scope is implemented.
- P8-004: `not_executed_owner_data_absent`. No authorized private workspace,
  data, observation window, rollout authority, deployment, or external
  writeback was supplied or used.
- P8-005: repository docs, configuration, tests, deferred-spec references, and
  review handoff reconciled. Independent review remains pending.

## Local receipt rehearsal

`tests/fixtures/assertion_ledger/prepare_p7_runtime_fixture.py` created a
temporary synthetic workspace, then
`scripts/assertion_ledger_readiness.py --root <synthetic-root> --write-receipts`
reported four run directories, four claim ledgers, four assertion records, zero
automated-reuse actions, zero external-writeback actions, and zero public-
promotion actions. Its backfill receipt reported `authoritative_data_mutated:
false`; its rollback rehearsal targeted all three controls to `false` while
preserving authoritative ledger records. The temporary workspace and local
receipts were removed after the check. This is repository-local synthetic
evidence only; P8-004 remains `not_executed_owner_data_absent`.

## Full-suite boundary

The full Python suite reaches completion but currently has six failures outside
the Phase 9 diff: five `tests/test_serve_api.py` cases expect `200` and receive
`404`, plus `tests/unit/test_report_anchors.py` expects export schema `1.4`.
The approved Phase 8 base already has `EXPORT_SCHEMA_VERSION = "1.5"`, and this
checkpoint does not modify those tests, export service, or API paths. Focused
P8/P3–P7 regression tests pass; the unrelated full-suite failures remain a
review risk rather than being rewritten in this phase.
