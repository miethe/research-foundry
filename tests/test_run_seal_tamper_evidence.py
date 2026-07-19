"""TASK-4.4: tamper-evidence hardening + pre-seal-unaffected regression.

Extends the TASK-4.3 digest/lineage coverage (``test_run_seal_lineage.py``)
and the TASK-4.2 CLI-wiring coverage (``test_seal_cli_flag.py``) with:

  - per-file tamper detection: each digest-covered file (claim ledger, a
    source card, report_final.md) independently flips ``recompute_digest``
    when mutated, and flips back when restored -- no false positives, no
    false negatives, no cross-contamination between files.
  - a regression guarantee that runs which are *never* sealed are
    completely unaffected by the seal feature's existence: no required
    ``lineage.yaml``, no exceptions from ordinary metadata-reading code
    paths (``export_service.export_run`` / ``derive_status``).
  - a no-file-locking invariant: ``seal_run`` never chmods the run
    directory or any covered file -- POSIX permissions before and after
    sealing are identical, because sealing only reads evidence and writes
    a brand-new ``lineage.yaml``.
  - resilience: a consumer reading lineage state for a run that was never
    sealed treats the absence as "unsealed" (``None``), not an exception.
"""

from __future__ import annotations

from pathlib import Path

from research_foundry.paths import FoundryPaths
from research_foundry.services.export_service import derive_status, export_run
from research_foundry.services.run_seal import recompute_digest, seal_run
from research_foundry.yamlio import loads_yaml


def _make_paths(tmp_path: Path) -> FoundryPaths:
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    return FoundryPaths(root=root)


def _populate_evidence(paths: FoundryPaths, run_id: str) -> None:
    """Same fixture shape as ``test_run_seal_lineage.py`` for consistency."""

    run_paths = paths.run_paths(run_id)
    run_paths.ensure_scaffold()
    # resolve_run_paths() (used by export_run/derive_status consumers below)
    # requires run.yaml to exist to resolve the run by id.
    run_paths.run_yaml.write_text(
        f"run_id: {run_id}\nschema_version: 1\n", encoding="utf-8"
    )
    run_paths.claim_ledger.write_text(
        "claims:\n  - claim_id: clm_001\n    text: Example claim.\n",
        encoding="utf-8",
    )
    (run_paths.sources / "src_0001.md").write_text(
        "# Source Card\n\nsource_card_id: src_0001\n", encoding="utf-8"
    )
    run_paths.reports.mkdir(parents=True, exist_ok=True)
    run_paths.report_final.write_text("# Final Report\n\nBody.\n", encoding="utf-8")


def _lineage_state(paths: FoundryPaths, run_id: str) -> dict | None:
    """Mimic a consumer reading a run's seal/lineage state.

    Returns the most recent lineage entry, or ``None`` if the run has never
    been sealed -- absence of ``lineage.yaml`` (or an empty entries list) is
    treated as "unsealed", never as an error.
    """

    rp = paths.run_paths(run_id)
    if not rp.lineage.exists():
        return None
    record = loads_yaml(rp.lineage.read_text(encoding="utf-8"))
    entries = record.get("entries") if isinstance(record, dict) else None
    if not entries:
        return None
    return entries[-1]


