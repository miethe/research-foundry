"""Shared evidence catalog — derived sqlite3 + FTS5 read model (Phase 1).

Public-multiuser-release Phase 1 (spec §6, plan D1/D2/D5/D6). Normalizes every
run's claim graph — claims, inferences, resolved sources, the report draft,
reusable-output candidates, and writeback targets — into a single searchable
cross-run index at ``<workspace>/.rf_cache/catalog.db``.

Hard invariants:

* **Derived, rebuildable** — the DB is never canonical. Markdown/YAML run
  artifacts remain the durable evidence; this store can be dropped and
  rebuilt from them at any time (``rebuild``). ``PRAGMA user_version`` is
  bumped whenever the schema changes; a mismatch triggers a drop + recreate
  of the schema (not an automatic re-import — callers re-run ``import_all``).
* **Import via the export layer, live** — every run is read through
  :func:`~research_foundry.services.export_service.export_run`, never by
  parsing ``run.json`` or source-card files directly. Import always requests
  ``sensitivity_threshold="client_sensitive"`` (max permissive) so the raw
  claim graph is captured once; sensitivity gating happens at READ time.
* **Sensitivity gated at read time, fail-closed** — every catalog item carries
  an effective sensitivity rank computed with the same
  :data:`~research_foundry.services.export_service.SENSITIVITY_ORDER`
  semantics as the export layer (unknown labels rank stricter than every
  known level). ``search``/``get_item``/``stats`` resolve the active
  threshold via
  :func:`~research_foundry.services.export_service.resolve_threshold` and
  EXCLUDE any item whose rank exceeds it. Source quote/summary text nested in
  a visible item's payload is independently redacted per evidence point.
* **Deterministic IDs** — ``catalog_item_id = "ci_" + sha1(f"{item_type}:
  {run_id}:{local_ref}").hexdigest()[:12]``. Re-importing a run is
  delete-then-insert in one transaction, so import is idempotent.

Recovering per-citation sensitivity
------------------------------------
``export_run()``'s resolved-source shape only exposes the *source card's*
``sensitivity`` label (constant across every claim that cites the card); the
per-*point* sensitivity (``extracted_points[].sensitivity``) that the export
layer factors into ``effective_rank = max(card_rank, point_rank)`` before
deciding its own ``redacted`` flag is never surfaced directly, and at the
max-permissive ``client_sensitive`` import threshold ``redacted`` is always
``False`` (nothing can exceed the loosest defined rank). To recover the true
per-citation effective rank — required by the plan's "max of card/point rank"
sensitivity derivation — :func:`_probe_citation_ranks` calls ``export_run()``
once per known threshold level and records the lowest threshold at which each
citation's ``redacted`` flag turns ``False``; that threshold *is* the
effective rank. A citation still redacted even at the loosest defined level
(``client_sensitive``) carries an unrecognized sensitivity label upstream and
is assigned :data:`_UNKNOWN_RANK` (fail-closed). This stays entirely within
the "import via export_run() live" contract — no raw source-card file is ever
read by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..ids import now_iso
from ..paths import FoundryPaths
from .export_service import (
    REDACTION_MARKER,
    SENSITIVITY_ORDER,
    ExportError,
    export_run,
    resolve_threshold,
)

# --- schema versioning (D1) --------------------------------------------------
# v2 (public-multiuser-release P3 Wave D, plan D10/D11/landmine #3): adds the
# catalog_report_drafts derived index table. A version bump means ANY
# mismatch drops and recreates the whole schema (see _ensure_schema) — this is
# always safe because catalog.db is 100% derived: run items are rebuilt from
# export_run() via import_all(), and draft index rows are rebuilt from
# on-disk draft.yaml files via builder_service.reindex_all_drafts(). Neither
# rebuild path reads anything from the DB itself.
SCHEMA_VERSION = 2

# --- sensitivity ranks (mirrors export_service's private helper; only the
# public SENSITIVITY_ORDER constant is reused, per the contract) ------------
_UNKNOWN_RANK = len(SENSITIVITY_ORDER)
_RANK_TO_LABEL: dict[int, str] = {v: k for k, v in SENSITIVITY_ORDER.items()}
# Ascending looseness (rank 0..3) — the full set of defined threshold labels,
# used to probe per-citation effective ranks (see module docstring).
_THRESHOLD_LABELS: tuple[str, ...] = tuple(
    sorted(SENSITIVITY_ORDER, key=SENSITIVITY_ORDER.__getitem__)
)

# --- item types (spec §6 / plan item-mapping table) -------------------------
ITEM_TYPES: tuple[str, ...] = (
    "claim",
    "inference",
    "source",
    "report",
    "reusable_output",
    "writeback",
)

_VALID_SORTS: tuple[str, ...] = ("updated", "title", "confidence")
_DEFAULT_PAGE_SIZE = 25
_MAX_PAGE_SIZE = 200

_CONFIDENCE_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3}
_WRITEBACK_STATUSES = frozenset({"published", "pending", "failed"})


class CatalogError(ExportError):
    """A catalog operation failed (unknown run, malformed artifact, ...)."""


# ---------------------------------------------------------------------------
# Connection + schema management
# ---------------------------------------------------------------------------

_DDL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS catalog_items (
        catalog_item_id   TEXT PRIMARY KEY,
        item_type         TEXT NOT NULL,
        run_id            TEXT NOT NULL,
        local_ref         TEXT NOT NULL,
        project           TEXT,
        title             TEXT NOT NULL,
        summary           TEXT,
        status            TEXT,
        sensitivity       TEXT NOT NULL,
        sensitivity_rank  INTEGER NOT NULL,
        trust_label       TEXT,
        confidence        TEXT,
        confidence_rank   INTEGER NOT NULL DEFAULT 0,
        source_count      INTEGER NOT NULL DEFAULT 0,
        created_at        TEXT,
        updated_at        TEXT,
        payload_json      TEXT NOT NULL,
        search_text       TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_run ON catalog_items(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_type ON catalog_items(item_type)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_project ON catalog_items(project)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_sensitivity_rank "
    "ON catalog_items(sensitivity_rank)",
    """
    CREATE TABLE IF NOT EXISTS catalog_links (
        run_id        TEXT NOT NULL,
        from_item_id  TEXT NOT NULL,
        to_item_id    TEXT NOT NULL,
        relation      TEXT NOT NULL,
        PRIMARY KEY (from_item_id, to_item_id, relation)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalog_links_run ON catalog_links(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_links_from ON catalog_links(from_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_links_to ON catalog_links(to_item_id)",
    """
    CREATE TABLE IF NOT EXISTS catalog_import_log (
        run_id       TEXT PRIMARY KEY,
        imported_at  TEXT NOT NULL,
        item_count   INTEGER NOT NULL
    )
    """,
    # --- Report Builder draft index (v2, plan D10/D11) ----------------------
    # Derived, rebuildable read model of file-canonical drafts living under
    # <workspace>/reports/drafts/<report_draft_id>/draft.yaml. NEVER the
    # source of truth (see builder_service module docstring) — a drop+rebuild
    # here (schema version bump, or `rf catalog rebuild`) must never touch the
    # draft files, and must reconstruct this table byte-for-byte from them via
    # builder_service.reindex_all_drafts().
    """
    CREATE TABLE IF NOT EXISTS catalog_report_drafts (
        report_draft_id     TEXT PRIMARY KEY,
        title               TEXT NOT NULL,
        status              TEXT,
        sensitivity         TEXT NOT NULL,
        sensitivity_rank    INTEGER NOT NULL,
        audience            TEXT,
        origin              TEXT,
        project_id          TEXT,
        workspace_id        TEXT,
        created_by          TEXT,
        current_version_id  TEXT,
        block_count         INTEGER NOT NULL DEFAULT 0,
        claim_link_count    INTEGER NOT NULL DEFAULT 0,
        source_link_count   INTEGER NOT NULL DEFAULT 0,
        created_at          TEXT,
        updated_at          TEXT,
        draft_path          TEXT NOT NULL,
        search_text         TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalog_report_drafts_status "
    "ON catalog_report_drafts(status)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_report_drafts_sensitivity_rank "
    "ON catalog_report_drafts(sensitivity_rank)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_report_drafts_project "
    "ON catalog_report_drafts(project_id)",
)

_FTS_DDL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts "
    "USING fts5(catalog_item_id UNINDEXED, title, summary, body)"
)

_DROP_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS catalog_fts",
    "DROP TABLE IF EXISTS catalog_links",
    "DROP TABLE IF EXISTS catalog_items",
    "DROP TABLE IF EXISTS catalog_import_log",
    "DROP TABLE IF EXISTS catalog_report_drafts",
)


def _create_schema(conn: sqlite3.Connection) -> None:
    for stmt in _DDL:
        conn.execute(stmt)
    try:
        conn.execute(_FTS_DDL)
    except sqlite3.OperationalError:
        # FTS5 not compiled into this sqlite3 build — search() falls back to
        # LIKE over the always-populated search_text column.
        pass


def _drop_schema(conn: sqlite3.Connection) -> None:
    for stmt in _DROP_STATEMENTS:
        conn.execute(stmt)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the schema, dropping and recreating it on a version mismatch (D1)."""

    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version != SCHEMA_VERSION:
        _drop_schema(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    _create_schema(conn)


def _fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_fts'"
    ).fetchone()
    return row is not None


def _connect(paths: FoundryPaths) -> sqlite3.Connection:
    db_path: Path = paths.catalog_db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    _ensure_schema(conn)
    return conn


@contextmanager
def _db(paths: FoundryPaths) -> Iterator[sqlite3.Connection]:
    conn = _connect(paths)
    try:
        yield conn
    finally:
        conn.close()


def rebuild_schema(paths: FoundryPaths) -> None:
    """Force a schema drop + recreate regardless of the stored user_version.

    Used by ``rf catalog rebuild`` / the rebuild API before re-importing every
    run from scratch.
    """

    with _db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _drop_schema(conn)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            _create_schema(conn)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


# ---------------------------------------------------------------------------
# Small deterministic helpers
# ---------------------------------------------------------------------------


def _make_item_id(item_type: str, run_id: str, local_ref: str) -> str:
    digest = hashlib.sha1(
        f"{item_type}:{run_id}:{local_ref}".encode()
    ).hexdigest()
    return f"ci_{digest[:12]}"


def report_item_id(run_id: str) -> str:
    """The ``catalog_item_id`` of a run's synthetic ``report`` item (P1).

    Public, deterministic helper so other services (P3 Wave D's
    ``builder_service``, plan D11) can link a Report Builder draft to its
    originating run's report item via ``catalog_links`` (``derived_from``)
    without re-deriving the ``(item_type, run_id, local_ref)`` hashing rule
    themselves — see :func:`_build_report_row`'s ``local_ref="report"``.
    """

    return _make_item_id("report", run_id, "report")


def _rank(label: str | None) -> int:
    if label is None:
        return SENSITIVITY_ORDER.get("public", 0)
    return SENSITIVITY_ORDER.get(str(label), _UNKNOWN_RANK)


def _label_for_rank(rank: int) -> str:
    return _RANK_TO_LABEL.get(rank, "unknown")


def _confidence_rank(value: str | None) -> int:
    if not value:
        return 0
    return _CONFIDENCE_RANK.get(str(value).lower(), 0)


def _scalar_text(value: Any) -> str | None:
    """Coerce any value to a sqlite3-bindable scalar (str or None).

    A dict/list can never be bound to a TEXT column; this is the last line of
    defense for scalar catalog_items columns (see :func:`_trust_label_of` for
    the specific ``trust`` object case this exists to catch).
    """

    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    stripped = " ".join(text.split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: max(limit - 1, 0)].rstrip() + "…"


_FRONTMATTER_FENCE_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def _first_non_heading_paragraph(markdown: str | None) -> str | None:
    """First non-empty, non-heading paragraph of a report draft (for summary)."""

    if not markdown:
        return None
    text = _FRONTMATTER_FENCE_RE.sub("", markdown, count=1)
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block or block.startswith("#"):
            continue
        return " ".join(block.split())
    return None


def _normalize_writeback_status(status: str | None) -> str:
    """Mirror the frontend's ``normalizeWritebackStatus`` (LibraryScreen.tsx)."""

    s = (status or "").lower()
    return s if s in _WRITEBACK_STATUSES else "other"


def _trust_label_of(trust: Any) -> str | None:
    """Coerce a source card's ``trust`` field to a scalar label.

    Per ``schemas/source_card.schema.yaml``, ``trust`` is an object
    (``{source_rank, reliability_notes, known_limitations, ...}``); legacy or
    synthetic data may instead carry a plain string. Extract ``source_rank``
    when present, otherwise fall back to a string cast, never a raw dict (a
    dict cannot be bound as a sqlite3 scalar column value).
    """

    if trust is None:
        return None
    if isinstance(trust, dict):
        rank = trust.get("source_rank")
        return str(rank) if rank is not None else None
    return str(trust)


def _project_of(export_data: dict[str, Any]) -> str | None:
    linked = export_data.get("linked_projects")
    if isinstance(linked, list) and linked:
        return str(linked[0])
    category = export_data.get("category")
    return str(category) if category else None


# ---------------------------------------------------------------------------
# Per-citation sensitivity probing (see module docstring)
# ---------------------------------------------------------------------------

_CitationKey = tuple[str | None, str | None, str | None]  # (claim_id, source_card_id, evidence_id)


def _iter_resolved_citations(
    export_data: dict[str, Any],
) -> Iterator[tuple[str | None, dict[str, Any]]]:
    for claim in export_data.get("claims") or []:
        claim_id = claim.get("claim_id")
        for src in claim.get("sources") or []:
            if not isinstance(src, dict):
                continue
            if not src.get("resolved") or src.get("dangling"):
                continue
            yield claim_id, src


def _probe_citation_ranks(
    paths: FoundryPaths,
    run_id: str,
    *,
    permissive_export: dict[str, Any],
) -> dict[_CitationKey, int]:
    """Recover each resolved citation's true effective sensitivity rank.

    Calls ``export_run()`` once per threshold level below the max-permissive
    one already fetched by the caller (``permissive_export``, expected to be
    the ``client_sensitive`` call) and records the lowest threshold at which
    ``redacted`` is ``False`` for each ``(claim_id, source_card_id,
    evidence_id)`` triple. Still-redacted-at-``client_sensitive`` citations
    get :data:`_UNKNOWN_RANK` (fail-closed).
    """

    ranks: dict[_CitationKey, int] = {}
    resolved_keys: set[_CitationKey] = set()

    for rank, label in enumerate(_THRESHOLD_LABELS):
        data = (
            permissive_export
            if label == _THRESHOLD_LABELS[-1]
            else export_run(paths, run_id, sensitivity_threshold=label)
        )
        for claim_id, src in _iter_resolved_citations(data):
            key = (claim_id, src.get("source_card_id"), src.get("evidence_id"))
            resolved_keys.add(key)
            if key in ranks:
                continue
            if not src.get("redacted"):
                ranks[key] = rank

    for key in resolved_keys:
        ranks.setdefault(key, _UNKNOWN_RANK)
    return ranks


# ---------------------------------------------------------------------------
# Row construction (item mapping table — plan §"Item mapping (import contract)")
# ---------------------------------------------------------------------------


def _base_row(
    *,
    item_type: str,
    run_id: str,
    local_ref: str,
    project: str | None,
    title: str,
    summary: str | None,
    status: str | None,
    sensitivity_rank: int,
    trust_label: str | None,
    confidence: str | None,
    source_count: int,
    created_at: str | None,
    updated_at: str | None,
    payload: dict[str, Any],
    extra_search_text: str = "",
) -> dict[str, Any]:
    catalog_item_id = _make_item_id(item_type, run_id, local_ref)
    # Defense in depth: on-disk artifacts don't always match their schema (a
    # real-world source card's ``trust``/``usage`` are objects per
    # source_card.schema.yaml, not strings) — coerce every scalar TEXT column
    # to a plain string so a stray dict/list can never fail the sqlite3 bind.
    project = _scalar_text(project)
    title = _scalar_text(title) or ""
    summary = _scalar_text(summary)
    status = _scalar_text(status)
    trust_label = _scalar_text(trust_label)
    confidence = _scalar_text(confidence)
    search_text = " ".join(
        filter(None, [title, summary or "", extra_search_text])
    ).lower()
    return {
        "catalog_item_id": catalog_item_id,
        "item_type": item_type,
        "run_id": run_id,
        "local_ref": local_ref,
        "project": project,
        "title": title,
        "summary": summary,
        "status": status,
        "sensitivity": _label_for_rank(sensitivity_rank),
        "sensitivity_rank": sensitivity_rank,
        "trust_label": trust_label,
        "confidence": confidence,
        "confidence_rank": _confidence_rank(confidence),
        "source_count": source_count,
        "created_at": created_at,
        "updated_at": updated_at,
        "payload_json": json.dumps(payload, ensure_ascii=False),
        "search_text": search_text,
    }


def _build_claim_and_inference_rows(
    export_data: dict[str, Any],
    run_id: str,
    *,
    project: str | None,
    created_at: str | None,
    run_sensitivity_rank: int,
    citation_ranks: dict[_CitationKey, int],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    """Build claim/inference rows.

    Returns ``(rows, claim_id_to_item_id, report_claim_ids)`` — the last
    element lists every claim/inference ``claim_id`` with a non-empty
    ``report_locations``, for the ``report -> claim`` ("contains") links.
    """

    rows: list[dict[str, Any]] = []
    claim_id_to_item_id: dict[str, str] = {}
    report_claim_ids: list[str] = []

    for claim in export_data.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or "")
        if not claim_id:
            continue
        basis = claim.get("inference_basis") or {}
        from_claims = basis.get("from_claims") or []
        is_inference = bool(from_claims)
        item_type = "inference" if is_inference else "claim"

        resolved_sources = [
            s
            for s in (claim.get("sources") or [])
            if isinstance(s, dict) and s.get("resolved") and not s.get("dangling")
        ]
        distinct_source_ids = {s.get("source_card_id") for s in resolved_sources}
        max_source_rank = 0
        for src in resolved_sources:
            key: _CitationKey = (claim_id, src.get("source_card_id"), src.get("evidence_id"))
            max_source_rank = max(max_source_rank, citation_ranks.get(key, _UNKNOWN_RANK))
        item_sensitivity_rank = max(run_sensitivity_rank, max_source_rank)

        text = claim.get("text") or ""
        title = _truncate(text, 160)
        summary = (
            basis.get("reasoning_summary") if is_inference and basis.get("reasoning_summary") else text
        ) or None

        payload = {
            "text": text,
            "materiality": claim.get("materiality"),
            "claim_type": claim.get("claim_type"),
            "inference_basis": {
                "from_claims": list(from_claims),
                "reasoning_summary": basis.get("reasoning_summary"),
            },
            "report_locations": claim.get("report_locations") or [],
            "cited_sources": [
                {
                    "source_card_id": s.get("source_card_id"),
                    "evidence_id": s.get("evidence_id"),
                    "relation": s.get("relation"),
                    "locator": s.get("locator"),
                }
                for s in resolved_sources
            ],
        }

        row = _base_row(
            item_type=item_type,
            run_id=run_id,
            local_ref=claim_id,
            project=project,
            title=title,
            summary=summary,
            status=claim.get("status"),
            sensitivity_rank=item_sensitivity_rank,
            trust_label=claim.get("status"),
            confidence=claim.get("confidence"),
            source_count=len(distinct_source_ids),
            created_at=created_at,
            updated_at=created_at,
            payload=payload,
            extra_search_text=str(basis.get("reasoning_summary") or ""),
        )
        rows.append(row)
        claim_id_to_item_id[claim_id] = row["catalog_item_id"]
        if claim.get("report_locations"):
            report_claim_ids.append(claim_id)

    return rows, claim_id_to_item_id, report_claim_ids


def _build_source_rows(
    export_data: dict[str, Any],
    run_id: str,
    *,
    project: str | None,
    created_at: str | None,
    run_sensitivity_rank: int,
    citation_ranks: dict[_CitationKey, int],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Dedup resolved (non-dangling) sources by ``source_card_id`` (plan row 3).

    Sensitivity floors to ``max(run_sensitivity_rank, own effective rank)`` —
    matching claim/inference rows — so a loosely-labeled source card cannot
    read as less sensitive than the run it was gathered under (F2).
    """

    aggregated: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for claim in export_data.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or "")
        for src in claim.get("sources") or []:
            if not isinstance(src, dict) or not src.get("resolved") or src.get("dangling"):
                continue
            sid = str(src.get("source_card_id") or "")
            if not sid:
                continue
            key: _CitationKey = (claim_id, sid, src.get("evidence_id"))
            point_rank = citation_ranks.get(key, _UNKNOWN_RANK)
            entry = aggregated.setdefault(
                sid,
                {
                    "title": src.get("title") or sid,
                    "source_type": src.get("source_type"),
                    "url": src.get("url"),
                    "trust": src.get("trust"),
                    "usage": src.get("usage"),
                    "card_sensitivity": src.get("sensitivity"),
                    "max_rank": 0,
                    "citing_claims": set(),
                    "evidence_points": [],
                },
            )
            if sid not in order:
                order.append(sid)
            entry["max_rank"] = max(entry["max_rank"], point_rank)
            entry["citing_claims"].add(claim_id)
            entry["evidence_points"].append(
                {
                    "claim_id": claim_id,
                    "evidence_id": src.get("evidence_id"),
                    "relation": src.get("relation"),
                    "locator": src.get("evidence_locator") or src.get("locator"),
                    "quote": src.get("quote"),
                    "summary": src.get("summary"),
                    "sensitivity_rank": point_rank,
                }
            )

    rows: list[dict[str, Any]] = []
    source_id_to_item_id: dict[str, str] = {}
    for sid in order:
        entry = aggregated[sid]
        payload = {
            "title": entry["title"],
            "source_type": entry["source_type"],
            "url": entry["url"],
            "trust": entry["trust"],
            "usage": entry["usage"],
            "evidence_points": entry["evidence_points"],
        }
        body_text = " ".join(
            filter(
                None,
                [
                    str(p.get("quote") or "") + " " + str(p.get("summary") or "")
                    for p in entry["evidence_points"]
                ],
            )
        )
        source_type = entry["source_type"]
        row = _base_row(
            item_type="source",
            run_id=run_id,
            local_ref=sid,
            project=project,
            title=str(entry["title"]),
            summary=str(source_type) if source_type is not None else None,
            status=None,
            sensitivity_rank=max(run_sensitivity_rank, entry["max_rank"]),
            trust_label=_trust_label_of(entry["trust"]),
            confidence=None,
            source_count=len(entry["citing_claims"]),
            created_at=created_at,
            updated_at=created_at,
            payload=payload,
            extra_search_text=body_text,
        )
        rows.append(row)
        source_id_to_item_id[sid] = row["catalog_item_id"]

    return rows, source_id_to_item_id


def _build_report_row(
    export_data: dict[str, Any],
    run_id: str,
    *,
    project: str | None,
    created_at: str | None,
    sensitivity_rank: int,
    total_sources: int,
) -> dict[str, Any] | None:
    """Build the ``report`` row.

    ``sensitivity_rank`` is the caller-computed ``run_content_max`` (F1) —
    ``max(run sensitivity, every claim's, every source's effective rank)`` —
    not just the run's own label, because ``report_draft`` free text can
    embed content synthesized from any claim/source in the run, regardless of
    whether that claim/source is linked via ``report_locations``.
    """

    report_draft = export_data.get("report_draft")
    if not report_draft:
        return None

    title = export_data.get("title") or run_id
    summary = _first_non_heading_paragraph(report_draft)
    payload = {
        "report_draft": report_draft,
        "writebacks": export_data.get("writebacks"),
        "claim_counts": export_data.get("claim_counts"),
    }
    return _base_row(
        item_type="report",
        run_id=run_id,
        local_ref="report",
        project=project,
        title=str(title),
        summary=summary,
        status=export_data.get("status_derived"),
        sensitivity_rank=sensitivity_rank,
        trust_label=None,
        confidence=None,
        source_count=total_sources,
        created_at=created_at,
        updated_at=created_at,
        payload=payload,
        extra_search_text=report_draft,
    )


def _build_reusable_output_rows(
    export_data: dict[str, Any],
    run_id: str,
    *,
    project: str | None,
    created_at: str | None,
    sensitivity_rank: int,
) -> list[dict[str, Any]]:
    """``reusable_output_candidates[]`` → ``reusable_output`` (plan row 5).

    ``sensitivity_rank`` is the caller-computed ``run_content_max`` (F1) — see
    :func:`_build_report_row`'s docstring; reusable outputs can likewise be
    derived from any claim/source in the run, not only ones they cite.

    NOTE (documented deviation): the current ``export_run()`` implementation
    (schema 1.3) never emits a ``reusable_output_candidates`` key — the field
    exists only in the frontend's TypeScript export type and is produced by a
    *different*, per-run writeback artifact (``intentree_update.yaml``'s own
    ``reusable_output_candidates: list[str]``), not by the export service.
    This mapper is implemented against the plan's literal shape (a list of
    ``{description, is_skillbom_candidate?, source_run_id?}`` dicts) so it is
    ready the moment a future export-schema revision threads the field
    through; today it is always a no-op (``export_data.get(...)`` returns
    ``None``) and produces zero ``reusable_output`` items. See the service's
    module docstring / delivery report for the full rationale.
    """

    candidates = export_data.get("reusable_output_candidates") or []
    rows: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates):
        if isinstance(candidate, dict):
            description = str(candidate.get("description") or f"reusable output {idx}")
            payload = dict(candidate)
        else:
            description = str(candidate)
            payload = {"description": description}
        row = _base_row(
            item_type="reusable_output",
            run_id=run_id,
            local_ref=f"ro_{idx}",
            project=project,
            title=_truncate(description, 160),
            summary=description,
            status=None,
            sensitivity_rank=sensitivity_rank,
            trust_label=None,
            confidence=None,
            source_count=0,
            created_at=created_at,
            updated_at=created_at,
            payload=payload,
        )
        rows.append(row)
    return rows


def _build_writeback_rows(
    export_data: dict[str, Any],
    run_id: str,
    *,
    project: str | None,
    created_at: str | None,
    run_sensitivity_rank: int,
) -> list[dict[str, Any]]:
    writebacks = export_data.get("writebacks") or {}
    targets = writebacks.get("targets") or []
    rows: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        name = str(target.get("target") or "unknown")
        status = _normalize_writeback_status(target.get("status"))
        row = _base_row(
            item_type="writeback",
            run_id=run_id,
            local_ref=f"wb_{name}",
            project=project,
            title=f"{name} writeback",
            summary=target.get("url"),
            status=status,
            sensitivity_rank=run_sensitivity_rank,
            trust_label=None,
            confidence=None,
            source_count=0,
            created_at=created_at,
            updated_at=created_at,
            payload=dict(target),
        )
        rows.append(row)
    return rows


def _build_links(
    *,
    claim_id_to_item_id: dict[str, str],
    source_id_to_item_id: dict[str, str],
    export_data: dict[str, Any],
    report_row: dict[str, Any] | None,
    report_anchors: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Build catalog link rows from a run's export data.

    report→claim ("contains") links are now sourced from ``report_anchors``
    (P2 Wave B / D4 parity): iterate every anchor block's ``claim_links``,
    skip entries with ``link_status="missing_claim"``, resolve each
    ``claim_id`` to its catalog item id, dedup by (from_id, to_id, relation).
    Pre-1.4 exports (``report_anchors`` absent/null) produce no report→claim
    links (graceful degradation — old behavior was report_locations which
    those exports also lack when the report hasn't been re-exported).
    """
    links: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(from_id: str | None, to_id: str | None, relation: str) -> None:
        if not from_id or not to_id:
            return
        key = (from_id, to_id, relation)
        if key in seen:
            return
        seen.add(key)
        links.append({"from_item_id": from_id, "to_item_id": to_id, "relation": relation})

    # claim/inference -> source ("supports", plan-fixed relation label).
    for claim in export_data.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id") or "")
        from_id = claim_id_to_item_id.get(claim_id)
        for src in claim.get("sources") or []:
            if not isinstance(src, dict) or not src.get("resolved") or src.get("dangling"):
                continue
            to_id = source_id_to_item_id.get(str(src.get("source_card_id") or ""))
            _add(from_id, to_id, "supports")

        # inference -> claim ("inferred_from")
        basis = claim.get("inference_basis") or {}
        if basis.get("from_claims"):
            for src_claim_id in basis["from_claims"]:
                _add(
                    claim_id_to_item_id.get(claim_id),
                    claim_id_to_item_id.get(str(src_claim_id)),
                    "inferred_from",
                )

    # report -> claim ("contains"), sourced from report_anchors claim_links (D4 parity).
    # Pre-1.4 exports have report_anchors=None → no links (graceful degradation).
    if report_row is not None and report_anchors is not None:
        report_id = report_row["catalog_item_id"]
        for block in report_anchors:
            if not isinstance(block, dict):
                continue
            for cl in block.get("claim_links") or []:
                if not isinstance(cl, dict):
                    continue
                if cl.get("link_status") == "missing_claim":
                    continue
                claim_id = str(cl.get("claim_id") or "")
                _add(report_id, claim_id_to_item_id.get(claim_id), "contains")

    return links


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def _build_catalog_rows(
    paths: FoundryPaths, run_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Build every catalog row + link row for a single run.

    Fetches ``export_run()`` at ``client_sensitive`` (max permissive) once,
    per D2, and reuses it as the loosest probe in :func:`_probe_citation_ranks`.
    """

    export_data = export_run(paths, run_id, sensitivity_threshold="client_sensitive")
    project = _project_of(export_data)
    created_at = export_data.get("created_at")
    run_sensitivity_rank = _rank(export_data.get("sensitivity"))

    citation_ranks = _probe_citation_ranks(paths, run_id, permissive_export=export_data)

    claim_rows, claim_id_to_item_id, report_claim_ids = _build_claim_and_inference_rows(
        export_data,
        run_id,
        project=project,
        created_at=created_at,
        run_sensitivity_rank=run_sensitivity_rank,
        citation_ranks=citation_ranks,
    )
    source_rows, source_id_to_item_id = _build_source_rows(
        export_data,
        run_id,
        project=project,
        created_at=created_at,
        run_sensitivity_rank=run_sensitivity_rank,
        citation_ranks=citation_ranks,
    )

    # F1: report_draft (and any future reusable-output derivation) can embed
    # content synthesized from ANY claim/source in the run — not just ones
    # linked via report_locations — so both item types must be gated by the
    # strictest sensitivity anywhere in the run, not merely the run's own
    # label. Each row's sensitivity_rank already folds in the run floor (see
    # _build_claim_and_inference_rows / _build_source_rows), and an unknown
    # label (rank _UNKNOWN_RANK) naturally wins the max, keeping this
    # fail-closed.
    run_content_max = max(
        [run_sensitivity_rank]
        + [row["sensitivity_rank"] for row in claim_rows]
        + [row["sensitivity_rank"] for row in source_rows]
    )

    report_row = _build_report_row(
        export_data,
        run_id,
        project=project,
        created_at=created_at,
        sensitivity_rank=run_content_max,
        total_sources=len(source_rows),
    )
    reusable_output_rows = _build_reusable_output_rows(
        export_data,
        run_id,
        project=project,
        created_at=created_at,
        sensitivity_rank=run_content_max,
    )
    writeback_rows = _build_writeback_rows(
        export_data,
        run_id,
        project=project,
        created_at=created_at,
        run_sensitivity_rank=run_sensitivity_rank,
    )

    # report_anchors from export_data (schema 1.4 / P2 Wave A). None on pre-1.4 exports
    # (key absent) or when report_draft is null. _build_links handles both gracefully.
    report_anchors: list[dict[str, Any]] | None = export_data.get("report_anchors")

    links = _build_links(
        claim_id_to_item_id=claim_id_to_item_id,
        source_id_to_item_id=source_id_to_item_id,
        export_data=export_data,
        report_row=report_row,
        report_anchors=report_anchors,
    )

    rows: list[dict[str, Any]] = [*claim_rows, *source_rows]
    if report_row is not None:
        rows.append(report_row)
    rows.extend(reusable_output_rows)
    rows.extend(writeback_rows)
    return rows, links


def _delete_run(conn: sqlite3.Connection, run_id: str) -> None:
    if _fts_available(conn):
        conn.execute(
            "DELETE FROM catalog_fts WHERE catalog_item_id IN "
            "(SELECT catalog_item_id FROM catalog_items WHERE run_id = ?)",
            (run_id,),
        )
    conn.execute("DELETE FROM catalog_links WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM catalog_items WHERE run_id = ?", (run_id,))


def _insert_rows(
    conn: sqlite3.Connection, rows: list[dict[str, Any]], links: list[dict[str, str]], run_id: str
) -> None:
    fts_on = _fts_available(conn)
    for row in rows:
        conn.execute(
            """
            INSERT INTO catalog_items (
                catalog_item_id, item_type, run_id, local_ref, project, title,
                summary, status, sensitivity, sensitivity_rank, trust_label,
                confidence, confidence_rank, source_count, created_at,
                updated_at, payload_json, search_text
            ) VALUES (
                :catalog_item_id, :item_type, :run_id, :local_ref, :project, :title,
                :summary, :status, :sensitivity, :sensitivity_rank, :trust_label,
                :confidence, :confidence_rank, :source_count, :created_at,
                :updated_at, :payload_json, :search_text
            )
            """,
            row,
        )
        if fts_on:
            conn.execute(
                "INSERT INTO catalog_fts (catalog_item_id, title, summary, body) "
                "VALUES (?, ?, ?, ?)",
                (row["catalog_item_id"], row["title"], row["summary"] or "", row["search_text"]),
            )
    for link in links:
        conn.execute(
            "INSERT OR IGNORE INTO catalog_links (run_id, from_item_id, to_item_id, relation) "
            "VALUES (?, ?, ?, ?)",
            (run_id, link["from_item_id"], link["to_item_id"], link["relation"]),
        )
    conn.execute(
        "INSERT INTO catalog_import_log (run_id, imported_at, item_count) VALUES (?, ?, ?) "
        "ON CONFLICT(run_id) DO UPDATE SET imported_at = excluded.imported_at, "
        "item_count = excluded.item_count",
        (run_id, now_iso(), len(rows)),
    )


def import_run(paths: FoundryPaths, run_id: str) -> dict[str, Any]:
    """Import (or re-import) a single run into the catalog.

    Delete-then-insert in one transaction (idempotent). Raises
    :class:`CatalogError` (an :class:`~research_foundry.errors.RFError`
    subclass) when the run cannot be exported.
    """

    try:
        rows, links = _build_catalog_rows(paths, run_id)
    except ExportError as exc:
        raise CatalogError(
            str(exc), run_id=run_id, artifact_path=exc.artifact_path
        ) from exc

    with _db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _delete_run(conn, run_id)
            _insert_rows(conn, rows, links, run_id)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    return {"run_id": run_id, "items": len(rows)}


def import_all(paths: FoundryPaths) -> dict[str, Any]:
    """Import every discovered run (reuses :func:`export_service.list_runs` for
    discovery). Best-effort: a malformed run is skipped, not fatal.
    """

    from .export_service import list_runs

    runs_imported = 0
    items_imported = 0
    errors: list[dict[str, str]] = []
    for summary in list_runs(paths):
        run_id = summary["run_id"]
        try:
            result = import_run(paths, run_id)
        except CatalogError as exc:
            errors.append({"run_id": run_id, "error": str(exc)})
            continue
        runs_imported += 1
        items_imported += result["items"]

    return {"runs": runs_imported, "items": items_imported, "errors": errors}


def rebuild(paths: FoundryPaths) -> dict[str, Any]:
    """Drop + recreate the schema, re-import every run, and reindex every
    on-disk Report Builder draft.

    R2 fix: ``catalog_report_drafts`` is derived exactly like ``catalog_items``
    (module docstring, v2/landmine #3) — a schema-version bump or explicit
    ``rf catalog rebuild`` must repopulate BOTH tables, not just the run-item
    one. :func:`~research_foundry.services.builder_service.reindex_all_drafts`
    existed since Wave D but was never called from here, so the draft index
    stayed empty until a draft was individually mutated. Imported locally
    (not at module scope) because ``builder_service`` imports this module —
    a top-level import here would be circular.
    """

    from .builder_service import reindex_all_drafts

    rebuild_schema(paths)
    result = import_all(paths)
    draft_result = reindex_all_drafts(paths)
    result["drafts"] = draft_result["drafts"]
    result["draft_errors"] = draft_result["errors"]
    return result


# ---------------------------------------------------------------------------
# Read: search / get_item / stats
# ---------------------------------------------------------------------------


def _redact_evidence_points(
    payload: dict[str, Any], threshold_rank: int
) -> dict[str, Any]:
    """Return a copy of a ``source`` item's payload with over-threshold points redacted."""

    points = payload.get("evidence_points")
    if not isinstance(points, list):
        return payload
    redacted_points = []
    for point in points:
        if not isinstance(point, dict):
            redacted_points.append(point)
            continue
        point_rank = point.get("sensitivity_rank", _UNKNOWN_RANK)
        if isinstance(point_rank, int) and point_rank > threshold_rank:
            new_point = {**point, "quote": REDACTION_MARKER, "summary": REDACTION_MARKER}
        else:
            new_point = dict(point)
        redacted_points.append(new_point)
    return {**payload, "evidence_points": redacted_points}


_SUMMARY_COLUMNS = (
    "catalog_item_id",
    "item_type",
    "title",
    "summary",
    "run_id",
    "local_ref",
    "project",
    "status",
    "sensitivity",
    "trust_label",
    "confidence",
    "source_count",
    "created_at",
    "updated_at",
)


def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {col: row[col] for col in _SUMMARY_COLUMNS}


def search(
    paths: FoundryPaths,
    *,
    q: str | None = None,
    item_type: str | None = None,
    project: str | None = None,
    status: str | None = None,
    sensitivity: str | None = None,
    run_id: str | None = None,
    sort: str = "updated",
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    sensitivity_threshold: str | None = None,
) -> dict[str, Any]:
    """Search the catalog. Over-threshold items are excluded (fail-closed)."""

    if sort not in _VALID_SORTS:
        sort = "updated"
    page = max(page, 1)
    page_size = max(1, min(page_size, _MAX_PAGE_SIZE))

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))

    where = ["sensitivity_rank <= ?"]
    params: list[Any] = [threshold_rank]
    if item_type:
        where.append("item_type = ?")
        params.append(item_type)
    if project:
        where.append("project = ?")
        params.append(project)
    if status:
        where.append("status = ?")
        params.append(status)
    if sensitivity:
        where.append("sensitivity = ?")
        params.append(sensitivity)
    if run_id:
        where.append("run_id = ?")
        params.append(run_id)

    order_sql = {
        "updated": "updated_at DESC, catalog_item_id ASC",
        "title": "title ASC, catalog_item_id ASC",
        "confidence": "confidence_rank DESC, catalog_item_id ASC",
    }[sort]

    with _db(paths) as conn:
        fts_on = _fts_available(conn)
        match_ids: list[str] | None = None
        if q:
            if not fts_on:
                where.append("search_text LIKE ?")
                params.append(f"%{q.lower()}%")
            else:
                fts_query = _fts_query(q)
                if fts_query is None:
                    # No valid token after sanitization (e.g. a lone quote
                    # mark, or an all-control-character string) — treat as no
                    # query at all rather than execute a degenerate MATCH
                    # that would spuriously return zero rows (F9).
                    pass
                else:
                    try:
                        fts_rows = conn.execute(
                            "SELECT catalog_item_id FROM catalog_fts WHERE catalog_fts MATCH ? "
                            "ORDER BY bm25(catalog_fts)",
                            (fts_query,),
                        ).fetchall()
                        match_ids = [r["catalog_item_id"] for r in fts_rows]
                    except sqlite3.OperationalError:
                        # Defense in depth: any FTS5 syntax edge case we
                        # didn't sanitize away (F9) falls back to the plain
                        # LIKE path instead of a 500.
                        where.append("search_text LIKE ?")
                        params.append(f"%{q.lower()}%")

        # Facets always reflect the full (sensitivity-gated) catalog, not the
        # current filter/query selection — so filter dropdowns stay complete.
        facets = _facets(conn, threshold_rank)

        if match_ids is not None:
            if not match_ids:
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "facets": facets,
                }
            placeholders = ",".join("?" for _ in match_ids)
            where.append(f"catalog_item_id IN ({placeholders})")
            params.extend(match_ids)

        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) FROM catalog_items WHERE {where_sql}", params
        ).fetchone()[0]

        if match_ids is not None:
            # Preserve bm25 rank order for the current page instead of the
            # generic ORDER BY (relevance beats recency when q is present).
            rank_order = {cid: i for i, cid in enumerate(match_ids)}
            all_rows = conn.execute(
                f"SELECT * FROM catalog_items WHERE {where_sql}", params
            ).fetchall()
            all_rows = sorted(all_rows, key=lambda r: rank_order.get(r["catalog_item_id"], 1 << 30))
            page_rows = all_rows[(page - 1) * page_size : (page - 1) * page_size + page_size]
        else:
            offset = (page - 1) * page_size
            page_rows = conn.execute(
                f"SELECT * FROM catalog_items WHERE {where_sql} "
                f"ORDER BY {order_sql} LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            ).fetchall()

    return {
        "items": [_row_to_summary(r) for r in page_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "facets": facets,
    }


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _fts_query(q: str) -> str | None:
    """Build a permissive prefix MATCH query from free text (AND across terms).

    Returns ``None`` when no valid token remains after stripping control
    characters and bare quote marks (e.g. ``'alpha "'`` degenerating to a
    lone empty token) — callers must treat that as "no query" rather than
    execute a MATCH expression, since an empty/degenerate token (``""*``)
    matches nothing and would silently hide otherwise-visible results (F9).
    """

    cleaned_q = _CONTROL_CHARS_RE.sub("", q)
    terms = [t for t in re.split(r"\s+", cleaned_q.strip()) if t]

    def _escape(term: str) -> str | None:
        cleaned = term.replace('"', "").strip()
        if not cleaned:
            return None
        return f'"{cleaned}"*'

    tokens = [tok for tok in (_escape(t) for t in terms) if tok is not None]
    if not tokens:
        return None
    return " AND ".join(tokens)


def _facets(conn: sqlite3.Connection, threshold_rank: int) -> dict[str, list[str]]:
    def _distinct(column: str) -> list[str]:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM catalog_items "
            f"WHERE sensitivity_rank <= ? AND {column} IS NOT NULL "
            f"ORDER BY {column}",
            (threshold_rank,),
        ).fetchall()
        return [r[0] for r in rows]

    return {
        "projects": _distinct("project"),
        "statuses": _distinct("status"),
        "sensitivities": _distinct("sensitivity"),
    }


def get_item(
    paths: FoundryPaths,
    catalog_item_id: str,
    *,
    sensitivity_threshold: str | None = None,
) -> dict[str, Any] | None:
    """Return the full detail for *catalog_item_id*, or ``None`` if unknown or

    excluded by the resolved sensitivity threshold (fail-closed — callers
    should translate ``None`` to a 404, never distinguishing "doesn't exist"
    from "not visible").
    """

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))

    with _db(paths) as conn:
        row = conn.execute(
            "SELECT * FROM catalog_items WHERE catalog_item_id = ?", (catalog_item_id,)
        ).fetchone()
        if row is None or row["sensitivity_rank"] > threshold_rank:
            return None

        payload = json.loads(row["payload_json"])
        if row["item_type"] == "source":
            payload = _redact_evidence_points(payload, threshold_rank)

        # F3: only surface an edge when the *other* endpoint is itself visible
        # at the resolved threshold — otherwise the edge leaks a hidden
        # catalog_item_id (and its relation) even though the requested item
        # is visible. Same rule as search()'s WHERE sensitivity_rank <= ?.
        outgoing = conn.execute(
            """
            SELECT l.to_item_id AS to_item_id, l.relation AS relation
            FROM catalog_links l
            JOIN catalog_items i ON i.catalog_item_id = l.to_item_id
            WHERE l.from_item_id = ? AND i.sensitivity_rank <= ?
            """,
            (catalog_item_id, threshold_rank),
        ).fetchall()
        incoming = conn.execute(
            """
            SELECT l.from_item_id AS from_item_id, l.relation AS relation
            FROM catalog_links l
            JOIN catalog_items i ON i.catalog_item_id = l.from_item_id
            WHERE l.to_item_id = ? AND i.sensitivity_rank <= ?
            """,
            (catalog_item_id, threshold_rank),
        ).fetchall()

    summary = _row_to_summary(row)
    summary["payload"] = payload
    summary["links"] = {
        "outgoing": [{"catalog_item_id": r["to_item_id"], "relation": r["relation"]} for r in outgoing],
        "incoming": [{"catalog_item_id": r["from_item_id"], "relation": r["relation"]} for r in incoming],
    }
    return summary


