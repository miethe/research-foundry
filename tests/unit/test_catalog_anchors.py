"""Wave B: API + CLI + catalog surfacing for report_anchors (P2 Wave B).

Covers:
  - GET /api/reports/{run_id}/anchors  endpoint — 200 shape, 404 for unknown
    run (no-existence-leak), 404 for over-threshold run, sensitivity_threshold
    query param, null anchors when no report draft.
  - Catalog _build_links sourced from report_anchors: "contains" links derived
    from anchor blocks, missing_claim entries skipped, dedup across blocks,
    null anchors produce no contains links (graceful degradation).
  - Run detail (GET /api/runs/{run_id}) passes through report_anchors field
    under the same key as run.json.
  - rf report anchors CLI command smoke test.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import catalog_service as svc
from research_foundry.services.export_service import derive_report_anchors, export_run
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_config(
    tmp_path: Path,
    *,
    sensitivity_threshold: str | None = None,
) -> FoundryConfig:
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
    viewer = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    if sensitivity_threshold is not None:
        viewer["sensitivity_threshold"] = sensitivity_threshold
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    paths = FoundryPaths(root=root)
    return FoundryConfig(paths=paths)


def _make_client(
    tmp_path: Path, *, sensitivity_threshold: str | None = None
) -> tuple[TestClient, FoundryConfig]:
    cfg = _make_config(tmp_path, sensitivity_threshold=sensitivity_threshold)
    app = create_app(cfg)
    from research_foundry.api.routers.runs import get_paths
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    return TestClient(app, raise_server_exceptions=True), cfg


def _plant_run(
    paths: FoundryPaths,
    run_id: str,
    *,
    sensitivity: str = "public",
    with_report: bool = True,
) -> None:
    """Plant a minimal run with a report draft containing [claim:clm_001] and [claim:clm_inf]."""
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": sensitivity,
            "created_at": "2026-06-13T09:41:00+00:00",
        },
        rp.run_yaml,
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "Alpha is supported.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                },
                {
                    "claim_id": "clm_inf",
                    "text": "Therefore beta.",
                    "materiality": "core",
                    "claim_type": "inference",
                    "status": "inference",
                    "confidence": "medium",
                    "sources": [],
                    "inference_basis": {
                        "from_claims": ["clm_001"],
                        "reasoning_summary": "Derived from alpha.",
                    },
                    "report_locations": [],
                },
            ],
        },
        rp.claim_ledger,
    )
    if with_report:
        rp.report_draft.write_text(
            "# Report Title\n\n"
            "Alpha supports the thesis. [claim:clm_001]\n\n"
            "## Inference\n\n"
            "Therefore beta holds. [claim:clm_inf]\n",
            encoding="utf-8",
        )
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 2},
            "governance": {"sensitivity": sensitivity, "approved_for_writeback": False},
        },
        rp.evidence_bundle,
    )


# ---------------------------------------------------------------------------
# Catalog _build_links: sourced from report_anchors
# ---------------------------------------------------------------------------


def test_catalog_build_links_uses_report_anchors_for_contains(tmp_foundry: FoundryPaths) -> None:
    """_build_links derives report→claim 'contains' links from report_anchors.

    clm_001 and clm_inf appear in the report draft as [claim:] tags →
    derive_report_anchors picks them up → import_run stores "contains" links.
    Neither claim has report_locations in the ledger (confirming the source
    is anchors, not report_locations).
    """
    _plant_run(tmp_foundry, "rf_anc_001")
    svc.import_run(tmp_foundry, "rf_anc_001")

    # Set threshold permissive to see all items.
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {}).setdefault("viewer", {})
    data["foundry"]["viewer"]["sensitivity_threshold"] = "client_sensitive"
    dump_yaml(data, tmp_foundry.foundry_yaml)

    report_id = svc._make_item_id("report", "rf_anc_001", "report")
    item = svc.get_item(tmp_foundry, report_id)
    assert item is not None, "report catalog item must be visible"

    outgoing = {(l["catalog_item_id"], l["relation"]) for l in item["links"]["outgoing"]}
    clm_001_id = svc._make_item_id("claim", "rf_anc_001", "clm_001")
    clm_inf_id = svc._make_item_id("inference", "rf_anc_001", "clm_inf")
    assert (clm_001_id, "contains") in outgoing, "clm_001 must be linked via anchors"
    assert (clm_inf_id, "contains") in outgoing, "clm_inf must be linked via anchors"


def test_catalog_build_links_skips_missing_claim_entries(tmp_foundry: FoundryPaths) -> None:
    """Anchor blocks with link_status='missing_claim' must NOT produce catalog links."""
    _plant_run(tmp_foundry, "rf_anc_002")
    # Add a report draft with a dangling [claim:clm_missing] tag.
    rp = tmp_foundry.run_paths("rf_anc_002")
    rp.report_draft.write_text(
        "# Title\n\n"
        "Alpha holds. [claim:clm_001]\n\n"
        "Unknown claim tag. [claim:clm_missing]\n",
        encoding="utf-8",
    )
    svc.import_run(tmp_foundry, "rf_anc_002")

    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {}).setdefault("viewer", {})
    data["foundry"]["viewer"]["sensitivity_threshold"] = "client_sensitive"
    dump_yaml(data, tmp_foundry.foundry_yaml)

    report_id = svc._make_item_id("report", "rf_anc_002", "report")
    item = svc.get_item(tmp_foundry, report_id)
    assert item is not None

    outgoing_ids = {l["catalog_item_id"] for l in item["links"]["outgoing"]}
    # clm_missing not in the ledger → link_status="missing_claim" → must be skipped.
    missing_id = svc._make_item_id("claim", "rf_anc_002", "clm_missing")
    assert missing_id not in outgoing_ids


def test_catalog_build_links_no_contains_when_no_report_anchors(tmp_foundry: FoundryPaths) -> None:
    """Pre-1.4 exports (report_anchors absent) produce no 'contains' links.

    Simulates a run without report_draft — report_anchors will be None —
    so no report catalog item exists (nothing to link from).  Assert that
    no 'contains' links appear in the DB.
    """
    _plant_run(tmp_foundry, "rf_anc_003", with_report=False)
    svc.import_run(tmp_foundry, "rf_anc_003")

    with svc._db(tmp_foundry) as conn:
        rows = conn.execute(
            "SELECT * FROM catalog_links WHERE run_id = ? AND relation = 'contains'",
            ("rf_anc_003",),
        ).fetchall()
    assert rows == [], "no 'contains' links expected when no report draft/anchors"


# ---------------------------------------------------------------------------
# Run detail: report_anchors passthrough
# ---------------------------------------------------------------------------


def test_run_detail_passes_through_report_anchors(tmp_path: Path) -> None:
    """GET /api/runs/{run_id} includes report_anchors under the same key as run.json."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_detail")

    resp = client.get("/api/runs/rf_anc_detail")
    assert resp.status_code == 200
    body = resp.json()
    assert "report_anchors" in body, "report_anchors must be in run detail response"
    anchors = body["report_anchors"]
    assert isinstance(anchors, list), "report_anchors must be a list when report_draft exists"
    assert len(anchors) > 0, "at least one anchor block expected"
    # Verify each block has the expected D8 fields.
    block = anchors[0]
    assert set(block.keys()) >= {"block_id", "section_id", "paragraph_ordinal", "text_hash", "claim_links"}


