"""External Research Report Interchange (ERI) v1 — Phase 5: resumable
importer orchestration (ERI-5.1, ERI-5.2, ERI-5.4).

Wires the frozen staging/receipt authority (``external_research_interchange``)
together with the real acquisition/resolution pipeline
(``external_research_resolution``) into ONE governed entry point:
:func:`import_external_report`. This module owns no second identity/receipt
authority of its own — ``ExternalResearchInterchange.stage()`` remains the
sole source of truth for `packet_digest`/`receipt_digest`/effects/checkpoints
(contract §3.5); this module only orchestrates *how many* actions a single
call processes before returning control, and records a safe, receipt-derived
run-timeline event when an explicit `target_run_id` is present.

**ERI-5.1 (deterministic action orchestration).** ``stage()`` itself already
builds the sorted, bounded action set from the canonical manifest and, on
resume, skips every action with an already-published immutable effect file
(``external_research_interchange._execute``) — this module adds nothing to
that mechanism. What it adds is the pre-flight identity computation (the same
`packet_digest`/`policy_digest`/`governance_policy_digest`/
`action_manifest_digest`/`receipt_digest` formulas ``stage()`` computes
internally, re-derived here so a caller can inspect pending state BEFORE
deciding whether to proceed) and the `resume=` guard below.

**ERI-5.2 (chunking and cancellation).** Per-invocation batching is
implemented WITHOUT touching ``stage()``'s internals: the
``resolve_source``/``resolve_candidate`` callables passed to `stage()` are
wrapped in a counter that raises the internal :class:`_BatchLimitReached`
signal once `limit` fresh resolutions have run in this call. Because
``stage()`` already durably persists each action's immutable effect record
(and an updated `pending` checkpoint) BEFORE resolving the next action, this
signal propagating out of ``stage()`` leaves exactly the same on-disk state a
genuine mid-acquisition cancellation (SIGINT/crash) would — a resumable
`pending` checkpoint, zero duplicate effects, and no false terminal receipt.
`limit=None` (or `--limit 0` at the CLI) disables batching entirely for one
unbounded call; batching is always disabled during `dry_run` (a dry run
performs no checkpoint-relevant writes at all — see
``external_research_resolution``'s dry-run interlock note).

**ERI-5.4 (provenance/export seam).** When `target_run_id` is present and the
call actually completes (not a dry run), a safe, receipt-derived event is
appended to that run's existing timeline via
``export_service.record_external_report_import_activity`` — reusing the same
best-effort `_trace(rp, stage=..., **fields)` idiom already used by
``source_cards``/``writeback``/``verification``/``synthesis``/etc. No new
provenance authority is introduced: `provenance_origin` stays an optional,
nullable, opaque string (contract §3.1 — RPC's real `provenance_origin`
schema does not exist yet; inventing structure for it here would be exactly
the "no invented field semantics" violation the contract forbids). This
module's public function, :func:`import_external_report`, is deliberately a
plain, typed, non-CLI-coupled service call — the intended future seam for an
Operator MCP tool. It is a seam only; no MCP tool is built here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import ExitCode, RFError
from ..paths import FoundryPaths
from .assertion_registry import AssertionRegistry
from .external_research_interchange import (
    ActionResolution,
    CallerContext,
    ExternalResearchInterchange,
    Limits,
    ResolutionDeclined,
    ResolveCandidate,
    ResolveSource,
    _action_manifest_and_digest,
    _build_action_inputs,
    authorize_caller,
    compute_governance_policy_digest,
    compute_policy_digest,
    compute_receipt_digest_accepted,
    inspect_packet,
)
from .external_research_resolution import (
    AcquireFn,
    AuthorizationPolicy,
    ExternalResearchResolver,
    Promote,
    default_promote,
)
from .source_acquisition_policy import acquire as default_acquire

# ---------------------------------------------------------------------------
# Frozen v1 acquisition-policy default (contract §4.2; mirrors the schema-valid
# ``VALID_POLICY`` fixture already exercised by
# ``tests/unit/test_external_research_interchange.py`` and
# ``tests/integration/test_external_research_resolution.py``). Callers may
# still supply their own schema-valid override; this is only the CLI/service
# default so an operator is never forced to hand-author a policy document to
# run a first import.
# ---------------------------------------------------------------------------

DEFAULT_ACQUISITION_POLICY: dict[str, Any] = {
    "schema_version": "1.0",
    "type": "external_research_acquisition_policy",
    "allowed_schemes": ["https", "http"],
    "reject_embedded_credentials": True,
    "canonicalization": {
        "single_parse": True,
        "idna_normalization": True,
        "reject_userinfo": True,
        "reject_percent_encoded_host": True,
        "reject_ipv6_zone_ids": True,
        "reject_ambiguous_numeric_host": True,
        "strip_single_trailing_root_label_dot": True,
        "shared_authority_object_for_transport": True,
    },
    "transport_architecture": {
        "single_actor_owns_full_lifecycle": True,
        "hands_off_acquired_bytes_only": True,
        "environment_and_pac_proxies_disabled": True,
        "provider_delegated_fetch_allowed": False,
    },
    "forbidden_address_categories": [
        "loopback",
        "private",
        "reserved",
        "link_local",
        "multicast",
        "unspecified",
        "carrier_grade_nat",
        "benchmark_or_documentation",
        "cloud_metadata",
        "encoded_or_obfuscated_host",
        "ipv6_transition_or_translation",
        "ipv6_site_local",
    ],
    "metadata_deny_set": [
        "169.254.169.254",
        "fd00:ec2::254",
        "metadata.google.internal",
        "metadata.azure.com",
        "169.254.169.253",
        "100.100.100.200",
    ],
    "metadata_deny_set_version": "v1-2026-07-26",
    "special_purpose_address_registry_version": "iana-special-purpose-2026-07-26",
    "ipv6_transition_policy": {
        "well_known_prefixes": [
            "64:ff9b::/96",
            "64:ff9b:1::/48",
            "2002::/16",
            "2001::/32",
            "::ffff:0:0/96",
            "::/96",
        ],
        "decode_and_validate_embedded_ipv4": True,
        "operator_configured_nat64_prefixes": [],
    },
    "dns_policy": {
        "validate_every_answer": True,
        "bind_to_validated_address": True,
        "verify_connected_peer": True,
    },
    "redirects": {"max_hops": 3, "revalidate_every_hop": True},
    "transport_fallback_allowed": False,
    "local_asset_carve_out": {
        "packet_internal_attachment_resolution": True,
        "out_of_packet_requires_operator_grant": True,
        "operator_grant_binds_path_and_digest": True,
        "producer_supplied_locator_type_hint_ignored": True,
    },
    "denial": {
        "leaks_denied_ids": False,
        "leaks_resolved_addresses": False,
        "leaks_text": False,
        "leaks_counts": False,
        "leaks_reason_code_differential": False,
    },
}

# ERI-OQ-4 frozen default batch size. ``limit=None`` disables batching for one
# unbounded call; the CLI maps ``--limit 0`` to ``None``.
DEFAULT_BATCH_SIZE = 100


class ImportOrchestrationError(RFError):
    """Base class for orchestration-level (not staging/resolution-level) errors."""

    exit_code = ExitCode.USAGE


class PendingImportError(ImportOrchestrationError):
    """A pending (incomplete) import already exists for this exact identity.

    Raised only when ALL of: no terminal receipt exists yet, a `pending`
    checkpoint from a PRIOR call does, `resume` was not requested, and this is
    not a `dry_run` (a dry run never mutates state and is always safe to
    re-run). A brand-new import (no checkpoint at all yet) never raises this —
    the guard exists only to stop an operator from *accidentally* continuing
    someone else's in-flight import, not to require `--resume` on every call.
    """


class _BatchLimitReached(ResolutionDeclined):
    """Internal control-flow signal (never a packet or resolver error).

    Raised by the wrapped resolver once `limit` fresh resolutions have run in
    this call; caught by :func:`import_external_report` immediately outside
    ``stage()``. Never a subclass of :class:`RFError` — it never reaches a
    caller as an exception.

    Subclasses :class:`ResolutionDeclined` (round-2 audit finding #5): the
    wrapper below raises this BEFORE calling the underlying resolve
    callable, never after, so `ExternalResearchInterchange._execute` can
    rely on catching :class:`ResolutionDeclined` to know no downstream
    mutation was attempted for the in-flight action and clear its
    just-written outbox "prepare" marker before re-raising.
    """


def _limited(
    resolve_fn: Callable[..., ActionResolution], counter: dict[str, int], limit: int
) -> Callable[..., ActionResolution]:
    """Wrap a ``resolve_source``/``resolve_candidate`` callable with a shared,
    cross-kind fresh-resolution counter (ERI-5.2's per-invocation batch size).
    """

    def _wrapped(*args: Any, **kwargs: Any) -> ActionResolution:
        if counter["done"] >= limit:
            raise _BatchLimitReached()
        result = resolve_fn(*args, **kwargs)
        counter["done"] += 1
        return result

    return _wrapped


@dataclass(frozen=True)
class ImportOutcome:
    """Result of one :func:`import_external_report` call.

    ``complete=False`` means the per-invocation batch limit was reached
    before every action resolved — a `pending` checkpoint was preserved
    on disk and re-calling with `resume=True` continues from the first
    incomplete action. ``receipt``/``checkpoint`` are the full (schema-valid)
    documents for callers that need them; :meth:`safe_dict` is the
    redaction-matrix-compliant (contract §4.6) subset safe for CLI machine
    output, logs, or a future MCP tool response — never packet-derived free
    text, never a resolved address, never a per-item reason code.
    """

    complete: bool
    workspace_id: str
    target_run_id: str | None
    packet_digest: str | None
    receipt_id: str | None
    receipt_digest: str
    status: str  # "completed" | "completed_with_quarantine" | "blocked" | "pending"
    replayed: bool
    dry_run: bool
    block_reason: str | None
    counts: dict[str, Any] | None
    cursor: dict[str, Any] | None
    receipt: dict[str, Any] | None
    checkpoint: dict[str, Any] | None

    def safe_dict(self) -> dict[str, Any]:
        """Machine-safe payload (contract §4.6 CLI-stdout row): safe
        generated IDs, aggregate counts, and cursor only — no packet-derived
        free text, no resolved addresses, and never the 14-code source/
        citation/candidate reason-code vocabulary (only `block_reason`, the
        packet family, which describes the caller's own submitted packet
        structure back to its own submitter).
        """

        return {
            "workspace_id": self.workspace_id,
            "target_run_id": self.target_run_id,
            "packet_digest": self.packet_digest,
            "receipt_id": self.receipt_id,
            "receipt_digest": self.receipt_digest,
            "status": self.status,
            "complete": self.complete,
            "replayed": self.replayed,
            "dry_run": self.dry_run,
            "block_reason": self.block_reason,
            "counts": self.counts,
            "cursor": self.cursor,
        }


def _cursor_from_checkpoint(checkpoint: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    cursor = checkpoint.get("cursor")
    return dict(cursor) if isinstance(cursor, Mapping) else None


def _authorization_policy_digest_input(policy: AuthorizationPolicy) -> dict[str, Any]:
    """Canonical, hashable representation of the effective per-import
    rights/sensitivity policy (contract §1.3, round-2 audit finding #1).

    Built here rather than in ``external_research_resolution.py`` (which
    owns the :class:`AuthorizationPolicy` dataclass but not receipt
    identity) so ``external_research_interchange.compute_governance_policy_digest``
    keeps accepting a plain mapping rather than depending on a resolution-
    layer dataclass shape. Always given a CONCRETE (never-``None``) policy —
    callers resolve the effective policy (explicit or
    ``AuthorizationPolicy()``'s default) before calling this, so "no policy
    was explicitly supplied" and "the default policy was explicitly
    supplied" hash identically, and a genuinely different effective policy
    (e.g. `denied_access_statuses` widened after an operator investigation)
    always hashes differently — closing the exploit the finding named:
    importing once under a permissive policy, then retrying under a
    denying one, no longer replays the earlier permissive outcome.
    """

    return {
        "denied_access_statuses": sorted(policy.denied_access_statuses),
        "require_rights_for_access_statuses": sorted(policy.require_rights_for_access_statuses),
    }


def import_external_report(
    packet_dir: str | Path,
    *,
    workspace_id: str,
    target_run_id: str | None = None,
    policy: Mapping[str, Any] | None = None,
    limits: Limits | None = None,
    dry_run: bool = False,
    resume: bool = False,
    limit: int | None = DEFAULT_BATCH_SIZE,
    paths: FoundryPaths | None = None,
    resolver: ExternalResearchResolver | None = None,
    authorization_policy: AuthorizationPolicy | None = None,
    acquire: AcquireFn | None = None,
    promote: Promote | None = default_promote,
    provenance_origin: str | None = None,
    caller: CallerContext | None = None,
) -> ImportOutcome:
    """ERI-5.1/5.2/5.4: stage (and, when `target_run_id` is set, project) one
    external research report packet, resumably and in bounded batches.

    This is the intended service seam for a future Operator MCP tool and for
    ``rf intake external-report`` (ERI-5.3) alike — plain, typed, and free of
    any CLI/argparse coupling.

    Args:
        packet_dir: materialized directory of the `external_research_handoff/v1`
            packet (contract §1.1 — directory-only transport).
        workspace_id: target workspace (always required, contract §1.3).
        target_run_id: optional target run; ``None`` is staging-only (contract
            §1.4) — no run is created, no run-local projection is written, and
            `verified` is categorically unreachable.
        policy: schema-valid `external_research_acquisition_policy` document;
            defaults to :data:`DEFAULT_ACQUISITION_POLICY` (the frozen v1
            defaults) when omitted.
        dry_run: report the plan with zero canonical effects; never mutates
            state (never writes staging artifacts, effects, checkpoints, the
            receipt, or a run-timeline event) and always disables batching
            (a dry run resolves every action in one pass, matching
            ``stage(dry_run=True)``'s own existing behavior).
        resume: authorizes continuing a PRE-EXISTING `pending` checkpoint for
            this exact identity. A brand-new import never needs this. Without
            it, a pre-existing pending checkpoint raises
            :class:`PendingImportError` rather than silently continuing
            someone else's possibly-abandoned in-flight import.
        limit: max NEW (not-yet-resolved) actions to process this call —
            ERI-5.2's per-invocation batch size (frozen default 100,
            ERI-OQ-4). ``None`` disables batching for one unbounded call.
        resolver: inject a pre-built :class:`ExternalResearchResolver` (tests,
            or a caller with its own authorization/acquire/promote wiring
            already assembled) instead of the default real one. The default
            resolver's own `dry_run` flag always mirrors this call's
            `dry_run` (see ``external_research_resolution``'s dry-run
            interlock note) — a caller-supplied `resolver` must do the same
            itself; this function does not override an injected resolver's
            own `dry_run` flag.
        provenance_origin: optional, nullable, opaque RPC import-context
            reference (contract §3.1 — `provenance_origin`'s real schema does
            not exist yet; this carries an operator/caller-supplied opaque
            string through to the run-timeline event only, inventing no
            structure for it).
        caller: optional live caller identity (contract §1.6 / audit finding
            #9). ``None`` (the only value the bare CLI passes today) is
            single-operator-trust and leaves this function's behavior
            unchanged; see ``external_research_interchange.CallerContext``
            and ``authorize_caller``. Re-checked FRESH here, before this
            function's own pre-derivation `_load_receipt`/pending-checkpoint
            lookup below, and again inside ``stage()`` itself — a caller
            that fails this gate never reaches any receipt-existence check
            at all, fresh or replayed.

    Returns:
        :class:`ImportOutcome`.

    Raises:
        PendingImportError: a pending checkpoint exists and `resume` was not
            requested (and this is not a `dry_run`).
        CallerNotAuthorizedError: `caller` failed live reauthorization.
    """

    paths = paths or FoundryPaths.discover()
    authorize_caller(caller, workspace_id=workspace_id, paths=paths)
    effective_policy: Mapping[str, Any] = policy if policy is not None else DEFAULT_ACQUISITION_POLICY
    # Round-2 audit finding #1: always resolve a CONCRETE effective
    # rights/sensitivity policy (explicit or `AuthorizationPolicy()`'s
    # default) and fold its canonical form into `governance_policy_digest`
    # (and therefore `receipt_digest`) — see `_authorization_policy_digest_input`.
    effective_authorization_policy = authorization_policy if authorization_policy is not None else AuthorizationPolicy()
    authorization_policy_digest_input = _authorization_policy_digest_input(effective_authorization_policy)
    interchange = ExternalResearchInterchange(workspace_id=workspace_id, paths=paths)

    # Round-2 audit finding #6: inspect the packet directory EXACTLY ONCE
    # for this whole call. The prior implementation inspected here AND
    # again inside `stage()`'s own internal `inspect_packet` call — two
    # independent snapshots of a mutable directory that a concurrent
    # mutation between them could straddle. This one `PacketInspection` is
    # now threaded through resolver construction (`candidate_records`
    # below), batching (`actions` below), and `stage(inspection=...)`
    # itself, which performs NO second inspection when one is supplied.
    inspection = inspect_packet(packet_dir, limits=limits)

    if not inspection.ok:
        # Blocked packets have zero actions (contract §2.2) -- nothing to
        # batch or resume; delegate straight to `stage()`.
        result = interchange.stage(
            packet_dir,
            target_run_id=target_run_id,
            policy=effective_policy,
            authorization_policy=authorization_policy_digest_input,
            limits=limits,
            dry_run=dry_run,
            caller=caller,
            inspection=inspection,
        )
        receipt = result.receipt
        return ImportOutcome(
            complete=True,
            workspace_id=workspace_id,
            target_run_id=target_run_id,
            packet_digest=receipt.get("packet_digest"),
            receipt_id=receipt.get("receipt_id"),
            receipt_digest=receipt["receipt_digest"],
            status=receipt["status"],
            replayed=result.replayed,
            dry_run=result.dry_run,
            block_reason=receipt.get("block_reason"),
            counts=receipt.get("counts"),
            cursor=None,
            receipt=receipt,
            checkpoint=result.checkpoint,
        )

    # Pre-derive the SAME identity `stage()` computes internally (contract
    # §1.3) so pending-checkpoint / batch-limit handling can inspect state
    # both before and after calling it, without a second identity authority.
    actions = _build_action_inputs(inspection)
    _manifest, action_manifest_digest = _action_manifest_and_digest(actions)
    policy_digest = compute_policy_digest(effective_policy)
    governance_policy_digest = compute_governance_policy_digest(
        authorization_policy=authorization_policy_digest_input
    )
    receipt_digest = compute_receipt_digest_accepted(
        packet_digest=inspection.packet_digest,
        workspace_id=workspace_id,
        target_run_id=target_run_id,
        policy_digest=policy_digest,
        schema_major_versions=inspection.schema_major_versions,
        action_manifest_digest=action_manifest_digest,
        governance_policy_digest=governance_policy_digest,
    )

    if resolver is None:
        resolver = ExternalResearchResolver(
            workspace_id=workspace_id,
            acquisition_policy=effective_policy,
            candidate_records=inspection.candidate_records,
            registry=AssertionRegistry(workspace_id=workspace_id, paths=paths),
            authorization_policy=effective_authorization_policy,
            acquire=acquire or default_acquire,
            promote=promote,
            dry_run=dry_run,
            paths=paths,
        )

    resolve_source: ResolveSource = resolver.resolve_source
    resolve_candidate: ResolveCandidate = resolver.resolve_candidate
    if not dry_run and limit is not None:
        counter = {"done": 0}
        resolve_source = _limited(resolve_source, counter, limit)  # type: ignore[assignment]
        resolve_candidate = _limited(resolve_candidate, counter, limit)  # type: ignore[assignment]

    if dry_run:
        # Dry-run never mutates state (contract §1.5) and is always safe to
        # run concurrently with a real in-flight import — it does not
        # participate in the receipt-identity lease or the pending-
        # checkpoint guard below (round-2 audit finding #9 only concerns
        # the non-dry-run resume race).
        result = interchange.stage(
            packet_dir,
            target_run_id=target_run_id,
            policy=effective_policy,
            authorization_policy=authorization_policy_digest_input,
            resolve_source=resolve_source,
            resolve_candidate=resolve_candidate,
            limits=limits,
            dry_run=True,
            caller=caller,
            inspection=inspection,
        )
        receipt = result.receipt
        return ImportOutcome(
            complete=True,
            workspace_id=workspace_id,
            target_run_id=target_run_id,
            packet_digest=receipt.get("packet_digest"),
            receipt_id=receipt.get("receipt_id"),
            receipt_digest=receipt["receipt_digest"],
            status=receipt["status"],
            replayed=result.replayed,
            dry_run=result.dry_run,
            block_reason=receipt.get("block_reason"),
            counts=receipt.get("counts"),
            cursor=_cursor_from_checkpoint(result.checkpoint),
            receipt=receipt,
            checkpoint=result.checkpoint,
        )

    # Round-2 audit finding #9: the pending-checkpoint guard and the actual
    # continuation (`stage()`) now share ONE receipt-identity lease,
    # acquired here and held across both — closing the race where two
    # initially-fresh (`resume=False`) calls could both observe "no pending
    # checkpoint yet" before either one's checkpoint existed, and the
    # second would then silently continue the first's in-flight import
    # despite explicitly not asking to resume. `stage()` is called with
    # `_lease_already_held=True` so it does not attempt a second,
    # self-deadlocking acquisition of the same lock file.
    with interchange._receipt_lease(receipt_digest):
        # Reauthorize immediately before the receipt-existence lookup below
        # (round-2 audit finding #3) — the top-of-function check may be
        # stale by the time this lease is acquired.
        authorize_caller(caller, workspace_id=workspace_id, paths=paths)

        existing_receipt = interchange._load_receipt(receipt_digest)
        existing_checkpoint = interchange._load_checkpoint(receipt_digest)
        if (
            not resume
            and existing_receipt is None
            and existing_checkpoint is not None
            and existing_checkpoint.get("status") == "pending"
        ):
            raise PendingImportError(
                "a pending import already exists for this exact packet/workspace/target/policy "
                f"identity (receipt_digest={receipt_digest}); pass resume=True (--resume) to "
                "continue it, or dry_run=True to inspect without mutating state"
            )

        try:
            result = interchange.stage(
                packet_dir,
                target_run_id=target_run_id,
                policy=effective_policy,
                authorization_policy=authorization_policy_digest_input,
                resolve_source=resolve_source,
                resolve_candidate=resolve_candidate,
                limits=limits,
                dry_run=False,
                caller=caller,
                inspection=inspection,
                _lease_already_held=True,
            )
        except _BatchLimitReached:
            checkpoint = interchange._load_checkpoint(receipt_digest)
            return ImportOutcome(
                complete=False,
                workspace_id=workspace_id,
                target_run_id=target_run_id,
                packet_digest=inspection.packet_digest,
                receipt_id=f"erh_{receipt_digest}",
                receipt_digest=receipt_digest,
                status="pending",
                replayed=False,
                dry_run=False,
                block_reason=None,
                counts=None,
                cursor=_cursor_from_checkpoint(checkpoint),
                receipt=None,
                checkpoint=checkpoint,
            )

    receipt = result.receipt
    outcome = ImportOutcome(
        complete=True,
        workspace_id=workspace_id,
        target_run_id=target_run_id,
        packet_digest=receipt.get("packet_digest"),
        receipt_id=receipt.get("receipt_id"),
        receipt_digest=receipt["receipt_digest"],
        status=receipt["status"],
        replayed=result.replayed,
        dry_run=result.dry_run,
        block_reason=receipt.get("block_reason"),
        counts=receipt.get("counts"),
        cursor=_cursor_from_checkpoint(result.checkpoint),
        receipt=receipt,
        checkpoint=result.checkpoint,
    )

    # ERI-5.4: record a safe, receipt-derived event on the target run's
    # EXISTING timeline -- never on a staging-only (target_run_id=None)
    # import, and never on a dry run (which must never mutate anything).
    if target_run_id is not None and not dry_run:
        from .export_service import record_external_report_import_activity

        record_external_report_import_activity(
            paths,
            target_run_id,
            receipt=receipt,
            provenance_origin=provenance_origin,
        )

    return outcome


__all__ = [
    "DEFAULT_ACQUISITION_POLICY",
    "DEFAULT_BATCH_SIZE",
    "ImportOrchestrationError",
    "ImportOutcome",
    "PendingImportError",
    "import_external_report",
]
