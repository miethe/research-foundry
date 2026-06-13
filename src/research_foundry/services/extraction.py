"""Deterministic extraction (``rf extract``).

For each source card in a run, produce one ``extraction_card`` YAML whose
``extracted_facts`` are derived deterministically from the source card's
``extracted_points``. ``contradictions_or_cautions`` are pulled from the source's
recorded ``known_limitations`` and its body ``## Limitations`` section. No network
or model is required; ``model_profile`` is recorded for provenance only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..errors import NotFoundError, SchemaError
from ..frontmatter import load_md
from ..ids import now_iso, short_hash
from ..paths import FoundryPaths
from ..schemas import SchemaRegistry
from ..yamlio import append_jsonl, dump_yaml

_NUMERIC = re.compile(r"\d")


@dataclass(frozen=True)
class ExtractResult:
    """Outcome of running extraction over a run's source cards."""

    run_id: str
    cards: list[str]  # extraction_card ids
    count: int


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


def _limitations_from_body(body: str) -> list[str]:
    """Extract bullet items under a ``## Limitations`` heading in the card body."""

    match = re.search(r"##\s*Limitations\s*\n(.*?)(?:\n##\s|\Z)", body or "", flags=re.S | re.I)
    if not match:
        return []
    out: list[str] = []
    for line in match.group(1).splitlines():
        item = line.strip().lstrip("-*").strip()
        if item and item.lower() not in ("none recorded.", "none.", "none"):
            out.append(item)
    return out


def _fact_from_point(point: dict) -> dict:
    """Map a source card extracted_point -> an extraction_card extracted_fact."""

    text = str(point.get("summary") or "").strip()
    quote = point.get("quote")
    return {
        "evidence_id": str(point.get("evidence_id") or "ev_001"),
        "text": text or "(no summary)",
        "locator": str(point.get("locator") or "para/0"),
        "confidence": "medium",
        "quote_available": bool(quote),
        "notes": ("flagged needs_content" if point.get("needs_content") else ""),
    }


def extract_run(
    run_id: str,
    *,
    model_profile: str = "rf_extract_cheap",
    paths: FoundryPaths | None = None,
) -> ExtractResult:
    """Produce one extraction_card per source card in ``runs/<run>/sources/``."""

    paths = paths or FoundryPaths.discover()
    run_paths = paths.run_paths(run_id)
    if not run_paths.run.exists():
        raise NotFoundError(f"run not found: {run_id} ({run_paths.run})")
    sources_dir = run_paths.sources
    extractions_dir = run_paths.extractions
    extractions_dir.mkdir(parents=True, exist_ok=True)

    # Clean overwrite: clear pre-existing extraction cards so a removed/replaced
    # source card cannot leave an orphan card behind. Regeneration below is
    # deterministic, so re-running with the same sources is idempotent.
    for stale in extractions_dir.glob("*.yaml"):
        stale.unlink()

    card_ids: list[str] = []
    for src_file in sorted(sources_dir.glob("*.md")):
        meta, body = load_md(src_file)
        source_card_id = str(meta.get("source_card_id") or src_file.stem)
        points = meta.get("extracted_points") or []
        facts = [_fact_from_point(p) for p in points if isinstance(p, dict)]

        cautions = [
            {"text": str(t), "locator": "card/trust"}
            for t in (meta.get("trust", {}).get("known_limitations") or [])
        ]
        for lim in _limitations_from_body(body):
            cautions.append({"text": lim, "locator": "card/limitations"})

        src_hash = short_hash(source_card_id)
        ext_id = f"ext_{now_iso()[:10].replace('-', '')}_{src_hash}_001"
        card = {
            "id": ext_id,
            "source_card_id": source_card_id,
            "created_at": now_iso(),
            "extractor_agent": "rf_extractor",
            "model_profile": model_profile,
            "extracted_facts": facts,
            "extracted_definitions": [],
            "extracted_metrics": [
                {
                    "metric_name": "evidence_point",
                    "value": str(f["evidence_id"]),
                    "unit": None,
                    "date_context": None,
                    "locator": f["locator"],
                }
                for f in facts
                if _NUMERIC.search(f["text"])
            ],
            "contradictions_or_cautions": cautions,
        }

        out_path = extractions_dir / f"{ext_id}.yaml"
        dump_yaml(card, out_path)
        _validate(card, "extraction_card", paths)
        card_ids.append(ext_id)

    _trace(run_paths, stage="extract", run_id=run_id, count=len(card_ids))

    return ExtractResult(run_id=run_id, cards=card_ids, count=len(card_ids))


def _trace(run_paths, **fields) -> None:
    try:
        append_jsonl({"ts": now_iso(), **fields}, run_paths.run_trace)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["ExtractResult", "extract_run"]
