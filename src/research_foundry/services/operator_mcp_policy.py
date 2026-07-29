"""Operator MCP policy: identity, sensitivity, guard/preflight ordering, and
confirmation binding (research-foundry-operator-mcp-v1 P1, OPM-1.2/1.3).

This module is the SOLE owner of:

* the closed operation-kind/tool-name/target-kind enumerations (mirrored
  from ``schemas/operator_mcp_operation.schema.yaml`` -- kept in sync by
  ``tests/unit/test_operator_mcp_policy.py``'s schema round-trip check);
* trusted local actor/workspace identity resolution (OPM-OQ-1): an explicit
  ``foundry.operator_mcp.identity`` config block, never a caller-supplied
  workspace, never a request-body default;
* the FIXED policy check order (decisions-block invariant, this plan's
  instructions): ``capability -> RBAC -> audit-health -> guard -> preflight
  -> confirmation binding`` -- :func:`evaluate_policy` runs the first five
  stages (used by the ``operation.preflight`` mint tool AND by every
  execute-time re-validation); :func:`authorize_operation` adds the sixth
  (confirmation binding), used only at execute time;
* confirmation minting/verification/consumption (OPM-OQ-2/3): a five-minute
  TTL, opaque single-use token bound to actor/workspace/sensitivity/
  operation/canonical-input-digest/idempotency-key/policy-snapshot/targets,
  with exact replay recognized as a distinct, non-error OUTCOME
  (:attr:`ConfirmationVerification.outcome` ``"exact_replay"``) that a
  caller uses to route to the PRIOR receipt -- but the underlying
  `PolicyDecision` for that outcome is NEVER `allowed=True`, on EITHER
  :func:`verify_confirmation` or :func:`authorize_operation` (security-
  review round 2, finding NEW-1, superseding round 1's C1 fix, which left
  the two functions disagreeing about whether a replay may proceed -- that
  disagreement was itself the bug). See the "EXACT REPLAY IS STRUCTURALLY
  NON-ACCEPTING" paragraph below;
* the bounded, redacted error-envelope builder (:func:`build_error`), whose
  ``message`` text is drawn ONLY from the closed :data:`_SAFE_MESSAGES`
  table -- never an f-string embedding caller-supplied VALUES or an
  exception's own text. (`_check_preflight`'s internal `detail` string does
  f-string a *closed enum member name* -- never caller input; see
  :func:`_check_preflight`'s docstring, finding L6.)

No effect adapter, AgentJob attempt, or MCP server exists in this module
(P1 scope note, decisions-block section "Quality gate": "no effect adapter
or MCP server exists yet"). :mod:`operator_operation_service` (P2) is the
durable-persistence owner that will call the functions here; this module
never touches disk itself except through the read-only
:func:`research_foundry.services.governance.guard_check`/
:func:`research_foundry.services.audit_service.get_health_state`/
:func:`research_foundry.services.audit_service.health_check`
calls it reuses (invariant: REUSE governance/audit primitives, never fork
them). Finding M6 (reopened and FIXED at security-review round 2, finding
NEW-3 -- see :func:`_check_audit_health`'s own comment): round 1's
wontfix rested on a false premise ("probing would brick every fresh
workspace"). `audit_service.health_check` is a cheap, idempotent,
never-raising write-then-read probe already imported into this module; P1
now probes ON DEMAND exactly once per workspace (whenever the persisted
state has never been probed) instead of assuming a never-probed store is
healthy forever. A workspace whose probe genuinely fails is now correctly
denied; a healthy workspace (the overwhelmingly common case) self-heals on
its own first mutating call with no separate bootstrap step required.

**EXACT REPLAY IS STRUCTURALLY NON-ACCEPTING (security-review round 2,
finding NEW-1 -- supersedes round 1's C1 fix)**: an exact replay -- an
already-``consumed``, still bound-matching, still-unexpired confirmation --
is denied by BOTH :func:`verify_confirmation` AND :func:`authorize_operation`
with an IDENTICAL (dataclass-``==``-equal) ``PolicyDecision(False,
"confirmation", "confirmation_replayed", retryable=False)``. Neither
function EVER returns ``allowed=True`` for a replay, regardless of which one
a caller invokes -- the safety property holds by SHAPE, not by which entry
point happens to be called or whether a docstring is read.
:attr:`ConfirmationVerification.outcome` ``"exact_replay"`` remains the
ONLY signal distinguishing "this exact request already executed" from every
other denial reason; it exists so a caller that reaches this state (always
via `authorize_operation`'s `confirmation_replayed` denial -- which has, by
construction, already passed stages 1-5: capability, RBAC, audit-health,
guard, preflight) can look up and return the PRIOR receipt from the
confirmation record it already holds (`consumed_at`/`consumed_by_operation_id`)
instead of a generic error, WITHOUT that signal ever being readable as
`allowed=True`.

Round 1's fix relocated the bug rather than closing it: it made
`authorize_operation` deny correctly but left `verify_confirmation` itself
returning `PolicyDecision(True, "confirmation")` for a replay, and then
*instructed* callers needing the replay distinction to call
`verify_confirmation` directly -- a function that runs ONLY the confirmation
stage, so a P2 author following that instruction and reading
`.decision.allowed` would execute a replay having skipped capability, RBAC,
the H3 cross-workspace gate, audit-health, the H7 ceiling gate, and
preflight. That instruction is RETRACTED: `verify_confirmation` MUST NEVER
be called directly by P2 or any execute-time caller to make an authorization
decision -- `authorize_operation` is the ONLY sanctioned execute-time entry
point. `verify_confirmation` remains exported because `authorize_operation`
and this module's own test suite call it directly to exercise each denial
branch in isolation; it is not, on its own, a caller-facing authorization
API.

**No permissive defaults on governed fields (H2/H3/H7)**: `effective_sensitivity`
and `sensitivity_ceiling` have no default and are validated in
`PolicyContext.__post_init__` against :data:`SENSITIVITY_LEVELS` --
constructing a context with an unknown/omitted-looking label is impossible,
not merely discouraged. `resolved_target_workspaces` is likewise validated
to supply exactly one entry (a real workspace id, or `None` meaning
"could not be resolved") per declared target whenever `targets` is
non-empty -- there is no default/omitted-means-skip cross-workspace gate
(the prior `requested_workspace_id: str | None = None` field this replaces
was exactly that footgun and has been removed).

**One denial shape for every post-lookup no-existence-leak case (H6)**:
`identity_denied` is reserved STRICTLY for a wholly missing/unresolved
identity (pre-lookup). A target whose resolved owning workspace differs
from the identity's own workspace, a target above `sensitivity_ceiling`,
and a target that could not be resolved at all (`None`) are ALL denied with
the SAME `not_found` reason code, the SAME `_SAFE_MESSAGES["not_found"]`
text, and `retryable=False` -- never a distinguishing message. See
`schemas/operator_mcp_error.schema.yaml`'s updated description.

**Canonicalization hardening (L4, hardened at NEW-8)**: `canonical_json()`
passes `allow_nan=False` to `json.dumps` -- `NaN`/`Infinity` in a canonical
field would otherwise silently produce non-JSON text no downstream reader
could reproduce. `PolicyContext.__post_init__` rejects this MUCH earlier,
at construction time (finding H8, hardened NEW-8): `input_payload` must be
an actual `Mapping` (not merely something `_is_json_primitive`-shaped -- a
bare `str`/`list` passes that recursive check but `canonical_payload()`'s
`dict(self.input_payload)` would then raise), and every nested float must
be finite (`math.isfinite`) -- a `PolicyContext` holding NaN/Infinity or a
non-`Mapping` payload can no longer be constructed at all, which closes the
gap where `mint_confirmation` (which returns `ConfirmationIssued`, not a
`PolicyDecision`, and therefore cannot participate in the H8
exception-to-`PolicyDecision` boundary the other three entry points use)
could raise a raw, uncaught exception from deep inside `ctx.canonical_digest()`.
There is deliberately NO Unicode normalization (e.g. NFC folding) anywhere
in the canonicalization path -- two strings that are visually identical but
differ in Unicode form produce DIFFERENT digests today (fails closed, never
silently unifies two distinct requests). State this explicitly so a future
change does not add normalization and silently change every existing
digest without a schema version bump.

**Clock-injection seam (M2)**: every `now: datetime | None = None` keyword
parameter in this module (`mint_confirmation`, `verify_confirmation`,
`consume_confirmation`, `authorize_operation`) is a TEST-ONLY seam for
deterministic TTL/expiry tests. P2/P5 MUST NEVER thread a caller- or
request-supplied timestamp through it -- doing so would let a caller forge
`issued_at`/`expires_at` or roll back the effective wall clock and defeat
every TTL check in this module. Production call sites always pass `now=None`.

**DURABLE CONSUMPTION IS A COMPARE-AND-SWAP (DUR-1, binding on P2)**:
`consume_confirmation` in this module is a PURE function -- it returns a
new dict (or `None` on a failed precondition) and touches no disk. P1
freezes the durability property P2's real persistence layer MUST implement
around it, verbatim:

    Consumption is a compare-and-swap on `status` from exactly `issued` to
    `consumed`, GUARDED BY THE SAME CLAMPED-EXPIRY CHECK `consume_confirmation`
    applies (`_record_expiry`: `min(expires_at, issued_at + CONFIRMATION_TTL)`,
    itself never later than `now` -- see finding NEW-7), performed in the
    same durable transaction as the operation-manifest write, under an
    exclusive single-writer lock (SQLite `BEGIN IMMEDIATE`, or `O_EXCL`
    create-then-atomic-rename). A CAS that observes any status other than
    `issued`, OR whose clamped expiry has already passed at commit time,
    MUST route to the exact-replay / idempotency-conflict / expired path and
    MUST NOT execute.

**NEW-10 (round 2)**: `WHERE status = 'issued'` alone is NOT the frozen
predicate above -- it is only the status half. A P2 implementation
following just that clause would consume an EXPIRED-but-still-`"issued"`
token and still satisfy a literal reading of round 1's text. The expiry
predicate is binding and MUST be folded into the SAME compare-and-swap,
not checked separately (a separate check reopens the TOCTOU window DUR-1
exists to close).

A P2 implementation that reads a confirmation record, does other work, and
only then writes `status="consumed"` (read-then-write, not a real CAS) can
pass every test in this phase while still permitting two concurrent callers
presenting the same token to both observe `status == "issued"` and both
win. This paragraph is the frozen acceptance bar for P2's closeout.

**Serve-extra import boundary**: :class:`~research_foundry.api.auth.provider.AuthIdentity`
is imported only under ``TYPE_CHECKING`` for annotations and lazily inside
:func:`resolve_operator_identity` at call time -- mirrors
``agent_job_service.py``'s own documented reason (``api.auth.provider``
module-imports ``starlette``, a ``[serve]``-tier dependency, so a
module-level import here would make this policy module -- usable from a
plain local stdio process with no HTTP server running -- hard-require the
``serve`` extra just to import).

**Zero overlap with the read-only Knowledge MCP** (decisions-block section
0, invariant 6): the eight ``rf-knowledge-mcp`` tool names (``search``,
``fetch``, ``rf_search``, ``rf_fetch``, ``rf_source_get``,
``rf_assertion_get``, ``rf_report_get``, ``rf_run_get`` --
:data:`research_foundry.knowledge_mcp.registry.TOOL_NAMES`) never appear in
:data:`OPERATION_KINDS`/:data:`TOOL_NAMES` below; the disjointness is
asserted at test time against the Knowledge MCP registry's own tuple (see
``schemas/operator_mcp_operation.schema.yaml``'s description for the full
inventory). This module never imports :mod:`research_foundry.knowledge_mcp`
or :mod:`research_foundry.services.knowledge_access`.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import logging
import math
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Literal, Mapping

from research_foundry.config import FoundryConfig
from research_foundry.errors import ExitCode
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service, governance
from research_foundry.services.export_service import SENSITIVITY_ORDER

if TYPE_CHECKING:
    from research_foundry.api.auth.provider import AuthIdentity

# NEW-13: internal_error was previously silent (zero telemetry) -- a
# malformed config/governance.yaml or a database error becomes a clean
# `PolicyDecision(..., "internal_error", retryable=True)` for the caller
# (correct, AC OPM-7), but a genuine bug hidden behind that denial with NO
# log line was invisible operationally, plus it invites a retry loop on a
# deterministic failure with nothing to page on. `_logger.warning` below
# logs ONLY the failing stage and the exception's TYPE NAME -- never
# `str(exc)`, which could embed caller-influenced data (e.g. a value read
# back out of a malformed YAML file).
_logger = logging.getLogger(__name__)

__all__ = [
    "OPERATION_KINDS",
    "PREFLIGHT_TOOL_NAME",
    "TOOL_NAMES",
    "TARGET_KINDS",
    "SENSITIVITY_LEVELS",
    "CONFIRMATION_NOT_REQUIRED_KINDS",
    "CLOSED_REASON_CODES",
    "CONFIRMATION_TTL",
    "TargetRef",
    "PolicyContext",
    "PolicyDecision",
    "ConfirmationIssued",
    "ConfirmationVerification",
    "resolve_operator_identity",
    "resolve_effective_sensitivity",
    "check_tool_name",
    "evaluate_policy",
    "authorize_operation",
    "mint_confirmation",
    "verify_confirmation",
    "consume_confirmation",
    "build_error",
]

# ---------------------------------------------------------------------------
# Closed enumerations -- mirror schemas/operator_mcp_operation.schema.yaml
# ---------------------------------------------------------------------------

#: The 13 closed operation kinds (PRD section 6.1 minus the `operation.preflight`
#: meta-tool itself). No wildcard, no `execute`/`shell`/`file`/`url.fetch`/
#: `provider.run`/`adapter.run`/`writeback.execute`/`agent-job.accept` member
#: exists or will be added without a schema version bump.
OPERATION_KINDS: tuple[str, ...] = (
    "run.plan",
    "swarm.start",
    "job.status",
    "job.cancel",
    "job.resume",
    "external_report.import",
    "source.ingest",
    "run.extract",
    "run.claim_map",
    "run.synthesize",
    "run.verify",
    "run.bundle",
    "writeback.preview",
)

#: The meta tool that previews/mints a confirmation for one of the 13 kinds
#: above; never itself a value of `operation_kind`.
PREFLIGHT_TOOL_NAME = "operation.preflight"

#: Tool names = operation kinds + the preflight meta tool (14 total).
#: Operator MCP has no tool-name namespace distinct from `operation_kind`.
TOOL_NAMES: tuple[str, ...] = OPERATION_KINDS + (PREFLIGHT_TOOL_NAME,)

#: The only concrete kind that is a bounded lifecycle READ with no
#: confirmation requirement and no canonical effect (PRD section 6.1 table).
CONFIRMATION_NOT_REQUIRED_KINDS: frozenset[str] = frozenset({"job.status"})

#: Closed target-kind vocabulary (mirrors `$defs.target_ref` in the operation
#: schema).
TARGET_KINDS: frozenset[str] = frozenset(
    {
        "run",
        "source",
        "extraction_card",
        "claim_ledger",
        "report_draft",
        "report_final",
        "evidence_bundle",
        "import_packet",
        "agent_job",
        "writeback_preview",
        "verification",
    }
)

#: Four-level sensitivity vocabulary, explicit tuple (not derived from dict
#: iteration order) so this module's contract is decoupled from
#: `export_service.SENSITIVITY_ORDER`'s own internal representation --
#: kept in sync by a round-trip test.
SENSITIVITY_LEVELS: tuple[str, ...] = ("public", "personal", "work_sensitive", "client_sensitive")

#: Closed reason-code enum -- mirrors schemas/operator_mcp_error.schema.yaml.
CLOSED_REASON_CODES: frozenset[str] = frozenset(
    {
        "identity_denied",
        "rbac_denied",
        "audit_unhealthy",
        "guard_blocked",
        "guard_review_required",
        "preflight_failed",
        "operation_unknown",
        "tool_unknown",
        "target_invalid",
        "confirmation_missing",
        "confirmation_expired",
        "confirmation_replayed",
        "confirmation_mismatch",
        "idempotency_conflict",
        "not_found",
        "payload_too_large",
        "internal_error",
    }
)

#: OPM-OQ-2 default: five-minute confirmation TTL.
CONFIRMATION_TTL: timedelta = timedelta(minutes=5)

# Envelope bounds (mirror schemas/operator_mcp_operation.schema.yaml's
# SEVEN declared bounds: `targets` maxItems 20, `input_payload`
# maxProperties 32, `target_ref` maxLength 256 + pattern, `idempotency_key`
# maxLength 128 + pattern, `policy_snapshot_version` maxLength 64).
# Enforced here in `_check_capability`, not via `SchemaRegistry` (finding
# M1) -- P1 constructs `PolicyContext` directly from already-typed Python
# values (no raw request envelope exists yet in this repository). ALL
# SEVEN bounds are enforced below, in code, as of the round-2 fix cycle
# (finding NEW-2): round 1 enforced only the two counts below and left the
# other five as schema-only decoration while this comment falsely called
# that PARTIAL enforcement "authoritative" -- an unbounded/path-shaped
# `target_ref` (e.g. `"../../../etc/passwd"`) or an empty `idempotency_key`
# passed every stage under that partial enforcement. P5's transport
# boundary MAY additionally schema-validate the raw wire envelope before
# ever constructing a `PolicyContext`, but this in-code enforcement does
# not depend on that happening and is what actually protects every caller
# today.
_MAX_TARGETS = 20
_MAX_INPUT_PAYLOAD_PROPERTIES = 32
_TARGET_REF_MAX_LENGTH = 256
_TARGET_REF_PATTERN = re.compile(r"^[A-Za-z0-9_\-:.]+$")
_IDEMPOTENCY_KEY_MAX_LENGTH = 128
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")
_POLICY_SNAPSHOT_VERSION_MAX_LENGTH = 64

# Stage-prerequisite target kinds per operation kind (the "preflight" stage
# below). Not an exhaustive service contract -- P3/P4 adapters own their own
# richer prerequisite checks once they exist; this is the generic, schema-
# level minimum this contract phase can freeze.
_REQUIRED_TARGET_KINDS: dict[str, frozenset[str]] = {
    "run.plan": frozenset(),
    "swarm.start": frozenset({"run"}),
    "job.status": frozenset({"agent_job"}),
    "job.cancel": frozenset({"agent_job"}),
    "job.resume": frozenset({"agent_job"}),
    "external_report.import": frozenset({"import_packet"}),
    "source.ingest": frozenset({"run"}),
    "run.extract": frozenset({"run"}),
    "run.claim_map": frozenset({"run", "extraction_card"}),
    "run.synthesize": frozenset({"run", "claim_ledger"}),
    "run.verify": frozenset({"run"}),
    "run.bundle": frozenset({"run", "verification"}),
    "writeback.preview": frozenset({"evidence_bundle"}),
}

# RBAC: mutating kinds require a "write-capable" role; the sole read kind
# (job.status) requires only SOME assigned role (mirrors rbac.py's
# viewer-has-zero-permissions convention: an empty roles tuple still denies).
_MUTATION_ROLES: frozenset[str] = frozenset({"owner", "admin", "researcher"})
_READ_ROLES: frozenset[str] = frozenset({"owner", "admin", "researcher", "reviewer", "viewer"})

_TRACEBACK_LIKE = re.compile(r'(?i)traceback|site-packages|File "[^"]*", line \d+')
_ERROR_MESSAGE_MAX = 300
_ERROR_DETAIL_MAX = 500

_IDENTITY_CONFIG_SECTION = "operator_mcp"
_IDENTITY_CONFIG_KEY = "identity"

_JSON_PRIMITIVE_MAX_DEPTH = 32


def _is_json_primitive(value: Any, *, _depth: int = 0) -> bool:
    """H8 construction-time guard: `True` iff `value` is composed entirely
    of JSON-primitive types (`None`/`bool`/`int`/`float`/`str`/`dict` with
    `str` keys/`list`), bounded to :data:`_JSON_PRIMITIVE_MAX_DEPTH` levels.

    Used by :meth:`PolicyContext.__post_init__` to reject a non-JSON-
    serializable (or pathologically deep) `input_payload` BEFORE it can ever
    reach `canonical_digest()` (which would otherwise raise `TypeError` on
    an arbitrary object, or `RecursionError` on unbounded nesting)."""

    if _depth > _JSON_PRIMITIVE_MAX_DEPTH:
        return False
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, float):
        # NEW-8(a): NaN/Infinity are Python floats but are NOT valid JSON
        # values -- reject them HERE (construction time) rather than
        # letting `canonical_json()`'s `allow_nan=False` raise deep inside
        # `canonical_digest()`, reachable UNCAUGHT from `mint_confirmation`
        # (which has no PolicyDecision-shaped H8 boundary of its own).
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(
            isinstance(k, str) and _is_json_primitive(v, _depth=_depth + 1) for k, v in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_is_json_primitive(v, _depth=_depth + 1) for v in value)
    return False


def _sensitivity_rank(label: str) -> int:
    """Rank lookup for `effective_sensitivity` (H7). Unknown labels rank
    `len(SENSITIVITY_ORDER)` -- STRICTER than every known level, mirroring
    `export_service.py`'s own `_UNKNOWN_SENSITIVITY` convention -- NEVER
    `-1`, which would make an unknown/malformed label the LOOSEST possible
    value and silently fail open. In normal operation this branch is
    unreachable (validated against :data:`SENSITIVITY_LEVELS` at
    `PolicyContext` construction) -- this is defense in depth, not the
    primary guard.

    NOT used for `sensitivity_ceiling` -- see :func:`_ceiling_rank` (finding
    NEW-6): the fail-closed direction is OPPOSITE for a ceiling."""

    return SENSITIVITY_ORDER.get(label, len(SENSITIVITY_ORDER))


def _ceiling_rank(label: str) -> int:
    """Rank lookup for `sensitivity_ceiling` (H7, hardened NEW-6).

    An unknown/malformed CEILING must rank BELOW every known level (`-1`),
    the OPPOSITE fail-closed direction from :func:`_sensitivity_rank`: an
    unknown `effective_sensitivity` must be treated as MORE restrictive
    (content), but an unknown `sensitivity_ceiling` must be treated as LESS
    permissive (clearance) -- ranking it `len(SENSITIVITY_ORDER)` (as the
    prior single shared helper did) would make an unknown/malformed ceiling
    the MAXIMUM possible clearance and silently permit everything. In
    normal operation this branch is unreachable (`sensitivity_ceiling` is
    validated against :data:`SENSITIVITY_LEVELS` at `PolicyContext`
    construction) -- this is defense in depth against a future drift
    between :data:`SENSITIVITY_LEVELS` and :data:`SENSITIVITY_ORDER`, not
    the primary guard."""

    return SENSITIVITY_ORDER.get(label, -1)


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetRef:
    """One closed target reference (mirrors `$defs.target_ref`)."""

    target_kind: str
    target_ref: str

    def to_dict(self) -> dict[str, str]:
        return {"target_kind": self.target_kind, "target_ref": self.target_ref}


@dataclass(frozen=True)
class PolicyContext:
    """Canonicalized operation-request context (mirrors
    `operator_mcp_operation.schema.yaml`).

    `resolved_target_workspaces` is the OWNING workspace of each element of
    `targets`, in the SAME order, resolved server-side (never caller-
    supplied) -- e.g. once P2+ performs a real object lookup, that result is
    threaded in here. `None` at a given position means "could not be
    resolved" (a genuinely absent target). H3 fix: whenever `targets` is
    non-empty, `resolved_target_workspaces` MUST supply exactly one entry
    per target -- there is no default/omitted-means-skip cross-workspace
    gate (this replaces the prior `requested_workspace_id: str | None =
    None` field, whose `None` meant "skip the check", a default workspace
    by another name). Every element that is `None` or differs from
    `identity.workspace_id` is denied with the SAME `not_found` reason code
    (H6) -- never a distinguishing message. It is intentionally NOT part of
    the canonical digest (it is a lookup-time authorization input, not a
    caller-supplied canonical field).

    `sensitivity_ceiling` is the caller's/workspace's resolved sensitivity
    clearance (H7); `evaluate_policy` denies with the SAME `not_found` shape
    when `effective_sensitivity`'s rank exceeds it. Also intentionally NOT
    part of the canonical digest, for the same lookup-time-input reason.

    `writeback_targets` is optional and meaningful only for
    `writeback.preview` -- it feeds `governance.GuardContext.writeback_targets`
    so the SAME `work_writeback_requires_review`/`intenttree_writeback_requires_review`/
    `arc_writeback_requires_review` guard rules apply here as everywhere else.
    `model_provider`/`source_sensitivities` are optional passthroughs to the
    SAME `GuardContext` fields, enabling the `no_work_sensitive_to_unapproved_provider`/
    `no_mixed_personal_work_bundle` block-severity rules to fire through this
    contract exactly as they do for run-level guard checks -- REUSE, not a
    fork, of `governance.guard_check`.
    """

    identity: "AuthIdentity | None"
    operation_kind: str
    idempotency_key: str
    effective_sensitivity: str
    sensitivity_ceiling: str
    targets: tuple[TargetRef, ...] = ()
    input_payload: Mapping[str, Any] = field(default_factory=dict)
    policy_snapshot_version: str = "policy-order-v1"
    resolved_target_workspaces: tuple[str | None, ...] = ()
    writeback_targets: tuple[str, ...] = ()
    model_provider: str | None = None
    source_sensitivities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # H2: no permissive default -- effective_sensitivity must be a real
        # member of the closed vocabulary, always. NEW-8(c): the message
        # names only the CLOSED vocabulary (safe, internal, never caller
        # data) -- it no longer echoes the caller-supplied value itself
        # (`got {value!r}`), which would have interpolated unredacted
        # caller-controlled data into an exception raised OUTSIDE every
        # H8 boundary (this dataclass's own __init__).
        if self.effective_sensitivity not in SENSITIVITY_LEVELS:
            raise ValueError(f"effective_sensitivity must be one of {SENSITIVITY_LEVELS!r}")
        # H7: sensitivity_ceiling is required and validated the same way.
        if self.sensitivity_ceiling not in SENSITIVITY_LEVELS:
            raise ValueError(f"sensitivity_ceiling must be one of {SENSITIVITY_LEVELS!r}")
        # H3: whenever any target is declared, its owning-workspace
        # resolution MUST be supplied (a real workspace id, or None for
        # "could not be resolved") -- no default/omitted-means-skip gate.
        if self.targets and len(self.resolved_target_workspaces) != len(self.targets):
            raise ValueError(
                "resolved_target_workspaces must supply exactly one owning-workspace "
                "entry (or None for an unresolved/absent target) per declared target "
                "-- there is no default/omitted-means-skip cross-workspace gate (H3)"
            )
        # NEW-8(b): input_payload must be an actual Mapping, not merely
        # something `_is_json_primitive`-shaped -- a bare `str`/`list`
        # passes that recursive primitive check (a `str` IS a JSON
        # primitive) but `canonical_payload()`'s `dict(self.input_payload)`
        # would then raise, uncaught, deep inside `canonical_digest()`.
        if not isinstance(self.input_payload, Mapping):
            raise ValueError("input_payload must be a Mapping (dict-like object)")
        # H8/NEW-8(a): input_payload must be JSON-primitive (finite floats
        # only) so canonical_digest() can never raise on caller-influenced
        # data.
        if not _is_json_primitive(self.input_payload):
            raise ValueError(
                "input_payload must be JSON-primitive (str/int/bool/None/dict/list/"
                "finite-float only, bounded depth)"
            )

    def canonical_payload(self) -> dict[str, Any]:
        """The exact payload `canonical_digest` hashes -- see
        `operator_mcp_operation.schema.yaml`'s canonicalization section.
        Excludes `resolved_target_workspaces` and `sensitivity_ceiling`
        (lookup-time authorization inputs, never caller-supplied canonical
        fields) and any wall-clock timestamp."""

        return {
            "operation_kind": self.operation_kind,
            "actor": {
                "user_id": self.identity.user_id if self.identity is not None else None,
                "workspace_id": self.identity.workspace_id if self.identity is not None else None,
                "roles": sorted(self.identity.roles) if self.identity is not None else [],
            },
            "idempotency_key": self.idempotency_key,
            "targets": [t.to_dict() for t in self.targets],
            "input_payload": dict(self.input_payload),
            "policy_snapshot_version": self.policy_snapshot_version,
            "effective_sensitivity": self.effective_sensitivity,
        }

    def canonical_json(self) -> str:
        # L4: allow_nan=False -- NaN/Infinity in a canonical field would
        # otherwise silently serialize to non-standard JSON text no
        # downstream reader (P2's durable store, a hash reproduction) could
        # reproduce; fail loudly instead.
        return json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )

    def canonical_digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolicyDecision:
    """Outcome of one policy stage or the full fixed-order evaluation.

    `stage` names the LAST stage evaluated -- one of `"capability"`,
    `"rbac"`, `"audit_health"`, `"guard"`, `"preflight"`, `"confirmation"`
    (an unexpected exception caught by the H8 boundary in `evaluate_policy`/
    `authorize_operation`/`verify_confirmation` is attributed to whichever
    of these stages was executing, never a synthetic seventh value).
    `reason_code` is `None` only when `allowed` is `True`; otherwise it is
    always a member of :data:`CLOSED_REASON_CODES`.
    """

    allowed: bool
    stage: str
    reason_code: str | None = None
    retryable: bool = False
    detail: str | None = None

    @property
    def denied(self) -> bool:
        return not self.allowed


@dataclass(frozen=True)
class ConfirmationIssued:
    """Result of :func:`mint_confirmation`.

    `token` is the RAW opaque token -- return to the caller exactly once;
    never persist it. `record` is a schema-valid
    `operator_mcp_confirmation` instance (status `"issued"`).
    """

    token: str
    record: dict[str, Any]


@dataclass(frozen=True)
class ConfirmationVerification:
    """Result of :func:`verify_confirmation`.

    `outcome` distinguishes the non-error "exact replay" case
    (decisions-block: "Exact replay returns the existing operation/receipt")
    from every denial case -- a caller that reaches this state (always via
    `authorize_operation`'s `confirmation_replayed` denial) routes
    `"exact_replay"` to the PRIOR terminal receipt rather than fabricate a
    new effect. `"error"` is the H8 exception-safety boundary: an
    unexpected internal failure while verifying, never propagated as a
    raised exception.

    **NEW-1 (round 2)**: `decision` for `outcome == "exact_replay"` is now
    `PolicyDecision(False, "confirmation", "confirmation_replayed",
    retryable=False)` -- IDENTICAL to what `authorize_operation` returns
    for the same case, never `allowed=True`. See the module docstring's
    "EXACT REPLAY IS STRUCTURALLY NON-ACCEPTING" paragraph. `outcome`
    remains the only field that distinguishes a replay from any other
    denial; `decision.allowed` alone can no longer be used (by anyone) to
    mistake a replay for a fresh accept.
    """

    outcome: Literal["accepted", "exact_replay", "expired", "mismatched", "missing", "error"]
    decision: PolicyDecision


# ---------------------------------------------------------------------------
# Identity resolution (OPM-OQ-1)
# ---------------------------------------------------------------------------


def resolve_operator_identity(
    paths: FoundryPaths | None = None, *, config: FoundryConfig | None = None
) -> "AuthIdentity | None":
    """Resolve the ONE trusted local operator identity (OPM-OQ-1).

    Reads `foundry.operator_mcp.identity` from `foundry.yaml`::

        foundry:
          operator_mcp:
            identity:
              user_id: alice
              workspace_id: default
              roles: [owner]

    Returns `None` when the block is absent or incomplete (missing
    `user_id`/`workspace_id`, or `roles` not a list) -- callers MUST treat
    `None` as "deny", never fall back to a caller-supplied or default
    workspace. There is no environment-variable or request-body override:
    this is the ONLY identity source for Operator MCP (contrast Knowledge
    MCP's `identity=None` "local trust" model -- Operator MCP mutates and
    therefore requires a real, configured identity).
    """

    resolved_paths = paths if paths is not None else FoundryPaths.discover()
    cfg = config if config is not None else FoundryConfig(paths=resolved_paths)
    foundry_block = cfg.foundry
    section = foundry_block.get(_IDENTITY_CONFIG_SECTION) if isinstance(foundry_block, dict) else None
    identity_cfg = section.get(_IDENTITY_CONFIG_KEY) if isinstance(section, dict) else None
    if not isinstance(identity_cfg, dict):
        return None

    user_id = identity_cfg.get("user_id")
    workspace_id = identity_cfg.get("workspace_id")
    roles = identity_cfg.get("roles")
    if not user_id or not isinstance(user_id, str):
        return None
    if not workspace_id or not isinstance(workspace_id, str):
        return None
    if not isinstance(roles, list):
        return None

    from research_foundry.api.auth.provider import AuthIdentity  # lazy: see module docstring

    return AuthIdentity(
        user_id=user_id, workspace_id=workspace_id, roles=tuple(str(r) for r in roles)
    )


def resolve_effective_sensitivity(*sensitivities: str | None) -> str:
    """Strictest (highest-rank) value across every supplied sensitivity.

    Unknown labels are treated as stricter than every known level
    (fail-closed, mirrors `export_service.SENSITIVITY_ORDER`'s own
    `_UNKNOWN_SENSITIVITY` convention).

    NEW-4 fix (round 2): returns the STRICTEST label
    (:data:`SENSITIVITY_LEVELS`'s last member), never `"public"`, when no
    non-empty sensitivity is supplied. Empty input is the FAILED-LOOKUP
    case -- every upstream sensitivity source came back `None`/`""`/absent
    -- and this function PRODUCES the value `PolicyContext.effective_sensitivity`
    consumes; resolving a failed lookup to the LOOSEST possible label here
    would silently reintroduce, in the producer, the exact permissive
    default H2 removed from the consumer (`PolicyContext.__post_init__`,
    which merely validates whatever value it is handed and cannot tell a
    genuine "public" apart from a failed lookup that resolved to "public").
    """

    values = [s for s in sensitivities if s]
    if not values:
        return SENSITIVITY_LEVELS[-1]
    if any(s not in SENSITIVITY_ORDER for s in values):
        return SENSITIVITY_LEVELS[-1]
    return max(values, key=_sensitivity_rank)


# ---------------------------------------------------------------------------
# Fixed-order policy stages (invariant 2: capability -> rbac -> audit_health
# -> guard -> preflight -> confirmation)
# ---------------------------------------------------------------------------


def check_tool_name(tool: str) -> PolicyDecision:
    """Closed tool-name check (AC OPM-4).

    FROZEN P5 OBLIGATION (finding L1): this function has no caller anywhere
    in this repository today -- P1 is a contract-only phase with no
    transport. P5's stdio server boundary MUST call this (or an equivalent
    schema-level check) on every inbound tool name BEFORE any operation-
    kind-specific check runs; shipping P5 without wiring it regresses this
    contract. Separately, `_check_capability` (the first `evaluate_policy`
    stage) necessarily runs before identity is established, so an
    unauthenticated caller can already distinguish `operation_unknown`/
    `target_invalid` from `identity_denied` -- this is an accepted,
    documented ordering (schema-shape rejection precedes authorization),
    not a fail-open gap.
    """

    if tool not in TOOL_NAMES:
        return PolicyDecision(False, "capability", "tool_unknown", retryable=False)
    return PolicyDecision(True, "capability")


def _check_capability(ctx: PolicyContext, _paths: FoundryPaths) -> PolicyDecision:
    if ctx.operation_kind not in OPERATION_KINDS:
        return PolicyDecision(False, "capability", "operation_unknown", retryable=False)
    # M1: bounded envelope, enforced here (not merely by tests/schema).
    if len(ctx.targets) > _MAX_TARGETS or len(ctx.input_payload) > _MAX_INPUT_PAYLOAD_PROPERTIES:
        return PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    # NEW-2: the remaining 5 declared bounds -- idempotency_key and
    # policy_snapshot_version shape/length are envelope-level (not a
    # per-target concern), so they share `payload_too_large`, the closed
    # reason code closest in meaning ("this envelope does not conform to
    # its configured bounds") among the 17 frozen members; adding a new
    # reason code is a schema version bump this contract phase does not take.
    if (
        not ctx.idempotency_key
        or len(ctx.idempotency_key) > _IDEMPOTENCY_KEY_MAX_LENGTH
        or not _IDEMPOTENCY_KEY_PATTERN.match(ctx.idempotency_key)
    ):
        return PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    if (
        not ctx.policy_snapshot_version
        or len(ctx.policy_snapshot_version) > _POLICY_SNAPSHOT_VERSION_MAX_LENGTH
    ):
        return PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    for target in ctx.targets:
        if target.target_kind not in TARGET_KINDS:
            return PolicyDecision(False, "capability", "target_invalid", retryable=False)
        # NEW-2: target_ref maxLength 256 + pattern -- e.g. rejects a raw
        # filesystem path (`"../../../etc/passwd"`) or an oversized ref
        # that round 1 let pass every stage and reach a minted confirmation.
        if (
            not target.target_ref
            or len(target.target_ref) > _TARGET_REF_MAX_LENGTH
            or not _TARGET_REF_PATTERN.match(target.target_ref)
        ):
            return PolicyDecision(False, "capability", "target_invalid", retryable=False)
    return PolicyDecision(True, "capability")


def _check_identity_and_rbac(ctx: PolicyContext, _paths: FoundryPaths) -> PolicyDecision:
    identity = ctx.identity
    if identity is None or not identity.user_id or not identity.workspace_id:
        return PolicyDecision(False, "rbac", "identity_denied", retryable=False)

    # H3/H6: every declared target's resolved owning workspace MUST match
    # the trusted identity's own workspace. A mismatch, or a target that
    # could not be resolved at all (None -- "genuinely absent"), collapses
    # to the SAME `not_found` denial as a missing reference -- never the
    # `identity_denied` code (reserved strictly for a wholly missing
    # identity) and never a distinguishing message (no-existence-leak).
    for owning_workspace in ctx.resolved_target_workspaces:
        if owning_workspace is None or owning_workspace != identity.workspace_id:
            return PolicyDecision(False, "rbac", "not_found", retryable=False)

    required_roles = _READ_ROLES if ctx.operation_kind in CONFIRMATION_NOT_REQUIRED_KINDS else _MUTATION_ROLES
    if not set(identity.roles) & required_roles:
        return PolicyDecision(False, "rbac", "rbac_denied", retryable=False)
    return PolicyDecision(True, "rbac")


def _check_audit_health(ctx: PolicyContext, paths: FoundryPaths) -> PolicyDecision:
    # OPM-OQ-6: audit-health only gates operations that will mint a
    # confirmation (privileged/mutating). The sole read kind never mints
    # one and is never gated on audit health.
    if ctx.operation_kind in CONFIRMATION_NOT_REQUIRED_KINDS:
        return PolicyDecision(True, "audit_health")
    # M6 REOPENED and FIXED at security-review round 2 (finding NEW-3):
    # round 1's wontfix rested on a false premise. `audit_service.health_check`
    # is a cheap, idempotent, never-raising write-then-read probe already
    # imported into this module (not a fork). PROBE ON DEMAND exactly once
    # per workspace: read the persisted state first (cheap); only when it
    # has NEVER been probed (`last_probe_at is None`) run a REAL live probe
    # and use ITS result instead of assuming healthy. This closes the
    # fail-open the M6 wontfix rested on ("never-probed == healthy forever")
    # without the wontfix's feared bricking -- a healthy workspace (the
    # overwhelmingly common case) self-heals silently on its own first
    # mutating call; a genuinely degraded audit store is now caught on that
    # SAME first call instead of never.
    state = audit_service.get_health_state(paths)
    if state.last_probe_at is None:
        state = audit_service.health_check(paths)
    if not state.healthy:
        return PolicyDecision(False, "audit_health", "audit_unhealthy", retryable=True)
    return PolicyDecision(True, "audit_health")


def _check_guard(ctx: PolicyContext, paths: FoundryPaths) -> PolicyDecision:
    # H7: above-ceiling content is denied with the SAME `not_found` shape
    # as a wrong-workspace/absent target (H6) -- checked first, and cheaply,
    # before touching disk via governance.guard_check.
    if _sensitivity_rank(ctx.effective_sensitivity) > _ceiling_rank(ctx.sensitivity_ceiling):
        return PolicyDecision(False, "guard", "not_found", retryable=False)

    guard_ctx = governance.GuardContext(
        sensitivity=ctx.effective_sensitivity,
        writeback_targets=ctx.writeback_targets,
        model_provider=ctx.model_provider,
        source_sensitivities=ctx.source_sensitivities,
    )
    result = governance.guard_check(guard_ctx, paths=paths)
    if result.passed:
        return PolicyDecision(True, "guard")
    # M5: governance `rule_id` (e.g. `no_work_sensitive_to_unapproved_provider`)
    # is internal-only -- it discloses effective sensitivity/source-set
    # composition and MUST NOT reach `build_error`'s output. `detail` is
    # therefore left `None` here rather than joining violation rule ids.
    if result.exit_code == int(ExitCode.HUMAN_REVIEW):
        return PolicyDecision(False, "guard", "guard_review_required", retryable=True)
    return PolicyDecision(False, "guard", "guard_blocked", retryable=False)


def _check_preflight(ctx: PolicyContext, _paths: FoundryPaths) -> PolicyDecision:
    """Missing-required-target-kind check.

    `detail` below f-strings `sorted(missing)` -- a list of CLOSED enum
    member names drawn from :data:`_REQUIRED_TARGET_KINDS`, never a
    caller-supplied value. Finding L6: this module's "never an f-string
    embedding caller input" guarantee is about caller-controlled VALUES
    (see `_SAFE_MESSAGES`/`build_error`); this is the one place internal
    enum names are interpolated, and they are never influenced by request
    data."""

    required = _REQUIRED_TARGET_KINDS.get(ctx.operation_kind, frozenset())
    present = {t.target_kind for t in ctx.targets}
    missing = required - present
    if missing:
        return PolicyDecision(
            False,
            "preflight",
            "preflight_failed",
            retryable=True,
            detail=f"missing required target kinds: {sorted(missing)}",
        )
    return PolicyDecision(True, "preflight")


# NEW-14 hygiene fix: stage names now live as an attribute COLOCATED with
# each check function's own definition (immediately below) rather than in a
# second, distant parallel structure that could drift out of order/silently
# mismatch (the prior `_STAGE_NAMES` dict). `evaluate_policy` reads
# `check.stage_name` directly.
_check_capability.stage_name = "capability"  # type: ignore[attr-defined]
_check_identity_and_rbac.stage_name = "rbac"  # type: ignore[attr-defined]
_check_audit_health.stage_name = "audit_health"  # type: ignore[attr-defined]
_check_guard.stage_name = "guard"  # type: ignore[attr-defined]
_check_preflight.stage_name = "preflight"  # type: ignore[attr-defined]

_POLICY_STAGES = (
    _check_capability,
    _check_identity_and_rbac,
    _check_audit_health,
    _check_guard,
    _check_preflight,
)


def evaluate_policy(ctx: PolicyContext, *, paths: FoundryPaths | None = None) -> PolicyDecision:
    """Run `capability -> rbac -> audit_health -> guard -> preflight`, in
    that fixed order, short-circuiting on the first denial.

    Used by BOTH the `operation.preflight` mint pass and every execute-time
    re-validation (PRD section 6.2 step 7: "Re-submit the exact operation
    ... re-evaluates current policy"). Does not evaluate confirmation
    binding -- see :func:`authorize_operation` for the full six-stage
    execute-time check.

    H8 exception boundary: any unexpected exception raised while resolving
    `paths` or running a stage (e.g. a malformed `config/governance.yaml`,
    a database error probing audit health) is caught here and converted to
    `PolicyDecision(False, <stage-that-was-running>, "internal_error",
    retryable=True)` -- this function never raises for those causes.
    """

    current_stage = "capability"
    try:
        resolved_paths = paths if paths is not None else FoundryPaths.discover()
        for check in _POLICY_STAGES:
            current_stage = check.stage_name  # type: ignore[attr-defined,union-attr]
            decision = check(ctx, resolved_paths)
            if decision.denied:
                return decision
        return PolicyDecision(True, "preflight")
    except Exception as exc:
        # NEW-13: log the failing stage + exception TYPE NAME only -- never
        # `str(exc)`, which could embed caller-influenced data (e.g. a
        # value echoed back out of a malformed governance.yaml).
        _logger.warning(
            "operator_mcp_policy.evaluate_policy: internal_error during %r stage (%s)",
            current_stage,
            type(exc).__name__,
        )
        return PolicyDecision(False, current_stage, "internal_error", retryable=True)


def authorize_operation(
    ctx: PolicyContext,
    *,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
) -> PolicyDecision:
    """Full six-stage execute-time authorization (invariant 2).

    Re-runs :func:`evaluate_policy` (policy may have drifted since mint
    time) and, for every confirmation-required kind, additionally validates
    the presented confirmation binds to `ctx` exactly (see
    :func:`verify_confirmation`). For :data:`CONFIRMATION_NOT_REQUIRED_KINDS`
    the confirmation stage is a no-op pass -- those kinds never mint or
    consume a token.

    **C1/NEW-1 (security review rounds 1 and 2)**: an exact-replay
    presentation is ALWAYS denied here (`reason_code="confirmation_replayed"`,
    `retryable=False`) -- NEVER `allowed=True`. `verify_confirmation`'s OWN
    decision for the same replay is now IDENTICAL (dataclass-`==`-equal) to
    what this function returns -- see the module docstring's "EXACT REPLAY
    IS STRUCTURALLY NON-ACCEPTING" paragraph. A caller doing
    `if authorize_operation(...).allowed: execute()` therefore CANNOT
    execute a second time on replay, and neither can a caller that
    (incorrectly) calls `verify_confirmation` directly and reads
    `.decision.allowed`.

    H8 exception boundary: wraps its own orchestration in
    `except Exception -> PolicyDecision(False, "confirmation",
    "internal_error", retryable=True)` in addition to the guards already
    inside `evaluate_policy`/`verify_confirmation` (defense in depth).
    """

    try:
        decision = evaluate_policy(ctx, paths=paths)
        if decision.denied:
            return decision
        if ctx.operation_kind in CONFIRMATION_NOT_REQUIRED_KINDS:
            return PolicyDecision(True, "confirmation")
        verification = verify_confirmation(
            confirmation_record, presented_token=presented_token, ctx=ctx, now=now
        )
        if verification.outcome == "exact_replay":
            return PolicyDecision(False, "confirmation", "confirmation_replayed", retryable=False)
        return verification.decision
    except Exception as exc:
        _logger.warning(
            "operator_mcp_policy.authorize_operation: internal_error (%s)", type(exc).__name__
        )
        return PolicyDecision(False, "confirmation", "internal_error", retryable=True)


# ---------------------------------------------------------------------------
# Confirmation lifecycle (OPM-OQ-2/3)
# ---------------------------------------------------------------------------


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp string; `None` on anything unparseable
    OR naive (no timezone offset). Finding L5: a naive timestamp is
    REJECTED, never coerced to UTC -- a hand-edited or foreign-written
    record using local time without an explicit offset could otherwise
    extend (or shorten) effective TTL by up to ~14 hours."""

    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _record_expiry(record: Mapping[str, Any], moment: datetime) -> datetime | None:
    """Effective, CLAMPED expiry for a confirmation record (finding H4):
    `min(stored expires_at, issued_at + CONFIRMATION_TTL)` -- a record
    whose stored `expires_at` claims an implausible far-future date (e.g.
    hand-edited, or a P2 bug) can never outlive the real TTL measured from
    its own `issued_at`. Returns `None` (meaning "always expired" per every
    caller's fail-closed convention) when either `issued_at` or
    `expires_at` is missing/unparseable/naive.

    NEW-7 fix (round 2): the clamp above defends against a forged
    far-future `expires_at` but NOT a forged far-future `issued_at` -- an
    `issued_at` of `now + 1 year` previously yielded a token effectively
    valid for a year (`min(expires_at, issued_at + TTL)` with both operands
    inflated together). `moment` (the caller's already-resolved "now") is
    now REQUIRED and compared against `issued_at`: an `issued_at` in the
    future relative to `moment` returns `None` (always expired) rather than
    granting a still-valid-looking window."""

    issued_at = _parse_iso(record.get("issued_at"))
    expires_at = _parse_iso(record.get("expires_at"))
    if issued_at is None or expires_at is None:
        return None
    if issued_at > moment:
        return None
    return min(expires_at, issued_at + CONFIRMATION_TTL)


def mint_confirmation(ctx: PolicyContext, *, now: datetime | None = None) -> ConfirmationIssued:
    """Mint an opaque, single-use confirmation token bound to `ctx`'s
    canonical fields (OPM-OQ-2: five-minute TTL).

    Callers MUST have already obtained an `allowed` :class:`PolicyDecision`
    from :func:`evaluate_policy` for `ctx` before calling this -- minting
    does not itself re-run policy checks. Raises `ValueError` if
    `ctx.identity` is `None`, if `ctx.operation_kind` is not a member of
    :data:`OPERATION_KINDS`, or if any `ctx.targets[i].target_kind` is not a
    member of :data:`TARGET_KINDS` (finding L3 defense-in-depth -- mint is
    never reachable without a resolved identity/valid enums in the real
    call flow, but this guards against a programming-error direct call).

    `now` is a TEST-ONLY clock-injection seam (finding M2) -- P2/P5 MUST
    NEVER thread a caller-/request-supplied timestamp through it; doing so
    would let a caller forge `issued_at`/`expires_at` and defeat the TTL.

    NEW-8(b) boundary: this function RETURNS `ConfirmationIssued`, not a
    `PolicyDecision`, so it cannot participate in the PolicyDecision-shaped
    H8 boundary `evaluate_policy`/`authorize_operation`/`verify_confirmation`
    use. The three deliberate `ValueError` guards immediately below (L3
    defense-in-depth) are intentionally OUTSIDE any try/except -- they are
    expected, documented failure modes with safe, closed-vocabulary message
    text. Everything AFTER them is wrapped: any UNEXPECTED exception during
    minting is re-raised as a plain `RuntimeError("internal_error during
    confirmation minting")` with NO caller-supplied text -- the raise-shaped
    equivalent of "never leak an exception whose message embeds
    caller-influenced data" (AC OPM-7). `PolicyContext.__post_init__`
    (NEW-8(a)/(b)) already guarantees `ctx.canonical_digest()` cannot raise
    on a non-finite float or non-Mapping payload, since such a `ctx` cannot
    be constructed in the first place -- this wrapper is defense in depth
    for anything else unexpected (e.g. an environment-level failure in
    `secrets`/`hashlib`).
    """

    if ctx.identity is None:
        raise ValueError("mint_confirmation requires a resolved ctx.identity")
    if ctx.operation_kind not in OPERATION_KINDS:
        raise ValueError(
            "mint_confirmation requires ctx.operation_kind in OPERATION_KINDS -- "
            "callers MUST call evaluate_policy first (L3 defense-in-depth)"
        )
    for target in ctx.targets:
        if target.target_kind not in TARGET_KINDS:
            raise ValueError(
                "mint_confirmation requires every ctx.targets[i].target_kind in "
                "TARGET_KINDS -- callers MUST call evaluate_policy first (L3 defense-in-depth)"
            )

    try:
        moment = now or datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        digest = ctx.canonical_digest()
        confirmation_id = "opc_" + hashlib.sha256(
            f"{digest}:{ctx.idempotency_key}:{secrets.token_hex(16)}".encode("utf-8")
        ).hexdigest()

        record: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "operator_mcp_confirmation",
            "confirmation_id": confirmation_id,
            "token_digest": token_digest,
            "actor": {
                "user_id": ctx.identity.user_id,
                "workspace_id": ctx.identity.workspace_id,
                "roles": list(ctx.identity.roles),
            },
            "effective_sensitivity": ctx.effective_sensitivity,
            "operation_kind": ctx.operation_kind,
            "canonical_input_digest": digest,
            "idempotency_key": ctx.idempotency_key,
            "policy_snapshot_version": ctx.policy_snapshot_version,
            "targets": [t.to_dict() for t in ctx.targets],
            "status": "issued",
            "issued_at": _iso_utc(moment),
            "expires_at": _iso_utc(moment + CONFIRMATION_TTL),
            "consumed_at": None,
            "consumed_by_operation_id": None,
        }
        return ConfirmationIssued(token=token, record=record)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_policy.mint_confirmation: internal_error (%s)", type(exc).__name__
        )
        raise RuntimeError("internal_error during confirmation minting") from None


