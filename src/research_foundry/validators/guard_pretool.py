"""PreToolUse Claude Code hook (spec §7.3).

Reads a Claude Code hook payload from stdin (``tool_name``, ``tool_input``),
runs a lightweight governance preflight: secret-scans Write/Edit content and
flags reads/writes to ``.env``/secret paths. Prints a JSON decision and exits:

* ``0`` + ``{"decision": "allow"}`` — proceed.
* non-zero + ``{"decision": "deny", ...}`` — block the tool call.

Safe no-op when there is no stdin or no workspace: prints an allow decision and
exits ``0`` so it never wedges an interactive session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Paths that should never be read/written by a tool call (spec §7.3 caution).
_SECRET_PATH_HINTS = (".env", "id_rsa", "id_ed25519", ".pem", "credentials")
_GUARD_TOOLS = {"Write", "Edit", "MultiEdit"}


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


def _extract_content(tool_input: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("content", "new_string", "new_str", "text"):
        val = tool_input.get(key)
        if isinstance(val, str):
            parts.append(val)
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for e in edits:
            if isinstance(e, dict) and isinstance(e.get("new_string"), str):
                parts.append(e["new_string"])
    return "\n".join(parts)


def _extract_target_path(tool_input: dict[str, Any]) -> str:
    for key in ("file_path", "path", "filename"):
        val = tool_input.get(key)
        if isinstance(val, str):
            return val
    return ""


def _touches_secret_path(target: str) -> bool:
    low = target.lower()
    return any(hint in low for hint in _SECRET_PATH_HINTS)


def _emit(decision: str, *, reason: str = "", violations: list[str] | None = None) -> int:
    payload: dict[str, Any] = {"decision": decision}
    if reason:
        payload["reason"] = reason
    if violations:
        payload["violations"] = violations
    # Hook-spec friendly fields (PreToolUse permissionDecision).
    if decision == "deny":
        payload["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason or "Governance guard blocked this tool call.",
        }
    print(json.dumps(payload))
    return 0 if decision == "allow" else 2


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the desired process exit code."""

    data = _read_stdin()
    if not data:
        return _emit("allow")

    tool_name = data.get("tool_name") or data.get("toolName") or ""
    tool_input = data.get("tool_input") or data.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    target = _extract_target_path(tool_input)
    if _touches_secret_path(target):
        return _emit(
            "deny",
            reason=f"Refusing tool access to a secret-bearing path: {target}",
            violations=["secret_path_access"],
        )

    if tool_name in _GUARD_TOOLS:
        content = _extract_content(tool_input)
        if content:
            hits = _scan(content)
            if hits:
                return _emit(
                    "deny",
                    reason="Potential secret detected in tool content; write blocked.",
                    violations=["no_secret_in_markdown"],
                )

    return _emit("allow")


def _scan(text: str) -> list[str]:
    """Secret-scan ``text`` via the governance service, degrading on import error."""

    try:
        from ..config import FoundryConfig
        from ..paths import FoundryPaths
        from ..services.governance import scan_secrets

        cfg = FoundryConfig(paths=FoundryPaths.discover())
        return scan_secrets(text, config=cfg)
    except Exception:  # noqa: BLE001 — hooks must never crash the session
        return _scan_builtin(text)


def _scan_builtin(text: str) -> list[str]:
    """Minimal built-in secret scan used when the package context is unavailable."""

    import re

    patterns = (
        r"sk-ant-[A-Za-z0-9_\-]{20,}",
        r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{36,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN[ A-Z]*PRIVATE KEY-----",
    )
    hits: list[str] = []
    for p in patterns:
        m = re.search(p, text)
        if m:
            hits.append(m.group(0))
    return hits


def _is_workspace() -> bool:
    """True when invoked from inside a foundry workspace (best-effort)."""

    try:
        from ..paths import find_workspace_root

        root = find_workspace_root()
        return (root / "foundry.yaml").exists()
    except Exception:  # noqa: BLE001
        return Path("foundry.yaml").exists()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
