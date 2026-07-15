---
title: Reusable Assertion Ledger Public Rights and Promotion Spec
doc_type: design_spec
schema_version: 2
status: deferred
maturity: shaping
created: 2026-07-15
updated: 2026-07-15
feature_slug: reusable-assertion-ledger
deferred_from: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-9-docs-private-rollout.md
---

# Reusable Assertion Ledger Public Rights and Promotion Spec

## Decision

Public rights promotion is deferred. P8 does not publish assertions, create a
public catalog, infer rights from metadata, enable canonical claims, or write
to any external system. Private source assertions and run evidence remain the
only implemented authority.

## Required design before any implementation

A future promotion flow must require an attributable human decision for each
source edition/passage/assertion version, record jurisdiction and license scope,
preserve revocation and expiry, isolate derived inference from source rights,
and provide an auditable public-removal path that blocks reuse before cache or
index reconciliation.

## Deal killers

- Inferred, inherited, blanket, or model-generated public rights instead of a
  versioned, attributable grant for the exact source material.
- Promotion of an assertion when any bound edition, passage, rights scope,
  sensitivity review, or license term is missing, stale, disputed, or revoked.
- Public records, caches, search snippets, exports, or writebacks that cannot
  remove revoked material and prove the removal boundary.
- Canonical grouping that turns a private source assertion into a public claim
  by association or permits a public derivative to reveal private provenance.

## Future SPIKE gates

1. Legal/privacy review of rights vocabulary, jurisdiction, provenance, consent,
   revocation, derivative-work handling, and retention obligations.
2. Synthetic promotion/revocation prototype proving default denial, exact
   version binding, no-private-provenance disclosure, and bounded cache purge.
3. Owner-authorized review of public presentation, deletion SLA, incident
   response, and external-writeback contracts before any implementation.
4. Independent security and accessibility review of the exact public candidate;
   no rollout follows from a design-spec approval alone.
