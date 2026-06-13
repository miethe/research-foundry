"""Tests for Phase 1 IntentTree outbound writeback integration.

Covers:
- intenttree_update candidate is schema-valid
- writeback() dispatch writes candidate when "intenttree" in targets
- online path (mock IntentTreeClient.available()=True) calls patch_node + add_node_artifact
- offline path writes candidate and makes no live calls
- requires_review holds the push (candidate proposed, no calls)
- governance: intenttree permitted for personal/work_approved/client_approved
- guard_check fires intenttree_writeback_requires_review for work-sensitive
- push_status: milestone stages trigger PATCH, non-milestones do not
- rf status push CLI command
- RunPaths.intenttree_update property
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services import telemetry, writeback
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.governance import GuardContext, guard_check
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import load_yaml

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
    paths: FoundryPaths,
    *,
    sensitivity: str = "personal",
    create_tree_node: bool = True,
) -> str:
    """Drive the deterministic pipeline and return the run_id."""
    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, create_tree_node=create_tree_node, paths=paths)
    assert tri.intent_id
    plan = plan_run(tri.intent_id, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / "input_source.txt"
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


def _inject_node_ref(paths: FoundryPaths, run_id: str, node_id: str = "node_test_123") -> None:
    """Inject intenttree_node_ref into the run's intent (simulates IntentTree dispatch)."""
    from research_foundry.yamlio import load_yaml, dump_yaml

    rp = paths.run_paths(run_id)
    run_meta = load_yaml(rp.run_yaml) or {}
    intent_id = str(run_meta.get("intent_id") or "")
    if intent_id:
        intent_path = paths.intents_active / f"{intent_id}.yaml"
        if intent_path.exists():
            intent = load_yaml(intent_path) or {}
            intent["intenttree_node_ref"] = node_id
            dump_yaml(intent, intent_path)


# ---------------------------------------------------------------------------
# RunPaths property
# ---------------------------------------------------------------------------


def test_run_paths_intenttree_update_property(tmp_foundry: FoundryPaths):
    rp = tmp_foundry.run_paths("rf_run_test")
    assert rp.intenttree_update == rp.run / "writebacks" / "intenttree_update.yaml"


# ---------------------------------------------------------------------------
# Schema validation of the candidate
# ---------------------------------------------------------------------------


def test_intenttree_update_candidate_is_schema_valid(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)
    assert result.intenttree_update_path is not None
    assert result.intenttree_update_path.exists()

    candidate = load_yaml(result.intenttree_update_path)
    vr = validate(candidate, "intenttree_update")
    assert vr.ok, f"Schema errors: {vr.errors}"


def test_candidate_fields_are_populated(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)
    candidate = load_yaml(result.intenttree_update_path)

    assert candidate["run_id"] == run_id
    assert candidate["update_timestamp"]
    assert candidate["status"] in {"in_progress", "completed"}
    assert isinstance(candidate["claims_total"], int)
    assert isinstance(candidate["claims_supported"], int)
    assert isinstance(candidate["verification_passed"], bool)
    assert isinstance(candidate["artifact_links"], list)
    assert any(a["type"] == "evidence_bundle" for a in candidate["artifact_links"])
    assert candidate["push_status"] in {
        "proposed", "pushed", "skipped_offline", "skipped_requires_review", "skipped_no_node"
    }


# ---------------------------------------------------------------------------
# Dispatch: writeback() writes candidate when "intenttree" in targets
# ---------------------------------------------------------------------------


def test_writeback_dispatch_writes_intenttree_candidate(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)

    assert result.intenttree_update_path is not None
    assert result.intenttree_update_path.exists()
    # Other targets were not requested
    assert result.meatywiki_path is None
    assert result.skillbom_path is None


