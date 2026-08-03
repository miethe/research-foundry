"""Tests for the INERT attribution-fetch seam (deferred DEF-1 mechanism).

Proves:
* ``FoundryConfig.attribution_fetch_controls().attribution_fetch_enabled``
  defaults ``False`` and requires an explicit ``true`` to flip.
* Every provider adapter's ``fetch()`` call path returns the shared
  value-free disabled result with **zero sockets opened** — verified with
  the umbrella flag both OFF and ON, and across all three providers.
* The unreachable ``_send_request`` boundary raises ``NotImplementedError``
  before touching any socket, for all three providers.
* No return type surfaced by any adapter exposes a bare ``value`` (or other
  governed-field-shaped) attribute a caller could write straight into
  ``source_attribution.value`` / ``trust.*`` without independently
  satisfying ``schemas/source_attribution.schema.yaml``.

Synthetic-fixture only: no run-data plane, no live network, no schemas/
config/templates dependency. Safe to run from either MAIN or the worktree.
"""

from __future__ import annotations

import dataclasses
import socket
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from research_foundry.config import AttributionFetchControls, FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.attribution_fetch import (
    DISABLED_STATUS,
    ProviderFetchResult,
    crossref,
    openalex,
    semantic_scholar,
)

_PROVIDER_MODULES = (openalex, crossref, semantic_scholar)


