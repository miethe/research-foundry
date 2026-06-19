---
type: progress
schema_version: 2
doc_type: progress
prd: runs-frontend
feature_slug: runs-frontend
phase: 2
title: Data Layer + TypeScript Types
status: completed
created: '2026-06-19'
updated: '2026-06-19'
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
commit_refs:
- e4045de
pr_refs: []
started: null
completed: null
overall_progress: 100
completion_estimate: on-track
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
execution_model: sequential
model_usage:
  primary: sonnet
  external: []
tasks:
- id: P2-FORK
  description: "Fork IntentTree Web into frontend/runs-viewer/; remove IntentTree\
    \ entity files; rename AgentRun\u2192RFRun; preserve React+Vite+React Query+Tailwind\
    \ config, router shell, Vitest config"
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P1-SCHEMA-FREEZE
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P2-TS-CODEGEN
  description: Set up json-schema-to-typescript build step; generate TS interfaces
    from all 20 schemas/*.schema.yaml into frontend/runs-viewer/src/types/rf/; all
    optional fields marked ?
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-FORK
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
- id: P2-AUDIT-OQ5
  description: Audit IntentTree Web fork against @miethe/ui peer requirements (React/Tailwind/radix
    compat); record decision in .claude/worknotes/runs-frontend/oq5-decision.md before
    P3 begins
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-FORK
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P2-API-CLIENT
  description: 'Implement frontend/runs-viewer/src/api/client.ts: dual-mode fetch
    (static JSON / loopback behind RUNS_FRONTEND_LOOPBACK_API flag); GET-only; typed
    returns from generated types'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-TS-CODEGEN
  estimated_effort: 0.5 pts
  assigned_model: sonnet
  model_effort: adaptive
- id: P2-HOOKS
  description: 'Implement 4 React Query hooks: useRunList(), useRunDetail(runId),
    useClaimLedger(runId), useSourceCard(runId, sourceCardId); all typed via generated
    types; Vitest tests passing'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-API-CLIENT
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
- id: P2-FIXTURE
  description: Copy run.json from P1 integration test into frontend/runs-viewer/src/test/fixtures/;
    add scaffold-only fixture; wire into Vitest config
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-HOOKS
  estimated_effort: 0.25 pts
  assigned_model: sonnet
  model_effort: adaptive
parallelization:
  batch_1:
  - P2-FORK
  batch_2:
  - P2-TS-CODEGEN
  - P2-AUDIT-OQ5
  batch_3:
  - P2-API-CLIENT
  batch_4:
  - P2-HOOKS
  batch_5:
  - P2-FIXTURE
  critical_path:
  - P2-FORK
  - P2-TS-CODEGEN
  - P2-API-CLIENT
  - P2-HOOKS
  - P2-FIXTURE
  estimated_total_time: 2-3 days
blockers: []
success_criteria:
- App boots in browser against P1 export fixture with no console errors
- tsc --noEmit clean; no any at entity (RFRun, RFClaim, RFSourceCard, RFEvidenceBundle)
  boundaries
- useRunList(), useRunDetail(), useClaimLedger(), useSourceCard() hooks return typed
  data from static JSON fixture
- OQ-5 @miethe/ui compatibility decision recorded in worknote before P3 begins
- Vitest hook contract tests passing
- task-completion-validator P2 phase review passed
progress: 100
---

# runs-frontend - Phase 2: Data Layer + TypeScript Types

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/runs-frontend/phase-2-progress.md -t P2-FORK -s completed --force
```

---

## Objective

Fork IntentTree Web into `frontend/runs-viewer/`, swap the entity model (`AgentRun` → `RFRun`), generate TypeScript types from the 20 `schemas/*.schema.yaml` files, wire React Query hooks, and resolve the OQ-5 `@miethe/ui` compatibility question. Mostly mechanical fork wiring — effort is `adaptive`. OQ-5 audit must complete before P3.

---

## Key Rules

- **Every task depends on P1-SCHEMA-FREEZE being merged** (hard gate — do not begin any task before P1 gate cleared).
- **No form elements rule**: The API client must not export any mutation methods (no POST/PUT/DELETE).
- **R-P2 compliance**: All generated types mark optional fields with `?`; access via `?.` throughout.
- **OQ-5 decision timing**: P2-AUDIT-OQ5 is the second task after fork, before any component work.

---

## Reviewer Gate

| Reviewer | Trigger | Blocks |
|----------|---------|--------|
| `task-completion-validator` | App boots, tsc clean, OQ-5 resolved | P3 start |
