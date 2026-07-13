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
status: review
created: '2026-07-13T21:07:20Z'
started: '2026-07-13T21:07:20Z'
completed: null
updated: '2026-07-13T21:51:41Z'
commit_refs: [ada09b1ef2d3d61213e0f2591f1165dc7967c274, 36039f57638eb44b26fdd22df425b74659ca540d]
pr_refs: []
overall_progress: 75
completion_estimate: on-track
total_tasks: 4
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
owners: [python-backend-engineer]
contributors: [backend-architect, task-completion-validator]
model_usage: {primary: gpt-5.6-terra, external: []}
tasks:
- id: P3-001
  description: Materialize passage-bound assertions and evaluations with provenance.
  status: completed
  assigned_to: [python-backend-engineer]
  dependencies: [P2-REVIEW]
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-13T21:05:22Z'
  completed: '2026-07-13T21:05:22Z'
  evidence: [artifact:src/research_foundry/services/assertion_materialization.py, test:tests/unit/test_assertion_materialization.py::test_materializes_published_passage, test:tests/unit/test_assertion_materialization.py::test_atomic_materialization_publish_retries_after_interruption, test:tests/unit/test_assertion_materialization.py::test_published_manifest_rejects_path_escape, test:tests/unit/test_assertion_materialization.py::test_durable_binding_failures_do_not_write]
  verified_by: [P3-002]
- id: P3-002
  description: Bounded resumable idempotent assertion replay over P0 fixtures.
  status: completed
  assigned_to: [python-backend-engineer]
  dependencies: [P3-001]
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-13T21:05:22Z'
  completed: '2026-07-13T21:05:22Z'
  evidence: [test:tests/unit/test_assertion_materialization.py::test_phase0_extraction_fixture_backfill_is_bounded_and_immutable, test:tests/unit/test_assertion_materialization.py::test_atomic_materialization_publish_retries_after_interruption]
  verified_by: [P3-003]
- id: P3-003
  description: Add optional assertion lineage to claim ledgers and exports without replacing local IDs.
  status: completed
  assigned_to: [python-backend-engineer]
  dependencies: [P3-001, P3-002]
  acceptance_criteria: [P3-LINEAGE]
  started: '2026-07-13T21:05:22Z'
  completed: '2026-07-13T21:05:22Z'
  evidence: [test:tests/test_pipeline_ingest_extract_claims.py::test_optional_persistent_references_preserve_legacy_claims, test:tests/integration/test_export_round_trip.py::test_build_claims_preserves_legacy_shape_with_optional_assertion_lineage, validation:90 passed/4 skipped; Ruff; focused mypy 3 source files; 27/27 codegen; exact tsc; diff check]
  verified_by: [P3-REVIEW]
- id: P3-REVIEW
  description: Independent Terra High review and milestone gate; this writer must not self-approve.
  status: pending
  assigned_to: [task-completion-validator]
  dependencies: [P3-003]
  acceptance_criteria: [P3-LINEAGE]
parallelization: {batch_1: [P3-001], batch_2: [P3-002], batch_3: [P3-003], batch_4: [P3-REVIEW], critical_path: [P3-001, P3-002, P3-003, P3-REVIEW]}
success_criteria:
- id: AC-P3-LINEAGE
  description: Persistent references remain additive while legacy identities and inference semantics remain intact.
  status: pending
  maps_to: [P3-001, P3-002, P3-003, P3-REVIEW]
notes:
- 'Implementation checkpoint tree: ac8a37ea6065b1e3aa8481c0c7e25e338fea240d.'
- Existing versioned deterministic extraction_card.extracted_facts to claim-mapping/locator contract is accepted for this assertion-only route.
- All reusable assertion, reuse, and canonical-claim flags remain disabled; citation/segmentation charters are deferred; no canonical records exist.
- Independent Terra High review and milestone gate pending; no self approval. Phase 5 is prohibited.
- No schema, export, or frontend source changed because the accepted optional seam already existed.
files_modified: [docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-4-assertion-materialization.md, src/research_foundry/services/assertion_materialization.py, src/research_foundry/services/assertion_registry.py, src/research_foundry/services/claim_mapping.py, tests/unit/test_assertion_materialization.py, tests/test_pipeline_ingest_extract_claims.py, tests/integration/test_export_round_trip.py]
progress: 75
---

# Reusable Assertion Ledger — Phase 4 (P3): Assertion Materialization

P3-001 through P3-003 are complete and await independent Terra High review.
The accepted extraction contract is assertion-only; all flags remain disabled,
draft citation/segmentation charters remain deferred, no canonical records are
created, and Phase 5 is prohibited.