def _confirmation_bound_targets(record: Mapping[str, Any]) -> Any:
    return record.get("targets")


def _bindings_match(record: Mapping[str, Any], ctx: PolicyContext) -> bool:
    """M3 fix: `identity is None` returns `False` as the FIRST line (no
    vacuous `{}`-vs-`None` match), and each `record["actor"]` field is read
    exactly once (no repeated `.get()` on a caller-influenced Mapping)."""

    identity = ctx.identity
    if identity is None:
        return False

    actor = record.get("actor")
    if not isinstance(actor, Mapping):
        return False
    actor_user_id = actor.get("user_id")
    actor_workspace_id = actor.get("workspace_id")

    return (
        record.get("operation_kind") == ctx.operation_kind
        and record.get("canonical_input_digest") == ctx.canonical_digest()
        and record.get("idempotency_key") == ctx.idempotency_key
        and record.get("policy_snapshot_version") == ctx.policy_snapshot_version
        and record.get("effective_sensitivity") == ctx.effective_sensitivity
        and actor_user_id == identity.user_id
        and actor_workspace_id == identity.workspace_id
        and _confirmation_bound_targets(record) == [t.to_dict() for t in ctx.targets]
    )


def verify_confirmation(
    record: Mapping[str, Any] | None,
    *,
    presented_token: str | None,
    ctx: PolicyContext,
    now: datetime | None = None,
) -> ConfirmationVerification:
    """Validate a presented confirmation token/record against `ctx`.

    Distinguishes `"exact_replay"` (an already-`consumed` record whose
    bound fields are byte-identical to `ctx`'s freshly recomputed
    canonical fields, AND still within its clamped expiry -- decisions-
    block: NOT an error) from every denial case. Any bound-field mismatch,
    expiry, or missing token fails closed with zero manifest and zero
    effect (AC OPM-1).

    H4 fix: expiry is evaluated via :func:`_record_expiry` (clamped to
    `issued_at + CONFIRMATION_TTL`, fails closed on any missing/
    unparseable/future-dated timestamp -- NEW-7) on EVERY branch, including
    the `consumed` (exact-replay) branch -- a consumed record is never an
    unbounded-lifetime replay oracle.

    H8: this function never raises -- any unexpected internal exception is
    caught and reported as `ConfirmationVerification("error",
    PolicyDecision(False, "confirmation", "internal_error", retryable=True))`.

    `now` is a TEST-ONLY clock-injection seam (finding M2); see
    :func:`mint_confirmation`'s docstring.

    **NEW-1 (round 2)**: the `exact_replay` branch's `PolicyDecision` is
    now `PolicyDecision(False, "confirmation", "confirmation_replayed",
    retryable=False)` -- IDENTICAL in shape to what `authorize_operation`
    returns for the same case. See the module docstring's "EXACT REPLAY IS
    STRUCTURALLY NON-ACCEPTING" paragraph: `ConfirmationVerification.outcome
    == "exact_replay"` remains the only signal distinguishing this case from
    every other denial, but `.decision.allowed` is now `False` on BOTH
    entry points, so no caller -- reading only `.decision`, direct or via
    `authorize_operation` -- can ever mistake a replay for a fresh accept.
    """

    try:
        moment = now or datetime.now(timezone.utc)

        if ctx.operation_kind in CONFIRMATION_NOT_REQUIRED_KINDS:
            return ConfirmationVerification("accepted", PolicyDecision(True, "confirmation"))

        if record is None or not presented_token:
            return ConfirmationVerification(
                "missing", PolicyDecision(False, "confirmation", "confirmation_missing", retryable=True)
            )

        presented_digest = hashlib.sha256(presented_token.encode("utf-8")).hexdigest()
        stored_digest = str(record.get("token_digest") or "")
        if not stored_digest or not hmac.compare_digest(presented_digest, stored_digest):
            return ConfirmationVerification(
                "missing", PolicyDecision(False, "confirmation", "confirmation_missing", retryable=True)
            )

        status = record.get("status")
        bound_matches = _bindings_match(record, ctx)
        expiry = _record_expiry(record, moment)
        is_expired = expiry is None or moment > expiry

        if status == "consumed":
            if bound_matches and not is_expired:
                # NEW-1: structurally non-accepting -- see docstring above.
                return ConfirmationVerification(
                    "exact_replay",
                    PolicyDecision(False, "confirmation", "confirmation_replayed", retryable=False),
                )
            if bound_matches and is_expired:
                # H4: a consumed-and-matching record past its clamped
                # expiry is NOT an unbounded-lifetime replay oracle.
                return ConfirmationVerification(
                    "expired",
                    PolicyDecision(False, "confirmation", "confirmation_expired", retryable=True),
                )
            return ConfirmationVerification(
                "mismatched",
                PolicyDecision(False, "confirmation", "idempotency_conflict", retryable=False),
            )

        if status == "revoked":
            # NEW-11 fix: a deliberately revoked confirmation must NOT
            # invite a retry via a fresh preflight -- the closed
            # reason-code set has no revoked-specific member, so this
            # reuses `confirmation_mismatch` (non-retryable, "this token is
            # no longer valid for this request"), never
            # `confirmation_expired` (retryable=True, "request a new
            # preflight preview" -- actively misleading for a revocation).
            return ConfirmationVerification(
                "mismatched",
                PolicyDecision(False, "confirmation", "confirmation_mismatch", retryable=False),
            )

        if status != "issued":
            # any other non-issued status (schema's "expired") presented again.
            return ConfirmationVerification(
                "expired", PolicyDecision(False, "confirmation", "confirmation_expired", retryable=True)
            )

        if is_expired:
            return ConfirmationVerification(
                "expired", PolicyDecision(False, "confirmation", "confirmation_expired", retryable=True)
            )

        if not bound_matches:
            return ConfirmationVerification(
                "mismatched",
                PolicyDecision(False, "confirmation", "confirmation_mismatch", retryable=False),
            )

        return ConfirmationVerification("accepted", PolicyDecision(True, "confirmation"))
    except Exception as exc:
        _logger.warning(
            "operator_mcp_policy.verify_confirmation: internal_error (%s)", type(exc).__name__
        )
        return ConfirmationVerification(
            "error", PolicyDecision(False, "confirmation", "internal_error", retryable=True)
        )


