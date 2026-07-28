"""Cross-transport contract-equivalence gate for the RF Knowledge MCP
(AC KMCP-5, KMCP-6.7).

``tests/api/test_knowledge_api.py`` already proves 4-way ``rf_search``/
``rf_fetch`` parity on the ``run`` kind (its own KMCP-5.3/5.4 scope). THIS
file is the dedicated KMCP-6.7 "Parity gate" the plan names explicitly: ONE
normalized, shared fixture -- built exactly once per test -- proven equal
through all four transports (:class:`~research_foundry.services.
knowledge_access.KnowledgeAccessService`, the ``rf knowledge`` CLI, the
GET-only HTTP API, and the stdio MCP process), extended to the two legs that
file's own scope does not cover:

1. The FROZEN CORE tools (``search``/``fetch``) -- exact ``{id, title, url}``
   / ``{id, title, text, url}`` shapes, never exercised in 4-way form
   anywhere else.
2. One typed getter (``rf_source_get``) -- also never exercised in 4-way form
   anywhere else; the ``source`` kind additionally has no caller-identity
   requirement (unlike ``run``, which every other parity test in this repo
   already leans on for the same reason), giving this file its own distinct
   fixture rather than re-deriving the ``run`` one.

Byte-for-byte equality is proven after stripping the ONE receipt field that
legitimately varies between two calls against the same snapshot
(``receipt.generated_at`` -- KMCP-3.4's own documented exception), exactly
like ``tests/api/test_knowledge_api.py``'s own ``_normalize`` helper
(reimplemented here by value, not imported, so this file stays a standalone
KMCP-6.7 gate rather than depending on another phase's own test module).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.cli import app as rf_cli_app
from research_foundry.config import FoundryConfig
from research_foundry.knowledge_mcp import settings as kmcp_settings
from research_foundry.paths import FoundryPaths
from research_foundry.services import knowledge_access as ka

# Sibling test modules, imported by name for their fixture builders -- same
# convention every other Knowledge test module already uses.
from tests.unit.test_catalog_service import _write_threshold, build_catalog_run
from tests.unit.test_export_service import build_run
from tests.unit.test_knowledge_access import _set_run_yaml_fields

REPO_ROOT = Path(__file__).resolve().parents[2]

_RUNNER = CliRunner()


@pytest.fixture(autouse=True)
def _clean_projector_registry() -> Any:
    """Every test starts and ends with an empty projector registry -- mirrors
    every sibling Knowledge test module's own convention."""

    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


def _bootstrap_projectors(paths: FoundryPaths) -> None:
    """Seed every projector for the SERVICE leg only -- CLI/API/MCP each
    self-bootstrap on every call/request (KMCP-5.1/5.2/4.1's own
    ``_bootstrap_projectors``, reimplemented by value in each transport
    module); only a bare :class:`KnowledgeAccessService` call needs this
    done manually."""

    ka.register_projector("source", ka.SourceKindProjector(paths))
    ka.register_projector("assertion", ka.AssertionKindProjector(paths))
    ka.register_projector("report_draft", ka.ReportKindProjector(paths, target_kind="report_draft"))
    ka.register_projector("report_final", ka.ReportKindProjector(paths, target_kind="report_final"))
    ka.register_projector("run", ka.RunKindProjector(paths))


def _cli_invoke(tmp_foundry: FoundryPaths, args: list[str]) -> Any:
    """Run ``rf knowledge <args>`` from ``tmp_foundry.root`` (mirrors
    ``tests/api/test_knowledge_api.py``'s identically-named helper)."""

    import os

    prev = Path.cwd()
    os.chdir(tmp_foundry.root)
    try:
        return _RUNNER.invoke(rf_cli_app, ["knowledge", *args])
    finally:
        os.chdir(prev)


def _api_client(tmp_foundry: FoundryPaths) -> TestClient:
    """A live app bound to ``tmp_foundry``, no auth middleware installed --
    ``request.state.identity`` is absent, so this resolves the SAME
    local-trust ``None`` identity the CLI and MCP transports use
    unconditionally in v1."""

    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app)


