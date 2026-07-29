"""Workspace-scoped, rebuildable read model for source assertions.

The assertion ledger's YAML records remain authoritative.  This module keeps
only a small derived projection beneath ``.rf_cache`` so lexical discovery can
be deleted and rebuilt without changing the ledger.  It deliberately provides
no vector or graph retrieval capability.

Every public operation requires an :class:`AuthIdentity`; absence of identity,
workspace scope, or usable rights metadata is represented as a typed denial
whose payload contains no result-derived values.

F18 (RPC-6.G / N7) design note: P6 records lifecycle staleness for
``inference``/``canonical_claim_edge`` records as a durable, content-addressed
effect receipt (``assertion_impact.collect_stale_object_ids``) rather than
mutating the record's own ``status``/``state`` field on disk (that field can,
and often does, lag reality once P6 has touched a workspace). ``_build_records``
computes that effective-status set ONCE per rebuild and OVERRIDES the
projected ``status``/``state`` value in place -- to ``"stale"`` -- whenever
P6 has recorded a completed ``mark_stale`` effect for that inference/canonical
claim, rather than adding a new sibling field (e.g. ``effective_status``).
Both are defensible for this rebuildable, non-authoritative projection; this
module chose override specifically because a sibling-field addition would
have changed shape for every consumer keying off this projection's existing
``status``/``state`` (including a downstream API contract test's frozen
literal outside this module's scope), while override is a no-op for the
common non-stale case (the exact value the record's own, immutable ``status``/
``state`` already holds) and only changes the DISPLAYED value once a lane
consumer would need to treat the record as non-current regardless.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..api.auth.provider import AuthIdentity
from ..paths import FoundryPaths
from ..yamlio import load_yaml
from .assertion_materialization import _referenced_target_ids
from .provenance_envelope import ProvenanceEnvelopeStore, derive_origin_facets
from .research_run_discovery import ResearchRunDiscovery

logger = logging.getLogger(__name__)

_MAX_PAGE_SIZE = 100
_DEFAULT_PAGE_SIZE = 25


class AssertionCatalogError(ValueError):
    """A malformed request or durable assertion artifact."""


class AssertionCatalogDenied(AssertionCatalogError):
    """A fail-closed read denial that is safe to return to a caller."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class AssertionCatalogUnavailable(AssertionCatalogError):
    """The derived assertion projection cannot be read without rebuilding it first.

    Raised by the RF Knowledge MCP's non-rebuilding read path (KMCP-2.3:
    :meth:`AssertionCatalog._records_read_only` and its ``*_read_only``
    callers below) when a workspace's projection file is missing or
    invalid. Distinct from :class:`AssertionCatalogDenied` (a policy/rights
    denial evaluated over an actually-read projection) so a caller can tell
    "nothing built yet" apart from "read and denied" — both still resolve to
    the SAME no-existence-leak response shape at the transport boundary
    (KMCP-OQ-1: "indistinguishable in shape from hidden"), but the
    distinction lets the Knowledge service log/telemetry differently
    without ever leaking it to a caller. Never raised by :meth:`_records`,
    :meth:`search`, :meth:`packet`, or :meth:`lineage` — those existing,
    rebuild-on-miss methods are completely unchanged.
    """

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ProjectionReceipt:
    """Stable proof that a derived projection was rebuilt.

    ``catalog_generation_id`` (CARP contract-freeze §3.6, Seam 1) is a
    ``sha256`` content digest over the canonicalized ``records`` list, never
    a filesystem path or an mtime. It changes iff the record set actually
    changes, so repeated ``rebuild()`` calls against an unchanged corpus are
    idempotent and return the same generation id -- a monotonic counter was
    explicitly rejected because it would increment on every cold-start
    rebuild and every no-op rebuild triggered by :meth:`AssertionCatalog._records`,
    spuriously tripping the "catalog generation changed mid-plan" scenario.
    """

    workspace_id: str
    record_count: int
    projection_path: Path
    catalog_generation_id: str


def _workspace_key(workspace_id: str) -> str:
    return hashlib.sha256(workspace_id.encode("utf-8")).hexdigest()


