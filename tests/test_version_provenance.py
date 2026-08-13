"""Tests for the vendored ``_version_provenance`` helper.

This module is the reference test suite for an artifact copied byte-identically into six AOS
repos, so it tests the *contract* rather than research-foundry specifics: never raise, never hang,
distinguish "unknown" from a fabricated value, and disclose an editable checkout's commit.

The two properties worth stating explicitly, because they are what a `--version` caller
depends on and what a plausible-looking rewrite would break:

  1. **Total.** Every failure mode (no git, not a repo, timeout, corrupt metadata, missing
     distribution) degrades to a None field or a short string. A traceback out of
     ``--version`` breaks health checks and shims.
  2. **Honest.** An undeterminable field is ``None``, never ``"unknown"``/``"0.0.0"``/``""``
     dressed up as data. A caller comparing two hosts must be able to tell "these differ"
     from "I could not tell".
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from research_foundry import _version_provenance as vp

# ---------------------------------------------------------------------------
# resolve_checkout
# ---------------------------------------------------------------------------


class TestResolveCheckout:
    def test_reports_commit_and_branch_for_a_real_repo(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        info = vp.resolve_checkout(tmp_path)

        assert info["commit"] is not None
        assert info["commit_short"] == info["commit"][:8]
        assert len(info["commit_short"]) == 8
        assert info["branch"] is not None
        assert info["describe"] is not None
        assert info["dirty"] is False

    def test_non_repo_directory_yields_none_commit_not_a_placeholder(self, tmp_path: Path) -> None:
        """An editable install off a non-git source tree is legitimate; do not invent a sha."""
        info = vp.resolve_checkout(tmp_path)

        assert info["commit"] is None
        assert info["commit_short"] is None
        assert info["describe"] is None
        assert info["root"] == str(tmp_path)

    def test_detects_dirty_tracked_modification(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "seed.txt").write_text("changed")

        assert vp.resolve_checkout(tmp_path)["dirty"] is True

    def test_untracked_only_tree_is_not_dirty(self, tmp_path: Path) -> None:
        """--untracked-files=no is deliberate: a stray build artifact is not a different build.

        Without this, every repo with an untracked scratch file reports dirty forever and the
        flag stops carrying information.
        """
        _init_repo(tmp_path)
        (tmp_path / "scratch.tmp").write_text("junk")

        assert vp.resolve_checkout(tmp_path)["dirty"] is False

    def test_detached_head_reports_no_branch(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        subprocess.run(["git", "checkout", "--detach", sha], cwd=tmp_path,
                       capture_output=True, check=True)

        info = vp.resolve_checkout(tmp_path)
        assert info["commit"] == sha
        assert info["branch"] is None, "detached HEAD must not report the literal 'HEAD'"

    def test_missing_directory_does_not_raise(self, tmp_path: Path) -> None:
        assert vp.resolve_checkout(tmp_path / "nope")["commit"] is None


# ---------------------------------------------------------------------------
# _run_git — the containment boundary
# ---------------------------------------------------------------------------


class TestRunGitIsTotal:
    def test_timeout_returns_none_rather_than_propagating(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hung git must yield None. `--version` is called by health checks and shims."""

        def _hang(*_a: object, **_k: object) -> None:
            raise subprocess.TimeoutExpired(cmd="git", timeout=vp._GIT_TIMEOUT_S)

        monkeypatch.setattr(vp.subprocess, "run", _hang)
        assert vp._run_git(tmp_path, "rev-parse", "HEAD") is None

    def test_missing_git_binary_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_git(*_a: object, **_k: object) -> None:
            raise FileNotFoundError("git")

        monkeypatch.setattr(vp.subprocess, "run", _no_git)
        assert vp._run_git(tmp_path, "rev-parse", "HEAD") is None

    def test_pins_fsmonitor_off(self) -> None:
        """core.fsmonitor has hung git tooling on this machine twice; the pin is load-bearing.

        Asserted on the constant rather than by observing behaviour: the failure it prevents is
        a hang, which a test cannot safely reproduce.
        """
        assert "core.fsmonitor=false" in vp._GIT_BASE

    def test_timeout_is_bounded_and_short(self) -> None:
        assert 0 < vp._GIT_TIMEOUT_S <= 5


# ---------------------------------------------------------------------------
# version_info / version_string
# ---------------------------------------------------------------------------


class TestVersionInfo:
    def test_reports_this_installed_distribution(self) -> None:
        info = vp.version_info("research-foundry", prog_name="rf")

        assert info["program"] == "rf"
        assert info["distribution"] == "research-foundry"
        assert info["install"] in {"editable", "wheel"}
        assert info["python"]

    def test_absent_distribution_is_labelled_not_installed(self) -> None:
        info = vp.version_info("definitely-not-a-real-distribution-xyz")

        assert info["install"] == "not-installed"
        assert info["version"] is None

    def test_is_json_serialisable(self) -> None:
        """The aggregator collects this over a pipe; a non-serialisable field breaks the fleet view."""
        json.dumps(vp.version_info("research-foundry"))

    def test_editable_install_discloses_its_checkout(self) -> None:
        info = vp.version_info("research-foundry")
        if info["install"] != "editable":
            pytest.skip("not an editable install")

        assert info["location"], "editable install must resolve its source path"
        assert Path(info["location"]).is_dir()


