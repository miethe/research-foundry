"""Workspace-scoped, rebuildable read model for source assertions.

The assertion ledger's YAML records remain authoritative.  This module keeps
only a small derived projection beneath ``.rf_cache`` so lexical discovery can
be deleted and rebuilt without changing the ledger.  It deliberately provides
no vector or graph retrieval capability.

Every public operation requires an :class:`AuthIdentity`; absence of identity,
workspace scope, or usable rights metadata is represented as a typed denial
whose payload contains no result-derived values.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..api.auth.provider import AuthIdentity
from ..paths import FoundryPaths
from ..yamlio import load_yaml

_MAX_PAGE_SIZE = 100
_DEFAULT_PAGE_SIZE = 25


class AssertionCatalogError(ValueError):
    """A malformed request or durable assertion artifact."""


class AssertionCatalogDenied(AssertionCatalogError):
    """A fail-closed read denial that is safe to return to a caller."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ProjectionReceipt:
    """Stable proof that a derived projection was rebuilt."""

    workspace_id: str
    record_count: int
    projection_path: Path


def _workspace_key(workspace_id: str) -> str:
    return hashlib.sha256(workspace_id.encode("utf-8")).hexdigest()


def _mapping(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.is_symlink():
        return None
    value = load_yaml(path)
    return value if isinstance(value, dict) else None


def _atomic_json_dump(value: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _cursor_encode(assertion_id: str) -> str:
    return base64.urlsafe_b64encode(assertion_id.encode("utf-8")).decode("ascii").rstrip("=")


def _cursor_decode(cursor: str) -> str:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise AssertionCatalogError("invalid_cursor") from exc
    if not value.startswith("ast_"):
        raise AssertionCatalogError("invalid_cursor")
    return value


class AssertionCatalog:
    """Derived lexical projection and governed evidence-packet assembly."""

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self.paths = paths or FoundryPaths.discover()

    def projection_path(self, workspace_id: str) -> Path:
        return self.paths.root / ".rf_cache" / "assertion_catalog" / f"{_workspace_key(workspace_id)}.json"

    def rebuild(self, workspace_id: str) -> ProjectionReceipt:
        """Rebuild one workspace's non-authoritative assertion projection."""

        if not workspace_id.strip():
            raise AssertionCatalogError("workspace_context_missing")
        records = self._build_records(workspace_id)
        path = self.projection_path(workspace_id)
        _atomic_json_dump({"schema_version": 1, "workspace_key": _workspace_key(workspace_id), "records": records}, path)
        return ProjectionReceipt(workspace_id=workspace_id, record_count=len(records), projection_path=path)

    def search(
        self,
        *,
        identity: AuthIdentity | None,
        query: str | None = None,
        lifecycle_state: str | None = None,
        access_scope: str | None = None,
        limit: int = _DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Return only authorized rows and facets from one workspace.

        Policy filtering precedes lexical matching, counts, facets, and cursor
        construction.  A denial never includes candidate-derived signals.
        """

        if identity is None or not identity.workspace_id:
            return self.denied_payload("workspace_context_missing")
        if not 1 <= limit <= _MAX_PAGE_SIZE:
            return self.denied_payload("invalid_page_size")
        try:
            records = self._records(identity.workspace_id)
        except AssertionCatalogDenied as exc:
            return self.denied_payload(exc.reason_code)
        except AssertionCatalogError as exc:
            return self.denied_payload(str(exc))

        # Rights metadata is policy context, not a presentation hint.  A
        # partially unknown corpus must not expose counts/facets for its known
        # subset, because that would turn missing policy into a derived signal.
        for record in records:
            decision = record["rights_decision"]
            if not decision["allowed"]:
                return self.denied_payload(str(decision["reason_code"]))
        # A projection can lag its durable cleanup.  Current discovery must
        # nevertheless follow the authoritative lifecycle immediately: only
        # eligible assertions may contribute rows, counts, facets, or cursors.
        # Historical packet/audit reads remain handled separately below.
        authorized = [record for record in records if record["lifecycle_state"] == "eligible"]
        normalized_query = (query or "").casefold().strip()
        filtered = [
            record
            for record in authorized
            if (not lifecycle_state or record["lifecycle_state"] == lifecycle_state)
            and (not access_scope or record["access_scope"] == access_scope)
            and (not normalized_query or normalized_query in record["search_text"].casefold())
        ]
        filtered.sort(key=lambda record: record["assertion_id"])
        if cursor is not None:
            try:
                after = _cursor_decode(cursor)
            except AssertionCatalogError as exc:
                return self.denied_payload(str(exc))
            filtered = [record for record in filtered if record["assertion_id"] > after]

        page = filtered[:limit]
        next_cursor = _cursor_encode(page[-1]["assertion_id"]) if len(filtered) > limit else None
        return {
            "items": [self._summary(record) for record in page],
            "next_cursor": next_cursor,
            "facets": {
                "lifecycle_states": sorted({record["lifecycle_state"] for record in authorized}),
                "access_scopes": sorted({record["access_scope"] for record in authorized}),
            },
            "denial_reason": None,
        }

    def packet(self, assertion_id: str, *, identity: AuthIdentity | None) -> dict[str, Any] | None:
        """Return one complete evidence packet or ``None`` without existence hints."""

        if identity is None or not identity.workspace_id:
            raise AssertionCatalogDenied("workspace_context_missing")
        for record in self._records(identity.workspace_id):
            if record["assertion_id"] != assertion_id:
                continue
            if not record["rights_decision"]["allowed"]:
                raise AssertionCatalogDenied(str(record["rights_decision"]["reason_code"]))
            return {key: value for key, value in record.items() if key != "search_text"}
        return None

    def lineage(self, assertion_id: str, *, identity: AuthIdentity | None) -> dict[str, Any] | None:
        packet = self.packet(assertion_id, identity=identity)
        if packet is None:
            return None
        return {
            "assertion_id": packet["assertion_id"],
            "assertion_version": packet["assertion_version"],
            "relationships": packet["relationships"],
            "run_uses": packet["run_uses"],
            "report_uses": packet["report_uses"],
            "denial_reason": None,
        }

    @staticmethod
    def denied_payload(reason_code: str) -> dict[str, Any]:
        return {
            "items": [],
            "next_cursor": None,
            "facets": {"lifecycle_states": [], "access_scopes": []},
            "denial_reason": reason_code,
        }

    @staticmethod
    def _summary(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "assertion_id": record["assertion_id"],
            "assertion_version": record["assertion_version"],
            "lifecycle_state": record["lifecycle_state"],
            "access_scope": record["access_scope"],
            "rights_decision": record["rights_decision"],
        }

    def _records(self, workspace_id: str) -> list[dict[str, Any]]:
        path = self.projection_path(workspace_id)
        if not path.exists():
            self.rebuild(workspace_id)
        projection = _mapping(path)
        if not projection or projection.get("workspace_key") != _workspace_key(workspace_id):
            raise AssertionCatalogError("projection_invalid")
        records = projection.get("records")
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise AssertionCatalogError("projection_invalid")
        return [dict(record) for record in records]

    def _build_records(self, workspace_id: str) -> list[dict[str, Any]]:
        root = self.paths.root / "assertion_ledger" / "workspaces" / _workspace_key(workspace_id)
        if not root.exists():
            return []
        if root.is_symlink():
            raise AssertionCatalogError("ledger_integrity_rejected")
        editions = self._editions(root)
        passages = self._passages(root)
        evaluations = self._evaluations(root)
        observations = self._observations(root)
        records: list[dict[str, Any]] = []
        for path in sorted((root / "assertions").glob("*.yaml")):
            assertion = _mapping(path)
            if not assertion or assertion.get("type") != "source_assertion":
                continue
            assertion_id = assertion.get("assertion_id")
            edition_id = assertion.get("source_edition_id")
            passage_id = assertion.get("passage_id")
            if not all(isinstance(value, str) and value for value in (assertion_id, edition_id, passage_id)):
                continue
            assert isinstance(assertion_id, str)
            assert isinstance(edition_id, str)
            assert isinstance(passage_id, str)
            edition = editions.get(edition_id)
            passage = passages.get(passage_id)
            if not edition or not passage or passage.get("source_edition_id") != edition_id:
                continue
            allowed_use = edition.get("metadata_extensions", {}).get("allowed_use") if isinstance(edition.get("metadata_extensions"), dict) else None
            rights_decision = self._rights_decision(edition, allowed_use)
            matching_evaluations = [
                evaluation for evaluation in evaluations
                if evaluation.get("assertion_id") == assertion_id
                and evaluation.get("assertion_version") == assertion.get("assertion_version")
            ]
            matching_observations = [
                observation for observation in observations
                if observation.get("assertion_id") == assertion_id
                and observation.get("assertion_version") == assertion.get("assertion_version")
            ]
            relationships = [
                {
                    "kind": "predecessor",
                    "assertion_id": assertion.get("predecessor_assertion_id"),
                    "assertion_version": assertion.get("predecessor_assertion_version"),
                }
            ] if assertion.get("predecessor_assertion_id") else []
            run_uses: set[str] = set()
            for observation in matching_observations:
                run_id = observation.get("run_id")
                if isinstance(run_id, str):
                    run_uses.add(run_id)
            packet = {
                "packet_version": "1.0",
                "assertion_id": assertion_id,
                "assertion_version": assertion.get("assertion_version"),
                "lifecycle_state": assertion.get("lifecycle_state"),
                "assertion": assertion,
                "passage": passage,
                "source_edition": edition,
                "qualifiers": assertion.get("qualifiers", {}),
                "qualifier_extensions": assertion.get("qualifier_extensions", {}),
                "evaluations": matching_evaluations,
                "freshness": {"lifecycle_state": assertion.get("lifecycle_state")},
                "access_scope": edition.get("access_scope"),
                "rights_decision": rights_decision,
                "relationships": relationships,
                "run_uses": sorted(run_uses),
                "report_uses": [],
            }
            packet["search_text"] = " ".join(
                value for value in (assertion.get("assertion_text"), passage.get("normalized_text")) if isinstance(value, str)
            )
            records.append(packet)
        return records

    @staticmethod
    def _rights_decision(edition: Mapping[str, Any], allowed_use: object) -> dict[str, Any]:
        if not isinstance(allowed_use, Mapping):
            return {"allowed": False, "reason_code": "rights_context_missing"}
        if edition.get("access_scope") not in {"public", "personal", "work_sensitive", "client_sensitive", "private"}:
            return {"allowed": False, "reason_code": "access_scope_unknown"}
        if allowed_use.get("allowed_for_work_output") is not True:
            return {"allowed": False, "reason_code": "rights_denied"}
        return {"allowed": True, "reason_code": "eligible"}

    @staticmethod
    def _editions(root: Path) -> dict[str, dict[str, Any]]:
        values: dict[str, dict[str, Any]] = {}
        for path in root.glob("sources/*/editions/*.yaml"):
            item = _mapping(path)
            if item and isinstance(item.get("source_edition_id"), str):
                values[item["source_edition_id"]] = item
        return values

    @staticmethod
    def _passages(root: Path) -> dict[str, dict[str, Any]]:
        values: dict[str, dict[str, Any]] = {}
        for path in root.glob("sources/*/editions/*/generations/*/passages/*.yaml"):
            item = _mapping(path)
            if item and isinstance(item.get("passage_id"), str):
                values[item["passage_id"]] = item
        return values

    @staticmethod
    def _evaluations(root: Path) -> Iterable[dict[str, Any]]:
        return [item for path in root.glob("evaluations/*.yaml") if (item := _mapping(path)) is not None]

    @staticmethod
    def _observations(root: Path) -> Iterable[dict[str, Any]]:
        return [item for path in root.glob("observations/*.yaml") if (item := _mapping(path)) is not None]


__all__ = [
    "AssertionCatalog",
    "AssertionCatalogDenied",
    "AssertionCatalogError",
    "ProjectionReceipt",
]