def _canonical_generation_digest(records: list[dict[str, Any]]) -> str:
    """Sha256 over the canonicalized ``records`` list (CARP-2 Seam 1).

    ``sort_keys=True`` plus fixed separators make the digest stable across
    dict key-insertion order; the list's own order is already deterministic
    (``_build_records`` walks ``sorted(...glob("*.yaml"))``), so this is a
    pure function of record *content*, never of the filesystem path or mtime
    the projection happens to be written to.
    """
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _report_use_index(root: Path) -> dict[tuple[str, str, int], list[str]]:
    """Bucket every published ``report_assertion_use`` record by its cited ref.

    Records under ``report_assertion_uses/records/*.yaml`` are immutable,
    content-addressed, and self-authoritative once written (freeze doc §13.2
    -- there is no separate ledger-pointer-generation layer for this lane the
    way there is for inference/canonical-claim, RPC-5 findings N5), so a
    direct glob of the canonical record directory is the lane's own reader
    surface, not a "raw manifest" read (N5 draws that line at the
    per-record-kind ``.generation_manifest.yaml`` files, never at a lane's
    published record store itself). A single malformed record is skipped,
    never aborts the whole index (mirrors this module's existing
    per-record degrade posture for editions/passages/evaluations/observations).
    """

    index: dict[tuple[str, str, int], list[str]] = {}
    records_dir = root / "report_assertion_uses" / "records"
    if not records_dir.is_dir():
        return index
    for path in sorted(records_dir.glob("*.yaml")):
        record = _mapping(path)
        if not record or record.get("type") != "report_assertion_use":
            continue
        use_id = record.get("use_id")
        cited_ref = record.get("cited_ref")
        if not isinstance(use_id, str) or not isinstance(cited_ref, Mapping):
            continue
        ref_kind = cited_ref.get("ref_kind")
        key: tuple[str, str, int] | None = None
        if ref_kind == "source_assertion":
            assertion_id, assertion_version = cited_ref.get("assertion_id"), cited_ref.get("assertion_version")
            if isinstance(assertion_id, str) and isinstance(assertion_version, int):
                key = ("source_assertion", assertion_id, assertion_version)
        elif ref_kind == "inference":
            inference_id, inference_version = cited_ref.get("inference_id"), cited_ref.get("inference_version")
            if isinstance(inference_id, str) and isinstance(inference_version, int):
                key = ("inference", inference_id, inference_version)
        elif ref_kind == "canonical_claim":
            canonical_claim_id = cited_ref.get("canonical_claim_id")
            canonical_claim_version = cited_ref.get("canonical_claim_version")
            if isinstance(canonical_claim_id, str) and isinstance(canonical_claim_version, int):
                key = ("canonical_claim", canonical_claim_id, canonical_claim_version)
        if key is None:
            continue
        index.setdefault(key, []).append(use_id)
    for uses in index.values():
        uses.sort()
    return index


def _authoritative_inference_records(paths: FoundryPaths, workspace_id: str, root: Path) -> dict[tuple[str, int], dict[str, Any]]:
    """Load every inference_record reachable from the claim-ledger's CURRENT
    generation pointer (freeze doc §17.7a's reader rule; RPC-5 findings N5) --
    never a record merely promoted-but-not-yet-authoritative, and never a
    private per-record-kind manifest consulted in isolation. Storage layout
    (``inferences/<inference_id>.yaml``) is the frozen convention
    ``assertion_inference.py`` documents; a version mismatch or unreadable
    file degrades that one record out of the set rather than raising.
    """

    referenced = _referenced_target_ids(paths, workspace_id=workspace_id, record_kind="inference_record")
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for inference_id, version in referenced:
        record = _mapping(root / "inferences" / f"{inference_id}.yaml")
        if not record or record.get("type") != "inference_record":
            continue
        if record.get("inference_id") != inference_id or record.get("inference_version") != version:
            continue
        records[(inference_id, version)] = record
    return records


def _authoritative_canonical_claim_records(paths: FoundryPaths, workspace_id: str, root: Path) -> dict[tuple[str, int], dict[str, Any]]:
    """Load every canonical_claim reachable from the claim-ledger's CURRENT
    generation pointer -- the canonical-claim sibling of
    :func:`_authoritative_inference_records`. Storage layout
    (``canonical_claims/<canonical_claim_id>/<canonical_claim_version>.yaml``)
    is the frozen convention ``canonical_claim_materialization.py`` documents.
    """

    referenced = _referenced_target_ids(paths, workspace_id=workspace_id, record_kind="canonical_claim")
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for canonical_claim_id, version in referenced:
        record = _mapping(root / "canonical_claims" / canonical_claim_id / f"{version}.yaml")
        if not record or record.get("type") != "canonical_claim":
            continue
        if record.get("canonical_claim_id") != canonical_claim_id or record.get("canonical_claim_version") != version:
            continue
        records[(canonical_claim_id, version)] = record
    return records


