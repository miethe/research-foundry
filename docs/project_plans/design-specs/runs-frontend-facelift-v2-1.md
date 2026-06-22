---
title: "Design Spec: Runs Frontend Facelift v2.1 Stabilization"
doc_type: design_spec
schema_version: 2
status: completed
maturity: implemented
created: 2026-06-19
updated: 2026-06-21
implemented_by: c3c76dd
feature_slug: runs-frontend-facelift
feature_family: runs-frontend
feature_version: v2.1
category: harden-polish
owner: nick
priority: high
risk_level: medium
related_documents:
  - docs/project_plans/design-specs/runs-frontend-facelift-v2.md
  - docs/project_plans/PRDs/features/runs-frontend-v1.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
  - docs/project_plans/human-briefs/runs-frontend.md
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/dev/architecture/adr-runs-read-path.md
  - docs/project_plans/design-specs/runs-context-panels.md
  - docs/project_plans/design-specs/runs-writeback-preview.md
mockup_assets:
  - docs/project_plans/design-specs/assets/runs-frontend-facelift/portfolio-command-center.png
  - docs/project_plans/design-specs/assets/runs-frontend-facelift/run-detail-trust-cockpit.png
  - docs/project_plans/design-specs/assets/runs-frontend-facelift/claim-audit-workbench.png
---

# Design Spec: Runs Frontend Facelift v2.1 Stabilization

## 1. Intent

The v2 facelift produced a strong operator cockpit, but it still exposes more
interface promises than the implementation fulfills. v2.1 is the stabilization
pass: make navigation honest, replace the portfolio right inspector with a
run-detail modal, repair audit-page claim behavior, expand selected-claim and
lineage detail, and improve report highlighting without changing the static
read path.

This is not a backend rewrite and not a new product direction. The goal is to
finish the interaction contract implied by v2 using the existing
`frontend/runs-viewer/` React/Vite app and the current `RFRunExport` shape.

## 2. Source-Verified Baseline

The following audit was performed against the current code after v2:

| Surface | Current state | Evidence | v2.1 decision |
|---------|---------------|----------|---------------|
| App shell left rail | Buttons exist, but most route to `/runs` and cannot become active. | `frontend/runs-viewer/src/app/AppShell.tsx` | Add capability registry. Wire real surfaces; disable stubs. |
| Portfolio command center | Implemented with health strip, filters, lanes, table, card fallback, and right inspector. | `frontend/runs-viewer/src/screens/RunList.tsx` | Keep portfolio, but replace right inspector with run modal entry point. |
| Detail route | Implemented at `/runs/:runId` with query-state tabs. | `frontend/runs-viewer/src/screens/RunDetail.tsx` | Preserve as expanded view. Extract tab workspace for modal reuse. |
| Trust tab | Implemented via `TrustCockpit`. | `frontend/runs-viewer/src/components/TrustPanel/TrustCockpit.tsx` | Keep wired. |
| Audit tab | Implemented as `ClaimAuditWorkbench`; `?view=audit` normalizes to ledger tab. | `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx` | Keep wired, fix ledger click policy and selected-claim detail. |
| Report tab | Implemented with report renderer, composition filter, and provenance modal. | `frontend/runs-viewer/src/components/ReportOverlay/ReportOverlay.tsx` | Keep wired, add optional text highlighting. |
| Lineage tab | Implemented as a static SVG artifact DAG with capped source display. | `frontend/runs-viewer/src/components/LineageGraph/LineageGraph.tsx` | Replace or augment with expandable lineage explorer. |
| Writeback tab | Implemented mostly as graceful absent-state text. | `frontend/runs-viewer/src/screens/RunDetail.tsx` | Disable when no `run.writebacks`; enable when exported. |
| Claim provenance modal | Implemented for claim details and source cards. | `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx` | Keep; make it stack cleanly over run modal. |
| Source cards | Rich, clickable cards exist in modal only. | `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx` | Reuse in selected-claim inspector. |

## 3. Scope

In scope:

- Make app shell navigation reflect implemented surfaces.
- Replace portfolio right sidebar inspection with a run-detail modal.
- Preserve `/runs/:runId` as the expanded detail page.
- Share detail tab composition between the modal and full page.
- Keep claim provenance modal behavior on report/tab surfaces where it already
  works, including modal-over-modal support from the run modal.
