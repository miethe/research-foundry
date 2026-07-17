---
title: "Assertion-Ledger Backfill Mapping Strategy"
doc_type: design_spec
schema_version: 2
status: accepted
maturity: ready
created: 2026-07-16
updated: 2026-07-16
feature_slug: assertion-ledger-activation
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
spike_ref: docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md
related_documents:
  - docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1/phase-2-backfill.md
problem_statement: >-
  Historical claim ledgers cannot be materialized into passage-bound source
  assertions at anything close to full coverage, because the extraction
  pipeline stores a paraphrase (not the verbatim quote) as the claim text.
  This spec records the resolved P2-01 backfill mapping-strategy decision so
  Phase 2's build tasks (P2-02+) proceed against a recorded, non-"TBD"
  verdict rather than an open research question.
open_questions: []
explored_alternatives:
  - "(a) Accept the exact-match-only yield and report coverage transparently."
  - "(b) A bounded quote-recovery step re-scoped to fuzzy>=0.9 over existing per-point quotes, with mandatory spot-check -- adopted as an add-on, not a replacement for (a)."
  - "(c) Defer via retroactive re-extraction of historical source cards -- rejected as out of scope and unnecessary given (a)+(b)."
  - "Open-ended gate-relaxation (any generic similarity/substring threshold on the materializer's exact-passage check) -- rejected; no such threshold preserves the fail-closed provenance guarantee (SPIKE RQ3)."
---

# Assertion-Ledger Backfill Mapping Strategy

## Decision

**Adopt accept-low-yield (option a) as the floor, plus a narrow, spot-checked
fuzzy>=0.9 quote-recovery add-on (re-scoped option b).** Reject open-ended
gate-relaxation and reject deferring the decision. This is the P2-01 SPIKE's
own resolved verdict (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`,
delivered 2026-07-15, RQ4), promoted here into a durable design-spec artifact
per this phase's residual administrative step -- not a new investigation.

Rejected alternatives and the reasoning behind each rejection are listed in
`explored_alternatives` above; see the SPIKE's RQ2/RQ3 sections for the full
empirical basis (a full-corpus fuzzy-ratio sweep, and a manual inspection of
the 0.90-0.999 similarity band that found real semantic drift even at that
top percentile).

## State the yield as two numbers, not one

The SPIKE's pre-fix estimate (~3.0% naive floor, ~6.8% with the fuzzy-recovery
add-on) was superseded by the 2026-07-16 post-fix re-measurement, once
Phase 1.5 landed the verbatim-quote-binding and passage-segmentation fixes
(commit `6af82ce`). Communicate both figures below to stakeholders; never
collapse them into one:

| Metric | What it measures | Result |
|---|---|---|
| **Fix-isolated fact-level yield** | Every supported fact across the 42-run corpus (2,991), materializing directly against the fixed passage-binding gate, bypassing only the (then still-broken) claim-ledger bijection check | **94.78%** (2,835/2,991) |
| **Real, end-to-end yield today** | The actual public `AssertionMaterializer.materialize_run()`, unmodified, called for all 42 runs | **0.70%** (21/2,991) -- blocked by defect 1c (39/42 runs abort with `non_bijective_fact_claim_mapping`) and the (pre-P2-01b) all-or-nothing-per-run design |

**94.78% fact-level yield is achievable once defect 1c (P2-01a) and
skip-and-continue materialization (P2-01b) land; 0.70% end-to-end yield is
what an unmodified backfill run produced before those two fixes.** P2-02's
write-path driver must re-measure and report the actual observed yield
against the real corpus rather than assuming either figure holds exactly
once real writes occur (see the parent phase file's "Post-Fix
Re-Measurement" section and P1.5's "Reconcile Before Locking Phase 2's Yield
Framing" note).

## Scope correction inherited from the SPIKE

Phase 2's own original task text described option (b) as re-deriving a
verbatim span "against the cached source text." No such cache exists
anywhere in this workspace (confirmed by the SPIKE: no `assertion_ledger/`
directory existed prior to `ba9e551`). Option (b), as adopted, is exactly
what the SPIKE measured: a fuzzy>=0.9 comparison against each source card's
own existing per-point `quote` field, with recovered matches flagged
spot-check-pending rather than auto-materialized (P2-06's scope; not built
by this design-spec).

## Deal killers

- Any generic similarity/substring threshold applied directly to the
  materializer's exact-passage-binding check (`AssertionRegistry.find_exact_passages`),
  in place of, rather than alongside, the fuzzy-recovery add-on's own
  spot-check gate.
- A fuzzy-recovery threshold below 0.9 accepted automatically without human/
  agent spot-check -- the SPIKE's manual inspection of the 0.90-0.999 band
  found real semantic drift (a tense-changed sentence) even at that top
  percentile; 0.8 and below demonstrably admits real paraphrase divergence.
- Silently reporting only one of the two yield figures (fix-isolated vs.
  real end-to-end) to stakeholders, or implying full-corpus coverage from
  either number alone.

## Status

Decision resolved and recorded. Residual implementation work (the P2-02
write-path driver, the P2-06 fuzzy-recovery add-on, and updating the parent
plan's `deferred_items_spec_refs` frontmatter field to point at this
document) is out of scope for this design-spec and is tracked by the parent
phase file's own task table -- the `deferred_items_spec_refs` frontmatter
update specifically is deferred to P6 per this feature's current sequencing.