def _minimal_paths(root: Path, *, attribution_fetch_enabled: bool | None = None) -> FoundryPaths:
    """Build a bare FoundryPaths pointing at a synthetic foundry.yaml.

    No schemas/config/templates copy — this test never touches schema
    validation, only ``FoundryConfig``'s plain-dict YAML resolution.
    """

    lines = ["foundry:", "  owner: Test"]
    if attribution_fetch_enabled is not None:
        lines += [
            "  attribution_fetch:",
            f"    attribution_fetch_enabled: {str(attribution_fetch_enabled).lower()}",
        ]
    (root / "foundry.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return FoundryPaths(root=root)


def _request_for(module: Any) -> Any:
    """Build the minimal request object each provider module's fetch() expects."""

    if module is openalex:
        return openalex.OpenAlexRequest(identifier="10.1234/example")
    if module is crossref:
        return crossref.CrossrefRequest(doi="10.1234/example")
    if module is semantic_scholar:
        return semantic_scholar.SemanticScholarRequest(paper_id="abc123")
    raise AssertionError(f"unexpected module: {module}")  # pragma: no cover


# --- flag default -----------------------------------------------------------


def test_attribution_fetch_enabled_defaults_false(tmp_path: Path) -> None:
    paths = _minimal_paths(tmp_path)
    cfg = FoundryConfig(paths=paths)
    controls = cfg.attribution_fetch_controls()
    assert isinstance(controls, AttributionFetchControls)
    assert controls.attribution_fetch_enabled is False


def test_attribution_fetch_enabled_false_when_explicitly_false(tmp_path: Path) -> None:
    paths = _minimal_paths(tmp_path, attribution_fetch_enabled=False)
    cfg = FoundryConfig(paths=paths)
    assert cfg.attribution_fetch_controls().attribution_fetch_enabled is False


def test_attribution_fetch_enabled_true_only_when_explicit(tmp_path: Path) -> None:
    paths = _minimal_paths(tmp_path, attribution_fetch_enabled=True)
    cfg = FoundryConfig(paths=paths)
    assert cfg.attribution_fetch_controls().attribution_fetch_enabled is True


def test_attribution_fetch_control_dataclass_default_is_false() -> None:
    # Construction with no args must default off, independent of any config file.
    assert AttributionFetchControls().attribution_fetch_enabled is False


# --- zero-socket guarantee, both flag states --------------------------------


@pytest.fixture
def _socket_guard():
    """Patch the lowest common network primitive plus the httpx client.

    ``socket.socket.connect`` catches ANY library (httpx, requests,
    urllib, raw sockets) that tries to open a real connection.
    ``httpx.Client.send`` is patched too as a second, library-specific
    tripwire in case a client is constructed without ever calling
    ``connect`` directly (e.g. mocked transports upstream).
    """

    with mock.patch.object(socket.socket, "connect") as connect_mock:
        try:
            import httpx

            with mock.patch.object(httpx.Client, "send") as send_mock:
                yield connect_mock, send_mock
        except ImportError:  # pragma: no cover - httpx is a declared dependency
            yield connect_mock, None


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
@pytest.mark.parametrize("flag_enabled", [False, True])
def test_fetch_never_opens_a_socket(
    module: Any, flag_enabled: bool, tmp_path: Path, _socket_guard
) -> None:
    connect_mock, send_mock = _socket_guard
    paths = _minimal_paths(tmp_path, attribution_fetch_enabled=flag_enabled)
    cfg = FoundryConfig(paths=paths)

    request = _request_for(module)
    result = module.fetch(request, config=cfg)

    assert isinstance(result, ProviderFetchResult)
    assert result.status == DISABLED_STATUS
    assert result.provider == module.PROVIDER_NAME
    assert result.reason  # non-empty explanation is always present

    connect_mock.assert_not_called()
    if send_mock is not None:
        send_mock.assert_not_called()


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_fetch_never_opens_a_socket_without_config(module: Any, _socket_guard) -> None:
    """``config=None`` (the default) must behave identically — still inert."""

    connect_mock, send_mock = _socket_guard
    request = _request_for(module)
    result = module.fetch(request)

    assert result.status == DISABLED_STATUS
    connect_mock.assert_not_called()
    if send_mock is not None:
        send_mock.assert_not_called()


# --- unreachable network boundary raises, before any socket ----------------


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_send_request_raises_before_any_socket(module: Any, _socket_guard) -> None:
    connect_mock, send_mock = _socket_guard
    request = _request_for(module)

    with pytest.raises(NotImplementedError):
        module._send_request(request)

    connect_mock.assert_not_called()
    if send_mock is not None:
        send_mock.assert_not_called()


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_fetch_never_calls_send_request(module: Any) -> None:
    """fetch() must not route through the raising internal boundary either."""

    request = _request_for(module)
    with mock.patch.object(module, "_send_request") as send_request_mock:
        result = module.fetch(request)
    send_request_mock.assert_not_called()
    assert result.status == DISABLED_STATUS


# --- non-laundering guarantee: no bare value/string escape hatch -----------


def test_provider_fetch_result_has_no_value_or_governed_field_shape() -> None:
    field_names = {f.name for f in dataclasses.fields(ProviderFetchResult)}
    assert field_names == {"provider", "status", "reason"}
    # None of these are a governed field name or a generic passthrough value.
    disallowed = {"value", "asserter_type", "license_basis", "trust", "best_value"}
    assert field_names.isdisjoint(disallowed)


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_fetch_return_type_is_always_the_shared_disabled_result(module: Any) -> None:
    """fetch() must return ProviderFetchResult, never a raw-response shape."""

    request = _request_for(module)
    result = module.fetch(request)
    assert type(result) is ProviderFetchResult


@pytest.mark.parametrize("module", _PROVIDER_MODULES)
def test_raw_response_shape_is_never_instantiated_by_this_module(module: Any) -> None:
    """The documented raw-response dataclass exists but this module never
    builds one — it has no constructor call sites at all in the module
    source, so nothing on it can ever reach a caller.
    """

    raw_response_names = [name for name in module.__all__ if name.endswith("RawResponse")]
    assert raw_response_names, f"{module.__name__} should declare a RawResponse shape"
    for name in raw_response_names:
        raw_cls = getattr(module, name)
        source = Path(module.__file__).read_text(encoding="utf-8")
        # The only occurrences of the class name in its own module are the
        # class definition and its docstring references — never a call
        # (`Name(`) constructing an instance.
        assert f"{name}(" not in source, (
            f"{name} must never be instantiated in {module.__name__}"
        )
        # Sanity: it is a real dataclass shape (documentation is honest).
        assert dataclasses.is_dataclass(raw_cls)


def test_disabled_result_helper_is_pure_and_value_free() -> None:
    from research_foundry.services.attribution_fetch import disabled_result

    result = disabled_result("openalex", "because DEF-1 is open")
    assert result == ProviderFetchResult(
        provider="openalex", status=DISABLED_STATUS, reason="because DEF-1 is open"
    )
