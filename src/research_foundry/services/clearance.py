"""Clearance gates — ship-blocking determinations, separated from feature flags.

A feature flag answers "is the mechanism reachable?". It cannot answer "has a
human with standing signed off?". Before this module the two were welded
together, so the only safe posture for anything license-gated was total
inertness — ``services/attribution_fetch/`` imports no networking library at
all — which blocked local development on a *legal* determination. This module
holds clearance state separately, so the site stays usable locally while
redistribution and clinical reliance stay blocked.

Three scopes, because gates block at different depths (see
``config/clearance_gates.yaml``):

``acquisition``
    May not fetch or cache even locally. DEF-2's vendors prohibit caching
    outright. The dev/test posture must NEVER open this scope.
``redistribution``
    May fetch and use locally; may not leave the machine. DEF-1, DEF-3, DEF-6.
``clinical_reliance``
    May be viewed and reasoned over; may not be relied upon clinically.

LAYERING. This module is a sibling of ``governance.py``, not part of it, and
the split is deliberate: ``guard_check`` is run-level policy over an aggregate
``GuardContext`` (run sensitivity, writeback targets, proposed field writes),
and structurally cannot express "this specific record is blocked, allow the
others". Clearance is per-record shape enforcement. The same layering already
exists between ``governance.py``'s name-based rules and
``schemas/source_attribution.schema.yaml``'s structural gate, where the module's
own rule-8 comment records that the schema shape — not the name list — is the
real control.

WHAT THIS MODULE DOES NOT DO. It cannot close a gate. Closing is an operator
edit of ``config/clearance_gates.yaml``, because any ``rf`` subcommand that
closed a gate would be agent-runnable by definition, and
``docs/dev/architecture/adr-rights-entity-model.md`` OQ-RF-6 records that RF has
no counsel/attestation workflow — the boundary is "human-only by exclusion".
``governance.py`` rule 9 blocks an agent-writable path from proposing
``state: closed`` or from clearing a record's stamp.

It also asserts NO license posture for any provider. DEF-1 and DEF-6 remain
open; this module is the mechanism that keeps content acquired under an
unsettled posture from leaving the machine, not a determination that the
posture has settled.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import ExitCode, RFError
from ..ids import now_iso
from ..paths import FoundryPaths, distribution_root
from ..yamlio import load_yaml

REGISTRY_FILENAME = "clearance_gates.yaml"

#: Key carrying a record's durable taint (schemas/clearance_taint.schema.yaml).
TAINT_KEY = "clearance"
#: Key inside the taint block listing scopes the record may not be used for.
BLOCKED_SCOPES_KEY = "blocked_scopes"

#: The complete scope vocabulary. Deliberately distinct from the
#: rights-clearance family (``CLEARED_*``/``counsel_approved``/``attested``,
#: human-only per ADR Invariant 1) — reusing those literals would make
#: clearance a laundering path into rights state.
BLOCKING_SCOPES: frozenset[str] = frozenset(
    {"acquisition", "redistribution", "clinical_reliance"}
)

#: Gate lifecycle values. ``closed`` is reachable only by an operator file edit.
GATE_STATES: frozenset[str] = frozenset({"open", "closed"})

_REQUIRED_GATE_FIELDS: tuple[str, ...] = (
    "gate_id",
    "blocks_scope",
    "state",
    "summary",
    "evidence_pointer",
)


class ClearanceConfigError(RFError):
    """The clearance registry is missing, malformed, or carries an unknown value.

    Raised rather than defaulted. A registry that silently defaulted a
    misspelled ``state`` to ``open`` would be indistinguishable from one that
    read the operator's intent correctly, and a typo in a *closed* gate would
    silently re-block; a typo in an *open* one would silently release. Neither
    may be guessed.
    """

    exit_code: ExitCode = ExitCode.SCHEMA


@dataclass(frozen=True)
class Gate:
    """One ship-blocking determination, loaded verbatim from the registry."""

    gate_id: str
    blocks_scope: str
    state: str
    summary: str
    evidence_pointer: str
    closed_by: str | None = None

    @property
    def is_open(self) -> bool:
        return self.state == "open"


def _registry_path(paths: FoundryPaths | None = None) -> Path:
    """Resolve the registry file, mirroring :func:`schemas._schemas_dir`.

    Prefers the active workspace's ``config/`` and falls back to the
    distribution root so a fresh checkout still resolves.
    """

    paths = paths or FoundryPaths.discover()
    candidate = paths.config / REGISTRY_FILENAME
    if candidate.exists():
        return candidate
    fallback = distribution_root() / "config" / REGISTRY_FILENAME
    return fallback if fallback.exists() else candidate


class GateRegistry:
    """Loads and validates ``config/clearance_gates.yaml``.

    Every value is validated on load and an unknown one raises. There is no
    accessor that evaluates a condition expression, because the registry
    carries none: ``config/governance.yaml``'s ``policy_rules`` has
    ``condition:``/``severity:`` keys that are never parsed, producing a file
    that looks enforcing and is not. All rule logic lives in Python.
    """

    def __init__(self, path: str | Path | None = None, *, paths: FoundryPaths | None = None) -> None:
        self.path = Path(path) if path else _registry_path(paths)
        self._gates: tuple[Gate, ...] | None = None
        self._applies_to_kinds: frozenset[str] | None = None

    # -- loading ----------------------------------------------------------

    def _load(self) -> None:
        if self._gates is not None:
            return
        if not self.path.exists():
            raise ClearanceConfigError(
                f"Clearance registry not found: {self.path}. Clearance is "
                "fail-closed — a missing registry is refused rather than "
                "treated as 'no gates open'."
            )
        try:
            data = load_yaml(self.path)
        except Exception as exc:  # malformed YAML
            raise ClearanceConfigError(f"Clearance registry {self.path} is unreadable: {exc}") from exc
        if not isinstance(data, dict):
            raise ClearanceConfigError(f"Clearance registry {self.path} is not a mapping")

        kinds = data.get("applies_to_kinds")
        if not isinstance(kinds, list) or not all(isinstance(k, str) and k.strip() for k in kinds):
            raise ClearanceConfigError(
                f"{self.path}: applies_to_kinds must be a list of non-empty strings "
                "(it is the backward-compatibility mechanism — an absent or "
                "malformed list must not be guessed)"
            )

        raw_gates = data.get("gates")
        if not isinstance(raw_gates, list):
            raise ClearanceConfigError(f"{self.path}: gates must be a list")

        gates: list[Gate] = []
        seen: set[str] = set()
        for index, entry in enumerate(raw_gates):
            if not isinstance(entry, dict):
                raise ClearanceConfigError(f"{self.path}: gates[{index}] is not a mapping")
            missing = [f for f in _REQUIRED_GATE_FIELDS if not str(entry.get(f) or "").strip()]
            if missing:
                raise ClearanceConfigError(
                    f"{self.path}: gates[{index}] is missing non-empty {', '.join(missing)}"
                )
            gate_id = str(entry["gate_id"]).strip()
            if gate_id in seen:
                raise ClearanceConfigError(
                    f"{self.path}: duplicate gate_id {gate_id!r} — two entries for one gate "
                    "would let a reader resolve either state depending on iteration order"
                )
            seen.add(gate_id)

            scope = str(entry["blocks_scope"]).strip()
            if scope not in BLOCKING_SCOPES:
                raise ClearanceConfigError(
                    f"{self.path}: gates[{index}] ({gate_id}) has unknown blocks_scope "
                    f"{scope!r}; expected one of {sorted(BLOCKING_SCOPES)}"
                )
            state = str(entry["state"]).strip()
            if state not in GATE_STATES:
                raise ClearanceConfigError(
                    f"{self.path}: gates[{index}] ({gate_id}) has unknown state {state!r}; "
                    f"expected one of {sorted(GATE_STATES)}. A misspelled state is never "
                    "defaulted to 'open' — that would be indistinguishable from a "
                    "correctly-read intent."
                )

            forbidden = set(entry) - set(_REQUIRED_GATE_FIELDS) - {"closed_by"}
            if forbidden:
                raise ClearanceConfigError(
                    f"{self.path}: gates[{index}] ({gate_id}) carries unsupported key(s) "
                    f"{sorted(forbidden)}. In particular `condition:` and `severity:` are "
                    "refused by design: config/governance.yaml has exactly such keys and "
                    "they are never parsed, which is the trap this registry avoids."
                )

            closed_by = entry.get("closed_by")
            closed_by = str(closed_by).strip() if isinstance(closed_by, str) and closed_by.strip() else None
            if state == "closed" and not closed_by:
                raise ClearanceConfigError(
                    f"{self.path}: gate {gate_id} is state: closed with no closed_by. A gate "
                    "may only be closed by a named human — an anonymous closure is refused."
                )

            gates.append(
                Gate(
                    gate_id=gate_id,
                    blocks_scope=scope,
                    state=state,
                    summary=str(entry["summary"]).strip(),
                    evidence_pointer=str(entry["evidence_pointer"]).strip(),
                    closed_by=closed_by,
                )
            )

        self._gates = tuple(gates)
        self._applies_to_kinds = frozenset(k.strip() for k in kinds)

    # -- accessors --------------------------------------------------------

    def gates(self) -> tuple[Gate, ...]:
        self._load()
        assert self._gates is not None  # _load populates or raises
        return self._gates

    def applies_to_kinds(self) -> frozenset[str]:
        """Record kinds subject to the fail-closed absence check.

        A kind absent from this set skips the check entirely. That is the
        backward-compatibility mechanism, not a loophole: every record kind
        predating clearance (source_card, claim, report, assertion, and the 7
        committed pediatric bundles) is structurally incapable of carrying a
        stamp, so listing one here would convert a safety control into a
        correctness regression.
        """

        self._load()
        assert self._applies_to_kinds is not None
        return self._applies_to_kinds

    def governs_kind(self, kind: str) -> bool:
        return kind in self.applies_to_kinds()

    def open_gates(self) -> tuple[Gate, ...]:
        return tuple(g for g in self.gates() if g.is_open)

    def open_scopes(self) -> frozenset[str]:
        """Scopes with at least one open gate — the scopes a new stamp must block."""

        return frozenset(g.blocks_scope for g in self.gates() if g.is_open)

    def gate_ids_for_scope(self, scope: str) -> tuple[str, ...]:
        """Open gate ids blocking *scope*, for a new stamp's ``gate_refs``."""

        if scope not in BLOCKING_SCOPES:
            raise ClearanceConfigError(
                f"Unknown scope {scope!r}; expected one of {sorted(BLOCKING_SCOPES)}"
            )
        return tuple(g.gate_id for g in self.gates() if g.is_open and g.blocks_scope == scope)


