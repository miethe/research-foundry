"""Unit tests for the `writeback.preview` Operator MCP adapter
(research-foundry-operator-mcp-v1 M2 leg A, task OPM-5.3).

Covers: parity between the adapter's staged output and the pure payload
functions (`writeback._intenttree_update_payload`/`_arc_review_payload`/
`_notebooklm_update_payload`) the layer-below refactor introduced, dry run's
zero-effects guarantee, zero integration-client construction across every
supported target, the D4-style "missing bundle / unsupported target /
degraded correlation are governed RESULTS, never denials" contract, the
review-required sensitivity denying the WHOLE operation one layer up (at the
policy guard stage, before `writeback.preview_writeback` is ever called),
the H7 fail-closed sensitivity-ceiling guard, and exact-retry idempotency.

Reuses, never reinvents: `tests/unit/test_operator_mcp_adapter_verify_bundle.
py`'s `_build_verified_run`/`_mint_and_record` helper shape,
`tests/unit/test_operator_mcp_adapter_run_plan.py`'s
`_default_sensitivity_ceiling`/`_recording_ceiling` fixtures.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import writeback as writeback_module
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.operator_mcp_adapters import writeback_preview
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import dump_yaml, load_yaml

from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)

_IDENTITY = AuthIdentity("alice", "ws-mine", ("owner",))

_IDEA = (
    "Research how agentic research workflows should handle evidence bundles and "
    "claim traceability across cheap extraction and deep synthesis models. "
    "Studies show 40% of unsupported claims come from synthesis drift."
)

_SOURCE_TEXT = (
    "Evidence bundles let a research run carry its sources, claims, and a report "
    "in one auditable package. A 2025 study found that 40% of unsupported claims "
    "originate during synthesis when extraction and synthesis use different models. "
    "Claim ledgers reduce citation mismatch by mapping every material sentence to "
    "an evidence id. Limitations: small sample, single domain."
)


def _build_verified_run(
    paths: FoundryPaths, *, identity: AuthIdentity = _IDENTITY, sensitivity: str = "personal"
) -> str:
    """Drives the real deterministic pipeline through synthesis. Returns a
    run_id with a real report + claim ledger, but NO evidence bundle yet --
    callers that need one call `writeback.build_bundle` themselves. Mirrors
    `test_operator_mcp_adapter_verify_bundle.py`'s own helper of the same
    name."""

    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    assert tri.intent_id
    plan = plan_run(tri.intent_id, identity=identity, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / f"input_source_{run_id}.txt"
    src_file.write_text(_SOURCE_TEXT, encoding="utf-8")
    ingest_source(
        str(src_file),
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        title="Evidence bundles and claim traceability",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


def _mint_and_record(
    ctx: policy.PolicyContext, op_service: OperatorOperationService
) -> tuple[Any, str]:
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)
    return issued.record, issued.token


def _preview_ctx(
    run_id: str, targets: tuple[str, ...], idempotency_key: str, tmp_foundry: FoundryPaths
) -> policy.PolicyContext:
    """Builds the exact `ctx` `invoke_preview` constructs internally for
    `run_id` -- reused by every test that needs a REAL confirmation cycle."""

    run_ctx = writeback_preview._resolve_run_context(run_id, tmp_foundry)
    normalized = tuple(sorted({str(t) for t in targets}))
    return policy.PolicyContext.for_configured_operator(
        operation_kind=writeback_preview.OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("evidence_bundle", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id, "targets": list(normalized)},
        writeback_targets=normalized,
        paths=tmp_foundry,
    )


# ---------------------------------------------------------------------------
# targets normalization -- canonical digest is order/duplicate independent
# ---------------------------------------------------------------------------


def test_preview_ctx_canonical_digest_independent_of_target_order_and_duplicates(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)

    ctx_a = _preview_ctx(run_id, ("arc", "intenttree"), "idem-normalize", tmp_foundry)
    ctx_b = _preview_ctx(run_id, ("intenttree", "arc", "intenttree"), "idem-normalize", tmp_foundry)

    assert ctx_a.canonical_digest() == ctx_b.canonical_digest()
    assert ctx_a.writeback_targets == ("arc", "intenttree")


# ---------------------------------------------------------------------------
# parity: staged content matches the pure payload functions directly
# ---------------------------------------------------------------------------


def test_invoke_preview_staged_content_matches_pure_payload_functions(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The adapter's staged JSON for `arc`/`notebooklm` must be BYTE-
    equivalent (as parsed JSON) to calling the pure payload functions
    directly with the same inputs -- proves the adapter is a lossless view
    over the shared pure-render seam, not an independently reconstructed
    one."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    ctx = _preview_ctx(run_id, ("arc", "notebooklm"), "idem-preview-parity", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-parity",
        confirmation_record=record,
        presented_token=token,
        targets=("arc", "notebooklm"),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["bundle_found"] is True

    rp = tmp_foundry.run_paths(run_id)
    bundle_doc = load_yaml(rp.evidence_bundle)
    bundle_ident = str(bundle_doc["id"])
    ledger = load_yaml(rp.claim_ledger)
    sensitivity = "personal"

    direct_arc = writeback_module._arc_review_payload(
        rp, tmp_foundry, bundle_ident=bundle_ident, ledger=ledger, sensitivity=sensitivity,
        requires_review=False,
    )
    from research_foundry.services import notebook_correlation

    notebook_id = notebook_correlation.notebook_for_run(run_id, paths=tmp_foundry)
    direct_notebooklm = writeback_module._notebooklm_update_payload(
        rp, tmp_foundry, bundle_ident=bundle_ident, ledger=ledger, requires_review=False,
        notebook_id=notebook_id, notebook_title=None,
    )

    by_target = {t["target"]: t for t in result.result["targets"]}
    staged_arc = json.loads((rp.run / by_target["arc"]["staged_path"]).read_text(encoding="utf-8"))
    staged_notebooklm = json.loads(
        (rp.run / by_target["notebooklm"]["staged_path"]).read_text(encoding="utf-8")
    )

    assert staged_arc == direct_arc
    assert staged_notebooklm == direct_notebooklm
    # Staged files live under the run's own staging root, never the live
    # writebacks/ paths.
    assert by_target["arc"]["staged_path"].startswith("staging/writeback_preview/")
    assert not rp.arc_review_request.exists()
    assert not rp.notebooklm_update.exists()


# ---------------------------------------------------------------------------
# zero client construction across every supported target
# ---------------------------------------------------------------------------


def test_invoke_preview_never_constructs_or_calls_any_integration_client(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spies on every network-reaching seam this codebase actually has
    (`IntentTreeClient.from_config`, `ArcClient.from_config`,
    `get_notebooklm_client`, `get_meatywiki_client`, and the real HTTP
    primitive `urllib.request.urlopen` -- this codebase has no `httpx`
    dependency at all, see `integrations/base.py`'s own module docstring)
    and asserts NONE fire across all three preview-supported targets,
    including a node/correlation that WOULD be bound (so the live-push gate
    would fire on the live path)."""

    from research_foundry.integrations import intenttree as intenttree_integration
    from research_foundry.integrations import arc as arc_integration
    from research_foundry import integrations as integrations_pkg

    def _must_not_construct(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("writeback.preview must never construct an integration client")

    monkeypatch.setattr(intenttree_integration.IntentTreeClient, "from_config", classmethod(_must_not_construct))
    monkeypatch.setattr(arc_integration.ArcClient, "from_config", classmethod(_must_not_construct))
    monkeypatch.setattr(integrations_pkg, "get_notebooklm_client", _must_not_construct)
    monkeypatch.setattr(integrations_pkg, "get_meatywiki_client", _must_not_construct)

    def _must_not_urlopen(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("writeback.preview must never reach the network")

    monkeypatch.setattr(urllib.request, "urlopen", _must_not_urlopen)

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    # Bind an IntentTree node so the LIVE path's push gate would fire --
    # proves the zero-construction guarantee isn't merely an artifact of an
    # unbound node/correlation short-circuiting before any client is ever
    # touched.
    rp = tmp_foundry.run_paths(run_id)
    run_doc = load_yaml(rp.run_yaml)
    run_doc["task_node_id"] = "itt_node_bound_for_test"
    dump_yaml(run_doc, rp.run_yaml)

    targets = ("intenttree", "arc", "notebooklm")
    ctx = _preview_ctx(run_id, targets, "idem-preview-zero-client", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-zero-client",
        confirmation_record=record,
        presented_token=token,
        targets=targets,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    by_target = {t["target"]: t["status"] for t in result.result["targets"]}
    assert by_target["intenttree"] == "staged"
    assert by_target["arc"] == "staged"
    assert by_target["notebooklm"] == "degraded"  # no notebook correlation registered


# ---------------------------------------------------------------------------
# dry run: zero effects
# ---------------------------------------------------------------------------


def test_invoke_preview_dry_run_never_calls_preview_writeback(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call writeback.preview_writeback")

    monkeypatch.setattr(writeback_module, "preview_writeback", _must_not_run)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-dry",
        confirmation_record=None,
        presented_token=None,
        targets=("arc",),
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "writeback.preview"}
    assert not (tmp_foundry.run_paths(run_id).run / "staging").exists()


# ---------------------------------------------------------------------------
# D4: missing bundle / unsupported target are governed RESULTS, never denials
# ---------------------------------------------------------------------------


def test_invoke_preview_missing_bundle_is_governed_result_zero_files_staged(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    assert not rp.evidence_bundle.exists()

    ctx = _preview_ctx(run_id, ("arc", "intenttree"), "idem-preview-missing-bundle", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-missing-bundle",
        confirmation_record=record,
        presented_token=token,
        targets=("arc", "intenttree"),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["bundle_found"] is False
    statuses = {t["target"]: t["status"] for t in result.result["targets"]}
    assert statuses == {"arc": "missing_bundle", "intenttree": "missing_bundle"}
    assert all(t["staged_path"] is None for t in result.result["targets"])
    assert not (rp.run / "staging").exists()


def test_invoke_preview_unsupported_target_is_governed_result(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ccdash` stays `unsupported_target` (orchestrator adjudication of
    JC-2, part 2): its live render path (`telemetry.emit_ccdash_event`)
    constructs a client but `telemetry.py` is outside this leg's file
    ownership AND M2's declared `files_affected` -- filed as a follow-up ITT
    node rather than split here. `meatywiki`/`skillmeat` are now SUPPORTED
    (JC-2 part 1, see the dedicated parity tests below)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    ctx = _preview_ctx(run_id, ("ccdash",), "idem-preview-unsupported", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-unsupported",
        confirmation_record=record,
        presented_token=token,
        targets=("ccdash",),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["targets"] == [
        {"target": "ccdash", "status": "unsupported_target", "staged_path": None}
    ]


# ---------------------------------------------------------------------------
# JC-2 extension: meatywiki/skillmeat preview parity (destination-override,
# never the live writebacks/ path, never the paths.meatywiki/paths.skillmeat
# mirror, never the SkillBOM registry upsert)
# ---------------------------------------------------------------------------


def test_invoke_preview_meatywiki_skillmeat_staged_never_touch_live_paths_or_registry(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    from research_foundry.registry import SKILLBOM_INDEX, Registry

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    ctx = _preview_ctx(run_id, ("meatywiki", "skillmeat"), "idem-preview-mw-sk", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-mw-sk",
        confirmation_record=record,
        presented_token=token,
        targets=("meatywiki", "skillmeat"),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    by_target = {t["target"]: t for t in result.result["targets"]}
    assert by_target["meatywiki"]["status"] == "staged"
    assert by_target["skillmeat"]["status"] == "staged"
    assert by_target["meatywiki"]["staged_path"].endswith("meatywiki.md")
    assert by_target["skillmeat"]["staged_path"].endswith("skillmeat.md")

    rp = tmp_foundry.run_paths(run_id)
    # Never the live writebacks/ path.
    assert not rp.meatywiki_writeback.exists()
    assert not rp.skillbom_candidate.exists()
    # Never the shared-workspace mirror.
    assert not (tmp_foundry.meatywiki / "sources").exists() or not list(
        (tmp_foundry.meatywiki / "sources").glob("*.md")
    )
    assert not (tmp_foundry.skillmeat / "skillboms").exists() or not list(
        (tmp_foundry.skillmeat / "skillboms").glob("*.md")
    )
    # Never the SkillBOM registry.
    reg = Registry.open(SKILLBOM_INDEX, paths=tmp_foundry)
    assert reg.items() == []

    # Staged content is a real, schema-shaped meatywiki_writeback/
    # skillbom_candidate front-matter document -- produced by the SAME
    # render functions the live path calls (destination override, not a
    # duplicated assembly).
    from research_foundry.frontmatter import load_md

    mw_front, _ = load_md(rp.run / by_target["meatywiki"]["staged_path"])
    assert mw_front["writeback_type"] == "source_note"
    sk_front, _ = load_md(rp.run / by_target["skillmeat"]["staged_path"])
    assert sk_front["proposed_skillbom_id"] == "skill_research_swarm_v0"


# ---------------------------------------------------------------------------
# review-required sensitivity denies the WHOLE operation one layer up
# ---------------------------------------------------------------------------


def test_invoke_preview_review_required_denies_before_preview_writeback_runs(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A work-sensitive run requesting the `intenttree` target must deny at
    the policy layer's guard stage (`guard_review_required`) -- the SAME
    `intenttree_writeback_requires_review` rule every other writeback path
    fires -- BEFORE `writeback.preview_writeback` is ever invoked."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry, sensitivity="work_sensitive")
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("preview_writeback must never run when the guard denies review-required")

    monkeypatch.setattr(writeback_module, "preview_writeback", _must_not_run)

    ctx = _preview_ctx(run_id, ("intenttree",), "idem-preview-review-required", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-review-required",
        confirmation_record=record,
        presented_token=token,
        targets=("intenttree",),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "guard_review_required"
    assert result.error["retryable"] is True


# ---------------------------------------------------------------------------
# H7 defect fix: above-ceiling denies at guard stage, SAME shape as a
# wrong-workspace denial for the same real, prerequisite-satisfied run.
# ---------------------------------------------------------------------------


def test_invoke_preview_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry, sensitivity="personal")
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    run_ctx = writeback_preview._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.sensitivity == "personal"

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    direct_ctx = _preview_ctx(run_id, ("arc",), "idem-preview-above-ceiling", tmp_foundry)
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=writeback_preview.OPERATION_KIND,
        idempotency_key="idem-preview-above-ceiling",
        effective_sensitivity=direct_ctx.effective_sensitivity,
        sensitivity_ceiling="public",
        targets=direct_ctx.targets,
        resolved_target_workspaces=direct_ctx.resolved_target_workspaces,
        input_payload=direct_ctx.input_payload,
        writeback_targets=direct_ctx.writeback_targets,
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"

    above_ceiling_result = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        targets=("arc",),
        dry_run=True,
        paths=tmp_foundry,
    )
    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert "detail" not in above_ceiling_result.error

    missing_run_result = writeback_preview.invoke_preview(
        run_id="does-not-exist-at-all-either",
        idempotency_key="idem-preview-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        targets=("arc",),
        dry_run=True,
        paths=tmp_foundry,
    )
    assert missing_run_result.ok is False
    assert missing_run_result.error is not None
    assert missing_run_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error == missing_run_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


# ---------------------------------------------------------------------------
# exact retry idempotency (D7)
# ---------------------------------------------------------------------------


def test_invoke_preview_exact_retry_does_not_recall_preview_writeback(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    call_count = 0
    real_preview_writeback = writeback_module.preview_writeback

    def _counting_preview_writeback(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return real_preview_writeback(*args, **kwargs)

    monkeypatch.setattr(writeback_module, "preview_writeback", _counting_preview_writeback)

    ctx = _preview_ctx(run_id, ("arc",), "idem-preview-retry", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    first = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-retry",
        confirmation_record=record,
        presented_token=token,
        targets=("arc",),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    second = writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key="idem-preview-retry",
        confirmation_record=record,
        presented_token=token,
        targets=("arc",),
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert first.operation_id == second.operation_id
    assert call_count == 1, "preview_writeback must be called exactly once across both invocations"
