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
from starlette.requests import Request as StarletteRequest

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
    auth_token_env: str | None = None,
    allowlist: list[str] | None = None,
    auth_block: dict | None = None,
) -> FoundryConfig:
    """Build a minimal FoundryConfig in a temp directory.

    Args:
        auth_mode: Legacy ``viewer.auth_mode`` value (kept for IP-allowlist tests
            that still exercise the viewer block).
        auth_token_env: Legacy ``viewer.auth_token_env`` value.  When supplied,
            written into the ``viewer`` block alongside ``auth_mode``.  Used to
            exercise the fail-closed legacy-fallback path in ``create_app``.
        allowlist: Optional IP allowlist for ``viewer.allowlist``.
        auth_block: New-style ``auth:`` block written verbatim under
            ``foundry.auth`` in ``foundry.yaml``. When provided, ``create_app``
            will use ``auth.provider`` for the new registry-based auth path.
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
    (root / "runs").mkdir(exist_ok=True)

    # Write viewer settings into foundry.yaml so auth middleware config is
    # picked up correctly from disk (mirrors _make_config in test_serve_api.py).
    foundry_yaml_path = root / "foundry.yaml"
    existing: dict = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict = {"auth_mode": auth_mode}
    if auth_token_env is not None:
        viewer["auth_token_env"] = auth_token_env
    if allowlist is not None:
        viewer["allowlist"] = allowlist
    existing["foundry"]["viewer"] = viewer
    if auth_block is not None:
        existing["foundry"]["auth"] = auth_block
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
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "test_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )
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
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "test_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )
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


# ---------------------------------------------------------------------------
# AUTH-900  Absent identity when auth.provider = "none"
# ---------------------------------------------------------------------------


class TestNoAuthProviderAbsentIdentity:
    """AUTH-900: With auth.provider=none (default), request.state never gains 'identity'.

    Asserts the absent-identity contract documented in api/auth/provider.py:
    when no auth middleware is active, ``request.state`` never receives an
    ``identity`` attribute.  Consumers MUST use
    ``getattr(request.state, 'identity', None)`` to safely detect the
    no-auth case.
    """

    def test_no_auth_provider_absent_identity(self, tmp_path):
        """auth.provider absent/none → getattr(request.state, 'identity', None) is None.

        Creates an app where ``auth.provider`` is absent from foundry.yaml
        (defaults to ``'none'``), attaches a lightweight probe route that
        reads ``request.state.identity``, and asserts the JSON response body
        carries ``null`` — not an AuthIdentity with placeholder defaults.
        """
        cfg = _minimal_config(tmp_path, auth_mode="none")
        app = create_app(cfg)

        # Probe route: serialises request.state.identity into the response
        # body so the assertion lives entirely at the HTTP layer.
        @app.get("/_test/identity-probe")
        def _identity_probe(request: StarletteRequest) -> dict:
            return {"identity": getattr(request.state, "identity", None)}

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/_test/identity-probe")
        assert resp.status_code == 200
        body = resp.json()
        assert body["identity"] is None, (
            "Expected request.state to have no 'identity' attribute when "
            f"auth.provider=none, but got: {body['identity']!r}"
        )


# ---------------------------------------------------------------------------
# AUTH-106  Provider-parametrized matrix: none vs local_static
# ---------------------------------------------------------------------------


class TestProviderMatrix:
    """AUTH-106: Provider matrix — none and local_static behaviour.

    Covers the observable surface of both configured providers:
      ``local_static`` — valid / invalid / missing-header token paths
      ``none``         — no AuthProviderMiddleware present in the stack
    """

    _TOKEN = "matrix-secret-token"
    _ENV_VAR = "RF_SERVE_TOKEN"

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture()
    def local_static_client(self, tmp_path, monkeypatch):
        """App configured with local_static provider + identity probe route."""
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "matrix_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )
        app = create_app(cfg)

        # Probe route: serialises AuthIdentity to JSON so assertions stay at the
        # HTTP layer.  StarletteRequest is imported at module scope so that
        # get_type_hints() can resolve the annotation correctly under
        # `from __future__ import annotations`.
        @app.get("/_test/identity-probe")
        def _probe(request: StarletteRequest) -> dict:
            idt = getattr(request.state, "identity", None)
            if idt is None:
                return {"identity": None}
            return {
                "identity": {
                    "user_id": idt.user_id,
                    "workspace_id": idt.workspace_id,
                    "roles": list(idt.roles),
                }
            }

        from research_foundry.api.routers.runs import get_paths
        app.dependency_overrides[get_paths] = lambda: cfg.paths
        return TestClient(app, raise_server_exceptions=True)

    @pytest.fixture()
    def none_provider_app(self, tmp_path):
        """App with auth.provider absent (defaults to 'none')."""
        cfg = _minimal_config(tmp_path)  # no auth_block → auth.provider = "none"
        return create_app(cfg)

    # ------------------------------------------------------------------
    # local_static tests
    # ------------------------------------------------------------------

    def test_local_static_valid_token_returns_200_with_identity(
        self, local_static_client
    ):
        """Valid bearer token → HTTP 200 and request.state.identity is populated."""
        resp = local_static_client.get(
            "/_test/identity-probe",
            headers={"Authorization": f"Bearer {self._TOKEN}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["identity"] is not None, (
            "Expected request.state.identity to be populated for a valid token "
            f"but got: {body['identity']!r}"
        )
        assert body["identity"]["user_id"] == "matrix_user"
        assert body["identity"]["workspace_id"] == "default"
        assert "owner" in body["identity"]["roles"]

    def test_local_static_invalid_token_returns_generic_401(
        self, local_static_client
    ):
        """Invalid bearer token → HTTP 401 with generic body; no provider detail leaked."""
        resp = local_static_client.get(
            "/api/runs",
            headers={"Authorization": "Bearer definitely-wrong-token"},
        )
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Unauthorized"}, (
            "Expected generic {'detail': 'Unauthorized'} but got: "
            f"{resp.json()!r} — provider name or token detail must not leak."
        )

    def test_local_static_missing_header_returns_401(self, local_static_client):
        """Missing Authorization header → HTTP 401."""
        resp = local_static_client.get("/api/runs")
        assert resp.status_code == 401

    # ------------------------------------------------------------------
    # none provider test
    # ------------------------------------------------------------------

    def test_none_provider_no_auth_middleware_in_stack(self, none_provider_app):
        """auth.provider=none → no AuthProviderMiddleware registered in user_middleware."""
        from research_foundry.api.middleware.auth import AuthProviderMiddleware

        auth_middlewares = [
            m
            for m in none_provider_app.user_middleware
            if m.cls is AuthProviderMiddleware
        ]
        assert len(auth_middlewares) == 0, (
            f"Expected no AuthProviderMiddleware in the middleware stack but found "
            f"{len(auth_middlewares)} instance(s).  auth.provider=none must be a "
            "true no-op — zero middleware, not a pass-through."
        )


# ---------------------------------------------------------------------------
# AUTH-106  RBAC store rebuild-survival guard (D2)
# ---------------------------------------------------------------------------


class TestRbacStoreRebuildSurvival:
    """AUTH-106 / D2: rbac.db durability — survives a catalog.db rebuild_schema call.

    This is the regression guard for the D2 gotcha documented in rbac_store.py:
    rbac.db lives under ``.rf_state/`` (durable, authoritative) while catalog.db
    lives under ``.rf_cache/`` (rebuildable).  They must never share a file path.
    A ``catalog_service.rebuild_schema`` call (drop + recreate) must leave all
    RBAC membership data untouched.
    """

    def test_rbac_data_survives_catalog_rebuild(self, tmp_path):
        """Membership inserted into rbac.db is present after catalog.rebuild_schema."""
        from research_foundry.services import catalog_service, rbac_store

        paths = FoundryPaths(root=tmp_path / "workspace")

        # --- D2 regression guard: fail LOUDLY if the two DB files share a path ---
        assert paths.catalog_db != paths.rbac_db, (
            "REGRESSION D2: catalog.db and rbac.db resolve to the same file!  "
            f"catalog_db={paths.catalog_db!r}  rbac_db={paths.rbac_db!r}.  "
            "These databases must be stored separately — rbac.db is durable "
            "authoritative state; catalog.db is a rebuildable cache."
        )

        # --- Setup: bootstrap RBAC store and insert a test membership ---
        conn = rbac_store.bootstrap(paths)
        try:
            rbac_store.upsert_workspace(conn, "ws_test", "Test Workspace")
            rbac_store.upsert_user(conn, "usr_alice", display_name="Alice")
            rbac_store.upsert_membership(conn, "usr_alice", "ws_test", "owner")
        finally:
            conn.close()

        # --- Action: trigger catalog schema drop + recreate ---
        catalog_service.rebuild_schema(paths)

        # --- Assert: RBAC membership is still intact after catalog rebuild ---
        conn2 = rbac_store.bootstrap(paths)
        try:
            rows = conn2.execute("SELECT * FROM memberships").fetchall()
            assert len(rows) == 1, (
                f"Expected exactly 1 membership row after catalog_service.rebuild_schema "
                f"but found {len(rows)}: {[dict(r) for r in rows]}.  "
                "This indicates rbac.db was dropped or truncated by the catalog rebuild — "
                "a durability violation."
            )
            row = rows[0]
            assert row["user_id"] == "usr_alice"
            assert row["workspace_id"] == "ws_test"
            assert row["role"] == "owner"
        finally:
            conn2.close()


# ---------------------------------------------------------------------------
# AUTH-110  Legacy viewer.auth_mode=token backward-compatibility (fail-closed)
# ---------------------------------------------------------------------------


class TestLegacyTokenAuthBackwardCompat:
    """AUTH-110: viewer.auth_mode='token' without a foundry.auth block installs middleware.

    Regression guard for the fail-closed legacy fallback added to ``create_app``:
    when ``foundry.auth`` is absent (so ``auth.provider`` defaults to ``"none"``)
    but ``viewer.auth_mode`` is ``"token"``, ``create_app`` must derive a
    ``LocalStaticAuthProvider`` from the legacy ``viewer.auth_token_env`` value
    and install ``AuthProviderMiddleware`` — NOT silently skip protection.

    This test MUST FAIL on the pre-fix code (no fallback) and PASS after the fix.
    """

    _TOKEN = "legacy-backward-compat-token"
    _ENV_VAR = "RF_SERVE_TOKEN"

    def test_viewer_auth_mode_token_without_new_auth_block_installs_middleware(
        self, tmp_path, monkeypatch
    ):
        """Legacy viewer.auth_mode=token without foundry.auth block → 401/200 correctly.

        Steps:
          1. Build a foundry.yaml with ONLY viewer.auth_mode=token and
             viewer.auth_token_env=RF_SERVE_TOKEN — NO foundry.auth block.
          2. Set the env var RF_SERVE_TOKEN to the test token value.
          3. Create the FastAPI app via create_app.
          4. Assert request WITHOUT bearer token → 401 (middleware installed).
          5. Assert request WITH correct bearer token → 200 (token accepted).
        """
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)

        # Write a config with legacy viewer fields only — no foundry.auth block.
        cfg = _minimal_config(
            tmp_path,
            auth_mode="token",
            auth_token_env=self._ENV_VAR,
            # Intentionally no auth_block= so auth.provider defaults to "none".
        )
        app = create_app(cfg)

        from research_foundry.api.routers.runs import get_paths
        app.dependency_overrides[get_paths] = lambda: cfg.paths

        client = TestClient(app, raise_server_exceptions=True)

        # Without a token the middleware must reject the request.
        resp_no_token = client.get("/api/runs")
        assert resp_no_token.status_code == 401, (
            f"Expected 401 for unauthenticated request (legacy fallback should "
            f"install middleware), but got {resp_no_token.status_code}. "
            "Pre-fix: auth.provider='none' silently skips middleware even when "
            "viewer.auth_mode='token' is set — this is the regression being guarded."
        )

        # With the correct token the middleware must admit the request.
        resp_with_token = client.get(
            "/api/runs",
            headers={"Authorization": f"Bearer {self._TOKEN}"},
        )
        assert resp_with_token.status_code == 200, (
            f"Expected 200 for correctly-authenticated request via legacy token "
            f"fallback, but got {resp_with_token.status_code}."
        )


# ---------------------------------------------------------------------------
# TestServeGateNewProvider (P2-a)
# ---------------------------------------------------------------------------


class TestServeGateNewProvider:
    """P2-a: pre-bind gate accepts the new auth.provider=local_static path.

    Guards the regression where a deployment using ``auth.provider: local_static``
    (the P5 canonical path) would be REJECTED at startup for non-loopback binds
    because the old gate only checked ``viewer.auth_mode == "token"``.
    """

    _ENV_VAR = "RF_SERVE_TOKEN"
    _TOKEN = "gate-test-secret"

    def test_local_static_with_token_env_set_passes_nonloopback_gate(
        self, tmp_path, monkeypatch
    ):
        """auth.provider=local_static + token env var SET → is_auth_enabled True and gate passes."""
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "gate_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )
        # is_auth_enabled must return True for the new auth.provider path.
        assert cfg.is_auth_enabled() is True, (
            "Expected is_auth_enabled()=True for auth.provider=local_static "
            f"but got False. Config auth block: {cfg.auth!r}"
        )

        import os as _os

        from research_foundry.cli_commands import _validate_nonloopback_bind

        # Gate must NOT raise when the token env var is set.
        _validate_nonloopback_bind(cfg, "0.0.0.0", "none", _os.environ)

    def test_local_static_with_token_env_unset_fails_nonloopback_gate(
        self, tmp_path, monkeypatch
    ):
        """auth.provider=local_static + token env var NOT SET → serve gate raises (fail closed)."""
        monkeypatch.delenv(self._ENV_VAR, raising=False)
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "gate_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )
        import os as _os

        from research_foundry.cli_commands import _validate_nonloopback_bind

        with pytest.raises(ValueError, match="no token env vars"):
            _validate_nonloopback_bind(cfg, "0.0.0.0", "none", _os.environ)

    def test_no_auth_provider_blocked_on_nonloopback(self, tmp_path):
        """No auth configured → is_auth_enabled() returns False and gate raises."""
        cfg = _minimal_config(tmp_path)  # No auth block — defaults to "none"

        assert cfg.is_auth_enabled() is False, (
            "Expected is_auth_enabled()=False when no auth is configured "
            f"but got True. Config foundry block: {cfg.foundry!r}"
        )

        from research_foundry.cli_commands import _validate_nonloopback_bind

        with pytest.raises(ValueError, match="no auth is configured"):
            _validate_nonloopback_bind(cfg, "0.0.0.0", "none", {})


# ---------------------------------------------------------------------------
# TestLocalStaticMalformedConfig (P2-b)
# ---------------------------------------------------------------------------


class TestLocalStaticMalformedConfig:
    """P2-b: malformed token entries surface as ValueError at startup (not 500 at request time).

    Guards two layers:
      1. Startup validation in LocalStaticAuthProvider.__init__ — raises ValueError
         before the app serves any requests, so operators see a clear error message.
      2. Match-time defensive guard in authenticate() — returns None instead of
         raising KeyError if a malformed entry somehow reaches the matching step.
    """

    _ENV_VAR = "RF_SERVE_TOKEN"
    _TOKEN = "malformed-guard-token"

    def test_missing_user_id_raises_startup_error(self, monkeypatch):
        """Token entry missing user_id key → ValueError at LocalStaticAuthProvider construction."""
        from research_foundry.api.auth.adapters.local_static import LocalStaticAuthProvider

        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        with pytest.raises(ValueError, match="user_id"):
            LocalStaticAuthProvider(
                token_configs=[
                    {
                        "token_env": self._ENV_VAR,
                        # user_id intentionally absent
                        "workspace_id": "default",
                        "roles": ["owner"],
                    }
                ]
            )

    def test_missing_workspace_id_raises_startup_error(self, monkeypatch):
        """Token entry missing workspace_id key → ValueError at LocalStaticAuthProvider construction."""
        from research_foundry.api.auth.adapters.local_static import LocalStaticAuthProvider

        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        with pytest.raises(ValueError, match="workspace_id"):
            LocalStaticAuthProvider(
                token_configs=[
                    {
                        "token_env": self._ENV_VAR,
                        "user_id": "valid_user",
                        # workspace_id intentionally absent
                        "roles": ["owner"],
                    }
                ]
            )

    def test_malformed_entry_at_match_time_returns_none_not_500(self, monkeypatch):
        """Malformed entry that bypasses __init__ → authenticate() returns None, not KeyError/500."""
        from types import SimpleNamespace

        from research_foundry.api.auth.adapters.local_static import LocalStaticAuthProvider

        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)

        # Construct with a valid entry to pass __init__ validation.
        provider = LocalStaticAuthProvider(
            token_configs=[
                {
                    "token_env": self._ENV_VAR,
                    "user_id": "valid_user",
                    "workspace_id": "default",
                    "roles": ["owner"],
                }
            ]
        )

        # Directly patch _token_configs with a malformed entry (bypasses __init__
        # validation — simulates a dynamically modified or externally supplied config).
        provider._token_configs = [
            {
                "token_env": self._ENV_VAR,
                # Missing user_id and workspace_id — will match the token but is malformed.
                "roles": ["owner"],
            }
        ]

        # Fake request with the valid token value.
        fake_request = SimpleNamespace(
            headers={"Authorization": f"Bearer {self._TOKEN}"}
        )

        # authenticate() must return None (not raise KeyError → 500).
        result = provider.authenticate(fake_request)  # type: ignore[arg-type]
        assert result is None, (
            f"Expected authenticate() to return None for a malformed (matched) entry "
            f"but got {result!r}. KeyError → 500 is still possible — fix incomplete."
        )


# ---------------------------------------------------------------------------
# TestServeOrderingFix — P1 root-cause fix: overrides applied before gate
# ---------------------------------------------------------------------------


class TestServeOrderingFix:
    """P1 ordering fix: CLI overrides must be applied BEFORE the non-loopback gate.

    The gate and create_app must read the SAME already-overridden config object.
    These unit tests assert is_auth_enabled() and _validate_nonloopback_bind()
    outcomes after the correct override ordering — simulating what the fixed
    `rf serve` command does internally.

    Test matrix for --bind-host 0.0.0.0 scenarios (6 cases):
      1. config auth_mode=token, no CLI override             → gate passes
      2. config auth_mode=token, --auth-mode=none APPLIED    → gate FAILS (P1 bypass case)
      3. config no auth, --auth-mode=token APPLIED + env set → gate passes
      4. config auth.provider=local_static, token env set    → gate passes
      5. config auth.provider=local_static, token env unset  → gate FAILS
      6. no auth anywhere, no CLI override                   → gate FAILS
    """

    _ENV_VAR = "RF_SERVE_TOKEN"
    _TOKEN = "ordering-fix-test-token"

    def test_config_auth_mode_token_no_cli_override_passes_gate(
        self, tmp_path, monkeypatch
    ):
        """config viewer.auth_mode=token, no CLI override → is_auth_enabled() True → gate passes."""
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(tmp_path, auth_mode="token", auth_token_env=self._ENV_VAR)

        # No CLI override applied — config read directly from YAML (viewer.auth_mode=token).
        assert cfg.is_auth_enabled() is True, (
            "Expected is_auth_enabled()=True for viewer.auth_mode=token "
            f"but got False. viewer block: {cfg.viewer!r}"
        )

        import os as _os

        from research_foundry.cli_commands import _validate_nonloopback_bind

        # Gate must pass: auth is enabled and token env var is set.
        _validate_nonloopback_bind(cfg, "0.0.0.0", "token", _os.environ)

    def test_config_auth_mode_token_cli_override_none_fails_gate(
        self, tmp_path, monkeypatch
    ):
        """config viewer.auth_mode=token, --auth-mode=none APPLIED before gate → gate FAILS.

        This is the P1 bypass test. Before the fix, the gate was called BEFORE
        the CLI override was applied: gate read pre-override viewer.auth_mode=token
        (passed), then create_app got auth_mode=none (server bound LAN with no auth).

        After the fix, the CLI override is applied first. This test confirms that
        after applying --auth-mode none, is_auth_enabled() returns False and the
        gate correctly refuses to bind.
        """
        monkeypatch.delenv(self._ENV_VAR, raising=False)
        cfg = _minimal_config(tmp_path, auth_mode="token", auth_token_env=self._ENV_VAR)

        # Simulate: CLI --auth-mode none override APPLIED to config BEFORE gate
        # (this is what the fixed serve command now does).
        effective_auth_mode = "none"
        cfg.viewer["auth_mode"] = effective_auth_mode

        # After override, is_auth_enabled() must return False.
        assert cfg.is_auth_enabled() is False, (
            "Expected is_auth_enabled()=False after applying --auth-mode=none override "
            f"but got True. viewer block after mutation: {cfg.viewer!r}"
        )

        from research_foundry.cli_commands import _validate_nonloopback_bind

        # Gate must FAIL — this is the bypass case that the fix prevents.
        with pytest.raises(ValueError, match="no auth is configured"):
            _validate_nonloopback_bind(cfg, "0.0.0.0", effective_auth_mode, {})

    def test_config_none_cli_override_token_passes_gate(
        self, tmp_path, monkeypatch
    ):
        """config no auth, --auth-mode=token CLI APPLIED + token env set → gate passes."""
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(tmp_path, auth_mode="none", auth_token_env=self._ENV_VAR)

        # Simulate: CLI --auth-mode token override APPLIED to config BEFORE gate.
        effective_auth_mode = "token"
        cfg.viewer["auth_mode"] = effective_auth_mode

        # After override, is_auth_enabled() must return True.
        assert cfg.is_auth_enabled() is True, (
            "Expected is_auth_enabled()=True after applying --auth-mode=token override "
            f"but got False. viewer block after mutation: {cfg.viewer!r}"
        )

        import os as _os

        from research_foundry.cli_commands import _validate_nonloopback_bind

        # Gate must pass: auth enabled via CLI override and token env var is set.
        _validate_nonloopback_bind(cfg, "0.0.0.0", effective_auth_mode, _os.environ)

    def test_config_new_provider_local_static_token_set_passes_gate(
        self, tmp_path, monkeypatch
    ):
        """config auth.provider=local_static, token env set → is_auth_enabled() True → gate passes."""
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "gate_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )

        # New canonical path: is_auth_enabled must return True for local_static.
        assert cfg.is_auth_enabled() is True, (
            "Expected is_auth_enabled()=True for auth.provider=local_static "
            f"but got False. auth block: {cfg.auth!r}"
        )

        import os as _os

        from research_foundry.cli_commands import _validate_nonloopback_bind

        # Gate must pass: local_static provider active and token env var is set.
        _validate_nonloopback_bind(cfg, "0.0.0.0", "none", _os.environ)

    def test_config_new_provider_local_static_token_unset_fails_gate(
        self, tmp_path, monkeypatch
    ):
        """config auth.provider=local_static, token env NOT set → _validate_nonloopback_bind raises."""
        monkeypatch.delenv(self._ENV_VAR, raising=False)
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "gate_user",
                            "workspace_id": "default",
                            "roles": ["owner"],
                        }
                    ]
                },
            },
        )

        from research_foundry.cli_commands import _validate_nonloopback_bind

        # Gate must fail: auth provider is configured but no token env var is set.
        with pytest.raises(ValueError, match="no token env vars"):
            _validate_nonloopback_bind(cfg, "0.0.0.0", "none", {})

    def test_no_auth_anywhere_fails_gate(self, tmp_path):
        """config no auth, no CLI override → is_auth_enabled() False → gate fails."""
        cfg = _minimal_config(tmp_path)  # No auth configured at all.

        assert cfg.is_auth_enabled() is False, (
            "Expected is_auth_enabled()=False when no auth is configured "
            f"but got True. foundry block: {cfg.foundry!r}"
        )

        from research_foundry.cli_commands import _validate_nonloopback_bind

        with pytest.raises(ValueError, match="no auth is configured"):
            _validate_nonloopback_bind(cfg, "0.0.0.0", "none", {})
