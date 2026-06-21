---
title: "Feature Contract: Swarm Tab — Visualize swarm_plan, Agents, and Routing Decision"
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-20
updated: 2026-06-21
feature_slug: "viewer-tab-swarm"
category: "features"
estimated_points: 5
tier: 1
owner: nick
priority: medium
risk_level: low
changelog_required: false
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
  - docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
  - docs/project_plans/feature_contracts/features/viewer-tab-policies.md
  - docs/project_plans/feature_contracts/features/viewer-tab-alerts.md
  - docs/project_plans/feature_contracts/features/viewer-tab-library.md
  - docs/project_plans/feature_contracts/features/viewer-tab-settings.md
  - docs/project_plans/feature_contracts/features/viewer-tab-help.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected:
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/app/routes.tsx
  - frontend/runs-viewer/src/app/App.tsx
  - frontend/runs-viewer/src/screens/SwarmScreen.tsx
  - frontend/runs-viewer/src/styles/swarm.css
  - frontend/runs-viewer/src/styles/index.css
  - frontend/runs-viewer/src/test/g1-swarm.test.tsx
---

# Feature Contract: Swarm Tab — Visualize swarm_plan, Agents, and Routing Decision

## 1. Goal

Enable the hard-disabled **Swarm** top-level navigation tab, adding a per-run screen that
visualizes the swarm execution plan, participating agents, and the routing decision/rationale
sourced from `RFRunExport.context` — with graceful empty states when context data is absent.

---

## 2. User / Actor

- **Primary user**: Nick (sole LAN operator) reviewing how a research run was orchestrated —
  which agent was selected, why, and how the swarm plan was structured.
- **Secondary users**: Developers inspecting swarm behavior during RF development.

---

## 3. Job To Be Done

When **reviewing a completed research run**, the user wants to **see at a glance how the swarm was
orchestrated** — which agents participated, what the routing decision was, and the rationale behind
it — so they can **diagnose orchestration choices, understand run quality, and improve future
swarm configurations**.

---

## 4. Scope

### In Scope

- Enable the Swarm item in `NAV_ITEMS` (remove `'not implemented'` / disabled state) in
  `AppShell.tsx`.
- Add a `/runs/:runId/swarm` route in `app/routes.tsx` and resolve it in `isActiveNav()`.
- Implement a `SwarmScreen` (new file: `frontend/runs-viewer/src/screens/SwarmScreen.tsx`) that
  renders:
  - **Routing Decision card**: `context.routing_decision` field (agent name + rationale prose)
    or empty state when absent.
  - **Swarm Plan section**: structured display of `context.swarm_plan` entries (agent tasks,
    sequence/parallel breakdown, or raw JSON fallback when structure is unrecognized).
  - **Agents list**: derived from swarm_plan participants or routing_decision target — name,
    role, model profile reference where available.
- Graceful empty state (informative placeholder) when `context` is absent or both
  `swarm_plan` and `routing_decision` are null/undefined — covers all runs exported before F5.
- Wire the Swarm nav item so it is context-sensitive: visible only when a run is selected
  (consistent with Runs/Reports/Ledger behavior per `§1.1`).
- Runtime smoke task: verify the screen renders without errors in both data-present and
  data-absent scenarios.

### Out of Scope

- Adding `swarm_plan` or `routing_decision` to the export (that is F5, Phase 7 — this contract
  depends on F5 having threaded those fields; see Data Requirements).
- Editing or re-running swarms from the viewer (read-only SPA).
- Graph/DAG visualization of the swarm plan (plain structured list/cards is sufficient for v2.2;
  graph is a P1 enhancement).
- Settings, Help, Policies, Alerts, Library tabs (separate G2–G6 contracts).
- Any changes to `RFRunExport` schema or `export_service.py` (owned by F5).

---

## 5. UX / Behavior Requirements

- The **Swarm** nav item appears in the top nav alongside Runs/Reports/Ledger when a run is
  selected. Clicking it navigates to `/runs/:runId/swarm`.
- `isActiveNav('swarm')` returns true when `pathname` ends with `/swarm` and a `runId` is
  active — consistent with the existing pattern for other contextual nav items (`§1.1`).
- The screen has a consistent page header (run title + run ID) matching the style of Overview
  and other detail screens.
- **Routing Decision card** (top of page):
  - When `context.routing_decision` is present: display agent name prominently + rationale
    prose in a readable card.
  - When absent: show a muted placeholder "No routing decision recorded for this run."
- **Swarm Plan section** (below routing decision):
  - When `context.swarm_plan` is a non-empty value: render each plan entry as a labeled card
    or list row — at minimum show the raw structure (agent, task description, status if present)
    in a readable format. If the shape is an array, map it; if it is an object/string, show it
    in a pre-formatted block.
  - When absent: show a muted placeholder "No swarm plan recorded for this run."
