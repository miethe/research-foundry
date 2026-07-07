"""Tests for GET /api/auth/identity endpoint (P5.4 FU-2).

Coverage:
  AUTH-ID-01  provider=none → 200 with null/anonymous response (no middleware)
  AUTH-ID-02  Route IS registered in create_app (not a 404)
  AUTH-ID-03  provider=clerk + valid JWT → 200 with correct identity shape
  AUTH-ID-04  provider=clerk + no token → 401 from middleware (before route runs)
  AUTH-ID-05  provider=local_static + valid token → 200 with correct identity
  AUTH-ID-06  Anonymous response shape is valid JSON with expected null fields
  AUTH-ID-07  Authenticated identity response passes the FE shape-guard

Gate #3 invariant (Clerk tests): all Clerk tokens are signed with the fixture
keypair from tests/fixtures/auth/clerk_jwks_fixture.json — never real Clerk keys.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths

# ---------------------------------------------------------------------------
# Clerk fixture loading (reuse from tests/fixtures/auth/clerk_jwks_fixture.json)
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "auth" / "clerk_jwks_fixture.json"


@pytest.fixture(scope="module")
def clerk_fixture() -> dict:
    """Load the JWKS fixture JSON once per test module."""
    assert _FIXTURE_PATH.exists(), (
        f"Clerk JWKS fixture not found at {_FIXTURE_PATH}. "
        "Run the fixture generator to create it."
    )
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def jwks_dict(clerk_fixture: dict) -> dict:
    """Return the public JWKS dict from the fixture."""
    return clerk_fixture["jwks"]


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _make_payload(
    clerk_fixture: dict,
    *,
    exp_offset: int = 3600,
    nbf_offset: int = -60,
    include_azp: bool = True,
) -> dict[str, Any]:
    """Build a Clerk-shaped JWT payload from fixture data."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": clerk_fixture["test_user_sub"],
        "org_id": clerk_fixture["test_org_id"],
        "org_role": clerk_fixture["test_org_role"],
        "iss": clerk_fixture["issuer"],
        "exp": now + exp_offset,
        "nbf": now + nbf_offset,
    }
    if include_azp:
        payload["azp"] = clerk_fixture["azp"]
    return payload


