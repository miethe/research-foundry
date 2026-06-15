"""Tests for integrations/notebooklm.py (NotebookLMClient).

Covers:
- available() returns False when 'notebooklm' not on PATH (shutil.which → None)
- available() returns False when _run_cli returns None (nonzero exit from subprocess)
- available() returns True when status probe succeeds (returns {} or non-None dict)
- _run_cli returns None on nonzero exit code (monkeypatched subprocess.run)
- _run_cli returns None on timeout
- _run_cli returns None on JSON parse error
- _run_cli returns None when stdout is a JSON list (not dict)
- create_notebook() returns None when unavailable
- add_source() returns None when unavailable
- get_notebook() returns matching entry from list; None when not found
- get_notebooklm_client() returns NotebookLMClient singleton
- _get/_post/_patch always return None (CLI transport, no HTTP)
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_foundry.integrations.notebooklm import NotebookLMClient, get_notebooklm_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    """Return a fake subprocess.CompletedProcess-like object."""
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _client_with_cli(cli_path: str = "/fake/notebooklm") -> NotebookLMClient:
    """Return a client wired to a fixed (fake) CLI path."""
    return NotebookLMClient(cli_path=cli_path)


# ---------------------------------------------------------------------------
# available() — binary resolution
# ---------------------------------------------------------------------------


class TestAvailableBinaryResolution:
    """available() gates on shutil.which / _resolve_cli."""

    def test_false_when_which_returns_none(self):
        """No binary on PATH → available() returns False without subprocess."""
        client = NotebookLMClient()
        with patch("shutil.which", return_value=None):
            result = client.available()
        assert result is False

    def test_false_when_cli_path_set_but_run_returns_none(self):
        """Binary path set but the status probe fails → False."""
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=1, stdout=""),
        ):
            result = client.available()
        assert result is False

    def test_true_when_status_probe_succeeds_empty_stdout(self):
        """Binary found and subprocess exits 0 with no stdout → {} → True."""
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=""),
        ):
            result = client.available()
        assert result is True

    def test_true_when_status_probe_returns_json_dict(self):
        """Binary returns JSON status dict → True."""
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout='{"status": "ok"}'),
        ):
            result = client.available()
        assert result is True

    def test_available_uses_env_cli_path(self, monkeypatch):
        """NOTEBOOKLM_CLI_PATH env takes precedence over PATH lookup."""
        monkeypatch.setenv("NOTEBOOKLM_CLI_PATH", "/env/notebooklm")
        client = NotebookLMClient()
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=""),
        ) as mock_run:
            client.available()
        # First positional arg to subprocess.run should use the env-provided path.
        args = mock_run.call_args[0][0]
        assert args[0] == "/env/notebooklm"


# ---------------------------------------------------------------------------
# _run_cli — return-value contract
# ---------------------------------------------------------------------------


class TestRunCli:
    """_run_cli returns dict | None; never raises."""

    def test_returns_none_on_nonzero_exit(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=1, stdout='{"error": "auth"}'),
        ):
            result = client._run_cli(["status"])
        assert result is None

    def test_returns_none_on_timeout(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="notebooklm", timeout=2.0),
        ):
            result = client._run_cli(["status"])
        assert result is None

    def test_returns_none_on_oserror(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch("subprocess.run", side_effect=OSError("binary not found")):
            result = client._run_cli(["list", "--json"])
        assert result is None

    def test_returns_none_on_invalid_json(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout="not valid json {{"),
        ):
            result = client._run_cli(["list", "--json"])
        assert result is None

    def test_returns_none_when_stdout_is_json_list(self):
        """Bare JSON list is not a dict → returned as None."""
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout="[1, 2, 3]"),
        ):
            result = client._run_cli(["list", "--json"])
        assert result is None

    def test_returns_dict_on_success(self):
        client = _client_with_cli("/fake/notebooklm")
        payload = {"notebooks": [{"id": "nb_001", "title": "Test"}]}
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=json.dumps(payload)),
        ):
            result = client._run_cli(["list", "--json"])
        assert result == payload

    def test_returns_empty_dict_on_empty_stdout(self):
        """Exit 0 with no stdout → {} (health signal for status)."""
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=""),
        ):
            result = client._run_cli(["status"])
        assert result == {}

    def test_returns_none_when_cli_not_found(self):
        """No cli_path and shutil.which returns None → None without subprocess call."""
        client = NotebookLMClient()
        with patch("shutil.which", return_value=None):
            result = client._run_cli(["list"])
        assert result is None


# ---------------------------------------------------------------------------
# create_notebook
# ---------------------------------------------------------------------------


class TestCreateNotebook:
    def test_returns_dict_on_success(self):
        client = _client_with_cli("/fake/notebooklm")
        payload = {"notebook_id": "nb_new_001", "notebook_title": "RF — test"}
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=json.dumps(payload)),
        ):
            result = client.create_notebook("RF — test")
        assert result is not None
        assert result["notebook_id"] == "nb_new_001"

    def test_returns_none_on_cli_failure(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=1),
        ):
            result = client.create_notebook("RF — test")
        assert result is None

    def test_passes_title_to_cli(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout='{"notebook_id": "x"}'),
        ) as mock_run:
            client.create_notebook("RF — my project")
        args = mock_run.call_args[0][0]
        assert "RF — my project" in args


# ---------------------------------------------------------------------------
# add_source
# ---------------------------------------------------------------------------


class TestAddSource:
    def test_returns_dict_on_success(self):
        client = _client_with_cli("/fake/notebooklm")
        payload = {"source_id": "src_001", "status": "processing"}
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=json.dumps(payload)),
        ):
            result = client.add_source("nb_001", "/tmp/report.md")
        assert result is not None
        assert result["source_id"] == "src_001"

    def test_returns_none_on_failure(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=1),
        ):
            result = client.add_source("nb_001", "/tmp/report.md")
        assert result is None

    def test_title_param_accepted_without_error(self):
        """title kwarg is accepted (future-compat) even though CLI ignores it currently."""
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout='{"source_id": "s1"}'),
        ):
            result = client.add_source("nb_001", "http://example.com", title="My Source")
        assert result is not None


# ---------------------------------------------------------------------------
# get_notebook
# ---------------------------------------------------------------------------


class TestGetNotebook:
    def test_returns_matching_notebook(self):
        client = _client_with_cli("/fake/notebooklm")
        payload = {
            "notebooks": [
                {"id": "nb_001", "title": "First"},
                {"id": "nb_002", "title": "Second"},
            ]
        }
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=json.dumps(payload)),
        ):
            result = client.get_notebook("nb_002")
        assert result is not None
        assert result["title"] == "Second"

    def test_returns_none_when_not_found(self):
        client = _client_with_cli("/fake/notebooklm")
        payload = {"notebooks": [{"id": "nb_001", "title": "First"}]}
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout=json.dumps(payload)),
        ):
            result = client.get_notebook("nb_nonexistent")
        assert result is None

    def test_returns_none_when_list_cli_fails(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=1),
        ):
            result = client.get_notebook("nb_001")
        assert result is None

    def test_returns_none_when_response_has_no_notebooks_key(self):
        client = _client_with_cli("/fake/notebooklm")
        with patch(
            "subprocess.run",
            return_value=_make_proc(returncode=0, stdout='{"status": "ok"}'),
        ):
            result = client.get_notebook("nb_001")
        assert result is None


# ---------------------------------------------------------------------------
# HTTP helpers always return None (CLI transport)
# ---------------------------------------------------------------------------


class TestHttpHelpersReturnNone:
    """_get/_post/_patch always return None; CLI transport replaces HTTP."""

    def test_get_returns_none(self):
        client = NotebookLMClient()
        assert client._get("/any/path") is None

    def test_post_returns_none(self):
        client = NotebookLMClient()
        assert client._post("/any/path", {}) is None

    def test_patch_returns_none(self):
        client = NotebookLMClient()
        assert client._patch("/any/path", {}) is None


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------


class TestGetNotebooklmClient:
    def test_returns_notebooklm_client_instance(self):
        # Reset module-level singleton first.
        import research_foundry.integrations.notebooklm as nlm_mod
        nlm_mod._notebooklm_client = None

        client = get_notebooklm_client()
        assert isinstance(client, NotebookLMClient)

    def test_returns_same_instance_on_repeat_calls(self):
        import research_foundry.integrations.notebooklm as nlm_mod
        nlm_mod._notebooklm_client = None

        c1 = get_notebooklm_client()
        c2 = get_notebooklm_client()
        assert c1 is c2

    def test_imported_from_integrations_init(self):
        from research_foundry.integrations import get_notebooklm_client as getnlm

        assert callable(getnlm)

    def test_notebooklm_client_imported_from_integrations_init(self):
        from research_foundry.integrations import NotebookLMClient as NLMCls

        assert NLMCls is NotebookLMClient


# ---------------------------------------------------------------------------
# from_config factory (never raises)
# ---------------------------------------------------------------------------


class TestFromConfig:
    def test_from_config_returns_client_without_foundry_yaml(self, tmp_path: Path):
        """from_config() succeeds even without a foundry.yaml on disk."""
        with patch(
            "research_foundry.config.FoundryConfig.load",
            side_effect=FileNotFoundError("no foundry.yaml"),
        ):
            client = NotebookLMClient.from_config()
        assert isinstance(client, NotebookLMClient)

    def test_from_config_respects_env_cli_path(self, monkeypatch):
        monkeypatch.setenv("NOTEBOOKLM_CLI_PATH", "/custom/notebooklm")
        with patch(
            "research_foundry.config.FoundryConfig.load",
            side_effect=Exception("config error"),
        ):
            client = NotebookLMClient.from_config()
        assert client._resolve_cli() == "/custom/notebooklm"
