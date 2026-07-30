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
from research_foundry.services.agent_job_schemas import AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.operator_attempt_adapter import (
    AttemptRecord,
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
