"""Unit tests for the `source.ingest` Operator MCP adapter (research-
foundry-operator-mcp-v1, M1 remainder leg B).

Covers: the parity acceptance criterion (D6), dry run's zero-effects
guarantee, exact-retry idempotency (D7), the H7 above-ceiling denial's
shape-identity with a missing-run denial (D1), and the workspace-binding
decision (D2): a non-"default" identity workspace threads through to
`ingest_source`, and the literal string "default" appears nowhere in the
adapter module's own source.

Reuses, never reinvents: `tests.test_planning`'s `_make_intent` helper,
`tests.unit.test_operator_mcp_adapter_run_plan`'s `_default_sensitivity_
ceiling`/`_recording_ceiling` fixtures, and `tests.unit.test_operator_mcp_
policy`'s identity fixtures.
"""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import source_cards as source_cards_module
from research_foundry.services.operator_mcp_adapters import source_ingest
from research_foundry.services.operator_operation_service import OperatorOperationService

from tests.test_planning import _make_intent
from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)
from tests.unit.test_operator_mcp_policy import _default_operator_identity  # noqa: F401

_IDENTITY = AuthIdentity("alice", "ws-mine", ("owner",))
_SAMPLE_CONTENT = "Alpha bravo charlie delta echo. Example content for ingestion testing."


def _planned_run(tmp_foundry: FoundryPaths, text: str) -> str:
    """Capture + triage + plan a real run, stamped into `_IDENTITY`'s own
    workspace (`ws-mine`) so `source_ingest._resolve_run_workspace_id`'s
    resolution matches whatever `policy.resolve_operator_identity` resolves
    to for every test in this module."""

    intent_id, _ = _make_intent(text, sensitivity="personal", tmp_foundry=tmp_foundry)
    from research_foundry.services import planning

    result = planning.plan_run(intent_id, profile="personal", identity=_IDENTITY, paths=tmp_foundry)
    return result.run_id


def _basic_ctx(
    tmp_foundry: FoundryPaths, *, run_id: str, idempotency_key: str, content: str | None = None
) -> policy.PolicyContext:
    """Builds the EXACT SAME canonical `PolicyContext` `source_ingest.
    invoke()` constructs internally for a call with every optional omitted
    apart from `content`, so a confirmation minted against it binds to the
    SAME canonical digest `invoke()` recomputes internally.

    `content` is bound in via its `sha256` digest (F4 fix, never the raw
    text -- see `source_ingest`'s own module docstring), and
    `effective_sensitivity` is `"personal"` because `_planned_run` always
    plans against a `sensitivity="personal"` intent, which
    `source_ingest.invoke()` now reads STRUCTURALLY from the target run's
    own `run.yaml` (F3 fix), not from any caller-supplied `sensitivity`
    parameter -- callers here still pass no explicit `sensitivity`, so the
    value happens to be the same string, but for a different reason than
    before this fix."""

    content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None
    payload: dict[str, Any] = {
        "locator": "https://example.com/test-source",
        "run_id": run_id,
        "source_type": "other",
        "sensitivity": "personal",
        "fetch": False,
        "created_by_agent": "rf_source_carder",
    }
    if content_digest is not None:
        payload["content_digest"] = content_digest

    return policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-mine",),
        input_payload=payload,
        paths=tmp_foundry,
    )


# ---------------------------------------------------------------------------
# Acceptance criterion: direct-service call vs MCP-adapter call produce
# equivalent canonical refs (D6, spy -- never double-call)
# ---------------------------------------------------------------------------


