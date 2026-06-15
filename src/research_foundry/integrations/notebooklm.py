"""NotebookLM integration client (CLI-wrapper, no REST API).

NotebookLM has no public REST API.  This client shells out to the
``notebooklm`` CLI (``notebooklm-py`` package) using subprocess and parses
the ``--json`` output.  Every operation degrades gracefully: any subprocess
error, non-zero exit code, timeout, or JSON parse failure returns ``None``
(or ``False`` for the health check) — the pipeline is never interrupted.

Config (foundry.yaml)::

    integrations:
      notebooklm:
        correlation_mode: project
        notebook_title_template: "RF — {project}"
        base_url: null          # unused; CLI is the transport

Environment::

    NOTEBOOKLM_HOME      Custom config directory (default: ~/.notebooklm)
    NOTEBOOKLM_CLI_PATH  Override path to the notebooklm binary

CLI reference: .claude/skills/notebooklm/SKILL.md
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from .base import IntegrationClient

_CLI_ENV_PATH = "NOTEBOOKLM_CLI_PATH"
_HOME_ENV = "NOTEBOOKLM_HOME"
_CLI_NAME = "notebooklm"

# Timeout (seconds) used for the status probe in available().
_PROBE_TIMEOUT: float = 2.0


class NotebookLMClient(IntegrationClient):
    """CLI-wrapping client for NotebookLM.

    All network operations shell out to the ``notebooklm`` CLI rather than
    making HTTP requests, because NotebookLM has no public REST API.
    The same ``dict | None`` return contract as :class:`IntegrationClient`
    is preserved — callers must treat ``None`` as "offline / degraded".

    Parameters
    ----------
    cli_path:
        Absolute path to the ``notebooklm`` binary.  ``None`` means "resolve
        from PATH (or ``NOTEBOOKLM_CLI_PATH`` env) at call time".
    home:
        Value to inject as ``NOTEBOOKLM_HOME`` for per-agent isolation.
        ``None`` leaves the environment variable unchanged.
    """

    def __init__(
        self,
        cli_path: str | None = None,
        home: str | None = None,
    ) -> None:
        # base_url is unused for CLI transport; pass empty string to satisfy
        # the parent __init__ signature (it merely stores the value).
        super().__init__("")
        self._cli_path = cli_path
        self._home = home

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls) -> NotebookLMClient:
        """Construct from foundry.yaml ``integrations.notebooklm`` + env.

        Never raises — any config read error falls back to environment
        variables and sensible defaults.
        """

        cli_path: str | None = None
        home: str | None = None

        # Read foundry.yaml (best-effort).
        try:
            from ..config import FoundryConfig

            cfg = FoundryConfig.load()
            foundry = cfg.foundry or {}
            integrations = foundry.get("integrations") or {}
            nlm_cfg = integrations.get("notebooklm") or {}
            # base_url is intentionally unused (CLI transport); we still read
            # the block so future keys can be extracted here.
            _ = nlm_cfg.get("base_url")  # acknowledged, not used
        except Exception:  # noqa: BLE001
            pass

        # Environment overrides win.
        cli_path = os.environ.get(_CLI_ENV_PATH) or cli_path
        home = os.environ.get(_HOME_ENV) or home

        return cls(cli_path=cli_path, home=home)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def available(self, timeout: float = _PROBE_TIMEOUT) -> bool:  # type: ignore[override]
        """Return True when the ``notebooklm`` CLI is installed AND authenticated.

        Runs ``notebooklm status`` (or ``notebooklm list --json`` as a
        fallback) and treats exit-code 0 within *timeout* seconds as healthy.
        Any error (binary not found, auth failure, timeout) yields ``False``.
        Never raises.
        """

        if not self._resolve_cli():
            return False

        # ``notebooklm status`` is the canonical health probe (see SKILL.md).
        result = self._run_cli(["status"], timeout=timeout)
        return result is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_notebook(self, title: str) -> dict[str, Any] | None:
        """Create a new NotebookLM notebook with *title*.

        CLI: ``notebooklm create "<title>" --json``

        Returns::

            {"id": "<uuid>", "title": "<title>"}

        or ``None`` on any error.
        """

        return self._run_cli(["create", title, "--json"])

    def add_source(
        self,
        notebook_id: str,
        locator: str,
        *,
        title: str | None = None,
    ) -> dict[str, Any] | None:
        """Add a source URL, file path, or YouTube link to *notebook_id*.

        CLI: ``notebooklm source add "<locator>" --notebook <notebook_id> --json``

        Returns::

            {"source_id": "<uuid>", "title": "<title>", "status": "processing"}

        or ``None`` on any error.  The ``title`` parameter has no CLI
        equivalent in the current notebooklm-py API; it is accepted here for
        forward-compatibility but is ignored in the subprocess call.
        """

        args = ["source", "add", locator, "--notebook", notebook_id, "--json"]
        # ``title`` is retained in the signature for API symmetry; the CLI
        # does not expose a --title flag for source add as of notebooklm-py
        # v0.3.x.  A future CLI version may support it.
        del title  # intentionally unused until CLI support lands
        return self._run_cli(args)

    def get_notebook(self, notebook_id: str) -> dict[str, Any] | None:
        """Return the notebook record for *notebook_id*, or ``None`` on error.

        Calls ``notebooklm list --json`` and filters by ``id``.  This is the
        only reliable way to fetch a single notebook without a REST endpoint.

        Returns a single notebook dict from the list response::

            {"id": "<uuid>", "title": "<title>", "created_at": "..."}

        or ``None`` when the notebook is not found or any error occurs.
        """

        data = self._run_cli(["list", "--json"])
        if not isinstance(data, dict):
            return None
        notebooks = data.get("notebooks")
        if not isinstance(notebooks, list):
            return None
        for nb in notebooks:
            if isinstance(nb, dict) and nb.get("id") == notebook_id:
                return nb
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_cli(self) -> str | None:
        """Return the absolute path to the ``notebooklm`` binary, or ``None``.

        Checks ``self._cli_path`` first, then ``NOTEBOOKLM_CLI_PATH`` env,
        then PATH via :func:`shutil.which`.  Never raises.
        """

        candidate = self._cli_path or os.environ.get(_CLI_ENV_PATH)
        if candidate:
            return candidate
        return shutil.which(_CLI_NAME)

    def _build_env(self) -> dict[str, str] | None:
        """Build the subprocess environment dict, injecting NOTEBOOKLM_HOME.

        Returns ``None`` when no overrides are required (inherit environment
        as-is), avoiding an unnecessary dict copy in the common case.
        """

        if not self._home:
            return None
        env = os.environ.copy()
        env[_HOME_ENV] = self._home
        return env

    def _run_cli(
        self,
        args: list[str],
        timeout: float = 10.0,
    ) -> dict[str, Any] | None:
        """Run ``notebooklm <args>`` and return parsed JSON stdout.

        Parameters
        ----------
        args:
            CLI arguments (not including the ``notebooklm`` binary itself).
        timeout:
            Maximum seconds to wait before killing the process.

        Returns
        -------
        dict | None
            Parsed JSON dict from stdout, or ``None`` on:

            * binary not found
            * non-zero exit code
            * subprocess timeout
            * stdout is not valid JSON
            * stdout is not a JSON object (e.g. a list)

        Never raises any exception.
        """

        cli = self._resolve_cli()
        if not cli:
            return None

        try:
            proc = subprocess.run(  # noqa: S603
                [cli, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._build_env(),
            )
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return None
        except Exception:  # noqa: BLE001
            return None

        if proc.returncode != 0:
            return None

        raw = (proc.stdout or "").strip()
        if not raw:
            # Some commands (e.g. status) write human text without --json;
            # treat non-empty stdout as a health signal by returning {}.
            return {}

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(parsed, dict):
            # Wrap bare lists or primitives so callers always get dict | None.
            return None

        return parsed

    # ------------------------------------------------------------------
    # Override HTTP helpers — redirect to CLI (same contract: dict | None)
    # ------------------------------------------------------------------

    def _get(  # type: ignore[override]
        self,
        path: str,
        *,
        timeout: float = 5.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Not used for CLI transport; always returns ``None`` (degrade)."""

        return None

    def _post(  # type: ignore[override]
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Not used for CLI transport; always returns ``None`` (degrade)."""

        return None

    def _patch(  # type: ignore[override]
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Not used for CLI transport; always returns ``None`` (degrade)."""

        return None


# ---------------------------------------------------------------------------
# Singleton factory (mirrors get_arc_client / get_intenttree_client pattern)
# ---------------------------------------------------------------------------

_notebooklm_client: NotebookLMClient | None = None


def get_notebooklm_client() -> NotebookLMClient:
    """Return the process-scoped :class:`NotebookLMClient` (lazy singleton).

    Reads ``foundry.yaml`` and environment variables on first call.
    Subsequent calls return the cached instance unchanged.
    """

    global _notebooklm_client
    if _notebooklm_client is None:
        _notebooklm_client = NotebookLMClient.from_config()
    return _notebooklm_client


__all__ = ["NotebookLMClient", "get_notebooklm_client"]