def load_registry(*, paths: FoundryPaths | None = None) -> GateRegistry:
    """Build a registry for the active workspace.

    Deliberately not cached process-wide: the registry is the operator's live
    statement of what is cleared, and a long-lived process must not pin a stale
    copy after a file edit.
    """

    return GateRegistry(paths=paths)


def summarize(registry: GateRegistry | None = None) -> dict[str, Any]:
    """Read-only projection backing ``rf clearance status``. Never mutates."""

    reg = registry or load_registry()
    gates = reg.gates()
    return {
        "registry_path": str(reg.path),
        "applies_to_kinds": sorted(reg.applies_to_kinds()),
        "open_scopes": sorted(reg.open_scopes()),
        "gates": [
            {
                "gate_id": g.gate_id,
                "blocks_scope": g.blocks_scope,
                "state": g.state,
                "closed_by": g.closed_by,
                "summary": g.summary,
                "evidence_pointer": g.evidence_pointer,
            }
            for g in gates
        ],
    }


# ---------------------------------------------------------------------------
# Durable per-record stamping — the WRITE side of the taint block (M3)
# ---------------------------------------------------------------------------
#
# mediate_egress (below) is the READ side: it consults a record's own
# ``clearance`` block and never re-derives it from the registry's live gate
# state. This is the WRITE side, called exactly once per fetched record, at
# fetch time. It takes NO ``GateRegistry`` parameter at all and never loads
# ``config/clearance_gates.yaml`` -- so a later edit to that file, or a later
# posture flip, cannot retroactively change what an already-produced stamp
# says. This is design invariant 2 (clearance-gates-v1.md), made structural
# rather than merely tested-to-hold: the function has nothing to re-derive
# from even if a future caller tried.

