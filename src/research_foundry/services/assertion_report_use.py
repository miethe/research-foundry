"""RPC-1.3 report-use service (AC RPC-3): ``schemas/report_assertion_use.schema.yaml``.

Grounded in ``docs/dev/architecture/research-provenance-contract-freeze.md``
Part 2 §13. A ``report_assertion_use`` record binds ONE verified report
revision to ONE exact cited persistent reference (a ``source_assertion``, an
``inference``, or a ``canonical_claim``). Publication is gated on
verification passing (RPC-OQ-2, §13.2) -- callers MUST only invoke
:func:`publish_report_assertion_uses_for_report` after ``verify_report``
returns ``passed=True`` for the exact ``report_content_digest`` supplied.

Identity model (§13.1/§13.5, worked test vectors verified against this
module -- see ``tests/unit/test_assertion_report_use.py``):

* ``use_id = "rau_" + sha256-canonical-json-v1({workspace_id, report_ref,
  cited_ref, rights_snapshot, created_at})`` -- the same canonicalization
  convention ``assertion_identity.py`` already ships for ``source_assertion``
  (``json.dumps(..., ensure_ascii=False, separators=(",", ":"),
  sort_keys=True)`` then ``sha256(...).hexdigest()``).
* For ``report_family: run_report``, ``report_revision_id = "rrv_" +
  sha256-canonical-json-v1({report_id, report_content_digest})`` (SOL-9,
  §13.1) -- ``report_family: report_draft`` is **out of scope for this
  module** (the task this module implements, RPC-3.1/3.2, is scoped to the
  ``run_report`` family only; ``report_draft`` echoes its own existing
  ``report_version_id`` verbatim per §13.1 and is a follow-up seam, not
  implemented here).
* ``rights_snapshot`` is a copy-only, non-authoritative mirror of the cited
  reference's own ``rights_summary`` (§13.4) -- this module NEVER accepts an
  arbitrary caller-supplied ``rights_snapshot`` for construction; it always
  derives one from an already-resolved persistent record, and
  :func:`assert_rights_snapshot_not_promoted` is the standalone guard proving
  a candidate snapshot cannot assert a value absent from every contributing
  source (agent-writable-path guard rule ``no_agent_cleared_rights_value``,
  restated at freeze doc §15.3).

Resolution scope note (forward-compatibility seam, findings candidate): as of
this tree, no P4 (``assertion_inference``/canonical-claim materialization)
reader exists yet to resolve ``persistent_references.inference_id`` /
``canonical_claim_id`` to a real record. Per AC RPC-3's resilience clause
("missing or legacy persistent refs produce ``legacy_unresolved`` skips, no
error"), this module treats an inference/canonical-claim reference the same
way it treats a genuinely missing reference: a typed ``legacy_unresolved``
skip, never an exception. :func:`fold_rights_snapshots_most_restrictive` is
provided as the most-restrictive-wins fold §13.4 case 2 requires, ready for
that future reader to call, but nothing in this module invokes it today.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..frontmatter import load_md
from ..paths import FoundryPaths
from ..schemas import SchemaRegistry, ValidationResult
from ..yamlio import load_yaml
from .assertion_registry import AssertionRegistry
from .assertion_workspace import resolve_or_deny

REPORT_ASSERTION_USE_IDENTITY_ALGORITHM = "sha256-canonical-json-v1"
REPORT_ASSERTION_USE_MATERIAL_FIELDS: tuple[str, ...] = (
    "workspace_id",
    "report_ref",
    "cited_ref",
    "rights_snapshot",
    "created_at",
)

# Strict id-shape guards (findings T3-1/T3-2/T3-3): every one of these ids is
# ALWAYS a literal prefix + 64 lowercase hex chars when honestly produced by
# this module's own constructors. Validating the shape BEFORE any of these
# values is used to build a filesystem path closes an injection vector a bare
# ``str`` type-check does not -- an attacker-controlled id containing ``/`` or
# ``..`` components could otherwise escape the intended subdirectory even
# before a symlink/resolve() check ever runs. Mirrors the existing
# ``_ASSERTION_ID_RE``/``_INFERENCE_ID_RE`` convention in
# ``assertion_materialization.py``/``canonical_claim_materialization.py``.
_ASSERTION_ID_RE = re.compile(r"^ast_[a-f0-9]{64}$")
_REPORT_REVISION_ID_RE = re.compile(r"^rrv_[a-f0-9]{64}$")
_USE_ID_RE = re.compile(r"^rau_[a-f0-9]{64}$")

_RESTRICTION_KEYS: tuple[str, ...] = (
    "incorporation_into_other_products",
    "adaptation",
    "commercial_use",
    "redistribution",
    "bulk_retrieval",
    "model_training",
)

# Most-restrictive-wins rank tables (freeze doc §13.4 case 2). These orderings
# are this module's own defensible default -- the freeze doc names the
# principle ("if any contributing assertion's clearance_status is
# PROHIBITED/LEGAL_REVIEW_REQUIRED, the snapshot's clearance_status is that
# value") but does not freeze a total order across every enum member; higher
# rank wins. Flagged as a contract ambiguity / findings candidate in the
# implementation report for this task.
_CLEARANCE_RANK: dict[str, int] = {
    "CLEARED_OPEN_LICENSE": 0,
    "CLEARED_PUBLIC_DOMAIN": 0,
    "CLEARED_FACTS_ONLY": 1,
    "CLEARED_PERMISSION": 1,
    "LOCAL_VALIDATION_ONLY": 2,
    "INTERNAL_ONLY": 3,
    "CONTRACT_RESTRICTED": 4,
    "PERMISSION_REQUIRED": 5,
    "UNKNOWN": 6,
    "LEGAL_REVIEW_REQUIRED": 7,
    "PROHIBITED": 8,
}
_REVIEW_RANK: dict[str, int] = {
    "human_reviewed": 0,
    "counsel_approved": 0,
    "agent_triage_only": 1,
    "unknown": 2,
    "expired": 3,
    "legal_review_required_before_commercial_use": 4,
    "counsel_rejected": 5,
}
_RESTRICTION_VALUE_RANK: dict[str, int] = {
    "allowed": 0,
    "allowed_with_conditions": 1,
    "not_addressed": 2,
    "unknown": 2,
    "prohibited": 3,
}
_COPYRIGHT_RANK: dict[str, int] = {
    "public_domain": 0,
    "us_federal_government_work": 0,
    "open_license": 0,
    "mixed_or_third_party": 1,
    "unknown": 2,
    "copyrighted": 2,
}
_ACCESS_RANK: dict[str, int] = {
    "public_web": 0,
    "open_repository": 0,
    "government_source": 0,
    "author_provided_copy": 1,
    "purchased_copy": 1,
    "personal_subscription": 1,
    "institutional_subscription": 1,
    "direct_permission": 1,
    "licensed_api": 2,
    "data_use_agreement": 2,
    "other": 2,
    "unknown": 2,
    "partner_confidential": 3,
}


class ReportAssertionUseError(ValueError):
    """Base error for the report-use service."""


class ReportAssertionUseConflict(ReportAssertionUseError):
    """An immutable ``report_assertion_use`` record exists with different bytes.

    Per freeze doc §13.5, the ONLY way to reach "same ``use_id``, different
    stored bytes" is a write-path bug or race -- this is the residual
    corruption guard, mirroring ``assertion_materialization.py``'s
    ``MaterializationConflict``, never a routine "stale rights fold" (that
    case mints a genuinely different ``use_id`` instead, since
    ``rights_snapshot`` is material to identity).
    """


def _digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _atomic_dump_yaml(data: Mapping[str, Any], path: Path) -> None:
    """Write one YAML artifact atomically, with a durable file flush.

    Mirrors ``assertion_materialization.py``'s ``_atomic_dump`` byte-for-byte
    (tempfile -> fsync -> ``os.replace``) -- duplicated locally rather than
    imported cross-module since that helper is a private, unexported symbol
    of a file this task's owner list excludes from edits.
    """

    from ..yamlio import dumps_yaml

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


# --- Rights-snapshot canonicalization (SOL-10/21, freeze doc §13.4) ---------


def normalize_rights_snapshot(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Expand every absent sub-field to its schema-documented default.

    Two sources that are semantically identical but stored with different
    shorthand (a bare ``{}`` vs. the fully-spelled all-``"unknown"`` form)
    must contribute identical bytes to ``identity.fingerprint`` -- this is
    the canonicalization step freeze doc §13.4 (SOL-10/21) requires. A key
    that is *absent* and a key that is *explicitly* ``None`` canonicalize
    identically (the same rule §4.1 rule 7 establishes one level up).
    """

    source = dict(raw) if isinstance(raw, Mapping) else {}

    def _get(key: str, default: Any) -> Any:
        value = source.get(key, default)
        return default if value is None else value

    raw_restrictions = source.get("restrictions")
    raw_restrictions = raw_restrictions if isinstance(raw_restrictions, Mapping) else {}
    restrictions = {
        key: (raw_restrictions.get(key) or "unknown") for key in _RESTRICTION_KEYS
    }

    return {
        "mirror_of_record_id": source.get("mirror_of_record_id"),
        "mirror_derived_at": source.get("mirror_derived_at"),
        # Hard governance invariant (freeze doc §13.4/§15.3): never authoritative.
        "mirror_is_authoritative": False,
        "rights_record_ids": list(_get("rights_record_ids", [])),
        "reuse_assessment_ids": list(_get("reuse_assessment_ids", [])),
        "permission_record_ids": list(_get("permission_record_ids", [])),
        "copyright_status": _get("copyright_status", "unknown"),
        "access_basis": _get("access_basis", "unknown"),
        "restrictions": restrictions,
        "clearance_status": _get("clearance_status", "UNKNOWN"),
        "review_status": _get("review_status", "unknown"),
        "rights_triage_failure": source.get("rights_triage_failure"),
    }


