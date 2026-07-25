---
schema_version: 2
doc_type: design_spec
title: "Term Index: Strict-Schema Extension to canonical_claim / inference_record / source_assertion (PRD-OQ-3)"
description: "Deferred v2 anchor for extending _term_index onto the strict-family entities (canonical_claim, inference_record, source_assertion), gated on an explicit schema-version bump and backend-architect sign-off."
status: draft
maturity: idea
created: 2026-07-25
updated: 2026-07-25
feature_slug: claim-term-indexing
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
open_questions:
  - "What concrete v2 use case needs term data on an inference, a canonical claim, or a source card rather than a leaf claim?"
  - "Does extending _term_index onto a strict-family entity require a new schema-version bump per entity, or one shared bump across canonical_claim/inference_record/source_assertion?"
  - "Does backend-architect sign-off against adr-rights-entity-model.md's strictness discipline need to happen once per entity family, or once for the whole extension?"
explored_alternatives: []
related_documents:
  - docs/project_plans/design-specs/claim-term-indexing.md
  - docs/project_plans/PRDs/features/claim-term-indexing-v1.md
  - docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
  - docs/dev/architecture/adr-rights-entity-model.md
---

# Term Index: Strict-Schema Extension to `canonical_claim` / `inference_record` / `source_assertion` (PRD-OQ-3)

## Status: Idea (Not Active)

This is claim-term-indexing v1's deferred-item anchor for **PRD-OQ-3**, per the implementation
plan's Deferred Items Triage Table and the feature PRD's open questions. It is a placeholder for a
future design record, not a specification anyone should build against today.

Claim-term-indexing v1 is locked to **claims-only, open schemas only** by decision D1: `_term_index`
is attached to `claim_ledger.yaml` claim items and rolled up onto `report_frontmatter` — both
already-`additionalProperties: true` schemas where an additive derived key is zero-schema-contract
risk. The strict families (`canonical_claim`, `inference_record`, `source_assertion`) are untouched
by v1 by design.

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred:** extending `_term_index` onto a strict-family entity is not the same kind of
change as an additive key on an open schema. The strict families enforce a fixed, versioned contract
(`adr-rights-entity-model.md`'s strictness discipline) precisely so that no agent-writable path can
silently widen what those entities mean. Adding even a non-authoritative derived key there requires an
explicit schema-version bump and `backend-architect` sign-off — not a decision v1's scope permits
itself to make unilaterally. v1's own guard tests (fingerprint byte-identity, `rf verify`
byte-inertness) were written specifically to prove `_term_index` is invisible to the identity/verify
path on a claim; that proof does not automatically transfer to a strict-family entity without its own
review.

## Trigger for Promotion

**A concrete v2 use case needing term data on an inference, canonical claim, or source card, with
architect sign-off secured.** Promotion requires:

1. A named consumer need — e.g. a CARP retrieval improvement or a catalog surface that specifically
   needs term/usage-role data attached to an inference or source card rather than only the claims
   that reference them.
2. `backend-architect` sign-off on the schema-version bump against `adr-rights-entity-model.md`'s
   strictness discipline, before any implementation begins.

## Next Steps

When promoted, this document's owner should:

- Author a full design record naming the exact strict-family entity/entities in scope, the schema-
  version bump required, and whether the same rule-based classifier (`services/term_index.py`) or a
  new extraction path computes the term data for that entity.
- Re-verify the non-authoritative posture (D2/D8) holds for the new entity: `_term_index` (or its
  equivalent there) must stay outside any material-fields tuple for that entity's own identity/verify
  path, with a dedicated guard test mirroring v1's `test_assertion_identity_term_index_regression.py`.
- Confirm the extension does not reopen the flat-blob sensitivity question D3 closed for
  `catalog_terms` — any new per-entity term surface should carry its own sensitivity provenance, not
  a single computed-once value.
