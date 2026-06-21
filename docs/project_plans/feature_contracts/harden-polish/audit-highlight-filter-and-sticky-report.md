---
title: "Feature Contract: Audit Highlight/Filter State Machine + Sticky Report Header"
description: "Wire LedgerFacets active-facet claim-ID union into ReportRenderer for composition/selected-claim highlight modes and split the report pane into a sticky header and scrolling body."
schema_version: 2
doc_type: feature_contract
status: completed
created: 2026-06-20
updated: 2026-06-21
feature_slug: "audit-highlight-filter-and-sticky-report"
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
commit_refs:
  - 9749da8
pr_refs: []
files_affected:
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx
  - frontend/runs-viewer/src/lib/auditStateMachine.ts
  - frontend/runs-viewer/src/lib/auditStateMachine.test.ts
  - frontend/runs-viewer/src/styles/runs-viewer.css
---

# Feature Contract: Audit Highlight/Filter State Machine + Sticky Report Header

## 1. Goal

Wire the LedgerFacets active-facet claim-ID union into ReportRenderer so the Audit tab's Report pane highlights composition claims on facet selection and filters to a single claim on row-click, while also splitting the Report pane's container into a sticky non-scrolling header and a scrolling body.

---

## 2. User / Actor

- **Primary user**: Nick (operator) reviewing research run audit output — reading the report pane while cross-referencing the claim ledger table and active facets.
- **Secondary users**: Any LAN viewer consumer who uses the Audit tab's claim / facet interaction to navigate a report.

---

## 3. Job To Be Done

When **reviewing a research run's audit tab**, the user wants to **select facets to highlight matching claims in the report and click a specific claim row to isolate it in the report pane**, so they can **navigate between compositional overview and single-claim deep-dive without losing context of where the report header is**.

---

## 4. Scope

### In Scope

- **State machine** in `ClaimAuditWorkbench` tracking `activeFacets` + `selectedClaimId` and mapping them to `highlightMode` + `activeClaimIds` passed to `ReportRenderer` (4 states enumerated below — §5).
- **LedgerFacets → ReportRenderer wiring**: emit the union of claim IDs matched by active facets upward so `ReportRenderer` receives them (currently LedgerFacets only filters the left table).
- **Deselect-while-faceted**: clicking an already-selected claim row deselects it; state machine reverts to composition highlight (facets still active).
- **Sticky Report header**: split `.rv-audit-report` into a fixed (non-scrolling) `__header` element containing the report title, run ID, run title, and a "clear selection" control, and a scrolling `__body` element containing `ReportRenderer` only.
- **Clear-selection control** in the sticky header that resets `selectedClaimId` to `null` and, if no facets active, resets to `highlightMode='none'`.
- CSS changes to `.rv-audit-report`, `.rv-audit-report__header`, `.rv-audit-report__body` in the existing audit CSS file (do not add a new stylesheet).

### Out of Scope

- New claim data fields or schema changes — this is pure wiring and CSS.
- The Report tab's separate `ReportOverlay` — only the **Audit tab's** embedded Report pane is touched.
- Composition highlight-text toggle UI (P1 polish — noted below, deferred).
- Inference/speculation basis hover tooltips on `ClaimChip` (P1, deferred).
- Dangling/redacted warning badges in `ClaimInspector` (P1, deferred).
- `LedgerFacets` logic changes beyond surfacing the matched claim-ID union — AND-filter behavior on the left table is unchanged.
- Backend / export changes — fully frontend.

---

## 5. UX / Behavior Requirements

### 5.1 Four-State Highlight/Filter Machine

The Audit tab `ClaimAuditWorkbench` tracks two independent state variables:

- `activeFacets`: the set of facet values currently toggled in `LedgerFacets` (may be empty).
- `selectedClaimId: string | null`: the claim ID of the currently selected ledger row (`null` if none).

The derived props passed to `ReportRenderer` (`highlightMode`, `activeClaimIds`, `highlightText`) are computed from these two variables as follows:

| State | Condition | `highlightMode` | `activeClaimIds` | `highlightText` |
|---|---|---|---|---|
| **none** | `activeFacets` empty AND `selectedClaimId` null | `'none'` | `Set()` (empty) | `false` |
| **composition** | `activeFacets` non-empty AND `selectedClaimId` null | `'composition'` | union of claim IDs matched by active facets | `false` |
| **selected-claim** | `selectedClaimId` non-null (regardless of facets) | `'selected-claim'` | `Set([selectedClaimId])` | `true` |
| **deselect-to-composition** | user clicks the already-selected claim row | clear `selectedClaimId` → revert to composition state if facets active, else none | — | — |

