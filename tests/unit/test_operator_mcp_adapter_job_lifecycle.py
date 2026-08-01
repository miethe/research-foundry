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

from pathlib import Path
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import operator_operation_service as ops_module
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
from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)
from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _IDENTITY,
    _IDENTITY_OTHER_WORKSPACE,
    _basic_ctx,
    _default_operator_identity,
    _run_targets,
)
from tests.unit.test_operator_operation_service import _authorize, _mint_and_record
from tests.unit.test_operator_receipt_service import _block_operations_db, _cold_paths

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _target_operation_id(
    tmp_foundry: FoundryPaths,
    op_service: OperatorOperationService,
    *,
    effective_sensitivity: str = "public",
) -> str:
    """Build and consume a real `run.plan`-kind operation via the exact
    P1/OPM-2.1 entry surface (`_consume`) -- the TARGET operation
    `job.status`/`job.cancel`/`job.resume` poll/cancel/resume.

    `effective_sensitivity` (P3 hardening pass, HIGH-2 defect fix) is the
    TARGET operation's own persisted sensitivity -- `_basic_ctx`'s own
    default (`"public"`) unless a test explicitly builds a higher-
    sensitivity target to prove the H7 guard still denies correctly against
    a REAL, non-strictest-by-hardcoding value (see the `*_denies_above_
    ceiling_*` tests below, which now build a `"client_sensitive"` target
    specifically). Every caller of this helper that does NOT override this
    parameter is asserting the target is `"public"` -- `_cancel_
    confirmation`/`_resume_confirmation` below MUST be minted against the
    SAME value, or the confirmation's canonical digest will not match what
    `invoke_cancel`/`invoke_resume` compute internally post-fix (a
    `confirmation_mismatch`, not a silent pass)."""

    ctx = _basic_ctx(
        operation_kind="run.plan", targets=_run_targets(), effective_sensitivity=effective_sensitivity
    )
    outcome = _consume(tmp_foundry, op_service, ctx)
    assert outcome.outcome == "created"
    assert outcome.operation is not None
    return outcome.operation.operation_id


def _cancel_confirmation(
    tmp_foundry: FoundryPaths,
    op_service: OperatorOperationService,
    operation_id: str,
    idempotency_key: str,
    *,
    target_effective_sensitivity: str = "public",
) -> tuple[dict[str, Any], str]:
    """`target_effective_sensitivity` (P3 hardening pass, HIGH-2 defect fix)
    MUST equal the `effective_sensitivity` the TARGET operation
    (`operation_id`, built via `_target_operation_id`) was itself created
    with -- `invoke_cancel` now derives its own internal ctx's
    `effective_sensitivity` from that TARGET's persisted manifest (no
    longer a hardcoded constant), so the confirmation minted here must bind
    to the SAME value for its canonical digest to match what `invoke_cancel`
    recomputes, exactly like `run_plan.py`'s own equivalence test already
    requires for intent-derived sensitivity."""

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=job_lifecycle.CANCEL_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=target_effective_sensitivity,
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
        input_payload={"operation_id": operation_id},
    )
    _confirmation_id, token, record = _mint_and_record(op_service, ctx)
    return record, token


def _resume_confirmation(
    tmp_foundry: FoundryPaths,
    op_service: OperatorOperationService,
    operation_id: str,
    idempotency_key: str,
    *,
    target_effective_sensitivity: str = "public",
) -> tuple[dict[str, Any], str]:
    """See `_cancel_confirmation`'s own docstring immediately above --
    identical `target_effective_sensitivity` contract, for `job.resume`."""

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=job_lifecycle.RESUME_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=target_effective_sensitivity,
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
        input_payload={"operation_id": operation_id},
    )
    _confirmation_id, token, record = _mint_and_record(op_service, ctx)
    return record, token


