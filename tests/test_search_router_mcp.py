"""Wave-4 MCP surface tests for the Research Foundry Search Router.

OFFLINE-ONLY: a fake discovery provider stands in for the real adapters; no
network call is made. Uses the shared ``tmp_foundry`` fixture so schema
validation and run-directory layout behave exactly as in the real workspace.

The whole module is skipped (not failed) when the optional ``mcp`` extra is
not installed — ``build_server()``/``main()`` are the only functions in
``mcp_server.py`` that touch the SDK, and importing the SDK here just lets us
exercise those functions instead of asserting only the (already-covered)
"missing SDK raises a clear error" contract.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

from research_foundry.paths import FoundryPaths  # noqa: E402
from research_foundry.services.search_router import mcp_server  # noqa: E402
from research_foundry.services.search_router import router as router_module
from research_foundry.services.search_router.providers.base import (  # noqa: E402
    ProviderResult,
    SearchHit,
)
from research_foundry.yamlio import load_yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Fake provider (offline-safe; mirrors the pattern in test_search_router_router.py)
# ---------------------------------------------------------------------------


class FakeDiscoveryProvider:
    id = "brave"
    roles = ("discovery",)
    requires: tuple[str, ...] = ()
    env_keys: tuple[str, ...] = ()

    def available(self) -> bool:
        return True

    def search(self, query: str, *, max_results: int, constraints: dict[str, Any]) -> ProviderResult:
        hits = [
            SearchHit(title="Alpha", url="https://example.com/a", provider="brave", rank=1, score=0.9),
        ]
        return ProviderResult(
            provider="brave", role="discovery", status="success",
            hits=hits, queries_executed=1, estimated_cost_usd=0.01,
        )

    def extract(self, urls: list[str]) -> ProviderResult:
        return ProviderResult(provider="brave", role="discovery", status="skipped")


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Build a real server and invoke ``name`` via the async ``call_tool`` API.

    Returns the structured-output dict (the second element of the
    ``call_tool`` tuple) — the same dict :func:`router.run_search` /
    :func:`router.extract_urls` return.
    """

    server = mcp_server.build_server()
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured


# ---------------------------------------------------------------------------
# TASK-4.1: build_server() registers the full expected tool surface
# ---------------------------------------------------------------------------


EXPECTED_TOOL_NAMES = {
    "search_run",
    "extract_url",
    "search_source_discovery",
    "search_semantic_discovery",
    "search_github_discovery",
    "search_quick_lookup",
    "search_official_sources",
    "search_academic_discovery",
}


def test_build_server_registers_expected_tools() -> None:
    server = mcp_server.build_server()

    async def _list_names() -> set[str]:
        tools = await server.list_tools()
        return {t.name for t in tools}

    names = asyncio.run(_list_names())
    assert names == EXPECTED_TOOL_NAMES


@pytest.mark.parametrize(
    ("tool_name", "expected_mode"),
    [
        ("search_quick_lookup", "quick_lookup"),
        ("search_official_sources", "official_source_check"),
        ("search_academic_discovery", "academic_discovery"),
        ("search_source_discovery", "source_discovery"),
        ("search_semantic_discovery", "semantic_discovery"),
        ("search_github_discovery", "github_discovery"),
    ],
)
def test_mode_preset_tools_fill_in_expected_mode(
    tmp_foundry: FoundryPaths,
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    expected_mode: str,
) -> None:
    monkeypatch.chdir(tmp_foundry.root)
    monkeypatch.setattr(router_module, "all_providers", lambda: {"brave": FakeDiscoveryProvider()})

    result = _call_tool(tool_name, {"request": {"query": "mode preset smoke"}})

    assert result["request"]["mode"] == expected_mode
    assert result["run_id"]


# ---------------------------------------------------------------------------
# TASK-4.1: intent_id / task_node_id passthrough into routing_decision.yaml
# ---------------------------------------------------------------------------


def test_search_run_tool_passes_intent_and_task_node_id_into_routing_decision(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_foundry.root)
    monkeypatch.setattr(router_module, "all_providers", lambda: {"brave": FakeDiscoveryProvider()})

    result = _call_tool(
        "search_run",
        {
            "request": {
                "query": "intent passthrough via mcp",
                "mode": "quick_lookup",
                "intent_id": "intent_mcp_test",
                "task_node_id": "node_mcp_test",
            }
        },
    )

    run_id = result["run_id"]
    rp = tmp_foundry.run_paths(run_id)
    routing_yaml = rp.run / "routing_decision.yaml"
    assert routing_yaml.exists()

    on_disk = load_yaml(routing_yaml)
    assert on_disk["intent_id"] == "intent_mcp_test"
    assert on_disk["active_node_id"] == "node_mcp_test"


def test_mode_preset_tool_also_passes_intent_and_task_node_id_through(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mode-preset wrappers only fill in ``mode`` — every other field on
    the request (including agent-harness correlation ids) rides through
    unchanged, exactly like the bare ``search_run`` tool."""

    monkeypatch.chdir(tmp_foundry.root)
    monkeypatch.setattr(router_module, "all_providers", lambda: {"brave": FakeDiscoveryProvider()})

    result = _call_tool(
        "search_quick_lookup",
        {
            "request": {
                "query": "preset intent passthrough",
                "intent_id": "intent_preset_test",
                "task_node_id": "node_preset_test",
            }
        },
    )

    rp = tmp_foundry.run_paths(result["run_id"])
    on_disk = load_yaml(rp.run / "routing_decision.yaml")
    assert on_disk["intent_id"] == "intent_preset_test"
    assert on_disk["active_node_id"] == "node_preset_test"
