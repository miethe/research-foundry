---
schema_version: 2
doc_type: exploration_charter
title: "Claim Term Indexing — Exploration Charter"
status: concluded
created: 2026-07-23
feature_slug: claim-term-indexing
timebox_days: 3
hypothesis: "We believe a deterministic, data-derived term index over RF entities
  (claims first, then inferences/reports/source cards) — each entity carrying the
  vocabulary terms it contains plus a usage-role annotation (finding, threshold, measurement,
  background) — is worth building because it enables cheap term-based entity search,
  term-centric analysis views (e.g. all claims touching CBC), and topic-driven research
  planning, without adding model calls to the read path."
deal_killer: "If the term/usage index cannot be produced as reproducible derived data
  at extract/write time — i.e., it would require a model call on the read/render path,
  or would let agent-writable paths mint authority-bearing annotations that alter
  claim verification status — abandon."
investigation_legs:
- id: tech
  question: Where does a term index attach in RF's entity model and file layout 
    (claim ledger, source cards, inferences, reports), and which rf CLI stages 
    (extract, verify, export, serve, catalog, search) must change to compute, 
    store, and query it deterministically? Can the usage-role pass (how a term 
    is used) stay off the read path?
  assigned_to: ica-executor
- id: priorart
  question: What internal prior art (search-router MVP rf search/fetch, CARP 
    catalog, MeatyWiki semantic/vector search, runs-viewer assertion ledger) and
    external patterns (controlled vocabularies like MeSH/UMLS/LOINC, BM25 vs 
    embedding retrieval, deterministic NER/term extraction) exist, and what is 
    the best build-vs-adapt anchor?
  assigned_to: ica-executor
- id: risk
  question: 'What are the top risks: migration of existing verified bundles (7 pediatric-CDS
    runs), sensitivity/redaction of derived term indexes at export, rights-governance
    guard interactions (no_agent_cleared_rights_value), reproducibility of embedding-derived
    usage roles, and rf verify gate interactions? Confirm or refute the declared deal_killer.'
  assigned_to: ica-executor
- id: value
  question: Does the pediatric-anemia-site evidence-foundry use case 
    (term-centric views over WBC/CBC/ferritin claims) plus RF-general 
    search/report-driving value justify the build? What do users do today 
    instead (counterfactual)?
  assigned_to: ica-executor
verdict_criteria:
  go:
  - tech and risk legs report confidence >= 0.7
  - Deal-killer condition not triggered; a deterministic write-time indexing 
    design is identified
  no_go:
  - Deal-killer condition triggered (index requires read-path model calls or 
    non-reproducible authority-bearing data)
  - tech leg reports infeasibility with confidence >= 0.8
  conditional:
  - Open question(s) remain resolvable by a specific named subsequent 
    investigation (e.g. vocabulary-source decision or usage-role model choice)
verdict: go
verdict_rationale: 'All four legs complete (tech 0.82, priorart 0.75, risk 0.78, value
  0.72). Go criteria met: tech and risk >= 0.7; deal-killer not triggered — a deterministic
  write-time index design (versioned vocabulary + CARP-adapted case-folded matching,
  non-authoritative _term_index namespace) was identified and empirically verified
  inert to rf verify (byte-identical output before/after injection on a real 87-claim
  pediatric-CDS ledger). Value corroborated by CARP having already hand-rolled a weaker
  per-question version (required_terms). H5 anchor: CARP P1+P2 (9 pts), estimate 8-13
  pts, Tier 2.'
output_artifacts:
- docs/project_plans/exploration/claim-term-indexing/spikes/tech-findings.md
- docs/project_plans/exploration/claim-term-indexing/spikes/priorart-findings.md
- docs/project_plans/exploration/claim-term-indexing/spikes/risk-findings.md
- docs/project_plans/exploration/claim-term-indexing/spikes/value-findings.md
- docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-feasibility-brief.md
- docs/project_plans/design-specs/claim-term-indexing.md
updated: '2026-07-23'
---

# Claim Term Indexing — Exploration Charter

## Hypothesis Context

Operator idea (2026-07-23): index the contents of claims by pulling out key terms from a relevant vocabulary (pediatric use case: WBC, CBC, ferritin, …), attach that index to every claim, and optionally annotate HOW each term is used (e.g. a finding that could drive new guidelines) — purely data-derived, no inferences. Extend the same indexing to all entity levels (inferences, reports). Payoffs: (1) cheap term-based search across entities, (2) term-centric views ("show all claims associated with CBC"), (3) powering future research/reports around a topic. Adjacent evidence: the CARP catalog (C3) already assumes topic-shaped reuse of prior research; the search-router MVP built query-shaped discovery but nothing indexes RF's own corpus.

## Investigation Legs

Each leg deposits `docs/project_plans/exploration/claim-term-indexing/spikes/[id]-findings.md` with a `confidence:` frontmatter field (0.0–1.0). Legs run in parallel on the ICA lane (`claude-sonnet-5[1m]`) per delegation-router RoutingRecords; see audit log.

## Verdict Criteria Narrative

**Go** if: a deterministic write-time index design lands with enumerated integration points, migration of existing bundles is tractable, and the pediatric evidence-foundry use case is corroborated.
**No-go** if: indexing can't be reproducible derived data (deal-killer), or the entity-model touch surface makes it infeasible.
**Conditional** if: the core index is feasible but a named decision (vocabulary source, usage-role mechanism) needs its own spike first.

## Out of Scope

- Implementing any indexing code in this exploration
- Full semantic search / RAG over evidence bundles (only assessed as prior art)
- pediatric-anemia-site repo changes (RF-side capability only)

## Citations / Prior Art

- `docs/projects/research-foundry/` MVP spec; search-router MVP (memory: offline-only); CARP C3 catalog contract (d824290); MeatyWiki semantic search (external subsystem)

## Notes

<!-- Append timestamped entries as legs complete. -->
