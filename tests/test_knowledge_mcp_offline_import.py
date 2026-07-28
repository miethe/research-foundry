"""Offline-safe-import contract test for the RF Knowledge MCP process (KMCP-4.1).

Mirrors ``tests/test_search_router_mcp_offline_import.py``'s own contract and
technique exactly (block every ``mcp``-namespaced import via
``builtins.__import__``), applied to the INDEPENDENT
``research_foundry.knowledge_mcp`` package instead of the Search Router's
``mcp_server``/``mcp_launcher`` modules. Carries no ``pytest.importorskip("mcp")``
gate -- it must run in every environment, including one where the optional
``mcp`` extra genuinely is not installed, because none of
``research_foundry.knowledge_mcp.{__init__,process,registry,settings}``
import it at module level.
"""

from __future__ import annotations

import builtins
import importlib
import sys
from typing import Any

import pytest

_MODULE_NAMES = (
    "research_foundry.knowledge_mcp",
    "research_foundry.knowledge_mcp.process",
    "research_foundry.knowledge_mcp.registry",
    "research_foundry.knowledge_mcp.settings",
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
    """A fresh import of ``process`` (and its sibling ``registry``/``settings``
    modules) must succeed even when every ``mcp``-namespaced import raises
    ``ImportError`` -- proving none of them touch the optional SDK at module
    level."""

    _clear_modules(monkeypatch)
    _block_mcp_imports(monkeypatch)

    module = importlib.import_module("research_foundry.knowledge_mcp.process")
    assert module.main is not None


def test_build_server_raises_clear_runtime_error_without_mcp_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """``build_server()`` is the only function that touches the SDK; with it
    genuinely unimportable, callers get the actionable ``_MISSING_SDK_MSG``
    (naming ``uv sync --extra mcp``), not a bare ``ImportError`` traceback."""

    registry = importlib.import_module("research_foundry.knowledge_mcp.registry")
    _block_mcp_imports(monkeypatch)

    with pytest.raises(RuntimeError, match="uv sync --extra mcp"):
        registry.build_server()


def test_knowledge_mcp_package_never_imports_search_router_or_operator() -> None:
    """Static import-graph check (invariant 1): none of
    ``research_foundry.knowledge_mcp``'s own source files reference
    ``search_router``, an Operator/Hermes-adjacent module, or the ``mcp`` SDK
    at module level."""

    import ast
    import inspect

    from research_foundry.knowledge_mcp import process, registry, settings

    forbidden = ("search_router", "operator", "hermes")
    for module in (process, registry, settings):
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
