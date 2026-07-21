---
type: progress
schema_version: 2
doc_type: progress
prd: rights-entity-model
feature_slug: rights-entity-model
phase: 4
phase_id: P4
title: "Phase 4: Capture Emission + Substitutability (C4) — Progress"
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

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

model_usage:
  primary: sonnet
  external: []

tasks:
  - id: P4-1
    title: "Capture-time rights_summary emission"
    description: "Extend ingest_source (source_cards.py) and capture_idea/triage_idea (capture.py) to emit rights_summary at review_status:agent_triage_only in the same call that creates the source card/evidence item. Satisfies AC P4-A. No separate backfill sweep for newly-ingested entities."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-4"]
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended
  - id: P4-2
    title: "Terms snapshotting: content-addressed artifact (H3-flagged)"
    description: "terms_snapshot_sha256 + terms_verified_at, stored under runs/<run_id>/rights/terms_snapshots/, excluded from exported/shipped bundles. 5 enumerated test scenarios (new URL, unchanged re-snapshot, changed re-snapshot+diff, export-exclusion; fetch-failure owned by P4-3)."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-1"]
    estimated_effort: "3 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended
  - id: P4-3
    title: "Structural snapshot-failure recording"
    description: "Snapshot failure (fetch timeout/4xx/5xx/malformed) recorded as a typed failure record (mirroring _IO_ERROR_SENTINEL_PREFIX pattern in verification.py), never as an absent/null field. Consumers must check terms_snapshot_failure before treating terms_snapshot_ref:null as success."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-2"]
    estimated_effort: "1 pt"
    priority: "high"
    assigned_model: sonnet
    model_effort: extended
  - id: P4-4
    title: "Substitutability search trigger (H3-flagged)"
    description: "Blocking triage status (CONTRACT_RESTRICTED/PERMISSION_REQUIRED/PROHIBITED/use-blocking UNKNOWN) triggers substitutability assessment. 5 enumerated test scenarios including no_substitute_found as a positive structured result, not an absent field."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-1"]
    estimated_effort: "2 pts"
    priority: "high"
    assigned_model: sonnet
    model_effort: extended
  - id: P4-5
    title: "Complete rf rights CLI group (inspect, list)"
    description: "Finish rights_app skeleton (from P2-4) with inspect and list subcommands. H7 flag: cli_commands.py is 2,755 lines — reuse P2-4's insertion point, grep-only navigation, <=40 tool uses."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4-1", "P4-4"]
    estimated_effort: "1 pt"
    priority: "medium"
    assigned_model: sonnet
    model_effort: extended

parallelization:
  batch_1: ["P4-1"]
  batch_2: ["P4-2", "P4-4"]
  batch_3: ["P4-3", "P4-5"]
  critical_path: ["P4-1", "P4-2", "P4-3"]
  estimated_total_time: "9 pts (plan bottom-up estimate)"

blockers: []

success_criteria:
  - {id: "P4-SC1", description: "AC P4-A satisfied: capture-time emission reaches both source_card and source_assertion in the same pass", status: pending}
  - {id: "P4-SC2", description: "Snapshot failure is always a structural record, never a bare absence", status: pending}
  - {id: "P4-SC3", description: "no_substitute_found is a positive structured result in the substitutability object", status: pending}
  - {id: "P4-SC4", description: "rf rights CLI group complete (inspect, list, validate)", status: pending}
  - {id: "P4-SC5", description: "Reviewer gate: karen milestone — Mode-D-adjacent capture writeback, explicit verdict required, silence is never a pass", status: pending}

notes: |
  Mode-D-adjacent capture writeback — reviewer gate is karen, NOT task-completion-validator.
  P5 (Governance Gate) depends on P3, not P4, and may run in parallel with this phase
  (different owner-file set: governance.py/verification.py/ADR vs source_cards.py/
  capture.py/cli_commands.py — no file overlap). AC P4-A verified_by: [P4-1, P4-3, P6-2].
---

# rights-entity-model — Phase 4: Capture Emission + Substitutability (C4)

**YAML frontmatter is the source of truth.** Do not duplicate in markdown. Update via CLI only.

---

## Objective

Wire capture-time `rights_summary` emission into `ingest_source`/`capture_idea`/
`triage_idea` (fail-closed by construction, no backfill sweep needed for new ingests),
plus terms-snapshot content-addressing and substitutability search for blocked items.

---

## Orchestration Quick Reference

### Task Delegation Commands

```markdown
# Batch 1
Task("python-backend-engineer", "P4-1: Extend ingest_source (source_cards.py) + capture_idea/triage_idea (capture.py) to emit rights_summary at review_status:agent_triage_only in the same capture call (AC P4-A). Full AC in docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-3-4-capture.md (P4-1 row). Depends on P3-4 (Phase 3) being complete.", model="sonnet")

# Batch 2 (parallel — single message, 2 calls; both depend only on P4-1)
Task("python-backend-engineer", "P4-2 (H3-flagged): Terms snapshotting content-addressed artifact under runs/<run_id>/rights/terms_snapshots/, excluded from export bundles. 5 enumerated test scenarios in phase-3-4-capture.md (P4-2 row).", model="sonnet")

Task("python-backend-engineer", "P4-4 (H3-flagged): Substitutability search trigger for blocking triage statuses. 5 enumerated test scenarios in phase-3-4-capture.md (P4-4 row) — no_substitute_found MUST be a positive structured result.", model="sonnet")

# Batch 3 (parallel — single message, 2 calls)
Task("python-backend-engineer", "P4-3: Structural snapshot-failure recording (typed failure record, mirrors _IO_ERROR_SENTINEL_PREFIX pattern in verification.py). Full AC in phase-3-4-capture.md (P4-3 row).", model="sonnet")

Task("python-backend-engineer", "P4-5: Complete rf rights CLI group (inspect, list) in cli_commands.py. H7 FLAG: 2,755 lines — reuse P2-4's insertion point, grep-only, <=40 tool uses. Full AC in phase-3-4-capture.md (P4-5 row).", model="sonnet")
```

### Reviewer Gate (karen — explicit verdict required)

```markdown
Task("karen", "Assess actual completion state of rights-entity-model Phase 4 (Capture Emission + Substitutability) against docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-3-4-capture.md Phase 4 quality gates. Confirm AC P4-A's resilience clause (rights-triage failure degrades to structural failure record, never blocks ingest) is actually tested — silence is not a pass.", model="sonnet")
```

---

## Implementation Notes

### Known Gotchas

- If rights-triage logic itself fails during capture, the capture pass must still complete — degrade to all-`unknown` + a structural failure record, never a silent absence and never a blocked ingest.
- `terms_snapshots/` must be verified absent from `rf run export` bundle listings — dedicated export-exclusion test required.

---

## Completion Notes

_(Fill in when phase is complete — must record karen's explicit verdict.)_
