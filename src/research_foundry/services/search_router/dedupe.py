"""URL canonicalization and hit deduplication for the Search Router.

:func:`canonicalize_url` normalises a URL to a stable key, stripping
tracking parameters, fragments, default ports, and ``www.`` prefix.

:func:`dedupe_hits` collapses a list of :class:`SearchHit` objects to one
entry per canonical URL, preserving the hit with the best rank/score and
maintaining stable ordering.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from research_foundry.services.search_router.providers.base import SearchHit

# Query-string parameters that carry no semantic content and are stripped.
_TRACKING_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "fbclid",
        "gclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
    }
)

# Default ports per scheme that are redundant and should be stripped.
_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


def canonicalize_url(url: str) -> str:
    """Return a canonical form of *url* suitable for deduplication keys.

    Normalisation steps (applied in order):

    1. Lowercase scheme and host.
    2. Strip default ports (80 for http, 443 for https).
    3. Remove ``www.`` prefix from the host.
    4. Remove fragment (``#...``).
    5. Remove tracking query parameters (``utm_*``, ``ref``, ``fbclid``, etc.).
    6. Strip trailing slash from the path (unless the path is just ``/``).
    """
    if not url:
        return url
    try:
        parsed = urlparse(url)
    except ValueError:
        return url

    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()

    # Strip default ports
    port = parsed.port
    if port and _DEFAULT_PORTS.get(scheme) == port:
        port = None

    # Drop leading 'www.'
    if host.startswith("www."):
        host = host[4:]

    netloc = host
    if port:
        netloc = f"{host}:{port}"

    # Sanitise path — strip trailing slash unless root
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Filter tracking query params; sort remaining pairs by key (then value)
    # so query-order permutations canonicalize identically.
    qs_pairs = sorted(
        (
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k not in _TRACKING_PARAMS and not k.startswith("utm_")
        ),
        key=lambda kv: (kv[0], kv[1]),
    )
    query = urlencode(qs_pairs)

    # No fragment
    canonical = urlunparse((scheme, netloc, path, parsed.params, query, ""))
    return canonical


def _hit_key(hit: SearchHit) -> str:
    return canonicalize_url(hit.url)


def _better(candidate: SearchHit, current: SearchHit) -> bool:
    """True when *candidate* should replace *current* as the representative hit."""
    # Lower rank is better (rank=1 means top result); 0 means unranked.
    # Higher score is better; None means no score.
    c_rank = candidate.rank if candidate.rank > 0 else 999_999
    cur_rank = current.rank if current.rank > 0 else 999_999
    c_score = candidate.score if candidate.score is not None else -1.0
    cur_score = current.score if current.score is not None else -1.0

    if c_score != cur_score:
        return c_score > cur_score
    return c_rank < cur_rank


def dedupe_hits(hits: list[SearchHit]) -> list[SearchHit]:
    """Deduplicate *hits* by canonical URL.

    For each group of hits sharing a canonical URL, keeps the entry with the
    best score (higher is better) or lowest rank (lower is better), breaking
    ties in favour of the first occurrence (stable).

    The returned list preserves the order of first occurrence of each
    canonical URL.
    """
    seen: dict[str, SearchHit] = {}
    order: list[str] = []

    for hit in hits:
        key = _hit_key(hit)
        if key not in seen:
            seen[key] = hit
            order.append(key)
        elif _better(hit, seen[key]):
            seen[key] = hit

    return [seen[k] for k in order]


__all__ = ["canonicalize_url", "dedupe_hits"]
