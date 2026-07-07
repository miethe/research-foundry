"""RBAC enforcement tests for reports.py mutation routes (RBAC-004).

Verifies that:
  - Under-privileged roles receive 403 on every mutation route.
  - Permitted roles are not blocked by RBAC (may receive other error codes
    from the service layer — 404/422 — but never 403).
  - The no-auth / single-operator-trust mode always allows.

Report mutation routes under test (14 total):
  POST   /api/reports                                   (report:create)
  DELETE /api/reports/{report_id}                       (owner/admin only)
  POST   /api/reports/{report_id}/versions              (report:update)
  POST   /api/reports/{report_id}/versions/{vid}/restore (report:update)
  POST   /api/reports/{report_id}/blocks                (report:update)
  PATCH  /api/reports/{report_id}/blocks/reorder        (report:update)
  PATCH  /api/reports/{report_id}/blocks/{block_id}     (report:update)
  DELETE /api/reports/{report_id}/blocks/{block_id}     (report:update)
  POST   /api/reports/{report_id}/claim-links           (report:update)
  DELETE /api/reports/{report_id}/claim-links/{id}      (report:update)
  POST   /api/reports/{report_id}/source-links          (report:update)
  DELETE /api/reports/{report_id}/source-links/{id}     (report:update)
  POST   /api/reports/{report_id}/verify                (report:update)
  POST   /api/reports/{report_id}/publish-preview       (report:publish → owner/admin)
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
# Fixtures & helpers
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


# Denied identities (no report mutation permissions)
_REVIEWER = AuthIdentity("reviewer", "ws1", ("reviewer",))
_VIEWER = AuthIdentity("viewer", "ws1", ("viewer",))
# researcher is denied for admin-only routes (delete draft, publish-preview)
_RESEARCHER = AuthIdentity("researcher", "ws1", ("researcher",))
# Allowed for all routes
_OWNER = AuthIdentity("owner", "ws1", ("owner",))
_ADMIN = AuthIdentity("admin", "ws1", ("admin",))

# Placeholder IDs (will 404 in service, which is the right outcome — we just confirm no 403)
_RPT = "rpt_test_draft_000"
_BLK = "blk_testblock000"
_VID = "rptv_testversion00"
_CL = "rl_testclaimlink0"
_SL = "sl_testsourcelink"


# ---------------------------------------------------------------------------
# Parametrised helper: check 403 for under-privileged roles and non-403 for permitted
# ---------------------------------------------------------------------------


def _request(client: TestClient, method: str, path: str, json: Any = None) -> Any:
    """Dispatch HTTP request; skip json kwarg for DELETE (not supported by httpx)."""
    fn = getattr(client, method.lower())
    if json is not None and method.upper() not in ("DELETE",):
        return fn(path, json=json)
    return fn(path)


def _check_forbidden(client: TestClient, method: str, path: str, json: Any = None) -> None:
    resp = _request(client, method, path, json)
    assert resp.status_code == 403, (
        f"Expected 403, got {resp.status_code} for {method} {path}"
    )


def _check_allowed(client: TestClient, method: str, path: str, json: Any = None) -> None:
    resp = _request(client, method, path, json)
    assert resp.status_code != 403, (
        f"Expected non-403, got {resp.status_code} for {method} {path} (RBAC blocking a permitted role)"
    )


# ---------------------------------------------------------------------------
# POST /api/reports  (report:create → owner, admin, researcher)
# ---------------------------------------------------------------------------


class TestCreateReportRBAC:
    _path = "/api/reports"
    _body = {"title": "Test", "origin": "blank"}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path, self._body)


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}  (owner/admin only)
# ---------------------------------------------------------------------------


class TestDeleteReportRBAC:
    _path = f"/api/reports/{_RPT}"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "DELETE", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "DELETE", self._path)

    def test_researcher_403(self, tmp_path):
        # researcher is NOT allowed to delete a draft (admin/owner only gate)
        _check_forbidden(_make_client(tmp_path, _RESEARCHER), "DELETE", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "DELETE", self._path)

    def test_admin_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _ADMIN), "DELETE", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "DELETE", self._path)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/versions  (report:update)
# ---------------------------------------------------------------------------


class TestCreateVersionRBAC:
    _path = f"/api/reports/{_RPT}/versions"
    _body: dict = {}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path, self._body)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/versions/{vid}/restore  (report:update)
# ---------------------------------------------------------------------------


class TestRestoreVersionRBAC:
    _path = f"/api/reports/{_RPT}/versions/{_VID}/restore"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/blocks  (report:update)
# ---------------------------------------------------------------------------


class TestAddBlockRBAC:
    _path = f"/api/reports/{_RPT}/blocks"
    _body = {"block_type": "paragraph", "markdown": "hello"}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path, self._body)


# ---------------------------------------------------------------------------
# PATCH /api/reports/{report_id}/blocks/reorder  (report:update)
# ---------------------------------------------------------------------------


class TestReorderBlocksRBAC:
    _path = f"/api/reports/{_RPT}/blocks/reorder"
    _body = {"block_ids": []}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "PATCH", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "PATCH", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "PATCH", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "PATCH", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "PATCH", self._path, self._body)


# ---------------------------------------------------------------------------
# PATCH /api/reports/{report_id}/blocks/{block_id}  (report:update)
# ---------------------------------------------------------------------------


class TestUpdateBlockRBAC:
    _path = f"/api/reports/{_RPT}/blocks/{_BLK}"
    _body = {"markdown": "updated"}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "PATCH", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "PATCH", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "PATCH", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "PATCH", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "PATCH", self._path, self._body)


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}/blocks/{block_id}  (report:update)
# ---------------------------------------------------------------------------


class TestDeleteBlockRBAC:
    _path = f"/api/reports/{_RPT}/blocks/{_BLK}"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "DELETE", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "DELETE", self._path)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "DELETE", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "DELETE", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "DELETE", self._path)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/claim-links  (report:update)
# ---------------------------------------------------------------------------


class TestAddClaimLinkRBAC:
    _path = f"/api/reports/{_RPT}/claim-links"
    _body = {"block_id": _BLK, "claim_id": "clm_test001"}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path, self._body)


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}/claim-links/{claim_link_id}  (report:update)
# ---------------------------------------------------------------------------


class TestRemoveClaimLinkRBAC:
    _path = f"/api/reports/{_RPT}/claim-links/{_CL}"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "DELETE", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "DELETE", self._path)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "DELETE", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "DELETE", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "DELETE", self._path)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/source-links  (report:update)
# ---------------------------------------------------------------------------


class TestAddSourceLinkRBAC:
    _path = f"/api/reports/{_RPT}/source-links"
    _body = {"source_card_id": "sc_test0001"}

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path, self._body)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path, self._body)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path, self._body)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path, self._body)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path, self._body)


# ---------------------------------------------------------------------------
# DELETE /api/reports/{report_id}/source-links/{source_link_id}  (report:update)
# ---------------------------------------------------------------------------


class TestRemoveSourceLinkRBAC:
    _path = f"/api/reports/{_RPT}/source-links/{_SL}"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "DELETE", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "DELETE", self._path)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "DELETE", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "DELETE", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "DELETE", self._path)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/verify  (report:update → owner/admin/researcher)
# ---------------------------------------------------------------------------


class TestVerifyDraftRBAC:
    _path = f"/api/reports/{_RPT}/verify"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path)

    def test_researcher_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _RESEARCHER), "POST", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path)


# ---------------------------------------------------------------------------
# POST /api/reports/{report_id}/publish-preview  (report:publish → owner/admin only)
# ---------------------------------------------------------------------------


class TestPublishPreviewRBAC:
    _path = f"/api/reports/{_RPT}/publish-preview"

    def test_reviewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _REVIEWER), "POST", self._path)

    def test_viewer_403(self, tmp_path):
        _check_forbidden(_make_client(tmp_path, _VIEWER), "POST", self._path)

    def test_researcher_403(self, tmp_path):
        # researcher cannot publish — this gate is owner/admin only
        _check_forbidden(_make_client(tmp_path, _RESEARCHER), "POST", self._path)

    def test_owner_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _OWNER), "POST", self._path)

    def test_admin_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, _ADMIN), "POST", self._path)

    def test_no_auth_allowed(self, tmp_path):
        _check_allowed(_make_client(tmp_path, None), "POST", self._path)