- **Agents derived list** (below or alongside swarm plan): deduplicate agent names mentioned
  across `swarm_plan` and `routing_decision`; display as a compact list of chips or rows.
  When empty: omit the section entirely.
- **Full empty state** (when `context` itself is null/absent): show a single full-page
  placeholder — "Swarm data not available. Re-export this run after updating to v2.2+ to see
  swarm details." This educates the user without alarming them.
- Navigation is keyboard-accessible: the Swarm nav item is reachable via Tab, activated via
  Enter/Space, and the route change does not trap focus.

---

## 6. Data Requirements

- **Source fields** (all from `RFRunExport.context`, typed in `run-export.ts`):
  - `context?: { routing_decision?: unknown; swarm_plan?: unknown; research_brief_md?: string;
    upstream_entities?: unknown }` — the `context` block is already typed as optional in schema
    1.1 (`§1.10`). `routing_decision` and `swarm_plan` are listed as v2-optional fields.
- **Dependency on F5**: F5 Phase 7 must thread `context.swarm_plan` and
  `context.routing_decision` into `export_service.export_run()` and re-export all runs before
  those fields appear in `public/data/<id>/run.json`. This contract's screen is authored
  independently but live data requires F5 to have run.
- **New TS types** (this contract): if `routing_decision` / `swarm_plan` shapes are known after
  F5, narrow the `unknown` type in `run-export.ts` to a concrete interface. If shape is
  unknown at sprint time, keep `unknown` and use runtime type-guards in `SwarmScreen.tsx` to
  distinguish expected shape vs. fallback-to-raw.
- **No new export fields** are introduced by this contract — it reads existing (F5-exported)
  fields only.
- **No index.json changes** needed — swarm data is run-detail only (not needed for list views).
- **No backend writes** — viewer is read-only.

---

## 7. API / Integration Requirements

**New or modified endpoints:** None — static data SPA; data read from
`public/data/<runId>/run.json` via existing `client.ts` fetch path.

**External service calls:** None.

**Internal service dependencies:**
- `frontend/runs-viewer/src/api/client.ts` — existing `fetchRun(runId)` returns `RFRunExport`;
  `SwarmScreen` consumes this via the same hook/loader pattern as `RunDetail` screens.
- `frontend/runs-viewer/src/app/AppShell.tsx` — nav registration.
- `frontend/runs-viewer/src/app/routes.tsx` — route registration.
- `frontend/runs-viewer/src/types/rf/run-export.ts` — type consumption; optional narrowing of
  `context.swarm_plan` / `context.routing_decision` shapes.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `AppShell.tsx` `NAV_ITEMS` array and `isActiveNav()` logic (`§1.1`) — replicate the exact
  same contextual-nav guard pattern used for Runs/Reports/Ledger.
- `app/routes.tsx` — add route using the same lazy/eager pattern as existing detail routes.
- `screens/` directory — new `SwarmScreen.tsx` follows the same file-placement and export
  conventions as `RunDetail.tsx`, `RunList.tsx`.
- `RFRunExport` type from `run-export.ts` — do not redefine or duplicate; import and use
  directly with type-guards for optional fields.
- Read-only SPA contract — no mutations, no API writes.

**Must not change (protected areas):**
- `export_service.py` or any Python backend code (owned by F5).
- `prebuild-static-data.mjs` export pipeline (F5 concern).
- `RFRunExport` schema_version or top-level shape (F5 owns export schema bumps).
- Existing enabled tabs (Overview, Trust, Ledger, Report, Lineage, Writeback) — no behavioral
  regressions.
- `AppShell.tsx` styling or layout outside the `NAV_ITEMS` entry for Swarm.

**New dependencies:**
- Allowed? **No** — no new npm packages. Use existing React, TypeScript, and any CSS/utility
  patterns already in the runs-viewer package.

---

## 9. Acceptance Criteria

#### AC G1-01: Swarm nav item enabled and navigable
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: `NAV_ITEMS` entry for Swarm has its disabled/not-implemented flag
  removed; route `/runs/:runId/swarm` is registered and renders `SwarmScreen`.
- resilience: if no run is selected, the Swarm nav item is not shown (same contextual guard as
  Runs/Reports/Ledger).
- visual_evidence_required: false
- verified_by: [SMOKE-G1-01]

#### AC G1-02: Routing Decision card renders when data present
- target_surfaces:
    - frontend/runs-viewer/src/screens/SwarmScreen.tsx
- propagation_contract: `run.context.routing_decision` (provided by F5 export) is read and
  displayed in a labeled card showing agent name and rationale.
- resilience: when `context.routing_decision` is absent or null, a muted placeholder
  "No routing decision recorded for this run." is shown instead of a blank or error.
