---
schema_version: 2
doc_type: design_spec
title: "Research Provenance: Derived Graph/Vector Traversal (RPC-DF-4)"
status: draft
maturity: idea
created: 2026-07-28
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
related_documents:
  - docs/dev/architecture/research-provenance-contract-freeze.md
  - .claude/findings/research-provenance-continuity-findings.md
deferred_from: "Research Provenance Continuity (RPC) implementation plan — Deferred Items table, RPC-DF-4"
---

# Research Provenance: Derived Graph/Vector Traversal (RPC-DF-4)

## Context

RPC's Phase P5 read surfaces (`assertion_catalog.py`'s `inference_lineage`/`canonical_claim_lineage`
projections, `research_run_discovery.py`'s activity listing, `export_service.py`'s schema-1.8
provenance additions) deliver **bounded, exact lineage** — every projection is derived directly from
canonical origin/envelope/receipt/use/inference/canonical-claim records via explicit id references
(`origin_ref`, `envelope_ref`, `cited_ref`, `source_assertion_refs`, `inference_refs`), rebuilt
deterministically from disk (contract freeze §4.1 rule 5's facet-rebuild-parity requirement, and the
dev guide's manifest/pointer authority section). Nothing in the shipped surface builds a general-
purpose traversable graph structure or a vector/embedding-based similarity index over provenance
records.

## Why it was deferred

Per the plan's Deferred Items table: **"Graph/vector traversal is unnecessary for bounded lineage and
can leak membership."** Two distinct concerns:

1. **Unnecessary for what P5 actually needs.** Every lineage question RPC's shipped read surfaces
   answer today — "what does this assertion's inference/canonical-claim/report-use lineage look
   like," "what activities produced this evidence" — is answered exactly and completely by following
   the explicit id references the canonical records already carry. A general graph-traversal or
   vector-similarity layer would add infrastructure (a graph store, an embedding index, a
   reindexing/rebuild pipeline of its own) to solve a problem the bounded, exact approach already
   solves deterministically and byte-for-byte reproducibly (the same "delete and rebuild is
   byte-identical" resilience guarantee every RPC facet already provides).
2. **Can leak membership.** A graph or vector index, by construction, tends to expose *proximity* or
   *connectedness* signals — "this record is near/related to that one" — even when neither record's
   full content is disclosed. In a workspace-isolated, rights-gated system where a denied caller must
   see **zero candidate-derived signal** (contract freeze's repeated denial-shape requirement,
   `ResearchRunDiscovery.denied_payload`, `AssertionCatalog`'s own empty/denied contract), a
   similarity or graph-adjacency signal is itself a new disclosure channel that the current
   exact-reference model does not have: two records existing "near" each other in an index can leak
   information (e.g. "these two workspaces cite similar evidence") that neither record's own governed
   read path would ever expose on its own.

## Trigger for promotion

Per the plan's Deferred Items table: **"Measured need plus separate threat model."** Concretely,
before this is promotable:

1. A measured, real gap exists where bounded exact-reference lineage cannot answer a question that
   matters (e.g. "find provenance records similar to X across a large corpus" or "traverse an
   open-ended chain of relationships no explicit id reference already names") — not a speculative
   capability, a demonstrated need.
2. A separate, explicit threat model is written and accepted for the specific membership/proximity
   leakage risk named above — this is not covered by any existing RPC threat boundary (contract
   freeze §10) and must not be treated as pre-cleared by them.
3. Any proposed mechanism preserves the existing denial-shape guarantee: a denied or unauthorized
   caller must still see zero candidate-derived signal, including proximity/similarity signal, not
   merely zero raw record content.

## Sketch of the eventual shape

Not designed here. This spec deliberately proposes no graph schema, no embedding model, no index
technology, and no traversal API. It exists to record that graph/vector traversal was considered and
intentionally deferred — the current bounded, exact, rebuildable-facet model (contract freeze §4.1
rule 5, dev guide's manifest/pointer authority section) remains the frozen approach until both the
measured-need and threat-model triggers above are independently satisfied.
