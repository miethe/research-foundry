"""AgentJob attempt adapter for the local-stdio Operator MCP
(research-foundry-operator-mcp-v1 P2, OPM-2.2).

This module does NOT reimplement job management. It is a thin, identity-
scoped wrapper around the existing :class:`~research_foundry.services.
agent_job_service.AgentJobService` -- every "attempt" IS an
:class:`~research_foundry.services.agent_job_schemas.AgentJob`; this module
adds exactly two things ``AgentJobService`` does not already provide:

1. **A durable, queryable link between an attempt and the Operator MCP
   ``operation_id`` that spawned it**, in BOTH directions (operation -> its
   attempts, attempt -> its operation). Confirmations and operation
   manifests already live in ``paths.operator_operations_db`` (see
   ``operator_operation_service.py``, OPM-2.1's module docstring for why
   that file, under ``.rf_state/``, is the sanctioned durable store for
   Operator-MCP-owned state) -- this module adds one more additive table,
   ``attempts``, to that SAME database file rather than inventing a second
   store. It does NOT modify ``operator_operation_service.py`` to do this;
   it opens its own connection to the same db path, mirroring that module's
   own ``_connect``/``_ensure_schema``/``BEGIN IMMEDIATE`` idiom (which
   itself mirrors ``services/rbac_store.py``) independently, so ownership of
   the ``operations``/``confirmations`` tables stays exactly where OPM-2.1
   left it.

2. **A single, uniformly-applied identity/workspace-scoping gate** in front
   of every wrapped call. ``AgentJobService`` itself only threads
   ``identity`` through :meth:`~AgentJobService.create_job` and
   :meth:`~AgentJobService.load_job` -- ``load_events``,
   ``list_staged_artifacts``, ``persist_event``, ``persist_artifact``,
   ``update_job_status``, ``poll_job``, ``terminate_job``, and
   ``cleanup_job`` take no ``identity`` parameter at all. Every wrapper
   method here therefore calls ``AgentJobService.load_job(attempt_id,
   identity=identity)`` FIRST -- exactly the same call ``load_attempt``
   itself makes -- before delegating to the corresponding unscoped
   ``AgentJobService`` method. A caller whose identity does not resolve
   under ``load_job``'s own workspace-scope predicate never reaches the
   wrapped call at all.

**Wrong-workspace attempts are indistinguishable from missing (AC OPM-2.2)**:
this module never catches, re-wraps, or re-messages the ``KeyError`` /
``ValueError`` raised by ``AgentJobService.load_job`` -- it propagates
verbatim. Since ``load_job`` itself already raises the identical
``KeyError`` (same type, same message text, ``f"agent job not found:
{job_id}"``) for both a genuinely missing job and a workspace-scope denial
(differing only in a server-side ``ERROR`` log line -- see its own
docstring), every wrapper in this module inherits that exact guarantee for
free, without re-deriving or duplicating the scoping predicate.

**``accept_job`` is deliberately unreachable through this adapter.** It is
the SOLE write path from agent-job staging into the catalog/report store
(see ``AgentJobService.accept_job``'s own docstring) and is out of scope for
this adapter (OPM-2.2's plan row explicitly excludes it). This module:

* never calls ``self._jobs.accept_job`` anywhere;
* never exposes ``self._jobs`` (or any other reference to the wrapped
  ``AgentJobService`` instance) as a public attribute or return value; and
* defines no method whose name contains ``accept``.

**Cross-store atomicity gap (documented, not silently papered over)**: an
attempt's ``AgentJob`` record (``job.json``, a plain file under
``agent_jobs/<job_id>/``) and its link row in the ``attempts`` table (a
SEPARATE sqlite database) are two different storage engines -- exactly the
same limitation ``operator_operation_service.py``'s own module docstring
calls out for why confirmations and operation manifests must live in ONE
database (they do; this module's own link write does not, and cannot,
extend that same transaction to a plain JSON file write). If the job.json
write in :meth:`OperatorAttemptAdapter.create_attempt` succeeds but the
subsequent ``attempts`` table INSERT fails, the created ``AgentJob`` is left
on disk with NO durable link to its ``operation_id`` -- an orphaned attempt,
not a corrupted operation manifest (OPM-2.1's own durability guarantees are
untouched). This module raises loudly (logs at ``ERROR`` with the orphaned
``attempt_id``/``operation_id`` and re-raises) rather than swallowing that
failure, but it cannot roll back the already-written ``job.json`` -- there
is no ``AgentJobService.delete_job``. Flagged here rather than solved
because solving it would require a delete/cleanup path on
``agent_job_service.py`` itself, a file this task's HARD CONSTRAINTS list as
a serialization-barrier module this task must wrap, never edit.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService

if TYPE_CHECKING:
    from research_foundry.api.auth.provider import AuthIdentity

logger = logging.getLogger(__name__)

__all__ = [
    "AttemptRecord",
    "OperatorAttemptAdapter",
]

# ---------------------------------------------------------------------------
# Storage: additive ``attempts`` table in the SAME db OPM-2.1 already owns.
# ---------------------------------------------------------------------------

#: Explicit busy-timeout, matching ``operator_operation_service.py``'s own
#: constant exactly -- both modules write to the SAME db file, so lock
#: contention between them must resolve under the same deterministic window.
_BUSY_TIMEOUT_MS = 15_000

_ATTEMPTS_DDL: tuple[str, ...] = (
    # attempt_id == the wrapped AgentJob's agent_job_id -- an "attempt" IS
    # an AgentJob execution instance; there is no separate id namespace.
    # workspace_id is nullable (mirrors AgentJob.workspace_id itself being
    # nullable -- legacy/no-identity jobs have no workspace_id).
    """
    CREATE TABLE IF NOT EXISTS attempts (
        attempt_id      TEXT PRIMARY KEY,
        operation_id    TEXT NOT NULL,
        workspace_id    TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_attempts_operation
        ON attempts (operation_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_attempts_workspace
        ON attempts (workspace_id)
    """,
)


def _connect(paths: FoundryPaths) -> sqlite3.Connection:
    """Open (or create) the SAME durable db ``operator_operation_service.py``
    owns (``paths.operator_operations_db``, under ``.rf_state/``).

    An independent connection function rather than importing
    ``operator_operation_service._connect`` -- this module must not modify
    that module, and duplicating its short, already-mirrored-from-
    ``rbac_store.py`` idiom locally keeps ownership of the ``operations``/
    ``confirmations`` tables entirely with OPM-2.1 while still writing into
    the same physical database file.
    """

    paths.rf_state.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(paths.operator_operations_db),
        isolation_level=None,
        timeout=_BUSY_TIMEOUT_MS / 1000,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    return conn


def _ensure_attempts_schema(conn: sqlite3.Connection) -> None:
    """Additive-only: every statement uses ``IF NOT EXISTS``, safe to call on
    every connection open, mirroring ``operator_operation_service._ensure_schema``.
    """

    for stmt in _ATTEMPTS_DDL:
        conn.execute(stmt)


def _record_attempt_link(
    paths: FoundryPaths,
    *,
    attempt_id: str,
    operation_id: str,
    workspace_id: str | None,
    created_at: str,
) -> None:
    """Durably persist the attempt<->operation link row.

    A single ``INSERT`` under ``BEGIN IMMEDIATE``, mirroring
    ``operator_operation_service.record_confirmation``'s own transaction
    shape exactly (open -> ensure schema -> BEGIN IMMEDIATE -> INSERT ->
    COMMIT, ROLLBACK on any exception).
    """

    conn = _connect(paths)
    try:
        _ensure_attempts_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "INSERT INTO attempts (attempt_id, operation_id, workspace_id, created_at)"
                " VALUES (?, ?, ?, ?)",
                (attempt_id, operation_id, workspace_id, created_at),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def _lookup_operation_id(paths: FoundryPaths, attempt_id: str) -> str | None:
    """Return the linked ``operation_id`` for *attempt_id*, or ``None`` if no
    link row exists.

    ``None`` (never an exception) is the correct result for a legacy
    ``AgentJob`` created directly via ``AgentJobService.create_job`` --
    before this adapter existed, or by any other caller that bypasses
    :meth:`OperatorAttemptAdapter.create_attempt` -- since such a job has no
    row in ``attempts`` at all. This is what makes "legacy AgentJob reads
    still pass" true: the absence of a link is not an error condition.
    """

    conn = _connect(paths)
    try:
        _ensure_attempts_schema(conn)
        row = conn.execute(
            "SELECT operation_id FROM attempts WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
    finally:
        conn.close()
    return row["operation_id"] if row is not None else None


def _list_attempt_ids_for_operation(paths: FoundryPaths, operation_id: str) -> list[str]:
    """Return every ``attempt_id`` linked to *operation_id*, oldest first.

    Deliberately does NOT filter by workspace here -- see
    :meth:`OperatorAttemptAdapter.list_attempts_for_operation`'s docstring
    for why workspace scoping for the list path is applied uniformly via
    ``AgentJobService.load_job`` per-candidate, the SAME single source of
    policy truth the single-attempt read path uses, rather than a second,
    independently-maintained SQL-level predicate that could silently diverge
    from it.
    """

    conn = _connect(paths)
    try:
        _ensure_attempts_schema(conn)
        rows = conn.execute(
            "SELECT attempt_id FROM attempts WHERE operation_id = ? ORDER BY created_at",
            (operation_id,),
        ).fetchall()
    finally:
        conn.close()
    return [row["attempt_id"] for row in rows]


# ---------------------------------------------------------------------------
# Value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttemptRecord:
    """An attempt (== an :class:`AgentJob`) together with its linked
    Operator MCP ``operation_id`` (``None`` for a legacy/unlinked job)."""

    attempt_id: str
    operation_id: str | None
    job: AgentJob


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class OperatorAttemptAdapter:
    """Identity-scoped wrapper over :class:`AgentJobService`, linking each
    attempt to the Operator MCP ``operation_id`` that created it.

    See module docstring for the full contract. ``accept_job`` is
    deliberately NOT wrapped or otherwise reachable through this class.
    """

    def __init__(
        self,
        paths: FoundryPaths,
        *,
        job_service: AgentJobService | None = None,
    ) -> None:
        self._paths = paths
        # Underscore-private: never exposed as a public attribute/property,
        # so a caller cannot reach ``accept_job`` (or any other
        # ``AgentJobService`` method this adapter deliberately does not
        # wrap) through an adapter instance.
        self._jobs = job_service or AgentJobService(paths)

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def create_attempt(
        self,
        operation_id: str,
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
        identity: "AuthIdentity | None" = None,
    ) -> AttemptRecord:
        """Create a new attempt (``AgentJobService.create_job``) durably
        linked to *operation_id*.

        ``identity`` is forwarded to ``create_job`` UNCHANGED --
        ``create_job``'s own DF-004 identity-overrides-client-input
        behaviour (an authenticated identity's ``workspace_id`` always wins
        over the *workspace_id* parameter) is preserved exactly, never
        bypassed or re-implemented here.

        Raises
        ------
        ValueError
            If *operation_id* is empty or not a string -- a durable link
            with no operation to point at is a caller programming error,
            never silently accepted.
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("create_attempt requires a non-empty operation_id")

        job = self._jobs.create_job(
            provider,
            model_profile,
            request_kind,
            policy_snapshot,
            project_id=project_id,
            workspace_id=workspace_id,
            created_by=created_by,
            input_claim_ids=input_claim_ids,
            input_source_ids=input_source_ids,
            input_report_id=input_report_id,
            budget_usd=budget_usd,
            max_runtime_minutes=max_runtime_minutes,
            identity=identity,
        )

        try:
            _record_attempt_link(
                self._paths,
                attempt_id=job.agent_job_id,
                operation_id=operation_id,
                workspace_id=job.workspace_id,
                created_at=ids.now_iso(),
            )
        except Exception:
            # See module docstring's "cross-store atomicity gap" section:
            # the AgentJob is already durably persisted on disk at this
            # point and cannot be rolled back from here. Log loudly
            # server-side (never swallow) and re-raise so the caller knows
            # attempt creation did not complete cleanly.
            logger.error(
                "operator_attempt_adapter: failed to link attempt %s to "
                "operation %s after job creation succeeded -- attempt is "
                "now ORPHANED (no durable operation link)",
                job.agent_job_id,
                operation_id,
                exc_info=True,
            )
            raise

        return AttemptRecord(attempt_id=job.agent_job_id, operation_id=operation_id, job=job)

    # ------------------------------------------------------------------
    # load
    # ------------------------------------------------------------------

    def load_attempt(
        self, attempt_id: str, *, identity: "AuthIdentity | None" = None
    ) -> AttemptRecord:
        """Load an attempt by id, identity-scoped exactly like
        ``AgentJobService.load_job`` (see module docstring's "wrong-workspace
        attempts are indistinguishable from missing" section -- this method
        neither catches nor re-messages ``load_job``'s exceptions).
        """

        job = self._jobs.load_job(attempt_id, identity=identity)
        operation_id = _lookup_operation_id(self._paths, attempt_id)
        return AttemptRecord(attempt_id=attempt_id, operation_id=operation_id, job=job)

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------

    def load_events(
        self, attempt_id: str, *, identity: "AuthIdentity | None" = None
    ) -> list[dict[str, Any]]:
        """Identity-gated wrapper over ``AgentJobService.load_events``."""

        self._jobs.load_job(attempt_id, identity=identity)
        return self._jobs.load_events(attempt_id)

    def persist_event(
        self,
        attempt_id: str,
        event: dict[str, Any],
        *,
        identity: "AuthIdentity | None" = None,
    ) -> Path:
        """Identity-gated wrapper over ``AgentJobService.persist_event``."""

        self._jobs.load_job(attempt_id, identity=identity)
        return self._jobs.persist_event(attempt_id, event)

    # ------------------------------------------------------------------
    # artifacts
    # ------------------------------------------------------------------

    def list_artifacts(
        self, attempt_id: str, *, identity: "AuthIdentity | None" = None
    ) -> list[dict[str, Any]]:
        """Identity-gated wrapper over ``AgentJobService.list_staged_artifacts``."""

        self._jobs.load_job(attempt_id, identity=identity)
        return self._jobs.list_staged_artifacts(attempt_id)

    def persist_artifact(
        self,
        attempt_id: str,
        artifact: dict[str, Any],
        *,
        identity: "AuthIdentity | None" = None,
    ) -> Path:
        """Identity-gated wrapper over ``AgentJobService.persist_artifact``."""

        self._jobs.load_job(attempt_id, identity=identity)
        return self._jobs.persist_artifact(attempt_id, artifact)

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------

    def get_status(
        self, attempt_id: str, *, identity: "AuthIdentity | None" = None
    ) -> AgentJobStatus:
        """Identity-gated current status read (``AgentJob.status``)."""

        job = self._jobs.load_job(attempt_id, identity=identity)
        return job.status

    def update_status(
        self,
        attempt_id: str,
        status: AgentJobStatus,
        *,
        identity: "AuthIdentity | None" = None,
    ) -> AttemptRecord:
        """Identity-gated wrapper over ``AgentJobService.update_job_status``.

        ``update_job_status`` itself takes no ``identity`` parameter and
        calls ``load_job`` internally WITHOUT one -- this wrapper performs
        its own identity-scoped ``load_job`` gate FIRST so a wrong-workspace
        caller cannot reach the write at all.
        """

        self._jobs.load_job(attempt_id, identity=identity)
        updated_job = self._jobs.update_job_status(attempt_id, status)
        operation_id = _lookup_operation_id(self._paths, attempt_id)
        return AttemptRecord(attempt_id=attempt_id, operation_id=operation_id, job=updated_job)

    # ------------------------------------------------------------------
    # poll / terminate / cleanup
    # ------------------------------------------------------------------

    def poll_attempt(
        self, attempt_id: str, *, identity: "AuthIdentity | None" = None
    ) -> int | None:
        """Identity-gated wrapper over ``AgentJobService.poll_job``."""

        self._jobs.load_job(attempt_id, identity=identity)
        return self._jobs.poll_job(attempt_id)

    def terminate_attempt(
        self,
        attempt_id: str,
        *,
        identity: "AuthIdentity | None" = None,
        kill_timeout: float = 5.0,
    ) -> None:
        """Identity-gated wrapper over ``AgentJobService.terminate_job``."""

        self._jobs.load_job(attempt_id, identity=identity)
        self._jobs.terminate_job(attempt_id, kill_timeout=kill_timeout)

    def cleanup_attempt(
        self,
        attempt_id: str,
        *,
        identity: "AuthIdentity | None" = None,
        kill_timeout: float = 5.0,
    ) -> None:
        """Identity-gated wrapper over ``AgentJobService.cleanup_job``."""

        self._jobs.load_job(attempt_id, identity=identity)
        self._jobs.cleanup_job(attempt_id, kill_timeout=kill_timeout)

    # ------------------------------------------------------------------
    # operation -> attempts (the reverse link direction)
    # ------------------------------------------------------------------

    def list_attempts_for_operation(
        self, operation_id: str, *, identity: "AuthIdentity | None" = None
    ) -> list[AttemptRecord]:
        """Return every attempt linked to *operation_id*, identity-scoped.

        Fetches candidate ``attempt_id``s unscoped from the ``attempts``
        table, then calls :meth:`load_attempt` (the SAME identity-scoped
        gate every other read in this class uses) for each candidate,
        silently skipping any that raise ``KeyError`` under this identity's
        scope. This keeps workspace-scoping policy in exactly ONE place
        (``AgentJobService.load_job``) rather than duplicating it as a
        second, independently-maintained SQL predicate that could silently
        diverge from it.
        """

        records: list[AttemptRecord] = []
        for attempt_id in _list_attempt_ids_for_operation(self._paths, operation_id):
            try:
                records.append(self.load_attempt(attempt_id, identity=identity))
            except KeyError:
                # Scoped out under this identity -- never surfaced as a
                # partial/leaked record (mirrors load_job's own
                # indistinguishable-from-missing convention).
                continue
        return records
