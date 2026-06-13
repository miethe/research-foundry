"""Lightweight indexes over the Markdown/YAML artifacts.

Registries (``registries/*.yaml``) index artifacts for fast lookup but never
replace them — the Markdown/YAML files remain the source of truth (spec §5
folder rules). Each registry is a YAML file with a top-level ``items`` list of
records keyed by ``id``; :meth:`Registry.upsert` is idempotent on ``id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ids import now_iso
from .paths import FoundryPaths
from .yamlio import dump_yaml, load_yaml

# Known registry files (spec §5 registries/).
RUN_INDEX = "run_index.yaml"
SOURCE_INDEX = "source_index.yaml"
CLAIM_INDEX = "claim_index.yaml"
REPORT_INDEX = "report_index.yaml"
SKILLBOM_INDEX = "skillbom_index.yaml"
AGENTS = "agents.yaml"
TOOLS = "tools.yaml"


@dataclass
class Registry:
    """An append/upsert index stored at ``registries/<filename>``."""

    path: Path
    key: str = "id"

    @classmethod
    def open(cls, name: str, *, paths: FoundryPaths | None = None, key: str = "id") -> "Registry":
        p = (paths or FoundryPaths.discover()).registries / name
        return cls(path=p, key=key)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"items": []}
        data = load_yaml(self.path)
        if not isinstance(data, dict):
            data = {"items": []}
        data.setdefault("items", [])
        return data

    def items(self) -> list[dict[str, Any]]:
        return list(self._read().get("items", []))

    def get(self, ident: str) -> dict[str, Any] | None:
        for item in self.items():
            if item.get(self.key) == ident:
                return item
        return None

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert or replace ``record`` keyed by :attr:`key`. Returns the record."""

        ident = record.get(self.key)
        if ident is None:
            raise ValueError(f"record missing key {self.key!r}: {record}")
        record = {**record, "indexed_at": now_iso()}
        data = self._read()
        items = data["items"]
        for i, existing in enumerate(items):
            if existing.get(self.key) == ident:
                items[i] = record
                break
        else:
            items.append(record)
        data["items"] = items
        data["count"] = len(items)
        data["updated_at"] = now_iso()
        dump_yaml(data, self.path)
        return record


__all__ = [
    "Registry",
    "RUN_INDEX",
    "SOURCE_INDEX",
    "CLAIM_INDEX",
    "REPORT_INDEX",
    "SKILLBOM_INDEX",
    "AGENTS",
    "TOOLS",
]
