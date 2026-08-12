"""CLI-level contract for ``rf --version``.

The vendored helper is unit-tested in ``test_version_provenance.py``; this module tests the
*wiring* — the part that is repo-specific and the part that silently breaks. Three failure
modes it exists to catch:

  1. ``--version`` needing a subcommand. The root group carries ``no_args_is_help=True``, so
     without ``invoke_without_command=True`` on the callback ``rf --version`` would exit 2 with
     a usage error instead of printing. That is exactly the state this change replaced.
  2. ``--version`` not being eager, so an unrelated required argument or a config load runs
     first and a broken workspace makes the CLI unable to report its own version — the one
     question a health check asks when everything else is broken.
  3. The flag bypassing ``_emit`` (e.g. calling ``version_string`` directly), which silently
     drops ``AOS_VERSION_JSON`` support and breaks the fleet-wide aggregator with no error.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from research_foundry import _version_provenance as vp
from research_foundry.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _plain_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise an ambient AOS_VERSION_JSON so plain-mode assertions are not env-dependent."""

    monkeypatch.delenv("AOS_VERSION_JSON", raising=False)


class TestVersionFlag:
    def test_exits_zero_with_no_subcommand(self) -> None:
        """`rf --version` must work bare. A required-subcommand group would exit 2 here."""

        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0, result.output

    def test_reports_the_installed_version(self) -> None:
        info = vp.version_info("research-foundry", prog_name="rf")
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0, result.output
        assert result.output.startswith("rf, version ")
        assert info["version"], "the distribution must be installed for this suite to be meaningful"
        assert info["version"] in result.output

    def test_output_is_a_single_line(self) -> None:
        """Health checks and shims grep this; a multi-line --version breaks one-line parsers."""

        result = runner.invoke(app, ["--version"])

        assert len(result.output.strip().splitlines()) == 1, result.output

    def test_discloses_the_checkout_commit_when_editable(self) -> None:
        """The whole point: an editable install's real identity is its checkout commit.

        Skipped for a wheel install, where there is no checkout to name and the declared
        version is the only honest answer.
        """

        info = vp.version_info("research-foundry", prog_name="rf")
        if info["install"] != "editable" or not info["commit_short"]:
            pytest.skip("not an editable git checkout")

        result = runner.invoke(app, ["--version"])

        assert "editable" in result.output
        assert info["commit_short"] in result.output

    def test_json_mode_emits_a_parseable_object(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AOS_VERSION_JSON must reach the CLI — proof the flag routes through `_emit`."""

        monkeypatch.setenv("AOS_VERSION_JSON", "1")
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["program"] == "rf"
        assert payload["distribution"] == "research-foundry"

    def test_is_eager_and_wins_over_a_bogus_subcommand(self) -> None:
        """An eager option is parsed before subcommand resolution, so this must not exit 2."""

        result = runner.invoke(app, ["--version", "definitely-not-a-subcommand"])

        assert result.exit_code == 0, result.output
        assert result.output.startswith("rf, version ")


class TestBareInvocationStillHelps:
    def test_no_args_prints_help_not_version(self) -> None:
        """Adding a root callback must not turn bare `rf` into a no-op or a version print."""

        result = runner.invoke(app, [])

        assert not result.output.startswith("rf, version ")
        assert "Usage" in result.output or "usage" in result.output


class TestVersionSubcommandAgrees:
    def test_rf_version_matches_the_flag(self) -> None:
        """Two answers to one question is the defect being fixed; keep the surfaces identical."""

        flag = runner.invoke(app, ["--version"])
        sub = runner.invoke(app, ["version"])

        assert sub.exit_code == 0, sub.output
        assert sub.output.strip() == flag.output.strip()