def _max_by_rank(values: Sequence[str], rank_table: Mapping[str, int]) -> str:
    best_value = values[0]
    best_rank = rank_table.get(best_value, 0)
    for value in values[1:]:
        rank = rank_table.get(value, 0)
        if rank > best_rank:
            best_rank = rank
            best_value = value
    return best_value


def fold_rights_snapshots_most_restrictive(
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Most-restrictive-wins fold over contributing ``rights_summary`` mappings.

    Freeze doc §13.4 case 2: an ``inference``/``canonical_claim`` cited_ref
    has no ``rights_summary`` of its own -- the writer folds every
    contributing ``source_assertion``'s ``rights_summary`` transitively,
    picking the most-restrictive value per sub-field, never an average,
    never first-seen, never a silent omission. Never invoked by this module
    today (no P4 reader exists yet to supply the contributing snapshots) --
    provided as the ready-to-call primitive a future P4 integration needs.
    """

    normalized_all = [normalize_rights_snapshot(s) for s in snapshots]
    if not normalized_all:
        return normalize_rights_snapshot(None)

    ids = sorted({rid for s in normalized_all for rid in s["rights_record_ids"]})
    reuse_ids = sorted({rid for s in normalized_all for rid in s["reuse_assessment_ids"]})
    permission_ids = sorted({rid for s in normalized_all for rid in s["permission_record_ids"]})
    restrictions = {
        key: _max_by_rank([s["restrictions"][key] for s in normalized_all], _RESTRICTION_VALUE_RANK)
        for key in _RESTRICTION_KEYS
    }
    failures = [s["rights_triage_failure"] for s in normalized_all if s["rights_triage_failure"] is not None]

    return {
        "mirror_of_record_id": None,
        "mirror_derived_at": None,
        "mirror_is_authoritative": False,
        "rights_record_ids": ids,
        "reuse_assessment_ids": reuse_ids,
        "permission_record_ids": permission_ids,
        "copyright_status": _max_by_rank([s["copyright_status"] for s in normalized_all], _COPYRIGHT_RANK),
        "access_basis": _max_by_rank([s["access_basis"] for s in normalized_all], _ACCESS_RANK),
        "restrictions": restrictions,
        "clearance_status": _max_by_rank([s["clearance_status"] for s in normalized_all], _CLEARANCE_RANK),
        "review_status": _max_by_rank([s["review_status"] for s in normalized_all], _REVIEW_RANK),
        "rights_triage_failure": failures[0] if failures else None,
    }


def assert_rights_snapshot_not_promoted(
    candidate: Mapping[str, Any],
    contributing_summaries: Sequence[Mapping[str, Any]],
) -> None:
    """Raise :class:`ReportAssertionUseError` if ``candidate`` asserts a rights
    value absent from every contributing source's own ``rights_summary``.

    Direct, standalone enforcement of the ``no_agent_cleared_rights_value``
    guard (freeze doc §13.4/§15.3) applied to report-use construction: a
    ``rights_snapshot`` is a passthrough record of fact, never an
    independent determination. This is checked per sub-field (never merely
    "does the whole object match one source") so a candidate cannot mix a
    permissive ``clearance_status`` from one contributor with a restrictive
    ``review_status`` from nowhere at all.
    """

    normalized_candidate = normalize_rights_snapshot(candidate)
    sources = [normalize_rights_snapshot(s) for s in contributing_summaries]
    if not sources:
        sources = [normalize_rights_snapshot(None)]

    for key in ("copyright_status", "access_basis", "clearance_status", "review_status"):
        value = normalized_candidate[key]
        if not any(source[key] == value for source in sources):
            raise ReportAssertionUseError(
                f"rights_snapshot_promotion_rejected: {key}={value!r} is not present "
                "on any contributing source"
            )
    for key in _RESTRICTION_KEYS:
        value = normalized_candidate["restrictions"][key]
        if not any(source["restrictions"][key] == value for source in sources):
            raise ReportAssertionUseError(
                f"rights_snapshot_promotion_rejected: restrictions.{key}={value!r} is not "
                "present on any contributing source"
            )


# --- Identity (§13.1/§13.5) --------------------------------------------------


def canonical_report_assertion_use_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact payload from which a report-use identity is derived."""

    return {
        "workspace_id": record.get("workspace_id"),
        "report_ref": record.get("report_ref"),
        "cited_ref": record.get("cited_ref"),
        "rights_snapshot": normalize_rights_snapshot(record.get("rights_snapshot")),
        "created_at": record.get("created_at"),
    }


def canonical_report_assertion_use_json(record: Mapping[str, Any]) -> str:
    """Serialize the identity payload with the stable v1 canonical JSON form."""

    return json.dumps(
        canonical_report_assertion_use_payload(record),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def report_assertion_use_fingerprint(record: Mapping[str, Any]) -> str:
    """Calculate the SHA-256 fingerprint for a report-use payload."""

    return sha256(canonical_report_assertion_use_json(record).encode("utf-8")).hexdigest()


def report_assertion_use_id(record: Mapping[str, Any]) -> str:
    """Calculate the public immutable ``use_id`` (``rau_`` + fingerprint)."""

    return f"rau_{report_assertion_use_fingerprint(record)}"


def report_revision_id_for_run_report(report_id: str, report_content_digest: str) -> str:
    """SOL-9's frozen ``run_report`` formula (freeze doc §13.1).

    ``"rrv_" + sha256-canonical-json-v1({report_id, report_content_digest})``,
    the exact convention ``assertion_identity.py`` already ships. Verified
    against the freeze doc's worked test vector in
    ``tests/unit/test_assertion_report_use.py``.
    """

    payload = {"report_id": report_id, "report_content_digest": report_content_digest}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return f"rrv_{sha256(encoded.encode('utf-8')).hexdigest()}"


# --- report_ref / cited_ref builders (SOL-9 canonical normalization) -------


def build_report_ref(
    *,
    report_id: str,
    report_content_digest: str,
    report_revision_id: str | None = None,
) -> dict[str, Any]:
    """Build a schema-shaped ``report_ref`` for ``report_family: run_report``.

    ``report_family: report_draft`` is out of scope for this module (see
    the module docstring) -- callers needing that family must build their
    own ``report_ref`` echoing the existing ``report_version_id`` verbatim.
    """

    if not report_id:
        raise ReportAssertionUseError("run_report report_ref requires report_id")
    if not report_content_digest:
        raise ReportAssertionUseError("run_report report_ref requires report_content_digest")
    computed = report_revision_id_for_run_report(report_id, report_content_digest)
    if report_revision_id is not None and report_revision_id != computed:
        raise ReportAssertionUseError(
            "report_revision_id does not match the frozen rrv_ formula for "
            "report_family=run_report"
        )
    return {
        "report_family": "run_report",
        "report_id": report_id,
        "report_draft_id": None,
        "report_content_digest": report_content_digest,
        "report_revision_id": computed,
    }


def build_cited_ref(
    *,
    ref_kind: str,
    assertion_id: str | None = None,
    assertion_version: int | None = None,
    inference_id: str | None = None,
    inference_version: int | None = None,
    canonical_claim_id: str | None = None,
    canonical_claim_version: int | None = None,
) -> dict[str, Any]:
    """Build a schema-shaped ``cited_ref`` -- all six id/version fields always
    explicitly present (SOL-9), the two inactive kinds' four fields always
    the literal ``null``.
    """

    base: dict[str, Any] = {
        "ref_kind": ref_kind,
        "assertion_id": None,
        "assertion_version": None,
        "inference_id": None,
        "inference_version": None,
        "canonical_claim_id": None,
        "canonical_claim_version": None,
    }
    if ref_kind == "source_assertion":
        if not assertion_id or not assertion_version:
            raise ReportAssertionUseError(
                "source_assertion cited_ref requires assertion_id and assertion_version"
            )
        base["assertion_id"] = assertion_id
        base["assertion_version"] = assertion_version
    elif ref_kind == "inference":
        if not inference_id or not inference_version:
            raise ReportAssertionUseError(
                "inference cited_ref requires inference_id and inference_version"
            )
        base["inference_id"] = inference_id
        base["inference_version"] = inference_version
    elif ref_kind == "canonical_claim":
        if not canonical_claim_id or not canonical_claim_version:
            raise ReportAssertionUseError(
                "canonical_claim cited_ref requires canonical_claim_id and "
                "canonical_claim_version"
            )
        base["canonical_claim_id"] = canonical_claim_id
        base["canonical_claim_version"] = canonical_claim_version
    else:
        raise ReportAssertionUseError(f"unknown ref_kind: {ref_kind!r}")
    return base


# --- Resolution (§13.5's per-ref currency/eligibility/workspace rules) -----


@dataclass(frozen=True)
class PersistentRefResolution:
    """Outcome of resolving one claim's ``persistent_references`` block."""

    status: str  # "resolved" | "legacy_unresolved" | "stale_persistent_reference"
    cited_ref: dict[str, Any] | None
    rights_summary: dict[str, Any] | None
    reason: str | None


@dataclass(frozen=True)
class PrepareOutcome:
    """Outcome of preparing one candidate ``report_assertion_use`` record."""

    status: str  # "prepared" | "legacy_unresolved" | "stale_persistent_reference"
    reason: str | None
    record: dict[str, Any] | None
    use_id: str | None


@dataclass(frozen=True)
class SkippedClaim:
    claim_id: str | None
    status: str
    reason: str | None


@dataclass(frozen=True)
class ReportAssertionUseBatchResult:
    """Outcome of publishing every cited claim of one verified report revision."""

    status: str  # "completed" | "denied"
    reason: str | None
    published: tuple[str, ...] = ()
    skipped: tuple[SkippedClaim, ...] = field(default_factory=tuple)


class ReportAssertionUseService:
    """Workspace-isolated prepare/validate/publish/replay for report-use records.

    Storage reuses the SAME workspace-scoped root
    ``AssertionRegistry.root`` already establishes
    (``<foundry-root>/assertion_ledger/workspaces/<sha256(workspace_id)>/``,
    per the findings doc's standing directive 2 -- "reuse canonical
    workspace guards ... never invent a fourth") with one new subtree,
    ``report_assertion_uses/``:

    * ``report_assertion_uses/records/<use_id>.yaml`` -- the canonical,
      content-addressed, immutable record (mirrors
      ``AssertionMaterializer._write_immutable``'s conflict-checked atomic
      write: identical bytes at an existing path is an idempotent replay
      no-op; different bytes at the same content-addressed path is a
      :class:`ReportAssertionUseConflict`).
    * ``report_assertion_uses/manifests/<report_revision_id>.yaml`` -- an
      append-only, per-report-revision generation manifest (freeze doc
      §17.7a's tamper-evidence-root concept, applied to a non-versioned
      entity -- see the module docstring / this task's implementation
      report for the scope note on why this is a deliberately lighter
      mechanism than §17.7a's full versioned-entity protocol).
    """

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        self._assertion_registry = AssertionRegistry(workspace_id=workspace_id, paths=self.paths)
        self.root = self._assertion_registry.root / "report_assertion_uses"
        self.schemas = SchemaRegistry(schemas_dir=self.paths.schemas)

    # -- paths ---------------------------------------------------------

    def _use_path(self, use_id: str) -> Path:
        if not _USE_ID_RE.fullmatch(use_id):
            raise ReportAssertionUseError(f"invalid use_id: {use_id!r}")
        return self.root / "records" / f"{use_id}.yaml"

    def _manifest_path(self, report_revision_id: str) -> Path:
        if not _REPORT_REVISION_ID_RE.fullmatch(report_revision_id):
            raise ReportAssertionUseError(f"invalid report_revision_id: {report_revision_id!r}")
        return self.root / "manifests" / f"{report_revision_id}.yaml"

    def _assertion_path(self, assertion_id: str) -> Path:
        return self._assertion_registry.root / "assertions" / f"{assertion_id}.yaml"

    def _verification_pass_path(self, report_revision_id: str) -> Path:
        if not _REPORT_REVISION_ID_RE.fullmatch(report_revision_id):
            raise ReportAssertionUseError(f"invalid report_revision_id: {report_revision_id!r}")
        return self.root / "verification_passes" / f"{report_revision_id}.yaml"

    def _publication_outcome_path(self, report_revision_id: str) -> Path:
        if not _REPORT_REVISION_ID_RE.fullmatch(report_revision_id):
            raise ReportAssertionUseError(f"invalid report_revision_id: {report_revision_id!r}")
        return self.root / "publication_outcomes" / f"{report_revision_id}.yaml"

    def _revision_lock_path(self, report_revision_id: str) -> Path:
        if not _REPORT_REVISION_ID_RE.fullmatch(report_revision_id):
            raise ReportAssertionUseError(f"invalid report_revision_id: {report_revision_id!r}")
        path = self.root / "locks" / f"{report_revision_id}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @contextmanager
    def _revision_lock(self, report_revision_id: str) -> Iterator[None]:
        """Serialize every read-modify-write against ONE report revision's
        shared state (verification-pass anchor, generation manifest,
        publication-outcome marker -- T3-2/T3-5) behind a single per-revision
        ``flock``. Mirrors ``assertion_materialization.py``'s per-run claim
        ledger lock convention; a fresh ``os.open``/``flock``/``close`` cycle
        per call is not reentrant-unsafe since nothing below ever acquires
        this SAME lock a second time while already holding it.
        """

        lock_path = self._revision_lock_path(report_revision_id)
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def _is_safe_workspace_path(self, path: Path) -> bool:
        """Symlink/traversal defense for a resolver READ (T3-3).

        A resolved reference must never be honored when the path a
        legitimately-shaped id resolves to is actually a symlink, or when
        its real (``Path.resolve()``) location escapes this workspace's own
        assertion-ledger root -- e.g. a same-named file at the expected
        path replaced with a symlink into another workspace, or anywhere
        else on the filesystem. Returns ``False`` (never raises) so callers
        can fold this into their existing "not found here" resolution
        branch without adding a new failure shape / existence leak.
        """

        if path.is_symlink():
            return False
        try:
            root_resolved = self._assertion_registry.root.resolve(strict=False)
            resolved = path.resolve(strict=False)
        except OSError:
            return False
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            return False
        return True

    # -- resolution ------------------------------------------------------

    def resolve_cited_reference(
        self, persistent_references: Mapping[str, Any] | None
    ) -> PersistentRefResolution:
        """Resolve one claim's ``persistent_references`` block to a cited_ref.

        Cross-workspace note: a ``source_assertion`` is read from THIS
        workspace's own assertion-ledger directory only (never a different
        workspace's) -- storage partitioning itself is the fail-closed
        mechanism (findings F14/standing directive 2's workspace guard
        reuse), so an assertion physically stored elsewhere is
        indistinguishable from "not found here" and resolves to
        ``legacy_unresolved``, never a cross-workspace probe.
        """

        if not isinstance(persistent_references, Mapping):
            return PersistentRefResolution(
                status="legacy_unresolved",
                cited_ref=None,
                rights_summary=None,
                reason="missing_persistent_references",
            )

        assertion_id = persistent_references.get("source_assertion_id")
        assertion_version = persistent_references.get("assertion_version")
        inference_id = persistent_references.get("inference_id")
        canonical_claim_id = persistent_references.get("canonical_claim_id")

        if assertion_id and assertion_version:
            return self._resolve_source_assertion(assertion_id, assertion_version)
        if inference_id or canonical_claim_id:
            # No P4 reader exists yet in this tree to resolve inference/
            # canonical-claim ids to a real record (module docstring). Treat
            # exactly like a missing reference -- typed skip, never an error.
            return PersistentRefResolution(
                status="legacy_unresolved",
                cited_ref=None,
                rights_summary=None,
                reason="inference_or_canonical_claim_resolver_not_available",
            )
        return PersistentRefResolution(
            status="legacy_unresolved",
            cited_ref=None,
            rights_summary=None,
            reason="missing_persistent_references",
        )

    def _resolve_source_assertion(
        self, assertion_id: str, assertion_version: int
    ) -> PersistentRefResolution:
        if not isinstance(assertion_id, str) or not _ASSERTION_ID_RE.fullmatch(assertion_id):
            # Malformed shape (including any path-traversal-shaped id, e.g.
            # containing "/" or "..") is indistinguishable from "not found"
            # -- never a distinct error, never a hint that the shape itself
            # was rejected (freeze doc §13.6 example (d)'s no-existence-leak
            # principle, applied to id validation).
            return PersistentRefResolution(
                status="legacy_unresolved",
                cited_ref=None,
                rights_summary=None,
                reason="source_assertion_not_found",
            )
        path = self._assertion_path(assertion_id)
        if not path.exists() or not self._is_safe_workspace_path(path):
            # Absent, a symlink, or resolving outside this workspace's own
            # assertion root (T3-3) all collapse to the SAME "not found"
            # signal -- a resolver read never distinguishes "doesn't exist"
            # from "exists but is an escape attempt".
            return PersistentRefResolution(
                status="legacy_unresolved",
                cited_ref=None,
                rights_summary=None,
                reason="source_assertion_not_found",
            )
        data = load_yaml(path)
        if not isinstance(data, dict) or data.get("assertion_id") != assertion_id:
            return PersistentRefResolution(
                status="legacy_unresolved",
                cited_ref=None,
                rights_summary=None,
                reason="source_assertion_invalid_or_identity_mismatch",
            )
        if data.get("assertion_version") != assertion_version:
            return PersistentRefResolution(
                status="stale_persistent_reference",
                cited_ref=None,
                rights_summary=None,
                reason="assertion_version_not_current",
            )
        if data.get("lifecycle_state") != "eligible":
            return PersistentRefResolution(
                status="stale_persistent_reference",
                cited_ref=None,
                rights_summary=None,
                reason="assertion_not_eligible",
            )
        # SOL-36: report-use is a fourth F19 citation writer -- the immutable
        # `lifecycle_state` field above never flips when P6 authoritatively
        # blocks a source assertion (the separate `lifecycle_policy/<id>.yaml`
        # artifact is the real boundary, `assertion_impact.py`'s own
        # "immutable source assertion is never overwritten" rule). Consulting
        # ONLY the raw field, as the check above did alone, lets a new
        # report-use cite a genuinely policy-blocked assertion -- exactly the
        # blindness `_recheck_transitive_support`/`resolve_support` already
        # close for the other three writers. A present-but-invalid policy
        # artifact (`policy_invalid`) fails closed the same way `blocked`
        # does -- never silently treated as still eligible.
        from .assertion_impact import effective_source_assertion_lifecycle_state

        effective_state = effective_source_assertion_lifecycle_state(
            root=self._assertion_registry.root, assertion_id=assertion_id
        )
        if effective_state != "eligible":
            return PersistentRefResolution(
                status="stale_persistent_reference",
                cited_ref=None,
                rights_summary=None,
                reason=(
                    "assertion_policy_blocked"
                    if effective_state == "blocked"
                    else "assertion_policy_invalid"
                ),
            )
        cited_ref = build_cited_ref(
            ref_kind="source_assertion",
            assertion_id=assertion_id,
            assertion_version=assertion_version,
        )
        rights_summary = data.get("rights_summary")
        rights_summary = dict(rights_summary) if isinstance(rights_summary, Mapping) else {}
        return PersistentRefResolution(
            status="resolved",
            cited_ref=cited_ref,
            rights_summary=rights_summary,
            reason=None,
        )

    # -- prepare / validate / publish -------------------------------------

    def prepare_report_assertion_use(
        self,
        *,
        report_ref: Mapping[str, Any],
        persistent_references: Mapping[str, Any] | None,
        created_at: str,
    ) -> PrepareOutcome:
        """Prepare (not publish) one candidate ``report_assertion_use`` record."""

        resolution = self.resolve_cited_reference(persistent_references)
        if resolution.status != "resolved":
            return PrepareOutcome(
                status=resolution.status, reason=resolution.reason, record=None, use_id=None
            )

        record: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "report_assertion_use",
            "workspace_id": self.workspace_id,
            "report_ref": dict(report_ref),
            "cited_ref": resolution.cited_ref,
            "rights_snapshot": normalize_rights_snapshot(resolution.rights_summary),
            "created_at": created_at,
        }
        fingerprint = report_assertion_use_fingerprint(record)
        use_id = f"rau_{fingerprint}"
        record["use_id"] = use_id
        record["identity"] = {
            "algorithm": REPORT_ASSERTION_USE_IDENTITY_ALGORITHM,
            "fingerprint": fingerprint,
            "material_fields": list(REPORT_ASSERTION_USE_MATERIAL_FIELDS),
        }
        return PrepareOutcome(status="prepared", reason=None, record=record, use_id=use_id)

    def validate(self, record: Mapping[str, Any]) -> ValidationResult:
        return self.schemas.validate(dict(record), "report_assertion_use")

    def publish(self, record: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        """Atomically publish one prepared record.

        Returns ``("published", record)`` on a fresh write, or
        ``("replayed", existing_record)`` when the identical content-addressed
        record already exists (idempotent no-op, freeze doc §13.5). Raises
        :class:`ReportAssertionUseConflict` when a different record already
        occupies this ``use_id`` (residual corruption guard, never expected
        in honest operation since ``use_id`` is content-derived). For a
        genuinely NEW ``use_id`` (never for the replay/conflict branch
        above, which already compares against the immutable file on disk),
        also raises :class:`ReportAssertionUseError` when the record's
        ``cited_ref``/``rights_snapshot`` no longer matches what re-running
        the SAME resolution right now produces -- see
        :meth:`_assert_fresh_write_is_grounded`.
        """

        record = dict(record)
        use_id = record.get("use_id")
        if not isinstance(use_id, str) or not _USE_ID_RE.fullmatch(use_id):
            raise ReportAssertionUseError("record is missing a valid use_id")

        path = self._use_path(use_id)
        if path.exists():
            existing = load_yaml(path)
            if not isinstance(existing, dict) or existing != record:
                raise ReportAssertionUseConflict("replay_conflict")
            self._append_manifest_entry(existing)
            return "replayed", existing

        # T3-1: the write-boundary hardening pass. Every check below runs
        # ONLY for a genuinely new use_id (never for the replay/conflict
        # branch above, which already compares the candidate against the
        # immutable file on disk byte-for-byte).
        self._assert_identity_is_self_consistent(record)
        self._assert_workspace_matches(record)
        self._assert_report_revision_is_verified(record)
        self._assert_fresh_write_is_grounded(record)

        validation = self.validate(record)
        if not validation.ok:
            raise ReportAssertionUseError(
                "invalid report_assertion_use: " + "; ".join(validation.errors)
            )
        _atomic_dump_yaml(record, path)
        self._append_manifest_entry(record)
        return "published", record

    def _assert_identity_is_self_consistent(self, record: Mapping[str, Any]) -> None:
        """Recompute ``identity.fingerprint``/``use_id`` from THIS record's own
        canonical bytes and require both to match exactly (T3-1).

        A ``report_assertion_use``'s identity is content-derived, never
        caller-asserted. :meth:`prepare_report_assertion_use` always sets
        ``identity.fingerprint``/``use_id`` honestly, but ``publish()`` is a
        public entry point a caller can invoke directly with a hand-mutated
        record (e.g. a changed ``created_at`` while the old ``use_id`` is
        kept) -- this closes that gap at the actual write boundary rather
        than trusting it was only ever reached through ``prepare``.
        """

        use_id = record.get("use_id")
        identity = record.get("identity")
        stored_fingerprint = identity.get("fingerprint") if isinstance(identity, Mapping) else None
        recomputed_fingerprint = report_assertion_use_fingerprint(record)
        recomputed_use_id = f"rau_{recomputed_fingerprint}"
        if (
            not isinstance(stored_fingerprint, str)
            or stored_fingerprint != recomputed_fingerprint
            or use_id != recomputed_use_id
        ):
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: identity.fingerprint/use_id do "
                "not match the record's own canonical bytes (forged or stale identity)"
            )

    def _assert_workspace_matches(self, record: Mapping[str, Any]) -> None:
        """Require ``record['workspace_id'] == self.workspace_id`` (T3-1/T3-3).

        Storage partitioning by workspace-scoped root is not, by itself, a
        content check -- nothing previously stopped a record physically
        written under workspace A's root from claiming ``workspace_id:
        "workspace-B"`` inside its own bytes. Enforced here, at the actual
        write boundary, for every fresh publish.
        """

        workspace_id = record.get("workspace_id")
        if workspace_id != self.workspace_id:
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: record workspace_id "
                f"{workspace_id!r} does not match the publishing service's "
                f"workspace {self.workspace_id!r}"
            )

    def _assert_report_revision_is_verified(self, record: Mapping[str, Any]) -> None:
        """Require a durable, already-recorded verification-pass attestation
        for this record's EXACT ``report_revision_id`` (T3-1/T3-4).

        Two things happen here, in order:

        1. The frozen ``rrv_`` formula (SOL-9, §13.1) is recomputed from
           THIS record's own ``report_id``/``report_content_digest`` and
           compared against its claimed ``report_revision_id`` -- a
           formula-invalid revision id is rejected outright. This recompute
           is the ONLY value ever used to build the attestation path below
           (never the caller-supplied ``report_revision_id`` string
           directly), so an attacker cannot use a crafted revision id to
           probe or traverse the attestation store.
        2. ONLY when that recompute succeeds does this check for a durable
           ``verification_passes/<report_revision_id>.yaml`` anchor on
           disk. That anchor is written EXCLUSIVELY by the module-private
           :meth:`_resolve_verification_pass_created_at`, reachable only
           via the public :func:`attest_verification_pass`, invoked
           EXCLUSIVELY from ``verification.py::verify_report``'s own call
           site after it decided ``passed=True`` for this exact digest
           (RPC-OQ-2/§13.2, K-FINAL-1/SOL-35). A direct ``publish()`` call
           for a report that was never actually run through that seam has
           no such attestation and is refused -- publish() never accepts a
           caller's bare say-so that a report passed verification.

        ``report_family`` values other than ``run_report`` are out of
        scope for this module (module docstring) and are refused the same
        way :meth:`_assert_fresh_write_is_grounded` refuses a
        non-``source_assertion`` ``cited_ref``: there is no independently
        re-verifiable formula for them here.
        """

        report_ref = record.get("report_ref")
        if not isinstance(report_ref, Mapping):
            raise ReportAssertionUseError("record is missing report_ref")

        report_family = report_ref.get("report_family")
        if report_family != "run_report":
            raise ReportAssertionUseError(
                f"cannot publish report_assertion_use: report_family={report_family!r} "
                "is not independently re-verifiable at publish time"
            )

        report_id = report_ref.get("report_id")
        report_content_digest = report_ref.get("report_content_digest")
        if (
            not isinstance(report_id, str)
            or not report_id
            or not isinstance(report_content_digest, str)
            or not report_content_digest
        ):
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: run_report report_ref is "
                "missing report_id/report_content_digest"
            )

        expected_revision_id = report_revision_id_for_run_report(report_id, report_content_digest)
        if report_ref.get("report_revision_id") != expected_revision_id:
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: report_revision_id does not "
                "match the frozen rrv_ formula for the bound report_id/"
                "report_content_digest"
            )

        if not self._verification_pass_path(expected_revision_id).exists():
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: no durable verification-pass "
                f"attestation exists for report_revision_id={expected_revision_id!r}"
            )

    def _assert_fresh_write_is_grounded(self, record: Mapping[str, Any]) -> None:
        """Re-verify a NEW record against the CURRENT resolvable state.

        Closes a public-entry-point gap surfaced by RPC-3.3's adversarial
        pass over AC RPC-3: :meth:`publish` previously trusted ANY
        schema-shaped record it was handed, including one hand-crafted with
        the public :func:`build_report_ref`/:func:`build_cited_ref` helpers
        plus an INVENTED ``rights_snapshot`` never derived from a real
        record -- directly contradicting this module's own stated trust
        model (module docstring: "this module NEVER accepts an arbitrary
        caller-supplied ``rights_snapshot`` for construction") which was,
        in practice, only enforced inside
        :meth:`prepare_report_assertion_use`, not at the actual write
        boundary. The same gap also covers a genuinely stale record whose
        backing ``source_assertion`` changed between an earlier
        ``prepare_report_assertion_use`` call and this ``publish`` call
        (freeze doc §13.5's replay/conflict rules describe per-ref
        staleness as a resolution-time concern; this closes the residual
        window between resolution and write for the two-call public API).

        This is checked ONLY for a genuinely new ``use_id`` -- never for
        the replay/conflict branch above, which already compares the
        candidate against the immutable file on disk. Re-running the exact
        same resolution :meth:`prepare_report_assertion_use` already ran
        must reproduce this record's exact ``cited_ref`` and
        ``rights_snapshot``, or the write is refused: fail closed, never a
        torn/mixed record that mixes the record's claimed identity with a
        different current truth.
        """

        cited_ref = record.get("cited_ref")
        if not isinstance(cited_ref, Mapping):
            raise ReportAssertionUseError("record is missing cited_ref")
        ref_kind = cited_ref.get("ref_kind")
        if ref_kind != "source_assertion":
            # No resolver exists yet in this tree for inference/
            # canonical_claim (module docstring) -- there is no real
            # backing record to re-verify a fresh write against, so
            # publishing one is refused rather than trusting an
            # unverifiable rights_snapshot claim.
            raise ReportAssertionUseError(
                f"cannot publish report_assertion_use: ref_kind={ref_kind!r} is not "
                "independently re-verifiable at publish time"
            )

        assertion_id = cited_ref.get("assertion_id")
        assertion_version = cited_ref.get("assertion_version")
        if not isinstance(assertion_id, str) or not isinstance(assertion_version, int):
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: cited_ref is missing "
                "assertion_id/assertion_version"
            )

        fresh = self._resolve_source_assertion(assertion_id, assertion_version)
        if (
            fresh.status != "resolved"
            or fresh.cited_ref != dict(cited_ref)
            or normalize_rights_snapshot(fresh.rights_summary) != record.get("rights_snapshot")
        ):
            raise ReportAssertionUseError(
                "cannot publish report_assertion_use: record no longer matches the "
                "current resolvable state (stale or forged cited_ref/rights_snapshot)"
            )

    def _append_manifest_entry(self, record: Mapping[str, Any]) -> None:
        """Append this record's identity to its report revision's manifest.

        A lighter-weight analogue of freeze doc §17.7a's generation-manifest
        tamper-evidence root, sized to a non-versioned, already
        content-addressed entity: since ``use_id`` itself is the record's own
        fingerprint (unlike a versioned ``inference_record``/
        ``canonical_claim``, whose OPTIONAL ``version_digest`` needs an
        external root to catch a stripped-digest forgery), this manifest's
        purpose is discoverability/audit -- "which uses were published for
        this report revision" -- not tamper-evidence the record's own
        content-derived id does not already provide. Idempotent: appending
        the same ``use_id`` twice is a no-op.
        """

        report_ref = record.get("report_ref")
        report_revision_id = (
            report_ref.get("report_revision_id") if isinstance(report_ref, Mapping) else None
        )
        if not isinstance(report_revision_id, str) or not report_revision_id:
            return
        if not _REPORT_REVISION_ID_RE.fullmatch(report_revision_id):
            return

        use_id = record.get("use_id")
        identity = record.get("identity")
        fingerprint = identity.get("fingerprint") if isinstance(identity, Mapping) else None
        new_entry = {
            "use_id": use_id,
            "fingerprint": fingerprint,
            "cited_ref": record.get("cited_ref"),
            "published_at": record.get("created_at"),
        }

        # T3-5: serialize the read-modify-write under this revision's shared
        # lock -- two concurrent publishes for the SAME report_revision_id
        # (e.g. two claims resolving to two different cited_refs) must never
        # race each other's read of the manifest and silently drop one
        # entry.
        with self._revision_lock(report_revision_id):
            manifest_path = self._manifest_path(report_revision_id)
            existing = load_yaml(manifest_path) if manifest_path.exists() else None
            entries = existing.get("entries") if isinstance(existing, dict) else None
            entries = list(entries) if isinstance(entries, list) else []

            if any(isinstance(e, dict) and e.get("use_id") == use_id for e in entries):
                return

            entries.append(new_entry)
            manifest = {
                "schema_version": "1.0",
                "type": "report_assertion_use_generation_manifest",
                "report_revision_id": report_revision_id,
                "entries": entries,
            }
            _atomic_dump_yaml(manifest, manifest_path)

    def _resolve_verification_pass_created_at(self, report_revision_id: str, candidate: str) -> str:
        """Idempotency anchor WRITER for §13.1/§13.5's deterministic
        ``created_at`` (K-FINAL-1/SOL-35: the ONLY method in this module
        permitted to durably WRITE a verification-pass anchor).

        K-FINAL-1 (CRITICAL, empirically demonstrated): this method is
        module/class-PRIVATE (leading underscore) and is reachable ONLY from
        the module-private :func:`_record_verification_pass`, itself
        reachable ONLY via the public, digest-verifying
        :func:`attest_verification_pass`, invoked EXCLUSIVELY from
        ``verification.py``'s own call site, AFTER ``verify_report`` has
        already decided ``passed=True`` for the exact ``report_content_digest``
        supplied. Before this closure, the method was named
        ``resolve_verification_pass_created_at`` with NO leading underscore
        -- a plain public method on this service class, reachable by any
        caller holding a ``ReportAssertionUseService`` instance. A two-call
        attack script confirmed this: constructing the service directly,
        calling the (then-public) method with a forged
        ``report_content_digest`` no report body was ever read against, then
        calling :func:`publish_report_assertion_uses_for_report` succeeded
        end-to-end -- self-issuing the very attestation the publish path
        later trusted, with the report's actual bytes never read once. The
        leading-underscore rename closes that path: it is no longer callable
        as public API, only from the one production call chain named above.
        It is NOT called from
        :func:`publish_report_assertion_uses_for_report`, which only CONSUMES
        an already-written anchor via the read-only
        :meth:`require_verification_pass_created_at` and denies the whole
        batch when one is absent -- it can no longer create one.

        The FIRST call for a given ``report_revision_id`` durably records
        ``candidate`` (the caller's wall-clock verification-pass instant) as
        that revision's ``created_at``; every subsequent call for the SAME
        ``report_revision_id`` (a retry, or re-verifying an unedited body)
        returns the SAME already-recorded value, never a fresh wall-clock
        stamp -- this is what makes replay converge on the identical
        ``use_id`` (freeze doc §13.5's round-2 fix) without requiring
        ``verification.py`` itself to change its own timestamp semantics.

        Write-once + race-safe (T3-2): the create-if-absent-then-read
        sequence runs under this revision's ``flock`` (:meth:`_revision_lock`)
        AND uses ``O_CREAT|O_EXCL`` for the create itself, so two genuinely
        concurrent first callers can no longer observe or return two
        different anchors for the same revision -- exactly one of them wins
        the create, and BOTH converge on reading back whichever value that
        winner wrote. The stored anchor's schema/type/``report_revision_id``
        are validated on every read; a corrupted or wrong-revision anchor is
        an integrity error (raised), never silently accepted or replaced.
        """

        # _verification_pass_path validates the id shape (raises if not
        # ``rrv_`` + 64 hex) before any path is built from it.
        path = self._verification_pass_path(report_revision_id)
        with self._revision_lock(report_revision_id):
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except FileExistsError:
                    pass  # lost a benign race with a non-flock-aware writer -- fall through to read
                else:
                    from ..yamlio import dumps_yaml

                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        handle.write(
                            dumps_yaml(
                                {
                                    "schema_version": "1.0",
                                    "type": "report_assertion_use_verification_pass",
                                    "report_revision_id": report_revision_id,
                                    "created_at": candidate,
                                }
                            )
                        )
                        handle.flush()
                        os.fsync(handle.fileno())

            existing = load_yaml(path)
            if (
                not isinstance(existing, dict)
                or existing.get("schema_version") != "1.0"
                or existing.get("type") != "report_assertion_use_verification_pass"
                or existing.get("report_revision_id") != report_revision_id
            ):
                raise ReportAssertionUseError(
                    "verification_pass_anchor_invalid: stored anchor for "
                    f"report_revision_id={report_revision_id!r} failed schema/revision "
                    "validation (corrupted or tampered)"
                )
            created_at = existing.get("created_at")
            if not isinstance(created_at, str) or not created_at:
                raise ReportAssertionUseError(
                    "verification_pass_anchor_invalid: stored anchor for "
                    f"report_revision_id={report_revision_id!r} is missing created_at"
                )
            return created_at

    def require_verification_pass_created_at(self, report_revision_id: str) -> str:
        """Idempotency anchor READER (SOL-35/K-FINAL-1): the read-only
        counterpart to the private :meth:`_resolve_verification_pass_created_at`.

        NEVER creates the anchor. A missing verification-pass anchor for
        this exact ``report_revision_id`` raises
        :class:`ReportAssertionUseError` rather than being silently minted
        from the caller's own say-so. This is the ONLY entry point
        :func:`publish_report_assertion_uses_for_report` uses to obtain the
        ``created_at`` it needs -- only the real verification call path
        (:func:`attest_verification_pass`, invoked from
        ``verification.py::verify_report`` after its own pass decision) may
        WRITE this anchor.
        """

        # _verification_pass_path validates the id shape (raises if not
        # ``rrv_`` + 64 hex) before any path is built from it.
        path = self._verification_pass_path(report_revision_id)
        with self._revision_lock(report_revision_id):
            if not path.exists():
                raise ReportAssertionUseError(
                    "verification_pass_missing: no durable verification-pass attestation "
                    f"exists for report_revision_id={report_revision_id!r} (publication only "
                    "consumes an anchor written by the real verification call path, it never "
                    "creates one)"
                )
            existing = load_yaml(path)
            if (
                not isinstance(existing, dict)
                or existing.get("schema_version") != "1.0"
                or existing.get("type") != "report_assertion_use_verification_pass"
                or existing.get("report_revision_id") != report_revision_id
            ):
                raise ReportAssertionUseError(
                    "verification_pass_anchor_invalid: stored anchor for "
                    f"report_revision_id={report_revision_id!r} failed schema/revision "
                    "validation (corrupted or tampered)"
                )
            created_at = existing.get("created_at")
            if not isinstance(created_at, str) or not created_at:
                raise ReportAssertionUseError(
                    "verification_pass_anchor_invalid: stored anchor for "
                    f"report_revision_id={report_revision_id!r} is missing created_at"
                )
            return created_at

    def record_publication_outcome(
        self,
        report_revision_id: str,
        *,
        status: str,
        reason: str | None = None,
        published: Sequence[str] = (),
        skipped: Sequence[Mapping[str, Any]] = (),
        generated_at: str | None = None,
    ) -> None:
        """Persist a per-revision publication-outcome marker (T3-5).

        ``publish_report_assertion_uses_for_report`` swallows every
        exception it lets escape into ``verification.py``'s own broad
        ``except Exception: pass`` (verdict compatibility is preserved --
        report-use publication must never change ``verify_report``'s
        pass/fail decision). That means a partial/failed finalization was
        previously completely invisible: no manifest entry, no error, no
        signal a retry is even needed. This marker makes that outcome
        durable and inspectable -- including the "pass, but zero uses
        published" case, which is a legitimate, auditable outcome, not a
        silent gap. Overwritten on every call for the SAME revision (a
        retry's outcome supersedes the prior attempt's, matching this
        module's existing publish-is-idempotent posture); serialized under
        the same per-revision lock the manifest append uses so a concurrent
        reader never observes a torn write.
        """

        with self._revision_lock(report_revision_id):
            path = self._publication_outcome_path(report_revision_id)
            payload = {
                "schema_version": "1.0",
                "type": "report_assertion_use_publication_outcome",
                "report_revision_id": report_revision_id,
                "status": status,
                "reason": reason,
                "published": list(published),
                "skipped": [dict(item) for item in skipped],
                "generated_at": generated_at,
            }
            _atomic_dump_yaml(payload, path)

    def load_manifest(self, report_revision_id: str) -> dict[str, Any]:
        """Read back the published-use manifest for one report revision.

        Returns an empty ``entries: []`` shape when nothing has been
        published for this revision yet (never raises for absence).
        """

        manifest_path = self._manifest_path(report_revision_id)
        if not manifest_path.exists():
            return {
                "schema_version": "1.0",
                "type": "report_assertion_use_generation_manifest",
                "report_revision_id": report_revision_id,
                "entries": [],
            }
        data = load_yaml(manifest_path)
        return data if isinstance(data, dict) else {
            "schema_version": "1.0",
            "type": "report_assertion_use_generation_manifest",
            "report_revision_id": report_revision_id,
            "entries": [],
        }


