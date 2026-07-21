"""Offline tests for the deterministic swarm-drive spine (E1-P0a, SD-007).

Every test here is fully offline and makes **zero** model/network calls:

* the deterministic pipeline (steps 1/4/5/7) is exercised on fixture runs built
  with the real rf services;
* the discovery lane is exercised with an **injected** fake SearXNG provider
  (no network) so SD-003's ``source_candidates.yaml`` + ``redact_payload``
  routing can be asserted;
* the milestone pushes are best-effort and offline (``push_status`` returns
  ``False`` with no IntentTree reachable — asserted never to block the loop).

Coverage maps to the SD-001..SD-007 task table:

* SD-001 — unknown/malformed run raises ``DriveError``.
* SD-002 — ``work_sensitive`` raises ``SensitivityBlocked`` before any dispatch;
  a drifted roster role-set raises ``RosterSchemaError``.
* SD-003 — discovery produces ``source_candidates.yaml`` via the free_discovery
  lane; ingest routes through ``run_job_tool``; the drive's own write routes
  through ``governance.redact_payload``.
* SD-004 — a fixture run reaches ``status_derived == "bundle_written"``; a
  telemetry-push failure never blocks the drive.
* SD-005 — resume-at-first-missing-artifact; a completed re-run is a no-op.
* SD-006 — ``--llm-legs ica`` fails loudly; the CLI ``drive`` path reaches
  ``bundle_written`` end-to-end in ``tmp_foundry``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths
from research_foundry.services import extraction, governance, planning, source_cards, swarm_drive
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.search_router.providers.base import (
    ProviderResult,
    SearchHit,
)
from research_foundry.services.swarm_drive import (
    DriveError,
    DriveState,
    RosterSchemaError,
    SensitivityBlocked,
    drive_run,
)
from research_foundry.yamlio import dump_yaml, load_yaml

runner = CliRunner()

_INTENT_ID = "intent_research_20260613_swarm_drive"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_intent(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    intent = {
        "id": _INTENT_ID,
        "title": "Swarm drive demo topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Investigate the swarm-drive spine deterministically.",
        "governance": {
            "sensitivity": sensitivity,
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")
    return _INTENT_ID


def _planned_run(paths: FoundryPaths) -> str:
    """A real planned run (correct 6-role roster) via ``plan_run``."""

    _write_intent(paths)
    result = planning.plan_run(_INTENT_ID, profile="personal", paths=paths)
    return result.run_id


def _seed_evidence(paths: FoundryPaths, run_id: str, tmp_path: Path) -> None:
    """Populate source card + extraction cards + claim ledger for a run.

    Also writes an (empty) ``source_candidates.yaml`` so the resume logic skips
    the discovery + ingest lanes entirely — keeping the test fully offline.
    """

    rp = paths.run_paths(run_id)
    doc = tmp_path / "evidence.txt"
    doc.write_text(
        "Latency dropped 30% with the new router.\n\n"
        "Teams report fewer escalations than before, according to the survey.\n\n"
        "Evidence bundles make claim traceability auditable end to end.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(
        str(doc), run_id=run_id, title="Evidence Source", paths=paths
    )
    extraction.extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=_INTENT_ID, paths=paths)
    # Pre-seed source_candidates so discovery is a no-op (offline resume).
    dump_yaml({"source_candidates": []}, rp.source_candidates)


class _FakeSearxProvider:
    """An injected free_discovery provider — no network, fixed hits."""

    id = "searxng"
    roles = ("discovery",)
    requires = ()
    env_keys = ()

    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    def available(self) -> bool:  # noqa: D401
        return True

    def search(self, query: str, *, max_results: int, constraints: dict) -> ProviderResult:
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=list(self._hits[:max_results]),
            estimated_cost_usd=0.0,
        )

    def extract(self, urls: list[str]) -> ProviderResult:  # pragma: no cover
        return ProviderResult(provider=self.id, role="extraction", status="skipped")


class _RecordingJobService:
    """Wraps a real ``AgentJobService`` and records tool-call names (SD-003)."""

    def __init__(self, paths: FoundryPaths) -> None:
        from research_foundry.services.agent_job_service import AgentJobService

        self._inner = AgentJobService(paths=paths)
        self.calls: list[str] = []

    def run_job_tool(self, tool_name, tool_input, job, paths=None):
        self.calls.append(tool_name)
        return self._inner.run_job_tool(tool_name, tool_input, job, paths=paths)


# ---------------------------------------------------------------------------
# SD-001 — resolve + typed errors
# ---------------------------------------------------------------------------


def test_unknown_run_raises_drive_error(tmp_foundry):
    with pytest.raises(DriveError):
        drive_run("rf_run_does_not_exist", paths=tmp_foundry)


def test_malformed_run_yaml_raises_drive_error(tmp_foundry):
    rp = tmp_foundry.run_paths("rf_run_malformed")
    rp.run.mkdir(parents=True)
    rp.run_yaml.write_text("", encoding="utf-8")  # empty → malformed
    with pytest.raises(DriveError):
        drive_run("rf_run_malformed", paths=tmp_foundry)


def test_drive_run_returns_drivestate(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)
    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert isinstance(state, DriveState)
    assert state.run_id == run_id
    assert state.llm_legs == "none"


# ---------------------------------------------------------------------------
# SD-002 — sensitivity assert + roster schema pin
# ---------------------------------------------------------------------------


def test_work_sensitive_run_blocked_before_dispatch(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    # Flip sensitivity to work_sensitive directly on run.yaml.
    meta = load_yaml(rp.run_yaml)
    meta["sensitivity"] = "work_sensitive"
    dump_yaml(meta, rp.run_yaml)

    with pytest.raises(SensitivityBlocked):
        drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})

    # Nothing was dispatched: no source_candidates / source cards written.
    assert not rp.source_candidates.exists()
    assert not any(rp.sources.glob("*.md")) if rp.sources.exists() else True


def test_public_sensitivity_is_drivable(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    meta = load_yaml(rp.run_yaml)
    meta["sensitivity"] = "public"
    dump_yaml(meta, rp.run_yaml)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert state.status_derived == "bundle_written"


def test_roster_role_set_drift_raises(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    plan = load_yaml(rp.swarm_plan)
    # Rename one role → role set drifts from the fixed roster.
    plan["agents"][0]["role"] = "rogue_role"
    dump_yaml(plan, rp.swarm_plan)

    with pytest.raises(RosterSchemaError):
        drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})


def test_missing_swarm_plan_raises(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    rp.swarm_plan.unlink()
    with pytest.raises(DriveError):
        drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})


# ---------------------------------------------------------------------------
# SD-003 — discovery + ingest via run_job_tool through redact_payload
# ---------------------------------------------------------------------------


def test_discovery_ingest_produces_candidates_and_routes_through_redact(
    tmp_foundry, tmp_path, monkeypatch
):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    hits = [
        SearchHit(title="Doc A", url="https://example.org/a", source_type="official_docs"),
        SearchHit(title="Doc B", url="https://example.org/b", source_type="reputable_news"),
    ]
    providers = {"searxng": _FakeSearxProvider(hits)}
    job_service = _RecordingJobService(tmp_foundry)

    # Spy on redact_payload to prove the drive's own write is redacted (SD-003).
    real_redact = governance.redact_payload
    seen: list[int] = []

    def _spy(obj, *, config=None):
        seen.append(1)
        return real_redact(obj, config=config)

    monkeypatch.setattr(governance, "redact_payload", _spy)

    state = drive_run(
        run_id,
        llm_legs="none",
        paths=tmp_foundry,
        providers=providers,
        job_service=job_service,
    )

    # Discovery wrote source_candidates.yaml with the injected hits.
    assert rp.source_candidates.exists()
    data = load_yaml(rp.source_candidates)
    assert len(data["source_candidates"]) == 2
    assert "discovery" in state.steps_run

    # The drive's own write routed through redact_payload.
    assert seen, "swarm-drive write bypassed governance.redact_payload"

    # Ingest went through run_job_tool (the redacting chokepoint) — one per hit.
    assert job_service.calls.count("source_card") == 2
    assert any(rp.sources.glob("*.md"))


# ---------------------------------------------------------------------------
# SD-004 — deterministic synth/verify/bundle + milestone resilience
# ---------------------------------------------------------------------------


def test_fixture_run_reaches_bundle_written(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})

    assert state.status_derived == "bundle_written"
    rp = tmp_foundry.run_paths(run_id)
    assert rp.report_draft.exists()
    assert rp.verification.exists()
    assert rp.evidence_bundle.exists()
    assert state.verified is True
    assert state.bundle_path == rp.evidence_bundle


def test_telemetry_push_failure_never_blocks(tmp_foundry, tmp_path, monkeypatch):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    def _boom(*args, **kwargs):
        raise RuntimeError("intenttree unreachable")

    # push_status raising must not break the drive (wrapped by _push).
    monkeypatch.setattr(swarm_drive.telemetry, "push_status", _boom)

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert state.status_derived == "bundle_written"
    assert state.milestones_pushed == ()  # all pushes swallowed


# ---------------------------------------------------------------------------
# SD-005 — resume / idempotency
# ---------------------------------------------------------------------------


def test_resume_from_missing_claim_ledger(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)
    rp = tmp_foundry.run_paths(run_id)

    # Simulate a crash after extraction but before claim-mapping.
    rp.claim_ledger.unlink()

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})

    assert state.status_derived == "bundle_written"
    # Resumed: discovery/ingest/extraction skipped; claim-map onward re-run.
    assert "claim_map" in state.steps_run
    assert "discovery" in state.steps_skipped
    assert "ingest" in state.steps_skipped
    assert "extraction" in state.steps_skipped


def test_rerun_completed_run_is_noop(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    first = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert first.status_derived == "bundle_written"

    # Snapshot mtimes of every run artifact, then re-drive.
    rp = tmp_foundry.run_paths(run_id)
    before = {p: p.stat().st_mtime_ns for p in rp.run.rglob("*") if p.is_file()}

    second = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert second.status_derived == "bundle_written"
    assert second.steps_run == ()  # pure no-op

    after = {p: p.stat().st_mtime_ns for p in rp.run.rglob("*") if p.is_file()}
    assert before == after, "re-running a completed run wrote to disk"


# ---------------------------------------------------------------------------
# SD-006 — --llm-legs flag + CLI path
# ---------------------------------------------------------------------------


def test_unknown_llm_legs_raises_drive_error(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    with pytest.raises(DriveError):
        drive_run(run_id, llm_legs="bogus", paths=tmp_foundry)


def _invoke(args: list[str], cwd: Path):
    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(prev)


def test_cli_drive_reaches_bundle_written(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    out = _invoke(["swarm", "drive", run_id], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert "bundle_written" in out.output


def test_cli_drive_json_output(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    out = _invoke(["swarm", "drive", run_id, "--json"], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert '"status_derived": "bundle_written"' in out.output


def test_cli_drive_ica_emits_bundle(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    # Pre-seed empty source_candidates so discovery is a fully offline no-op.
    dump_yaml({"source_candidates": []}, rp.source_candidates)

    out = _invoke(["swarm", "drive", run_id, "--llm-legs", "ica"], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert "awaiting_legs" in out.output
    assert "leg-request bundle" in out.output
    assert (rp.run / "leg_requests.yaml").exists()


def test_cli_drive_ica_json(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    dump_yaml({"source_candidates": []}, rp.source_candidates)

    out = _invoke(["swarm", "drive", run_id, "--llm-legs", "ica", "--json"], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert '"status_derived": "awaiting_legs"' in out.output
    assert '"leg_bundle"' in out.output


# ---------------------------------------------------------------------------
# SD-008 — --llm-legs ica emits a well-formed leg-request bundle (SEAM-001)
# ---------------------------------------------------------------------------


def test_ica_emit_bundle_shape_and_fences(tmp_foundry, monkeypatch):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    hits = [
        SearchHit(
            title="Doc A", url="https://example.org/a",
            snippet="Alpha finding.", source_type="official_docs",
        ),
        SearchHit(
            title="Doc B", url="https://example.org/b",
            snippet="Beta finding.", source_type="reputable_news",
        ),
    ]
    providers = {"searxng": _FakeSearxProvider(hits)}

    # Spy on redact_payload to prove the emitted bundle routes through it.
    real_redact = governance.redact_payload
    seen: list[int] = []

    def _spy(obj, *, config=None):
        seen.append(1)
        return real_redact(obj, config=config)

    monkeypatch.setattr(governance, "redact_payload", _spy)

    state = drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers=providers)

    # Terminal state = awaiting_legs, bundle returned in DriveState.
    assert isinstance(state, DriveState)
    assert state.status_derived == "awaiting_legs"
    assert state.llm_legs == "ica"
    assert state.bundle_path is None
    assert state.leg_bundle is not None

    b = state.leg_bundle
    assert b["schema_version"] == swarm_drive._LEG_SCHEMA_VERSION
    assert b["kind"] == swarm_drive._LEG_BUNDLE_KIND
    assert b["run_id"] == run_id
    assert b["safety_instruction"] == swarm_drive._SAFETY_INSTRUCTION

    legs = b["legs"]
    carding = [leg for leg in legs if leg["leg_type"] == swarm_drive._LEG_CARDING]
    claim = [leg for leg in legs if leg["leg_type"] == swarm_drive._LEG_CLAIM_MAP]

    # One carding leg per discovered source; exactly one claim_map leg.
    assert [leg["id"] for leg in carding] == ["carding-1", "carding-2"]
    assert len(claim) == 1

    for leg in carding:
        assert leg["untrusted"] is True
        assert swarm_drive._UNTRUSTED_FLAG in leg["risk_flags"]
        assert leg["model"] == swarm_drive._CARDING_MODEL
        assert leg["prompt"] == swarm_drive._CARDING_PROMPT
        assert leg["feedback_note"] == swarm_drive._CARDING_FEEDBACK_NOTE
        # Fenced untrusted body — begins/ends with the canonical fence.
        assert leg["body"].startswith(swarm_drive._FENCE_BEGIN)
        assert leg["body"].rstrip().endswith(swarm_drive._FENCE_END)

    cm = claim[0]
    assert cm["id"] == swarm_drive._CLAIM_MAP_LEG_ID
    assert cm["model"] == swarm_drive._CLAIM_MAP_MODEL
    assert cm["prompt"] == swarm_drive._CLAIM_MAP_PROMPT
    assert cm["feedback_note"] == swarm_drive._CLAIM_MAP_FEEDBACK_NOTE
    assert cm["claim_schema"] == swarm_drive._CLAIM_SCHEMA
    # claim_map depends on every carding leg id.
    assert cm["depends_on"] == ["carding-1", "carding-2"]

    # Emitted bundle routed through governance.redact_payload (D5).
    assert seen, "ica emit bypassed governance.redact_payload"

    # Written to a run artifact, and the on-disk copy matches.
    leg_path = rp.run / "leg_requests.yaml"
    assert leg_path.exists()
    disk = load_yaml(leg_path)
    assert disk["schema_version"] == swarm_drive._LEG_SCHEMA_VERSION
    assert len([leg for leg in disk["legs"] if leg["leg_type"] == "carding"]) == 2


def test_ica_emit_no_sources_still_emits_bundle(tmp_foundry):
    """Never a silent no-op: zero sources still emits a claim_map leg."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    # providers={} → no discovery provider dispatched → zero candidates.
    state = drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers={})

    assert state.status_derived == "awaiting_legs"
    legs = state.leg_bundle["legs"]
    carding = [leg for leg in legs if leg["leg_type"] == swarm_drive._LEG_CARDING]
    claim = [leg for leg in legs if leg["leg_type"] == swarm_drive._LEG_CLAIM_MAP]
    assert carding == []
    assert len(claim) == 1
    assert claim[0]["depends_on"] == []
    assert (rp.run / "leg_requests.yaml").exists()


def test_ica_emit_blocked_for_work_sensitive(tmp_foundry):
    """The ica emit path is gated by the same sensitivity guard as `none`."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    meta = load_yaml(rp.run_yaml)
    meta["sensitivity"] = "work_sensitive"
    dump_yaml(meta, rp.run_yaml)

    with pytest.raises(SensitivityBlocked):
        drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers={})

    # Nothing emitted before the guard.
    assert not (rp.run / "leg_requests.yaml").exists()


def test_ica_emit_roster_drift_blocks_before_emit(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    plan = load_yaml(rp.swarm_plan)
    plan["agents"][0]["role"] = "rogue_role"
    dump_yaml(plan, rp.swarm_plan)

    with pytest.raises(RosterSchemaError):
        drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers={})
    assert not (rp.run / "leg_requests.yaml").exists()