def _insert_corrupt_operation_row(paths: FoundryPaths, operation_id: str, workspace_id: str) -> None:
    """Directly persists an `operations` row whose `manifest_json` is
    valid JSON that deserializes to `None` (a non-Mapping) -- simulating
    an on-disk corrupted manifest (K4-NB-3) that
    `OperationRecord.from_manifest`'s bare `manifest["operation_id"]`/
    `manifest["workspace_id"]` subscripting (`operator_operation_service.py`
    `:811-816`) turns into a `TypeError`, not a `KeyError`.

    Bypasses `OperatorOperationService`'s own write path entirely (a raw
    `INSERT` against the same table/columns `_ensure_schema` creates) --
    there is no legitimate way to produce this row through this module's
    real API, which is the point: this simulates corruption, not a code
    path this service would ever take itself."""

    conn = ops_module._connect(paths)
    try:
        ops_module._ensure_schema(conn)
        conn.execute(
            "INSERT INTO operations (operation_id, workspace_id, idempotency_key, "
            "canonical_input_digest, policy_snapshot_version, operation_kind, "
            "effective_sensitivity, manifest_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                operation_id,
                workspace_id,
                "corrupt-idem-key",
                "0" * 64,
                "v1",
                "run.plan",
                "client_sensitive",
                "null",  # valid JSON -> Python None, a non-Mapping
                "2026-01-01T00:00:00Z",
            ),
        )
    finally:
        conn.close()


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
# Retry-contract fix: operations-store transient unavailability must be
# reported as a RETRYABLE `internal_error`, never folded into the SAME
# non-retryable `not_found` a genuinely missing operation gets. Before this
# fix, `_resolve_operation_workspace`'s blanket `except Exception` swallowed
# `OperationStoreUnavailableError` identically to a real `KeyError`
# ("genuinely missing"), so a transient SQLite lock on the operations store
# was reported through the H3/H6 RBAC gate as a permanent, non-retryable
# absence -- correct denial, wrong retryability, wrong reason code.
#
# Uses `test_operator_receipt_service.py`'s own established, non-vacuous
# technique (`_cold_paths` + `_block_operations_db`) rather than `tmp_foundry`
# -- per this task's own vacuity-trap warning, a WARM `_ensure_schema` does
# not reliably block under contention, so a test against a warm schema would
# pass for free without ever exercising the guard. `_cold_paths` builds a
# `FoundryPaths` whose operations db has genuinely never been touched, so
# `_ensure_schema`'s FIRST call attempts real DDL and blocks behind a REAL
# competing writer lock, never a monkeypatched stand-in.
# ---------------------------------------------------------------------------


