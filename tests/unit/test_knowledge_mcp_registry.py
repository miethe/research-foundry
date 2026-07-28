"""Unit tests for `rf-knowledge-mcp`'s tool registry (KMCP-4.1/4.2).

OFFLINE-ONLY: the whole module is skipped (not failed) when the optional
``mcp`` extra is not installed -- ``build_server()`` is the only function in
``registry.py`` that touches it (see
``tests/test_knowledge_mcp_offline_import.py`` for that separate,
never-skipped contract).

Covers the CORE ``search``/``fetch`` tools specifically (KMCP-4.1/4.2): the
stdio-only transport guard (invariant 8), the KMCP-1.3 dual-encoding contract
against the frozen P1 schemas, the KMCP-OQ-1/decisions-block §0 "safe
denial" contract (empty results for search, one generic tool error for
fetch), and that :func:`build_server` actually wires the P3 domain
projectors so the core tools resolve real content end to end. The six
RF-extended tools (KMCP-4.3 "Part B") are now also registered by
:func:`build_server` -- see ``tests/test_knowledge_mcp_process.py``
(KMCP-4.4) for the exact eight-tool inventory snapshot and the full
process/import/environment/transport negative-space guard; this file stays
scoped to the two core tools' own behavior.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

from research_foundry.knowledge_mcp import registry  # noqa: E402
from research_foundry.knowledge_mcp.settings import KnowledgeMcpSettings  # noqa: E402
from research_foundry.paths import FoundryPaths  # noqa: E402
from research_foundry.schemas import SchemaRegistry  # noqa: E402
from research_foundry.services import catalog_service as catalog_svc  # noqa: E402
from research_foundry.services import knowledge_access as ka  # noqa: E402
from tests.unit.test_catalog_service import _write_threshold, build_catalog_run  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_projector_registry() -> Any:
    """Every test starts and ends with an empty projector registry -- mirrors
    ``tests/unit/test_knowledge_access.py``'s own fixture of the same name."""

    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


@pytest.fixture()
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry()


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    return asyncio.run(server.call_tool(name, arguments))


def _seeded_settings(tmp_foundry: FoundryPaths, **overrides: Any) -> tuple[KnowledgeMcpSettings, str]:
    """Seed a real, eligible ``source`` catalog item and return
    ``(settings, item_id)`` for tests that need genuine end-to-end content."""

    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")
    settings = KnowledgeMcpSettings(
        paths=tmp_foundry,
        sensitivity_threshold_max=overrides.get("sensitivity_threshold_max"),
        log_level="WARNING",
    )
    return settings, item_id


# ---------------------------------------------------------------------------
# Exact "Part A" tool inventory
# ---------------------------------------------------------------------------