- visual_evidence_required: false
- verified_by: [SMOKE-G1-02, TEST-G1-01]

#### AC G1-03: Swarm Plan section renders when data present
- target_surfaces:
    - frontend/runs-viewer/src/screens/SwarmScreen.tsx
- propagation_contract: `run.context.swarm_plan` (provided by F5 export) is read; if it is
  an array, each entry is rendered as a labeled card/row; if it is an object or string, it is
  shown in a pre-formatted readable block.
- resilience: when `context.swarm_plan` is absent or null, a muted placeholder
  "No swarm plan recorded for this run." is shown.
- visual_evidence_required: false
- verified_by: [SMOKE-G1-02, TEST-G1-02]

#### AC G1-04: Full empty state when context block absent
- target_surfaces:
    - frontend/runs-viewer/src/screens/SwarmScreen.tsx
- propagation_contract: when `run.context` is null/undefined (pre-F5 exported runs), the
  screen shows a single informative placeholder: "Swarm data not available. Re-export this run
  after updating to v2.2+ to see swarm details."
- resilience: no JavaScript error thrown; no blank white screen; existing nav and shell remain
  functional.
- visual_evidence_required: false
- verified_by: [SMOKE-G1-03, TEST-G1-03]

#### AC G1-05: `isActiveNav` highlights Swarm correctly
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: `isActiveNav()` returns true for the Swarm item when
  `pathname` ends with `/swarm` and a `runId` is active; returns false otherwise.
- resilience: does not interfere with Portfolio, Runs, Reports, or Ledger active states.
- visual_evidence_required: false
- verified_by: [TEST-G1-04]

#### AC G1-06: Runtime smoke — data-present scenario
- target_surfaces:
    - frontend/runs-viewer/src/screens/SwarmScreen.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: with a mock `RFRunExport` containing a non-null `context` with both
  `swarm_plan` and `routing_decision`, `SwarmScreen` renders without React errors or
  unhandled exceptions; Routing Decision card and Swarm Plan section both appear.
- resilience: n/a (positive path).
- visual_evidence_required: false
- verified_by: [SMOKE-G1-02]

#### AC G1-07: Runtime smoke — data-absent scenario
- target_surfaces:
    - frontend/runs-viewer/src/screens/SwarmScreen.tsx
- propagation_contract: with a mock `RFRunExport` where `context` is undefined, `SwarmScreen`
  renders the full empty state without errors.
