---
schema_version: 2
doc_type: exploration_charter
title: "Source Metadata Capture & Provenance-Preserving Propagation — Exploration
  Charter"
status: completed
created: 2026-08-02
feature_slug: source-metadata-propagation
timebox_days: 3
hypothesis: "We believe capturing rich source metadata plus third-party assertions
  ABOUT sources, and propagating them as queryable attributes up to claims and reports,
  is worth building because RF records quality signals write-only today and discards
  all of them at the claim boundary — leaving evidence unfilterable by anything except
  its own text."
deal_killer: "If propagating source attributes to claims cannot be made deterministic
  and fully recomputable from files alone — i.e. it requires a model call on the read
  path, or makes the derived catalog DB authoritative — abandon."
investigation_legs:
- id: tech
  question: "Can rich source metadata and third-party assertions-about-sources be
    modeled and propagated to claims/reports deterministically inside RF's existing
    file-canonical architecture, without a model call on the read path? Which entity
    owns them: source_card.schema.yaml, the Reusable Assertion Ledger, or a new attribution
    entity?"
  assigned_to: spike-writer
- id: risk
  question: What breaks? Assess schema-migration blast radius on the 
    verifier-consumed source card, the 7 committed pediatric bundles and all 
    cards born source_rank:unknown under a no-backfill regime, third-party 
    ToS/licensing for cached rating and citation data, staleness of cached 
    third-party assertions, and the governance risk of a rating being mistaken 
    for an RF-authored fact.
  assigned_to: data-layer-expert
- id: prior-art
  question: What existing standards and internal precedents cover 
    assertions-about-sources with their own provenance, and attribute 
    propagation up an evidence chain? Assess PROV-O, W3C Web Annotation, 
    nanopublications, RO-Crate, DataCite/Crossref/OpenAlex/Semantic Scholar 
    APIs, SPDX-style attribution, and internally the 
    source_assertion.schema.yaml Reusable Assertion Ledger + the landed 
    rights-entity-model. Recommend the H5 anchor and a build-vs-adopt call.
  assigned_to: search-specialist
verdict_criteria:
  go:
  - Technical leg reports feasible or feasible-with-constraints at confidence >=
    0.7 with a named owning entity and a deterministic propagation mechanism
  - 'Deal-killer refuted: propagation is recomputable from files with no read-path
    model call and no authoritative DB'
  - Risk leg produces a concrete migration path that leaves the 7 committed 
    pediatric bundles verifying
  no_go:
  - 'Deal-killer confirmed: no deterministic file-only propagation exists'
  - Technical leg reports infeasibility at confidence >= 0.8
  - Risk leg finds the source-card schema change breaks rf verify for existing 
    bundles with no additive path
  conditional:
  - Propagation design is sound but third-party assertion sourcing 
    (ratings/backlinks) is blocked on licensing or an unbuilt fetch path — split
    into an additive metadata-capture phase now and defer third-party ingestion 
    behind a named precondition
  - Owning-entity choice depends on an unresolved question about the Reusable 
    Assertion Ledger's attestation lifecycle
verdict: conditional
verdict_rationale: "Propagation design is sound and the deal-killer was refuted (deterministic, file-recomputable, no read-path model call), but third-party assertion sourcing is gated on per-provider license verification for bundle redistribution — so scope Phases A+B now and defer C."
output_artifacts:
- docs/project_plans/exploration/source-metadata-propagation/spikes/tech-findings.md
- docs/project_plans/exploration/source-metadata-propagation/spikes/risk-findings.md
- docs/project_plans/exploration/source-metadata-propagation/spikes/prior-art-findings.md
- docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-feasibility-brief.md
- docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-proposed-adr.md
updated: '2026-08-02'
---

# Source Metadata Capture & Provenance-Preserving Propagation — Exploration Charter

## Hypothesis Context

RF's enforcement today is traceability-only: `rf verify` checks that each material claim resolves to
≥1 existing source card carrying a verbatim quote anchor, and that non-supported claims are labeled.
Quality is captured but inert. `trust.source_rank` is a 4-value enum (`primary|secondary|tertiary|
unknown`) that the Python ingest path hardcodes to `unknown` and never upgrades; `authority_score()`
exists but has no call site in the pipeline; `rf_deep_reader` is instructed to emit a
`credibility_score` that appears in no schema and is read by no code. At the claim boundary, a claim
references only `{source_card_id, evidence_id, relation, locator}` — every attribute of the source
is dropped, so no report or query can filter, sort, or triage evidence by anything but its text.

