## Completion Report

### Summary

Enabled the disabled Library nav tab (G4 of the enable-disabled-viewer-tabs epic) by implementing a new top-level `/library` screen that aggregates writeback artifacts, published reports, and reusable output candidates across all loaded runs. The screen degrades gracefully when backing data is absent (pre-F5 exports), showing non-error empty states per section instead of crashing or rendering blank. All four shared ACs and all six tab-specific ACs are met.

### Files Changed

- `frontend/runs-viewer/src/types/rf/run-export.ts` — added `ReusableOutputCandidate` interface and `reusable_output_candidates?: ReusableOutputCandidate[] | null` field to `RFRunExport`
- `frontend/runs-viewer/src/types/rf/index.ts` — added `ReusableOutputCandidate` to the barrel export
- `frontend/runs-viewer/src/app/AppShell.tsx` — changed Library NAV_ITEMS entry from `state: "disabled"` to `state: "enabled"` with `resolveTarget: () => "/library"`; added `isActiveNav` case for `pathname === '/library'`
- `frontend/runs-viewer/src/app/routes.tsx` — added `"library"` to `RouteName` union and `library: { path: "/library", label: "Library" }` to `ROUTES`
- `frontend/runs-viewer/src/app/App.tsx` — imported `LibraryScreen` and added `{ path: "library", element: <LibraryScreen /> }` route
- `frontend/runs-viewer/src/screens/LibraryScreen.tsx` — new screen: three sections (Published Reports, Writeback Artifacts, Reusable Outputs/SkillBOM), graceful empty states, cross-run data aggregation from React Query cache
- `frontend/runs-viewer/src/styles/library.css` — new CSS using `rv-library-*` BEM prefix with existing `--it-*` design tokens only
- `frontend/runs-viewer/src/styles/index.css` — added `@import "./library.css"` after policies
- `frontend/runs-viewer/src/test/g4-library.test.tsx` — new vitest file: 33 tests covering nav active state, render-no-crash, empty-states, data aggregation, resilience, and regression guard

### Acceptance Criteria Status

**Shared ACs:**
- [x] AC-SHARED-1: Library NAV_ITEMS entry changed from `state: "disabled"` to enabled with `resolveTarget: () => "/library"`; `isActiveNav()` adds Library case for `pathname === '/library'`
- [x] AC-SHARED-2: Route registered in `routes.tsx` (RouteName union + ROUTES); wired in `App.tsx` as `{ path: "library", element: <LibraryScreen /> }`
- [x] AC-SHARED-3: `LibraryScreen.tsx` created with graceful empty states per section; `reusable_output_candidates` absent/null never throws; screen never blanks
- [x] AC-SHARED-4: `src/test/g4-library.test.tsx` with render-no-crash, empty-state, nav-highlight tests (33 tests, all pass)

**Tab-specific ACs:**
- [x] AC G4-1: Library nav item enabled with `path: '/library'`; `/library` route registered pointing to `LibraryScreen`
- [x] AC G4-2: `isActiveNav()` returns true for Library when `pathname === '/library'` — no `routeRunId` dependency
- [x] AC G4-3: Published Reports section renders runs where `report_draft != null && writebacks?.approved_for_writeback === true`; absent `writebacks` treated as false (excluded silently); empty state shown when no qualifying runs
- [x] AC G4-4: Writeback Artifacts section flattens all `writebacks.targets[]` across runs; each entry shows run title, target name, destination, status badge (grouped by status class), and URL if present; empty state when no targets
- [x] AC G4-5: Reusable Outputs section shows specific empty-state message ("Reusable output data requires the enriched export from run-metadata-enrichment (F5). Re-export runs to populate.") when field is absent on ALL loaded runs; when present, renders entries with `is_skillbom_candidate` SkillBOM badge; no crash, no TypeError, no blank area
- [x] AC G4-6: `RFRunExport` has `reusable_output_candidates?: ReusableOutputCandidate[] | null`; `ReusableOutputCandidate` interface exported with `description: string`, `is_skillbom_candidate?: boolean`, `source_run_id?: string`; TypeScript enforces optional-chaining at call sites
- [x] AC G4-7: Run title/ID in all Library sections navigates to that run via `<Link to={/runs/${runId}}>` (react-router); when a run is not in the loaded index, the link is rendered as plain `<span>` text (not a broken `<a>`). **Post-review fix applied**: `ReusableOutputsSection` initially lacked the `inIndex` guard (always rendered `<Link>`). Fixed by: (1) adding `inIndex: boolean` to `ReusableOutputEntry`, (2) computing `summaryIds.has(candidate.source_run_id ?? runId)` in `aggregateReusableOutputs`, (3) rendering `<span data-testid="library-reusable-run-text">` when `inIndex` is false. Three new test cases added covering the stale-run path, indexed path, and `source_run_id`-absent fallback.

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm exec tsc -b` | Pass | Zero errors, zero output |
| `pnpm exec vitest run` | Pass | 515/515 tests, 20 test files (3 new stale-run guard tests added in fix cycle) |
| `pnpm lint` | Pass | Zero warnings (--max-warnings=0) |
| Python tests | Not run | Contract is frontend-only; no Python files touched |

### Deviations From Contract

- **`anyLoading` aggregation**: All three sections show a loading panel while any run is still fetching. This is acceptable for the small-deployment target audience and avoids partial-data flicker; it mirrors the PoliciesScreen pattern.
- **No `eslint-disable` comment needed**: The hook-in-map pattern in LibraryScreen uses the same structure as PoliciesScreen (which had `// eslint-disable-next-line react-hooks/rules-of-hooks`). Lint passes without any disable comment.

### Risks and Limitations

- **Partial data on first Library visit**: Library content reflects only runs that have been fetched into the React Query cache. Runs not yet lazy-loaded do not contribute entries. This is documented per the contract's Risk Areas.
- **Loading state covers all sections**: While any run is still loading, all three sections show a "Loading runs..." panel.
- **`approved_for_writeback` absent on older exports**: Treated as `false` via optional chaining. These runs are silently excluded from Published Reports.

### Follow-Up Recommendations

- Add filtering/search within Library (P1 follow-on per contract's Out of Scope).
- Per-artifact deep-link modals when clicking a writeback or report entry from the Library.
- Optimize loading: consider a "load all runs" trigger button instead of eager batch-loading all run details on Library mount.

### Memory Candidates Captured

- Pattern: `LibraryScreen` follows `PoliciesScreen`'s hook-in-map pattern (`useLoadedRuns`) to batch-load full run exports from summaries. Established cross-run aggregation pattern in this codebase.
- Data pattern: `anyFieldPresent` guard distinguishes pre-F5 (field absent on ALL runs) from post-F5 (field present, possibly empty). Reusable for other optional F5 fields.
