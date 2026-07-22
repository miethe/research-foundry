---
title: "Phase 2: Pediatric Evidence-Card Schema + Hard-Gate"
schema_version: 2
doc_type: phase_plan
status: draft
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: rfup-external-routing
feature_version: v1
phase: 2
phase_title: "Pediatric evidence-card schema + hard-gate"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
entry_criteria:
  - "Phase 1 not required as a precondition (parallel wave) but schema field list from scope-brief is available"
exit_criteria:
  - "pediatric_cds schema hard-gates 100% of a >=5-case red-team fixture set"
  - "0 false positives against the 7 existing verified pediatric-CDS bundles"
  - "task-completion-validator pass"
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
spike_ref: null
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces: []
seam_tasks: []
owner: null
contributors: []
priority: high
risk_level: high
category: enhancements
tags: [phase-plan, schema, hard-gate, pediatric-cds]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/schemas/pediatric_cds.schema.json
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/verification.py
---

# Phase 2: Pediatric Evidence-Card Schema + Hard-Gate

**Parent Plan**: [rfup-external-routing-v1.md](../rfup-external-routing-v1.md)
**Wave**: 2 (solo — critical-path root; both P3 and P4 depend on this phase)
**Effort**: 5 pts
**Dependencies**: None
**Agents**: python-backend-engineer (primary, sonnet, extended), data-layer-expert (secondary — schema modeling)

## Phase Overview

Today, `pediatric_cds` blocks pass through `rf verify` with `additionalProperties: true` — i.e., no formal schema exists anywhere in the codebase (confirmed by state-audit: zero hits for a `pediatric_cds` schema artifact). This phase authors a formal JSON Schema for the block's 9 top-level sections (`source_status`, `study`, `applicability`, `laboratory`, `implementable_statement`, `diagnostic_accuracy`, `safety`, `conflict`, `lifecycle`) and wires it as a hard-gate check into `rf verify`.

**Seam boundary reminder**: `rf` validates *structural completeness* of whatever `pediatric_cds` block is supplied. The block's clinical semantics (age partitions, lab/method/analyzer fields, threshold portability, lifecycle/review-by content) are authored and owned by pediatric-anemia-site — this phase does not originate or interpret that content, only enforces that required fields/types are present.

### Goals

- Replace `additionalProperties: true` with a required-field/type-enforcing JSON Schema.
- Hard-gate at verify-time (decision: primarily `rf verify`, per parent plan decisions list — ingest-time is a Should, not a Must).
- Validate against both a red-team malformed-block fixture set (must reject 100%) and the 7 existing verified pediatric-CDS bundles (must accept 100%, 0 false positives).

## Task Breakdown

| Task ID | Task Name | Description | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------|-------------|-------|--------|--------------|
| P2-001 | Author `pediatric_cds` JSON Schema | Formal schema for all 9 top-level sections with required-field/type enforcement; stamp a schema version consistent with RFUP-4's existing machine-contract versioning convention. | 2 pts | python-backend-engineer, data-layer-expert | sonnet | extended | None |
| P2-002 | Wire hard-gate into `rf verify` | Add a new check in `verification.py` that loads the schema and validates any `pediatric_cds` block found on a source card, following the existing `resolve_exact_passage_mode`/`exact_passage_present` fail-closed idiom (`add(..., "fail", ...)` + `unsupported[]` append on invalid/incomplete). | 2 pts | python-backend-engineer | sonnet | extended | P2-001 |
| P2-003 | Fixtures: red-team set + 7-bundle regression | Author ≥5 malformed `pediatric_cds` fixture cases (missing required field, wrong type, empty required object, extra-but-otherwise-valid, nested-field violation) and run the schema validator against the 7 existing verified pediatric-CDS bundles (0 false positives required). | 1 pt | python-backend-engineer | sonnet | adaptive | P2-002 |

## Detailed Task Specifications

### Task P2-001: Author `pediatric_cds` JSON Schema

