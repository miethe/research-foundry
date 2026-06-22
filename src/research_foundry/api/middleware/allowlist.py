"""IP allowlist middleware for the RF loopback API.

When ``viewer.allowlist`` is non-empty, only requests from listed IP addresses
are accepted.  All other clients receive ``HTTP 403``.

The middleware is only added to the app when the allowlist is non-empty (the
caller, ``create_app``, is responsible for this gate).  When the allowlist is
empty, no middleware is added and all IPs are allowed.

Middleware stack position: after CORS, before auth.  This order ensures:
  - CORS preflight requests from browsers are handled before the IP check.
  - Unlisted IPs are rejected before the (more expensive) token comparison.
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class IPAllowlistMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces an IP allowlist.

    Only instantiate and add this middleware when the allowlist is non-empty.
    ``create_app`` is responsible for that gate.

    Args:
        app:       The inner ASGI application.
        allowlist: A non-empty sequence of permitted client IP strings.
                   Entries are matched exactly against ``request.client.host``.
                   Typical values: ``["127.0.0.1", "192.168.1.42"]``.
    """

    def __init__(self, app: ASGIApp, *, allowlist: list[str]) -> None:
        super().__init__(app)
        # Store as a frozenset for O(1) membership testing.
        self._allowed: frozenset[str] = frozenset(allowlist)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_host = request.client.host if request.client else None
        if client_host is None or client_host not in self._allowed:
            return JSONResponse(
                {"detail": "IP not in allowlist"},
                status_code=403,
            )
        return await call_next(request)


__all__ = ["IPAllowlistMiddleware"]