# --- Top-level verification-finalization entry point (RPC-3.2) -------------


def _current_report_body_digest(report_path: Path) -> str | None:
    """Re-read ``report_path`` from disk RIGHT NOW and return its exact
    content digest, or ``None`` when it cannot be read (never raises).

    Used exclusively for the T3-4 verify->publish TOCTOU close -- this is a
    read-only probe of the file's CURRENT bytes, never a re-verification and
    never something that changes ``verify_report``'s own pass/fail decision.
    """

    try:
        _, current_body = load_md(report_path)
    except Exception:  # noqa: BLE001 - unreadable now is treated as "cannot compare", not an error
        return None
    return _digest(current_body)


@dataclass(frozen=True)
class _VerificationAttestation:
    """Module-private capability token (SOL-35 REOPENED closure): the ONLY
    argument type :func:`_record_verification_pass` accepts as proof its
    caller is entitled to durably write an attestation.

    Constructed EXCLUSIVELY inside :func:`attest_verification_pass`, and
    only AFTER that function has independently re-read ``report_path`` from
    disk and confirmed the caller-supplied ``report_content_digest``
    matches those bytes RIGHT NOW. Before this token existed,
    ``record_verification_pass`` was a plain public function: any
    in-process caller could invoke it directly with an arbitrary,
    unverified ``report_content_digest`` and mint a durable "verification
    passed" anchor for a report body it had never actually read (the SOL-35
    reopened finding -- a test in this module's own suite did exactly
    that). Requiring this token means a caller must first prove possession
    of the real current report bytes; a bare docstring convention no longer
    does the enforcing.
    """

    __slots__ = ()


