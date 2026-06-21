---
title: "Feature Contract: Item Modal Expansion"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-20
updated: 2026-06-20
feature_slug: item-modal-expansion
category: features
estimated_points: 7
tier: 1
owner: nick
priority: medium
risk_level: medium
changelog_required: false
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
  - docs/project_plans/feature_contracts/harden-polish/nav-titles-lineage-fixes.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Feature Contract: Item Modal Expansion

## 1. Goal

Any item in the runs-viewer — a run card, a lineage node row, or a claim ledger row — can be expanded to a full detail modal via double-click OR an explicit expand button (⤢), in both list-view and side-pane contexts, while single-click continues to open the existing side-pane detail unchanged.

---

## 2. User / Actor

- **Primary user**: Nick (operator) reviewing research runs on the LAN SPA at `10.42.10.76:3030`.
- **Secondary users**: Any developer consuming the static export viewer.

---

## 3. Job To Be Done

When the user is scanning the portfolio, lineage graph, or claim ledger and spots a row of interest, they want to expand it to a full modal overlay without losing their scrolled position in the list, so they can inspect the item in depth (sources, provenance, node metadata) without navigating away from the current view.

---

## 4. Scope

### In Scope

- **`<DetailModal>` component** — a new generic overlay component that mirrors `ProvenanceModal`'s overlay conventions (`role="dialog"`, `aria-modal`, Escape-to-close, backdrop-click-to-close, `stacked` z-index prop, `onOpenChange` callback). Accepts either a claim payload or a lineage-node payload; renders appropriate body content for each.
- **Double-click handler on RunCard** (`RunCard.tsx`) — fires `onExpandRun` callback; parent wires to open `DetailModal` (or the existing `RunDetailModal`) in expanded/full context.
- **Expand button (⤢) on RunCard** — explicit affordance alongside the existing card click/hover actions; same `onExpandRun` target.
- **Double-click handler on LineageList rows** — `LineageList.tsx` rows gain `onDoubleClick → onExpandNode(node)` prop; parent wires to open `DetailModal` with lineage-node payload.
- **Expand button (⤢) on `LineageDetailPanel`** — added to the detail panel header; opens `DetailModal` with the currently selected `LineageNode`.
- **Double-click handler on `ClaimLedgerTable` rows** — rows gain `onDoubleClick → onExpandClaim(claimId)` prop alongside the existing `onClaimSelect` single-click.
- **Expand button (⤢) in `ClaimInspector`** (inside `ClaimAuditWorkbench`) — supplements the existing "Open modal" button; opens `DetailModal` (or the existing `ProvenanceModal` via `modalRef.current?.open(claimId)`) in stacked mode.
- **Stacked z-index support** — `DetailModal` rendered stacked when opened from within an existing overlay (e.g., from `LineageDetailPanel` inside a `RunDetailModal`). Escape dismisses innermost modal first; outer modal Escape is suppressed while inner is open (mirrors existing `ProvenanceModal` + `RunDetailModal` `claimModalOpen` guard pattern).
- **Keyboard**: double-click gesture and explicit expand button are the two entry points; no additional keyboard shortcut required beyond the standard Escape-to-close already mandated.
- **Resilience**: a lineage node with no associated claim (`node.claimId === undefined`) still opens `DetailModal` showing node metadata only (no provenance section); a claim ID not found in the claims array renders "Claim not found" (mirrors `ProvenanceModal` fallback at line 127-132).

### Out of Scope

- New data, new export fields, or backend changes of any kind — FE-only.
- Redaction changes (F4) or metadata enrichment (F5).
- Changes to existing `RunDetailModal` internals beyond wiring `onExpandNode` callbacks.
- Default-tab or run-click routing fix (F1).
- Graph view (`LineageFlow.tsx`) — double-click on React Flow graph nodes is explicitly out of scope for v2.2 (adds React Flow event complexity); list view rows only.
- Mobile/touch optimisation beyond what the existing CSS already handles.

---

## 5. UX / Behavior Requirements

1. **Single-click unchanged**: clicking a RunCard opens `RunDetailModal` (portfolio → modal). Clicking a lineage row selects the node → `LineageDetailPanel` updates. Clicking a claim row → `ClaimInspector` updates. None of these behaviors change.

