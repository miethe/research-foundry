"""Crossref provider adapter — INERT scaffolding. See package docstring
(``services/attribution_fetch/__init__.py``) for the DEF-1/DEF-6 gates that
keep every adapter in this package unreachable regardless of configuration.

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

PROVIDER_NAME = "crossref"

_REASON = (
    "attribution_fetch/crossref is inert scaffolding: DEF-1 (per-provider "
    "license terms verified for bundle redistribution) is open. No network "
    "call is issued regardless of configuration."
)


@dataclass(frozen=True)
class CrossrefRequest:
    """Typed request-builder shape only — never sent anywhere.

    Models what a lookup request would need once/if DEF-1 closes: a DOI.
    Structurally present so a future implementation has a typed parameter
    to build against; carries no behavior of its own.
    """

    doi: str


@dataclass(frozen=True)
class CrossrefRawResponse:
    """Typed response-parser shape only — never constructed anywhere.

    Documents the subset of Crossref's work-object JSON a future
    implementation would read (``is-referenced-by-count``, ``DOI``). Not
    used as the return type of :func:`fetch`, not instantiated by this
    module, and not reachable from any current code path.
    """

    doi: str
    is_referenced_by_count: int | None


def _send_request(request: CrossrefRequest) -> NoReturn:
    """The one place a live Crossref call would eventually be issued.

    Raises immediately, before any socket, DNS lookup, or HTTP client is
    touched. Never called by :func:`fetch`; exists only to make the
    unreachable network boundary explicit and independently testable.
    """

    raise NotImplementedError(
        "attribution_fetch.crossref._send_request is unreachable scaffolding "
        "— DEF-1/DEF-6 are open (see package docstring). No network call "
        "may be issued."
    )


def fetch(request: CrossrefRequest, *, config: object | None = None) -> ProviderFetchResult:
    """Always returns a disabled result. Never opens a socket.

    ``config`` is accepted only for future call-site symmetry with a real
    implementation; it is never consulted here because reachability is
    unconditionally off in this package, independent of any flag's value.
    """

    del request, config  # unused — reachability is unconditional, not flag-gated
    return disabled_result(PROVIDER_NAME, _REASON)


__all__ = ["PROVIDER_NAME", "CrossrefRequest", "CrossrefRawResponse", "fetch"]