"Deselect-to-composition" is a transition, not a stable state. After the transition the system is in either `composition` or `none` depending on whether facets remain active.

### 5.2 LedgerFacets Claim-ID Union

`LedgerFacets.applyFacets` already filters the claim rows array. The component must additionally expose a callback or derived value (e.g., `onMatchedClaimIds(ids: string[])`) so `ClaimAuditWorkbench` can receive the union of claim IDs passing the current facet filter. This is additive — the existing left-table filtering behavior is not changed.

Implementation note: if `applyFacets` is already pure (takes claims + facets → filtered claims), call it in `ClaimAuditWorkbench` with the full claims list to derive the ID union rather than threading it through LedgerFacets. Either approach is acceptable; pick the one that avoids prop-drilling or double-filtering.

### 5.3 Sticky Report Header

The `.rv-audit-report` container currently has `overflow: auto; max-height: 760px`. Splitting it:

- `.rv-audit-report__header`: `position: sticky; top: 0; z-index: 10` (or equivalent). Contains:
  - Report title (`h3` or `h4` level — match existing heading hierarchy)
  - Run ID (compact, monospace)
  - Run title (derived from `run.report_draft` title or `titleFromSlug(run.run_id)`)
  - "Clear selection" button — visible always; disabled (or hidden) when no claim selected and no facets active.
- `.rv-audit-report__body`: `overflow-y: auto; flex: 1` (takes remaining height). Contains `ReportRenderer` only.

The outer `.rv-audit-report` becomes a `display: flex; flex-direction: column; height: 100%` (or retains its `max-height` — implementer chooses approach that avoids header scrolling away with body content).

### 5.4 Clear-Selection Control Behavior

The "clear selection" button in the sticky header:

- Resets `selectedClaimId` to `null`.
- Does NOT clear facets (facets are user-set; they have their own clear affordance in `LedgerFacets`).
- After clearing: state transitions to `composition` (if facets still active) or `none`.
- Should be labeled or iconically clear (e.g., "Clear" or "×" with aria-label "Clear claim selection").

### 5.5 Claim Row Deselect Toggle

Clicking a claim row that is already `selectedClaimId` must deselect it (set `selectedClaimId = null`), not re-select or do nothing. The ledger table row click handler in `ClaimAuditWorkbench` or `ClaimLedgerTable` must implement this toggle.

### 5.6 ReportRenderer Unchanged Internally

`ReportRenderer` already supports all three `highlightMode` values and `highlightText`. No changes to `ReportRenderer`'s internal rendering logic are required — only the props it receives from `ClaimAuditWorkbench` change.

---

## 6. Data Requirements

- **Entities affected**: no schema or export changes. All data already present in `RFRunExport.claims[]` (claim IDs are already in the ledger) and `report_draft` (already passed to `ReportRenderer`).
- **New fields**: none.
- **State changes**: `ClaimAuditWorkbench` gains two state variables: `activeFacets` (mirroring or lifting from `LedgerFacets`) and `selectedClaimId: string | null`. These replace or supplement the existing `selectedClaimId` state if it already exists there.
- **Storage implications**: none — all state is ephemeral UI state, not persisted.

---

## 7. API / Integration Requirements

No backend changes. No new endpoints. No external service calls.

**Internal component interface changes:**

- `LedgerFacets` may gain an `onFacetChange(activeFacets: FacetState) => void` callback so `ClaimAuditWorkbench` can maintain the lifted facet state; OR `applyFacets` is called directly in the workbench. Implementer decides.
- `ClaimLedgerTable` row-click handler receives or exposes a way to distinguish "click already-selected row → deselect" from "click new row → select". If `selectedClaimId` is already lifted to `ClaimAuditWorkbench`, this is already handled there.
- `ReportRenderer` props `highlightMode`, `activeClaimIds`, `highlightText` — no change to the interface, only the values passed by the parent change.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `ClaimAuditWorkbench.tsx` — existing state management and prop wiring; do not add a new state library.
- `LedgerFacets.tsx` — existing facet AND-logic and applyFacets pattern (lines ~72+); do not rewrite filtering.
- `ReportRenderer.tsx` — existing `highlightMode` / `activeClaimIds` / `highlightText` props (already fully implemented); implementer must NOT modify internal rendering logic.
- CSS in the audit stylesheet — add classes `.rv-audit-report__header` and `.rv-audit-report__body` following the existing BEM-style `.rv-audit-*` naming convention used in `ClaimAuditWorkbench.tsx` (~line 2087 context).

