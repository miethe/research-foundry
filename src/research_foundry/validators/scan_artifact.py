"""PostToolUse Claude Code hook (spec §7.3).

After a Write/Edit, secret-scans the written file and lints claim labels in
Markdown reports. Warnings are **non-blocking**: it always exits ``0`` and only
prints an advisory JSON payload when something looks off.

Safe no-op when there is no stdin or the target file is unreadable.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Material-claim phrasing that should carry an explicit claim label/id.
_MATERIAL_HINT = re.compile(
    r"\b(proves?|demonstrates?|shows? that|confirms?|guarantees?|always|never|"
    r"\d+\s*%|\d+x\b)",
    re.IGNORECASE,
)
_LABEL_HINT = re.compile(
    r"(claim_id|\[supported\]|\[inference\]|\[speculation\]|\[unsupported\]|"
    r"supported|inference|speculation)",
    re.IGNORECASE,
)


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


def _target_path(data: dict[str, Any]) -> str:
    tool_input = data.get("tool_input") or data.get("toolInput") or {}
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "filename"):
            val = tool_input.get(key)
            if isinstance(val, str):
                return val
    resp = data.get("tool_response") or data.get("toolResponse") or {}
    if isinstance(resp, dict):
        for key in ("filePath", "file_path", "path"):
            val = resp.get(key)
            if isinstance(val, str):
                return val
    return ""


def _scan_secrets(text: str) -> list[str]:
    try:
        from ..config import FoundryConfig
        from ..paths import FoundryPaths
        from ..services.governance import scan_secrets

        cfg = FoundryConfig(paths=FoundryPaths.discover())
        return scan_secrets(text, config=cfg)
    except Exception:  # noqa: BLE001 — never crash a PostToolUse hook
        return []


def _lint_claims(text: str, path: str) -> list[str]:
    """Warn when a Markdown report makes material claims with no labels."""

    if not path.lower().endswith((".md", ".markdown")):
        return []
    warnings: list[str] = []
    has_material = bool(_MATERIAL_HINT.search(text))
    has_labels = bool(_LABEL_HINT.search(text))
    if has_material and not has_labels:
        warnings.append(
            "Report contains material-claim phrasing but no claim labels "
            "(supported/inference/speculation/claim_id)."
        )
    return warnings


def _emit(warnings: list[str]) -> int:
    if not warnings:
        print(json.dumps({"decision": "allow"}))
        return 0
    print(
        json.dumps(
            {
                "decision": "allow",
                "warnings": warnings,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": " ".join(warnings),
                },
            }
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Always returns ``0`` (non-blocking advisory)."""

    data = _read_stdin()
    if not data:
        return _emit([])

    target = _target_path(data)
    if not target:
        return _emit([])

    path = Path(target)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _emit([])

    warnings: list[str] = []
    hits = _scan_secrets(text)
    if hits:
        warnings.append(
            f"Potential secret detected in {path.name} ({len(hits)} match(es))."
        )
    warnings.extend(_lint_claims(text, target))
    return _emit(warnings)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
