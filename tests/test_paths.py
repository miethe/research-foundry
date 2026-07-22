"""Workspace-root resolution tests, incl. the RESEARCH_FOUNDRY_HOME override (FU-2)."""

from __future__ import annotations

from research_foundry.paths import _ROOT_ENV, find_workspace_root


def test_env_override_pins_root_regardless_of_cwd(tmp_path, monkeypatch):
    """RESEARCH_FOUNDRY_HOME pins the workspace root for the default (cwd) discovery
    so an embedding process (e.g. Hermes cd'd into another repo) does not make rf
    adopt that checkout's .git ancestor (FU-2)."""

    dedicated = tmp_path / "rf-workspace"
    dedicated.mkdir()
    # cwd is a *different* directory that itself looks like a workspace root.
    other = tmp_path / "some_repo"
    (other / ".git").mkdir(parents=True)
    monkeypatch.chdir(other)
    monkeypatch.setenv(_ROOT_ENV, str(dedicated))

    assert find_workspace_root() == dedicated.resolve()


def test_explicit_start_beats_env_override(tmp_path, monkeypatch):
    """An explicit start= argument is intentional and wins over the env override."""

    dedicated = tmp_path / "rf-workspace"
    dedicated.mkdir()
    explicit = tmp_path / "explicit"
    (explicit / ".git").mkdir(parents=True)
    monkeypatch.setenv(_ROOT_ENV, str(dedicated))

    assert find_workspace_root(start=explicit) == explicit.resolve()


def test_env_override_ignored_when_dir_missing(tmp_path, monkeypatch):
    """A stale RESEARCH_FOUNDRY_HOME pointing at a non-existent dir is ignored — we
    fall back to the cwd walk rather than fabricating a root."""

    marker_root = tmp_path / "walk_root"
    (marker_root / ".git").mkdir(parents=True)
    child = marker_root / "child"
    child.mkdir()
    monkeypatch.chdir(child)
    monkeypatch.setenv(_ROOT_ENV, str(tmp_path / "does_not_exist"))

    assert find_workspace_root() == marker_root.resolve()
