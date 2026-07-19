"""TASK-4.3: content digest + append-only lineage record for ``seal_run``.

Covers the real digest/lineage-write logic (as opposed to
``test_seal_cli_flag.py``, which only covers the CLI trigger surface with
``seal_run`` mocked out):

  - sealing a run produces a lineage.yaml with a real (non-None) digest
  - sealing twice appends a second entry rather than overwriting the first
    (append-only)
  - ``recompute_digest`` on an unmutated run matches the stored digest
  - a run with no claims/sources/report still seals without crashing
    (empty-evidence edge case)
"""

from __future__ import annotations

from pathlib import Path

from research_foundry.paths import FoundryPaths
from research_foundry.services.run_seal import recompute_digest, seal_run
from research_foundry.yamlio import loads_yaml


def _make_paths(tmp_path: Path) -> FoundryPaths:
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    return FoundryPaths(root=root)


def _populate_evidence(paths: FoundryPaths, run_id: str) -> None:
    run_paths = paths.run_paths(run_id)
    run_paths.ensure_scaffold()
    run_paths.claim_ledger.write_text(
        "claims:\n  - claim_id: clm_001\n    text: Example claim.\n",
        encoding="utf-8",
    )
    (run_paths.sources / "src_0001.md").write_text(
        "# Source Card\n\nsource_card_id: src_0001\n", encoding="utf-8"
    )
    run_paths.reports.mkdir(parents=True, exist_ok=True)
    run_paths.report_final.write_text("# Final Report\n\nBody.\n", encoding="utf-8")


class TestSealRunLineage:
    def test_seal_produces_real_digest(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_digest_test"
        _populate_evidence(paths, run_id)

        entry = seal_run(paths, run_id)

        assert entry["run_id"] == run_id
        assert entry["digest"] is not None
        assert isinstance(entry["digest"], str) and len(entry["digest"]) == 64  # sha256 hex
        assert entry["digest_algorithm"] == "sha256"
        assert "sealed_at" in entry

        lineage_path = paths.run_paths(run_id).lineage
        assert lineage_path.exists()
        record = loads_yaml(lineage_path.read_text(encoding="utf-8"))
        assert record["run_id"] == run_id
        assert len(record["entries"]) == 1
        assert record["entries"][0]["digest"] == entry["digest"]

    def test_seal_twice_appends_rather_than_overwrites(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_append_test"
        _populate_evidence(paths, run_id)

        first_entry = seal_run(paths, run_id)
        second_entry = seal_run(paths, run_id)

        lineage_path = paths.run_paths(run_id).lineage
        record = loads_yaml(lineage_path.read_text(encoding="utf-8"))
        entries = record["entries"]

        assert len(entries) == 2
        assert entries[0] == first_entry
        assert entries[1] == second_entry
        # unmutated evidence between seals -> identical digest, distinct timestamps allowed
        assert entries[0]["digest"] == entries[1]["digest"]

    def test_recompute_digest_matches_unmutated_run(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_recompute_test"
        _populate_evidence(paths, run_id)

        entry = seal_run(paths, run_id)
        recomputed = recompute_digest(paths, run_id)

        assert recomputed == entry["digest"]

    def test_recompute_digest_diverges_after_mutation(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_mutation_test"
        _populate_evidence(paths, run_id)

        entry = seal_run(paths, run_id)

        run_paths = paths.run_paths(run_id)
        run_paths.claim_ledger.write_text(
            "claims:\n  - claim_id: clm_001\n    text: Mutated claim.\n",
            encoding="utf-8",
        )

        assert recompute_digest(paths, run_id) != entry["digest"]

    def test_seal_empty_evidence_does_not_crash(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_empty_test"
        # No claims/sources/report populated -- only ensure_scaffold runs inside seal_run.

        entry = seal_run(paths, run_id)

        assert entry["digest"] is not None
        assert entry["manifest"] == []
        assert recompute_digest(paths, run_id) == entry["digest"]
