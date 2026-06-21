---
title: "Feature Contract: Settings Tab — Viewer Config Surface"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-20
updated: 2026-06-20
feature_slug: "viewer-tab-settings"
category: "features"
estimated_points: 3
tier: 1
owner: nick
priority: medium
risk_level: low
changelog_required: false
audience: [ai-agents, developers]
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
  - docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
  - docs/project_plans/feature_contracts/harden-polish/viewer-unredact-lan.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Feature Contract: Settings Tab — Viewer Config Surface

## 1. Goal

Enable the currently hard-disabled Settings nav tab by adding a route and screen that exposes
client-side viewer configuration (sensitivity threshold display toggle, theme, default tab, base
data path), persisted to `localStorage` — no server or export changes required.

---

## 2. User / Actor

- **Primary user**: Nick (operator) — the sole LAN user of the read-only runs-viewer SPA deployed
  at `10.42.10.76:3030`.
- **Secondary users**: Any developer running the viewer locally who wants to tune display behaviour
  without a rebuild.

---

## 3. Job To Be Done

When the operator wants to adjust how the viewer presents run data (e.g. toggle redaction display
after running F4, or change which tab opens by default), they want to open a Settings screen in the
viewer and change a preference, so they can have those preferences take effect immediately without
a rebuild, a code change, or an environment variable rotation.

---

## 4. Scope

### In Scope

- **Enable nav entry**: remove the `'not implemented'` gate for "Settings" in `AppShell.tsx`
  `NAV_ITEMS` and wire the route so clicking the item navigates to `/settings`.
- **Route registration**: add `/settings` route in `app/routes.tsx` (or equivalent router config)
  pointing to the new `SettingsScreen` component.
- **New screen** `frontend/runs-viewer/src/screens/SettingsScreen.tsx` with the following
  preference controls:
  - **Sensitivity threshold display toggle** — mirrors the `VITE_SHOW_ALL` / F4 intent; a toggle
    that sets a `localStorage` flag causing `SourceCard.isRedacted()` to treat all content as
    unredacted (the FE-side display gate bypass from F4 spec §1.8). Labelled "Show all content
    (bypass redaction display)" with a note that the underlying run.json must have been exported
    with `viewer.sensitivity_threshold: client_sensitive` for full text to appear.
  - **Theme selector** — light / dark / system (system = `prefers-color-scheme`). Persist to
    `localStorage`; apply immediately via a CSS class on `<html>` or `<body>`.
  - **Default detail tab** — dropdown matching `DetailTab` enum values
    (`overview | trust | ledger | report | lineage | writeback`); stored in `localStorage`;
    consumed by `coerceDetailTab()` fallback instead of the hard-coded `'overview'` (F1 sets it
    to `'overview'`; Settings should let the user override it).
  - **Base data path** — text input for the static data root (default `'/data'`); stored in
    `localStorage`; consumed by `client.ts` when fetching `index.json` and run bundles. Useful
    for local dev pointing at a different export directory.
- **`useViewerSettings` hook** — centralised hook (`lib/viewerSettings.ts`) that reads/writes
  all settings from `localStorage`, provides defaults, and is consumed by `SettingsScreen` and
  any other component that needs a setting.
- All settings changes take effect immediately (no page reload required where feasible; base data
  path change requires reload — document this clearly in the UI).

### Out of Scope

