"""Shared helper for stamping ``rf_schema_version`` onto LAN API JSON payloads.

Part of PRD FR-4.1 / AC-RFUP4-1 (see
``docs/dev/architecture/machine-surface-inventory.md``): every machine-readable
``rf`` surface carries a top-level ``rf_schema_version`` field so downstream
consumers can detect contract drift.

Only **object-shaped** (``dict``) responses can carry this field — a JSON
array has no top-level key namespace to add a version into. Endpoints that
return a bare list (``GET /api/runs``, ``GET /api/runs/{id}/claims``,
``GET /api/reports``, ``GET /api/reports/{id}/versions``) are intentionally
left unstamped; this is documented as N/A (not a gap) in the machine-surface
inventory rather than worked around by wrapping the array in an envelope,
which would be a breaking shape change for existing consumers (the runs-viewer
client expects a bare array from these endpoints).

``GET /api/runs/{run_id}/context`` is also intentionally excluded — its
docstring states the response mirrors ``run.json``'s ``context`` key exactly
(schema 1.3 contract), and that sub-object is not itself an API envelope.
"""

from __future__ import annotations

from typing import Any, TypeVar

from .. import RF_SCHEMA_VERSION

_D = TypeVar("_D", bound=dict[str, Any])


def stamp(payload: _D) -> _D:
    """Set ``rf_schema_version`` on *payload* (in place) and return it.

    Additive-only: sets/overwrites exactly one top-level key, never touches
    any other field. Callers should apply this to every top-level ``dict``
    response just before returning it from a router handler.
    """
    payload["rf_schema_version"] = RF_SCHEMA_VERSION
    return payload


__all__ = ["stamp"]
