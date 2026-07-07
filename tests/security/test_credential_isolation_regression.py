"""Credential-firewall regression suite — AC-5.1 through AC-5.5 (P4 Phase-7 VAL-7.1).

This module verifies the five credential-firewall acceptance criteria from the
Public Multi-User P4 implementation plan (PRD: public-multiuser-p4-agents-v1.md).

Acceptance criteria covered:
    AC-5.1  Secret-scan regression: no raw credential passes through
            redact_payload even in deeply nested payloads.
    AC-5.2  Crash-safety regression: credential temp file is cleaned up
            even after a SIGKILL / crash scenario.
    AC-5.3  Code-path audit: spawn_job enforces env={} (no parent env
            inheritance) and embeds no credential bytes in the child argv.
    AC-5.4  Fingerprint construction: make_key_fingerprint returns a
            12-hex-char, deterministic, non-reversible value.
    AC-5.5  Governance-pattern non-match: the fingerprint itself does NOT
            trigger scan_secrets (the fingerprint is not a secret).

=============================================================================
GATE #3 DEFERRAL NOTICE
=============================================================================
Mode-D Gate #3 requires verifying redaction against a REAL run-trace file
produced with a live provider credential (Gate #2 approval required first).

This test suite operates entirely with SYNTHETIC credentials (format below).
A placeholder test ``test_DEFERRED_real_run_trace_redaction`` is marked
``pytest.mark.skip`` and documents the missing Gate #2 precondition.

Real-key testing MUST NOT proceed until Gate #2 (live provider approval) is
obtained from the project owner.
=============================================================================

All credentials in this module are **synthetic** and clearly non-real.
``SYNTHETIC_CRED`` uses the form ``sk-test0000...`` (no inner hyphen) so it
matches the built-in pattern ``r"sk-[A-Za-z0-9]{20,}"`` in governance.py.
The form ``sk-test-0000...`` (with a second hyphen after ``test``) would NOT
match that regex because the hyphen terminates the alphanumeric run at only
4 chars — a comment on SYNTHETIC_CRED explains the rationale.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import unittest.mock as mock
from pathlib import Path
from typing import Any, Generator

import pytest

import yaml

from research_foundry.adapters.openai_agents import OpenAIAgentsAdapter
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import (
    AgentJobService,
    InProcessProviderError,
)
from research_foundry.services.governance import redact_payload, scan_secrets
from research_foundry.services.telemetry import make_key_fingerprint

# ---------------------------------------------------------------------------
# Synthetic credentials — clearly non-real (test prefix + zero fill)
# ---------------------------------------------------------------------------

# No inner hyphen: matches r"sk-[A-Za-z0-9]{20,}" in governance.py.
# The form "sk-test-0000..." (with a second hyphen) would break that regex
# because the hyphen terminates the alphanumeric run after only 4 chars.
SYNTHETIC_CRED = "sk-test0000000000000000000000000000000000000000000000"
SYNTHETIC_CRED_BYTES = SYNTHETIC_CRED.encode()

# Anthropic-pattern synthetic key; matches r"sk-ant-[A-Za-z0-9_\-]{20,}"
SYNTHETIC_ANT_CRED = "sk-ant-test00000000000000000000000000000000000000000000000000"

_HEX_RE = re.compile(r"^[0-9a-f]{12}$")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_job(
    job_id: str = "regression-job-001",
    provider: str = "sdk_runner",
) -> AgentJob:
    """Build a minimal but valid AgentJob for regression testing."""
    return AgentJob(
        agent_job_id=job_id,
        project_id="proj-regression-001",
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
    for job_id in list(svc._registry):
        svc.cleanup_job(job_id)


# ===========================================================================
# AC-5.1 — Secret-scan regression: redact_payload on deeply nested payloads
# ===========================================================================


def test_ac51_flat_string_redacted() -> None:
    """AC-5.1: A top-level credential string is replaced with '[REDACTED]'."""
    result = redact_payload(SYNTHETIC_CRED)
    assert result == "[REDACTED]", f"Expected '[REDACTED]', got {result!r}"
    hits = scan_secrets(json.dumps(result))
    assert hits == [], f"scan_secrets found hits in result: {hits}"


def test_ac51_deeply_nested_dict_redacted() -> None:
    """AC-5.1: Credential nested 4 levels deep inside a dict is fully replaced."""
    payload = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "api_key": SYNTHETIC_CRED,
                        "safe_value": "innocent string",
                    }
                }
            }
        }
    }
    result = redact_payload(payload)
    serialised = json.dumps(result)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Raw credential found in deeply nested redact_payload output: {hits}"
    )
    assert "[REDACTED]" in serialised, "Expected '[REDACTED]' marker in output"
    assert "innocent string" in serialised, "Safe value must survive redaction"


def test_ac51_list_of_dicts_with_multiple_credentials() -> None:
    """AC-5.1: Credentials inside a list-of-dicts are all individually redacted."""
    payload = [
        {"key": SYNTHETIC_CRED, "model": "claude"},
        {"key": SYNTHETIC_ANT_CRED, "model": "gpt"},
        {"safe": "no-cred-here"},
    ]
    result = redact_payload(payload)
    serialised = json.dumps(result)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Raw credentials found in list-of-dicts payload: {hits}"
    )
    assert serialised.count("[REDACTED]") == 2, (
        "Expected exactly 2 '[REDACTED]' markers (one per credential entry)"
    )
    assert "no-cred-here" in serialised, "Safe entry must survive redaction"


def test_ac51_mixed_list_dict_nesting() -> None:
    """AC-5.1: Mixed nesting (dict -> list -> dict) with credentials is fully redacted."""
    payload = {
        "agents": [
            {"name": "agent-alpha", "credentials": [SYNTHETIC_CRED]},
            {"name": "agent-beta", "safe_key": "safe-value-001"},
        ],
        "config": {"fallback": SYNTHETIC_ANT_CRED},
    }
    result = redact_payload(payload)
    serialised = json.dumps(result)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Raw credentials found in mixed nested payload: {hits}"
    )
    assert "safe-value-001" in serialised, "Safe value must survive redaction"


def test_ac51_scalars_pass_through_unchanged() -> None:
    """AC-5.1: Scalar non-string types (None, int, float, bool) pass through unchanged."""
    assert redact_payload(None) is None
    assert redact_payload(42) == 42
    assert redact_payload(3.14) == 3.14
    assert redact_payload(True) is True
    assert redact_payload(False) is False


def test_ac51_event_shaped_payload_sanitised() -> None:
    """AC-5.1: An agent-event-shaped dict with deeply nested credentials is sanitised."""
    event = {
        "event_id": "evt-regression-001",
        "agent_job_id": "job-regression-001",
        "stage": "plan",
        "timestamp": "2026-07-07T00:00:00Z",
        "payload": {
            "context": {
                "auth": {
                    "openai_key": SYNTHETIC_CRED,
                    "anthropic_key": SYNTHETIC_ANT_CRED,
                }
            },
            "note": "regression fixture — safe text",
        },
        "sequence": 1,
    }
    result = redact_payload(event)
    serialised = json.dumps(result)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Raw credentials found in sanitized event-shaped dict: {hits}"
    )
    assert serialised.count("[REDACTED]") == 2, (
        "Expected exactly 2 '[REDACTED]' markers for the two injected credentials"
    )
    assert "regression fixture" in serialised, "Safe text must survive redaction"


def test_redact_payload_dict_key_is_redacted() -> None:
    """AC-5.1: A dict key that matches a secret pattern is replaced with '[REDACTED]'."""
    # Key is a synthetic Anthropic-format credential; value is innocuous.
    result = redact_payload({SYNTHETIC_ANT_CRED: "value"})
    assert result == {"[REDACTED]": "value"}, (
        f"Expected dict key to be redacted, got: {result!r}"
    )
    # Also verify the raw key doesn't appear anywhere in the serialised output.
    serialised = json.dumps(result)
    assert SYNTHETIC_ANT_CRED not in serialised, (
        "Raw credential key must not appear in serialised output"
    )


def test_redact_payload_tuple_element_is_redacted() -> None:
    """AC-5.1: Tuple elements matching a secret pattern are replaced with '[REDACTED]'."""
    result = redact_payload((SYNTHETIC_CRED, "safe-value"))
    assert result == ("[REDACTED]", "safe-value"), (
        f"Expected first tuple element to be redacted, got: {result!r}"
    )
    assert isinstance(result, tuple), "redact_payload must return a tuple for tuple input"


def test_redact_payload_nested_tuple_in_dict() -> None:
    """AC-5.1: Tuple nested inside a dict value is walked and secret elements redacted."""
    result = redact_payload({"args": (SYNTHETIC_ANT_CRED, "safe-arg")})
    assert result == {"args": ("[REDACTED]", "safe-arg")}, (
        f"Expected tuple inside dict to have credential element redacted, got: {result!r}"
    )
    serialised = json.dumps(result)
    assert SYNTHETIC_ANT_CRED not in serialised, (
        "Raw credential must not appear in serialised output of nested tuple-in-dict"
    )


# ===========================================================================
# AC-5.2 — Crash-safety regression: temp file cleanup after SIGKILL
# ===========================================================================


def test_ac52_cred_file_cleaned_after_sigkill(service: AgentJobService) -> None:
    """AC-5.2: cleanup_job unlinks the credential temp file even after child SIGKILL."""
    child_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    job = _make_job(job_id="ac52-sigkill-regression")
    proc = service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)

    _, cred_path = service._registry[job.agent_job_id]
    assert cred_path.exists(), "Credential file must exist immediately after spawn"

    # Simulate a crash by sending SIGKILL and reaping the process.
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()

    # cleanup_job must still unlink the credential file despite the crash.
    service.cleanup_job(job.agent_job_id)
    assert not cred_path.exists(), (
        "Credential file must be deleted by cleanup_job even after child SIGKILL"
    )


def test_ac52_cred_file_cleaned_after_clean_exit(service: AgentJobService) -> None:
    """AC-5.2: cleanup_job unlinks the credential temp file after a clean process exit."""
    child_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    job = _make_job(job_id="ac52-clean-exit-regression")
    service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)

    _, cred_path = service._registry[job.agent_job_id]
    assert cred_path.exists(), "Credential file must exist before cleanup"

    service.cleanup_job(job.agent_job_id)
    assert not cred_path.exists(), (
        "Credential file must be deleted by cleanup_job after graceful terminate"
    )


def test_ac52_no_raw_cred_bytes_after_cleanup(service: AgentJobService) -> None:
    """AC-5.2: No raw credential bytes remain in the job's temp directory after cleanup."""
    child_cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    job = _make_job(job_id="ac52-filesystem-check")
    proc = service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)

    _, cred_path = service._registry[job.agent_job_id]
    cred_dir = cred_path.parent
    proc.wait()

    service.cleanup_job(job.agent_job_id)

    # After cleanup, no remaining file in the temp dir should contain the raw cred.
    if cred_dir.exists():
        for f in cred_dir.rglob("*"):
            if f.is_file():
                try:
                    content = f.read_bytes()
                    assert SYNTHETIC_CRED_BYTES not in content, (
                        f"Raw credential bytes found in {f} after cleanup"
                    )
                except OSError:
                    pass  # File may have been removed between the glob and read


