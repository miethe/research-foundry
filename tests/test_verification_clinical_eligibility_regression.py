"""RFUP-1 P3-003 — eligibility regression tests (depends_on: P3-002).

Two distinct obligations, per AC-P3-6/AC-P3-7 (phase-3-4-clinical-gate-cluster.md):

1. AC-P3-6: 0 false-positive hard-gates against **existing** non-clinical
   warn-mode regression runs. Two layers of proof:
   a) Real-corpus proof (read-only, no ``verify_report()`` side effects):
      every claim across the 7 already-committed verified pediatric-CDS
      bundles (commit ``aaa9d92``, same corpus as P2-003's
      ``test_seven_verified_bundles_zero_false_positives``) is
      non-eligible for the P3-001 auto-strict override, because every
      ``pediatric_cds`` block on those bundles uses the legacy shape (no
      ``assertion_kind`` field) — see ``claim_clinical_eligibility``'s
      docstring. This is what keeps those 7 bundles from newly tripping
      into strict mode under this filter.
   b) Composed-scenario proof (synthetic, via ``verify_report()``): several
      "almost eligible but not quite" claim shapes — non-threshold
      assertion_kind on an otherwise-plain card; non-threshold assertion_kind
      on an elevated-sensitivity card; legacy pediatric_cds shape (no
      assertion_kind field) on an elevated-sensitivity card; no pediatric_cds
      block at all on an elevated-sensitivity card — all missing their quote
      anchor, composed into ONE warn-mode run. Note: a genuinely
      ``assertion_kind == "threshold"`` point is deliberately NOT one of
      these near-miss shapes — per ``claim_clinical_eligibility``'s own
      docstring, today's schema can only surface that signal from a
      ``pediatric_cds`` block, so a real threshold assertion always implies
      ``pediatric_cds_present`` and is therefore always eligible regardless
      of sensitivity; it would not be a "near-miss," it would just be
      eligible (that positive path is AC-P3-7, covered separately below).
      This proves the four genuine near-misses don't combine to trip a hard
      gate, beyond P3-001's own test file's single-scenario end-to-end check.
2. AC-P3-7: a threshold+clinical-eligible claim lacking a locator (no quote
   anchor to a source card) fails closed end-to-end: non-zero exit code and
   an ``unsupported[]`` append — the positive-path counterpart to (1).

Real-bundle read access mirrors the read-only pattern already established by
``test_pediatric_cds_redteam_fixtures.py``'s ``test_seven_verified_bundles_
zero_false_positives`` (AC-P2-10): this module never calls ``verify_report()``
against the committed bundles, because that function writes
``reviews/verification.yaml`` and updates the claim ledger's
``verification_status`` in place — an unwanted mutation of the
data-plane-split private corpus. Synthetic scenarios use the ``tmp_foundry``
fixture instead, exactly like ``test_verification_clinical_eligibility.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import (
    _index_source_cards,
    claim_clinical_eligibility,
    verify_report,
)
from research_foundry.yamlio import dump_yaml, load_yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Same 7 bundles named in test_pediatric_cds_redteam_fixtures.py (P2-003,
# AC-P2-10) and the phase-3-4 exit criteria's "0 regressions on non-clinical
# warn-mode runs" — hardcoded, not globbed, so an unrelated future run
# directory under runs/ can never silently widen or narrow this regression.
_VERIFIED_BUNDLE_RUN_IDS = (
    "rf_run_20260717_reg_001_pediatric_cds_map_the",
    "rf_run_20260717_reg_004_pediatric_cds_scope_the",
    "rf_run_20260717_rf_cbc_001_pediatric_cds_establish",
    "rf_run_20260717_rf_cbc_002_pediatric_cds_establish",
    "rf_run_20260717_rf_ev_001_pediatric_cds_backfill",
    "rf_run_20260717_rf_gro_002_pediatric_cds_evidence",
    "rf_run_20260717_rf_kid_001_pediatric_cds_evidence",
)


# --- AC-P3-6a: real 7-bundle corpus, read-only, 0 eligible claims ----------


def _real_bundle_paths() -> FoundryPaths:
    return FoundryPaths(root=_REPO_ROOT)


def _load_claims(run_id: str) -> list[dict[str, Any]]:
    rp = _real_bundle_paths().run_paths(run_id)
    assert rp.claim_ledger.exists(), f"expected claim ledger at {rp.claim_ledger}"
    ledger = load_yaml(rp.claim_ledger)
    assert isinstance(ledger, dict)
    return [c for c in (ledger.get("claims") or []) if isinstance(c, dict)]


def test_seven_verified_bundles_zero_eligible_claims():
    """AC-P3-6: the real regression corpus has ZERO claims that resolve
    eligible for the P3-001 auto-strict override — every pediatric_cds block
    on these 7 bundles is the legacy shape (no assertion_kind field), so
    ``claim_clinical_eligibility`` fails safe to non-eligible (AC-P3-3) for
    every one of them. This is the concrete proof behind "0 false-positive
    hard-gates against existing non-clinical warn-mode regression runs" —
    the P3 filter cannot newly hard-gate a claim it never marks eligible."""

    paths = _real_bundle_paths()
    n_claims_checked = 0
    eligible_claim_ids: list[str] = []
    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        rp = paths.run_paths(run_id)
        source_index = _index_source_cards(rp)
        for claim in _load_claims(run_id):
            if not (claim.get("sources") or []):
                continue
            n_claims_checked += 1
            if claim_clinical_eligibility(claim, source_index):
                eligible_claim_ids.append(f"{run_id}#{claim.get('claim_id')}")

    # Sanity: fail loudly (not silently-vacuous-pass) if bundle/claim
    # discovery itself regresses to finding zero sourced claims.
    assert n_claims_checked > 0, "expected at least one sourced claim across the 7 verified bundles"
    assert not eligible_claim_ids, (
        f"{len(eligible_claim_ids)}/{n_claims_checked} claim(s) across the 7 verified bundles "
        "unexpectedly resolved eligible for the P3-001 auto-strict override "
        "(0 false-positive hard-gates required, AC-P3-6):\n" + "\n".join(eligible_claim_ids[:10])
    )


def test_seven_verified_bundles_exact_passage_present_never_hard_gated_by_p3():
    """Belt-and-suspenders on the same corpus, one level closer to
    ``verify_report()``'s own decision without incurring its write side
    effects: for every claim missing a quote anchor on these 7 bundles, the
    per-claim strict/warn bucketing decision
    (``exact_passage_mode == "strict" or claim_clinical_eligibility(...)``,
    ``verification.py``'s exact_passage_present check) can only ever resolve
    to the warn bucket, because the run-level mode defaults to "warn" and
    (per the previous test) eligibility is always False on this corpus."""

    paths = _real_bundle_paths()
    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        rp = paths.run_paths(run_id)
        source_index = _index_source_cards(rp)
        for claim in _load_claims(run_id):
            if claim.get("status") != "supported":
                continue
            cited = [
                s.get("source_card_id") for s in (claim.get("sources") or []) if s.get("source_card_id")
            ]
            if not cited:
                continue
            has_anchor = any(source_index.get(sid, {}).get("has_quote") for sid in cited)
            if has_anchor:
                continue
            # Missing-anchor claim: with the default "warn" run mode, the only
            # way this claim could land in the strict/hard-gate bucket is via
            # claim_clinical_eligibility() — which must be False here.
            assert claim_clinical_eligibility(claim, source_index) is False, (
                f"{run_id}#{claim.get('claim_id')} unexpectedly eligible; "
                "would newly hard-gate a warn-mode regression run (AC-P3-6)"
            )


# --- AC-P3-6b: composed "almost eligible" scenarios, one warn-mode run ----

_INTENT_ID = "intent_research_20260722_p3003"
_RUN_ID = "rf_run_20260722_p3003_regression"

def _valid_rich_pediatric_cds_block(*, assertion_kind: str) -> dict[str, Any]:
    """A ``pediatric_cds`` block satisfying every required field on every one
    of ``PediatricCdsBlockRich``'s 9 top-level sections
    (``schemas/pediatric_cds.schema.json``) — mirrors
    ``test_verification_pediatric_cds.py``'s ``_valid_pediatric_cds_block``
    fixture. Used (rather than the minimal shape in
    ``test_verification_clinical_eligibility.py``) so these composed-run
    scenarios exercise ONLY the P3 eligibility filter, not P2's own
    structural-completeness hard-gate — a rich block missing required
    sections would trip ``pediatric_cds_schema_invalid`` for unrelated
    reasons and mask what this regression is actually proving."""

    return {
        "schema_version": "1.0",
        "module_id": "cbc_suite_v1",
        "evidence_role": "context",
        "source_status": {
            "update_checked_at": "2026-07-01",
            "correction_checked": True,
            "retraction_checked": True,
            "withdrawal_checked": True,
            "supersession_checked": True,
            "superseded_by": None,
            "foundational_exception_reason": None,
        },
        "study": {
            "design": "retrospective_cohort",
            "population": "pediatric",
            "setting": "outpatient",
            "sample_size": 512,
            "inclusion": ["age < 18"],
            "exclusion": ["known hemoglobinopathy"],
            "comparator": None,
            "outcome": "anemia detection",
            "evidence_grade": "B",
        },
        "applicability": {
            "age_min_months": 6,
            "age_max_months_exclusive": 216,
            "sex_or_physiology": "any",
            "gestational": "term",
            "ancestry_or_population": "general",
            "comorbidities": [],
            "jurisdictions": ["US"],
        },
        "laboratory": {
            "test": "CBC",
            "specimen": "whole_blood",
            "method": "automated_hematology_analyzer",
            "analyzer": "Sysmex XN-1000",
            "unit": "g/dL",
            "ucum": "g/dL",
            "reference_interval": "11.0-14.0",
            "timing": "any",
            "preanalytic_requirements": [],
        },
        "implementable_statement": {
            "kind": "threshold",
            "value_or_formula": 11.0,
            "portability": "local_lab_dependent",
            "assertion_kind": assertion_kind,
            "exact_passage_required": True,
        },
        "diagnostic_accuracy": {
            "sensitivity": 0.85,
            "specificity": 0.9,
            "likelihood_ratio_positive": 8.5,
            "likelihood_ratio_negative": 0.17,
            "predictive_value_positive": None,
            "predictive_value_negative": None,
            "confidence_interval": "0.80-0.90",
            "prevalence": None,
        },
        "safety": {
            "contraindications": [],
            "confounders": ["iron deficiency"],
            "false_positive_contexts": [],
            "false_negative_contexts": [],
            "dangerous_exceptions": [],
        },
        "conflict": {
            "conflicts_with_claim_ids": [],
            "conflict_summary": None,
            "safe_representation": "no_conflict",
        },
        "lifecycle": {
            "review_by": "2028-07-01",
            "surveillance_query": "pediatric anemia CBC threshold",
            "owner_role": "clinical_lead",
        },
    }


# Four distinct "close but non-eligible" shapes, each missing its quote
# anchor. None of these should ever land in the strict bucket while the
# run's resolved exact_passage_mode is "warn" (the default, unset here). Each
# fails the AND's first operand (assertion_kind_is_threshold) — see the
# module docstring above for why a genuinely non-threshold assertion_kind
# (never "threshold" itself) is the only way to construct a real near-miss.
_NON_THRESHOLD_PLAIN_POINT = {
    "evidence_id": "ev_non_threshold_plain",
    "locator": "p.1",
    "summary": "non-threshold assertion_kind, otherwise unremarkable public card",
    "pediatric_cds": _valid_rich_pediatric_cds_block(assertion_kind="descriptive"),
}

_NON_THRESHOLD_SENSITIVE_POINT = {
    "evidence_id": "ev_non_threshold",
    "locator": "p.2",
    "summary": "non-threshold assertion_kind on an elevated-sensitivity card",
    "pediatric_cds": _valid_rich_pediatric_cds_block(assertion_kind="implementation_proposed"),
}

_LEGACY_SENSITIVE_POINT = {
    "evidence_id": "ev_legacy",
    "locator": "p.3",
    "summary": "legacy pediatric_cds shape, elevated-sensitivity card",
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

_PLAIN_SENSITIVE_POINT = {
    "evidence_id": "ev_plain",
    "locator": "p.4",
    "summary": "no pediatric_cds block at all, elevated-sensitivity card",
}

_SCENARIOS: dict[str, tuple[dict, str]] = {
    "clm_non_threshold_plain": (_NON_THRESHOLD_PLAIN_POINT, "public"),
    "clm_non_threshold_sensitive": (_NON_THRESHOLD_SENSITIVE_POINT, "client_sensitive"),
    "clm_legacy_sensitive": (_LEGACY_SENSITIVE_POINT, "client_sensitive"),
    "clm_plain_sensitive": (_PLAIN_SENSITIVE_POINT, "work_sensitive"),
}


def _write_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": _INTENT_ID,
        "title": "P3-003 composed-regression demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")


def _write_source_card(paths: FoundryPaths, *, claim_id: str, point: dict, sensitivity: str) -> None:
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    source_card_id = f"src_20260722_p3003_{claim_id}"
    front: dict = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": source_card_id,
        "created_at": "2026-07-22T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": sensitivity,
        "source": {
            "title": f"P3-003 demo source ({claim_id})",
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-22T09:00:00-04:00",
        },
        "extracted_points": [point],
    }
    dump_md(
        front,
        f"# P3-003 demo source ({claim_id})\n\nSummary.\n",
        rp.sources / f"{source_card_id}.md",
    )


def _seed_composed_regression_run(paths: FoundryPaths) -> None:
    _write_intent(paths)
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()

    claims = []
    for claim_id, (point, sensitivity) in _SCENARIOS.items():
        source_card_id = f"src_20260722_p3003_{claim_id}"
        _write_source_card(paths, claim_id=claim_id, point=point, sensitivity=sensitivity)
        claims.append(
            {
                "claim_id": claim_id,
                "text": f"claim text for {claim_id}",
                "materiality": "material",
                "claim_type": "quantitative",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": source_card_id,
                        "evidence_id": point["evidence_id"],
                        "relation": "supports",
                        "locator": point["locator"],
                    }
                ],
            }
        )

    ledger = {
        "id": "claim_ledger_p3003_regression",
        "intent_id": _INTENT_ID,
        "verification_status": "pending",
        "claims": claims,
    }
    dump_yaml(ledger, rp.claim_ledger)


def test_composed_near_eligible_scenarios_stay_warn_only(tmp_foundry):
    """AC-P3-6: four distinct "close but non-eligible" claim shapes, all
    missing their quote anchor, composed into ONE default-warn-mode run.
    None hard-gates: exact_passage_present stays "warn", none is appended to
    unsupported[], and the run still passes end-to-end — proving the
    eligibility filter's narrow trigger (AC-P3-1/AC-P3-3) holds even when
    several near-miss shapes are combined, not just checked one at a time."""

    _seed_composed_regression_run(tmp_foundry)
    synthesize_report(_RUN_ID, paths=tmp_foundry)

    result = verify_report(_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert result.exact_passage_mode == "warn"

    check = by_id["exact_passage_present"]
    assert check.status == "warn"
    for claim_id in _SCENARIOS:
        assert claim_id in check.locations
        assert not any(claim_id in u for u in result.unsupported)

    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)


# --- AC-P3-7: positive path, threshold+clinical-eligible claim fails closed


_ELIGIBLE_RUN_ID = "rf_run_20260722_p3003_eligible_positive"
_ELIGIBLE_INTENT_ID = "intent_research_20260722_p3003_eligible"
_ELIGIBLE_CLAIM_ID = "clm_p3003_eligible"
_ELIGIBLE_SOURCE_ID = "src_20260722_p3003_eligible"

# assertion_kind == "threshold" on a fully valid rich pediatric_cds block —
# the straightforward eligible case (AC-P3-1); pediatric_cds presence is
# implied. Uses the same fully-populated shape as the near-miss scenarios
# above so this positive-path test also stays scoped to the P3 filter, not
# P2's schema hard-gate.
_ELIGIBLE_PEDIATRIC_CDS_BLOCK = _valid_rich_pediatric_cds_block(assertion_kind="threshold")


def _seed_eligible_run_missing_locator(paths: FoundryPaths) -> None:
    """A single threshold+clinical-eligible claim whose only cited source
    card has NO quote anchor (missing locator to an exact passage) — the
    exact scenario AC-P3-7 names: "a threshold+clinical-eligible claim
    lacking a locator"."""

    intent = {
        "id": _ELIGIBLE_INTENT_ID,
        "title": "P3-003 eligible-positive-path demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{_ELIGIBLE_INTENT_ID}.yaml")

    rp = paths.run_paths(_ELIGIBLE_RUN_ID)
    rp.ensure_scaffold()

    front: dict = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": _ELIGIBLE_SOURCE_ID,
        "created_at": "2026-07-22T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": "client_sensitive",
        "source": {
            "title": "P3-003 eligible-positive-path demo source",
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-22T09:00:00-04:00",
        },
        "extracted_points": [
            {
                "evidence_id": "ev_1",
                "locator": "p.1",
                "summary": "hemoglobin threshold, no quote anchor",
                "pediatric_cds": _ELIGIBLE_PEDIATRIC_CDS_BLOCK,
            }
        ],
    }
    dump_md(front, "# P3-003 eligible-positive-path demo\n\nSummary.\n", rp.sources / f"{_ELIGIBLE_SOURCE_ID}.md")

    ledger = {
        "id": "claim_ledger_p3003_eligible_positive",
        "intent_id": _ELIGIBLE_INTENT_ID,
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": _ELIGIBLE_CLAIM_ID,
                "text": "Hemoglobin below 11.0 g/dL indicates anemia in this population",
                "materiality": "material",
                "claim_type": "quantitative",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": _ELIGIBLE_SOURCE_ID,
                        "evidence_id": "ev_1",
                        "relation": "supports",
                        "locator": "p.1",
                    }
                ],
            }
        ],
    }
    dump_yaml(ledger, rp.claim_ledger)


def test_threshold_clinical_eligible_claim_lacking_locator_fails_closed(tmp_foundry):
    """AC-P3-7: a threshold+clinical-eligible claim lacking a locator to an
    exact-passage quote fails closed end-to-end — non-zero exit code AND an
    unsupported[] append — even though the run's own resolved
    exact_passage_mode is the default "warn" (no --exact-passage flag, no
    config override). This is the dedicated P3-003 assertion for the
    positive path named in the task's own AC; P3-001's test file exercises
    the same shape as one property among several in a two-claim run."""

    _seed_eligible_run_missing_locator(tmp_foundry)
    synthesize_report(_ELIGIBLE_RUN_ID, paths=tmp_foundry)

    result = verify_report(_ELIGIBLE_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert result.exact_passage_mode == "warn"

    check = by_id["exact_passage_present"]
    assert check.status == "fail"
    assert _ELIGIBLE_CLAIM_ID in check.locations

    assert any(_ELIGIBLE_CLAIM_ID in u for u in result.unsupported)
    assert result.passed is False
    assert result.exit_code != int(ExitCode.OK)
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
