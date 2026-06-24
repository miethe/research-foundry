---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-context-panels"
feature_slug: "runs-context-panels"
prd_ref: "docs/project_plans/PRDs/features/runs-context-panels-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
execution_model: sequential
phase: 2
title: "Export Wiring & Redaction"
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

owners: ["python-backend-engineer"]
contributors: ["ui-engineer-enhanced"]

model_usage:
  primary: "sonnet"
  external: []

tasks:
  - id: "P2-001"
    description: "Add _build_context(run_paths: RunPaths) -> dict | None to export_service.py. Reads routing_decision.yaml, research_brief.md, swarm_plan.yaml, upstream entity IDs from run.yaml. Returns None when all source artifacts absent."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1-005"]
    estimated_effort: "2 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P2-002"
    description: "Each absent artifact sets context.* field to null (not omitted). When all artifacts absent, context itself is null. Unit test BE-002 per-artifact."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-001"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P2-003"
    description: "Extend R9 redaction pass to cover context.routing_decision, context.swarm_plan, context.research_brief_md source URLs and work_sensitive-tagged text. Unit test BE-003."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-001"]
    estimated_effort: "1 pt"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P2-004"
    description: "Wire _build_context() into main export pipeline so run.json emits context: {...} | null. Integration test: full export with realistic fixture emits schema 1.3 with populated+redacted context."
    status: pending
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2-003"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P2-005"
    description: "Serialization barrier verification: ui-engineer-enhanced confirms exported run.json context structure matches TS RunContext type exactly; no type-shape mismatches."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P2-004", "P1-002"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

parallelization:
  batch_1: ["P2-001"]
  batch_2: ["P2-002", "P2-003"]
  batch_3: ["P2-004"]
  batch_4: ["P2-005"]
  critical_path: ["P2-001", "P2-003", "P2-004", "P2-005"]
  estimated_total_time: "2-3 days"

blockers: []

success_criteria:
  - id: "SC-P2-1"
    description: "_build_context() helper implemented and tested (all-present + each-absent-independently cases)"
    status: pending
  - id: "SC-P2-2"
    description: "Null-fill semantics verified (absent field → null, not omitted)"
    status: pending
  - id: "SC-P2-3"
    description: "R9 redaction extended to context.*; redaction unit test BE-003 passes"
    status: pending
  - id: "SC-P2-4"
    description: "Export pipeline integration test passes; run.json emits schema 1.3"
    status: pending
  - id: "SC-P2-5"
    description: "Export errors emit to stderr as structured JSON lines (not uncaught exceptions)"
    status: pending
  - id: "SC-P2-6"
    description: "Serialization barrier verification (P2-005) complete — no type-shape mismatches"
    status: pending
  - id: "SC-P2-7"
    description: "task-completion-validator sign-off"
    status: pending

files_modified:
  - "src/research_foundry/services/export_service.py"
---

# runs-context-panels - Phase 2: Export Wiring & Redaction

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/runs-context-panels/phase-2-progress.md -t P2-001 -s completed
```

---

## Objective

Wire `_build_context()` into `export_service.py` to populate the `context` block from on-disk YAML/Markdown artifacts and extend the existing R9 sensitivity redaction pass. After P2 the `rf run export --json` command emits schema 1.3 with a populated, redacted `context` key.

---

## Implementation Notes

### Architectural Decisions

- ICA free-tier delegation candidate for this phase (bounded, well-specified, mechanical wave). Re-run authoritative pytest + backward-compat assertion in-session after ICA completes.
- `_build_context()` reads exclusively via `RunPaths` — no stored absolute paths.
- Error handling: structured errors on stderr (JSON lines), never uncaught exceptions.

### Patterns and Best Practices

- Reuse existing R9 sensitivity rules; only one field-specific extension required (OQ-5 resolution): `context.research_brief_md` source URLs and `sensitivity: work_sensitive`-tagged text.
- P2-002 and P2-003 can run in parallel after P2-001.
- P2-005 (serialization barrier) is owned by `ui-engineer-enhanced` (integration_owner per plan) — this is a mandatory seam check before P3 FE integration testing.

### Known Gotchas

- Verify whether `ibom_id` / `intenttree_node_id` are present in `run.yaml` before implementing P2-001; if absent, `upstream_entities` degrades to `intent_id`-only without erroring.
- Backward-compat assertion from P1-004 must still pass after P2-004 completes (1.2 consumers unaffected).

---

## Completion Notes

_(Fill when phase complete)_
