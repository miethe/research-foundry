---
schema_version: 2
doc_type: design-spec
title: "External Research Citation Recovery — Fuzzy Matching (ERI-DF-3)"
status: draft
maturity: shaping
created: 2026-07-27
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
related_documents:
  - docs/dev/architecture/external-research-handoff-contract.md
  - docs/dev/architecture/assertion-ledger-contract.md
deferred_from: "ERI Phase 4 (Exact Resolution, Quarantine, and Promotion) — deferred item ERI-DF-3 in the ERI implementation plan's Deferred Items table"
---

# External Research Citation Recovery (ERI-DF-3)

## What is deferred

ERI v1's exact-passage resolver (`external_research_resolution.py`, contract §2.4 step 7) requires a
candidate's quoted text to **uniquely and exactly** match one passage in the re-acquired source's
bound edition. Zero matches, multiple matches, or a drifted quote (the vendor's quote no longer
matches what is on record for that source) all quarantine — `citation_unresolved`,
`citation_ambiguous`, or `citation_mismatch` — with **no fallback of any kind**.
`AssertionRegistry.find_exact_passages()`'s own docstring states the invariant ERI-4.3 preserves
verbatim: "More than one result is intentionally an ambiguity. [The resolver] must abstain, not pick
a newer edition or a similar-looking passage."

This spec names, but does not scope, a **fuzzy/approximate citation-recovery** mechanism: something
that could recover a quarantined `citation_mismatch`/`citation_unresolved` item when the vendor's
quote is a close-but-not-exact match to real content (paraphrase, minor re-wording, whitespace/
punctuation drift beyond what normalization already handles, OCR noise, etc.), rather than leaving it
permanently quarantined.

## Why it was deferred (from the implementation plan)

> Fuzzy matching cannot establish exact passage identity safely.

This is not a tooling gap — it is a structural property of what "exact passage" means as an evidence
primitive in this codebase. RF's entire claim-traceability discipline (`CLAUDE.md`: "every material
claim in a report maps to a source card or is labeled inference/speculation") rests on a claim
pointing at *the actual bytes*, not at *something that resembles* the actual bytes. A similarity
score — however calibrated — introduces exactly the failure mode `find_exact_passages()`'s own
docstring is written to prevent: a "close enough" match silently substituting for ground truth,
which is far more dangerous in an evidence pipeline than an honest, visible quarantine, because it
looks like real evidence to everything downstream (verification, materialization, a human reviewer
skimming a claim ledger).

There is also no existing labeled ground-truth corpus in this codebase to validate a fuzzy matcher
against — building one without evidence of measured, real-world need would be premature
infrastructure, and any similarity threshold picked without that corpus would be an arbitrary,
untested guess baked into a safety-relevant path.

## Trigger for promotion

Per the plan's Deferred Items table: "Measured unresolved need plus labeled evaluation corpus."
Concretely, before this is promotable:

1. **Measured need**: real ERI import runs (not synthetic fixtures) accumulate a non-trivial rate of
   `citation_mismatch`/`citation_unresolved` quarantines that a human reviewer, upon inspection,
   confirms *were* genuinely the same underlying passage (i.e. false negatives of the exact matcher,
   not genuinely wrong vendor citations) — recorded with counts and examples, not asserted.
2. **Labeled evaluation corpus**: a dataset of (vendor quote, ground-truth passage, human-labeled
   match/no-match) pairs large enough to evaluate a candidate matcher's precision/recall — critically,
   **precision** (false-positive rate: how often it recovers a WRONG passage) is the metric that
   matters most for an evidence pipeline, not recall.
3. Any promoted design must preserve, not weaken, the existing "quarantine and stop" default: a
   recovered fuzzy match should land at a **new, explicitly lower-trust outcome** (never silently
   promoted to `passage_resolved`, and categorically never to `verified`) — something a human or a
   stricter downstream gate must explicitly accept, mirroring the same "explicit promotion seam, no
   automatic authority" pattern the contract already uses for `verified` (§2.4.1).

## What this spec does NOT do

It does not propose an algorithm (edit distance, embedding similarity, or otherwise), does not set a
threshold, and does not modify `AssertionRegistry.find_exact_passages()`'s existing exact-match
contract, which other RF evidence paths (not only ERI) depend on remaining exact.
