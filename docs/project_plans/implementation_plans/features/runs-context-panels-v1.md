---
schema_version: 2
doc_type: implementation_plan
title: "Implementation Plan: Runs Viewer — Run Context Panels (FR-14)"
status: draft
created: 2026-06-23
updated: 2026-06-23
feature_slug: runs-context-panels
feature_version: "v1"
prd_ref: docs/project_plans/PRDs/features/runs-context-panels-v1.md
plan_ref: null
scope: "Additive context block in run.json (1.2→1.3), export wiring for 4 source artifacts, 4 read-only collapsed panels in the run-detail view, export-time redaction extension, and schema/CHANGELOG docs."
effort_estimate: "~15 pts"
architecture_summary: "Static-export SPA feature: schema contract → export producer → FE consumer. No new tables, no CRUD endpoints. Backend adds _build_context() to export_service.py; FE adds 4 collapsed panel components to RunDetailWorkspace."
related_documents:
  - docs/project_plans/PRDs/features/runs-context-panels-v1.md
  - docs/project_plans/design-specs/runs-context-panels.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/PRDs/features/runs-frontend-v1.md
  - docs/project_plans/PRDs/features/runs-loopback-api-v1.md
  - .claude/worknotes/runs-context-panels/decisions-block.md
references:
  user_docs: []
  context: []
  specs: []
  related_prds:
    - docs/project_plans/PRDs/features/runs-frontend-v1.md
    - docs/project_plans/PRDs/features/runs-loopback-api-v1.md
spike_ref: null
adr_refs: []
deferred_items_spec_refs: []
findings_doc_ref: null
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: medium
risk_level: medium
category: features
tags: [implementation, runs-viewer, context-panels, schema, fr-14]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/export_service.py
  - src/research_foundry/schemas/run_export.py
  - src/runs_viewer/components/RunDetail/RoutingDecisionPanel.tsx
  - src/runs_viewer/components/RunDetail/ResearchBriefPanel.tsx
  - src/runs_viewer/components/RunDetail/SwarmPlanPanel.tsx
  - src/runs_viewer/components/RunDetail/UpstreamEntitiesPanel.tsx
  - src/runs_viewer/components/RunDetail/RunDetailWorkspace.tsx
  - src/runs_viewer/types/run.ts
  - docs/dev/architecture/rf-run-export-schema.md
  - CHANGELOG.md
wave_plan:
  serialization_barriers:
    - src/runs_viewer/types/run.ts
    - src/research_foundry/schemas/run_export.py
  phases:
    - id: P1
      depends_on: []
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - src/research_foundry/schemas/run_export.py
        - src/runs_viewer/types/run.ts
        - docs/dev/architecture/rf-run-export-schema.md
    - id: P2
      depends_on: [P1]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - src/research_foundry/services/export_service.py
    - id: P3_scaffold
      depends_on: [P1]
      isolation: shared
      parallelizable: true
      owner_skills: []
      files_affected:
        - src/runs_viewer/types/run.ts
    - id: P3
      depends_on: [P2, P3_scaffold]
      isolation: shared
      parallelizable: true
      owner_skills: []
      files_affected:
        - src/runs_viewer/components/RunDetail/RoutingDecisionPanel.tsx
        - src/runs_viewer/components/RunDetail/ResearchBriefPanel.tsx
        - src/runs_viewer/components/RunDetail/SwarmPlanPanel.tsx
        - src/runs_viewer/components/RunDetail/UpstreamEntitiesPanel.tsx
        - src/runs_viewer/components/RunDetail/RunDetailWorkspace.tsx
    - id: P4
      depends_on: [P3]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - docs/dev/architecture/rf-run-export-schema.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2, P3_scaffold]
    - [P3]
    - [P4]
---

# Implementation Plan: Runs Viewer — Run Context Panels (FR-14)

