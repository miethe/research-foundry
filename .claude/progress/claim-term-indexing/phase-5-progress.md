---
type: progress
schema_version: 2
doc_type: progress
prd: claim-term-indexing
feature_slug: claim-term-indexing
phase: 5
title: Finalization
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
total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ica-executor
contributors:
- karen
execution_model: batch-parallel
model_usage:
  primary: sonnet
  external: []
tasks:
- id: DOC-001
  description: 'CHANGELOG entry: add [Unreleased] entry per Keep A Changelog format
    for _term_index write-time indexing + --term/--role catalog facets'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.1 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-002
  description: 'CLI reference + architecture note: document rf catalog search --term/--role,
    the vocab/*.yaml format, and the _term_index namespace contract; update rf-run-export-schema.json''s
    changelog for the 1.7 bump'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.15 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-003
  description: 'Update design spec + PRD frontmatter: set design spec (docs/project_plans/design-specs/claim-term-indexing.md)
    status: implemented; set this plan''s plan_ref field on the PRD; populate this
    plan''s commit_refs/files_affected/updated'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.1 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-D1
  description: 'Deferred design spec -- model-assisted usage-role enrichment (PRD-OQ-2):
    author docs/project_plans/design-specs/term-index-model-assisted-roles-v2.md,
    maturity: idea, prd_ref set to this feature''s PRD'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.1 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-D2
  description: 'Deferred design spec -- strict-schema extension (PRD-OQ-3): author
    docs/project_plans/design-specs/term-index-strict-schema-extension-v2.md, maturity:
    idea'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.1 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-D3
  description: 'Deferred design spec -- controlled vocabulary import (PRD-OQ-1 residual):
    author docs/project_plans/design-specs/controlled-vocabulary-import-v2.md, maturity:
    idea'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.05 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-D4
  description: 'Deferred design spec -- search_text term aliasing (design-spec OQ-B):
    author docs/project_plans/design-specs/catalog-search-text-term-aliasing-v2.md,
    maturity: idea, naming the sensitivity-leak risk that must be resolved before
    this is attempted'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.05 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: DOC-005
  description: 'Symbol graph regen: regenerate ai/symbols-*.json via /analyze:symbols:symbols-update
    to reflect new/changed modules (term_index_backfill.py, catalog/export/claim-map
    extensions)'
  status: pending
  assigned_to:
  - ica-executor
  dependencies:
  - DOC-001
  - DOC-002
  - DOC-003
  - DOC-D1
  - DOC-D2
  - DOC-D3
  - DOC-D4
  estimated_effort: 0.05 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: GATE-001
  description: 'karen end-of-feature reality check: full-feature validation across
    all 8 PRD ACs, all P1-P4 exit gates, deferred-item specs, docs -- cut through
    claimed-vs-actual completion before merge'
  status: pending
  assigned_to:
  - karen
  dependencies:
  - DOC-005
  estimated_effort: gate
  assigned_model: opus
  model_effort: extended
parallelization:
  batch_1:
  - DOC-001
  - DOC-002
  - DOC-003
  - DOC-D1
  - DOC-D2
  - DOC-D3
  - DOC-D4
  batch_2:
  - DOC-005
  batch_3:
  - GATE-001
  critical_path:
  - DOC-D1
  - DOC-005
  - GATE-001
  estimated_total_time: 1 pt
blockers:
- id: BLOCKER-P3-P4-GATE
  title: Both Phase 3 and Phase 4 exit gates must be green before this phase starts
  severity: critical
  blocking:
  - DOC-001
  - DOC-002
  - DOC-003
  - DOC-D1
  - DOC-D2
  - DOC-D3
  - DOC-D4
  resolution: Confirm Phase 3 TASK-3.4 and Phase 4 TASK-4.4 task-completion-validator
    reviews both passed before dispatching any Phase 5 task
  created: '2026-07-24'
success_criteria:
- 'CHANGELOG [Unreleased] entry present'
- All 4 deferred items have design-spec paths in deferred_items_spec_refs (none N/A
  -- all 4 have concrete v2 specs per the triage table)
- Findings doc finalized if any findings captured, else N/A
- Design spec + PRD frontmatter consistent post-ship
- Symbol graph regenerated
- karen end-of-feature gate passed
files_modified:
- CHANGELOG.md
- docs/project_plans/design-specs/claim-term-indexing.md
notes: 'GATE-001 (karen) is the last task in the plan and is claude-native/opus,
  never offloaded to ica-executor per the plan''s MUST-stay verdict-class routing.
  Feature Guide + PR creation are triggered automatically once this phase''s quality
  gates pass (see plan §Wrap-Up).'
---

# claim-term-indexing - Phase 5: Finalization

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/claim-term-indexing/phase-5-progress.md -t DOC-001 -s completed
```

---

## Objective

Close out the feature: CHANGELOG entry, CLI/architecture docs, design-spec + PRD frontmatter consistency, all 4 deferred-item design specs stubbed, symbol graph regenerated, and the `karen` end-of-feature reality check before merge.

---

## Task Table

| Task ID | Task Name | Depends On | Assigned To | Estimate |
|---------|-----------|------------|-------------|----------|
| DOC-001 | CHANGELOG entry | P3, P4 | ica-executor | 0.1 pts |
| DOC-002 | CLI reference + architecture note | P3, P4 | ica-executor | 0.15 pts |
| DOC-003 | Update design spec + PRD frontmatter | P3, P4 | ica-executor | 0.1 pts |
| DOC-D1 | Deferred spec — model-assisted usage-role enrichment | P3, P4 | ica-executor | 0.1 pts |
| DOC-D2 | Deferred spec — strict-schema extension | P3, P4 | ica-executor | 0.1 pts |
| DOC-D3 | Deferred spec — controlled vocabulary import | P3, P4 | ica-executor | 0.05 pts |
| DOC-D4 | Deferred spec — `search_text` term aliasing | P3, P4 | ica-executor | 0.05 pts |
| DOC-005 | Symbol graph regen | DOC-001..DOC-D4 | ica-executor | 0.05 pts |
| GATE-001 | karen end-of-feature reality check | DOC-005 | karen (claude opus) | — |

---

## Quick Reference — Dispatch Commands

```text
Task(
  subagent_type="ica-executor",
  description="DOC-001..DOC-D4 docs and deferred specs batch",
  prompt="Mode: B — Contract Drafting. Implement DOC-001, DOC-002, DOC-003, DOC-D1, DOC-D2, DOC-D3, DOC-D4 from docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md (§Phase 5). Requires Phase 3 TASK-3.4 and Phase 4 TASK-4.4 both green. Profile: documentation-writer. Append each new deferred-item spec path to this plan's deferred_items_spec_refs."
)

Task(
  subagent_type="ica-executor",
  description="DOC-005 symbol graph regen",
  prompt="Mode: C — Autonomous Feature Sprint. Run /analyze:symbols:symbols-update to regenerate ai/symbols-*.json reflecting term_index_backfill.py and the catalog/export/claim-map extensions from this feature. Depends on DOC-001..DOC-D4 being complete."
)

Task(
  subagent_type="karen",
  description="GATE-001 end-of-feature reality check",
  prompt="Mode: E — Reviewer. Full-feature validation of claim-term-indexing against docs/project_plans/PRDs/features/claim-term-indexing-v1.md (all 8 ACs) and docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md (all P1-P4 exit gates, all 4 deferred-item specs, docs). Cut through claimed-vs-actual completion before merge; route any gap back to the relevant phase, not silently accepted."
)
```

---

## Quality Gates

- [ ] CHANGELOG `[Unreleased]` entry present
- [ ] All 4 deferred items have design-spec paths in `deferred_items_spec_refs` (none N/A — all 4 have concrete v2 specs per the triage table)
- [ ] Findings doc finalized if any findings captured, else N/A
- [ ] Design spec + PRD frontmatter consistent post-ship
- [ ] Symbol graph regenerated
- [ ] karen end-of-feature gate passed

---

## Validation Commands

```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/ -k "term_index" -v
cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit
```

---

## Completion Notes

Fill in when phase is complete: what was built, key learnings, unexpected challenges, and confirmation that the Feature Guide + PR wrap-up steps ran.
