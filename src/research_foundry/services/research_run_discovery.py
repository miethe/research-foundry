"""Governed, read-only list/fetch over research-run activities (RPC-2.2, RPC-FR-2/FR-3).

Read counterpart to ``provenance_envelope.py``'s writers. A ``search_only``
activity with no planned run is fully discoverable here with no fabricated
``run_id`` or ``activity_id`` (RPC-FR-2's explicit success metric) — listing
and fetching never depend on ``planned_run_ref`` being populated.

Guards reused, none invented (freeze doc §10 threat boundary 4):

- Workspace-scoped reads use the same per-service ``workspace_id`` constructor
  + fail-closed-denial shape ``AssertionCatalogDenied`` already establishes for
  the assertion ledger (``services/assertion_catalog.py``).
- Run-scoped reads (for a ``planned_run`` activity) reuse
  ``export_service._run_read_allowed`` rather than reimplementing run
  visibility — a caller who supplies a ``run_meta_loader`` gets that run's own
  DF-004 workspace-scope gate applied on top of this activity's own workspace
  scoping.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..paths import FoundryPaths
from . import export_service
from .provenance_envelope import REASON_DENIED, ProvenanceEnvelopeStore

if TYPE_CHECKING:  # pragma: no cover - typing only, mirrors export_service's own FU-1 pattern
    from ..api.auth.provider import AuthIdentity


class ResearchRunDiscoveryError(ValueError):
    """A malformed request or a durable record failing integrity checks."""


class ResearchRunDiscoveryDenied(ResearchRunDiscoveryError):
    """Fail-closed denial. Mirrors ``AssertionCatalogDenied``'s shape exactly:
    one uninformative reason code, never a candidate/derived value.
    """

    def __init__(self, reason_code: str = REASON_DENIED) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ActivityRecord:
    """One discovered activity: its envelope (current version) and receipt,
    if the receipt has been published yet.
    """

    envelope: dict[str, Any]
    receipt: dict[str, Any] | None


class ResearchRunDiscovery:
    """Workspace-scoped, read-only governed access to research-run activities."""

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.workspace_id = workspace_id
        self.paths = paths or FoundryPaths.discover()
        self._store = ProvenanceEnvelopeStore(workspace_id=workspace_id, paths=self.paths)

    @staticmethod
    def denied_payload(reason_code: str = REASON_DENIED) -> dict[str, Any]:
        """Same no-existence-leak shape as ``AssertionCatalog.denied_payload``:
        an empty result set plus one uninformative reason, never a
        candidate/derived value.
        """

        return {"items": [], "next_cursor": None, "denial_reason": reason_code}

    def list_activities(
        self,
        *,
        activity_kind: str | None = None,
        identity: AuthIdentity | None = None,
        run_meta_loader: Callable[[str], Mapping[str, Any] | None] | None = None,
    ) -> dict[str, Any]:
        """List every activity in this workspace, current version only.

        ``activity_kind="search_only"`` returns activities with NO planned
        run and no fabricated id anywhere on the result (RPC-FR-2). Listing
        never raises for an individual malformed/tampered record — it is
        skipped, mirroring the fail-closed-per-record posture the assertion
        catalog uses for its own rebuild path (a single bad record must not
        take down an entire workspace's listing).

        T2-5 (hardening): applies the SAME embedded-workspace check and the
        SAME run-visibility gate (:func:`export_service._run_read_allowed`,
        via :meth:`_run_visible`) as :meth:`fetch_activity` — a
        ``planned_run`` activity whose referenced run is not readable by
        ``identity`` is silently excluded from the listing (never raised;
        listing degrades per-item, same as a malformed record).
        """

        envelopes_dir = self._store._envelopes_dir()
        items: list[dict[str, Any]] = []
        if envelopes_dir.exists():
            for envelope_dir in sorted(p for p in envelopes_dir.iterdir() if p.is_dir()):
                try:
                    envelope, receipt = self._store.read_envelope(envelope_dir.name)
                except Exception:  # noqa: BLE001 - one bad record must not break listing
                    continue
                if envelope is None:
                    continue
                # Redundant with the store's own workspace-keyed root (a
                # cross-workspace envelope_id physically cannot resolve
                # here), kept as an explicit, defense-in-depth fail-closed
                # check for parity with fetch_activity's own check (T2-5).
                if envelope.get("workspace_id") != self.workspace_id:
                    continue
                if activity_kind is not None and envelope.get("activity_kind") != activity_kind:
                    continue
                if not self._run_visible(
                    envelope, identity=identity, run_meta_loader=run_meta_loader
                ):
                    continue
                items.append(self._summary(envelope, receipt))
        return {"items": items, "next_cursor": None, "denial_reason": None}

    def fetch_activity(
        self,
        envelope_id: str,
        *,
        identity: AuthIdentity | None = None,
        run_meta_loader: Callable[[str], Mapping[str, Any] | None] | None = None,
    ) -> ActivityRecord:
        """Fetch one activity by ``envelope_id``.

        Fails closed with :class:`ResearchRunDiscoveryDenied` (never leaks
        existence) when: the envelope does not exist under THIS workspace's
        store, the stored pair fails its integrity/cross-record checks
        (:class:`~.provenance_envelope.ProvenanceIntegrityError` is
        translated to the same denial shape rather than propagated raw), or
        — for a ``planned_run`` activity — the referenced run is not
        readable by ``identity`` per ``export_service._run_read_allowed``
        (reused verbatim, never reimplemented; see :meth:`_run_visible`).

        T2-5 (hardening): ``run_meta_loader`` is no longer a caller-optional
        escape hatch. When omitted, this method resolves the run's own
        on-disk metadata itself (:meth:`_default_run_meta_loader`) rather
        than skipping the run-visibility gate entirely — the SAME real gate
        applies whether or not a caller supplies a loader. ``run_meta_loader``
        remains available for tests to override that resolution. Either way,
        a resolvable-but-``None`` run_meta (the run genuinely cannot be
        found) is NOT itself a denial signal — only an explicit ``False``
        from the reused guard is.
        """

        from .provenance_envelope import ProvenanceIntegrityError

        try:
            envelope, receipt = self._store.read_envelope(envelope_id)
        except ProvenanceIntegrityError as exc:
            raise ResearchRunDiscoveryDenied(REASON_DENIED) from exc
        if envelope is None:
            raise ResearchRunDiscoveryDenied(REASON_DENIED)
        # Redundant with the store's own workspace-keyed root (a cross-workspace
        # envelope_id physically cannot resolve here), kept as an explicit,
        # defense-in-depth fail-closed check per freeze doc §10 threat boundary 2.
        if envelope.get("workspace_id") != self.workspace_id:
            raise ResearchRunDiscoveryDenied(REASON_DENIED)

        if not self._run_visible(envelope, identity=identity, run_meta_loader=run_meta_loader):
            raise ResearchRunDiscoveryDenied(REASON_DENIED)

        return ActivityRecord(envelope=envelope, receipt=receipt)

    def _run_visible(
        self,
        envelope: Mapping[str, Any],
        *,
        identity: AuthIdentity | None,
        run_meta_loader: Callable[[str], Mapping[str, Any] | None] | None,
    ) -> bool:
        """T2-5: the ONE run-visibility gate shared by ``list_activities`` and
        ``fetch_activity``. Not a ``planned_run`` activity, no
        ``identity`` supplied (single-operator-trust, the same
        ``identity is None`` convention ``export_service._run_read_allowed``
        itself uses), or no resolvable ``run_id`` -> nothing to gate,
        visible. Otherwise resolves run metadata via ``run_meta_loader`` when
        supplied, else :meth:`_default_run_meta_loader` (closing the
        caller-optional escape hatch: omitting the loader no longer skips
        this check) and defers to ``export_service._run_read_allowed`` --
        an unresolvable run (``run_meta is None``) is visible (absence of
        metadata is not itself a denial signal).
        """

        if identity is None:
            return True
        if envelope.get("activity_kind") != "planned_run":
            return True
        run_ref = envelope.get("planned_run_ref") or {}
        run_id = run_ref.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            return True
        loader = run_meta_loader or self._default_run_meta_loader
        run_meta = loader(run_id)
        if run_meta is None:
            return True
        return export_service._run_read_allowed(self.paths, dict(run_meta), run_id, identity)

    def _default_run_meta_loader(self, run_id: str) -> Mapping[str, Any] | None:
        """T2-5: resolve real on-disk run metadata for ``run_id`` under this
        store's own foundry root, reusing ``export_service``'s own
        ``run.yaml`` resolution/load path rather than reimplementing it.
        Returns ``None`` when the run cannot be resolved on disk (never
        raises) -- "no run to check" is not itself a denial signal, it just
        means no run-scope gate applies for this read. This is what actually
        closes the caller-optional-loader escape hatch: a caller that never
        supplies ``run_meta_loader`` still gets the SAME real run-visibility
        gate applied against the run's actual on-disk state, not a silently
        skipped one.
        """

        try:
            run_paths = export_service.resolve_run_paths(self.paths, run_id)
        except export_service.ExportError:
            return None
        return export_service._load_yaml_dict(run_paths.run_yaml, run_id=run_id) or None

    @staticmethod
    def _summary(envelope: Mapping[str, Any], receipt: Mapping[str, Any] | None) -> dict[str, Any]:
        outcome = None
        if receipt is not None:
            selection_receipt = receipt.get("selection_receipt")
            if isinstance(selection_receipt, Mapping):
                outcome = selection_receipt.get("outcome")
        return {
            "envelope_id": envelope.get("envelope_id"),
            "activity_kind": envelope.get("activity_kind"),
            "activity_id": envelope.get("activity_id"),
            "planned_run_ref": envelope.get("planned_run_ref"),
            "outcome": outcome,
        }


__all__ = [
    "ResearchRunDiscoveryError",
    "ResearchRunDiscoveryDenied",
    "ActivityRecord",
    "ResearchRunDiscovery",
]