**Plan ID**: `IMPL-2026-06-23-RUNS-CONTEXT-PANELS`
**Date**: 2026-06-23
**Author**: Implementation Planner (sonnet) — scaffolded from Opus decisions block
**Human Brief**: `docs/project_plans/human-briefs/runs-context-panels.md`
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/runs-context-panels-v1.md`
- **Design Spec**: `docs/project_plans/design-specs/runs-context-panels.md`
- **Frozen Schema Contract**: `docs/dev/architecture/rf-run-export-schema.md`
- **Decisions Block**: `.claude/worknotes/runs-context-panels/decisions-block.md`

**Complexity**: Large (Tier-3-lite, 15 pts, 4 phases)
**Total Estimated Effort**: ~15 story points
**Target Timeline**: 2–3 weeks

---

## Executive Summary

This plan implements FR-14 (Run Context Panels) as four collapsed, read-only panels in the runs-viewer run-detail view, feeding from an additive `context` key embedded in `run.json` at export time. The delivery follows a strict **contract → producer → consumer** sequence: Phase 1 freezes the `context` schema shape and TypeScript types under backend-architect governance review; Phase 2 wires the export service to populate `context` from on-disk YAML/Markdown artifacts and extends the existing sensitivity redaction pass; Phase 3 builds the four frontend panels consuming `context.*` fields with full offline resilience; Phase 4 hardens tests, finalizes schema documentation, adds the CHANGELOG entry, and passes `karen` feature-end review.

A parallel slice is available: FE type-scaffolding (from P1 TS types) may start while P2 export wiring executes. The four P3 panels are fully parallel by file ownership. ICA free-tier delegation is recommended for the bounded P2 and P4 test-authoring waves to cost-shift. All authoritative gates (pytest, tsc, backend-architect, karen) run in-session.

**Success criteria**: All four panels render correctly from real exported `context`; every panel independently degrades to an empty-state when its backing field is null; `rf run export --json` emits schema 1.3; backend-architect re-review approved; karen feature-end gate passes.

---

## Implementation Strategy

### Architecture Sequence

Research Foundry is a file-backed control plane. This feature follows the export-then-consume pattern — no database layer, no API layer, no CRUD endpoints:

1. **Schema & Contract (P1)** — Freeze `context` shape in Python schema + TypeScript types; update schema doc stub; governance gate
2. **Export Producer (P2)** — Wire `export_service.py` to populate `context` from `routing_decision.yaml`, `research_brief.md`, `swarm_plan.yaml`, and upstream entity IDs; extend R9 redaction
3. **Frontend Consumer (P3)** — Four collapsed panel components in `RunDetailWorkspace`; reuse existing MD renderer and lineage-tree pattern; per-panel resilience
4. **Tests, Docs & Validation (P4)** — Test hardening, schema-doc finalize, CHANGELOG, deferred-items DOC-006, karen feature-end gate

### Design Decisions (OQ Resolutions)

**OQ-1 — RESOLVED: Embed `context` in `run.json` at export time (Option A).**
The runs-viewer is a static export SPA that must work offline. Embedding keeps sensitivity redaction in a single deterministic export-time pass and keeps the viewer self-contained. Lazy-load via the loopback API is deferred to v2, to be reconsidered only if `run.json` size becomes a measured problem. Do not reopen.

**OQ-2 — Collapse-state persistence: `sessionStorage` keyed by `${run_id}:${panel_id}`.**
Panels are collapsed by default on first page load for a given run. State persists for the browser session (survives navigate-to-list → navigate-back-to-run). On page reload, panels reset to collapsed. The `sessionStorage` key scheme is: `rf:context-panel:${runId}:${panelId}` where `panelId` ∈ `{routing_decision, research_brief, swarm_plan, upstream_entities}`. No cross-session persistence required. Reset semantics: clearing `sessionStorage` resets all panels to collapsed.

**OQ-3 — Swarm plan representation: two-level typed tree; `Record<string,unknown>` escape hatch.**
`swarm_plan.yaml` is treated as having a stable enough top-level shape (adapters list with step sub-arrays) to define a typed `SwarmPlanNode` interface (`{ id: string; label: string; steps?: SwarmStep[] }`). For unrecognized shapes beyond two levels, a raw-YAML collapsible escape hatch ("Show raw") is provided. Tree render depth is capped at 3 levels (adapter → step → sub-step). The lineage-graph collapsible component is the visual reference; a new lighter list-based tree component is implemented (no code import from MeatyWiki).

**OQ-4 — P3 split: NOT required.**
Phase 3 stays as a single phase (6 pts, 4 parallel panel files). The plan file remains under 800 lines with unified structure. Panels are batched in parallel by file ownership within P3.

**OQ-5 — Redaction policy: reuse existing R9 sensitivity rules with one field-specific extension.**
`context.*` fields (routing_decision, swarm_plan) reuse the existing run.json sensitivity rules from `export_service.py`. The one extension: `context.research_brief_md` source URLs and any text tagged `sensitivity: work_sensitive` or higher are also subject to redaction. No entirely new rule set is required. Decision recorded; implementation owner verifies against the current policy doc in P2.

### Parallel Work Opportunities

- **P3-scaffold ∥ P2 export wiring**: FE stubs panel component shells against P1's TS types while P2 wires the backend producer. Integration testing (real data flow) waits for P2 completion.
- **4-panel parallel batch within P3**: `RoutingDecisionPanel`, `ResearchBriefPanel`, `SwarmPlanPanel`, `UpstreamEntitiesPanel` are independent files → execute in a single parallel batch.
- **Within P1**: Schema-doc stub ∥ Python schema + TS type definitions (different files).

### Critical Path

P1 (schema + governance gate) → P2 (export wiring) → P3 (FE integration) → P4 (karen gate)

Bottleneck: P1 backend-architect re-review. Initiate early with the `context` field contract from the design spec in the review request.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| P1 | Schema & Contract | 3 pts | python-backend-engineer, data-layer-expert | sonnet | Exit gate: backend-architect re-review APPROVED (extended) |
| P2 | Export Wiring & Redaction | 4 pts | python-backend-engineer | sonnet | ICA free-tier candidate wave |
| P3 | FE Context Panels | 6 pts | ui-engineer-enhanced, frontend-developer | sonnet | 4-panel parallel batch; P3-scaffold ∥ P2 |
| P4 | Tests, Docs & Validation | 2 pts | python-backend-engineer, ui-engineer-enhanced, documentation-writer, changelog-generator | sonnet / haiku / opus | ICA free-tier for test authoring; karen feature-end (opus/extended) |
| **Total** | — | **15 pts** | — | — | — |

---

## Deferred Items & In-Flight Findings Policy

### Deferred Items

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-----------------|
| DFR-001 | backlog | OQ-1: Lazy-load optimization via loopback API — deferred to v2. Embed is the v1 delivery; lazy-load would be an additive enhancement once `run.json` size becomes a measured problem. | `run.json` median size exceeds 500 KB, or operator feedback requests live-refresh of context data | `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md` |

**Rule**: DOC-006 in P4 must author the design spec for DFR-001 before P4 can be sealed.

### In-Flight Findings

Lazy-creation rule applies. Create `.claude/findings/runs-context-panels-findings.md` only on the first real finding during execution. Update `findings_doc_ref` in frontmatter at that point.

### Quality Gate

P4 cannot be sealed until:
- `deferred_items_spec_refs` contains the path for DFR-001 design spec
- `findings_doc_ref` is null OR findings doc is finalized and status is `accepted`

---

## Phase Breakdown

**Column conventions**:
- `Estimate` — Story points
- `Model` — `sonnet` | `haiku` | `opus`
- `Effort` — Reasoning budget: `adaptive` (default) or `extended` (high-stakes tasks)

---

### Phase 1: Schema & Contract

**Duration**: 2–3 days
**Dependencies**: None
**Entry Criteria**: Design spec `docs/project_plans/design-specs/runs-context-panels.md` reviewed; decisions-block OQ-1 resolved (embed)
**Exit Gate**: **backend-architect re-review APPROVED** (frozen-schema policy) — recorded approval in PR before any P2 work begins
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert; backend-architect (mandatory re-review)

**karen checkpoint**: Not required at P1 exit (task-completion-validator per-phase is sufficient here).

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P1-001 | Python schema extension | Extend `run_export.py` (or equivalent schema module) with `RunContext` dataclass/TypedDict containing 4 sub-objects: `routing_decision: dict | None`, `research_brief_md: str | None`, `swarm_plan: dict | None`, `upstream_entities: dict | None`. Bump schema_version constant to `"1.3"`. | `RunContext` type defined; `RunExport` gains `context: RunContext \| None` field; schema_version `"1.3"` in Python constant; existing `RunExport` fields unchanged | 1 pt | python-backend-engineer | sonnet | adaptive | None |
| P1-002 | TypeScript type definitions | Define `RunContext` TypeScript interface in `src/runs_viewer/types/run.ts` with 4 optional nullable sub-types: `RoutingDecision`, `ResearchBriefMd` (string alias), `SwarmPlan` (with `SwarmPlanNode` typed tree), `UpstreamEntities`. Extend `RunExport` with `context?: RunContext \| null`. | TS types compile without errors (`npx tsc --noEmit`); `RunExport.context` is optional+nullable; no existing type fields modified | 1 pt | python-backend-engineer | sonnet | adaptive | P1-001 |
| P1-003 | Schema doc stub update | Update `docs/dev/architecture/rf-run-export-schema.md` §9 (existing `context` stub) with the finalized v1.3 `context` field contract: field names, types, nullability, source artifact per field, graceful-degradation contract. Add a changelog row for v1.3. This is a stub — full documentation finalized in P4. | §9 reflects the finalized shape; changelog row present; doc compiles (no broken internal links) | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-001 |
| P1-004 | Backward-compat assertion | Add a regression test fixture using a schema 1.2 `run.json` (no `context` key). Assert that all existing consumer code paths (`RunListView`, `ClaimLedgerView`, `GovernanceBlock`, `ReportOverlay`) load without errors when `context` is absent. | Test passes; no `context` access error in existing consumers with 1.2 fixture | 0.5 pts | python-backend-engineer | sonnet | adaptive | P1-002 |
| P1-005 | backend-architect re-review gate | Submit the frozen-schema bump (schema 1.2 → 1.3, additive `context` field) for backend-architect re-review per frozen-schema policy. Provide: field contract from §9, additive+optional access proof (backward-compat assertion from P1-004), and rationale from decisions-block OQ-1. Record approval. | backend-architect approval recorded in PR (or review note); schema frozen for P2 | — | backend-architect | sonnet | extended | P1-003, P1-004 |

#### AC P1-A: Schema 1.3 backward compatibility

```markdown
#### AC P1-A: Schema 1.3 backward compatibility
- target_surfaces:
    - src/research_foundry/schemas/run_export.py
    - src/runs_viewer/types/run.ts
    - src/runs_viewer/components/RunDetail/RunListView.tsx (or equivalent)
    - src/runs_viewer/components/RunDetail/ClaimLedgerView.tsx (or equivalent)
    - src/runs_viewer/components/RunDetail/GovernanceBlock.tsx (or equivalent)
