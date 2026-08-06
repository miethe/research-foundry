"""Attribution-fetch seam — inert by default; gated real fetch for dev/test.

This package is the deferred "Phase C" fetch path named by
``docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md``
(the "source-metadata-propagation-v1" PRD, §7 deferrals table). By DEFAULT it
issues **no network call under any input combination**, including with any
provider or the umbrella ``attribution_fetch_enabled`` flag enabled — see
``FoundryConfig.attribution_fetch_controls()`` (``src/research_foundry/
config.py``) for that (also hard-off-by-default) config flag, which gates
*visibility* of this package's intent, not its network reachability.

Two gates keep real provider fetch off by default. Neither is closed by this
package, by any doc this package touches, or by any tracker entry this
package touches:

DEF-1
    Per-provider license terms verified for bundle redistribution — NOT
    yet true. PRD §7: "``defer-until: per-provider license terms verified
    for bundle redistribution.`` Propagation architecture is proven
    independent of what feeds it; ingestion itself is the licensing-gated
    piece." Until each provider's terms are independently verified for RF's
    specific redistribution model, no adapter in this package may fetch,
    cache, or redistribute a live third-party value **for redistribution**.

DEF-6
    Live ToS re-verification for Semantic Scholar / NCBI — NOT yet done.
    PRD §7: "Licensing table in risk-findings.md is stated from general
    domain knowledge of these programs' public policies, not re-verified
    against live current ToS pages." This is explicitly **not legal
    advice**, and nothing in this package should be read as a licensing or
    legal determination for any provider.

Clearance-gates M3: the dev/test live-fetch escape hatch
----------------------------------------------------------
``foundry.dev_test_posture.live_fetch_enabled`` (:meth:`FoundryConfig.
dev_test_posture_live_fetch_enabled`) is a SEPARATE, explicit, auditable
operator opt-in that permits a REAL live provider fetch for LOCAL
development/testing only. It does not close DEF-1 or DEF-6, and it does not
assert any license posture for any provider — see that method's own
docstring. Every adapter's :func:`fetch` call takes this decision from a
``config`` argument:

* ``config=None`` (the default, and every pre-M3 caller) — BYTE-FOR-BYTE the
  pre-M3 behaviour: no socket, HTTP client, or DNS lookup is ever touched.
* ``config`` supplied but the posture resolves ``False`` — identical to the
  above.
* ``config`` supplied and the posture resolves ``True`` — a real HTTP GET is
  issued (stdlib ``urllib.request`` only) and the result is stamped with a
  durable clearance taint (:func:`~research_foundry.services.clearance.
  stamp_taint`) UNCONDITIONALLY, at fetch time, before being returned. That
  stamp is never re-derived later; a subsequent posture flip or gate closure
  cannot retroactively release a record already fetched this way (design
  invariant 2 in ``docs/project_plans/implementation_plans/infrastructure/
  clearance-gates-v1.md``).

This posture opens ONLY ``redistribution`` (never ``acquisition``, never
implicitly). :data:`PROVIDER_GATE_SCOPE` is the static map that makes this
true by construction rather than by runtime check: DEF-2's vendors (Scopus /
Web of Science / JCR / SCImago) are absent from that map because no adapter
module for them exists anywhere in this package — there is no key to add
without first building a reviewable new module, and no amount of posture
flipping can open a scope for a provider this package cannot reach.

Non-laundering guarantee (UNCHANGED by M3)
--------------------------------------------
Every provider adapter's public entrypoint (``fetch()``) returns EITHER the
existing :class:`ProviderFetchResult` — a value-free, disabled/no-op result
carrying only ``provider``, ``status`` (``"disabled"``), and a human
``reason`` — OR, only on the gated dev/test-posture path, the NEW
:class:`ClearedProviderFetchResult`. ``ProviderFetchResult`` still has **no**
``value``, ``asserter_type``, or ``license_basis`` attribute of any kind —
that type's value-free shape was never touched by this change and remains
the non-laundering guarantee for every caller that does not opt into the
posture. ``ClearedProviderFetchResult`` is a genuinely different, separate
type specifically for the dev/test escape hatch; a caller holding a bare
``ProviderFetchResult`` still cannot extract a third-party value from it. A
caller wanting to author a real ``source_attribution`` record still has to
independently construct a full record satisfying ``schemas/
source_attribution.schema.yaml`` — including its ``if asserter_type
startsWith "third_party_" then retrieval_evidence_ref required`` gate —
exactly as before this package existed; neither result type is a shortcut
around that schema gate.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from ...errors import AdapterError, SchemaError
from ...frontmatter import dump_md, load_md
from ...paths import FoundryPaths, distribution_root
from ...schemas import SchemaRegistry
from ..clearance import (
    BLOCKED_SCOPES_KEY,
    BLOCKING_SCOPES,
    TAINT_KEY,
    ClearanceConfigError,
    stamp_taint,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ...config import FoundryConfig

#: The only status value ``ProviderFetchResult`` can currently produce.
#: Reserved for future non-disabled statuses once DEF-1/DEF-6 close and a
#: real, unconditional implementation lands — neither exists yet.
DISABLED_STATUS = "disabled"

#: Status carried by :class:`ClearedProviderFetchResult` — a real fetch
#: actually happened, under the dev/test posture only.
FETCHED_STATUS = "fetched"

#: Static provider -> blocked-use-scope map (clearance-gates M3). NOT
#: derived from ``GateRegistry`` and never consulted at ``mediate_egress``
#: time. DEF-2 vendors (Scopus / Web of Science / JCR / SCImago) are absent
#: BY CONSTRUCTION: no adapter module for them exists in this package, so
#: there is no key to add here, and none should be added without first
#: building a reviewable new module. The dev/test posture must never be
#: able to open ``acquisition`` for any provider — this map only ever
#: carries ``"redistribution"``.
#:
#: A ``MappingProxyType``, NOT a plain ``dict`` (round 1, finding B4):
#: item-assignment/deletion on THIS object raise ``TypeError``. Round 2
#: found that insufficient on its own — Python has no real access control,
#: so an importer can still mutate ``_PROVIDER_GATE_SCOPE_DATA`` (the plain
#: dict this proxy wraps) in place, or rebind the module attribute
#: ``PROVIDER_GATE_SCOPE`` itself to point at a different mapping entirely.
#: Round 2's fix does NOT try to further harden this object (an unwinnable
#: goal by the same "no access control" argument) — instead,
#: :func:`stamp_dev_test_fetch` below no longer reads this map's VALUES to
#: decide what a stamp blocks at all, so neither mutation has anything to
#: corrupt. This map remains the known-providers set
#: :func:`authorize_live_fetch` validates against, and public documentation
#: of each provider's nominal scope — but it is advisory/provenance only
#: with respect to stamping.
_PROVIDER_GATE_SCOPE_DATA: dict[str, str] = {
    "openalex": "redistribution",
    "crossref": "redistribution",
    "semantic_scholar": "redistribution",
}
PROVIDER_GATE_SCOPE: "MappingProxyType[str, str]" = MappingProxyType(_PROVIDER_GATE_SCOPE_DATA)

#: Static, advisory-only provenance hint for a stamp's ``gate_refs``
#: (clearance-gates M3) — the DEF-* gate ids in ``config/
#: clearance_gates.yaml`` that motivated ``PROVIDER_GATE_SCOPE``'s
#: "redistribution" entry for each provider. Hardcoded for the same reason
#: ``PROVIDER_GATE_SCOPE`` is static: :func:`~research_foundry.services.
#: clearance.stamp_taint` never consults the registry's LIVE state, and
#: ``gate_refs`` plays no role in any enforcement decision — see that
#: function's docstring. Private (not exported), but frozen the same way
#: for consistency and defense in depth.
_PROVIDER_GATE_REFS: "MappingProxyType[str, tuple[str, ...]]" = MappingProxyType(
    {
        "openalex": ("DEF-1",),
        "crossref": ("DEF-1",),
        "semantic_scholar": ("DEF-1", "DEF-3", "DEF-6"),
    }
)

#: Hard cap on a provider response body, applied BEFORE ``json.loads`` is
#: ever called. Untrusted-input handling is explicitly in scope for M3:
#: every byte read by :func:`_fetch_json` originates from a third-party HTTP
#: server, never from this codebase, and a hostile/oversized response is
#: refused outright rather than buffered without bound.
MAX_RESPONSE_BYTES = 1_000_000

#: Hard timeout on the dev/test live fetch. Never omitted — an unbounded
#: request would hang a CLI/test process indefinitely.
REQUEST_TIMEOUT_SECONDS = 10.0

#: Hosts a real dev/test fetch may ever contact (clearance-gates M3
#: CHANGES_REQUESTED review, finding M4 — SSRF via provider-controlled
#: redirects). Every URL passed to :func:`_fetch_json` is validated against
#: this allowlist (scheme MUST be ``https``, host MUST be exactly one of
#: these) BEFORE any socket is opened, and every redirect response is
#: refused outright rather than followed (see ``_NoRedirectHandler``) — a
#: compromised or intercepted provider endpoint cannot use a 3xx response
#: to redirect this process to an internal/metadata address
#: (``169.254.169.254``, ``127.0.0.1``, ...).
_ALLOWED_PROVIDER_HOSTS: frozenset[str] = frozenset(
    {"api.openalex.org", "api.crossref.org", "api.semanticscholar.org"}
)


@dataclass(frozen=True)
class ProviderFetchResult:
    """Value-free result returned by every provider adapter's ``fetch()``
    on the (default) disabled path.

    Deliberately carries no ``value``, ``asserter_type``, or
    ``license_basis`` field — see the module docstring's "Non-laundering
    guarantee". A caller cannot extract a third-party value from this type
    because it never carries one; there is nothing here to write into a
    governed field. UNCHANGED by clearance-gates M3 — the gated real-fetch
    path returns :class:`ClearedProviderFetchResult` instead, never this
    type with a bolted-on value.
    """

    provider: str
    status: str
    reason: str


@dataclass(frozen=True)
class ClearedProviderFetchResult:
    """Result of a REAL provider fetch under the dev/test live-fetch
    posture (clearance-gates M3). NEVER returned unless the caller supplied
    a ``config`` whose ``dev_test_posture_live_fetch_enabled()`` resolved
    ``True``.

    Deliberately a SEPARATE type from :class:`ProviderFetchResult` rather
    than a ``value`` field bolted onto it — that type's value-free shape is
    the existing non-laundering guarantee (see the module docstring), and a
    caller holding a plain ``ProviderFetchResult`` must remain structurally
    unable to extract a third-party value regardless of what this type
    does.

    ``value`` is a plain, defensively-parsed ``dict`` — never an instance of
    a provider's documented ``*RawResponse`` dataclass (those remain
    reserved, never-instantiated scaffolding; see each adapter module's
    docstring and ``tests/test_attribution_fetch_seam.py::
    test_raw_response_shape_is_never_instantiated_by_this_module``).

    ``clearance`` is the durable taint block
    (``schemas/clearance_taint.schema.yaml`` shape) produced by
    :func:`~research_foundry.services.clearance.stamp_taint` at
    construction time, UNCONDITIONALLY — every instance of this type
    carries one; there is no code path that constructs this type without
    also stamping it.
    """

    provider: str
    status: str
    value: dict[str, Any]
    clearance: dict[str, Any]

    def to_record(self) -> dict[str, Any]:
        """Projection directly consumable by ``clearance.mediate_egress``.

        NOT a schema-valid ``source_attribution`` record on its own — it
        lacks ``attribution_id``/``source``/``asserter_id``/etc.; authoring
        a full record from a fetched value is a separate, later concern.
        This carries exactly what ``mediate_egress``'s internal
        ``_blocked_scopes_of`` reads (the ``clearance`` block) plus enough
        provenance (``provider``, ``status``, ``value``) for a caller to
        inspect what was fetched.
        """

        return {
            "provider": self.provider,
            "status": self.status,
            "value": dict(self.value),
            "clearance": dict(self.clearance),
        }


def disabled_result(provider: str, reason: str) -> ProviderFetchResult:
    """Build the standard disabled result shared by every adapter.

    Always returns ``status=DISABLED_STATUS`` — this is the ONLY result
    shape any adapter produces when the dev/test posture is not declared
    (or no ``config`` is supplied at all). No socket, HTTP client, or DNS
    lookup is touched to produce this value.
    """

    return ProviderFetchResult(provider=provider, status=DISABLED_STATUS, reason=reason)


def authorize_live_fetch(config: "FoundryConfig | None", *, provider: str) -> bool:
    """The fetch-authorization point shared by every provider adapter AND
    by :func:`_fetch_json` itself (clearance-gates M3 CHANGES_REQUESTED
    review, findings B1/B2: every layer that can reach a socket re-checks
    this — there is exactly one place the decision is made, but it is
    re-consulted at every layer rather than trusted from a layer above).

    Validates *provider* is KNOWN first: one with no entry in the static,
    immutable :data:`PROVIDER_GATE_SCOPE` raises
    :class:`~research_foundry.services.clearance.ClearanceConfigError`
    immediately, before any config/posture check and therefore before any
    network attempt could even be contemplated. This is deliberately
    unconditional (checked even when *config* is ``None``) so the failure
    mode for an unknown provider is always "refuse", never "fetch, then
    fail after the value is already in hand with no stamp". Note (round 2,
    finding B4): this check only validates provider IDENTITY against the
    known-providers set — it does not resolve or trust a SCOPE value from
    the map; the actual mandatory scope a stamp blocks comes from
    :data:`_MANDATORY_PROVIDER_FETCH_SCOPE` in :func:`stamp_dev_test_fetch`,
    never from here.

    Returns ``False`` (no audit emission, no exception) when ``config`` is
    ``None`` — the default, and every pre-M3 caller's shape — or when the
    posture resolves ``False``.

    When the posture resolves ``True``, this ALSO emits the
    ``dev_test_posture_activated`` audit event via
    ``audit_service.emit_dev_test_posture_activated_once`` — the SAME
    dedup point ``api.app.create_app()`` uses (CHANGES_REQUESTED finding
    M2: unified so the two call sites can never double-emit for one
    config), which itself only marks a config audited AFTER a confirmed
    successful write (finding M1: ``record_event`` is fail-open, so a
    failed write must not permanently suppress every later retry).

    Propagates :class:`~research_foundry.errors.RFError` unchanged when the
    posture is half-declared (fail-closed; see ``FoundryConfig.
    dev_test_posture_live_fetch_enabled``'s own docstring) — an operator who
    set ``live_fetch_enabled: true`` with a missing required field must see
    that surface loudly, including from this call site.
    """

    if provider not in PROVIDER_GATE_SCOPE:
        raise ClearanceConfigError(
            f"attribution_fetch: unknown provider {provider!r} -- no entry in "
            f"the static PROVIDER_GATE_SCOPE map (known: {sorted(PROVIDER_GATE_SCOPE)}). "
            "Refusing to authorize any live fetch for it; adding a provider "
            "requires a reviewable new adapter module AND a PROVIDER_GATE_SCOPE entry."
        )
    if config is None:
        return False
    if not config.dev_test_posture_live_fetch_enabled():
        return False

    from .. import audit_service

    audit_service.emit_dev_test_posture_activated_once(
        config, source_ref=f"attribution_fetch.{provider}"
    )
    return True


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse EVERY HTTP redirect (clearance-gates M3 CHANGES_REQUESTED
    review, finding M4 — SSRF via provider-controlled redirects).

    ``urllib.request``'s default opener follows 301/302/303/307/308
    redirects with no validation of the target scheme/host/address. A
    compromised or intercepted provider endpoint could use that to redirect
    this process to an internal service or a cloud metadata endpoint
    (``http://169.254.169.254/...``) and have the response read as if it
    came from the provider. Returning ``None`` here (rather than building a
    redirected request) makes ``urllib``'s ``HTTPErrorProcessor`` raise
    ``HTTPError`` for the 3xx status instead of following it — surfaced to
    callers as :class:`~research_foundry.errors.AdapterError` by
    :func:`_fetch_json`'s existing ``URLError`` handling (``HTTPError`` is a
    ``URLError`` subclass).
    """

    def redirect_request(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D102
        return None


def _fetch_json(
    url: str,
    *,
    config: "FoundryConfig | None",
    provider: str,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    """PRIVATE. Authorization-gated, hostile-input-safe GET + JSON decode.

    NOT exported (clearance-gates M3 CHANGES_REQUESTED review, finding B1):
    the original public ``fetch_json(url)`` took no ``config`` at all, so
    ANY importer could call it directly to issue a real GET with the
    dev/test posture OFF (or never even consulted) — a structural bypass of
    the entire opt-in gate. ``config``/``provider`` are now REQUIRED
    (no default) and re-validated via :func:`authorize_live_fetch` on
    every call, so this function cannot reach a socket no matter how it is
    invoked or by what layer.

    Host/scheme allowlist + no-redirect opener (finding M4): *url* must be
    ``https`` and its host must be one of :data:`_ALLOWED_PROVIDER_HOSTS`,
    checked BEFORE any socket is opened; the request is issued through an
    opener built with :class:`_NoRedirectHandler`, which refuses (never
    follows) any 3xx response.

    Every byte read here originates from a third-party server and is
    treated as untrusted: the read is size-capped BEFORE ``json.loads``
    ever sees it (a response that exceeds *max_bytes* is refused outright,
    never truncated and parsed anyway); decoding uses the standard
    library's ``json`` module only (no ``eval``, no ``pickle``, no YAML)
    and explicitly catches ``RecursionError`` (finding M3 — deeply nested
    JSON is cheap in bytes and not stopped by the size cap, but
    ``json.loads`` can still blow the recursion limit on it); and any
    network/decode/shape/depth failure raises
    :class:`~research_foundry.errors.AdapterError` rather than propagating
    a raw stdlib exception type callers would need to know to catch.

    stdlib ``urllib.request`` only — this package adds no new third-party
    HTTP dependency for the dev/test posture.

    NON-ENFORCEMENT NOTE (round 2 adjudication on finding B1, no behaviour
    change): the reachability of this private function is DELIBERATELY not
    this package's clearance boundary. Under posture-OFF,
    :func:`authorize_live_fetch`'s mandatory ``config``/``provider`` gate
    stops this before any network attempt, exactly as documented above.
    Under posture-ON, a caller that reaches around :func:`fetch`/
    :func:`_send_request` and calls this directly gets back a RAW,
    unstamped ``dict`` — no ``clearance`` key, no taint block — which is
    exactly the local acquisition the declared posture already authorizes,
    not a new egress path: that bare dict carries nothing that can survive
    ``services.clearance.mediate_egress``'s fail-closed treatment of an
    absent/empty stamp for a governed kind (see
    ``clearance.py::_blocked_scopes_of`` — absence is refused, never read
    as clean), so it cannot be laundered into a governed record that
    passes egress mediation. The actual enforcement boundary is
    ``mediate_egress`` itself, at every writeback chokepoint (M2/M5) — not
    "can this function be called". This function's mandatory-gate check is
    a missing DEFENSE-IN-DEPTH layer for that specific bypass, not an
    egress hole; hardening it further (making a private helper truly
    unreachable) is not attempted, and is explicitly out of scope per the
    same round-2 adjudication that closed B4 by enforcing at the point of
    use instead of by hiding.
    """

    if not authorize_live_fetch(config, provider=provider):
        raise NotImplementedError(
            f"attribution_fetch: _fetch_json refuses to contact a live provider "
            f"for {provider!r} -- the dev_test_posture live-fetch escape hatch is "
            "not declared on the supplied config. No network call may be issued."
        )

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_PROVIDER_HOSTS:
        raise AdapterError(
            f"attribution_fetch: refusing to contact {url!r} -- scheme must be "
            f"'https' and host must be one of {sorted(_ALLOWED_PROVIDER_HOSTS)} "
            "(finding M4: host/scheme allowlist checked before any socket opens)"
        )

    request = urllib.request.Request(
        url, headers={"User-Agent": "research-foundry-dev-test-posture/1.0"}
    )
    opener = urllib.request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310
            raw = response.read(max_bytes + 1)
    except urllib.error.URLError as exc:
        raise AdapterError(f"attribution_fetch: request to {url!r} failed: {exc}") from exc

    if len(raw) > max_bytes:
        raise AdapterError(
            f"attribution_fetch: response from {url!r} exceeded {max_bytes} bytes; "
            "refusing to parse an oversized third-party response"
        )
    try:
        data = json.loads(raw)
    except RecursionError as exc:
        raise AdapterError(
            f"attribution_fetch: response from {url!r} is too deeply nested to "
            "parse safely"
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise AdapterError(
            f"attribution_fetch: response from {url!r} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise AdapterError(
            f"attribution_fetch: response from {url!r} is not a JSON object "
            f"(got {type(data).__name__})"
        )
    return data


#: The use scope EVERY provider-fetch stamp in this package blocks,
#: UNCONDITIONALLY (clearance-gates M3 CHANGES_REQUESTED round 2, finding
#: B4). A bare module constant — deliberately NEVER read from
#: :data:`PROVIDER_GATE_SCOPE` when resolving a stamp's ``blocked_scopes``.
#:
#: Round 1's fix (``MappingProxyType``) closed *item-assignment*/*deletion*
#: on ``PROVIDER_GATE_SCOPE``, but round 2 found the boundary was still
#: only convention: Python has no real access control, so an in-process
#: caller can mutate the underlying ``_PROVIDER_GATE_SCOPE_DATA`` dict the
#: proxy wraps, or rebind the ``PROVIDER_GATE_SCOPE`` module attribute
#: wholesale (``attribution_fetch.PROVIDER_GATE_SCOPE = {"openalex":
#: "acquisition"}``) — either one previously produced a stamp that blocked
#: ``acquisition`` and OMITTED ``redistribution``, which then PASSED
#: ``mediate_egress(target_scope="redistribution")``: a genuine leak, and
#: "acquisition" is a valid ``BLOCKING_SCOPES`` member so ``stamp_taint``'s
#: own validation never caught it. "Make it unreachable" is unwinnable by
#: construction (there is no such thing as a private name in Python), so
#: this closes the hole by making the invariant hold REGARDLESS of
#: reachability: nothing in :func:`stamp_dev_test_fetch` below ever reads
#: ``PROVIDER_GATE_SCOPE``'s value to decide what to block, so there is
#: nothing for a mutation or a rebind to corrupt.
#:
#: ``PROVIDER_GATE_SCOPE`` itself is KEPT — as the known-providers set
#: :func:`authorize_live_fetch` validates against, and as public
#: documentation/provenance of each provider's nominal scope — but it is no
#: longer a load-bearing input to any stamp.
_MANDATORY_PROVIDER_FETCH_SCOPE: str = "redistribution"


def _resolve_provider_fetch_scopes(provider: str) -> list[str]:
    """Resolve the ``blocked_scopes`` list for a provider-fetch stamp.

    Isolated from :func:`stamp_dev_test_fetch` specifically so the
    mandatory-scope guard there can be tested against a genuinely
    DIVERGENT result (by monkeypatching this function), not merely against
    a value that is trivially guaranteed correct by inspection. Today this
    always returns ``[_MANDATORY_PROVIDER_FETCH_SCOPE]`` — there is no
    additional per-provider scope to union in (every current provider's own
    ``PROVIDER_GATE_SCOPE`` entry already equals the mandatory floor) — but
    the split keeps that a fact about today's data, not an assumption baked
    into the guard.
    """

    return [_MANDATORY_PROVIDER_FETCH_SCOPE]


def stamp_dev_test_fetch(*, provider: str) -> dict[str, Any]:
    """Build the durable clearance taint for a record fetched under the
    dev/test live-fetch posture.

    ``"redistribution"`` is ALWAYS present in the resulting stamp — see
    :data:`_MANDATORY_PROVIDER_FETCH_SCOPE`'s docstring for why this is
    unconditional and independent of ``PROVIDER_GATE_SCOPE``'s live state.

    The runtime assertion below re-verifies the mandatory scope actually
    survived into :func:`_resolve_provider_fetch_scopes`'s result
    immediately before calling
    :func:`~research_foundry.services.clearance.stamp_taint` — this is the
    ENFORCEMENT point, and it holds no matter what happened to any dict in
    this module, because it checks the ACTUAL value about to be stamped,
    not a hardcoded literal repeated twice. A future refactor of that
    resolver that accidentally drops the mandatory scope is caught here,
    at the moment of stamping, rather than shipping an under-restrictive
    taint.
    """

    scopes = _resolve_provider_fetch_scopes(provider)
    if _MANDATORY_PROVIDER_FETCH_SCOPE not in scopes:
        raise ClearanceConfigError(
            f"attribution_fetch: stamp_dev_test_fetch resolved blocked_scopes "
            f"{scopes!r} for provider {provider!r} WITHOUT the mandatory "
            f"{_MANDATORY_PROVIDER_FETCH_SCOPE!r} scope -- refusing to stamp "
            "an under-restrictive taint. This is a programming-error guard: "
            "the mandatory scope is a bare module constant and is never "
            "omittable by mutating or rebinding PROVIDER_GATE_SCOPE."
        )

    return stamp_taint(
        blocked_scopes=scopes,
        stamped_by=f"attribution_fetch.{provider}",
        posture_at_stamp="dev_test",
        gate_refs=_PROVIDER_GATE_REFS.get(provider, ()),
    )


#: Human-only rights-clearance literals (``docs/dev/architecture/
#: adr-rights-entity-model.md`` Invariant 1). This writer never constructs one;
#: the constant exists so :func:`_merged_blocked_scopes`' refusal can name the
#: family it is refusing rather than failing with a bare vocabulary error, and
#: so the prohibition is asserted at the point of use rather than only in prose.
#: Note these are NOT members of ``clearance.BLOCKING_SCOPES`` — the two
#: vocabularies are deliberately disjoint, and the subset check below is what
#: makes that disjointness load-bearing instead of incidental.
_HUMAN_ONLY_RIGHTS_VALUES: frozenset[str] = frozenset({"counsel_approved", "attested"})

#: Schema governing the ``clearance`` block this writer emits.
_CLEARANCE_TAINT_SCHEMA = "clearance_taint"


def _clearance_schema_registry(paths: FoundryPaths | None) -> SchemaRegistry | None:
    """Locate the schema registry holding ``clearance_taint.schema.yaml``.

    Mirrors ``services/source_cards.py::_schema_registry`` (workspace schemas
    first, distribution schemas as fallback) but deliberately does NOT call
    ``FoundryPaths.discover()`` when *paths* is ``None``: discovery resolves
    relative to the current working directory, which in a git worktree points
    at a tree that may carry no ``schemas/`` at all. Returning ``None`` here
    hands :func:`stamp_source_card` a fail-CLOSED refusal instead of a
    silently-unvalidated write.
    """

    if paths is not None and paths.schemas.exists():
        return SchemaRegistry(schemas_dir=paths.schemas)
    dist = distribution_root() / "schemas"
    return SchemaRegistry(schemas_dir=dist) if dist.exists() else None


def _read_scopes(block: Mapping[str, Any], *, source: str) -> list[str]:
    """Read a stamp's ``blocked_scopes``, refusing an unreadable shape.

    *source* names where the block came from (the card path, or
    ``result.clearance``) so a refusal says which side was malformed.

    Refusing (rather than treating an unreadable list as absent) is what makes
    the merge monotone in practice: if a malformed existing value were read as
    the empty set, a scope a human had recorded could be dropped by a
    subsequent stamp. This raises BEFORE any write, so the on-disk card is
    left byte-identical.
    """

    raw = block.get(BLOCKED_SCOPES_KEY, [])
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise SchemaError(
            f"stamp_source_card: {source} carries a {TAINT_KEY!r} block whose "
            f"{BLOCKED_SCOPES_KEY!r} is {type(raw).__name__}, not a list -- refusing "
            "to merge against a shape that cannot be read back as a scope set. "
            "Repair the card by hand; a writer that guessed here could silently "
            "narrow an existing stamp."
        )
    scopes: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            raise SchemaError(
                f"stamp_source_card: {source}'s {BLOCKED_SCOPES_KEY!r} "
                f"contains a non-string entry {entry!r} -- refusing before any write."
            )
        scopes.append(entry)
    return scopes


def _merged_blocked_scopes(
    *, existing_scopes: list[str], incoming_scopes: list[str], card_path: Path
) -> list[str]:
    """Set-union the two scope lists — monotone, widen-only, never empty.

    Union is the ONLY merge operation used: it cannot remove a scope the card
    already carried, and it cannot introduce a scope that neither the existing
    stamp nor ``result.clearance`` already asserted (so this writer can never
    widen permitted use, nor invent a restriction out of nothing).

    Both invariants that ``governance.py`` rule 9
    (``no_agent_cleared_clearance_taint``) protects are re-checked here at the
    point of use, because rule 9 evaluates ``proposed_field_writes`` and this
    writer does not route through that surface: the result must be non-empty
    (an empty set is the release assertion) and must stay inside
    ``clearance.BLOCKING_SCOPES`` — which structurally excludes the
    ``CLEARED_*``/``counsel_approved``/``attested`` family, so no value from
    that family can reach disk through this path.
    """

    merged = sorted(set(existing_scopes) | set(incoming_scopes))
    forged = sorted(s for s in merged if s in _HUMAN_ONLY_RIGHTS_VALUES or s.startswith("CLEARED_"))
    if forged:
        raise ClearanceConfigError(
            f"stamp_source_card: refusing to write human-only rights-clearance "
            f"value(s) {forged} into {TAINT_KEY}.{BLOCKED_SCOPES_KEY} of {card_path} "
            "-- those literals are reserved for humans (ADR Invariant 1) and are "
            "not clearance scopes."
        )
    unknown = sorted(s for s in merged if s not in BLOCKING_SCOPES)
    if unknown:
        raise ClearanceConfigError(
            f"stamp_source_card: merged blocked_scopes for {card_path} contain "
            f"unknown scope(s) {unknown}; expected members of "
            f"{sorted(BLOCKING_SCOPES)}."
        )
    if not merged:
        raise ClearanceConfigError(
            f"stamp_source_card: refusing to write an EMPTY "
            f"{TAINT_KEY}.{BLOCKED_SCOPES_KEY} to {card_path} -- the empty set is a "
            "release assertion, which only a human editing the record may make."
        )
    return merged


def _merged_clearance_block(
    *,
    incoming: Mapping[str, Any],
    existing: Mapping[str, Any] | None,
    card_path: Path,
) -> dict[str, Any]:
    """Compose the block to write from *incoming* (authoritative) + *existing*.

    ``incoming`` is ``result.clearance`` verbatim — built by
    :func:`~research_foundry.services.clearance.stamp_taint` at fetch time.
    Nothing here re-derives a taint, consults gate state, or hand-assembles a
    field ``stamp_taint`` owns; this function only chooses, per field, between
    a value already present in one of the two blocks.

    Per-field merge, all widen-only:

    ``blocked_scopes``   union (see :func:`_merged_blocked_scopes`).
    ``posture_at_stamp`` ``dev_test`` wins over ``none``. Overwriting a
                         dev/test-acquired card with ``none`` is exactly the
                         retroactive release rule 9 refuses.
    ``gate_refs``        union — advisory provenance; a superset can never
                         widen permitted use (``mediate_egress`` reads only
                         ``blocked_scopes``).
    ``note``            incoming when it carries one, else the existing
                         operator annotation is preserved rather than dropped.
    ``stamped_at`` /
    ``stamped_by``       incoming; provenance for THIS acquisition, and
                         carrying no authority per the schema.
    """

    existing = existing or {}
    incoming_scopes = _read_scopes(incoming, source="result.clearance")
    block: dict[str, Any] = {
        "schema_version": incoming.get("schema_version", "1.0"),
        BLOCKED_SCOPES_KEY: _merged_blocked_scopes(
            existing_scopes=_read_scopes(existing, source=str(card_path)),
            incoming_scopes=incoming_scopes,
            card_path=card_path,
        ),
        "stamped_at": incoming.get("stamped_at"),
        "stamped_by": incoming.get("stamped_by"),
        "posture_at_stamp": (
            "dev_test"
            if "dev_test" in {existing.get("posture_at_stamp"), incoming.get("posture_at_stamp")}
            else incoming.get("posture_at_stamp")
        ),
        "gate_refs": sorted(
            {str(g) for g in _iter_refs(existing.get("gate_refs"))}
            | {str(g) for g in _iter_refs(incoming.get("gate_refs"))}
        ),
    }
    note = incoming.get("note", existing.get("note"))
    if note is not None:
        block["note"] = note
    return block


def _iter_refs(value: Any) -> tuple[Any, ...]:
    """Coerce a ``gate_refs`` value to a tuple; a non-sequence contributes none."""

    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        return ()
    return tuple(value)


def stamp_source_card(
    card_path: Path,
    result: ClearedProviderFetchResult,
    *,
    paths: FoundryPaths | None = None,
) -> None:
    """Persist *result*'s durable clearance taint onto an existing source card.

    The production caller for the M3 stamp: a real dev/test fetch produced a
    :class:`ClearedProviderFetchResult` whose ``clearance`` block records the
    posture in force at acquisition time, and that block has to ride on the
    card from here on — ``clearance.mediate_egress`` reads the stamp off the
    record and treats its ABSENCE as blocked for any governed kind, so an
    unstamped card is refused outward rather than leaking.

    Contract:

    * The taint is taken from ``result.clearance`` verbatim. This function
      never calls ``stamp_taint``, never reads gate state, and never
      hand-assembles a taint dict — a second derivation point could disagree
      with the fetch-time one about what was true at acquisition.
    * Merging an existing stamp is monotone and widen-only on every axis: a
      scope already on the card survives, the empty set is refused, and
      ``posture_at_stamp: dev_test`` is never downgraded to ``none``.
    * No ``CLEARED_*``/``counsel_approved``/``attested`` value is ever
      constructed or written — those are human-only (ADR Invariant 1) and are
      not clearance vocabulary. Re-checked at the point of use.
    * The composed block is schema-validated (``clearance_taint``) BEFORE any
      byte is written, and validation is fail-CLOSED: an unavailable schema
      raises rather than skipping (unlike ``source_cards._validate``, whose
      skip-if-absent behaviour would here mean writing an unvalidated
      governance stamp).
    * The write is atomic — temp file in the card's own directory then
      ``os.replace`` — so a failure at any point leaves the card
      byte-identical, never half-rewritten frontmatter.

    Only the ``clearance`` key is touched; every other frontmatter field and
    the Markdown body are round-tripped unchanged.

    Raises:
        TypeError: *result* is not a :class:`ClearedProviderFetchResult`.
        FileNotFoundError: *card_path* does not exist.
        SchemaError: the card has no frontmatter, its existing ``clearance``
            block has an unreadable shape, or the composed block fails
            ``clearance_taint`` validation (or that schema is unavailable).
        ClearanceConfigError: the merge would produce a non-monotone,
            empty, or out-of-vocabulary stamp.
    """

    if not isinstance(result, ClearedProviderFetchResult):
        # A dict/ProviderFetchResult would let a caller supply a hand-assembled
        # taint; the whole point of this signature is that the only stamp it can
        # write is one stamp_taint already produced at fetch time.
        raise TypeError(
            "stamp_source_card: result must be a ClearedProviderFetchResult "
            f"(got {type(result).__name__}) -- a hand-assembled clearance block "
            "is not an acceptable input."
        )

    card_path = Path(card_path)
    meta, body = load_md(card_path)
    if not meta:
        raise SchemaError(
            f"stamp_source_card: {card_path} has no YAML frontmatter to stamp -- "
            "refusing to synthesize a governed record around a clearance block."
        )

    existing = meta.get(TAINT_KEY)
    if existing is not None and not isinstance(existing, Mapping):
        raise SchemaError(
            f"stamp_source_card: {card_path}'s {TAINT_KEY!r} key is "
            f"{type(existing).__name__}, not a mapping -- refusing before any write."
        )

    block = _merged_clearance_block(
        incoming=result.clearance, existing=existing, card_path=card_path
    )

    registry = _clearance_schema_registry(paths)
    if registry is None or not registry.has(_CLEARANCE_TAINT_SCHEMA):
        raise SchemaError(
            f"stamp_source_card: {_CLEARANCE_TAINT_SCHEMA}.schema.yaml is unavailable, "
            "so the composed clearance block cannot be validated. Refusing to write an "
            "unvalidated governance stamp (fail-closed: an absent or malformed stamp "
            "is refused outward, so a bad one is worse than no write)."
        )
    validation = registry.validate(block, _CLEARANCE_TAINT_SCHEMA)
    if not validation.ok:
        raise SchemaError(
            f"stamp_source_card: {_CLEARANCE_TAINT_SCHEMA} validation failed for "
            f"{card_path}: " + "; ".join(validation.errors)
        )

    meta[TAINT_KEY] = block
    tmp_path = card_path.parent / f".{card_path.name}.clearance-{uuid.uuid4().hex}.tmp"
    try:
        dump_md(meta, body, tmp_path)
        os.replace(tmp_path, card_path)
    finally:
        tmp_path.unlink(missing_ok=True)


__all__ = [
    "DISABLED_STATUS",
    "FETCHED_STATUS",
    "MAX_RESPONSE_BYTES",
    "PROVIDER_GATE_SCOPE",
    "REQUEST_TIMEOUT_SECONDS",
    "ClearedProviderFetchResult",
    "ProviderFetchResult",
    "authorize_live_fetch",
    "disabled_result",
    "stamp_dev_test_fetch",
    "stamp_source_card",
]
# NOTE (finding B1): `_fetch_json` is deliberately NOT exported here. It is
# a private, authorization-gated network primitive -- see its own
# docstring. Do not add it to __all__ or re-export it as a public name.