- On the audit page, ledger row clicks select only; the explicit Selected Claim
  "Open modal" button remains the modal entry point.
- Expand Selected Claim to show materiality, type, status, confidence,
  source cards, inference/speculation basis, report locations, warning states,
  and linked actions.
- Replace the Lineage tab's static summary with an expandable source,
  extraction, claim, report, and writeback tree.
- Derive human-readable titles for runs, sources, claims, lineage nodes, and
  modal headers while keeping IDs as sublabels, links, and citations.
- Add report text highlighting for composition filters and selected claims.

Out of scope for v2.1:

- Persisted saved views.
- New backend mutation APIs.
- Full writeback authoring or approval workflows.
- Schema version bump solely for display titles. Client-side title derivation
  should ship first; optional exported `display_title` fields can be planned
  later.
- Replacing the whole app shell with `@miethe/ui`.

## 4. Navigation Contract

The current left rail creates false affordances because every item points to
`/runs`. v2.1 introduces a single navigation capability registry:

```ts
type NavCapability = {
  label: string;
  short: string;
  state: "enabled" | "contextual" | "disabled";
  resolveTarget?: (ctx: ShellNavContext) => string | null;
  disabledReason?: string;
};
```

Initial state:

| Rail item | v2.1 behavior |
|-----------|---------------|
| Portfolio | Enabled. Navigates to `/runs`. |
| Runs | Enabled. Navigates to `/runs`; active for `/runs/:runId`. |
| Reports | Contextual. If current run id is known, navigate to `/runs/:runId?view=report`; otherwise disabled with "Select a run first." |
| Ledger | Contextual. If current run id is known, navigate to `/runs/:runId?view=audit`; otherwise disabled with "Select a run first." |
| Library | Disabled. No implemented route. |
| Swarm | Disabled. No implemented route. |
| Policies | Disabled. No implemented route. |
| Alerts | Disabled. No implemented route. |
| Settings | Disabled. No implemented route. |
| Help | Disabled until a help panel or route exists. |

Portfolio local controls also need honesty:

- "High Claim Volume" should either filter to high-claim runs or be relabeled
  "Sort by claim volume." Prefer filtering because the count already implies a
  view.
- "This Week" should either filter by date or be disabled. Prefer disabling
  unless a stable created-at window exists in fixtures.
- Writeback tab/buttons should be disabled when `run.writebacks` is absent or
  empty, while still showing graceful absent states in the expanded page when
  directly deep-linked.

## 5. Run Detail Modal

Clicking a run from the portfolio should open a modal, not push the user
straight to the detail page. The right sidebar is too narrow for useful run
details, and it duplicates a small subset of the detail route.

### Modal Shape

Create `RunDetailModal` under `frontend/runs-viewer/src/components/RunDetail/`
or a similar local folder.

Required structure:

- Header:
  - human-readable run title
  - `run_id` as monospace sublabel
  - derived status, sensitivity, verification, and governance chips
  - "Open full page" action pointing to `/runs/:runId?view=<activeTab>`
- Summary strip:
  - created date
  - claim totals
  - failed checks
  - redacted/dangling source counts
  - top attention state
- Tabs:
  - Overview
  - Trust
  - Audit
  - Report
  - Lineage
  - Writeback, disabled unless exported

The modal should use the same data source as the page: `useRunDetail(openRunId)`.
Do not add a second API contract.

### Shared Workspace Extraction

Extract the tab composition from `RunDetailScreen` into a shared component:

```ts
type RunDetailWorkspaceProps = {
  run: RFRunExport;
  activeTab: DetailTab;
  selectedClaimId?: string | null;
  mode: "page" | "modal";
  onTabChange: (tab: DetailTab, claimId?: string | null) => void;
  onOpenProvenance?: (claimId: string) => void;
};
```

The full page remains responsible for URL state. The modal owns local state,
but "Open full page" preserves the active tab and selected claim when present.

### Stacked Claim Modal

When viewing the Report or Audit tab inside the run modal, clicking a claim
from report content outside the audit page should still open the claim modal.
The claim modal must appear above the run modal with an unambiguous stacking
order and Escape behavior:

- First Escape closes the claim modal.
- Second Escape closes the run modal.
- Overlay click on the claim modal closes only the claim modal.
- Overlay click on the run modal closes only when no claim modal is open.

