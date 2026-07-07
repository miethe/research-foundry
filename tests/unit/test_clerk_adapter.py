"""Unit tests for ClerkAuthProvider JWKS-based JWT verification (CLK-4.1).

All tests run without any network access — the JWKS fixture in
``tests/fixtures/auth/clerk_jwks_fixture.json`` supplies both the public JWKS
and the RSA private key used to sign test JWTs on the fly.

Test coverage:
  CLK-4.1-T01  Valid JWT → populated AuthIdentity (user_id, workspace_id, roles non-empty)
  CLK-4.1-T02  Expired JWT → returns None (not an exception)
  CLK-4.1-T03  Bad-signature JWT → returns None
  CLK-4.1-T04  JWT missing 'azp' claim → returns None
  CLK-4.1-T05  JWKS caching — fetch called exactly once for two authenticate() calls
  CLK-4.1-T06  Missing Authorization header → returns None
  CLK-4.1-T07  Cookie fallback (__session) → valid JWT accepted
  CLK-4.1-T08  JWKS unavailable → returns None (never raises)

Gate #3 invariants enforced here:
  - NEVER point tests at Clerk's real JWKS endpoint.
  - NEVER hardcode a real Clerk secret.
  - All JWTs are signed with the fixture's isolated test keypair.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import jwt
import pytest

from research_foundry.api.auth.adapters.clerk import ClerkAuthProvider
from research_foundry.api.auth.provider import AuthIdentity

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "auth" / "clerk_jwks_fixture.json"


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
    """Return the JWKS dict from the fixture (public keys only — safe to use as mock return)."""
    return clerk_fixture["jwks"]


# ---------------------------------------------------------------------------
# JWT signing helpers
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
        Seconds relative to ``now`` for the ``exp`` claim.  Use a negative
        value for an already-expired token.
    nbf_offset:
        Seconds relative to ``now`` for the ``nbf`` claim.
    include_azp:
        When ``False``, the ``azp`` claim is omitted (for missing-claim tests).
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
    """Sign ``payload`` with the given RSA private key PEM and return a JWT string."""
    return jwt.encode(
        payload,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": kid},
    )


# ---------------------------------------------------------------------------
# Fake request helpers
# ---------------------------------------------------------------------------


def _bearer_request(token: str) -> SimpleNamespace:
    """Minimal fake Starlette request with Authorization: Bearer <token>."""
    return SimpleNamespace(
        headers={"Authorization": f"Bearer {token}"},
        cookies={},
    )


def _cookie_request(token: str) -> SimpleNamespace:
    """Minimal fake Starlette request with __session cookie."""
    return SimpleNamespace(
        headers={},
        cookies={"__session": token},
    )


def _empty_request() -> SimpleNamespace:
    """Request with no auth credentials."""
    return SimpleNamespace(
        headers={},
        cookies={},
    )


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def _make_provider(jwks_dict: dict, azp_expected: str | None = None) -> ClerkAuthProvider:
    """Return a ClerkAuthProvider whose JWKS fetch is mocked to return ``jwks_dict``."""
    mock_fetch = MagicMock(return_value=jwks_dict)
    provider = ClerkAuthProvider(
        frontend_api_url="https://test.clerk.accounts.dev",
        azp_expected=azp_expected,
        jwks_fetch_fn=mock_fetch,
    )
    return provider


# ---------------------------------------------------------------------------
# CLK-4.1-T01  Valid JWT → populated AuthIdentity
# ---------------------------------------------------------------------------


class TestValidJwt:
    """CLK-4.1-T01: A correctly-signed, non-expired JWT yields a populated AuthIdentity."""

    def test_valid_jwt_returns_auth_identity(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])
        request = _bearer_request(token)

        result = provider.authenticate(request)  # type: ignore[arg-type]

        assert result is not None, (
            "Expected an AuthIdentity for a valid Clerk JWT but got None. "
            "Check JWKS key matching, signature verification, and claim extraction."
        )
        assert isinstance(result, AuthIdentity)

    def test_valid_jwt_user_id_populated(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is not None
        assert result.user_id == clerk_fixture["test_user_sub"], (
            f"Expected user_id={clerk_fixture['test_user_sub']!r} "
            f"but got {result.user_id!r}."
        )

    def test_valid_jwt_workspace_id_populated(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is not None
        assert result.workspace_id == clerk_fixture["test_org_id"], (
            f"Expected workspace_id={clerk_fixture['test_org_id']!r} "
            f"but got {result.workspace_id!r}."
        )

    def test_valid_jwt_roles_non_empty(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is not None
        assert len(result.roles) > 0, (
            f"Expected non-empty roles tuple but got {result.roles!r}. "
            "org:owner should map to at least one role."
        )
        assert isinstance(result.roles, tuple), (
            f"roles must be a tuple (AuthIdentity contract), got {type(result.roles)!r}."
        )

    def test_org_owner_maps_to_owner_role(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)  # fixture has org_role=org:owner
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is not None
        assert "owner" in result.roles, (
            f"Expected 'owner' role for org:owner but got {result.roles!r}."
        )


# ---------------------------------------------------------------------------
# CLK-4.1-T02  Expired JWT → returns None
# ---------------------------------------------------------------------------


class TestExpiredJwt:
    """CLK-4.1-T02: An expired JWT must return None without raising."""

    def test_expired_jwt_returns_none(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        # exp_offset=-3600 → expired 1 hour ago
        payload = _make_payload(clerk_fixture, exp_offset=-3600, nbf_offset=-7200)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is None, (
            f"Expected None for an expired JWT but got {result!r}. "
            "authenticate() must return None (not raise) for expired tokens."
        )

    def test_expired_jwt_does_not_raise(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture, exp_offset=-1, nbf_offset=-120)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        # Must not raise under any circumstances.
        try:
            provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]
        except Exception as exc:
            pytest.fail(
                f"authenticate() raised {type(exc).__name__} for an expired token: {exc}. "
                "The adapter MUST swallow all exceptions and return None."
            )


# ---------------------------------------------------------------------------
# CLK-4.1-T03  Bad-signature JWT → returns None
# ---------------------------------------------------------------------------


class TestBadSignatureJwt:
    """CLK-4.1-T03: A JWT signed with a different key must return None."""

    def test_bad_signature_returns_none(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        # Sign with the 'bad' keypair — different from the JWKS public key.
        token = _sign_jwt(
            clerk_fixture["bad_sig_private_key_pem"], payload, clerk_fixture["kid"]
        )
        # Use the same kid so key lookup succeeds but signature verification fails.

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is None, (
            f"Expected None for a bad-signature JWT but got {result!r}. "
            "authenticate() must detect signature mismatch and return None."
        )

    def test_bad_signature_does_not_raise(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(
            clerk_fixture["bad_sig_private_key_pem"], payload, clerk_fixture["kid"]
        )

        try:
            provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]
        except Exception as exc:
            pytest.fail(
                f"authenticate() raised {type(exc).__name__} for a bad-signature token: {exc}"
            )


# ---------------------------------------------------------------------------
# CLK-4.1-T04  JWT missing 'azp' claim → returns None
# ---------------------------------------------------------------------------


class TestMissingAzpClaim:
    """CLK-4.1-T04: A JWT without the 'azp' claim must return None."""

    def test_missing_azp_returns_none(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture, include_azp=False)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is None, (
            f"Expected None when 'azp' claim is absent but got {result!r}. "
            "Clerk JWTs without azp must be rejected."
        )

    def test_empty_azp_returns_none(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture, include_azp=False)
        payload["azp"] = ""  # explicit empty string — should be treated as absent
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        assert result is None, (
            "Expected None when 'azp' is an empty string but got {result!r}."
        )


# ---------------------------------------------------------------------------
# CLK-4.1-T05  JWKS caching — fetch called exactly once
# ---------------------------------------------------------------------------


class TestJwksCaching:
    """CLK-4.1-T05: The JWKS fetch function must be called exactly once for two authenticate() calls."""

    def test_jwks_fetch_called_exactly_once(self, clerk_fixture, jwks_dict):
        mock_fetch = MagicMock(return_value=jwks_dict)
        provider = ClerkAuthProvider(
            frontend_api_url="https://test.clerk.accounts.dev",
            jwks_fetch_fn=mock_fetch,
        )

        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])
        request = _bearer_request(token)

        # First call — should fetch JWKS.
        result1 = provider.authenticate(request)  # type: ignore[arg-type]
        # Second call — must NOT fetch JWKS again.
        result2 = provider.authenticate(request)  # type: ignore[arg-type]

        assert mock_fetch.call_count == 1, (
            f"Expected JWKS fetch to be called exactly once but was called "
            f"{mock_fetch.call_count} time(s). "
            "In-process JWKS caching is a hard NFR — subsequent calls must reuse the cache."
        )
        assert result1 is not None and result2 is not None, (
            f"Both authenticate() calls should succeed: result1={result1!r}, result2={result2!r}"
        )

    def test_jwks_cache_persists_across_calls(self, clerk_fixture, jwks_dict):
        """Separate verify: cached JWKS is used; results are consistent."""
        mock_fetch = MagicMock(return_value=jwks_dict)
        provider = ClerkAuthProvider(
            frontend_api_url="https://test.clerk.accounts.dev",
            jwks_fetch_fn=mock_fetch,
        )

        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        r1 = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]
        r2 = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]

        # Both results should be equivalent AuthIdentity instances.
        assert r1 is not None and r2 is not None
        assert r1.user_id == r2.user_id
        assert r1.workspace_id == r2.workspace_id
        assert r1.roles == r2.roles


# ---------------------------------------------------------------------------
# CLK-4.1-T06  Missing Authorization header → returns None
# ---------------------------------------------------------------------------


class TestMissingToken:
    """CLK-4.1-T06: No token in header or cookie → None."""

    def test_no_auth_header_returns_none(self, jwks_dict):
        provider = _make_provider(jwks_dict)
        result = provider.authenticate(_empty_request())  # type: ignore[arg-type]
        assert result is None, f"Expected None for request with no credentials but got {result!r}."

    def test_non_bearer_auth_header_returns_none(self, jwks_dict):
        provider = _make_provider(jwks_dict)
        request = SimpleNamespace(
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
            cookies={},
        )
        result = provider.authenticate(request)  # type: ignore[arg-type]
        assert result is None, (
            f"Expected None for Basic-auth header (non-Bearer) but got {result!r}."
        )

    def test_empty_bearer_returns_none(self, jwks_dict):
        provider = _make_provider(jwks_dict)
        request = SimpleNamespace(
            headers={"Authorization": "Bearer "},
            cookies={},
        )
        result = provider.authenticate(request)  # type: ignore[arg-type]
        assert result is None


# ---------------------------------------------------------------------------
# CLK-4.1-T07  Cookie fallback (__session) → valid JWT accepted
# ---------------------------------------------------------------------------


class TestCookieFallback:
    """CLK-4.1-T07: __session cookie is accepted as the token source."""

    def test_session_cookie_valid_jwt_returns_identity(self, clerk_fixture, jwks_dict):
        provider = _make_provider(jwks_dict)
        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])
        request = _cookie_request(token)

        result = provider.authenticate(request)  # type: ignore[arg-type]

        assert result is not None, (
            "Expected AuthIdentity from __session cookie token but got None. "
            "Cookie fallback must be supported."
        )
        assert result.user_id == clerk_fixture["test_user_sub"]

    def test_bearer_takes_precedence_over_cookie(self, clerk_fixture, jwks_dict):
        """If both Bearer header and __session cookie are present, header wins."""
        provider = _make_provider(jwks_dict)

        # Valid token in Bearer header.
        valid_payload = _make_payload(clerk_fixture)
        valid_token = _sign_jwt(
            clerk_fixture["private_key_pem"], valid_payload, clerk_fixture["kid"]
        )

        # Expired token in cookie — if header loses precedence, this causes None.
        expired_payload = _make_payload(clerk_fixture, exp_offset=-3600, nbf_offset=-7200)
        expired_token = _sign_jwt(
            clerk_fixture["private_key_pem"], expired_payload, clerk_fixture["kid"]
        )

        request = SimpleNamespace(
            headers={"Authorization": f"Bearer {valid_token}"},
            cookies={"__session": expired_token},
        )

        result = provider.authenticate(request)  # type: ignore[arg-type]

        assert result is not None, (
            "Expected valid AuthIdentity from Bearer header (precedence over cookie) "
            f"but got {result!r}. Header must win when both sources are present."
        )


# ---------------------------------------------------------------------------
# CLK-4.1-T08  JWKS unavailable → returns None (never raises)
# ---------------------------------------------------------------------------


class TestJwksUnavailable:
    """CLK-4.1-T08: Network failure during JWKS fetch → None, not an exception."""

    def test_jwks_fetch_error_returns_none(self, clerk_fixture):
        def _failing_fetch(url: str) -> dict:  # noqa: ARG001
            raise OSError("simulated network failure")

        provider = ClerkAuthProvider(
            frontend_api_url="https://test.clerk.accounts.dev",
            jwks_fetch_fn=_failing_fetch,
        )

        payload = _make_payload(clerk_fixture)
        # We can't sign with the real key here — we just need something to check the path.
        # Use the fixture's real private key so no InsecureKeyLengthWarning from PyJWT.
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])
        # Use a valid-looking Bearer token; the adapter should fail at JWKS fetch, not at decode.
        request = _bearer_request(token)

        try:
            result = provider.authenticate(request)  # type: ignore[arg-type]
        except Exception as exc:
            pytest.fail(
                f"authenticate() raised {type(exc).__name__} when JWKS fetch failed: {exc}. "
                "The adapter MUST return None instead of propagating exceptions."
            )
        assert result is None, (
            f"Expected None when JWKS fetch fails but got {result!r}."
        )

    def test_jwks_returns_invalid_type_returns_none(self, clerk_fixture):
        """If the JWKS fetch returns something that's not a dict, return None."""
        def _bad_fetch(url: str) -> dict:  # noqa: ARG001
            return "not-a-dict"  # type: ignore[return-value]

        provider = ClerkAuthProvider(
            frontend_api_url="https://test.clerk.accounts.dev",
            jwks_fetch_fn=_bad_fetch,
        )

        payload = _make_payload(clerk_fixture)
        token = _sign_jwt(clerk_fixture["private_key_pem"], payload, clerk_fixture["kid"])

        result = provider.authenticate(_bearer_request(token))  # type: ignore[arg-type]
        assert result is None


