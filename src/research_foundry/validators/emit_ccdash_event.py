"""Stop Claude Code hook (spec §7.3) — thin shim.

On session Stop, emit a CCDash execution event for the latest run by delegating
to :func:`research_foundry.services.telemetry.emit_latest_or_noop`. That module
is owned by another service; it is imported **lazily** inside :func:`main` so
this file imports standalone and no-ops on ``ImportError``.

Always safe: no stdin required, no workspace required, always exits ``0``.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def _read_stdin() -> dict[str, Any]:
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return {}
        raw = sys.stdin.read()
    except (OSError, ValueError):  # closed/captured/non-readable stdin
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def main(argv: list[str] | None = None) -> int:
    """Entry point. Always returns ``0`` (Stop hooks must not wedge the session)."""

    # Drain stdin (Stop payload) but it is not required for the emit.
    _read_stdin()

    emitted: str | None = None
    try:
        from ..services.telemetry import emit_latest_or_noop

        path = emit_latest_or_noop()
        emitted = str(path) if path is not None else None
    except ImportError:
        emitted = None
    except Exception:  # noqa: BLE001 — telemetry failures never break Stop
        emitted = None

    print(json.dumps({"decision": "allow", "ccdash_event": emitted}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
