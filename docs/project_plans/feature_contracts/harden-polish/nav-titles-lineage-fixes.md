---
title: "Feature Contract: Nav Titles & Lineage Fixes"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-20
updated: 2026-06-20
feature_slug: "nav-titles-lineage-fixes"
category: "harden-polish"
estimated_points: 7
tier: 1
owner: nick
priority: high
risk_level: low
changelog_required: true
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Feature Contract: Nav Titles & Lineage Fixes

## 1. Goal

Fix the broken/missing basics in the runs-viewer so every run shows a readable title on all list surfaces, run-click reliably opens the detail modal with nav highlight aligned to actual location, the default detail tab is Overview everywhere, and lineage tree edges render correctly with a registered smoothstep edge type.

---

## 2. User / Actor

- **Primary user**: Researcher / operator browsing the LAN-deployed runs-viewer SPA (`10.42.10.76:3030`) to review research run results, lineage, and trust scores.
- **Secondary users**: Any agent or human reading the runs-viewer as a read-only audit surface.

---

## 3. Job To Be Done

When a researcher opens the runs-viewer Portfolio page, they want to immediately see a meaningful title for each run (not a raw `run_id` slug), navigate into a run by clicking its card, land on the Overview tab by default, and see the full lineage graph with edges rendered, so they can quickly understand what a run produced and trace its evidence chain without configuration or workarounds.

---

## 4. Scope

### In Scope

- **(a) Readable run titles on all list surfaces**: Add a `title` field to `export_service.py`'s `export_run()` dict (populated from `report_draft` frontmatter H1 title, fallback `titleFromSlug(run_id)`); thread `title` into `index.json` summary in `prebuild-static-data.mjs`; add `title?: string` to `RFRunSummary` in `run-export.ts`; display title via existing `deriveRunTitle()` / `titleFromSlug()` fallback chain on `RunCard`, `StatusLane` inside `RunList.tsx`, and the Portfolio table.
- **(b) Reliable run-click → modal + aligned nav highlight**: Reproduce the §1.4 bug (card click updates `selectedRunId` / nav highlight without reliably opening the modal); make card click → `setModalRunId(runId)` deterministic on all click paths (RunList card, StatusLane card, any lineage/audit card that currently updates state without opening the modal); confirm the existing "Open full page" link in `RunDetailModal.tsx:94` is preserved.
- **(c) Default detail tab = Overview**: Change `coerceDetailTab` fallback in `detailTabs.ts:8` from `'trust'` to `'overview'`; confirm modal default (already `'overview'` in `RunDetailModal.tsx:23`) is unchanged; add unit test covering `coerceDetailTab(null)` returns `'overview'`.
- **(d) Lineage tree edges render**: In `LineageFlow.tsx`, import `SmoothStepEdge` from `@xyflow/react`; define `const edgeTypes: EdgeTypes = { smoothstep: SmoothStepEdge }` at module scope (alongside existing `nodeTypes`); pass `edgeTypes={edgeTypes}` to `<ReactFlow>` in `LineageFlowInner`; add `className: 'rv-lineage-edge'` to edge definitions in `lineageFlowElements.ts` for CSS targeting; add render-level test confirming `<path>` elements appear in the rendered graph.
- **Re-export + rebuild static data**: After backend export changes, run `rf run export --all` and `pnpm --filter runs-viewer build` (which re-runs `prebuild-static-data.mjs`); deploy via manual UI-only path (git reset --hard + pnpm build + restart `research-foundry-ui.service`).

### Out of Scope

- Item detail modals / double-click expand for lineage nodes or claim rows (F2).
- Audit tab state machine and sticky report header (F3).
- Un-redaction / sensitivity threshold changes (F4).
- Run metadata enrichment (linked projects, categories, tags, backlog linkage) (F5).
- Enabling any of the hard-disabled nav tabs (Library, Swarm, Policies, Alerts, Settings, Help) (G1–G6).
- Data-driven "High Claim Volume" threshold (currently hardcoded 75) — P1, noted below.
- Enabling the "This Week" filter — P1, noted below.
- TS codegen for `run-export.ts` — proposed in F5.

---

## 5. UX / Behavior Requirements

