"""Policy-first read service behind the RF Knowledge MCP (Phase P2 skeleton).

Implements KMCP-2.1 of
``docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md``
("Phase P2: Non-Writing Knowledge Core") against the FROZEN P1 contracts in
``schemas/knowledge_search_request.schema.yaml``,
``schemas/knowledge_search_response.schema.yaml``,
``schemas/knowledge_document.schema.yaml``, and
``schemas/knowledge_activity_receipt.schema.yaml``, plus
``.codex/worknotes/research-foundry-knowledge-mcp/decisions-block.md``. Every
invariant cited below is that decisions block's own numbering.

**Invariant 1 (no transport/MCP imports).** This module imports only from
``..errors``, ``..paths``, ``..api.auth.provider`` (the identity value
object every other read service already depends on — not a transport), and
governed READ services (:mod:`export_service` today; :mod:`catalog_service`
and :mod:`assertion_catalog` are wired in by Phase P3's concrete
:class:`KindProjector` implementations, never by this module directly). It
never imports ``research_foundry.knowledge_mcp.*``, ``search_router.*``, an
Operator/Hermes module, a provider client, or a CLI/API router. Enforced by
construction — there is nothing here to import them with.

**Invariant 2 (reads never repair state).** Nothing in this module opens a
database connection, writes a file, or calls a rebuild/import/migration
function. A P3 :class:`KindProjector` that has not been registered yet (the
normal state for every kind during this Phase P2 skeleton) makes every
:class:`KnowledgeAccessService` search/fetch call resolve to the SAME
bounded, no-existence-leak :class:`KnowledgeDenied` outcome a real policy
denial would produce — this is Phase P2's own exit condition ("missing
projections fail typed/unavailable without writes"), not a special case.

**Invariant 3 (policy before derivation).** :func:`resolve_context` and
:class:`KnowledgeAccessContext` are the ONLY place identity/workspace,
sensitivity ceiling, and tool/kind eligibility are resolved; every method on
:class:`KnowledgeAccessService` consults them before touching a
:class:`KindProjector`, and no count/snippet/rank/cursor/URL/receipt is ever
derived from a record that policy has not already cleared.

**Invariant 6 (opaque, authority-neutral IDs).** :func:`parse_knowledge_id`
and :func:`build_local_resource_url` are the single source of truth for the
``rfk:v1:<kind>:<opaque>`` ID form and the loopback
``/api/knowledge/v1/fetch/<id>`` route pattern frozen in the P1 schemas'
``$defs.opaque_knowledge_id`` / ``$defs.local_resource_url`` — kept
byte-identical to those regexes so a change to either can never silently
drift out of sync with the schemas.

**Scope of this task (KMCP-2.1).** Defines the seams P3 (KMCP-3.1..3.4)
fills — the :class:`KindProjector` Protocol and its registry — but does NOT
implement a single one of the four domain projections itself. No source,
assertion, report, or run record is ever read by this module.

**Phase P3 scope added here (KMCP-3.1, KMCP-3.2).** Fills two of those four
seams. :class:`SourceKindProjector` (kind ``"source"``) resolves governed
source-catalog rows through :mod:`catalog_service`'s read-only seam
(:func:`catalog_service.is_catalog_available` /
:func:`catalog_service.query_only_connection` — never
:func:`catalog_service.search`/:func:`catalog_service.get_item`, both
write-capable via ``_connect``/``_db``, which may lazily create/migrate
``catalog.db``). :class:`AssertionKindProjector` (kind ``"assertion"``)
resolves exact assertion packets through
:class:`assertion_catalog.AssertionCatalog`'s non-rebuilding
``search_read_only``/``packet_read_only`` seam — never ``search``/
``packet``/``rebuild`` (all rebuild-on-miss or write-capable). Both fold the
caller's sensitivity ceiling — and, when WKSP-304 isolation is active,
workspace scope — directly into the read itself, before any snippet, title,
URL, or provenance field is derived (invariant 3), and never surface a raw
filesystem path: a source card's un-resolved ``url`` and an assertion
edition's sibling ``retrieval_locator.file_path`` are both omitted outright;
only an already-``http(s)`` locator ever becomes ``original_source_url``
(invariant 7, AC KMCP-4).

**Phase P3 scope added here (KMCP-3.3).** Fills the remaining two seams.
:class:`ReportKindProjector` (kinds ``"report_draft"`` XOR ``"report_final"``)
resolves :mod:`builder_service`'s file-canonical Report Builder draft store
through its existing READ path (:func:`builder_service.load_draft` /
:func:`builder_service.list_drafts` / :func:`builder_service.export_markdown`
— never a mutator; ``create_draft*``/``add_block``/``delete_draft`` and every
other write path in that module are never called here). KMCP-OQ-2's
resolution means ``report_draft`` and ``report_final`` are the SAME
underlying draft entity, distinguished only by its current lifecycle
``status`` at read time (:func:`_report_kind_for_status`: ``published``/
``archived`` resolve to ``report_final``; everything else, including an
unrecognized status, resolves to ``report_draft``) — never stored twice,
never merged into one ambiguous kind. Because
:func:`builder_service.load_draft` applies only the WKSP-304 workspace-scope
gate on its own, this projector ADDS the sensitivity-ceiling gate on top
(mirroring the same R2 fix ``api/routers/reports.py`` layers onto the
identical read paths) before deriving any title/snippet/text/rf_metadata
field (invariant 3). :class:`RunKindProjector` (kind ``"run"``) resolves
:mod:`export_service`'s run read model through :func:`export_service.list_runs`
/ :func:`export_service.export_run` — the SAME DF-004 workspace-scope gate
(``_run_read_allowed``) those already apply — but additionally reproduces the
no-existence-leak sensitivity gate ``api/routers/runs.py``'s own
``_enforce_existence_gate`` layers on top of ``export_run()``: that function's
own ``sensitivity_threshold`` argument only redacts per-claim quote/summary
text at or below the given rank, it does NOT by itself hide a run whose own
declared sensitivity exceeds that rank, so this projector checks that itself
before deriving anything (invariant 3). Neither projector ever surfaces a raw
filesystem path — no field from either read authority is passed through
unfiltered; every field is allowlisted exactly like the source/assertion
projectors above.

**Phase P3 scope added here (KMCP-3.4).** :meth:`KnowledgeAccessService._search`
/ :meth:`KnowledgeAccessService._fetch` (added in the P2 skeleton as the
composer scaffold every kind's page merges through) already provide the
deterministic multi-kind merge, bounding, and shared opaque-ID/local-URL
construction; this phase adds the two pieces that scaffold deliberately left
out: cursor-based text paging shared by every kind
(:func:`_paginate_document_text`, threaded through every concrete
:class:`KindProjector`'s ``fetch``) and the caller-carried, non-persisted RF
activity receipt (:func:`_build_receipt`, wired into
:meth:`KnowledgeAccessService.search_extended` /
:meth:`KnowledgeAccessService.fetch_extended` via an explicit
``include_receipt`` flag that defaults to ``False`` — preserving every
existing KMCP-2.4/3.1/3.2 caller's byte-for-byte equality against a
receipt-less :class:`RfKnowledgeSearchOutcome`/:class:`RfKnowledgeDocument`
literal; P4/P5 transports pass ``True`` for the actual ``rf_search``/
``rf_fetch``/typed-getter tool calls). The receipt's ``request_context_hash``
is a SHA-256 over the normalized, canonical-JSON request+policy context —
never the literal query/id/identity — and its ``generated_at`` timestamp is
the only field that legitimately varies between two calls against the same
underlying snapshot; every other field (``returned_ids``, ``bounds``,
``request_context_hash`` itself) replays byte-identically (KMCP-3.4's "same
snapshot replays byte-equivalent" exit condition).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import quote

from ..api.auth.provider import AuthIdentity
from ..api.auth.scope import resolve_workspace_isolation_active
from ..errors import NotFoundError, RFError
from ..frontmatter import split_frontmatter
from ..paths import FoundryPaths
from . import builder_service, catalog_service, clearance
from .assertion_catalog import (
    AssertionCatalog,
    AssertionCatalogDenied,
    AssertionCatalogUnavailable,
)
from .export_service import (
    SENSITIVITY_ORDER,
    ExportError,
    _title_from_slug,
    export_run,
    list_runs,
    resolve_threshold,
)

# ---------------------------------------------------------------------------
# Frozen vocabulary (byte-identical to the P1 schemas — KMCP-OQ-2, decisions
# block §0/§9.2)
# ---------------------------------------------------------------------------

KNOWLEDGE_KINDS: tuple[str, ...] = (
    "source",
    "assertion",
    "report_draft",
    "report_final",
    "run",
)

CORE_TOOL_NAMES: tuple[str, ...] = ("search", "fetch")
RF_TOOL_NAMES: tuple[str, ...] = (
    "rf_search",
    "rf_fetch",
    "rf_source_get",
    "rf_assertion_get",
    "rf_report_get",
    "rf_run_get",
)
# Exact eight-tool inventory (decisions-block §9.2) — P4 (KMCP-4.4) snapshots
# this same tuple as its negative-space guard; this module is its sole source.
TOOL_NAMES: tuple[str, ...] = CORE_TOOL_NAMES + RF_TOOL_NAMES

# --- fixed caps (KMCP-1.1 freeze; never caller-configurable) ---------------
QUERY_MAX_LENGTH = 512
CORE_SEARCH_MAX_RESULTS = 10
RF_SEARCH_MAX_RESULTS = 50
RF_SEARCH_DEFAULT_LIMIT = 25
TITLE_MAX_LENGTH = 300
SNIPPET_MAX_LENGTH = 1000
# Schema `maxLength` counts Unicode codepoints, not bytes (KMCP-FR-10); the
# actual operational cap is the tighter UTF-8 byte figure, enforced by P3
# adapters at construction time — this module only records both numbers.
DOCUMENT_MAX_TEXT_CODEPOINTS = 400_000
DOCUMENT_MAX_TEXT_BYTES = 200_000
RETURNED_IDS_MAX = 50
LOCAL_URL_MAX_LENGTH = 2048

# --- P3 projection caps (KMCP-3.1/3.2 freeze; never caller-configurable) ---
SOURCE_EVIDENCE_POINTS_MAX = 20
ASSERTION_EVALUATIONS_MAX = 10
ASSERTION_RUN_USES_MAX = RETURNED_IDS_MAX

# --- P3 projection caps (KMCP-3.3 freeze; never caller-configurable) -------
RUN_TAGS_MAX = 20

# --- P3/P4 policy + receipt constants (KMCP-3.4) ----------------------------
# Fixed, deterministic policy/ruleset version tag (invariant 3's fixed
# evaluation order) -- a hardcoded string, never wall-clock or environment
# derived, so a receipt's `policy_version` field replays byte-identically
# across repeated calls against the same snapshot (KMCP-3.4 exit condition).
# Bump this string, and only this string, when the policy order/set itself
# changes.
KNOWLEDGE_POLICY_VERSION = "kmcp-v1"

# Lifecycle statuses (report_draft.schema.yaml's `status` enum) that resolve
# a Report Builder draft to the "report_final" knowledge kind rather than
# "report_draft" -- KMCP-OQ-2 resolution, see :func:`_report_kind_for_status`.
REPORT_FINAL_STATUSES: frozenset[str] = frozenset({"published", "archived"})

# Fixed loopback origin every concrete P3 KindProjector builds its own
# `url`/`original_source_url` pair against. The real bind host/port is a
# P4/P5 transport-configuration concern (see build_local_resource_url's own
# docstring) that is not yet threaded through KnowledgeAccessContext, so
# every P3 projector uses this SAME constant -- exactly like the P2 test-only
# fixtures already do (`origin="http://127.0.0.1"`) -- rather than inventing
# its own.
_LOCAL_ORIGIN = "http://127.0.0.1"

# ---------------------------------------------------------------------------
# Opaque ID / local URL — byte-identical to every schema copy of these
# patterns (see module docstring, invariant 6)
# ---------------------------------------------------------------------------

_OPAQUE_ID_RE = re.compile(
    r"^rfk:v1:(source|assertion|report_draft|report_final|run):[A-Za-z0-9._~-]+$"
)
_LOCAL_URL_RE = re.compile(
    r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:[0-9]{1,5})?"
    r"/api/knowledge/v1/fetch/[A-Za-z0-9%._~-]+$"
)


class KnowledgeAccessError(RFError):
    """Base class for every error this module raises."""


class KnowledgeRequestError(KnowledgeAccessError):
    """A caller-supplied request shape is malformed (defense in depth).

    Every P1-frozen schema already rejects the same malformed shapes at the
    transport boundary before a service method is ever called; this
    exception exists only so the service does not silently misbehave if a
    future transport skips that step. It never carries a policy/denial
    reason — see :class:`KnowledgeDenied` for that.
    """


class KnowledgeInvariantError(KnowledgeAccessError):
    """A response object failed to satisfy its own frozen schema shape.

    Raised only by a DTO's own ``__post_init__`` validation (below) or by
    :func:`build_local_resource_url` when the constructed URL itself would
    not match the frozen pattern. This always signals a defect in the code
    building the DTO (a future P3 adapter, most likely) — never a caller
    input problem (:class:`KnowledgeRequestError`) or a policy decision
    (:class:`KnowledgeDenied`). No caller ever observes this class.
    """


@dataclass(frozen=True)
class KnowledgeDenied(KnowledgeAccessError):
    """The single, bounded, no-existence-leak outcome for every denial (AC KMCP-3).

    Every branch that could otherwise distinguish "genuinely unknown",
    "hidden by policy", "rights-denied", "stale/unavailable projection", or
    "cross-workspace" raises THIS shape instead. ``reason`` is an
    internal-only diagnostic code — callers (transports, P4/P5) MUST map
    every instance of this exception to the same generic, detail-free
    outcome (an empty ``results: []`` for a search-shaped call, or a single
    generic tool-call error for a fetch-shaped call per
    ``knowledge_document.schema.yaml``'s header); ``reason`` must never be
    rendered into a response body. See decisions-block §3 Risk 2 and
    KMCP-OQ-1's "indistinguishable in shape from hidden" resolution.
    """

    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.reason


# ---------------------------------------------------------------------------
# Opaque ID / local URL helpers (invariant 6)
# ---------------------------------------------------------------------------


def parse_knowledge_id(value: str) -> tuple[str, str]:
    """Parse an opaque knowledge id into ``(kind, opaque_id)``.

    Raises :class:`KnowledgeRequestError` for anything not matching the
    frozen ``rfk:v1:<kind>:<opaque>`` form (byte-identical to every schema
    copy of ``$defs.opaque_knowledge_id``) or longer than 200 characters.
    Never distinguishes "malformed" from "well-formed but unknown/hidden" in
    its own raised type — that distinction belongs to
    :class:`KnowledgeDenied`, resolved only after a real lookup, so a
    malformed vs. hidden id cannot be told apart by exception type either.
    """

    if not isinstance(value, str) or len(value) > 200:
        raise KnowledgeRequestError("malformed_knowledge_id")
    match = _OPAQUE_ID_RE.match(value)
    if match is None:
        raise KnowledgeRequestError("malformed_knowledge_id")
    return match.group(1), value


def build_local_resource_url(knowledge_id: str, *, origin: str) -> str:
    """Build the loopback, route-backed, non-canonical resource URL for ``knowledge_id``.

    KMCP-OQ-3 resolution: the SAME URL is returned by both `search` result
    items and `fetch`'s own document (self-referential fetch route).
    ``origin`` must already be one of the loopback forms the frozen schemas
    allow (``http(s)://127.0.0.1[:port]``, ``localhost[:port]``, or
    ``[::1][:port]``) — this function does not choose the bind host itself
    (a P4/P5 transport-configuration concern); it only appends the frozen
    ``/api/knowledge/v1/fetch/<percent-encoded-id>`` route.

    ``knowledge_id`` is percent-encoded with ``safe=""`` so the literal
    ``:`` characters inside its own ``rfk:v1:<kind>:<opaque>`` form are also
    encoded, matching the route segment's ``[A-Za-z0-9%._~-]+`` pattern.
    Raises :class:`KnowledgeRequestError` if ``knowledge_id`` itself is
    malformed, or :class:`KnowledgeInvariantError` if the constructed URL
    does not match the frozen ``local_resource_url`` pattern (e.g. a
    non-loopback ``origin``) — defense in depth; this function never
    silently emits a URL its own schema copy would reject.
    """

    parse_knowledge_id(knowledge_id)  # validates shape; raises KnowledgeRequestError if not
    encoded = quote(knowledge_id, safe="")
    url = f"{origin}/api/knowledge/v1/fetch/{encoded}"
    if len(url) > LOCAL_URL_MAX_LENGTH or not _LOCAL_URL_RE.match(url):
        raise KnowledgeInvariantError("invalid_local_resource_url")
    return url


def deterministic_id_sort_key(knowledge_id: str) -> tuple[str, str]:
    """Stable ``(kind, opaque)`` sort key for merging/ordering knowledge items.

    Groups a merged page by kind before breaking ties within a kind by the
    opaque segment, giving byte-identical ordering across repeated calls
    against the same underlying data (KMCP-3.4's "same snapshot replays
    byte-equivalent" exit condition) regardless of per-adapter iteration
    order. Real relevance ranking (score/rank) is P3 scope (KMCP-3.4); this
    is only the deterministic fallback every projection can already rely on.
    """

    kind, opaque = parse_knowledge_id(knowledge_id)
    return (kind, opaque)


# ---------------------------------------------------------------------------
# Access context (invariant 3 — resolved by the TRANSPORT, never accepted as
# a request field; see knowledge_search_request.schema.yaml's header)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeAccessContext:
    """Resolved caller context for one Knowledge read (KMCP-1.1 access contract).

    Built by the calling transport (CLI/API/MCP) via :func:`resolve_context`
    and passed into every :class:`KnowledgeAccessService` method — never
    accepted as a field inside a request body (a caller cannot widen its own
    sensitivity ceiling or workspace by adding a JSON field).

    Two resolution modes match the P1 freeze:

    * **Local trust** (``identity=None``) — the local stdio transport (P4)
      runs under the calling OS process's identity; there is no separate
      remote auth in v1.
    * **Enforced identity** (``identity`` set) — CLI/API transports resolve
      and enforce an explicit workspace/identity exactly like existing read
      services (WKSP-304 row-level isolation).

    ``sensitivity_ceiling`` is intersected with every existing
    workspace/source sensitivity gate downstream
    (:data:`export_service.SENSITIVITY_ORDER`'s four-level vocabulary) — a
    request can never widen it (invariant 3).
    """

    identity: AuthIdentity | None
    sensitivity_ceiling: str
    tool: str

    def __post_init__(self) -> None:
        if self.tool not in TOOL_NAMES:
            raise KnowledgeRequestError("unknown_tool")
        if self.sensitivity_ceiling not in SENSITIVITY_ORDER:
            raise KnowledgeRequestError("unknown_sensitivity_ceiling")

    @property
    def workspace_id(self) -> str | None:
        return self.identity.workspace_id if self.identity is not None else None

    @property
    def sensitivity_rank(self) -> int:
        return SENSITIVITY_ORDER[self.sensitivity_ceiling]


def resolve_context(
    paths: FoundryPaths,
    *,
    tool: str,
    identity: AuthIdentity | None = None,
    sensitivity_threshold: str | None = None,
) -> KnowledgeAccessContext:
    """Resolve one caller's :class:`KnowledgeAccessContext` (KMCP-1.1).

    ``sensitivity_threshold`` (an explicit transport-level override) takes
    precedence; otherwise falls back to the workspace's configured ceiling
    via :func:`export_service.resolve_threshold` — the SAME resolution every
    existing read service (:mod:`catalog_service`) already uses, so a
    Knowledge caller never gets a looser ceiling than any other RF reader
    would. Never reads a request body field to do this (see
    :class:`KnowledgeAccessContext`'s docstring).
    """

    ceiling = resolve_threshold(paths, sensitivity_threshold)
    return KnowledgeAccessContext(identity=identity, sensitivity_ceiling=ceiling, tool=tool)


# ---------------------------------------------------------------------------
# Kind allowlist
# ---------------------------------------------------------------------------


def eligible_kinds(requested: Sequence[str] | None = None) -> tuple[str, ...]:
    """Resolve which of :data:`KNOWLEDGE_KINDS` a request may search/fetch.

    ``requested`` (the optional ``rf_search`` ``kinds`` filter) can only
    NARROW the frozen five-kind vocabulary — never widen it (invariant 3: "a
    filter can narrow eligible results but never widen them"). An unknown
    kind name in ``requested`` is silently dropped rather than raising,
    since ``knowledge_search_request.schema.yaml``'s
    ``rf_search_request.kinds`` enum already rejects it at the transport
    boundary before this is ever called — this is defense in depth, not the
    primary gate. Always returns kinds in the fixed :data:`KNOWLEDGE_KINDS`
    order (deterministic ordering).
    """

    if requested is None:
        return KNOWLEDGE_KINDS
    wanted = set(requested)
    return tuple(kind for kind in KNOWLEDGE_KINDS if kind in wanted)


# ---------------------------------------------------------------------------
# Response objects — mirror the frozen core/RF DTO split exactly (invariant 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeSearchResultItem:
    """Frozen core ``SearchDTO`` result item — exactly id/title/url (invariant 5).

    Mirrors ``knowledge_search_response.schema.yaml``'s
    ``$defs.core_search_result_item``. No snippet, kind, rank, score, or
    receipt field is ever added here.
    """

    id: str
    title: str
    url: str

    def __post_init__(self) -> None:
        parse_knowledge_id(self.id)
        if not 1 <= len(self.title) <= TITLE_MAX_LENGTH:
            raise KnowledgeInvariantError("invalid_title")
        if len(self.url) > LOCAL_URL_MAX_LENGTH or not _LOCAL_URL_RE.match(self.url):
            raise KnowledgeInvariantError("invalid_local_resource_url")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "url": self.url}


@dataclass(frozen=True)
class KnowledgeSearchResponse:
    """Frozen core ``SearchDTO`` — exactly one ``results`` property (invariant 5)."""

    results: tuple[KnowledgeSearchResultItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.results) > CORE_SEARCH_MAX_RESULTS:
            raise KnowledgeInvariantError("too_many_results")

    def to_dict(self) -> dict[str, Any]:
        return {"results": [item.to_dict() for item in self.results]}


@dataclass(frozen=True)
class RfKnowledgeSearchResultItem:
    """RF-extended search result item — separately named from the core item.

    Mirrors ``knowledge_search_response.schema.yaml``'s
    ``$defs.rf_search_result_item``. ``content_is_untrusted`` is not a
    stored field — it is always emitted as the constant ``True``
    (KMCP-FR-11), so no adapter can ever construct one with it ``False``.
    """

    id: str
    title: str
    url: str
    kind: str
    snippet: str | None = None
    rank: int | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        resolved_kind, _ = parse_knowledge_id(self.id)
        if self.kind not in KNOWLEDGE_KINDS or self.kind != resolved_kind:
            raise KnowledgeInvariantError("kind_mismatch")
        if not 1 <= len(self.title) <= TITLE_MAX_LENGTH:
            raise KnowledgeInvariantError("invalid_title")
        if len(self.url) > LOCAL_URL_MAX_LENGTH or not _LOCAL_URL_RE.match(self.url):
            raise KnowledgeInvariantError("invalid_local_resource_url")
        if self.snippet is not None and len(self.snippet) > SNIPPET_MAX_LENGTH:
            raise KnowledgeInvariantError("invalid_snippet")
        if self.rank is not None and self.rank < 0:
            raise KnowledgeInvariantError("invalid_rank")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "kind": self.kind,
            "content_is_untrusted": True,
        }
        if self.snippet is not None:
            payload["snippet"] = self.snippet
        if self.rank is not None:
            payload["rank"] = self.rank
        if self.score is not None:
            payload["score"] = self.score
        return payload


@dataclass(frozen=True)
class RfKnowledgeSearchOutcome:
    """RF-extended ``rf_search`` output (separately named from the core root).

    ``receipt`` defaults to ``None`` -- the P2/KMCP-3.1/3.2 skeleton's every
    existing caller constructs/compares against a receipt-less instance
    (``RfKnowledgeSearchOutcome(results=..., next_cursor=..., truncated=...)``)
    and every one of those equality checks must keep passing unchanged; only
    :meth:`KnowledgeAccessService.search_extended` (KMCP-3.4, opt-in via its
    own ``include_receipt`` flag) ever sets this to a real
    ``knowledge_activity_receipt.schema.yaml``-shaped dict (see
    :func:`_build_receipt`). Omitted from :meth:`to_dict` entirely when
    ``None`` (matches ``rf_search_response.receipt``'s own not-required
    schema slot; this file's other ``to_dict`` methods use the identical
    omit-when-absent convention for optional fields).
    """

    results: tuple[RfKnowledgeSearchResultItem, ...] = field(default_factory=tuple)
    next_cursor: str | None = None
    truncated: bool = False
    receipt: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if len(self.results) > RF_SEARCH_MAX_RESULTS:
            raise KnowledgeInvariantError("too_many_results")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "results": [item.to_dict() for item in self.results],
            "next_cursor": self.next_cursor,
            "truncated": self.truncated,
        }
        if self.receipt is not None:
            payload["receipt"] = self.receipt
        return payload


@dataclass(frozen=True)
class KnowledgeDocument:
    """Frozen core ``FetchDTO`` — id/title/text/url required, ``metadata`` open+optional.

    Mirrors ``knowledge_document.schema.yaml``'s root shape (invariant 5).
    """

    id: str
    title: str
    text: str
    url: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        parse_knowledge_id(self.id)
        if not 1 <= len(self.title) <= TITLE_MAX_LENGTH:
            raise KnowledgeInvariantError("invalid_title")
        if len(self.text) > DOCUMENT_MAX_TEXT_CODEPOINTS:
            raise KnowledgeInvariantError("text_too_long")
        if len(self.url) > LOCAL_URL_MAX_LENGTH or not _LOCAL_URL_RE.match(self.url):
            raise KnowledgeInvariantError("invalid_local_resource_url")
        if self.metadata is not None and len(self.metadata) > 50:
            raise KnowledgeInvariantError("metadata_too_large")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "url": self.url,
        }
        if self.metadata is not None:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class RfKnowledgeDocument:
    """RF-extended document — returned by ``rf_fetch`` and the four typed getters.

    Mirrors ``knowledge_document.schema.yaml``'s
    ``$defs.knowledge_document_extended``. ``content_is_untrusted`` is not a
    stored field — always emitted as the constant ``True`` (KMCP-FR-11).
    Concrete per-kind ``rf_metadata`` fields are P3 scope (KMCP-3.1..3.3);
    this dataclass only reserves the open slot.
    """

    id: str
    title: str
    url: str
    kind: str
    text: str | None = None
    original_source_url: str | None = None
    truncated: bool | None = None
    next_cursor: str | None = None
    rf_metadata: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        resolved_kind, _ = parse_knowledge_id(self.id)
        if self.kind not in KNOWLEDGE_KINDS or self.kind != resolved_kind:
            raise KnowledgeInvariantError("kind_mismatch")
        if not 1 <= len(self.title) <= TITLE_MAX_LENGTH:
            raise KnowledgeInvariantError("invalid_title")
        if len(self.url) > LOCAL_URL_MAX_LENGTH or not _LOCAL_URL_RE.match(self.url):
            raise KnowledgeInvariantError("invalid_local_resource_url")
        if self.text is not None and len(self.text) > DOCUMENT_MAX_TEXT_CODEPOINTS:
            raise KnowledgeInvariantError("text_too_long")
        if self.original_source_url is not None and not self.original_source_url.startswith(
            ("http://", "https://")
        ):
            raise KnowledgeInvariantError("invalid_original_source_url")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "kind": self.kind,
            "content_is_untrusted": True,
        }
        if self.text is not None:
            payload["text"] = self.text
        if self.original_source_url is not None:
            payload["original_source_url"] = self.original_source_url
        if self.truncated is not None:
            payload["truncated"] = self.truncated
        if self.next_cursor is not None:
            payload["next_cursor"] = self.next_cursor
        if self.rf_metadata is not None:
            payload["rf_metadata"] = self.rf_metadata
        if self.receipt is not None:
            payload["receipt"] = self.receipt
        return payload


# ---------------------------------------------------------------------------
# Kind projector seam (KMCP-2.1 seam; KMCP-3.1..3.3 implement it — this
# module never implements a projection itself)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KindSearchPage:
    """One kind projector's page of results.

    Internal seam type (not itself a frozen schema shape). ``truncated``
    reports only whether THIS projector found more than it returned for its
    own kind — cross-kind cursor/merge semantics belong to the P3 KMCP-3.4
    composer, not to an individual projector.
    """

    items: tuple[RfKnowledgeSearchResultItem, ...] = field(default_factory=tuple)
    truncated: bool = False


class KindProjector(Protocol):
    """P3 projection contract for one knowledge kind (KMCP-2.1 seam).

    A concrete projector (KMCP-3.1..3.3) resolves a governed read authority
    (:mod:`catalog_service`, :mod:`assertion_catalog`, :mod:`export_service`,
    :mod:`builder_service`) into allowlisted
    :class:`RfKnowledgeSearchResultItem` / :class:`RfKnowledgeDocument`
    values AFTER policy (invariant 3) has already filtered the underlying
    records — this Protocol carries no policy logic of its own.

    Implementations MUST raise :class:`KnowledgeDenied` (never return a
    partial/null-valued document) for any id that is unknown, hidden,
    cross-workspace, or rights-denied, and MUST NOT rebuild, migrate, or
    otherwise write to the read authority they wrap (invariant 2) — a
    missing/stale index resolves to :class:`KnowledgeDenied`, exactly like
    every other denial.
    """

    def search(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        limit: int,
        cursor: str | None,
    ) -> KindSearchPage:
        ...

    def fetch(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None = None,
    ) -> RfKnowledgeDocument:
        ...


_PROJECTOR_REGISTRY: dict[str, KindProjector] = {}


def register_projector(kind: str, projector: KindProjector) -> None:
    """Register a P3 kind projector.

    ``kind`` must be one of :data:`KNOWLEDGE_KINDS` — the SAME five-kind
    vocabulary the frozen P1 schemas close their ``kind`` enum to; no other
    string is ever accepted, so a typo or an extra "helper" kind can never
    silently register.
    """

    if kind not in KNOWLEDGE_KINDS:
        raise KnowledgeRequestError("unknown_knowledge_kind")
    _PROJECTOR_REGISTRY[kind] = projector


def unregister_projector(kind: str) -> None:
    """Remove a registered projector; a no-op if none is registered (test helper)."""

    _PROJECTOR_REGISTRY.pop(kind, None)


def registered_kinds() -> tuple[str, ...]:
    """Kinds with a live projector, in :data:`KNOWLEDGE_KINDS` order."""

    return tuple(kind for kind in KNOWLEDGE_KINDS if kind in _PROJECTOR_REGISTRY)


# ---------------------------------------------------------------------------
# P3 projection helpers (KMCP-3.1/3.2 shared) -- pure functions, no I/O
# ---------------------------------------------------------------------------


def _truncate_title(value: str) -> str:
    """Bound to :data:`TITLE_MAX_LENGTH`; never emit an empty title."""

    cleaned = value.strip() or "untitled"
    return cleaned[:TITLE_MAX_LENGTH]


def _truncate_snippet(value: str) -> str:
    """Bound to :data:`SNIPPET_MAX_LENGTH` (invariant 7)."""

    return value[:SNIPPET_MAX_LENGTH]


def _truncate_text(value: str) -> tuple[str, bool]:
    """Bound untrusted document text to the fixed operational caps (invariant 7).

    Enforces both the codepoint cap (:data:`DOCUMENT_MAX_TEXT_CODEPOINTS`,
    what the frozen schema's own ``maxLength`` can express) and the tighter
    UTF-8 byte cap (:data:`DOCUMENT_MAX_TEXT_BYTES`, the real operational
    limit -- a codepoint-bounded string can still exceed it). Returns
    ``(possibly-truncated text, was_truncated)``.
    """

    truncated = False
    if len(value) > DOCUMENT_MAX_TEXT_CODEPOINTS:
        value = value[:DOCUMENT_MAX_TEXT_CODEPOINTS]
        truncated = True
    encoded = value.encode("utf-8")
    if len(encoded) > DOCUMENT_MAX_TEXT_BYTES:
        value = encoded[:DOCUMENT_MAX_TEXT_BYTES].decode("utf-8", errors="ignore")
        truncated = True
    return value, truncated


def _public_locator_url(value: Any) -> str | None:
    """Return ``value`` iff it is an ``http(s)`` URL string; else ``None``.

    The single path-stripping gate every P3 projector routes a source/edition
    locator through before it can ever become ``original_source_url``. A raw
    filesystem path -- a source card's un-resolved local ``url``, or an
    assertion edition's sibling ``retrieval_locator.file_path`` -- never
    satisfies this and is silently omitted rather than passed through
    (invariant 7 / AC KMCP-4's "path-like values are omitted, never
    synthesized").
    """

    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _load_source_payload(raw: Any) -> dict[str, Any]:
    """Best-effort ``json.loads`` of a ``catalog_items.payload_json`` cell.

    Never raises -- a malformed/missing payload degrades to an empty dict
    (every field derived from it below is already optional).
    """

    if not isinstance(raw, str) or not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _stamped_clearance_candidates(*records: Any) -> list[dict[str, Any]]:
    """Filter *records* down to only those structurally carrying a clearance stamp.

    Mirrors ``services.export_service``/``services.catalog_service``'s
    identically-named helper (each module keeps its own small copy rather
    than importing another module's private name — the same self-contained
    convention this codebase already uses elsewhere, e.g.
    ``services.writeback._stamped_attribution_records``). A dict with no
    ``clearance`` dict key was never produced by
    ``services.clearance.stamp_taint()`` and must never be fed to
    :func:`~research_foundry.services.clearance.mediate_egress` under
    ``kind="source_attribution"`` — doing so would refuse every pre-existing
    catalog row, which predates clearance and cannot carry a stamp.
    """

    return [
        dict(record)
        for record in records
        if isinstance(record, Mapping) and isinstance(record.get(clearance.TAINT_KEY), dict)
    ]


def _knowledge_payload_candidates(payload: Any) -> list[Any]:
    """Every dict inside one deserialized source *payload* worth checking
    for a clearance stamp -- the payload itself plus each ``evidence_points``
    entry. Returns raw candidates, unfiltered — callers pass the result
    through :func:`_stamped_clearance_candidates` before mediating.
    """

    candidates: list[Any] = [payload]
    if isinstance(payload, Mapping):
        nested = payload.get("evidence_points")
        if isinstance(nested, list):
            candidates.extend(nested)
    return candidates


def _mediate_knowledge_payloads(*payloads: Any, paths: FoundryPaths, target: str) -> None:
    """Mediate every clearance-stamped record inside one or more catalog
    *payloads* (KMCP-3.1's own read of ``catalog_items.payload_json``,
    clearance-gates-v1 M5).

    ``SourceKindProjector`` deliberately reads ``payload_json`` via its own
    raw SQL + :func:`_load_source_payload` rather than
    ``catalog_service.search``/``catalog_service.get_item`` (see that
    class's docstring — those two are write-capable, this projector must
    never be), so ``catalog_service``'s own mediation at those two functions
    does NOT cover this path. This IS the same chokepoint for both transports
    this class serves (Knowledge MCP stdio and the ``/knowledge/*`` HTTP
    surface both call through ``KnowledgeAccessService`` -> this projector),
    so one insertion point here suffices for both — see this module's other
    ``KindProjector`` implementations (``AssertionKindProjector``,
    ``ReportKindProjector``) for the two kinds that do NOT route through one
    of clearance-gates-v1 M5's four owned files and are therefore explicitly
    OUT of this milestone's scope.

    ``paths`` is REQUIRED and keyword-only (M5 gate finding: "mediation loses
    the caller's workspace context"). Callers pass their own ``self.paths`` --
    the SAME ``FoundryPaths`` whose ``catalog_items`` rows they just read via
    :func:`catalog_service.query_only_connection` -- so the gate registry
    consulted is that workspace's ``config/clearance_gates.yaml``. Before this
    was mandatory it was omitted entirely, so a ``KnowledgeAccessService``
    constructed for a non-default workspace mediated against
    ``FoundryPaths.discover()`` (the process CWD) instead: source text could
    leave through the Knowledge MCP stdio surface or ``/knowledge/*`` HTTP
    despite the reading workspace's own gate denying it, while the control
    reported success. Required rather than defaulted so the silent-discovery
    fallback cannot be reintroduced without the call failing loudly.

    Every caller has ``self.paths`` in scope (both projectors set it in
    ``__init__``), so no site here needs to fall back to discovery.
    """

    candidates: list[Any] = []
    for payload in payloads:
        candidates.extend(_knowledge_payload_candidates(payload))
    clearance.mediate_egress(
        _stamped_clearance_candidates(*candidates),
        kind="source_attribution",
        target_scope="redistribution",
        target=target,
        paths=paths,
    )


def _allowed_source_evidence_points(
    payload: Mapping[str, Any],
    threshold_rank: int,
    *,
    limit: int = SOURCE_EVIDENCE_POINTS_MAX,
) -> list[dict[str, Any]]:
    """Allowlisted, bounded, threshold-filtered evidence points for one source payload.

    Mirrors catalog_service's own per-point ``sensitivity_rank`` floor: a
    point whose OWN rank exceeds ``threshold_rank`` is OMITTED outright
    (never redacted with a marker) -- defense in depth on top of the
    catalog-item-level floor (``max(run_rank, point_ranks)``) that should
    already make an over-threshold point unreachable whenever the item
    itself is visible (invariant 3: never derive a field from a record --
    or a point within one -- that policy has not already cleared). Every
    surfaced point is allowlisted to exactly ``claim_id``/``relation``/
    ``quote``/``summary`` -- no raw locator or path field.
    """

    raw_points = payload.get("evidence_points")
    if not isinstance(raw_points, list):
        return []
    allowed: list[dict[str, Any]] = []
    for point in raw_points:
        if not isinstance(point, dict):
            continue
        point_rank = point.get("sensitivity_rank")
        if isinstance(point_rank, int) and point_rank > threshold_rank:
            continue
        quote_text = point.get("quote")
        summary_text = point.get("summary")
        allowed.append(
            {
                "claim_id": point.get("claim_id"),
                "relation": point.get("relation"),
                "quote": _truncate_snippet(str(quote_text)) if quote_text else None,
                "summary": _truncate_snippet(str(summary_text)) if summary_text else None,
            }
        )
        if len(allowed) >= limit:
            break
    return allowed


def _record_sensitivity_rank(label: Any) -> int:
    """Fail-closed sensitivity rank for an on-disk record's own label.

    Mirrors ``api.routers.reports._sensitivity_rank`` /
    ``catalog_service``'s rank lookup: an unknown, missing, or malformed
    label ranks STRICTER than every known level (never a wildcard, never
    silently passes a threshold gate) -- invariant 3. Shared by
    :class:`ReportKindProjector` and :class:`RunKindProjector`, whose
    backing read authorities (:mod:`builder_service`, :mod:`export_service`)
    apply the workspace-scope gate on their own but do not themselves apply
    this sensitivity-ceiling gate to the RECORD itself (only, in
    ``export_run``'s case, to per-claim text) -- this projector-level check
    is what closes that gap.
    """

    return SENSITIVITY_ORDER.get(str(label), len(SENSITIVITY_ORDER))


def _report_kind_for_status(status: Any) -> str:
    """Resolve a Report Builder draft's CURRENT ``status`` to one of the two
    report knowledge kinds (KMCP-OQ-2 resolution).

    ``report_draft`` and ``report_final`` are the SAME underlying
    ``builder_service`` draft entity (one ``report_draft_id``), read through
    the SAME gate, distinguished only by this lifecycle field at read
    time -- never stored twice, never merged into one ambiguous "report"
    kind. :data:`REPORT_FINAL_STATUSES` (``published``/``archived``) resolve
    to ``report_final`` (promoted); every other status -- ``draft``,
    ``verified``, or an unrecognized/missing value -- resolves to
    ``report_draft`` (still under active composition/review).
    """

    return "report_final" if status in REPORT_FINAL_STATUSES else "report_draft"


def _paginate_document_text(full_text: str, cursor: str | None) -> tuple[str, str | None, bool]:
    """Deterministic byte-offset pagination of untrusted document text (KMCP-3.4).

    Shared by every concrete :class:`KindProjector`'s ``fetch`` so a caller
    pages through ANY kind's oversized document through the identical
    contract. ``full_text`` is first bounded to
    :data:`DOCUMENT_MAX_TEXT_CODEPOINTS` (the schema's own ``maxLength``),
    then windowed to :data:`DOCUMENT_MAX_TEXT_BYTES` UTF-8 bytes per page,
    starting at the byte offset ``cursor`` encodes (decimal string; ``None``
    means offset 0, the first page). Returns
    ``(page_text, next_cursor, truncated)`` where ``next_cursor`` is the
    decimal offset of the next unread byte, or ``None`` once the final page
    has been returned. Deterministic and pure (no I/O, no clock) -- the SAME
    ``(full_text, cursor)`` pair always yields the SAME page, which is what
    makes "same snapshot replays byte-equivalent" (KMCP-3.4) provable.

    Raises :class:`KnowledgeRequestError` for a malformed or out-of-range
    cursor rather than silently clamping it -- defense in depth; a caller
    that mangles its own previously-issued cursor gets a typed error, not a
    silently wrong page.
    """

    if len(full_text) > DOCUMENT_MAX_TEXT_CODEPOINTS:
        full_text = full_text[:DOCUMENT_MAX_TEXT_CODEPOINTS]
    encoded = full_text.encode("utf-8")
    if cursor is None:
        offset = 0
    else:
        try:
            offset = int(cursor)
        except (TypeError, ValueError) as exc:
            raise KnowledgeRequestError("invalid_cursor") from exc
        if offset < 0 or offset > len(encoded):
            raise KnowledgeRequestError("invalid_cursor")
    window = encoded[offset : offset + DOCUMENT_MAX_TEXT_BYTES]
    page_text = window.decode("utf-8", errors="ignore")
    next_offset = offset + len(window)
    truncated = next_offset < len(encoded)
    next_cursor = str(next_offset) if truncated else None
    return page_text, next_cursor, truncated


def _canonical_json(payload: Mapping[str, Any]) -> str:
    """Same canonical-JSON convention every DTO in this repo already uses
    (``assertion_identity.canonical_source_assertion_json`` and the P1
    schemas' dual-encoding rule) -- reused here, not reinvented, for the
    receipt's own hash input."""

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _utc_now_iso() -> str:
    """Current UTC instant as ``YYYY-MM-DDTHH:MM:SSZ`` -- the ONE field on a
    receipt that legitimately varies between two calls against the same
    snapshot (KMCP-3.4); every other receipt field is a pure function of the
    request/context/result and replays byte-identically."""

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request_context_hash(context: KnowledgeAccessContext, request_key: Mapping[str, Any]) -> str:
    """One-way SHA-256 hex digest over the resolved, normalized request +
    policy context (KMCP-OQ-4's frozen field list) -- never the literal
    query/id/identity itself, only their hash. ``request_key`` carries the
    per-call-shape fields (query/id, validated filters, cursor); this
    function folds in the caller-independent policy context
    (tool/workspace/sensitivity-ceiling/policy-version) that is common to
    every receipt so no call site has to repeat it."""

    normalized = {
        "tool": context.tool,
        "workspace_id": context.workspace_id,
        "sensitivity_ceiling": context.sensitivity_ceiling,
        "policy_version": KNOWLEDGE_POLICY_VERSION,
        **request_key,
    }
    return hashlib.sha256(_canonical_json(normalized).encode("utf-8")).hexdigest()


def _build_receipt(
    context: KnowledgeAccessContext,
    *,
    request_key: Mapping[str, Any],
    returned_ids: Sequence[str],
    results_max: int,
    truncated: bool,
    text_bytes_returned: int | None = None,
    text_bytes_max: int | None = None,
    correlation_ref: str | None = None,
) -> dict[str, Any]:
    """Build one caller-carried, non-persisted RF activity receipt (KMCP-OQ-4,
    KMCP-3.4) -- ``knowledge_activity_receipt.schema.yaml``-shaped.

    Never written to disk/DB/log/audit store by this function or its
    callers (``persisted`` is hard-pinned ``False``); never carries a
    total-candidate, denied, or hidden count (KMCP-OQ-4's "no denied
    membership" default) -- ``returned_ids``/``bounds`` describe ONLY what
    the accompanying response already returned to this same caller.
    """

    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "knowledge_activity_receipt",
        "tool": context.tool,
        "generated_at": _utc_now_iso(),
        "persisted": False,
        "request_context_hash": _request_context_hash(context, request_key),
        "policy_version": KNOWLEDGE_POLICY_VERSION,
        "returned_ids": list(returned_ids),
        "bounds": {
            "results_returned": len(returned_ids),
            "results_max": results_max,
            "text_bytes_returned": text_bytes_returned,
            "text_bytes_max": text_bytes_max,
            "truncated": truncated,
        },
    }
    if correlation_ref is not None:
        receipt["correlation_ref"] = correlation_ref
    return receipt


# ---------------------------------------------------------------------------
# Concrete KindProjector implementations (KMCP-3.1, KMCP-3.2)
# ---------------------------------------------------------------------------


class SourceKindProjector:
    """KMCP-3.1: governed ``source`` catalog projection.

    Resolves rows from :mod:`catalog_service`'s ``catalog_items`` table
    through its read-only seam (:func:`catalog_service.is_catalog_available`
    / :func:`catalog_service.query_only_connection`) -- NEVER
    :func:`catalog_service.search`/:func:`catalog_service.get_item` (both
    write-capable via ``_connect``/``_db``, which may lazily create/migrate
    ``catalog.db`` -- invariant 2). The sensitivity ceiling and, when
    WKSP-304 isolation is active, the workspace scope are folded directly
    into the SQL ``WHERE`` clause, so a hidden row is never even fetched,
    let alone used to derive a snippet/title/URL/provenance field
    (invariant 3).

    Allowlists title, an ``http(s)``-only locator URL (never the raw
    source-card ``url`` when it is a filesystem path -- see
    :func:`_public_locator_url`), trust label, permitted evidence snippets
    (see :func:`_allowed_source_evidence_points`), and provenance IDs (run
    id, source-card local ref, catalog item id) into the shared
    :class:`RfKnowledgeDocument`/:class:`RfKnowledgeSearchResultItem` shapes.
    """

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self.paths = paths or FoundryPaths.discover()

    def _where_clause(self, context: KnowledgeAccessContext) -> tuple[str, list[Any]]:
        where = ["item_type = 'source'", "sensitivity_rank <= ?"]
        params: list[Any] = [context.sensitivity_rank]
        if context.identity is not None and resolve_workspace_isolation_active(self.paths):
            where.append("workspace_id = ?")
            params.append(context.workspace_id)
        return " AND ".join(where), params

    def search(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        limit: int,
        cursor: str | None,
    ) -> KindSearchPage:
        if not catalog_service.is_catalog_available(self.paths):
            return KindSearchPage(items=(), truncated=False)
        where_sql, params = self._where_clause(context)
        try:
            with catalog_service.query_only_connection(self.paths) as conn:
                rows = conn.execute(
                    "SELECT catalog_item_id, title, payload_json FROM catalog_items "
                    f"WHERE {where_sql} AND search_text LIKE ? "
                    "ORDER BY catalog_item_id LIMIT ?",
                    [*params, f"%{query.lower()}%", limit],
                ).fetchall()
        except catalog_service.CatalogUnavailable:
            return KindSearchPage(items=(), truncated=False)

        # clearance-gates-v1 M5: mediate every row's raw payload BEFORE
        # deriving any search-result field from it (design invariant 4).
        # All-or-nothing across the whole page — see _mediate_knowledge_
        # payloads' docstring for why this path needs its own call
        # independent of catalog_service.search()'s identical-in-spirit one.
        # `paths=self.paths` threads THIS projector's workspace (M5 gate
        # finding): `rows` came from self.paths' catalog.db via the
        # query_only_connection above, so the gate registry consulted must be
        # that workspace's, never the process CWD's.
        _mediate_knowledge_payloads(
            *(_load_source_payload(row["payload_json"]) for row in rows),
            paths=self.paths,
            target="knowledge_access.source.search",
        )

        items: list[RfKnowledgeSearchResultItem] = []
        for row in rows:
            payload = _load_source_payload(row["payload_json"])
            allowed = _allowed_source_evidence_points(payload, context.sensitivity_rank, limit=1)
            snippet_source = None
            if allowed:
                snippet_source = allowed[0]["summary"] or allowed[0]["quote"]
            item_id = f"rfk:v1:source:{row['catalog_item_id']}"
            items.append(
                RfKnowledgeSearchResultItem(
                    id=item_id,
                    title=_truncate_title(str(row["title"] or row["catalog_item_id"])),
                    url=build_local_resource_url(item_id, origin=_LOCAL_ORIGIN),
                    kind="source",
                    snippet=_truncate_snippet(str(snippet_source)) if snippet_source else None,
                )
            )
        return KindSearchPage(items=tuple(items), truncated=len(rows) >= limit)

    def fetch(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None = None,
    ) -> RfKnowledgeDocument:
        opaque = knowledge_id.rsplit(":", 1)[-1]
        if not catalog_service.is_catalog_available(self.paths):
            raise KnowledgeDenied("projection_unavailable")
        where_sql, params = self._where_clause(context)
        try:
            with catalog_service.query_only_connection(self.paths) as conn:
                row = conn.execute(
                    f"SELECT * FROM catalog_items WHERE catalog_item_id = ? AND {where_sql}",
                    [opaque, *params],
                ).fetchone()
        except catalog_service.CatalogUnavailable as exc:
            raise KnowledgeDenied("projection_unavailable") from exc
        if row is None:
            raise KnowledgeDenied("not_found")

        payload = _load_source_payload(row["payload_json"])
        # clearance-gates-v1 M5: mediate BEFORE deriving any document field
        # (text, evidence_points, rf_metadata) from the raw payload.
        # `paths=self.paths` threads THIS projector's workspace (M5 gate
        # finding) — `row` came from self.paths' catalog.db above.
        _mediate_knowledge_payloads(
            payload, paths=self.paths, target="knowledge_access.source.fetch"
        )
        evidence_points = _allowed_source_evidence_points(payload, context.sensitivity_rank)
        title = _truncate_title(str(row["title"] or opaque))
        body_parts = [title]
        for point in evidence_points:
            if point["quote"]:
                body_parts.append(point["quote"])
            if point["summary"]:
                body_parts.append(point["summary"])
        text, next_cursor, truncated = _paginate_document_text("\n\n".join(body_parts), cursor)

        rf_metadata: dict[str, Any] = {
            "source_type": payload.get("source_type"),
            "trust": row["trust_label"] or payload.get("trust"),
            "evidence_points": evidence_points,
            "provenance": {
                "catalog_item_id": row["catalog_item_id"],
                "run_id": row["run_id"],
                "source_card_id": row["local_ref"],
            },
        }
        return RfKnowledgeDocument(
            id=knowledge_id,
            title=title,
            url=build_local_resource_url(knowledge_id, origin=_LOCAL_ORIGIN),
            kind="source",
            text=text,
            original_source_url=_public_locator_url(payload.get("url")),
            truncated=truncated,
            next_cursor=next_cursor,
            rf_metadata=rf_metadata,
        )


class AssertionKindProjector:
    """KMCP-3.2: exact ``assertion`` packet/lineage projection.

    Resolves through :class:`assertion_catalog.AssertionCatalog`'s
    non-rebuilding seam (``search_read_only``/``packet_read_only``) -- NEVER
    ``search``/``packet``/``rebuild`` (rebuild-on-miss or write-capable;
    invariant 2). Only ``lifecycle_state == "eligible"`` packets are
    visible; every other cause -- stale/blocked lifecycle, rights-denied, a
    missing projection, a cross-workspace id, or a genuinely unknown id --
    raises the SAME :class:`KnowledgeDenied` (KMCP-OQ-1's
    "indistinguishable in shape from hidden"). ``search_read_only`` itself
    already excludes non-``"eligible"`` records from its own result set; the
    ``lifecycle_state`` re-check in :meth:`fetch` below is defense in depth
    for the same reason :meth:`AssertionCatalog.packet_read_only` does not
    apply that filter on its own.

    Allowlists edition/passage/version/lifecycle/evaluation/rights fields
    within caps and NEVER surfaces
    ``source_edition.retrieval_locator.file_path`` (a raw filesystem path)
    -- only its sibling ``retrieval_locator.url``, and only when that is
    itself an ``http(s)`` locator (see :func:`_public_locator_url`).
    """

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self.catalog = AssertionCatalog(paths or FoundryPaths.discover())

    def search(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        limit: int,
        cursor: str | None,
    ) -> KindSearchPage:
        if context.identity is None or not context.workspace_id:
            return KindSearchPage(items=(), truncated=False)
        result = self.catalog.search_read_only(
            identity=context.identity, query=query, limit=limit, cursor=cursor
        )
        if result["denial_reason"] is not None:
            return KindSearchPage(items=(), truncated=False)

        items: list[RfKnowledgeSearchResultItem] = []
        for summary in result["items"]:
            assertion_id = summary["assertion_id"]
            try:
                packet = self.catalog.packet_read_only(assertion_id, identity=context.identity)
            except (AssertionCatalogDenied, AssertionCatalogUnavailable):
                continue
            if packet is None or packet.get("lifecycle_state") != "eligible":
                continue
            assertion = packet.get("assertion")
            assertion = assertion if isinstance(assertion, dict) else {}
            text_source = str(assertion.get("assertion_text") or assertion_id)
            item_id = f"rfk:v1:assertion:{assertion_id}"
            items.append(
                RfKnowledgeSearchResultItem(
                    id=item_id,
                    title=_truncate_title(text_source),
                    url=build_local_resource_url(item_id, origin=_LOCAL_ORIGIN),
                    kind="assertion",
                    snippet=_truncate_snippet(text_source),
                )
            )
        return KindSearchPage(items=tuple(items), truncated=result["next_cursor"] is not None)

    def fetch(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None = None,
    ) -> RfKnowledgeDocument:
        opaque = knowledge_id.rsplit(":", 1)[-1]
        try:
            packet = self.catalog.packet_read_only(opaque, identity=context.identity)
        except (AssertionCatalogDenied, AssertionCatalogUnavailable) as exc:
            raise KnowledgeDenied(exc.reason_code) from exc
        if packet is None:
            raise KnowledgeDenied("not_found")
        if packet.get("lifecycle_state") != "eligible":
            raise KnowledgeDenied("not_eligible")

        assertion = packet.get("assertion")
        assertion = assertion if isinstance(assertion, dict) else {}
        passage = packet.get("passage")
        passage = passage if isinstance(passage, dict) else {}
        edition = packet.get("source_edition")
        edition = edition if isinstance(edition, dict) else {}
        retrieval_locator = edition.get("retrieval_locator")
        retrieval_locator = retrieval_locator if isinstance(retrieval_locator, dict) else {}

        body = str(assertion.get("assertion_text") or passage.get("normalized_text") or opaque)
        title = _truncate_title(body)
        text, next_cursor, truncated = _paginate_document_text(body, cursor)

        evaluations = [
            {
                "evaluation_id": evaluation.get("evaluation_id"),
                "evaluation_kind": evaluation.get("evaluation_kind"),
                "verdict": evaluation.get("verdict"),
            }
            for evaluation in (packet.get("evaluations") or [])
            if isinstance(evaluation, dict)
        ][:ASSERTION_EVALUATIONS_MAX]

        rf_metadata: dict[str, Any] = {
            "assertion_version": packet.get("assertion_version"),
            "lifecycle_state": packet.get("lifecycle_state"),
            "qualifiers": assertion.get("qualifiers") or {},
            "source_edition": {
                "source_edition_id": edition.get("source_edition_id"),
                "media_type": edition.get("media_type"),
                "access_scope": edition.get("access_scope"),
                "captured_at": edition.get("captured_at"),
            },
            "passage": {"passage_id": passage.get("passage_id")},
            "evaluations": evaluations,
            "rights_decision": packet.get("rights_decision"),
            "provenance": {
                "assertion_id": packet.get("assertion_id"),
                "source_edition_id": edition.get("source_edition_id"),
                "passage_id": passage.get("passage_id"),
                "run_uses": list(packet.get("run_uses") or [])[:ASSERTION_RUN_USES_MAX],
            },
        }
        return RfKnowledgeDocument(
            id=knowledge_id,
            title=title,
            url=build_local_resource_url(knowledge_id, origin=_LOCAL_ORIGIN),
            kind="assertion",
            text=text,
            original_source_url=_public_locator_url(retrieval_locator.get("url")),
            truncated=truncated,
            next_cursor=next_cursor,
            rf_metadata=rf_metadata,
        )


class ReportKindProjector:
    """KMCP-3.3: governed ``report_draft``/``report_final`` projection.

    Resolves through :mod:`builder_service`'s existing file-canonical READ
    seam (:func:`builder_service.list_drafts` / :func:`builder_service.load_draft`
    / :func:`builder_service.export_markdown`) -- NEVER a mutator; this class
    calls none of ``create_draft*``/``add_block``/``update_block``/
    ``delete_draft``/etc. (invariant 2). ``load_draft`` applies ONLY the
    WKSP-304 workspace-scope gate on its own; this projector ADDS the
    sensitivity-ceiling gate on top (:func:`_record_sensitivity_rank`,
    mirroring ``api/routers/reports.py``'s own R2 fix over the identical read
    paths) before deriving a title/snippet/text/rf_metadata field for ANY
    draft (invariant 3).

    ``report_draft`` and ``report_final`` are the SAME underlying draft
    entity -- one instance is registered per target kind (``target_kind``),
    and :func:`_report_kind_for_status` resolves which of the two a given
    draft's CURRENT ``status`` belongs to at read time (KMCP-OQ-2). Fetching
    a draft by an id whose kind segment does not match its current status
    (e.g. a still-``draft`` record addressed as ``report_final``) denies with
    the SAME generic shape as a genuinely missing id -- never a distinct
    "wrong kind" signal (KMCP-OQ-1's "indistinguishable in shape from
    hidden").

    Allowlists title, lifecycle/audience/origin fields, block/claim-link/
    source-link COUNTS (never raw block markdown beyond the rendered body
    text itself), and provenance IDs into the shared
    :class:`RfKnowledgeDocument`/:class:`RfKnowledgeSearchResultItem` shapes
    -- never ``workspace_id``, ``created_by``, ``updated_by``, or
    ``project_id`` (operator/identity fields, not needed by any allowlisted
    field here) and never a raw filesystem path (``export_markdown`` never
    emits one).
    """

    def __init__(self, paths: FoundryPaths | None = None, *, target_kind: str) -> None:
        if target_kind not in ("report_draft", "report_final"):
            raise KnowledgeRequestError("unknown_knowledge_kind")
        self.paths = paths or FoundryPaths.discover()
        self.target_kind = target_kind

    def search(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        limit: int,
        cursor: str | None,
    ) -> KindSearchPage:
        query_lower = query.lower()
        candidates: list[dict[str, Any]] = []
        for summary in builder_service.list_drafts(self.paths, identity=context.identity):
            if _record_sensitivity_rank(summary.get("sensitivity")) > context.sensitivity_rank:
                continue
            if _report_kind_for_status(summary.get("status")) != self.target_kind:
                continue
            title = str(summary.get("title") or summary["report_draft_id"])
            if query_lower not in title.lower():
                continue
            candidates.append(summary)

        truncated = len(candidates) > limit
        items: list[RfKnowledgeSearchResultItem] = []
        for summary in candidates[:limit]:
            report_draft_id = summary["report_draft_id"]
            item_id = f"rfk:v1:{self.target_kind}:{report_draft_id}"
            status = summary.get("status")
            items.append(
                RfKnowledgeSearchResultItem(
                    id=item_id,
                    title=_truncate_title(str(summary.get("title") or report_draft_id)),
                    url=build_local_resource_url(item_id, origin=_LOCAL_ORIGIN),
                    kind=self.target_kind,
                    snippet=_truncate_snippet(f"status: {status}") if status else None,
                )
            )
        return KindSearchPage(items=tuple(items), truncated=truncated)

    def fetch(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None = None,
    ) -> RfKnowledgeDocument:
        report_draft_id = knowledge_id.rsplit(":", 1)[-1]
        try:
            draft = builder_service.load_draft(self.paths, report_draft_id, identity=context.identity)
        except (NotFoundError, builder_service.BuilderError) as exc:
            raise KnowledgeDenied("not_found") from exc
        if _report_kind_for_status(draft.get("status")) != self.target_kind:
            raise KnowledgeDenied("not_found")
        if _record_sensitivity_rank(draft.get("sensitivity")) > context.sensitivity_rank:
            raise KnowledgeDenied("not_found")

        title = _truncate_title(str(draft.get("title") or report_draft_id))
        try:
            rendered = builder_service.export_markdown(
                self.paths, report_draft_id, identity=context.identity
            )
        except (NotFoundError, builder_service.BuilderError) as exc:
            raise KnowledgeDenied("not_found") from exc
        _frontmatter, body = split_frontmatter(rendered)
        text, next_cursor, truncated = _paginate_document_text(body, cursor)

        rf_metadata: dict[str, Any] = {
            "status": draft.get("status"),
            "audience": draft.get("audience"),
            "origin": draft.get("origin"),
            "block_count": len(draft.get("blocks") or []),
            "claim_link_count": len(draft.get("claim_links") or []),
            "source_link_count": len(draft.get("source_links") or []),
            "provenance": {
                "report_draft_id": report_draft_id,
                "source_run_id": draft.get("source_run_id"),
            },
        }
        return RfKnowledgeDocument(
            id=knowledge_id,
            title=title,
            url=build_local_resource_url(knowledge_id, origin=_LOCAL_ORIGIN),
            kind=self.target_kind,
            text=text,
            truncated=truncated,
            next_cursor=next_cursor,
            rf_metadata=rf_metadata,
        )


class RunKindProjector:
    """KMCP-3.3: governed ``run`` summary/detail projection.

    Resolves through :mod:`export_service`'s existing run read model
    (:func:`export_service.list_runs` / :func:`export_service.export_run`) --
    the SAME DF-004 workspace-scope gate (``_run_read_allowed``) those already
    apply. ``export_run``'s own ``sensitivity_threshold`` argument only
    redacts per-claim quote/summary text at or below the given rank; it does
    NOT by itself hide a run whose OWN declared ``sensitivity`` exceeds that
    rank, so this projector reproduces the same no-existence-leak gate
    ``api/routers/runs.py``'s ``_enforce_existence_gate`` layers on top of
    ``export_run()`` before deriving a title/snippet/text/rf_metadata field
    for ANY run (invariant 3).

    Exposes a bounded, synthesized run SUMMARY as ``text`` (status,
    sensitivity, claim counts, verification/governance verdicts, category/
    tags) -- never the run's own on-disk ``report_draft``/``report_final``
    markdown (those are the SEPARATE ``report_draft``/``report_final`` kinds,
    :class:`ReportKindProjector`) and never a raw artifact path (``export_run``
    itself never emits one -- see its own "path re-derivation" invariant).
    """

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self.paths = paths or FoundryPaths.discover()

    def search(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        limit: int,
        cursor: str | None,
    ) -> KindSearchPage:
        query_lower = query.lower()
        candidates: list[dict[str, Any]] = []
        for summary in list_runs(self.paths, identity=context.identity):
            if _record_sensitivity_rank(summary.get("sensitivity")) > context.sensitivity_rank:
                continue
            run_id = str(summary["run_id"])
            haystack_parts = [
                run_id,
                str(summary.get("intent_id") or ""),
                str(summary.get("category") or ""),
                " ".join(summary.get("tags") or []),
            ]
            if query_lower not in " ".join(haystack_parts).lower():
                continue
            candidates.append(summary)

        truncated = len(candidates) > limit
        items: list[RfKnowledgeSearchResultItem] = []
        for summary in candidates[:limit]:
            run_id = str(summary["run_id"])
            item_id = f"rfk:v1:run:{run_id}"
            title = _truncate_title(str(_title_from_slug(run_id) or run_id))
            status = summary.get("status_derived")
            items.append(
                RfKnowledgeSearchResultItem(
                    id=item_id,
                    title=title,
                    url=build_local_resource_url(item_id, origin=_LOCAL_ORIGIN),
                    kind="run",
                    snippet=_truncate_snippet(f"status: {status}") if status else None,
                )
            )
        return KindSearchPage(items=tuple(items), truncated=truncated)

    def fetch(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None = None,
    ) -> RfKnowledgeDocument:
        run_id = knowledge_id.rsplit(":", 1)[-1]
        try:
            data = export_run(
                self.paths,
                run_id,
                sensitivity_threshold=context.sensitivity_ceiling,
                identity=context.identity,
            )
        except ExportError as exc:
            raise KnowledgeDenied("not_found") from exc
        except clearance.ClearanceDenied as exc:
            # clearance-gates-v1 M5: export_run() now mediates every
            # citation's raw source-card record before projecting it
            # (export_service.py _resolve_source). Without this handler,
            # ClearanceDenied would propagate as an unmapped exception out
            # of this projector — mapped to KnowledgeDenied instead, this
            # class's own single bounded, no-existence-leak denial contract
            # (KnowledgeDenied's own docstring, AC KMCP-3) rather than a
            # bespoke shape.
            raise KnowledgeDenied("clearance_denied") from exc
        if data is None:
            # DF-004 workspace-scope denial (export_run returns None rather
            # than raising) -- same generic shape as a genuinely missing run.
            raise KnowledgeDenied("not_found")
        if _record_sensitivity_rank(data.get("sensitivity")) > context.sensitivity_rank:
            # No-existence-leak gate (mirrors routers/runs.py's own
            # _enforce_existence_gate): export_run()'s threshold arg only
            # redacted per-claim text, it never hid the run record itself.
            raise KnowledgeDenied("not_found")

        title = _truncate_title(str(data.get("title") or run_id))
        claim_counts = data.get("claim_counts") or {}
        governance = data.get("governance") or {}
        verification = data.get("verification") or {}
        tags = list(data.get("tags") or [])[:RUN_TAGS_MAX]
        summary_lines = [
            title,
            f"status: {data.get('status_derived')}",
            f"sensitivity: {data.get('sensitivity')}",
            f"claim_counts: {_canonical_json(claim_counts)}",
        ]
        text, next_cursor, truncated = _paginate_document_text("\n".join(summary_lines), cursor)

        rf_metadata: dict[str, Any] = {
            "status_derived": data.get("status_derived"),
            "sensitivity": data.get("sensitivity"),
            "claim_counts": claim_counts,
            "verification_passed": verification.get("passed"),
            "governance_verdict": governance.get("approved_for_writeback"),
            "category": data.get("category"),
            "tags": tags,
            "provenance": {
                "run_id": run_id,
                "intent_id": data.get("intent_id"),
            },
        }
        return RfKnowledgeDocument(
            id=knowledge_id,
            title=title,
            url=build_local_resource_url(knowledge_id, origin=_LOCAL_ORIGIN),
            kind="run",
            text=text,
            truncated=truncated,
            next_cursor=next_cursor,
            rf_metadata=rf_metadata,
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class KnowledgeAccessService:
    """Policy-first read service behind every Knowledge transport (KMCP-2.1).

    Every public method takes an already-resolved :class:`KnowledgeAccessContext`
    (never a raw identity/workspace argument) so policy resolution can never
    be skipped or duplicated per call site. This Phase P2 skeleton wires
    request validation, kind eligibility, and deterministic ordering around
    the :class:`KindProjector` registry; it never implements a domain
    projection itself (KMCP-3.1..3.4 do that in Phase P3) and never opens a
    database connection or writes a file (invariant 2).
    """

    def __init__(self, paths: FoundryPaths | None = None) -> None:
        self.paths = paths or FoundryPaths.discover()

    # -- core tools ----------------------------------------------------------

    def search_core(self, context: KnowledgeAccessContext, *, query: str) -> KnowledgeSearchResponse:
        """Frozen core ``search(query)`` (KMCP-1.2) — exactly one input field."""

        outcome = self._search(context, query=query, kinds=None, limit=CORE_SEARCH_MAX_RESULTS)
        items = tuple(
            KnowledgeSearchResultItem(id=item.id, title=item.title, url=item.url)
            for item in outcome.results[:CORE_SEARCH_MAX_RESULTS]
        )
        return KnowledgeSearchResponse(results=items)

    def fetch_core(self, context: KnowledgeAccessContext, *, knowledge_id: str) -> KnowledgeDocument:
        """Frozen core ``fetch(id)`` (KMCP-1.2) — exactly one input field.

        Raises :class:`KnowledgeDenied` for any id this context cannot
        resolve — never returns a partial/null-valued document (see
        ``knowledge_document.schema.yaml``'s header).
        """

        doc = self._fetch(context, knowledge_id=knowledge_id, cursor=None)
        if doc.text is None:
            # Defense in depth: a projector that denies should raise
            # KnowledgeDenied (see KindProjector's contract), never return a
            # document with no text — the frozen core FetchDTO requires it.
            raise KnowledgeDenied("document_incomplete")
        return KnowledgeDocument(id=doc.id, title=doc.title, text=doc.text, url=doc.url, metadata=None)

    # -- RF-extended tools -----------------------------------------------------

    def search_extended(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        kinds: Sequence[str] | None = None,
        limit: int = RF_SEARCH_DEFAULT_LIMIT,
        cursor: str | None = None,
        parent_run_ref: str | None = None,
        include_receipt: bool = False,
    ) -> RfKnowledgeSearchOutcome:
        """RF-extended ``rf_search`` (KMCP-FR-5) — filters/paging, plus the
        opt-in caller-carried receipt (KMCP-3.4, KMCP-OQ-4).

        ``include_receipt`` defaults to ``False`` — every KMCP-2.4/3.1/3.2
        caller that compares this method's return value against a bare
        ``RfKnowledgeSearchOutcome(results=..., next_cursor=..., truncated=...)``
        literal (``receipt`` implicitly ``None``) keeps passing unchanged.
        P4/P5 transports registering the actual ``rf_search`` tool pass
        ``True``. ``parent_run_ref`` is the optional caller-supplied
        correlation hint echoed into the receipt's ``correlation_ref`` when
        one is built — never used for anything else, carries no policy
        weight (see ``rf_search_request.parent_run_ref``'s own docstring).
        """

        outcome = self._search(context, query=query, kinds=kinds, limit=limit, cursor=cursor)
        if not include_receipt:
            return outcome
        receipt = _build_receipt(
            context,
            request_key={
                "query": query,
                "kinds": sorted(kinds) if kinds else None,
                "limit": self._resolve_limit(limit),
                "cursor": cursor,
            },
            returned_ids=[item.id for item in outcome.results],
            results_max=self._resolve_limit(limit),
            truncated=outcome.truncated,
            correlation_ref=parent_run_ref,
        )
        return replace(outcome, receipt=receipt)

    def fetch_extended(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None = None,
        parent_run_ref: str | None = None,
        include_receipt: bool = False,
    ) -> RfKnowledgeDocument:
        """RF-extended ``rf_fetch`` (KMCP-FR-5) — same denial contract as
        :meth:`fetch_core`, plus the opt-in caller-carried receipt (see
        :meth:`search_extended`'s docstring for the ``include_receipt`` /
        ``parent_run_ref`` contract, identical here)."""

        doc = self._fetch(context, knowledge_id=knowledge_id, cursor=cursor)
        if not include_receipt:
            return doc
        text_bytes_returned = len(doc.text.encode("utf-8")) if doc.text is not None else None
        receipt = _build_receipt(
            context,
            request_key={"id": knowledge_id, "cursor": cursor},
            returned_ids=[doc.id],
            results_max=1,
            truncated=bool(doc.truncated),
            text_bytes_returned=text_bytes_returned,
            text_bytes_max=DOCUMENT_MAX_TEXT_BYTES,
            correlation_ref=parent_run_ref,
        )
        return replace(doc, receipt=receipt)

    # -- shared implementation -------------------------------------------------

    def _validate_query(self, query: str) -> None:
        if not isinstance(query, str) or not 1 <= len(query) <= QUERY_MAX_LENGTH:
            raise KnowledgeRequestError("invalid_query")

    def _resolve_limit(self, limit: int) -> int:
        try:
            value = int(limit)
        except (TypeError, ValueError) as exc:
            raise KnowledgeRequestError("invalid_limit") from exc
        return max(1, min(value, RF_SEARCH_MAX_RESULTS))

    def _search(
        self,
        context: KnowledgeAccessContext,
        *,
        query: str,
        kinds: Sequence[str] | None,
        limit: int,
        cursor: str | None = None,
    ) -> RfKnowledgeSearchOutcome:
        """Policy/allowlist/ordering scaffold every kind's page is merged through.

        A kind with no registered :class:`KindProjector` — every kind, in
        this Phase P2 skeleton — contributes zero results and marks the
        outcome ``truncated`` only if a REGISTERED projector reported more
        than it returned; a missing projector is Phase P2's own exit
        condition ("missing projections fail typed/unavailable without
        writes"), never an error, and never causes a write of any kind.
        """

        self._validate_query(query)
        resolved_limit = self._resolve_limit(limit)
        candidates: list[RfKnowledgeSearchResultItem] = []
        truncated = False
        for kind in eligible_kinds(kinds):
            projector = _PROJECTOR_REGISTRY.get(kind)
            if projector is None:
                continue
            page = projector.search(context, query=query, limit=resolved_limit, cursor=None)
            candidates.extend(page.items)
            truncated = truncated or page.truncated
        candidates.sort(key=lambda item: deterministic_id_sort_key(item.id))
        bounded = tuple(candidates[:resolved_limit])
        return RfKnowledgeSearchOutcome(
            results=bounded,
            next_cursor=None,
            truncated=truncated or len(candidates) > resolved_limit,
        )

    def _fetch(
        self,
        context: KnowledgeAccessContext,
        *,
        knowledge_id: str,
        cursor: str | None,
    ) -> RfKnowledgeDocument:
        kind, _opaque = parse_knowledge_id(knowledge_id)
        if kind not in eligible_kinds():
            raise KnowledgeDenied("kind_not_eligible")
        projector = _PROJECTOR_REGISTRY.get(kind)
        if projector is None:
            # Phase P2 exit condition (see module docstring, invariant 2):
            # a missing projection denies safely, indistinguishable in shape
            # from "hidden" (KMCP-OQ-1) — never a rebuild, never a write.
            raise KnowledgeDenied("projection_unavailable")
        return projector.fetch(context, knowledge_id=knowledge_id, cursor=cursor)


__all__ = [
    "KNOWLEDGE_KINDS",
    "CORE_TOOL_NAMES",
    "RF_TOOL_NAMES",
    "TOOL_NAMES",
    "QUERY_MAX_LENGTH",
    "CORE_SEARCH_MAX_RESULTS",
    "RF_SEARCH_MAX_RESULTS",
    "RF_SEARCH_DEFAULT_LIMIT",
    "TITLE_MAX_LENGTH",
    "SNIPPET_MAX_LENGTH",
    "DOCUMENT_MAX_TEXT_CODEPOINTS",
    "DOCUMENT_MAX_TEXT_BYTES",
    "RETURNED_IDS_MAX",
    "LOCAL_URL_MAX_LENGTH",
    "SOURCE_EVIDENCE_POINTS_MAX",
    "ASSERTION_EVALUATIONS_MAX",
    "ASSERTION_RUN_USES_MAX",
    "RUN_TAGS_MAX",
    "KNOWLEDGE_POLICY_VERSION",
    "REPORT_FINAL_STATUSES",
    "KnowledgeAccessError",
    "KnowledgeRequestError",
    "KnowledgeInvariantError",
    "KnowledgeDenied",
    "parse_knowledge_id",
    "build_local_resource_url",
    "deterministic_id_sort_key",
    "KnowledgeAccessContext",
    "resolve_context",
    "eligible_kinds",
    "KnowledgeSearchResultItem",
    "KnowledgeSearchResponse",
    "RfKnowledgeSearchResultItem",
    "RfKnowledgeSearchOutcome",
    "KnowledgeDocument",
    "RfKnowledgeDocument",
    "KindSearchPage",
    "KindProjector",
    "register_projector",
    "unregister_projector",
    "registered_kinds",
    "SourceKindProjector",
    "AssertionKindProjector",
    "ReportKindProjector",
    "RunKindProjector",
    "KnowledgeAccessService",
]
