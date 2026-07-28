"""Process/tool/inventory gate for `rf-knowledge-mcp` (KMCP-4.4).

The authoritative "separate-process inventory" snapshot for the FULL,
eight-tool `rf-knowledge-mcp` server (Parts A + B, KMCP-4.1/4.2/4.3). Where
``tests/unit/test_knowledge_mcp_registry.py`` stays scoped to the two CORE
tools' own dual-encoding/denial behavior, and
``tests/test_knowledge_mcp_offline_import.py`` proves the module-level
offline-safe-import contract unconditionally (no ``mcp`` SDK required),
THIS file proves, against the fully-built, eight-tool server:

1. The exact eight-tool inventory (decisions-block §9.2) -- and that no
   Search-Router-native, acquisition/writeback/mutator-shaped, or otherwise
   forbidden tool name is ever present.
2. The process/registry/settings import graph is an explicit ALLOWLIST (not
   only a denylist over a few forbidden package names) -- every absolute
   import resolves under a small, declared dependency surface.
3. The settings/environment view stays exhaustive and minimal, and a
   poisoned process environment (Search Router / Operator / writeback
   credentials) never leaks into any of the eight tools' output.
4. Streamable HTTP / SSE / OAuth / non-loopback listener options are ABSENT
   from the fully-built server -- stdio is the only enforced transport
   (invariant 8).
5. KMCP-1.3 dual encoding (``content[0].text`` deep-equals
   ``structuredContent``) holds across every tool, not only the two core
   ones.
6. The core `FetchDTO`'s optional `metadata` slot: the ABSENT case (this
   v1 implementation never itself populates it) and the PRESENT case (the
   schema's own arbitrary-keys contract) are both covered.
7. Zero write-surface/provider calls occur across all eight tools, exercised
   together with real, seeded content across all five knowledge kinds.
8. Every typed getter's kind-scoping denies generically for a wrong-kind id
   and resolves correctly for a matching one; `rf_assertion_get` denies
   generically for EVERY id under this process's local-trust identity
   model (expected v1 behavior -- see `registry.py`'s module docstring).
9. No unqualified OpenAI/ChatGPT (or other hosted-client) compatibility
   claim appears anywhere in this package's own source or in any
   registered tool's advertised description (decisions-block §10).
10. The packaged entry point (`process.main`) wires settings -> server ->
    stdio `run()` correctly, and `pyproject.toml` declares the dedicated
    `rf-knowledge-mcp` script distinct from the Search Router's `rf-mcp`.

OFFLINE-ONLY for every test that needs a real, built `FastMCP` server: the
whole module is skipped (not failed) when the optional ``mcp`` extra is not
installed, mirroring every other MCP test module's own convention.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

import research_foundry.knowledge_mcp as knowledge_mcp_pkg  # noqa: E402
from research_foundry.knowledge_mcp import process, registry  # noqa: E402
from research_foundry.knowledge_mcp import settings as kmcp_settings  # noqa: E402
from research_foundry.knowledge_mcp.settings import KnowledgeMcpSettings  # noqa: E402
from research_foundry.paths import FoundryPaths  # noqa: E402
from research_foundry.schemas import SchemaRegistry  # noqa: E402
from research_foundry.services import builder_service  # noqa: E402
from research_foundry.services import catalog_service as catalog_svc  # noqa: E402
from research_foundry.services import knowledge_access as ka  # noqa: E402
from research_foundry.services.assertion_catalog import AssertionCatalog  # noqa: E402

# Sibling test modules, imported by name for their fixture builders/helpers --
# same convention ``tests/unit/test_knowledge_access.py`` and
# ``tests/unit/test_knowledge_mcp_registry.py`` already use.
from tests.unit.test_assertion_catalog import _materialize  # noqa: E402
from tests.unit.test_catalog_service import _write_threshold, build_catalog_run  # noqa: E402
from tests.unit.test_export_service import build_run  # noqa: E402
from tests.unit.test_knowledge_access import (  # noqa: E402
    _install_write_surface_spies,
    _publish_draft,
    _snapshot_tree,
)


@pytest.fixture(autouse=True)
def _clean_projector_registry() -> Any:
    """Every test starts and ends with an empty projector registry -- each
    test's own `registry.build_server()` call re-registers fresh projectors
    bound to its own `tmp_foundry`, but this mirrors every sibling Knowledge
    test module's own convention rather than relying on that overwrite."""

    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


