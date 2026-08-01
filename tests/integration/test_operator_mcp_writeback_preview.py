"""Integration coverage for the `writeback.preview` Operator MCP adapter
(research-foundry-operator-mcp-v1 M2 leg A, task OPM-5.3, implementer
contract D9).

Runtime spies on every integration-client seam this codebase actually has
(`IntentTreeClient.from_config`, `ArcClient.from_config`,
`get_notebooklm_client`, `get_meatywiki_client`) plus the real HTTP
primitive (`urllib.request.urlopen` -- this codebase has no `httpx`
dependency at all, see `research_foundry/integrations/base.py`'s own module
docstring, which the M2 implementer contract's D9 text did not anticipate)
-- asserting ZERO constructions and ZERO calls across every preview
outcome: a fully-staged non-degraded run, a degraded run (no bound node /
no notebook correlation), a missing-bundle denial-shaped governed result,
and a review-required policy-layer denial. Plus staged-artifact content
assertions against the run's own on-disk state.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
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


def _build_run(
    paths: FoundryPaths, *, identity: AuthIdentity = _IDENTITY, sensitivity: str = "personal"
) -> str:
    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    plan = plan_run(tri.intent_id, identity=identity, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / f"input_source_{run_id}.txt"
    src_file.write_text(_SOURCE_TEXT, encoding="utf-8")
    ingest_source(
        str(src_file), run_id=run_id, source_type="paper", sensitivity=sensitivity,
        title="Evidence bundles and claim traceability", paths=paths,
    )
    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


@pytest.fixture(autouse=True)
def _default_sensitivity_ceiling(tmp_foundry: FoundryPaths) -> None:
    data = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"].setdefault("operator_mcp", {})
    data["foundry"]["operator_mcp"]["sensitivity_ceiling"] = "client_sensitive"
    dump_yaml(data, tmp_foundry.foundry_yaml)


@pytest.fixture(autouse=True)
def _spy_all_integration_seams(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """Installs a raise-on-touch spy over every network-reaching seam this
    codebase actually has. Every test in this module asserts `ok`/denial
    shape WITHOUT any of these firing -- proving `writeback.preview`'s call
    graph is genuinely client-free across every outcome branch, not merely
    on the happy path."""

    from research_foundry import integrations as integrations_pkg
    from research_foundry.integrations import arc as arc_integration
    from research_foundry.integrations import intenttree as intenttree_integration

    calls: dict[str, list[Any]] = {
        "intenttree_client": [], "arc_client": [], "notebooklm_client": [],
        "meatywiki_client": [], "urlopen": [],
    }

    def _record(key: str) -> Any:
        def _fn(*args: Any, **kwargs: Any) -> Any:
            calls[key].append((args, kwargs))
            raise AssertionError(f"writeback.preview must never touch {key}")
        return _fn

    monkeypatch.setattr(
        intenttree_integration.IntentTreeClient, "from_config", classmethod(lambda cls: _record("intenttree_client")())
    )
    monkeypatch.setattr(
        arc_integration.ArcClient, "from_config", classmethod(lambda cls: _record("arc_client")())
    )
    monkeypatch.setattr(integrations_pkg, "get_notebooklm_client", _record("notebooklm_client"))
    monkeypatch.setattr(integrations_pkg, "get_meatywiki_client", _record("meatywiki_client"))
    monkeypatch.setattr(urllib.request, "urlopen", _record("urlopen"))

    return calls


def _confirm_and_invoke(
    run_id: str, targets: tuple[str, ...], idempotency_key: str, tmp_foundry: FoundryPaths
) -> Any:
    run_ctx = writeback_preview._resolve_run_context(run_id, tmp_foundry)
    normalized = tuple(sorted({str(t) for t in targets}))
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=writeback_preview.OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id), policy.TargetRef("evidence_bundle", run_id)),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id, "targets": list(normalized)},
        writeback_targets=normalized,
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    return writeback_preview.invoke_preview(
        run_id=run_id,
        idempotency_key=idempotency_key,
        confirmation_record=issued.record,
        presented_token=issued.token,
        targets=targets,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )


# ---------------------------------------------------------------------------
# Fully-staged, non-degraded path -- content assertions
# ---------------------------------------------------------------------------


def test_preview_full_matrix_staged_zero_client_calls_with_content_assertions(
    tmp_foundry: FoundryPaths,
    monkeypatch: pytest.MonkeyPatch,
    _spy_all_integration_seams: dict[str, list[Any]],
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    # `capture_idea` already back-patches a deterministic, locally-derived
    # `intenttree_node_ref` onto every intent (see `services/capture.py`
    # line ~401) -- no network, no manual seeding needed for a "bound node"
    # fixture. Confirm that precondition explicitly so this test's "staged"
    # assertion is a real proof, not an accident of an unset field.
    rp = tmp_foundry.run_paths(run_id)
    run_meta = load_yaml(rp.run_yaml)
    intent_id = str(run_meta["intent_id"])
    intent_doc = load_yaml(tmp_foundry.intents_active / f"{intent_id}.yaml")
    assert intent_doc.get("intenttree_node_ref")

    from research_foundry.services import notebook_correlation

    notebook_correlation.record_run_notebook(run_id, "nb_test_seed", paths=tmp_foundry)

    result = _confirm_and_invoke(
        run_id, ("intenttree", "arc", "notebooklm", "meatywiki", "skillmeat"), "idem-matrix-staged", tmp_foundry
    )

    assert result.ok is True, result.error
    by_target = {t["target"]: t for t in result.result["targets"]}
    assert by_target["intenttree"]["status"] == "staged"
    assert by_target["arc"]["status"] == "staged"
    assert by_target["notebooklm"]["status"] == "staged"
    assert by_target["meatywiki"]["status"] == "staged"
    assert by_target["skillmeat"]["status"] == "staged"

    for name in ("intenttree_client", "arc_client", "notebooklm_client", "meatywiki_client", "urlopen"):
        assert _spy_all_integration_seams[name] == [], f"{name} was touched during preview"

    # Staged content assertions -- never the live writebacks/ paths.
    staged_intenttree = json.loads((rp.run / by_target["intenttree"]["staged_path"]).read_text(encoding="utf-8"))
    assert staged_intenttree["node_id"] == intent_doc["intenttree_node_ref"]
    assert staged_intenttree["push_status"] == "proposed"

    staged_notebooklm = json.loads((rp.run / by_target["notebooklm"]["staged_path"]).read_text(encoding="utf-8"))
    assert staged_notebooklm["notebook_id"] == "nb_test_seed"
    assert staged_notebooklm["push_status"] == "proposed"

    staged_arc = json.loads((rp.run / by_target["arc"]["staged_path"]).read_text(encoding="utf-8"))
    assert staged_arc["status"] == "proposed"
    assert staged_arc["arc_run_id"] is None

    from research_foundry.frontmatter import load_md

    mw_front, _ = load_md(rp.run / by_target["meatywiki"]["staged_path"])
    assert mw_front["writeback_type"] == "source_note"
    assert mw_front["status"] == "written"  # not requires_review for a personal run

    sk_front, _ = load_md(rp.run / by_target["skillmeat"]["staged_path"])
    assert sk_front["proposed_skillbom_id"] == "skill_research_swarm_v0"
    assert sk_front["status"] == "candidate"  # not requires_review for a personal run

    assert not rp.intenttree_update.exists()
    assert not rp.arc_review_request.exists()
    assert not rp.notebooklm_update.exists()
    assert not rp.meatywiki_writeback.exists()
    assert not rp.skillbom_candidate.exists()
    assert not (tmp_foundry.meatywiki / "sources").exists() or not list(
        (tmp_foundry.meatywiki / "sources").glob("*.md")
    )
    assert not (tmp_foundry.skillmeat / "skillboms").exists() or not list(
        (tmp_foundry.skillmeat / "skillboms").glob("*.md")
    )

    from research_foundry.registry import SKILLBOM_INDEX, Registry

    assert Registry.open(SKILLBOM_INDEX, paths=tmp_foundry).items() == []

    for name, target in by_target.items():
        assert target["staged_path"].startswith("staging/writeback_preview/")
        assert (rp.run / target["staged_path"]).is_relative_to(rp.run / "staging" / "writeback_preview")


# ---------------------------------------------------------------------------
# Degraded path -- unbound node / no notebook correlation
# ---------------------------------------------------------------------------


def test_preview_degraded_path_zero_client_calls(
    tmp_foundry: FoundryPaths,
    monkeypatch: pytest.MonkeyPatch,
    _spy_all_integration_seams: dict[str, list[Any]],
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_run(tmp_foundry)
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    # `capture_idea` back-patches a deterministic `intenttree_node_ref` onto
    # every intent by default (services/capture.py) -- blank it explicitly
    # so this test exercises a genuine "no bound node" condition rather than
    # an accidental one.
    rp0 = tmp_foundry.run_paths(run_id)
    run_meta0 = load_yaml(rp0.run_yaml)
    intent_path = tmp_foundry.intents_active / f"{run_meta0['intent_id']}.yaml"
    intent_doc = load_yaml(intent_path)
    intent_doc["intenttree_node_ref"] = ""
    dump_yaml(intent_doc, intent_path)

    result = _confirm_and_invoke(run_id, ("intenttree", "notebooklm"), "idem-matrix-degraded", tmp_foundry)

    assert result.ok is True, result.error
    by_target = {t["target"]: t for t in result.result["targets"]}
    assert by_target["intenttree"]["status"] == "degraded"
    assert by_target["notebooklm"]["status"] == "degraded"
    assert by_target["intenttree"]["staged_path"] is not None  # degraded still stages a candidate

    rp = tmp_foundry.run_paths(run_id)
    staged_intenttree = json.loads((rp.run / by_target["intenttree"]["staged_path"]).read_text(encoding="utf-8"))
    assert staged_intenttree["push_status"] == "skipped_no_node"

    for name in ("intenttree_client", "arc_client", "notebooklm_client", "meatywiki_client", "urlopen"):
        assert _spy_all_integration_seams[name] == []


# ---------------------------------------------------------------------------
# Missing-bundle governed result -- zero effect, zero client calls
# ---------------------------------------------------------------------------


def test_preview_missing_bundle_zero_client_calls_zero_files(
    tmp_foundry: FoundryPaths,
    monkeypatch: pytest.MonkeyPatch,
    _spy_all_integration_seams: dict[str, list[Any]],
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    assert not rp.evidence_bundle.exists()

    result = _confirm_and_invoke(
        run_id,
        ("intenttree", "arc", "notebooklm", "meatywiki", "skillmeat"),
        "idem-matrix-missing-bundle",
        tmp_foundry,
    )

    assert result.ok is True, result.error
    assert result.result["bundle_found"] is False
    assert {t["status"] for t in result.result["targets"]} == {"missing_bundle"}
    assert not (rp.run / "staging").exists()

    for name in ("intenttree_client", "arc_client", "notebooklm_client", "meatywiki_client", "urlopen"):
        assert _spy_all_integration_seams[name] == []


# ---------------------------------------------------------------------------
# Review-required policy-layer denial -- zero client calls
# ---------------------------------------------------------------------------


def test_preview_review_required_denial_zero_client_calls(
    tmp_foundry: FoundryPaths,
    monkeypatch: pytest.MonkeyPatch,
    _spy_all_integration_seams: dict[str, list[Any]],
) -> None:
    """`arc`/`meatywiki` both carry a `*_writeback_requires_review` guard
    rule (`arc_writeback_requires_review`/`work_writeback_requires_review`)
    -- requesting both together for a client-sensitive run still denies the
    WHOLE operation with the SAME `guard_review_required` reason code, zero
    client calls, zero staged files (extends the path matrix per
    orchestrator adjudication of JC-2, part 4: `meatywiki` denial path now
    covered, not just `arc`)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_run(tmp_foundry, sensitivity="client_sensitive")
    writeback_module.build_bundle(run_id, verify=False, paths=tmp_foundry)

    result = _confirm_and_invoke(run_id, ("arc", "meatywiki"), "idem-matrix-review-required", tmp_foundry)

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "guard_review_required"

    rp = tmp_foundry.run_paths(run_id)
    assert not (rp.run / "staging").exists()

    for name in ("intenttree_client", "arc_client", "notebooklm_client", "meatywiki_client", "urlopen"):
        assert _spy_all_integration_seams[name] == []