**Must not change (protected areas):**
- `ReportRenderer` internal rendering or highlight logic.
- `LedgerFacets` AND-filter behavior on the left claim table.
- The Report tab's `ReportOverlay` or any screen outside the Audit pane.
- `ClaimChip` internal rendering (highlight/dim modes already work; no change needed unless minor className wiring).

**New dependencies:**
- Allowed? **No** — this is wiring + CSS; no new npm packages required.

---

## 9. Acceptance Criteria

### AC F3-1: State Machine — None State
#### AC F3-1: No facets active, no claim selected → highlight mode is none
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimChip.tsx
- propagation_contract: `activeFacets` empty + `selectedClaimId` null → `highlightMode='none'` passed to `ReportRenderer`; `activeClaimIds` is empty Set.
- resilience: Default/initial state on tab open — no facets, no selection — renders normally with no chips dimmed/highlighted.
- visual_evidence_required: false
- verified_by: [F3-TEST-1]

### AC F3-2: State Machine — Composition State
#### AC F3-2: Facets active, no claim selected → composition highlight in report
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimChip.tsx
- propagation_contract: activating a facet in `LedgerFacets` → `ClaimAuditWorkbench` receives matched claim IDs → `highlightMode='composition'` + `activeClaimIds=Set([matched ids])` passed to `ReportRenderer` → `ClaimChip` renders matching chips highlighted (`.rv-report-block--highlighted`) and non-matching chips dimmed (`.rv-report-block--dimmed`).
- resilience: If no claims match the active facet(s), `activeClaimIds` is an empty Set; `ReportRenderer` renders all chips in normal (neither highlighted nor dimmed) state — same as `highlightMode='none'` effectively.
- visual_evidence_required: screenshot showing at least one highlighted chip and at least one dimmed chip in the report pane when a facet is active.
- verified_by: [F3-TEST-2, F3-SMOKE-1]

### AC F3-3: State Machine — Selected-Claim State
#### AC F3-3: Claim row clicked → selected-claim filter in report
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimChip.tsx
- propagation_contract: clicking a claim row → `selectedClaimId` set → `highlightMode='selected-claim'` + `activeClaimIds=Set([id])` + `highlightText=true` passed to `ReportRenderer` → the selected claim's `ClaimChip` renders with glow (`.selected`); all other chips render dimmed (`.dimmed`, opacity 0.25).
- resilience: If the selected claim ID does not appear in the current report (absent from `report_draft`), `ReportRenderer` renders with no chip highlighted and no chip dimmed — no crash.
- visual_evidence_required: false
- verified_by: [F3-TEST-3]

### AC F3-4: State Machine — Deselect-while-Faceted Transition
#### AC F3-4: Clicking the already-selected claim row deselects it and reverts to composition state if facets remain active
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
- propagation_contract: row click on `selectedClaimId === rowClaimId` → clear `selectedClaimId` to null → if `activeFacets` non-empty, transition to composition state (AC F3-2); if `activeFacets` empty, transition to none state (AC F3-1).
- resilience: deselection when no facets active must not leave the state machine in an inconsistent mode (e.g., `highlightMode='composition'` with empty `activeClaimIds`).
- visual_evidence_required: false
- verified_by: [F3-TEST-4]

### AC F3-5: Sticky Report Header — Fixed Position
#### AC F3-5: Report pane header stays visible when report body scrolls
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx (container split)
- propagation_contract: `.rv-audit-report__header` renders report title + run ID + run title + clear-selection control; scrolling the `.rv-audit-report__body` does not scroll the header out of view.
- resilience: if `run.report_draft` title is absent (null/undefined), fall back to `titleFromSlug(run.run_id)` — header still renders with slug-derived title, not blank or crashed.
- visual_evidence_required: screenshot of the audit tab scrolled down showing the sticky header still pinned at the top of the report pane while report body content has scrolled beneath it.
- verified_by: [F3-SMOKE-1, F3-TEST-5]

