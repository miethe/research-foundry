"""Sole tool registry for `rf-operator-mcp` (M2 Leg B, OPM-5.1/5.2/5.4).

This module is the ONE place any `rf-operator-mcp` tool name is ever
registered. It imports only `research_foundry.services.operator_mcp_policy`
(the P1 contract/policy module) and `research_foundry.services.
operator_mcp_adapters` (the P3 closed adapter registry) -- never
`research_foundry.knowledge_mcp.*`, never `research_foundry.services.
search_router.*`, never `..integrations` (M2 contract hard boundary 2, D9
Leg B). It never imports Typer, `cli_commands`, `subprocess`, `os.system`,
or uses `shell=True` anywhere in its own call path (hard boundary 3).

**Offline-safe-import contract** (mirrors `knowledge_mcp/registry.py`):
this module imports cleanly without the optional `mcp` SDK installed. Only
:func:`build_server` touches it, and only lazily, raising a clear
:class:`RuntimeError` (naming the `mcp` extra) if it is missing.

**Closed, derived tool inventory (D4).** The registered tool set is
EXACTLY `operator_mcp_policy.TOOL_NAMES` (14 = the 13 `OPERATION_KINDS` +
`operation.preflight`), built by iterating that tuple -- no wildcard tool,
no dynamic registration path, no name rewriting. For each operation kind,
:func:`build_server` builds ONE thin handler that resolves the adapter via
`operator_mcp_adapters.get_adapter(kind)` and forwards every caller input
to `adapter.invoke(**kwargs)` unchanged; `input_payload`'s keys become that
adapter's own kind-specific keyword arguments (e.g. `intent_id`/`depth`/
`audience` for `run.plan`, `run_id`/`adapter_ids` for `swarm.start`) --
this mirrors `operator_mcp_operation.schema.yaml`'s own generic, bounded
`input_payload` envelope field exactly (`additionalProperties: true,
maxProperties: 32` -- the per-tool payload SHAPE is intentionally NOT
frozen at the transport layer; each adapter's own `invoke()` signature is
the true, already-frozen per-kind contract). `build_server()` RAISES at
build time if any `OPERATION_KINDS` member lacks a registered adapter --
never a silent, partial server (see the "Leg A/B integration" section
below for why this is expected to raise until `writeback.preview` lands).

**`operation.preflight` (D5).** The one server-IMPLEMENTED meta tool.
Builds a `PolicyContext` via `PolicyContext.for_configured_operator` (the
ONE sanctioned way to obtain a populated `identity` -- never caller-
supplied), runs `operator_mcp_policy.evaluate_policy`, and on an ALLOW
decision for a confirmation-requiring kind mints a confirmation via
`operator_mcp_policy.mint_confirmation` -- the EXACT same two functions
`tests/unit/test_operator_mcp_serve_extra_boundary.py::
test_evaluate_policy_and_mint_confirmation_run_without_serve_extra`
exercises. It NEVER calls `authorize_for_consumption`/
`consume_and_create_operation`/`run_or_replay` -- no operation manifest, no
receipt, no adapter action ever runs on this path. M2 fix cycle 2, SEC-3
correction: the parenthetical here used to read "(zero effect)" -- that
became FALSE the moment F1.1 (TERRA-1) started durably persisting the
minted confirmation (see the "F1.1" comments inside :func:`build_server`
below). The accurate claim is **zero effect beyond one durable
`confirmations` row**: no operation manifest, no receipt, no adapter
action, no canonical/business-domain write of any kind -- only the single,
bounded INSERT `record_confirmation` performs for a confirmation-requiring
kind that clears policy (a `CONFIRMATION_NOT_REQUIRED_KINDS` member and
every DENIED preflight write nothing at all, in `.rf_state` or anywhere
else). Denials
return the standard `build_error` envelope; a `CONFIRMATION_NOT_REQUIRED_KINDS`
member (`job.status`) returns `{"allowed": True, "confirmation": None}`
without minting (a token that could never be verified would be misleading,
not merely inert).

`sensitivity_ceiling` is NEVER caller-suppliable here either (H7 doctrine,
identical to every P3 adapter) -- resolved via `operator_mcp_adapters.
resolve_local_sensitivity_ceiling(paths)`, the SAME public helper every P3
adapter entry point already calls. `identity` is likewise never caller-
suppliable (NEW-18 doctrine) -- resolved exclusively inside
`PolicyContext.for_configured_operator`.

`targets` IS accepted (optional) so a caller can preview/mint for a
target-bearing kind (e.g. `swarm.start`'s required `run` target) -- see the
D8 caller-input table in this task's completion note for the full judgment
call on how `resolved_target_workspaces` is resolved for this generic,
per-kind-domain-lookup-free preview tool, and why it is structurally safe
(`resolved_target_workspaces` is never part of the canonical digest or the
minted confirmation record -- confirmed against `PolicyContext.
canonical_payload()`'s own docstring and `mint_confirmation`'s record
construction -- so this preview-only resolution can never weaken the REAL
execute-time `authorize_operation()` a target-bearing kind's own adapter
independently reconstructs from real domain state).

**Transport error mapping (D7).** `_stdio_only_fastmcp_class`'s
`call_tool` override is the ONE dispatch chokepoint every real stdio
request AND every direct `server.call_tool(...)` call goes through
(confirmed against the installed SDK: `FastMCP.__init__` registers
`self.call_tool` -- the overridden bound method, resolved via normal
attribute lookup -- as the low-level protocol server's own `call_tool`
handler: `self._mcp_server.call_tool(...)(self.call_tool)`). It maps ONLY
the three transport-level failures D7
names -- unknown tool name (`operator_mcp_policy.check_tool_name`,
P5's own "FROZEN P5 OBLIGATION"), an oversized raw argument payload (a
transport-level short-circuit BEFORE any adapter/policy code runs; the
authoritative, bound `_check_capability` stage inside `evaluate_policy`
still runs later, per adapter, over that adapter's own narrowed
`ctx.input_payload` -- this is defense-in-depth, not a replacement), and
any unexpected exception raised while dispatching a registered tool
function -- ALL via `operator_mcp_policy.build_error`. Every
adapter-returned error envelope (already `build_error`-shaped, per
`OperatorAdapterResult.error`'s own contract) passes through this method
UNTOUCHED inside the `CallToolResult` `super().call_tool(...)` already
returns; this module adds NOTHING that could distinguish existence beyond
what that layer already returns (the H6 "one denial shape" guarantee).

**Dual encoding.** Every tool result places the identical core payload
dict in BOTH `structuredContent` and exactly one `content` block of
`{"type": "text", "text": "<canonical-json>"}` -- the SAME canonical-JSON
convention (`json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
sort_keys=True)`) `knowledge_mcp/registry.py`'s own `_canonical_json`
uses, reimplemented by value here (this module never imports from
`knowledge_mcp`). Tools are registered with `structured_output=False` so
the SDK's own `convert_result` passes an explicitly-returned
`CallToolResult` straight through unmodified, exactly as `knowledge_mcp`
does.

**Leg A/B integration note (D10).** `writeback.preview` is Leg A's file
ownership (`operator_mcp_adapters/writeback_preview.py` +
`operator_mcp_adapters/__init__.py` registration). At the time this leg
was implemented, Leg A had not yet registered it
(`operator_mcp_adapters.get_adapter("writeback.preview")` returns `None`)
-- `build_server()`'s fail-loud check (D4) therefore RAISES today; this is
the CORRECT, expected behavior per D10, not a bug in this module. The
exact-14 inventory test (`tests/integration/test_operator_mcp_server.py`)
is written for the FULL, integrated 14-tool surface and will pass once
Leg A lands; it is left in place, not weakened, per the contract.

**Stdio-only transport guard (invariant 8).** `build_server` constructs a
genuine `FastMCP` SUBCLASS (`_stdio_only_fastmcp_class`) directly --
a subclass, not a delegating wrapper/proxy, so there is no second,
unguarded object for a bound method's `__self__` to resolve to instead
(the same bypass class `knowledge_mcp/registry.py`'s own docstring
documents and closes). This module reimplements that shape independently,
by value, rather than importing it, per this module's own import
boundary (never `knowledge_mcp.*`).

**Scope of the stdio-only guard (M2 fix cycle 1, F1.6/TERRA-5 -- READ
BEFORE relying on this guard for anything stronger than defense in
depth).** The guard above blocks every REACHABLE activation path a normal
caller (a real stdio client, `process.main()`, or test code calling bound
instance methods like `server.run(...)`/`server.sse_app()`) can drive: it
is a genuine subclass, so ordinary virtual dispatch through the instance
always resolves to the overriding method, never the base class's. It does
**NOT** and structurally **CANNOT** prevent an UNBOUND base-class call --
`FastMCP.sse_app(server_instance)` or `FastMCP.streamable_http_app(server_instance)`
-- from returning a live, network-capable Starlette app for that same
instance; Python has no mechanism to make a subclass override observable
through an explicit unbound-base-method call (`Base.method(instance)`
always resolves `method` on `Base`, never re-dispatches virtually). This is
NOT a gap this task closes: reaching that call requires the caller to
already be executing arbitrary Python in this process (there is no
registered MCP tool, and no reachable code path from a real stdio request,
that ever calls an unbound base method on `server`) -- at which point the
attacker could `import socket` directly and mount a listener themselves,
making the guard moot either way. The guard is therefore **defense in
depth against every transport path a real caller can drive, not a sandbox
against arbitrary in-process code execution** -- `test_transport_guard_
unbound_base_class_call_bypasses_the_guard_by_design` below PINS this
limitation explicitly (asserts the unbound call succeeds) so no future
reader mistakes the guard for stronger than it is. The identical
limitation exists, unfixed, in the already-shipped `knowledge_mcp` guard
this module's shape mirrors; filed as a follow-up ITT node, not carried
here as an open task -- see `m2-fix-contract.md`'s TERRA-5 adjudication for
the full reasoning, including why redesigning the guard (e.g. a delegating
wrapper) only trades this bypass class for the `__self__`/`_inner` bypass
class `knowledge_mcp/registry.py`'s own docstring already rejected a
wrapper to avoid.

**Unknown top-level tool arguments (M2 fix cycle 1, F1.4/ICA E2 -- claim
correction).** Every tool's ADVERTISED `list_tools()` schema declares
`additionalProperties: false` (D4, `_close_input_schema`) -- but this is
advisory to a well-behaved client, not a runtime rejection this module
performs: the SDK validates real requests against a pydantic model
generated FROM each handler's own signature
(`mcp.server.fastmcp.utilities.func_metadata`), and that generated model's
`extra` config is pydantic v2's own default (`"ignore"`), not `"forbid"`.
A caller-supplied top-level key with no matching parameter (e.g. an
`EXTRA_UNDECLARED` key alongside `idempotency_key`/`input_payload`) is
therefore SILENTLY DROPPED before it ever reaches this module's own code
-- never forwarded to an adapter (confirmed empirically: `adapter.invoke`
never observes it), but also never surfaced to the caller as a validation
error. Security-neutral (nothing downstream ever sees the dropped key),
but reading D4's "closed input schemas" language as "the server rejects
unknown fields" is incorrect; `test_unknown_top_level_argument_is_
silently_dropped_not_rejected` below pins the actual (drop, not reject)
behavior so this distinction stays test-enforced, not merely documented.
This module does not attempt to override the SDK's own `extra="ignore"`
default (a judgment call, not a limitation this task ran out of scope to
fix: doing so would mean reaching into SDK-internal `func_metadata`
construction, a materially larger and more fragile change than this fix
cycle's scope, for a security-neutral gap) -- flagged for the security
gate to weigh in on, per this task's own disposition table.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
from collections.abc import Mapping
from typing import Any, Literal

from research_foundry import ids
from research_foundry.errors import RFError
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_operation_service import OperatorOperationService

__all__ = ["UnsupportedTransportError", "build_server"]

logger = logging.getLogger(__name__)

_MISSING_SDK_MSG = (
    "The 'mcp' Python SDK is not installed. The Research Foundry Operator "
    "MCP server is an optional surface; install it with:\n"
    "    uv sync --extra mcp\n"
    "or\n"
    "    pip install 'research-foundry[mcp]'"
)

# Closed literal types for the two enum-shaped `operation.preflight`
# arguments (D4 "closed input schemas") -- built FROM the policy module's
# own frozen tuples (single source of truth), never a second, independently
# hand-typed enum that could drift. `evaluate_policy`'s own `_check_capability`
# stage remains the AUTHORITATIVE runtime check either way (see
# `_preflight_tool` below); these annotations only make the ADVERTISED
# `list_tools()` schema strict too.
_OperationKindLiteral = Literal[*policy.OPERATION_KINDS]  # type: ignore[valid-type]
_SensitivityLiteral = Literal[*policy.SENSITIVITY_LEVELS]  # type: ignore[valid-type]

# D7: cheap, EARLY transport-level short-circuit on raw argument size,
# BEFORE any adapter/policy code runs -- mirrors `operator_mcp_policy`'s own
# private `_MAX_INPUT_PAYLOAD_BYTES` bound BY VALUE, not import (this module
# never imports a private, underscore-prefixed symbol from
# `operator_mcp_policy` -- the same convention `operator_mcp_adapters/
# __init__.py` documents for its own `_CEILING_CONFIG_SECTION`/
# `_CEILING_CONFIG_KEY`). `_check_capability` inside `evaluate_policy`
# remains the AUTHORITATIVE, later bound check over each adapter's OWN
# narrowed `ctx.input_payload`; this is defense-in-depth, not a
# replacement, and its numeric value is free to drift independently of the
# authoritative one without weakening anything (a stricter or looser
# transport-level short-circuit only changes how EARLY an oversized
# request is rejected, never whether it eventually is).
_MAX_TRANSPORT_ARGUMENT_BYTES = 65_536

# M2 fix cycle 1, F1.4 (TERRA-6): an explicit-stack (never recursive)
# nesting-depth cap, checked BEFORE `_check_transport_payload_size` ever
# calls `json.dumps` on caller-supplied `arguments` -- a naive recursive
# depth/size computation (or `json.dumps` itself, on sufficiently deep
# input) raises `RecursionError` on adversarially nested input, which
# escaped this module's D7 exception boundary entirely before this fix
# (TERRA-6's reproduction: `_check_transport_payload_size` called directly
# on a 100,000-level nested mapping). Generous headroom over any real tool
# argument shape (`input_payload` itself is capped at 32 top-level
# properties elsewhere; nothing in this transport's own schemas nests more
# than a handful of levels).
_MAX_ARGUMENT_DEPTH = 32

_ALLOWED_TRANSPORTS: tuple[str | None, ...] = (None, "stdio")

# M2 fix cycle 2, SEC-2 (HIGH) -- partial, server-layer bound on preflight
# mint volume. The security gate measured TERRA-1's persistence fix as an
# UNBOUNDED durable write path: 200 preflights with distinct idempotency
# keys -> 200 permanent `confirmations` rows (`confirmation_id` embeds
# fresh randomness, so nothing collapses/dedupes), no quota, no eviction,
# no expiry sweep anywhere in `operator_operation_service.py` -- measured
# sustained throughput 25.5 MiB/min. `operator_operation_service.py` is
# OFF LIMITS this fix cycle (hard boundary), so the durable fix this
# defect really wants -- a `status='issued' AND expires_at < now` sweep on
# write, or a dedupe-by-`(canonical_input_digest, idempotency_key)` upsert
# -- cannot be implemented here. What CAN be owned entirely inside this
# file: a per-workspace sliding-window CAP on how many confirmations THIS
# process's preflight will mint, enforced BEFORE `mint_confirmation`/
# `record_confirmation` ever run (so a throttled request writes ZERO
# rows, the same "zero effect on denial" property every other preflight
# denial already has). This is explicitly a PARTIAL fix, not a substitute
# for the durable one: it is in-memory only (resets on process restart,
# per-`build_server()`-instance, never touches the 200+ rows a pre-fix run
# may have already written), and does not evict/reclaim anything already
# on disk. See the fix-cycle-2 completion note's SEC-2 section for the
# residual filed as a follow-up (a store-side TTL sweep or upsert, which
# belongs in `operator_operation_service.py`).
_PREFLIGHT_MINT_WINDOW_SECONDS = 60.0
_PREFLIGHT_MINT_MAX_PER_WINDOW = 20

# M2 fix cycle 1, F1.3 (TERRA-4): keyword names `_operation_tool`/
# `_preflight_tool` ALREADY supply explicitly and unconditionally to every
# `adapter.invoke(...)` call -- never legitimate `input_payload` keys (a
# caller-supplied duplicate collides as a raw `TypeError`, the exact
# TERRA-4 pre-fix symptom `_allowed_input_payload_keys` below now prevents
# by construction).
_SERVER_SUPPLIED_KEYS: frozenset[str] = frozenset(
    {"idempotency_key", "confirmation_record", "presented_token", "dry_run", "paths"}
)

# M2 fix cycle 1, F1.3 (TERRA-4): dependency-injection/test-only keyword
# names every P3 adapter's own `invoke*` signature declares (`now` for
# clock injection, `operations`/`cancel_resume`/`receipts`/`attempts` for
# service-double injection) -- NONE of these is a real caller-facing
# semantic parameter. TERRA-4's reproduction showed an in-process MCP
# caller could supply `now` via `input_payload` and reach a canonical
# service call. M2 fix cycle 2, SEC-6 correction: the pre-gate framing of
# this as "an authorization bypass" OVERSTATED what the security gate
# actually demonstrated on this transport -- MCP delivers `input_payload`
# values as JSON, so a caller-supplied `now` arrives as a `str`, not a
# `datetime`, and dies with `internal_error` (`AttributeError`) BEFORE
# reaching any expiry check; no expiry bypass was ever reachable this way.
# What IS real, and why this key is still rejected: (1) it poisons the
# canonical digest execute independently recomputes, so a preflighted
# confirmation using this path can never actually be consumed
# (`confirmation_mismatch`) -- an unconsumable, durably-persisted row, one
# of the SEC-2 write-amplification levers; (2) it is dependency-injection/
# test-only plumbing that has no caller-facing meaning at all, regardless
# of whether misusing it happens to be exploitable today. `now` in
# particular MUST always be server-derived (real wall-clock time, via
# `ids.now()` -- see the F1.1 companion fix below), never caller-supplied,
# as a matter of design hygiene, not because a live expiry-forgery path
# was ever proven reachable through this transport.
_DI_ONLY_KEYS: frozenset[str] = frozenset({"now", "operations", "cancel_resume", "receipts", "attempts"})

# M2 fix cycle 1, F1.3 (TERRA-4): (module attribute name on the `adapters`
# package, real function name) for every `OPERATION_KINDS` member's REAL
# `invoke*` function -- `_allowed_input_payload_keys` below derives each
# kind's allowlist from `inspect.signature` of the ACTUAL function this
# table points at, never a hand-typed, independently-driftable parameter
# list (the exact "guard was right but the parameter inventory was
# incomplete" defect class D8 warns about). Every `operator_mcp_adapters`
# submodule listed here is ALREADY imported (as a side effect of
# `operator_mcp_adapters/__init__.py`'s own registration-import block) by
# the time this module's `from research_foundry.services import
# operator_mcp_adapters as adapters` import above completes -- Python binds
# every imported submodule as an attribute of its parent package
# regardless of any `as`-alias used to import it, so `getattr(adapters,
# <module attribute name>)` below never triggers a fresh import.
_ADAPTER_INVOKE_TARGETS: dict[str, tuple[str, str]] = {
    "run.plan": ("run_plan", "invoke"),
    "swarm.start": ("swarm_start", "invoke"),
    "job.status": ("job_lifecycle", "invoke_status"),
    "job.cancel": ("job_lifecycle", "invoke_cancel"),
    "job.resume": ("job_lifecycle", "invoke_resume"),
    "external_report.import": ("external_import", "invoke"),
    "source.ingest": ("source_ingest", "invoke"),
    "run.extract": ("research_stages", "invoke_extract"),
    "run.claim_map": ("research_stages", "invoke_claim_map"),
    "run.synthesize": ("research_stages", "invoke_synthesize"),
    "run.verify": ("verify_bundle", "invoke_verify"),
    "run.bundle": ("verify_bundle", "invoke_bundle"),
    "writeback.preview": ("writeback_preview", "invoke_preview"),
}

if set(_ADAPTER_INVOKE_TARGETS) != set(policy.OPERATION_KINDS):  # pragma: no cover - import-time invariant
    raise RuntimeError(
        "operator_mcp.server: _ADAPTER_INVOKE_TARGETS must cover exactly "
        "operator_mcp_policy.OPERATION_KINDS -- no silent partial F1.3 "
        f"allowlist coverage, ever (diff: {set(_ADAPTER_INVOKE_TARGETS) ^ set(policy.OPERATION_KINDS)!r})."
    )

# Cache for :func:`_stdio_only_fastmcp_class`, keyed by the real
# `FastMCP` class it was derived from -- mirrors `knowledge_mcp/
# registry.py`'s own sentinel-cache pattern, reimplemented independently.
_cached_stdio_only_class: Any = None
_cached_stdio_only_base: Any = None


class UnsupportedTransportError(RFError):
    """Raised when a caller attempts to run `rf-operator-mcp` over a
    non-stdio transport (invariant 8) -- enforced at the code level, not
    only by convention. Mirrors `knowledge_mcp.registry.
    UnsupportedTransportError` in spirit but is NOT imported from it --
    this package never imports from `research_foundry.knowledge_mcp.*`."""


def _blocked_transport_message(name: str) -> str:
    return (
        f"{name}() is not supported by rf-operator-mcp. stdio is the only enforced "
        "transport (invariant 8). This server is a FastMCP SUBCLASS constructed "
        "directly by build_server(), not a delegating proxy -- there is no distinct "
        "wrapped instance for any bound method's __self__ to resolve to instead."
    )


def _canonical_json(payload: Mapping[str, Any]) -> str:
    """Same canonical-JSON convention `knowledge_mcp/registry.py`'s own
    `_canonical_json` uses -- reimplemented by value, not import."""

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _build_dual_encoder(call_tool_result_cls: Any, text_content_cls: Any) -> Any:
    """Return a `(payload, *, is_error=False) -> CallToolResult` closure
    bound to the SDK's real `CallToolResult`/`TextContent` classes -- both
    `_stdio_only_fastmcp_class`'s `call_tool` override and `build_server`'s
    own tool handlers build one of these from their OWN lazy `mcp.types`
    import (each only ever invoked after that import already succeeded),
    rather than importing `mcp.types` at this module's top level."""

    def _dual_encode(payload: Mapping[str, Any], *, is_error: bool = False) -> Any:
        return call_tool_result_cls(
            content=[text_content_cls(type="text", text=_canonical_json(payload))],
            structuredContent=dict(payload),
            isError=is_error,
        )

    return _dual_encode


