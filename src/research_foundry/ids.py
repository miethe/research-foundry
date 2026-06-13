"""Identifier, slug, and clock helpers.

Centralizes ID minting so every artifact uses the same conventions from the
spec (e.g. ``raw_YYYYMMDD_HHMM_slug``, ``intent_research_YYYYMMDD_slug``,
``src_YYYYMMDD_slug_hash``).

The clock is injectable (``set_clock``) so tests are deterministic without
patching ``datetime`` globally.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime

# --- Clock -----------------------------------------------------------------


def _default_clock() -> datetime:
    return datetime.now(UTC).astimezone()


_clock: Callable[[], datetime] = _default_clock


def set_clock(fn: Callable[[], datetime]) -> None:
    """Override the wall clock (tests). ``fn`` must return an aware datetime."""

    global _clock
    _clock = fn


def now() -> datetime:
    """Current local time (aware)."""

    return _clock()


def now_iso() -> str:
    """ISO-8601 timestamp, seconds precision (e.g. ``2026-06-13T09:41:00-04:00``)."""

    return now().replace(microsecond=0).isoformat()


def today_compact() -> str:
    """``YYYYMMDD`` for the current day."""

    return now().strftime("%Y%m%d")


def stamp_compact() -> str:
    """``YYYYMMDD_HHMM`` for the current minute."""

    return now().strftime("%Y%m%d_%H%M")


# --- Slugs & hashes --------------------------------------------------------

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, max_words: int = 6, max_len: int = 48) -> str:
    """Lowercase, hyphen-free, underscore-joined slug suitable for filenames/ids.

    Keeps up to ``max_words`` significant words and truncates to ``max_len``.
    Returns ``"untitled"`` for empty input.
    """

    cleaned = _SLUG_STRIP.sub(" ", (text or "").lower()).strip()
    words = [w for w in cleaned.split() if w]
    if not words:
        return "untitled"
    slug = "_".join(words[:max_words])
    return slug[:max_len].rstrip("_") or "untitled"


def short_hash(*parts: str, length: int = 8) -> str:
    """Stable short hex digest of the joined parts (for content-addressed ids)."""

    h = hashlib.sha256(" ".join(parts).encode("utf-8")).hexdigest()
    return h[:length]


# --- ID minting ------------------------------------------------------------


def make_id(prefix: str, slug: str, *, date: bool = True, suffix: str | None = None) -> str:
    """Compose an id like ``<prefix>_<YYYYMMDD>_<slug>[_<suffix>]``."""

    parts = [prefix]
    if date:
        parts.append(today_compact())
    parts.append(slug)
    if suffix:
        parts.append(suffix)
    return "_".join(p for p in parts if p)


def disambiguate_id(
    base_id: str,
    *,
    seed: str,
    exists: Callable[[str], bool],
) -> str:
    """Return ``base_id`` unless ``exists(base_id)``, else a collision-free variant.

    On collision (distinct ideas sharing a 6-word slug mint the same id), append a
    short 4-char hash of ``seed`` — and, only if that also collides, an incrementing
    numeric suffix — so the new artifact does not silently overwrite an existing one.
    Returns ``base_id`` unchanged when there is no collision.
    """

    if not exists(base_id):
        return base_id
    candidate = f"{base_id}_{short_hash(seed, length=4)}"
    if not exists(candidate):
        return candidate
    n = 2
    while exists(f"{candidate}_{n}"):
        n += 1
    return f"{candidate}_{n}"


def raw_idea_id(title: str) -> str:
    return f"raw_{stamp_compact()}_{slugify(title)}"


def intent_id(title: str) -> str:
    return f"intent_research_{today_compact()}_{slugify(title)}"


def ibom_id(title: str) -> str:
    return f"ibom_research_{today_compact()}_{slugify(title)}"


def tree_node_id(title: str) -> str:
    return f"tree_rf_{today_compact()}_{slugify(title)}"


def run_id(title: str) -> str:
    return f"rf_run_{today_compact()}_{slugify(title)}"


def brief_id(title: str) -> str:
    return f"brief_{today_compact()}_{slugify(title)}"


def swarm_id(title: str) -> str:
    return f"swarm_{today_compact()}_{slugify(title)}"


def routing_id(title: str) -> str:
    return f"route_{today_compact()}_{slugify(title)}"


def source_card_id(title: str, locator: str) -> str:
    return f"src_{today_compact()}_{slugify(title)}_{short_hash(title, locator)}"


def bundle_id(title: str) -> str:
    return f"bundle_{today_compact()}_{slugify(title)}"


def report_id(title: str) -> str:
    return f"report_{today_compact()}_{slugify(title)}"


def ccdash_event_id(title: str) -> str:
    return f"exec_{today_compact()}_{slugify(title)}"


def meatywiki_writeback_id(title: str) -> str:
    return f"mwb_{today_compact()}_{slugify(title)}"


def skillbom_candidate_id(title: str) -> str:
    return f"skillcand_research_swarm_{today_compact()}_{slugify(title)}"


__all__ = [
    "set_clock",
    "now",
    "now_iso",
    "today_compact",
    "stamp_compact",
    "slugify",
    "short_hash",
    "make_id",
    "disambiguate_id",
    "raw_idea_id",
    "intent_id",
    "ibom_id",
    "tree_node_id",
    "run_id",
    "brief_id",
    "swarm_id",
    "routing_id",
    "source_card_id",
    "bundle_id",
    "report_id",
    "ccdash_event_id",
    "meatywiki_writeback_id",
    "skillbom_candidate_id",
]
