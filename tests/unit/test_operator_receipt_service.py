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
    assert outcome.reason_code == "internal_error"

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
    """No matching `action_receipt` exists either, so this exercises
    `record_effect_receipt`'s pre-existing MISMATCHED guard (real,
    unrelated to P2S-BLOCK-4) -- kept as the golden-path proof that a
    phantom operation_id denies via AT LEAST one guard.
    `test_record_effect_receipt_direct_referential_guard_fires_even_when_
    mismatch_guard_would_not` below isolates BLOCK-4's OWN direct check."""

    service = _service(tmp_foundry)
    outcome = service.record_effect_receipt(
        _PHANTOM_OPERATION_ID,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-phantom-operation"),
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


def test_record_effect_receipt_direct_referential_guard_fires_even_when_mismatch_guard_would_not(
    tmp_foundry: FoundryPaths,
) -> None:
    """Isolates P2S-BLOCK-4's OWN direct `_derive_workspace_id` check in
    `record_effect_receipt`, independent of the (real, but DIFFERENT)
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
        action_id="act-orphan",
        effect_kind="source_card_created",
        effect_digest=_SHA("effect-phantom-operation-direct"),
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
    assert outcome.reason_code == "internal_error"
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
    assert outcome.reason_code == "internal_error"
    assert service.load_terminal_receipt(_PHANTOM_OPERATION_ID) is None


def test_gap_receipt_on_real_operation_is_permanently_unrecoverable(
    tmp_foundry: FoundryPaths,
) -> None:
    """Reproduces the P2 security gate's exact empirical "brick" repro on
    a REAL, seeded operation (`_OPERATION_ID`, a real 4-action operation
    per this test's own intent): a single out-of-turn receipt at index 3
    (skipping 0-2) denies `resolve_resume_point` forever, and the
    immutability triggers (already covered elsewhere for the golden path)
    confirm there is genuinely no repair path -- this is why BLOCK-4's
    referential-integrity guard on `record_action_receipt` matters even
    though this specific scenario is a GAP, not a phantom-operation-id: it
    documents the severity BLOCK-4 exists to prevent for that other case
    (a phantom id's receipts are equally unrecoverable once written, since
    `action_receipts` has no UPDATE/DELETE path at all).
    """

    service = _service(tmp_foundry)
    outcome = _record_action(service, action_id="act-3", action_index=3)
    assert outcome.outcome == "created"

    resume_point = service.resolve_resume_point(_OPERATION_ID)
    assert resume_point.outcome == "denied"
    assert resume_point.reason_code == "internal_error"

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "DELETE FROM action_receipts WHERE operation_id = ? AND action_index = 3",
                (_OPERATION_ID,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE action_receipts SET action_index = 0"
                " WHERE operation_id = ? AND action_index = 3",
                (_OPERATION_ID,),
            )
    finally:
        conn.close()

    # Still denied after the failed repair attempts -- genuinely permanent.
    assert service.resolve_resume_point(_OPERATION_ID).outcome == "denied"


# ---------------------------------------------------------------------------
# P2S-BLOCK-3: identity/workspace seam.
#
# Write side: `write_checkpoint`/`finalize_terminal_receipt` DERIVE
# `workspace_id` from the real `operations` row rather than trusting the
# caller-supplied parameter (so a wrong/forged value can never be
# persisted into these otherwise-immutable rows).
#
# Read side: `load_terminal_receipt`/`load_checkpoint`/`resolve_resume_point`
# accept `identity: AuthIdentity | None`; a wrong-workspace `identity`
# returns the SAME shape as "does not exist" (`None` for the two
# `Optional`-returning reads, `("denied", "not_found", None)` for
# `resolve_resume_point`), no derived detail leaked.
# ---------------------------------------------------------------------------


def test_write_checkpoint_derives_workspace_from_operation_not_caller(
    tmp_foundry: FoundryPaths,
) -> None:
    """`_OPERATION_ID` is seeded (by the autouse fixture) into `_WORKSPACE`
    -- a caller asserting a DIFFERENT workspace_id must not be able to
    misattribute the persisted checkpoint row."""

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
    assert outcome.outcome == "created"
    # The RETURNED receipt reflects the DERIVED (real) workspace, not the
    # caller's forged one.
    assert outcome.receipt["workspace_id"] == _WORKSPACE

    conn = _raw_connect(tmp_foundry)
    try:
        row = conn.execute(
            "SELECT workspace_id FROM checkpoints WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchone()
        assert row["workspace_id"] == _WORKSPACE
    finally:
        conn.close()


def test_finalize_terminal_receipt_derives_workspace_from_operation_not_caller(
    tmp_foundry: FoundryPaths,
) -> None:
    service = _service(tmp_foundry)
    _record_action(service, action_id="act-0", action_index=0)

    outcome = service.finalize_terminal_receipt(
        _OPERATION_ID,
        workspace_id="ws-attacker-forged",
        operation_kind="run.plan",
        expected_action_count=1,
        status="completed",
    )
    assert outcome.outcome == "created"
    assert outcome.receipt["workspace_id"] == _WORKSPACE

    conn = _raw_connect(tmp_foundry)
    try:
        row = conn.execute(
            "SELECT workspace_id FROM terminal_receipts WHERE operation_id = ?",
            (_OPERATION_ID,),
        ).fetchone()
        assert row["workspace_id"] == _WORKSPACE
    finally:
        conn.close()


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
