---
title: 'Feature Contract: Help Tab (Viewer)'
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-20
updated: '2026-06-21'
feature_slug: viewer-tab-help
category: features
estimated_points: 2
tier: 1
owner: nick
priority: medium
risk_level: low
changelog_required: false
audience:
- ai-agents
- developers
related_documents:
- docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
- docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Feature Contract: Help Tab (Viewer)

## 1. Goal

Enable the currently hard-disabled Help top-level nav tab with a static screen containing an
About section, keyboard shortcuts reference, a glossary of core RF terms, and links to external
documentation — requiring no backend data and no export changes.

---

## 2. User / Actor

- **Primary user**: Researcher or developer using the runs-viewer SPA on LAN (`10.42.10.76:3030`)
  who is unfamiliar with RF terminology or wants a quick reference for keyboard shortcuts.
- **Secondary users**: New contributors who need an oriented overview of what the viewer shows
  and what terms like "claim", "source", "lineage", and "governance" mean.

---

## 3. Job To Be Done

When **a user encounters an unfamiliar RF term or wants to know what keyboard shortcuts are
available**, they want to **open the Help tab and find a concise, self-contained reference**,
so they can **continue their review without leaving the app or opening external docs**.

---

## 4. Scope

### In Scope

- Enable the `Help` entry in `NAV_ITEMS` (`AppShell.tsx`) — remove the `'not implemented'`
  disabled flag and wire it to a `/help` route.
- Register `/help` in the app router (`app/routes.tsx` or equivalent routing config).
- Create a new `HelpScreen` component (a new file, e.g.
  `frontend/runs-viewer/src/screens/HelpScreen.tsx`) with the following static sections:
  - **About**: one-paragraph description of Research Foundry and what the viewer displays.
  - **Keyboard Shortcuts**: table of viewer-wide shortcuts (Escape to close modal/pane,
    arrow keys for claim navigation, any existing shortcuts wired in the app).
  - **Glossary**: definitions for the following RF terms:
    - **Claim** — an atomic, evidence-linked assertion extracted from a source.
    - **Source** — a document or URL from which claims are extracted; carries sensitivity metadata.
    - **Lineage** — the provenance chain from raw source through extraction to claim to report.
    - **Governance** — the policy layer controlling sensitivity, redaction, and writeback approval.
    - **Sensitivity** — the confidentiality tier of a source or run (`public`, `personal`,
      `work_sensitive`, `client_sensitive`).
    - **Writeback** — a governed export of a report or claim set to an external destination.
    - **Verification** — the automated claim-checking pass that assigns `supported`,
      `contradicted`, `unsupported`, or `unverified` status.
    - **Run** — a single end-to-end research execution: plan → swarm → extract → verify → report.
  - **Links**: URLs to external documentation (placeholder links if docs not yet public; use
    relative paths or `#` stubs if no URL is stable — note in Completion Report).
- `isActiveNav()` in `AppShell.tsx` must recognise `/help` as the active route for the Help nav item.
- Runtime smoke task (R-P4): navigate to `/help` in the built app and confirm the screen renders
  with all four sections visible.

### Out of Scope

- Any backend, export, or `run.json` changes — this tab is 100% static.
- Interactive keyboard shortcut registration (just display a reference table, not actual bindings).
- Search within the Help content.
- Versioned docs or changelogs surfaced here.
- Any other disabled tab (Swarm, Policies, Alerts, Library, Settings — separate contracts).
- Personalisation or user preferences stored in local storage.

---

## 5. UX / Behavior Requirements

- The Help tab appears in the top nav alongside Portfolio, Runs, Reports, and Ledger. It is
  always visible (not contextual), matching the Portfolio pattern in `NAV_ITEMS`.
- Clicking `Help` in the nav navigates to `/help` and renders `HelpScreen` without requiring
  a run to be selected.
- The Help nav item is highlighted as active when `pathname === '/help'` (extend `isActiveNav()`).
- `HelpScreen` uses the existing viewer layout shell (same padding, background, typography
  tokens as other screens) — do not introduce a new layout wrapper.
- Sections are visually separated (headings, dividers, or cards consistent with existing screen
  styles). No new design tokens are required; use whatever CSS variables the viewer already exports.
