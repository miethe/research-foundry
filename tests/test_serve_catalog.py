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
from research_foundry.api.routers.runs import get_paths as get_paths_dep
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


def _plant_run_with_terms(paths: FoundryPaths, run_id: str) -> None:
    """Two claims at different sensitivity ranks, each carrying a
    ``_term_index`` block on the SAME term (``cbc``) with a DIFFERENT role —
    mirrors ``tests/unit/test_catalog_terms.py``'s ``_build_two_rank_run``
    fixture, adapted to this file's ``_plant_run`` conventions, for
    serve-layer (HTTP) ``--term``/``--role`` passthrough (TASK-2.6) and
    sensitivity-gate-parity (TASK-2.7) tests.

    - ``clm_low`` cites ``src_public`` (no evidence-point override) -> the
      lowest possible effective rank (public).
    - ``clm_high`` cites ``src_sensitive`` whose evidence point is pinned
      ``work_sensitive`` -> a strictly higher effective rank.
    """

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "planned",
            "sensitivity": "public",
            "created_at": "2026-07-24T09:00:00-04:00",
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_public",
            "sensitivity": "public",
            "trust": "high",
            "usage": "direct",
            "source": {"title": "Public Source", "source_type": "web"},
            "extracted_points": [
                {
                    "evidence_id": "ev_pub",
                    "locator": "p1",
                    "quote": "PUBLIC QUOTE",
                    "summary": "public point",
                }
            ],
        },
        "",
        rp.sources / "src_public.md",
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_sensitive",
            "sensitivity": "public",
            "trust": "medium",
            "usage": "paraphrase",
            "source": {"title": "Sensitive Source", "source_type": "paper"},
            "extracted_points": [
                {
                    "evidence_id": "ev_sens",
                    "locator": "s1",
                    "quote": "SENSITIVE QUOTE",
                    "summary": "sensitive point",
                    "sensitivity": "work_sensitive",
                }
            ],
        },
        "",
        rp.sources / "src_sensitive.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_low",
                    "text": "CBC panel is unremarkable in this cohort.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_public",
                            "evidence_id": "ev_pub",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "_term_index": {
                        "terms": ["cbc"],
                        "usage_roles": {"cbc": "background"},
                        "vocabulary_version": "pediatric-v1",
                    },
                },
                {
                    "claim_id": "clm_high",
                    "text": "CBC threshold above 15 x10^9/L triggers escalation.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_sensitive",
                            "evidence_id": "ev_sens",
                            "relation": "supports",
                            "locator": "s1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "_term_index": {
                        "terms": ["cbc"],
                        "usage_roles": {"cbc": "threshold"},
                        "vocabulary_version": "pediatric-v1",
                    },
                },
            ],
        },
        rp.claim_ledger,
    )


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
        "facets": {
            "projects": [],
            "statuses": [],
            "sensitivities": [],
            "terms": [],
            "roles": [],
        },
        "rf_schema_version": "1.0.0",
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


