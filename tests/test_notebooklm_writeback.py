"""Tests for the NotebookLM writeback integration (Phase 4, _render_notebooklm_update).

Covers:
- _render_notebooklm_update always writes notebooklm_update.yaml (schema-valid)
- offline client → push_status='skipped_offline' (client.available()=False)
- notebook not resolved → push_status='skipped_no_notebook'
- requires_review=True → push_status='skipped_requires_review'
- never raises into pipeline from any path
- writeback() with 'notebooklm' in targets writes the candidate yaml
- writeback() without 'notebooklm' in targets → notebooklm_update_path is None
- WritebackResult.notebooklm_update_path is set correctly
- schema validates with jsonschema via research_foundry.schemas.validate
- RunPaths.notebooklm_update property returns correct path
- default writeback() targets unchanged when 'notebooklm' not requested
- governance: notebooklm_writeback_requires_review would mirror arc rule
  (guard_check with 'notebooklm' target + work_sensitive)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services import writeback as svc
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import load_yaml

# ---------------------------------------------------------------------------
# Pipeline helper (same as ARC test — builds a real run on disk)
# ---------------------------------------------------------------------------


_IDEA = (
    "Research how NotebookLM grounded synthesis should integrate with the "
    "Research Foundry evidence pipeline and claim traceability model."
)

_SOURCE_TEXT = (
    "NotebookLM provides grounded Q&A backed by uploaded sources. "
    "Integrating NLM with a research control plane requires mapping synthesized "
    "answers to evidence cards so every material claim is traceable. "
    "Offline mode must degrade gracefully without blocking the pipeline. "
    "Limitations: this test uses stub content; real NLM requires auth."
)


def _build_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    """Drive the deterministic pipeline and return the run_id."""
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
        title="NLM integration test source",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


# ---------------------------------------------------------------------------
# RunPaths.notebooklm_update property
# ---------------------------------------------------------------------------


class TestRunPathsNotebooklmUpdate:
    def test_notebooklm_update_path_under_writebacks(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)
        expected = rp.writebacks / "notebooklm_update.yaml"
        assert rp.notebooklm_update == expected


# ---------------------------------------------------------------------------
# _render_notebooklm_update — offline path
# ---------------------------------------------------------------------------


class TestRenderNotebooklmUpdateOffline:
    """When NotebookLM client is unavailable, candidate is written with correct push_status."""

    def _call_render(self, run_id: str, paths: FoundryPaths, **kwargs: Any) -> Path:
        from research_foundry.ids import bundle_id
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_notebooklm_update,
        )

        svc.build_bundle(run_id, verify=True, paths=paths)
        rp = paths.run_paths(run_id)
        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)
        return _render_notebooklm_update(
            rp,
            paths,
            bundle_ident=bundle_ident,
            ledger=ledger,
            requires_review=kwargs.get("requires_review", False),
        )

    def test_always_writes_yaml(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            path = self._call_render(run_id, tmp_foundry)
        assert path.exists()

    def test_push_status_skipped_offline_when_client_unavailable(
        self, tmp_foundry: FoundryPaths
    ):
        """Client says available()=False after notebook resolved → push_status skipped_offline."""
        run_id = _build_run(tmp_foundry)

        # Patch correlation at the module level (lazily imported inside _render_notebooklm_update)
        # and client.available() to False to simulate the offline scenario.
        with (
            patch(
                "research_foundry.services.notebook_correlation.resolve_notebook",
                return_value={
                    "notebook_id": "nb_offline_test",
                    "notebook_title": "RF — test-proj",
                    "project": "test-proj",
                    "run_id": run_id,
                    "mode": "project",
                },
            ),
            patch(
                "research_foundry.integrations.notebooklm.NotebookLMClient.available",
                return_value=False,
            ),
        ):
            path = self._call_render(run_id, tmp_foundry)

        candidate = load_yaml(path)
        assert candidate["push_status"] == "skipped_offline"

    def test_push_status_skipped_no_notebook_when_no_correlation(
        self, tmp_foundry: FoundryPaths
    ):
        """Notebook correlation returns None → push_status skipped_no_notebook."""
        run_id = _build_run(tmp_foundry)

        with (
            patch(
                "research_foundry.services.notebook_correlation.resolve_notebook",
                return_value=None,
            ),
            patch(
                "research_foundry.integrations.notebooklm.NotebookLMClient.available",
                return_value=False,
            ),
        ):
            path = self._call_render(run_id, tmp_foundry)

        candidate = load_yaml(path)
        assert candidate["push_status"] == "skipped_no_notebook"

    def test_push_status_skipped_requires_review(self, tmp_foundry: FoundryPaths):
        """requires_review=True → push_status skipped_requires_review."""
        run_id = _build_run(tmp_foundry)

        # Patch correlation at the module level so notebook_id is resolved.
        with patch(
            "research_foundry.services.notebook_correlation.resolve_notebook",
            return_value={
                "notebook_id": "nb_review_test",
                "notebook_title": "RF — test-proj",
                "project": "test-proj",
                "run_id": run_id,
                "mode": "project",
            },
        ):
            path = self._call_render(run_id, tmp_foundry, requires_review=True)

        candidate = load_yaml(path)
        assert candidate["push_status"] == "skipped_requires_review"

    def test_candidate_is_schema_valid(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            path = self._call_render(run_id, tmp_foundry)

        candidate = load_yaml(path)
        result = validate(candidate, "notebooklm_update")
        assert result.ok, f"schema invalid: {result.errors}"

    def test_candidate_has_required_fields(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            path = self._call_render(run_id, tmp_foundry)

        candidate = load_yaml(path)
        assert "run_id" in candidate
        assert "update_timestamp" in candidate
        assert "status" in candidate
        assert "push_status" in candidate
        assert candidate["run_id"] == run_id
        assert candidate["status"] == "proposed"

    def test_never_raises(self, tmp_foundry: FoundryPaths):
        """Even with a broken correlation import, _render_notebooklm_update returns cleanly."""
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)
        rp = tmp_foundry.run_paths(run_id)

        from research_foundry.ids import bundle_id
        from research_foundry.services.writeback import (
            _ledger,
            _load_bundle,
            _render_notebooklm_update,
        )

        bundle = _load_bundle(rp)
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))
        ledger = _ledger(rp)

        # Simulate correlation service entirely broken.
        with patch(
            "research_foundry.services.notebook_correlation.resolve_notebook",
            side_effect=RuntimeError("correlation failure"),
        ):
            # Must not raise.
            path = _render_notebooklm_update(
                rp,
                tmp_foundry,
                bundle_ident=bundle_ident,
                ledger=ledger,
                requires_review=False,
            )

        assert path.exists()


# ---------------------------------------------------------------------------
# writeback() dispatch
# ---------------------------------------------------------------------------


class TestWritebackNotebooklmDispatch:
    def test_notebooklm_target_writes_candidate(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            result = svc.writeback(
                run_id,
                targets=("notebooklm",),
                paths=tmp_foundry,
            )

        assert result.notebooklm_update_path is not None
        assert result.notebooklm_update_path.exists()

    def test_candidate_yaml_is_schema_valid(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            result = svc.writeback(
                run_id,
                targets=("notebooklm",),
                paths=tmp_foundry,
            )

        candidate = load_yaml(result.notebooklm_update_path)
        v = validate(candidate, "notebooklm_update")
        assert v.ok, f"schema invalid: {v.errors}"

    def test_candidate_run_id_matches(self, tmp_foundry: FoundryPaths):
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            result = svc.writeback(
                run_id,
                targets=("notebooklm",),
                paths=tmp_foundry,
            )

        candidate = load_yaml(result.notebooklm_update_path)
        assert candidate["run_id"] == run_id

    def test_without_notebooklm_target_path_is_none(self, tmp_foundry: FoundryPaths):
        """'notebooklm' not in targets → notebooklm_update_path is None."""
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        result = svc.writeback(
            run_id,
            targets=("ccdash",),
            paths=tmp_foundry,
        )

        assert result.notebooklm_update_path is None

    def test_default_targets_do_not_include_notebooklm(self, tmp_foundry: FoundryPaths):
        """Default writeback() targets=(meatywiki, skillmeat, ccdash) exclude notebooklm."""
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        result = svc.writeback(run_id, paths=tmp_foundry)

        assert result.notebooklm_update_path is None

    def test_push_status_proposed_in_offline_run(self, tmp_foundry: FoundryPaths):
        """Candidate push_status is 'skipped_offline' or 'skipped_no_notebook' when offline."""
        run_id = _build_run(tmp_foundry)
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        with patch(
            "research_foundry.integrations.notebooklm.NotebookLMClient.available",
            return_value=False,
        ):
            result = svc.writeback(
                run_id,
                targets=("notebooklm",),
                paths=tmp_foundry,
            )

        candidate = load_yaml(result.notebooklm_update_path)
        assert candidate["push_status"] in (
            "skipped_offline",
            "skipped_no_notebook",
            "proposed",
        )

    def test_work_sensitive_sets_requires_review(self, tmp_foundry: FoundryPaths):
        """work_sensitive run sets requires_review → push_status skipped_requires_review."""
        run_id = _build_run(tmp_foundry, sensitivity="work_sensitive")
        svc.build_bundle(run_id, verify=True, paths=tmp_foundry)

        # Patch correlation at the module level so notebook_id is resolved,
        # ensuring the requires_review gate is reached (not skipped_no_notebook).
        with patch(
            "research_foundry.services.notebook_correlation.resolve_notebook",
            return_value={
                "notebook_id": "nb_work_test",
                "notebook_title": "RF — work-project",
                "project": "work-project",
                "run_id": run_id,
                "mode": "project",
            },
        ):
            result = svc.writeback(
                run_id,
                targets=("notebooklm",),
                paths=tmp_foundry,
            )

        assert result.requires_review is True
        candidate = load_yaml(result.notebooklm_update_path)
        assert candidate["push_status"] == "skipped_requires_review"


# ---------------------------------------------------------------------------
# Schema validation — valid / invalid instances
# ---------------------------------------------------------------------------


class TestNotebooklmUpdateSchema:
    """notebooklm_update.schema.yaml: minimal valid and invalid instances."""

    def test_minimal_valid_instance(self):
        instance = {
            "run_id": "rf_run_test",
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "proposed",
            "push_status": "proposed",
        }
        result = validate(instance, "notebooklm_update")
        assert result.ok, f"expected valid, got: {result.errors}"

    def test_full_valid_instance(self):
        instance = {
            "run_id": "rf_run_test",
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "live_pushed",
            "push_status": "pushed",
            "notebook_id": "nb_abc123",
            "notebook_title": "RF — test-project",
            "project": "test-project",
            "evidence_bundle_id": "eb_test",
            "pushed_source_ids": [
                {"nlm_source_id": "src_001", "rf_source_card_id": "sc_001"},
            ],
            "artifact_links": [
                {"type": "report", "path": "runs/rf_run_test/reports/report.md", "label": "Report"},
            ],
            "node_id": None,
        }
        result = validate(instance, "notebooklm_update")
        assert result.ok, f"expected valid, got: {result.errors}"

    def test_invalid_when_run_id_missing(self):
        instance = {
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "proposed",
            "push_status": "proposed",
        }
        result = validate(instance, "notebooklm_update")
        assert not result.ok

    def test_invalid_push_status_enum(self):
        instance = {
            "run_id": "rf_run_test",
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "proposed",
            "push_status": "not_a_valid_push_status",
        }
        result = validate(instance, "notebooklm_update")
        assert not result.ok

    def test_invalid_status_enum(self):
        instance = {
            "run_id": "rf_run_test",
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "invalid_status",
            "push_status": "proposed",
        }
        result = validate(instance, "notebooklm_update")
        assert not result.ok

    def test_null_notebook_id_is_valid(self):
        instance = {
            "run_id": "rf_run_test",
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "proposed",
            "push_status": "skipped_no_notebook",
            "notebook_id": None,
        }
        result = validate(instance, "notebooklm_update")
        assert result.ok, f"null notebook_id should be valid, got: {result.errors}"

    def test_additional_properties_allowed(self):
        """additionalProperties: true — extra fields pass validation."""
        instance = {
            "run_id": "rf_run_test",
            "update_timestamp": "2026-06-13T09:41:00-04:00",
            "status": "proposed",
            "push_status": "proposed",
            "extra_custom_field": "some-value",
        }
        result = validate(instance, "notebooklm_update")
        assert result.ok, f"additional properties should be allowed, got: {result.errors}"
