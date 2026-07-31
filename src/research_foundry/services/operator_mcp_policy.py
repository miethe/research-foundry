"""Operator MCP policy: identity, sensitivity, guard/preflight ordering, and
confirmation binding (research-foundry-operator-mcp-v1 P1, OPM-1.2/1.3).

This module is the SOLE owner of:

* the closed operation-kind/tool-name/target-kind enumerations (mirrored
  from ``schemas/operator_mcp_operation.schema.yaml`` -- kept in sync by
  ``tests/unit/test_operator_mcp_policy.py``'s schema round-trip check);
* trusted local actor/workspace identity resolution (OPM-OQ-1): an explicit
  ``foundry.operator_mcp.identity`` config block, never a caller-supplied
  workspace, never a request-body default -- STRUCTURALLY enforced as of
  NEW-18 (security review round 3), not merely by convention: see "Identity
  is structurally non-forgeable" below;
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
  exception's own text; its optional free-text ``detail`` is routed through
  :func:`_redact_and_bound`, which replaces the ENTIRE string (never a
  per-match substitution -- BLOCK-1, round 4 gate) with a fixed safe marker
  whenever it detects traceback- OR absolute-filesystem-path-shaped content
  (`_TRACEBACK_LIKE`/`_PATH_LIKE`) -- a bare ``str(exc)`` for a
  filesystem-related failure embeds a path with no traceback framing at
  all, which a traceback-only guard never caught. (`_check_preflight`'s
  internal `detail` string does f-string a *closed enum member name* --
  never caller input; see :func:`_check_preflight`'s docstring, finding L6.)
  :func:`build_audit_delivery` goes further: its ``detail`` is not free text
  at all, only a closed ``detail_code`` selecting from
  :data:`_AUDIT_DELIVERY_SAFE_DETAILS` -- nothing exception-derived can
  reach a durable receipt through it, not merely "nothing pattern-matched".

No effect adapter, AgentJob attempt, or MCP server exists in this module
(P1 scope note, decisions-block section "Quality gate": "no effect adapter
or MCP server exists yet"). :mod:`operator_operation_service` (P2) is the
durable-persistence owner that will call the functions here; this module
touches disk only through the
:func:`research_foundry.services.governance.guard_check`/
:func:`research_foundry.services.audit_service.health_check` calls it
reuses (invariant: REUSE governance/audit primitives, never fork them) --
NEITHER is read-only: `guard_check` may read workspace-configured
`governance.yaml`, and `health_check` is a write-then-read-then-delete
probe against the local `audit_event` table (see immediately below). This
module has NO call sites for
:func:`research_foundry.services.audit_service.get_health_state` (its
"assume healthy until proven otherwise" persisted-default read) at all --
see the audit-health paragraph immediately below for why.

**Audit-health is a LIVE, UNCONDITIONAL probe on every confirmation-
requiring evaluation (BLOCK-5, round 4 gate; supersedes M6/NEW-3's round-2
fix and NEW-19's round-3 fix, both of which this paragraph previously
mis-described)**: `_check_audit_health` calls
:func:`research_foundry.services.audit_service.health_check` -- a cheap,
idempotent, never-raising write-then-read-then-delete probe against the
local audit store -- on EVERY evaluation for a confirmation-requiring
(privileged/mutating) `operation_kind` (`job.status`, the sole read kind,
never reaches this stage at all). Two round-2/round-3 fix cycles are
superseded by this, in order:

1. Round 1's wontfix rested on a false premise ("probing would brick every
   fresh workspace") and never probed at all -- a never-probed store was
   silently assumed healthy forever (M6).
2. Round 2 (NEW-3) probed ON DEMAND exactly once per workspace: read the
   PERSISTED `get_health_state` snapshot first, and only run a live probe
   when it had NEVER been probed (`last_probe_at is None`) -- trusting the
   persisted row forever after that first probe, in BOTH directions
   (NEW-19: a failed probe latched `healthy=False` and never recovered even
   after `retryable=True` invited a retry; a healthy probe latched
   `healthy=True` and never caught a later degradation).
3. This module now probes LIVE, UNCONDITIONALLY, on every such evaluation
   -- never consulting the persisted `get_health_state` snapshot at all.
   Recovery is detected on the very next call (making `retryable=True`
   honest) and degradation is detected immediately rather than never or
   only once. The cost is one small local write-then-read-then-delete per
   confirmation-requiring evaluation, which this module accepts as the
   price of removing the latch in both directions.

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
    `consumed`, GUARDED BY:
      (a) THE SAME CLAMPED-EXPIRY CHECK `consume_confirmation` applies
          (`_record_expiry`: `min(expires_at, issued_at + CONFIRMATION_TTL)`,
          itself never later than `now` -- see finding NEW-7); AND
      (b) THE SAME BINDING CHECK `consume_confirmation` applies
          (`_bindings_match`: the record's bound actor/workspace/
          sensitivity/operation/canonical-input-digest/idempotency-key/
          policy-snapshot/targets fields, recomputed fresh against the
          request being committed, byte-identical to the record's own --
          BLOCK-9, round 4 gate),
    performed in the same durable transaction as the operation-manifest
    write, under an exclusive single-writer lock (SQLite `BEGIN IMMEDIATE`,
    or `O_EXCL` create-then-atomic-rename). A CAS that observes any status
    other than `issued`, whose clamped expiry has already passed at commit
    time, OR whose binding check fails, MUST route to the exact-replay /
    idempotency-conflict / expired / mismatch path and MUST NOT execute.

**NEW-10 (round 2)**: `WHERE status = 'issued'` alone is NOT the frozen
predicate above -- it is only the status half. A P2 implementation
following just that clause would consume an EXPIRED-but-still-`"issued"`
token and still satisfy a literal reading of round 1's text. The expiry
predicate is binding and MUST be folded into the SAME compare-and-swap,
not checked separately (a separate check reopens the TOCTOU window DUR-1
exists to close).

**BLOCK-9 (round 4 gate)**: the BINDING predicate (b) above was, until this
fix, likewise not folded in -- it was the exact same defect NEW-10 raised
against the expiry half, one predicate over. NEW-12 (round 2) added
`consume_confirmation`'s `ctx`-based binding check but left `ctx` OPTIONAL
(`None` skipped the check), so "P2 SHOULD always pass `ctx`" was prose, not
shape. `consume_confirmation`'s `ctx` parameter is now REQUIRED (no
default) -- a P2 implementation calling this function at all is
structurally unable to skip the binding half, and the frozen predicate
above now states the binding requirement explicitly rather than leaving it
implicit in code comments only.

A P2 implementation that reads a confirmation record, does other work, and
only then writes `status="consumed"` (read-then-write, not a real CAS) can
pass every test in this phase while still permitting two concurrent callers
presenting the same token to both observe `status == "issued"` and both
win. This paragraph is the frozen acceptance bar for P2's closeout.

**Serve-extra import boundary** (NEW-23): this module -- usable from a plain
local stdio process with no HTTP server running -- must both IMPORT and
FUNCTION in a base install without the ``[serve]`` extra.  The previous
TYPE_CHECKING-plus-lazy-import arrangement documented here did NOT achieve
that, in two independent ways:

1. ``services.audit_service`` (a module-level import below) itself imported
   ``api.auth.provider``, so importing this module raised ``ImportError``
   regardless of how careful *this* file was; and
2. :func:`resolve_operator_identity` CONSTRUCTS an
   :class:`~research_foundry.auth_identity.AuthIdentity` at runtime, so even
   a clean import would still have failed on first real use -- the lazy
   import merely moved the failure later.

Both are now fixed structurally: :class:`AuthIdentity` lives in the
serve-free :mod:`research_foundry.auth_identity` (``api.auth.provider``
re-exports that exact class object, so all existing imports and
``isinstance`` checks are unaffected), and this module imports it at top
level -- deliberately NOT under ``TYPE_CHECKING`` -- so the serve-gated path
cannot silently return.  ``tests/unit/test_operator_mcp_serve_extra_boundary.py``
pins both halves in a subprocess with fastapi/uvicorn/starlette blocked.

**Identity is structurally non-forgeable (NEW-18, security review round
3)**: round 2 left ``PolicyContext.identity`` as an ordinary caller-supplied
constructor field on a frozen dataclass -- the decisions-block rated this
*critical* ("no default workspace on mutation"; configured-local identity
ONLY), but the mitigation was PROSE, not SHAPE: any caller could construct
``PolicyContext(identity=AuthIdentity("attacker", "any-ws", ("owner",)),
...)`` directly and ``_check_identity_and_rbac`` would authorize against it.
Three layers close this, matching in severity what a single ``identity:
AuthIdentity | None`` field previously tried to guarantee alone:

1. **Layer 1 (shape)**: ``identity`` is now ``field(init=False,
   default=None)`` -- ``PolicyContext(...)`` can no longer ACCEPT an
   ``identity=`` keyword at all; every context starts with ``identity is
   None`` until something populates it via ``object.__setattr__`` (the
   dataclass stays frozen).
2. **Layer 2 (the one sanctioned constructor)**: :meth:`PolicyContext.for_configured_operator`
   is the ONLY public way to obtain a context whose ``identity`` is
   populated -- it builds the instance from every OTHER field, then calls
   :func:`resolve_operator_identity` and installs the result. It cannot be
   asked to install a caller-supplied identity; there is no parameter for
   one.
3. **Layer 3 (the layer BELOW -- the actual guard)**: even Layer 2 is
   defense in depth, not the primary guard, because a frozen dataclass can
   still be tampered with via ``object.__setattr__`` by anything with
   direct Python access to an already-built instance.
   :func:`_check_identity_and_rbac` -- the sole function that turns identity
   into an authorization decision -- therefore NEVER reads ``ctx.identity``
   as an input to that decision. It calls :func:`resolve_operator_identity`
   itself, fresh, on every evaluation, and uses ONLY that derived value for
   the workspace/RBAC checks below. ``ctx.identity`` participates only as an
   EQUALITY COMMITMENT: if it is not ``None`` and disagrees with the derived
   identity, that state is only reachable by bypassing Layer 2, and it is
   denied ``identity_denied`` -- the SAME code and message as a wholly
   missing identity, never a distinguishing detail (H6's no-existence-leak
   convention extended to this case: an attacker forcing a value onto
   ``ctx.identity`` learns nothing about whether it was "close" to correct).

The net property, SCOPED TO ``authorize_operation`` (round 3's original
framing): **no value forced onto ``ctx.identity`` can ever grant more than
the identity already configured in ``foundry.operator_mcp.identity`` would
grant on its own** through that ONE sanctioned execute-time entry point --
at best a forged value exactly matches configured truth (in which case
nothing was actually forged), and at worst Layer 3 denies it outright.

**BLOCK-6 adjudication (round 4 gate): this property did NOT hold for the
whole module, only for ``authorize_operation``.** Round 3's closure claimed
the broader "no value forced onto ``ctx.identity``, BY ANY MEANS, can ever
grant more" -- but :func:`mint_confirmation`, :func:`verify_confirmation`,
and :func:`consume_confirmation` are all in ``__all__``, and round 3's
``mint_confirmation`` still read ``ctx.identity`` directly to populate a
confirmation record's durable ``actor`` block, with no ``paths`` parameter
to re-derive it. Empirically: a forged ``ctx.identity`` minted a record
whose ``actor`` block matched the forgery; ``verify_confirmation(record,
ctx=forged)`` then returned ``allowed=True`` (`_bindings_match` compares
the record's ``actor`` against ``ctx.identity``, and a forged mint makes
both sides the SAME forgery); and ``consume_confirmation`` (no ``ctx``
argument existed to bind against) transitioned the forged record to
``consumed`` with no identity check at all. Only ``authorize_operation``
itself was safe, because it always re-runs :func:`evaluate_policy` (whose
``rbac`` stage denies the forgery) BEFORE reaching the confirmation stage
-- the narrow claim its own docstring made, correctly.

``mint_confirmation`` now closes this the SAME way Layer 3 closes
``_check_identity_and_rbac``: it accepts an optional ``paths`` parameter
and derives the record's ``actor`` block from a FRESH
:func:`resolve_operator_identity` call, raising ``ValueError`` if that
disagrees with ``ctx.identity`` -- never trusting ``ctx.identity`` to
populate durable content. A record's ``actor`` block is therefore
authentic at its ONLY point of production, which transitively closes
``verify_confirmation``'s counterexample (`_bindings_match` now compares a
forged ``ctx.identity`` against a REAL, config-derived ``actor`` block, and
the two disagree). ``consume_confirmation``'s counterexample is closed
separately by making its ``ctx`` parameter REQUIRED (BLOCK-9, folded into
the frozen DUR-1 predicate below) rather than an opt-in default. With both
fixes, the net property now holds for the WHOLE module, not merely
``authorize_operation``: no value forced onto ``ctx.identity``, through any
of the three exported confirmation-lifecycle functions, can ever produce,
verify, or consume a confirmation whose durable content diverges from what
the actually-configured local identity would produce on its own.

**R5-BLOCK-2/R5-BLOCK-4 (round 5 gate)**: round 4's ``mint_confirmation``
fix above introduced two adjacent defects in the same edit. First, the new
``resolve_operator_identity(paths)`` derive call sat OUTSIDE
``mint_confirmation``'s exception boundary, so a malformed
``foundry.yaml`` propagated a raw ``yaml.*`` exception embedding the
malformed file's content verbatim -- reopening NEW-8 in the very function
NEW-8 was raised against. It is now wrapped in its own
``try/except Exception -> RuntimeError("internal_error during confirmation
minting")`` boundary (see :func:`mint_confirmation`'s own docstring).
Second, ``PolicyContext.for_configured_operator`` accepted and threaded a
``config: FoundryConfig | None`` parameter that neither
``_check_identity_and_rbac`` nor the new ``mint_confirmation`` derive call
accepted -- a caller using that documented seam could construct a ``ctx``
whose ``identity`` was resolved against one config while
``mint_confirmation`` re-derived against another, making every mint
HARD-FAIL. ``config`` is now REMOVED from ``for_configured_operator``
(P1 has zero production callers of it) rather than threaded to the other
two sites, so the three identity-derivation call sites in this module --
``for_configured_operator``, ``_check_identity_and_rbac``, and
``mint_confirmation`` -- always call ``resolve_operator_identity(paths)``
with no ``config`` override and therefore cannot disagree.

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
from typing import Any, Literal, Mapping

from research_foundry.auth_identity import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.errors import ExitCode
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service, governance
from research_foundry.services.export_service import SENSITIVITY_ORDER

# NEW-23: `AuthIdentity` is imported at module level from the serve-free
# `research_foundry.auth_identity`, NOT from `api.auth.provider` (which drags
# in the `[serve]` extra via `api/__init__.py`). It is a plain top-level
# import rather than a TYPE_CHECKING/lazy one precisely so this module cannot
# silently regress to the serve-gated path: `resolve_operator_identity()`
# CONSTRUCTS an AuthIdentity at runtime, so a type-only import would let the
# module import cleanly in a base install and then fail on first real use.

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
    "check_capability_and_workspace",
    "authorize_operation",
    "mint_confirmation",
    "verify_confirmation",
    "consume_confirmation",
    "build_error",
    "AUDIT_DELIVERY_STATUSES",
    "build_audit_delivery",
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
#: NB-1 (round 5, non-blocking, fixed): `_MAX_INPUT_PAYLOAD_PROPERTIES` bounds
#: the top-level KEY COUNT only -- a small number of properties can still
#: carry an effectively unbounded total byte size (round 5's empirical
#: repro: 32 properties x 300 KB each = 9,600,086 bytes, accepted). This
#: bounds the CANONICAL JSON serialization of the whole payload -- checked
#: here (`_check_capability`, a runtime `PolicyDecision`-producing stage),
#: never in `PolicyContext.__post_init__` (which only ever raises a bare
#: `ValueError` for STRUCTURAL malformation a well-formed caller could never
#: produce -- NaN, non-Mapping -- not for a legitimately oversized request a
#: real caller's payload could hit). Enforcing it in `__post_init__` instead
#: would misclassify every oversized request as `internal_error` (via
#: `evaluate_policy`'s H8 exception boundary, which never sees a
#: construction-time raise anyway -- the context is built by the CALLER,
#: before `evaluate_policy` is ever invoked) rather than the correct,
#: retryable-false `payload_too_large` this stage produces for every other
#: envelope bound.
_MAX_INPUT_PAYLOAD_BYTES = 65_536
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

# RBAC: role grants are aligned with `api/auth/rbac.py`'s `ROLE_PERMISSIONS`
# matrix, which is the single source of truth for what each role may do.
#
# NEW-22 (security review round 3) corrected TWO divergences here. The comment
# this replaces was factually wrong about both -- it asserted the read grant
# "mirrors rbac.py's viewer-has-zero-permissions convention" while the set it
# annotated did the opposite:
#
#  1. Agent-job-class kinds (`swarm.start`, `job.cancel`, `job.resume`) are
#     `agent_job:launch`-class actions. rbac.py grants `agent_job:launch` to
#     owner/admin ONLY -- `researcher` is explicitly excluded there
#     ("# agent_job:launch NOT granted to researcher") and its forward-compat
#     note requires `Depends(require_role("owner", "admin"))` on EVERY
#     agent-job mutation route. Granting `researcher` these kinds was a
#     privilege escalation relative to the HTTP surface's own rule.
#     (`swarm.start` targets a `run`, not an `agent_job`, so this class cannot
#     be derived from `_REQUIRED_TARGET_KINDS` -- it is launch-class by what it
#     DOES, not by what it points at.)
#  2. The read kind (`job.status`) granted `viewer`. rbac.py sets
#     `"viewer": set()` -- zero permissions -- and marks `run:read` as NOT
#     granted to viewer. Including `viewer` therefore contradicted the very
#     convention the old comment cited.
_AGENT_JOB_ROLES: frozenset[str] = frozenset({"owner", "admin"})
_MUTATION_ROLES: frozenset[str] = frozenset({"owner", "admin", "researcher"})
_READ_ROLES: frozenset[str] = frozenset({"owner", "admin", "researcher", "reviewer"})

#: EXHAUSTIVE operation-kind -> required-roles map. Deliberately exhaustive
#: rather than "default to `_MUTATION_ROLES`": a permissive default is exactly
#: the fail-open class that recurred through every prior review round. Adding a
#: new member to `OPERATION_KINDS` without classifying it here raises at import
#: time (see the completeness check below) instead of silently inheriting the
#: researcher-inclusive grant.
_OPERATION_ROLES: dict[str, frozenset[str]] = {
    "run.plan": _MUTATION_ROLES,
    "swarm.start": _AGENT_JOB_ROLES,
    "job.status": _READ_ROLES,
    "job.cancel": _AGENT_JOB_ROLES,
    "job.resume": _AGENT_JOB_ROLES,
    "external_report.import": _MUTATION_ROLES,
    "source.ingest": _MUTATION_ROLES,
    "run.extract": _MUTATION_ROLES,
    "run.claim_map": _MUTATION_ROLES,
    "run.synthesize": _MUTATION_ROLES,
    "run.verify": _MUTATION_ROLES,
    "run.bundle": _MUTATION_ROLES,
    # `writeback.preview` is a PREVIEW, not `report:publish` (which rbac.py
    # withholds from researcher). BLOCK-7 (round 4 gate) corrected this
    # comment's second, independent justification: it used to claim
    # `writeback.preview` "additionally passes the same
    # `*_writeback_requires_review` guard rules as every other writeback, so
    # researcher-initiated previews still cannot self-approve" -- but those
    # rules are gated on `writeback_targets`/`model_provider`/
    # `source_sensitivities`, which ALL defaulted empty/None, so for a
    # default-constructed context none of them could fire at all; the
    # rbac-eligibility comment rested on a guard-stage property that was not
    # actually guaranteed. `_check_preflight` now REQUIRES `writeback_targets`
    # to be non-empty for `writeback.preview` (BLOCK-7), so the
    # `*_writeback_requires_review` rules are now guaranteed reachable for
    # every `writeback.preview` that gets this far -- but `model_provider`/
    # `source_sensitivities` remain caller-supplied and advisory (see the
    # `PolicyContext` docstring), so `no_work_sensitive_to_unapproved_provider`/
    # `no_mixed_personal_work_bundle` are NOT guaranteed to fire. Researcher
    # eligibility here rests on the rbac.py axis alone (verified above);
    # do not re-add a compound guard-stage justification without also
    # populating those two fields from resolved server-side state.
    "writeback.preview": _MUTATION_ROLES,
}

#: NB-10 (round 5, fixed): the known role vocabulary `_OPERATION_ROLES`'
#: values are drawn from. This module deliberately does NOT import
#: `api.auth.rbac` at module level (NEW-23, the serve-extra import
#: boundary) -- `rbac.ROLE_PERMISSIONS`' key set is therefore not directly
#: importable here, so this is a local, hand-kept mirror of its five role
#: names. `tests/unit/test_operator_mcp_policy.py`'s
#: `test_operation_roles_align_with_rbac_permissions` (Part C, round 5)
#: imports `rbac` directly, in the TEST only, and mechanically checks every
#: `_OPERATION_ROLES` entry against `rbac.ROLE_PERMISSIONS` itself -- THAT
#: is the drift guard; this frozenset only bounds what a role NAME may be,
#: not what it GRANTS.
_KNOWN_ROLE_NAMES: frozenset[str] = frozenset({"owner", "admin", "researcher", "reviewer", "viewer"})

_ALL_OPERATION_KINDS: set[str] = set(OPERATION_KINDS)
_OPERATION_ROLES_KEYS: set[str] = set(_OPERATION_ROLES)
if _ALL_OPERATION_KINDS != _OPERATION_ROLES_KEYS:  # pragma: no cover - import-time invariant
    # NB-10 (round 5, fixed): this was previously a ONE-DIRECTIONAL
    # `OPERATION_KINDS - _OPERATION_ROLES` check -- an `_OPERATION_ROLES`
    # entry for a kind that had since been REMOVED from `OPERATION_KINDS`
    # (a stale/orphaned classification) would silently pass. Full set
    # equality catches both directions.
    raise RuntimeError(
        "operator_mcp_policy: OPERATION_KINDS and _OPERATION_ROLES must classify "
        f"the exact same set; missing={sorted(_ALL_OPERATION_KINDS - _OPERATION_ROLES_KEYS)!r} "
        f"orphaned={sorted(_OPERATION_ROLES_KEYS - _ALL_OPERATION_KINDS)!r}"
    )
def _validate_operation_roles(table: Mapping[str, frozenset[str]]) -> None:
    """Import-time invariant: every classification is non-empty and names only
    known roles.

    NB-10 (round 5): kept as a FUNCTION rather than a module-level `for` loop so
    the loop variables do not leak into module scope (a trailing
    `del _kind, _roles` was flagged as a possibly-unbound delete, and would have
    turned a hypothetically-empty table into a confusing NameError at import
    instead of the explicit RuntimeError intended here).
    """

    for kind, roles in table.items():
        if not roles:
            raise RuntimeError(
                f"operator_mcp_policy: _OPERATION_ROLES[{kind!r}] is empty -- an empty "
                "role set denies every identity unconditionally, which is never the intent "
                "of an explicit classification (use a real, non-empty role set)"
            )
        if not roles <= _KNOWN_ROLE_NAMES:
            raise RuntimeError(
                f"operator_mcp_policy: _OPERATION_ROLES[{kind!r}] names unknown role(s) "
                f"{sorted(roles - _KNOWN_ROLE_NAMES)!r} -- update _KNOWN_ROLE_NAMES if this "
                "is a genuine new role, never silently accept an unrecognized name"
            )


_validate_operation_roles(_OPERATION_ROLES)

_TRACEBACK_LIKE = re.compile(r'(?i)traceback|site-packages|File "[^"]*", line \d+')
#: BLOCK-1 (round 4 gate): an ABSOLUTE FILESYSTEM PATH pattern, added
#: alongside `_TRACEBACK_LIKE`. Prior to this fix `_TRACEBACK_LIKE` matched
#: only traceback/stack-frame shapes, so `str(exc)` -- the natural producer
#: of both `build_error`'s `detail` and (before this fix) `build_audit_delivery`'s
#: `detail` -- passed through completely unredacted for exceptions whose
#: message embeds a bare path with no traceback framing at all, e.g.
#: `OSError(2, "No such file or directory", "/Users/alice/.config/research-foundry/serve.env")`
#: or `PermissionError(13, "Permission denied", "/home/bob/.ssh/id_ed25519")`.
#: `governance.redact_payload`'s built-in secret patterns do not cover
#: filesystem paths either (they target credential/token shapes). This
#: pattern mirrors the receipt/error schemas' `not: pattern` guards below.
_PATH_LIKE = re.compile(r"(?:/Users/|/home/|/var/|/etc/|/opt/|/tmp/|/root/|[A-Za-z]:\\)[^\s'\"]*")
#: BLOCK-1: the fixed, safe replacement text substituted for the ENTIRE
#: input when `_redact_and_bound` detects traceback- or path-shaped
#: content -- a WHOLESALE replacement, not a per-match substitution (see
#: `_redact_and_bound`'s docstring for why a partial substitution is not
#: sufficient).
_UNSAFE_DETAIL_MARKER = "[REDACTED: unsafe content stripped]"
_ERROR_MESSAGE_MAX = 300
_ERROR_DETAIL_MAX = 500

_IDENTITY_CONFIG_SECTION = "operator_mcp"
_IDENTITY_CONFIG_KEY = "identity"

#: NB-9: heuristic-only markers used SOLELY to classify (never to change the
#: outcome of) an `audit_unhealthy` denial for telemetry -- see
#: `_check_audit_health`'s docstring/comment.
_AUDIT_CONTENTION_MARKERS: tuple[str, ...] = ("locked", "busy")

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

    `writeback_targets` is meaningful only for `writeback.preview` -- it
    feeds `governance.GuardContext.writeback_targets` so the SAME
    `work_writeback_requires_review`/`intenttree_writeback_requires_review`/
    `arc_writeback_requires_review` guard rules apply here as everywhere
    else. BLOCK-7 (round 4 gate) NARROWS a prior over-claim here: this
    field defaults to `()`, and until this fix nothing required it to be
    non-empty for `writeback.preview` -- for a default-constructed context
    NONE of those three rules could fire at all, silently reducing
    `_check_guard` to the H7 ceiling comparison alone (the same
    fail-open-by-omission shape H3 removed from `requested_workspace_id`).
    `_check_preflight` NOW REQUIRES `writeback_targets` to be non-empty for
    `writeback.preview` (`preflight_failed` otherwise), so those three
    rules are guaranteed REACHABLE for every `writeback.preview` that
    clears preflight -- reachable, not necessarily TRIGGERED, since
    whether a specific declared target is one this repo's governance rules
    actually key on is still a governance-config question, not a shape one.

    `model_provider`/`source_sensitivities` are optional, caller-supplied
    passthroughs to the SAME `GuardContext` fields, ADVISORY ONLY (BLOCK-7):
    unlike `writeback_targets`, this contract phase has no equivalent
    non-empty requirement for them (there is no single well-formed "empty"
    to reject -- `model_provider` is meaningfully `None` for many real
    requests, and `source_sensitivities` is meaningfully `()` for a preview
    with no source-derived content yet). The `no_work_sensitive_to_unapproved_provider`/
    `no_mixed_personal_work_bundle` block-severity rules therefore fire ONLY
    when a caller supplies these -- they do NOT fire "exactly as they do
    for run-level guard checks" the way a prior version of this docstring
    claimed; a P2/P5 that wants them to fire unconditionally must resolve
    and populate them from server-side state before constructing this
    context, which this contract phase does not yet do. Still REUSE, not a
    fork, of `governance.guard_check`.

    NEW-18 (security review round 3): `identity` is `init=False` -- there is
    NO public way to construct a `PolicyContext` with a caller-supplied
    identity. Use :meth:`for_configured_operator`, the ONE sanctioned
    construction path, which populates it from :func:`resolve_operator_identity`.
    See the module docstring's "Identity is structurally non-forgeable"
    paragraph for the full three-layer rationale, including why even THIS
    field being unforgeable is defense in depth rather than the primary
    guard (`_check_identity_and_rbac` never trusts this field either way).
    """

    identity: "AuthIdentity | None" = field(init=False, default=None)
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

    @classmethod
    def for_configured_operator(
        cls,
        *,
        operation_kind: str,
        idempotency_key: str,
        effective_sensitivity: str,
        sensitivity_ceiling: str,
        targets: tuple["TargetRef", ...] = (),
        input_payload: Mapping[str, Any] | None = None,
        policy_snapshot_version: str = "policy-order-v1",
        resolved_target_workspaces: tuple[str | None, ...] = (),
        writeback_targets: tuple[str, ...] = (),
        model_provider: str | None = None,
        source_sensitivities: tuple[str, ...] = (),
        paths: "FoundryPaths | None" = None,
    ) -> "PolicyContext":
        """THE one sanctioned way to construct a `PolicyContext` with a
        populated `identity` (NEW-18 Layer 2, security review round 3).

        Every keyword argument is identical to this dataclass's own fields
        MINUS `identity` (which cannot be supplied here, or anywhere else --
        Layer 1: `identity` is `init=False`) PLUS `paths`, threaded straight
        through to :func:`resolve_operator_identity`. There is deliberately
        no parameter that lets a caller pass an identity through this
        factory.

        This does NOT itself run any policy stage -- callers still call
        :func:`evaluate_policy`/:func:`authorize_operation` afterward exactly
        as before. It exists ONLY to close the public identity-injection
        door: the `identity` on the returned instance is always whatever
        `resolve_operator_identity(paths)` resolves right now (including
        `None` when no/incomplete config block exists) -- never a
        caller-supplied value, by construction.

        **R5-BLOCK-4 (round 5 gate)**: this factory previously also accepted
        a `config: FoundryConfig | None` parameter, threaded to
        `resolve_operator_identity(paths, config=config)` -- a SEPARATE
        derivation input that `_check_identity_and_rbac` (NEW-18 Layer 3) and
        :func:`mint_confirmation` (BLOCK-6, round 4) do NOT accept and could
        therefore never agree with. A `ctx` built via
        `for_configured_operator(paths=A, config=FoundryConfig(paths=B))`
        made `mint_confirmation(ctx, paths=A)` HARD-FAIL with `ValueError`
        (round 4's disagreement-is-fatal fix), even though every derivation
        site was individually correct -- the `config` parameter itself was
        the trap, a seam through which the SAME identity question could be
        asked two different ways. `config` is REMOVED here (not threaded
        elsewhere) rather than added to the other two sites: P1 has zero
        production callers of any of the three (`grep` confirms), and
        removing the option is strictly less new surface than adding it
        twice more. Every identity-derivation site in this module now calls
        `resolve_operator_identity(paths)` with no `config` override, so
        there is no longer a seam through which the three CAN disagree.

        NEW-18 Layer 3 note: even this factory is defense in depth, not the
        primary guard -- :func:`_check_identity_and_rbac` (the actual
        authorization stage) independently RE-DERIVES identity from config
        and never trusts whatever ends up on `ctx.identity`, so a
        `PolicyContext` built any other way (e.g. `object.__setattr__`
        directly on an already-built instance) still cannot be authorized
        against a forged identity. See the module docstring's "Identity is
        structurally non-forgeable" paragraph.
        """

        instance = cls(
            operation_kind=operation_kind,
            idempotency_key=idempotency_key,
            effective_sensitivity=effective_sensitivity,
            sensitivity_ceiling=sensitivity_ceiling,
            targets=targets,
            input_payload=input_payload if input_payload is not None else {},
            policy_snapshot_version=policy_snapshot_version,
            resolved_target_workspaces=resolved_target_workspaces,
            writeback_targets=writeback_targets,
            model_provider=model_provider,
            source_sensitivities=source_sensitivities,
        )
        identity = resolve_operator_identity(paths)
        object.__setattr__(instance, "identity", identity)
        return instance


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

    # R5-BLOCK-2 (round 5 gate): loading/parsing config is inside the failure
    # boundary. A malformed `foundry.yaml` previously propagated a raw
    # `yaml.parser.ParserError` OUT OF THIS FUNCTION with the offending file's
    # CONTENT embedded in the message -- reopening NEW-8 (no caller-influenced
    # data in an exception raised outside an H8 boundary) in the very primitive
    # every identity path depends on. `evaluate_policy` caught it (converting to
    # `internal_error`), but this function is public in `__all__` and
    # `for_configured_operator`/`mint_confirmation` call it DIRECTLY, so they
    # inherited the raw raise.
    #
    # Fail closed instead, consistent with this function's own documented
    # contract ("Returns `None` when the block is absent or incomplete --
    # callers MUST treat `None` as deny"): an unparseable config IS an
    # incomplete one. Log the exception TYPE NAME only, never `str(exc)`
    # (the NEW-13 convention), so nothing caller-influenced reaches the log.
    try:
        resolved_paths = paths if paths is not None else FoundryPaths.discover()
        cfg = config if config is not None else FoundryConfig(paths=resolved_paths)
        foundry_block = cfg.foundry
    except Exception as exc:
        _logger.warning(
            "operator_mcp_policy.resolve_operator_identity: config load failed (%s) -- "
            "resolving to None (deny)",
            type(exc).__name__,
        )
        return None
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


