"""Unit + integration tests for RFUP-1 P3-001 — the exact-passage clinical-
eligibility filter (PRD FR-5, OQ-1).

Trigger under test: ``assertion_kind == "threshold"`` AND (a ``pediatric_cds``
block is present on >=1 cited source card OR >=1 cited card carries an
existing elevated-sensitivity tag) — deliberately **not** "threshold alone"
(AC-P3-1). When eligible, the claim's own ``exact_passage_present`` evaluation
is forced to ``strict`` regardless of the run's configured/CLI
``--exact-passage`` value — a per-claim override, not a global mode flip
(AC-P3-2). When the signal is indeterminate the claim defaults to
non-eligible, i.e. today's warn-only behavior (AC-P3-3).

Full regression against real (legacy-shaped) pediatric-CDS bundles and the
default-policy wiring in ``config/claim_policy.yaml`` are P3-002/P3-003 —
out of scope here; these tests cover P3-001's own function contract plus one
end-to-end proof that the override is per-claim, not global.
"""

from __future__ import annotations

import copy

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import claim_clinical_eligibility, verify_report
from research_foundry.yamlio import dump_yaml

# --- Pure-function unit tests: claim_clinical_eligibility -------------------

_RICH_THRESHOLD_POINT = {
    "evidence_id": "ev_1",
    "locator": "p.1",
    "summary": "threshold point",
    "pediatric_cds": {
        "schema_version": "1.0",
        "evidence_role": "threshold",
        "implementable_statement": {
            "kind": "rule_candidate",
            "value_or_formula": "< 11.0",
            "portability": "universal",
            "assertion_kind": "threshold",
            "exact_passage_required": True,
        },
    },
}

_RICH_NON_THRESHOLD_POINT = {
    "evidence_id": "ev_2",
    "locator": "p.2",
    "summary": "non-threshold point",
    "pediatric_cds": {
        "schema_version": "1.0",
        "evidence_role": "context",
        "implementable_statement": {
            "kind": "rule_candidate",
            "value_or_formula": None,
            "portability": "universal",
            "assertion_kind": "implementation_proposed",
            "exact_passage_required": False,
        },
    },
}

_LEGACY_POINT = {
    "evidence_id": "ev_3",
    "locator": "p.3",
    "summary": "legacy point",
    "pediatric_cds": {
        "population": "0-24mo",
        "assay_method": "not method-dependent",
        "threshold": {"value": "< 11.0", "units_ucum": "g/dL", "passage_locator": "p.3"},
        "lifecycle": {
            "effective": None,
            "retire": None,
            "guideline_version": None,
            "supersedes": None,
        },
        "classification": "source_supported_fact",
    },
}

_PLAIN_POINT = {"evidence_id": "ev_4", "locator": "p.4", "summary": "plain point"}


def _claim(*, sources: list[str]) -> dict:
    return {
        "claim_id": "clm_x",
        "text": "irrelevant",
        "status": "supported",
        "sources": [{"source_card_id": sid} for sid in sources],
    }


def _card(*, points: list[dict], sensitivity: str | None = "public") -> dict:
    return {"sensitivity": sensitivity, "has_locator": True, "has_quote": False, "points": points}


def test_eligible_true_rich_threshold_block_present():
    """AC-P3-1: assertion_kind == threshold on a rich pediatric_cds block is
    the straightforward eligible case (pediatric_cds presence is implied)."""

    source_index = {"src_1": _card(points=[_RICH_THRESHOLD_POINT])}
    claim = _claim(sources=["src_1"])
    assert claim_clinical_eligibility(claim, source_index) is True


def test_eligible_true_case_insensitive_assertion_kind():
    point = copy.deepcopy(_RICH_THRESHOLD_POINT)
    point["pediatric_cds"]["implementable_statement"]["assertion_kind"] = "THRESHOLD"
    source_index = {"src_1": _card(points=[point])}
    claim = _claim(sources=["src_1"])
    assert claim_clinical_eligibility(claim, source_index) is True


