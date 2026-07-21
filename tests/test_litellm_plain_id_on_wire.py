"""TEST-002 (E2-P3) — plain-id-on-wire enforcement for the ICA ``complete()`` path.

Invariant (R2, FR-15)
---------------------
A ``[1m]`` context suffix is a Claude-Code *client-side* hint; a raw
LiteLLM/HTTP caller that sends the literal ``claude-sonnet-5[1m]`` to ICA gets
HTTP 401 (``team_model_access_denied``). So the in-process completion path must
put the **plain** model id on the wire, prefixed only by ``openai/`` (which
forces litellm's OpenAI-compatible chat client against ``api_base``). This
module proves no ``[1m]``-suffixed id ever reaches the raw ``litellm.completion``
call, at two levels:

1. **Config level** — no ``model`` in ``config/model_profiles.yaml`` carries a
   ``[1m]`` suffix (a suffix planted there would propagate to the wire).
2. **Wire level** — driving ``complete()`` for every ICA profile, the wired
   ``model`` kwarg is exactly ``openai/<plain-id>`` and contains no ``[1m]``.

``_EXPECTED_IDS`` is the allowlist of plain wire model ids the ICA lane may send
(the E2-P3 "add the new provider id to _EXPECTED_IDS" obligation — the adapter's
own registry id ``litellm_router`` is already covered by
``tests/test_adapters.py::_EXPECTED_IDS``).
"""

from __future__ import annotations

import sys
import types
import unittest.mock as mock

import pytest

from research_foundry.adapters import get_adapter, load_all
from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths

_ICA_KEY_VAR = "RF_LLM_API_KEY"
_ICA_KEY_VALUE = "rf-secret-value-0002"

# Plain wire model ids the ICA lane is allowed to place on the wire (openai/<id>).
# Sourced from config/model_profiles.yaml — all plain, never a [1m] suffix.
_EXPECTED_IDS = {
    "claude-haiku-4-5",
    "gemma-4-26b-a4b-it",
    "claude-sonnet-5",
    "claude-opus-4-8",
}

# ICA-lane profiles that resolve to an ICA provider (all profiles in the config).
_ICA_PROFILES = [
    "rf_extract_free",
    "rf_extract_cheap",
    "rf_verify_balanced",
    "rf_synthesize_deep",
]


def _fake_litellm() -> types.ModuleType:
    mod = types.ModuleType("litellm")
    msg = types.SimpleNamespace(content="pong")
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    usage = types.SimpleNamespace(total_tokens=5)
    response = types.SimpleNamespace(choices=[choice], usage=usage, _hidden_params={})
    mod.completion = mock.MagicMock(name="litellm.completion", return_value=response)  # type: ignore[attr-defined]
    return mod


def _all_profile_model_ids(paths: FoundryPaths) -> list[tuple[str, str]]:
    """Return ``(profile_name, model_id)`` pairs across every preferred entry."""
    cfg = FoundryConfig(paths=paths)
    profiles = cfg.model_profiles.get("model_profiles", {})
    out: list[tuple[str, str]] = []
    for name, spec in profiles.items():
        if not isinstance(spec, dict):
            continue
        for entry in spec.get("preferred") or []:
            if isinstance(entry, dict) and entry.get("model"):
                out.append((name, str(entry["model"])))
    return out


def test_litellm_router_registered_in_adapters_allowlist() -> None:
    """The completion adapter's registry id is present in the adapters allowlist
    (the E2-P3 "add the new adapter id to _EXPECTED_IDS" obligation)."""
    from tests.test_adapters import _EXPECTED_IDS as _ADAPTER_IDS

    assert "litellm_router" in _ADAPTER_IDS
    load_all()
    assert get_adapter("litellm_router") is not None


def test_no_model_profile_id_carries_a_1m_suffix(tmp_foundry) -> None:
    """Config-level: no profile model id carries a ``[1m]`` suffix (which would
    propagate onto the wire and 401 the ICA lane)."""
    pairs = _all_profile_model_ids(tmp_foundry)
    assert pairs, "expected at least one profile model id in the fixture config"
    offenders = [(p, m) for (p, m) in pairs if "[1m]" in m]
    assert offenders == [], (
        f"model_profiles.yaml entries carry a forbidden [1m] suffix: {offenders}"
    )
    # Every configured plain id must be in the wire allowlist.
    for profile, model in pairs:
        assert model in _EXPECTED_IDS, (
            f"profile {profile!r} model {model!r} is not in the plain-wire "
            f"allowlist _EXPECTED_IDS={_EXPECTED_IDS}"
        )


@pytest.mark.parametrize("profile", _ICA_PROFILES)
def test_wire_model_is_openai_prefixed_plain_id(tmp_foundry, profile: str) -> None:
    """Wire-level: for each ICA profile the wired model is ``openai/<plain-id>``
    with no ``[1m]`` suffix, and the plain id is in the allowlist."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping",
            model_profile=profile,
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: _ICA_KEY_VALUE},
        )

    assert result["degraded"] is False
    fake.completion.assert_called_once()
    wire_model = fake.completion.call_args.kwargs["model"]

    assert "[1m]" not in wire_model, (
        f"[1m] suffix reached the wire for profile {profile!r}: {wire_model!r}"
    )
    assert wire_model.startswith("openai/"), (
        f"wire model must force the OpenAI-compatible client: {wire_model!r}"
    )
    plain = wire_model[len("openai/") :]
    assert plain in _EXPECTED_IDS, (
        f"wire model {wire_model!r} carries an unexpected plain id {plain!r}"
    )


def test_result_model_field_is_plain_not_suffixed(tmp_foundry) -> None:
    """The returned ``model`` field (used for accounting/telemetry) is also the
    plain id — no ``[1m]`` leaks into the result payload either."""
    adapter = LiteLLMRouterAdapter()
    fake = _fake_litellm()
    with mock.patch.object(adapter, "available", return_value=True), mock.patch.dict(
        sys.modules, {"litellm": fake}
    ):
        result = adapter.complete(
            "ping",
            model_profile="rf_verify_balanced",
            paths=tmp_foundry,
            env={_ICA_KEY_VAR: _ICA_KEY_VALUE},
        )

    assert "[1m]" not in str(result["model"])
    assert result["model"] in _EXPECTED_IDS