def consume_confirmation(
    record: Mapping[str, Any],
    *,
    operation_id: str,
    now: datetime | None = None,
    ctx: PolicyContext | None = None,
) -> dict[str, Any] | None:
    """Return a NEW confirmation record transitioned to `status="consumed"`,
    or `None` if the compare-and-swap precondition fails.

    H5 fix: this is now a GUARDED transition, not an unconditional
    overwrite. Returns `None` (never raises) when `record["status"] !=
    "issued"` OR the record's clamped expiry (:func:`_record_expiry`,
    NEW-7-hardened against a forged future `issued_at` too) has already
    passed at `now` -- an already-`consumed` record is NEVER silently
    rebound to a new `operation_id` (which would destroy the first
    consumption's proof), and an expired-but-still-`"issued"` record can
    never be consumed.

    NEW-12 fix (round 2, hardening): optional `ctx` -- when supplied,
    additionally requires `_bindings_match(record, ctx)` before consuming.
    Without it, this function had no binding precondition at all (only
    `operation_id`/`record`), so nothing enforced that the caller had
    actually obtained a matching `verify_confirmation(..., ctx=...)` for the
    SAME `ctx`/token before consuming -- the H5 fix made it merely LOOK
    self-sufficient. `ctx` defaults to `None` (skips this check) for
    backward compatibility with P1's own call sites/tests, which already
    call `verify_confirmation` first; P2 SHOULD always pass `ctx`.

    Pure function -- atomically persisting this alongside the operation
    manifest write is P2's job (`operator_operation_service.py`, OPM-2.1).
    See the module docstring's DUR-1 paragraph for the NORMATIVE
    compare-and-swap contract P2's real persistence layer must implement:
    callers MUST treat a `None` return here as "route to the exact-replay /
    idempotency-conflict path, do not execute."

    `now` is a TEST-ONLY clock-injection seam (finding M2); see
    :func:`mint_confirmation`'s docstring.
    """

    if record.get("status") != "issued":
        return None
    if ctx is not None and not _bindings_match(record, ctx):
        return None
    moment = now or datetime.now(timezone.utc)
    expiry = _record_expiry(record, moment)
    if expiry is None or moment > expiry:
        return None
    # NEW-14 hygiene fix: DEEP copy, not `dict(record)` (shallow) -- a
    # shallow copy shares the nested `actor`/`targets` values with the
    # INPUT record, so a caller mutating the returned record's nested
    # structures could previously mutate the original too.
    updated = copy.deepcopy(dict(record))
    updated["status"] = "consumed"
    updated["consumed_at"] = _iso_utc(moment)
    updated["consumed_by_operation_id"] = operation_id
    return updated


