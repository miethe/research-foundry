"""Unit tests for the D13 Report Builder draft verification checks (P3 Wave D).

Covers each standalone check (pass + fail) plus the ``verify_draft``
aggregate, including the sensitivity fail-closed guarantee: a draft body
embedding a raw ``client_sensitive`` quote must refuse a ``public`` publish
(spec §11), while the same claim referenced only structurally (no raw quote
pasted into the body) passes.
"""

from __future__ import annotations

from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import builder_service as bsvc
from research_foundry.services import verification as vsvc
from research_foundry.yamlio import dump_yaml

_SENSITIVE_QUOTE = "THE CLIENT CONFIDENTIAL FIGURE IS $42 MILLION."


def _plant_run_with_sensitive_source(paths: FoundryPaths, run_id: str) -> None:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": "public",
            "created_at": "2026-06-13T09:41:00+00:00",
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_client",
            "sensitivity": "client_sensitive",
            "source": {"title": "Client Deck", "source_type": "document"},
            "trust": "high",
            "usage": "direct",
            "extracted_points": [
                {
                    "evidence_id": "ev_client",
                    "locator": "p1",
                    "summary": "client figure",
                    "quote": _SENSITIVE_QUOTE,
                }
            ],
        },
        "",
        rp.sources / "src_client.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_client",
                    "text": "The client figure is large.",
                    "materiality": "core",
                    "claim_type": "quantitative",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_client",
                            "evidence_id": "ev_client",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        rp.claim_ledger,
    )


# ---------------------------------------------------------------------------
# check_paragraph_has_support
# ---------------------------------------------------------------------------


def test_paragraph_has_support_fails_on_unlinked_material_block() -> None:
    blocks = [
        {"block_id": "blk_1", "block_type": "paragraph", "materiality": "material", "linked_claim_ids": []},
    ]
    result = vsvc.check_paragraph_has_support(blocks)
    assert result.status == "fail"
    assert "blk_1" in result.locations


def test_paragraph_has_support_passes_when_linked_or_exempt() -> None:
    blocks = [
        {"block_id": "blk_1", "block_type": "paragraph", "materiality": "material", "linked_claim_ids": ["clm_a"]},
        {"block_id": "blk_2", "block_type": "paragraph", "materiality": "narrative", "linked_claim_ids": []},
        {"block_id": "blk_3", "block_type": "heading", "materiality": "material", "linked_claim_ids": []},
    ]
    result = vsvc.check_paragraph_has_support(blocks)
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# check_claim_tags_resolve
# ---------------------------------------------------------------------------


def test_claim_tags_resolve_fails_on_unknown_tag() -> None:
    blocks = [{"block_id": "blk_1", "markdown": "Some text. [claim:clm_ghost]"}]
    result = vsvc.check_claim_tags_resolve(blocks, known_claim_ids={"clm_a"})
    assert result.status == "fail"
    assert "clm_ghost" in result.locations


def test_claim_tags_resolve_passes_when_known() -> None:
    blocks = [{"block_id": "blk_1", "markdown": "Some text. [claim:clm_a]"}]
    result = vsvc.check_claim_tags_resolve(blocks, known_claim_ids={"clm_a"})
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# check_anchor_hash_match
# ---------------------------------------------------------------------------


