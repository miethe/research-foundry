"""CCDash integration client.

CCDash is the run-telemetry consumer sibling of Research Foundry. RF already
writes a durable ``ccdash_event`` YAML mirror on every run (the source of
truth / replay log — see ``services/telemetry.py:emit_ccdash_event``); this
client adds a best-effort, config-gated HTTP POST of the same event dict to
CCDash's ingest endpoint so dashboards can see events live instead of relying
on a filesystem-watch fallback. See
``docs/project_plans/design-specs/ccdash-run-telemetry-transport-handoff.md``.

Target: ``POST {CCDASH_BASE_URL}/api/v1/ingest/rf-events``
Auth: bearer token from env ``CCDASH_INGEST_TOKEN``.

Config (foundry.yaml)::

    integrations:
      ccdash:
        base_url: http://10.42.10.76:9200   # example — no compiled default

Token (per-profile .env file, gitignored)::

    CCDASH_INGEST_TOKEN=replace-me-ccdash-token

Unlike ARC/IntentTree, CCDash has **no hardcoded default base_url** — this
integration is entirely opt-in and must be explicitly configured. ``available()``
is a pure config check (both ``base_url`` and a token must be set); it never
makes a network call, because the CCDash ingest contract defines no health
endpoint for RF to probe.
"""

from __future__ import annotations

import os
from typing import Any

from .base import IntegrationClient

_BASE_URL_ENV = "CCDASH_BASE_URL"
_TOKEN_ENV = "CCDASH_INGEST_TOKEN"
_INGEST_PATH = "/api/v1/ingest/rf-events"


class CCDashClient(IntegrationClient):
    """Thin HTTP client for CCDash's run-telemetry ingest endpoint.

    Parameters
    ----------
    base_url:
        CCDash base URL. When not supplied, read from env ``CCDASH_BASE_URL``
        (default ``""`` — unset). An empty ``base_url`` makes ``available()``
        return ``False``, which is the intended "not configured" state.
    token:
        Bearer token. When not supplied, read from env
        ``CCDASH_INGEST_TOKEN`` (default ``""``). Pass ``""`` explicitly to
        force "no token".
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
    ) -> None:
        if base_url is None:
            base_url = os.environ.get(_BASE_URL_ENV, "")
        super().__init__(base_url)
        if token is None:
            token = os.environ.get(_TOKEN_ENV, "")
        self._token = token

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls) -> CCDashClient:
        """Construct from foundry.yaml / env (see module docstring).

        The bearer token is **always** read from ``CCDASH_INGEST_TOKEN`` — a
        secret never belongs in foundry.yaml — while ``base_url`` may
        optionally be overridden via ``integrations.ccdash.base_url``.
        """

        base_url = _load_ccdash_base_url()
        return cls(base_url=base_url)

    # ------------------------------------------------------------------
    # Auth header helper
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    # ------------------------------------------------------------------
    # Availability — pure config gate, no network call.
    # ------------------------------------------------------------------

    def available(self, timeout: float = 2.0) -> bool:  # type: ignore[override]
        """Return True only when both ``base_url`` and a bearer token are set.

        CCDash's ingest contract defines no health endpoint, so this is a
        config check rather than a live probe (unlike ARC/IntentTree). Never
        raises; unset config (either field) yields False so callers skip the
        POST silently.
        """

        try:
            return bool(self.base_url) and bool(self._token)
        except Exception:  # noqa: BLE001
            return False

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def post_rf_event(self, event: dict[str, Any]) -> bool:
        """POST ``event`` verbatim to CCDash's rf-events ingest endpoint.

        Returns ``True`` on a 2xx response (parsed JSON or empty body),
        ``False`` when unconfigured, unreachable, or on any non-2xx/error
        response. Never raises — a dropped POST must never block or fail the
        run; the YAML mirror written by ``emit_ccdash_event`` remains the
        durable record CCDash can replay from.
        """

        try:
            if not self.available():
                return False
            result = self._post(_INGEST_PATH, event, headers=self._auth_headers())
            return result is not None
        except Exception:  # noqa: BLE001
            return False


# ---------------------------------------------------------------------------
# Config helpers (internal)
# ---------------------------------------------------------------------------


def _load_ccdash_base_url() -> str:
    """Read base_url from foundry.yaml under ``integrations.ccdash.base_url``.

    Falls back to env var ``CCDASH_BASE_URL``, then ``""`` (unconfigured —
    ``available()`` will be False and the POST silently skipped). Degrades
    silently — any config read error falls through to the env/default.
    """

    try:
        from ..config import FoundryConfig

        cfg = FoundryConfig.load()
        foundry = cfg.foundry or {}
        integrations = foundry.get("integrations") or {}
        cd_cfg = integrations.get("ccdash") or {}
        url = cd_cfg.get("base_url")
        if url:
            return str(url).rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get(_BASE_URL_ENV, "")


__all__ = ["CCDashClient"]