- **Title display**: Every `RunCard` in the Portfolio grid shows a human-readable title string. Where `title` is present on `RFRunSummary` (post-export), `deriveRunTitle()` is called with the full `RFRunExport` on the detail page; on the list / summary views where only `RFRunSummary` is available, the `title` field is used directly, with `titleFromSlug(run_id)` as fallback when `title` is absent or null. The raw `run_id` slug must NOT be the primary display string when a title is derivable.
- **StatusLane heading**: Each status-lane group label on the Portfolio page (`RunList.tsx`) shows the run title (not run_id) on each rendered RunCard within the lane.
- **Run-click → modal**: A single click on a RunCard (in the Portfolio grid, StatusLane, or any lineage/audit surface that currently links by run) deterministically opens `RunDetailModal` for that run. After the click, `selectedRunId` matches the open modal's run and the Runs nav item becomes active (consistent state). No click path should update `selectedRunId` without opening the modal or navigating to the run page.
- **"Open full page" preserved**: The existing `<Link>` / button in `RunDetailModal` that opens the full-page detail view (`/runs/:runId`) is unchanged and continues to work.
- **Default tab = Overview**: Navigating to `/runs/:runId` with no tab query param (or an invalid tab) lands on the Overview tab. Opening a run via the modal also shows Overview first. Both paths were previously inconsistent (page defaulted to Trust; modal defaulted to Overview); after the fix both default to Overview.
- **Lineage edges visible**: The Lineage tab graph view renders edges (connector lines) between nodes. The smoothstep curve connects parent nodes to child nodes from left to right with the existing stroke color, ArrowClosed marker, strokeWidth 2, and opacity 0.85 as configured by `buildFlowElements`. Edges were missing pre-fix because `edgeTypes` was not registered on `<ReactFlow>`.
- **Older runs (pre-export)**: RunCards for runs that have not yet been re-exported show `titleFromSlug(run_id)` gracefully rather than `undefined`, empty string, or a JS error.

---

## 6. Data Requirements

- **New export field `title`** (`string | null`):
  - Producer: `export_service.py` `export_run()`. Derive from `report_draft` frontmatter YAML — parse the `title:` key from the fenced YAML block at the top of `report_draft` (if present); fallback to `titleFromSlug(run_id)` rendered in Python (or keep null and let FE derive from slug). Recommended: export a non-null string always (Python equivalent of `titleFromSlug`), so list view never falls back to raw slug.
  - Threading: add to the run.json dict in `export_run()`; add to the `index.json` per-entry in `prebuild-static-data.mjs` (summary shape `{run_id, status_derived, created_at, sensitivity, claim_counts, title}`).
  - Type: add `title?: string` to `RFRunSummary` in `frontend/runs-viewer/src/types/rf/run-export.ts`. The full `RFRunExport` already has `report_draft` as raw markdown; title extraction on the FE side uses `deriveRunTitle()` for the detail page (unchanged). The new `title` field on `RFRunSummary` is the list-view shortcut.
- **`RFRunSummary` shape** (hand-written in `run-export.ts`): add `title?: string` field. No other type changes in this contract.
- **No schema version bump required** for this fix (title is additive and optional). Older cached `index.json` without `title` still works via the `titleFromSlug` fallback.
- **No new DB tables, no RLS, no migration** — static export only.

---

## 7. API / Integration Requirements

**Static export pipeline** (no HTTP API server involved in this contract):

- `src/research_foundry/services/export_service.py`: `export_run()` function — add `title` key to the returned dict.
- `frontend/runs-viewer/scripts/prebuild-static-data.mjs`: `index.json` builder — include `title` from each run's `run.json` in the summary entry.
- After any backend export change: run `rf run export --all` (regenerates all `public/data/<id>/run.json` + `public/data/index.json`), then `pnpm --filter runs-viewer build` (prebuild step copies + vite bundles). Deploy to `10.42.10.76:3030` per memory entry `runs-viewer-deploy`.

**Optional loopback API** (`api/client.ts`): not modified; this contract uses only the static export path.

