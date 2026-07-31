"""End-to-end `operation.preflight` -> execute coverage through the REAL
registered MCP route (`server.call_tool`), M2 fix cycle 1 Leg 1, task F1.5.

**Why this file exists (orchestrator adjudication, `m2-fix-contract.md`).**
Every M2 test before this fix cycle either drove an adapter's `invoke*`
directly with a hand-built `PolicyContext`/confirmation (bypassing the
transport entirely), or drove `server.call_tool` for a SINGLE call in
isolation (e.g. `operation.preflight` alone, or an operation tool alone
with a forged/absent confirmation). Nothing ever ran
**preflight -> (persist) -> execute** as a SEQUENCE through the registered
route. That gap is exactly what let TERRA-1 (preflight never persists its
own minted confirmation), TERRA-2 (`writeback.preview` preflight always
drops `writeback_targets`), and TERRA-3/TERRA-4 (canonical-payload/DI-
parameter gaps) go undetected by every prior green suite.

Every test below is run against CURRENT HEAD (post-fix); the completion
note records the pre-fix failure proof (a scratch copy of `server.py`
reverted to strip F1.1/F1.2, run against this SAME file, per contract hard
boundary 6 -- never `git stash`).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

from research_foundry.operator_mcp import server as server_module  # noqa: E402
from research_foundry.paths import FoundryPaths  # noqa: E402
from research_foundry.services import operator_mcp_policy as policy  # noqa: E402
from research_foundry.services import writeback as writeback_module  # noqa: E402
from research_foundry.services.operator_mcp_adapters import run_plan, writeback_preview  # noqa: E402
from research_foundry.yamlio import dump_yaml, load_yaml  # noqa: E402

from tests.integration.test_operator_mcp_writeback_preview import (  # noqa: E402
    _IDENTITY,
    _build_run,
)
from tests.test_planning import _make_intent  # noqa: E402


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    return asyncio.run(server.call_tool(name, arguments))


def _configure_operator(
    paths: FoundryPaths,
    *,
    user_id: str = "alice",
    workspace_id: str = "ws-mine",
    roles: tuple[str, ...] = ("owner",),
    sensitivity_ceiling: str = "client_sensitive",
) -> None:
    """Same shape as `test_operator_mcp_server.py`'s own `_configure_operator`
    (deliberately re-inlined, not imported -- that file's own docstring
    explains why this transport-only leg avoids cross-file coupling for a
    ~10-line helper)."""

    data: dict[str, Any] = load_yaml(paths.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {"user_id": user_id, "workspace_id": workspace_id, "roles": list(roles)},
        "sensitivity_ceiling": sensitivity_ceiling,
    }
    dump_yaml(data, paths.foundry_yaml)


@pytest.fixture()
def server(tmp_foundry: FoundryPaths) -> Any:
    _configure_operator(tmp_foundry, user_id=_IDENTITY.user_id, workspace_id=_IDENTITY.workspace_id, roles=_IDENTITY.roles)
    return server_module.build_server(paths=tmp_foundry)


# ---------------------------------------------------------------------------
# Mutation kind: run.plan -- preflight -> execute, and every drift scenario
# ---------------------------------------------------------------------------


def _run_plan_payload(intent_id: str) -> dict[str, Any]:
    """The FULL, explicit `input_payload` (every optional adapter
    parameter spelled out at its own default value) so preflight's LITERAL
    caller-supplied payload and execute's adapter-reconstructed payload
    (which always includes every non-None field, including ones that took
    a DEFAULT) are byte-identical -- see `run_plan.invoke`'s own
    `input_payload` construction. A caller who instead omits optional
    fields at preflight and relies on the adapter's own defaults at
    execute would NOT bind (a separate, general "who owns default
    expansion" question outside this fix cycle's six assigned findings --
    flagged in the completion note, not fixed here)."""

    return {
        "intent_id": intent_id,
        "depth": "standard",
        "audience": "technical",
        "max_cost_usd": 5.0,
        "max_runtime_minutes": 60,
        "freshness_days": 180,
    }


def _run_plan_effective_sensitivity(intent_id: str, paths: FoundryPaths) -> str:
    """The SAME derivation `run_plan.invoke` performs internally
    (structurally, from the intent's own real sensitivity -- never
    caller-supplied) -- preflight must present the SAME value or
    `_bindings_match`'s `effective_sensitivity` field comparison fails
    before `targets`/`input_payload` are ever compared, mirroring
    `tests/unit/test_operator_mcp_adapter_run_plan.py`'s own equivalence
    test's construction."""

    return policy.resolve_effective_sensitivity(run_plan._resolve_intent_sensitivity(intent_id, paths))


