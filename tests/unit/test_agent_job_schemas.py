"""Unit tests for agent-job schema dataclasses (plan OQ-B, FR-3, JOB-1.3).

Covers:
- AgentJob round-trip (to_dict / from_dict identity)
- validate_agent_job — empty dict, valid minimal dict
- FoundryPaths.agent_job_dir path resolution (NOT under .rf_cache/)
- Round-trips for all 5 child records: AgentJobEvent, AgentJobArtifact,
  AgentJobToolCall, AgentJobApproval, AgentJobAcceptance
- ResearchAgentProvider Protocol isinstance check with a concrete stub

No state-machine transition tests (that is JOB-1.4's scope).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import (
    LEGAL_TRANSITIONS,
    AgentJob,
    AgentJobAcceptance,
    AgentJobApproval,
    AgentJobArtifact,
    AgentJobEvent,
    AgentJobStage,
    AgentJobStatus,
    AgentJobToolCall,
    validate_agent_job,
    validate_transition,
)
from research_foundry.services.agent_providers.base import ResearchAgentProvider

# ---------------------------------------------------------------------------
# Fixtures — fully-populated dicts (used as both construction input and
# round-trip targets)
# ---------------------------------------------------------------------------


def _agent_job_dict() -> dict[str, Any]:
    return {
        "agent_job_id": "job-abc-001",
        "project_id": "proj-xyz",
        "workspace_id": "ws-001",
        "created_by": "user-alice",
        "provider": "local_swarm",
        "model_profile": "sonnet",
        "request_kind": "deep_research",
        "input_claim_ids": ["clm_001", "clm_002"],
        "input_source_ids": ["src_001"],
        "input_report_id": "rep_001",
        "policy_snapshot": {
            "allowed_tools": ["web_search", "file_read"],
            "data_scopes": ["public"],
        },
        "budget_usd": 2.50,
        "max_runtime_minutes": 30,
        "status": "queued",
        "created_at": "2026-07-06T10:00:00Z",
        "updated_at": "2026-07-06T10:00:01Z",
        "started_at": None,
        "completed_at": None,
    }


def _event_dict() -> dict[str, Any]:
    return {
        "event_id": "evt-001",
        "agent_job_id": "job-abc-001",
        "stage": "search",
        "timestamp": "2026-07-06T10:01:00Z",
        "payload": {"query": "agentic sdlc", "results_count": 12},
        "sequence": 1,
    }


def _artifact_dict() -> dict[str, Any]:
    return {
        "artifact_id": "art-001",
        "agent_job_id": "job-abc-001",
        "artifact_kind": "report_draft",
        "created_at": "2026-07-06T10:05:00Z",
        "path": "report_draft.md",
        "content_hash": "sha256:abc123",
        "accepted": True,
    }


def _tool_call_dict() -> dict[str, Any]:
    return {
        "tool_call_id": "tc-001",
        "agent_job_id": "job-abc-001",
        "tool_name": "web_search",
        "tool_input": {"query": "agentic sdlc governance"},
        "called_at": "2026-07-06T10:01:05Z",
        "event_id": "evt-001",
        "tool_output": {"results": ["url1", "url2"]},
        "duration_ms": 340,
    }


def _approval_dict() -> dict[str, Any]:
    return {
        "approval_id": "apr-001",
        "agent_job_id": "job-abc-001",
        "requested_at": "2026-07-06T10:02:00Z",
        "approved_by": "user-alice",
        "approved_at": "2026-07-06T10:03:00Z",
        "rejected_at": None,
        "notes": "LGTM",
        "approved": True,
    }


def _acceptance_dict() -> dict[str, Any]:
    return {
        "acceptance_id": "acc-001",
        "agent_job_id": "job-abc-001",
        "accepted_at": "2026-07-06T10:06:00Z",
        "artifact_ids": ["art-001", "art-002"],
        "accepted_by": "user-alice",
        "notes": "Accepted both artifacts",
    }


# ---------------------------------------------------------------------------
# AgentJob round-trip
# ---------------------------------------------------------------------------


def test_agent_job_round_trip() -> None:
    raw = _agent_job_dict()
    job = AgentJob.from_dict(raw)
    assert AgentJob.from_dict(job.to_dict()) == job


def test_agent_job_status_enum_roundtrip() -> None:
    job = AgentJob.from_dict(_agent_job_dict())
    assert job.status is AgentJobStatus.queued
    assert job.to_dict()["status"] == "queued"


def test_agent_job_list_fields_default_to_empty() -> None:
    """Missing list fields in raw dict fall back to empty lists gracefully."""
    raw = _agent_job_dict()
    del raw["input_claim_ids"]
    del raw["input_source_ids"]
    job = AgentJob.from_dict(raw)
    assert job.input_claim_ids == []
    assert job.input_source_ids == []


# ---------------------------------------------------------------------------
# validate_agent_job
# ---------------------------------------------------------------------------


def test_validate_agent_job_empty_dict_has_errors() -> None:
    errors = validate_agent_job({})
    assert len(errors) > 0


def test_validate_agent_job_valid_minimal_dict_no_errors() -> None:
    raw = _agent_job_dict()
    errors = validate_agent_job(raw)
    assert errors == []


def test_validate_agent_job_invalid_status() -> None:
    raw = _agent_job_dict()
    raw["status"] = "not_a_real_status"
    errors = validate_agent_job(raw)
    assert any("invalid status" in e for e in errors)


def test_validate_agent_job_missing_policy_snapshot_keys() -> None:
    raw = _agent_job_dict()
    raw["policy_snapshot"] = {}  # missing allowed_tools + data_scopes
    errors = validate_agent_job(raw)
    assert any("allowed_tools" in e for e in errors)
    assert any("data_scopes" in e for e in errors)


# ---------------------------------------------------------------------------
# FoundryPaths.agent_job_dir
# ---------------------------------------------------------------------------


def test_agent_job_dir_not_under_rf_cache() -> None:
    fp = FoundryPaths(root=Path("/tmp/ws"))
    result = fp.agent_job_dir("abc-123")
    assert result == Path("/tmp/ws/agent_jobs/abc-123")
    # Must NOT be under .rf_cache/
    assert ".rf_cache" not in result.parts


def test_agent_jobs_property() -> None:
    fp = FoundryPaths(root=Path("/tmp/ws"))
    assert fp.agent_jobs == Path("/tmp/ws/agent_jobs")


# ---------------------------------------------------------------------------
# AgentJobEvent round-trip
# ---------------------------------------------------------------------------


def test_agent_job_event_round_trip() -> None:
    raw = _event_dict()
    evt = AgentJobEvent.from_dict(raw)
    assert AgentJobEvent.from_dict(evt.to_dict()) == evt


def test_agent_job_event_stage_enum() -> None:
    evt = AgentJobEvent.from_dict(_event_dict())
    assert evt.stage is AgentJobStage.search
    assert evt.to_dict()["stage"] == "search"


def test_agent_job_event_all_stages_valid() -> None:
    """Every AgentJobStage value round-trips through from_dict."""
    for stage in AgentJobStage:
        raw = _event_dict()
        raw["stage"] = stage.value
        evt = AgentJobEvent.from_dict(raw)
        assert evt.stage is stage


# ---------------------------------------------------------------------------
# AgentJobArtifact round-trip
# ---------------------------------------------------------------------------


def test_agent_job_artifact_round_trip() -> None:
    raw = _artifact_dict()
    art = AgentJobArtifact.from_dict(raw)
    assert AgentJobArtifact.from_dict(art.to_dict()) == art


def test_agent_job_artifact_defaults() -> None:
    """Required-only construction uses correct defaults."""
    art = AgentJobArtifact(
        artifact_id="art-min",
        agent_job_id="job-abc-001",
        artifact_kind="source_card",
        created_at="2026-07-06T10:00:00Z",
    )
    assert art.path is None
    assert art.content_hash is None
    assert art.accepted is False


def test_agent_job_artifact_nullable_fields_round_trip() -> None:
    raw = _artifact_dict()
    raw["path"] = None
    raw["content_hash"] = None
    raw["accepted"] = False
    art = AgentJobArtifact.from_dict(raw)
    assert art.path is None
    assert art.content_hash is None
    assert art.accepted is False
    assert AgentJobArtifact.from_dict(art.to_dict()) == art


# ---------------------------------------------------------------------------
# AgentJobToolCall round-trip
# ---------------------------------------------------------------------------


def test_agent_job_tool_call_round_trip() -> None:
    raw = _tool_call_dict()
    tc = AgentJobToolCall.from_dict(raw)
    assert AgentJobToolCall.from_dict(tc.to_dict()) == tc


def test_agent_job_tool_call_nullable_fields() -> None:
    raw = _tool_call_dict()
    raw["event_id"] = None
    raw["tool_output"] = None
    raw["duration_ms"] = None
    tc = AgentJobToolCall.from_dict(raw)
    assert tc.event_id is None
    assert tc.tool_output is None
    assert tc.duration_ms is None
    assert AgentJobToolCall.from_dict(tc.to_dict()) == tc


# ---------------------------------------------------------------------------
# AgentJobApproval round-trip
# ---------------------------------------------------------------------------


def test_agent_job_approval_round_trip() -> None:
    raw = _approval_dict()
    apr = AgentJobApproval.from_dict(raw)
    assert AgentJobApproval.from_dict(apr.to_dict()) == apr


def test_agent_job_approval_pending_state() -> None:
    """``approved=None`` means pending — must survive round-trip."""
    raw = _approval_dict()
    raw["approved"] = None
    raw["approved_by"] = None
    raw["approved_at"] = None
    apr = AgentJobApproval.from_dict(raw)
    assert apr.approved is None
    assert AgentJobApproval.from_dict(apr.to_dict()) == apr


def test_agent_job_approval_rejected_state() -> None:
    raw = _approval_dict()
    raw["approved"] = False
    raw["approved_at"] = None
    raw["rejected_at"] = "2026-07-06T10:04:00Z"
    apr = AgentJobApproval.from_dict(raw)
    assert apr.approved is False
    assert AgentJobApproval.from_dict(apr.to_dict()) == apr


# ---------------------------------------------------------------------------
# AgentJobAcceptance round-trip
# ---------------------------------------------------------------------------


def test_agent_job_acceptance_round_trip() -> None:
    raw = _acceptance_dict()
    acc = AgentJobAcceptance.from_dict(raw)
    assert AgentJobAcceptance.from_dict(acc.to_dict()) == acc


def test_agent_job_acceptance_artifact_ids_list() -> None:
    acc = AgentJobAcceptance.from_dict(_acceptance_dict())
    assert acc.artifact_ids == ["art-001", "art-002"]


def test_agent_job_acceptance_empty_artifact_ids() -> None:
    raw = _acceptance_dict()
    raw["artifact_ids"] = []
    acc = AgentJobAcceptance.from_dict(raw)
    assert acc.artifact_ids == []
    assert AgentJobAcceptance.from_dict(acc.to_dict()) == acc


# ---------------------------------------------------------------------------
# ResearchAgentProvider Protocol isinstance check
# ---------------------------------------------------------------------------


class _ConcreteProvider:
    """Minimal concrete stub satisfying ResearchAgentProvider Protocol."""

    id: str = "test_provider"

    def start_job(self, job: dict[str, Any]) -> str:
        return "job-stub-001"

    def stream_events(self, job_id: str) -> Iterator[dict[str, Any]]:
        return iter([])

    def cancel_job(self, job_id: str) -> None:
        pass

    def list_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        return []

    def accept_artifacts(self, job_id: str, artifact_ids: list[str]) -> None:
        pass


def test_concrete_provider_satisfies_protocol() -> None:
    stub = _ConcreteProvider()
    assert isinstance(stub, ResearchAgentProvider)


def test_object_missing_method_fails_protocol() -> None:
    """An object lacking required Protocol methods must fail isinstance."""

    class _Incomplete:
        id: str = "incomplete"
        # Missing: start_job, stream_events, cancel_job, list_artifacts, accept_artifacts

    assert not isinstance(_Incomplete(), ResearchAgentProvider)


# ---------------------------------------------------------------------------
# State-machine transition tests (JOB-1.4)
# ---------------------------------------------------------------------------


def test_state_machine_legal_transitions() -> None:
    """Every edge declared in LEGAL_TRANSITIONS must not raise."""
    for from_s, targets in LEGAL_TRANSITIONS.items():
        for to_s in targets:
            # Must not raise
            validate_transition(from_s, to_s)


def test_state_machine_illegal_transitions() -> None:
    """Every pair NOT in LEGAL_TRANSITIONS must raise ValueError with
    the expected message fragment."""
    all_statuses = list(AgentJobStatus)
    for from_s in all_statuses:
        for to_s in all_statuses:
            if to_s not in LEGAL_TRANSITIONS[from_s]:
                with pytest.raises(ValueError, match=r"Illegal AgentJob transition"):
                    validate_transition(from_s, to_s)


def test_terminal_states_have_no_outgoing() -> None:
    """``failed``, ``canceled``, and ``accepted`` are terminal — no outgoing edges."""
    assert LEGAL_TRANSITIONS[AgentJobStatus.failed] == set()
    assert LEGAL_TRANSITIONS[AgentJobStatus.canceled] == set()
    assert LEGAL_TRANSITIONS[AgentJobStatus.accepted] == set()
