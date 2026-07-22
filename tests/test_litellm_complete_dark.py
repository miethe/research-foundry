"""E2-P1 — offline/dark tests for ``LiteLLMRouterAdapter.complete()``.

These prove the DARK gate (D3, FR-13, R2/R3/R6): the live wire call fires only
when *all three* of {provider==ica, available(), RF_LLM_API_KEY present} hold.
In the default offline env ``litellm`` is absent, so ``available() is False`` and
``complete()`` returns ``degraded=True`` with zero live calls — verified here by
asserting a mocked ``litellm.completion`` is never invoked.

The comprehensive credential-isolation / plain-id / forced-tool-call regression
suite is E2-P3; this file only establishes the degraded/dark branch holds.
"""

from __future__ import annotations

import sys
import types
import unittest.mock as mock

from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter

# rf_extract_cheap's first preferred entry is provider=ica (see model_profiles.yaml).
_ICA_KEY_VAR = "RF_LLM_API_KEY"


def _fake_litellm() -> types.ModuleType:
    """A stand-in ``litellm`` module whose ``completion`` is a MagicMock."""
    mod = types.ModuleType("litellm")
    mod.completion = mock.MagicMock(name="litellm.completion")  # type: ignore[attr-defined]
    return mod


def test_default_env_is_dark_and_degraded(tmp_foundry) -> None:
    """Core DoD: with the litellm import gate closed → degraded, no fire.

    FU-5: mock the import gate rather than asserting the suite venv lacks
    ``litellm``. The ``[llm]`` extra installs litellm, which would flip
    ``available()`` to True and make the old absence-assertion fail. The
    invariant under test is the behavior when the gate is closed, not the
    dependency's physical absence.
    """
    adapter = LiteLLMRouterAdapter()
    with mock.patch.object(adapter, "available", return_value=False):
        assert adapter.available() is False
        result = adapter.complete(
            "ping", model_profile="rf_extract_cheap", paths=tmp_foundry, env={}
        )

    assert result["degraded"] is True
    assert result["text"] is None
    assert result["reason"] in {"litellm_unavailable", "no_ica_key"}


def test_no_live_call_when_litellm_unavailable(tmp_foundry) -> None:
    """available()==False → litellm.completion is never called, even with a key present."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    # FU-5: force the import gate closed rather than relying on litellm being
    # absent from the venv (the [llm] extra installs it). Inject a fake litellm
    # so that IF the gate wrongly opened we'd observe a call; provide a key so
    # the ONLY closed gate is available().
    with mock.patch.object(adapter, "available", return_value=False), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping",
            model_profile="rf_extract_cheap",
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: "rf-secret-value"},
        )

    assert result["degraded"] is True
    assert result["reason"] == "litellm_unavailable"
    fake.completion.assert_not_called()


def test_no_live_call_when_key_absent(tmp_foundry) -> None:
    """provider==ica + available() but NO RF_LLM_API_KEY → degraded, no fire."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping", model_profile="rf_extract_cheap", paths=tmp_foundry, env={}
        )

    assert result["degraded"] is True
    assert result["reason"] == "no_ica_key"
    assert result["provider"] == "ica"
    fake.completion.assert_not_called()


def test_non_ica_provider_is_unsupported(tmp_foundry) -> None:
    """A non-ICA routing decision never attempts a completion (unsupported lane)."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        # Force the decision to a non-ica provider.
        with mock.patch.object(
            adapter,
            "route",
            return_value={
                "provider": "anthropic",
                "model": "claude-sonnet-5",
                "api_base": None,
                "degraded": False,
            },
        ):
            result = adapter.complete("ping", paths=tmp_foundry, env={"ANY": "x"})

    assert result["degraded"] is True
    assert result["reason"] == "non_ica_provider_completion_unsupported"
    fake.completion.assert_not_called()


def test_live_path_fires_only_when_all_gates_open(tmp_foundry) -> None:
    """Basic mocked-live proof: with all three gates open, litellm.completion fires
    exactly once, targeting the OpenAI-compatible chat client with the PLAIN wire id
    (``openai/<plain-id>``, never a ``[1m]`` suffix) and the RF_LLM_API_KEY value."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()

    # Shape a minimal litellm-style response object.
    msg = types.SimpleNamespace(content="pong")
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    usage = types.SimpleNamespace(total_tokens=7)
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
        )

    fake.completion.assert_called_once()
    kwargs = fake.completion.call_args.kwargs
    assert kwargs["model"] == "openai/claude-haiku-4-5"  # plain id, openai/ prefix
    assert "[1m]" not in kwargs["model"]
    assert kwargs["api_key"] == "rf-secret-value"  # RF_LLM_API_KEY value only
    assert kwargs["api_base"] == "https://api.nextgen-beta.ica.ibm.com/ica/v1"
    assert result["degraded"] is False
    assert result["text"] == "pong"
    assert result["tokens"] == 7
