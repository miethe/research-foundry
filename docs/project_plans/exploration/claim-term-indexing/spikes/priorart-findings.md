---
schema_version: 2
doc_type: spike
leg: priorart
feature_slug: claim-term-indexing
status: complete
confidence: 0.75
created: 2026-07-23
---

# Prior Art — Claim Term Indexing

## Internal matches

### 1. CARP `required_terms` lexical match (closest functional analog)
`schemas/research_evidence_plan.schema.yaml:111-112` defines `required_terms`: "Case-folded lexical
terms every selected candidate's search_text must contain (conservative rule; no semantic/vector
matching)." Implemented in `src/research_foundry/services/catalog_retrieval.py:385-419`
(`_collect_candidates`): for each term, case-fold substring match against `search_text`, computed
*inside* `AssertionCatalog.search()` (`src/research_foundry/services/assertion_catalog.py:199`),
never read directly by the adapter (documented "Seam 2" boundary, `docs/dev/architecture/carp-contract-freeze.md` §3).
**Similarity**: identical matching philosophy to what a term index needs — deterministic, case-folded,
substring, zero model calls. **Delta**: CARP computes matches at *query time* against an ad-hoc term
list from the caller's question; it does not *persist* a per-entity term set, has no fixed vocabulary,
and has no usage-role concept. It proves the matching primitive works but is not storage.

### 2. Catalog derived sqlite3 + FTS5 read model (closest architectural analog)
`src/research_foundry/services/catalog_service.py:1-20` docstring: "derived sqlite3 + FTS5 read
model... Derived, rebuildable — the DB is never canonical... can be dropped and rebuilt... at any
time (`rebuild`)." DDL at `catalog_service.py:170-244`; FTS5 virtual table with graceful LIKE
fallback if FTS5 isn't compiled in (`catalog_service.py:247-270`). The `catalog_report_drafts` table
(`catalog_service.py:211-238`) is explicitly commented as a "derived, rebuildable read model of
file-canonical drafts... byte-for-byte" reconstruction contract via `builder_service.reindex_all_drafts()`.
**Similarity**: this is the exact shape a term index should take — a derived index table
(SQLite, possibly FTS5) computed from file-canonical Markdown/YAML, rebuildable, never authoritative.
**Delta**: it indexes free-text blobs (`search_text`) for whole-string/LIKE search over *items*, not
a fixed-vocabulary term extraction with per-term usage-role tags attached to each *claim*. No
concept of "which controlled terms appear in this claim" exists today — it's the file to extend,
not a template to copy verbatim (1985 lines — H7 huge-file-touch multiplier applies if edited in place).

### 3. search_router (rf search/fetch) — provider search, not corpus indexing
`src/research_foundry/services/search_router/` (`router.py` 482 lines, `ranking.py`, `dedupe.py`,
`modes.py`, `policy.py`, `budgets.py`). `ranking.py:1-9,20-56` implements `authority_score` (source-type
weight + freshness bonus + risk-flag penalty) and `rank_hits` — a heuristic scorer over *external*
provider results, not RF's own corpus. `modes.py:37-50` defines `cache_first` etc. as query-shaped
discovery modes. **Similarity**: none directly on term extraction; **Delta**: search_router is
entirely about routing/ranking/deduping *external* web results for a query — it has no notion of
indexing RF's own claims/entities at all. Cited by the charter as "adjacent evidence" but is not an
implementation anchor for this feature.

### 4. Canonical claim / claim ledger schemas — no existing vocabulary field (confirmed gap)
`schemas/canonical_claim.schema.yaml` and `schemas/claim_ledger.schema.yaml`: no `tags`, `topics`,
`terms`, or `keywords` property anywhere in either schema (grep across both files: zero hits).
`schemas/meatywiki_writeback.schema.yaml` → `MeatyWikiWriteback` interface (`frontend/runs-viewer/src/types/rf/meatywiki_writeback.generated.ts:1-29`)
carries `key_claims[].claim_id`/`include` only — no topic/term surface on the writeback contract either.
**Delta**: confirms there is currently zero term/vocabulary concept anywhere in the claim, ledger, or
writeback schemas — this is genuinely new surface, not an extension of an existing (if hidden) field.

