---
title: Runs-Viewer v2.3 Fixes — Staged Implementation Plan
created: 2026-06-22
status: draft
owner: nick
---

# Runs-Viewer v2.3 Fixes — Staged Implementation Plan

Single conflict-free plan for the six v2.3 deliverables. Three SEQUENTIAL stages, each owning a
disjoint set of files. Read-only SPA, static export — NO backend/export/python changes.

## Scope recap (authoritative decisions)

- **D1** Whole run-item opens the run modal (table rows + status lane cards), keyboard-accessible, Open stays secondary.
- **D2** Remove run-scoped sidebar nav (Runs, Reports, Ledger, Swarm); keep Portfolio + global tabs.
- **D3** Lineage graph edge connectors — **already fixed in code** (`edgeTypes={{ smoothstep: SmoothStepEdge }}` present at `LineageFlow.tsx:174-175,225`). Only a regression render test is owed.
- **D4** Single-click any lineage node → DetailModal with node details + a primary "jump to view" action.
- **D5** Report tab: sticky run title + tab bar with a visible divider (general chrome) + a navigable heading outline in the report right sidebar (report-specific).
- **D6** Swarm becomes a run-scoped DETAIL TAB on both page and modal; retire/redirect the standalone `/runs/:runId/swarm` route.

## Verified facts (checked this pass)

- Router lives in `src/app/App.tsx` (`{ path: "runs/:runId/swarm", element: <SwarmScreen /> }` at line 31). There is no separate `AppRouter.tsx`. `routes.tsx` holds the name table (`swarm` entry line 24, `RouteName` union line 10).
- D3 edgeTypes registration is already present at module scope — do not "re-fix"; just add the guard test.
- `runs-viewer.css` is a single 4895-line monolith. It is the ONE append target for all CSS.

## CSS strategy

- **Single global stylesheet:** `src/styles/runs-viewer.css` (4895 lines). Imported once via `src/styles/index.css` → `main.tsx`. No Tailwind, no CSS modules, no co-located CSS. `swarm.css` is already globally imported, so the embedded Swarm pane needs no extra import.
- **Each stage MUST re-read `runs-viewer.css` (with an offset) immediately before editing** — line numbers in this plan are advisory and will drift. Because stages are sequential, only one stage touches the file at a time; never assume the numbers above.
- **Append convention:** add a clearly comment-marked section per stage at the end of the file, e.g. `/* ===== v2.3 D1 clickable table row ===== */`. Edit existing rules in place only when changing established selectors (e.g. lifting the modal tab bar out of the scroll container). Dark-theme overrides use the existing `[data-theme='dark'] .rv-*` block pattern.
- Reuse existing sticky/modal patterns rather than inventing tokens: `.rv-audit-report__header` (sticky top:0 z:10 border-bottom) is the model for D5 sticky chrome; `.rv-modal-overlay--stacked` is the model for D4 modal z-index; `.rv-report-overlay__sidebar` (sticky top:space-6) is the hook for the D5 outline.

---

## Stage 1 — core-nav-tabs (D1, D2, D6, D5 sticky chrome)

**Owns:** `src/app/AppShell.tsx`, `src/app/App.tsx`, `src/app/routes.tsx`, `src/screens/RunList.tsx`,
`src/components/RunList/*`, `src/screens/RunDetail.tsx`, `src/components/RunDetail/RunDetailWorkspace.tsx`,
`src/components/RunDetail/RunDetailModal.tsx`, `src/components/RunDetail/detailTabs.ts`,
`src/screens/SwarmScreen.tsx`, a new Swarm tab pane (`src/components/RunDetail/SwarmPane.tsx`), the
swarm/detailTabs tests, and the sidebar + clickable-row + sticky-workspace-chrome sections of `runs-viewer.css`.

**MUST NOT touch:** `components/LineageGraph/*`, `components/ReportOverlay/*`, `components/RunDetail/DetailModal.tsx`.

### D1 — run-item click

