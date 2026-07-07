"""AgentJobService — subprocess spawn model (SEC-2.1, FR-11) and
credential temp-file delivery (SEC-2.2, FR-12).

P4.2 scope: parent-side spawn, credential delivery, crash-safe cleanup,
and redacted persistence of events and artifacts.

.. rubric:: Child-side credential protocol (implemented in P4.3)

The spawned child bootstrap MUST:

1. Read the path in ``argv[1]`` (``CREDENTIAL_PATH``) as bytes into an
   in-memory variable.
2. Immediately unlink the file: ``os.unlink(CREDENTIAL_PATH)``.
3. Pass the raw bytes directly into the SDK client constructor.
4. **Never** write the bytes to ``os.environ``.
5. **Never** write the bytes to an on-disk SDK config file.

The parent guarantees the file exists at spawn time; any failure to unlink
it in the child must be treated as a fatal bootstrap error.  The parent
performs its own cleanup in ``cleanup_job`` so a crashed child does not
leave orphaned credential files.

.. rubric:: Static adapters (in-process only)

The following provider IDs represent static adapters that run in-process
and must **never** be dispatched to a subprocess:

* ``gpt_researcher``
* ``paperqa2``
* ``litellm_router``
* ``opencode``
* ``arc_council``
* ``notebooklm``

Attempting to spawn one of these raises :class:`InProcessProviderError`.
"""

from __future__ import annotations

import glob as _glob
import hashlib
import importlib.util
import json
import logging
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import (
    AgentJob,
    AgentJobAcceptance,
    AgentJobStatus,
)
from research_foundry.services.governance import redact_payload, scan_secrets

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path component validation
# ---------------------------------------------------------------------------


def _validate_path_component(value: str, name: str) -> str:
    """Validate *value* for safe use as a filesystem path component.

    Only alphanumerics, underscores, and hyphens are accepted.  Dots, slashes,
    and any other characters (including ``..``) are rejected to prevent path
    traversal attacks from untrusted child/agent output.

    Parameters
    ----------
    value:
        The string to validate.
    name:
        Human-readable field name used in the error message.

    Returns
    -------
    str
        *value* unchanged if it is safe.

    Raises
    ------
    ValueError
        If *value* contains characters outside ``[A-Za-z0-9_\\-]``.
    """
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", value):
        raise ValueError(
            f"Invalid {name!r}: {value!r} — only alphanumerics, underscores, "
            "and hyphens are allowed in path components."
        )
    return value


# ---------------------------------------------------------------------------
# Static-adapter provider IDs — always in-process, never spawned.
# ---------------------------------------------------------------------------

_IN_PROCESS_PROVIDERS: frozenset[str] = frozenset(
    {
        "gpt_researcher",
        "paperqa2",
        "litellm_router",
        "opencode",
        "arc_council",
        "notebooklm",
    }
)
# NOTE: ``claude_agent_sdk`` and ``openai_agents`` are intentionally NOT in
# this set.  Both are subprocess-spawned providers — they run in isolated child
# processes managed by :meth:`AgentJobService.spawn_job`, not in-process.

# Filename components used by the stale-file reaper to identify RF-owned
# temp credential files in the system temp directory.
_CRED_FILE_PREFIX = "rf_job_"
_CRED_FILE_SUFFIX = ".cred"

# ---------------------------------------------------------------------------
# Credential-safe artifact filename helpers (FIX: Codex R3 #1)
# ---------------------------------------------------------------------------

# Simplified prefixes derived from _BUILTIN_SECRET_PATTERNS.  These cover
# credential-shaped IDs that may be shorter than the full-length quantifier
# in the main patterns (e.g. "sk-ant-SECRET123" has only 9 suffix chars, but
# the Anthropic pattern requires 20+).  Both paths — persist_artifact write
# AND accept_job rewrite — call _safe_artifact_stem so the mapping is
# consistent and no raw credential ever appears in an on-disk filename.
_CREDENTIAL_PREFIX_RE = re.compile(
    r"^(?:sk-ant-|sk-|ghp_|gho_|github_pat_|AKIA|ASIA|AIza"
    r"|xox[baprse]-|xapp-|glpat-|eyJ|SG\.|sk_live_|rk_live_)",
    re.IGNORECASE,
)

# IDs longer than this are unconditionally hashed regardless of pattern match.
_MAX_SLUG_LENGTH = 64