- Re-exporting run data or modifying `foundry.yaml` (that is F4's job).
- Server-side persistence or user accounts.
- Any new backend/export fields (this is client-side only).
- The `VITE_SHOW_ALL` build-time env var itself (this adds a runtime override on top of it; F4
  manages the env var path).
- Theming implementation beyond a CSS class toggle (full design-token theme system is out of scope).
- Disabling or hiding any other nav tab beyond enabling Settings.
- Help tab content (G6 is a separate contract).

---

## 5. UX / Behavior Requirements

- The Settings nav item in `AppShell.tsx` is enabled (no `'not implemented'` disabled state) and
  active when `pathname === '/settings'`.
- Navigating to `/settings` (or clicking the Settings nav item) renders `SettingsScreen` in the
  main content area using the same AppShell layout as other top-level screens.
- `SettingsScreen` displays a titled page ("Settings") with clearly labelled sections for each
  preference group (e.g. "Display", "Navigation", "Data").
- The sensitivity redaction toggle: when ON, `SourceCard.isRedacted()` returns `false` regardless
  of source sensitivity (localStorage flag `rv_show_all = 'true'`). A read-only info banner under
  the toggle reads: "Run data must be exported with threshold `client_sensitive` for full text to
  appear. See the unredaction guide." The banner is always visible (not conditional on toggle state).
- The theme selector changes the theme immediately on selection (no save button required for theme).
- The default tab dropdown: the selected value is read by `coerceDetailTab()` as the fallback when
  no tab is specified in the URL. If the stored value is not a valid `DetailTab`, fall back to
  `'overview'`.
- The base data path input: changes are saved with an explicit "Save" button (since a reload is
  required). After save, a notice appears: "Reload the page for the new data path to take effect."
- All preferences default to sensible values if not yet stored:
  - Show all content: `false`
  - Theme: `'system'`
  - Default tab: `'overview'`
  - Base data path: `'/data'`
- Settings persist across browser refreshes and tab closes (localStorage).
- No settings reset button is required (P1 / out of scope for this contract).

---

## 6. Data Requirements

- **Entities affected**: no backend entities. All state is `localStorage`-only.
- **New localStorage keys**:
  - `rv_show_all` — `'true' | 'false'` (string; default `'false'`)
  - `rv_theme` — `'light' | 'dark' | 'system'` (default `'system'`)
  - `rv_default_tab` — a valid `DetailTab` string (default `'overview'`)
  - `rv_data_path` — string path (default `'/data'`)
- **State changes**: `useViewerSettings` hook manages reads and writes; components subscribe via
  the hook (re-render on change via a custom event or state setter pattern).
- **Storage implications**: none — no schema migrations, no new tables, no export changes.

---

## 7. API / Integration Requirements

**No new or modified endpoints.** The viewer is a read-only SPA; Settings is client-side only.

**Internal integration points:**

- `frontend/runs-viewer/src/app/AppShell.tsx` — enable Settings `NAV_ITEMS` entry; update
  `isActiveNav()` to recognise `/settings`.
- `frontend/runs-viewer/src/app/routes.tsx` (or equivalent router config) — add `/settings` →
  `SettingsScreen`.
- `frontend/runs-viewer/src/components/RunDetail/detailTabs.ts` — `coerceDetailTab()` reads
  `useViewerSettings().defaultTab` as the fallback instead of hard-coded `'overview'`. The F1
  contract sets the default to `'overview'`; this contract makes it user-configurable.
- `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx` — `isRedacted()` (lines 27-35
  per §1.8) reads `useViewerSettings().showAll`; if `true`, returns `false` regardless of threshold
  comparison.
- `frontend/runs-viewer/src/api/client.ts` — base data path read from `useViewerSettings` (or a
  direct `localStorage` read in the fetch helper) when constructing `index.json` / run bundle URLs.
- Theme: apply `data-theme` attribute (or `rv-theme-light` / `rv-theme-dark` class) on `<html>`.
  Respect `prefers-color-scheme` when `rv_theme === 'system'`.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `frontend/runs-viewer/src/screens/` — file layout, export pattern, CSS module or class-name
  conventions used by `RunList.tsx`, `RunDetail.tsx`.
- `frontend/runs-viewer/src/app/AppShell.tsx` `NAV_ITEMS` structure — enable via the same pattern
  used by enabled tabs (remove/omit the `disabled: true` / `'not implemented'` guard); do not
  invent a new nav registration mechanism.
- React hooks pattern used in `lib/runs.ts`, `lib/rf.ts` — the new `lib/viewerSettings.ts` should
  be a plain module (not a context provider) exporting a hook and direct accessor helpers, matching
  the existing lib style.

**Must not change** (protected areas):
- `rf` CLI, `export_service.py`, `foundry.yaml`, `prebuild-static-data.mjs` — this feature is
  client-side only.
- The `RFRunExport` / `RFRunSummary` types in `run-export.ts` — no new export fields here.
- The `coerceDetailTab` hard-coded `'overview'` change is **additive only**: read localStorage
  first; fall back to `'overview'` when nothing stored. If F1 already changed the fallback to
  `'overview'`, this contract stacks on top and just reads the stored pref before that fallback.

**New dependencies:**
- Allowed? **No** — no new npm packages. Use only browser `localStorage` API, existing React
  patterns, and the established CSS approach already in the project.

---

## 9. Acceptance Criteria

#### AC G5-01: Settings nav is enabled and routes correctly
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: NAV_ITEMS entry for Settings has no `disabled` / `'not implemented'`
  guard; clicking it navigates to `/settings`; `isActiveNav()` returns `true` when
  `pathname === '/settings'`.
- resilience: n/a (no external data dependency)
- visual_evidence_required: screenshot of nav with Settings item active and SettingsScreen visible
- verified_by: [G5-SMOKE-01]

#### AC G5-02: SettingsScreen renders with all four preference controls
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
- propagation_contract: Screen is reachable at `/settings`; it renders sensitivity toggle, theme
  selector, default tab dropdown, and base data path input with their current `localStorage` values
  (or defaults if not yet stored).
- resilience: if any `localStorage` key is absent or malformed, the corresponding control renders
  the documented default value without error.
- visual_evidence_required: screenshot showing SettingsScreen with all four controls
- verified_by: [G5-SMOKE-01]

#### AC G5-03: Sensitivity display toggle wires to SourceCard redaction gate
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
    - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
- propagation_contract: toggling ON sets `rv_show_all = 'true'` in localStorage; `isRedacted()`
  reads the hook/helper and returns `false` for all sources when flag is `'true'`; toggling OFF
  restores normal threshold comparison.
- resilience: if localStorage is unavailable, toggle renders in OFF state and SourceCard falls back
  to threshold comparison (no crash).
- visual_evidence_required: false (unit test sufficient)
- verified_by: [G5-TEST-REDACT]

#### AC G5-04: Theme selector applies immediately
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: selecting a theme writes `rv_theme` to localStorage and immediately sets
  `data-theme` attribute (or CSS class) on `<html>`; `'system'` reads `prefers-color-scheme`
  media query.
- resilience: if stored value is not `'light' | 'dark' | 'system'`, treat as `'system'`.
- visual_evidence_required: false
- verified_by: [G5-TEST-THEME]

#### AC G5-05: Default tab setting is consumed by coerceDetailTab
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
    - frontend/runs-viewer/src/components/RunDetail/detailTabs.ts
- propagation_contract: storing a valid `DetailTab` value via the dropdown causes
  `coerceDetailTab(null)` to return that stored value; if stored value is invalid, falls back to
  `'overview'`.
- resilience: if localStorage is unavailable, `coerceDetailTab` falls back to `'overview'` (same
  as F1 baseline — no regression).
- visual_evidence_required: false
- verified_by: [G5-TEST-DEFAULT-TAB]

#### AC G5-06: Base data path is saved and acknowledged
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: editing the path and clicking Save writes `rv_data_path` to localStorage
  and displays the reload notice; `client.ts` reads the stored path (or default `'/data'`) when
  building fetch URLs.
- resilience: if stored path is empty string, falls back to `'/data'`.
- visual_evidence_required: false
- verified_by: [G5-SMOKE-01]

#### AC G5-07: Settings persist across page refresh
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
- propagation_contract: after setting any preference and refreshing the page, the SettingsScreen
  shows the previously stored value.
- resilience: if localStorage is cleared externally, all controls revert to documented defaults
  without error.
- visual_evidence_required: false
- verified_by: [G5-TEST-PERSIST]

#### AC G5-08: Runtime smoke — SettingsScreen renders without console errors
- target_surfaces:
    - frontend/runs-viewer/src/screens/SettingsScreen.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: `pnpm --filter runs-viewer build` succeeds; navigating to `/settings` in
  the built app produces no JS console errors or React render errors.
- resilience: n/a
- visual_evidence_required: screenshot of `/settings` route in the running app (desktop viewport)
- verified_by: [G5-SMOKE-01]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` (run from `frontend/runs-viewer/`)
- [ ] **Lint** passes: ESLint / project lint command
- [ ] **Build** passes: `pnpm --filter runs-viewer build`
- [ ] **Unit tests** added for `useViewerSettings` hook covering: read defaults, write/read
      round-trip, invalid-value fallback for each key (AC G5-03, G5-04, G5-05, G5-06, G5-07)
- [ ] **Component test** for `SettingsScreen` covering: renders with defaults, toggle interaction
      updates localStorage, coerceDetailTab reads stored default tab
- [ ] **Smoke task G5-SMOKE-01**: start the app (`pnpm --filter runs-viewer dev` or serve built
      output), navigate to `/settings`, confirm all four controls render, confirm no console errors,
      take a screenshot
- [ ] **No unrelated changes** introduced (no changes to `export_service.py`, `run-export.ts`
      types, or any non-Settings screen behaviour beyond the wiring items listed in §7)

---

## 11. Risk Areas

- **Coordination with F4 (viewer-unredact-lan)**: F4 adds the FE display-gate bypass via
  `VITE_SHOW_ALL` env var and a `redacted?: boolean` type field. AC G5-03 adds a runtime-toggle
  path to the same `isRedacted()` gate. If F4 ships first, the executor must layer on top of F4's
  implementation, not replace it. If G5 ships first, F4 should preserve the localStorage check.
  Note this explicitly in the Completion Report.
- **`coerceDetailTab` coordination with F1**: F1 changes `coerceDetailTab` fallback from `'trust'`
  to `'overview'`. G5 adds a localStorage read before that fallback. If F1 has not shipped when G5
  executes, the executor must apply the F1 change (fallback `'overview'`) AND the G5 localStorage
  read in one pass. If F1 has already shipped, stack on top. Document which case applies in the
  Completion Report.
- **localStorage availability**: `localStorage` is not available in SSR or some test environments.
  The `useViewerSettings` hook must guard with `typeof window !== 'undefined'` and return defaults
  gracefully.
- **Theme implementation breadth**: If the project has no existing CSS custom-property theme
  system, the executor should add a minimal `data-theme` attribute approach and wire only the
  toggle/selector; do not attempt a full design-token overhaul. Keep it shippable.
- **Base data path change requires reload**: the `client.ts` fetch helpers likely capture the path
  at module init. The executor must verify whether a hot change is feasible or whether a reload
  notice is genuinely required, and implement accordingly.

---

## 12. Implementation Notes

**Suggested approach:**

1. Create `frontend/runs-viewer/src/lib/viewerSettings.ts` — define storage keys as constants,
   write `getViewerSettings()` (reads all keys, applies defaults), `setViewerSetting(key, value)`
   (writes one key), and a `useViewerSettings()` React hook that returns current settings and a
   setter, triggering re-render via `useState` + a `storage` event listener.
2. Wire `AppShell.tsx` NAV_ITEMS: find the Settings entry (currently disabled/`'not implemented'`
   per §1.1 lines ~24-35) and remove the disable guard. Update `isActiveNav()` to cover
   `/settings` (similar to Portfolio `pathname === '/runs'` check at lines ~105-111).
3. Register `/settings` route in `app/routes.tsx` (or wherever other top-level routes live).
4. Create `SettingsScreen.tsx` — use existing screen layout patterns from `RunList.tsx` or
   `RunDetail.tsx`. Render four preference sections using `useViewerSettings`.
5. Wire `SourceCard.isRedacted()` to read `getViewerSettings().showAll` (or call the hook if
   SourceCard is already a hook-consuming component).
6. Wire `coerceDetailTab()` to call `getViewerSettings().defaultTab` before its hardcoded fallback.
7. Wire `client.ts` data path: read `getViewerSettings().dataPath` in the fetch URL builder.
8. Apply theme attribute in `AppShell.tsx` (or a top-level `App.tsx` effect) using
   `useViewerSettings().theme` + `prefers-color-scheme` media query listener.
9. Add unit tests for the hook and component test for SettingsScreen.
10. Run smoke task G5-SMOKE-01.

**Similar existing code:**
- `frontend/runs-viewer/src/lib/runs.ts` — lib module pattern (pure functions, no context
  provider); follow the same export style for `viewerSettings.ts`.
- `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx:27-35` — the `isRedacted()`
  function being wired (§1.8).
- `frontend/runs-viewer/src/components/RunDetail/detailTabs.ts:8` — `coerceDetailTab` being
  extended.
- `frontend/runs-viewer/src/app/AppShell.tsx:24-35, 105-111` — NAV_ITEMS structure and
  `isActiveNav()` to mirror.

**Known gotchas:**
- `localStorage` key collisions: prefix all keys with `rv_` (already specified in §6) to avoid
  clobbering other apps on the same origin.
- If `@xyflow/react` or another heavy dep is tree-shaken per-route, ensure SettingsScreen does not
  inadvertently import from lineage/ledger modules (keep the settings module dependency-light).
- The `coerceDetailTab` change must not break the modal default-tab behaviour (modal starts at
  `'overview'` per `RunDetailModal.tsx:23` — that path is separate from `coerceDetailTab` and
  should remain unchanged).

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: list of all modified/new files with brief reason (at minimum:
  `AppShell.tsx`, `routes.tsx`, `SettingsScreen.tsx` (new), `lib/viewerSettings.ts` (new),
  `SourceCard.tsx`, `detailTabs.ts`, `client.ts`, plus test files)
- **Tests run**: what unit/component tests were added and their pass/fail result
- **Validation results**: table of typecheck / lint / build / tests with pass/fail
- **F1 and F4 coordination note**: which of the two coordination cases applied (F1/F4 shipped
  first vs G5 ships first) and how the executor handled it
- **Deviations from contract**: any material changes and justification
- **Risks / limitations**: any remaining risks (e.g. theme system is minimal, reload required
  for data path)
- **Follow-up recommendations**: e.g. settings reset button, full theme token system, settings
  export/import

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full template.

---

## Metadata & References

**Tier**: 1 (3 points estimated)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion

**Reviewer**: `task-completion-validator` (mandatory, reviews Completion Report against ACs)

**Dependency note**: No data dependency — can start immediately, in parallel with F1–F4.
Coordination with F1 (`coerceDetailTab` fallback) and F4 (SourceCard redaction gate) required;
see §11.

**Related Documents:**
- Epic index: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Tabs sub-epic: `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md`
- F4 (redaction): `docs/project_plans/feature_contracts/harden-polish/viewer-unredact-lan.md`
- F1 (default tab): `docs/project_plans/feature_contracts/harden-polish/nav-titles-lineage-fixes.md`
- AppShell source: `frontend/runs-viewer/src/app/AppShell.tsx` (NAV_ITEMS ~24-35, isActiveNav ~105-111)
- Redaction gate: `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx:27-35`
- Tab coercion: `frontend/runs-viewer/src/components/RunDetail/detailTabs.ts:8`
- Client fetch: `frontend/runs-viewer/src/api/client.ts`

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass
validation. Scope is intentionally narrow — client-side localStorage only, no backend touches.

- **Scope ambiguity**: if the existing route config or AppShell pattern differs from what §12
  describes, follow the existing pattern and note the deviation in the Completion Report.
- **F1/F4 coordination**: explicitly state which coordination case applied in the Completion
  Report (see §11 and §13).
- **Theme system**: if the project has an existing theme mechanism, use it. If not, implement the
  minimal `data-theme` attribute approach — do not overengineer.
- **Impossible constraints**: if `coerceDetailTab` is already wired by F1 with a different
  mechanism, adapt and document.
- Stay within scope. Do not add analytics, user accounts, or any server-side storage.