@pytest.fixture()
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry()


def _build(tmp_foundry: FoundryPaths, **overrides: Any) -> Any:
    settings = KnowledgeMcpSettings(
        paths=tmp_foundry,
        sensitivity_threshold_max=overrides.get("sensitivity_threshold_max"),
        log_level=overrides.get("log_level", "WARNING"),
    )
    return registry.build_server(settings)


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    return asyncio.run(server.call_tool(name, arguments))


def _seed_all_kinds(paths: FoundryPaths) -> dict[str, str]:
    """Seed one real, eligible item for each of the five frozen knowledge
    kinds and return their opaque-id local segments, keyed by kind name
    (``report_draft``/``report_final`` map to two DISTINCT draft ids, per
    KMCP-OQ-2)."""

    build_catalog_run(paths)
    catalog_svc.import_run(paths, "rf_run_catalog001")
    _write_threshold(paths, "client_sensitive")
    source_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    run_id = "rf_run_km_process01"
    build_run(paths, run_id)

    draft = builder_service.create_draft(
        paths,
        title="Process Draft Report",
        sensitivity="public",
        blocks=[{"markdown": "PROCESS DRAFT BODY"}],
    )
    report_draft_id = draft["report_draft_id"]

    final_draft = builder_service.create_draft(
        paths,
        title="Process Final Report",
        sensitivity="public",
        blocks=[{"markdown": "PROCESS FINAL BODY"}],
    )
    report_final_id = final_draft["report_draft_id"]
    _publish_draft(paths, report_final_id, status="published")

    assertion_id = _materialize(
        paths, "rf_run_km_process_assertion", "workspace-km-process", "The process assertion fact is real."
    )
    AssertionCatalog(paths).rebuild("workspace-km-process")

    return {
        "source": source_id,
        "run": run_id,
        "report_draft": report_draft_id,
        "report_final": report_final_id,
        "assertion": assertion_id,
    }


# ===========================================================================
# 1. Exact eight-tool inventory + forbidden-name negative space
# ===========================================================================


def test_exact_eight_tool_names_registered(tmp_foundry: FoundryPaths) -> None:
    server = _build(tmp_foundry)
    names = sorted(t.name for t in asyncio.run(server.list_tools()))

    assert names == sorted(
        (
            "search",
            "fetch",
            "rf_search",
            "rf_fetch",
            "rf_source_get",
            "rf_assertion_get",
            "rf_report_get",
            "rf_run_get",
        )
    )
    assert len(names) == 8
    assert set(names) == set(ka.TOOL_NAMES) == set(registry.TOOL_NAMES)
    assert registry.CORE_TOOL_NAMES == ka.CORE_TOOL_NAMES == ("search", "fetch")
    assert registry.RF_TOOL_NAMES == ka.RF_TOOL_NAMES


_SEARCH_ROUTER_TOOL_NAMES = (
    "search_run",
    "extract_url",
    "search_source_discovery",
    "search_semantic_discovery",
    "search_github_discovery",
    "search_quick_lookup",
    "search_official_sources",
    "search_academic_discovery",
)

# decisions-block §9.2's own denylist vocabulary -- no tool name in this
# registry may ever contain one of these substrings.
_FORBIDDEN_TOOL_NAME_SUBSTRINGS = (
    "acquire",
    "acquisition",
    "extract",
    "job",
    "import",
    "approve",
    "approval",
    "bundle",
    "provider",
    "cache_build",
    "rebuild",
    "telemetry",
    "audit",
    "persist",
    "writeback",
    "migrate",
    "delete",
    "web_search",
    "fetch_url",
)


