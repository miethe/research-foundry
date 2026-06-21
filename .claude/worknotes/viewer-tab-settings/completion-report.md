# Completion Report — viewer-tab-settings (G5)

**Contract**: `docs/project_plans/feature_contracts/features/viewer-tab-settings.md` (Tier 1, 3 pts, risk: low)
**Mode**: C — Autonomous Feature Sprint (implementation wave delegated to ICA `claude-sonnet-4-6[1m]`; gates + adjudication re-run in-session)
**Verdict**: SPRINT COMPLETE — all AC met

## Files Changed (11, all under `frontend/runs-viewer/src/`)

| File | Type | Purpose |
|------|------|---------|
| `lib/viewerSettings.ts` | NEW | `ViewerSettings` type, `getViewerSettings()` (validated, try/catch-guarded), `setViewerSetting()`, `applyTheme()`, `useViewerSettings()` hook. `import type { DetailTab }` breaks the runtime cycle with detailTabs. |
| `screens/SettingsScreen.tsx` | NEW | `/settings` screen: Display (sensitivity toggle), Appearance (theme), Navigation (default tab), Data (base path + Save + reload notice). BEM `rv-settings*`, a11y labels. |
| `styles/settings.css` | NEW | BEM stylesheet — uses ONLY existing `--it-*` tokens; zero hardcoded colors. |
| `test/g5-settings.test.tsx` | NEW | 48 tests: defaults, round-trips, per-key invalid-value fallbacks, `applyTheme`, SettingsScreen render + interactions, coerceDetailTab wiring. |
| `app/AppShell.tsx` | MOD | Settings nav `disabled`→`enabled` (`resolveTarget`→`/settings`); `isActiveNav` recognizes `/settings`; `useEffect` applies persisted theme on mount. |
| `app/App.tsx` | MOD | Import + route child `{ path: "settings", element: <SettingsScreen /> }`. |
| `app/routes.tsx` | MOD | `settings` added to `RouteName` + `ROUTES`. |
| `components/SourceCard/SourceCard.tsx` | MOD | `isRedacted()` runtime bypass (`getViewerSettings().showAll`) prepended above existing F4 `VITE_SHOW_ALL` check. |
| `components/RunDetail/detailTabs.ts` | MOD | `coerceDetailTab()` returns validated `getViewerSettings().defaultTab` before the `'overview'` baseline. |
| `api/client.ts` | MOD | `getStaticDataBase()` reads `dataPath` (default `/data`), slash-normalized → identical URLs for the default. |
| `styles/index.css` | MOD | `@import "./settings.css"`. |

## Acceptance Criteria

| AC | Status | Evidence |
|----|--------|----------|
| G5-01 Settings nav enabled + routes | ✅ | Smoke: nav item `class="rv-shell-nav__item active"`, `aria-current="page"` on `/settings`; screenshot `settings-screen.png`. |
| G5-02 Screen renders 4 controls | ✅ | Smoke: all 6 testids present (screen + 4 controls + save); component tests. |
| G5-03 Sensitivity toggle → redaction gate | ✅ | `SourceCard.isRedacted()` reads `getViewerSettings().showAll`; unit/component tests. |
| G5-04 Theme applies immediately | ✅ | Smoke: selecting Dark → `html[data-theme="dark"]` (confirmed `themeAttrAfterDark: "dark"`). |
| G5-05 Default tab consumed by coerceDetailTab | ✅ | `coerceDetailTab(null)` returns stored default; test asserts wiring. |
| G5-06 Base data path saved + acknowledged | ✅ | Save writes `rv_data_path`, reload notice shown; `client.ts` consumes it. |
| G5-07 Persist across refresh | ✅ | localStorage-backed; hook seeds from `getViewerSettings()`; tests. |
| G5-08 Runtime smoke, no console errors | ✅ | Playwright smoke: `consoleErrors: []`, `pageErrors: []`; screenshots (light + dark) on disk. |

## Validation Run (authoritative, re-run in-session — not delegate-reported)

| Gate | Command | Result |
|------|---------|--------|
| Typecheck | `npx tsc --noEmit` | ✅ exit 0 |
| Lint | `pnpm lint` (eslint `--max-warnings=0`) | ✅ exit 0 |
| Tests | `pnpm test` (Vitest) | ✅ 371/371 passed (14 files; +48 new G5 tests) |
| Build | `pnpm build` (`tsc -b && vite build`) | ✅ exit 0 |
| Runtime smoke | Playwright headless on `vite preview` `/settings` | ✅ controls present, 0 console errors, theme flips live, nav active |

Visual evidence: `~/.claude/jobs/0ead63f9/tmp/settings-screen.png` (light), `settings-screen-dark.png` (dark).

## Scope Integrity
- Diff = 11 files, all under `frontend/runs-viewer/src/`. No backend/export changes (`export_service.py`, `run-export.ts` untouched). No other screen behaviour changed beyond the §7 wiring. No scope creep.
- F1 (`coerceDetailTab`→`overview`) and F4 (`VITE_SHOW_ALL` gate) confirmed already shipped; G5 layers cleanly on top without altering their logic.

## Known Limitations (accepted, in-scope-bounded)
- **Dark-mode canvas coverage is minimal**: `applyTheme` correctly sets `data-theme="dark"` on `<html>` (the contract's required mechanism). The app's outer canvas/shell background does not fully re-tint for dark mode (pre-existing design-system gap, never previously exercised since no theme toggle existed). Full app-wide dark-token polish is explicitly OUT OF SCOPE per contract §4.2 ("Theming implementation beyond a CSS class toggle"). New screen's own cards/controls render correctly in both themes.
- No `prefers-color-scheme` live listener for `'system'` (resolves at selection/boot) — out of scope.
- No cross-tab `storage` sync, no reset button — out of scope; logged as follow-ups.
