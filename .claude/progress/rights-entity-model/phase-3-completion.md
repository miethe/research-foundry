## Phase 3 Completion Note — Derived Synthesis (C3)

### Summary

Added first-class `derived_synthesis` provenance to `source_assertion` (conditional `synthesis`
object with `input_refs[]`/`method`/`divergence_notes[]`/`reproduces_source_arrangement`/
`first_party_rights_holder`/`attestation`) and made `source_edition_id`/`passage_id` nullable
only for that evidence type, with a regression guard for every other type. Added a service-layer
write ceiling forcing `synthesis.attestation.status` to `candidate` on every persist path, backed
by an allow-list negative test proving no agent-writable code path can currently, or could in the
future without loudly failing this test, produce `attestation.status: attested`. This closes ONE
of the two §9.10 write-path halves (P5-2, a future phase, closes the other independently).

### Deviation from plan (load-bearing — read before touching P4/P5 in this area)

The plan (`phase-3-4-capture.md`, P3-3/P3-4) names `services/source_cards.py` and
`services/capture.py` as the write-path targets for the attestation ceiling. This is **factually
wrong for this codebase**: grep-verified, neither file constructs a `source_assertion` dict at
all. The only real construction site is `AssertionMaterializer._prepare_one` /
`_write_immutable_assertion` in `src/research_foundry/services/assertion_materialization.py`,
also reused by the backfill path in `src/research_foundry/services/assertion_rollout.py`. P3-3/
P3-4 were redirected to that real site. Karen independently re-derived this via her own grep and
confirmed the redirect is factually correct and the ceiling is genuinely enforced (not dead code).
**P4-1's plan text has the same `source_cards.py`/`capture.py` targeting for capture-time
`rights_summary` emission — this may recur; whoever executes P4 should re-verify the real
construction/ingest site before assuming the plan's named files are correct.**

### Tasks

- [x] P3-1 → data-layer-expert — conditional `synthesis` object added to
      `schemas/source_assertion.schema.yaml` (if/then on `evidence_item_type == derived_synthesis`,
      `input_refs` minItems:2); positive + negative branches both tested.
- [x] P3-2 → data-layer-expert — `source_edition_id`/`passage_id` nullable only for
      `derived_synthesis`; non-synthesis regression guard tested.
- [x] P3-3 → python-backend-engineer — `synthesis.attestation` schema object added; service-layer
      `_enforce_synthesis_attestation_ceiling` added and wired into `_write_immutable_assertion`
      (the sole persist point for `source_assertion` files); forces `status: candidate` whenever a
      `synthesis` block is present.
- [x] P3-4 → python-backend-engineer — allow-list negative test
      (`tests/unit/test_synthesis_attestation_write_ceiling.py`, 8 tests): enumerates real
      construction/entry-point functions across `assertion_materialization.py` +
      `assertion_rollout.py` (and confirms, with a regression guard, that `source_cards.py`/
      `capture.py` construct zero `source_assertion` dicts), adversarially smuggles
      `attestation.status: attested` through monkeypatched inputs on both the forward-materialize
      and backfill paths, and includes a structural (`inspect.signature`) guard that fails loudly
      if any enumerated function grows an attestation-override parameter.

### Validator Verdict

**Reviewer: karen** (Mode-D-adjacent milestone per project's silent-reviewer rule — explicit
verdict required, silence never a pass). Karen independently re-verified the write-path redirect
via her own grep of `src/`, read the ceiling helper and its call site to confirm live (not dead)
code, attempted an adversarial bypass analysis (checked `rights_backfill.py`, `assertion_impact.py`,
API routers, CLI) and found no path that can mint a new attested assertion outside the ceiling.
Ran the full scoped suite herself.

**VERDICT: PASS** (0 fix cycles needed — no required fixes raised).

Non-blocking observations from karen:
- `attestation` sub-object is not itself required when `synthesis` is present (only `input_refs`/
  `method`/`reproduces_source_arrangement` are required) — consistent with the ceiling's
  "fills-missing-attestation" behavior, not a gap, but worth noting for future phases expecting
  `attestation` always present at write time.
- P3-4 correctly scoped to its half of the §9.10 boundary; P5-2 remains responsible for the other
  half (`rights_record.overall_status`/`content_reuse_assessment.decision`).

### Files Changed

- `schemas/source_assertion.schema.yaml` — data-layer-expert (P3-1/P3-2 conditional synthesis +
  nullable locator fields) then python-backend-engineer (P3-3 `attestation` sub-object).
- `src/research_foundry/services/assertion_materialization.py` — python-backend-engineer (P3-3):
  `_prepare_one` now emits `extensions.evidence_taxonomy` defaults (`evidence_item_type: "other"`,
  `judgment_basis: "unassessed"` — honest fail-closed defaults, this path only ever does
  single-passage direct extraction, never synthesis); added
  `_enforce_synthesis_attestation_ceiling`, called from `_write_immutable_assertion`.
- `tests/test_schema_validation.py` — data-layer-expert: 7 new tests (P3-1 positive/negative
  conditional branches, minItems enforcement, P3-2 nullable/non-null regression guards).
- `tests/unit/test_synthesis_attestation_write_ceiling.py` (new) — python-backend-engineer: 8 new
  tests (P3-4 allow-list negative test suite).

### Carry-forward from P1 (evidence_taxonomy required-field breakage) — RESOLVED, not deferred

P1 made `extensions.evidence_taxonomy` required on `source_assertion`, breaking
`tests/unit/test_assertion_materialization.py`, `tests/unit/test_assertion_backfill.py`, and
`tests/api/test_assertions_api.py` (the single production write path,
`AssertionMaterializer._prepare_one`, never set `extensions` at all). Because P3-3's real target
turned out to be the exact same write path, this was fixed in this phase rather than deferred to
P4: `_prepare_one` now sets safe `extensions.evidence_taxonomy` defaults. **All three carry-forward
files are green again** — confirmed via direct pytest run (not self-report):
`tests/unit/test_synthesis_attestation_write_ceiling.py tests/unit/test_assertion_materialization.py
tests/unit/test_assertion_backfill.py tests/api/test_assertions_api.py tests/test_schema_validation.py
tests/test_no_derivation_guard.py` → 326 passed, 0 failed (karen's independently-run count).

### Deviations & Risks

- File-target deviation from plan text (see "Deviation from plan" section above) — flagged for P4.
- No other deviations. No Mode-D escalation was required (the redirect was a mechanical
  "plan named the wrong file" correction, not an ambiguous authorization-boundary judgment call).

### Commits (this run, shared worktree branch `feat/rights-entity-model`)

- `1087982` — feat(rights): P3 — evidence taxonomy + fail-closed writes (§9.10 negative tests, path 1)
