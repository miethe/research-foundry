---
schema_version: 2
doc_type: design_spec
title: "Catalog Planning: Adaptive/Model-Generated Query Decomposition (CARP-DF-2)"
status: draft
maturity: idea
created: 2026-07-23
updated: 2026-07-23
feature_slug: catalog-assisted-research-planning
prd_ref: docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
open_questions:
  - "What would the approved evaluation set look like, and who authors/approves it before any model-generated decomposition is trusted?"
  - "If model-generated decomposition is added, does it replace or supplement the deterministic residual-question set — and how would the byte-equivalence/determinism guarantee (carp-contract-freeze.md §3.4) be preserved or explicitly relaxed?"
  - "Which model, prompt, and provenance record would be attached to a model-generated sub-question, and how would that provenance flow through selected_assertion_ref/retrieval_receipt without inventing a new authority?"
explored_alternatives: []
related_documents:
  - docs/dev/architecture/carp-contract-freeze.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
---

# Catalog Planning: Adaptive/Model-Generated Query Decomposition (CARP-DF-2)

## Status: Idea (Not Active)

This is Catalog-Assisted Research Planning's (CARP) deferred-item anchor for CARP-DF-2
("Adaptive/model-generated query decomposition") per the CARP implementation plan's Deferred Items
Triage table and the CARP PRD's §12 Deferred Items. It is a placeholder for a future design record,
not a specification anyone should build against today.

CARP v1 resolves each research-brief question with a fixed, deterministic coverage rule
(`docs/dev/architecture/carp-contract-freeze.md` §3.1) against the question exactly as the brief
states it. It does not decompose a question into model-generated sub-questions, and it does not use
a model anywhere in the coverage-decision path.

## Why this feature defers it (plan Deferred Items Triage)

**Reason deferred:** Model-generated query decomposition adds nondeterminism and prompt/model
provenance concerns. CARP's frozen contract guarantees "same inputs + same catalog generation ⇒
byte-equivalent plan" (`carp-contract-freeze.md` §3.4) — a guarantee that a model call in the
decision path would put at risk, since model output is not guaranteed reproducible across calls,
providers, or versions. It would also introduce a new provenance question (which model, which
prompt, which version generated this sub-question) that the frozen contract's deterministic,
auditable design does not need to answer today.

## Trigger for Promotion

**An approved evaluation showing deterministic residual questions are insufficient.** Promotion
requires evidence — reviewed and approved, not simply asserted — that the existing deterministic
planner's residual-question set misses coverage that a decomposed query would have found, at a rate
that justifies accepting nondeterminism and model/prompt provenance into the coverage-decision path.

## Next Steps

When promoted, this document's owner should:

- Decide whether decomposition happens strictly before the deterministic coverage rule runs (each
  sub-question independently resolved as its own terminal `covered`/`residual` entry) or whether it
  changes the coverage rule itself — the two have very different provenance and byte-equivalence
  implications.
- Design how a decomposed sub-question's provenance (model, prompt, version) is recorded without
  duplicating or diluting `selected_assertion_ref`/`retrieval_receipt`'s existing authority
  (`carp-contract-freeze.md` §4.1's "one authoritative location per fact" principle).
- Define what "byte-equivalent" means once model output is in the loop — either a new determinism
  guarantee (e.g. pinning model+prompt+seed) or an explicit, reviewed relaxation of §3.4.