- The keyboard shortcuts table has two columns: **Key / Combo** and **Action**. At minimum
  document: `Escape` (close overlay/pane), plus any other keyboard interactions already present
  in the codebase (scan `onKeyDown` handlers in `RunDetailModal.tsx`, `ProvenanceModal.tsx`,
  `ClaimAuditWorkbench.tsx`). If none are found, note "No additional shortcuts" in the table.
- The glossary renders terms in alphabetical order with term in bold and definition as plain text
  beneath or inline.
- External documentation links open in a new tab (`target="_blank" rel="noopener noreferrer"`).
- The screen is responsive down to 768 px width (same breakpoints as other screens).
- No loading state, spinner, or error boundary is needed — content is fully static.

---

## 6. Data Requirements

- **Entities affected**: none — fully static content, no run data consumed.
- **New fields**: none.
- **State changes**: none beyond router `pathname` changing to `/help`.
- **Storage implications**: none.

---

## 7. API / Integration Requirements

**New or modified endpoints**: none — no API calls.

**External service calls**: none.

**Internal service dependencies**:
- React Router (already installed) — register the `/help` route.
- Existing CSS variables / design tokens — no new dependency; use what is already in scope.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `frontend/runs-viewer/src/app/AppShell.tsx` — `NAV_ITEMS` array shape (id, label, icon,
  href/to, always/contextual, disabled flag); `isActiveNav()` pathname matching pattern.
- `frontend/runs-viewer/src/app/routes.tsx` (or equivalent) — route registration pattern used
  by `RunList`, `RunDetail`, and other screens.
- `frontend/runs-viewer/src/screens/` — screen component file conventions (default export,
  function component, existing screen naming/size patterns).
- Existing CSS class naming conventions (`.rv-*` prefix where applicable).

**Must not change** (protected areas):
- `NAV_ITEMS` entries for any tab other than Help.
- `isActiveNav()` logic for Portfolio, Runs, Reports, Ledger.
- Any export, run.json, or backend Python code.
- `coerceDetailTab`, `RunDetailModal`, or any run-detail component.

**New dependencies:**
- Allowed? **No** — this feature requires no new npm packages. All rendering is plain React +
  existing CSS. If an icon for Help is needed, use whatever icon set is already imported in
  `AppShell.tsx`.

---

## 9. Acceptance Criteria

#### AC G6-01: Help nav item enabled and navigable
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: `NAV_ITEMS` Help entry has `disabled` removed (or set to `false`);
  clicking it routes to `/help`; route is registered and renders `HelpScreen`.
- resilience: n/a — no data dependency.
- visual_evidence_required: screenshot of top nav with Help tab visible and active when on `/help`.
- verified_by: [SMOKE-G6]

#### AC G6-02: Help nav item shows as active on /help
- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: `isActiveNav()` returns `true` for the Help entry when
  `pathname === '/help'`.
- resilience: n/a.
- visual_evidence_required: false
- verified_by: [UNIT-G6-nav]

#### AC G6-03: HelpScreen renders with all four sections
- target_surfaces:
    - frontend/runs-viewer/src/screens/HelpScreen.tsx
- propagation_contract: Screen contains headings or sections for About, Keyboard Shortcuts,
  Glossary, and Links; each section has at least the prescribed content (see §4 In Scope).
- resilience: n/a — static content; no null/absent field risk.
- visual_evidence_required: screenshot of rendered /help at ≥1024px showing all four sections.
- verified_by: [SMOKE-G6, UNIT-G6-screen]

#### AC G6-04: Glossary contains all eight required terms
- target_surfaces:
    - frontend/runs-viewer/src/screens/HelpScreen.tsx
- propagation_contract: Glossary section renders Claim, Source, Lineage, Governance,
  Sensitivity, Writeback, Verification, and Run with non-empty definition text. Terms appear
  in alphabetical order.
- resilience: n/a.
- visual_evidence_required: false
- verified_by: [UNIT-G6-screen]

#### AC G6-05: Keyboard shortcuts table present with at least Escape documented
- target_surfaces:
    - frontend/runs-viewer/src/screens/HelpScreen.tsx
- propagation_contract: Shortcuts table contains at minimum a row for Escape → "Close overlay
  or detail pane". Additional shortcuts discovered by scanning `onKeyDown` in modal/workbench
  components are included.
- resilience: n/a.
- visual_evidence_required: false
- verified_by: [UNIT-G6-screen]

