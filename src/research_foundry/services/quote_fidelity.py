"""Quote-vs-source fidelity check (RFUP-1 P4-001/P4-002, PRD FR-6/OQ-2).

Detects **extraction-time corruption**: does the passage a claim's source
citation says it extracted still match, character-for-character, the passage
the *cited source card itself* stored when it was ingested? The canonical
failure mode this exists to catch is a PMC HTML fetch that silently strips a
superscript before the text is ever recorded (``×10⁹/L`` -> ``×10/L``) — a
corruption that is already baked into whichever stored text differs from the
other, with nothing to "drift" afterward.

Explicit distinction from ``verification.check_anchor_hash_match``
------------------------------------------------------------------
``check_anchor_hash_match`` (``services/verification.py``) hashes a **report
builder draft's own block text** against a ``quote_text_hash`` recorded at
link time, so it detects *drift* — someone edited the draft body **after**
a claim was linked (post-hoc tampering of an already-extracted quote, within
one document, over time).

This module's check instead compares **two already-stored, independently
authored documents exactly once** — a claim ledger entry's cited-source quote
against that same source card's own ``extracted_points[].quote`` text. There
is no "time" axis here and nothing to redetect on a second run: either the
two stored renderings agree character-for-character (after the Stage-1
normalization below) or they never did. It catches corruption introduced at
the moment a quote was captured **from** a source **into** a claim, which
``check_anchor_hash_match`` — scoped to a single document's internal
consistency — cannot see.

Kept in its own module (not inlined into ``verification.py``'s monolith) per
the parent plan's H3 risk note: bound the algorithmic surface of the diffing
logic so it stays reviewable and testable in isolation from the rest of the
verifier.

Two-stage normalization policy (P4-002, AC-P4-4..AC-P4-6)
-----------------------------------------------------------
A naive character-for-character diff would false-positive on differences a
publisher's rendering pipeline introduces for purely cosmetic reasons (a
Unicode compatibility variant of a character, collapsed/expanded whitespace,
a "smart quote" vs. its straight-ASCII equivalent) — noise that is NOT
corruption and must never be flagged (AC-P4-5). The policy is two stages,
applied in this order, and the boundary between them is the entire point of
this task:

* **Stage 1 — normalization allowlist** (:func:`_normalize_stage1`): NFKC
  Unicode normalization, whitespace-run collapsing, and quote-mark style
  unification. This is a **comparison-time-only** transform — it is applied
  to *copies* of the two strings purely to decide whether they match; the
  original, un-normalized quote text is never mutated, rewritten, or
  "auto-corrected" in place anywhere (AC-P4-6). If Stage 1 makes the two
  strings agree, that is the *entire* class of difference this check is
  willing to treat as safe.
- **Stage 2 — everything else is material.** Any difference that survives
  Stage-1 normalization is, by definition, not on the allowlist — it is
  always flagged/failed (AC-P4-6). There is no third "close enough, let it
  through" tier and no silent auto-correction step; Stage 2 either matches
  or it fails.

A quote whose Stage-1 normalization itself cannot be completed (an internal
error in the normalization pipeline — *not* the ``locator_only`` case
described below) must never be misreported as a silent "pass":
:func:`check_quote_fidelity` catches that case explicitly and reports a
distinguishable ``"error"`` status (AC-P4-4), kept apart from a confirmed
``"pass"``, a confirmed Stage-2 ``"fail"``, and the ``locator_only``
``"warn"`` case so a caller can tell "verified fidelity", "verified
corruption", "fidelity could not be determined", and "fidelity is
unverifiable" apart. This is also distinct from a claim/card pair for which
this check never had anything to compare and that this check never ran
against at all (a card ingested before this check existed) — *absence* of a
finding is not the same thing as a *checked-and-passed* finding; callers
must not conflate the two.

Scope: P4-001/P4-002/P4-003
----------------------------
A (claim, source) pair with nothing stored on the cited source card's side
to diff against is handled two different ways, depending on *why* nothing
is stored:

* If the cited card's own ``extraction_status`` is explicitly
  ``"locator_only"`` (RFUP-1 P4-003, AC-P4-7/AC-P4-8): fidelity is
  genuinely *unverifiable* for that pair, not confirmed pass or fail, so
  this is reported as a distinguishable, non-blocking ``"warn"``-status
  finding tagged with the reason code :data:`LOCATOR_ONLY_REASON_CODE`
  (``"quote_fidelity_unverifiable_locator_only"``) — never conflated with a
  clean ``"pass"``, a confirmed Stage-2 ``"fail"``, or the internal-error
  ``"error"`` case above. It also never contributes to ``verify_report``'s
  ``unsupported[]`` list (AC-P4-8): this module never decides
  ``unsupported[]`` membership itself, and the ``quote_fidelity`` check's
  registered severity stays ``"warning"`` (see ``verification.py``'s 6d
  wiring comment), so this finding cannot, by itself, block publish.
* Any other reason nothing is stored (a card whose ``extraction_status`` is
  ``"full_text"``/``"partial"``/absent, but whose points simply have no
  ``quote`` populated for some other reason) is unchanged from P4-001:
  silently skipped here — not flagged, not warned, not errored.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# Join separator for concatenating a card's per-point stored quotes into one
# comparison string. Deliberately not empty: two adjacent points' quotes
# should never accidentally fuse into a false-positive substring match. Each
# point's quote is Stage-1-normalized *before* joining (see
# ``_stored_full_text_normalized``), specifically so whitespace collapsing
# can never eat this boundary and fuse two points into a spurious match.
_JOIN_SEP = "\n\n"

# Stage-1 normalization allowlist, part 2/3: quote-mark style unification.
# NFKC (part 1/3, applied separately below) does NOT touch these -- "smart"/
# curly quotation marks are not Unicode compatibility-equivalent to their
# ASCII counterparts, so they survive plain NFKC untouched and need their own
# explicit mapping. Deliberately a small, reviewable allowlist (AC-P4-5) --
# only quote-style variants, nothing that could mask a real character loss.
_CURLY_QUOTE_MAP: dict[str, str] = {
    "‘": "'",  # LEFT SINGLE QUOTATION MARK
    "’": "'",  # RIGHT SINGLE QUOTATION MARK
    "‚": "'",  # SINGLE LOW-9 QUOTATION MARK
    "‛": "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    "′": "'",  # PRIME
    "“": '"',  # LEFT DOUBLE QUOTATION MARK
    "”": '"',  # RIGHT DOUBLE QUOTATION MARK
    "„": '"',  # DOUBLE LOW-9 QUOTATION MARK
    "‟": '"',  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
    "″": '"',  # DOUBLE PRIME
}

# Stage-1 normalization allowlist, part 3/3: whitespace-run collapsing (any
# run of whitespace, including newlines/tabs, becomes a single space; leading
#/trailing whitespace is stripped).
_WHITESPACE_RUN = re.compile(r"\s+")

# Reason code for the P4-003 locator_only warn finding (AC-P4-7) — a distinct,
# grep-able string so callers can tell "fidelity is unverifiable because
# nothing was stored" apart from a confirmed Stage-2 "fail" or the Stage-1
# internal-error "error" case, without having to parse free-text detail
# prose. Public (no leading underscore) and exported via __all__ so callers
# never need to hardcode the literal.
LOCATOR_ONLY_REASON_CODE = "quote_fidelity_unverifiable_locator_only"


def _normalize_stage1(text: str) -> str:
    """Apply the Stage-1 normalization allowlist to ``text`` (AC-P4-5).

    Three safe transforms, applied in this fixed order:

    1. NFKC Unicode normalization -- folds compatibility variants (e.g. a
       superscript digit) to their canonical form.
    2. Quote-mark style unification -- curly/"smart" quotes to their
       straight-ASCII equivalents (:data:`_CURLY_QUOTE_MAP`; NFKC alone does
       not do this).
    3. Whitespace-run collapsing -- any run of whitespace becomes a single
       space, then the result is stripped.

    This is a **read-only, comparison-time** transform: it returns a new
    string and never mutates ``text`` or anything stored on disk (AC-P4-6) --
    callers use the *return value* only to decide whether two strings match;
    the original, un-normalized text is always what gets stored and reported
    in any finding.
    """

    normalized = unicodedata.normalize("NFKC", text)
    for curly, straight in _CURLY_QUOTE_MAP.items():
        normalized = normalized.replace(curly, straight)
    return _WHITESPACE_RUN.sub(" ", normalized).strip()


@dataclass(frozen=True)
class QuoteFidelityResult:
    """Outcome of :func:`check_quote_fidelity`.

    Deliberately its own (severity-less) shape rather than reusing
    ``verification.CheckResult`` — severity is a verifier/config-policy
    concern (see ``config/claim_policy.yaml``'s ``verifier_checks`` entry for
    ``quote_fidelity``), not this module's. Keeping this module free of any
    import from ``verification`` also avoids inviting an import cycle, since
    ``verification.py`` is the one importing *this* module.
    """

    status: str  # "pass" | "fail" | "error" | "warn"
    detail: str
    locations: list[str] = field(default_factory=list)
    #: Subset of ``locations`` (AC-P4-4): (claim, source) pairs for which the
    #: Stage-1 normalization pipeline itself raised, so their fidelity could
    #: not be determined at all -- distinguishable from ``fail`` (a
    #: confirmed Stage-2 material difference) and from ``pass``. Additive
    #: field, defaulted so any existing keyword-arg construction site is
    #: unaffected.
    error_locations: list[str] = field(default_factory=list)
    #: Subset of ``locations`` (RFUP-1 P4-003, AC-P4-7): (claim, source)
    #: pairs whose cited source card is ``extraction_status: locator_only``
    #: -- nothing was ever stored to diff against, so fidelity is genuinely
    #: *unverifiable* for that pair, not confirmed pass, confirmed Stage-2
    #: fail, or an internal Stage-1 error. Additive field, defaulted so any
    #: existing keyword-arg construction site is unaffected.
    warn_locations: list[str] = field(default_factory=list)


def _stored_full_text(card: dict[str, Any]) -> str:
    """Join a source card's own stored per-point quotes, unnormalized
    (AC-P4-1).

    ``card`` is one ``source_index`` entry as produced by
    ``verification._index_source_cards``/``build_global_source_index`` —
    already loaded from disk for this run's other checks (e.g.
    ``supported_claims_have_source_cards``, ``exact_passage_present``), so
    this performs **zero additional I/O and no new fetch/re-crawl** (AC-P4-1).

    Only points with a non-empty ``quote`` contribute. A card with nothing
    stored to diff against (e.g. an ``extraction_status: locator_only`` card,
    or a card whose paragraphs were all too long to retain a short ``quote``
    — see ``source_cards._SHORT_QUOTE``) yields an empty string; the caller
    treats that as "not yet checkable", not a failure.

    Bounded/linear (AC-P4-3): a card's ``extracted_points[]`` is capped
    upstream at ingestion (``source_cards._MAX_POINTS`` points x
    ``source_cards._SHORT_QUOTE`` chars each), so this join can never scale
    worse than linear in a single already-bounded, already-stored card.

    Used only for the P4-001 "is there anything stored at all" emptiness
    check below; the Stage-1-normalized comparison text is built separately
    by :func:`_stored_full_text_normalized`.
    """

    points = card.get("points") or []
    quotes = [
        str(pt.get("quote")) for pt in points if isinstance(pt, dict) and pt.get("quote")
    ]
    return _JOIN_SEP.join(quotes)


def _stored_full_text_normalized(card: dict[str, Any]) -> str:
    """Stage-1-normalized counterpart of :func:`_stored_full_text` (P4-002).

    Each stored point's quote is normalized **independently, then** rejoined
    with :data:`_JOIN_SEP` — never the other way around (normalize-then-join,
    not join-then-normalize) — specifically so whitespace-run collapsing
    inside one point's quote can never eat the boundary between two adjacent
    points and fuse them into a spurious cross-point substring match (see
    :data:`_JOIN_SEP`'s docstring note, which predates this function but
    whose guarantee this function is responsible for preserving).
    """

    points = card.get("points") or []
    quotes = [
        _normalize_stage1(str(pt.get("quote")))
        for pt in points
        if isinstance(pt, dict) and pt.get("quote")
    ]
    return _JOIN_SEP.join(quotes)


def check_quote_fidelity(
    claims: list[dict[str, Any]],
    source_index: dict[str, dict[str, Any]],
) -> QuoteFidelityResult:
    """Compare each claim's cited-source extracted quote against that source
    card's own stored full-text rendering (AC-P4-1), through the two-stage
    normalization policy (AC-P4-4..AC-P4-6).

    A claim's ``sources[]`` entry may carry an optional ``quote`` field — the
    exact passage as captured into the claim at extraction time (the
    ``claim_ledger`` schema's ``sources[]`` items allow
    ``additionalProperties: true``, so this field is purely additive: claims
    written before this task exist have no ``quote`` and are simply skipped,
    never flagged). When present, both it and the cited card's own stored
    text are put through the Stage-1 normalization allowlist
    (:func:`_normalize_stage1`) before the containment check runs — a
    difference Stage 1 resolves is never flagged (AC-P4-5); any difference
    still present afterward always is (AC-P4-6), with no auto-correction of
    either string in place.

    If the Stage-1 normalization pipeline itself raises for a given pair
    (not the ``locator_only``/nothing-stored case below), that pair is
    recorded as ``"error"`` rather than silently treated as a pass
    (AC-P4-4).

    Diffing is a single substring-containment test per (claim, source) pair,
    bounded by the target card's already-bounded stored text (AC-P4-3) — no
    new fetch, no re-crawl, no scan of anything not already loaded into
    ``source_index``.

    A pair with nothing stored to diff against is either warned (the cited
    card's ``extraction_status`` is explicitly ``"locator_only"`` — RFUP-1
    P4-003, AC-P4-7/AC-P4-8) or silently skipped (any other reason nothing
    is stored — unchanged from P4-001). See the module docstring's "Scope"
    section for the full distinction.
    """

    mismatches: list[str] = []
    errors: list[str] = []
    # Parallel to `errors` (same pair ids) but carrying the exception detail
    # for the human-readable `detail` text -- kept separate so `errors`
    # itself stays in the same plain "cid -> sid" shape as `mismatches` and
    # can be unioned into `locations` without format drift.
    error_reasons: list[str] = []
    # RFUP-1 P4-003 (AC-P4-7): (claim, source) pairs whose cited card is
    # extraction_status == "locator_only" -- nothing stored to diff against,
    # so fidelity is genuinely unverifiable for that pair, distinguishable
    # from a confirmed "fail" and from an "error".
    warn_pairs: list[str] = []
    for c in claims:
        cid = c.get("claim_id") or "<no-id>"
        for s in c.get("sources") or []:
            if not isinstance(s, dict):
                continue
            extracted_quote = s.get("quote")
            if not extracted_quote:
                continue
            sid = s.get("source_card_id")
            card = source_index.get(sid) if sid else None
            if card is None:
                # Unresolved source cards are supported_claims_have_source_cards's
                # job to flag, not this check's.
                continue
            pair_id = f"{cid} -> {sid}"
            stored_text = _stored_full_text(card)
            if not stored_text:
                if card.get("extraction_status") == "locator_only":
                    # AC-P4-7: distinguishable, non-blocking warn -- this is
                    # NOT the AC-P4-4 error case (no normalization failure
                    # here, simply nothing to normalize/compare against) and
                    # NOT a confirmed Stage-2 fail.
                    warn_pairs.append(pair_id)
                # Any other reason nothing is stored is out of scope here
                # (unchanged from P4-001): silently skipped, not flagged,
                # not warned, not errored.
                continue

            try:
                normalized_quote = _normalize_stage1(str(extracted_quote))
                normalized_stored = _stored_full_text_normalized(card)
            except Exception as exc:  # noqa: BLE001 — AC-P4-4: any internal
                # Stage-1 normalization failure must surface as a
                # distinguishable error, never be swallowed into a silent
                # "pass" (nor mis-filed as a confirmed Stage-2 "fail" — we
                # genuinely do not know the outcome for this pair).
                errors.append(pair_id)
                error_reasons.append(f"{pair_id} ({type(exc).__name__}: {exc})")
                continue

            if normalized_quote not in normalized_stored:
                mismatches.append(pair_id)

    mismatches = sorted(set(mismatches))
    errors = sorted(set(errors))
    warn_pairs = sorted(set(warn_pairs))
    error_reasons = sorted(set(error_reasons))
    # Status precedence: "error" (fidelity undetermined for >=1 pair, AC-P4-4)
    # outranks "fail" (a confirmed Stage-2 difference), which outranks "warn"
    # (a locator_only pair whose fidelity is unverifiable, AC-P4-7), which
    # outranks "pass". A pair in a higher-precedence bucket must never be
    # masked by, or silently collapsed into, a lower-precedence status
    # elsewhere in the same run.
    if errors:
        status = "error"
    elif mismatches:
        status = "fail"
    elif warn_pairs:
        status = "warn"
    else:
        status = "pass"

    detail_parts: list[str] = []
    if error_reasons:
        detail_parts.append(
            "fidelity could not be determined for the following pair(s) — "
            "Stage-1 normalization raised an internal error (distinguishable "
            "error/unknown status, never reported as pass): "
            + "; ".join(error_reasons)
        )
    if mismatches:
        detail_parts.append(
            "extracted quote does not match its cited source card's stored "
            "text after Stage-1 normalization (NFKC, whitespace collapsing, "
            "quote-mark style — a residual difference is always material, "
            "never auto-corrected): " + ", ".join(mismatches)
        )
    if warn_pairs:
        detail_parts.append(
            f"{LOCATOR_ONLY_REASON_CODE}: cited source card(s) are "
            "extraction_status=locator_only with nothing stored to diff "
            "against — fidelity is unverifiable for the following pair(s), "
            "not confirmed pass or fail, and does not block publish: "
            + ", ".join(warn_pairs)
        )
    if not detail_parts:
        detail_parts.append(
            "every checked claim's extracted quote matches its cited source "
            "card's stored text after Stage-1 normalization"
        )

    # Union so nothing implicated in any bucket is silently absent from the
    # finding's locations — the bucket-specific text above (and
    # error_locations/warn_locations below) is what distinguishes an error
    # pair, a confirmed mismatch pair, and a locator_only-unverifiable pair
    # from one another.
    locations = sorted(set(mismatches) | set(errors) | set(warn_pairs))

    return QuoteFidelityResult(
        status=status,
        detail=" | ".join(detail_parts),
        locations=locations,
        error_locations=errors,
        warn_locations=warn_pairs,
    )


__all__ = ["QuoteFidelityResult", "check_quote_fidelity", "LOCATOR_ONLY_REASON_CODE"]
