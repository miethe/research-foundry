"""Unit tests for :mod:`research_foundry.services.operator_receipt_service`
(research-foundry-operator-mcp-v1 P2, OPM-2.3).

Covers the acceptance criterion verbatim: "Truncated/extra/duplicate/
reordered/mismatched receipt fixtures deny" -- one test per defect class,
each exercised against REAL sqlite persistence (never a fake/monkeypatched
store), per this task's proof requirement.

Also covers:

* the quality-gate invariant that the terminal receipt is PRIMARY and an
  audit-service failure never erases or blocks it (`audit_delivery.status
  == "unavailable"`, receipt still produced, still schema-valid);
* `completed_action_count <= total_action_count` enforcement on both
  `write_checkpoint` and (defense in depth) the reconciliation path;
* `checkpoint` mutability (atomic replace, no immutability trigger) versus
  `action_receipt`/`effect_receipt`/`terminal_receipt` immutability
  (DB-level triggers reject UPDATE/DELETE, not merely application
  discipline);
* `finalize_terminal_receipt` idempotency (second call for the same
  operation_id resolves to the existing row, never a second one).
"""

from __future__ import annotations

import sqlite3

import pytest

from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.operator_receipt_service import (
    OperatorReceiptService,
    ReceiptOutcome,
    _validate_action_counts,
)

_OPERATION_ID = "opm_" + "a" * 64
_OTHER_OPERATION_ID = "opm_" + "b" * 64
_PHANTOM_OPERATION_ID = "opm_" + "c" * 64  # deliberately NEVER seeded -- see P2S-BLOCK-4 tests
_WORKSPACE = "ws-mine"

# P2S-BLOCK-3 identity fixtures -- `_IDENTITY`'s workspace matches
# `_WORKSPACE` (the workspace every seeded operation in this module
# lives in); `_IDENTITY_OTHER_WORKSPACE` never does.
_IDENTITY = AuthIdentity("alice", _WORKSPACE, ("owner",))
_IDENTITY_OTHER_WORKSPACE = AuthIdentity("mallory", "ws-attacker", ("owner",))

_SHA = lambda tag: __import__("hashlib").sha256(tag.encode()).hexdigest()  # noqa: E731


def _service(paths: FoundryPaths) -> OperatorReceiptService:
    return OperatorReceiptService(paths)


def _raw_connect(paths: FoundryPaths) -> sqlite3.Connection:
    conn = sqlite3.connect(str(paths.operator_operations_db))
    conn.row_factory = sqlite3.Row
    return conn


def _seed_operation(
    paths: FoundryPaths, operation_id: str, workspace_id: str = _WORKSPACE
) -> None:
    """Insert a minimal, REAL `operations` row via raw SQL, through the
    schema-owning module's own `_connect`/`_ensure_schema` (P2-ARCH-1).

    P2S-BLOCK-4 hardening changed `record_action_receipt`/
    `record_effect_receipt`/`write_checkpoint`/`finalize_terminal_receipt`
    to DENY when `operation_id` has no persisted operation manifest --
    closing the exact referential-integrity gap this test module's OWN
    fixtures used to exploit unintentionally (every test below used to
    call these methods against a purely fabricated `operation_id` with no
    `operations` row at all, which is precisely the P2S-BLOCK-4
    vulnerability: a receipt for an operation that was never created).
    This helper seeds a real row so this module's tests exercise the
    HAPPY path of the new guard, not its own former hole -- never a fake
    or in-memory stand-in, an actual persisted row in the actual table.
    """

    from research_foundry.services import operator_operation_service as _ops_store

    conn = _ops_store._connect(paths)
    try:
        _ops_store._ensure_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR IGNORE INTO operations"
            " (operation_id, workspace_id, idempotency_key, canonical_input_digest,"
            "  policy_snapshot_version, operation_kind, effective_sensitivity,"
            "  manifest_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                operation_id,
                workspace_id,
                f"idem-{operation_id}",
                _SHA(operation_id),
                "v1",
                "run.plan",
                "public",
                "{}",
                "2026-07-29T00:00:00Z",
            ),
        )
        conn.execute("COMMIT")
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _seed_operations(tmp_foundry: FoundryPaths) -> None:
    """Every test in this module exercises receipt persistence against a
    REAL, referentially-valid `operation_id` -- see P2S-BLOCK-4. Seeds both
    ids this module's tests use, in the SAME workspace (`_WORKSPACE`) every
    test already asserts against."""

    _seed_operation(tmp_foundry, _OPERATION_ID, _WORKSPACE)
    _seed_operation(tmp_foundry, _OTHER_OPERATION_ID, _WORKSPACE)


