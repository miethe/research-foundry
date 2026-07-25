---
schema_version: 2
doc_type: design_spec
title: "Controlled Vocabulary Import — MeSH / UMLS / LOINC (PRD-OQ-1 residual)"
description: "Deferred v2 anchor for sourcing the term-index vocabulary from a controlled medical vocabulary (MeSH/UMLS/LOINC) once the hand-maintained vocab/*.yaml list outgrows itself."
status: draft
maturity: idea
created: 2026-07-25
updated: 2026-07-25
feature_slug: claim-term-indexing
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
open_questions:
  - "Which controlled vocabulary (MeSH, UMLS, LOINC, or a combination) best covers the pediatric-CDS domain without requiring a licensed API key (UMLS requires a UTS account)?"
  - "Does a controlled-vocabulary import replace vocab/pediatric-terms.yaml wholesale, or layer on top of it as an additional, separately-versioned vocabulary source?"
  - "What is the actual size of the hand-maintained list at the point this triggers, and does the D5 ~200-term threshold still hold as the right promotion signal?"
explored_alternatives: []
related_documents:
  - docs/project_plans/design-specs/claim-term-indexing.md
  - docs/project_plans/PRDs/features/claim-term-indexing-v1.md
  - docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
---

# Controlled Vocabulary Import — MeSH / UMLS / LOINC (PRD-OQ-1 residual)

## Status: Idea (Not Active)

This is claim-term-indexing v1's deferred-item anchor for the **residual portion of PRD-OQ-1**, per
the implementation plan's Deferred Items Triage Table. It is a placeholder for a future design
record, not a specification anyone should build against today.

Claim-term-indexing v1 sources its vocabulary from a single hand-maintained file,
`vocab/pediatric-terms.yaml` — a canonical term ID mapped to a list of case-insensitive surface-form
aliases, jsonschema-validated at load time against `schemas/term_vocab.schema.yaml`. Decision D4
locks this as hand-maintained-only for v1; no Aho-Corasick dependency and no external vocabulary
import is in scope (D5).

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred:** controlled-vocabulary sourcing (MeSH/UMLS/LOINC) beyond the hand-maintained list
is backlog, not blocking. D4 explicitly locks the hand-maintained-only approach for v1's initial
pediatric-CDS domain, where the term set (CBC, hemoglobin, hematocrit, ferritin, anemia, iron
deficiency, and similar) is small and stable enough that a curated list is both accurate and easy to
audit. A controlled-vocabulary import adds licensing, versioning, and mapping-fidelity concerns (a
MeSH/UMLS/LOINC concept ID does not map 1:1 onto this feature's flat canonical-term-ID shape) that are
not worth taking on before the hand-maintained approach actually runs out of room.

## Trigger for Promotion

**The hand-maintained vocabulary list outgrows itself.** Per D4/D5's own stated trigger, this is
roughly when `vocab/pediatric-terms.yaml` (or its per-domain siblings, if the feature expands beyond
pediatric anemia/CBC) approaches **~200 terms** and hand-curation of surface-form aliases becomes a
maintenance burden rather than a one-time authoring pass.

## Next Steps

When promoted, this document's owner should:

- Author a full design record: which controlled vocabulary (or combination) to import, how a
  MeSH/UMLS/LOINC concept maps onto this feature's flat `canonical_term_id -> [aliases]` shape, and
  whether `vocabulary_version` stamping needs to change to also carry a source-vocabulary version
  (e.g. a UMLS release date).
- Confirm the import path stays offline/deterministic at claim-map write time — no live API call
  during indexing, consistent with D6's zero-model-call invariant for this module.
- Decide whether the hand-maintained file is retired, kept as a project-specific overlay on top of
  the imported vocabulary, or merged — and how `rf term-index backfill` behaves across that
  transition for already-indexed claims.