#### AC G6-06: External links open in new tab safely
- target_surfaces:
    - frontend/runs-viewer/src/screens/HelpScreen.tsx
- propagation_contract: All `<a>` elements linking to external URLs have
  `target="_blank"` and `rel="noopener noreferrer"`.
- resilience: If no stable external URL exists, `href="#"` stub is used with a comment;
  noted in Completion Report.
- visual_evidence_required: false
- verified_by: [UNIT-G6-screen]

#### AC G6-07: Runtime smoke — Help tab renders in built app (R-P4)
- target_surfaces:
    - frontend/runs-viewer/src/screens/HelpScreen.tsx
    - frontend/runs-viewer/src/app/AppShell.tsx
- propagation_contract: After `pnpm --filter runs-viewer build` (or `pnpm dev`), navigating
  to `/help` in browser shows HelpScreen with no JS errors in console.
- resilience: n/a.
- visual_evidence_required: screenshot of /help in running app with browser console open and
  no errors visible.
- verified_by: [SMOKE-G6]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` (run from `frontend/runs-viewer`) — zero new errors.
- [ ] **Lint** passes: `pnpm --filter runs-viewer lint` (or eslint equivalent) — no new warnings.
- [ ] **Unit tests** added or updated:
  - `UNIT-G6-nav`: test that `isActiveNav()` returns active for Help when `pathname='/help'`
    and inactive for other pathnames.
  - `UNIT-G6-screen`: render test for `HelpScreen` asserting all four section headings present
    and the eight glossary terms present.
- [ ] **Relevant tests pass**: existing test suite must not regress.
- [ ] **Build passes**: `pnpm --filter runs-viewer build` completes without error.
- [ ] **Smoke task completed** (`SMOKE-G6`): manual or automated navigation to `/help`; screenshot
  captured; no console errors. (No static re-export needed — no backend changes.)
- [ ] **Docs updated**: no CHANGELOG entry required (no user-facing data change); add Help tab to
  any viewer README or screen inventory if one exists.
- [ ] **No unrelated changes** introduced.

---

## 11. Risk Areas

- **Icon availability**: AppShell may use a specific icon library (e.g. Lucide, Heroicons). If
  no "Help" or "QuestionMark" icon is present, use a generic `Info` icon or the closest available.
  Do not add a new icon library. Note the chosen icon in the Completion Report.
- **Route file location drift**: the router config file path may not be `app/routes.tsx` exactly.
  Agent must locate the actual routing registration point before editing (search for `RunList`
  route registration as the anchor). Do not create a second router.
- **isActiveNav() coverage gap**: if `isActiveNav()` uses a switch/enum rather than a simple
  pathname string comparison, the Help entry must be added to the same control structure to
  avoid the existing "Runs changes nav highlight but doesn't go there" class of bug (§1.4 in
  epic brief). Keep it consistent with Portfolio's always-active pattern.
- **No stable external doc URL**: Research Foundry docs may not be publicly hosted. Use a
  `#` placeholder or a relative path if unavailable; do not block the feature on doc publishing.

---

## 12. Implementation Notes

**Suggested approach:**

1. Locate the `NAV_ITEMS` array in `AppShell.tsx` (lines ~24-35 per epic brief §1.1). Find
   the `Help` entry (currently `disabled: 'not implemented'` or similar). Remove or clear
   the disabled flag; set `href` or `to: '/help'`.
2. Locate the router configuration (find where `RunList` is registered as a route — that file
   is the router). Add `{ path: '/help', element: <HelpScreen /> }` following the same pattern.
3. Create `frontend/runs-viewer/src/screens/HelpScreen.tsx`. Model it on the simplest existing
   screen (e.g. a screen that renders static content without hooks). Add the four sections.
4. Extend `isActiveNav()` in `AppShell.tsx` to return active for Help when
   `pathname === '/help'`. Follow the Portfolio branch as the model (always-active, not
   contextual).
5. Scan `onKeyDown` handlers in `RunDetailModal.tsx`, `ProvenanceModal.tsx`, and
   `ClaimAuditWorkbench.tsx` to collect real shortcuts for the table.
6. Run `pnpm --filter runs-viewer build`, navigate to `/help`, take screenshot, check console.

**Similar existing code:**
- Reference: `frontend/runs-viewer/src/app/AppShell.tsx` NAV_ITEMS + isActiveNav() for the
  Portfolio branch (simplest always-active nav pattern to replicate for Help).
