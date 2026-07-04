"""Tests for the catalog API endpoints (public-multiuser-release Phase 1).

Coverage:
  stats   — GET /api/catalog/stats: zeroed on an empty catalog; counts after import.
  search  — GET /api/catalog/search: q/filters/pagination; sensitivity threshold
            enforcement (parity with catalog_service.search()).
  detail  — GET /api/catalog/items/{id}: 200 shape + payload/links; 404 for both
            an unknown id and a threshold-excluded id.
  import  — POST /api/catalog/import/run/{run_id} and /api/catalog/import:
            {"imported": {"runs", "items"}} shape; 404 for an unknown run_id.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import catalog_service as svc
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Helpers (mirror tests/test_serve_api.py's _make_config / _make_client)
# ---------------------------------------------------------------------------


def _make_config(
    tmp_path: Path,
    *,
    sensitivity_threshold: str | None = None,
) -> FoundryConfig:
    import shutil

    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)

    from research_foundry.paths import distribution_root

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


def _plant_run(paths: FoundryPaths, run_id: str, *, sensitivity: str = "public") -> None:
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
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_001",
            "sensitivity": sensitivity,
            "trust": "high",
            "usage": "direct",
            "source": {"title": "Source 001", "source_type": "web"},
            "extracted_points": [
                {
                    "evidence_id": "ev_001",
                    "locator": "p1",
                    "quote": "some quote",
                    "summary": "some summary",
                }
            ],
        },
        f"# Source {run_id}",
        rp.sources / "src_001.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "A supported claim about the run topic.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_001",
                            "evidence_id": "ev_001",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                }
            ],
        },
        rp.claim_ledger,
    )


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def test_stats_empty_catalog(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/catalog/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["runs_indexed"] == 0
    assert data["last_import_at"] is None
    for item_type in svc.ITEM_TYPES:
        assert data["counts"][item_type] == 0


def test_stats_after_import(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_stats")
    svc.import_run(cfg.paths, "rf_run_stats")

    resp = client.get("/api/catalog/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["runs_indexed"] == 1
    assert data["counts"]["claim"] == 1
    assert data["counts"]["source"] == 1


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_empty_catalog_returns_empty_not_404(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/catalog/search")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 25,
        "facets": {"projects": [], "statuses": [], "sensitivities": []},
    }


def test_search_after_import_finds_claim(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_search")
    svc.import_run(cfg.paths, "rf_run_search")

    resp = client.get("/api/catalog/search", params={"q": "supported"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["local_ref"] == "clm_001"
    assert data["items"][0]["item_type"] == "claim"


def test_search_item_type_filter(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_filter")
    svc.import_run(cfg.paths, "rf_run_filter")

    resp = client.get("/api/catalog/search", params={"item_type": "source"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["item_type"] == "source"


def test_search_sensitivity_threshold_enforced(tmp_path):
    """Parity: the API applies the exact same gate as catalog_service.search()."""

    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_run_gate", sensitivity="work_sensitive")
    svc.import_run(cfg.paths, "rf_run_gate")

    resp = client.get("/api/catalog/search")
    assert resp.status_code == 200
    data = resp.json()
    # Everything in this run is work_sensitive; threshold=public excludes it all.
    assert data["items"] == []
    assert data["total"] == 0

    direct = svc.search(cfg.paths)
    assert direct["total"] == data["total"]


def test_search_pagination_params(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_page")
    svc.import_run(cfg.paths, "rf_run_page")

    resp = client.get("/api/catalog/search", params={"page": 1, "page_size": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["items"]) <= 1


def test_search_page_size_capped_at_200(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/catalog/search", params={"page_size": 9999})
    assert resp.status_code == 422  # FastAPI Query(le=200) validation


# ---------------------------------------------------------------------------
# item detail
# ---------------------------------------------------------------------------


def test_get_item_known_id_returns_detail(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_detail")
    svc.import_run(cfg.paths, "rf_run_detail")

    item_id = svc._make_item_id("claim", "rf_run_detail", "clm_001")
    resp = client.get(f"/api/catalog/items/{item_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["catalog_item_id"] == item_id
    assert data["item_type"] == "claim"
    assert "payload" in data
    assert "links" in data
    assert "outgoing" in data["links"]
    assert "incoming" in data["links"]


def test_get_item_unknown_id_returns_404(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/catalog/items/ci_doesnotexist")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_item_excluded_by_threshold_returns_404(tmp_path):
    """A real item, but hidden by the resolved threshold, is also 404 (fail-closed)."""

    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run(cfg.paths, "rf_run_hidden", sensitivity="client_sensitive")
    svc.import_run(cfg.paths, "rf_run_hidden")

    item_id = svc._make_item_id("claim", "rf_run_hidden", "clm_001")
    resp = client.get(f"/api/catalog/items/{item_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


def test_post_import_run(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_import_one")

    resp = client.post("/api/catalog/import/run/rf_run_import_one")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"imported": {"runs": 1, "items": 2}}  # 1 claim + 1 source

    # Idempotent: importing again does not error or duplicate.
    resp2 = client.post("/api/catalog/import/run/rf_run_import_one")
    assert resp2.status_code == 200
    assert resp2.json() == data


def test_post_import_run_unknown_returns_404(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/catalog/import/run/rf_run_ghost")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_post_import_all(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_all_a")
    _plant_run(cfg.paths, "rf_run_all_b")

    resp = client.post("/api/catalog/import")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"imported": {"runs": 2, "items": 4}, "errors": []}

    stats_resp = client.get("/api/catalog/stats")
    assert stats_resp.json()["runs_indexed"] == 2


def test_post_import_all_passes_through_errors(tmp_path, monkeypatch):
    """F8: POST /api/catalog/import must not drop import_all()'s per-run
    errors list — the router previously discarded it entirely."""

    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run(cfg.paths, "rf_run_ok")

    def _fake_import_all(paths):
        return {
            "runs": 1,
            "items": 2,
            "errors": [{"run_id": "rf_run_bad", "error": "boom"}],
        }

    monkeypatch.setattr(svc, "import_all", _fake_import_all)

    resp = client.post("/api/catalog/import")
    assert resp.status_code == 200
    assert resp.json() == {
        "imported": {"runs": 1, "items": 2},
        "errors": [{"run_id": "rf_run_bad", "error": "boom"}],
    }
