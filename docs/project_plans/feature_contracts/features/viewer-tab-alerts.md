---
title: "Feature Contract: Alerts Tab \u2014 Cross-Run Attention Feed"
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-20
updated: '2026-06-21'
feature_slug: viewer-tab-alerts
category: features
estimated_points: 5
tier: 1
owner: nick
priority: medium
risk_level: low
changelog_required: false
related_documents:
- docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
- docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
audience:
- ai-agents
- developers
---

# Feature Contract: Alerts Tab — Cross-Run Attention Feed

## 1. Goal

Enable the Alerts top-level nav tab by implementing a cross-run attention feed screen that aggregates
verification failures, unsupported/contradicted claims, dangling sources, redacted sources, and
needs-human-review signals from all loaded runs, derived entirely from data already present in
existing `run.json` exports and the `summarizeRunAttention` utility in `lib/runs.ts`.

---

## 2. User / Actor

- **Primary user**: Nick (LAN operator) reviewing the research foundry output portfolio and needing
  a single surface to triage quality issues across multiple runs without opening each run individually.
- **Secondary users**: Any future developer running the viewer who wants a quick health-at-a-glance
  across all exported runs.

---

## 3. Job To Be Done

When **reviewing the research foundry output after a batch of runs completes**, the user wants to
**scan a consolidated list of attention signals from all runs in one place**, so they can **quickly
identify which runs need follow-up (failed checks, disputed claims, dangling sources, redactions)
and prioritize triage without navigating into each run individually**.

---

## 4. Scope

### In Scope

- Enable the Alerts nav entry in `AppShell.tsx` (change `state: "disabled"` → `state: "enabled"`,
  set `resolveTarget: () => "/alerts"`).
- Register the `/alerts` route in `app/routes.tsx` and wire it to a new `AlertsFeed` screen component.
- New screen `screens/AlertsFeed.tsx`: loads `index.json` to get all run summaries, then loads each
  run's full `run.json` (via existing `client.ts` fetch helpers), calls `summarizeRunAttention(run)`
  for each, and renders a feed of alert rows grouped by run.
- Each alert row shows: run ID (or title via `titleFromSlug`), the alert category (failed checks,
  warning checks, unsupported claims, mixed/contradicted claims, dangling sources, redacted sources,
  empty inference basis, schema mismatch), and a count or flag value from `RunAttentionSummary`.
- Rows with zero-alert runs are hidden by default (show only runs that have at least one non-zero
  alert field or `schemaMismatch: true`).
- Empty state when no runs have any alerts: a clean zero-alert confirmation message.
- Each row links to the relevant run detail page (`/runs/:runId`) so the user can drill in.
- Graceful loading state while per-run JSON files are being fetched (progressive render acceptable —
  show rows as they resolve).
- Graceful error state if a per-run fetch fails (show the run ID with an "unavailable" indicator,
  do not crash the whole feed).

### Out of Scope

- No new backend export fields: this feature uses only data already present in `run.json` (no
  changes to `export_service.py`, no re-export task).
- No governance.py integration or `requires_human_review` flag threading (that field is not in the
  current `RFRunExport` schema; noted as P1 if added via F5 metadata enrichment).
- No mutation of run data (viewer is read-only).
- No per-alert filtering or faceting UI (P1 enhancement).
- No alerts notification/badge on the nav entry (P1).
- No cross-tab alert counts on the portfolio RunCards (P1).
- Dependency on F5 run-metadata-enrichment (this tab uses only existing `run.json` data; starts
  before F5).

---

## 5. UX / Behavior Requirements

- Navigating to `/alerts` via the Alerts nav item renders the `AlertsFeed` screen inside the
  existing `AppShell` layout with the Alerts nav item highlighted as active.
- On mount, the screen fetches `index.json` to enumerate all known run IDs, then fires parallel
  fetches for each run's `run.json`. A loading spinner or skeleton is shown until results begin
  arriving.
- As each run resolves, if `summarizeRunAttention(run)` produces at least one non-zero field or
  `schemaMismatch: true`, a run alert card/row is rendered. Zero-alert runs are suppressed.
