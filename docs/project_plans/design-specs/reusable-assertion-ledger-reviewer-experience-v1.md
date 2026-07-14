---
schema_version: 2
doc_type: design_spec
title: "Reusable Assertion Ledger Reviewer Experience v1"
status: draft
maturity: shaping
created: 2026-07-14
updated: 2026-07-14
feature_slug: reusable-assertion-ledger
feature_family: runs-viewer
feature_version: v1
category: features
owner: nick
priority: high
risk_level: high
source_basis: "P7 reviewer-experience requirements, code-truth UI inspection, existing runtime screenshots, current design tokens, and conceptual imagegen mockups"
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-7-reviewer-experience.md
mockup_assets:
  - docs/project_plans/design-specs/assets/reusable-assertion-ledger-reviewer-experience/mockup-full-packet-catalog.png
  - docs/project_plans/design-specs/assets/reusable-assertion-ledger-reviewer-experience/mockup-legacy-missing-provenance.png
  - docs/project_plans/design-specs/assets/reusable-assertion-ledger-reviewer-experience/mockup-denied-catalog.png
  - docs/project_plans/design-specs/assets/reusable-assertion-ledger-reviewer-experience/mockup-stale-impact-workbench.png
  - docs/project_plans/design-specs/assets/reusable-assertion-ledger-reviewer-experience/mockup-assertion-only-lineage.png
reference_screenshots:
  - docs/project_plans/design-specs/assets/public-multiuser-release/current-audit.png
  - docs/project_plans/design-specs/assets/public-multiuser-release/mockup-evidence-catalog.png
related_documents:
  - docs/project_plans/design-specs/runs-frontend-facelift-v2-1.md
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-5-catalog-search-api.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-6-reuse-refresh-impact.md
  - docs/dev/architecture/rf-run-export-schema.md
---

# Reusable Assertion Ledger Reviewer Experience v1

## 1. Decision and intent

P7 extends the existing Runs Viewer into an evidence-packet review experience;
it does not create a second reviewer application. The Catalog, Claim Audit,
Provenance, Lineage, and Run Detail surfaces remain the product frame. The
design must let a reviewer answer five questions without semantic laundering:

1. What exactly does this source assertion say?
2. Which immutable edition and exact passage support it?
3. Is reuse allowed, denied, stale, or unavailable, and why?
4. Which reports, runs, inferences, and derived records are affected?
5. Is this an assertion-only deployment, or are optional canonical-claim
   relationships actually enabled?

The feature is private, workspace-scoped, lexical-first, and read/review
oriented. It must not imply vector search, shared graph search, automatic truth
adjudication, public promotion, or an enabled canonical-merge capability.

## 2. Mockups are planning inputs, not validation evidence

The five `mockup-*.png` assets in this spec are **conceptual target images**.
They establish hierarchy, density, state communication, labels, and interaction
intent. They may contain synthetic fixture values and do not prove that a
component, API, state, or accessibility behavior exists.

Logical P7 task P7-004, located in physical Phase 8 (Evaluation and Hardening),
still requires screenshots captured from the implemented app at desktop width
`>=1440px`, backed by deterministic full, legacy-missing, denied, stale, impact,
and assertion-only fixtures. Runtime screenshots must be saved under the
implementation evidence location selected during execution, not silently
substituted with these mockups. A visual comparison may use the mockups as a
target, but mockup presence, visual similarity, or image-generation completion
cannot satisfy logical P7-004 / physical Phase 8 runtime evidence.

| Asset | Planning question | Runtime evidence still required |
|---|---|---|
| `mockup-full-packet-catalog.png` | Can the catalog and inspector expose a complete packet without becoming a raw JSON viewer? | Authorized full packet rendered from the typed API. |
| `mockup-legacy-missing-provenance.png` | Are absent additive fields honest and useful? | Legacy fixture with fields genuinely absent/null. |
| `mockup-denied-catalog.png` | Does fail-closed denial avoid membership leakage? | Typed denied response with zero results, facets, counts, candidates, or object hints. |
| `mockup-stale-impact-workbench.png` | Can a reviewer understand authoritative blocking and downstream impact? | Stale/impact fixture from the implemented impact read seam. |
| `mockup-assertion-only-lineage.png` | Is canonical-claim absence clearly intentional rather than broken? | Runtime with `RF_CANONICAL_CLAIMS_ENABLED=false`. |

