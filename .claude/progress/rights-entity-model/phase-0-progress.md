---
type: progress
schema_version: 2
doc_type: progress
prd: rights-entity-model
feature_slug: rights-entity-model
phase: 0
phase_id: P0
title: "Phase 0: Rights Substrate — Progress"
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

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["data-layer-expert"]
contributors: ["python-backend-engineer"]

model_usage:
  primary: sonnet
  external: []

tasks:
  - id: P0-1
    title: "Port rights_record.schema.yaml"
    description: "Port v1.0 baseline; apply §9.3, §9.4, §9.5, §9.6a, §9.6b, §9.7, §9.8 adjudications (Draft 2020-12, additionalProperties:false, nullable via type:[T,\"null\"])."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended
  - id: P0-2
    title: "Port rights_extension.schema.yaml"
    description: "Port fuller entity-level extension record; §9.1 negative-space guard — must NOT define evidence_item_type/judgment_basis/any taxonomy field."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "1 pt"
    priority: "high"
    assigned_model: sonnet
    model_effort: extended
  - id: P0-3
    title: "Port content_reuse_assessment.schema.yaml"
    description: "Port with unified component_type vocabulary (§9.2/§9.8) and shared review_status/decision.status enums (§9.7/§9.10 — enum values only, enforcement deferred to P5-2)."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended
  - id: P0-4
    title: "Port permission_record.schema.yaml + rights_failure.schema.yaml"
    description: "Port both as-is structurally — no §9 conflicts named against either in the handoff review."
    status: pending
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "1 pt"
    priority: "medium"
    assigned_model: sonnet
    model_effort: adaptive
  - id: P0-5
    title: "Registry wiring + test builders"
    description: "Extend SchemaRegistry/EXPECTED_SCHEMA_NAMES in src/research_foundry/schemas.py and tests/test_schema_validation.py builders to cover all 5 new schemas."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P0-1", "P0-2", "P0-3", "P0-4"]
    estimated_effort: "2 pts"
    priority: "critical"
    assigned_model: sonnet
    model_effort: extended

parallelization:
  batch_1: ["P0-1", "P0-2", "P0-3", "P0-4"]
  batch_2: ["P0-5"]
  critical_path: ["P0-1", "P0-5"]
  estimated_total_time: "8 pts (plan bottom-up estimate; no hour estimates in plan)"

blockers: []

success_criteria:
  - {id: "P0-SC1", description: "All 5 schemas register in SchemaRegistry and pass test_registry_lists_all_schemas", status: pending}
  - {id: "P0-SC2", description: "All 7 owned §9 adjudication rows (§9.2 owned by P1) have a passing fixture demonstrating the fix and a failing fixture demonstrating the pre-fix defect would be caught", status: pending}
  - {id: "P0-SC3", description: "./.venv/bin/python -m pytest tests/test_schema_validation.py green", status: pending}
  - {id: "P0-SC4", description: "Reviewer gate: task-completion-validator sign-off (explicit verdict required)", status: pending}

notes: |
  Root of the critical path — gates every other phase (P1-P6). Owns 6 of the 10 §9
  schema-conflict adjudications; do not re-litigate resolutions (locked in the decisions
  block: .claude/worknotes/rights-entity-model/decisions-block.md).
  Reviewer gate is task-completion-validator (not karen) — this phase is schema-only,
  not Mode-D-adjacent.
---

# rights-entity-model — Phase 0: Rights Substrate

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Update via CLI (never Edit/Write on frontmatter):

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/rights-entity-model/phase-0-progress.md -t P0-1 -s completed \
  --started <ISO> --completed <ISO> --evidence "test:tests/test_schema_validation.py"
```

---

## Objective

Port the pediatric-anemia-site's v1.0 rights-governance schemas into RF's own
`schemas/*.schema.yaml` registry as RF's canonical substrate, applying the ten §9
schema-conflict adjudications at the source (this phase owns 6 of the 10) rather than
carrying them forward as debt. Gates every other phase.

---

## Orchestration Quick Reference

### Task Delegation Commands

```markdown
# Batch 1 (parallel — single message, 4 calls)
Task("data-layer-expert", "P0-1: Port schemas/rights_record.schema.yaml. Apply §9.3/§9.4/§9.5/§9.6a/§9.6b/§9.7/§9.8 adjudications per docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md (P0-1 row). Decisions block (locked, do not re-litigate): .claude/worknotes/rights-entity-model/decisions-block.md", model="sonnet")

Task("data-layer-expert", "P0-2: Port schemas/rights_extension.schema.yaml. §9.1 negative-space guard — must NOT define evidence_item_type/judgment_basis/taxonomy fields. Full AC in phase-0-2-schema.md (P0-2 row).", model="sonnet")

Task("data-layer-expert", "P0-3: Port schemas/content_reuse_assessment.schema.yaml. Unified component_type vocabulary (§9.2/§9.8) + shared review_status/decision.status enums, byte-identical to P0-1's. Full AC in phase-0-2-schema.md (P0-3 row).", model="sonnet")

Task("data-layer-expert", "P0-4: Port schemas/permission_record.schema.yaml + schemas/rights_failure.schema.yaml as-is structurally. Full AC in phase-0-2-schema.md (P0-4 row).", model="sonnet")

# Batch 2 (after batch_1 completes)
Task("python-backend-engineer", "P0-5: Wire SchemaRegistry/EXPECTED_SCHEMA_NAMES in src/research_foundry/schemas.py + test builders in tests/test_schema_validation.py for all 5 new schemas from P0-1..P0-4. Full AC in phase-0-2-schema.md (P0-5 row).", model="sonnet")
```

### After Batch Completes

```markdown
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/rights-entity-model/phase-0-progress.md \
  --updates "P0-1:completed,P0-2:completed,P0-3:completed,P0-4:completed"
```

---

## Implementation Notes

### Architectural Decisions

See decisions block §locked entries: schema-first port as Phase 0 prerequisite; RF authors
its own canonical ADR (P5-4) rather than editing the pediatric-repo v1.0 spec.

### Known Gotchas

- Do not re-derive §9 adjudication resolutions — they are locked in the decisions block.
- §9.6b's empty-`contract`-object case needs a dedicated invalid fixture (fail-open regression guard) — do not skip.
- P0-3's `component_type`/`review_status` enums must be byte-identical *literal lists* to P0-1's — no `$ref` (SchemaRegistry has no resolver support).

---

## Completion Notes

_(Fill in when phase is complete: what was built, key learnings, unexpected challenges, recommendations for Phase 1.)_
