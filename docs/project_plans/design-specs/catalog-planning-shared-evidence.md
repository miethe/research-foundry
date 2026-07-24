---
schema_version: 2
doc_type: design_spec
title: "Catalog Planning: Cross-Workspace/Public Shared Evidence Planning (CARP-DF-4)"
status: draft
maturity: idea
created: 2026-07-23
updated: 2026-07-23
feature_slug: catalog-assisted-research-planning
prd_ref: docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
open_questions:
  - "What federation model (if any) would let a caller in one workspace benefit from another workspace's catalog evidence without violating either workspace's rights and sensitivity boundaries?"
  - "Does a public evidence plan require a distinct, separately-versioned schema shape from the private per-workspace plan, or can the same schema be reused with a public-visibility flag?"
  - "Who is the security approver for any cross-workspace/public retrieval design, and what threat model must it clear before this is promotable?"
explored_alternatives: []
related_documents:
  - docs/dev/architecture/carp-contract-freeze.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
---

# Catalog Planning: Cross-Workspace/Public Shared Evidence Planning (CARP-DF-4)

## Status: Idea (Not Active)

This is Catalog-Assisted Research Planning's (CARP) deferred-item anchor for CARP-DF-4
("Cross-workspace/public evidence planning") per the CARP implementation plan's Deferred Items
Triage table and the CARP PRD's §12 Deferred Items. It is a placeholder for a future design record,
not a specification anyone should build against today.

CARP v1 is strictly private-first: identity precedes retrieval on every retrieval-bearing DTO
(`docs/dev/architecture/carp-contract-freeze.md` §2.1), and a two-workspace case is a required
fixture proving isolation (§7.3) — two independently valid `research_evidence_plan` instances scoped
to distinct `workspace_id` values, with no sharing between them.

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred (policy):** Cross-workspace/public planning violates CARP's private-first v1
boundary. Every part of the frozen contract — identity-before-retrieval, the denial guarantees, the
zero-candidate-derived-fields-on-denial rule — is built around a single owning workspace's
authorized view. Sharing evidence across workspaces, or exposing a plan publicly, is a fundamentally
different trust model that the current contract does not attempt to support and was never asked to.

## Trigger for Promotion

**Rights/federation design and security approval.** Promotion requires a separate rights/federation
design — covering how (or whether) evidence can cross a workspace boundary without leaking
candidate-derived signal to a party not authorized for the source workspace — plus explicit security
approval of that design. This is a materially different problem from CARP's per-workspace coverage
rule and should not be solved as an incremental extension of it without that review.

## Next Steps

When promoted, this document's owner should:

- Decide whether sharing happens at the evidence-plan level (a plan explicitly marked shareable) or
  at the underlying catalog level (a federation layer the adapter queries), since the two have very
  different blast radii if the design is wrong.
- Confirm how the existing denial guarantees (`carp-contract-freeze.md` §2.3 — zero
  candidate-derived fields on denial) extend to a cross-workspace read: a workspace that is denied
  access to shared evidence must get the same zeroed shape a same-workspace denial gets today.
- Re-validate the two-workspace isolation fixture (§7.3) against whatever federation model is
  proposed, to confirm it still proves isolation rather than assuming it.