- `RunList.tsx` RunTable `<tr>`: add `onClick={() => onOpen(run.run_id)}`, `tabIndex={0}`, `onKeyDown` (Enter/Space → onOpen), `aria-label`, class `rv-run-table-row--clickable`. Add `e.stopPropagation()` to the title-cell button and the Action-column **Open** button so they don't double-fire; Open stays as secondary affordance.
- a11y decision: keep `<tr>` with `onClick`+`onKeyDown`+`tabIndex={0}` (not a `<button>` wrapper — `<tr>` cannot contain a button spanning cells). Add a `role`-appropriate label. StatusLane cards (already `<button>` → onOpen) and RunCard grid (already `role=button`+keyboard → setModalRunId) need NO change.
- CSS: `.rv-run-table-row--clickable { cursor:pointer; }` + a `:focus-visible` ring matching the existing selected-row highlight.

### D2 — sidebar cleanup

- `AppShell.tsx`: remove `Runs`, `Reports`, `Ledger`, `Swarm` from `NAV_ITEMS`; keep Portfolio, Library, Policies, Alerts, Settings, Help. Drop the now-dead `isActiveNav()` branches (incl. the `endsWith('/swarm')` branch line 116). Simplify `ShellNavContext` only if `routeRunId`/`runId` become unused by remaining items (Portfolio resolves to `/runs`; globals need no runId) — verify before pruning.
- Tests: rewrite `src/test/g1-swarm.test.tsx` nav blocks (SMOKE-G1-01, TEST-G1-04 + any "Swarm nav" regression tests) — assert Runs/Reports/Ledger/Swarm are ABSENT from `.rv-shell-nav__item`; retain assertions for the 6 kept items.

### D6 — swarm as detail tab

- `detailTabs.ts`: add `'swarm'` to `DetailTab` union; `coerceDetailTab` passes `'swarm'` through; `tabToQuery('swarm')='swarm'`. Update `detailTabs.test.ts` accordingly.
- `SwarmScreen.tsx`: export `RoutingDecisionCard`, `SwarmPlanSection`, `AgentsList`, `extractAgents` (or extract to a shared module) so the pane can reuse them.
- New `SwarmPane.tsx`: reads `run.context?.swarm_plan` + `run.context?.routing_decision`, renders the shared sub-components WITHOUT a top-level header (title is in the page/modal header). Graceful empty state when `context` is null (reuse `data-testid='swarm-context-empty'`).
- `RunDetailWorkspace.tsx`: add `{ id:'swarm', label:'Swarm' }` to the tabs array (after `lineage`, before `writeback`) and a `activeTab==='swarm'` tabpanel rendering `<SwarmPane run={run} />`. This auto-propagates to the modal (no RunDetailModal change for the tab itself).
- `App.tsx`: replace the `runs/:runId/swarm` element with a thin `<SwarmRedirect/>` component (`useParams` → `<Navigate to={\`/runs/${encodeURIComponent(runId)}?view=swarm\`} replace/>`). Keep the route path so deep links resolve. `SwarmScreen.tsx` stays (its sub-components are now imported) but is no longer route-mounted.
- `routes.tsx`: keep the `swarm` name entry (still used as a type-safe label/path reference); no removal required.

### D5 (sticky chrome only — outline is Stage 3)

- Goal: pin run title + the detail tab bar at the top with a VISIBLE divider; tab-panel body scrolls independently. This is general chrome benefiting all tabs.
- `RunDetailWorkspace.tsx`: add a `hideTabBar?: boolean` prop OR export a standalone `RunDetailTabBar` sub-component so callers can place the tab bar in their own sticky layer while the panel body owns its scroll. Tabpanel container gets `overflow:auto; min-height:0` when embedded in a fixed-height host.
- `RunDetailModal.tsx`: lift `.rv-detail__tabs` OUT of the scrolling `.rv-detail-workspace` to be a `flex-shrink:0` sibling between the summary and the workspace body; add a divider (border-bottom). Modal header is already pinned (`.rv-run-modal__header` flex-shrink:0).
- `RunDetail.tsx` (page): wrap nav + header + tab bar in `.rv-detail__sticky` (`position:sticky; top:0; z-index:20; background; border-bottom`), and give the page a constrained-height scroll body `.rv-detail__body` (`overflow-y:auto; flex:1; min-height:0`) with `.rv-detail` as a full-height flex column. **Verify AppShell gives the route container a full-height flex child** before relying on sticky; if not, set `.rv-detail { height:100%; }` and confirm the shell main is `display:flex; min-height:0`.
- CSS: append `.rv-detail__sticky`, `.rv-detail__body`, `.rv-run-modal__tab-bar` (flex-shrink:0, border-bottom). Expose the sticky-header height as a CSS var (`--rv-sticky-header-height`) so Stage 3's outline/sidebar sticky offset can align.