### 2.1 Imagegen prompt record

All five final PNGs were generated with the built-in `image_gen` mode and then
saved at the `mockup_assets` paths. No CLI/API fallback was used. The inputs
below were working visual references; they record generation provenance but do
not become durable frontmatter dependencies. Live code and
`frontend/runs-viewer/src/styles/tokens.css` remained the authoritative product
constraints when a reference image conflicted with the app.

| Final image | Image input roles | Final prompt intent and constraints |
|---|---|---|
| Full packet catalog | `assets/screens-7-10/catalog.png` primary layout reference; tracked `public-multiuser-release/mockup-evidence-catalog.png` secondary catalog-style reference. | Authorized **Assertion Catalog** with selected source assertion, exact edition/passage, qualifiers, evaluation, and uses; keep Lifecycle Current, Access Workspace, Reuse Eligible, and Freshness Current separate; RF rail, dense white panels, no truth/fact language, no vector/shared-graph affordance. |
| Legacy-missing provenance | `assets/screens-7-10/run-modal.png` primary modal/shell reference; `runs-frontend-facelift/mockup-claim-audit-workbench.png` secondary audit-density reference. | **Claim provenance** modal preserving run-local source card, quote, locator, report location, and inference basis while seven persistent assertion fields show `Unavailable in this export`; no identity or reuse inference. |
| Denied catalog | `assets/screens-7-10/catalog.png` initial catalog reference; targeted edit of the first generated result to restore the Catalog-selected rail. | Fail-closed **Assertion ledger unavailable** state with Catalog selected, a safe reason code, and zero assertion content, counts, facets, suggestions, or prior-use signals; retain route context and a safe Portfolio exit. |
| Stale impact workbench | `assets/screens-7-10/run-audit.png` primary workbench reference; `runs-frontend-facelift/mockup-claim-audit-workbench.png` secondary density/reference style. | **Claim Audit** with `Reuse blocked — source edition changed`, historical/non-reusable passage, freshness receipt, pending impact operation, complete affected-use groups, pending deterministic reconciliation, and default-denied writeback semantics. |
| Assertion-only lineage | `assets/screens-7-10/run-lineage-graph.png` primary graph reference; `assets/screens-7-10/run-lineage.png` secondary list/detail reference. | **Evidence to assertions and uses** graph with source edition, passage, source assertion, derived inference, report/run uses, and inspector with separate lifecycle, qualifiers, access, reuse decision, and rights sections; canonical grouping explicitly disabled with no canonical lane or merge control. |

## 3. Source-verified visual baseline

The durable visual baseline is the tracked
`public-multiuser-release/current-audit.png`, the tracked
`public-multiuser-release/mockup-evidence-catalog.png`, the live components, and
the token source. Working generation references listed in section 2.1 may be
absent from a clean clone and are not implementation dependencies. Reuse:

- dark navy RF navigation rail and compact route glyphs;
- blue-gray app canvas with white operational panels;
- dense tables and three-column workbench layouts at wide desktop sizes;
- docked inspectors instead of navigation for every selection;
- monospace object IDs as secondary signatures, not primary titles;
- compact chips, eyebrow labels, thin borders, and restrained shadows;
- green for eligible/supported, blue for structural selection and provenance,
  amber for review/refresh/stale, red for denied/invalid/blocked, purple for
  inference/derived reasoning, and neutral gray for unavailable/legacy data.

Use `frontend/runs-viewer/src/styles/tokens.css` as the source of truth. Product
styles must consume semantic or existing primitive tokens; no mockup-sampled
hex colors enter component CSS. The core surfaces remain:

