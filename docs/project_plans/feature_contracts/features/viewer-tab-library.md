---
title: "Feature Contract: Library Tab — Reusable Outputs & Writeback Artifacts Index"
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-20
updated: 2026-06-21
feature_slug: "viewer-tab-library"
category: "features"
estimated_points: 5
tier: 1
owner: nick
priority: medium
risk_level: low
changelog_required: false
audience: [ai-agents, developers]
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
  - docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
  - docs/project_plans/feature_contracts/features/viewer-tab-swarm.md
  - docs/project_plans/feature_contracts/features/viewer-tab-policies.md
  - docs/project_plans/feature_contracts/features/viewer-tab-alerts.md
  - docs/project_plans/feature_contracts/features/viewer-tab-settings.md
  - docs/project_plans/feature_contracts/features/viewer-tab-help.md
  - docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected:
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - frontend/runs-viewer/src/types/rf/index.ts
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/app/routes.tsx
  - frontend/runs-viewer/src/app/App.tsx
  - frontend/runs-viewer/src/screens/LibraryScreen.tsx
  - frontend/runs-viewer/src/styles/library.css
  - frontend/runs-viewer/src/styles/index.css
  - frontend/runs-viewer/src/test/g4-library.test.tsx
depends_on: [run-metadata-enrichment]
---

# Feature Contract: Library Tab — Reusable Outputs & Writeback Artifacts Index

## 1. Goal

Enable the disabled Library top-level navigation tab by implementing a new screen that presents a
cross-run index of reusable outputs, writeback artifacts, skillbom candidates, and published reports,
with graceful empty-state handling when writeback or reusable-output data is absent.

---

## 2. User / Actor

- **Primary user**: Nick (LAN operator) reviewing the RF research archive to discover artifacts
  produced across runs that are ready for reuse, promotion to SkillMeat, or writeback publication.
- **Secondary users**: AI agents reading viewer output for post-run orchestration decisions.

---

## 3. Job To Be Done

When **browsing the runs-viewer after a batch of research swarms complete**, the user wants to
**see a unified index of all writeback artifacts, reusable outputs, and published reports across
runs in one place**, so they can **quickly identify what is ready to ship, reuse, or promote
without opening each run individually**.

---

## 4. Scope

### In Scope

- Enable the Library entry in `AppShell.tsx` `NAV_ITEMS` (remove `disabled: true`, set route to `/library`).
- Register a `/library` route in `app/routes.tsx` pointing to a new `LibraryScreen` component.
- Implement `screens/LibraryScreen.tsx` as a new read-only screen that aggregates across all
  loaded runs and renders:
  - **Writeback artifacts** — from `RFRunExport.writebacks.targets[]`
    (`{name, destination, status, url?}`). Group or filter by writeback `status`.
  - **Reusable output candidates** — from `backlog_idea.intenttree.reusable_output_candidates[]`
    (available post-F5/P7 export enrichment); fall back to absent-field empty state if not present.
  - **Published reports** — runs where `report_draft` is non-null and `writebacks.approved_for_writeback` is true.
  - **SkillBOM candidates** — surfaced as a labeled subset of reusable outputs (label-only; no separate data source needed at this tier).
- Graceful empty state for each section when the backing data is absent or null (R-P2).
- `isActiveNav()` recognition: Library tab becomes active when `pathname === '/library'`.
- Runtime smoke verification task included in the validation phase.

### Out of Scope

- Mutating, approving, or triggering writebacks (viewer is read-only).
- Adding new export fields beyond what F5/P7 provides; this contract only consumes what F5 threads.
- Filtering/search within Library (P1 follow-on).
- Deep per-artifact detail modals (reuse RunDetailModal / ProvenanceModal patterns; out of scope for this contract).
- SkillBOM schema changes or SkillMeat API calls.
- Any backend change to `export_service.py` or `run.yaml` — all data must already be present in
  the static export from F5. This contract is frontend-only given that F5 P7 has run.

---

## 5. UX / Behavior Requirements

- The Library tab appears in the top navigation alongside Portfolio, Runs, Reports, Ledger.
  It is always visible and always navigable (not contextual on a selected run).
- Navigating to `/library` renders `LibraryScreen` full-width within the existing AppShell layout.
- The screen is divided into labeled sections (e.g., card groups or a tabbed sub-nav — implementer
  choice; card groups preferred for simplicity):
  1. **Published Reports** — runs with non-null `report_draft` and `writebacks.approved_for_writeback === true`,
     listed as cards showing run title (via `deriveRunTitle`/`titleFromSlug` fallback), run ID, writeback
     destination(s), and a link to open the run's Report tab (`/runs/:runId?tab=report`).
  2. **Writeback Artifacts** — all `writebacks.targets[]` entries across runs, grouped by `status`
     (published / pending / failed). Each entry shows: run title, target name, destination, status badge,
     and URL if present.
  3. **Reusable Outputs / SkillBOM Candidates** — entries from `reusable_output_candidates[]` if
     present in the enriched export (F5/P7); labeled "SkillBOM candidate" if candidate field is set.
     Each entry shows: run title, candidate description, source run link.