def test_run_plan_preflight_confirmation_is_consumable_by_execute(
    server: Any, tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    """THE core proof (contract: "assert the confirmation minted by
    preflight is actually consumable by the subsequent execute call").
    Fails against pre-fix HEAD with `reason_code == "confirmation_missing"`
    (TERRA-1: preflight never persists) -- see the completion note for the
    scratch-copy proof."""

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    input_payload = _run_plan_payload(intent_id)

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "run.plan",
            "idempotency_key": "idem-e2e-1",
            "effective_sensitivity": _run_plan_effective_sensitivity(intent_id, tmp_foundry),
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False, preflight.structuredContent
    confirmation = preflight.structuredContent["confirmation"]
    assert confirmation is not None

    execute = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-e2e-1",
            "input_payload": input_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is False, execute.structuredContent
    result = execute.structuredContent
    assert result["ok"] is True
    assert result["operation_id"] is not None
    assert result["result"]["run_id"].startswith("rf_run_")
    assert result["result"]["canonical_refs_available"] is True


def test_run_plan_execute_with_changed_payload_is_refused_zero_effect(
    server: Any, tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    """Drift: same confirmation, DIFFERENT `input_payload` at execute
    (`depth` changed) -- `_bindings_match` recomputes `ctx.canonical_
    digest()` fresh from the EXECUTE-time payload and it no longer matches
    the record's `canonical_input_digest`. Zero-effect: no operation row is
    ever created for this call (proven by immediately reusing the SAME,
    still-`issued` confirmation successfully below)."""

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    input_payload = _run_plan_payload(intent_id)

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "run.plan",
            "idempotency_key": "idem-e2e-drift-payload",
            "effective_sensitivity": _run_plan_effective_sensitivity(intent_id, tmp_foundry),
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False
    confirmation = preflight.structuredContent["confirmation"]

    drifted_payload = {**input_payload, "depth": "deep"}
    execute = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-e2e-drift-payload",
            "input_payload": drifted_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is True
    assert execute.structuredContent["reason_code"] == "confirmation_mismatch"

    # Zero effect: the confirmation is untouched -- a SECOND execute call
    # with the ORIGINAL, undrifted payload still succeeds.
    execute_ok = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-e2e-drift-payload",
            "input_payload": input_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute_ok.isError is False, execute_ok.structuredContent


def test_run_plan_execute_with_changed_idempotency_key_is_refused_zero_effect(
    server: Any, tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    input_payload = _run_plan_payload(intent_id)

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "run.plan",
            "idempotency_key": "idem-e2e-drift-idem",
            "effective_sensitivity": _run_plan_effective_sensitivity(intent_id, tmp_foundry),
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False
    confirmation = preflight.structuredContent["confirmation"]

    execute = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-e2e-drift-idem-DIFFERENT",
            "input_payload": input_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is True
    assert execute.structuredContent["reason_code"] == "confirmation_mismatch"


def test_run_plan_execute_expired_confirmation_is_refused(
    server: Any, tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    """Expiry drift: presents a confirmation record whose `expires_at` has
    already passed (constructed by copying a REAL, freshly minted +
    persisted record and only backdating its timestamps -- never a
    from-scratch forged record, so `token_digest`/binding fields are all
    genuine and this isolates EXPIRY as the one failing predicate)."""

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    input_payload = _run_plan_payload(intent_id)

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "run.plan",
            "idempotency_key": "idem-e2e-expired",
            "effective_sensitivity": _run_plan_effective_sensitivity(intent_id, tmp_foundry),
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False
    confirmation = preflight.structuredContent["confirmation"]

    expired_record = {
        **confirmation["record"],
        "issued_at": "2000-01-01T00:00:00Z",
        "expires_at": "2000-01-01T00:05:00Z",
    }

    from research_foundry.services import operator_operation_service as ops_module

    conn = ops_module._connect(tmp_foundry)
    try:
        import json as _json

        # `_connect` opens in autocommit mode (`isolation_level=None`,
        # mirrors `rbac_store._connect`'s convention) -- this single
        # `UPDATE` commits itself; no explicit `COMMIT` statement.
        conn.execute(
            "UPDATE confirmations SET record_json = ? WHERE confirmation_id = ?",
            (_json.dumps(expired_record), expired_record["confirmation_id"]),
        )
    finally:
        conn.close()

    execute = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-e2e-expired",
            "input_payload": input_payload,
            "confirmation_record": expired_record,
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is True
    assert execute.structuredContent["reason_code"] == "confirmation_expired"


def test_run_plan_execute_replayed_confirmation_is_a_zero_additional_effect_idempotent_success(
    server: Any, tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    """Replay drift, proven against the REAL (already-shipped, un-editable
    P1/P2) design rather than an assumption: presenting the EXACT SAME
    confirmation for the EXACT SAME request twice is `verify_confirmation`'s
    own `"exact_replay"` outcome, which `operator_mcp_policy`'s module
    docstring explicitly documents as "decisions-block: NOT an error" --
    `consume_and_create_operation`'s own `_consume_locked` special-cases it
    to return the ALREADY-COMPLETED prior operation again, `ok=True`,
    rather than executing a second time or denying. The correct "zero
    [ADDITIONAL] effect" proof for replay is therefore: the SECOND call
    succeeds, is marked `replayed`, and resolves to the SAME
    `operation_id` the first call minted -- never a distinct second
    operation. (An EARLIER version of this test asserted the second call
    would be REFUSED with `confirmation_replayed` -- that assumption was
    WRONG about this repo's actual, documented DUR-1 semantics and was
    corrected here before ever landing; flagged in the completion note per
    contract hard boundary 5's spirit, even though no shipped test pinned
    the wrong assumption.)"""

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    input_payload = _run_plan_payload(intent_id)

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "run.plan",
            "idempotency_key": "idem-e2e-replay",
            "effective_sensitivity": _run_plan_effective_sensitivity(intent_id, tmp_foundry),
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False
    confirmation = preflight.structuredContent["confirmation"]

    args = {
        "idempotency_key": "idem-e2e-replay",
        "input_payload": input_payload,
        "confirmation_record": confirmation["record"],
        "presented_token": confirmation["token"],
    }
    first = _call(server, "run.plan", args)
    assert first.isError is False, first.structuredContent
    first_operation_id = first.structuredContent["operation_id"]
    assert first.structuredContent["result"].get("replayed") is not True

    second = _call(server, "run.plan", args)
    assert second.isError is False, second.structuredContent
    assert second.structuredContent["operation_id"] == first_operation_id
    assert second.structuredContent["result"]["replayed"] is True


# ---------------------------------------------------------------------------
# writeback.preview: the SAME preflight -> execute proof, plus the
# TERRA-2-specific target-binding drift
# ---------------------------------------------------------------------------


def test_writeback_preview_preflight_confirmation_is_consumable_by_execute(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """Fails against pre-fix HEAD with `reason_code == "preflight_failed"`
    at the PREFLIGHT step itself (TERRA-2: `writeback_targets` always
    empty) -- never even reaches an execute call to fail a SECOND way."""

    run_id = _build_run(tmp_foundry, identity=_IDENTITY)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)
    run_ctx = writeback_preview._resolve_run_context(run_id, tmp_foundry)
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)
    input_payload = {"run_id": run_id, "targets": ["meatywiki", "arc"]}

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-e2e-wb-1",
            "effective_sensitivity": effective_sensitivity,
            "targets": [
                {"target_kind": "run", "target_ref": run_id},
                {"target_kind": "evidence_bundle", "target_ref": run_id},
            ],
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False, preflight.structuredContent
    confirmation = preflight.structuredContent["confirmation"]
    assert confirmation is not None

    execute = _call(
        server,
        "writeback.preview",
        {
            "idempotency_key": "idem-e2e-wb-1",
            "input_payload": input_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is False, execute.structuredContent
    result = execute.structuredContent["result"]
    assert result["status"] == "completed"
    assert result["bundle_found"] is True
    returned_targets = {t["target"] for t in result["targets"]}
    assert returned_targets == {"meatywiki", "arc"}


def test_writeback_preview_execute_with_changed_targets_is_refused_zero_effect(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """TERRA-2-specific drift: preflight minted for `{"meatywiki", "arc"}`,
    execute presents a DIFFERENT target set -- must be refused, proving
    `writeback_targets`/`input_payload["targets"]` genuinely participate in
    the binding this fix wires up (not merely accepted and ignored)."""

    run_id = _build_run(tmp_foundry, identity=_IDENTITY)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)
    run_ctx = writeback_preview._resolve_run_context(run_id, tmp_foundry)
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)
    input_payload = {"run_id": run_id, "targets": ["meatywiki", "arc"]}

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-e2e-wb-drift",
            "effective_sensitivity": effective_sensitivity,
            "targets": [
                {"target_kind": "run", "target_ref": run_id},
                {"target_kind": "evidence_bundle", "target_ref": run_id},
            ],
            "input_payload": input_payload,
        },
    )
    assert preflight.isError is False
    confirmation = preflight.structuredContent["confirmation"]

    drifted_payload = {"run_id": run_id, "targets": ["skillmeat"]}
    execute = _call(
        server,
        "writeback.preview",
        {
            "idempotency_key": "idem-e2e-wb-drift",
            "input_payload": drifted_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is True
    assert execute.structuredContent["reason_code"] == "confirmation_mismatch"

    # Zero effect: the ORIGINAL, undrifted payload still consumes cleanly.
    execute_ok = _call(
        server,
        "writeback.preview",
        {
            "idempotency_key": "idem-e2e-wb-drift",
            "input_payload": input_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute_ok.isError is False, execute_ok.structuredContent


def test_writeback_preview_execute_with_changed_workspace_target_is_refused(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """Workspace/target drift: preflight minted for run A, execute presents
    the SAME confirmation but for a DIFFERENT run id (different `run`/
    `evidence_bundle` target refs) -- the confirmation's bound `targets`
    list no longer matches what execute's own adapter reconstructs."""

    run_id_a = _build_run(tmp_foundry, identity=_IDENTITY)
    writeback_module.build_bundle(run_id_a, verify=False, paths=tmp_foundry)
    run_id_b = _build_run(tmp_foundry, identity=_IDENTITY)
    writeback_module.build_bundle(run_id_b, verify=False, paths=tmp_foundry)
    run_ctx = writeback_preview._resolve_run_context(run_id_a, tmp_foundry)
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-e2e-wb-workspace",
            "effective_sensitivity": effective_sensitivity,
            "targets": [
                {"target_kind": "run", "target_ref": run_id_a},
                {"target_kind": "evidence_bundle", "target_ref": run_id_a},
            ],
            "input_payload": {"run_id": run_id_a, "targets": ["meatywiki"]},
        },
    )
    assert preflight.isError is False
    confirmation = preflight.structuredContent["confirmation"]

    execute = _call(
        server,
        "writeback.preview",
        {
            "idempotency_key": "idem-e2e-wb-workspace",
            "input_payload": {"run_id": run_id_b, "targets": ["meatywiki"]},
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is True
    assert execute.structuredContent["reason_code"] == "confirmation_mismatch"
