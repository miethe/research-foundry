"""Unit tests for :mod:`research_foundry.services.operator_attempt_adapter`
(research-foundry-operator-mcp-v1 P2, OPM-2.2).

Two acceptance criteria drive this file:

1. **Legacy AgentJob reads still pass** -- an ``AgentJob`` created directly
   via ``AgentJobService.create_job`` (never through
   ``OperatorAttemptAdapter.create_attempt``, so it has no row in the
   adapter's own ``attempts`` link table) must still load cleanly through
   the adapter, with ``operation_id is None`` rather than an error.
2. **Wrong-workspace attempts are indistinguishable from missing** -- mirrors
   ``AgentJobService.load_job``'s own guarantee (proven in
   ``test_agent_job_service.py``) through every adapter method that gates on
   identity.

``accept_job`` unreachability is proven structurally (no such name anywhere
in the adapter's public surface) rather than behaviourally, since there is
nothing to "call and observe" for an absent method.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_operation_service as ops_module
from research_foundry.services.agent_job_schemas import AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.operator_attempt_adapter import (
    AttemptRecord,
    AttemptStoreUnavailableError,
    OperatorAttemptAdapter,
)

_MINIMAL_POLICY_SNAPSHOT = {"allowed_tools": ["search"], "data_scopes": []}

_WS_MINE = AuthIdentity("u1", "ws-mine", ("owner",))
_WS_OTHER = AuthIdentity("u2", "ws-other", ("owner",))

_OPERATION_ID = "opm_" + "a" * 64


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same convention as ``test_agent_job_service.py``: monkeypatch the
    REAL config resolver, never the service's own private helper."""

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


def _adapter(paths: FoundryPaths) -> OperatorAttemptAdapter:
    return OperatorAttemptAdapter(paths)


def _create_attempt(
    adapter: OperatorAttemptAdapter,
    *,
    operation_id: str = _OPERATION_ID,
    workspace_id: str | None = "ws-mine",
    identity: AuthIdentity | None = None,
) -> AttemptRecord:
    return adapter.create_attempt(
        operation_id,
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        dict(_MINIMAL_POLICY_SNAPSHOT),
        project_id="test-project",
        workspace_id=workspace_id,
        identity=identity,
    )


# ---------------------------------------------------------------------------
# accept_job unreachability
# ---------------------------------------------------------------------------


def test_accept_job_not_present_on_adapter_public_surface() -> None:
    public_names = {name for name in dir(OperatorAttemptAdapter) if not name.startswith("_")}
    assert "accept_job" not in public_names
    assert not any("accept" in name for name in public_names)


def test_adapter_does_not_expose_the_wrapped_job_service(tmp_foundry: FoundryPaths) -> None:
    adapter = _adapter(tmp_foundry)
    public_names = {name for name in dir(adapter) if not name.startswith("_")}
    # No public attribute/property hands back the raw AgentJobService, which
    # would let a caller reach ``.accept_job`` around the adapter entirely.
    for name in public_names:
        value = getattr(adapter, name)
        assert not isinstance(value, AgentJobService)


