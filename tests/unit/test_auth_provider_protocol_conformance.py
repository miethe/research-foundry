"""Parametrized Protocol conformance tests for all AuthProvider adapters.

CLK-4.4: Cross-check that local_static, clerk, and oidc all satisfy the
AuthProvider Protocol defined in api/auth/provider.py.

These tests assert STRUCTURAL conformance only — they do not exercise
authentication logic (CLK-4.1/CLK-4.2 cover behaviour).

Test coverage:
  CONF-01  isinstance() check: all three adapters are AuthProvider instances
  CONF-02  id attribute is a non-empty string on each adapter
  CONF-03  authenticate() method exists and is callable on each adapter
  CONF-04  authenticate() signature exposes a 'request' parameter
  CONF-05  authenticate() return annotation is AuthIdentity | None
  CONF-06  available() method exists and is callable on each adapter
  CONF-07  Registry sweep: every registered provider satisfies the Protocol
  CONF-08  local_static is registered and conforming
  CONF-09  clerk is registered and conforming
  CONF-10  oidc is NOT registered (xfail — documents what oidc.py needs)
  CONF-11  oidc.authenticate() raises NotImplementedError (stub behaviour)

Invariant — FAIL LOUDLY:
  Any adapter registered in the provider registry that does NOT satisfy the
  AuthProvider Protocol is caught by CONF-07 at test-collection time.
"""

from __future__ import annotations

import inspect
import typing

import pytest

# Importing the adapter modules triggers their self-registration side-effects.
# local_static registers LocalStaticAuthProvider(token_configs=[]).
# clerk registers a sentinel ClerkAuthProvider instance.
# oidc explicitly does NOT register (see module docstring and CONF-10 below).
from research_foundry.api.auth.adapters.clerk import ClerkAuthProvider
from research_foundry.api.auth.adapters.local_static import LocalStaticAuthProvider
from research_foundry.api.auth.adapters.oidc import OidcAuthProvider
from research_foundry.api.auth.provider import (
    AuthIdentity,
    AuthProvider,
    all_providers,
    get_provider,
)

# ---------------------------------------------------------------------------
# Shared adapter instances (created once, reused across all parametrized tests)
# ---------------------------------------------------------------------------

# local_static: zero-token config is valid at construction (no rbac bootstrap).
_LOCAL_STATIC = LocalStaticAuthProvider(token_configs=[])

# clerk: sentinel URL is acceptable for structural conformance tests — no
# network calls are made because authenticate() is never invoked here.
_CLERK = ClerkAuthProvider(frontend_api_url="https://conformance-test.clerk.accounts.dev")

# oidc: structural stub; all methods either raise or return sentinel values.
_OIDC = OidcAuthProvider()


ADAPTERS = [
    pytest.param(_LOCAL_STATIC, id="local_static"),
    pytest.param(_CLERK, id="clerk"),
    pytest.param(_OIDC, id="oidc"),
]

# ---------------------------------------------------------------------------
# CONF-01 — isinstance() (runtime_checkable Protocol)
# ---------------------------------------------------------------------------


class TestProtocolInstanceCheck:
    """AuthProvider is @runtime_checkable — isinstance() must pass for all adapters."""

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_isinstance_auth_provider(self, adapter: object) -> None:
        """CONF-01: adapter satisfies the runtime_checkable AuthProvider Protocol."""
        assert isinstance(adapter, AuthProvider), (
            f"{type(adapter).__name__} does not satisfy the AuthProvider Protocol. "
            "Ensure it exposes: id (str), authenticate(request) -> AuthIdentity | None, "
            "and available() -> bool."
        )


# ---------------------------------------------------------------------------
# CONF-02 to CONF-06 — individual attribute / method conformance
# ---------------------------------------------------------------------------


