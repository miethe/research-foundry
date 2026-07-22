"""Bidirectional release-gate tests for ``judgment_basis: unassessed`` (P5-3,
decisions-block OQ-6).

The predicate itself
(:func:`research_foundry.services.governance.release_gate_blocked_by_unassessed_judgment`)
is policy logic owned by ``governance.py``; ``verification.py::verify_report``
is the CALLER — a new named check in its existing check sequence, not a
duplicate implementation. Both directions of the "release-gate asymmetry" NFR
must be tested EXPLICITLY, never assumed from the other:

* a commercial-release verification run with an ``unassessed`` evidence item
  FAILS (blocked);
* an internal-capture write with the SAME ``unassessed`` item SUCCEEDS
  (never blocked).
"""

from __future__ import annotations

import copy

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.governance import (
    release_gate_blocked_by_unassessed_judgment,
)
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml

RUN_ID = "rf_run_20260721_release_gate_demo"
INTENT_ID = "intent_research_20260721_release_gate_demo"

_LEDGER = {
    "id": "claim_ledger_release_gate_demo",
    "intent_id": INTENT_ID,
    "verification_status": "pending",
    "claims": [
        {
            "claim_id": "clm_001",
            "text": "The dataset is licensed for research use",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_20260721_licensing_aaaaaaaa",
                    "evidence_id": "ev_001",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        },
    ],
}


def _write_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": INTENT_ID,
        "title": "Release-gate demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{INTENT_ID}.yaml")


def _write_source_card(paths: FoundryPaths) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    front = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": "src_20260721_licensing_aaaaaaaa",
        "created_at": "2026-07-21T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": "personal",
        "source": {
            "title": "Dataset license terms",
            "source_type": "document",
            "locator": {"url": "https://example.org/license", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-21T09:00:00-04:00",
        },
    }
    dump_md(
        front,
        "# Dataset license terms\n\nSummary of licensing terms.\n",
        rp.sources / "src_20260721_licensing_aaaaaaaa.md",
    )


def _write_report(paths: FoundryPaths) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    front = {
        "type": "report",
        "report_id": "report_release_gate_demo",
        "run_id": RUN_ID,
        "sensitivity": "personal",
    }
    body = (
        "## Findings\n\n"
        "The dataset is licensed for research use. [claim:clm_001]\n"
    )
    dump_md(front, body, rp.report_draft)


def _seed_valid_run(paths: FoundryPaths) -> None:
    """A hand-written run that passes every OTHER verify_report check, so the
    only variable in these tests is the new release-gate check."""

    _write_intent(paths)
    dump_yaml(copy.deepcopy(_LEDGER), paths.run_paths(RUN_ID).claim_ledger)
    _write_source_card(paths)
    _write_report(paths)


# --- Unit-level predicate tests (governance.py) ------------------------------


def test_predicate_blocks_commercial_release_when_unassessed() -> None:
    assert (
        release_gate_blocked_by_unassessed_judgment(
            ["unassessed"], disposition="commercial_release"
        )
        is True
    )


def test_predicate_does_not_block_internal_capture_with_same_item() -> None:
    """The SAME unassessed item, gated by disposition alone, must NOT block
    an internal-capture write — this is the asymmetry, tested explicitly and
    never inferred from the commercial-release direction above."""

    assert (
        release_gate_blocked_by_unassessed_judgment(
            ["unassessed"], disposition="internal_capture"
        )
        is False
    )


def test_predicate_does_not_block_commercial_release_when_assessed() -> None:
    """Sanity: the gate is about `unassessed` specifically, not disposition alone."""

    assert (
        release_gate_blocked_by_unassessed_judgment(
            ["measured"], disposition="commercial_release"
        )
        is False
    )


def test_predicate_handles_empty_and_none_entries() -> None:
    assert (
        release_gate_blocked_by_unassessed_judgment([], disposition="commercial_release")
        is False
    )
    assert (
        release_gate_blocked_by_unassessed_judgment(
            [None, "measured"], disposition="commercial_release"  # type: ignore[list-item]
        )
        is False
    )


# --- verify_report integration (the actual caller) ---------------------------


def test_commercial_release_verification_run_with_unassessed_item_fails(tmp_foundry):
    """Direction 1: a commercial-release verification run with an unassessed
    evidence item FAILS."""

    _seed_valid_run(tmp_foundry)

    result = verify_report(
        RUN_ID,
        paths=tmp_foundry,
        disposition="commercial_release",
        evidence_judgment_bases=["unassessed"],
    )

    by_id = {c.id: c for c in result.checks}
    assert by_id["release_gate_judgment_basis_assessed"].status == "fail"
    assert result.passed is False
    assert result.exit_code != int(ExitCode.OK)


def test_internal_capture_write_with_same_unassessed_item_succeeds(tmp_foundry):
    """Direction 2 (tested EXPLICITLY, not assumed from direction 1 above): an
    internal-capture write with the SAME unassessed evidence item SUCCEEDS."""

    _seed_valid_run(tmp_foundry)

    result = verify_report(
        RUN_ID,
        paths=tmp_foundry,
        disposition="internal_capture",
        evidence_judgment_bases=["unassessed"],
    )

    by_id = {c.id: c for c in result.checks}
    assert by_id["release_gate_judgment_basis_assessed"].status == "pass"
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)


def test_default_call_with_no_evidence_items_is_a_backward_compatible_skip(tmp_foundry):
    """Every pre-existing caller of verify_report supplies neither `disposition`
    nor `evidence_judgment_bases` — this must remain a no-op skip, not a
    silent pass/fail, so no existing behavior regresses."""

    _seed_valid_run(tmp_foundry)

    result = verify_report(RUN_ID, paths=tmp_foundry)

    by_id = {c.id: c for c in result.checks}
    assert by_id["release_gate_judgment_basis_assessed"].status == "skip"
    assert result.passed is True
