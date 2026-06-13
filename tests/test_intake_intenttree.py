"""Tests for Phase 2 IntentTree inbound intake.

Covers:
- get_node: real GET /api/nodes/{node_id}?include=artifacts,edges (mock HTTP)
- get_node: fail-soft returns None on any error
- intake_from_intenttree: online path — mock get_node returns node → raw_idea +
  intent created; attachments carried; intent.intenttree_node_ref == source node_id
- intake_from_intenttree: offline --from-file path
- intake_from_intenttree: --plan creates a run
- intake_from_intenttree: missing node (server unreachable, no file) raises RFError
- intake_from_intenttree: missing node file raises NotFoundError
- CLI: rf intake intenttree command wiring
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from research_foundry.errors import NotFoundError, RFError
from research_foundry.integrations.intenttree import IntentTreeClient
from research_foundry.paths import FoundryPaths
from research_foundry.services.intake import IntakeResult, intake_from_intenttree
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Sample node fixture
# ---------------------------------------------------------------------------

_SAMPLE_NODE: dict[str, Any] = {
    "node_id": "node_research_agentic_sys",
    "title": "Research Agentic Systems",
    "level": "L4",
    "status": "ready",
    "priority": "high",
    "body": (
        "Investigate how agentic research workflows handle evidence bundles "
        "and claim traceability. Focus on cheap-extraction vs deep-synthesis split."
    ),
    "links": [
        {
            "type": "url",
            "url": "https://meatywiki.example.com/notes/agentic-research",
            "label": "MeatyWiki: Agentic Research",
        },
        {
            "url": "https://arxiv.org/abs/2401.12345",
            "label": "Related paper",
        },
    ],
    "artifacts": [
        {
            "type": "evidence_bundle",
            "path": "runs/rf_run_prior/evidence_bundle.yaml",
        }
    ],
    "intent_id": "intent_research_agentic_sys",
}


def _make_urlopen_mock(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ===========================================================================
# IntentTreeClient.get_node (Phase 2 implementation)
# ===========================================================================


class TestGetNode:
    """get_node sends GET /api/nodes/{node_id}?include=... and returns the record."""

    def test_get_node_returns_record_on_success(self):
        resp = _make_urlopen_mock(_SAMPLE_NODE)
        with patch("urllib.request.urlopen", return_value=resp):
            client = IntentTreeClient(base_url="http://it.test")
            result = client.get_node("node_research_agentic_sys")

        assert result is not None
        assert result["node_id"] == "node_research_agentic_sys"

    def test_get_node_sends_include_query_param(self):
        """URL must contain ?include=artifacts,edges."""
        captured = []

        def fake_urlopen(req, timeout=None):
            captured.append(req.get_full_url())
            resp = MagicMock()
            resp.read.return_value = json.dumps({"node_id": "n1"}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client = IntentTreeClient(base_url="http://it.test")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.get_node("n1")

        assert len(captured) == 1
        assert "include=artifacts,edges" in captured[0]
        assert "/api/nodes/n1" in captured[0]

    def test_get_node_sends_custom_include(self):
        captured = []

        def fake_urlopen(req, timeout=None):
            captured.append(req.get_full_url())
            resp = MagicMock()
            resp.read.return_value = json.dumps({"node_id": "n2"}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client = IntentTreeClient(base_url="http://it.test")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.get_node("n2", include="artifacts")

        assert "include=artifacts" in captured[0]

    def test_get_node_returns_none_on_connection_error(self):
        import urllib.error

        client = IntentTreeClient()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = client.get_node("node_xyz")
        assert result is None

    def test_get_node_returns_none_on_timeout(self):
        client = IntentTreeClient()
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            result = client.get_node("node_xyz")
        assert result is None

    def test_get_node_returns_none_on_http_error(self):
        import urllib.error

        client = IntentTreeClient()
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://localhost:8000/api/nodes/n1",
                code=404,
                msg="Not Found",
                hdrs=None,  # type: ignore[arg-type]
                fp=None,
            ),
        ):
            result = client.get_node("n1")
        assert result is None

    def test_get_node_sends_auth_header_when_token_set(self, monkeypatch):
        monkeypatch.setenv("INTENTTREE_API_TOKEN", "bearer-tok-xyz")
        captured_headers: list[dict] = []

        def fake_urlopen(req, timeout=None):
            captured_headers.append(dict(req.headers))
            resp = MagicMock()
            resp.read.return_value = json.dumps({"node_id": "n3"}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client = IntentTreeClient(base_url="http://it.test")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.get_node("n3")

        assert len(captured_headers) == 1
        # urllib capitalizes header name
        auth = captured_headers[0].get("Authorization") or captured_headers[0].get("authorization")
        assert auth == "Bearer bearer-tok-xyz"


# ===========================================================================
# intake_from_intenttree: online path
# ===========================================================================


class TestIntakeOnline:
    """Online path: mock get_node returns a node → artifacts created."""

    def test_online_creates_raw_idea_and_intent(self, tmp_foundry: FoundryPaths):
        with (
            patch(
                "research_foundry.services.intake._fetch_node_online",
                return_value=_SAMPLE_NODE,
            ),
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                sensitivity="personal",
                paths=tmp_foundry,
            )

        assert result.node_id == "node_research_agentic_sys"
        assert result.raw_idea_id
        assert result.raw_idea_path and result.raw_idea_path.exists()
        assert result.intent_id
        assert result.intent_path and result.intent_path.exists()
        assert result.run_id is None  # do_plan=False (default)

    def test_online_intent_node_ref_is_source_node_id(self, tmp_foundry: FoundryPaths):
        """The intent's intenttree_node_ref must equal the source node_id."""
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=_SAMPLE_NODE,
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                paths=tmp_foundry,
            )

        intent = load_yaml(result.intent_path)
        assert isinstance(intent, dict)
        assert intent.get("intenttree_node_ref") == "node_research_agentic_sys"

    def test_online_attachments_are_carried_from_links(self, tmp_foundry: FoundryPaths):
        """Links + artifacts in the node become attachments on the raw idea."""
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=_SAMPLE_NODE,
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                paths=tmp_foundry,
            )

        from research_foundry.frontmatter import load_md

        meta, _ = load_md(result.raw_idea_path)
        attachments = meta.get("attachments") or []
        assert len(attachments) > 0
        uris = [a["path_or_uri"] for a in attachments]
        assert any("meatywiki" in u for u in uris)
        # All attachments must carry the source tag
        for att in attachments:
            assert att["source"] == f"intenttree:node_research_agentic_sys"

    def test_online_captured_from_is_intenttree(self, tmp_foundry: FoundryPaths):
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=_SAMPLE_NODE,
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                paths=tmp_foundry,
            )

        from research_foundry.frontmatter import load_md

        meta, _ = load_md(result.raw_idea_path)
        assert meta.get("captured_from") == "intenttree"

    def test_online_sensitivity_flows_into_intent(self, tmp_foundry: FoundryPaths):
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=_SAMPLE_NODE,
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                sensitivity="work_sensitive",
                paths=tmp_foundry,
            )

        intent = load_yaml(result.intent_path)
        assert isinstance(intent, dict)
        gov = intent.get("governance") or {}
        assert gov.get("sensitivity") == "work_sensitive"

    def test_online_node_with_no_links_still_works(self, tmp_foundry: FoundryPaths):
        """Nodes without links/artifacts should still produce raw_idea + intent."""
        minimal_node: dict[str, Any] = {
            "node_id": "node_minimal",
            "title": "Minimal research node",
            "body": "A minimal node with no links.",
        }
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=minimal_node,
        ):
            result = intake_from_intenttree("node_minimal", paths=tmp_foundry)

        assert result.raw_idea_id
        assert result.intent_id
        intent = load_yaml(result.intent_path)
        assert intent.get("intenttree_node_ref") == "node_minimal"


