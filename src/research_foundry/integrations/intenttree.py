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

        Returns the node record or ``None`` when offline.
        **Phase 2 stub — currently a no-op.**
        """

        return None  # pragma: no cover (Phase 2)

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
