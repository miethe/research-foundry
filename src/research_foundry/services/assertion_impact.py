"""Idempotent, resumable lifecycle impact reconciliation.

An authoritative lifecycle block must already have been persisted before this
module receives a dependency list.  The returned receipt is pure data so a
worker can persist it, stop at any action, and resume without duplicating work.
Real downstream writebacks are never invoked here: their action is explicitly
queued as default-denied evidence for a separately authorized adapter.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from yaml import YAMLError

from ..api.auth.provider import AuthIdentity
from ..paths import FoundryPaths
from ..schemas import SchemaRegistry
from ..yamlio import dumps_yaml, load_yaml
from .assertion_catalog import AssertionCatalog, AssertionCatalogDenied, AssertionCatalogError
from .assertion_materialization import _referenced_target_ids
from .assertion_registry import AssertionRegistry, RegistryIntegrityError
from .assertion_reuse import block_authoritative_reuse

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_INFERENCE_ID_RE = re.compile(r"^inf_[a-f0-9]{64}$")
_CANONICAL_CLAIM_ID_RE = re.compile(r"^ccl_[a-f0-9]{64}$")
_REPORT_USE_ID_RE = re.compile(r"^rau_[a-f0-9]{64}$")

@dataclass(frozen=True)
class ImpactAction:
    """One deterministically-addressed reconciliation action."""

    object_id: str
    object_class: str
    action: str
    status: str = "pending"


@dataclass(frozen=True)
class ImpactReceipt:
    """A stable, resumable receipt for one lifecycle event."""

    event_id: str
    assertion_id: str
    status: str
    actions: tuple[ImpactAction, ...]


_ACTIONS = {
    "source_edition": "block_reuse",
    "passage": "block_reuse",
    "assertion_version": "block_reuse",
    "canonical_claim_edge": "mark_stale",
    "inference": "mark_stale",
    "report_revision": "mark_stale",
    "run": "mark_stale",
    "export": "mark_stale",
    "derived_cache_or_index": "purge_current_read",
    "assertion_regeneration": "regenerate",
    "mock_writeback_receipt": "queue_default_denied_reconciliation",
}

# These are the only reason codes written into a durable blocked receipt by
# ``_new_receipt``.  Keep the read seam closed over the writer's vocabulary so
# arbitrary receipt content cannot be reflected through the API.
_BLOCKED_RECEIPT_REASON_CODES = frozenset(
    {
        "dependency_manifest_missing",
        "dependency_manifest_invalid",
        # RPC-6.3: raised by the manifest-authoring merge seam
        # (``_merge_canonical_dependents_into_manifest``) when a canonical
        # dependent shares an (object_id, object_class) key with a
        # pre-existing manifest entry that does not match it byte-for-byte.
        "dependency_manifest_conflict",
        # SOL-40 (HIGH, gate-blocking): ``reconcile()`` itself persists this
        # when the unconditional per-call derived-cache purge
        # (``purge_lifecycle_derived_file``) raises ``OSError`` -- a failed
        # purge must fail reconciliation closed and durably record why,
        # exactly like the manifest failures above, rather than silently
        # letting reconciliation "complete" while a stale catalog
        # projection is left behind.
        "derived_cache_purge_failed",
    }
)

# ``default_denied`` is the status emitted by the current mock writeback
# writer.  The other values are retained receipt vocabulary for authorized
# writeback adapters; all are deliberately separate from action progress.
_WRITEBACK_STATUSES = frozenset({"default_denied", "denied", "queued"})


class ImpactOperationError(ValueError):
    """A persisted lifecycle operation cannot safely continue."""


class ImpactInterrupted(RuntimeError):
    """Test-only interruption after a durable action checkpoint."""


class AssertionImpactReadDenied(ValueError):
    """A safe, typed reason why an impact receipt cannot be read."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ReconciliationResult:
    """Persisted lifecycle-operation outcome, safe to return to a worker."""

    event_id: str
    assertion_id: str
    status: str
    receipt_path: Path
    action_count: int


class AssertionImpactReader:
    """Read one policy-authorized, workspace-local impact receipt.

    The reader intentionally treats unavailable, malformed, interrupted, and
    cross-workspace receipt state as the same absence.  It never falls back to
    scanning another workspace or reconstructing dependencies from ledger
    relationships, so callers cannot use the endpoint as a membership oracle.
    """

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self.paths = paths or FoundryPaths.discover()
        self.catalog = AssertionCatalog(self.paths)

    def summary(self, assertion_id: str, *, identity: AuthIdentity | None) -> dict[str, Any] | None:
        """Return an authorized receipt summary, or ``None`` without hints.

        ``None`` deliberately covers an absent assertion, absent receipt,
        malformed artifacts, and a receipt owned by another workspace.  A
        caller lacking workspace context or rights receives a typed denial.
        """

        workspace_id = getattr(identity, "workspace_id", None)
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise AssertionImpactReadDenied("workspace_context_missing")
        if not isinstance(assertion_id, str) or not _TOKEN_RE.fullmatch(assertion_id):
            return None

        try:
            packet = self.catalog.packet(assertion_id, identity=identity)
        except AssertionCatalogDenied as exc:
            raise AssertionImpactReadDenied(exc.reason_code) from exc
        except AssertionCatalogError:
            return None
        if packet is None:
            return None

        try:
            registry = AssertionRegistry(workspace_id=workspace_id, paths=self.paths)
            policy = self._mapping(
                registry,
                registry.root / "lifecycle_policy" / f"{assertion_id}.yaml",
            )
            if not self._valid_policy(policy, assertion_id):
                return None
            event_id = policy["invalidation_event_id"]
            assert isinstance(event_id, str)
            receipt = AssertionImpactReconciler(
                workspace_id=workspace_id,
                paths=self.paths,
            ).validated_receipt(
                assertion_id=assertion_id,
                event_id=event_id,
            )
            if receipt is None:
                return None
            status = receipt["status"]
            assert isinstance(status, str)
            actions = receipt["actions"]
            assert isinstance(actions, list)
            reason_code = receipt.get("reason_code")
            projected_actions: list[dict[str, str]] = []
            for action in actions:
                projected_action = {
                    "object_id": action["object_id"],
                    "object_class": action["object_class"],
                    "action": action["action"],
                    "status": action["status"],
                }
                if "writeback_status" in action:
                    projected_action["writeback_status"] = action["writeback_status"]
                projected_actions.append(projected_action)

            return {
                "event_id": event_id,
                "assertion_id": assertion_id,
                "lifecycle_state": policy["lifecycle_state"],
                "access_scope": packet["access_scope"],
                "authoritative_reuse_blocked": True,
                "operation_status": status,
                "reason_code": reason_code if isinstance(reason_code, str) else None,
                # P5 receipts do not carry an independently authorized edition
                # target.  Do not surface a future extension until its target has
                # its own governed read check.
                "replacement_edition_id": None,
                "resumable": status == "pending",
                "actions": projected_actions,
            }
        except (ImpactOperationError, FileNotFoundError, OSError, RegistryIntegrityError, ValueError, YAMLError):
            return None
        except Exception:
            # A receipt is an untrusted persisted boundary.  Do not let an
            # unexpected projection or validation failure become a 500 or
            # distinguish malformed state from absence.
            return None

    @staticmethod
    def _mapping(registry: AssertionRegistry, path: Path) -> dict[str, Any]:
        """Read one in-workspace YAML artifact without following symlinks."""

        value = registry._load_yaml_file(path, path.parent)
        if not isinstance(value, dict):
            raise ValueError("impact_receipt_invalid")
        return value

    @staticmethod
    def _valid_policy(policy: Mapping[str, Any], assertion_id: str) -> bool:
        event_id = policy.get("invalidation_event_id")
        return (
            policy.get("type") == "assertion_lifecycle_policy_state"
            and policy.get("assertion_id") == assertion_id
            and policy.get("invalidation_state") == "blocked"
            and policy.get("lifecycle_state") == "blocked"
            and isinstance(event_id, str)
            and bool(_TOKEN_RE.fullmatch(event_id))
        )

    @staticmethod
    def _valid_active_policy(policy: Mapping[str, Any], assertion_id: str) -> bool:
        """SOL-37 (CRITICAL, PARTIAL closure completed): the exact
        ACTIVE-snapshot counterpart to :meth:`_valid_policy`'s full-shape
        validation for the blocked branch. Previously the active branch
        checked only three fields (``type``/``assertion_id``/
        ``invalidation_state``) -- a one-field tamper on a REAL blocked
        policy (flip ``invalidation_state`` from ``"blocked"`` to
        ``"active"`` while leaving ``lifecycle_state: blocked`` and its real
        ``invalidation_event_id`` intact) passed that loose check and read
        as ``eligible``. This validates the COMPLETE pre-block snapshot
        shape ``_load_policy``'s own no-path-exists branch produces
        (``.assertion_impact.AssertionImpactReconciler._load_policy``):
        ``lifecycle_state`` MUST be one of the two legitimate "from" states
        `block_authoritative_reuse` accepts (never ``"blocked"``), and
        ``invalidation_event_id`` MUST be the literal ``None`` (the
        null-event invariant -- an active/pre-block snapshot never carries a
        real event id). Either half of the tamper alone now fails this
        check.

        SOL-37 PARTIAL closure: the writer's no-path-exists branch always
        also emits ``schema_version: "1.0"`` and the assertion's own
        ``assertion_version`` (a positive, non-bool int), but this check
        previously validated neither field -- a policy tampered to a
        different ``schema_version``, or to a missing/malformed/non-
        positive ``assertion_version``, still passed as a valid active
        snapshot. Both fields are now part of the required shape, exactly
        matching what the writer emits.
        """

        assertion_version = policy.get("assertion_version")
        return (
            policy.get("type") == "assertion_lifecycle_policy_state"
            and policy.get("schema_version") == "1.0"
            and policy.get("assertion_id") == assertion_id
            and policy.get("invalidation_state") == "active"
            and policy.get("lifecycle_state") in ("eligible", "stale")
            and policy.get("invalidation_event_id") is None
            and isinstance(assertion_version, int)
            and not isinstance(assertion_version, bool)
            and assertion_version >= 1
        )