def test_no_serve_override_defaults_to_public_threshold_unchanged(tmp_path):
    """(a) No explicit `rf serve --sensitivity-threshold` override → the
    foundry.yaml viewer default (``"public"`` in the shipped config) remains
    the effective catalog threshold, exactly as before the serve-override
    plumbing fix. This is the fail-closed invariant that must never regress:
    adding the override path must not change default (no-flag) behavior.
    """

    client, cfg = _make_client(tmp_path)
    assert cfg.viewer.get("sensitivity_threshold") == "public"

    _plant_run(cfg.paths, "rf_run_default_gate", sensitivity="client_sensitive")
    svc.import_run(cfg.paths, "rf_run_default_gate")

    stats_resp = client.get("/api/catalog/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["counts"]["claim"] == 0
    assert stats_data["counts"]["source"] == 0
    assert stats_data["runs_indexed"] == 0

    search_resp = client.get("/api/catalog/search")
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 0


def test_explicit_serve_override_takes_precedence_over_foundry_yaml(tmp_path):
    """(b) An explicit `rf serve --sensitivity-threshold` override must reach
    the catalog stats/search endpoints even when foundry.yaml on disk still
    says ``"public"``.

    Regression test for the catalog-visibility bug: ``rf serve
    --sensitivity-threshold client_sensitive`` mutates ``config.viewer
    ["sensitivity_threshold"]`` in memory (cli_commands.py's serve(), BEFORE
    calling create_app() — see that function's "Apply ALL CLI overrides to
    config BEFORE the gate runs" step). Prior to the fix, that mutation went
    nowhere the catalog router/service could see: ``get_paths()`` and
    ``catalog_service.resolve_threshold()`` both constructed a *fresh*
    ``FoundryConfig`` per request and re-read foundry.yaml from disk — which
    still said ``"public"`` — silently ignoring the serve-time override. We
    reproduce that exact mutation here (without touching the on-disk YAML) to
    prove the fix threads it through ``app.state`` instead.
    """

    cfg = _make_config(tmp_path)
    assert cfg.viewer.get("sensitivity_threshold") == "public"  # on-disk default, untouched

    # Simulate `rf serve --sensitivity-threshold client_sensitive`.
    cfg.viewer["sensitivity_threshold"] = "client_sensitive"

    app = create_app(cfg)
    app.dependency_overrides[get_paths_dep] = lambda: cfg.paths
    client = TestClient(app, raise_server_exceptions=True)

    _plant_run(cfg.paths, "rf_run_override_gate", sensitivity="client_sensitive")
    svc.import_run(cfg.paths, "rf_run_override_gate")

    stats_resp = client.get("/api/catalog/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["counts"]["claim"] == 1
    assert stats_data["counts"]["source"] == 1
    assert stats_data["runs_indexed"] == 1

    search_resp = client.get("/api/catalog/search")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] > 0


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
# term/role passthrough (claim-term-indexing v1, TASK-2.6)
# ---------------------------------------------------------------------------


def _local_refs(payload: dict) -> set[str]:
    return {item["local_ref"] for item in payload["items"]}


def test_search_term_query_param_matches_cli_layer_output(tmp_path):
    """AC: the endpoint's `term` param returns the same result set as
    `rf catalog search --term` (`catalog_service.search(term=...)`) for the
    same fixture — FR-13's "zero new read-path computation" means the router
    is a pure passthrough, so this is really testing that the wiring exists.
    """

    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run_with_terms(cfg.paths, "rf_run_term_api")
    svc.import_run(cfg.paths, "rf_run_term_api")

    resp = client.get("/api/catalog/search", params={"term": "cbc"})
    assert resp.status_code == 200
    data = resp.json()
    assert _local_refs(data) == {"clm_low", "clm_high"}

    direct = svc.search(cfg.paths, term=["cbc"], sensitivity_threshold="client_sensitive")
    assert _local_refs(direct) == _local_refs(data)
    assert direct["total"] == data["total"]


def test_search_role_query_param_narrows_to_matching_role(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run_with_terms(cfg.paths, "rf_run_role_api")
    svc.import_run(cfg.paths, "rf_run_role_api")

    resp = client.get("/api/catalog/search", params={"role": "threshold"})
    assert resp.status_code == 200
    assert _local_refs(resp.json()) == {"clm_high"}


def test_search_term_and_role_query_params_combine_with_and(tmp_path):
    """OQ-C at the HTTP layer: distinct params (`term` + `role`) combine
    with AND, not OR — a request is not silently ignoring one of them.
    """

    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run_with_terms(cfg.paths, "rf_run_and_api")
    svc.import_run(cfg.paths, "rf_run_and_api")

    resp = client.get("/api/catalog/search", params={"term": "cbc", "role": "background"})
    assert resp.status_code == 200
    assert _local_refs(resp.json()) == {"clm_low"}


def test_search_repeated_term_query_params_combine_with_or(tmp_path):
    """OQ-C at the HTTP layer: repeats of the SAME param (`?term=cbc&term=x`)
    OR together — a second `term=` value that matches nothing must not
    narrow the result produced by the first.
    """

    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run_with_terms(cfg.paths, "rf_run_or_api")
    svc.import_run(cfg.paths, "rf_run_or_api")

    resp = client.get(
        "/api/catalog/search",
        params=[("term", "cbc"), ("term", "not_a_real_term")],
    )
    assert resp.status_code == 200
    assert _local_refs(resp.json()) == {"clm_low", "clm_high"}


# ---------------------------------------------------------------------------
# sensitivity-threshold gate parity (TASK-2.7, PHASE EXIT GATE)
#
# Serve-layer (HTTP), not just service-layer -- the documented trap in this
# repo is that a router can silently ignore `rf serve --sensitivity-threshold`
# even when the underlying service function enforces it correctly (see the
# 5 known-failing tests in tests/test_serve_api.py this file's sibling
# baseline documents). Every threshold tier below is exercised through the
# actual HTTP client, never by calling catalog_service.search() directly.
# ---------------------------------------------------------------------------


def test_serve_term_filter_hides_above_threshold_row_at_public(tmp_path):
    """At the strictest tier (`public`), only `clm_low` (public rank) may
    match `--term cbc` -- `clm_high` (work_sensitive rank) must not appear,
    proving the term-row sensitivity gate is enforced through the live HTTP
    router, not only in the service function under direct test.
    """

    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    _plant_run_with_terms(cfg.paths, "rf_run_gate_public")
    svc.import_run(cfg.paths, "rf_run_gate_public")

    resp = client.get("/api/catalog/search", params={"term": "cbc"})
    assert resp.status_code == 200
    data = resp.json()
    assert _local_refs(data) == {"clm_low"}
    assert data["total"] == 1


def test_serve_term_filter_hides_above_threshold_row_at_personal(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="personal")
    _plant_run_with_terms(cfg.paths, "rf_run_gate_personal")
    svc.import_run(cfg.paths, "rf_run_gate_personal")

    resp = client.get("/api/catalog/search", params={"term": "cbc"})
    assert resp.status_code == 200
    assert _local_refs(resp.json()) == {"clm_low"}


def test_serve_term_filter_shows_both_rows_at_work_sensitive(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="work_sensitive")
    _plant_run_with_terms(cfg.paths, "rf_run_gate_ws")
    svc.import_run(cfg.paths, "rf_run_gate_ws")

    resp = client.get("/api/catalog/search", params={"term": "cbc"})
    assert resp.status_code == 200
    assert _local_refs(resp.json()) == {"clm_low", "clm_high"}


def test_serve_term_filter_shows_both_rows_at_client_sensitive(tmp_path):
    client, cfg = _make_client(tmp_path, sensitivity_threshold="client_sensitive")
    _plant_run_with_terms(cfg.paths, "rf_run_gate_cs")
    svc.import_run(cfg.paths, "rf_run_gate_cs")

    resp = client.get("/api/catalog/search", params={"term": "cbc"})
    assert resp.status_code == 200
    assert _local_refs(resp.json()) == {"clm_low", "clm_high"}


def test_serve_role_filter_never_exposes_above_threshold_role_at_any_tier(tmp_path):
    """AC-5, consolidated: across every defined threshold tier, `--role
    threshold` (the role that only exists on `clm_high`, the higher-rank
    claim) never surfaces a result above what that tier permits -- 0 items
    exposed above the requesting read's own sensitivity threshold, at every
    tested tier, via the live HTTP endpoint.
    """

    expected_by_tier = {
        "public": set(),
        "personal": set(),
        "work_sensitive": {"clm_high"},
        "client_sensitive": {"clm_high"},
    }
    for tier, expected in expected_by_tier.items():
        client, cfg = _make_client(tmp_path / tier, sensitivity_threshold=tier)
        _plant_run_with_terms(cfg.paths, f"rf_run_gate_role_{tier}")
        svc.import_run(cfg.paths, f"rf_run_gate_role_{tier}")

        resp = client.get("/api/catalog/search", params={"role": "threshold"})
        assert resp.status_code == 200
        assert _local_refs(resp.json()) == expected, f"tier={tier}"


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
    assert data == {
        "imported": {"runs": 1, "items": 2},  # 1 claim + 1 source
        "rf_schema_version": "1.0.0",
    }

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
    assert data == {
        "imported": {"runs": 2, "items": 4},
        "errors": [],
        "rf_schema_version": "1.0.0",
    }

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
        "rf_schema_version": "1.0.0",
    }
