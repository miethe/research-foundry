"""Starlette middleware for the RF loopback API.

Middleware stack applied by ``create_app`` (outermost → innermost):

    CORS → allowlist → auth → rate-limit

The order guarantees that:
  - CORS preflight requests are handled before any IP or auth check.
  - IP filtering fires before the (more expensive) token comparison.
  - Auth sets ``request.state.identity`` before rate-limit reads it.
  - Rate limiting runs as close to the handler as possible.

Modules:
  auth       — Bearer-token / provider authentication middleware
  allowlist  — IP allowlist middleware (viewer.allowlist non-empty)
  rate_limit — Per-identity + per-route sliding-window rate limiter (P5.6)
"""
