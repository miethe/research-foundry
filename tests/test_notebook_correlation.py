"""Tests for services/notebook_correlation.py.

Covers:
- correlation_mode(): reads foundry.yaml; defaults to 'project'
- resolve_notebook(): project mode reuses one notebook across runs
- resolve_notebook(): run mode creates per-run notebooks
- resolve_notebook(): explicit mode records notebook_id without creation
- resolve_notebook(): degrade gracefully when client returns None / unavailable
- record_run_notebook(): idempotent; repeated writes do not duplicate entries
- notebook_for_run(): looks up by run_id; None when absent
- notebook_for_path(): parses run_id from path; delegates to notebook_for_run
- Registry round-trips via yamlio (dump_yaml/load_yaml, insertion-order preserved)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from research_foundry.paths import FoundryPaths
from research_foundry.services.notebook_correlation import (
    _parse_run_id_from_path,
    _read_registry,
    _write_registry,
    correlation_mode,
    notebook_for_path,
    notebook_for_run,
    record_run_notebook,
    resolve_notebook,
)
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_client(*, available: bool = True, notebook_id: str = "nb_test_001") -> MagicMock:
    """Return a mock NotebookLMClient with controlled availability."""
    client = MagicMock()
    client.available.return_value = available
    client.create_notebook.return_value = {
        "notebook_id": notebook_id,
        "notebook_title": f"RF — stub-{notebook_id}",
    }
    return client


# ---------------------------------------------------------------------------
# correlation_mode
# ---------------------------------------------------------------------------


class TestCorrelationMode:
    """correlation_mode() reads foundry.yaml; defaults to 'project'."""

    def test_default_is_project(self, tmp_foundry: FoundryPaths):
        mode = correlation_mode(paths=tmp_foundry)
        assert mode == "project"

    def test_reads_from_foundry_yaml(self, tmp_foundry: FoundryPaths):
        # Inject a different mode into foundry.yaml.
        foundry_yaml = tmp_foundry.root / "foundry.yaml"
        data = load_yaml(foundry_yaml) if foundry_yaml.exists() else {}
        if not isinstance(data, dict):
            data = {}
        foundry_block = data.setdefault("foundry", {})
        integrations = foundry_block.setdefault("integrations", {})
        integrations["notebooklm"] = {"correlation_mode": "run"}
        dump_yaml(data, foundry_yaml)

        mode = correlation_mode(paths=tmp_foundry)
        assert mode == "run"

    def test_fallback_on_corrupt_yaml(self, tmp_path: Path):
        # Write a non-dict foundry.yaml; should still return default.
        root = tmp_path / "corrupt"
        root.mkdir()
        (root / "foundry.yaml").write_text("- not_a_dict\n", encoding="utf-8")
        (root / "registries").mkdir()
        paths = FoundryPaths(root=root)
        mode = correlation_mode(paths=paths)
        assert mode == "project"


# ---------------------------------------------------------------------------
# resolve_notebook — project mode
# ---------------------------------------------------------------------------


class TestResolveNotebookProjectMode:
    """project mode: runs sharing a project slug share one notebook."""

    def test_returns_none_when_no_project_and_no_registry(self, tmp_foundry: FoundryPaths):
        result = resolve_notebook("run_001", mode="project", paths=tmp_foundry)
        assert result is None

    def test_creates_notebook_when_create_true_and_client_available(
        self, tmp_foundry: FoundryPaths
    ):
        client = _fake_client(notebook_id="nb_proj_001")
        result = resolve_notebook(
            "run_001",
            project="my-project",
            mode="project",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert result is not None
        assert result["notebook_id"] == "nb_proj_001"
        assert result["project"] == "my-project"
        assert result["run_id"] == "run_001"
        assert result["mode"] == "project"
        client.create_notebook.assert_called_once()

    def test_second_run_reuses_same_notebook(self, tmp_foundry: FoundryPaths):
        """Two runs with the same project slug share one notebook (no second create)."""
        client = _fake_client(notebook_id="nb_proj_shared")
        # First run creates the notebook.
        resolve_notebook(
            "run_001",
            project="shared-project",
            mode="project",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert client.create_notebook.call_count == 1

        # Second run reuses the existing notebook — no new creation.
        result2 = resolve_notebook(
            "run_002",
            project="shared-project",
            mode="project",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert result2 is not None
        assert result2["notebook_id"] == "nb_proj_shared"
        assert result2["run_id"] == "run_002"
        # Still only one create_notebook call.
        assert client.create_notebook.call_count == 1

    def test_no_create_when_client_unavailable(self, tmp_foundry: FoundryPaths):
        client = _fake_client(available=False)
        result = resolve_notebook(
            "run_001",
            project="my-project",
            mode="project",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert result is None
        client.create_notebook.assert_not_called()

    def test_no_create_when_create_false(self, tmp_foundry: FoundryPaths):
        client = _fake_client(notebook_id="nb_should_not_create")
        result = resolve_notebook(
            "run_001",
            project="my-project",
            mode="project",
            create=False,
            client=client,
            paths=tmp_foundry,
        )
        assert result is None
        client.create_notebook.assert_not_called()

    def test_degrade_when_create_notebook_returns_none(self, tmp_foundry: FoundryPaths):
        client = MagicMock()
        client.available.return_value = True
        client.create_notebook.return_value = None  # network failure
        result = resolve_notebook(
            "run_001",
            project="my-project",
            mode="project",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert result is None

    def test_fallback_to_run_entry_when_no_project_given(self, tmp_foundry: FoundryPaths):
        """If project is None but the run is already recorded, return that entry."""
        record_run_notebook("run_x", "nb_fallback", project="p1", paths=tmp_foundry)
        result = resolve_notebook("run_x", mode="project", paths=tmp_foundry)
        assert result is not None
        assert result["notebook_id"] == "nb_fallback"


# ---------------------------------------------------------------------------
# resolve_notebook — run mode
# ---------------------------------------------------------------------------


class TestResolveNotebookRunMode:
    """run mode: each run_id gets its own dedicated notebook."""

    def test_creates_per_run_notebook(self, tmp_foundry: FoundryPaths):
        client = _fake_client(notebook_id="nb_run_aaa")
        r1 = resolve_notebook(
            "run_001",
            project="proj",
            mode="run",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert r1 is not None
        assert r1["notebook_id"] == "nb_run_aaa"
        assert r1["run_id"] == "run_001"

    def test_two_runs_get_two_notebooks(self, tmp_foundry: FoundryPaths):
        client = MagicMock()
        client.available.return_value = True
        client.create_notebook.side_effect = [
            {"notebook_id": "nb_run_1", "notebook_title": "RF-1"},
            {"notebook_id": "nb_run_2", "notebook_title": "RF-2"},
        ]

        r1 = resolve_notebook(
            "run_001", project="p", mode="run", create=True, client=client, paths=tmp_foundry
        )
        r2 = resolve_notebook(
            "run_002", project="p", mode="run", create=True, client=client, paths=tmp_foundry
        )
        assert r1["notebook_id"] == "nb_run_1"
        assert r2["notebook_id"] == "nb_run_2"
        assert client.create_notebook.call_count == 2

    def test_existing_run_not_recreated(self, tmp_foundry: FoundryPaths):
        record_run_notebook("run_001", "nb_existing", paths=tmp_foundry)
        client = _fake_client(notebook_id="nb_should_not_be_created")
        result = resolve_notebook(
            "run_001", mode="run", create=True, client=client, paths=tmp_foundry
        )
        assert result is not None
        assert result["notebook_id"] == "nb_existing"
        client.create_notebook.assert_not_called()


# ---------------------------------------------------------------------------
# resolve_notebook — explicit mode
# ---------------------------------------------------------------------------


class TestResolveNotebookExplicitMode:
    """explicit mode: project arg is treated as a raw notebook_id."""

    def test_returns_explicit_notebook_id(self, tmp_foundry: FoundryPaths):
        result = resolve_notebook(
            "run_001",
            project="nb_explicit_abc",
            mode="explicit",
            paths=tmp_foundry,
        )
        assert result is not None
        assert result["notebook_id"] == "nb_explicit_abc"
        assert result["mode"] == "explicit"

    def test_explicit_mode_no_project_returns_none(self, tmp_foundry: FoundryPaths):
        result = resolve_notebook("run_001", mode="explicit", paths=tmp_foundry)
        assert result is None

    def test_explicit_mode_no_network_calls(self, tmp_foundry: FoundryPaths):
        client = _fake_client(notebook_id="nb_should_not_be_called")
        result = resolve_notebook(
            "run_001",
            project="nb_explicit_xyz",
            mode="explicit",
            create=True,
            client=client,
            paths=tmp_foundry,
        )
        assert result is not None
        client.create_notebook.assert_not_called()


# ---------------------------------------------------------------------------
# record_run_notebook — idempotency
# ---------------------------------------------------------------------------


class TestRecordRunNotebook:
    """record_run_notebook is idempotent; repeated writes do not duplicate entries."""

    def test_records_run_without_project(self, tmp_foundry: FoundryPaths):
        record_run_notebook("run_001", "nb_abc", paths=tmp_foundry)
        assert notebook_for_run("run_001", paths=tmp_foundry) == "nb_abc"

    def test_records_run_with_project(self, tmp_foundry: FoundryPaths):
        record_run_notebook("run_001", "nb_abc", project="my-proj", paths=tmp_foundry)
        data = _read_registry(tmp_foundry)
        assert "my-proj" in data["projects"]
        assert "run_001" in data["projects"]["my-proj"]["runs"]
        assert data["runs"]["run_001"]["notebook_id"] == "nb_abc"

    def test_idempotent_repeated_calls(self, tmp_foundry: FoundryPaths):
        record_run_notebook("run_001", "nb_abc", project="proj", paths=tmp_foundry)
        record_run_notebook("run_001", "nb_abc", project="proj", paths=tmp_foundry)
        record_run_notebook("run_001", "nb_abc", project="proj", paths=tmp_foundry)

        data = _read_registry(tmp_foundry)
        # run appears exactly once in project runs list.
        assert data["projects"]["proj"]["runs"].count("run_001") == 1
        # Only one entry in the runs section.
        assert list(data["runs"].keys()).count("run_001") == 1

    def test_updates_notebook_id_on_re_record(self, tmp_foundry: FoundryPaths):
        record_run_notebook("run_001", "nb_v1", project="proj", paths=tmp_foundry)
        record_run_notebook("run_001", "nb_v2", project="proj", paths=tmp_foundry)
        assert notebook_for_run("run_001", paths=tmp_foundry) == "nb_v2"

    def test_persists_notebook_title(self, tmp_foundry: FoundryPaths):
        record_run_notebook(
            "run_001", "nb_abc", notebook_title="RF — my-proj", paths=tmp_foundry
        )
        data = _read_registry(tmp_foundry)
        assert data["runs"]["run_001"]["notebook_title"] == "RF — my-proj"


# ---------------------------------------------------------------------------
# notebook_for_run
# ---------------------------------------------------------------------------


class TestNotebookForRun:
    def test_returns_none_when_run_absent(self, tmp_foundry: FoundryPaths):
        result = notebook_for_run("run_nonexistent", paths=tmp_foundry)
        assert result is None

    def test_returns_notebook_id_after_record(self, tmp_foundry: FoundryPaths):
        record_run_notebook("run_001", "nb_for_run", paths=tmp_foundry)
        assert notebook_for_run("run_001", paths=tmp_foundry) == "nb_for_run"


# ---------------------------------------------------------------------------
# notebook_for_path
# ---------------------------------------------------------------------------


class TestNotebookForPath:
    def test_parses_run_id_from_path(self, tmp_foundry: FoundryPaths):
        record_run_notebook("rf_run_20260613_test", "nb_path_001", paths=tmp_foundry)
        result = notebook_for_path(
            "runs/rf_run_20260613_test/sources/src_001.md", paths=tmp_foundry
        )
        assert result == "nb_path_001"

    def test_returns_none_for_unknown_run(self, tmp_foundry: FoundryPaths):
        result = notebook_for_path(
            "runs/rf_run_unknown/sources/src.md", paths=tmp_foundry
        )
        assert result is None

    def test_returns_none_for_non_run_path(self, tmp_foundry: FoundryPaths):
        result = notebook_for_path("/some/other/path/file.yaml", paths=tmp_foundry)
        assert result is None

    def test_works_with_pathlib_path(self, tmp_foundry: FoundryPaths):
        record_run_notebook("rf_run_pathlib", "nb_pl", paths=tmp_foundry)
        result = notebook_for_path(
            Path("runs") / "rf_run_pathlib" / "telemetry" / "run_trace.jsonl",
            paths=tmp_foundry,
        )
        assert result == "nb_pl"


# ---------------------------------------------------------------------------
# _parse_run_id_from_path (private, but tested for precision)
# ---------------------------------------------------------------------------


class TestParseRunIdFromPath:
    def test_standard_runs_path(self):
        assert _parse_run_id_from_path("runs/rf_run_20260613_test/sources/s.md") == "rf_run_20260613_test"

    def test_absolute_path(self):
        assert _parse_run_id_from_path("/workspace/runs/rf_run_abc/evidence_bundle.yaml") == "rf_run_abc"

    def test_no_runs_segment_returns_none(self):
        assert _parse_run_id_from_path("/workspace/intents/active/intent.yaml") is None

    def test_runs_at_end_with_no_child_returns_none(self):
        # "runs" is the last component — no run_id follows.
        assert _parse_run_id_from_path("workspace/runs") is None


# ---------------------------------------------------------------------------
# Registry round-trip via yamlio
# ---------------------------------------------------------------------------


class TestRegistryRoundTrip:
    """Registry persists via yamlio with insertion-order preserved."""

    def test_empty_registry_written_and_loaded(self, tmp_foundry: FoundryPaths):
        data = {"projects": {}, "runs": {}}
        _write_registry(data, tmp_foundry)
        loaded = _read_registry(tmp_foundry)
        assert loaded["projects"] == {}
        assert loaded["runs"] == {}

    def test_registry_order_preserved(self, tmp_foundry: FoundryPaths):
        for i in range(5):
            record_run_notebook(f"run_00{i}", f"nb_{i}", paths=tmp_foundry)
        data = _read_registry(tmp_foundry)
        keys = list(data["runs"].keys())
        assert keys == [f"run_00{i}" for i in range(5)]

    def test_registry_dir_created_on_first_write(self, tmp_path: Path):
        """Registry directory is created atomically if absent."""
        root = tmp_path / "fresh"
        root.mkdir()
        (root / "foundry.yaml").write_text(
            "foundry:\n  owner: Test\n", encoding="utf-8"
        )
        (root / "registries").mkdir()
        paths = FoundryPaths(root=root)

        record_run_notebook("run_001", "nb_abc", paths=paths)
        reg_file = paths.registries / "notebooklm" / "notebooks.yaml"
        assert reg_file.exists()
        data = load_yaml(reg_file)
        assert data["runs"]["run_001"]["notebook_id"] == "nb_abc"

    def test_corrupt_registry_returns_empty_skeleton(self, tmp_foundry: FoundryPaths):
        reg = tmp_foundry.registries / "notebooklm" / "notebooks.yaml"
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text("!!python/object:object {}\n", encoding="utf-8")
        data = _read_registry(tmp_foundry)
        assert data == {"projects": {}, "runs": {}}
