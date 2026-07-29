"""Canonical origin / run-envelope / activity-receipt writers (RPC-2.1, RPC-2.2).

Owns ALL writes for the three record families
``schemas/provenance_origin.schema.yaml``, ``schemas/research_run_envelope.schema.yaml``,
and ``schemas/search_activity_receipt.schema.yaml`` in ONE module — design note
N1, ``docs/dev/architecture/research-provenance-contract-freeze.md`` §12/§17.9.
JSON Schema describes the *shape* of each record; this module binds the
content-addressed identity fields (``origin_id``/``envelope_id``/``activity_id``)
to their canonical payload and enforces the cross-record protocol the schema
alone cannot express — the same division of labor
``assertion_identity.py`` already established for ``source_assertion``.

Storage layout (a P2 design decision the contract records the *paths* for but
leaves the workspace-scoping convention to this module — mirrors
``assertion_registry.py``'s own ``assertion_ledger/workspaces/<key>/`` split so
a workspace's provenance store is isolated the same way its assertion ledger
is)::

    <foundry-root>/provenance_ledger/workspaces/<sha256(workspace_id)>/
        origins/<origin_id>.yaml
        envelopes/<envelope_id>/v1.yaml
        envelopes/<envelope_id>/v2.yaml                  (once published)
        envelopes/<envelope_id>/receipt.yaml              (once published)
        envelopes/<envelope_id>/.generation_manifest.yaml (append-only, RPC-7.17/7.18)

``origin_id`` is fully content-addressed over all ten material fields
including ``workspace_id`` (freeze doc §4.1 rule 7) so the workspace-keyed
directory is a belt-and-suspenders isolation boundary, not the sole one: a
cross-workspace read attempt simply never resolves a real file (§10 threat
boundary 2 — fail closed, never silently followed).

Guards reused, none invented (freeze doc §10 threat boundary 4): every write
entry point resolves through :func:`research_foundry.services.assertion_workspace.resolve_or_deny`
before anything is minted or persisted; a pre-resolution denial is EPHEMERAL
(freeze doc §5.2 fixture c-1) — no ``envelope_id``/``origin_id`` is minted and
nothing reaches disk.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..ids import now_iso
from ..paths import FoundryPaths
from ..schemas import SchemaRegistry
from ..yamlio import dumps_yaml, loads_yaml
from .assertion_workspace import resolve_or_deny

CANONICAL_ALGORITHM = "sha256-canonical-json-v1"

#: Freeze doc §4.1 rule 7/7a — the FULL, ten-field material payload for
#: ``provenance_origin.identity``. Order matches the schema's `const` list
#: exactly (order is part of the frozen contract, not incidental).
ORIGIN_MATERIAL_FIELDS: tuple[str, ...] = (
    "origin_version",
    "workspace_id",
    "method",
    "producer",
    "source_kind",
    "locator",
    "content_digest",
    "external_receipt_ref",
    "parent_origin_refs",
    "created_at",
)

#: Freeze doc §5.1a — ``research_run_envelope.identity.material_fields``.
#: Deliberately EXCLUDES ``activity_id``/``receipt_commitment``/``envelope_version``
#: so ``envelope_id`` is version-invariant across the one permitted v1->v2
#: promotion (§5.1b).
ENVELOPE_MATERIAL_FIELDS: tuple[str, ...] = (
    "workspace_id",
    "activity_kind",
    "request_id",
    "planned_run_ref",
    "parent_run_ref",
    "origin_ref",
    "aos_refs",
    "created_at",
)

#: Freeze doc §5.1a — ``search_activity_receipt.identity.material_fields``,
#: binding the FULL outcome payload (not just request-facing fields).
RECEIPT_MATERIAL_FIELDS: tuple[str, ...] = (
    "workspace_id",
    "activity_kind",
    "request_id",
    "query",
    "purpose",
    "scope",
    "candidate_set_digest",
    "selected_evidence_versions",
    "selection_receipt",
    "envelope_ref",
    "created_at",
)

#: Freeze doc §5.1b — ``version_digest`` covers every envelope field at the
#: CURRENT version, including the two fields ``identity.fingerprint``
#: deliberately excludes.
ENVELOPE_VERSION_DIGEST_FIELDS: tuple[str, ...] = (
    "envelope_id",
    "envelope_version",
    "workspace_id",
    "activity_kind",
    "request_id",
    "activity_id",
    "planned_run_ref",
    "parent_run_ref",
    "origin_ref",
    "aos_refs",
    "created_at",
    "receipt_commitment",
)

#: Freeze doc §5.1/§10 — the ONE public, uninformative denial reason. Never a
#: menu of failure shapes.
REASON_DENIED = "not_authorized_or_not_found"

#: SOL-31: the ONE lookup-id shape every ``read_origin`` call (and every
#: parent/envelope reference check that routes through it) validates BEFORE
#: building a path or trusting a loaded record's own claimed identity.
_ORIGIN_ID_RE = re.compile(r"^pvo_[a-f0-9]{64}$")


class ProvenanceEnvelopeError(ValueError):
    """Base error for the provenance/envelope writer and its integrity checks."""


class ProvenanceEnvelopeDenied(ProvenanceEnvelopeError):
    """Fail-closed denial. Carries exactly one uninformative reason code —
    never a candidate/content-derived value (freeze doc §10 threat boundary 1).
    """

    def __init__(self, reason_code: str = REASON_DENIED) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class ProvenanceIntegrityError(ProvenanceEnvelopeError):
    """A candidate or stored record fails content-binding, schema validation,
    or the cross-record protocol (freeze doc §5.3/§17.7a).
    """


class ProvenancePromotionInterrupted(RuntimeError):
    """Raised ONLY by the ``_interrupt_after_staging``/``_interrupt_before_manifest``
    test seams on :meth:`ProvenanceEnvelopeStore.create_receipt_and_promote` --
    simulates a crash mid-promotion so the recovery sweep
    (:meth:`ProvenanceEnvelopeStore.recover_orphaned_promotions`) has a
    deterministic half-pair to converge on. Never raised by normal operation.
    """


@dataclass(frozen=True)
class ActivityDenial:
    """Ephemeral, pre-workspace-resolution denial (freeze doc §5.2 fixture c-1).

    Never written to disk; carries no ``envelope_id``/``activity_id`` because
    none was ever minted.
    """

    denied: bool
    reason: str


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _fingerprint(payload: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _material_payload(record: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    """``.get(field)`` semantics per freeze doc §4.1 rule 7: an omitted key and
    an explicit ``null`` canonicalize identically.
    """

    return {field_name: record.get(field_name) for field_name in fields}


def _workspace_key(workspace_id: str) -> str:
    return sha256(workspace_id.encode("utf-8")).hexdigest()


def _atomic_write(payload: Mapping[str, Any], path: Path) -> None:
    """Atomically replace one YAML artifact (tempfile -> fsync -> os.replace),
    the same primitive ``assertion_registry.py::_atomic_dump`` already ships.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps_yaml(dict(payload)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = loads_yaml(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


# --- verification (service-layer checks JSON Schema alone cannot express) ----


def verify_origin_integrity(record: Mapping[str, Any]) -> list[str]:
    """Recompute ``origin_id``'s content-binding and report any mismatch
    (freeze doc §4.1 rule 7, §4.2 fixture d/d-1). Empty list == valid.
    """

    errors: list[str] = []
    identity = record.get("identity")
    if not isinstance(identity, Mapping):
        return ["identity: missing or not an object"]
    if identity.get("algorithm") != CANONICAL_ALGORITHM:
        errors.append("identity/algorithm: must be sha256-canonical-json-v1")
    if identity.get("material_fields") != list(ORIGIN_MATERIAL_FIELDS):
        errors.append("identity/material_fields: must match the frozen v1 field list")
    fingerprint = _fingerprint(_material_payload(record, ORIGIN_MATERIAL_FIELDS))
    if identity.get("fingerprint") != fingerprint:
        errors.append(
            "identity/fingerprint: recomputed fingerprint does not match the stored value "
            "(tamper-evident mismatch)"
        )
    if record.get("origin_id") != f"pvo_{fingerprint}":
        errors.append("origin_id: must equal 'pvo_' plus the recomputed fingerprint")
    return errors


def verify_envelope_identity(record: Mapping[str, Any]) -> list[str]:
    """Recompute ``envelope_id``'s content-binding (T2-1/T2-2, freeze doc
    §5.1a) and report any mismatch. Empty list == valid.

    ``ENVELOPE_MATERIAL_FIELDS`` is version-invariant by construction (it
    excludes ``activity_id``/``receipt_commitment``/``envelope_version``), so
    this same check applies unmodified to a v1 OR a v2 record -- a tampered
    field anywhere in the shared material payload changes the recomputed
    fingerprint and is caught here before any pair/manifest check runs.

    SOL-32 (hardening): this now ALSO validates the stored ``identity`` block
    itself -- ``algorithm`` and ``material_fields`` -- the same shape
    :func:`verify_origin_integrity` already requires for ``provenance_origin``.
    Previously this function recomputed the fingerprint and compared it only
    against ``envelope_id``, never checking whether the stored
    ``identity.algorithm``/``identity.material_fields``/``identity.fingerprint``
    themselves were honest or even present -- a record could carry a forged
    or missing identity block yet still pass as long as its bare
    ``envelope_id`` happened to match.
    """

    errors: list[str] = []
    identity = record.get("identity")
    if not isinstance(identity, Mapping):
        return ["identity: missing or not an object"]
    if identity.get("algorithm") != CANONICAL_ALGORITHM:
        errors.append("identity/algorithm: must be sha256-canonical-json-v1")
    if identity.get("material_fields") != list(ENVELOPE_MATERIAL_FIELDS):
        errors.append("identity/material_fields: must match the frozen field list")
    fingerprint = _fingerprint(_material_payload(record, ENVELOPE_MATERIAL_FIELDS))
    if identity.get("fingerprint") != fingerprint:
        errors.append(
            "identity/fingerprint: recomputed fingerprint does not match the stored value "
            "(tamper-evident mismatch)"
        )
    if record.get("envelope_id") != f"rre_{fingerprint}":
        errors.append(
            "envelope_id: recomputed fingerprint does not match the stored value "
            "(tamper-evident mismatch)"
        )
    return errors


def verify_receipt_identity(record: Mapping[str, Any]) -> list[str]:
    """Recompute ``activity_id``'s content-binding over the FULL outcome
    payload (T2-2, freeze doc §5.1a) and report any mismatch. Empty list ==
    valid. A receipt whose ``query``/``scope``/``selection_receipt``/etc. was
    altered without recomputing ``identity.fingerprint`` fails here -- never
    silently trusted on the strength of its own stored bytes.
    """

    errors: list[str] = []
    identity = record.get("identity")
    if not isinstance(identity, Mapping):
        return ["identity: missing or not an object"]
    fingerprint = _fingerprint(_material_payload(record, RECEIPT_MATERIAL_FIELDS))
    if identity.get("fingerprint") != fingerprint:
        errors.append(
            "identity/fingerprint: recomputed fingerprint does not match the stored value "
            "(tamper-evident mismatch)"
        )
    if record.get("activity_id") != f"sar_{fingerprint}":
        errors.append("activity_id: must equal 'sar_' plus the recomputed fingerprint")
    return errors


def verify_pair_integrity(
    envelope: Mapping[str, Any], receipt: Mapping[str, Any] | None
) -> list[str]:
    """Freeze doc §5.3's six cross-record equality checks.

    ``receipt is None`` is NOT an integrity failure for a v1-ONLY,
    receipt-pending envelope — §5.3 items 4/6 apply only once a receipt/v2
    exist. SOL-32 (CRITICAL): the inverse is now enforced too -- a
    ``envelope_version: 2`` record REQUIRES a present, identity-verified
    receipt; ``receipt is None`` alongside a v2 envelope is now itself a
    reported integrity error, never silently accepted as though the pair
    were merely not-yet-promoted (that state cannot exist once
    ``envelope_version`` has actually reached 2 -- v2 and the receipt are
    published atomically together, freeze doc §5.1a step 3).
    """

    errors: list[str] = []
    if receipt is None:
        if envelope.get("envelope_version") == 2:
            errors.append(
                "receipt: envelope_version 2 requires a present, identity-verified receipt "
                "(a v2 without its receipt violates the frozen v1->receipt->v2 invariant)"
            )
        return errors
    if envelope.get("workspace_id") != receipt.get("workspace_id"):
        errors.append("workspace_id mismatch between envelope and receipt")
    if envelope.get("activity_kind") != receipt.get("activity_kind"):
        errors.append("activity_kind mismatch between envelope and receipt")
    if envelope.get("request_id") != receipt.get("request_id"):
        errors.append("request_id mismatch between envelope and receipt")
    envelope_ref = receipt.get("envelope_ref")
    if not isinstance(envelope_ref, Mapping) or (
        envelope_ref.get("envelope_id") != envelope.get("envelope_id")
        or envelope_ref.get("envelope_version") != 1
    ):
        errors.append(
            "receipt.envelope_ref must equal {envelope_id, envelope_version: 1} (fixed literal)"
        )
    if envelope.get("envelope_version") == 2:
        if envelope.get("activity_id") != receipt.get("activity_id"):
            errors.append("activity_id mismatch between envelope v2 and receipt")
        receipt_identity = receipt.get("identity")
        receipt_fingerprint = (
            receipt_identity.get("fingerprint") if isinstance(receipt_identity, Mapping) else None
        )
        if envelope.get("receipt_commitment") != receipt_fingerprint:
            errors.append("envelope.receipt_commitment does not equal receipt.identity.fingerprint")
    return errors


def derive_origin_facets(origin: Mapping[str, Any]) -> dict[str, Any]:
    """Pure, SINGLE derivation path for origin-derived facets (freeze doc §4.1
    rule 5). Every consumer (a catalog column, a search-index entry, an API
    convenience field) MUST call this rather than re-derive independently, so
    deleting all derived facets for a workspace and rebuilding them from the
    canonical records on disk MUST produce byte-identical values (AC RPC-1
    resilience clause).
    """

    method = origin.get("method") or {}
    producer = origin.get("producer") or {}
    return {
        "origin_id": origin.get("origin_id"),
        "origin_source_kind": origin.get("source_kind"),
        "origin_locator": origin.get("locator"),
        "origin_producer_tool": producer.get("tool"),
        "origin_method_kind": method.get("kind"),
    }


def denied_selection_receipt() -> dict[str, Any]:
    """The ONE canonical ``outcome: denied`` shape (freeze doc §5.2 fixture c,
    §5.1 rule 5) — zero candidate-derived fields, one uninformative reason.
    """

    return {
        "outcome": "denied",
        "source": None,
        "catalog_generation_id": None,
        "decided_at": None,
        "denial_reason": REASON_DENIED,
        "degraded_reason": None,
        "fallback_reason": None,
    }


# --- outcome-arm builders (RPC-2.3, freeze doc §5.1 rule 4 / §5.2) -----------
#
# One builder per outcome, mirroring ``denied_selection_receipt`` above, so a
# caller never has to hand-construct the exact null/non-null shape from the
# freeze doc's table themselves. Every builder is a pure dict factory — the
# authoritative enforcement remains schema validation inside
# ``ProvenanceEnvelopeStore.create_receipt_and_promote`` (the schema's own
# ``allOf`` partition, freeze doc §5.1 rule 4); these builders exist to make
# the *correct* shape the easy one to produce, not to duplicate that
# enforcement. ``selected``/``fallback`` additionally require the caller to
# pass a non-empty ``selected_evidence_versions`` to
# ``create_receipt_and_promote`` — that cardinality rule lives on the
# top-level receipt payload, not the ``selection_receipt`` sub-object these
# builders return, so it is not (and cannot be) checked here.


def selected_selection_receipt(
    *, source: str, decided_at: str, catalog_generation_id: str | None = None
) -> dict[str, Any]:
    """The ``outcome: selected`` shape: at least one candidate was selected."""

    return {
        "outcome": "selected",
        "source": source,
        "catalog_generation_id": catalog_generation_id,
        "decided_at": decided_at,
        "denial_reason": None,
        "degraded_reason": None,
        "fallback_reason": None,
    }


def empty_selection_receipt(
    *, source: str, decided_at: str, catalog_generation_id: str | None = None
) -> dict[str, Any]:
    """The ``outcome: empty`` shape (SOL-7): an AUTHORIZED activity whose
    evaluated candidate set contained zero matches — ``source``/``decided_at``
    stay non-null (a real candidate set WAS evaluated), never conflated with
    ``denied``'s all-null shape.
    """

    return {
        "outcome": "empty",
        "source": source,
        "catalog_generation_id": catalog_generation_id,
        "decided_at": decided_at,
        "denial_reason": None,
        "degraded_reason": None,
        "fallback_reason": None,
    }


def degraded_selection_receipt(
    *,
    source: str,
    decided_at: str,
    degraded_reason: str,
    catalog_generation_id: str | None = None,
) -> dict[str, Any]:
    """The ``outcome: degraded`` shape: a selection made under a documented
    degraded condition. ``selected_evidence_versions`` may legitimately stay
    empty on this outcome (unlike ``denied``, a real candidate set WAS
    evaluated) — that cardinality is the caller's own choice via
    ``create_receipt_and_promote``, not encoded by this builder.
    """

    if not degraded_reason:
        raise ProvenanceIntegrityError(
            "degraded_reason is required (non-blank) for outcome=degraded"
        )
    return {
        "outcome": "degraded",
        "source": source,
        "catalog_generation_id": catalog_generation_id,
        "decided_at": decided_at,
        "denial_reason": None,
        "degraded_reason": degraded_reason,
        "fallback_reason": None,
    }


def fallback_selection_receipt(
    *,
    source: str,
    decided_at: str,
    fallback_reason: str,
    catalog_generation_id: str | None = None,
) -> dict[str, Any]:
    """The ``outcome: fallback`` shape (SOL-7): a provider-fallback attempt
    that FOUND at least one candidate — a fallback attempt that finds nothing
    is ``empty``, never ``fallback`` (this builder does not itself decide
    when to fall back; see freeze doc §12 RPC-1.2.a / CARP §3.6 — this module
    only makes the outcome shape constructible once a caller has already
    decided it applies).
    """

    if not fallback_reason:
        raise ProvenanceIntegrityError(
            "fallback_reason is required (non-blank) for outcome=fallback"
        )
    return {
        "outcome": "fallback",
        "source": source,
        "catalog_generation_id": catalog_generation_id,
        "decided_at": decided_at,
        "denial_reason": None,
        "degraded_reason": None,
        "fallback_reason": fallback_reason,
    }


# --- selected_evidence_versions[] entry builders (RPC-2.3, freeze doc §5.1
# rule 8 / §6 row 1, SOL-8/23) -------------------------------------------------


def search_evidence_entry(*, assertion_id: str, assertion_version: int) -> dict[str, Any]:
    """A plain, non-question-scoped ``selected_evidence_versions[]`` entry —
    the legacy-compatible default (``selection_origin`` omitted; ``question_id``/
    ``decided_at`` both ``None``).
    """

    return {
        "assertion_id": assertion_id,
        "assertion_version": assertion_version,
        "question_id": None,
        "decided_at": None,
    }


def catalog_planning_evidence_entry(
    *, assertion_id: str, assertion_version: int, question_id: str, decided_at: str
) -> dict[str, Any]:
    """A CARP evidence-plan-rebased ``selected_evidence_versions[]`` entry
    (SOL-8/23): MUST carry non-null ``question_id`` + ``decided_at`` so the
    per-question selection membership CARP's rebase depends on is never
    silently dropped. Enforced here defensively (fails before the schema
    would) and again by ``search_activity_receipt.schema.yaml``'s own
    ``allOf`` conditional on ``selection_origin: catalog_planning``.
    """

    if not question_id:
        raise ProvenanceIntegrityError(
            "question_id is required (non-blank) for selection_origin=catalog_planning"
        )
    if not decided_at:
        raise ProvenanceIntegrityError(
            "decided_at is required (non-blank) for selection_origin=catalog_planning"
        )
    return {
        "assertion_id": assertion_id,
        "assertion_version": assertion_version,
        "question_id": question_id,
        "decided_at": decided_at,
        "selection_origin": "catalog_planning",
    }


class ProvenanceEnvelopeStore:
    """Workspace-isolated persistence for the origin/envelope/receipt family."""

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        self.workspace_key = _workspace_key(workspace_id)
        self.root = self.paths.root / "provenance_ledger" / "workspaces" / self.workspace_key
        self._schemas = SchemaRegistry(schemas_dir=self.paths.schemas)

    # --- paths ---------------------------------------------------------

    def _origins_dir(self) -> Path:
        return self.root / "origins"

    def _origin_path(self, origin_id: str) -> Path:
        return self._origins_dir() / f"{origin_id}.yaml"

    def _envelopes_dir(self) -> Path:
        return self.root / "envelopes"

    def _envelope_dir(self, envelope_id: str) -> Path:
        return self._envelopes_dir() / envelope_id

    def _envelope_version_path(self, envelope_id: str, version: int) -> Path:
        return self._envelope_dir(envelope_id) / f"v{version}.yaml"

    def _receipt_path(self, envelope_id: str) -> Path:
        return self._envelope_dir(envelope_id) / "receipt.yaml"

    def _manifest_path(self, envelope_id: str) -> Path:
        return self._envelope_dir(envelope_id) / ".generation_manifest.yaml"

    # --- origin (RPC-2.1) -----------------------------------------------

    def write_origin(
        self,
        *,
        origin_version: int = 1,
        method: Mapping[str, Any],
        producer: Mapping[str, Any],
        source_kind: str,
        locator: str | None,
        content_digest: str | None,
        external_receipt_ref: Mapping[str, Any] | None = None,
        parent_origin_refs: Sequence[Mapping[str, Any]] = (),
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Write (or idempotently replay) one canonical ``provenance_origin``.

        Fails closed rather than partially writing: a cross-workspace or
        missing parent ref raises :class:`ProvenanceEnvelopeDenied`; a schema
        violation or a same-``origin_id`` content conflict raises
        :class:`ProvenanceIntegrityError`. Because ``origin_id`` is fully
        content-addressed (freeze doc §4.1 rule 7), a second call with
        byte-identical inputs is a safe no-op (replay-safe) — it never mints a
        duplicate record or silently overwrites the first.

        T2-6: routes through :func:`~.assertion_workspace.resolve_or_deny`
        FIRST (this module's own standing directive 2) — redundant with
        ``__init__``'s own non-blank check today, but keeps every public
        writer speaking the SAME canonical guard/denial shape rather than a
        bespoke ``ValueError``, so a future relaxation of the constructor
        check can never silently widen this write path.
        """

        if not resolve_or_deny(self.workspace_id).allowed:
            raise ProvenanceEnvelopeDenied(REASON_DENIED)

        parent_refs = [dict(p) for p in parent_origin_refs]
        for parent in parent_refs:
            self._require_parent_origin_in_workspace(parent)

        candidate = {
            "origin_version": origin_version,
            "workspace_id": self.workspace_id,
            "method": dict(method),
            "producer": dict(producer),
            "source_kind": source_kind,
            "locator": locator,
            "content_digest": content_digest,
            "external_receipt_ref": dict(external_receipt_ref) if external_receipt_ref else None,
            "parent_origin_refs": parent_refs,
            "created_at": created_at or now_iso(),
        }
        fingerprint = _fingerprint(_material_payload(candidate, ORIGIN_MATERIAL_FIELDS))
        origin_id = f"pvo_{fingerprint}"

        record: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "provenance_origin",
            "origin_id": origin_id,
            **candidate,
            "identity": {
                "algorithm": CANONICAL_ALGORITHM,
                "fingerprint": fingerprint,
                "material_fields": list(ORIGIN_MATERIAL_FIELDS),
            },
        }

        errors = self._schemas.validate(record, "provenance_origin").errors
        if errors:
            raise ProvenanceIntegrityError("; ".join(errors))

        path = self._origin_path(origin_id)
        existing = _read_yaml(path)
        if existing is not None:
            if existing == record:
                return existing  # replay-safe no-op
            raise ProvenanceIntegrityError(
                f"origin {origin_id} already exists on disk with different content "
                "(content-addressed id collision or on-disk tamper)"
            )

        _atomic_write(record, path)
        return record

    def read_origin(self, origin_id: str) -> dict[str, Any] | None:
        """Read one origin, verifying tamper-evident content-binding AND that
        the loaded record's OWN ``origin_id`` equals the requested one.

        SOL-31: a malformed ``origin_id`` shape is treated identically to
        "not found" (fail-closed, no existence leak) — it is validated
        BEFORE any path is built or file read. Because ``origin_id`` is
        content-addressed, ``verify_origin_integrity`` alone proves a
        record is internally self-consistent (its own fingerprint matches
        its own claimed id) -- it does NOT prove that record actually
        belongs at THIS path. Copying a different, otherwise-valid origin's
        bytes onto this ``origin_id``'s canonical filename passes
        self-consistency yet names a DIFFERENT ``origin_id`` than requested;
        that binding mismatch is checked explicitly here and raises
        :class:`ProvenanceIntegrityError` — never silently returns a record
        for a different origin than the one asked for.
        """

        if not isinstance(origin_id, str) or not _ORIGIN_ID_RE.fullmatch(origin_id):
            return None
        record = _read_yaml(self._origin_path(origin_id))
        if record is None:
            return None
        errors = verify_origin_integrity(record)
        if errors:
            raise ProvenanceIntegrityError("; ".join(errors))
        if record.get("origin_id") != origin_id:
            raise ProvenanceIntegrityError(
                "origin_id: the record loaded from this path does not carry the requested "
                "origin_id (tamper-evident mismatch -- stored content does not belong here)"
            )
        return record

    def rebuild_origin_facets(self) -> dict[str, dict[str, Any]]:
        """Rebuild every origin-derived facet for this workspace from the
        canonical records on disk (AC RPC-1 resilience clause). Deterministic
        by construction: calling this twice (the "delete facets and rebuild"
        scenario — there is no separate facet cache to delete, since facets
        are always computed fresh from canonical records, never persisted as
        a second authority) MUST produce byte-identical output.
        """

        origins_dir = self._origins_dir()
        facets: dict[str, dict[str, Any]] = {}
        if not origins_dir.exists():
            return facets
        for path in sorted(origins_dir.glob("*.yaml")):
            record = _read_yaml(path)
            if record is None:
                continue
            errors = verify_origin_integrity(record)
            if errors:
                raise ProvenanceIntegrityError("; ".join(errors))
            facets[record["origin_id"]] = derive_origin_facets(record)
        return facets

    def _require_parent_origin_in_workspace(self, parent_ref: Mapping[str, Any]) -> None:
        origin_id = parent_ref.get("origin_id")
        origin_version = parent_ref.get("origin_version")
        if not isinstance(origin_id, str) or not origin_id:
            raise ProvenanceIntegrityError("parent_origin_refs: origin_id is required")
        # Fail closed (freeze doc §4.2 fixture e / §10 threat boundary 2): a
        # parent origin is resolved ONLY within THIS workspace's own store —
        # an origin belonging to another workspace never resolves here, even
        # if the caller knows its id. Never silently dropped, never promoted
        # to a root-level origin.
        #
        # SOL-31: routed through the VERIFIED read (``read_origin``, which
        # binds identity: the loaded record's own ``origin_id`` must equal
        # the requested one) rather than a bare existence probe — an
        # existence-only check cannot detect a same-filename content
        # substitution. The ref's own ``origin_version`` is additionally
        # bound here (never existence-only on version either): a parent ref
        # naming a stale/mismatched version of an otherwise-real origin is
        # denied the same way a wholly-nonexistent one is.
        origin = self.read_origin(origin_id)
        if origin is None or origin.get("origin_version") != origin_version:
            raise ProvenanceEnvelopeDenied(REASON_DENIED)

    # --- envelope + receipt (RPC-2.2) ------------------------------------

    def create_envelope_v1(
        self,
        *,
        activity_kind: str,
        request_id: str | None = None,
        planned_run_ref: Mapping[str, Any] | None = None,
        parent_run_ref: str | None = None,
        origin_ref: Mapping[str, Any] | None = None,
        aos_refs: Mapping[str, Any] | None = None,
        aos_ref_authorizer: Callable[[Mapping[str, Any], str], bool] | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Write (or idempotently replay) a planning-time ``envelope_version: 1``.

        Freeze doc §5.1a step 1 / §5.1b point 1: v1 carries NO receipt-linkage
        fields at all (never even ``null`` — the schema's own ``allOf``
        partition would reject them). ``activity_kind: planned_run`` requires
        a non-null ``planned_run_ref``; ``search_only`` requires it be absent
        (never a fabricated ``run_id``, freeze doc §5.1 rule 2).

        ``aos_refs`` (RPC-2.4, freeze doc §9/AC RPC-7) round-trips as opaque
        strings only — this method never fetches, loads, or dereferences the
        referenced AOS project/intent/knowledge object. A malformed shape
        (wrong type, blank, too long, or the round-2 ``{}``/partial-null
        forms) fails schema validation directly, below, and raises
        :class:`ProvenanceIntegrityError` (a format defect, not a denial).
        Authorization/cross-workspace validation of an otherwise well-formed
        ref is NOT a check this module can perform itself (the refs are
        opaque by design) — ``aos_ref_authorizer``, when supplied, is called
        with ``(aos_refs, self.workspace_id)`` BEFORE anything is minted or
        persisted; a ``False`` result fails closed with the SAME ONE public
        denial shape every other guard in this module uses
        (:class:`ProvenanceEnvelopeDenied`, freeze doc §9 fixture (d)/§10
        threat boundary 1 — no existence signal).

        T2-6 (hardening): when ``aos_refs`` is present, an
        ``aos_ref_authorizer`` is now REQUIRED — omitting it is itself a
        denial (the SAME one public shape, no existence signal), never a
        silent no-check pass-through. This module cannot resolve AOS policy
        itself (the refs are opaque by design); a caller that supplies
        ``aos_refs`` with no way to authorize them is a defect in the CALLER,
        not a reason to persist an unauthorized-by-construction reference.
        ``aos_refs`` being absent entirely (the canonical no-context shape,
        fixture (a)) is unaffected — no authorizer is required, and none is
        invoked, when there is nothing to authorize.

        T2-6: also routes through :func:`~.assertion_workspace.resolve_or_deny`
        FIRST — see :meth:`write_origin`'s docstring for why this is
        redundant-but-required defense in depth against a future constructor
        relaxation.
        """

        if not resolve_or_deny(self.workspace_id).allowed:
            raise ProvenanceEnvelopeDenied(REASON_DENIED)
        if activity_kind not in ("planned_run", "search_only"):
            raise ProvenanceIntegrityError("activity_kind must be planned_run or search_only")
        if activity_kind == "planned_run" and not planned_run_ref:
            raise ProvenanceIntegrityError("planned_run activity requires a non-null planned_run_ref")
        if activity_kind == "search_only" and planned_run_ref is not None:
            raise ProvenanceIntegrityError("search_only activity must not carry a planned_run_ref")
        if origin_ref is not None:
            self._require_origin_exists(origin_ref)
        if aos_refs is not None:
            # T2-6: an absent authorizer is now itself a denial -- there is no
            # "no check performed" path once aos_refs is present. Checked
            # BEFORE anything is minted or persisted, same as every other
            # guard in this method.
            if aos_ref_authorizer is None or not aos_ref_authorizer(aos_refs, self.workspace_id):
                raise ProvenanceEnvelopeDenied(REASON_DENIED)

        candidate = {
            "workspace_id": self.workspace_id,
            "activity_kind": activity_kind,
            "request_id": request_id,
            "planned_run_ref": dict(planned_run_ref) if planned_run_ref else None,
            "parent_run_ref": parent_run_ref,
            "origin_ref": dict(origin_ref) if origin_ref else None,
            # SOL-6/22: an explicitly-empty dict (`{}`) is NOT the same fact
            # as "no refs supplied" -- it must reach schema validation below
            # and fail `minProperties: 1` (freeze doc §9 fixture c), never be
            # silently folded into the canonical-absence `None` the way a
            # falsy-but-still-distinct value would be. Only `None` itself
            # (aos_refs not supplied at all) takes the omission path.
            "aos_refs": dict(aos_refs) if aos_refs is not None else None,
            "created_at": created_at or now_iso(),
        }
        fingerprint = _fingerprint(_material_payload(candidate, ENVELOPE_MATERIAL_FIELDS))
        envelope_id = f"rre_{fingerprint}"

        record: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "research_run_envelope",
            "envelope_id": envelope_id,
            "envelope_version": 1,
            **candidate,
            "identity": {
                "algorithm": CANONICAL_ALGORITHM,
                "fingerprint": fingerprint,
                "material_fields": list(ENVELOPE_MATERIAL_FIELDS),
            },
        }
        if record["aos_refs"] is None:
            # SOL-6 canonical absence: top-level OMISSION, never an explicit
            # null, is the one canonical "no AOS refs" encoding.
            del record["aos_refs"]

        errors = self._schemas.validate(record, "research_run_envelope").errors
        if errors:
            raise ProvenanceIntegrityError("; ".join(errors))

        path = self._envelope_version_path(envelope_id, 1)
        existing = _read_yaml(path)
        if existing is not None:
            if existing == record:
                return existing
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id} v1 already exists with different content"
            )
        _atomic_write(record, path)
        return record

    def create_receipt_and_promote(
        self,
        envelope_v1: Mapping[str, Any],
        *,
        query: str,
        purpose: str | None,
        scope: Mapping[str, Any],
        candidate_set_digest: str | None,
        selected_evidence_versions: Sequence[Mapping[str, Any]],
        selection_receipt: Mapping[str, Any],
        created_at: str | None = None,
        _interrupt_after_staging: bool = False,
        _interrupt_before_manifest: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Publish the terminal receipt for ``envelope_v1`` and atomically
        promote the envelope to v2 in the SAME call (freeze doc §5.1a
        steps 2-4 / §5.1b) — this module never leaves a receipt published
        with no corresponding v2 promotion, or vice versa.

        Returns ``(receipt, envelope_v2)``. Replay-safe: calling this twice
        with byte-identical inputs against the same ``envelope_v1`` returns
        the same pair without re-appending a generation-manifest entry;
        calling it with DIFFERENT inputs against an already-published
        envelope raises :class:`ProvenanceIntegrityError` (never a silent
        overwrite of an already-published receipt/commitment — freeze doc
        §17.1 rule 5's "no re-triggering already-satisfied references" applied
        here to the envelope/receipt pair).

        T2-1 (hardening): ``envelope_v1`` is NEVER trusted as the source of
        truth by itself — the caller's mapping is only used to name
        ``envelope_id``. Every field this call derives (``workspace_id``,
        ``activity_kind``, ``request_id``, and the ``v2`` base record itself)
        is read from the CANONICAL ``v1.yaml`` reloaded from this store's own
        root, whose own content-binding is re-verified, and whose eight
        shared material fields (``ENVELOPE_MATERIAL_FIELDS``) must byte-equal
        the caller's argument — a forged mapping bearing a real
        ``envelope_id`` but altered fields is rejected before anything is
        minted, never silently trusted because "the id looked right."

        T2-3 (hardening): promotion is a staged transaction, guarded by a
        per-envelope ``flock`` lock (mirrors
        ``assertion_materialization.py``'s claim-ledger lock) — the receipt
        and v2 are written into ``.staging/<envelope_id>/`` first, then
        ``os.replace``d into their canonical paths together, with the
        generation-manifest append as the SOLE commit/visibility point
        (contract §17.7). A crash between the staged write and the manifest
        append leaves an on-disk artifact :meth:`read_envelope` treats as
        NOT-promoted and :meth:`recover_orphaned_promotions` can quarantine
        and converge from — this call is safe to retry with the identical
        inputs at any point.
        """

        if envelope_v1.get("envelope_version") != 1:
            raise ProvenanceIntegrityError(
                "a receipt can only be published against an envelope_version: 1 record"
            )
        if "activity_id" in envelope_v1 or "receipt_commitment" in envelope_v1:
            raise ProvenanceIntegrityError(
                "envelope_v1 must not already carry activity_id/receipt_commitment"
            )
        envelope_id = envelope_v1.get("envelope_id")
        if not isinstance(envelope_id, str) or not envelope_id:
            raise ProvenanceIntegrityError("envelope_v1 must carry a non-blank envelope_id")

        # T2-6: same canonical guard every other public writer now uses.
        if not resolve_or_deny(self.workspace_id).allowed:
            raise ProvenanceEnvelopeDenied(REASON_DENIED)

        envelope_dir = self._envelope_dir(envelope_id)
        envelope_dir.mkdir(parents=True, exist_ok=True)
        lock_path = envelope_dir / ".promotion.lock"
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            return self._create_receipt_and_promote_locked(
                envelope_v1,
                envelope_id,
                query=query,
                purpose=purpose,
                scope=scope,
                candidate_set_digest=candidate_set_digest,
                selected_evidence_versions=selected_evidence_versions,
                selection_receipt=selection_receipt,
                created_at=created_at,
                _interrupt_after_staging=_interrupt_after_staging,
                _interrupt_before_manifest=_interrupt_before_manifest,
            )
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def _create_receipt_and_promote_locked(
        self,
        envelope_v1: Mapping[str, Any],
        envelope_id: str,
        *,
        query: str,
        purpose: str | None,
        scope: Mapping[str, Any],
        candidate_set_digest: str | None,
        selected_evidence_versions: Sequence[Mapping[str, Any]],
        selection_receipt: Mapping[str, Any],
        created_at: str | None,
        _interrupt_after_staging: bool,
        _interrupt_before_manifest: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        # T2-1: reload the CANONICAL v1 from this store's own root -- the
        # caller's `envelope_v1` mapping is never trusted for its field
        # values, only for naming which envelope_id to promote.
        canonical_v1 = _read_yaml(self._envelope_version_path(envelope_id, 1))
        if canonical_v1 is None:
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id} v1 does not exist in this workspace's store"
            )
        identity_errors = verify_envelope_identity(canonical_v1)
        if identity_errors:
            raise ProvenanceIntegrityError("; ".join(identity_errors))
        mismatches = [
            field_name
            for field_name in ENVELOPE_MATERIAL_FIELDS
            if envelope_v1.get(field_name) != canonical_v1.get(field_name)
        ]
        if mismatches:
            raise ProvenanceIntegrityError(
                f"envelope_v1 argument does not match the canonical stored v1 record for: "
                f"{', '.join(mismatches)} (forged mapping rejected)"
            )

        envelope_ref = {"envelope_id": envelope_id, "envelope_version": 1}
        receipt_candidate = {
            "workspace_id": canonical_v1["workspace_id"],
            "activity_kind": canonical_v1["activity_kind"],
            "request_id": canonical_v1.get("request_id"),
            "query": query,
            "purpose": purpose,
            "scope": dict(scope),
            "candidate_set_digest": candidate_set_digest,
            "selected_evidence_versions": [dict(e) for e in selected_evidence_versions],
            "selection_receipt": dict(selection_receipt),
            "envelope_ref": envelope_ref,
            "created_at": created_at or now_iso(),
        }
        receipt_fingerprint = _fingerprint(_material_payload(receipt_candidate, RECEIPT_MATERIAL_FIELDS))
        activity_id = f"sar_{receipt_fingerprint}"
        receipt: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "search_activity_receipt",
            "activity_id": activity_id,
            **receipt_candidate,
            "identity": {
                "algorithm": CANONICAL_ALGORITHM,
                "fingerprint": receipt_fingerprint,
                "material_fields": list(RECEIPT_MATERIAL_FIELDS),
            },
        }
        errors = self._schemas.validate(receipt, "search_activity_receipt").errors
        if errors:
            raise ProvenanceIntegrityError("; ".join(errors))

        v2: dict[str, Any] = dict(canonical_v1)
        v2["envelope_version"] = 2
        v2["activity_id"] = activity_id
        v2["receipt_commitment"] = receipt_fingerprint
        version_digest = _fingerprint(_material_payload(v2, ENVELOPE_VERSION_DIGEST_FIELDS))
        v2["version_digest"] = version_digest

        errors = self._schemas.validate(v2, "research_run_envelope").errors
        if errors:
            raise ProvenanceIntegrityError("; ".join(errors))

        receipt_path = self._receipt_path(envelope_id)
        v2_path = self._envelope_version_path(envelope_id, 2)
        existing_receipt = _read_yaml(receipt_path)
        existing_v2 = _read_yaml(v2_path)
        if existing_receipt is not None or existing_v2 is not None:
            if existing_receipt == receipt and existing_v2 == v2:
                return existing_receipt, existing_v2  # replay-safe no-op
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id} already has a published receipt/v2 with different content"
            )

        # T2-3: staged write first (never touches the canonical path), THEN
        # an atomic os.replace of both files, THEN the manifest append as the
        # sole commit point -- mirrors assertion_inference.py's
        # stage -> promote -> manifest protocol (contract §17.7).
        staging_dir = self._staging_dir(envelope_id)
        _atomic_write(receipt, staging_dir / "receipt.yaml")
        _atomic_write(v2, staging_dir / "v2.yaml")
        if _interrupt_after_staging:
            raise ProvenancePromotionInterrupted("interrupted after staged write")

        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging_dir / "receipt.yaml", receipt_path)
        os.replace(staging_dir / "v2.yaml", v2_path)
        try:
            staging_dir.rmdir()
        except OSError:
            pass

        if _interrupt_before_manifest:
            raise ProvenancePromotionInterrupted("interrupted before manifest entry")

        self._append_manifest_entry(
            envelope_id,
            {
                "record_kind": "research_run_envelope",
                "record_id": envelope_id,
                "version": 2,
                "version_digest": version_digest,
                "fingerprint": receipt_fingerprint,
            },
        )
        return receipt, v2

    def read_envelope(
        self, envelope_id: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Return ``(current envelope, receipt or None)`` for ``envelope_id``.

        "Current" is v2 if published, else v1. T2-2/T2-3 (hardening): a v1
        AND (if present) a v2 have their OWN content-binding
        (``verify_envelope_identity``) recomputed and verified before any
        pair/manifest check runs; a receipt has its own content-binding
        (``verify_receipt_identity``) recomputed and verified the same way.
        A published v2 additionally requires exactly one matching
        generation-manifest entry (T2-4, freeze doc §17.7a reader rule) —
        absent that entry, the v2/receipt pair is treated as NOT-YET-
        PROMOTED (a legitimate crash-window state, converged by
        :meth:`recover_orphaned_promotions`) rather than trusted on the
        strength of its own bytes; a manifest entry that IS present but
        disagrees with the recomputed ``version_digest``/``fingerprint`` is
        tamper-evidence and raises :class:`ProvenanceIntegrityError`. T2-1's
        eight-shared-field v1<->v2 byte equality (freeze doc §5.1b) is also
        enforced here on every read. The six §5.3 cross-record equality
        checks run last, against whatever the above steps determined is
        actually visible.
        """

        v2 = _read_yaml(self._envelope_version_path(envelope_id, 2))
        v1 = _read_yaml(self._envelope_version_path(envelope_id, 1))
        receipt = _read_yaml(self._receipt_path(envelope_id))

        if v1 is None and v2 is None:
            return None, None

        if v1 is not None:
            errors = verify_envelope_identity(v1)
            if errors:
                raise ProvenanceIntegrityError("; ".join(errors))

        manifest_entry = self._find_manifest_entry(
            envelope_id, record_kind="research_run_envelope", version=2
        )

        if v2 is not None:
            errors = verify_envelope_identity(v2)
            if errors:
                raise ProvenanceIntegrityError("; ".join(errors))
            if manifest_entry is None:
                # T2-3: promoted-but-unreferenced (crash window between the
                # atomic file replace and the manifest append) -- treat as
                # NOT-YET-PROMOTED rather than silently trusting an
                # un-committed v2 (freeze doc §17.7 step 2).
                v2 = None
            else:
                self._verify_manifest_entry_fields(envelope_id, v2, manifest_entry)
                # SOL-32 (CRITICAL): a manifested v2 REQUIRES retained v1 to
                # still be present -- freeze doc §5.1b's retention rule is
                # not optional once v2 is genuinely committed (proven by the
                # manifest entry above). Removing v1 out from under a real
                # v2 is a reader-invariant violation, never a silent
                # downgrade to "just serve v2 alone" — that state is
                # supposed to be structurally impossible once promotion
                # actually completed.
                if v1 is None:
                    raise ProvenanceIntegrityError(
                        f"envelope {envelope_id}: v2 is manifested but its retained v1 is "
                        "missing (v1 must be retained for the lifetime of v2, freeze doc §5.1b)"
                    )
                mismatches = [
                    field_name
                    for field_name in ENVELOPE_MATERIAL_FIELDS
                    if v1.get(field_name) != v2.get(field_name)
                ]
                if mismatches:
                    raise ProvenanceIntegrityError(
                        "envelope v1/v2 material-field mismatch on read: "
                        + ", ".join(mismatches)
                    )

        envelope = v2 if v2 is not None else v1
        if envelope is None:
            # Defense in depth: only reachable if v1 was itself absent/removed
            # AND v2 turned out unmanifested (T2-3) -- never surface a bare
            # `None` to verify_pair_integrity, which expects a real mapping.
            return None, None

        if receipt is not None:
            receipt_errors = verify_receipt_identity(receipt)
            if receipt_errors:
                raise ProvenanceIntegrityError("; ".join(receipt_errors))
            if manifest_entry is None or manifest_entry.get("fingerprint") != receipt["identity"]["fingerprint"]:
                # T2-3: a receipt not covered by the SAME manifest entry that
                # committed v2 is a half-pair (crash window) -- not visible
                # until a legitimate promotion (re-run or converged by
                # recovery) commits it.
                receipt = None

        errors = verify_pair_integrity(envelope, receipt)
        if errors:
            raise ProvenanceIntegrityError("; ".join(errors))
        return envelope, receipt

    def recover_orphaned_promotions(self) -> tuple[str, ...]:
        """Contract §17.7 step 6 analog for the envelope/receipt atomic
        promotion (T2-3). Quarantines (never silently adopts or re-uses):

        * a staged-but-never-promoted receipt/v2 pair (crash between the
          staged write and the atomic file replace), and
        * a promoted receipt and/or v2 NOT covered by a single valid
          generation-manifest entry (crash between the file replace and the
          manifest append, or a half-pair where only one of receipt/v2 made
          it to its canonical path).

        A retried :meth:`create_receipt_and_promote` always starts fresh
        from the caller's current candidate — it never resumes from, or
        silently wires in, a quarantined record. Returns the tuple of
        ``envelope_id`` values quarantined; a no-op (empty tuple) when
        nothing is orphaned. Safe to call repeatedly.
        """

        quarantined: list[str] = []
        staging_root = self.root / ".staging"
        if staging_root.is_dir():
            for child in sorted(staging_root.iterdir()):
                if not child.is_dir():
                    continue
                envelope_id = child.name
                quarantine_dir = self.root / "quarantine" / envelope_id / "staging"
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                for item in child.iterdir():
                    os.replace(item, quarantine_dir / item.name)
                try:
                    child.rmdir()
                except OSError:
                    pass
                quarantined.append(envelope_id)

        envelopes_dir = self._envelopes_dir()
        if envelopes_dir.is_dir():
            for envelope_dir in sorted(p for p in envelopes_dir.iterdir() if p.is_dir()):
                envelope_id = envelope_dir.name
                if envelope_id in quarantined:
                    continue
                receipt_path = self._receipt_path(envelope_id)
                v2_path = self._envelope_version_path(envelope_id, 2)
                has_receipt = receipt_path.exists()
                has_v2 = v2_path.exists()
                if not has_receipt and not has_v2:
                    continue
                try:
                    manifest_entry = self._find_manifest_entry(
                        envelope_id, record_kind="research_run_envelope", version=2
                    )
                except ProvenanceIntegrityError:
                    manifest_entry = None
                if has_receipt and has_v2 and manifest_entry is not None:
                    continue  # legitimate, fully-committed promotion
                quarantine_dir = self.root / "quarantine" / envelope_id / "promoted"
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                if has_receipt:
                    os.replace(receipt_path, quarantine_dir / "receipt.yaml")
                if has_v2:
                    os.replace(v2_path, quarantine_dir / "v2.yaml")
                quarantined.append(envelope_id)
        return tuple(quarantined)

    def _staging_dir(self, envelope_id: str) -> Path:
        return self.root / ".staging" / envelope_id

    def _append_manifest_entry(self, envelope_id: str, entry: Mapping[str, Any]) -> None:
        manifest_path = self._manifest_path(envelope_id)
        loaded = _read_yaml(manifest_path) or {}
        entries = list(loaded.get("entries", []))
        key = (entry.get("record_kind"), entry.get("record_id"), entry.get("version"))
        for existing_entry in entries:
            if (
                existing_entry.get("record_kind"),
                existing_entry.get("record_id"),
                existing_entry.get("version"),
            ) == key:
                return  # already committed -- never append a duplicate entry
        entries.append(dict(entry))
        _atomic_write({"entries": entries}, manifest_path)

    def _find_manifest_entry(
        self, envelope_id: str, *, record_kind: str, version: int
    ) -> Mapping[str, Any] | None:
        """T2-4: require EXACTLY ONE entry matching ``(record_kind,
        record_id=envelope_id, version)``; validate every field is present
        and non-blank. Duplicate or malformed entries fail closed (never
        picked arbitrarily) rather than being silently tolerated.
        """

        loaded = _read_yaml(self._manifest_path(envelope_id)) or {}
        entries = loaded.get("entries", [])
        if not isinstance(entries, list):
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id}: generation manifest is malformed (entries is not a list)"
            )

        matches: list[Mapping[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ProvenanceIntegrityError(
                    f"envelope {envelope_id}: generation manifest contains a malformed entry"
                )
            if (
                entry.get("record_kind") == record_kind
                and entry.get("record_id") == envelope_id
                and entry.get("version") == version
            ):
                matches.append(entry)

        if not matches:
            return None
        if len(matches) > 1:
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id}: generation manifest has {len(matches)} entries for "
                f"({record_kind}, v{version}) -- expected exactly one; duplicate manifest "
                "entries are fail-closed"
            )
        entry = matches[0]
        for field_name in ("record_kind", "record_id", "version", "version_digest", "fingerprint"):
            if not entry.get(field_name):
                raise ProvenanceIntegrityError(
                    f"envelope {envelope_id}: generation manifest entry missing/blank field "
                    f"{field_name!r}"
                )
        return entry

    def _verify_manifest_entry_fields(
        self,
        envelope_id: str,
        envelope: Mapping[str, Any],
        entry: Mapping[str, Any],
    ) -> None:
        version = envelope.get("envelope_version")
        recomputed = _fingerprint(_material_payload(envelope, ENVELOPE_VERSION_DIGEST_FIELDS))
        if recomputed != entry.get("version_digest"):
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id} v{version}: recomputed version_digest does not match "
                "its generation-manifest entry (tamper-evident mismatch, freeze doc §17.7a)"
            )
        if entry.get("fingerprint") != envelope.get("receipt_commitment"):
            raise ProvenanceIntegrityError(
                f"envelope {envelope_id} v{version}: manifest entry fingerprint does not equal "
                "envelope.receipt_commitment (tamper-evident mismatch, T2-4)"
            )

    def _require_origin_exists(self, origin_ref: Mapping[str, Any]) -> None:
        # SOL-31: same verified-read + version binding as
        # ``_require_parent_origin_in_workspace`` — an envelope's
        # ``origin_ref`` gets the identical identity+version check a parent
        # origin ref does, never an existence-only probe.
        origin_id = origin_ref.get("origin_id")
        origin_version = origin_ref.get("origin_version")
        if not isinstance(origin_id, str):
            raise ProvenanceEnvelopeDenied(REASON_DENIED)
        origin = self.read_origin(origin_id)
        if origin is None or origin.get("origin_version") != origin_version:
            raise ProvenanceEnvelopeDenied(REASON_DENIED)


