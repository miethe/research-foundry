"""Tests for the `_term_index` backfill service (claim-term-indexing-v1, Phase 3).

TASK-3.1/3.2 cover the service + CLI in isolation with hand-built ledgers.
TASK-3.3/3.4 build realistic ledgers through the real ingest -> extract ->
claim-map pipeline (mirrors ``test_claim_mapping_term_index.py``) so claim
text, evidence_ids, and the deterministic extraction output are produced
exactly as they would be in a live run, then strip `_term_index` to
simulate a legacy pre-P1 ledger that needs backfilling.

Availability note (TASK-3.3): the 7 real pediatric-CDS bundles live in a
private, gitignored data repo (data-plane split) and are not present in
this worktree. Per ``test_verify_byte_inertness.py``'s own precedent for
this exact gap (OQ-A), the "population" validation here uses
pipeline-generated fixtures standing in for that corpus -- never a
fabricated bundle presented as the real one.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.services import claim_mapping, extraction, source_cards
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.term_index import VocabularyError
from research_foundry.services.term_index_backfill import (
    ACTION_BACKFILLED,
    ACTION_SKIPPED_NO_MATCH,
    ACTION_SKIPPED_NO_VOCABULARY,
    ACTION_SKIPPED_PRESENT,
    backfill_term_index,
)
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml, load_yaml

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RUN_ID = "rf_run_20260724_term_index_backfill_test"

_NOTES_TEXT = (
    "Hemoglobin below 11.0 g/dL indicates anemia in this population.\n\n"
    "Ferritin levels help confirm iron deficiency in pediatric patients.\n\n"
    "The clinic schedules a routine visit next month.\n"
)


def _build_real_ledger(paths, tmp_path: Path, *, run_id: str = RUN_ID):
    """Build a real claim_ledger.yaml via ingest -> extract -> claim-map.

    Live P1 write path already attaches `_term_index`; callers that want a
    "pre-P1 / legacy" ledger must call :func:`_strip_term_index` afterward.
    """

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    doc = tmp_path / f"{run_id}_notes.txt"
    doc.write_text(_NOTES_TEXT, encoding="utf-8")
    source_cards.ingest_source(str(doc), run_id=run_id, title="Notes", paths=paths)
    extraction.extract_run(run_id, paths=paths)
    result = claim_mapping.build_claim_ledger(run_id, paths=paths)
    return rp, result.ledger_path


def _strip_term_index(ledger_path: Path) -> dict:
    """Simulate a legacy pre-P1 ledger: remove `_term_index` from every claim."""

    ledger = load_yaml(ledger_path)
    for claim in ledger["claims"]:
        claim.pop("_term_index", None)
    dump_yaml(ledger, ledger_path)
    return ledger


def _invoke(args: list[str], cwd: Path):
    orig = os.getcwd()
    os.chdir(cwd)
    try:
        result = runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(orig)
    return result


# ---------------------------------------------------------------------------
# TASK-3.1: service — dry-run diff, additive-only wet-run, non-clobber
# ---------------------------------------------------------------------------


def test_dry_run_reports_would_backfill_with_zero_writes(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    original_bytes = ledger_path.read_bytes()
    _strip_term_index(ledger_path)
    stripped_bytes = ledger_path.read_bytes()

    results = backfill_term_index([ledger_path], dry_run=True, paths=tmp_foundry)

    would_backfill = [r for r in results if r.action == ACTION_BACKFILLED]
    assert would_backfill, "expected >=1 claim to be reported as would-backfill"
    assert all(r.dry_run is True for r in results)

    # Zero writes: the file is byte-identical to the stripped (pre-backfill) state.
    assert ledger_path.read_bytes() == stripped_bytes
    assert ledger_path.read_bytes() != original_bytes  # sanity: strip actually changed it


def test_wet_run_writes_only_term_index_key_additive_only(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    live_ledger = load_yaml(ledger_path)
    _strip_term_index(ledger_path)

    results = backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)
    backfilled = [r for r in results if r.action == ACTION_BACKFILLED]
    assert backfilled

    after = load_yaml(ledger_path)

    # The backfill reconstructs the exact same `_term_index` the live write
    # path produced (same deterministic extraction over the same text).
    for claim in after["claims"]:
        live_claim = next(c for c in live_ledger["claims"] if c["claim_id"] == claim["claim_id"])
        assert claim.get("_term_index") == live_claim.get("_term_index")

    # Additive-only: every other field is untouched.
    for claim in after["claims"]:
        live_claim = next(c for c in live_ledger["claims"] if c["claim_id"] == claim["claim_id"])
        for key in live_claim:
            if key == "_term_index":
                continue
            assert claim[key] == live_claim[key], f"non-term_index field {key!r} was altered"

    assert after["verification_status"] == live_ledger["verification_status"]
    assert after["id"] == live_ledger["id"]


def test_skips_claims_that_already_have_term_index_non_clobber(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    before = ledger_path.read_bytes()

    # Ledger already carries `_term_index` from the live write path -- backfill
    # over it must be a pure no-op.
    results = backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)

    assert all(r.action == ACTION_SKIPPED_PRESENT for r in results if r.action != ACTION_SKIPPED_NO_MATCH)
    assert not any(r.action == ACTION_BACKFILLED for r in results)
    assert ledger_path.read_bytes() == before


def test_missing_vocabulary_skips_without_writing(tmp_foundry, tmp_path, monkeypatch):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    _strip_term_index(ledger_path)
    before = ledger_path.read_bytes()

    monkeypatch.setattr(
        "research_foundry.services.term_index_backfill.load_vocabulary", lambda paths=None: None
    )

    results = backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)

    assert results
    assert all(r.action == ACTION_SKIPPED_NO_VOCABULARY for r in results)
    assert ledger_path.read_bytes() == before  # zero writes


def test_malformed_vocabulary_raises_and_is_not_softened(tmp_foundry, tmp_path, monkeypatch):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    _strip_term_index(ledger_path)

    def _raise(paths=None):
        raise VocabularyError("malformed vocabulary file (test)")

    monkeypatch.setattr(
        "research_foundry.services.term_index_backfill.load_vocabulary", _raise
    )

    with pytest.raises(VocabularyError):
        backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)


def test_claim_with_zero_vocabulary_hits_stays_absent(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    _strip_term_index(ledger_path)

    results = backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)
    no_match = [r for r in results if r.action == ACTION_SKIPPED_NO_MATCH]
    assert no_match, "the background 'clinic visit' claim should have zero vocabulary hits"

    after = load_yaml(ledger_path)
    by_claim_id = {c["claim_id"]: c for c in after["claims"]}
    for r in no_match:
        assert "_term_index" not in by_claim_id[r.claim_id]


# ---------------------------------------------------------------------------
# TASK-3.2: CLI wiring
# ---------------------------------------------------------------------------


def test_cli_help_names_mandatory_catalog_rebuild_followup():
    result = runner.invoke(app, ["term-index", "backfill", "--help"])
    assert result.exit_code == 0
    assert "rf catalog rebuild" in result.output


def test_cli_default_is_dry_run_zero_writes(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    _strip_term_index(ledger_path)
    before = ledger_path.read_bytes()

    result = _invoke(["term-index", "backfill"], cwd=tmp_foundry.root)

    assert result.exit_code == 0, result.output
    assert ledger_path.read_bytes() == before  # default (no flag) never writes


def test_cli_wet_run_requires_explicit_flag(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    _strip_term_index(ledger_path)
    before = ledger_path.read_bytes()

    result = _invoke(["term-index", "backfill", "--wet-run"], cwd=tmp_foundry.root)

    assert result.exit_code == 0, result.output
    assert ledger_path.read_bytes() != before
    after = load_yaml(ledger_path)
    assert any("_term_index" in c for c in after["claims"])
    assert "Follow-up required" in result.output
    assert "rf catalog rebuild" in result.output


# ---------------------------------------------------------------------------
# TASK-3.3: validate against a pediatric-CDS-style bundle population
#
# The real 7-bundle corpus is not reachable in this worktree (see module
# docstring). Dry-run + wet-run are exercised here against pipeline-generated
# fixtures with the same shape (hemoglobin/ferritin/anemia terminology,
# mixed threshold + background usage roles, a zero-vocabulary-hit claim).
# ---------------------------------------------------------------------------


def test_population_style_dry_run_diff_then_wet_run_against_fixtures_only(tmp_foundry, tmp_path):
    run_ids = [f"{RUN_ID}_pop_a", f"{RUN_ID}_pop_b"]
    ledger_paths = []
    expected_by_run: dict[str, dict] = {}
    for run_id in run_ids:
        _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path, run_id=run_id)
        expected_by_run[run_id] = copy.deepcopy(load_yaml(ledger_path))
        _strip_term_index(ledger_path)
        ledger_paths.append(ledger_path)

    # Dry-run diff, reviewed before any wet run (AC).
    dry_results = backfill_term_index(ledger_paths, dry_run=True, paths=tmp_foundry)
    would_backfill = [r for r in dry_results if r.action == ACTION_BACKFILLED]
    assert would_backfill
    for ledger_path in ledger_paths:
        stripped = load_yaml(ledger_path)
        assert not any("_term_index" in c for c in stripped["claims"])  # zero writes from dry-run

    # Wet-run against these fixtures only.
    wet_results = backfill_term_index(ledger_paths, dry_run=False, paths=tmp_foundry)
    assert [r.action for r in wet_results] == [r.action for r in dry_results]

    for run_id, ledger_path in zip(run_ids, ledger_paths, strict=True):
        after = load_yaml(ledger_path)
        expected = expected_by_run[run_id]
        by_id = {c["claim_id"]: c for c in expected["claims"]}
        for claim in after["claims"]:
            assert claim.get("_term_index") == by_id[claim["claim_id"]].get("_term_index")


# ---------------------------------------------------------------------------
# TASK-3.4 (PHASE EXIT GATE): idempotency, verify-unchanged, interrupt-safety
# ---------------------------------------------------------------------------


def test_idempotency_rerun_on_already_indexed_ledger_is_zero_writes(tmp_foundry, tmp_path):
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path)
    _strip_term_index(ledger_path)

    first = backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)
    assert any(r.action == ACTION_BACKFILLED for r in first)
    after_first_bytes = ledger_path.read_bytes()

    second = backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)

    assert not any(r.action == ACTION_BACKFILLED for r in second)
    assert all(r.action != ACTION_BACKFILLED for r in second)
    assert ledger_path.read_bytes() == after_first_bytes  # 0 writes on re-run


def test_verify_unchanged_before_after_backfill(tmp_foundry, tmp_path):
    """Before/after `rf verify` regression: backfilling `_term_index` onto a
    legacy ledger must not change verification_status, the check table, or
    the exit code -- mirrors test_verify_byte_inertness.py's guard but drives
    the real backfill service instead of a hand-injected block."""

    run_id = f"{RUN_ID}_verify"
    _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path, run_id=run_id)
    synthesize_report(run_id, paths=tmp_foundry)

    _strip_term_index(ledger_path)

    # First `rf verify` call (against the legacy, un-indexed ledger) is the
    # "before" baseline -- it is expected to flip verification_status itself
    # (pending -> passed/failed); that side effect is orthogonal to backfill
    # and must not be conflated with it.
    before = verify_report(run_id, paths=tmp_foundry)
    before_ledger = load_yaml(ledger_path)
    before_verification_status = before_ledger["verification_status"]
    before_attested = {c["claim_id"]: c.get("status") for c in before_ledger["claims"]}
    assert not any("_term_index" in c for c in before_ledger["claims"])

    backfill_term_index([ledger_path], dry_run=False, paths=tmp_foundry)
    after = verify_report(run_id, paths=tmp_foundry)

    assert len(before.checks) > 0, "guard is vacuous if the check table is empty"
    assert [c.id for c in before.checks] == [c.id for c in after.checks]
    assert [c.status for c in before.checks] == [c.status for c in after.checks]
    assert before.passed == after.passed
    assert before.exit_code == after.exit_code
    assert before.unsupported == after.unsupported

    after_ledger = load_yaml(ledger_path)
    assert any("_term_index" in c for c in after_ledger["claims"])  # backfill actually ran
    assert after_ledger["verification_status"] == before_verification_status
    after_attested = {c["claim_id"]: c.get("status") for c in after_ledger["claims"]}
    assert after_attested == before_attested


def test_interrupted_then_rerun_backfill_converges_with_no_duplicate_or_partial_writes(
    tmp_foundry, tmp_path
):
    run_ids = [f"{RUN_ID}_interrupt_a", f"{RUN_ID}_interrupt_b"]
    ledger_paths = []
    for run_id in run_ids:
        _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path, run_id=run_id)
        _strip_term_index(ledger_path)
        ledger_paths.append(ledger_path)

    # Simulate an interruption: only the first ledger gets backfilled...
    backfill_term_index([ledger_paths[0]], dry_run=False, paths=tmp_foundry)
    interrupted_first_snapshot = load_yaml(ledger_paths[0])

    # ...then the process resumes and re-runs across both ledgers.
    resumed_results = backfill_term_index(ledger_paths, dry_run=False, paths=tmp_foundry)

    final_first = load_yaml(ledger_paths[0])
    final_second = load_yaml(ledger_paths[1])

    # The already-backfilled ledger converges to the same content (no
    # duplicate/partial state) and is reported skipped_present, not re-written.
    assert final_first == interrupted_first_snapshot
    first_results = [r for r in resumed_results if r.path == str(ledger_paths[0])]
    assert all(r.action == ACTION_SKIPPED_PRESENT for r in first_results if r.action != ACTION_SKIPPED_NO_MATCH)
    assert not any(r.action == ACTION_BACKFILLED for r in first_results)

    # The un-backfilled ledger from before the interruption is now fully backfilled.
    assert any("_term_index" in c for c in final_second["claims"])

    # A from-scratch run with no interruption converges to the exact same end state.
    run_ids_fresh = [f"{RUN_ID}_fresh_a", f"{RUN_ID}_fresh_b"]
    fresh_paths = []
    for run_id in run_ids_fresh:
        _, ledger_path = _build_real_ledger(tmp_foundry, tmp_path, run_id=run_id)
        _strip_term_index(ledger_path)
        fresh_paths.append(ledger_path)
    backfill_term_index(fresh_paths, dry_run=False, paths=tmp_foundry)

    for interrupted_path, fresh_path in zip(ledger_paths, fresh_paths, strict=True):
        interrupted_ledger = load_yaml(interrupted_path)
        fresh_ledger = load_yaml(fresh_path)
        interrupted_claims = {c["claim_id"]: c.get("_term_index") for c in interrupted_ledger["claims"]}
        fresh_claims = {c["claim_id"]: c.get("_term_index") for c in fresh_ledger["claims"]}
        assert interrupted_claims == fresh_claims
