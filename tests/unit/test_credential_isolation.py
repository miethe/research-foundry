"""Tests for AgentJobService — SEC-2.1 (subprocess spawn model) and
SEC-2.2 (credential temp-file delivery + crash-safe cleanup).

Acceptance criteria covered:
* AC-5.1 (SEC-2.1): spawned child process does not inherit parent env vars.
* AC-5.2 (SEC-2.2): credential temp file is created with mode 0600.
* AC-5.3 (SEC-2.2): credential file is unlinked by cleanup_job in all exit
  scenarios (clean terminate, SIGKILL crash).
* Redaction gate: persist_event/persist_artifact call redact_payload so no
  raw secret appears on disk.

All credentials in this module are **synthetic** and never associated with
any real service.  The synthetic key ``SYNTHETIC_CRED`` is purposely
formatted WITHOUT an inner hyphen so it matches the built-in pattern
``r"sk-[A-Za-z0-9]{20,}"`` in governance.py.  The format
``sk-test-000...`` (with a second hyphen) would NOT match that pattern; a
comment on SYNTHETIC_CRED explains the rationale.
"""

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import sys
import unittest.mock as mock
from pathlib import Path
from typing import Generator

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import (
    AgentJobService,
    InProcessProviderError,
)

# ---------------------------------------------------------------------------
# Synthetic credential
# ---------------------------------------------------------------------------

