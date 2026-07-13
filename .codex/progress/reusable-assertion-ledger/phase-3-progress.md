---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-3-edition-passage-registry.md
execution_model: sequential
phase: 3
title: P2 Edition and Passage Registry
status: complete
created: '2026-07-13T20:53:25Z'
started: '2026-07-13T20:53:25Z'
completed: '2026-07-13T21:05:22Z'
updated: '2026-07-13T21:05:22Z'
commit_refs:
- 78bcb239d4bb4417dcb31c9d865b5fd93271608b
- ceb3bfc32b6551606f4df5df5a541b9eac6e67d9
- d65971e035b2b7a575d29405ea3fd8dac76c10ab
pr_refs: []
overall_progress: 100
completion_estimate: complete
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- data-layer-expert
- task-completion-validator
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P2-001
  description: Create idempotent source/edition persistence, raw and normalized hashes, revision lineage, allowed-use/sensitivity metadata, and workspace path isolation.
  status: completed
  assigned_to: [python-backend-engineer]
  dependencies: [P1-REVIEW]
  estimated_effort: 3 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  acceptance_criteria: [P2-REGISTRY]
  started: '2026-07-13T20:53:25Z'
  completed: '2026-07-13T20:53:25Z'
  evidence:
  - artifact: src/research_foundry/services/assertion_registry.py
  - test: tests/unit/test_assertion_registry.py::test_idempotent_edition_and_schema_valid_passage
  - test: tests/unit/test_assertion_registry.py::test_workspace_paths_are_isolated_and_unsupported_content_is_typed
  verified_by: [P2-002]
- id: P2-002
  description: Persist exact quote/context plus position, structural, and hash selectors; classify unresolved or changed passages as non-reusable drift.
  status: completed
  assigned_to: [python-backend-engineer]
  dependencies: [P2-001]
  estimated_effort: 3 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  acceptance_criteria: [P2-REGISTRY]
  started: '2026-07-13T20:53:25Z'
  completed: '2026-07-13T20:53:25Z'
  evidence:
  - artifact: src/research_foundry/services/assertion_registry.py
  - test: tests/unit/test_assertion_registry.py::test_multiformat_identity_is_deterministic_in_three_input_orders
  - test: tests/unit/test_assertion_registry.py::test_rights_and_ambiguous_selector_are_non_reusable_without_mutation
  verified_by: [P2-003]
- id: P2-003
  description: Integrate source-card/import entry points and multi-format fixtures without changing legacy source-card identity or canonical run files.
  status: completed
  assigned_to: [python-backend-engineer]
  dependencies: [P2-001, P2-002]
  estimated_effort: 2 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  acceptance_criteria: [P2-REGISTRY]
  started: '2026-07-13T20:53:25Z'
  completed: '2026-07-13T20:53:25Z'
  evidence:
  - artifact: src/research_foundry/services/source_cards.py
  - test: tests/unit/test_assertion_registry.py::test_interrupted_write_keeps_prior_manifest_complete
  - test: tests/unit/test_assertion_registry.py::test_source_card_registry_seam_is_opt_in_and_preserves_card_identity
  - test: tests/unit/test_assertion_registry.py::test_source_card_first_ingest_accepts_later_granular_passages
  - review: Independent task-completion-validator REQUEST CHANGES; thread 019f5d44-9f26-7152-ba82-1d454d11087f; checkpoint ceb3bfc32b6551606f4df5df5a541b9eac6e67d9; atomic generation correction pending review
  - test: tests/unit/test_assertion_registry.py::test_interrupted_multi_passage_union_keeps_published_generation_complete
  - validation: Saved-checkout Python focused pytest 18 passed; Ruff passed; mypy passed with --follow-imports=skip
  verified_by: [P2-REVIEW]
- id: P2-REVIEW
  description: Independent task-completion-validator review of P2-001 through P2-003 and AC P2-REGISTRY; this writer must not self-approve phase completion.
  status: completed
  assigned_to: [task-completion-validator]
  dependencies: [P2-003]
  estimated_effort: review gate
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  acceptance_criteria: [P2-REGISTRY]
  started: '2026-07-13T20:53:25Z'
  completed: '2026-07-13T21:05:22Z'
  evidence:
  - review: Independent task-completion-validator APPROVE; thread 019f5d44-9f26-7152-ba82-1d454d11087f; approved commit d65971e035b2b7a575d29405ea3fd8dac76c10ab; tree d9ab53bdfaa64df8304682ea0c69adc2214cb6ad; prior request-changes correction cycles ceb3bfc32b6551606f4df5df5a541b9eac6e67d9 and d65971e035b2b7a575d29405ea3fd8dac76c10ab accepted
  verified_by: [task-completion-validator]
parallelization:
  batch_1: [P2-001]
  batch_2: [P2-002]
  batch_3: [P2-003]
  batch_4: [P2-REVIEW]
  critical_path: [P2-001, P2-002, P2-003, P2-REVIEW]
  estimated_total_time: 8 pts plus independent review
blockers:
- id: P2-BLOCKER-001
  title: Feature enablement remains prohibited by the conditional P0 evidence boundary
  severity: high
  blocking: [RF_ASSERTION_LEDGER_ENABLED, RF_ASSERTION_REUSE_ENABLED, RF_CANONICAL_CLAIMS_ENABLED]
  resolution: Preserve assertion-only contracts and obtain the named corpus/upstream gates before any enablement decision.
success_criteria:
- id: AC-P2-REGISTRY
  description: Registry resolves immutable editions and passages deterministically while drift, ambiguity, and missing rights remain non-reusable.
  status: completed
  maps_to: [P2-001, P2-002, P2-003, P2-REVIEW]
notes:
- Independent review approved P2 at d65971e035b2b7a575d29405ea3fd8dac76c10ab.
- No schema or frontend contract changed, so codegen:check and TypeScript gates are not applicable to this Python-only checkpoint.
files_modified:
- src/research_foundry/services/assertion_registry.py
- src/research_foundry/services/source_cards.py
- tests/unit/test_assertion_registry.py
- tests/fixtures/assertion_ledger/p2_formats/
progress: 75
---

# Reusable Assertion Ledger — Phase 3 (P2): Edition and Passage Registry

P2-001 through P2-003 are implemented and await independent review. The registry
is private and file-canonical; source-card integration is explicit opt-in, so
assertion-only mode and all feature flags remain unchanged.

## Validation record

| Command | Result |
|---|---|
| Saved-checkout Python focused pytest for P2 registry and P1 regressions | Passed: 18 tests. |
| Saved-checkout Python Ruff for changed Python/test files | Passed. |
| Saved-checkout Python mypy with `--follow-imports=skip` for changed Python/test files | Passed: no issues in 3 source files. |
| `git diff --check` | Passed. |

## Review scope

Review idempotency, raw and normalized hashes, revision lineage, rights metadata,
exact selectors, typed drift/ambiguity handling, atomic-retry recovery, isolated
multi-format file trees, and the opt-in source-card seam. Do not authorize
feature flags, canonical-claim behavior, or Phase 4.