# ===========================================================================
# AC-5.3 — Code-path audit: spawn_job enforces env={} and clean argv
# ===========================================================================


def test_ac53_spawn_job_passes_empty_env(service: AgentJobService) -> None:
    """AC-5.3: spawn_job passes env={} to subprocess.Popen (no parent env inheritance)."""
    child_cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    job = _make_job(job_id="ac53-empty-env-regression")

    with mock.patch("subprocess.Popen", wraps=subprocess.Popen) as mock_popen:
        service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)
        service.cleanup_job(job.agent_job_id)

    assert mock_popen.call_count == 1, "subprocess.Popen must be called exactly once"
    child_env: dict = mock_popen.call_args.kwargs.get("env") or {}
    assert child_env == {}, (
        f"spawn_job must pass env={{}} to Popen, got: {child_env}"
    )


def test_ac53_no_credential_in_child_env_values(service: AgentJobService) -> None:
    """AC-5.3: Raw credential bytes must not appear as any env var value passed to Popen."""
    child_cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    job = _make_job(job_id="ac53-no-cred-in-env")

    with mock.patch("subprocess.Popen", wraps=subprocess.Popen) as mock_popen:
        service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)
        service.cleanup_job(job.agent_job_id)

    child_env: dict = mock_popen.call_args.kwargs.get("env") or {}
    for k, v in child_env.items():
        assert SYNTHETIC_CRED not in str(v), (
            f"Raw credential found in child env[{k!r}] = {v!r}"
        )
        assert "cred" not in k.lower(), (
            f"Suspiciously named key {k!r} found in child env"
        )