def test_no_search_router_or_forbidden_tool_names_present(tmp_foundry: FoundryPaths) -> None:
    server = _build(tmp_foundry)
    names = {t.name for t in asyncio.run(server.list_tools())}

    for forbidden in _SEARCH_ROUTER_TOOL_NAMES:
        assert forbidden not in names
    for name in names:
        for substring in _FORBIDDEN_TOOL_NAME_SUBSTRINGS:
            assert substring not in name, f"tool name {name!r} contains forbidden substring {substring!r}"


# ===========================================================================
# 2. Import-graph allowlist (decisions-block §9.1/§9.4)
# ===========================================================================

_ALLOWED_ABSOLUTE_IMPORT_PREFIXES = (
    "__future__",
    "logging",
    "json",
    "os",
    "dataclasses",
    "typing",
    "collections",
    "research_foundry.errors",
    "research_foundry.paths",
    "research_foundry.config",
    "research_foundry.services.knowledge_access",
    # Lazy-only inside `registry.build_server` (never at module level) --
    # allowed by the offline-safe-import contract, which this test does not
    # re-derive; see `tests/test_knowledge_mcp_offline_import.py`.
    "mcp",
)


def _resolved_absolute_imports(module: Any) -> list[str]:
    """Every absolute (non-relative) import in ``module``, resolved to its
    full dotted path per imported alias.

    ``from a.b import c`` resolves to ``a.b.c`` -- not just ``a.b`` -- so
    that ``from research_foundry.services import knowledge_access`` is
    checked against the allowlist as ``research_foundry.services.
    knowledge_access``, matching how this repo actually declares that
    import (a package-relative submodule import, not a bare package
    import).
    """

    source = inspect.getsource(module)
    tree = ast.parse(source)
    resolved: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            resolved.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            base = node.module or ""
            for alias in node.names:
                resolved.append(f"{base}.{alias.name}" if base else alias.name)
    return resolved


def _matches_allowlist(name: str) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in _ALLOWED_ABSOLUTE_IMPORT_PREFIXES)


def test_process_registry_settings_import_graph_is_an_explicit_allowlist() -> None:
    for module in (knowledge_mcp_pkg, process, registry, kmcp_settings):
        for name in _resolved_absolute_imports(module):
            assert _matches_allowlist(name), (
                f"{module.__name__} imports {name!r}, outside the declared dependency "
                "allowlist (decisions-block §9.1/§9.4)"
            )


def test_process_registry_settings_never_reference_search_router_or_operator() -> None:
    """Static AST substring check (invariant 1) -- complements the allowlist
    check above with the explicit forbidden-name vocabulary."""

    forbidden = ("search_router", "operator", "hermes")
    for module in (knowledge_mcp_pkg, process, registry, kmcp_settings):
        source = inspect.getsource(module)
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        for name in names:
            lowered = name.lower()
            for banned in forbidden:
                assert banned not in lowered, f"{module.__name__} has forbidden import: {name}"


# ===========================================================================
# 3. Settings/environment view (decisions-block §9.3)
# ===========================================================================


def test_settings_allowed_env_vars_stay_minimal_and_exhaustive() -> None:
    assert kmcp_settings.ALLOWED_ENV_VARS == (
        kmcp_settings.WORKSPACE_ROOT_ENV,
        kmcp_settings.LOG_LEVEL_ENV,
    )
    assert len(kmcp_settings.ALLOWED_ENV_VARS) == 2


_POISONED_ENV = {
    "RF_MCP_PRINCIPAL_USER_ID": "attacker-user",
    "RF_MCP_PRINCIPAL_WORKSPACE_ID": "attacker-workspace",
    "RF_MCP_PRINCIPAL_ROLES": "attacker-role",
    "RF_TOKEN_AGENT": "super-secret-agent-token",
    "BRAVE_API_KEY": "brave-secret-key",
    "SERPAPI_API_KEY": "serpapi-secret-key",
    "TAVILY_API_KEY": "tavily-secret-key",
    "MEATYWIKI_TOKEN": "meatywiki-secret-token",
    "SKILLMEAT_TOKEN": "skillmeat-secret-token",
    "CCDASH_API_KEY": "ccdash-secret-key",
}


