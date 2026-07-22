"""Unit + integration tests for RFUP-1 P4-001/P4-002/P4-003 — the
quote-vs-source fidelity check (PRD FR-6/OQ-3, AC-P4-1..AC-P4-8).

Under test: :func:`research_foundry.services.quote_fidelity.check_quote_fidelity`
compares a claim's cited-source extracted quote against that same source
card's own stored ``extracted_points[].quote`` text — through the two-stage
normalization policy (P4-002) — plus the ``locator_only`` warn path (P4-003)
for cards with nothing stored to diff against — and its wiring into
``verify_report`` as the ``quote_fidelity`` check.

File-based P4-004 fixture scenarios under ``tests/fixtures/quote_fidelity/``
are a separate, additive follow-on task — out of scope here. These tests
cover P4-001's function contract (comparison against already-stored text
only, AC-P4-1), P4-002's two-stage normalization policy (Stage 1 allowlist
never flags, AC-P4-4/AC-P4-5; Stage 2 residual differences always flag/fail
with no auto-correction, AC-P4-6), P4-003's ``locator_only`` warn path
(AC-P4-7/AC-P4-8), and one end-to-end proof that the wiring is non-blocking
by default (AC-P4-3's "no worse than linear, no new I/O" boundary implies no
regression risk to existing runs).
"""

from __future__ import annotations

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import quote_fidelity
from research_foundry.services.quote_fidelity import LOCATOR_ONLY_REASON_CODE, check_quote_fidelity
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml

# --- Pure-function unit tests: check_quote_fidelity -------------------------


def _card(*, points: list[dict], extraction_status: str | None = None) -> dict:
    return {
        "sensitivity": "public",
        "has_locator": True,
        "has_quote": True,
        "points": points,
        "extraction_status": extraction_status,
    }


def _claim(*, claim_id: str, sources: list[dict]) -> dict:
    return {"claim_id": claim_id, "text": "irrelevant", "status": "supported", "sources": sources}


def test_pass_when_extracted_quote_matches_stored_point_quote():
    """AC-P4-1: the claim's cited-source quote is a verbatim substring of the
    source card's own stored extracted_points[].quote text."""

    source_index = {
        "src_1": _card(points=[{"evidence_id": "ev_1", "quote": "the sky is blue today"}])
    }
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "the sky is blue"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []


def test_fail_when_extracted_quote_diverges_from_stored_text():
    """The canonical PMC-superscript-stripping shape: the claim's quote has
    characters the source card's own stored text does not."""

    source_index = {
        "src_1": _card(
            points=[{"evidence_id": "ev_1", "quote": "WBC of 12.5 x10/L was recorded"}]
        )
    }
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "WBC of 12.5 ×10⁹/L"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "fail"
    assert result.locations == ["clm_1 -> src_1"]


def test_skip_when_claim_source_has_no_quote_field():
    """Claims/ledgers written before this task exists have no `quote` field
    on their source entries — additive, never flagged."""

    source_index = {"src_1": _card(points=[{"evidence_id": "ev_1", "quote": "some text"}])}
    claim = _claim(claim_id="clm_1", sources=[{"source_card_id": "src_1"}])
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []


def test_skip_when_source_card_has_no_stored_quote_for_other_reason():
    """A card with no point quotes stored, but whose extraction_status is
    NOT locator_only (e.g. absent -- a card ingested before this field
    existed), is unchanged from before P4-003: silently skipped, not
    warned, not flagged."""

    source_index = {"src_1": _card(points=[{"evidence_id": "ev_1", "quote": None}])}
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "anything at all"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []
    assert result.warn_locations == []


def test_warn_when_source_card_is_locator_only_with_nothing_stored():
    """RFUP-1 P4-003, AC-P4-7/AC-P4-12: a card whose extraction_status is
    explicitly "locator_only" has nothing stored to diff against, so
    fidelity is genuinely unverifiable for that pair -- a distinguishable,
    non-blocking "warn" finding tagged with LOCATOR_ONLY_REASON_CODE, NOT a
    silent skip (AC-P4-1's default) and NOT a Stage-2 "fail"."""

    source_index = {
        "src_1": _card(
            points=[{"evidence_id": "ev_1", "quote": None}],
            extraction_status="locator_only",
        )
    }
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "anything at all"}],
    )
    result = check_quote_fidelity([claim], source_index)

    assert result.status == "warn"
    assert result.status not in ("pass", "fail", "error")
    assert result.warn_locations == ["clm_1 -> src_1"]
    assert "clm_1 -> src_1" in result.locations
    assert result.error_locations == []
    assert LOCATOR_ONLY_REASON_CODE in result.detail
    assert LOCATOR_ONLY_REASON_CODE == "quote_fidelity_unverifiable_locator_only"


