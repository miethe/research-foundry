"""Adversarial schema fixture matrix for the four Operator MCP contract
schemas (research-foundry-operator-mcp-v1 P1, OPM-1.1/1.3/1.4).

`tests/test_schema_validation.py`'s generic golden/negative harness already
covers "drop the first required field" for each of these four schemas (see
its `EXPECTED_SCHEMA_NAMES`/`_valid`/`_invalid`). This file covers the
RICHER adversarial matrix the P1 acceptance criteria specifically call out:
unknown operation kind, wildcard tool, expired/consumed confirmation shape
mismatches, oversized payload, raw-exception-shaped error, and unauthorized
extra fields -- using `jsonschema.Draft202012Validator` directly, mirroring
`test_schema_validation.py`'s own dedicated per-schema draft202012 tests
(e.g. `test_permission_record_schema_rejects_additional_properties`).
"""

from __future__ import annotations

from typing import Any

import jsonschema

from research_foundry.schemas import SchemaRegistry

_SHA = "a" * 64


def _errors(schema_name: str, instance: dict[str, Any]) -> list[str]:
    schema = SchemaRegistry().get(schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(instance)]


# ---------------------------------------------------------------------------
# operator_mcp_operation.schema.yaml
# ---------------------------------------------------------------------------


def _valid_operation() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "type": "operator_mcp_operation",
        "operation_kind": "run.plan",
        "actor": {"user_id": "alice", "workspace_id": "default", "roles": ["owner"]},
        "idempotency_key": "idem-1",
        "targets": [],
        "input_payload": {},
        "policy_snapshot_version": "policy-order-v1",
        "effective_sensitivity": "public",
        "requested_at": "2026-07-28T00:00:00Z",
    }


def test_operation_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_operation", _valid_operation())


def test_operation_rejects_unknown_operation_kind() -> None:
    instance = _valid_operation()
    instance["operation_kind"] = "shell.exec"
    assert _errors("operator_mcp_operation", instance)


def test_operation_rejects_wildcard_operation_kind() -> None:
    instance = _valid_operation()
    instance["operation_kind"] = "*"
    assert _errors("operator_mcp_operation", instance)


def test_operation_rejects_unknown_target_kind() -> None:
    instance = _valid_operation()
    instance["targets"] = [{"target_kind": "filesystem_path", "target_ref": "/etc/passwd"}]
    assert _errors("operator_mcp_operation", instance)


def test_operation_rejects_oversized_targets_array() -> None:
    instance = _valid_operation()
    instance["targets"] = [{"target_kind": "run", "target_ref": f"run_{i}"} for i in range(21)]
    assert _errors("operator_mcp_operation", instance)


def test_operation_rejects_oversized_input_payload() -> None:
    instance = _valid_operation()
    instance["input_payload"] = {f"field_{i}": i for i in range(33)}
    assert _errors("operator_mcp_operation", instance)


def test_operation_rejects_additional_properties() -> None:
    instance = _valid_operation()
    instance["unexpected_field"] = "nope"
    assert _errors("operator_mcp_operation", instance)


def test_operation_actor_rejects_additional_properties() -> None:
    instance = _valid_operation()
    instance["actor"]["extra"] = "nope"
    assert _errors("operator_mcp_operation", instance)


# ---------------------------------------------------------------------------
# operator_mcp_confirmation.schema.yaml
# ---------------------------------------------------------------------------


def _valid_confirmation(**overrides: Any) -> dict[str, Any]:
    instance = {
        "schema_version": "1.0",
        "type": "operator_mcp_confirmation",
        "confirmation_id": f"opc_{_SHA}",
        "token_digest": _SHA,
        "actor": {"user_id": "alice", "workspace_id": "default", "roles": ["owner"]},
        "effective_sensitivity": "public",
        "operation_kind": "run.plan",
        "canonical_input_digest": _SHA,
        "idempotency_key": "idem-1",
        "policy_snapshot_version": "policy-order-v1",
        "targets": [],
        "status": "issued",
        "issued_at": "2026-07-28T00:00:00Z",
        "expires_at": "2026-07-28T00:05:00Z",
        "consumed_at": None,
        "consumed_by_operation_id": None,
    }
    instance.update(overrides)
    return instance