def test_writeback_dispatch_all_targets_includes_intenttree(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(
        run_id, targets=("meatywiki", "skillmeat", "ccdash", "intenttree"), paths=paths
    )

    assert result.intenttree_update_path is not None
    assert result.intenttree_update_path.exists()
    # Other targets also written
    assert result.meatywiki_path and result.meatywiki_path.exists()
    assert result.skillbom_path and result.skillbom_path.exists()
    assert result.ccdash_path and result.ccdash_path.exists()


def test_writeback_without_intenttree_target_does_not_write_candidate(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, targets=("meatywiki", "ccdash"), paths=paths)

    assert result.intenttree_update_path is None


# ---------------------------------------------------------------------------
# Online path: calls patch_node + add_node_artifact when available
# ---------------------------------------------------------------------------


def _make_urlopen_mock(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_online_path_calls_patch_node_and_add_node_artifact(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _inject_node_ref(paths, run_id, "node_online_test")

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=True,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
            return_value={"node_id": "node_online_test", "status": "in_progress"},
        ) as mock_patch,
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.add_node_artifact",
            return_value={"artifact_id": "art_1"},
        ) as mock_add,
    ):
        result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)

    assert result.intenttree_update_path and result.intenttree_update_path.exists()

    # patch_node was called exactly once with the node_id
    mock_patch.assert_called_once()
    call_args = mock_patch.call_args
    assert call_args[0][0] == "node_online_test"
    payload_sent = call_args[0][1]
    assert "status" in payload_sent

    # add_node_artifact was called at least once (one per artifact link)
    assert mock_add.call_count >= 1
    artifact_node_ids = {c[0][0] for c in mock_add.call_args_list}
    assert "node_online_test" in artifact_node_ids

    # candidate reflects push_status=pushed
    candidate = load_yaml(result.intenttree_update_path)
    assert candidate["push_status"] == "pushed"


# ---------------------------------------------------------------------------
# Offline path: candidate written, no HTTP calls
# ---------------------------------------------------------------------------


def test_offline_path_writes_candidate_and_makes_no_calls(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _inject_node_ref(paths, run_id, "node_offline_test")

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=False,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
        ) as mock_patch,
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.add_node_artifact",
        ) as mock_add,
    ):
        result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)

    # Candidate still exists
    assert result.intenttree_update_path and result.intenttree_update_path.exists()

    # No live calls made
    mock_patch.assert_not_called()
    mock_add.assert_not_called()

    # push_status indicates offline
    candidate = load_yaml(result.intenttree_update_path)
    assert candidate["push_status"] == "skipped_offline"


def test_no_node_ref_skips_push(tmp_foundry: FoundryPaths):
    """Without intenttree_node_ref, the candidate is written with push_status=skipped_no_node."""
    paths = tmp_foundry
    run_id = _build_run(paths, create_tree_node=False)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    # create_tree_node=False means no intenttree_node_ref on the intent

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=True,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
        ) as mock_patch,
    ):
        result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)

    mock_patch.assert_not_called()
    candidate = load_yaml(result.intenttree_update_path)
    assert candidate["push_status"] == "skipped_no_node"
    assert candidate["node_id"] == ""


# ---------------------------------------------------------------------------
# requires_review holds the push
# ---------------------------------------------------------------------------


def test_requires_review_holds_push(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths, sensitivity="work_sensitive")
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _inject_node_ref(paths, run_id, "node_review_test")

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=True,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
        ) as mock_patch,
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.add_node_artifact",
        ) as mock_add,
    ):
        result = writeback.writeback(run_id, targets=("intenttree",), paths=paths)

    assert result.requires_review is True
    mock_patch.assert_not_called()
    mock_add.assert_not_called()

    candidate = load_yaml(result.intenttree_update_path)
    assert candidate["push_status"] == "skipped_requires_review"


def test_explicit_require_review_holds_push(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths, sensitivity="personal")
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _inject_node_ref(paths, run_id, "node_explicit_review")

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=True,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
        ) as mock_patch,
    ):
        result = writeback.writeback(
            run_id, targets=("intenttree",), require_review=True, paths=paths
        )

    assert result.requires_review is True
    mock_patch.assert_not_called()
    candidate = load_yaml(result.intenttree_update_path)
    assert candidate["push_status"] == "skipped_requires_review"


