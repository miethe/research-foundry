"""TEST-001 (E2-P3) — credential-isolation regression for the ICA ``complete()`` path.

Mirrors the style of ``tests/security/test_credential_isolation_regression.py``:
a load-bearing security regression that FAILS if the invariant is ever broken.

Invariant (R3, FR-15, and E2-P1 LLM-003 credential-review obligation)
---------------------------------------------------------------------
The in-process ICA completion path
(:meth:`research_foundry.adapters.litellm_router.LiteLLMRouterAdapter.complete`)
resolves its wire credential **exclusively** from ``RF_LLM_API_KEY`` (via
``_PROVIDER_KEYS["ica"]``). It must **never** read ``ANTHROPIC_API_KEY`` or
``OPENAI_API_KEY`` — those point at the real-vendor APIs and are forbidden under
Mode-D Gate #2. This module proves that with two independent, complementary
tripwires:

1. **Access tripwire** — a recording ``Mapping`` supplied as ``env`` records
   every key the code reads. Driving ``complete()`` all the way down the live
   (mocked) wire path and asserting neither forbidden var appears in the access
   log FAILS if any future change reads them.
2. **Poison-value tripwire** — real-looking ``ANTHROPIC_API_KEY`` /
   ``OPENAI_API_KEY`` values are planted in ``os.environ`` AND in the passed
   ``env`` mapping; the test asserts those poison strings never reach the raw
   ``litellm.completion`` call kwargs and that the wired ``api_key`` is the
   ``RF_LLM_API_KEY`` value only. FAILS if either vendor key leaks onto the wire.

All work is offline: ``litellm`` is faked via ``sys.modules`` and
``available()`` is monkeypatched True — no network, no real key.
"""

from __future__ import annotations

import os
import sys
import types
import unittest.mock as mock
from typing import Any

import pytest

from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter

_ICA_KEY_VAR = "RF_LLM_API_KEY"
_ICA_KEY_VALUE = "rf-secret-value-0001"
_FORBIDDEN_VARS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")

# Real-looking (but synthetic) poison values for the forbidden vendor vars.
_POISON_ANTHROPIC = "sk-ant-poison00000000000000000000000000000000000000000000"
_POISON_OPENAI = "sk-poison0000000000000000000000000000000000000000"


class _RecordingEnv(dict):
    """A ``dict`` that logs every key read via ``get``/``__getitem__``.

    Used to prove that the completion path never even *reads* a forbidden vendor
    env var — a stronger claim than "the value never leaks", because it catches
    an access whose result would be ``None`` today but a live key tomorrow.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.accessed: list[str] = []

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        self.accessed.append(key)
        return super().get(key, default)

    def __getitem__(self, key: str) -> Any:
        self.accessed.append(key)
        return super().__getitem__(key)


def _fake_litellm() -> types.ModuleType:
    """A stand-in ``litellm`` whose ``completion`` returns a minimal response."""
    mod = types.ModuleType("litellm")
    msg = types.SimpleNamespace(content="pong")
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    usage = types.SimpleNamespace(total_tokens=5)
    response = types.SimpleNamespace(choices=[choice], usage=usage, _hidden_params={})
    mod.completion = mock.MagicMock(name="litellm.completion", return_value=response)  # type: ignore[attr-defined]
    return mod


def test_ica_complete_path_never_reads_vendor_key_env_vars(tmp_foundry) -> None:
    """TEST-001: driving the full live path, ANTHROPIC/OPENAI env vars are never read.

    The access tripwire records every ``env`` key touched by ``route()`` +
    ``complete()``. For an all-ICA profile the only key that should be read is
    ``RF_LLM_API_KEY``; the two forbidden vendor vars must be absent from the log.
    """
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    env = _RecordingEnv({_ICA_KEY_VAR: _ICA_KEY_VALUE})

    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping", model_profile="rf_extract_cheap", paths=tmp_foundry, env=env
        )

    # The live path fired (all three dark-gate conditions open).
    fake.completion.assert_called_once()
    assert result["degraded"] is False

    # Hard invariant: neither forbidden vendor var was ever accessed.
    for var in _FORBIDDEN_VARS:
        assert var not in env.accessed, (
            f"Forbidden vendor env var {var!r} was READ on the ICA completion path; "
            f"access log = {env.accessed}"
        )
    # Positive control: the ICA key WAS read (proves the tripwire is live).
    assert _ICA_KEY_VAR in env.accessed, (
        "RF_LLM_API_KEY was never read — the recording env is not on the path, "
        "so the negative assertion above would be vacuous"
    )


def test_vendor_keys_in_os_environ_never_reach_the_wire(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TEST-001: poison ANTHROPIC/OPENAI keys never appear in litellm.completion kwargs.

    Even with real-looking vendor keys planted in BOTH ``os.environ`` and the
    passed ``env``, the wired ``api_key`` must be the RF_LLM_API_KEY value and
    neither poison string may appear anywhere in the call kwargs.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", _POISON_ANTHROPIC)
    monkeypatch.setenv("OPENAI_API_KEY", _POISON_OPENAI)

    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    # env carries the poison AND the RF key; the ICA path must ignore the poison.
    env = {
        _ICA_KEY_VAR: _ICA_KEY_VALUE,
        "ANTHROPIC_API_KEY": _POISON_ANTHROPIC,
        "OPENAI_API_KEY": _POISON_OPENAI,
    }

    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping", model_profile="rf_extract_cheap", paths=tmp_foundry, env=env
        )

    assert result["degraded"] is False
    fake.completion.assert_called_once()
    kwargs = fake.completion.call_args.kwargs

    # The wire credential is the RF key — not either poison vendor value.
    assert kwargs["api_key"] == _ICA_KEY_VALUE

    serialised = repr(kwargs)
    for poison in (_POISON_ANTHROPIC, _POISON_OPENAI):
        assert poison not in serialised, (
            "A vendor API key leaked into the raw litellm.completion call kwargs: "
            f"{serialised}"
        )


def test_os_environ_is_not_mutated_by_the_completion_path(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TEST-001 (defensive): the completion path does not read/clobber vendor keys
    from the ambient process environment when an explicit ``env`` is supplied."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", _POISON_ANTHROPIC)
    monkeypatch.setenv("OPENAI_API_KEY", _POISON_OPENAI)

    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        adapter.complete(
            "ping",
            model_profile="rf_extract_cheap",
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: _ICA_KEY_VALUE},
        )

    # The ambient vendor vars are untouched (never-clobber contract).
    assert os.environ["ANTHROPIC_API_KEY"] == _POISON_ANTHROPIC
    assert os.environ["OPENAI_API_KEY"] == _POISON_OPENAI