# No inner hyphen so this matches r"sk-[A-Za-z0-9]{20,}" in governance.py.
# The form "sk-test-0000..." (with a second hyphen) would break that regex.
SYNTHETIC_CRED = b"sk-test0000000000000000000000000000000000000000000000"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    job_id: str = "test-job-001",
    provider: str = "sdk_runner",
) -> AgentJob:
    """Build a minimal but valid AgentJob for testing."""
    return AgentJob(
        agent_job_id=job_id,
        project_id="proj-001",
        workspace_id=None,
        created_by=None,
        provider=provider,
        model_profile="sonnet",
        request_kind="research",
        input_claim_ids=[],
        input_source_ids=[],
        input_report_id=None,
        policy_snapshot={"allowed_tools": [], "data_scopes": []},
        budget_usd=None,
        max_runtime_minutes=None,
        status=AgentJobStatus.queued,
        created_at="2026-07-07T00:00:00Z",
        updated_at="2026-07-07T00:00:00Z",
        started_at=None,
        completed_at=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> FoundryPaths:
    return FoundryPaths(root=tmp_path)


@pytest.fixture
def service(tmp_workspace: FoundryPaths) -> Generator[AgentJobService, None, None]:
    svc = AgentJobService(paths=tmp_workspace)
    yield svc
    # Best-effort teardown: cleanup any jobs that tests didn't clean up.
    for job_id in list(svc._registry):
        svc.cleanup_job(job_id)


# ---------------------------------------------------------------------------
# SEC-2.1: Subprocess spawn model — env isolation
# ---------------------------------------------------------------------------


def test_spawn_does_not_inherit_environ(service: AgentJobService) -> None:
    """Spawned child must not inherit any parent shell env vars (SEC-2.1 FR-11).

    A quick-exit child command prints its own ``os.environ`` keys as JSON;
    we assert that common host env vars (HOME, PATH, ANTHROPIC_API_KEY,
    OPENAI_API_KEY, USER, SHELL) are all absent.
    """
    child_cmd = [
        sys.executable,
        "-c",
        "import os, json, sys; print(json.dumps(list(os.environ.keys()))); sys.exit(0)",
    ]
    job = _make_job(job_id="env-isolation-job")
    proc = service.spawn_job(job, SYNTHETIC_CRED, command_override=child_cmd)
    stdout, _ = proc.communicate(timeout=15)

    env_keys = json.loads(stdout.decode())

    forbidden = {
        "HOME",
        "PATH",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "USER",
        "SHELL",
        "VIRTUAL_ENV",
        "PYTHONPATH",
    }
    present = forbidden & set(env_keys)
    assert not present, f"Child inherited forbidden env vars: {present}"

    service.cleanup_job(job.agent_job_id)


def test_in_process_providers_raise(service: AgentJobService) -> None:
    """Static in-process adapters must raise InProcessProviderError when spawned."""
    in_process = (
        "gpt_researcher",
        "paperqa2",
        "litellm_router",
        "opencode",
        "arc_council",
        "notebooklm",
    )
    for provider in in_process:
        job = _make_job(job_id=f"inprocess-{provider}", provider=provider)
        with pytest.raises(InProcessProviderError, match=provider):
            service.spawn_job(job, SYNTHETIC_CRED)


# ---------------------------------------------------------------------------
# SEC-2.2 / AC-5.2: Credential temp-file mode 0600
# ---------------------------------------------------------------------------


def test_cred_file_mode_0600(service: AgentJobService) -> None:
    """Credential temp file must have mode 0600 at spawn time (AC-5.2)."""
    child_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    job = _make_job(job_id="cred-mode-job")
    service.spawn_job(job, SYNTHETIC_CRED, command_override=child_cmd)

    _, cred_path = service._registry[job.agent_job_id]
    file_mode = stat.S_IMODE(cred_path.stat().st_mode)
    assert file_mode == 0o600, (
        f"Expected cred file mode 0600, got {oct(file_mode)}"
    )

    service.cleanup_job(job.agent_job_id)


# ---------------------------------------------------------------------------
# SEC-2.2 / AC-5.3: Credential file cleanup
# ---------------------------------------------------------------------------


def test_cred_file_cleaned_up_on_terminate(service: AgentJobService) -> None:
    """cleanup_job must unlink the credential file after graceful terminate (AC-5.3)."""
    child_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    job = _make_job(job_id="cred-cleanup-terminate-job")
    service.spawn_job(job, SYNTHETIC_CRED, command_override=child_cmd)

    _, cred_path = service._registry[job.agent_job_id]
    assert cred_path.exists(), "Credential file must exist before cleanup"

    service.cleanup_job(job.agent_job_id)
    assert not cred_path.exists(), (
        "Credential file must be deleted after cleanup_job"
    )


def test_cred_file_cleaned_up_on_crash(service: AgentJobService) -> None:
    """cleanup_job must unlink the credential file even after child SIGKILL (AC-5.3)."""
    child_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    job = _make_job(job_id="cred-cleanup-crash-job")
    proc = service.spawn_job(job, SYNTHETIC_CRED, command_override=child_cmd)

    _, cred_path = service._registry[job.agent_job_id]

    # Simulate a child crash by sending SIGKILL directly.
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()

    # The parent cleanup must still unlink the cred file.
    service.cleanup_job(job.agent_job_id)
    assert not cred_path.exists(), (
        "Credential file must be deleted after crash + cleanup_job"
    )


# ---------------------------------------------------------------------------
# SEC-2.2: Credential must NOT appear in child env= dict
# ---------------------------------------------------------------------------


def test_no_env_var_credential(service: AgentJobService) -> None:
    """spawn_job must pass env={} and must not embed credential in env (SEC-2.2).

    We intercept the :class:`subprocess.Popen` call with ``wraps=`` so the
    real process still spawns, and then inspect the ``env`` kwarg to verify:

    * ``env`` is an empty dict ``{}``.
    * The raw credential bytes do not appear as any value.
    * No key is suspiciously named ``cred`` or similar.
    """
    child_cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    job = _make_job(job_id="no-env-cred-job")

    with mock.patch("subprocess.Popen", wraps=subprocess.Popen) as mock_popen:
        service.spawn_job(job, SYNTHETIC_CRED, command_override=child_cmd)
        service.cleanup_job(job.agent_job_id)

    assert mock_popen.call_count == 1, "subprocess.Popen should be called once"
    call_kwargs = mock_popen.call_args.kwargs
    child_env: dict = call_kwargs.get("env") or {}

    # Primary assertion: env must be empty.
    assert child_env == {}, f"Child env should be empty {{}}, got {child_env}"

    # Defensive assertions: even if env is somehow non-empty, no raw credential.
    cred_str = SYNTHETIC_CRED.decode()
    for k, v in child_env.items():
        assert cred_str not in str(v), (
            f"Raw credential found in child env[{k!r}]"
        )
        assert "cred" not in k.lower(), (
            f"Suspiciously named key {k!r} found in child env"
        )


# ---------------------------------------------------------------------------
# Redaction gate: persist_event and persist_artifact
# ---------------------------------------------------------------------------


def test_persist_event_redacts_secrets(
    service: AgentJobService, tmp_path: Path
) -> None:
    """persist_event must call redact_payload so raw secrets never hit disk.

    We embed the synthetic key in a nested payload field and assert:
    * The raw key string is NOT present in the written file.
    * The string ``'[REDACTED]'`` IS present in the written file.
    """
    job_id = "redact-event-job"
    synthetic_key = SYNTHETIC_CRED.decode()
    event = {
        "event_id": "evt-001",
        "agent_job_id": job_id,
        "stage": "plan",
        "timestamp": "2026-07-07T00:00:00Z",
        "payload": {
            "api_key": synthetic_key,
            "message": "testing redaction",
        },
        "sequence": 1,
    }
    events_file = service.persist_event(job_id, event)

    content = events_file.read_text(encoding="utf-8")
    assert synthetic_key not in content, (
        "Raw synthetic key must not appear in the persisted event file"
    )
    assert "[REDACTED]" in content, (
        "Persisted event file must contain '[REDACTED]' placeholder"
    )


def test_persist_artifact_redacts_secrets(service: AgentJobService) -> None:
    """persist_artifact must call redact_payload so raw secrets never hit disk."""
    job_id = "redact-artifact-job"
    synthetic_key = SYNTHETIC_CRED.decode()
    artifact = {
        "artifact_id": "art-001",
        "agent_job_id": job_id,
        "artifact_kind": "source_card",
        "created_at": "2026-07-07T00:00:00Z",
        "meta": {"token": synthetic_key},
    }
    artifact_file = service.persist_artifact(job_id, artifact)

    content = artifact_file.read_text(encoding="utf-8")
    assert synthetic_key not in content, (
        "Raw synthetic key must not appear in the persisted artifact file"
    )
    assert "[REDACTED]" in content, (
        "Persisted artifact file must contain '[REDACTED]' placeholder"
    )


# ---------------------------------------------------------------------------
# FIX 1: _safe_write_json always calls redact_payload
# ---------------------------------------------------------------------------


def test_safe_write_json_calls_redact_payload(
    service: AgentJobService, tmp_path: Path
) -> None:
    """_safe_write_json must call redact_payload before writing any data.

    Mocks redact_payload and asserts it is called when _safe_write_json
    writes a dict.  This test fails if someone writes around the chokepoint.
    """
    dest = tmp_path / "test_output.json"
    payload = {"key": "value", "nested": {"x": 1}}

    with mock.patch(
        "research_foundry.services.agent_job_service.redact_payload",
        wraps=lambda obj, **_kw: obj,
    ) as mock_redact:
        service._safe_write_json(payload, dest, append=False)

    mock_redact.assert_called_once()
    called_with = mock_redact.call_args.args[0]
    assert called_with == payload, (
        "_safe_write_json must pass the original data to redact_payload"
    )
    assert dest.exists(), "_safe_write_json must write the output file"


# ---------------------------------------------------------------------------
# FIX 2: Path traversal rejected on artifact_id
# ---------------------------------------------------------------------------


def test_persist_artifact_rejects_path_traversal(service: AgentJobService) -> None:
    """persist_artifact must raise ValueError for artifact_id containing '..'."""
    artifact = {
        "artifact_id": "../../evil",
        "agent_job_id": "safe-job",
        "artifact_kind": "source_card",
    }
    with pytest.raises(ValueError, match="artifact_id"):
        service.persist_artifact("safe-job", artifact)


def test_persist_event_rejects_path_traversal_job_id(
    service: AgentJobService,
) -> None:
    """persist_event must raise ValueError for job_id containing path traversal."""
    with pytest.raises(ValueError, match="job_id"):
        service.persist_event("../../etc", {"event_id": "evt-001"})
