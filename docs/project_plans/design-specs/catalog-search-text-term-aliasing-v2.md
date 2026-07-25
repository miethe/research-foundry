---
schema_version: 2
doc_type: design_spec
title: "Catalog search_text Term Aliasing (Design-Spec OQ-B)"
description: "Deferred v2 anchor for aliasing canonical vocabulary terms into catalog_items.search_text for FTS5 substring recall (e.g. \"cbc\" -> \"complete blood count\"); blocked on the sensitivity-leak risk catalog_terms's per-row sensitivity_rank (D3) was built to close."
status: draft
maturity: idea
created: 2026-07-25
updated: 2026-07-25
feature_slug: claim-term-indexing
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
open_questions:
  - "Is there a demonstrated recall gap where catalog_terms facet search alone is insufficient and FTS5 substring search on aliased text is specifically requested?"
  - "If aliasing proceeds, can search_text carry per-row sensitivity provenance at all, or does its current architecture (search_service.py:541-563, computed once per catalog_items row) structurally preclude the per-row sensitivity_rank discipline D3 established?"
  - "Would a redesigned search_text (e.g. multiple sensitivity-tiered copies, or a join-time filter instead of a precomputed blob) close the leak without abandoning FTS5 substring search entirely?"
explored_alternatives:
  - "catalog_terms as the only new query surface (v1 default, per this feature's D3/FR-11) — ships in v1; this document is the alternative that was NOT taken."
related_documents:
  - docs/project_plans/design-specs/claim-term-indexing.md
  - docs/project_plans/PRDs/features/claim-term-indexing-v1.md
  - docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
---

# Catalog `search_text` Term Aliasing (Design-Spec OQ-B)

## Status: Idea (Not Active)

This is claim-term-indexing v1's deferred-item anchor for **design-spec OQ-B**, per the
implementation plan's Deferred Items Triage Table. It is a placeholder for a future design record,
not a specification anyone should build against today.

Claim-term-indexing v1 ships `catalog_terms(catalog_item_id, term, role, run_id, sensitivity_rank)` —
a dedicated join table, with **per-row** `sensitivity_rank` carried from the claim/evidence point each
row derives from — as the **only** new query surface for term/usage-role lookup (D3, FR-11). It does
**not** alias canonical vocabulary terms (e.g. `cbc` -> `complete blood count`) into the existing flat
`search_text` field on `catalog_items`, which powers today's FTS5 substring search.

## Why this feature defers it (plan Deferred Items Triage) — the sensitivity-leak risk, named plainly

**This is a scope-cut, not a backlog item, and the reason is a security property, not a nice-to-have.**

`catalog_items.search_text` is a single flat blob, computed once per row (`catalog_service.py:541-563`,
with sensitivity redaction applied via `_redact_evidence_points` at `catalog_service.py:1215-1234`).
That "compute once, at the most-permissive tier" architecture is exactly the failure mode
claim-term-indexing v1's own `catalog_terms` design was built to avoid: TASK-2.3's acceptance criteria
require that a fixture item with evidence points at two *different* sensitivity ranks produce **two
distinct-ranked rows, not one blob at the max tier**. Aliasing canonical terms into `search_text`
would reintroduce precisely that flattening — a term that only appears in a `personal`- or
`client_sensitive`-ranked evidence point would sit in the same flat, single-sensitivity `search_text`
string as everything else on that catalog item, and a lower-threshold reader's FTS5 substring query
could recover its presence indirectly (via a term-aliased hit) even though the direct `catalog_terms`
row for that term is correctly gated above their threshold. In other words: fixing the leak in one
query surface (`catalog_terms`, via D3) while reopening the same leak in a second query surface
(`search_text`, via aliasing) is a net-zero security outcome dressed as a recall improvement.

## Trigger for Promotion

**A demonstrated recall gap, specifically requesting FTS5 substring search on aliased text.**
Promotion requires both:

1. A measured case where `catalog_terms` facet search (`--term`/`--role`, exact canonical-ID match)
   is insufficient — e.g. an operator searches free-text `q=complete blood count` and expects it to
   surface items that only carry the canonical term `cbc` in `catalog_terms`, and the facet-only
   surface does not serve that need.
2. Either a redesigned `search_text` architecture that can carry the same per-row sensitivity
   provenance `catalog_terms` already has (not a proven approach today — see the open questions
   above), or an explicit accepted-risk sign-off that revisits and supersedes D3's rationale.

## Next Steps

When promoted, this document's owner should:

- Not treat this as "just add aliases to `search_text`." The sensitivity-leak risk above must be
  closed first, structurally — not documented and accepted, unless that acceptance itself goes through
  the same review rigor D3's original decision did.
- Evaluate whether a join-time filtered search (FTS5 query joined against `catalog_terms` at the
  correct per-row sensitivity threshold, rather than a precomputed blob) achieves the same recall
  without the leak.
- Re-run the TASK-2.7-equivalent redaction-parity test (0 terms exposed above the requesting read's
  sensitivity threshold, at every tested tier) against whatever design is chosen before it ships.