def test_ac53_no_credential_in_child_argv(service: AgentJobService) -> None:
    """AC-5.3: The raw credential must not appear in any argv element passed to Popen."""
    child_cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    job = _make_job(job_id="ac53-no-cred-in-argv")

    with mock.patch("subprocess.Popen", wraps=subprocess.Popen) as mock_popen:
        service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)
        service.cleanup_job(job.agent_job_id)

    call_args = mock_popen.call_args
    argv = call_args.args[0] if call_args.args else call_args.kwargs.get("args", [])
    for arg in argv:
        assert SYNTHETIC_CRED not in str(arg), (
            f"Raw credential found in child argv element: {arg!r}"
        )


def test_ac53_child_does_not_inherit_parent_env(service: AgentJobService) -> None:
    """AC-5.3: Spawned child's runtime environment does not contain host env vars.

    A quick-exit child prints its own os.environ keys as JSON; the test asserts
    that HOME, PATH, ANTHROPIC_API_KEY, OPENAI_API_KEY, USER, SHELL, and
    VIRTUAL_ENV are all absent from the child's actual runtime environment.
    """
    child_cmd = [
        sys.executable,
        "-c",
        "import os, json, sys; print(json.dumps(list(os.environ.keys()))); sys.exit(0)",
    ]
    job = _make_job(job_id="ac53-env-isolation-regression")
    proc = service.spawn_job(job, SYNTHETIC_CRED_BYTES, command_override=child_cmd)
    stdout, _ = proc.communicate(timeout=15)
    service.cleanup_job(job.agent_job_id)

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
    leaked = forbidden & set(env_keys)
    assert not leaked, (
        f"Child process inherited forbidden env vars from parent: {leaked}"
    )


