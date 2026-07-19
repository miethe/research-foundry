"""Tests for ``research_foundry.services.writeback.approve_and_dispatch`` (ORC-001..005).

Covers the Phase 1 Quality Gates for the runs-writeback approve & dispatch
feature:

1. Call-order: the combined governance gate (``guard_check``) must run before
   any of the three per-target dispatch primitives are attempted.
2. A blocked gate writes zero files under ``writebacks/`` and every requested
   target is recorded ``"skipped"``.
3. Per-target isolation: one target raising does not prevent the other two
   from being attempted.
4. ``approved_by``/``approval_timestamp`` are populated in
   ``evidence_bundle.yaml`` on a successful invocation and left ``None`` on a
   blocked one.
5. ``overall_status`` aggregation: success only when every requested target
   succeeds; a blocked gate is always ``"blocked"``; any post-gate failure
   (partial or total) is ``"partial"``, never ``"blocked"``.

Follows the ``tmp_foundry`` fixture convention from ``tests/test_writebacks.py``
(a real, schema-backed run built via the deterministic pipeline) and mocks only
what is necessary to force a specific branch (guard failure, a target
exception, or a call-order assertion).
"""

from __future__ import annotations

from unittest.mock import patch

from research_foundry.paths import FoundryPaths
from research_foundry.services import writeback
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.governance import GuardResult, Violation
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


def _build_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    """Drive the deterministic pipeline and return the run_id (mirrors
    ``tests/test_writebacks.py::_build_run``)."""

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
        title="Evidence bundles and claim traceability",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


# --------------------------------------------------------------------------- #
# 1. Call order: guard_check before any target dispatch primitive.
# --------------------------------------------------------------------------- #
def test_guard_check_runs_before_any_target_dispatch(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)

    call_order: list[str] = []

    def _fake_build_bundle(run_id_arg, *, verify=True, paths=None):
        call_order.append("build_bundle")
        return writeback.BundleResult(
            run_id=run_id_arg,
            bundle_id="bundle_test_001",
            bundle_path=paths.run_paths(run_id_arg).evidence_bundle,
            counts={},
            verified=True,
        )

    def _fake_council_review(run_id_arg, *, roles, vote="approve-concern-block", paths=None):
        call_order.append("council_review")
        return paths.run_paths(run_id_arg).council_review

    def _fake_guard_check(ctx, *, paths=None):
        call_order.append("guard_check")
        return GuardResult(passed=True, exit_code=0, violations=[])

    def _fake_emit_ccdash(run_id_arg, *, paths=None):
        call_order.append("emit_ccdash_event")
        # A real (but non-existent) Path: _safe_load degrades cleanly on
        # FileNotFoundError so the dispatch is recorded as a real attempt,
        # not an accidental "failed" from a Mock leaking into load_yaml.
        return paths.root / "does_not_exist_ccdash_event.yaml"

    def _fake_render_meatywiki(rp, paths_arg, *, bundle_ident, sensitivity, ledger, requires_review):
        call_order.append("_render_meatywiki")
        return rp.meatywiki_writeback

    def _fake_render_skillbom(
        rp, paths_arg, *, bundle_ident, ccdash_event_id_value, requires_review, ledger=None
    ):
        call_order.append("_render_skillbom")
        return rp.skillbom_candidate

    with (
        patch.object(writeback, "build_bundle", side_effect=_fake_build_bundle),
        patch.object(writeback, "council_review", side_effect=_fake_council_review),
        patch.object(writeback.governance, "guard_check", side_effect=_fake_guard_check),
        patch.object(writeback.telemetry, "emit_ccdash_event", side_effect=_fake_emit_ccdash),
        patch.object(writeback, "_render_meatywiki", side_effect=_fake_render_meatywiki),
        patch.object(writeback, "_render_skillbom", side_effect=_fake_render_skillbom),
    ):
        result = writeback.approve_and_dispatch(run_id, paths=paths)

    assert "guard_check" in call_order
    guard_idx = call_order.index("guard_check")
    for dispatch_marker in ("emit_ccdash_event", "_render_meatywiki", "_render_skillbom"):
        assert dispatch_marker in call_order
        assert guard_idx < call_order.index(dispatch_marker), (
            f"guard_check (idx={guard_idx}) must precede {dispatch_marker} "
            f"(idx={call_order.index(dispatch_marker)}); order was {call_order}"
        )

    assert result.overall_status == "success"
    assert result.target_status == {
        "ccdash": "success",
        "meatywiki": "success",
        "skillmeat": "success",
    }