# --- guarded top-level entry point ------------------------------------------


def create_activity(
    *,
    workspace_id: str | None,
    activity_kind: str,
    request_id: str | None = None,
    planned_run_ref: Mapping[str, Any] | None = None,
    parent_run_ref: str | None = None,
    origin_ref: Mapping[str, Any] | None = None,
    aos_refs: Mapping[str, Any] | None = None,
    aos_ref_authorizer: Callable[[Mapping[str, Any], str], bool] | None = None,
    paths: FoundryPaths | None = None,
    created_at: str | None = None,
) -> dict[str, Any] | ActivityDenial:
    """Guarded entry point for creating a planning-time envelope.

    Resolves ``workspace_id`` through
    :func:`research_foundry.services.assertion_workspace.resolve_or_deny`
    FIRST (standing directive 2) — a pre-resolution denial is EPHEMERAL
    (freeze doc §5.2 fixture c-1): returns an :class:`ActivityDenial` with no
    ``envelope_id`` ever minted and nothing written to disk. Callers needing
    an HTTP-layer equivalent should use
    ``api.auth.scope.require_workspace_scope`` instead and call
    :meth:`ProvenanceEnvelopeStore.create_envelope_v1` directly.

    ``aos_ref_authorizer`` (RPC-2.4) is forwarded unmodified to
    :meth:`ProvenanceEnvelopeStore.create_envelope_v1` — see that method's
    docstring for the full contract. T2-6 (hardening): omitting it is
    byte-identical to omitting it there — a no-op ONLY when ``aos_refs`` is
    also absent; when ``aos_refs`` is present, omitting the authorizer is
    itself a denial.
    """

    resolution = resolve_or_deny(workspace_id)
    if not resolution.allowed or resolution.workspace_id is None:
        return ActivityDenial(denied=True, reason=REASON_DENIED)
    store = ProvenanceEnvelopeStore(workspace_id=resolution.workspace_id, paths=paths)
    return store.create_envelope_v1(
        activity_kind=activity_kind,
        request_id=request_id,
        planned_run_ref=planned_run_ref,
        parent_run_ref=parent_run_ref,
        origin_ref=origin_ref,
        aos_refs=aos_refs,
        aos_ref_authorizer=aos_ref_authorizer,
        created_at=created_at,
    )


__all__ = [
    "CANONICAL_ALGORITHM",
    "ORIGIN_MATERIAL_FIELDS",
    "ENVELOPE_MATERIAL_FIELDS",
    "RECEIPT_MATERIAL_FIELDS",
    "ENVELOPE_VERSION_DIGEST_FIELDS",
    "REASON_DENIED",
    "ProvenanceEnvelopeError",
    "ProvenanceEnvelopeDenied",
    "ProvenanceIntegrityError",
    "ProvenancePromotionInterrupted",
    "ActivityDenial",
    "ProvenanceEnvelopeStore",
    "verify_origin_integrity",
    "verify_envelope_identity",
    "verify_receipt_identity",
    "verify_pair_integrity",
    "derive_origin_facets",
    "denied_selection_receipt",
    "selected_selection_receipt",
    "empty_selection_receipt",
    "degraded_selection_receipt",
    "fallback_selection_receipt",
    "search_evidence_entry",
    "catalog_planning_evidence_entry",
    "create_activity",
]
