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

**M2 fix cycle 2, SEC-1 test inversion (flagged loudly, per boundary rule 5
-- "if a test pins wrong behavior, invert it").** `test_invoke_result_
matches_direct_import_call` and `test_exact_retry_does_not_duplicate_import_
receipt` are the only two tests here that reach `_run()` for a REAL (non-
dry-run) execution; both previously built `packet_dir` at a sibling `tmp_
path` location OUTSIDE `tmp_foundry.root` -- pinning the exact unbounded-
path-reach behavior the security gate's SEC-1 finding determined was a
defect, not intended design. Both now build `packet_dir` under `tmp_
foundry.root` instead, via `_blocked_packet(tmp_foundry.root)`. The
remaining four tests in this file are all `dry_run=True` (never reach
`_run()`, per D3's own zero-effect guarantee) and are UNCHANGED -- the SEC-1
containment check only runs inside `_run()`, so it is inert on those paths
regardless of where their `packet_dir` fixtures point.
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

from tests.test_planning import _make_intent
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

    # M2 fix cycle 2, SEC-1: packet_dir now must resolve inside the
    # authorized workspace tree (tmp_foundry.root), not a sibling tmp_path
    # location -- see the module-level note at the top of this file.
    packet_dir = _blocked_packet(tmp_foundry.root)

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
    # M2 fix cycle 2, SEC-1: packet_dir must resolve inside the workspace.
    packet_dir = _blocked_packet(tmp_foundry.root)

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


# ---------------------------------------------------------------------------
# F2 regression: `target_run_id` is a sibling parameter to `workspace_id`
# that was never independently authorized. Before the fix, a caller could
# supply their OWN correctly-matching `workspace_id` (passing H3) together
# with a `target_run_id` belonging to a DIFFERENT workspace, and
# `import_external_report` would still record import activity against that
# foreign run (`external_research_import.py:611`) -- the guard that existed
# (workspace_id re-derivation) simply did not cover this sibling input.
# ---------------------------------------------------------------------------


def test_invoke_denies_foreign_target_run_id_despite_matching_workspace_id(
    tmp_foundry: FoundryPaths, tmp_path: Path, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`workspace_id="ws-mine"` matches the configured identity and would
    pass H3 on its own (see `test_invoke_denies_above_ceiling_for_cross_
    workspace_target`, the mirror-image case). `target_run_id`, however,
    points at a REAL run owned by a different workspace ("ws-other") --
    this must now ALSO be denied, proving `target_run_id` is independently
    authorized rather than riding through on `workspace_id`'s own check."""

    identity = _IDENTITY  # workspace_id == "ws-mine"
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    packet_dir = _blocked_packet(tmp_path)

    from research_foundry.auth_identity import AuthIdentity
    from research_foundry.services import planning

    foreign_identity = AuthIdentity("carol", "ws-other", ("owner",))
    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    foreign_run = planning.plan_run(
        intent_id, profile="personal", identity=foreign_identity, paths=tmp_foundry
    )

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "import_external_report must never be called against a target_run_id "
            "this identity does not own"
        )

    monkeypatch.setattr(eri_module, "import_external_report", _must_not_run)

    result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        target_run_id=foreign_run.run_id,
        idempotency_key="idem-foreign-target-run",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "not_found"


# ---------------------------------------------------------------------------
# M2 fix cycle 2, SEC-1 (BLOCKING): packet_dir must resolve inside the
# authorized workspace tree. Before this fix, an MCP caller could name any
# absolute host path as packet_dir and it reached import_external_report
# verbatim -- an existence/type/symlink/content oracle over the entire host
# filesystem, empirically demonstrated by the security gate against /etc,
# ~/.ssh, /var/root, and a workspace-planted symlink escape.
# ---------------------------------------------------------------------------


def test_invoke_denies_packet_dir_outside_workspace_tree(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real, authorized (non-dry-run) call whose `packet_dir` resolves
    OUTSIDE `tmp_foundry.root` must deny with a bounded `internal_error`
    envelope, and `import_external_report` must never be called for it --
    the containment check runs INSIDE `_run()`, before the canonical service
    is ever reached.

    MUTATION NOTE: the spy RECORDS (never raises) so this test is sensitive
    to the guard's ABSENCE, not merely to *some* exception firing inside
    `_run()` -- an earlier draft used an assertion-raising spy, whose crash
    ALSO produces `ok=False`/`internal_error`, making the reason-code
    assertion alone unable to distinguish "the guard denied" from "the
    guard was removed and this trap fired instead" (both converge to the
    same envelope via `run_actions`'s own exception boundary). The load-
    bearing assertion here is `calls == []`, verified by killing this exact
    mutation (commenting out the `_resolved_within` check) in a scratch
    copy and confirming `calls` becomes non-empty."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    # Deliberately a SIBLING of tmp_foundry.root, not beneath it.
    outside_packet_dir = _blocked_packet(tmp_path, "outside-packet")

    calls: list[Any] = []

    def _recording_import(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise AssertionError("import_external_report reached -- containment guard did not fire")

    monkeypatch.setattr(eri_module, "import_external_report", _recording_import)

    ctx = _basic_ctx(tmp_foundry, packet_dir=outside_packet_dir, idempotency_key="idem-sec1-outside")
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = external_import.invoke(
        packet_dir=outside_packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-sec1-outside",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert calls == [], "import_external_report must never be called for an out-of-workspace packet_dir"
    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


def test_invoke_denies_packet_dir_symlink_escape(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `packet_dir` that is LEXICALLY inside the workspace but a symlink
    resolving OUTSIDE it must deny identically -- SEC-1's own PoC used
    exactly this shape (`<ws>/evil_link` -> `/etc`) to reach `os.scandir`
    on `/private/etc`. Proves the containment check resolves symlinks,
    never trusts the lexical path alone."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    outside_target = tmp_path / "outside-target"
    outside_target.mkdir()
    evil_link = tmp_foundry.root / "evil_link"
    evil_link.symlink_to(outside_target, target_is_directory=True)
    packet_dir = str(evil_link)

    calls: list[Any] = []

    def _recording_import(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise AssertionError("import_external_report reached -- containment guard did not fire")

    monkeypatch.setattr(eri_module, "import_external_report", _recording_import)

    ctx = _basic_ctx(tmp_foundry, packet_dir=packet_dir, idempotency_key="idem-sec1-symlink")
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-sec1-symlink",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert calls == [], "import_external_report must never be called for a symlink-escaped packet_dir"
    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


def test_invoke_allows_packet_dir_inside_workspace_tree(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive counterpart: a `packet_dir` genuinely inside
    `tmp_foundry.root` reaches `import_external_report` normally -- the
    SEC-1 fix bounds, it does not break, the legitimate in-workspace case."""

    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    packet_dir = _blocked_packet(tmp_foundry.root, "inside-packet")

    ctx = _basic_ctx(tmp_foundry, packet_dir=packet_dir, idempotency_key="idem-sec1-inside")
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        idempotency_key="idem-sec1-inside",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error


# ---------------------------------------------------------------------------
# M2 fix cycle 2 -- path-containment sweep: target_run_id's own read-before-
# validate hazard (a NEW instance found beyond packet_dir, same class).
# `_resolve_run_workspace_id` reads `paths.run_paths(run_id).run_yaml`
# BEFORE `ctx`/`operator_mcp_policy._TARGET_REF_PATTERN` ever validates
# `run_id` -- a traversal-shaped `target_run_id` (e.g. ".." -- legal against
# that pattern, since it contains no "/") could therefore trigger a read
# one level above `runs/` before any policy stage ever runs.
# ---------------------------------------------------------------------------


def test_resolve_run_workspace_id_denies_traversal_before_read(tmp_foundry: FoundryPaths) -> None:
    """Direct unit proof: `_resolve_run_workspace_id("..", ...)` resolves to
    `None` -- the SAME fail-closed sentinel a genuinely missing run gets --
    without ever attempting `load_yaml` outside `runs/`.

    MUTATION NOTE: `run_id=".."` resolves (`paths.runs / ".."`) to
    `paths.root` -- a directory that normally has NO `run.yaml` of its own,
    so a plain "does the containment check fire" assertion would pass
    EVEN WITHOUT the guard (the read would simply hit `FileNotFoundError`
    and fall through to the SAME pre-existing `None` return the guard also
    produces -- a vacuous test, indistinguishable from a real guard). A
    real `run.yaml` is planted AT the escape target
    (`tmp_foundry.root/run.yaml`) with a MATCHING `workspace_id` so an
    unguarded read would return a REAL, non-`None` value -- only the
    containment check itself can make this assertion hold."""

    (tmp_foundry.root / "run.yaml").write_text("workspace_id: ws-mine\n", encoding="utf-8")

    result = external_import._resolve_run_workspace_id("..", tmp_foundry)
    assert result is None


def test_invoke_denies_traversal_target_run_id_same_shape_as_missing_run(
    tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _IDENTITY
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    packet_dir = _blocked_packet(tmp_foundry.root)

    traversal_result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        target_run_id="..",
        idempotency_key="idem-sec1-traversal-run",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_run_result = external_import.invoke(
        packet_dir=packet_dir,
        workspace_id="ws-mine",
        target_run_id="does-not-exist-at-all",
        idempotency_key="idem-sec1-missing-run",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert traversal_result.ok is False
    assert traversal_result.error is not None
    assert traversal_result.error["reason_code"] == "not_found"
    assert missing_run_result.ok is False
    assert traversal_result.error == missing_run_result.error