class TestAuthenticateMethodConformance:
    """Structural checks on the authenticate() method signature."""

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_id_is_non_empty_string(self, adapter: object) -> None:
        """CONF-02: id attribute is a non-empty string."""
        assert hasattr(adapter, "id"), (
            f"{type(adapter).__name__} is missing 'id' attribute."
        )
        assert isinstance(adapter.id, str), (  # type: ignore[union-attr]
            f"{type(adapter).__name__}.id must be a str, "
            f"got {type(adapter.id).__name__!r}."  # type: ignore[union-attr]
        )
        assert adapter.id, (  # type: ignore[union-attr]
            f"{type(adapter).__name__}.id must be non-empty."
        )

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_authenticate_is_callable(self, adapter: object) -> None:
        """CONF-03: authenticate() exists and is callable."""
        assert hasattr(adapter, "authenticate"), (
            f"{type(adapter).__name__} is missing 'authenticate' method."
        )
        assert callable(getattr(adapter, "authenticate")), (
            f"{type(adapter).__name__}.authenticate must be callable."
        )

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_authenticate_accepts_request_parameter(self, adapter: object) -> None:
        """CONF-04: authenticate() signature includes a 'request' parameter."""
        sig = inspect.signature(getattr(adapter, "authenticate"))
        assert "request" in sig.parameters, (
            f"{type(adapter).__name__}.authenticate() is missing 'request' parameter. "
            f"Found parameters: {list(sig.parameters.keys())}. "
            "Protocol requires: authenticate(self, request: Request) -> AuthIdentity | None."
        )

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_authenticate_return_annotation_is_auth_identity_or_none(
        self, adapter: object
    ) -> None:
        """CONF-05: authenticate() return annotation is AuthIdentity | None.

        Uses typing.get_type_hints() to evaluate lazy string annotations
        (from __future__ import annotations) into live types, then asserts
        both AuthIdentity and NoneType appear in the union args.
        """
        method = getattr(type(adapter), "authenticate")
        try:
            hints = typing.get_type_hints(method)
        except Exception as exc:
            pytest.fail(
                f"typing.get_type_hints({type(adapter).__name__}.authenticate) raised "
                f"{type(exc).__name__}: {exc}. "
                "Ensure return annotation is present and resolvable."
            )

        return_hint = hints.get("return")
        assert return_hint is not None, (
            f"{type(adapter).__name__}.authenticate() has no return annotation. "
            "Protocol requires: -> AuthIdentity | None."
        )

        # Unwrap Union / Optional args and check both AuthIdentity and NoneType present.
        union_args = typing.get_args(return_hint)
        assert union_args, (
            f"{type(adapter).__name__}.authenticate() return annotation {return_hint!r} "
            "is not a Union/Optional type. "
            "Expected: AuthIdentity | None (or Optional[AuthIdentity])."
        )
        assert AuthIdentity in union_args, (
            f"{type(adapter).__name__}.authenticate() return annotation {return_hint!r} "
            "does not include AuthIdentity. "
            "Protocol requires: -> AuthIdentity | None."
        )
        assert type(None) in union_args, (
            f"{type(adapter).__name__}.authenticate() return annotation {return_hint!r} "
            "does not include NoneType. "
            "Protocol requires: -> AuthIdentity | None (None return is the "
            "'no valid credential' signal, never an exception)."
        )

    @pytest.mark.parametrize("adapter", ADAPTERS)
    def test_available_is_callable(self, adapter: object) -> None:
        """CONF-06: available() exists and is callable."""
        assert hasattr(adapter, "available"), (
            f"{type(adapter).__name__} is missing 'available' method."
        )
        assert callable(getattr(adapter, "available")), (
            f"{type(adapter).__name__}.available must be callable."
        )


# ---------------------------------------------------------------------------
# CONF-07 — Registry sweep (fail-loudly invariant)
# ---------------------------------------------------------------------------


class TestRegistrySweep:
    """Every provider registered in the module-level registry must satisfy the Protocol.

    This test catches any future adapter that is registered without proper
    Protocol conformance — it fails at assertion time, not silently.
    """

    def test_all_registered_providers_satisfy_protocol(self) -> None:
        """CONF-07: every entry in the provider registry is an AuthProvider instance."""
        registry = all_providers()
        assert registry, (
            "Provider registry is empty. "
            "At minimum, local_static and clerk should be registered after import."
        )

        violations: list[str] = []
        for name, provider in registry.items():
            if not isinstance(provider, AuthProvider):
                violations.append(
                    f"  {name!r}: {type(provider).__name__} does not satisfy AuthProvider Protocol"
                )

        assert not violations, (
            "The following registered providers do NOT satisfy the AuthProvider Protocol:\n"
            + "\n".join(violations)
            + "\n\nAll providers registered via register_provider() MUST expose: "
            "id (str), authenticate(request) -> AuthIdentity | None, available() -> bool."
        )


