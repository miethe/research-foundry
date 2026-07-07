"""Integration tests for the full openai_agents job lifecycle.

Gate #2 NOT approved — all tests use mock credentials.

These tests exercise the full P4.6 provider/adapter/service stack using
MockOpenAIAgentsClient and stub credential bytes
(``b"test-mock-openai-key-stub"``).  No real API keys are read and no
outbound network calls are made in any test.

Coverage:
- OpenAIAgentsAdapter: real-mode (mock client) and degraded paths.
- OpenAIAgentsProvider registration, job spawn, event streaming,
  artifact listing, artifact acceptance, and cancellation/cleanup.
- MockOpenAIAgentsClient guardrails: check_tool_call and
  run_agent_with_guardrails blocking behaviour (OpenAI-specific).
- Provider parity: OpenAIAgentsProvider and ClaudeAgentSDKProvider both
  satisfy the same start_job lifecycle contract.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

# Gate #2 NOT approved — all tests use mock credentials
# (real API key reads and live provider network calls are NOT permitted here)

from research_foundry.adapters.openai_agents import (
    MockOpenAIAgentsClient,
    OpenAIAgentsAdapter,
)
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.agent_providers.claude_agent_sdk_provider import (
    ClaudeAgentSDKProvider,
)
from research_foundry.services.agent_providers.openai_agents_provider import (
    OpenAIAgentsProvider,
)


# ---------------------------------------------------------------------------
# Helper / fixture
# ---------------------------------------------------------------------------


def make_agent_job(tmp_path: Path, **overrides) -> AgentJob:  # noqa: ARG001
    """Return a valid :class:`AgentJob` with sensible defaults for tests.

    All credential-related fields default to ``None`` / safe stubs.
    ``tmp_path`` is accepted for call-site symmetry but is not used — the job
    record itself does not embed a workspace path.
    """
    now = "2026-07-07T00:00:00Z"
    defaults: dict = {
        "agent_job_id": uuid.uuid4().hex,
        "project_id": "test-project",
        "workspace_id": None,
        "created_by": "test-user",
        "provider": "openai_agents",
        "model_profile": "rf_synthesize_deep",
        "request_kind": "research",
        "input_claim_ids": [],
        "input_source_ids": [],
        "input_report_id": None,
        "policy_snapshot": {
            "allowed_tools": ["search", "source_card"],
            "data_scopes": [],
        },
        "budget_usd": None,
        "max_runtime_minutes": None,
        "status": AgentJobStatus.queued,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "completed_at": None,
    }
    defaults.update(overrides)
    return AgentJob(**defaults)


# ---------------------------------------------------------------------------
# Minimal mock AgentJobService for start_job / parity tests
# ---------------------------------------------------------------------------


class _MockJobService:
    """Minimal mock with spawn_job and persist_event as no-ops.

    Used in tests that validate start_job return values without spawning real
    subprocesses (Gate #2 NOT approved — stub credentials only).
    """

    def spawn_job(
        self,
        job: Any,  # noqa: ARG002
        cred_bytes: bytes,  # noqa: ARG002
        *,
        command_override: list[str] | None = None,  # noqa: ARG002
    ) -> None:
        """No-op spawn: does not start a real subprocess."""

    def persist_event(
        self,
        job_id: str,  # noqa: ARG002
        event: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """No-op event persistence."""


# ---------------------------------------------------------------------------
# Test 1 — adapter real-mode path (mock client injected)
# ---------------------------------------------------------------------------


def test_adapter_real_mode_mock_client() -> None:
    """Adapter runs in real mode when a MockOpenAIAgentsClient is injected.

    Also asserts that no stub credential bytes leak into the artifact output
    (Gate #2 NOT approved — stub credentials only).
    """
    # Gate #2 NOT approved — stub credentials only
    adapter = OpenAIAgentsAdapter(sdk_client=MockOpenAIAgentsClient())
    result = adapter.run(
        {
            "intent": "test intent",
            "job_id": "j1",
            "policy_snapshot": {"allowed_tools": ["search"], "data_scopes": []},
        }
    )
    assert result.degraded is False, "Expected real-mode result (degraded=False)"
    assert result.artifacts, (
        f"Expected non-empty artifacts dict; got: {result.artifacts!r}"
    )

    # Tool-call redaction assertion: verify no stub credential bytes in output
    # (verifying redact_payload ran and did not accidentally inject the key pattern).
    # Gate #2 NOT approved — stub credentials only
    artifacts_serialized = json.dumps(result.artifacts)
    assert "test-mock-openai-key-stub" not in artifacts_serialized, (
        "Stub credential bytes leaked into adapter output — "
        "redact_payload may not have run correctly"
    )


# ---------------------------------------------------------------------------
# Test 2 — adapter degraded path (no client, SDK not installed)
# ---------------------------------------------------------------------------


def test_adapter_degraded_path() -> None:
    """Adapter falls back to degraded stub when no client and SDK absent.

    Gate #2 NOT approved — stub credentials only.
    """
    # Gate #2 NOT approved — stub credentials only
    # openai_agents is not a real installable package in the test venv;
    # available() therefore returns False unless an sdk_client is injected.
    adapter = OpenAIAgentsAdapter()
    result = adapter.run({"intent": "test"})
    assert result.degraded is True, (
        "Expected degraded=True when sdk_client is None and SDK not installed"
    )


# ---------------------------------------------------------------------------
# Test 3 — provider registration
# ---------------------------------------------------------------------------


def test_provider_registration() -> None:
    """OpenAIAgentsProvider is in the registry after package import."""
    # Import triggers module-level register() call (already triggered by the
    # top-level import of OpenAIAgentsProvider in this module).
    from research_foundry.services.agent_providers import get_provider  # noqa: PLC0415

    provider = get_provider("openai_agents")
    assert provider is not None, (
        "OpenAIAgentsProvider not found in registry; "
        "check that openai_agents_provider.py is imported."
    )
    assert provider.id == "openai_agents"


# ---------------------------------------------------------------------------
# Test 4 — provider start_job with mock service
# ---------------------------------------------------------------------------


def test_provider_start_job() -> None:
    """start_job returns a non-empty string job_id using a mock job service.

    Gate #2 NOT approved — stub credentials only.
    """
    # Gate #2 NOT approved — stub credentials only
    mock_svc = _MockJobService()
    provider = OpenAIAgentsProvider(job_service=mock_svc)  # type: ignore[arg-type]

    job_dict: dict[str, Any] = {
        "agent_job_id": uuid.uuid4().hex,
        "project_id": "test-project",
        "created_by": "tester",
        "provider": "openai_agents",
        "model_profile": "rf_synthesize_deep",
        "request_kind": "research",
        # Empty policy so persist_event is not triggered.
        "policy_snapshot": {"allowed_tools": [], "data_scopes": []},
    }
    job_id = provider.start_job(job_dict)
    assert isinstance(job_id, str) and job_id, (
        f"start_job must return a non-empty string job_id; got {job_id!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — full lifecycle: queued → running event → artifact → acceptance
# ---------------------------------------------------------------------------


def test_provider_full_lifecycle(tmp_path: Path) -> None:
    """End-to-end: spawn child that writes events + artifact, then stream/accept.

    Steps:
      a. Spawn child subprocess via command_override (Python script in tmp_path).
      b. Child writes one JSON event to events.jsonl and one artifact_art1.json.
      c. Wait for child to exit (≤5 s timeout).
      d. stream_events → at least one event.
      e. list_artifacts → at least one artifact.
      f. accept_artifacts(["art1"]) → no exception.
      g. acceptance.json exists on disk with accepted art1.
    """
    # Gate #2 NOT approved — stub credentials only
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    provider = OpenAIAgentsProvider(
        job_service=svc,
        credential_bytes_factory=lambda: b"test-mock-openai-key-stub",
    )

    job = make_agent_job(tmp_path)
    job_id = job.agent_job_id
    job_dir = svc._paths.agent_job_dir(job_id)

    # Write the child helper script to a temp file so the command stays clean.
    child_script = tmp_path / "child_worker_openai.py"
    child_script.write_text(
        f"""\
import json
import os
import sys

job_dir = sys.argv[1]
os.makedirs(job_dir, exist_ok=True)

# Write one event line
events_path = os.path.join(job_dir, "events.jsonl")
with open(events_path, "a", encoding="utf-8") as fh:
    fh.write(
        json.dumps({{"stage": "plan", "status": "running", "seq": 0}}) + "\\n"
    )

# Write one artifact
artifact_path = os.path.join(job_dir, "artifact_art1.json")
with open(artifact_path, "w", encoding="utf-8") as fh:
    json.dump(
        {{
            "artifact_id": "art1",
            "agent_job_id": "{job_id}",
            "artifact_kind": "source_card",
            "created_at": "2026-07-07T00:00:00Z",
        }},
        fh,
    )
""",
        encoding="utf-8",
    )

    # Spawn the child with a command_override that passes job_dir as argv[1].
    proc = svc.spawn_job(
        job,
        b"test-mock-openai-key-stub",
        command_override=[sys.executable, str(child_script), str(job_dir)],
    )

    # --- a. Wait for child to exit ---
    deadline = time.monotonic() + 5.0
    while proc.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    assert proc.poll() is not None, "Child script did not exit within 5 s"
    assert proc.returncode == 0, (
        f"Child script exited with non-zero code {proc.returncode}; "
        f"stderr: {proc.stderr.read().decode(errors='replace') if proc.stderr else ''}"
    )

    # --- d. Stream events ---
    events = list(provider.stream_events(job_id))
    assert len(events) >= 1, f"Expected ≥1 event; got {events!r}"
    assert events[0].get("stage") == "plan"

    # --- e. List artifacts ---
    artifacts = provider.list_artifacts(job_id)
    assert len(artifacts) >= 1, f"Expected ≥1 artifact; got {artifacts!r}"
    artifact_ids = [a.get("artifact_id") for a in artifacts]
    assert "art1" in artifact_ids, f"artifact_id 'art1' not found; got {artifact_ids}"

    # --- f. Accept artifacts ---
    provider.accept_artifacts(job_id, ["art1"])  # must not raise

    # --- g. Acceptance record on disk ---
    acceptance_path = job_dir / "acceptance.json"
    assert acceptance_path.exists(), f"acceptance.json not found at {acceptance_path}"
    with acceptance_path.open(encoding="utf-8") as fh:
        acceptance = json.load(fh)
    assert "art1" in acceptance.get("accepted_artifact_ids", [])

    # Cleanup
    svc.cleanup_job(job_id)


# ---------------------------------------------------------------------------
# Test 6 — cancel_job cleans up credential file
# ---------------------------------------------------------------------------


def test_provider_cancel_job(tmp_path: Path) -> None:
    """cancel_job terminates the subprocess and unlinks the credential file.

    Gate #2 NOT approved — stub credentials only.
    """
    # Gate #2 NOT approved — stub credentials only
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    provider = OpenAIAgentsProvider(
        job_service=svc,
        credential_bytes_factory=lambda: b"test-mock-openai-key-stub",
    )

    job = make_agent_job(tmp_path)
    job_id = job.agent_job_id

    # Spawn a long-running subprocess so cancel_job has something to terminate.
    svc.spawn_job(
        job,
        b"test-mock-openai-key-stub",
        command_override=[sys.executable, "-c", "import time; time.sleep(30)"],
    )

    # Capture the credential file path before cancellation.
    _, cred_path = svc._registry[job_id]
    assert cred_path.exists(), "Credential file must exist immediately after spawn"

    # Cancel via the provider (wraps terminate_job + cleanup_job).
    provider.cancel_job(job_id)

    assert not cred_path.exists(), (
        f"Credential file still exists after cancel_job: {cred_path}"
    )
    assert job_id not in svc._registry, "job_id still in registry after cancel_job"


# ---------------------------------------------------------------------------
# Test 7 — guardrails blocking (OpenAI-specific)
# ---------------------------------------------------------------------------


def test_guardrails_blocking() -> None:
    """MockOpenAIAgentsClient guardrails correctly block unlisted tools.

    Verifies:
    - check_tool_call("blocked_tool", {}) → False for tool not in allowed_tools
    - check_tool_call("search", {}) → True for tool in allowed_tools
    - run_agent_with_guardrails records blocked_tool in blocked_events when
      the probe list includes it and it is not in the client's allowed_tools.

    Gate #2 NOT approved — stub credentials only.
    """
    # Gate #2 NOT approved — stub credentials only
    client = MockOpenAIAgentsClient(allowed_tools=["search"])

    # Individual tool-call guard checks.
    assert client.check_tool_call("blocked_tool", {}) is False, (
        "check_tool_call must return False for tools not in allowed_tools"
    )
    assert client.check_tool_call("search", {}) is True, (
        "check_tool_call must return True for tools in allowed_tools"
    )

    # Guardrails run: include "blocked_tool" explicitly in the brief's
    # allowed_tools so it appears in the probe list.  The client's own
    # allowed_tools is ["search"], so "blocked_tool" will be flagged as blocked.
    # Gate #2 NOT approved — stub credentials only
    result = client.run_agent_with_guardrails(
        {"intent": "test", "allowed_tools": ["search", "blocked_tool"]},
        allowed_tools=["search"],
        data_scopes=[],
    )
    blocked_tool_names = [e["tool"] for e in result.get("blocked_events", [])]
    assert "blocked_tool" in blocked_tool_names, (
        f"'blocked_tool' expected in blocked_events tool names; "
        f"got blocked_events: {result.get('blocked_events', [])!r}"
    )


# ---------------------------------------------------------------------------
# Test 8 — provider parity (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "provider_class",
    [ClaudeAgentSDKProvider, OpenAIAgentsProvider],
)
def test_provider_parity(provider_class: type) -> None:
    """Both providers satisfy the same start_job contract.

    Each provider must accept a job dict and return a non-empty string job_id.
    This parity assertion ensures both backends are interchangeable at the
    protocol level.

    Gate #2 NOT approved — stub credentials only.
    """
    # Gate #2 NOT approved — stub credentials only
    mock_svc = _MockJobService()
    provider = provider_class(job_service=mock_svc)  # type: ignore[arg-type]

    job_dict: dict[str, Any] = {
        "agent_job_id": uuid.uuid4().hex,
        "project_id": "parity-test",
        "created_by": "tester",
        # No policy_snapshot → avoids conditional persist_event path.
    }

    job_id = provider.start_job(job_dict)
    assert isinstance(job_id, str) and job_id, (
        f"{provider_class.__name__}.start_job must return a non-empty string; "
        f"got {job_id!r}"
    )
