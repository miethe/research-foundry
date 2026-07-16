"""Source card ingestion (``rf ingest`` / ``rf source-card create``).

Turns a locator (local file path or URL) into a schema-valid ``source_card``
Markdown document under ``runs/<run>/sources/``. The default path is fully
deterministic and offline: URL fetching is opt-in (``fetch=True``), best-effort
with an 8s timeout, and any failure degrades to a locator-only card rather than
raising.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from ..config import FoundryConfig
from ..errors import NotFoundError, SchemaError
from ..frontmatter import dump_md
from ..ids import now_iso, source_card_id
from ..paths import FoundryPaths
from ..registry import SOURCE_INDEX, Registry
from ..schemas import SchemaRegistry
from ..yamlio import append_jsonl
from . import audit_service
from .audit_service import AuditEvent

_MAX_POINTS = 8
_SHORT_QUOTE = 280
_FETCH_TIMEOUT = 8


@dataclass(frozen=True)
class IngestResult:
    """Outcome of ingesting one source into a run."""

    source_card_id: str
    path: Path
    source_type: str
    degraded: bool  # True if content could not be fetched/read


def _schema_registry(paths: FoundryPaths) -> SchemaRegistry | None:
    """Resolve a schema registry rooted at the injected workspace (or dist)."""

    if paths.schemas.exists():
        return SchemaRegistry(schemas_dir=paths.schemas)
    from ..paths import distribution_root

    dist = distribution_root() / "schemas"
    return SchemaRegistry(schemas_dir=dist) if dist.exists() else None


def _validate(obj: dict, schema_name: str, paths: FoundryPaths) -> None:
    """Validate ``obj`` vs its schema; raise SchemaError on failure (skip if absent)."""

    registry = _schema_registry(paths)
    if registry is None or not registry.has(schema_name):
        return
    result = registry.validate(obj, schema_name)
    if not result.ok:
        raise SchemaError(f"{schema_name} validation failed: " + "; ".join(result.errors))


def _is_url(locator: str) -> bool:
    parsed = urlparse(locator)
    return parsed.scheme in ("http", "https", "file")


def _split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs (blank-line separated)."""

    parts = re.split(r"\n\s*\n", text or "")
    return [p.strip() for p in parts if p.strip()]


def _summary_of(paragraph: str, *, limit: int = 200) -> str:
    """One-line summary: first sentence (or truncated paragraph)."""

    flat = " ".join(paragraph.split())
    match = re.search(r"^(.+?[.!?])(\s|$)", flat)
    candidate = match.group(1) if match else flat
    return candidate[:limit].rstrip()


def _fetch_url(url: str) -> str | None:
    """Best-effort fetch of a URL's text; returns None on any failure/timeout."""

    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=_FETCH_TIMEOUT) as resp:  # noqa: S310
            raw = resp.read()
        text = raw.decode("utf-8", errors="replace")
        # Strip HTML tags lightly so deterministic point extraction stays readable.
        if "<" in text and ">" in text:
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
            text = re.sub(r"<[^>]+>", " ", text)
        return text
    except Exception:  # noqa: BLE001  (offline / unreachable -> degraded, never raise)
        return None


def _read_local(path: Path) -> tuple[str | None, bool]:
    """Read a local file's text. PDFs with no extractor -> (None, degraded)."""

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        # No bundled PDF text extractor: record the locator and degrade.
        return None, True
    try:
        return path.read_text(encoding="utf-8", errors="replace"), False
    except Exception:  # noqa: BLE001
        try:
            data = path.read_bytes()
            return data.decode("utf-8", errors="replace"), False
        except Exception:  # noqa: BLE001
            return None, True


def _build_points(content: str | None, *, degraded: bool) -> list[dict]:
    """Deterministically split content into up to 8 evidence points."""

    if degraded or not content:
        return [
            {
                "evidence_id": "ev_001",
                "locator": "para/0",
                "summary": "Content not retrieved; locator recorded for follow-up.",
                "quote": None,
                "supports_potential_claims": ["clm_pending"],
                "needs_content": True,
            }
        ]
    paragraphs = _split_paragraphs(content)[:_MAX_POINTS]
    if not paragraphs:
        paragraphs = [content.strip()[:_SHORT_QUOTE]] if content.strip() else []
    points: list[dict] = []
    for i, para in enumerate(paragraphs, start=1):
        quote = para if len(para) <= _SHORT_QUOTE else None
        points.append(
            {
                "evidence_id": f"ev_{i:03d}",
                "locator": f"para/{i}",
                "summary": _summary_of(para),
                "quote": quote,
                "supports_potential_claims": ["clm_pending"],
            }
        )
    return points


