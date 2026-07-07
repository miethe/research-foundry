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
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ..auth.provider import AuthProvider

logger = logging.getLogger(__name__)

# Path exempted from all auth checks — liveness probe must always be reachable.
_HEALTH_PATH = "/health"


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
    """Registry-based auth middleware for the RF loopback API (P5.1).

    Delegates authentication to a registered
    :class:`~research_foundry.api.auth.provider.AuthProvider`.  Only
    instantiate when ``auth.provider != "none"`` — ``create_app`` is
    responsible for that guard (security invariant: a ``None`` provider means
    zero middleware is added, not a middleware that passes all requests through
    unconditionally).

    Middleware ordering (outermost → innermost): CORS → allowlist → auth.
    Auth is innermost so it only runs after IP filtering has already passed.

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
    """

    def __init__(self, app: ASGIApp, *, provider: AuthProvider) -> None:
        super().__init__(app)
        self._provider = provider

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # GET /health is always unauthenticated (security invariant 1).
        if request.url.path == _HEALTH_PATH:
            return await call_next(request)

        identity = self._provider.authenticate(request)
        if identity is None:
            # Return a generic 401 — do not leak provider name or token detail
            # (security invariant 3).
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        # Attach the resolved identity to request state for downstream
        # consumers (e.g. require_role dependency introduced in P5.2).
        request.state.identity = identity
        return await call_next(request)


__all__ = ["TokenAuthMiddleware", "AuthProviderMiddleware"]
