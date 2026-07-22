"""E2-P2 — offline tests for governance wiring on ``LiteLLMRouterAdapter.complete()``.

LLM-004/LLM-005: proves ``complete()`` sits strictly downstream of
``governance.guard_check()`` — a work/client-sensitive completion is BLOCKED
under the default ``approved_work_providers: []`` (rule
``no_work_sensitive_to_unapproved_provider``, governance.py ~L283-297), while
a personal/public completion is NOT gated by this check. No network, no
``litellm`` import required on the blocked path.
"""

from __future__ import annotations

import sys
import types
import unittest.mock as mock

from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter

_ICA_KEY_VAR = "RF_LLM_API_KEY"


def _fake_litellm() -> types.ModuleType:
    mod = types.ModuleType("litellm")
    mod.completion = mock.MagicMock(name="litellm.completion")  # type: ignore[attr-defined]
    return mod


def test_work_sensitive_completion_blocked_by_default_approved_providers(tmp_foundry) -> None:
    """Default approved_work_providers: [] BLOCKS a work_sensitive completion,
    even with every dark-gate condition (available + key) open — the guard
    fires before can_fire is ever evaluated."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping",
            model_profile="rf_extract_cheap",
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: "rf-secret-value"},
            sensitivity="work_sensitive",
        )

    assert result["degraded"] is True
    assert result["reason"] == "governance_blocked"
    assert "no_work_sensitive_to_unapproved_provider" in result["violations"]
    fake.completion.assert_not_called()


def test_client_sensitive_completion_also_blocked(tmp_foundry) -> None:
    """client_sensitive is in the same blocked class as work_sensitive."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping",
            model_profile="rf_extract_cheap",
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: "rf-secret-value"},
            sensitivity="client_sensitive",
        )

    assert result["degraded"] is True
    assert result["reason"] == "governance_blocked"
    fake.completion.assert_not_called()


def test_personal_sensitivity_not_gated_by_this_check(tmp_foundry) -> None:
    """personal sensitivity is NOT matched by no_work_sensitive_to_unapproved_provider
    — the guard passes, and the dark gate's own logic (available/key/provider)
    is what decides whether the live path fires."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()

    msg = types.SimpleNamespace(content="pong")
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    usage = types.SimpleNamespace(total_tokens=3)
    response = types.SimpleNamespace(choices=[choice], usage=usage, _hidden_params={})
    fake.completion.return_value = response

    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping",
            model_profile="rf_extract_cheap",
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: "rf-secret-value"},
            sensitivity="personal",
        )

    # The guard did not block it — the dark gate's own three conditions
    # (provider==ica, available(), key present) are all open, so it fires live.
    assert result["reason"] != "governance_blocked"
    assert result["degraded"] is False
    fake.completion.assert_called_once()


def test_public_sensitivity_not_gated_by_this_check(tmp_foundry) -> None:
    """public sensitivity is likewise ungated by no_work_sensitive_to_unapproved_provider;
    with the litellm import gate closed it still degrades — but for the
    dark-gate reason, never governance_blocked.

    FU-5: mock the import gate instead of asserting litellm's absence, so the
    test holds whether or not the ``[llm]`` extra is installed."""
    adapter = LiteLLMRouterAdapter()
    with mock.patch.object(adapter, "available", return_value=False):
        assert adapter.available() is False
        result = adapter.complete(
            "ping",
            model_profile="rf_extract_cheap",
            paths=tmp_foundry,
            env={},
            sensitivity="public",
        )

    assert result["degraded"] is True
    assert result["reason"] in {"litellm_unavailable", "no_ica_key"}
    assert result["reason"] != "governance_blocked"


def test_unspecified_sensitivity_not_gated_by_this_check(tmp_foundry) -> None:
    """No sensitivity supplied (the pre-E2-P2 default) is not matched by the
    work-sensitivity rule either — callers that omit it are unaffected by
    this specific check (existing/default behavior preserved)."""
    adapter = LiteLLMRouterAdapter()
    result = adapter.complete(
        "ping", model_profile="rf_extract_cheap", paths=tmp_foundry, env={}
    )

    assert result["reason"] != "governance_blocked"