**Internal FE dependencies**:
- `lib/runs.ts` → `deriveRunTitle()`, `titleFromSlug()`: these already exist and require no changes; the FE simply uses `title` from `RFRunSummary` on list views (direct field access, no parsing).
- `@xyflow/react` (already installed as peer dep for React Flow v12): import `SmoothStepEdge` and `EdgeTypes` from this package. No new package installation required.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `export_service.py` `export_run()`: explicit field-by-field dict construction (§0.1.2 of epic brief) — do not use spread or `**vars()`; add `title` as an explicit key.
- `prebuild-static-data.mjs`: explicit field enumeration in the summary object written to `index.json` — add `title` explicitly alongside `run_id`, `status_derived`, `created_at`, `sensitivity`, `claim_counts`.
- `LineageFlow.tsx`: `nodeTypes` is already defined at module scope; follow the same pattern for `edgeTypes`.
- `RunDetailModal.tsx` overlay conventions (role=dialog, Escape, backdrop) — no changes to modal chrome in this contract.
- FE hand-written types in `run-export.ts` — keep in sync manually (no codegen in this contract).

**Must not change** (protected areas):
- `detailTabs.ts` `tabToQuery()` and the `'audit'→'ledger'` alias — only the fallback value in `coerceDetailTab` changes.
- `RunDetailModal.tsx` default tab initialization (`'overview'`, line 23) — already correct; leave it.
- `lineageFlowElements.ts` edge definitions — they are already correct (`type:'smoothstep'`, correct styles); only the registration in `LineageFlow.tsx` is missing.
- `ProvenanceModal` and `ClaimInspector` overlays — untouched in this contract.
- Any writeback, governance, or redaction logic.

**New dependencies:**
- No new npm packages. `SmoothStepEdge` is exported from `@xyflow/react` (already installed).
- No new Python packages. `re` (stdlib) is sufficient to parse `report_draft` frontmatter title.

---

## 9. Acceptance Criteria

### AC 1: Run titles appear on all list surfaces

#### AC 1.1: Backend `title` field exported
- Export field `title` (string, non-null when derivable) is present in each run's `public/data/<id>/run.json` after `rf run export --all`.
- `title` is derived from `report_draft` YAML frontmatter `title:` key when present; falls back to a slug-humanized string (equivalent of `titleFromSlug(run_id)`) when `report_draft` is absent or has no `title`.
- `propagation_contract`: `export_service.py:export_run()` → `run.json` dict → written to `public/data/<id>/run.json` by the export step.
- `resilience`: runs with no `report_draft` produce a non-null `title` (slug fallback); no KeyError or missing-field exception in `export_run()`.

#### AC 1.2: `title` present in `index.json` summary
- Each entry in `public/data/index.json` includes `title` alongside existing fields.
- `propagation_contract`: `prebuild-static-data.mjs` reads each run's `run.json` and copies `title` into the summary entry.
- `resilience`: runs whose `run.json` lacks `title` (cached before this export) produce an entry with `title: null` or `title: undefined` — the FE `titleFromSlug` fallback handles the absent field without JS exception.

#### AC 1.3: `RFRunSummary` TypeScript type updated
- `frontend/runs-viewer/src/types/rf/run-export.ts` `RFRunSummary` interface includes `title?: string`.
- No TypeScript errors (`npx tsc --noEmit` passes) after the type addition.

#### AC 1.4: Title rendered on all target list surfaces
- `target_surfaces`:
  - `frontend/runs-viewer/src/screens/RunList.tsx` (portfolio table + status lanes)
  - `frontend/runs-viewer/src/components/RunList/RunCard.tsx`
- Each `RunCard` renders the run's title as primary text instead of raw `run_id`.
- `StatusLane` headings in `RunList.tsx` display per-card titles on each card within a lane.
- `propagation_contract`: `RFRunSummary.title` → `RunCard` prop → rendered heading; falls back to `titleFromSlug(run.run_id)` when `title` absent.
- `resilience`: when `title` is absent/null on `RFRunSummary` (older runs not yet re-exported), `titleFromSlug(run_id)` is called and the result is displayed; no `undefined`, empty string, or crash.
- `visual_evidence_required`: screenshot of the Portfolio page showing at least 3 RunCards with human-readable titles (not raw `rf_run_YYYYMMDD_...` slugs).

---

### AC 2: Run-click deterministically opens modal with aligned nav highlight

#### AC 2.1: Card click opens `RunDetailModal`
- `target_surfaces`:
  - `frontend/runs-viewer/src/screens/RunList.tsx` (portfolio table + status lanes)
  - `frontend/runs-viewer/src/components/RunList/RunCard.tsx`