2. **Double-click expand**: a second click within the browser's native double-click window on any RunCard, lineage list row, or claim ledger row fires the expand action. Implementer must debounce/guard to prevent the first click of a double-click from also triggering the single-click side-pane update, OR accept that single-click fires first then the modal opens on top (both are acceptable; note in Completion Report).

3. **Expand button (⤢)**: visible (not hidden-on-hover-only) on RunCard and in `LineageDetailPanel` header. For `ClaimInspector`, the expand button lives next to the existing "Open modal" button. Button aria-label: `"Expand [item type] in modal"`.

4. **`<DetailModal>` overlay**: renders using the same CSS class pattern as `ProvenanceModal` — `.rv-modal-overlay` / `.rv-modal-overlay--stacked` / `.rv-modal` — so existing z-index and backdrop styles apply. Header shows: item kind label + primary ID (node title or claim ID). Body: for claim payloads, reuse `ProvenanceModal` content or delegate to `ProvenanceModal` in stacked mode. For lineage-node payloads, render the node metadata (title, subtitle, kind, chips, details, claim link) in a readable layout.

5. **Escape ordering**: when `DetailModal` is open inside `RunDetailModal`, pressing Escape closes `DetailModal` first; `RunDetailModal` Escape listener is suppressed while `DetailModal` is open (same guard as existing `claimModalOpen` flag in `RunDetailModal.tsx:59`).

6. **Backdrop click**: clicking the overlay backdrop closes `DetailModal`; does not close the parent modal behind it.

7. **No provenance for lineage node without claim**: if `node.claimId` is absent, `DetailModal` renders node metadata only with a `<p class="rv-muted">No provenance available for this node type.</p>` section. No error thrown.

---

## 6. Data Requirements

- **No new export fields** — all data displayed in `DetailModal` for claims already exists in `run.claims[]` (available in `RunDetailModal` and `ClaimAuditWorkbench`). Lineage node data is already fully populated in `LineageNode` from `lineageTree.ts`.
- **New prop contracts**:
  - `RunCard`: add optional `onExpandRun?: (runId: string) => void` prop.
  - `LineageList` rows (inside `LineageList.tsx`): add optional `onExpandNode?: (node: LineageNode) => void` prop.
  - `ClaimLedgerTable`: add optional `onExpandClaim?: (claimId: string) => void` prop.
  - `LineageDetailPanel`: add optional `onExpandNode?: (node: LineageNode) => void` prop.
  - `ClaimInspector` / `ClaimAuditWorkbench`: `onExpandClaim` or reuse `onOpenModal` already wired at `ClaimAuditWorkbench.tsx:113`.
- **State**: the parent that opens `DetailModal` holds `detailModalPayload: ClaimPayload | LineageNodePayload | null` state; `null` = closed.

---

## 7. API / Integration Requirements

**No backend endpoints, no API calls.** FE-only; all data comes from already-loaded `run.json` static export.

**Internal component integration points:**

- `RunDetailModal.tsx` — add `detailModalPayload` state + `<DetailModal>` render; wire `onExpandNode` down to lineage workspace; update `claimModalOpen` guard to also suppress when `DetailModal` is open.
- `ClaimAuditWorkbench.tsx` — wire `onExpandClaim` from `ClaimInspector`; open `DetailModal` in stacked mode (or delegate to existing `ProvenanceModal` ref, whichever is cleaner; note decision in Completion Report).
- `RunList.tsx` — wire `onExpandRun` from `RunCard` to open `RunDetailModal` (this is already the single-click path; double-click expand opens the same modal, so `onExpandRun` may simply call `setModalRunId(runId)`; document if expansion and selection share the same modal).

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `ProvenanceModal.tsx` — overlay CSS classes (`.rv-modal-overlay`, `.rv-modal-overlay--stacked`, `.rv-modal`), `role="dialog"`, `aria-modal="true"`, `onOpenChange` callback pattern, `stacked` prop.
- `RunDetailModal.tsx` — `claimModalOpen` guard pattern for Escape suppression (lines 59-63); `onClick` backdrop guard (lines 74-76).
- Component prop-callback wiring conventions (callbacks passed down from workspace/workbench parents, not hoisted to global state).

