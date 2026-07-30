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
# R5-NB-3 / Part B: pin the frozen DUR-1 contract text (schema half).
# ---------------------------------------------------------------------------

#: R5-NB-3 (round 5, fixed): round 5's mutation sweep found that DELETING the
#: entire BINDING CHECK clause (b) from this schema's frozen DUR-1
#: description -- the exact prose P2's closeout is graded against -- was NOT
#: DETECTED by any test: exit 0, zero failures. No test anywhere pinned this
#: frozen normative text; grepping both operator-mcp test files for `DUR-1`/
#: `BINDING CHECK`/`compare-and-swap` found one hit, in a docstring, not an
#: assertion. This asserts the REQUIRED PREDICATE CLAUSES are present --
#: deliberately NOT a byte-for-byte text comparison, which would be brittle
#: to ordinary copy-edits that don't change the normative content -- so
#: silently weakening (deleting a clause, softening "MUST" to "should",
#: dropping the compare-and-swap framing) fails this test while a harmless
#: rewording does not.
_DUR1_REQUIRED_CLAUSES: tuple[str, ...] = (
    "compare-and-swap",
    "GUARDED BY",
    "CLAMPED-EXPIRY CHECK",
    "BINDING CHECK",
    "byte-identical",
    "MUST NOT execute",
)


def test_confirmation_schema_pins_the_frozen_dur1_binding_predicate() -> None:
    """R5-NB-3 (schema half): M9b (deleting the schema-side BINDING CHECK
    clause) previously went undetected -- see `_DUR1_REQUIRED_CLAUSES`'s
    docstring above. The mirrored module-docstring half is pinned by
    `test_operator_mcp_policy.py::test_dur1_binding_predicate_is_pinned_in_module_docstring`."""

    schema = SchemaRegistry().get("operator_mcp_confirmation")
    description = schema.get("description", "")
    assert description, "operator_mcp_confirmation.schema.yaml lost its top-level description"
    for clause in _DUR1_REQUIRED_CLAUSES:
        assert clause in description, (
            f"DUR-1 predicate clause missing from the confirmation schema's "
            f"description: {clause!r}"
        )


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


def _valid_action_receipt(**overrides: Any) -> dict[str, Any]:
    """BLOCK-2 (round 4 gate): `action_receipt` previously had ZERO test
    coverage of any kind in this file (`grep -n action_receipt
    tests/unit/test_operator_mcp_schemas.py` returned no matches) -- the
    only one of the five `$defs` with no golden instance, no negative
    fixture, and no `_valid_*` helper. Added alongside closing
    `reason_code` to the same enum `terminal_receipt.denial_reason_code`
    uses."""

    instance = {
        "schema_version": "1.0",
        "kind": "action_receipt",
        "operation_id": f"opm_{_SHA}",
        "action_id": "action-1",
        "action_index": 0,
        "status": "completed",
        "attempt_ref": "attempt-1",
        "started_at": "2026-07-28T00:00:00Z",
        "completed_at": "2026-07-28T00:00:01Z",
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
        "workspace_id": "default",
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


def test_receipt_action_receipt_golden_instance_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_action_receipt())


