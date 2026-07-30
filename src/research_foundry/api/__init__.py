"""Research Foundry HTTP API (optional ``serve`` extra).

Importing this bare package does **not** require ``fastapi`` or ``uvicorn`` —
several CLI-reachable services import typed support modules such as
``api.auth.provider`` / ``api.auth.scope`` at runtime, and those must stay
import-safe without the ``serve`` extra installed. Only :func:`create_app`
(and the ``.app`` module it lazily imports) require the extra; calling it
without ``fastapi``/``uvicorn`` installed still raises a clear
``ModuleNotFoundError`` from that lazy import. Install with::

    pip install 'research-foundry[serve]'
"""

from __future__ import annotations

from typing import Any


def create_app(*args: Any, **kwargs: Any) -> Any:
    """Lazily import the application factory without coupling service imports.

    Services use typed API support modules such as ``api.auth.provider``.  An
    eager package-level app import makes that ordinary dependency re-import
    routers while a service is only partially initialized.  Keeping the
    public factory lazy preserves ``from research_foundry.api import
    create_app`` while avoiding that circular import path.
    """

    from .app import create_app as _create_app

    return _create_app(*args, **kwargs)

__all__ = ["create_app"]