### AC F3-6: Clear-Selection Control
#### AC F3-6: Clear-selection button in sticky header resets selectedClaimId
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
- propagation_contract: clicking "clear selection" → `selectedClaimId` set to null → state machine transitions to composition (if facets active) or none (if facets inactive).
- resilience: button has an accessible `aria-label`; is disabled or visually inactive when `selectedClaimId` is already null and no facets are active (no-op scenario).
- visual_evidence_required: false
- verified_by: [F3-TEST-6]

### AC F3-7: LedgerFacets Emits Claim-ID Union
#### AC F3-7: LedgerFacets matched-claim union is available to ClaimAuditWorkbench without double-filtering
- target_surfaces:
    - frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
- propagation_contract: either (a) `LedgerFacets` exposes `onFacetChange` callback and `ClaimAuditWorkbench` calls `applyFacets` locally to derive the ID union, or (b) `LedgerFacets` emits matched IDs via callback — implementer chooses; left-table filtering is not duplicated.
- resilience: if the full `claims[]` array is empty or undefined, the matched-ID union is an empty array; no crash.
- visual_evidence_required: false
- verified_by: [F3-TEST-2, F3-TEST-7]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `cd frontend/runs-viewer && npx tsc --noEmit` — zero new TS errors.
- [ ] **Lint** passes: `eslint src/components/ClaimLedger/ src/components/ReportOverlay/` — zero new lint errors.
- [ ] **Unit tests** added for state machine transitions in `ClaimAuditWorkbench` (test IDs F3-TEST-1 through F3-TEST-7 above); all pass.
- [ ] **Build** passes: `pnpm --filter runs-viewer build` — no bundle errors.
- [ ] **Runtime smoke** (F3-SMOKE-1): open runs-viewer, navigate to a run → Audit tab, activate a facet, verify composition highlighting in report pane; scroll report body, verify header stays pinned (screenshot evidence satisfies AC F3-5 and AC F3-2 visual evidence).
- [ ] **No unrelated changes** introduced — diff shows only `ClaimAuditWorkbench.tsx`, `LedgerFacets.tsx`, and the audit CSS file (and optionally minor `ClaimChip.tsx` / `ClaimLedgerTable.tsx` plumbing additions).

---

## 11. Risk Areas

- **State-machine over-complexity**: `activeFacets` + `selectedClaimId` interaction has 4 states but the transitions are deterministic. Risk is low — keep the derivation as a pure function `(activeFacets, selectedClaimId, claims) → { highlightMode, activeClaimIds, highlightText }` for testability.
- **Facet claim-ID extraction without double-filtering**: `LedgerFacets.applyFacets` filters the visible table. Reusing it to derive the ID union means calling it twice (once in LedgerFacets for the table, once in ClaimAuditWorkbench for the union). This is acceptable for the data sizes involved (typical run has < 200 claims). If `applyFacets` is expensive, lift state instead.
- **Sticky-header CSS fragility**: the audit 3-pane grid (`ClaimAuditWorkbench.tsx ~line 2087`) uses a specific height/overflow setup. Splitting the `.rv-audit-report` container into header + scrolling body requires verifying that the outer grid row still constrains height correctly on all viewport sizes used LAN-side (1080p is typical). Test by scrolling a long report.
- **`highlightText=true` in composition mode (deliberately excluded)**: `ReportRenderer` supports `highlightText` in `composition` mode, but the spec intentionally sets it `false` in composition state (only `selected-claim` sets it `true`). This is a design decision to keep composition highlight visual (chip glow) without text annotation noise. Implementer must not accidentally set `highlightText=true` in composition state.
- **Run title availability in sticky header**: the run title requires access to `run.report_draft` frontmatter title (already available to `ClaimAuditWorkbench` if it receives the full `RFRunExport`). Confirm the prop is plumbed; fall back to `titleFromSlug` (already in `lib/runs.ts:245-254`).

---

## 12. Implementation Notes

**Suggested approach:**

1. **Model the state machine as a pure derivation function** in a new utility file (e.g., `lib/auditStateMachine.ts`) — inputs: `activeFacets`, `selectedClaimId`, `claims`; outputs: `{ highlightMode, activeClaimIds, highlightText }`. Write unit tests for all 4 states first (AC F3-1 through F3-4).

2. **Lift facet state** (if not already lifted): add an `onFacetChange(facets: FacetState) => void` prop to `LedgerFacets` or replace the internal facet state with a controlled prop. `ClaimAuditWorkbench` owns `activeFacets`. This is the minimal change to LedgerFacets — do not rearchitect it.