def test_receipt_action_receipt_with_closed_reason_code_passes() -> None:
    instance = _valid_action_receipt(status="failed", reason_code="rbac_denied")
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_action_reason_code_rejects_value_outside_closed_enum() -> None:
    """BLOCK-2 (round 4 gate) negative fixture: `action_receipt.reason_code`
    was the exact open `type: [string, "null"], maxLength: 64` shape
    NEW-20 (round 3) closed on its sibling `terminal_receipt.denial_reason_code`
    but left open here, one `$def` above. An arbitrary code must now be
    REJECTED, mirroring `test_receipt_denial_reason_code_rejects_value_outside_closed_enum`."""

    instance = _valid_action_receipt(status="failed", reason_code="totally_made_up_code")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_reason_code_rejects_near_miss_of_a_real_code() -> None:
    instance = _valid_action_receipt(status="failed", reason_code="guard_blocked_extra")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_failed_requires_reason_code_key_to_be_present() -> None:
    """R5-BLOCK-3 (round 5 gate): `action_receipt` had NO presence coupling
    between `status` and `reason_code` at all -- `status: failed` with
    `reason_code` entirely ABSENT validated, sidestepping BLOCK-2's closed
    enum exactly the way BLOCK-3 (round 4) closed for the sibling
    `terminal_receipt.denial_reason_code` one `$def` below. Mirrors
    `test_receipt_terminal_denied_requires_reason_code_key_to_be_present`."""

    instance = _valid_action_receipt(status="failed")  # reason_code absent
    assert "reason_code" not in instance
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_skipped_requires_reason_code_key_to_be_present() -> None:
    instance = _valid_action_receipt(status="skipped")  # reason_code absent
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_failed_with_null_reason_code_rejected() -> None:
    """The presence-key case above cannot distinguish "absent" from "present
    and null" (dropping a key is not the same JSON Schema condition as the
    key being present with value `null`) -- this pins the null-value case
    specifically, mirroring `test_receipt_terminal_denied_requires_reason_code`."""

    instance = _valid_action_receipt(status="failed", reason_code=None)
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_failed_with_reason_code_passes() -> None:
    instance = _valid_action_receipt(status="failed", reason_code="rbac_denied")
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_completed_forbids_reason_code() -> None:
    """R5-BLOCK-3: the other direction -- `status: completed` with a
    NON-NULL `reason_code` (a "completed" action carrying a denial cause)
    previously validated too, the exact shape `terminal_receipt`'s own
    `completed`/`canceled` branch already forbade."""

    instance = _valid_action_receipt(status="completed", reason_code="guard_blocked")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_completed_with_absent_reason_code_still_passes() -> None:
    """`reason_code` is NOT in `action_receipt`'s top-level `required` list
    (unlike `terminal_receipt.denial_reason_code`, which is required and
    nullable) -- the common case of a completed action with no reason_code
    key at all must keep validating after the R5-BLOCK-3 fix."""

    instance = _valid_action_receipt(status="completed")
    assert "reason_code" not in instance
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_completed_with_null_reason_code_passes() -> None:
    instance = _valid_action_receipt(status="completed", reason_code=None)
    assert not _errors("operator_mcp_receipt", instance)


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


def test_receipt_terminal_denied_requires_reason_code_key_to_be_present() -> None:
    """BLOCK-3 (round 4 gate): the test above only pins the NULL case (the
    key present with value `null`). The `allOf` `then` branch previously
    had no `required: [denial_reason_code]`, so a `denied` receipt with the
    KEY ABSENT ENTIRELY (not merely null) validated -- sidestepping the
    whole NEW-20/BLOCK-2 enum. This pins the absent-key case specifically,
    which the null-case test above cannot (dropping the key is not the same
    JSON Schema condition as the key being present and null)."""

    instance = _valid_terminal_receipt(status="denied")
    del instance["denial_reason_code"]
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_denied_with_reason_code_passes() -> None:
    instance = _valid_terminal_receipt(status="denied", denial_reason_code="guard_blocked")
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_completed_forbids_reason_code() -> None:
    instance = _valid_terminal_receipt(status="completed", denial_reason_code="guard_blocked")
    assert _errors("operator_mcp_receipt", instance)


def test_audit_delivery_detail_rejects_a_raw_traceback() -> None:
    """NEW-21: `audit_delivery.detail`'s natural producer is `str(exc)`, and
    the field previously carried no traceback guard at all. A raw traceback
    must now fail validation."""

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = {
        "status": "unavailable",
        "audit_event_id": None,
        "detail": 'Traceback (most recent call last):\n  File "/x/y.py", line 12, in write\n    raise OSError',
    }
    assert _errors("operator_mcp_receipt", instance)


def test_audit_delivery_detail_rejects_site_packages_path() -> None:
    """The guard mirrors the error envelope's, which also blocks
    `site-packages` paths (filesystem-layout disclosure)."""

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = {
        "status": "degraded",
        "audit_event_id": None,
        "detail": "failed in /opt/venv/lib/python3.14/site-packages/foo/bar.py",
    }
    assert _errors("operator_mcp_receipt", instance)


def test_audit_delivery_detail_rejects_absolute_filesystem_path() -> None:
    """BLOCK-1 (round 4 gate): the schema-level guard also flags a BARE
    absolute filesystem path with NO traceback framing at all -- exactly
    the shape a real `str(exc)` naturally produces (e.g. `OSError`/
    `PermissionError` messages) and that the pre-BLOCK-1 traceback-only
    pattern missed entirely (empirically: it validated verbatim)."""

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = {
        "status": "unavailable",
        "audit_event_id": None,
        "detail": "audit store unreachable at /var/secrets/db.sock",
    }
    assert _errors("operator_mcp_receipt", instance)


