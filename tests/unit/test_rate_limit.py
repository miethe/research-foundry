"""Unit tests for the sliding-window rate-limit middleware (P5.6 / FR-9).

Test catalogue
--------------
SlidingWindowRateLimiter (algorithm-level unit tests)
  SW-01  Requests within budget are allowed
  SW-02  Request exceeding budget is denied (429 path)
  SW-03  ``remaining`` counts down correctly per allowed request
  SW-04  Per-identity key isolation: alice's burst does not block bob
  SW-05  Per-route key isolation: /route_a exhaustion does not block /route_b
  SW-06  Window reset: timestamps older than window_seconds are evicted
  SW-07  ``reset_at`` accuracy: oldest_timestamp + window_seconds
  SW-08  Invalid constructor args raise ValueError

RateLimitMiddleware (ASGI/HTTP integration tests via TestClient)
  MW-01  Requests within budget return 200
  MW-02  Request exceeding budget returns 429
  MW-03  429 response includes Retry-After header (int, 1 ≤ value ≤ window)
  MW-04  429 response includes X-RateLimit-Remaining: 0
  MW-05  429 response includes X-RateLimit-Reset header (int)
  MW-06  Allowed response includes X-RateLimit-Remaining (non-negative int)
  MW-07  Allowed response includes X-RateLimit-Reset (int)
  MW-08  Per-identity isolation at middleware level (alice burst ≠ throttle bob)
  MW-09  GET /health is always exempt, even after budget exhausted
  MW-10  No identity on request.state (auth_mode=none) → exempt, passes through
  MW-11  Retry-After value is within expected window range
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.middleware.rate_limit import (
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_app(
    requests_per_window: int = 3,
    window_seconds: int = 60,
) -> FastAPI:
    """Build a minimal FastAPI app with RateLimitMiddleware.

    Rate limit is the innermost middleware (added first).  A
    ``DynamicIdentityMiddleware`` is added second (runs first = outer) and
    reads the ``X-Test-User-ID`` request header to populate
    ``request.state.identity``.  Requests without that header have no
    identity and are exempt from rate limiting (auth_mode=none semantics).
    """
    app = FastAPI()

    class _DynamicIdentityMiddleware(BaseHTTPMiddleware):
        """Test-only middleware: reads identity from X-Test-User-ID header."""

        def __init__(self, inner: ASGIApp) -> None:
            super().__init__(inner)

        async def dispatch(self, request: Request, call_next):
            user_id = request.headers.get("X-Test-User-ID")
            if user_id:
                request.state.identity = AuthIdentity(
                    user_id=user_id,
                    workspace_id="default",
                    roles=("researcher",),
                )
            return await call_next(request)

    # Add rate-limit FIRST (innermost) then identity SECOND (outer).
    # Execution order: identity → rate-limit → handler.
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
    )
    app.add_middleware(_DynamicIdentityMiddleware)

    @app.get("/api/test")
    def test_route() -> dict:
        return {"ok": True}

    @app.get("/api/other")
    def other_route() -> dict:
        return {"ok": True}

    @app.get("/health")
    def health_route() -> dict:
        return {"status": "ok"}

    return app


def _client(app: FastAPI) -> TestClient:
    """Return a TestClient that does NOT follow redirects."""
    return TestClient(app, raise_server_exceptions=True)


def _as(user_id: str) -> dict[str, str]:
    """Build the identity header dict for a given user."""
    return {"X-Test-User-ID": user_id}


# ---------------------------------------------------------------------------
# SlidingWindowRateLimiter — algorithm-level unit tests
# ---------------------------------------------------------------------------


class TestSlidingWindowRateLimiter:
    """SW-01 through SW-08: pure algorithm tests using the _now injection hook."""

    def test_sw01_allows_requests_within_budget(self) -> None:
        """SW-01: first N requests are allowed when N == requests_per_window."""
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        now = 1_000.0
        for i in range(3):
            allowed, _, _ = limiter.check("alice", "/api/test", _now=now + i)
            assert allowed, f"Request {i + 1} should be allowed but was denied"

    def test_sw02_blocks_over_budget(self) -> None:
        """SW-02: the (N+1)th request is denied."""
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        for i in range(3):
            limiter.check("alice", "/api/test", _now=1_000.0 + i)
        allowed, remaining, _ = limiter.check("alice", "/api/test", _now=1_003.0)
        assert not allowed
        assert remaining == 0

    def test_sw03_remaining_counts_down(self) -> None:
        """SW-03: remaining decrements by 1 per allowed request."""
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        _, rem, _ = limiter.check("alice", "/api/test", _now=1_000.0)
        assert rem == 2
        _, rem, _ = limiter.check("alice", "/api/test", _now=1_001.0)
        assert rem == 1
        _, rem, _ = limiter.check("alice", "/api/test", _now=1_002.0)
        assert rem == 0

    def test_sw04_per_identity_isolation(self) -> None:
        """SW-04: alice's exhaustion does not affect bob's budget."""
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=60)
        limiter.check("alice", "/api/test", _now=1_000.0)
        limiter.check("alice", "/api/test", _now=1_001.0)
        alice_allowed, _, _ = limiter.check("alice", "/api/test", _now=1_002.0)
        bob_allowed, _, _ = limiter.check("bob", "/api/test", _now=1_002.0)
        assert not alice_allowed
        assert bob_allowed

    def test_sw05_per_route_isolation(self) -> None:
        """SW-05: /route_a exhaustion does not affect /route_b for the same user."""
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=60)
        limiter.check("alice", "/api/route_a", _now=1_000.0)
        limiter.check("alice", "/api/route_a", _now=1_001.0)
        a_allowed, _, _ = limiter.check("alice", "/api/route_a", _now=1_002.0)
        b_allowed, _, _ = limiter.check("alice", "/api/route_b", _now=1_002.0)
        assert not a_allowed
        assert b_allowed

    def test_sw06_window_reset_after_expiry(self) -> None:
        """SW-06: timestamps older than window_seconds are evicted; budget resets."""
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=10)
        # Exhaust at t=0
        limiter.check("alice", "/api/test", _now=0.0)
        limiter.check("alice", "/api/test", _now=0.0)
        denied, _, _ = limiter.check("alice", "/api/test", _now=0.0)
        assert not denied

        # At t=11 the window has slid past both t=0 timestamps.
        allowed, remaining, _ = limiter.check("alice", "/api/test", _now=11.0)
        assert allowed
        assert remaining == 1  # one slot used, one remaining

    def test_sw07_reset_at_accuracy(self) -> None:
        """SW-07: reset_at == oldest_timestamp + window_seconds."""
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        limiter.check("alice", "/api/test", _now=1_000.0)  # oldest
        limiter.check("alice", "/api/test", _now=1_010.0)
        _, _, reset_at = limiter.check("alice", "/api/test", _now=1_020.0)
        # Oldest entry is at 1_000.0; reset_at = 1_000.0 + 60 = 1_060.0
        assert reset_at == pytest.approx(1_060.0)

    def test_sw07b_reset_at_on_first_request(self) -> None:
        """SW-07b: reset_at == now + window_seconds when bucket is empty."""
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        _, _, reset_at = limiter.check("alice", "/api/test", _now=500.0)
        # No prior requests; reset_at should be now + window = 500 + 60 = 560
        assert reset_at == pytest.approx(560.0)

    def test_sw08_invalid_config_raises_value_error(self) -> None:
        """SW-08: zero or negative budget/window raises ValueError at construction."""
        with pytest.raises(ValueError, match="requests_per_window"):
            SlidingWindowRateLimiter(requests_per_window=0, window_seconds=60)
        with pytest.raises(ValueError, match="window_seconds"):
            SlidingWindowRateLimiter(requests_per_window=3, window_seconds=0)
        with pytest.raises(ValueError):
            SlidingWindowRateLimiter(requests_per_window=-1, window_seconds=60)


# ---------------------------------------------------------------------------
# RateLimitMiddleware — ASGI/HTTP integration tests
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """MW-01 through MW-11: HTTP-level tests via TestClient."""

    def test_mw01_allows_within_budget(self) -> None:
        """MW-01: first N requests return 200."""
        client = _client(_make_app(requests_per_window=3))
        for _ in range(3):
            resp = client.get("/api/test", headers=_as("alice"))
            assert resp.status_code == 200

    def test_mw02_returns_429_on_exceed(self) -> None:
        """MW-02: (N+1)th request returns 429."""
        client = _client(_make_app(requests_per_window=2))
        client.get("/api/test", headers=_as("alice"))
        client.get("/api/test", headers=_as("alice"))
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 429
        body = resp.json()
        assert "detail" in body

    def test_mw03_429_has_retry_after_header(self) -> None:
        """MW-03: 429 response includes Retry-After header (int, 1 <= value <= window)."""
        window = 30
        client = _client(_make_app(requests_per_window=1, window_seconds=window))
        client.get("/api/test", headers=_as("alice"))
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        retry_after = int(resp.headers["Retry-After"])
        assert 1 <= retry_after <= window

    def test_mw04_429_has_x_ratelimit_remaining_zero(self) -> None:
        """MW-04: 429 response carries X-RateLimit-Remaining: 0."""
        client = _client(_make_app(requests_per_window=1))
        client.get("/api/test", headers=_as("alice"))
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 429
        assert resp.headers.get("X-RateLimit-Remaining") == "0"

    def test_mw05_429_has_x_ratelimit_reset_header(self) -> None:
        """MW-05: 429 response carries X-RateLimit-Reset (positive int)."""
        client = _client(_make_app(requests_per_window=1))
        client.get("/api/test", headers=_as("alice"))
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 429
        assert "X-RateLimit-Reset" in resp.headers
        reset = int(resp.headers["X-RateLimit-Reset"])
        assert reset > 0

    def test_mw06_allowed_response_has_x_ratelimit_remaining(self) -> None:
        """MW-06: allowed response carries X-RateLimit-Remaining (non-negative int)."""
        client = _client(_make_app(requests_per_window=10))
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 200
        assert "X-RateLimit-Remaining" in resp.headers
        remaining = int(resp.headers["X-RateLimit-Remaining"])
        assert remaining >= 0

    def test_mw07_allowed_response_has_x_ratelimit_reset(self) -> None:
        """MW-07: allowed response carries X-RateLimit-Reset (positive int)."""
        client = _client(_make_app(requests_per_window=10))
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 200
        assert "X-RateLimit-Reset" in resp.headers
        reset = int(resp.headers["X-RateLimit-Reset"])
        assert reset > 0

    def test_mw08_per_identity_isolation(self) -> None:
        """MW-08: exhausting alice's budget does NOT throttle bob."""
        client = _client(_make_app(requests_per_window=2))
        # Exhaust alice.
        client.get("/api/test", headers=_as("alice"))
        client.get("/api/test", headers=_as("alice"))
        alice_resp = client.get("/api/test", headers=_as("alice"))
        # Bob is on a separate key — must still pass.
        bob_resp = client.get("/api/test", headers=_as("bob"))
        assert alice_resp.status_code == 429
        assert bob_resp.status_code == 200

    def test_mw09_health_always_exempt(self) -> None:
        """MW-09: GET /health returns 200 regardless of rate-limit state."""
        client = _client(_make_app(requests_per_window=1))
        # Exhaust the limit on a regular route.
        client.get("/api/test", headers=_as("alice"))
        # /health must still pass.
        resp = client.get("/health", headers=_as("alice"))
        assert resp.status_code == 200

    def test_mw10_no_identity_is_exempt(self) -> None:
        """MW-10: requests with no identity (auth_mode=none) pass through unconditionally.

        This simulates a deployment where auth middleware is not installed.
        The rate limiter has no user_id to key on, so it passes through.
        All requests should return 200 regardless of request count.
        """
        # Limit is tiny (1) so any rate limiting would fire immediately.
        client = _client(_make_app(requests_per_window=1))
        # No X-Test-User-ID header → no identity → exempt.
        for _ in range(5):
            resp = client.get("/api/test")
            assert resp.status_code == 200, (
                "Requests without identity should always pass (auth_mode=none path)"
            )

    def test_mw11_retry_after_value_accuracy(self) -> None:
        """MW-11: Retry-After is within [1, window_seconds] on budget exhaustion."""
        window = 60
        client = _client(_make_app(requests_per_window=1, window_seconds=window))
        client.get("/api/test", headers=_as("alice"))  # consume the only slot
        resp = client.get("/api/test", headers=_as("alice"))  # 429
        assert resp.status_code == 429
        retry_after = int(resp.headers["Retry-After"])
        # Retry-After = max(1, reset_at_int - now).  Since the slot was just
        # consumed, reset_at ≈ now + window → Retry-After ≈ window.
        assert 1 <= retry_after <= window

    def test_mw_remaining_header_decrements(self) -> None:
        """X-RateLimit-Remaining decrements with each successive allowed request."""
        client = _client(_make_app(requests_per_window=5))
        previous = None
        for _ in range(4):
            resp = client.get("/api/test", headers=_as("alice"))
            assert resp.status_code == 200
            current = int(resp.headers["X-RateLimit-Remaining"])
            if previous is not None:
                assert current == previous - 1, (
                    f"remaining should decrement: got {current!r}, "
                    f"previous was {previous!r}"
                )
            previous = current

    def test_mw_per_route_isolation_at_http_level(self) -> None:
        """Exhausting /api/test does not throttle /api/other for the same user."""
        client = _client(_make_app(requests_per_window=2))
        client.get("/api/test", headers=_as("alice"))
        client.get("/api/test", headers=_as("alice"))
        test_resp = client.get("/api/test", headers=_as("alice"))
        other_resp = client.get("/api/other", headers=_as("alice"))
        assert test_resp.status_code == 429
        assert other_resp.status_code == 200