- When a section has no data (field absent, null, or empty array), show a non-error empty state:
  a short explanatory message (e.g., "No writeback artifacts found. Run `rf run export --all` and
  rebuild if you expect data here.") — not a spinner or error UI.
- Clicking a run title / run ID in any section navigates to that run's modal (reuse existing
  routing; do not embed RunDetailModal inline).
- No infinite scroll or pagination required at this point (total artifact count is small for a LAN
  personal viewer).

---

## 6. Data Requirements

- **Source**: `RFRunExport` objects loaded from `public/data/<id>/run.json` via existing data
  loading infrastructure (`api/client.ts` + `lib/runs.ts` data hooks). No new fetch mechanism needed.
- **Fields consumed** (all already in or planned for the export schema):
  - `writebacks.targets[]` — `{name: string, destination: string, status: string, url?: string}` (schema 1.1, present now)
  - `writebacks.approved_for_writeback` — `boolean` (schema 1.1, present now)
  - `report_draft` — `string | null` (schema 1.1, present now; non-null = report exists)
  - `reusable_output_candidates[]` — NEW field threaded by F5/P7; may be absent on pre-F5 exports
  - Run title: via `deriveRunTitle(run)` / `titleFromSlug(run.run_id)` (already in `lib/runs.ts`)
- **Index (summary) data**: `RFRunSummary` from `public/data/index.json` is insufficient for Library
  (it lacks `writebacks` and `report_draft`). LibraryScreen must load full `RFRunExport` for each run
  that has been pre-loaded, OR trigger a lazy load per run. Preferred: reuse existing run-detail data
  hooks; do not issue N+1 loads upfront — aggregate from already-loaded runs in the store, and
  provide a "load all" trigger if needed.
- **New TS types**: Add `reusable_output_candidates?: ReusableOutputCandidate[]` to `RFRunExport`
  in `frontend/runs-viewer/src/types/rf/run-export.ts` with `ReusableOutputCandidate` as
  `{ description: string; is_skillbom_candidate?: boolean; source_run_id?: string }`. Mark optional
  (R-P2: absent on pre-F5 runs).
- **No new backend export changes required from this contract** — all threading is F5's responsibility.

---

## 7. API / Integration Requirements

**New or modified endpoints:** None. The viewer is a static SPA; all data comes from pre-built
`public/data/` JSON files.

**External service calls:** None.

**Internal service dependencies:**
- `api/client.ts` — existing `fetchRun(runId)` / `fetchRunIndex()` patterns; reuse as-is.
- `lib/runs.ts` — `deriveRunTitle()`, `titleFromSlug()` for display; no new exports needed.
- Existing run data store / context (however runs are currently cached in the app) — aggregate
  from already-fetched runs; do not force a full pre-load of all N run.json files.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `frontend/runs-viewer/src/app/AppShell.tsx` `NAV_ITEMS` — enable entry using same shape as other
  always-visible tabs (no `disabled` field, `path: '/library'`, no `contextual: true`).
- `frontend/runs-viewer/src/app/routes.tsx` — register route using same pattern as `RunList` /
  `RunDetail` routes.
- Screen file convention: `frontend/runs-viewer/src/screens/LibraryScreen.tsx` (alongside
  `RunList.tsx`, `RunDetail.tsx`).
- CSS class naming: `rv-library-*` prefix, consistent with `rv-portfolio-*`, `rv-audit-*` etc.
- `lib/runs.ts` utility functions for title derivation — do not inline derivation logic in the screen.

**Must not change** (protected areas):
- `RFRunExport` schema_version or any existing field shapes.
- Existing tab routing for run-detail views (`/runs/:runId?tab=*`) — Library links INTO these but
  does not alter them.
- `AppShell.tsx` `isActiveNav()` logic for existing tabs — only add the Library condition.
- `prebuild-static-data.mjs` and `export_service.py` — no backend changes in this contract.

**New dependencies:**
- Allowed? **No** — no new npm packages. Use existing React, CSS modules, and internal utilities.

---

## 9. Acceptance Criteria

### AC G4-1: Library nav item enabled and routed

- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: `NAV_ITEMS` entry for Library has `disabled` removed and `path: '/library'`;
  `routes.tsx` registers `/library` → `LibraryScreen`.
- resilience: N/A (routing is always present).
- visual_evidence_required: screenshot showing Library tab active in nav when at `/library`.
- verified_by: [smoke-G4]