def stats(paths: FoundryPaths, *, sensitivity_threshold: str | None = None) -> dict[str, Any]:
    """Aggregate counts (visible items only, per the resolved threshold)."""

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))

    with _db(paths) as conn:
        counts = {t: 0 for t in ITEM_TYPES}
        rows = conn.execute(
            "SELECT item_type, COUNT(*) AS n FROM catalog_items "
            "WHERE sensitivity_rank <= ? GROUP BY item_type",
            (threshold_rank,),
        ).fetchall()
        for r in rows:
            if r["item_type"] in counts:
                counts[r["item_type"]] = r["n"]

        # F7: runs_indexed must reflect only runs with >=1 item visible at the
        # resolved threshold — a global COUNT(*) over catalog_import_log would
        # leak the existence of a run that is entirely above threshold (e.g.
        # a whole run tagged client_sensitive, viewed at a public threshold).
        runs_row = conn.execute(
            "SELECT COUNT(DISTINCT run_id) AS n FROM catalog_items WHERE sensitivity_rank <= ?",
            (threshold_rank,),
        ).fetchone()
        runs_indexed = runs_row["n"] if runs_row else 0

        # last_import_at stays global — it is a housekeeping timestamp, not a
        # per-run existence signal.
        log_row = conn.execute(
            "SELECT MAX(imported_at) AS last_import_at FROM catalog_import_log"
        ).fetchone()

    return {
        "counts": counts,
        "runs_indexed": runs_indexed,
        "last_import_at": log_row["last_import_at"] if log_row else None,
    }