def test_run_detail_report_anchors_null_when_no_report(tmp_path: Path) -> None:
    """report_anchors is null in run detail when there is no report_draft."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_nodrft", with_report=False)

    resp = client.get("/api/runs/rf_anc_nodrft")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_anchors"] is None


def test_run_detail_report_anchors_consistent_with_export_run(tmp_path: Path) -> None:
    """The run detail API returns the same report_anchors as export_run() directly."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_parity")

    resp = client.get("/api/runs/rf_anc_parity")
    assert resp.status_code == 200
    api_anchors = resp.json()["report_anchors"]

    direct = export_run(cfg.paths, "rf_anc_parity")
    assert api_anchors == direct["report_anchors"]


# ---------------------------------------------------------------------------
# GET /api/reports/{run_id}/anchors — 200 shape
# ---------------------------------------------------------------------------


def test_anchors_endpoint_200_shape(tmp_path: Path) -> None:
    """GET /api/reports/{run_id}/anchors returns run_id + report_anchors list."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_ep200")

    resp = client.get("/api/reports/rf_anc_ep200/anchors")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["run_id"] == "rf_anc_ep200"
    assert isinstance(body["report_anchors"], list)
    assert len(body["report_anchors"]) > 0
    # Spot-check first block shape.
    block = body["report_anchors"][0]
    assert "block_id" in block
    assert "section_id" in block
    assert "paragraph_ordinal" in block
    assert "text_hash" in block
    assert "claim_links" in block


def test_anchors_endpoint_null_when_no_report(tmp_path: Path) -> None:
    """report_anchors is null when the run has no report_draft."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_epnull", with_report=False)

    resp = client.get("/api/reports/rf_anc_epnull/anchors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_anchors"] is None