- Clicking any `RunCard` in the Portfolio grid or StatusLane calls `setModalRunId(runId)` and opens `RunDetailModal` for that run on every click — no click path updates `selectedRunId` without also opening the modal.
- `propagation_contract`: `RunCard.onClick` → `RunList.onClick` handler → `setModalRunId(runId)` (and optionally `setSelectedRunId(runId)` if that drives nav highlight) → `RunDetailModal` visible with correct `runId`.
- `resilience`: clicking the same card twice does not produce a broken state (modal already open → stays open for same run).

#### AC 2.2: Nav highlight matches actual location
- After opening the modal (§AC 2.1), the "Runs" nav item in `AppShell.tsx` is active (`isActiveNav` returns true for 'runs').
- Navigating away (closing the modal) reverts nav highlight correctly.
- `propagation_contract`: `selectedRunId` state (which drives `isActiveNav`) is set in sync with `setModalRunId`; they must not diverge.

#### AC 2.3: "Open full page" link preserved
- `target_surfaces`:
  - `frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx`
- The existing "Open full page" `<Link>` at `RunDetailModal.tsx:~94` navigates to `/runs/:runId` and continues to function correctly after any changes to click handlers.

---

### AC 3: Default detail tab is Overview

#### AC 3.1: `coerceDetailTab(null)` returns `'overview'`
- `detailTabs.ts:coerceDetailTab` fallback (line 8) returns `'overview'` for all null / unrecognized inputs.
- Unit test: `coerceDetailTab(null) === 'overview'`; `coerceDetailTab('') === 'overview'`; `coerceDetailTab('unknown') === 'overview'`; `coerceDetailTab('audit') === 'ledger'` (alias unchanged).
- `target_surfaces`:
  - `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` (Overview tab content)
  - `frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx`

#### AC 3.2: Page-mode default tab is Overview
- Navigating to `/runs/:runId` with no `?tab=` query param renders the Overview tab active and its content visible.
- `propagation_contract`: `RunDetail.tsx` (or equivalent screen) calls `coerceDetailTab(searchParams.get('tab'))` which now returns `'overview'` → Overview tab active.

#### AC 3.3: Modal-mode default tab is Overview
- Opening `RunDetailModal` (via card click, §AC 2.1) renders the Overview tab active by default.
- Confirmed: `RunDetailModal.tsx:23` already initializes to `'overview'`; this AC verifies it is unchanged after the `coerceDetailTab` fix.
- `resilience`: switching tabs in the modal and then closing/reopening resets to Overview (or preserves last tab, whichever is the current designed behavior — document in completion report).

---

### AC 4: Lineage graph edges render

#### AC 4.1: `edgeTypes` registered in `LineageFlow.tsx`
- `SmoothStepEdge` is imported from `@xyflow/react`.
- `const edgeTypes: EdgeTypes = { smoothstep: SmoothStepEdge }` is defined at module scope in `LineageFlow.tsx` (alongside existing `nodeTypes`).
- `edgeTypes={edgeTypes}` is passed to the `<ReactFlow>` component in `LineageFlowInner`.
- `target_surfaces`:
  - `frontend/runs-viewer/src/components/LineageGraph/LineageFlow.tsx`

#### AC 4.2: Edges render in the Lineage graph view
- The Lineage tab graph view renders visible connector lines (SVG `<path>` elements) between parent and child nodes when a run with linked claims/sources is viewed.
- `propagation_contract`: `buildFlowElements` (in `lineageFlowElements.ts`) already produces edge objects with `type: 'smoothstep'`; registering `edgeTypes` in `LineageFlow.tsx` causes React Flow v12 to render them.
- `resilience`: a run with no edges (single root node, no children) renders the graph without error (empty edges array is valid).
- `visual_evidence_required`: screenshot of the Lineage tab for a run with multiple nodes showing smoothstep connector lines between nodes (before: no lines; after: lines visible).

#### AC 4.3: Render-level test confirms edge `<path>` elements
- A test (unit or component-level) renders `LineageFlow` with a mock dataset containing at least one parent→child edge and asserts that at least one SVG `<path>` element with `class` containing `rv-lineage-edge` (or equivalent React Flow edge selector) is present in the rendered output.
- `target_surfaces`:
  - `frontend/runs-viewer/src/components/LineageGraph/LineageFlow.tsx` (test file alongside)

#### AC 4.4: Existing unit tests remain green
- `lineageFlowElements.test.ts` continues to pass without modification (edge construction logic is unchanged; only registration is added).

---

### AC 5: Re-export and rebuild static data