- Each alert card displays:
  - Run title (from `deriveRunTitle(run)` if full export is available, fallback `titleFromSlug(run.run_id)`).
  - Run ID in a monospace chip (secondary label).
  - Per-signal rows: only signals with value > 0 (or `true`) are shown. Labels and counts:
    - `failedChecks` → "Failed verification checks: N"
    - `warningChecks` → "Warning checks: N"
    - `unsupportedClaims` → "Unsupported claims: N"
    - `mixedClaims` → "Mixed/contradicted claims: N"
    - `danglingSources` → "Dangling sources: N"
    - `redactedSources` → "Redacted sources: N"
    - `emptyInferenceBasis` → "Inferences with empty basis: N"
    - `schemaMismatch` → "Schema version mismatch" (flag, no count)
  - A "View run" link navigating to `/runs/:runId`.
- If all fetches complete with zero alerts across all runs: render an empty-state panel with the
  message "No attention signals — all runs look clean."
- If a per-run fetch errors: render a placeholder row for that run ID showing "Run data unavailable."
  Do not block rendering of other rows.
- The Alerts nav item is always-enabled (not contextual); it does not require a run to be selected.

---

## 6. Data Requirements

- **Entities read (no writes)**: `public/data/index.json` (list of run summaries) and
  `public/data/<runId>/run.json` (full `RFRunExport` per run).
- **No new export fields**: all required data is present in the existing `run.json` schema 1.1
  (`verification.checks`, `claims[].status`, `claims[].sources[].dangling`,
  `claims[].sources[].resolved`, `claims[].claim_type`, `claims[].inference_basis`,
  `schema_version`, `sensitivity_threshold`).
- **No schema changes** to `run-export.ts` required for this tab (existing `RFRunExport` and the
  `summarizeRunAttention` function in `lib/runs.ts` at lines 107-134 are sufficient).
- **State**: component-local React state (fetch results map keyed by `run_id`). No global store
  changes required.
- **Storage**: none (read-only static data fetch).

---

## 7. API / Integration Requirements

**New or modified endpoints**: None. Alerts tab reads the same static files the rest of the viewer
uses.

**Internal service dependencies**:
- `api/client.ts` — use existing `fetchRunIndex()` (or equivalent) to load `index.json` and
  `fetchRunExport(runId)` (or equivalent) to load per-run `run.json`. If these helpers do not
  already exist by name, follow their existing patterns for constructing the fetch URL from
  `import.meta.env.VITE_DATA_BASE_URL` or the configured base path.
- `lib/runs.ts:summarizeRunAttention` (lines 118-134) — call for each loaded `RFRunExport`.
- `lib/runs.ts:deriveRunTitle` (lines 193-202) and `titleFromSlug` (lines 245-254) — for display.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `app/AppShell.tsx` — NAV_ITEMS array for nav registration; `resolveTarget` returning the route path.
- `app/routes.tsx` — `ROUTES` record for route path/label, `ScreenRoute` interface for the element
  binding. Add `"alerts"` to the `RouteName` union and to the `ROUTES` record.
- Screen files under `screens/` — follow existing screen component conventions (e.g., `RunList.tsx`,
  `RunDetail.tsx`): named export, no default export, CSS class prefix `rv-`.
- Fetch patterns in `api/client.ts` — do not introduce a new HTTP client library.
- `lib/runs.ts` — call the existing exported functions; do not duplicate their logic in the screen.

**Must not change** (protected areas):
- `lib/runs.ts:summarizeRunAttention` — consume it, do not modify it.
- `RFRunExport` and `RFRunSummary` types in `types/rf/run-export.ts` — no changes needed for this
  tab (do not add fields; that is F5 scope).
- Existing route behavior for `/runs` and `/runs/:runId`.
- `AppShell.tsx` nav rendering logic beyond the one NAV_ITEMS entry change.

**New dependencies:**
- Allowed? **No** — no new npm packages. All required utilities (`summarizeRunAttention`,
  `deriveRunTitle`, `titleFromSlug`, fetch client) already exist in the codebase.

---

## 9. Acceptance Criteria