def ingest_source(
    locator: str,
    *,
    run_id: str,
    source_type: str = "other",
    sensitivity: str = "personal",
    title: str | None = None,
    created_by_agent: str = "rf_source_carder",
    fetch: bool = False,
    content: str | None = None,
    extra_limitations: list[str] | None = None,
    assertion_registry_workspace_id: str | None = None,
    paths: FoundryPaths | None = None,
) -> IngestResult:
    """Ingest one source into ``runs/<run>/sources/`` as a source_card.

    Deterministic + offline by default. ``fetch=True`` attempts a best-effort URL
    fetch (8s timeout); any failure degrades to a locator-only card. Local files
    are read as text; PDFs without a text extractor are recorded by locator and
    flagged degraded.

    When ``content`` is supplied (e.g. markdown already extracted by a search-
    router provider) no fetch/read is attempted: the given text is used directly
    as the source content. An empty ``content`` string degrades to a locator-only
    card. Pass extractor provenance via ``created_by_agent``.
    """

    paths = paths or FoundryPaths.discover()
    run_paths = paths.run_paths(run_id)
    if not run_paths.run.exists():
        raise NotFoundError(f"run not found: {run_id} ({run_paths.run})")
    run_paths.sources.mkdir(parents=True, exist_ok=True)

    local_path = Path(locator)
    is_local_file = local_path.exists() and local_path.is_file()
    is_url = (not is_local_file) and _is_url(locator)

    degraded = False
    loc_url: str | None = None
    loc_file: str | None = None

    if content is not None:
        # Caller supplied content directly (e.g. extractor markdown) — no fetch.
        degraded = not content
        if _is_url(locator):
            loc_url = locator
        else:
            loc_file = locator
    elif is_local_file:
        loc_file = str(local_path)
        content, degraded = _read_local(local_path)
    elif is_url:
        loc_url = locator
        if fetch:
            content = _fetch_url(locator)
            degraded = content is None
        else:
            degraded = True  # offline default: locator-only
    else:
        # Unknown locator: record it as a file_path-shaped reference, degraded.
        loc_file = locator
        degraded = True

    eff_title = title or (local_path.stem if is_local_file else None) or locator
    src_id = source_card_id(eff_title, locator)

    points = _build_points(content, degraded=degraded)

    # known_limitations: base (degraded marker) + any caller-supplied flags
    # (e.g. prompt-injection risk from extraction), deduped, existing first.
    known_limitations: list[str] = ["content_not_retrieved"] if degraded else []
    for lim in extra_limitations or []:
        if lim and lim not in known_limitations:
            known_limitations.append(lim)

    front_matter = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": src_id,
        "created_at": now_iso(),
        "created_by_agent": created_by_agent,
        "sensitivity": sensitivity,
        "source": {
            "title": eff_title,
            "source_type": source_type,
            "locator": {
                "url": loc_url,
                "file_path": loc_file,
                "doi": None,
                "repo": None,
            },
            "authors": [],
            "publisher": None,
            "published_at": None,
            "accessed_at": now_iso(),
            "version": None,
        },
        "trust": {
            "source_rank": "unknown",
            "reliability_notes": (
                "Content unavailable; locator recorded only."
                if degraded
                else "Ingested deterministically; not yet reliability-rated."
            ),
            "known_limitations": known_limitations,
            "conflicts_with": [],
        },
        "usage": {
            "allowed_for_public_output": sensitivity == "public",
            "allowed_for_work_output": sensitivity in ("public", "work_sensitive", "personal"),
            "allowed_for_personal_meatywiki": sensitivity != "client_sensitive",
            "citation_required": True,
            "quote_limit_notes": "Quote short excerpts only; cite the source.",
        },
        "extracted_points": points,
    }

    body = (
        f"# Source Card: {eff_title}\n\n"
        "## Summary\n\n"
        f"{'Content not retrieved.' if degraded else _summary_of(content or '')}\n\n"
        "## Key evidence\n\n"
        + "".join(f"- ({p['evidence_id']}) {p['summary']}\n" for p in points)
        + "\n## Limitations\n\n"
        + ("- Content could not be fetched/read.\n" if degraded else "- None recorded.\n")
        + "\n## Related source cards\n\n"
    )

    out_path = run_paths.sources / f"{src_id}.md"
    dump_md(front_matter, body, out_path)

    _validate(front_matter, "source_card", paths)

    Registry.open(SOURCE_INDEX, paths=paths).upsert(
        {
            "id": src_id,
            "run_id": run_id,
            "title": eff_title,
            "source_type": source_type,
            "sensitivity": sensitivity,
            "degraded": degraded,
            "path": str(out_path.relative_to(paths.root)),
        }
    )

    _trace(run_paths, stage="ingest", source_card_id=src_id, degraded=degraded)

    # Explicit opt-in seam: the default source-card flow remains run-local.
    # The registry never enables reuse or canonical-claim feature flags.
    ledger_writes_allowed = (
        FoundryConfig(paths=paths).assertion_ledger_capabilities().ledger_write_allowed
    )
    if assertion_registry_workspace_id and content is not None and not degraded and ledger_writes_allowed:
        from .assertion_registry import AssertionRegistry

        registry_usage: dict[str, Any] = dict(cast(dict[str, Any], front_matter["usage"]))
        registry = AssertionRegistry(workspace_id=assertion_registry_workspace_id, paths=paths)
        # Segment the edition by each point's verbatim quote so a short exact
        # quote can bind via find_exact_passages() instead of only ever
        # matching the single whole-document passage the registry stored
        # before this fix (see docs/project_plans/SPIKEs/
        # assertion-ledger-backfill-mapping.md, defect 1b). Dedupe
        # whitespace-normalized duplicates: registry.ingest() rejects an
        # ambiguous passage selector list outright. Falls back to `None`
        # (whole-document passage) when no point carries a short-enough quote.
        seen_quotes: set[str] = set()
        quote_passages: list[str] = []
        for point in points:
            point_quote = point.get("quote")
            if isinstance(point_quote, str) and point_quote:
                normalized = " ".join(point_quote.split())
                if normalized not in seen_quotes:
                    seen_quotes.add(normalized)
                    quote_passages.append(point_quote)
        registry.ingest(
            src_id,
            content,
            media_type="text/html" if is_url else "text/plain",
            access_scope=sensitivity,
            allowed_use=registry_usage,
            retrieval_locator={"url": loc_url, "file_path": loc_file},
            passages=quote_passages or None,
            source_card_snapshot=registry.source_card_snapshot(src_id, front_matter),
        )
    elif assertion_registry_workspace_id and content is not None and not degraded:
        _trace(run_paths, stage="ingest", assertion_ledger_write_disabled=True)

    # Audit: record artifact acceptance after file write + registry upsert (fail-open).
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="artifact_accepted",
            action="ingest_source",
            target_ref=src_id,
            result="success",
        ),
    )

    return IngestResult(
        source_card_id=src_id,
        path=out_path,
        source_type=source_type,
        degraded=degraded,
    )


def create_source_card(**kwargs) -> IngestResult:
    """Thin alias to :func:`ingest_source` (``rf source-card create``)."""

    return ingest_source(**kwargs)


def list_source_cards(run_id: str, paths: FoundryPaths | None = None) -> list[Path]:
    """List source card Markdown files for a run (sorted, deterministic)."""

    paths = paths or FoundryPaths.discover()
    sources_dir = paths.run_paths(run_id).sources
    if not sources_dir.exists():
        return []
    return sorted(sources_dir.glob("*.md"))


def _trace(run_paths, **fields) -> None:
    """Append a best-effort run-trace record (never fail the stage)."""

    try:
        append_jsonl({"ts": now_iso(), **fields}, run_paths.run_trace)
    except Exception:  # noqa: BLE001
        pass


__all__ = [
    "IngestResult",
    "ingest_source",
    "create_source_card",
    "list_source_cards",
]
