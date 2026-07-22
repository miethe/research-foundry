"""Bearer-token authentication middleware for the RF loopback API.

AUTH-HEADER CONTRACT (P4-SEAM)
================================
This contract governs both the server-side check (this file) and the
frontend ``loopbackGet()`` implementation in
``frontend/runs-viewer/src/api/client.ts`` (implemented in Phase P5).

Server side (this module):
  - When ``auth_mode == "token"``:
      - Expects the header ``Authorization: Bearer <token>``
      - Reads the expected token from ``os.environ[auth_token_env]``
      - Compares via ``hmac.compare_digest`` (constant-time; no timing leak)
      - Returns ``HTTP 401`` for missing or invalid header
      - ``GET /health`` is ALWAYS exempted — 200 regardless of auth_mode
  - When ``auth_mode != "token"`` (i.e. "none"):
      - Middleware is NOT added to the app at all (invariant 6 — true no-op)

Client side (loopbackGet in client.ts — implemented in P5):
  - When ``VITE_RUNS_LOOPBACK_API_TOKEN`` is set and non-empty:
      - MUST send ``Authorization: Bearer ${VITE_RUNS_LOOPBACK_API_TOKEN}``
      - Token value is injected at Vite build time (never at runtime from JS)
  - When ``VITE_RUNS_LOOPBACK_API_TOKEN`` is absent or empty:
      - The ``Authorization`` header MUST be omitted entirely
      - MUST NOT send ``Authorization: Bearer `` (empty string after "Bearer ")
  - On ``HTTP 401`` from the server:
      - Surface the error via ``ClientError`` — do NOT silently swallow it

Security invariants upheld by this module:
  1. ``hmac.compare_digest`` exclusively — never ``==``
  2. No token value appears in any log line, error message, or stack trace
  3. ``GET /health`` is always unauthenticated
  4. Middleware is only added to the app when ``auth_mode == "token"``
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from research_foundry.paths import FoundryPaths
from research_foundry.services import token_service

from ..auth.provider import AuthIdentity, AuthProvider

logger = logging.getLogger(__name__)

# Path exempted from all auth checks — liveness probe must always be reachable.
_HEALTH_PATH = "/health"

# Prefix for the share-token resolution endpoint.
# GET /api/reports/shares/{share_token} is publicly accessible — the token IS
# the credential; sensitivity is re-checked inside the resolver (PRD AC-2).
# All other /api/reports/* routes remain fully auth-gated.
_SHARE_TOKEN_PATH_PREFIX = "/api/reports/shares/"


# DEPRECATED: superseded by AuthProviderMiddleware in P5.1; remove in P5.2.
class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that validates ``Authorization: Bearer <token>``.

    Only instantiate and add this middleware to the app when
    ``auth_mode == "token"``; the caller (``create_app``) is responsible for
    that gate (security invariant 6 — auth_mode==none is a true no-op, not
    a middleware that passes all requests).

    Args:
        app:           The inner ASGI application.
        token_env_var: Name of the environment variable holding the expected
                       token.  The variable is read at request time (not at
                       construction) so that process-level env changes take
                       effect without a restart.  The *name* of the variable
                       is safe to store; the *value* is never stored or logged.
    """

    def __init__(self, app: ASGIApp, *, token_env_var: str) -> None:
        super().__init__(app)
        self._token_env_var = token_env_var

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # GET /health is always unauthenticated (security invariant 5).
        if request.url.path == _HEALTH_PATH:
            return await call_next(request)

        # Read the Authorization header.
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Authorization header missing or not Bearer"},
                status_code=401,
            )

        # Extract the supplied token after "Bearer ".
        supplied = auth_header[len("Bearer "):]
        if not supplied:
            return JSONResponse(
                {"detail": "Bearer token is empty"},
                status_code=401,
            )

        # Read the expected token from the environment at request time.
        # SECURITY: never log the value of either supplied or expected.
        expected = os.environ.get(self._token_env_var, "")
        if not expected:
            # Token env var disappeared at runtime — fail closed.
            logger.warning(
                "Auth token env var %r is unset at request time; rejecting.",
                self._token_env_var,
            )
            return JSONResponse(
                {"detail": "Server auth token not configured"},
                status_code=401,
            )

        # Constant-time comparison — security invariant 3.
        if not hmac.compare_digest(
            supplied.encode("utf-8"),
            expected.encode("utf-8"),
        ):
            return JSONResponse(
                {"detail": "Invalid token"},
                status_code=401,
            )

        return await call_next(request)