# ---------------------------------------------------------------------------
# Report Builder draft index (P3 Wave D — plan D10/D11, landmine #3)
# ---------------------------------------------------------------------------
# This module knows nothing about the draft.yaml file format — callers
# (builder_service) hand it a plain summary dict + a link list, and this
# section only ever upserts/deletes derived rows. The draft.yaml + revision
# files under <workspace>/reports/drafts/ remain the sole source of truth;
# see builder_service's module docstring. A drop+rebuild of this table must
# never touch those files — rebuild-safety is proved by
# builder_service.reindex_all_drafts() re-deriving every row from disk.

_DRAFT_LINK_RUN_PREFIX = "draft:"


def _draft_link_scope(report_draft_id: str) -> str:
    """The ``catalog_links.run_id`` sentinel scoping one draft's link rows.

    ``catalog_links.run_id`` is NOT NULL and doubles as a real run id
    elsewhere; prefixing with ``"draft:"`` (never a valid run id) keeps a
    draft's link rows in their own delete scope without colliding with an
    actual run's rows.
    """

    return f"{_DRAFT_LINK_RUN_PREFIX}{report_draft_id}"


_DRAFT_INDEX_COLUMNS: tuple[str, ...] = (
    "report_draft_id",
    "title",
    "status",
    "sensitivity",
    "sensitivity_rank",
    "audience",
    "origin",
    "project_id",
    "workspace_id",
    "created_by",
    "current_version_id",
    "block_count",
    "claim_link_count",
    "source_link_count",
    "created_at",
    "updated_at",
    "draft_path",
)