def test_ac53_in_process_providers_rejected_before_spawn(
    service: AgentJobService,
) -> None:
    """AC-5.3: In-process providers raise InProcessProviderError before any subprocess.

    This regression ensures the isolation gate fires immediately and no Popen call
    is made, so credentials are never even considered for passing to these providers.
    """
    in_process = ("gpt_researcher", "paperqa2", "litellm_router")
    for provider in in_process:
        job = _make_job(job_id=f"ac53-inprocess-{provider}", provider=provider)
        with mock.patch("subprocess.Popen") as mock_popen:
            with pytest.raises(InProcessProviderError, match=provider):
                service.spawn_job(job, SYNTHETIC_CRED_BYTES)
            mock_popen.assert_not_called()


# ===========================================================================
# AC-5.4 — Fingerprint construction: 12-hex-char, deterministic, non-reversible
# ===========================================================================


def test_ac54_fingerprint_is_12_hex_chars() -> None:
    """AC-5.4: make_key_fingerprint returns exactly 12 lowercase hex characters."""
    fp = make_key_fingerprint(SYNTHETIC_CRED)
    assert len(fp) == 12, f"Expected 12 chars, got {len(fp)}: {fp!r}"
    assert _HEX_RE.match(fp), f"Not 12 lowercase hex chars: {fp!r}"


def test_ac54_fingerprint_is_deterministic() -> None:
    """AC-5.4: Same key + same pepper always produces the same fingerprint."""
    fp1 = make_key_fingerprint(SYNTHETIC_CRED, pepper="regression-pepper")
    fp2 = make_key_fingerprint(SYNTHETIC_CRED, pepper="regression-pepper")
    assert fp1 == fp2, (
        f"make_key_fingerprint is not deterministic: {fp1!r} != {fp2!r}"
    )


def test_ac54_different_keys_produce_different_fingerprints() -> None:
    """AC-5.4: Different input keys must produce different fingerprints."""
    fp1 = make_key_fingerprint(SYNTHETIC_CRED)
    fp2 = make_key_fingerprint(SYNTHETIC_ANT_CRED)
    assert fp1 != fp2, (
        "Different input keys produced the same fingerprint (collision risk)"
    )


def test_ac54_fingerprint_is_not_raw_key_prefix() -> None:
    """AC-5.4: The fingerprint must not be a raw truncation/prefix of the input key."""
    fp = make_key_fingerprint(SYNTHETIC_CRED)
    assert fp != SYNTHETIC_CRED[:12], (
        "Fingerprint equals raw key prefix — HMAC was not applied correctly"
    )


def test_ac54_pepper_changes_fingerprint() -> None:
    """AC-5.4: Changing the pepper produces a different fingerprint (pepper is applied)."""
    fp1 = make_key_fingerprint(SYNTHETIC_CRED, pepper="pepper-A")
    fp2 = make_key_fingerprint(SYNTHETIC_CRED, pepper="pepper-B")
    assert fp1 != fp2, (
        "Different peppers produced identical fingerprints — pepper is being ignored"
    )


# ===========================================================================
# AC-5.5 — Governance-pattern non-match: fingerprint is not a secret
# ===========================================================================


