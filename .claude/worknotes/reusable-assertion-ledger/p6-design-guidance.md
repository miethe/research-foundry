# P6 Reviewer Experience — Orchestrator Design Guidance (mockup visual pass)

Distilled from the five conceptual mockups by the orchestrator's direct visual inspection.
Authoritative constraints remain: `docs/project_plans/design-specs/reusable-assertion-ledger-reviewer-experience-v1.md`
(exact copy in §6, replacement table §4.4, IA §5) and `frontend/runs-viewer/src/styles/tokens.css`.
Mockups guide **hierarchy and state design**, not pixel duplication; existing components/tokens win
on conflict. No mockup-sampled hex values in component CSS.

## Shared patterns observed across all five mockups

- **Object signature line**: mono ID + `· v3` renders as a distinct signature row under/next to a
  blue all-caps eyebrow (`SOURCE ASSERTION`), with status chips inline-right. Human text is the
  heading below the signature, not the other way around.
- **Status chips**: small rounded pills with a leading colored dot (green Current/Eligible, amber
  Stale/Under review, red denied/blocked, blue-gray Workspace access, purple inference). Text always
  carries the state; the dot is redundant.
- **Vertical timeline rail** in inspectors/modals: circular outlined icon nodes (document, quote
  marks, shield, star, chart) connected by a thin vertical line, one node per packet section. Reuse
  the existing provenance/timeline treatment if one exists; otherwise a simple left icon column with
  a connecting border is enough — hierarchy matters, not the exact rail art.
- **Definition-list qualifier tables**: two-column label/value rows with muted small-caps labels
  (Population / Metric / Comparator / Timeframe), hairline row separators.
- **Verbatim passages**: rendered inside a bordered, slightly tinted box as `blockquote`, with a
  separate small "Locator" box beneath (`Section 5.3 · Paragraph 2`) with copy affordance.

## A. CatalogScreen — `Source assertions` tab (P6-002)

- Header: title `Assertion Catalog`, muted subtitle, search field top-right
  (`Search source assertions…`). Tab strip adds `Source assertions` as first/active tab alongside
  existing tabs; keep existing tab component.
- Filter row: pill-shaped dropdown buttons each with a leading icon and `Label: Value` text —
  `Lifecycle: Current`, `Access: Workspace`, `Reuse: Eligible`, `Evaluation: Reviewed`,
  `Freshness: Current`, then `More filters`. Reuse the existing catalog filter control style; do NOT
  invent a new filter component.
- Table columns: ASSERTION (two-line cell: assertion text wraps, mono ID chip `ast_…` below),
  VERSION (mono `v3` pill), SOURCE EDITION (mono id + capture date stacked), LIFECYCLE / ACCESS /
  REUSE / FRESHNESS (dot chips), PRIOR USES (`Used in 4 runs · 3 report revisions`, two lines),
  row overflow menu. Selected row gets the blue selection ring; selection updates the docked
  inspector without navigation.
- Docked inspector (right, ~360-400px at >=1440px): eyebrow `SOURCE ASSERTION` + close X;
  signature `ast_01JX7QF8M2 · v3` with `Current` + `Reuse eligible` chips; assertion text as the
  large heading; then timeline sections in this exact order: **Edition** (mono edition id +
  captured date + `Open provenance` secondary button) → **Passage** (mono passage id, `VERBATIM
  PASSAGE` micro-eyebrow, blockquote box, Locator box) → **Source assertion** (`QUALIFIERS`
  micro-eyebrow + definition table) → **Evaluation** (`Supported` green + `Reviewed` blue chips,
  reviewer/date two-column) → **Uses** (`Used in N runs · M report revisions` + `View lineage`
  button). Footer: non-action chips `Workspace` / `Attribution required` / `Reuse allowed` under a
  muted `Workspace` label.

## B. ProvenanceModal — packet fields + legacy-missing (P6-002)

- Modal title `Claim provenance`; orange/amber caps eyebrow `LEGACY RUN CLAIM` (legacy fixture
  only); large mono claim id (`clm_043`) with `Inference` (blue/purple per existing inference
  treatment) + `Supported` (green) chips; claim text under it.
- Two-column body at desktop: left `Run-local provenance` = existing content (Source Cards card,
  Verbatim quote box, Locator with copy, Report locations, Inference basis in a tinted info panel)
  arranged on the timeline rail; right `Reusable assertion fields` column.
