---
schema_version: 2
doc_type: design_spec
title: "Catalog Planning: Canonical-Claim Coverage (CARP-DF-3)"
status: draft
maturity: idea
created: 2026-07-23
updated: 2026-07-23
feature_slug: catalog-assisted-research-planning
prd_ref: docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
open_questions:
  - "Once canonical claim merging is qualified and authorized, does CARP's coverage rule evaluate against canonical claims in addition to (or instead of) individual source assertions?"
  - "Would a canonical claim's aggregation of multiple source assertions change the six-condition coverage rule's per-candidate semantics (e.g. contradiction, version pinning) or require new conditions?"
  - "Who authorizes canonical claim activation, and is that authorization CARP-scoped or inherited wholesale from the owning canonical-claim feature?"
explored_alternatives: []
related_documents:
  - docs/dev/architecture/carp-contract-freeze.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
---

# Catalog Planning: Canonical-Claim Coverage (CARP-DF-3)

## Status: Idea (Not Active)

This is Catalog-Assisted Research Planning's (CARP) deferred-item anchor for CARP-DF-3
("Canonical-claim coverage") per the CARP implementation plan's Deferred Items Triage table and the
CARP PRD's §12 Deferred Items. It is a placeholder for a future design record, not a specification
anyone should build against today.

CARP v1's coverage rule (`docs/dev/architecture/carp-contract-freeze.md` §3.1) evaluates individual
source assertions only. It has no dependency on, and does not evaluate against, any canonical-claim
merging layer.

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred (dependency-blocked):** Canonical-claim coverage depends on qualified merge safety
and activation — capabilities that are not authorized or built today. Canonical claim merging
remains optional in the wider assertion-ledger model, and individual source assertions are
sufficient for CARP v1's coverage rule. There is nothing for CARP to evaluate against a canonical
claim until that merging capability exists, is proven safe, and is activated by whichever feature
owns it.

## Trigger for Promotion

**Canonical merge qualified and authorized.** Promotion requires the owning canonical-claim feature
to have qualified merge safety and to have authorized canonical-claim activation, independent of
CARP. CARP-DF-3 only becomes actionable once that upstream dependency clears — this document does
not itself design or authorize canonical merging.

## Next Steps

When promoted (i.e. once canonical merge is qualified and authorized elsewhere), this document's
owner should:

- Determine whether CARP's six-condition coverage rule needs new conditions to reason about a
  canonical claim's aggregated source set, or whether it can treat a canonical claim as a single
  candidate with the same six conditions applied to its own fields.
- Confirm how contradiction (condition 5) and version pinning (condition 6) behave when the
  candidate under evaluation is itself an aggregation of multiple source assertions that could
  individually drift.
- Re-run the H3 coverage scenario matrix (`carp-contract-freeze.md` §3.5) with canonical-claim
  candidates included, to confirm the terminal-state/residual-reason partition still holds.
