"""ERI-6.3 — Large-report resume and limits.

`tests/integration/test_external_research_import.py::TestBatchingAndResume`
already proves batching/resume convergence at small scale (3 sources).
This module scales that same convergence property to a genuinely large
packet (60 sources / 60 candidates = 120 canonical actions), exercises
batch-limit BOUNDARY conditions (limit evenly dividing the action count,
limit leaving a remainder, limit exceeding the action count), and adds two
FAULT tests proving a corrupted on-disk artifact fails closed at scale
rather than silently completing.

Elapsed-time and peak-memory numbers are captured and printed (run with
`-s` to see them) purely as INDICATIVE evidence for the phase-6 completion
report -- they are measurements of this test machine running fake,
in-process acquisition with zero real I/O, and make NO production
performance claim of any kind.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path
from typing import Any

import pytest

from research_foundry.services.external_research_import import (
    import_external_report,
)
from research_foundry.services.external_research_interchange import (
    ExternalResearchInterchange,
    StagingIntegrityError,
)
from research_foundry.yamlio import dumps_yaml
from tests.unit.test_external_research_interchange import build_packet

from .test_external_research_import import _fake_acquire, _paths

pytestmark = pytest.mark.integration

_LARGE_N = 60  # 60 sources + 60 candidates = 120 canonical actions


def _large_packet(tmp_path: Path, n: int = _LARGE_N):
    sources = [
        {
            "source_id": f"src_{i:04d}",
            "title": f"Source {i}",
            "locator": {"doi": None, "url": f"https://example.test/article-{i}"},
            "publication_year": 2024,
            "access_status": "open-access",
        }
        for i in range(n)
    ]
    candidates = [
        {
            "candidate_id": f"cand_{i:04d}",
            "statement": f"Statement number {i}.",
            "classification": "assertion",
            "source_refs": [f"src_{i:04d}"],
            "quote": f"exact evidence text number {i}",
        }
        for i in range(n)
    ]
    content = {
        f"https://example.test/article-{i}": f"exact evidence text number {i}.".encode()
        for i in range(n)
    }
    root = build_packet(tmp_path / "large-packet", sources=sources, candidates=candidates)
    return root, sources, candidates, content


def _receipt_without_created_at(receipt: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in receipt.items() if k != "created_at"}


# ---------------------------------------------------------------------------
# Convergence at scale, with indicative elapsed/memory evidence
# ---------------------------------------------------------------------------


def test_large_packet_batched_resume_converges_with_uninterrupted_run(tmp_path: Path) -> None:
    root, _sources, _candidates, content = _large_packet(tmp_path)
    total_actions = 2 * _LARGE_N

    tracemalloc.start()
    t0 = time.perf_counter()

    # Batched: limit=10 -> 12 calls needed for 120 actions.
    batched_paths = _paths(tmp_path, "batched")
    calls = 0
    outcome = import_external_report(
        root, workspace_id="ws_large", target_run_id=None, paths=batched_paths,
        acquire=_fake_acquire(content), limit=10,
    )
    calls += 1
    while not outcome.complete:
        outcome = import_external_report(
            root, workspace_id="ws_large", target_run_id=None, paths=batched_paths,
            acquire=_fake_acquire(content), limit=10, resume=True,
        )
        calls += 1
    assert outcome.receipt["counts"]["actions_total"] == total_actions
    # 120 actions / 10 per call = exactly 12 calls.
    assert calls == 12

    batched_elapsed = time.perf_counter() - t0
    _current, batched_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Uninterrupted: one unbatched call, fresh storage root.
    tracemalloc.start()
    t1 = time.perf_counter()
    uninterrupted_paths = _paths(tmp_path, "unbatched")
    straight = import_external_report(
        root, workspace_id="ws_large", target_run_id=None, paths=uninterrupted_paths,
        acquire=_fake_acquire(content), limit=None,
    )
    unbatched_elapsed = time.perf_counter() - t1
    _current2, unbatched_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert straight.complete is True
    assert outcome.receipt_digest == straight.receipt_digest
    assert _receipt_without_created_at(outcome.receipt) == _receipt_without_created_at(straight.receipt)
    batched_effects = {a["action_id"]: a["effect_digest"] for a in outcome.receipt["actions"]}
    straight_effects = {a["action_id"]: a["effect_digest"] for a in straight.receipt["actions"]}
    assert batched_effects == straight_effects

    # INDICATIVE ONLY -- this test machine, fake in-process acquisition, zero
    # real network I/O. Not a production performance claim.
    print(
        f"\n[ERI-6.3 indicative evidence] {total_actions} actions "
        f"({_LARGE_N} sources + {_LARGE_N} candidates):\n"
        f"  batched (12 calls, limit=10): {batched_elapsed:.4f}s wall, "
        f"{batched_peak / 1024:.1f} KiB peak traced Python memory\n"
        f"  unbatched (1 call, limit=None): {unbatched_elapsed:.4f}s wall, "
        f"{unbatched_peak / 1024:.1f} KiB peak traced Python memory"
    )


# ---------------------------------------------------------------------------
# Batch-boundary conditions
# ---------------------------------------------------------------------------


def test_batch_limit_leaves_a_remainder_still_converges(tmp_path: Path) -> None:
    """120 actions, limit=13 (does not evenly divide) -> 10 batches (9 full
    + 1 remainder of 3), still resumes to completion and converges with an
    unbatched run."""

    root, _s, _c, content = _large_packet(tmp_path)
    paths = _paths(tmp_path, "remainder")

    outcome = import_external_report(
        root, workspace_id="ws_remainder", target_run_id=None, paths=paths,
        acquire=_fake_acquire(content), limit=13,
    )
    calls = 1
    while not outcome.complete:
        outcome = import_external_report(
            root, workspace_id="ws_remainder", target_run_id=None, paths=paths,
            acquire=_fake_acquire(content), limit=13, resume=True,
        )
        calls += 1

    assert outcome.receipt["counts"]["actions_total"] == 2 * _LARGE_N
    # ceil(120 / 13) = 10 calls.
    assert calls == 10


def test_batch_limit_exceeding_total_actions_completes_in_one_call(tmp_path: Path) -> None:
    root, _s, _c, content = _large_packet(tmp_path, n=5)  # 10 actions
    paths = _paths(tmp_path, "over-limit")

    outcome = import_external_report(
        root, workspace_id="ws_over", target_run_id=None, paths=paths,
        acquire=_fake_acquire(content), limit=10_000,
    )
    assert outcome.complete is True
    assert outcome.receipt["counts"]["actions_total"] == 10


def test_batch_limit_of_one_processes_action_at_a_time(tmp_path: Path) -> None:
    """The tightest legal boundary: limit=1 forces exactly N calls for N
    actions -- proves the batching mechanism has no off-by-one that
    silently processes zero or two actions per call at the extreme."""

    root, _s, _c, content = _large_packet(tmp_path, n=4)  # 8 actions
    paths = _paths(tmp_path, "one-at-a-time")

    outcome = import_external_report(
        root, workspace_id="ws_one", target_run_id=None, paths=paths,
        acquire=_fake_acquire(content), limit=1,
    )
    calls = 1
    while not outcome.complete:
        outcome = import_external_report(
            root, workspace_id="ws_one", target_run_id=None, paths=paths,
            acquire=_fake_acquire(content), limit=1, resume=True,
        )
        calls += 1
    assert calls == 8
    assert outcome.receipt["counts"]["actions_total"] == 8


# ---------------------------------------------------------------------------
# Fault tests — corrupted on-disk artifacts fail closed at scale
# ---------------------------------------------------------------------------


def test_corrupted_effect_record_fails_closed_on_resume(tmp_path: Path) -> None:
    root, _s, _c, content = _large_packet(tmp_path, n=10)  # 20 actions
    paths = _paths(tmp_path, "corrupted-effect")

    outcome = import_external_report(
        root, workspace_id="ws_corrupt", target_run_id=None, paths=paths,
        acquire=_fake_acquire(content), limit=5,
    )
    assert outcome.complete is False

    interchange = ExternalResearchInterchange(workspace_id="ws_corrupt", paths=paths)
    receipt_digest = outcome.receipt_digest
    receipt_dir = interchange._receipt_dir(receipt_digest)
    effects_dir = receipt_dir / "effects"
    effect_files = sorted(effects_dir.glob("*.yaml"))
    assert effect_files, "expected at least one published effect file after a partial batch"

    # Corrupt one already-published effect record: replace it with a
    # non-mapping YAML document (a bare scalar).
    corrupted = effect_files[0]
    corrupted.write_text(dumps_yaml("not-a-mapping"), encoding="utf-8")

    with pytest.raises(StagingIntegrityError):
        import_external_report(
            root, workspace_id="ws_corrupt", target_run_id=None, paths=paths,
            acquire=_fake_acquire(content), limit=5, resume=True,
        )


def test_checkpoint_context_mismatch_fails_closed_at_scale(tmp_path: Path) -> None:
    """A checkpoint whose bound `target_run_id` no longer matches the
    presented staging context (contract §1.4/§3.5's staging-context binding)
    fails closed rather than silently resuming under the wrong context."""

    root, _s, _c, content = _large_packet(tmp_path, n=10)
    paths = _paths(tmp_path, "checkpoint-mismatch")

    outcome = import_external_report(
        root, workspace_id="ws_ctx", target_run_id=None, paths=paths,
        acquire=_fake_acquire(content), limit=5,
    )
    assert outcome.complete is False

    interchange = ExternalResearchInterchange(workspace_id="ws_ctx", paths=paths)
    checkpoint_path = interchange._checkpoint_path(outcome.receipt_digest)
    assert checkpoint_path.exists()

    from research_foundry.yamlio import loads_yaml

    checkpoint = dict(loads_yaml(checkpoint_path.read_text(encoding="utf-8")))
    checkpoint["target_run_id"] = "run_someone_elses_context"
    checkpoint_path.write_text(dumps_yaml(checkpoint), encoding="utf-8")

    with pytest.raises(StagingIntegrityError):
        import_external_report(
            root, workspace_id="ws_ctx", target_run_id=None, paths=paths,
            acquire=_fake_acquire(content), limit=5, resume=True,
        )