# ---------------------------------------------------------------------------
# CLK-4.1-T09 / CLK-4.3  available() classmethod — dark-by-default gate
# ---------------------------------------------------------------------------


class TestAvailable:
    """CLK-4.3 (supersedes CLK-4.1-T09 placeholder): available() is False with no config.

    The dark-by-default invariant: Clerk must never become active without an
    explicit operator opt-in in foundry.yaml.  With a default/empty foundry.yaml
    both preconditions (clerk_frontend_api + clerk_outbound_internet_enabled)
    are absent, so available() must return False.
    """

    def test_available_false_by_default(self):
        """available() returns False when no Clerk config is active (dark-by-default)."""
        mock_cfg = MagicMock()
        mock_cfg.auth_clerk_frontend_api.return_value = ""
        mock_cfg.auth_clerk_outbound_internet_enabled.return_value = False

        with patch("research_foundry.config.FoundryConfig") as mock_fc_cls:
            mock_fc_cls.load.return_value = mock_cfg
            result = ClerkAuthProvider.available()

        assert result is False, (
            f"ClerkAuthProvider.available() must return False when no Clerk config is "
            f"present (dark-by-default invariant) but got {result!r}."
        )


# ---------------------------------------------------------------------------
# CLK-4.3  Config-flag dark-by-default gate (available() preconditions)
# ---------------------------------------------------------------------------


