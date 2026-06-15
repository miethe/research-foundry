---
name: feedback-degrade-pattern
description: The house degrade/fail-soft pattern for all RF integration clients and adapters — must match adapters/base.py exactly.
metadata:
  type: feedback
---

All RF integration clients (and adapters) must match the degrade pattern from `adapters/base.py`:

- `available()` returns bool, never raises, has a short timeout (2s default)
- HTTP helpers `_get/_post/_patch` return parsed JSON or None on ANY error (broad `except Exception`)
- Callers always test `if client.available()` before live calls
- Offline / unreachable is informational, not pipeline-fatal

**Why:** The spec's "candidate first, push second" principle: RF is file-first and must complete offline. Pipeline must never fail due to an unreachable integration.

**How to apply:** In any new integration client or service that calls external HTTP endpoints, wrap the call in the `_get/_post/_patch` helpers from `IntegrationClient` and gate on `available()`. Never let a network exception propagate to the caller.
