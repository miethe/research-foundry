"""Seam contract test: FE↔BE Clerk login round-trip (CLERK-900 / AC P5.4-A, P5.4-B).

Proves the full FE↔BE contract at the HTTP boundary WITHOUT a running server:
  - FastAPI TestClient simulates the HTTP layer end-to-end.
  - ClerkAuthProvider is wired to the fixture JWKS (no real Clerk API calls).
  - JWTs are signed with the fixture private key, matching the fixture public key
    in the JWKS — the same crypto path that production Clerk tokens use.
  - A test-only ``GET /auth/identity`` probe route stands in for the P5.5 endpoint
    (NOT added to app.py — that is P5.5 scope). It returns the AuthIdentity that
    AuthProviderMiddleware attaches to request.state after a successful verify.

Gate #3 invariant: NEVER point this test at Clerk's live JWKS endpoint.
All keys and tokens come from ``tests/fixtures/auth/clerk_jwks_fixture.json``.

FE contract (from useClerkAuth.ts):
  fetchIdentityWithToken(token):
    - calls GET /auth/identity
    - sends:    Authorization: Bearer <token>
    - expects:  { user_id: string, workspace_id: string, roles: string[] }
    - on 401:   raises ClientError(401, "Authentication failed: ...")
    - on 403:   raises ClientError(403, "Authorization failed: ...")
    - on malformed body:
                raises ClientError(502, "Identity response is malformed: ...")
    - invariant (AC P5.4-B): identity === null always paired with error !== null

BE contract (from ClerkAuthProvider.authenticate() + AuthProviderMiddleware):
  - reads:    Authorization: Bearer <token>
  - verifies: RS256 JWT against JWKS (fixture)
  - success:  sets request.state.identity = AuthIdentity(user_id, workspace_id, roles)
  - failure:  returns {"detail": "Unauthorized"} HTTP 401
  - never raises past the adapter boundary

Three seam-level invariants this test locks down:
  I-1  Header format: FE sends "Authorization: Bearer <token>" ↔ BE reads it identically.
  I-2  Identity shape: BE JSON { user_id, workspace_id, roles[] } ↔ FE AuthIdentity interface.
  I-3  Failure is explicit: expired/bad-sig tokens → 401, never silent empty identity.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from research_foundry.api.auth.adapters.clerk import ClerkAuthProvider
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.middleware.auth import AuthProviderMiddleware

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "auth" / "clerk_jwks_fixture.json"
)


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
    """Return the public JWKS dict from the fixture (safe to use as mock return value)."""
    return clerk_fixture["jwks"]


# ---------------------------------------------------------------------------
# JWT signing helpers
# (mirror of helpers in tests/unit/test_clerk_adapter.py — kept local to make
#  the seam test self-contained and reviewable without cross-file context)
# ---------------------------------------------------------------------------


def _make_payload(
    clerk_fixture: dict,
    *,
    exp_offset: int = 3600,
    nbf_offset: int = -60,
    include_azp: bool = True,
) -> dict[str, Any]:
    """Build a Clerk-shaped JWT payload from fixture data.

    Parameters
    ----------
    exp_offset:
        Seconds relative to ``now`` for the ``exp`` claim.
        Use a negative value for an already-expired token.
    nbf_offset:
        Seconds relative to ``now`` for the ``nbf`` claim.
    include_azp:
        When ``False``, the ``azp`` claim is omitted.
    """
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


# ---------------------------------------------------------------------------
# Seam app builder
#
# Creates a minimal FastAPI app with:
#   - AuthProviderMiddleware configured with a fixture-JWKS ClerkAuthProvider
#   - A test-only GET /auth/identity probe route that mirrors the P5.5 endpoint
#     shape exactly as useClerkAuth.ts expects it
#
# IMPORTANT: This /auth/identity route MUST NOT be added to app.py — that is
# P5.5 scope. It lives here only to make the seam contract testable without
# modifying production code.
# ---------------------------------------------------------------------------


def _build_seam_app(provider: ClerkAuthProvider) -> FastAPI:
    """Build a minimal FastAPI app + AuthProviderMiddleware + /auth/identity probe.

    The probe route returns:
        { "user_id": str, "workspace_id": str, "roles": [str, ...] }

    This is the shape that useClerkAuth.ts expects from the backend identity
    endpoint (AuthIdentity interface). On auth failure, AuthProviderMiddleware
    intercepts before the route is reached and returns HTTP 401.
    """
    app = FastAPI()
    app.add_middleware(AuthProviderMiddleware, provider=provider)

    @app.get("/auth/identity")
    def identity_endpoint(request: StarletteRequest) -> dict:
        # AuthProviderMiddleware sets request.state.identity on success.
        # If it's absent here, the middleware allowed a gap — surface it loudly.
        idt: AuthIdentity | None = getattr(request.state, "identity", None)
        if idt is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {
            "user_id": idt.user_id,
            "workspace_id": idt.workspace_id,
            "roles": list(idt.roles),
        }

    return app


@pytest.fixture(scope="module")
def clerk_provider(clerk_fixture: dict, jwks_dict: dict) -> ClerkAuthProvider:
    """ClerkAuthProvider wired to the fixture JWKS — no network calls.

    The ``jwks_fetch_fn`` mock returns the fixture JWKS directly, bypassing
    urllib so no live Clerk API is reachable from this test.
    """
    mock_fetch = MagicMock(return_value=jwks_dict)
    return ClerkAuthProvider(
        frontend_api_url="https://test.clerk.accounts.dev",
        jwks_fetch_fn=mock_fetch,
    )


@pytest.fixture(scope="module")
def seam_client(clerk_provider: ClerkAuthProvider) -> TestClient:
    """TestClient for the seam app.  Module-scoped — shared across all tests."""
    app = _build_seam_app(clerk_provider)
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# CLERK-900 / AC P5.4-A  Positive case: valid JWT → AuthIdentity
# ---------------------------------------------------------------------------


class TestSeamPositiveCase:
    """AC P5.4-A: A fixture-signed, non-expired JWT round-trips to a populated AuthIdentity.

    This is the core seam proof: FE signs a JWT via Clerk → backend verifies via
    JWKS → AuthIdentity with expected shape is returned over HTTP.
    """

    def test_valid_jwt_returns_200(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """Valid fixture-signed JWT → HTTP 200.

        This is the primary positive gate: the full path from Bearer header
        parsing through RS256 JWKS verification to HTTP 200 succeeds.
        """
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200, (
            f"Expected HTTP 200 for a valid Clerk JWT but got {resp.status_code}. "
            f"Body: {resp.text!r}. "
            "Check JWKS key matching and RS256 signature verification."
        )

    def test_valid_jwt_user_id_matches_fixture(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """Resolved user_id matches the 'sub' claim in the fixture payload."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == clerk_fixture["test_user_sub"], (
            f"Expected user_id={clerk_fixture['test_user_sub']!r} "
            f"but got {body.get('user_id')!r}."
        )

    def test_valid_jwt_workspace_id_matches_fixture(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """Resolved workspace_id matches the 'org_id' claim in the fixture payload."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["workspace_id"] == clerk_fixture["test_org_id"], (
            f"Expected workspace_id={clerk_fixture['test_org_id']!r} "
            f"but got {body.get('workspace_id')!r}."
        )

    def test_valid_jwt_roles_non_empty(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """Resolved roles tuple is non-empty — fixture uses org:owner → ['owner']."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        roles = resp.json().get("roles")
        assert isinstance(roles, list) and len(roles) > 0, (
            f"Expected non-empty roles list but got {roles!r}."
        )
        assert "owner" in roles, (
            f"Expected 'owner' role from org:owner fixture but got {roles!r}."
        )


# ---------------------------------------------------------------------------
# CLERK-900  Seam invariant I-1: Header format contract
#
# FE sends:    Authorization: Bearer <token>
# BE reads:    request.headers.get("Authorization", "").startswith("Bearer ")
#
# Both sides must agree on the exact format — this test locks the contract.
# ---------------------------------------------------------------------------


class TestSeamHeaderContract:
    """Seam invariant I-1: 'Authorization: Bearer <token>' is the binding contract.

    useClerkAuth.ts (FE) always sends this exact header format.
    ClerkAuthProvider._extract_token() (BE) reads it via startswith("Bearer ").
    The AuthProviderMiddleware sits in the middle and calls authenticate().

    A valid JWT in the correct format → 200.
    Any deviation → 401 (FE would surface a ClientError).
    """

    def test_bearer_header_format_yields_200(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """'Authorization: Bearer <token>' — the exact FE format — yields 200.

        This is the primary I-1 assertion: the FE header format is accepted.
        """
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200, (
            f"'Authorization: Bearer <token>' (the exact format useClerkAuth.ts sends) "
            f"must yield 200 but got {resp.status_code}. "
            f"Body: {resp.text!r}"
        )

    def test_no_authorization_header_yields_401(
        self, seam_client: TestClient
    ) -> None:
        """No Authorization header → 401.

        FE without an active Clerk session calls getToken() → null, raises
        ClientError(401) before fetch. This test confirms the backend also
        rejects headerless requests.
        """
        resp = seam_client.get("/auth/identity")

        assert resp.status_code == 401, (
            f"Expected 401 when Authorization header is absent but got {resp.status_code}."
        )

    def test_basic_auth_prefix_yields_401(
        self, seam_client: TestClient
    ) -> None:
        """'Authorization: Basic ...' (wrong scheme) → 401.

        ClerkAuthProvider ignores non-Bearer auth headers — consistent with
        the FE only ever sending Bearer tokens.
        """
        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for Basic auth scheme (not Bearer) but got {resp.status_code}."
        )

    def test_jwt_without_bearer_prefix_yields_401(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """JWT sent WITHOUT 'Bearer ' prefix → 401.

        The 'Bearer ' prefix is part of the FE↔BE contract — omitting it means
        the BE cannot locate the token in the header.
        """
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        # Send the raw token without "Bearer " prefix
        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": token},
        )

        assert resp.status_code == 401, (
            f"Expected 401 when 'Bearer ' prefix is omitted but got {resp.status_code}. "
            "The 'Bearer ' prefix is mandatory — both FE and BE must agree on this."
        )

    def test_empty_bearer_value_yields_401(
        self, seam_client: TestClient
    ) -> None:
        """'Authorization: Bearer ' (empty after prefix) → 401."""
        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": "Bearer "},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for empty Bearer value but got {resp.status_code}."
        )


