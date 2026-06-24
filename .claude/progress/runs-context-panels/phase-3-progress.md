---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-context-panels"
feature_slug: "runs-context-panels"
prd_ref: "docs/project_plans/PRDs/features/runs-context-panels-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
execution_model: batch-parallel
phase: 3
title: "Frontend Context Panels"
status: pending
created: 2026-06-23
updated: 2026-06-23
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: on-track

total_tasks: 8
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["frontend-developer"]

model_usage:
  primary: "sonnet"
  external: []

tasks:
  # P3-scaffold: runs in parallel with P2 after P1 completes
  - id: "P3S-001"
    description: "Create 4 empty panel component files with prop types, empty-state render, and collapsed-by-default shell (stubs only — no real data rendering). Used for early type-checking while P2 runs."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P1-002"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  # P3 main batch: all 4 panels run in parallel after P2 + P3-scaffold
  - id: "P3-001"
    description: "Implement RoutingDecisionPanel.tsx: selected model profile, routing rationale, estimated cost vs budget, sensitivity tier. Collapsed by default. sessionStorage key rf:context-panel:${runId}:routing_decision. Empty-state for null prop (AC P2-R1)."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3S-001", "P2-005"]
    estimated_effort: "1 pt"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P3-002"
    description: "Implement ResearchBriefPanel.tsx: wrap existing ReportMarkdownRenderer for context.research_brief_md. Strip YAML frontmatter before passing to renderer. Collapsed by default. Empty-state for null prop (AC P2-R2)."
    status: pending
    assigned_to: ["frontend-developer"]
    dependencies: ["P3S-001", "P2-005"]
    estimated_effort: "1 pt"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P3-003"
    description: "Implement SwarmPlanPanel.tsx: two-level collapsible list tree (adapters → steps), cost columns, 3-level depth cap, raw-YAML 'Show raw' escape hatch for unrecognized shapes. SwarmPlanNode type per OQ-3. Empty-state for null prop (AC P2-R3)."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3S-001", "P2-005"]
    estimated_effort: "2 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P3-004"
    description: "Implement UpstreamEntitiesPanel.tsx: render intent_id, ibom_id, intenttree_node_id as styled badge links (online) or plain-text badges with tooltip (offline). Best-effort service ping; never blocks render. Empty-state for null prop (AC P2-R4)."
    status: pending
    assigned_to: ["frontend-developer"]
    dependencies: ["P3S-001", "P2-005"]
    estimated_effort: "1 pt"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P3-005"
    description: "Wire all 4 panels into RunDetailWorkspace.tsx. Each panel receives context.* field via optional chaining (no hard destructuring). Order: Routing Decision, Research Brief, Swarm Plan, Upstream Entities. sessionStorage collapse state per run+panel."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-001", "P3-002", "P3-003", "P3-004"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "P3-006"
    description: "Add schema_version guard in frontend: schema_version >= 1.3 → panels active; lower/absent → all panels show 'Context not available for this run' empty-state. No regressions in existing 1.2 consumers."
    status: pending
    assigned_to: ["frontend-developer"]
    dependencies: ["P3-005"]
    estimated_effort: "0.5 pts"
    priority: high
    assigned_model: sonnet
    model_effort: adaptive

  - id: "TEST-SMOKE"
    description: "Runtime smoke across all 4 panel surfaces: (1) fully populated context run; (2) pre-1.3 context-absent run (context: null) — all panels empty-state, no JS errors; (3) offline static build — SPA built without rf serve, panels functional from run.json alone."
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3-006"]
    estimated_effort: "0.5 pts"
    priority: critical
    assigned_model: sonnet
    model_effort: adaptive

