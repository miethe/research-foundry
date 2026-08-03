---
it_schema: 1
feature_slug: eri-legacy-extraction-status-backfill
title: "ERI legacy extraction_status backfill — implementation plan"
doc_type: implementation_plan
status: complete
planning_maturity: shipped
tier: 2
priority: P2
points: 13
risk_level: high
context_class: C3
created: 2026-07-31
updated: 2026-08-03
merge_commit: e3ca9ba
merge_branch: main
open_items:
  - "M1 COMPLETE (AC met). Dry-run over live workspace W: 35 eligible / 452 ineligible / 16 already-set, 34 full_text + 1 partial, authoritative_data_mutated false. OQ-1 resolved to the plan's PRIMARY hypothesis empirically, and caught a real defect: the 100,232-byte edition decodes to exactly 100,000 chars and its stored text is cut mid-word, so recompute must fail closed at >= (asymmetric from extract_bytes' strict >). Without that fix the backfill would have stamped full_text provenance onto a truncated document."
  - "M2 COMPLETE (AC met on live data) under explicit human Mode-D approval 2026-08-02. 35 applied; manifest diff vs pre-apply baseline = 70 changed (35 edition records + 35 provenance.yaml), 0 removed; no content.bin touched; 35/35 pass binding recompute-and-compare; the 452 + 16 byte-identical; rollback input validated at would_restore 35 writing nothing. Receipt ral_eri_legacy_status_apply_edc5562345bf6620 in the workspace's backfill_operations/. Out-of-band snapshot at ~/rf-ledger-snapshots/20260802-modeD/ (70MB, 503 editions) plus a 16,873-file sha256 baseline manifest."
  - "M2 scope deviation, deliberate: the repair-on-apply path was REMOVED after three consecutive review rounds found the same defect class (approval-scope drift). It was never in M2's AC — it was added mid-execution in response to a review finding, and the state it repaired is already recoverable by re-running the same rollback receipt. Result: exactly one write loop, iterating the approved set, so touching an unapproved edition is structurally impossible."
  - "M3 COMPLETE (AC met on live data, 2026-08-03) after the AC was re-pointed at the field that carries the signal and the missing target run was scaffolded. Receipt erh_6221f13ef51a4891b6f5b61edadfc3eb8f9c7515057c8fad9c075f4efde1bf50 against run rf_run_20260803_knitwit_s1_rights_evidence: 38 actions, 20 completed / 18 quarantined, by_completeness_tier {source_resolved: 16, passage_resolved: 4}, and verification_failed == 0 on the per-action reason codes (was 4). All four formerly-failing candidates completed at passage_resolved with real source cards in the run's sources/."
  - "M3 ROOT CAUSE (resolved 2026-08-03) — the earlier 'excluded 452' hypothesis is REFUTED. The 4 verification_failed candidates are hobbii-/lion-brand-/lovecrafts-/yarnspirations-product-pages. All four bind to editions with basis: producer_declared_access_status that ALREADY carried extraction_status: full_text (the 16 already-set, acquired 2026-07-31) — not the excluded 452, and not the 35 M2 applied. All four rehydrate cleanly (1 exact passage, 1 distinct edition, content loads), so the bound.extraction_status is None guard never fires. The real cause: default_promote raises NotFoundError because the --run ids passed to M3 (rf_run_20260731_knitwit_s1_postbackfill, ..._v2) NEVER EXISTED in runs/ — no KnitWit run has ever existed in data-plane git history — and the resolver maps that to _candidate_quarantine('verification_failed'). Positive control reproduces error='target_run_not_found' for both ids; natural control group: every receipt whose target run exists has verification_failed 0, while all four KnitWit receipts had exactly 4, the same 4 action ids, invariant before and after the backfill. So M3's premise was wrong, not just its field — the backfill could never have moved this number, because these 4 failures never depended on extraction_status at all. Note this does NOT diminish M1+M2: the 35 editions genuinely needed and received honest status; M3 was simply measuring something else."
  - "FOLLOW-UP DEFECT (filed): reason_code verification_failed CONFLATES a missing target run with a genuine verification failure, and default_promote's bare `except Exception` funnels every other staging failure into promotion_failed — an operator input error is reported as an evidence problem. Reason codes are the authoritative surface for M3-class ACs, so a misattributing code is load-bearing."
  - "FOLLOW-UP DEFECT (filed): the 'dry-run does not predict live' finding below is NOT an independent regression of 1f982a7 — same single root cause. _finish_passage_resolved short-circuits on self._dry_run BEFORE the promotion call, so a preview is STRUCTURALLY INCAPABLE of seeing any promotion failure. Hoisting the content/status guard above that early return fixed only half the class."
  - "PROCESS FINDING (M3): the first M3 run was INERT. Run with cwd inside the git worktree, FoundryPaths.discover() resolved to the WORKTREE root, so the import created a fresh empty assertion_ledger/ there and fresh-acquired 16 sources into it, never touching the backfilled live ledger — while exiting 0 with the correct packet digest and a plausible receipt. Rule: run rf from the main checkout; the data plane does not follow the worktree."
  - "PROCESS FINDING (M3): dry-run does NOT predict the live outcome, a regression of the property 1f982a7 established. Same packet/workspace/target against the live ledger: --dry-run reported {locator_only: 15, passage_resolved: 4, source_resolved: 4} / 23 completed / 15 quarantined, while the real import gave {source_resolved: 16} / 16 completed / 22 quarantined with passage_resolved 0. Confirmed not a receipt replay (a fresh target run id produced a new receipt and the same live numbers)."
  - "NON-BLOCKING follow-up: a refused apply leaves a zero-byte .apply.lock in the evidence tree (the lock precedes the pinned-scope check, which is correct ordering and must stay). Now created 0600 and unlinked when nothing mutated, but any ledger-integrity check must still exclude backfill_operations/.apply.lock."