def test_audit_delivery_audit_event_id_rejects_absolute_filesystem_path() -> None:
    """R5-BLOCK-1 (round 5 gate): `audit_event_id` is `detail`'s SIBLING
    property, one property over, and previously carried NO pattern guard at
    all -- the exact BLOCK-1 shape recurring one field later. A bare
    absolute path with no traceback framing (real `str(exc)` shape) must
    now be rejected, mirroring `test_audit_delivery_detail_rejects_absolute_filesystem_path`."""

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = {
        "status": "unavailable",
        "audit_event_id": "/var/secrets/db.sock",
    }
    assert _errors("operator_mcp_receipt", instance)


def test_audit_delivery_audit_event_id_rejects_raw_traceback() -> None:
    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = {
        "status": "unavailable",
        "audit_event_id": 'Traceback (most recent call last):\n  File "/x/y.py", line 1',
    }
    assert _errors("operator_mcp_receipt", instance)


def test_audit_delivery_audit_event_id_null_still_passes() -> None:
    """Regression check for the JSON-Schema `not: {pattern: ...}` gotcha
    this fix hit: applying a bare `not: {pattern: ...}` to a NULLABLE field
    incorrectly rejects `null` itself (`pattern` is vacuously satisfied by a
    non-string instance, so `not` of that inverts to a rejection) -- the
    guard here MUST include `type: string` inside the `not` sub-schema so a
    genuinely absent/null `audit_event_id` (a normal, common case) keeps
    validating."""

    instance = _valid_terminal_receipt(status="completed")
    instance["audit_delivery"] = {"status": "delivered", "audit_event_id": None}
    assert not _errors("operator_mcp_receipt", instance)


def test_audit_delivery_audit_event_id_genuine_uuid_passes() -> None:
    instance = _valid_terminal_receipt(status="completed")
    instance["audit_delivery"] = {
        "status": "delivered",
        "audit_event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    }
    assert not _errors("operator_mcp_receipt", instance)


def test_audit_delivery_builder_redacts_path_shaped_audit_event_id() -> None:
    """R5-BLOCK-1: code-level closure companion to the schema-level negative
    fixtures above -- `build_audit_delivery` now routes `audit_event_id`
    through the same `_redact_and_bound` pass `detail` uses, so a caller
    that passes a path-shaped `audit_event_id` gets the SAME safe marker
    back, never the raw path."""

    from research_foundry.services.operator_mcp_policy import build_audit_delivery

    unsafe_id = "/var/secrets/db.sock"
    block = build_audit_delivery("unavailable", audit_event_id=unsafe_id)
    assert block["audit_event_id"] != unsafe_id
    assert "/var/secrets/db.sock" not in (block["audit_event_id"] or "")

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = block
    assert not _errors("operator_mcp_receipt", instance), block


def test_receipt_operation_receipt_workspace_id_rejects_path_shaped_value() -> None:
    """R5-BLOCK-1: `workspace_id` (`operation_receipt` and its identically-
    shaped sibling `terminal_receipt.workspace_id`) previously had no
    pattern guard at all."""

    instance = _valid_operation_receipt(workspace_id="/etc/passwd")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_receipt_workspace_id_rejects_path_shaped_value() -> None:
    instance = _valid_terminal_receipt(workspace_id="/etc/passwd")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_action_id_rejects_path_shaped_value() -> None:
    """R5-BLOCK-1: `action_id` appears in BOTH `action_receipt` and
    `effect_receipt` with the identical open-string shape -- both siblings
    need the same fix."""

    instance = _valid_action_receipt(action_id="/home/bob/.ssh/id_ed25519")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_effect_receipt_action_id_rejects_path_shaped_value() -> None:
    instance = {
        "schema_version": "1.0",
        "kind": "effect_receipt",
        "operation_id": f"opm_{_SHA}",
        "action_id": "/home/bob/.ssh/id_ed25519",
        "effect_kind": "source_card_created",
        "effect_digest": _SHA,
        "effect_ref": "run_demo",
        "generated_at": "2026-07-28T00:00:00Z",
    }
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_attempt_ref_rejects_path_shaped_value() -> None:
    instance = _valid_action_receipt(attempt_ref="/opt/agent/state/attempt.log")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_checkpoint_workspace_id_rejects_path_shaped_value() -> None:
    """NB-11 item 1: `checkpoint` previously had no `workspace_id` at all."""

    instance = _valid_checkpoint(workspace_id="/etc/passwd")
    assert _errors("operator_mcp_receipt", instance)


# ---------------------------------------------------------------------------
# P2R-BLOCK-1: operation_receipt.idempotency_key
# ---------------------------------------------------------------------------


def test_receipt_operation_receipt_idempotency_key_rejects_path_shaped_value() -> None:
    """P2R-BLOCK-1: `idempotency_key` was a completely unguarded open
    string, one property below the newly-guarded `workspace_id` in the
    SAME `$def` -- the fourth instance of the fix-the-layer-below sibling
    class this file has produced every round examined."""

    instance = _valid_operation_receipt(idempotency_key="/etc/passwd")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_idempotency_key_rejects_traceback_shaped_value() -> None:
    instance = _valid_operation_receipt(idempotency_key="Traceback: File x.py")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_idempotency_key_golden_value_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_operation_receipt())


