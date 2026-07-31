"""Unit tests for the `external_report.import` Operator MCP adapter
(research-foundry-operator-mcp-v1, M1 remainder leg B).

Covers: the parity acceptance criterion (a direct-service call and the
MCP-adapter call produce equivalent canonical refs, D6), dry run's
zero-effects guarantee (D3), exact-retry idempotency (D7), and the H7
above-ceiling denial's shape-identity with a missing-target denial (D1).

Every fixture packet is deliberately BLOCKED (`omit_member_role="report"`)
so these tests exercise the adapter's own wiring -- authorize/consume/
execute/bounded-result -- without needing network access or a fake
resolver: a blocked packet still produces a real, schema-valid
`ImportOutcome` (packet_digest/receipt_id/receipt_digest/status="blocked")
through the exact same `import_external_report` call path a resolvable
packet would use.

Reuses, never reinvents: `tests.unit.test_external_research_interchange`'s
`build_packet` helper, `tests.unit.test_operator_mcp_adapter_run_plan`'s
`_default_sensitivity_ceiling`/`_recording_ceiling` fixtures, and
`tests.unit.test_operator_mcp_policy`'s identity fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import external_research_import as eri_module
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_mcp_adapters import external_import
from research_foundry.services.operator_operation_service import OperatorOperationService

from tests.unit.test_external_research_interchange import build_packet
from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)
from tests.unit.test_operator_mcp_policy import _default_operator_identity  # noqa: F401

_IDENTITY = AuthIdentity("alice", "ws-mine", ("owner",))


def _blocked_packet(tmp_path: Path, name: str = "packet") -> str:
    root = build_packet(tmp_path / name, omit_member_role="report")
    return str(root)


def _basic_ctx(tmp_foundry: FoundryPaths, *, packet_dir: str, idempotency_key: str) -> policy.PolicyContext:
    """Builds the EXACT SAME canonical `PolicyContext` `external_import.
    invoke()` constructs internally for a staging-only (no `target_run_id`,
    no `resume`) call, so a confirmation minted against it binds to the SAME
    canonical digest `invoke()` recomputes internally."""

    target_ref = external_import._target_ref_for(packet_dir, "ws-mine")
    return policy.PolicyContext.for_configured_operator(
        operation_kind=external_import.OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.resolve_effective_sensitivity(),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("import_packet", target_ref),),
        resolved_target_workspaces=("ws-mine",),
        input_payload={"packet_dir": packet_dir, "workspace_id": "ws-mine", "resume": False},
        paths=tmp_foundry,
    )


# ---------------------------------------------------------------------------
# Acceptance criterion: direct-service call vs MCP-adapter call produce
# equivalent canonical refs (D6, spy -- never double-call)
# ---------------------------------------------------------------------------


def test_invoke_result_matches_direct_import_call(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    packet_dir = _blocked_packet(tmp_path)

    captured_direct: list[Any] = []
    real_import = eri_module.import_external_report

    def _spy_import(*args: Any, **kwargs: Any) -> Any:
        result = real_import(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(eri_module, "import_external_report", _spy_import)

    ctx = _basic_ctx(tmp_foundry, packet_dir=packet_dir, idempotency_key="idem-equivalence")
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "import_external_report must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["workspace_id"] == direct.workspace_id
    assert result.result["target_run_id"] == direct.target_run_id
    assert result.result["packet_digest"] == direct.packet_digest
    assert result.result["receipt_id"] == direct.receipt_id
    assert result.result["receipt_digest"] == direct.receipt_digest
    assert result.result["status"] == direct.status
    assert result.result["status"] == "blocked"
    assert result.result["canonical_refs_available"] is True


# ---------------------------------------------------------------------------
# Dry run: zero effects (D3 -- the substrate's is the ONE dry-run this
# adapter exposes; the service's own native dry_run is unreachable)
# ---------------------------------------------------------------------------


def test_invoke_dry_run_never_calls_import_external_report(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    packet_dir = _blocked_packet(tmp_path)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call import_external_report")

    monkeypatch.setattr(eri_module, "import_external_report", _must_not_run)

    result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        resume=True,  # must be ignored entirely on the dry-run path (D3)
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "external_report.import"}


# ---------------------------------------------------------------------------
# Exact retry idempotency (D7): no duplicate import receipt
# ---------------------------------------------------------------------------


def test_exact_retry_does_not_duplicate_import_receipt(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    packet_dir = _blocked_packet(tmp_path)

    call_count = 0
    real_import = eri_module.import_external_report

    def _counting_import(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return real_import(*args, **kwargs)

    monkeypatch.setattr(eri_module, "import_external_report", _counting_import)

    ctx = _basic_ctx(tmp_foundry, packet_dir=packet_dir, idempotency_key="idem-retry")
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    kwargs: dict[str, Any] = dict(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        operations=op_service,
    )

    first = external_import.invoke(now=ids.now(), **kwargs)
    second = external_import.invoke(now=ids.now(), **kwargs)

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert call_count == 1, "exact retry must not re-invoke import_external_report"
    assert second.result is not None
    assert second.result.get("replayed") is True


# ---------------------------------------------------------------------------
# H7 defect fix: an above-ceiling target denies at the guard stage, with the
# SAME `not_found` shape a genuinely-missing target gets (D1)
# ---------------------------------------------------------------------------


def test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_target(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`effective_sensitivity` for `external_report.import` always resolves
    to the STRICTEST label (module docstring's "no target-content signal"
    note) -- there is no packet-existence branch before the guard stage, so
    a real packet and a nonexistent one deny IDENTICALLY once the locally
    configured ceiling is below the strictest label, proving the guard
    fires without leaking whether the packet_dir it was pointed at exists."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    from research_foundry.services import operator_mcp_adapters as adapters_pkg

    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    real_packet_dir = _blocked_packet(tmp_path, "real-packet")

    above_ceiling_result = external_import.invoke(
        packet_dir=real_packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_target_result = external_import.invoke(
        packet_dir=str(tmp_path / "does-not-exist-at-all"),
        workspace_id="ws-mine",
        idempotency_key="idem-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert above_ceiling_result.error["operation_id"] is None
    assert above_ceiling_result.error["receipt_ref"] is None
    assert "detail" not in above_ceiling_result.error

    assert missing_target_result.ok is False
    assert above_ceiling_result.error == missing_target_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_invoke_denies_above_ceiling_for_cross_workspace_target(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller-declared `workspace_id` that does not match the ONE
    configured operator identity's own workspace denies at the rbac stage
    (H3) with the SAME `not_found` shape -- proving `resolved_target_
    workspaces` is not merely echoed back as an authorization grant."""

    identity = _IDENTITY  # workspace_id == "ws-mine"
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    packet_dir = _blocked_packet(tmp_path)

    result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-not-mine",
        idempotency_key="idem-cross-workspace",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "not_found"
