---
type: progress
schema_version: 2
doc_type: progress
prd: reusable-assertion-ledger
feature_slug: reusable-assertion-ledger
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-2-canonical-contracts.md
execution_model: sequential
phase: 2
title: P1 Canonical Contracts
status: complete
created: '2026-07-13T15:08:00Z'
started: '2026-07-13T15:08:00Z'
completed: '2026-07-13T20:45:14Z'
updated: '2026-07-13T20:45:14Z'
commit_refs:
- 7fec855e8f5221d7af9076cf82e7e6371e59821f
- 24277e8226817ca1a6a977bf17b51dd7d2ca787e
pr_refs: []
overall_progress: 100
completion_estimate: complete
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
owners:
- p1-canonical-contracts-implementation-owner
contributors:
- task-completion-validator
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P1-001
  description: Define versioned source edition, passage, source assertion, evaluation,
    lifecycle event, inference, and optional canonical-claim schemas with qualifier preservation.
  status: completed
  assigned_to:
  - p1-canonical-contracts-implementation-owner
  dependencies:
  - P0-GATES
  estimated_effort: 3 pts
  priority: high
  assigned_model: sonnet
  model_effort: extended
  acceptance_criteria:
  - P1-IDENTITY
  started: '2026-07-13T15:08:00Z'
  completed: '2026-07-13T15:41:00Z'
  evidence:
  - artifact: schemas/source_edition.schema.yaml
  - artifact: schemas/passage.schema.yaml
  - artifact: schemas/source_assertion.schema.yaml
  - artifact: schemas/assertion_evaluation.schema.yaml
  - artifact: schemas/assertion_lifecycle_event.schema.yaml
  - artifact: schemas/canonical_claim.schema.yaml
  - artifact: schemas/inference_record.schema.yaml
  - test: tests/test_reusable_assertion_ledger_phase1.py
  verified_by:
  - P1-002
- id: P1-002
  description: Document identity normalization, fingerprints, versions, supersession,
    invalidation, tombstones, inference separation, and merge/split reversal.
  status: completed
  assigned_to:
  - p1-canonical-contracts-implementation-owner
  dependencies:
  - P1-001
  estimated_effort: 3 pts
  priority: high
  assigned_model: sonnet
  model_effort: extended
  acceptance_criteria:
  - P1-IDENTITY
  started: '2026-07-13T15:41:00Z'
  completed: '2026-07-13T15:48:00Z'
  evidence:
  - artifact: docs/dev/architecture/assertion-ledger-contract.md
  - artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
  - artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
  - test: tests/test_reusable_assertion_ledger_phase1.py
  verified_by:
  - P1-003
- id: P1-003
  description: Map optional persistent references into claim-ledger and export contracts;
    validate legacy and linked fixtures plus strict export schema/type seams.
  status: completed
  assigned_to:
  - p1-canonical-contracts-implementation-owner
  dependencies:
  - P1-001
  - P1-002
  estimated_effort: 2 pts
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  acceptance_criteria:
  - P1-IDENTITY
  started: '2026-07-13T15:48:00Z'
  completed: '2026-07-13T15:55:18Z'
  evidence:
  - artifact: schemas/claim_ledger.schema.yaml
  - artifact: docs/dev/architecture/rf-run-export-schema.json
  - artifact: docs/dev/architecture/rf-run-export-schema.md
  - artifact: frontend/runs-viewer/src/types/rf/run-export.ts
  - test: tests/test_schema_validation.py
  - test: tests/unit/test_export_service.py
  - test: tests/integration/test_export_round_trip.py
  verified_by:
  - P1-REVIEW