### Stage-1 contract for Stage 3 (DOM/CSS handshake)

- Stage 1 establishes the scroll boundary for the Report tab: in modal mode the scroll container is `.rv-detail-workspace` (tabpanel body); in page mode it is `.rv-detail__body`. Stage 3's IntersectionObserver root + outline sticky offset MUST anchor to these. Stage 1 sets `--rv-sticky-header-height`; Stage 3 consumes it for `.rv-report-overlay__sidebar` top offset.

**Stage 1 verification:** `tsc -b` clean; `eslint src --max-warnings=0`; `vitest run` green (with updated g1-swarm + detailTabs tests). Add a row-click test (fireEvent.click on the `<tr>` opens the modal — assert run modal testid appears) and a Swarm-tab render test (switch to `?view=swarm` / Swarm tab → SwarmPane content or empty state renders) in `RunList`/workspace test files.

---

## Stage 2 — lineage (D3 test + D4)

**Owns:** `src/components/LineageGraph/*`, `src/components/RunDetail/DetailModal.tsx` (extend),
new `src/test/lineage-flow-edges.test.tsx`, and the lineage-edge/node-modal CSS sections of `runs-viewer.css`.

**MUST NOT touch:** any Stage-1 files. Note Stage 1 already added `'swarm'` to `DetailTab`; Stage 2 imports `DetailTab`/`tabToQuery` from `detailTabs.ts` read-only.

### D3 — regression test only (code already fixed)

- No `LineageFlow.tsx` change for the edgeTypes fix — it is present. Create `lineage-flow-edges.test.tsx`: render `<LineageFlow>` with a minimal 2-node tree (one edge); assert an SVG `<path class="rv-lineage-edge">` and an arrowhead `<marker>` are present in the canvas. (jsdom + ResizeObserver stub already in `setup.ts`.)
- If edges visibly fail in-browser despite registration, root cause is elsewhere (missing `@xyflow/react` stylesheet, zero-height canvas, container z-index) — out of scope for this deliverable beyond the guard test; flag in completion report.

### D4 — single-click node → DetailModal with navigate action

- `LineageList.tsx`: add `onExpandNode?` to the shared `LineageViewProps` interface. Change row single-click to call BOTH `onSelectNode` and `onExpandNode` (primary body click only, not the toggle); remove the double-click-to-expand handler so single-click opens the modal in list view too.
- `lineageFlowElements.ts`: add `onExpandNode?` param to `buildFlowElements`; store it in `node.data` alongside `onToggle`/`onSelectNode`.
- `LineageFlow.tsx`: add the typed `onExpandNode?` field to `LineageFlowNodeData`; in `handleBodyClick` call `data.onExpandNode?.(data.node)` after `onSelectNode(id)`; add Enter/Space keyboard trigger. Pass `onExpandNode` through `LineageFlowInner` → `buildFlowElements`.
- `LineageGraph.tsx`: forward `onExpandNode={onExpandNode}` to `<LineageFlow>` (currently only forwarded to list + detail panel). **Memoize** `onExpandNode` via `useCallback` upstream so storing it in `node.data` does not re-render all nodes each parent render.
- `DetailModal.tsx`: add `onNavigate?: (tab: DetailTab, claimId?: string) => void`. In `NodeModalBody` render a primary action per kind: claim → `onNavigate('ledger', node.claimId)` (label "Jump to Ledger"); report → `onNavigate('report')`; writeback → `onNavigate('writeback')`; source/extraction → `onNavigate('lineage')` (no dedicated source page exists — fallback to lineage); run → `onNavigate('overview')` or omit. Omit the button gracefully when `onNavigate` is absent or the kind has no target. Import `DetailTab` from `detailTabs.ts`.
- `RunDetailModal.tsx` is a Stage-1-owned file. **Resolution:** the `onNavigate` wiring in RunDetailModal/RunDetail (close detail modal → `setActiveTab(tab)` → `setSelectedClaimId(claimId)`) is implemented in **Stage 1** as part of the workspace refactor, exposed as a `handleDetailModalNavigate` callback passed down to `RunDetailWorkspace` → `ArtifactLineageGraph`. Stage 2 only consumes the prop name `onNavigate` on `DetailModal`. See shared_file_map.

