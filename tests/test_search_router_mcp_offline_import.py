"""Offline-safe-import contract test for the Search Router MCP server.

Unlike ``tests/test_search_router_mcp.py`` (which gates its whole module on
``pytest.importorskip("mcp", ...)`` since it exercises the real ``FastMCP``
server), this file carries **no** such gate -- it must run in every
environment, including one where the optional ``mcp`` extra genuinely is not
installed, because it never imports the SDK itself; it only verifies that
``mcp_server.py`` doesn't either (except lazily, inside ``build_server()``).

It blocks every ``mcp``-namespaced import via ``builtins.__import__`` so the
two halves of the module's documented contract hold true regardless of
whether ``mcp`` happens to be installed in the venv actually running this
test:

1. The module itself imports cleanly with the SDK unavailable -- only
   :func:`build_server`/:func:`main` touch it, and only lazily.
2. When the SDK genuinely cannot be imported, :func:`build_server` raises a
   clear, actionable :class:`RuntimeError` (naming the install command)
   instead of letting an opaque ``ImportError`` from inside ``mcp.server.
   fastmcp`` propagate.
"""

from __future__ import annotations

import builtins
import importlib
import sys
from typing import Any

import pytest

_MODULE_NAME = "research_foundry.services.search_router.mcp_server"


def _block_mcp_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def _blocking_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError(f"simulated: {name!r} is not installed (offline-safe-import test)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)


def test_module_imports_without_mcp_sdk_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fresh import of ``mcp_server`` must succeed even when every ``mcp``-
    namespaced import raises ``ImportError`` -- proving the module's own
    top-level imports (``from .router import extract_urls, run_search``,
    the CARP-5.2 ``TYPE_CHECKING``-only ``AuthIdentity`` import) never touch
    the optional SDK."""

    for name in [n for n in list(sys.modules) if n == _MODULE_NAME or n == "mcp" or n.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, name, raising=False)

    _block_mcp_imports(monkeypatch)

    module = importlib.import_module(_MODULE_NAME)
    assert module.build_server is not None
    assert module.main is not None


def test_build_server_raises_clear_runtime_error_without_mcp_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """``build_server()`` is the *only* function that touches the SDK; with
    it genuinely unimportable, callers get the actionable
    ``_MISSING_SDK_MSG`` (naming ``uv sync --extra mcp``), not a bare
    ``ImportError`` traceback from inside ``mcp.server.fastmcp``."""

    module = importlib.import_module(_MODULE_NAME)
    _block_mcp_imports(monkeypatch)

    with pytest.raises(RuntimeError, match="uv sync --extra mcp"):
        module.build_server()