- `rf run export --all` is run after backend export changes and completes without error.
- `pnpm --filter runs-viewer build` is run after re-export and succeeds (prebuild step regenerates `public/data/`).
- `public/data/index.json` entries contain the `title` field after rebuild.
- At least one run's `public/data/<id>/run.json` contains `title` with a non-slug human-readable string (verified by inspection).

---

## 10. Validation Requirements

- [ ] **TypeScript typecheck** passes: `npx tsc --noEmit` in `frontend/runs-viewer/` with no new errors.
- [ ] **ESLint** passes: `pnpm --filter runs-viewer lint` (or equivalent) with no new warnings/errors.
- [ ] **Unit tests** added: `coerceDetailTab` fallback test (AC 3.1); `LineageFlow` render-level test (AC 4.3).
- [ ] **Existing tests pass**: `lineageFlowElements.test.ts` and any existing `detailTabs.test.ts` continue green.
- [ ] **Build passes**: `pnpm --filter runs-viewer build` completes successfully after export changes.
- [ ] **Runtime smoke** (manual): open the deployed viewer at `10.42.10.76:3030`; verify (a) run titles on Portfolio, (b) click opens modal, (c) default tab is Overview, (d) Lineage graph shows edges. Capture screenshots for ACs 1.4 and 4.2.
- [ ] **No unrelated changes** introduced (no refactor of ClaimLedger, ProvenanceModal, or other features not in scope).
- [ ] **CHANGELOG `[Unreleased]`** entry added (user-facing title display + lineage fix qualify as user-visible improvements).

---

## 11. Risk Areas

- **React Flow v12 edge API version drift**: `SmoothStepEdge` export path may differ between `@xyflow/react` minor versions. Implementer must verify the import from the actual installed version (`package.json` lock). If `SmoothStepEdge` is not a named export, check for `BezierEdge` or the `BaseEdge` + `getSmoothStepPath` pattern as fallback.
- **`report_draft` frontmatter parsing in Python**: `report_draft` is a raw Markdown string with a fenced YAML block at the top. Parsing must handle cases where the frontmatter is absent, malformed, or missing the `title` key without raising an exception in `export_run()`. Use a try/except and fall back to slug derivation.
- **Title cost on list view**: Prior design had `deriveRunTitle()` requiring the full `RFRunExport`; this contract mitigates by adding `title` to `RFRunSummary` (list-view summary). Ensure the list view reads from `RFRunSummary.title`, not from a lazy-loaded full export. No extra HTTP/disk reads per card.
- **Nav highlight / state synchronism** (§1.4 bug): the root cause may be a `setSelectedRunId` call without an accompanying `setModalRunId` call in a non-obvious click path (e.g., a programmatic selection from lineage or audit). Reproducing the bug is mandatory before fixing; document the reproduction steps in the Completion Report.
- **coerceDetailTab alias integrity**: changing the fallback from `'trust'` to `'overview'` must not break the `'audit'→'ledger'` alias or any existing bookmarked URL with explicit `?tab=trust` (those still resolve to trust because the coercion only applies to null/unrecognized values).
- **Static-data re-export scope**: re-exporting all runs may take several minutes on a large corpus. If `rf run export --all` fails on any run, the implementer must document the failure and ensure the rest of the index is still updated (partial failure must not block deployment).

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):

1. **Start with the two-line lineage fix** (AC 4.1): it is the highest-confidence, lowest-risk change. Add the import, define `edgeTypes`, pass it to `<ReactFlow>`. Run existing tests. Write the render-level test (AC 4.3). Commit.
2. **Fix `coerceDetailTab`** (AC 3.1): change line 8 from `return "trust"` to `return "overview"`. Add unit tests. Verify modal default is unchanged. Commit.
3. **Reproduce and fix the run-click bug** (AC 2.1–2.2): add console/debugger instrumentation to trace which click handlers fire; identify whether `setModalRunId` is called in all paths. Fix the divergence. Verify "Open full page" still works. Commit.
4. **Add title to export** (AC 1.1–1.4): edit `export_service.py:export_run()` to derive and include `title`; edit `prebuild-static-data.mjs` to include `title` in the summary; add `title?: string` to `RFRunSummary` in `run-export.ts`; update `RunCard` and `RunList.tsx` to display `title` (with `titleFromSlug` fallback). Run `rf run export --all` + `pnpm build`. Commit.
5. **Runtime smoke** (AC 5 + validation §10): deploy and capture screenshots for ACs 1.4 and 4.2. Attach to Completion Report.