# ---------------------------------------------------------------------------
# Governance: permitted profiles + guard_check rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sensitivity,profile", [
    ("personal", "personal"),
    ("personal", "work_approved"),
    ("personal", "client_approved"),
])
def test_governance_intenttree_permitted_for_three_tiers(
    sensitivity: str, profile: str, tmp_foundry: FoundryPaths
):
    """intenttree target is permitted for personal, work_approved, client_approved profiles."""
    ctx = GuardContext(
        profile=profile,
        sensitivity=sensitivity,
        writeback_targets=("intenttree",),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    # No violations expected for non-sensitive content + permitted profiles
    assert result.passed


def test_governance_intenttree_requires_review_for_work_sensitive(tmp_foundry: FoundryPaths):
    """work_sensitive + intenttree target should trigger intenttree_writeback_requires_review."""
    ctx = GuardContext(
        profile="work_approved",
        sensitivity="work_sensitive",
        writeback_targets=("intenttree",),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert not result.passed
    rule_ids = {v.rule_id for v in result.violations}
    assert "intenttree_writeback_requires_review" in rule_ids


def test_governance_intenttree_requires_review_for_client_sensitive(tmp_foundry: FoundryPaths):
    """client_sensitive + intenttree target should trigger intenttree_writeback_requires_review."""
    ctx = GuardContext(
        profile="client_approved",
        sensitivity="client_sensitive",
        writeback_targets=("intenttree",),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert not result.passed
    rule_ids = {v.rule_id for v in result.violations}
    assert "intenttree_writeback_requires_review" in rule_ids


def test_governance_doctor_still_passes(tmp_foundry: FoundryPaths):
    """guard_check with no violations still returns exit_code=0."""
    ctx = GuardContext(
        profile="personal",
        sensitivity="personal",
        writeback_targets=("intenttree",),
    )
    result = guard_check(ctx, paths=tmp_foundry)
    assert result.passed
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# push_status: telemetry milestone callbacks
# ---------------------------------------------------------------------------


def test_push_status_milestone_calls_patch_node(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    _inject_node_ref(paths, run_id, "node_milestone")

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=True,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
            return_value={"status": "ok"},
        ) as mock_patch,
    ):
        pushed = telemetry.push_status(run_id, "verify_passed", paths=paths)

    assert pushed is True
    mock_patch.assert_called_once()
    call_args = mock_patch.call_args[0]
    assert call_args[0] == "node_milestone"
    assert call_args[1]["progress_stage"] == "verify_passed"


@pytest.mark.parametrize("stage", [
    "discovery_started",
    "sources_ingested",
    "verify_passed",
    "bundle_written",
])
def test_push_status_all_milestone_stages(stage: str, tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    _inject_node_ref(paths, run_id, "node_stages")

    with (
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.available",
            return_value=True,
        ),
        patch(
            "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
            return_value={"status": "ok"},
        ) as mock_patch,
    ):
        pushed = telemetry.push_status(run_id, stage, paths=paths)

    assert pushed is True
    mock_patch.assert_called_once()


def test_push_status_non_milestone_is_noop(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    _inject_node_ref(paths, run_id, "node_noop")

    with patch(
        "research_foundry.integrations.intenttree.IntentTreeClient.patch_node",
    ) as mock_patch:
        pushed = telemetry.push_status(run_id, "some_random_stage", paths=paths)

    assert pushed is False
    mock_patch.assert_not_called()


def test_push_status_offline_returns_false(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    _inject_node_ref(paths, run_id, "node_offline")

    with patch(
        "research_foundry.integrations.intenttree.IntentTreeClient.available",
        return_value=False,
    ):
        pushed = telemetry.push_status(run_id, "bundle_written", paths=paths)

    assert pushed is False


def test_push_status_no_node_ref_returns_false(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths, create_tree_node=False)
    # create_tree_node=False means no intenttree_node_ref on the intent

    with patch(
        "research_foundry.integrations.intenttree.IntentTreeClient.available",
        return_value=True,
    ):
        pushed = telemetry.push_status(run_id, "bundle_written", paths=paths)

    assert pushed is False


def test_push_status_never_raises(tmp_foundry: FoundryPaths):
    """push_status must swallow all exceptions silently."""
    import urllib.error

    paths = tmp_foundry
    run_id = _build_run(paths)
    _inject_node_ref(paths, run_id, "node_crash")

    with patch(
        "research_foundry.integrations.intenttree.IntentTreeClient.available",
        side_effect=RuntimeError("unexpected crash"),
    ):
        pushed = telemetry.push_status(run_id, "bundle_written", paths=paths)

    assert pushed is False


# ---------------------------------------------------------------------------
# CLI: rf status push
# ---------------------------------------------------------------------------


def test_cli_status_push_prints_pushed_when_success(tmp_foundry: FoundryPaths):
    from typer.testing import CliRunner
    from research_foundry.cli import app

    paths = tmp_foundry
    run_id = _build_run(paths)
    _inject_node_ref(paths, run_id, "node_cli_test")

    with (
        patch(
            "research_foundry.services.telemetry.push_status",
            return_value=True,
        ),
        patch("research_foundry.paths.FoundryPaths.discover", return_value=paths),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["status", "push", "--run", run_id, "--to", "intenttree"])

    assert result.exit_code == 0
    assert "pushed" in result.output


def test_cli_status_push_prints_skipped_when_offline(tmp_foundry: FoundryPaths):
    from typer.testing import CliRunner
    from research_foundry.cli import app

    paths = tmp_foundry
    run_id = _build_run(paths)

    with (
        patch(
            "research_foundry.services.telemetry.push_status",
            return_value=False,
        ),
        patch("research_foundry.paths.FoundryPaths.discover", return_value=paths),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["status", "push", "--run", run_id, "--to", "intenttree"])

    assert result.exit_code == 0
    assert "skipped" in result.output


def test_cli_status_push_unknown_target_exits_1():
    from typer.testing import CliRunner
    from research_foundry.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["status", "push", "--run", "some_run", "--to", "meatywiki"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Real patch_node / add_node_artifact (online mock)
# ---------------------------------------------------------------------------


def test_patch_node_sends_correct_url_and_payload():
    """patch_node calls PATCH /api/nodes/{node_id} with the payload."""
    import json as _json
    from unittest.mock import MagicMock

    from research_foundry.integrations.intenttree import IntentTreeClient

    captured_requests = []

    def fake_urlopen(req, timeout=None):
        captured_requests.append(req)
        resp = MagicMock()
        resp.read.return_value = _json.dumps({"node_id": "n1", "status": "updated"}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    client = IntentTreeClient(base_url="http://intenttree.test")
    payload = {"status": "completed", "progress": {"claims_total": 5}}

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = client.patch_node("n1", payload)

    assert result == {"node_id": "n1", "status": "updated"}
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.get_full_url() == "http://intenttree.test/api/nodes/n1"
    assert req.get_method() == "PATCH"
    body = _json.loads(req.data)
    assert body["status"] == "completed"


def test_add_node_artifact_sends_post_to_artifacts_endpoint():
    """add_node_artifact calls POST /api/nodes/{node_id}/artifacts."""
    import json as _json
    from unittest.mock import MagicMock

    from research_foundry.integrations.intenttree import IntentTreeClient

    captured_requests = []

    def fake_urlopen(req, timeout=None):
        captured_requests.append(req)
        resp = MagicMock()
        resp.read.return_value = _json.dumps({"artifact_id": "art_1"}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    client = IntentTreeClient(base_url="http://intenttree.test")
    artifact = {"type": "evidence_bundle", "path": "runs/x/evidence_bundle.yaml"}

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = client.add_node_artifact("n1", artifact)

    assert result == {"artifact_id": "art_1"}
    req = captured_requests[0]
    assert req.get_full_url() == "http://intenttree.test/api/nodes/n1/artifacts"
    assert req.get_method() == "POST"


def test_patch_node_returns_none_on_connection_error():
    import urllib.error
    from research_foundry.integrations.intenttree import IntentTreeClient

    client = IntentTreeClient()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        result = client.patch_node("n1", {"status": "done"})
    assert result is None


def test_add_node_artifact_returns_none_on_connection_error():
    import urllib.error
    from research_foundry.integrations.intenttree import IntentTreeClient

    client = IntentTreeClient()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        result = client.add_node_artifact("n1", {"type": "report", "path": "/x"})
    assert result is None