class AuthProviderMiddleware(BaseHTTPMiddleware):
    """Registry-based auth middleware for the RF loopback API (P5.1; composite
    chain added in public-multiuser Phase 2, ACT-203).

    Delegates authentication to a registered
    :class:`~research_foundry.api.auth.provider.AuthProvider`.  Only
    instantiate when ``auth.provider != "none"`` — ``create_app`` is
    responsible for that guard (security invariant: a ``None`` provider means
    zero middleware is added, not a middleware that passes all requests through
    unconditionally).

    Middleware ordering (outermost → innermost): CORS → allowlist → auth.
    Auth is innermost so it only runs after IP filtering has already passed.

    Composite auth chain (ACT-203, FR-11)
    --------------------------------------
    Every Bearer credential is checked against the ``access_tokens`` store
    (via :func:`~research_foundry.services.token_service.verify_token`)
    BEFORE the configured provider adapter runs:

      * Token-store HIT  → resolve identity directly from the token row; the
        provider adapter (Clerk, local_static, ...) is never invoked for this
        request.
      * Token-store MISS (including a malformed/absent header, or a
        genuinely unrecognized/expired/revoked token) → fall through
        unchanged to ``self._provider.authenticate(request)``, exactly as
        before ACT-203.

    This lets machine tokens and human provider sessions (e.g. Clerk JWTs)
    coexist without introducing a new ``auth.provider`` enum value — the
    token-store check is a chain link in front of whichever provider is
    configured, not a provider itself.  ``self._paths`` is ``None`` in any
    test/construction path that predates ACT-203 (or that deliberately
    opts out); the chain link is a no-op in that case and behavior is
    byte-identical to the pre-ACT-203 provider-only path.

    Security invariants
    -------------------
    1. ``GET /health`` is always unauthenticated — consistent with the legacy
       :class:`TokenAuthMiddleware` contract and required for liveness probes.
    2. ``request.state.identity`` is set only on authenticated requests.
       Routes and dependencies that require authentication must check
       ``getattr(request.state, "identity", None)`` — ``None`` means either
       "no provider configured" or "provider rejected this request" depending
       on whether middleware was added at all.
    3. A generic ``{"detail": "Unauthorized"}`` 401 is returned on failure.
       No provider name, token detail, or diagnostic information is included
       to avoid leaking adapter topology to unauthenticated callers.
    4. (ACT-203) A token-store lookup failure of ANY kind — including an
       unexpected exception from ``token_service.verify_token`` — degrades
       to "no match" and falls through to the provider adapter.  It never
       propagates as a 500 (AC-4 resilience).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        provider: AuthProvider,
        paths: Optional[FoundryPaths] = None,
    ) -> None:
        super().__init__(app)
        self._provider = provider
        self._paths = paths

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # GET /health is always unauthenticated (security invariant 1).
        if request.url.path == _HEALTH_PATH:
            return await call_next(request)

        # Share token is the credential; sensitivity re-check happens inside
        # the resolver (PRD AC-2).  This exemption is PRECISELY scoped:
        #   - only GET (not POST/PATCH/DELETE)
        #   - only the /api/reports/shares/{token} path (token must be non-empty)
        #   - all other /api/reports/* routes still require session auth
        if (
            request.method == "GET"
            and request.url.path.startswith(_SHARE_TOKEN_PATH_PREFIX)
            and len(request.url.path) > len(_SHARE_TOKEN_PATH_PREFIX)
        ):
            return await call_next(request)

        identity = self._authenticate(request)
        if identity is None:
            # Return a generic 401 — do not leak provider name or token detail
            # (security invariant 3).
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        # Attach the resolved identity to request state for downstream
        # consumers (e.g. require_role dependency introduced in P5.2).
        request.state.identity = identity
        return await call_next(request)

    def _authenticate(self, request: Request) -> Optional[AuthIdentity]:
        """Resolve an identity: token-store first, provider fallthrough (ACT-203)."""
        if self._paths is not None:
            # Pass the narrowed `self._paths` as an argument (rather than
            # re-reading `self._paths` inside `_resolve_token_identity`) so
            # the None-check above is visible to static type checking too.
            token_identity = self._resolve_token_identity(request, self._paths)
            if token_identity is not None:
                return token_identity
        return self._provider.authenticate(request)

    def _resolve_token_identity(
        self, request: Request, paths: FoundryPaths
    ) -> Optional[AuthIdentity]:
        """Check the Bearer credential against the access_tokens store.

        Returns ``None`` (never raises) for: no/malformed Authorization
        header, an empty Bearer value, or any ``token_service.verify_token``
        outcome that is not a hit (unrecognized/expired/revoked token, or an
        unexpected exception from the token-store lookup itself — security
        invariant 4 above).
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        supplied = auth_header[len("Bearer "):]
        if not supplied:
            return None

        try:
            resolved = token_service.verify_token(paths, supplied)
        except Exception:  # noqa: BLE001 — fail-soft: never let a token-store
            # bug turn into a 500; fall through to the provider adapter instead.
            logger.warning(
                "AuthProviderMiddleware: token_service.verify_token raised; "
                "falling through to the configured provider adapter.",
                exc_info=True,
            )
            return None

        if resolved is None:
            return None

        return AuthIdentity(
            user_id=resolved.principal_id,
            workspace_id=resolved.workspace_id,
            roles=(resolved.role,),
        )


__all__ = ["TokenAuthMiddleware", "AuthProviderMiddleware"]