def _input_payload_byte_size(payload: Mapping[str, Any]) -> int:
    """NB-1: total canonical-JSON byte size of `payload` -- the same
    `json.dumps` convention `PolicyContext.canonical_json()` uses, so this
    measurement matches exactly what would eventually be hashed/persisted.
    `PolicyContext.__post_init__` already guarantees `payload` is JSON-
    primitive with only finite floats, so this can never raise on a
    well-formed `PolicyContext`."""

    return len(
        json.dumps(
            dict(payload), ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
        ).encode("utf-8")
    )


def _check_capability(ctx: PolicyContext, _paths: FoundryPaths) -> PolicyDecision:
    if ctx.operation_kind not in OPERATION_KINDS:
        return PolicyDecision(False, "capability", "operation_unknown", retryable=False)
    # M1: bounded envelope, enforced here (not merely by tests/schema).
    if len(ctx.targets) > _MAX_TARGETS or len(ctx.input_payload) > _MAX_INPUT_PAYLOAD_PROPERTIES:
        return PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    # NB-1 (round 5, fixed): a small property COUNT does not bound total
    # BYTE SIZE -- see `_MAX_INPUT_PAYLOAD_BYTES`'s docstring above.
    if _input_payload_byte_size(ctx.input_payload) > _MAX_INPUT_PAYLOAD_BYTES:
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