- id: P1-REVIEW
  description: Independent task-completion-validator review of P1-001 through P1-003
    and AC P1-IDENTITY; this writer must not self-approve phase completion.
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies:
  - P1-003
  estimated_effort: review gate
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  acceptance_criteria:
  - P1-IDENTITY
  started: '2026-07-13T17:14:52Z'
  completed: '2026-07-13T20:45:14Z'
  evidence:
  - review: Independent task-completion-validator REQUEST CHANGES; thread 019f5d31-9ec7-74a2-b575-3f2e22792cc4; scope commit 7fec855e8f5221d7af9076cf82e7e6371e59821f; tree f5e34e065f9fb3bbeb55d5d1caadb33626f9baea; corrected-tracker recertification pending
  - review: Independent task-completion-validator APPROVE; thread 019f5d31-9ec7-74a2-b575-3f2e22792cc4; reviewed implementation commit 7fec855e8f5221d7af9076cf82e7e6371e59821f; tree f5e34e065f9fb3bbeb55d5d1caadb33626f9baea; correction checkpoint 24277e8226817ca1a6a977bf17b51dd7d2ca787e
  - test: 'Focused P1 suite passed: 199 tests'
  verified_by:
  - task-completion-validator
parallelization:
  batch_1:
  - P1-001
  batch_2:
  - P1-002
  batch_3:
  - P1-003
  batch_4:
  - P1-REVIEW
  critical_path:
  - P1-001
  - P1-002
  - P1-003
  - P1-REVIEW
  estimated_total_time: 8 pts plus independent review
blockers:
- id: P1-BLOCKER-001
  title: Feature enablement remains prohibited by the conditional P0 evidence boundary
  severity: high
  blocking:
  - RF_ASSERTION_LEDGER_ENABLED
  - RF_ASSERTION_REUSE_ENABLED
  - RF_CANONICAL_CLAIMS_ENABLED
  resolution: Preserve assertion-only contracts and obtain the named corpus/upstream gates before any enablement decision.
success_criteria:
- id: AC-P1-IDENTITY
  description: Immutable evidence identity, mutable lifecycle, inference separation,
    qualifier preservation, optional canonical grouping, and legacy compatibility validate.
  status: completed
  maps_to:
  - P1-001
  - P1-002
  - P1-003
  - P1-REVIEW
completion_evidence:
- review: Independent task-completion-validator APPROVE; thread 019f5d31-9ec7-74a2-b575-3f2e22792cc4; reviewed implementation commit 7fec855e8f5221d7af9076cf82e7e6371e59821f; tree f5e34e065f9fb3bbeb55d5d1caadb33626f9baea; correction checkpoint 24277e8226817ca1a6a977bf17b51dd7d2ca787e
- validation: Ruff, mypy, codegen drift 27/27, exact TypeScript, 33-schema meta-validation, artifact validation, phase gate, AC coverage, and git diff check passed
- protected_assets_fingerprint: a5ec9d56934724d037aac51dc1a715d0e3c9286d71d8cb61c96d6d7fca620e77
verified_by:
- task-completion-validator
notes:
- 'Residual closeout: rerun codegen:check and mypy in the dependency-complete writer/integration environment.'
files_modified:
- schemas/source_edition.schema.yaml
- schemas/passage.schema.yaml
- schemas/source_assertion.schema.yaml
- schemas/assertion_evaluation.schema.yaml
- schemas/assertion_lifecycle_event.schema.yaml
- schemas/canonical_claim.schema.yaml
- schemas/inference_record.schema.yaml
- schemas/claim_ledger.schema.yaml
- docs/dev/architecture/assertion-ledger-contract.md
- docs/dev/architecture/rf-run-export-schema.json
- docs/dev/architecture/rf-run-export-schema.md
- src/research_foundry/assertion_identity.py
- src/research_foundry/schemas.py
- src/research_foundry/services/export_service.py
- frontend/runs-viewer/codegen/generate-types.mjs
- frontend/runs-viewer/package.json
- frontend/runs-viewer/src/types/rf/run-export.ts
- frontend/runs-viewer/src/types/rf/index.ts
- frontend/runs-viewer/src/types/rf/generated.ts
- frontend/runs-viewer/src/types/rf/claim_ledger.generated.ts
- tests/test_schema_validation.py
- tests/test_reusable_assertion_ledger_phase1.py
- tests/unit/test_export_service.py
progress: 75
---