def test_registers_core_tools(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert {"search", "fetch"} <= names
    assert registry.CORE_TOOL_NAMES == ka.CORE_TOOL_NAMES == ("search", "fetch")


def test_rf_extended_tools_are_also_registered(tmp_foundry: FoundryPaths) -> None:
    """KMCP-4.3 ("Part B") registers the six RF-extended tools alongside the
    two core ones -- see ``tests/test_knowledge_mcp_process.py`` for the
    exact eight-tool inventory snapshot."""

    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    names = {t.name for t in asyncio.run(server.list_tools())}
    for expected in ka.RF_TOOL_NAMES:
        assert expected in names


def test_core_tool_input_schemas_are_closed_and_exact(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}

    assert set(tools["search"].inputSchema["properties"]) == {"query"}
    assert tools["search"].inputSchema["required"] == ["query"]
    assert tools["search"].inputSchema["additionalProperties"] is False

    assert set(tools["fetch"].inputSchema["properties"]) == {"id"}
    assert tools["fetch"].inputSchema["required"] == ["id"]
    assert tools["fetch"].inputSchema["additionalProperties"] is False


# ---------------------------------------------------------------------------
# Stdio-only transport guard (invariant 8)
# ---------------------------------------------------------------------------


def test_transport_guard_allows_stdio(tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp.server.fastmcp import FastMCP

    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    monkeypatch.setattr(FastMCP, "run", lambda self, transport=None, mount_path=None: None)
    server.run()  # default
    server.run(transport="stdio")  # explicit


def test_transport_guard_rejects_sse(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    with pytest.raises(registry.UnsupportedTransportError):
        server.run(transport="sse")


def test_transport_guard_rejects_streamable_http(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    with pytest.raises(registry.UnsupportedTransportError):
        server.run(transport="streamable-http")


def test_transport_guard_blocks_sse_app_directly(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    with pytest.raises(registry.UnsupportedTransportError):
        server.sse_app()


def test_transport_guard_blocks_streamable_http_app_directly(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    with pytest.raises(registry.UnsupportedTransportError):
        server.streamable_http_app()


def test_transport_guard_server_is_a_genuine_fastmcp_subclass(tmp_foundry: FoundryPaths) -> None:
    """Same closed generation-4 shape as `search_router.mcp_launcher`'s own
    guard (module docstring) -- no bound-method ``__self__`` bypass exists
    because there is only one object."""

    from mcp.server.fastmcp import FastMCP

    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    assert isinstance(server, FastMCP)
    assert server.list_tools.__self__ is server


# ---------------------------------------------------------------------------
# KMCP-1.3 dual encoding + schema round-trip
# ---------------------------------------------------------------------------


def test_search_result_dual_encodes_and_matches_schema(
    tmp_foundry: FoundryPaths, schema_registry: SchemaRegistry
) -> None:
    settings, _item_id = _seeded_settings(tmp_foundry)
    server = registry.build_server(settings)

    result = _call(server, "search", {"query": "alpha"})
    assert result.isError is False
    assert len(result.content) == 1
    assert result.content[0].type == "text"

    parsed_text = json.loads(result.content[0].text)
    assert parsed_text == result.structuredContent

    validation = schema_registry.validate(result.structuredContent, "knowledge_search_response")
    assert validation.ok, validation.errors
    assert len(result.structuredContent["results"]) >= 1
    item = result.structuredContent["results"][0]
    assert set(item) == {"id", "title", "url"}


def test_search_empty_results_matches_schema(
    tmp_foundry: FoundryPaths, schema_registry: SchemaRegistry
) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)

    result = _call(server, "search", {"query": "zzz_nothing_matches_zzz"})
    assert result.isError is False
    assert result.structuredContent == {"results": []}
    assert json.loads(result.content[0].text) == {"results": []}

    validation = schema_registry.validate(result.structuredContent, "knowledge_search_response")
    assert validation.ok, validation.errors


def test_fetch_document_dual_encodes_and_matches_schema(
    tmp_foundry: FoundryPaths, schema_registry: SchemaRegistry
) -> None:
    settings, item_id = _seeded_settings(tmp_foundry)
    server = registry.build_server(settings)

    result = _call(server, "fetch", {"id": f"rfk:v1:source:{item_id}"})
    assert result.isError is False
    parsed_text = json.loads(result.content[0].text)
    assert parsed_text == result.structuredContent

    validation = schema_registry.validate(result.structuredContent, "knowledge_document")
    assert validation.ok, validation.errors
    assert set(result.structuredContent) <= {"id", "title", "text", "url", "metadata"}
    assert "ALPHA QUOTE" in result.structuredContent["text"]


# ---------------------------------------------------------------------------
# Safe denial (decisions-block §0/§3 Risk 2, KMCP-OQ-1)
# ---------------------------------------------------------------------------


def test_fetch_malformed_id_returns_single_generic_error(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)

    result = _call(server, "fetch", {"id": "not-a-valid-knowledge-id"})
    assert result.isError is True
    assert len(result.content) == 1
    assert result.content[0].text == registry._FETCH_DENIED_MESSAGE
    assert "malformed" not in result.content[0].text
    assert result.structuredContent is None


def test_fetch_unknown_but_well_formed_id_returns_same_generic_error(tmp_foundry: FoundryPaths) -> None:
    """A genuinely-absent id and a hidden/denied one must be
    indistinguishable to the caller (KMCP-OQ-1) -- both produce the SAME
    message as the malformed-id case above."""

    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)

    result = _call(server, "fetch", {"id": "rfk:v1:source:does-not-exist"})
    assert result.isError is True
    assert result.content[0].text == registry._FETCH_DENIED_MESSAGE


def test_fetch_above_ceiling_denies_generically_not_visibly(tmp_foundry: FoundryPaths) -> None:
    """A real, existing item whose sensitivity exceeds this process's
    configured ceiling denies with the SAME generic message -- never a
    distinct "too sensitive" signal."""

    settings, item_id = _seeded_settings(tmp_foundry, sensitivity_threshold_max="public")
    server = registry.build_server(settings)

    result = _call(server, "fetch", {"id": f"rfk:v1:source:{item_id}"})
    assert result.isError is True
    assert result.content[0].text == registry._FETCH_DENIED_MESSAGE


def test_search_ignores_extra_argument_values_silently(tmp_foundry: FoundryPaths) -> None:
    """An unrecognized property is never widened into capability -- it is
    simply not delivered to the tool function (SDK-level `extra='ignore'`
    behavior); the advertised schema still declares the root closed (see
    ``test_core_tool_input_schemas_are_closed_and_exact``)."""

    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    server = registry.build_server(settings)
    result = _call(server, "search", {"query": "alpha", "kinds": ["run"]})
    assert result.isError is False


# ---------------------------------------------------------------------------
# Process bootstrap wires the P3 domain projectors (KMCP-4.1)
# ---------------------------------------------------------------------------


def test_build_server_registers_all_five_domain_projectors(tmp_foundry: FoundryPaths) -> None:
    settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    registry.build_server(settings)
    assert ka.registered_kinds() == ka.KNOWLEDGE_KINDS