def _check_identity_and_rbac(ctx: PolicyContext, paths: FoundryPaths) -> PolicyDecision:
    # NEW-18 (Layer 3, "the layer below" -- security review round 3): this
    # is the ONLY function that turns identity into an authorization
    # decision, and it NEVER trusts `ctx.identity` for that decision. Layers
    # 1/2 (identity is `init=False`; `PolicyContext.for_configured_operator`
    # is the sole public constructor that populates it) already close the
    # ordinary injection door, but a frozen dataclass instance can still be
    # tampered with via `object.__setattr__` by anything with direct Python
    # access to it. The decision is therefore computed ENTIRELY from a
    # FRESH `resolve_operator_identity` call against configured local
    # config -- `ctx.identity` participates only as an equality commitment
    # checked below, never as an input to what gets authorized.
    identity = resolve_operator_identity(paths)
    if identity is None:
        return PolicyDecision(False, "rbac", "identity_denied", retryable=False)
    if ctx.identity is not None and ctx.identity != identity:
        # `ctx.identity` disagrees with the freshly-derived, configured
        # identity -- reachable only by bypassing `for_configured_operator`
        # (e.g. `object.__setattr__` on an already-built, frozen instance).
        # Fail closed with the SAME reason code as a wholly missing
        # identity, and no distinguishing detail (H6's no-existence-leak
        # convention extended here: an attacker forcing a value onto
        # `ctx.identity` must learn nothing about how close it was).
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

    # NEW-22: per-kind grants from the EXHAUSTIVE `_OPERATION_ROLES` map, never
    # a two-way read/mutate split with a permissive default. An unclassified
    # kind is impossible at import time, but if one ever reaches here it denies
    # rather than falling through to the researcher-inclusive set.
    required_roles = _OPERATION_ROLES.get(ctx.operation_kind)
    if required_roles is None:
        return PolicyDecision(False, "rbac", "rbac_denied", retryable=False)
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
    # NEW-19 (security review round 3): the round-2 NEW-3 fix OVERCORRECTED.
    # It probed only when `last_probe_at is None`, then trusted the persisted
    # row forever after. That latched in BOTH directions:
    #
    #   * once a probe failed, every later call reused the stored
    #     `healthy=False` and never re-probed -- so the operation was
    #     permanently denied and the `retryable=True` this branch returns was
    #     UNACHIEVABLE (the caller could retry forever and never recover, even
    #     after the audit store came back); and
    #   * symmetrically, once a probe succeeded the stored `healthy=True` was
    #     reused forever, so a store that degraded AFTER that first probe was
    #     never caught -- the same "healthy forever" fail-open NEW-3 set out
    #     to close, merely relocated from "never probed" to "probed once".
    #
    # `health_check` is a cheap, idempotent, never-raising write-then-read
    # probe against the local audit store, and this stage is reached only for
    # confirmation-requiring (privileged/mutating) kinds -- `job.status`, the
    # sole read kind, returned above. Probing unconditionally on each such
    # call therefore costs one small local upsert on an operation that is
    # about to launch a swarm/agent job, and in exchange removes the latch in
    # both directions: recovery is detected on the very next call (making
    # `retryable=True` honest), and degradation is detected immediately rather
    # than never. It also removes any dependence on `get_health_state`'s
    # "assume healthy until proven otherwise" default, which is a fail-open
    # shape we should not be reading from on an authorization path at all.
    state = audit_service.health_check(paths)
    if not state.healthy:
        # NB-9 (round 5, non-blocking, partially mitigated): this probe runs
        # AT LEAST TWICE per mint->execute flow -- once inside this
        # `evaluate_policy` call at mint/preflight time, again inside
        # `authorize_operation`'s own `evaluate_policy` re-run at execute
        # time (deliberate re-validation, see `evaluate_policy`'s docstring:
        # policy "may have drifted since mint time"). Under concurrent
        # callers this can legitimately contend for SQLite's single-writer
        # lock; `audit_service._connect` (out of this module's file
        # ownership) does not override `sqlite3.connect`'s DEFAULT 5-second
        # busy-timeout, so brief contention already resolves silently
        # *inside* the probe -- only sustained (>5s) contention or a
        # genuinely broken store denies here, and both surface identically
        # as `state.healthy=False`. This module cannot structurally tell
        # them apart (only `audit_service.py` could, and it is out of this
        # fix's file ownership) -- the WARNING below applies a heuristic to
        # the error text's SHAPE only, NEVER the text itself (NEW-13
        # convention: never log `str(exc)`-derived content), so an operator
        # paging on repeated `audit_unhealthy` denials can distinguish
        # "kept timing out under load, retries clear it" from "store is
        # genuinely broken, needs intervention" without this module ever
        # having logged or returned the distinguishing detail anywhere
        # caller-reachable. The denial itself is UNCHANGED and already
        # `retryable=True` either way -- this is additive telemetry, not a
        # new safety property.
        contention_suspected = any(
            marker in (state.error_detail or "").lower() for marker in _AUDIT_CONTENTION_MARKERS
        )
        _logger.warning(
            "operator_mcp_policy._check_audit_health: audit_unhealthy denial "
            "(contention_suspected=%s)",
            contention_suspected,
        )
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
    """Missing-required-target-kind check, PLUS (BLOCK-7, round 4 gate)
    `writeback.preview`'s missing-required-writeback_targets check.

    `detail` below f-strings `sorted(missing)` -- a list of CLOSED enum
    member names drawn from :data:`_REQUIRED_TARGET_KINDS`, never a
    caller-supplied value. Finding L6: this module's "never an f-string
    embedding caller input" guarantee is about caller-controlled VALUES
    (see `_SAFE_MESSAGES`/`build_error`); this is the one place internal
    enum names are interpolated, and they are never influenced by request
    data.

    BLOCK-7: `PolicyContext.writeback_targets`/`model_provider`/
    `source_sensitivities` all default empty/`None` (see the class
    docstring), so a default-constructed `writeback.preview` context left
    ALL THREE `governance.guard_check` block-severity rules
    (`*_writeback_requires_review`, `no_work_sensitive_to_unapproved_provider`,
    `no_mixed_personal_work_bundle`) structurally unable to fire -- omission
    silently reduced `_check_guard` to the H7 ceiling comparison alone, the
    same fail-open-by-omission shape H3 removed from `requested_workspace_id`
    on the mutating plane. This stage now fails CLOSED on the one input this
    contract phase can validate without a server-side resolver:
    `writeback_targets` must be non-empty for `writeback.preview`. See the
    `PolicyContext` docstring for why `model_provider`/`source_sensitivities`
    are NOT similarly enforced here (their guard rules remain advisory,
    populated only if a caller supplies them)."""

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
    if ctx.operation_kind == "writeback.preview" and not ctx.writeback_targets:
        return PolicyDecision(
            False,
            "preflight",
            "preflight_failed",
            retryable=True,
            detail="writeback.preview requires at least one writeback_targets entry",
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


def check_capability_and_workspace(
    ctx: PolicyContext, *, paths: FoundryPaths | None = None
) -> PolicyDecision:
    """Non-mutating ORDERING GATE: runs ONLY the first two of the six fixed
    stages (`capability`, `rbac`) -- deliberately via `_POLICY_STAGES[:2]`,
    the SAME tuple `evaluate_policy` iterates, so this can never silently
    drift out of the frozen stage order -- never `audit_health`/`guard`/
    `preflight`/`confirmation`.

    **Why this exists (M3 pre-gate fix cycle, TERRA-M3-1).** An adapter
    whose own domain-specific prerequisite check must not itself become an
    existence-of-target oracle (the F6 defect class -- see
    `research_stages.py`'s and `swarm_start.py`'s own module docstrings)
    needs the missing-vs-foreign convergence property BEFORE running that
    check. That property depends ONLY on `_check_identity_and_rbac`'s H3
    cross-workspace comparison -- never on a later stage. `swarm_start.py`'s
    first F6 fix called the FULL `evaluate_policy` as that pre-check, which
    genuinely works (a missing run and a foreign run both deny `not_found`
    at `rbac`) but pays for `_check_audit_health`'s live, mutating
    write-then-read-then-delete SQLite probe TWICE per request -- once here,
    once again inside `authorize_operation`/`authorize_for_consumption`
    (called by `base.run_pipeline` for the real accept/consume decision) --
    for every request that reaches that second call. TERRA-M3-1 named two
    concrete costs: doubled write load, and a new availability-failure
    window (a transient lock/audit-store failure landing BETWEEN the two
    probes can turn an otherwise-authorized request into `audit_unhealthy`
    that a single-probe design would never have hit).

    This function is the fix: it reaches exactly far enough (`capability`,
    `rbac`) to guarantee the F6 convergence property, and no further, so it
    costs NOTHING on the audit_health probe -- `audit_health` is stage 3,
    never reached here. The eventual REAL accept/consume decision still
    goes through `evaluate_policy`'s full six-stage stack exactly once,
    inside `authorize_operation`/`authorize_for_consumption`, unchanged.

    **This is NOT authorization.** `PolicyDecision(True, "rbac")` from this
    function means only "capability-shape and cross-workspace ownership
    both check out" -- `audit_health`/`guard`/`preflight`/`confirmation`
    have not run. A caller MUST NOT treat an `allowed=True` result from
    this function as sufficient to execute any effect; it exists ONLY to
    let a caller order "does this even resolve to something in my own
    workspace" ahead of a domain-specific, existence-revealing side check,
    without paying for two full evaluations. The eventual effect-gating
    decision MUST still come from `authorize_operation`
    (`base.run_pipeline` / `authorize_for_consumption`), exactly as before
    this function existed.

    Same H8 exception boundary as `evaluate_policy` (log the failing
    stage's TYPE NAME only, never `str(exc)`; never raise for those
    causes)."""

    current_stage = "capability"
    try:
        resolved_paths = paths if paths is not None else FoundryPaths.discover()
        for check in _POLICY_STAGES[:2]:
            current_stage = check.stage_name  # type: ignore[attr-defined,union-attr]
            decision = check(ctx, resolved_paths)
            if decision.denied:
                return decision
        return PolicyDecision(True, "rbac")
    except Exception as exc:
        _logger.warning(
            "operator_mcp_policy.check_capability_and_workspace: internal_error during %r stage (%s)",
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


def mint_confirmation(
    ctx: PolicyContext, *, paths: FoundryPaths | None = None, now: datetime | None = None
) -> ConfirmationIssued:
    """Mint an opaque, single-use confirmation token bound to `ctx`'s
    canonical fields (OPM-OQ-2: five-minute TTL).

    Callers MUST have already obtained an `allowed` :class:`PolicyDecision`
    from :func:`evaluate_policy` for `ctx` before calling this -- minting
    does not itself re-run policy checks. Raises `ValueError` if
    `ctx.identity` is `None`, if `ctx.operation_kind` is not a member of
    :data:`OPERATION_KINDS`, if any `ctx.targets[i].target_kind` is not a
    member of :data:`TARGET_KINDS` (finding L3 defense-in-depth -- mint is
    never reachable without a resolved identity/valid enums in the real
    call flow, but this guards against a programming-error direct call), or
    if `ctx.identity` disagrees with the identity freshly resolved from
    configured local config (BLOCK-6, round 4 gate -- see immediately
    below).

    **BLOCK-6 (round 4 gate)**: this function now accepts an optional
    `paths` parameter and derives the minted record's durable `actor` block
    from a FRESH :func:`resolve_operator_identity` call -- the SAME
    derive-and-compare pattern :func:`_check_identity_and_rbac` (NEW-18
    Layer 3) uses -- rather than embedding `ctx.identity` verbatim. Round
    3's version had no `paths` parameter and could not re-derive; the
    module docstring's round-3 claim that this was "safe despite that"
    (because `authorize_operation` always re-checks identity before
    EXECUTING) was true only for `authorize_operation` itself --
    `verify_confirmation`/`consume_confirmation`, both also in `__all__`,
    had no equivalent re-check and could accept/consume a confirmation
    minted against a forged `ctx.identity` (see the module docstring's
    "BLOCK-6 adjudication" paragraph for the full empirical repro). Deriving
    the `actor` block from real config here, at the record's ONLY point of
    production, makes it unforgeable regardless of which of the three
    exported functions a caller reaches for next.

    `now` is a TEST-ONLY clock-injection seam (finding M2) -- P2/P5 MUST
    NEVER thread a caller-/request-supplied timestamp through it; doing so
    would let a caller forge `issued_at`/`expires_at` and defeat the TTL.

    NEW-8(b) boundary: this function RETURNS `ConfirmationIssued`, not a
    `PolicyDecision`, so it cannot participate in the PolicyDecision-shaped
    H8 boundary `evaluate_policy`/`authorize_operation`/`verify_confirmation`
    use. The three deliberate `ValueError` guards immediately below (L3
    defense-in-depth: missing identity / unknown operation kind / unknown
    target kind) are intentionally OUTSIDE any try/except -- they are
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

    **R5-BLOCK-2 (round 5 gate)**: the BLOCK-6 identity re-derivation call
    (`resolve_operator_identity(paths)`, immediately below) is its OWN
    SEPARATE exception boundary, wrapping ONLY that call -- an unexpected
    exception raised while resolving `paths`/reading `foundry.yaml` (e.g. a
    malformed YAML block, which previously escaped as a raw
    `yaml.parser.ParserError`/`yaml.scanner.ScannerError` embedding the
    malformed file's content verbatim) is now caught there and converted to
    the SAME safe `RuntimeError("internal_error during confirmation
    minting")` the main body's boundary below produces -- never propagated
    raw. The FOURTH deliberate `ValueError` guard (the identity-mismatch
    check, immediately after) stays OUTSIDE any try/except, matching the
    other three L3 guards: it is an expected, documented failure mode with
    safe, closed-vocabulary message text, not an unexpected exception.
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
    # BLOCK-6 (round 4 gate): derive the actor identity FRESH from
    # configured local config -- never trust `ctx.identity` to populate
    # durable content. A disagreement is only reachable by bypassing
    # `PolicyContext.for_configured_operator` (e.g. `object.__setattr__` on
    # an already-built instance), and it is denied here, at the record's
    # ONLY point of production, the same way Layer 3 denies it for
    # execute-time authorization.
    #
    # R5-BLOCK-2 (round 5 gate): this call is wrapped in its OWN exception
    # boundary -- round 4's version placed it OUTSIDE the function's main
    # try/except (below), so an internal failure while resolving identity
    # (e.g. a malformed `foundry.yaml`) propagated as a raw, uncaught
    # `yaml.*` exception embedding the malformed file's content verbatim,
    # reopening NEW-8 in the very function NEW-8 was raised against. Never
    # log/embed the exception's own text (NEW-13 convention) -- only its
    # type name.
    try:
        derived_identity = resolve_operator_identity(paths)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_policy.mint_confirmation: internal_error while deriving "
            "identity (%s)",
            type(exc).__name__,
        )
        raise RuntimeError("internal_error during confirmation minting") from None
    # R5-BLOCK-2 (round 5, hardened): `resolve_operator_identity` now itself
    # fails CLOSED to `None` on an unparseable config rather than raising (the
    # `except` above remains as defence in depth for any other internal
    # failure). That makes `derived_identity is None` ambiguous between
    # "config unavailable/unparseable" and "no identity configured" -- but in
    # NEITHER case is it evidence of forgery, so it must NOT be reported with
    # the forged-identity message. Report it as the same safe internal error
    # the `except` branch raises, so the two indistinguishable causes produce
    # one indistinguishable, content-free outcome.
    if derived_identity is None:
        _logger.warning(
            "operator_mcp_policy.mint_confirmation: internal_error -- no identity could "
            "be resolved from configured local config (absent, incomplete, or unparseable)"
        )
        raise RuntimeError("internal_error during confirmation minting")
    if derived_identity != ctx.identity:
        raise ValueError(
            "mint_confirmation requires ctx.identity to match the identity "
            "resolved from configured local config -- callers MUST call "
            "evaluate_policy first (L3 defense-in-depth); a mismatch means "
            "ctx.identity was forged or local config changed since evaluate_policy ran"
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
                "user_id": derived_identity.user_id,
                "workspace_id": derived_identity.workspace_id,
                "roles": list(derived_identity.roles),
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
    ctx: PolicyContext,
    now: datetime | None = None,
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

    **BLOCK-9 (round 4 gate)**: `ctx` is now a REQUIRED keyword argument --
    `_bindings_match(record, ctx)` is ALWAYS checked before consuming.
    NEW-12 (round 2, hardening) added this check but left `ctx` optional
    (default `None`, skipping the check entirely), on the reasoning that P1's
    own call sites already call `verify_confirmation` first. That reasoning
    was the exact "trust the caller by convention" shape this module's own
    H6/NEW-9 fixes reject everywhere else: the frozen DUR-1 compare-and-swap
    predicate (module docstring) folds in a binding check, so a P2
    implementation following the reference `WHERE status='issued' AND
    <clamped expiry>` predicate literally, without ALSO binding, would
    consume a record that never bound to the request it is committing --
    and pass every P1 test, because P1's own tests could omit `ctx` too.
    P1's call sites all already have a `ctx` in scope (they call
    `verify_confirmation(..., ctx=...)` immediately before), so requiring it
    here costs nothing today and closes the gap for P2.

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
    if not _bindings_match(record, ctx):
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
    """Redact secret-shaped substrings, then scrub anything traceback- or
    path-shaped, then bound the length.

    BLOCK-1 (round 4 gate) hardening: when `text` (post-secret-redaction)
    matches `_TRACEBACK_LIKE` OR `_PATH_LIKE` ANYWHERE, the WHOLE string is
    replaced with :data:`_UNSAFE_DETAIL_MARKER` -- never a per-match
    substitution. A per-match substitution (the pre-fix behaviour) only
    scrubs the matched span and leaves the REST of the string -- including
    any second, differently-shaped sensitive fragment the patterns don't
    happen to cover -- untouched. `str(exc)` is exception-shaped text of
    unbounded, caller-influenced structure; once ANY exception/path marker
    is detected, the safest bound is to trust none of the surrounding text,
    not merely the matched substring. `build_error`'s free-text `detail`
    and (indirectly, defense-in-depth) `build_audit_delivery`'s closed
    vocabulary both route through this function.
    """

    if not text:
        return None
    redacted = governance.redact_payload(text, config=config)
    if not isinstance(redacted, str):
        redacted = str(redacted)
    if _TRACEBACK_LIKE.search(redacted) or _PATH_LIKE.search(redacted):
        return _UNSAFE_DETAIL_MARKER
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
    supplementary context; anything traceback- or path-shaped (BLOCK-1,
    round 4 gate: an absolute filesystem path with no traceback framing at
    all, e.g. bare `str(exc)` text) causes the WHOLE `detail` string to be
    replaced with a fixed safe marker via `_redact_and_bound`, never a
    partial per-match substitution.

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

    `operation_id`/`receipt_ref` (finding NEW-9) AND `detail` (finding
    BLOCK-8, round 4 gate): for `reason_code == "not_found"` ALL THREE are
    ALWAYS forced to `None`/absent in the returned payload, REGARDLESS of
    what the caller passes in. H6's one-denial-shape guarantee
    (wrong-workspace vs above-ceiling vs genuinely-missing all look
    identical) is a property of the CLOSED envelope this function builds,
    not something a caller can be trusted to preserve by convention -- NEW-9
    closed this for `operation_id`/`receipt_ref` on exactly that argument,
    but left `detail` -- on the SAME envelope, subject to the IDENTICAL
    argument -- passed through untouched. A P2 that attaches a `detail` on
    the "exists, not yours" case (e.g. naming the resource) and omits it on
    the genuinely-absent case would restore the existence oracle H6/NEW-9
    closed, through the one field NEW-9 didn't force.
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

    # NEW-9 / BLOCK-8 (round 4 gate): force operation_id/receipt_ref/detail
    # to None for not_found, independent of what the caller supplied -- see
    # docstring above. `detail` is forced by the IDENTICAL argument NEW-9
    # already applied to the other two fields.
    if decision.reason_code == "not_found":
        operation_id = None
        receipt_ref = None
        safe_detail = None

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


#: Closed `audit_delivery.status` vocabulary (mirrors `$defs.audit_delivery`
#: in the receipt schema).
AUDIT_DELIVERY_STATUSES: frozenset[str] = frozenset({"delivered", "degraded", "unavailable"})

#: `$defs.audit_delivery.audit_event_id` bound in the receipt schema.
_AUDIT_EVENT_ID_MAX = 128

#: BLOCK-1 (round 4 gate) -- CLOSED vocabulary for `audit_delivery.detail`.
#: NEW-21 (round 3) routed a caller-supplied free-text `detail` through
#: `_redact_and_bound`, but its own named producer -- `str(exc)` from a
#: failed audit write -- routinely embeds an absolute filesystem path with
#: NO traceback framing at all (e.g. `OSError`/`PermissionError` messages),
#: which `_TRACEBACK_LIKE` never matched (see `_PATH_LIKE`'s docstring).
#: Rather than trust every future producer to keep calling a redaction
#: helper correctly on ad-hoc text, `detail` is now selected from this
#: fixed, safe-string table by a closed `detail_code` -- nothing
#: exception-derived can reach this field AT ALL, not merely "usually,
#: after redaction". Each member describes WHY delivery degraded/failed,
#: never HOW (no path, no exception message, no caller-influenced text).
_AUDIT_DELIVERY_SAFE_DETAILS: dict[str, str] = {
    "write_failed": "The audit write did not complete.",
    "probe_failed": "The audit health probe did not complete.",
    "connection_unavailable": "The audit store connection was unavailable.",
    "unhealthy_at_delivery": "The audit store was unhealthy at delivery time.",
}


def build_audit_delivery(
    status: str,
    *,
    audit_event_id: str | None = None,
    detail_code: str | None = None,
) -> dict[str, Any]:
    """Build a schema-valid `audit_delivery` block with a CLOSED-VOCABULARY
    `detail` (finding NEW-21, security review round 3; hardened BLOCK-1,
    round 4 gate).

    Round 3's fix routed a caller-supplied FREE-TEXT `detail` through
    `_redact_and_bound` (`governance.redact_payload` -> `_TRACEBACK_LIKE`
    strip -> length cap). That closed the traceback/stack-frame shape but
    NOT this field's own named producer: `str(exc)` for a filesystem-related
    failure (`OSError`/`PermissionError`/similar) embeds an absolute path
    with NO traceback framing -- `_TRACEBACK_LIKE` never matched it, and
    `governance.redact_payload`'s built-in patterns target credential/token
    shapes, not paths. BLOCK-1's empirical repro: `build_audit_delivery(
    "degraded", detail=str(OSError(2, "No such file or directory",
    "/Users/alice/.config/research-foundry/serve.env")))` emitted the path
    VERBATIM, and the embedding `terminal_receipt` validated.

    `detail` is therefore no longer free text: callers select a
    `detail_code` from the fixed, safe-string :data:`_AUDIT_DELIVERY_SAFE_DETAILS`
    table -- describing WHY delivery degraded/failed, never HOW. This is a
    STRONGER guarantee than redaction: nothing exception-derived can reach
    this field, not merely "nothing that matches a known-unsafe pattern".
    The resolved safe string is still routed through `_redact_and_bound`
    (defense in depth -- a no-op for the fixed strings in the table today,
    keeping this producer aligned with `build_error`'s pipeline).

    Raises `ValueError` for an unknown `status`, an over-long
    `audit_event_id`, or an unknown `detail_code` (all are caller
    programming errors, and this module's convention -- see :func:`build_error`
    -- is to fail loudly on them rather than emit a silently-malformed
    payload).

    **R5-BLOCK-1 (round 5 gate)**: `audit_event_id` -- `detail`'s SIBLING
    property on this same `$def`, one property over -- was length/type
    checked above but never redacted: a caller-supplied path- or
    traceback-shaped `audit_event_id` (this field's real producer,
    `audit_service.AuditHealth`, always supplies a UUID4, but this function
    itself imposes no such restriction on a caller) passed straight through
    to the returned payload, and the receipt schema had no pattern guard on
    it either (see `schemas/operator_mcp_receipt.schema.yaml`'s
    `audit_delivery.audit_event_id` description). It is now routed through
    the SAME :func:`_redact_and_bound` defense-in-depth pass `detail` uses
    below -- a no-op for a genuine UUID, but no longer a silent pass-through
    for anything path- or traceback-shaped.
    """

    if status not in AUDIT_DELIVERY_STATUSES:
        raise ValueError(f"unknown audit_delivery status: {status!r}")
    if audit_event_id is not None:
        if not isinstance(audit_event_id, str):
            raise ValueError("audit_event_id must be a string or None")
        if len(audit_event_id) > _AUDIT_EVENT_ID_MAX:
            raise ValueError(
                f"audit_event_id exceeds the schema bound of {_AUDIT_EVENT_ID_MAX} characters"
            )
    if detail_code is not None and detail_code not in _AUDIT_DELIVERY_SAFE_DETAILS:
        raise ValueError(f"unknown audit_delivery detail_code: {detail_code!r}")

    payload: dict[str, Any] = {
        "status": status,
        # R5-BLOCK-1: route through the same redaction pass `detail` uses --
        # a no-op for the genuine-UUID producer, defense in depth against a
        # path-/traceback-shaped caller-supplied value.
        "audit_event_id": _redact_and_bound(audit_event_id) if audit_event_id is not None else None,
    }
    if detail_code is not None:
        safe_detail = _redact_and_bound(_AUDIT_DELIVERY_SAFE_DETAILS[detail_code])
        if safe_detail:
            payload["detail"] = safe_detail
    return payload
