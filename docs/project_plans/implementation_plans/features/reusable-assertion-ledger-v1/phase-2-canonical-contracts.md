---
schema_version: 2
doc_type: phase_plan
title: "Phase 2 (P1): Canonical Contracts"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 2
phase_id: P1
phase_title: Canonical Contracts
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - P0 research gate in Phase 1 passed.
  - Identity, qualifier, and lifecycle inputs are enumerable.
exit_criteria:
  - Versioned schemas, identity rules, state machines, and compatibility mappings validate.
  - Legacy claim ledgers and run exports round-trip unchanged.
related_documents:
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
  - docs/dev/architecture/rf-run-export-schema.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
integration_owner: backend-architect
ui_touched: false
target_surfaces: []
seam_tasks: [P1-003]
owner: backend-architect
contributors: [data-layer-expert, python-backend-engineer]
priority: high
risk_level: high
files_affected:
  - schemas/source_assertion.schema.yaml
  - schemas/source_edition.schema.yaml
  - schemas/passage.schema.yaml
  - schemas/assertion_evaluation.schema.yaml
  - schemas/assertion_lifecycle_event.schema.yaml
  - schemas/canonical_claim.schema.yaml
  - schemas/inference_record.schema.yaml
  - docs/dev/architecture/assertion-ledger-contract.md
  - tests/test_schema_validation.py
---

# Phase 2 (P1): Canonical Contracts

**Effort:** 8 points
**Dependencies:** P0 approved.

## Outcome

Freeze additive, versioned contracts before storage or APIs are implemented. Public identifiers remain opaque; content hashes stay access-controlled.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P1-001 | Domain schemas | Define source edition, passage, assertion, evaluation, lifecycle, inference, and optional canonical-claim schemas with qualifier preservation. | 3 pts | data-layer-expert, backend-architect | sonnet | extended | P0 |
| P1-002 | Identity and lifecycle contract | Record normalization, fingerprints, versions, supersession, invalidation, deletion tombstones, inference separation, and merge/split reversal. | 3 pts | backend-architect, data-layer-expert | sonnet | extended | P1-001 |
| P1-003 | Compatibility/codegen seam [H6] | Map optional persistent references into claim-ledger/export contracts; add legacy/new fixtures and schema-generation checks. | 2 pts | python-backend-engineer, backend-architect | sonnet | adaptive | P1-001, P1-002 |

## Structured acceptance

#### AC P1-IDENTITY: Schema preserves immutable evidence and mutable lifecycle
- target_surfaces:
  - `schemas/source_edition.schema.yaml`
  - `schemas/passage.schema.yaml`
  - `schemas/source_assertion.schema.yaml`
  - `schemas/assertion_lifecycle_event.schema.yaml`
  - `schemas/canonical_claim.schema.yaml`
  - `schemas/inference_record.schema.yaml`
- propagation_contract: Identity SPIKE rules become schema constraints and documented generators; lifecycle and canonical grouping reference immutable assertions by version.
- resilience: Unknown optional qualifiers remain preserved in an extension map; absent canonical-claim fields mean assertion-only mode; legacy artifacts need no synthetic persistent IDs.
- visual_evidence_required: false
- verified_by: [P1-003]

## File ownership

- `data-layer-expert`: new ledger schemas and validation fixtures.
- `backend-architect`: identity/lifecycle architecture contract.
- `python-backend-engineer`: existing-schema compatibility seam and codegen fixture.
- `P1-003` serializes overlapping schema/export changes and signs off cross-owner propagation.

## Quality and review gates

- [ ] Same bytes and contract version produce deterministic identities; changed material bytes do not.
- [ ] Source assertion cannot be mutated by a canonical-claim operation.
- [ ] Inference cannot validate as a source assertion.
- [ ] Qualifier fixtures round-trip without silent omission.
- [ ] Legacy ledger/export fixtures remain valid.
- [ ] `task-completion-validator` passes P1.

## Validation

- Run schema-validation and export round-trip tests.
- Validate example objects against every new schema version.
- Regenerate types in check mode and confirm no uncommitted drift.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