prd_ref: null
intenttree_node: node_01KYWX69SRH981ZGE419GM31EE
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
related_documents:
  - docs/project_plans/implementation_plans/enhancements/eri-reused-edition-promotion-v1.md
  - .claude/worknotes/eri-reused-edition-promotion/implementation-notes.md
acceptance_criteria:
  - "The 35 ERI-acquired editions carry a recomputed extraction_status; the 452 rollout editions are untouched."
  - "A live re-run of the operator packet, against an EXISTING target run, shows verification_failed == 0 measured on the per-action reason codes in receipts/<receipt_digest>/effects/*.yaml (NOT by_completeness_tier, which tallies only completed actions and can never hold the value)."
open_questions:
  - "OQ-1: does the 100,232-byte edition decode to exactly 100_000 chars (=> partial) or fewer (=> full_text)? M1 must answer empirically."
  - "OQ-2: could promotion create a duplicate run source card for candidates that previously quarantined?"
  - "OQ-3: confirm no run source card already references the 35."
decisions:
  - decision: "Eligibility is gated on allowed_use.basis == producer_declared_access_status, never on content shape."
    rationale: "Content shape (full_text/partial) is recomputable for both eligible and ineligible editions; only basis distinguishes an honest extraction from a quote-join with no real full text."
    status: accepted
  - decision: "The 452 assertion_rollout quote-join editions are out of scope permanently."
    rationale: "A quote-join has no honest full_text to recompute; backfilling them would overclaim fidelity."
    status: accepted
  - decision: "M2 requires explicit human Mode-D approval before the first apply; dry-run needs none."
    rationale: "Irreversible-outward: rewrites provenance.yaml + edition_binding_sha256 for live workspace data."
    status: accepted
routing_constraints:
  - "Recompute predicate + provenance re-attestation (M1/M2) MUST stay claude-primary — any leg touching assertion_registry.py must reason about content-addressed immutability and provenance-digest invariants."
  - "Test authoring is offload-eligible."
  - "M3 live packet re-run is offload-eligible."
wave_plan:
  waves: [["M1"], ["M2"], ["M3"]]
  phases:
    - id: M1
      title: "Status is recomputable and provable without mutating anything"
      depends_on: []
      exit_criteria: ["Dry-run over W reports 35 eligible / 452 ineligible / 16 already-set, 34 full_text + 1 partial; receipt records authoritative_data_mutated: false"]
      gate_lens: [validator]
    - id: M2
      title: "Apply rewrites the 35 pairs reversibly and re-attests provenance"
      depends_on: ["M1"]
      exit_criteria: ["All 35 pass verify_source_card_binding post-apply; rollback restores byte-identical prior state; the 452 are untouched with unchanged digests"]
      gate_lens: [security, validator]
      gate_lens_reason: irreversible-outward
    - id: M3
      title: "Live re-prove with the real packet"
      depends_on: ["M2"]
      exit_criteria: ["Target run exists BEFORE the import (a nonexistent --run id degrades silently into per-candidate quarantine, not an error); operator packet re-import yields passage_resolved 4 with verification_failed == 0 on the per-action reason codes in receipts/<receipt_digest>/effects/*.yaml"]
      gate_lens: [validator]
---

# Implementation Plan — ERI Legacy extraction_status Backfill

Live workspace W has 503 editions; 16 carry `extraction_status`, 487 do not. Of the 487, 35
(2026-07-29, ERI-acquired) are recomputable to an honest status since `extract_bytes` is
pure/zero-I/O and the ledger stores exactly `extraction.text`; the remaining 452 (2026-07-17,
assertion_rollout quote-join) have no honest full text and stay quarantined by decision. Done
state: the 35 carry recomputed `extraction_status` + re-attested provenance; the KnitWit S1 packet
re-import no longer quarantines them as `verification_failed`.

## Scope boundary

**In:** the 35 ERI-acquired editions; the pure recompute function; provenance re-attestation; M3.