def test_poisoned_environment_never_leaks_into_any_tool_output(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A process environment carrying Search Router / Operator / writeback
    credentials (decisions-block §9.3's FORBIDDEN list) never influences,
    nor leaks into, any of the eight tools' output -- even with real content
    seeded across every knowledge kind to search/fetch through."""

    ids = _seed_all_kinds(tmp_foundry)
    monkeypatch.setenv(kmcp_settings.WORKSPACE_ROOT_ENV, str(tmp_foundry.root))
    for key, value in _POISONED_ENV.items():
        monkeypatch.setenv(key, value)

    server = registry.build_server()  # resolves settings from the (poisoned) env itself

    calls = [
        ("search", {"query": "process"}),
        ("fetch", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_search", {"query": "process"}),
        ("rf_fetch", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_source_get", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_run_get", {"id": f"rfk:v1:run:{ids['run']}"}),
        ("rf_report_get", {"id": f"rfk:v1:report_draft:{ids['report_draft']}"}),
        ("rf_assertion_get", {"id": f"rfk:v1:assertion:{ids['assertion']}"}),
    ]
    for name, args in calls:
        result = _call(server, name, args)
        text_blocks = "".join(getattr(block, "text", "") for block in result.content)
        dumped = json.dumps(result.structuredContent) + text_blocks
        for secret in _POISONED_ENV.values():
            assert secret not in dumped, f"tool {name!r} leaked a poisoned credential value"


# ===========================================================================
# 4. Transport guard on the FULL eight-tool server (invariant 8)
# ===========================================================================


def test_full_server_transport_guard_stdio_only(tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp.server.fastmcp import FastMCP

    server = _build(tmp_foundry)
    monkeypatch.setattr(FastMCP, "run", lambda self, transport=None, mount_path=None: None)
    server.run()
    server.run(transport="stdio")

    with pytest.raises(registry.UnsupportedTransportError):
        server.run(transport="sse")
    with pytest.raises(registry.UnsupportedTransportError):
        server.run(transport="streamable-http")
    with pytest.raises(registry.UnsupportedTransportError):
        server.sse_app()
    with pytest.raises(registry.UnsupportedTransportError):
        server.streamable_http_app()
    with pytest.raises(registry.UnsupportedTransportError):
        server.run_sse_async()
    with pytest.raises(registry.UnsupportedTransportError):
        server.run_streamable_http_async()


def test_full_server_never_wires_oauth_or_a_non_loopback_listener(tmp_foundry: FoundryPaths) -> None:
    server = _build(tmp_foundry)

    assert server.settings.auth is None
    assert server._auth_server_provider is None
    assert server._token_verifier is None
    assert server.settings.host in ("127.0.0.1", "localhost")


# ===========================================================================
# 5. KMCP-1.3 dual encoding across every tool
# ===========================================================================


def test_dual_encoding_equality_across_all_eight_tools(tmp_foundry: FoundryPaths) -> None:
    ids = _seed_all_kinds(tmp_foundry)
    server = _build(tmp_foundry)

    calls = [
        ("search", {"query": "process"}),
        ("fetch", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_search", {"query": "process"}),
        ("rf_fetch", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_source_get", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_run_get", {"id": f"rfk:v1:run:{ids['run']}"}),
        ("rf_report_get", {"id": f"rfk:v1:report_draft:{ids['report_draft']}"}),
        ("rf_report_get", {"id": f"rfk:v1:report_final:{ids['report_final']}"}),
    ]
    for name, args in calls:
        result = _call(server, name, args)
        assert result.isError is False, (name, result)
        assert len(result.content) == 1
        assert result.content[0].type == "text"
        assert json.loads(result.content[0].text) == result.structuredContent, name


def test_rf_search_and_rf_fetch_mirror_core_safe_denial_for_malformed_input(tmp_foundry: FoundryPaths) -> None:
    server = _build(tmp_foundry)

    over_length_query = "x" * (ka.QUERY_MAX_LENGTH + 1)
    core_search = _call(server, "search", {"query": over_length_query})
    rf_search = _call(server, "rf_search", {"query": over_length_query})
    assert core_search.isError is False
    assert core_search.structuredContent == {"results": []}
    assert rf_search.isError is False
    assert rf_search.structuredContent == {"results": [], "next_cursor": None, "truncated": False}
    assert json.loads(core_search.content[0].text) == core_search.structuredContent
    assert json.loads(rf_search.content[0].text) == rf_search.structuredContent

    core_fetch = _call(server, "fetch", {"id": "not-a-real-id"})
    rf_fetch = _call(server, "rf_fetch", {"id": "not-a-real-id"})
    assert core_fetch.isError is True and core_fetch.content[0].text == registry._FETCH_DENIED_MESSAGE
    assert rf_fetch.isError is True and rf_fetch.content[0].text == registry._FETCH_DENIED_MESSAGE
    assert core_fetch.structuredContent is None
    assert rf_fetch.structuredContent is None


# ===========================================================================
# 6. Core FetchDTO `metadata`: absent (live) and present (schema-level)
# ===========================================================================


def test_core_and_rf_fetch_never_populate_metadata_live(tmp_foundry: FoundryPaths) -> None:
    """ABSENT case: this v1 implementation never itself constructs a
    populated `metadata` map -- `fetch_core` hardcodes `metadata=None`, so
    neither `fetch` nor any RF-extended tool ever emits the key."""

    ids = _seed_all_kinds(tmp_foundry)
    server = _build(tmp_foundry)

    core = _call(server, "fetch", {"id": f"rfk:v1:source:{ids['source']}"})
    assert "metadata" not in core.structuredContent

    rf = _call(server, "rf_fetch", {"id": f"rfk:v1:source:{ids['source']}"})
    assert "metadata" not in rf.structuredContent  # RF documents carry `rf_metadata`, never `metadata`


def test_core_document_metadata_slot_accepts_arbitrary_keys_when_present(schema_registry: SchemaRegistry) -> None:
    """PRESENT case: the frozen core `FetchDTO` root stays closed, but its
    OWN `metadata` map is an intentionally open `Record<str, unknown>`
    (AC KMCP-2) -- proven at the DTO/schema level since no live call in this
    process ever populates one."""

    doc = ka.KnowledgeDocument(
        id="rfk:v1:run:km_process_meta",
        title="Metadata Present Example",
        text="body",
        url=ka.build_local_resource_url("rfk:v1:run:km_process_meta", origin="http://127.0.0.1"),
        metadata={"kind": "run", "truncated": False, "custom_forward_compatible_key": 42},
    )
    result = schema_registry.validate(doc.to_dict(), "knowledge_document")
    assert result.ok, result.errors
    assert doc.to_dict()["metadata"]["custom_forward_compatible_key"] == 42


# ===========================================================================
# 7. Zero write-surface/provider calls across all eight tools
# ===========================================================================


def test_all_eight_tools_touch_zero_write_surface(tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> None:
    ids = _seed_all_kinds(tmp_foundry)
    server = _build(tmp_foundry)  # bootstraps projectors -- plain dict registration, no I/O

    before = _snapshot_tree(tmp_foundry.root)
    _install_write_surface_spies(monkeypatch)

    calls = [
        ("search", {"query": "process"}),
        ("fetch", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("fetch", {"id": "rfk:v1:source:does-not-exist-at-all"}),
        ("rf_search", {"query": "process", "kinds": ["source", "run", "report_draft", "report_final", "assertion"]}),
        ("rf_fetch", {"id": f"rfk:v1:run:{ids['run']}"}),
        ("rf_source_get", {"id": f"rfk:v1:source:{ids['source']}"}),
        ("rf_assertion_get", {"id": f"rfk:v1:assertion:{ids['assertion']}"}),
        ("rf_report_get", {"id": f"rfk:v1:report_draft:{ids['report_draft']}"}),
        ("rf_report_get", {"id": f"rfk:v1:report_final:{ids['report_final']}"}),
        ("rf_run_get", {"id": f"rfk:v1:run:{ids['run']}"}),
        ("rf_run_get", {"id": f"rfk:v1:source:{ids['source']}"}),  # wrong kind -- denies before any read
    ]
    for name, args in calls:
        _call(server, name, args)

    assert _snapshot_tree(tmp_foundry.root) == before


# ===========================================================================
# 8. Typed getter kind-scoping + local-trust assertion caveat
# ===========================================================================


@pytest.mark.parametrize(
    ("tool", "wrong_kind_key", "wrong_kind_prefix"),
    [
        ("rf_source_get", "run", "run"),
        ("rf_run_get", "source", "source"),
        ("rf_report_get", "run", "run"),
        ("rf_assertion_get", "source", "source"),
    ],
)
def test_typed_getter_denies_generically_for_wrong_kind_id(
    tmp_foundry: FoundryPaths, tool: str, wrong_kind_key: str, wrong_kind_prefix: str
) -> None:
    ids = _seed_all_kinds(tmp_foundry)
    server = _build(tmp_foundry)

    wrong_id = f"rfk:v1:{wrong_kind_prefix}:{ids[wrong_kind_key]}"
    result = _call(server, tool, {"id": wrong_id})

    assert result.isError is True
    assert result.content[0].text == registry._FETCH_DENIED_MESSAGE
    assert result.structuredContent is None


def test_typed_getters_resolve_matching_kind(tmp_foundry: FoundryPaths) -> None:
    ids = _seed_all_kinds(tmp_foundry)
    server = _build(tmp_foundry)

    checks = [
        ("rf_source_get", f"rfk:v1:source:{ids['source']}", "source"),
        ("rf_run_get", f"rfk:v1:run:{ids['run']}", "run"),
        ("rf_report_get", f"rfk:v1:report_draft:{ids['report_draft']}", "report_draft"),
        ("rf_report_get", f"rfk:v1:report_final:{ids['report_final']}", "report_final"),
    ]
    for tool, knowledge_id, expected_kind in checks:
        result = _call(server, tool, {"id": knowledge_id})
        assert result.isError is False, (tool, result)
        assert result.structuredContent["kind"] == expected_kind
        assert result.structuredContent["id"] == knowledge_id
        assert result.structuredContent["receipt"]["tool"] == tool
        assert result.structuredContent["receipt"]["persisted"] is False


def test_rf_assertion_get_always_denies_under_local_trust_even_for_a_real_id(tmp_foundry: FoundryPaths) -> None:
    """The local-trust caveat (`registry.py`'s module docstring): this
    process always resolves `identity=None`, and the assertion catalog
    unconditionally denies without one -- so even a REAL, well-formed,
    eligible assertion id denies generically, and no `assertion`-kind
    result is ever returned by `search`/`rf_search` through this
    transport. Expected v1 behavior, not a bug."""

    ids = _seed_all_kinds(tmp_foundry)
    server = _build(tmp_foundry)

    result = _call(server, "rf_assertion_get", {"id": f"rfk:v1:assertion:{ids['assertion']}"})
    assert result.isError is True
    assert result.content[0].text == registry._FETCH_DENIED_MESSAGE

    search_result = _call(server, "rf_search", {"query": "process", "kinds": ["assertion"]})
    assert search_result.structuredContent["results"] == []

    core_search_result = _call(server, "search", {"query": "process"})
    assert all(
        not item["id"].startswith("rfk:v1:assertion:") for item in core_search_result.structuredContent["results"]
    )


# ===========================================================================
# 9. No unqualified hosted-compatibility claim (decisions-block §10)
# ===========================================================================

_HOSTED_COMPAT_CLAIM_MARKERS = (
    "chatgpt-compatible",
    "chatgpt compatible",
    "openai-compatible",
    "openai compatible",
    "hosted-compatible",
    "compatible with chatgpt",
    "compatible with openai",
)


def test_no_unqualified_hosted_compatibility_claim_in_source_or_tool_descriptions(tmp_foundry: FoundryPaths) -> None:
    texts = [inspect.getsource(module).lower() for module in (knowledge_mcp_pkg, process, registry, kmcp_settings)]

    server = _build(tmp_foundry)
    for tool in asyncio.run(server.list_tools()):
        if tool.description:
            texts.append(tool.description.lower())

    combined = "\n".join(texts)
    for marker in _HOSTED_COMPAT_CLAIM_MARKERS:
        assert marker not in combined, f"unqualified hosted-compatibility claim found: {marker!r}"


# ===========================================================================
# 10. Entry point wiring + pyproject.toml declaration
# ===========================================================================


def test_process_main_wires_settings_build_server_and_run_stdio(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: dict[str, Any] = {}

    class _FakeServer:
        def run(self) -> None:
            calls["ran"] = True

    fake_settings = KnowledgeMcpSettings(paths=tmp_foundry, sensitivity_threshold_max=None, log_level="WARNING")
    fake_server = _FakeServer()

    monkeypatch.setattr(process, "resolve_settings", lambda: fake_settings)

    def _fake_build_server(settings: KnowledgeMcpSettings) -> Any:
        calls["settings"] = settings
        return fake_server

    monkeypatch.setattr(process, "build_server", _fake_build_server)

    process.main()

    assert calls.get("ran") is True
    assert calls.get("settings") is fake_settings


def test_pyproject_declares_the_dedicated_entry_point_and_extra() -> None:
    import tomllib

    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    scripts = pyproject["project"]["scripts"]
    assert scripts["rf-knowledge-mcp"] == "research_foundry.knowledge_mcp.process:main"
    assert scripts["rf-mcp"] != scripts["rf-knowledge-mcp"]

    mcp_extra = pyproject["project"]["optional-dependencies"]["mcp"]
    assert any(dep.startswith("mcp") for dep in mcp_extra)


# ===========================================================================
# 11. Full transitive import-graph closure (KMCP-6.2; see KMCP-F1 in
#     .claude/findings/research-foundry-knowledge-mcp-findings.md)
# ===========================================================================
#
# Section 2 above (`test_process_registry_settings_import_graph_is_an_explicit
# _allowlist`) is a STATIC AST check of only the four `knowledge_mcp.*`
# files' own source -- it treats `research_foundry.services.knowledge_access`
# as one opaque allowed prefix and never asks what THAT module (and
# everything it imports) actually pulls in once loaded. This section closes
# that gap with the REAL, live transitive `sys.modules` closure, in a fresh
# subprocess (never the pytest process's own already-polluted `sys.modules`,
# which every other test module in the full suite may have already imported
# fastapi/search_router/etc into).
#
# KMCP-F1 (investigated and NOT fixed this phase -- see the finding doc):
# `research_foundry.api.__init__` unconditionally probes `import fastapi;
# import uvicorn` in its own package body, and Python always runs a
# package's `__init__.py` before any submodule -- so both
# `knowledge_access.py`'s `AuthIdentity` (type-only) import AND its
# `resolve_workspace_isolation_active` (real, runtime-called) import from
# `..api.auth.*` transitively require `fastapi`/`starlette`/`uvicorn` to be
# importable. This is a real, pre-existing, documented limitation -- `fastapi`
# etc. are EXPECTED present below, not asserted absent. What THIS test
# actually proves is AC KMCP-1's own forbidden set: Search Router / Operator
# / Hermes registries, provider-credential/cost-bearing tool clients, and
# every known mutator/writeback/acquisition service module never enter the
# process's real import graph despite that unrelated `serve`-extra
# dependency.

_FULL_CLOSURE_PROBE = """
import sys, json
import research_foundry.knowledge_mcp.process
print(json.dumps(sorted(m for m in sys.modules if m.startswith("research_foundry"))))
"""

# Every module name substring that would signal a Search Router / Operator /
# Hermes registry, a provider-credential/cost-bearing client, or a known
# mutator/writeback/acquisition service leaking into this read-only process's
# import graph (decisions-block Sec 9.1/9.4, AC KMCP-1's forbidden set).
_FORBIDDEN_MODULE_SUBSTRINGS = (
    "search_router",
    "operator",
    "hermes",
    "agent_job",
    "agent_providers",
    "swarm_drive",
    "writeback",
    "share_store",
    "token_service",
    "meatywiki",
    "skillmeat",
    "ccdash",
    "notebooklm",
    "notebook_correlation",
    "extraction",
    "extractors",
    "capture",
    "acquisition",
    "intake",
    "run_launch",
    "run_seal",
)


def test_full_process_import_transitive_closure_excludes_search_router_and_operator_but_documents_fastapi() -> None:
    """The REAL transitive import graph of a fresh ``rf-knowledge-mcp``
    process import -- not just the four ``knowledge_mcp.*`` files' own static
    imports -- never pulls in a Search Router/Operator/Hermes registry, a
    provider-credential client, or a mutator/writeback/acquisition service
    module (AC KMCP-1's forbidden set), even though (KMCP-F1) it does
    transitively pull in ``fastapi``/``starlette``/``uvicorn`` via
    ``knowledge_access.py``'s two ``..api.auth.*`` imports. A subprocess is
    used deliberately -- the pytest process's own ``sys.modules`` is already
    polluted by unrelated test modules elsewhere in the full suite (some of
    which DO import Search Router / FastAPI code), so only a fresh
    interpreter proves what THIS process, started cold, actually loads.
    """

    result = subprocess.run(
        [sys.executable, "-c", _FULL_CLOSURE_PROBE],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    modules: list[str] = json.loads(result.stdout)

    assert "research_foundry.knowledge_mcp.process" in modules
    assert "research_foundry.knowledge_mcp.registry" in modules
    assert "research_foundry.knowledge_mcp.settings" in modules
    assert "research_foundry.services.knowledge_access" in modules

    for name in modules:
        for forbidden in _FORBIDDEN_MODULE_SUBSTRINGS:
            assert forbidden not in name, (
                f"{name!r} in the real transitive import graph contains forbidden "
                f"substring {forbidden!r} (AC KMCP-1's forbidden set)"
            )


def test_full_process_import_transitive_closure_pulls_in_serve_extra_per_kmcp_f1() -> None:
    """Documents KMCP-F1 directly (rather than leaving it an unexplained
    side-effect of the test above): a fresh, otherwise-``mcp``-only
    interpreter importing ``research_foundry.knowledge_mcp.process`` DOES
    load ``fastapi``/``starlette``/``uvicorn`` (via ``knowledge_access.py``'s
    ``..api.auth.provider``/``..api.auth.scope`` imports, both of which run
    ``research_foundry.api``'s own unconditional ``import fastapi; import
    uvicorn`` package-init probe). This is the SAME real interpreter run
    ``pyproject.toml``'s own ``mcp`` extra declaration undersells -- an
    operator installing only ``pip install 'research-foundry[mcp]'`` (no
    ``serve``) hits this at process-import time, not this repo's own clear
    missing-SDK message. See ``.claude/findings/research-foundry-knowledge-
    mcp-findings.md`` (KMCP-F1) for why this was investigated and NOT fixed
    this phase (no purely mechanical, non-behavioral fix exists)."""

    result = subprocess.run(
        [sys.executable, "-c", _FULL_CLOSURE_PROBE],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    modules: set[str] = set(json.loads(result.stdout))

    assert "research_foundry.api" in modules
    assert "research_foundry.api.auth.provider" in modules
    assert "research_foundry.api.auth.scope" in modules