# ---------------------------------------------------------------------------
# CONF-08 / CONF-09 — Named registry entries
# ---------------------------------------------------------------------------


class TestNamedRegistryEntries:
    """Check that expected adapter names are present (or absent) in the registry."""

    def test_local_static_is_registered(self) -> None:
        """CONF-08: get_provider('local_static') returns a conforming AuthProvider instance."""
        provider = get_provider("local_static")
        assert provider is not None, (
            "get_provider('local_static') returned None. "
            "Importing research_foundry.api.auth.adapters.local_static should "
            "self-register a LocalStaticAuthProvider via register_provider()."
        )
        assert isinstance(provider, AuthProvider), (
            f"Registered 'local_static' provider ({type(provider).__name__}) does not "
            "satisfy the AuthProvider Protocol."
        )

    def test_clerk_is_registered(self) -> None:
        """CONF-09: get_provider('clerk') returns a conforming AuthProvider instance."""
        provider = get_provider("clerk")
        assert provider is not None, (
            "get_provider('clerk') returned None. "
            "Importing research_foundry.api.auth.adapters.clerk should "
            "self-register a ClerkAuthProvider sentinel via register_provider()."
        )
        assert isinstance(provider, AuthProvider), (
            f"Registered 'clerk' provider ({type(provider).__name__}) does not "
            "satisfy the AuthProvider Protocol."
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "oidc.py is intentionally a Protocol-conformance stub (FU-2). "
            "Its module docstring explicitly states: "
            "'DO NOT call register_provider() here' to avoid a silent broken-config "
            "state when auth.provider=oidc is set in foundry.yaml. "
            "AUTH-104 owns the config-validation gate that surfaces the actionable error. "
            "\n\n"
            "What oidc.py needs to pass this test: "
            "(1) Implement functional JWKS/OIDC discovery in authenticate(). "
            "(2) Remove the unconditional NotImplementedError. "
            "(3) Call register_provider(OidcAuthProvider()) at module level. "
            "This work is tracked as FU-2."
        ),
    )
    def test_oidc_is_registered(self) -> None:
        """CONF-10 (xfail): get_provider('oidc') is None until FU-2 implements the adapter.

        This test is marked xfail/strict so that it:
        - Currently XFAILs (expected) — oidc is not registered.
        - Becomes XPASS (unexpected, surfaced as an error) when oidc.py is
          implemented and registers itself, prompting removal of this xfail marker.
        """
        provider = get_provider("oidc")
        assert provider is not None, (
            "get_provider('oidc') returned None — oidc is not yet registered."
        )
        assert isinstance(provider, AuthProvider)


# ---------------------------------------------------------------------------
# CONF-11 — oidc stub behaviour documentation
# ---------------------------------------------------------------------------


class TestOidcStubBehavior:
    """Document the oidc stub's non-functional behaviour.

    OidcAuthProvider satisfies the Protocol structurally (isinstance passes)
    but raises NotImplementedError from authenticate() by design.  These tests
    pin that contract so a future implementor knows exactly what must change.
    """

    def test_oidc_available_returns_false(self) -> None:
        """CONF-11a: OidcAuthProvider.available() returns False (stub is not operational)."""
        provider = OidcAuthProvider()
        result = provider.available()
        assert result is False, (
            "OidcAuthProvider.available() must return False until FU-2 is implemented. "
            f"Got: {result!r}."
        )

    def test_oidc_authenticate_raises_not_implemented(self) -> None:
        """CONF-11b: OidcAuthProvider.authenticate() raises NotImplementedError.

        This is expected stub behaviour.  A correctly-configured deployment
        must never call this method — AUTH-104's validation gate rejects
        auth.provider=oidc before any request reaches the adapter.

        When FU-2 is implemented, this test should be REMOVED (or converted
        to a test that verifies authenticate() returns AuthIdentity | None).
        """
        from unittest.mock import MagicMock

        provider = OidcAuthProvider()
        mock_request = MagicMock()

        with pytest.raises(NotImplementedError, match="OidcAuthProvider is not yet implemented"):
            provider.authenticate(mock_request)
