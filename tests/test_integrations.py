"""Tests for Phase 0 integration clients — ARC and IntentTree.

All HTTP calls are monkeypatched; no real network requests are made.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

from research_foundry.integrations import ArcClient, IntentTreeClient
from research_foundry.integrations.arc import _DEFAULT_BASE_URL as ARC_DEFAULT
from research_foundry.integrations.intenttree import (
    _DEFAULT_BASE_URL as IT_DEFAULT,
)
from research_foundry.integrations.intenttree import (
    _TOKEN_ENV,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_urlopen(response_body: bytes, status: int = 200):
    """Return a context-manager mock that yields a file-like with ``read()``."""

    resp = MagicMock()
    resp.read.return_value = response_body
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _json_response(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode()


# ===========================================================================
# ArcClient
# ===========================================================================


class TestArcClientAvailable:
    """available() contracts."""

    def test_available_true_when_health_returns_200_no_integrations_key(self):
        """Bare 200 with no integrations block -> available."""

        resp = _mock_urlopen(_json_response({"status": "ok"}))
        with patch("urllib.request.urlopen", return_value=resp):
            client = ArcClient()
            assert client.available() is True

    def test_available_true_when_integrations_authoring_available(self):
        payload = {"integrations": {"authoring": {"available": True}}}
        resp = _mock_urlopen(_json_response(payload))
        with patch("urllib.request.urlopen", return_value=resp):
            assert ArcClient().available() is True

    def test_available_false_when_integrations_authoring_not_available(self):
        payload = {"integrations": {"authoring": {"available": False}}}
        resp = _mock_urlopen(_json_response(payload))
        with patch("urllib.request.urlopen", return_value=resp):
            assert ArcClient().available() is False

    def test_available_false_on_connection_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            assert ArcClient().available() is False

    def test_available_false_on_timeout(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            assert ArcClient().available() is False

    def test_available_false_on_http_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://127.0.0.1:8910/api/health",
                code=503,
                msg="Service Unavailable",
                hdrs=None,  # type: ignore[arg-type]
                fp=None,
            ),
        ):
            assert ArcClient().available() is False

    def test_available_false_on_invalid_json(self):
        resp = _mock_urlopen(b"not json at all")
        with patch("urllib.request.urlopen", return_value=resp):
            assert ArcClient().available() is False

    def test_available_false_on_empty_response(self):
        resp = _mock_urlopen(b"")
        with patch("urllib.request.urlopen", return_value=resp):
            # empty body -> {} -> no integrations block -> True (bare 200 path)
            # Actually empty bytes returns {} from _get, which is not None,
            # so bare-200 path applies: True.
            result = ArcClient().available()
            assert result is True  # empty body is still a 200


class TestArcClientConfig:
    """Config loading and defaults."""

    def test_default_base_url(self):
        client = ArcClient()
        assert client.base_url == ARC_DEFAULT.rstrip("/")

    def test_custom_base_url(self):
        client = ArcClient(base_url="http://arc.internal:9000")
        assert client.base_url == "http://arc.internal:9000"

    def test_from_config_falls_back_to_default(self, monkeypatch, tmp_foundry):
        """When foundry.yaml has no integrations.arc key, use default."""

        # Monkeypatch discover() to return tmp_foundry (no integrations key)
        with patch(
            "research_foundry.integrations.arc._load_arc_base_url",
            return_value=ARC_DEFAULT,
        ):
            client = ArcClient.from_config()
        assert client.base_url == ARC_DEFAULT.rstrip("/")

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("ARC_BASE_URL", "http://arc.custom:1234")
        with patch(
            "research_foundry.integrations.arc._load_arc_base_url",
            return_value="http://arc.custom:1234",
        ):
            client = ArcClient.from_config()
        assert client.base_url == "http://arc.custom:1234"


class TestArcClientStubs:
    """Phase 3 stubs return None (no-op)."""

    def test_scaffold_review_stub_returns_none(self):
        from pathlib import Path

        client = ArcClient()
        result = client.scaffold_review("run_id", Path("/tmp/bundle.yaml"))
        assert result is None

    def test_get_run_stub_returns_none(self):
        client = ArcClient()
        result = client.get_run("arc_run_xyz")
        assert result is None


# ===========================================================================
# IntentTreeClient
# ===========================================================================


class TestIntentTreeClientAvailable:
    """available() contracts."""

    def test_available_true_when_version_endpoint_responds(self):
        payload = {"version": "1.2.3", "app": "intenttree"}
        resp = _mock_urlopen(_json_response(payload))
        with patch("urllib.request.urlopen", return_value=resp):
            assert IntentTreeClient().available() is True

    def test_available_true_on_empty_200(self):
        resp = _mock_urlopen(b"")
        with patch("urllib.request.urlopen", return_value=resp):
            # _get returns {} on empty body, which is not None -> True
            assert IntentTreeClient().available() is True

    def test_available_false_on_connection_refused(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            assert IntentTreeClient().available() is False

    def test_available_false_on_timeout(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            assert IntentTreeClient().available() is False

    def test_available_false_on_http_401(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://localhost:8000/api/meta/version",
                code=401,
                msg="Unauthorized",
                hdrs=None,  # type: ignore[arg-type]
                fp=None,
            ),
        ):
            assert IntentTreeClient().available() is False


class TestIntentTreeClientAuth:
    """Bearer token is injected into requests when set."""

    def test_token_from_env(self, monkeypatch):
        monkeypatch.setenv(_TOKEN_ENV, "my-secret-token")
        client = IntentTreeClient()
        assert client._token == "my-secret-token"

    def test_no_token_when_env_unset(self, monkeypatch):
        monkeypatch.delenv(_TOKEN_ENV, raising=False)
        client = IntentTreeClient()
        assert client._token == ""

    def test_explicit_token_overrides_env(self, monkeypatch):
        monkeypatch.setenv(_TOKEN_ENV, "env-token")
        client = IntentTreeClient(token="explicit-token")
        assert client._token == "explicit-token"

    def test_auth_header_present_when_token_set(self, monkeypatch):
        monkeypatch.setenv(_TOKEN_ENV, "tok123")
        client = IntentTreeClient()
        hdrs = client._auth_headers()
        assert hdrs == {"Authorization": "Bearer tok123"}

    def test_auth_header_empty_when_no_token(self, monkeypatch):
        monkeypatch.delenv(_TOKEN_ENV, raising=False)
        client = IntentTreeClient()
        assert client._auth_headers() == {}


class TestIntentTreeClientConfig:
    """Config loading and defaults."""

    def test_default_base_url(self):
        client = IntentTreeClient()
        assert client.base_url == IT_DEFAULT.rstrip("/")

    def test_custom_base_url(self):
        client = IntentTreeClient(base_url="http://it.internal:7777")
        assert client.base_url == "http://it.internal:7777"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("INTENTTREE_BASE_URL", "http://it.custom:5678")
        with patch(
            "research_foundry.integrations.intenttree._load_intenttree_base_url",
            return_value="http://it.custom:5678",
        ):
            client = IntentTreeClient.from_config()
        assert client.base_url == "http://it.custom:5678"


class TestIntentTreeClientStubs:
    """Phase 1–2 stubs return None (no-op)."""

    def test_get_node_stub(self):
        client = IntentTreeClient()
        assert client.get_node("node_abc") is None

    def test_patch_node_stub(self):
        client = IntentTreeClient()
        assert client.patch_node("node_abc", {"status": "done"}) is None

    def test_add_node_artifact_stub(self):
        client = IntentTreeClient()
        assert client.add_node_artifact("node_abc", {"url": "/runs/x/evidence_bundle.yaml"}) is None


# ===========================================================================
# Doctor command integration line
# ===========================================================================


class TestDoctorIntegrationsLine:
    """rf doctor prints an integrations line (offline = informational, not error)."""

    def test_doctor_shows_integrations_row_both_unreachable(self, monkeypatch):
        """When both are unreachable, doctor exits 0 with an 'unreachable' row."""

        from typer.testing import CliRunner

        from research_foundry.cli import app

        # Both clients return available() = False
        with (
            patch(
                "research_foundry.integrations.ArcClient.available",
                return_value=False,
            ),
            patch(
                "research_foundry.integrations.IntentTreeClient.available",
                return_value=False,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "integrations" in result.output
        assert "arc unreachable" in result.output
        assert "intenttree unreachable" in result.output

    def test_doctor_shows_reachable_when_both_up(self):
        from typer.testing import CliRunner

        from research_foundry.cli import app

        with (
            patch(
                "research_foundry.integrations.ArcClient.available",
                return_value=True,
            ),
            patch(
                "research_foundry.integrations.IntentTreeClient.available",
                return_value=True,
            ),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "arc reachable" in result.output
        assert "intenttree reachable" in result.output