def _record_action(
    service: OperatorReceiptService,
    *,
    operation_id: str = _OPERATION_ID,
    workspace_id: str = _WORKSPACE,
    action_id: str,
    action_index: int,
    status: str = "completed",
    reason_code: str | None = None,
) -> ReceiptOutcome:
    return service.record_action_receipt(
        operation_id,
        workspace_id=workspace_id,
        action_id=action_id,
        action_index=action_index,
        status=status,
        attempt_ref="attempt-1",
        started_at="2026-07-29T00:00:00Z",
        completed_at="2026-07-29T00:00:05Z",
        reason_code=reason_code,
    )


# ---------------------------------------------------------------------------
# action_receipt: golden path + schema validity
# ---------------------------------------------------------------------------


def test_action_receipt_golden_path_persists_schema_valid_row(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    outcome = _record_action(service, action_id="act-0", action_index=0)

    assert outcome.outcome == "created"
    assert outcome.reason_code is None
    registry = SchemaRegistry(schemas_dir=tmp_foundry.schemas if tmp_foundry.schemas.exists() else None)
    result = registry.validate(outcome.receipt, "operator_mcp_receipt")
    assert result.ok, result.errors

    conn = _raw_connect(tmp_foundry)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?", (_OPERATION_ID,)
        ).fetchone()
        assert row[0] == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DUPLICATE (action_receipt): same action_index submitted twice denies.
# ---------------------------------------------------------------------------


def test_duplicate_action_receipt_same_index_denies(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    first = _record_action(service, action_id="act-0", action_index=0)
    assert first.outcome == "created"

    second = _record_action(service, action_id="act-0-again", action_index=0)
    assert second.outcome == "denied"
    assert second.reason_code == "internal_error"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?", (_OPERATION_ID,)
        ).fetchone()[0]
        assert count == 1  # the denied duplicate never persisted a second row
    finally:
        conn.close()


def test_duplicate_effect_receipt_same_digest_denies(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    digest = _SHA("effect-1")
    first = service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=digest,
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert first.outcome == "created"

    second = service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=digest,
        effect_ref="source_card:xyz999",
        generated_at="2026-07-29T00:00:07Z",
    )
    assert second.outcome == "denied"
    assert second.reason_code == "internal_error"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM effect_receipts WHERE effect_digest = ?", (digest,)
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# MISMATCHED: effect_receipt.action_id references no persisted action.
# ---------------------------------------------------------------------------


def test_mismatched_effect_receipt_unknown_action_id_denies(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    # Deliberately never record an action_receipt for "act-ghost".
    outcome = service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-ghost",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-mismatched"),
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute("SELECT COUNT(*) FROM effect_receipts").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# TRUNCATED / EXTRA / REORDERED: finalize_terminal_receipt reconciliation.
# ---------------------------------------------------------------------------


