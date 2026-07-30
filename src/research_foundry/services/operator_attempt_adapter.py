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
   Operator-MCP-owned state) -- the ``attempts`` table lives in that SAME
   database file rather than a second store. **P2-ARCH-1 update**: this
   module used to create that table itself, independently; it now opens
   ``operator_operation_service._connect``'s connection and calls that
   module's ``_ensure_schema`` (the SOLE schema authority for this database
   file as of OPM-2.3 -- see that module's ``_SCHEMA_VERSION`` docstring)
   before every DML statement, using the SAME ``BEGIN IMMEDIATE`` idiom
   (which itself mirrors ``services/rbac_store.py``) it always has. Table
   ownership (``operations``/``confirmations``/``attempts``/the four OPM-2.3
   receipt tables) is now entirely OPM-2.1's; this module writes DML rows
   into ``attempts`` only, never DDL.

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
sqlite table) are two different storage engines -- exactly the same
limitation ``operator_operation_service.py``'s own module docstring calls
out for why confirmations and operation manifests must live in ONE
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

**P2-ARCH-1 (OPM-2.3 schema consolidation)**: this module used to own a
private ``CREATE TABLE IF NOT EXISTS attempts`` DDL path (its own
``_ensure_attempts_schema``), independent of and uncoordinated with
``operator_operation_service.py``'s ``PRAGMA user_version``-gated
migrations -- a second, uncoordinated schema author on the SAME database
file. ``operator_operation_service._ensure_schema`` is now the SOLE schema/
migration authority for ``paths.operator_operations_db`` (the ``attempts``
table DDL moved there verbatim, under schema version 2); this module now
imports and calls that module's ``_connect``/``_ensure_schema`` directly
(a deliberate, directed cross-module reach into leading-underscore helpers
-- see that module's ``_SCHEMA_VERSION`` docstring) for DML only. It never
issues a ``CREATE TABLE``/``CREATE INDEX``/``CREATE TRIGGER`` of its own
anymore.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_operation_service as _ops_store
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService

if TYPE_CHECKING:
    from research_foundry.api.auth.provider import AuthIdentity

logger = logging.getLogger(__name__)

__all__ = [
    "AttemptRecord",
    "OperatorAttemptAdapter",
    "AttemptLimitExceededError",
    "AttemptStoreUnavailableError",
    "MAX_ATTEMPTS_PER_OPERATION",
]


# ---------------------------------------------------------------------------
# K3-BLOCK-1 / K4-BLOCK-1 / K4-NB-1 sibling instance in THIS module: this
# module's three private DML/read helpers each open
# `paths.operator_operations_db` via `operator_operation_service`'s own
# `_connect`/`_ensure_schema` (see module docstring's P2-ARCH-1 section) and,
# until this fix, had ZERO `except sqlite3` handling on any of them -- a
# contending writer (another attempt being linked/looked-up concurrently, or
# a cold-start DDL race) raised a raw `sqlite3.OperationalError` ("database
# is locked", full driver text) straight out of this module's boundary, the
# exact defect class K3-BLOCK-1/K4-BLOCK-1/K4-NB-1 already closed everywhere
# else in `operator_operation_service.py`/`operator_receipt_service.py`.
# ---------------------------------------------------------------------------


class AttemptStoreUnavailableError(RuntimeError):
    """The operations database (the SAME file this module's `attempts` link
    table lives in -- see module docstring's P2-ARCH-1) was unavailable
    (locked) for a read or write one of this module's own DML helpers
    (`_record_attempt_link`, `_lookup_operation_id`,
    `_list_attempt_ids_for_operation`) could not complete.

    Module-owned, deliberately NOT reused from `operator_operation_service.
    OperationStoreUnavailableError` / `operator_receipt_service.
    ReceiptStoreUnavailableError` even though all three wrap the identical
    underlying `sqlite3.OperationalError` on the identical database file --
    mirrors this codebase's own established convention (see
    `ReceiptStoreUnavailableError`'s own docstring) of a bounded,
    module-owned type per failure surface.

    PUBLIC and deliberately **not** folded into any of this module's
    existing return/raise shapes:

    * NOT `None` from `_lookup_operation_id` -- that already means "no
      link row exists for this attempt_id" (the correct, documented result
      for a legacy `AgentJob` created outside this adapter). Folding a
      transient lock into that shape would misreport an unreadable store as
      "this attempt has no linked operation", which is a PERMANENT fact
      about an already-created attempt.
    * NOT `AttemptLimitExceededError` -- that means "the cap is correctly
      enforced against a REAL, successfully-read attempt count", a
      permanent-for-this-count refusal. A caller that cannot read the count
      at all has learned nothing about whether the cap is exceeded, and
      reporting it as "limit exceeded" would deny retries that would
      otherwise succeed once the lock clears.
    * NOT swallowed by `create_attempt`'s own "cross-store atomicity gap"
      `except Exception: logger.error(...); raise` around
      `_record_attempt_link` -- that block re-raises the ORIGINAL exception
      object verbatim, so `_record_attempt_link` raising a raw
      `sqlite3.OperationalError` would have let raw driver text escape
      through it unchanged. Raising this bounded type FROM
      `_record_attempt_link` itself is what that surrounding handler needed
      to make its own re-raise safe.

    Carries no driver text, no SQL, and no file path, per
    `schemas/operator_mcp_error.schema.yaml` (AC OPM-7) -- the full
    un-redacted detail is logged server-side via `logger.error` at each
    raise site.

    Retryable by contract: means the writer lock (or DDL/setup on a cold
    start) was unavailable within
    `operator_operation_service._BUSY_TIMEOUT_MS`, never that the
    attempt/operation_id itself is invalid.
    """


def _raise_store_unavailable(exc: sqlite3.OperationalError, *, method: str, detail: str) -> NoReturn:
    """Shared raise-site for this module's three guarded DML/read helpers,
    mirroring `operator_receipt_service._raise_store_unavailable` exactly --
    one classification/logging/redaction shape instead of three
    independently-drifting copies."""

    logger.error(
        "operator_attempt_adapter: %s could not access the operations store "
        "for %s -- %s: %s (busy_timeout exhausted, or schema setup failed "
        "on a cold start)",
        method,
        detail,
        type(exc).__name__,
        exc,
    )
    raise AttemptStoreUnavailableError(f"{method}: operations database unavailable") from None

# ---------------------------------------------------------------------------
# P2S-NB-9 (AC OPM-3 "bounded attempts", scheduled at OPM-3.4): before this
# fix, `create_attempt` had no cap at all -- `grep -rn "max_attempt\|
# attempt_limit\|MAX_ATTEMPT" src/research_foundry/services/` returned zero
# hits (findings ledger P2S-NB-9). A caller (originally: any future retry
# loop; concretely, as of OPM-3.4: `operator_mcp_adapters.job_lifecycle`'s
# `job.resume` adapter, and `OperatorCancelResumeService.resume_operation`'s
# own direct call) could mint an unbounded number of attempts (real
# `AgentJob` subprocess-spawn records, each with its own credential
# lifecycle) against a single `operation_id`.
#
# **No fail-open (defect class 1)**: the cap is a hard-coded Python `int`,
# always present -- never a caller-suppliable/config-parsed value whose
# absence or malformed shape could be misread as "unlimited". A caller
# cannot raise, lower, or bypass it through any parameter this method
# accepts.
#
# **Not literally "an exception" from the governed caller's perspective**:
# `AttemptLimitExceededError` is still a real, named Python exception (the
# ONLY mechanism this method has to refuse a would-be side-effecting write
# before performing it, consistent with this module's own existing
# convention -- see `create_attempt`'s pre-existing empty-`operation_id`
# `ValueError`), but every reachable caller in this codebase invokes
# `create_attempt` from inside an `ActionSpec.run()` closure executed by
# `OperatorCancelResumeService.run_actions` (`operator_cancel_resume_
# service.py:624-647`), which already converts ANY raised exception from an
# action into a governed, typed, bounded `ExecutionOutcome("failed", ...)`
# terminal receipt (`reason_code="internal_error"`, `retryable=False`) --
# never a raw traceback reaching an Operator MCP caller, never a silent
# success, and (since the failure is terminal, not retried by this method
# itself) never an infinite retry loop. This reuses that EXISTING governed-
# failure path rather than inventing a second, parallel one.
_DEFAULT_MAX_ATTEMPTS_PER_OPERATION = 5

#: Hard cap on the number of attempts (`AgentJob` records) a single
#: `operation_id` may accumulate via :meth:`OperatorAttemptAdapter.
#: create_attempt`. Chosen conservatively: every existing test and call site
#: in this tree creates at most 2 attempts for any one `operation_id`
#: (verified by inspection of `tests/unit/test_operator_attempt_adapter.py`
#: and `tests/unit/test_operator_cancel_resume_service.py`), so this cap is
#: never reached by legitimate existing usage while still bounding a
#: pathological retry loop.
MAX_ATTEMPTS_PER_OPERATION = _DEFAULT_MAX_ATTEMPTS_PER_OPERATION


class AttemptLimitExceededError(RuntimeError):
    """Raised by :meth:`OperatorAttemptAdapter.create_attempt` when
    `operation_id` already has :data:`MAX_ATTEMPTS_PER_OPERATION` linked
    attempts. See the module-level P2S-NB-9 comment above this class for
    why this is the correct, bounded (never fail-open, never silently
    successful, never infinitely retried) way to enforce the cap."""

    def __init__(self, operation_id: str, limit: int) -> None:
        super().__init__(
            f"attempt limit exceeded for operation_id={operation_id!r} (limit={limit})"
        )
        self.operation_id = operation_id
        self.limit = limit

# ---------------------------------------------------------------------------
# Storage: the ``attempts`` table in the SAME db OPM-2.1 already owns.
#
# P2-ARCH-1: schema ownership (the ``CREATE TABLE``/``CREATE INDEX`` DDL,
# and the `PRAGMA user_version`-gated migration counter) now lives SOLELY in
# ``operator_operation_service._ensure_schema`` -- this module calls that
# module's own ``_connect``/``_ensure_schema`` and issues DML only.
# ---------------------------------------------------------------------------


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

    conn = _ops_store._connect(paths)
    try:
        try:
            _ops_store._ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            # Acquisition half (K3-BLOCK-1 half 1 analogue): `_ensure_schema`
            # is DDL (RESERVED lock) and `BEGIN IMMEDIATE` itself also
            # acquires RESERVED -- either can block behind a concurrent
            # writer until `_BUSY_TIMEOUT_MS` is exhausted. No transaction
            # was ever opened here, so there is nothing to roll back.
            _raise_store_unavailable(
                exc, method="_record_attempt_link", detail=f"attempt_id={attempt_id}"
            )
        try:
            conn.execute(
                "INSERT INTO attempts (attempt_id, operation_id, workspace_id, created_at)"
                " VALUES (?, ?, ?, ?)",
                (attempt_id, operation_id, workspace_id, created_at),
            )
            conn.execute("COMMIT")
        except sqlite3.OperationalError as exc:
            # Promotion half (K3-BLOCK-1 half 2 analogue): `BEGIN IMMEDIATE`
            # takes RESERVED immediately but SQLite promotes to EXCLUSIVE
            # lazily, on the first real write -- the INSERT above -- so
            # contention can still fire AFTER a successful `BEGIN IMMEDIATE`.
            # Best-effort ROLLBACK: if the SAME contention that raised this
            # also makes ROLLBACK raise, a second raw exception must not
            # replace the bounded error about to be raised (COMMIT was
            # never reached either way).
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            _raise_store_unavailable(
                exc, method="_record_attempt_link", detail=f"attempt_id={attempt_id}"
            )
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

    conn = _ops_store._connect(paths)
    try:
        try:
            _ops_store._ensure_schema(conn)
            row = conn.execute(
                "SELECT operation_id FROM attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            _raise_store_unavailable(
                exc, method="_lookup_operation_id", detail=f"attempt_id={attempt_id}"
            )
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

    conn = _ops_store._connect(paths)
    try:
        try:
            _ops_store._ensure_schema(conn)
            rows = conn.execute(
                "SELECT attempt_id FROM attempts WHERE operation_id = ? ORDER BY created_at",
                (operation_id,),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            _raise_store_unavailable(
                exc, method="_list_attempt_ids_for_operation", detail=f"operation_id={operation_id}"
            )
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

        # P2S-NB-9: enforce the bounded-attempts cap BEFORE any side effect
        # (no `AgentJob` is created, no `job.json` written, no `attempts`
        # row inserted) -- a clean fail-closed check, mirroring this
        # method's own pre-existing empty-`operation_id` guard immediately
        # above. Counts existing linked attempts via the SAME unscoped
        # helper `list_attempts_for_operation`/`_lookup_operation_id` build
        # on (`_list_attempt_ids_for_operation`) -- never a second,
        # independently-maintained count.
        existing_attempt_count = len(_list_attempt_ids_for_operation(self._paths, operation_id))
        if existing_attempt_count >= MAX_ATTEMPTS_PER_OPERATION:
            logger.error(
                "operator_attempt_adapter: create_attempt REJECTED -- "
                "operation_id=%s already has %d attempts (limit=%d, P2S-NB-9)",
                operation_id,
                existing_attempt_count,
                MAX_ATTEMPTS_PER_OPERATION,
            )
            raise AttemptLimitExceededError(operation_id, MAX_ATTEMPTS_PER_OPERATION)

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