def test_confirmation_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_confirmation", _valid_confirmation())


def test_confirmation_expired_status_is_structurally_valid() -> None:
    """Schema-level: `status: expired` never requires consumed_at/
    consumed_by_operation_id (the TTL check itself is policy-level, see
    `operator_mcp_policy.verify_confirmation`)."""

    instance = _valid_confirmation(status="expired")
    assert not _errors("operator_mcp_confirmation", instance)


def test_confirmation_consumed_status_requires_consumed_fields() -> None:
    instance = _valid_confirmation(status="consumed")  # consumed_at/consumed_by_operation_id still null
    assert _errors("operator_mcp_confirmation", instance)


def test_confirmation_consumed_status_with_fields_passes() -> None:
    instance = _valid_confirmation(
        status="consumed",
        consumed_at="2026-07-28T00:01:00Z",
        consumed_by_operation_id=f"opm_{_SHA}",
    )
    assert not _errors("operator_mcp_confirmation", instance)


def test_confirmation_issued_status_rejects_nonnull_consumed_fields() -> None:
    instance = _valid_confirmation(status="issued", consumed_at="2026-07-28T00:01:00Z")
    assert _errors("operator_mcp_confirmation", instance)


def test_confirmation_rejects_unknown_operation_kind() -> None:
    instance = _valid_confirmation(operation_kind="writeback.execute")
    assert _errors("operator_mcp_confirmation", instance)


def test_confirmation_rejects_malformed_token_digest() -> None:
    instance = _valid_confirmation(token_digest="not-a-hex-digest")
    assert _errors("operator_mcp_confirmation", instance)


def test_confirmation_rejects_additional_properties() -> None:
    instance = _valid_confirmation()
    instance["unexpected_field"] = "nope"
    assert _errors("operator_mcp_confirmation", instance)


# ---------------------------------------------------------------------------
# operator_mcp_receipt.schema.yaml (discriminated union)
# ---------------------------------------------------------------------------


def _valid_operation_receipt(**overrides: Any) -> dict[str, Any]:
    instance = {
        "schema_version": "1.0",
        "kind": "operation_receipt",
        "operation_id": f"opm_{_SHA}",
        "workspace_id": "default",
        "operation_kind": "run.plan",
        "status": "accepted",
        "idempotency_key": "idem-1",
        "canonical_input_digest": _SHA,
        "generated_at": "2026-07-28T00:00:00Z",
    }
    instance.update(overrides)
    return instance


def _valid_terminal_receipt(**overrides: Any) -> dict[str, Any]:
    instance = {
        "schema_version": "1.0",
        "kind": "terminal_receipt",
        "operation_id": f"opm_{_SHA}",
        "workspace_id": "default",
        "operation_kind": "run.plan",
        "status": "completed",
        "effect_receipt_refs": [],
        "action_count_total": 1,
        "action_count_completed": 1,
        "denial_reason_code": None,
        "audit_delivery": {"status": "delivered", "audit_event_id": "audit_1"},
        "completed_at": "2026-07-28T00:00:00Z",
    }
    instance.update(overrides)
    return instance


def _valid_checkpoint(**overrides: Any) -> dict[str, Any]:
    instance = {
        "schema_version": "1.0",
        "kind": "checkpoint",
        "operation_id": f"opm_{_SHA}",
        "status": "pending",
        "next_action_index": 1,
        "completed_action_count": 1,
        "total_action_count": 3,
        "non_cancelable": False,
        "updated_at": "2026-07-28T00:00:00Z",
    }
    instance.update(overrides)
    return instance


def test_receipt_operation_receipt_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_operation_receipt())