def test_ac55_fingerprint_does_not_trigger_scan_secrets() -> None:
    """AC-5.5: The HMAC fingerprint must not match any governance secret pattern."""
    fp = make_key_fingerprint(SYNTHETIC_CRED)
    violations = scan_secrets(fp)
    assert violations == [], (
        f"Fingerprint {fp!r} triggered governance scan_secrets violations: {violations}"
    )


def test_ac55_fingerprint_not_redacted_by_redact_payload() -> None:
    """AC-5.5: redact_payload must leave a fingerprint value unchanged (not over-redact)."""
    fp = make_key_fingerprint(SYNTHETIC_CRED)
    payload = {"key_fingerprint": fp, "other": "safe-text"}
    result = redact_payload(payload)
    assert result["key_fingerprint"] == fp, (
        f"Fingerprint was incorrectly redacted to {result['key_fingerprint']!r}"
    )
    assert result["other"] == "safe-text"


def test_ac55_telemetry_record_with_fingerprint_passes_governance_scan() -> None:
    """AC-5.5: A telemetry record containing only a fingerprint (not a raw key) is clean."""
    fp = make_key_fingerprint(SYNTHETIC_CRED)
    telemetry_record = {
        "job_id": "job-telemetry-regression-001",
        "key_profile_used": "personal",
        "key_fingerprint": fp,
        "timestamp": "2026-07-07T00:00:00Z",
    }
    serialised = json.dumps(telemetry_record)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Governance scan found hits in telemetry record containing only a fingerprint: {hits}"
    )


def test_ac55_fingerprint_for_ant_key_does_not_trigger_scan_secrets() -> None:
    """AC-5.5: Fingerprint of an Anthropic-pattern synthetic key also passes governance."""
    fp = make_key_fingerprint(SYNTHETIC_ANT_CRED)
    assert _HEX_RE.match(fp), f"Fingerprint is not 12 lowercase hex chars: {fp!r}"
    violations = scan_secrets(fp)
    assert violations == [], (
        f"Fingerprint of ANT-pattern key triggered violations: {violations}"
    )


# ===========================================================================
# Codex HIGH #2 regression — custom governance.yaml secret_patterns applied
#   to agent-job output via redact_payload(config=...)
# ===========================================================================


def test_custom_governance_secret_patterns_applied_to_agent_job_output(
    tmp_path: Path,
) -> None:
    """Codex firewall finding #2 closed: custom governance.yaml secret_patterns
    are now applied to agent-job output via redact_payload(config=...).

    Setup
    -----
    A temporary governance.yaml is written that contains:
      - A custom token format ``INTERNAL-[A-Z0-9]{16}`` that is NOT in the
        built-in pattern list.
      - The standard Anthropic key pattern ``sk-ant-[A-Za-z0-9_\\-]{20,}``.

    Assertions (with config)
    ------------------------
    Both the custom token ``INTERNAL-ABCD1234EFGH5678`` and the built-in-format
    key ``SYNTHETIC_ANT_CRED`` must be absent from the redacted output.

    Contrasting assertion (config=None)
    ------------------------------------
    With ``config=None`` only the built-in patterns apply; the custom token
    ``INTERNAL-ABCD1234EFGH5678`` is NOT matched and therefore NOT redacted.
    This proves that the config-threaded path is what closes the gap —
    without it, custom governance patterns are silently ignored.
    """
    custom_token = "INTERNAL-ABCD1234EFGH5678"

    # Write a minimal governance.yaml into the tmp workspace.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    gov_data = {
        "secret_patterns": [
            r"INTERNAL-[A-Z0-9]{16}",
            r"sk-ant-[A-Za-z0-9_\-]{20,}",
        ]
    }
    (config_dir / "governance.yaml").write_text(
        yaml.dump(gov_data), encoding="utf-8"
    )

    from research_foundry.paths import FoundryPaths  # already imported above; re-alias for clarity
    cfg = FoundryConfig(paths=FoundryPaths(root=tmp_path))

    payload = {
        "agent_output": custom_token,
        "provider_key": SYNTHETIC_ANT_CRED,
        "safe_field": "harmless-value",
    }

    # --- With custom config: BOTH tokens must be redacted -------------------
    result_with_config = redact_payload(payload, config=cfg)
    serialised = json.dumps(result_with_config)

    assert custom_token not in serialised, (
        f"Custom token {custom_token!r} was NOT redacted when governance.yaml "
        "secret_patterns were active — Codex HIGH #2 is NOT closed"
    )
    assert SYNTHETIC_ANT_CRED not in serialised, (
        "Built-in-format Anthropic key was NOT redacted when governance.yaml "
        "secret_patterns were active"
    )
    assert result_with_config["safe_field"] == "harmless-value", (
        "Safe field must survive redaction"
    )

    # --- Contrasting: with config=None, built-ins only → custom token stays -
    result_no_config = redact_payload(payload, config=None)
    serialised_no_config = json.dumps(result_no_config)
    assert custom_token in serialised_no_config, (
        f"Custom token {custom_token!r} was unexpectedly redacted with "
        "config=None — it should only be caught via governance.yaml patterns"
    )


