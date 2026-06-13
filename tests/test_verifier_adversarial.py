"""Adversarial / hardening cases for the claim verifier (FOCUS 1 audit).

These were written by an adversarial auditor trying to BREAK claim traceability.
They build minimal reports + ledgers directly (no network) and drive
``verify_report`` to probe hard cases the existing suite does not cover.

IMPORTANT — reading these tests:
Several tests assert the **current (vulnerable) behavior** and are marked
``BUG:`` in their docstring. They exist to (a) prove the defect is real and
reproducible and (b) act as a tripwire: when the verifier is hardened, the
assertion will start failing and the maintainer should flip it to the
``# HARDENED`` expectation noted inline. Tests marked ``GUARD:`` assert correct
behavior we want to keep (regression guards / false-alarm documentation).

Defects found (see the audit findings for full repro):

* BUG-1  inference-status claim cited WITHOUT the **Inference:** label passes
         (exit 0). spec §12.2 marks inference report_label_required: true, but
         there is no ``inference_is_labeled`` check (only speculation has one).
* BUG-2  contradicted-status claim presented as a PLAIN finding passes (exit 0).
         spec §12.2 requires the "Contradicted / do not use as finding" label.
* BUG-3  mixed-status claim presented without the **Mixed evidence:** label
         passes (exit 0). spec §12.2 marks mixed report_label_required: true.
* BUG-4  duplicate claim_id in the ledger: an ``unsupported`` claim is masked
         by a later ``supported`` claim with the same id (last-write-wins in the
         ``claims_by_id`` dict), so ``unsupported_claims_block_publish`` passes.
* WEAK-1 a fake ``**Inference:**`` prefix on a line exempts *all* untagged
         material claims on that line, with no ledger claim of that status.
* WEAK-2 a whole line wrapped in single ``*...*`` emphasis is treated as an
         editorial note and exempted, even if it asserts dangerous claims.
* WEAK-3 a material assertion smuggled under an ``## Open questions`` heading is
         never checked (the section is wholesale exempted).
* WEAK-4 a line beginning ``<!--`` is dropped wholesale; trailing claim text on
         the same line after ``-->`` is silently ignored.
"""

from __future__ import annotations

import copy

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml

RUN_ID = "rf_run_20260613_adversarial"
INTENT_ID = "intent_research_20260613_adversarial"

_SUPPORTED = {
    "claim_id": "clm_sup",
    "text": "The retrieval pipeline indexes documents",
    "materiality": "material",
    "claim_type": "factual",
    "status": "supported",
    "confidence": "high",
    "sources": [
        {
            "source_card_id": "src_a",
            "evidence_id": "ev_a",
            "relation": "supports",
            "locator": "p.1",
        }
    ],
}

_BASE_FRONT = {
    "schema_version": "0.1",
    "type": "research_report",
    "report_id": "rpt_adv",
    "title": "Adversarial probe",
    "intent_id": INTENT_ID,
    "evidence_bundle_id": "pending",
    "created_at": "2026-06-13T09:41:00-04:00",
    "status": "draft",
    "audience": "technical",
    "sensitivity": "personal",
    "claim_policy": "policy",
    "verification_status": "pending",
}


# --- helpers ----------------------------------------------------------------


def _write_intent(paths: FoundryPaths) -> None:
    dump_yaml(
        {
            "id": INTENT_ID,
            "title": "Adversarial intent",
            "type": "research",
            "status": "active",
            "governance": {"sensitivity": "personal", "requires_human_review": False},
            "output": {"audience": "technical"},
        },
        paths.intents_active / f"{INTENT_ID}.yaml",
    )


def _write_source(
    paths: FoundryPaths, sid: str, *, sensitivity: str = "personal"
) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    front = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": sid,
        "created_at": "2026-06-13T09:41:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": sensitivity,
        "source": {
            "title": sid,
            "source_type": "paper",
            "locator": {"url": "https://example.org", "file_path": None},
            "authors": ["A"],
            "accessed_at": "2026-06-13T09:41:00-04:00",
        },
    }
    dump_md(front, f"# {sid}\n", rp.sources / f"{sid}.md")