Implementation options:

1. Keep the current app-local modal styles and add a `z-index` layer for nested
   provenance.
2. Adopt `@miethe/ui` `Dialog` or `BaseArtifactModal` semantics only after
   confirming Radix/Tailwind dependency impact. The local SkillMeat package has
   useful primitives, but `runs-viewer` currently does not depend on Radix or
   Tailwind.

Recommended v2.1 path: port behavior locally first. Re-evaluate `@miethe/ui`
after the modal contract is stable.

## 6. Audit Page Claim Policy

The audit page is a workbench, so clicking a ledger row should not open a modal.
It should select the claim, update URL state, and update the Selected Claim
panel. The modal remains available through the explicit "Open modal" button.

Click policy:

| Context | Claim click behavior |
|---------|----------------------|
| Full Report tab | Open claim modal. |
| Report tab inside run modal | Open claim modal stacked over run modal. |
| Audit page ledger row | Select claim only; update `?claim=`. |
| Audit page embedded report chip | Select claim only; update `?claim=`. |
| Selected Claim chain link | Select linked claim. |
| Selected Claim "Open modal" | Open claim modal. |
| Lineage explorer claim node outside audit workbench | Select node and optionally open claim modal via explicit action. |

Implementation touchpoints:

- `ClaimAuditWorkbench.selectClaim`
- `ClaimLedgerTable.onClaimSelect`
- `ReportRenderer.onClaimSelect`
- `ReportOverlay.handleClaimSelect`
- `RunDetailWorkspace.onOpenProvenance`

Add a prop to make the intent explicit:

```ts
type ClaimClickMode = "select" | "open-modal";
```

Default audit workbench mode should be `"select"`. Report overlay mode should
be `"open-modal"`.

## 7. Selected Claim Inspector

The Selected Claim section should become the authoritative in-page view for the
claim. It should not be a thin preview that forces the modal for basic data.

### Required Data

Show available claim fields:

- human-readable claim title, derived from the claim text
- `claim_id`
- materiality
- claim type
- status
- confidence
- source count
- report locations
- inference/speculation basis
- warnings for redaction, dangling source, empty inference basis, mixed, and
  contradicted states

Confidence display:

| Confidence | Temporary score | Indicator |
|------------|-----------------|-----------|
| high | 92 percent | green ring |
| medium | 74 percent | amber ring |
| low | 45 percent | red ring |
| absent | unknown | neutral ring |

If a future export provides numeric confidence, prefer numeric thresholds:
green at `>= 0.8`, amber at `>= 0.6`, red below `0.6`.

### Source Cards

Replace the primary-source-only `SourceSummary` with a reusable source list:

- Render each `claim.sources[]` entry.
- Use the existing `SourceCard` component or an extracted compact variant.
- Source titles should be clickable when `source.url` exists.
- Source rows should expose quote, summary, locator, trust, usage, redaction,
  and dangling state.
- Keep redaction fail-closed: do not reveal hidden text above threshold.

### Basis Flow

Create a reusable `ClaimBasisFlow` component for inference and speculation.

For inference:

- Render `from_claims` as a flow of linked claim chips.
- Hover/focus on a linked claim shows a small details tooltip: claim text,
  status, confidence, and source count.
- Clicking a linked claim selects that claim in audit mode.
- The reasoning summary is shown as supporting context, not as a blob before
  or after the flow.
- If `from_claims` exists but `reasoning_summary` is absent, still show the
  flow.
- If `from_claims` is empty, show the existing RIB-018 warning state.

For speculation:

- Render a "Speculation Basis" section when claim type or status is
  speculation.
- If no structured basis exists, show "No structured basis exported" with a
  link to open the provenance modal.
- If future exports add basis data, the same `ClaimBasisFlow` should support it.

## 8. Lineage Explorer

The current static SVG is useful as a quick visual summary, but it hides the
details the user needs for audit work. v2.1 should introduce an expandable
Lineage Explorer that starts with sources and can expand down to individual
claims and report locations.

### Target Hierarchy

Default grouping:

```text
Run
  Source Card
    Extraction / evidence point
      Claim
        Report location
        Writeback target
```

Alternate view:

```text
Run
  Claim
    Source Card
      Extraction / evidence point
    Report location
    Writeback target
```