#### AC G3-1: Alerts nav item is enabled and routes correctly
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: NAV_ITEMS entry for "Alerts" has `state: "enabled"` and
  `resolveTarget: () => "/alerts"`; the `/alerts` path is registered in `ROUTES` and bound to
  `AlertsFeed` screen element.
- resilience: N/A (static config).
- visual_evidence_required: screenshot showing Alerts nav item is clickable (not greyed out) and
  clicking it navigates to `/alerts` with the Alerts item highlighted active.
- verified_by: [runtime-smoke]

#### AC G3-2: AlertsFeed screen renders inside AppShell at `/alerts`
- target_surfaces:
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx (new file)
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: Visiting `/alerts` renders `AlertsFeed` inside the shell `<Outlet>` with
  correct nav highlighting.
- resilience: Screen renders without crashing even when `index.json` returns zero runs.
- visual_evidence_required: screenshot of the Alerts screen at `/alerts` with shell nav visible.
- verified_by: [runtime-smoke, unit-test-screen-mount]

#### AC G3-3: Feed aggregates attention signals across all runs using `summarizeRunAttention`
- target_surfaces:
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx
- propagation_contract: For each run in `index.json`, `AlertsFeed` fetches the full `run.json`,
  calls `summarizeRunAttention(run)`, and includes an alert card for that run if any field of
  `RunAttentionSummary` is non-zero or `schemaMismatch === true`. The eight signal categories
  (failedChecks, warningChecks, unsupportedClaims, mixedClaims, danglingSources, redactedSources,
  emptyInferenceBasis, schemaMismatch) are all surfaced with human-readable labels and values.
- resilience: If a `run.json` fetch fails, that run shows a "Run data unavailable" placeholder;
  remaining runs continue to render. If a run has all-zero signals it is suppressed from the feed.
- visual_evidence_required: false
- verified_by: [unit-test-aggregation]

#### AC G3-4: Empty state when no runs have alerts
- target_surfaces:
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx
- propagation_contract: When all fetches complete and zero runs have any non-zero alert signal,
  the screen renders an empty-state message (e.g., "No attention signals — all runs look clean.")
  with no alert cards.
- resilience: Works correctly when `index.json` is empty (zero runs) or all runs are clean.
- visual_evidence_required: false
- verified_by: [unit-test-empty-state]

#### AC G3-5: Run title display with fallback chain
- target_surfaces:
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx
- propagation_contract: Each alert card shows a human-readable title derived from
  `deriveRunTitle(run)` if the full export is available (report_draft frontmatter H1 / context /
  intent_id slug), falling back to `titleFromSlug(run.run_id)` if `deriveRunTitle` returns null/empty.
  The raw `run_id` is always shown as a secondary monospace label.
- resilience: Older runs that have no `report_draft` or `context` still display a slug-derived
  title rather than an empty or blank label.
- visual_evidence_required: false
- verified_by: [unit-test-title-fallback]

#### AC G3-6: "View run" navigation link per alert card
- target_surfaces:
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx
- propagation_contract: Each alert card contains a navigable link (React Router `<Link>`) pointing
  to `/runs/:runId` (using `encodeURIComponent(run.run_id)` to match existing nav conventions).
- resilience: Link is rendered even when some signal counts are zero (as long as the card is shown
  at all).
- visual_evidence_required: false
- verified_by: [unit-test-card-link]

#### AC G3-7: Loading state while per-run fetches are in-flight
- target_surfaces:
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx
- propagation_contract: While `index.json` or any per-run `run.json` is pending, a loading
  indicator (spinner or skeleton) is shown. Progressive rendering is acceptable — already-resolved
  run cards may appear while others are still loading.
- resilience: Loading state clears correctly even if some fetches error.
- visual_evidence_required: false
- verified_by: [unit-test-loading-state]

#### AC G3-8: Runtime smoke — Alerts tab works end-to-end in the built app
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
    - frontend/runs-viewer/src/screens/AlertsFeed.tsx
