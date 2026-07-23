---
schema_version: 2
doc_type: spike
leg: value
feature_slug: claim-term-indexing
status: complete
confidence: 0.72
created: 2026-07-23
---

# Value Leg — Claim Term Indexing

## Evidence Summary

**1. The counterfactual is not "nothing" — it is FTS5/BM25 substring search with no vocabulary layer.**
`rf catalog search --q CBC --item-type claim` (`src/research_foundry/cli_commands.py:1474`) calls
`catalog_service.search()` (`src/research_foundry/services/catalog_service.py:1259-1340`), which runs
SQLite FTS5 `MATCH`+`bm25()` ranking when available, else `search_text LIKE '%q%'`
(`catalog_service.py:1315-1332`), over a flattened `search_text` column, filtered by
`item_type|project|status|sensitivity|run_id`. This already answers "find claims mentioning CBC"
reasonably for exact tokens. It does **not**: canonicalize aliases (a claim saying "complete blood
count" won't surface on query `CBC` unless the literal token co-occurs), expose a term facet/browse
list, or carry any usage-role (finding vs. threshold vs. measurement vs. background).

**2. The assertion catalog's own search is cruder than the CLI's** — pure `casefold()` substring
containment on `search_text`, no FTS at all: `AssertionCatalog.search()`
(`src/research_foundry/services/assertion_catalog.py:154-215`, match at line ~194:
`normalized_query in record["search_text"].casefold()`). Facets exposed are only
`lifecycle_states`/`access_scopes` (`assertion_catalog.py:212-214`) — no term/topic facet exists
anywhere in the catalog layer today.

**3. CARP (merged *today*, commit `d824290`) independently reinvented per-term matching to work
around exactly this gap** — strong same-day corroboration that the need is real, not hypothetical.
`catalog_retrieval.py:_collect_candidates()` (`src/research_foundry/services/catalog_retrieval.py:385-449`)
iterates `question.required_terms` and issues one substring `catalog.search(query=term)` call per
term, intersecting `assertion_id` sets to compute `matched_terms` (line ~437-446) — an N-substring-scan
emulation of "does this assertion carry these terms," built at the call site because no stored
per-entity term field exists. The schema even documents the caveat: `required_terms` are
"case-folded lexical terms every selected candidate's search_text must contain (conservative rule;
no semantic/vector matching)" (`schemas/research_evidence_plan.schema.yaml:111-114`), and the CARP PRD
names the accepted risk directly: *"Lexical catalog matching plus explicit constraints is sufficient
for a conservative v1 selection surface; **missed matches become residual discovery, not false
coverage**"* (`docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md:349`).
That is a concrete, dated admission that today's approach silently over-triggers external
discovery/model calls when a claim uses a synonym RF hasn't been told to also search for — precisely
the failure mode a canonical term index (with alias resolution) removes.

**4. `required_terms` are hand-authored per research question today**, not derived from the claim
corpus (`research_evidence_plan.schema.yaml:106-114`, populated by the planner, not the ledger). A
claim-side term index would let `required_terms` be populated/validated against the vocabulary claims
actually carry, rather than guessed per question — a direct quality lever on CARP's covered/residual
partition (`research_evidence_plan.schema.yaml` six-condition contract, frozen this session).

**5. UI hosting surface already exists and already tabs by item_type + live query.**
`AssertionCatalogPane.tsx` (`frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx:53-114`)
has a debounced free-text `searchInput` and a facet-driven filter row wired to `search.data?.facets`
(line 83); `CatalogScreen.tsx` (`frontend/runs-viewer/src/screens/CatalogScreen.tsx:448-497`) tabs
`useCatalogSearch` by `item_type` with its own debounced query. Both are the natural slot for a
"terms present" facet chip-row or a `?term=CBC` deep link — no new screen architecture needed, only a
new facet/param, which lowers the marginal UI cost of the term-view payoff considerably.

