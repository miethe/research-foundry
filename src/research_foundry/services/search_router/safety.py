"""Prompt-injection risk scanning for extracted content (spec §15.1).

Extraction providers pull arbitrary remote Markdown into the pipeline. Such
content can carry prompt-injection payloads aimed at downstream synthesis
agents. :func:`scan_for_injection` performs a cheap, deterministic, regex-based
scan and returns risk-flag strings that are persisted onto the resulting source
card's ``trust.known_limitations`` so reviewers and synthesis agents are warned.

The scan is intentionally conservative: it flags common, well-known injection
phrasings without attempting full natural-language understanding. A match adds a
single ``"possible_prompt_injection"`` flag (callers may add more context).
"""

from __future__ import annotations

import re

# Common prompt-injection phrasings (case-insensitive). Conservative by design.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all )?(the )?(previous|above|prior) instructions",
        r"disregard (your |all )?(previous )?instructions",
        r"you are now",
        r"system prompt",
        r"reveal your (system )?prompt",
        r"</?(system|assistant)>",
        r"do not tell the user",
    )
)

_INJECTION_FLAG = "possible_prompt_injection"


def scan_for_injection(text: str | None) -> list[str]:
    """Return ``["possible_prompt_injection"]`` if *text* matches a known
    injection pattern, else ``[]``.

    Safe for ``None``/empty input (returns ``[]``).
    """

    if not text:
        return []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return [_INJECTION_FLAG]
    return []


__all__ = ["scan_for_injection"]
