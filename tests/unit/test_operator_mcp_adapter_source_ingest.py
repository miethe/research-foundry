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
import os
import urllib.request
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


# ---------------------------------------------------------------------------
# M2 fix cycle 2 -- path-containment sweep (a NEW instance found beyond
# packet_dir, same class, arguably more severe): `source_cards.ingest_source`
# unconditionally reads ANY existing local file named by `locator` as FULL
# TEXT CONTENT whenever `content` is not already supplied -- no containment
# at all before this fix. `content=_SAMPLE_CONTENT` in every test above
# bypasses that branch entirely (source_cards.py's own precedence order),
# so none of them exercise it; these tests target it directly.
# ---------------------------------------------------------------------------


def test_invoke_denies_local_locator_outside_workspace_tree(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION NOTE: the spy RECORDS (never raises) so this test is
    sensitive to the guard's ABSENCE, not merely to *some* exception firing
    inside `_run()` -- see `test_operator_mcp_adapter_external_import.py`'s
    identical note for the full rationale (an assertion-raising spy's own
    crash converges to the SAME `internal_error` envelope a real guard
    denial produces, so the reason-code assertion alone cannot tell them
    apart)."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    outside_file = tmp_path / "outside_secret.txt"
    outside_file.write_text("host-local content the adapter must never read", encoding="utf-8")

    calls: list[Any] = []

    def _recording_ingest(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise AssertionError("ingest_source reached -- containment guard did not fire")

    monkeypatch.setattr(source_cards_module, "ingest_source", _recording_ingest)

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key="idem-sec-locator-outside",
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-mine",),
        input_payload={
            "locator": str(outside_file),
            "run_id": run_id,
            "source_type": "other",
            "sensitivity": "personal",
            "fetch": False,
            "created_by_agent": "rf_source_carder",
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = source_ingest.invoke(
        locator=str(outside_file),
        run_id=run_id,
        idempotency_key="idem-sec-locator-outside",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert calls == [], "ingest_source must never be called for a locator outside the workspace"
    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


def test_invoke_allows_local_locator_inside_workspace_tree(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive counterpart: a `locator` genuinely inside
    `tmp_foundry.root` is read normally -- the fix bounds, it does not
    break, the legitimate in-workspace local-file case."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    inside_file = tmp_foundry.root / "inside_source.txt"
    inside_file.write_text(_SAMPLE_CONTENT, encoding="utf-8")

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key="idem-sec-locator-inside",
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-mine",),
        input_payload={
            "locator": str(inside_file),
            "run_id": run_id,
            "source_type": "other",
            "sensitivity": "personal",
            "fetch": False,
            "created_by_agent": "rf_source_carder",
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = source_ingest.invoke(
        locator=str(inside_file),
        run_id=run_id,
        idempotency_key="idem-sec-locator-inside",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error


def test_resolve_run_context_denies_traversal_run_id_before_read(tmp_foundry: FoundryPaths) -> None:
    """Direct unit proof: a traversal-shaped `run_id` (`".."`, legal against
    `operator_mcp_policy._TARGET_REF_PATTERN` since it contains no `/`)
    resolves to `_RunContext(None, None)` -- the SAME fail-closed sentinel a
    genuinely missing run gets -- without ever attempting `load_yaml`
    outside `runs/`.

    MUTATION NOTE: a real `run.yaml` (matching workspace_id/sensitivity) is
    planted AT the escape target (`tmp_foundry.root/run.yaml`, what
    `paths.runs / ".."` resolves to) so an UNGUARDED read would return REAL,
    non-`None` values -- a bare "resolves to None" assertion without this
    plant would pass vacuously even with the guard removed, since
    `tmp_foundry.root` normally has no `run.yaml` of its own and the
    pre-existing exception handler would mask the missing guard."""

    (tmp_foundry.root / "run.yaml").write_text(
        "workspace_id: ws-mine\nsensitivity: public\n", encoding="utf-8"
    )

    result = source_ingest._resolve_run_context("..", tmp_foundry)
    assert result.workspace_id is None
    assert result.sensitivity is None


# ---------------------------------------------------------------------------
# M2 fix cycle 3, F3.1/SEC2-1 (BLOCKING) -- check/use anchor mismatch: the
# cycle-2 guard resolved a RELATIVE locator against the workspace root, then
# forwarded the caller's ORIGINAL unresolved string to `ingest_source`,
# which resolves it against the server process's CWD instead. F3.3: every
# pre-existing test here runs with CWD INSIDE the workspace, so none of them
# could ever observe this -- this test chdirs OUTSIDE the workspace first,
# exactly like the security re-gate's own reproduction
# (`locator="secret.txt"` after chdir).
# ---------------------------------------------------------------------------


def test_invoke_never_reads_cwd_relative_canary_after_chdir_outside_workspace(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`locator="secret.txt"` (relative, no scheme) is resolve-and-
    substituted against the WORKSPACE ROOT, never the process CWD -- so
    with CWD moved outside the workspace and a canary planted only at the
    CWD, `ingest_source` is still called (a relative locator is a
    legitimate shape, unlike `packet_dir`'s "reject outright" treatment --
    see F3.1's own scoping) but resolves to a NONEXISTENT path inside the
    workspace, never the real canary. The real `ingest_source` runs
    end-to-end (not mocked) so the produced source card is checked
    directly: the canary's content must never appear anywhere, and the
    result must be `degraded` (locator-only), not a real content read."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    outside_cwd = tmp_path / "outside-cwd-locator-root"
    outside_cwd.mkdir()
    canary = outside_cwd / "secret.txt"
    canary.write_text("CANARY: host-local content the adapter must never read", encoding="utf-8")

    captured_locator: list[str] = []
    real_ingest_source = source_cards_module.ingest_source

    def _spy_ingest_source(locator: str, **kwargs: Any) -> Any:
        captured_locator.append(locator)
        return real_ingest_source(locator, **kwargs)

    monkeypatch.setattr(source_cards_module, "ingest_source", _spy_ingest_source)

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key="idem-sec2-1-cwd-relative-locator",
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-mine",),
        input_payload={
            "locator": "secret.txt",
            "run_id": run_id,
            "source_type": "other",
            "sensitivity": "personal",
            "fetch": False,
            "created_by_agent": "rf_source_carder",
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    real_cwd = os.getcwd()
    os.chdir(outside_cwd)
    try:
        result = source_ingest.invoke(
            locator="secret.txt",
            run_id=run_id,
            idempotency_key="idem-sec2-1-cwd-relative-locator",
            confirmation_record=issued.record,
            presented_token=issued.token,
            paths=tmp_foundry,
            now=ids.now(),
            operations=op_service,
        )
    finally:
        os.chdir(real_cwd)

    # The resolved locator forwarded to ingest_source is anchored at the
    # WORKSPACE ROOT, never the CWD where the real canary lives.
    assert captured_locator == [str(tmp_foundry.root / "secret.txt")]
    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["degraded"] is True  # nonexistent path -- locator-only, never read
    # No source card anywhere in the run carries the canary's content.
    run_paths = tmp_foundry.run_paths(run_id)
    for card in run_paths.sources.glob("*.md"):
        assert "CANARY" not in card.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# M2 fix cycle 3, F3.2/SEC2-2 (BLOCKING) -- `file://` (and any other
# non-http(s) scheme) locator must be refused outright, before any dispatch,
# regardless of `fetch`. Covers every variant the security re-gate proved:
# `file:///etc/passwd`, `file://localhost/...`, `FILE://...` (urlparse
# lowercases), `file:/...` (single slash).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious_locator",
    [
        "file:///etc/passwd",
        "file://localhost/etc/passwd",
        "FILE:///etc/passwd",
        "file:/etc/passwd",
    ],
)
def test_invoke_denies_file_scheme_locator_variants_with_fetch_true(
    tmp_foundry: FoundryPaths,
    sample_idea_text: str,
    monkeypatch: pytest.MonkeyPatch,
    malicious_locator: str,
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    ingest_calls: list[Any] = []

    def _recording_ingest(*args: Any, **kwargs: Any) -> Any:
        ingest_calls.append((args, kwargs))
        raise AssertionError("ingest_source reached -- scheme allowlist did not fire")

    monkeypatch.setattr(source_cards_module, "ingest_source", _recording_ingest)

    urlopen_calls: list[Any] = []

    def _recording_urlopen(*args: Any, **kwargs: Any) -> Any:
        urlopen_calls.append((args, kwargs))
        raise AssertionError("urlopen reached -- scheme allowlist did not fire")

    monkeypatch.setattr(urllib.request, "urlopen", _recording_urlopen)

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=source_ingest.OPERATION_KIND,
        idempotency_key="idem-sec2-2-file-scheme",
        effective_sensitivity=policy.resolve_effective_sensitivity("personal"),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=("ws-mine",),
        input_payload={
            "locator": malicious_locator,
            "run_id": run_id,
            "source_type": "other",
            "sensitivity": "personal",
            "fetch": True,
            "created_by_agent": "rf_source_carder",
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = source_ingest.invoke(
        locator=malicious_locator,
        run_id=run_id,
        idempotency_key="idem-sec2-2-file-scheme",
        confirmation_record=issued.record,
        presented_token=issued.token,
        fetch=True,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert ingest_calls == [], "ingest_source must never be called for a file: scheme locator"
    assert urlopen_calls == [], "urlopen must never be called for a file: scheme locator"
    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


def test_looks_like_url_no_longer_accepts_file_scheme() -> None:
    """Direct unit proof: `file:` is no longer treated as an allowed URL
    scheme at all (M2 wave 1 originally included it alongside http/https)."""

    assert source_ingest._looks_like_url("file:///etc/passwd") is False
    assert source_ingest._looks_like_url("https://example.com/x") is True
    assert source_ingest._looks_like_url("http://example.com/x") is True
