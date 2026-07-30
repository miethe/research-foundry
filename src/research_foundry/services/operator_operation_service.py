"""Durable operation store for the local-stdio Operator MCP
(research-foundry-operator-mcp-v1 P2, OPM-2.1 -- DUR-1).

This module is the SOLE owner of durable persistence for two closely related
things `operator_mcp_policy.py` (P1) only models as pure, in-memory value
objects:

* **confirmation records** (`operator_mcp_confirmation` instances minted by
  `operator_mcp_policy.mint_confirmation`) -- P1 never wrote these to disk;
  :meth:`OperatorOperationService.record_confirmation` is the first durable
  write path for one; and
* **operation manifests** -- the immutable, canonical record of a
  successfully authorized and consumed operation (canonical operation
  envelope, canonical input digest, policy-snapshot version, token-
  consumption proof, workspace, effective sensitivity, and target refs).

**DUR-1 (frozen by P1, binding here)**: confirmation-token consumption MUST
be a compare-and-swap on `status` from exactly `issued` to `consumed`, IN THE
SAME DURABLE TRANSACTION as the operation-manifest write, under an exclusive
single-writer lock. A CAS that observes any status other than `issued`, whose
clamped expiry has already passed at commit time, or whose binding check
fails, MUST route to the exact-replay / idempotency-conflict / expired /
mismatch path and MUST NOT execute. See
`schemas/operator_mcp_confirmation.schema.yaml`'s DUR-1 section and
`operator_mcp_policy.py`'s module docstring (same section, verbatim) for the
full normative predicate this module implements.

**A read-then-write implementation passes every P1 test and is still
wrong** (P1's own warning, repeated here because it is the entire point of
this module): `operator_mcp_policy.consume_confirmation` is a PURE function
-- it returns a new dict (or `None` on a failed precondition) and touches no
disk. Real atomicity -- the guarantee that two concurrent callers presenting
the SAME confirmation cannot both observe `status == "issued"` and both
win -- is this module's job, not P1's.

**Mechanism (the sanctioned one, already used by `services/rbac_store.py`)**:
SQLite with `isolation_level=None` (autocommit) plus an explicit
`conn.execute("BEGIN IMMEDIATE")` -- SQLite's `IMMEDIATE` transaction mode
acquires the RESERVED lock immediately (rather than lazily on first write),
so a concurrent second connection's own `BEGIN IMMEDIATE` blocks (up to the
explicit `busy_timeout` below) rather than interleaving with this
transaction's read-then-write sequence. Every write in this module --
reading the confirmation row, calling `operator_mcp_policy.consume_confirmation`,
the guarded `UPDATE ... WHERE status = 'issued'` (asserting `rowcount == 1`),
and the `INSERT` of the new operation manifest -- happens inside ONE such
transaction, on ONE connection, so no other writer can observe or mutate the
confirmation row between the read and the guarded write.

**Confirmations and operation manifests live in the SAME database file**
(`paths.operator_operations_db`, under `.rf_state/` -- durable, NOT
gitignored, sibling to `rbac_db`, never `.rf_cache/`) -- this is load-bearing:
a cross-store write (e.g. confirmations in one sqlite file, operations in
another) cannot be made durably atomic with SQLite's single-database
transaction model.

**Idempotency (AC OPM-3)**: `(workspace_id, idempotency_key)` is UNIQUE on
the `operations` table. A second consume attempt under the same key:

* with the SAME `canonical_input_digest` -- an "exact manifest replay" --
  resolves to the SAME operation (no new manifest row, no new effect); the
  newly presented confirmation is still consumed (pointing
  `consumed_by_operation_id` at the pre-existing operation), since it is a
  legitimately bound confirmation for the same logical retried request; or
* with a DIFFERENT digest -- a genuine idempotency-key collision -- is an
  `idempotency_conflict`: zero manifest, zero effect, and the presented
  confirmation is left `issued` (never consumed for a request the server
  refused to execute).

Presenting the exact SAME (already-`consumed`) confirmation again is handled
one layer up, by `operator_mcp_policy.verify_confirmation` itself
(`outcome == "exact_replay"`) -- this module never re-attempts the CAS for
that case; it looks up the operation the FIRST consumption already recorded
(`consumed_by_operation_id` on the confirmation record) and returns it.

**Workspace scoping on lookup (mirrors `AgentJobService.load_job` exactly)**:
:meth:`OperatorOperationService.load_operation` raises the SAME `KeyError`
with the SAME message text for both a genuinely missing operation and a
wrong-workspace one -- the two are indistinguishable to any caller. A
scope-denied lookup is additionally logged at `ERROR` server-side (never
caller-reachable), the same asymmetry `agent_job_service.py` uses.

Manifests and confirmation-consumption records are immutable once written --
this module has no UPDATE path for `operations.manifest_json` and no DELETE
path for either table. Only the CAS `UPDATE` on `confirmations.status` (and
its accompanying `record_json`) ever mutates an existing row, and it only
ever transitions `issued -> consumed`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import operator_mcp_policy as policy

_logger = logging.getLogger(__name__)

__all__ = [
    "AuthorizationProof",
    "OperationRecord",
    "OperationOutcome",
    "OperatorOperationService",
    "authorize_for_consumption",
]

# ---------------------------------------------------------------------------
# Schema / storage constants
# ---------------------------------------------------------------------------

#: Additive-only schema versioning, mirroring `rbac_store.py`'s convention:
#: bump only when a real migration is applied; never drop/recreate.
_SCHEMA_VERSION = 1

#: Explicit busy-timeout (milliseconds) so lock contention under `BEGIN
#: IMMEDIATE` resolves deterministically within a bounded window rather than
#: relying on sqlite3's implicit 5-second default (the task's own
#: instruction: "Set an explicit busy_timeout so lock contention is
#: deterministic"). 15s comfortably covers the sub-millisecond hold time of
#: every transaction in this module even under real thread contention.
_BUSY_TIMEOUT_MS = 15_000

_DDL: tuple[str, ...] = (
    # confirmations: durable persistence of P1's `operator_mcp_confirmation`
    # records. `record_json` is the FULL schema-shaped record (mint_confirmation's
    # `.record`, later replaced wholesale by `consume_confirmation`'s return
    # value on the guarded transition) -- `status`/`workspace_id` are
    # denormalized columns purely for the CAS predicate and lookup, never the
    # source of truth (the JSON blob is).
    """
    CREATE TABLE IF NOT EXISTS confirmations (
        confirmation_id TEXT PRIMARY KEY,
        workspace_id    TEXT NOT NULL,
        status          TEXT NOT NULL,
        record_json     TEXT NOT NULL,
        created_at      TEXT NOT NULL
    )
    """,
    # operations: immutable operation manifests. UNIQUE(workspace_id,
    # idempotency_key) is the idempotency-conflict/exact-replay dedup key
    # (AC OPM-3) -- never relaxed to a plain index.
    """
    CREATE TABLE IF NOT EXISTS operations (
        operation_id            TEXT PRIMARY KEY,
        workspace_id            TEXT NOT NULL,
        idempotency_key         TEXT NOT NULL,
        canonical_input_digest  TEXT NOT NULL,
        policy_snapshot_version TEXT NOT NULL,
        operation_kind          TEXT NOT NULL,
        effective_sensitivity   TEXT NOT NULL,
        manifest_json           TEXT NOT NULL,
        created_at              TEXT NOT NULL,
        UNIQUE (workspace_id, idempotency_key)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_operations_workspace
        ON operations (workspace_id)
    """,
)


def _connect(paths: FoundryPaths) -> sqlite3.Connection:
    """Open (or create) the durable operator-operations database.

    Mirrors `rbac_store._connect`'s idiom exactly: `isolation_level=None`
    (autocommit -- callers issue explicit `BEGIN IMMEDIATE`/`COMMIT`/
    `ROLLBACK`), `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`.
    Additionally sets an explicit `busy_timeout` (both the DBAPI `timeout`
    kwarg and the `PRAGMA`, belt-and-suspenders) per this module's own
    determinism requirement.
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


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply the schema, additive-only (mirrors `rbac_store._ensure_schema`).

    Every statement in :data:`_DDL` uses `IF NOT EXISTS`, so this is safe to
    call on every connection open, including inside a caller's own
    transaction boundary (it is always called BEFORE any explicit `BEGIN
    IMMEDIATE` in this module, never inside one).
    """

    (version,) = conn.execute("PRAGMA user_version").fetchone()
    for stmt in _DDL:
        conn.execute(stmt)
    if version < _SCHEMA_VERSION:
        conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")


def _iso_utc(dt: datetime) -> str:
    """Same format `operator_mcp_policy._iso_utc` uses -- kept as an
    independent copy rather than importing a private helper across module
    boundaries."""

    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_OPERATION_ID_PREFIX = "opm_"


def _mint_operation_id(canonical_input_digest: str, idempotency_key: str) -> str:
    """Mint a fresh `opm_<64 hex>` operation id (P2's job -- P1's
    `mint_confirmation` mints `opc_...` confirmation ids only). Matches the
    `^opm_[a-f0-9]{64}$` pattern the plan freezes, and follows the same
    digest+key+random-salt construction `mint_confirmation` uses for
    `confirmation_id` -- deterministic reproducibility is not required (the
    idempotency-key uniqueness constraint is what makes replay detection
    deterministic, not the id's own shape)."""

    salt = secrets.token_hex(16)
    return _OPERATION_ID_PREFIX + hashlib.sha256(
        f"{canonical_input_digest}:{idempotency_key}:{salt}".encode("utf-8")
    ).hexdigest()


def _build_manifest(
    *,
    operation_id: str,
    ctx: "policy.PolicyContext",
    confirmation_id: str,
    consumed_at: str,
    action_manifest: Mapping[str, Any] | None,
    moment: datetime,
) -> dict[str, Any]:
    """Build the immutable operation manifest for a freshly consumed
    confirmation.

    The nested `operation` object is schema-shape-identical to
    `schemas/operator_mcp_operation.schema.yaml` (validated against it by
    the caller) -- every OTHER top-level field here (`operation_id`,
    `canonical_input_digest`, `confirmation_proof`, `target_refs`,
    `action_manifest`, ...) is this module's own durable-envelope shape, not
    part of that request schema (which is `additionalProperties: false` and
    has no field for token-consumption proof or an operation id -- those are
    lookup-time/execute-time facts the request envelope schema predates).

    ``ctx.identity`` MUST NOT be ``None`` here -- callers only reach this
    function after `verify_confirmation` returned `outcome == "accepted"`,
    which (via `_bindings_match`) already requires a non-`None` identity.
    """

    assert ctx.identity is not None, "manifest build requires a resolved ctx.identity"

    operation_envelope: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "operator_mcp_operation",
        "operation_kind": ctx.operation_kind,
        "actor": {
            "user_id": ctx.identity.user_id,
            "workspace_id": ctx.identity.workspace_id,
            "roles": sorted(ctx.identity.roles),
        },
        "idempotency_key": ctx.idempotency_key,
        "targets": [t.to_dict() for t in ctx.targets],
        "input_payload": dict(ctx.input_payload),
        "policy_snapshot_version": ctx.policy_snapshot_version,
        "effective_sensitivity": ctx.effective_sensitivity,
        "requested_at": _iso_utc(moment),
    }

    return {
        "schema_version": "1.0",
        "type": "operator_mcp_operation_manifest",
        "operation_id": operation_id,
        "workspace_id": ctx.identity.workspace_id,
        "operation": operation_envelope,
        "canonical_input_digest": ctx.canonical_digest(),
        "policy_snapshot_version": ctx.policy_snapshot_version,
        "effective_sensitivity": ctx.effective_sensitivity,
        "target_refs": [t.to_dict() for t in ctx.targets],
        "confirmation_proof": {
            "confirmation_id": confirmation_id,
            "consumed_at": consumed_at,
        },
        "action_manifest": dict(action_manifest) if action_manifest is not None else {},
        "created_at": _iso_utc(moment),
    }


class _Dur1InvariantViolation(RuntimeError):
    """Internal-only: DUR-1's own single-writer CAS-exclusivity invariant
    was violated (F4).

    Raised exactly once, at the `cur.rowcount != 1` guard inside
    `_consume_locked`, and caught by `consume_and_create_operation` --
    NEVER allowed to propagate raw out of this module. A raw `RuntimeError`
    escaping this boundary would violate
    `schemas/operator_mcp_error.schema.yaml`'s bounded/redacted contract
    (AC OPM-7) the moment any caller (an MCP tool handler, a test) let it
    bubble past its own try/except into a caller-visible message. The full,
    loud, un-redacted detail is still logged server-side via `_logger.error`
    at the raise site -- ONLY the caller-visible surface is bounded, never
    the operator's own diagnostic trail.
    """


# ---------------------------------------------------------------------------
# F1: authorization as a data dependency (DUR-1's other half)
# ---------------------------------------------------------------------------
#
# `consume_and_create_operation`'s only prior authorization guard was its
# OWN DOCSTRING instruction that callers must have already obtained an
# `allowed` decision from `operator_mcp_policy.authorize_operation` --
# structurally identical to the P1 round-2 critical defect, where
# `authorize_operation` was hardened while a weaker, doc-only-gated door
# stayed reachable. `AuthorizationProof` closes that door: it is the ONLY
# object `consume_and_create_operation` accepts as proof of authorization,
# and the ONLY way to construct one is :func:`authorize_for_consumption`,
# which calls `operator_mcp_policy.authorize_operation` exactly once and
# immediately stamps the result with the digest of the EXACT `PolicyContext`
# it was computed against -- mirroring the "one sanctioned way" factory
# idiom `PolicyContext.for_configured_operator` already uses in
# `operator_mcp_policy.py` (NEW-18 Layer 2) for the identical problem
# (closing a public forgery/bypass seam by removing every OTHER path to the
# same object, not merely documenting the sanctioned one).
#
# **Why this checks `decision.stage == "confirmation"`, not literally
# `decision.allowed`** (the plan's own wording says "it is allowed" --
# recorded here because a literal read would be WRONG and would regress a
# frozen OPM-2.1 acceptance criterion): `operator_mcp_policy.authorize_operation`
# ALWAYS returns `allowed=False, reason_code="confirmation_replayed"` for an
# exact-replay presentation (P1's own C1/NEW-1 guarantee, `test_operator_mcp_policy
# .test_authorize_operation_denies_exact_replay_never_returns_accept`) -- by
# design, so that a naive `if authorize_operation(...).allowed: execute()`
# caller can never execute twice. But `consume_and_create_operation` itself
# is NOT that naive caller: exact-replay resolving to the SAME
# pre-existing operation (never minting a second effect) is core OPM-2.1
# acceptance criteria for THIS module (see the docstrings on
# `OperationOutcome` and `_consume_locked`'s own exact-replay branch, and
# `test_operator_operation_service.test_same_confirmation_presented_twice_is_exact_replay_of_same_operation`).
# Requiring literal `allowed is True` here would make every legitimate
# idempotent retry deny instead of replay-resolve -- trading one bug
# (fail-open on the missing gate) for a different one (fail-closed on a
# safe, already-tested, frozen retry path). `PolicyDecision.stage` is the
# right predicate instead: `authorize_operation`'s own control flow (see its
# docstring/body) returns EARLY, before ever reaching the confirmation
# stage, for every capability/RBAC/audit-health/guard/preflight denial --
# so `stage == "confirmation"` is true if and only if all FIVE of those
# prior stages already passed, regardless of what the confirmation stage
# itself then decided (accepted / exact_replay / mismatched / expired /
# missing / idempotency_conflict). Those confirmation-specific outcomes are
# exactly what `_consume_locked`'s OWN independent `verify_confirmation` +
# `consume_confirmation` re-check (unchanged by this fix, and still the
# actual DUR-1 atomicity guarantee) is responsible for classifying -- this
# gate's only job is making sure that re-check is never reached without the
# five stages it cannot itself see having already been evaluated and passed.
# A decision denied at ANY earlier stage (`decision.stage != "confirmation"`)
# is propagated here using that stage's own `reason_code`, never silently
# reinterpreted as a confirmation problem.


@dataclass(frozen=True)
class AuthorizationProof:
    """Binds a `operator_mcp_policy.PolicyDecision` to the EXACT
    `PolicyContext` it was computed against, via `ctx.canonical_digest()`.

    The ONLY sanctioned constructor is :func:`authorize_for_consumption` --
    there is deliberately no public way to build one with a hand-picked
    `decision`/`ctx_digest` pair pointing at different requests (mirrors
    `PolicyContext.for_configured_operator`'s own "one sanctioned way"
    idiom). `consume_and_create_operation` re-derives `ctx.canonical_digest()`
    from the `ctx` IT was called with and compares against `ctx_digest` --
    so a proof minted for one operation can never be replayed against a
    different one, even by a caller holding a valid, unexpired proof.
    """

    decision: "policy.PolicyDecision"
    ctx_digest: str


def authorize_for_consumption(
    ctx: "policy.PolicyContext",
    *,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
) -> AuthorizationProof:
    """The ONE sanctioned way to obtain an `AuthorizationProof` (F1).

    Calls `operator_mcp_policy.authorize_operation` -- re-validating
    capability, RBAC, audit-health, guard, preflight, and (for
    confirmation-required kinds) the confirmation binding -- exactly once,
    and immediately stamps the result with `ctx.canonical_digest()` before
    handing it back. Callers MUST call this (never construct
    `AuthorizationProof` any other way) before calling
    `OperatorOperationService.consume_and_create_operation`.

    Deliberately called OUTSIDE any `BEGIN IMMEDIATE` transaction (NB-9,
    P1 finding): `evaluate_policy`'s audit-health stage does its own
    INSERT+SELECT+DELETE probe, so running this INSIDE the DUR-1 exclusive
    lock would surface as spurious `audit_unhealthy` denials and lock
    contention under concurrency. `now` and `paths` are forwarded verbatim
    to `operator_mcp_policy.authorize_operation`'s own (frozen, P1-owned)
    seams -- this wrapper adds no new clock/config-injection surface of its
    own, only the digest stamp.
    """

    decision = policy.authorize_operation(
        ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        paths=paths,
        now=now,
    )
    return AuthorizationProof(decision=decision, ctx_digest=ctx.canonical_digest())


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationRecord:
    """A persisted, immutable operation manifest."""

    operation_id: str
    workspace_id: str
    manifest: Mapping[str, Any]

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, Any]) -> "OperationRecord":
        return cls(
            operation_id=manifest["operation_id"],
            workspace_id=manifest["workspace_id"],
            manifest=manifest,
        )