# ---------------------------------------------------------------------------
# GET /api/reports/{run_id}/anchors — 404 no-existence-leak
# ---------------------------------------------------------------------------


def test_anchors_endpoint_404_unknown_run(tmp_path: Path) -> None:
    """Unknown run_id returns 404 (not 500 or 422)."""
    client, _ = _make_client(tmp_path, sensitivity_threshold="public")
    resp = client.get("/api/reports/rf_does_not_exist/anchors")
    assert resp.status_code == 404


def test_anchors_endpoint_404_over_threshold_run_is_indistinguishable(tmp_path: Path) -> None:
    """An over-threshold run returns 404 — indistinguishable from an unknown run.

    This enforces the no-existence-leak invariant (landmine #4): callers cannot
    distinguish "this run does not exist" from "this run exists but is hidden".
    """
    # Plant a public run (visible) and a client_sensitive run (hidden).
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_visible", sensitivity="public")
    _plant_run(cfg.paths, "rf_anc_hidden", sensitivity="client_sensitive")

    visible_resp = client.get("/api/reports/rf_anc_visible/anchors")
    hidden_resp = client.get("/api/reports/rf_anc_hidden/anchors")
    unknown_resp = client.get("/api/reports/rf_anc_totally_unknown/anchors")

    # Visible → 200
    assert visible_resp.status_code == 200

    # Hidden and unknown → both 404 with the SAME detail string (no-leak).
    assert hidden_resp.status_code == 404
    assert unknown_resp.status_code == 404
    assert hidden_resp.json()["detail"] == unknown_resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/reports/{run_id}/anchors — sensitivity_threshold param
# ---------------------------------------------------------------------------


def test_anchors_endpoint_threshold_param_reveals_run(tmp_path: Path) -> None:
    """?sensitivity_threshold=client_sensitive reveals a previously-hidden run."""
    # Default threshold in config is "public"; run is "personal" → hidden by default.
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_personal", sensitivity="personal")

    # At default public threshold: 404.
    assert client.get("/api/reports/rf_anc_personal/anchors").status_code == 404

    # At explicit personal (or higher) threshold: 200.
    resp = client.get("/api/reports/rf_anc_personal/anchors?sensitivity_threshold=personal")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "rf_anc_personal"


def test_anchors_endpoint_invalid_threshold_returns_400(tmp_path: Path) -> None:
    """An unrecognized sensitivity_threshold value returns 400."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_anc_badth")
    resp = client.get("/api/reports/rf_anc_badth/anchors?sensitivity_threshold=bogus_level")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CLI: rf report anchors
# ---------------------------------------------------------------------------


def test_cli_report_anchors_json(tmp_foundry: FoundryPaths) -> None:
    """rf report anchors --json outputs a valid JSON object with run_id + report_anchors."""
    from unittest.mock import patch
    from typer.testing import CliRunner
    from research_foundry.cli import app as cli_app

    _plant_run(tmp_foundry, "rf_anc_cli")

    runner = CliRunner()
    with patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry):
        result = runner.invoke(cli_app, ["report", "anchors", "rf_anc_cli", "--json"])
    assert result.exit_code == 0, f"CLI exited {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert data["run_id"] == "rf_anc_cli"
    assert isinstance(data["report_anchors"], list)


def test_cli_report_anchors_unknown_run_exits_nonzero(tmp_foundry: FoundryPaths) -> None:
    """rf report anchors on an unknown run_id exits with a non-zero code."""
    from unittest.mock import patch
    from typer.testing import CliRunner
    from research_foundry.cli import app as cli_app

    runner = CliRunner()
    with patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry):
        result = runner.invoke(cli_app, ["report", "anchors", "rf_run_does_not_exist", "--json"])
    assert result.exit_code != 0


def test_cli_report_anchors_over_threshold_exits_nonzero(tmp_foundry: FoundryPaths) -> None:
    """rf report anchors with threshold=public on a client_sensitive run exits non-zero."""
    from unittest.mock import patch
    from typer.testing import CliRunner
    from research_foundry.cli import app as cli_app

    _plant_run(tmp_foundry, "rf_anc_cli_hidden", sensitivity="client_sensitive")

    runner = CliRunner()
    with patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry):
        result = runner.invoke(
            cli_app,
            ["report", "anchors", "rf_anc_cli_hidden", "--json",
             "--sensitivity-threshold", "public"],
        )
    assert result.exit_code != 0