def test_receipt_operation_receipt_idempotency_key_matches_operation_schema_pattern() -> None:
    """Parity check (empirical, not reasoned): the receipt's
    `idempotency_key` must be closed to the IDENTICAL pattern
    `operator_mcp_operation.schema.yaml`'s own `idempotency_key` uses,
    since this field is defined to echo that exact source field (single
    source of truth). Compares the live schema strings directly rather
    than asserting behavior on a handful of sample instances."""

    receipt_schema = SchemaRegistry().get("operator_mcp_receipt")
    operation_schema = SchemaRegistry().get("operator_mcp_operation")
    receipt_pattern = receipt_schema["$defs"]["operation_receipt"]["properties"]["idempotency_key"][
        "pattern"
    ]
    operation_pattern = operation_schema["properties"]["idempotency_key"]["pattern"]
    assert receipt_pattern == operation_pattern


# ---------------------------------------------------------------------------
# NB-11 item 2: operation_receipt.denial_reason_code
# ---------------------------------------------------------------------------


def test_receipt_operation_receipt_denied_requires_reason_code_key_to_be_present() -> None:
    instance = _valid_operation_receipt(status="denied")  # denial_reason_code absent entirely
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_denied_with_null_reason_code_rejected() -> None:
    instance = _valid_operation_receipt(status="denied", denial_reason_code=None)
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_denied_with_reason_code_passes() -> None:
    instance = _valid_operation_receipt(status="denied", denial_reason_code="guard_blocked")
    assert not _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_accepted_forbids_reason_code() -> None:
    instance = _valid_operation_receipt(status="accepted", denial_reason_code="guard_blocked")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_accepted_with_absent_reason_code_still_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_operation_receipt())


def test_receipt_operation_receipt_accepted_with_null_reason_code_passes() -> None:
    instance = _valid_operation_receipt(status="accepted", denial_reason_code=None)
    assert not _errors("operator_mcp_receipt", instance)


# ---------------------------------------------------------------------------
# P2R-NB-1: checkpoint next_action_index / status bidirectional coupling
# ---------------------------------------------------------------------------


def test_receipt_checkpoint_pending_with_null_next_action_index_rejected() -> None:
    """P2R-NB-1: previously unenforced -- a `pending` checkpoint with
    `next_action_index: null` validated cleanly, contradicting this
    `$def`'s own docstring ("null only when status is converged")."""

    instance = _valid_checkpoint(status="pending", next_action_index=None)
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_checkpoint_pending_with_non_null_next_action_index_passes() -> None:
    assert not _errors("operator_mcp_receipt", _valid_checkpoint())


def test_receipt_checkpoint_converged_rejects_non_cancelable_true() -> None:
    """P2R-NB-4: the converged branch's `non_cancelable: const false`
    coupling had no negative fixture -- only `next_action_index` was
    varied by the existing converged-branch tests."""

    instance = _valid_checkpoint(status="converged", next_action_index=None, non_cancelable=True)
    assert _errors("operator_mcp_receipt", instance)


# ---------------------------------------------------------------------------
# P2R-NB-3: regression-detection gap -- operation_id / operation_kind /
# status negative fixtures across all five $defs.
# ---------------------------------------------------------------------------