def _record_verification_pass(
    _attestation: _VerificationAttestation,
    *,
    workspace_id: str | None,
    report_id: str,
    report_content_digest: str,
    verified_at: str,
    paths: FoundryPaths | None = None,
) -> str:
    """Module-private WRITER of a durable verification-pass attestation.

    Reachable EXCLUSIVELY via :func:`attest_verification_pass`, which is
    the only code in this module able to construct the
    ``_VerificationAttestation`` token this function requires. Never call
    this directly and never re-export it -- see the module-private ``_``
    prefix and the token gate immediately below.

    Returns the durable, idempotent ``created_at`` recorded for this
    ``report_revision_id`` -- the FIRST caller's ``verified_at`` wins; every
    subsequent call for the same revision (a retry, or re-verifying an
    unedited body) returns that SAME value, never a fresh wall-clock stamp
    (freeze doc §13.1/§13.5).

    Workspace resolution reuses :func:`~.assertion_workspace.resolve_or_deny`
    (standing directive 2) -- an absent/blank ``workspace_id`` raises
    :class:`ReportAssertionUseError` rather than writing an anchor under an
    unverified workspace context.
    """

    if not isinstance(_attestation, _VerificationAttestation):
        raise ReportAssertionUseError(
            "cannot record verification pass: no genuine "
            "_VerificationAttestation token supplied (only "
            "attest_verification_pass may construct one)"
        )
    resolution = resolve_or_deny(workspace_id)
    if not resolution.allowed or resolution.workspace_id is None:
        raise ReportAssertionUseError(
            "cannot record verification pass: workspace resolution denied"
        )
    report_ref = build_report_ref(report_id=report_id, report_content_digest=report_content_digest)
    report_revision_id = report_ref["report_revision_id"]
    service = ReportAssertionUseService(workspace_id=resolution.workspace_id, paths=paths)
    return service._resolve_verification_pass_created_at(report_revision_id, verified_at)


