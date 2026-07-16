---
title: "Phase 1.5: Forward Extraction/Ingest Contract Fix"
schema_version: 2
doc_type: phase_plan
it_schema: 1
status: draft
created: 2026-07-15
phase: P1.5
phase_title: "Forward extraction/ingest contract fix"
feature_slug: assertion-ledger-activation
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
spike_ref: docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md
entry_criteria: ["PRD approved", "P2-01 SPIKE verdict reviewed"]
exit_criteria: ["a verbatim quote materializes end-to-end (>=1 exact-passage match)", "no-workspace-id/flag-off path unchanged", "karen security sign-off"]
delegation_mode: D
---

# Phase 1.5: Forward Extraction/Ingest Contract Fix

**Mode: D -- High-Risk Change (WKSP-304-adjacent).** This phase changes what the persisted `assertion_text` field means for every future write -- forward or backfilled. No auto-merge; diffs reviewed before merge/deploy.

**NEW, BLOCKING.** This phase did not exist in the pre-SPIKE plan. It is inserted per the P2-01 SPIKE's primary recommendation (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`).

**Duration**: ~2 days
**Dependencies**: None (wave 1, parallelizable with P1 and P5)
**Assigned Subagent(s)**: python-backend-engineer (primary), karen (security milestone)
**Model default**: sonnet | **Effort default**: extended

[<- Back to parent plan](../assertion-ledger-activation-v1.md)

## Why This Phase Exists

The P2-01 SPIKE found two independent, compounding defects that any forward run through `rf ingest -> source_cards.ingest_source() -> AssertionMaterializer.materialize_run()` reproduces almost exactly, capping forward yield near **0%** -- not the historical corpus's ~3% floor:

1. **Defect 1a (paraphrase-vs-quote).** `extraction.py::_fact_from_point` copies the source card's paraphrased `summary` into `extracted_facts[].text`; the verbatim `quote` field is read only to set a boolean `quote_available` flag and is never persisted past the source card. The claim ledger's `text` -- what the materializer must byte-match -- is therefore always the paraphrase, by construction.
2. **Defect 1b (no passage segmentation, new finding beyond OQ-1).** `source_cards.py::ingest_source()` calls `AssertionRegistry.ingest()` without a `passages=` argument, so the entire raw document becomes exactly one passage. A short verbatim quote can never bind via `find_exact_passages()` unless the quote is the entire document. Proven live: 0 matches before passing `passages=`, 1 match after (SPIKE RQ1, `passage_binding_test.py`).

OQ-2 already resolved that the forward write driver (Phase 3) reuses `ingest_source()` verbatim -- so both defects transfer unchanged to Phase 3 unless fixed here first. **This phase is the blocking prerequisite that makes the ledger populate at all, and it unblocks Phase 3.**

## Scope