def test_receipt_operation_receipt_operation_id_rejects_malformed_value() -> None:
    instance = _valid_operation_receipt(operation_id="not-an-opm-id")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_operation_id_rejects_malformed_value() -> None:
    instance = _valid_action_receipt(operation_id="not-an-opm-id")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_effect_receipt_operation_id_rejects_malformed_value() -> None:
    instance = {
        "schema_version": "1.0",
        "kind": "effect_receipt",
        "operation_id": "not-an-opm-id",
        "action_id": "action-1",
        "effect_kind": "source_card_created",
        "effect_digest": _SHA,
        "effect_ref": "run_demo",
        "generated_at": "2026-07-28T00:00:00Z",
    }
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_checkpoint_operation_id_rejects_malformed_value() -> None:
    instance = _valid_checkpoint(operation_id="not-an-opm-id")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_receipt_operation_id_rejects_malformed_value() -> None:
    instance = _valid_terminal_receipt(operation_id="not-an-opm-id")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_operation_kind_rejects_unknown_value() -> None:
    instance = _valid_operation_receipt(operation_kind="shell.exec")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_receipt_operation_kind_rejects_unknown_value() -> None:
    instance = _valid_terminal_receipt(operation_kind="shell.exec")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_operation_receipt_status_rejects_unknown_value() -> None:
    instance = _valid_operation_receipt(status="bogus_status")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_action_receipt_status_rejects_unknown_value() -> None:
    instance = _valid_action_receipt(status="bogus_status")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_checkpoint_status_rejects_unknown_value() -> None:
    instance = _valid_checkpoint(status="bogus_status")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_terminal_receipt_status_rejects_unknown_value() -> None:
    instance = _valid_terminal_receipt(status="bogus_status")
    assert _errors("operator_mcp_receipt", instance)


# NOTE (P2R-NB-3, date-time fields): NOT extended to `generated_at`/
# `started_at`/`completed_at`/`updated_at`. Confirmed empirically that this
# repo's `jsonschema.Draft202012Validator` usage -- both here (`_errors`
# above) and in `research_foundry.schemas.SchemaRegistry.validate` -- never
# attaches a `format_checker`, so `format: date-time` is annotation-only and
# NOT enforced (`grep -rn "format_checker\|FormatChecker"` across
# `tests/unit/test_operator_mcp_schemas.py`, `tests/test_schema_validation.py`,
# and `src/research_foundry/schemas.py` returns zero hits). A malformed
# `generated_at` value validates today regardless of this schema's content,
# so a "negative fixture" here would be dishonest -- it would assert
# behavior this schema cannot currently provide. Wiring a `FormatChecker`
# is a validator-plumbing change outside this schema file's scope; flagged
# for OPM-2.3/a follow-up rather than faked here.


def test_audit_delivery_builder_never_leaks_exception_derived_content() -> None:
    """BLOCK-1 (round 4 gate): supersedes the round-3 producer test, which
    only asserted the SCHEMA validates for a real traceback -- schema
    validity does not prove the sensitive CONTENT is gone. It empirically
    was not: `build_audit_delivery`'s pre-BLOCK-1 free-text `detail` let a
    bare `str(exc)` path (no traceback framing) straight through
    unredacted, because `_TRACEBACK_LIKE` never matched it.

    `detail` is no longer free text at all -- `detail_code` selects from a
    closed, fixed table, so an exception's own text (a full traceback, an
    embedded path, the exception message itself) has NO channel to reach
    the output. This test asserts the CONTENT is absent, not merely that
    the result happens to validate."""

    import traceback as _traceback

    from research_foundry.services.operator_mcp_policy import build_audit_delivery

    try:
        raise OSError("audit store unreachable at /var/secrets/db.sock")
    except OSError as exc:
        raw_traceback = _traceback.format_exc()
        raw_message = str(exc)

    assert "Traceback" in raw_traceback, "precondition: the raw text really is a traceback"
    assert "/var/secrets/db.sock" in raw_message, "precondition: the raw message embeds a path"

    block = build_audit_delivery("unavailable", audit_event_id=None, detail_code="write_failed")
    instance = _valid_terminal_receipt(status="denied", denial_reason_code="internal_error")
    instance["audit_delivery"] = block

    produced_detail = block.get("detail", "")
    assert raw_traceback not in produced_detail
    assert raw_message not in produced_detail
    assert "/var/secrets/db.sock" not in produced_detail
    assert not _errors("operator_mcp_receipt", instance), block


def test_audit_delivery_builder_rejects_unknown_status_and_overlong_event_id() -> None:
    """Fail-loud on caller programming errors rather than emitting a
    silently-malformed block (same convention as `build_error`)."""

    import pytest as _pytest

    from research_foundry.services.operator_mcp_policy import build_audit_delivery

    with _pytest.raises(ValueError):
        build_audit_delivery("totally_unknown_status")
    with _pytest.raises(ValueError):
        build_audit_delivery("delivered", audit_event_id="x" * 129)


