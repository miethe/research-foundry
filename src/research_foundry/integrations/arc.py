"""ARC (Agent Review Council) integration client.

ARC is the council-review sibling of Research Foundry. RF hands it an evidence
bundle and ARC returns a verdict (approve / concern / block). This client is the
Phase 0 foundation only — method stubs are present but no-op until Phase 3.

Health check: ``GET /api/health``
Expected response shape (Phase 3 will parse): ``{"integrations": {"authoring": {"available": true}}}``

Config (foundry.yaml)::

    integrations:
      arc:
        base_url: http://127.0.0.1:8910   # default

No auth required for local ARC; the remote runs on the same machine.
"""

from __future__ import annotations

import os
from typing import Any

from .base import IntegrationClient

_DEFAULT_BASE_URL = "http://127.0.0.1:8910"
_HEALTH_PATH = "/api/health"


class ArcClient(IntegrationClient):
    """Thin HTTP client for the local ARC server.

    Parameters
    ----------
    base_url:
        ARC server base URL (default ``http://127.0.0.1:8910``).
    """

    def __init__(self, base_url: str = _DEFAULT_BASE_URL) -> None:
        super().__init__(base_url)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls) -> ArcClient:
        """Construct from foundry.yaml ``integrations.arc.base_url`` or default."""

        base_url = _load_arc_base_url()
        return cls(base_url=base_url)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def available(self, timeout: float = 2.0) -> bool:  # type: ignore[override]
        """Return True only when ARC is reachable AND reports integrations available.

        Never raises; timeout / connection error / unexpected body all yield False.
        """

        data = self._get(_HEALTH_PATH, timeout=timeout)
        if not isinstance(data, dict):
            return False
        # ARC's health response embeds an integrations availability map.
        # Until Phase 3 we treat any 200 response as "reachable enough" since
        # the exact schema isn't confirmed; the authoring.available check is
        # included here for forward-compatibility.
        integrations = data.get("integrations")
        if isinstance(integrations, dict):
            authoring = integrations.get("authoring")
            if isinstance(authoring, dict):
                return bool(authoring.get("available", True))
        # No integrations block in the response — treat bare 200 as available.
        return True

    # ------------------------------------------------------------------
    # Review operations (Phase 3)
    # ------------------------------------------------------------------

    def scaffold_review(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """POST ``payload`` to ARC ``POST /api/runs`` to scaffold a council review.

        ``payload`` must include at minimum ``council``, ``target``, and
        ``objective`` (ARC surface contract). Returns the ARC response (which
        includes ``run_id`` as the arc_run_id) or ``None`` on any error.
        Never raises.
        """

        return self._post("/api/runs", payload)

    def get_run(self, arc_run_id: str) -> dict[str, Any] | None:
        """GET ``/api/runs/{arc_run_id}`` — return the ARC run record or ``None``.

        The run record may include a ``verdict`` field once reviewers have
        populated the run. Returns ``None`` on any network/parse error.
        Never raises.
        """

        return self._get(f"/api/runs/{arc_run_id}")


# ---------------------------------------------------------------------------
# Config helpers (internal)
# ---------------------------------------------------------------------------


def _load_arc_base_url() -> str:
    """Read base_url from foundry.yaml under ``integrations.arc.base_url``.

    Falls back to the env var ``ARC_BASE_URL``, then the compiled default.
    Degrades silently — any read error returns the default.
    """

    try:
        from ..config import FoundryConfig

        cfg = FoundryConfig.load()
        foundry = cfg.foundry or {}
        integrations = foundry.get("integrations") or {}
        arc_cfg = integrations.get("arc") or {}
        url = arc_cfg.get("base_url")
        if url:
            return str(url).rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("ARC_BASE_URL", _DEFAULT_BASE_URL)


__all__ = ["ArcClient"]