def _search_only_activity_index(paths: FoundryPaths, workspace_id: str) -> dict[tuple[str, int], list[str]]:
    """Bucket search-only activity ids by the assertion versions their
    published receipt selected (``search_activity_receipt.selected_evidence_versions``).

    Uses :class:`~.research_run_discovery.ResearchRunDiscovery` -- the lane's
    own governed reader (RPC-5 findings N5) -- rather than reading
    ``provenance_ledger`` envelopes/receipts directly. No ``identity`` is
    passed: this runs server-side, inside a workspace-scoped rebuild that
    already owns the workspace boundary; ``activity_kind="search_only"``
    activities carry no ``planned_run_ref`` to gate on regardless (RPC-FR-2).
    """

    index: dict[tuple[str, int], list[str]] = {}
    discovery = ResearchRunDiscovery(workspace_id=workspace_id, paths=paths)
    listing = discovery.list_activities(activity_kind="search_only")
    for item in listing.get("items", []):
        envelope_id = item.get("envelope_id")
        if not isinstance(envelope_id, str):
            continue
        try:
            activity = discovery.fetch_activity(envelope_id)
        except Exception:  # noqa: BLE001 - one bad record must not break the index
            continue
        if activity.receipt is None:
            continue
        activity_id = activity.receipt.get("activity_id")
        if not isinstance(activity_id, str):
            continue
        selected = activity.receipt.get("selected_evidence_versions")
        if not isinstance(selected, list):
            continue
        for entry in selected:
            if not isinstance(entry, Mapping):
                continue
            assertion_id, assertion_version = entry.get("assertion_id"), entry.get("assertion_version")
            if isinstance(assertion_id, str) and isinstance(assertion_version, int):
                index.setdefault((assertion_id, assertion_version), []).append(activity_id)
    for activity_ids in index.values():
        activity_ids[:] = sorted(set(activity_ids))
    return index