**Must not change (protected areas):**
- `ProvenanceModal` public API (`ProvenanceModalHandle`, `open(claimId)`, `close()`). The new `DetailModal` may internally delegate to `ProvenanceModal` for claim payloads, but must not alter its interface.
- `ClaimLedgerTable` `onClaimSelect` single-click behavior — adding `onExpandClaim` must not interfere.
- `LineageDetailPanel` existing `onOpenProvenance` callback (claim-only, existing button).
- `LineageFlow.tsx` (React Flow graph view) — no changes; double-click on graph nodes is out of scope.
- Static export shape — no new fields, no `prebuild-static-data.mjs` changes.

**New dependencies:**
- Allowed? **No.** `DetailModal` is authored with existing React + CSS patterns only. No new npm packages.

---

## 9. Acceptance Criteria

### AC F2-01: Double-click opens DetailModal on RunCard

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunList/RunCard.tsx`
    - `frontend/runs-viewer/src/screens/RunList.tsx`
- propagation_contract: double-click on RunCard fires `onExpandRun(runId)` → parent (`RunList.tsx`) opens `RunDetailModal` (or passes runId to `DetailModal`).
- resilience: single-click behavior (side-pane / existing modal) is unchanged; double-click does not cause a double-open.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-01]

### AC F2-02: Expand button (⤢) on RunCard opens DetailModal

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunList/RunCard.tsx`
- propagation_contract: clicking the ⤢ button fires `onExpandRun(runId)`.
- resilience: button is visible without hover; does not conflict with existing card-level click.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-01]

### AC F2-03: Double-click on LineageList row opens DetailModal with node payload

- target_surfaces:
    - `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
    - `frontend/runs-viewer/src/components/LineageGraph/LineageList.tsx` (rows)
- propagation_contract: double-click on a lineage list row fires `onExpandNode(node)` → parent renders `<DetailModal>` with the `LineageNode` payload.
- resilience: single-click (select node → `LineageDetailPanel` update) is unchanged.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-02]

### AC F2-04: Expand button (⤢) in LineageDetailPanel opens DetailModal

- target_surfaces:
    - `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
- propagation_contract: ⤢ button in panel header fires `onExpandNode(node)` for the currently selected node.
- resilience: when no node is selected (`node === null`), button is absent or disabled.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-02]

### AC F2-05: Node with no claimId renders graceful modal (resilience)

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunDetail/DetailModal.tsx` (new component)
    - `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
- propagation_contract: `DetailModal` receives `LineageNode` with `claimId === undefined`; renders node metadata + "No provenance available for this node type." text; no error thrown.
- resilience: this IS the resilience AC — modal opens safely for all node kinds.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-02]

### AC F2-06: Double-click on ClaimLedgerTable row opens DetailModal with claim payload

- target_surfaces:
    - `frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx`
    - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
- propagation_contract: double-click on a claim row fires `onExpandClaim(claimId)` → `ClaimAuditWorkbench` opens `DetailModal` (or `ProvenanceModal` in stacked mode) with the claim.
- resilience: single-click → `onClaimSelect` → `ClaimInspector` side-pane update is unchanged.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-03]

### AC F2-07: Expand button (⤢) in ClaimInspector opens DetailModal

- target_surfaces:
    - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
- propagation_contract: ⤢ button (or enhanced "Open modal" button) in `ClaimInspector` fires `onExpandClaim(claimId)` for the selected claim.
- resilience: button absent or disabled when no claim is selected.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-03]

### AC F2-08: Claim not found renders gracefully in DetailModal (resilience)

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunDetail/DetailModal.tsx` (new component)
- propagation_contract: when `claimId` not in `run.claims[]`, renders "Claim not found" message (mirrors `ProvenanceModal.tsx:127-132`).
- resilience: this IS the resilience AC — no uncaught error; no blank screen.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-03]

### AC F2-09: Escape ordering — inner modal closes first

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunDetail/DetailModal.tsx` (new component)
    - `frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx`
- propagation_contract: when `DetailModal` is stacked inside `RunDetailModal`, pressing Escape closes `DetailModal`; `RunDetailModal` Escape listener is suppressed while `DetailModal` is open (mirrors `claimModalOpen` guard at `RunDetailModal.tsx:59`).
- resilience: pressing Escape when no inner modal is open closes `RunDetailModal` as expected.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-04]