**Similar existing code / patterns:**
- `nodeTypes` definition at `LineageFlow.tsx:~164-168` — `edgeTypes` follows the same module-scope pattern.
- `deriveRunTitle()` at `lib/runs.ts:193-202` — shows the title derivation chain already available on FE; the new `RFRunSummary.title` skips the report_draft parsing on list views.
- `titleFromSlug()` at `lib/runs.ts:245-254` — used as the final fallback; already handles null/undefined input.
- `ProvenanceModal.tsx` — example of modal open/close state and stacking; not modified here but illustrates the overlay pattern.

**Known gotchas:**
- `@xyflow/react` v12 may require `edgeTypes` to be defined outside the component render function (as a stable reference) to avoid edge flickering on re-render. The module-scope `const edgeTypes = {...}` pattern (same as `nodeTypes`) is the correct approach — do not define inside the component.
- `prebuild-static-data.mjs` runs `rf run export --all` as a subprocess during `pnpm build`. If the Python environment is not activated, the prebuild will fail silently or error. The deployer must ensure the RF venv is active in the build environment.
- `report_draft` in `run.yaml` may be a multiline string starting with `---\ntitle: ...\n---\n...`; use a YAML or regex parse scoped to the frontmatter block only; do not attempt to parse the entire Markdown body as YAML.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason.
- **Bug reproduction**: Step-by-step reproduction of the §1.4 nav/click bug before the fix; confirmed fix behavior after.
- **Tests run**: `coerceDetailTab` unit tests (AC 3.1), `LineageFlow` render test (AC 4.3), full test suite results.
- **Validation results**: Table of all validation commands and their results (tsc, lint, build, rf run export --all).
- **Screenshots**: Portfolio page with titles (AC 1.4); Lineage graph with edges (AC 4.2).
- **Deviations from contract**: Any material changes and justification.
- **Risks / Limitations**: Remaining risks (e.g., runs that haven't been re-exported still show slug-derived titles).
- **Follow-up recommendations**: P1 items (data-driven claim-volume threshold; This Week filter enablement) and any other observed gaps.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## P1 Items (Out of Scope — Noted for Follow-up)

The following items were identified during planning but are deferred from this contract:

- **Data-driven "High Claim Volume" threshold** (`RunList.tsx` FilterTabs): currently hardcoded at 75 claims. Should be derived from the actual distribution of `claim_counts` across the loaded runs. Deferred because it requires a data analysis pass and a UI to configure the threshold; not a blocker for the core fixes in this contract.
- **Enable "This Week" filter** (`FilterTabs.tsx`): the `This Week` filter tab is currently disabled because `created_at` was previously absent from the index summary. Now that `created_at` is in `RFRunSummary`, this filter can be enabled with a simple date-window comparison. Deferred because it is a new feature (not a fix), but the prerequisite data is now present. Can be a Tier 0 quick-feature follow-on.

---

## Metadata & References

**Tier**: 1 (7 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration.

**Reviewer**: `task-completion-validator` (mandatory at sprint end)

**Related Documents**:
- `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md` — parent epic
- `frontend/runs-viewer/src/components/LineageGraph/LineageFlow.tsx` — primary lineage fix target
- `frontend/runs-viewer/src/lib/runs.ts` — `deriveRunTitle()`, `titleFromSlug()`
- `frontend/runs-viewer/src/components/RunDetail/detailTabs.ts` — `coerceDetailTab()` fix
- `frontend/runs-viewer/src/types/rf/run-export.ts` — `RFRunSummary` type update
- `src/research_foundry/services/export_service.py` — backend `title` export
- `frontend/runs-viewer/scripts/prebuild-static-data.mjs` — index.json summary update
- `.claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md` — verified source intel (§1.1–1.4, §1.6)

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. The four sub-items (a)–(d) in §4 In Scope are intentionally ordered from lowest-risk to highest-integration: start with lineage edges (isolated), then default tab (2-line fix + test), then the nav/click bug (requires reproduction), then the title export (backend + FE + rebuild).

If you find:
- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with justification.

Stay within scope. Avoid cleanup, refactors, or feature expansion beyond this contract. The reviewer will check for scope drift.
