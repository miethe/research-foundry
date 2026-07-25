"""Deterministic write-time term/usage-role index (`_term_index`).

Attaches a namespaced, additive, **non-authoritative** index to claim items:
which canonical vocabulary terms a claim's text mentions, and how each is
used (``threshold`` vs ``background``). Everything here is a pure function
over already-loaded data or a bounded local-file read of the vocabulary/
source-card files already present in a run -- there is no model or network
call anywhere in this module (D6), and nothing here is added to
``SOURCE_ASSERTION_MATERIAL_FIELDS`` or consulted by ``rf verify`` (D2/D8).

Vocabulary files (``vocab/*.yaml``) are jsonschema-validated at load time
against ``schemas/term_vocab.schema.yaml``: a malformed file fails closed
(raises :class:`VocabularyError`, blocking claim-map); a missing file warns
and returns ``None`` so callers can proceed with `_term_index` omitted
(OQ-D).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..frontmatter import load_md
from ..paths import FoundryPaths, distribution_root
from ..schemas import SchemaRegistry
from ..yamlio import load_yaml

logger = logging.getLogger(__name__)

DEFAULT_VOCAB_FILENAME = "pediatric-terms.yaml"

# Comparator vocabulary -> a matched term is describing a threshold only when
# one of these appears *together with* a digit in its context window (design
# spec §2, TASK-1.3a; tightened per second-review defect: a bare digit alone
# is never sufficient -- see _THRESHOLD_DIGIT below).
#
# `over` was dropped (fresh-corpus review, TASK-remediation): clinical prose
# writes cut-points as "above"/"greater than"; "over" is overwhelmingly
# temporal ("recovered over 12 weeks") or a quantity ("over 300,000 births"),
# never a threshold phrasing in the fresh 26-sentence hand-labeled sample --
# it cost 6 false positives there and bought 0 true positives. `under` earns
# its keep despite the same review flagging 3 residual false positives on
# quantity phrasings ("under 4 percent prevalence") -- it also buys genuine
# clinical cut-points no other comparator word covers ("ferritin under 12
# ng/mL", "growth percentile drops under the 5th percentile"); dropping it
# too traded those true positives away (see _THRESHOLD_CLASSIFICATION_CORPUS
# and classify_usage_role's "Known limitation" docstring section).
_THRESHOLD_COMPARATOR = re.compile(
    r"[<>]=?"
    r"|\b(?:less|more|greater|fewer|higher|lower)\s+than\b"
    r"|\babove\b|\bbelow\b|\bat\s+least\b|\bat\s+most\b"
    r"|\bexceed(?:s|ed|ing)?\b"
    r"|\bcutoff\b|\bthreshold\b|\bunder\b",
    re.IGNORECASE,
)

# A bare digit is *never* sufficient on its own -- numeric proximity (a year,
# an age, a dose, a guideline version) is common in clinical prose and is not
# threshold semantics. classify_usage_role requires _THRESHOLD_COMPARATOR AND
# _THRESHOLD_DIGIT to both match within the same window before labeling
# "threshold" (closes the second-review defect: the previous regex treated a
# bare `\d` alternative as sufficient by itself, so mere numeric proximity --
# not threshold semantics -- triggered the label).
_THRESHOLD_DIGIT = re.compile(r"\d")

# Characters of context scanned on *each side* of a matched term's own
# occurrence when looking for comparator+digit threshold context.
#
# Measured over the >=15-sentence hand-labeled corpus in
# ``tests/test_term_index.py`` (``_THRESHOLD_CLASSIFICATION_CORPUS``), not
# fitted to a handful of fixtures (the ±15 value this replaced was derived
# from only 3 sentences and broke in both directions once the corpus grew).
# Sweeping window width against that corpus:
#   - Widths up to ~35 chars: precision 0.75, recall 0.75 -- the comparator+
#     digit requirement alone fixes every same-clause false positive, but two
#     genuine thresholds separated from their term by an intervening
#     descriptive clause ("Hematocrit, measured on a venous blood sample,
#     was below 33 percent.": ~38 chars from "Hematocrit" to "below"; "...
#     when measured at altitude, below 11.0 g/dL...": ~30 chars) are still
#     missed (false negatives).
#   - 50 chars: recovers both intervening-clause cases (recall 1.00) while a
#     stress fixture with an unrelated comparator+digit ~55 chars away in a
#     different clause ("The CBC was drawn during a visit where blood
#     pressure was below 90 systolic in some patients.") still stays
#     background -- precision holds at 0.80.
#   - 60+ chars: that stress fixture flips to a false positive -- precision
#     drops back to 0.73. 60 is the measured point where the window starts
#     reaching into unrelated clauses again.
# 50 is the widest value in the safe band, chosen to maximize recall without
# yet crossing into the failure mode the original ±15 window existed to
# prevent. It does NOT recover every intervening-clause case in general --
# ``venous_blood_sample`` in the hematocrit example above is *closer* to
# "below 33" than "hematocrit" is, so it is a genuine, unavoidable structural
# false positive at any window wide enough to reach "hematocrit" from the
# other side of the same clause (see the classify_usage_role docstring's
# "Known limitation" section and the corpus regression test asserting this).
_THRESHOLD_WINDOW_CHARS = 50

USAGE_ROLE_THRESHOLD = "threshold"
USAGE_ROLE_BACKGROUND = "background"


class VocabularyError(ValueError):
    """A vocabulary file exists but is malformed -- fail closed (OQ-D)."""


def _vocab_dir(paths: FoundryPaths) -> Path:
    if paths.vocab.exists():
        return paths.vocab
    dist = distribution_root() / "vocab"
    return dist if dist.exists() else paths.vocab


def load_vocabulary(
    paths: FoundryPaths | None = None, *, filename: str = DEFAULT_VOCAB_FILENAME
) -> dict[str, Any] | None:
    """Load + validate the term vocabulary file.

    Returns ``None`` (after logging a warning) when the file is missing --
    callers must treat this as "skip indexing," not an error. Raises
    :class:`VocabularyError` when the file exists but is not a well-formed
    ``{vocabulary_version, terms}`` mapping per
    ``schemas/term_vocab.schema.yaml`` -- callers must let this propagate and
    block claim-map (fail closed, OQ-D).
    """

    paths = paths or FoundryPaths.discover()
    vocab_path = _vocab_dir(paths) / filename
    if not vocab_path.exists():
        logger.warning(
            "term vocabulary file not found at %s; _term_index will be omitted", vocab_path
        )
        return None

    data = load_yaml(vocab_path)
    if not isinstance(data, dict):
        raise VocabularyError(f"vocabulary file {vocab_path} is not a mapping")

    registry = SchemaRegistry(schemas_dir=paths.schemas if paths.schemas.exists() else None)
    result = registry.validate(data, "term_vocab")
    if not result.ok:
        raise VocabularyError(
            f"vocabulary file {vocab_path} failed schema validation: " + "; ".join(result.errors)
        )

    return {
        "vocabulary_version": data["vocabulary_version"],
        "terms": {term_id: list(aliases) for term_id, aliases in data["terms"].items()},
    }


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)


def match_terms(text: str, vocabulary: Mapping[str, Any] | None) -> list[str]:
    """Return canonical term ids whose aliases match *text*.

    Pure function, no I/O. Case-insensitive, word-boundary matching (adapted
    from CARP's case-folded substring matcher, D5 -- no Aho-Corasick
    dependency for this vocabulary size). Returns ``[]`` for empty text, a
    missing vocabulary, or zero hits -- never raises on a no-match input.
    """

    if not text or not vocabulary:
        return []
    terms = vocabulary.get("terms")
    if not isinstance(terms, Mapping):
        return []

    matched: list[str] = []
    for term_id, aliases in terms.items():
        if not isinstance(aliases, Iterable):
            continue
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                continue
            if _alias_pattern(alias).search(text):
                matched.append(term_id)
                break
    return sorted(matched)


def _context_windows(text: str, aliases: Iterable[str]) -> list[tuple[int, int]]:
    """Character spans of ``text``, each ± ``_THRESHOLD_WINDOW_CHARS`` around
    one occurrence of one of *aliases* (case-insensitive, word-boundary).

    Pure local computation -- the same word-boundary matching
    :func:`match_terms` uses, just also recording *where* each alias
    occurred so the threshold regex can be scoped to a window around the
    term's own match rather than the whole claim text.
    """

    windows: list[tuple[int, int]] = []
    for alias in aliases:
        if not isinstance(alias, str) or not alias:
            continue
        for occurrence in _alias_pattern(alias).finditer(text):
            start = max(0, occurrence.start() - _THRESHOLD_WINDOW_CHARS)
            end = min(len(text), occurrence.end() + _THRESHOLD_WINDOW_CHARS)
            windows.append((start, end))
    return windows


def classify_usage_role(
    term_id: str,
    text: str,
    *,
    pediatric_cds_threshold_terms: Iterable[str] = (),
    aliases: Iterable[str] | None = None,
) -> str:
    """Rule-based usage-role classification for one matched term (D6).

    Structured-field keying takes precedence and bypasses regex entirely:
    when *term_id* is in *pediatric_cds_threshold_terms* -- a term that
    :func:`build_term_index` has already resolved as the one(s) a claim's
    cited ``pediatric_cds`` legacy-shape ``threshold{value, units_ucum}``
    block actually names (TASK-1.3b/defect-1b) -- the role is ``threshold``
    directly from that structured field.

    Otherwise falls back to a regex check scoped to a bounded **context
    window around this term's own match position(s)** in *text*
    (``_THRESHOLD_WINDOW_CHARS`` on each side, see that constant's docstring
    for how the size was chosen) -- not the whole claim text, so a
    comparator or a coincidental digit elsewhere in an unrelated clause of
    the same sentence (a year, an age, a guideline version) cannot promote
    this term (defect-1a). *aliases* are the term's own surface forms from
    the vocabulary, used to locate its match positions; when omitted (e.g.
    direct unit-test calls), *term_id* itself is used as the alias.

    A window is only "threshold" when it contains **both** a comparator
    (``_THRESHOLD_COMPARATOR``: <, >, "less/more/greater/fewer/higher/lower
    than", "above", "below", "at least", "at most", "exceed(s/ed/ing)",
    "cutoff", "threshold", "under") **and** a digit (``_THRESHOLD_DIGIT``).
    A bare digit alone is never sufficient (second-review defect: mere
    numeric proximity -- not threshold semantics -- was previously enough to
    trigger the label, and clinical prose puts numbers near clinical terms
    constantly). A bare mention, or a comparator with no nearby digit, ->
    ``background``. No model or embedding call anywhere.

    Known limitations (documented, not silently wrong -- both are inherent
    to a pure distance-based window and are deferred to the semantic pass in
    PRD-OQ-2, not fixed here):

    1. Quantity/temporal phrasing using "under" is indistinguishable from a
       clinical cut-point without unit semantics. "IDA prevalence fell ...
       to under 4 percent" and "Thalassemia trait is present in under 1
       percent of this cohort" are quantity statements, not thresholds, but
       read identically to "ferritin under 12 ng/mL" -- comparator+digit
       within the window -- to a regex with no notion of what the number
       *means*. This is the dominant residual failure mode after dropping
       `over` (see the comment above ``_THRESHOLD_COMPARATOR`` and the
       corpus rows in ``_THRESHOLD_CLASSIFICATION_CORPUS`` in
       ``tests/test_term_index.py`` labeled as such), not a footnote.
    2. When a threshold phrase is separated from its term by an intervening
       descriptive clause set off by commas (e.g. "Hematocrit, measured on
       a venous blood sample, was below 33 percent."), the window is
       centered on *each* term's own match position, so a term that sits
       structurally closer to the comparator+digit phrase than the term the
       phrase actually describes can still be misclassified "threshold"
       (here: ``venous_blood_sample``, not just ``hematocrit``, falls inside
       the window around "below 33 percent"). There is no reliable
       regex-only way to tell which of two terms in the same clause a
       threshold phrase modifies. See the corpus regression test
       ``test_classify_usage_role_intervening_clause_corpus`` in
       ``tests/test_term_index.py`` for the measured behavior on this case.
    """

    if term_id in pediatric_cds_threshold_terms:
        return USAGE_ROLE_THRESHOLD
    for start, end in _context_windows(text, aliases if aliases is not None else (term_id,)):
        window = text[start:end]
        if _THRESHOLD_COMPARATOR.search(window) and _THRESHOLD_DIGIT.search(window):
            return USAGE_ROLE_THRESHOLD
    return USAGE_ROLE_BACKGROUND


def index_pediatric_cds_thresholds(sources_dir: Path) -> dict[tuple[str, str], str]:
    """Map ``(source_card_id, evidence_id) -> locator_text`` for evidence
    points that carry a ``pediatric_cds`` legacy-shape ``threshold`` block
    with a non-null ``value`` (schemas/pediatric_cds.schema.json's
    ``PediatricCdsBlockLegacy``).

    *locator_text* is the block's own ``threshold.passage_locator`` -- "the
    verbatim quote fragment carrying the number" per that field's schema
    description -- or ``""`` when the block has a value but no locator text.
    This is deliberately **not** a bare ``True``/``False`` flag (defect-1b):
    the legacy schema has no explicit "which analyte does this threshold
    describe" field, so the caller-facing contract keys the structured
    signal to *whatever text the block itself supplies to identify it*,
    letting :func:`build_term_index` match vocabulary aliases against that
    text to resolve the specific term(s) named -- never every term the
    claim happens to also mention. An empty string is a legitimate "value
    present but unidentified" result; callers must treat that as "no term
    named" (fall back to regex), not "promote everything".

    Local file I/O only (reads already-written source-card Markdown front
    matter for this run) -- no model or network call. Mirrors the read shape
    of ``verification._index_source_cards`` but scoped to only the field
    this module needs.
    """

    index: dict[tuple[str, str], str] = {}
    if not sources_dir.exists():
        return index
    for card_path in sorted(sources_dir.glob("*.md")):
        try:
            meta, _ = load_md(card_path)
        except Exception:  # noqa: BLE001 - a broken card is treated as missing
            continue
        source_card_id = meta.get("source_card_id")
        if not isinstance(source_card_id, str) or not source_card_id:
            continue
        for point in meta.get("extracted_points") or []:
            if not isinstance(point, dict):
                continue
            evidence_id = point.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id:
                continue
            block = point.get("pediatric_cds")
            threshold = block.get("threshold") if isinstance(block, dict) else None
            if not isinstance(threshold, dict) or threshold.get("value") is None:
                continue
            locator = threshold.get("passage_locator")
            index[(source_card_id, evidence_id)] = locator if isinstance(locator, str) else ""
    return index


def build_term_index(
    text: str,
    vocabulary: Mapping[str, Any] | None,
    *,
    pediatric_cds_threshold: str | bool = False,
) -> dict[str, Any] | None:
    """Compute the ``_term_index`` block for one claim's text.

    *pediatric_cds_threshold* is the locator text returned by
    :func:`index_pediatric_cds_thresholds` for this claim's cited evidence
    point (``""``/``False`` when there is none). It is matched against the
    vocabulary to resolve the **specific** term(s) it names -- via the same
    alias matcher :func:`match_terms` uses -- and only those term(s) inherit
    ``threshold`` directly from the structured field (defect-1b: FR-3(b)
    keys the signal to the term it references, never to every term the
    claim's text happens to also mention). When the locator text is empty,
    unset, or names none of this claim's matched terms, no term is promoted
    on that basis -- each term falls back to the windowed regex check in
    :func:`classify_usage_role` instead of being blanket-promoted.

    Returns ``None`` when there is no vocabulary loaded or zero term hits --
    callers must omit the ``_term_index`` key entirely in that case (AC-1
    resilience), never write an empty-but-present block.
    """

    terms = match_terms(text, vocabulary)
    if not terms:
        return None

    named_terms: set[str] = set()
    if pediatric_cds_threshold and isinstance(pediatric_cds_threshold, str):
        named_terms = set(match_terms(pediatric_cds_threshold, vocabulary))
    threshold_terms = tuple(term for term in terms if term in named_terms)

    term_aliases = vocabulary.get("terms") if vocabulary else None
    usage_roles = {
        term: classify_usage_role(
            term,
            text,
            pediatric_cds_threshold_terms=threshold_terms,
            aliases=term_aliases.get(term) if isinstance(term_aliases, Mapping) else None,
        )
        for term in terms
    }
    return {
        "terms": terms,
        "usage_roles": usage_roles,
        "vocabulary_version": vocabulary["vocabulary_version"] if vocabulary else None,
    }


def report_term_index_rollup(claims: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Union `_term_index` fields across a report's claims into a
    report-level rollup (OQ-E), computed at the same write time as
    claim-map's own attach -- purely additive, no new extraction.

    Returns ``None`` when no claim carries a `_term_index` block.
    """

    terms: set[str] = set()
    usage_roles: dict[str, set[str]] = {}
    vocabulary_version: str | None = None

    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        idx = claim.get("_term_index")
        if not isinstance(idx, Mapping):
            continue
        for term in idx.get("terms") or []:
            if isinstance(term, str):
                terms.add(term)
        roles = idx.get("usage_roles")
        if isinstance(roles, Mapping):
            for term, role in roles.items():
                if isinstance(term, str) and isinstance(role, str):
                    usage_roles.setdefault(term, set()).add(role)
        version = idx.get("vocabulary_version")
        if isinstance(version, str) and version:
            vocabulary_version = version

    if not terms and vocabulary_version is None:
        return None

    return {
        "terms": sorted(terms),
        "usage_roles": {term: sorted(roles) for term, roles in usage_roles.items()},
        "vocabulary_version": vocabulary_version,
    }


__all__ = [
    "DEFAULT_VOCAB_FILENAME",
    "USAGE_ROLE_BACKGROUND",
    "USAGE_ROLE_THRESHOLD",
    "VocabularyError",
    "build_term_index",
    "classify_usage_role",
    "index_pediatric_cds_thresholds",
    "load_vocabulary",
    "match_terms",
    "report_term_index_rollup",
]