def test_skip_when_cited_source_card_does_not_resolve():
    """An unresolved source_card_id is supported_claims_have_source_cards's
    job to flag, not this check's."""

    source_index: dict = {}
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_missing", "quote": "anything"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []


def test_multiple_points_joined_for_comparison():
    """The comparison string spans every stored point quote on the card, not
    just the first — a quote landing entirely inside a later point still
    matches."""

    source_index = {
        "src_1": _card(
            points=[
                {"evidence_id": "ev_1", "quote": "first paragraph text"},
                {"evidence_id": "ev_2", "quote": "second paragraph has the real quote here"},
            ]
        )
    }
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "the real quote"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"


# --- Pure-function unit tests: Stage-1 normalization allowlist (P4-002) ----


def test_stage1_nfkc_normalization_not_flagged():
    """AC-P4-5: a difference NFKC folds away (here, a compatibility ligature
    that NFKC decomposes to its plain-ASCII equivalent) is never flagged --
    it is exactly the class of "safe" difference Stage 1 exists to allow."""

    source_index = {
        "src_1": _card(points=[{"evidence_id": "ev_1", "quote": "the filing was submitted"}])
    }
    claim = _claim(
        claim_id="clm_1",
        # U+FB01 LATIN SMALL LIGATURE FI -- NFKC-decomposes to "fi".
        sources=[{"source_card_id": "src_1", "quote": "the ﬁling was submitted"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []
    assert result.error_locations == []


def test_stage1_whitespace_collapsing_not_flagged():
    """AC-P4-5: irregular whitespace (extra spaces/newlines) in the stored
    text versus the claim's captured quote is a safe difference -- never
    flagged."""

    source_index = {
        "src_1": _card(
            points=[{"evidence_id": "ev_1", "quote": "the   sky is\nblue   today"}]
        )
    }
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "the sky is blue today"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []


def test_stage1_curly_quote_style_not_flagged():
    """AC-P4-5: a "smart"/curly quote-mark rendering versus its straight-ASCII
    equivalent is a safe difference -- NFKC alone does not fold this, so the
    explicit quote-mark mapping in the allowlist must."""

    source_index = {
        "src_1": _card(
            points=[{"evidence_id": "ev_1", "quote": 'the patient’s "chart" was reviewed'}]
        )
    }
    claim = _claim(
        claim_id="clm_1",
        sources=[{"source_card_id": "src_1", "quote": "the patient's “chart” was reviewed"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "pass"
    assert result.locations == []


def test_stage2_residual_difference_survives_normalization_allowlist():
    """AC-P4-6: a genuine material difference (not on the Stage-1 allowlist)
    is still flagged even when combined with Stage-1-safe cosmetic noise --
    the allowlist must not overreach and mask a real corruption."""

    source_index = {
        "src_1": _card(
            points=[{"evidence_id": "ev_1", "quote": "the patient’s dose was 5mg"}]
        )
    }
    claim = _claim(
        claim_id="clm_1",
        # Curly apostrophe (Stage-1-safe) *plus* a genuinely different dose
        # (Stage-2 material) -- the safe part must not launder the real one.
        sources=[{"source_card_id": "src_1", "quote": "the patient's dose was 50mg"}],
    )
    result = check_quote_fidelity([claim], source_index)
    assert result.status == "fail"
    assert result.locations == ["clm_1 -> src_1"]
    assert result.error_locations == []


def test_error_status_when_stage1_normalization_raises(monkeypatch):
    """AC-P4-4: an internal Stage-1 normalization failure (distinct from the
    locator_only/nothing-stored skip case) must surface as a distinguishable
    "error" status -- never silently reported as "pass", and never mis-filed
    as a confirmed Stage-2 "fail" either, since the outcome is genuinely
    unknown."""

    def _boom(_text: str) -> str:
        raise ValueError("simulated Stage-1 normalization failure")

    monkeypatch.setattr(quote_fidelity, "_normalize_stage1", _boom)

    source_index = {"src_1": _card(points=[{"evidence_id": "ev_1", "quote": "some stored text"}])}
    claim = _claim(claim_id="clm_1", sources=[{"source_card_id": "src_1", "quote": "some text"}])
    result = check_quote_fidelity([claim], source_index)

    assert result.status == "error"
    assert result.status not in ("pass", "fail")
    assert result.error_locations == ["clm_1 -> src_1"]
    assert "clm_1 -> src_1" in result.locations


def test_error_status_distinct_from_skip_when_nothing_stored(monkeypatch):
    """AC-P4-4 corollary: "checked and undetermined" (error) must be
    reachable independently of the pre-existing "nothing to check yet" skip
    path (a nothing-stored card whose extraction_status is NOT locator_only,
    so it is out of P4-003's warn scope) -- the two must never be conflated.
    Patching _normalize_stage1 to raise has no effect at all on a pair this
    check still just skips."""

    def _boom(_text: str) -> str:
        raise ValueError("should never be called for a nothing-stored pair")

    monkeypatch.setattr(quote_fidelity, "_normalize_stage1", _boom)

    source_index = {"src_1": _card(points=[{"evidence_id": "ev_1", "quote": None}])}
    claim = _claim(claim_id="clm_1", sources=[{"source_card_id": "src_1", "quote": "anything"}])
    result = check_quote_fidelity([claim], source_index)

    assert result.status == "pass"
    assert result.error_locations == []


# --- Integration: wiring into verify_report is non-blocking by default -----

_INTENT_ID = "intent_research_20260722_p4001"
_RUN_ID = "rf_run_20260722_p4001_fidelity"
_SOURCE_ID = "src_20260722_p4001_fidelity00"


def _write_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": _INTENT_ID,
        "title": "P4-001 fidelity demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")


def _write_source_card(paths: FoundryPaths, *, points: list[dict]) -> None:
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    front: dict = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": _SOURCE_ID,
        "created_at": "2026-07-22T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": "public",
        "source": {
            "title": "P4-001 demo source",
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-22T09:00:00-04:00",
        },
        "extracted_points": points,
    }
    dump_md(
        front,
        "# P4-001 demo source\n\nSummary of P4-001 demo source.\n",
        rp.sources / f"{_SOURCE_ID}.md",
    )


def _write_ledger(paths: FoundryPaths, *, claim_quote: str) -> None:
    ledger = {
        "id": "claim_ledger_p4001_fidelity",
        "intent_id": _INTENT_ID,
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_fidelity",
                "text": "The stored source text supports this factual claim",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": _SOURCE_ID,
                        "evidence_id": "ev_1",
                        "relation": "supports",
                        "locator": "p.1",
                        "quote": claim_quote,
                    }
                ],
            }
        ],
    }
    rp = paths.run_paths(_RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(ledger, rp.claim_ledger)


def test_verify_report_surfaces_quote_fidelity_pass(tmp_foundry):
    """Wiring smoke test: the new check runs as part of `rf verify` and
    passes when the claim's cited quote matches the source card's stored
    text — no impact on the run's overall exit code."""

    _write_intent(tmp_foundry)
    _write_source_card(
        tmp_foundry,
        points=[{"evidence_id": "ev_1", "locator": "p.1", "summary": "s", "quote": "the exact stored passage"}],
    )
    _write_ledger(tmp_foundry, claim_quote="the exact stored passage")
    synthesize_report(_RUN_ID, paths=tmp_foundry)

    result = verify_report(_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert "quote_fidelity" in by_id
    assert by_id["quote_fidelity"].status == "pass"
    assert by_id["quote_fidelity"].severity == "warning"


def test_verify_report_quote_fidelity_mismatch_is_non_blocking(tmp_foundry):
    """AC-P4-3 corollary of this task's scoped severity: a genuine fidelity
    mismatch is surfaced as a "fail"-status, "warning"-severity finding, and
    does NOT by itself flip the run's `passed`/exit_code — P4-002/P4-003 own
    any future decision to escalate this. Zero regression risk to the 7
    verified bundles from wiring this check in."""

    _write_intent(tmp_foundry)
    _write_source_card(
        tmp_foundry,
        points=[{"evidence_id": "ev_1", "locator": "p.1", "summary": "s", "quote": "the stored passage without superscript"}],
    )
    _write_ledger(tmp_foundry, claim_quote="the stored passage WITH a mismatched superscript")
    synthesize_report(_RUN_ID, paths=tmp_foundry)

    result = verify_report(_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert by_id["quote_fidelity"].status == "fail"
    assert by_id["quote_fidelity"].severity == "warning"
    assert "clm_fidelity -> " + _SOURCE_ID in by_id["quote_fidelity"].locations

    # Non-blocking: this check alone must not fail the run.
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert not any("quote_fidelity" in u for u in result.unsupported)
