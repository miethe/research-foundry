"""IntentTree integration client.

IntentTree is the task-dispatch sibling. RF receives research tasks dispatched
from IntentTree (Phase 2 inbound) and pushes status + result links back to the
originating node (Phase 1 outbound). This client is the Phase 0 foundation
only — method stubs are present but no-op until Phases 1–2.

Health check: ``GET /api/meta/version``
Auth: optional bearer token from env ``INTENTTREE_API_TOKEN``.

Config (foundry.yaml)::

    integrations:
      intenttree:
        base_url: http://localhost:8000   # default

Token (per-profile .env file, gitignored)::

    INTENTTREE_API_TOKEN=replace-me-intenttree-token
"""

from __future__ import annotations

import os
from typing import Any

from .base import IntegrationClient

_DEFAULT_BASE_URL = "http://localhost:8000"
_HEALTH_PATH = "/api/meta/version"
_TOKEN_ENV = "INTENTTREE_API_TOKEN"


class IntentTreeClient(IntegrationClient):
    """Thin HTTP client for the IntentTree service.

    Parameters
    ----------
    base_url:
        IntentTree base URL (default ``http://localhost:8000``).
    token:
        Optional bearer token (read from ``INTENTTREE_API_TOKEN`` env var when
        not supplied). Pass ``None`` to force unauthenticated requests.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        token: str | None = None,
    ) -> None:
        super().__init__(base_url)
        # token=None means "try env"; token="" means "no auth"
        if token is None:
            token = os.environ.get(_TOKEN_ENV) or ""
        self._token = token

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls) -> IntentTreeClient:
        """Construct from foundry.yaml / env (see module docstring)."""

        base_url = _load_intenttree_base_url()
        return cls(base_url=base_url)

    # ------------------------------------------------------------------
    # Auth header helper
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def available(self, timeout: float = 2.0) -> bool:  # type: ignore[override]
        """Return True when IntentTree's version endpoint responds with HTTP 200.

        Never raises; any error yields False.
        """

        data = self._get(_HEALTH_PATH, timeout=timeout, headers=self._auth_headers())
        # Any non-None response (even empty dict) means the server responded.
        return data is not None

    # ------------------------------------------------------------------
    # Phase 1–2 stubs (no-op; will be filled in during Phases 1 and 2)
    # ------------------------------------------------------------------

    def get_node(
        self,
        node_id: str,
        *,
        include: str = "artifacts,edges",
    ) -> dict[str, Any] | None:
        """GET ``/api/nodes/{node_id}?include={include}``.

        Returns the node record or ``None`` when offline or on any error
        (fail-soft contract mirrors ``patch_node`` / ``add_node_artifact``).
        """

        path = f"/api/nodes/{node_id}"
        if include:
            path = f"{path}?include={include}"
        return self._get(path, headers=self._auth_headers())

    def patch_node(
        self,
        node_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """PATCH status/progress fields on an IntentTree node.

        Sends a PATCH request to ``/api/nodes/{node_id}`` with ``payload`` as
        the JSON body. Returns the updated node record on success, or ``None``
        on any error (offline, auth failure, timeout, unexpected response). Never
        raises — all errors are silently swallowed (fail-soft contract).
        """

        return self._patch(
            f"/api/nodes/{node_id}",
            payload,
            headers=self._auth_headers(),
        )

    def add_node_artifact(
        self,
        node_id: str,
        artifact: dict[str, Any],
    ) -> dict[str, Any] | None:
        """POST a new artifact link to ``/api/nodes/{node_id}/artifacts``.

        Returns the created artifact record on success, or ``None`` on any
        error. Never raises — fail-soft contract mirrors ``patch_node``.
        """

        return self._post(
            f"/api/nodes/{node_id}/artifacts",
            artifact,
            headers=self._auth_headers(),
        )

    # ------------------------------------------------------------------
    # HITL gate primitives (E1-P1 / GOV-001, GOV-002) — the human-in-the-loop
    # approval surface the swarm-driver uses to escalate a sensitivity-gated run
    # and to gate an irreversible MeatyWiki writeback. These map onto the
    # IntentTree MCP ``request_create`` / ``request_approve`` / ``request_reject``
    # primitives named in the swarm-driver design §5.3/§5.4.
    #
    # HTTP-contract assumption (confirm against a live IntentTree; noted in the
    # handoff): the MCP request lifecycle is exposed over HTTP as
    #   POST   /api/requests                 -> {"request_id", "status": "pending"}
    #   GET    /api/requests/{request_id}    -> {"request_id", "status"}
    #   POST   /api/requests/{request_id}/approve
    #   POST   /api/requests/{request_id}/reject
    # A ``node_id`` (the bound research node) associates the gate with its run.
    # All four fail-soft to ``None`` (offline / auth / parse error), like the
    # node methods above.
    # ------------------------------------------------------------------

    def request_create(
        self,
        *,
        node_id: str | None,
        kind: str,
        title: str,
        body: str = "",
        artifacts: list[dict[str, Any]] | None = None,
        sensitivity: str | None = None,
    ) -> dict[str, Any] | None:
        """Open a HITL approval request (MCP ``request_create``).

        POSTs to ``/api/requests`` and returns the created request record
        (expected to carry ``request_id`` + ``status``) or ``None`` on any
        error. Never raises.
        """

        payload: dict[str, Any] = {
            "kind": kind,
            "title": title,
            "body": body,
        }
        if node_id:
            payload["node_id"] = node_id
        if artifacts:
            payload["artifacts"] = artifacts
        if sensitivity:
            payload["sensitivity"] = sensitivity
        return self._post(
            "/api/requests",
            payload,
            headers=self._auth_headers(),
        )

    def request_status(self, request_id: str) -> dict[str, Any] | None:
        """GET ``/api/requests/{request_id}`` — the current request record.

        Returns the record (expected ``status`` ∈ ``pending|approved|rejected``)
        or ``None`` on any error. Never raises.
        """

        return self._get(
            f"/api/requests/{request_id}",
            headers=self._auth_headers(),
        )

    def request_approve(
        self,
        request_id: str,
        *,
        approver: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        """POST ``/api/requests/{request_id}/approve`` (MCP ``request_approve``)."""

        payload: dict[str, Any] = {}
        if approver:
            payload["approver"] = approver
        if note:
            payload["note"] = note
        return self._post(
            f"/api/requests/{request_id}/approve",
            payload,
            headers=self._auth_headers(),
        )

    def request_reject(
        self,
        request_id: str,
        *,
        approver: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        """POST ``/api/requests/{request_id}/reject`` (MCP ``request_reject``)."""

        payload: dict[str, Any] = {}
        if approver:
            payload["approver"] = approver
        if note:
            payload["note"] = note
        return self._post(
            f"/api/requests/{request_id}/reject",
            payload,
            headers=self._auth_headers(),
        )


# ---------------------------------------------------------------------------
# Config helpers (internal)
# ---------------------------------------------------------------------------


def _load_intenttree_base_url() -> str:
    """Read base_url from foundry.yaml under ``integrations.intenttree.base_url``.

    Falls back to env var ``INTENTTREE_BASE_URL``, then the compiled default.
    """

    try:
        from ..config import FoundryConfig

        cfg = FoundryConfig.load()
        foundry = cfg.foundry or {}
        integrations = foundry.get("integrations") or {}
        it_cfg = integrations.get("intenttree") or {}
        url = it_cfg.get("base_url")
        if url:
            return str(url).rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("INTENTTREE_BASE_URL", _DEFAULT_BASE_URL)


__all__ = ["IntentTreeClient"]
