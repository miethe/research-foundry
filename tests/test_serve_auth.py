"""Tests for RF loopback API auth and IP-allowlist middleware (TEST-007, TEST-009).

Coverage:
  TEST-007  Token auth: valid Bearer→200; missing header→401; invalid token→401;
            /health always→200 (exercises hmac.compare_digest path).
  TEST-009  IP allowlist: non-empty allowlist → unlisted IP 403; listed IP 200.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_config(
    tmp_path: Path,
    *,
    auth_mode: str = "none",
    allowlist: list[str] | None = None,
) -> FoundryConfig:
    """Build a minimal FoundryConfig in a temp directory."""
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
    (root / "runs").mkdir(exist_ok=True)

    # Write viewer settings into foundry.yaml so auth middleware config is
    # picked up correctly from disk (mirrors _make_config in test_serve_api.py).
    foundry_yaml_path = root / "foundry.yaml"
    existing: dict = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict = {"auth_mode": auth_mode}
    if allowlist is not None:
        viewer["allowlist"] = allowlist
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    paths = FoundryPaths(root=root)
    cfg = FoundryConfig(paths=paths)
    return cfg


# ---------------------------------------------------------------------------
# TEST-007  Bearer-token auth
# ---------------------------------------------------------------------------


class TestTokenAuth:
    """Token auth exercising the hmac.compare_digest path (TEST-007)."""

    _TOKEN = "super-secret-test-token"
    _ENV_VAR = "RF_SERVE_TOKEN"

    @pytest.fixture()
    def token_client(self, tmp_path, monkeypatch):
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(tmp_path, auth_mode="token")
        fastapi_app = create_app(cfg)
        from research_foundry.api.routers.runs import get_paths
        fastapi_app.dependency_overrides[get_paths] = lambda: cfg.paths
        return TestClient(fastapi_app, raise_server_exceptions=True)

    def test_valid_bearer_returns_200(self, token_client):
        """Correct Bearer token → 200 on a protected endpoint."""
        resp = token_client.get(
            "/api/runs",
            headers={"Authorization": f"Bearer {self._TOKEN}"},
        )
        assert resp.status_code == 200

    def test_missing_header_returns_401(self, token_client):
        """No Authorization header → 401."""
        resp = token_client.get("/api/runs")
        assert resp.status_code == 401
        body = resp.json()
        assert "detail" in body

    def test_wrong_bearer_token_returns_401(self, token_client):
        """Wrong token value → 401 (exercises hmac.compare_digest mismatch)."""
        resp = token_client.get(
            "/api/runs",
            headers={"Authorization": "Bearer wrong-token-value"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert "detail" in body

    def test_empty_bearer_returns_401(self, token_client):
        """Authorization: Bearer  (empty after 'Bearer ') → 401."""
        resp = token_client.get(
            "/api/runs",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_health_exempt_from_auth_no_token(self, token_client):
        """GET /health always 200, even without Authorization header."""
        resp = token_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_exempt_from_auth_wrong_token(self, token_client):
        """GET /health always 200, even with a wrong token."""
        resp = token_client.get(
            "/health",
            headers={"Authorization": "Bearer definitely-wrong"},
        )
        assert resp.status_code == 200

    def test_token_env_unset_at_request_time_returns_401(self, tmp_path, monkeypatch):
        """When the token env var disappears at request time, fail closed (401)."""
        # Set the env var at app-creation time, then remove it before the request.
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(tmp_path, auth_mode="token")
        app = create_app(cfg)
        client = TestClient(app, raise_server_exceptions=True)

        # Unset the var before making the request.
        monkeypatch.delenv(self._ENV_VAR, raising=False)
        resp = client.get(
            "/api/runs",
            headers={"Authorization": f"Bearer {self._TOKEN}"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TEST-009  IP allowlist
# ---------------------------------------------------------------------------


class TestIPAllowlist:
    """IP allowlist middleware (TEST-009)."""

    @pytest.fixture()
    def allowlist_client(self, tmp_path):
        """App with allowlist=["testclient"] — TestClient's ASGI peer host."""
        # fastapi.testclient.TestClient sets client.host to "testclient" in the
        # ASGI scope (not "127.0.0.1"); match that value in the allowlist.
        cfg = _minimal_config(tmp_path, auth_mode="none", allowlist=["testclient"])
        app = create_app(cfg)
        from research_foundry.api.routers.runs import get_paths
        app.dependency_overrides[get_paths] = lambda: cfg.paths
        return TestClient(app, raise_server_exceptions=True)

    @pytest.fixture()
    def unlisted_client(self, tmp_path):
        """App that allows only 10.0.0.99; TestClient's host "testclient" is unlisted."""
        cfg = _minimal_config(tmp_path, auth_mode="none", allowlist=["10.0.0.99"])
        app = create_app(cfg)
        from research_foundry.api.routers.runs import get_paths
        app.dependency_overrides[get_paths] = lambda: cfg.paths
        return TestClient(app, raise_server_exceptions=True)

    def test_listed_ip_gets_200(self, allowlist_client):
        """TestClient host is in the allowlist → 200."""
        resp = allowlist_client.get("/api/runs")
        assert resp.status_code == 200

    def test_unlisted_ip_gets_403(self, unlisted_client):
        """TestClient host is NOT in [10.0.0.99] → 403."""
        resp = unlisted_client.get("/api/runs")
        assert resp.status_code == 403
        body = resp.json()
        assert "detail" in body

    def test_health_blocked_by_allowlist(self, unlisted_client):
        """The allowlist middleware applies to /health too (unlike the auth exemption)."""
        # NOTE: The allowlist middleware does not exempt /health — only the
        # TokenAuthMiddleware has that exemption.  Any request from an unlisted
        # IP should be 403.
        resp = unlisted_client.get("/health")
        assert resp.status_code == 403

    def test_empty_allowlist_allows_all(self, tmp_path):
        """No allowlist (empty list) → all IPs pass through."""
        cfg = _minimal_config(tmp_path, auth_mode="none", allowlist=[])
        app = create_app(cfg)
        from research_foundry.api.routers.runs import get_paths
        app.dependency_overrides[get_paths] = lambda: cfg.paths
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/runs")
        assert resp.status_code == 200
