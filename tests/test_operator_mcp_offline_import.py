"""Offline-safe-import contract test for the RF Operator MCP process (M2 Leg B,
OPM-5.1/5.2/5.4).

Mirrors ``tests/test_knowledge_mcp_offline_import.py``'s own contract and
technique exactly (block every ``mcp``-namespaced import via
``builtins.__import__``), applied to the INDEPENDENT
``research_foundry.operator_mcp`` package. Carries no
``pytest.importorskip("mcp")`` gate -- it must run in every environment,
including one where the optional ``mcp`` extra genuinely is not installed,
because none of ``research_foundry.operator_mcp.{__init__,process,server}``
imports it at module level.
"""

from __future__ import annotations

import builtins
import importlib
import sys
from typing import Any

import pytest

_MODULE_NAMES = (
    "research_foundry.operator_mcp",
    "research_foundry.operator_mcp.process",
    "research_foundry.operator_mcp.server",
)


def _block_mcp_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def _blocking_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError(f"simulated: {name!r} is not installed (offline-safe-import test)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)


def _clear_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name in _MODULE_NAMES or name == "mcp" or name.startswith("mcp."):
            monkeypatch.delitem(sys.modules, name, raising=False)


def test_process_module_imports_without_mcp_sdk_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fresh import of ``process`` (and its sibling ``server`` module) must
    succeed even when every ``mcp``-namespaced import raises ``ImportError``
    -- proving neither touches the optional SDK at module level."""

    _clear_modules(monkeypatch)
    _block_mcp_imports(monkeypatch)

    module = importlib.import_module("research_foundry.operator_mcp.process")
    assert module.main is not None


def test_base_package_imports_without_mcp_sdk_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """The base ``research_foundry`` package (and, transitively, the
    ``operator_mcp`` package itself) must import cleanly with the SDK
    unimportable -- ``rf --help`` and every other CLI path must not
    regress just because ``operator_mcp`` exists on disk."""

    _clear_modules(monkeypatch)
    _block_mcp_imports(monkeypatch)

    import research_foundry  # noqa: F401
    module = importlib.import_module("research_foundry.operator_mcp")
    assert module.__all__ == []


def test_build_server_raises_clear_runtime_error_without_mcp_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """``build_server()`` is the only function that touches the SDK; with it
    genuinely unimportable, callers get the actionable ``_MISSING_SDK_MSG``
    (naming ``uv sync --extra mcp``), not a bare ``ImportError`` traceback.

    This holds REGARDLESS of the (separate, D4) adapter-completeness
    check -- the SDK-missing check runs first, before `build_server` ever
    looks at the adapter registry."""

    server_module = importlib.import_module("research_foundry.operator_mcp.server")
    _block_mcp_imports(monkeypatch)

    with pytest.raises(RuntimeError, match="uv sync --extra mcp"):
        server_module.build_server()


def test_operator_mcp_package_never_imports_knowledge_mcp_search_router_or_integrations() -> None:
    """Static import-graph check (M2 contract hard boundary 2 / D9 Leg B):
    none of ``research_foundry.operator_mcp``'s own source files reference
    ``knowledge_mcp``, ``search_router``, ``integrations``, or a
    Typer/subprocess-shaped import at module level."""

    import ast
    import inspect

    from research_foundry.operator_mcp import process, server

    forbidden = ("knowledge_mcp", "search_router", "integrations", "typer", "subprocess")
    for module in (process, server):
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
