---
schema_version: 2
doc_type: phase_plan
title: "Run Metadata Enrichment — Phases 4–5: Export & FE Types · Viewer Display"
status: draft
phase: "4-5"
phase_title: "Export & FE Types, Viewer Display"
created: 2026-06-20
updated: 2026-06-20
feature_slug: run-metadata-enrichment
prd_ref: docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
plan_ref: docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
entry_criteria:
  - "Phase 1–3 complete (fields in run.yaml; migration executed; creation path wired)"
  - "P4 is the serialization barrier: no FE display work starts until export fields confirmed in public/data"
exit_criteria:
  - "P4: re-export + rebuild produces public/data with all new fields; RFRunSummary/RFRunExport TS types compile"
  - "P5: all target_surfaces render linked_projects/category/tags; pre-migration run (no fields) renders gracefully"
---

# Phases 4–5: Export & FE Types · Viewer Display

**Parent plan**: [run-metadata-enrichment-v1.md](../run-metadata-enrichment-v1.md)
**Phases covered**: P4 (Export & FE Types), P5 (Viewer Display)
**Critical path**: P2/P3 → P4 → P5 (barrier; all P5 surfaces share this barrier)

---

## Column conventions

| Column | Values |
|--------|--------|
| Estimate | story points |
| Model | `sonnet` \| `haiku` |
| Effort | `adaptive` \| `extended` (Claude only) |

---

## Phase 4: Export & FE Types

**Duration**: 1–2 days
**Dependencies**: Phases 1–3 complete
**Assigned Subagents**: python-backend-engineer (export), ui-engineer-enhanced (FE types)

### Overview

Thread the 5 new fields into `export_service.py:export_run()` dict and into `index.json` summary
(for list-view performance). Bump export `schema_version` to `1.2`. Extend `RFRunSummary` and
`RFRunExport` in `run-export.ts`. Re-export all runs to populate `public/data`. This phase is the
serialization barrier — P5 display work cannot start until this ships.

### Source references (verified)
- `export_service.py:export_run()` lines ~417-436: builds run.json dict field-by-field. **Not auto-included.**
  Each new field must be threaded explicitly (epic brief §0.1.2).
- `prebuild-static-data.mjs`: copies `runs/<id>/run.json` → `public/data/<id>/run.json` + builds
  `public/data/index.json` summary. Summary shape today: `{run_id, status_derived, created_at,
  sensitivity, claim_counts}` (epic brief §1.2).