# ---------------------------------------------------------------------------
# Runtime override helpers
# ---------------------------------------------------------------------------


def _make_app_with_overrides(
    requests_per_window: int = 10,
    window_seconds: int = 60,
) -> FastAPI:
    """Build a minimal FastAPI app wired with RateLimitMiddleware + a simple
    runtime-override PATCH endpoint.

    The PATCH endpoint at ``/test/set-override`` writes directly into
    ``app.state.rate_limit_overrides``, mirroring what
    ``PATCH /api/admin/rate-limit-config`` does — but without the admin RBAC
    gate so the regression tests stay self-contained.

    ``app.state.rate_limit_overrides`` is initialised empty (the same as
    ``create_app()`` does) so the middleware starts from the startup budget.
    """
    app = FastAPI()
    app.state.rate_limit_overrides: dict = {}

    class _DynamicIdentityMiddleware(BaseHTTPMiddleware):
        def __init__(self, inner: ASGIApp) -> None:
            super().__init__(inner)

        async def dispatch(self, request: Request, call_next):
            user_id = request.headers.get("X-Test-User-ID")
            if user_id:
                request.state.identity = AuthIdentity(
                    user_id=user_id,
                    workspace_id="default",
                    roles=("researcher",),
                )
            return await call_next(request)

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
    )
    app.add_middleware(_DynamicIdentityMiddleware)

    @app.get("/api/test")
    def test_route() -> dict:
        return {"ok": True}

    @app.patch("/test/set-override")
    def set_override(body: dict) -> dict:
        """Write runtime overrides into app.state — mirrors admin PATCH endpoint."""
        if "max_requests" in body:
            app.state.rate_limit_overrides["max_requests"] = int(body["max_requests"])
        if "window_seconds" in body:
            app.state.rate_limit_overrides["window_seconds"] = int(body["window_seconds"])
        return {"ok": True, "overrides": dict(app.state.rate_limit_overrides)}

    return app