def attest_verification_pass(
    *,
    workspace_id: str | None,
    report_id: str,
    report_content_digest: str,
    verified_at: str,
    report_path: Path,
    paths: FoundryPaths | None = None,
) -> str:
    """The ONE public entry point permitted to durably WRITE a
    verification-pass attestation (SOL-35 REOPENED closure).

    Reachable in practice EXCLUSIVELY from ``verification.py``'s own call
    site, AFTER ``verify_report`` has already decided ``passed=True`` for
    the exact ``report_content_digest`` supplied -- never from
    :func:`publish_report_assertion_uses_for_report`, which only CONSUMES an
    already-written anchor (via
    :meth:`ReportAssertionUseService.require_verification_pass_created_at`)
    and denies the whole batch when one is absent.

    Unlike the prior (now module-private) writer, this function does not
    trust ``report_content_digest`` on the caller's say-so alone: it
    re-reads ``report_path`` from disk RIGHT NOW, recomputes that body's
    digest with the exact formula ``verify_report`` uses
    (``sha256(body.encode("utf-8")).hexdigest()``, matching :func:`_digest`),
    and REFUSES -- raising :class:`ReportAssertionUseError` -- when the two
    disagree or when the report cannot currently be read. A caller must
    therefore possess the TRUE current report body bytes, not merely
    assert an arbitrary digest value, to mint a durable attestation. This
    is what closes the self-attestation gap: it is no longer merely
    impossible-by-convention for a caller to invoke the publish function
    directly, bypassing real verification, and have it self-issue the very
    attestation it would otherwise trust -- it is impossible without also
    possessing (or forging on disk) the exact report bytes that hash to the
    claimed digest.

    HONEST, BOUNDED limitation (freeze doc §22b/§22c): an in-process caller
    that already has filesystem write access to this workspace's storage
    root can always write an anchor file directly, or place a forged report
    body at some path before calling this function -- the trust boundary
    this guard enforces is the process/module API, not the filesystem
    itself (the same boundary the manifest's own append-only guarantee
    already accepts). This function's concrete guarantee is narrower: no
    caller reaching it through the public API can mint an attestation for
    report bytes it has never actually read.

    Returns the durable, idempotent ``created_at`` recorded for this
    ``report_revision_id`` (see :func:`_record_verification_pass`).
    """

    try:
        _, current_body = load_md(report_path)
    except Exception as exc:  # noqa: BLE001 - unreadable now is a hard refusal here,
        # never a silent fallthrough -- attestation requires proof of
        # possession of the actual current report body.
        raise ReportAssertionUseError(
            "cannot attest verification pass: report_path "
            f"{report_path!s} is unreadable ({exc.__class__.__name__}) -- "
            "attestation requires proof of possession of the actual "
            "current report body"
        ) from exc
    current_digest = _digest(current_body)
    if current_digest != report_content_digest:
        raise ReportAssertionUseError(
            "cannot attest verification pass: recomputed digest of "
            f"report_path {report_path!s} does not match the supplied "
            "report_content_digest -- refusing to mint an attestation "
            "unbound to the actual current report body"
        )
    return _record_verification_pass(
        _VerificationAttestation(),
        workspace_id=workspace_id,
        report_id=report_id,
        report_content_digest=report_content_digest,
        verified_at=verified_at,
        paths=paths,
    )