- `RFRunSummary` today: `{run_id, status_derived, created_at?, sensitivity?, claim_counts?}`.
- `RFRunExport` today: schema 1.1 — does not include new metadata fields.
- P4 also supersedes F1's `title` field addition to index.json/RFRunSummary — coordinate with F1
  implementer to avoid conflict (F5-P4 extends F1's index.json touch).

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| EXP-001 | Thread fields into export_run() | In `export_service.py:export_run()`, add explicit entries for `linked_projects`, `category`, `tags`, `backlog_idea_ref`, `backlog_idea_id` to the output dict. Read from `run.yaml` metadata. If field absent in run.yaml: emit `null` (not omit) so FE can detect cleanly. | Re-exporting a run that has the fields populated yields a `run.json` containing all 5 new fields (even if null for old runs); existing fields unaffected; `null` emitted for absent fields (not key omission) | 2 pts | python-backend-engineer | sonnet | adaptive | MIG-002, CRE-001 |
| EXP-002 | Thread fields into index.json summary | In `prebuild-static-data.mjs` (or in `export_run()` if index is built there), add `linked_projects`, `category`, `tags` to each run's summary entry in `public/data/index.json`. These 3 fields are needed on list views; `backlog_idea_ref`/`backlog_idea_id` only needed on detail views (omit from index). Coordinate with F1 to also add `title` in the same pass if not already done. | `public/data/index.json` contains `linked_projects`, `category`, `tags` (plus `title` from F1) for each run entry; null for runs without data; rebuild succeeds | 1 pt | python-backend-engineer | sonnet | adaptive | EXP-001 |
| EXP-003 | Bump schema_version | Increment `schema_version` from `"1.1"` to `"1.2"` in `export_run()` output AND in the formal JSON schema from SCH-002. Add a migration note in the schema doc: "v1.2 adds linked_projects, category, tags, backlog_idea_ref, backlog_idea_id (all optional)". | `run.json` output has `schema_version: "1.2"`; JSON schema file has `"version": "1.2"` in its title/description; schema_version bump documented | 0.5 pts | python-backend-engineer | sonnet | adaptive | EXP-001 |
| EXP-004 | Extend RFRunSummary in run-export.ts | Finalize the stubs from SCH-004: add full JSDoc comments to `linked_projects?: string[] \| null`, `category?: string \| null`, `tags?: string[] \| null`. These match the index.json shape from EXP-002. If codegen was opted in (SCH-003), regenerate types. | `RFRunSummary` compiles; `npx tsc --noEmit` clean; all 3 list-view fields present with correct nullability | 1 pt | ui-engineer-enhanced | sonnet | adaptive | EXP-002, SCH-003 |
| EXP-005 | Extend RFRunExport in run-export.ts | Add `linked_projects?: string[] \| null`, `category?: string \| null`, `tags?: string[] \| null`, `backlog_idea_ref?: string \| null`, `backlog_idea_id?: string \| null` to `RFRunExport` interface. If codegen used, regenerate. | `RFRunExport` compiles with all 5 new fields; `npx tsc --noEmit` clean | 1 pt | ui-engineer-enhanced | sonnet | adaptive | EXP-003, SCH-003 |
| EXP-006 | Re-export all runs + rebuild static data | Run `rf run export --all` then `pnpm --filter runs-viewer build` (prebuild step triggers re-export automatically). Verify `public/data/index.json` and a sample `public/data/<id>/run.json` contain the new fields. (See epic brief §0.1.1 re-export discipline.) | `public/data/index.json` has new fields for all runs with backlog links (null for others); at least one `run.json` has non-null values; `pnpm build` succeeds without type errors | 0.5 pts | python-backend-engineer | sonnet | adaptive | EXP-001, EXP-002, EXP-005 |

**Phase 4 Quality Gates:**
- [ ] `run.json` has `schema_version: "1.2"` and all 5 new fields (null or populated)
- [ ] `public/data/index.json` has `linked_projects`, `category`, `tags` for all runs
- [ ] `RFRunSummary` and `RFRunExport` compile (`npx tsc --noEmit` clean)
- [ ] Re-export + rebuild succeeds without errors
- [ ] Backlog-linked runs have non-null values in public/data (verify ≥3 runs manually)

---

## Phase 5: Viewer Display

**Duration**: 2–3 days
**Dependencies**: Phase 4 complete (export barrier)
**Assigned Subagents**: ui-engineer-enhanced (primary), frontend-developer

### Overview

Surface Linked Projects as a PRIMARY column/field on all list surfaces, and add category + tags chips
everywhere relevant. Enumerate all target_surfaces explicitly per R-P1. Every surface must handle
absent/null fields gracefully (R-P2) — pre-migration runs will have null values until re-exported.

### Target surfaces (per §1.9, with display role)

| Surface | linked_projects display | category | tags |
|---------|------------------------|----------|------|
| `screens/RunList.tsx` (portfolio table, status lanes) | Primary column in table + StatusLane | badge | chips row |
| `components/RunList/RunCard.tsx` | Primary badge below run ID | — | chips (top 3, overflow badge) |
| `components/RunList/FilterTabs.tsx` | — | — | — (filter UI in P6) |
| `components/RunDetail/RunDetailWorkspace.tsx` (Overview tab) | Section in Overview | inline label | chips |
| `components/RunDetail/RunDetailModal.tsx` (header) | sub-header line | inline | chips |
| `components/ClaimLedger/ClaimAuditWorkbench.tsx` (ClaimInspector pane) | — | — | optional reference chips |
| `components/LineageGraph/LineageDetailPanel.tsx` | — | — | optional reference chips |

*`SourceCard.tsx`, `ClaimLedgerTable.tsx`, `ProvenanceModal.tsx` do NOT need primary metadata display —
they are claim/source-level surfaces, not run-level.*

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| DISP-001 | RunCard: linked_projects + tags | Add a `LinkedProjectBadge` (or reuse existing badge component) under the run ID on `RunCard.tsx`. Display `linked_projects` as comma-separated pills (or "Project: unassigned" fallback). Add `tags` chips below (top 3, "+N more" overflow). Handle null: render nothing (no empty placeholder). | RunCard shows linked_projects badge + tags chips for runs with data; renders without any badge/chip for runs with null values; `npx tsc --noEmit` clean; visual smoke (desktop ≥1280px) | 2 pts | ui-engineer-enhanced | sonnet | adaptive | EXP-006 |
| DISP-002 | RunList table: linked_projects primary column | Add a "Project" column to the portfolio table in `RunList.tsx` between status and created_at. Render linked_projects as comma-joined text (or badges if space allows). StatusLane header: add linked_projects sub-label under the run title in each lane card. Null → "—" in table; omit sub-label in lane. | Table has "Project" column; linked_projects rendered for backlog-linked runs; "—" for null; status lane cards show sub-label when present; existing columns unaffected; responsive: column hides gracefully at narrow widths | 2 pts | ui-engineer-enhanced | sonnet | adaptive | DISP-001 |
| DISP-003 | RunDetailModal: metadata in header | In `RunDetailModal.tsx` header area (below run ID / title), add a sub-header line showing linked_projects and category (inline label), plus tags chips. Null: omit the sub-header line entirely (no empty space). | RunDetailModal header shows project/category/tags line when any field non-null; omits line when all null; Escape/overlay focus order unaffected; `npx tsc --noEmit` clean | 1 pt | ui-engineer-enhanced | sonnet | adaptive | EXP-006 |
| DISP-004 | RunDetailWorkspace: Overview tab metadata section | In `RunDetailWorkspace.tsx` Overview tab content, add a "Run Metadata" section (collapsible or flat) showing: Linked Projects (list), Category (label), Tags (chips), Backlog Ref (link if present). Null fields: omit the row (do not show empty rows). | Overview tab has Run Metadata section; all 5 fields rendered when present; null fields omitted; section renders without errors when all fields null (pre-migration run) | 2 pts | ui-engineer-enhanced | sonnet | adaptive | EXP-006 |
| DISP-005 | Side panes: optional reference chips | In `ClaimAuditWorkbench.tsx` (ClaimInspector header) and `LineageDetailPanel.tsx` (panel header), add a single line of small `tags` chips + `category` label as context reference. Show only when tags/category non-null. These are reference-only (not interactive). | ClaimInspector header shows tags + category when non-null; LineageDetailPanel header shows same; graceful omission when null; no layout shift | 1 pt | frontend-developer | sonnet | adaptive | EXP-006 |

#### AC DISP-001 (structured — multi-surface)

```
AC DISP-001: RunCard linked_projects + tags display
- target_surfaces:
    - frontend/runs-viewer/src/components/RunList/RunCard.tsx
- propagation_contract: RunCard receives RFRunSummary (from index.json); reads linked_projects and tags fields
- resilience: when linked_projects null/absent → no badge rendered; when tags null/absent → no chips rendered; no console error
- visual_evidence_required: "desktop ≥1280px screenshot of portfolio showing RunCard with project badge + tags (≥1 run with data, ≥1 run without)"
- verified_by: [SMOKE-001]
```

#### AC DISP-002 (structured — multi-surface)

```
AC DISP-002: RunList table + StatusLane linked_projects
- target_surfaces:
    - frontend/runs-viewer/src/screens/RunList.tsx
- propagation_contract: RunList reads from RFRunSummary[] (index.json); passes linked_projects to table column + StatusLane sub-label
- resilience: null linked_projects → "—" in table column; no sub-label in StatusLane; no layout break
- visual_evidence_required: "desktop ≥1440px screenshot of portfolio table showing 'Project' column with mixed data/null rows"
- verified_by: [SMOKE-001]
```

#### AC DISP-003 (structured)

```
AC DISP-003: RunDetailModal header metadata
- target_surfaces:
    - frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx
- propagation_contract: RunDetailModal receives full RFRunExport; reads linked_projects, category, tags
- resilience: all fields null → sub-header line omitted; partial fields → only non-null rendered
- visual_evidence_required: "RunDetailModal header screenshot for a backlog-linked run + for a pre-migration run (no metadata)"
- verified_by: [SMOKE-001]
```

#### AC DISP-004 (structured)

```
AC DISP-004: RunDetailWorkspace Overview metadata section
- target_surfaces:
    - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
- propagation_contract: receives full RFRunExport; reads all 5 new fields for Run Metadata section
- resilience: all fields null → section still renders but shows no rows (not empty placeholder); no console error
- visual_evidence_required: "Overview tab screenshot for a backlog-linked run + for a pre-migration run"
- verified_by: [SMOKE-001]
```

**Phase 5 Quality Gates:**
- [ ] All 7 target_surfaces from the table above render linked_projects, category, or tags correctly
- [ ] Pre-migration run (all new fields null) renders without errors on all surfaces (R-P2)
- [ ] `npx tsc --noEmit` clean after all display changes
- [ ] Runtime smoke task SMOKE-001 (P8) signed off against all target_surfaces from this phase
- [ ] Visual evidence (screenshots) captured for structured ACs above
