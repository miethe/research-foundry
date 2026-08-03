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
import logging
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..api.auth.provider import AuthIdentity
from ..api.auth.scope import require_workspace_scope, resolve_workspace_isolation_active
from ..ids import now_iso
from ..paths import FoundryPaths
from . import audit_service
from .attribution_triage import _merge_attribution_summaries
from .audit_service import AuditEvent
from .export_service import (
    REDACTION_MARKER,
    SENSITIVITY_ORDER,
    ExportError,
    export_run,
    resolve_threshold,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WKSP-304 Phase 3: query-layer workspace_id scoping (flag-gated, inert by
# default — decision D4)
# ---------------------------------------------------------------------------
#
# Every read function below accepts an optional ``identity: AuthIdentity |
# None = None`` parameter. When ``identity is None`` (the byte-identical
# default — no caller passes one yet; Phase 2 routers extract identity but do
# not thread it into service calls until a later phase), every query below is
# unchanged from its pre-WKSP-304 shape. When ``identity`` is supplied AND
# :func:`_isolation_active` resolves ``True``, an ``AND workspace_id = ?``
# predicate (parameterized — never string-interpolated) is added to the
# affected query. This module never reimplements the enforcement truth
# table — it always defers to
# :meth:`~research_foundry.config.FoundryConfig.resolve_workspace_isolation_enforced`
# (Phase 1, TASK-1.2).


def _isolation_active(paths: FoundryPaths) -> bool:
    """Resolve whether WKSP-304 workspace isolation is actively enforced.

    WKSP-304 Phase 4 (TASK-4.2 consolidation): delegates to the single
    shared implementation in
    :func:`research_foundry.api.auth.scope.resolve_workspace_isolation_active`
    — Phase 3 duplicated this helper identically into this module,
    ``builder_service.py``, and ``AgentJobService`` as a deliberate
    single-owner-phase choice (see phase-3-query-layer-scoping.md "why
    single-owner"); this module-level name/call sites are kept unchanged so
    no caller here needs to change. Pure refactor, no behaviour change.
    """

    return resolve_workspace_isolation_active(paths)

# --- schema versioning (D1) --------------------------------------------------
# v2 (public-multiuser-release P3 Wave D, plan D10/D11/landmine #3): adds the
# catalog_report_drafts derived index table. A version bump means ANY
# mismatch drops and recreates the whole schema (see _ensure_schema) — this is
# always safe because catalog.db is 100% derived: run items are rebuilt from
# export_run() via import_all(), and draft index rows are rebuilt from
# on-disk draft.yaml files via builder_service.reindex_all_drafts(). Neither
# rebuild path reads anything from the DB itself.
# v4 (claim-term-indexing v1, TASK-2.3/D3): adds the catalog_terms derived
# index table. Rows are rebuilt from each claim/inference item's own
# `_term_index` block during import_run()/rebuild() — never a separate read
# path, so a version bump is safe by the same "100% derived" argument above.
# v5 (source-metadata-propagation-v1 M4, SMP-4.2/4.3): adds first-party
# provider metadata columns (`doi`, `publisher`, `source_version`,
# `authors_json`) plus a queryable projection of the M2 attribution mirror
# (`source_rank`, `attribution_count`) to `catalog_items`. Rows are rebuilt
# from export_run()'s resolved-source shape via `_build_source_rows()` during
# import_run()/rebuild() — never a separate read path, so a version bump is
# safe by the same "100% derived" argument above. `attribution_count` is
# nullable BY DESIGN: NULL means "not yet assessed" (no `attribution_summary`
# mirror present on the card), 0 means "assessed, none found" — collapsing
# that distinction would recreate the no-backfill result-set bias the tri-
# state coverage surface (SMP-4.5) exists to close. `source_rank` is the raw
# `trust.source_rank` value (`primary`/`secondary`/`tertiary`/`unknown`),
# deliberately distinct from the pre-existing `trust_label` column (which
# falls back to an arbitrary string cast for legacy non-dict `trust` values
# and is therefore not safe to treat as a rank).
SCHEMA_VERSION = 5

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


class CatalogUnavailable(CatalogError):
    """The derived ``catalog.db`` cannot be queried without performing a write.

    Raised by :func:`query_only_connection` / :func:`is_catalog_available`
    (KMCP-2.2) when ``catalog.db`` is absent, a symlink, unreadable, or was
    created by a different :data:`SCHEMA_VERSION` than this build expects.
    This is the RF Knowledge MCP's invariant-2 ("reads never repair state")
    boundary — read-only callers (the P2/P3 Knowledge service) must treat
    this identically to "no matches" and MUST NOT fall back to
    :func:`_connect`/:func:`rebuild_schema`/:func:`import_all` to repair it;
    only an explicit ``rf catalog rebuild`` (an unchanged, deliberate write
    path) may do that. Distinct from :class:`CatalogError` (a malformed run
    export) so callers can tell "nothing built yet" apart from "a specific
    run failed to export".
    """

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


# ---------------------------------------------------------------------------
# Connection + schema management
# ---------------------------------------------------------------------------

_DDL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS catalog_items (
        catalog_item_id   TEXT PRIMARY KEY,
        item_type         TEXT NOT NULL,
        run_id            TEXT NOT NULL,
        workspace_id      TEXT NOT NULL DEFAULT 'default',
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
        search_text       TEXT NOT NULL,
        doi               TEXT,
        publisher         TEXT,
        source_version    TEXT,
        authors_json      TEXT,
        source_rank       TEXT,
        attribution_count INTEGER
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_run ON catalog_items(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_type ON catalog_items(item_type)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_project ON catalog_items(project)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_sensitivity_rank "
    "ON catalog_items(sensitivity_rank)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_items_workspace "
    "ON catalog_items(workspace_id)",
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
    # --- catalog_terms (v4, claim-term-indexing v1 TASK-2.3, decision D3) ---
    # Mirrors catalog_links's join-table shape. Each row is a single
    # (catalog_item_id, term) hit derived from THAT item's own `_term_index`
    # block, carrying THAT item's own already-computed effective
    # sensitivity_rank (see _build_claim_and_inference_rows) — never a single
    # flat value computed once at the run's max-permissive tier, which would
    # repeat the search_text flat-blob leak this table's design is written to
    # avoid (see module docstring + _redact_evidence_points). Read-time
    # filtering (a future task) must apply the same
    # `sensitivity_rank <= threshold_rank` predicate used by catalog_items.
    """
    CREATE TABLE IF NOT EXISTS catalog_terms (
        catalog_item_id   TEXT NOT NULL,
        term              TEXT NOT NULL,
        role              TEXT NOT NULL,
        run_id            TEXT NOT NULL,
        sensitivity_rank  INTEGER NOT NULL,
        PRIMARY KEY (catalog_item_id, term)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalog_terms_run ON catalog_terms(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_terms_term ON catalog_terms(term)",
    "CREATE INDEX IF NOT EXISTS idx_catalog_terms_sensitivity_rank "
    "ON catalog_terms(sensitivity_rank)",
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
    "DROP TABLE IF EXISTS catalog_terms",
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
# Query-only / read-only seam (RF Knowledge MCP KMCP-2.2)
# ---------------------------------------------------------------------------
# Additive only — every function above (``_connect``/``_db`` and everything
# built on them: ``search``, ``get_item``, ``stats``, ``import_run``,
# ``rebuild``, ``index_draft``, ...) is completely unchanged and keeps its
# own lazy-create/migrate behavior for every existing caller (``rf catalog
# ...``, the API routers, etc.). The functions below are a NEW, read-only
# path for callers (the P2/P3 Knowledge service) that must never create,
# migrate, or rebuild ``catalog.db`` as a side effect of a read.


def _catalog_db_readable(paths: FoundryPaths) -> Path | None:
    """Return ``catalog.db``'s path iff it exists as a plain, non-symlink file.

    Never creates the parent directory or the file itself (contrast
    :func:`_connect`, which does both unconditionally). Symlinks are
    rejected outright (same "no symlink escape" defense used elsewhere in
    this codebase, e.g. ``assertion_catalog``'s ``_build_records``) so a
    read-only caller can never be pointed at an arbitrary file outside the
    workspace.
    """

    db_path = paths.catalog_db
    if db_path.is_symlink() or not db_path.is_file():
        return None
    return db_path


@contextmanager
def query_only_connection(paths: FoundryPaths) -> Iterator[sqlite3.Connection]:
    """Open ``catalog.db`` in explicit read-only mode; never create/migrate/rebuild it.

    KMCP invariant 2 ("reads never repair state"): raises
    :class:`CatalogUnavailable` — rather than lazily creating the DB the way
    every existing write-capable caller's :func:`_connect` does — when the
    file is missing, a symlink, unreadable, or its ``PRAGMA user_version``
    does not match :data:`SCHEMA_VERSION` (a stale or mid-migration DB is
    treated as unavailable, never auto-migrated by a read).

    The connection is opened via the sqlite3 URI ``mode=ro`` (an OS/VFS-level
    write rejection) plus ``PRAGMA query_only = ON`` as defense in depth. It
    never calls :func:`_ensure_schema`, :func:`_create_schema`, or any other
    DDL/DML statement — SELECT only. This is a NEW, additive seam; every
    existing caller keeps using :func:`_connect`/:func:`_db` unchanged.
    """

    db_path = _catalog_db_readable(paths)
    if db_path is None:
        raise CatalogUnavailable("catalog_missing")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as exc:
        raise CatalogUnavailable("catalog_unreadable") from exc
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        try:
            (version,) = conn.execute("PRAGMA user_version").fetchone()
        except sqlite3.DatabaseError as exc:
            raise CatalogUnavailable("catalog_unreadable") from exc
        if version != SCHEMA_VERSION:
            raise CatalogUnavailable("catalog_schema_stale")
        yield conn
    finally:
        conn.close()


def is_catalog_available(paths: FoundryPaths) -> bool:
    """Cheap availability probe — ``True`` iff :func:`query_only_connection` would succeed.

    Never creates, migrates, or writes anything. Safe to call before every
    Knowledge read to decide whether a catalog-backed kind is queryable at
    all before delegating to a P3 projection.
    """

    try:
        with query_only_connection(paths):
            return True
    except CatalogUnavailable:
        return False


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


def _source_rank_of(trust: Any) -> str | None:
    """Extract ``trust.source_rank`` as a scalar column value, EXCLUDING the
    legacy string-cast fallback :func:`_trust_label_of` applies.

    ``trust.source_rank`` (M1 / :func:`~research_foundry.services.source_rank.
    derive_source_rank`) is one of a closed set (``primary``/``secondary``/
    ``tertiary``/``unknown``). A plain-string ``trust`` value (pre-M1 or
    synthetic data) carries no such rank — :func:`_trust_label_of` treats
    that string itself as the label, which is fine for display but would be
    wrong to hand to a caller expecting one of the four rank values. This
    helper returns ``None`` in that case instead of the arbitrary string, so
    the tri-state coverage query surface (SMP-4.5) never mistakes free text
    for a rank.
    """

    if isinstance(trust, dict):
        rank = trust.get("source_rank")
        return str(rank) if rank is not None else None
    return None


def _attribution_count_of(attribution_summary: Any) -> int | None:
    """Coerce a card's ``attribution_summary`` mirror to a nullable count.

    ``None`` — whether the key is absent, explicitly ``null``, or the value
    is malformed/non-dict — means "not yet assessed". ``0`` means "assessed;
    zero authoritative ``source_attribution`` records reduced into this
    mirror". Collapsing these two into one value would recreate the
    no-backfill result-set bias (plan named risk) the tri-state coverage
    surface exists to close; SMP-4.5 builds the query surface on top of this
    distinction, not here — this function only preserves it at row-build
    time.
    """

    if not isinstance(attribution_summary, dict):
        return None
    count = attribution_summary.get("count")
    return count if isinstance(count, int) else None


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
    doi: str | None = None,
    publisher: str | None = None,
    source_version: str | None = None,
    authors: Any = None,
    source_rank: str | None = None,
    attribution_count: int | None = None,
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
    # SMP-4.2/4.3: first-party provider metadata (M1) + a queryable
    # projection of the M2 attribution mirror. `doi`/`publisher`/
    # `source_version`/`authors`/`source_rank` are only meaningful for
    # ``item_type == "source"`` and only `_build_source_rows()` supplies
    # them — every other caller keeps its pre-M4 byte-identical row shape
    # via these defaults. `attribution_count` is the one exception (SMP-4.4
    # Part 2): `_build_claim_and_inference_rows()` also supplies it, from
    # its own cross-source merge across a claim's cited sources — a claim
    # can be meaningfully "assessed"/"not yet assessed" too, not just a
    # source. `_scalar_text` is the same last-line-of-defense coercion used
    # for `trust_label` above; it also JSON-encodes `authors` (a list) into
    # a bindable string.
    doi = _scalar_text(doi)
    publisher = _scalar_text(publisher)
    source_version = _scalar_text(source_version)
    authors_json = _scalar_text(authors)
    source_rank = _scalar_text(source_rank)
    search_text = " ".join(
        filter(None, [title, summary or "", extra_search_text])
    ).lower()
    return {
        "catalog_item_id": catalog_item_id,
        "item_type": item_type,
        "run_id": run_id,
        "workspace_id": "default",  # WKSP-303: all CLI/CLI-run imports land in "default"
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
        "doi": doi,
        "publisher": publisher,
        "source_version": source_version,
        "authors_json": authors_json,
        "source_rank": source_rank,
        "attribution_count": attribution_count,
    }


def _build_term_rows(
    term_index: Any, *, catalog_item_id: str, run_id: str, sensitivity_rank: int
) -> list[dict[str, Any]]:
    """Build ``catalog_terms`` rows for one claim/inference item's `_term_index`.

    D3: every row carries *this item's own* already-computed effective
    ``sensitivity_rank`` (the same value used for the item's own
    ``catalog_items`` row) — never a run-wide or max-permissive constant.
    Absent, malformed, or empty `_term_index` (no vocabulary hits, no
    vocabulary loaded, or pre-backfill legacy claim — see term_index.py's
    module docstring) yields ``[]``, never a placeholder row.
    """

    if not isinstance(term_index, dict):
        return []
    terms = term_index.get("terms")
    usage_roles = term_index.get("usage_roles")
    if not isinstance(terms, list) or not isinstance(usage_roles, dict):
        return []

    rows: list[dict[str, Any]] = []
    for term in terms:
        if not isinstance(term, str) or not term:
            continue
        role = usage_roles.get(term)
        if not isinstance(role, str) or not role:
            # Defensive only (D8: non-authoritative) — build_term_index()
            # always populates a role for every term it emits; a term
            # missing its role here signals corrupted upstream data, not a
            # governance/sensitivity gap, so it is simply skipped rather
            # than defaulted to an invented label.
            continue
        rows.append(
            {
                "catalog_item_id": catalog_item_id,
                "term": term,
                "role": role,
                "run_id": run_id,
                "sensitivity_rank": sensitivity_rank,
            }
        )
    return rows


def _build_claim_and_inference_rows(
    export_data: dict[str, Any],
    run_id: str,
    *,
    project: str | None,
    created_at: str | None,
    run_sensitivity_rank: int,
    citation_ranks: dict[_CitationKey, int],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str], list[dict[str, Any]]]:
    """Build claim/inference rows.

    Returns ``(rows, claim_id_to_item_id, report_claim_ids, term_rows)`` —
    ``report_claim_ids`` lists every claim/inference ``claim_id`` with a
    non-empty ``report_locations``, for the ``report -> claim`` ("contains")
    links; ``term_rows`` are the ``catalog_terms`` rows derived from each
    claim's own `_term_index` block (D3 — see :func:`_build_term_rows`).
    """

    rows: list[dict[str, Any]] = []
    claim_id_to_item_id: dict[str, str] = {}
    report_claim_ids: list[str] = []
    term_rows: list[dict[str, Any]] = []

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

        # SMP-4.4 Part 2: a claim may cite several distinct source_card_ids,
        # each carrying its own (still per-card) attribution_summary mirror.
        # Merge them into one cross-source view via _merge_attribution_
        # summaries — the "cross-source values propagate as set-union keyed
        # by (asserter_id, assertion_kind)" plan decision, applied at the
        # claim rather than the source-row level.
        #
        # Phase C: pass (source_card_id, attribution_summary) PAIRS, not bare
        # summaries. `resolved_sources` can (and, for the ordinary "one card
        # cited via several evidence anchors" case, does) contain multiple
        # entries for the SAME source_card_id — `distinct_source_ids` three
        # lines above exists precisely because of that. The merge function
        # dedupes by source_card_id internally so sources_assessed/
        # sources_total count DISTINCT sources, never input positions.
        claim_attribution_summary = _merge_attribution_summaries(
            (s.get("source_card_id"), s.get("attribution_summary")) for s in resolved_sources
        )

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
            # SMP-4.4 Part 2: value-free, cross-source rollup across every
            # source this claim cites. Never recomputed from raw records at
            # this layer — merged purely from the per-source mirrors, per
            # attribution_triage._merge_attribution_summaries's own
            # docstring (relocated there per the duplicate-rollup-owner
            # cleanup).
            "attribution_summary": claim_attribution_summary,
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
            attribution_count=_attribution_count_of(claim_attribution_summary),
        )
        rows.append(row)
        claim_id_to_item_id[claim_id] = row["catalog_item_id"]
        if claim.get("report_locations"):
            report_claim_ids.append(claim_id)
        term_rows.extend(
            _build_term_rows(
                claim.get("_term_index"),
                catalog_item_id=row["catalog_item_id"],
                run_id=run_id,
                sensitivity_rank=item_sensitivity_rank,
            )
        )

    return rows, claim_id_to_item_id, report_claim_ids, term_rows


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
                    # SMP-4.2: M1 first-party provider metadata + the M2
                    # attribution mirror. First-citation-wins, same as
                    # title/url/trust/usage above — every citation of one
                    # `source_card_id` should describe the SAME card, and
                    # import always runs at the max-permissive
                    # `client_sensitive` threshold (module docstring), so
                    # these are never `REDACTION_MARKER` at import time.
                    # `attribution_summary` is read defensively (`.get()`,
                    # never a raw file read) — this module's hard invariant
                    # is "import via export_run() live"; if the export layer
                    # has not yet been widened to carry this key, it is
                    # simply absent (`None`), which is the correct
                    # "not yet assessed" state, not an error.
                    "authors": src.get("authors"),
                    "doi": src.get("doi"),
                    "publisher": src.get("publisher"),
                    "version": src.get("version"),
                    "attribution_summary": src.get("attribution_summary"),
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
            "authors": entry["authors"],
            "doi": entry["doi"],
            "publisher": entry["publisher"],
            "version": entry["version"],
            "trust": entry["trust"],
            "usage": entry["usage"],
            # Value-free mirror, propagated verbatim — never recomputed or
            # widened here (SMP-4.4/4.5 own the rollup computation and the
            # tri-state query surface respectively; this row builder only
            # carries whatever the card/export layer already produced).
            "attribution_summary": entry["attribution_summary"],
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
            doi=entry["doi"],
            publisher=entry["publisher"],
            source_version=entry["version"],
            authors=entry["authors"],
            source_rank=_source_rank_of(entry["trust"]),
            attribution_count=_attribution_count_of(entry["attribution_summary"]),
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
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    """Build every catalog row + link row + term row for a single run.

    Fetches ``export_run()`` at ``client_sensitive`` (max permissive) once,
    per D2, and reuses it as the loosest probe in :func:`_probe_citation_ranks`.
    """

    export_data = export_run(paths, run_id, sensitivity_threshold="client_sensitive")
    project = _project_of(export_data)
    created_at = export_data.get("created_at")
    run_sensitivity_rank = _rank(export_data.get("sensitivity"))

    citation_ranks = _probe_citation_ranks(paths, run_id, permissive_export=export_data)

    claim_rows, claim_id_to_item_id, report_claim_ids, term_rows = _build_claim_and_inference_rows(
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
    return rows, links, term_rows


def _delete_run(conn: sqlite3.Connection, run_id: str) -> None:
    if _fts_available(conn):
        conn.execute(
            "DELETE FROM catalog_fts WHERE catalog_item_id IN "
            "(SELECT catalog_item_id FROM catalog_items WHERE run_id = ?)",
            (run_id,),
        )
    conn.execute("DELETE FROM catalog_links WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM catalog_terms WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM catalog_items WHERE run_id = ?", (run_id,))


def _insert_rows(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
    links: list[dict[str, str]],
    run_id: str,
    term_rows: list[dict[str, Any]] | None = None,
) -> None:
    fts_on = _fts_available(conn)
    term_rows = term_rows or []
    for row in rows:
        conn.execute(
            """
            INSERT INTO catalog_items (
                catalog_item_id, item_type, run_id, workspace_id, local_ref, project, title,
                summary, status, sensitivity, sensitivity_rank, trust_label,
                confidence, confidence_rank, source_count, created_at,
                updated_at, payload_json, search_text,
                doi, publisher, source_version, authors_json, source_rank, attribution_count
            ) VALUES (
                :catalog_item_id, :item_type, :run_id, :workspace_id, :local_ref, :project, :title,
                :summary, :status, :sensitivity, :sensitivity_rank, :trust_label,
                :confidence, :confidence_rank, :source_count, :created_at,
                :updated_at, :payload_json, :search_text,
                :doi, :publisher, :source_version, :authors_json, :source_rank, :attribution_count
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
    for term_row in term_rows:
        conn.execute(
            "INSERT OR IGNORE INTO catalog_terms "
            "(catalog_item_id, term, role, run_id, sensitivity_rank) "
            "VALUES (:catalog_item_id, :term, :role, :run_id, :sensitivity_rank)",
            term_row,
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
        rows, links, term_rows = _build_catalog_rows(paths, run_id)
    except ExportError as exc:
        raise CatalogError(
            str(exc), run_id=run_id, artifact_path=exc.artifact_path
        ) from exc

    with _db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _delete_run(conn, run_id)
            _insert_rows(conn, rows, links, run_id, term_rows)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    # Audit: record catalog mutation after the transaction commits (fail-open).
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="catalog_mutation",
            action="import_run",
            target_ref=run_id,
            result="success",
        ),
    )

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
    # SMP-4.2 (M4 coupling note): `source_rank` and `attribution_count` are
    # the two SCALAR new attributes — the tri-state coverage query surface
    # (SMP-4.5) needs both visible in list results, not just item detail, to
    # render a coverage indicator per search row. `doi`/`publisher`/
    # `source_version`/`authors_json` stay detail-only (same precedent as
    # the pre-existing `url`/`trust`/`usage`, which are payload-only and not
    # in this tuple) — RETRACTED claim (see execution ledger): `get_item()`
    # does NOT return every column via `dict(row)`. Its returned `summary`
    # goes through this same `_row_to_summary()`/`_SUMMARY_COLUMNS` gate;
    # `dict(row)` is used internally only for the `require_workspace_scope`
    # comparison, never returned to the caller. Any column absent from this
    # tuple and absent from `payload_json` is invisible to both `search()`
    # and `get_item()` alike.
    "source_rank",
    "attribution_count",
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
    term: list[str] | None = None,
    role: list[str] | None = None,
    sort: str = "updated",
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    sensitivity_threshold: str | None = None,
    identity: AuthIdentity | None = None,
) -> dict[str, Any]:
    """Search the catalog. Over-threshold items are excluded (fail-closed).

    ``identity`` is WKSP-304 Phase 3 query-layer scoping (see module docstring
    section above): ``None`` (the default) is byte-identical to the
    pre-WKSP-304 query; supplied + isolation active adds a parameterized
    ``AND workspace_id = ?`` predicate to every statement this function runs,
    including the facet query.

    ``term``/``role`` are the claim-term-indexing v1 facets (TASK-2.5, OQ-C):
    repeatable — OR semantics within repeats of the *same* flag (``term=["cbc",
    "hgb"]`` matches either), AND semantics against every other filter
    including each other. Each is enforced via an ``EXISTS`` against
    ``catalog_terms`` that also re-checks ``sensitivity_rank <= threshold_rank``
    (D3) — a term/role row above the caller's threshold can never be used to
    match an item, even one that is itself visible, closing the same
    flat-blob leak class ``_redact_evidence_points`` guards against.
    """

    if sort not in _VALID_SORTS:
        sort = "updated"
    page = max(page, 1)
    page_size = max(1, min(page_size, _MAX_PAGE_SIZE))

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))
    workspace_scoped = identity is not None and _isolation_active(paths)

    where = ["sensitivity_rank <= ?"]
    params: list[Any] = [threshold_rank]
    if workspace_scoped:
        where.append("workspace_id = ?")
        params.append(identity.workspace_id)  # type: ignore[union-attr]
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
    if term:
        placeholders = ",".join("?" for _ in term)
        where.append(
            "EXISTS (SELECT 1 FROM catalog_terms ct WHERE "
            "ct.catalog_item_id = catalog_items.catalog_item_id "
            f"AND ct.term IN ({placeholders}) AND ct.sensitivity_rank <= ?)"
        )
        params.extend(term)
        params.append(threshold_rank)
    if role:
        placeholders = ",".join("?" for _ in role)
        where.append(
            "EXISTS (SELECT 1 FROM catalog_terms ct WHERE "
            "ct.catalog_item_id = catalog_items.catalog_item_id "
            f"AND ct.role IN ({placeholders}) AND ct.sensitivity_rank <= ?)"
        )
        params.extend(role)
        params.append(threshold_rank)

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
        # Workspace scoping (when active) is NOT a "current filter" — it is an
        # identity boundary, so it applies here too (AC-4: a facet must never
        # leak a project/status/sensitivity value that exists only in another
        # workspace's rows).
        facets = _facets(
            conn,
            threshold_rank,
            workspace_id=identity.workspace_id if workspace_scoped else None,  # type: ignore[union-attr]
        )

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


def _facets(
    conn: sqlite3.Connection, threshold_rank: int, *, workspace_id: str | None = None
) -> dict[str, list[str]]:
    """``workspace_id`` is WKSP-304 Phase 3 scoping — ``None`` (the default)
    is byte-identical to the pre-WKSP-304 query; a non-``None`` value adds a
    parameterized ``AND workspace_id = ?`` predicate (caller is responsible
    for only passing one when ``identity`` is present and isolation is
    active — see :func:`search`)."""

    extra_where = " AND workspace_id = ?" if workspace_id is not None else ""

    def _distinct(column: str) -> list[str]:
        params: tuple[Any, ...] = (
            (threshold_rank, workspace_id) if workspace_id is not None else (threshold_rank,)
        )
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM catalog_items "
            f"WHERE sensitivity_rank <= ?{extra_where} AND {column} IS NOT NULL "
            f"ORDER BY {column}",
            params,
        ).fetchall()
        return [r[0] for r in rows]

    def _distinct_term_column(column: str) -> list[str]:
        # catalog_terms carries its own per-row sensitivity_rank (D3) but no
        # workspace_id, so workspace scoping (WKSP-304) requires a join back
        # to catalog_items — a bare `SELECT DISTINCT ... FROM catalog_terms`
        # would silently cross workspace boundaries. The sensitivity gate
        # mirrors search()'s term/role EXISTS clauses: only ct.sensitivity_rank
        # is checked (it is already the item's own effective rank), never a
        # value looser than the caller's threshold.
        term_extra_where = " AND ci.workspace_id = ?" if workspace_id is not None else ""
        params: tuple[Any, ...] = (
            (threshold_rank, workspace_id) if workspace_id is not None else (threshold_rank,)
        )
        rows = conn.execute(
            f"SELECT DISTINCT ct.{column} FROM catalog_terms ct "
            "JOIN catalog_items ci ON ci.catalog_item_id = ct.catalog_item_id "
            f"WHERE ct.sensitivity_rank <= ?{term_extra_where} "
            f"ORDER BY ct.{column}",
            params,
        ).fetchall()
        return [r[0] for r in rows]

    return {
        "projects": _distinct("project"),
        "statuses": _distinct("status"),
        "sensitivities": _distinct("sensitivity"),
        "terms": _distinct_term_column("term"),
        "roles": _distinct_term_column("role"),
    }


def _log_enforced_denial_if_exists_elsewhere(
    conn: sqlite3.Connection,
    identity: AuthIdentity | None,
    *,
    record_type: str,
    record_id: str,
    table: str = "catalog_items",
    id_column: str = "catalog_item_id",
) -> None:
    """WKSP-304 Phase 4 (TASK-4.2, OQ-1): audit-log a cross-workspace deny.

    Called only from the branch where the scoped ``AND workspace_id = ?``
    query has already returned no row *and* isolation is actively enforced
    (i.e. ``workspace_id is not None``/``workspace_scoped is True`` at the
    call site — see :func:`get_item` and :func:`get_draft_index`). This
    helper's sole job is distinguishing "genuinely missing" (no log —
    nothing was denied) from "exists in another workspace, access denied"
    (logs), purely for the server-side audit trail; the caller-visible
    outcome (``None`` -> 404) is byte-identical either way, so this never
    changes response shape or timing-observable behaviour (OQ-1: the deny
    stays silent to the caller). Logged at ``ERROR`` — distinct from
    scope.py's advisory-mode ``WARNING`` — so a security-monitoring
    pipeline can tell "advisory: logged but let through" apart from
    "enforcing: actually denied".

    ``table``/``id_column`` default to the ``catalog_items`` shape
    (:func:`get_item`'s call site is unchanged); :func:`get_draft_index`
    passes ``table="catalog_report_drafts", id_column="report_draft_id"``
    to reuse the exact same "genuinely-missing vs. exists-elsewhere" logic
    against the draft index table instead. ``table``/``id_column`` are
    fixed literals at every call site in this module (never derived from
    request input), so this f-string never carries untrusted data.
    """

    if identity is None:
        return
    raw = conn.execute(
        f"SELECT workspace_id FROM {table} WHERE {id_column} = ?",
        (record_id,),
    ).fetchone()
    if raw is None:
        return  # genuinely missing -- no denial occurred, nothing to audit
    _logger.error(
        json.dumps(
            {
                "event": "workspace_scope_enforced_denial",
                "record_type": record_type,
                "record_id": record_id,
                "record_workspace_id": raw["workspace_id"],
                "identity_workspace_id": identity.workspace_id,
            }
        )
    )


def get_item(
    paths: FoundryPaths,
    catalog_item_id: str,
    *,
    sensitivity_threshold: str | None = None,
    identity: AuthIdentity | None = None,
) -> dict[str, Any] | None:
    """Return the full detail for *catalog_item_id*, or ``None`` if unknown or

    excluded by the resolved sensitivity threshold (fail-closed — callers
    should translate ``None`` to a 404, never distinguishing "doesn't exist"
    from "not visible").

    ``identity`` is WKSP-304 Phase 3 query-layer scoping (see module
    docstring): ``None`` (the default) is byte-identical to the pre-WKSP-304
    query for every statement below, including the outgoing/incoming link
    joins and the citing-drafts join (AC-4 — the predicate is applied to the
    joined side, not only the primary ``catalog_items`` row, so a cross-
    workspace link target can't leak through an edge even once isolation is
    active).

    WKSP-304 Phase 4 (TASK-4.2): the primary row's scoped ``WHERE
    workspace_id = ?`` predicate below is the query-layer deny mechanism for
    this single-record read (same idiom as the list-oriented ``search()``);
    a cross-workspace lookup returns no row and is audit-logged (distinct
    from the advisory ``WARNING``) via
    :func:`_log_enforced_denial_if_exists_elsewhere`, then 404s exactly like
    a genuinely-missing item (OQ-1 — silent either way).
    """

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))
    workspace_scoped = identity is not None and _isolation_active(paths)
    workspace_id = identity.workspace_id if workspace_scoped else None  # type: ignore[union-attr]

    with _db(paths) as conn:
        if workspace_id is not None:
            row = conn.execute(
                "SELECT * FROM catalog_items WHERE catalog_item_id = ? AND workspace_id = ?",
                (catalog_item_id, workspace_id),
            ).fetchone()
            if row is None:
                _log_enforced_denial_if_exists_elsewhere(
                    conn, identity, record_type="catalog_item", record_id=catalog_item_id
                )
                return None
        else:
            row = conn.execute(
                "SELECT * FROM catalog_items WHERE catalog_item_id = ?", (catalog_item_id,)
            ).fetchone()
            if row is None:
                return None
        if row["sensitivity_rank"] > threshold_rank:
            return None

        payload = json.loads(row["payload_json"])
        if row["item_type"] == "source":
            payload = _redact_evidence_points(payload, threshold_rank)

        # F3: only surface an edge when the *other* endpoint is itself visible
        # at the resolved threshold — otherwise the edge leaks a hidden
        # catalog_item_id (and its relation) even though the requested item
        # is visible. Same rule as search()'s WHERE sensitivity_rank <= ?.
        # AC-4: the same workspace predicate applied to the primary row above
        # is applied to the JOINed side (``i.workspace_id``) here too — the
        # requested item may be in-scope while a linked item is not.
        outgoing_ws_clause = " AND i.workspace_id = ?" if workspace_id is not None else ""
        outgoing_params: tuple[Any, ...] = (
            (catalog_item_id, threshold_rank, workspace_id)
            if workspace_id is not None
            else (catalog_item_id, threshold_rank)
        )
        outgoing = conn.execute(
            f"""
            SELECT l.to_item_id AS to_item_id, l.relation AS relation
            FROM catalog_links l
            JOIN catalog_items i ON i.catalog_item_id = l.to_item_id
            WHERE l.from_item_id = ? AND i.sensitivity_rank <= ?{outgoing_ws_clause}
            """,
            outgoing_params,
        ).fetchall()
        incoming = conn.execute(
            f"""
            SELECT l.from_item_id AS from_item_id, l.relation AS relation
            FROM catalog_links l
            JOIN catalog_items i ON i.catalog_item_id = l.from_item_id
            WHERE l.to_item_id = ? AND i.sensitivity_rank <= ?{outgoing_ws_clause}
            """,
            outgoing_params,
        ).fetchall()

        # D11 reverse-catalog: drafts that cite this item via catalog_links.
        # Draft from_item_ids are report_draft_id values — never catalog_item_ids —
        # so the existing `incoming` query (which joins catalog_items) silently
        # drops every draft edge. Resolve at read time against catalog_report_drafts
        # only (no schema change — catalog.db is disposable and reindex_all_drafts
        # repopulates the forward rows this query reads).
        # Drafts are gated by their own sensitivity_rank so a draft above the
        # resolved threshold cannot leak its existence through this field.
        # AC-4: same workspace predicate applied to the joined ``d`` side.
        citing_ws_clause = " AND d.workspace_id = ?" if workspace_id is not None else ""
        citing_params: tuple[Any, ...] = (
            (catalog_item_id, threshold_rank, workspace_id)
            if workspace_id is not None
            else (catalog_item_id, threshold_rank)
        )
        citing_drafts_rows = conn.execute(
            f"""
            SELECT d.report_draft_id, d.title, l.relation, d.project_id
            FROM catalog_links l
            JOIN catalog_report_drafts d ON d.report_draft_id = l.from_item_id
            WHERE l.to_item_id = ? AND d.sensitivity_rank <= ?{citing_ws_clause}
            """,
            citing_params,
        ).fetchall()

    summary = _row_to_summary(row)
    summary["payload"] = payload
    summary["links"] = {
        "outgoing": [{"catalog_item_id": r["to_item_id"], "relation": r["relation"]} for r in outgoing],
        "incoming": [{"catalog_item_id": r["from_item_id"], "relation": r["relation"]} for r in incoming],
        "citing_drafts": [
            {
                "report_draft_id": r["report_draft_id"],
                "draft_name": r["title"],
                "relation": r["relation"],
                "project_id": r["project_id"],
            }
            for r in citing_drafts_rows
        ],
    }
    # WKSP-304 Phase 4 (TASK-4.2): only ever reached once the scoped query
    # above has already denied (and audit-logged) a cross-workspace
    # mismatch when enforcing, so this call is advisory-only in practice
    # here (identity=None, isolation inactive, or an already-confirmed
    # workspace match) — kept for parity with builder_service/
    # agent_job_service's identical call shape and to preserve the
    # WKSP-301 advisory WARNING for those cases. Passes ``dict(row)``
    # (not ``summary``, which omits ``workspace_id`` — see
    # ``_SUMMARY_COLUMNS``) so the mismatch/match comparison is against
    # the record's real workspace_id rather than always reading as a
    # mismatch.
    require_workspace_scope(
        identity,
        dict(row),
        record_type="catalog_item",
        record_id=catalog_item_id,
        resolve_enforcement=lambda: _isolation_active(paths),
    )
    return summary


