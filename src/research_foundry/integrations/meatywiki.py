"""MeatyWiki Portal integration client (E1-P1 / GOV-002).

MeatyWiki is the knowledge-vault sink for a completed research run. The
swarm-driver's governed writeback (``services.writeback.governed_writeback``)
posts a compiled source note to the Portal intake endpoint, which auto-compiles
it into the vault.

Health check: ``GET /api/admin/health``
Auth: optional bearer token from env ``MEATYWIKI_API_TOKEN``.

Config (foundry.yaml)::

    integrations:
      meatywiki:
        base_url: http://127.0.0.1:8765   # default (Portal binds loopback-only)

The intake write is the one irreversible hop the swarm-driver performs, so it is
always gated upstream (personal/public + verified → auto; else HITL). This
client only performs the mechanical POST; it makes no governance decision.

HTTP-contract assumption (confirm against a live Portal; noted in the handoff):
``POST /api/intake/note`` accepts ``{title, body, source, tags, metadata}`` and
returns ``{"note_id", "status"}``.
"""

from __future__ import annotations

import os
from typing import Any

from .base import IntegrationClient

_DEFAULT_BASE_URL = "http://127.0.0.1:8765"
_HEALTH_PATH = "/api/admin/health"
_INTAKE_PATH = "/api/intake/note"
_TOKEN_ENV = "MEATYWIKI_API_TOKEN"


class MeatyWikiClient(IntegrationClient):
    """Thin HTTP client for the MeatyWiki Portal intake API.

    Parameters
    ----------
    base_url:
        Portal base URL (default ``http://127.0.0.1:8765``).
    token:
        Optional bearer token (read from ``MEATYWIKI_API_TOKEN`` when not
        supplied). Pass ``""`` to force unauthenticated requests.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        token: str | None = None,
    ) -> None:
        super().__init__(base_url)
        if token is None:
            token = os.environ.get(_TOKEN_ENV) or ""
        self._token = token

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls) -> MeatyWikiClient:
        """Construct from foundry.yaml ``integrations.meatywiki.base_url`` / env."""

        return cls(base_url=_load_meatywiki_base_url())

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
        """Return True when the Portal admin-health endpoint responds.

        Never raises; any error (offline, auth, parse) yields False.
        """

        data = self._get(_HEALTH_PATH, timeout=timeout, headers=self._auth_headers())
        return data is not None

    # ------------------------------------------------------------------
    # Intake
    # ------------------------------------------------------------------

    def post_note(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """POST a compiled note to ``/api/intake/note``.

        Returns the intake response (expected ``note_id`` + ``status``) or
        ``None`` on any error. Never raises — fail-soft contract.

        Idempotency contract (A1): the payload carries
        ``metadata.meatywiki_writeback_id`` (a deterministic hash of the note
        title) precisely so the Portal can dedup a re-POST of the *same*
        writeback. The RF side is now hardened (per-run advisory lock + a
        pre-POST intent receipt in ``services.writeback``), but a crash between
        a successful POST and its terminal receipt can still trigger one re-POST
        on resume — which is only fully idempotent if the Portal dedups on
        ``meatywiki_writeback_id`` server-side. That server-side dedup is the
        one remaining cross-repo obligation for end-to-end exactly-once.
        """

        return self._post(_INTAKE_PATH, payload, headers=self._auth_headers())


# ---------------------------------------------------------------------------
# Config helpers (internal)
# ---------------------------------------------------------------------------


def _load_meatywiki_base_url() -> str:
    """Read base_url from foundry.yaml ``integrations.meatywiki.base_url``.

    Falls back to env ``MEATYWIKI_BASE_URL``, then the compiled default.
    Degrades silently — any read error returns the default.
    """

    try:
        from ..config import FoundryConfig

        cfg = FoundryConfig.load()
        foundry = cfg.foundry or {}
        integrations = foundry.get("integrations") or {}
        mw_cfg = integrations.get("meatywiki") or {}
        url = mw_cfg.get("base_url")
        if url:
            return str(url).rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("MEATYWIKI_BASE_URL", _DEFAULT_BASE_URL)


__all__ = ["MeatyWikiClient"]
