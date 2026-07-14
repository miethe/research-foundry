"""Idempotent, resumable lifecycle impact reconciliation.

An authoritative lifecycle block must already have been persisted before this
module receives a dependency list.  The returned receipt is pure data so a
worker can persist it, stop at any action, and resume without duplicating work.
Real downstream writebacks are never invoked here: their action is explicitly
queued as default-denied evidence for a separately authorized adapter.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..paths import FoundryPaths
from ..schemas import SchemaRegistry
from ..yamlio import dumps_yaml, load_yaml
from .assertion_registry import AssertionRegistry
from .assertion_reuse import block_authoritative_reuse

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

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


class ImpactOperationError(ValueError):
    """A persisted lifecycle operation cannot safely continue."""


class ImpactInterrupted(RuntimeError):
    """Test-only interruption after a durable action checkpoint."""


@dataclass(frozen=True)
class ReconciliationResult:
    """Persisted lifecycle-operation outcome, safe to return to a worker."""

    event_id: str
    assertion_id: str
    status: str
    receipt_path: Path
    action_count: int


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


class AssertionImpactReconciler:
    """Persist and resume one workspace-local assertion lifecycle operation.

    The authoritative assertion is blocked and atomically written before the
    manifest is read or any derived object is touched.  The receipt is then
    checkpointed after each action, so retrying an interrupted operation never
    repeats a completed cleanup or invokes a real downstream writeback.
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

        if receipt is None:
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

    def _new_receipt(self, *, event_id: str, assertion_id: str, blocked: Mapping[str, Any]) -> dict[str, Any]:
        try:
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
            receipt.get("type") != "assertion_impact_operation"
            or receipt.get("event_id") != event_id
            or receipt.get("assertion_id") != assertion_id
            or receipt.get("status") not in {"pending", "completed", "blocked"}
            or not isinstance(actions, list)
        ):
            raise ImpactOperationError("impact_receipt_invalid")
        for action in actions:
            if (
                not isinstance(action, dict)
                or not isinstance(action.get("object_id"), str)
                or not action["object_id"]
                or not isinstance(action.get("object_class"), str)
                or action.get("action") != _ACTIONS.get(action["object_class"])
                or action.get("status") not in {"pending", "completed"}
            ):
                raise ImpactOperationError("impact_receipt_invalid")
            if action["status"] == "completed":
                effect_path = self._effect_path(event_id, action)
                if action.get("effect_receipt") != str(effect_path.relative_to(self.root)):
                    raise ImpactOperationError("impact_effect_invalid")
                if self._load_mapping(effect_path, "impact_effect_invalid") != self._effect_record(event_id, action):
                    raise ImpactOperationError("impact_effect_invalid")
        actual_identities = [
            (action["object_id"], action["object_class"], action["action"])
            for action in actions
        ]
        expected_identities = [
            (action.object_id, action.object_class, action.action)
            for action in self._manifest_actions(event_id, assertion_id)
        ]
        if actual_identities != expected_identities:
            raise ImpactOperationError("impact_receipt_action_set_invalid")
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
    "AssertionImpactReconciler",
    "ImpactAction",
    "ImpactInterrupted",
    "ImpactOperationError",
    "ImpactReceipt",
    "ReconciliationResult",
    "enumerate_impact",
    "resume_impact",
]