def _attribution_coverage_counts(
    conn: sqlite3.Connection,
    threshold_rank: int,
    *,
    workspace_id: str | None = None,
) -> dict[str, int]:
    """Raw tri-state counts over visible ``source`` catalog items (SMP-4.5).

    ``attribution_count`` (SMP-4.2/4.3's nullable column, populated per
    :func:`_attribution_count_of` at row-build time) already carries the
    tri-state signal: ``NULL`` == not-yet-assessed, ``0`` == assessed and
    absent, ``>0`` == assessed and present. This is a single read-only SQL
    aggregate over already-imported rows — no recomputation, no file read,
    no wall-clock read, no model or network call — so it stays consistent
    with the module's "recomputable from files on every export" invariant.

    The three states are returned as three distinct dict keys (never
    collapsed into one another, never a shared ``null``) — that distinction
    is the entire point of this milestone's no-backfill decision.
    """

    where = ["item_type = 'source'", "sensitivity_rank <= ?"]
    params: list[Any] = [threshold_rank]
    if workspace_id is not None:
        where.append("workspace_id = ?")
        params.append(workspace_id)
    where_sql = " AND ".join(where)

    row = conn.execute(
        "SELECT "
        "  SUM(CASE WHEN attribution_count IS NULL THEN 1 ELSE 0 END) AS not_yet_assessed, "
        "  SUM(CASE WHEN attribution_count = 0 THEN 1 ELSE 0 END) AS absent, "
        "  SUM(CASE WHEN attribution_count > 0 THEN 1 ELSE 0 END) AS present, "
        "  COUNT(*) AS total "
        f"FROM catalog_items WHERE {where_sql}",
        params,
    ).fetchone()
    return {
        "present": row["present"] or 0,
        "absent": row["absent"] or 0,
        "not_yet_assessed": row["not_yet_assessed"] or 0,
        "total": row["total"] or 0,
    }