def _sign_jwt(private_key_pem: str, payload: dict, kid: str) -> str:
    """Sign ``payload`` with the given RSA private key PEM, returning a JWT string."""
    return jwt.encode(
        payload,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _minimal_config(
    tmp_path: Path,
    *,
    auth_block: dict | None = None,
    auth_token_env: str | None = None,
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

    foundry_yaml_path = root / "foundry.yaml"
    existing: dict = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict = {"auth_mode": "none"}
    if auth_token_env is not None:
        viewer["auth_token_env"] = auth_token_env
    existing["foundry"]["viewer"] = viewer
    if auth_block is not None:
        existing["foundry"]["auth"] = auth_block
    dump_yaml(existing, foundry_yaml_path)

    paths = FoundryPaths(root=root)
    return FoundryConfig(paths=paths)


# ---------------------------------------------------------------------------
# AUTH-ID-01, AUTH-ID-02, AUTH-ID-06
# provider=none — route IS registered and returns anonymous response
# ---------------------------------------------------------------------------


class TestAuthIdentityRouteNoAuth:
    """AUTH-ID-01 / AUTH-ID-02 / AUTH-ID-06: /api/auth/identity in provider=none mode."""

    @pytest.fixture()
    def no_auth_client(self, tmp_path):
        """App with auth.provider=none (default)."""
        cfg = _minimal_config(tmp_path)
        app = create_app(cfg)
        return TestClient(app, raise_server_exceptions=True)

    def test_route_is_registered_not_404(self, no_auth_client):
        """AUTH-ID-02: GET /api/auth/identity must be registered — not 404.

        A 404 means the route is absent; the frontend would never get a response.
        This test locks the route registration in create_app.
        """
        resp = no_auth_client.get("/api/auth/identity")
        assert resp.status_code != 404, (
            f"GET /api/auth/identity returned 404 — the route is not registered "
            "in create_app.  The P5.4 FU-2 fix must include_router(auth_identity_router)."
        )

    def test_provider_none_returns_200(self, no_auth_client):
        """AUTH-ID-01: With auth.provider=none, GET /api/auth/identity returns 200."""
        resp = no_auth_client.get("/api/auth/identity")
        assert resp.status_code == 200, (
            f"Expected 200 for auth.provider=none but got {resp.status_code}. "
            "No-auth mode must always return a graceful anonymous response."
        )

    def test_provider_none_returns_anonymous_shape(self, no_auth_client):
        """AUTH-ID-06: Anonymous response has the expected null-field shape.

        Shape: {"user_id": null, "workspace_id": null, "roles": []}
        """
        resp = no_auth_client.get("/api/auth/identity")
        assert resp.status_code == 200
        body = resp.json()

        assert "user_id" in body, f"Missing 'user_id' in anonymous response: {body!r}"
        assert "workspace_id" in body, f"Missing 'workspace_id' in anonymous response: {body!r}"
        assert "roles" in body, f"Missing 'roles' in anonymous response: {body!r}"
        assert body["user_id"] is None, (
            f"Expected user_id=null in anonymous mode but got {body['user_id']!r}"
        )
        assert body["workspace_id"] is None, (
            f"Expected workspace_id=null in anonymous mode but got {body['workspace_id']!r}"
        )
        assert body["roles"] == [], (
            f"Expected roles=[] in anonymous mode but got {body['roles']!r}"
        )

    def test_provider_none_response_is_valid_json(self, no_auth_client):
        """AUTH-ID-06: Response is valid JSON — not an error page."""
        resp = no_auth_client.get("/api/auth/identity")
        assert resp.status_code == 200
        try:
            body = resp.json()
        except Exception as exc:
            pytest.fail(
                f"GET /api/auth/identity with provider=none returned non-JSON body: {exc}. "
                f"Body text: {resp.text!r}"
            )
        assert isinstance(body, dict), (
            f"Expected a JSON dict but got {type(body).__name__!r}: {body!r}"
        )


# ---------------------------------------------------------------------------
# AUTH-ID-03, AUTH-ID-04, AUTH-ID-07
# provider=clerk — uses fixture JWKS (Gate #3: no real Clerk API calls)
# ---------------------------------------------------------------------------


class TestAuthIdentityRouteClerk:
    """AUTH-ID-03 / AUTH-ID-04 / AUTH-ID-07: /api/auth/identity with provider=clerk.

    Uses the Clerk JWKS fixture and patches _default_jwks_fetch so no real
    Clerk API calls are made.  All JWTs are signed with the fixture private key.

    Gate #3 invariant: NEVER point tests at Clerk's live JWKS endpoint.
    """

    @pytest.fixture()
    def clerk_app_client(self, tmp_path, jwks_dict):
        """App with auth.provider=clerk, JWKS fetch mocked to return fixture keys."""
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "clerk",
                "clerk_frontend_api": "https://test.clerk.accounts.dev",
                "clerk_outbound_internet_enabled": True,
            },
        )
        # Patch _default_jwks_fetch so the ClerkAuthProvider constructed inside
        # create_app uses the fixture JWKS instead of making real network calls.
        with patch(
            "research_foundry.api.auth.adapters.clerk._default_jwks_fetch",
            return_value=jwks_dict,
        ):
            app = create_app(cfg)
        return TestClient(app, raise_server_exceptions=False)

    def test_valid_jwt_returns_200(self, clerk_app_client, clerk_fixture, jwks_dict):
        """AUTH-ID-03: Valid fixture-signed JWT → HTTP 200 on /api/auth/identity."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        resp = clerk_app_client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200, (
            f"Expected 200 for a valid Clerk JWT on /api/auth/identity but got "
            f"{resp.status_code}. Body: {resp.text!r}. "
            "Check that ClerkAuthProvider is properly wired in create_app."
        )

    def test_valid_jwt_returns_correct_identity(self, clerk_app_client, clerk_fixture, jwks_dict):
        """AUTH-ID-03: Resolved identity matches fixture claims (sub, org_id, org_role)."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        resp = clerk_app_client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        body = resp.json()

        assert body["user_id"] == clerk_fixture["test_user_sub"], (
            f"user_id mismatch: expected {clerk_fixture['test_user_sub']!r} "
            f"but got {body.get('user_id')!r}"
        )
        assert body["workspace_id"] == clerk_fixture["test_org_id"], (
            f"workspace_id mismatch: expected {clerk_fixture['test_org_id']!r} "
            f"but got {body.get('workspace_id')!r}"
        )
        assert isinstance(body["roles"], list) and len(body["roles"]) > 0, (
            f"Expected non-empty roles list but got {body.get('roles')!r}"
        )
        assert "owner" in body["roles"], (
            f"Expected 'owner' role from org:owner fixture slug but got {body['roles']!r}"
        )

    def test_no_token_returns_401(self, clerk_app_client):
        """AUTH-ID-04: provider=clerk + no Authorization header → 401 from middleware."""
        resp = clerk_app_client.get("/api/auth/identity")

        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated request with auth.provider=clerk "
            f"but got {resp.status_code}. "
            "AuthProviderMiddleware must reject unauthenticated requests."
        )

    def test_expired_jwt_returns_401(self, clerk_app_client, clerk_fixture):
        """AUTH-ID-04 (expired variant): Expired Clerk JWT → 401."""
        payload = _make_payload(clerk_fixture, exp_offset=-3600, nbf_offset=-7200)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        resp = clerk_app_client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for an expired JWT but got {resp.status_code}."
        )

    def test_fe_shape_guard_passes(self, clerk_app_client, clerk_fixture):
        """AUTH-ID-07: Authenticated response passes the FE AuthIdentity shape-guard.

        Simulates the check in useClerkAuth.ts fetchIdentityWithToken():
          if (!d || typeof d.user_id !== "string" || ...)
            throw new ClientError(502, "Identity response is malformed")

        The backend response must pass this check.
        """
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        resp = clerk_app_client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        body = resp.json()

        fe_shape_ok = (
            body is not None
            and isinstance(body.get("user_id"), str)
            and isinstance(body.get("workspace_id"), str)
            and isinstance(body.get("roles"), list)
        )
        assert fe_shape_ok, (
            f"Backend /api/auth/identity response FAILS the FE shape-guard "
            f"in fetchIdentityWithToken().  The FE would raise ClientError(502). "
            f"Response body: {body!r}"
        )


