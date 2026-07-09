"""Report Builder draft store — file-canonical, catalog-indexed (Phase 3, D10).

Public-multiuser-release Phase 3 Wave D (plan D10-D13, spec §8). Parallels
``catalog_service.py`` but inverts its durability contract:

* **Draft truth lives ONLY in files.** Every draft is
  ``<workspace>/reports/drafts/<report_draft_id>/draft.yaml`` (current state)
  plus ``revisions/<report_version_id>.yaml`` (immutable snapshots). Every
  mutator in this module writes those files atomically (temp file in the
  same directory, then ``os.replace``) so a crash mid-write can never leave a
  torn draft.
* **``catalog.db`` holds only a derived, rebuildable index** —
  ``catalog_service.catalog_report_drafts`` (+ ``catalog_links`` edges for
  ``derived_from``/``cites``, D11). Every mutator here re-syncs that index as
  its last step (:func:`_sync_catalog_index`), but the index is never
  consulted to reconstruct a draft — :func:`reindex_all_drafts` proves this by
  rebuilding the whole index from disk with zero reads of the old index.
  This is the inverse of ``catalog_service``, whose ``catalog_items`` rows
  ARE safely disposable because ``export_run()`` can always regenerate them
  from run artifacts; a builder draft has no equivalent regeneration source,
  which is exactly why plan D10 forbids treating it as cache.

Block markdown carries `[claim:<id>]` tags inline (added by
:func:`add_claim_link`) rather than only in structured metadata, so
:func:`export_markdown`'s output is stable Markdown+frontmatter with no
second claim-linking pass — the same contract ``rf`` run reports already use.

D13 verification checks live in :mod:`research_foundry.services.verification`
(``check_paragraph_has_support`` et al. + the ``verify_draft`` aggregate);
this module calls none of them directly, only maintains the denormalized
``coverage_status``/``linked_claim_ids`` fields used to render the Builder UI
before a verify pass runs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from ..api.auth.provider import AuthIdentity
from ..api.auth.scope import require_workspace_scope, resolve_workspace_isolation_active
from ..errors import NotFoundError, RFError
from ..frontmatter import join_frontmatter
from ..ids import now_iso, short_hash
from ..ids import report_draft_id as _mint_report_draft_base
from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, load_yaml
from . import audit_service, catalog_service
from .audit_service import AuditEvent
from .export_service import SENSITIVITY_ORDER, export_run

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WKSP-304 Phase 3: query-layer workspace_id scoping (flag-gated, inert by
# default — decision D4). Same idiom as catalog_service.py's identically-
# named helper (single-owner phase — see phase-3-query-layer-scoping.md
# "why single-owner"): duplicated rather than shared so each of the 3
# services in this phase stays self-contained; TASK-3.5 (backend-architect)
# decides whether/how to consolidate into one shared helper for Phase 4.
# ---------------------------------------------------------------------------


def _isolation_active(paths: FoundryPaths) -> bool:
    """Resolve whether WKSP-304 workspace isolation is actively enforced.

    WKSP-304 Phase 4 (TASK-4.2 consolidation): delegates to the single
    shared implementation in
    :func:`research_foundry.api.auth.scope.resolve_workspace_isolation_active`
    — Phase 3 duplicated this helper identically into this module,
    ``catalog_service.py``, and ``AgentJobService`` as a deliberate
    single-owner-phase choice (see phase-3-query-layer-scoping.md "why
    single-owner"); this module-level name/call sites are kept unchanged so
    no caller here needs to change. Pure refactor, no behaviour change.
    """

    return resolve_workspace_isolation_active(paths)

# Reused verbatim from export_service (D8's text_hash recipe) so a claim
# link's `quote_text_hash` and P2's `report_anchors[].text_hash` share one
# hash contract. These are intentionally the *same* private helpers P2 uses,
# not a fork — do not reimplement the normalization/hash rule here.
from .export_service import _anchor_text_hash as _text_hash  # noqa: E402
from .export_service import _normalize_anchor_text as _normalize_text  # noqa: E402

BUILDER_SCHEMA_VERSION = 1

BLOCK_TYPES: tuple[str, ...] = (
    "heading",
    "paragraph",
    "table",
    "quote",
    "callout",
    "evidence_summary",
)
MATERIALITY_VALUES: tuple[str, ...] = ("material", "narrative", "background")
DRAFT_STATUSES: tuple[str, ...] = ("draft", "verified", "published", "archived")
AUDIENCES: tuple[str, ...] = ("self", "technical", "executive", "public", "client")
ORIGINS: tuple[str, ...] = ("blank", "template", "run", "collection")
RELATIONS: tuple[str, ...] = (
    "supports",
    "contradicts",
    "context",
    "inferred_from",
    "cited_nearby",
)
LINK_STATUSES: tuple[str, ...] = (
    "linked",
    "stale",
    "missing_claim",
    "missing_source",
    "needs_review",
)

# claim.status -> claim_links[].relation default, when the caller doesn't pin
# one explicitly. Mirrors export_service's _ANCHOR_RELATION_BY_STATUS (P2)
# intentionally duplicated here (tiny, stable mapping) rather than importing
# a private symbol whose name/shape is P2's business, not ours.
_RELATION_BY_CLAIM_STATUS: dict[str, str] = {
    "supported": "supports",
    "mixed": "supports",
    "contradicted": "contradicts",
    "inference": "inferred_from",
    "speculation": "inferred_from",
    "unsupported": "context",
}

_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "title",
    "audience",
    "sensitivity",
    "status",
    "blocks",
    "claim_links",
    "source_links",
    "comments",
    "review_state",
)


class BuilderError(RFError):
    """A Report Builder draft operation failed validation (bad enum, etc.)."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
#
# R2 CRITICAL fix: report_draft_id / report_version_id are caller-controlled
# strings that get joined onto a filesystem Path. The API router used to gate
# on ``report_id.startswith("rpt_")`` — a PREFIX check that a payload like
# ``rpt_../../../etc`` satisfies unchanged, giving arbitrary file read (GET
# .../versions/{vid}) and arbitrary ``shutil.rmtree`` (DELETE .../{report_id})
# outside ``reports/drafts/``. Every mutator/reader in this module funnels
# through :func:`_draft_dir` / :func:`_revision_path`, so validating the id
# SHAPE here (not just in the router) protects the API, the CLI, and any
# future direct caller alike. A resolve()+containment assertion is kept as
# defense-in-depth in case the shape regex is ever loosened.

_DRAFT_ID_RE = re.compile(r"^rpt_[A-Za-z0-9_-]+$")
_VERSION_ID_RE = re.compile(r"^rptv_[A-Za-z0-9_-]+$")


def _validate_draft_id(report_draft_id: str) -> None:
    if not report_draft_id or not _DRAFT_ID_RE.fullmatch(report_draft_id):
        raise NotFoundError(f"report draft not found: {report_draft_id}")


def _validate_version_id(report_draft_id: str, report_version_id: str) -> None:
    if not report_version_id or not _VERSION_ID_RE.fullmatch(report_version_id):
        raise NotFoundError(f"revision not found: {report_draft_id}/{report_version_id}")


def _draft_dir(paths: FoundryPaths, report_draft_id: str) -> Path:
    _validate_draft_id(report_draft_id)
    candidate = paths.report_draft_dir(report_draft_id)
    if not candidate.resolve().is_relative_to(paths.report_drafts.resolve()):
        raise NotFoundError(f"report draft not found: {report_draft_id}")
    return candidate


def _draft_yaml_path(paths: FoundryPaths, report_draft_id: str) -> Path:
    return _draft_dir(paths, report_draft_id) / "draft.yaml"


def _revisions_dir(paths: FoundryPaths, report_draft_id: str) -> Path:
    return _draft_dir(paths, report_draft_id) / "revisions"


def _revision_path(paths: FoundryPaths, report_draft_id: str, report_version_id: str) -> Path:
    _validate_version_id(report_draft_id, report_version_id)
    path = _revisions_dir(paths, report_draft_id) / f"{report_version_id}.yaml"
    if not path.resolve().is_relative_to(paths.report_drafts.resolve()):
        raise NotFoundError(f"revision not found: {report_draft_id}/{report_version_id}")
    return path


# ---------------------------------------------------------------------------
# Atomic writes (D10 durability discipline)
# ---------------------------------------------------------------------------


def _atomic_write_yaml(obj: dict[str, Any], path: Path) -> Path:
    """Write YAML atomically: temp file in the same directory, then rename.

    A crash mid-write must never leave a torn/partial ``draft.yaml`` or
    revision snapshot — ``os.replace`` is atomic on the same filesystem, and
    the temp file is unlinked on any failure before it is ever visible at
    *path*.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(dumps_yaml(obj))
        os.replace(tmp_name, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(tmp_name)
        raise
    return path


# ---------------------------------------------------------------------------
# ID minting (deterministic — counters, not randomness/uuid)
# ---------------------------------------------------------------------------


def _mint_draft_id(paths: FoundryPaths, title: str) -> str:
    """Atomically claim a fresh, unused draft directory.

    R2 HIGH fix: the previous implementation used ``disambiguate_id``'s
    check-then-act ``exists()`` probe, which has a race window between the
    check and :func:`_save_draft`'s eventual write — two concurrent
    ``create_draft`` calls for the same title (``report_draft_id(title)`` has
    no time component, only the day) can both observe "doesn't exist" and
    mint the identical id, and the second ``os.replace`` silently clobbers
    the first draft. Exclusive ``os.mkdir`` (no ``exist_ok``) makes the claim
    itself the atomic operation — only one caller's ``mkdir`` for a given
    path can ever succeed, so a collision is a guaranteed
    ``FileExistsError``, never a race, and the loop below always retries with
    a fresh candidate rather than reusing an occupied one.
    """

    base = _mint_report_draft_base(title)
    paths.report_drafts.mkdir(parents=True, exist_ok=True)
    seed = f"{title}:{now_iso()}"
    candidate = base
    attempt = 0
    while True:
        try:
            os.mkdir(_draft_dir(paths, candidate))
            return candidate
        except FileExistsError:
            attempt += 1
            suffix = short_hash(seed, length=4) if attempt == 1 else short_hash(seed, str(attempt), length=4)
            candidate = f"{base}_{suffix}" if attempt == 1 else f"{base}_{suffix}_{attempt}"
            if attempt > 1000:  # pragma: no cover - pathological collision guard
                raise BuilderError(
                    f"could not allocate a unique report_draft_id for title {title!r}"
                ) from None


def _next_seq(draft: dict[str, Any], kind: str) -> int:
    seq = draft.setdefault("seq", {})
    n = int(seq.get(kind, 0)) + 1
    seq[kind] = n
    return n


def _mint_block_id(report_draft_id: str, seq: int) -> str:
    return f"blk_{short_hash(report_draft_id, 'block', str(seq), length=10)}"


def _mint_claim_link_id(report_draft_id: str, seq: int) -> str:
    return f"rl_{short_hash(report_draft_id, 'claim_link', str(seq), length=10)}"


def _mint_source_link_id(report_draft_id: str, seq: int) -> str:
    return f"sl_{short_hash(report_draft_id, 'source_link', str(seq), length=10)}"


def _mint_version_id(report_draft_id: str, seq: int) -> str:
    return f"rptv_{short_hash(report_draft_id, 'version', str(seq), length=10)}"


# ---------------------------------------------------------------------------
# Load / save / list / delete
# ---------------------------------------------------------------------------


def load_draft(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    identity: AuthIdentity | None = None,
) -> dict[str, Any]:
    """Load a draft's current state from disk. Raises :class:`NotFoundError`.

    ``identity`` is WKSP-304 Phase 3 query-layer scoping (see
    :func:`_isolation_active`). This module has no SQL query to add an
    ``AND workspace_id = ?`` predicate to (drafts are file-canonical, per the
    module docstring) — the file-storage equivalent of that predicate is
    applied here: when ``identity`` is not ``None`` and isolation is
    actively enforced, a draft whose ``workspace_id`` does not match
    ``identity.workspace_id`` is treated exactly like a missing draft
    (:class:`NotFoundError`), the same fail-closed contract every other
    "not visible" case in this codebase uses (e.g. catalog_service.get_item's
    over-threshold items). ``identity=None`` (the default) is byte-identical
    to the pre-WKSP-304 behavior — every existing caller (:func:`list_drafts`,
    :func:`export_markdown`, revision helpers) that does not pass ``identity``
    is unaffected.

    WKSP-304 Phase 4 (TASK-4.2, OQ-1): the file-storage predicate below is
    this module's query-layer-equivalent deny mechanism — on an enforcing-
    mode mismatch it raises :class:`NotFoundError` (silent 404, same
    exception a genuinely-missing draft already raises) *and* emits a
    structured ``ERROR``-level denial log, distinct from scope.py's
    advisory-mode ``WARNING`` below it.
    """

    path = _draft_yaml_path(paths, report_draft_id)
    if not path.exists():
        raise NotFoundError(f"report draft not found: {report_draft_id}")
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise BuilderError(f"malformed draft.yaml: {path}")

    if identity is not None and _isolation_active(paths):
        if data.get("workspace_id") != identity.workspace_id:
            _logger.error(
                json.dumps(
                    {
                        "event": "workspace_scope_enforced_denial",
                        "record_type": "draft",
                        "record_id": report_draft_id,
                        "record_workspace_id": data.get("workspace_id"),
                        "identity_workspace_id": identity.workspace_id,
                    }
                )
            )
            raise NotFoundError(f"report draft not found: {report_draft_id}")

    # WKSP-304 Phase 4 (TASK-4.2): only ever reached once the enforcing
    # branch above has already denied (and audit-logged) a cross-workspace
    # mismatch, so this call is advisory-only in practice here
    # (identity=None, isolation inactive, or an already-confirmed
    # workspace match) — the resolver is still wired through so the
    # WKSP-301 advisory WARNING path stays correct for those cases.
    require_workspace_scope(
        identity,
        data,
        record_type="draft",
        record_id=report_draft_id,
        resolve_enforcement=lambda: _isolation_active(paths),
    )
    return data


def _save_draft(paths: FoundryPaths, draft: dict[str, Any]) -> dict[str, Any]:
    """Persist *draft* atomically, then re-sync its derived catalog index row.

    Every mutator in this module funnels through here as its last step.
    """

    path = _draft_yaml_path(paths, draft["report_draft_id"])
    _atomic_write_yaml(draft, path)
    _sync_catalog_index(paths, draft)

    # Audit: single choke-point for all 11+ report-edit call-sites (fail-open).
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="report_edit",
            action="save_draft",
            target_ref=draft["report_draft_id"],
            result="success",
        ),
    )

    return draft


def _touch(draft: dict[str, Any], updated_by: str | None) -> None:
    draft["updated_at"] = now_iso()
    if updated_by is not None:
        draft["updated_by"] = updated_by


def list_drafts(
    paths: FoundryPaths, *, identity: AuthIdentity | None = None
) -> list[dict[str, Any]]:
    """Scan on-disk drafts (the source of truth) and return summaries.

    ``identity`` is WKSP-304 Phase 3 query-layer scoping: threading it
    straight into :func:`load_draft` is deliberate — that function already
    raises :class:`NotFoundError` for a workspace mismatch when isolation is
    active, and this loop already treats ``NotFoundError`` as "skip", so a
    cross-workspace draft is filtered out of the listing for free, with the
    single predicate living in one place (:func:`load_draft`) rather than
    duplicated here. ``identity=None`` (the default) is byte-identical to the
    pre-WKSP-304 listing.
    """

    root = paths.report_drafts
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        try:
            draft = load_draft(paths, d.name, identity=identity)
        except (NotFoundError, BuilderError):
            continue
        out.append(_summary_of(draft))
    return out


def delete_draft(paths: FoundryPaths, report_draft_id: str) -> None:
    """Delete a draft's directory (draft.yaml + revisions) and its index row."""

    d = _draft_dir(paths, report_draft_id)
    if d.exists():
        shutil.rmtree(d)
    catalog_service.remove_draft_index(paths, report_draft_id)

    # Audit: separate call because delete_draft does not go through _save_draft (fail-open).
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="report_edit",
            action="delete_draft",
            target_ref=report_draft_id,
            result="success",
        ),
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def create_draft(
    paths: FoundryPaths,
    *,
    title: str,
    origin: str = "blank",
    audience: str = "self",
    sensitivity: str = "public",
    project_id: str | None = None,
    workspace_id: str | None = None,
    created_by: str | None = None,
    source_run_id: str | None = None,
    source_template_id: str | None = None,
    source_collection_id: str | None = None,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new draft (spec §8: from a template, a run, a collection, or
    blank). *blocks* pre-seeds content (used by the ``create_draft_from_*``
    helpers below); each is a plain seed dict consumed by :func:`_append_block`.

    ``workspace_id``/``created_by`` are forward-compat, unenforced (plan D12).

    Returns the full persisted draft state (same shape as :func:`load_draft`).
    """

    if origin not in ORIGINS:
        raise BuilderError(f"unknown draft origin: {origin!r}; expected one of {ORIGINS}")
    if audience not in AUDIENCES:
        raise BuilderError(f"unknown audience: {audience!r}; expected one of {AUDIENCES}")
    if sensitivity not in SENSITIVITY_ORDER:
        raise BuilderError(f"unknown sensitivity: {sensitivity!r}")

    report_draft_id = _mint_draft_id(paths, title)
    ts = now_iso()
    draft: dict[str, Any] = {
        "schema_version": BUILDER_SCHEMA_VERSION,
        "type": "report_draft",
        "report_draft_id": report_draft_id,
        "title": title,
        "origin": origin,
        "source_run_id": source_run_id,
        "source_template_id": source_template_id,
        "source_collection_id": source_collection_id,
        "audience": audience,
        "sensitivity": sensitivity,
        "status": "draft",
        "workspace_id": workspace_id,
        "project_id": project_id,
        "created_by": created_by,
        "updated_by": created_by,
        "created_at": ts,
        "updated_at": ts,
        "current_version_id": None,
        "seq": {"block": 0, "claim_link": 0, "source_link": 0, "revision": 0},
        "blocks": [],
        "claim_links": [],
        "source_links": [],
        "comments": [],
        "review_state": {"status": "pending", "reviewers": []},
        "revisions": [],
    }
    for seed in blocks or []:
        _append_block(draft, seed)
    return _save_draft(paths, draft)


def _append_block(draft: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    """In-memory-only block append (no persistence/index sync)."""

    block_type = seed.get("block_type", "paragraph")
    if block_type not in BLOCK_TYPES:
        raise BuilderError(f"unknown block_type: {block_type!r}; expected one of {BLOCK_TYPES}")
    materiality = seed.get("materiality", "material")
    if materiality not in MATERIALITY_VALUES:
        raise BuilderError(f"unknown materiality: {materiality!r}; expected one of {MATERIALITY_VALUES}")
    order = seed.get("order")
    if order is None:
        order = max([b["order"] for b in draft["blocks"]], default=-1) + 1
    seq = _next_seq(draft, "block")
    block = {
        "block_id": seed.get("block_id") or _mint_block_id(draft["report_draft_id"], seq),
        "block_type": block_type,
        "order": order,
        "markdown": seed.get("markdown", ""),
        "materiality": materiality,
        "linked_claim_ids": list(seed.get("linked_claim_ids") or []),
        "linked_source_ids": list(seed.get("linked_source_ids") or []),
        "coverage_status": _compute_coverage_status(materiality, []),
        "risk_flags": list(seed.get("risk_flags") or []),
    }
    draft["blocks"].append(block)
    return block


def _find_block(draft: dict[str, Any], block_id: str) -> dict[str, Any]:
    for b in draft["blocks"]:
        if b["block_id"] == block_id:
            return b
    raise NotFoundError(f"block not found in draft {draft['report_draft_id']}: {block_id}")


# ---------------------------------------------------------------------------
# Block CRUD
# ---------------------------------------------------------------------------


def add_block(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    block_type: str = "paragraph",
    markdown: str = "",
    order: int | None = None,
    materiality: str = "material",
    updated_by: str | None = None,
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    _append_block(
        draft,
        {"block_type": block_type, "markdown": markdown, "order": order, "materiality": materiality},
    )
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


def update_block(
    paths: FoundryPaths,
    report_draft_id: str,
    block_id: str,
    *,
    markdown: str | None = None,
    block_type: str | None = None,
    materiality: str | None = None,
    order: int | None = None,
    risk_flags: list[str] | None = None,
    updated_by: str | None = None,
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    block = _find_block(draft, block_id)
    if block_type is not None:
        if block_type not in BLOCK_TYPES:
            raise BuilderError(f"unknown block_type: {block_type!r}; expected one of {BLOCK_TYPES}")
        block["block_type"] = block_type
    if markdown is not None:
        block["markdown"] = markdown
    if materiality is not None:
        if materiality not in MATERIALITY_VALUES:
            raise BuilderError(f"unknown materiality: {materiality!r}")
        block["materiality"] = materiality
    if order is not None:
        block["order"] = order
    if risk_flags is not None:
        block["risk_flags"] = list(risk_flags)
    _recompute_block_coverage(draft, block_id)
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


def delete_block(
    paths: FoundryPaths, report_draft_id: str, block_id: str, *, updated_by: str | None = None
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    _find_block(draft, block_id)  # raises NotFoundError if absent
    draft["blocks"] = [b for b in draft["blocks"] if b["block_id"] != block_id]
    draft["claim_links"] = [cl for cl in draft["claim_links"] if cl["block_id"] != block_id]
    draft["source_links"] = [sl for sl in draft["source_links"] if sl.get("block_id") != block_id]
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


def reorder_blocks(
    paths: FoundryPaths, report_draft_id: str, block_ids: list[str], *, updated_by: str | None = None
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    by_id = {b["block_id"]: b for b in draft["blocks"]}
    if set(block_ids) != set(by_id):
        raise BuilderError("reorder_blocks: block_ids must be a permutation of the draft's blocks")
    for i, bid in enumerate(block_ids):
        by_id[bid]["order"] = i
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


def _compute_coverage_status(materiality: str, links: list[dict[str, Any]]) -> str:
    if materiality != "material":
        return "narrative"
    if not links:
        return "unsupported"
    relations = {cl.get("relation") for cl in links}
    statuses = {cl.get("link_status") for cl in links}
    if "contradicts" in relations:
        return "contradicted"
    if statuses & {"missing_claim", "missing_source"}:
        return "unsupported"
    if statuses & {"needs_review", "stale"}:
        return "needs_review"
    return "supported"


def _recompute_block_coverage(draft: dict[str, Any], block_id: str) -> None:
    block = _find_block(draft, block_id)
    links = [cl for cl in draft["claim_links"] if cl["block_id"] == block_id]
    block["linked_claim_ids"] = sorted({cl["claim_id"] for cl in links})
    block["coverage_status"] = _compute_coverage_status(block["materiality"], links)


# ---------------------------------------------------------------------------
# Claim links
# ---------------------------------------------------------------------------


def _resolve_claim(
    paths: FoundryPaths,
    *,
    catalog_item_id: str | None,
    source_run_id: str | None,
    claim_id: str,
) -> dict[str, Any] | None:
    """Best-effort claim lookup for relation inference + existence checking.

    Catalog resolution (stable cross-run id) is tried first; falls back to a
    direct read of the run's claim ledger when only ``(source_run_id,
    claim_id)`` is known. Uses the max-permissive threshold internally — this
    is an existence/status check for link bookkeeping, not a read-time
    redaction decision (that happens at export/verify time).
    """

    if catalog_item_id:
        item = catalog_service.get_item(paths, catalog_item_id, sensitivity_threshold="client_sensitive")
        if item is not None:
            return {"status": item.get("status")}
        return None
    if source_run_id:
        rp = paths.run_paths(source_run_id)
        if rp.claim_ledger.exists():
            ledger = load_yaml(rp.claim_ledger) or {}
            for c in ledger.get("claims") or []:
                if isinstance(c, dict) and c.get("claim_id") == claim_id:
                    return {"status": c.get("status")}
    return None


def add_claim_link(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    block_id: str,
    claim_id: str,
    relation: str | None = None,
    source_run_id: str | None = None,
    catalog_item_id: str | None = None,
    span_start: int | None = None,
    span_end: int | None = None,
    insert_tag: bool = True,
    updated_by: str | None = None,
) -> dict[str, Any]:
    """Link *claim_id* to *block_id* (spec §7 Report Location V2 / §8 claim_links[]).

    When *insert_tag* is true (default) and the block's markdown does not
    already carry a ``[claim:<claim_id>]`` tag, one is appended — this is
    what makes the eventual :func:`export_markdown` output's claim
    references "stable" (spec §8): the tag always lives in the persisted
    block text, never only in structured metadata.

    *span_start*/*span_end* are character offsets into the block's
    *normalized* markdown (spec §7 Report Location V2) for a caller that
    knows which excerpt it linked (e.g. a future "select text, link claim"
    Builder UI action). Omitted (the common case — linking a whole
    paragraph, or importing a bare ``[claim:]`` tag from a run), the span
    defaults to the *entire* normalized block — one hash validates "this
    paragraph is unchanged", matching P2's per-block ``text_hash`` semantics
    (D8) rather than the narrow tag-marker text.
    """

    draft = load_draft(paths, report_draft_id)
    block = _find_block(draft, block_id)

    if insert_tag and not re.search(rf"\[claim:{re.escape(claim_id)}\]", block["markdown"]):
        block["markdown"] = (block["markdown"].rstrip() + f" [claim:{claim_id}]").strip()

    resolved = _resolve_claim(
        paths, catalog_item_id=catalog_item_id, source_run_id=source_run_id, claim_id=claim_id
    )
    link_status = "linked" if resolved is not None else "missing_claim"
    if relation is None:
        relation = _RELATION_BY_CLAIM_STATUS.get(str((resolved or {}).get("status")), "context")
    elif relation not in RELATIONS:
        raise BuilderError(f"unknown relation: {relation!r}; expected one of {RELATIONS}")

    normalized = _normalize_text(block["markdown"])
    start = span_start if span_start is not None else 0
    end = span_end if span_end is not None else len(normalized)
    quote_text_hash = _text_hash(normalized[start:end]) if normalized else None

    seq = _next_seq(draft, "claim_link")
    link = {
        "claim_link_id": _mint_claim_link_id(report_draft_id, seq),
        "block_id": block_id,
        "claim_id": claim_id,
        "source_run_id": source_run_id,
        "catalog_item_id": catalog_item_id,
        "relation": relation,
        "span_start": start,
        "span_end": end,
        "quote_text_hash": quote_text_hash,
        "link_status": link_status,
    }
    draft["claim_links"].append(link)
    _recompute_block_coverage(draft, block_id)
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


def remove_claim_link(
    paths: FoundryPaths, report_draft_id: str, claim_link_id: str, *, updated_by: str | None = None
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    target = next((cl for cl in draft["claim_links"] if cl["claim_link_id"] == claim_link_id), None)
    if target is None:
        raise NotFoundError(f"claim link not found: {claim_link_id}")
    draft["claim_links"] = [cl for cl in draft["claim_links"] if cl["claim_link_id"] != claim_link_id]
    _recompute_block_coverage(draft, target["block_id"])
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


# ---------------------------------------------------------------------------
# Source links
# ---------------------------------------------------------------------------


def add_source_link(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    source_card_id: str,
    run_id: str | None = None,
    catalog_item_id: str | None = None,
    block_id: str | None = None,
    relation: str | None = None,
    updated_by: str | None = None,
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    if block_id is not None:
        _find_block(draft, block_id)  # validate existence

    seq = _next_seq(draft, "source_link")
    link = {
        "source_link_id": _mint_source_link_id(report_draft_id, seq),
        "block_id": block_id,
        "source_card_id": source_card_id,
        "run_id": run_id,
        "catalog_item_id": catalog_item_id,
        "relation": relation,
    }
    draft["source_links"].append(link)
    if block_id is not None:
        block = _find_block(draft, block_id)
        block["linked_source_ids"] = sorted(
            {sl["source_card_id"] for sl in draft["source_links"] if sl.get("block_id") == block_id}
        )
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


def remove_source_link(
    paths: FoundryPaths, report_draft_id: str, source_link_id: str, *, updated_by: str | None = None
) -> dict[str, Any]:
    draft = load_draft(paths, report_draft_id)
    target = next((sl for sl in draft["source_links"] if sl["source_link_id"] == source_link_id), None)
    if target is None:
        raise NotFoundError(f"source link not found: {source_link_id}")
    draft["source_links"] = [
        sl for sl in draft["source_links"] if sl["source_link_id"] != source_link_id
    ]
    block_id = target.get("block_id")
    if block_id is not None:
        block = _find_block(draft, block_id)
        block["linked_source_ids"] = sorted(
            {sl["source_card_id"] for sl in draft["source_links"] if sl.get("block_id") == block_id}
        )
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


# ---------------------------------------------------------------------------
# Revisions (versioned history)
# ---------------------------------------------------------------------------


def create_revision(
    paths: FoundryPaths, report_draft_id: str, *, created_by: str | None = None, note: str | None = None
) -> dict[str, Any]:
    """Snapshot the draft's current content into ``revisions/<version>.yaml``.

    Snapshots are full copies (not diffs) — cheap at report scale and
    trivially restorable without replaying history. Returns the revision
    pointer that was appended to ``draft.yaml``'s ``revisions[]`` list.
    """

    draft = load_draft(paths, report_draft_id)
    seq = _next_seq(draft, "revision")
    report_version_id = _mint_version_id(report_draft_id, seq)
    ts = now_iso()
    snapshot = {
        "report_draft_id": report_draft_id,
        "report_version_id": report_version_id,
        "created_at": ts,
        "created_by": created_by,
        "note": note,
        **{k: draft[k] for k in _SNAPSHOT_FIELDS},
    }
    _atomic_write_yaml(snapshot, _revision_path(paths, report_draft_id, report_version_id))

    pointer = {
        "report_version_id": report_version_id,
        "created_at": ts,
        "created_by": created_by,
        "note": note,
    }
    draft["revisions"].append(pointer)
    draft["current_version_id"] = report_version_id
    _touch(draft, created_by)
    _save_draft(paths, draft)
    return pointer


def list_revisions(paths: FoundryPaths, report_draft_id: str) -> list[dict[str, Any]]:
    draft = load_draft(paths, report_draft_id)
    return list(draft.get("revisions") or [])


def get_revision(paths: FoundryPaths, report_draft_id: str, report_version_id: str) -> dict[str, Any]:
    path = _revision_path(paths, report_draft_id, report_version_id)
    if not path.exists():
        raise NotFoundError(f"revision not found: {report_draft_id}/{report_version_id}")
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise BuilderError(f"malformed revision snapshot: {path}")
    return data


def restore_revision(
    paths: FoundryPaths, report_draft_id: str, report_version_id: str, *, updated_by: str | None = None
) -> dict[str, Any]:
    """Overwrite the draft's content fields with a prior revision snapshot.

    Does not itself create a new revision — callers wanting a pre-restore
    checkpoint should call :func:`create_revision` first.
    """

    snapshot = get_revision(paths, report_draft_id, report_version_id)
    draft = load_draft(paths, report_draft_id)
    for k in _SNAPSHOT_FIELDS:
        draft[k] = snapshot[k]
    _touch(draft, updated_by)
    return _save_draft(paths, draft)


# ---------------------------------------------------------------------------
# Create-from-* helpers (spec §8: template / run / collection / blank)
# ---------------------------------------------------------------------------

_RAW_MD = MarkdownIt("commonmark")
_RAW_CONTAINER_OPEN = frozenset(
    {"blockquote_open", "bullet_list_open", "ordered_list_open", "list_item_open"}
)
_RAW_CONTAINER_CLOSE = frozenset(
    {"blockquote_close", "bullet_list_close", "ordered_list_close", "list_item_close"}
)


def _extract_raw_blocks(report_draft_md: str) -> list[dict[str, str]]:
    """Ordered top-level heading/paragraph text from *report_draft_md*.

    Mirrors ``export_service.derive_report_anchors()``'s token walk (same
    container-exclusion + h2/h3-only heading rule) purely to recover each
    block's editable raw text — ``report_anchors`` itself carries no prose
    (see that function's docstring), so this positional walk is how the
    Builder gets human-editable text that lines up 1:1, in document order,
    with the paragraph anchors already computed by the export layer.
    """

    if not report_draft_md:
        return []
    tokens = _RAW_MD.parse(report_draft_md)
    n = len(tokens)
    blocks: list[dict[str, str]] = []
    container_depth = 0
    i = 0
    while i < n:
        tok = tokens[i]
        if tok.type in _RAW_CONTAINER_OPEN:
            container_depth += 1
            i += 1
            continue
        if tok.type in _RAW_CONTAINER_CLOSE:
            container_depth -= 1
            i += 1
            continue
        if tok.type == "heading_open":
            next_tok = tokens[i + 1] if i + 1 < n else None
            has_inline = next_tok is not None and next_tok.type == "inline"
            if container_depth == 0 and has_inline and next_tok is not None:
                tag_level = tok.tag[1:]
                level = int(tag_level) if tag_level.isdigit() else None
                if level in (2, 3):
                    blocks.append({"kind": "heading", "text": next_tok.content})
            i += 3 if has_inline else 1
            continue
        if tok.type == "paragraph_open":
            next_tok = tokens[i + 1] if i + 1 < n else None
            has_inline = next_tok is not None and next_tok.type == "inline"
            if container_depth == 0 and has_inline and next_tok is not None:
                normalized = _normalize_text(next_tok.content)
                if normalized:
                    blocks.append({"kind": "paragraph", "text": normalized})
            i += 3 if has_inline else 1
            continue
        i += 1
    return blocks


def create_draft_from_run(
    paths: FoundryPaths,
    *,
    run_id: str,
    title: str | None = None,
    audience: str = "self",
    sensitivity: str | None = None,
    project_id: str | None = None,
    workspace_id: str | None = None,
    created_by: str | None = None,
    sensitivity_threshold: str = "client_sensitive",
) -> dict[str, Any]:
    """Seed a draft from a run's ``report_draft`` + ``report_anchors`` (P2, D7/D8).

    Reuses the run's already-derived, AST-based ``report_anchors`` for
    claim_links (never re-derives anchor hashes/ids independently — Wave A's
    derivation stays the single source of truth) and :func:`_extract_raw_blocks`
    purely to recover each anchored paragraph's editable text.
    """

    export_data = export_run(paths, run_id, sensitivity_threshold=sensitivity_threshold)
    report_draft_md = export_data.get("report_draft") or ""
    anchors = export_data.get("report_anchors") or []

    raw_blocks = _extract_raw_blocks(report_draft_md)
    seeds: list[dict[str, Any]] = []
    anchor_for_seed: list[dict[str, Any] | None] = []
    para_idx = 0
    for raw in raw_blocks:
        if raw["kind"] == "heading":
            seeds.append({"block_type": "heading", "markdown": raw["text"], "materiality": "narrative"})
            anchor_for_seed.append(None)
            continue
        anchor = anchors[para_idx] if para_idx < len(anchors) else None
        para_idx += 1
        seeds.append({"block_type": "paragraph", "markdown": raw["text"]})
        anchor_for_seed.append(anchor)

    resolved_title = title or export_data.get("title") or run_id
    draft = create_draft(
        paths,
        title=resolved_title,
        origin="run",
        audience=audience,
        sensitivity=sensitivity or export_data.get("sensitivity") or "public",
        project_id=project_id,
        workspace_id=workspace_id,
        created_by=created_by,
        source_run_id=run_id,
        blocks=seeds,
    )
    report_draft_id = draft["report_draft_id"]

    for seed_anchor, block in zip(anchor_for_seed, draft["blocks"], strict=True):
        if seed_anchor is None:
            continue
        for cl in seed_anchor.get("claim_links") or []:
            if cl.get("link_status") == "missing_claim":
                continue
            # Deliberately do NOT pass the anchor's own span_start/span_end —
            # those are P2's tag-marker offsets, not a meaningful excerpt;
            # add_claim_link's default (whole normalized block) gives
            # paragraph-level drift detection matching P2's text_hash intent.
            draft = add_claim_link(
                paths,
                report_draft_id,
                block_id=block["block_id"],
                claim_id=cl["claim_id"],
                relation=cl.get("relation"),
                source_run_id=run_id,
                insert_tag=False,  # tag already present verbatim in the run's report_draft text
            )

    return load_draft(paths, report_draft_id)


def create_draft_from_collection(
    paths: FoundryPaths,
    *,
    catalog_item_ids: list[str],
    title: str,
    audience: str = "self",
    sensitivity: str = "public",
    project_id: str | None = None,
    workspace_id: str | None = None,
    created_by: str | None = None,
    sensitivity_threshold: str = "client_sensitive",
) -> dict[str, Any]:
    """Seed a draft with one ``evidence_summary`` block per catalog item (spec §8).

    Each resolved claim/inference/source becomes a pre-linked block;
    unresolved ids are skipped (best-effort — collection membership can drift
    as the catalog changes underneath a saved selection).
    """

    draft = create_draft(
        paths,
        title=title,
        origin="collection",
        audience=audience,
        sensitivity=sensitivity,
        project_id=project_id,
        workspace_id=workspace_id,
        created_by=created_by,
    )
    report_draft_id = draft["report_draft_id"]

    for catalog_item_id in catalog_item_ids:
        item = catalog_service.get_item(paths, catalog_item_id, sensitivity_threshold=sensitivity_threshold)
        if item is None:
            continue
        markdown = item.get("summary") or item.get("title") or ""
        draft = add_block(paths, report_draft_id, block_type="evidence_summary", markdown=markdown)
        block = draft["blocks"][-1]
        item_type = item.get("item_type")
        local_ref = str(item.get("local_ref") or "")
        if item_type in ("claim", "inference"):
            add_claim_link(
                paths,
                report_draft_id,
                block_id=block["block_id"],
                claim_id=local_ref,
                relation=_RELATION_BY_CLAIM_STATUS.get(str(item.get("status")), "context"),
                source_run_id=item.get("run_id"),
                catalog_item_id=catalog_item_id,
                insert_tag=True,
            )
        elif item_type == "source":
            add_source_link(
                paths,
                report_draft_id,
                source_card_id=local_ref,
                run_id=item.get("run_id"),
                catalog_item_id=catalog_item_id,
                block_id=block["block_id"],
            )

    return load_draft(paths, report_draft_id)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_markdown(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    identity: AuthIdentity | None = None,
) -> str:
    """Render the draft to Markdown with frontmatter + stable ``[claim:]`` tags.

    Blocks already carry ``[claim:<id>]`` tags inline (added by
    :func:`add_claim_link`), so this is a structural frontmatter+body join,
    not a second claim-linking pass.

    ``identity`` is WKSP-304 Phase 3 query-layer scoping — threaded straight
    into :func:`load_draft`, which raises :class:`NotFoundError` for a
    cross-workspace draft when isolation is active. ``identity=None`` (the
    default) is byte-identical to the pre-WKSP-304 export.
    """

    draft = load_draft(paths, report_draft_id, identity=identity)
    frontmatter = {
        "schema_version": "1.0",
        "type": "research_report",
        "report_id": draft["report_draft_id"],
        "title": draft["title"],
        "status": draft.get("status"),
        "audience": draft.get("audience"),
        "sensitivity": draft.get("sensitivity"),
        "created_at": draft.get("created_at"),
        "updated_at": draft.get("updated_at"),
    }
    lines: list[str] = []
    for block in sorted(draft["blocks"], key=lambda b: b["order"]):
        text = (block.get("markdown") or "").strip()
        if not text:
            continue
        if block["block_type"] == "heading":
            lines.append(text if text.startswith("#") else f"## {text}")
        else:
            lines.append(text)
        lines.append("")
    body = "\n".join(lines).strip() + "\n"
    return join_frontmatter(frontmatter, body)


# ---------------------------------------------------------------------------
# Derived catalog.db index sync (D11) + rebuild-safety (landmine #3)
# ---------------------------------------------------------------------------


def _summary_of(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_draft_id": draft["report_draft_id"],
        "title": draft["title"],
        "status": draft.get("status"),
        "sensitivity": draft.get("sensitivity"),
        "audience": draft.get("audience"),
        "origin": draft.get("origin"),
        "project_id": draft.get("project_id"),
        "workspace_id": draft.get("workspace_id"),
        "created_by": draft.get("created_by"),
        "current_version_id": draft.get("current_version_id"),
        "block_count": len(draft.get("blocks") or []),
        "claim_link_count": len(draft.get("claim_links") or []),
        "source_link_count": len(draft.get("source_links") or []),
        "created_at": draft.get("created_at"),
        "updated_at": draft.get("updated_at"),
    }


def _sync_catalog_index(paths: FoundryPaths, draft: dict[str, Any]) -> None:
    """Upsert *draft*'s row + ``catalog_links`` edges into the derived index.

    ``derived_from`` links the draft to its originating run's synthetic P1
    ``report`` catalog item (when created via :func:`create_draft_from_run`);
    ``cites`` links every claim/source the draft references that has a known
    ``catalog_item_id`` (D11).
    """

    report_draft_id = draft["report_draft_id"]
    entry = _summary_of(draft)
    entry["draft_path"] = str(_draft_yaml_path(paths, report_draft_id))

    links: list[dict[str, str]] = []
    if draft.get("source_run_id"):
        links.append(
            {
                "to_item_id": catalog_service.report_item_id(draft["source_run_id"]),
                "relation": "derived_from",
            }
        )
    seen: set[str] = set()
    for cl in draft.get("claim_links") or []:
        to_id = cl.get("catalog_item_id")
        if to_id and to_id not in seen:
            seen.add(to_id)
            links.append({"to_item_id": to_id, "relation": "cites"})
    for sl in draft.get("source_links") or []:
        to_id = sl.get("catalog_item_id")
        if to_id and to_id not in seen:
            seen.add(to_id)
            links.append({"to_item_id": to_id, "relation": "cites"})

    catalog_service.index_draft(paths, entry, links=links)


def reindex_all_drafts(paths: FoundryPaths) -> dict[str, Any]:
    """Rebuild the derived ``catalog.db`` draft index from on-disk drafts.

    Safe to call any time, in particular right after
    ``catalog_service.rebuild_schema()`` — draft.yaml files are the only
    thing ever read here, proving the index is 100% disposable (landmine #3)
    without touching a single draft file.
    """

    root = paths.report_drafts
    count = 0
    errors: list[dict[str, str]] = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            try:
                draft = load_draft(paths, d.name)
            except (NotFoundError, BuilderError) as exc:
                errors.append({"report_draft_id": d.name, "error": str(exc)})
                continue
            _sync_catalog_index(paths, draft)
            count += 1
    return {"drafts": count, "errors": errors}


__all__ = [
    "BUILDER_SCHEMA_VERSION",
    "BLOCK_TYPES",
    "MATERIALITY_VALUES",
    "DRAFT_STATUSES",
    "AUDIENCES",
    "ORIGINS",
    "RELATIONS",
    "LINK_STATUSES",
    "BuilderError",
    "load_draft",
    "list_drafts",
    "delete_draft",
    "create_draft",
    "create_draft_from_run",
    "create_draft_from_collection",
    "add_block",
    "update_block",
    "delete_block",
    "reorder_blocks",
    "add_claim_link",
    "remove_claim_link",
    "add_source_link",
    "remove_source_link",
    "create_revision",
    "list_revisions",
    "get_revision",
    "restore_revision",
    "export_markdown",
    "reindex_all_drafts",
]