The first grouping should be default because the user specifically asked to
start with the current per-source breakdown and expand to individual claims.

### Interaction Model

Use the IntentTree recursive row pattern:

- `expanded: Set<string>` state.
- `Expand all` and `Collapse all` controls.
- Row-level chevron with `aria-expanded`.
- Title-first row, ID sublabel, status/type/confidence chips, and an explicit
  open action.
- Hover/focus tooltip for dense metadata.
- Detail modal or side panel for node payloads that are too large for a row.

The implementation may remain a local `rv-*` component. Do not import
IntentTree code directly.

### Node Details

Lineage nodes should expose:

- Source: display title, source card id, URL, source type, rank, sensitivity,
  usage constraints, known limitations, and reliability notes.
- Extraction: evidence id, locator, quote/summary with redaction behavior,
  relation to claim, dangling/resolved state.
- Claim: display title, claim id, type, status, materiality, confidence, source
  count, report locations, and warnings.
- Report location: file, heading, paragraph id, linked claim chip.
- Writeback: target name, destination, status, URL, required fix.

Keep the pure data adapter separate from rendering:

```ts
buildLineageTree(run: RFRunExport): LineageNode[]
```

This makes the tree testable without a browser.

## 9. Human-Readable Titles

IDs remain the canonical links and citation targets, but display surfaces should
lead with meaningful titles.

Add title derivation helpers under `frontend/runs-viewer/src/lib/runs.ts` or a
new `frontend/runs-viewer/src/lib/displayTitles.ts`.

Rules:

| Entity | Title source order | ID treatment |
|--------|--------------------|--------------|
| Run | first report H1, research brief heading, intent id slug, run id slug | Show `run_id` beneath title and in tooltip. |
| Source | `source.title`, URL hostname/path, `source_card_id` | Show source card id beneath title. |
| Claim | first 96 characters of claim text, trimmed at word boundary | Show claim id as chip/sublabel. |
| Extraction | evidence locator, evidence id, source title | Show evidence id beneath title. |
| Report | report H1, first heading, "Draft report" | Show file/heading metadata beneath title. |
| Writeback target | target name, destination, URL hostname | Show destination/status beneath title. |

No schema change is required for v2.1. If derived titles become unreliable, add
a later export-schema proposal for optional `display_title` fields.

## 10. Report Highlighting

The current report composition sidebar dims nonmatching claim chips. v2.1 adds
optional attributed-text highlighting.

### Composition Highlighting

When the user clicks a composition box:

- Preserve the existing chip filter.
- Add a toggle: "Highlight attributed text."
- When enabled, highlight paragraphs or list items containing matching claim
  chips using the same color family as the composition box.
- Apply transparency to nonmatching report text and claim chips.
- Reset restores normal report rendering.

Because the export does not provide character offsets, v2.1 should highlight
the smallest Markdown block containing a claim chip. Do not claim exact
character attribution until the export includes offsets or spans.

### Audit Selection Highlighting

When a claim is selected in audit mode:

- Highlight the selected claim chip and its containing report text block.
- Dim nonselected report text and nonselected claim chips.
- Keep the Selected Claim panel in sync.
- Optionally scroll the selected chip into view when selected from the ledger.

ReportRenderer should accept explicit highlight props:

```ts
type ReportHighlightMode = "none" | "composition" | "selected-claim";

type ReportRendererProps = {
  selectedClaimId?: string | null;
  activeClaimIds?: Set<string> | null;
  highlightMode?: ReportHighlightMode;
  highlightText?: boolean;
};
```

## 11. Phased Execution Plan

| Phase | Name | Goal | Primary files | Assigned subagents | Model | Effort |
|-------|------|------|---------------|--------------------|-------|--------|
| 1 | Navigation Honesty | Disable stubs and wire real surfaces. | `AppShell.tsx`, `RunList.tsx`, shell CSS | ui-engineer-enhanced | sonnet | adaptive |
| 2 | Run Modal Shell | Add run modal and shared detail workspace. | `RunList.tsx`, `RunDetail.tsx`, new `RunDetail/` components | ui-engineer-enhanced | sonnet | extended |
| 3 | Audit Interaction Repair | Fix audit click policy and expand Selected Claim. | `ClaimAuditWorkbench.tsx`, `ClaimLedgerTable.tsx`, `SourceCard.tsx` | ui-engineer-enhanced | sonnet | extended |
| 4 | Lineage Explorer | Replace static-only lineage with expandable tree. | `LineageGraph.tsx`, new lineage adapter/component tests | frontend-architect, ui-engineer-enhanced | sonnet | extended |
| 5 | Titles and Report Highlighting | Add display title helpers and text highlight modes. | `lib/runs.ts` or `lib/displayTitles.ts`, `ReportRenderer.tsx`, `CompositionSidebar.tsx`, CSS | frontend-developer | sonnet | adaptive |
| 6 | Verification | Update unit, E2E, accessibility, and visual smoke coverage. | `src/test/*`, `e2e/*`, screenshots | task-completion-validator | sonnet | adaptive |