| Surface | Current pattern retained | P7 extension |
|---|---|---|
| `CatalogScreen` | Tabbed, filtered table with docked inspector | Assertion search, packet state, lifecycle/access filters, packet inspector. |
| `ProvenanceModal` | Two-click claim-to-source provenance | Edition, exact passage, selectors, qualifiers, evaluation, freshness, rights, prior use. |
| `ClaimAuditWorkbench` | Ledger/report/selected-claim tri-pane | Stale banner, impact summary, lifecycle reasoning, assertion relationship context. |
| `LineageDetailPanel` | Selected-node detail beside lineage explorer | Typed assertion relationships, run/report uses, explicit assertion-only state. |
| `RunDetailWorkspace` | Shared modal/page tab composition | Persistent assertion version and impact state in audit/lineage paths. |

## 4. Domain language, color, signatures, and default replacements

### 4.1 Object language

The UI uses these names exactly:

| Domain object | Visible noun | Never substitute |
|---|---|---|
| `source_assertion` | **Source assertion** | Fact, truth, canonical fact |
| `canonical_claim` | **Canonical claim** | Assertion (without a qualifier), truth |
| `inference_record` | **Inference** | Source assertion, sourced fact |
| `source_edition` | **Source edition** | Latest source, document version when unknown |
| `passage` | **Exact passage** | Source summary, evidence snippet as a complete packet |
| `rights_decision` | **Reuse decision** | Trust score, source quality |
| impact receipt | **Impact operation** | Cascade, deletion job |

### 4.2 Semantic color contract

Color is redundant with text and iconography; it never carries the state alone.

| State | Token family | Visible signature |
|---|---|---|
| eligible/current/supported | green status/success tokens | check icon + `Eligible for reuse` or `Current` |
| selected/structural/provenance | blue accent/progress tokens | focus/selection treatment + object label |
| inference/derived | purple tokens | branch icon + `Inference` |
| stale/refresh/review | orange warning tokens | warning icon + `Stale — refresh required` |
| denied/invalid/retracted/blocked | red danger/blocked tokens | stop icon + explicit reason text |
| legacy/unavailable/not enabled | neutral idle tokens | em dash/unavailable icon + explanatory label |

### 4.3 Object signatures

Every selected object has a stable, scannable signature line:

`<Object type> · <opaque ID> · v<version> · <lifecycle state>`

Examples:

- `Source assertion · ast_01JZ8Q9A · v3 · current`
- `Source edition · ed_01JZ8P11 · SHA-256 4c8f…9a21`
- `Impact operation · evt_retract_017 · 12 of 12 actions`

Human-readable text remains the heading. IDs use `--it-font-mono`, support
copy, and are never visually mistaken for prose. When a value is absent, omit
the delimiter segment rather than fabricating `v0`, `unknown`, or `latest`.

### 4.4 Replace generic defaults

| Generic/default behavior | P7 replacement |
|---|---|
| Existing `Claims` catalog tab | `Source assertions`, while retaining other current tabs. |
| Existing generic selected-item title | Atomic assertion text plus object signature. |
| Empty string, `undefined`, or invented fallback | `Not recorded in this legacy artifact` for absent additive fields. |
| Generic `403`, toast-only error, or empty table | Bounded `Assertion ledger unavailable` panel with typed safe reason and no candidate-derived data. |
| Generic `Status` | `Lifecycle` for assertion lifecycle; `Evaluation` for review outcome; `Reuse decision` for policy. |
| Generic source excerpt | `Exact passage`, paired with edition and passage identity. |
| Missing canonical node rendered as a broken gap | `Assertion-only mode` explainer; no canonical branch is drawn. |
| Stale chip alone | Authoritative blocked banner plus impact counts and next safe action. |
| `No data` | Object-specific explanation and recovery guidance; never infer a value. |

## 5. Information architecture

### 5.1 Catalog discovery

The existing `/catalog` route gains a `Source assertions` tab. Keep current
project and sensitivity controls, then add:

- lexical search labeled `Search source assertions`;
- `Lifecycle` filter: All, Current, Stale, Corrected, Retracted, Invalid;
- `Access scope` filter sourced from typed facets;
- optional `Reuse decision` filter only if the response contract supplies it;
- results columns: Assertion, Edition, Lifecycle, Reuse decision, Updated;
- a docked packet inspector that loads only after an authorized selection.

Search denial replaces the result region and inspector together. It must not
show a previous result count, previous inspector, facet count, autocomplete,
pagination total, dedupe hint, or existence-sensitive retry copy.