### AC G4-2: Library nav becomes active when pathname is `/library`

- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: `isActiveNav()` returns true for Library when `pathname === '/library'`.
- resilience: No run selection required — Library is always-visible, not contextual.
- visual_evidence_required: false
- verified_by: [smoke-G4]

### AC G4-3: Published Reports section renders correctly

- target_surfaces:
    - frontend/runs-viewer/src/screens/LibraryScreen.tsx
- propagation_contract: Runs where `report_draft` is non-null AND
  `writebacks.approved_for_writeback === true` appear in the Published Reports section with run
  title (via `deriveRunTitle`/`titleFromSlug` fallback), run ID, and a link to `/runs/:runId?tab=report`.
- resilience: When no run satisfies the condition, section shows empty-state message (not error/spinner).
  When `writebacks` field is absent/null on a run, that run is excluded from this section silently.
- visual_evidence_required: false
- verified_by: [smoke-G4, unit-G4-data]

### AC G4-4: Writeback Artifacts section renders with status grouping

- target_surfaces:
    - frontend/runs-viewer/src/screens/LibraryScreen.tsx
- propagation_contract: All `writebacks.targets[]` entries across loaded runs appear, grouped or
  badged by `status`. Each entry shows: run title, target `name`, `destination`, status badge, `url`
  if present (as a link).
- resilience: When `writebacks` is absent/null on a run, that run contributes no entries to this
  section. When `writebacks.targets` is an empty array, section shows empty-state message.
- visual_evidence_required: false
- verified_by: [smoke-G4, unit-G4-data]

### AC G4-5: Reusable Outputs / SkillBOM section handles absent field gracefully

- target_surfaces:
    - frontend/runs-viewer/src/screens/LibraryScreen.tsx
- propagation_contract: When `reusable_output_candidates` is present (post-F5/P7 exports), entries
  render with description and a "SkillBOM candidate" label when `is_skillbom_candidate` is true.
  When field is absent or null (pre-F5 exports), section shows a specific empty-state: "Reusable
  output data requires the enriched export from run-metadata-enrichment (F5). Re-export runs to populate."
- resilience: **Primary resilience AC** — the entire section must render without errors when
  `reusable_output_candidates` is absent/null/undefined on every loaded run. No crash, no `undefined`
  TypeError, no blank white area — only the empty-state message.
- visual_evidence_required: false
- verified_by: [unit-G4-resilience, smoke-G4]

### AC G4-6: `RFRunExport` type updated for `reusable_output_candidates`

- target_surfaces:
    - frontend/runs-viewer/src/types/rf/run-export.ts
- propagation_contract: `RFRunExport` has `reusable_output_candidates?: ReusableOutputCandidate[]`;
  `ReusableOutputCandidate` interface exported with fields `description: string`,
  `is_skillbom_candidate?: boolean`, `source_run_id?: string`.
- resilience: Field is optional; TypeScript enforces optional-chaining usage at all call sites.
- visual_evidence_required: false
- verified_by: [typecheck]

### AC G4-7: Run title deep-links to run modal / run page

- target_surfaces:
    - frontend/runs-viewer/src/screens/LibraryScreen.tsx
- propagation_contract: Clicking a run title or run ID in any Library section navigates to that
  run using existing routing (e.g., sets `selectedRunId` / navigates to `/runs/:runId` or opens
  modal via the same mechanism as RunCard click).
- resilience: If a run referenced in writebacks is not in the loaded index (stale data), the link
  is rendered as plain text (not a broken `<a>`).
