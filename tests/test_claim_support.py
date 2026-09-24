"""Tests for the deterministic claim-support gate (research_foundry.services.claim_support).

Fixture is the measured defect: an ICA claim-map leg produced 4 "supported"
claims for the M3b L2 run citing a quantum-chemistry library roadmap whose
only text borrowed the QUESTION's own "pass-1" vocabulary while never
appearing in the actually-cited source text.
"""

from __future__ import annotations

from pathlib import Path

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.yamlio import dump_yaml, load_yaml

from research_foundry.services.claim_support import apply_claim_map, support_verdict

_QUESTION = "M3b L2: bind pass-1 results and methods finding (v1 closed, v2 chartered)"
_VIBE_QC_TITLE = "Roadmap - vibe-qc documentation"
_VIBE_QC_SNIPPET = (
    "8-system × 3-method × 2-basis sweep: 20/23 sub-µHa parity "
    "(3 outliers convergence-protocol differences). UHF closed-shell parity "
    "gate passes (UHF M=1 ..."
)
_VIBE_QC_TEXT = _VIBE_QC_TITLE + " " + _VIBE_QC_SNIPPET

_L2_CLAIMS = [
    (
        "The pass-1 computational sweep spanned an 8-system × 3-method × "
        "2-basis matrix (23 total configurations), of which 20 achieved "
        "sub-microhartree parity"
    ),
    (
        "The 3 configurations that failed to reach sub-µHa parity in the "
        "pass-1 sweep are attributed to differences in convergence protocol"
    ),
    (
        "The UHF (unrestricted Hartree-Fock) closed-shell parity validation "
        "gate passed in the pass-1 sweep."
    ),
    (
        "Given 20 of 23 configurations meeting the sub-µHa parity bar, "
        "the pass-1 results support the binding"
    ),
]


def test_l2_claims_rejected_for_borrowing_question_vocabulary() -> None:
    for claim_text in _L2_CLAIMS:
        verdict = support_verdict(claim_text, [_VIBE_QC_TEXT], _QUESTION)
        assert verdict["supported"] is False
        assert "pass" in verdict["borrowed_terms"], verdict


def test_faithful_restatement_accepted_against_unrelated_question() -> None:
    claim_text = "A sweep reached sub-µHa parity on 20 of 23 systems"
    verdict = support_verdict(claim_text, [_VIBE_QC_TEXT], "What is the weather forecast today?")
    assert verdict["supported"] is True, verdict
    assert verdict["reasons"] == []
    assert verdict["borrowed_terms"] == []


def test_number_absent_from_source_is_rejected() -> None:
    claim_text = "The sweep reached sub-µHa parity on 999 of 23 systems"
    verdict = support_verdict(claim_text, [_VIBE_QC_TEXT], "unrelated question about weather")
    assert verdict["supported"] is False
    assert "claim cites numbers absent from its sources" in verdict["reasons"]


def _plant_source_card(run_paths, source_card_id: str, url: str) -> None:
    dump_md(
        {"source_card_id": source_card_id, "source": {"locator": {"url": url}}},
        "(card body written by the model -- never read by claim_support)",
        run_paths.sources / f"{source_card_id}.md",
    )


def test_apply_claim_map_accepts_and_rejects(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_claim_support_fixture"
    run_paths = tmp_foundry.run_paths(run_id)
    run_paths.run.mkdir(parents=True)
    run_paths.sources.mkdir(parents=True)
    dump_yaml({"id": run_id, "intent_id": "intent_research_fixture"}, run_paths.run_yaml)

    good_url = "https://example.org/sweep-report"
    bad_url = "https://example.org/vibe-qc-roadmap"
    _plant_source_card(run_paths, "src_good", good_url)
    _plant_source_card(run_paths, "src_bad", bad_url)

    dump_yaml(
        {
            "source_candidates": [
                {
                    "url": good_url,
                    "title": "Sweep report",
                    "snippet": "A sweep reached sub-µHa parity on 20 of 23 systems.",
                },
                {"url": bad_url, "title": _VIBE_QC_TITLE, "snippet": _VIBE_QC_SNIPPET},
            ]
        },
        run_paths.source_candidates,
    )

    claims = [
        {
            "text": "A sweep reached sub-µHa parity on 20 of 23 systems",
            "sources": [{"source_card_id": "src_good", "relation": "supports"}],
        },
        {
            "text": _L2_CLAIMS[0],
            "sources": [{"source_card_id": "src_bad", "relation": "supports"}],
        },
    ]

    result = apply_claim_map(run_id, claims, question_text=_QUESTION, paths=tmp_foundry)

    assert result["accepted"] == 1
    assert result["rejected"] == 1
    assert Path(result["ledger"]).exists()
    assert Path(result["rejections"]).exists()

    ledger = load_yaml(result["ledger"])
    assert len(ledger["claims"]) == 1
    assert ledger["claims"][0]["sources"][0]["source_card_id"] == "src_good"

    rejections = load_yaml(result["rejections"])
    assert len(rejections["rejections"]) == 1
    assert rejections["rejections"][0]["verdict"]["supported"] is False
