"""OpenAIAgentsProvider — ResearchAgentProvider backed by AgentJobService subprocesses.

Implements the full :class:`ResearchAgentProvider` Protocol for the
``openai_agents`` backend, wrapping the subprocess-isolation boundary
provided by :class:`~research_foundry.services.agent_job_service.AgentJobService`.

**Credential constraint (Mode-D Gate #2 not yet approved)**:
The ``credential_bytes_factory`` constructor param defaults to a zero-argument
callable that returns ``b"test-mock-openai-key-stub"``.  All test and offline
usage MUST rely on this default or a custom factory that similarly returns stub
bytes.  Real API credential factories MUST NOT be wired in until Gate #2 is
approved.

**Write-path constraint**:
Every JSON write to disk MUST go through
:meth:`AgentJobService._safe_write_json`, which calls
:func:`~research_foundry.services.governance.redact_payload` as a structural
invariant.  Do not bypass this chokepoint.
"""

from __future__ import annotations

import glob as _glob
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.agent_providers.base import BaseProvider, register

logger = logging.getLogger(__name__)

# Stub credential bytes used in tests / offline mode (Gate #2 not yet approved).
_TEST_CREDENTIAL_BYTES = b"test-mock-openai-key-stub"


def _iso_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class OpenAIAgentsProvider(BaseProvider):
    """ResearchAgentProvider for the ``openai_agents`` backend.

    Wraps :class:`~research_foundry.services.agent_job_service.AgentJobService`
    so each research job runs as an isolated child process (SEC-2.1 / FR-11).

    Parameters
    ----------
    job_service:
        An optional pre-built :class:`AgentJobService`.  Defaults to a service
        auto-discovered from the current workspace.  Inject a mock in tests to
        avoid real subprocess spawning.
    credential_bytes_factory:
        A zero-argument callable returning the raw credential bytes delivered
        to the child process via a ``0600`` temp file.  Defaults to a factory
        that returns ``b"test-mock-openai-key-stub"`` (safe for offline / CI use).

        **Constraint**: MUST NOT return real API credentials until Mode-D
        Gate #2 is approved.  Never read ``OPENAI_API_KEY`` or any other
        live credential in this factory until that gate opens.
    """

    id = "openai_agents"

    def __init__(
        self,
        *,
        job_service: AgentJobService | None = None,
        credential_bytes_factory: Callable[[], bytes] | None = None,
    ) -> None:
        self._svc = job_service or AgentJobService()
        self._cred_factory: Callable[[], bytes] = (
            credential_bytes_factory or (lambda: _TEST_CREDENTIAL_BYTES)
        )

    # ------------------------------------------------------------------
    # ResearchAgentProvider Protocol
    # ------------------------------------------------------------------

    def start_job(self, job: dict[str, Any]) -> str:
        """Build an AgentJob record, spawn the child process, and return the job_id.

        The ``job_id`` is taken from ``job["agent_job_id"]`` or
        ``job["job_id"]`` if present, otherwise a fresh UUID hex is generated.
        Credential bytes are obtained from :attr:`_cred_factory` — in test
        mode this returns ``b"test-mock-openai-key-stub"``.

        Parameters
        ----------
        job:
            A dict with the job parameters.  Any field recognised by
            :class:`~research_foundry.services.agent_job_schemas.AgentJob`
            can be supplied.  ``policy_snapshot.allowed_tools`` and
            ``policy_snapshot.data_scopes`` are injected as empty lists if
            missing.

        Returns
        -------
        str
            The ``job_id`` under which the job was registered in the service.
        """
        job_id = str(job.get("agent_job_id") or job.get("job_id") or uuid.uuid4().hex)
        now = _iso_now()

        # Ensure the policy_snapshot has the mandatory fields so downstream
        # validation does not trip.
        policy_snapshot: dict[str, Any] = dict(job.get("policy_snapshot") or {})
        policy_snapshot.setdefault("allowed_tools", [])
        policy_snapshot.setdefault("data_scopes", [])

        agent_job = AgentJob(
            agent_job_id=job_id,
            project_id=str(job.get("project_id") or "default"),
            workspace_id=job.get("workspace_id"),
            created_by=job.get("created_by"),
            provider=self.id,
            model_profile=str(job.get("model_profile") or "rf_synthesize_deep"),
            request_kind=str(job.get("request_kind") or "research"),
            input_claim_ids=list(job.get("input_claim_ids") or []),
            input_source_ids=list(job.get("input_source_ids") or []),
            input_report_id=job.get("input_report_id"),
            policy_snapshot=policy_snapshot,
            budget_usd=job.get("budget_usd"),
            max_runtime_minutes=job.get("max_runtime_minutes"),
            status=AgentJobStatus.queued,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
        )

        cred_bytes = self._cred_factory()
        self._svc.spawn_job(agent_job, cred_bytes)
        logger.info("OpenAIAgentsProvider: started job %s", job_id)

        # Persist a guardrails_registered event when the policy declares
        # allowed_tools or data_scopes so downstream consumers can audit the
        # guardrail configuration that was in effect at job start (AC-4.2).
        _allowed_tools: list[str] = list(policy_snapshot.get("allowed_tools") or [])
        _data_scopes: list[str] = list(policy_snapshot.get("data_scopes") or [])
        if _allowed_tools or _data_scopes:
            try:
                self._svc.persist_event(
                    job_id,
                    {
                        "type": "guardrails_registered",
                        "allowed_tools": _allowed_tools,
                        "data_scopes": _data_scopes,
                        "provider": self.id,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                # Non-fatal: log at INFO so CI/tests can observe the skip without
                # a noisy WARNING when the job directory cannot be written (e.g.
                # a mock service with a read-only temp dir).
                logger.info(
                    "OpenAIAgentsProvider: guardrails_registered event could not be "
                    "persisted for job %s: %s",
                    job_id,
                    exc,
                )

        return job_id

    def stream_events(self, job_id: str) -> Iterator[dict[str, Any]]:
        """Yield progress events from the job's ``events.jsonl`` file.

        Handles missing, empty, or partially-written files gracefully — yields
        nothing rather than raising.  Malformed JSON lines are skipped with a
        warning.

        Parameters
        ----------
        job_id:
            The job identifier returned by :meth:`start_job`.

        Yields
        ------
        dict[str, Any]
            Parsed event records as written by
            :meth:`AgentJobService.persist_event`.
        """
        job_dir = self._svc._paths.agent_job_dir(job_id)
        events_file = job_dir / "events.jsonl"
        if not events_file.exists():
            return
        try:
            with events_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        yield json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            "Skipping malformed event line in %s: %s",
                            events_file,
                            exc,
                        )
        except OSError as exc:
            logger.warning(
                "Could not read events file %s: %s", events_file, exc
            )

    def cancel_job(self, job_id: str) -> None:
        """Terminate the subprocess and clean up job resources.

        Calls :meth:`AgentJobService.terminate_job` (SIGTERM → SIGKILL) then
        :meth:`AgentJobService.cleanup_job` (unlink cred file, remove from
        registry).  Both calls are idempotent; it is safe to cancel a job that
        has already exited.
        """
        self._svc.terminate_job(job_id)
        self._svc.cleanup_job(job_id)

    def list_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        """Scan ``artifact_*.json`` files in the job directory.

        Returns an empty list when the job directory does not exist or contains
        no artifact files.  Unreadable or malformed files are skipped with a
        warning.

        Parameters
        ----------
        job_id:
            The job identifier returned by :meth:`start_job`.

        Returns
        -------
        list[dict[str, Any]]
            Parsed artifact records, sorted by file name.
        """
        job_dir = self._svc._paths.agent_job_dir(job_id)
        if not job_dir.is_dir():
            return []
        artifacts: list[dict[str, Any]] = []
        pattern = str(job_dir / "artifact_*.json")
        for path_str in sorted(_glob.glob(pattern)):
            try:
                with Path(path_str).open("r", encoding="utf-8") as fh:
                    artifacts.append(json.load(fh))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping unreadable artifact file %s: %s", path_str, exc
                )
        return artifacts

    def accept_artifacts(
        self, job_id: str, artifact_ids: list[str]
    ) -> None:
        """Mark a subset of artifacts as accepted.

        For each ``artifact_id`` in *artifact_ids*:

        1. Reads ``<agent_job_dir>/artifact_<artifact_id>.json``.
        2. Sets ``"accepted": true`` in the record.
        3. Writes the updated record back via
           :meth:`AgentJobService._safe_write_json` (redaction enforced).

        Additionally, an ``acceptance.json`` file in the job directory is
        created or updated with a running list of all accepted artifact IDs and
        the timestamp of the last acceptance operation.  This file is also
        written through :meth:`AgentJobService._safe_write_json`.

        Missing artifact files are logged as warnings and skipped; they do not
        cause the call to raise.

        Parameters
        ----------
        job_id:
            The job identifier returned by :meth:`start_job`.
        artifact_ids:
            IDs of artifacts to accept (must match the ``artifact_id`` field
            written by :meth:`AgentJobService.persist_artifact`).
        """
        job_dir = self._svc._paths.agent_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        accepted_now: list[str] = []
        for artifact_id in artifact_ids:
            artifact_path = job_dir / f"artifact_{artifact_id}.json"
            if not artifact_path.exists():
                logger.warning(
                    "accept_artifacts: artifact file not found — job=%s artifact=%s",
                    job_id,
                    artifact_id,
                )
                continue
            try:
                with artifact_path.open("r", encoding="utf-8") as fh:
                    data: dict[str, Any] = json.load(fh)
                data["accepted"] = True
                # Every write MUST go through the redaction chokepoint.
                self._svc._safe_write_json(data, artifact_path, append=False)
                accepted_now.append(artifact_id)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Could not accept artifact %s/%s: %s",
                    job_id,
                    artifact_id,
                    exc,
                )

        if not accepted_now:
            return

        # Update (or create) the acceptance.json record for the job.
        acceptance_path = job_dir / "acceptance.json"
        if acceptance_path.exists():
            try:
                with acceptance_path.open("r", encoding="utf-8") as fh:
                    acceptance: dict[str, Any] = json.load(fh)
            except (OSError, json.JSONDecodeError):
                acceptance = {"job_id": job_id, "accepted_artifact_ids": []}
        else:
            acceptance = {"job_id": job_id, "accepted_artifact_ids": []}

        existing: list[str] = list(acceptance.get("accepted_artifact_ids") or [])
        # Deduplicate while preserving insertion order.
        merged: list[str] = list(dict.fromkeys(existing + accepted_now))
        acceptance["accepted_artifact_ids"] = merged
        acceptance["last_accepted_at"] = _iso_now()

        # Write through the redaction chokepoint.
        self._svc._safe_write_json(acceptance, acceptance_path, append=False)

        logger.info(
            "OpenAIAgentsProvider: accepted artifacts %s for job %s",
            accepted_now,
            job_id,
        )


# ---------------------------------------------------------------------------
# Module-level registration
# ---------------------------------------------------------------------------

register(OpenAIAgentsProvider())

__all__ = ["OpenAIAgentsProvider"]
