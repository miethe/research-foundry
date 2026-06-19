---
type: progress
schema_version: 2
doc_type: progress
prd: runs-frontend
feature_slug: runs-frontend
phase: 1
title: Export Contract (Upstream Gate)
status: completed
created: '2026-06-19'
updated: '2026-06-19'
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
commit_refs:
- 14bc23c
pr_refs: []
started: null
completed: null
overall_progress: 100
completion_estimate: on-track
total_tasks: 10
completed_tasks: 10
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
contributors:
- backend-architect
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P1-SCHEMA-FREEZE
  description: Author docs/dev/architecture/rf-run-export-schema.md with denormalized
    claim-graph shape; resolve OQ-1; submit for backend-architect review before merge
  status: completed
  assigned_to:
  - python-backend-engineer
  - backend-architect
  dependencies: []
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P1-STATUS-001
  description: "Resolve OQ-2: define derived-status enum (planned\u2192sources_ingested\u2192\
    extracted\u2192claim_mapped\u2192synthesized\u2192verified\u2192published); encode\
    \ in schema and implement in export service"
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-SCHEMA-FREEZE
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: extended
- id: P1-SENS-CONFIG
  description: 'Resolve OQ-3: default sensitivity threshold = public-only; add viewer.sensitivity_threshold
    to foundry.yaml schema; export service reads this key'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-SCHEMA-FREEZE
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P1-EXPORT-SVC
  description: "Implement src/research_foundry/services/export_service.py: file walk\
    \ via FoundryPaths.discover(), claim-graph join (clm_NNN\u2192source_card YAML\u2192\
    extracted_points[].quote), sensitivity filter"
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-STATUS-001
  - P1-SENS-CONFIG
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
- id: P1-CLI-EXPORT
  description: Implement rf run export --json [--run-id RUN_ID | --all] sub-command
    in cli_commands.py; writes run.json to <run_dir>/run.json or stdout with --stdout
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-EXPORT-SVC
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P1-CLI-LIST
  description: "Implement rf run list --json sub-command; recursive runs/**/run.yaml\
    \ discovery depth \u2264 3; returns JSON array with status_derived (not run.yaml.status)"
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-EXPORT-SVC
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P1-TEST-PATHS
  description: 'Unit test: assert no field from run_index.yaml or verification.yaml
    is used as a file path in export service; all file reads via FoundryPaths.discover()'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-EXPORT-SVC
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P1-SENS-001
  description: 'Synthetic sensitivity fixture: src_SYNTH001.md with sensitivity: work_sensitive;
    assert work_sensitive quote absent from export JSON; confirms R9 gate'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-EXPORT-SVC
  - P1-SENS-CONFIG
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: extended
- id: P1-TEST-UNIT
  description: 'Unit tests for export_service.py: claim-graph join correctness, status
    derivation (stale-status case), sensitivity filter, path derivation; >80% coverage'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-EXPORT-SVC
  - P1-STATUS-001
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
- id: P1-INT-TEST
  description: 'Integration test on rf_run_20260613_*: every [claim:clm_NNN] in report_draft.md
    has entry in claims[]; 3 sampled claims have non-null sources[] with non-empty
    quote; schema validation passes'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - P1-TEST-UNIT
  - P1-CLI-EXPORT
  - P1-SCHEMA-FREEZE
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: extended
parallelization:
  batch_1:
  - P1-SCHEMA-FREEZE
  batch_2:
  - P1-STATUS-001
  - P1-SENS-CONFIG
  batch_3:
  - P1-EXPORT-SVC
  batch_4:
  - P1-CLI-EXPORT
  - P1-CLI-LIST
  - P1-TEST-PATHS
  - P1-SENS-001
  batch_5:
  - P1-TEST-UNIT
  batch_6:
  - P1-INT-TEST
  critical_path:
  - P1-SCHEMA-FREEZE
  - P1-STATUS-001
  - P1-EXPORT-SVC
  - P1-TEST-UNIT
  - P1-INT-TEST
  estimated_total_time: 3-4 days
blockers: []
success_criteria:
- rf run export --json produces valid run.json for rf_run_20260613_* real run
- Export schema frozen at docs/dev/architecture/rf-run-export-schema.md and merged
- Sensitivity redaction confirmed by synthetic fixture test (R9 gate)
- "Integration round-trip test green; claim\u2192source\u2192quote chain correct"
- backend-architect schema review sign-off recorded
- Unit test coverage > 80% for export_service.py
- task-completion-validator phase review passed
progress: 100
---

# runs-frontend - Phase 1: Export Contract (Upstream Gate)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/runs-frontend/phase-1-progress.md -t P1-SCHEMA-FREEZE -s completed --force
```

---

## Objective

Python-only phase that creates the deterministic `rf run export --json` contract — the frontend's sole data source. Produces a denormalized `run.json` with sensitivity redaction applied at the export layer and all file paths re-derived via `FoundryPaths.discover()`. This is the **hard upstream gate**: no Phase 2+ task may begin until this phase is fully cleared and the export schema is merged.

---

## Key Rules

- **P1-SCHEMA-FREEZE is the root task**. It must be authored first and reviewed by `backend-architect` before merge.
- **P1-SCHEMA-FREEZE is an explicit dependency of every Phase 2 task** (propagates to all P3+ tasks transitively).
- **R9 Sensitivity Gate**: P1-SENS-001 must pass before the P1 gate clears. Sensitive content (`work_sensitive`, `client_sensitive`) must never appear in the export JSON.
- **No stored absolute paths**: All file reads via `FoundryPaths.discover()`; `run_index.yaml` and `verification.yaml` stored path fields are never used for file I/O.
- **No LLM calls**: The export service is deterministic; no LLM is on the recall path.

---

## Reviewer Gates

| Reviewer | Trigger | Blocks |
|----------|---------|--------|
| `backend-architect` | Schema freeze candidate ready | P1 gate clearance |
| `task-completion-validator` | All P1 quality gates pass including sensitivity fixture | P2 start |
