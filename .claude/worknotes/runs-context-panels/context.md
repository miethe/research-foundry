---
type: context
schema_version: 2
doc_type: context
prd: "runs-context-panels"
feature_slug: "runs-context-panels"
title: "Run Context Panels - Development Context"
status: active
created: 2026-06-23
updated: 2026-06-23
prd_ref: "docs/project_plans/PRDs/features/runs-context-panels-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
commit_refs: []
pr_refs: []

critical_notes_count: 0
implementation_decisions_count: 5
active_gotchas_count: 0
agent_contributors: []
agents: []

phase_status:
  - phase: 1
    status: pending
    reason: null
  - phase: 2
    status: pending
    reason: null
  - phase: 3
    status: pending
    reason: null
  - phase: 4
    status: pending
    reason: null

blockers: []

decisions:
  - id: "OQ-1"
    question: "Where does context data live — embedded in run.json or fetched lazily?"
    decision: "Embed context in run.json at export time (Option A). RESOLVED — do not reopen."
    rationale: "runs-viewer is a static export SPA that must work offline. Embedding keeps sensitivity redaction in a single deterministic export-time pass and keeps the viewer self-contained."
    tradeoffs: "Lazy-load via loopback API deferred to v2 (DFR-001) — revisit only if run.json median size exceeds 500 KB."
    location: "src/research_foundry/services/export_service.py"
    phase: 1

  - id: "OQ-2"
    question: "How should panel collapse-state persist across navigations?"
    decision: "sessionStorage keyed by rf:context-panel:${runId}:${panelId}. Panels reset to collapsed on page reload."
    rationale: "Survives navigate-to-list → navigate-back-to-run within session; no cross-session persistence required."
    tradeoffs: "Clearing sessionStorage resets all panels to collapsed."
    location: "src/runs_viewer/components/RunDetail/RunDetailWorkspace.tsx"
    phase: 3

  - id: "OQ-3"
    question: "How to represent swarm_plan.yaml in the UI?"
    decision: "Two-level typed tree (SwarmPlanNode: { id, label, steps?: SwarmStep[] }); raw-YAML 'Show raw' escape hatch for unrecognized shapes; depth cap 3 levels."
    rationale: "swarm_plan.yaml has a stable enough top-level shape for typing; escape hatch handles variation without failing."
    tradeoffs: "New lighter list-based tree component (no code import from MeatyWiki); lineage-graph collapsible is the visual reference."
    location: "src/runs_viewer/components/RunDetail/SwarmPlanPanel.tsx"
    phase: 3

  - id: "OQ-4"
    question: "Should Phase 3 be split into P3a and P3b?"
    decision: "NOT required. Phase 3 stays unified (6 pts, 4 parallel panel files)."
    rationale: "Plan file stays under 800 lines with unified structure. Panels batched in parallel by file ownership within P3."
    tradeoffs: "None — the parallel batch within P3 achieves the same concurrency."
    location: "docs/project_plans/implementation_plans/features/runs-context-panels-v1.md"
    phase: 1

  - id: "OQ-5"
    question: "What redaction policy applies to context.* fields?"
    decision: "Reuse existing R9 sensitivity rules with one field-specific extension: context.research_brief_md source URLs and text tagged sensitivity: work_sensitive or higher are also redacted."
    rationale: "No entirely new rule set required; implementation owner verifies against current policy doc in P2."
    tradeoffs: "Minimal scope extension limits risk of policy drift."
    location: "src/research_foundry/services/export_service.py"
    phase: 2

gotchas: []

modified_files: []
---

# Run Context Panels - Development Context

**Status**: Pending (not yet started)
**Created**: 2026-06-23

> Shared worknotes for all agents working on runs-context-panels (FR-14). Add observations, decisions, gotchas, and handoff notes here. YAML frontmatter is the source of truth for structured data.

---

## Quick Reference

| Artifact | Path |
|----------|------|
| PRD | `docs/project_plans/PRDs/features/runs-context-panels-v1.md` |
| Implementation Plan | `docs/project_plans/implementation_plans/features/runs-context-panels-v1.md` |
| Design Spec | `docs/project_plans/design-specs/runs-context-panels.md` |
| Decisions Block | `.claude/worknotes/runs-context-panels/decisions-block.md` |
| Human Brief | `docs/project_plans/human-briefs/runs-context-panels.md` |
| Schema Doc | `docs/dev/architecture/rf-run-export-schema.md` |
| P1 Progress | `.claude/progress/runs-context-panels/phase-1-progress.md` |
| P2 Progress | `.claude/progress/runs-context-panels/phase-2-progress.md` |
| P3 Progress | `.claude/progress/runs-context-panels/phase-3-progress.md` |
| P4 Progress | `.claude/progress/runs-context-panels/phase-4-progress.md` |

---

## Feature Goal

Implement FR-14: 4 collapsed, read-only context panels in the runs-viewer run-detail view (Routing Decision, Research Brief, Swarm Plan, Upstream Entities), feeding from an additive `context` key embedded in `run.json` at export time. Schema bumps 1.2 → 1.3. No new tables, no CRUD endpoints, no loopback API calls in v1.

---

## Phase Summary

| Phase | Title | Owner(s) | Hard Gate |
|-------|-------|----------|-----------|
| P1 | Schema & Contract (3 pts) | python-backend-engineer, data-layer-expert | backend-architect re-review APPROVED |
| P2 | Export Wiring & Redaction (4 pts) | python-backend-engineer | P2-005 serialization barrier + task-completion-validator |
| P3 | Frontend Context Panels (6 pts) | ui-engineer-enhanced, frontend-developer | karen milestone review PASS |
| P4 | Tests, Docs & Validation (2 pts) | python-backend-engineer, ui-engineer-enhanced, documentation-writer, changelog-generator | karen feature-end gate PASS |

**Critical path**: P1 → P2 → P3 → P4. P3-scaffold (∥ P2) and 4-panel parallel batch within P3 are the key parallelism opportunities.

---

## Resolved Decisions (OQ-1 through OQ-5)

All 5 open questions from the planning phase are resolved. See `decisions:` block in YAML frontmatter above for full rationale. Key constraint: **OQ-1 is frozen — do not reopen**. `context` is embedded in `run.json` at export time (v1); lazy-load is DFR-001 deferred to v2.

---

## Open Items

- **DFR-001** (P4 deliverable): Author `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md` with `maturity: shaping`. Required before P4 can be sealed.
- **ibom_id / intenttree_node_id** presence in `run.yaml`: Verify before P2-001 implementation. If absent, `UpstreamEntitiesPanel` degrades to `intent_id`-only display without erroring.
- **Run.json size baseline**: Record median size after first P2 export run — establishes the DFR-001 trigger threshold baseline.

---

## Implementation Notes

_(Agents: add observations below as development proceeds)_