def test_audit_delivery_builder_rejects_unknown_detail_code() -> None:
    """BLOCK-1: `detail_code` is a closed vocabulary -- an unknown code is a
    caller programming error, same fail-loud convention as `status`/
    `audit_event_id` above."""

    import pytest as _pytest

    from research_foundry.services.operator_mcp_policy import build_audit_delivery

    with _pytest.raises(ValueError):
        build_audit_delivery("unavailable", detail_code="totally_made_up_code")


def test_receipt_denial_reason_code_rejects_value_outside_closed_enum() -> None:
    """NEW-20 negative fixture: `denial_reason_code` was declared as an OPEN
    string (`type: [string, "null"]`, `maxLength: 64`) while both the schema
    description and the phase completion note claimed a closed enum. An
    arbitrary code must now be REJECTED."""

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="totally_made_up_code")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_denial_reason_code_rejects_near_miss_of_a_real_code() -> None:
    """A near-miss (valid code with a suffix) must also be rejected -- this is
    what an open `maxLength: 64` string would have silently accepted."""

    instance = _valid_terminal_receipt(status="denied", denial_reason_code="guard_blocked_extra")
    assert _errors("operator_mcp_receipt", instance)


def test_receipt_denial_reason_code_enum_matches_code_closed_reason_codes() -> None:
    """Drift guard: the schema's closed enum and
    `operator_mcp_policy.CLOSED_REASON_CODES` are duplicated by value, so pin
    them to each other. If someone adds a reason code in one place only, this
    fails instead of silently reopening the vocabulary.

    BLOCK-2 (round 4 gate): this guard previously read ONLY
    `terminal_receipt.denial_reason_code` -- `action_receipt.reason_code`,
    the exact sibling field NEW-20 (round 3) forgot to close, was
    unguarded. NB-11 item 2 (P2 pre-persistence re-attack gate): extended
    again to cover `operation_receipt.denial_reason_code`, the newly-added
    THIRD copy of this same enum. Now asserts all three fields against
    `CLOSED_REASON_CODES`."""

    from research_foundry.services.operator_mcp_policy import CLOSED_REASON_CODES

    schema = SchemaRegistry().get("operator_mcp_receipt")

    terminal = schema["$defs"]["terminal_receipt"]["properties"]["denial_reason_code"]
    terminal_codes = {c for c in terminal["enum"] if c is not None}
    assert None in terminal["enum"], "null must remain a member (completed/canceled require it)"
    assert terminal_codes == set(CLOSED_REASON_CODES)

    action = schema["$defs"]["action_receipt"]["properties"]["reason_code"]
    action_codes = {c for c in action["enum"] if c is not None}
    assert None in action["enum"], "null must remain a member (reason_code is optional)"
    assert action_codes == set(CLOSED_REASON_CODES)

    operation = schema["$defs"]["operation_receipt"]["properties"]["denial_reason_code"]
    operation_codes = {c for c in operation["enum"] if c is not None}
    assert None in operation["enum"], "null must remain a member (only denied requires non-null)"
    assert operation_codes == set(CLOSED_REASON_CODES)


def test_receipt_every_closed_reason_code_is_accepted() -> None:
    """The enum must not be narrower than the code's vocabulary either -- every
    real reason code has to validate on a denied receipt."""

    from research_foundry.services.operator_mcp_policy import CLOSED_REASON_CODES

    for code in sorted(CLOSED_REASON_CODES):
        instance = _valid_terminal_receipt(status="denied", denial_reason_code=code)
        assert not _errors("operator_mcp_receipt", instance), f"{code} should validate"


def test_receipt_operation_receipt_every_closed_reason_code_is_accepted() -> None:
    """NB-11 item 2: same coverage as the terminal_receipt test above, for
    the newly-added operation_receipt.denial_reason_code."""

    from research_foundry.services.operator_mcp_policy import CLOSED_REASON_CODES

    for code in sorted(CLOSED_REASON_CODES):
        instance = _valid_operation_receipt(status="denied", denial_reason_code=code)
        assert not _errors("operator_mcp_receipt", instance), f"{code} should validate"


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


def test_error_rejects_absolute_filesystem_path_in_detail() -> None:
    """BLOCK-1 (round 4 gate): the schema guard also flags a BARE absolute
    filesystem path with no traceback framing -- the shape a real
    `str(exc)` naturally produces (see the mirrored receipt-schema test)."""

    instance = _valid_error(detail="failed to read /home/bob/.ssh/id_ed25519")
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
