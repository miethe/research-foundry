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

CLEARANCE BACKSTOP (clearance-gates M2)
---------------------------------------
``_post`` / ``_patch`` route their payload through
``services.clearance.assert_payload_mediated`` before a socket is opened. A
payload carrying a clearance-stamped record with blocked scopes is refused
unless it arrives wrapped in a ``MediatedPayload`` proving
``mediate_egress()`` already ran on the raw records.

This is a BACKSTOP, not the control. Two limits are deliberate and must not be
mistaken for coverage:

1. It inspects a POST-PROJECTION payload. DEF-5 records that run-export and the
   catalog project records through hand-listed key allowlists which silently
   drop unknown fields; a projection that strips ``clearance`` leaves nothing
   here to find. The control is ``mediate_egress()`` on raw records at each
   payload constructor.
2. It only covers clients that actually reach these helpers.
   ``integrations/notebooklm.py`` overrides all three as no-op stubs and does
   its real work through a ``subprocess`` call to the ``notebooklm`` CLI, so it
   is gated at its own call site instead — see that module's overrides.

A bare dict with no taint marker passes unchanged, which is what keeps every
pre-existing call site working.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..services.clearance import MediatedPayload, assert_payload_mediated


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
        payload: dict[str, Any] | MediatedPayload,
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """POST JSON ``payload`` to ``{base_url}{path}``, return parsed JSON or None.

        Refuses (raises ``ClearanceDenied``) when *payload* carries a
        clearance-stamped record with blocked scopes and no proof of mediation.
        That refusal is deliberately NOT swallowed by the fail-soft ``except``
        below: a governance decision must surface, whereas a network error
        degrades. See the module docstring for why this is a backstop only.
        """

        payload = assert_payload_mediated(payload, target=self.base_url + path)
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
        payload: dict[str, Any] | MediatedPayload,
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """PATCH JSON ``payload`` to ``{base_url}{path}``, return parsed JSON or None.

        Same clearance backstop as :meth:`_post`.
        """

        payload = assert_payload_mediated(payload, target=self.base_url + path)
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
