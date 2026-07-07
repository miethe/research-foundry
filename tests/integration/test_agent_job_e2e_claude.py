"""Integration tests for the full claude_agent_sdk job lifecycle.

Gate #2 NOT approved — all tests use mock credentials.

These tests exercise the full P4.3 provider/adapter/service stack using
MockSDKClient and stub credential bytes (``b"test-mock-key-stub"``).  No real
API keys are read and no outbound network calls are made in any test.

Coverage:
- ClaudeAgentSDKAdapter: real-mode (mock client) and degraded paths.
- AgentJobService.build_job_brief + run_job_tool (allowed-tools policy).
- ClaudeAgentSDKProvider registration, job spawn, event streaming,
  artifact listing, artifact acceptance, and cancellation/cleanup.
- Full lifecycle: subprocess spawn → events.jsonl → artifact_*.json → accept.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import pytest

# Gate #2 NOT approved — all tests use mock credentials
# (real API key reads and live provider network calls are NOT permitted here)

from research_foundry.adapters.claude_agent_sdk import (
    ClaudeAgentSDKAdapter,
    MockSDKClient,
)
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.agent_providers.claude_agent_sdk_provider import (
    ClaudeAgentSDKProvider,
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
        "provider": "claude_agent_sdk",
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
# Test 1 — provider registry
# ---------------------------------------------------------------------------


def test_provider_registered() -> None:
    """ClaudeAgentSDKProvider is in the registry after package import."""
    # Import triggers module-level register() call.
    from research_foundry.services.agent_providers import get_provider  # noqa: PLC0415

    provider = get_provider("claude_agent_sdk")
    assert provider is not None, (
        "ClaudeAgentSDKProvider not found in registry; "
        "check that claude_agent_sdk_provider.py is imported."
    )
    assert provider.id == "claude_agent_sdk"


# ---------------------------------------------------------------------------
# Test 2 — adapter real-mode path (mock client injected)
# ---------------------------------------------------------------------------


def test_adapter_real_mode_with_mock_client() -> None:
    """Adapter runs in real mode when a MockSDKClient is injected."""
    adapter = ClaudeAgentSDKAdapter(sdk_client=MockSDKClient())
    result = adapter.run(
        {
            "intent": "test intent",
            "job_id": "j1",
            "policy_snapshot": {"allowed_tools": ["search"], "data_scopes": []},
        }
    )
    assert result.degraded is False, "Expected real-mode result (degraded=False)"
    assert "sdk_result" in result.artifacts, (
        f"'sdk_result' key missing from artifacts; got: {list(result.artifacts)}"
    )


# ---------------------------------------------------------------------------
# Test 3 — adapter degraded path (no client, SDK not installed)
# ---------------------------------------------------------------------------


def test_adapter_degraded_without_client() -> None:
    """Adapter falls back to degraded stub when no client and SDK absent."""
    # claude_agent_sdk is not a real installable package in the test venv;
    # available() therefore returns False unless an sdk_client is injected.
    adapter = ClaudeAgentSDKAdapter()
    result = adapter.run({})
    assert result.degraded is True, (
        "Expected degraded=True when sdk_client is None and SDK not installed"
    )


# ---------------------------------------------------------------------------
# Test 4 — build_job_brief tool descriptors
# ---------------------------------------------------------------------------


def test_job_brief_contains_tool_descriptors(tmp_path: Path) -> None:
    """build_job_brief populates 'tools' with descriptors for each allowed tool."""
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    job = make_agent_job(
        tmp_path,
        policy_snapshot={"allowed_tools": ["search", "source_card"], "data_scopes": []},
    )
    brief = svc.build_job_brief(job)

    assert "tools" in brief, f"'tools' key missing from job brief; got keys: {list(brief)}"
    tool_names = {t["name"] for t in brief["tools"]}
    assert "search" in tool_names, f"'search' not in tool names: {tool_names}"
    assert "source_card" in tool_names, f"'source_card' not in tool names: {tool_names}"


# ---------------------------------------------------------------------------
# Test 5 — run_job_tool disallowed tool policy enforcement
# ---------------------------------------------------------------------------


def test_run_job_tool_disallowed_raises(tmp_path: Path) -> None:
    """run_job_tool raises ValueError when the tool is not in allowed_tools."""
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    job = make_agent_job(
        tmp_path,
        policy_snapshot={"allowed_tools": ["search"], "data_scopes": []},
    )
    with pytest.raises(ValueError, match="not in the job's allowed_tools"):
        svc.run_job_tool("source_card", {}, job)


# ---------------------------------------------------------------------------
# Test 6 — spawn_job registers in service registry
# ---------------------------------------------------------------------------


def test_spawn_job_registers_in_service(tmp_path: Path) -> None:
    """spawn_job with command_override populates the service registry."""
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    job = make_agent_job(tmp_path)
    job_id = job.agent_job_id

    # Use a no-op command to avoid attempting the real (non-existent) runner.
    proc = svc.spawn_job(
        job,
        b"test-mock-key-stub",
        command_override=[sys.executable, "-c", "import time; time.sleep(0)"],
    )

    try:
        assert job_id in svc._registry, "job_id not found in service registry after spawn"
        registered_proc, cred_path = svc._registry[job_id]
        assert registered_proc is proc
        assert cred_path.exists(), "credential temp file does not exist right after spawn"

        proc.wait(timeout=5)
    finally:
        svc.cleanup_job(job_id)

    assert job_id not in svc._registry, "job_id still in registry after cleanup"


# ---------------------------------------------------------------------------
# Test 7 — full lifecycle: queued → running event → artifact → acceptance
# ---------------------------------------------------------------------------


def test_full_lifecycle_queued_to_staged(tmp_path: Path) -> None:
    """End-to-end: spawn child that writes events + artifact, then stream/accept.

    Steps:
      a. Spawn child subprocess via command_override (Python script in tmp_path).
      b. Child writes one JSON event to events.jsonl and one artifact_art1.json.
      c. Wait for child to exit (≤5 s timeout).
      d. stream_events → at least one event.
      e. list_artifacts → at least one artifact.
      f. accept_artifacts(["art1"]) → no exception.
      g. acceptance.json exists on disk.
    """
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    provider = ClaudeAgentSDKProvider(
        job_service=svc,
        credential_bytes_factory=lambda: b"test-mock-key-stub",
    )

    job = make_agent_job(tmp_path)
    job_id = job.agent_job_id
    job_dir = svc._paths.agent_job_dir(job_id)

    # Write the child helper script to a temp file so the command stays clean.
    child_script = tmp_path / "child_worker.py"
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
        b"test-mock-key-stub",
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
# Test 8 — cancel_job cleans up credential file
# ---------------------------------------------------------------------------


def test_cancel_job_cleans_up_cred_file(tmp_path: Path) -> None:
    """cancel_job terminates the subprocess and unlinks the credential file."""
    svc = AgentJobService(paths=FoundryPaths(root=tmp_path))
    provider = ClaudeAgentSDKProvider(
        job_service=svc,
        credential_bytes_factory=lambda: b"test-mock-key-stub",
    )

    job = make_agent_job(tmp_path)
    job_id = job.agent_job_id

    # Spawn a long-running subprocess so cancel_job has something to terminate.
    svc.spawn_job(
        job,
        b"test-mock-key-stub",
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
