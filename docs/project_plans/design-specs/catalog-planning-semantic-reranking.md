---
schema_version: 2
doc_type: design_spec
title: "Catalog Planning: Semantic/Vector Reranking (CARP-DF-1)"
status: draft
maturity: idea
created: 2026-07-23
updated: 2026-07-23
feature_slug: catalog-assisted-research-planning
prd_ref: docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
open_questions:
  - "What is an acceptable lexical-miss rate on a real corpus that would justify the added complexity and threat-model exposure of a private vector index?"
  - "Would a private-index threat model change the trust boundary of the reusable assertion ledger (RAL), and who must approve that change?"
  - "Does semantic reranking operate on the same authorized/eligible candidate set the lexical rule already produces, or does it require a separate index that must independently enforce workspace/rights isolation?"
explored_alternatives: []
related_documents:
  - docs/dev/architecture/carp-contract-freeze.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
---

# Catalog Planning: Semantic/Vector Reranking (CARP-DF-1)

## Status: Idea (Not Active)

This is Catalog-Assisted Research Planning's (CARP) deferred-item anchor for CARP-DF-1
("Semantic/vector reranking") per the CARP implementation plan's Deferred Items Triage table and
the CARP PRD's §12 Deferred Items. It is a placeholder for a future design record, not a
specification anyone should build against today.

CARP v1's coverage rule (`docs/dev/architecture/carp-contract-freeze.md` §3.1, condition 1) uses a
conservative, case-folded, whole-required-term substring match against a candidate's catalog
`search_text` — a literal lexical match, never a semantic or vector similarity comparison.

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred:** Vector/semantic reranking is excluded by the Reusable Assertion Ledger (RAL)
and unnecessary for a conservative lexical fallback. RAL v1 explicitly excludes vector indexes, and
CARP's coverage rule is deliberately conservative — it is designed to under-claim coverage
(resolving to `residual` on any uncertainty, per the freeze doc's six-condition rule) rather than
risk a semantic match that cannot be verified as precisely as a literal substring check. Adding a
vector/semantic layer now would introduce a new private-index surface and a new class of
"approximately relevant" matches into a coverage rule whose entire design intent in v1 is exact,
auditable, deterministic matching.

## Trigger for Promotion

**Measured lexical miss rate plus an approved private-index threat model.** Promotion requires both:

1. A measured rate of `lexical_miss` residual questions on a real, authorized corpus, high enough to
   justify additional complexity (this measurement does not exist today — see the CARP guide's
   honesty constraint on real-corpus claims).
2. A threat model for a private vector/semantic index — covering workspace isolation, rights
   propagation, and whether embeddings themselves could leak sensitive content across the same
   boundaries the lexical rule respects — reviewed and approved before any implementation begins.

## Next Steps

When promoted, this document's owner should:

- Author a full design record (design assumptions, index architecture, workspace/rights isolation
  proof, coverage-rule interaction) as its own spec, or expand this one in place.
- Confirm whether semantic reranking augments condition 1 (lexical match) as an additional signal,
  or replaces it — the frozen contract's conservative intent should not be weakened without an
  explicit contract-freeze cycle (`carp-contract-freeze.md`'s own re-litigation rule).
- Re-run the H3 coverage scenario matrix (`carp-contract-freeze.md` §3.5) against any reranking
  change to confirm the terminal-state/residual-reason partition still holds.
