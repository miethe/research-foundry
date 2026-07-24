---
type: progress
schema_version: 2
doc_type: progress
prd: claim-term-indexing
feature_slug: claim-term-indexing
phase: 4
title: runs-viewer Surfaces
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
total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ica-executor
contributors:
- task-completion-validator
execution_model: batch-parallel
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-4.1
  description: 'AssertionCatalogPane.tsx terms facet chip-row: add a "terms present"
    facet chip-row sourced from catalog_terms, wired into the existing facet-driven
    filter row (search.data?.facets, AssertionCatalogPane.tsx:53-114); no-hit items
    render an empty/omitted state, not an error'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-4.2
  description: 'CatalogScreen.tsx ?term= deep-link: add a ?term=CBC deep-link parameter
    to CatalogScreen.tsx (:448-497), filtering the existing useCatalogSearch tab
    query; absence of the param behaves exactly as today (no regression)'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-4.3
  description: 'ClaimLedgerTable.tsx term/role badge: add a term/usage-role column
    or badge sourced from _term_index.usage_roles, visually distinct from any real
    pediatric_cds structured threshold value (namespace-boundary reinforcement,
    D2/FR-15); a claim with no _term_index renders no badge, not an empty/error
    badge'
  status: pending
  assigned_to:
  - ica-executor
  dependencies: []
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: TASK-4.4
  description: 'tsc clean + runtime smoke across every target_surface (EXIT GATE,
    R-P4): run tsc -p tsconfig.app.json --noEmit (the real gate -- plain npx tsc
    --noEmit is a no-op in this repo); runtime-smoke the dev build against all three
    target_surfaces plus a desktop >=1440px screenshot per PRD AC-8''s visual-evidence
    requirement'
  status: pending
  assigned_to:
  - ica-executor
  - task-completion-validator
  dependencies:
  - TASK-4.1
  - TASK-4.2
  - TASK-4.3
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
parallelization:
  batch_1:
  - TASK-4.1
  - TASK-4.2
  - TASK-4.3
  batch_2:
  - TASK-4.4
  critical_path:
  - TASK-4.1
  - TASK-4.4
  estimated_total_time: 2 pts
blockers:
- id: BLOCKER-P2-GATE
  title: Phase 2 exit gate (TASK-2.7) must be green before this phase starts
  severity: critical
  blocking:
  - TASK-4.1
  - TASK-4.2
  - TASK-4.3
  resolution: Confirm Phase 2 task-completion-validator review passed before dispatching
    any Phase 4 task
  created: '2026-07-24'
success_criteria:
- 'tsc -p tsconfig.app.json --noEmit clean (not the no-op npx tsc --noEmit)'
- Runtime smoke covers all three target_surfaces (AssertionCatalogPane, CatalogScreen,
  ClaimLedgerTable)
- Term/role badge visually distinct from real pediatric_cds threshold values
- Missing-_term_index state renders empty/omitted, never an error or misleading
  zero-value badge
- Desktop >=1440px screenshot captured per AC-8 visual-evidence requirement
- task-completion-validator review passed
files_modified:
- frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx
- frontend/runs-viewer/src/screens/CatalogScreen.tsx
- frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
notes: 'Runs in parallel with Phase 3 (disjoint file ownership -- frontend-only).
  Both fork from the Phase 2 exit gate and join at Phase 5. Use the real gate: tsc
  -p tsconfig.app.json --noEmit (plain npx tsc --noEmit is a no-op in this repo).'
---

# claim-term-indexing - Phase 4: runs-viewer Surfaces

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/claim-term-indexing/phase-4-progress.md -t TASK-4.1 -s completed
```

---

## Objective

Surface `_term_index` in the runs-viewer: a terms facet chip-row on `AssertionCatalogPane`, a `?term=` deep-link on `CatalogScreen`, and a term/role badge on `ClaimLedgerTable`, distinct from real `pediatric_cds` threshold displays, with graceful empty states for legacy data.

---

## Task Table

| Task ID | Task Name | Depends On | Assigned To | Estimate |
|---------|-----------|------------|-------------|----------|
| TASK-4.1 | `AssertionCatalogPane.tsx` terms facet chip-row | Phase 2 | ica-executor | 0.5 pts |
| TASK-4.2 | `CatalogScreen.tsx` `?term=` deep-link | Phase 2 | ica-executor | 0.5 pts |
| TASK-4.3 | `ClaimLedgerTable.tsx` term/role badge | Phase 2 | ica-executor | 0.5 pts |
| TASK-4.4 | `tsc` clean + runtime-smoke exit gate | TASK-4.1, TASK-4.2, TASK-4.3 | ica-executor + task-completion-validator | 0.5 pts |

---

## Quick Reference — Dispatch Commands

```text
Task(
  subagent_type="ica-executor",
  description="TASK-4.1 terms facet chip-row",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-4.1 from docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md (§Phase 4). Requires Phase 2 TASK-2.7 green. Target: frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx. Profile: ui-engineer-enhanced."
)

Task(
  subagent_type="ica-executor",
  description="TASK-4.2 ?term= deep-link",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-4.2 from the claim-term-indexing-v1 implementation plan (§Phase 4). Requires Phase 2 TASK-2.7 green. Target: frontend/runs-viewer/src/screens/CatalogScreen.tsx. Profile: ui-engineer-enhanced."
)

Task(
  subagent_type="ica-executor",
  description="TASK-4.3 term/role badge",
  prompt="Mode: C — Autonomous Feature Sprint. Implement TASK-4.3 from the claim-term-indexing-v1 implementation plan (§Phase 4). Requires Phase 2 TASK-2.7 green. Target: frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx. Profile: ui-engineer-enhanced."
)

Task(
  subagent_type="task-completion-validator",
  description="TASK-4.4 tsc + runtime-smoke gate review",
  prompt="Mode: E — Reviewer. Verify TASK-4.4: run `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit`, confirm runtime smoke across all three target_surfaces from TASK-4.1/4.2/4.3, and confirm a desktop >=1440px screenshot exists per PRD AC-8."
)
```

---

## Quality Gates

- [ ] `tsc -p tsconfig.app.json --noEmit` clean (not the no-op `npx tsc --noEmit`)
- [ ] Runtime smoke covers all three target_surfaces (AssertionCatalogPane, CatalogScreen, ClaimLedgerTable)
- [ ] Term/role badge visually distinct from real `pediatric_cds` threshold values
- [ ] Missing-`_term_index` state renders empty/omitted, never an error or misleading zero-value badge
- [ ] Desktop >=1440px screenshot captured per AC-8 visual-evidence requirement
- [ ] task-completion-validator review passed

---

## Validation Commands

```bash
cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit
```

---

## Completion Notes

Fill in when phase is complete: what was built, key learnings, unexpected challenges, recommendations for Phase 5.