# ===========================================================================
# intake_from_intenttree: offline / from_file
# ===========================================================================


class TestIntakeOffline:
    """Offline path: --from-file loads node from a local YAML file."""

    def test_offline_from_file_creates_artifacts(
        self, tmp_foundry: FoundryPaths, tmp_path: Path
    ):
        node_file = tmp_path / "node.yaml"
        dump_yaml(_SAMPLE_NODE, node_file)

        result = intake_from_intenttree(
            "node_research_agentic_sys",
            from_file=node_file,
            paths=tmp_foundry,
        )

        assert result.raw_idea_id
        assert result.intent_id
        assert result.raw_idea_path and result.raw_idea_path.exists()
        assert result.intent_path and result.intent_path.exists()

    def test_offline_intent_node_ref_is_source_node_id(
        self, tmp_foundry: FoundryPaths, tmp_path: Path
    ):
        node_file = tmp_path / "node.yaml"
        dump_yaml(_SAMPLE_NODE, node_file)

        result = intake_from_intenttree(
            "node_research_agentic_sys",
            from_file=node_file,
            paths=tmp_foundry,
        )

        intent = load_yaml(result.intent_path)
        assert intent.get("intenttree_node_ref") == "node_research_agentic_sys"

    def test_offline_does_not_hit_server(
        self, tmp_foundry: FoundryPaths, tmp_path: Path
    ):
        """With from_file, no live HTTP should be attempted."""
        node_file = tmp_path / "node.yaml"
        dump_yaml(_SAMPLE_NODE, node_file)

        with patch(
            "research_foundry.services.intake._fetch_node_online",
        ) as mock_fetch:
            intake_from_intenttree(
                "node_research_agentic_sys",
                from_file=node_file,
                paths=tmp_foundry,
            )

        mock_fetch.assert_not_called()

    def test_offline_missing_file_raises_not_found_error(
        self, tmp_foundry: FoundryPaths, tmp_path: Path
    ):
        missing = tmp_path / "does_not_exist.yaml"

        with pytest.raises(NotFoundError, match="offline node file not found"):
            intake_from_intenttree(
                "node_xyz",
                from_file=missing,
                paths=tmp_foundry,
            )


