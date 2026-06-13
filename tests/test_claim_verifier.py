"""Adversarial tests for the report claim verifier (the crown jewel).

These build a run with a hand-written, minimal-but-valid claim ledger and prove
that ``synthesize_report`` + ``verify_report`` behave exactly per spec §12.3 and
the documented exit-code precedence (research_foundry.errors.ExitCode):

* happy path passes (exit 0)
* an untagged material claim injected into the body -> exit 4 (UNSUPPORTED)
* a [claim:] tag absent from the ledger -> all_claim_ids_exist fails
* a ledger claim with status 'unsupported' -> exit 4
* an inference claim missing inference_basis.from_claims -> inferences_have_basis fails
* a work-sensitive cited source in a public report -> exit 3 (GOVERNANCE)
"""

from __future__ import annotations

import copy

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml

RUN_ID = "rf_run_20260613_verifier_demo"
INTENT_ID = "intent_research_20260613_verifier_demo"

# Hand-written, minimal-but-valid claim ledger: 2 supported (with sources),
# 1 inference (with basis.from_claims), 1 speculation, plus unresolved questions.
LEDGER = {
    "id": "claim_ledger_verifier_demo",
    "intent_id": INTENT_ID,
    "verification_status": "pending",
    "claims": [
        {
            "claim_id": "clm_001",
            "text": "PaperQA2 supports scientific PDF ingestion",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_20260613_paperqa2_aaaaaaaa",
                    "evidence_id": "ev_001",
                    "relation": "supports",
                    "locator": "p.3",
                }
            ],
        },
        {
            "claim_id": "clm_002",
            "text": "The retrieval pipeline indexes documents before answering",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "medium",
            "sources": [
                {
                    "source_card_id": "src_20260613_pipeline_bbbbbbbb",
                    "evidence_id": "ev_002",
                    "relation": "supports",
                    "locator": "sec.2",
                }
            ],
        },
        {
            "claim_id": "clm_007",
            "text": "A unified claim ledger likely reduces synthesis hallucination",
            "materiality": "material",
            "claim_type": "causal",
            "status": "inference",
            "confidence": "medium",
            "inference_basis": {
                "from_claims": ["clm_001", "clm_002"],
                "reasoning_summary": "Both supported claims constrain synthesis to cited evidence.",
            },
        },
        {
            "claim_id": "clm_012",
            "text": "This pattern will likely become a reusable research skill",
            "materiality": "material",
            "claim_type": "prediction",
            "status": "speculation",
            "confidence": "low",
        },
    ],
    "unresolved_questions": [
        {
            "question": "How should contradicting sources be weighted?",
            "why_unresolved": "No primary benchmark found.",
            "recommended_next_source": None,
        }
    ],
}


def _write_intent(paths: FoundryPaths, *, requires_human_review: bool = False) -> None:
    intent = {
        "id": INTENT_ID,
        "title": "Verifier demo intent",
        "type": "research",
        "status": "active",
        "governance": {
            "sensitivity": "personal",
            "requires_human_review": requires_human_review,
        },
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{INTENT_ID}.yaml")


def _write_source_card(
    paths: FoundryPaths,
    source_card_id: str,
    *,
    title: str,
    sensitivity: str = "personal",
    with_locator: bool = True,
) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    front = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": source_card_id,
        "created_at": "2026-06-13T09:41:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": sensitivity,
        "source": {
            "title": title,
            "source_type": "paper",
            "locator": (
                {"url": "https://example.org/paper", "file_path": None}
                if with_locator
                else {"url": None, "file_path": None}
            ),
            "authors": ["A. Author"],
            "accessed_at": "2026-06-13T09:41:00-04:00",
        },
    }
    dump_md(front, f"# {title}\n\nSummary of {title}.\n", rp.sources / f"{source_card_id}.md")


def _write_ledger(paths: FoundryPaths, ledger: dict) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(ledger, rp.claim_ledger)


def _seed_happy_run(paths: FoundryPaths) -> None:
    _write_intent(paths)
    _write_ledger(paths, copy.deepcopy(LEDGER))
    _write_source_card(
        paths, "src_20260613_paperqa2_aaaaaaaa", title="PaperQA2 documentation"
    )
    _write_source_card(
        paths, "src_20260613_pipeline_bbbbbbbb", title="Retrieval pipeline note"
    )


# --- Tests ------------------------------------------------------------------


def test_synthesize_then_verify_passes(tmp_foundry):
    _seed_happy_run(tmp_foundry)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    assert synth.report_path.exists()
    # Supported, inference and speculation claims are all cited; unsupported are not.
    assert set(synth.claims_cited) == {"clm_001", "clm_002", "clm_007", "clm_012"}

    body = synth.report_path.read_text(encoding="utf-8")
    assert "[claim:clm_001]" in body
    assert "**Inference:**" in body and "[claim:clm_007]" in body
    assert "**Speculation:**" in body and "[claim:clm_012]" in body

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert result.unsupported == []
    assert result.verification_path.exists()

    # The ledger's verification_status is flipped to passed.
    rp = tmp_foundry.run_paths(RUN_ID)
    from research_foundry.yamlio import load_yaml

    assert load_yaml(rp.claim_ledger)["verification_status"] == "passed"

    # Every error-severity check passed.
    by_id = {c.id: c for c in result.checks}
    for check_id in (
        "report_has_frontmatter",
        "all_claim_ids_exist",
        "material_claims_have_claim_ids",
        "supported_claims_have_source_cards",
        "inferences_have_basis",
        "speculation_is_labeled",
        "unsupported_claims_block_publish",
        "work_sensitive_claims_block_public_report",
    ):
        assert by_id[check_id].status == "pass", by_id[check_id]


