## Phase 2 Completion Note — Rights Summary Mirror + Validator (C1)

### Summary

Phase 2 adds a denormalized `rights_summary` mirror (field-identical, `mirror_is_authoritative: const false`,
link-before-assert `allOf` conditional) to both `source_card.schema.yaml` and `source_assertion.schema.yaml`,
a time-parameterized, never-wall-clock divergence validator (`services/rights_validation.py::check_rights_divergence`),
an idempotent, non-clobbering all-`unknown` backfill (`services/rights_backfill.py`), and the `rf rights`
CLI group (`validate`/`backfill` fully implemented; `inspect`/`list` stubbed for P4-5).

### Tasks

- [x] P2-1 → data-layer-expert — `rights_summary` added to `source_card.schema.yaml`; 11-field shape defined (byte-identical replication target for P2-2).
- [x] P2-2 → data-layer-expert — `rights_summary` added to `source_assertion.schema.yaml`, byte-identical to P2-1; dedicated field-set-identity test added (feeds P6-1).
- [x] P2-3 → python-backend-engineer — `check_rights_divergence` built; `as_of` required kwarg, no wall-clock reads (monkeypatch-proven); all 5 H3 scenarios covered + reproducibility test.
- [x] P2-4 → python-backend-engineer — `rf rights validate --as-of` wired via `rights_app`; `--as-of` rejects omission (Click required-option, exit 2). A follow-up dispatch closed a CLI test-coverage gap left by an interrupted first pass (API timeout mid-task; no product-code defect, only missing tests).
- [x] P2-5 → python-backend-engineer — backfill migration (`rights_backfill.py` + `rf rights backfill`); idempotent, non-clobbering, produces schema-valid all-`unknown` summaries; unit-level exit-gate proof (`needs_backfill: True → False`, no divergence) stands in for a corpus-level check since this workspace has no real `runs/` corpus yet.

### Validator Verdict

`task-completion-validator`: **PASS**. All 5 Phase 2 Quality Gates confirmed (AC P2-A mirror identity, time-parameterization + all 5 H3 scenarios, backfill idempotency/non-clobber, CLI `--as-of` required-flag enforcement, full test suite green — 140 tests across `test_schema_validation.py`, `test_rights_validation.py`, `test_rights_backfill.py`, `test_cli_rights.py`). One fix cycle (0 — no fixes required; PASS on first pass). No re-dispatch needed.

**Informational, not blocking** (flagged by validator): `RightsCheckResult.ok` is a `@property`, not a dataclass field, so `as_dict()`/JSON CLI output omits it — external JSON consumers must derive pass/fail from `findings` being non-empty. Self-documented by a test (`test_rights_validate_surfaces_divergence_json`). No AC requires `ok` in the JSON payload; CLI exit-code logic reads `.ok` directly in Python and is unaffected. Left as a follow-up note for whoever touches `rights_validation.py`/`rights` JSON API ergonomics next (candidate: P4-5, when `inspect`/`list` are completed).

### Files Changed

- `schemas/source_card.schema.yaml` — `rights_summary` mirror (P2-1)
- `schemas/source_assertion.schema.yaml` — `rights_summary` mirror, byte-identical (P2-2)
- `src/research_foundry/services/rights_validation.py` — new; `check_rights_divergence` (P2-3)
- `src/research_foundry/services/rights_backfill.py` — new; `backfill_rights_summary` (P2-5)
- `src/research_foundry/cli_commands.py` — `rights_app` (`validate`/`backfill`/`inspect`-stub/`list`-stub) (P2-4, P2-5)
- `tests/test_schema_validation.py` — P2-1/P2-2 schema fixture + identity tests
- `tests/test_rights_validation.py` — new; P2-3 validator tests (all 5 H3 scenarios + wall-clock guard)
- `tests/test_cli_rights.py` — new; P2-4 CLI tests
- `tests/test_rights_backfill.py` — new; P2-5 backfill tests

### Deviations & Risks

- P2-4's first dispatch was interrupted by an API timeout after the implementation landed but before tests/report — recovered by re-dispatching a scoped follow-up to close the test-coverage gap only (no re-implementation). No lasting risk; final result passed the validator gate.
- `RightsCheckResult.ok` JSON-serialization gap (see above) — informational, not required for this phase, carried forward as a note.
- No real `runs/` corpus exists in this workspace yet, so P2-5's corpus-level backfill exit gate is proven at unit-test granularity only (`test_backfill_resolves_needs_backfill_and_no_divergence`), per the validator's explicit acceptance of this substitution.
- Known pre-existing failures out of scope for this gate (carried forward from P1, deferred to P3/P4): `tests/unit/test_assertion_materialization.py`, `tests/unit/test_assertion_backfill.py`, `tests/api/test_assertions_api.py` (evidence_taxonomy required-field regressions) — not touched, not re-verified here.

### Commits (worktree runs)

- `b017b53` — feat(rights): P2 — rights_summary mirror + rights_validation + rf rights CLI