- propagation_contract: `context` field is typed as `RunContext | null` in both Python and TypeScript; consumers use optional chaining for all `context.*` access; hard destructuring of `context` is forbidden.
- resilience: When schema_version is "1.2" or lower, `context` key is absent; existing components continue to function unchanged.
- visual_evidence_required: false
- verified_by: [P1-004 backward-compat regression test]
```

**Phase 1 Quality Gates:**
- [ ] Python `RunContext` type defined; `RunExport` gains optional `context` field
- [ ] TypeScript `RunContext` interface defined; `tsc --noEmit` passes
- [ ] Schema doc §9 updated with v1.3 contract stub
- [ ] Backward-compat regression test passes with 1.2 fixture
- [ ] **backend-architect re-review APPROVED** (hard gate — P2 cannot start without this)
- [ ] `task-completion-validator` sign-off

---

### Phase 2: Export Wiring & Redaction

**Duration**: 2–3 days
**Dependencies**: P1 complete (backend-architect gate APPROVED)
**Entry Criteria**: P1 exit gate cleared; `context` shape frozen
**Exit Gate**: Export tests pass including redaction + missing-field cases; serialization barrier verified (P1 TS types unchanged)
**Assigned Subagent(s)**: python-backend-engineer
**ICA delegation note**: This phase is a bounded, well-specified, mechanical wave → ICA free-tier candidate (`~/ica-claude.sh`, sonnet-4-6[1m]). Keep P1 + P3 on native agents. Re-run authoritative pytest + backward-compat assertion in-session after ICA completes.

**karen checkpoint**: Not required at P2 exit (task-completion-validator per-phase).

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P2-001 | `_build_context()` helper | Add `_build_context(run_paths: RunPaths) -> dict \| None` to `export_service.py`. Reads: `routing_decision.yaml` → `context.routing_decision`; `research_brief.md` verbatim → `context.research_brief_md`; `swarm_plan.yaml` → `context.swarm_plan`; upstream entity IDs from `run.yaml` (`ibom_id`, `intenttree_node_id`) + existing `intent_id` → `context.upstream_entities`. All reads via `RunPaths` (no stored absolute paths). Returns `None` when all source artifacts are absent. | `_build_context()` returns correct dict with all 4 sub-objects from fixture; returns `None` when all artifacts absent; no stored absolute paths; no LLM calls in code path | 2 pts | python-backend-engineer | sonnet | adaptive | P1-005 |
| P2-002 | Null-fill semantics | Each absent artifact sets its corresponding `context.*` field to `null` (not omitted, not an empty object). When any artifact is absent, its field is `null`; when all are absent, `context` itself is `null`. | Unit test BE-002: each artifact absent independently → corresponding field is `null`, others populated; all absent → `context` is `null` | 0.5 pts | python-backend-engineer | sonnet | adaptive | P2-001 |
| P2-003 | R9 redaction extension | Extend the existing export-time R9 sensitivity redaction pass in `export_service.py` to cover `context.routing_decision` and `context.swarm_plan` (text fields that may carry governed content). Also extend to `context.research_brief_md` source URLs and text tagged `sensitivity: work_sensitive` or higher. Reuses existing sensitivity rules + one field-specific extension (per OQ-5 resolution). | Unit test BE-003: `routing_decision.yaml` with `sensitivity: work_sensitive` content → exported `context.routing_decision` has `[redacted:sensitivity]` in place; same for swarm_plan and research_brief_md | 1 pt | python-backend-engineer | sonnet | adaptive | P2-001 |
| P2-004 | Export pipeline integration | Wire `_build_context()` into the main export pipeline in `export_service.py` so that `run.json` emits `"context": {...} \| null` as a top-level key at export time. Verify: `rf run export --json` on a test fixture run emits schema 1.3 with populated+redacted `context`. | Integration test: full export pipeline with realistic run fixture; `context` block present; schema_version `"1.3"`; structured errors on stderr for missing artifacts (not uncaught exceptions); `run.json` consumers with 1.2 fixture still pass (backward-compat) | 0.5 pts | python-backend-engineer | sonnet | adaptive | P2-003 |

#### P2→P3 Seam Task (R-P3 Integration Owner)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P2-005 | Serialization barrier verification | ui-engineer-enhanced (integration_owner) verifies the `context.*` propagation contract from `run.json` into each of the 4 panel `target_surfaces`. Confirm: exported `run.json` `context` structure matches TS `RunContext` type exactly; each panel prop type aligns with its backing field. Resolve any type-shape mismatches before FE integration tests run. | No TypeScript type errors in panel components receiving `context.*` props; `RunContext` Python dict keys match TS interface keys 1:1; mismatch report or "verified: no mismatches" recorded | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P2-004, P1-002 |

**integration_owner**: `ui-engineer-enhanced` owns this seam verification task (R-P3 compliance).

#### R-P2 Resilience ACs: FE handles missing `context.<field>`

These ACs are mandated by Plan Generator Rule R-P2 — one per `context.*` sub-object.

```markdown
#### AC P2-R1: FE handles missing `context.routing_decision`
- target_surfaces:
    - src/runs_viewer/components/RunDetail/RoutingDecisionPanel.tsx