def _atomic_dump(data: Mapping[str, Any], path: Path) -> None:
    """Atomically replace a YAML operation artifact after flushing it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(dumps_yaml(dict(data)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_dump_json(data: Mapping[str, Any], path: Path) -> None:
    """Atomically replace a JSON manifest artifact after flushing it.

    RPC-6.3: the ``impact_manifests/<event_id>.json`` shape is JSON (unlike
    every other durable artifact this module writes), so this mirrors
    :func:`_atomic_dump`'s crash-safe write/fsync/replace sequence rather than
    reusing it directly.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(data), handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class AssertionImpactReconciler:
    """Persist and resume one workspace-local assertion lifecycle operation.

    The authoritative assertion is blocked and atomically written before the
    manifest is read or any derived object is touched.  The receipt is then
    checkpointed after each action, so retrying an interrupted operation never
    repeats a completed cleanup or invokes a real downstream writeback.

    RPC-6.3 lifecycle seam (blocked assertion -> stale dependents): before the
    receipt is first derived, :meth:`_merge_canonical_dependents_into_manifest`
    merges :func:`enumerate_canonical_dependents`'s (RPC-6.1) read of the
    currently-authoritative ``inference_record``/``canonical_claim``/
    ``report_assertion_use`` records into this event's on-disk manifest.
    ``reconcile`` then traverses that manifest exactly as it always has,
    checkpointing a ``mark_stale`` action (contract F13/§17.5 -- the shared
    ``canonical_claim_edge``/``inference``/``report_revision`` object classes,
    never a new schema-widening lifecycle event targeting those record kinds
    directly) per dependent.  The durable, content-addressed
    ``impact_effects/<event_id>/<digest>.yaml`` effect receipt each completed
    action gets IS the staleness propagation mechanism: no inference/
    canonical-claim/report-use record file is ever mutated in place (they
    stay immutable, tamper-evidence-checked durable records per §17.7a); a
    dependent's lane-visible staleness is read back through this reconciler's
    own receipt -- :class:`AssertionImpactReader`, or
    :meth:`validated_receipt` directly -- never through the P5 projection
    catalog.
    """

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        self.root = AssertionRegistry(workspace_id=workspace_id, paths=self.paths).root
        self.schemas = SchemaRegistry(schemas_dir=self.paths.schemas)

    def manifest_path(self, event_id: str) -> Path:
        return self.root / "impact_manifests" / f"{self._token(event_id, 'event_id')}.json"

    def receipt_path(self, event_id: str) -> Path:
        return self.root / "impact_operations" / f"{self._token(event_id, 'event_id')}.yaml"

    def event_path(self, event_id: str) -> Path:
        return self.root / "lifecycle_events" / f"{self._token(event_id, 'event_id')}.yaml"

    def policy_path(self, assertion_id: str) -> Path:
        return self.root / "lifecycle_policy" / f"{self._token(assertion_id, 'assertion_id')}.yaml"

    def reconcile(
        self,
        *,
        assertion_id: str,
        event_id: str,
        _interrupt_after_actions: int | None = None,
    ) -> ReconciliationResult:
        """Block authoritative eligibility, then consume and checkpoint a manifest.

        The dependency graph is loaded only from the workspace's durable
        ``impact_manifests/<event_id>.json`` artifact.  Missing or malformed
        manifests produce a persisted blocked receipt; they never permit a
        partial traversal or a current/reusable assertion.
        """

        assertion_id = self._token(assertion_id, "assertion_id")
        event_id = self._token(event_id, "event_id")
        if _interrupt_after_actions is not None and _interrupt_after_actions < 1:
            raise ValueError("interrupt_after_actions must be positive")
        assertion_path = self.root / "assertions" / f"{assertion_id}.yaml"
        assertion = self._load_mapping(assertion_path, "assertion_missing")
        if not self.schemas.validate(assertion, "source_assertion").ok:
            raise ImpactOperationError("assertion_schema_invalid")
        event = self._load_event(event_id, assertion)
        receipt_path = self.receipt_path(event_id)
        receipt = self._load_receipt(receipt_path, assertion_id, event_id)

        # This write is intentionally before manifest loading and traversal.
        # The immutable source assertion is never overwritten; its separate
        # lifecycle policy state becomes the authoritative reuse boundary.
        policy_path = self.policy_path(assertion_id)
        policy = self._load_policy(policy_path, assertion, event)
        try:
            blocked = block_authoritative_reuse(policy, event_id=event_id)
        except ValueError as exc:
            raise ImpactOperationError(str(exc)) from exc
        if policy != blocked:
            _atomic_dump(blocked, policy_path)
        # SOL-38 (HIGH, gate-blocking): F19's effective-lifecycle boundary
        # must be visible on the VERY NEXT read of this workspace's catalog
        # projection -- an existing projection built before this exact block
        # is now stale display authority for THIS assertion. Invalidated
        # here as part of policy establishment itself -- never merely when
        # this event's OWN manifest happens to also enumerate a
        # `derived_cache_or_index` dependent (`_apply_action` below does
        # that too, but only for objects the manifest actually names; a
        # direct citation check against THIS assertion is not
        # manifest-dependent). The projection is rebuildable by design (this
        # module's own docstring, `assertion_catalog.py`'s own docstring):
        # normal search/packet/lineage callers transparently rebuild on next
        # read (`AssertionCatalog._records`); the C4/Knowledge read-only
        # callers instead surface `AssertionCatalogUnavailable`/
        # `catalog_unavailable` until a fresh rebuild runs
        # (`AssertionCatalog._records_read_only`) -- never silently serve
        # the pre-block projection either way. `AssertionCatalog` is already
        # a module-level import above; `purge_lifecycle_derived_file`
        # mirrors `_apply_action`'s own lazy import of it below.
        #
        # SOL-40 (HIGH, gate-blocking): this purge is now attempted on EVERY
        # `reconcile()` call while the effective policy is blocked -- which,
        # since this method only ever runs for a `block_reuse` event, is
        # unconditionally true past this point -- never only on the ONE
        # call that actually flipped `policy != blocked` above. Previously:
        # the policy was persisted as blocked BEFORE the purge ran, and a
        # purge failure (e.g. a transient `OSError` unlinking the projection
        # file) left the assertion durably blocked on disk while the
        # derived catalog projection silently kept serving stale pre-block
        # content forever -- a RETRY's freshly-reloaded `policy` already
        # equalled `blocked`, so the old `if policy != blocked:` gate
        # skipped the purge attempt entirely and the failure was never
        # revisited. `purge_lifecycle_derived_file` is already idempotent (a
        # no-op returning `False` once the projection file no longer
        # exists), so repeating this call on every already-purged call is
        # always safe. A genuine failure now fails THIS call closed with a
        # durable, typed blocked receipt (mirroring every other durable
        # precondition `_new_receipt` already persists this way) instead of
        # silently letting reconciliation proceed -- the retry path
        # naturally re-attempts the purge because it reaches this same
        # unconditional call again.
        from .catalog_service import purge_lifecycle_derived_file

        try:
            purge_lifecycle_derived_file(
                AssertionCatalog(self.paths).projection_path(self.workspace_id),
                lifecycle_state=blocked.get("lifecycle_state"),
            )
        except OSError:
            purge_failed_receipt = {
                "schema_version": "1.0",
                "type": "assertion_impact_operation",
                "event_id": event_id,
                "assertion_id": assertion_id,
                "status": "blocked",
                "reason_code": "derived_cache_purge_failed",
                "actions": [],
            }
            _atomic_dump(purge_failed_receipt, receipt_path)
            return self._result(purge_failed_receipt, receipt_path)

        # RPC-6.3: (re-)derive the receipt -- which (re-)authors the manifest
        # with RPC-6.1's canonical dependents, see ``_new_receipt`` -- only
        # when there is no committed progress to lose: a fresh event, or a
        # persisted ``blocked`` receipt (``actions`` is always ``[]`` for
        # those, per ``_load_receipt``'s own invariant, so re-deriving never
        # discards a completed/pending action).  This is what makes the
        # RPC-6.4 repair path converge: fixing an invalid/missing manifest out
        # from under a stale ``blocked`` receipt and calling ``reconcile``
        # again re-tries ``_new_receipt`` instead of replaying the same stale
        # block forever.
        if receipt is None or receipt["status"] == "blocked":
            receipt = self._new_receipt(event_id=event_id, assertion_id=assertion_id, blocked=blocked)
            _atomic_dump(receipt, receipt_path)
        if receipt["status"] == "blocked":
            return self._result(receipt, receipt_path)

        processed = 0
        actions = receipt["actions"]
        assert isinstance(actions, list)
        for action in actions:
            if action["status"] == "completed":
                continue
            self._apply_action(action, blocked, event_id)
            action["status"] = "completed"
            processed += 1
            receipt["status"] = "pending"
            _atomic_dump(receipt, receipt_path)
            if _interrupt_after_actions is not None and processed >= _interrupt_after_actions:
                raise ImpactInterrupted("impact_operation_interrupted")
        receipt["status"] = "completed"
        _atomic_dump(receipt, receipt_path)
        return self._result(receipt, receipt_path)

    def _merge_canonical_dependents_into_manifest(
        self, canonical_dependents: list[dict[str, str]], *, event_id: str
    ) -> None:
        """RPC-6.3: the manifest-authoring seam -- merge RPC-6.1's canonical
        dependents into ``impact_manifests/<event_id>.json`` before the
        manifest is read for receipt (re-)derivation.

        No production writer for this manifest existed before this task (the
        legacy ``source_edition``/``passage``/``assertion_version`` propagation
        this reconciler already traverses is authored externally -- by a
        producer outside this repo's scope, exercised in tests only via
        hand-written fixtures/``_persist_impact_inputs``-style helpers).  This
        is now the ONE place :func:`enumerate_canonical_dependents`'s
        read-only output is turned into durable manifest content, so this is
        also the writer any future legacy-propagation producer's output must
        be merged with, never silently replaced.

        Idempotent and additive-only:

        * A pre-existing manifest's entries are preserved.  A canonical
          dependent sharing an ``(object_id, object_class)`` key with an
          existing entry must match it byte-for-byte or the merge fails
          closed (``dependency_manifest_conflict``) -- it never silently
          overwrites a differing entry.
        * No canonical dependents and no pre-existing manifest means nothing
          is written: a lifecycle event with neither a legacy producer's
          manifest nor any canonical dependent still yields the existing
          ``dependency_manifest_missing`` blocked outcome (AC RPC-8), never a
          spurious empty manifest that would flip that outcome to
          "completed, zero actions".

        Both failure modes this raises (``dependency_manifest_invalid`` for a
        malformed pre-existing manifest, ``dependency_manifest_conflict`` for
        a genuine identity clash) are caught by :meth:`_new_receipt`'s own
        ``ImpactOperationError`` handler -- exactly the same graceful
        blocked-receipt path ``_load_manifest``'s own malformed-manifest case
        already uses, never a bare exception out of ``reconcile``.
        """

        if not canonical_dependents:
            return

        path = self.manifest_path(event_id)
        existing: list[Any] = []
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise ImpactOperationError("dependency_manifest_invalid")
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ImpactOperationError("dependency_manifest_invalid") from exc
            raw_objects = raw.get("expected_objects") if isinstance(raw, dict) else None
            if not isinstance(raw_objects, list):
                raise ImpactOperationError("dependency_manifest_invalid")
            existing = raw_objects

        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for item in existing:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("object_id"), str)
                or not item["object_id"]
                or not isinstance(item.get("object_class"), str)
            ):
                raise ImpactOperationError("dependency_manifest_invalid")
            merged[(item["object_id"], item["object_class"])] = item
        for item in canonical_dependents:
            key = (item["object_id"], item["object_class"])
            if key in merged and merged[key] != item:
                raise ImpactOperationError("dependency_manifest_conflict")
            merged[key] = item

        ordered = sorted(merged.values(), key=lambda item: (item["object_class"], item["object_id"]))
        _atomic_dump_json({"expected_objects": ordered}, path)

    def _new_receipt(self, *, event_id: str, assertion_id: str, blocked: Mapping[str, Any]) -> dict[str, Any]:
        # RPC-6.1's own enumeration is called OUTSIDE the ImpactOperationError
        # handler below on purpose: a bad workspace/assertion id or version is
        # a caller/programming error (already schema-guarded upstream in
        # ``reconcile``) and a "canonical_dependents_unavailable" orphaned
        # authority pointer is a genuine store/authority desync -- both hard
        # fail exactly as :func:`enumerate_canonical_dependents` already does
        # when called directly, never a swallowed "blocked" receipt.
        canonical_dependents = enumerate_canonical_dependents(
            paths=self.paths,
            workspace_id=self.workspace_id,
            assertion_id=assertion_id,
            assertion_version=blocked["assertion_version"],
        )
        try:
            self._merge_canonical_dependents_into_manifest(canonical_dependents, event_id=event_id)
            dependencies = self._load_manifest(event_id)
            enumerated = enumerate_impact(event_id=event_id, assertion=blocked, dependencies=dependencies)
        except ImpactOperationError as exc:
            return {
                "schema_version": "1.0",
                "type": "assertion_impact_operation",
                "event_id": event_id,
                "assertion_id": assertion_id,
                "status": "blocked",
                "reason_code": str(exc),
                "actions": [],
            }
        if enumerated.status == "blocked":
            return {
                "schema_version": "1.0",
                "type": "assertion_impact_operation",
                "event_id": event_id,
                "assertion_id": assertion_id,
                "status": "blocked",
                "reason_code": "dependency_graph_unknown",
                "actions": [],
            }
        return {
            "schema_version": "1.0",
            "type": "assertion_impact_operation",
            "event_id": event_id,
            "assertion_id": assertion_id,
            "status": "pending",
            "actions": [
                {
                    "object_id": action.object_id,
                    "object_class": action.object_class,
                    "action": action.action,
                    "status": "pending",
                }
                for action in enumerated.actions
            ],
        }

    def _load_manifest(self, event_id: str) -> list[dict[str, Any]]:
        path = self.manifest_path(event_id)
        if not path.is_file() or path.is_symlink():
            raise ImpactOperationError("dependency_manifest_missing")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImpactOperationError("dependency_manifest_invalid") from exc
        dependencies = value.get("expected_objects") if isinstance(value, dict) else None
        if not isinstance(dependencies, list):
            raise ImpactOperationError("dependency_manifest_invalid")
        normalised: list[dict[str, Any]] = []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                raise ImpactOperationError("dependency_manifest_invalid")
            object_id = dependency.get("object_id")
            object_class = dependency.get("object_class")
            action = dependency.get("action")
            if (
                not isinstance(object_id, str)
                or not object_id
                or not isinstance(object_class, str)
                or _ACTIONS.get(object_class) != action
            ):
                raise ImpactOperationError("dependency_manifest_invalid")
            normalised.append({"object_id": object_id, "object_class": object_class})
        return normalised

    def _load_event(self, event_id: str, assertion: Mapping[str, Any]) -> dict[str, Any]:
        event = self._load_mapping(self.event_path(event_id), "lifecycle_event_missing")
        if not self.schemas.validate(event, "assertion_lifecycle_event").ok:
            raise ImpactOperationError("lifecycle_event_invalid")
        target = event.get("target")
        if (
            event.get("event_id") != event_id
            or not isinstance(target, Mapping)
            or target.get("kind") != "source_assertion"
            or target.get("id") != assertion.get("assertion_id")
            or target.get("version") != assertion.get("assertion_version")
            or event.get("authoritative_action") != "block_reuse"
        ):
            raise ImpactOperationError("lifecycle_event_target_invalid")
        return event

    def _load_policy(
        self, path: Path, assertion: Mapping[str, Any], event: Mapping[str, Any]
    ) -> dict[str, Any]:
        transition = event.get("transition")
        assert isinstance(transition, Mapping)
        if not path.exists():
            if assertion.get("lifecycle_state") != transition.get("from"):
                raise ImpactOperationError("lifecycle_transition_source_mismatch")
            return {
                "schema_version": "1.0",
                "type": "assertion_lifecycle_policy_state",
                "assertion_id": assertion["assertion_id"],
                "assertion_version": assertion["assertion_version"],
                "lifecycle_state": transition["from"],
                "invalidation_state": "active",
                "invalidation_event_id": None,
            }
        policy = self._load_mapping(path, "lifecycle_policy_invalid")
        if (
            policy.get("type") != "assertion_lifecycle_policy_state"
            or policy.get("assertion_id") != assertion.get("assertion_id")
            or policy.get("assertion_version") != assertion.get("assertion_version")
            or policy.get("invalidation_state") not in {"active", "blocked"}
            or (
                policy.get("invalidation_state") == "active"
                and policy.get("lifecycle_state") != transition.get("from")
            )
            or (
                policy.get("invalidation_state") == "blocked"
                and policy.get("lifecycle_state") != "blocked"
            )
        ):
            raise ImpactOperationError("lifecycle_policy_invalid")
        return policy

    def _apply_action(self, action: dict[str, Any], blocked: Mapping[str, Any], event_id: str) -> None:
        object_class = action["object_class"]
        if object_class == "derived_cache_or_index":
            from .assertion_catalog import AssertionCatalog
            from .catalog_service import purge_lifecycle_derived_file

            projection = AssertionCatalog(self.paths).projection_path(self.workspace_id)
            action["derived_cleanup"] = purge_lifecycle_derived_file(projection, lifecycle_state=blocked["lifecycle_state"])
        elif object_class == "export":
            from .export_service import assertion_lifecycle_export_status

            action["export_status"] = assertion_lifecycle_export_status(blocked["lifecycle_state"])
        elif object_class == "run":
            from .run_launch import retrieve_first_reuse_decision

            decision = retrieve_first_reuse_decision(
                {**blocked, "workspace_id": self.workspace_id}, workspace_id=self.workspace_id
            )
            action["reuse_reason"] = decision.reason_code
        elif object_class == "mock_writeback_receipt":
            action["writeback_status"] = "default_denied"
        effect_path = self._effect_path(event_id, action)
        effect = self._effect_record(event_id, action)
        if effect_path.exists():
            if self._load_mapping(effect_path, "impact_effect_invalid") != effect:
                raise ImpactOperationError("impact_effect_conflict")
        else:
            _atomic_dump(effect, effect_path)
        action["effect_receipt"] = str(effect_path.relative_to(self.root))

    def _effect_path(self, event_id: str, action: Mapping[str, Any]) -> Path:
        key = json.dumps(
            {"id": action["object_id"], "class": action["object_class"], "action": action["action"]},
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = sha256(key.encode("utf-8")).hexdigest()
        return self.root / "impact_effects" / event_id / f"{digest}.yaml"

    @staticmethod
    def _effect_record(event_id: str, action: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "type": "assertion_impact_effect",
            "event_id": event_id,
            "object_id": action["object_id"],
            "object_class": action["object_class"],
            "action": action["action"],
            "mode": "mock_file_backed_control_plane",
            "status": "recorded",
        }

    def validated_receipt(
        self,
        *,
        assertion_id: str,
        event_id: str,
    ) -> dict[str, Any] | None:
        """Return a receipt only when it satisfies reconciliation invariants.

        This is intentionally the reader's validation seam as well as the
        reconciler's resume seam.  It verifies the exact manifest action set
        and every completed action's durable effect receipt before either
        caller can trust projected action data.
        """

        return self._load_receipt(self.receipt_path(event_id), assertion_id, event_id)

    def _load_receipt(
        self,
        path: Path,
        assertion_id: str,
        event_id: str,
    ) -> dict[str, Any] | None:
        if not path.exists():
            return None
        receipt = self._load_mapping(path, "impact_receipt_invalid")
        actions = receipt.get("actions")
        if (
            receipt.get("schema_version") != "1.0"
            or receipt.get("type") != "assertion_impact_operation"
            or receipt.get("event_id") != event_id
            or receipt.get("assertion_id") != assertion_id
            or receipt.get("status") not in {"pending", "completed", "blocked"}
            or not isinstance(actions, list)
        ):
            raise ImpactOperationError("impact_receipt_invalid")
        status = receipt["status"]
        reason_code = receipt.get("reason_code")
        if status == "blocked":
            if (
                actions
                or not isinstance(reason_code, str)
                or reason_code not in _BLOCKED_RECEIPT_REASON_CODES
            ):
                raise ImpactOperationError("impact_receipt_invalid")
        elif reason_code is not None:
            raise ImpactOperationError("impact_receipt_invalid")
        for action in actions:
            if (
                not isinstance(action, dict)
                or not isinstance(action.get("object_id"), str)
                or not action["object_id"]
                or not isinstance(action.get("object_class"), str)
                or not isinstance(action.get("action"), str)
                or not isinstance(action.get("status"), str)
                or action["action"] != _ACTIONS.get(action["object_class"])
                or action["status"] not in {"pending", "completed"}
            ):
                raise ImpactOperationError("impact_receipt_invalid")
            writeback_status = action.get("writeback_status")
            if action["object_class"] == "mock_writeback_receipt":
                if action["status"] == "completed" and (
                    not isinstance(writeback_status, str)
                    or writeback_status not in _WRITEBACK_STATUSES
                ):
                    raise ImpactOperationError("impact_receipt_invalid")
                if action["status"] == "pending" and "writeback_status" in action:
                    raise ImpactOperationError("impact_receipt_invalid")
            elif "writeback_status" in action:
                raise ImpactOperationError("impact_receipt_invalid")
        if status == "blocked":
            # Writer-persisted zero-action blocked receipts deliberately
            # record manifest read failures.  Re-reading that unavailable or
            # invalid manifest here would hide the authoritative block.
            return receipt
        actual_identities = [(action["object_id"], action["object_class"], action["action"]) for action in actions]
        expected_identities = [
            (action.object_id, action.object_class, action.action)
            for action in self._manifest_actions(event_id, assertion_id)
        ]
        if actual_identities != expected_identities:
            raise ImpactOperationError("impact_receipt_action_set_invalid")
        seen_pending_action = False
        for action in actions:
            if action["status"] == "pending":
                seen_pending_action = True
                continue
            if seen_pending_action:
                raise ImpactOperationError("impact_receipt_invalid")
            effect_path = self._effect_path(event_id, action)
            if action.get("effect_receipt") != str(effect_path.relative_to(self.root)):
                raise ImpactOperationError("impact_effect_invalid")
            if self._load_mapping(effect_path, "impact_effect_invalid") != self._effect_record(event_id, action):
                raise ImpactOperationError("impact_effect_invalid")
        if status == "completed" and any(action["status"] != "completed" for action in actions):
            raise ImpactOperationError("impact_receipt_invalid")
        return receipt

    def _manifest_actions(self, event_id: str, assertion_id: str) -> tuple[ImpactAction, ...]:
        dependencies = self._load_manifest(event_id)
        receipt = enumerate_impact(
            event_id=event_id,
            assertion={
                "assertion_id": assertion_id,
                "invalidation_state": "blocked",
                "invalidation_event_id": event_id,
            },
            dependencies=dependencies,
        )
        if receipt.status != "pending":
            raise ImpactOperationError("dependency_graph_unknown")
        return receipt.actions

    @staticmethod
    def _load_mapping(path: Path, error: str) -> dict[str, Any]:
        if not path.is_file() or path.is_symlink():
            raise ImpactOperationError(error)
        try:
            value = load_yaml(path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise ImpactOperationError(error) from exc
        if not isinstance(value, dict):
            raise ImpactOperationError(error)
        return value

    @staticmethod
    def _token(value: object, label: str) -> str:
        if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
            raise ImpactOperationError(f"invalid_{label}")
        return value

    @staticmethod
    def _result(receipt: Mapping[str, Any], path: Path) -> ReconciliationResult:
        actions = receipt.get("actions")
        assert isinstance(actions, list)
        return ReconciliationResult(
            event_id=str(receipt["event_id"]),
            assertion_id=str(receipt["assertion_id"]),
            status=str(receipt["status"]),
            receipt_path=path,
            action_count=len(actions),
        )


def enumerate_impact(
    *, event_id: str, assertion: Mapping[str, Any], dependencies: Iterable[Mapping[str, Any]]
) -> ImpactReceipt:
    """Enumerate every expected dependency after the authoritative block.

    Unknown or malformed dependencies are represented as a blocked receipt
    rather than being skipped.  This avoids a successful-looking partial
    traversal when a reader is interrupted or the graph is incomplete.
    """

    assertion_id = assertion.get("assertion_id")
    if not isinstance(assertion_id, str) or not assertion_id:
        raise ValueError("assertion_id_required")
    if assertion.get("invalidation_state") != "blocked" or assertion.get("invalidation_event_id") != event_id:
        raise ValueError("authoritative_block_required")
    actions: list[ImpactAction] = []
    for dependency in dependencies:
        object_id = dependency.get("object_id")
        object_class = dependency.get("object_class")
        if not isinstance(object_id, str) or not object_id or not isinstance(object_class, str):
            return ImpactReceipt(event_id, assertion_id, "blocked", tuple(actions))
        action = _ACTIONS.get(object_class)
        if action is None:
            return ImpactReceipt(event_id, assertion_id, "blocked", tuple(actions))
        actions.append(ImpactAction(object_id, object_class, action))
    actions.sort(key=lambda item: (item.object_class, item.object_id, item.action))
    return ImpactReceipt(event_id, assertion_id, "pending", tuple(actions))


def _load_canonical_record(path: Path) -> dict[str, Any] | None:
    """Read one on-disk canonical record for enumeration, or ``None``.

    A missing, symlinked, or non-mapping path is treated as absent.  The
    caller only ever consults this for ids already proven authoritative via
    ``_referenced_target_ids``/``.claim_ledger_published.yaml`` (N5), so an
    absence here means the on-disk store has fallen out of sync with that
    authority -- reported by the caller as ``canonical_dependents_unavailable``
    rather than silently skipped (never a partial traversal, mirrors
    :func:`enumerate_impact`'s own "unknown dependency -> blocked" rule).
    """

    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = load_yaml(path)
    except (OSError, UnicodeDecodeError, ValueError, YAMLError):
        return None
    return value if isinstance(value, dict) else None


def enumerate_canonical_dependents(
    *,
    paths: FoundryPaths,
    workspace_id: str,
    assertion_id: str,
    assertion_version: int,
) -> list[dict[str, str]]:
    """RPC-6.1: the manifest-shaped dependent-object list one blocked source
    assertion version produces from CURRENTLY AUTHORITATIVE canonical records.

    Pure and read-only (contract §17.4: P6 consumes `inference_record`/
    `canonical_claim` as read-only input).  This function never reads or
    writes ``impact_manifests/<event_id>.json``, never calls
    :func:`enumerate_impact`/:class:`AssertionImpactReconciler`, and never
    changes the authoritative assertion-blocking order
    (``block_authoritative_reuse``).  RPC-6.3 wires this output into the live
    manifest writer (:meth:`AssertionImpactReconciler._author_manifest_with_canonical_dependents`),
    which merges it with whatever else that manifest already names rather
    than replacing it.

    Authority comes from each lane's own reader/recovery mechanism, never a
    raw manifest file consulted in isolation (standing directive N5):

    * ``inference_record``/``canonical_claim`` citability is
      ``_referenced_target_ids`` -- the workspace's CURRENT
      ``.claim_ledger_published.yaml`` generation pointer, the exact
      authority ``assertion_inference.py``/``canonical_claim_materialization.py``'s
      own recovery sweeps already consult (contract §17.7a).
    * ``report_assertion_use`` has no separate generation-manifest lane of
      its own (``services/assertion_report_use.py``'s module docstring) --
      its own immutable, content-addressed record file IS its authority, so
      every record under ``report_assertion_uses/records/`` is read
      directly.

    Only a NON-TERMINAL record is a live dependent: an ``inference_record``
    whose own ``status`` is not ``active`` (already ``stale``/``invalidated``/
    ``tombstoned`` from a prior event), or a ``canonical_claim`` whose own
    ``state`` is not ``active`` (``proposed``/``reviewed``/``split``/
    ``superseded``/``rolled_back``), is excluded -- re-flagging an
    already-handled or not-yet-live record would duplicate a prior action.

    Transitive rule: a ``canonical_claim`` citing an AFFECTED inference via
    its own ``inference_refs`` is affected even when its own
    ``source_assertion_refs`` never name the blocked assertion directly.

    Every returned action reuses ``_ACTIONS``'s EXISTING, already-shipped
    object-class vocabulary (``inference``, ``canonical_claim_edge``,
    ``report_revision``, all ``-> mark_stale``, contract finding F13) --
    this function invents no new object class and widens no schema.
    """

    if not isinstance(workspace_id, str) or not _TOKEN_RE.fullmatch(workspace_id):
        raise ImpactOperationError("invalid_workspace_id")
    if not isinstance(assertion_id, str) or not _TOKEN_RE.fullmatch(assertion_id):
        raise ImpactOperationError("invalid_assertion_id")
    if (
        not isinstance(assertion_version, int)
        or isinstance(assertion_version, bool)
        or assertion_version < 1
    ):
        raise ImpactOperationError("invalid_assertion_version")

    root = AssertionRegistry(workspace_id=workspace_id, paths=paths).root

    # -- inference_record: direct support --------------------------------
    affected_inferences: set[tuple[str, int]] = set()
    for inference_id, inference_version in sorted(
        _referenced_target_ids(paths, workspace_id=workspace_id, record_kind="inference_record")
    ):
        if not _INFERENCE_ID_RE.fullmatch(inference_id):
            raise ImpactOperationError("canonical_dependents_unavailable")
        record = _load_canonical_record(root / "inferences" / f"{inference_id}.yaml")
        if (
            record is None
            or record.get("inference_id") != inference_id
            or record.get("inference_version") != inference_version
        ):
            raise ImpactOperationError("canonical_dependents_unavailable")
        if record.get("status") != "active":
            continue
        refs = record.get("source_assertion_refs")
        if not isinstance(refs, list):
            raise ImpactOperationError("canonical_dependents_unavailable")
        if any(
            isinstance(ref, Mapping)
            and ref.get("assertion_id") == assertion_id
            and ref.get("assertion_version") == assertion_version
            for ref in refs
        ):
            affected_inferences.add((inference_id, inference_version))

    # -- canonical_claim: direct support, or transitive via an affected
    #    inference -------------------------------------------------------
    affected_canonical_claims: set[tuple[str, int]] = set()
    for canonical_claim_id, canonical_claim_version in sorted(
        _referenced_target_ids(paths, workspace_id=workspace_id, record_kind="canonical_claim")
    ):
        if not _CANONICAL_CLAIM_ID_RE.fullmatch(canonical_claim_id):
            raise ImpactOperationError("canonical_dependents_unavailable")
        record = _load_canonical_record(
            root / "canonical_claims" / canonical_claim_id / f"{canonical_claim_version}.yaml"
        )
        if (
            record is None
            or record.get("canonical_claim_id") != canonical_claim_id
            or record.get("canonical_claim_version") != canonical_claim_version
        ):
            raise ImpactOperationError("canonical_dependents_unavailable")
        if record.get("state") != "active":
            continue
        source_refs = record.get("source_assertion_refs")
        if not isinstance(source_refs, list):
            raise ImpactOperationError("canonical_dependents_unavailable")
        direct = any(
            isinstance(ref, Mapping)
            and ref.get("assertion_id") == assertion_id
            and ref.get("assertion_version") == assertion_version
            for ref in source_refs
        )
        inference_refs = record.get("inference_refs") or []
        if not isinstance(inference_refs, list):
            raise ImpactOperationError("canonical_dependents_unavailable")
        transitive = any(
            isinstance(ref, Mapping)
            and (ref.get("inference_id"), ref.get("inference_version")) in affected_inferences
            for ref in inference_refs
        )
        if direct or transitive:
            affected_canonical_claims.add((canonical_claim_id, canonical_claim_version))

    # -- report_assertion_use: cites an affected assertion/inference/claim --
    affected_report_revisions: set[str] = set()
    records_dir = root / "report_assertion_uses" / "records"
    if records_dir.is_dir():
        for use_path in sorted(records_dir.glob("*.yaml")):
            use_id = use_path.stem
            if not _REPORT_USE_ID_RE.fullmatch(use_id):
                continue
            record = _load_canonical_record(use_path)
            if record is None or record.get("use_id") != use_id:
                raise ImpactOperationError("canonical_dependents_unavailable")
            cited = record.get("cited_ref")
            report_ref = record.get("report_ref")
            if not isinstance(cited, Mapping) or not isinstance(report_ref, Mapping):
                raise ImpactOperationError("canonical_dependents_unavailable")
            ref_kind = cited.get("ref_kind")
            hit = (
                (
                    ref_kind == "source_assertion"
                    and cited.get("assertion_id") == assertion_id
                    and cited.get("assertion_version") == assertion_version
                )
                or (
                    ref_kind == "inference"
                    and (cited.get("inference_id"), cited.get("inference_version")) in affected_inferences
                )
                or (
                    ref_kind == "canonical_claim"
                    and (cited.get("canonical_claim_id"), cited.get("canonical_claim_version"))
                    in affected_canonical_claims
                )
            )
            if not hit:
                continue
            report_revision_id = report_ref.get("report_revision_id")
            if not isinstance(report_revision_id, str) or not report_revision_id:
                raise ImpactOperationError("canonical_dependents_unavailable")
            affected_report_revisions.add(report_revision_id)

    dependents: list[dict[str, str]] = []
    for inference_id in {key[0] for key in affected_inferences}:
        dependents.append(
            {"object_id": inference_id, "object_class": "inference", "action": _ACTIONS["inference"]}
        )
    for canonical_claim_id in {key[0] for key in affected_canonical_claims}:
        dependents.append(
            {
                "object_id": canonical_claim_id,
                "object_class": "canonical_claim_edge",
                "action": _ACTIONS["canonical_claim_edge"],
            }
        )
    for report_revision_id in affected_report_revisions:
        dependents.append(
            {
                "object_id": report_revision_id,
                "object_class": "report_revision",
                "action": _ACTIONS["report_revision"],
            }
        )
    dependents.sort(key=lambda item: (item["object_class"], item["object_id"]))
    return dependents


_STALEABLE_OBJECT_CLASSES = (
    "inference",
    "canonical_claim_edge",
    # K-3 (Karen Wave-3 gate, LOW): collected here for symmetry with the
    # other two classes and forward-looking report-use staleness DISPLAY
    # (a report revision citing a since-blocked/stale assertion or
    # inference), but there is no consumer yet -- `report_assertion_use.py`
    # has no lifecycle-recheck seam of its own, and no caller currently reads
    # `collect_stale_object_ids(...)["report_revision"]` for anything beyond
    # what `assertion_catalog.py`'s lineage builder already projects via
    # `report_use_index`. Left in the vocabulary by design, not a gap.
    "report_revision",
)


def collect_stale_object_ids(
    *, paths: FoundryPaths, workspace_id: str, strict: bool = False
) -> Mapping[str, frozenset[str]]:
    """F18 (RPC-6.G / N7): the ONE effective-status reader both P4's commit
    recheck (``assertion_materialization._recheck_transitive_support``) and
    P5's catalog lineage builders (``assertion_catalog._build_records``)
    must consult before trusting an ``inference``/``canonical_claim_edge``/
    ``report_revision`` record's own, never-mutated-on-disk ``status``/
    ``state`` field.

    P6 propagates staleness ONLY as durable, content-addressed
    ``impact_effects/<event_id>/<digest>.yaml`` effect receipts (N7) -- the
    inference/canonical-claim/report-revision record files themselves stay
    immutable forever.  This walks every workspace-local lifecycle receipt
    under ``impact_operations/*.yaml`` and, for each one, re-validates it
    through :meth:`AssertionImpactReconciler.validated_receipt` -- the SAME
    invariant-checked seam :class:`AssertionImpactReader` uses -- so a raw,
    untrusted effect file on disk is never consulted directly.  Only actions
    that are ``action: mark_stale``, ``status: completed`` (i.e. the receipt
    itself proves a checkpointed, tamper-evidence-checked effect record
    exists) count as stale.

    Returns a mapping keyed by exactly the three object classes P6's
    ``mark_stale`` action ever targets among the shared lifecycle vocabulary
    (``_ACTIONS``) that these two consumers care about: ``inference``,
    ``canonical_claim_edge``, ``report_revision``.  A missing workspace, a
    missing/empty ``impact_operations`` directory, or a malformed receipt
    (skipped, never fatal -- mirrors this module's existing per-record
    degrade posture) all fall back to the all-empty mapping, which is
    legacy parity: a workspace P6 has never touched behaves byte-identically
    to before this task existed.

    Callers MUST compute this once per rebuild/commit-attempt and reuse the
    result -- never call this per-assertion or per-inference-ref (perf note,
    RPC-6.G).

    K-2 (Karen Wave-3 gate, MEDIUM) split posture: a receipt file that IS
    PRESENT under ``impact_operations/`` but fails
    :meth:`AssertionImpactReconciler.validated_receipt`'s invariant checks
    (corrupt, tampered, or otherwise inconsistent) is a DIFFERENT signal than
    a workspace P6 has simply never touched -- silently dropping it from the
    stale set would "un-stale" whatever object that receipt was meant to
    mark, exactly backwards from this reader's fail-safe intent. ``strict``
    controls the posture:

    * ``strict=False`` (default; the P5 catalog lineage READ path) --
      degrades exactly as before (per-record skip, never a workspace-wide
      failure, V5-1's no-500 guarantee), but now logs a ``logging.warning``
      for every degraded record so the corruption is observable.
    * ``strict=True`` (the P4 commit-time recheck,
      ``assertion_materialization._commit_persistent_reference_locked``) --
      raises :class:`ImpactOperationError` on the FIRST present-but-invalid
      receipt instead of skipping it, so a new persistent-reference commit
      fails closed while this workspace's impact ledger has ANY corrupt
      governance record, rather than risk committing against a stale object
      this reader failed to recognize as stale.
    """

    empty: dict[str, frozenset[str]] = {name: frozenset() for name in _STALEABLE_OBJECT_CLASSES}
    if not isinstance(workspace_id, str) or not _TOKEN_RE.fullmatch(workspace_id):
        return empty
    root = AssertionRegistry(workspace_id=workspace_id, paths=paths).root
    operations_dir = root / "impact_operations"
    if not operations_dir.is_dir():
        return empty

    def _degrade_or_fail(detail: str) -> None:
        if strict:
            raise ImpactOperationError("impact_receipt_invalid")
        logger.warning(
            "assertion_impact.collect_stale_object_ids: workspace=%s %s; degrading to non-stale for read",
            workspace_id,
            detail,
        )

    reconciler = AssertionImpactReconciler(workspace_id=workspace_id, paths=paths)
    stale: dict[str, set[str]] = {name: set() for name in _STALEABLE_OBJECT_CLASSES}
    for receipt_path in sorted(operations_dir.glob("*.yaml")):
        if receipt_path.is_symlink() or not receipt_path.is_file():
            continue
        event_id = receipt_path.stem
        if not _TOKEN_RE.fullmatch(event_id):
            continue
        try:
            raw = load_yaml(receipt_path)
        except (OSError, UnicodeDecodeError, ValueError, YAMLError):
            _degrade_or_fail(f"unreadable receipt {receipt_path.name}")
            continue
        if not isinstance(raw, dict):
            _degrade_or_fail(f"malformed receipt {receipt_path.name}")
            continue
        assertion_id = raw.get("assertion_id")
        if not isinstance(assertion_id, str) or not _TOKEN_RE.fullmatch(assertion_id):
            _degrade_or_fail(f"receipt {receipt_path.name} has no valid assertion_id")
            continue
        try:
            receipt = reconciler.validated_receipt(assertion_id=assertion_id, event_id=event_id)
        except Exception:  # noqa: BLE001 - degrade-one-record: a single bad
            # receipt (invalid, tampered, or any unexpected processing error)
            # must never take down a whole workspace's catalog rebuild in
            # non-strict (read) mode -- mirrors every other best-effort index
            # this module and assertion_catalog.py already build (V5-1 / AC
            # RPC-5). K-2: the strict (commit-time) caller deliberately
            # reverses this posture via ``_degrade_or_fail`` above.
            _degrade_or_fail(f"receipt {receipt_path.name} failed validation")
            continue
        if receipt is None:
            # Structurally unreachable today (this loop only ever derives a
            # path that ``self.receipt_path(event_id)`` also resolves to,
            # and that path is proven to exist by the glob above) -- kept as
            # a defensive, non-fatal degrade rather than an assumption.
            _degrade_or_fail(f"receipt {receipt_path.name} unexpectedly absent on re-read")
            continue
        actions = receipt.get("actions")
        if not isinstance(actions, list):
            _degrade_or_fail(f"receipt {receipt_path.name} has no valid actions list")
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            object_class = action.get("object_class")
            if (
                action.get("status") == "completed"
                and action.get("action") == "mark_stale"
                and object_class in stale
                and isinstance(action.get("object_id"), str)
            ):
                stale[object_class].add(action["object_id"])
    return {name: frozenset(ids) for name, ids in stale.items()}


# Return values of :func:`effective_source_assertion_lifecycle_state`.
SOURCE_ASSERTION_ELIGIBLE = "eligible"
SOURCE_ASSERTION_BLOCKED = "blocked"
SOURCE_ASSERTION_POLICY_INVALID = "policy_invalid"


def effective_source_assertion_lifecycle_state(*, root: Path, assertion_id: str) -> str:
    """F19 (RPC-6.G validator, Karen K-1, HIGH): the ONE effective-lifecycle
    reader every DIRECT source-assertion support check must consult, instead
    of trusting the immutable ``assertions/<id>.yaml`` record's own,
    never-mutated ``lifecycle_state`` field.  Symmetric to F18's
    :func:`collect_stale_object_ids` for inference/canonical-claim/
    report-revision staleness, but for the authoritative BLOCK boundary a
    source assertion itself carries.

    A P6-authoritative block NEVER flips the immutable source assertion's
    own ``lifecycle_state`` -- :meth:`AssertionImpactReconciler.reconcile`'s
    own comment is explicit: "the immutable source assertion is never
    overwritten; its separate lifecycle policy state becomes the
    authoritative reuse boundary." That separate boundary is
    ``lifecycle_policy/<assertion_id>.yaml``. This function reuses the EXACT
    validity rule :class:`AssertionImpactReader`'s own ``_valid_policy``
    already applies when projecting a receipt summary -- never a second,
    independently-drifting definition of "validly blocked".

    Returns one of three states:

    * ``"eligible"`` -- no policy file exists yet (never blocked), or a
      validly-shaped policy exists and is not (yet) blocking this exact
      assertion (``invalidation_state: active``, the ``_load_policy``
      pre-block snapshot shape).
    * ``"blocked"`` -- a validly-shaped, blocked policy names this exact
      assertion (the SAME shape :class:`AssertionImpactReader` requires to
      surface a receipt at all).
    * ``"policy_invalid"`` -- a policy file IS PRESENT at this path but does
      not parse, or does not validate against either shape above (K-2,
      MEDIUM): deliberately distinct from ``"eligible"`` so a caller never
      silently treats a corrupt authority artifact as "not blocked". Every
      caller decides its OWN failure posture on this value: a COMMIT-path
      caller (``_recheck_transitive_support``, ``resolve_bases``,
      ``resolve_support``) must fail closed (a typed abstain/skip -- never
      silently un-blocks); a READ-path caller (the P5 catalog lineage
      builder) may degrade this to the raw record's own state, but only
      after logging a warning (never a bare, unlogged skip).

    Never raises: a missing file, a symlink (treated as absent -- the same
    posture the rest of this module already applies to untrusted on-disk
    artifacts), or an unreadable/malformed file are all reported through the
    return value, never an exception -- the caller's context decides whether
    that is fatal.
    """

    if not isinstance(assertion_id, str) or not _TOKEN_RE.fullmatch(assertion_id):
        # An unparseable id can't even NAME a policy file -- not this
        # function's job to invent a validation error for a shape its own
        # callers already gate before reaching here.
        return SOURCE_ASSERTION_ELIGIBLE
    path = root / "lifecycle_policy" / f"{assertion_id}.yaml"
    # SOL-37: a non-regular (symlinked) policy path is now `policy_invalid`,
    # never folded into the "genuinely no policy yet" absence case -- a
    # symlink at this exact path is something present and suspicious (same
    # posture the rest of this module already applies to untrusted on-disk
    # artifacts, e.g. `_is_safe_workspace_path` elsewhere in this codebase),
    # not the legitimate "P6 has never touched this assertion" state.
    if path.is_symlink():
        return SOURCE_ASSERTION_POLICY_INVALID
    if not path.is_file():
        return SOURCE_ASSERTION_ELIGIBLE
    try:
        raw = load_yaml(path)
    except (OSError, UnicodeDecodeError, ValueError, YAMLError):
        return SOURCE_ASSERTION_POLICY_INVALID
    if not isinstance(raw, dict):
        return SOURCE_ASSERTION_POLICY_INVALID
    if AssertionImpactReader._valid_policy(raw, assertion_id):
        return SOURCE_ASSERTION_BLOCKED
    # SOL-37: the full-shape active-snapshot validator, symmetric to the
    # blocked branch above -- see `_valid_active_policy`'s own docstring for
    # the exact one-field-tamper attack this closes.
    if AssertionImpactReader._valid_active_policy(raw, assertion_id):
        return SOURCE_ASSERTION_ELIGIBLE
    return SOURCE_ASSERTION_POLICY_INVALID


def resume_impact(receipt: ImpactReceipt, *, completed_object_ids: Iterable[str] = ()) -> ImpactReceipt:
    """Advance a receipt idempotently without reissuing completed actions."""

    completed = frozenset(completed_object_ids)
    if receipt.status == "blocked":
        return receipt
    actions = tuple(
        ImpactAction(action.object_id, action.object_class, action.action, "completed" if action.object_id in completed else action.status)
        for action in receipt.actions
    )
    status = "completed" if all(action.status == "completed" for action in actions) else "pending"
    return ImpactReceipt(receipt.event_id, receipt.assertion_id, status, actions)


__all__ = [
    "AssertionImpactReadDenied",
    "AssertionImpactReader",
    "AssertionImpactReconciler",
    "ImpactAction",
    "ImpactInterrupted",
    "ImpactOperationError",
    "ImpactReceipt",
    "ReconciliationResult",
    "SOURCE_ASSERTION_BLOCKED",
    "SOURCE_ASSERTION_ELIGIBLE",
    "SOURCE_ASSERTION_POLICY_INVALID",
    "collect_stale_object_ids",
    "effective_source_assertion_lifecycle_state",
    "enumerate_canonical_dependents",
    "enumerate_impact",
    "resume_impact",
]