**Estimate**: 2 pts · **Model**: sonnet · **Effort**: extended · **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-P2-1: Schema declares required fields for all 9 top-level sections (`source_status`, `study`, `applicability`, `laboratory`, `implementable_statement`, `diagnostic_accuracy`, `safety`, `conflict`, `lifecycle`) per the scope-brief field list.
- [ ] AC-P2-2: `additionalProperties` is no longer unconditionally `true` at the top level of the `pediatric_cds` block (structural completeness enforced, not clinical semantics — do not encode age-partition/lab-method/threshold-portability business rules into the schema itself; that content is authored/owned by pediatric-anemia-site).
- [ ] AC-P2-3: A schema-version field/stamp is present and consistent with RFUP-4's existing machine-contract versioning convention (R6 — schema-version drift risk).
- [ ] AC-P2-4 (**R-P2 implicit AC**): When a `pediatric_cds` block is entirely absent from a source card, the schema check does not itself fail the card (absence of the block is a pre-existing, separately-handled state — this schema only validates blocks that ARE present); when a block IS present but a required sub-field is missing, the check fails closed with a distinguishable reason code naming the missing field/path.

**Files Involved**:
- `src/research_foundry/schemas/pediatric_cds.schema.json` (new) — the JSON Schema artifact.

### Task P2-002: Wire hard-gate into `rf verify`

**Estimate**: 2 pts · **Model**: sonnet · **Effort**: extended · **Dependencies**: P2-001

**Acceptance Criteria**:
- [ ] AC-P2-5: New check follows the existing `resolve_exact_passage_mode`/`exact_passage_present` fail-closed convention: invalid schema config raises `RFError`; invalid/incomplete `pediatric_cds` blocks emit `add(..., "fail", ...)` and are appended to `unsupported[]` (the same list that blocks publish).
- [ ] AC-P2-6: The check introduces zero new live network I/O (validates already-loaded in-memory structures only).
- [ ] AC-P2-7: Failure emits a structured `rf verify` finding with a distinguishable reason code (e.g. `pediatric_cds_schema_invalid`) consistent with existing emission conventions in `verification.py`.

**Files Involved**:
- `src/research_foundry/services/verification.py` — new check function + wiring into the verify pipeline.
- `src/research_foundry/services/source_cards.py` — only if the block accessor needs a helper (read-check first; avoid edits if `_index_source_cards` already exposes what's needed).

### Task P2-003: Fixtures — red-team set + 7-bundle regression

**Estimate**: 1 pt · **Model**: sonnet · **Effort**: adaptive · **Dependencies**: P2-002

**Acceptance Criteria**:
- [ ] AC-P2-8: ≥5 red-team malformed-block fixtures exist, each targeting a distinct violation class (missing required top-level section, wrong type on a required field, empty required object, unexpected additional property at a section boundary that IS schema-constrained, nested-field required-property violation).
- [ ] AC-P2-9: 100% of the red-team fixture set fails schema validation.
- [ ] AC-P2-10: 0 false positives when the schema validator runs against the 7 existing verified pediatric-CDS bundles (committed `aaa9d92`, per project memory) — any bundle-breaking field is treated as a schema-authoring bug in this task, not a downstream bug (PRD Risks table).

**Files Involved**:
- Test fixtures directory (e.g. `tests/fixtures/pediatric_cds/` — new; exact layout at task-executor's discretion, following any existing fixture convention in the test suite).
- `./.venv/bin/python -m pytest` test file exercising both fixture sets.

## Quality Gates

This phase is complete when:

- [ ] **Functional**: Schema hard-gates 100% of red-team fixtures; 0 false positives against the 7 verified bundles.
- [ ] **Testing**: `./.venv/bin/python -m pytest` passes for all new/changed test files (never bare `pytest`, per project convention).
- [ ] **Security**: No new live network I/O introduced.
- [ ] **Documentation**: Schema-version stamp documented inline; new schema file has a header comment stating the seam-boundary scope (structural completeness only, not clinical semantics).
- [ ] **Architecture**: Fail-closed convention matches `resolve_exact_passage_mode`/`exact_passage_present` exactly (no new enforcement idiom introduced).
- [ ] **Karen milestone deferred**: no standalone `karen` pass at the end of this phase — per the parent plan's Reviewer Gates override, the clinical-gate cluster's `karen` review is consolidated to after Wave 3 (P3+P4+SEAM-001), not here.

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Schema stricter than what pediatric-anemia-site currently emits, breaking existing verified bundles | High | AC-P2-10 (0-false-positive gate against all 7 bundles) is a hard exit criterion, not a nice-to-have. |
| Schema-version/machine-contract drift vs. RFUP-4 | Low | AC-P2-3; reuse existing stamping pattern verbatim. |

## Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0 · **Last Updated**: 2026-07-22

[Return to Parent Plan](../rfup-external-routing-v1.md)