The operator ask is two-part and the second part is the harder one: capture *all* available source
metadata at ingest (DOI, PMID, authors, publisher, version, inbound citations/backlinks), **and**
carry third-party judgments about a source (ratings, rankings, citation counts) with their own
provenance — asserted *by whom*, retrieved *when*, under *what terms* — so they are never mistaken
for RF-authored fact. Adjacent precedent exists internally: `source_assertion.schema.yaml` already
models an assertion with `input_refs` and a `contribution` vocabulary, and the landed
rights-entity-model established the pattern of a separate governance entity over the evidence chain.

---

## Investigation Legs

### Leg: tech — Technical Feasibility & Owning Entity

**Question**: see frontmatter.
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/source-metadata-propagation/spikes/tech-findings.md`

- Where propagation can happen deterministically: claim-map write time (cf. the landed `_term_index`
  write-time precedent), catalog derivation, bundle export, or report render.
- Whether `additionalProperties: true` on the source card makes capture additive and migration-free.
- Whether a third-party rating belongs as a nested block on the card, a separate assertion record, or
  a new entity — and what the aggregation semantics are when a claim cites N cards with conflicting
  attributes (min? max? set-union? no aggregation at all, just carry the set?).
- Constraint check against the AOS eight: files canonical, DB derived, no model on the read path.

### Leg: risk — Migration, Licensing & Governance Blast Radius

**Question**: see frontmatter.
**Assigned to**: `data-layer-expert`
**Expected output**: `docs/project_plans/exploration/source-metadata-propagation/spikes/risk-findings.md`

- The no-backfill precedent (AssertionRegistry) and what forward-only means for existing cards.
- `rf verify` exit-code precedence and whether any new field can reach `SCHEMA(2)`/`UNSUPPORTED(4)`.
- Third-party terms: which citation/rating sources permit caching and redistribution in a bundle.
- The governance hazard: an agent-writable path minting a rating that reads as RF-attested — cf. the
  existing `no_agent_cleared_rights_value` guard rule.

### Leg: prior-art — Standards & Internal Precedent

**Question**: see frontmatter.
**Assigned to**: `search-specialist`
**Expected output**: `docs/project_plans/exploration/source-metadata-propagation/spikes/prior-art-findings.md`

- External: PROV-O, W3C Web Annotation, nanopublications, RO-Crate, DataCite/Crossref/OpenAlex/
  Semantic Scholar, SPDX attribution.
- Internal: `source_assertion.schema.yaml`, rights-entity-model, `_term_index`, catalog derivation.
- Deliverable: the single best H5 anchor + an explicit adopt-vs-build recommendation.

---

## Verdict Criteria Narrative

**Go** if a named entity owns third-party assertions with their own provenance, propagation to claims
is deterministic and file-recomputable, and existing bundles keep verifying under an additive change.
**No-go** if propagation cannot avoid a read-path model call or an authoritative DB, or if the schema
change cannot be made additive.
**Conditional** if the propagation design holds but third-party *ingestion* is blocked on licensing or
an unbuilt fetch path — then ship metadata capture + propagation now and defer third-party assertion
sourcing behind a named precondition.

---

## Out of Scope

- Reviving `authority_score()` as a ranking input, or any change to search-router result ordering.
- Implementing corroboration/multi-source thresholds on claims (a separate, larger question — the
  spec's unimplemented "two independent sources" rule is explicitly *not* this exploration).
- Any bibliometric *judgment* authored by RF itself (computing our own impact score). This
  exploration covers carrying third-party judgments with provenance, not minting new ones.
- Retroactive re-rating of the 7 committed pediatric bundles.
- runs-viewer UI work to surface the new attributes.

---

## Citations / Prior Art

- `schemas/source_card.schema.yaml` — `trust.source_rank` enum; `additionalProperties: true`.
- `src/research_foundry/services/source_cards.py:331-338` — hardcoded `source_rank: "unknown"`.
- `src/research_foundry/services/search_router/ranking.py:19-43` — weight table; `authority_score()` uncalled.
- `schemas/claim_ledger.schema.yaml:54-70` — `sources[]` shape; no attribute carry-through.
- `schemas/source_assertion.schema.yaml:106-152, 404-422` — evidence taxonomy; `input_refs` minItems 2.
- `docs/dev/architecture/adr-rights-entity-model.md` — separate-governance-entity precedent.
- `docs/project_plans/design-specs/research_foundry_search_router_spec.md` §15.3–15.4 — unimplemented rules.

---

## Notes

- 2026-08-02: Charter scaffolded. `value` leg deliberately skipped — single-operator internal control
  plane; the operator stated the need directly, so desirability is not the open question.