# ===========================================================================
# GATE #3 DEFERRED — Real run-trace redaction (requires Gate #2 approval)
# ===========================================================================


# ===========================================================================
# Codex R2 — #1  Tuple dict-key bypass
# ===========================================================================


def test_r2_tuple_dict_key_with_secret_is_redacted() -> None:
    """Codex R2 #1: A secret embedded inside a tuple dict-key is redacted.

    Previously _walk_redact only recursed dict keys when isinstance(k, str),
    so a tuple key containing a credential bypassed the firewall entirely.
    """
    # Tuple key where one element is a raw credential.
    payload = {(SYNTHETIC_CRED, "metadata"): "safe-value"}
    result = redact_payload(payload)
    # The tuple key must have the credential element replaced.
    assert (SYNTHETIC_CRED, "metadata") not in result, (
        "Tuple dict-key containing a secret must be replaced/redacted"
    )
    # The redacted form's key should contain '[REDACTED]' and 'metadata'.
    keys = list(result.keys())
    assert len(keys) == 1
    redacted_key = keys[0]
    assert SYNTHETIC_CRED not in str(redacted_key), (
        f"Raw credential still present in tuple dict-key after redaction: {redacted_key!r}"
    )
    # Safe value must survive.
    assert "safe-value" in result.values(), "Value must survive key redaction"


# ===========================================================================
# Codex R2 — #5  Crash-orphan sweeper wired at construction
# ===========================================================================


def test_r2_startup_sweep_removes_stale_cred_file(tmp_path: Path) -> None:
    """Codex R2 #5: Constructing AgentJobService removes orphaned cred files from
    a prior crashed run.

    We write a synthetic cred file matching the _CRED_FILE_PREFIX/_SUFFIX
    naming convention to tempfile.gettempdir() with a PID that cannot be a
    live job (PID 0 is never a real process), then construct a fresh service
    and assert the orphan is gone.
    """
    import tempfile

    from research_foundry.services.agent_job_service import (
        _CRED_FILE_PREFIX,  # type: ignore[attr-defined]
        _CRED_FILE_SUFFIX,  # type: ignore[attr-defined]
    )

    # Craft a stale cred file name that matches the glob used by scan_stale_cred_files.
    stale_name = f"{_CRED_FILE_PREFIX}pid0_stale_regression{_CRED_FILE_SUFFIX}"
    stale_path = Path(tempfile.gettempdir()) / stale_name
    try:
        stale_path.write_bytes(SYNTHETIC_CRED_BYTES)
        stale_path.chmod(0o600)

        # Constructing a new service must sweep the stale file.
        paths = FoundryPaths(root=tmp_path)
        _svc = AgentJobService(paths=paths)
        assert not stale_path.exists(), (
            "AgentJobService.__init__ must remove orphaned cred files via "
            "scan_stale_cred_files(); stale file still present after construction"
        )
    finally:
        # Best-effort cleanup if the test fails and the file still exists.
        if stale_path.exists():
            stale_path.unlink(missing_ok=True)


# ===========================================================================
# Codex R2 — NEW-A  OpenAI adapter exception leak
# ===========================================================================


def test_r2_openai_adapter_exception_notes_are_redacted() -> None:
    """Codex R2 NEW-A: An OpenAI SDK exception containing a raw credential is
    redacted before it enters AdapterResult.notes.

    The adapter's _run_real path catches all SDK exceptions and routes them
    through _degraded(note=...).  Without redaction the note carries the raw
    exception string which may include the API key.
    """

    class _FailingClient:
        """Minimal mock SDK client whose run_agent raises with a credential in the message."""

        def run_agent(self, _job_brief: dict) -> dict:
            raise RuntimeError(f"Authentication failed: key={SYNTHETIC_CRED}")

    adapter = OpenAIAgentsAdapter(sdk_client=_FailingClient())
    result = adapter.run({"prompt": "test intent", "model_profile": "sonnet"})

    assert result.degraded, "Adapter must be in degraded mode after SDK exception"
    notes_text = " ".join(result.notes)
    assert SYNTHETIC_CRED not in notes_text, (
        f"Raw credential found in degraded adapter notes after SDK exception: {notes_text!r}"
    )
    assert "[REDACTED]" in notes_text, (
        "Exception message must contain '[REDACTED]' marker when credential was present"
    )