class TestClerkDarkByDefault:
    """CLK-4.3: Config-flag dark-by-default gate for the Clerk provider.

    Covers all four branches of the available() precondition check plus
    the config.auth_provider() startup validation.  All tests run without
    any network access and without mutating the project foundry.yaml.
    """

    # ------------------------------------------------------------------
    # available() precondition branches
    # ------------------------------------------------------------------

    def test_available_false_when_frontend_api_missing(self):
        """available() returns False when clerk_frontend_api is absent/empty."""
        mock_cfg = MagicMock()
        mock_cfg.auth_clerk_frontend_api.return_value = ""
        mock_cfg.auth_clerk_outbound_internet_enabled.return_value = True  # would be ok alone

        with patch("research_foundry.config.FoundryConfig") as mock_fc_cls:
            mock_fc_cls.load.return_value = mock_cfg
            result = ClerkAuthProvider.available()

        assert result is False, (
            "available() must return False when clerk_frontend_api is empty, "
            f"even if outbound_internet_enabled=True.  Got {result!r}."
        )

    def test_available_false_when_outbound_not_enabled(self):
        """available() returns False when clerk_outbound_internet_enabled is False."""
        mock_cfg = MagicMock()
        mock_cfg.auth_clerk_frontend_api.return_value = "https://test.clerk.accounts.dev"
        mock_cfg.auth_clerk_outbound_internet_enabled.return_value = False  # explicit False

        with patch("research_foundry.config.FoundryConfig") as mock_fc_cls:
            mock_fc_cls.load.return_value = mock_cfg
            result = ClerkAuthProvider.available()

        assert result is False, (
            "available() must return False when clerk_outbound_internet_enabled=False, "
            f"even if clerk_frontend_api is set.  Got {result!r}."
        )

    def test_available_true_when_both_preconditions_met(self):
        """available() returns True only when both preconditions are explicitly satisfied."""
        mock_cfg = MagicMock()
        mock_cfg.auth_clerk_frontend_api.return_value = "https://test.clerk.accounts.dev"
        mock_cfg.auth_clerk_outbound_internet_enabled.return_value = True

        with patch("research_foundry.config.FoundryConfig") as mock_fc_cls:
            mock_fc_cls.load.return_value = mock_cfg
            result = ClerkAuthProvider.available()

        assert result is True, (
            "available() must return True when both clerk_frontend_api is non-empty "
            f"AND clerk_outbound_internet_enabled=True.  Got {result!r}."
        )

    def test_available_false_when_config_load_fails(self):
        """available() returns False (never raises) when config loading throws."""
        with patch("research_foundry.config.FoundryConfig") as mock_fc_cls:
            mock_fc_cls.load.side_effect = RuntimeError("simulated config load failure")
            result = ClerkAuthProvider.available()

        assert result is False, (
            "available() must return False (not raise) when FoundryConfig.load() "
            f"throws an exception.  Got {result!r}."
        )

    # ------------------------------------------------------------------
    # Startup validation in auth_provider() — not a silent pass
    # ------------------------------------------------------------------

    def test_startup_error_when_clerk_enabled_without_frontend_api(self):
        """auth_provider()=clerk + missing clerk_frontend_api raises a clear ValueError."""
        from research_foundry.config import FoundryConfig

        # Simulate: provider=clerk, but clerk_frontend_api absent (empty).
        with patch.object(FoundryConfig, "foundry", new_callable=PropertyMock) as mock_foundry:
            mock_foundry.return_value = {
                "auth": {
                    "provider": "clerk",
                    # clerk_frontend_api intentionally absent
                    "clerk_outbound_internet_enabled": True,
                }
            }
            mock_paths = MagicMock()
            cfg = FoundryConfig(paths=mock_paths)

            with pytest.raises(ValueError, match="Clerk provider requires"):
                cfg.auth_provider()

    def test_startup_error_when_clerk_enabled_without_outbound_flag(self):
        """auth_provider()=clerk + outbound_internet_enabled=False raises a clear ValueError."""
        from research_foundry.config import FoundryConfig

        # Simulate: provider=clerk, frontend_api set, but outbound flag absent/False.
        with patch.object(FoundryConfig, "foundry", new_callable=PropertyMock) as mock_foundry:
            mock_foundry.return_value = {
                "auth": {
                    "provider": "clerk",
                    "clerk_frontend_api": "https://test.clerk.accounts.dev",
                    # clerk_outbound_internet_enabled intentionally absent → defaults False
                }
            }
            mock_paths = MagicMock()
            cfg = FoundryConfig(paths=mock_paths)

            with pytest.raises(ValueError, match="Clerk provider requires"):
                cfg.auth_provider()

    def test_startup_error_message_is_actionable(self):
        """The startup error message tells the operator exactly what to set."""
        from research_foundry.config import FoundryConfig

        with patch.object(FoundryConfig, "foundry", new_callable=PropertyMock) as mock_foundry:
            mock_foundry.return_value = {"auth": {"provider": "clerk"}}
            mock_paths = MagicMock()
            cfg = FoundryConfig(paths=mock_paths)

            with pytest.raises(ValueError) as exc_info:
                cfg.auth_provider()

        msg = str(exc_info.value)
        assert "clerk_frontend_api" in msg, (
            f"Error message must mention 'clerk_frontend_api'; got: {msg!r}"
        )
        assert "clerk_outbound_internet_enabled" in msg, (
            f"Error message must mention 'clerk_outbound_internet_enabled'; got: {msg!r}"
        )

    # ------------------------------------------------------------------
    # Regression: non-Clerk providers are unaffected by the Clerk gate
    # ------------------------------------------------------------------

    def test_none_provider_unaffected_by_clerk_gate(self):
        """auth_provider()='none' works normally with no Clerk config present."""
        from research_foundry.config import FoundryConfig

        with patch.object(FoundryConfig, "foundry", new_callable=PropertyMock) as mock_foundry:
            mock_foundry.return_value = {}  # no auth block → defaults to "none"
            mock_paths = MagicMock()
            cfg = FoundryConfig(paths=mock_paths)

            result = cfg.auth_provider()

        assert result == "none", (
            f"auth_provider() should return 'none' when no auth block is configured, "
            f"got {result!r}."
        )

    def test_local_static_provider_unaffected_by_clerk_gate(self):
        """auth_provider()='local_static' works normally without triggering Clerk checks."""
        from research_foundry.config import FoundryConfig

        with patch.object(FoundryConfig, "foundry", new_callable=PropertyMock) as mock_foundry:
            mock_foundry.return_value = {"auth": {"provider": "local_static"}}
            mock_paths = MagicMock()
            cfg = FoundryConfig(paths=mock_paths)

            result = cfg.auth_provider()

        assert result == "local_static", (
            f"auth_provider() should return 'local_static' for local_static config, "
            f"got {result!r}."
        )