def test_not_eligible_non_threshold_assertion_kind():
    """assertion_kind resolves, but to a non-threshold value — the AND's
    first operand is False regardless of the clinical-signal OR clause."""

    source_index = {"src_1": _card(points=[_RICH_NON_THRESHOLD_POINT], sensitivity="client_sensitive")}
    claim = _claim(sources=["src_1"])
    assert claim_clinical_eligibility(claim, source_index) is False


def test_not_eligible_legacy_shape_has_no_assertion_kind_field():
    """AC-P3-3: the legacy pediatric_cds shape (the ONLY shape on the 7
    existing verified bundles) has no ``implementable_statement.
    assertion_kind`` field at all — the signal is indeterminate, which fails
    safe to non-eligible even though a pediatric_cds block IS present and the
    card is elevated-sensitivity. This is what keeps SEAM-001's "0
    regressions on the 7 verified bundles" requirement intact."""

    source_index = {"src_1": _card(points=[_LEGACY_POINT], sensitivity="client_sensitive")}
    claim = _claim(sources=["src_1"])
    assert claim_clinical_eligibility(claim, source_index) is False


def test_not_eligible_no_pediatric_cds_block_even_with_elevated_sensitivity():
    """Elevated sensitivity alone (no pediatric_cds block anywhere among the
    claim's cited cards) never satisfies the assertion_kind operand."""

    source_index = {"src_1": _card(points=[_PLAIN_POINT], sensitivity="work_sensitive")}
    claim = _claim(sources=["src_1"])
    assert claim_clinical_eligibility(claim, source_index) is False


def test_not_eligible_claim_with_no_resolvable_cited_cards():
    source_index: dict = {}
    claim = _claim(sources=["src_missing"])
    assert claim_clinical_eligibility(claim, source_index) is False


def test_not_eligible_claim_with_no_sources_at_all():
    source_index = {"src_1": _card(points=[_RICH_THRESHOLD_POINT])}
    claim = {"claim_id": "clm_x", "status": "supported", "sources": []}
    assert claim_clinical_eligibility(claim, source_index) is False


def test_eligible_true_across_multiple_cited_cards():
    """The AND's two operands may resolve from different cited cards on the
    same claim — assertion_kind from one card, the pediatric_cds-presence /
    elevated-sensitivity signal from another."""

    source_index = {
        "src_threshold": _card(points=[_RICH_THRESHOLD_POINT], sensitivity="public"),
        "src_plain": _card(points=[_PLAIN_POINT], sensitivity="public"),
    }
    claim = _claim(sources=["src_threshold", "src_plain"])
    assert claim_clinical_eligibility(claim, source_index) is True


# --- Integration: per-claim override, not a global mode flip (AC-P3-2) ------

_INTENT_ID = "intent_research_20260722_p3001"
_RUN_ID = "rf_run_20260722_p3001_eligibility"
_CLINICAL_SOURCE_ID = "src_20260722_p3001_clinical0"
_PLAIN_SOURCE_ID = "src_20260722_p3001_plain0000"


def _write_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": _INTENT_ID,
        "title": "P3-001 eligibility demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")


def _write_source_card(
    paths: FoundryPaths, *, source_card_id: str, sensitivity: str, points: list[dict]
) -> None:
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    front: dict = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": source_card_id,
        "created_at": "2026-07-22T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": sensitivity,
        "source": {
            "title": "P3-001 demo source",
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-22T09:00:00-04:00",
        },
        "extracted_points": points,
    }
    dump_md(
        front,
        "# P3-001 demo source\n\nSummary of P3-001 demo source.\n",
        rp.sources / f"{source_card_id}.md",
    )


def _write_ledger(paths: FoundryPaths) -> None:
    ledger = {
        "id": "claim_ledger_p3001_eligibility",
        "intent_id": _INTENT_ID,
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_clinical",
                "text": "Hemoglobin below 11.0 g/dL indicates anemia in this population",
                "materiality": "material",
                "claim_type": "quantitative",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": _CLINICAL_SOURCE_ID,
                        "evidence_id": "ev_1",
                        "relation": "supports",
                        "locator": "p.1",
                    }
                ],
            },
            {
                "claim_id": "clm_plain",
                "text": "PaperQA2 supports scientific PDF ingestion",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": _PLAIN_SOURCE_ID,
                        "evidence_id": "ev_4",
                        "relation": "supports",
                        "locator": "p.4",
                    }
                ],
            },
        ],
    }
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(ledger, rp.claim_ledger)