def test_adapter_public_surface_never_calls_accept_job(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Call-spy supplement to the two structural tests above (A2, OPM Karen
    finding). A substring name-ban plus ``dir()`` scan only proves no method
    literally named "accept*" exists on the adapter -- it would NOT catch a
    differently-named method that reaches ``accept_job`` internally. This
    proves the module docstring's actual, stronger claim ("never calls
    ``self._jobs.accept_job``") by monkeypatching the wrapped service's
    ``accept_job`` with a call-counting spy and exercising the adapter's
    entire public surface (every method exercised at least once, including
    both writes and the create/list-for-operation paths), then asserting the
    spy was never invoked. Follows the existing spy pattern in
    ``test_workspace_isolation_enforcement.py::TestMutationDenySpies
    ::test_accept_job_cross_workspace_never_calls_accept_job``.
    """

    calls = {"n": 0}
    original = AgentJobService.accept_job

    def spy(self: AgentJobService, job_id: str, **kwargs: Any) -> Any:
        calls["n"] += 1
        return original(self, job_id, **kwargs)

    monkeypatch.setattr(AgentJobService, "accept_job", spy)

    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter, identity=_WS_MINE)
    attempt_id = record.attempt_id

    adapter.load_attempt(attempt_id, identity=_WS_MINE)
    adapter.load_events(attempt_id, identity=_WS_MINE)
    adapter.persist_event(attempt_id, {"kind": "probe"}, identity=_WS_MINE)
    adapter.list_artifacts(attempt_id, identity=_WS_MINE)
    adapter.persist_artifact(
        attempt_id, {"artifact_id": "spy-artifact", "artifact_kind": "claim"}, identity=_WS_MINE
    )
    adapter.get_status(attempt_id, identity=_WS_MINE)
    adapter.update_status(attempt_id, AgentJobStatus.running, identity=_WS_MINE)
    adapter.poll_attempt(attempt_id, identity=_WS_MINE)
    adapter.list_attempts_for_operation(_OPERATION_ID, identity=_WS_MINE)
    adapter.terminate_attempt(attempt_id, identity=_WS_MINE)
    adapter.cleanup_attempt(attempt_id, identity=_WS_MINE)

    assert calls["n"] == 0


def test_accept_job_spy_sanity_check_fires_on_direct_service_call(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves the spy in the test above is actually live -- i.e. that a
    ``calls["n"] == 0`` result there is meaningful evidence and not a
    tautology of a spy that never fires. Calling ``AgentJobService
    .accept_job`` directly (bypassing the adapter entirely, exactly as the
    module docstring's third guarantee forbids the adapter itself from
    doing) increments the counter. The freshly-created job is in the
    default ``pending`` status, not ``waiting_for_approval``/``completed``,
    so the real ``accept_job`` raises ``ValueError`` -- irrelevant here: the
    spy increments BEFORE delegating to the original, so the counter proves
    the call reached the spy regardless of what the wrapped call does next.
    """

    calls = {"n": 0}
    original = AgentJobService.accept_job

    def spy(self: AgentJobService, job_id: str, **kwargs: Any) -> Any:
        calls["n"] += 1
        return original(self, job_id, **kwargs)

    monkeypatch.setattr(AgentJobService, "accept_job", spy)

    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter, identity=_WS_MINE)

    jobs = AgentJobService(tmp_foundry)
    with pytest.raises(ValueError):
        jobs.accept_job(record.attempt_id)

    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# create_attempt: durable bidirectional link
# ---------------------------------------------------------------------------


def test_create_attempt_links_operation_and_attempt_bidirectionally(
    tmp_foundry: FoundryPaths,
) -> None:
    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter)

    assert record.operation_id == _OPERATION_ID

    # attempt -> operation
    loaded = adapter.load_attempt(record.attempt_id)
    assert loaded.operation_id == _OPERATION_ID
    assert loaded.job.agent_job_id == record.attempt_id

    # operation -> attempts
    for_op = adapter.list_attempts_for_operation(_OPERATION_ID)
    assert [a.attempt_id for a in for_op] == [record.attempt_id]


