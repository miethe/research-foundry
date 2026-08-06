"""Semantic Scholar provider adapter — inert by default; gated real fetch for
dev/test. See package docstring (``services/attribution_fetch/__init__.py``)
for the DEF-1/DEF-6 gates that keep this adapter's disabled path the default,
and for the clearance-gates M3 dev/test live-fetch posture that gates the
one real-fetch path this module now has.

This provider is one of the two DEF-6 names explicitly: "Live ToS
re-verification for Semantic Scholar / NCBI". That verification ran
2026-08-06 (``docs/project_plans/exploration/source-metadata-propagation/
spikes/def-6-tos-verification-2026-08-06.md``) and the gate is **still
open** — verifying the terms is not closing the gate. What the pass found
makes this adapter's inertness more load-bearing, not less: the S2 API
License Agreement defers per-dataset ("such as CC BY-NC or ODC-BY"), so no
blanket redistribution license for S2 data exists to rely on, and any
future ``license_basis`` this adapter stamps must come from the payload's
own accompanying license rather than a hardcoded default. That record is
**not legal advice**. This module asserts no licensing determination for
Semantic Scholar, even on the gated dev/test path below.

On the default (disabled) path — ``config=None``, or ``config`` supplied but
the posture unset/``False`` — no HTTP client of any kind is imported,
instantiated, or called anywhere in this module's execution, exactly as
before M3: :func:`fetch` returns a
:class:`~research_foundry.services.attribution_fetch.ProviderFetchResult`
built purely in-process, and :func:`_send_request` raises
``NotImplementedError`` before doing anything else.

On the gated dev/test path ONLY — a ``config`` whose
``dev_test_posture_live_fetch_enabled()`` resolves ``True`` —
:func:`_send_request` issues a real stdlib ``urllib.request`` GET and
:func:`fetch` returns a
:class:`~research_foundry.services.attribution_fetch.ClearedProviderFetchResult`
stamped with a durable clearance taint. That stamp is produced
unconditionally and is never re-derived later.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from . import (
    ClearedProviderFetchResult,
    ProviderFetchResult,
    _fetch_json,
    authorize_live_fetch,
    disabled_result,
    stamp_dev_test_fetch,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ...config import FoundryConfig

PROVIDER_NAME = "semantic_scholar"

_REASON = (
    "attribution_fetch/semantic_scholar is inert scaffolding: DEF-1 "
    "(per-provider license terms verified for bundle redistribution) AND "
    "DEF-6 (live ToS re-verification for Semantic Scholar / NCBI) are both "
    "open. No network call is issued regardless of configuration."
)


@dataclass(frozen=True)
class SemanticScholarRequest:
    """Typed request-builder shape.

    Models what a lookup request needs: a paper identifier. Consumed by
    :func:`_send_request` ONLY on the gated dev/test live-fetch path; on
    the default disabled path it is accepted and ignored, exactly as
    before M3.
    """

    paper_id: str


@dataclass(frozen=True)
class SemanticScholarRawResponse:
    """Typed response-parser shape only — never constructed anywhere.

    Documents the subset of Semantic Scholar's paper-object JSON a caller
    could read (``paperId``, ``citationCount``) — the SAME field names
    :func:`_parse_raw_response` extracts, defensively, into a plain
    ``dict`` on the gated dev/test path. This dataclass itself is never
    instantiated by this module (see
    ``tests/test_attribution_fetch_seam.py::
    test_raw_response_shape_is_never_instantiated_by_this_module``) — it
    remains documentation of the shape, not a return type.
    """

    paper_id: str
    citation_count: int | None


def _parse_raw_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Defensively project a hostile third-party JSON object into the
    :class:`SemanticScholarRawResponse` field-name SHAPE, as a plain
    ``dict``.

    Every field access is ``.get()`` with an explicit type check: a missing
    key, wrong-typed value, or unexpected extra key never raises — it
    degrades to ``None`` rather than propagating a ``KeyError``/``TypeError``
    from untrusted input.
    """

    paper_id = raw.get("paperId")
    if not isinstance(paper_id, str):
        paper_id = None
    citation_count = raw.get("citationCount")
    if not isinstance(citation_count, int) or isinstance(citation_count, bool):
        citation_count = None
    return {"paper_id": paper_id, "citation_count": citation_count}