### 5.2 Packet inspector and provenance modal

Order the complete packet for evidence review, not schema inspection:

1. atomic assertion text and signature;
2. lifecycle and reuse-decision banner with typed reason;
3. exact passage, source edition, locator/selectors, and passage hash;
4. structured qualifiers and qualifier extensions;
5. evaluation and extraction provenance;
6. freshness and rights/allowed-use decision;
7. typed relationships;
8. prior report and run uses;
9. `Open provenance` and `View lineage` actions when authorized targets exist.

Raw record maps are not dumped into the UI. Unknown extension keys may appear
in a compact `Additional qualifiers` definition list after known qualifiers.
This review surface does not introduce report mutation or reuse actions.

### 5.3 Stale impact workbench

The audit workbench remains ledger/report/inspector at wide desktop sizes. When
the selected assertion is non-current, place a full-width status band below the
toolbar and above the three columns. The band states the authoritative reuse
block before showing downstream cleanup progress.

The selected-assertion inspector adds an `Impact` section with:

- operation signature and event type;
- authoritative state: `Reuse blocked`;
- receipt state: Pending, Blocked, Completed, or Interrupted;
- affected totals grouped by assertions, relationships/inferences, reports,
  runs/exports, indexes/caches, and default-denied writeback receipts;
- action/status list with completed, pending, failed, or blocked labels;
- `View impact receipt` to inspect the typed operation detail;
- `Open replacement edition` when the typed receipt supplies an authorized
  replacement-edition target.

The workbench never implies that cleanup completion restores eligibility.
Restore is a distinct governed lifecycle decision.

### 5.4 Assertion-only lineage

When `RF_CANONICAL_CLAIMS_ENABLED=false`, lineage starts with the source
edition and exact passage, continues to the source assertion version, then to
typed inference/report/run uses. It omits the canonical-claim lane entirely and
shows one neutral inline notice titled `Assertion-only mode` with the text:

`Canonical claim grouping is disabled pending an independently labeled merge audit.`

There is no disabled merge button, empty canonical column, upgrade CTA, or
error icon. If the feature is enabled and data is absent, that is a different
state and must be represented as `No canonical relationship recorded`.

## 6. Five conceptual target states

The images establish the selected hierarchy and copy. They keep Lifecycle,
Access, Reuse decision, and Freshness as separate labeled concepts.

### A. Full packet catalog

Required visible content:

- page title `Assertion Catalog`, subtitle `Reusable source assertions with exact provenance, lifecycle, and prior use.`, and selected tab `Source assertions`;
- filters `Lifecycle: Current`, `Access: Workspace`, `Reuse: Eligible`,
  `Evaluation: Reviewed`, and `Freshness: Current`;
- selected result `Hybrid retrieval improves recall for long-tail research questions.` with ID `ast_01JX7QF8M2`, version `v3`, lifecycle `Current`, reuse decision `Eligible`, access `Workspace`, freshness `Current`, and prior-use totals;
- inspector signature `ast_01JX7QF8M2 · v3` and chips `Current` and `Reuse eligible`;
- vertical sections `Edition`, `Passage`, `Source assertion`, `Evaluation`, and `Uses`;
- verbatim passage `Hybrid retrieval increased Recall@50 by 22.3% compared with the best single retriever.` and locator `Section 5.3 · Paragraph 2`;
- qualifier rows `Population`, `Metric`, `Comparator`, and `Timeframe`;
- `Open provenance` and `View lineage` actions, plus non-action workspace,
  attribution, and reuse-allowed chips.

### B. Legacy-missing provenance

Required visible content:

- modal title `Claim provenance`, eyebrow `Legacy run claim`, claim ID `clm_043`, and `Inference` / `Supported` chips;
- left column `Run-local provenance` with `Source Cards`, `Verbatim quote`,
  `Locator`, `Report locations`, and `Inference basis`;