# ===========================================================================
# Codex R2 — NEW-B  launch_job API response redacted
# ===========================================================================


def test_r2_launch_job_response_redacts_policy_snapshot(tmp_path: Path) -> None:
    """Codex R2 NEW-B: The launch_job API endpoint redacts its response dict so
    a secret embedded in policy_snapshot cannot leak via the HTTP response body.

    We configure a FastAPI test client with a mocked guard_check (passing) and
    a mocked spawn_job (no-op), then POST a policy_snapshot that embeds a raw
    credential and assert it is absent from the 201 response body.
    """
    from unittest.mock import patch

    import yaml as _yaml
    from fastapi.testclient import TestClient

    from research_foundry.api.app import create_app
    from research_foundry.api.routers.runs import get_paths
    from research_foundry.config import FoundryConfig
    from research_foundry.services.governance import GuardResult

    fp = FoundryPaths(root=tmp_path)
    # Enable the agent-jobs router (off by default; requires agents.enabled=true).
    fp.foundry_yaml.write_text("foundry:\n  agents:\n    enabled: true\n", encoding="utf-8")
    config = FoundryConfig(paths=fp)
    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: fp

    http = TestClient(app, raise_server_exceptions=True)

    payload = {
        "provider": "sdk_runner",
        "model_profile": "sonnet",
        "request_kind": "research",
        "policy_snapshot": {
            "key_profile": "personal",
            # Embed a raw credential inside policy_snapshot — must be redacted.
            "secret_field": SYNTHETIC_CRED,
        },
        "project_id": "proj-r2-newb",
    }

    with patch(
        "research_foundry.api.routers.agent_jobs.guard_check",
        return_value=GuardResult(passed=True, exit_code=0, violations=[]),
    ):
        with patch(
            "research_foundry.services.agent_job_service.AgentJobService.spawn_job"
        ):
            resp = http.post("/api/agent-jobs", json=payload)

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body_text = resp.text
    assert SYNTHETIC_CRED not in body_text, (
        "Raw credential from policy_snapshot leaked in launch_job API response body"
    )


# ===========================================================================
# Codex R3 — FIX-1  Credential-shaped artifact_id must not appear in filename
# ===========================================================================


def test_r3_credential_artifact_id_not_in_filename(
    service: AgentJobService,
) -> None:
    """Codex R3 FIX-1: An artifact_id that matches a known credential prefix
    must not appear raw in any on-disk filename in the job directory.

    Uses a credential-id that is shorter than the full-length regex threshold
    (9 chars after 'sk-ant-' instead of the required 20+) to verify that
    prefix-based detection closes the gap independently of the length
    quantifier — i.e. _safe_artifact_stem hashes the id based on the known
    prefix even when scan_secrets would not match it.

    Assertions
    ----------
    - No file whose name contains the raw 'sk-ant-SECRET123' string exists
      anywhere in the job directory after persist_artifact.
    - The artifact is still discoverable via list_staged_artifacts (the
      artifact_id VALUE inside the stored JSON is preserved; only the
      on-disk filename is hashed).
    - The artifact is still acceptable via accept_job (both write and accept
      paths use the same _safe_artifact_stem mapping, so the file is found).
    """
    job_id = "r3-fix1-cred-id-test"
    cred_artifact_id = "sk-ant-SECRET123"
    artifact = {
        "artifact_id": cred_artifact_id,
        "artifact_kind": "catalog_item",
        "content": "safe content field",
    }

    service.persist_artifact(job_id, artifact)
    job_dir = service._paths.agent_job_dir(job_id)

    # No filename in the job dir should contain the raw credential id.
    for f in job_dir.iterdir():
        assert cred_artifact_id not in f.name, (
            f"Raw credential artifact_id found in on-disk filename: {f.name!r}"
        )

    # Artifact must still be discoverable via list_staged_artifacts.
    staged = service.list_staged_artifacts(job_id)
    assert len(staged) == 1, "Artifact must be discoverable via list_staged_artifacts"
    assert staged[0].get("artifact_id") == cred_artifact_id, (
        "artifact_id field inside the persisted JSON must be preserved unchanged"
    )

    # Artifact must be acceptable: write a completed-state job manifest so
    # accept_job's status gate is satisfied.
    import dataclasses as _dc

    from research_foundry.services.agent_job_schemas import AgentJobStatus

    completed_job = _dc.replace(
        _make_job(job_id=job_id),
        status=AgentJobStatus.completed,
    )
    (job_dir / "job.json").write_text(
        json.dumps(completed_job.to_dict()), encoding="utf-8"
    )
    result = service.accept_job(job_id)
    assert result["accepted_artifact_count"] == 1, (
        "accept_job must locate and accept the artifact via its hashed filename"
    )


