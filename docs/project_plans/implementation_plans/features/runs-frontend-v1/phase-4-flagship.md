---
schema_version: 2
doc_type: phase_plan
title: "Phase 4: Flagship — Claim Ledger + Report Overlay"
status: draft
created: 2026-06-19
updated: 2026-06-19
phase: 4
phase_title: "Flagship — Claim Ledger + Report Overlay"
feature_slug: runs-frontend
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
entry_criteria:
  - Phase 3 complete (run list + trust panel render from fixture; seam task passed; Vitest green)
  - OQ-5 decision recorded (component vocabulary settled)
integration_owner: ui-engineer-enhanced
exit_criteria:
  - Claim ledger renders all clm_NNN entries with facets
  - Provenance drill-down modal resolves in ≤ 2 clicks from fixture
  - Inference claim modal shows from_claims chain; empty from_claims flagged as warning
  - Source card sensitivity gate: work_sensitive body content absent from rendered output
  - Report overlay renders Markdown with working claim chips
  - Composition sidebar renders
  - Seam task P4-SEAM-001 passes
  - Vitest green for drill-down/inference/sensitivity
  - task-completion-validator P4 phase review passed
---

# Phase 4: Flagship — Claim Ledger + Report Overlay

**Parent Plan**: [runs-frontend-v1.md](../runs-frontend-v1.md)
**Duration**: ~3–4 days
**Primary Subagent**: `ui-engineer-enhanced` (claim ledger + provenance modal) | Model: `sonnet` | Effort: `extended`
**Parallel Subagent**: `frontend-developer` (report overlay + lineage graph) | Model: `sonnet` | Effort: `adaptive`
**Integration Owner**: `ui-engineer-enhanced`

---

## Phase Overview

Phase 4 is the product's highest-value and highest-novelty phase. It delivers the two-click claim audit (W1 flagship) via a claim ledger table and provenance drill-down modal, plus the report overlay with live `[claim:clm_NNN]` chips that open the modal. The claim-graph join is pre-computed in the P1 export service; Phase 4 only needs to resolve UI presentation logic. The H3 algorithmic flag fires again for the inference-chain walkability (the RIB-018 false-pass class) and the sensitivity-gate rendering in the source card terminus.

**R-P3 (two FE owners)**: `ui-engineer-enhanced` owns `ClaimLedgerView`, `ProvenanceModal`, and the shared `[claim:clm_NNN]` modal trigger interface. `frontend-developer` owns `ReportOverlay` and `LineageGraph`. The seam is the `[claim:clm_NNN]` chip → `ProvenanceModal.open(claimId)` call contract. Seam task P4-SEAM-001 verifies this contract and the sensitivity-gate boundary.

---

## Task Table — Claim Ledger Sub-Track (ui-engineer-enhanced)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-LEDGER-TABLE | Claim ledger table | Implement `frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx`. Tabular display of all `clm_NNN` entries from `useClaimLedger()`. Columns: claim ID (anchor `id="clm_NNN"` for deep-link from P3), claim text (truncated), status badge (supported/inference/speculation), confidence badge, materiality badge. Clicking a row opens `ProvenanceModal`. | Table renders all claims from fixture with correct badges; row click triggers `onClaimSelect(claimId)` callback; each row has `id="clm_NNN"` anchor; no `any` in props | 0.5 pts | ui-engineer-enhanced | sonnet | extended | P2-HOOKS |
| P4-LEDGER-FACETS | Claim ledger facets | Implement `frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx`. Facets: status (supported/inference/speculation), materiality, claim_type, confidence range. Each facet updates the visible set of claims in `ClaimLedgerTable`. | Facets filter correctly for each dimension; multi-facet selection is additive (AND logic); selecting no facets shows all claims | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | P4-LEDGER-TABLE |
| P4-SOURCE-CARD | Source card component | Implement `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx`. Renders: trust badge, source-type icon, usage-permission pills, expandable section showing verbatim quote + locator. Sensitivity gate: if `sensitivity` of the source card or `extracted_points[].sensitivity` is above the configured threshold, render a redaction placeholder ("Content redacted — sensitivity: work_sensitive") instead of the quote. Component vocabulary: `@miethe/ui` card (per OQ-5 decision). | Source card renders trust badge, source-type icon, usage pills; expandable quote section shows verbatim quote for `public` content; `work_sensitive` quote rendered as redaction placeholder (not the quote text); redaction confirmed by synthetic fixture test | 0.75 pts | ui-engineer-enhanced | sonnet | extended | P2-TS-CODEGEN |

#### AC P4-SOURCE-CARD-1: Sensitivity Gate in Source Card (R9 high-severity, FR-9)
- target_surfaces:
    - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
