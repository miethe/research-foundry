---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-4-assertion-materialization.md
execution_model: sequential
phase: 4
title: P3 Assertion Materialization
status: complete
created: '2026-07-14T01:38:37Z'
started: '2026-07-14T01:37:56Z'
updated: '2026-07-14T02:21:46Z'
commit_refs:
- 302ddc3ab9e7acaa886d030d4ddcbe74f81ac217
- 4218964c86c32e946c243029fbf7ccf154e1647e
- 483a716eec859e5213964da714add10634926d8d
- 974747a733379e63b22449ac7cd6bbe758e03b78
pr_refs: []
overall_progress: 100
completion_estimate: complete
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- p3-recovery-sole-writer
contributors: []
model_usage:
  primary: codex
  external: []
tasks:
- id: P3-001
  description: Persist exact passage-bound source assertions, rule evaluations, and audit observations from the constrained deterministic extraction-card fact to claim locator contract.
  status: completed
  assigned_to: [p3-recovery-sole-writer]
  dependencies: [P2-REVIEW]
  estimated_effort: 3 pts
  priority: high
  assigned_model: codex
  model_effort: extra-high
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-14T01:37:56Z'
  completed: '2026-07-14T01:37:56Z'
  evidence:
  - commit: 302ddc3ab9e7acaa886d030d4ddcbe74f81ac217
  - artifact: src/research_foundry/services/assertion_materialization.py
  - artifact: src/research_foundry/services/claim_mapping.py
  - test: tests/unit/test_assertion_materialization.py::test_p3_materializes_one_exact_fact_claim_passage_chain
  - test: tests/unit/test_assertion_materialization.py::test_fabricated_passage_provenance_abstains_without_materialization
  - commit: 4218964c86c32e946c243029fbf7ccf154e1647e
  - test: tests/unit/test_assertion_materialization.py::test_tampered_extraction_snapshot_cannot_select_registry_passage
  - test: tests/unit/test_assertion_materialization.py::test_tampered_source_card_snapshot_cannot_select_registry_edition
  verified_by: [focused-validation]
- id: P3-002
  description: Implement exact deterministic dedupe plus bounded, cursor-resumable P0 replay; reject conflicting records, forged provenance, ambiguous passage bindings, registry traversal, and workspace substitution.
  status: completed
  assigned_to: [p3-recovery-sole-writer]
  dependencies: [P3-001]
  estimated_effort: 3 pts
  priority: high
  assigned_model: codex
  model_effort: extra-high
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-14T01:37:56Z'
  completed: '2026-07-14T01:37:56Z'
  evidence:
  - commit: 302ddc3ab9e7acaa886d030d4ddcbe74f81ac217
  - artifact: src/research_foundry/services/assertion_registry.py
  - test: tests/unit/test_assertion_materialization.py::test_identical_historical_runs_share_assertion_identity_but_keep_observations
  - test: tests/unit/test_assertion_materialization.py::test_conflicting_existing_deterministic_assertion_is_rejected
  - test: tests/unit/test_assertion_materialization.py::test_tampered_registry_generation_path_is_confined_and_rejected
  - test: tests/unit/test_assertion_materialization.py::test_bounded_resumable_replay_retains_identity
  - commit: 4218964c86c32e946c243029fbf7ccf154e1647e
  - test: tests/unit/test_assertion_registry.py::test_fabricated_passage_is_rejected_before_registry_publication
  - test: tests/unit/test_assertion_materialization.py::test_tampered_published_edition_provenance_abstains_without_mutation
  - commit: 483a716eec859e5213964da714add10634926d8d
  - test: tests/unit/test_assertion_materialization.py::test_external_symlinked_registry_artifact_abstains_without_mutation
  verified_by: [focused-validation]
- id: P3-003
  description: Materialize optional persistent edition, passage, and assertion references into existing claim ledgers without changing run-local IDs, source entries, report locations, anchors, or inference semantics.
  status: completed
  assigned_to: [p3-recovery-sole-writer]
  dependencies: [P3-001, P3-002]
  estimated_effort: 2 pts
  priority: high
  assigned_model: codex
  model_effort: extra-high
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-14T01:37:56Z'
  completed: '2026-07-14T01:37:56Z'
  evidence:
  - commit: 302ddc3ab9e7acaa886d030d4ddcbe74f81ac217
  - artifact: src/research_foundry/services/assertion_materialization.py
  - artifact: src/research_foundry/services/export_service.py
  - test: tests/unit/test_assertion_materialization.py::test_legacy_and_enriched_export_shapes_preserve_local_claim_semantics
  - test: tests/integration/test_export_round_trip.py
  verified_by: [focused-validation]
- id: P3-REVIEW
  description: Independent task-completion-validator review of P3-001 through P3-003 and AC P3-LINEAGE; this writer must not self-approve the phase.
  status: completed
  assigned_to: [task-completion-validator]
  dependencies: [P3-003]
  estimated_effort: review gate
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-14T02:21:46Z'
  completed: '2026-07-14T02:21:46Z'
  evidence:
  - reviewer_task: 019f5e4d-c031-7763-a3bb-93fee471db24
  - reviewer_checkpoint: 974747a733379e63b22449ac7cd6bbe758e03b78
  - reviewer_tree: 6d247da3f61566d25caaa31ad221db590e4b5d9a
  - reviewer_verdict: Physical Phase 4/logical P3 APPROVE
  - reviewer_verdict: Cumulative phases 3-4 milestone APPROVE
  - validation: 166 passed, 4 skipped; Ruff, focused mypy (4 sources), strict artifact/phase/AC/diff, codegen 27/27, and exact tsc all passed
  verified_by: [019f5e4d-c031-7763-a3bb-93fee471db24]