#: Values ``posture_at_stamp`` may carry (schemas/clearance_taint.schema.yaml).
POSTURE_VALUES: frozenset[str] = frozenset({"none", "dev_test"})


def stamp_taint(
    *,
    blocked_scopes: Iterable[str],
    stamped_by: str,
    posture_at_stamp: str,
    gate_refs: Iterable[str] = (),
    note: str | None = None,
) -> dict[str, Any]:
    """Build a durable clearance-taint block (schemas/clearance_taint.schema.yaml).

    Callers pass the scopes to block EXPLICITLY -- this function does not
    consult :meth:`GateRegistry.open_scopes` or any other live gate state.
    The caller (e.g. the dev/test posture's real-fetch path, which uses a
    STATIC provider->scope map) decides what was true at THIS moment, and
    that decision is frozen into the returned dict forever. A later change
    to the registry, or to the posture that authorized the fetch, can only
    affect NEW stamps produced by a later call -- never this one.

    ``gate_refs`` is advisory provenance only (per the schema's own
    description: "an empty or stale ``gate_refs`` can never widen permitted
    use" -- :func:`mediate_egress` never reads it). Passing ``()`` (the
    default) is valid; nothing requires consulting the registry to populate
    it.

    Raises :class:`ClearanceConfigError` if ``blocked_scopes`` or
    ``posture_at_stamp`` carries a value outside the schema's vocabulary --
    a stamp that could not later be read back correctly must never be
    produced.
    """

    scopes = sorted({str(s) for s in blocked_scopes})
    unknown = [s for s in scopes if s not in BLOCKING_SCOPES]
    if unknown:
        raise ClearanceConfigError(
            f"stamp_taint: unknown blocked_scopes {unknown}; expected one of "
            f"{sorted(BLOCKING_SCOPES)}"
        )
    if posture_at_stamp not in POSTURE_VALUES:
        raise ClearanceConfigError(
            f"stamp_taint: unknown posture_at_stamp {posture_at_stamp!r}; expected "
            f"one of {sorted(POSTURE_VALUES)}"
        )
    if not str(stamped_by).strip():
        raise ClearanceConfigError("stamp_taint: stamped_by must be a non-empty string")

    block: dict[str, Any] = {
        "schema_version": "1.0",
        "blocked_scopes": scopes,
        "stamped_at": now_iso(),
        "stamped_by": stamped_by,
        "posture_at_stamp": posture_at_stamp,
        "gate_refs": sorted({str(g) for g in gate_refs}),
    }
    if note is not None:
        block["note"] = note
    return block