def test_job_status_reports_retryable_internal_error_when_store_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION-TESTED GUARD (see this task's report) for `invoke_status`'s
    call site of `_resolve_operation_workspace_or_error`."""

    cold_paths = _cold_paths(tmp_path)
    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(cold_paths)
    try:
        result = job_lifecycle.invoke_status(
            operation_id="op-does-not-matter",
            idempotency_key="status-locked",
            paths=cold_paths,
            now=ids.now(),
        )
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert result.error["retryable"] is True


def test_job_cancel_reports_retryable_internal_error_when_store_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION-TESTED GUARD (see this task's report) for `invoke_cancel`'s
    call site of `_resolve_operation_workspace_or_error` -- proves the fix
    was applied to this sibling site too, not only `job.status`'s."""

    cold_paths = _cold_paths(tmp_path)
    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(cold_paths)
    try:
        result = job_lifecycle.invoke_cancel(
            operation_id="op-does-not-matter",
            idempotency_key="cancel-locked",
            confirmation_record=None,
            presented_token=None,
            paths=cold_paths,
            now=ids.now(),
        )
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert result.error["retryable"] is True


def test_job_resume_reports_retryable_internal_error_when_store_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION-TESTED GUARD (see this task's report) for `invoke_resume`'s
    call site of `_resolve_operation_workspace_or_error` -- proves the fix
    was applied to this sibling site too, not only `job.status`'s."""

    cold_paths = _cold_paths(tmp_path)
    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(cold_paths)
    try:
        result = job_lifecycle.invoke_resume(
            operation_id="op-does-not-matter",
            idempotency_key="resume-locked",
            confirmation_record=None,
            presented_token=None,
            paths=cold_paths,
            now=ids.now(),
        )
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert result.error["retryable"] is True


def test_store_locked_result_is_distinct_from_genuinely_missing_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual regression this task fixes, proven directly: a locked
    store and a genuinely-missing operation used to produce the IDENTICAL
    `not_found`/`retryable: false` envelope (both swallowed by
    `_resolve_operation_workspace`'s old blanket `except Exception`). They
    MUST now differ in BOTH `reason_code` and `retryable`."""

    cold_paths = _cold_paths(tmp_path)
    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(cold_paths)
    try:
        locked_result = job_lifecycle.invoke_status(
            operation_id="op-does-not-matter",
            idempotency_key="status-locked-vs-missing",
            paths=cold_paths,
            now=ids.now(),
        )
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    # Lock released -- `_ensure_schema` now succeeds for real, and the
    # SAME operation_id is a genuine `KeyError` ("not found") this time.
    missing_result = job_lifecycle.invoke_status(
        operation_id="op-does-not-matter",
        idempotency_key="status-locked-vs-missing-2",
        paths=cold_paths,
        now=ids.now(),
    )

    assert locked_result.error is not None
    assert missing_result.error is not None
    assert locked_result.error["reason_code"] == "internal_error"
    assert locked_result.error["retryable"] is True
    assert missing_result.error["reason_code"] == "not_found"
    assert missing_result.error["retryable"] is False
    assert locked_result.error != missing_result.error


def test_job_status_reports_bounded_nonretryable_error_for_corrupt_manifest(
    tmp_path: Path,
) -> None:
    """K4-NB-3, MUTATION-TESTED GUARD (see this task's report): a
    persisted `operations` row whose `manifest_json` deserializes to a
    non-Mapping makes `OperationRecord.from_manifest`'s bare subscripting
    raise `TypeError` -- `_resolve_operation_workspace_or_error`'s final
    `except Exception` MUST turn this into a bounded, NON-retryable
    `internal_error`, never a raw `TypeError` crossing `invoke_status`'s
    public surface. If the guard were absent, THIS CALL ITSELF would
    raise `TypeError` and the test would error out rather than reach any
    assertion below -- that failure mode IS the proof of boundedness,
    no separate `isinstance` check needed."""

    cold_paths = _cold_paths(tmp_path)
    operation_id = "corrupt-manifest-op"
    _insert_corrupt_operation_row(cold_paths, operation_id, "ws-mine")

    result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="status-corrupt",
        paths=cold_paths,
        now=ids.now(),
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert result.error["retryable"] is False


def test_locked_missing_and_corrupt_manifest_produce_three_distinct_bounded_envelopes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The full retry-contract picture for the SAME `operation_id`, all
    three states reachable through `_resolve_operation_workspace_or_error`:

    1. Store LOCKED (transient) -> `internal_error`, `retryable: True`.
    2. Genuinely MISSING (permanent absence) -> `not_found`,
       `retryable: False`.
    3. Persisted but CORRUPT (permanent, but NOT "missing") ->
       `internal_error`, `retryable: False` -- same reason_code as (1),
       opposite retryability; distinguishable from (2) by reason_code.

    All three envelopes must be pairwise distinct, and NEITHER "locked"
    NOR "corrupt" may ever collapse into `not_found`'s shape (the
    original defect class this whole task addresses, one layer up)."""

    operation_id = "three-way-op"
    cold_paths = _cold_paths(tmp_path)

    monkeypatch.setattr(ops_module, "_BUSY_TIMEOUT_MS", 50)
    blocker = _block_operations_db(cold_paths)
    try:
        locked_result = job_lifecycle.invoke_status(
            operation_id=operation_id,
            idempotency_key="three-way-locked",
            paths=cold_paths,
            now=ids.now(),
        )
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    missing_result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="three-way-missing",
        paths=cold_paths,
        now=ids.now(),
    )

    _insert_corrupt_operation_row(cold_paths, operation_id, "ws-mine")
    corrupt_result = job_lifecycle.invoke_status(
        operation_id=operation_id,
        idempotency_key="three-way-corrupt",
        paths=cold_paths,
        now=ids.now(),
    )

    for result in (locked_result, missing_result, corrupt_result):
        assert result.ok is False
        assert result.error is not None

    assert locked_result.error["reason_code"] == "internal_error"
    assert locked_result.error["retryable"] is True

    assert missing_result.error["reason_code"] == "not_found"
    assert missing_result.error["retryable"] is False

    assert corrupt_result.error["reason_code"] == "internal_error"
    assert corrupt_result.error["retryable"] is False

    # Pairwise distinct envelopes -- no two of the three collapse together.
    assert locked_result.error != missing_result.error
    assert locked_result.error != corrupt_result.error
    assert missing_result.error != corrupt_result.error


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------


def test_resolve_operation_workspace_swallows_lookup_failure(tmp_foundry: FoundryPaths) -> None:
    """MUTATION-TESTED GUARD (see this task's report): `_resolve_operation_
    workspace` swallows a failed `load_operation` lookup (missing
    `operation_id`, malformed store) and returns `(None, <strictest>)` --
    NEVER a permissive/fabricated workspace id, and NEVER a permissive
    sensitivity pairing either (P3 hardening pass, HIGH-2 defect fix added
    the second tuple element). `None` workspace then makes `PolicyContext`'s
    H3/H6 gate deny with `not_found`, the SAME shape a genuinely-missing
    operation produces -- mirrors `run_plan.py`'s own `test_resolve_intent_
    sensitivity_swallows_lookup_failure` convention exactly."""

    workspace_id, effective_sensitivity = job_lifecycle._resolve_operation_workspace(
        "does-not-exist-at-all", tmp_foundry
    )
    assert workspace_id is None
    assert effective_sensitivity == policy.SENSITIVITY_LEVELS[-1]


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


# ---------------------------------------------------------------------------
# H7/HIGH-2 defect fix: `job.status`/`job.cancel`/`job.resume` now resolve
# `effective_sensitivity` from the TARGET operation's own persisted manifest
# (`_operation_effective_sensitivity_of`), not from an unconditional
# `policy.resolve_effective_sensitivity(None)` hardcode to the STRICTEST
# label.
#
# **P3 hardening pass, HIGH-2 defect fix.** The three tests this section
# used to contain (`test_job_*_denies_above_ceiling_h7_guard_stage_
# indistinguishable_from_missing`) each built their target operation via
# `_target_operation_id(tmp_foundry, op_service)` -- which, via `_basic_ctx`,
# has ALWAYS defaulted to `effective_sensitivity="public"` -- and then
# asserted a `"work_sensitive"` ceiling (one rank ABOVE `"public"`) DENIED
# that target. That assertion was true ONLY because of the HIGH-2 defect
# (every `job.*` call was judged against the hardcoded strictest label,
# `"client_sensitive"`, regardless of the target's real, lower sensitivity)
# -- it PINNED the bug as correct behavior. Per this task's own defect-class
# checklist ("never pin unsafe behavior with a test"), these three tests are
# inverted below into PAIRS:
#
#   *_allows_when_ceiling_covers_target_real_sensitivity -- the SAME
#   `"public"`-sensitivity target, the SAME `"work_sensitive"` ceiling, but
#   now ALLOWED -- this is the direct, mutation-provable proof of the
#   HIGH-2 fix: reverting `_resolve_operation_workspace`'s
#   `_operation_effective_sensitivity_of` call back to a hardcoded
#   `policy.SENSITIVITY_LEVELS[-1]` makes this test FAIL (it would deny
#   instead of allow).
#
#   *_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing --
#   kept, but now built against a target whose OWN real, persisted
#   sensitivity is EXPLICITLY `"client_sensitive"` (via `_target_operation_
#   id`'s `effective_sensitivity` parameter), proving the guard still
#   functions correctly against a genuinely HIGH-sensitivity target -- not
#   merely because every target was judged at the strictest label by
#   construction.
#
# Every ceiling override below also uses `_recording_ceiling` (HIGH-1 fix,
# `test_operator_mcp_adapter_run_plan.py`) instead of a discarding
# `lambda *a, **kw: ...`, proving each of `job_lifecycle`'s three
# `resolve_local_sensitivity_ceiling` call sites (`invoke_status`/
# `invoke_cancel`/`invoke_resume`) threads its resolved `paths` through
# correctly.
# ---------------------------------------------------------------------------


def test_job_status_allows_when_ceiling_covers_target_real_sensitivity(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HIGH-2 defect fix, direct proof: a `"public"`-sensitivity target
    (this file's own default, see `_target_operation_id`) under a
    `"work_sensitive"` ceiling -- one rank ABOVE `"public"` -- now ALLOWS.
    Before this fix, `invoke_status` hardcoded `effective_sensitivity` to
    the STRICTEST label regardless of the target's real content, so this
    exact scenario incorrectly denied every time. MUTATION-TESTED GUARD
    (see this task's report): reverting `_operation_effective_sensitivity_
    of`'s use in `_resolve_operation_workspace` back to a hardcoded
    `policy.SENSITIVITY_LEVELS[-1]` makes this test FAIL."""

    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(tmp_foundry, op_service, effective_sensitivity="public")

    ceiling_double, ceiling_calls = _recording_ceiling("work_sensitive")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    result = job_lifecycle.invoke_status(
        operation_id=real_operation_id,
        idempotency_key="idem-within-ceiling",
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["operation_id"] == real_operation_id
    assert result.result["operation_kind"] == "run.plan"
    assert result.result["terminal"] is False

    # HIGH-1 fix, direct proof: `resolve_local_sensitivity_ceiling` was
    # called with the REAL `paths` value (`tmp_foundry`).
    assert ceiling_calls == [tmp_foundry]


def test_job_status_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`job.status` sibling of the ALLOW test immediately above -- here the
    TARGET operation's own real, persisted sensitivity is EXPLICITLY
    `"client_sensitive"` (not merely a hardcoded judgment applied
    regardless of content), one rank above the `"work_sensitive"` ceiling,
    proving the H7 guard still denies correctly against a genuinely
    HIGH-sensitivity target post-HIGH-2-fix.

    Also proves the SAME H6/H7 one-denial-shape guarantee this task's
    `run_plan.py`/`swarm_start.py` sibling tests prove: this above-ceiling
    denial (guard stage) is byte-identical to a genuinely-missing-operation
    denial (rbac stage, `test_missing_operation_denies_via_h3_gate_not_a_
    fabricated_workspace_match` above) -- a caller cannot tell "this
    operation exists but you are not cleared for it" from "this operation
    does not exist" from the response alone."""

    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(
        tmp_foundry, op_service, effective_sensitivity="client_sensitive"
    )

    ceiling_double, ceiling_calls = _recording_ceiling("work_sensitive")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    # Direct proof of STAGE: build the identical PolicyContext `invoke_
    # status` would build internally and evaluate it directly. The target
    # above was built with `effective_sensitivity="client_sensitive"`
    # explicitly (`policy.SENSITIVITY_LEVELS[-1]`) -- this ctx mirrors THAT
    # real, persisted value, not a `resolve_effective_sensitivity(None)`
    # hardcode (removed by the HIGH-2 fix).
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=job_lifecycle.STATUS_OPERATION_KIND,
        idempotency_key="idem-above-ceiling",
        effective_sensitivity=policy.SENSITIVITY_LEVELS[-1],
        sensitivity_ceiling="work_sensitive",
        targets=(policy.TargetRef(target_kind="agent_job", target_ref=real_operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
        input_payload={"operation_id": real_operation_id},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = job_lifecycle.invoke_status(
        operation_id=real_operation_id,
        idempotency_key="idem-above-ceiling",
        paths=tmp_foundry,
        operations=op_service,
    )
    missing_result = job_lifecycle.invoke_status(
        operation_id="op_does_not_exist_at_all_either",
        idempotency_key="idem-above-ceiling-missing",
        paths=tmp_foundry,
        operations=op_service,
    )

    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert above_ceiling_result.error["operation_id"] is None
    assert above_ceiling_result.error["receipt_ref"] is None
    assert "detail" not in above_ceiling_result.error

    assert missing_result.ok is False
    assert above_ceiling_result.error == missing_result.error

    # HIGH-1 fix, direct proof: `resolve_local_sensitivity_ceiling` was
    # called with the REAL `paths` value (`tmp_foundry`) both times
    # `invoke_status` ran above.
    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_job_cancel_allows_when_ceiling_covers_target_real_sensitivity(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`job.cancel` sibling of `job.status`'s own ALLOW test above -- same
    HIGH-2 fix, same proof, via `dry_run=True` so no confirmation needs
    minting (mirrors this file's own `*_wrong_workspace_indistinguishable_
    from_missing_dry_run` convention)."""

    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(tmp_foundry, op_service, effective_sensitivity="public")

    ceiling_double, ceiling_calls = _recording_ceiling("work_sensitive")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    result = job_lifecycle.invoke_cancel(
        operation_id=real_operation_id,
        idempotency_key="idem-within-ceiling-cancel",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "job.cancel"}
    assert ceiling_calls == [tmp_foundry]


def test_job_cancel_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`job.cancel` sibling of `job.status`'s own DENY test above -- same
    defect, same fix, same H6/H7 shape proof, via `dry_run=True` so no
    confirmation ever needs to be minted."""

    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(
        tmp_foundry, op_service, effective_sensitivity="client_sensitive"
    )

    ceiling_double, ceiling_calls = _recording_ceiling("work_sensitive")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    above_ceiling_result = job_lifecycle.invoke_cancel(
        operation_id=real_operation_id,
        idempotency_key="idem-above-ceiling-cancel",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
        operations=op_service,
    )
    missing_result = job_lifecycle.invoke_cancel(
        operation_id="op_does_not_exist_at_all_either",
        idempotency_key="idem-above-ceiling-cancel-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
        operations=op_service,
    )

    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert above_ceiling_result.error["operation_id"] is None
    assert above_ceiling_result.error["receipt_ref"] is None
    assert "detail" not in above_ceiling_result.error

    assert missing_result.ok is False
    assert above_ceiling_result.error == missing_result.error
    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_job_resume_allows_when_ceiling_covers_target_real_sensitivity(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`job.resume` sibling of `job.status`'s own ALLOW test above -- same
    HIGH-2 fix, same proof, via `dry_run=True`."""

    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(tmp_foundry, op_service, effective_sensitivity="public")

    ceiling_double, ceiling_calls = _recording_ceiling("work_sensitive")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    result = job_lifecycle.invoke_resume(
        operation_id=real_operation_id,
        idempotency_key="idem-within-ceiling-resume",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "job.resume"}
    assert ceiling_calls == [tmp_foundry]


def test_job_resume_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`job.resume` sibling of `job.status`'s own DENY test above -- same
    defect, same fix, same H6/H7 shape proof."""

    op_service = OperatorOperationService(tmp_foundry)
    real_operation_id = _target_operation_id(
        tmp_foundry, op_service, effective_sensitivity="client_sensitive"
    )

    ceiling_double, ceiling_calls = _recording_ceiling("work_sensitive")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    above_ceiling_result = job_lifecycle.invoke_resume(
        operation_id=real_operation_id,
        idempotency_key="idem-above-ceiling-resume",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
        operations=op_service,
    )
    missing_result = job_lifecycle.invoke_resume(
        operation_id="op_does_not_exist_at_all_either",
        idempotency_key="idem-above-ceiling-resume-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
        operations=op_service,
    )

    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert above_ceiling_result.error["operation_id"] is None
    assert above_ceiling_result.error["receipt_ref"] is None
    assert "detail" not in above_ceiling_result.error

    assert missing_result.ok is False
    assert above_ceiling_result.error == missing_result.error
    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_operation_effective_sensitivity_of_fails_closed_on_missing_or_invalid_value() -> None:
    """Direct unit test of `_operation_effective_sensitivity_of` (P3
    hardening pass, HIGH-2 defect fix) -- the producer
    `_resolve_operation_workspace` relies on. A missing field, a
    non-string value, and an unrecognized label all fail closed to
    `SENSITIVITY_LEVELS[-1]` (`"client_sensitive"`, the STRICTEST label);
    only a genuinely valid member of `SENSITIVITY_LEVELS` passes through
    unchanged."""

    assert (
        job_lifecycle._operation_effective_sensitivity_of({}) == policy.SENSITIVITY_LEVELS[-1]
    )
    assert (
        job_lifecycle._operation_effective_sensitivity_of({"effective_sensitivity": 123})
        == policy.SENSITIVITY_LEVELS[-1]
    )
    assert (
        job_lifecycle._operation_effective_sensitivity_of(
            {"effective_sensitivity": "not_a_real_label"}
        )
        == policy.SENSITIVITY_LEVELS[-1]
    )
    assert job_lifecycle._operation_effective_sensitivity_of({"effective_sensitivity": "public"}) == "public"


def test_all_three_kinds_are_registered() -> None:
    assert base.get_adapter("job.status") is job_lifecycle.STATUS_ADAPTER
    assert base.get_adapter("job.cancel") is job_lifecycle.CANCEL_ADAPTER
    assert base.get_adapter("job.resume") is job_lifecycle.RESUME_ADAPTER