class TestVersionString:
    def test_absent_distribution_renders_without_raising(self) -> None:
        out = vp.version_string("definitely-not-a-real-distribution-xyz", prog_name="ghost")
        assert out == "ghost (not installed)"

    def test_includes_program_and_version(self) -> None:
        info = vp.version_info("research-foundry", prog_name="rf")
        out = vp.version_string("research-foundry", prog_name="rf")

        assert out.startswith("rf, version ")
        if info["version"]:
            assert info["version"] in out

    def test_editable_string_names_the_commit(self) -> None:
        info = vp.version_info("research-foundry", prog_name="rf")
        if info["install"] != "editable" or not info["commit_short"]:
            pytest.skip("not an editable git checkout")

        out = vp.version_string("research-foundry", prog_name="rf")
        assert "editable" in out
        assert info["commit_short"] in out

    def test_is_a_single_line(self) -> None:
        """Callers grep this; a multi-line --version breaks one-line parsers."""
        assert "\n" not in vp.version_string("research-foundry", prog_name="rf")


class TestEmit:
    def test_plain_mode_prints_one_line(self, capsys: pytest.CaptureFixture[str],
                                       monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AOS_VERSION_JSON", raising=False)
        vp._emit("research-foundry", prog_name="rf")

        out = capsys.readouterr().out.strip()
        assert out.startswith("rf, version ")
        assert "\n" not in out

    @pytest.mark.parametrize("flag", ["1", "true", "TRUE", "yes", "on"])
    def test_json_mode_emits_parseable_object(self, flag: str,
                                             capsys: pytest.CaptureFixture[str],
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AOS_VERSION_JSON", flag)
        vp._emit("research-foundry", prog_name="rf")

        payload = json.loads(capsys.readouterr().out)
        assert payload["program"] == "rf"
        assert payload["distribution"] == "research-foundry"

    @pytest.mark.parametrize("flag", ["0", "false", "no", "off", ""])
    def test_falsy_flag_stays_in_plain_mode(self, flag: str,
                                           capsys: pytest.CaptureFixture[str],
                                           monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AOS_VERSION_JSON", flag)
        vp._emit("research-foundry", prog_name="rf")

        with pytest.raises(ValueError):
            json.loads(capsys.readouterr().out)


# ---------------------------------------------------------------------------
# _editable_path
# ---------------------------------------------------------------------------


class TestEditablePath:
    def test_non_editable_local_install_is_not_treated_as_editable(self, tmp_path: Path) -> None:
        """`dir_info.editable` is the marker. A wheel built from a local dir is a SNAPSHOT —
        reporting its build directory's current commit would describe code that is not running.
        """
        dist = _FakeDist(json.dumps({"dir_info": {}, "url": tmp_path.as_uri()}))
        assert vp._editable_path(dist) is None  # type: ignore[arg-type]

    def test_editable_marker_resolves_the_path(self, tmp_path: Path) -> None:
        dist = _FakeDist(json.dumps({"dir_info": {"editable": True}, "url": tmp_path.as_uri()}))
        assert vp._editable_path(dist) == tmp_path  # type: ignore[arg-type]

    def test_percent_encoded_path_is_decoded(self, tmp_path: Path) -> None:
        spaced = tmp_path / "My Repos"
        spaced.mkdir()
        dist = _FakeDist(json.dumps({"dir_info": {"editable": True}, "url": spaced.as_uri()}))
        assert vp._editable_path(dist) == spaced  # type: ignore[arg-type]

    @pytest.mark.parametrize("raw", ["", "not json", "[]", '{"dir_info":{"editable":true}}'])
    def test_malformed_metadata_yields_none(self, raw: str) -> None:
        assert vp._editable_path(_FakeDist(raw)) is None  # type: ignore[arg-type]

    def test_unreadable_metadata_yields_none(self) -> None:
        assert vp._editable_path(_FakeDist(None, raise_on_read=True)) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class _FakeDist:
    """Minimal stand-in for importlib.metadata.Distribution.read_text."""

    def __init__(self, payload: str | None, *, raise_on_read: bool = False) -> None:
        self._payload = payload
        self._raise = raise_on_read

    def read_text(self, name: str) -> str | None:
        if self._raise:
            raise OSError("unreadable")
        return self._payload if name == "direct_url.json" else None


def _init_repo(path: Path) -> None:
    """Create a committed git repo at ``path``, isolated from the ambient user config."""
    env_args = [
        "-c", "user.email=test@example.invalid",
        "-c", "user.name=Test",
        "-c", "commit.gpgsign=false",
        "-c", "init.defaultBranch=main",
    ]
    subprocess.run(["git", *env_args, "init", "-q"], cwd=path, check=True,
                   capture_output=True)
    (path / "seed.txt").write_text("seed")
    subprocess.run(["git", *env_args, "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", *env_args, "commit", "-qm", "seed"], cwd=path, check=True,
                   capture_output=True)