Critical path:

1. Phase 1 first, because shell navigation affects every subsequent smoke test.
2. Phase 2 before Phase 3 if audit components must render inside the modal.
3. Phase 3 before Phase 4, because lineage claim-node behavior depends on the
   selected-claim contract.
4. Phase 5 can run after Phase 3 starts, but must merge before verification.

Parallel opportunities:

- Display-title helper work can run while modal extraction is underway.
- Lineage adapter tests can be written before final lineage styling.
- Playwright updates can begin once modal selectors and tab names are stable.

## 12. Acceptance Criteria

### AC-V21-1: Shell navigation is honest

- target_surfaces:
  - frontend/runs-viewer/src/app/AppShell.tsx
  - frontend/runs-viewer/src/screens/RunList.tsx
  - frontend/runs-viewer/src/styles/runs-viewer.css
- propagation_contract: the shell reads route context and selected-run context,
  computes each navigation capability, and renders enabled/contextual/disabled
  states consistently.
- resilience: disabled items have `disabled`, `aria-disabled`, and a reason in
  `title` or accessible text; contextual report/ledger links do not navigate
  without a run id.
- visual_evidence_required: desktop screenshot showing disabled stub rail items
  and enabled portfolio/runs items.
- verified_by:
  - new shell navigation component test
  - portfolio Playwright smoke

### AC-V21-2: Run clicks open a useful modal

- target_surfaces:
  - frontend/runs-viewer/src/screens/RunList.tsx
  - frontend/runs-viewer/src/screens/RunDetail.tsx
  - frontend/runs-viewer/src/components/RunDetail/
  - frontend/runs-viewer/src/components/ReportOverlay/
  - frontend/runs-viewer/src/components/ClaimLedger/
- propagation_contract: selecting a run loads one `RFRunExport`; the modal and
  expanded page share tab content through `RunDetailWorkspace`.
- resilience: modal loading, error, and absent optional run data states render
  without throwing; "Open full page" preserves tab and selected claim.
- visual_evidence_required: desktop screenshot of portfolio with run modal open
  on Report tab and stacked claim modal open.
- verified_by:
  - modal component tests
  - new Playwright run-modal smoke

### AC-V21-3: Audit claim clicks select only

- target_surfaces:
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
  - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
  - frontend/runs-viewer/e2e/runs-facelift-v2.spec.ts
- propagation_contract: audit ledger rows and embedded audit report chips call
  selection handlers; report overlay chips outside audit call provenance modal
  handlers.
- resilience: keyboard Enter/Space on ledger rows follows the same select-only
  behavior on the audit page.
- visual_evidence_required: false
- verified_by:
  - updated "ledger row selection updates copied URL state" E2E asserting no
    provenance modal appears
  - existing W3 report-chip modal E2E

### AC-V21-4: Selected Claim shows full available data

- target_surfaces:
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
  - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
  - frontend/runs-viewer/src/types/rf/run-export.ts
- propagation_contract: the selected `RFClaim` drives metadata, confidence,
  basis flow, source cards, report locations, and warning states from the same
  object passed to the modal.
- resilience: multi-source, zero-source, dangling-source, redacted-source,
  inference-without-summary, inference-without-basis, and speculation claims
  render explicit states.
- visual_evidence_required: desktop screenshot showing selected claim with
  multiple source cards and basis flow.
- verified_by:
  - component tests for multi-source and inference-basis variants
  - W1 claim audit E2E

### AC-V21-5: Lineage explorer exposes expandable details