def index_draft(
    paths: FoundryPaths,
    entry: dict[str, Any],
    *,
    links: list[dict[str, str]] | None = None,
) -> None:
    """Upsert one report draft's derived index row + ``catalog_links`` (D11).

    ``entry`` must supply ``report_draft_id``, ``title``, ``sensitivity``, and
    ``draft_path``; every other :data:`_DRAFT_INDEX_COLUMNS` key is optional.
    ``links`` are the draft's outgoing edges — ``[{"to_item_id":
    <catalog_item_id>, "relation": "cites"|"derived_from"}, ...]``;
    ``from_item_id`` is always the draft's own ``report_draft_id`` (D11:
    "link drafts to source runs/claims via catalog_links relations").

    Delete-then-insert in one transaction (idempotent) — mirrors
    :func:`import_run`'s contract, so re-indexing after every draft mutation
    is always safe and cheap.
    """

    report_draft_id = str(entry["report_draft_id"])
    sensitivity_rank = _rank(entry.get("sensitivity"))
    row: dict[str, Any] = {col: entry.get(col) for col in _DRAFT_INDEX_COLUMNS}
    row["report_draft_id"] = report_draft_id
    row["title"] = _scalar_text(entry.get("title")) or ""
    row["status"] = _scalar_text(entry.get("status"))
    row["sensitivity"] = _label_for_rank(sensitivity_rank)
    row["sensitivity_rank"] = sensitivity_rank
    row["block_count"] = int(entry.get("block_count") or 0)
    row["claim_link_count"] = int(entry.get("claim_link_count") or 0)
    row["source_link_count"] = int(entry.get("source_link_count") or 0)
    row["draft_path"] = str(entry["draft_path"])
    row["search_text"] = " ".join(
        filter(None, [row["title"], str(entry.get("status") or "")])
    ).lower()

    link_rows = links or []
    scope = _draft_link_scope(report_draft_id)
    columns = [*_DRAFT_INDEX_COLUMNS, "search_text"]

    with _db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "DELETE FROM catalog_report_drafts WHERE report_draft_id = ?",
                (report_draft_id,),
            )
            conn.execute("DELETE FROM catalog_links WHERE run_id = ?", (scope,))
            placeholders = ", ".join(f":{c}" for c in columns)
            conn.execute(
                f"INSERT INTO catalog_report_drafts ({', '.join(columns)}) "
                f"VALUES ({placeholders})",
                row,
            )
            for link in link_rows:
                to_id = link.get("to_item_id")
                relation = link.get("relation")
                if not to_id or not relation:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO catalog_links "
                    "(run_id, from_item_id, to_item_id, relation) VALUES (?, ?, ?, ?)",
                    (scope, report_draft_id, to_id, relation),
                )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