- propagation_contract: SourceCard receives pre-filtered source data from ProvenanceModal (which reads from the export JSON; sensitive content already absent at the JSON level per P1-SENS-001); SourceCard additionally checks `sensitivity` field as defense-in-depth and renders redaction placeholder if `work_sensitive` or `client_sensitive`
- resilience: If `sensitivity` field absent, treat as `public` (safe default — renders the quote)
- visual_evidence_required: false
- verified_by: [P4-SENS-001, P4-SEAM-001]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-MODAL | Provenance drill-down modal | Implement `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`. Opens when `onClaimSelect(claimId)` called. For the selected claim: renders claim text + status; resolves `sources[]` from the export JSON's claim record (pre-joined in P1); renders one `SourceCard` per source. For inference claims (`status: inference`): renders `from_claims` linked chain instead of source cards; empty `from_claims` (RIB-018 class) renders a visible warning ("No basis claims — inference unsupported"). Component vocabulary: `@miethe/ui` modal (per OQ-5 decision). | Modal opens for any claim in the fixture; source cards render for supported claims; inference modal shows `from_claims` chain for a claim with non-empty `from_claims`; empty `from_claims` renders "inference unsupported" warning; ≤ 2 UI interactions from claim ledger row click to verbatim quote visible | 1.5 pts | ui-engineer-enhanced | sonnet | extended | P4-LEDGER-TABLE, P4-SOURCE-CARD |

#### AC P4-MODAL-1: Two-Click Claim Audit (W1 Flagship, FR-5 + FR-6)
- target_surfaces:
    - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
- propagation_contract: Click 1 = row click on ClaimLedgerTable (or chip click in ReportOverlay) → ProvenanceModal.open(claimId); Click 2 = expand source card → verbatim quote visible; provenance join data pre-computed in export JSON (no additional fetch)
- resilience: If claim has zero sources (supported claim with missing source data), renders "Source data unavailable" placeholder; never crashes
- visual_evidence_required: false
- verified_by: [P4-MODAL, P5-E2E-W1]

#### AC P4-MODAL-2: RIB-018 Class Flagging (FR-6)
- target_surfaces:
    - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
- propagation_contract: When `status: inference` and `from_claims: []` (empty array), modal renders a visible warning in the inference basis section
- resilience: Empty `from_claims` renders warning, not error; populated `from_claims` renders a linked chain
- visual_evidence_required: false
- verified_by: [P4-VITEST-INFERENCE, P5-E2E-W1]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-SENS-001 | Source card sensitivity test in UI | UI-level sensitivity test: using the synthetic sensitivity fixture from P1-SENS-001 (with a `work_sensitive` source card), verify that `SourceCard` renders the redaction placeholder (not the quote text) when the fixture's `extracted_points[].quote` is absent from the JSON (redacted by P1 export service) AND when the `sensitivity` field is `work_sensitive`. | Vitest test confirms: (a) `work_sensitive` source card quote content does not appear in rendered output; (b) redaction placeholder renders; (c) `public` source card quote does appear | 0.25 pts | ui-engineer-enhanced | sonnet | extended | P4-SOURCE-CARD |

---

## Task Table — Report Overlay Sub-Track (frontend-developer)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-REPORT-MD | Report Markdown renderer | Implement `frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx`. Renders `report_draft.md` as Markdown (using `react-markdown` or equivalent). Transforms `[claim:clm_NNN]` patterns into interactive chip components that call `onClaimSelect(claimId)`. `**Inference:**` and `**Speculation:**` sentences: apply color-coded CSS class (amber for Inference, gray/strikethrough for Speculation) based on claim status from the claim ledger data. | Markdown renders correctly; `[claim:clm_NNN]` patterns render as clickable chips (not raw text); chip click fires `onClaimSelect("clm_NNN")`; at least one Inference sentence is color-coded in fixture | 0.75 pts | frontend-developer | sonnet | adaptive | P2-HOOKS |

#### AC P4-REPORT-001-1: Report Claim Chips (FR-7, R-P1)
FR-7 says "inline [claim:clm_NNN] citations" — explicit `target_surfaces:` required:
- target_surfaces:
    - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ClaimChip.tsx
