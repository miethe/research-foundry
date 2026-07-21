---
type: progress
schema_version: 2
doc_type: progress
prd: rights-entity-model
feature_slug: rights-entity-model
phase: 1
phase_id: P1
title: "Phase 1: Evidence Taxonomy (C2) — Progress"
status: pending
created: '2026-07-21'
updated: '2026-07-21'
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md
commit_refs: []
pr_refs: []
execution_model: batch-parallel
reviewer_gate: task-completion-validator

overall_progress: 0
completion_estimate: on-track

total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["data-layer-expert"]
contributors: ["python-backend-engineer"]

model_usage:
  primary: sonnet
  external: []

tasks:
  - id: P1-1
    title: "Add evidence_item_type to source_assertion.schema.yaml"
    description: "Required enum (observed_finding|reference_interval_value|equation_or_method|guideline_recommendation|instrument_or_questionnaire|bibliographic_metadata|derived_synthesis|other) inside a new extensions.evidence_taxonomy sibling block — never nested under rights_extension (§9.1)."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: ["P0-5"]
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: adaptive
  - id: P1-2
    title: "Add judgment_basis to extensions.evidence_taxonomy"
    description: "Required enum (measured|derived_from_measured|expert_judgment|mixed|unassessed), independent axis, default unassessed. Domain-general naming per OQ-RF-2."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: ["P1-1"]
    estimated_effort: "1.5 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: adaptive
  - id: P1-3
    title: "No-derivation static guard"
    description: "Automated static test (AST/grep-based) asserting no function derives evidence_item_type from judgment_basis or vice versa, or from any component_type-shaped field. Three-axes invariant (FR-8)."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-1", "P1-2"]
    estimated_effort: "1.5 pts"
    priority: "high"
    assigned_model: sonnet
    model_effort: adaptive
  - id: P1-4
    title: "other-extensibility test (OQ-RF-2)"
    description: "Test proving evidence_item_type: other validates; schema doc-comment states the extensibility contract (domain-extensible, not a closed clinical list)."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: ["P1-1"]
    estimated_effort: "1 pt"
    priority: "medium"
    assigned_model: sonnet
    model_effort: adaptive

parallelization:
  batch_1: ["P1-1"]
  batch_2: ["P1-2", "P1-4"]
  batch_3: ["P1-3"]
  critical_path: ["P1-1", "P1-2", "P1-3"]
  estimated_total_time: "6 pts (plan bottom-up estimate)"

blockers: []

success_criteria:
  - {id: "P1-SC1", description: "evidence_item_type and judgment_basis are independent, required fields with correct defaults", status: pending}
  - {id: "P1-SC2", description: "No-derivation static test passes", status: pending}
  - {id: "P1-SC3", description: "other-extensibility test passes", status: pending}
  - {id: "P1-SC4", description: "Reviewer gate: task-completion-validator sign-off (explicit verdict required)", status: pending}

notes: |
  Sequenced after P0 per decisions-block risk conservatism (shared evidence-entity file),
  not a direct field dependency. evidence_item_type + judgment_basis live in
  extensions.evidence_taxonomy — a sibling block, NOT inside rights_extension (§9.1,
  locked). Reviewer gate is task-completion-validator, not karen.
---

# rights-entity-model — Phase 1: Evidence Taxonomy (C2)

**YAML frontmatter is the source of truth.** Do not duplicate in markdown. Update via CLI only.

---

## Objective

Add an evidence-quality taxonomy (`evidence_item_type`, `judgment_basis`) to
`source_assertion.schema.yaml` as an axis fully independent of rights (§9.1) — the base
axis a future domain (e.g. Evidence-Foundry) specializes rather than replaces (OQ-RF-2).

---

## Orchestration Quick Reference

### Task Delegation Commands

```markdown
# Batch 1
Task("data-layer-expert", "P1-1: Add extensions.evidence_taxonomy.evidence_item_type to schemas/source_assertion.schema.yaml per docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md (P1-1 row). Depends on P0-5 (registry wiring) being complete.", model="sonnet")

# Batch 2 (parallel — single message, 2 calls; both depend only on P1-1)
Task("data-layer-expert", "P1-2: Add judgment_basis to the same extensions.evidence_taxonomy block. Full AC in phase-0-2-schema.md (P1-2 row).", model="sonnet")

Task("data-layer-expert", "P1-4: other-extensibility test for evidence_item_type (OQ-RF-2). Full AC in phase-0-2-schema.md (P1-4 row).", model="sonnet")

# Batch 3 (after P1-2 lands)
Task("python-backend-engineer", "P1-3: No-derivation static guard — AST/grep test asserting no function derives evidence_item_type <-> judgment_basis <-> component_type. Full AC in phase-0-2-schema.md (P1-3 row).", model="sonnet")
```

---

## Implementation Notes

### Known Gotchas

- The `other`-extensibility test (P1-4) is about documenting an open-ended domain axis, not adding a catch-all default.
- R-P2 implicit AC on P1-1/P1-2: absence of `evidence_item_type`/`judgment_basis` on pre-existing instances must resolve to `other`/`unassessed`, never crash or silently coerce to a specific member.

---

## Completion Notes

_(Fill in when phase is complete.)_