def publish_report_assertion_uses_for_report(
    *,
    workspace_id: str | None,
    report_id: str,
    report_content_digest: str,
    verification_passed_at: str,
    claims: Sequence[Mapping[str, Any]],
    paths: FoundryPaths | None = None,
    report_path: Path | None = None,
) -> ReportAssertionUseBatchResult:
    """Publish every resolvable cited-claim's ``report_assertion_use`` record.

    Callers (``verification.py``) MUST only invoke this after
    ``verify_report`` returns ``passed=True`` AND after calling
    :func:`attest_verification_pass` for the exact same
    ``report_content_digest`` -- publication gates on verification
    (RPC-OQ-2, §13.2). ``report_content_digest`` MUST be the SHA-256 of the
    exact report body bytes that verification just ran against, computed in
    the same call as the pass decision, before any other write could change
    the file.

    SOL-35 (CRITICAL, reopened and re-closed) attestation architecture: this
    function NEVER writes the verification-pass anchor itself -- it only
    CONSUMES one, via the read-only
    :meth:`ReportAssertionUseService.require_verification_pass_created_at`.
    A caller invoking this function directly, bypassing ``verify_report``
    and :func:`attest_verification_pass` entirely, gets a fail-closed
    ``status="denied"``/``reason="verification_pass_missing"`` result with
    zero records published -- it can no longer self-issue the very
    attestation it would otherwise trust.

    ``report_path``, when supplied, closes the residual verify->publish
    TOCTOU window (T3-4, freeze doc §13.5): the report file is re-read RIGHT
    NOW, immediately before any report-use write, and its CURRENT digest is
    compared against ``report_content_digest``. A mismatch OR an unreadable/
    deleted report -- SOL-35: an unreadable report is now ALSO a denial,
    never the prior fail-open behavior where "cannot even compare" silently
    proceeded to publish -- means publication is skipped entirely (zero
    records written, the ``verify_report`` verdict itself is untouched)
    rather than publishing a use bound to a body nobody just verified.
    Omitting ``report_path`` (the default) preserves this function's
    pre-T3-4 behavior for callers that have no live file to re-read (e.g.
    tests constructing a batch directly from an in-memory digest).

    ``verification_passed_at`` doubles as the ``generated_at`` on this
    call's publication-outcome marker (T3-5); the ``created_at`` actually
    used for each published record instead comes from the durable
    verification-pass anchor :func:`attest_verification_pass` already wrote
    (freeze doc §13.1/§13.5, SOL-1/22 round 2) -- never a fresh value this
    function itself computes or mints.

    ``claims`` is the set of claim-ledger rows the report body actually
    cites for this revision (one ``report_assertion_use`` per resolvable
    cited persistent reference, never one aggregate record, per §13.1).

    Workspace resolution reuses :func:`~.assertion_workspace.resolve_or_deny`
    (findings doc standing directive 2) -- an absent/blank ``workspace_id``
    fails the WHOLE batch closed (``status="denied"``), publishing zero
    records, rather than partially publishing under an unverified workspace
    context.

    T3-5: this call's outcome (``completed``, ``denied`` for a digest
    mismatch/unreadable report/missing attestation, or ``failed`` when an
    exception propagates out of the publish loop) is durably recorded via
    :meth:`ReportAssertionUseService.record_publication_outcome` before
    returning/re-raising -- including the legitimate "pass, but zero uses
    published" case. This is what makes a report-use publication failure
    that ``verification.py``'s own broad exception handler swallows visible
    and retryable rather than silent.
    """

    resolution = resolve_or_deny(workspace_id)
    if not resolution.allowed:
        return ReportAssertionUseBatchResult(status="denied", reason=resolution.reason)

    assert resolution.workspace_id is not None  # narrows for type-checkers
    report_ref = build_report_ref(
        report_id=report_id,
        report_content_digest=report_content_digest,
    )
    report_revision_id = report_ref["report_revision_id"]
    service = ReportAssertionUseService(workspace_id=resolution.workspace_id, paths=paths)

    if report_path is not None:
        current_digest = _current_report_body_digest(report_path)
        # SOL-35 TOCTOU fail-open close: an unreadable/deleted report
        # (``current_digest is None``) previously fell through this check
        # entirely and proceeded to publish -- "cannot compare" is NOT the
        # same fact as "matches", and must deny the whole batch exactly like
        # a genuine mismatch does, never silently proceed on ``None``.
        toctou_denial_reason: str | None = None
        toctou_outcome_status: str = ""
        if current_digest is None:
            toctou_denial_reason = "report_body_unreadable_since_verification"
            toctou_outcome_status = "skipped_unreadable"
        elif current_digest != report_content_digest:
            toctou_denial_reason = "report_body_changed_since_verification"
            toctou_outcome_status = "skipped_digest_mismatch"
        if toctou_denial_reason is not None:
            try:
                service.record_publication_outcome(
                    report_revision_id,
                    status=toctou_outcome_status,
                    reason=toctou_denial_reason,
                    generated_at=verification_passed_at,
                )
            except Exception:  # noqa: BLE001 - the marker itself must never mask this skip
                pass
            return ReportAssertionUseBatchResult(status="denied", reason=toctou_denial_reason)

    # SOL-35: consume-only. This function has never been permitted to WRITE
    # a verification-pass anchor since this fix -- a caller reaching this
    # point without a real, prior `attest_verification_pass` call for the
    # exact same report_revision_id gets a fail-closed denial, the whole
    # batch skipped, rather than this call minting its own attestation from
    # nothing but its own say-so.
    try:
        created_at = service.require_verification_pass_created_at(report_revision_id)
    except ReportAssertionUseError:
        try:
            service.record_publication_outcome(
                report_revision_id,
                status="denied",
                reason="verification_pass_missing",
                generated_at=verification_passed_at,
            )
        except Exception:  # noqa: BLE001 - the marker itself must never mask this denial
            pass
        return ReportAssertionUseBatchResult(status="denied", reason="verification_pass_missing")

    published: list[str] = []
    skipped: list[SkippedClaim] = []
    outcome_status = "completed"
    outcome_reason: str | None = None
    try:
        for claim in claims:
            if not isinstance(claim, Mapping):
                continue
            claim_id = claim.get("claim_id")
            persistent_references = claim.get("persistent_references")
            outcome = service.prepare_report_assertion_use(
                report_ref=report_ref,
                persistent_references=persistent_references,
                created_at=created_at,
            )
            if outcome.status != "prepared" or outcome.record is None:
                skipped.append(
                    SkippedClaim(claim_id=claim_id, status=outcome.status, reason=outcome.reason)
                )
                continue
            _publish_status, published_record = service.publish(outcome.record)
            published.append(published_record["use_id"])
    except Exception as exc:  # noqa: BLE001 - record, then re-raise for the caller's own handling
        outcome_status = "failed"
        outcome_reason = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        try:
            service.record_publication_outcome(
                report_revision_id,
                status=outcome_status,
                reason=outcome_reason,
                published=published,
                skipped=[
                    {"claim_id": s.claim_id, "status": s.status, "reason": s.reason}
                    for s in skipped
                ],
                generated_at=verification_passed_at,
            )
        except Exception:  # noqa: BLE001 - the marker itself must never mask the real outcome
            pass

    return ReportAssertionUseBatchResult(
        status="completed",
        reason=None,
        published=tuple(published),
        skipped=tuple(skipped),
    )


__all__ = [
    "REPORT_ASSERTION_USE_IDENTITY_ALGORITHM",
    "REPORT_ASSERTION_USE_MATERIAL_FIELDS",
    "PersistentRefResolution",
    "PrepareOutcome",
    "ReportAssertionUseBatchResult",
    "ReportAssertionUseConflict",
    "ReportAssertionUseError",
    "ReportAssertionUseService",
    "SkippedClaim",
    "assert_rights_snapshot_not_promoted",
    "build_cited_ref",
    "build_report_ref",
    "canonical_report_assertion_use_json",
    "canonical_report_assertion_use_payload",
    "fold_rights_snapshots_most_restrictive",
    "normalize_rights_snapshot",
    "publish_report_assertion_uses_for_report",
    "report_assertion_use_fingerprint",
    "report_assertion_use_id",
    "report_revision_id_for_run_report",
]
