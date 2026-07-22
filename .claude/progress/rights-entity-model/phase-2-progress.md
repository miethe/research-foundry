---
type: progress
schema_version: 2
doc_type: progress
prd: rights-entity-model
feature_slug: rights-entity-model
phase: 2
phase_id: P2
title: "Phase 2: Rights Summary Mirror + Validator (C1) \u2014 Progress"
status: completed
created: '2026-07-21'
updated: '2026-07-21'
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
phase_plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md
commit_refs:
- b017b53
pr_refs: []
execution_model: batch-parallel
reviewer_gate: task-completion-validator
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
owners:
- data-layer-expert
- python-backend-engineer
contributors: []
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P2-1
  title: Add rights_summary to source_card.schema.yaml
  description: AC P2-A attach point 1. All fields default unknown/null; mirror_is_authoritative
    const false; rights_record_ids[] required non-empty whenever any restriction/status
    field is non-unknown.
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - P1-4
  estimated_effort: 2 pts
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-21T19:21:20Z'
  completed: '2026-07-21T19:25:54Z'
  evidence:
  - test: tests/test_schema_validation.py -k source_card
  verified_by:
  - P2-2
- id: P2-2
  title: Add rights_summary to source_assertion.schema.yaml
  description: "AC P2-A attach point 2 \u2014 identical field shape to P2-1, applied\
    \ to the evidence-item-level entity. Test confirms the two schemas' rights_summary\
    \ field lists are identical."
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - P2-1
  estimated_effort: 2 pts
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-21T19:25:55Z'
  completed: '2026-07-21T19:29:55Z'
  evidence:
  - test: tests/test_schema_validation.py -k source_assertion
  verified_by:
  - P2-3
- id: P2-3
  title: check_rights_divergence validator (H3-flagged)
  description: Build services/rights_validation.py::check_rights_divergence(paths,
    *, as_of, ...). Must accept --as-of as required param; must NEVER call datetime.now()/time.time()/date.today().
    5 enumerated test scenarios required (link-before-assert, divergence, needs-backfill,
    staleness, reproducibility).
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-1
  - P2-2
  estimated_effort: 3 pts
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-21T19:29:56Z'
  completed: '2026-07-21T19:37:01Z'
  evidence:
  - test: tests/test_rights_validation.py
  verified_by:
  - P2-4
- id: P2-4
  title: rf rights validate --as-of CLI + rights_app skeleton
  description: "Wire validator as `rf rights validate --as-of YYYY-MM-DD` (required,\
    \ no wall-clock default). Scaffold rights_app Typer sub-app (inspect/list/validate).\
    \ H7 flag: cli_commands.py is 2,755 lines \u2014 grep-only navigation, <=40 tool\
    \ uses, STOP-and-report-partial if exhausted."
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-3
  estimated_effort: 1 pt
  priority: high
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-21T19:37:01Z'
  completed: '2026-07-21T19:48:29Z'
  evidence:
  - test: tests/test_cli_rights.py
  verified_by:
  - P2-5
- id: P2-5
  title: Backfill migration
  description: Existing source_card/source_assertion instances without rights_summary
    get an all-unknown fail-closed summary (valid by construction). Run existing corpus
    through P2-3's validator as phase exit gate.
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P2-3
  - P2-4
  estimated_effort: 1 pt
  priority: critical
  assigned_model: sonnet
  model_effort: extended
  started: '2026-07-21T19:48:32Z'
  completed: '2026-07-21T19:54:46Z'
  evidence:
  - test: tests/test_rights_backfill.py
  verified_by:
  - task-completion-validator
parallelization:
  batch_1:
  - P2-1
  batch_2:
  - P2-2
  batch_3:
  - P2-3
  batch_4:
  - P2-4
  batch_5:
  - P2-5
  critical_path:
  - P2-1
  - P2-2
  - P2-3
  - P2-4
  - P2-5
  estimated_total_time: 9 pts (plan bottom-up estimate; fully serial phase)
blockers: []
success_criteria:
- id: P2-SC1
  description: rights_summary attaches identically to both source_card and source_assertion
    (AC P2-A satisfied)
  status: pending
- id: P2-SC2
  description: check_rights_divergence is time-parameterized and never reads wall-clock
    time (reproducibility test passes)
  status: pending
- id: P2-SC3
  description: Backfill migration brings the existing corpus to 0 divergences
  status: pending
- id: P2-SC4
  description: rf rights validate --as-of rejects invocation without the flag
  status: pending
- id: P2-SC5
  description: 'Reviewer gate: task-completion-validator sign-off (explicit verdict
    required)'
  status: pending
notes: "H3 flag: P2-3 is the algorithmic core of this phase (time-parameterized, never-wall-clock\n\
  divergence validator) \u2014 5 enumerated test scenarios required, see phase file.\n\
  H7 flag: P2-4 touches cli_commands.py (2,755 lines) \u2014 apply the >=2x dispatch\
  \ multiplier\nand anti-blow guardrail (grep-only navigation, <=40 tool uses).\n\
  AC P2-A (multi-surface propagation) verified_by: [P2-1, P2-2, P2-5, P6-1].\n"
progress: 100
---

# rights-entity-model — Phase 2: Rights Summary Mirror + Validator (C1)

**YAML frontmatter is the source of truth.** Do not duplicate in markdown. Update via CLI only.

---

## Objective

Add a denormalized `rights_summary` mirror (mirror_is_authoritative const false) to both
`source_card` and `source_assertion`, plus a time-parameterized, reproducible divergence
validator (`check_rights_divergence`) and its `rf rights validate` CLI surface.

---

## Orchestration Quick Reference

### Task Delegation Commands

```markdown
# Batch 1
Task("data-layer-expert", "P2-1: Add rights_summary to schemas/source_card.schema.yaml (AC P2-A attach point 1) per docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md (P2-1 row).", model="sonnet")

# Batch 2
Task("data-layer-expert", "P2-2: Add rights_summary to schemas/source_assertion.schema.yaml (AC P2-A attach point 2, identical shape to P2-1). Full AC in phase-0-2-schema.md (P2-2 row).", model="sonnet")

# Batch 3
Task("python-backend-engineer", "P2-3: Build src/research_foundry/services/rights_validation.py::check_rights_divergence (H3-flagged, --as-of required, never wall-clock). 5 enumerated scenarios in phase-0-2-schema.md (P2-3 row) — implement all 5 as tests.", model="sonnet")

# Batch 4
Task("python-backend-engineer", "P2-4: Wire `rf rights validate --as-of` CLI + rights_app skeleton in cli_commands.py. H7 FLAG: file is 2,755 lines — grep -n 'assertion_app' for insertion point, do not read whole file, budget <=40 tool uses. Full AC in phase-0-2-schema.md (P2-4 row).", model="sonnet")

# Batch 5
Task("python-backend-engineer", "P2-5: Backfill migration — all-unknown rights_summary for pre-existing instances; run corpus through P2-3's validator as exit gate. Full AC in phase-0-2-schema.md (P2-5 row).", model="sonnet")
```

---

## Implementation Notes

### Known Gotchas

- `check_rights_divergence` must NEVER call `datetime.now()`/`time.time()`/`date.today()` — a dedicated monkeypatch test asserts this.
- A genuinely absent `rights_summary` on an unmigrated legacy instance is a distinct non-fatal "needs backfill" state, not a divergence failure — do not conflate the two.
- `cli_commands.py` is 2,755 lines (H7 threshold exceeded) — P2-4 carries the >=2x dispatch multiplier; grep-only navigation mandated.

---

## Completion Notes

_(Fill in when phase is complete.)_