- propagation_contract: After `pnpm --filter runs-viewer build` (with existing static data), the
  built SPA at `localhost:3030` (or preview server) renders the Alerts tab without a white-screen
  error; at least one alert card or the empty-state panel is visible.
- resilience: Build must succeed with zero TypeScript errors (`tsc --noEmit` clean).
- visual_evidence_required: screenshot of the built app showing Alerts screen with content.
- verified_by: [runtime-smoke]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` (zero errors, excluding known pre-existing test errors)
- [ ] **Lint** passes: `npx eslint frontend/runs-viewer/src --ext .ts,.tsx`
- [ ] **Build** passes: `pnpm --filter runs-viewer build` succeeds
- [ ] **Unit tests** added for `AlertsFeed` covering: aggregation logic (AC G3-3), empty state (AC G3-4),
      title fallback chain (AC G3-5), card link href (AC G3-6), loading state (AC G3-7)
- [ ] **Relevant tests pass**: `pnpm --filter runs-viewer test`
- [ ] **Runtime smoke** (AC G3-8): dev or preview server shows Alerts screen at `/alerts` with nav
      item enabled and at least one alert card or empty-state panel visible
- [ ] **No unrelated changes** introduced (existing routes, nav items, and lib functions unchanged)

---

## 11. Risk Areas

- **Parallel fetch waterfall**: fetching full `run.json` for every run on mount could be slow if
  the portfolio is large. Mitigate: use `Promise.allSettled` for parallelism; show progressive
  results. P1: cap to first N runs or paginate. No architectural risk — pattern is established.
- **`deriveRunTitle` requires full `RFRunExport`**: the function signature (`lib/runs.ts:193`) takes
  `RFRunExport`, which is only available after the per-run fetch. The list-view `RFRunSummary` in
  `index.json` lacks `report_draft` and `intent_id`. This is expected — the screen fetches full
  exports for the alert-bearing runs, so `deriveRunTitle` receives a valid argument. No risk.
- **`RouteName` union extension**: `app/routes.tsx` exports `RouteName = "runList" | "runDetail"`.
  Adding `"alerts"` extends the union; verify no exhaustive switch in the codebase breaks
  (search for `RouteName` usages before committing).
- **No `summarizeRunAttention` changes needed**: the function already covers all eight signal
  categories (verified lines 107-134). Risk of logic drift is low since the function is imported,
  not copied.
- **`needs-human-review` is not in current export schema**: the brief mentions it as an alert
  category, but `RunAttentionSummary` (lines 107-116) does not include a `needsHumanReview` field —
  it is a governance field not yet threaded to the export. Do not add it here; note as P1 pending F5.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):

1. **Extend routes**: In `app/routes.tsx`, add `"alerts"` to `RouteName`, add entry to `ROUTES`
   (`{ path: "/alerts", label: "Alerts" }`), import and wire the new `AlertsFeed` screen element
   in the router (wherever `ScreenRoute` array is constructed — trace from `main.tsx` or the root
   router setup).
2. **Enable nav**: In `app/AppShell.tsx`, change the Alerts `NAV_ITEMS` entry:
   `state: "enabled"`, `resolveTarget: () => "/alerts"`, remove `disabledReason`.
   Add `"alerts"` to the active-nav detection in `isActiveNav()` (or equivalent function) so the
   nav item highlights when at `/alerts`.
3. **Create `screens/AlertsFeed.tsx`**: Named export `AlertsFeed`. On mount:
   - Fetch `index.json` using the existing client helper to get run IDs.
   - `Promise.allSettled` over per-run `run.json` fetches.
   - For each settled result: if fulfilled, call `summarizeRunAttention(run)`; if rejected, record
     an error placeholder.
   - Filter to runs with at least one alert signal.
   - Render: loading state → alert cards → empty state (if zero alerts).
4. **Alert card**: a `<div className="rv-alert-card">` (or similar) per run. Show title, run ID
   chip, signal rows (only non-zero signals), "View run" `<Link>`.
5. **Add tests** in `src/__tests__/` or co-located `AlertsFeed.test.tsx` covering the scenarios
   in AC G3-3 through G3-7. Mock `summarizeRunAttention` with fixture data.
6. **Runtime smoke**: run `pnpm --filter runs-viewer dev`, navigate to `/alerts`, confirm content.

**Similar existing code**:
- `screens/RunList.tsx` — existing screen mounted at `/runs`; follow its shell/layout conventions.
- `lib/runs.ts:summarizeRunAttention` (lines 118-134) — the core aggregation function; import and
  call, do not reimplement.
- `lib/runs.ts:deriveRunTitle` (lines 193-202), `titleFromSlug` (lines 245-254) — title resolution.
- `api/client.ts` — fetch client; follow existing fetch patterns for `index.json` and per-run JSON.

**Known gotchas**:
- `RouteName` is a string literal union in `routes.tsx` (line 10); extending it is safe but verify
  no exhaustive type check elsewhere constrains it (e.g., a `Record<RouteName, ...>` map).
- The `isActiveNav()` function in `AppShell.tsx` (lines ~105-111) checks specific pathnames/views;
  add `/alerts` to the "always match by pathname prefix" logic so the Alerts nav item stays
  highlighted while at `/alerts`.
- `shouldRedactSource` in `lib/runs.ts` (line 98) used by `summarizeRunAttention` checks
  `sensitivity_threshold` from the run export. The count reflects threshold-aware redaction — no
  special handling needed in `AlertsFeed`.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: list of all modified/new files with brief reason
- **Tests run**: what tests were added/updated and results
- **Validation results**: table of all validation commands and their results (pass/fail/not applicable)
- **Deviations from contract**: any material changes to the contract during implementation and why
- **Risks / Limitations**: any remaining risks or known limitations (specifically: `needsHumanReview`
  deferred to F5; parallel fetch performance if portfolio grows large)
- **Follow-up recommendations**: P1 items (governance `needsHumanReview` signal, nav badge counts,
  per-RunCard alert indicators, feed filtering/faceting)

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (5 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration

**Reviewer**: `task-completion-validator` (mandatory)

**Dependency note**: G3 is the LEAST data-dependent of the G1–G6 tab contracts. It uses only data
already present in existing `run.json` exports and the existing `summarizeRunAttention` utility.
It CAN start before F5 (run-metadata-enrichment) is complete.

**Related Documents**:
- `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md` — parent sub-epic index
- `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md` — top-level epic
- `frontend/runs-viewer/src/lib/runs.ts` — `summarizeRunAttention`, `deriveRunTitle`, `titleFromSlug`
- `frontend/runs-viewer/src/app/AppShell.tsx` — NAV_ITEMS, `isActiveNav`
- `frontend/runs-viewer/src/app/routes.tsx` — `RouteName`, `ROUTES`

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation.

- **Scope is FE-only**: no backend changes, no `export_service.py` changes, no re-export task.
- **No new npm dependencies**: everything needed is already in the codebase.
- **`summarizeRunAttention` is the source of truth** for what counts as an alert signal; do not
  add logic outside it (the `needsHumanReview` omission is intentional — deferred to F5).
- If a `run.json` fetch is slow or fails, degrade gracefully — do not block the entire feed.
- Stay within scope. The reviewer will check for scope drift into F5 territory (new export fields,
  type changes) or F2 territory (modal expansion).

---

## Completion Report

### Summary

Implemented the Alerts tab (G3) end-to-end as a new `AlertsFeed` screen at `/alerts`. The screen fetches the run index and all per-run exports in parallel, calls `summarizeRunAttention()` for each, and progressively renders alert cards for runs with any non-zero signal. Clean runs are suppressed. A zero-alert empty state is shown when all runs are clean. Per-run fetch errors show a placeholder card without blocking the rest of the feed. All eight signal categories (failedChecks, warningChecks, unsupportedClaims, mixedClaims, danglingSources, redactedSources, emptyInferenceBasis, schemaMismatch) are displayed with human-readable labels.

### Files Changed

- `frontend/runs-viewer/src/app/AppShell.tsx` — enabled Alerts NAV_ITEM; added isActiveNav branch for /alerts
- `frontend/runs-viewer/src/app/routes.tsx` — added "alerts" to RouteName union and ROUTES record
- `frontend/runs-viewer/src/app/App.tsx` — registered /alerts route bound to AlertsFeed
- `frontend/runs-viewer/src/screens/AlertsFeed.tsx` — new screen component (named export)
- `frontend/runs-viewer/src/styles/alerts.css` — BEM rv-alerts* / rv-alert-card* styles using existing design tokens
- `frontend/runs-viewer/src/styles/index.css` — added @import for alerts.css
- `frontend/runs-viewer/src/test/g3-alerts.test.tsx` — 33 new tests covering all ACs

### Acceptance Criteria Status

- [x] AC G3-1: Alerts nav item is enabled and routes correctly — NAV_ITEMS entry has state: "enabled", resolveTarget: () => "/alerts"; /alerts registered in ROUTES and App.tsx
- [x] AC G3-2: AlertsFeed screen renders inside AppShell at /alerts — route registered, named export consumed, renders within Outlet
- [x] AC G3-3: Feed aggregates attention signals using summarizeRunAttention — all 8 signal categories rendered; per-run error shows placeholder; zero-signal runs suppressed
- [x] AC G3-4: Empty state when no runs have alerts — "No attention signals — all runs look clean." panel shown when all fetches complete with zero alert runs
- [x] AC G3-5: Run title display with fallback chain — deriveRunTitle(run) used, fallback to titleFromSlug(run.run_id); run_id chip always shown
- [x] AC G3-6: "View run" navigation link per alert card — React Router Link to /runs/:runId with encodeURIComponent
- [x] AC G3-7: Loading state while per-run fetches are in-flight — loading spinner shown during index and per-run fetches; progressive render supported
- [x] AC G3-8: Runtime smoke — build passes with zero TypeScript errors; existing routes unaffected

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm test` | Pass | 433/433 tests pass (17 test files) |
| `pnpm lint` | Pass | 0 warnings, --max-warnings=0 |
| `pnpm build` | Pass | tsc -b clean + vite build succeeds; chunk size warning is pre-existing (React Flow) |

