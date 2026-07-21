"""TEST-003 (E2-P3) — forced-tool-call structured output + mocked-live-path gate.

OQ-4 resolution — which ``model_profile`` roles need schema-constrained output
================================================================================
Grouped by ``config/model_profiles.yaml`` ``allowed_for`` roles / tier:

* **Schema-constrained → forced tool-call** (output deserialised into a typed
  artifact, so it MUST conform to a strict JSON shape):
    - ``rf_extract_free``  → source_carding, simple_extraction, tagging, dedupe
    - ``rf_extract_cheap`` → source_carding, extraction_cards, initial_claim_mapping
    - ``rf_verify_balanced`` → claim_audit, contradiction_review, council_review
  These emit source cards / extraction cards / claim maps / verdicts / tag sets.
  Structured output is obtained via OpenAI-compatible ``tools`` + ``tool_choice``
  (a forced function call) passed straight to ``litellm.completion``.

* **Free prose → no schema**:
    - ``rf_synthesize_deep`` → final_report, executive_synthesis,
      deep_literature_synthesis
  These produce natural-language report text; no tool-call is forced.

Load-bearing invariant (R5/R6, FR-15)
-------------------------------------
For the schema-constrained roles the structured shape is ALWAYS a forced
tool-call. The completion path must **never** put ``response_format`` or
``output_config`` / ``output_config.format`` on the wire: ICA's
OpenAI-compatible chat endpoint honours forced tool-calls but not JSON-mode
``response_format`` (R5), and ``output_config.format`` is an ICA-native field
dropped on the OpenAI-compatible path (R6). This module locks both the positive
(tools+tool_choice forwarded verbatim) and the negative (no response_format /
output_config ever) sides, plus the live-branch truth table.

All offline: ``litellm`` faked via ``sys.modules``; no network, no real key.
"""

from __future__ import annotations

import sys
import types
import unittest.mock as mock
from typing import Any

import pytest

from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter

_ICA_KEY_VAR = "RF_LLM_API_KEY"
_ICA_KEY_VALUE = "rf-secret-value-0003"

# OQ-4 enumeration, machine-checkable.
_SCHEMA_CONSTRAINED_PROFILES = ("rf_extract_free", "rf_extract_cheap", "rf_verify_balanced")
_FREE_PROSE_PROFILES = ("rf_synthesize_deep",)

# A minimal OpenAI-compatible forced-tool-call spec for the schema-constrained roles.
_EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_extraction_card",
        "description": "Emit one structured extraction card.",
        "parameters": {
            "type": "object",
            "properties": {"claim": {"type": "string"}, "confidence": {"type": "number"}},
            "required": ["claim"],
        },
    },
}
_FORCED_CHOICE = {"type": "function", "function": {"name": "emit_extraction_card"}}

# Forbidden structured-output channels — must NEVER reach the wire.
_FORBIDDEN_WIRE_KEYS = ("response_format", "output_config")


def _fake_litellm() -> types.ModuleType:
    mod = types.ModuleType("litellm")
    msg = types.SimpleNamespace(content="pong")
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    usage = types.SimpleNamespace(total_tokens=5)
    response = types.SimpleNamespace(choices=[choice], usage=usage, _hidden_params={})
    mod.completion = mock.MagicMock(name="litellm.completion", return_value=response)  # type: ignore[attr-defined]
    return mod


def _run_live(adapter: LiteLLMRouterAdapter, fake: types.ModuleType, **kw: Any) -> dict:
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        return adapter.complete("ping", **kw)


# ---------------------------------------------------------------------------
# OQ-4 enumeration coverage — no profile is unclassified
# ---------------------------------------------------------------------------


def test_oq4_enumeration_covers_every_configured_profile(tmp_foundry) -> None:
    """The OQ-4 schema-constrained ∪ free-prose partition covers every profile
    in the config and the two sets are disjoint — no profile is unclassified."""
    from research_foundry.config import FoundryConfig

    cfg = FoundryConfig(paths=tmp_foundry)
    configured = set((cfg.model_profiles.get("model_profiles") or {}).keys())
    enumerated = set(_SCHEMA_CONSTRAINED_PROFILES) | set(_FREE_PROSE_PROFILES)

    assert set(_SCHEMA_CONSTRAINED_PROFILES).isdisjoint(_FREE_PROSE_PROFILES)
    assert configured <= enumerated, (
        f"config profiles not classified by OQ-4: {configured - enumerated}"
    )