- Legacy state (any absent additive field): right column leads with the explainer
  `This run predates persistent assertion fields. Run-local provenance remains available.` then one
  row per field — amber warning-triangle icon, bold field name (`Persistent assertion ID`,
  `Immutable source edition`, `Exact passage selector`, `Structured qualifiers`, `Rights decision`,
  `Freshness`, `Impact data`), and value `Unavailable in this export` (amber "Unavailable", muted
  "in this export"). Field-granular: a populated field renders its real value; one missing field
  never collapses the rest.
- Footer: full-width amber notice `Run-local provenance preserved. No durable assertion identity
  was inferred.` + right-aligned `Open source card` (secondary, external-link icon) and `Close`
  (primary). Focus trap; close returns focus to the invoking `Open provenance` control.

## C. Denied catalog state (P6-001/P6-002)

- The result region AND inspector are replaced together by one centered bounded card on the page
  canvas: red shield/lock icon, H2 `Assertion ledger unavailable`, one-line safe copy, hairline
  divider, `Reason:` + red mono `assertion_ledger_access_denied`, divider, the zero-disclosure
  sentence, recovery sentence with `Portfolio` emphasized, and a red-outlined full-width
  `← Return to Portfolio` action. Page title + rail stay; NOTHING candidate-derived remains
  (no counts, facets, pagination, previous inspector).

## D. ClaimAuditWorkbench — stale impact (P6-003)

- Full-width status band between toolbar and the tri-pane: amber/orange background, warning icon,
  bold `Reuse blocked — source edition changed`, secondary line `A newer immutable edition
  supersedes the evidence used by this assertion. Existing uses remain traceable; new reuse is
  blocked.`, right-aligned `View impact receipt` outlined button. `role="status"` (alert only if it
  appears during the current interaction).
- Selected-assertion inspector adds, in order: **Lifecycle** (`Stale` amber dot | `Reuse blocked`
  red with lock icon — two separate labeled facts side by side); **Exact provenance** (mono
  signature); **Freshness receipt** (Reason: mono `source_edition_superseded`; Edition transition:
  mono `sed_old → sed_new` with arrow; Detected timestamp); **Impact operation** signature
  (`evt_supersede_017 · pending`); **Affected uses** rows each icon + label + right-aligned count
  badge — `Assertion versions`, `Relationships / inferences`, `Report revisions`, `Runs`,
  `Exports / projections`, `Indexes / caches`, `Writebacks` (writebacks show `1 denied · 1 queued`
  style, not a bare count); **Reconciliation** line `Deterministic reconciliation pending`;
  `Open replacement edition` button ONLY when the typed receipt supplies an authorized target.
- Passage in report context gets an amber chip `Historical · non-reusable` when stale.
- Counts/groups come ONLY from the generated DTO's action list grouped by object_class in the UI —
  never reordered, never invented; interrupted/unknown never renders as completed/safe.
- Blocking is visually senior to progress: the band outranks any progress affordance; progress is
  announced as text (`12 of 12 actions completed`).

## E. Lineage — assertion-only (P6-003)

- Eyebrow `SOURCE-FIRST LINEAGE`, title `Evidence to assertions and uses`.
- Amber/neutral inline notice card at top: bold `Assertion-only mode` + exact copy
  `Canonical claim grouping is disabled pending an independently labeled merge audit.` — an info
  notice, NOT an error; no disabled merge button, no empty canonical lane anywhere.
- Node chain left→right: `Source edition` (mono id + Workspace chip) → `Passage` → `Source
  assertion` (selected = blue border; assertion text inside) → `Report / run uses` (stacked count
  pills: `4 runs`, `3 report revisions`, `2 exports`). Inference hangs BELOW the assertion with a
  dashed purple connector and a purple caps label `INFERENCE · DERIVED`, lightbulb icon, text, and
  a mono `Inputs: ast_…, ast_…` footer — visually impossible to mistake for a source assertion.
- Inspector sections, separately labeled: `Durable identity` (mono + copy button), `Lifecycle`
  (`Current` chip), `Qualifiers` (definition table), `Access` (`Workspace`), `Reuse decision`
  (`Eligible`), `Rights` (`Attribution required` + `Reuse allowed` chips), `Prior uses` (`9 total`
  + chevron), then `Open provenance` and `View prior uses` actions.
- If the canonical feature is enabled but data absent, that is `No canonical relationship
  recorded` — a different state from assertion-only mode.

## Hard don'ts (from spec, enforced in review)

- Never say Fact/Truth/Canonical fact for a source assertion; `Status` is replaced by
  `Lifecycle`/`Evaluation`/`Reuse decision` per context.
- Absent values omit the signature segment (no `v0`/`unknown`/`latest`).
- Unknown enum → `Unavailable (<safe value>)`, never an eligible/current default.
- Denied surfaces atomically clear candidate-derived UI; no query fires before workspace/auth
  context resolves.
