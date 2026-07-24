---
type: progress
schema_version: 2
doc_type: progress
prd: claim-term-indexing
feature_slug: claim-term-indexing
phase: 2
title: Read-Model Propagation
status: pending
created: '2026-07-24'
updated: '2026-07-24'
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ica-executor
contributors:
- task-completion-validator
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-2.1
  description: 'export_run additive _term_index field: extend export_run (export_service.py:668-694)
    to additively include _term_index in run.json; bump rf-run-export-schema.json
    to schema version 1.7 (additive-only); a legacy claim with no _term_index exports
    cleanly'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.75 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-2.2
  description: 'runs-viewer run-export.ts type bump (seam task, R-P3, D7 dual-update):
    same leaf as TASK-2.1; add _term_index to the hand-written run-export.ts types
    so the field is not silently dropped'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-2.1
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-2.3
  description: 'catalog_terms DDL + per-row sensitivity_rank: add catalog_terms(catalog_item_id,
    term, role, run_id, sensitivity_rank) join table mirroring catalog_links (catalog_service.py:192-199);
    each row carries the sensitivity_rank of the claim/evidence point it derives
    from (D3) -- never a single flat blob at max-permissive tier'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 1.0 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-2.4
  description: '_build_claim_and_inference_rows extension + rebuild wiring: extend
    _build_claim_and_inference_rows (:567-620) to carry _term_index fields into
    catalog_terms rows at the sensitivity rank established by TASK-2.3; wire into
    the same rebuild()/rebuild_schema() pass as catalog_items (:313)'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-2.3
  estimated_effort: 0.75 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-2.5
  description: 'rf catalog search --term/--role facets (OQ-C resolved): add repeatable
    --term/--role filters against catalog_terms, following the existing --item_type/--project
    multi-value filter pattern (catalog_service.py:1263-1298); AND across distinct
    flags, OR within repeats of the same flag'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-2.4
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-2.6
  description: 'rf serve term/role passthrough: api/routers/catalog.py passes --term/--role-equivalent
    query params through to the catalog layer with zero new read-path computation
    (FR-13)'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - TASK-2.5
  estimated_effort: 0.25 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-2.7
  description: 'Sensitivity-threshold tests + rebuild idempotency (EXIT GATE): serve-api
    sensitivity tests at each threshold level, testing the serve layer (not just
    service layer) per the sensitivity-threshold-router-gate diagnostic trap; plus
    a catalog_terms rebuild idempotency test'
  status: pending
  assigned_to:
  - ica-executor
  - task-completion-validator
  dependencies:
  - TASK-2.6
  estimated_effort: 0.25 pts
  assigned_model: sonnet
  model_effort: adaptive
parallelization:
  batch_1:
  - TASK-2.1
  - TASK-2.3
  batch_2:
  - TASK-2.2
  - TASK-2.4
  batch_3:
  - TASK-2.5
  batch_4:
  - TASK-2.6
  batch_5:
  - TASK-2.7
  critical_path:
  - TASK-2.3
  - TASK-2.4
  - TASK-2.5
  - TASK-2.6
  - TASK-2.7
  estimated_total_time: 4 pts
blockers:
- id: BLOCKER-P1-GATE
  title: Phase 1 guard tests (TASK-1.6) must be green before this phase starts
  severity: critical
  blocking:
  - TASK-2.1
  - TASK-2.3
  resolution: Confirm Phase 1 task-completion-validator review passed before dispatching
    any Phase 2 task
  created: '2026-07-24'
success_criteria:
- run.json schema 1.7 is additive-only; a 1.6-shaped consumer still parses it (AC-4)
- run-export.ts types bumped in the same phase (D7 dual-update, no dropped field)
- catalog_terms rows respect per-row sensitivity_rank; serve-api tests pass at each
  threshold (AC-5, Risk 1 mitigation)
- rf catalog search --term/--role and rf serve equivalent return matching results
  (AC-6)
- Rebuild idempotency confirmed
- task-completion-validator review passed
files_modified:
- src/research_foundry/services/export_service.py
- docs/dev/architecture/rf-run-export-schema.json
- src/research_foundry/services/catalog_service.py
- src/research_foundry/cli_commands.py
- src/research_foundry/api/routers/catalog.py
- frontend/runs-viewer/src/lib/run-export.ts
notes: 'Highest-risk phase in the plan. Entry gate: Phase 1 TASK-1.6 green. Exit
  gate (TASK-2.7) unlocks P3 and P4, which fork in parallel on disjoint file sets.'