def _mapping_depth(value: Any, *, limit: int) -> int:
    """Nesting depth of `value` (dict/list/tuple nesting only), computed
    with an EXPLICIT stack rather than recursion -- short-circuits as soon
    as `limit` is exceeded, so this can never itself raise `RecursionError`
    on adversarially deep input (M2 fix cycle 1, F1.4/TERRA-6: the exact
    failure mode this helper exists to prevent, previously reproduced by
    calling `json.dumps` -- CPython's own recursive serializer -- directly
    on a 100,000-level nested mapping)."""

    stack: list[tuple[Any, int]] = [(value, 0)]
    deepest = 0
    while stack:
        current, depth = stack.pop()
        if depth > deepest:
            deepest = depth
            if deepest > limit:
                return deepest
        if isinstance(current, Mapping):
            for nested in current.values():
                stack.append((nested, depth + 1))
        elif isinstance(current, (list, tuple)):
            for nested in current:
                stack.append((nested, depth + 1))
    return deepest


def _check_transport_payload_size(arguments: Mapping[str, Any]) -> policy.PolicyDecision | None:
    """`None` when `arguments` is within the transport-level bound;
    otherwise a `payload_too_large` denial. See this module's docstring's
    "Transport error mapping" section.

    M2 fix cycle 1, F1.4 (TERRA-6): the depth cap below runs BEFORE
    `json.dumps` ever touches `arguments`, using the non-recursive
    `_mapping_depth` walk -- a pathologically deep (but otherwise
    byte-small) argument mapping is rejected here, never reaches
    `json.dumps`, and therefore can never raise `RecursionError` on this
    path. This function's caller (`_StdioOnlyFastMCP.call_tool`) now also
    wraps this ENTIRE call inside its own outer exception boundary (F1.4's
    other half: "put all argument inspection inside the exception
    boundary"), so even an exhaustive future change to this function's own
    body cannot re-open TERRA-6 by escaping uncaught.
    """

    if _mapping_depth(arguments, limit=_MAX_ARGUMENT_DEPTH) > _MAX_ARGUMENT_DEPTH:
        return policy.PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    try:
        size = len(
            json.dumps(
                dict(arguments), ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
            ).encode("utf-8")
        )
    except (TypeError, ValueError, RecursionError):
        # Not even measurable -- let the real dispatch attempt run; a
        # genuinely malformed argument mapping will fail there too, mapped
        # to internal_error by the SAME call_tool override's outer
        # try/except (which now also wraps THIS call, per F1.4 above).
        return None
    if size > _MAX_TRANSPORT_ARGUMENT_BYTES:
        return policy.PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    return None