- right column `Reusable assertion fields` with the explanation `This run predates persistent assertion fields. Run-local provenance remains available.`;
- seven rows—`Persistent assertion ID`, `Immutable source edition`, `Exact passage selector`, `Structured qualifiers`, `Rights decision`, `Freshness`, and `Impact data`—each show `Unavailable in this export`;
- footer notice `Run-local provenance preserved. No durable assertion identity was inferred.`;
- actions `Open source card` and `Close`;
- no refresh, merge, or reuse eligibility is inferred.

### C. Denied catalog

Required visible content:

- page title `Assertion Catalog` with the catalog route retained in the rail;
- bounded panel title `Assertion ledger unavailable`;
- safe copy `This workspace cannot access reusable assertion records.`;
- reason label `Reason: assertion_ledger_access_denied`;
- disclosure statement `No assertion content, counts, facets, suggestions, or prior-use metadata was loaded.`;
- recovery text `Run-local research remains available from Portfolio.` and action
  `Return to Portfolio`;
- no results, count, facets, suggestions, pagination, selected ID, or inspector
  detail from the denied request.

### D. Stale impact workbench

Required visible content:

- page title `Claim Audit` and subtitle `Review assertions, exact evidence, and downstream impact.`;
- status band `Reuse blocked — source edition changed` with explanation `A newer immutable edition supersedes the evidence used by this assertion. Existing uses remain traceable; new reuse is blocked.`;
- actions `View impact receipt` and `Open replacement edition`;
- selected signature `ast_01JX7QF8M2 · v3`, lifecycle `Stale`, and state `Reuse blocked`;
- report context with `Supporting passage`, `Source card`, and `Run context`;
- `Freshness receipt` reason `source_edition_superseded`, edition transition,
  and detection timestamp;
- impact signature `Impact operation · evt_supersede_017 · pending`;
- affected-use rows `Assertion versions`, `Relationships / inferences`,
  `Report revisions`, `Runs`, `Exports / projections`, `Indexes / caches`, and
  `Writebacks`, including `1 denied · 1 queued`;
- passage chip `Historical · non-reusable`;
- reconciliation label `Deterministic reconciliation pending` and bottom
  source-edition-to-passage-to-assertion-to-affected-uses-to-writeback-gate flow.

### E. Assertion-only lineage

Required visible content:

- title `Evidence to assertions and uses`;
- neutral `Assertion-only mode` notice using the exact title and copy from section 5.4;
- visible `Source edition`, `Passage`, `Source assertion`, `Inference · Derived`,
  and `Report / run uses` nodes;
- no canonical-claim node, blank canonical lane, or merge control;
- selected source-assertion inspector separately shows `Durable identity`,
  `Lifecycle` (`Current`), `Qualifiers`, `Access` (`Workspace`), `Reuse decision`
  (`Eligible`), `Rights`, and `Prior uses`, with `Open provenance` and `View prior uses` actions.

## 7. Interaction contracts

### Selection and navigation

- Row click and `Enter`/`Space` select the assertion and update the docked
  inspector without opening a modal.
- `Open provenance` is the explicit modal entry point; it returns focus to the
  invoking control when closed.
- Deep links may encode selected assertion ID only when doing so does not expose
  an unauthorized identifier before policy resolution.
- `Inspect lineage` opens the existing lineage context with the same assertion
  selected; browser Back restores catalog filters and selection.
- Run/report links include accessible human titles and keep opaque IDs as
  secondary text.

### Loading, stale, denied, and error behavior

- First load uses a labeled skeleton or `Loading source assertions…` and does
  not present zero as a real result count.
- Filter changes may retain the prior table as visually busy, but the prior
  inspector is not presented as the newly requested packet.
- A typed denied envelope clears previous candidate-derived UI atomically.
- A `403` packet response becomes the denied state; `404` becomes `Assertion not
  found or unavailable`; neither distinguishes cross-workspace existence.
- Missing optional fields render at field granularity; one missing field does
  not collapse the rest of a packet.
- Unexpected errors present retry and a safe correlation identifier, never raw
  passage content or an internal stack.

### Optional merge review

Merge-candidate controls exist only when all are true: the compile/runtime flag
is enabled, generated contract fields are present, the identity SPIKE verdict
permits the behavior, and the user is authorized. Otherwise the controls are
absent. Assertion-only mode is a valid product state, not a disabled-control
state.