def test_anchor_hash_match_detects_drift(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Hash Drift Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Original text.")
    block_id = draft["blocks"][0]["block_id"]
    draft = bsvc.add_claim_link(tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_a")

    # Not yet drifted.
    result = vsvc.check_anchor_hash_match(draft["blocks"], draft["claim_links"])
    assert result.status == "pass"

    # Mutate the block's text directly (bypassing update_block on purpose —
    # simulating stale in-memory state / a hand-authored diff).
    draft["blocks"][0]["markdown"] = "Completely different text."
    result = vsvc.check_anchor_hash_match(draft["blocks"], draft["claim_links"])
    assert result.status == "fail"
    assert draft["claim_links"][0]["claim_link_id"] in result.locations


# ---------------------------------------------------------------------------
# check_report_body_sensitivity
# ---------------------------------------------------------------------------


def test_report_body_sensitivity_fails_on_raw_quote_leak(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_leak")
    blocks = [{"block_id": "blk_1", "markdown": f"The figure was huge: {_SENSITIVE_QUOTE}"}]
    source_links = [{"source_card_id": "src_client", "run_id": "rf_run_leak"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry, blocks, source_links, sensitivity_threshold="public"
    )
    assert result.status == "fail"
    assert "src_client" in result.detail


def test_report_body_sensitivity_passes_without_raw_quote(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_safe")
    blocks = [{"block_id": "blk_1", "markdown": "The client figure is large. [claim:clm_client]"}]
    source_links = [{"source_card_id": "src_client", "run_id": "rf_run_safe"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry, blocks, source_links, sensitivity_threshold="public"
    )
    assert result.status == "pass"


def test_report_body_sensitivity_fails_on_unlinked_raw_quote_leak(tmp_foundry: FoundryPaths) -> None:
    """R2 CRITICAL fix: spec §11's dangerous case is the UNLINKED one — a raw
    sensitive quote pasted into the body with NO source_link (and no
    claim_link) pointing at it. The check previously only scanned source
    cards that already had a matching source_links[] entry, so this exact
    case sailed through. Reachability now comes from source_run_id (a draft
    created ``from_run``), so the full source corpus of that run is scanned
    regardless of whether any individual card was explicitly linked."""
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_leak_unlinked")
    blocks = [{"block_id": "blk_1", "markdown": f"The figure was huge: {_SENSITIVE_QUOTE}"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry,
        blocks,
        source_links=[],
        source_run_id="rf_run_leak_unlinked",
        sensitivity_threshold="public",
    )
    assert result.status == "fail"
    assert "src_client" in result.detail


def test_report_body_sensitivity_passes_at_matching_threshold(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_matched")
    blocks = [{"block_id": "blk_1", "markdown": f"Raw quote: {_SENSITIVE_QUOTE}"}]
    source_links = [{"source_card_id": "src_client", "run_id": "rf_run_matched"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry, blocks, source_links, sensitivity_threshold="client_sensitive"
    )
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# verify_draft aggregate
# ---------------------------------------------------------------------------


def test_verify_draft_passes_clean_draft(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_verify_ok")
    draft = bsvc.create_draft_from_run(tmp_foundry, run_id="rf_run_verify_ok")

    result = vsvc.verify_draft(tmp_foundry, draft["report_draft_id"])
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert result.verification_path.exists()


def test_verify_draft_fails_closed_on_sensitive_quote_leak(tmp_foundry: FoundryPaths) -> None:
    """A report body embedding a client_sensitive quote must refuse public export."""

    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_verify_leak")
    draft = bsvc.create_draft(tmp_foundry, title="Leaky Draft", sensitivity="public")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(
        tmp_foundry, report_draft_id, markdown=f"The client figure was: {_SENSITIVE_QUOTE} [claim:clm_client]"
    )
    block_id = draft["blocks"][0]["block_id"]
    bsvc.add_claim_link(
        tmp_foundry,
        report_draft_id,
        block_id=block_id,
        claim_id="clm_client",
        source_run_id="rf_run_verify_leak",
        insert_tag=False,
    )
    bsvc.add_source_link(
        tmp_foundry,
        report_draft_id,
        source_card_id="src_client",
        run_id="rf_run_verify_leak",
        block_id=block_id,
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    sensitivity_check = next(c for c in result.checks if c.id == "report_body_sensitivity")
    assert sensitivity_check.status == "fail"
    assert result.verification_path.exists()


def test_verify_draft_fails_closed_on_unlinked_sensitive_quote(tmp_foundry: FoundryPaths) -> None:
    """R2 CRITICAL fix, aggregate level: a draft created ``from`` a run (so
    its ``source_run_id`` makes that run's sources reachable) that pastes a
    raw client_sensitive quote into a block with NO claim_link and NO
    source_link at all must still fail publish-preview — the unlinked case is
    the one with zero governance trail, and is the one spec §11 is actually
    worried about."""

    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_verify_unlinked")
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Unlinked Leak",
        sensitivity="public",
        source_run_id="rf_run_verify_unlinked",
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Some narrative text: {_SENSITIVE_QUOTE}",
        materiality="narrative",
    )
    # Deliberately no claim_link, no source_link to src_client.

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    sensitivity_check = next(c for c in result.checks if c.id == "report_body_sensitivity")
    assert sensitivity_check.status == "fail"