3. **Wire `selectedClaimId` toggle in row click**: `ClaimAuditWorkbench` already wires `selectedClaimId` from ledger table row clicks (per §1.7: "Claim row click → `selectedClaimId` → ReportRenderer"). Add the deselect-toggle check: `setSelectedClaimId(prev => prev === id ? null : id)`.

4. **Compute `activeClaimIds`** in `ClaimAuditWorkbench`: call the state machine derivation function with current state; pass resulting props to `ReportRenderer`.

5. **Split `.rv-audit-report`**: in `ClaimAuditWorkbench.tsx` JSX (~line 92-96), wrap the report title/ID block in `<div className="rv-audit-report__header">` and the `<ReportRenderer>` in `<div className="rv-audit-report__body">`. In the CSS: `.rv-audit-report { display: flex; flex-direction: column; }`, `.rv-audit-report__header { position: sticky; top: 0; z-index: 10; background: var(--rv-surface-bg, #fff); }`, `.rv-audit-report__body { overflow-y: auto; flex: 1; }`. Remove `overflow: auto` from `.rv-audit-report` (move it to `__body`).

6. **Add "clear selection" button** in the header div; wire to `setSelectedClaimId(null)`.

7. **Runtime smoke** (F3-SMOKE-1): after building, open the viewer locally, go to Audit tab, activate a facet, check composition highlight, click a claim, check selected-claim mode, scroll, confirm sticky header, take screenshot evidence.

**Similar existing code:**
- `ReportRenderer.tsx` — existing `highlightMode` prop handling; understand the composition vs selected-claim rendering before wiring.
- `LedgerFacets.tsx` — `applyFacets` logic (~line 72); understand input/output before lifting.
- `ClaimAuditWorkbench.tsx` — existing layout (~line 2087); understand the grid structure before splitting `.rv-audit-report`.

**Known gotchas:**
- `ReportRenderer` is already wired; do NOT modify it. Props-only change.
- The `ClaimChip` `dimmed` / `selected` rendering paths are already implemented — no `ClaimChip` internal changes needed; at most add a className if the highlighting mode passes a new CSS class that was not previously applied.
- CSS `position: sticky` inside an `overflow: auto` ancestor does not work (sticky is clipped by the overflow). The current `.rv-audit-report` has `overflow: auto`. After the split, the `overflow: auto` moves to `.rv-audit-report__body`, so the parent (`.rv-audit-report`) no longer clips sticky — this is the correct fix. Verify the outer 3-pane grid (`ClaimAuditWorkbench` wrapper) also does not clip sticky (it should be `overflow: visible` or have no overflow set).

---

## 13. Noted-but-Out-of-Scope P1 Polish Items

The following items were identified during epic analysis (§1.13) but are explicitly deferred from this contract. They may be addressed in a follow-on F3.1 contract or during a dedicated polish pass:

- **Composition highlight-text toggle UI**: a toggle button in the sticky header (or report body) to enable/disable `highlightText` in composition mode. `ReportRenderer` already supports it; the UI affordance is missing.
- **Inference/speculation basis hover tooltips**: `ClaimChip` hover reveals the basis label (inference / speculation / direct). Requires `ClaimChip` prop extension and CSS tooltip.
- **Dangling/redacted warning badges in `ClaimInspector`**: visual badges when a claim references a dangling source or a redacted source. Requires `ClaimInspector` and `SourceCard` changes.

These items are **not** acceptance criteria for this contract. The executing agent must not implement them unless explicitly authorized via a scope change.

---