# ---------------------------------------------------------------------------
# CLERK-900 / AC P5.4-A + P5.4-B  Negative cases: invalid tokens → 401
# ---------------------------------------------------------------------------


class TestSeamNegativeCases:
    """AC P5.4-A + P5.4-B: Invalid/expired tokens are hard-rejected with 401.

    The FE useClerkAuth hook checks res.ok — any non-2xx raises a ClientError
    rather than returning a silent empty identity. This test confirms the BE
    never returns 200 for an unverifiable token.
    """

    def test_expired_jwt_yields_401(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """JWT expired 1 hour ago → HTTP 401.

        ClerkAuthProvider rejects expired tokens (exp < now).
        AuthProviderMiddleware translates None → {"detail": "Unauthorized"} 401.
        The FE hook raises ClientError(401, "Authentication failed: ...").
        """
        payload = _make_payload(clerk_fixture, exp_offset=-3600, nbf_offset=-7200)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for an expired Clerk JWT but got {resp.status_code}. "
            "Expired tokens must be hard-rejected — the FE must surface this as an error."
        )

    def test_expired_jwt_response_has_detail_key(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """Expired token 401 response body has a 'detail' key.

        AuthProviderMiddleware returns {"detail": "Unauthorized"} on rejection.
        The FE useClerkAuth hook doesn't inspect the body on non-2xx (it raises
        based on status code alone), but the body must be valid JSON with 'detail'
        for consistency with the rest of the API error contract.
        """
        payload = _make_payload(clerk_fixture, exp_offset=-3600, nbf_offset=-7200)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401
        body = resp.json()
        assert "detail" in body, (
            f"Expected 401 body to have 'detail' key but got: {body!r}."
        )

    def test_bad_signature_jwt_yields_401(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """JWT signed with wrong RSA key → 401.

        Uses the same kid as the fixture JWKS key so key-lookup succeeds, but
        the signature verification fails because the private key doesn't match
        the public key in the JWKS. This exercises the RS256 signature check.
        """
        payload = _make_payload(clerk_fixture)
        # Sign with the fixture's 'bad_sig_private_key_pem' — different key pair
        token = _sign_jwt(
            clerk_fixture["bad_sig_private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for a JWT with an invalid signature but got {resp.status_code}. "
            "RS256 signature mismatch must be a hard rejection."
        )

    def test_401_body_does_not_contain_identity_fields(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """AC P5.4-B: 401 response body must NOT contain user_id/workspace_id/roles.

        The FE checks res.ok before parsing the body. A 401 body that accidentally
        contains identity-shaped fields could be mistaken for a valid identity in
        a future caller that bypasses the ok check. This test locks out that class
        of bug.
        """
        payload = _make_payload(clerk_fixture, exp_offset=-3600, nbf_offset=-7200)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401
        body = resp.json()

        for field in ("user_id", "workspace_id", "roles"):
            assert field not in body, (
                f"401 response must not contain identity field '{field}' "
                f"but got: {body!r}. This is a security-relevant shape invariant."
            )

    def test_missing_azp_claim_yields_401(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """JWT without required 'azp' claim → 401.

        Clerk JWTs always include 'azp'. A JWT without it is malformed from the
        Clerk perspective; ClerkAuthProvider.authenticate() returns None for it.
        """
        payload = _make_payload(clerk_fixture, include_azp=False)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for JWT missing 'azp' claim but got {resp.status_code}."
        )


# ---------------------------------------------------------------------------
# CLERK-900  Seam invariant I-2: AuthIdentity JSON shape contract
#
# The BE JSON shape for a successful identity resolve must match the FE
# AuthIdentity interface from useClerkAuth.ts exactly.  The FE shape-check:
#   if (!d || typeof d.user_id !== "string" || typeof d.workspace_id !== "string"
#       || !Array.isArray(d.roles)) → ClientError(502, "Identity response is malformed")
#
# This test asserts the BE response PASSES the FE shape guard.
# ---------------------------------------------------------------------------


class TestSeamIdentityJsonShape:
    """Seam invariant I-2: BE /auth/identity JSON shape matches FE AuthIdentity interface.

    FE interface (useClerkAuth.ts):
        interface AuthIdentity {
          user_id: string;        // non-empty string
          workspace_id: string;   // non-empty string
          roles: string[];        // non-empty array of strings
        }

    BE dataclass (provider.py):
        @dataclass(frozen=True)
        class AuthIdentity:
            user_id: str
            workspace_id: str
            roles: tuple[str, ...]  # serialized as JSON array by the endpoint
    """

    def test_response_has_all_three_required_fields(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """200 response contains user_id, workspace_id, and roles — all required by FE."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()

        for field in ("user_id", "workspace_id", "roles"):
            assert field in body, (
                f"Required field '{field}' missing from /auth/identity response: {body!r}. "
                f"useClerkAuth.ts raises ClientError(502) when any of the three fields is absent."
            )

    def test_user_id_is_non_empty_string(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """user_id is a non-empty string — FE validates typeof d.user_id === 'string'."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        user_id = resp.json().get("user_id")

        assert isinstance(user_id, str) and user_id, (
            f"user_id must be a non-empty string but got {user_id!r}."
        )

    def test_workspace_id_is_non_empty_string(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """workspace_id is a non-empty string — FE validates typeof d.workspace_id === 'string'."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        workspace_id = resp.json().get("workspace_id")

        assert isinstance(workspace_id, str) and workspace_id, (
            f"workspace_id must be a non-empty string but got {workspace_id!r}."
        )

    def test_roles_is_non_empty_list_of_strings(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """roles is a non-empty list of strings — FE validates Array.isArray(d.roles)."""
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        roles = resp.json().get("roles")

        assert isinstance(roles, list), (
            f"roles must be a JSON array but got {type(roles).__name__!r}: {roles!r}."
        )
        assert len(roles) > 0, (
            f"roles must be non-empty — AuthIdentity always carries at least one role: {roles!r}."
        )
        assert all(isinstance(r, str) for r in roles), (
            f"All roles entries must be strings: {roles!r}."
        )

    def test_fe_shape_guard_passes(
        self, seam_client: TestClient, clerk_fixture: dict
    ) -> None:
        """Simulate fetchIdentityWithToken() shape validation from useClerkAuth.ts.

        useClerkAuth.ts raises ClientError(502) when the FE shape-check fails:
            if (!d
                || typeof d.user_id !== "string"
                || typeof d.workspace_id !== "string"
                || !Array.isArray(d.roles))
              throw new ClientError(502, "Identity response is malformed: ...")

        This test asserts the BE response PASSES that check — the FE would NOT
        raise ClientError(502) for a valid Clerk JWT.
        """
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"]
        )

        resp = seam_client.get(
            "/auth/identity",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()

        # Mirror the FE shape-guard verbatim
        fe_shape_ok = (
            body is not None
            and isinstance(body.get("user_id"), str)
            and isinstance(body.get("workspace_id"), str)
            and isinstance(body.get("roles"), list)
        )
        assert fe_shape_ok, (
            f"Backend response FAILS the FE shape-guard in fetchIdentityWithToken(). "
            f"The FE would raise ClientError(502, 'Identity response is malformed: "
            f"missing required fields (user_id, workspace_id, roles)'). "
            f"Response body: {body!r}"
        )