- resilience: verifies R-P2 (FE handles absent field gracefully).
- visual_evidence_required: false
- verified_by: [SMOKE-G1-03]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` (run from `frontend/runs-viewer`) with zero new
      errors.
- [ ] **Lint** passes: ESLint on new/modified files with zero new warnings or errors.
- [ ] **Tests added** (see §12 for test IDs): at minimum one unit test per AC G1-02, G1-03,
      G1-04, G1-05 using React Testing Library + Vitest/Jest; mocked `RFRunExport`.
- [ ] **Smoke tasks pass** (SMOKE-G1-01, SMOKE-G1-02, SMOKE-G1-03): manual or scripted render
      verification in the dev server.
- [ ] **Build passes**: `pnpm --filter runs-viewer build` completes without errors.
- [ ] **No regressions**: existing enabled tabs (Overview, Trust, Ledger, Report, Lineage)
      render without errors after nav changes.
- [ ] **No unrelated changes** introduced outside the Swarm tab nav/route/screen.

---

## 11. Risk Areas

- **Data dependency on F5 (P7)**: `context.swarm_plan` and `context.routing_decision` are only
  populated after F5 Phase 7 threads them into the export. This contract can be implemented
  and merged independently — the empty-state path covers the pre-F5 case — but live data
  requires F5 to have completed and a `rf run export --all` + rebuild to have been run.
  Mitigation: build with strong empty-state handling (AC G1-04) and test with mock data.
- **Unknown swarm_plan shape**: the exact JSON shape of `context.swarm_plan` is inferred from
  field names but not formally specified (no JSON Schema today per §1.12). Use runtime
  type-guards (`Array.isArray`, `typeof`) and a raw-JSON fallback to avoid rendering failures
  when the shape differs from expectation.
- **isActiveNav extension**: adding a new nav variant must not break the existing Portfolio
  active check (`pathname === '/runs'`) or Runs active check (`routeRunId && view ∈
  {null, overview, trust, lineage, writeback}`). Test the discriminants carefully (§1.1).
- **Route conflict**: ensure `/runs/:runId/swarm` does not shadow or conflict with any
  existing routes (verify against current `app/routes.tsx` route table).

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):
1. **AppShell.tsx**: find the Swarm entry in `NAV_ITEMS` (currently marked `'not implemented'`
   or similar disabled flag, lines ~24-35 per §1.1); remove the disabled flag; add a `href`
   pointing to `/runs/:runId/swarm` (use the same `resolveTarget()` or equivalent helper as
   the Runs contextual link). Update `isActiveNav()` to handle `view === 'swarm'` analogously
   to how it handles other contextual views.
2. **app/routes.tsx**: register route `{ path: '/runs/:runId/swarm', element: <SwarmScreen /> }`
   using the existing lazy/eager pattern. Import `SwarmScreen` (or use `React.lazy`).
3. **SwarmScreen.tsx** (new file, `screens/`): use the existing run-data loader/hook pattern
   (same as RunDetail screens) to obtain `RFRunExport` for the `:runId` param. Render in order:
   - Page header (run title + run ID) — reuse whatever title-display helper F1 introduces
     (`deriveRunTitle` / `titleFromSlug` chain).
   - Routing Decision card.
   - Swarm Plan section.
   - Agents list (derived, deduplicated).
   - Full empty state guard at the top-level if `run.context == null`.
4. **Type-guards**: write narrow helper `isRoutingDecision(v: unknown): v is RoutingDecision`
   and `isSwarmPlanArray(v: unknown): v is SwarmPlanEntry[]` (define minimal interfaces inline
   in `SwarmScreen.tsx` or in a `types/rf/swarm.ts` helper). Keep `run-export.ts` top-level
   type as `unknown` until F5 formalizes the shape.
5. **Tests**: create `SwarmScreen.test.tsx` with three test cases mapped to SMOKE-G1-01 /
   SMOKE-G1-02 / SMOKE-G1-03 / TEST-G1-01..04 using mocked `RFRunExport` objects.

**Similar existing code**:
- Reference: `frontend/runs-viewer/src/screens/RunDetail.tsx` — same loader + header pattern.
- Reference: `frontend/runs-viewer/src/app/AppShell.tsx` lines ~24-35 and ~105-111 — nav
  item structure and `isActiveNav` discriminant pattern.
- Reference: `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` lines
  34-45 — disabled tab pattern (see how `writeback` is conditionally disabled).

**Known gotchas**:
- The `NAV_ITEMS` disabled entry for Swarm may use a string `'not implemented'` as the href
  or a boolean `disabled` prop — inspect the exact shape before editing to avoid type errors.
- `isActiveNav` uses `view` derived from `routeRunId` + URL segments; the new 'swarm' segment
  must be added to the recognized set (§1.1 shows `view ∈ {null, overview, trust, lineage,
  writeback}` — add `'swarm'`).
- F1 title helpers (`deriveRunTitle`, `titleFromSlug`) may not yet be available if F1 has not
  merged; fall back to `run.run_id` in that case and note the deviation in the Completion
  Report.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: list of all modified/new files with brief reason.
- **Tests run**: test IDs (TEST-G1-01..04, SMOKE-G1-01..03) with pass/fail results.
- **Validation results**: table of `tsc --noEmit`, lint, build, regression check — pass/fail.
- **Deviations from contract**: any material changes (e.g., swarm_plan shape differed,
  title helper not yet available from F1) and rationale.
- **Risks / Limitations**: data-dependency note on F5 P7; swarm_plan shape uncertainty.
- **Follow-up recommendations**: once F5 ships, narrow `unknown` types; consider DAG
  visualization as P1 enhancement.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full template.

---

## Metadata & References

**Tier**: 1 (5 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion

**Reviewer**: `task-completion-validator` (mandatory)

**Depends on**: F5 (`run-metadata-enrichment`) Phase 7 for live `context.swarm_plan` +
`context.routing_decision` export data. This contract can be implemented and tested with mock
data before F5 ships; the empty-state path (AC G1-04) covers the interim period.

**Related Documents**:
- Epic brief (source of truth): `.claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md`
- Parent sub-epic: `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md`
- Outer epic: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Data source (§1.10): `frontend/runs-viewer/src/types/rf/run-export.ts` (`RFRunExport.context`)
- Nav source (§1.1): `frontend/runs-viewer/src/app/AppShell.tsx`

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass
validation. Key reminders:

- **Empty state is not optional** — AC G1-04 is a first-class deliverable, not a fallback.
  All pre-F5 runs will hit this path.
- **Do not touch `export_service.py` or the Python backend** — that is F5 scope.
- **Scope ambiguity on swarm_plan shape**: if the actual JSON shape at sprint time differs
  from the inferred structure, use runtime type-guards and the raw-JSON fallback, and
  document the actual shape in the Completion Report.
- **F1 dependency**: if `deriveRunTitle` is not yet available, fall back to `run.run_id` and
  note it as a follow-up item.

Stay within scope. Avoid cleanup, refactors, or feature expansion beyond this contract.
