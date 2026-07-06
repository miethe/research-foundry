"""Unit tests for the Report Builder API router (Phase 3 Wave E).

Covers:
  - POST /api/reports (create blank, from-run, from-collection)
  - GET  /api/reports (list)
  - GET  /api/reports/{report_id} (detail; rpt_ guard; 404 for run ids)
  - DELETE /api/reports/{report_id}
  - POST /api/reports/{report_id}/versions + GET list + GET by id + POST restore
  - POST /api/reports/{report_id}/blocks
  - PATCH /api/reports/{report_id}/blocks/reorder (fixed route doesn't collide)
  - PATCH /api/reports/{report_id}/blocks/{block_id}
  - DELETE /api/reports/{report_id}/blocks/{block_id}
  - POST /api/reports/{report_id}/claim-links  +  DELETE
  - POST /api/reports/{report_id}/source-links +  DELETE
  - POST /api/reports/{report_id}/verify   (D13 structured result)
  - POST /api/reports/{report_id}/publish-preview — fail-closed on sensitive raw quote
  - GET  /api/reports/{report_id}/export
  - CRITICAL: GET /api/reports/{run_id}/anchors (runs.py) still resolves
    after reports router is added — no routing collision.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, RunPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SENSITIVE_QUOTE = "THE CLIENT CONFIDENTIAL FIGURE IS $42 MILLION."


def _make_config(tmp_path: Path, *, sensitivity_threshold: str | None = None) -> FoundryConfig:
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

    foundry_yaml_path = root / "foundry.yaml"
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict[str, Any] = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    if sensitivity_threshold is not None:
        viewer["sensitivity_threshold"] = sensitivity_threshold
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    return FoundryConfig(paths=FoundryPaths(root=root))


def _make_client(tmp_path: Path) -> tuple[TestClient, FoundryConfig]:
    cfg = _make_config(tmp_path)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    return TestClient(app, raise_server_exceptions=True), cfg


def _plant_run_with_report(paths: FoundryPaths, run_id: str = "rf_run_e001") -> RunPaths:
    """Plant a minimal run with a report draft + claim ledger for seeding tests."""
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
            "source_card_id": "src_e001",
            "sensitivity": "public",
            "source": {
                "title": "Alpha",
                "source_type": "web",
                "locator": {"url": "https://example.test/alpha"},
            },
            "trust": "high",
            "usage": "direct",
            "extracted_points": [],
        },
        "",
        rp.sources / "src_e001.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_e001",
                    "text": "Alpha supports this.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {"source_card_id": "src_e001", "relation": "supports"}
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        rp.claim_ledger,
    )
    report_md = (
        "---\n"
        "type: research_report\n"
        f"report_id: {run_id}\n"
        "sensitivity: public\n"
        "---\n\n"
        "## Alpha Result\n\n"
        "Alpha supports this. [claim:clm_e001]\n"
    )
    rp.report_draft.write_text(report_md, encoding="utf-8")
    return rp


def _plant_run_with_sensitive_source(paths: FoundryPaths, run_id: str = "rf_run_sensitive") -> RunPaths:
    """Plant a run with a client_sensitive source card containing a raw quote."""
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
    return rp


# ---------------------------------------------------------------------------
# POST /api/reports — create
# ---------------------------------------------------------------------------


def test_create_blank_draft(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/reports", json={"origin": "blank", "title": "Test Draft"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["report_draft_id"].startswith("rpt_")
    assert data["title"] == "Test Draft"
    assert data["origin"] == "blank"
    assert data["status"] == "draft"
    assert isinstance(data["blocks"], list)


def test_create_template_draft(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/reports", json={"origin": "template", "title": "Template Draft", "audience": "technical"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["audience"] == "technical"


def test_create_draft_from_run(tmp_path: Path) -> None:
    client, cfg = _make_client(tmp_path)
    _plant_run_with_report(cfg.paths, "rf_run_e001")
    resp = client.post("/api/reports", json={"origin": "run", "source_run_id": "rf_run_e001"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["origin"] == "run"
    assert data["source_run_id"] == "rf_run_e001"


def test_create_draft_from_run_missing_run_id(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/reports", json={"origin": "run"})
    assert resp.status_code == 422


def test_create_draft_from_collection(tmp_path: Path) -> None:
    client, cfg = _make_client(tmp_path)
    # collection with empty list returns a draft with no blocks (best-effort)
    resp = client.post("/api/reports", json={
        "origin": "collection", "title": "Coll Draft", "catalog_item_ids": ["cat_missing_001"]
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["origin"] == "collection"


def test_create_draft_from_collection_missing_ids(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/reports", json={"origin": "collection", "title": "X"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/reports — list
# ---------------------------------------------------------------------------


def test_list_drafts_empty(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_drafts_returns_summaries(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    client.post("/api/reports", json={"origin": "blank", "title": "A"})
    client.post("/api/reports", json={"origin": "blank", "title": "B"})
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    titles = {d["title"] for d in items}
    assert "A" in titles and "B" in titles


# ---------------------------------------------------------------------------
# GET /api/reports/{report_id} — detail
# ---------------------------------------------------------------------------


def test_get_draft_detail(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Detail Test"}).json()
    rid = created["report_draft_id"]
    resp = client.get(f"/api/reports/{rid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_draft_id"] == rid


def test_get_draft_unknown_id_returns_404(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/reports/rpt_doesnotexist")
    assert resp.status_code == 404


def test_get_draft_run_id_returns_404_no_leak(tmp_path: Path) -> None:
    """A run id passed to the draft detail endpoint must return 404 (no-existence-leak)."""
    client, cfg = _make_client(tmp_path)
    _plant_run_with_report(cfg.paths, "rf_run_e001")
    resp = client.get("/api/reports/rf_run_e001")
    # The rpt_ guard fires first — run ids do not start with rpt_
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CRITICAL: GET /api/reports/{run_id}/anchors still resolves after reports router
# ---------------------------------------------------------------------------


def test_anchors_route_still_resolves(tmp_path: Path) -> None:
    """Regression: GET /api/reports/{run_id}/anchors must not be swallowed by
    the new /api/reports/{report_id} route from the reports router."""
    client, cfg = _make_client(tmp_path)
    _plant_run_with_report(cfg.paths, "rf_run_e001")

    # Should return 200 with report_anchors key (or null anchors — run exists)
    resp = client.get("/api/reports/rf_run_e001/anchors")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "run_id" in data
    assert "report_anchors" in data


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}
# ---------------------------------------------------------------------------


def test_delete_draft(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Delete Me"}).json()
    rid = created["report_draft_id"]
    resp = client.delete(f"/api/reports/{rid}")
    assert resp.status_code == 204
    # Subsequent GET returns 404
    resp2 = client.get(f"/api/reports/{rid}")
    assert resp2.status_code == 404


def test_delete_draft_idempotent(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    resp = client.delete("/api/reports/rpt_nonexistent")
    assert resp.status_code == 204  # idempotent


# ---------------------------------------------------------------------------
# Versions (revisions)
# ---------------------------------------------------------------------------


def test_create_and_list_versions(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Versioned"}).json()
    rid = created["report_draft_id"]

    v_resp = client.post(f"/api/reports/{rid}/versions", json={"note": "v1 snap"})
    assert v_resp.status_code == 201
    pointer = v_resp.json()
    assert "report_version_id" in pointer

    list_resp = client.get(f"/api/reports/{rid}/versions")
    assert list_resp.status_code == 200
    versions = list_resp.json()
    assert len(versions) == 1
    assert versions[0]["note"] == "v1 snap"


def test_get_revision_and_restore(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Restore Test"}).json()
    rid = created["report_draft_id"]
    # Add a block, snap, modify, restore
    client.post(f"/api/reports/{rid}/blocks", json={"block_type": "paragraph", "markdown": "Before snap"})
    v_resp = client.post(f"/api/reports/{rid}/versions", json={"note": "snap1"})
    vid = v_resp.json()["report_version_id"]

    # Modify the draft
    draft_after = client.get(f"/api/reports/{rid}").json()
    blk_id = draft_after["blocks"][0]["block_id"]
    client.patch(f"/api/reports/{rid}/blocks/{blk_id}", json={"markdown": "After edit"})

    # Restore
    restore_resp = client.post(f"/api/reports/{rid}/versions/{vid}/restore")
    assert restore_resp.status_code == 200
    restored = restore_resp.json()
    assert restored["blocks"][0]["markdown"] == "Before snap"


# ---------------------------------------------------------------------------
# Blocks CRUD
# ---------------------------------------------------------------------------


def test_add_block(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Blocks Test"}).json()
    rid = created["report_draft_id"]

    resp = client.post(f"/api/reports/{rid}/blocks", json={"block_type": "paragraph", "markdown": "Hello world."})
    assert resp.status_code == 201
    data = resp.json()
    blk = data["blocks"][-1]
    assert blk["block_type"] == "paragraph"
    assert blk["markdown"] == "Hello world."


def test_update_block(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Update Block"}).json()
    rid = created["report_draft_id"]
    after_add = client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Original"}).json()
    blk_id = after_add["blocks"][-1]["block_id"]

    resp = client.patch(f"/api/reports/{rid}/blocks/{blk_id}", json={"markdown": "Updated"})
    assert resp.status_code == 200
    updated = resp.json()
    blk = next(b for b in updated["blocks"] if b["block_id"] == blk_id)
    assert blk["markdown"] == "Updated"


def test_delete_block(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Del Block"}).json()
    rid = created["report_draft_id"]
    after_add = client.post(f"/api/reports/{rid}/blocks", json={"markdown": "To delete"}).json()
    blk_id = after_add["blocks"][-1]["block_id"]

    del_resp = client.delete(f"/api/reports/{rid}/blocks/{blk_id}")
    assert del_resp.status_code == 200
    del_draft = del_resp.json()
    assert del_draft["report_draft_id"] == rid
    assert blk_id not in [b["block_id"] for b in del_draft["blocks"]]

    detail = client.get(f"/api/reports/{rid}").json()
    block_ids = [b["block_id"] for b in detail["blocks"]]
    assert blk_id not in block_ids


def test_reorder_blocks(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Reorder"}).json()
    rid = created["report_draft_id"]
    client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Block A"})
    after_b = client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Block B"}).json()
    block_ids = [b["block_id"] for b in after_b["blocks"]]
    reversed_ids = list(reversed(block_ids))

    resp = client.patch(f"/api/reports/{rid}/blocks/reorder", json={"block_ids": reversed_ids})
    assert resp.status_code == 200
    reordered = resp.json()
    new_order = [b["block_id"] for b in sorted(reordered["blocks"], key=lambda b: b["order"])]
    assert new_order == reversed_ids


def test_reorder_route_does_not_eat_block_id_route(tmp_path: Path) -> None:
    """PATCH /blocks/reorder (fixed) and PATCH /blocks/{block_id} (param) must both work."""
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Route Check"}).json()
    rid = created["report_draft_id"]
    after = client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Z"}).json()
    blk_id = after["blocks"][-1]["block_id"]

    # Parameterized PATCH on a real block_id
    patch_resp = client.patch(f"/api/reports/{rid}/blocks/{blk_id}", json={"markdown": "Z updated"})
    assert patch_resp.status_code == 200
    # Fixed PATCH on /reorder
    reorder_resp = client.patch(f"/api/reports/{rid}/blocks/reorder", json={"block_ids": [blk_id]})
    assert reorder_resp.status_code == 200


# ---------------------------------------------------------------------------
# Claim links
# ---------------------------------------------------------------------------


def test_add_and_remove_claim_link(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Claims"}).json()
    rid = created["report_draft_id"]
    after = client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Evidence here."}).json()
    blk_id = after["blocks"][-1]["block_id"]

    add_resp = client.post(f"/api/reports/{rid}/claim-links", json={
        "block_id": blk_id, "claim_id": "clm_001", "relation": "supports"
    })
    assert add_resp.status_code == 201
    draft = add_resp.json()
    assert any(cl["claim_id"] == "clm_001" for cl in draft["claim_links"])

    cl_id = next(cl["claim_link_id"] for cl in draft["claim_links"] if cl["claim_id"] == "clm_001")
    del_resp = client.delete(f"/api/reports/{rid}/claim-links/{cl_id}")
    assert del_resp.status_code == 200
    del_draft = del_resp.json()
    assert not any(cl["claim_id"] == "clm_001" for cl in del_draft["claim_links"])

    after_del = client.get(f"/api/reports/{rid}").json()
    assert not any(cl["claim_id"] == "clm_001" for cl in after_del["claim_links"])


# ---------------------------------------------------------------------------
# Source links
# ---------------------------------------------------------------------------


def test_add_and_remove_source_link(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Sources"}).json()
    rid = created["report_draft_id"]
    after = client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Sourced para."}).json()
    blk_id = after["blocks"][-1]["block_id"]

    add_resp = client.post(f"/api/reports/{rid}/source-links", json={
        "source_card_id": "src_001", "block_id": blk_id, "run_id": "rf_run_x"
    })
    assert add_resp.status_code == 201
    draft = add_resp.json()
    assert any(sl["source_card_id"] == "src_001" for sl in draft["source_links"])

    sl_id = next(sl["source_link_id"] for sl in draft["source_links"])
    del_resp = client.delete(f"/api/reports/{rid}/source-links/{sl_id}")
    assert del_resp.status_code == 200
    del_draft = del_resp.json()
    assert not any(sl["source_link_id"] == sl_id for sl in del_draft["source_links"])


# ---------------------------------------------------------------------------
# Verify endpoint
# ---------------------------------------------------------------------------


def test_verify_endpoint_pass(tmp_path: Path) -> None:
    """A draft with only narrative blocks should pass verification (no material claim gate)."""
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Verify Pass"}).json()
    rid = created["report_draft_id"]
    # Add narrative block — exempt from paragraph_has_support
    client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Intro text.", "materiality": "narrative"})

    resp = client.post(f"/api/reports/{rid}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "passed" in data
    assert isinstance(data["checks"], list)


def test_verify_endpoint_fail_unsupported_material_block(tmp_path: Path) -> None:
    """A material block with no claim links must show paragraph_has_support fail."""
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Verify Fail"}).json()
    rid = created["report_draft_id"]
    client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Material but no link.", "materiality": "material"})

    resp = client.post(f"/api/reports/{rid}/verify")
    assert resp.status_code == 200  # always 200 (structured result)
    data = resp.json()
    assert data["passed"] is False
    check_ids = [c["id"] for c in data["checks"] if c["status"] == "fail"]
    assert "paragraph_has_support" in check_ids


# ---------------------------------------------------------------------------
# Publish-preview — fail-closed (spec §11)
# ---------------------------------------------------------------------------


def test_publish_preview_pass_narrative_only(tmp_path: Path) -> None:
    """A draft with only narrative blocks and no sensitive source links passes."""
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Preview Pass"}).json()
    rid = created["report_draft_id"]
    client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Narrative para.", "materiality": "narrative"})

    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "preview_markdown" in data
    assert isinstance(data["checks"], list)


def test_publish_preview_blocked_by_material_unsupported(tmp_path: Path) -> None:
    """A material block without a claim link must block publish-preview (422)."""
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Preview Block"}).json()
    rid = created["report_draft_id"]
    client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Material no support.", "materiality": "material"})

    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["ok"] is False
    assert any(c["id"] == "paragraph_has_support" for c in detail["blocking"])


def test_publish_preview_blocked_by_sensitive_raw_quote(tmp_path: Path) -> None:
    """Spec §11: publish-preview MUST fail-closed when a draft body embeds a raw
    sensitive quote, even if the block is narrative (sensitivity check is independent
    of support check)."""
    client, cfg = _make_client(tmp_path)
    _plant_run_with_sensitive_source(cfg.paths, "rf_run_sensitive")

    # Create a draft and attach a source link to the sensitive source
    created = client.post("/api/reports", json={"origin": "blank", "title": "Sensitive Preview"}).json()
    rid = created["report_draft_id"]

    # Add a block that contains the raw sensitive quote
    client.post(f"/api/reports/{rid}/blocks", json={
        "markdown": f"Narrative: {_SENSITIVE_QUOTE}",
        "materiality": "narrative",
    })
    # Link the source so the sensitivity check can inspect it
    client.post(f"/api/reports/{rid}/source-links", json={
        "source_card_id": "src_client",
        "run_id": "rf_run_sensitive",
    })

    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 422, "sensitivity fail-closed gate must block"
    detail = resp.json()["detail"]
    assert detail["ok"] is False
    blocking_ids = [c["id"] for c in detail["blocking"]]
    assert "report_body_sensitivity" in blocking_ids


def test_publish_preview_passes_when_sensitive_source_not_in_body(tmp_path: Path) -> None:
    """A governed reference (claim link, no raw quote) should NOT block publish-preview."""
    client, cfg = _make_client(tmp_path)
    _plant_run_with_sensitive_source(cfg.paths, "rf_run_sensitive")

    created = client.post("/api/reports", json={"origin": "blank", "title": "Governed Ref"}).json()
    rid = created["report_draft_id"]
    # Add narrative block WITHOUT pasting the raw quote
    client.post(f"/api/reports/{rid}/blocks", json={
        "markdown": "The client figure is large.",
        "materiality": "narrative",
    })
    # Attach source link (governed path — no raw quote in body)
    client.post(f"/api/reports/{rid}/source-links", json={
        "source_card_id": "src_client",
        "run_id": "rf_run_sensitive",
    })

    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_draft(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    created = client.post("/api/reports", json={"origin": "blank", "title": "Export Test"}).json()
    rid = created["report_draft_id"]
    client.post(f"/api/reports/{rid}/blocks", json={"markdown": "Export body.", "materiality": "narrative"})

    resp = client.get(f"/api/reports/{rid}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_draft_id"] == rid
    assert "markdown" in data
    assert "Export body." in data["markdown"]


# ---------------------------------------------------------------------------
# 404 guard: non-rpt_ ids are not served by the draft endpoints
# ---------------------------------------------------------------------------


def test_draft_endpoints_reject_non_rpt_ids(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    for method, path in [
        ("get", "/api/reports/rf_run_abc123"),
        ("delete", "/api/reports/rf_run_abc123"),
        ("get", "/api/reports/rf_run_abc123/versions"),
    ]:
        resp = getattr(client, method)(path)
        assert resp.status_code == 404, f"{method.upper()} {path} expected 404, got {resp.status_code}"


# ---------------------------------------------------------------------------
# R2 fix: sensitivity gating on draft read endpoints (fail-closed)
# ---------------------------------------------------------------------------


def test_get_draft_sensitivity_gate_hides_over_threshold_draft(tmp_path: Path) -> None:
    """A draft's own sensitivity must gate GET /reports/{id} exactly like
    catalog_service.get_item gates a catalog item — an over-threshold draft
    is an indistinguishable 404, not merely present-but-redacted."""
    client, _ = _make_client(tmp_path)
    created = client.post(
        "/api/reports",
        json={"origin": "blank", "title": "Sensitive Draft", "sensitivity": "client_sensitive"},
    ).json()
    rid = created["report_draft_id"]

    # Default threshold is "public" (foundry.yaml) -> over-threshold draft is hidden.
    resp = client.get(f"/api/reports/{rid}")
    assert resp.status_code == 404

    # An explicit override matching the draft's own sensitivity reveals it.
    resp2 = client.get(f"/api/reports/{rid}", params={"sensitivity_threshold": "client_sensitive"})
    assert resp2.status_code == 200
    assert resp2.json()["report_draft_id"] == rid


def test_list_drafts_sensitivity_gate_filters_over_threshold(tmp_path: Path) -> None:
    """GET /reports must omit over-threshold drafts entirely (fail-closed),
    at the default 'public' threshold."""
    client, _ = _make_client(tmp_path)
    client.post("/api/reports", json={"origin": "blank", "title": "Public One"})
    client.post(
        "/api/reports",
        json={"origin": "blank", "title": "Sensitive One", "sensitivity": "client_sensitive"},
    )

    resp = client.get("/api/reports")
    assert resp.status_code == 200
    titles = {d["title"] for d in resp.json()}
    assert titles == {"Public One"}

    resp2 = client.get("/api/reports", params={"sensitivity_threshold": "client_sensitive"})
    assert resp2.status_code == 200
    titles2 = {d["title"] for d in resp2.json()}
    assert titles2 == {"Public One", "Sensitive One"}