def _format_attribution_coverage(counts: dict[str, int]) -> dict[str, Any]:
    """Derive ``assessed`` and the human-readable "N of M sources assessed"
    line from :func:`_attribution_coverage_counts`'s raw tri-state counts.

    ``assessed`` = ``present + absent`` — both states mean "a source's
    attribution mirror was actually evaluated", the "N" the plan's AC names.
    ``not_yet_assessed`` is deliberately excluded from that numerator: folding
    it in would silently read the historical, never-assessed corpus as
    evaluated, exactly the no-backfill result-set bias this milestone exists
    to close.
    """

    present = counts["present"]
    absent = counts["absent"]
    not_yet_assessed = counts["not_yet_assessed"]
    total = counts["total"]
    assessed = present + absent
    return {
        "present": present,
        "absent": absent,
        "not_yet_assessed": not_yet_assessed,
        "assessed": assessed,
        "total": total,
        "coverage_line": f"{assessed} of {total} sources assessed",
    }


def attribution_coverage(
    paths: FoundryPaths,
    *,
    sensitivity_threshold: str | None = None,
    identity: AuthIdentity | None = None,
) -> dict[str, Any]:
    """Tri-state attribution coverage over visible ``source`` items
    (SMP-4.5) — the milestone's honesty control for the plan's no-backfill
    decision.

    Returns ``present`` / ``absent`` / ``not_yet_assessed`` as three
    DISTINCT counts, plus ``assessed`` (``present + absent``) and a
    human-readable ``coverage_line`` (``"N of M sources assessed"``).
    Read-path only: identical recomputability guarantee as :func:`stats` —
    no file read, no wall-clock read, no model or network call, safe to call
    twice in a row over an unchanged catalog and get the same answer.

    Also folded into :func:`stats` (which applies this SAME scoping rule to
    its ``attribution_coverage`` block — see that function's own docstring)
    so ``GET /catalog/stats`` surfaces the same N-of-M line without a
    dedicated endpoint.
    """

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))
    workspace_scoped = identity is not None and _isolation_active(paths)
    with _db(paths) as conn:
        counts = _attribution_coverage_counts(
            conn,
            threshold_rank,
            workspace_id=identity.workspace_id if workspace_scoped else None,  # type: ignore[union-attr]
        )
    return _format_attribution_coverage(counts)


