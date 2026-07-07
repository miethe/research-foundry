"""OIDC / BYO auth adapter — Protocol-conformance stub only.

This module defines :class:`OidcAuthProvider` as a structural stub that
satisfies the :class:`~research_foundry.api.auth.provider.AuthProvider`
Protocol (``isinstance`` check passes) but is **not functional**.

Implementation is deferred to FU-2.  This stub exists solely to:

* Reserve the ``"oidc"`` provider ``id`` in the adapter namespace.
* Allow AUTH-104 to produce a clear config-validation error when
  ``auth.provider: oidc`` is set in ``foundry.yaml``, rather than a
  confusing ``KeyError`` from an absent registry entry.
* Document the intended Protocol shape for the future implementor.

DO NOT call :func:`~research_foundry.api.auth.provider.register_provider`
here.  Registering an ``available() == False`` provider would allow
``foundry.yaml`` to select it accidentally and produce a silent broken
state.  AUTH-104 owns the validation gate that surfaces the actionable
error.
"""

from __future__ import annotations

from starlette.requests import Request

from research_foundry.api.auth.provider import AuthIdentity, AuthProvider  # noqa: F401


class OidcAuthProvider:
    """Structural stub conforming to :class:`AuthProvider`.

    All methods raise :exc:`NotImplementedError` or return sentinel values
    that signal non-availability.  No JWKS fetching, no OIDC discovery,
    no token validation — all deferred to FU-2.
    """

    id: str = "oidc"

    def available(self) -> bool:
        """Always returns ``False``; this stub is not operational."""
        return False

    def authenticate(self, request: Request) -> AuthIdentity | None:
        """Raises :exc:`NotImplementedError` unconditionally.

        This method must never be reached in a correctly configured
        deployment.  If it is reached, AUTH-104's config-validation gate
        failed to reject the ``oidc`` provider selection.

        Raises
        ------
        NotImplementedError
            Always.  The caller should configure ``auth.provider`` to
            ``none`` or ``local_static``.
        """
        raise NotImplementedError(
            "OidcAuthProvider is not yet implemented. "
            "This is a Protocol-conformance stub for FU-2. "
            "Set auth.provider to 'none' or 'local_static'."
        )


# Structural Protocol conformance assertion (evaluated at import time in
# test/dev environments; stripped by the optimiser in production builds).
assert isinstance(OidcAuthProvider(), AuthProvider), (
    "OidcAuthProvider must satisfy the AuthProvider Protocol — "
    "check that id, authenticate, and available are all present."
)


__all__ = ["OidcAuthProvider"]
