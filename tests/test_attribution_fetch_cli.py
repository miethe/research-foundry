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
