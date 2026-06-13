"""Deterministic YAML + JSON I/O helpers.

All artifacts are Markdown/YAML so reads/writes must be stable and diff-friendly:
keys preserve insertion order, strings stay readable, and multi-line text uses
block scalars. Built on PyYAML with a couple of representer tweaks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class _RFDumper(yaml.SafeDumper):
    """SafeDumper that keeps insertion order and emits readable block scalars."""


def _str_representer(dumper, data):  # noqa: ANN001  (PyYAML calls this as a method)
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_RFDumper.add_representer(str, _str_representer)  # type: ignore[arg-type]


def dumps_yaml(obj: Any) -> str:
    """Serialize ``obj`` to a deterministic YAML string (insertion order kept)."""

    return yaml.dump(
        obj,
        Dumper=_RFDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


def loads_yaml(text: str) -> Any:
    """Parse a YAML string. Empty/whitespace input returns ``None``."""

    return yaml.safe_load(text) if text and text.strip() else None


def load_yaml(path: str | Path) -> Any:
    """Load a YAML file. Missing file raises ``FileNotFoundError``."""

    return loads_yaml(Path(path).read_text(encoding="utf-8"))


def dump_yaml(obj: Any, path: str | Path) -> Path:
    """Write ``obj`` as YAML to ``path`` (creating parent dirs). Returns the path."""

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps_yaml(obj), encoding="utf-8")
    return p


def load_jsonl(path: str | Path) -> list[Any]:
    """Read a JSON-lines file into a list (skips blank lines)."""

    out: list[Any] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def append_jsonl(obj: Any, path: str | Path) -> Path:
    """Append one JSON object as a line to ``path`` (creating parent dirs)."""

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return p


__all__ = [
    "dumps_yaml",
    "loads_yaml",
    "load_yaml",
    "dump_yaml",
    "load_jsonl",
    "append_jsonl",
]