### AC F2-10: Backdrop click closes only the topmost modal

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunDetail/DetailModal.tsx` (new component)
- propagation_contract: clicking the `.rv-modal-overlay` backdrop of `DetailModal` closes `DetailModal` only; does not close the parent overlay behind it.
- resilience: clicking inside the `.rv-modal` dialog content area does not close anything.
- visual_evidence_required: false
- verified_by: [F2-VERIFY-04]

### AC F2-11: Runtime smoke — modal opens without console errors

- target_surfaces:
    - `frontend/runs-viewer/src/components/RunList/RunCard.tsx`
    - `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
    - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
    - `frontend/runs-viewer/src/components/RunDetail/DetailModal.tsx` (new component)
    - `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`
- propagation_contract: developer runs `pnpm --filter runs-viewer dev`; exercises each entry point (double-click RunCard, ⤢ LineageDetailPanel, double-click claim row, ⤢ ClaimInspector); browser console shows no uncaught errors or React warnings.
- resilience: smoke passes with a run that has claims AND with a run that has no claims (empty claims array).
- visual_evidence_required: false
- verified_by: [F2-VERIFY-05-SMOKE]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes: `npx tsc --noEmit` (run from `frontend/runs-viewer/`)
- [ ] **Lint** passes: `pnpm --filter runs-viewer lint` (or equivalent eslint invocation)
- [ ] **Unit tests** added for `DetailModal` covering: claim payload render, lineage-node-without-claim render (resilience), Escape handler with `onOpenChange`, and backdrop-click close
- [ ] **Component tests** updated for `ClaimLedgerTable` (double-click fires `onExpandClaim`), `RunCard` (⤢ button fires `onExpandRun`), `LineageDetailPanel` (⤢ button fires `onExpandNode`)
- [ ] **Build passes**: `pnpm --filter runs-viewer build` (Vite; no type or bundle errors)
- [ ] **Runtime smoke** (AC F2-11): exercise all entry points in dev server; zero console errors
- [ ] **No unrelated changes** introduced — diff is scoped to new `DetailModal` component + prop additions + wiring in `RunCard`, `RunList`, `ClaimLedgerTable`, `ClaimAuditWorkbench`, `LineageDetailPanel`, `RunDetailModal`

---

## 11. Risk Areas

- **Stacked-modal focus and Escape ordering**: the existing `claimModalOpen` guard in `RunDetailModal.tsx:59` suppresses the parent Escape listener while `ProvenanceModal` is open. The same pattern must be applied for `DetailModal`. If a third modal stacks (e.g., `DetailModal` opens inside `RunDetailModal` which already has `ProvenanceModal` wired), ordering can collide. Mitigation: limit stacking to one level deep; if `ProvenanceModal` is already open, do not open `DetailModal` simultaneously. Document the invariant.
- **Double-click vs single-click race**: the first click of a double-click also fires the `onClick` handler (single-click action). This may cause a brief side-pane update before the modal opens. Mitigation options: (a) `setTimeout` debounce on single-click (classic pattern but adds latency); (b) accept the sequence (select fires, then modal opens on top) and note in Completion Report. Either is acceptable; document the choice.
- **`LineageList.tsx` row double-click wiring**: the brief cites `LineageList.tsx` rows but the file is not reviewed in full. Implementer must confirm the list renders discrete clickable row elements (not a flat div) where `onDoubleClick` can attach without interfering with internal row interaction patterns.
- **Soft dependency on F1**: the brief notes F2 depends on F1 "soft" for default-tab/title helpers. If F1 is not complete, `deriveRunTitle()` may not be available in list context. Mitigation: `DetailModal` for run-card expand can fall back to `titleFromSlug(runId)` if the full `RFRunExport` is not loaded yet (RunCard expand opens `RunDetailModal` which already fetches the full export).

---

## 12. Implementation Notes

**Suggested approach:**

1. **Author `<DetailModal>`** at `frontend/runs-viewer/src/components/RunDetail/DetailModal.tsx`. Mirror `ProvenanceModal.tsx` overlay structure. Accept a discriminated union prop: `payload: { kind: 'claim'; claimId: string; claims: RFClaim[] } | { kind: 'node'; node: LineageNode }`. Render claim body by delegating to `ProvenanceModal` internals (copy/extract) or render a simplified summary; render node body from `LineageNode` fields. Expose `stacked` + `onOpenChange` props identical to `ProvenanceModal`.

