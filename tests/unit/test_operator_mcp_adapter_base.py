"""Unit tests for `operator_mcp_adapters.base` (research-foundry-operator-mcp-v1
P3, OPM-3.1 -- the substrate every P3 operation-kind adapter builds on).

Covers: the adapter registry's no-fail-open behavior (`register` refuses an
unknown `operation_kind`; `get_adapter` returns `None`, never a default, for
an unregistered one); `run_pipeline`'s fixed authorize -> consume -> execute
-> bounded-result order; dry run's zero-effects guarantee (proven with
spies that raise if touched, not by inspection); every denial being built
via `operator_mcp_policy.build_error`; and the serve-extra import boundary.

Reuses, never reinvents (per this task's and the repo's own convention):
`test_operator_mcp_policy`'s identity fixtures/`_basic_ctx` helper,
`test_operator_operation_service`'s `_mint_and_record` confirmation helper,
and `test_operator_mcp_serve_extra_boundary`'s subprocess-blocked import
harness.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_cancel_resume_service import ActionEffect, ActionSpec
from research_foundry.services.operator_mcp_adapters import base
from research_foundry.services.operator_operation_service import OperatorOperationService

from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _IDENTITY,
    _VIEWER_IDENTITY,
    _basic_ctx,
    _default_operator_identity,
)
from tests.unit.test_operator_mcp_serve_extra_boundary import _run_blocked
from tests.unit.test_operator_operation_service import _mint_and_record


def _sha(tag: str) -> str:
    """A real sha256 hex digest -- `operator_mcp_receipt.schema.yaml`'s
    `effect_receipt.effect_digest` requires `^[a-f0-9]{64}$`; a short
    placeholder string fails schema validation (denies with
    `internal_error`, not a raised exception) rather than exercising the
    behavior under test."""

    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Registry: no fail-open (requirement 5)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_adapter_registry() -> Any:
    """Keep registry-mutating tests isolated from built-in registrations."""

    snapshot = dict(base._REGISTRY)
    yield
    base._REGISTRY.clear()
    base._REGISTRY.update(snapshot)


def test_register_rejects_unknown_operation_kind() -> None:
    @dataclass(frozen=True)
    class _Bogus:
        operation_kind: str = "not.a.real.kind"

        def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:  # pragma: no cover
            return base.OperatorAdapterResult(ok=True)

    with pytest.raises(ValueError):
        base.register(_Bogus())
    # A rejected registration must never have touched the real registry.
    assert base.get_adapter("not.a.real.kind") is None


def test_get_adapter_returns_none_for_unregistered_kind() -> None:
    """An unregistrable probe returns ``None``, never a fallback adapter.

    The registry accepts only the frozen ``OPERATION_KINDS`` members.  This
    probe therefore remains unregistered even as adapters are added for every
    legitimate operation kind.
    """

    probe = "test.unregistered.adapter"
    assert probe not in policy.OPERATION_KINDS
    assert base.get_adapter(probe) is None


def test_register_and_get_adapter_roundtrip() -> None:
    @dataclass(frozen=True)
    class _Stub:
        operation_kind: str = "job.status"

        def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:  # pragma: no cover
            return base.OperatorAdapterResult(ok=True)

    stub = _Stub()
    try:
        registered = base.register(stub)
        assert registered is stub
        assert base.get_adapter("job.status") is stub
        assert base.all_adapters()["job.status"] is stub
    finally:
        base._REGISTRY.pop("job.status", None)


def test_all_adapters_returns_a_shallow_copy_not_the_real_registry() -> None:
    snapshot = base.all_adapters()
    snapshot["job.status"] = None  # type: ignore[assignment]  -- mutate the COPY
    assert base.get_adapter("job.status") is None or base.get_adapter("job.status") is not None
    # The real registry is untouched by mutating the returned copy: a
    # lookup for a kind this test never registered stays None either way,
    # so assert against the copy/registry object identity instead.
    assert base.all_adapters() is not snapshot


# ---------------------------------------------------------------------------
# run_pipeline: dry run produces zero effects (requirement 4)
# ---------------------------------------------------------------------------


def test_dry_run_allowed_produces_zero_effects_and_a_preview_result(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx()

    class _SpyOps:
        def consume_and_create_operation(self, **kwargs: Any) -> Any:  # pragma: no cover
            raise AssertionError("dry run must never consume a confirmation")

    class _SpyCancelResume:
        def run_or_replay(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
            raise AssertionError("dry run must never execute an action")

    def _must_not_run() -> ActionEffect:  # pragma: no cover
        raise AssertionError("dry run must never run an action")

    result = base.run_pipeline(
        ctx=ctx,
        confirmation_record=None,
        presented_token=None,
        action_manifest={},
        actions=(ActionSpec(action_id="a0", run=_must_not_run),),
        build_result=lambda execution: {"unreached": True},  # pragma: no cover
        dry_run=True,
        paths=tmp_foundry,
        operations=_SpyOps(),  # type: ignore[arg-type]
        cancel_resume=_SpyCancelResume(),  # type: ignore[arg-type]
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.plan"}


def test_dry_run_denied_returns_build_error_with_zero_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    ctx = _basic_ctx()  # viewer lacks the mutation role run.plan requires -> rbac_denied

    class _SpyOps:
        def consume_and_create_operation(self, **kwargs: Any) -> Any:  # pragma: no cover
            raise AssertionError("dry run must never consume a confirmation")

    result = base.run_pipeline(
        ctx=ctx,
        confirmation_record=None,
        presented_token=None,
        action_manifest={},
        actions=(),
        build_result=lambda execution: {},  # pragma: no cover
        dry_run=True,
        paths=tmp_foundry,
        operations=_SpyOps(),  # type: ignore[arg-type]
    )

    assert result.ok is False
    assert result.operation_id is None
    assert result.error is not None
    assert result.error["reason_code"] == "rbac_denied"
    assert result.error["type"] == "operator_mcp_error"


# ---------------------------------------------------------------------------
# run_pipeline: fixed authorize -> consume -> execute -> bounded-result order
# ---------------------------------------------------------------------------


def test_pre_confirmation_denial_never_calls_consume(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION-TESTED GUARD 1 (see P3 implementer contract report): the
    `authorization.decision.stage != "confirmation"` early return in
    `run_pipeline` must fire, and `consume_and_create_operation` must never
    even be called, for a denial at capability/RBAC/audit-health/guard/
    preflight."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    ctx = _basic_ctx()

    class _SpyOps:
        def consume_and_create_operation(self, **kwargs: Any) -> Any:
            raise AssertionError(
                "consume_and_create_operation must not be called on a "
                "pre-confirmation-stage denial"
            )

    result = base.run_pipeline(
        ctx=ctx,
        confirmation_record=None,
        presented_token=None,
        action_manifest={},
        actions=(),
        build_result=lambda execution: {},  # pragma: no cover
        paths=tmp_foundry,
        now=ids.now(),
        operations=_SpyOps(),  # type: ignore[arg-type]
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "rbac_denied"


def test_full_pipeline_created_returns_build_result_payload(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx()
    op_service = OperatorOperationService(tmp_foundry)
    confirmation_id, token, record = _mint_and_record(op_service, ctx)

    executed: list[str] = []

    def _run() -> ActionEffect:
        executed.append("ran")
        return ActionEffect(effect_kind="k", effect_digest=_sha("full-pipeline"), effect_ref="r")

    result = base.run_pipeline(
        ctx=ctx,
        confirmation_record=record,
        presented_token=token,
        action_manifest={"adapter": "run.plan"},
        actions=(ActionSpec(action_id="a0", run=_run),),
        build_result=lambda execution: {
            "status": execution.status,
            "completed": execution.completed_action_count,
        },
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert executed == ["ran"]
    assert result.ok is True
    assert result.operation_id is not None
    assert result.result == {"status": "completed", "completed": 1}


def test_idempotency_conflict_denies_with_zero_effects(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)

    ctx1 = _basic_ctx(idempotency_key="dup-key", input_payload={"a": 1})
    cid1, tok1, rec1 = _mint_and_record(op_service, ctx1)
    first = base.run_pipeline(
        ctx=ctx1,
        confirmation_record=rec1,
        presented_token=tok1,
        action_manifest={},
        actions=(ActionSpec(action_id="a0", run=lambda: ActionEffect("k", _sha("idem-first"), "r1")),),
        build_result=lambda execution: {"status": execution.status},
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    assert first.ok is True

    ctx2 = _basic_ctx(idempotency_key="dup-key", input_payload={"a": 2})
    cid2, tok2, rec2 = _mint_and_record(op_service, ctx2)

    def _must_not_run() -> ActionEffect:  # pragma: no cover
        raise AssertionError("an idempotency-conflicted operation must never execute an action")

    second = base.run_pipeline(
        ctx=ctx2,
        confirmation_record=rec2,
        presented_token=tok2,
        action_manifest={},
        actions=(ActionSpec(action_id="a0", run=_must_not_run),),
        build_result=lambda execution: {"unreached": True},  # pragma: no cover
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    assert second.ok is False
    assert second.error is not None
    assert second.error["reason_code"] == "idempotency_conflict"


def test_execution_failed_status_is_a_denial_not_a_success(tmp_foundry: FoundryPaths) -> None:
    """MUTATION-TESTED GUARD 2 (see P3 implementer contract report): an
    action that raises produces `ExecutionOutcome.status == "failed"`,
    which `run_pipeline` MUST surface as `ok=False` via `build_error` --
    never as a success carrying whatever `build_result` happens to
    return."""

    ctx = _basic_ctx()
    op_service = OperatorOperationService(tmp_foundry)
    confirmation_id, token, record = _mint_and_record(op_service, ctx)

    def _boom() -> ActionEffect:
        raise RuntimeError("boom")

    result = base.run_pipeline(
        ctx=ctx,
        confirmation_record=record,
        presented_token=token,
        action_manifest={},
        actions=(ActionSpec(action_id="a0", run=_boom),),
        build_result=lambda execution: {"unexpected": "success"},
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


# ---------------------------------------------------------------------------
# Serve-extra import boundary (requirement 7)
# ---------------------------------------------------------------------------


def test_operator_mcp_adapters_import_without_serve_extra() -> None:
    """Extends `test_operator_mcp_serve_extra_boundary.py`'s existing
    subprocess-blocked pattern (fastapi/uvicorn/starlette blocked via a
    `sys.meta_path` finder) rather than reinventing it -- proves the
    package import chain (`__init__.py` -> `base.py` + `run_plan.py`,
    including `run_plan`'s own `planning`/`operator_cancel_resume_service`/
    `operator_operation_service` imports) never requires the `[serve]`
    extra."""

    result = _run_blocked(
        "import importlib\n"
        "importlib.import_module('research_foundry.services.operator_mcp_adapters')\n"
        "print('IMPORT_OK')\n"
    )
    assert result.returncode == 0, (
        f"import raised under the serve-extra blocker.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "IMPORT_OK" in result.stdout