def test_link_row_is_really_persisted_in_the_operator_operations_db(
    tmp_foundry: FoundryPaths,
) -> None:
    """Mutation-resistant proof: query the on-disk sqlite file directly,
    never through the adapter's own read path."""

    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter)

    conn = sqlite3.connect(str(tmp_foundry.operator_operations_db))
    try:
        row = conn.execute(
            "SELECT operation_id, workspace_id FROM attempts WHERE attempt_id = ?",
            (record.attempt_id,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == _OPERATION_ID
    assert row[1] == "ws-mine"


def test_create_attempt_rejects_empty_operation_id(tmp_foundry: FoundryPaths) -> None:
    adapter = _adapter(tmp_foundry)
    with pytest.raises(ValueError):
        _create_attempt(adapter, operation_id="")


def test_create_attempt_identity_overrides_client_workspace_id(
    tmp_foundry: FoundryPaths,
) -> None:
    """DF-004 override must survive unchanged through the adapter."""

    adapter = _adapter(tmp_foundry)
    record = _create_attempt(
        adapter, workspace_id="ws-spoofed", identity=_WS_MINE
    )
    assert record.job.workspace_id == "ws-mine"
    assert record.job.workspace_id != "ws-spoofed"


# ---------------------------------------------------------------------------
# Legacy AgentJob reads still pass
# ---------------------------------------------------------------------------


def test_legacy_agent_job_created_outside_adapter_loads_with_no_operation_link(
    tmp_foundry: FoundryPaths,
) -> None:
    jobs = AgentJobService(tmp_foundry)
    job = jobs.create_job(
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        dict(_MINIMAL_POLICY_SNAPSHOT),
        project_id="test-project",
        workspace_id="ws-mine",
    )

    adapter = _adapter(tmp_foundry)
    record = adapter.load_attempt(job.agent_job_id)

    assert record.job.agent_job_id == job.agent_job_id
    assert record.operation_id is None


def test_legacy_agent_job_events_and_artifacts_still_readable_through_adapter(
    tmp_foundry: FoundryPaths,
) -> None:
    jobs = AgentJobService(tmp_foundry)
    job = jobs.create_job(
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        dict(_MINIMAL_POLICY_SNAPSHOT),
        project_id="test-project",
        workspace_id="ws-mine",
    )
    jobs.persist_event(job.agent_job_id, {"kind": "started"})
    jobs.persist_artifact(job.agent_job_id, {"artifact_id": "a1", "artifact_kind": "claim"})

    adapter = _adapter(tmp_foundry)
    events = adapter.load_events(job.agent_job_id)
    artifacts = adapter.list_artifacts(job.agent_job_id)

    assert events == [{"kind": "started"}]
    assert len(artifacts) == 1
    assert artifacts[0]["artifact_id"] == "a1"


# ---------------------------------------------------------------------------
# Wrong-workspace attempts are indistinguishable from missing
# ---------------------------------------------------------------------------


def test_load_attempt_wrong_workspace_same_exception_type_and_message_as_missing(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves indistinguishability for the SAME attempt_id: the message
    template embeds the queried id either way (that alone is not a leak --
    the caller already knows the id it asked for), so the only way to prove
    "wrong-workspace" and "missing" are truly indistinguishable is to
    compare the error raised for one id BEFORE vs AFTER it stops existing,
    never two different ids (which would trivially differ by id alone)."""

    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter, identity=_WS_MINE)

    _force_isolation_active(monkeypatch)

    # Sanity: the owning identity can still load it.
    assert adapter.load_attempt(record.attempt_id, identity=_WS_MINE).attempt_id == record.attempt_id

    with pytest.raises(KeyError) as wrong_ws_exc:
        adapter.load_attempt(record.attempt_id, identity=_WS_OTHER)

    # Now make the SAME attempt_id genuinely missing (delete its job.json)
    # and re-query with the SAME wrong-workspace identity.
    job_file = tmp_foundry.agent_job_dir(record.attempt_id) / "job.json"
    job_file.unlink()

    with pytest.raises(KeyError) as missing_exc:
        adapter.load_attempt(record.attempt_id, identity=_WS_OTHER)

    assert type(wrong_ws_exc.value) is type(missing_exc.value)
    assert str(wrong_ws_exc.value) == str(missing_exc.value)


def test_load_attempt_wrong_workspace_denial_logged_missing_is_not(
    tmp_foundry: FoundryPaths,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter, identity=_WS_MINE)

    _force_isolation_active(monkeypatch)

    caplog.set_level("INFO", logger="research_foundry.services.agent_job_service")
    caplog.clear()
    with pytest.raises(KeyError):
        adapter.load_attempt(record.attempt_id, identity=_WS_OTHER)
    assert any(
        "workspace_scope_enforced_denial" in r.getMessage() for r in caplog.records
    )

    caplog.clear()
    with pytest.raises(KeyError):
        adapter.load_attempt("job_does_not_exist_at_all", identity=_WS_OTHER)
    assert not any(
        "workspace_scope_enforced_denial" in r.getMessage() for r in caplog.records
    )


@pytest.mark.parametrize(
    "call",
    [
        lambda adapter, attempt_id, identity: adapter.load_events(attempt_id, identity=identity),
        lambda adapter, attempt_id, identity: adapter.persist_event(
            attempt_id, {"kind": "probe"}, identity=identity
        ),
        lambda adapter, attempt_id, identity: adapter.list_artifacts(attempt_id, identity=identity),
        lambda adapter, attempt_id, identity: adapter.persist_artifact(
            attempt_id, {"artifact_id": "probe-artifact", "artifact_kind": "claim"}, identity=identity
        ),
        lambda adapter, attempt_id, identity: adapter.get_status(attempt_id, identity=identity),
        lambda adapter, attempt_id, identity: adapter.poll_attempt(attempt_id, identity=identity),
        lambda adapter, attempt_id, identity: adapter.terminate_attempt(attempt_id, identity=identity),
        lambda adapter, attempt_id, identity: adapter.cleanup_attempt(attempt_id, identity=identity),
        lambda adapter, attempt_id, identity: adapter.update_status(
            attempt_id, AgentJobStatus.running, identity=identity
        ),
    ],
    ids=[
        "load_events",
        "persist_event",
        "list_artifacts",
        "persist_artifact",
        "get_status",
        "poll_attempt",
        "terminate_attempt",
        "cleanup_attempt",
        "update_status",
    ],
)
def test_every_lifecycle_wrapper_denies_wrong_workspace_when_isolation_active(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, call
) -> None:
    """Covers all 9 identity-gated lifecycle wrappers on the adapter (every
    public method that operates on an EXISTING attempt via a bare
    ``self._jobs.load_job(attempt_id, identity=identity)`` gate before
    delegating). ``create_attempt`` (create path, DF-004 identity-override
    tested separately), ``load_attempt`` (its own dedicated
    indistinguishable-from-missing tests above), and
    ``list_attempts_for_operation`` (filters rather than raises, its own
    dedicated test below) are intentionally not parametrized here -- their
    gating is proven by name-matched tests elsewhere in this file, not
    omitted. ``persist_event``/``persist_artifact`` were the two ORIGINAL
    gaps in this parametrize list: the gate existed in the adapter source
    all along, but nothing exercised it, so a regression removing either
    gate would previously pass this entire suite (see the per-wrapper
    mutation verification performed for OPM Karen finding A1)."""

    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter, identity=_WS_MINE)

    _force_isolation_active(monkeypatch)

    with pytest.raises(KeyError):
        call(adapter, record.attempt_id, _WS_OTHER)

    # The owning identity is unaffected.
    call(adapter, record.attempt_id, _WS_MINE)


def test_list_attempts_for_operation_excludes_wrong_workspace_when_isolation_active(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter, identity=_WS_MINE)

    _force_isolation_active(monkeypatch)

    assert [a.attempt_id for a in adapter.list_attempts_for_operation(_OPERATION_ID, identity=_WS_MINE)] == [
        record.attempt_id
    ]
    assert adapter.list_attempts_for_operation(_OPERATION_ID, identity=_WS_OTHER) == []


# ---------------------------------------------------------------------------
# status transition + poll/terminate/cleanup delegate to the real service
# ---------------------------------------------------------------------------


def test_update_status_transitions_and_preserves_operation_link(
    tmp_foundry: FoundryPaths,
) -> None:
    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter)

    updated = adapter.update_status(record.attempt_id, AgentJobStatus.running)
    assert updated.job.status == AgentJobStatus.running
    assert updated.operation_id == _OPERATION_ID
    assert adapter.get_status(record.attempt_id) == AgentJobStatus.running


def test_poll_attempt_returns_none_for_unspawned_job(tmp_foundry: FoundryPaths) -> None:
    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter)
    assert adapter.poll_attempt(record.attempt_id) is None


def test_terminate_and_cleanup_attempt_are_idempotent_noops_for_unspawned_job(
    tmp_foundry: FoundryPaths,
) -> None:
    adapter = _adapter(tmp_foundry)
    record = _create_attempt(adapter)
    # Neither raises for a job with no live subprocess registry entry.
    adapter.terminate_attempt(record.attempt_id)
    adapter.cleanup_attempt(record.attempt_id)



# ---------------------------------------------------------------------------
# K3-BLOCK-1 / K4-BLOCK-1 / K4-NB-1 sibling instance in THIS module: this
# module's own three private DML/read helpers (`_record_attempt_link`,
# `_lookup_operation_id`, `_list_attempt_ids_for_operation`) had ZERO
# `except sqlite3` handlers -- a contending writer raised a raw
# `sqlite3.OperationalError` straight out of this module's boundary. Every
# test below proves a bounded `AttemptStoreUnavailableError`, never the raw
# driver exception, using REAL competing sqlite locks (never a
# fake/monkeypatched store), mirroring
# `test_operator_cancel_resume_service.py`'s and
# `test_operator_receipt_service.py`'s own K4-BLOCK-1/K4-NB-1 techniques.
# ---------------------------------------------------------------------------


def _block_operations_db(paths: FoundryPaths) -> sqlite3.Connection:
    """Hold a REAL competing writer lock on the operations DB. Caller must
    ROLLBACK + close. Identical technique to
    `test_operator_cancel_resume_service._block_operations_db` /
    `test_operator_receipt_service._block_operations_db` (K4-BLOCK-1 /
    K4-NB-1)."""

    paths.operator_operations_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(paths.operator_operations_db), isolation_level=None)
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("CREATE TABLE IF NOT EXISTS _attempt_adapter_blocker (x INTEGER)")
    return conn


def _assert_bounded_not_raw(excinfo: pytest.ExceptionInfo, paths: FoundryPaths) -> None:
    """Bounded per `schemas/operator_mcp_error.schema.yaml` (AC OPM-7): no
    driver text, no SQL, no path. Mirrors the sibling assertion helpers in
    `test_operator_cancel_resume_service.py` / `test_operator_receipt_service.py`."""

    message = str(excinfo.value)
    assert "database is locked" not in message
    assert "SELECT" not in message
    assert "INSERT" not in message
    assert str(paths.operator_operations_db) not in message
    assert not isinstance(excinfo.value, sqlite3.OperationalError)


def test_list_attempt_ids_for_operation_raises_bounded_error_not_raw_driver_exception_when_locked(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_list_attempt_ids_for_operation`'s own guard, reached via the public
    `list_attempts_for_operation` -- the first (and only) db interaction in
    that method, so a cold store + real competing lock exercises it
    directly, no confound from any other guard."""

    adapter = _adapter(tmp_foundry)

    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(tmp_foundry)
    try:
        with pytest.raises(AttemptStoreUnavailableError) as excinfo:
            adapter.list_attempts_for_operation(_OPERATION_ID)
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    _assert_bounded_not_raw(excinfo, tmp_foundry)


def test_lookup_operation_id_raises_bounded_error_not_raw_driver_exception_when_locked(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_lookup_operation_id`'s own guard, reached via the public
    `load_attempt`. A REAL `AgentJob` is created first, directly via
    `AgentJobService.create_job` (bypassing this adapter's own
    `create_attempt` -- so `attempts` has no link row for it and the
    operations db stays genuinely untouched/cold), so `load_job` succeeds
    (file-based, no sqlite involved) and execution reaches
    `_lookup_operation_id` -- the ONLY sqlite interaction `load_attempt`
    makes -- which then hits the real competing lock."""

    adapter = _adapter(tmp_foundry)
    jobs = AgentJobService(tmp_foundry)
    job = jobs.create_job(
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        dict(_MINIMAL_POLICY_SNAPSHOT),
        project_id="test-project",
        workspace_id="ws-mine",
    )

    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(tmp_foundry)
    try:
        with pytest.raises(AttemptStoreUnavailableError) as excinfo:
            adapter.load_attempt(job.agent_job_id)
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    _assert_bounded_not_raw(excinfo, tmp_foundry)


def test_record_attempt_link_acquisition_raises_bounded_error_not_raw_driver_exception_when_locked(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_record_attempt_link`'s own acquisition-half guard (K3-BLOCK-1 half
    1 analogue), reached via the public `create_attempt`.

    Schema is warmed FIRST via an unrelated, successful `create_attempt`
    call -- both so the blocker connection below can open an existing file,
    and (the real reason) so `create_attempt`'s OWN cap-check
    (`_list_attempt_ids_for_operation`, a plain SELECT against a WARM
    schema) succeeds against the blocker's held RESERVED lock rather than
    tripping ITS OWN guard first -- which would prove the wrong guard fired.
    This isolates `_record_attempt_link`'s `BEGIN IMMEDIATE` (which DOES
    conflict with an already-held RESERVED lock -- SQLite allows only one
    RESERVED holder at a time) as the thing under test.
    """

    adapter = _adapter(tmp_foundry)
    _create_attempt(adapter, operation_id="opm_" + "b" * 64)

    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(tmp_foundry)
    try:
        with pytest.raises(AttemptStoreUnavailableError) as excinfo:
            _create_attempt(adapter, operation_id="opm_" + "c" * 64)
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    _assert_bounded_not_raw(excinfo, tmp_foundry)


def test_record_attempt_link_promotion_raises_bounded_error_not_raw_driver_exception_when_locked(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_record_attempt_link`'s own promotion-half guard (K3-BLOCK-1 half 2
    analogue): `BEGIN IMMEDIATE` takes RESERVED immediately but SQLite
    promotes to EXCLUSIVE lazily, on the first real write -- the INSERT --
    so contention can still fire AFTER a successful `BEGIN IMMEDIATE`.
    Identical proxy-connection technique to
    `test_operator_operation_service.
    test_record_confirmation_lock_contention_inside_transaction_raises_bounded_error_not_raw`
    (`sqlite3.Connection` is an immutable C type and cannot be patched
    directly): wraps the module's `_connect` in a proxy whose `execute`
    raises the SAME exception class SQLite raises, on the INSERT into
    `attempts` specifically, so the transaction, the connection, and the
    surrounding handling are all real and only the failing statement is
    simulated.

    NOT redundant with the acquisition-half test above: that test's guard
    sits around `_ensure_schema`/`BEGIN IMMEDIATE` and cannot fire here
    (`BEGIN IMMEDIATE` succeeds on this path); deleting only the
    promotion-half `except` clause leaves the acquisition-half test green
    and fails this one.
    """

    adapter = _adapter(tmp_foundry)
    rollbacks: list[str] = []

    class _FailingInsertConnection:
        def __init__(self, conn: sqlite3.Connection) -> None:
            self._conn = conn

        def execute(self, sql: str, *args: Any, **kwargs: Any) -> Any:
            if sql.lstrip().upper().startswith("INSERT INTO ATTEMPTS"):
                raise sqlite3.OperationalError("database is locked")
            if sql.strip().upper() == "ROLLBACK":
                rollbacks.append(sql)
            return self._conn.execute(sql, *args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._conn, name)

    real_connect = ops_module._connect
    monkeypatch.setattr(
        ops_module, "_connect", lambda paths: _FailingInsertConnection(real_connect(paths))
    )

    with pytest.raises(AttemptStoreUnavailableError) as excinfo:
        _create_attempt(adapter, operation_id="opm_" + "d" * 64)

    assert not isinstance(excinfo.value, sqlite3.OperationalError)
    assert "database is locked" not in str(excinfo.value)
    assert rollbacks == ["ROLLBACK"]