def stats(
    paths: FoundryPaths,
    *,
    sensitivity_threshold: str | None = None,
    identity: AuthIdentity | None = None,
) -> dict[str, Any]:
    """Aggregate counts (visible items only, per the resolved threshold).

    ``identity`` scopes ONLY the ``attribution_coverage`` block below to the
    same workspace-scoping rule :func:`attribution_coverage` applies
    (``None``/isolation-inactive stays unscoped, byte-identical to before).
    The rest of this function's counts (``counts``, ``runs_indexed``,
    ``last_import_at``) are deliberately left unscoped — that is a separate,
    already-tracked pre-existing gap (WKSP-304 P4 TODO on the router's call
    site), not something this fix widens.
    """

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))
    workspace_scoped = identity is not None and _isolation_active(paths)

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

        # SMP-4.5 / isolation fix: tri-state attribution coverage over
        # visible `source` items. Reuses the already-open connection/
        # threshold rather than opening a second one via
        # attribution_coverage() — but now applies the SAME workspace scope
        # that function applies, rather than always reading every
        # workspace's counts (the pre-fix behavior leaked cross-workspace
        # aggregate counts through GET /catalog/stats; see
        # attribution_coverage()'s own docstring for the scoping rule).
        attribution_counts = _attribution_coverage_counts(
            conn,
            threshold_rank,
            workspace_id=identity.workspace_id if workspace_scoped else None,  # type: ignore[union-attr]
        )

    return {
        "counts": counts,
        "runs_indexed": runs_indexed,
        "last_import_at": log_row["last_import_at"] if log_row else None,
        "attribution_coverage": _format_attribution_coverage(attribution_counts),
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


def get_draft_index(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    identity: AuthIdentity | None = None,
) -> dict[str, Any] | None:
    """Return the indexed summary row for *report_draft_id*, or ``None``.

    ``identity`` is WKSP-304 Phase 3 query-layer scoping (see module
    docstring): ``None`` (the default) is byte-identical to the pre-WKSP-304
    query, including the outgoing ``catalog_links`` query below. TASK-3.4
    (AC-4): the pre-WKSP-304 links query never joined ``catalog_items``, so
    it cannot gain an unconditional ``JOIN`` without risking a behavior
    change for the ``identity=None``/inactive baseline (a dangling
    ``to_item_id`` with no matching ``catalog_items`` row — however
    unlikely — would silently vanish from the result under an unconditional
    INNER JOIN). Instead the JOIN only exists on the actively-scoped branch:
    a draft can cite a catalog item that lives in a different workspace, and
    without this the linked item's ``catalog_item_id`` would leak through
    ``get_draft_index``'s ``links`` field even once isolation is active.

    WKSP-304 Phase 4 (TASK-4.2): mirrors :func:`get_item`'s audit-log
    parity — a cross-workspace lookup (``workspace_scoped`` branch,
    scoped query returns no row) is audit-logged (distinct from the
    advisory ``WARNING``) via
    :func:`_log_enforced_denial_if_exists_elsewhere` before falling through
    to the same ``None`` -> 404 outcome a genuinely-missing draft produces
    (OQ-1 — silent either way).
    """

    workspace_scoped = identity is not None and _isolation_active(paths)

    with _db(paths) as conn:
        if workspace_scoped:
            row = conn.execute(
                "SELECT * FROM catalog_report_drafts WHERE report_draft_id = ? "
                "AND workspace_id = ?",
                (report_draft_id, identity.workspace_id),  # type: ignore[union-attr]
            ).fetchone()
            if row is None:
                _log_enforced_denial_if_exists_elsewhere(
                    conn,
                    identity,
                    record_type="report_draft",
                    record_id=report_draft_id,
                    table="catalog_report_drafts",
                    id_column="report_draft_id",
                )
                return None
        else:
            row = conn.execute(
                "SELECT * FROM catalog_report_drafts WHERE report_draft_id = ?",
                (report_draft_id,),
            ).fetchone()
            if row is None:
                return None
        result = {col: row[col] for col in _DRAFT_INDEX_COLUMNS}
        if workspace_scoped:
            link_rows = conn.execute(
                """
                SELECT l.to_item_id AS to_item_id, l.relation AS relation
                FROM catalog_links l
                JOIN catalog_items i ON i.catalog_item_id = l.to_item_id
                WHERE l.from_item_id = ? AND i.workspace_id = ?
                """,
                (report_draft_id, identity.workspace_id),  # type: ignore[union-attr]
            ).fetchall()
        else:
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
    identity: AuthIdentity | None = None,
) -> list[dict[str, Any]]:
    """List indexed draft summaries (fail-closed on the resolved threshold).

    ``identity`` is WKSP-304 Phase 3 query-layer scoping (see module
    docstring): ``None`` (the default) is byte-identical to the pre-WKSP-304
    query.
    """

    threshold_rank = _rank(resolve_threshold(paths, sensitivity_threshold))
    workspace_scoped = identity is not None and _isolation_active(paths)
    where = ["sensitivity_rank <= ?"]
    params: list[Any] = [threshold_rank]
    if workspace_scoped:
        where.append("workspace_id = ?")
        params.append(identity.workspace_id)  # type: ignore[union-attr]
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


def purge_lifecycle_derived_file(path: Path, *, lifecycle_state: object) -> bool:
    """Purge a derived catalog/cache file only after an authoritative block.

    Reconciliation callers provide the already-persisted lifecycle state.  A
    stale, unknown, or merely requested event cannot delete a current read;
    symlinks are likewise rejected so cleanup cannot escape the workspace.
    """

    if lifecycle_state != "blocked" or not path.exists() or path.is_symlink() or not path.is_file():
        return False
    path.unlink()
    return True


__all__ = [
    "SCHEMA_VERSION",
    "ITEM_TYPES",
    "CatalogError",
    "CatalogUnavailable",
    "query_only_connection",
    "is_catalog_available",
    "rebuild_schema",
    "import_run",
    "import_all",
    "rebuild",
    "search",
    "get_item",
    "stats",
    "attribution_coverage",
    "index_draft",
    "remove_draft_index",
    "get_draft_index",
    "list_draft_index",
    "purge_lifecycle_derived_file",
    "report_item_id",
]