# Reusable Assertion Ledger — Phase 2 (P1): Canonical Contracts

Independent review approved P1-001 through P1-003 and the corrected tracker;
`P1-REVIEW` is complete and the phase is marked complete.

## Implementation decisions

- New durable schemas are versioned `1.0`. Immutable edition, passage, and
  assertion records use content-addressed identities; mutable concepts use
  opaque IDs and versions.
- `qualifier_extensions` retains unknown optional qualifiers as identity-bearing
  data. Inference is a distinct contract and cannot validate as source evidence.
- Canonical claims remain optional and reversible. No feature flag was enabled.
- Source assertion identity is executable: canonical payloads bind the text
  digest, fingerprint, and `ast_` ID; object-key ordering does not change it.
- Invalidating lifecycle transitions require a synchronous `block_reuse` action;
  split/rollback claims require provenance plus versioned replacement/results.
- Export schema `1.5` adds optional `claims[].persistent_references`; legacy
  ledgers omit the block and exports never synthesize persistent IDs.
- Existing AOS correlation UUID and native alias semantics remain unchanged.

## Validation record

| Command | Result |
|---|---|
| `./.venv/bin/python -m pytest tests/test_schema_validation.py tests/test_reusable_assertion_ledger_phase1.py tests/unit/test_export_service.py tests/integration/test_export_round_trip.py -q` | Passed: 199 tests; existing FastAPI/TestClient deprecation warnings only. |
| `./.venv/bin/python -m ruff check schemas src/research_foundry/assertion_identity.py src/research_foundry/schemas.py src/research_foundry/services/export_service.py tests/test_schema_validation.py tests/test_reusable_assertion_ledger_phase1.py tests/unit/test_export_service.py` | Passed. |
| `./.venv/bin/python -m mypy --ignore-missing-imports src/research_foundry/assertion_identity.py src/research_foundry/schemas.py src/research_foundry/services/export_service.py tests/test_schema_validation.py tests/test_reusable_assertion_ledger_phase1.py` | Passed: no issues in 5 source files. |
| `./.venv/bin/python -c '<Draft 2020-12/Draft 7 validator loop>'` over `schemas/*.schema.yaml` and `rf-run-export-schema.json` | Passed: 33 schemas. |
| `CI=1 pnpm --dir frontend/runs-viewer install --frozen-lockfile --force` | Passed: recreated ignored local `node_modules` from the existing lockfile; `@clerk/clerk-react` 5.61.3 is installed with no manifest or lockfile drift. |
| `./frontend/runs-viewer/node_modules/.bin/tsc --noEmit -p frontend/runs-viewer/tsconfig.app.json` | Passed. |
| `pnpm --dir frontend/runs-viewer run codegen` and `pnpm --dir frontend/runs-viewer run codegen:check` | Passed: generated and verified 27 viewer-consumed schemas, including all seven P1 schemas. |
| Supersession regression correction: versioned `replaces[]` schema fixture | Passed: a valid `superseded` canonical claim accepts `canonical_claim_id` plus `canonical_claim_version`. |
| Artifact validation, `validate-phase-completion.py`, and `ac-coverage-report.py` | Passed; phase is complete and `P1-REVIEW` is independently approved. |

## Review closeout

Independent review recorded `APPROVE` for correction checkpoint
`24277e8226817ca1a6a977bf17b51dd7d2ca787e` and implementation commit
`7fec855e8f5221d7af9076cf82e7e6371e59821f` at tree
`f5e34e065f9fb3bbeb55d5d1caadb33626f9baea`. Legacy semantics and the absence
of feature-enablement or deployment authority remain unchanged.

Residual closeout: rerun `codegen:check` and `mypy` later in the
dependency-complete writer/integration environment.
