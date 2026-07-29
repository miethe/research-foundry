---
schema_version: 2
doc_type: design_spec
title: "Research Provenance: Public Provenance Export (RPC-DF-3)"
status: draft
maturity: idea
created: 2026-07-28
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
related_documents:
  - docs/dev/architecture/research-provenance-contract-freeze.md
  - .claude/findings/research-provenance-continuity-findings.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md
deferred_from: "Research Provenance Continuity (RPC) implementation plan — Deferred Items table, RPC-DF-3"
---

# Research Provenance: Public Provenance Export (RPC-DF-3)

## Context

RPC's governed read surfaces (Phase P5 — `research_run_discovery.py`, `assertion_catalog.py`'s
`inference_lineage`/`canonical_claim_lineage` projections, `export_service.py`'s schema-1.8
provenance/lineage additions, `api/routers/assertions.py`'s `/assertions/activities*` routes) are all
**workspace-scoped and identity-gated** — every read requires a resolved `AuthIdentity` with a
`workspace_id`, and a missing/denied/cross-workspace caller gets the same uninformative, no-existence-
leak shape (`ResearchRunDiscovery.denied_payload`, the dev guide's Governance boundaries section).
Nothing in the shipped P1-P6 surface defines what a **public**, unauthenticated, cross-workspace
export of provenance data would look like — that question is out of scope by design.

## Why it was deferred

Public provenance export is a **rights and policy** question before it is an engineering one. The
provenance records this feature governs (`provenance_origin`, `research_run_envelope`,
`search_activity_receipt`, `report_assertion_use`, `inference_record`, `canonical_claim`) can carry
sensitive facts — a locator, a producer identity, an AOS project/intent reference, a rights snapshot
(`assertion_report_use.py`'s `normalize_rights_snapshot`/`fold_rights_snapshots_most_restrictive`).
Exporting any of this to a public, unauthenticated consumer without an explicit rights-promotion
policy would bypass every workspace/rights gate this feature and its siblings (the Reusable Assertion
Ledger, its own public-rights-promotion deferred spec) were built to enforce.

**DI-1 is BLOCKED** (`.claude/findings/research-provenance-continuity-findings.md`, standing directive
3): no deployment-enabling flag flip, gate clearing, or Mode-D self-sign is authorized by any RPC
phase, and that constraint applies with full force to public export — a public-export feature is, by
definition, a multi-tenant/adversarial-exposure surface, exactly the class DI-1 exists to gate.

## Trigger for promotion

Per the plan's Deferred Items table: **"Public-rights approval and threat model accepted."**
Concretely, before this is promotable:

1. An explicit rights-promotion policy exists and is approved — naming exactly which provenance
   fields (if any) are safe to expose publicly, and which (locator, producer identity, AOS refs,
   rights snapshots) must remain workspace-scoped regardless of "public" framing.
2. A threat model for this specific export path is written and accepted, covering at minimum:
   cross-tenant enumeration, existence-leak via timing or error-shape, and rights-snapshot disclosure.
3. DI-1's adversarial-multi-tenant re-audit (the standing pre-multi-tenant-deploy gate this findings
   doc and the broader public-multi-user release plan both name) is satisfied for this specific
   surface — a public export route is exactly the kind of surface that gate exists to catch.
4. Any deployment-enabling flag this feature would need remains `False` by default, per this
   document's own constraint and every prior RPC phase's DI-1 posture — this design spec does not,
   and must not, propose flipping one.

## Sketch of the eventual shape

Not designed here. If promoted, the design would need to specify (not sketched further in this
document):

- A separate, explicitly-named public-export projection distinct from the existing governed read
  projections — never a mode flag on `research_run_discovery.py`/`assertion_catalog.py`'s existing
  identity-gated methods, to avoid a single code path having to safely serve two very different trust
  levels.
- Which fields, if any, from `provenance_origin`/`research_run_envelope`/`search_activity_receipt`/
  `report_assertion_use`/`inference_record`/`canonical_claim` are rights-cleared for public disclosure
  — likely a strict allowlist, not a denylist, mirroring this codebase's existing fail-closed posture
  (contract freeze's repeated "denial reveals nothing" pattern).
- How the existing rights-promotion mechanism (the Reusable Assertion Ledger's own deferred public
  rights-promotion spec, `reusable-assertion-ledger-public-rights-promotion.md`) composes with
  RPC's provenance layer, rather than inventing a second, parallel rights-promotion concept.

This spec proposes no schema, no export format, and no policy. It exists to record that public export
was considered and intentionally deferred pending rights and security review.
