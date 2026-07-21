---
type: progress
schema_version: 2
doc_type: progress
prd: rights-entity-model
feature_slug: rights-entity-model
phase: 3
phase_id: P3
title: "Phase 3: Derived Synthesis (C3) — Progress"
status: pending
created: '2026-07-21'
updated: '2026-07-21'
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-3-4-capture.md
commit_refs: []
pr_refs: []
execution_model: batch-parallel
reviewer_gate: karen

overall_progress: 0
completion_estimate: on-track

total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["python-backend-engineer"]
contributors: ["data-layer-expert"]

model_usage:
  primary: sonnet
  external: []

tasks:
  - id: P3-1
    title: "Add conditional synthesis object"
    description: "Add to source_assertion.schema.yaml via JSON Schema if/then, required iff evidence_item_type == derived_synthesis: input_refs[] (minItems:2), method, divergence_notes[], reproduces_source_arrangement, first_party_rights_holder. Test both positive and negative conditional branches explicitly (PRD Risk 3)."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: ["P2-5"]
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended
  - id: P3-2
    title: "Nullable source_edition_id/passage_id conditional"
    description: "Make source_edition_id/passage_id nullable ONLY when evidence_item_type == derived_synthesis; every other evidence_item_type still requires them non-null (regression guard)."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: ["P3-1"]
    estimated_effort: "1 pt"
    priority: "high"
    assigned_model: sonnet
    model_effort: extended
  - id: P3-3
    title: "synthesis.attestation object + schema-level write ceiling"
    description: "Add attestation{attested_by, attested_at, attestation_ref, status:enum[candidate,attested]}. Pair schema enum with a service-layer check in every services/source_cards.py code path constructing a synthesis block, asserting attestation.status is always candidate for agent identities."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-1", "P3-2"]
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended
  - id: P3-4
    title: "Negative test: agent path -> attestation.status=attested unreachable (MANDATORY)"
    description: "Enumerate every code path in services/source_cards.py and services/capture.py that can write a synthesis block; assert none can produce attestation.status:attested under any input. Closes ONE of the two §9.10 write-path halves (P5-2 closes the other, independently — this test alone is not sufficient). Allow-list style: fails loudly on new unenumerated write paths."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-3"]
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended

parallelization:
  batch_1: ["P3-1"]
  batch_2: ["P3-2"]
  batch_3: ["P3-3"]
  batch_4: ["P3-4"]
  critical_path: ["P3-1", "P3-2", "P3-3", "P3-4"]
  estimated_total_time: "7 pts (plan bottom-up estimate; fully serial phase)"

blockers: []

success_criteria:
  - {id: "P3-SC1", description: "synthesis object's if/then conditional validates both the positive (derived_synthesis) and negative (non-synthesis) branch correctly", status: pending}
  - {id: "P3-SC2", description: "derived_synthesis assertions can exist without a third-party source_id/source_edition_id/passage_id", status: pending}
  - {id: "P3-SC3", description: "P3-4's negative test passes and is written as an allow-list (fails loudly on new unenumerated write paths)", status: pending}
  - {id: "P3-SC4", description: "Reviewer gate: karen milestone — Mode-D-adjacent, explicit verdict required, silence is never a pass", status: pending}

notes: |
  Mode-D-adjacent: this phase touches the authorization boundary the entire feature exists
  to protect. Reviewer gate is karen, NOT task-completion-validator — per the project's
  silent-reviewer rule, karen's silence must never be treated as a pass; the phase owner
  must receive an explicit verdict before proceeding to P4/P5.
  §9.10 note: P3-4 closes only ONE of the two enum write-path halves. The boundary is only
  proven once P3-4 AND P5-2 (Phase 5) both pass — do not report this phase as closing the
  full §9.10 gap on its own.
---

# rights-entity-model — Phase 3: Derived Synthesis (C3)

**YAML frontmatter is the source of truth.** Do not duplicate in markdown. Update via CLI only.

---

## Objective

Add first-class `derived_synthesis` provenance to `source_assertion` (conditional schema
fields for multi-input synthesis) with an agent-write ceiling on `attestation.status`,
proven by a mandatory negative test over every agent-reachable write path.

---

## Orchestration Quick Reference

### Task Delegation Commands

```markdown
# Batch 1
Task("data-layer-expert", "P3-1: Add conditional synthesis object to schemas/source_assertion.schema.yaml (if/then, required iff evidence_item_type==derived_synthesis). Full AC in docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-3-4-capture.md (P3-1 row). Test BOTH positive and negative conditional branches explicitly.", model="sonnet")

# Batch 2
Task("data-layer-expert", "P3-2: Make source_edition_id/passage_id nullable ONLY for derived_synthesis assertions; regression-guard the non-synthesis case. Full AC in phase-3-4-capture.md (P3-2 row).", model="sonnet")

# Batch 3
Task("python-backend-engineer", "P3-3: Add synthesis.attestation object + service-layer write ceiling in services/source_cards.py forcing attestation.status=candidate for agent identities. Full AC in phase-3-4-capture.md (P3-3 row).", model="sonnet")

# Batch 4
Task("python-backend-engineer", "P3-4 (MANDATORY, karen-gated): Negative test — enumerate every services/source_cards.py + services/capture.py write path to synthesis.attestation.status and assert none can reach 'attested'. Allow-list style test, fails loudly on new unenumerated paths. Full AC in phase-3-4-capture.md (P3-4 row).", model="sonnet")
```

### Reviewer Gate (karen — explicit verdict required)

```markdown
Task("karen", "Assess actual completion state of rights-entity-model Phase 3 (Derived Synthesis) against docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-3-4-capture.md Phase 3 quality gates. Confirm P3-4's negative test is genuinely exhaustive (allow-list, not best-effort scan) before signing off — silence is not a pass.", model="sonnet")
```

---

## Implementation Notes

### Known Gotchas

- P3-4 is an **independent** test from P5-2 (different phase, different fields/paths) — do not collapse or treat as redundant; both must pass to close §9.10.
- The conditional `if/then` in P3-1 must not misfire on non-synthesis assertions (PRD Risk 3: "under-tested conditional silently permits malformed record").

---

## Completion Notes

_(Fill in when phase is complete — must record karen's explicit verdict, not just task completion.)_
