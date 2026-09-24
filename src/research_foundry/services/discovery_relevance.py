"""Deterministic discovery query derivation + relevance check against a run brief.

No model call, no network: pure functions over the brief text and a candidate's
title/snippet. The check is reproducible — the same brief and candidate always
yield the same verdict — and is stated here in full:

  * brief terms  B = normalized tokens of the brief title + objective, minus
    STOPWORDS (English function words + research boilerplate) and run labels;
  * a query's terms Q = normalized tokens of that query (Q ⊆ B);
  * a candidate (title + snippet) is ON-TOPIC iff it matches at least
    MIN_BRIEF_TERMS distinct terms of B AND at least MIN_QUERY_TERMS distinct
    terms of the query Q that retrieved it.

Normalization: lowercase; split on anything that is not a letter or digit;
drop tokens shorter than 4 chars or containing a digit; singularize a trailing
"ies"->"y" and a trailing "s" (not "ss").
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

MIN_BRIEF_TERMS = 3
MIN_QUERY_TERMS = 2
MAX_QUERIES = 8
MAX_QUERY_TERMS = 8

STOPWORDS = frozenset(
    """
    about above after again against also among another based because been before being below
    between both could does doing done down during each either else even every from further have
    having here into itself just like made make many more most much must near need only other
    over same should since some such than that their them then there these they this those
    through under until upon very were what when where which while will with within without
    would your yours whose whom
    evidence research published result question project state study paper include included
    including incl relative gather closest marking fresh prior pilot phase section commit docs
    measured decision verify stated record because using used also after against controlled
    question objective brief depth audience technical standard say says said what does
    """.split()
)

_LABEL_RE = re.compile(r"^\s*(?:[A-Za-z]*\d[\w-]*\s+){0,2}[A-Za-z]*\d[\w-]*\s*:\s*")
_BOILERPLATE_RE = re.compile(
    r"\b(?:what does the evidence say about|prior[- ]art evidence (?:for|on)|evidence (?:for|on))\b",
    re.IGNORECASE,
)
_EVIDENCE_ON_RE = re.compile(r"[Ee]vidence on\s*:\s*(.+?)(?:\.\s+(?=[A-Z])|\.\s*$|$)", re.DOTALL)


def normalize(text: str) -> list[str]:
    out: list[str] = []
    for tok in re.split(r"[^A-Za-z0-9]+", text.lower()):
        if len(tok) < 4 or any(ch.isdigit() for ch in tok):
            continue
        if tok.endswith("ies") and len(tok) > 5:
            tok = tok[:-3] + "y"
        elif tok.endswith("s") and not tok.endswith("ss") and len(tok) > 4:
            tok = tok[:-1]
        if tok in STOPWORDS:
            continue
        out.append(tok)
    return out


def _dedupe(tokens: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    for t in tokens:
        seen.setdefault(t, None)
    return list(seen)


def clean_title(title: str) -> str:
    t = _LABEL_RE.sub("", title or "")
    return _BOILERPLATE_RE.sub(" ", t).strip()


def brief_terms(title: str, objective: str) -> set[str]:
    return set(normalize(clean_title(title))) | set(normalize(objective or ""))


def bigrams(text: str) -> set[tuple[str, str]]:
    """Pairs of content tokens that are adjacent in the ORIGINAL text.

    A dropped stopword or short word breaks adjacency (so "pass-1 results and
    methods" never forms "pass method"); a dropped digit-bearing token such as
    a version number does not (so "gemini-3.5-flash" forms "gemini flash").
    """
    pairs: set[tuple[str, str]] = set()
    prev: str | None = None
    for raw in re.split(r"[^A-Za-z0-9]+", text.lower()):
        if not raw:
            continue
        if any(ch.isdigit() for ch in raw):
            continue
        norm = normalize(raw)
        if not norm:
            prev = None
            continue
        tok = norm[0]
        if prev is not None and prev != tok:
            pairs.add((prev, tok))
        prev = tok
    return pairs


def brief_bigrams(title: str, objective: str) -> set[tuple[str, str]]:
    return bigrams(clean_title(title)) | bigrams(objective or "")


def _split_topics(clause: str) -> list[str]:
    """Split a comma/'and' list at depth 0 (parentheses kept with their topic)."""
    parts, depth, cur = [], 0, []
    for ch in clause:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    topics: list[str] = []
    for p in parts:
        p = re.sub(r"^\s*and\s+", "", p.strip())
        inner = re.findall(r"\(([^)]*)\)", p)
        base = re.sub(r"\([^)]*\)", " ", p)
        topics.append(base)
        topics.extend(re.sub(r"^\s*incl\.?\s*", "", i) for i in inner)
    return [t for t in topics if t.strip()]


def build_queries(title: str, objective: str, *, max_queries: int = MAX_QUERIES) -> list[str]:
    """Derive keyword queries: the cleaned title first, then one per listed sub-topic."""
    queries: list[list[str]] = []
    title_terms = _dedupe(normalize(clean_title(title)))
    if title_terms:
        queries.append(title_terms[:MAX_QUERY_TERMS])
    m = _EVIDENCE_ON_RE.search(objective or "")
    topics = _split_topics(m.group(1)) if m else []
    if not topics and objective:
        topics = [s for s in re.split(r"(?<=[.?!])\s+", objective) if s.strip()]
    for topic in topics:
        terms = _dedupe(normalize(topic))
        if len(terms) >= 2:
            queries.append(terms[:MAX_QUERY_TERMS])
    out: list[str] = []
    for q in queries:
        s = " ".join(q)
        if s not in out:
            out.append(s)
    return out[:max_queries]


def relevance(candidate: Mapping[str, Any], terms: set[str], query: str,
              phrases: set[tuple[str, str]] | None = None) -> dict[str, Any]:
    text = f"{candidate.get('title') or ''} {candidate.get('snippet') or ''}"
    toks = set(normalize(text))
    matched = sorted(toks & terms)
    q_matched = sorted(toks & set(normalize(query)))
    p_matched = sorted(" ".join(p) for p in (bigrams(text) & (phrases or set())))
    on_topic = (len(matched) >= MIN_BRIEF_TERMS and len(q_matched) >= MIN_QUERY_TERMS
                and (phrases is None or len(p_matched) >= 1))
    return {
        "on_topic": on_topic,
        "brief_terms_matched": matched,
        "query_terms_matched": q_matched,
        "brief_phrases_matched": p_matched,
        "rule": f">={MIN_BRIEF_TERMS} brief terms, >={MIN_QUERY_TERMS} query terms, >=1 brief phrase",
    }
