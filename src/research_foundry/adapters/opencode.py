"""OpenCode adapter — local/open-source code agent (spec §13.4).

OpenCode is a CLI binary, not a Python module, so availability is detected with
``shutil.which("opencode")`` rather than an importable dependency. In the
default environment the binary is absent, so this adapter degrades to a
deterministic note (no subprocess, no file edits).
"""

from __future__ import annotations

import shutil
from typing import Any

from .base import AdapterResult, BaseAdapter, register


class OpenCodeAdapter(BaseAdapter):
    """Wraps the OpenCode CLI for local codebase edits."""

    id = "opencode"
    requires: tuple[str, ...] = ()

    def available(self) -> bool:
        return shutil.which("opencode") is not None

    def run(self, request: dict[str, Any]) -> AdapterResult:
        if not self.available():
            return self._degraded(request)
        return self._degraded(request, note="opencode binary present but real mode is opt-in")

    def _degraded(self, request: dict[str, Any], *, note: str | None = None) -> AdapterResult:
        repo_path = str(request.get("repo_path") or "")
        notes = [
            "opencode unavailable: `opencode` not on PATH; no code agent run "
            "performed (no files changed)"
        ]
        if repo_path:
            notes.append(f"requested repo_path: {repo_path}")
        if note:
            notes.append(note)
        return AdapterResult(
            adapter=self.id,
            degraded=True,
            notes=notes,
        )


register(OpenCodeAdapter())

__all__ = ["OpenCodeAdapter"]
