"""Integration tests for ERI Phase 5 — Resumable Importer and CLI
(ERI-5.1 deterministic action orchestration, ERI-5.2 chunking and
cancellation, ERI-5.4 provenance/export seam).

``external_research_import.import_external_report`` is the orchestration
seam under test; it wires ``ExternalResearchInterchange.stage()`` (Phase 2)
together with ``ExternalResearchResolver`` (Phase 4) without introducing a
second identity/receipt authority of its own (contract §3.5). ERI-5.3 (the
CLI itself) is unit-tested separately in
``tests/unit/test_external_research_cli.py``.

No real network access anywhere in this module — every scenario injects a
fake ``acquire`` callable, matching
``tests/integration/test_external_research_resolution.py``'s own convention.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.external_research_import import (
    DEFAULT_ACQUISITION_POLICY,
    PendingImportError,
    import_external_report,
)
from research_foundry.services.external_research_interchange import ExternalResearchInterchange
from research_foundry.services.source_acquisition_policy import AcquisitionOutcome
from research_foundry.yamlio import dump_yaml
from tests.unit.test_external_research_interchange import build_packet

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _paths(tmp_path: Path, name: str = "workspace") -> FoundryPaths:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "foundry.yaml").write_text("workspace: true\n", encoding="utf-8")
    return FoundryPaths(root=root)


def _make_run(paths: FoundryPaths, run_id: str) -> None:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml({"run_id": run_id, "status": "planned"}, rp.run_yaml)


def _fake_acquire(content_by_locator: dict[str, bytes], *, interrupt_locator: str | None = None) -> Any:
    calls: list[str] = []

    def acquire(locator: str, *, policy: Any, **_kwargs: Any) -> AcquisitionOutcome:
        calls.append(locator)
        if interrupt_locator is not None and locator == interrupt_locator:
            raise KeyboardInterrupt("simulated operator cancellation mid-acquisition")
        content = content_by_locator.get(locator)
        if content is None:
            return AcquisitionOutcome(ok=False, denial_code="source_unavailable")
        return AcquisitionOutcome(ok=True, content=content, status_code=200, content_type="text/plain", final_locator=locator)

    acquire.calls = calls  # type: ignore[attr-defined]
    return acquire


def _sources_and_candidates(n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, bytes]]:
    """``n`` independent source+candidate pairs -> 2n canonical actions."""

    sources = [
        {
            "source_id": f"src_{i:03d}",
            "title": f"Source {i}",
            "locator": {"doi": None, "url": f"https://example.test/article-{i}"},
            "publication_year": 2024,
            "access_status": "open-access",
        }
        for i in range(n)
    ]
    candidates = [
        {
            "candidate_id": f"cand_{i:03d}",
            "statement": f"Statement number {i}.",
            "classification": "assertion",
            "source_refs": [f"src_{i:03d}"],
            "relation": "supports",
            "quote": f"the distinguishing exact phrase number {i}",
        }
        for i in range(n)
    ]
    content_by_locator = {
        f"https://example.test/article-{i}": f"prefix text the distinguishing exact phrase number {i} suffix text".encode()
        for i in range(n)
    }
    return sources, candidates, content_by_locator


def _receipt_without_created_at(receipt: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in receipt.items() if k != "created_at"}


# ---------------------------------------------------------------------------
# ERI-5.1: deterministic orchestration / no-target-run staging-only
# ---------------------------------------------------------------------------


def test_staging_only_fresh_import_completes_in_one_call(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    root = build_packet(tmp_path / "packet")

    outcome = import_external_report(
        root,
        workspace_id="ws_demo",
        target_run_id=None,
        paths=paths,
        acquire=_fake_acquire({}),
    )

    assert outcome.complete is True
    assert outcome.dry_run is False
    assert outcome.replayed is False
    assert outcome.status in ("completed", "completed_with_quarantine")
    assert outcome.receipt is not None
    assert outcome.receipt["target_run_id"] is None


def test_no_target_run_means_no_run_creation_or_projection(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    root = build_packet(tmp_path / "packet")

    import_external_report(
        root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire({})
    )

    assert not paths.runs.exists() or not any(paths.runs.iterdir())


def test_blocked_packet_returns_complete_with_blocked_status(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    root = build_packet(tmp_path / "packet", omit_member_role="report")

    outcome = import_external_report(
        root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire({})
    )

    assert outcome.complete is True
    assert outcome.status == "blocked"
    assert outcome.block_reason is not None
    assert outcome.cursor is None
    assert outcome.receipt is not None
    assert outcome.receipt["actions"] == []


def test_default_acquisition_policy_is_schema_valid(tmp_path: Path) -> None:
    from research_foundry.schemas import validate as schema_validate

    validation = schema_validate(DEFAULT_ACQUISITION_POLICY, "external_research_acquisition_policy")
    assert validation.ok, validation.errors


# ---------------------------------------------------------------------------
# ERI-5.2: chunking (--limit) and resume convergence
# ---------------------------------------------------------------------------


class TestBatchingAndResume:
    def test_batch_limit_reached_leaves_pending_and_reports_cursor(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        sources, candidates, content = _sources_and_candidates(3)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        first = import_external_report(
            root,
            workspace_id="ws_demo",
            target_run_id=None,
            paths=paths,
            acquire=_fake_acquire(content),
            limit=2,
        )

        assert first.complete is False
        assert first.status == "pending"
        assert first.receipt is None
        assert first.cursor is not None
        assert first.cursor["completed_count"] == 2
        assert first.cursor["total_count"] == 6  # 3 sources + 3 candidates

    def test_pending_without_resume_raises(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        sources, candidates, content = _sources_and_candidates(3)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire(content), limit=2
        )

        with pytest.raises(PendingImportError):
            import_external_report(
                root,
                workspace_id="ws_demo",
                target_run_id=None,
                paths=paths,
                acquire=_fake_acquire(content),
                limit=2,
                resume=False,
            )

    def test_dry_run_bypasses_resume_guard_and_never_mutates(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        sources, candidates, content = _sources_and_candidates(3)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        first = import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire(content), limit=2
        )
        assert first.complete is False
        interchange = ExternalResearchInterchange(workspace_id="ws_demo", paths=paths)
        checkpoint_before = interchange._load_checkpoint(first.receipt_digest)
        assert checkpoint_before is not None

        dry = import_external_report(
            root,
            workspace_id="ws_demo",
            target_run_id=None,
            paths=paths,
            acquire=_fake_acquire(content),
            dry_run=True,
            resume=False,
        )
        assert dry.dry_run is True
        assert dry.complete is True  # dry_run always resolves everything in one pass

        # The pending checkpoint from the earlier real (non-dry) call is untouched.
        checkpoint_after = interchange._load_checkpoint(first.receipt_digest)
        assert checkpoint_after == checkpoint_before

    def test_interrupted_and_uninterrupted_runs_converge_to_identical_receipt(self, tmp_path: Path) -> None:
        """AC ERI-5 / Phase 5 quality gate: interrupted (batched + resumed)
        and uninterrupted (single unbatched call) runs over the SAME packet
        converge to the same receipt content and identical canonical
        effects. Compared across two independent storage roots (same
        `workspace_id`/policy/packet, so the SAME `receipt_digest` is
        expected) -- `created_at` is the one field excluded from the
        comparison since it is deliberately NOT a `receipt_digest` input
        (contract §1.3) and is expected to differ between two independently
        time-stamped completions.
        """

        sources, candidates, content = _sources_and_candidates(3)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        # Interrupted: three separate calls, batch size 2, requiring resume.
        interrupted_paths = _paths(tmp_path, "interrupted")
        first = import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=interrupted_paths,
            acquire=_fake_acquire(content), limit=2,
        )
        assert first.complete is False
        second = import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=interrupted_paths,
            acquire=_fake_acquire(content), limit=2, resume=True,
        )
        assert second.complete is False
        third = import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=interrupted_paths,
            acquire=_fake_acquire(content), limit=2, resume=True,
        )
        assert third.complete is True
        assert third.receipt is not None

        # Uninterrupted: one unbatched call, fresh storage root.
        uninterrupted_paths = _paths(tmp_path, "uninterrupted")
        straight = import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=uninterrupted_paths,
            acquire=_fake_acquire(content), limit=None,
        )
        assert straight.complete is True
        assert straight.receipt is not None

        assert third.receipt_digest == straight.receipt_digest
        assert _receipt_without_created_at(third.receipt) == _receipt_without_created_at(straight.receipt)
        # "identical canonical effects": every action's own effect_digest
        # (which now folds in `canonical_refs` -- Phase 5's fix to the
        # Phase-4-flagged gap) matches between the two independently-built
        # runs, not merely the receipt's own top-level identity fields.
        third_effects = {a["action_id"]: a["effect_digest"] for a in third.receipt["actions"]}
        straight_effects = {a["action_id"]: a["effect_digest"] for a in straight.receipt["actions"]}
        assert third_effects == straight_effects

    def test_unlimited_limit_processes_everything_in_one_call(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        sources, candidates, content = _sources_and_candidates(5)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        outcome = import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire(content), limit=None
        )

        assert outcome.complete is True
        assert outcome.receipt["counts"]["actions_total"] == 10


# ---------------------------------------------------------------------------
# ERI-5.2: cancellation (genuine interruption, not a deliberate batch limit)
# ---------------------------------------------------------------------------


class TestCancellation:
    def test_keyboard_interrupt_preserves_pending_checkpoint_and_resume_completes(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        sources, candidates, content = _sources_and_candidates(3)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)
        interrupt_locator = "https://example.test/article-1"

        with pytest.raises(KeyboardInterrupt):
            import_external_report(
                root,
                workspace_id="ws_demo",
                target_run_id=None,
                paths=paths,
                acquire=_fake_acquire(content, interrupt_locator=interrupt_locator),
                limit=None,  # unbounded -- only the injected interrupt stops this call
            )

        interchange = ExternalResearchInterchange(workspace_id="ws_demo", paths=paths)
        # Compute the same identity a resume call would, to inspect state.
        pending_outcome_probe = import_external_report(
            root,
            workspace_id="ws_demo",
            target_run_id=None,
            paths=paths,
            acquire=_fake_acquire(content, interrupt_locator=interrupt_locator),
            dry_run=True,  # bypasses the resume guard; never mutates
        )
        assert pending_outcome_probe.dry_run is True

        # A real (non-dry) call without --resume must refuse to silently continue.
        with pytest.raises(PendingImportError):
            import_external_report(
                root,
                workspace_id="ws_demo",
                target_run_id=None,
                paths=paths,
                acquire=_fake_acquire(content),  # no interrupt this time
                resume=False,
            )

        resumed = import_external_report(
            root,
            workspace_id="ws_demo",
            target_run_id=None,
            paths=paths,
            acquire=_fake_acquire(content),  # no interrupt this time
            resume=True,
        )
        assert resumed.complete is True
        assert resumed.receipt["counts"]["actions_total"] == 6
        # No duplicate effects were written for the actions already
        # completed before the interrupt.
        effects_dir = interchange._receipt_dir(resumed.receipt_digest) / "effects"
        assert len(list(effects_dir.iterdir())) == 6


# ---------------------------------------------------------------------------
# ERI-5.4: provenance/export seam
# ---------------------------------------------------------------------------


class TestProvenanceExportSeam:
    def test_target_run_records_safe_provenance_event(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        run_id = "rf_run_eri_test001"
        _make_run(paths, run_id)
        sources, candidates, content = _sources_and_candidates(1)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        outcome = import_external_report(
            root,
            workspace_id="ws_demo",
            target_run_id=run_id,
            paths=paths,
            acquire=_fake_acquire(content),
            provenance_origin="search_run:sr_example",
        )
        assert outcome.complete is True

        rp = paths.run_paths(run_id)
        assert rp.run_trace.exists()
        events = [
            __import__("json").loads(line)
            for line in rp.run_trace.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        matches = [e for e in events if e.get("stage") == "external_report_import"]
        assert len(matches) == 1
        event = matches[0]
        assert event["run_id"] == run_id
        assert event["receipt_digest"] == outcome.receipt_digest
        assert event["packet_digest"] == outcome.packet_digest
        assert event["status"] == outcome.status
        assert event["provenance_origin"] == "search_run:sr_example"
        assert event["actions_total"] == outcome.counts["actions_total"]
        # Never packet-derived free text or private absolute paths.
        assert "Report" not in __import__("json").dumps(event)
        assert str(root) not in __import__("json").dumps(event)

    def test_dry_run_never_records_provenance_event(self, tmp_path: Path) -> None:
        paths = _paths(tmp_path)
        run_id = "rf_run_eri_test002"
        _make_run(paths, run_id)
        sources, candidates, content = _sources_and_candidates(1)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        import_external_report(
            root, workspace_id="ws_demo", target_run_id=run_id, paths=paths, acquire=_fake_acquire(content),
            dry_run=True,
        )

        rp = paths.run_paths(run_id)
        assert not rp.run_trace.exists()

    def test_staging_only_seam_is_not_invoked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`target_run_id=None` must never even attempt the export-seam call."""

        paths = _paths(tmp_path)
        sources, candidates, content = _sources_and_candidates(1)
        root = build_packet(tmp_path / "packet", sources=sources, candidates=candidates)

        called = {"n": 0}

        def _boom(*args: Any, **kwargs: Any) -> None:
            called["n"] += 1
            raise AssertionError("must not be called for a staging-only import")

        monkeypatch.setattr(
            "research_foundry.services.export_service.record_external_report_import_activity", _boom
        )

        import_external_report(
            root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire(content)
        )

        assert called["n"] == 0


# ---------------------------------------------------------------------------
# ImportOutcome.safe_dict() — machine-safe payload shape
# ---------------------------------------------------------------------------


def test_safe_dict_excludes_full_receipt_and_checkpoint(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    root = build_packet(tmp_path / "packet")

    outcome = import_external_report(
        root, workspace_id="ws_demo", target_run_id=None, paths=paths, acquire=_fake_acquire({})
    )
    payload = outcome.safe_dict()

    assert set(payload.keys()) == {
        "workspace_id",
        "target_run_id",
        "packet_digest",
        "receipt_id",
        "receipt_digest",
        "status",
        "complete",
        "replayed",
        "dry_run",
        "block_reason",
        "counts",
        "cursor",
    }
    assert "receipt" not in payload
    assert "checkpoint" not in payload
