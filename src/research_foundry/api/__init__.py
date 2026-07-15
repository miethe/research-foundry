"""Research Foundry HTTP API (optional ``serve`` extra).

Importing this package requires ``fastapi`` and ``uvicorn`` to be installed.
Install with::

    pip install 'research-foundry[serve]'

The core ``research_foundry`` package does **not** import this sub-package on
startup, so a plain ``pip install research-foundry`` never pulls in FastAPI or
Uvicorn.
"""

from __future__ import annotations

from typing import Any

try:
    import fastapi  # noqa: F401
    import uvicorn  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "fastapi and uvicorn are required. Install with: pip install 'research-foundry[serve]'"
    ) from exc

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