@functools.lru_cache(maxsize=None)
def _allowed_input_payload_keys(kind: str) -> frozenset[str]:
    """The set of semantic keyword-argument names `input_payload` may
    supply for operation kind `kind` -- derived via `inspect.signature`
    from the REAL `invoke*` function `_ADAPTER_INVOKE_TARGETS[kind]` names,
    minus `_SERVER_SUPPLIED_KEYS` (already threaded explicitly by
    `_make_operation_tool`/`_preflight_tool`) and `_DI_ONLY_KEYS`
    (dependency-injection/test-only, never caller-facing). M2 fix cycle 1,
    F1.3 (TERRA-4). Cached: `inspect.signature` is not free, and every
    `OPERATION_KINDS` member's allowlist is fixed for the process lifetime
    (the real functions it introspects are module-level, never
    monkeypatched mid-process in production)."""

    module_attr, func_name = _ADAPTER_INVOKE_TARGETS[kind]
    func = getattr(getattr(adapters, module_attr), func_name)
    return frozenset(
        name
        for name in inspect.signature(func).parameters
        if name not in _SERVER_SUPPLIED_KEYS and name not in _DI_ONLY_KEYS
    )


def _stdio_only_fastmcp_class(fastmcp_cls: type[Any]) -> type[Any]:
    """Return the `_StdioOnlyFastMCP` subclass of `fastmcp_cls` (cached).
    See this module's docstring's "Stdio-only transport guard" and
    "Transport error mapping" sections. Mirrors `knowledge_mcp/registry.py`'s
    own `_stdio_only_fastmcp_class` shape by value, not import."""

    global _cached_stdio_only_class, _cached_stdio_only_base
    if _cached_stdio_only_class is not None and _cached_stdio_only_base is fastmcp_cls:
        return _cached_stdio_only_class

    from mcp.types import CallToolResult, TextContent  # type: ignore[import-not-found]

    dual_encode = _build_dual_encoder(CallToolResult, TextContent)

    class _StdioOnlyFastMCP(fastmcp_cls):  # type: ignore[misc]
        """`FastMCP` restricted to the `stdio` transport (invariant 8),
        with the D7 transport-error-mapping chokepoint (`call_tool`)."""

        def sse_app(self, mount_path: str | None = None) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("sse_app"))

        def streamable_http_app(self) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("streamable_http_app"))

        # Deliberately NOT `async def` -- see `knowledge_mcp/registry.py`'s
        # identical override for why a plain function raises strictly
        # earlier than an `async def` override would (the call itself
        # raises before there is ever a coroutine object left to await).
        def run_sse_async(self, mount_path: str | None = None) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_sse_async"))

        def run_streamable_http_async(self) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_streamable_http_async"))

        def run(self, transport: str | None = "stdio", mount_path: str | None = None) -> None:
            if transport not in _ALLOWED_TRANSPORTS:
                raise UnsupportedTransportError(
                    f"Non-stdio MCP transport {transport!r} is not supported by "
                    "rf-operator-mcp (invariant 8). Direct network-transport mounts "
                    "(sse/streamable-http) are refused at the code level, not only by "
                    "convention."
                )
            super().run(transport=transport or "stdio", mount_path=mount_path)  # type: ignore[misc]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            """D7's ONE dispatch chokepoint -- every real stdio request AND
            every direct `server.call_tool(...)` test call goes through
            this method (`FastMCP.__init__` registers the OVERRIDDEN bound
            method -- `self._mcp_server.call_tool(...)(self.call_tool)` --
            as the low-level protocol server's own handler; confirmed
            against the installed 1.x SDK's source).

            M2 fix cycle 1, F1.4 (TERRA-6): the tool-name check and the
            payload-size/depth check now run INSIDE the SAME outer
            `try/except Exception` boundary as the real dispatch below --
            previously `_check_transport_payload_size` ran BEFORE (outside)
            this boundary, so an adversarially deep argument mapping could
            raise `RecursionError` straight through this method, uncaught.
            `_check_transport_payload_size` is now itself depth-capped
            (never recurses), but this is defense in depth on top of that
            fix, not a replacement for it: "put all argument inspection
            inside the exception boundary" per the F1.4 disposition.
            """

            try:
                name_decision = policy.check_tool_name(name)
                if name_decision.denied:
                    return dual_encode(policy.build_error(name_decision), is_error=True)

                size_decision = _check_transport_payload_size(arguments or {})
                if size_decision is not None:
                    return dual_encode(policy.build_error(size_decision), is_error=True)

                return await super().call_tool(name, arguments)  # type: ignore[misc]
            except Exception as exc:  # noqa: BLE001 -- the ONE D7 internal_error boundary
                logger.warning(
                    "operator_mcp.server: internal_error dispatching tool %r (%s)",
                    name,
                    type(exc).__name__,
                )
                decision = policy.PolicyDecision(False, "capability", "internal_error", retryable=True)
                return dual_encode(policy.build_error(decision), is_error=True)

    _cached_stdio_only_class = _StdioOnlyFastMCP
    _cached_stdio_only_base = fastmcp_cls
    return _StdioOnlyFastMCP


def _close_input_schema(server: Any, name: str) -> None:
    """Best-effort tightening of one registered tool's ADVERTISED input
    schema to `additionalProperties: false` (D4) -- mirrors `knowledge_mcp/
    registry.py`'s own `_close_input_schema` by value, not import.
    Intentionally best-effort (guarded by `AttributeError`/`KeyError`)
    against the SDK's own internal `_tool_manager`/`Tool.parameters` shape
    ever changing; correct denial behavior never depends on it succeeding
    (the real, authoritative bound checks are `_check_capability` and each
    adapter's own `invoke()` signature, both unaffected by this schema
    annotation)."""

    try:
        tool = server._tool_manager.get_tool(name)
        if tool is not None:
            tool.parameters = {**tool.parameters, "additionalProperties": False}
    except (AttributeError, KeyError):  # pragma: no cover - defensive only
        logger.debug("Could not tighten input schema for tool %r (SDK internals changed).", name)


def build_server(paths: FoundryPaths | None = None) -> Any:
    """Construct and return a guarded, stdio-only `FastMCP` server with the
    exact 14-tool inventory registered (D4): the 13 `OPERATION_KINDS`, each
    a thin dispatch to `operator_mcp_adapters.get_adapter(kind)`, plus the
    server-implemented `operation.preflight` meta tool (D5).

    Lazily imports the `mcp` SDK; raises :class:`RuntimeError` with a clear
    install hint if it is missing (see :data:`_MISSING_SDK_MSG`). Raises a
    DIFFERENT, equally clear :class:`RuntimeError` if any `OPERATION_KINDS`
    member lacks a registered adapter (D4's fail-loud, no-silent-partial-
    server guarantee) -- see this module's docstring's "Leg A/B integration
    note" for why this is EXPECTED today (`writeback.preview` not yet
    registered by Leg A).

    ``paths`` defaults to :meth:`FoundryPaths.discover` when omitted; tests
    pass an explicit :class:`FoundryPaths` pointed at a fixture workspace.
    """

    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError as exc:  # noqa: BLE001 - re-raise as a clear runtime error
        raise RuntimeError(_MISSING_SDK_MSG) from exc

    from mcp.types import CallToolResult, TextContent  # type: ignore[import-not-found]

    resolved_paths = paths if paths is not None else FoundryPaths.discover()

    # M2 fix cycle 1, F1.1 (TERRA-1): the ONE `OperatorOperationService`
    # instance `_preflight_tool` durably persists every minted confirmation
    # through (`record_confirmation`) -- built once per server, over the
    # SAME `resolved_paths` every operation tool already dispatches
    # against, so a confirmation minted by THIS server instance's preflight
    # is persisted to the SAME `.rf_state/operator_operations.db` an
    # execute call against THIS server instance's operation tools reads
    # from (`operator_mcp_adapters.base.run_pipeline`'s own `operations or
    # OperatorOperationService(resolved_paths)` fallback resolves to an
    # equivalent connection over the same file).
    operations = OperatorOperationService(resolved_paths)

    # M2 fix cycle 2, SEC-2: per-`build_server()`-instance (never module-
    # level -- module-level state would leak across tests/servers in the
    # same process) sliding-window mint history, keyed by workspace_id.
    # See `_PREFLIGHT_MINT_WINDOW_SECONDS`/`_PREFLIGHT_MINT_MAX_PER_WINDOW`'s
    # own comment for the full SEC-2 rationale and residual.
    _preflight_mint_history: dict[str, list[float]] = {}

    def _preflight_mint_rate_limited(workspace_id: str | None) -> bool:
        """`True` when minting one more confirmation for `workspace_id`
        would exceed `_PREFLIGHT_MINT_MAX_PER_WINDOW` within the trailing
        `_PREFLIGHT_MINT_WINDOW_SECONDS` -- records this attempt as
        counting toward the window ONLY when it is allowed (a denied
        attempt must not itself consume quota, mirroring every other
        preflight denial's zero-effect property). Uses `ids.now()` -- the
        SAME canonical clock `mint_confirmation`/`record_confirmation` are
        threaded with above -- never a bare `time.time()`/`datetime.now()`
        read, so this stays correctly inert under the test suite's pinned
        clock rather than silently never expiring entries (or expiring
        them all immediately) against a clock nothing else in this
        request agrees with."""

        key = workspace_id or ""
        now_ts = ids.now().timestamp()
        cutoff = now_ts - _PREFLIGHT_MINT_WINDOW_SECONDS
        history = _preflight_mint_history.setdefault(key, [])
        history[:] = [ts for ts in history if ts >= cutoff]
        if len(history) >= _PREFLIGHT_MINT_MAX_PER_WINDOW:
            return True
        history.append(now_ts)
        return False

    missing = [kind for kind in policy.OPERATION_KINDS if adapters.get_adapter(kind) is None]
    if missing:
        raise RuntimeError(
            "operator_mcp.server.build_server: missing adapter registration for "
            f"operation kind(s) {missing!r} -- every member of "
            "operator_mcp_policy.OPERATION_KINDS must be registered in "
            "operator_mcp_adapters before this server can be built (D4: no "
            "silent, partial 13/14-tool server, ever)."
        )

    StdioOnlyFastMCP = _stdio_only_fastmcp_class(FastMCP)
    server = StdioOnlyFastMCP("rf-operator-mcp")

    dual_encode = _build_dual_encoder(CallToolResult, TextContent)

    def _adapter_result_payload(outcome: Any) -> dict[str, Any]:
        return {"ok": bool(outcome.ok), "operation_id": outcome.operation_id, "result": outcome.result}

    def _make_operation_tool(kind: str) -> Any:
        def _operation_tool(
            idempotency_key: str,
            input_payload: dict[str, Any] | None = None,
            confirmation_record: dict[str, Any] | None = None,
            presented_token: str | None = None,
            dry_run: bool = False,
        ) -> Any:
            adapter = adapters.get_adapter(kind)
            if adapter is None:  # pragma: no cover - build_server's own fail-loud check makes this unreachable
                decision = policy.PolicyDecision(False, "capability", "operation_unknown", retryable=False)
                return dual_encode(policy.build_error(decision), is_error=True)

            payload = input_payload or {}
            rejected_keys = set(payload) - _allowed_input_payload_keys(kind)
            if rejected_keys:
                # M2 fix cycle 1, F1.3 (TERRA-4): explicit, bounded
                # rejection of any `input_payload` key that is not a
                # declared semantic parameter of `kind`'s REAL `invoke*`
                # signature -- this closes BOTH DI-injection (e.g. a
                # caller-supplied `now` reaching a canonical service; see
                # `_DI_ONLY_KEYS`'s own comment, M2 fix cycle 2/SEC-6, for
                # why this is digest-poisoning/write-amplification hygiene
                # rather than a proven expiry-authorization bypass on this
                # transport) AND the accidental, fragile "colliding key
                # raises TypeError, which happens to
                # get mapped to internal_error" behavior the pre-fix D7
                # boundary relied on for the SAME collision (never a
                # deliberate rejection). `payload_too_large` is reused here,
                # not invented: `operator_mcp_policy._check_capability`
                # already uses this SAME reason code for the sibling
                # "input_payload does not conform to what capability
                # accepts" condition (its own maxProperties bound) -- see
                # this module's docstring's "F1.3" section.
                decision = policy.PolicyDecision(False, "capability", "payload_too_large", retryable=False)
                return dual_encode(policy.build_error(decision), is_error=True)

            outcome = adapter.invoke(
                idempotency_key=idempotency_key,
                confirmation_record=confirmation_record,
                presented_token=presented_token,
                dry_run=dry_run,
                paths=resolved_paths,
                **payload,
            )
            if not outcome.ok:
                # D7: adapter-returned error envelopes pass through
                # UNTOUCHED -- outcome.error is already a build_error-built
                # operator_mcp_error instance; this handler adds nothing.
                return dual_encode(dict(outcome.error or {}), is_error=True)
            return dual_encode(_adapter_result_payload(outcome), is_error=False)

        _operation_tool.__name__ = kind.replace(".", "_").replace("-", "_")
        _operation_tool.__doc__ = (
            f"Operator MCP `{kind}` tool (M2, OPM-5.1/5.2/5.4). Thin dispatch to "
            "`operator_mcp_adapters.get_adapter(kind).invoke(**kwargs)` -- "
            "`input_payload`'s keys become that adapter's own kind-specific "
            "keyword arguments. Every caller input flows through the SAME "
            "P1-P3 authorize -> consume -> execute pipeline this transport "
            "does not modify."
        )
        return _operation_tool

    for _kind in policy.OPERATION_KINDS:
        server.tool(name=_kind, structured_output=False)(_make_operation_tool(_kind))

    def _preflight_tool(
        operation_kind: _OperationKindLiteral,
        idempotency_key: str,
        effective_sensitivity: _SensitivityLiteral,
        targets: list[dict[str, str]] | None = None,
        input_payload: dict[str, Any] | None = None,
        policy_snapshot_version: str = "policy-order-v1",
    ) -> Any:
        """`operation.preflight` -- evaluate + mint, never consume, zero
        effect. See this module's docstring's "operation.preflight"
        section for the full contract."""

        if operation_kind not in policy.OPERATION_KINDS:  # defense in depth; schema already restricts this
            decision = policy.PolicyDecision(False, "capability", "operation_unknown", retryable=False)
            return dual_encode(policy.build_error(decision), is_error=True)

        # M2 fix cycle 1, F1.3 (TERRA-4): the SAME per-kind allowlist
        # `_operation_tool` enforces, applied here too -- a preflight that
        # accepted an `input_payload` shape execute would later reject
        # could mint a confirmation for a request that can never actually
        # be consumed, and (more sharply) preflight's `ctx.input_payload`
        # feeds `canonical_digest()` the SAME way execute's does, so an
        # unvalidated DI/reserved key here would poison the digest a real
        # execute call could never reproduce anyway. Checked BEFORE the
        # `targets` loop so a malformed `input_payload` is never partially
        # processed.
        payload = input_payload or {}
        if set(payload) - _allowed_input_payload_keys(operation_kind):
            decision = policy.PolicyDecision(False, "capability", "payload_too_large", retryable=False)
            return dual_encode(policy.build_error(decision), is_error=True)

        target_refs: list[policy.TargetRef] = []
        for raw_target in targets or []:
            kind_value = raw_target.get("target_kind") if isinstance(raw_target, dict) else None
            ref_value = raw_target.get("target_ref") if isinstance(raw_target, dict) else None
            if not isinstance(kind_value, str) or not isinstance(ref_value, str):
                decision = policy.PolicyDecision(False, "capability", "target_invalid", retryable=False)
                return dual_encode(policy.build_error(decision), is_error=True)
            target_refs.append(policy.TargetRef(kind_value, ref_value))

        # M2 fix cycle 1, F1.2 (TERRA-2): `writeback.preview` cannot mint a
        # USABLE confirmation without a non-empty `writeback_targets` --
        # `_check_preflight` denies `preflight_failed` otherwise, and (even
        # if it did not) an empty `writeback_targets` would leave every
        # `governance.guard_check` writeback-review rule structurally
        # unable to fire (see `PolicyContext`'s own docstring, "BLOCK-7").
        # Sourced from `input_payload["targets"]` -- the SAME key
        # `writeback_preview.invoke_preview`'s own `targets` parameter
        # receives when a caller later presents this SAME `input_payload`
        # to execute -- and normalized (sorted + deduplicated) the
        # IDENTICAL way `invoke_preview` normalizes its own, so the
        # `input_payload` baked into this ctx's canonical digest is
        # byte-identical to the one execute independently reconstructs
        # (F1.5's e2e test proves this binds). Validated against
        # `writeback.WRITEBACK_TARGET_NAMES` -- the closed, six-member
        # vocabulary Leg 2 owns and built specifically for this cross-leg
        # coordination point (see `m2-fix-contract.md`'s "Cross-leg
        # coordination" section and that constant's own docstring) -- never
        # a second, independently-typed vocabulary.
        writeback_targets: tuple[str, ...] = ()
        if operation_kind == "writeback.preview":
            from research_foundry.services import writeback as _writeback  # lazy: keeps this module's frozen module-level import boundary (D1) unchanged, mirrors every P3 adapter's own lazy-import convention for this exact module

            raw_preview_targets = payload.get("targets")
            # A genuinely ABSENT `targets` key is left to `_check_preflight`'s
            # own existing empty-`writeback_targets` -> `preflight_failed`
            # check below (unchanged pre-fix behavior for that specific
            # case) -- `target_invalid` here is reserved for a `targets` key
            # that IS present but malformed-shaped or names an out-of-
            # vocabulary target, a DIFFERENT failure mode than "omitted
            # entirely".
            if raw_preview_targets is not None:
                if not isinstance(raw_preview_targets, list) or not all(
                    isinstance(t, str) for t in raw_preview_targets
                ):
                    decision = policy.PolicyDecision(False, "capability", "target_invalid", retryable=False)
                    return dual_encode(policy.build_error(decision), is_error=True)
                normalized_preview_targets = tuple(sorted({str(t) for t in raw_preview_targets}))
                if any(t not in _writeback.WRITEBACK_TARGET_NAMES for t in normalized_preview_targets):
                    decision = policy.PolicyDecision(False, "capability", "target_invalid", retryable=False)
                    return dual_encode(policy.build_error(decision), is_error=True)
                writeback_targets = normalized_preview_targets
                payload = {**payload, "targets": list(normalized_preview_targets)}

        # Judgment call -- see this module's docstring's "operation.preflight"
        # section and this task's completion note (D8 table): every
        # declared target's `resolved_target_workspaces` entry is resolved
        # OPTIMISTICALLY to the operator's OWN `identity.workspace_id`
        # (never caller-supplied). Structurally safe: `resolved_target_
        # workspaces` is excluded from `PolicyContext.canonical_payload()`
        # and from `mint_confirmation`'s own record construction, so this
        # preview-only guess can never weaken the REAL execute-time
        # `authorize_operation()` a target-bearing kind's own adapter
        # independently reconstructs from real domain state.
        preview_identity = policy.resolve_operator_identity(resolved_paths)
        workspace_guess = preview_identity.workspace_id if preview_identity is not None else None
        resolved_target_workspaces = tuple(workspace_guess for _ in target_refs)

        ctx = policy.PolicyContext.for_configured_operator(
            operation_kind=operation_kind,
            idempotency_key=idempotency_key,
            effective_sensitivity=effective_sensitivity,
            sensitivity_ceiling=adapters.resolve_local_sensitivity_ceiling(resolved_paths),
            targets=tuple(target_refs),
            resolved_target_workspaces=resolved_target_workspaces,
            input_payload=payload,
            writeback_targets=writeback_targets,
            policy_snapshot_version=policy_snapshot_version,
            paths=resolved_paths,
        )

        decision = policy.evaluate_policy(ctx, paths=resolved_paths)
        if decision.denied:
            return dual_encode(policy.build_error(decision), is_error=True)

        if operation_kind in policy.CONFIRMATION_NOT_REQUIRED_KINDS:
            return dual_encode({"allowed": True, "confirmation": None}, is_error=False)

        # M2 fix cycle 2, SEC-2 (HIGH): the per-workspace mint-volume cap
        # -- checked BEFORE `mint_confirmation`/`record_confirmation` run,
        # so a throttled request writes ZERO rows, matching every other
        # preflight denial's zero-effect property. `preflight_failed` is
        # reused (not invented -- the closed reason-code enum is frozen):
        # it is this module's existing general-purpose "the preflight
        # stage cannot proceed" bucket (already used for missing required
        # targets and empty `writeback_targets`), and this IS a
        # preflight-stage-level condition, `retryable=True` because the
        # window rolls forward. See `_PREFLIGHT_MINT_MAX_PER_WINDOW`'s own
        # comment for why this is a PARTIAL bound, not the durable fix.
        workspace_key = ctx.identity.workspace_id if ctx.identity is not None else None
        if _preflight_mint_rate_limited(workspace_key):
            decision = policy.PolicyDecision(False, "preflight", "preflight_failed", retryable=True)
            return dual_encode(policy.build_error(decision), is_error=True)

        # M2 fix cycle 1, F1.1 companion fix (discovered while proving F1.5's
        # e2e test): `mint_confirmation`'s own docstring says its `now`
        # parameter is the clock-injection seam "P2/P5 MUST NEVER thread a
        # caller-/request-supplied timestamp through" -- but P5 (this
        # server) still owns choosing WHICH clock source it threads by
        # default, and `mint_confirmation` itself falls back to
        # `datetime.now(timezone.utc)` (a bare wall-clock read) when `now`
        # is omitted, while the P2 CONSUME side (`OperatorOperationService.
        # consume_and_create_operation`) always uses `research_foundry.ids.
        # now()` -- this repo's ONE injectable clock (`ids.set_clock()`,
        # pinned for the whole test suite by `tests/conftest.py`'s autouse
        # `_fixed_clock` fixture). Omitting `now=` here left mint and
        # consume reading TWO DIFFERENT clocks: harmless in production
        # (both read real wall time), but under the test suite's pinned
        # clock every confirmation minted this way is `issued_at` in the
        # FUTURE relative to consume's `moment` -- `operator_mcp_policy.
        # _record_expiry`'s NEW-7 anti-forgery check (`if issued_at >
        # moment: return None`) then treats it as unconditionally expired,
        # regardless of order or elapsed time. `ids.now()` is this
        # module's own top-level import (offline-safe, no `mcp` SDK
        # dependency) -- passing it here makes mint and consume agree on
        # the SAME clock source always, test or production.
        issued = policy.mint_confirmation(ctx, paths=resolved_paths, now=ids.now())
        # M2 fix cycle 1, F1.1 (TERRA-1): durably persist the minted
        # confirmation BEFORE returning it -- the ONLY way a later execute
        # call's `consume_and_create_operation` (which looks this record up
        # by `confirmation_id` in the SAME `confirmations` table) can ever
        # find it; pre-fix, NOTHING on this path ever called
        # `record_confirmation`, so no normal preflight -> execute flow
        # through this transport could ever consume its own confirmation
        # (F1.5's e2e test proves the fix; the SAME test, run against a
        # pre-fix scratch copy, fails with `confirmation_missing`). A
        # persistence failure (e.g. `ConfirmationPersistenceError` on lock
        # contention/store unavailability) is deliberately left to
        # propagate OUT of this function -- through the SDK's own
        # tool-dispatch wrapper, into `_StdioOnlyFastMCP.call_tool`'s outer
        # `except Exception` boundary (F1.4) -- surfacing as a governed,
        # bounded `internal_error` envelope, never a silent success. This
        # preflight still performs NO OTHER effect: no operation manifest,
        # no receipt, no adapter action -- only this one durable row, and
        # only for confirmation-requiring kinds that reach this line.
        operations.record_confirmation(issued.record)
        return dual_encode(
            {"allowed": True, "confirmation": {"token": issued.token, "record": issued.record}},
            is_error=False,
        )

    server.tool(name=policy.PREFLIGHT_TOOL_NAME, structured_output=False)(_preflight_tool)

    for _name in policy.TOOL_NAMES:
        _close_input_schema(server, _name)

    # `server` is already a `_StdioOnlyFastMCP` instance (constructed
    # above, before any `@server.tool()`-equivalent registration) -- no
    # separate wrap/guard step is needed or performed here.
    return server