---

# claim-term-indexing - Phase 2: Read-Model Propagation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/claim-term-indexing/phase-2-progress.md -t TASK-2.1 -s completed
```

---

## Objective

Propagate the write-time `_term_index` read-only through `export` (schema 1.7), `catalog` (`catalog_terms` DDL with per-row `sensitivity_rank`), `search`/`serve` (`--term`/`--role` facets), never recomputing and never touching identity hashing.

---

## Task Table

| Task ID | Task Name | Depends On | Assigned To | Estimate |
|---------|-----------|------------|-------------|----------|
| TASK-2.1 | `export_run` additive `_term_index` field (schema 1.7) | Phase 1 | ica-executor | 0.75 pts |
| TASK-2.2 | runs-viewer `run-export.ts` type bump (D7 dual-update) | TASK-2.1 | ica-executor | 0.5 pts |
| TASK-2.3 | `catalog_terms` DDL + per-row `sensitivity_rank` | Phase 1 | ica-executor (data-layer-expert profile) | 1.0 pts |
| TASK-2.4 | `_build_claim_and_inference_rows` extension + rebuild wiring | TASK-2.3 | ica-executor | 0.75 pts |
| TASK-2.5 | `rf catalog search --term/--role` facets | TASK-2.4 | ica-executor | 0.5 pts |
| TASK-2.6 | `rf serve` term/role passthrough | TASK-2.5 | ica-executor | 0.25 pts |
| TASK-2.7 | Sensitivity-threshold tests + rebuild idempotency (exit gate) | TASK-2.6 | ica-executor + task-completion-validator | 0.25 pts |

---

## Quick Reference — Dispatch Commands

```text
Task(
  subagent_type="ica-executor",
  description="TASK-2.1 + TASK-2.2 export schema 1.7 bump",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-2.1 and TASK-2.2 from docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md (§Phase 2). Requires Phase 1 TASK-1.6 green. Bump run.json to schema 1.7 additively and update runs-viewer run-export.ts types in the SAME leaf per D7. Profile: python-backend-engineer."
)

Task(
  subagent_type="ica-executor",
  description="TASK-2.3 catalog_terms DDL",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-2.3 from the claim-term-indexing-v1 implementation plan (§Phase 2): catalog_terms table with per-row sensitivity_rank (D3). Requires Phase 1 TASK-1.6 green. Profile: data-layer-expert."
)

Task(
  subagent_type="ica-executor",
  description="TASK-2.4 through TASK-2.6 rebuild + search + serve",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-2.4, TASK-2.5, TASK-2.6 from the claim-term-indexing-v1 implementation plan (§Phase 2) in sequence. Depends on TASK-2.3 (catalog_terms DDL) being complete. Profile: python-backend-engineer."
)

Task(
  subagent_type="task-completion-validator",
  description="TASK-2.7 sensitivity + idempotency gate review",
  prompt="Mode: E — Reviewer. Verify TASK-2.7 sensitivity-threshold serve-api tests and catalog_terms rebuild idempotency are green per docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md Phase 2 acceptance criteria before P3/P4 may start."
)
```

---

## Quality Gates

- [ ] `run.json` schema 1.7 is additive-only; a 1.6-shaped consumer still parses it (AC-4)
- [ ] `run-export.ts` types bumped in the same phase (D7 dual-update, no dropped field)
- [ ] `catalog_terms` rows respect per-row `sensitivity_rank`; serve-api tests pass at each threshold (AC-5, Risk 1 mitigation)
- [ ] `rf catalog search --term/--role` and `rf serve` equivalent return matching results (AC-6)
- [ ] Rebuild idempotency confirmed
- [ ] task-completion-validator review passed

---

## Validation Commands

```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/services/test_export_service_term_index.py tests/services/test_catalog_terms_sensitivity.py tests/api/test_serve_catalog_term_facets.py -v
cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit
```

---

## Completion Notes

Fill in when phase is complete: what was built, key learnings, unexpected challenges, recommendations for Phase 3/4 (which fork in parallel from this gate).