### 5. runs-viewer Assertion/Claim Ledger UI — no term/tag column (confirmed gap)
`frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx`,
`ClaimAuditWorkbench.tsx`, `AssertionAuditPanel.tsx`: grep for topic/term/tag/keyword returns zero
hits. The "assertion ledger" mentioned in the charter is the reusable-assertion-ledger feature
(`docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md`, AAR
`docs/project_plans/aars/2026-07-14-reusable-assertion-ledger-p0-p5-execution.md`) — it governs
reuse/versioning of assertions, not term indexing. **Delta**: a term-centric view ("all claims
touching CBC") has no existing UI seam to extend; it would be new columns/filters on
`ClaimLedgerTable` plus a new derived query surface.

### 6. MeatyWiki semantic search [model-knowledge, unverified]
MeatyWiki is external to this repo (no source present); per charter it does vector/semantic search
over wiki pages. Not inspectable here — flagged as an integration target for term-tagged writebacks
(term-tagged claims could set MeatyWiki page tags at writeback time), not a build anchor.

## External matches [model-knowledge, unverified]

- **Controlled vocabularies (MeSH, UMLS Metathesaurus, LOINC, SNOMED CT)**: standard biomedical
  terminologies; LOINC specifically codes lab tests (CBC panel, ferritin, hemoglobin have LOINC
  codes), UMLS links synonyms/abbreviations across vocabularies. Relevant as a *future* vocabulary
  source once the pediatric curated list outgrows a hand-maintained YAML file — not needed for v1.
- **BM25/tf-idf vs embedding retrieval**: full-text ranking algorithms assume a growing, statistically
  modeled corpus (IDF recomputed as documents are added/removed) — this adds non-trivial state and
  reproducibility risk (a claim's term score could drift as unrelated claims are added elsewhere).
  For a *closed, curated* vocabulary, simple deterministic presence-matching (does term X appear in
  claim Y, case-folded, word-boundary aware) is strictly simpler, cheaper, and fully reproducible —
  matches the CARP precedent (#1 above) rather than reinventing IR ranking.
- **Deterministic multi-pattern matching (Aho-Corasick, e.g. `pyahocorasick`)**: for a vocabulary of
  even a few hundred terms, single-pass multi-pattern string matching is O(text length), fully
  deterministic, and avoids per-term regex loops. This is the right *algorithm* for extraction, not
  a full NLP pipeline.
- **Deterministic biomedical NER (scispaCy `en_core_sci_sm`/`en_ner_bc5cdr_md`)**: pinned-weight
  models are reproducible per-version but add a heavyweight ML dependency + version-pinning surface
  purely to recognize entities that a fixed pediatric vocabulary list already enumerates. Overkill
  for a closed vocabulary; would matter only if the project later wants *open-vocabulary* term
  discovery (finding new terms it didn't know to look for) — explicitly out of scope per charter.

## Recommended H5 estimation anchor

**Anchor**: CARP P1 (Contract and Policy Freeze, 4 pts) + P2 (Governed Catalog Adapter, 5 pts) = **9 pts**
(`docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md:246-247`,
landed commit `d824290`), read alongside the catalog's derived-index architecture pattern (#2 above)
as the *shape* to imitate for storage.

**Justification**: CARP-P1+P2 is the most recently-shipped, most structurally similar slice: a schema
contract (vocabulary/DTO shape) + a deterministic, no-model, no-network adapter that matches terms
against a derived text field (`catalog_retrieval.py:385-419`, `assertion_catalog.py:199`) and writes
results. Claim-term-indexing needs the same two halves (vocabulary/schema contract, then a
write-time extraction adapter) but **without** CARP's identity/authorization/reuse-decision/pagination
complexity (CARP-2.1, CARP-2.3 ≈ 3.5 of the 5 P2 points are auth/reuse-specific — not needed here).
Expect the term-index P1+P2 analog to land **below** 9 pts, offset by: (a) new schema surface on
canonical_claim/claim_ledger + a migration/backfill script for existing verified bundles (not present
in CARP, adds back ~1-2 pts), (b) if a persisted index table is added to `catalog_service.py`
(1985 lines), the H7 huge-file-touch multiplier applies (≥2× the naive point cost for that slice).
Net: **plausible range 6-10 pts** for a v1 write-time term-attachment slice (vocabulary + schema +
extraction + backfill), excluding any term-centric UI/CLI query surface (separate, additive slice).

## Build-vs-adapt recommendation

**Adapt, don't build from scratch.** Two existing primitives cover ~80% of the mechanism:
1. Reuse the CARP-style case-folded substring match (#1) as the extraction algorithm — swap the
   caller-supplied `required_terms` for a fixed, versioned vocabulary file, and swap "does the
   candidate's search_text contain this term" for "does this claim's statement contain this term" —
   run at write/extract time (not read time), satisfying the charter's deal-killer constraint directly.
2. Reuse the catalog's derived/rebuildable-index doctrine (#2) for *storage*: don't mutate
   `canonical_claim.schema.yaml`'s notion of authority — add the term list as a plain array field
   (analogous to how `search_text` is a derived, non-authoritative column) and optionally mirror it
   into a new `catalog_terms` (or extended `catalog_items`) sqlite table for term-centric queries,
   never as the sole store.
**Do not** build a BM25/embedding index or bring in an NLP model dependency for v1 — the vocabulary is
closed and small; deterministic substring/word-boundary matching is sufficient, matches existing
project precedent, and avoids new reproducibility risk. Usage-role tagging (finding/threshold/
measurement/background) should be scoped as a *separate*, explicitly-labeled deterministic rule set
(e.g., regex context windows around the matched term — "≥"/"<" nearby ⇒ threshold) rather than any
model inference, to keep the whole pipeline read-path-model-free per the charter's deal-killer.

## Confidence rationale

0.75. High confidence on internal findings — direct file/line citations for the CARP match, the
catalog's derived-index doctrine, and the confirmed absence of any term/tag field in the claim,
ledger, and writeback schemas and in the runs-viewer claim UI (exhaustive grep, not sampling).
Moderate uncertainty on: (a) MeatyWiki internals (external, unverified, model-knowledge only), (b)
the precise point delta for the H5 anchor (CARP's actual P1/P2 cost is plan-estimated, not yet
AAR-confirmed as "actual" — CARP P1+P2 landed in commit d824290 but no post-hoc AAR exists yet in
`docs/project_plans/aars/` to confirm actual vs. planned cost), and (c) external vocabulary/algorithm
claims are general ML/IR knowledge, not verified against current literature (no web access).
