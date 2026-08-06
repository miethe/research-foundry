"""Tests for the ``rf attribution fetch`` CLI surface (Phase C CLI seam).

Covers: the subcommand is discoverable under ``rf attribution`` (and the
``attribution`` group is still discoverable under root ``rf``); it prints a
disabled message and exits 0 without ever calling a provider adapter or
opening a socket when ``attribution_fetch_enabled`` is off (the default, and
the only state exercised here -- this is a Mode C sprint, not a scope to flip
the flag on); no enumerated combination of the command's own CLI arguments
bypasses that disabled state; and the pre-existing sibling ``rf attribution
validate`` command still works unchanged (regression guard against breaking
the shared ``attribution_app`` sub-app).
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths
from research_foundry.services.attribution_fetch import crossref, openalex, semantic_scholar

runner = CliRunner()


def _invoke(args: list[str], cwd: Path):
    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(prev)


@pytest.fixture(autouse=True)
def _blocked_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail hard if anything under test opens a real socket.

    Belt-and-suspenders alongside the adapter-layer spies below: even if a
    future edit routed around the patched ``fetch()`` functions, a raw
    ``socket.socket()`` call would blow up the test instead of silently
    reaching the network.
    """

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("rf attribution fetch must never open a socket")

    monkeypatch.setattr(socket, "socket", _forbidden)


@pytest.fixture
def _adapter_spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Wrap every provider adapter's ``fetch`` in a call-counting spy."""

    spies = {
        "crossref": MagicMock(wraps=crossref.fetch),
        "openalex": MagicMock(wraps=openalex.fetch),
        "semantic_scholar": MagicMock(wraps=semantic_scholar.fetch),
    }
    monkeypatch.setattr(crossref, "fetch", spies["crossref"])
    monkeypatch.setattr(openalex, "fetch", spies["openalex"])
    monkeypatch.setattr(semantic_scholar, "fetch", spies["semantic_scholar"])
    return spies


def _assert_no_adapter_calls(spies: dict[str, MagicMock]) -> None:
    for spy in spies.values():
        spy.assert_not_called()


# --- discoverability ---------------------------------------------------------


