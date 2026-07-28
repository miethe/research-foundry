---
schema_version: 2
doc_type: design-spec
title: "External Research Exactly-Once Effect Promotion — Prepare/Commit Idempotency (ERI-DF-5)"
status: draft
maturity: shaping
created: 2026-07-28
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
related_documents:
  - docs/dev/architecture/external-research-handoff-contract.md
  - .claude/findings/eri-implementation-audit-round2-gpt56.md
deferred_from: "ERI round-2 implementation audit finding #5 (HIGH, PARTIAL) — remediated partially in the round-2 fix pass; full prepare/commit idempotency formally deferred here"
---

# External Research Exactly-Once Effect Promotion (ERI-DF-5)

## What is deferred

Round-2 audit finding #5 ("Exactly-once effects have an unprotected crash window and weak replay
verification", `external_research_interchange.py` effect recording + `external_research_resolution.py`
promotion) was **partially** remediated:

**Closed in v1:**
- Effect resume now **binds and recomputes** persisted effect records (`receipt_digest`, `action_id`,
  `kind`, recomputed `effect_digest`) instead of trusting a bare action-ID/kind set.
- An **outbox `.prepare` marker** is written before each downstream promotion, ordering intent before
  effect. A leftover `.prepare` with no committed effect record is an inspectable audit trail of a
  crash inside the window (`external_research_interchange.py` — see the `prepare_path` block in the
  effect-recording section).

**Still open (this spec):**
- The window between the downstream mutation (source-card/registry promotion) and the durable effect
  record is *detected* but not *neutralized*. A crash inside it means resume sees a `.prepare` marker
  without a committed effect and cannot know whether the downstream mutation happened; today a repeat
  of the downstream promotion is still possible on resume. Full **prepare/commit idempotency** —
  where every downstream mutation is idempotent by `action_id` so a repeat is a harmless no-op —
  is not implemented.

## Why it was deferred

1. **The downstream authorities are not ERI's to change unilaterally.** True idempotency-by-
   `action_id` requires the *receiving* authorities (source-card registry, assertion-ledger
   materialization) to accept an idempotency key and dedupe on it. ERI v1's design invariant is
   "no second evidence authority" — it deliberately introduces no new semantics on those surfaces.
   Retrofitting idempotency keys onto them is a cross-cutting change belonging to those authorities'
   own plans, not a patch inside an importer.
2. **The residual risk is bounded and visible.** The crash window is milliseconds wide, requires a
   hard process kill inside it, and the `.prepare` marker makes any such crash *detectable* on
   resume — the failure mode is a duplicate quarantined item, not silent corruption or a bypassed
   gate. Quarantined items are already human-reviewed before promotion to evidence.
3. **A half-measure inside ERI alone would be false safety.** Recording "effect committed" before
   the mutation inverts the bug (mutation lost but marked done); two-phase files inside ERI without
   downstream dedupe still cannot distinguish "mutated then crashed" from "crashed before mutating".

## Trigger for promotion

Promote this spec to a plan when **any** of:

1. A real (non-fixture) ERI import run produces a duplicate downstream promotion attributable to a
   crash-in-window resume (a leftover `.prepare` marker plus a duplicate record is the signature).
2. The source-card registry or assertion ledger gains an idempotency-key/dedupe surface for any
   other reason — at that point wiring ERI's `action_id` through it is cheap and this closes fully.
3. ERI import moves from operator-invoked CLI to an unattended/automated surface (queue, HTTP,
   scheduled), where crash-resume cycles happen without a human noticing the marker.

## Sketch of the full fix (non-normative)

- Downstream authorities accept `idempotency_key` (ERI passes `action_id` bound to
  `receipt_digest`); repeated apply with the same key is a verified no-op returning the original
  outcome digest.
- ERI's effect recording becomes prepare → apply(idempotent) → commit; resume replays any
  prepared-uncommitted action unconditionally, relying on downstream dedupe for safety.
- The adversarial matrix gains a kill-inside-window harness (fault injection between apply and
  commit) proving byte-identical receipts across a crash/resume at every window boundary.

## Explicit non-goals

- No relaxation of the existing bind/recompute replay verification (already shipped).
- No new evidence authority or schema version bump — `external_research_handoff/v1` is frozen;
  this is importer-internal plus opt-in parameters on existing authorities.
