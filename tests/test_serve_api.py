"""Tests for the RF loopback API endpoints (TEST-001..006, TEST-011).

Coverage:
  TEST-001  GET /api/runs  — list shape; empty corpus → []; RFRunSummary fields.
  TEST-002  GET /api/runs/{run_id}  — known→200+shape; unknown→404 with {"detail":...}.
  TEST-003  GET /api/runs/{run_id}/claims and /sources/{id}.
  TEST-004  GET /data/governance.json  — GovernanceConfig shape; no 500 on minimal config.
  TEST-005  GET /health  — 200 under both auth_mode=none and auth_mode=token.
  TEST-006  Sensitivity-gate parity (MOST CRITICAL): API response == export_service.export_run()
            for a work_sensitive claim with threshold=public; also confirms quote/summary
            are replaced with the REDACTION_MARKER so the gate is never bypassed.
  TEST-011  POST /api/runs (http-run-launch-endpoint) — text path 201 + GET parity;
            intent_id path 201 with raw_idea_id null; both/neither-set 400; unknown
            intent_id 404; governance-block 422; RBAC 403/201 under auth_mode=token;
            audit event written; pre-existing GET routes unchanged (regression).
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


def _make_rbac_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    roles: list[str],
) -> tuple[TestClient, FoundryConfig, str]:
    """Build a client with ``auth.provider=local_static`` granting *roles*.

    Mirrors ``tests/test_serve_auth.py``'s ``local_static`` fixture pattern
    (TEST-007/AUTH-106) — the only existing example of a role-bearing bearer
    token in this codebase's test suite. Returns ``(client, cfg, token)``.
    """
    cfg = _make_config(tmp_path)
    token = "run-launch-rbac-test-token"
    from research_foundry.yamlio import dump_yaml as _dump_yaml
    from research_foundry.yamlio import load_yaml as _load_yaml

    foundry_yaml_path = cfg.paths.root / "foundry.yaml"
    existing: dict[str, Any] = _load_yaml(foundry_yaml_path) or {}
    existing.setdefault("foundry", {})["auth"] = {
        "provider": "local_static",
        "local_static": {
            "tokens": [
                {
                    "token_env": "RF_RUN_LAUNCH_TEST_TOKEN",
                    "user_id": "test_user",
                    "workspace_id": "default",
                    "roles": roles,
                }
            ]
        },
    }
    _dump_yaml(existing, foundry_yaml_path)
    cfg2 = FoundryConfig(paths=cfg.paths)

    monkeypatch.setenv("RF_RUN_LAUNCH_TEST_TOKEN", token)
    app = create_app(cfg2)
    from research_foundry.api.routers.runs import get_paths
    app.dependency_overrides[get_paths] = lambda: cfg2.paths
    return TestClient(app, raise_server_exceptions=True), cfg2, token


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
# TEST-012  GET /api/runs/{run_id}/context (DFR-001 v2 lazy-load endpoint)
# ---------------------------------------------------------------------------


def _plant_run_context(
    paths: FoundryPaths,
    run_id: str,
    *,
    routing_sensitivity: str | None = None,
    swarm_sensitivity: str | None = None,
) -> None:
    """Write routing_decision.yaml + swarm_plan.yaml for *run_id*.

    Mirrors ``tests/unit/test_export_service.py::_build_run_with_routing`` —
    the only existing fixture that exercises ``export_service._context_summary``.
    ``*_sensitivity`` optionally sets the artifact-level ``sensitivity`` label
    consumed by the context redaction pass (P2-003).
    """
    rp = paths.run_paths(run_id)
    routing: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "routing_decision",
        "id": f"route_{run_id}",
        "selected_abstraction_level": "L4",
        "rationale": "Test rationale for routing",
        "human_required": False,
    }
    if routing_sensitivity is not None:
        routing["sensitivity"] = routing_sensitivity
    dump_yaml(routing, rp.routing_decision)

    swarm: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "swarm_plan",
        "id": f"swarm_{run_id}",
        "agents": [{"role": "source_scout", "posture": "researcher"}],
        "required_outputs": ["source_cards"],
    }
    if swarm_sensitivity is not None:
        swarm["sensitivity"] = swarm_sensitivity
    dump_yaml(swarm, rp.swarm_plan)


def test_get_context_unknown_run_returns_404(tmp_path):
    """Unknown run_id → 404 with structured {"detail": ...}."""
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/runs/rf_run_ctx_ghost/context")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_context_null_when_no_context_artifacts(tmp_path):
    """Run exists but has no routing_decision/swarm_plan/research_brief →
    200 with JSON null (not 404, not {}).

    ``sensitivity_threshold="personal"`` is pinned explicitly (matching
    ``_plant_run``'s default ``sensitivity="personal"``) rather than relying
    on the copied dist ``foundry.yaml`` template's default — the same
    ambient-default gap that pre-dates this endpoint and already fails
    ``test_get_run_detail_known_run_returns_200`` et al. on this worktree.
    """
    client, cfg = _make_client(tmp_path, sensitivity_threshold="personal")
    _plant_run(cfg.paths, "rf_run_ctx_empty")

    resp = client.get("/api/runs/rf_run_ctx_empty/context")
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_context_populated_matches_run_json_context_key(tmp_path):
    """Populated context → 200 with the identical shape as
    export_run(...)["context"] (parity with run.json's "context" key).

    ``sensitivity_threshold`` pinned to "personal" — see
    ``test_get_context_null_when_no_context_artifacts`` docstring.
    """
    client, cfg = _make_client(tmp_path, sensitivity_threshold="personal")
    run_id = "rf_run_ctx_populated"
    _plant_run(cfg.paths, run_id)
    _plant_run_context(cfg.paths, run_id)

    resp = client.get(f"/api/runs/{run_id}/context")
    assert resp.status_code == 200
    ctx = resp.json()
    assert ctx is not None
    assert ctx["routing_decision"]["rationale"] == "Test rationale for routing"
    assert ctx["swarm_plan"]["agents"] == ["source_scout"]

    direct = export_run(cfg.paths, run_id, sensitivity_threshold="personal")
    assert ctx == direct["context"]


def test_get_context_sensitivity_existence_gate_returns_404(tmp_path):
    """A work_sensitive run at threshold=public → 404 on /context too (same
    no-existence-leak gate as GET /runs/{run_id} and /claims)."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    run_id = "rf_run_ctx_gated"
    _plant_run(cfg.paths, run_id, sensitivity="work_sensitive")
    _plant_run_context(cfg.paths, run_id)

    resp = client.get(f"/api/runs/{run_id}/context")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_context_redacts_over_threshold_artifact_content(tmp_path):
    """Run itself is at/under threshold, but routing_decision.yaml carries a
    higher artifact-level sensitivity → its string fields are redacted
    (P2-003), matching export_service parity."""
    client, cfg = _make_client(tmp_path, sensitivity_threshold="public")
    run_id = "rf_run_ctx_redact"
    _plant_run(cfg.paths, run_id, sensitivity="public")
    _plant_run_context(cfg.paths, run_id, routing_sensitivity="work_sensitive")

    resp = client.get(f"/api/runs/{run_id}/context")
    assert resp.status_code == 200
    ctx = resp.json()
    assert ctx is not None
    assert ctx["routing_decision"]["rationale"] == REDACTION_MARKER
    assert "Test rationale for routing" not in str(ctx)

    direct = export_run(cfg.paths, run_id, sensitivity_threshold="public")
    assert ctx == direct["context"]


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


# ---------------------------------------------------------------------------
# TEST-011  POST /api/runs (http-run-launch-endpoint contract)
# ---------------------------------------------------------------------------


def _plant_intent(paths: FoundryPaths, *, key_profile_allowed: str = "personal") -> str:
    """Minimal intent fixture — same shape as test_cli_governance.py::_write_intent."""
    intent_id = "intent_research_20260613_demo_topic"
    dump_yaml(
        {
            "id": intent_id,
            "title": "Demo research topic",
            "owner": "Tester",
            "status": "active",
            "type": "research",
            "objective": "Investigate the demo topic deterministically.",
            "governance": {
                "sensitivity": "personal",
                "key_profile_allowed": key_profile_allowed,
                "requires_human_review": False,
                "allowed_writebacks": ["meatywiki_personal"],
            },
        },
        paths.intents_active / f"{intent_id}.yaml",
    )
    return intent_id


def test_launch_run_text_path_returns_201_and_resolves_via_get(tmp_path):
    """TEST-011a: text path -> 201; run_id then resolves via GET with status_derived=='planned'.

    Passes ``sensitivity_threshold=personal`` explicitly on the follow-up GET:
    ``launch_run`` defaults to ``sensitivity="personal"`` (contract default)
    while ``GET /api/runs/{run_id}``'s own default threshold is
    ``"public"`` (``export_service.DEFAULT_THRESHOLD``) — a caller reading
    back a personal-sensitivity run at the default threshold would 404 via
    the no-existence-leak gate regardless of this endpoint; that is
    pre-existing `_enforce_existence_gate` behavior, not something this
    contract changes, so the test overrides the threshold to isolate the
    run-launch behavior under test.
    """
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/runs", json={"text": "Research evidence bundle traceability."})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "planned"
    assert body["raw_idea_id"] is not None
    assert body["intent_id"] is not None
    assert "next_step" in body

    get_resp = client.get(
        f"/api/runs/{body['run_id']}", params={"sensitivity_threshold": "personal"}
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status_derived"] == "planned"


def test_launch_run_intent_id_path_skips_capture_triage(tmp_path):
    """TEST-011b: intent_id path -> 201; skips capture/triage; raw_idea_id is null."""
    client, cfg = _make_client(tmp_path)
    intent_id = _plant_intent(cfg.paths)

    resp = client.post("/api/runs", json={"intent_id": intent_id})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["raw_idea_id"] is None
    assert body["intent_id"] == intent_id
    assert body["status"] == "planned"


def test_launch_run_both_text_and_intent_id_returns_400(tmp_path):
    """TEST-011c: both text and intent_id set -> 400."""
    client, cfg = _make_client(tmp_path)
    intent_id = _plant_intent(cfg.paths)

    resp = client.post(
        "/api/runs", json={"text": "some idea", "intent_id": intent_id}
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_launch_run_neither_text_nor_intent_id_returns_400(tmp_path):
    """TEST-011d: neither text nor intent_id set -> 400."""
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/runs", json={})
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_launch_run_unknown_intent_id_returns_404(tmp_path):
    """TEST-011e: unknown intent_id -> 404."""
    client, _ = _make_client(tmp_path)
    resp = client.post("/api/runs", json={"intent_id": "intent_does_not_exist"})
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_launch_run_governance_block_returns_422(tmp_path):
    """TEST-011f: governance-blocked plan -> 422 with {"error": "governance_rejected", ...}."""
    client, cfg = _make_client(tmp_path)
    intent_id = _plant_intent(cfg.paths, key_profile_allowed="personal")

    resp = client.post(
        "/api/runs", json={"intent_id": intent_id, "profile": "work_approved"}
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()["detail"]
    assert body["error"] == "governance_rejected"
    assert isinstance(body["violations"], list)
    assert body["violations"], "expected at least one violation entry"
    assert "rule_id" in body["violations"][0]


def test_launch_run_writes_exactly_one_audit_event(tmp_path):
    """TEST-011g: a successful launch writes exactly one run_launched audit event."""
    from research_foundry.services.rbac_store import _connect

    client, cfg = _make_client(tmp_path)
    resp = client.post("/api/runs", json={"text": "Audit event coverage check."})
    assert resp.status_code == 201, resp.text

    conn = _connect(cfg.paths)
    try:
        rows = conn.execute(
            "SELECT * FROM audit_event WHERE mutation_type = 'run_launched'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1, f"expected exactly 1 run_launched audit row, found {len(rows)}"
    assert rows[0]["target_ref"] == resp.json()["run_id"]


def test_launch_run_rbac_forbidden_without_role(tmp_path, monkeypatch):
    """TEST-011h: auth_mode=token + no owner/admin role -> 403."""
    client, _cfg, token = _make_rbac_client(tmp_path, monkeypatch, roles=["viewer"])
    resp = client.post(
        "/api/runs",
        json={"text": "Should be forbidden."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_launch_run_rbac_allowed_with_owner_role(tmp_path, monkeypatch):
    """TEST-011i: auth_mode=token + owner role + valid bearer token -> 201."""
    client, _cfg, token = _make_rbac_client(tmp_path, monkeypatch, roles=["owner"])
    resp = client.post(
        "/api/runs",
        json={"text": "Should succeed with owner role."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# TEST-011j  Regression: pre-existing GET routes unchanged (additive-only)
# ---------------------------------------------------------------------------


def test_existing_get_routes_unaffected_by_new_mutation_route(tmp_path):
    """TEST-011j: the five pre-existing GET routes still behave identically.

    Uses ``sensitivity_threshold="personal"`` (matching ``_plant_run``'s
    default sensitivity) so this regression check is isolated from the
    pre-existing, unrelated default-threshold/default-sensitivity mismatch
    in ``_enforce_existence_gate`` (see the note on
    ``test_launch_run_text_path_returns_201_and_resolves_via_get`` above).
    """
    client, cfg = _make_client(tmp_path, sensitivity_threshold="personal")
    _plant_run(cfg.paths, "rf_run_regression_check")
    _plant_source_card(cfg.paths, "rf_run_regression_check", "src_reg")
    _plant_claim_ledger(cfg.paths, "rf_run_regression_check", "src_reg")

    assert client.get("/api/runs").status_code == 200
    assert client.get("/api/runs/rf_run_regression_check").status_code == 200
    assert client.get("/api/runs/rf_run_regression_check/claims").status_code == 200
    assert (
        client.get("/api/runs/rf_run_regression_check/sources/src_reg").status_code
        == 200
    )
    assert client.get("/api/reports/rf_run_regression_check/anchors").status_code == 200