2. **Wire RunCard** (`RunCard.tsx`): add `onExpandRun?: (runId: string) => void` prop; add ⤢ button to card header/actions area; add `onDoubleClick` to card root element calling `onExpandRun?.(runId)`.

3. **Wire RunList** (`RunList.tsx`): pass `onExpandRun={setModalRunId}` to `<RunCard>` (double-click expand opens the same `RunDetailModal` as single-click; modal is already idempotent on `runId`).

4. **Wire LineageDetailPanel**: add `onExpandNode?: (node: LineageNode) => void` prop; add ⤢ button to `.rv-lineage-detail__header`; guard: only render when `node !== null`.

5. **Wire ClaimLedgerTable**: add `onExpandClaim?: (claimId: string) => void` prop; add `onDoubleClick={() => onExpandClaim?.(claimId)}` to each `<tr>`.

6. **Wire ClaimAuditWorkbench**: hold `detailModalPayload` state; pass `onExpandClaim` down to `ClaimInspector`; render `<DetailModal stacked payload={...} onOpenChange={...} />` when payload is set; update Escape guard to include `detailModalOpen` in addition to `claimModalOpen`.

7. **Write tests** for `DetailModal` and updated components; run `tsc --noEmit` + build.

**Similar existing code:**
- Reference: `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx` — full overlay pattern including Escape handler (`lines 68-75`), `stacked` prop (`line 84`), `onOpenChange` callback (`lines 58-63`), backdrop click guard (`line 87`).
- Reference: `frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx` — parent `claimModalOpen` Escape suppression pattern (`lines 56-63`), stacked `<ProvenanceModal stacked onOpenChange={setClaimModalOpen} />` usage (`lines 150-156`).

**Known gotchas:**
- `LineageDetailPanel` currently only calls `onOpenProvenance(claimId)` for nodes with a `claimId` (see `LineageDetailPanel.tsx:77-98`). The new ⤢ button for non-claim nodes must separately check `node !== null` (the panel already returns early at `line 16-25` when `node === null`).
- `ProvenanceModal` uses a `forwardRef` + imperative handle (`ProvenanceModalHandle`). If `DetailModal` delegates to it internally, the `useRef` and `useImperativeHandle` plumbing must be preserved. Alternatively, `DetailModal` can render its own claim view without re-using `ProvenanceModal` as a sub-component — both approaches are valid; document the choice.
- Double-click on a `<tr>` in `ClaimLedgerTable` requires `onDoubleClick` on the row element. Confirm that `role="grid"` + `<tr>` is compatible with the double-click event in the target browsers (it is; note it anyway).

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: list of all modified/new files with brief reason (new `DetailModal.tsx`; updated `RunCard.tsx`, `RunList.tsx`, `ClaimLedgerTable.tsx`, `ClaimAuditWorkbench.tsx`, `LineageDetailPanel.tsx`, `RunDetailModal.tsx`, plus any test files)
- **Tests run**: what tests were added/updated and results (unit tests for `DetailModal`; component tests for each wired surface)
- **Validation results**: table of all validation commands (tsc, lint, build, runtime smoke) and their results
- **Deviations from contract**: particularly — (a) double-click vs single-click race resolution approach chosen; (b) whether `DetailModal` internally reuses `ProvenanceModal` content or renders its own claim view; (c) whether `onExpandRun` on RunCard opens a new modal or reuses the existing `RunDetailModal`
- **Risks / Limitations**: any stacking depth limits documented; any interaction edge cases deferred
- **Follow-up recommendations**: graph-node double-click (out of scope, worth a future contract); keyboard-shortcut to expand focused item

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (7 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration

**Reviewer**: `task-completion-validator` (mandatory)

**Related Documents:**
- Epic: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Sibling: `docs/project_plans/feature_contracts/harden-polish/nav-titles-lineage-fixes.md` (F1 — soft dependency for title helpers)
- Source intel: epic-brief §1.5 (modal infra), §1.9 (canonical viewer surfaces)
- Pattern reference: `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`
- Pattern reference: `frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx`

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. If you find:

- **Scope ambiguity**: make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: flag in the Completion Report before attempting workarounds.
- **Better implementation path**: document the deviation in the Completion Report with justification.

Stay within scope. The F2 feature is FE-only; do not touch backend, export, or static-data scripts. Do not implement graph-node double-click (out of scope). The reviewer will check for scope drift.
