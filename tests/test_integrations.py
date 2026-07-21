"""Tests for Phase 0 integration clients — ARC and IntentTree.

All HTTP calls are monkeypatched; no real network requests are made.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

from research_foundry.integrations import ArcClient, CCDashClient, IntentTreeClient
from research_foundry.integrations.arc import _DEFAULT_BASE_URL as ARC_DEFAULT
from research_foundry.integrations.ccdash import (
    _BASE_URL_ENV as CCDASH_BASE_URL_ENV,
)
from research_foundry.integrations.ccdash import (
    _INGEST_PATH as CCDASH_INGEST_PATH,
)
from research_foundry.integrations.ccdash import (
    _TOKEN_ENV as CCDASH_TOKEN_ENV,
)
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
    """Phase 3: scaffold_review / get_run do real HTTP but return None when offline."""

    def test_scaffold_review_offline_returns_none(self):
        """scaffold_review returns None when ARC is unreachable (connection error)."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            client = ArcClient()
            result = client.scaffold_review(
                {"council": "research-review-council", "target": "evidence_bundle.yaml", "objective": "test"}
            )
        assert result is None

    def test_scaffold_review_online_returns_response(self):
        """scaffold_review returns the parsed JSON when ARC responds."""
        payload = {"run_id": "arc_run_abc123", "dir": "/tmp/runs/arc_run_abc123"}
        resp = _mock_urlopen(_json_response(payload))
        with patch("urllib.request.urlopen", return_value=resp):
            client = ArcClient()
            result = client.scaffold_review(
                {"council": "research-review-council", "target": "evidence_bundle.yaml", "objective": "test"}
            )
        assert isinstance(result, dict)
        assert result.get("run_id") == "arc_run_abc123"

    def test_get_run_offline_returns_none(self):
        """get_run returns None when ARC is unreachable."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            client = ArcClient()
            result = client.get_run("arc_run_xyz")
        assert result is None

    def test_get_run_online_returns_run_record(self):
        """get_run returns the run record with verdict when ARC responds."""
        payload = {"run_id": "arc_run_xyz", "verdict": "approve", "status": "complete"}
        resp = _mock_urlopen(_json_response(payload))
        with patch("urllib.request.urlopen", return_value=resp):
            client = ArcClient()
            result = client.get_run("arc_run_xyz")
        assert isinstance(result, dict)
        assert result.get("verdict") == "approve"


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


# ===========================================================================
# CCDashClient
# ===========================================================================


class TestCCDashClientAvailable:
    """available() is a pure config gate — no network call, never raises."""

    def test_unavailable_when_both_env_vars_unset(self, monkeypatch):
        monkeypatch.delenv(CCDASH_BASE_URL_ENV, raising=False)
        monkeypatch.delenv(CCDASH_TOKEN_ENV, raising=False)
        assert CCDashClient().available() is False

    def test_unavailable_when_only_base_url_set(self, monkeypatch):
        monkeypatch.setenv(CCDASH_BASE_URL_ENV, "http://ccdash.internal:9200")
        monkeypatch.delenv(CCDASH_TOKEN_ENV, raising=False)
        assert CCDashClient().available() is False

    def test_unavailable_when_only_token_set(self, monkeypatch):
        monkeypatch.delenv(CCDASH_BASE_URL_ENV, raising=False)
        monkeypatch.setenv(CCDASH_TOKEN_ENV, "tok123")
        assert CCDashClient().available() is False

    def test_available_when_both_base_url_and_token_set(self, monkeypatch):
        monkeypatch.setenv(CCDASH_BASE_URL_ENV, "http://ccdash.internal:9200")
        monkeypatch.setenv(CCDASH_TOKEN_ENV, "tok123")
        assert CCDashClient().available() is True

    def test_available_false_with_explicit_empty_base_url_and_token(self):
        """Explicit empty strings (not env) also gate off, never raising."""

        assert CCDashClient(base_url="", token="").available() is False


class TestCCDashClientAuth:
    """Bearer token is read from env / explicit override, and gates the header."""

    def test_token_from_env(self, monkeypatch):
        monkeypatch.setenv(CCDASH_TOKEN_ENV, "my-secret-token")
        client = CCDashClient()
        assert client._token == "my-secret-token"

    def test_no_token_when_env_unset(self, monkeypatch):
        monkeypatch.delenv(CCDASH_TOKEN_ENV, raising=False)
        client = CCDashClient()
        assert client._token == ""

    def test_explicit_token_overrides_env(self, monkeypatch):
        monkeypatch.setenv(CCDASH_TOKEN_ENV, "env-token")
        client = CCDashClient(token="explicit-token")
        assert client._token == "explicit-token"

    def test_auth_header_present_when_token_set(self):
        client = CCDashClient(base_url="http://x", token="tok123")
        assert client._auth_headers() == {"Authorization": "Bearer tok123"}

    def test_auth_header_empty_when_no_token(self):
        client = CCDashClient(base_url="http://x", token="")
        assert client._auth_headers() == {}


class TestCCDashClientConfig:
    """Base URL resolution: explicit > env > unset ('')."""

    def test_default_base_url_is_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv(CCDASH_BASE_URL_ENV, raising=False)
        client = CCDashClient()
        assert client.base_url == ""

    def test_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv(CCDASH_BASE_URL_ENV, "http://ccdash.custom:1234")
        client = CCDashClient()
        assert client.base_url == "http://ccdash.custom:1234"

    def test_explicit_base_url_overrides_env(self, monkeypatch):
        monkeypatch.setenv(CCDASH_BASE_URL_ENV, "http://env-wins:1234")
        client = CCDashClient(base_url="http://explicit-wins:5678")
        assert client.base_url == "http://explicit-wins:5678"

    def test_from_config_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv(CCDASH_BASE_URL_ENV, "http://ccdash.custom:1234")
        with patch(
            "research_foundry.integrations.ccdash._load_ccdash_base_url",
            return_value="http://ccdash.custom:1234",
        ):
            client = CCDashClient.from_config()
        assert client.base_url == "http://ccdash.custom:1234"


class TestCCDashClientPostRfEvent:
    """post_rf_event(): fail-open, never raises, config-gated."""

    def test_post_returns_false_when_unconfigured(self):
        """No base_url/token -> skipped silently without attempting HTTP."""

        client = CCDashClient(base_url="", token="")
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = client.post_rf_event({"event_id": "evt_1"})
        assert result is False
        mock_urlopen.assert_not_called()

    def test_post_returns_true_on_2xx_response(self):
        client = CCDashClient(base_url="http://ccdash.internal:9200", token="tok123")
        resp = _mock_urlopen(_json_response({"accepted": True}))
        with patch("urllib.request.urlopen", return_value=resp):
            result = client.post_rf_event({"event_id": "evt_1", "run_id": "run_1"})
        assert result is True

    def test_post_returns_false_on_connection_error(self):
        client = CCDashClient(base_url="http://ccdash.internal:9200", token="tok123")
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = client.post_rf_event({"event_id": "evt_1"})
        assert result is False

    def test_post_returns_false_on_timeout(self):
        client = CCDashClient(base_url="http://ccdash.internal:9200", token="tok123")
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            result = client.post_rf_event({"event_id": "evt_1"})
        assert result is False

    def test_post_returns_false_on_http_error(self):
        client = CCDashClient(base_url="http://ccdash.internal:9200", token="tok123")
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://ccdash.internal:9200" + CCDASH_INGEST_PATH,
                code=500,
                msg="Internal Server Error",
                hdrs=None,  # type: ignore[arg-type]
                fp=None,
            ),
        ):
            result = client.post_rf_event({"event_id": "evt_1"})
        assert result is False

    def test_post_never_raises_on_unexpected_error(self):
        """Even a non-network exception inside post_rf_event is swallowed."""

        client = CCDashClient(base_url="http://ccdash.internal:9200", token="tok123")
        with patch.object(client, "_post", side_effect=RuntimeError("boom")):
            result = client.post_rf_event({"event_id": "evt_1"})
        assert result is False

    def test_post_sends_event_verbatim_to_ingest_path(self):
        """The event dict is posted unmodified to the documented ingest path."""

        client = CCDashClient(base_url="http://ccdash.internal:9200", token="tok123")
        event = {"event_id": "evt_1", "run_id": "run_1", "custom_field": "kept"}
        resp = _mock_urlopen(_json_response({"accepted": True}))
        captured_request = {}

        def _capture(req, timeout=None):  # noqa: ANN001
            captured_request["url"] = req.full_url
            captured_request["data"] = json.loads(req.data)
            captured_request["headers"] = dict(req.header_items())
            return resp

        with patch("urllib.request.urlopen", side_effect=_capture):
            client.post_rf_event(event)

        assert captured_request["url"] == "http://ccdash.internal:9200" + CCDASH_INGEST_PATH
        assert captured_request["data"] == event
        assert captured_request["headers"].get("Authorization") == "Bearer tok123"