# ---------------------------------------------------------------------------
# Positive — schema-constrained roles: tools+tool_choice forwarded verbatim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", _SCHEMA_CONSTRAINED_PROFILES)
def test_schema_constrained_role_forwards_forced_tool_call(tmp_foundry, profile: str) -> None:
    """A schema-constrained role's ``tools`` + ``tool_choice`` reach
    ``litellm.completion`` verbatim, and NO forbidden structured-output key is set."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    result = _run_live(
        adapter,
        fake,
        model_profile=profile,
        paths=tmp_foundry,
        env={_ICA_KEY_VAR: _ICA_KEY_VALUE},
        tools=[_EXTRACT_TOOL],
        tool_choice=_FORCED_CHOICE,
    )

    assert result["degraded"] is False
    fake.completion.assert_called_once()
    kwargs = fake.completion.call_args.kwargs

    # Positive: forced tool-call forwarded unchanged.
    assert kwargs["tools"] == [_EXTRACT_TOOL]
    assert kwargs["tool_choice"] == _FORCED_CHOICE

    # Negative: no JSON-mode / ICA-native structured-output channel on the wire.
    for forbidden in _FORBIDDEN_WIRE_KEYS:
        assert forbidden not in kwargs, (
            f"forbidden structured-output key {forbidden!r} reached the wire for "
            f"profile {profile!r}: {kwargs}"
        )


# ---------------------------------------------------------------------------
# Negative — response_format / output_config are NEVER emitted by complete()
# ---------------------------------------------------------------------------


def test_no_forbidden_structured_output_key_without_tools(tmp_foundry) -> None:
    """With no tools supplied, ``complete()`` still never emits response_format /
    output_config (it adds no implicit structured-output channel)."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    result = _run_live(
        adapter,
        fake,
        model_profile="rf_extract_cheap",
        paths=tmp_foundry,
        env={_ICA_KEY_VAR: _ICA_KEY_VALUE},
    )

    assert result["degraded"] is False
    kwargs = fake.completion.call_args.kwargs
    for forbidden in _FORBIDDEN_WIRE_KEYS:
        assert forbidden not in kwargs
    # No tools/tool_choice were injected either when the caller passed none.
    assert "tools" not in kwargs
    assert "tool_choice" not in kwargs


@pytest.mark.parametrize("profile", _FREE_PROSE_PROFILES)
def test_free_prose_role_sends_no_tools_and_no_forbidden_keys(tmp_foundry, profile: str) -> None:
    """A free-prose role called without tools sends neither a tool-call nor a
    forbidden structured-output channel — it is plain-text synthesis."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    result = _run_live(
        adapter,
        fake,
        model_profile=profile,
        paths=tmp_foundry,
        env={_ICA_KEY_VAR: _ICA_KEY_VALUE},
    )

    assert result["degraded"] is False
    kwargs = fake.completion.call_args.kwargs
    assert "tools" not in kwargs and "tool_choice" not in kwargs
    for forbidden in _FORBIDDEN_WIRE_KEYS:
        assert forbidden not in kwargs


# ---------------------------------------------------------------------------
# Mocked-live-path truth table — fires ONLY when key AND available() both true
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("available", "has_key", "expect_fire"),
    [
        (True, True, True),  # both open → live fire
        (True, False, False),  # available but no key → dark
        (False, True, False),  # key but not available → dark
        (False, False, False),  # neither → dark
    ],
)
def test_live_branch_fires_only_when_key_and_available_both_true(
    tmp_foundry, available: bool, has_key: bool, expect_fire: bool
) -> None:
    """Truth table (R6): the live wire call fires iff available() AND the ICA key
    are both present (provider is ICA for this profile). Every other cell degrades."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    env = {_ICA_KEY_VAR: _ICA_KEY_VALUE} if has_key else {}

    with mock.patch.object(adapter, "available", return_value=available), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping", model_profile="rf_extract_cheap", paths=tmp_foundry, env=env
        )

    if expect_fire:
        fake.completion.assert_called_once()
        assert result["degraded"] is False
        assert result["reason"] == "live_completion"
    else:
        fake.completion.assert_not_called()
        assert result["degraded"] is True
        assert result["reason"] in {"litellm_unavailable", "no_ica_key"}