- propagation_contract: ReportRenderer parses `[claim:clm_NNN]` patterns with regex; each match renders as `<ClaimChip claimId="clm_NNN" onClick={onClaimSelect} />`; clicking any chip fires onClaimSelect which is wired in ReportOverlay to open ProvenanceModal
- resilience: `[claim:clm_NNN]` for a claim ID not present in the ledger renders as a disabled chip with "Claim not found" tooltip; never crashes
- visual_evidence_required: false
- verified_by: [P4-SEAM-001, P5-E2E-W3]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-REPORT-SIDEBAR | Composition sidebar | Implement `frontend/runs-viewer/src/components/ReportOverlay/CompositionSidebar.tsx`. Shows: % supported / % inference / % speculation claim counts (from `evidence_bundle.counts`). Click on a category filters the claim chips in the report to show only matching-status claims highlighted (non-matching chips dimmed). | Sidebar shows correct % counts from fixture; clicking "Inference" dims all non-inference chips; clicking again resets | 0.25 pts | frontend-developer | sonnet | adaptive | P4-REPORT-MD |
| P4-REPORT-OVERLAY | Report overlay composite | Implement `frontend/runs-viewer/src/components/ReportOverlay/ReportOverlay.tsx`. Composes `ReportRenderer` + `CompositionSidebar` into a two-column layout. Wires `onClaimSelect` from `ReportRenderer` to `ProvenanceModal.open()`. Run tab navigation: the run detail view tabs between TrustPanel and ReportOverlay. | Report overlay renders in a run detail tab; claim chip click opens ProvenanceModal with correct claim; composition sidebar renders alongside report | 0.25 pts | frontend-developer | sonnet | adaptive | P4-REPORT-SIDEBAR |
| P4-LINEAGE | Lineage graph panel (should-have) | Adapt `ArtifactLineageGraph` from MeatyWiki Portal (`src/components/workflow/viewer/artifact-lineage-graph.tsx`). Render SVG DAG showing: source_card → extraction_card → claim_ledger_entry → evidence_bundle → report provenance chain, with verdict badge decorations. Graceful empty-state when lineage data absent. | SVG DAG renders correct node types and edges for a representative run from fixture; verdict badges present on evidence_bundle and report nodes; graceful "No lineage data" empty-state when absent; no SVG render errors | 0.75 pts | frontend-developer | sonnet | adaptive | P2-TS-CODEGEN |

---

## Task Table — Seam + Vitest (ui-engineer-enhanced)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P4-SEAM-001 | Seam task: report-chip → modal open contract + sensitivity-gate boundary | Verify two integration contracts: (1) `ReportRenderer` chip click → `ProvenanceModal.open(claimId)` contract: simulate chip click in `ReportOverlay`, assert ProvenanceModal opens with the correct claim data; (2) Sensitivity-gate boundary: for a `work_sensitive` source card in the modal, assert that the `SourceCard` renders a redaction placeholder (not quote text) — even when the parent `ReportOverlay` has no knowledge of the sensitivity. | Seam test 1 passes: chip click in ReportOverlay triggers ProvenanceModal open with correct claimId; Seam test 2 passes: work_sensitive source card in modal shows redaction placeholder; both tests use fixture data | 0.25 pts | ui-engineer-enhanced | sonnet | extended | P4-REPORT-OVERLAY, P4-MODAL, P4-SENS-001 |
| P4-VITEST-INFERENCE | Inference chain Vitest test | Unit test: render ProvenanceModal with a fixture claim of `status: inference` and non-empty `from_claims: ["clm_010", "clm_022"]`. Assert linked chain renders. Render with empty `from_claims: []`. Assert "inference unsupported" warning renders. | Both assertions pass | 0.25 pts | ui-engineer-enhanced | sonnet | extended | P4-MODAL |
| P4-VITEST | Phase 4 Vitest suite | Full Vitest suite for P4: claim ledger render, facet filter logic, provenance modal open/close, inference chain render, RIB-018 empty-basis warning, source card sensitivity redaction, report chip click triggers modal, composition sidebar filter. | All Vitest tests green in CI | 0.5 pts | ui-engineer-enhanced | sonnet | extended | P4-SEAM-001, P4-VITEST-INFERENCE |

---

## Phase 4 Parallel Execution

```
Phase 3 complete
      │
      ├── ui-engineer-enhanced track:
      │     P4-LEDGER-TABLE → P4-LEDGER-FACETS
      │     P4-SOURCE-CARD → P4-MODAL → P4-SENS-001
      │
      └── frontend-developer track (parallel):
            P4-REPORT-MD → P4-REPORT-SIDEBAR → P4-REPORT-OVERLAY
            P4-LINEAGE (independent; should-have)
      │
      P4-SEAM-001 (after both tracks; owned by ui-engineer-enhanced)
      P4-VITEST-INFERENCE (after P4-MODAL)
      P4-VITEST (after seam + inference)
```

---

## Key Files Affected

- `frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx` (new)
- `frontend/runs-viewer/src/components/ClaimLedger/LedgerFacets.tsx` (new)
- `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx` (new — integration_owner file)
- `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx` (new)
- `frontend/runs-viewer/src/components/ReportOverlay/ReportOverlay.tsx` (new)
- `frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx` (new)
- `frontend/runs-viewer/src/components/ReportOverlay/ClaimChip.tsx` (new)
- `frontend/runs-viewer/src/components/ReportOverlay/CompositionSidebar.tsx` (new)
- `frontend/runs-viewer/src/components/LineageGraph/LineageGraph.tsx` (new — adapted from MeatyWiki ArtifactLineageGraph)
- `frontend/runs-viewer/src/screens/RunDetailScreen.tsx` (updated — adds report overlay tab)
