"""Unit tests for the `run.extract`, `run.claim_map`, and `run.synthesize`
Operator MCP adapters (research-foundry-operator-mcp-v1 M1 remainder).

Covers, per adapter, the M1 implementer contract's mandatory set (§D6/§D7):
a direct-service-vs-adapter canonical-refs parity check (spy pattern, never
a double-call, since each service mints artifacts derived from a run's own
already-persisted state), exact-retry idempotency (no re-invocation of the
wrapped service on an exact replay), and the H7 negative fixture (an
above-ceiling target denies with the SAME shape a genuinely-missing run
gets). Also covers dry run's zero-effects guarantee per adapter, mirroring
`test_operator_mcp_adapter_run_plan.py`'s own suite shape.

Reuses, never reinvents: `tests/test_planning.py`'s `_make_intent` helper,
`tests/unit/test_operator_mcp_adapter_run_plan.py`'s `_default_sensitivity_
ceiling`/`_recording_ceiling` fixtures (the H7 fix's own reviewer-recommended
shape), and `tests/unit/test_operator_mcp_policy.py`'s identity fixtures --
the SAME reuse convention `test_operator_mcp_adapter_swarm_start.py`
establishes for this family of tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import claim_mapping, extraction, source_cards, synthesis
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_mcp_adapters import research_stages
from research_foundry.services.operator_operation_service import OperatorOperationService
from tests.test_planning import _make_intent
from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)
from tests.unit.test_operator_mcp_policy import _default_operator_identity  # noqa: F401

_IDENTITY = AuthIdentity("alice", "ws-mine", ("owner",))


def _planned_run(tmp_foundry: FoundryPaths, text: str) -> str:
    """Capture + triage + plan a real run, stamped into `_IDENTITY`'s own
    workspace (`ws-mine`) so `research_stages._resolve_run_context`'s
    `workspace_id` resolution matches whatever `policy.resolve_operator_
    identity` resolves to for every test in this module -- mirrors
    `test_operator_mcp_adapter_swarm_start.py`'s own `_planned_run` helper."""

    intent_id, _ = _make_intent(text, sensitivity="personal", tmp_foundry=tmp_foundry)
    from research_foundry.services import planning

    result = planning.plan_run(intent_id, profile="personal", identity=_IDENTITY, paths=tmp_foundry)
    return result.run_id


def _ingest_source(tmp_foundry: FoundryPaths, run_id: str, tmp_path: Path, text: str) -> None:
    doc = tmp_path / f"{run_id}-notes.txt"
    doc.write_text(text, encoding="utf-8")
    source_cards.ingest_source(str(doc), run_id=run_id, title="Notes", paths=tmp_foundry)


def _extracted_run(tmp_foundry: FoundryPaths, run_id: str, tmp_path: Path, text: str) -> None:
    _ingest_source(tmp_foundry, run_id, tmp_path, text)
    extraction.extract_run(run_id, paths=tmp_foundry)


def _claim_mapped_run(tmp_foundry: FoundryPaths, run_id: str, tmp_path: Path, text: str) -> None:
    _extracted_run(tmp_foundry, run_id, tmp_path, text)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)


_SAMPLE_FACT_TEXT = (
    "Latency dropped 30% with the new router.\n\n"
    "Evidence bundles make claim traceability auditable end to end.\n"
)


# ---------------------------------------------------------------------------
# run.extract
# ---------------------------------------------------------------------------


