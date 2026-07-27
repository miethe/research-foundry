"""Per-identity + per-route sliding-window rate limiter for the RF loopback API.

RATE-LIMIT HEADER CONTRACT (GATE-900)
======================================
This contract governs both the server-side emission (this file) and the
frontend resilience implementation (GATE-900, batch 3).  Both sides MUST
implement exactly these headers; changing a name or type here requires a
coordinated update on the frontend.

On every **allowed** request::

    X-RateLimit-Limit: <int>       # configured maximum requests per window
    X-RateLimit-Remaining: <int>   # requests remaining in the current window
    X-RateLimit-Reset: <int>       # UNIX timestamp (seconds) when the window
                                   # resets — i.e. when the oldest in-window
                                   # request expires and the count drops by 1.

On a **rate-limited** request (HTTP 429)::

    Retry-After: <int>             # seconds until the window resets (ceil)
    X-RateLimit-Limit: <int>       # configured maximum requests per window
    X-RateLimit-Remaining: 0
    X-RateLimit-Reset: <int>       # same semantics as the allowed-request header

Key scheme
----------
``(AuthIdentity.workspace_id, AuthIdentity.user_id, request.url.path)``

One user's burst NEVER throttles another user.  One endpoint's burst NEVER
throttles another endpoint for the same user.  ``workspace_id`` is part of
the key (F5, DI-1 delta re-audit MISSED-NEIGHBOR fix) so that if a
``user_id`` is ever reused across workspaces, two tenants never share a
counter bucket — the limiter must not rely on ``user_id`` being globally
unique.

Algorithm
---------
Sliding window via per-key :class:`collections.deque` of request timestamps
(float, UNIX seconds).  CPython's GIL serialises ``deque.append`` /
``deque.popleft`` for this single-writer, single-process pattern; no
explicit lock is needed.

Exempt paths
------------
- ``GET /health`` — always passes through (consistent with auth middleware
  invariant; liveness probes MUST remain reachable regardless of rate state).
- Requests where ``request.state.identity`` is absent — i.e. when
  ``auth_mode=none`` and no auth middleware is installed.  Exempting these
  prevents single-operator loopback deployments from being throttled when
  they have not enabled auth.  The rate limiter cannot key on identity if
  none exists, so the safe default is to pass through.

Configuration (``foundry.yaml``)
---------------------------------
::

    foundry:
      auth:
        rate_limit:
          enabled: true            # default true
          requests_per_window: 60  # default 60
          window_seconds: 60       # default 60

Defaults yield 60 requests/minute per ``(workspace_id, user_id, route)``
triple — 1 req/sec sustained without bursting.  Adjust per-deployment.

Middleware stack position
-------------------------
``RateLimitMiddleware`` is the **innermost** middleware (added to the app
*before* :class:`~research_foundry.api.middleware.auth.AuthProviderMiddleware`
in ``create_app``).  Because Starlette/FastAPI processes middleware in
reverse-insertion order, ``AuthProviderMiddleware`` runs first and sets
``request.state.identity``; ``RateLimitMiddleware`` then reads it.

Execution order (outermost → innermost)::

    CORS → allowlist → auth → rate-limit → handler
"""

from __future__ import annotations

import collections
import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Path exempted from all rate-limit checks — consistent with auth middleware.
_HEALTH_PATH = "/health"

# Type alias for per-key sliding-window bucket: deque of float timestamps.
_Bucket = collections.deque


