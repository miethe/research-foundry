"""Regression tests for finding node_01M38EDY9SJBWAH8VX53KH36EA: an empty
claim ledger (``claims: []``) must not verify. Before this fix
``verify_report`` had no check that the ledger contained any claim, so a
0-claim run returned ``passed=True`` / ``verified=True`` vacuously -- every
downstream check simply had nothing to iterate over.
"""

from __future__ import annotations

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import planning
from research_foundry.services.swarm_drive import drive_run
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml
from tests.test_swarm_drive import _write_intent as _sd_write_intent

RUN_ID = "rf_run_20260923_empty_ledger_demo"
INTENT_ID = "intent_research_20260923_empty_ledger_demo"


def _write_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": INTENT_ID,
        "title": "Empty ledger demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / (INTENT_ID + ".yaml"))


def _write_ledger(paths: FoundryPaths, ledger: dict) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(ledger, rp.claim_ledger)


def _write_report(paths: FoundryPaths) -> None:
    rp = paths.run_paths(RUN_ID)
    front = {
        "schema_version": "0.1",
        "type": "report",
        "report_id": "rep_20260923_empty_ledger_demo",
        "sensitivity": "personal",
    }
    dump_md(front, "## Findings\n\nNothing here.\n", rp.report_draft)


def test_empty_ledger_fails_verification(tmp_foundry):
    """(a) claims: [] -> passed is False, ledger_has_claims fails."""
    _write_intent(tmp_foundry)
    ledger = {
        "id": "claim_ledger_empty_demo",
        "intent_id": INTENT_ID,
        "verification_status": "pending",
        "claims": [],
    }
    _write_ledger(tmp_foundry, ledger)
    _write_report(tmp_foundry)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is False
    by_id = {c.id: c for c in result.checks}
    assert by_id["ledger_has_claims"].status == "fail"


def test_nonempty_ledger_still_passes_the_check(tmp_foundry):
    """(b) a ledger with >=1 supported claim still passes ledger_has_claims."""
    _write_intent(tmp_foundry)
    ledger = {
        "id": "claim_ledger_nonempty_demo",
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
                        "source_card_id": "src_20260923_demo_aaaaaaaa",
                        "relation": "supports",
                        "locator": "p.3",
                    }
                ],
            }
        ],
    }
    _write_ledger(tmp_foundry, ledger)
    _write_report(tmp_foundry)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}
    assert by_id["ledger_has_claims"].status == "pass"


def test_drive_run_on_zero_claim_run_is_not_verified(tmp_foundry, tmp_path):
    """(c) drive_run(..., llm_legs="none", providers={}) on a planted run
    whose sources yield no claims (no extraction cards -> build_claim_ledger
    writes claims: []) returns verified is False."""

    intent_id = _sd_write_intent(tmp_foundry)
    result = planning.plan_run(intent_id, profile="personal", paths=tmp_foundry)
    run_id = result.run_id
    rp = tmp_foundry.run_paths(run_id)
    # No source cards / extraction cards seeded -> build_claim_ledger produces
    # zero claims. Pre-seed empty source_candidates so discovery/ingest are
    # skipped (offline resume), matching tests/test_swarm_drive.py's idiom.
    dump_yaml({"source_candidates": []}, rp.source_candidates)

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert state.verified is False