def test_attribution_fetch_listed_under_attribution_help(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["attribution", "--help"], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert "fetch" in out.output


def test_attribution_group_listed_under_rf_help(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["--help"], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert "attribution" in out.output


# --- disabled by default, no network ----------------------------------------


def test_attribution_fetch_disabled_by_default_table_output(
    tmp_foundry: FoundryPaths, _adapter_spies: dict[str, MagicMock]
) -> None:
    out = _invoke(["attribution", "fetch", "crossref", "10.1000/xyz"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert "disabled" in out.output
    assert "DEF-1" in out.output
    assert "DEF-6" in out.output
    _assert_no_adapter_calls(_adapter_spies)


def test_attribution_fetch_disabled_by_default_json_output(
    tmp_foundry: FoundryPaths, _adapter_spies: dict[str, MagicMock]
) -> None:
    out = _invoke(["attribution", "fetch", "openalex", "W123456789", "--json"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    payload = json.loads(out.output)
    assert payload["status"] == "disabled"
    assert "DEF-1" in payload["reason"]
    assert "DEF-6" in payload["reason"]
    _assert_no_adapter_calls(_adapter_spies)


# --- no argument combination bypasses the disabled state --------------------

_PROVIDERS = ["crossref", "openalex", "semantic_scholar", "not-a-real-provider", ""]
_IDENTIFIERS = ["10.1000/xyz", "", "W123456789", "paper-id-with-dashes", "../../etc/passwd"]
_JSON_FLAGS = ["--json", "--no-json"]


@pytest.mark.parametrize("provider", _PROVIDERS)
@pytest.mark.parametrize("identifier", _IDENTIFIERS)
@pytest.mark.parametrize("json_flag", _JSON_FLAGS)
def test_no_arg_combination_bypasses_disabled_state(
    tmp_foundry: FoundryPaths,
    _adapter_spies: dict[str, MagicMock],
    provider: str,
    identifier: str,
    json_flag: str,
) -> None:
    """Enumerate every arg this command accepts: 3 valid providers + an
    unknown provider + an empty provider, x 5 identifier shapes (normal DOI,
    empty string, OpenAlex-shaped id, dashed id, a path-traversal-looking
    string), x both --json/--no-json. All 50 combinations must land in the
    disabled branch — exit 0, disabled output, zero adapter calls.
    """

    out = _invoke(["attribution", "fetch", provider, identifier, json_flag], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    if json_flag == "--json":
        payload = json.loads(out.output)
        assert payload["status"] == "disabled"
    else:
        assert "disabled" in out.output
    _assert_no_adapter_calls(_adapter_spies)


# --- sibling regression: `rf attribution validate` still works unchanged ---


def test_attribution_validate_still_works_unchanged(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["attribution", "validate", "--as-of", "2026-07-21"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert "0" in out.output


# --- clearance-gates M3: the posture-on path renders without AttributeError --


def _declare_posture(root: Path) -> None:
    """Turn BOTH controls on in *root*'s ``foundry.yaml``.

    Mirrors ``tests/test_attribution_fetch_dev_test_posture.py::
    _posture_config``'s ``dev_test_posture`` block, but merged into the
    fixture's real ``foundry.yaml`` (rather than a hand-built minimal one) so
    the CLI's own ``FoundryConfig.load()`` discovery resolves it from cwd
    exactly as it does in production.
    """

    import yaml

    data = yaml.safe_load((root / "foundry.yaml").read_text(encoding="utf-8")) or {}
    foundry = data.setdefault("foundry", {})
    foundry["attribution_fetch"] = {"attribution_fetch_enabled": True}
    foundry["dev_test_posture"] = {
        "live_fetch_enabled": True,
        "rationale": "local dev/test only; no license/ToS posture asserted",
        "declared_at": "2026-08-05",
        "declared_by": "nick",
    }
    (root / "foundry.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


@pytest.mark.parametrize("json_flag", ["--json", "--no-json"])
def test_posture_on_path_renders_without_attribute_error(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, json_flag: str
) -> None:
    """Regression guard: with both the umbrella flag and the dev/test posture
    declared, ``crossref.fetch`` returns a ``ClearedProviderFetchResult`` --
    which has ``provider``/``status``/``value``/``clearance`` but deliberately
    NO ``reason`` field. The renderer previously read ``result.reason``
    unconditionally and raised ``AttributeError`` on this shape.

    Mocked at the ``_fetch_json`` seam (the same seam
    ``test_attribution_fetch_dev_test_posture.py`` uses), so no socket is
    opened -- the module-level ``_blocked_socket`` autouse fixture would fail
    the test outright if one were.
    """

    _declare_posture(tmp_foundry.root)
    monkeypatch.setattr(
        crossref,
        "_fetch_json",
        lambda url, **kw: {"status": "ok", "message": {"DOI": "10.1/x", "is-referenced-by-count": 3}},
    )

    out = _invoke(["attribution", "fetch", "crossref", "10.1/x", json_flag], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert out.exception is None or isinstance(out.exception, SystemExit), out.exception
    if json_flag == "--json":
        payload = json.loads(out.output)
        assert payload["provider"] == "crossref"
        assert payload["status"] == "fetched"
        assert payload["reason"] == "fetched (dev/test posture): fetched"
        # The fetched value and its clearance stamp are NOT rendered on this
        # surface -- it reports posture + status only.
        assert "value" not in payload
        assert "clearance" not in payload
    else:
        assert "crossref" in out.output
        assert "fetched" in out.output


def test_posture_on_result_is_the_cleared_shape_with_no_reason_field(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pins the premise of the test above: the object the CLI renders on the
    posture-on path really is ``ClearedProviderFetchResult`` and really has no
    ``reason`` attribute. Without this, the regression guard could pass
    vacuously if a future edit gave that type a ``reason`` field.
    """

    from research_foundry.config import FoundryConfig
    from research_foundry.services.attribution_fetch import ClearedProviderFetchResult

    _declare_posture(tmp_foundry.root)
    monkeypatch.setattr(
        crossref,
        "_fetch_json",
        lambda url, **kw: {"status": "ok", "message": {"DOI": "10.1/x", "is-referenced-by-count": 3}},
    )

    prev = Path.cwd()
    os.chdir(tmp_foundry.root)
    try:
        config = FoundryConfig.load()
        result = crossref.fetch(crossref.CrossrefRequest(doi="10.1/x"), config=config)
    finally:
        os.chdir(prev)

    assert isinstance(result, ClearedProviderFetchResult)
    assert not hasattr(result, "reason")
    assert result.clearance, "every ClearedProviderFetchResult carries a stamp"


def test_posture_off_with_umbrella_on_still_renders_adapter_reason(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The middle state -- umbrella flag on, posture NOT declared -- still
    goes through the plain ``ProviderFetchResult`` ``.reason`` rendering,
    unchanged. Threading ``config`` into ``fetch()`` must not have flipped
    this path on by itself.
    """

    import yaml

    def _boom(*a: object, **k: object) -> None:
        raise AssertionError("no fetch may be issued without a declared posture")

    monkeypatch.setattr(crossref, "_fetch_json", _boom)

    root = tmp_foundry.root
    data = yaml.safe_load((root / "foundry.yaml").read_text(encoding="utf-8")) or {}
    data.setdefault("foundry", {})["attribution_fetch"] = {"attribution_fetch_enabled": True}
    (root / "foundry.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    out = _invoke(["attribution", "fetch", "crossref", "10.1/x", "--json"], root)

    assert out.exit_code == 0, out.output
    payload = json.loads(out.output)
    assert payload["status"] == "disabled"
    assert "DEF-1" in payload["reason"]