## 8. Typed API and frontend seam

P6-001 must consume generated types and keep transport semantics distinct from
display derivation. The currently implemented packet seam includes
`AssertionSearchResponse`, `EvidencePacket`, `AssertionLineage`,
`RightsDecision`, and typed denial behavior. P7 must not replace these with
parallel handwritten packet interfaces.

P6-000 owns the missing impact read seam before P6-001 or P6-003 begins: add a
workspace-authorized, policy-filtered `GET
/api/assertions/{assertion_id}/impact` read route over persisted P5 receipts,
freeze OpenAPI, regenerate TypeScript, and verify that denied reads expose zero
actions, counts, object IDs, replacement targets, or membership hints. No
mutation route is introduced. The minimum generated contract is:

```ts
type ImpactOperationStatus = "pending" | "blocked" | "completed" | "interrupted";
type ImpactActionStatus = "pending" | "completed" | "failed" | "blocked";

interface AssertionImpactSummary {
  event_id: string;
  assertion_id: string;
  lifecycle_state: string;
  access_scope: string;
  authoritative_reuse_blocked: true;
  operation_status: ImpactOperationStatus;
  reason_code?: string | null;
  replacement_edition_id?: string | null;
  resumable: boolean;
  actions: Array<{
    object_id: string;
    object_class: string;
    action: string;
    status: ImpactActionStatus;
  }>;
}
```

This shape is a design requirement, not permission to hand-author the generated
file. P6-000 owns route/DTO/OpenAPI/code generation; P6-001 consumes the frozen
generated output. The client query key includes workspace/auth resolution plus
assertion/event ID.
No assertion or impact query runs before workspace/auth context resolves.
Denied responses are not cached as globally reusable data, and a workspace
change clears selected records and candidate-derived UI.

The typed impact read seam is an implementation prerequisite for the impact
counts, action list, receipt status, replacement-edition link, and stale-impact
runtime fixture. P6-003 does not start until P6-000 is frozen. If P6-000 is
blocked, the only safe fallback is a feature-gated `Impact data unavailable`
state with no counts and no mutation control; the frontend must not read ledger
files directly, derive a dependency graph from packet relationships, or
synthesize completion. That fallback may preserve packet/provenance review, but
it cannot satisfy AC UX-4 or logical P7 task P7-004 in physical Phase 8.

Typed renderer rules:

- object maps inside packets are narrowed by small defensive selectors;
- optional fields remain optional through hooks and view models;
- reason codes map to concise human copy while the code remains visible;
- unknown enum values render `Unavailable (<safe value>)` and never become an
  eligible/current default;
- the impact action list is grouped in the UI without changing receipt order or
  inventing actions;
- inferences and source assertions use separate view-model discriminants.

## 9. Responsive behavior

| Width/state | Contract |
|---|---|
| `>=1440px` | Catalog table + docked inspector; audit three-column workbench; lineage explorer + inspector. This is the required runtime screenshot width. |
| `1100–1439px` | Catalog inspector moves below results; audit ledger and report remain side-by-side with selected item below; impact groups wrap without horizontal page scroll. |
| `768–1099px` | One primary column; filters collapse behind `Filters`; selected packet is an in-flow detail region or full-height drawer; tables retain labeled horizontal scroll regions. |
| `<768px` | Review-only fallback: stacked list rows, details in a full-screen dialog/drawer, sticky close/back action, 44px targets. Dense graph defaults to list/tree. |

At every width, exact passage text wraps, IDs can break safely, definition
lists retain label/value association, and no fixed-height panel clips denial or
legacy explanations. The desktop mockups do not define mobile pixel layouts;
the contracts above do.

## 10. Accessibility

- Meet WCAG 2.2 AA contrast with token-driven light and dark themes.
- All state colors have visible text; icons are supplementary and decorative
  icons use `aria-hidden`.
- Search results use an accessible table or listbox pattern consistently. Do
  not add `role="grid"` behavior without implementing its keyboard contract.
- Filters have persistent labels; counts are included in accessible names only
  when authorized and meaningful.
- Selection is exposed with `aria-selected`; focus and selection remain
  distinct.