def remove_draft_index(paths: FoundryPaths, report_draft_id: str) -> None:
    """Remove one draft's index row + ``catalog_links`` edges (idempotent)."""

    scope = _draft_link_scope(report_draft_id)
    with _db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "DELETE FROM catalog_report_drafts WHERE report_draft_id = ?",
                (report_draft_id,),
            )
            conn.execute("DELETE FROM catalog_links WHERE run_id = ?", (scope,))
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


def get_draft_index(paths: FoundryPaths, report_draft_id: str) -> dict[str, Any] | None:
    """Return the indexed summary row for *report_draft_id*, or ``None``."""

    with _db(paths) as conn:
        row = conn.execute(
            "SELECT * FROM catalog_report_drafts WHERE report_draft_id = ?",
            (report_draft_id,),
        ).fetchone()
        if row is None:
            return None
        result = {col: row[col] for col in _DRAFT_INDEX_COLUMNS}
        link_rows = conn.execute(
            "SELECT to_item_id, relation FROM catalog_links WHERE from_item_id = ?",
            (report_draft_id,),
        ).fetchall()
    result["links"] = [
        {"catalog_item_id": r["to_item_id"], "relation": r["relation"]} for r in link_rows
    ]
    return result


def list_draft_index(
    paths: FoundryPaths,
    *,
    status: str | None = None,
    sensitivity_threshold: str | None = None,
) -> list[dict[str, Any]]:
    """List indexed draft summaries (fail-closed on the resolved threshold)."""

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))
    where = ["sensitivity_rank <= ?"]
    params: list[Any] = [threshold_rank]
    if status:
        where.append("status = ?")
        params.append(status)
    with _db(paths) as conn:
        rows = conn.execute(
            f"SELECT * FROM catalog_report_drafts WHERE {' AND '.join(where)} "
            "ORDER BY updated_at DESC, report_draft_id ASC",
            params,
        ).fetchall()
    return [{col: r[col] for col in _DRAFT_INDEX_COLUMNS} for r in rows]


__all__ = [
    "SCHEMA_VERSION",
    "ITEM_TYPES",
    "CatalogError",
    "rebuild_schema",
    "import_run",
    "import_all",
    "rebuild",
    "search",
    "get_item",
    "stats",
    "index_draft",
    "remove_draft_index",
    "get_draft_index",
    "list_draft_index",
    "report_item_id",
]