# ---------------------------------------------------------------------------
# Mediation — the per-record egress check (M2)
# ---------------------------------------------------------------------------
#
# WHY A NEW CHOKEPOINT HAD TO BE BUILT. Egress was fragmented across three
# dispatchers in services/writeback.py with three different policies:
# ``writeback()`` never called guard_check at all, ``governed_writeback()``
# gated only MeatyWiki, and ``approve_and_dispatch()`` gated only three of six
# targets. ``guard_check`` itself operates on aggregate run-level context and
# structurally cannot say "this record is blocked, allow the others". So
# per-record enforcement needed a new primitive rather than an extension of an
# existing one.
#
# TWO LAYERS, AND ONLY ONE OF THEM IS THE CONTROL.
#
# PRIMARY — ``mediate_egress`` called on RAW LOADED RECORDS at each payload
# constructor, before the record is flattened into an untyped dict. This is the
# real control and the only one that sees the whole record.
#
# BACKSTOP — ``assert_payload_mediated`` scanning an outgoing transport payload
# for taint markers. This is deliberately NOT sufficient on its own: it inspects
# a POST-PROJECTION payload, and DEF-5 records that run-export and the catalog
# both project through hand-listed key allowlists that silently drop unknown
# fields. A projection that strips ``clearance`` leaves the backstop with
# nothing to find. That is precisely why M5 must carry ``clearance.*`` through
# every allowlist, and why checking only at the transport would be a control a
# caller defeats by choosing a narrower projection.

#: Module-private capability sentinel. :class:`MediationClearance` refuses to
#: construct without it, so the token cannot be forged from outside this module
#: even though the dataclass itself is public. Mirrors the proof-of-possession
#: pattern in ``services/assertion_report_use.py``'s ``_VerificationAttestation``.
_MEDIATION_SENTINEL = object()


class ClearanceDenied(RFError):
    """A record blocked for the requested scope, or an unmediated tainted payload.

    Carries ``GOVERNANCE`` so a CLI surfaces it as a policy refusal (exit 3)
    rather than a crash — this is a decision, not a failure.
    """

    exit_code: ExitCode = ExitCode.GOVERNANCE