def test_untagged_material_claim_is_unsupported(tmp_foundry):
    _seed_happy_run(tmp_foundry)
    synth = synthesize_report(RUN_ID, paths=tmp_foundry)

    # Inject an UNTAGGED material (quantitative) claim into the Findings section.
    meta, body = load_md(synth.report_path)
    injected = "The benchmark used 1,000 queries."
    body = body.replace(
        "## Findings\n",
        f"## Findings\n\n{injected}\n",
        1,
    )
    dump_md(meta, body, synth.report_path)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    assert result.passed is False
    assert injected in result.unsupported
    by_id = {c.id: c for c in result.checks}
    assert by_id["material_claims_have_claim_ids"].status == "fail"
    assert injected in by_id["material_claims_have_claim_ids"].locations


def test_unknown_claim_tag_fails_existence_check(tmp_foundry):
    _seed_happy_run(tmp_foundry)
    synth = synthesize_report(RUN_ID, paths=tmp_foundry)

    meta, body = load_md(synth.report_path)
    # Reference a claim id that is NOT in the ledger. Tag it so it isn't also
    # an untagged-material failure — we want all_claim_ids_exist to be the cause.
    body = body.replace(
        "## Findings\n",
        "## Findings\n\nGhost finding. [claim:clm_999]\n",
        1,
    )
    dump_md(meta, body, synth.report_path)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}
    assert by_id["all_claim_ids_exist"].status == "fail"
    assert by_id["all_claim_ids_exist"].severity == "error"
    assert "clm_999" in by_id["all_claim_ids_exist"].locations
    assert result.passed is False


def test_unsupported_ledger_claim_blocks_publish(tmp_foundry):
    _write_intent(tmp_foundry)
    ledger = copy.deepcopy(LEDGER)
    ledger["claims"].append(
        {
            "claim_id": "clm_099",
            "text": "An unverifiable assertion with no source or label",
            "materiality": "material",
            "claim_type": "factual",
            "status": "unsupported",
            "confidence": "low",
        }
    )
    _write_ledger(tmp_foundry, ledger)
    _write_source_card(
        tmp_foundry, "src_20260613_paperqa2_aaaaaaaa", title="PaperQA2 documentation"
    )
    _write_source_card(
        tmp_foundry, "src_20260613_pipeline_bbbbbbbb", title="Retrieval pipeline note"
    )

    # Synthesize: the unsupported claim is intentionally NOT rendered into the body.
    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    assert "clm_099" not in synth.claims_cited

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    by_id = {c.id: c for c in result.checks}
    assert by_id["unsupported_claims_block_publish"].status == "fail"
    assert "clm_099" in by_id["unsupported_claims_block_publish"].locations
    assert any("clm_099" in u for u in result.unsupported)


def test_inference_without_basis_fails(tmp_foundry):
    _write_intent(tmp_foundry)
    ledger = copy.deepcopy(LEDGER)
    # Strip the inference basis from clm_007.
    for c in ledger["claims"]:
        if c["claim_id"] == "clm_007":
            c.pop("inference_basis", None)
    _write_ledger(tmp_foundry, ledger)
    _write_source_card(
        tmp_foundry, "src_20260613_paperqa2_aaaaaaaa", title="PaperQA2 documentation"
    )
    _write_source_card(
        tmp_foundry, "src_20260613_pipeline_bbbbbbbb", title="Retrieval pipeline note"
    )

    synthesize_report(RUN_ID, paths=tmp_foundry)
    result = verify_report(RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}
    assert by_id["inferences_have_basis"].status == "fail"
    assert "clm_007" in by_id["inferences_have_basis"].locations
    assert result.passed is False
    # An error-severity failure with no unsupported/governance issue maps to SCHEMA.
    assert result.exit_code == int(ExitCode.SCHEMA)


def test_work_sensitive_source_in_public_report_is_governance(tmp_foundry):
    _seed_happy_run(tmp_foundry)
    # Make one cited source card work-sensitive.
    _write_source_card(
        tmp_foundry,
        "src_20260613_pipeline_bbbbbbbb",
        title="Internal retrieval pipeline note",
        sensitivity="work_sensitive",
    )

    # Synthesize a PUBLIC report (overrides intent's personal default).
    synth = synthesize_report(RUN_ID, sensitivity="public", paths=tmp_foundry)
    meta, _ = load_md(synth.report_path)
    assert meta["sensitivity"] == "public"

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.exit_code == int(ExitCode.GOVERNANCE)
    by_id = {c.id: c for c in result.checks}
    assert by_id["work_sensitive_claims_block_public_report"].status == "fail"
    assert "src_20260613_pipeline_bbbbbbbb" in (
        by_id["work_sensitive_claims_block_public_report"].locations
    )


def test_human_review_flag_surfaced(tmp_foundry):
    _write_intent(tmp_foundry, requires_human_review=True)
    _write_ledger(tmp_foundry, copy.deepcopy(LEDGER))
    _write_source_card(
        tmp_foundry, "src_20260613_paperqa2_aaaaaaaa", title="PaperQA2 documentation"
    )
    _write_source_card(
        tmp_foundry, "src_20260613_pipeline_bbbbbbbb", title="Retrieval pipeline note"
    )
    synthesize_report(RUN_ID, paths=tmp_foundry)
    result = verify_report(RUN_ID, paths=tmp_foundry)
    # Service exposes the flag; it does NOT change the exit code (CLI maps that).
    assert result.human_review_required is True
    assert result.exit_code == int(ExitCode.OK)
