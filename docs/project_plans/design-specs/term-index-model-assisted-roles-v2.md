---
schema_version: 2
doc_type: design_spec
title: "Term Index: Model-Assisted Usage-Role Enrichment (PRD-OQ-2)"
description: "Deferred v2 anchor for a model-assisted usage-role classification pass over claim-term-indexing v1's rule-based classifier, gated by its own usage_role_model_version stamp."
status: draft
maturity: idea
created: 2026-07-25
updated: 2026-07-25
feature_slug: claim-term-indexing
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
open_questions:
  - "What miss-rate threshold on the rule-based classifier (regex context window + pediatric_cds structured-field keying) justifies the added complexity and non-determinism of a model pass?"
  - "What does a usage_role_model_version reproducibility-gating scheme look like — is it a per-claim stamp analogous to vocabulary_version, and does a version bump require re-running the classifier over the full historical corpus?"
  - "Does a model-assisted classification ever get to *override* the rule-based result, or only supplement it as a separate, distinctly-labeled field?"
explored_alternatives: []
related_documents:
  - docs/project_plans/design-specs/claim-term-indexing.md
  - docs/project_plans/PRDs/features/claim-term-indexing-v1.md
  - docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
---

# Term Index: Model-Assisted Usage-Role Enrichment (PRD-OQ-2)

## Status: Idea (Not Active)

This is claim-term-indexing v1's deferred-item anchor for **PRD-OQ-2**, per the implementation
plan's Deferred Items Triage Table and the feature PRD's open questions. It is a placeholder for a
future design record, not a specification anyone should build against today.

Claim-term-indexing v1 ships a **rule-based, zero-model** usage-role classifier
(`services/term_index.py::classify_usage_role`): a regex context window around a matched term
(comparative operators / numeric adjacency ⇒ `threshold`; bare mention ⇒ `background`), plus direct
`pediatric_cds` structured `threshold{value, units_ucum}` field keying where that structured
extraction already exists. No embedding call, no LLM call, anywhere in the module (D6, FR-3).

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred:** model-assisted usage-role enrichment is a *conditional-go* gate distinct from
v1's rule-based clearance — it introduces its own `usage_role_model_version` stamp, a reproducibility
question that does not exist for a pure function, and a non-determinism risk that v1's design
explicitly avoided (D6: "no model/embedding call anywhere"). It is not required for v1's go-ahead;
the rule-based classifier's accuracy on the real pediatric-CDS corpus has not yet been measured
against a model-assisted baseline.

## Trigger for Promotion

**A rule-based classifier miss-rate high enough to justify a model pass, with an explicit
reproducibility-gating proposal.** Promotion requires:

1. A measured miss-rate (false `background` where the term is actually a threshold mention, or vice
   versa) on a real, authorized corpus — this measurement does not exist today.
2. An explicit `usage_role_model_version` gating proposal: how the stamp is minted, whether a version
   bump forces a full-corpus re-classification, and how a model-assisted result is distinguished from
   a rule-based one in the `_term_index.usage_roles` shape (never silently merged into the same key
   without a distinguishing marker — this would repeat the "bare `usage_role` next to a real
   `pediatric_cds` value" readability hazard v1's design spec already flags).

## Next Steps

When promoted, this document's owner should:

- Author a full design record: model choice, prompt/extraction contract, `usage_role_model_version`
  stamping and reproducibility scheme, and how a model-assisted result composes with (or is clearly
  distinguished from) the existing rule-based `usage_roles` map.
- Confirm the model pass stays outside `SOURCE_ASSERTION_MATERIAL_FIELDS` and is never consulted by
  `rf verify` — the same non-authoritative posture v1 locked in (D2/D8) must not be weakened by adding
  a model in the loop.
- Re-run v1's guard tests (fingerprint byte-identity, `rf verify` byte-inertness) against any
  model-assisted addition before it ships.