def _send_request(
    request: SemanticScholarRequest, *, config: "FoundryConfig | None" = None
) -> "ClearedProviderFetchResult":
    """The one place a live Semantic Scholar call is issued — ONLY when
    the dev/test live-fetch posture (clearance-gates M3) is declared on
    *config*. Returns a FULLY STAMPED
    :class:`~research_foundry.services.attribution_fetch.ClearedProviderFetchResult`
    — NEVER a bare/unstamped dict (clearance-gates M3 CHANGES_REQUESTED
    review, finding B2: previously this function returned a raw dict with
    no clearance block at all, so a caller invoking it directly — bypassing
    :func:`fetch` — got back a real third-party value with zero taint on
    it). Authorization, the network fetch, value-shaping, AND stamping now
    happen in one atomic composition, so there is no way to obtain a real
    fetched value from this module without also getting its stamp.

    Gated HERE via :func:`authorize_live_fetch`, not only in :func:`fetch`,
    so this function stays correct even when called directly (as
    ``tests/test_attribution_fetch_seam.py::
    test_send_request_raises_before_any_socket`` does, with no ``config``
    at all): that call resolves ``config=None`` and raises
    ``NotImplementedError`` with the SAME message this function always
    raised before M3 — preserving pre-M3 behaviour byte for byte.
    :func:`~research_foundry.services.attribution_fetch._fetch_json`
    re-checks authorization AGAIN internally, so even a caller holding a
    reference to that lower-level function directly cannot bypass this.

    Untrusted-input handling: the response body is treated as hostile
    third-party input — see ``_fetch_json``'s docstring for the size cap,
    host/scheme allowlist, no-redirect opener, and JSON-only decode this
    delegates to.
    """

    if not authorize_live_fetch(config, provider=PROVIDER_NAME):
        raise NotImplementedError(
            "attribution_fetch.semantic_scholar._send_request is unreachable "
            "scaffolding — DEF-1/DEF-6 are open (see package docstring), and "
            "the dev_test_posture live-fetch escape hatch is not declared. No "
            "network call may be issued."
        )
    quoted = urllib.parse.quote(request.paper_id, safe="")
    url = f"https://api.semanticscholar.org/graph/v1/paper/{quoted}?fields=paperId,citationCount"
    raw = _fetch_json(url, config=config, provider=PROVIDER_NAME)
    value = _parse_raw_response(raw)
    clearance = stamp_dev_test_fetch(provider=PROVIDER_NAME)
    return ClearedProviderFetchResult(
        provider=PROVIDER_NAME, status="fetched", value=value, clearance=clearance
    )


def fetch(
    request: SemanticScholarRequest, *, config: "FoundryConfig | None" = None
) -> ProviderFetchResult | ClearedProviderFetchResult:
    """Returns a disabled result by default; a REAL, fully-stamped fetch
    only when the dev/test live-fetch posture (clearance-gates M3) is
    declared on *config*.

    ``config=None`` (the default, and every pre-M3 caller) is BYTE-FOR-BYTE
    the pre-M3 behaviour: no socket, HTTP client, or DNS lookup is ever
    touched, and the return value is unchanged. A ``config`` whose posture
    resolves ``False`` behaves identically. A thin delegator to
    :func:`_send_request`, which now owns the full authorize→fetch→parse→
    stamp composition (finding B2) — this function's only remaining job is
    choosing between the disabled result and that composed result.
    """

    if authorize_live_fetch(config, provider=PROVIDER_NAME):
        return _send_request(request, config=config)
    del request, config  # unused on the disabled path
    return disabled_result(PROVIDER_NAME, _REASON)


__all__ = ["PROVIDER_NAME", "SemanticScholarRequest", "SemanticScholarRawResponse", "fetch"]
