---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-context-panels"
feature_slug: "runs-context-panels"
prd_ref: "docs/project_plans/PRDs/features/runs-context-panels-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
execution_model: batch-parallel
phase: 1
title: "Schema & Contract"
status: pending
created: 2026-06-23
updated: 2026-06-23
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: on-track

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer", "data-layer-expert"]
contributors: ["backend-architect"]

model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "P1-001"
    description: "Extend run_export.py with RunContext dataclass/TypedDict (4 sub-objects). Bump schema_version constant to 1.3."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "1 pt"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P1-002"
    description: "Define RunContext TypeScript interface in src/runs_viewer/types/run.ts with 4 optional nullable sub-types. Extend RunExport with context?: RunContext | null."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-001"]
    estimated_effort: "1 pt"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P1-003"
    description: "Update docs/dev/architecture/rf-run-export-schema.md §9 with finalized v1.3 context field contract (stub — full doc in P4). Add changelog row for v1.3."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-001"]
    estimated_effort: "0.5 pts"
    priority: medium
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P1-004"
    description: "Add backward-compat regression test using schema 1.2 run.json fixture (no context key). Assert existing consumers load without errors."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-002"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P1-005"
    description: "Submit schema 1.2→1.3 bump for backend-architect re-review per frozen-schema policy. Provide field contract, additive+optional proof, OQ-1 rationale. Record approval."
    status: pending
    assigned_to: ["backend-architect"]
    dependencies: ["P1-003", "P1-004"]
    estimated_effort: "—"
    priority: critical
    assigned_model: sonnet
    model_effort: extended

parallelization:
  batch_1: ["P1-001"]
  batch_2: ["P1-002", "P1-003"]
  batch_3: ["P1-004"]
  batch_4: ["P1-005"]
  critical_path: ["P1-001", "P1-002", "P1-004", "P1-005"]
  estimated_total_time: "2-3 days"

blockers: []

success_criteria:
  - id: "SC-P1-1"
    description: "Python RunContext type defined; RunExport gains optional context field"
    status: pending
  - id: "SC-P1-2"
    description: "TypeScript RunContext interface defined; tsc --noEmit passes"
    status: pending
  - id: "SC-P1-3"
    description: "Schema doc §9 updated with v1.3 contract stub"
    status: pending
  - id: "SC-P1-4"
    description: "Backward-compat regression test passes with 1.2 fixture"
    status: pending
  - id: "SC-P1-5"
    description: "backend-architect re-review APPROVED (hard gate — P2 cannot start without this)"
    status: pending
  - id: "SC-P1-6"
    description: "task-completion-validator sign-off"
    status: pending

files_modified:
  - "src/research_foundry/schemas/run_export.py"
  - "src/runs_viewer/types/run.ts"
  - "docs/dev/architecture/rf-run-export-schema.md"
---

# runs-context-panels - Phase 1: Schema & Contract

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/runs-context-panels/phase-1-progress.md -t P1-001 -s completed
```

---

## Objective

Freeze the `context` field shape in the Python schema and TypeScript types, update the schema doc stub, and obtain backend-architect governance approval before any export-wiring work (P2) begins. This is the serialization barrier that gates the entire feature.

---

## Implementation Notes

### Architectural Decisions

- `context` key is **additive + optional** (`RunContext | None` in Python; `context?: RunContext | null` in TypeScript). Existing consumers must never hard-destructure `context`.
- Schema version bumps 1.2 → 1.3. The Python constant and the schema doc row must match.
- P1-002 may NOT modify any existing fields in `run.ts` — only additions allowed (serialization barrier rule).

### Patterns and Best Practices

- Follow `RunPaths` pattern for all file-path references (no stored absolute paths).
- Use `TypedDict` or `dataclass` for `RunContext` in Python per existing schema module conventions.
- 4 sub-objects: `routing_decision: dict | None`, `research_brief_md: str | None`, `swarm_plan: dict | None`, `upstream_entities: dict | None`.

### Known Gotchas

- P1-002 depends on P1-001 completing the Python shape first — TypeScript types must mirror Python dict keys 1:1.
- P1-003 and P1-002 can run in parallel after P1-001.
- backend-architect re-review (P1-005) is a **hard gate** — P2 cannot start until approval is recorded.

---

## Completion Notes

_(Fill when phase complete)_