class TestPerFileTamperEvidence:
    """Each digest-covered file independently flips the digest when mutated."""

    def test_recompute_matches_immediately_after_seal(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_tamper_baseline"
        _populate_evidence(paths, run_id)

        entry = seal_run(paths, run_id)

        # No false positive: nothing changed between seal and recompute.
        assert recompute_digest(paths, run_id) == entry["digest"]

    def test_claim_ledger_mutation_is_independently_detected(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_tamper_ledger"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)

        entry = seal_run(paths, run_id)
        baseline_digest = entry["digest"]
        original = run_paths.claim_ledger.read_text(encoding="utf-8")

        run_paths.claim_ledger.write_text(
            original + "  - claim_id: clm_002\n    text: Tampered addition.\n",
            encoding="utf-8",
        )
        assert recompute_digest(paths, run_id) != baseline_digest

        # Restore -> digest returns to baseline (mutation was the only diff).
        run_paths.claim_ledger.write_text(original, encoding="utf-8")
        assert recompute_digest(paths, run_id) == baseline_digest

    def test_source_card_mutation_is_independently_detected(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_tamper_source"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)
        card_path = run_paths.sources / "src_0001.md"

        entry = seal_run(paths, run_id)
        baseline_digest = entry["digest"]
        original = card_path.read_text(encoding="utf-8")

        card_path.write_text(original + "\nTampered evidence text.\n", encoding="utf-8")
        assert recompute_digest(paths, run_id) != baseline_digest

        card_path.write_text(original, encoding="utf-8")
        assert recompute_digest(paths, run_id) == baseline_digest

    def test_report_final_mutation_is_independently_detected(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_tamper_report"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)

        entry = seal_run(paths, run_id)
        baseline_digest = entry["digest"]
        original = run_paths.report_final.read_text(encoding="utf-8")

        run_paths.report_final.write_text(original + "\nTampered conclusion.\n", encoding="utf-8")
        assert recompute_digest(paths, run_id) != baseline_digest

        run_paths.report_final.write_text(original, encoding="utf-8")
        assert recompute_digest(paths, run_id) == baseline_digest

    def test_mutations_are_independent_not_cumulative_noise(self, tmp_path):
        """Sanity check: restoring one file after mutating it doesn't mask a
        still-outstanding mutation in another covered file."""

        paths = _make_paths(tmp_path)
        run_id = "rf_run_tamper_multi"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)
        card_path = run_paths.sources / "src_0001.md"

        entry = seal_run(paths, run_id)
        baseline_digest = entry["digest"]

        ledger_original = run_paths.claim_ledger.read_text(encoding="utf-8")
        card_original = card_path.read_text(encoding="utf-8")

        run_paths.claim_ledger.write_text(ledger_original + "tampered\n", encoding="utf-8")
        card_path.write_text(card_original + "tampered\n", encoding="utf-8")
        assert recompute_digest(paths, run_id) != baseline_digest

        # Restore only the ledger -- the source card is still mutated, so the
        # digest must still diverge from baseline (not silently pass).
        run_paths.claim_ledger.write_text(ledger_original, encoding="utf-8")
        assert recompute_digest(paths, run_id) != baseline_digest

        # Restore the card too -- now everything matches baseline again.
        card_path.write_text(card_original, encoding="utf-8")
        assert recompute_digest(paths, run_id) == baseline_digest


class TestUnsealedRunUnaffected:
    """Runs that are never sealed behave exactly as before the seal feature."""

    def test_lineage_path_does_not_exist_for_unsealed_run(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_never_sealed"
        _populate_evidence(paths, run_id)

        run_paths = paths.run_paths(run_id)
        # Resolving the path never raises, and no file is created as a
        # side effect of merely referencing it.
        assert isinstance(run_paths.lineage, Path)
        assert not run_paths.lineage.exists()

    def test_export_run_unaffected_by_absent_lineage(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_never_sealed_export"
        _populate_evidence(paths, run_id)

        # export_run (the rf run export / run.json metadata path) must
        # succeed exactly as it would have before the seal feature existed
        # -- no new required fields, no exceptions triggered by a missing
        # lineage.yaml.
        result = export_run(paths, run_id)

        assert result["run_id"] == run_id
        assert "lineage" not in result
        assert result["status_derived"] == "synthesized"

    def test_derive_status_unaffected_by_absent_lineage(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_never_sealed_status"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)

        # derive_status never references lineage/seal state at all; a
        # never-sealed run computes status identically to a sealed one.
        assert derive_status(run_paths, run_id=run_id) == "synthesized"

    def test_export_run_unaffected_even_after_sealing_elsewhere(self, tmp_path):
        """Sealing one run must not perturb metadata export for a sibling
        run in the same workspace that was never sealed."""

        paths = _make_paths(tmp_path)
        sealed_run_id = "rf_run_sibling_sealed"
        unsealed_run_id = "rf_run_sibling_unsealed"
        _populate_evidence(paths, sealed_run_id)
        _populate_evidence(paths, unsealed_run_id)

        seal_run(paths, sealed_run_id)

        result = export_run(paths, unsealed_run_id)
        assert result["run_id"] == unsealed_run_id
        assert not paths.run_paths(unsealed_run_id).lineage.exists()


class TestSealAppliesNoFileLocking:
    """Sealing reads evidence and writes lineage.yaml only -- no chmod."""

    def test_covered_file_permissions_unchanged_after_seal(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_seal_permissions"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)
        card_path = run_paths.sources / "src_0001.md"

        watched_paths = [
            run_paths.run,
            run_paths.claim_ledger,
            card_path,
            run_paths.report_final,
        ]
        before_modes = {p: p.stat().st_mode for p in watched_paths}

        seal_run(paths, run_id)

        after_modes = {p: p.stat().st_mode for p in watched_paths}
        assert after_modes == before_modes

    def test_sealing_twice_still_leaves_permissions_unchanged(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_seal_permissions_twice"
        _populate_evidence(paths, run_id)
        run_paths = paths.run_paths(run_id)

        before_mode = run_paths.claim_ledger.stat().st_mode
        seal_run(paths, run_id)
        seal_run(paths, run_id)
        after_mode = run_paths.claim_ledger.stat().st_mode

        assert after_mode == before_mode


class TestLineageStateResilience:
    """A consumer reading seal/lineage state treats absence as unsealed."""

    def test_missing_lineage_reports_unsealed_without_raising(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_lineage_missing"
        _populate_evidence(paths, run_id)

        # Must not raise despite lineage.yaml never having been written.
        state = _lineage_state(paths, run_id)
        assert state is None

    def test_sealed_lineage_reports_the_latest_entry(self, tmp_path):
        paths = _make_paths(tmp_path)
        run_id = "rf_run_lineage_present"
        _populate_evidence(paths, run_id)

        entry = seal_run(paths, run_id)

        state = _lineage_state(paths, run_id)
        assert state is not None
        assert state["digest"] == entry["digest"]