parallelization:
  # P3S-001 runs parallel to P2 (after P1)
  batch_1: ["P3S-001"]
  # After P2-005: 4 panels run in parallel
  batch_2: ["P3-001", "P3-002", "P3-003", "P3-004"]
  batch_3: ["P3-005"]
  batch_4: ["P3-006"]
  batch_5: ["TEST-SMOKE"]
  critical_path: ["P3S-001", "P3-003", "P3-005", "P3-006", "TEST-SMOKE"]
  estimated_total_time: "3-4 days"

blockers: []

success_criteria:
  - id: "SC-P3-1"
    description: "P3S-001 panel shells in place before P2 completes (∥ P2 execution)"
    status: pending
  - id: "SC-P3-2"
    description: "All 4 panel components implemented (P3-001 through P3-004)"
    status: pending
  - id: "SC-P3-3"
    description: "RunDetailWorkspace wired (P3-005); no hard destructuring of context"
    status: pending
  - id: "SC-P3-4"
    description: "Schema version guard implemented (P3-006)"
    status: pending
  - id: "SC-P3-5"
    description: "tsc --noEmit passes across all new .tsx files"
    status: pending
  - id: "SC-P3-6"
    description: "FE-002 through FE-006 unit tests pass"
    status: pending
  - id: "SC-P3-7"
    description: "TEST-SMOKE runtime smoke passes (all 3 scenarios including offline build and pre-1.3 run)"
    status: pending
  - id: "SC-P3-8"
    description: "karen milestone review PASS (mid-feature gate)"
    status: pending
  - id: "SC-P3-9"
    description: "task-completion-validator sign-off"
    status: pending

files_modified:
  - "src/runs_viewer/components/RunDetail/RoutingDecisionPanel.tsx"
  - "src/runs_viewer/components/RunDetail/ResearchBriefPanel.tsx"
  - "src/runs_viewer/components/RunDetail/SwarmPlanPanel.tsx"
  - "src/runs_viewer/components/RunDetail/UpstreamEntitiesPanel.tsx"
  - "src/runs_viewer/components/RunDetail/RunDetailWorkspace.tsx"
---

# runs-context-panels - Phase 3: Frontend Context Panels

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/runs-context-panels/phase-3-progress.md -t P3-001 -s completed
```

---

## Objective

Build 4 collapsed, read-only context panels in the runs-viewer run-detail view, feeding from `context.*` fields in `run.json`. All panels degrade gracefully to empty-state when their backing field is null. Offline static-export invariant must be preserved throughout.

---

## Implementation Notes

### Architectural Decisions

- **P3S-001 ∥ P2**: FE panel shells scaffold off P1 TS types while P2 export wiring executes. Integration testing (real data flow) waits for P2-005 serialization barrier verification.
- **4-panel parallel batch** (P3-001 through P3-004): Each panel owns an independent file; execute as a single parallel batch after P2-005 clears.
- **sessionStorage key scheme**: `rf:context-panel:${runId}:${panelId}` where `panelId` ∈ `{routing_decision, research_brief, swarm_plan, upstream_entities}`. Panels reset to collapsed on page reload.
- **karen milestone review** required at P3 exit (mid-feature gate) before P4 can start.

### Patterns and Best Practices

- `ResearchBriefPanel` reuses the existing `ReportMarkdownRenderer` — no new renderer code.
- `SwarmPlanPanel` implements a new lighter list-based tree component (no code import from MeatyWiki). Reference visual: lineage-graph collapsible component.
- `UpstreamEntitiesPanel` service ping is best-effort only; render must never block on it.
- Use optional chaining throughout (`run.context?.routing_decision`); hard destructuring of `context` is forbidden.

### Known Gotchas

- Frontmatter stripping in `ResearchBriefPanel`: unit test fixture must include YAML frontmatter to verify strip-before-render.
- `SwarmPlanPanel` raw-YAML escape hatch is required for shapes beyond the typed 2-level tree.
- Schema version guard (P3-006) must not break existing 1.2 consumers in `RunListView`, `ClaimLedgerView`, `GovernanceBlock`, `ReportOverlay`.

---

## Completion Notes

_(Fill when phase complete)_
