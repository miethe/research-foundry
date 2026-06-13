"""Tests for Phase 3 RF-ARC review integration.

Covers:
- arc_review_request.schema.yaml: minimal valid + invalid instances
- _render_arc_council: candidate always written (schema-valid); offline path writes
  proposed status with no calls; online path records arc_run_id + verdict + exit mapping;
  requires_review holds the push
- writeback() dispatch: 'arc' in targets writes candidate; arc_review_path on result
- rf council --via arc: approve->0, block->7; falls back to local when ARC unreachable
- ARCCouncilAdapter: available() / degraded mode / real mode
- Governance: arc target triggers arc_writeback_requires_review for work_sensitive
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import load_yaml

_IDEA = (
    "ARC integration test: validating RF->ARC council review dispatch for "
    "evidence bundles with claim traceability."
)
_SOURCE_TEXT = (
    "Evidence bundles carry sources, claims, and reports in one auditable package. "
    "ARC council reviews validate quality before writeback. Claim ledgers map every "
    "material claim to an evidence id. Limitations: small test scope."
)


def _build_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
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
        title="ARC integration test source",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestArcReviewRequestSchema:
    """arc_review_request.schema.yaml coverage."""

    def test_minimal_valid_instance_passes(self):
        instance = {
            "id": "arc_review_run_test",
            "run_id": "run_test",
            "evidence_bundle_id": "eb_test",
            "target": "runs/run_test/evidence_bundle.yaml",
            "objective": "Review evidence bundle quality.",
            "council": "research-review-council",
            "roles": ["domain_reviewer"],
            "claims_for_review": [],
            "rf_exit_code": 7,
            "status": "proposed",
            "governance_context": {"sensitivity": "personal", "requires_review": False},
        }
        result = validate(instance, "arc_review_request")
        assert result.ok, f"expected valid, got: {result.errors}"

    def test_invalid_when_required_id_missing(self):
        instance = {
            "run_id": "run_test",
            "evidence_bundle_id": "eb_test",
            "target": "runs/run_test/evidence_bundle.yaml",
            "objective": "Review evidence bundle quality.",
            "council": "research-review-council",
            "roles": ["domain_reviewer"],
            "claims_for_review": [],
            "rf_exit_code": 7,
            "status": "proposed",
            "governance_context": {},
        }
        result = validate(instance, "arc_review_request")
        assert not result.ok

    def test_invalid_status_value(self):
        instance = {
            "id": "arc_review_run_test",
            "run_id": "run_test",
            "evidence_bundle_id": "eb_test",
            "target": "runs/run_test/evidence_bundle.yaml",
            "objective": "Review evidence bundle quality.",
            "council": "research-review-council",
            "roles": ["domain_reviewer"],
            "claims_for_review": [],
            "rf_exit_code": 0,
            "status": "invalid_status_value",
            "governance_context": {},
        }
        result = validate(instance, "arc_review_request")
        assert not result.ok

    def test_valid_with_verdict_and_arc_run_id(self):
        instance = {
            "id": "arc_review_run_test",
            "run_id": "run_test",
            "arc_run_id": "arc_run_abc",
            "evidence_bundle_id": "eb_test",
            "target": "runs/run_test/evidence_bundle.yaml",
            "objective": "Review evidence bundle.",
            "council": "research-review-council",
            "roles": ["domain_reviewer", "claim_critic"],
            "claims_for_review": [{"claim_id": "clm_001", "text": "foo", "status": "supported"}],
            "verdict": "approve",
            "rf_exit_code": 0,
            "status": "approved",
            "governance_context": {"sensitivity": "personal", "requires_review": False, "profile": "personal"},
        }
        result = validate(instance, "arc_review_request")
        assert result.ok, f"expected valid, got: {result.errors}"


# ---------------------------------------------------------------------------
# _render_arc_council: offline + online paths
# ---------------------------------------------------------------------------


class TestRenderArcCouncil:
    """_render_arc_council writes a schema-valid candidate in all code paths."""

    def test_offline_writes_proposed_candidate(self, tmp_foundry: FoundryPaths):
        """With ARC unavailable, candidate is written with status=proposed, no calls."""
        run_id = _build_run(tmp_foundry)
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_arc_council,
            _sensitivity,
            build_bundle,
        )
        from research_foundry.ids import bundle_id

        build_bundle(run_id, verify=True, paths=tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)
        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)
        sensitivity = _sensitivity(rp)

        # ARC unavailable: scaffold_review should NOT be called
        with patch(
            "research_foundry.integrations.arc.ArcClient.available",
            return_value=False,
        ) as mock_avail:
            path = _render_arc_council(
                rp, tmp_foundry,
                bundle_ident=bundle_ident,
                ledger=ledger,
                sensitivity=sensitivity,
                requires_review=False,
            )

        assert path.exists()
        candidate = load_yaml(path)
        assert candidate["status"] == "proposed"
        assert candidate["arc_run_id"] is None
        result = validate(candidate, "arc_review_request")
        assert result.ok, f"schema invalid: {result.errors}"

    def test_requires_review_holds_push(self, tmp_foundry: FoundryPaths):
        """When requires_review=True, candidate stays proposed and no ARC calls are made."""
        run_id = _build_run(tmp_foundry)
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_arc_council,
            _sensitivity,
            build_bundle,
        )
        from research_foundry.ids import bundle_id

        build_bundle(run_id, verify=True, paths=tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)
        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)
        sensitivity = "work_sensitive"

        scaffold_called = []

        def _fake_scaffold(payload: dict[str, Any]) -> dict[str, Any] | None:
            scaffold_called.append(payload)
            return {"run_id": "arc_run_xyz"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", side_effect=_fake_scaffold),
        ):
            path = _render_arc_council(
                rp, tmp_foundry,
                bundle_ident=bundle_ident,
                ledger=ledger,
                sensitivity=sensitivity,
                requires_review=True,  # requires_review holds the push
            )

        assert path.exists()
        candidate = load_yaml(path)
        assert candidate["status"] == "proposed"
        assert candidate["arc_run_id"] is None
        assert len(scaffold_called) == 0, "scaffold_review should NOT be called when requires_review=True"

    def test_online_path_records_arc_run_id_and_approve_verdict(self, tmp_foundry: FoundryPaths):
        """Online path: scaffold_review called, arc_run_id persisted, verdict mapped, exit 0."""
        run_id = _build_run(tmp_foundry)
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_arc_council,
            _sensitivity,
            build_bundle,
        )
        from research_foundry.ids import bundle_id

        build_bundle(run_id, verify=True, paths=tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)
        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)
        sensitivity = _sensitivity(rp)

        arc_response = {"run_id": "arc_run_test_abc"}
        run_record = {"run_id": "arc_run_test_abc", "verdict": "approve"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
        ):
            path = _render_arc_council(
                rp, tmp_foundry,
                bundle_ident=bundle_ident,
                ledger=ledger,
                sensitivity=sensitivity,
                requires_review=False,
            )

        assert path.exists()
        candidate = load_yaml(path)
        assert candidate["arc_run_id"] == "arc_run_test_abc"
        assert candidate["verdict"] == "approve"
        assert candidate["rf_exit_code"] == 0
        assert candidate["status"] == "approved"
        result = validate(candidate, "arc_review_request")
        assert result.ok, f"schema invalid: {result.errors}"

    def test_online_path_block_verdict_maps_exit_7(self, tmp_foundry: FoundryPaths):
        """Online path with block verdict: rf_exit_code=7, status=block."""
        run_id = _build_run(tmp_foundry)
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_arc_council,
            _sensitivity,
            build_bundle,
        )
        from research_foundry.ids import bundle_id

        build_bundle(run_id, verify=True, paths=tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)
        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)
        sensitivity = _sensitivity(rp)

        arc_response = {"run_id": "arc_run_block_test"}
        run_record = {"run_id": "arc_run_block_test", "verdict": "block"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
        ):
            path = _render_arc_council(
                rp, tmp_foundry,
                bundle_ident=bundle_ident,
                ledger=ledger,
                sensitivity=sensitivity,
                requires_review=False,
            )

        candidate = load_yaml(path)
        assert candidate["verdict"] == "block"
        assert candidate["rf_exit_code"] == 7
        assert candidate["status"] == "block"

    def test_concern_verdict_maps_exit_7(self, tmp_foundry: FoundryPaths):
        """concern verdict maps to rf_exit_code=7 (same as block)."""
        run_id = _build_run(tmp_foundry)
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_arc_council,
            _sensitivity,
            build_bundle,
        )
        from research_foundry.ids import bundle_id

        build_bundle(run_id, verify=True, paths=tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)
        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)
        sensitivity = _sensitivity(rp)

        arc_response = {"run_id": "arc_run_concern"}
        run_record = {"run_id": "arc_run_concern", "verdict": "concern"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
        ):
            path = _render_arc_council(
                rp, tmp_foundry,
                bundle_ident=bundle_ident,
                ledger=ledger,
                sensitivity=sensitivity,
                requires_review=False,
            )

        candidate = load_yaml(path)
        assert candidate["verdict"] == "concern"
        assert candidate["rf_exit_code"] == 7


# ---------------------------------------------------------------------------
# writeback() dispatch
# ---------------------------------------------------------------------------


class TestWritebackArcDispatch:
    """writeback() with 'arc' in targets writes the candidate."""

    def test_writeback_arc_target_writes_candidate(self, tmp_foundry: FoundryPaths):
        """'arc' in targets causes arc_review_request.yaml to be written."""
        from research_foundry.services import writeback as svc

        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        with patch("research_foundry.integrations.arc.ArcClient.available", return_value=False):
            result = svc.writeback(
                run_id,
                targets=("arc",),
                paths=tmp_foundry,
            )

        assert result.arc_review_path is not None
        assert result.arc_review_path.exists()
        candidate = load_yaml(result.arc_review_path)
        assert candidate["run_id"] == run_id
        v_result = validate(candidate, "arc_review_request")
        assert v_result.ok, f"schema invalid: {v_result.errors}"

    def test_writeback_without_arc_target_no_candidate(self, tmp_foundry: FoundryPaths):
        """Without 'arc' in targets, arc_review_path is None."""
        from research_foundry.services import writeback as svc

        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        result = svc.writeback(
            run_id,
            targets=("ccdash",),
            paths=tmp_foundry,
        )

        assert result.arc_review_path is None

    def test_writeback_arc_online_records_verdict(self, tmp_foundry: FoundryPaths):
        """Online ARC dispatch records arc_run_id + verdict."""
        from research_foundry.services import writeback as svc

        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        arc_response = {"run_id": "arc_run_dispatch_test"}
        run_record = {"run_id": "arc_run_dispatch_test", "verdict": "approve"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
        ):
            result = svc.writeback(
                run_id,
                targets=("arc",),
                paths=tmp_foundry,
            )

        assert result.arc_review_path is not None
        candidate = load_yaml(result.arc_review_path)
        assert candidate["arc_run_id"] == "arc_run_dispatch_test"
        assert candidate["verdict"] == "approve"
        assert candidate["rf_exit_code"] == 0


# ---------------------------------------------------------------------------
# rf council --via arc CLI
# ---------------------------------------------------------------------------


class TestCouncilViaArcCLI:
    """rf council --via arc exits 0 on approve, 7 on block; falls back when unreachable."""

    def test_via_arc_approve_exits_0(self, tmp_foundry: FoundryPaths):
        from typer.testing import CliRunner

        from research_foundry.cli import app

        run_id = _build_run(tmp_foundry)

        arc_response = {"run_id": "arc_run_cli_approve"}
        run_record = {"run_id": "arc_run_cli_approve", "verdict": "approve"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
            patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["council", run_id, "--via", "arc"])

        assert result.exit_code == 0, f"expected 0 on approve, got {result.exit_code}: {result.output}"

    def test_via_arc_block_exits_7(self, tmp_foundry: FoundryPaths):
        from typer.testing import CliRunner

        from research_foundry.cli import app

        run_id = _build_run(tmp_foundry)

        arc_response = {"run_id": "arc_run_cli_block"}
        run_record = {"run_id": "arc_run_cli_block", "verdict": "block"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
            patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["council", run_id, "--via", "arc"])

        assert result.exit_code == 7, f"expected 7 on block, got {result.exit_code}: {result.output}"

    def test_via_arc_fallback_to_local_when_unreachable(self, tmp_foundry: FoundryPaths):
        """When ARC is unreachable, falls back to local council (exits 0)."""
        from typer.testing import CliRunner

        from research_foundry.cli import app

        run_id = _build_run(tmp_foundry)

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=False),
            patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["council", run_id, "--via", "arc"])

        # Local fallback should succeed (deterministic council exits 0)
        assert result.exit_code == 0, f"fallback should succeed, got {result.exit_code}: {result.output}"
        assert "fallback" in result.output.lower() or "local" in result.output.lower()

    def test_via_local_uses_existing_council_review(self, tmp_foundry: FoundryPaths):
        """--via local uses the existing deterministic council path."""
        from typer.testing import CliRunner

        from research_foundry.cli import app

        run_id = _build_run(tmp_foundry)

        with patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry):
            runner = CliRunner()
            result = runner.invoke(app, ["council", run_id, "--via", "local"])

        assert result.exit_code == 0
        assert "council review" in result.output.lower()


# ---------------------------------------------------------------------------
# ARCCouncilAdapter
# ---------------------------------------------------------------------------


class TestARCCouncilAdapter:
    """ARCCouncilAdapter degrades cleanly when ARC is unavailable."""

    def test_adapter_registered(self):
        from research_foundry.adapters import load_all

        adapters = load_all()
        assert "arc_council" in adapters

    def test_adapter_available_false_when_arc_down(self):
        from research_foundry.adapters.arc_council import ARCCouncilAdapter

        adapter = ARCCouncilAdapter()
        with patch("research_foundry.integrations.arc.ArcClient.available", return_value=False):
            assert adapter.available() is False

    def test_adapter_available_true_when_arc_up(self):
        from research_foundry.adapters.arc_council import ARCCouncilAdapter

        adapter = ARCCouncilAdapter()
        with patch("research_foundry.integrations.arc.ArcClient.available", return_value=True):
            assert adapter.available() is True

    def test_degraded_when_unavailable(self):
        from research_foundry.adapters.arc_council import ARCCouncilAdapter

        adapter = ARCCouncilAdapter()
        with patch("research_foundry.integrations.arc.ArcClient.available", return_value=False):
            result = adapter.run({"objective": "test"})

        assert result.degraded is True
        assert any("arc unreachable" in n for n in result.notes)
        assert result.adapter == "arc_council"

    def test_real_mode_submits_brief(self):
        from research_foundry.adapters.arc_council import ARCCouncilAdapter

        adapter = ARCCouncilAdapter()
        arc_response = {"run_id": "arc_run_adapter_test"}
        run_record = {"run_id": "arc_run_adapter_test", "verdict": "approve"}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=arc_response),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
        ):
            result = adapter.run({"objective": "test review", "council": "research-review-council"})

        assert result.degraded is False
        assert result.artifacts.get("arc_verdict") == "approve"
        assert result.artifacts.get("arc_run_id") == "arc_run_adapter_test"

    def test_degrades_when_scaffold_returns_none(self):
        from research_foundry.adapters.arc_council import ARCCouncilAdapter

        adapter = ARCCouncilAdapter()
        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch("research_foundry.integrations.arc.ArcClient.scaffold_review", return_value=None),
        ):
            result = adapter.run({"objective": "test"})

        assert result.degraded is True


# ---------------------------------------------------------------------------
# Governance: arc_writeback_requires_review
# ---------------------------------------------------------------------------


class TestArcGovernanceRule:
    """arc_writeback_requires_review fires for work_sensitive + arc target."""

    def test_arc_requires_review_for_work_sensitive(self):
        from research_foundry.services.governance import GuardContext, guard_check
        from research_foundry.paths import FoundryPaths

        ctx = GuardContext(
            profile="work_approved",
            sensitivity="work_sensitive",
            source_sensitivities=("work_sensitive",),
            writeback_targets=("arc",),
        )
        result = guard_check(ctx)
        assert not result.passed
        rule_ids = [v.rule_id for v in result.violations]
        assert "arc_writeback_requires_review" in rule_ids
        assert result.exit_code == 7

    def test_arc_personal_profile_permits_without_review(self):
        from research_foundry.services.governance import GuardContext, guard_check

        ctx = GuardContext(
            profile="personal",
            sensitivity="personal",
            writeback_targets=("arc",),
        )
        result = guard_check(ctx)
        # personal sensitivity + arc target should not trigger arc_writeback_requires_review
        rule_ids = [v.rule_id for v in result.violations]
        assert "arc_writeback_requires_review" not in rule_ids

    def test_arc_client_sensitive_also_requires_review(self):
        from research_foundry.services.governance import GuardContext, guard_check

        ctx = GuardContext(
            profile="client_approved",
            sensitivity="client_sensitive",
            source_sensitivities=("client_sensitive",),
            writeback_targets=("arc",),
        )
        result = guard_check(ctx)
        rule_ids = [v.rule_id for v in result.violations]
        assert "arc_writeback_requires_review" in rule_ids

    def test_three_permitted_profiles_for_arc(self):
        """personal, work_approved, client_approved may target arc (governance check,
        no block solely from profile mismatch on arc target)."""
        from research_foundry.services.governance import GuardContext, guard_check

        for profile in ("personal", "work_approved", "client_approved"):
            ctx = GuardContext(
                profile=profile,
                sensitivity="personal",
                writeback_targets=("arc",),
            )
            result = guard_check(ctx)
            # arc target with personal sensitivity should not block
            block_violations = [v for v in result.violations if v.severity == "block"]
            assert not block_violations, (
                f"profile={profile} should not block arc target with personal sensitivity, "
                f"got: {block_violations}"
            )