def _mcp_structured_content(tmp_foundry: FoundryPaths, tool: str, arguments: dict[str, Any]) -> Any:
    """Call one stdio MCP tool end-to-end and return its ``structuredContent``.

    Skips (never fails) the calling test when the optional ``mcp`` extra is
    not installed."""

    pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")
    from research_foundry.knowledge_mcp import registry as kmcp_registry

    settings = kmcp_settings.KnowledgeMcpSettings(
        paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING"
    )
    server = kmcp_registry.build_server(settings)
    result = asyncio.run(server.call_tool(tool, arguments))
    return result.structuredContent


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy ``payload`` and drop the ONE receipt field that legitimately
    varies between two calls against the same snapshot (KMCP-3.4's
    ``generated_at``)."""

    normalized = json.loads(json.dumps(payload))
    receipt = normalized.get("receipt")
    if isinstance(receipt, dict):
        receipt.pop("generated_at", None)
    return normalized


# ===========================================================================
# One shared fixture, RF-extended search + fetch, across all four transports
# ===========================================================================


def test_one_shared_run_fixture_rf_search_parity_across_service_cli_api_mcp(
    tmp_foundry: FoundryPaths,
) -> None:
    """Build the fixture EXACTLY ONCE; call ``rf_search`` through all four
    transports against it; assert every normalized payload is identical."""

    run_id = "rf_run_parity_shared_search"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    query = "parity_shared_search"

    _bootstrap_projectors(tmp_foundry)
    service_payload = (
        ka.KnowledgeAccessService(tmp_foundry)
        .search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query=query, include_receipt=True)
        .to_dict()
    )

    cli_result = _cli_invoke(tmp_foundry, ["search", query])
    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)

    api_resp = _api_client(tmp_foundry).get("/api/knowledge/search", params={"query": query})
    assert api_resp.status_code == 200
    api_payload = api_resp.json()

    mcp_payload = _mcp_structured_content(tmp_foundry, "rf_search", {"query": query})

    normalized = [_normalize(p) for p in (service_payload, cli_payload, api_payload, mcp_payload)]
    assert len(normalized[0]["results"]) == 1
    assert normalized[0]["results"][0]["id"] == f"rfk:v1:run:{run_id}"
    service_n, cli_n, api_n, mcp_n = normalized
    assert service_n == cli_n == api_n == mcp_n


def test_one_shared_run_fixture_rf_fetch_parity_across_service_cli_api_mcp(
    tmp_foundry: FoundryPaths,
) -> None:
    """The SAME kind of shared-fixture equality, for ``rf_fetch`` instead of
    ``rf_search`` -- a distinct code path (``fetch_extended`` vs
    ``search_extended``/``_search``) that happens to touch the identical
    fixture record."""

    run_id = "rf_run_parity_shared_fetch"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    knowledge_id = f"rfk:v1:run:{run_id}"

    _bootstrap_projectors(tmp_foundry)
    service_payload = (
        ka.KnowledgeAccessService(tmp_foundry)
        .fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=knowledge_id, include_receipt=True
        )
        .to_dict()
    )

    cli_result = _cli_invoke(tmp_foundry, ["fetch", knowledge_id])
    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/fetch/{knowledge_id}")
    assert api_resp.status_code == 200
    api_payload = api_resp.json()

    mcp_payload = _mcp_structured_content(tmp_foundry, "rf_fetch", {"id": knowledge_id})

    normalized = [_normalize(p) for p in (service_payload, cli_payload, api_payload, mcp_payload)]
    assert normalized[0]["id"] == knowledge_id
    service_n, cli_n, api_n, mcp_n = normalized
    assert service_n == cli_n == api_n == mcp_n


# ===========================================================================
# Frozen CORE tools (search/fetch) -- exact {id,title,url} / {id,title,text,
# url} shapes, never exercised in 4-way form anywhere else in this repo
# ===========================================================================


def test_core_search_parity_across_service_cli_api_mcp(tmp_foundry: FoundryPaths) -> None:
    """The CLI has no core ``search``/``fetch`` equivalent (KMCP-5.1's own
    module docstring: "CLI never exposes the frozen core search/fetch tool
    names at all") -- this is a THREE-way parity gate (service/API/MCP), not
    four, and asserts that gap explicitly rather than silently narrowing the
    comparison."""

    run_id = "rf_run_parity_core_search"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    query = "parity_core_search"

    _bootstrap_projectors(tmp_foundry)
    service_payload = (
        ka.KnowledgeAccessService(tmp_foundry)
        .search_core(ka.resolve_context(tmp_foundry, tool="search"), query=query)
        .to_dict()
    )

    from research_foundry.cli.commands import knowledge as knowledge_cli_module

    assert not hasattr(knowledge_cli_module, "search_core")  # no CLI core-search command exists

    api_resp = _api_client(tmp_foundry).get("/api/knowledge/v1/search", params={"query": query})
    assert api_resp.status_code == 200
    api_payload = api_resp.json()

    mcp_payload = _mcp_structured_content(tmp_foundry, "search", {"query": query})

    assert set(service_payload) == {"results"}
    assert service_payload == api_payload == mcp_payload
    assert len(service_payload["results"]) == 1
    assert set(service_payload["results"][0]) == {"id", "title", "url"}


def test_core_fetch_parity_across_service_api_mcp(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_parity_core_fetch"
    build_run(tmp_foundry, run_id)
    _set_run_yaml_fields(tmp_foundry, run_id, sensitivity="public")
    knowledge_id = f"rfk:v1:run:{run_id}"

    _bootstrap_projectors(tmp_foundry)
    service_payload = (
        ka.KnowledgeAccessService(tmp_foundry)
        .fetch_core(ka.resolve_context(tmp_foundry, tool="fetch"), knowledge_id=knowledge_id)
        .to_dict()
    )

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/v1/fetch/{knowledge_id}")
    assert api_resp.status_code == 200
    api_payload = api_resp.json()

    mcp_payload = _mcp_structured_content(tmp_foundry, "fetch", {"id": knowledge_id})

    assert set(service_payload) <= {"id", "title", "text", "url", "metadata"}
    assert service_payload == api_payload == mcp_payload

    # The core fetch's own `url` is the literal local-resource-URL contract
    # route -- resolves back through the SAME core fetch route on this API.
    path = urlsplit(service_payload["url"]).path
    assert path == f"/api/knowledge/v1/fetch/{knowledge_id.replace(':', '%3A')}"


# ===========================================================================
# One typed getter (rf_source_get) -- also never exercised in 4-way form
# anywhere else; `source` needs no caller identity, unlike `run`, so this
# uses its own distinct fixture rather than re-deriving the run one above.
# ===========================================================================


def test_typed_getter_rf_source_get_parity_across_service_cli_api_mcp(tmp_foundry: FoundryPaths) -> None:
    from research_foundry.services import catalog_service as catalog_svc

    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")
    knowledge_id = f"rfk:v1:source:{item_id}"

    _bootstrap_projectors(tmp_foundry)
    service_payload = (
        ka.KnowledgeAccessService(tmp_foundry)
        .fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_source_get"),
            knowledge_id=knowledge_id,
            include_receipt=True,
        )
        .to_dict()
    )

    cli_result = _cli_invoke(tmp_foundry, ["source-get", knowledge_id])
    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)

    api_resp = _api_client(tmp_foundry).get(f"/api/knowledge/source/{knowledge_id}")
    assert api_resp.status_code == 200
    api_payload = api_resp.json()

    mcp_payload = _mcp_structured_content(tmp_foundry, "rf_source_get", {"id": knowledge_id})

    normalized = [_normalize(p) for p in (service_payload, cli_payload, api_payload, mcp_payload)]
    assert normalized[0]["kind"] == "source"
    assert normalized[0]["id"] == knowledge_id
    service_n, cli_n, api_n, mcp_n = normalized
    assert service_n == cli_n == api_n == mcp_n


__all__: list[str] = []