- target_surfaces:
  - frontend/runs-viewer/src/components/LineageGraph/LineageGraph.tsx
  - frontend/runs-viewer/src/components/LineageGraph/
  - frontend/runs-viewer/src/lib/runs.ts
- propagation_contract: `buildLineageTree(run)` maps sources, extraction
  evidence, claims, report locations, and writebacks into a renderable tree;
  expand/collapse state controls which detail rows render.
- resilience: runs with no claims, capped source counts, dangling sources,
  missing report locations, and absent writebacks render without hiding known
  lineage data.
- visual_evidence_required: desktop screenshot with one source expanded to
  extraction and claim rows.
- verified_by:
  - adapter unit tests
  - lineage component tests
  - Playwright smoke for expand/collapse

### AC-V21-6: Report highlighting matches claim data

- target_surfaces:
  - frontend/runs-viewer/src/components/ReportOverlay/ReportRenderer.tsx
  - frontend/runs-viewer/src/components/ReportOverlay/CompositionSidebar.tsx
  - frontend/runs-viewer/src/components/ReportOverlay/ClaimChip.tsx
  - frontend/runs-viewer/src/styles/runs-viewer.css
- propagation_contract: composition filters and selected claim state provide
  active claim ids and highlight mode to `ReportRenderer`; renderer marks
  claim chips and containing Markdown blocks.
- resilience: reports with missing claims, missing chips, duplicate claim
  chips, and absent report text keep the current empty/missing states.
- visual_evidence_required: desktop screenshot with inference composition text
  highlighted and nonmatching report text dimmed.
- verified_by:
  - ReportRenderer unit tests
  - updated report-chip Playwright smoke

## 13. Test Plan

Unit and component tests:

- `displayTitles` helper tests for run, source, claim, extraction, report, and
  writeback fallbacks.
- `buildLineageTree` tests for source-first grouping, multi-source claims,
  dangling source refs, absent report locations, and writeback targets.
- `ClaimAuditWorkbench` tests for ledger select-only behavior and selected
  claim metadata.
- `ReportRenderer` tests for selected-claim and composition highlight modes.
- Modal tests for open, close, stacked close order, active tab, and full-page
  action target.

Playwright:

- Portfolio shell nav: disabled stubs do not navigate.
- Portfolio run modal: table/card run click opens modal; full-page button
  navigates with active view.
- Report-in-modal: claim chip opens stacked claim modal.
- Audit page: ledger click selects and updates URL without opening modal.
- Audit page: explicit Selected Claim "Open modal" opens provenance modal.
- Lineage page: expand a source, then expand a claim.
- Report page: composition highlight toggle dims nonmatching report text.

Visual smoke:

- Portfolio with disabled nav states.
- Run modal desktop.
- Audit selected-claim inspector with basis flow.
- Lineage explorer expanded source.
- Report composition highlighting.

## 14. Open Questions

| ID | Question | Proposed resolution |
|----|----------|---------------------|
| OQ-V21-1 | Should global shell Reports/Ledger use selected portfolio run state on `/runs`? | Yes if selected run id is promoted to shell context; otherwise keep disabled until on `/runs/:runId`. |
| OQ-V21-2 | Should the run modal use `@miethe/ui` immediately? | No. Port the interaction behavior locally first; adopt package primitives only after dependency/style review. |
| OQ-V21-3 | Should Lineage use `@xyflow/react`? | Not for v2.1 default. Start with expandable tree; consider graph mode after the tree proves useful. |
| OQ-V21-4 | Can report highlighting be exact text attribution? | Not with current export data. Use Markdown block attribution until claim spans/offsets exist. |
| OQ-V21-5 | Should display titles be exported by backend? | Defer. Client-side derivation is enough for v2.1 and avoids schema churn. |

## 15. Implementation Notes

- Preserve static export as the default read path.
- Preserve redaction fail-closed behavior.
- Preserve `?view=audit&claim=<id>` deep links.
- Keep existing test ids where possible; add new test ids for modal, lineage,
  and highlight controls.
- Do not let disabled shell items silently navigate to `/runs`.
- Avoid nested card layouts in the new modal and lineage surfaces.
- Keep text sizing compact inside modal tabs; the modal is an operational tool,
  not a marketing hero.

No new bitmap mockups are required for v2.1. The existing v2 mockups remain
directional references; v2.1 is primarily an interaction and information
architecture correction.