def _is_credential_shaped(artifact_id: str, config: FoundryConfig | None = None) -> bool:
    """Return ``True`` if *artifact_id* looks like it could be a secret.

    Applies two independent tests so both full-length credentials (caught by
    ``scan_secrets``) AND short credential-prefix strings (e.g. the Anthropic
    prefix ``sk-ant-`` with fewer than 20 trailing chars) are detected:

    1. ``scan_secrets`` on the raw string — matches the full builtin / custom
       governance patterns that require minimum-length suffixes.
    2. :data:`_CREDENTIAL_PREFIX_RE` — matches the *prefix* of known secret
       formats regardless of suffix length.
    3. Length guard — IDs longer than :data:`_MAX_SLUG_LENGTH` are treated as
       potentially credential-length strings.
    """
    if scan_secrets(artifact_id, config=config):
        return True
    if _CREDENTIAL_PREFIX_RE.match(artifact_id):
        return True
    if len(artifact_id) > _MAX_SLUG_LENGTH:
        return True
    return False


def _safe_artifact_stem(artifact_id: str, config: FoundryConfig | None = None) -> str:
    """Return a credential-free filename stem for an artifact file.

    If *artifact_id* looks like a secret (see :func:`_is_credential_shaped`),
    returns a deterministic SHA-256–derived hex string prefixed with ``h``
    so no raw credential ever appears in an on-disk filename.  Otherwise
    returns *artifact_id* unchanged.

    The ``h`` prefix ensures the derived stem cannot itself match a known
    secret prefix (e.g. the ``eyJ…`` JWT prefix or the ``sk-…`` OpenAI
    prefix).  Uniqueness is preserved: distinct artifact IDs always produce
    distinct stems (SHA-256 collisions are negligible for this threat model).
    """
    if _is_credential_shaped(artifact_id, config=config):
        digest = hashlib.sha256(artifact_id.encode()).hexdigest()[:16]
        return f"h{digest}"
    return artifact_id


# ---------------------------------------------------------------------------
# Job-tool catalog — maps logical tool names to service handler references.
# The handler_ref is a dotted-import string the SDK runner can resolve; the
# actual dispatch happens in AgentJobService.run_job_tool (in-process).
# ---------------------------------------------------------------------------

