"""RBAC enforcement tests for audit.py read routes (RBAC-006).

Verifies that:
  - Non-admin roles (viewer, reviewer, researcher) receive 403 on all three routes.
  - Admin and owner roles are not blocked (may receive any non-403 response).
  - The no-auth / single-operator-trust mode always allows.

Audit read routes under test (3 total):
  GET /api/audit
  GET /api/audit/health
  GET /api/audit/{audit_event_id}
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
from research_foundry.services import audit_service
from research_foundry.services.audit_service import AuditEvent
from research_foundry.yamlio import dump_yaml, load_yaml


# ---------------------------------------------------------------------------
# Fixtures & helpers (mirrors pattern from test_rbac_reports.py)
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
    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


def _make_client(tmp_path: Path, identity: AuthIdentity | None = None) -> TestClient:
    cfg = _make_config(tmp_path)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Identities
# ---------------------------------------------------------------------------

# Denied (no audit:read / admin-class access)
_VIEWER = AuthIdentity("viewer", "ws1", ("viewer",))
_REVIEWER = AuthIdentity("reviewer", "ws1", ("reviewer",))
_RESEARCHER = AuthIdentity("researcher", "ws1", ("researcher",))

# Allowed
_ADMIN = AuthIdentity("admin", "ws1", ("admin",))
_OWNER = AuthIdentity("owner", "ws1", ("owner",))

# Placeholder audit event id — will produce 404 from the service layer,
# which is correct: we just need to confirm no 403 for permitted roles.
_EVT = "aud_testevt000001"


# ---------------------------------------------------------------------------
# Parametrised route table
# ---------------------------------------------------------------------------

AUDIT_ROUTES = [
    ("GET", "/api/audit"),
    ("GET", "/api/audit/health"),
    ("GET", f"/api/audit/{_EVT}"),
]


# ---------------------------------------------------------------------------
# Helper: assert 403 / non-403
# ---------------------------------------------------------------------------


def _check_forbidden(client: TestClient, method: str, path: str) -> None:
    resp = getattr(client, method.lower())(path)
    assert resp.status_code == 403, (
        f"Expected 403, got {resp.status_code} for {method} {path}"
    )


def _check_allowed(client: TestClient, method: str, path: str) -> None:
    resp = getattr(client, method.lower())(path)
    assert resp.status_code != 403, (
        f"Expected non-403, got {resp.status_code} for {method} {path} "
        "(RBAC blocking a permitted role)"
    )


# ---------------------------------------------------------------------------
# GET /api/audit
# ---------------------------------------------------------------------------


class TestListAuditEventsRBAC:
    _path = "/api/audit"

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "GET", self._path)

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "GET", self._path)

    def test_researcher_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _RESEARCHER), "GET", self._path)

    def test_admin_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _ADMIN), "GET", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "GET", self._path)

    def test_no_auth_allowed(self, tmp_path):
        # Single-operator mode: absent identity → allow unconditionally.
        _check_allowed(_make_client(tmp_path, None), "GET", self._path)


# ---------------------------------------------------------------------------
# GET /api/audit/health
# ---------------------------------------------------------------------------


class TestAuditHealthRBAC:
    _path = "/api/audit/health"

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "GET", self._path)

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "GET", self._path)

    def test_researcher_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _RESEARCHER), "GET", self._path)

    def test_admin_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _ADMIN), "GET", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "GET", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "GET", self._path)


# ---------------------------------------------------------------------------
# GET /api/audit/{audit_event_id}
# ---------------------------------------------------------------------------


class TestGetAuditEventRBAC:
    _path = f"/api/audit/{_EVT}"

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "GET", self._path)

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "GET", self._path)

    def test_researcher_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _RESEARCHER), "GET", self._path)

    def test_admin_allowed(self, tmp_path):
        # Will 404 from service layer (no such audit event) — not 403.
        _check_allowed(_make_client(tmp_path, _ADMIN), "GET", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "GET", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "GET", self._path)


# ---------------------------------------------------------------------------
# DI-1 full-surface audit (Phase 4 ACT-401): cross-tenant scoping at the
# router layer, end-to-end. RBAC-006's owner/admin gate above only checks
# role membership (workspace-scoped, see AuthIdentity docstring) — it does
# NOT itself prevent an owner of ws1 from reading ws2's audit trail. This
# closes that gap: once isolation enforcement is active, an owner/admin can
# only ever see their own workspace's events via these two routes.
# ---------------------------------------------------------------------------

_OWNER_WS1 = AuthIdentity("owner1", "ws1", ("owner",))
_OWNER_WS2 = AuthIdentity("owner2", "ws2", ("owner",))


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


class TestAuditCrossTenantScoping:
    def test_list_events_hides_other_workspace_once_enforcing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _make_client(tmp_path, _OWNER_WS1)
        paths = client.app.dependency_overrides[get_paths]()
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="catalog_mutation",
                action="import_run",
                target_ref="run_ws1",
                actor_workspace_id="ws1",
            ),
        )
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="catalog_mutation",
                action="import_run",
                target_ref="run_ws2",
                actor_workspace_id="ws2",
            ),
        )

        _force_isolation_active(monkeypatch)

        # Even explicitly asking for ws2's events, an owner of ws1 gets ws1's.
        resp = client.get("/api/audit", params={"workspace": "ws2"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["actor_workspace_id"] == "ws1" for item in items)
        assert any(item["target_ref"] == "run_ws1" for item in items)
        assert not any(item["target_ref"] == "run_ws2" for item in items)

    def test_get_event_404s_for_other_workspace_once_enforcing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _make_client(tmp_path, _OWNER_WS1)
        paths = client.app.dependency_overrides[get_paths]()
        event_id = audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="catalog_mutation",
                action="import_run",
                target_ref="run_ws2",
                actor_workspace_id="ws2",
            ),
        )
        assert event_id is not None

        _force_isolation_active(monkeypatch)

        resp = client.get(f"/api/audit/{event_id}")
        assert resp.status_code == 404