def _run_origin_facet(paths: FoundryPaths, workspace_id: str, run_id: str, cache: dict[str, dict[str, Any] | None]) -> dict[str, Any] | None:
    """Resolve one run's origin-derived facet (freeze doc §4.1 rule 5), memoized.

    A run's ``planned_run`` activity envelope carries an optional ``origin_ref``
    (``research_run_envelope.schema.yaml``); when present, the referenced
    ``provenance_origin`` record is read via
    :meth:`~.provenance_envelope.ProvenanceEnvelopeStore.read_origin` -- the
    lane's own reader -- and reduced through the ONE shared derivation path,
    :func:`~.provenance_envelope.derive_origin_facets`, so a facet rebuild is
    always byte-identical to any other consumer's. A run with no envelope, no
    ``origin_ref``, or an unresolvable origin simply has no facet (``None``),
    never a fabricated placeholder (freeze doc §4.1 rule 6).
    """

    if run_id in cache:
        return cache[run_id]
    facet: dict[str, Any] | None = None
    try:
        discovery = ResearchRunDiscovery(workspace_id=workspace_id, paths=paths)
        listing = discovery.list_activities(activity_kind="planned_run")
        envelope_id = None
        for item in listing.get("items", []):
            planned_run_ref = item.get("planned_run_ref") or {}
            if isinstance(planned_run_ref, Mapping) and planned_run_ref.get("run_id") == run_id:
                envelope_id = item.get("envelope_id")
                break
        if isinstance(envelope_id, str):
            activity = discovery.fetch_activity(envelope_id)
            origin_ref = activity.envelope.get("origin_ref")
            if isinstance(origin_ref, Mapping):
                origin_id = origin_ref.get("origin_id")
                if isinstance(origin_id, str):
                    store = ProvenanceEnvelopeStore(workspace_id=workspace_id, paths=paths)
                    origin = store.read_origin(origin_id)
                    if origin is not None:
                        facet = derive_origin_facets(origin)
    except Exception:  # noqa: BLE001 - a facet is best-effort, never fatal to rebuild
        facet = None
    cache[run_id] = facet
    return facet


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
        generation_id = _canonical_generation_digest(records)
        path = self.projection_path(workspace_id)
        _atomic_json_dump(
            {
                "schema_version": 1,
                "workspace_key": _workspace_key(workspace_id),
                "catalog_generation_id": generation_id,
                "records": records,
            },
            path,
        )
        return ProjectionReceipt(
            workspace_id=workspace_id,
            record_count=len(records),
            projection_path=path,
            catalog_generation_id=generation_id,
        )

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
            "inference_lineage": packet["inference_lineage"],
            "canonical_claim_lineage": packet["canonical_claim_lineage"],
            "run_facets": packet["run_facets"],
            "search_activity_ids": packet["search_activity_ids"],
            "denial_reason": None,
        }

    # -- RF Knowledge MCP non-rebuilding read path (KMCP-2.3) ---------------
    # Additive only — search/packet/lineage above are completely unchanged
    # and keep their existing rebuild-on-miss behavior for every current
    # caller. The three methods below are new siblings that a Knowledge read
    # (P2/P3) must use instead: they NEVER call self.rebuild() as a side
    # effect of a missing/invalid projection.

    def search_read_only(
        self,
        *,
        identity: AuthIdentity | None,
        query: str | None = None,
        lifecycle_state: str | None = None,
        access_scope: str | None = None,
        limit: int = _DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Non-rebuilding sibling of :meth:`search` (KMCP-2.3, invariant 2).

        Identical policy-before-match ordering and denial shape as
        :meth:`search` (see that method's docstring) — the ONLY difference
        is that a missing or workspace-key-mismatched projection never
        triggers :meth:`rebuild` as a side effect; it instead returns the
        same bounded, no-existence-leak :meth:`denied_payload` shape with
        reason code ``"catalog_unavailable"`` (KMCP-OQ-1:
        "indistinguishable in shape from hidden"). :meth:`search` itself is
        completely unchanged for every existing caller.
        """

        if identity is None or not identity.workspace_id:
            return self.denied_payload("workspace_context_missing")
        if not 1 <= limit <= _MAX_PAGE_SIZE:
            return self.denied_payload("invalid_page_size")
        try:
            records = self._records_read_only(identity.workspace_id)
        except AssertionCatalogUnavailable:
            return self.denied_payload("catalog_unavailable")
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

    def packet_read_only(
        self, assertion_id: str, *, identity: AuthIdentity | None
    ) -> dict[str, Any] | None:
        """Non-rebuilding sibling of :meth:`packet` (KMCP-2.3, invariant 2).

        Same policy-before-match ordering, denial
        (:class:`AssertionCatalogDenied`), and existence-hiding contract as
        :meth:`packet` — the only difference is that a missing or invalid
        projection raises :class:`AssertionCatalogUnavailable` instead of
        silently calling :meth:`rebuild`. :meth:`packet` itself is
        completely unchanged for every existing caller.
        """

        if identity is None or not identity.workspace_id:
            raise AssertionCatalogDenied("workspace_context_missing")
        for record in self._records_read_only(identity.workspace_id):
            if record["assertion_id"] != assertion_id:
                continue
            if not record["rights_decision"]["allowed"]:
                raise AssertionCatalogDenied(str(record["rights_decision"]["reason_code"]))
            return {key: value for key, value in record.items() if key != "search_text"}
        return None

    def lineage_read_only(
        self, assertion_id: str, *, identity: AuthIdentity | None
    ) -> dict[str, Any] | None:
        """Non-rebuilding sibling of :meth:`lineage` (KMCP-2.3).

        See :meth:`packet_read_only` for the rebuild-avoidance contract this
        mirrors; :meth:`lineage` itself is unchanged.
        """

        packet = self.packet_read_only(assertion_id, identity=identity)
        if packet is None:
            return None
        return {
            "assertion_id": packet["assertion_id"],
            "assertion_version": packet["assertion_version"],
            "relationships": packet["relationships"],
            "run_uses": packet["run_uses"],
            "report_uses": packet["report_uses"],
            "inference_lineage": packet["inference_lineage"],
            "canonical_claim_lineage": packet["canonical_claim_lineage"],
            "run_facets": packet["run_facets"],
            "search_activity_ids": packet["search_activity_ids"],
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

    def _records_read_only(self, workspace_id: str) -> list[dict[str, Any]]:
        """Non-rebuilding sibling of :meth:`_records` (KMCP-2.3, invariant 2).

        Returns the SAME parsed record list :meth:`_records` would, but
        NEVER calls :meth:`rebuild` when the projection file is missing —
        it raises :class:`AssertionCatalogUnavailable` instead, so a
        Knowledge read can never trigger a ledger rebuild (a filesystem
        write) as a side effect of a lookup. :meth:`_records` is completely
        unchanged for every existing caller.
        """

        path = self.projection_path(workspace_id)
        if not path.exists():
            raise AssertionCatalogUnavailable("projection_missing")
        projection = _mapping(path)
        if not projection or projection.get("workspace_key") != _workspace_key(workspace_id):
            raise AssertionCatalogUnavailable("projection_invalid")
        records = projection.get("records")
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise AssertionCatalogUnavailable("projection_invalid")
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

        # RPC-5.1: activity/lineage projections, computed ONCE per rebuild
        # (never per-assertion) and read exclusively via each lane's own
        # reader/recovery API (findings N5) -- never a raw per-record-kind
        # manifest, and never the ledger-authority pointer consulted in
        # isolation from `_referenced_target_ids`.
        report_use_index = _report_use_index(root)
        inference_records = _authoritative_inference_records(self.paths, workspace_id, root)
        canonical_claim_records = _authoritative_canonical_claim_records(self.paths, workspace_id, root)
        search_only_index = _search_only_activity_index(self.paths, workspace_id)
        run_facet_cache: dict[str, dict[str, Any] | None] = {}

        # F18 (RPC-6.G / N7): P6 marks an inference/canonical-claim stale as a
        # durable effect receipt, never as an on-disk record mutation
        # (`status`/`state` here can be, and often is, stale). Computed ONCE
        # per rebuild (never per-record) via the impact lane's own
        # invariant-checked reader -- a raw effect file is never consulted
        # directly. Lazy import: assertion_impact.py imports this module's
        # `_referenced_target_ids` at module scope, so a module-level import
        # here would be circular.
        from .assertion_impact import (
            collect_stale_object_ids,
            effective_source_assertion_lifecycle_state,
        )

        stale_object_ids = collect_stale_object_ids(paths=self.paths, workspace_id=workspace_id)
        stale_inference_ids = stale_object_ids.get("inference", frozenset())
        stale_canonical_claim_ids = stale_object_ids.get("canonical_claim_edge", frozenset())

        inference_by_assertion: dict[tuple[str, int], list[dict[str, Any]]] = {}
        for (inference_id, inference_version), inference in sorted(inference_records.items()):
            refs = inference.get("source_assertion_refs")
            if not isinstance(refs, list):
                continue
            # F18: `status` is OVERRIDDEN to `"stale"` when P6 has recorded a
            # completed `mark_stale` effect for this inference, regardless of
            # what its immutable record still says -- see module docstring
            # for why override (not an additive sibling field) was chosen.
            effective_status = "stale" if inference_id in stale_inference_ids else inference.get("status")
            summary = {
                "inference_id": inference_id,
                "inference_version": inference_version,
                "status": effective_status,
                "report_uses": report_use_index.get(("inference", inference_id, inference_version), []),
            }
            for ref in refs:
                if not isinstance(ref, Mapping):
                    continue
                ref_assertion_id = ref.get("assertion_id")
                ref_assertion_version = ref.get("assertion_version")
                if isinstance(ref_assertion_id, str) and isinstance(ref_assertion_version, int):
                    inference_by_assertion.setdefault(
                        (ref_assertion_id, ref_assertion_version), []
                    ).append(summary)

        canonical_by_assertion: dict[tuple[str, int], dict[tuple[str, int], dict[str, Any]]] = {}
        for (canonical_claim_id, canonical_claim_version), canonical_claim in sorted(canonical_claim_records.items()):
            # F18: see the inference summary above -- `state` is overridden
            # the same way.
            effective_state = (
                "stale" if canonical_claim_id in stale_canonical_claim_ids else canonical_claim.get("state")
            )
            summary = {
                "canonical_claim_id": canonical_claim_id,
                "canonical_claim_version": canonical_claim_version,
                "state": effective_state,
                "report_uses": report_use_index.get(
                    ("canonical_claim", canonical_claim_id, canonical_claim_version), []
                ),
            }
            target_assertion_keys: set[tuple[str, int]] = set()
            source_refs = canonical_claim.get("source_assertion_refs")
            if isinstance(source_refs, list):
                for ref in source_refs:
                    if not isinstance(ref, Mapping):
                        continue
                    ref_assertion_id = ref.get("assertion_id")
                    ref_assertion_version = ref.get("assertion_version")
                    if isinstance(ref_assertion_id, str) and isinstance(ref_assertion_version, int):
                        target_assertion_keys.add((ref_assertion_id, ref_assertion_version))
            # Indirect lineage: a canonical claim citing an inference this
            # workspace's assertions fed. `inference_refs` is additive
            # supplementary support (freeze doc §16.1) -- it never replaces a
            # direct `source_assertion_refs` citation, only widens lineage.
            inference_refs = canonical_claim.get("inference_refs")
            if isinstance(inference_refs, list):
                for ref in inference_refs:
                    if not isinstance(ref, Mapping):
                        continue
                    inference_key = (ref.get("inference_id"), ref.get("inference_version"))
                    base_inference = inference_records.get(inference_key)  # type: ignore[arg-type]
                    if not base_inference:
                        continue
                    base_refs = base_inference.get("source_assertion_refs")
                    if not isinstance(base_refs, list):
                        continue
                    for base_ref in base_refs:
                        if not isinstance(base_ref, Mapping):
                            continue
                        base_assertion_id = base_ref.get("assertion_id")
                        base_assertion_version = base_ref.get("assertion_version")
                        if isinstance(base_assertion_id, str) and isinstance(base_assertion_version, int):
                            target_assertion_keys.add((base_assertion_id, base_assertion_version))
            for key in target_assertion_keys:
                canonical_by_assertion.setdefault(key, {})[
                    (canonical_claim_id, canonical_claim_version)
                ] = summary

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
            sorted_run_uses = sorted(run_uses)
            assertion_version = assertion.get("assertion_version")
            if not isinstance(assertion_version, int):
                continue
            lineage_key = (assertion_id, assertion_version)

            # F19 (RPC-6.G validator, Karen K-1, HIGH): the raw
            # `assertion.lifecycle_state` never flips to "blocked" on disk --
            # P6's authoritative block boundary lives in the separate
            # `lifecycle_policy/<id>.yaml` artifact (see
            # `AssertionImpactReconciler.reconcile`). Override IN PLACE, the
            # SAME choice F18 already made for inference/canonical-claim
            # staleness above -- never an additive sibling field.
            effective_policy_state = effective_source_assertion_lifecycle_state(
                root=root, assertion_id=assertion_id
            )
            effective_lifecycle_state: Any
            if effective_policy_state == "blocked":
                effective_lifecycle_state = "blocked"
            elif effective_policy_state == "policy_invalid":
                # K-2 (Karen Wave-3 gate, MEDIUM): a present-but-invalid
                # policy artifact for THIS assertion is READ-path corruption
                # -- degrade to the assertion's own recorded state (never
                # crash a whole catalog rebuild, V5-1) but log it so the
                # corruption is observable, unlike a silent skip.
                logger.warning(
                    "assertion_catalog: lifecycle_policy for %s is present but invalid; "
                    "degrading to the assertion's own recorded lifecycle_state",
                    assertion_id,
                )
                effective_lifecycle_state = assertion.get("lifecycle_state")
            else:
                effective_lifecycle_state = assertion.get("lifecycle_state")

            packet = {
                "packet_version": "1.0",
                "assertion_id": assertion_id,
                "assertion_version": assertion_version,
                "lifecycle_state": effective_lifecycle_state,
                "assertion": assertion,
                "passage": passage,
                "source_edition": edition,
                "qualifiers": assertion.get("qualifiers", {}),
                # Do not normalize a genuinely absent additive field into an
                # empty map: P6 consumers distinguish legacy absence from an
                # authoritatively recorded empty qualifier-extension map.
                "qualifier_extensions": assertion.get("qualifier_extensions"),
                "evaluations": matching_evaluations,
                "freshness": {"lifecycle_state": effective_lifecycle_state},
                "access_scope": edition.get("access_scope"),
                "rights_decision": rights_decision,
                "relationships": relationships,
                "run_uses": sorted_run_uses,
                # RPC-5.1: F4's frozen `report_uses: list[str]` slot, now
                # filled with this assertion's DIRECT `rau_` citations.
                "report_uses": report_use_index.get(("source_assertion", assertion_id, assertion_version), []),
                "inference_lineage": sorted(
                    inference_by_assertion.get(lineage_key, []),
                    key=lambda item: (item["inference_id"], item["inference_version"]),
                ),
                "canonical_claim_lineage": sorted(
                    canonical_by_assertion.get(lineage_key, {}).values(),
                    key=lambda item: (item["canonical_claim_id"], item["canonical_claim_version"]),
                ),
                "run_facets": {
                    run_id: _run_origin_facet(self.paths, workspace_id, run_id, run_facet_cache)
                    for run_id in sorted_run_uses
                },
                "search_activity_ids": search_only_index.get(lineage_key, []),
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
    "AssertionCatalogUnavailable",
    "ProjectionReceipt",
]