### D4 CSS

- New `.rv-detail-modal__footer` / `.rv-detail-modal__navigate-action` (flex row, `padding-top`, `border-top: 1px solid var(--it-border-soft)`); the button reuses existing `.it-btn.secondary.sm`. Confirm `.rv-modal-overlay--stacked` z-index is above the base `z:900` overlay before finalizing.

**Stage 2 verification:** `tsc -b`; `eslint src --max-warnings=0`; `vitest run` green. New edge test passes. Add a node-click-opens-modal test (graph and/or list: fireEvent.click a node → `data-testid` for the node modal appears) and a navigate-action test (click "Jump to Ledger" → `onNavigate` spy called with `('ledger', claimId)`).

---

## Stage 3 — report (D5 outline + body scroll)

**Owns:** `src/components/ReportOverlay/*`, new `src/components/ReportOverlay/ReportOutline.tsx`,
and the report-outline CSS section of `runs-viewer.css`.

**MUST NOT touch:** Stage-1 or Stage-2 files. Anchors to Stage 1's sticky-chrome DOM/CSS contract
(`.rv-detail__body` / `.rv-detail-workspace` scroll container, `--rv-sticky-header-height`).

### D5-B — heading outline

- `ReportRenderer.tsx`: either add custom heading renderers that emit `<hN id={slug}>` (slugify: lowercase, non-alphanum→hyphen, dedupe with `-2/-3` counters), OR export a pure `extractHeadings(markdown): {level,text,slug}[]` run after `stripReportMetadata`. **Prefer the heading-renderer-with-ids approach** (ids are required for `scrollIntoView`); pair it with `extractHeadings` for the outline list so slugs match exactly. Decide outline depth: include h2/h3 (h1 is the report title, already shown in sticky chrome) — confirm in completion report.
- New `ReportOutline.tsx`: props `headings`, `activeSlug`, `onHeadingClick`. Renders a `<nav>` list indented by level (via inline `--level` CSS var); click → `getElementById(slug)?.scrollIntoView({behavior:'smooth',block:'start'})`; active item gets `rv-report-outline__item--active`. Empty `headings` → render a muted "No headings" note or nothing.
- `ReportOverlay.tsx`: extract headings from `reportDraft`; track `activeSlug` via `IntersectionObserver` over heading elements within the report main column. **Guard `typeof IntersectionObserver !== 'undefined'`** (jsdom lacks it) or mock in `setup.ts`. The observer `root` MUST be the active scroll container — accept a `scrollContainer` ref/prop or detect: in modal mode `.rv-detail-workspace`, in page mode `.rv-detail__body` (Stage-1 contract). `rootMargin: '-10% 0px -80% 0px'`.
- Sidebar layout: stack `ReportOutline` ABOVE `CompositionSidebar` inside the existing `.rv-report-overlay__sidebar` (already `position:sticky top:space-6`). Add `max-height` + `overflow-y:auto` to the sidebar so a long outline doesn't push CompositionSidebar off-screen. Set the sidebar sticky `top` to `var(--rv-sticky-header-height)` (from Stage 1) so it clears the pinned chrome.

### D5-B CSS

- Append `.rv-report-outline`, `.rv-report-outline__title`, `.rv-report-outline__item` (level indent via `padding-left: calc((var(--level,1) - 1) * 12px)`), `.rv-report-outline__item--active` (accent color + weight). Update `.rv-report-overlay__sidebar` top offset to `var(--rv-sticky-header-height)`.

**Stage 3 verification:** `tsc -b`; `eslint src --max-warnings=0`; `vitest run` green. Add a `ReportOutline` unit test (renders heading list from a fixture; click fires `onHeadingClick(slug)`; active class applied for `activeSlug`). Verify existing ReportOverlay/CompositionSidebar tests still pass.

---

## Shared / cross-stage files (resolution)

