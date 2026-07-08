"""Unit tests for the admin settings API (P5.6 T2).

Test coverage:
  - Role gating on every route (owner/admin allowed; viewer/contributor/reader → 403)
  - No-secrets assertion: auth-provider-status payload contains no private keys,
    JWKS secrets, or Bearer tokens
  - Rate-limit config round-trip: PATCH updates, GET reflects update
  - Workspace member list and role update endpoints
  - RBAC-status endpoint (accessible by any authenticated user)
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
from research_foundry.api.routers.admin import _get_config
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> FoundryConfig:
    """Minimal workspace config with auth disabled (provider=none)."""
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
        return await call_next(request)


def _make_client(
    tmp_path: Path,
    identity: AuthIdentity | None = None,
    *,
    rbac_enforcement: str = "enabled",
) -> tuple[TestClient, FoundryConfig]:
    """Create a TestClient with admin-API routes wired and optional identity injection.

    Uses ``rbac_enforcement=enabled`` by default so role gating is active
    regardless of auth.provider.  Pass ``rbac_enforcement="auto"`` or ``"disabled"``
    to test passthrough scenarios.
    """
    config = _make_config(tmp_path)

    # Patch foundry.yaml to set rbac_enforcement for the test
    foundry_yaml_path = config.paths.foundry_yaml
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing:
        existing["foundry"] = {}
    auth: dict[str, Any] = dict(existing["foundry"].get("auth") or {})
    auth["rbac_enforcement"] = rbac_enforcement
    existing["foundry"]["auth"] = auth
    dump_yaml(existing, foundry_yaml_path)
    # Reload config after patching
    config = FoundryConfig(paths=FoundryPaths(root=config.paths.root))

    app = create_app(config)
    # Override path/config dependencies to use the test workspace
    app.dependency_overrides[get_paths] = lambda: config.paths
    app.dependency_overrides[_get_config] = lambda: config

    if identity is not None:
        app.add_middleware(_InjectIdentityMiddleware, identity=identity)

    return TestClient(app, raise_server_exceptions=True), config


# Standard identities used across tests
_OWNER = AuthIdentity("u_owner", "default", ("owner",))
_ADMIN = AuthIdentity("u_admin", "default", ("admin",))
_RESEARCHER = AuthIdentity("u_researcher", "default", ("researcher",))
_REVIEWER = AuthIdentity("u_reviewer", "default", ("reviewer",))
_VIEWER = AuthIdentity("u_viewer", "default", ("viewer",))
# Roles that should be blocked on admin endpoints
_BLOCKED_ROLES = [_RESEARCHER, _REVIEWER, _VIEWER]


# ---------------------------------------------------------------------------
# Role gating: GET /api/admin/workspace
# ---------------------------------------------------------------------------


class TestWorkspaceRoleGating:
    """owner and admin are allowed; researcher/reviewer/viewer get 403."""

    def test_owner_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/workspace")
        assert response.status_code != 403

    def test_admin_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_ADMIN)
        response = client.get("/api/admin/workspace")
        assert response.status_code != 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_blocked(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/workspace")
        assert response.status_code == 403

    def test_response_shape_owner(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/workspace")
        data = response.json()
        assert "workspace_id" in data
        assert "members" in data


# ---------------------------------------------------------------------------
# Role gating: PATCH /api/admin/members/{user_id}/role
# ---------------------------------------------------------------------------


class TestUpdateMemberRoleGating:
    def test_owner_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.patch(
            "/api/admin/members/nonexistent_user/role",
            json={"role": "viewer"},
        )
        # 404 (member not found) or 200 — never 403
        assert response.status_code != 403

    def test_admin_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_ADMIN)
        response = client.patch(
            "/api/admin/members/nonexistent_user/role",
            json={"role": "viewer"},
        )
        assert response.status_code != 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_blocked(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.patch(
            "/api/admin/members/some_user/role",
            json={"role": "viewer"},
        )
        assert response.status_code == 403

    def test_missing_role_field_returns_422(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.patch(
            "/api/admin/members/user123/role",
            json={},  # no "role" key
        )
        assert response.status_code == 422

    def test_not_found_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.patch(
            "/api/admin/members/definitely_missing_user/role",
            json={"role": "viewer"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Role gating + no-secrets: GET /api/admin/auth-provider-status
# ---------------------------------------------------------------------------


class TestAuthProviderStatusRoleGating:
    def test_owner_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/auth-provider-status")
        assert response.status_code == 200

    def test_admin_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_ADMIN)
        response = client.get("/api/admin/auth-provider-status")
        assert response.status_code == 200

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_blocked(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/auth-provider-status")
        assert response.status_code == 403


class TestAuthProviderStatusNoSecrets:
    """Security: auth-provider-status must NEVER return credentials or secrets."""

    _SECRET_KEYS = [
        "secret",
        "key",
        "jwks",
        "token",
        "password",
        "private",
        "credential",
        "bearer",
        "api_key",
        "clerk_secret",
    ]

    def test_response_contains_only_safe_fields(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/auth-provider-status")
        assert response.status_code == 200
        data = response.json()
        # Only expected safe keys
        for key in data.keys():
            assert key in {"provider", "available", "details"}, (
                f"Unexpected field {key!r} in auth-provider-status response — "
                "may be leaking sensitive data"
            )

    def test_no_secret_material_in_values(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/auth-provider-status")
        assert response.status_code == 200
        # Stringify the response and check for suspicious keywords
        body_lower = response.text.lower()
        for secret_keyword in self._SECRET_KEYS:
            # Allow "available" field name containing "able" but not "key" in isolation
            # Practical check: the literal env var or JWKS content should not appear.
            # We check that the response text doesn't contain standalone secret_keyword
            # preceded by a quote/colon (JSON key position).
            assert f'"{secret_keyword}"' not in body_lower, (
                f"Response body contains suspicious key {secret_keyword!r}: {response.text}"
            )

    def test_response_shape(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/auth-provider-status")
        data = response.json()
        assert "provider" in data
        assert "available" in data
        assert isinstance(data["available"], bool)


# ---------------------------------------------------------------------------
# Role gating + round-trip: GET/PATCH /api/admin/rate-limit-config
# ---------------------------------------------------------------------------


class TestRateLimitConfigRoleGating:
    def test_owner_can_read(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/rate-limit-config")
        assert response.status_code == 200

    def test_admin_can_read(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_ADMIN)
        response = client.get("/api/admin/rate-limit-config")
        assert response.status_code == 200

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_read(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/rate-limit-config")
        assert response.status_code == 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_patch(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.patch(
            "/api/admin/rate-limit-config",
            json={"max_requests": 30},
        )
        assert response.status_code == 403


class TestRateLimitConfigRoundTrip:
    """PATCH updates are reflected by GET."""

    def test_get_returns_expected_shape(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/rate-limit-config")
        data = response.json()
        assert "enabled" in data
        assert "window_seconds" in data
        assert "max_requests" in data
        assert data["per_identity"] is True
        assert data["per_route"] is True

    def test_patch_max_requests_reflected_by_get(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        # PATCH to update max_requests
        patch_response = client.patch(
            "/api/admin/rate-limit-config",
            json={"max_requests": 42},
        )
        assert patch_response.status_code == 200

        # GET must reflect the update
        get_response = client.get("/api/admin/rate-limit-config")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["max_requests"] == 42

    def test_patch_window_seconds_reflected(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        client.patch("/api/admin/rate-limit-config", json={"window_seconds": 120})
        response = client.get("/api/admin/rate-limit-config")
        assert response.json()["window_seconds"] == 120

    def test_patch_enabled_is_startup_only_and_silently_ignored(self, tmp_path):
        """``enabled`` is a startup-only field; sending it in the PATCH body must
        not change the value returned by GET.  The PATCH must still succeed (200)
        so that callers that include ``enabled`` for forward-compatibility don't break."""
        client, _ = _make_client(tmp_path, identity=_OWNER)
        # Record the current config-driven value.
        before = client.get("/api/admin/rate-limit-config").json()["enabled"]
        # Attempt to flip it — the body key should be silently ignored.
        patch_resp = client.patch("/api/admin/rate-limit-config", json={"enabled": not before})
        assert patch_resp.status_code == 200
        # GET must still reflect the startup config, not the body value.
        after = client.get("/api/admin/rate-limit-config").json()["enabled"]
        assert after == before, (
            "enabled is startup-only and must not be overridable via the admin API"
        )

    def test_patch_partial_update_preserves_other_fields(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        # First set both fields
        client.patch(
            "/api/admin/rate-limit-config",
            json={"max_requests": 99, "window_seconds": 30},
        )
        # Then update only max_requests
        client.patch("/api/admin/rate-limit-config", json={"max_requests": 50})
        response = client.get("/api/admin/rate-limit-config")
        data = response.json()
        assert data["max_requests"] == 50
        assert data["window_seconds"] == 30  # preserved

    def test_patch_returns_full_config(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.patch(
            "/api/admin/rate-limit-config",
            json={"max_requests": 75},
        )
        data = response.json()
        assert "enabled" in data
        assert "window_seconds" in data
        assert data["max_requests"] == 75
        assert data["per_identity"] is True
        assert data["per_route"] is True


# ---------------------------------------------------------------------------
# GET /api/admin/rbac-status (any authenticated user)
# ---------------------------------------------------------------------------


class TestRbacStatusEndpoint:
    """rbac-status is accessible by any authenticated user, not just admin."""

    @pytest.mark.parametrize(
        "identity",
        [_OWNER, _ADMIN, _RESEARCHER, _REVIEWER, _VIEWER],
        ids=["owner", "admin", "researcher", "reviewer", "viewer"],
    )
    def test_any_role_can_read(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/rbac-status")
        assert response.status_code == 200

    def test_no_auth_can_read(self, tmp_path):
        """In no-auth mode (no identity), rbac-status is still accessible."""
        client, _ = _make_client(tmp_path, identity=None, rbac_enforcement="auto")
        response = client.get("/api/admin/rbac-status")
        assert response.status_code == 200

    def test_response_shape(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/rbac-status")
        data = response.json()
        assert "rbac_enforcement" in data
        assert "rbac_enforced" in data
        assert "auth_provider" in data
        assert isinstance(data["rbac_enforced"], bool)

    def test_rbac_enforcement_value_in_response(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER, rbac_enforcement="enabled")
        response = client.get("/api/admin/rbac-status")
        data = response.json()
        assert data["rbac_enforcement"] == "enabled"
        assert data["rbac_enforced"] is True

    def test_rbac_auto_none_resolves_true(self, tmp_path):
        """AUTO always yields rbac_enforced=True; identity-None path handles passthrough."""
        client, _ = _make_client(tmp_path, identity=_OWNER, rbac_enforcement="auto")
        response = client.get("/api/admin/rbac-status")
        data = response.json()
        assert data["rbac_enforcement"] == "auto"
        # AUTO always True: the identity-None path in require_role gives the passthrough
        # for provider=none deployments; rbac_enforced=True means "gate is active".
        assert data["rbac_enforced"] is True


# ---------------------------------------------------------------------------
# Helpers for rate-limit-enabled test environment
# ---------------------------------------------------------------------------


def _make_client_rate_limit(
    tmp_path: Path,
    identity: AuthIdentity | None = None,
    *,
    requests_per_window: int = 10,
    window_seconds: int = 60,
    rbac_enforcement: str = "enabled",
) -> tuple[TestClient, FoundryConfig]:
    """Like _make_client but with rate limiting explicitly enabled in foundry.yaml.

    Used for tests that need the rate limiter middleware to be active so they
    can verify the 429 threshold changes when admin PATCH overrides apply.
    """
    config = _make_config(tmp_path)

    foundry_yaml_path = config.paths.foundry_yaml
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing:
        existing["foundry"] = {}
    auth: dict[str, Any] = dict(existing["foundry"].get("auth") or {})
    auth["rbac_enforcement"] = rbac_enforcement
    auth["rate_limit"] = {
        "enabled": True,
        "requests_per_window": requests_per_window,
        "window_seconds": window_seconds,
    }
    existing["foundry"]["auth"] = auth
    dump_yaml(existing, foundry_yaml_path)
    config = FoundryConfig(paths=FoundryPaths(root=config.paths.root))

    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: config.paths
    app.dependency_overrides[_get_config] = lambda: config

    if identity is not None:
        app.add_middleware(_InjectIdentityMiddleware, identity=identity)

    return TestClient(app, raise_server_exceptions=True), config


# ---------------------------------------------------------------------------
# Validation: PATCH /api/admin/rate-limit-config must reject non-positive values
# ---------------------------------------------------------------------------


class TestRateLimitConfigValidation:
    """REGRESSION tests — must FAIL before fix, PASS after.

    The rate-limit PATCH handler must reject max_requests <= 0 and
    window_seconds <= 0 with HTTP 422, matching the >= 1 invariant that
    SlidingWindowRateLimiter enforces at construction time.

    Test IDs match the defect specification:
      (a) max_requests=0  → 422, limiter budget unchanged
      (b) window_seconds=0 → 422, no side effects on stored config
      (c) max_requests=-5 → 422 (any non-positive integer)
      (d) max_requests=3  → 200, reflected in GET + enforced as 429 threshold
    """

    def test_a_max_requests_zero_rejected_with_422(self, tmp_path):
        """(a) PATCH max_requests=0 → 422; limiter budget must be unchanged."""
        client, _ = _make_client(tmp_path, identity=_OWNER)
        before = client.get("/api/admin/rate-limit-config").json()["max_requests"]

        response = client.patch("/api/admin/rate-limit-config", json={"max_requests": 0})
        assert response.status_code == 422, (
            f"Expected 422 for max_requests=0 but got {response.status_code}: "
            f"{response.text}"
        )

        # Budget must be unchanged after a rejected request.
        after = client.get("/api/admin/rate-limit-config").json()["max_requests"]
        assert after == before, (
            f"max_requests changed from {before} to {after} after a rejected PATCH — "
            "the invalid value was stored despite the 422"
        )

    def test_b_window_seconds_zero_rejected_with_422(self, tmp_path):
        """(b) PATCH window_seconds=0 → 422; no side effects on stored config."""
        client, _ = _make_client(tmp_path, identity=_OWNER)
        before = client.get("/api/admin/rate-limit-config").json()["window_seconds"]

        response = client.patch("/api/admin/rate-limit-config", json={"window_seconds": 0})
        assert response.status_code == 422, (
            f"Expected 422 for window_seconds=0 but got {response.status_code}: "
            f"{response.text}"
        )

        after = client.get("/api/admin/rate-limit-config").json()["window_seconds"]
        assert after == before, (
            f"window_seconds changed from {before} to {after} after a rejected PATCH"
        )

    def test_c_max_requests_negative_rejected_with_422(self, tmp_path):
        """(c) PATCH max_requests=-5 (any non-positive integer) → 422."""
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.patch("/api/admin/rate-limit-config", json={"max_requests": -5})
        assert response.status_code == 422, (
            f"Expected 422 for max_requests=-5 but got {response.status_code}: "
            f"{response.text}"
        )

    def test_d_valid_positive_applied_and_enforced_as_429_threshold(self, tmp_path):
        """(d) PATCH max_requests=3 → 200, reflected by GET, enforced as 429 threshold.

        Uses a rate-limit-enabled config (startup budget=10) so the middleware
        is active.  After PATCH to 3, exactly 3 requests on a fresh route are
        allowed; the 4th must be 429.
        """
        # Use rate-limit-enabled config so the middleware is actually installed.
        client, _ = _make_client_rate_limit(
            tmp_path, identity=_OWNER, requests_per_window=10
        )

        # Apply valid override — must return 200.
        patch_resp = client.patch("/api/admin/rate-limit-config", json={"max_requests": 3})
        assert patch_resp.status_code == 200, (
            f"Expected 200 for valid max_requests=3 but got {patch_resp.status_code}"
        )
        assert patch_resp.json()["max_requests"] == 3

        # GET must reflect the override immediately.
        get_data = client.get("/api/admin/rate-limit-config").json()
        assert get_data["max_requests"] == 3, (
            f"GET did not reflect override: max_requests={get_data['max_requests']!r}"
        )

        # 429 threshold: 3 requests on a fresh route must be allowed, the 4th denied.
        # Use /api/admin/rbac-status — no prior requests on this route, separate
        # (user_id, route) key from /api/admin/rate-limit-config.
        for i in range(3):
            r = client.get("/api/admin/rbac-status")
            assert r.status_code == 200, (
                f"Request {i + 1}/3 to /api/admin/rbac-status returned "
                f"{r.status_code}, expected 200"
            )

        limited = client.get("/api/admin/rbac-status")
        assert limited.status_code == 429, (
            f"4th request to /api/admin/rbac-status returned {limited.status_code}, "
            "expected 429 — the max_requests=3 override is not being enforced"
        )
