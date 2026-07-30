"""Effect/checkpoint/terminal receipt persistence for the local-stdio
Operator MCP (research-foundry-operator-mcp-v1 P2, OPM-2.3).

This module is the durable-persistence owner of the FOUR non-operation
receipt kinds `schemas/operator_mcp_receipt.schema.yaml` freezes:
`action_receipt`, `effect_receipt`, `checkpoint`, and `terminal_receipt`
(`operation_receipt` is minted at accept/deny time by the confirmation/
authorization path, OPM-1.4's own concern -- not this module's). It writes
into the SAME database `operator_operation_service.py` (OPM-2.1) owns
(`paths.operator_operations_db`) -- **P2-ARCH-1**: that module's
`_ensure_schema` is the SOLE schema/migration authority for this database
file (see its `_SCHEMA_VERSION` docstring); this module opens it via that
module's own `_connect`/`_ensure_schema` and issues DML only, never DDL.

IMMUTABLE VS MUTABLE (mirrors the schema's own split): `action_receipt` and
`effect_receipt` are immutable once written -- enforced BOTH by DB triggers
(`trg_action_receipts_immutable_no_*`/`trg_effect_receipts_immutable_no_*`)
AND by this module never issuing an UPDATE/DELETE against either table.
`checkpoint` is the ONE mutable kind -- a single row per `operation_id`,
atomically REPLACED (`INSERT ... ON CONFLICT ... DO UPDATE`, one statement)
by :meth:`OperatorReceiptService.write_checkpoint`, never appended to.
`terminal_receipt` is immutable and, once persisted for an `operation_id`,
is never re-emitted -- a second :meth:`finalize_terminal_receipt` call for
the SAME `operation_id` resolves to the EXISTING row (`outcome ==
"exact_replay"`), never a second row and never a raw `IntegrityError`.

RECONCILIATION (OPM-2.3 AC: "Truncated/extra/duplicate/reordered/mismatched
receipt fixtures deny") is split across TWO enforcement points, by design,
so each defect class is caught as close to its root cause as possible and
NONE of the five degrade to a raw, un-governed exception:

* **DUPLICATE** and **MISMATCHED** are caught at WRITE time, against REAL
  persisted state (never a fake/in-memory stand-in):
    - :meth:`record_action_receipt`'s INSERT targets a table whose PRIMARY
      KEY is `(operation_id, action_index)` (and a UNIQUE index on
      `(operation_id, action_id)`) -- a second receipt presenting an
      `action_index`/`action_id` already recorded for this `operation_id`
      raises `sqlite3.IntegrityError`, caught here and turned into a
      governed `ReceiptOutcome("denied", "internal_error", None)`.
    - :meth:`record_effect_receipt` first checks, INSIDE the same locked
      transaction as its own INSERT, that `action_id` references an
      already-persisted `action_receipt` for this `operation_id` -- an
      effect claiming to belong to an action that was never recorded
      denies before any row is written. Its own INSERT then targets a
      table whose PRIMARY KEY is `effect_digest` (a content-addressed
      identity) -- a second receipt presenting the SAME digest (even for a
      different action) also denies via the identical `IntegrityError`
      path.
* **TRUNCATED**, **EXTRA**, and **REORDERED** are properties of the WHOLE
  persisted set relative to the operation's own declared action count, so
  they can only be caught at RECONCILIATION time -- :meth:`_reconcile`,
  called from :meth:`finalize_terminal_receipt`, reads back every
  `action_receipt` for `operation_id` and denies unless the persisted
  `action_index` values are EXACTLY the contiguous sequence
  `range(expected_action_count)` (too few is truncated, too many is extra,
  present-but-out-of-sequence is reordered -- all three collapse to the
  same `!= list(range(...))` check once duplicates/gaps are impossible by
  construction, per the write-time guard above).

AUDIT IS SUPPLEMENTAL, RECEIPT IS PRIMARY (OPM-OQ-6, quality-gate
invariant): :meth:`finalize_terminal_receipt` calls
`audit_service.record_event` (itself fail-open -- never raises) to record
ONE supplemental audit event for the operation's terminal disposition, and
records the OUTCOME of that call (`delivered`/`unavailable`) in the
terminal receipt's own `audit_delivery` field via
`operator_mcp_policy.build_audit_delivery`. A failed, degraded, or entirely
unavailable audit write NEVER erases, blocks, or delays the terminal
receipt itself -- the receipt is built and persisted regardless of what
`audit_delivery` ends up recording. `audit_service` is additionally
imported lazily (mirrors `agent_job_service.create_job`'s own deferred-
import pattern for the identical reason: it must stay an OPTIONAL
dependency for a base install), and that import/call is wrapped in its OWN
`try/except` -- even an import-time failure of `audit_service` cannot
prevent a terminal receipt from being produced, only its `audit_delivery`
records that fact.

`completed_action_count <= total_action_count` (an application-layer
obligation JSON Schema cannot express -- confirmed empirically that
`{completed_action_count: 5, total_action_count: 1}` validates against the
schema with zero errors) is enforced by :func:`_validate_action_counts`,
called from BOTH :meth:`write_checkpoint` (the load-bearing site -- a
caller supplies both counts directly there) and :meth:`finalize_terminal_receipt`
(defense in depth; structurally unreachable via the reconciled path alone,
since `completed_action_count` there is a subset count of the SAME rows
`_reconcile` has already proven number exactly `expected_action_count`).

**Sensitivity threshold (P2S-NB-1, assessed and deliberately deferred, not
a silent gap)**: this module's identity-scoping seam (P2S-BLOCK-3, above)
enforces WORKSPACE only, never `effective_sensitivity`. This is an explicit
architectural decision, not an oversight: `operations.effective_sensitivity`
is written once, at creation, by `operator_operation_service.py`, and this
codebase's established precedent (the runs/reports API routers' own
`sensitivity_threshold`/`resolve_workspace_isolation_active`-style gating)
enforces a sensitivity CEILING at the CALLER/transport boundary -- the
layer that knows the REQUESTING actor's own clearance -- not inside a
low-level durable store that has no such context and would otherwise need
a THIRD scoping parameter threaded through every read/write in this
module ahead of any P3-P5 caller existing to supply it correctly. P5
(`OPM-5.4`, the plan's own "limits and error mapping ... at the transport
boundary" task) is the correct, already-planned integration point for an
above-threshold gate; wiring one INTO this store now, before that
boundary exists, would be unvalidated surface area with no real caller to
prove it against. Workspace scoping alone is not a partial substitute for
this -- it is the orthogonal, independently-complete half of AC OPM-2 this
module owns.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import operator_operation_service as _ops_store

_logger = logging.getLogger(__name__)

__all__ = [
    "ReceiptOutcome",
    "ResumePointOutcome",
    "OperatorReceiptService",
]


def _iso_utc(dt: datetime) -> str:
    """Same format `operator_operation_service._iso_utc` uses -- kept as an
    independent copy rather than importing a private helper across module
    boundaries for a three-line function (that module's own convention)."""

    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _derive_workspace_id(conn: sqlite3.Connection, operation_id: str) -> str | None:
    """Look up the REAL, persisted `workspace_id` for `operation_id` from
    the authoritative `operations` table (P2S-BLOCK-3 / P2S-BLOCK-4).

    Returns `None` if no `operations` row exists for `operation_id` --
    callers MUST treat that as a referential-integrity denial (a receipt
    can never be written for, or a workspace derived from, an operation
    that was never durably created), never as "use the caller-supplied
    value instead".

    Safe to call OUTSIDE a `BEGIN IMMEDIATE` lock: `operations` rows are
    immutable (`operator_operation_service.py`'s own
    `trg_operations_immutable_no_update`/`_no_delete` triggers, module
    docstring) -- once a row exists, its `workspace_id` can never change,
    so there is no TOCTOU window for a value that is either absent or
    permanently fixed.
    """

    row = conn.execute(
        "SELECT workspace_id FROM operations WHERE operation_id = ?",
        (operation_id,),
    ).fetchone()
    return row["workspace_id"] if row is not None else None


def _validate_action_counts(completed_action_count: int, total_action_count: int) -> None:
    """Application-layer enforcement of `completed_action_count <=
    total_action_count` -- see module docstring for why JSON Schema cannot
    express this and where this is called from.

    Raises `ValueError`: a caller presenting `completed > total` (or either
    count negative) is a programming error in the CALLER (an adapter
    miscounting its own actions), never a runtime/security condition an
    untrusted request could trigger through this service alone -- mirrors
    `operator_operation_service.record_confirmation`'s own convention of
    failing loudly on contract violations rather than silently persisting
    something unusable.
    """

    if completed_action_count < 0 or total_action_count < 0:
        raise ValueError(
            "completed_action_count and total_action_count must both be >= 0 "
            f"(got completed={completed_action_count}, total={total_action_count})"
        )
    if completed_action_count > total_action_count:
        raise ValueError(
            f"completed_action_count ({completed_action_count}) must not exceed "
            f"total_action_count ({total_action_count})"
        )


@dataclass(frozen=True)
class ReceiptOutcome:
    """Result of every write method on :class:`OperatorReceiptService`.

    `outcome`:
        `"created"`
            A brand-new, immutable receipt row (or, for `write_checkpoint`,
            the current mutable checkpoint row) was durably persisted.
        `"exact_replay"`
            `finalize_terminal_receipt` only: an operation already has a
            persisted `terminal_receipt` -- the pre-existing one is
            returned, never a second row.
        `"denied"`
            The write was refused -- `reason_code` is one of
            `operator_mcp_policy.CLOSED_REASON_CODES` (always
            `"internal_error"` in this module: every denial here is a
            receipt-integrity/reconciliation violation, never a
            caller-request-shaped policy denial -- see module docstring).
            Zero rows written.
    """

    outcome: Literal["created", "exact_replay", "denied"]
    reason_code: str | None
    receipt: Mapping[str, Any] | None


@dataclass(frozen=True)
class ResumePointOutcome:
    """Result of :meth:`OperatorReceiptService.resolve_resume_point`
    (OPM-2.4, H3 scenario 7/8-extended-to-resume).

    `outcome`:
        `"ok"`
            `next_action_index` is the first action index with no
            persisted `action_receipt` for this `operation_id` --
            computed ENTIRELY from real, already-committed
            `action_receipts` rows, never from `checkpoint`'s own
            (possibly stale, possibly never-written-for-this-index)
            `next_action_index`, and never from any in-process/surviving
            Python object. This is what makes it safe to call after a
            genuine process loss (scenario 7): the truth is reconstructed
            entirely from what actually committed to disk before the loss.
        `"denied"`
            The persisted `action_index` sequence for this `operation_id`
            is not the contiguous `range(0, N)` for its own length `N` --
            corrupt receipt state (e.g. a gap from an out-of-band write).
            `next_action_index` is `None`. A caller MUST NOT resume
            execution when this denies (scenario 8, extended to the
            resume path -- corrupt receipt state must deny resume, not
            merely deny at write time, which the write-time
            duplicate/mismatched guards in this module already cover).
    """

    outcome: Literal["ok", "denied"]
    reason_code: str | None
    next_action_index: int | None


class OperatorReceiptService:
    """Durable persistence for Operator MCP action/effect/checkpoint/
    terminal receipts (P2, OPM-2.3). See module docstring for the full
    reconciliation and audit-linking contract."""

    def __init__(self, paths: FoundryPaths) -> None:
        self._paths = paths
        self._schemas = SchemaRegistry(schemas_dir=paths.schemas if paths.schemas.exists() else None)

    # -- action receipts ----------------------------------------------

    def record_action_receipt(
        self,
        operation_id: str,
        *,
        action_id: str,
        action_index: int,
        status: str,
        attempt_ref: str,
        started_at: str,
        completed_at: str | None = None,
        reason_code: str | None = None,
        retryable: bool | None = None,
    ) -> ReceiptOutcome:
        """Persist one immutable `action_receipt`.

        Denies (governed, never a raw exception) if `action_index` or
        `action_id` was already recorded for this `operation_id` -- the
        DUPLICATE/REORDERED write-time guard (module docstring).
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("record_action_receipt requires a non-empty operation_id")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("record_action_receipt requires a non-empty action_id")
        if isinstance(action_index, bool) or not isinstance(action_index, int) or action_index < 0:
            raise ValueError("record_action_receipt requires action_index to be an int >= 0")
        if status not in ("completed", "failed", "skipped"):
            raise ValueError(f"record_action_receipt requires a closed status (got {status!r})")
        if status in ("failed", "skipped") and not reason_code:
            raise ValueError(f"record_action_receipt requires reason_code when status={status!r}")
        if status == "completed" and reason_code is not None:
            raise ValueError("record_action_receipt forbids reason_code when status == 'completed'")
        if reason_code is not None and reason_code not in policy.CLOSED_REASON_CODES:
            raise ValueError(f"unknown reason_code: {reason_code!r}")
        if not isinstance(attempt_ref, str) or not attempt_ref:
            raise ValueError("record_action_receipt requires a non-empty attempt_ref")
        if not isinstance(started_at, str) or not started_at:
            raise ValueError("record_action_receipt requires a non-empty started_at")

        receipt: dict[str, Any] = {
            "schema_version": "1.0",
            "kind": "action_receipt",
            "operation_id": operation_id,
            "action_id": action_id,
            "action_index": action_index,
            "status": status,
            "attempt_ref": attempt_ref,
            "started_at": started_at,
            "completed_at": completed_at,
        }
        if reason_code is not None:
            receipt["reason_code"] = reason_code
        if retryable is not None:
            receipt["retryable"] = bool(retryable)

        try:
            self._validate_receipt(receipt)
        except RuntimeError:
            # F4 sibling (P2S-NB-4): schema validation is believed
            # unreachable (the receipt is built entirely from already
            # ValueError-guarded values above) -- but "believed
            # unreachable" was explicitly rejected as sufficient for this
            # module family's OTHER internal invariant
            # (`_Dur1InvariantViolation` in `operator_operation_service.py`),
            # so this is caught and converted here too, never allowed to
            # cross this method's boundary as a raw `RuntimeError`.
            _logger.error(
                "operator_receipt_service: action_receipt failed schema "
                "validation for operation_id=%s action_id=%s -- denying "
                "rather than raising raw",
                operation_id,
                action_id,
            )
            return ReceiptOutcome("denied", "internal_error", None)

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                # P2S-BLOCK-4: referential integrity -- `operation_id` MUST
                # reference an already-persisted `operations` manifest.
                # Checked INSIDE this locked transaction (mirrors
                # `record_effect_receipt`'s own MISMATCHED guard immediately
                # below): without this, a single out-of-turn receipt for a
                # phantom operation_id was accepted and, because
                # action_receipts rows are immutable, could never be
                # repaired -- permanently bricking that operation_id the
                # moment a REAL operation with the same id (astronomically
                # unlikely, but the point is this store must not depend on
                # that) or any resume/reconcile path touched it.
                if _derive_workspace_id(conn, operation_id) is None:
                    conn.execute("ROLLBACK")
                    _logger.error(
                        "operator_receipt_service: action_receipt REJECTED -- "
                        "operation_id=%s has no persisted operation manifest "
                        "(referential integrity guard, P2S-BLOCK-4)",
                        operation_id,
                    )
                    return ReceiptOutcome("denied", "internal_error", None)

                conn.execute(
                    "INSERT INTO action_receipts"
                    " (operation_id, action_id, action_index, status, attempt_ref,"
                    "  started_at, completed_at, reason_code, retryable, receipt_json, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        operation_id,
                        action_id,
                        action_index,
                        status,
                        attempt_ref,
                        started_at,
                        completed_at,
                        reason_code,
                        None if retryable is None else int(bool(retryable)),
                        json.dumps(receipt),
                        ids.now_iso(),
                    ),
                )
                conn.execute("COMMIT")
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                _logger.error(
                    "operator_receipt_service: DUPLICATE/REORDERED action_receipt "
                    "rejected (operation_id=%s, action_id=%s, action_index=%d) -- "
                    "PRIMARY KEY or UNIQUE constraint violated",
                    operation_id,
                    action_id,
                    action_index,
                )
                return ReceiptOutcome("denied", "internal_error", None)
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

        return ReceiptOutcome("created", None, receipt)

    # -- effect receipts ------------------------------------------------

    def record_effect_receipt(
        self,
        operation_id: str,
        *,
        action_id: str,
        effect_kind: str,
        effect_digest: str,
        effect_ref: str,
        generated_at: str,
    ) -> ReceiptOutcome:
        """Persist one immutable `effect_receipt`.

        Denies (governed) if `action_id` does not reference an
        already-persisted `action_receipt` for this `operation_id` -- the
        MISMATCHED write-time guard -- or if `effect_digest` was already
        recorded (for ANY action/operation) -- the DUPLICATE guard.
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("record_effect_receipt requires a non-empty operation_id")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("record_effect_receipt requires a non-empty action_id")
        if not isinstance(effect_kind, str) or not effect_kind:
            raise ValueError("record_effect_receipt requires a non-empty effect_kind")
        if not isinstance(effect_digest, str) or not effect_digest:
            raise ValueError("record_effect_receipt requires a non-empty effect_digest")
        if not isinstance(effect_ref, str) or not effect_ref:
            raise ValueError("record_effect_receipt requires a non-empty effect_ref")
        if not isinstance(generated_at, str) or not generated_at:
            raise ValueError("record_effect_receipt requires a non-empty generated_at")

        receipt: dict[str, Any] = {
            "schema_version": "1.0",
            "kind": "effect_receipt",
            "operation_id": operation_id,
            "action_id": action_id,
            "effect_kind": effect_kind,
            "effect_digest": effect_digest,
            "effect_ref": effect_ref,
            "generated_at": generated_at,
        }
        try:
            self._validate_receipt(receipt)
        except RuntimeError:
            # F4 sibling (P2S-NB-4) -- see the identical guard in
            # `record_action_receipt` for the full rationale.
            _logger.error(
                "operator_receipt_service: effect_receipt failed schema "
                "validation for operation_id=%s action_id=%s -- denying "
                "rather than raising raw",
                operation_id,
                action_id,
            )
            return ReceiptOutcome("denied", "internal_error", None)

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                # P2S-BLOCK-4: referential integrity, direct check (defense
                # in depth -- "fix the layer below": once
                # `record_action_receipt` closes the phantom-operation_id
                # hole, this is transitively unreachable via the
                # MISMATCHED guard just below (an action_receipt cannot
                # exist for a phantom operation), but a DIRECT caller of
                # THIS method alone must not depend on that other guard
                # staying correct forever).
                if _derive_workspace_id(conn, operation_id) is None:
                    conn.execute("ROLLBACK")
                    _logger.error(
                        "operator_receipt_service: effect_receipt REJECTED -- "
                        "operation_id=%s has no persisted operation manifest "
                        "(referential integrity guard, P2S-BLOCK-4)",
                        operation_id,
                    )
                    return ReceiptOutcome("denied", "internal_error", None)

                # MISMATCHED guard -- checked INSIDE this locked
                # transaction (not a separate, earlier read) so no
                # concurrent writer can insert a phantom effect for an
                # action that doesn't, and never will, exist.
                row = conn.execute(
                    "SELECT 1 FROM action_receipts WHERE operation_id = ? AND action_id = ?",
                    (operation_id, action_id),
                ).fetchone()
                if row is None:
                    conn.execute("ROLLBACK")
                    _logger.error(
                        "operator_receipt_service: MISMATCHED effect_receipt rejected -- "
                        "action_id=%s has no matching action_receipt for operation_id=%s",
                        action_id,
                        operation_id,
                    )
                    return ReceiptOutcome("denied", "internal_error", None)

                conn.execute(
                    "INSERT INTO effect_receipts"
                    " (operation_id, action_id, effect_digest, effect_kind, effect_ref,"
                    "  generated_at, receipt_json, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        operation_id,
                        action_id,
                        effect_digest,
                        effect_kind,
                        effect_ref,
                        generated_at,
                        json.dumps(receipt),
                        ids.now_iso(),
                    ),
                )
                conn.execute("COMMIT")
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                _logger.error(
                    "operator_receipt_service: DUPLICATE effect_receipt rejected -- "
                    "effect_digest=%s already recorded",
                    effect_digest,
                )
                return ReceiptOutcome("denied", "internal_error", None)
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

        return ReceiptOutcome("created", None, receipt)

    # -- checkpoint (the ONE mutable kind) -------------------------------

    def write_checkpoint(
        self,
        operation_id: str,
        *,
        workspace_id: str,
        status: str,
        next_action_index: int | None,
        completed_action_count: int,
        total_action_count: int,
        non_cancelable: bool,
    ) -> ReceiptOutcome:
        """Atomically REPLACE the single checkpoint row for `operation_id`.

        Raises `ValueError` (never silently clamps) if
        `completed_action_count > total_action_count`, or if
        `next_action_index`'s nullness disagrees with `status` -- see
        module docstring and :func:`_validate_action_counts`.
        """

        if status not in ("pending", "converged"):
            raise ValueError(f"write_checkpoint requires status in ('pending','converged') (got {status!r})")
        if status == "converged" and next_action_index is not None:
            raise ValueError("write_checkpoint requires next_action_index=None when status == 'converged'")
        if status == "pending" and next_action_index is None:
            raise ValueError("write_checkpoint requires a non-null next_action_index when status == 'pending'")
        if status == "converged" and non_cancelable:
            raise ValueError("write_checkpoint requires non_cancelable=False when status == 'converged'")
        _validate_action_counts(completed_action_count, total_action_count)
        if not isinstance(workspace_id, str) or not workspace_id:
            raise ValueError("write_checkpoint requires a non-empty workspace_id")

        moment = ids.now()

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)

            # P2S-BLOCK-3/BLOCK-4: derive the REAL workspace_id from the
            # authoritative `operations` row rather than trusting the
            # caller-supplied parameter (which, before this fix, was
            # written verbatim into an IMMUTABLE row -- a wrong or forged
            # attribution could never be corrected). Denies (governed,
            # never a raw write) if `operation_id` has no persisted
            # manifest at all -- the same referential-integrity guard as
            # the receipt tables. Safe to read unlocked: see
            # `_derive_workspace_id`'s own docstring.
            resolved_workspace_id = _derive_workspace_id(conn, operation_id)
            if resolved_workspace_id is None:
                _logger.error(
                    "operator_receipt_service: write_checkpoint REJECTED -- "
                    "operation_id=%s has no persisted operation manifest "
                    "(referential integrity guard, P2S-BLOCK-4)",
                    operation_id,
                )
                return ReceiptOutcome("denied", "internal_error", None)
            if workspace_id != resolved_workspace_id:
                _logger.warning(
                    "operator_receipt_service: write_checkpoint caller-supplied "
                    "workspace_id=%r for operation_id=%s does not match the "
                    "operation's own workspace_id=%r -- using the operation's "
                    "value (P2S-BLOCK-3 hardening)",
                    workspace_id,
                    operation_id,
                    resolved_workspace_id,
                )
            workspace_id = resolved_workspace_id

            checkpoint: dict[str, Any] = {
                "schema_version": "1.0",
                "kind": "checkpoint",
                "operation_id": operation_id,
                "workspace_id": workspace_id,
                "status": status,
                "next_action_index": next_action_index,
                "completed_action_count": completed_action_count,
                "total_action_count": total_action_count,
                "non_cancelable": bool(non_cancelable),
                "updated_at": _iso_utc(moment),
            }
            try:
                self._validate_receipt(checkpoint)
            except RuntimeError:
                # F4 sibling (P2S-NB-4).
                _logger.error(
                    "operator_receipt_service: checkpoint failed schema "
                    "validation for operation_id=%s -- denying rather than "
                    "raising raw",
                    operation_id,
                )
                return ReceiptOutcome("denied", "internal_error", None)

            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO checkpoints"
                    " (operation_id, workspace_id, status, next_action_index,"
                    "  completed_action_count, total_action_count, non_cancelable,"
                    "  updated_at, checkpoint_json)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT(operation_id) DO UPDATE SET"
                    "   workspace_id = excluded.workspace_id,"
                    "   status = excluded.status,"
                    "   next_action_index = excluded.next_action_index,"
                    "   completed_action_count = excluded.completed_action_count,"
                    "   total_action_count = excluded.total_action_count,"
                    "   non_cancelable = excluded.non_cancelable,"
                    "   updated_at = excluded.updated_at,"
                    "   checkpoint_json = excluded.checkpoint_json",
                    (
                        operation_id,
                        workspace_id,
                        status,
                        next_action_index,
                        completed_action_count,
                        total_action_count,
                        int(bool(non_cancelable)),
                        checkpoint["updated_at"],
                        json.dumps(checkpoint),
                    ),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

        return ReceiptOutcome("created", None, checkpoint)

    # -- resume point (OPM-2.4) -------------------------------------------

    def resolve_resume_point(
        self,
        operation_id: str,
        *,
        identity: AuthIdentity | None = None,
        total_action_count: int | None = None,
    ) -> ResumePointOutcome:
        """Determine the first INCOMPLETE action index for `operation_id`,
        reading real persisted `action_receipts` -- see
        :class:`ResumePointOutcome` for the full contract and why this is
        the resume-safe (process-loss-safe) way to ask this question,
        instead of trusting `checkpoint.next_action_index` (which is a
        SEPARATE, independently-written row that can be stale relative to
        `action_receipts` if a process was lost between the two writes --
        exactly the OPM-2.4 scenario-7 gap this method closes).

        **P2S-BLOCK-3 (identity/workspace seam)**: `identity=None` (the
        default) performs NO workspace scoping, matching
        `OperatorOperationService.load_operation`'s own default -- existing
        internal callers that have already established the correct
        workspace by other means (e.g. having just loaded the operation
        with scoping applied) are unaffected. When `identity` IS supplied,
        a wrong-workspace `operation_id` denies with `reason_code=
        "not_found"` -- the SAME code used for a genuinely missing
        `operation_id` (denied one line below, before the workspace
        comparison), so the two are indistinguishable to the caller,
        mirroring `load_operation`'s own no-existence-leak convention.

        **P2S-BLOCK-2 (EXTRA receipt corruption caught before resume, not
        only at `finalize_terminal_receipt`)**: when `total_action_count`
        is supplied (the caller's own declared action count -- e.g.
        `len(actions)` in `operator_cancel_resume_service.run_or_replay`/
        `resume_operation`), more persisted `action_receipts` than that
        declared count denies -- the EXTRA corruption class, caught here
        BEFORE any action would be (re-)executed, rather than discovered
        only once `run_actions` reaches `finalize_terminal_receipt` at the
        end. `total_action_count=None` (the default) skips this check,
        preserving the exact prior contiguity-only behavior for callers
        that do not (yet) know their own declared count.
        """

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)

            op_row = conn.execute(
                "SELECT workspace_id FROM operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if op_row is None:
                _logger.error(
                    "operator_receipt_service: resolve_resume_point REJECTED -- "
                    "operation_id=%s has no persisted operation manifest "
                    "(referential integrity guard, P2S-BLOCK-4)",
                    operation_id,
                )
                return ResumePointOutcome("denied", "not_found", None)
            if identity is not None and op_row["workspace_id"] != identity.workspace_id:
                _logger.error(
                    json.dumps(
                        {
                            "event": "workspace_scope_enforced_denial",
                            "record_type": "operation",
                            "record_id": operation_id,
                            "record_workspace_id": op_row["workspace_id"],
                            "identity_workspace_id": identity.workspace_id,
                        }
                    )
                )
                return ResumePointOutcome("denied", "not_found", None)

            rows = conn.execute(
                "SELECT action_index FROM action_receipts"
                " WHERE operation_id = ? ORDER BY action_index",
                (operation_id,),
            ).fetchall()
        finally:
            conn.close()

        indices = [row["action_index"] for row in rows]
        if indices != list(range(len(indices))):
            _logger.error(
                "operator_receipt_service: resolve_resume_point found a "
                "non-contiguous action_index sequence %r for operation_id=%s "
                "-- denying resume (corrupt receipt state)",
                indices,
                operation_id,
            )
            return ResumePointOutcome("denied", "internal_error", None)
        if total_action_count is not None and len(indices) > total_action_count:
            _logger.error(
                "operator_receipt_service: resolve_resume_point found %d "
                "persisted action_receipt(s) for operation_id=%s, exceeding "
                "the declared total_action_count=%d -- denying resume "
                "(EXTRA receipt corruption, P2S-BLOCK-2)",
                len(indices),
                operation_id,
                total_action_count,
            )
            return ResumePointOutcome("denied", "internal_error", None)
        return ResumePointOutcome("ok", None, len(indices))

    # -- reconciliation + terminal receipt -------------------------------

    def _reconcile(
        self, conn: sqlite3.Connection, operation_id: str, expected_action_count: int
    ) -> tuple[list[str], int] | None:
        """Read back every persisted `action_receipt`/`effect_receipt` for
        `operation_id` and reconcile counts/digests. Returns
        `(effect_receipt_refs, completed_action_count)` on success, `None`
        on a TRUNCATED/EXTRA/REORDERED defect (logged server-side; see
        module docstring for why DUPLICATE/MISMATCHED can never reach this
        point at all).
        """

        action_rows = conn.execute(
            "SELECT action_index, status FROM action_receipts"
            " WHERE operation_id = ? ORDER BY action_index",
            (operation_id,),
        ).fetchall()

        if len(action_rows) != expected_action_count:
            _logger.error(
                "operator_receipt_service: reconciliation failed for operation_id=%s -- "
                "persisted %d action_receipt(s), expected %d (TRUNCATED if fewer, "
                "EXTRA if more)",
                operation_id,
                len(action_rows),
                expected_action_count,
            )
            return None

        indices = [row["action_index"] for row in action_rows]
        if indices != list(range(expected_action_count)):
            _logger.error(
                "operator_receipt_service: reconciliation failed for operation_id=%s -- "
                "action_index sequence %r is not the contiguous range(%d) (REORDERED)",
                operation_id,
                indices,
                expected_action_count,
            )
            return None

        effect_rows = conn.execute(
            "SELECT effect_digest FROM effect_receipts WHERE operation_id = ? ORDER BY rowid",
            (operation_id,),
        ).fetchall()
        effect_receipt_refs = [row["effect_digest"] for row in effect_rows]

        completed_action_count = sum(1 for row in action_rows if row["status"] == "completed")
        # Defense in depth (structurally unreachable via THIS reconciled
        # path alone -- see module docstring): `completed_action_count` is
        # a subset count of the SAME `action_rows` already proven, above,
        # to number exactly `expected_action_count`.
        _validate_action_counts(completed_action_count, expected_action_count)

        return effect_receipt_refs, completed_action_count

    def _record_supplemental_audit_event(
        self,
        *,
        operation_id: str,
        workspace_id: str,
        status: str,
        actor_user_id: str | None,
    ) -> dict[str, Any]:
        """Record ONE supplemental audit event for `operation_id`'s
        terminal disposition; return a schema-valid `audit_delivery` block
        built from the outcome. NEVER raises -- see module docstring's
        "AUDIT IS SUPPLEMENTAL, RECEIPT IS PRIMARY" section.
        """

        audit_event_id: str | None = None
        try:
            from research_foundry.services.audit_service import (  # noqa: PLC0415
                AuditEvent,
                record_event,
            )

            audit_event_id = record_event(
                self._paths,
                AuditEvent(
                    mutation_type="agent_job_launched",
                    action="operator_operation_finalize",
                    target_ref=operation_id,
                    actor_user_id=actor_user_id,
                    actor_workspace_id=workspace_id,
                    result="success" if status in ("completed", "canceled") else "failure",
                ),
            )
        except Exception:  # pragma: no cover - defense in depth, see docstring
            _logger.error(
                "operator_receipt_service: audit_service unavailable while finalizing "
                "operation_id=%s -- terminal receipt still produced; audit_delivery "
                "marked unavailable",
                operation_id,
                exc_info=True,
            )
            audit_event_id = None

        if audit_event_id is not None:
            return policy.build_audit_delivery("delivered", audit_event_id=audit_event_id)
        return policy.build_audit_delivery("unavailable", detail_code="write_failed")

    def finalize_terminal_receipt(
        self,
        operation_id: str,
        *,
        workspace_id: str,
        operation_kind: str,
        expected_action_count: int,
        status: str,
        denial_reason_code: str | None = None,
        audit_actor_user_id: str | None = None,
    ) -> ReceiptOutcome:
        """Reconcile every persisted action/effect receipt for
        `operation_id` and persist ONE immutable `terminal_receipt`.

        Idempotent: a second call for an `operation_id` that already has a
        terminal receipt returns the EXISTING one (`outcome ==
        "exact_replay"`), never a second row.

        Denies (`ReceiptOutcome("denied", "internal_error", None)`) if
        reconciliation fails (TRUNCATED/EXTRA/REORDERED) -- see
        :meth:`_reconcile`. A denied reconciliation persists NOTHING; this
        is distinct from `status="denied"`/`"failed"`, which DOES persist a
        terminal receipt (the operation itself was denied/failed, not this
        module's own bookkeeping).

        Audit delivery NEVER blocks or erases the terminal receipt -- see
        module docstring's "AUDIT IS SUPPLEMENTAL, RECEIPT IS PRIMARY"
        section and :meth:`_record_supplemental_audit_event`.
        """

        if status not in ("completed", "failed", "denied", "canceled"):
            raise ValueError(f"finalize_terminal_receipt requires a closed status (got {status!r})")
        if status in ("denied", "failed") and not denial_reason_code:
            raise ValueError(f"finalize_terminal_receipt requires denial_reason_code when status={status!r}")
        if status in ("completed", "canceled") and denial_reason_code is not None:
            raise ValueError(
                "finalize_terminal_receipt forbids denial_reason_code when status is completed/canceled"
            )
        if denial_reason_code is not None and denial_reason_code not in policy.CLOSED_REASON_CODES:
            raise ValueError(f"unknown denial_reason_code: {denial_reason_code!r}")
        if expected_action_count < 0:
            raise ValueError("finalize_terminal_receipt requires expected_action_count >= 0")
        if not isinstance(workspace_id, str) or not workspace_id:
            raise ValueError("finalize_terminal_receipt requires a non-empty workspace_id")

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)

            # P2S-BLOCK-3/BLOCK-4: derive the REAL workspace_id from the
            # authoritative `operations` row -- see `write_checkpoint`'s
            # identical guard for the full rationale. Checked BEFORE the
            # `existing`/idempotency short-circuit so a phantom
            # operation_id can never even produce an `"exact_replay"`
            # lookup hit.
            resolved_workspace_id = _derive_workspace_id(conn, operation_id)
            if resolved_workspace_id is None:
                _logger.error(
                    "operator_receipt_service: finalize_terminal_receipt REJECTED -- "
                    "operation_id=%s has no persisted operation manifest "
                    "(referential integrity guard, P2S-BLOCK-4)",
                    operation_id,
                )
                return ReceiptOutcome("denied", "internal_error", None)
            if workspace_id != resolved_workspace_id:
                _logger.warning(
                    "operator_receipt_service: finalize_terminal_receipt caller-"
                    "supplied workspace_id=%r for operation_id=%s does not match "
                    "the operation's own workspace_id=%r -- using the operation's "
                    "value (P2S-BLOCK-3 hardening)",
                    workspace_id,
                    operation_id,
                    resolved_workspace_id,
                )
            workspace_id = resolved_workspace_id

            existing = conn.execute(
                "SELECT receipt_json FROM terminal_receipts WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if existing is not None:
                return ReceiptOutcome("exact_replay", None, json.loads(existing["receipt_json"]))

            reconciled = self._reconcile(conn, operation_id, expected_action_count)
            if reconciled is None:
                return ReceiptOutcome("denied", "internal_error", None)
            effect_receipt_refs, completed_action_count = reconciled

            # AUDIT IS SUPPLEMENTAL, RECEIPT IS PRIMARY: called OUTSIDE any
            # BEGIN IMMEDIATE on THIS database -- mirrors
            # `operator_operation_service.authorize_for_consumption`'s own
            # NB-9 rationale (a separate database's own write shouldn't be
            # made while holding this module's exclusive writer lock).
            moment = ids.now()
            audit_delivery = self._record_supplemental_audit_event(
                operation_id=operation_id,
                workspace_id=workspace_id,
                status=status,
                actor_user_id=audit_actor_user_id,
            )

            terminal_receipt: dict[str, Any] = {
                "schema_version": "1.0",
                "kind": "terminal_receipt",
                "operation_id": operation_id,
                "workspace_id": workspace_id,
                "operation_kind": operation_kind,
                "status": status,
                "effect_receipt_refs": effect_receipt_refs,
                "action_count_total": expected_action_count,
                "action_count_completed": completed_action_count,
                "denial_reason_code": denial_reason_code,
                "audit_delivery": audit_delivery,
                "completed_at": _iso_utc(moment),
            }
            try:
                self._validate_receipt(terminal_receipt)
            except RuntimeError:
                # F4 sibling (P2S-NB-4).
                _logger.error(
                    "operator_receipt_service: terminal_receipt failed schema "
                    "validation for operation_id=%s -- denying rather than "
                    "raising raw",
                    operation_id,
                )
                return ReceiptOutcome("denied", "internal_error", None)

            conn.execute("BEGIN IMMEDIATE")
            try:
                # Re-check idempotency INSIDE the lock -- closes the
                # narrow race window between the unlocked read above and
                # this write (a concurrent finalize call for the SAME
                # operation_id racing this one).
                row = conn.execute(
                    "SELECT receipt_json FROM terminal_receipts WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
                if row is not None:
                    conn.execute("COMMIT")
                    return ReceiptOutcome("exact_replay", None, json.loads(row["receipt_json"]))

                conn.execute(
                    "INSERT INTO terminal_receipts"
                    " (operation_id, workspace_id, status, receipt_json, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        operation_id,
                        workspace_id,
                        status,
                        json.dumps(terminal_receipt),
                        _iso_utc(moment),
                    ),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

        return ReceiptOutcome("created", None, terminal_receipt)

    # -- read path --------------------------------------------------------

    def load_terminal_receipt(
        self, operation_id: str, *, identity: AuthIdentity | None = None
    ) -> Mapping[str, Any] | None:
        """Return the persisted `terminal_receipt` for `operation_id`, or
        `None` if none has been finalized yet.

        **P2S-BLOCK-3**: `identity=None` (the default) performs no
        workspace scoping. When `identity` IS supplied, a terminal receipt
        belonging to a DIFFERENT workspace returns `None` -- the IDENTICAL
        shape as "not yet finalized", indistinguishable to the caller, no
        derived detail leaked (mirrors `OperatorOperationService.
        load_operation`'s own no-existence-leak convention, adapted to this
        method's `Optional`-return shape rather than a raised `KeyError`).
        `terminal_receipts.workspace_id` is trustworthy for this comparison
        because `finalize_terminal_receipt` now DERIVES it from the
        authoritative `operations` row rather than accepting a caller-
        asserted value (P2S-BLOCK-3's write-side half, above).
        """

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            row = conn.execute(
                "SELECT receipt_json, workspace_id FROM terminal_receipts WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        if identity is not None and row["workspace_id"] != identity.workspace_id:
            _logger.error(
                json.dumps(
                    {
                        "event": "workspace_scope_enforced_denial",
                        "record_type": "terminal_receipt",
                        "record_id": operation_id,
                        "record_workspace_id": row["workspace_id"],
                        "identity_workspace_id": identity.workspace_id,
                    }
                )
            )
            return None
        return json.loads(row["receipt_json"])

    def load_checkpoint(
        self, operation_id: str, *, identity: AuthIdentity | None = None
    ) -> Mapping[str, Any] | None:
        """Return the current (possibly-superseded-by-a-later-write)
        `checkpoint` for `operation_id`, or `None` if none exists yet.

        **P2S-BLOCK-3**: identical identity-scoping contract as
        :meth:`load_terminal_receipt` -- see that method's docstring.
        `checkpoints.workspace_id` is trustworthy for this comparison
        because `write_checkpoint` now DERIVES it from the authoritative
        `operations` row (P2S-BLOCK-3's write-side half, above).
        """

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            row = conn.execute(
                "SELECT checkpoint_json, workspace_id FROM checkpoints WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        if identity is not None and row["workspace_id"] != identity.workspace_id:
            _logger.error(
                json.dumps(
                    {
                        "event": "workspace_scope_enforced_denial",
                        "record_type": "checkpoint",
                        "record_id": operation_id,
                        "record_workspace_id": row["workspace_id"],
                        "identity_workspace_id": identity.workspace_id,
                    }
                )
            )
            return None
        return json.loads(row["checkpoint_json"])

    # -- internal ---------------------------------------------------------

    def _validate_receipt(self, receipt: Mapping[str, Any]) -> None:
        validation = self._schemas.validate(receipt, "operator_mcp_receipt")
        if not validation.ok:
            # Should be unreachable for every call site in this module --
            # every receipt is built entirely from already-validated
            # (ValueError-guarded) Python values. Never log the errors
            # themselves (could echo caller-influenced content) -- only the
            # count, mirroring `operator_operation_service`'s own NEW-13
            # "log the type, never the content" convention.
            raise RuntimeError(
                f"operator_receipt_service: {receipt.get('kind')} failed schema "
                f"validation ({len(validation.errors)} error(s))"
            )