# ---------------------------------------------------------------------------
# Bounded, redacted error envelope
# ---------------------------------------------------------------------------

_SAFE_MESSAGES: dict[str, str] = {
    "identity_denied": "The requested operation could not be authorized for this actor/workspace.",
    "rbac_denied": "This actor's role does not permit the requested operation.",
    "audit_unhealthy": "The audit store is not healthy; privileged operations are paused until it recovers.",
    "guard_blocked": "Governance policy blocked this operation.",
    "guard_review_required": "Governance policy requires human review before this operation can proceed.",
    "preflight_failed": "A required prerequisite target is missing for this operation.",
    "operation_unknown": "The requested operation kind is not recognized.",
    "tool_unknown": "The requested tool name is not recognized.",
    "target_invalid": "A declared target kind is not recognized.",
    "confirmation_missing": "A valid confirmation token is required for this operation.",
    "confirmation_expired": "The confirmation token has expired; request a new preflight preview.",
    "confirmation_replayed": "This confirmation token has already been used for a different request.",
    "confirmation_mismatch": "The confirmation token does not match the current request.",
    "idempotency_conflict": "This idempotency key was already used with different inputs.",
    "not_found": "The requested reference could not be found.",
    "payload_too_large": "The request payload exceeds the configured size limit.",
    "internal_error": "An internal error occurred while processing this operation.",
}


