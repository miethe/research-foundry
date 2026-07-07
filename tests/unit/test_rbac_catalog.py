"""RBAC enforcement tests for catalog.py mutation routes (RBAC-003).

Verifies that:
  - Under-privileged roles receive 403 on every mutation route.
  - Permitted roles are not blocked by RBAC (may receive other error codes
    from the service layer, e.g. 404 for an unknown run_id, but not 403).
  - The no-auth / single-operator-trust mode always allows (no identity set).

Catalog mutation routes under test:
  POST /api/catalog/import/run/{run_id}
  POST /api/catalog/import
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> FoundryConfig:
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
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    return FoundryConfig(paths=FoundryPaths(root=root))


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Test middleware that injects a fixed AuthIdentity onto request.state."""

    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        # When self._identity is None, leave request.state.identity absent →
        # single-operator-trust semantics (no-auth mode).
        return await call_next(request)


def _make_client(tmp_path: Path, identity: AuthIdentity | None = None) -> TestClient:
    cfg = _make_config(tmp_path)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


# Denied identity: reviewer has no catalog mutation permissions.
_REVIEWER = AuthIdentity("reviewer_user", "ws1", ("reviewer",))
# Denied identity: viewer has zero permissions.
_VIEWER = AuthIdentity("viewer_user", "ws1", ("viewer",))
# Allowed identity: researcher has catalog:create and catalog:update.
_RESEARCHER = AuthIdentity("researcher_user", "ws1", ("researcher",))
# Allowed identity: owner has all permissions.
_OWNER = AuthIdentity("owner_user", "ws1", ("owner",))


# ---------------------------------------------------------------------------
# POST /api/catalog/import/run/{run_id}
# ---------------------------------------------------------------------------


class TestCatalogImportRunRBAC:
    def test_reviewer_gets_403(self, tmp_path):
        client = _make_client(tmp_path, identity=_REVIEWER)
        resp = client.post("/api/catalog/import/run/rf_test_run_001")
        assert resp.status_code == 403

    def test_viewer_gets_403(self, tmp_path):
        client = _make_client(tmp_path, identity=_VIEWER)
        resp = client.post("/api/catalog/import/run/rf_test_run_001")
        assert resp.status_code == 403

    def test_researcher_not_blocked_by_rbac(self, tmp_path):
        client = _make_client(tmp_path, identity=_RESEARCHER)
        resp = client.post("/api/catalog/import/run/rf_nonexistent_run")
        # May return 404 (run not found) but must not return 403.
        assert resp.status_code != 403

    def test_owner_not_blocked_by_rbac(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        resp = client.post("/api/catalog/import/run/rf_nonexistent_run")
        assert resp.status_code != 403

    def test_no_auth_single_operator_trust_allows(self, tmp_path):
        # No identity injected → auth disabled mode → must not get 403.
        client = _make_client(tmp_path, identity=None)
        resp = client.post("/api/catalog/import/run/rf_nonexistent_run")
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# POST /api/catalog/import
# ---------------------------------------------------------------------------


class TestCatalogImportAllRBAC:
    def test_reviewer_gets_403(self, tmp_path):
        client = _make_client(tmp_path, identity=_REVIEWER)
        resp = client.post("/api/catalog/import")
        assert resp.status_code == 403

    def test_viewer_gets_403(self, tmp_path):
        client = _make_client(tmp_path, identity=_VIEWER)
        resp = client.post("/api/catalog/import")
        assert resp.status_code == 403

    def test_researcher_not_blocked_by_rbac(self, tmp_path):
        client = _make_client(tmp_path, identity=_RESEARCHER)
        resp = client.post("/api/catalog/import")
        assert resp.status_code != 403

    def test_owner_not_blocked_by_rbac(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        resp = client.post("/api/catalog/import")
        assert resp.status_code != 403

    def test_no_auth_single_operator_trust_allows(self, tmp_path):
        client = _make_client(tmp_path, identity=None)
        resp = client.post("/api/catalog/import")
        assert resp.status_code != 403