# ===========================================================================
# intake_from_intenttree: do_plan=True
# ===========================================================================


class TestIntakeWithPlan:
    """--plan creates a run after triage."""

    def test_do_plan_creates_run(self, tmp_foundry: FoundryPaths):
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=_SAMPLE_NODE,
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                do_plan=True,
                paths=tmp_foundry,
            )

        assert result.run_id is not None
        assert result.run_dir is not None
        assert result.run_dir.exists()

    def test_no_plan_by_default(self, tmp_foundry: FoundryPaths):
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=_SAMPLE_NODE,
        ):
            result = intake_from_intenttree(
                "node_research_agentic_sys",
                paths=tmp_foundry,
            )

        assert result.run_id is None
        assert result.run_dir is None


# ===========================================================================
# intake_from_intenttree: error cases
# ===========================================================================


class TestIntakeMissingNode:
    """When neither live server nor from_file yields a node, RFError is raised."""

    def test_server_unreachable_no_file_raises_rf_error(self, tmp_foundry: FoundryPaths):
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=None,
        ):
            with pytest.raises(RFError, match="could not be sourced"):
                intake_from_intenttree("node_missing_xyz", paths=tmp_foundry)

    def test_rf_error_message_contains_node_id(self, tmp_foundry: FoundryPaths):
        with patch(
            "research_foundry.services.intake._fetch_node_online",
            return_value=None,
        ):
            with pytest.raises(RFError) as exc_info:
                intake_from_intenttree("node_specific_id_abc", paths=tmp_foundry)
        assert "node_specific_id_abc" in str(exc_info.value)


# ===========================================================================
# CLI: rf intake intenttree
# ===========================================================================


class TestIntakeCLI:
    """CLI wiring: rf intake intenttree <node_id> [--from-file] [--plan]."""

    def test_cli_intake_intenttree_success(self, tmp_foundry: FoundryPaths):
        from typer.testing import CliRunner

        from research_foundry.cli import app

        fake_result = IntakeResult(
            node_id="node_abc",
            raw_idea_id="raw_idea_abc_123",
            intent_id="intent_abc_123",
            run_id=None,
            raw_idea_path=tmp_foundry.raw_ideas / "raw_idea_abc_123.md",
            intent_path=tmp_foundry.intents_active / "intent_abc_123.yaml",
            run_dir=None,
        )

        with (
            patch("research_foundry.services.intake.intake_from_intenttree", return_value=fake_result),
            patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["intake", "intenttree", "node_abc"])

        assert result.exit_code == 0
        assert "node_abc" in result.output
        assert "raw_idea=raw_idea_abc_123" in result.output
        assert "intent=intent_abc_123" in result.output

    def test_cli_intake_intenttree_with_plan(self, tmp_foundry: FoundryPaths):
        from typer.testing import CliRunner

        from research_foundry.cli import app

        fake_result = IntakeResult(
            node_id="node_plan",
            raw_idea_id="raw_idea_plan",
            intent_id="intent_plan",
            run_id="rf_run_plan",
            raw_idea_path=tmp_foundry.raw_ideas / "raw_idea_plan.md",
            intent_path=tmp_foundry.intents_active / "intent_plan.yaml",
            run_dir=tmp_foundry.runs / "rf_run_plan",
        )

        with (
            patch("research_foundry.services.intake.intake_from_intenttree", return_value=fake_result),
            patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["intake", "intenttree", "node_plan", "--plan"])

        assert result.exit_code == 0
        assert "run=rf_run_plan" in result.output

    def test_cli_intake_intenttree_rf_error_exits_nonzero(self, tmp_foundry: FoundryPaths):
        from typer.testing import CliRunner

        from research_foundry.cli import app

        with (
            patch(
                "research_foundry.services.intake.intake_from_intenttree",
                side_effect=RFError("node could not be sourced: server is unreachable"),
            ),
            patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["intake", "intenttree", "node_missing"])

        assert result.exit_code != 0

    def test_cli_intake_intenttree_from_file_option(
        self, tmp_foundry: FoundryPaths, tmp_path: Path
    ):
        """Smoke-test: --from-file is forwarded to the service."""
        from typer.testing import CliRunner

        from research_foundry.cli import app

        node_file = tmp_path / "offline_node.yaml"
        dump_yaml(_SAMPLE_NODE, node_file)

        with patch("research_foundry.paths.FoundryPaths.discover", return_value=tmp_foundry):
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "intake",
                    "intenttree",
                    "node_research_agentic_sys",
                    "--from-file",
                    str(node_file),
                ],
            )

        # Should succeed (from_file path is valid)
        assert result.exit_code == 0
        assert "node_research_agentic_sys" in result.output
