"""Base integration client contract.

Every integration client:

* Has a ``base_url`` (overridable from foundry.yaml + env).
* Implements ``available(timeout=2.0) -> bool`` — a lightweight health probe
  that returns ``False`` (never raises) when the remote is unreachable, slow,
  or returns an unexpected response. This mirrors the adapter ``available()``
  degrade pattern in ``adapters/base.py``.
* Provides ``_get`` / ``_post`` / ``_patch`` helpers that return parsed JSON or
  ``None`` on any error. Callers must treat ``None`` as "offline / degraded".

No new required dependency is introduced — all HTTP calls use the stdlib
``urllib.request`` / ``urllib.error`` so the package installs without httpx.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class IntegrationClient:
    """Lightweight HTTP integration client (stdlib only, fail-soft).

    Parameters
    ----------
    base_url:
        Root URL of the remote service (no trailing slash).
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def available(self, timeout: float = 2.0) -> bool:
        """Return True only when the remote health endpoint responds OK.

        Never raises — any exception (connection refused, timeout, non-2xx,
        parse error) is treated as "not available" and silently swallowed.
        """

        raise NotImplementedError  # subclasses override

    # ------------------------------------------------------------------
    # HTTP helpers — all return None on any error, never raise.
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        *,
        timeout: float = 5.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """GET ``{base_url}{path}`` and return parsed JSON, or None on error."""

        url = self.base_url + path
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw) if raw else {}
        except Exception:  # noqa: BLE001
            return None

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """POST JSON ``payload`` to ``{base_url}{path}``, return parsed JSON or None."""

        url = self.base_url + path
        try:
            body = json.dumps(payload).encode()
            hdrs = {"Content-Type": "application/json", **(headers or {})}
            req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw) if raw else {}
        except Exception:  # noqa: BLE001
            return None

    def _patch(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """PATCH JSON ``payload`` to ``{base_url}{path}``, return parsed JSON or None."""

        url = self.base_url + path
        try:
            body = json.dumps(payload).encode()
            hdrs = {"Content-Type": "application/json", **(headers or {})}
            req = urllib.request.Request(url, data=body, headers=hdrs, method="PATCH")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw) if raw else {}
        except Exception:  # noqa: BLE001
            return None


__all__ = ["IntegrationClient"]