- propagation_contract: Panel receives `routingDecision: RoutingDecision | null | undefined` prop from RunDetailWorkspace.
- resilience: When prop is null or undefined, panel renders "Routing decision not available for this run" empty-state. No JS error. No blank element.
- visual_evidence_required: false
- verified_by: [FE-001 unit test: RoutingDecisionPanel with null prop]

#### AC P2-R2: FE handles missing `context.research_brief_md`
- target_surfaces:
    - src/runs_viewer/components/RunDetail/ResearchBriefPanel.tsx
- propagation_contract: Panel receives `researchBriefMd: string | null | undefined` prop.
- resilience: When prop is null or undefined, panel renders "Research brief not available for this run" empty-state. No JS error.
- visual_evidence_required: false
- verified_by: [FE-001 unit test: ResearchBriefPanel with null prop]

#### AC P2-R3: FE handles missing `context.swarm_plan`
- target_surfaces:
    - src/runs_viewer/components/RunDetail/SwarmPlanPanel.tsx
- propagation_contract: Panel receives `swarmPlan: SwarmPlan | null | undefined` prop.
- resilience: When prop is null or undefined, panel renders "Swarm plan not available for this run" empty-state. No JS error.
- visual_evidence_required: false
- verified_by: [FE-001 unit test: SwarmPlanPanel with null prop]

