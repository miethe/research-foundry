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

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.operator_receipt_service import (
    OperatorReceiptService,
    ReceiptOutcome,
    _validate_action_counts,
)

_OPERATION_ID = "opm_" + "a" * 64
_OTHER_OPERATION_ID = "opm_" + "b" * 64
_WORKSPACE = "ws-mine"

_SHA = lambda tag: __import__("hashlib").sha256(tag.encode()).hexdigest()  # noqa: E731


def _service(paths: FoundryPaths) -> OperatorReceiptService:
    return OperatorReceiptService(paths)


def _raw_connect(paths: FoundryPaths) -> sqlite3.Connection:
    conn = sqlite3.connect(str(paths.operator_operations_db))
    conn.row_factory = sqlite3.Row
    return conn


def _record_action(
    service: OperatorReceiptService,
    *,
    operation_id: str = _OPERATION_ID,
    action_id: str,
    action_index: int,
    status: str = "completed",
    reason_code: str | None = None,
) -> ReceiptOutcome:
    return service.record_action_receipt(
        operation_id,
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
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=digest,
        effect_ref="source_card:abc123",
        generated_at="2026-07-29T00:00:06Z",
    )
    assert first.outcome == "created"

    second = service.record_effect_receipt(
        _OPERATION_ID,
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
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)
    _record_action(service, action_id="act-1", action_index=1)
    # Skip index 2 entirely; jump to 3 -- exactly 3 rows persisted (matches
    # expected_action_count) but NOT the contiguous 0..2 sequence.
    _record_action(service, action_id="act-3", action_index=3)

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