parallelization:
  batch_1: [P3-001]
  batch_2: [P3-002]
  batch_3: [P3-003]
  batch_4: [P3-REVIEW]
  critical_path: [P3-001, P3-002, P3-003, P3-REVIEW]
  estimated_total_time: 8 pts plus independent review
blockers:
- id: P3-BLOCKER-001
  title: Feature enablement remains prohibited by the conditional P0 evidence boundary
  severity: high
  blocking: [RF_ASSERTION_LEDGER_ENABLED, RF_ASSERTION_REUSE_ENABLED, RF_CANONICAL_CLAIMS_ENABLED]
  resolution: Preserve the assertion-only contract and obtain the named corpus and upstream gates before any enablement decision.
success_criteria:
- id: AC-P3-LINEAGE
  description: Persistent references remain additive; exact passage-bound assertions, evaluations, and audit observations are private, deterministic, resilient to interruption, and never imply canonical or inference behavior.
  status: completed
  maps_to: [P3-001, P3-002, P3-003, P3-REVIEW]
notes:
- P3 consumes only the existing versioned deterministic 1:1 extraction-card fact to claim locator contract. Draft citation precision/recall and segmentation/alignment charters remain deferred.
- No feature flag was enabled, no canonical record was materialized, and no Phase 5 work was implemented.
- Independent reviewer `019f5e4d-c031-7763-a3bb-93fee471db24` approved physical Phase 4/logical P3 and the cumulative phases 3-4 milestone at implementation checkpoint `974747a733379e63b22449ac7cd6bbe758e03b78` / tree `6d247da3f61566d25caaa31ad221db590e4b5d9a`; this writer recorded the disposition and did not self-approve.
- The tracker-only closeout commit is not part of the reviewed implementation checkpoint.
- "Correction cycle 1 closes reviewer finding P1 on `696cb362`: immutable rendition bytes, deterministic passage selectors, and source-card snapshot provenance now fail closed before selection or publication."
- "Correction cycle 2 closes reviewer finding P1 on `5a6a033`: descriptor-walked no-follow reads reject symlinked or path-substituted edition, rendition, provenance, publication, and passage artifacts before materialization."
files_modified:
- src/research_foundry/services/assertion_materialization.py
- src/research_foundry/services/assertion_registry.py
- src/research_foundry/services/claim_mapping.py
- src/research_foundry/services/source_cards.py
- tests/unit/test_assertion_materialization.py
- tests/unit/test_assertion_registry.py
---

# Reusable Assertion Ledger — Phase 4 (P3): Assertion Materialization

## Independent approval recorded

P3-001 through P3-003 are implemented at
`302ddc3ab9e7acaa886d030d4ddcbe74f81ac217`. Correction cycle 1 for the
independent reviewer's P1 provenance-integrity finding is implemented at
`4218964c86c32e946c243029fbf7ccf154e1647e`. Correction cycle 2 for the
path-substitution finding is implemented at
`483a716eec859e5213964da714add10634926d8d`. Independent reviewer task
`019f5e4d-c031-7763-a3bb-93fee471db24` issued both the physical
Phase 4/logical P3 APPROVE and cumulative phases 3-4 milestone APPROVE verdicts
against implementation checkpoint `974747a733379e63b22449ac7cd6bbe758e03b78`
(tree `6d247da3f61566d25caaa31ad221db590e4b5d9a`). This tracker-only closeout
commit records that disposition; it was not itself part of the reviewed
implementation checkpoint.

## Evidence scope

The materializer publishes only after an exact source-card, source-key,
edition, passage, evidence-ID, and locator binding succeeds. It keeps
run-local claim IDs, source links, report locations, anchors, and inference
fields unchanged, adding a persistent-reference object only for eligible
source assertions. Canonical, inference, malformed, ambiguous, forged, and
path-substituted candidates abstain or reject without publication.

Correction cycle 1 also proves an exact selected quote against immutable
edition bytes and selectors. Edition content identity, access scope, allowed
use, retrieval locator, and the stable source-card evidence snapshot are
verified at load and again before P3 materialization. A changed extraction
fact cannot diverge from that source-card quote.

Correction cycle 2 opens immutable registry files through a descriptor walk
anchored under the expected workspace and edition/generation directories. Each
component is no-follow where supported and inode-checked; edition, rendition,
provenance, publication, and passage symlinks abstain before a durable P3 write.

## Validation record

| Command | Result |
| --- | --- |
| Saved-checkout Python P3/P2/P1/pipeline/export pytest | Passed: 166 passed, 4 skipped (prior 161-test scope plus 5 symlink/path-substitution regressions). |
| Saved-checkout Python Ruff for changed sources/tests | Passed. |
| Saved-checkout Python mypy with `--follow-imports=skip` for changed services | Passed: no issues in 4 source files. |
| Saved-checkout frontend `codegen:check` harness | Passed: 27 generated artifacts verified. |
| Saved-checkout frontend exact `tsc -b --pretty false` harness | Passed. |
| Strict artifact validator, phase-completion validator, AC coverage report, and `git diff --check` | Passed. |

The independent reviewer also confirmed that all five artifact-symlink cases,
five directory-component symlink cases, out-of-root routing, and a forced
stat/open swap reject before mutation, while regular files materialize.

## Review scope

Review the constrained 1:1 fact-to-claim contract, source-card/source-key/
edition/passage/locator binding, deterministic cross-run identity, immutable
conflict detection, generation-pointer integrity, retry behavior, bounded
replay cursor, workspace confinement, additive export behavior, and the
continued flag/canonical/Phase-5 boundaries.