class SlidingWindowRateLimiter:
    """In-process sliding-window rate limiter keyed on
    ``(workspace_id, user_id, route)``.

    Each ``(workspace_id, user_id, route)`` triple maintains a
    :class:`collections.deque` of request timestamps (UNIX seconds, float).
    ``workspace_id`` defaults to ``""`` when the caller does not pass one
    (F5, DI-1 delta re-audit: including it in the key closes a cross-tenant
    counter-sharing gap — without it, two identities with the same
    ``user_id`` in different workspaces would throttle each other even
    though the F5 override read is already correctly per-workspace).  On
    each :meth:`check` call:

    1. Evict expired entries from the left (older than ``now - window_seconds``).
    2. Compute ``reset_at``: the moment the oldest in-window entry expires.
    3. If ``len(bucket) >= requests_per_window`` → deny (return ``False``).
    4. Otherwise: append ``now``, return ``True``.

    Thread/concurrency safety
    -------------------------
    CPython's GIL serialises :class:`collections.deque` ``append`` /
    ``popleft`` in this single-interpreter, single-process context.  No
    explicit lock is required for the dict lookup + deque mutation pattern
    used here.

    The :meth:`check` method accepts an optional ``_now`` parameter for
    deterministic testing (eliminates ``time.time`` patching in unit tests).

    Args:
        requests_per_window: Maximum requests allowed within any rolling
            ``window_seconds``-wide window per ``(user_id, route)`` key.
            Must be >= 1.
        window_seconds: Width of the sliding window in seconds.  Must be >= 1.

    Raises:
        ValueError: If ``requests_per_window`` < 1 or ``window_seconds`` < 1.
    """

    def __init__(self, requests_per_window: int, window_seconds: int) -> None:
        if requests_per_window < 1:
            raise ValueError(
                f"requests_per_window must be >= 1, got {requests_per_window!r}"
            )
        if window_seconds < 1:
            raise ValueError(
                f"window_seconds must be >= 1, got {window_seconds!r}"
            )
        self._limit = requests_per_window
        self._window = window_seconds
        # Mapping (workspace_id, user_id, route) → deque[float] of request
        # timestamps.
        self._buckets: dict[tuple[str, str, str], _Bucket] = {}

    def check(
        self,
        user_id: str,
        route: str,
        _now: float | None = None,
        *,
        workspace_id: str | None = None,
        limit_override: int | None = None,
        window_override: int | None = None,
    ) -> tuple[bool, int, float]:
        """Check and (if allowed) record a request for
        ``(workspace_id, user_id, route)``.

        Args:
            user_id:         The authenticated user identifier.
            route:           The request path (``request.url.path``).
            _now:            Override for the current timestamp.  Pass a float
                             for deterministic unit tests; ``None`` (default)
                             uses :func:`time.time`.
            workspace_id:    The identity's workspace, included in the bucket
                             key (F5, DI-1 delta re-audit) so a ``user_id``
                             shared across workspaces never shares a counter.
                             ``None`` (default) is normalised to ``""`` —
                             callers that never pass it (e.g. the pre-F5
                             algorithm-level unit tests) keep a single shared
                             bucket per ``(user_id, route)``, unchanged.
            limit_override:  Override the configured ``requests_per_window``
                             for this check only.  ``None`` keeps
                             ``self._limit``.  Used by
                             :class:`RateLimitMiddleware` to apply in-memory
                             admin overrides without rebuilding the limiter.
            window_override: Override the configured ``window_seconds`` for
                             this check only.  ``None`` keeps
                             ``self._window``.

        Returns:
            A ``(allowed, remaining, reset_at)`` triple:

            ``allowed``
                ``True`` when the request is within budget; ``False`` when the
                caller should reject with HTTP 429.

            ``remaining``
                Requests remaining *after* this call within the current window.
                ``0`` when rejected (the over-budget request is not recorded).

            ``reset_at``
                UNIX timestamp (float, seconds) at which the *oldest*
                in-window request expires — i.e. when the count drops by one.
                When the bucket is empty after eviction (first-ever request),
                returns ``now + window_seconds``.
        """
        now = _now if _now is not None else time.time()
        effective_limit: int = limit_override if limit_override is not None else self._limit
        effective_window: int = window_override if window_override is not None else self._window

        key = (workspace_id or "", user_id, route)
        bucket: _Bucket = self._buckets.setdefault(key, collections.deque())

        # Evict timestamps outside the sliding window's left boundary.
        window_start = now - effective_window
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        # reset_at: when the oldest in-window entry expires.
        reset_at: float = bucket[0] + effective_window if bucket else now + effective_window

        if len(bucket) >= effective_limit:
            # Over budget — do NOT record this request.
            return False, 0, reset_at

        # Under budget — record and return updated remaining count.
        bucket.append(now)
        remaining = effective_limit - len(bucket)
        return True, remaining, reset_at


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces per-identity + per-route rate limits.

    Rate-limit key: ``(AuthIdentity.workspace_id, AuthIdentity.user_id,
    request.url.path)``.  This ensures one user's burst does NOT throttle
    another user, one endpoint's burst does NOT throttle other endpoints for
    the same user, and (F5, DI-1 delta re-audit) two identities that happen
    to share a ``user_id`` across different workspaces do NOT share a
    counter bucket either.

    **Exempt cases** (pass through unconditionally):

    - ``GET /health`` — liveness probe; always unauthenticated.
    - Requests where ``request.state.identity`` is absent — the auth
      middleware was not installed (``auth_mode=none`` deployment).  This
      keeps single-operator loopback deployments unthrottled.

    **Header contract** (GATE-900 — frontend resilience)

    Every *allowed* response carries::

        X-RateLimit-Limit: <int>       # configured maximum requests per window
        X-RateLimit-Remaining: <int>   # requests left in current window
        X-RateLimit-Reset: <int>       # UNIX timestamp when window resets

    A *rejected* response (HTTP 429) carries::

        Retry-After: <int>             # seconds until window resets (ceil ≥ 1)
        X-RateLimit-Limit: <int>       # configured maximum requests per window
        X-RateLimit-Remaining: 0
        X-RateLimit-Reset: <int>

    Args:
        app:                 The inner ASGI application.
        requests_per_window: Maximum requests per ``(workspace_id, user_id,
                             route)`` per window.  Default: 60.
        window_seconds:      Sliding window width in seconds.  Default: 60.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        requests_per_window: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self._limiter = SlidingWindowRateLimiter(requests_per_window, window_seconds)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # GET /health is always exempt.
        if request.url.path == _HEALTH_PATH:
            return await call_next(request)

        # auth_mode=none → no identity on request.state → exempt (cannot key).
        identity = getattr(request.state, "identity", None)
        if identity is None:
            return await call_next(request)

        user_id: str = identity.user_id
        route: str = request.url.path

        # Read runtime overrides set by PATCH /api/admin/rate-limit-config.
        # These are applied per-request so changes take effect immediately
        # without rebuilding the limiter or restarting the process.
        #
        # F5 (DI-1 delta re-audit): overrides are keyed by workspace_id — a
        # workspace-local admin's PATCH mutates only that workspace's own
        # bucket (see admin.py's update_rate_limit_config), so this reads
        # the bucket for the CURRENT request's own identity.workspace_id
        # only. A workspace-B admin's override can never change the
        # effective budget applied to a workspace-A request, and vice versa.
        _app_state = getattr(getattr(request, "app", None), "state", None)
        _overrides_by_workspace: dict = getattr(_app_state, "rate_limit_overrides", None) or {}
        _overrides: dict = _overrides_by_workspace.get(identity.workspace_id) or {}
        limit_override: int | None = _overrides.get("max_requests")
        window_override: int | None = _overrides.get("window_seconds")

        # Belt-and-suspenders: ignore any non-positive override that the admin
        # PATCH handler should already have blocked.  A zero or negative
        # max_requests would deny every request (availability break); a zero
        # or negative window_seconds corrupts the sliding-window semantics.
        if limit_override is not None and limit_override <= 0:
            logger.warning(
                "Ignoring invalid max_requests override %r from app.state "
                "(must be >= 1); using startup-configured limit",
                limit_override,
            )
            limit_override = None
        if window_override is not None and window_override <= 0:
            logger.warning(
                "Ignoring invalid window_seconds override %r from app.state "
                "(must be >= 1); using startup-configured window",
                window_override,
            )
            window_override = None

        # Effective limit for X-RateLimit-Limit header: override if present,
        # otherwise fall back to the startup-configured value.
        effective_limit: int = (
            limit_override if limit_override is not None else self._limiter._limit
        )

        allowed, remaining, reset_at = self._limiter.check(
            user_id,
            route,
            workspace_id=identity.workspace_id,
            limit_override=limit_override,
            window_override=window_override,
        )
        reset_at_int = int(reset_at)

        if not allowed:
            retry_after = max(1, reset_at_int - int(time.time()))
            logger.warning(
                "Rate limit exceeded: user_id=%r route=%r retry_after=%d",
                user_id,
                route,
                retry_after,
            )
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(effective_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at_int),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(effective_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at_int)
        return response


__all__ = ["SlidingWindowRateLimiter", "RateLimitMiddleware"]