def test_invoke_result_matches_direct_ingest_call(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    captured_direct: list[Any] = []
    real_ingest_source = source_cards_module.ingest_source

    def _spy_ingest_source(*args: Any, **kwargs: Any) -> Any:
        result = real_ingest_source(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(source_cards_module, "ingest_source", _spy_ingest_source)

    ctx = _basic_ctx(tmp_foundry, run_id=run_id, idempotency_key="idem-equivalence", content=_SAMPLE_CONTENT)
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        content=_SAMPLE_CONTENT,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "ingest_source must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["source_card_id"] == direct.source_card_id
    assert result.result["path"] == str(direct.path)
    assert result.result["source_type"] == direct.source_type
    assert result.result["degraded"] == direct.degraded
    assert result.result["extraction_status"] == direct.extraction_status
    assert result.result["degraded"] is False
    assert result.result["canonical_refs_available"] is True


# ---------------------------------------------------------------------------
# F4 regression: confirmation-binding bypass via omitted `content`.
#
# Before the fix, `content` (plus `extra_limitations`/`created_by_agent`) was
# omitted from the canonical `input_payload` the confirmation digest covers,
# so a confirmation minted for NO content (or benign content) would still
# authorize executing WITH arbitrary replacement content -- `ingest_source`
# forwarded `content` unchanged regardless of what the confirmation actually
# committed to. This is the inversion of what
# `test_invoke_result_matches_direct_ingest_call` used to assert inline (it
# minted a confirmation without `content` at all, then invoked WITH content
# and asserted SUCCESS -- pinning the bypass rather than testing the parity
# contract). That test above now mints its confirmation WITH matching
# `content` (a real parity case); THIS test isolates the mismatch case and
# asserts it now DENIES.
# ---------------------------------------------------------------------------


def test_invoke_denies_when_confirmed_content_differs_from_supplied_content(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    captured_content: list[Any] = []
    real_ingest_source = source_cards_module.ingest_source

    def _spy_ingest_source(*args: Any, **kwargs: Any) -> Any:
        captured_content.append(kwargs.get("content"))
        return real_ingest_source(*args, **kwargs)

    monkeypatch.setattr(source_cards_module, "ingest_source", _spy_ingest_source)

    # Mint a confirmation against the EXACT payload shape the pre-fix
    # adapter built for a call with `content=None` -- deliberately NOT
    # `_basic_ctx` (which now builds the POST-fix shape, including
    # `created_by_agent`/`content_digest`, and would mismatch on its own
    # regardless of `content`, masking the specific defect this test proves
    # was fixed). This is the exact scenario the previously-pinned assertion
    # in `test_invoke_result_matches_direct_ingest_call` exercised inline:
    # mint without `content`, then invoke WITH content.
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key="idem-content-mismatch",
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-mine",),
        input_payload={
            "locator": "https://example.com/test-source",
            "run_id": run_id,
            "source_type": "other",
            "sensitivity": "personal",
            "fetch": False,
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    # Present that confirmation, but supply real content on the live call.
    result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-content-mismatch",
        confirmation_record=issued.record,
        presented_token=issued.token,
        content=_SAMPLE_CONTENT,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "confirmation_mismatch"
    assert captured_content == [], "ingest_source must never be reached with mismatched content"


# ---------------------------------------------------------------------------
# Dry run: zero effects
# ---------------------------------------------------------------------------


def test_invoke_dry_run_never_calls_ingest_source(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call ingest_source")

    monkeypatch.setattr(source_cards_module, "ingest_source", _must_not_run)

    result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        content=_SAMPLE_CONTENT,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "source.ingest"}


# ---------------------------------------------------------------------------
# Exact retry idempotency (D7): no duplicate source card
# ---------------------------------------------------------------------------


def test_exact_retry_does_not_duplicate_source_card(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    call_count = 0
    real_ingest_source = source_cards_module.ingest_source

    def _counting_ingest_source(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return real_ingest_source(*args, **kwargs)

    monkeypatch.setattr(source_cards_module, "ingest_source", _counting_ingest_source)

    ctx = _basic_ctx(tmp_foundry, run_id=run_id, idempotency_key="idem-retry", content=_SAMPLE_CONTENT)
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    kwargs: dict[str, Any] = dict(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-retry",
        confirmation_record=issued.record,
        presented_token=issued.token,
        content=_SAMPLE_CONTENT,
        paths=tmp_foundry,
        operations=op_service,
    )

    first = source_ingest.invoke(now=ids.now(), **kwargs)
    second = source_ingest.invoke(now=ids.now(), **kwargs)

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert call_count == 1, "exact retry must not re-invoke ingest_source"
    assert second.result is not None
    assert second.result.get("replayed") is True

    run_paths = tmp_foundry.run_paths(run_id)
    source_cards_on_disk = list(run_paths.sources.glob("*.md"))
    assert len(source_cards_on_disk) == 1, "exact retry must not create a duplicate source card"


# ---------------------------------------------------------------------------
# F3 regression: `effective_sensitivity` must be resolved from the target
# run's OWN `run.yaml`, never from the caller-supplied `sensitivity`
# parameter. Before the fix, a caller under a below-"personal" ceiling could
# mislabel `sensitivity="public"` on a source destined for a genuinely
# "personal"-sensitivity run and the guard stage would compare the caller's
# own permissive claim against the ceiling -- always passing. This run is
# real and owned by this identity, so the ONLY thing that can now cause a
# denial is the run's OWN structurally-resolved sensitivity ("personal",
# from `_planned_run`'s `sensitivity="personal"` intent) exceeding the
# forced "public" ceiling -- the caller's `sensitivity="public"` claim must
# have no bearing on this outcome.
# ---------------------------------------------------------------------------


def test_invoke_denies_caller_mislabeled_public_sensitivity_on_sensitive_run(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    from research_foundry.services import operator_mcp_adapters as adapters_pkg

    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    run_id = _planned_run(tmp_foundry, sample_idea_text)  # real run, sensitivity="personal"

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("ingest_source must never be called past a fail-open sensitivity guard")

    monkeypatch.setattr(source_cards_module, "ingest_source", _must_not_run)

    result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-mislabeled-sensitivity",
        confirmation_record=None,
        presented_token=None,
        # The caller's own self-attested claim -- BELOW the run's real
        # "personal" sensitivity. Before the fix, this caller-supplied value
        # was what the guard stage evaluated, so this would have PASSED.
        sensitivity="public",
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "not_found"
    assert ceiling_calls == [tmp_foundry]


# ---------------------------------------------------------------------------
# H7 defect fix: an above-ceiling target denies at the guard stage, with the
# SAME `not_found` shape a genuinely-missing run gets (H3) (D1)
# ---------------------------------------------------------------------------


def test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the locally configured ceiling resolved to `"public"`, a REAL
    run this identity owns (structurally-resolved sensitivity "personal",
    per `_planned_run`) is denied at the guard stage (H7) regardless of the
    caller-declared `sensitivity="client_sensitive"` parameter (F3 fix: that
    parameter no longer feeds the guard comparison at all). A
    genuinely-missing run denies at the rbac stage instead (H3: its owning
    workspace cannot be resolved) -- `build_error`'s own documented
    one-denial-shape guarantee (H6) means both envelopes are byte-identical
    regardless of which stage produced them."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    from research_foundry.services import operator_mcp_adapters as adapters_pkg

    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    run_id = _planned_run(tmp_foundry, sample_idea_text)

    above_ceiling_result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        sensitivity="client_sensitive",
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_run_result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id="does-not-exist-at-all",
        idempotency_key="idem-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        sensitivity="client_sensitive",
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


# ---------------------------------------------------------------------------
# D2: workspace binding -- structurally resolved from identity, never the
# CLI's own hard-coded single-operator literal
# ---------------------------------------------------------------------------


def test_non_default_identity_workspace_threads_through_to_ingest_source(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller identity whose workspace is NOT the CLI's own hard-coded
    single-operator literal (`cli_commands.py:354`) still threads correctly
    into `ingest_source`'s `assertion_registry_workspace_id` -- proving
    D2's resolution is generic, not accidentally tied to that one literal
    value."""

    identity = AuthIdentity("bob", "ws-not-the-cli-literal", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    from research_foundry.services import planning

    run_result = planning.plan_run(intent_id, profile="personal", identity=identity, paths=tmp_foundry)
    run_id = run_result.run_id

    captured_kwargs: list[dict[str, Any]] = []
    real_ingest_source = source_cards_module.ingest_source

    def _spy_ingest_source(*args: Any, **kwargs: Any) -> Any:
        captured_kwargs.append(kwargs)
        return real_ingest_source(*args, **kwargs)

    monkeypatch.setattr(source_cards_module, "ingest_source", _spy_ingest_source)

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key="idem-workspace",
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-not-the-cli-literal",),
        input_payload={
            "locator": "https://example.com/test-source",
            "run_id": run_id,
            "source_type": "other",
            "sensitivity": "personal",
            "fetch": False,
            "created_by_agent": "rf_source_carder",
            # F4 fix: content is bound in via digest, never raw text.
            "content_digest": hashlib.sha256(_SAMPLE_CONTENT.encode("utf-8")).hexdigest(),
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = source_ingest.invoke(
        locator="https://example.com/test-source",
        run_id=run_id,
        idempotency_key="idem-workspace",
        confirmation_record=issued.record,
        presented_token=issued.token,
        content=_SAMPLE_CONTENT,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["assertion_registry_workspace_id"] == "ws-not-the-cli-literal"


def test_default_literal_absent_from_source_ingest_module() -> None:
    """D2, source-level assertion: the literal string this task's contract
    names must not appear anywhere in the adapter module's own source --
    `assertion_registry_workspace_id` is resolved from `ctx.identity.
    workspace_id`, never a hard-coded single-operator fallback."""

    source = inspect.getsource(source_ingest)
    assert "default" not in source.lower()
