"""TASK-1.6b (ENTRY-BLOCKING GUARD TEST): `rf verify`'s byte-inertness to an
injected `_term_index` key, across >=2 fixture ledgers (OQ-A) -- one
populated ledger (multiple claims/statuses) and one zero-vocabulary-hit
fixture. Asserts byte-identical console output, an unchanged check table
(same ids/order), and 0 status flips.

Mirrors the empirical before/after validation recorded in the design spec
(claim-term-indexing.md §3) for the real 87-claim pediatric-CDS ledger
(rf_run_20260717_rf_cbc_001_pediatric_cds_establish) -- that ledger is not
re-encoded here because it lives in the private, gitignored data repo
(data-plane split) and is not available in this worktree; these two
synthetic fixtures satisfy the same >=2-run / populated-plus-zero-hit
breadth this task's acceptance criteria ask for (OQ-A).
"""

from __future__ import annotations

import copy
import io

import pytest
from rich.console import Console

from research_foundry import cli_commands
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml

INTENT_ID = "intent_research_20260724_byte_inertness"

POPULATED_LEDGER = {
    "id": "claim_ledger_byte_inertness_populated",
    "intent_id": INTENT_ID,
    "verification_status": "pending",
    "claims": [
        {
            "claim_id": "clm_001",
            "text": "Hemoglobin below 11.0 g/dL indicates anemia in this population.",
            "materiality": "material",
            "claim_type": "quantitative",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": "src_20260724_cbc_aaaaaaaa",
                    "evidence_id": "ev_001",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        },
        {
            "claim_id": "clm_002",
            "text": "Ferritin levels help confirm iron deficiency in pediatric patients.",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "medium",
            "sources": [
                {
                    "source_card_id": "src_20260724_ferritin_bbbbbbbb",
                    "evidence_id": "ev_002",
                    "relation": "supports",
                    "locator": "p.2",
                }
            ],
        },
        {
            "claim_id": "clm_003",
            "text": "A unified CBC panel likely reduces repeat draws in this cohort",
            "materiality": "material",
            "claim_type": "causal",
            "status": "inference",
            "confidence": "medium",
            "inference_basis": {
                "from_claims": ["clm_001", "clm_002"],
                "reasoning_summary": "Both supported claims constrain a shared panel recommendation.",
            },
        },
        {
            "claim_id": "clm_004",
            "text": "This pattern will likely generalize to other pediatric CBC screens",
            "materiality": "material",
            "claim_type": "prediction",
            "status": "speculation",
            "confidence": "low",
        },
    ],
    "unresolved_questions": [],
}

ZERO_HIT_LEDGER = {
    "id": "claim_ledger_byte_inertness_zero_hit",
    "intent_id": INTENT_ID,
    "verification_status": "pending",
    "claims": [
        {
            "claim_id": "clm_001",
            "text": "The retrieval pipeline indexes documents before answering",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "medium",
            "sources": [
                {
                    "source_card_id": "src_20260724_pipeline_cccccccc",
                    "evidence_id": "ev_001",
                    "relation": "supports",
                    "locator": "p.1",
                }
            ],
        },
    ],
    "unresolved_questions": [],
}


def _write_source_card(paths: FoundryPaths, run_id: str, source_card_id: str, title: str) -> None:
    rp = paths.run_paths(run_id)
    front = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": source_card_id,
        "created_at": "2026-07-24T09:00:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": "personal",
        "source": {
            "title": title,
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-24T09:00:00-04:00",
        },
    }
    dump_md(front, f"# {title}\n\nSummary of {title}.\n", rp.sources / f"{source_card_id}.md")


def _write_intent(paths: FoundryPaths) -> None:
    dump_yaml(
        {
            "id": INTENT_ID,
            "title": "Byte-inertness guard intent",
            "type": "research",
            "status": "active",
            "governance": {"sensitivity": "personal", "requires_human_review": False},
            "output": {"audience": "technical"},
        },
        paths.intents_active / f"{INTENT_ID}.yaml",
    )


def _render_checks_text(checks) -> str:
    buf = io.StringIO()
    original = cli_commands.console
    cli_commands.console = Console(file=buf, width=100, force_terminal=False, no_color=True)
    try:
        cli_commands._render_checks(checks)
    finally:
        cli_commands.console = original
    return buf.getvalue()


def _inject_term_index(ledger: dict) -> dict:
    """Simulate this feature's effect on a pre-existing ledger: every claim
    gains a well-formed `_term_index` block, nothing else changes."""

    injected = copy.deepcopy(ledger)
    for claim in injected["claims"]:
        claim["_term_index"] = {
            "terms": ["cbc"],
            "usage_roles": {"cbc": "background"},
            "vocabulary_version": "pediatric-terms-v1",
        }
    return injected


@pytest.mark.parametrize(
    "run_id,ledger,source_cards_spec",
    [
        (
            "rf_run_20260724_byte_inertness_populated",
            POPULATED_LEDGER,
            [
                ("src_20260724_cbc_aaaaaaaa", "CBC reference"),
                ("src_20260724_ferritin_bbbbbbbb", "Ferritin reference"),
            ],
        ),
        (
            "rf_run_20260724_byte_inertness_zero_hit",
            ZERO_HIT_LEDGER,
            [("src_20260724_pipeline_cccccccc", "Pipeline reference")],
        ),
    ],
    ids=["populated", "zero-vocabulary-hit"],
)
def test_term_index_injection_is_byte_inert_for_verify(
    tmp_foundry, run_id, ledger, source_cards_spec
):
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    _write_intent(tmp_foundry)
    for source_card_id, title in source_cards_spec:
        _write_source_card(tmp_foundry, run_id, source_card_id, title)

    dump_yaml(copy.deepcopy(ledger), rp.claim_ledger)
    synthesize_report(run_id, paths=tmp_foundry)
    before = verify_report(run_id, paths=tmp_foundry)

    dump_yaml(_inject_term_index(ledger), rp.claim_ledger)
    after = verify_report(run_id, paths=tmp_foundry)

    assert len(before.checks) == 17, "guard is vacuous if the check table is empty/resized"

    # Unchanged check table: same check ids, same order.
    assert [c.id for c in before.checks] == [c.id for c in after.checks]
    # 0 status flips.
    assert [c.status for c in before.checks] == [c.status for c in after.checks]
    assert before.passed == after.passed
    assert before.exit_code == after.exit_code
    assert before.unsupported == after.unsupported
    # Byte-identical console output.
    assert _render_checks_text(before.checks) == _render_checks_text(after.checks)
