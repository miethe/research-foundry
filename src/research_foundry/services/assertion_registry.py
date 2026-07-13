"""Private, file-canonical edition and passage registry for assertion-only reuse.

The registry is deliberately separate from run-local source cards.  Callers opt
in with a workspace id; no assertion or canonical-claim feature flag is enabled
by this module.  Records are immutable YAML files and every replacement write
uses ``os.replace`` so a reader observes either the previous complete record or
the next complete record.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, load_yaml


def _digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _atomic_dump(data: Mapping[str, Any], path: Path) -> None:
    """Atomically replace one YAML artifact without exposing partial YAML."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps_yaml(dict(data)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


@dataclass(frozen=True)
class PassageResolution:
    """Typed reuse decision; drift never silently returns reusable content."""

    reusable: bool
    passage: dict[str, Any] | None
    reason: str | None = None


@dataclass(frozen=True)
class RegistryImportResult:
    source_id: str
    edition: dict[str, Any] | None
    passages: tuple[dict[str, Any], ...]
    created: bool
    reusable: bool
    reason: str | None = None


class AssertionRegistry:
    """Workspace-isolated persistence for immutable editions and passages."""

    _SUPPORTED_MEDIA_TYPES = {"text/plain", "text/html", "application/pdf", "text/ocr"}

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        # Do not put a tenant-supplied string into the path or into another tenant's lookup key.
        self.workspace_key = _digest(workspace_id)
        self.root = self.paths.root / "assertion_ledger" / "workspaces" / self.workspace_key

    def _source_id(self, source_key: str) -> str:
        if not source_key:
            raise ValueError("source_key is required")
        return f"src_{_digest(f'{self.workspace_key}:{source_key}') }"

    def _source_dir(self, source_id: str) -> Path:
        return self.root / "sources" / source_id

    def _source_manifest(self, source_id: str) -> Path:
        return self._source_dir(source_id) / "source.yaml"

    def _edition_path(self, source_id: str, edition_id: str) -> Path:
        return self._source_dir(source_id) / "editions" / f"{edition_id}.yaml"

    def _passage_path(self, source_id: str, edition_id: str, passage_id: str) -> Path:
        return self._source_dir(source_id) / "editions" / edition_id / "passages" / f"{passage_id}.yaml"

    def ingest(
        self,
        source_key: str,
        content: str | bytes | None,
        *,
        media_type: str = "text/plain",
        access_scope: str = "private",
        allowed_use: Mapping[str, Any] | None = None,
        retrieval_locator: Mapping[str, Any] | None = None,
        passages: Sequence[str] | None = None,
        metadata_extensions: Mapping[str, Any] | None = None,
        _interrupt_after_edition_write: bool = False,
    ) -> RegistryImportResult:
        """Persist an immutable edition and deterministic passage records.

        Unsupported or missing content is a typed non-reusable result.  The
        existing source manifest is untouched in that case.
        """

        source_id = self._source_id(source_key)
        if media_type not in self._SUPPORTED_MEDIA_TYPES or content is None:
            return RegistryImportResult(source_id, None, (), False, False, "unsupported_or_missing_content")
        if not allowed_use:
            return RegistryImportResult(source_id, None, (), False, False, "missing_rights_metadata")
        raw = content.encode("utf-8") if isinstance(content, str) else content
        if not raw:
            return RegistryImportResult(source_id, None, (), False, False, "unsupported_or_missing_content")

        content_sha256 = _digest(raw)
        edition_id = f"sed_{content_sha256}"
        manifest_path = self._source_manifest(source_id)
        manifest = load_yaml(manifest_path) if manifest_path.exists() else {"source_id": source_id, "edition_ids": []}
        edition_ids = list(manifest.get("edition_ids", []))
        edition_path = self._edition_path(source_id, edition_id)
        selected = list(passages) if passages is not None else [raw.decode("utf-8", errors="replace")]
        if len({_normalise(text) for text in selected}) != len(selected):
            return RegistryImportResult(source_id, None, (), False, False, "ambiguous_selector")
        if edition_path.exists() and edition_id in edition_ids:
            edition = load_yaml(edition_path)
            return RegistryImportResult(source_id, edition, tuple(self._load_passages(source_id, edition_id)), False, True)

        predecessor = edition_ids[-1] if edition_ids else None
        normalized_content = _normalise(raw.decode("utf-8", errors="replace"))
        edition = {
            "schema_version": "1.0", "type": "source_edition", "source_edition_id": edition_id,
            "content_sha256": content_sha256, "source_id": source_id, "media_type": media_type,
            "captured_at": now_iso(), "retrieval_locator": dict(retrieval_locator or {}),
            "predecessor_edition_id": predecessor, "access_scope": access_scope,
            "metadata_extensions": {
                **dict(metadata_extensions or {}),
                "raw_content_sha256": content_sha256,
                "normalized_content_sha256": _digest(normalized_content),
                "allowed_use": dict(allowed_use),
            },
        }
        passage_records = [self._passage(edition_id, text, index) for index, text in enumerate(selected)]

        # Write immutable children first; publish the manifest last.
        _atomic_dump(edition, edition_path)
        if _interrupt_after_edition_write:
            raise RuntimeError("simulated atomic-write interruption")
        for passage in passage_records:
            _atomic_dump(passage, self._passage_path(source_id, edition_id, passage["passage_id"]))
        manifest["edition_ids"] = [*edition_ids, edition_id]
        manifest["updated_at"] = now_iso()
        _atomic_dump(manifest, manifest_path)
        return RegistryImportResult(source_id, edition, tuple(passage_records), True, True)

    def resolve_passage(self, source_key: str, edition_id: str, passage_id: str, raw_text: str | bytes) -> PassageResolution:
        """Resolve only an exact passage; changes become an explicit drift result."""

        source_id = self._source_id(source_key)
        path = self._passage_path(source_id, edition_id, passage_id)
        if not path.exists():
            return PassageResolution(False, None, "unresolved")
        passage = load_yaml(path)
        if passage.get("raw_text_sha256") != _digest(raw_text):
            return PassageResolution(False, passage, "drift")
        return PassageResolution(True, passage)

    def _load_passages(self, source_id: str, edition_id: str) -> list[dict[str, Any]]:
        directory = self._source_dir(source_id) / "editions" / edition_id / "passages"
        return [load_yaml(path) for path in sorted(directory.glob("*.yaml"))] if directory.exists() else []

    def _passage(self, edition_id: str, raw_text: str, index: int) -> dict[str, Any]:
        normalized = _normalise(raw_text)
        raw_digest, normalized_digest = _digest(raw_text), _digest(normalized)
        selectors = [
            {"kind": "position", "value": f"0:{len(raw_text)}", "confidence": 1.0},
            {"kind": "structural", "value": f"passage:{index}", "confidence": 1.0},
            {"kind": "hash", "value": raw_digest, "confidence": 1.0},
        ]
        passage_id = f"psg_{_digest(f'{edition_id}:{raw_digest}:{index}') }"
        return {
            "schema_version": "1.0", "type": "passage", "passage_id": passage_id,
            "source_edition_id": edition_id, "normalized_text": normalized,
            "normalized_text_sha256": normalized_digest, "raw_text_sha256": raw_digest,
            "selectors": selectors, "predecessor_passage_id": None,
            "normalization": {"algorithm": "collapse-whitespace", "version": "1.0"},
            "context": {"exact_quote": raw_text, "passage_index": index},
        }


__all__ = ["AssertionRegistry", "PassageResolution", "RegistryImportResult"]