**Out (stated):** the 452 assertion_rollout editions — permanently quarantined by decision, not a
deferred follow-up; no backfill tooling is built for them.

## Rubric — what "good" looks like

Eligibility is decided by `allowed_use.basis`, never content shape — no code path recomputes
status without first checking `basis == producer_declared_access_status`. M2's apply writes both
the `extraction_status` extension and the recomputed `edition_binding`/`edition_binding_sha256`
for one edition, or neither. Tests exercise real entry points (`extract_bytes`,
`verify_source_card_binding`, the intake CLI), not unit shims.

## Named risks

- **Overclaiming fidelity (R1).** Never content-derive status for a rollout edition; `basis` is
  the only gate, even if the text looks full-length.
- **Byte-vs-char miscount (R2, OQ-1).** The 100,232-byte edition must be char-counted after UTF-8
  decode against `_MAX_EXTRACT_CHARS` (304); a raw byte check misclassifies it — M1 must answer
  this empirically before M2 applies anything.
- **Vacuous tests (R3).** The "legacy still verifies" test must use a frozen hand-authored
  fixture, not a live read. Clear `__pycache__` + `PYTHONDONTWRITEBYTECODE=1` every mutation-verify
  iteration — a stale `.pyc` on a same-size mutation false-greens silently.
- **Green-but-inert (R4).** Unit coverage alone is not proof; M3's real-entry-point re-run is what
  catches a change that passes tests but never reaches production.
- **Partial apply (R5).** New `extraction_status` with stale `edition_binding_sha256` must be
  structurally impossible — write both as one atomic pair, or roll the whole edition back.

## References

- `external_research_resolution.py:304,348-388` — `extract_bytes`, `_MAX_EXTRACT_CHARS`.
- `assertion_registry.py:213-232,246,387,527,702-725,1055` — `verify_source_card_binding`,
  `_provenance_record`, `_write_immutable_mapping`, `_load_provenance`, `_finish_passage_resolved`.
- `assertion_rollout.py:98-119,396,428,473,560` — backfill precedent, shape to copy into `backfill_operations/`.
- `.claude/worknotes/eri-reused-edition-promotion/implementation-notes.md` — reconcile-not-rebuild lessons.

## Milestones

### M1 — Status is recomputable and provable without mutating anything

Pure recompute function + eligibility predicate (gated on `allowed_use.basis`), dry-run only;
resolves OQ-1 without writing anything.

**AC:** dry-run over W reports 35/452/16 (eligible/ineligible/already-set), 34 full_text + 1
partial (or 35 full_text — OQ-1). Receipt records `authoritative_data_mutated: false`.

### M2 — Apply rewrites the 35 pairs reversibly and re-attests provenance

For each of the 35, write `extraction_status` and recompute `edition_binding`/
`edition_binding_sha256` as one atomic pair, snapshotting first; receipt in
`backfill_operations/`. Requires explicit human Mode-D approval before the first live apply.

**AC:** all 35 pass `verify_source_card_binding` post-apply; rollback restores byte-identical
prior state; the 452 untouched, digests unchanged.

### M3 — Live re-prove with the real packet

Re-run the operator packet import through the real intake entry point, not a unit-test stand-in.
**The target run must exist first** — `default_promote` raises `NotFoundError` for an unknown run id
and the resolver maps that to a per-candidate `verification_failed` quarantine, so a missing run looks
like an evidence problem rather than an operator input error.

**AC:** with the target run scaffolded (`rf capture` → `rf triage` → `rf plan`),
`rf intake external-report ~/Downloads/knitwit-s1/packet --workspace default --run
<existing_run_id>` yields `passage_resolved: 4` and `verification_failed == 0` measured on
`receipts/<receipt_digest>/effects/*.yaml`.

## AC -> command -> evidence

| AC | Command | Evidence of pass |
|---|---|---|
| M1 dry-run counts | recompute dry-run script over W | 35/452/16 split + 34 full_text/1 partial (or 35/0); `authoritative_data_mutated: false` |
| M2 re-attestation | `verify_source_card_binding` per edition | all 35 pass; digest diff on the 452 = zero change |
| M2 rollback | apply then rollback, diff workspace tree | byte-identical to pre-apply snapshot |
| M3 live re-run | `rf intake external-report ... --run <existing_run_id>` | `passage_resolved: 4`; `grep -l verification_failed receipts/<digest>/effects/*.yaml \| wc -l` = 0 |

## Sequencing

M1 -> M2 -> M3: M2 gated on M1 resolving OQ-1; M3 meaningful only after M2 lands.

## Execution ledger

Deviations logged to `.claude/worknotes/eri-legacy-extraction-status-backfill/implementation-notes.md`,
reviewed per milestone boundary. **Blockers still stop; Mode-D is non-negotiable** — M2 rewrites
live provenance (irreversible-outward) and requires explicit human approval before first apply.
