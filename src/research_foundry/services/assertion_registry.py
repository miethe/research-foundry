"""Private, file-canonical edition and passage registry for assertion-only reuse.

The registry is deliberately separate from run-local source cards.  Callers opt
in with a workspace id; no assertion or canonical-claim feature flag is enabled
by this module.  Records are immutable YAML files and every replacement write
uses ``os.replace`` so a reader observes either the previous complete record or
the next complete record.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, loads_yaml

_SOURCE_ID_RE = re.compile(r"^src_[a-f0-9]{64}$")
_EDITION_ID_RE = re.compile(r"^sed_[a-f0-9]{64}$")
_PASSAGE_ID_RE = re.compile(r"^psg_[a-f0-9]{64}$")
_GENERATION_ID_RE = re.compile(r"^gen_[a-f0-9]{64}$")


class RegistryIntegrityError(ValueError):
    """A persisted registry pointer is malformed or escapes its workspace."""


def _digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _digest(encoded)


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


def _atomic_write_bytes(data: bytes, path: Path) -> None:
    """Atomically persist a rendition without exposing partial edition bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class _PassageSelectionError(ValueError):
    """A caller-supplied passage cannot be bound to a unique edition range."""


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
        self._require_id(source_id, _SOURCE_ID_RE, "source_id")
        return self.root / "sources" / source_id

    def _source_manifest(self, source_id: str) -> Path:
        return self._source_dir(source_id) / "source.yaml"

    def _edition_path(self, source_id: str, edition_id: str) -> Path:
        self._require_id(edition_id, _EDITION_ID_RE, "source_edition_id")
        return self._source_dir(source_id) / "editions" / f"{edition_id}.yaml"

    def _edition_dir(self, source_id: str, edition_id: str) -> Path:
        self._require_id(edition_id, _EDITION_ID_RE, "source_edition_id")
        return self._source_dir(source_id) / "editions" / edition_id

    def _content_path(self, source_id: str, edition_id: str) -> Path:
        return self._edition_dir(source_id, edition_id) / "content.bin"

    def _provenance_path(self, source_id: str, edition_id: str) -> Path:
        return self._edition_dir(source_id, edition_id) / "provenance.yaml"

    def _publication_path(self, source_id: str, edition_id: str) -> Path:
        return self._edition_dir(source_id, edition_id) / "published.yaml"

    def _generation_path(self, source_id: str, edition_id: str, generation_id: str, passage_id: str) -> Path:
        self._require_id(generation_id, _GENERATION_ID_RE, "generation_id")
        self._require_id(passage_id, _PASSAGE_ID_RE, "passage_id")
        return self._edition_dir(source_id, edition_id) / "generations" / generation_id / "passages" / f"{passage_id}.yaml"

    @staticmethod
    def source_card_snapshot(source_card_id: str, source_card: Mapping[str, Any]) -> dict[str, Any]:
        """Return the stable source-card fields that P3 is allowed to trust.

        Timestamps and report prose are intentionally excluded so historical
        runs of the same source retain one edition.  Rights, retrieval locator,
        and the exact evidence points are included and therefore immutable for
        materialization purposes.
        """

        if source_card.get("source_card_id") != source_card_id:
            raise RegistryIntegrityError("source card does not bind the expected source key")
        source = source_card.get("source")
        usage = source_card.get("usage")
        sensitivity = source_card.get("sensitivity")
        if not isinstance(source, Mapping) or not isinstance(usage, Mapping):
            raise RegistryIntegrityError("source card omits rights provenance")
        if not isinstance(sensitivity, str) or not sensitivity:
            raise RegistryIntegrityError("source card omits access scope")
        locator = source.get("locator")
        if not isinstance(locator, Mapping):
            raise RegistryIntegrityError("source card omits retrieval locator")
        points = source_card.get("extracted_points")
        if not isinstance(points, list):
            raise RegistryIntegrityError("source card omits evidence points")
        evidence_points: list[dict[str, str | None]] = []
        for point in points:
            if not isinstance(point, Mapping):
                raise RegistryIntegrityError("source card has invalid evidence point")
            evidence_id = point.get("evidence_id")
            point_locator = point.get("locator")
            quote = point.get("quote")
            if not isinstance(evidence_id, str) or not isinstance(point_locator, str):
                raise RegistryIntegrityError("source card has invalid evidence point")
            if quote is not None and not isinstance(quote, str):
                raise RegistryIntegrityError("source card has invalid evidence quote")
            evidence_points.append(
                {"evidence_id": evidence_id, "locator": point_locator, "quote": quote}
            )
        return {
            "source_card_id": source_card_id,
            "access_scope": sensitivity,
            "allowed_use": dict(usage),
            "retrieval_locator": {
                "url": locator.get("url"),
                "file_path": locator.get("file_path"),
            },
            "evidence_points": evidence_points,
        }

    def verify_source_card_binding(
        self,
        source_key: str,
        edition: Mapping[str, Any],
        source_card: Mapping[str, Any],
    ) -> None:
        """Reject a registry edition whose source-card snapshot no longer binds."""

        source_id = self._source_id(source_key)
        edition_id = self._require_id(edition.get("source_edition_id"), _EDITION_ID_RE, "source_edition_id")
        verified = self._load_edition(source_id, edition_id)
        if dict(edition) != verified:
            raise RegistryIntegrityError("selected edition changed during verification")
        provenance = self._load_provenance(source_id, edition_id, verified)
        expected = provenance.get("source_card_snapshot")
        if not isinstance(expected, Mapping):
            raise RegistryIntegrityError("edition omits source-card provenance snapshot")
        actual = self.source_card_snapshot(source_key, source_card)
        if _canonical_digest(dict(expected)) != _canonical_digest(actual):
            raise RegistryIntegrityError("source-card provenance snapshot mismatch")

    def _provenance_record(
        self, edition: Mapping[str, Any], source_card_snapshot: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        binding = self._edition_binding(edition)
        snapshot = None if source_card_snapshot is None else dict(source_card_snapshot)
        return {
            "schema_version": "1.0",
            "type": "source_edition_provenance",
            "source_id": binding["source_id"],
            "source_edition_id": binding["source_edition_id"],
            "content_sha256": binding["content_sha256"],
            "edition_binding": binding,
            "edition_binding_sha256": _canonical_digest(binding),
            "source_card_snapshot": snapshot,
        }

    @staticmethod
    def _edition_binding(edition: Mapping[str, Any]) -> dict[str, Any]:
        source_edition_id = edition.get("source_edition_id")
        source_id = edition.get("source_id")
        content_sha256 = edition.get("content_sha256")
        media_type = edition.get("media_type")
        access_scope = edition.get("access_scope")
        retrieval_locator = edition.get("retrieval_locator")
        extensions = edition.get("metadata_extensions")
        if not all(isinstance(value, str) and value for value in (source_edition_id, source_id, content_sha256, media_type, access_scope)):
            raise RegistryIntegrityError("source edition omits immutable identity metadata")
        if not isinstance(retrieval_locator, Mapping) or not isinstance(extensions, Mapping):
            raise RegistryIntegrityError("source edition omits immutable provenance metadata")
        allowed_use = extensions.get("allowed_use")
        raw_content_sha256 = extensions.get("raw_content_sha256")
        normalized_content_sha256 = extensions.get("normalized_content_sha256")
        if not isinstance(allowed_use, Mapping) or not allowed_use:
            raise RegistryIntegrityError("source edition omits immutable rights metadata")
        if not isinstance(raw_content_sha256, str) or not isinstance(normalized_content_sha256, str):
            raise RegistryIntegrityError("source edition omits immutable content metadata")
        return {
            "source_id": source_id,
            "source_edition_id": source_edition_id,
            "content_sha256": content_sha256,
            "media_type": media_type,
            "access_scope": access_scope,
            "retrieval_locator": dict(retrieval_locator),
            "allowed_use": dict(allowed_use),
            "raw_content_sha256": raw_content_sha256,
            "normalized_content_sha256": normalized_content_sha256,
        }

    def _read_regular_file(self, path: Path, expected_directory: Path) -> bytes:
        """Read one in-root regular file without following path substitutions.

        The directory-descriptor walk pins every component beneath this registry
        workspace.  ``O_NOFOLLOW`` protects each component where the platform
        supports it; the ``fstat`` checks retain a regular-file boundary on
        platforms without that flag.
        """

        try:
            relative_file = path.relative_to(self.root)
            relative_directory = expected_directory.relative_to(self.root)
        except ValueError as exc:
            raise RegistryIntegrityError("registry path escapes its workspace") from exc
        if relative_file.parent != relative_directory or not relative_file.parts:
            raise RegistryIntegrityError("registry file is outside its expected directory")

        no_follow = getattr(os, "O_NOFOLLOW", 0)
        root_fd: int | None = None
        directory_fds: list[int] = []
        file_fd: int | None = None

        def open_component(name: str | Path, *, directory: bool, parent_fd: int | None) -> int:
            before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                raise RegistryIntegrityError("registry artifact symlink rejected")
            flags = os.O_RDONLY | no_follow
            if directory:
                flags |= getattr(os, "O_DIRECTORY", 0)
            descriptor = os.open(name, flags, dir_fd=parent_fd)
            after = os.fstat(descriptor)
            if (
                before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or (directory and not stat.S_ISDIR(after.st_mode))
                or (not directory and not stat.S_ISREG(after.st_mode))
            ):
                os.close(descriptor)
                raise RegistryIntegrityError("registry artifact path substitution rejected")
            return descriptor

        try:
            root_fd = open_component(self.paths.root, directory=True, parent_fd=None)
            current_fd = root_fd
            workspace_parts = ("assertion_ledger", "workspaces", self.workspace_key)
            for part in (*workspace_parts, *relative_directory.parts):
                next_fd = open_component(part, directory=True, parent_fd=current_fd)
                directory_fds.append(next_fd)
                current_fd = next_fd
            file_fd = open_component(relative_file.name, directory=False, parent_fd=current_fd)
            with os.fdopen(file_fd, "rb", closefd=True) as handle:
                file_fd = None
                return handle.read()
        except FileNotFoundError:
            raise
        except RegistryIntegrityError:
            raise
        except OSError as exc:
            raise RegistryIntegrityError("registry artifact path substitution rejected") from exc
        finally:
            if file_fd is not None:
                os.close(file_fd)
            for descriptor in reversed(directory_fds):
                os.close(descriptor)
            if root_fd is not None:
                os.close(root_fd)

    def _load_yaml_file(self, path: Path, expected_directory: Path) -> Any:
        try:
            return loads_yaml(self._read_regular_file(path, expected_directory).decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise RegistryIntegrityError("registry YAML artifact is not UTF-8") from exc

    def _write_immutable_mapping(self, data: Mapping[str, Any], path: Path) -> None:
        try:
            existing = self._load_yaml_file(path, path.parent)
        except FileNotFoundError:
            _atomic_dump(data, path)
            return
        if not isinstance(existing, Mapping) or dict(existing) != dict(data):
            raise RegistryIntegrityError("immutable registry record conflicts with existing bytes")

    def _write_immutable_bytes(self, data: bytes, path: Path) -> None:
        try:
            existing = self._read_regular_file(path, path.parent)
        except FileNotFoundError:
            _atomic_write_bytes(data, path)
            return
        if existing != data:
            raise RegistryIntegrityError("immutable edition content conflicts with existing bytes")

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
        source_card_snapshot: Mapping[str, Any] | None = None,
        _interrupt_after_edition_write: bool = False,
        _interrupt_before_generation_publish: bool = False,
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
        raw_text = raw.decode("utf-8", errors="replace")
        selected = list(passages) if passages is not None else [raw_text]
        if any(not isinstance(text, str) or not text for text in selected):
            return RegistryImportResult(source_id, None, (), False, False, "invalid_passage_selector")
        if len({_normalise(text) for text in selected}) != len(selected):
            return RegistryImportResult(source_id, None, (), False, False, "ambiguous_selector")
        try:
            passage_records = [
                self._passage(
                    edition_id,
                    raw,
                    text,
                    index,
                    allow_full_rendition=passages is None,
                )
                for index, text in enumerate(selected)
            ]
        except _PassageSelectionError as exc:
            return RegistryImportResult(source_id, None, (), False, False, str(exc))

        manifest_path = self._source_manifest(source_id)
        manifest = (
            self._load_source_manifest(source_id)
            if manifest_path.exists()
            else {"source_id": source_id, "edition_ids": []}
        )
        edition_ids = list(manifest.get("edition_ids", []))
        edition_path = self._edition_path(source_id, edition_id)
        if edition_path.exists() and edition_id in edition_ids:
            edition = self._load_edition(source_id, edition_id)
            try:
                self._verify_expected_source_snapshot(source_id, edition_id, source_card_snapshot)
            except RegistryIntegrityError as exc:
                return RegistryImportResult(source_id, None, (), False, False, str(exc))
            existing = {passage["passage_id"]: passage for passage in self._load_passages(source_id, edition_id)}
            changed = False
            for passage in passage_records:
                if passage["passage_id"] not in existing:
                    existing[passage["passage_id"]] = passage
                    changed = True
            if changed:
                self._publish_passages(source_id, edition_id, existing, _interrupt_before_generation_publish)
            return RegistryImportResult(source_id, edition, tuple(existing[key] for key in sorted(existing)), False, True)

        predecessor = edition_ids[-1] if edition_ids else None
        normalized_content = _normalise(raw_text)
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
        provenance = self._provenance_record(edition, source_card_snapshot)
        # Write immutable children first; publish the manifest last.
        self._write_immutable_bytes(raw, self._content_path(source_id, edition_id))
        self._write_immutable_mapping(provenance, self._provenance_path(source_id, edition_id))
        self._write_immutable_mapping(edition, edition_path)
        if _interrupt_after_edition_write:
            raise RuntimeError("simulated atomic-write interruption")
        self._publish_passages(source_id, edition_id, {p["passage_id"]: p for p in passage_records}, _interrupt_before_generation_publish)
        manifest["edition_ids"] = [*edition_ids, edition_id]
        manifest["updated_at"] = now_iso()
        _atomic_dump(manifest, manifest_path)
        return RegistryImportResult(source_id, edition, tuple(passage_records), True, True)

    def resolve_passage(self, source_key: str, edition_id: str, passage_id: str, raw_text: str | bytes) -> PassageResolution:
        """Resolve only an exact passage; changes become an explicit drift result."""

        source_id = self._source_id(source_key)
        passage = next((item for item in self._load_passages(source_id, edition_id) if item["passage_id"] == passage_id), None)
        if passage is None:
            return PassageResolution(False, None, "unresolved")
        if passage.get("raw_text_sha256") != _digest(raw_text):
            return PassageResolution(False, passage, "drift")
        return PassageResolution(True, passage)

    def find_exact_passages(
        self, source_key: str, raw_text: str | bytes
    ) -> tuple[tuple[dict[str, Any], dict[str, Any]], ...]:
        """Return integrity-checked passages whose exact raw text matches.

        More than one result is intentionally an ambiguity.  P3 must abstain,
        not pick a newer edition or a similar-looking passage.
        """

        source_id = self._source_id(source_key)
        if not self._source_manifest(source_id).exists():
            return ()
        manifest = self._load_source_manifest(source_id)
        expected_digest = _digest(raw_text)
        matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for edition_id in manifest["edition_ids"]:
            edition = self._load_edition(source_id, edition_id)
            for passage in self._load_passages(source_id, edition_id):
                if passage.get("raw_text_sha256") == expected_digest:
                    matches.append((edition, passage))
        return tuple(matches)

    def _load_passages(self, source_id: str, edition_id: str) -> list[dict[str, Any]]:
        edition = self._load_edition(source_id, edition_id)
        raw = self._load_edition_content(source_id, edition_id, edition)
        publication = self._publication_path(source_id, edition_id)
        missing = object()
        try:
            data: Any = self._load_yaml_file(publication, self._edition_dir(source_id, edition_id))
        except FileNotFoundError:
            data = missing
        if data is not missing:
            if not isinstance(data, Mapping):
                raise RegistryIntegrityError("published passage pointer must be a mapping")
            generation_id = self._require_id(
                data.get("generation_id"), _GENERATION_ID_RE, "generation_id"
            )
            passage_ids = data.get("passage_ids")
            if not isinstance(passage_ids, list) or not passage_ids or len(set(passage_ids)) != len(passage_ids):
                raise RegistryIntegrityError("published passage pointer must contain unique passage_ids")
            if passage_ids != sorted(passage_ids):
                raise RegistryIntegrityError("published passage_ids must be sorted")
            return [
                self._load_passage_file(
                    self._generation_path(source_id, edition_id, generation_id, passage_id),
                    edition_id,
                    passage_id,
                    raw,
                )
                for passage_id in passage_ids
            ]
        directory = self._edition_dir(source_id, edition_id) / "passages"
        if not directory.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.yaml")):
            self._require_id(path.stem, _PASSAGE_ID_RE, "passage_id")
            records.append(self._load_passage_file(path, edition_id, path.stem, raw))
        return records

    def list_passages(self, source_key: str, edition_id: str) -> tuple[dict[str, Any], ...]:
        """Return only the atomically published passage generation."""
        return tuple(self._load_passages(self._source_id(source_key), edition_id))

    def _publish_passages(self, source_id: str, edition_id: str, passages: Mapping[str, dict[str, Any]], interrupt: bool) -> None:
        passage_ids = sorted(passages)
        generation_id = f"gen_{_digest(':'.join(passage_ids))}"
        for passage_id in passage_ids:
            _atomic_dump(passages[passage_id], self._generation_path(source_id, edition_id, generation_id, passage_id))
        if interrupt:
            raise RuntimeError("simulated generation publication interruption")
        _atomic_dump({"generation_id": generation_id, "passage_ids": passage_ids}, self._publication_path(source_id, edition_id))

    @staticmethod
    def _require_id(value: object, pattern: re.Pattern[str], label: str) -> str:
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise RegistryIntegrityError(f"invalid {label}")
        return value

    def _load_source_manifest(self, source_id: str) -> dict[str, Any]:
        data = self._load_yaml_file(self._source_manifest(source_id), self._source_dir(source_id))
        if not isinstance(data, dict) or data.get("source_id") != source_id:
            raise RegistryIntegrityError("source manifest does not bind the expected source_id")
        edition_ids = data.get("edition_ids")
        if not isinstance(edition_ids, list) or len(set(edition_ids)) != len(edition_ids):
            raise RegistryIntegrityError("source manifest must contain unique edition_ids")
        for edition_id in edition_ids:
            self._require_id(edition_id, _EDITION_ID_RE, "source_edition_id")
        return data

    def _load_edition(self, source_id: str, edition_id: str) -> dict[str, Any]:
        data = self._load_yaml_file(
            self._edition_path(source_id, edition_id), self._source_dir(source_id) / "editions"
        )
        if not isinstance(data, dict):
            raise RegistryIntegrityError("source edition must be a mapping")
        if data.get("source_edition_id") != edition_id or data.get("source_id") != source_id:
            raise RegistryIntegrityError("source edition does not bind the expected source and edition")
        raw = self._load_edition_content(source_id, edition_id, data)
        content_sha256 = _digest(raw)
        if data.get("content_sha256") != content_sha256 or edition_id != f"sed_{content_sha256}":
            raise RegistryIntegrityError("source edition content hash does not bind its immutable identity")
        binding = self._edition_binding(data)
        if binding["raw_content_sha256"] != content_sha256:
            raise RegistryIntegrityError("source edition raw-content hash does not bind rendition bytes")
        self._load_provenance(source_id, edition_id, data)
        return data

    def _load_edition_content(
        self, source_id: str, edition_id: str, edition: Mapping[str, Any]
    ) -> bytes:
        path = self._content_path(source_id, edition_id)
        try:
            raw = self._read_regular_file(path, self._edition_dir(source_id, edition_id))
        except FileNotFoundError as exc:
            raise RegistryIntegrityError("source edition omits immutable rendition bytes") from exc
        if not raw:
            raise RegistryIntegrityError("source edition rendition bytes are empty")
        expected = edition.get("content_sha256")
        if not isinstance(expected, str) or _digest(raw) != expected:
            raise RegistryIntegrityError("source edition rendition bytes do not match content hash")
        return raw

    def _load_provenance(
        self, source_id: str, edition_id: str, edition: Mapping[str, Any]
    ) -> dict[str, Any]:
        try:
            data = self._load_yaml_file(
                self._provenance_path(source_id, edition_id), self._edition_dir(source_id, edition_id)
            )
        except FileNotFoundError as exc:
            raise RegistryIntegrityError("source edition omits immutable provenance") from exc
        if not isinstance(data, dict):
            raise RegistryIntegrityError("source edition provenance must be a mapping")
        if (
            data.get("type") != "source_edition_provenance"
            or data.get("source_id") != source_id
            or data.get("source_edition_id") != edition_id
            or data.get("content_sha256") != edition.get("content_sha256")
        ):
            raise RegistryIntegrityError("source edition provenance does not bind the expected identity")
        binding = self._edition_binding(edition)
        if (
            data.get("edition_binding") != binding
            or data.get("edition_binding_sha256") != _canonical_digest(binding)
        ):
            raise RegistryIntegrityError("source edition immutable provenance metadata mismatch")
        return data

    def _verify_expected_source_snapshot(
        self,
        source_id: str,
        edition_id: str,
        expected_snapshot: Mapping[str, Any] | None,
    ) -> None:
        if expected_snapshot is None:
            return
        edition = self._load_edition(source_id, edition_id)
        provenance = self._load_provenance(source_id, edition_id, edition)
        actual = provenance.get("source_card_snapshot")
        if not isinstance(actual, Mapping) or _canonical_digest(dict(actual)) != _canonical_digest(dict(expected_snapshot)):
            raise RegistryIntegrityError("source-card provenance snapshot mismatch")

    def _load_passage_file(
        self, path: Path, edition_id: str, passage_id: str, edition_raw: bytes
    ) -> dict[str, Any]:
        try:
            data = self._load_yaml_file(path, path.parent)
        except FileNotFoundError as exc:
            raise RegistryIntegrityError("published passage record is missing") from exc
        if not isinstance(data, dict):
            raise RegistryIntegrityError("passage record must be a mapping")
        if data.get("passage_id") != passage_id or data.get("source_edition_id") != edition_id:
            raise RegistryIntegrityError("passage does not bind the expected edition and passage")
        raw_digest = data.get("raw_text_sha256")
        context = data.get("context")
        if not isinstance(raw_digest, str) or not isinstance(context, Mapping):
            raise RegistryIntegrityError("passage omits raw-text provenance")
        exact_quote = context.get("exact_quote")
        if not isinstance(exact_quote, str) or _digest(exact_quote) != raw_digest:
            raise RegistryIntegrityError("passage exact quote does not match its raw hash")
        selectors = data.get("selectors")
        if not isinstance(selectors, list):
            raise RegistryIntegrityError("passage omits deterministic edition selectors")
        by_kind: dict[str, list[Mapping[str, Any]]] = {}
        for selector in selectors:
            if not isinstance(selector, Mapping):
                raise RegistryIntegrityError("passage selector must be a mapping")
            kind = selector.get("kind")
            if not isinstance(kind, str):
                raise RegistryIntegrityError("passage selector omits kind")
            by_kind.setdefault(kind, []).append(selector)
        hashes = by_kind.get("hash", [])
        if len(hashes) != 1 or hashes[0].get("value") != raw_digest:
            raise RegistryIntegrityError("passage hash selector does not bind exact quote")
        structural = by_kind.get("structural", [])
        passage_index = context.get("passage_index")
        if (
            not isinstance(passage_index, int)
            or len(structural) != 1
            or structural[0].get("value") != f"passage:{passage_index}"
        ):
            raise RegistryIntegrityError("passage structural selector does not bind context")
        if "position" in by_kind:
            if len(by_kind["position"]) != 1:
                raise RegistryIntegrityError("passage position selector is ambiguous")
            start, end = self._selector_range(by_kind["position"][0].get("value"))
            quote_bytes = exact_quote.encode("utf-8")
            if edition_raw[start:end] != quote_bytes:
                raise RegistryIntegrityError("passage position selector does not occur in edition bytes")
            if edition_raw.find(quote_bytes) != start or edition_raw.find(quote_bytes, start + 1) != -1:
                raise RegistryIntegrityError("passage position selector is not unique in edition bytes")
        elif "byte_range" in by_kind:
            if len(by_kind["byte_range"]) != 1:
                raise RegistryIntegrityError("passage byte-range selector is ambiguous")
            start, end = self._selector_range(by_kind["byte_range"][0].get("value"))
            if (
                start != 0
                or end != len(edition_raw)
                or context.get("edition_raw_content_sha256") != _digest(edition_raw)
            ):
                raise RegistryIntegrityError("passage byte-range selector does not bind edition bytes")
        else:
            raise RegistryIntegrityError("passage omits a verified edition selector")
        return data

    @staticmethod
    def _selector_range(value: object) -> tuple[int, int]:
        if not isinstance(value, str):
            raise RegistryIntegrityError("passage selector range must be a string")
        match = re.fullmatch(r"(\d+):(\d+)", value)
        if match is None:
            raise RegistryIntegrityError("passage selector range is invalid")
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            raise RegistryIntegrityError("passage selector range is inverted")
        return start, end

    def _passage(
        self,
        edition_id: str,
        edition_raw: bytes,
        raw_text: str,
        index: int,
        *,
        allow_full_rendition: bool,
    ) -> dict[str, Any]:
        normalized = _normalise(raw_text)
        raw_digest, normalized_digest = _digest(raw_text), _digest(normalized)
        quote_bytes = raw_text.encode("utf-8")
        start = edition_raw.find(quote_bytes)
        if start < 0:
            if not allow_full_rendition:
                raise _PassageSelectionError("passage_not_in_edition")
            end = len(edition_raw)
            position = {"kind": "byte_range", "value": f"0:{end}", "confidence": 1.0}
            edition_content_digest: str | None = _digest(edition_raw)
        else:
            if edition_raw.find(quote_bytes, start + 1) != -1:
                raise _PassageSelectionError("ambiguous_selector")
            end = start + len(quote_bytes)
            position = {"kind": "position", "value": f"{start}:{end}", "confidence": 1.0}
            edition_content_digest = None
        selectors = [
            position,
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
            "context": {
                "exact_quote": raw_text,
                "passage_index": index,
                "edition_raw_content_sha256": edition_content_digest,
            },
        }


__all__ = [
    "AssertionRegistry",
    "PassageResolution",
    "RegistryImportResult",
    "RegistryIntegrityError",
]
