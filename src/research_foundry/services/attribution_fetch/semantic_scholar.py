"""Semantic Scholar provider adapter — INERT scaffolding. See package
docstring (``services/attribution_fetch/__init__.py``) for the DEF-1/DEF-6
gates that keep every adapter in this package unreachable regardless of
configuration.

This provider is one of the two DEF-6 names explicitly: "Live ToS
re-verification for Semantic Scholar / NCBI" is open — the PRD's licensing
table is stated from general domain knowledge of Semantic Scholar's public
API policies, not re-verified against its live current ToS, and that is
**not legal advice**. This module asserts no licensing determination for
Semantic Scholar.

No HTTP client of any kind (``httpx``, ``requests``, ``urllib``, raw
sockets) is imported, instantiated, or called anywhere in this module —
not even in an unreachable branch. :func:`fetch` always returns a
:class:`~research_foundry.services.attribution_fetch.ProviderFetchResult`
built purely in-process; :func:`_send_request` — the single place a live
call would eventually go — raises ``NotImplementedError`` before doing
anything else, and is never invoked by :func:`fetch`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

from . import ProviderFetchResult, disabled_result

PROVIDER_NAME = "semantic_scholar"

_REASON = (
    "attribution_fetch/semantic_scholar is inert scaffolding: DEF-1 "
    "(per-provider license terms verified for bundle redistribution) AND "
    "DEF-6 (live ToS re-verification for Semantic Scholar / NCBI) are both "
    "open. No network call is issued regardless of configuration."
)


@dataclass(frozen=True)
class SemanticScholarRequest:
    """Typed request-builder shape only — never sent anywhere.

    Models what a lookup request would need once/if DEF-1 and DEF-6 close:
    a paper identifier. Structurally present so a future implementation
    has a typed parameter to build against; carries no behavior of its
    own.
    """

    paper_id: str


@dataclass(frozen=True)
class SemanticScholarRawResponse:
    """Typed response-parser shape only — never constructed anywhere.

    Documents the subset of Semantic Scholar's paper-object JSON a future
    implementation would read (``paperId``, ``citationCount``). Not used
    as the return type of :func:`fetch`, not instantiated by this module,
    and not reachable from any current code path.
    """

    paper_id: str
    citation_count: int | None


def _send_request(request: SemanticScholarRequest) -> NoReturn:
    """The one place a live Semantic Scholar call would eventually be
    issued.

    Raises immediately, before any socket, DNS lookup, or HTTP client is
    touched. Never called by :func:`fetch`; exists only to make the
    unreachable network boundary explicit and independently testable.
    """

    raise NotImplementedError(
        "attribution_fetch.semantic_scholar._send_request is unreachable "
        "scaffolding — DEF-1/DEF-6 are open (see package docstring). No "
        "network call may be issued."
    )


def fetch(
    request: SemanticScholarRequest, *, config: object | None = None
) -> ProviderFetchResult:
    """Always returns a disabled result. Never opens a socket.

    ``config`` is accepted only for future call-site symmetry with a real
    implementation; it is never consulted here because reachability is
    unconditionally off in this package, independent of any flag's value.
    """

    del request, config  # unused — reachability is unconditional, not flag-gated
    return disabled_result(PROVIDER_NAME, _REASON)


__all__ = ["PROVIDER_NAME", "SemanticScholarRequest", "SemanticScholarRawResponse", "fetch"]