# ---------------------------------------------------------------------------
# CLK-4.2  Role mapping table (CLERK_ROLE_MAP)
# ---------------------------------------------------------------------------


class TestOrgRoleMappingTable:
    """CLK-4.2: Formalised CLERK_ROLE_MAP — explicit per-slug tests."""

    @pytest.mark.parametrize("clerk_slug,expected_rf_role", [
        ("org:owner", "owner"),
        ("org:admin", "admin"),
        ("org:member", "researcher"),
        ("org:reviewer", "reviewer"),
        ("org:viewer", "viewer"),
    ])
    def test_explicit_role_mapping(self, clerk_slug: str, expected_rf_role: str) -> None:
        """All 5 RF roles (owner/admin/researcher/reviewer/viewer) have an explicit mapping."""
        result = ClerkAuthProvider._map_org_role(clerk_slug)
        assert expected_rf_role in result, (
            f"Expected _map_org_role({clerk_slug!r}) to contain {expected_rf_role!r} "
            f"but got {result!r}. "
            "Every RF role must be reachable from a Clerk org slug."
        )

    @pytest.mark.parametrize("unknown_slug", [
        "org:superadmin",
        "org:god",
        "custom:role",
        "",
        "random_garbage",
        "ORG:OWNER",   # case-sensitive — must not match
    ])
    def test_unknown_slug_maps_to_viewer_not_elevated(self, unknown_slug: str) -> None:
        """Unknown/unrecognised Clerk role slug maps to 'viewer' (least-privilege).

        Must never raise, never return an elevated role (owner/admin).
        """
        result = ClerkAuthProvider._map_org_role(unknown_slug)
        assert result == ["viewer"], (
            f"Expected _map_org_role({unknown_slug!r}) == ['viewer'] (least-privilege) "
            f"but got {result!r}. "
            "Unknown slugs MUST fall back to viewer — never elevated."
        )
        assert "owner" not in result, (
            f"Unknown slug {unknown_slug!r} must never map to 'owner' but got {result!r}."
        )
        assert "admin" not in result, (
            f"Unknown slug {unknown_slug!r} must never map to 'admin' but got {result!r}."
        )

    @pytest.mark.parametrize("slug", [
        "org:owner",
        "org:admin",
        "org:member",
        "org:reviewer",
        "org:viewer",
        "unrecognised:slug",
    ])
    def test_mapping_result_is_list(self, slug: str) -> None:
        """_map_org_role must return a list for every input (not tuple, set, or other iterable)."""
        result = ClerkAuthProvider._map_org_role(slug)
        assert isinstance(result, list), (
            f"_map_org_role({slug!r}) must return a list but got {type(result).__name__!r}. "
            "AuthIdentity converts to tuple; the adapter returns a list by contract."
        )
        assert len(result) > 0, (
            f"_map_org_role({slug!r}) returned an empty list — must always have at least one role."
        )


# ---------------------------------------------------------------------------
# CLK-4.1-T10  Provider registry self-registration
# ---------------------------------------------------------------------------


class TestProviderRegistration:
    """CLK-4.1-T10: Importing the clerk module registers 'clerk' in the provider registry."""

    def test_clerk_registered_in_provider_registry(self):
        from research_foundry.api.auth.provider import get_provider

        provider = get_provider("clerk")
        assert provider is not None, (
            "Expected 'clerk' to be registered in the AuthProvider registry after import, "
            "but get_provider('clerk') returned None."
        )
        assert isinstance(provider, ClerkAuthProvider), (
            f"Expected a ClerkAuthProvider instance but got {type(provider)!r}."
        )