def test_receipt_terminal_receipt_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_terminal_receipt())


def test_receipt_checkpoint_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_checkpoint())


def test_receipt_rejects_unknown_kind_discriminator() -> None:
    instance = _valid_operation_receipt(kind="not_a_real_kind")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_rejects_missing_kind_discriminator() -> None:
    instance = _valid_operation_receipt()
    del instance["kind"]
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_denied_requires_reason_code() -> None:
    instance = _valid_terminal_receipt(status="denied")  # denial_reason_code still None
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_denied_with_reason_code_passes() -> None:
    instance = _valid_terminal_receipt(status="denied", denial_reason_code="guard_blocked")
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_completed_forbids_reason_code() -> None:
    instance = _valid_terminal_receipt(status="completed", denial_reason_code="guard_blocked")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_checkpoint_converged_requires_null_next_action_index() -> None:
    instance = _valid_checkpoint(status="converged")  # next_action_index still 1, non_cancelable still False-ok but index wrong
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_checkpoint_converged_with_null_next_action_passes() -> None:
    instance = _valid_checkpoint(status="converged", next_action_index=None)
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_effect_kind_rejects_non_snake_case() -> None:
    instance = {
        "schema_version": "1.0",
        "kind": "effect_receipt",
        "operation_id": f"opm_{_SHA}",
        "action_id": "action-1",
        "effect_kind": "NotSnakeCase!",
        "effect_digest": _SHA,
        "effect_ref": "run_demo",
        "generated_at": "2026-07-28T00:00:00Z",
    }
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_rejects_additional_properties() -> None:
    instance = _valid_operation_receipt()
    instance["unexpected_field"] = "nope"
    assert _errors("operator_mcp_receipt", instance)


# ---------------------------------------------------------------------------
# operator_mcp_error.schema.yaml
# ---------------------------------------------------------------------------


def _valid_error(**overrides: Any) -> dict[str, Any]:
    instance = {
        "schema_version": "1.0",
        "type": "operator_mcp_error",
        "reason_code": "identity_denied",
        "message": "The requested operation could not be authorized for this actor/workspace.",
        "retryable": False,
        "operation_id": None,
        "receipt_ref": None,
        "occurred_at": "2026-07-28T00:00:00Z",
    }
    instance.update(overrides)
    return instance


def test_error_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_error", _valid_error())


def test_error_with_bounded_detail_passes() -> None:
    instance = _valid_error(detail="missing required target kinds: ['run']")
    assert not _errors("operator_mcp_error", instance)


def test_error_rejects_unknown_reason_code() -> None:
    instance = _valid_error(reason_code="totally_made_up_reason")
    assert _errors("operator_mcp_error", instance)


def test_error_rejects_raw_exception_shaped_message() -> None:
    instance = _valid_error(
        message='Traceback (most recent call last):\n  File "/x/y.py", line 12, in foo'
    )
    assert _errors("operator_mcp_error", instance)


def test_error_rejects_raw_exception_shaped_detail() -> None:
    instance = _valid_error(detail="ValueError raised in site-packages/foo/bar.py")
    assert _errors("operator_mcp_error", instance)


def test_error_rejects_oversized_message() -> None:
    instance = _valid_error(message="x" * 301)
    assert _errors("operator_mcp_error", instance)


def test_error_rejects_oversized_detail() -> None:
    instance = _valid_error(detail="x" * 501)
    assert _errors("operator_mcp_error", instance)


def test_error_rejects_additional_properties() -> None:
    instance = _valid_error()
    instance["stack_trace"] = "should never exist"
    assert _errors("operator_mcp_error", instance)


def test_error_operation_id_pattern_enforced() -> None:
    instance = _valid_error(operation_id="not-a-valid-operation-id")
    assert _errors("operator_mcp_error", instance)


def test_error_operation_id_valid_pattern_passes() -> None:
    instance = _valid_error(operation_id=f"opm_{_SHA}")
    assert not _errors("operator_mcp_error", instance)