- Status banners use `role="status"` for passive changes and `role="alert"`
  only when reuse becomes blocked during the current interaction.
- Modal focus is trapped; Escape closes only the top modal; close returns focus
  to `Open provenance`.
- Impact progress is announced as text (`12 of 12 actions completed`), not a
  color-only ring.
- Exact passages use semantic `blockquote` plus source/edition attribution.
- Copy controls have object-specific names such as `Copy source assertion ID`.
- Reduced-motion mode removes smooth scrolling and nonessential transitions.
- At 200% zoom, reading order remains catalog/results then packet, or ledger,
  report, then selected assertion/impact.

## 11. Acceptance criteria

### AC UX-1 — Complete packet is evidence-first

- An authorized reviewer can select a source assertion and see assertion text,
  exact passage, immutable edition, qualifiers, evaluation, freshness, rights,
  relationships, and prior uses without inspecting raw JSON.
- Source assertion, canonical claim, and inference labels remain distinct.
- No report/reuse mutation action is introduced by this review surface.

### AC UX-2 — Missing data is honest

- Legacy fixtures preserve current run-local provenance.
- Every absent additive field uses the legacy/unavailable treatment; no
  persistent ID, version, qualifier, freshness, impact, or merge state is
  inferred.
- Existing supported export fixtures remain readable.

### AC UX-3 — Denial leaks no derived signals

- A denied search or packet clears prior counts, facets, pagination,
  suggestions, selection, and inspector content from the denied surface.
- The reviewer sees a typed safe reason and recovery guidance without learning
  whether an assertion exists in another workspace.

### AC UX-4 — Stale impact is actionable but conservative

- Authoritative reuse blocking is more prominent than cleanup progress.
- Impact groups and action statuses exactly reflect the generated receipt DTO.
- Historical provenance remains visible only to authorized auditors and is
  labeled non-reusable.
- Interrupted/unknown states do not render as completed or safe.

### AC UX-5 — Assertion-only is first-class

- With `RF_CANONICAL_CLAIMS_ENABLED=false`, merge controls and canonical nodes
  are absent and the assertion-only notice is present.
- Source-edition, passage, assertion, inference, report, and run relationships
  remain reviewable.
- No visual gap implies missing or failed canonical data.

### AC UX-6 — Interaction, responsive, and accessibility contracts pass

- Keyboard-only users can filter, select, inspect, open/close provenance, and
  traverse lineage with visible focus and correct focus return.
- Full, legacy-missing, denied, stale/impact, and assertion-only component tests
  cover labels and absent false affordances.
- Layouts meet section 9 at representative breakpoints and at 200% zoom.
- Light/dark contrast, accessible names, status announcements, and reduced
  motion pass the phase accessibility checks.

### AC UX-7 — Planning imagery stays non-authoritative

- The five conceptual mockups exist at the frontmatter paths and are linked for
  implementation reference.
- Logical P7 task P7-004 in physical Phase 8 captures new runtime screenshots
  at `>=1440px` from deterministic fixtures after implementation and only after
  the P6-000 impact OpenAPI/codegen output is frozen.
- Validation records identify each runtime fixture/API state; none cites a
  conceptual mockup as proof of implemented behavior.

## 12. Implementation handoff

- P6-000: workspace-authorized impact receipt read route/DTO, API denial tests,
  OpenAPI freeze, and generated TypeScript; its output gates P6-001/P6-003.
- P6-001: generated assertion/impact types, client calls, hooks, query gating,
  and explicit loading/denied/error/missing-field view states.
- P6-002: Catalog and Provenance packet discovery/detail, exact content and
  labels from sections 5.1–5.2.
- P6-003: audit/lineage/run-detail impact and assertion-only behavior, optional
  merge controls only behind every named gate.
- P6-004: component, keyboard, accessibility, responsive, and resilience tests;
  hand implemented surfaces and deterministic fixtures to logical P7 task
  P7-004 in physical Phase 8 runtime smoke.

Implementation should compare the runtime against the mockups for information
hierarchy, not pixel duplication. Existing tokens, components, and tested
interaction patterns win when an image-generation artifact contains an
ambiguous control, impossible value, inconsistent spacing, or inaccurate text.