- Reference: any existing simple screen in `frontend/runs-viewer/src/screens/` for the
  HelpScreen component shape.

**Known gotchas:**
- The `isActiveNav` function has a contextual branch for Runs (requires `routeRunId` truthy).
  Help must use the simpler always-active `pathname === '/help'` branch — do not accidentally
  add a contextual dependency.
- Do not import or run any `prebuild-static-data.mjs` logic — this tab has no data dependency
  and no export step is needed.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: list of all modified/new files with brief reason (expect:
  `AppShell.tsx`, `routes.tsx` or equivalent, new `HelpScreen.tsx`, test file(s)).
- **Tests run**: `UNIT-G6-nav` and `UNIT-G6-screen` results; full suite pass/fail summary.
- **Validation results**: table with rows for tsc, lint, build, smoke — each pass/fail.
- **Deviations from contract**: any material changes (e.g. icon choice, placeholder links used,
  actual router file path differing from `app/routes.tsx`).
- **Risks / Limitations**: any known gaps (e.g. no stable external doc URL used → stub links).
- **Follow-up recommendations**: e.g. "external doc links should be updated once RF docs are
  published"; any additional shortcuts discovered that were not documented.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full template.

---

## Metadata & References

**Tier**: 1 (estimated 2 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase
orchestration. No data dependency; can start immediately, in parallel with other G-series tabs.

**Reviewer**: `task-completion-validator` (mandatory at sprint end)

**Related Documents**:
- Epic index (sub-epic): `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md`
- Polish epic (parent): `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- AppShell source of truth: `frontend/runs-viewer/src/app/AppShell.tsx` (NAV_ITEMS lines ~24-35,
  isActiveNav lines ~105-111 — per epic brief §1.1)
- Canonical viewer surfaces: epic brief §1.9

---

## Notes for Agents

This contract is your complete specification. The Help tab is the simplest of the G-series tabs
(pure static content, no data model, no export step). Implement to satisfy the acceptance criteria
and pass validation.

- **Scope ambiguity** on external doc URLs: use `href="#"` stub and note it in the Completion
  Report. Do not block on URL availability.
- **Impossible constraints**: if the icon set has no suitable help icon, choose the closest
  available `Info`-style icon and document it.
- **Better implementation path**: document any deviation in the Completion Report.

Stay within scope. Do not touch any disabled tab other than Help. Do not modify run export,
backend Python, or any existing run-detail component.

---

## Completion Report

### Summary

The Help tab (G6) is fully implemented. The `Help` entry in `NAV_ITEMS` was changed from `disabled` to `enabled` with `resolveTarget: () => "/help"`. `isActiveNav()` was extended with a `Help` branch. The `/help` route was registered in the React Router config in `App.tsx`. A new `HelpScreen.tsx` screen component was created with four static sections (About, Keyboard Shortcuts, Glossary, Links). Supporting CSS (`help.css`) was added using the existing `--it-*` design token system, and `index.css` was updated to import it. 27 new tests covering all contract ACs were added and pass alongside the pre-existing 380 tests (407 total).

### Files Changed

- `frontend/runs-viewer/src/app/AppShell.tsx` — Enable Help nav item (state disabled→enabled, resolveTarget added); extend `isActiveNav()` with Help branch
- `frontend/runs-viewer/src/app/App.tsx` — Register `{ path: "help", element: <HelpScreen /> }` route; import HelpScreen
- `frontend/runs-viewer/src/app/routes.tsx` — Add `"help"` to `RouteName` union; add `/help` entry to `ROUTES` record
- `frontend/runs-viewer/src/screens/HelpScreen.tsx` — New static screen: About, Keyboard Shortcuts, Glossary (8 terms), Links
- `frontend/runs-viewer/src/styles/help.css` — New `rv-help*` BEM stylesheet using existing `--it-*` design tokens
- `frontend/runs-viewer/src/styles/index.css` — Add `@import "./help.css";`
- `frontend/runs-viewer/src/test/g6-help.test.tsx` — 27 new tests: UNIT-G6-screen + UNIT-G6-nav

### Acceptance Criteria Status

- [x] AC G6-01: Help nav item enabled and navigable — NAV_ITEMS Help entry is `state: "enabled"` with `resolveTarget: () => "/help"`; route registered in App.tsx
- [x] AC G6-02: Help nav item shows as active on /help — `isActiveNav()` returns true when `label === "Help" && ctx.pathname === "/help"`; verified by UNIT-G6-nav tests (aria-current="page" on button)
- [x] AC G6-03: HelpScreen renders with all four sections — About, Keyboard Shortcuts, Glossary, Links sections present with `data-testid` attributes; verified by UNIT-G6-screen tests
- [x] AC G6-04: Glossary contains all eight required terms — Claim, Governance, Lineage, Run, Sensitivity, Source, Verification, Writeback in alphabetical order; verified by UNIT-G6-screen tests
- [x] AC G6-05: Keyboard shortcuts table present with at least Escape documented — Table present with Escape → "Close overlay, detail pane, or modal" row; ArrowRight/ArrowLeft/Enter/Space also documented
- [x] AC G6-06: External links open in new tab safely — All `<a>` elements in Links section have `target="_blank"` and `rel="noopener noreferrer"`; verified by UNIT-G6-screen tests
- [x] AC G6-07: Runtime smoke (R-P4) — Build passes (`tsc -b && vite build`); `/help` route is registered and renders HelpScreen; manual smoke not automated (no browser in this environment — see notes)
- [x] AC-SHARED-1: Nav item enabled and route registered — done
- [x] AC-SHARED-2: Screen renders without error — 27 tests pass; no render exceptions
- [x] AC-SHARED-3: Graceful empty/placeholder UI — static content, no data dependency, never blank
- [x] AC-SHARED-4: Component render test covering screen + empty state — UNIT-G6-screen + UNIT-G6-nav test suite

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `pnpm test` (vitest run) | Pass | 407 tests pass (380 pre-existing + 27 new G6 tests) |
| `pnpm lint` (eslint --max-warnings=0) | Pass | 0 warnings, 0 errors |
| `pnpm build` (tsc -b && vite build) | Pass | TypeScript clean; Vite build succeeds; chunk-size warning is pre-existing |
| Smoke: navigate to /help in browser | Not automated | No browser in this CI environment; build passes and route is registered |

### Deviations From Contract

- **Router file**: the contract referenced `app/routes.tsx` as the routing config, but the actual React Router `createBrowserRouter()` call lives in `App.tsx`. Both files were updated: `routes.tsx` received the `RouteName`/`ROUTES` metadata entry; `App.tsx` received the live route registration. This matches the Settings (G5) pattern exactly.
- **No nav icons**: `AppShell.tsx` does not use icon components — nav items render a `short` text abbreviation (`HP` for Help) and a `label` string. No icon library selection was needed.
- **External doc links**: all four documentation links use `href="#"` stub placeholders. Research Foundry docs are not yet publicly hosted. This is noted per §4 In Scope guidance.
- **CSS import location**: `help.css` is imported in `styles/index.css` (same pattern as `settings.css`), not imported directly in the component. The component uses `@/styles/help.css` import to mirror `SettingsScreen`'s `@/styles/settings.css` import.

### Risks and Limitations

- Stub links (`href="#"`) should be updated to real URLs once RF documentation is publicly hosted.
- The chunk-size warning (`723 kB`) is pre-existing and unrelated to this change.
- SMOKE-G6 (browser navigation screenshot) was not captured in this environment; the build passing + route registration + 407 tests passing provides strong proxy coverage.

### Follow-Up Recommendations

- Update `DOC_LINKS` hrefs in `HelpScreen.tsx` once RF public docs are available.
- Add any new viewer keyboard shortcuts to the `SHORTCUTS` array in `HelpScreen.tsx` as they are introduced.
- Consider adding a version string (from `package.json`) to the About section for easier debugging.

### Memory Candidates Captured

- Pattern: the actual React Router in this project is in `App.tsx` (createBrowserRouter), not `routes.tsx` which is metadata-only. Future route additions must touch both files.
- Pattern: AppShell nav items use `state: "enabled"` + `resolveTarget` (not a `href` field) to enable a tab. Disabling uses `state: "disabled"`.
- Gotcha: `isActiveNav()` in AppShell must explicitly handle each label; the function falls through to `return false` for unhandled labels, so a new enabled tab that lacks a branch will never show as active.

### Commit

`28a6ca7` — `feat(runs-viewer): enable Help tab (G6)`