- visual_evidence_required: false
- verified_by: [smoke-G4]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` with zero new errors.
- [ ] **Lint** passes: ESLint on modified files with zero new warnings.
- [ ] **Unit tests** — `unit-G4-data`: test `LibraryScreen` data aggregation logic (Published Reports
      filter, Writeback Artifacts flattening) with mock `RFRunExport` fixtures covering: normal data,
      all fields absent, empty arrays.
- [ ] **Resilience test** — `unit-G4-resilience`: render `LibraryScreen` with a fixture where
      `writebacks` is null AND `reusable_output_candidates` is undefined; assert no thrown error and
      empty-state message appears for each section.
- [ ] **Runtime smoke** — `smoke-G4`: start the dev server (or build + serve static); navigate to
      `/library`; assert (a) Library tab is active in nav, (b) screen renders without console error,
      (c) at least one section's empty state OR populated content is visible.
- [ ] **Build** passes: `pnpm --filter runs-viewer build` with zero new errors.
- [ ] **No unrelated changes** introduced.

---

## 11. Risk Areas

- **Data availability at render time**: LibraryScreen needs full `RFRunExport` objects but the index
  only carries `RFRunSummary`. If runs are lazy-loaded, there may be a loading state flash or
  incomplete data on first render. Mitigation: aggregate from already-fetched runs in the existing
  store; document that Library content reflects whichever runs have been loaded.

- **F5 dependency**: `reusable_output_candidates` will be absent until F5/P7 ships and a re-export
  runs. The resilience AC (G4-5) is the mitigation — the screen must not crash on pre-F5 data.
  This contract MUST NOT block on F5 completion for the nav enable, route, and writeback/report
  sections; only the reusable-output section depends on F5.

- **`approved_for_writeback` field presence**: The field is schema 1.1 but may be null/missing on
  older exports. The Published Reports filter must treat absent as `false` (not crash).

- **N+1 loading**: Aggregating across all runs requires full exports. If the app doesn't pre-load
  all runs, Library will show partial data. Keep this documented as a known limitation; do not
  implement a full pre-load waterfall (performance concern on large archives).

---

## 12. Implementation Notes

**Suggested approach:**

1. Add `reusable_output_candidates?: ReusableOutputCandidate[]` to `run-export.ts` (`RFRunExport`)
   and define the `ReusableOutputCandidate` interface. All other `RFRunExport` fields already exist.

2. Enable the Library `NAV_ITEMS` entry in `AppShell.tsx` (remove `disabled: true`, set `path: '/library'`).
   Add the `isActiveNav` condition: `pathname === '/library'` (no `routeRunId` dependency).

3. Register `/library` route in `app/routes.tsx` with lazy or eager import of `LibraryScreen`.

4. Implement `screens/LibraryScreen.tsx`:
   - Access loaded runs from the existing data context/store.
   - Derive Published Reports: filter runs where `run.writebacks?.approved_for_writeback === true && run.report_draft != null`.
   - Derive Writeback Artifacts: flatMap runs over `run.writebacks?.targets ?? []`, attach run metadata.
   - Derive Reusable Outputs: flatMap runs over `run.reusable_output_candidates ?? []`.
   - Render three labeled sections; each has a populated list or an empty-state `<p>` message.

5. Add CSS under `rv-library-*` namespace in the screen's module CSS (or global `rv-*.css` per project convention).

6. Write unit tests for the aggregation/filter logic (pure functions, no DOM needed for data logic).

7. Smoke test: navigate to `/library` in dev server; confirm all three sections render (empty or populated).

**Similar existing code:**
- `screens/RunList.tsx` — pattern for a top-level screen aggregating runs data.
- `components/RunDetail/RunDetailWorkspace.tsx` — tab-pane layout pattern.
- `app/AppShell.tsx` NAV_ITEMS — follow the exact same shape as Settings/Help entries (no `disabled`, no `contextual`).

**Known gotchas:**
- `RFRunExport.writebacks` is typed as optional (`writebacks?`); always optional-chain.
- `reusable_output_candidates` does not exist in the current export schema (F5/P7 adds it); the
  TS field must be optional and guarded everywhere.
- Do not import `RunDetailModal` into LibraryScreen — use navigation (link or `navigate()`) instead
  of embedding the modal, to avoid circular dependency and complexity.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason.
- **Tests run**: Unit tests (data aggregation, resilience) + smoke test results.
- **Validation results**: Table of all validation commands and their results (pass/fail/N-A).
- **Deviations from contract**: Any material changes and justification.
- **Risks / Limitations**: Especially note if Library shows partial data due to lazy-load constraints.
- **Follow-up recommendations**: Filtering/search within Library (P1); deep-link to run modal vs page.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (estimated 5 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion

**Reviewer**: `task-completion-validator` (mandatory)

**Data dependency**: F5 (`run-metadata-enrichment`) Phase 7 — required for `reusable_output_candidates`
field; the nav enable, route, Published Reports, and Writeback Artifacts sections are **F5-independent**
and can ship before F5 completes.

**Related Documents:**
- Epic index: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Sub-epic: `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md`
- F5 plan: `docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md`
- Sibling tab contracts: `viewer-tab-swarm.md`, `viewer-tab-policies.md`, `viewer-tab-alerts.md`,
  `viewer-tab-settings.md`, `viewer-tab-help.md` (all in `feature_contracts/features/`)

**Key source refs (from epic brief §1):**
- `frontend/runs-viewer/src/app/AppShell.tsx` lines ~24-35 (NAV_ITEMS), ~105-111 (isActiveNav)
- `frontend/runs-viewer/src/types/rf/run-export.ts` (RFRunExport, RFRunSummary)
- `frontend/runs-viewer/src/lib/runs.ts` (`deriveRunTitle`, `titleFromSlug`)
- `run.yaml` / `export_service.py` — writeback threading already present (schema 1.1)
- `backlog/research_idea_backlog.yaml` — `intenttree.reusable_output_candidates` source (post-F5)