# ===========================================================================
# Codex R3 — FIX-2  source_card tool_input redacted before create_source_card
# ===========================================================================


def test_r3_source_card_tool_input_redacted_before_write(
    service: AgentJobService,
) -> None:
    """Codex R3 FIX-2: A credential present in source_card tool_input is
    redacted BEFORE it is forwarded to create_source_card, preventing the
    raw secret from reaching any on-disk source-card artifact.

    The existing post-call return-value redaction is insufficient on its own
    because create_source_card may persist the locator/content to disk
    internally before returning.  This test verifies the pre-write gate
    added to run_job_tool's source_card branch.

    Uses SYNTHETIC_ANT_CRED (full-length Anthropic-format key) so the
    redact_payload built-in pattern catches it and '[REDACTED]' appears in
    the kwarg forwarded to the (mocked) create_source_card.
    """
    import dataclasses as _dc

    from research_foundry.services.agent_job_schemas import AgentJobStatus

    job = _dc.replace(
        _make_job(job_id="r3-fix2-source-card"),
        policy_snapshot={"allowed_tools": ["source_card"], "data_scopes": []},
        status=AgentJobStatus.running,
    )

    # tool_input with a full-length credential embedded in the content field.
    tool_input: dict = {
        "locator": "https://example.com/article",
        "title": "Test Source",
        "content": f"Auth token: {SYNTHETIC_ANT_CRED}",
    }

    # Capture the kwargs forwarded to create_source_card.
    captured: dict = {}

    class _FakeResult:
        source_card_id = "sc-r3-fix2"
        path = Path("/tmp/sc-r3-fix2.md")
        source_type = "web"
        degraded = False

    def _mock_create(**kwargs: Any) -> _FakeResult:
        captured.update(kwargs)
        return _FakeResult()

    with mock.patch(
        "research_foundry.services.source_cards.create_source_card",
        side_effect=_mock_create,
    ):
        result = service.run_job_tool("source_card", tool_input, job)

    assert result["status"] == "ok", f"run_job_tool returned error: {result}"

    # The raw credential must NOT be present in the content forwarded to
    # create_source_card — it must have been replaced by '[REDACTED]' before
    # the call, not just in the return value.
    content_received = str(captured.get("content", ""))
    assert SYNTHETIC_ANT_CRED not in content_received, (
        "Raw credential found in tool_input content forwarded to create_source_card; "
        "FIX-2 pre-write redaction did not execute"
    )
    assert "[REDACTED]" in content_received, (
        "Expected '[REDACTED]' marker in the content forwarded to create_source_card; "
        "redact_payload must have been applied to tool_input before the call"
    )


@pytest.mark.skip(
    reason=(
        "DEFERRED — Mode-D Gate #3: verifying redaction against a REAL run-trace "
        "file requires Gate #2 (live provider approval) before a real-key run can "
        "be executed. This test MUST NOT be un-skipped until the project owner "
        "grants Gate #2 approval. This entire test module uses SYNTHETIC fixtures "
        "only and must never reference real API keys."
    )
)
def test_DEFERRED_real_run_trace_redaction() -> None:
    """DEFERRED: Verify redaction against a real run-trace file (Gate #3).

    Gate #3 requires all of the following preconditions:
      1.  Gate #2 (live provider) approval from the project owner.
      2.  A real ``rf run`` execution producing a telemetry/run_trace.jsonl
          file that was generated with a live provider credential.
      3.  Proof that no raw credential appears anywhere in the on-disk trace
          after being passed through redact_payload.

    Implementation steps (complete only after Gate #2 is approved):
      - Obtain a live provider credential under an approved test harness.
      - Execute ``rf run`` with that credential to produce a real trace file.
      - Deserialize the trace (JSONL) and apply redact_payload to each record.
      - Re-serialize and assert that scan_secrets finds zero hits.
      - Assert that the original raw key string is absent from the trace file.

    This stub exists to make Gate #3 requirements explicit and traceable.
    Execution must never reach this body while the test is marked skip.
    """
    pytest.fail(
        "Gate #3 DEFERRED: un-skip and implement only after Gate #2 approval"
    )