def _seed(
    paths: FoundryPaths,
    claims: list[dict],
    body: str,
    *,
    sensitivity: str = "personal",
    sources: list[str] | None = None,
):
    _write_intent(paths)
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "id": "ledger",
            "intent_id": INTENT_ID,
            "verification_status": "pending",
            "claims": claims,
            "unresolved_questions": [],
        },
        rp.claim_ledger,
    )
    for sid in sources or ["src_a"]:
        _write_source(paths, sid)
    front = copy.deepcopy(_BASE_FRONT)
    front["sensitivity"] = sensitivity
    dump_md(front, body, rp.report_draft)
    return verify_report(RUN_ID, paths=paths)


def _by(result) -> dict:
    return {c.id: c for c in result.checks}


# --- BUG-1: inference status without the Inference label --------------------


def test_inference_status_unlabeled_passes_BUG(tmp_foundry):
    """BUG-1: a ledger 'inference' claim rendered as a PLAIN finding (no
    **Inference:** label) is published with exit 0. spec §12.2 requires the
    Inference label (report_label_required: true) but the verifier has no
    inference_is_labeled check.

    # HARDENED expectation: result.exit_code != int(ExitCode.OK) and a check
    # flags clm_inf as an unlabeled inference.
    """
    claims = [
        {
            "claim_id": "clm_inf",
            "text": "A unified ledger reduces hallucination",
            "materiality": "material",
            "claim_type": "causal",
            "status": "inference",
            "confidence": "medium",
            "inference_basis": {
                "from_claims": ["clm_sup"],
                "reasoning_summary": "r",
            },
        },
        _SUPPORTED,
    ]
    body = (
        "## Findings\n\n"
        "A unified ledger reduces hallucination. [claim:clm_inf]\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, claims, body)
    # Documents the defect: an inference is presented as a plain finding and passes.
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


# --- BUG-2: contradicted status presented as a plain finding ----------------


def test_contradicted_status_unlabeled_passes_BUG(tmp_foundry):
    """BUG-2: a ledger 'contradicted' claim rendered as a PLAIN finding (label
    stripped) publishes with exit 0 — the most dangerous case, since evidence
    *contradicts* the claim yet it reads as a finding.

    # HARDENED expectation: exit_code != OK; a check flags the unlabeled
    # contradicted claim.
    """
    claims = [
        {
            "claim_id": "clm_con",
            "text": "This drug cures the disease",
            "materiality": "material",
            "claim_type": "factual",
            "status": "contradicted",
            "confidence": "low",
        },
        _SUPPORTED,
    ]
    body = (
        "## Findings\n\n"
        "This drug cures the disease. [claim:clm_con]\n\n"
        "The retrieval pipeline indexes documents. [claim:clm_sup]\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, claims, body)
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


# --- BUG-3: mixed status presented without the Mixed evidence label ----------


def test_mixed_status_unlabeled_passes_BUG(tmp_foundry):
    """BUG-3: a ledger 'mixed' claim rendered without the **Mixed evidence:**
    label publishes with exit 0. spec §12.2 requires the Mixed evidence label.

    # HARDENED expectation: exit_code != OK.
    """
    claims = [
        {
            "claim_id": "clm_mix",
            "text": "Tool X is faster in some benchmarks",
            "materiality": "material",
            "claim_type": "comparative",
            "status": "mixed",
            "confidence": "medium",
            "sources": [
                {
                    "source_card_id": "src_a",
                    "evidence_id": "ev_a",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        },
        _SUPPORTED,
    ]
    body = (
        "## Findings\n\n"
        "Tool X is faster in some benchmarks. [claim:clm_mix]\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, claims, body)
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


def test_speculation_unlabeled_IS_caught_GUARD(tmp_foundry):
    """GUARD: by contrast, an unlabeled 'speculation' claim *is* caught
    (speculation_is_labeled fails). This proves the asymmetry that makes
    BUG-1/2/3 real: only speculation has a label-enforcement check.
    """
    claims = [
        {
            "claim_id": "clm_spec",
            "text": "This pattern will likely become reusable",
            "materiality": "material",
            "claim_type": "prediction",
            "status": "speculation",
            "confidence": "low",
        },
        _SUPPORTED,
    ]
    body = (
        "## Findings\n\n"
        "This pattern will likely become reusable. [claim:clm_spec]\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, claims, body)
    by = _by(result)
    assert by["speculation_is_labeled"].status == "fail"
    assert result.passed is False


# --- BUG-4: duplicate claim_id masks an unsupported claim -------------------


def test_duplicate_claim_id_masks_unsupported_BUG(tmp_foundry):
    """BUG-4: two ledger claims share claim_id 'clm_dup' — an 'unsupported' one
    FIRST, a 'supported' one SECOND. ``claims_by_id`` is built by a dict
    comprehension, so last-write-wins: the unsupported entry is dropped and
    ``unsupported_claims_block_publish`` passes (exit 0).

    # HARDENED expectation: the unsupported duplicate is NOT masked; exit 4.
    """
    claims = [
        {
            "claim_id": "clm_dup",
            "text": "Unverifiable assertion",
            "materiality": "material",
            "claim_type": "factual",
            "status": "unsupported",
            "confidence": "low",
        },
        {
            "claim_id": "clm_dup",
            "text": "A safe supported version",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_a",
                    "evidence_id": "ev_a",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        },
    ]
    body = "## Findings\n\n*No findings rendered.*\n\n## Sources\n\n- src_a\n"
    result = _seed(tmp_foundry, claims, body)
    by = _by(result)
    # HARDENED: the unsupported duplicate is evaluated on the raw claims list and
    # the duplicate id is itself flagged; publish is blocked.
    assert by["unsupported_claims_block_publish"].status == "fail"
    assert by["claim_ids_unique"].status == "fail"
    assert result.exit_code == int(ExitCode.UNSUPPORTED)


def test_duplicate_claim_id_order_sensitivity_GUARD(tmp_foundry):
    """GUARD: the masking in BUG-4 is order-dependent — if the 'unsupported'
    duplicate is LAST it wins and is correctly caught (exit 4). This pins the
    order sensitivity so a fix that de-dupes deterministically is observable.
    """
    claims = [
        {
            "claim_id": "clm_dup",
            "text": "A safe supported version",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_a",
                    "evidence_id": "ev_a",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        },
        {
            "claim_id": "clm_dup",
            "text": "Unverifiable assertion",
            "materiality": "material",
            "claim_type": "factual",
            "status": "unsupported",
            "confidence": "low",
        },
    ]
    body = "## Findings\n\n*No findings rendered.*\n\n## Sources\n\n- src_a\n"
    result = _seed(tmp_foundry, claims, body)
    assert result.exit_code == int(ExitCode.UNSUPPORTED)


# --- WEAK-1: fake **Inference:** label exempts arbitrary claims -------------


def test_fake_inference_label_exempts_untagged_claims_WEAK(tmp_foundry):
    """WEAK-1: an attacker prefixes a line with **Inference:** even though no
    inference ledger claim exists. The label is purely textual and exempts ALL
    untagged material claims on that line (here two dangerous ones), passing
    with exit 0. The label is never reconciled against the ledger.

    # HARDENED expectation: an Inference label with no corresponding inference
    # ledger claim should not silently exempt material content.
    """
    body = (
        "## Findings\n\n"
        "**Inference:** Vaccines cause autism and the system handled 9000 queries.\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, [_SUPPORTED], body)
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


# --- WEAK-2: single-emphasis line treated as a non-claim note ---------------


def test_emphasis_line_exempts_material_claim_WEAK(tmp_foundry):
    """WEAK-2: a whole line wrapped in single ``*...*`` emphasis is treated as
    an editorial note (``_EMPHASIS_LINE``) and dropped before classification,
    so a dangerous untagged assertion italicized as one line passes (exit 0).

    # HARDENED expectation: emphasis alone must not exempt a material claim.
    """
    body = (
        "## Findings\n\n"
        "The retrieval pipeline indexes documents. [claim:clm_sup]\n\n"
        "*Vaccines cause autism and the system is 10x faster than alternatives.*\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, [_SUPPORTED], body)
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


# --- WEAK-3: claims laundered under an exempt heading -----------------------


def test_material_claim_under_open_questions_heading_WEAK(tmp_foundry):
    """WEAK-3: ``## Open questions`` / ``## Sources`` / ``## References`` are
    wholesale-exempt sections. A material assertion (not a question) placed
    under ``## Open questions`` is never checked and the report passes (exit 0).

    # HARDENED expectation: declarative material claims under these headings
    # should still require a tag/label (only genuine questions are exempt).
    """
    body = (
        "## Findings\n\n"
        "The retrieval pipeline indexes documents. [claim:clm_sup]\n\n"
        "## Open questions\n\n"
        "- GPT-Researcher is strictly better than PaperQA2 for all workloads.\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, [_SUPPORTED], body)
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


# --- WEAK-4: HTML-comment-prefixed line drops trailing claim text -----------


def test_html_comment_prefix_drops_trailing_claim_WEAK(tmp_foundry):
    """WEAK-4: a line beginning ``<!--`` is skipped wholesale, so real claim
    text after the comment close on the SAME line is silently ignored and the
    report passes (exit 0).

    # HARDENED expectation: content after ``-->`` on a line should not be
    # exempted from material-claim checks.
    """
    body = (
        "## Findings\n\n"
        "The retrieval pipeline indexes documents. [claim:clm_sup]\n\n"
        "<!-- note --> Use PaperQA2 because it is faster than alternatives.\n\n"
        "## Sources\n\n- src_a\n"
    )
    result = _seed(tmp_foundry, [_SUPPORTED], body)
    assert result.exit_code != int(ExitCode.OK)  # HARDENED: traceability gap now blocked
    assert result.passed is False


# --- GUARD: empty sources list on a supported claim is caught ---------------


def test_supported_claim_empty_sources_is_caught_GUARD(tmp_foundry):
    """GUARD: a 'supported' ledger claim with an EMPTY sources list correctly
    fails supported_claims_have_source_cards (exit 2). Regression guard.
    """
    claims = [
        {
            "claim_id": "clm_es",
            "text": "X is true",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [],
        }
    ]
    body = "## Findings\n\n*No findings rendered.*\n\n## Sources\n\n- None.\n"
    result = _seed(tmp_foundry, claims, body)
    by = _by(result)
    assert by["supported_claims_have_source_cards"].status == "fail"
    assert result.exit_code == int(ExitCode.SCHEMA)


# --- GUARD: governance precedence over unsupported (false-alarm doc) --------


def test_governance_precedence_over_unsupported_GUARD(tmp_foundry):
    """GUARD / FALSE-ALARM: when a public report BOTH leaks a work-sensitive
    source AND contains an untagged material claim, exit code is 3 (GOVERNANCE),
    correctly winning over 4 (UNSUPPORTED) per the contract precedence. Verified
    correct; documented so it is not re-flagged.
    """
    claims = [
        {
            "claim_id": "clm_sup",
            "text": "The internal system indexes documents",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_ws",
                    "evidence_id": "ev_a",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        }
    ]
    _write_intent(tmp_foundry)
    rp = tmp_foundry.run_paths(RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "id": "ledger",
            "intent_id": INTENT_ID,
            "verification_status": "pending",
            "claims": claims,
            "unresolved_questions": [],
        },
        rp.claim_ledger,
    )
    _write_source(tmp_foundry, "src_ws", sensitivity="work_sensitive")
    front = copy.deepcopy(_BASE_FRONT)
    front["sensitivity"] = "public"
    body = (
        "## Findings\n\n"
        "The internal system indexes documents. [claim:clm_sup]\n\n"
        "Use PaperQA2 for everything.\n\n"
        "## Sources\n\n- src_ws\n"
    )
    dump_md(front, body, rp.report_draft)
    result = verify_report(RUN_ID, paths=tmp_foundry)
    by = _by(result)
    assert by["work_sensitive_claims_block_public_report"].status == "fail"
    assert by["material_claims_have_claim_ids"].status == "fail"
    assert result.exit_code == int(ExitCode.GOVERNANCE)