def _redact_and_bound(text: str | None, *, config: FoundryConfig | None = None) -> str | None:
    if not text:
        return None
    redacted = governance.redact_payload(text, config=config)
    if not isinstance(redacted, str):
        redacted = str(redacted)
    redacted = _TRACEBACK_LIKE.sub("[REDACTED]", redacted)
    return redacted[:_ERROR_DETAIL_MAX] or None


def build_error(
    decision: PolicyDecision,
    *,
    operation_id: str | None = None,
    receipt_ref: str | None = None,
    detail: str | None = None,
    now: datetime | None = None,
    config: FoundryConfig | None = None,
) -> dict[str, Any]:
    """Build a schema-valid `operator_mcp_error` instance from a denied
    `PolicyDecision`.

    `message` is ALWAYS drawn from :data:`_SAFE_MESSAGES` by `reason_code`
    -- never an f-string embedding caller input or an exception's `str()`.
    `detail` (optional, bounded, redacted) is the only field that may carry
    supplementary context, and is scrubbed of anything traceback-shaped.

    `config` (finding M4, hardened NEW-5): optional `FoundryConfig`,
    threaded through to `governance.redact_payload` so workspace-configured
    `secret_patterns` are UNIONED WITH -- never replace -- the built-in
    list (`governance._secret_patterns` itself guarantees the union; round
    1 threaded `config` through correctly but the function it fed silently
    REPLACED the built-ins with a narrow workspace list, which made a
    workspace with its own `secret_patterns` LESS strict than the no-config
    default). Callers that already have a resolved `FoundryConfig` for the
    current workspace SHOULD pass it; omitting it falls back to the
    built-in patterns only (unchanged prior behavior).

    `operation_id`/`receipt_ref` (finding NEW-9): for `reason_code ==
    "not_found"` these are ALWAYS forced to `None` in the returned payload,
    REGARDLESS of what the caller passes in. H6's one-denial-shape
    guarantee (wrong-workspace vs above-ceiling vs genuinely-missing all
    look identical) is a property of the CLOSED envelope this function
    builds, not something a caller can be trusted to preserve by convention
    -- a caller that populates `operation_id` only on the "exists, not
    yours" case would silently restore the existence oracle H6 closed.
    """

    if decision.allowed or decision.reason_code is None:
        raise ValueError("build_error requires a denied PolicyDecision with a reason_code")
    if decision.reason_code not in CLOSED_REASON_CODES:
        raise ValueError(f"unknown reason_code: {decision.reason_code!r}")

    moment = now or datetime.now(timezone.utc)
    message = _SAFE_MESSAGES[decision.reason_code][:_ERROR_MESSAGE_MAX]
    safe_detail = _redact_and_bound(
        detail if detail is not None else decision.detail, config=config
    )

    # NEW-9: force operation_id/receipt_ref to None for not_found,
    # independent of what the caller supplied -- see docstring above.
    if decision.reason_code == "not_found":
        operation_id = None
        receipt_ref = None

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "operator_mcp_error",
        "reason_code": decision.reason_code,
        "message": message,
        "retryable": bool(decision.retryable),
        "operation_id": operation_id,
        "receipt_ref": receipt_ref,
        "occurred_at": _iso_utc(moment),
    }
    if safe_detail:
        payload["detail"] = safe_detail
    return payload
