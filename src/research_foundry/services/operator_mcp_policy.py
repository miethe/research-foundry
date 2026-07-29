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
  with exact replay recognized as a distinct, non-error outcome
  (:attr:`ConfirmationVerification.outcome` ``"exact_replay"``) rather than
  a denial -- **but only from :func:`verify_confirmation` itself**. See the
  "EXACT REPLAY VS `authorize_operation`" paragraph below (security-review
  round 1, finding C1): the two functions deliberately disagree about
  whether a replay may proceed, and that disagreement is the fix, not a bug;
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
:func:`research_foundry.services.audit_service.is_healthy_for_exposure`
calls it reuses (invariant: REUSE governance/audit primitives, never fork
them). Finding M6 (wontfix-justified, see :func:`_check_audit_health`'s
own comment): `is_healthy_for_exposure` inherits a documented
"never-probed == healthy" tri-state from `audit_service.get_health_state`.
Treating never-probed as unhealthy at this call site was evaluated and
rejected -- P1 ships no probe-triggering code path, so doing so would brick
every mutating operation in any fresh workspace. P2 MUST instead ensure at
least one health probe has run before the first mint in a workspace.

**EXACT REPLAY VS `authorize_operation` (security-review round 1, C1)**:
:func:`verify_confirmation` reports an already-consumed, still bound-
matching, still-unexpired token as ``ConfirmationVerification(outcome=
"exact_replay", decision=PolicyDecision(True, "confirmation"))`` -- this
correctly means "not an error" for a caller (P2) that wants the RICH result
so it can route to the PRIOR receipt. :func:`authorize_operation`, by
contrast, is the boolean-shaped, execute-time entry point a naive caller
might use as ``if authorize_operation(...).allowed: execute()``. Such a
caller MUST NEVER execute a second time on replay. `authorize_operation`
therefore NEVER returns ``allowed=True`` for a replay -- it denies with
``reason_code="confirmation_replayed"`` (``retryable=False``), a decision
that is never dataclass-``==``-equal to the ``accepted`` decision and never
satisfies a bare ``.allowed`` check. Callers that need the "return the
prior receipt, do not error" distinction MUST call :func:`verify_confirmation`
directly and branch on ``outcome == "exact_replay"``; they must never infer
it from `authorize_operation`'s boolean-shaped return.

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

**Canonicalization hardening (L4)**: `canonical_json()` passes
`allow_nan=False` to `json.dumps` -- `NaN`/`Infinity` in a canonical field
would otherwise silently produce non-JSON text no downstream reader could
reproduce; `PolicyContext.__post_init__` additionally rejects a
non-JSON-primitive `input_payload` at construction (finding H8) so
`canonical_digest()` can never raise `TypeError` on caller-influenced data.
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
    `consumed`, performed in the same durable transaction as the
    operation-manifest write, under an exclusive single-writer lock (SQLite
    `BEGIN IMMEDIATE`, or `O_EXCL` create-then-atomic-rename). A CAS that
    observes any status other than `issued` MUST route to the exact-replay /
    idempotency-conflict path and MUST NOT execute.

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

import hashlib
import hmac
import json
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
# `maxItems: 20` on `targets` / `maxProperties: 32` on `input_payload`).
# Enforced here in `_check_capability`, not via `SchemaRegistry` (finding
# M1) -- P1 constructs `PolicyContext` directly from already-typed Python
# values (no raw request envelope exists yet in this repository); P5's
# transport boundary MAY additionally schema-validate the raw wire envelope
# before ever constructing a `PolicyContext`, but THIS enforcement is
# authoritative and does not depend on that happening.
_MAX_TARGETS = 20
_MAX_INPUT_PAYLOAD_PROPERTIES = 32

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
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, Mapping):
        return all(
            isinstance(k, str) and _is_json_primitive(v, _depth=_depth + 1) for k, v in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_is_json_primitive(v, _depth=_depth + 1) for v in value)
    return False