### Deviations From Contract

- **Error placeholder behavior**: `fetchRunDetail` in `client.ts` has a built-in graceful fallback that returns an empty `RFRunExport` shape (with `schema_version: "1.0"`) rather than throwing on 404/static fetch error. Tests for the error path use `vi.spyOn(clientModule, "fetchRunDetail").mockRejectedValue(...)` to simulate loopback-mode network failures, which is the only realistic throw path. The error UI renders correctly in that scenario.
- No other deviations from contract.

### Risks and Limitations

- **`needsHumanReview` deferred to F5**: `summarizeRunAttention` does not include a `needsHumanReview` field; this is intentional per contract §4 Out of Scope. Deferred to F5 metadata enrichment.
- **Parallel fetch performance at scale**: all per-run `run.json` files are fetched in parallel on mount. With large portfolios (50+ runs) this could be slow. Mitigated by `Promise.allSettled` with progressive rendering. P1: cap to first N runs or paginate.
- **404 static fetch errors swallowed by client**: `fetchRunDetail` returns a minimal empty run on 404 (schema_version: "1.0" → triggers schemaMismatch). This is consistent with existing client behavior for all other screens.

### Follow-Up Recommendations

- P1: `needsHumanReview` governance signal (pending F5 run-metadata-enrichment adding `requires_human_review` to `RFRunExport`)
- P1: nav badge count showing number of alerted runs on the Alerts nav item
- P1: per-RunCard alert indicator in the Portfolio view
- P1: feed filtering/faceting by signal category
- P1: cap parallel fetches or paginate for portfolios > 20 runs

### Memory Candidates Captured

- `fetchRunDetail` in `client.ts` has a built-in graceful fallback on 404 — returns empty `RFRunExport` with `schema_version: "1.0"` rather than throwing. Tests for the error path must mock at the module level (`vi.spyOn(clientModule, "fetchRunDetail")`).
- Alert cards use `data-testid="alert-card"` for normal alert runs and `data-testid="alert-card-error"` for runs where `fetchRunDetail` threw; these are mutually exclusive.