# --------------------------------------------------------------------------- #
# 2. Blocked path: zero files under writebacks/, every target skipped.
# --------------------------------------------------------------------------- #
def test_blocked_gate_writes_zero_files_and_skips_all_targets(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)

    writebacks_dir = rp.writebacks
    before = set(writebacks_dir.rglob("*")) if writebacks_dir.exists() else set()

    failing_guard = GuardResult(
        passed=False,
        exit_code=3,
        violations=[
            Violation(
                rule_id="test_forced_block",
                severity="block",
                message="Forced block for test.",
            )
        ],
    )

    with patch.object(writeback.governance, "guard_check", return_value=failing_guard):
        result = writeback.approve_and_dispatch(run_id, paths=paths)

    assert result.overall_status == "blocked"
    assert result.guard_result.passed is False
    assert result.target_status == {
        "ccdash": "skipped",
        "meatywiki": "skipped",
        "skillmeat": "skipped",
    }

    after = set(writebacks_dir.rglob("*")) if writebacks_dir.exists() else set()
    assert after == before, f"expected zero new files under writebacks/, found {after - before}"


# --------------------------------------------------------------------------- #
# 3. Per-target isolation: one target's exception does not stop the others.
# --------------------------------------------------------------------------- #
def test_per_target_isolation_one_failure_does_not_block_others(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)

    def _raise(*args, **kwargs):
        raise RuntimeError("forced meatywiki failure for test")

    with patch.object(writeback, "_render_meatywiki", side_effect=_raise):
        result = writeback.approve_and_dispatch(run_id, paths=paths)

    assert result.target_status["meatywiki"] == "failed"
    assert result.target_status["ccdash"] != "skipped"
    assert result.target_status["skillmeat"] != "skipped"
    assert result.target_status["ccdash"] == "success"
    assert result.target_status["skillmeat"] == "success"

    # The other two targets were genuinely attempted (real files on disk).
    assert rp.ccdash_event.exists()
    assert rp.skillbom_candidate.exists()

    assert result.overall_status == "partial"


# --------------------------------------------------------------------------- #
# 4. approved_by / approval_timestamp: populated on success, None on blocked.
# --------------------------------------------------------------------------- #
def test_approved_by_and_timestamp_populated_on_success(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)

    result = writeback.approve_and_dispatch(
        run_id, approver_identity="alice@example.com", paths=paths
    )
    assert result.overall_status == "success"

    bundle = load_yaml(rp.evidence_bundle)
    assert bundle["governance"]["approved_by"] == "alice@example.com"
    assert bundle["governance"]["approval_timestamp"] is not None


def test_approved_by_and_timestamp_not_populated_on_blocked(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)

    failing_guard = GuardResult(passed=False, exit_code=3, violations=[])
    with patch.object(writeback.governance, "guard_check", return_value=failing_guard):
        result = writeback.approve_and_dispatch(
            run_id, approver_identity="alice@example.com", paths=paths
        )

    assert result.overall_status == "blocked"

    bundle = load_yaml(rp.evidence_bundle)
    assert bundle["governance"]["approved_by"] is None
    assert bundle["governance"]["approval_timestamp"] is None


# --------------------------------------------------------------------------- #
# 5. overall_status aggregation.
# --------------------------------------------------------------------------- #
def test_overall_status_success_when_gate_passes_and_all_targets_succeed(
    tmp_foundry: FoundryPaths,
):
    paths = tmp_foundry
    run_id = _build_run(paths)

    result = writeback.approve_and_dispatch(run_id, paths=paths)

    assert result.overall_status == "success"
    assert all(status == "success" for status in result.target_status.values())


def test_overall_status_partial_when_gate_passes_but_all_targets_fail(
    tmp_foundry: FoundryPaths,
):
    paths = tmp_foundry
    run_id = _build_run(paths)

    def _boom(*args, **kwargs):
        raise RuntimeError("forced failure for test")

    with (
        patch.object(writeback.telemetry, "emit_ccdash_event", side_effect=_boom),
        patch.object(writeback, "_render_meatywiki", side_effect=_boom),
        patch.object(writeback, "_render_skillbom", side_effect=_boom),
    ):
        result = writeback.approve_and_dispatch(run_id, paths=paths)

    # A fully-failed post-gate dispatch is "partial", never "blocked" — the
    # gate itself passed, so this is "we tried and it went badly", not
    # "we never tried".
    assert result.overall_status == "partial"
    assert result.overall_status != "blocked"
    assert all(status == "failed" for status in result.target_status.values())


def test_overall_status_partial_when_gate_passes_and_targets_are_mixed(
    tmp_foundry: FoundryPaths,
):
    paths = tmp_foundry
    run_id = _build_run(paths)

    def _boom(*args, **kwargs):
        raise RuntimeError("forced failure for test")

    with patch.object(writeback, "_render_meatywiki", side_effect=_boom):
        result = writeback.approve_and_dispatch(run_id, paths=paths)

    assert result.overall_status == "partial"
    assert result.overall_status != "blocked"
    assert result.target_status["meatywiki"] == "failed"
    assert result.target_status["ccdash"] == "success"
    assert result.target_status["skillmeat"] == "success"