def _seed_run(paths: FoundryPaths) -> None:
    """Two claims, neither with a quote anchor: one threshold+clinical-
    eligible (forced strict per-claim), one ordinary (stays warn) — same run,
    same (default warn) exact_passage_mode."""

    _write_intent(paths)
    _write_ledger(paths)
    _write_source_card(
        paths,
        source_card_id=_CLINICAL_SOURCE_ID,
        sensitivity="client_sensitive",
        points=[
            {
                "evidence_id": "ev_1",
                "locator": "p.1",
                "summary": "hemoglobin threshold",
                "pediatric_cds": _RICH_THRESHOLD_POINT["pediatric_cds"],
            }
        ],
    )
    _write_source_card(
        paths,
        source_card_id=_PLAIN_SOURCE_ID,
        sensitivity="public",
        points=[{"evidence_id": "ev_4", "locator": "p.4", "summary": "plain point"}],
    )


def test_clinical_eligible_claim_forced_strict_while_run_stays_warn(tmp_foundry):
    """AC-P3-2: in a run whose resolved exact_passage_mode is the default
    ("warn"), a threshold+clinical-eligible claim missing its quote anchor
    still fails closed (unsupported[]), while the ordinary claim in the SAME
    run stays warn-only — proving the override is per-claim, not a global
    mode flip, and that non-eligible claims see zero behavior change."""

    _seed_run(tmp_foundry)
    synthesize_report(_RUN_ID, paths=tmp_foundry)

    result = verify_report(_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    # The run's own resolved mode is unchanged — this is a per-claim
    # override, not a global flip.
    assert result.exact_passage_mode == "warn"

    check = by_id["exact_passage_present"]
    assert check.status == "fail"
    assert "clm_clinical" in check.locations
    assert "clm_plain" in check.locations

    assert any("clm_clinical" in u for u in result.unsupported)
    assert not any("clm_plain" in u for u in result.unsupported)

    # Fails closed end-to-end: an eligible claim lacking a locator blocks
    # publish (AC-P3-7's positive-path assertion, exercised here for P3-001).
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)

    # AC-RFUP3-4/3-5: the dedicated violation list stays mode-independent and
    # still reports BOTH claims regardless of which bucket each landed in.
    assert sorted(result.exact_passage_violations) == ["clm_clinical", "clm_plain"]


def test_non_clinical_run_has_zero_regression_when_no_claim_is_eligible(tmp_foundry):
    """Exit criteria: "0 regressions on non-clinical warn-mode runs". A run
    with only the ordinary (non-eligible) claim behaves exactly as it did
    before P3-001 — warn-only, passed, exit code OK."""

    _write_intent(tmp_foundry)
    rp = tmp_foundry.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    ledger = {
        "id": "claim_ledger_p3001_no_regression",
        "intent_id": _INTENT_ID,
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_plain",
                "text": "PaperQA2 supports scientific PDF ingestion",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": _PLAIN_SOURCE_ID,
                        "evidence_id": "ev_4",
                        "relation": "supports",
                        "locator": "p.4",
                    }
                ],
            }
        ],
    }
    dump_yaml(ledger, rp.claim_ledger)
    _write_source_card(
        tmp_foundry,
        source_card_id=_PLAIN_SOURCE_ID,
        sensitivity="public",
        points=[{"evidence_id": "ev_4", "locator": "p.4", "summary": "plain point"}],
    )
    synthesize_report(_RUN_ID, paths=tmp_foundry)

    result = verify_report(_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert result.exact_passage_mode == "warn"
    assert by_id["exact_passage_present"].status == "warn"
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert not any("clm_plain" in u for u in result.unsupported)
