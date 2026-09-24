"""Deterministic claim-support gate for claim-map results.

No model call, no network: pure functions over a claim's text, the ORIGINAL
discovery text of its cited sources (never the model-authored source card
body), and the run's question/objective text.

Rule (SUPPORT_RATIO_THRESHOLD = 0.6):

  * C = set(normalize(claim_text)) -- normalized content terms of the claim
    (see research_foundry.services.discovery_relevance.normalize);
  * S = set(normalize(" ".join(source_texts))) -- normalized content terms
    of every cited source's ORIGINAL discovery text (title + snippet);
  * Qt = set(normalize(question_text)) -- normalized content terms of the
    run's question/objective.

A claim is REJECTED when any of the following hold:

  1. C is empty -> "claim has no content terms".
  2. borrowed_terms = sorted((C & Qt) - S) is non-empty -> "claim borrows
     question terms absent from its sources". This is the measured defect: a
     model reuses the QUESTION's own vocabulary (e.g. "pass-1") to make an
     unrelated source look relevant, when that vocabulary never appears in
     the source text it actually cites.
  3. support_ratio = |C & S| / |C| < SUPPORT_RATIO_THRESHOLD -> "claim terms
     not found in cited sources".
  4. any number in the claim (plain numeric regex over the raw claim text)
     is not also a number token of the raw source text (token match, so "1"
     is not supported by "10") -> "claim cites
     numbers absent from its sources". Numbers are checked against the RAW
     text, never the normalized term sets, because normalize() drops any
     token containing a digit.

A claim with none of the above reasons is "supported".
"""

from __future__ import annotations

import re
from typing import Any

from ..frontmatter import load_md
from ..ids import slugify, today_compact
from ..paths import FoundryPaths
from ..yamlio import dump_yaml, load_yaml
from .claim_mapping import _claim_type, _intent_from_run, _materiality, _validate
from .discovery_relevance import normalize

SUPPORT_RATIO_THRESHOLD = 0.6

_NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def support_verdict(
    claim_text: str, source_texts: list[str], question_text: str
) -> dict[str, Any]:
    """Deterministic accept/reject verdict for one claim against its cited
    sources' original discovery text. See module docstring for the rule."""

    claim_terms = set(normalize(claim_text or ""))
    source_terms = set(normalize(" ".join(source_texts or [])))
    question_terms = set(normalize(question_text or ""))

    reasons: list[str] = []
    borrowed_terms = sorted((claim_terms & question_terms) - source_terms)

    if not claim_terms:
        support_ratio = 0.0
        reasons.append("claim has no content terms")
    else:
        support_ratio = len(claim_terms & source_terms) / len(claim_terms)
        if borrowed_terms:
            reasons.append("claim borrows question terms absent from its sources")
        if support_ratio < SUPPORT_RATIO_THRESHOLD:
            reasons.append("claim terms not found in cited sources")

    # Token-level, not substring: "1" must not be "supported" by a "10".
    source_numbers = set(_NUMBER_RE.findall(" ".join(source_texts or [])))
    unsupported_numbers = [
        n for n in _NUMBER_RE.findall(claim_text or "") if n not in source_numbers
    ]
    if unsupported_numbers:
        reasons.append("claim cites numbers absent from its sources")

    unsupported_terms = sorted(claim_terms - source_terms)

    return {
        "supported": not reasons,
        "reasons": reasons,
        "claim_terms": sorted(claim_terms),
        "unsupported_terms": unsupported_terms,
        "borrowed_terms": borrowed_terms,
        "support_ratio": round(support_ratio, 4),
    }


def _candidate_text_by_url(run_paths) -> dict[str, str]:
    """url -> "title snippet" for every entry of a run's
    source_candidates.yaml -- the ORIGINAL discovery text, never the
    model-written source card body."""

    out: dict[str, str] = {}
    if not run_paths.source_candidates.exists():
        return out
    data = load_yaml(run_paths.source_candidates) or {}
    for entry in data.get("source_candidates") or []:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not url:
            continue
        title = str(entry.get("title") or "")
        snippet = str(entry.get("snippet") or "")
        out[url] = (title + " " + snippet).strip()
    return out


