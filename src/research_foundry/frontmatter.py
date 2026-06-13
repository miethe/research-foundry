"""Markdown front matter split/join.

Source cards and reports are Markdown files with a YAML front-matter block
delimited by ``---`` fences. This module converts between
``(metadata: dict, body: str)`` and the on-disk text, without a third-party
dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .yamlio import dumps_yaml, loads_yaml

_FENCE = "---"


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(metadata, body)`` from front-mattered Markdown.

    If the text has no leading ``---`` fence, metadata is ``{}`` and the whole
    text is the body.
    """

    if not text.startswith(_FENCE):
        return {}, text
    lines = text.splitlines()
    # lines[0] == '---'; find the closing fence.
    for i in range(1, len(lines)):
        if lines[i].strip() == _FENCE:
            meta_block = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            meta = loads_yaml(meta_block) or {}
            if not isinstance(meta, dict):
                meta = {}
            return meta, body.lstrip("\n")
    # No closing fence — treat as body.
    return {}, text


def join_frontmatter(metadata: dict[str, Any], body: str) -> str:
    """Compose front-mattered Markdown text from metadata + body."""

    meta_yaml = dumps_yaml(metadata).rstrip("\n") if metadata else ""
    body = body or ""
    return f"{_FENCE}\n{meta_yaml}\n{_FENCE}\n\n{body.lstrip(chr(10))}".rstrip("\n") + "\n"


def load_md(path: str | Path) -> tuple[dict[str, Any], str]:
    """Read a front-mattered Markdown file → ``(metadata, body)``."""

    return split_frontmatter(Path(path).read_text(encoding="utf-8"))


def dump_md(metadata: dict[str, Any], body: str, path: str | Path) -> Path:
    """Write ``(metadata, body)`` to a front-mattered Markdown file."""

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(join_frontmatter(metadata, body), encoding="utf-8")
    return p


__all__ = ["split_frontmatter", "join_frontmatter", "load_md", "dump_md"]
