---
schema_version: 2
doc_type: spike
title: "Reusable Assertion Ledger — Historical Replay and Reuse Economics SPIKE"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
complexity: large
estimated_research_time: "5 working days"
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
research_questions:
  - "How much historical source processing can be safely reused across representative recurring-domain runs?"
  - "What time, model-call, and evidence-preparation savings result after freshness and extraction-contract checks?"
  - "Does reused evidence preserve exact edition and passage provenance without degrading claim support quality?"
related_documents:
  - docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md
output_artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md
downstream_phase_unlocked: "P1 / Phase 2 — Canonical Contracts"
---

# Historical Replay and Reuse Economics SPIKE Charter

## Decision to make

Determine whether recurring Research Foundry workloads contain enough safely
reusable source-edition and assertion work to justify the private ledger, and
establish a measured baseline against which implementation uplift is judged.

## Hypothesis

Across recurring-domain runs, immutable source-edition identity plus extraction-
contract and freshness checks will allow at least 20% of source processing to be
reused while at least 95% of sampled reused assertions retain the correct exact
passage provenance. This reuse will reduce model calls, elapsed time, and manual
evidence preparation without increasing unsupported claims.

## Deal-killer

Stop the private-ledger implementation if representative replay cannot safely
reuse at least 10% of processing, or if correct passage provenance remains below
90% after one bounded remediation cycle. Low raw cache hits are not sufficient
to fail the SPIKE unless the corpus contains meaningful repeated source editions.

## Timebox

Five working days. Freeze the fixture manifest and measurement definitions by
the end of day one. At cutoff, publish partial results and a verdict; do not
extend the corpus to chase the target.

## Bounded method and fixtures

1. Select 10–20 historical or representative runs from one or two recurring
   research domains, covering 100–300 source inputs with a documented mixture of
   exact repeats, changed editions, and one-off sources.
2. Create a read-only fixture manifest containing source locator, retrieved
   content hash, edition classification, run membership, extraction-contract
   version, freshness state, and expected reuse eligibility. Do not mutate the
   source runs or production catalog.
3. Establish the baseline by measuring ingestion/extraction model calls, elapsed
   time, estimated cost, and evidence-preparation effort under current behavior.
4. Prototype edition-level reuse in an isolated harness. Reuse only when edition
   hash, extraction contract, sensitivity/rights policy, freshness, and
   evaluation state all permit it; otherwise record the rejection reason.
5. Sample at least 60 reused assertions, or every reused assertion when fewer
   than 60 qualify. A reviewer verifies exact edition, passage text/hash,
   locator, qualifiers, and support relationship against the fixture source.
6. Compare baseline and replay for safe reuse rate, avoided model calls, elapsed
   time, estimated cost, evidence-preparation effort, support rate, and citation
   correctness. Report exact denominators and confidence limits where practical.

## Required result artifact

Write `docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md`
with:

- The frozen fixture manifest or a durable pointer to it.
- Definitions and formulas for every metric.
- Per-run and aggregate measurements, including reuse-rejection reasons.
- Provenance-audit failures with severity and root cause.
- Baseline-versus-replay quality comparison.
- A structured `go`, `conditional`, or `no-go` verdict and implementation inputs.

No implementation phase may claim replay savings from estimates after this
artifact exists; the measured result becomes the planning baseline.

## Verdict thresholds

### Go

- Safely reusable processing is at least 20% across the representative corpus.
- At least 95% of audited reused assertions preserve exact edition and passage
  provenance, with no high-severity provenance mismatch.
- Unsupported-claim rate does not increase and citation correctness declines by
  no more than two percentage points.
- Avoided model calls, elapsed-time savings, and review cost are all reported,
  and net evidence-preparation effort improves rather than shifts to reviewers.

### Conditional

- Safely reusable processing is 10–19.9%, or provenance accuracy is 90–94.9%,
  and a single named, bounded change is likely to clear the go threshold; or
- The aggregate misses the gate but one recurring workload segment clears it.
  Limit the pilot to that segment and name the re-evaluation condition.

### No-go

- Safely reusable processing is below 10% on a corpus with meaningful repeated
  editions; or
- Correct passage provenance is below 90% after one remediation cycle; or
- Reuse increases unsupported claims or creates a high-severity source/passage
  mismatch that cannot be prevented by a deterministic eligibility rule.

## Risks and controls

| Risk | Control |
|---|---|
| Corpus selection overstates recurrence | Publish selection criteria, repeat-rate distribution, and per-domain results. |
| Changed sources are mislabeled as cache hits | Require content hashes and explicit edition classification. |
| Savings merely move work to reviewers | Include human review time in net evidence-preparation effort. |
| Quality comparison is circular | Audit against source passages, not extractor confidence. |
| Sensitive material escapes the fixture | Keep the harness workspace-scoped and emit only aggregated results plus redacted failures. |

## Scope boundary

This SPIKE does not design canonical-claim merging, implement production storage,
test shared indexes, or clear sources for public redistribution. Shared/public
rights and tenant-leakage gates remain conditional future work.

## Downstream handoff

A `go` verdict unlocks P1 / Phase 2 Canonical Contracts. A `conditional`
verdict unlocks only the named workload-limited pilot. A `no-go` verdict stops
reusable-processing work while leaving provenance improvements available as an
independent enhancement.
