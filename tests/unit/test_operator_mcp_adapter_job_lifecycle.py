"""Unit tests for the `job.status`/`job.cancel`/`job.resume` Operator MCP
adapters (research-foundry-operator-mcp-v1 P3, OPM-3.4).

Reuses, never reinvents (per this task's and the repo's own convention):
`test_operator_mcp_policy`'s identity fixtures/`_basic_ctx`/`_run_targets`
helpers, `test_operator_operation_service`'s `_mint_and_record`/`_authorize`
confirmation helpers, and `test_operator_cancel_resume_service`'s `_consume`
helper for building a real target operation to poll/cancel/resume.

Importing `job_lifecycle` here registers its three adapters into
`operator_mcp_adapters.base._REGISTRY` for the remainder of this pytest
process (module-level `base.register(...)` side effect, same convention
`run_plan.py`/`swarm_start.py` already use) -- see this task's own report
for the resulting, unavoidable collision with
`test_operator_mcp_adapter_base.py::test_get_adapter_returns_none_for_unregistered_kind`
(which probes the now-registered `"job.resume"` kind) and the one-line fix
that test needs (out of this task's file ownership; reported, not made).
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_attempt_adapter import (
    MAX_ATTEMPTS_PER_OPERATION,
    OperatorAttemptAdapter,
)
from research_foundry.services.operator_cancel_resume_service import (
    CancellationOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_mcp_adapters import base, job_lifecycle
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.services.operator_receipt_service import OperatorReceiptService

from tests.unit.test_operator_cancel_resume_service import _action, _consume
from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _IDENTITY,
    _IDENTITY_OTHER_WORKSPACE,
    _basic_ctx,
    _default_operator_identity,
    _run_targets,
)
from tests.unit.test_operator_operation_service import _authorize, _mint_and_record

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _target_operation_id(tmp_foundry: FoundryPaths, op_service: OperatorOperationService) -> str:
    """Build and consume a real `run.plan`-kind operation via the exact
    P1/OPM-2.1 entry surface (`_consume`) -- the TARGET operation
    `job.status`/`job.cancel`/`job.resume` poll/cancel/resume."""

    ctx = _basic_ctx(operation_kind="run.plan", targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    assert outcome.outcome == "created"
    assert outcome.operation is not None
    return outcome.operation.operation_id


def _cancel_confirmation(
    tmp_foundry: FoundryPaths, op_service: OperatorOperationService, operation_id: str, idempotency_key: str
) -> tuple[dict[str, Any], str]:
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=job_lifecycle.CANCEL_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.SENSITIVITY_LEVELS[-1],
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
        input_payload={"operation_id": operation_id},
    )
    _confirmation_id, token, record = _mint_and_record(op_service, ctx)
    return record, token


def _resume_confirmation(
    tmp_foundry: FoundryPaths, op_service: OperatorOperationService, operation_id: str, idempotency_key: str
) -> tuple[dict[str, Any], str]:
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=job_lifecycle.RESUME_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.SENSITIVITY_LEVELS[-1],
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
        input_payload={"operation_id": operation_id},
    )
    _confirmation_id, token, record = _mint_and_record(op_service, ctx)
    return record, token


class _DenyingCancelResumeService(OperatorCancelResumeService):
    """Subclass overriding ONLY `request_cancellation` to always deny --
    every other method (notably `run_or_replay`, which
    `base.run_pipeline` itself calls to execute `job.cancel`'s OWN
    action) is inherited, real behavior. Used to prove
    `invoke_cancel`'s action converts a `request_cancellation` denial
    into a governed `ExecutionOutcome("failed", ...)`, never a raw
    exception reaching the caller."""

    def request_cancellation(self, operation_id: str, *, workspace_id: str, requested_by: str | None = None) -> CancellationOutcome:  # noqa: ARG002
        return CancellationOutcome("denied", operation_id, None, None, reason_code="not_found")


# ---------------------------------------------------------------------------
# job.status
# ---------------------------------------------------------------------------


def test_job_status_in_progress_before_any_attempt_or_terminal_receipt(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="status-1",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.operation_id is None  # job.status never consumes/creates a manifest
    assert result.result is not None
    assert result.result["operation_id"] == operation_id
    assert result.result["operation_kind"] == "run.plan"
    assert result.result["status"] == "in_progress"
    assert result.result["terminal"] is False
    assert result.result["latest_attempt_id"] is None
    assert result.result["attempt_count"] == 0


def test_job_status_reports_terminal_receipt_status_after_cancel(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    cancel_resume = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    cancel_resume.request_cancellation(operation_id, workspace_id=_IDENTITY.workspace_id, requested_by="alice")
    execution = cancel_resume.run_actions(
        operation_id,
        identity=_IDENTITY,
        operation_kind="run.plan",
        actions=[_action("act-0", [])],
        attempt_ref="attempt-1",
    )
    assert execution.status == "canceled"

    result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="status-2",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
        receipts=receipt_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["status"] == "canceled"
    assert result.result["terminal"] is True


def test_job_status_reports_latest_attempt_status(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    attempt = attempt_adapter.create_attempt(
        operation_id,
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        {"allowed_tools": [], "data_scopes": []},
        workspace_id=_IDENTITY.workspace_id,
        identity=_IDENTITY,
    )

    result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="status-3",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["status"] == "queued"
    assert result.result["latest_attempt_id"] == attempt.attempt_id
    assert result.result["attempt_count"] == 1


def test_job_status_dry_run_returns_bounded_shape_and_touches_nothing(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="status-dry",
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "job.status"}


def test_job_status_never_reaches_agent_job_service_unbounded_reads(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION-TESTED GUARD (see this task's report): `job_lifecycle`
    never imports `agent_job_service` at all -- structurally impossible to
    reach `AgentJobService.load_events` (unbounded full-file read) or
    `list_staged_artifacts` (unbounded glob), the two defect-class examples
    the P3 implementer contract names. Proven with spies that raise if
    touched (module docstring's own convention, mirroring
    `base.py`'s dry-run spy proof), not mere inspection."""

    from research_foundry.services.agent_job_service import AgentJobService

    def _must_not_call(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("job.status must never call AgentJobService.load_events/list_staged_artifacts")

    monkeypatch.setattr(AgentJobService, "load_events", _must_not_call)
    monkeypatch.setattr(AgentJobService, "list_staged_artifacts", _must_not_call)

    op_service = OperatorOperationService(tmp_foundry)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)
    attempt_adapter.create_attempt(
        operation_id,
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        {"allowed_tools": [], "data_scopes": []},
        workspace_id=_IDENTITY.workspace_id,
        identity=_IDENTITY,
    )

    result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="status-spy",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    assert result.ok is True, result.error


