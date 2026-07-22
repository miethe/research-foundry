"""SEAM-001 -- `rf verify` gate-composition regression (RFUP-1, phase-3-4).

Per ``docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/
phase-3-4-clinical-gate-cluster.md``, SEAM-001 is the mandatory seam-task gate
for the phase's declared ``integration_owner``: P2 (``pediatric_cds_schema_invalid``,
structural-completeness hard-gate), P3 (``claim_clinical_eligibility``'s per-claim
auto-strict override feeding ``exact_passage_present``), and P4
(``quote_fidelity``, extraction-time corruption detection) all converge on
``verify_report`` and must be proven to compose correctly with all three gates
active *simultaneously* -- not just individually, which P2-003/P3-003/P4-004
already cover.

Three obligations, per AC-SEAM-1..AC-SEAM-3 (AC-SEAM-4 is a process gate for
the parent plan's ``karen`` milestone, not a code assertion):

1. AC-SEAM-1: all 7 existing verified pediatric-CDS bundles (commit ``aaa9d92``,
   the same corpus P2-003/P3-003 already regression-test individually) pass
   ``verify_report`` end-to-end with P2+P3+P4 all active. Mirrors the read-only
   convention established by ``test_verification_clinical_eligibility_
   regression.py``'s module docstring: ``verify_report`` writes
   ``reviews/verification.yaml`` and mutates the claim ledger's
   ``verification_status`` in place, so this module never calls it against the
   real, committed data-plane-split bundles directly. Instead each bundle's
   ``sources/``, ``claims/``, and ``reports/`` are copied read-only into an
   isolated ``tmp_foundry`` root and verified there -- the composed end-to-end
   proof AC-SEAM-1 asks for, with zero mutation of the private corpus.

2. AC-SEAM-2: a composed synthetic run (one ``tmp_foundry``, ``verify_report``
   called exactly once) mixes the P2-003 red-team ``pediatric_cds`` fixture set
   (``tests/fixtures/pediatric_cds/red_team/*.json``, reused verbatim via
   ``test_pediatric_cds_redteam_fixtures``'s own loader -- not re-invented here)
   with the P4 quote-corruption shape already exercised by
   ``test_quote_fidelity.py`` (the canonical PMC-superscript-stripping pattern,
   ``×10⁹/L`` -> ``x10/L``) and the P3 positive-path shape from
   ``test_verification_clinical_eligibility_regression.py`` (a threshold+
   clinical-eligible claim lacking a locator). Each fixture must fail for its
   OWN check's reason code, with none of the other two gates' reason codes
   appearing alongside it for that same fixture's claim/source pair (no
   masking).

3. AC-SEAM-3: one additional fixture in that same composed run is deliberately
   BOTH schema-incomplete (P2) AND quote-corrupted (P4) on the same source
   card. Both findings must surface distinctly -- ``pediatric_cds_schema_
   invalid`` fails and contributes exactly one ``unsupported[]`` entry for that
   card, ``quote_fidelity`` independently fails for that claim/source pair in
   its own check, and (since ``quote_fidelity`` is a ``severity: warning``
   check, per ``config/claim_policy.yaml``'s ``verifier_checks`` entry and
   ``verification.py``'s 6d wiring comment) its finding never itself
   contributes to ``unsupported[]`` -- so the one underlying "both broken" data
   issue is never collapsed into a single finding and never double-counted in
   ``unsupported[]``.

P4-003 (``extraction_status: locator_only`` warn handling) and file-based
P4-004 fixtures under ``tests/fixtures/quote_fidelity/`` are not implemented on
this branch yet (only P4-001/P4-002 -- the diff check and its two-stage
normalization policy -- have landed); this module does not exercise or assume
either, and does not implement them (SEAM-001 is a test-authoring task only,
per its own instructions -- it must not modify
``verification.py``/``quote_fidelity.py``/the schema).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

import test_pediatric_cds_redteam_fixtures as _p2_redteam
import test_verification_clinical_eligibility_regression as _p3_regression
from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import verification as verification_module
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Same 7 bundles P2-003/P3-003 already regression-test individually -- reused
# by reference (not re-hardcoded here) so this module can never silently drift
# from theirs.
_VERIFIED_BUNDLE_RUN_IDS = _p2_redteam._VERIFIED_BUNDLE_RUN_IDS


@pytest.fixture(autouse=True)
def _clear_pediatric_cds_schema_cache():
    """Mirror the cache-isolation fixture used by every other pediatric_cds
    test module -- a poisoned cache entry must never leak across modules."""

    verification_module._load_pediatric_cds_schema.cache_clear()
    yield
    verification_module._load_pediatric_cds_schema.cache_clear()


# === AC-SEAM-1: all 7 verified bundles pass composed verify_report =========


def _copy_bundle_run_readonly(paths: FoundryPaths, run_id: str) -> None:
    """Copy one verified bundle's run directory into an isolated foundry root.

    Read-only with respect to the real, committed bundle: ``shutil.copytree``
    only ever reads from ``_REPO_ROOT / "runs" / run_id`` and writes into the
    caller's ``tmp_foundry``. This is what lets AC-SEAM-1 call the real
    ``verify_report`` (needed to prove the composed, end-to-end behavior, not
    just each gate's underlying function in isolation) without the mutation
    hazard ``test_verification_clinical_eligibility_regression.py``'s
    docstring calls out (``reviews/verification.yaml`` write +
    ``verification_status`` update against the private data-plane-split
    corpus).
    """

    src = _REPO_ROOT / "runs" / run_id
    assert src.is_dir(), f"expected verified bundle run dir at {src}"
    dst = paths.run_dir(run_id)
    assert not dst.exists(), f"unexpected pre-existing copy target {dst}"
    shutil.copytree(src, dst)


def test_seven_verified_bundles_pass_verify_report_with_all_three_gates_active(tmp_foundry):
    """AC-SEAM-1: every one of the 7 verified pediatric-CDS bundles passes
    ``verify_report`` end-to-end with P2 (schema), P3 (eligibility), and P4
    (fidelity) all wired in simultaneously -- the composed proof, distinct
    from each gate's own individual 0-false-positive regression
    (``test_seven_verified_bundles_zero_false_positives`` for P2,
    ``test_seven_verified_bundles_zero_eligible_claims`` for P3). P4 has no
    dedicated 7-bundle check of its own yet (P4-004's AC-P4-14 is unchecked in
    the phase plan) -- this is also the first regression proof that
    ``quote_fidelity`` itself introduces zero false positives against the real
    corpus, as a side effect of exercising the full composed pipeline."""

    n_checked = 0
    failures: list[str] = []
    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        _copy_bundle_run_readonly(tmp_foundry, run_id)
        result = verify_report(run_id, paths=tmp_foundry)
        n_checked += 1
        if not (result.passed and result.exit_code == int(ExitCode.OK)):
            by_id = {c.id: c for c in result.checks}
            failing = [c.id for c in by_id.values() if c.status == "fail"]
            failures.append(
                f"{run_id}: passed={result.passed} exit_code={result.exit_code} "
                f"failing_checks={failing} unsupported={result.unsupported[:5]}"
            )

    assert n_checked == len(_VERIFIED_BUNDLE_RUN_IDS)
    assert not failures, (
        "expected all 7 verified pediatric-CDS bundles to pass verify_report "
        "with P2+P3+P4 all active (AC-SEAM-1); failures:\n" + "\n".join(failures)
    )


# === AC-SEAM-2 / AC-SEAM-3: composed synthetic red-team + fidelity run =====

_INTENT_ID = "intent_research_20260722_seam001"
_RUN_ID = "rf_run_20260722_seam001_composed"

# P4 quote-corruption shape reused verbatim from test_quote_fidelity.py's
# `test_fail_when_extracted_quote_diverges_from_stored_text` -- the canonical
# PMC-superscript-stripping pattern this whole cluster exists to catch.
_STORED_TEXT_UNCORRUPTED = "WBC of 12.5 x10/L was recorded in this cohort"
_CITED_TEXT_CORRUPTED = "WBC of 12.5 ×10⁹/L was recorded in this cohort"

# Reused, not re-invented (module docstring): a fully schema-valid rich
# pediatric_cds block with assertion_kind == "threshold", exactly the shape
# test_verification_clinical_eligibility_regression.py's own AC-P3-7 positive
# path uses -- pediatric_cds_present alone (independent of sensitivity) is
# enough to satisfy claim_clinical_eligibility's OR-branch.
_ELIGIBLE_THRESHOLD_BLOCK = _p3_regression._valid_rich_pediatric_cds_block(assertion_kind="threshold")

# One red-team fixture, reused for the AC-SEAM-3 "both broken" card, distinct
# from the standalone loop below only in that its block also gets a
# deliberately quote-corrupted point on the same source card. Chosen because
# it resolves to exactly one schema error (a single missing top-level
# section) -- 03_empty_required_object's "study{} present but every nested
# required field absent" shape produces 9 sub-field errors for one
# violation, which would make the "how many unsupported[] entries" assertion
# below conflate "one JSON-schema check emits one message per violated
# required field" (expected, unrelated to this seam) with genuine
# cross-gate double-counting (the actual AC-SEAM-3 concern).
_BOTH_BROKEN_FIXTURE_STEM = "01_missing_top_level_section"


def _write_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": _INTENT_ID,
        "title": "SEAM-001 gate-composition regression demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")


def _write_source_card(
    paths: FoundryPaths, *, source_card_id: str, point: dict[str, Any], sensitivity: str = "public"
) -> None:
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    front: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": source_card_id,
        "created_at": "2026-07-22T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": sensitivity,
        "source": {
            "title": f"SEAM-001 demo source ({source_card_id})",
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-22T09:00:00-04:00",
        },
        "extracted_points": [point],
    }
    dump_md(
        front,
        f"# SEAM-001 demo source ({source_card_id})\n\nSummary.\n",
        rp.sources / f"{source_card_id}.md",
    )


def _claim(
    *, claim_id: str, source_card_id: str, evidence_id: str, locator: str, quote: str | None
) -> dict[str, Any]:
    source_entry: dict[str, Any] = {
        "source_card_id": source_card_id,
        "evidence_id": evidence_id,
        "relation": "supports",
        "locator": locator,
    }
    if quote is not None:
        source_entry["quote"] = quote
    return {
        "claim_id": claim_id,
        "text": f"claim text for {claim_id}",
        "materiality": "material",
        "claim_type": "factual",
        "status": "supported",
        "confidence": "high",
        "sources": [source_entry],
    }


def _redteam_fixture_scenarios() -> list[dict[str, Any]]:
    """One (claim_id, source_card_id, fixture_doc) scenario per red-team
    fixture (>=5, AC-P2-8) -- reused via ``test_pediatric_cds_redteam_
    fixtures``'s own loader, not re-invented here. Each card's point is
    otherwise clean (a matching, uncorrupted quote) so only the P2 gate has
    anything to flag on it."""

    scenarios = []
    for fixture_path in _p2_redteam._red_team_fixture_paths():
        doc = _p2_redteam._load_fixture(fixture_path)
        stem = fixture_path.stem
        scenarios.append(
            {
                "stem": stem,
                "doc": doc,
                "claim_id": f"clm_redteam_{stem}",
                "source_card_id": f"src_seam_redteam_{stem}",
                "quote": f"Clean stored passage for the {stem} scenario, no corruption.",
            }
        )
    return scenarios


def _seed_composed_seam_run(paths: FoundryPaths) -> None:
    _write_intent(paths)
    claims: list[dict[str, Any]] = []

    # -- P2-only scenarios: one card per red-team fixture, clean matching quote.
    for sc in _redteam_fixture_scenarios():
        _write_source_card(
            paths,
            source_card_id=sc["source_card_id"],
            point={
                "evidence_id": "ev_1",
                "locator": "p.1",
                "summary": f"red-team fixture {sc['stem']}",
                "quote": sc["quote"],
                "pediatric_cds": sc["doc"]["block"],
            },
        )
        claims.append(
            _claim(
                claim_id=sc["claim_id"],
                source_card_id=sc["source_card_id"],
                evidence_id="ev_1",
                locator="p.1",
                quote=sc["quote"],
            )
        )

    # -- P4-only scenario: schema-valid-absent card, quote-corrupted claim.
    _write_source_card(
        paths,
        source_card_id="src_seam_quote_corrupt",
        point={
            "evidence_id": "ev_1",
            "locator": "p.1",
            "summary": "quote-fidelity corruption only, no pediatric_cds block",
            "quote": _STORED_TEXT_UNCORRUPTED,
        },
    )
    claims.append(
        _claim(
            claim_id="clm_quote_corrupted",
            source_card_id="src_seam_quote_corrupt",
            evidence_id="ev_1",
            locator="p.1",
            quote=_CITED_TEXT_CORRUPTED,
        )
    )

    # -- AC-SEAM-3 scenario: BOTH schema-incomplete AND quote-corrupted.
    both_broken_doc = next(
        _p2_redteam._load_fixture(p)
        for p in _p2_redteam._red_team_fixture_paths()
        if p.stem == _BOTH_BROKEN_FIXTURE_STEM
    )
    _write_source_card(
        paths,
        source_card_id="src_seam_both_broken",
        point={
            "evidence_id": "ev_1",
            "locator": "p.1",
            "summary": "schema-invalid AND quote-corrupted on the same card",
            "quote": _STORED_TEXT_UNCORRUPTED,
            "pediatric_cds": both_broken_doc["block"],
        },
    )
    claims.append(
        _claim(
            claim_id="clm_both_broken",
            source_card_id="src_seam_both_broken",
            evidence_id="ev_1",
            locator="p.1",
            quote=_CITED_TEXT_CORRUPTED,
        )
    )

    # -- P3-only scenario: threshold+clinical-eligible claim, no quote anchor.
    _write_source_card(
        paths,
        source_card_id="src_seam_p3_eligible",
        point={
            "evidence_id": "ev_1",
            "locator": "p.1",
            "summary": "clinical threshold claim missing its exact-passage quote anchor",
            "pediatric_cds": _ELIGIBLE_THRESHOLD_BLOCK,
        },
    )
    claims.append(
        _claim(
            claim_id="clm_p3_eligible_missing_locator",
            source_card_id="src_seam_p3_eligible",
            evidence_id="ev_1",
            locator="p.1",
            quote=None,
        )
    )

    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    ledger = {
        "id": "claim_ledger_seam001_composed",
        "intent_id": _INTENT_ID,
        "verification_status": "pending",
        "claims": claims,
    }
    dump_yaml(ledger, rp.claim_ledger)


@pytest.fixture
def _composed(tmp_foundry):
    """Seed the SEAM-001 composed run once and verify it exactly once; every
    assertion below reads from this single ``verify_report`` call so the
    "simultaneously active" requirement (AC-SEAM-1..3) is actually exercised
    once per test, not reconstructed piecemeal per assertion."""

    _seed_composed_seam_run(tmp_foundry)
    synthesize_report(_RUN_ID, paths=tmp_foundry)
    result = verify_report(_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}
    return result, by_id


def test_composed_run_fails_overall_from_both_p2_and_p3_contributions(_composed):
    """Sanity precondition for AC-SEAM-2/AC-SEAM-3: the composed run's overall
    failure is a genuine composition of >=2 distinct gates' unsupported[]
    contributions (not just one gate dominating), and quote_fidelity (a
    severity: warning check) never itself contributes an unsupported[] entry
    -- confirming its findings live only in checks[], never double-counted
    into the blocking list."""

    result, by_id = _composed

    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    assert any("pediatric_cds_schema_invalid" in u for u in result.unsupported)
    assert any("exact_passage" in u for u in result.unsupported)

    qcheck = by_id["quote_fidelity"]
    for loc in qcheck.locations:
        assert not any(loc in u for u in result.unsupported), (
            f"quote_fidelity location {loc!r} unexpectedly counted in unsupported[] "
            "(AC-SEAM-3: a warning-severity finding must never double-count)"
        )


@pytest.mark.parametrize("scenario", _redteam_fixture_scenarios(), ids=lambda s: s["stem"])
def test_red_team_fixture_fails_only_its_own_gate_no_masking(_composed, scenario):
    """AC-SEAM-2: each red-team fixture's card fails ``pediatric_cds_schema_
    invalid`` for its own expected reason code (mirroring ``test_pediatric_
    cds_redteam_fixtures.py``'s own per-fixture assertion), while neither
    ``exact_passage_present`` nor ``quote_fidelity`` also flags that same
    claim/source pair -- proving P3/P4 do not mask or duplicate P2's
    independent finding on a fixture that is P2-only."""

    result, by_id = _composed
    sid = scenario["source_card_id"]
    cid = scenario["claim_id"]

    pcheck = by_id["pediatric_cds_schema_invalid"]
    assert pcheck.status == "fail"
    own_errors = [loc for loc in pcheck.locations if sid in loc]
    assert own_errors, f"expected {sid} to appear in pediatric_cds_schema_invalid's own locations"
    assert any(scenario["doc"]["expect_error_substring"] in loc for loc in own_errors), (
        f"{sid}: expected an error mentioning {scenario['doc']['expect_error_substring']!r}, "
        f"got: {own_errors}"
    )

    qcheck = by_id["quote_fidelity"]
    assert f"{cid} -> {sid}" not in qcheck.locations, (
        f"quote_fidelity unexpectedly also flagged {cid} -> {sid} "
        "(P4 masking a P2-only fixture, AC-SEAM-2)"
    )

    epcheck = by_id["exact_passage_present"]
    assert cid not in epcheck.locations, (
        f"exact_passage_present unexpectedly flagged {cid} "
        "(P3/base gate masking a P2-only fixture, AC-SEAM-2)"
    )


def test_quote_corruption_fixture_fails_only_p4_no_masking(_composed):
    """AC-SEAM-2: the P4-only fixture (PMC-superscript-corruption shape,
    reused from test_quote_fidelity.py) fails ``quote_fidelity`` for its own
    reason, while ``pediatric_cds_schema_invalid`` (no block on this card) and
    ``exact_passage_present`` (the card has a stored quote anchor) both stay
    silent on it."""

    result, by_id = _composed
    sid = "src_seam_quote_corrupt"
    cid = "clm_quote_corrupted"

    qcheck = by_id["quote_fidelity"]
    assert qcheck.status == "fail"
    assert f"{cid} -> {sid}" in qcheck.locations

    pcheck = by_id["pediatric_cds_schema_invalid"]
    assert not any(sid in loc for loc in pcheck.locations), (
        f"pediatric_cds_schema_invalid unexpectedly flagged {sid} "
        "(P2 masking a P4-only fixture, AC-SEAM-2)"
    )

    epcheck = by_id["exact_passage_present"]
    assert cid not in epcheck.locations, (
        f"exact_passage_present unexpectedly flagged {cid} "
        "(base gate masking a P4-only fixture, AC-SEAM-2)"
    )


def test_p3_eligible_missing_locator_fixture_fails_only_p3_no_masking(_composed):
    """AC-SEAM-2: the P3-only fixture (threshold+clinical-eligible claim
    lacking a locator, reused from test_verification_clinical_eligibility_
    regression.py's own AC-P3-7 positive path) fails ``exact_passage_present``
    (strict bucket, per-claim override) for its own reason and appends to
    unsupported[] with the ``[exact_passage]`` prefix, while
    ``pediatric_cds_schema_invalid`` (the block is fully schema-valid) and
    ``quote_fidelity`` (no ``quote`` field to compare) both stay silent on it."""

    result, by_id = _composed
    sid = "src_seam_p3_eligible"
    cid = "clm_p3_eligible_missing_locator"

    epcheck = by_id["exact_passage_present"]
    assert epcheck.status == "fail"
    assert cid in epcheck.locations
    assert any(cid in u and "exact_passage" in u for u in result.unsupported)

    pcheck = by_id["pediatric_cds_schema_invalid"]
    assert not any(sid in loc for loc in pcheck.locations), (
        f"pediatric_cds_schema_invalid unexpectedly flagged {sid} "
        "(P2 masking a P3-only fixture, AC-SEAM-2)"
    )

    qcheck = by_id["quote_fidelity"]
    assert not any(loc.startswith(f"{cid} -> ") for loc in qcheck.locations), (
        f"quote_fidelity unexpectedly flagged {cid} (P4 masking a P3-only fixture, AC-SEAM-2)"
    )


def test_both_broken_fixture_surfaces_both_findings_distinctly_not_double_counted(_composed):
    """AC-SEAM-3: a single source card that is BOTH schema-incomplete (P2)
    AND quote-corrupted (P4) surfaces BOTH findings -- neither collapsed into
    one, nor double-counted in ``unsupported[]``.

    ``pediatric_cds_schema_invalid`` fails and contributes exactly one
    ``unsupported[]`` entry for this card (the schema violation).
    ``quote_fidelity`` independently fails for the same claim/source pair in
    its own check, but (severity ``warning``, per the 6d wiring comment in
    ``verification.py``) never itself appends to ``unsupported[]`` -- so the
    one underlying "both broken" fixture produces exactly ONE unsupported[]
    contribution (from P2), not two, while still surfacing the P4 finding
    visibly in ``checks[]``."""

    result, by_id = _composed
    sid = "src_seam_both_broken"
    cid = "clm_both_broken"

    pcheck = by_id["pediatric_cds_schema_invalid"]
    assert pcheck.status == "fail"
    schema_locs = [loc for loc in pcheck.locations if sid in loc]
    assert schema_locs
    assert any("conflict" in loc for loc in schema_locs), (
        f"expected the {_BOTH_BROKEN_FIXTURE_STEM} fixture's own reason code "
        f"('conflict') among {sid}'s errors, got: {schema_locs}"
    )
    # No bleed-through from the *other* gate's vocabulary into this gate's
    # own error text for this card (distinctness, not just co-occurrence).
    assert not any("does not match" in loc for loc in schema_locs)

    qcheck = by_id["quote_fidelity"]
    assert qcheck.status == "fail"
    assert f"{cid} -> {sid}" in qcheck.locations
    assert "conflict" not in qcheck.detail

    # No double-counting: exactly one unsupported[] contribution for this
    # card, and it is the schema one -- quote_fidelity's independent finding
    # is never counted a second time alongside it.
    schema_unsupported = [u for u in result.unsupported if sid in u]
    assert len(schema_unsupported) == 1, (
        f"expected exactly one unsupported[] entry for {sid} (AC-SEAM-3, no "
        f"double-counting); got: {schema_unsupported}"
    )
    assert "pediatric_cds_schema_invalid" in schema_unsupported[0]
    assert not any(f"{cid} -> {sid}" in u for u in result.unsupported), (
        "quote_fidelity's independent finding for this same card must never "
        "also appear in unsupported[] (AC-SEAM-3)"
    )
