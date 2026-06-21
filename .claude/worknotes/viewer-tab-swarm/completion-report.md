# Completion Report — viewer-tab-swarm (Wave-2 Swarm Tab)

## Summary

Enabled the disabled "Swarm" nav tab in the runs-viewer SPA per contract `viewer-tab-swarm.md`. Changed the NAV_ITEMS entry from `state: "disabled"` to `state: "contextual"` with a `resolveTarget` pointing to `/runs/:runId/swarm`, updated `isActiveNav` to handle the swarm path, registered the `/runs/:runId/swarm` route in both `routes.tsx` and `App.tsx`, created the new `SwarmScreen.tsx` with full graceful empty states, added `swarm.css` for styling, and added 23 vitest smoke tests in `g1-swarm.test.tsx`.

## Files Changed

- `frontend/runs-viewer/src/app/AppShell.tsx` — Changed Swarm NAV_ITEMS entry from `state: "disabled"` to `state: "contextual"` with `resolveTarget`; added `isActiveNav` case for Swarm.
- `frontend/runs-viewer/src/app/routes.tsx` — Added `"swarm"` to `RouteName` union and `ROUTES` record with path `/runs/:runId/swarm`.
- `frontend/runs-viewer/src/app/App.tsx` — Imported `SwarmScreen` and registered `runs/:runId/swarm` route in the router.
- `frontend/runs-viewer/src/screens/SwarmScreen.tsx` — NEW. Swarm orchestration visualizer screen with routing decision card, swarm plan section (array/structured/raw-JSON fallback), agents chip list, and full empty state for pre-F5 exports.
- `frontend/runs-viewer/src/styles/swarm.css` — NEW. BEM CSS for `rv-swarm*` classes using existing `--it-*` design tokens.
- `frontend/runs-viewer/src/styles/index.css` — Added `@import "./swarm.css"`.
- `frontend/runs-viewer/src/test/g1-swarm.test.tsx` — NEW. 23 vitest smoke tests covering all contract ACs.

## Acceptance Criteria Status

- [x] AC G1-01: Swarm nav item enabled and navigable — NAV_ITEMS entry is `state: "contextual"` with `resolveTarget`; route is registered; nav item is disabled when no run is selected (contextual guard).
- [x] AC G1-02: Routing Decision card renders when data present — renders agent name + rationale; shows placeholder when absent.
- [x] AC G1-03: Swarm Plan section renders when data present — handles structured object, array, and raw-JSON fallback; placeholder when absent.
- [x] AC G1-04: Full empty state when context block absent — "Swarm data not available. Re-export this run after updating to v2.2+ to see swarm details." — no JS error.
- [x] AC G1-05: `isActiveNav` highlights Swarm correctly — returns true when `pathname.endsWith("/swarm")` and `routeRunId` is set; does not interfere with other nav items.
- [x] AC G1-06: Runtime smoke — data-present — SMOKE-G1-02 / TEST-G1-01 / TEST-G1-02 all pass.
- [x] AC G1-07: Runtime smoke — data-absent — SMOKE-G1-03 / TEST-G1-03 all pass.

## Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm exec tsc -b` | Pass | Zero errors. |
| `pnpm exec vitest run` | Pass | 456 tests / 18 test files. 23 new swarm tests all green. |
| `pnpm lint` | Pass | Zero warnings. `eslint src --max-warnings=0`. |

## Deviations From Contract

- **`state: "contextual"` instead of `state: "enabled"`**: The contract says mirror Alerts/Settings/Help (which are `enabled`). Swarm is per-run and should only be clickable when a run is selected — matching the Runs/Reports/Ledger contextual pattern (AC §5: "visible only when a run is selected"). This is a correct interpretation; `state: "enabled"` would make it always clickable (pointing nowhere when no run is selected).
- **`isActiveNav` uses `pathname.endsWith("/swarm")`**: The AppShell `view` variable reads `?view=` query params. The swarm route uses a path segment, not a query param, so `pathname.endsWith("/swarm")` is the correct discriminant.

## Risks and Limitations

- **Data dependency on F5 (P7)**: All current runs will show the full empty state until F5 ships and runs are re-exported.
- **Unknown swarm_plan shape**: Handled via type-guards (`Array.isArray`, `isSwarmPlanObject`) and raw-JSON fallback.

## Follow-Up Recommendations

- Once F5 ships, narrow `unknown` index-signature fields in `RFRunContextSummary` to concrete interfaces.
- Consider DAG/graph visualization of the swarm plan as a P1 enhancement (out of scope per contract §4).
- Run manual browser smoke after F5 ships to validate live data rendering.

## Memory Candidates Captured

- Pattern: `isActiveNav` for sub-path routes must use `pathname.endsWith()` rather than the `view` query param, since `view` only captures `?view=` params.
- Pattern: A nested run-detail route must be added to both `App.tsx` router config AND `routes.tsx` `ROUTES` record.
