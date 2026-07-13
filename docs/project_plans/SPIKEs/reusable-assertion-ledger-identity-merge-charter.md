---
schema_version: 2
doc_type: spike
title: "Reusable Assertion Ledger — Identity and Semantic Merge Audit SPIKE"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
complexity: large
estimated_research_time: "7 working days"
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
research_questions:
  - "Which immutable identifiers and fingerprints remain stable for unchanged source editions, passages, and source assertions?"
  - "How should changed editions and corrected passages receive new identities while preserving lineage?"
  - "Can qualifier-aware semantic merge candidates reach useful reviewer acceptance without harmful false merges?"
  - "What reversible versioning model preserves every source assertion when canonical-claim grouping changes?"
related_documents:
  - docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md
  - docs/project_plans/exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md
  - docs/project_plans/exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md
output_artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
downstream_phase_unlocked: "P1 / Phase 2 — Canonical Contracts and P2 / Phase 3 — Edition and Passage Registry (canonical merge optional)"
---

# Identity and Semantic Merge Audit SPIKE Charter

## Decision to make

Choose a durable identity and versioning contract for source editions, passages,
source assertions, and canonical claims. Determine whether semantic grouping is
safe enough for the first private release or must remain an optional later
layer over reusable source assertions.

## Required upstream inputs

This SPIKE consumes, and does not duplicate, the outputs and definitions owned
by:

- `docs/project_plans/exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md`
- `docs/project_plans/exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md`

Their chosen atomicity, passage-alignment, and citation-quality contracts are
entry criteria. If either exploration has not concluded, use its explicitly
versioned fixture contract and record the dependency; do not invent a competing
segmentation algorithm, alignment metric, or citation evaluator in this SPIKE.

## Hypothesis

Content-addressed edition and passage identity plus a versioned assertion
fingerprint can deterministically recognize unchanged evidence and issue new,
lineage-linked identities for changed evidence. In one narrow domain,
qualifier-aware similarity can propose canonical-claim merges that reviewers
accept at least 80% of the time, with harmful false merges below 2% and no silent
loss of modality, population, timeframe, geography, method, or other material
qualifiers.

## Deal-killer

Stop durable assertion reuse if unchanged editions or passages cannot reproduce
the same identity, or if changed evidence can silently retain the old identity.
Semantic-merge failure is not a deal-killer for the private ledger: it forces the
assertion-only fallback and defers canonical grouping.

## Timebox

Seven working days: two for identity/version prototypes, three for the bounded
merge audit, one for adversarial and rollback tests, and one for synthesis.

## Bounded method and fixtures

1. Select one domain with 200–500 upstream-aligned source assertions from at
   least 30 immutable editions. Include exact duplicate retrievals, formatting-
   only renditions, substantive revised editions, OCR variants, and corrected
   passages.
2. Define candidate identity inputs for source, edition, passage, assertion, and
   canonical-claim version. Distinguish immutable content hashes from opaque
   stable record IDs and document normalization before hashing.
3. Run every unchanged fixture through identity generation at least three times
   and in two input orders. Verify deterministic identities and stable lineage.
4. Mutate one material fact or qualifier in each adversarial fixture. Verify a
   new passage/assertion identity is produced and linked to its predecessor.
5. Generate 100–250 semantic merge candidates, including at least 40 hard
   negatives differing by population, timeframe, modality, geography, method,
   measurement basis, negation, or uncertainty.
6. Have two reviewers independently label equivalence/non-equivalence and merge
   harm; adjudicate disagreements. Measure candidate acceptance, harmful false
   merges, missed obvious equivalents, and reviewer time.
7. Exercise merge, split, supersede, and rollback. Confirm canonical-claim
   changes never rewrite or delete source assertions and every prior report/run
   reference can still resolve its original assertion version.

## Required result artifact

Write `docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md`
with the identity contract, normalization rules, collision analysis, example
lineage, canonical-claim version state machine, reviewer rubric, labeled fixture
summary, metric denominators, rollback proof, verdict, and assertion-only
fallback contract.

## Verdict thresholds

### Go

- 100% of unchanged edition, passage, and assertion fixtures reproduce their
  identities across reruns and input ordering.
- 100% of materially changed edition/passage fixtures receive new identities
  with predecessor lineage; no stale identity is silently reused.
- Reviewers accept at least 80% of proposed merge candidates.
- Harmful false merges are below 2%, with zero silent material-qualifier loss.
- Merge/split/rollback preserves all source assertions and historical references.

### Conditional

- Durable source-edition, passage, and assertion identity passes in full, but
  merge acceptance is below 80%, harmful false merges are 2–5%, or reviewer cost
  is uneconomic. Proceed with reusable source assertions and search; disable
  automatic canonical grouping and name a later domain-specific merge gate.

### No-go

- Any unchanged fixture is nondeterministic after one root-cause remediation;
- Any material change silently retains the old passage/assertion identity; or
- Merge/version operations can destroy a source assertion or prevent a report
  from resolving the exact assertion version it used.

## Risks and controls

| Risk | Control |
|---|---|
| Normalization erases meaningful changes | Hash raw edition bytes and separately hash explicitly normalized passage text. |
| Similarity conflates related with equivalent | Candidate-only merges, qualifier hard negatives, human review, and reversible versions. |
| Reviewers share the same bias | Independent labels, adjudication, and disagreement reporting. |
| A narrow domain inflates merge accuracy | Publish domain limits; do not generalize thresholds without a new fixture audit. |
| Identity leaks source content | Use opaque public-facing IDs; keep content hashes and passages access-controlled. |

## Scope boundary

This SPIKE does not reopen segmentation, source alignment, or citation-quality
methodology. It does not implement public nanopublication export, shared-index
tenancy, public-source rights review, or production merge automation.

## Downstream handoff

A `go` verdict clears the identity constraints for P1 / Phase 2 Canonical
Contracts and P2 / Phase 3 Edition and Passage Registry; canonical merge remains
optional. A `conditional` verdict constrains those phases to durable assertion
identity only. A `no-go` verdict blocks cross-run assertion reuse until the
identity contract is redesigned.
