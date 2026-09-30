"""AC3: tainted Assertion/Report projection data cannot leave HTTP or MCP.

The real projectors are deliberately exercised behind each transport.  The
inverted controls below replace only their shared mediation chokepoint with an
identity function: if a future edit removes/misplaces that call, these tests
would expose the unique sentinel in the actual transport response.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers import knowledge as knowledge_router
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.knowledge_mcp import registry as mcp_registry
from research_foundry.knowledge_mcp.settings import KnowledgeMcpSettings
from research_foundry.paths import FoundryPaths
from research_foundry.services import builder_service, clearance
from research_foundry.services import knowledge_access as ka
from research_foundry.services.assertion_catalog import AssertionCatalog
from research_foundry.yamlio import dump_yaml
from tests.unit.test_assertion_catalog import _materialize

SENTINEL = "AC3-TAINTED-PROJECTOR-EGRESS-SENTINEL-7d934d"
WORKSPACE = "workspace-ac3-egress"


@pytest.fixture(autouse=True)
def _clean_projector_registry() -> Any:
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


def _stamp() -> dict[str, Any]:
    return clearance.stamp_taint(
        blocked_scopes=["redistribution"],
        stamped_by="ac3-surface-test",
        posture_at_stamp="dev_test",
        gate_refs=["DEF-1"],
    )


def _seed_tainted_records(paths: FoundryPaths) -> tuple[str, str]:
    """Persist one tainted assertion packet and one tainted report draft."""

    assertion_id = _materialize(paths, "rf_run_ac3_assertion", WORKSPACE, SENTINEL)
    catalog = AssertionCatalog(paths)
    catalog.rebuild(WORKSPACE)
    projection_path = catalog.projection_path(WORKSPACE)
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection["records"][0]["clearance"] = _stamp()
    projection_path.write_text(json.dumps(projection), encoding="utf-8")

    draft = builder_service.create_draft(
        paths, title=SENTINEL, sensitivity="public", blocks=[{"markdown": SENTINEL}]
    )
    draft["clearance"] = _stamp()
    dump_yaml(draft, paths.report_draft_dir(draft["report_draft_id"]) / "draft.yaml")
    return assertion_id, str(draft["report_draft_id"])


def _http_client(paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = create_app(FoundryConfig(paths=paths))
    app.dependency_overrides[get_paths] = lambda: paths
    monkeypatch.setattr(
        knowledge_router,
        "_identity_from_request",
        lambda _request: AuthIdentity("ac3", WORKSPACE, ("viewer",)),
    )
    return TestClient(app)


def _mcp_server(paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Build the real stdio tool registry with its assertion identity seam.

    Stdio intentionally has no caller identity in production, so assertion
    reads otherwise deny before reaching the projector.  Giving this test-only
    registry a workspace identity lets the same stdio tool exercise its egress
    gate, rather than falsely treating the local-trust denial as AC3 proof.
    """

    original_resolve_context = ka.resolve_context

    def _context_with_assertion_identity(
        foundry_paths: FoundryPaths, *, tool: str, identity: Any = None, **kwargs: Any
    ) -> ka.KnowledgeAccessContext:
        return original_resolve_context(
            foundry_paths,
            tool=tool,
            identity=AuthIdentity("ac3", WORKSPACE, ("viewer",)),
            **kwargs,
        )

    monkeypatch.setattr(ka, "resolve_context", _context_with_assertion_identity)
    return mcp_registry.build_server(
        KnowledgeMcpSettings(paths=paths, sensitivity_threshold_max=None, log_level="WARNING")
    )


def _identity_mediation(*_payloads: Any, **_kwargs: Any) -> None:
    """The deliberately unsafe control used to prove the assertions grip."""


def test_tainted_assertion_and_report_are_absent_from_http_responses(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    assertion_id, report_id = _seed_tainted_records(tmp_foundry)
    client = _http_client(tmp_foundry, monkeypatch)

    assertion = client.get(f"/api/knowledge/assertion/rfk:v1:assertion:{assertion_id}")
    report = client.get(f"/api/knowledge/report/rfk:v1:report_draft:{report_id}")

    assert assertion.status_code == report.status_code == 404
    assert SENTINEL not in assertion.text
    assert SENTINEL not in report.text


def test_tainted_assertion_and_report_are_absent_from_mcp_stdio_responses(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    assertion_id, report_id = _seed_tainted_records(tmp_foundry)
    server = _mcp_server(tmp_foundry, monkeypatch)

    assertion = asyncio.run(server.call_tool("rf_assertion_get", {"id": f"rfk:v1:assertion:{assertion_id}"}))
    report = asyncio.run(server.call_tool("rf_report_get", {"id": f"rfk:v1:report_draft:{report_id}"}))

    assert assertion.isError is report.isError is True
    assert SENTINEL not in assertion.content[0].text
    assert SENTINEL not in report.content[0].text


@pytest.mark.parametrize("surface", ["http", "mcp"])
def test_inverted_mediation_control_exposes_tainted_assertion_and_report(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, surface: str
) -> None:
    """Bypassing the exact projector chokepoint makes both sentinels escape."""

    assertion_id, report_id = _seed_tainted_records(tmp_foundry)
    monkeypatch.setattr(ka, "_mediate_knowledge_payloads", _identity_mediation)

    if surface == "http":
        client = _http_client(tmp_foundry, monkeypatch)
        assertion_text = client.get(
            f"/api/knowledge/assertion/rfk:v1:assertion:{assertion_id}"
        ).text
        report_text = client.get(f"/api/knowledge/report/rfk:v1:report_draft:{report_id}").text
    else:
        server = _mcp_server(tmp_foundry, monkeypatch)
        assertion_text = asyncio.run(
            server.call_tool("rf_assertion_get", {"id": f"rfk:v1:assertion:{assertion_id}"})
        ).content[0].text
        report_text = asyncio.run(
            server.call_tool("rf_report_get", {"id": f"rfk:v1:report_draft:{report_id}"})
        ).content[0].text

    assert SENTINEL in assertion_text
    assert SENTINEL in report_text
