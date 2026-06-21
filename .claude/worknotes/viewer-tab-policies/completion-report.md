## Completion Report

### Summary

Enabled the "Policies" nav tab (G2) as a top-level route `/policies`. Implemented `PoliciesScreen` with two sections: a Global Governance Panel (reads `governance.json` from the static build, shows key profiles and policy rules) and a Per-Run Governance Table (loads all run governance blocks, shows sensitivity, writeback approval, allowed writebacks, and human review flag). Extended `export_service.py` to thread `allowed_writebacks` and `requires_human_review` from `run.yaml` into the exported `governance` dict. Extended `RFGovernanceBlock` with those two new optional fields. Extended `prebuild-static-data.mjs` to write `public/data/governance.json` from `config/governance.yaml`.

### Files Changed

- `src/research_foundry/services/export_service.py` — AC-4: thread `allowed_writebacks` and `requires_human_review` from `run_meta.get("governance", {})` into the exported governance dict (additive-only, uses `setdefault` so existing keys are not overwritten)
- `frontend/runs-viewer/src/types/rf/run-export.ts` — AC-4: extend `RFGovernanceBlock` with `allowed_writebacks?: string[] | null` and `requires_human_review?: boolean | null`
- `frontend/runs-viewer/src/types/governance.ts` — New: `GovernanceConfig` and `GovernancePolicyRule` types for the static governance snapshot
- `frontend/runs-viewer/scripts/prebuild-static-data.mjs` — AC-2: step 5 reads `config/governance.yaml` via `js-yaml` and writes `public/data/governance.json` (fallback `{}` on any read/parse failure)
- `frontend/runs-viewer/src/api/client.ts` — New: `fetchGovernanceConfig()` following the `fetchIndex()` pattern; returns `{}` gracefully on 404 or parse error
- `frontend/runs-viewer/src/app/AppShell.tsx` — AC-1: change Policies `state: "disabled"` to `state: "enabled"`, add `resolveTarget: () => "/policies"`, add `isActiveNav` case for `"Policies"`
- `frontend/runs-viewer/src/app/routes.tsx` — AC-1: add `"policies"` to `RouteName` union and `ROUTES` record
- `frontend/runs-viewer/src/app/App.tsx` — AC-1: import `PoliciesScreen` and wire `{ path: "policies", element: <PoliciesScreen /> }` in the router
- `frontend/runs-viewer/src/screens/PoliciesScreen.tsx` — New: full screen with `GlobalGovernancePanel` + `RunGovernanceTable`, graceful empty states, sortable columns (Sensitivity, Writeback Approved)
- `frontend/runs-viewer/src/styles/policies.css` — New: `rv-policies__*` BEM classes following swarm.css conventions
- `frontend/runs-viewer/src/styles/index.css` — Add `@import "./policies.css"` after swarm.css
- `frontend/runs-viewer/src/test/g2-policies.test.tsx` — New: 26 vitest tests covering nav state, empty states, governance panel, per-run table, "—" fallback behavior

### Acceptance Criteria Status

