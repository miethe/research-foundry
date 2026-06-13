"""Claim ledger construction (``rf claim-map``).

Reads all extraction cards in a run, maps every extracted fact to a claim with a
deterministic ``claim_type`` heuristic, and writes ``claims/claim_ledger.yaml``
(plus ``contradiction_log.yaml`` and ``inference_log.yaml``). Every claim carries
at least one ``source.source_card_id`` and is recorded ``supported`` since each is
backed by extracted evidence. No network or model is required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..errors import NotFoundError, SchemaError
from ..ids import now_iso, slugify, today_compact
from ..paths import FoundryPaths
from ..registry import CLAIM_INDEX, Registry
from ..schemas import SchemaRegistry
from ..yamlio import append_jsonl, dump_yaml, load_yaml

_NUMERIC = re.compile(r"\d|%")
_COMPARATIVE = re.compile(r"\b(more|less|than|vs\.?|versus|fewer|greater|higher|lower)\b", re.I)
_CAUSAL = re.compile(r"\b(because|causes?|leads? to|reduces?|increases?|results? in)\b", re.I)
_ATTRIBUTION = re.compile(r"\b(says?|according to|claims?|reports?|states?)\b", re.I)


@dataclass(frozen=True)
class ClaimMapResult:
    """Outcome of building a claim ledger for a run."""

    run_id: str
    ledger_path: Path
    claims_total: int
    by_status: dict  # {supported: n, inference: n, ...}


def _schema_registry(paths: FoundryPaths) -> SchemaRegistry | None:
    if paths.schemas.exists():
        return SchemaRegistry(schemas_dir=paths.schemas)
    from ..paths import distribution_root

    dist = distribution_root() / "schemas"
    return SchemaRegistry(schemas_dir=dist) if dist.exists() else None


def _validate(obj: dict, schema_name: str, paths: FoundryPaths) -> None:
    registry = _schema_registry(paths)
    if registry is None or not registry.has(schema_name):
        return
    result = registry.validate(obj, schema_name)
    if not result.ok:
        raise SchemaError(f"{schema_name} validation failed: " + "; ".join(result.errors))


def _claim_type(text: str) -> str:
    """Deterministic claim-type heuristic per the contract."""

    if _NUMERIC.search(text):
        return "quantitative"
    if _COMPARATIVE.search(text):
        return "comparative"
    if _CAUSAL.search(text):
        return "causal"
    if _ATTRIBUTION.search(text):
        return "attribution"
    return "factual"


def _materiality(text: str, claim_type: str) -> str:
    """Facts/metrics are material; everything else is background."""

    if claim_type == "quantitative" or _NUMERIC.search(text):
        return "material"
    return "background"


def build_claim_ledger(
    run_id: str,
    *,
    intent_id: str | None = None,
    paths: FoundryPaths | None = None,
) -> ClaimMapResult:
    """Build ``claims/claim_ledger.yaml`` from a run's extraction cards."""

    paths = paths or FoundryPaths.discover()
    run_paths = paths.run_paths(run_id)
    if not run_paths.run.exists():
        raise NotFoundError(f"run not found: {run_id} ({run_paths.run})")
    run_paths.claims.mkdir(parents=True, exist_ok=True)

    if intent_id is None:
        intent_id = _intent_from_run(run_paths) or f"intent_research_{today_compact()}_{slugify(run_id)}"

    claims: list[dict] = []
    contradictions: list[dict] = []
    counter = 0

    for ext_file in sorted(run_paths.extractions.glob("*.yaml")):
        card = load_yaml(ext_file)
        if not isinstance(card, dict):
            continue
        source_card_id = str(card.get("source_card_id") or "")
        for fact in card.get("extracted_facts") or []:
            if not isinstance(fact, dict):
                continue
            counter += 1
            text = str(fact.get("text") or "").strip()
            claim_type = _claim_type(text)
            evidence_id = str(fact.get("evidence_id") or "ev_001")
            locator = str(fact.get("locator") or "para/0")
            claims.append(
                {
                    "claim_id": f"clm_{counter:03d}",
                    "text": text or "(no text)",
                    "materiality": _materiality(text, claim_type),
                    "claim_type": claim_type,
                    "status": "supported",
                    "confidence": str(fact.get("confidence") or "medium"),
                    "sources": [
                        {
                            "source_card_id": source_card_id,
                            "evidence_id": evidence_id,
                            "relation": "supports",
                            "locator": locator,
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                    "reviewer_notes": "",
                }
            )

        # Seed contradictions from extraction cautions.
        for caution in card.get("contradictions_or_cautions") or []:
            if isinstance(caution, dict) and caution.get("text"):
                contradictions.append(
                    {
                        "source_card_id": source_card_id,
                        "text": str(caution["text"]),
                        "locator": str(caution.get("locator") or "card"),
                    }
                )

    ledger = {
        "id": f"claims_{today_compact()}_{slugify(run_id)}",
        "intent_id": intent_id,
        "report_ref": "reports/report_draft.md",
        "verification_status": "pending",
        "claims": claims,
        "unresolved_questions": _seed_questions(claims),
    }

    ledger_path = run_paths.claim_ledger
    dump_yaml(ledger, ledger_path)
    _validate(ledger, "claim_ledger", paths)

    dump_yaml(
        {"run_id": run_id, "generated_at": now_iso(), "contradictions": contradictions},
        run_paths.contradiction_log,
    )
    inferences = [
        {"claim_id": c["claim_id"], "from_claims": c["inference_basis"]["from_claims"]}
        for c in claims
        if c["status"] == "inference"
    ]
    dump_yaml(
        {"run_id": run_id, "generated_at": now_iso(), "inferences": inferences},
        run_paths.inference_log,
    )

    by_status: dict[str, int] = {}
    for c in claims:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1

    Registry.open(CLAIM_INDEX, paths=paths).upsert(
        {
            "id": ledger["id"],
            "run_id": run_id,
            "intent_id": intent_id,
            "claims_total": len(claims),
            "by_status": by_status,
            "path": str(ledger_path.relative_to(paths.root)),
        }
    )

    _trace(run_paths, stage="claim_map", run_id=run_id, claims_total=len(claims))

    return ClaimMapResult(
        run_id=run_id,
        ledger_path=ledger_path,
        claims_total=len(claims),
        by_status=by_status,
    )


def _intent_from_run(run_paths) -> str | None:
    """Best-effort: read intent_id from run.yaml if present."""

    try:
        data = load_yaml(run_paths.run_yaml)
        if isinstance(data, dict):
            return data.get("intent_id")
    except Exception:  # noqa: BLE001
        pass
    return None


def _seed_questions(claims: list[dict]) -> list[dict]:
    """Seed one unresolved question when no material claims were found."""

    if any(c["materiality"] == "material" for c in claims):
        return []
    return [
        {
            "question": "Are there quantitative or material findings to substantiate?",
            "why_unresolved": "No material claims surfaced from current sources.",
            "recommended_next_source": None,
        }
    ]


def _trace(run_paths, **fields) -> None:
    try:
        append_jsonl({"ts": now_iso(), **fields}, run_paths.run_trace)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["ClaimMapResult", "build_claim_ledger"]
