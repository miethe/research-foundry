"""Security tests: zero-raw-creds guarantee and redact_payload coverage.

Verifies that:
- redact_payload replaces secret-matching strings with '[REDACTED]' at any depth
- Scalar pass-through types (None, int, float, bool) are unchanged
- AgentJobEvent and AgentJobArtifact to_dict() output contains zero raw credentials
  after redact_payload is applied

All test credentials are SYNTHETIC and clearly non-real (contain 'test' + zeros).
"""

from __future__ import annotations

import json

import pytest

from research_foundry.services.agent_job_schemas import (
    AgentJobArtifact,
    AgentJobEvent,
    AgentJobStage,
)
from research_foundry.services.governance import redact_payload, scan_secrets

# ---------------------------------------------------------------------------
# Synthetic credentials — clearly non-real (test prefix + zero fill)
# ---------------------------------------------------------------------------

# Matches r"sk-[A-Za-z0-9]{20,}" — 'sk-' + 46 alphanumeric chars
_FAKE_OPENAI_KEY = "sk-test0000000000000000000000000000000000000000000000"

# Matches r"sk-ant-[A-Za-z0-9_\-]{20,}" — 'sk-ant-' + 50 alphanumeric chars
_FAKE_ANTHROPIC_KEY = "sk-ant-test00000000000000000000000000000000000000000000000000"


# ---------------------------------------------------------------------------
# Basic redact_payload behaviour
# ---------------------------------------------------------------------------


def test_redact_payload_flat_string() -> None:
    """A top-level string matching a secret pattern is fully replaced."""
    result = redact_payload("sk-abc123abc123abc123abc123")
    assert result == "[REDACTED]"


def test_redact_payload_nested_dict() -> None:
    """Matching strings inside nested dicts are replaced; safe values survive."""
    obj = {"outer": {"key": "sk-ant-abc123abc123abc123abc123abc", "safe": "hello"}}
    result = redact_payload(obj)
    assert result == {"outer": {"key": "[REDACTED]", "safe": "hello"}}


def test_redact_payload_list() -> None:
    """Matching strings inside a list are replaced; safe elements survive."""
    obj = ["sk-abc123abc123abc123abc123", "safe"]
    result = redact_payload(obj)
    assert result == ["[REDACTED]", "safe"]


def test_redact_payload_passthrough_types() -> None:
    """Scalar non-string types pass through without modification."""
    assert redact_payload(42) == 42
    assert redact_payload(3.14) == 3.14
    assert redact_payload(True) is True
    assert redact_payload(False) is False
    assert redact_payload(None) is None


# ---------------------------------------------------------------------------
# Zero-raw-creds guarantee for agent job schema shapes
# ---------------------------------------------------------------------------


def test_zero_raw_creds_in_agent_job_event() -> None:
    """No raw credential survives redact_payload on an AgentJobEvent.to_dict()."""
    event = AgentJobEvent(
        event_id="evt-sec-001",
        agent_job_id="job-sec-001",
        stage=AgentJobStage.plan,
        timestamp="2026-07-07T00:00:00Z",
        payload={
            "model": "claude-opus",
            "credentials": {
                "api_key": _FAKE_OPENAI_KEY,
                "fallback_key": _FAKE_ANTHROPIC_KEY,
            },
            "note": "safe text",
        },
        sequence=1,
    )
    raw = event.to_dict()
    sanitized = redact_payload(raw)

    # Serialize to a flat string so scan_secrets can sweep the entire structure
    serialised = json.dumps(sanitized)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Raw credentials found in sanitized AgentJobEvent output: {hits}"
    )


def test_zero_raw_creds_in_agent_job_artifact() -> None:
    """No raw credential survives redact_payload on an AgentJobArtifact.to_dict()."""
    artifact = AgentJobArtifact(
        artifact_id="art-sec-001",
        agent_job_id="job-sec-001",
        artifact_kind="source_card",
        created_at="2026-07-07T00:00:00Z",
        path="outputs/report.md",
        # Simulate a mistakenly stored credential in content_hash field
        content_hash=_FAKE_OPENAI_KEY,
        accepted=False,
    )
    raw = artifact.to_dict()
    sanitized = redact_payload(raw)

    serialised = json.dumps(sanitized)
    hits = scan_secrets(serialised)
    assert hits == [], (
        f"Raw credentials found in sanitized AgentJobArtifact output: {hits}"
    )