@dataclass(frozen=True)
class MediationClearance:
    """Proof that :func:`mediate_egress` ran and every record cleared.

    Unforgeable by construction: ``__post_init__`` refuses any instance not
    carrying the module-private sentinel, so a caller cannot fabricate the token
    to satisfy a transport that demands one. Carries no payload and no record
    data — it attests that a check happened for a specific (scope, target), and
    nothing more.
    """

    target_scope: str
    target: str
    record_count: int
    _sentinel: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._sentinel is not _MEDIATION_SENTINEL:
            raise ClearanceDenied(
                "MediationClearance cannot be constructed directly — it is proof "
                "that clearance.mediate_egress() ran. Call mediate_egress() and "
                "use the token it returns."
            )


@dataclass(frozen=True)
class MediatedPayload:
    """An outgoing transport payload plus proof its records were mediated.

    Wrapping requires a genuine :class:`MediationClearance`, so a caller cannot
    mark an unchecked payload as checked.
    """

    payload: dict[str, Any]
    clearance: MediationClearance

    def __post_init__(self) -> None:
        if not isinstance(self.clearance, MediationClearance):
            raise ClearanceDenied(
                "MediatedPayload requires a MediationClearance from mediate_egress()"
            )

    def unwrap(self) -> dict[str, Any]:
        return self.payload


def _blocked_scopes_of(record: Mapping[str, Any]) -> tuple[frozenset[str], bool]:
    """Return (blocked scopes, stamp_present) for one record.

    ``stamp_present`` is False when the record carries no usable taint block.
    The caller decides what absence means — for a governed kind it means
    refused, which is the opposite of this repo's prevailing fail-open habit and
    is deliberate: a stamp dropped by a projection allowlist must never read as
    "cleared".

    An EMPTY ``blocked_scopes`` is ALSO treated as no-usable-stamp
    (clearance-gates M3 CHANGES_REQUESTED B1-4 review, finding B3). Earlier,
    ``[]`` here was read as "explicitly unrestricted" (see
    ``schemas/clearance_taint.schema.yaml``'s own — now stale — description
    of that state, and ``services/governance.py`` rule 9's on-disk
    monotonicity guard, which was believed sufficient to gate it). That is
    insufficient: this function inspects whatever mapping sits at
    ``record["clearance"]`` at READ time, in-process, and nothing stops a
    caller from emptying an existing stamp's list a moment before mediation
    (e.g. mutating a :class:`~research_foundry.services.attribution_fetch.
    ClearedProviderFetchResult`'s ``clearance`` dict in place) — rule 9
    governs on-disk agent WRITES, not this in-memory window, so it provides
    no protection here at all. Treating ``[]`` identically to the malformed
    case closes that gap: a governed kind now requires a genuinely
    NON-EMPTY ``blocked_scopes`` to be read as stamped.
    """

    raw = record.get(TAINT_KEY) if isinstance(record, Mapping) else None
    if not isinstance(raw, Mapping):
        return frozenset(), False
    scopes = raw.get(BLOCKED_SCOPES_KEY)
    if not isinstance(scopes, (list, tuple, set, frozenset)):
        # Present but malformed. Treated as no-usable-stamp so a governed record
        # is refused rather than silently read as unrestricted.
        return frozenset(), False
    resolved = frozenset(str(s) for s in scopes)
    if not resolved:
        # Empty is ALSO no-usable-stamp — see the docstring above (B3).
        return frozenset(), False
    return resolved, True