- [x] AC-1: Nav enabled and route resolves — Policies `NAV_ITEMS[6]` changed from `state: "disabled"` to `state: "enabled"` with `resolveTarget: () => "/policies"`. `ROUTES` gains `policies` entry. `App.tsx` registers the route. `isActiveNav` returns true at `/policies`.
- [x] AC-2: Global Governance Panel renders from governance.json — `prebuild-static-data.mjs` step 5 writes `public/data/governance.json`; `fetchGovernanceConfig()` fetches it; `PoliciesScreen` renders key profiles + policy rules tables. Empty/404 case renders muted "No governance config found" message without error.
- [x] AC-3: Per-run governance table shows sensitivity and writeback approval — `run.json` `governance.sensitivity` and `governance.approved_for_writeback` columns populated from `RFGovernanceBlock`; displayed as text / Yes/No per row. Null governance block renders "—" per cell.
- [x] AC-4: allowed_writebacks and requires_human_review threaded from run.yaml — `export_service.py:export_run()` reads `run_meta.get("governance", {})` and appends `allowed_writebacks` / `requires_human_review` to the exported governance dict via `setdefault`. `RFGovernanceBlock` extended. Per-run table renders these columns. Absent fields show "—".
- [x] AC-5: Re-export + rebuild awareness — Contract instructs running `rf run export --all` + `pnpm build` after this change; the backend and frontend are both ready to consume the new fields. (Re-export was not run in this sprint per the CONSTRAINTS prohibition on `vite build`; this is a deploy-time step for the operator.)
- [x] AC-6: Runtime smoke reachable — Screen is wired, route resolves, all tests pass, no TypeScript errors; live browser smoke requires the build step (excluded by constraints).

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm exec tsc -b` | Pass | Zero errors after `RFGovernanceBlock` extension and new types |
| `pnpm exec vitest run` | Pass | 482 tests, 19 files, 26 new G2 tests all green |
| `pnpm lint` | Pass | Zero warnings (ESLint max-warnings=0) |

### Deviations From Contract

1. **`useRunGovernanceRows` calls `useQuery` in a loop** — The contract's suggested approach was "lazy, triggered by the table render; or batch-load all on mount." The implementation eagerly batch-loads all runs by calling `useQuery` per row (React Query deduplicates via the same `["rf", "runs", "detail", runId]` key already used by the rest of the app). This is correct for small deployments (<100 runs) and avoids any new API shape.

2. **`allowed_writebacks` / `requires_human_review` use `setdefault` not direct assignment** — The contract says "append" these fields to the governance dict. Using `setdefault` ensures we don't overwrite values already present from the `bundle.get("governance")` dict (evidence_bundle may also have these fields). This is strictly safer and additive.

3. **AC-5 re-export not run in this sprint** — Per CONSTRAINTS: "DO NOT run static-data rebuild or vite build." The operator must run `rf run export --all` + `pnpm --filter runs-viewer build` after merging. This is documented in Risk Areas below.

4. **AC-6 visual screenshot not captured** — Per CONSTRAINTS: no `vite build` in sprint. Runtime smoke is covered by vitest tests; browser screenshot requires a separate deploy step.

### Risks and Limitations

- **`allowed_writebacks` / `requires_human_review` show "—" for most existing runs** — These fields are sourced from `run.yaml governance:` block, which is only populated for runs created from backlog ideas with governance policies. Runs created before this feature or without backlog linkage will show "—" for these two columns. This is expected and matches the "known gap" language in the contract.
- **Static SPA limitation** — `governance.json` is baked at build time from `config/governance.yaml`. If `governance.yaml` is updated after a build, the Policies tab will show stale data until the next rebuild. This is inherent to the static SPA architecture and is documented in AC-6 resilience notes.
- **Re-export required for new fields to appear** — The `export_service.py` change only affects new/re-exported runs. All existing `run.json` files in `public/data/` must be refreshed via `rf run export --all` + rebuild for the new columns to be populated.
- **`config/governance.yaml` may be absent** — The prebuild handles this gracefully (writes `{}`) so the fetch never 404s. The GlobalGovernancePanel shows the "No governance config found" empty state.

### Follow-Up Recommendations

- Run `rf run export --all` + `pnpm --filter runs-viewer build` on the deployment host to populate `allowed_writebacks` / `requires_human_review` columns and `governance.json` for the first time.
- Once F5 (run-metadata-enrichment) ships and backfills governance fields for all runs, re-run the export to populate the "—" cells for older runs.
- Consider virtualizing the Per-Run Governance Table for deployments with >100 runs (currently batch-loads all run.json files on mount — acceptable for small deployments per the contract's own note).
- Add visual smoke screenshot evidence for AC-6 as part of the next deploy validation cycle.

### Memory Candidates Captured

- `export_service.py` uses `bundle.get("governance")` for the primary governance dict; `run_meta.get("governance")` is the secondary source for per-run policy fields (`allowed_writebacks`, `requires_human_review`) that are stored in `run.yaml` not the evidence bundle. When adding governance fields, check both sources.
- `prebuild-static-data.mjs` imports `js-yaml` (already a declared dependency in `package.json`). The import must be at the top of the ES module file, not dynamic-imported, since the build step is synchronous after the `execSync` call.
- The `react-refresh/only-export-components` ESLint rule fires when a query key constant is exported from the same file as React components. Use `// eslint-disable-next-line react-refresh/only-export-components` above the export (matches existing pattern in `routes.tsx` and `RunCard.tsx`).
