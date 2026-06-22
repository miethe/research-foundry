"""Tests for the RF loopback API endpoints (TEST-001..006).

Coverage:
  TEST-001  GET /api/runs  — list shape; empty corpus → []; RFRunSummary fields.
  TEST-002  GET /api/runs/{run_id}  — known→200+shape; unknown→404 with {"detail":...}.
  TEST-003  GET /api/runs/{run_id}/claims and /sources/{id}.
  TEST-004  GET /data/governance.json  — GovernanceConfig shape; no 500 on minimal config.
  TEST-005  GET /health  — 200 under both auth_mode=none and auth_mode=token.
  TEST-006  Sensitivity-gate parity (MOST CRITICAL): API response == export_service.export_run()
            for a work_sensitive claim with threshold=public; also confirms quote/summary
            are replaced with the REDACTION_MARKER so the gate is never bypassed.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.export_service import REDACTION_MARKER, export_run
from research_foundry.yamlio import dump_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    tmp_path: Path,
    *,
    auth_mode: str = "none",
    sensitivity_threshold: str | None = None,
    allowlist: list[str] | None = None,
) -> FoundryConfig:
    """Build a minimal FoundryConfig pointing at a temp workspace.

    Writes the viewer settings into foundry.yaml on disk so that
    ``resolve_threshold`` (which creates a fresh FoundryConfig from paths)
    picks up the right values without monkeypatching module state.
    """
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)

    from research_foundry.paths import distribution_root
    from research_foundry.yamlio import dump_yaml, load_yaml

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

    for d in (
        "runs",
        "inbox/raw_ideas",
        "intents/active",
    ):
        (root / d).mkdir(parents=True, exist_ok=True)

    # Build and write the viewer block into the on-disk foundry.yaml so that
    # resolve_threshold() (which reads config from disk at request time) also
    # sees the correct sensitivity threshold.
    foundry_yaml_path = root / "foundry.yaml"
    existing: dict[str, Any] = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict[str, Any] = {}
    viewer["auth_mode"] = auth_mode
    if sensitivity_threshold is not None:
        viewer["sensitivity_threshold"] = sensitivity_threshold
    if allowlist is not None:
        viewer["allowlist"] = allowlist
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    paths = FoundryPaths(root=root)
    cfg = FoundryConfig(paths=paths)
    return cfg


def _make_client(
    tmp_path: Path,
    *,
    auth_mode: str = "none",
    sensitivity_threshold: str | None = None,
    allowlist: list[str] | None = None,
) -> tuple[TestClient, FoundryConfig]:
    cfg = _make_config(
        tmp_path,
        auth_mode=auth_mode,
        sensitivity_threshold=sensitivity_threshold,
        allowlist=allowlist,
    )
    app = create_app(cfg)
    # Override the get_paths dependency so endpoints read from our isolated
    # tmp workspace rather than discovering the real foundry.yaml.
    from research_foundry.api.routers.runs import get_paths
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    return TestClient(app, raise_server_exceptions=True), cfg


def _plant_run(
    paths: FoundryPaths,
    run_id: str,
    *,
    sensitivity: str = "personal",
) -> None:
    """Write a minimal run scaffold so export_service can discover it."""
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "planned",
            "sensitivity": sensitivity,
            "created_at": "2026-06-13T09:41:00+00:00",
        },
        rp.run_yaml,
    )


def _plant_source_card(
    paths: FoundryPaths,
    run_id: str,
    source_card_id: str,
    *,
    sensitivity: str = "personal",
    quote: str = "some evidence quote",
    summary: str = "some evidence summary",
) -> None:
    """Write a minimal source_card.md with one extracted point."""
    rp = paths.run_paths(run_id)
    rp.sources.mkdir(parents=True, exist_ok=True)
    dump_md(
        {
            "type": "source_card",
            "source_card_id": source_card_id,
            "sensitivity": sensitivity,
            "trust": "high",
            "usage": "direct",
            "source": {"title": f"Source {source_card_id}", "source_type": "web"},
            "extracted_points": [
                {
                    "evidence_id": "ev_001",
                    "sensitivity": sensitivity,
                    "quote": quote,
                    "summary": summary,
                }
            ],
        },
        f"# Source {source_card_id}",
        rp.sources / f"{source_card_id}.md",
    )


def _plant_claim_ledger(
    paths: FoundryPaths,
    run_id: str,
    source_card_id: str,
    claim_id: str = "clm_001",
) -> None:
    """Write a claim_ledger.yaml referencing source_card_id."""
    rp = paths.run_paths(run_id)
    rp.claims.mkdir(parents=True, exist_ok=True)
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": claim_id,
                    "text": "Test claim text.",
                    "materiality": "primary",
                    "status": "supported",
                    "sources": [
                        {
                            "source_card_id": source_card_id,
                            "evidence_id": "ev_001",
                            "relation": "supports",
                        }
                    ],
                }
            ],
        },
        rp.claim_ledger,
    )


# ---------------------------------------------------------------------------
# TEST-001  GET /api/runs
# ---------------------------------------------------------------------------


def test_list_runs_empty_corpus_returns_empty_list(tmp_path):
    """Empty runs/ dir → [] (not 404)."""
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_runs_returns_summary_list(tmp_path):
    """Non-empty corpus → list of RFRunSummary-shaped dicts."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_test_001")

    resp = client.get("/api/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1

    summary = data[0]
    # Required RFRunSummary fields
    assert summary["run_id"] == "rf_run_test_001"
    assert "status_derived" in summary
    assert "sensitivity" in summary
    assert "created_at" in summary


def test_list_runs_multiple_runs(tmp_path):
    """Multiple planted runs appear in the list."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_alpha")
    _plant_run(cfg.paths, "rf_run_beta")

    resp = client.get("/api/runs")
    assert resp.status_code == 200
    ids = {r["run_id"] for r in resp.json()}
    assert "rf_run_alpha" in ids
    assert "rf_run_beta" in ids


# ---------------------------------------------------------------------------
# TEST-002  GET /api/runs/{run_id}
# ---------------------------------------------------------------------------


def test_get_run_detail_known_run_returns_200(tmp_path):
    """Known run_id → 200 with RFRunExport shape."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_detail_test")

    resp = client.get("/api/runs/rf_run_detail_test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "rf_run_detail_test"
    # Required RFRunExport fields
    assert "schema_version" in data
    assert "status_derived" in data
    assert "claims" in data
    assert isinstance(data["claims"], list)


def test_get_run_detail_unknown_run_returns_404(tmp_path):
    """Unknown run_id → 404 with structured {"detail": ...}."""
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/runs/rf_run_does_not_exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body


# ---------------------------------------------------------------------------
# TEST-003  GET /api/runs/{run_id}/claims and /sources/{id}
# ---------------------------------------------------------------------------


def test_get_claims_non_empty(tmp_path):
    """Run with claims → non-empty list."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_claims_test")
    _plant_source_card(cfg.paths, "rf_run_claims_test", "src_001")
    _plant_claim_ledger(cfg.paths, "rf_run_claims_test", "src_001")

    resp = client.get("/api/runs/rf_run_claims_test/claims")
    assert resp.status_code == 200
    claims = resp.json()
    assert isinstance(claims, list)
    assert len(claims) == 1
    assert claims[0]["claim_id"] == "clm_001"


def test_get_claims_empty_ledger_returns_empty_list(tmp_path):
    """Run with empty ledger → [] (not null or 404)."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_empty_claims")

    resp = client.get("/api/runs/rf_run_empty_claims/claims")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_claims_unknown_run_returns_404(tmp_path):
    """Unknown run_id → 404 with {"detail": ...}."""
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/runs/rf_run_ghost/claims")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_source_found(tmp_path):
    """Source cited in claims → 200 with source shape."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_src_test")
    _plant_source_card(cfg.paths, "rf_run_src_test", "src_abc")
    _plant_claim_ledger(cfg.paths, "rf_run_src_test", "src_abc")

    resp = client.get("/api/runs/rf_run_src_test/sources/src_abc")
    assert resp.status_code == 200
    src = resp.json()
    assert src["source_card_id"] == "src_abc"
    assert "resolved" in src


def test_get_source_not_found_returns_404(tmp_path):
    """Source not cited in any claim → 404."""
    client, cfg = _make_client(tmp_path)
    _plant_run(cfg.paths, "rf_run_src_missing")

    resp = client.get("/api/runs/rf_run_src_missing/sources/nonexistent_src")
    assert resp.status_code == 404
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# TEST-004  GET /data/governance.json
# ---------------------------------------------------------------------------


def test_governance_json_shape(tmp_path):
    """Returns GovernanceConfig shape (key_profiles + policy_rules keys)."""
    client, _ = _make_client(tmp_path)
    resp = client.get("/data/governance.json")
    assert resp.status_code == 200
    data = resp.json()
    # Shape: {key_profiles: ..., policy_rules: ...}
    assert "key_profiles" in data
    assert "policy_rules" in data


def test_governance_json_no_500_on_minimal_config(tmp_path):
    """Minimal foundry.yaml with no governance section → no 500."""
    root = tmp_path / "minimal"
    root.mkdir(parents=True)
    (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    (root / "runs").mkdir()
    paths = FoundryPaths(root=root)
    cfg = FoundryConfig(paths=paths)
    cfg.foundry.setdefault("viewer", {})  # type: ignore[arg-type]
    fastapi_app = create_app(cfg)
    from research_foundry.api.routers.runs import get_paths
    fastapi_app.dependency_overrides[get_paths] = lambda: cfg.paths
    client = TestClient(fastapi_app)

    resp = client.get("/data/governance.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "key_profiles" in data
    assert "policy_rules" in data


# ---------------------------------------------------------------------------
# TEST-005  GET /health
# ---------------------------------------------------------------------------


def test_health_under_auth_mode_none(tmp_path):
    """GET /health returns 200 when auth_mode=none."""
    client, _ = _make_client(tmp_path, auth_mode="none")
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_under_auth_mode_token(tmp_path, monkeypatch):
    """GET /health returns 200 even when auth_mode=token (health is always exempt)."""
    monkeypatch.setenv("RF_SERVE_TOKEN", "test-secret")
    client, _ = _make_client(tmp_path, auth_mode="token")
    # No Authorization header — /health must still pass.
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# TEST-006  Sensitivity-gate parity (MOST CRITICAL — Risk R1)
# ---------------------------------------------------------------------------


def test_sensitivity_gate_parity_work_sensitive_claim(tmp_path):
    """API response for a work_sensitive claim at threshold=public equals
    export_service.export_run() on the same fixture.

    This proves:
    1. The route does NOT bypass the sensitivity gate.
    2. quote and summary are replaced with REDACTION_MARKER.
    3. API response == direct export_service call (parity invariant).
    """
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    run_id = "rf_run_gate_parity"
    _plant_run(cfg.paths, run_id, sensitivity="work_sensitive")
    _plant_source_card(
        cfg.paths,
        run_id,
        "src_work",
        sensitivity="work_sensitive",
        quote="SECRET WORK QUOTE",
        summary="SECRET WORK SUMMARY",
    )
    _plant_claim_ledger(cfg.paths, run_id, "src_work", claim_id="clm_gate")

    # --- API response --------------------------------------------------------
    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    api_data = resp.json()

    # Confirm redaction actually happened in the API response.
    claim = next(c for c in api_data["claims"] if c["claim_id"] == "clm_gate")
    source = next(s for s in claim["sources"] if s["source_card_id"] == "src_work")
    assert source["redacted"] is True, "source must be marked redacted"
    assert source["quote"] == REDACTION_MARKER, (
        f"quote must be REDACTION_MARKER, got: {source['quote']!r}"
    )
    assert source["summary"] == REDACTION_MARKER, (
        f"summary must be REDACTION_MARKER, got: {source['summary']!r}"
    )
    # The raw secret strings must not appear anywhere in the API response.
    assert "SECRET WORK QUOTE" not in str(api_data)
    assert "SECRET WORK SUMMARY" not in str(api_data)

    # --- Direct export_service call (parity) ---------------------------------
    direct = export_run(cfg.paths, run_id, sensitivity_threshold="public")

    # Parity: every top-level key present in the API response should match the
    # direct call.  We compare claim-level source sensitivity specifically since
    # that is where R1 lives.
    direct_claim = next(c for c in direct["claims"] if c["claim_id"] == "clm_gate")
    direct_source = next(
        s for s in direct_claim["sources"] if s["source_card_id"] == "src_work"
    )
    assert source["redacted"] == direct_source["redacted"]
    assert source["quote"] == direct_source["quote"]
    assert source["summary"] == direct_source["summary"]

    # Scalar top-level fields must match.
    for key in ("run_id", "schema_version", "sensitivity_threshold", "status_derived"):
        assert api_data.get(key) == direct.get(key), (
            f"parity mismatch on {key!r}: API={api_data.get(key)!r} direct={direct.get(key)!r}"
        )


def test_sensitivity_gate_personal_at_personal_threshold_not_redacted(tmp_path):
    """A personal-sensitivity claim at threshold=personal is NOT redacted."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="personal")
    run_id = "rf_run_personal_pass"
    _plant_run(cfg.paths, run_id, sensitivity="personal")
    _plant_source_card(
        cfg.paths,
        run_id,
        "src_pers",
        sensitivity="personal",
        quote="personal quote",
        summary="personal summary",
    )
    _plant_claim_ledger(cfg.paths, run_id, "src_pers")

    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    claim = resp.json()["claims"][0]
    source = next(s for s in claim["sources"] if s["source_card_id"] == "src_pers")
    assert source["redacted"] is False
    assert source["quote"] == "personal quote"
    assert source["summary"] == "personal summary"