# ---------------------------------------------------------------------------
# RateLimitMiddleware — runtime override regression tests
# ---------------------------------------------------------------------------


class TestRateLimitRuntimeOverrides:
    """OV-01 through OV-03: verify PATCH /admin/rate-limit-config actually
    changes the 429 threshold and X-RateLimit-Limit header at request time.

    These tests FAIL before the fix (middleware ignores app.state overrides)
    and PASS after (middleware reads overrides per-request).
    """

    def test_ov01_lower_budget_override_enforced_at_new_threshold(self) -> None:
        """OV-01: After PATCH to max_requests=2, 429 fires at 3rd request.

        Startup budget is 10.  Without the fix the 3rd request would be
        allowed (budget still 10); with the fix it must return 429.
        """
        client = _client(_make_app_with_overrides(requests_per_window=10))

        # Apply override: reduce budget to 2
        patch_resp = client.patch("/test/set-override", json={"max_requests": 2})
        assert patch_resp.status_code == 200

        # First two requests must be allowed
        for i in range(2):
            resp = client.get("/api/test", headers=_as("alice"))
            assert resp.status_code == 200, f"Request {i + 1} unexpectedly denied"

        # Third request must be denied at the overridden threshold (2), not startup (10)
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 429, (
            "Expected 429 at the overridden threshold (max_requests=2) but got "
            f"{resp.status_code}; middleware is likely still using the startup budget"
        )

    def test_ov02_x_ratelimit_limit_header_reflects_override(self) -> None:
        """OV-02: X-RateLimit-Limit header after PATCH reflects the new max_requests.

        Startup budget is 10.  Without the fix the header always shows 10;
        with the fix it must show the overridden value (5).
        """
        client = _client(_make_app_with_overrides(requests_per_window=10))

        # Apply override: set budget to 5
        client.patch("/test/set-override", json={"max_requests": 5})

        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 200
        limit_header = resp.headers.get("X-RateLimit-Limit")
        assert limit_header is not None, "X-RateLimit-Limit header missing"
        assert limit_header == "5", (
            f"X-RateLimit-Limit should be '5' (override) but got {limit_header!r}; "
            "middleware is likely still returning the startup default"
        )

    def test_ov03_restoring_higher_budget_unblocks_requests(self) -> None:
        """OV-03: Patching back to the original budget unblocks further requests.

        Sequence:
          1. PATCH max_requests=2  → budget is 2
          2. Make 2 allowed requests, then 1 denied (429) request
          3. PATCH max_requests=10 → budget restored
          4. New request must be allowed (bucket has 2 entries, limit is 10)
        """
        client = _client(_make_app_with_overrides(requests_per_window=10))

        # Step 1+2: reduce to 2 and exhaust
        client.patch("/test/set-override", json={"max_requests": 2})
        client.get("/api/test", headers=_as("alice"))
        client.get("/api/test", headers=_as("alice"))
        blocked = client.get("/api/test", headers=_as("alice"))
        assert blocked.status_code == 429, "Expected 429 before restoring budget"

        # Step 3: restore the higher budget
        client.patch("/test/set-override", json={"max_requests": 10})

        # Step 4: next request must be allowed (bucket has 2 entries < limit 10)
        resp = client.get("/api/test", headers=_as("alice"))
        assert resp.status_code == 200, (
            "Expected 200 after restoring budget to 10 but got "
            f"{resp.status_code}; middleware override is not being read at request time"
        )
