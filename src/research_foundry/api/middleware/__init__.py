"""Starlette middleware for the RF loopback API.

Middleware stack applied by ``create_app`` (outermost → innermost):

    CORS → allowlist → auth

The order guarantees that CORS preflight requests are handled before any IP
or auth check, and that IP filtering fires before the (more expensive) token
comparison.

Modules:
  auth      — Bearer-token authentication middleware (auth_mode == "token")
  allowlist — IP allowlist middleware (viewer.allowlist non-empty)
"""
