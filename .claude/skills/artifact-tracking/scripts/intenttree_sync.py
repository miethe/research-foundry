#!/usr/bin/env python3
"""
Best-effort IntentTree sync helper.

When the environment variable ``INTENTTREE_SDLC_SYNC`` is set to a truthy
value (non-empty, non-zero string), :func:`push_to_intenttree` shells out to::

    itt sync import <file> --apply

for the given planning / progress file that was just updated.

All exceptions are swallowed.  The function **never** raises and **never**
changes the caller's exit code.  If the flag is unset or the push fails for
any reason (CLI missing, network error, nonzero exit, etc.) the call is a
silent no-op — existing script behaviour is byte-for-byte unchanged.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Union


def push_to_intenttree(file: Union[str, Path]) -> None:
    """Push *file* to IntentTree via ``itt sync import --apply``.

    This is a **best-effort, non-fatal** hook:

    * Runs only when ``INTENTTREE_SDLC_SYNC`` is set to a truthy string
      (non-empty, case-insensitive; ``"0"`` and ``"false"`` are treated as
      falsy for convenience, matching common shell conventions).
    * Swallows every exception and subprocess error.
    * Writes a single warning line to *stderr* when the push fails so the
      caller can observe the failure without it affecting exit codes.

    Args:
        file: The markdown artifact path that was just successfully updated.
    """
    raw = os.environ.get("INTENTTREE_SDLC_SYNC", "")
    if not _is_truthy(raw):
        return

    tree = os.environ.get("INTENTTREE_TREE", "").strip()
    if not tree:
        print(
            "[intenttree_sync] warn: INTENTTREE_SDLC_SYNC is on but INTENTTREE_TREE is unset; "
            f"skipping sync for {file} (set the repo's tree id).",
            file=sys.stderr,
        )
        return

    # Use the normalizing capture script (sibling), NOT `itt sync import`: the thin client
    # has no YAML parser and silently drops rich tasks[] (IntentTree backlog DI-103).
    script = Path(__file__).resolve().parent / "intenttree_capture.py"
    path_str = str(file)
    cmd = [sys.executable, str(script), "sync", path_str, "--tree", tree, "--apply"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(
                f"[intenttree_sync] warn: capture sync exited {result.returncode} "
                f"for {path_str}: {result.stderr.strip() or result.stdout.strip()}",
                file=sys.stderr,
            )
    except FileNotFoundError:
        print(
            f"[intenttree_sync] warn: capture script not found ({script}); "
            f"skipping sync for {path_str}",
            file=sys.stderr,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"[intenttree_sync] warn: unexpected error syncing {path_str}: {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_truthy(value: str) -> bool:
    """Return True for non-empty strings that don't spell out a falsy value."""
    return value.strip().lower() not in ("", "0", "false", "no", "off")