# ---------------------------------------------------------------------------
# job.cancel
# ---------------------------------------------------------------------------


def test_job_cancel_requests_cancellation_and_completes(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)
    record, token = _cancel_confirmation(tmp_foundry, op_service, operation_id, "cancel-1")

    result = job_lifecycle.invoke_cancel(
        operation_id=operation_id,
        idempotency_key="cancel-1",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.operation_id is not None
    assert result.result is not None
    assert result.result["target_operation_id"] == operation_id
    assert result.result["status"] == "completed"

    cancel_resume = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    assert cancel_resume.cancellation_requested(operation_id, workspace_id=_IDENTITY.workspace_id) is True


def test_job_cancel_denial_converts_to_governed_failure_not_a_raw_exception(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)
    record, token = _cancel_confirmation(tmp_foundry, op_service, operation_id, "cancel-deny")

    denying_service = _DenyingCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    result = job_lifecycle.invoke_cancel(
        operation_id=operation_id,
        idempotency_key="cancel-deny",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
        cancel_resume=denying_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


def test_job_cancel_dry_run_never_calls_request_cancellation(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    def _must_not_run(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("dry run must never call request_cancellation")

    monkeypatch.setattr(OperatorCancelResumeService, "request_cancellation", _must_not_run)

    result = job_lifecycle.invoke_cancel(
        operation_id=operation_id,
        idempotency_key="cancel-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "job.cancel"}


# ---------------------------------------------------------------------------
# job.resume
# ---------------------------------------------------------------------------


def test_job_resume_authorizes_and_provisions_fresh_attempt(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)
    record, token = _resume_confirmation(tmp_foundry, op_service, operation_id, "resume-1")

    result = job_lifecycle.invoke_resume(
        operation_id=operation_id,
        idempotency_key="resume-1",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["status"] == "resume_authorized"
    assert result.result["target_operation_kind"] == "run.plan"
    assert result.result["original_actions_reexecuted"] is False
    assert result.result["new_attempt_id"]

    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    attempts = attempt_adapter.list_attempts_for_operation(operation_id, identity=_IDENTITY)
    assert len(attempts) == 1
    assert attempts[0].attempt_id == result.result["new_attempt_id"]


def test_job_resume_already_terminal_denies_governed_not_a_silent_success(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    cancel_resume = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    cancel_resume.request_cancellation(operation_id, workspace_id=_IDENTITY.workspace_id, requested_by="alice")
    execution = cancel_resume.run_actions(
        operation_id, identity=_IDENTITY, operation_kind="run.plan", actions=[_action("act-0", [])], attempt_ref="attempt-1"
    )
    assert execution.status == "canceled"

    record, token = _resume_confirmation(tmp_foundry, op_service, operation_id, "resume-terminal")

    result = job_lifecycle.invoke_resume(
        operation_id=operation_id,
        idempotency_key="resume-terminal",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
        receipts=receipt_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"

    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    assert attempt_adapter.list_attempts_for_operation(operation_id, identity=_IDENTITY) == []


def test_job_resume_bounded_attempts_cap_denies_governed_not_infinite_retry(tmp_foundry: FoundryPaths) -> None:
    """Proves the P2S-NB-9/OPM-3.4 integration: exceeding
    `MAX_ATTEMPTS_PER_OPERATION` inside `job.resume`'s own action surfaces
    as a governed `ok=False` result (via `run_actions`' existing exception
    -> failed-terminal-receipt conversion), never an uncaught exception,
    never an infinite retry, and never a silent success (no NEW attempt is
    created beyond the cap)."""

    op_service = OperatorOperationService(tmp_foundry)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    for i in range(MAX_ATTEMPTS_PER_OPERATION):
        attempt_adapter.create_attempt(
            operation_id,
            "claude_agent_sdk",
            "rf_synthesize_deep",
            f"pre-seed-{i}",
            {"allowed_tools": [], "data_scopes": []},
            workspace_id=_IDENTITY.workspace_id,
            identity=_IDENTITY,
        )
    assert len(attempt_adapter.list_attempts_for_operation(operation_id, identity=_IDENTITY)) == MAX_ATTEMPTS_PER_OPERATION

    record, token = _resume_confirmation(tmp_foundry, op_service, operation_id, "resume-capped")

    result = job_lifecycle.invoke_resume(
        operation_id=operation_id,
        idempotency_key="resume-capped",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert len(attempt_adapter.list_attempts_for_operation(operation_id, identity=_IDENTITY)) == MAX_ATTEMPTS_PER_OPERATION


def test_job_resume_dry_run_never_creates_an_attempt(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    operation_id = _target_operation_id(tmp_foundry, op_service)

    def _must_not_run(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("dry run must never call create_attempt")

    monkeypatch.setattr(OperatorAttemptAdapter, "create_attempt", _must_not_run)

    result = job_lifecycle.invoke_resume(
        operation_id=operation_id,
        idempotency_key="resume-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "job.resume"}


# ---------------------------------------------------------------------------
# AC OPM-3.4: wrong-workspace is indistinguishable from missing, for all
# three kinds -- proven by asserting the two error envelopes are IDENTICAL,
# not merely both-unsuccessful (the no-existence-leak convention, H6).
# ---------------------------------------------------------------------------


def test_job_status_wrong_workspace_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(tmp_foundry, op_service)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY_OTHER_WORKSPACE)

    wrong_workspace_result = job_lifecycle.invoke_status(
        operation_id=real_operation_id,
        idempotency_key="status-wrong-ws",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    missing_result = job_lifecycle.invoke_status(
        operation_id="op_does_not_exist_at_all",
        idempotency_key="status-missing",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert wrong_workspace_result.ok is False
    assert missing_result.ok is False
    assert wrong_workspace_result.error == missing_result.error


def test_job_cancel_wrong_workspace_indistinguishable_from_missing_dry_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(tmp_foundry, op_service)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY_OTHER_WORKSPACE)

    wrong_workspace_result = job_lifecycle.invoke_cancel(
        operation_id=real_operation_id,
        idempotency_key="cancel-wrong-ws",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_result = job_lifecycle.invoke_cancel(
        operation_id="op_does_not_exist_at_all",
        idempotency_key="cancel-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert wrong_workspace_result.ok is False
    assert missing_result.ok is False
    assert wrong_workspace_result.error == missing_result.error


def test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(tmp_foundry, op_service)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY_OTHER_WORKSPACE)

    wrong_workspace_result = job_lifecycle.invoke_resume(
        operation_id=real_operation_id,
        idempotency_key="resume-wrong-ws",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_result = job_lifecycle.invoke_resume(
        operation_id="op_does_not_exist_at_all",
        idempotency_key="resume-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert wrong_workspace_result.ok is False
    assert missing_result.ok is False
    assert wrong_workspace_result.error == missing_result.error


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------


def test_resolve_operation_workspace_swallows_lookup_failure(tmp_foundry: FoundryPaths) -> None:
    """MUTATION-TESTED GUARD (see this task's report): `_resolve_operation_
    workspace` swallows a failed `load_operation` lookup (missing
    `operation_id`, malformed store) and returns `None` -- NEVER a
    permissive/fabricated workspace id. `None` then makes `PolicyContext`'s
    H3/H6 gate deny with `not_found`, the SAME shape a genuinely-missing
    operation produces -- mirrors `run_plan.py`'s own `test_resolve_intent_
    sensitivity_swallows_lookup_failure` convention exactly."""

    result = job_lifecycle._resolve_operation_workspace("does-not-exist-at-all", tmp_foundry)
    assert result is None


def test_missing_operation_denies_via_h3_gate_not_a_fabricated_workspace_match(
    tmp_foundry: FoundryPaths,
) -> None:
    """The layer above the unit test just above: a MISSING `operation_id`,
    looked up under the DEFAULT identity's own workspace (`_IDENTITY`,
    `ws-mine`) via `dry_run=True` (so only `evaluate_policy`'s H3 gate
    decides -- no `load_operation` call inside `invoke_cancel` itself on
    this path), must still deny `not_found`. If `_resolve_operation_
    workspace` ever regressed to fabricate a workspace matching the
    caller's own identity on a lookup failure (rather than `None`), the H3
    gate would incorrectly PASS for this genuinely-missing operation and
    `dry_run` would report `ok=True` -- a real fail-open this test would
    catch that the wrong-workspace-focused tests above do not (there, the
    caller's OWN identity is already a different workspace than any
    plausible fabricated value, which coincidentally still denies even
    under that mutation)."""

    result = job_lifecycle.invoke_cancel(
        operation_id="does-not-exist-at-all",
        idempotency_key="cancel-missing-samews",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "not_found"


def test_all_three_kinds_are_registered() -> None:
    assert base.get_adapter("job.status") is job_lifecycle.STATUS_ADAPTER
    assert base.get_adapter("job.cancel") is job_lifecycle.CANCEL_ADAPTER
    assert base.get_adapter("job.resume") is job_lifecycle.RESUME_ADAPTER