@dataclass(frozen=True)
class OperationOutcome:
    """Result of :meth:`OperatorOperationService.consume_and_create_operation`.

    `outcome`:
        `"created"`
            A brand-new operation manifest was durably persisted and the
            presented confirmation was consumed in the same transaction.
        `"exact_replay"`
            No new manifest was created -- either the SAME confirmation was
            presented again (P1's `exact_replay`, resolved via the
            confirmation record's own `consumed_by_operation_id`), or a
            FRESH confirmation matched an existing `(workspace_id,
            idempotency_key)` row with the SAME `canonical_input_digest`
            (still consumed, pointing at the pre-existing operation).
            `.operation` is the pre-existing operation in both cases.
        `"idempotency_conflict"`
            The presented confirmation is otherwise valid, but
            `(workspace_id, idempotency_key)` already maps to a DIFFERENT
            `canonical_input_digest` -- zero manifest, zero effect, and the
            confirmation is left unconsumed.
        `"denied"`
            The confirmation itself was not usable (missing, expired,
            mismatched, revoked, replayed-with-different-bindings, or an
            internal error) -- `reason_code` is one of
            `operator_mcp_policy.CLOSED_REASON_CODES`. Zero manifest, zero
            effect.
    """

    outcome: Literal["created", "exact_replay", "idempotency_conflict", "denied"]
    reason_code: str | None
    operation: OperationRecord | None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OperatorOperationService:
    """Durable persistence for Operator MCP confirmations and operation
    manifests (P2, OPM-2.1). See module docstring for the DUR-1 contract."""

    def __init__(self, paths: FoundryPaths) -> None:
        self._paths = paths
        self._schemas = SchemaRegistry(schemas_dir=paths.schemas if paths.schemas.exists() else None)

    # -- confirmation persistence ---------------------------------------

    def record_confirmation(self, record: Mapping[str, Any]) -> None:
        """Durably persist a freshly minted confirmation record (the
        `.record` of `operator_mcp_policy.mint_confirmation`'s
        `ConfirmationIssued` return value) so it can later be atomically
        consumed by :meth:`consume_and_create_operation`.

        Raises `ValueError` if the record is missing `confirmation_id` or
        `actor.workspace_id`, if `status` is anything other than exactly
        `"issued"`, or if `issued_at` is missing/empty -- a malformed record
        is a caller programming error (mirrors this module's convention of
        failing loudly on contract violations rather than silently
        persisting something unusable), never a runtime/caller-input
        condition.

        **F3 (fail-open defaults on security-relevant fields)**: earlier
        revisions defaulted a missing `status` to `"issued"` -- the ONE
        value that permits later consumption -- and a missing `issued_at`
        to *now*, which (via `_record_expiry`'s clamp) MAXIMIZES rather than
        minimizes the effective TTL window for a malformed record. Both
        `None`-means-permissive substitutions are REJECTED here instead:
        the record is durably persisted only if it already, explicitly,
        carries a valid `status`/`issued_at` -- never coerced into looking
        like a freshly, correctly minted one.

        This also closes the two-sources-of-truth divergence between the
        denormalized `status` COLUMN (the CAS predicate's own gate) and the
        `status` field INSIDE `record_json` (what `verify_confirmation`/
        `consume_confirmation` actually read): both are now derived from
        the SAME validated `status` local, in the SAME statement, so they
        cannot disagree at write time the way an independently-defaulted
        column previously could (e.g. a record missing the `status` key
        entirely used to write column `"issued"` while the persisted JSON
        blob carried no `status` field at all -- silently divergent from
        the moment it was written). The CAS `UPDATE` in `_consume_locked`
        already writes both together from the SAME `updated_record`
        (`policy.consume_confirmation`'s own `status="consumed"`
        assignment); this closes the ONLY OTHER write path in this module.
        """

        confirmation_id = record.get("confirmation_id")
        actor = record.get("actor")
        workspace_id = actor.get("workspace_id") if isinstance(actor, Mapping) else None
        if not confirmation_id or not workspace_id:
            raise ValueError(
                "record_confirmation requires a confirmation_id and actor.workspace_id"
            )
        status = record.get("status")
        if status != "issued":
            raise ValueError(
                f"record_confirmation requires status == 'issued' for a freshly "
                f"minted record (got {status!r}) -- never defaulted"
            )
        issued_at = record.get("issued_at")
        if not isinstance(issued_at, str) or not issued_at:
            raise ValueError("record_confirmation requires a non-empty issued_at -- never defaulted")

        conn = _connect(self._paths)
        try:
            _ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO confirmations"
                    " (confirmation_id, workspace_id, status, record_json, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (confirmation_id, workspace_id, status, json.dumps(dict(record)), issued_at),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

    # -- DUR-1: atomic confirmation-consumption + manifest write --------

    def consume_and_create_operation(
        self,
        *,
        confirmation_id: str,
        presented_token: str,
        ctx: "policy.PolicyContext",
        authorization: AuthorizationProof | None = None,
        action_manifest: Mapping[str, Any] | None = None,
    ) -> OperationOutcome:
        """The DUR-1 compare-and-swap: verify the presented confirmation,
        atomically transition it `issued -> consumed`, and durably persist
        the operation manifest -- all in one `BEGIN IMMEDIATE` transaction
        on one connection.

        **F1 (authorization is now a DATA DEPENDENCY, not a docstring)**:
        callers MUST pass `authorization`, the `AuthorizationProof` returned
        by :func:`authorize_for_consumption` for THIS exact `ctx` --
        capability, RBAC, audit-health, guard, and preflight are all
        re-validated there. `authorization=None` (the default) or an
        `authorization` computed for a DIFFERENT `PolicyContext` (detected
        via `ctx.canonical_digest()`) denies immediately, before this method
        even opens a database connection -- see :data:`AuthorizationProof`'s
        module-level comment for why the gate checks
        `authorization.decision.stage == "confirmation"` rather than
        literally `authorization.decision.allowed`. This method's OWN
        `_consume_locked` re-validates ONLY the confirmation-binding
        predicate (via `verify_confirmation` then the guarded
        `consume_confirmation` CAS) -- unchanged by this fix, and still the
        actual DUR-1 atomicity guarantee against concurrent consumers of the
        SAME confirmation.

        `now` was removed (F2 / P1 finding NB-4: a public `now` here would
        let a caller thread an arbitrary request-supplied timestamp straight
        into the expiry-clamp check on this durability boundary). The
        `moment` used for the CAS and the manifest's `created_at`/
        `requested_at` is always `research_foundry.ids.now()` -- the
        repo-wide injectable clock (`ids.set_clock()`), pinned to a fixed
        value for the whole test suite by the autouse `_fixed_clock`
        fixture in `tests/conftest.py`; a test that needs to move time
        forward calls `ids.set_clock(...)` (or monkeypatches `ids.now`)
        itself, exactly like every other service in this codebase.
        """

        if authorization is None:
            return OperationOutcome("denied", "internal_error", None)
        decision = authorization.decision
        if decision.stage != "confirmation":
            # Denied at capability/RBAC/audit-health/guard/preflight --
            # never even reached the confirmation stage. Propagate that
            # stage's own reason_code; never proceed to the CAS, which has
            # no visibility into any of those five checks.
            return OperationOutcome("denied", decision.reason_code or "internal_error", None)
        if authorization.ctx_digest != ctx.canonical_digest():
            # F1(c): the decision was minted for a DIFFERENT PolicyContext.
            # A proof cannot be replayed against an operation it was never
            # computed for, even if it is itself valid and unexpired.
            return OperationOutcome("denied", "internal_error", None)

        moment = ids.now()
        conn = _connect(self._paths)
        try:
            _ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                outcome = self._consume_locked(
                    conn,
                    confirmation_id=confirmation_id,
                    presented_token=presented_token,
                    ctx=ctx,
                    action_manifest=action_manifest,
                    moment=moment,
                )
                conn.execute("COMMIT")
                return outcome
            except _Dur1InvariantViolation:
                # F4: never let this escape raw -- already logged loudly
                # (server-side, `_logger.error`) at the raise site inside
                # `_consume_locked`. Roll back and return the SAME bounded,
                # governed denial shape every other closed path here uses.
                conn.execute("ROLLBACK")
                return OperationOutcome("denied", "internal_error", None)
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

    def _consume_locked(
        self,
        conn: sqlite3.Connection,
        *,
        confirmation_id: str,
        presented_token: str,
        ctx: "policy.PolicyContext",
        action_manifest: Mapping[str, Any] | None,
        moment: datetime,
    ) -> OperationOutcome:
        """The critical section -- MUST only ever be called while holding
        the `BEGIN IMMEDIATE` exclusive lock acquired by the caller."""

        row = conn.execute(
            "SELECT record_json FROM confirmations WHERE confirmation_id = ?",
            (confirmation_id,),
        ).fetchone()
        if row is None:
            return OperationOutcome("denied", "confirmation_missing", None)
        record: dict[str, Any] = json.loads(row["record_json"])

        # Full verify (token digest + status + clamped expiry + bindings) --
        # NOT the bare `consume_confirmation` CAS alone -- so a caller gets
        # the precise, P1-defined denial classification (missing/expired/
        # mismatched/replayed/internal_error) rather than a single generic
        # conflict. `moment` is threaded through unchanged so this check and
        # the guarded consume below observe an IDENTICAL clock reading.
        verification = policy.verify_confirmation(
            record, presented_token=presented_token, ctx=ctx, now=moment
        )

        if verification.outcome == "exact_replay":
            # P1's structurally-non-accepting replay case: the SAME
            # confirmation was already consumed, still binds this exact
            # ctx, and is still within its clamped expiry. Do not re-attempt
            # the CAS (it would correctly no-op via consume_confirmation's
            # own `status != "issued"` guard) -- resolve directly to the
            # operation the FIRST consumption already recorded.
            existing_operation_id = record.get("consumed_by_operation_id")
            operation = (
                self._fetch_operation(conn, existing_operation_id)
                if existing_operation_id
                else None
            )
            return OperationOutcome("exact_replay", None, operation)

        if verification.outcome != "accepted":
            # missing / expired / mismatched (includes revoked and
            # different-bindings-on-a-consumed-record) / error.
            return OperationOutcome("denied", verification.decision.reason_code, None)

        if ctx.identity is None:  # pragma: no cover - unreachable: see docstring
            # `verify_confirmation`'s `_bindings_match` returns False (never
            # "accepted") whenever `ctx.identity is None` -- this branch is
            # defense in depth only, matching this module's convention of
            # never trusting a downstream invariant by silence alone.
            return OperationOutcome("denied", "internal_error", None)

        workspace_id = ctx.identity.workspace_id
        digest = ctx.canonical_digest()

        existing_row = conn.execute(
            "SELECT operation_id, canonical_input_digest, manifest_json FROM operations"
            " WHERE workspace_id = ? AND idempotency_key = ?",
            (workspace_id, ctx.idempotency_key),
        ).fetchone()

        if existing_row is not None and existing_row["canonical_input_digest"] != digest:
            # AC OPM-3 / DUR-1: a changed manifest under the same
            # idempotency_key is a conflict -- zero manifest, zero effect.
            # The presented confirmation is left `issued` (never consumed
            # for a request the server refused to execute); it may still
            # legitimately time out via its own TTL.
            return OperationOutcome("idempotency_conflict", "idempotency_conflict", None)

        reusing_existing = existing_row is not None
        operation_id = (
            existing_row["operation_id"] if reusing_existing else _mint_operation_id(digest, ctx.idempotency_key)
        )

        # The DUR-1 CAS itself -- `consume_confirmation` re-checks status ==
        # "issued", the clamped expiry, AND the binding predicate against
        # THIS `record`/`ctx`/`moment` (the identical inputs `verify_confirmation`
        # just used) before returning a transitioned copy, or `None` on any
        # precondition failure.
        updated_record = policy.consume_confirmation(
            record, operation_id=operation_id, ctx=ctx, now=moment
        )
        if updated_record is None:
            # DUR-1: the CAS precondition failed -- route to conflict, do
            # not execute. Reachable in practice only if `record` was
            # mutated between the two calls, which cannot happen inside
            # this single locked transaction; kept as the frozen contract's
            # own fail-closed path rather than assumed impossible.
            return OperationOutcome("denied", "idempotency_conflict", None)

        cur = conn.execute(
            "UPDATE confirmations SET status = 'consumed', record_json = ?"
            " WHERE confirmation_id = ? AND status = 'issued'",
            (json.dumps(updated_record), confirmation_id),
        )
        if cur.rowcount != 1:
            # DUR-1's own invariant: under BEGIN IMMEDIATE's exclusive lock,
            # a status of "issued" observed by `consume_confirmation` above
            # MUST still be "issued" here -- no other writer can have run
            # between the two statements on this connection/transaction. A
            # rowcount other than 1 means that invariant was violated (e.g.
            # a future refactor that reuses a connection across threads, or
            # a caller committing an earlier connection concurrently outside
            # this method) -- fail loudly rather than silently corrupt the
            # ledger.
            #
            # F4: the FULL detail stays server-side, in the log, forever --
            # only a bounded `_Dur1InvariantViolation` (caught by
            # `consume_and_create_operation`, never allowed to cross the
            # module boundary raw) is raised. A raw `RuntimeError.__str__`
            # reaching a caller would violate
            # `schemas/operator_mcp_error.schema.yaml`'s bounded/redacted
            # contract the moment anything downstream serialized it verbatim.
            _logger.error(
                "operator_operation_service: DUR-1 CAS observed rowcount=%d "
                "(expected 1) for confirmation_id=%s -- a concurrent writer "
                "bypassed BEGIN IMMEDIATE exclusivity",
                cur.rowcount,
                confirmation_id,
            )
            raise _Dur1InvariantViolation(
                "operator_operation_service: DUR-1 CAS invariant violated"
            )

        if reusing_existing:
            manifest = json.loads(existing_row["manifest_json"])
            return OperationOutcome(
                "exact_replay", None, OperationRecord.from_manifest(manifest)
            )

        manifest = _build_manifest(
            operation_id=operation_id,
            ctx=ctx,
            confirmation_id=confirmation_id,
            consumed_at=updated_record["consumed_at"],
            action_manifest=action_manifest,
            moment=moment,
        )
        validation = self._schemas.validate(manifest["operation"], "operator_mcp_operation")
        if not validation.ok:  # pragma: no cover - defense in depth
            # Should be unreachable: `manifest["operation"]` is built
            # entirely from an already-`PolicyContext.__post_init__`-
            # validated `ctx`. Never log the errors themselves (they could
            # echo caller-influenced values) -- only the count, mirroring
            # `operator_mcp_policy.py`'s NEW-13 "log the type, never the
            # content" convention.
            raise RuntimeError(
                f"operator_operation_service: manifest failed schema validation "
                f"({len(validation.errors)} error(s))"
            )

        conn.execute(
            "INSERT INTO operations"
            " (operation_id, workspace_id, idempotency_key, canonical_input_digest,"
            "  policy_snapshot_version, operation_kind, effective_sensitivity,"
            "  manifest_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                operation_id,
                workspace_id,
                ctx.idempotency_key,
                digest,
                ctx.policy_snapshot_version,
                ctx.operation_kind,
                ctx.effective_sensitivity,
                json.dumps(manifest),
                _iso_utc(moment),
            ),
        )
        return OperationOutcome("created", None, OperationRecord.from_manifest(manifest))

    def _fetch_operation(
        self, conn: sqlite3.Connection, operation_id: str
    ) -> OperationRecord | None:
        row = conn.execute(
            "SELECT manifest_json FROM operations WHERE operation_id = ?",
            (operation_id,),
        ).fetchone()
        if row is None:
            return None
        return OperationRecord.from_manifest(json.loads(row["manifest_json"]))

    # -- read path --------------------------------------------------------

    def load_operation(
        self, operation_id: str, *, identity: AuthIdentity | None = None
    ) -> OperationRecord:
        """Load a persisted operation manifest by id.

        Mirrors `AgentJobService.load_job`'s workspace-scoping shape
        exactly: a wrong-workspace lookup raises the IDENTICAL `KeyError`
        message as a genuinely missing operation -- the two cases are
        indistinguishable to any caller (H6's no-existence-leak convention,
        extended to this store). The mismatch is distinguished only by a
        server-side `ERROR` log line, never in anything caller-reachable.
        `identity=None` performs no workspace scoping at all (local-trust /
        no-identity callers -- matches `load_job`'s own `identity=None`
        default behavior).

        Raises
        ------
        KeyError
            If no operation with `operation_id` exists, or (when `identity`
            is supplied) it belongs to a different workspace.
        """

        conn = _connect(self._paths)
        try:
            _ensure_schema(conn)
            row = conn.execute(
                "SELECT manifest_json, workspace_id FROM operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            raise KeyError(f"operation not found: {operation_id}")
        if identity is not None and row["workspace_id"] != identity.workspace_id:
            _logger.error(
                json.dumps(
                    {
                        "event": "workspace_scope_enforced_denial",
                        "record_type": "operation",
                        "record_id": operation_id,
                        "record_workspace_id": row["workspace_id"],
                        "identity_workspace_id": identity.workspace_id,
                    }
                )
            )
            raise KeyError(f"operation not found: {operation_id}")
        return OperationRecord.from_manifest(json.loads(row["manifest_json"]))