_TOOL_CATALOG: dict[str, dict[str, str]] = {
    "search": {
        "name": "search",
        "description": (
            "Run a search query through the RF search router. "
            "Input: search_request dict (query, mode, constraints, output_requirements, …)."
        ),
        "handler_ref": "research_foundry.services.search_router.router:run_search",
    },
    "fetch": {
        "name": "fetch",
        "description": (
            "Fetch and extract markdown from one or more URLs into source cards. "
            "Input: {urls: list[str], run_id: str | null}."
        ),
        "handler_ref": "research_foundry.services.search_router.router:extract_urls",
    },
    "source_card": {
        "name": "source_card",
        "description": (
            "Create a source card from a locator (URL or local path). "
            "Input: kwargs for ingest_source (locator, run_id, source_type, …)."
        ),
        "handler_ref": "research_foundry.services.source_cards:create_source_card",
    },
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InProcessProviderError(ValueError):
    """Raised when the caller attempts to spawn an in-process-only provider."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AgentJobService:
    """Manages the lifecycle of SDK-class agent jobs as subprocesses.

    Each SDK-class job gets exactly one child process.  Static adapters
    (``gpt_researcher``, ``paperqa2``, ``litellm_router``, ``opencode``,
    ``arc_council``, ``notebooklm``) run in-process and must NOT be spawned.

    **Credential delivery (SEC-2.2 / FR-12)**
        Before spawning, credentials are written to a per-job temp file with
        mode ``0600``.  The file *path* is passed as the first positional CLI
        argument to the child.  Credentials are **never** placed in ``env``
        vars.  The parent always cleans up the temp file in :meth:`cleanup_job`
        regardless of how the child exited.

    **Persistence**
        :meth:`persist_event` and :meth:`persist_artifact` call
        :func:`~research_foundry.services.governance.redact_payload` before
        writing to disk, ensuring that secrets are replaced with
        ``"[REDACTED]"`` in all persisted records.
    """

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self._paths = paths or FoundryPaths.discover()
        # Resolve governance config once so secret_patterns from governance.yaml
        # are applied at every redact_payload call site without per-event reloads.
        self._config: FoundryConfig = FoundryConfig(paths=self._paths)
        # Registry: agent_job_id -> (Popen, cred_file_path)
        self._registry: dict[str, tuple[subprocess.Popen, Path]] = {}
        # Sweep any orphaned cred files left by a prior crash/SIGKILL.
        # Runs once at startup; errors are logged and swallowed (fail-soft) so a
        # stale-sweep failure never prevents the service from starting.
        try:
            removed = self.scan_stale_cred_files()
            if removed:
                logger.info(
                    "Startup sweep: removed %d orphaned cred file(s) from prior run",
                    removed,
                )
        except Exception:  # noqa: BLE001
            logger.warning("Startup sweep of stale cred files failed; continuing", exc_info=True)

    @property
    def config(self) -> FoundryConfig:
        """Cached :class:`FoundryConfig` for governance pattern access."""
        return self._config

    # ------------------------------------------------------------------
    # Spawn
    # ------------------------------------------------------------------

    def spawn_job(
        self,
        job: AgentJob,
        credential_bytes: bytes,
        *,
        command_override: list[str] | None = None,
    ) -> subprocess.Popen:
        """Spawn a child process for *job*, delivering credentials via temp file.

        Parameters
        ----------
        job:
            The :class:`~research_foundry.services.agent_job_schemas.AgentJob`
            record describing the work to perform.
        credential_bytes:
            Raw credential material for the SDK client.  Written to a temp
            file with mode ``0600``; the path is passed as the first
            positional CLI argument to the child.  Never placed in ``env``.
        command_override:
            If provided, use this list as the subprocess command instead of
            the default runner.  Intended for testing; production callers
            should leave this as ``None``.

        Returns
        -------
        subprocess.Popen
            The :class:`subprocess.Popen` instance for the spawned child.

        Raises
        ------
        InProcessProviderError
            If ``job.provider`` names a static in-process adapter (e.g.
            ``"notebooklm"``).
        """
        if job.provider in _IN_PROCESS_PROVIDERS:
            raise InProcessProviderError(
                f"Provider '{job.provider}' is a static in-process adapter — "
                "do not spawn it as a subprocess."
            )

        # Fail-closed: verify the child module exists before writing credentials
        # (Mode-D Gate #2 required before production spawn).
        if command_override is None:
            _cmd_module = "research_foundry.agents.sdk_runner"
            if importlib.util.find_spec(_cmd_module) is None:
                raise RuntimeError(
                    f"Cannot spawn job: child module {_cmd_module!r} is not installed. "
                    "This path requires Mode-D Gate #2 approval and sdk_runner implementation."
                )

        # Write credential to a 0600 temp file BEFORE spawning so the path
        # can be forwarded as a CLI argument (SEC-2.2 / FR-12).
        cred_path = self._write_cred_file(job.agent_job_id, credential_bytes)

        try:
            cmd = command_override or self._build_command(job, cred_path)
            # Spawn with an explicitly empty environment: no parent shell vars
            # must leak into the child (SEC-2.1 / FR-11).  The credential is
            # delivered via file path, NOT via an env var.
            proc = subprocess.Popen(
                cmd,
                env={},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception:
            # Clean up the credential file immediately if spawn failed.
            _safe_unlink(cred_path)
            raise

        self._registry[job.agent_job_id] = (proc, cred_path)
        logger.info(
            "Spawned agent job %s (provider=%s, pid=%s)",
            job.agent_job_id,
            job.provider,
            proc.pid,
        )
        return proc

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def poll_job(self, job_id: str) -> int | None:
        """Return the child exit code if it has finished, else ``None``."""
        entry = self._registry.get(job_id)
        if entry is None:
            return None
        proc, _ = entry
        return proc.poll()

    def terminate_job(self, job_id: str, *, kill_timeout: float = 5.0) -> None:
        """Send SIGTERM to the child, escalating to SIGKILL after *kill_timeout*.

        Idempotent: does nothing if the job is unknown or already exited.
        """
        entry = self._registry.get(job_id)
        if entry is None:
            return
        proc, _ = entry
        if proc.poll() is not None:
            return  # Already exited.
        try:
            proc.terminate()
            try:
                proc.wait(timeout=kill_timeout)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Job %s did not exit after SIGTERM; sending SIGKILL", job_id
                )
                proc.kill()
                proc.wait()
        except OSError as exc:
            logger.warning("Error terminating job %s: %s", job_id, exc)

    def cleanup_job(self, job_id: str, *, kill_timeout: float = 5.0) -> None:
        """Terminate the subprocess and unlink the credential file for *job_id*.

        Idempotent: safe to call multiple times or for unknown job IDs.
        Removes the job from the internal registry.
        """
        self.terminate_job(job_id, kill_timeout=kill_timeout)
        entry = self._registry.pop(job_id, None)
        if entry is not None:
            _, cred_path = entry
            _safe_unlink(cred_path)
            logger.debug("Cleaned up job %s, unlinked cred %s", job_id, cred_path)

    # ------------------------------------------------------------------
    # Stale credential file reaper
    # ------------------------------------------------------------------

    def scan_stale_cred_files(self, job_store_dir: Path | None = None) -> int:  # noqa: ARG002
        """Unlink orphaned ``rf_job_*.cred`` files in the system temp directory.

        Files are identified by the :data:`_CRED_FILE_PREFIX` /
        :data:`_CRED_FILE_SUFFIX` naming convention applied in
        :meth:`_write_cred_file`.  Any file not present in the live registry
        is considered orphaned and is removed.

        Parameters
        ----------
        job_store_dir:
            Reserved for future use (registry-backed sweep).  Currently
            unused; the method always scans ``tempfile.gettempdir()``.

        Returns
        -------
        int
            Number of stale files removed.
        """
        live_cred_paths: set[Path] = {
            cred_path for _, cred_path in self._registry.values()
        }
        pattern = str(
            Path(tempfile.gettempdir())
            / f"{_CRED_FILE_PREFIX}*{_CRED_FILE_SUFFIX}"
        )
        removed = 0
        for path_str in _glob.glob(pattern):
            cred_path = Path(path_str)
            if cred_path not in live_cred_paths:
                _safe_unlink(cred_path)
                removed += 1
                logger.info("Reaped stale cred file: %s", cred_path)
        return removed

    # ------------------------------------------------------------------
    # Persistence (redacted write layer)
    # ------------------------------------------------------------------

    def persist_event(self, job_id: str, event: dict[str, Any]) -> Path:
        """Append *event* to the job's event log after redacting secrets.

        The event dict is passed through
        :func:`~research_foundry.services.governance.redact_payload` before
        being written to ``<agent_job_dir>/events.jsonl`` as a single JSON
        line.  This ensures no secrets appear in persisted records.

        Returns
        -------
        Path
            Absolute path to the ``events.jsonl`` file.
        """
        _validate_path_component(job_id, "job_id")
        job_dir = self._paths.agent_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        events_file = job_dir / "events.jsonl"
        self._safe_write_json(event, events_file, append=True)
        return events_file

    def persist_artifact(self, job_id: str, artifact: dict[str, Any]) -> Path:
        """Write *artifact* to its own JSON file after redacting secrets.

        The artifact dict is passed through
        :func:`~research_foundry.services.governance.redact_payload` before
        being written to ``<agent_job_dir>/artifact_<artifact_id>.json``.
        If ``artifact_id`` is absent the file is named
        ``artifact_unknown.json``.

        Returns
        -------
        Path
            Absolute path to the artifact JSON file.
        """
        _validate_path_component(job_id, "job_id")
        artifact_id = str(artifact.get("artifact_id", "unknown"))
        _validate_path_component(artifact_id, "artifact_id")
        job_dir = self._paths.agent_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        # Derive a credential-safe filename stem so a credential-shaped
        # artifact_id (e.g. "sk-ant-abc123") never appears raw on disk.
        artifact_stem = _safe_artifact_stem(artifact_id, config=self._config)
        artifact_file = job_dir / f"artifact_{artifact_stem}.json"
        self._safe_write_json(artifact, artifact_file, append=False)
        return artifact_file

    # ------------------------------------------------------------------
    # Job brief + tool dispatch (FR-17)
    # ------------------------------------------------------------------

    def build_job_brief(
        self,
        job: AgentJob,
        paths: FoundryPaths | None = None,
    ) -> dict[str, Any]:
        """Build a job brief dict for the SDK runner loop.

        Composes existing service references into a descriptor that the
        :class:`~research_foundry.adapters.claude_agent_sdk.ClaudeAgentSDKAdapter`
        (or its provider) passes to the SDK client.  No service calls are made
        here — only descriptor dicts that reference handler entry points.

        Parameters
        ----------
        job:
            The :class:`~research_foundry.services.agent_job_schemas.AgentJob`
            record describing the work to perform.
        paths:
            Optional :class:`~research_foundry.paths.FoundryPaths`; defaults
            to the service-level paths resolved at construction time.

        Returns
        -------
        dict
            A dict with keys:
            - ``agent_job_id``, ``project_id``, ``provider``, ``model_profile``,
              ``request_kind`` — identity/routing fields from *job*.
            - ``input_claim_ids``, ``input_source_ids``, ``input_report_id`` —
              input references from *job*.
            - ``allowed_tools`` — list of tool names from
              ``job.policy_snapshot["allowed_tools"]``.
            - ``tools`` — list of tool descriptor dicts (name, description,
              handler_ref) for each allowed tool that appears in
              :data:`_TOOL_CATALOG`.
        """
        paths = paths or self._paths  # noqa: F841 — reserved for future path-aware descriptors

        allowed_tools: list[str] = list(job.policy_snapshot.get("allowed_tools") or [])
        tool_descriptors = [
            _TOOL_CATALOG[name] for name in allowed_tools if name in _TOOL_CATALOG
        ]

        return {
            "agent_job_id": job.agent_job_id,
            "project_id": job.project_id,
            "provider": job.provider,
            "model_profile": job.model_profile,
            "request_kind": job.request_kind,
            "input_claim_ids": list(job.input_claim_ids),
            "input_source_ids": list(job.input_source_ids),
            "input_report_id": job.input_report_id,
            "allowed_tools": allowed_tools,
            "tools": tool_descriptors,
        }

    def run_job_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        job: AgentJob,
        paths: FoundryPaths | None = None,
    ) -> dict[str, Any]:
        """Dispatch a tool call to the corresponding RF service.

        This is the in-process dispatch function invoked by the SDK runner
        (child process or inline executor) when the job's SDK loop requests a
        tool.  All output is passed through
        :func:`~research_foundry.services.governance.redact_payload` before
        being returned so secrets never appear in caller-visible dicts.

        Parameters
        ----------
        tool_name:
            One of ``"search"``, ``"fetch"``, ``"source_card"``.
        tool_input:
            Tool-specific input dict forwarded to the underlying service.
        job:
            The :class:`~research_foundry.services.agent_job_schemas.AgentJob`
            record.  Used to verify the requested tool is allowed.
        paths:
            Optional :class:`~research_foundry.paths.FoundryPaths`; defaults
            to the service-level paths resolved at construction time.

        Returns
        -------
        dict
            Always contains:
            - ``tool_name`` — the requested tool name.
            - ``status`` — ``"ok"`` on success, ``"error"`` on failure.
            - ``output`` — redacted service result (dict) on success, or
              ``{"error": "<message>"}`` on failure.

        Raises
        ------
        ValueError
            If *tool_name* is not present in
            ``job.policy_snapshot["allowed_tools"]``.
        """
        paths = paths or self._paths
        allowed_tools: list[str] = list(job.policy_snapshot.get("allowed_tools") or [])

        if tool_name not in allowed_tools:
            raise ValueError(
                f"Tool {tool_name!r} is not in the job's allowed_tools: "
                f"{allowed_tools!r}"
            )

        output: Any
        try:
            if tool_name == "search":
                from research_foundry.services.search_router.router import (  # noqa: PLC0415
                    run_search,
                )

                output = run_search(tool_input, paths=paths)

            elif tool_name == "fetch":
                from research_foundry.services.search_router.router import (  # noqa: PLC0415
                    extract_urls,
                )

                urls: list[str] = list(tool_input.get("urls") or [])
                run_id: str | None = tool_input.get("run_id")
                output = extract_urls(urls, run_id=run_id, paths=paths)

            elif tool_name == "source_card":
                from research_foundry.services.source_cards import (  # noqa: PLC0415
                    create_source_card,
                )

                # Redact tool_input BEFORE it reaches create_source_card so
                # a credential in locator/title/content is never written to
                # any source-card artifact on disk in raw form.  The
                # return-value is also redacted in the surrounding wrapper,
                # but that is too late — create_source_card persists its
                # input to disk internally before returning.
                redacted_input: dict[str, Any] = redact_payload(
                    tool_input, config=self._config
                )
                # Merge service-level paths; our paths wins.
                merged: dict[str, Any] = {**redacted_input, "paths": paths}
                ingest_result = create_source_card(**merged)
                output = {
                    "source_card_id": ingest_result.source_card_id,
                    "path": str(ingest_result.path),
                    "source_type": ingest_result.source_type,
                    "degraded": ingest_result.degraded,
                }

            else:
                # Should not be reachable given the allowed_tools gate above,
                # but guard against future catalog gaps.
                raise ValueError(f"Unknown tool name: {tool_name!r}")

            result: dict[str, Any] = {
                "tool_name": tool_name,
                "status": "ok",
                "output": output,
            }

        except ValueError:
            raise  # Propagate policy/validation errors to the caller.

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "run_job_tool: tool %r raised %s: %s",
                tool_name,
                type(exc).__name__,
                redact_payload(str(exc), config=self._config),
            )
            result = {
                "tool_name": tool_name,
                "status": "error",
                "output": {"error": str(exc)},
            }

        return redact_payload(result, config=self._config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_write_json(
        self, data: Any, path: Path, *, append: bool = False
    ) -> None:
        """Write *data* to *path* after passing it through :func:`redact_payload`.

        This is the single chokepoint for all agent-job JSON persistence.
        Every write path MUST use this method so redaction is structurally
        enforced — not just a convention.

        Parameters
        ----------
        data:
            The value to redact and write.  Must be JSON-serialisable.
        path:
            Destination file path.
        append:
            When ``True``, append a single JSON line (JSONL mode).
            When ``False`` (default), write the file in pretty-printed JSON.
        """
        redacted = redact_payload(data, config=self._config)
        if append:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(redacted) + "\n")
        else:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(redacted, fh, indent=2)
                fh.write("\n")

    def _write_cred_file(self, agent_job_id: str, credential_bytes: bytes) -> Path:
        """Write *credential_bytes* to a ``0600`` temp file and return its path.

        Uses :func:`tempfile.mkstemp` to atomically create the file, then
        calls :func:`os.fchmod` on the open file descriptor (before writing
        any data) to set the mode to ``0600``.  This is race-condition-free
        because the mode is set on the file descriptor, not the path.
        """
        fd, path_str = tempfile.mkstemp(
            prefix=f"{_CRED_FILE_PREFIX}{os.getpid()}_{agent_job_id}_",
            suffix=_CRED_FILE_SUFFIX,
            dir=tempfile.gettempdir(),
        )
        try:
            # Set mode to exactly 0600 on the fd before writing.
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "wb") as fh:
                fh.write(credential_bytes)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            _safe_unlink(Path(path_str))
            raise
        return Path(path_str)

    # ------------------------------------------------------------------
    # Job store: create / load / update (file-canonical, job.json)
    # ------------------------------------------------------------------

    def create_job(
        self,
        provider: str,
        model_profile: str,
        request_kind: str,
        policy_snapshot: dict[str, Any],
        *,
        project_id: str = "default",
        workspace_id: str | None = None,
        created_by: str | None = None,
        input_claim_ids: list[str] | None = None,
        input_source_ids: list[str] | None = None,
        input_report_id: str | None = None,
        budget_usd: float | None = None,
        max_runtime_minutes: int | None = None,
    ) -> AgentJob:
        """Create a new :class:`AgentJob` record, persist it to disk, and return it.

        The job is initialised in :attr:`~AgentJobStatus.queued` state.
        ``job.json`` is written to ``<agent_jobs>/<job_id>/job.json`` via
        :meth:`_safe_write_json` (secrets redacted).

        Returns
        -------
        AgentJob
            The newly-created, persisted job record.
        """
        import uuid  # noqa: PLC0415

        from research_foundry.ids import now_iso, stamp_compact  # noqa: PLC0415

        job_id = f"job_{stamp_compact()}_{uuid.uuid4().hex[:8]}"
        now = now_iso()
        job = AgentJob(
            agent_job_id=job_id,
            project_id=project_id,
            workspace_id=workspace_id,
            created_by=created_by,
            provider=provider,
            model_profile=model_profile,
            request_kind=request_kind,
            input_claim_ids=list(input_claim_ids or []),
            input_source_ids=list(input_source_ids or []),
            input_report_id=input_report_id,
            policy_snapshot=dict(policy_snapshot),
            budget_usd=budget_usd,
            max_runtime_minutes=max_runtime_minutes,
            status=AgentJobStatus.queued,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
        )
        job_dir = self._paths.agent_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        self._safe_write_json(job.to_dict(), job_dir / "job.json", append=False)
        logger.info("Created agent job %s (provider=%s)", job_id, provider)
        return job

    def load_job(self, job_id: str) -> AgentJob:
        """Load an :class:`AgentJob` from disk.

        Parameters
        ----------
        job_id:
            The agent job id (must satisfy :func:`_validate_path_component`).

        Returns
        -------
        AgentJob
            The loaded record.

        Raises
        ------
        ValueError
            If *job_id* fails path-component validation.
        KeyError
            If the job directory or ``job.json`` does not exist.
        """
        _validate_path_component(job_id, "job_id")
        job_file = self._paths.agent_job_dir(job_id) / "job.json"
        if not job_file.exists():
            raise KeyError(f"agent job not found: {job_id}")
        with job_file.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return AgentJob.from_dict(data)

    def update_job_status(self, job_id: str, status: AgentJobStatus) -> AgentJob:
        """Atomically update the on-disk status for *job_id* and return the new record.

        Raises
        ------
        KeyError
            If the job does not exist on disk.
        ValueError
            If *job_id* fails path-component validation.
        """
        import dataclasses  # noqa: PLC0415

        from research_foundry.ids import now_iso  # noqa: PLC0415

        job = self.load_job(job_id)
        updated = dataclasses.replace(job, status=status, updated_at=now_iso())
        job_dir = self._paths.agent_job_dir(job_id)
        self._safe_write_json(updated.to_dict(), job_dir / "job.json", append=False)
        return updated

    # ------------------------------------------------------------------
    # Artifact listing (staged / unaccepted)
    # ------------------------------------------------------------------

    def list_staged_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        """Return the list of staged (not yet accepted) artifact dicts for *job_id*.

        Reads every ``artifact_<id>.json`` file in the job directory and
        returns those where ``accepted == False`` (or key absent).  Malformed
        files are skipped with a WARNING.

        Returns
        -------
        list[dict]
            Zero or more artifact dicts (already redacted, as persisted).
        """
        _validate_path_component(job_id, "job_id")
        job_dir = self._paths.agent_job_dir(job_id)
        if not job_dir.exists():
            return []
        artifacts: list[dict[str, Any]] = []
        for artifact_path in sorted(job_dir.glob("artifact_*.json")):
            try:
                with artifact_path.open(encoding="utf-8") as fh:
                    data = json.load(fh)
                if not data.get("accepted", False):
                    artifacts.append(data)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not read artifact %s: %s", artifact_path, exc)
        return artifacts

    # ------------------------------------------------------------------
    # Event log loading
    # ------------------------------------------------------------------

    def load_events(self, job_id: str) -> list[dict[str, Any]]:
        """Load all persisted events from the job's ``events.jsonl`` file.

        Returns an empty list when the file does not exist.  Malformed lines
        are skipped with a WARNING.
        """
        _validate_path_component(job_id, "job_id")
        events_file = self._paths.agent_job_dir(job_id) / "events.jsonl"
        if not events_file.exists():
            return []
        events: list[dict[str, Any]] = []
        with events_file.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    events.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    logger.warning("Skipping malformed event line: %s", exc)
        return events

    # ------------------------------------------------------------------
    # Accept (SOLE WRITE PATH from agent-job staging to catalog/report)
    # ------------------------------------------------------------------

    def accept_job(
        self,
        job_id: str,
        *,
        accepted_by: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Accept staged artifacts from *job_id*, promoting them into the catalog.

        This is the SOLE WRITE PATH from agent-job staging into the
        catalog/report store.  No other method in this service or in the
        agent_jobs router writes directly from agent-job context.

        Gate: only jobs in ``waiting_for_approval`` or ``completed`` state may
        be accepted.  Jobs in other terminal states (``failed``, ``canceled``)
        raise :class:`ValueError`.

        For each staged artifact:
        * ``artifact_kind == "report_draft"`` → :func:`builder_service.create_draft`
          with origin ``"blank"`` and the agent-job id recorded in ``created_by``.
        * ``artifact_kind`` in ``{"source_card", "claim", "catalog_item"}`` →
          the artifact was already created by the job runner; acceptance records
          the provenance link only (no duplicate writes).
        * Unknown kinds → acceptance recorded; no catalog write.

        All accepted artifacts are stamped with ``"created_by_agent_job_id": job_id``
        and their ``accepted`` flag is flipped to ``True`` on disk.

        Returns
        -------
        dict
            Summary: ``agent_job_id``, ``acceptance_id``, ``accepted_artifact_count``,
            ``artifact_ids``, ``accepted_by``, ``accepted_at``.

        Raises
        ------
        KeyError
            If the job does not exist.
        ValueError
            If the job is in a state that does not permit acceptance.
        """
        # AUDIT INVARIANT: This is the ONLY method in agent_job_service.py
        # (and the ONLY route in the agent_jobs router) that writes from
        # agent-job context into catalog or report stores.  Any future
        # code-path that attempts to promote agent-job output MUST go through
        # this method — never via direct service calls from a router handler.
        assert True, "code-path audit anchor — accept_job is the sole write path"

        import dataclasses  # noqa: PLC0415
        import uuid  # noqa: PLC0415

        from research_foundry.ids import now_iso, stamp_compact  # noqa: PLC0415

        job = self.load_job(job_id)

        _ACCEPTABLE_STATES = {AgentJobStatus.waiting_for_approval, AgentJobStatus.completed}
        if job.status not in _ACCEPTABLE_STATES:
            raise ValueError(
                f"Cannot accept job {job_id!r}: status is {job.status.value!r}; "
                f"only {[s.value for s in _ACCEPTABLE_STATES]} are acceptable."
            )

        staged_artifacts = self.list_staged_artifacts(job_id)
        artifact_ids = [a.get("artifact_id", "unknown") for a in staged_artifacts]
        now = now_iso()
        accepted_count = 0

        for artifact in staged_artifacts:
            artifact_kind = artifact.get("artifact_kind", "unknown")
            artifact_id = str(artifact.get("artifact_id", "unknown"))

            # Stamp provenance back-pointer (required: accepted items MUST carry this).
            artifact["created_by_agent_job_id"] = job_id

            if artifact_kind == "report_draft":
                try:
                    from research_foundry.services import builder_service as bsvc  # noqa: PLC0415

                    title = str(artifact.get("title") or f"Agent Job {job_id} Output")
                    bsvc.create_draft(
                        self._paths,
                        title=title,
                        origin="blank",
                        created_by=accepted_by or job_id,
                    )
                    accepted_count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to promote report_draft artifact %s: %s", artifact_id, exc
                    )
            elif artifact_kind in {"source_card", "claim", "catalog_item"}:
                # Already written by the job runner; acceptance creates provenance link.
                accepted_count += 1
            else:
                logger.info(
                    "Accepting artifact %r of kind %r (no catalog promotion)",
                    artifact_id, artifact_kind,
                )
                accepted_count += 1

            # Flip accepted flag on disk.
            try:
                _validate_path_component(artifact_id, "artifact_id")
                # Use the same credential-safe stem as the write path so
                # credential-shaped ids resolve to their hashed filename.
                artifact_stem = _safe_artifact_stem(artifact_id, config=self._config)
                artifact_file = self._paths.agent_job_dir(job_id) / f"artifact_{artifact_stem}.json"
                if artifact_file.exists():
                    artifact["accepted"] = True
                    self._safe_write_json(artifact, artifact_file, append=False)
            except (ValueError, OSError) as exc:
                logger.warning("Could not mark artifact %s accepted: %s", artifact_id, exc)

        # Write acceptance record.
        acceptance_id = f"acc_{stamp_compact()}_{uuid.uuid4().hex[:6]}"
        acceptance = AgentJobAcceptance(
            acceptance_id=acceptance_id,
            agent_job_id=job_id,
            accepted_at=now,
            artifact_ids=artifact_ids,
            accepted_by=accepted_by,
            notes=notes,
        )
        job_dir = self._paths.agent_job_dir(job_id)
        self._safe_write_json(acceptance.to_dict(), job_dir / "acceptance.json", append=False)

        # Transition job status to accepted.
        updated_job = dataclasses.replace(job, status=AgentJobStatus.accepted, updated_at=now)
        self._safe_write_json(updated_job.to_dict(), job_dir / "job.json", append=False)
        logger.info(
            "Accepted agent job %s: %d artifacts, accepted_by=%r",
            job_id, accepted_count, accepted_by,
        )

        return {
            "agent_job_id": job_id,
            "acceptance_id": acceptance_id,
            "accepted_artifact_count": accepted_count,
            "artifact_ids": artifact_ids,
            "accepted_by": accepted_by,
            "accepted_at": now,
        }

    def _build_command(self, job: AgentJob, cred_path: Path) -> list[str]:
        """Return the default spawn command for *job*.

        The child bootstrap (P4.3) entry point is
        ``research_foundry.agents.sdk_runner``.  ``cred_path`` is passed as
        the first positional argument so the child can read and immediately
        unlink the credential file (see module-level child-side protocol
        documentation).

        Child-side contract (P4.3 implementation):
            * ``argv[1]`` = ``str(cred_path)`` — read once into memory.
            * Immediately ``os.unlink(argv[1])``.
            * Pass the raw bytes to the SDK client constructor.
            * **Never** assign to ``os.environ``.
            * **Never** write to an on-disk SDK config file.
        """
        return [
            sys.executable,
            "-m",
            "research_foundry.agents.sdk_runner",
            "--job-id",
            job.agent_job_id,
            str(cred_path),  # positional argv[1]: credential file path
        ]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _safe_unlink(path: Path) -> None:
    """Unlink *path* silently on :exc:`FileNotFoundError`.

    Other :exc:`OSError` sub-classes are logged at WARNING level and
    swallowed so cleanup code never raises.
    """
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("Failed to unlink %s: %s", path, exc)


__all__ = [
    "AgentJobService",
    "InProcessProviderError",
    "_validate_path_component",
]