**(a) Bind assertion passages to the verbatim quote, not the paraphrase.** The persisted `assertion_text` (and the exact-match gate that authorizes it) must be sourced from the source card's `extracted_points[].quote`, not from `extracted_facts[].text` / the claim ledger's paraphrased `text`. There are two valid implementation shapes for this -- either is acceptable, and the choice should be made by whichever keeps the smaller blast radius:
   - **Pipeline-threading approach**: modify `extraction.py::_fact_from_point` to carry the verbatim `quote` through to a materializable field on the extraction fact (and thread it through `claim_mapping.py::build_claim_ledger`), so `mapping.text` itself becomes the quote.
   - **Materialization-layer approach**: leave the extraction/claim-mapping pipeline untouched, and instead change `assertion_materialization.py::_prepare_one` to persist the source card's already-resolved evidence-point quote (`evidence.get("quote")`) as `assertion_text`, rather than requiring `quote == mapping.text` and persisting the paraphrase. The evidence point is already uniquely selected by `evidence_id` + `locator`, so no additional text-equality check against `mapping.text` is required.

   **Implementation status note (updated)**: the **materialization-layer approach** has already **landed** on this branch (`fix/assertion-extraction-contract`) as commit `6af82c` ("fix(assertion-ledger): bind assertions to verbatim source quotes + segment passages on ingest"), touching `assertion_materialization.py::_prepare_one` (removes the `quote != mapping.text` abstain check; sets `assertion_text = quote` / `assertion_text_sha256 = _digest(quote)`, while leaving the `find_exact_passages()` SHA-256 binding gate unchanged, per the commit message's own note) and `tests/unit/test_assertion_materialization.py` (updated coverage). This phase's remaining tasks are to **validate and formally gate** that committed change against this phase's ACs (P1.5-03) and the karen milestone, not to build it from scratch.

**(b) Wire passage segmentation into ingest.** `source_cards.py::ingest_source()` must pass `passages=[p["quote"] for p in points if isinstance(p.get("quote"), str) and p["quote"]]` (deduped, whitespace-normalized) into its `registry.ingest()` call, so a short verbatim quote can bind via `find_exact_passages()` instead of only ever matching the single whole-document passage. This is additive and non-breaking: re-ingesting the same content with new passages extends the edition (SPIKE RQ1: `created=False, reusable=True`).

**Implementation status note (updated)**: the fix for (b) has also **landed** in the same commit `6af82c`, touching `source_cards.py::ingest_source()` (computes a deduped `quote_passages` list and passes `passages=quote_passages or None` into `registry.ingest()`). The commit message explicitly confirms this is scoped as a prerequisite for Phase 3 ("Prereq for C1") and explicitly does **not** wire the forward driver or backfill itself ("Does NOT wire the forward driver (C1) or backfill (B2)") -- matching this phase's boundary exactly.

## IMPORTANT -- Reconcile Before Locking Phase 2's Yield Framing

**RESOLVED (2026-07-16, post-fix re-measurement) -- see the dated entry in `## Findings` below and `docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`'s "## Post-fix re-measurement (2026-07-16)" section for the actual measured numbers.** The paragraph below is retained as the original (correct) prediction that prompted the re-measurement.

The materialization-layer approach described above removes the `quote != mapping.text` check **entirely** for any caller, not just the forward path -- it does not "relax" a similarity threshold (which the SPIKE's RQ3 explicitly rejects); it changes which field (`quote`, not the paraphrase) authorizes and becomes the persisted `assertion_text`. Because `AssertionMaterializer.materialize_run()` is shared code (Phase 2's backfill calls it too, per Phase 2's own seam task P2-03), **if Phase 2 reuses this same fixed materializer unmodified, its actual observed backfill yield may land materially higher than the SPIKE's ~6.8% estimate** -- that estimate was computed against the *pre-fix* byte-identity gate. This is not a defect in this phase's scope; it is a downstream interaction the Phase 2 implementer and the P6 audit MUST reconcile explicitly: report the *actual measured* backfill yield in the receipt (the transparent-reporting principle this plan already requires), rather than assuming the SPIKE's pre-fix estimate still holds once this phase lands. If Phase 2 intentionally wants a stricter, different binding rule for backfill specifically, that divergence must be a documented, deliberate design choice (in the P2-01 design-spec promotion), not an unstated implicit behavior.

## R-P3 Check (integration ownership)

Single owner specialty (python-backend-engineer) builds; karen is a Mode E-equivalent security reviewer, not a co-builder with overlapping `files_affected`. **R-P3 does not trigger** -- no `integration_owner` declaration needed for this phase.

## Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|--------------|-------|--------|--------------|
| P1.5-01 | Fix defect 1a: bind assertion_text to the verbatim quote | Implement the binding fix (materialization-layer or pipeline-threading approach; see Scope above -- validate/harden the existing uncommitted diff if reused). Remove or replace the `quote != mapping.text` abstain gate with a check grounded in `quote` availability plus the pre-existing evidence_id/locator resolution. | AC-8 target_surfaces: [src/research_foundry/services/assertion_materialization.py, src/research_foundry/services/extraction.py]. propagation_contract: `assertion_text`/`assertion_text_sha256` are sourced from the source card's verbatim quote, never from the paraphrased fact/claim text. resilience: a fact with no resolvable quote still abstains cleanly (no exception escapes as an unrelated failure). visual_evidence_required: false. verified_by: [P1.5-03]. | 1 pt | python-backend-engineer | sonnet | extended | None |
| P1.5-02 | Fix defect 1b: wire passage segmentation into ingest | Modify `source_cards.py::ingest_source()` to compute a deduped, whitespace-normalized list of per-point verbatim quotes and pass it as `passages=` into `AssertionRegistry.ingest()`. Falls back to `None` (whole-document passage) when no point carries a usable quote. | AC-8 target_surfaces: [src/research_foundry/services/source_cards.py, src/research_foundry/services/assertion_registry.py]. propagation_contract: after ingest, `find_exact_passages(source_id, quote)` returns >=1 match for at least one real verbatim quote (SPIKE RQ1 live-proven pattern). resilience: re-ingesting the same content with new passages is additive, not a duplicate/breaking write (registry-layer guarantee, confirmed not defeated by this change). visual_evidence_required: false. verified_by: [P1.5-03]. | 1 pt | python-backend-engineer | sonnet | extended | None |
| P1.5-03 | End-to-end verbatim-quote materialization test + flag-off/no-workspace-id regression | (a) Integration test proving a real fact with a resolvable verbatim quote materializes end-to-end (extraction -> claim mapping -> ingest with passages -> materialize), with >=1 exact-passage match -- this is AC-8's primary anchor. (b) Regression test proving the no-workspace-id path (fails closed, zero writes, per P1-03's shared fixture) and the `ledger_write_enabled=false` path are both byte-identical to pre-P1.5 behavior -- this is AC-9's anchor. Reuse P1-03's shared isolation fixture rather than duplicating it. | AC-8, AC-9 (see descriptions above; this task IS both ACs' `verified_by` anchor). | 1 pt | python-backend-engineer | sonnet | extended | P1.5-01, P1.5-02 |

**Phase 1.5 total: 3 pts.**

## Karen Security Milestone (exit gate, not a priced task)

After P1.5-03 passes: **karen** reviews the full P1.5 diff (P1.5-01, P1.5-02, P1.5-03). This is a Tier 3-mandated security milestone -- this phase changes the trust-boundary meaning of the persisted `assertion_text` field for every future write, forward or backfilled, so it receives the same rigor as P2's and P3's write-enabling milestones. karen's model is `opus` per this project's agent registry. karen's review MUST explicitly confirm the "Reconcile Before Locking Phase 2's Yield Framing" note above is either resolved (Phase 2's actual measured yield is reported, not assumed) or explicitly deferred to Phase 2's own karen milestone with a written note.

## AC Mapping

- **AC-8** (a verbatim quote materializes end-to-end, >=1 exact-passage match) -- primary verification anchor is **P1.5-03**.
- **AC-9** (the no-workspace-id/flag-off path is unchanged) -- primary verification anchor is **P1.5-03**; reused (not re-derived) by P3's flag-off regression test (P3-02), which additionally confirms the contract fix itself introduces no flag-off behavior change.

## R-P2 Check (implicit "FE handles missing X" AC)

This phase introduces no new backend *response* field consumed by any frontend surface -- both defects are internal to the extraction/ingest/materialization write path, with no API-visible shape change. **R-P2 does not trigger.**

## Quality Gates

- [ ] Defect 1a fix lands: `assertion_text`/`assertion_text_sha256` sourced from the verbatim quote, not the paraphrase.
- [ ] Defect 1b fix lands: `ingest_source()` passes a deduped `passages=` list into `AssertionRegistry.ingest()`.
- [ ] End-to-end test proves >=1 verbatim-quote exact-passage match (AC-8).
- [ ] Flag-off/no-workspace-id regression test green, byte-identical to pre-P1.5 behavior (AC-9).
- [ ] `task-completion-validator` passes P1.5 (Tier 3 mandatory per-phase gate).
- [ ] **karen** security sign-off recorded, including explicit disposition of the Phase 2 yield-reconciliation note above.
- [ ] DI-1 scoping note: this phase's write-binding change is flagged for inclusion in P6's DI-1-scoped audit (P6-01).

## Key Files & Integration Points

- `src/research_foundry/services/assertion_materialization.py` (defect 1a fix)
- `src/research_foundry/services/extraction.py` (defect 1a fix, if the pipeline-threading approach is chosen instead of/in addition to the materialization-layer approach)
- `src/research_foundry/services/source_cards.py` (defect 1b fix)
- `src/research_foundry/services/assertion_registry.py` (called, not modified -- `passages=` is an existing parameter on `ingest()`)
- `tests/unit/test_assertion_materialization.py` (updated/new coverage)
- Cross-reference: P1's shared workspace-resolution + fail-closed helper and isolation fixture (`tests/unit/test_assertion_workspace_isolation.py`) -- this phase's regression test (P1.5-03b) reuses that fixture rather than re-deriving it. P1 itself lists `assertion_materialization.py` under "no behavior change yet" -- this phase is the one that actually changes its behavior; the two phases run in the same wave (wave 1) but do not conflict since P1 does not edit that file.

## Findings

**2026-07-15 (plan revision time)**: Both defect fixes landed on this branch as commit `6af82c` during the course of this plan's own SPIKE-driven revision -- the materialization-layer approach was chosen for defect 1a (not pipeline-threading). The commit's own message confirms the fail-closed `find_exact_passages()` gate is unchanged and that it is explicitly scoped as a P3 prerequisite, not a wiring of P3 or P2 itself -- consistent with this phase's boundary as written. **Remaining work for this phase is validation, not construction**: confirm P1.5-03's end-to-end AC-8/AC-9 coverage against the committed diff (the committed test changes cover unit-level defect-1a/1b behavior; an explicit end-to-end "extraction -> ingest -> materialize" integration test proving >=1 real verbatim-quote match, per P1.5-03, still needs confirmation), and run the karen security milestone against the committed diff before treating this phase as closed.

**2026-07-16 (post-fix re-measurement)**: The passage-binding fix (commit `6af82ce`) is now **validated, not speculative**. A full corpus-wide re-measurement (all 42 runs, isolated `/tmp` registry, zero writes to real `.rf_state/`/`assertion_ledger/`/`.rf_cache/`/run artifacts) found **94.78% fact-level materialization yield** (2,835/2,991 supported facts) when the fixed `_prepare_one()` and `ingest_source()` are exercised directly against every supported fact -- an order-of-magnitude improvement over the pre-fix 3.0%/6.8% estimate this SPIKE originally used to scope Phase 2. This number is real but fact-isolated: it does **not** yet reflect what the public `materialize_run()` produces end-to-end today, because a third, independent, pre-existing defect (1c: the claim-ledger bijection gate in `claim_mapping.py`, out of this phase's scope -- it was last touched in `adeddcb`, long before `6af82ce`) currently aborts 39/42 runs before any fact ever reaches this phase's fix at all; real end-to-end yield today is 0.70% (21/2,991). See `docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md` -- "## Post-fix re-measurement (2026-07-16)" -- for the full methodology and both metrics (fix-isolated vs. real end-to-end). Defect 1c and `materialize_run()`'s all-or-nothing-per-run design are tracked as two new blocking prerequisite tasks (P2-01a, P2-01b) in Phase 2 (`phase-2-backfill.md`), not this phase -- **this phase's own scope (defects 1a/1b) is fully validated and closed by this measurement.**

_Resolved (2026-07-16): see the dated entry immediately above and the SPIKE's "Post-fix re-measurement" section for the actual measured impact on Phase 2's backfill yield (see also the "IMPORTANT -- Reconcile" note above, now marked resolved)._
