"""DF-004: runs/claims/evidence workspace-isolation read + stamping tests.

Covers the runs read-surface half of DF-004 (the writeback-approve gate lives
in ``tests/test_writeback_router.py`` and the agent-jobs row-9 fix in
``tests/unit/test_agent_jobs_workspace_stamp.py``):

  * launch stamps ``run.yaml.workspace_id`` from ``identity.workspace_id``,
    NEVER from client-supplied input (mirrors ``builder_service.create_draft``);
  * a cross-workspace GET returns an indistinguishable 404 under enforcement
    (never a 403 — no-existence-leak);
  * a ``visibility: public`` run is readable cross-workspace regardless of
    enforcement;
  * advisory mode allows the cross-workspace read (and logs) — non-breaking;
  * ``identity=None`` (single-operator-trust / auth_mode=none, i.e. the LAN
    single_user deployment) reads everything, byte-identical to pre-DF-004;
  * ``GET /runs`` list filtering omits unreadable runs under enforcement.
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
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, *, auth_mode: str = "none") -> FoundryConfig:
    """Minimal FoundryConfig pointing at a temp workspace (mirrors the
    ``tests/test_serve_api.py::_make_config`` scaffold)."""
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
    existing: dict[str, Any] = load_yaml(foundry_yaml_path) or {}
    if not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    existing["foundry"]["viewer"] = {"auth_mode": auth_mode}
    dump_yaml(existing, foundry_yaml_path)

    return FoundryConfig(paths=FoundryPaths(root=root))


# Two workspaces, two bearer tokens, one local_static config.
_TOKENS = {
    "ws-owner": ("RF_DF004_TOKEN_OWNER", "df004-owner-token"),
    "ws-caller": ("RF_DF004_TOKEN_CALLER", "df004-caller-token"),
}


def _make_config_with_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> FoundryConfig:
    """local_static auth granting a real ``request.state.identity`` for each of
    the two workspaces in ``_TOKENS`` (bearer-token → workspace mapping)."""
    cfg = _make_config(tmp_path)
    foundry_yaml_path = cfg.paths.root / "foundry.yaml"
    existing = load_yaml(foundry_yaml_path) or {}
    tokens = []
    for workspace_id, (token_env, token) in _TOKENS.items():
        monkeypatch.setenv(token_env, token)
        tokens.append(
            {
                "token_env": token_env,
                "user_id": f"user_{workspace_id}",
                "workspace_id": workspace_id,
                "roles": ["owner"],
            }
        )
    existing["foundry"]["auth"] = {
        "provider": "local_static",
        "local_static": {"tokens": tokens},
    }
    dump_yaml(existing, foundry_yaml_path)
    return FoundryConfig(paths=cfg.paths)


def _auth(workspace_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_TOKENS[workspace_id][1]}"}


def _client(cfg: FoundryConfig) -> TestClient:
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    return TestClient(app, raise_server_exceptions=True)


def _set_enforcement(monkeypatch: pytest.MonkeyPatch, enforced: bool) -> None:
    """Force the WKSP-304/DF-004 enforcement truth table deterministically."""
    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: enforced,
    )


def _plant_run(
    paths: FoundryPaths,
    run_id: str,
    *,
    workspace_id: str | None = None,
    visibility: str = "workspace",
    sensitivity: str = "public",
) -> None:
    """Write a minimal run scaffold export_service can discover.

    ``sensitivity=public`` keeps the orthogonal sensitivity gate out of the
    way so these tests isolate the workspace gate.
    """
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    doc: dict[str, Any] = {
        "run_id": run_id,
        "intent_id": f"intent_{run_id}",
        "status": "planned",
        "sensitivity": sensitivity,
        "visibility": visibility,
        "created_at": "2026-07-23T09:41:00+00:00",
    }
    if workspace_id is not None:
        doc["workspace_id"] = workspace_id
    dump_yaml(doc, rp.run_yaml)


# ---------------------------------------------------------------------------
# Read-scope gate — the security core
# ---------------------------------------------------------------------------

def test_cross_workspace_get_is_indistinguishable_404_when_enforcing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    _set_enforcement(monkeypatch, True)
    _plant_run(cfg.paths, "run_owned", workspace_id="ws-owner")
    client = _client(cfg)

    # Owner reads its own run.
    owner_resp = client.get("/api/runs/run_owned", headers=_auth("ws-owner"))
    assert owner_resp.status_code == 200, owner_resp.text

    # A different workspace gets the SAME 404 a missing run would produce.
    caller_resp = client.get("/api/runs/run_owned", headers=_auth("ws-caller"))
    missing_resp = client.get("/api/runs/run_does_not_exist", headers=_auth("ws-caller"))
    assert caller_resp.status_code == 404
    assert missing_resp.status_code == 404
    # Indistinguishable: identical body, never a 403 that would confirm existence.
    assert caller_resp.json() == missing_resp.json()


def test_public_run_readable_cross_workspace_even_when_enforcing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    _set_enforcement(monkeypatch, True)
    _plant_run(cfg.paths, "run_public", workspace_id="ws-owner", visibility="public")
    client = _client(cfg)

    resp = client.get("/api/runs/run_public", headers=_auth("ws-caller"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["run_id"] == "run_public"


def test_advisory_mode_allows_cross_workspace_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    _set_enforcement(monkeypatch, False)  # advisory (WKSP-301 default)
    _plant_run(cfg.paths, "run_owned", workspace_id="ws-owner")
    client = _client(cfg)

    with caplog.at_level("WARNING"):
        resp = client.get("/api/runs/run_owned", headers=_auth("ws-caller"))
    assert resp.status_code == 200, resp.text
    assert any("workspace_scope_advisory_mismatch" in r.message for r in caplog.records)


def test_single_operator_trust_reads_everything(tmp_path: Path) -> None:
    """auth_mode=none → identity=None → the LAN single_user deployment path is
    byte-identical to pre-DF-004: every run is readable, no gate applies."""
    cfg = _make_config(tmp_path, auth_mode="none")
    _plant_run(cfg.paths, "run_a", workspace_id="ws-owner")
    _plant_run(cfg.paths, "run_b", workspace_id="ws-other")
    client = _client(cfg)

    assert client.get("/api/runs/run_a").status_code == 200
    assert client.get("/api/runs/run_b").status_code == 200
    assert {r["run_id"] for r in client.get("/api/runs").json()} == {"run_a", "run_b"}


def test_list_runs_filters_unreadable_when_enforcing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    _set_enforcement(monkeypatch, True)
    _plant_run(cfg.paths, "run_mine", workspace_id="ws-owner")
    _plant_run(cfg.paths, "run_theirs", workspace_id="ws-caller")
    _plant_run(cfg.paths, "run_public", workspace_id="ws-caller", visibility="public")
    client = _client(cfg)

    listed = {r["run_id"] for r in client.get("/api/runs", headers=_auth("ws-owner")).json()}
    assert listed == {"run_mine", "run_public"}  # own + public; NOT run_theirs


def test_sub_resources_inherit_run_workspace_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """claims/context/anchors all route through the same gate → 404 for a
    cross-workspace caller under enforcement."""
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    _set_enforcement(monkeypatch, True)
    _plant_run(cfg.paths, "run_owned", workspace_id="ws-owner")
    client = _client(cfg)

    for path in ("claims", "context", "anchors"):
        endpoint = (
            f"/api/reports/run_owned/anchors"
            if path == "anchors"
            else f"/api/runs/run_owned/{path}"
        )
        resp = client.get(endpoint, headers=_auth("ws-caller"))
        assert resp.status_code == 404, f"{path}: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Launch stamping — identity overrides client input
# ---------------------------------------------------------------------------

def test_launch_stamps_workspace_id_from_identity_not_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /runs stamps run.yaml.workspace_id from the authenticated identity,
    ignoring any client-supplied workspace_id (there is no such request field —
    this proves it can't be reintroduced by a spoofed body key either)."""
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    client = _client(cfg)

    resp = client.post(
        "/api/runs",
        json={"text": "Owner-stamped launch.", "workspace_id": "ws-EVIL-SPOOF"},
        headers=_auth("ws-owner"),
    )
    assert resp.status_code == 201, resp.text
    run_id = resp.json()["run_id"]

    run_yaml = load_yaml(cfg.paths.run_paths(run_id).run_yaml)
    assert run_yaml["workspace_id"] == "ws-owner"  # identity, not the spoofed body
    assert run_yaml.get("visibility") == "workspace"  # default


def test_launch_honors_public_visibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _make_config_with_identities(tmp_path, monkeypatch)
    client = _client(cfg)

    resp = client.post(
        "/api/runs",
        json={"text": "Public run.", "visibility": "public"},
        headers=_auth("ws-owner"),
    )
    assert resp.status_code == 201, resp.text
    run_yaml = load_yaml(cfg.paths.run_paths(resp.json()["run_id"]).run_yaml)
    assert run_yaml["workspace_id"] == "ws-owner"
    assert run_yaml["visibility"] == "public"