**6. Pediatric-CDS bundles are the sharpest concrete use case but their runs are not resident in this
repo** (`runs/` is empty in this worktree — runs are workspace-local/gitignored). The "7 verified
pediatric-CDS bundles" figure comes from the charter's risk-leg framing, not independently observed
here. What *is* verifiable in-repo: the `pediatric_cds` evidence-card contract
(`.claude/workflows/rf-pediatric-cds-run-execute.js:63-99`, schema at
`src/research_foundry/schemas/pediatric_cds.schema.json`) structures each extracted point with
`population`/`assay_method`/`threshold{value,units_ucum}`/`lifecycle`/`classification` fields per
finding — i.e., the source cards already carry the raw material (numeric threshold + assay context)
that a term/usage-role pass would key off deterministically (e.g. "CBC" appearing inside a `threshold`
block ⇒ usage-role `threshold`), without needing any new extraction step. The pediatric-anemia-site
repo itself (out of scope per charter) is [model-knowledge, unverified]: I have prior exposure to it as
a sibling project under active build (multiple worktrees named `evidence-foundry-*`,
`wave0-ep*-*`, `multi-bundle-conversion-*` under `~/dev/homelab/development/pediatric-anemia-site`),
consistent with an actively-growing bundle count, but I did not open that repo for this leg.

## User Segments + Frequency

| Segment | Job | Today's tool | Frequency (estimate) |
|---|---|---|---|
| RF operator authoring a pediatric-CDS run | "What does the corpus already say about CBC/ferritin thresholds before I discover more?" | `rf catalog search --q <term> --item-type claim`, manual re-reading of source cards | Per-run, likely 3-8x/run across the discover→enrich loop (workflow has 8 phases, several re-touch evidence) |
| CARP planner (now automated, `catalog_retrieval.py`) | Decide covered vs. residual per research question | Hand-typed `required_terms` list + N substring scans | Every planned run with retrieval-first enabled (new, just merged) — will scale with run volume, not per-session |
| Runs-viewer analyst reviewing a bundle | "Show me everything touching CBC across this/related runs" | Free-text search box in `CatalogScreen`/`AssertionCatalogPane`, no term facet, no cross-run browse | Ad hoc, per-review session |
| Future report/positioning-memo author | Topic-driven drafting ("gather every threshold claim for CBC") | Manual grep/re-read of claim ledger markdown | Not yet instrumented — payoff #3 is aspirational until CARP-style consumers exist beyond retrieval-first planning |

Frequency is moderate, not high-volume: RF is a single/small-team control plane, not a high-QPS search
product. The value case rests more on **precision/consistency of a small number of high-stakes
lookups** (pediatric-CDS runs feed a clinical decision-support product) than on raw search traffic.

## Counterfactual Behavior Today

Absent a term index, "find/browse claims about CBC" resolves via: (a) `rf catalog search --q CBC`
(FTS5/BM25 substring, works for exact tokens, silent on aliases), (b) manual `grep`/re-reading of
claim-ledger and source-card markdown files, or (c) CARP's `required_terms` mechanism, which is a
per-question, hand-typed, N-substring-scan workaround already merged into production code
(`catalog_retrieval.py:385-449`) specifically because no stored per-entity term field exists. None of
these three paths distinguish *how* a term is used (threshold vs. background mention), so a
term-centric "show me every place CBC appears as a threshold" query is not answerable today without
opening every candidate claim by hand.

## Value Confidence Rationale — 0.72

**Supports go:**
- Concrete, *same-day*, in-repo evidence (not speculative) that a consuming feature (CARP) already
  needed and hand-rolled a weaker version of exactly this capability, and documented the resulting
  risk (`catalog-assisted-research-planning-v1.md:349`).
- A real hosting UI surface exists with near-zero incremental screen-architecture cost.
- The pediatric_cds schema already carries structured fields (`threshold`, `assay_method`) that make
  deterministic usage-role tagging plausible without new model calls — directly satisfying the
  charter's deal-killer constraint from the value side.

**Tempers confidence below 0.8:**
- Payoff #1 (cheap term search) is **already substantially served** by existing FTS5/BM25 —the
  incremental value there is narrower than the charter implies (alias/canonicalization + facet browse,
  not "search didn't exist before").
- The headline pediatric-anemia-site use case (7 bundles) could not be independently corroborated
  in-repo this session (out of scope by charter + empty local `runs/`); it is taken on the charter's
  word, not verified.
- Frequency is low-to-moderate (small-team control plane), so ROI depends on stakes-per-lookup
  (clinical/regulatory correctness) more than volume — a valid case, but a narrower one than "cheap
  search for everyone."
- Payoff #3 (topic-driven planning) is real and dated (CARP), but its current form (`required_terms`)
  is planner-authored, not yet claim-derived — the value is contingent on a follow-on integration
  (feed the index into `required_terms` generation), not automatic.

**Net**: value is real and evidenced by an already-merged workaround, not merely aspirational — but
it is a precision/consistency play for a small number of high-stakes lookups plus a concrete efficiency
fix for CARP's residual-discovery false-positive risk, rather than a broad search-volume win.