#### AC P2-R4: FE handles missing `context.upstream_entities`
- target_surfaces:
    - src/runs_viewer/components/RunDetail/UpstreamEntitiesPanel.tsx
- propagation_contract: Panel receives `upstreamEntities: UpstreamEntities | null | undefined` prop.
- resilience: When prop is null or undefined, panel renders "No upstream entities for this run" empty-state. No JS error.
- visual_evidence_required: false
- verified_by: [FE-001 unit test: UpstreamEntitiesPanel with null prop]
```

**Phase 2 Quality Gates:**
- [ ] `_build_context()` helper implemented and tested (all-present, each-absent-independently cases)
- [ ] Null-fill semantics verified (absent field → `null`, not omitted)
- [ ] R9 redaction extended to `context.*`; redaction unit test passes
- [ ] Export pipeline integration test passes; `run.json` emits schema 1.3
- [ ] Export errors emit to stderr as structured JSON lines (not uncaught exceptions)
- [ ] Serialization barrier verification (P2-005) complete — no type-shape mismatches
- [ ] `task-completion-validator` sign-off

---

### Phase 3: Frontend Context Panels

**Duration**: 3–4 days
**Dependencies**: P2 complete (export wiring); P3-scaffold (TS types from P1) may start in parallel with P2
**Entry Criteria**: P2 exit gate cleared; serialization barrier verified (P2-005); TS types from P1 available
**Exit Gate**: Runtime smoke task (TEST-SMOKE) passes across all 4 `target_surfaces` including pre-1.3 context-absent run and offline build; FE component tests pass
**Assigned Subagent(s)**: ui-engineer-enhanced (primary), frontend-developer (secondary)

**karen checkpoint**: karen milestone review after P3 exit — mid-feature gate before P4.

**Parallel batch**: Tasks P3-001 through P3-004 execute in parallel (independent files). P3-005 (RunDetailWorkspace wiring) depends on all four. P3-006 (collapse-state) depends on P3-005.

#### P3-scaffold (∥ P2, starts after P1)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3S-001 | Panel component shells | Create 4 empty panel component files with prop types, empty-state render, and collapsed-by-default shell. No real data rendering yet — stubs only. Used for early type-checking while P2 runs. | 4 `.tsx` files exist; each compiles against P1 TS types; each renders empty-state for null prop | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P1-002 |

#### P3 main batch (after P2 + P3-scaffold)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-001 | RoutingDecisionPanel | Implement `RoutingDecisionPanel.tsx`. Renders: selected model profile name, routing rationale text, estimated cost vs budget, sensitivity tier at routing time. Collapses by default; uses `sessionStorage` key `rf:context-panel:${runId}:routing_decision`. Shows empty-state for null prop (AC P2-R1). | All fields render from populated fixture; empty-state renders for null prop; sessionStorage key correct; unit test FE-002 passes | 1 pt | ui-engineer-enhanced | sonnet | adaptive | P3S-001, P2-005 |
| P3-002 | ResearchBriefPanel | Implement `ResearchBriefPanel.tsx`. Wraps existing `ReportMarkdownRenderer` (or equivalent) component for `context.research_brief_md`. Strips YAML frontmatter before passing to renderer. Collapses by default. Shows empty-state for null prop (AC P2-R2). | Markdown renders from string fixture (including frontmatter strip); empty-state for null; reuses existing renderer with no new renderer code; unit test FE-003 passes | 1 pt | frontend-developer | sonnet | adaptive | P3S-001, P2-005 |
| P3-003 | SwarmPlanPanel | Implement `SwarmPlanPanel.tsx`. Two-level collapsible list tree: adapters at top level, steps within each adapter, with estimated and actual cost columns where available. Render depth cap: 3 levels. Raw-YAML "Show raw" escape hatch for unrecognized shapes. `SwarmPlanNode` type per OQ-3 resolution. Collapses by default. Shows empty-state for null prop (AC P2-R3). | Two-level tree renders from typed `SwarmPlan` fixture; raw-YAML fallback renders for unknown shapes; empty-state for null; unit test FE-004 passes | 2 pts | ui-engineer-enhanced | sonnet | adaptive | P3S-001, P2-005 |
| P3-004 | UpstreamEntitiesPanel | Implement `UpstreamEntitiesPanel.tsx`. Renders `intent_id`, `ibom_id`, `intenttree_node_id` as styled badge links (navigable when services reachable) or plain-text badge with tooltip when offline. Best-effort service reachability ping; never blocks panel render. Shows empty-state for null prop (AC P2-R4). | All 3 IDs render as links in online fixture; plain-text badges in offline fixture; service ping failure never blocks render; empty-state for null; unit test FE-005 passes | 1 pt | frontend-developer | sonnet | adaptive | P3S-001, P2-005 |
| P3-005 | RunDetailWorkspace wiring | Add all four panels to `RunDetailWorkspace.tsx`. Each panel receives its backing `context.*` field as a prop (optional chaining from `run.context`). No hard destructuring of `context`. Wire collapse state via `sessionStorage` with per-run-per-panel keys. Order: Routing Decision, Research Brief, Swarm Plan, Upstream Entities. | All 4 panels appear in run-detail; all panels collapsed by default on load; collapse state persists within session; no hard destructuring of `context`; integration test FE-006 passes | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3-001, P3-002, P3-003, P3-004 |
| P3-006 | Schema version guard | Add a `schema_version` guard in the frontend: when `schema_version` is `"1.3"` or higher, render context panels; when lower (or absent), show the existing "Context not available for this run" empty-state for all panels. Does not break existing 1.2 consumers. | `schema_version: "1.2"` fixture → all panels in empty-state mode; `schema_version: "1.3"` → panels active; no regressions in existing views | 0.5 pts | frontend-developer | sonnet | adaptive | P3-005 |

#### R-P4 Runtime Smoke Task

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| TEST-SMOKE | Runtime smoke across all 4 panel surfaces | Smoke test verifying all 4 context panels in the rendered viewer. Must include: (1) a fully populated `context` run (all 4 panels active); (2) a pre-1.3 context-absent run (`context: null`) — all panels in empty-state, no JS errors; (3) offline static build — SPA built without `rf serve`; panels functional from `run.json` alone. Covers all `target_surfaces` from P3. | All 3 smoke scenarios pass; no console errors; panels render within 200ms of expand; offline build confirms SPA static-export invariant | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3-006 |

#### AC P3-A: All 4 context panels render from populated context
- target_surfaces:
    - src/runs_viewer/components/RunDetail/RoutingDecisionPanel.tsx
    - src/runs_viewer/components/RunDetail/ResearchBriefPanel.tsx
    - src/runs_viewer/components/RunDetail/SwarmPlanPanel.tsx
    - src/runs_viewer/components/RunDetail/UpstreamEntitiesPanel.tsx
    - src/runs_viewer/components/RunDetail/RunDetailWorkspace.tsx
- propagation_contract: Each panel receives its backing `context.*` field as a typed prop from RunDetailWorkspace; prop type matches the exported TS interface exactly.
- resilience: Each panel handles null/undefined prop independently (AC P2-R1 through P2-R4).
- visual_evidence_required: false
- verified_by: [TEST-SMOKE, FE-002, FE-003, FE-004, FE-005]

**Phase 3 Quality Gates:**
- [ ] P3S-001 panel shells in place before P2 completes
- [ ] All 4 panel components implemented (P3-001 through P3-004)
- [ ] RunDetailWorkspace wired (P3-005); no hard destructuring of `context`
- [ ] Schema version guard implemented (P3-006)
- [ ] `tsc --noEmit` passes across all new `.tsx` files
- [ ] FE-002 through FE-006 unit tests pass
- [ ] TEST-SMOKE runtime smoke passes (all 3 scenarios including offline build and pre-1.3 run)
- [ ] **karen milestone review PASS** (mid-feature gate)
- [ ] `task-completion-validator` sign-off

---

### Phase 4: Tests, Docs & Validation

**Duration**: 1–2 days
**Dependencies**: P3 complete (karen milestone passed)
**Entry Criteria**: P3 exit gate cleared including karen milestone
**Exit Gate**: **`karen` feature-end gate PASS** — full suite green, docs/CHANGELOG merged, design spec for DFR-001 authored
**Assigned Subagent(s)**: python-backend-engineer, ui-engineer-enhanced, documentation-writer, changelog-generator; karen (feature-end)
**ICA delegation note**: Test authoring sub-tasks (P4-001, P4-002) are bounded and well-specified → ICA free-tier candidate. Re-run authoritative pytest + tsc in-session after ICA completes.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-001 | Backend test hardening | Complete test suite for `_build_context()` and export pipeline: BE-001 (all-present), BE-002 (each-absent-independently for all 4 fields), BE-003 (redaction: routing_decision + swarm_plan + research_brief_md), BE-004 (export pipeline integration with real run fixture, round-trip verification). Confirm pytest suite is green. | pytest passes; BE-001 through BE-004 all green; no regressions in existing export tests | 0.5 pts | python-backend-engineer | sonnet | adaptive | P2-004 |
| P4-002 | Frontend test hardening | Complete test suite for all 4 panels and workspace: FE-001 (each panel null-context render → empty-state, no error), FE-002–FE-005 (populated context render for each panel), FE-006 (RunDetailWorkspace integration with real context fixture), FE-007 (schema 1.2 fixture → existing views unaffected, no regressions). Confirm `tsc --noEmit` + test runner green. | All FE unit + integration tests pass; no regressions; `tsc --noEmit` clean | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3-006 |
| P4-003 | Schema doc finalization | Finalize `docs/dev/architecture/rf-run-export-schema.md` §9 with complete v1.3 `context` contract: all field names, types, nullability, source artifact per field, graceful-degradation contract, sensitivity redaction coverage. Update §Changelog with v1.3 row. | §9 fully populated; §Changelog updated; schema doc reviews no broken links or stale stubs | 0.5 pts | documentation-writer | haiku | adaptive | P4-001 |
| P4-004 | CHANGELOG entry | Add `CHANGELOG.md [Unreleased]` entry under "Added": "Run context panels (Routing Decision, Research Brief, Swarm Plan, Upstream Entities) in the run detail view; `run.json` schema 1.3 `context` block." Set `changelog_ref: CHANGELOG.md` in plan frontmatter. | Entry present under `[Unreleased]` → "Added"; wording matches PRD §12 documentation acceptance criteria | 0.5 pts | changelog-generator | haiku | adaptive | P4-003 |
| DOC-006 | DFR-001 design spec | Author `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md` with `maturity: shaping`. Document the v2 lazy-load optimization: trigger condition (run.json size threshold), delivery via loopback API `GET /runs/{run_id}/context`, hybrid embed+lazy-load approach, offline fallback semantics, and the frozen-schema implications. Set `prd_ref` to the parent PRD. Append path to `deferred_items_spec_refs` in this plan's frontmatter. | Design spec exists at target path with `maturity: shaping`; covers delivery mechanism, trigger condition, and offline fallback; `deferred_items_spec_refs` updated | 0.5 pts | documentation-writer | sonnet | adaptive | P4-003 |
| P4-005 | Plan frontmatter update | Update this plan's frontmatter: `status: completed`, populate `commit_refs`, `files_affected`, `updated`, `changelog_ref`, `deferred_items_spec_refs`. | Frontmatter complete per lifecycle spec; all fields accurate | 0.25 pts | documentation-writer | haiku | adaptive | DOC-006 |
| P4-006 | karen feature-end gate | `karen` performs final feature-end review across: frozen-schema invariant (schema 1.3 additive, backward-compat), offline-viewer invariant (SPA works without rf serve), sensitivity redaction coverage (context.* fields), and feature acceptance criteria AC-CP-1 through AC-CP-4. Outputs PASS or FAIL with specific items. | karen gate PASS; all identified issues resolved before seal | — | karen | opus | extended | P4-005 |

**Phase 4 Quality Gates:**
- [ ] pytest suite green (backend: BE-001 through BE-004; no regressions)
- [ ] FE unit + integration tests green (FE-001 through FE-007; no regressions)
- [ ] `tsc --noEmit` clean
- [ ] Schema doc fully finalized (§9 + §Changelog)
- [ ] CHANGELOG `[Unreleased]` entry present
- [ ] DFR-001 design spec authored at target path; `deferred_items_spec_refs` updated
- [ ] Plan frontmatter complete
- [ ] **`karen` feature-end gate PASS** (hard gate — final seal requires this)

---

## Risk Mitigation

### Technical Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Frozen-schema bump without governance sign-off | High | Medium | P1 exit gate is backend-architect APPROVED (hard gate); additive+optional `context` key means existing consumers unaffected; verify with backward-compat assertion P1-004 |
| Sensitive content leaking via `context.*` | Medium-High | Low | P2 extends R9 redaction to every `context.*` field; BE-003 redaction test per sub-object; embed decision (OQ-1) keeps redaction in single export-time pass |
| Offline static-viewer regression | Medium | Low | Embed (Option A) by OQ-1 decision; R-P2 resilience ACs for all 4 fields; TEST-SMOKE scenario 2 (pre-1.3 context-absent) + scenario 3 (offline build) |
| Swarm-plan tree-view complexity | Low-Medium | Medium | Two-level typed tree cap (OQ-3); raw-YAML escape hatch for unrecognized shapes; collapsed-by-default bounds initial cost |
| Upstream entity link resolution failure | Low | Low | Best-effort ping only; never blocks panel render; graceful degradation to plain-text badges (AC P2-R4) |

### Schedule Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| P1 backend-architect gate delays P2 | Medium | Initiate review early with field contract in PR description; P3-scaffold can run in parallel with P2 while gate resolves |
| `ibom_id`/`intenttree_node_id` not in `run.yaml` | Medium | Verified before P2-001 implementation; if absent, Panel 4 degrades to `intent_id`-only display without erroring |
| Markdown renderer frontmatter stripping | Low | Unit test includes a fixture with YAML frontmatter; strip before pass to renderer |

---

## Success Metrics

### Delivery Metrics
- All 4 phases complete with exit gates passed
- Zero P1/P2 gate blockers at karen feature-end review

### Functional Metrics
- All four panels render correctly from fully populated `context`
- All four panels degrade to empty-state when `context` or individual field is null
- Zero CLI round-trips required for "review run context" task when context exported
- Schema consumer regressions: 0

### Technical Metrics
- `run.json` schema 1.3 emitted by all post-P2 exports
- `tsc --noEmit` clean; pytest suite green
- Offline build confirmed functional (TEST-SMOKE scenario 3)
- `context.*` field access uses optional chaining throughout; no hard destructuring

---

## Wrap-Up: Feature Guide & PR

After P4 is sealed (all quality gates pass, including karen):

1. Delegate to `documentation-writer` (haiku) to create `.claude/worknotes/runs-context-panels/feature-guide.md` covering: what was built, architecture overview (files changed, key decisions OQ-1..5), how to test (export a run with context, open viewer, expand panels), test coverage summary, known limitations (DFR-001 lazy-load deferred).
2. Open PR: `gh pr create` with title "feat(runs-viewer): run context panels + run.json schema 1.3 (FR-14)".

---

**Progress Tracking:**

See `.claude/progress/runs-context-panels/` (created by artifact-tracking step after this plan is approved).

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-06-23