def mediate_egress(
    records: Iterable[Mapping[str, Any]],
    *,
    kind: str,
    target_scope: str,
    target: str,
    paths: FoundryPaths | None = None,
    registry: GateRegistry | None = None,
) -> MediationClearance:
    """Fail-closed per-record clearance check. Returns proof, or raises.

    Pass **raw loaded records**, never an already-projected payload dict:
    checking after projection trivially passes anything the projection stripped.

    ``kind`` is explicit rather than inferred. An inferred kind that failed to
    match would silently skip the check — the exact failure mode this design
    refuses — so the caller must name the kind it is mediating, and one call
    handles one kind.

    Raises :class:`ClearanceDenied` when, for a governed *kind*:

    * any record's ``blocked_scopes`` contains *target_scope*; or
    * any record has an absent or malformed taint stamp; or
    * any record blocks ``acquisition`` at all — a record that should never have
      been fetched must not travel anywhere, regardless of the scope asked
      about. Defence-in-depth for a case that cannot occur while no DEF-2
      provider adapter exists.

    Reads only each record's own durable stamp. It never consults the registry's
    current gate ``state`` to decide, which is what makes a later gate closure
    or a deleted posture declaration unable to retroactively release a record.
    The registry is consulted only to resolve which kinds are governed.
    """

    if target_scope not in BLOCKING_SCOPES:
        raise ClearanceConfigError(
            f"Unknown target_scope {target_scope!r}; expected one of {sorted(BLOCKING_SCOPES)}"
        )

    reg = registry or load_registry(paths=paths)
    materialized = list(records)

    if not reg.governs_kind(kind):
        # Not a governed kind — no stamp is expected and absence is not a
        # finding. This is the backward-compatibility mechanism: every record
        # kind predating clearance is structurally incapable of carrying a
        # stamp, so demanding one would break correctness, not add safety.
        return MediationClearance(
            target_scope=target_scope,
            target=target,
            record_count=len(materialized),
            _sentinel=_MEDIATION_SENTINEL,
        )

    for index, record in enumerate(materialized):
        scopes, stamped = _blocked_scopes_of(record)
        if not stamped:
            raise ClearanceDenied(
                f"{kind}[{index}] carries no usable clearance stamp and {kind} is a "
                f"governed kind, so it cannot leave via {target!r}. An absent or "
                "malformed stamp is treated as blocked, never as cleared — a stamp "
                "dropped by a projection allowlist must not read as permission."
            )
        if "acquisition" in scopes:
            raise ClearanceDenied(
                f"{kind}[{index}] blocks the 'acquisition' scope, meaning it should "
                f"never have been acquired at all; refusing egress to {target!r} "
                f"regardless of the requested scope {target_scope!r}."
            )
        if target_scope in scopes:
            raise ClearanceDenied(
                f"{kind}[{index}] blocks scope {target_scope!r}; refusing egress to "
                f"{target!r}. Blocked scopes: {sorted(scopes)}."
            )

    return MediationClearance(
        target_scope=target_scope,
        target=target,
        record_count=len(materialized),
        _sentinel=_MEDIATION_SENTINEL,
    )


def _walk_for_taint(node: Any, *, _depth: int = 0) -> list[frozenset[str]]:
    """Collect every non-empty ``blocked_scopes`` set reachable inside *node*.

    Depth-bounded so a pathological or self-referential structure cannot hang
    the transport path.
    """

    if _depth > 12:
        return []
    found: list[frozenset[str]] = []
    if isinstance(node, Mapping):
        scopes, stamped = _blocked_scopes_of(node)
        if stamped and scopes:
            found.append(scopes)
        for value in node.values():
            found.extend(_walk_for_taint(value, _depth=_depth + 1))
    elif isinstance(node, (list, tuple)):
        for value in node:
            found.extend(_walk_for_taint(value, _depth=_depth + 1))
    return found


def assert_payload_mediated(payload: Any, *, target: str) -> dict[str, Any]:
    """Transport BACKSTOP. Unwrap a payload, refusing unproven tainted content.

    Accepts either a :class:`MediatedPayload` (proof present — returned
    unwrapped) or a bare dict. A bare dict is allowed **only** when it carries
    no visible taint marker, which keeps every pre-existing untainted call site
    working unchanged while making it impossible to ship a record whose stamp
    survived projection without having been mediated.

    This is NOT the primary control and must not be relied on as one: it sees a
    post-projection payload, so a projection that dropped ``clearance`` leaves
    nothing here to catch. ``mediate_egress`` on raw records upstream is the
    control; this catches the case where that call was forgotten.
    """

    if isinstance(payload, MediatedPayload):
        return payload.unwrap()
    tainted = _walk_for_taint(payload)
    if tainted:
        union = sorted({s for group in tainted for s in group})
        raise ClearanceDenied(
            f"Refusing to transmit to {target!r}: payload carries {len(tainted)} "
            f"clearance-stamped record(s) with blocked scope(s) {union} but no proof "
            "of mediation. Call clearance.mediate_egress() on the raw records and "
            "wrap the payload in a MediatedPayload."
        )
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "BLOCKED_SCOPES_KEY",
    "BLOCKING_SCOPES",
    "GATE_STATES",
    "POSTURE_VALUES",
    "REGISTRY_FILENAME",
    "TAINT_KEY",
    "ClearanceConfigError",
    "ClearanceDenied",
    "Gate",
    "GateRegistry",
    "MediatedPayload",
    "MediationClearance",
    "assert_payload_mediated",
    "load_registry",
    "mediate_egress",
    "stamp_taint",
    "summarize",
]