| File | Touched by | Resolution |
|------|-----------|------------|
| `src/styles/runs-viewer.css` | all 3 stages | Sequential only. Each stage RE-READS with offset before editing; appends a comment-marked `/* ===== v2.3 <Dn> ... ===== */` section. Stage 1 also defines `--rv-sticky-header-height` consumed by Stage 3. |
| `src/components/RunDetail/RunDetailModal.tsx` | Stage 1 (owns) | Stage 1 implements `handleDetailModalNavigate` (close DetailModal → switch tab/claim) and passes it down so Stage 2's `DetailModal.onNavigate` has a producer. Stage 2 does NOT edit this file. |
| `src/components/RunDetail/RunDetailWorkspace.tsx` | Stage 1 (owns) | Stage 1 forwards `onNavigate`/`onExpandNode` props to `ArtifactLineageGraph`. Stage 2 consumes the contract; does not edit. |
| `src/components/RunDetail/detailTabs.ts` | Stage 1 (owns) | Stage 1 adds `'swarm'`. Stage 2 imports `DetailTab`/`tabToQuery` read-only for `DetailModal.onNavigate` typing. |
| `src/components/RunDetail/DetailModal.tsx` | Stage 2 (owns) | Generic node-expand modal. Stage 1 must NOT touch it even though RunDetailModal renders it — Stage 1 only passes the `onNavigate` value through, it does not change DetailModal's signature. **Sequencing note:** Stage 1 references a prop (`onNavigate`) that Stage 2 adds. Stage 1 should pass it conditionally/optionally so `tsc` stays clean before Stage 2 lands (DetailModal already accepts extra props loosely, or Stage 1 adds the optional prop to the JSX which is type-safe once Stage 2 widens DetailModalProps — order Stage 1 before Stage 2 and have Stage 1 wire the callback only; Stage 2 adds the receiving prop). |
| `src/screens/SwarmScreen.tsx` | Stage 1 (owns) | Stage 1 exports sub-components + redirects route. Stage 2/3 do not touch. |

### Sequencing caveat (DetailModal onNavigate)

To keep each stage independently `tsc`-clean: Stage 1 wires `handleDetailModalNavigate` and passes `onNavigate={handleDetailModalNavigate}` to `<DetailModal>`. `DetailModalProps` does not yet declare `onNavigate` until Stage 2. **Mitigation:** Stage 1 adds the optional `onNavigate?` field to `DetailModalProps` as a typed-but-unused prop (a one-line interface addition is allowed since RunDetailModal is Stage-1-owned and imports the type), and Stage 2 implements the consuming logic in `NodeModalBody`. This keeps the interface change with the file's importer while the behavior lands in the owner. If preferred, run all three stages then a single `tsc -b` at the end — but per-stage gating is safer.

## Global verification (run from `frontend/runs-viewer`, all via `node_modules/.bin/*`)

1. `node_modules/.bin/tsc -b` → no errors.
2. `node_modules/.bin/eslint src --max-warnings=0` → clean.
3. `node_modules/.bin/vitest run` → all green (existing + new tests).
4. Optional manual: `node_modules/.bin/vite build` succeeds (static export integrity).

### Per-deliverable assertions

- **D1:** vitest — clicking a RunTable `<tr>` opens the run modal; Open button still works and does not double-open; row is focusable + Enter/Space activates.
- **D2:** vitest — Runs/Reports/Ledger/Swarm absent from `.rv-shell-nav__item`; Portfolio + 5 globals present; `isActiveNav` has no dead Swarm branch.
- **D3:** vitest — `lineage-flow-edges.test.tsx` finds `<path.rv-lineage-edge>` + arrow `<marker>`.
- **D4:** vitest — single-click a lineage node opens DetailModal (role=dialog, Escape/backdrop close); navigate action fires `onNavigate(tab, claimId?)`; modal opens from both page and modal lineage surfaces.
- **D5:** vitest + visual — tab bar + title stay pinned with visible divider while body scrolls (assert sticky classes present); `ReportOutline` lists headings, click scrolls (spy), active item highlights on scroll.
- **D6:** vitest — Swarm tab present in workspace tabs on page AND modal; renders SwarmPane content or empty state from `run.context.swarm_plan`; `/runs/:id/swarm` redirects to `?view=swarm`.
