---
it_schema: 1
feature_slug: eri-legacy-extraction-status-backfill
title: "ERI legacy extraction_status backfill — implementation plan"
doc_type: implementation_plan
status: draft
tier: 2
priority: P2
points: 13
risk_level: high
context_class: C3
created: 2026-07-31
updated: 2026-07-31
prd_ref: null
related_documents:
  - docs/project_plans/implementation_plans/enhancements/eri-reused-edition-promotion-v1.md
  - .claude/worknotes/eri-reused-edition-promotion/implementation-notes.md
acceptance_criteria:
  - "The 35 ERI-acquired editions carry a recomputed extraction_status; the 452 rollout editions are untouched."
  - "A live re-run of the operator packet shows verification_failed < 4."
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
      exit_criteria: ["Operator packet re-import yields passage_resolved with verification_failed < 4"]
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

**AC:** `rf intake external-report ~/Downloads/knitwit-s1/packet --workspace default --run
rf_run_20260731_knitwit_s1_postbackfill` yields `verification_failed < 4`.

## AC -> command -> evidence

| AC | Command | Evidence of pass |
|---|---|---|
| M1 dry-run counts | recompute dry-run script over W | 35/452/16 split + 34 full_text/1 partial (or 35/0); `authoritative_data_mutated: false` |
| M2 re-attestation | `verify_source_card_binding` per edition | all 35 pass; digest diff on the 452 = zero change |
| M2 rollback | apply then rollback, diff workspace tree | byte-identical to pre-apply snapshot |
| M3 live re-run | `rf intake external-report ... --run rf_run_20260731_knitwit_s1_postbackfill` | `by_completeness_tier.verification_failed < 4` |

## Sequencing

M1 -> M2 -> M3: M2 gated on M1 resolving OQ-1; M3 meaningful only after M2 lands.

## Execution ledger

Deviations logged to `.claude/worknotes/eri-legacy-extraction-status-backfill/implementation-notes.md`,
reviewed per milestone boundary. **Blockers still stop; Mode-D is non-negotiable** — M2 rewrites
live provenance (irreversible-outward) and requires explicit human approval before first apply.
