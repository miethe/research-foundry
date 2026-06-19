---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-frontend"
feature_slug: "runs-frontend"
phase: 3
title: "Read Surfaces — Run List + Trust Panel"
status: "pending"
created: 2026-06-19
updated: 2026-06-19
prd_ref: "docs/project_plans/PRDs/features/runs-frontend-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-frontend-v1.md"
commit_refs: []
pr_refs: []
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 9
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["frontend-developer"]

execution_model: batch-parallel

model_usage:
  primary: "sonnet"
  external: []

tasks:
  # Run List sub-track (ui-engineer-enhanced)
  - id: "P3-LIST-CARD"
    description: "Implement RunCard.tsx: derived lifecycle badge, sensitivity badge, claim counts, verification pass/fail, governance verdict; uses RFRunSummary typed data from useRunList()"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P2-HOOKS"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-LIST-SCREEN"
    description: "Implement RunListScreen.tsx: uses useRunList() hook; renders RunCard per run; filter tabs by derived state (verified/needs-review/failed/planned); 4 nested runs/runs/ runs must appear"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-LIST-CARD"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-SCHEMA-BADGE"
    description: "Add optional schema-version mismatch badge to RunCard; renders when schema_version_mismatch: true present; graceful absent when field absent (OQ-7 partial resolution)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-LIST-CARD"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  # Trust Panel sub-track (frontend-developer — parallel)
  - id: "P3-TRUST-CHECKLIST"
    description: "Implement VerificationChecklist.tsx: named checks from verification.yaml with pass/fail/warning badges; each failing check renders deep-link anchor href=#clm_NNN"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-HOOKS"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-TRUST-DONUT"
    description: "Implement ClaimStatusDonut.tsx: donut chart from evidence_bundle.counts (supported/inference/speculation); graceful empty-state when evidence_bundle absent"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-HOOKS"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-TRUST-PANEL"
    description: "Implement TrustPanel.tsx: assembles header badges, VerificationChecklist, ClaimStatusDonut, timeline stepper from run_trace.jsonl, governance block from evidence_bundle.governance"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P3-TRUST-CHECKLIST", "P3-TRUST-DONUT"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  # Shared + Seam tasks (ui-engineer-enhanced; after both parallel tracks)
  - id: "P3-EMPTY-STATES"
    description: "All 9 optional entities show graceful empty-states in RunDetailScreen.tsx: source_candidates, report_final, critic_review, council_review, governance_review, raw_idea, research_intent, ibom, intenttree_node"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-TRUST-PANEL", "P3-LIST-SCREEN"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-SEAM-001"
    description: "Seam task: verify RunListScreen→RunDetailScreen navigation passes correct runId; RunDetailScreen composes TrustPanel via useRunDetail(runId); failing check deep-link renders #clm_NNN"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-EMPTY-STATES"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P3-VITEST"
    description: "Phase 3 Vitest tests: run list card rendering, filter tab logic, verification checklist check rendering, sensitivity badge, empty-state for scaffold-only fixture"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-SEAM-001"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

parallelization:
  batch_1:
    - "P3-LIST-CARD"
    - "P3-TRUST-CHECKLIST"
    - "P3-TRUST-DONUT"
  batch_2:
    - "P3-LIST-SCREEN"
    - "P3-SCHEMA-BADGE"
    - "P3-TRUST-PANEL"
  batch_3: ["P3-EMPTY-STATES"]
  batch_4: ["P3-SEAM-001"]
  batch_5: ["P3-VITEST"]
  critical_path: ["P3-LIST-CARD", "P3-LIST-SCREEN", "P3-EMPTY-STATES", "P3-SEAM-001", "P3-VITEST"]
  estimated_total_time: "2 days"

blockers: []

success_criteria:
  - "Run list renders all runs including 4 nested runs/runs/ runs"
  - "Filter tabs (verified/needs-review/failed/planned) function correctly from fixture"
  - "Trust panel renders per-check verification checklist from verification.yaml fixture; failing check deep-link renders clm_NNN anchor"
  - "Claim-status donut renders from evidence_bundle.counts data"
  - "All 9 optional entities show graceful empty-states (never errors) on scaffold-only fixture"
  - "OQ-7 schema-mismatch badge renders when schema_version_mismatch: true"
  - "Seam task P3-SEAM-001 passes: run list card → run detail navigation contract verified"
  - "Vitest tests green for list/filter/checklist"
  - "task-completion-validator P3 phase review passed"
---

# runs-frontend - Phase 3: Read Surfaces — Run List + Trust Panel

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/runs-frontend/phase-3-progress.md -t P3-LIST-CARD -s completed --force
```

---

## Objective

Build the two "direct adaptation" surfaces: the run list (adapted from IntentTree `WorkspaceRuns.tsx`) and the run overview trust panel (adapted from IntentTree `WorkflowViewerScreen` 4-panel layout). Two subagents work in parallel on disjoint component files but share the `useRunDetail()` hook and `RunDetailScreen.tsx` parent container.

---

## Parallel Execution Structure

- **Batch 1 (parallel)**: ui-engineer-enhanced (P3-LIST-CARD) ∥ frontend-developer (P3-TRUST-CHECKLIST, P3-TRUST-DONUT)
- **Batch 2 (parallel)**: ui-engineer-enhanced (P3-LIST-SCREEN, P3-SCHEMA-BADGE) ∥ frontend-developer (P3-TRUST-PANEL)
- **Sequential after both tracks**: P3-EMPTY-STATES → P3-SEAM-001 → P3-VITEST (all ui-engineer-enhanced)

## Integration Owner

`ui-engineer-enhanced` — owns `RunDetailScreen.tsx` (seam file) and `RunListScreen.tsx`. Resolves hook contract questions between tracks.

---

## Reviewer Gate

| Reviewer | Trigger | Blocks |
|----------|---------|--------|
| `task-completion-validator` | List + trust panel render from fixture; seam task passes | P4 start |
