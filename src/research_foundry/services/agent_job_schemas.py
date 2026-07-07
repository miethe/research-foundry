"""Schema definitions for durable agent-job records (plan OQ-B, FR-3).

Each ``AgentJob`` record represents a single bounded agent execution request
persisted under ``<workspace>/agent_jobs/<agent_job_id>/``.  Records are
file-canonical: the YAML on disk is the truth; the catalog DB is a rebuildable
read model.

Child records (``AgentJobEvent``, ``AgentJobArtifact``, ``AgentJobToolCall``,
``AgentJobApproval``, ``AgentJobAcceptance``) follow the same frozen-dataclass
/ ``to_dict`` / ``from_dict`` pattern as ``AgentJob``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "AgentJobStatus",
    "AgentJobStage",
    "AgentJob",
    "AgentJobEvent",
    "AgentJobArtifact",
    "AgentJobToolCall",
    "AgentJobApproval",
    "AgentJobAcceptance",
    "validate_agent_job",
    "LEGAL_TRANSITIONS",
    "validate_transition",
]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {
    "agent_job_id",
    "project_id",
    "provider",
    "model_profile",
    "request_kind",
    "policy_snapshot",
    "status",
    "created_at",
    "updated_at",
}


class AgentJobStatus(str, Enum):
    """Lifecycle states for an ``AgentJob`` record."""

    queued = "queued"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    failed = "failed"
    canceled = "canceled"
    completed = "completed"
    accepted = "accepted"


class AgentJobStage(str, Enum):
    """Discrete pipeline stage recorded on each streaming event."""

    plan = "plan"
    search = "search"
    source_intake = "source_intake"
    extraction = "extraction"
    claim_proposal = "claim_proposal"
    contradiction_check = "contradiction_check"
    verification = "verification"
    synthesis = "synthesis"


# ---------------------------------------------------------------------------
# AgentJob dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentJob:
    """Immutable record for a single durable agent-job (plan OQ-B, FR-3).

    All timestamp fields use ISO-8601 strings so the record round-trips
    through YAML/JSON without a datetime dependency.
    """

    # --- identity ---
    agent_job_id: str
    project_id: str

    # --- optional actor/workspace context ---
    workspace_id: str | None
    created_by: str | None

    # --- routing ---
    provider: str
    model_profile: str
    request_kind: str

    # --- input references ---
    input_claim_ids: list[str]
    input_source_ids: list[str]
    input_report_id: str | None

    # --- policy ---
    policy_snapshot: dict[str, Any]

    # --- resource limits ---
    budget_usd: float | None
    max_runtime_minutes: int | None

    # --- lifecycle ---
    status: AgentJobStatus
    created_at: str
    updated_at: str
    started_at: str | None
    completed_at: str | None

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-serialisable dictionary representation."""
        return {
            "agent_job_id": self.agent_job_id,
            "workspace_id": self.workspace_id,
            "created_by": self.created_by,
            "project_id": self.project_id,
            "provider": self.provider,
            "model_profile": self.model_profile,
            "request_kind": self.request_kind,
            "input_claim_ids": list(self.input_claim_ids),
            "input_source_ids": list(self.input_source_ids),
            "input_report_id": self.input_report_id,
            "policy_snapshot": dict(self.policy_snapshot),
            "budget_usd": self.budget_usd,
            "max_runtime_minutes": self.max_runtime_minutes,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentJob:
        """Construct an ``AgentJob`` from a raw dictionary (e.g. parsed YAML).

        Missing list/optional fields fall back to their defaults so that
        partial records stored on disk (e.g. before a field was added) can
        still be loaded.
        """
        return cls(
            agent_job_id=d["agent_job_id"],
            workspace_id=d.get("workspace_id"),
            created_by=d.get("created_by"),
            project_id=d["project_id"],
            provider=d["provider"],
            model_profile=d["model_profile"],
            request_kind=d["request_kind"],
            input_claim_ids=list(d.get("input_claim_ids") or []),
            input_source_ids=list(d.get("input_source_ids") or []),
            input_report_id=d.get("input_report_id"),
            policy_snapshot=dict(d.get("policy_snapshot") or {}),
            budget_usd=d.get("budget_usd"),
            max_runtime_minutes=d.get("max_runtime_minutes"),
            status=AgentJobStatus(d["status"]),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
        )


# ---------------------------------------------------------------------------
# Child record dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentJobEvent:
    """A single streaming event emitted by a running agent job.

    ``payload`` is stored as-is (will be selectively redacted in P4.2).
    ``sequence`` is a monotonic counter within the parent job.
    """

    event_id: str
    agent_job_id: str
    stage: AgentJobStage
    timestamp: str
    payload: dict[str, Any]
    sequence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "agent_job_id": self.agent_job_id,
            "stage": self.stage.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentJobEvent:
        return cls(
            event_id=d["event_id"],
            agent_job_id=d["agent_job_id"],
            stage=AgentJobStage(d["stage"]),
            timestamp=d["timestamp"],
            payload=dict(d.get("payload") or {}),
            sequence=int(d["sequence"]),
        )


@dataclass(frozen=True)
class AgentJobArtifact:
    """A file or content artifact produced by a completed agent job.

    ``path`` is relative to the job's ``agent_job_dir``; ``content_hash``
    is an optional integrity check.  ``accepted`` defaults to ``False`` and
    is flipped by an :class:`AgentJobAcceptance` record.
    """

    artifact_id: str
    agent_job_id: str
    artifact_kind: str
    created_at: str
    path: str | None = None
    content_hash: str | None = None
    accepted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "agent_job_id": self.agent_job_id,
            "artifact_kind": self.artifact_kind,
            "created_at": self.created_at,
            "path": self.path,
            "content_hash": self.content_hash,
            "accepted": self.accepted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentJobArtifact:
        return cls(
            artifact_id=d["artifact_id"],
            agent_job_id=d["agent_job_id"],
            artifact_kind=d["artifact_kind"],
            created_at=d["created_at"],
            path=d.get("path"),
            content_hash=d.get("content_hash"),
            accepted=bool(d.get("accepted", False)),
        )


@dataclass(frozen=True)
class AgentJobToolCall:
    """Record of a single tool invocation during a job run.

    ``tool_input`` and ``tool_output`` are stored as-is (will be selectively
    redacted in P4.2).  ``duration_ms`` and ``tool_output`` are nullable to
    support in-flight records (output not yet available).
    """

    tool_call_id: str
    agent_job_id: str
    tool_name: str
    tool_input: dict[str, Any]
    called_at: str
    event_id: str | None = None
    tool_output: dict[str, Any] | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "agent_job_id": self.agent_job_id,
            "tool_name": self.tool_name,
            "tool_input": dict(self.tool_input),
            "called_at": self.called_at,
            "event_id": self.event_id,
            "tool_output": dict(self.tool_output) if self.tool_output is not None else None,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentJobToolCall:
        raw_output = d.get("tool_output")
        return cls(
            tool_call_id=d["tool_call_id"],
            agent_job_id=d["agent_job_id"],
            tool_name=d["tool_name"],
            tool_input=dict(d.get("tool_input") or {}),
            called_at=d["called_at"],
            event_id=d.get("event_id"),
            tool_output=dict(raw_output) if raw_output is not None else None,
            duration_ms=d.get("duration_ms"),
        )


@dataclass(frozen=True)
class AgentJobApproval:
    """Human approval request created when a job enters ``waiting_for_approval``.

    ``approved`` is tri-state: ``None`` = pending, ``True`` = approved,
    ``False`` = rejected.
    """

    approval_id: str
    agent_job_id: str
    requested_at: str
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_at: str | None = None
    notes: str | None = None
    approved: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "agent_job_id": self.agent_job_id,
            "requested_at": self.requested_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejected_at": self.rejected_at,
            "notes": self.notes,
            "approved": self.approved,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentJobApproval:
        raw_approved = d.get("approved")
        return cls(
            approval_id=d["approval_id"],
            agent_job_id=d["agent_job_id"],
            requested_at=d["requested_at"],
            approved_by=d.get("approved_by"),
            approved_at=d.get("approved_at"),
            rejected_at=d.get("rejected_at"),
            notes=d.get("notes"),
            approved=bool(raw_approved) if raw_approved is not None else None,
        )


@dataclass(frozen=True)
class AgentJobAcceptance:
    """Formal acceptance record binding a set of artifacts to an approver.

    ``artifact_ids`` lists every :class:`AgentJobArtifact` accepted in this
    operation; the corresponding ``AgentJobArtifact.accepted`` flag is also
    flipped to ``True`` by the service layer (P4.2).
    """

    acceptance_id: str
    agent_job_id: str
    accepted_at: str
    artifact_ids: list[str]
    accepted_by: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "acceptance_id": self.acceptance_id,
            "agent_job_id": self.agent_job_id,
            "accepted_at": self.accepted_at,
            "artifact_ids": list(self.artifact_ids),
            "accepted_by": self.accepted_by,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentJobAcceptance:
        return cls(
            acceptance_id=d["acceptance_id"],
            agent_job_id=d["agent_job_id"],
            accepted_at=d["accepted_at"],
            artifact_ids=list(d.get("artifact_ids") or []),
            accepted_by=d.get("accepted_by"),
            notes=d.get("notes"),
        )


# ---------------------------------------------------------------------------
# State-machine transition table
# ---------------------------------------------------------------------------

#: Maps each ``AgentJobStatus`` to the set of statuses it may legally
#: transition into.  Terminal states map to the empty set.
LEGAL_TRANSITIONS: dict[AgentJobStatus, set[AgentJobStatus]] = {
    AgentJobStatus.queued: {
        AgentJobStatus.running,
        AgentJobStatus.canceled,
    },
    AgentJobStatus.running: {
        AgentJobStatus.waiting_for_approval,
        AgentJobStatus.failed,
        AgentJobStatus.canceled,
        AgentJobStatus.completed,
    },
    AgentJobStatus.waiting_for_approval: {
        AgentJobStatus.running,
        AgentJobStatus.failed,
        AgentJobStatus.canceled,
    },
    AgentJobStatus.failed: set(),
    AgentJobStatus.canceled: set(),
    AgentJobStatus.completed: {
        AgentJobStatus.accepted,
    },
    AgentJobStatus.accepted: set(),
}


def validate_transition(
    from_status: AgentJobStatus,
    to_status: AgentJobStatus,
) -> None:
    """Assert that transitioning *from_status* → *to_status* is legal.

    Raises:
        ValueError: if the transition is not in :data:`LEGAL_TRANSITIONS`.

    Returns ``None`` on success (callers may ignore the return value).
    """
    if to_status not in LEGAL_TRANSITIONS[from_status]:
        raise ValueError(
            f"Illegal AgentJob transition: {from_status} → {to_status}"
        )


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def validate_agent_job(d: dict[str, Any]) -> list[str]:
    """Validate *d* as an agent-job record; return a list of error strings.

    An empty return value means the record is valid.  The function checks:
    - all required fields are present and non-``None``/non-empty
    - ``status`` is a known ``AgentJobStatus`` value
    - ``policy_snapshot`` contains the mandatory ``allowed_tools`` and
      ``data_scopes`` keys

    It does **not** raise — callers decide how to handle errors.
    """
    errors: list[str] = []

    # Required field presence
    for req in sorted(_REQUIRED_FIELDS):
        if req not in d or d[req] is None or d[req] == "":
            errors.append(f"missing required field: '{req}'")

    # Status validity (only if present — already caught above if absent)
    if "status" in d and d["status"] is not None:
        valid_statuses = {s.value for s in AgentJobStatus}
        if d["status"] not in valid_statuses:
            errors.append(
                f"invalid status '{d['status']}'; must be one of {sorted(valid_statuses)}"
            )

    # policy_snapshot structure
    ps = d.get("policy_snapshot")
    if isinstance(ps, dict):
        for mandatory_key in ("allowed_tools", "data_scopes"):
            if mandatory_key not in ps:
                errors.append(
                    f"policy_snapshot missing mandatory key: '{mandatory_key}'"
                )
    elif ps is not None:
        errors.append("policy_snapshot must be a dict")

    return errors
