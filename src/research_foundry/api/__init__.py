"""Research Foundry HTTP API (optional ``serve`` extra).

Importing this package requires ``fastapi`` and ``uvicorn`` to be installed.
Install with::

    pip install 'research-foundry[serve]'

The core ``research_foundry`` package does **not** import this sub-package on
startup, so a plain ``pip install research-foundry`` never pulls in FastAPI or
Uvicorn.
"""

from __future__ import annotations

try:
    import fastapi  # noqa: F401
    import uvicorn  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "fastapi and uvicorn are required. Install with: pip install 'research-foundry[serve]'"
    ) from exc

from .app import create_app  # noqa: E402 — guard above ensures imports succeed

__all__ = ["create_app"]