def apply_claim_map(
    run_id: str,
    claims: list[dict],
    *,
    question_text: str,
    paths: FoundryPaths | None = None,
) -> dict[str, Any]:
    """Filter claims (claim_schema shape: text, sources: [{source_card_id,
    relation}], ...) against each cited source's ORIGINAL discovery text,
    writing accepted claims to claims/claim_ledger.yaml (the shape
    research_foundry.services.claim_mapping.build_claim_ledger writes) and
    rejected claims + verdicts to claims/claim_map_rejections.yaml."""

    paths = paths or FoundryPaths.discover()
    run_paths = paths.run_paths(run_id)
    run_paths.claims.mkdir(parents=True, exist_ok=True)

    candidate_text_by_url = _candidate_text_by_url(run_paths)

    accepted: list[dict] = []
    rejections: list[dict] = []
    counter = 0

    for claim in claims:
        text = str(claim.get("text") or "")
        sources = claim.get("sources") or []
        source_texts: list[str] = []
        resolved_sources: list[dict] = []
        no_original_text = not sources

        for src in sources:
            if not isinstance(src, dict):
                no_original_text = True
                continue
            source_card_id = src.get("source_card_id")
            card_path = run_paths.sources / f"{source_card_id}.md"
            if not source_card_id or not card_path.is_file():
                no_original_text = True
                continue
            try:
                metadata, _body = load_md(card_path)
            except Exception:  # noqa: BLE001
                no_original_text = True
                continue
            if not isinstance(metadata, dict) or metadata.get("source_card_id") != source_card_id:
                no_original_text = True
                continue
            locator = (metadata.get("source") or {}).get("locator") or {}
            url = locator.get("url")
            original_text = candidate_text_by_url.get(url) if url else None
            if not original_text:
                no_original_text = True
                continue
            source_texts.append(original_text)
            resolved_sources.append(src)

        if no_original_text or not source_texts:
            verdict = {
                "supported": False,
                "reasons": ["no original source text for cited card"],
                "claim_terms": sorted(set(normalize(text))),
                "unsupported_terms": [],
                "borrowed_terms": [],
                "support_ratio": 0.0,
            }
            rejections.append({"claim": claim, "verdict": verdict})
            continue

        verdict = support_verdict(text, source_texts, question_text)
        if not verdict["supported"]:
            rejections.append({"claim": claim, "verdict": verdict})
            continue

        counter += 1
        claim_type = _claim_type(text)
        materiality = _materiality(text, claim_type)
        ledger_sources = []
        for src in resolved_sources:
            ledger_sources.append(
                {
                    "source_card_id": src.get("source_card_id"),
                    "evidence_id": str(src.get("evidence_id") or "ev_001"),
                    "relation": str(src.get("relation") or "supports"),
                    "locator": str(src.get("locator") or "para/0"),
                }
            )
        accepted.append(
            {
                "claim_id": f"clm_{counter:03d}",
                "text": text or "(no text)",
                "materiality": materiality,
                "claim_type": claim_type,
                "status": "supported",
                "confidence": "medium",
                "sources": ledger_sources,
                "inference_basis": {"from_claims": [], "reasoning_summary": None},
                "report_locations": [],
                "reviewer_notes": "",
            }
        )

    intent_id = (
        _intent_from_run(run_paths)
        or f"intent_research_{today_compact()}_{slugify(run_id)}"
    )
    ledger = {
        "id": f"claims_{today_compact()}_{slugify(run_id)}",
        "intent_id": intent_id,
        "report_ref": "reports/report_draft.md",
        "verification_status": "pending",
        "claims": accepted,
        "unresolved_questions": [],
    }

    ledger_path = run_paths.claim_ledger
    dump_yaml(ledger, ledger_path)
    _validate(ledger, "claim_ledger", paths)

    rejections_path = run_paths.claims / "claim_map_rejections.yaml"
    dump_yaml(
        {"run_id": run_id, "question_text": question_text, "rejections": rejections},
        rejections_path,
    )

    return {
        "accepted": len(accepted),
        "rejected": len(rejections),
        "ledger": ledger_path,
        "rejections": rejections_path,
    }


__all__ = ["SUPPORT_RATIO_THRESHOLD", "support_verdict", "apply_claim_map"]