def _sensitivity_rank(label: str) -> int:
    """Shared rank lookup for `effective_sensitivity`/`sensitivity_ceiling`
    comparisons (H7). Unknown labels rank `len(SENSITIVITY_ORDER)` --
    STRICTER than every known level, mirroring `export_service.py`'s own
    `_UNKNOWN_SENSITIVITY` convention -- NEVER `-1`, which would make an
    unknown/malformed label the LOOSEST possible value and silently fail
    open. In normal operation this branch is unreachable (both fields are
    validated against :data:`SENSITIVITY_LEVELS` at `PolicyContext`
    construction) -- this is defense in depth, not the primary guard."""

    return SENSITIVITY_ORDER.get(label, len(SENSITIVITY_ORDER))


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
        # member of the closed vocabulary, always.
        if self.effective_sensitivity not in SENSITIVITY_LEVELS:
            raise ValueError(
                f"effective_sensitivity must be one of {SENSITIVITY_LEVELS!r}, "
                f"got {self.effective_sensitivity!r}"
            )
        # H7: sensitivity_ceiling is required and validated the same way.
        if self.sensitivity_ceiling not in SENSITIVITY_LEVELS:
            raise ValueError(
                f"sensitivity_ceiling must be one of {SENSITIVITY_LEVELS!r}, "
                f"got {self.sensitivity_ceiling!r}"
            )
        # H3: whenever any target is declared, its owning-workspace
        # resolution MUST be supplied (a real workspace id, or None for
        # "could not be resolved") -- no default/omitted-means-skip gate.
        if self.targets and len(self.resolved_target_workspaces) != len(self.targets):
            raise ValueError(
                "resolved_target_workspaces must supply exactly one owning-workspace "
                "entry (or None for an unresolved/absent target) per declared target "
                "-- there is no default/omitted-means-skip cross-workspace gate (H3)"
            )
        # H8: input_payload must be JSON-primitive so canonical_digest() can
        # never raise on caller-influenced data.
        if not _is_json_primitive(self.input_payload):
            raise ValueError(
                "input_payload must be JSON-primitive (str/int/float/bool/None/"
                "dict/list only, bounded depth)"
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
    from every denial case -- callers (P2) route `"exact_replay"` to the
    PRIOR terminal receipt rather than fabricate a new effect. `"error"` is
    the H8 exception-safety boundary: an unexpected internal failure while
    verifying, never propagated as a raised exception.

    See the module docstring's "EXACT REPLAY VS `authorize_operation`"
    paragraph (finding C1) -- `authorize_operation` deliberately does NOT
    pass a bare `exact_replay` `allowed=True` through to its own callers.
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
    `_UNKNOWN_SENSITIVITY` convention). Returns `"public"` when no
    non-empty sensitivity is supplied.
    """

    values = [s for s in sensitivities if s]
    if not values:
        return "public"
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
    for target in ctx.targets:
        if target.target_kind not in TARGET_KINDS:
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
    # M6 (wontfix-justified, see finding table + phase-1-completion.md):
    # `audit_service.get_health_state`'s own docstring documents a
    # "never-probed == healthy" tri-state ("assume healthy until proven
    # otherwise"). Treating never-probed as UNHEALTHY here was evaluated
    # and rejected: P1 ships no probe-triggering code path (no MCP server,
    # no scheduled health check), so a fresh workspace would brick every
    # mutating operation until an unrelated subsystem happens to run a
    # probe -- a worse regression than the inherited fail-open gap. Kept as
    # the finding's own documented alternative: P2 MUST ensure at least one
    # `audit_service.health_check()` probe has run (e.g. at process start,
    # or synchronously before the very first mint in a workspace) before
    # privileged operations begin, resolving this tri-state deliberately
    # rather than leaving it to chance.
    if not audit_service.is_healthy_for_exposure(paths):
        return PolicyDecision(False, "audit_health", "audit_unhealthy", retryable=True)
    return PolicyDecision(True, "audit_health")


def _check_guard(ctx: PolicyContext, paths: FoundryPaths) -> PolicyDecision:
    # H7: above-ceiling content is denied with the SAME `not_found` shape
    # as a wrong-workspace/absent target (H6) -- checked first, and cheaply,
    # before touching disk via governance.guard_check.
    if _sensitivity_rank(ctx.effective_sensitivity) > _sensitivity_rank(ctx.sensitivity_ceiling):
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


_POLICY_STAGES = (
    _check_capability,
    _check_identity_and_rbac,
    _check_audit_health,
    _check_guard,
    _check_preflight,
)

_STAGE_NAMES: dict[Any, str] = {
    _check_capability: "capability",
    _check_identity_and_rbac: "rbac",
    _check_audit_health: "audit_health",
    _check_guard: "guard",
    _check_preflight: "preflight",
}


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
            current_stage = _STAGE_NAMES[check]
            decision = check(ctx, resolved_paths)
            if decision.denied:
                return decision
        return PolicyDecision(True, "preflight")
    except Exception:
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

    **C1 (security review round 1)**: an exact-replay presentation is
    ALWAYS denied here (`reason_code="confirmation_replayed"`,
    `retryable=False`) -- NEVER `allowed=True`. This is deliberately
    different from `verify_confirmation`'s own `outcome == "exact_replay"`,
    which correctly reports "not an error" for a caller that wants to
    return the prior receipt. See the module docstring's "EXACT REPLAY VS
    `authorize_operation`" paragraph. A caller doing
    `if authorize_operation(...).allowed: execute()` therefore CANNOT
    execute a second time on replay.

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
    except Exception:
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


def _record_expiry(record: Mapping[str, Any]) -> datetime | None:
    """Effective, CLAMPED expiry for a confirmation record (finding H4):
    `min(stored expires_at, issued_at + CONFIRMATION_TTL)` -- a record
    whose stored `expires_at` claims an implausible far-future date (e.g.
    hand-edited, or a P2 bug) can never outlive the real TTL measured from
    its own `issued_at`. Returns `None` (meaning "always expired" per every
    caller's fail-closed convention) when either `issued_at` or
    `expires_at` is missing/unparseable/naive."""

    issued_at = _parse_iso(record.get("issued_at"))
    expires_at = _parse_iso(record.get("expires_at"))
    if issued_at is None or expires_at is None:
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
    unparseable timestamp) on EVERY branch, including the `consumed`
    (exact-replay) branch -- a consumed record is never an unbounded-
    lifetime replay oracle.

    H8: this function never raises -- any unexpected internal exception is
    caught and reported as `ConfirmationVerification("error",
    PolicyDecision(False, "confirmation", "internal_error", retryable=True))`.

    `now` is a TEST-ONLY clock-injection seam (finding M2); see
    :func:`mint_confirmation`'s docstring.

    See the module docstring's "EXACT REPLAY VS `authorize_operation`"
    paragraph (finding C1) for why `authorize_operation` does NOT pass this
    function's `exact_replay` outcome through as `allowed=True`.
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
        expiry = _record_expiry(record)
        is_expired = expiry is None or moment > expiry

        if status == "consumed":
            if bound_matches and not is_expired:
                return ConfirmationVerification("exact_replay", PolicyDecision(True, "confirmation"))
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

        if status != "issued":
            # expired/revoked record presented again.
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
    except Exception:
        return ConfirmationVerification(
            "error", PolicyDecision(False, "confirmation", "internal_error", retryable=True)
        )


def consume_confirmation(
    record: Mapping[str, Any], *, operation_id: str, now: datetime | None = None
) -> dict[str, Any] | None:
    """Return a NEW confirmation record transitioned to `status="consumed"`,
    or `None` if the compare-and-swap precondition fails.

    H5 fix: this is now a GUARDED transition, not an unconditional
    overwrite. Returns `None` (never raises) when `record["status"] !=
    "issued"` OR the record's clamped expiry (:func:`_record_expiry`) has
    already passed at `now` -- an already-`consumed` record is NEVER
    silently rebound to a new `operation_id` (which would destroy the
    first consumption's proof), and an expired-but-still-`"issued"`
    record can never be consumed.

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
    moment = now or datetime.now(timezone.utc)
    expiry = _record_expiry(record)
    if expiry is None or moment > expiry:
        return None
    updated = dict(record)
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

    `config` (finding M4): optional `FoundryConfig`, threaded through to
    `governance.redact_payload` so workspace-configured `secret_patterns`
    (not just the built-in list) are scrubbed from `detail`. Callers that
    already have a resolved `FoundryConfig` for the current workspace
    SHOULD pass it; omitting it falls back to the built-in patterns only
    (unchanged prior behavior).
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