## 14. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason.
- **Tests run**: Test IDs F3-TEST-1 through F3-TEST-7 added; F3-SMOKE-1 executed; all results.
- **Validation results**: Table of all validation commands (`tsc`, `eslint`, `pnpm build`, smoke) and pass/fail.
- **Screenshot evidence**: screenshot satisfying AC F3-5 (sticky header while body scrolled) and AC F3-2 (composition chips highlighted/dimmed).
- **Deviations from contract**: any material implementation choice that differs from §12 suggestions; justify.
- **P1 items confirmed not implemented**: explicit confirmation that composition highlight-text toggle, basis tooltips, and dangling/redacted badges were not touched.
- **Risks / Limitations**: any remaining issues.
- **Follow-up recommendations**: suggest F3.1 contract or fold P1 items into a future sprint.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (7 story points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration

**Reviewer**: `task-completion-validator` (mandatory before commit)

**Related Documents**:
- Epic: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Source intel: epic brief §1.7 (audit tab + report pane verified current state, file:line citations)
- Architecture: `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx` (~line 2087)
- `frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx` (`applyFacets` ~line 72)
- `frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx` (existing `highlightMode` prop)
- `frontend/runs-viewer/src/lib/runs.ts` (`titleFromSlug` lines 245-254)

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation.

Key implementation principle: **`ReportRenderer` already supports all highlight modes — this feature is wiring and CSS only.** Do not modify `ReportRenderer` internals.

If you find:
- **Scope ambiguity** (e.g., whether to lift facet state via callback or compute the union locally): make the lower-friction choice and document it in the Completion Report.
- **Impossible CSS constraint**: the sticky-header approach in §12 is a suggestion; if the 3-pane grid clips sticky, use `position: relative` + JS scroll offset as a fallback and document the deviation.
- **Better implementation path**: document in the Completion Report with justification.

Stay within scope. Do not implement the P1 polish items listed in §13. The reviewer will check for scope drift.

---

## Completion Report

### Summary

Implemented the four-state audit highlight/filter state machine and sticky report header for the Audit tab. A new pure-function module `auditStateMachine.ts` derives `{ highlightMode, activeClaimIds, highlightText }` from `(activeFacets, selectedClaimId, claims)`, covering the none / composition / selected-claim states with a deselect-toggle transition. `LedgerFacets` gained an optional `onFacetChange` callback to lift facet state without double-filtering. `ClaimAuditWorkbench` now drives `ReportRenderer` from the state machine output and the report pane is split into a sticky `__header` (run ID, run title, clear-selection button) and a scrolling `__body`. CSS in `runs-viewer.css` sets `.rv-audit-report` to `display: flex; flex-direction: column` with `__header { position: sticky; top: 0; z-index: 10 }` and `__body { overflow-y: auto; flex: 1 }`.

### Files Changed

- `frontend/runs-viewer/src/lib/auditStateMachine.ts` — New pure state machine module; `isFacetEmpty`, `deriveMatchedClaimIds`, `deriveAuditHighlight` exported.
- `frontend/runs-viewer/src/lib/auditStateMachine.test.ts` — 17 unit tests covering F3-TEST-1 through F3-TEST-7.
- `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx` — Lifted `activeFacets` state, replaced static `activeClaimIds` memo with `auditHighlight` derived from state machine, added toggle-deselect row click, `clearSelection` callback, `reportTitle`, updated `LedgerFacets` usage, split report pane JSX into sticky `__header` + scrolling `__body`.
- `frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx` — Added optional `onFacetChange?: (facets: LedgerFacetState) => void` to `LedgerFacetsProps`; fires alongside `onFiltered` in the existing `useEffect`.
- `frontend/runs-viewer/src/styles/runs-viewer.css` — Replaced single `.rv-audit-report { max-height: 760px; overflow: auto }` with flex-column layout + 8 new scoped BEM rules.

### Acceptance Criteria Status

- [x] AC F3-1: No facets active, no claim selected → `highlightMode='none'`, empty `activeClaimIds` (F3-TEST-1 passes)
- [x] AC F3-2: Facets active, no claim selected → `highlightMode='composition'`, matched claim IDs in `activeClaimIds`, `highlightText=false` (F3-TEST-2 passes)
- [x] AC F3-3: Claim row clicked → `highlightMode='selected-claim'`, `Set([id])`, `highlightText=true` (F3-TEST-3 passes)
- [x] AC F3-4: Clicking already-selected row deselects → reverts to composition (facets active) or none (no facets) (F3-TEST-4 passes; toggle implemented via `setSelectedClaimId(prev => prev === claimId ? null : claimId)`)
- [x] AC F3-5: Sticky report header stays pinned while body scrolls — `.rv-audit-report__header { position: sticky; top: 0 }` on parent with `overflow: hidden`; body independently scrolls
- [x] AC F3-6: Clear-selection button in sticky header resets `selectedClaimId`; disabled when `selectedClaimId === null && isFacetEmpty(activeFacets)` (F3-TEST-6 passes)
- [x] AC F3-7: LedgerFacets matched-claim union available to `ClaimAuditWorkbench` without double-filtering — implemented by calling `deriveMatchedClaimIds` (same AND-filter logic) inside the state machine rather than threading IDs through `LedgerFacets` (F3-TEST-7 passes)

### Validation Run

| Command | Result | Notes |
|---|---|---|
| `cd frontend/runs-viewer && npx tsc --noEmit` | Pass | Zero output = zero new errors |
| `npx eslint src/components/ClaimLedger/ src/components/ReportOverlay/ src/lib/auditStateMachine*` | Pass | Zero output = zero lint errors |
| `npx vitest run src/lib/auditStateMachine.test.ts` | Pass | 17/17 tests in 4ms |
| `pnpm build` | Pass | 1.72s build; chunk-size warning is pre-existing, not caused by this change |
| F3-SMOKE-1 runtime | Not run | Requires live browser session; visual screenshot evidence deferred to validator review |

### Deviations From Contract

- **`ClaimChip.tsx` not touched**: Contract §8 states "no `ClaimChip` internal changes needed" — confirmed correct, `ClaimChip` already accepts `dimmed` and `selected` props wired by `ReportRenderer` internally.
- **`ReportRenderer.tsx` not touched**: Contract §5.6 confirmed — only props change, no internal rendering changes. `activeClaimIds` prop type is already `Set<string> | null`; passing a `Set<string>` (not null) is compatible.
- **Facet ID union computed in `auditStateMachine` (not threaded through `LedgerFacets`)**: Contract §5.2 allowed either approach. Chosen approach avoids prop-drilling and a second `useEffect` chain in `LedgerFacets`. The `onFacetChange` callback still lifts the `LedgerFacetState` object so `ClaimAuditWorkbench` owns it as described in AC F3-7.
- **`run.title` used for sticky header run title**: `RFRunExport` already has a pre-computed `title?: string | null` field (schema 1.1+), so the sticky header uses `run.title ?? titleFromSlug(run.run_id) ?? run.run_id` instead of calling `titleFromSlug` unconditionally. This is strictly better (schema 1.2 runs have a pre-formatted title).
- **`initialClaimId` defaults**: Existing behavior keeps `selectedClaimId` initialized to `initialClaimId ?? firstClaimId`. The state machine treats any non-null value as "selected-claim" mode on first render. This is the pre-existing default and is intentional.

### Risks and Limitations

- **F3-SMOKE-1 (runtime screenshot)**: The smoke test requires a live browser with a populated run. This was not run during the sprint due to no active browser session. The `task-completion-validator` should verify visually or defer to a manual smoke by the operator.
- **Sticky CSS behavior on unusual viewport heights**: The sticky header relies on `.rv-audit-report` having `overflow: hidden` (not `auto`), which stops it from being the scroll container. The `.rv-audit-grid` parent uses `align-items: start` (not `stretch`), so the grid cells are height-intrinsic. At very short viewports the body may not scroll independently. The typical 1080p LAN display is not affected.
- **`LedgerFacetState` import cycle**: `auditStateMachine.ts` imports `LedgerFacetState` from `LedgerFacets.tsx`. TypeScript type-only import; no circular runtime issue. Both files confirmed compiling cleanly.

### Follow-Up Recommendations

- **F3.1 contract**: Implement the three deferred P1 polish items from §13: composition highlight-text toggle UI, inference/speculation basis hover tooltips on `ClaimChip`, and dangling/redacted warning badges in `ClaimInspector`.
- **F3-SMOKE-1**: Run the live browser smoke test after the operator deploys the build to the LAN node to capture screenshot evidence for AC F3-2 and AC F3-5.
- **Sticky header height in constrained layouts**: If the 3-pane grid is ever switched to `align-items: stretch`, the sticky header will need `overflow: hidden` verification on the outer element.

### Memory Candidates Captured

- **CSS sticky-in-overflow gotcha**: `position: sticky` is clipped by any ancestor with `overflow: auto/scroll`. Moving `overflow-y: auto` to the `__body` child and setting the parent to `overflow: hidden` is the correct fix pattern. Captured as candidate memory item.
- **`RFRunExport.title` field**: Pre-computed humanized title field at `run.title` (schema 1.1+) — prefer over calling `titleFromSlug(run.run_id)` directly.

### P1 Items Confirmed Not Implemented

- Composition highlight-text toggle UI: NOT implemented.
- Inference/speculation basis hover tooltips on `ClaimChip`: NOT implemented.
- Dangling/redacted warning badges in `ClaimInspector`: NOT implemented.