# ---------------------------------------------------------------------------
# AUTH-ID-05  provider=local_static — uses bearer token
# ---------------------------------------------------------------------------


class TestAuthIdentityRouteLocalStatic:
    """AUTH-ID-05: /api/auth/identity with provider=local_static.

    Verifies the identity endpoint returns the resolved AuthIdentity from a
    local_static bearer token — not Clerk-specific, but proves the endpoint
    is provider-agnostic.
    """

    _TOKEN = "test-auth-id-bearer-token"
    _ENV_VAR = "RF_SERVE_TOKEN_AUTHID"

    @pytest.fixture()
    def local_static_client(self, tmp_path, monkeypatch):
        """App with local_static provider."""
        monkeypatch.setenv(self._ENV_VAR, self._TOKEN)
        cfg = _minimal_config(
            tmp_path,
            auth_block={
                "provider": "local_static",
                "local_static": {
                    "tokens": [
                        {
                            "token_env": self._ENV_VAR,
                            "user_id": "auth_id_test_user",
                            "workspace_id": "ws_test",
                            "roles": ["researcher"],
                        }
                    ]
                },
            },
        )
        app = create_app(cfg)
        return TestClient(app, raise_server_exceptions=True)

    def test_valid_token_returns_identity(self, local_static_client):
        """AUTH-ID-05: Valid local_static Bearer token → 200 with populated identity."""
        resp = local_static_client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {self._TOKEN}"},
        )

        assert resp.status_code == 200, (
            f"Expected 200 for a valid local_static token but got {resp.status_code}. "
            f"Body: {resp.text!r}"
        )
        body = resp.json()

        assert body["user_id"] == "auth_id_test_user", (
            f"user_id mismatch: expected 'auth_id_test_user' but got {body.get('user_id')!r}"
        )
        assert body["workspace_id"] == "ws_test", (
            f"workspace_id mismatch: expected 'ws_test' but got {body.get('workspace_id')!r}"
        )
        assert "researcher" in body["roles"], (
            f"Expected 'researcher' role but got {body['roles']!r}"
        )

    def test_missing_token_returns_401(self, local_static_client):
        """AUTH-ID-05 (negative): No token → 401 from AuthProviderMiddleware."""
        resp = local_static_client.get("/api/auth/identity")
        assert resp.status_code == 401, (
            f"Expected 401 for unauthenticated request but got {resp.status_code}."
        )

    def test_wrong_token_returns_401(self, local_static_client):
        """AUTH-ID-05 (negative): Wrong token → 401."""
        resp = local_static_client.get(
            "/api/auth/identity",
            headers={"Authorization": "Bearer wrong-token-value"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for a wrong token but got {resp.status_code}."
        )
