"""Mandatory 5-scenario test suite for the RBAC enforcement toggle (P5.6 T5).

Tests the ``auth.rbac_enforcement`` config option (auto / disabled / enabled)
end-to-end: config resolution, ``create_app`` startup gate, and
``require_role`` passthrough / enforcement behaviour.

Mandatory scenarios (all 5 must be present):
  (a) provider=none + rbac_enforcement=auto     → mutation route ALLOWED (passthrough)
  (b) provider=local_static + rbac_enforcement=auto → enforced (403 for wrong role)
  (c) rbac_enforcement=disabled + loopback bind → ALLOWED (startup succeeds)
  (d) rbac_enforcement=disabled + non-loopback  → startup REFUSED (raises)
  (e) rbac_enforcement=enabled + provider=none  → enforced (403 for wrong role)
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
from research_foundry.cli_commands import _validate_nonloopback_bind
from research_foundry.config import AuthRbacEnforcement, FoundryConfig, _is_loopback
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    tmp_path: Path,
    *,
    provider: str = "none",
    rbac_enforcement: str = "auto",
    bind_host: str = "127.0.0.1",
) -> FoundryConfig:
    """Create a temporary workspace with the given auth settings."""
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

    # viewer block
    viewer: dict[str, Any] = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    viewer["bind_host"] = bind_host
    existing["foundry"]["viewer"] = viewer

    # auth block
    auth: dict[str, Any] = dict(existing["foundry"].get("auth") or {})
    auth["provider"] = provider
    auth["rbac_enforcement"] = rbac_enforcement
    existing["foundry"]["auth"] = auth

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
        return await call_next(request)


def _make_app(config: FoundryConfig, identity: AuthIdentity | None = None) -> TestClient:
    """Create a TestClient wired with *config* and optional injected identity."""
    from research_foundry.api.routers.runs import get_paths

    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: config.paths
    if identity is not None:
        # Add identity-inject middleware after create_app so it runs as the
        # outermost wrapper (last-added = outermost in Starlette).
        app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


# Viewer-role identity (has no admin/owner permissions → triggers 403 when
# RBAC is enforced and a route requires owner/admin).
_VIEWER_IDENTITY = AuthIdentity("test_viewer", "default", ("viewer",))
_OWNER_IDENTITY = AuthIdentity("test_owner", "default", ("owner",))


# ---------------------------------------------------------------------------
# Unit tests for config-level helpers
# ---------------------------------------------------------------------------


class TestIsLoopback:
    def test_127_0_0_1_is_loopback(self):
        assert _is_loopback("127.0.0.1") is True

    def test_127_prefix_is_loopback(self):
        assert _is_loopback("127.0.0.2") is True

    def test_ipv6_loopback(self):
        assert _is_loopback("::1") is True

    def test_localhost_is_loopback(self):
        assert _is_loopback("localhost") is True

    def test_0_0_0_0_not_loopback(self):
        assert _is_loopback("0.0.0.0") is False

    def test_lan_ip_not_loopback(self):
        assert _is_loopback("10.42.10.76") is False


class TestResolveRbacEnforced:
    """Unit tests for FoundryConfig.resolve_rbac_enforced()."""

    def test_auto_none_provider_is_true(self, tmp_path):
        """AUTO always returns True; identity-None path in require_role handles passthrough."""
        cfg = _make_config(tmp_path, provider="none", rbac_enforcement="auto")
        assert cfg.resolve_rbac_enforced("none", "127.0.0.1") is True

    def test_auto_local_static_is_true(self, tmp_path):
        """Scenario (b) config-level assertion: local_static + auto → True."""
        cfg = _make_config(tmp_path, provider="none", rbac_enforcement="auto")
        assert cfg.resolve_rbac_enforced("local_static", "127.0.0.1") is True

    def test_enabled_is_always_true(self, tmp_path):
        cfg = _make_config(tmp_path, rbac_enforcement="enabled")
        assert cfg.resolve_rbac_enforced("none", "127.0.0.1") is True

    def test_disabled_loopback_is_false(self, tmp_path):
        cfg = _make_config(tmp_path, rbac_enforcement="disabled", bind_host="127.0.0.1")
        assert cfg.resolve_rbac_enforced("none", "127.0.0.1") is False

    def test_disabled_nonloopback_raises(self, tmp_path):
        """Scenario (d) config-level assertion: disabled + 0.0.0.0 → raises."""
        cfg = _make_config(tmp_path, rbac_enforcement="disabled", bind_host="0.0.0.0")
        with pytest.raises(ValueError, match="non-loopback"):
            cfg.resolve_rbac_enforced("none", "0.0.0.0")


# ---------------------------------------------------------------------------
# Scenario (a): provider=none + rbac_enforcement=auto → ALLOWED
# ---------------------------------------------------------------------------


class TestScenarioA_AutoNonePassthrough:
    """(a) provider=none + rbac_enforcement=auto → mutation route ALLOWED."""

    def test_mutation_route_not_403_when_no_identity(self, tmp_path):
        """With provider=none + auto, no identity is set → require_role allows via identity-None path."""
        config = _make_config(tmp_path, provider="none", rbac_enforcement="auto")
        # rbac_enforced=True but no auth middleware → identity stays None → allow
        assert config.resolve_rbac_enforced("none", "127.0.0.1") is True

        # No identity injection — auth disabled, require_role sees identity=None → allow
        client = _make_app(config, identity=None)
        # GET /api/audit requires owner/admin; identity=None → single-operator-trust → not 403
        response = client.get("/api/audit")
        assert response.status_code != 403, (
            f"Expected no RBAC block (auto+none, no identity → passthrough), got {response.status_code}"
        )

    def test_app_state_rbac_enforced_is_true(self, tmp_path):
        """AUTO sets rbac_enforced=True; passthrough comes from identity-None path."""
        config = _make_config(tmp_path, provider="none", rbac_enforcement="auto")
        app = create_app(config)
        assert app.state.rbac_enforced is True


# ---------------------------------------------------------------------------
# Scenario (b): provider=local_static + rbac_enforcement=auto → ENFORCED
# ---------------------------------------------------------------------------


class TestScenarioB_AutoLocalStaticEnforced:
    """(b) provider=local_static + rbac_enforcement=auto → enforced (403 wrong role).

    We test the enforcement behaviour by verifying:
    1. resolve_rbac_enforced("local_static", ...) returns True (config level).
    2. An app with rbac_enforced=True blocks a viewer-role identity on an
       owner/admin-gated route with 403 (integration level).

    For (2), we use rbac_enforcement=enabled+provider=none to produce
    rbac_enforced=True without needing a real token-configured provider (which
    would reject test requests at the auth middleware layer).  The RBAC logic
    under test is identical: require_role sees rbac_enforced=True and checks
    identity.roles.
    """

    def test_resolve_local_static_auto_returns_true(self, tmp_path):
        cfg = _make_config(tmp_path, provider="none", rbac_enforcement="auto")
        # Simulate what create_app does for a local_static deployment.
        result = cfg.resolve_rbac_enforced("local_static", "127.0.0.1")
        assert result is True

    def test_viewer_role_gets_403_when_rbac_enforced(self, tmp_path):
        # Use enabled+none to set rbac_enforced=True without real auth middleware.
        config = _make_config(tmp_path, provider="none", rbac_enforcement="enabled")
        client = _make_app(config, identity=_VIEWER_IDENTITY)
        # GET /api/audit requires owner/admin → viewer identity → 403
        response = client.get("/api/audit")
        assert response.status_code == 403, (
            f"Expected 403 (viewer role blocked), got {response.status_code}"
        )

    def test_owner_role_not_403_when_rbac_enforced(self, tmp_path):
        config = _make_config(tmp_path, provider="none", rbac_enforcement="enabled")
        client = _make_app(config, identity=_OWNER_IDENTITY)
        response = client.get("/api/audit")
        assert response.status_code != 403


# ---------------------------------------------------------------------------
# Scenario (c): rbac_enforcement=disabled + loopback → ALLOWED
# ---------------------------------------------------------------------------


class TestScenarioC_DisabledLoopbackAllowed:
    """(c) rbac_enforcement=disabled + loopback bind → startup succeeds, passthrough."""

    def test_startup_succeeds_on_loopback(self, tmp_path):
        """create_app must NOT raise when disabled+loopback."""
        config = _make_config(
            tmp_path,
            provider="none",
            rbac_enforcement="disabled",
            bind_host="127.0.0.1",
        )
        # Should not raise
        app = create_app(config)
        assert app.state.rbac_enforced is False

    def test_wrong_role_still_allowed_when_disabled(self, tmp_path):
        """Even with a viewer identity, routes pass through when RBAC is disabled."""
        config = _make_config(
            tmp_path,
            provider="none",
            rbac_enforcement="disabled",
            bind_host="127.0.0.1",
        )
        client = _make_app(config, identity=_VIEWER_IDENTITY)
        response = client.get("/api/audit")
        assert response.status_code != 403, (
            f"RBAC=disabled should passthrough all roles, got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# Scenario (d): rbac_enforcement=disabled + non-loopback → STARTUP REFUSED
# ---------------------------------------------------------------------------


class TestScenarioD_DisabledNonLoopbackRefused:
    """(d) rbac_enforcement=disabled + non-loopback bind → startup REFUSED (raises).

    CRITICAL SECURITY TEST: A mis-configured server that tries to disable RBAC
    on a public bind must be refused at startup, not silently allowed through.
    """

    def test_create_app_raises_on_public_bind(self, tmp_path):
        config = _make_config(
            tmp_path,
            provider="none",
            rbac_enforcement="disabled",
            bind_host="0.0.0.0",
        )
        with pytest.raises((ValueError, RuntimeError), match="non-loopback|public bind|cannot be disabled"):
            create_app(config)

    def test_lan_ip_also_refused(self, tmp_path):
        """LAN-routable IP is not loopback — must also be refused."""
        config = _make_config(
            tmp_path,
            provider="none",
            rbac_enforcement="disabled",
            bind_host="10.42.10.76",
        )
        with pytest.raises((ValueError, RuntimeError)):
            create_app(config)


# ---------------------------------------------------------------------------
# Scenario (e): rbac_enforcement=enabled + provider=none → ENFORCED
# ---------------------------------------------------------------------------


class TestScenarioE_EnabledNoneEnforced:
    """(e) rbac_enforcement=enabled + provider=none → enforced (403 for wrong role)."""

    def test_viewer_gets_403_when_enforcement_enabled(self, tmp_path):
        """Even with provider=none, rbac_enforcement=enabled causes 403 for wrong role."""
        config = _make_config(tmp_path, provider="none", rbac_enforcement="enabled")
        assert config.resolve_rbac_enforced("none", "127.0.0.1") is True

        client = _make_app(config, identity=_VIEWER_IDENTITY)
        response = client.get("/api/audit")
        assert response.status_code == 403, (
            f"Expected 403 (rbac_enforcement=enabled blocks viewer), "
            f"got {response.status_code}"
        )

    def test_no_identity_still_allowed_when_enabled(self, tmp_path):
        """When rbac_enforcement=enabled but no identity is set (provider=none),
        the existing identity-None passthrough still applies.
        require_role: rbac_enforced=True → check identity → identity is None → allow.
        """
        config = _make_config(tmp_path, provider="none", rbac_enforcement="enabled")
        # No identity injection — provider=none, no auth middleware
        client = _make_app(config, identity=None)
        response = client.get("/api/audit")
        # No identity → require_role passes (single-operator-trust mode)
        assert response.status_code != 403

    def test_app_state_rbac_enforced_is_true(self, tmp_path):
        config = _make_config(tmp_path, provider="none", rbac_enforcement="enabled")
        app = create_app(config)
        assert app.state.rbac_enforced is True


# ---------------------------------------------------------------------------
# auth.provider=none + non-loopback bind → REFUSED by CLI pre-bind gate
# ---------------------------------------------------------------------------


class TestAuthNoneNonLoopbackCLIGate:
    """Invariant: auth.provider=none + non-loopback bind must be refused.

    This gate lives in cli_commands._validate_nonloopback_bind (NOT in
    create_app).  create_app carries an auditable cross-reference comment
    pointing here.  These tests verify the gate is enforced at the CLI layer
    so that no code path can silently bypass the check.
    """

    def test_provider_none_nonloopback_raises(self, tmp_path):
        """auth.provider=none + bind 0.0.0.0 → _validate_nonloopback_bind raises."""
        config = _make_config(tmp_path, provider="none")
        with pytest.raises(ValueError, match="no auth is configured|Cannot bind"):
            _validate_nonloopback_bind(
                config,
                effective_bind_host="0.0.0.0",
                effective_auth_mode="none",
                env={},
            )

    def test_provider_none_lan_ip_raises(self, tmp_path):
        """auth.provider=none + LAN-routable IP → refused (LAN is not loopback)."""
        config = _make_config(tmp_path, provider="none")
        with pytest.raises(ValueError):
            _validate_nonloopback_bind(
                config,
                effective_bind_host="10.42.10.76",
                effective_auth_mode="none",
                env={},
            )

    def test_provider_none_loopback_not_called(self, tmp_path):
        """The CLI gate is only invoked for non-loopback binds.

        create_app is called for loopback binds without the pre-bind gate;
        verify that provider=none + loopback succeeds end-to-end (no raise
        from create_app or config resolution).
        """
        config = _make_config(tmp_path, provider="none", bind_host="127.0.0.1")
        # create_app must not raise for the normal loopback case
        app = create_app(config)
        assert app is not None

    def test_provider_local_static_nonloopback_with_token_allowed(self, tmp_path):
        """auth.provider=local_static + non-loopback + token env set → gate passes."""
        config = _make_config(tmp_path, provider="none")
        # Simulate a local_static config by patching is_auth_enabled result
        # indirectly: write local_static provider with a token into foundry.yaml
        foundry_path = config.paths.foundry_yaml
        existing = load_yaml(foundry_path) or {}
        existing.setdefault("foundry", {})["auth"] = {
            "provider": "local_static",
            "rbac_enforcement": "auto",
            "local_static": {
                "tokens": [
                    {
                        "token_env": "RF_SERVE_TOKEN",
                        "user_id": "test",
                        "workspace_id": "default",
                        "roles": ["owner"],
                    }
                ]
            },
        }
        dump_yaml(existing, foundry_path)
        config2 = FoundryConfig(paths=config.paths)
        # Gate must pass when the token env var is set
        _validate_nonloopback_bind(
            config2,
            effective_bind_host="0.0.0.0",
            effective_auth_mode="none",
            env={"RF_SERVE_TOKEN": "secret-token-value"},
        )
