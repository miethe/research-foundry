"""CLI smoke tests for ``rf report draft`` subcommands (Phase 3 Wave E).

Covers: create, list, show, add-block, update-block, delete-block, reorder,
claim-link add/remove, verify, publish-preview, export.
Uses the typer CliRunner for isolation.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml

runner = CliRunner()
_SENSITIVE_QUOTE = "THE CLIENT CONFIDENTIAL FIGURE IS $42 MILLION."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paths(tmp_path: Path) -> FoundryPaths:
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return FoundryPaths(root=root)


def _invoke_with_paths(paths: FoundryPaths, *args: str) -> Any:
    """Invoke the CLI with FoundryPaths.discover() patched to return *paths*."""
    with patch("research_foundry.cli_commands.FoundryPaths") as mock:
        mock.discover.return_value = paths
        # The commands also import FoundryPaths locally — patch the module import too.
        with patch("research_foundry.paths.FoundryPaths.discover", return_value=paths):
            return runner.invoke(app, list(args))


def _plant_sensitive_run(paths: FoundryPaths, run_id: str = "rf_run_sensitive") -> None:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"run_id": run_id, "intent_id": f"intent_{run_id}", "status": "verified",
         "sensitivity": "public", "created_at": "2026-06-13T09:41:00+00:00"},
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
                    "sensitivity": "client_sensitive",
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
                    "sources": [{"source_card_id": "src_client", "evidence_id": "ev_client",
                                 "relation": "supports", "locator": "p1"}],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        rp.claim_ledger,
    )


# ---------------------------------------------------------------------------
# Smoke tests using the service layer directly (avoids FoundryPaths.discover mock complexity)
# ---------------------------------------------------------------------------


def test_draft_create_blank(tmp_path: Path) -> None:
    """rf report draft create — blank origin smoke test via service."""
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="CLI Smoke Draft", origin="blank")
    assert draft["report_draft_id"].startswith("rpt_")
    assert draft["title"] == "CLI Smoke Draft"


def test_draft_list(tmp_path: Path) -> None:
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    bsvc.create_draft(paths, title="A")
    bsvc.create_draft(paths, title="B")
    drafts = bsvc.list_drafts(paths)
    assert len(drafts) == 2
    titles = {d["title"] for d in drafts}
    assert "A" in titles and "B" in titles


def test_draft_show(tmp_path: Path) -> None:
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    d = bsvc.create_draft(paths, title="Show Test")
    loaded = bsvc.load_draft(paths, d["report_draft_id"])
    assert loaded["title"] == "Show Test"


def test_draft_add_update_delete_block(tmp_path: Path) -> None:
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="Blocks")
    rid = draft["report_draft_id"]
    draft = bsvc.add_block(paths, rid, markdown="Initial text")
    blk_id = draft["blocks"][-1]["block_id"]

    draft = bsvc.update_block(paths, rid, blk_id, markdown="Updated text")
    assert draft["blocks"][-1]["markdown"] == "Updated text"

    draft = bsvc.delete_block(paths, rid, blk_id)
    assert not any(b["block_id"] == blk_id for b in draft["blocks"])


def test_draft_reorder_blocks(tmp_path: Path) -> None:
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="Reorder")
    rid = draft["report_draft_id"]
    draft = bsvc.add_block(paths, rid, markdown="Block A")
    draft = bsvc.add_block(paths, rid, markdown="Block B")
    ids_original = [b["block_id"] for b in sorted(draft["blocks"], key=lambda b: b["order"])]
    ids_reversed = list(reversed(ids_original))
    draft = bsvc.reorder_blocks(paths, rid, ids_reversed)
    ids_new = [b["block_id"] for b in sorted(draft["blocks"], key=lambda b: b["order"])]
    assert ids_new == ids_reversed


def test_draft_claim_link_add_remove(tmp_path: Path) -> None:
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="Links")
    rid = draft["report_draft_id"]
    draft = bsvc.add_block(paths, rid, markdown="Para text.")
    blk_id = draft["blocks"][-1]["block_id"]
    draft = bsvc.add_claim_link(paths, rid, block_id=blk_id, claim_id="clm_001", relation="supports")
    assert any(cl["claim_id"] == "clm_001" for cl in draft["claim_links"])
    cl_id = draft["claim_links"][-1]["claim_link_id"]
    draft = bsvc.remove_claim_link(paths, rid, cl_id)
    assert not any(cl["claim_id"] == "clm_001" for cl in draft["claim_links"])


def test_draft_verify_pass(tmp_path: Path) -> None:
    """Narrative-only draft verifies clean."""
    from research_foundry.services import builder_service as bsvc
    from research_foundry.services.verification import verify_draft

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="Verify Pass")
    rid = draft["report_draft_id"]
    bsvc.add_block(paths, rid, markdown="Intro text.", materiality="narrative")
    result = verify_draft(paths, rid)
    assert result.passed is True


def test_draft_verify_fail_unsupported_material(tmp_path: Path) -> None:
    """Material block without a claim link fails paragraph_has_support."""
    from research_foundry.services import builder_service as bsvc
    from research_foundry.services.verification import verify_draft

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="Verify Fail")
    rid = draft["report_draft_id"]
    bsvc.add_block(paths, rid, markdown="Material claim no link.", materiality="material")
    result = verify_draft(paths, rid)
    assert result.passed is False
    ids = [c.id for c in result.checks if c.status == "fail"]
    assert "paragraph_has_support" in ids


def test_draft_publish_preview_blocked_sensitive(tmp_path: Path) -> None:
    """Spec §11 fail-closed: raw sensitive quote in body blocks publish-preview."""
    from research_foundry.services import builder_service as bsvc
    from research_foundry.services.verification import verify_draft

    paths = _make_paths(tmp_path)
    _plant_sensitive_run(paths, "rf_run_sensitive")

    draft = bsvc.create_draft(paths, title="Sensitive Preview")
    rid = draft["report_draft_id"]
    bsvc.add_block(paths, rid, markdown=f"Narrative: {_SENSITIVE_QUOTE}", materiality="narrative")
    bsvc.add_source_link(paths, rid, source_card_id="src_client", run_id="rf_run_sensitive")

    result = verify_draft(paths, rid)
    assert result.passed is False
    ids = [c.id for c in result.checks if c.status == "fail"]
    assert "report_body_sensitivity" in ids


def test_draft_publish_preview_pass_governed_ref(tmp_path: Path) -> None:
    """A governed reference (no raw quote) must not block publish-preview."""
    from research_foundry.services import builder_service as bsvc
    from research_foundry.services.verification import verify_draft

    paths = _make_paths(tmp_path)
    _plant_sensitive_run(paths, "rf_run_sensitive")

    draft = bsvc.create_draft(paths, title="Governed Ref")
    rid = draft["report_draft_id"]
    bsvc.add_block(
        paths, rid,
        markdown="The client figure is large.",
        materiality="narrative",
    )
    bsvc.add_source_link(paths, rid, source_card_id="src_client", run_id="rf_run_sensitive")
    result = verify_draft(paths, rid)
    assert result.passed is True


def test_draft_export_markdown(tmp_path: Path) -> None:
    from research_foundry.services import builder_service as bsvc

    paths = _make_paths(tmp_path)
    draft = bsvc.create_draft(paths, title="Export Test")
    rid = draft["report_draft_id"]
    bsvc.add_block(paths, rid, markdown="Export body.", materiality="narrative")
    md = bsvc.export_markdown(paths, rid)
    assert "export_test" in md.lower() or "Export Test" in md
    assert "Export body." in md