def test_invoke_extract_result_matches_direct_extract_run_call(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spies on the ONE real `extraction.extract_run` call `invoke_extract()`
    makes and asserts the adapter's bounded result dict carries EXACTLY the
    same canonical fields the direct `ExtractResult` holds."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _ingest_source(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    captured_direct: list[Any] = []
    real_extract_run = extraction.extract_run

    def _spy(*args: Any, **kwargs: Any) -> Any:
        result = real_extract_run(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(extraction, "extract_run", _spy)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.workspace_id == "ws-mine"

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.EXTRACT_OPERATION_KIND,
        idempotency_key="idem-equivalence",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "model_profile": "rf_extract_cheap"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = research_stages.invoke_extract(
        run_id=run_id,
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "extract_run must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["run_id"] == direct.run_id
    assert result.result["cards"] == list(direct.cards)
    assert result.result["count"] == direct.count
    assert result.result["canonical_refs_available"] is True


def test_invoke_extract_dry_run_never_calls_extract_run(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _ingest_source(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call extraction.extract_run")

    monkeypatch.setattr(extraction, "extract_run", _must_not_run)

    result = research_stages.invoke_extract(
        run_id=run_id,
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.extract"}


def test_invoke_extract_exact_retry_does_not_reexecute(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D7: an exact retry (same idempotency_key, same confirmation) must not
    re-invoke `extraction.extract_run` -- proven by counting real calls, not
    merely by inspecting the second result."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _ingest_source(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    calls: list[int] = []
    real_extract_run = extraction.extract_run

    def _spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return real_extract_run(*args, **kwargs)

    monkeypatch.setattr(extraction, "extract_run", _spy)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.EXTRACT_OPERATION_KIND,
        idempotency_key="idem-retry",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "model_profile": "rf_extract_cheap"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    first = research_stages.invoke_extract(
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    second = research_stages.invoke_extract(
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert len(calls) == 1, "exact retry must not re-invoke extract_run"
    assert first.operation_id == second.operation_id


def test_invoke_extract_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H7 guard fix: an above-ceiling real run and a genuinely-missing run
    deny with byte-identical `error` envelopes -- proven end to end at this
    adapter's own public surface, mirroring `test_operator_mcp_adapter_
    run_plan.py`'s own `test_invoke_denies_above_ceiling_...` convention."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _ingest_source(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.EXTRACT_OPERATION_KIND,
        idempotency_key="idem-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="public",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = research_stages.invoke_extract(
        run_id=run_id,
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_run_result = research_stages.invoke_extract(
        run_id="rf_run_does_not_exist_at_all",
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

    assert missing_run_result.ok is False
    assert above_ceiling_result.error == missing_run_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_invoke_extract_denies_preflight_failed_when_no_source_cards(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1 (checklist item 2, applied to run.extract): a run with ZERO
    `sources/*.md` cards must DENY `preflight_failed`, never silently
    succeed with `ExtractResult(cards=[], count=0)`. Proven with a spy: the
    real `extraction.extract_run` must never be invoked at all -- a
    zero-effect denial, not a governed-but-executed no-op.

    Mints a REAL, valid confirmation (mirrors the `_result_matches_direct_`
    tests' own pattern) so this reaches the same execution path a
    successful call would -- without it, a pre-fix run would deny
    `confirmation_missing` for an unrelated reason and never actually prove
    F1 (the pre-fix bug only manifests once execution is reached)."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("extract_run must never be called when sources are missing")

    monkeypatch.setattr(extraction, "extract_run", _must_not_run)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.EXTRACT_OPERATION_KIND,
        idempotency_key="idem-no-sources",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "model_profile": "rf_extract_cheap"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = research_stages.invoke_extract(
        run_id=run_id,
        idempotency_key="idem-no-sources",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "preflight_failed"
    assert result.operation_id is None


# ---------------------------------------------------------------------------
# run.claim_map
# ---------------------------------------------------------------------------


def test_invoke_claim_map_result_matches_direct_build_claim_ledger_call(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _extracted_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    captured_direct: list[Any] = []
    real_build_claim_ledger = claim_mapping.build_claim_ledger

    def _spy(*args: Any, **kwargs: Any) -> Any:
        result = real_build_claim_ledger(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(claim_mapping, "build_claim_ledger", _spy)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.CLAIM_MAP_OPERATION_KIND,
        idempotency_key="idem-equivalence",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("extraction_card", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "build_claim_ledger must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["run_id"] == direct.run_id
    assert result.result["ledger_path"] == str(direct.ledger_path)
    assert result.result["claims_total"] == direct.claims_total
    assert result.result["by_status"] == dict(direct.by_status)
    assert result.result["canonical_refs_available"] is True


def test_invoke_claim_map_dry_run_never_calls_build_claim_ledger(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _extracted_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call claim_mapping.build_claim_ledger")

    monkeypatch.setattr(claim_mapping, "build_claim_ledger", _must_not_run)

    result = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.claim_map"}


def test_invoke_claim_map_exact_retry_does_not_reexecute(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _extracted_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    calls: list[int] = []
    real_build_claim_ledger = claim_mapping.build_claim_ledger

    def _spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return real_build_claim_ledger(*args, **kwargs)

    monkeypatch.setattr(claim_mapping, "build_claim_ledger", _spy)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.CLAIM_MAP_OPERATION_KIND,
        idempotency_key="idem-retry",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("extraction_card", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    first = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    second = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert len(calls) == 1, "exact retry must not re-invoke build_claim_ledger"
    assert first.operation_id == second.operation_id


def test_invoke_claim_map_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _extracted_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.CLAIM_MAP_OPERATION_KIND,
        idempotency_key="idem-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="public",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("extraction_card", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_run_result = research_stages.invoke_claim_map(
        run_id="rf_run_does_not_exist_at_all",
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

    assert missing_run_result.ok is False
    assert above_ceiling_result.error == missing_run_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_invoke_claim_map_denies_preflight_failed_when_no_extraction_cards(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1 -- reproduces the exact scenario both lenses found empirically: a
    valid, owned run with ZERO extraction cards must DENY `preflight_failed`,
    never return `ok=True, claims_total=0`. Proven with a spy: the real
    `claim_mapping.build_claim_ledger` must never be invoked.

    Mints a REAL, valid confirmation (see `test_invoke_extract_denies_
    preflight_failed_when_no_source_cards`'s own docstring for why -- a
    pre-fix run without one denies `confirmation_missing` and never
    actually reaches, let alone proves, the F1 bug)."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("build_claim_ledger must never be called when extraction cards are missing")

    monkeypatch.setattr(claim_mapping, "build_claim_ledger", _must_not_run)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.CLAIM_MAP_OPERATION_KIND,
        idempotency_key="idem-no-cards",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("extraction_card", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-no-cards",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "preflight_failed"
    assert result.operation_id is None


def test_invoke_claim_map_denies_preflight_failed_for_unauthorized_caller_without_leaking_prerequisite_state(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F6 lesson applied here (not fixed in this file's `verify_bundle.py`
    sibling, but the SAME leak this adapter must not reproduce): an
    UNAUTHORIZED caller (wrong-workspace identity) must deny at RBAC
    (`not_found`), never at `preflight_failed` -- even when the run in
    question genuinely has zero extraction cards. If the new prerequisite
    check ran BEFORE authorization, a caller could distinguish "no
    extraction cards yet" (`preflight_failed`) from "not yours"
    (`not_found`) by reason code alone; this proves that distinction is
    unreachable for an unauthorized caller."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    # Deliberately never extract -- this run genuinely has zero cards, so a
    # pre-authorization prerequisite check WOULD deny preflight_failed here.
    foreign_identity = AuthIdentity("mallory", "ws-other", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: foreign_identity)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("build_claim_ledger must never be called for an unauthorized caller")

    monkeypatch.setattr(claim_mapping, "build_claim_ledger", _must_not_run)

    result = research_stages.invoke_claim_map(
        run_id=run_id,
        idempotency_key="idem-foreign",
        confirmation_record=None,
        presented_token=None,
        paths=tmp_foundry,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "not_found"


# ---------------------------------------------------------------------------
# run.synthesize
# ---------------------------------------------------------------------------


def test_invoke_synthesize_result_matches_direct_synthesize_report_call(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _claim_mapped_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    captured_direct: list[Any] = []
    real_synthesize_report = synthesis.synthesize_report

    def _spy(*args: Any, **kwargs: Any) -> Any:
        result = real_synthesize_report(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(synthesis, "synthesize_report", _spy)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.SYNTHESIZE_OPERATION_KIND,
        idempotency_key="idem-equivalence",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("claim_ledger", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id, "model_profile": "rf_synthesize_deep", "final": False, "llm": False},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = research_stages.invoke_synthesize(
        run_id=run_id,
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "synthesize_report must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["run_id"] == direct.run_id
    assert result.result["report_path"] == str(direct.report_path)
    assert result.result["claims_cited"] == list(direct.claims_cited)
    assert result.result["canonical_refs_available"] is True


def test_invoke_synthesize_dry_run_never_calls_synthesize_report(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _claim_mapped_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call synthesis.synthesize_report")

    monkeypatch.setattr(synthesis, "synthesize_report", _must_not_run)

    result = research_stages.invoke_synthesize(
        run_id=run_id,
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.synthesize"}


def test_invoke_synthesize_exact_retry_does_not_reexecute(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _claim_mapped_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    calls: list[int] = []
    real_synthesize_report = synthesis.synthesize_report

    def _spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return real_synthesize_report(*args, **kwargs)

    monkeypatch.setattr(synthesis, "synthesize_report", _spy)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.SYNTHESIZE_OPERATION_KIND,
        idempotency_key="idem-retry",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("claim_ledger", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id, "model_profile": "rf_synthesize_deep", "final": False, "llm": False},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    first = research_stages.invoke_synthesize(
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    second = research_stages.invoke_synthesize(
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert len(calls) == 1, "exact retry must not re-invoke synthesize_report"
    assert first.operation_id == second.operation_id


def test_invoke_synthesize_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _claim_mapped_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.SYNTHESIZE_OPERATION_KIND,
        idempotency_key="idem-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="public",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("claim_ledger", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = research_stages.invoke_synthesize(
        run_id=run_id,
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_run_result = research_stages.invoke_synthesize(
        run_id="rf_run_does_not_exist_at_all",
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

    assert missing_run_result.ok is False
    assert above_ceiling_result.error == missing_run_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


def test_invoke_synthesize_denies_preflight_failed_when_no_claim_ledger(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1 -- reproduces the exact scenario both lenses found empirically: a
    valid, owned run with NO claim ledger must DENY `preflight_failed`,
    never return `ok=True` with a fully "completed" placeholder report
    (`synthesis._load_ledger` silently substitutes an empty ledger).
    Proven with a spy: the real `synthesis.synthesize_report` must never be
    invoked -- no placeholder report is ever written to disk.

    Mints a REAL, valid confirmation (see `test_invoke_extract_denies_
    preflight_failed_when_no_source_cards`'s own docstring for why -- a
    pre-fix run without one denies `confirmation_missing` and never
    actually reaches, let alone proves, the F1 bug)."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    _extracted_run(tmp_foundry, run_id, tmp_path, _SAMPLE_FACT_TEXT)
    # Deliberately never claim_map -- no claims/claim_ledger.yaml exists.
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("synthesize_report must never be called when the claim ledger is missing")

    monkeypatch.setattr(synthesis, "synthesize_report", _must_not_run)

    run_ctx = research_stages._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=research_stages.SYNTHESIZE_OPERATION_KIND,
        idempotency_key="idem-no-ledger",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("claim_ledger", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id, "model_profile": "rf_synthesize_deep", "final": False, "llm": False},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = research_stages.invoke_synthesize(
        run_id=run_id,
        idempotency_key="idem-no-ledger",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "preflight_failed"
    assert result.operation_id is None
    assert not tmp_foundry.run_paths(run_id).report_draft.exists()
    assert not tmp_foundry.run_paths(run_id).report_final.exists()