def test_truncated_action_receipts_denies_finalize(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    _record_action(service, action_id="act-1", action_index=1)
    # Only 2 of the expected 3 actions were ever persisted.

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=3,
        status="completed",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert service.load_terminal_receipt(_OPERATION_ID) is None


def test_extra_action_receipts_denies_finalize(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    _record_action(service, action_id="act-1", action_index=1)
    _record_action(service, action_id="act-2", action_index=2)
    # 3 persisted, but the operation only declared 2 expected actions.

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=2,
        status="completed",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert service.load_terminal_receipt(_OPERATION_ID) is None


def test_reordered_action_receipts_denies_finalize(tmp_foundry: FoundryPaths) -> None:
    """U5/REGATE-BLOCK-3 changed what "REORDERED" means as a REACHABLE
    state: `record_action_receipt` now refuses any `action_index` that
    is not the next contiguous index at WRITE time, so a gap/out-of-order
    sequence can no longer be created through this module's own governed
    API at all (`_record_action(service, action_id="act-3",
    action_index=3)` against an operation with only indices 0-1 persisted
    would itself now be DENIED -- proven directly by
    `test_gap_receipt_denies_at_write_time_operation_remains_resumable`
    above). This test now plants the reordered state via raw SQL (real
    persistence, bypassing this module's write path entirely -- the SAME
    pattern `test_record_effect_receipt_direct_referential_guard_fires_
    even_when_mismatch_guard_would_not` already uses) to prove
    `finalize_terminal_receipt`'s own reconciliation remains a correct
    defense-in-depth backstop for out-of-band writes, independent of the
    write-time guard."""

    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    _record_action(service, action_id="act-1", action_index=1)

    conn = _raw_connect(tmp_foundry)
    try:
        # Skip index 2 entirely; jump to 3 -- exactly 3 rows persisted
        # (matches expected_action_count) but NOT the contiguous 0..2
        # sequence. Only reachable out-of-band -- see docstring above.
        conn.execute(
            "INSERT INTO action_receipts"
            " (operation_id, action_id, action_index, status, attempt_ref,"
            "  started_at, completed_at, reason_code, retryable, receipt_json, created_at)"
            " VALUES (?, 'act-3', 3, 'completed', 'attempt-x', ?, ?, NULL, NULL, '{}', ?)",
            (
                _OPERATION_ID,
                "2026-07-29T00:00:00Z",
                "2026-07-29T00:00:00Z",
                "2026-07-29T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=3,
        status="completed",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert service.load_terminal_receipt(_OPERATION_ID) is None


# ---------------------------------------------------------------------------
# Golden finalize path: reconciliation succeeds, terminal receipt persists.
# ---------------------------------------------------------------------------


def test_finalize_terminal_receipt_golden_path(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    _record_action(service, action_id="act-1", action_index=1)
    digest = _SHA("effect-golden")
    effect_outcome = service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=digest,
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert effect_outcome.outcome == "created"

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=2,
        status="completed",
    )
    assert outcome.outcome == "created"
    receipt = outcome.receipt
    assert receipt["kind"] == "terminal_receipt"
    assert receipt["operation_id"] == _OPERATION_ID
    assert receipt["action_count_total"] == 2
    assert receipt["action_count_completed"] == 2
    assert receipt["effect_receipt_refs"] == [digest]
    assert receipt["denial_reason_code"] is None
    assert receipt["audit_delivery"]["status"] in ("delivered", "unavailable")

    registry = SchemaRegistry(schemas_dir=tmp_foundry.schemas if tmp_foundry.schemas.exists() else None)
    result = registry.validate(receipt, "operator_mcp_receipt")
    assert result.ok, result.errors


def test_finalize_terminal_receipt_is_idempotent(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    first = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )
    assert first.outcome == "created"

    second = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )
    assert second.outcome == "exact_replay"
    assert second.receipt == first.receipt

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM terminal_receipts WHERE operation_id = ?", (_OPERATION_ID,)
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Quality gate: audit-service failure never erases or blocks effect truth.
# ---------------------------------------------------------------------------


def test_audit_delivery_failure_never_blocks_terminal_receipt(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate `audit_service.record_event` failing (its own documented
    fail-open contract: returns `None`, never raises) and prove the
    terminal receipt is STILL produced, STILL schema-valid, and its effect
    truth (`effect_receipt_refs`/`action_count_*`) is UNCHANGED -- only
    `audit_delivery.status` reflects the failure.
    """

    from research_foundry.services import audit_service

    def _fail(paths: FoundryPaths, event: object) -> None:
        return None

    monkeypatch.setattr(audit_service, "record_event", _fail)

    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    digest = _SHA("effect-audit-fail")
    service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=digest,
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )

    assert outcome.outcome == "created"
    receipt = outcome.receipt
    assert receipt["audit_delivery"]["status"] == "unavailable"
    # Effect truth is intact regardless of audit delivery.
    assert receipt["action_count_total"] == 1
    assert receipt["action_count_completed"] == 1
    assert receipt["effect_receipt_refs"] == [digest]

    registry = SchemaRegistry(schemas_dir=tmp_foundry.schemas if tmp_foundry.schemas.exists() else None)
    result = registry.validate(receipt, "operator_mcp_receipt")
    assert result.ok, result.errors

    # And it is durably persisted -- not merely returned in-memory.
    persisted = service.load_terminal_receipt(_OPERATION_ID)
    assert persisted == receipt


# ---------------------------------------------------------------------------
# completed_action_count <= total_action_count enforcement.
# ---------------------------------------------------------------------------


def test_validate_action_counts_rejects_completed_exceeding_total() -> None:
    with pytest.raises(ValueError):
        _validate_action_counts(5, 1)


def test_validate_action_counts_accepts_equal_or_fewer() -> None:
    _validate_action_counts(1, 1)
    _validate_action_counts(0, 3)


def test_write_checkpoint_rejects_completed_exceeding_total(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    with pytest.raises(ValueError):
        service.write_checkpoint(
            _OPERATION_ID,
            workspace_id=_WORKSPACE,
            status="pending",
            next_action_index=1,
            completed_action_count=5,
            total_action_count=1,
            non_cancelable=False,
        )

    # Nothing was persisted -- the raise happens before any DB write. The
    # db file may not even exist yet (the very first write in this test),
    # so check existence before opening it.
    if tmp_foundry.operator_operations_db.exists():
        conn = _raw_connect(tmp_foundry)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM checkpoints WHERE operation_id = ?", (_OPERATION_ID,)
            ).fetchone()[0]
            assert count == 0
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# checkpoint mutability: atomic replace, no immutability trigger.
# ---------------------------------------------------------------------------


def test_checkpoint_is_atomically_replaced_not_appended(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    first = service.write_checkpoint(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        status="pending",
        next_action_index=1,
        completed_action_count=0,
        total_action_count=3,
        non_cancelable=False,
    )
    assert first.outcome == "created"

    second = service.write_checkpoint(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        status="pending",
        next_action_index=2,
        completed_action_count=1,
        total_action_count=3,
        non_cancelable=False,
    )
    assert second.outcome == "created"

    conn = _raw_connect(tmp_foundry)
    try:
        rows = conn.execute(
            "SELECT next_action_index, completed_action_count FROM checkpoints"
            " WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchall()
        assert len(rows) == 1  # replaced, not appended
        assert rows[0]["next_action_index"] == 2
        assert rows[0]["completed_action_count"] == 1
    finally:
        conn.close()

    loaded = service.load_checkpoint(_OPERATION_ID)
    assert loaded["next_action_index"] == 2


def test_checkpoint_converged_forbids_next_action_index(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    with pytest.raises(ValueError):
        service.write_checkpoint(
            _OPERATION_ID,
            workspace_id=_WORKSPACE,
            status="converged",
            next_action_index=1,
            completed_action_count=3,
            total_action_count=3,
            non_cancelable=False,
        )


# ---------------------------------------------------------------------------
# Immutability: action_receipt/effect_receipt/terminal_receipt reject
# UPDATE/DELETE at the DB level (triggers), not merely application
# discipline -- revert-detection: comment out a trigger and these fail.
# ---------------------------------------------------------------------------


def test_action_receipts_table_rejects_raw_update(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE action_receipts SET status = 'failed' WHERE operation_id = ?",
                (_OPERATION_ID,),
            )
    finally:
        conn.close()


def test_effect_receipts_table_rejects_raw_delete(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    digest = _SHA("effect-immutable")
    service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=digest,
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM effect_receipts WHERE effect_digest = ?", (digest,))
    finally:
        conn.close()


def test_terminal_receipts_table_rejects_raw_update(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE terminal_receipts SET status = 'failed' WHERE operation_id = ?",
                (_OPERATION_ID,),
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Independent operations do not interfere with each other's reconciliation.
# ---------------------------------------------------------------------------


def test_two_operations_reconcile_independently(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, operation_id=_OPERATION_ID, action_id="act-0", action_index=0)
    _record_action(service, operation_id=_OTHER_OPERATION_ID, action_id="act-0", action_index=0)
    _record_action(service, operation_id=_OTHER_OPERATION_ID, action_id="act-1", action_index=1)

    outcome_a = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )
    outcome_b = service.finalize_terminal_receipt(
        _OTHER_OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=2,
        status="completed",
    )
    assert outcome_a.outcome == "created"
    assert outcome_b.outcome == "created"
    assert outcome_a.receipt["action_count_total"] == 1
    assert outcome_b.receipt["action_count_total"] == 2


# ---------------------------------------------------------------------------
# P2S-BLOCK-2 (fix half (b)): `resolve_resume_point`'s own `total_action_count`
# bound, exercised directly and in isolation from `run_actions`/
# `finalize_terminal_receipt`'s SEPARATE, already-covered EXTRA guard (see
# `test_operator_cancel_resume_service.py`'s
# `test_p2s_block2_extra_receipt_denies_run_actions_completed_branch`).
# `run_or_replay`/`resume_operation` always derive `start_index` FROM this
# method's own `next_action_index`, so for THOSE two callers an
# EXTRA-corrupted operation's `start_index` structurally ends up >=
# `total`, which coincidentally makes `run_actions`' own for-else
# "completed" branch (and its outcome-check) the thing that denies too --
# masking whether THIS method's bound fired at all. Calling
# `resolve_resume_point` directly, with no `run_actions` involved,
# isolates fix half (b) on its own.
# ---------------------------------------------------------------------------


def test_resolve_resume_point_denies_when_persisted_count_exceeds_declared_total(
    tmp_foundry: FoundryPaths,
) -> None:
    service = _service(tmp_foundry)
    for i in range(7):
        _record_action(service, action_id=f"act-{i}", action_index=i)

    # Without a declared total, contiguous 0..6 is a normal "ok" resume
    # point -- this method has no independent way to know 7 is too many.
    unbounded = service.resolve_resume_point(_OPERATION_ID)
    assert unbounded.outcome == "ok"
    assert unbounded.next_action_index == 7

    # WITH the operation's own declared total_action_count=5, 7 persisted
    # receipts is EXTRA -- denies, and does NOT report a resume point at
    # all (`next_action_index is None`), so no caller could compute a
    # `start_index` from it even by accident.
    bounded = service.resolve_resume_point(_OPERATION_ID, total_action_count=5)
    assert bounded.outcome == "denied"
    assert bounded.reason_code == "internal_error"
    assert bounded.next_action_index is None

    # Exactly matching the total (not EXTRA) still resolves normally.
    exact = service.resolve_resume_point(_OPERATION_ID, total_action_count=7)
    assert exact.outcome == "ok"
    assert exact.next_action_index == 7


# ---------------------------------------------------------------------------
# P2S-BLOCK-4: referential integrity -- a receipt for an `operation_id`
# with NO persisted `operations` manifest MUST deny, never silently
# accept. `_PHANTOM_OPERATION_ID` is deliberately NEVER seeded by the
# autouse `_seed_operations` fixture above -- every OTHER test in this
# module now runs against a REAL operation (that fixture's own point), so
# these are the ONLY tests in this file exercising the phantom-id path,
# and they do it against REAL persistence (a real, empty `operations`
# table query), never a fake/monkeypatched store.
# ---------------------------------------------------------------------------


def test_record_action_receipt_denies_for_phantom_operation_id(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    outcome = _record_action(
        service, operation_id=_PHANTOM_OPERATION_ID, action_id="act-0", action_index=0
    )
    assert outcome.outcome == "denied"
    # U2/REGATE-BLOCK-2: a phantom operation_id and a wrong-workspace one
    # are now INDISTINGUISHABLE -- both deny "not_found" (was
    # "internal_error" before this module gained a workspace-authorization
    # seam on its write paths).
    assert outcome.reason_code == "not_found"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?",
            (_PHANTOM_OPERATION_ID,),
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()

    # And the phantom id's resume point is UNCHANGED by the denied write --
    # it looks exactly like what it is: an operation that does not exist.
    resume_point = service.resolve_resume_point(_PHANTOM_OPERATION_ID)
    assert resume_point.outcome == "denied"
    assert resume_point.reason_code == "not_found"


def test_record_effect_receipt_denies_for_phantom_operation_id_via_mismatch_guard(
    tmp_foundry: FoundryPaths,
) -> None:
    """No matching `action_receipt` exists either. Before U2/REGATE-BLOCK-2
    added an explicit workspace-authorization check to this method, this
    exercised `record_effect_receipt`'s pre-existing MISMATCHED guard as
    the golden-path proof a phantom operation_id denies via AT LEAST one
    guard. The NEW workspace-authorization check now runs FIRST (a phantom
    operation_id has no derivable workspace at all), so this test now
    isolates THAT guard instead; the MISMATCHED guard's own isolation is
    `test_mismatched_effect_receipt_unknown_action_id_denies` above (a
    REAL operation, deliberately no matching action_receipt), and
    `test_record_effect_receipt_direct_referential_guard_fires_even_when_
    mismatch_guard_would_not` below still isolates the referential guard
    independent of MISMATCHED specifically."""

    service = _service(tmp_foundry)
    outcome = service.record_effect_receipt(
        _PHANTOM_OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-phantom-operation"),
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute("SELECT COUNT(*) FROM effect_receipts").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_record_effect_receipt_direct_referential_guard_fires_even_when_mismatch_guard_would_not(
    tmp_foundry: FoundryPaths,
) -> None:
    """Isolates P2S-BLOCK-4/U2's OWN direct workspace-authorization check
    in `record_effect_receipt`, independent of the (real, but DIFFERENT)
    MISMATCHED guard immediately below it. Plants an ORPHAN
    `action_receipt` for the phantom operation_id via raw SQL (real
    persistence -- a row genuinely present in the real table, just not
    reachable through this module's own governed write path) so the
    MISMATCHED guard's `action_receipts` existence check would, on its
    own, PASS -- isolating whether the referential-integrity-to-
    `operations` check fires on its own merits.
    """

    service = _service(tmp_foundry)
    conn = _raw_connect(tmp_foundry)
    try:
        conn.execute(
            "INSERT INTO action_receipts"
            " (operation_id, action_id, action_index, status, attempt_ref,"
            "  started_at, completed_at, reason_code, retryable, receipt_json, created_at)"
            " VALUES (?, 'act-orphan', 0, 'completed', 'attempt-x', ?, ?, NULL, NULL, '{}', ?)",
            (
                _PHANTOM_OPERATION_ID,
                "2026-07-29T00:00:00Z",
                "2026-07-29T00:00:00Z",
                "2026-07-29T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    outcome = service.record_effect_receipt(
        _PHANTOM_OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-orphan",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-phantom-operation-direct"),
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute("SELECT COUNT(*) FROM effect_receipts").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_write_checkpoint_denies_for_phantom_operation_id(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    outcome = service.write_checkpoint(
        _PHANTOM_OPERATION_ID,
        workspace_id=_WORKSPACE,
        status="pending",
        next_action_index=0,
        completed_action_count=0,
        total_action_count=3,
        non_cancelable=False,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"
    assert service.load_checkpoint(_PHANTOM_OPERATION_ID) is None


def test_finalize_terminal_receipt_denies_for_phantom_operation_id(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    outcome = service.finalize_terminal_receipt(
        _PHANTOM_OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=0,
        status="completed",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"
    assert service.load_terminal_receipt(_PHANTOM_OPERATION_ID) is None


def test_gap_receipt_denies_at_write_time_operation_remains_resumable(
    tmp_foundry: FoundryPaths,
) -> None:
    """U5/REGATE-BLOCK-3: an earlier revision of this module ACCEPTED a
    gap receipt (e.g. index 3 with 0-2 absent) on a real, healthy
    operation, and -- because `action_receipts` is immutable (no
    UPDATE/DELETE path, enforced by DB trigger) -- that single out-of-turn
    write PERMANENTLY and IRREPARABLY bricked the operation:
    `resolve_resume_point` denied forever, and both attempted repairs
    (`DELETE`, `UPDATE`) raised `sqlite3.IntegrityError`.

    A previous fix wave shipped a test named
    `test_gap_receipt_on_real_operation_is_permanently_unrecoverable` that
    ASSERTED this bricked state was the CORRECT, expected outcome --
    pinning a bug as a feature (mandatory checklist item 3: never do this).
    This test REPLACES it, in the opposite direction: the actual fix is to
    reject the gap AT WRITE TIME, before a single row is written, so the
    unrecoverable state can never be created at all -- proven here by the
    operation staying fully healthy and resumable from index 0 afterward.
    """

    service = _service(tmp_foundry)

    outcome = _record_action(service, action_id="act-3", action_index=3)
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()

    # The operation is UNAFFECTED -- still cleanly resumable from index 0,
    # never bricked. This is the actual proof of the fix: the denied write
    # left nothing behind for `resolve_resume_point`/reconciliation to
    # ever discover as corrupt.
    resume_point = service.resolve_resume_point(_OPERATION_ID)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 0

    # A normal, correctly-contiguous write for the SAME operation still
    # succeeds -- the guard rejects only the out-of-order index, never the
    # operation itself.
    normal = _record_action(service, action_id="act-0", action_index=0)
    assert normal.outcome == "created"


# ---------------------------------------------------------------------------
# U2/REGATE-BLOCK-2: `record_action_receipt`/`record_effect_receipt` must
# be workspace-AUTHORIZED, not merely accepted, for a REAL operation that
# exists in a DIFFERENT workspace than the caller-supplied `workspace_id`
# -- distinct from the phantom-operation-id tests above (which prove
# ABSENCE denies; these prove a wrong-but-real workspace also denies, and
# indistinguishably from absence).
# ---------------------------------------------------------------------------


def test_record_action_receipt_denies_wrong_workspace_not_phantom(
    tmp_foundry: FoundryPaths,
) -> None:
    """`_OPERATION_ID` is real and seeded into `_WORKSPACE` -- a caller
    asserting a DIFFERENT, wrong workspace_id must be refused, exactly as
    if the operation did not exist at all."""

    service = _service(tmp_foundry)
    outcome = _record_action(
        service, workspace_id="ws-attacker", action_id="act-0", action_index=0
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()

    # The legitimate owner, presenting the REAL workspace_id, still
    # succeeds -- the fix denies the WRONG workspace, not the operation.
    legit = _record_action(service, action_id="act-0", action_index=0)
    assert legit.outcome == "created"


def test_record_effect_receipt_denies_wrong_workspace_not_phantom(
    tmp_foundry: FoundryPaths,
) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    outcome = service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id="ws-attacker",
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-wrong-workspace"),
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute("SELECT COUNT(*) FROM effect_receipts").fetchone()[0]
        assert count == 0
    finally:
        conn.close()

    legit = service.record_effect_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-wrong-workspace-legit"),
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:07Z",
    )
    assert legit.outcome == "created"


# ---------------------------------------------------------------------------
# U1/REGATE-BLOCK-2 + P2S-BLOCK-3: identity/workspace seam.
#
# Write side: `write_checkpoint`/`finalize_terminal_receipt` AUTHORIZE
# `workspace_id` against the real `operations` row and DENY (never
# silently correct) on disagreement -- so a wrong/forged value can never
# be attributed OR persisted into these otherwise-immutable rows. An
# earlier revision of this module DERIVED the real value and used it
# anyway on a mismatch (logging only a warning) -- that is attribution,
# not authorization, and the two tests immediately below used to assert
# exactly that vulnerable "creates despite the forged workspace_id, but
# silently substitutes the truth" behavior as correct (mandatory
# checklist item 3: never pin unsafe behavior with a test). They are
# INVERTED here to assert the fix: a forged `workspace_id` now denies,
# with zero effect, full stop.
#
# Read side: `load_terminal_receipt`/`load_checkpoint`/`resolve_resume_point`
# accept `identity: AuthIdentity | None`; a wrong-workspace `identity`
# returns the SAME shape as "does not exist" (`None` for the two
# `Optional`-returning reads, `("denied", "not_found", None)` for
# `resolve_resume_point`), no derived detail leaked.
# ---------------------------------------------------------------------------


def test_write_checkpoint_denies_forged_workspace_not_derives(
    tmp_foundry: FoundryPaths,
) -> None:
    """`_OPERATION_ID` is seeded (by the autouse fixture) into `_WORKSPACE`
    -- a caller asserting a DIFFERENT workspace_id is the caller's OWN
    claimed authority to write this checkpoint, and a wrong one must be
    REFUSED, not silently corrected. (Inverted from this test's own former
    name/behavior -- `..._derives_workspace_from_operation_not_caller` --
    which asserted the pre-fix vulnerability: the write succeeded anyway,
    just with the truth quietly substituted for storage. REGATE-BLOCK-2's
    empirical attack showed exactly why that is unsafe: it let a caller
    holding only an `operation_id` -- not a secret -- attribute writes
    into ANOTHER workspace's checkpoint at will.)"""

    service = _service(tmp_foundry)
    outcome = service.write_checkpoint(
        _OPERATION_ID,
        workspace_id="ws-attacker-forged",
        status="pending",
        next_action_index=1,
        completed_action_count=0,
        total_action_count=3,
        non_cancelable=False,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"
    assert outcome.receipt is None

    # ZERO effect: no checkpoint row at all -- not one attributed to the
    # forger, not one (silently corrected) attributed to the real owner.
    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()

    # The legitimate owner, presenting its OWN real workspace_id, still
    # succeeds normally -- the fix denies the FORGED case, not writing in
    # general.
    legit = service.write_checkpoint(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        status="pending",
        next_action_index=1,
        completed_action_count=0,
        total_action_count=3,
        non_cancelable=False,
    )
    assert legit.outcome == "created"
    assert legit.receipt["workspace_id"] == _WORKSPACE


def test_finalize_terminal_receipt_denies_forged_workspace_not_derives(
    tmp_foundry: FoundryPaths,
) -> None:
    """Inverted from `..._derives_workspace_from_operation_not_caller` --
    see the section header and `test_write_checkpoint_denies_forged_
    workspace_not_derives` above for the full rationale. This is the
    EXACT X2 attack REGATE-BLOCK-2 demonstrated: a forged `workspace_id`
    on `finalize_terminal_receipt` used to plant a PERMANENT, IMMUTABLE
    terminal receipt that the operation's own later, legitimate,
    successful run would then read back as truth."""

    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id="ws-attacker-forged",
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "not_found"
    assert outcome.receipt is None

    # ZERO effect: no terminal_receipts row at all, and the operation is
    # still NOT terminal -- the legitimate owner can still finalize it for
    # real afterward (proves the forged attempt left no trace to collide
    # with, not merely that the row was attributed correctly).
    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM terminal_receipts WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()
    assert service.load_terminal_receipt(_OPERATION_ID) is None

    legit = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )
    assert legit.outcome == "created"
    assert legit.receipt["workspace_id"] == _WORKSPACE


def test_load_terminal_receipt_wrong_workspace_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths,
) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )

    genuinely_missing = service.load_terminal_receipt(_PHANTOM_OPERATION_ID, identity=_IDENTITY)
    scope_denied = service.load_terminal_receipt(_OPERATION_ID, identity=_IDENTITY_OTHER_WORKSPACE)
    assert genuinely_missing is None
    assert scope_denied is None

    # Correct-workspace identity still sees it.
    same_workspace = service.load_terminal_receipt(_OPERATION_ID, identity=_IDENTITY)
    assert same_workspace is not None
    assert same_workspace["operation_id"] == _OPERATION_ID

    # identity=None (default) performs no scoping.
    unscoped = service.load_terminal_receipt(_OPERATION_ID)
    assert unscoped is not None


def test_load_checkpoint_wrong_workspace_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths,
) -> None:
    service = _service(tmp_foundry)
    service.write_checkpoint(
        _OPERATION_ID,
        workspace_id=_WORKSPACE,
        status="pending",
        next_action_index=1,
        completed_action_count=0,
        total_action_count=3,
        non_cancelable=False,
    )

    genuinely_missing = service.load_checkpoint(_PHANTOM_OPERATION_ID, identity=_IDENTITY)
    scope_denied = service.load_checkpoint(_OPERATION_ID, identity=_IDENTITY_OTHER_WORKSPACE)
    assert genuinely_missing is None
    assert scope_denied is None

    same_workspace = service.load_checkpoint(_OPERATION_ID, identity=_IDENTITY)
    assert same_workspace is not None


def test_resolve_resume_point_wrong_workspace_denies_not_found(tmp_foundry: FoundryPaths) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    scope_denied = service.resolve_resume_point(_OPERATION_ID, identity=_IDENTITY_OTHER_WORKSPACE)
    assert scope_denied.outcome == "denied"
    assert scope_denied.reason_code == "not_found"
    assert scope_denied.next_action_index is None

    # Indistinguishable from a genuinely missing operation_id.
    genuinely_missing = service.resolve_resume_point(_PHANTOM_OPERATION_ID, identity=_IDENTITY)
    assert genuinely_missing.outcome == "denied"
    assert genuinely_missing.reason_code == "not_found"

    same_workspace = service.resolve_resume_point(_OPERATION_ID, identity=_IDENTITY)
    assert same_workspace.outcome == "ok"
    assert same_workspace.next_action_index == 1
