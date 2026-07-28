"""Unit tests for the RF Knowledge MCP service skeleton (KMCP-2.1) plus the
KMCP-2.4 core negative matrix.

The first half covers KMCP-2.1's own acceptance criteria: no transport/MCP
imports, the frozen tool/kind vocabularies, context resolution (local trust
vs. enforced identity), the opaque-id/local-URL helpers byte-identical to the
P1 schemas, deterministic ordering, the kind-projector registry seam, and
that every response DTO round-trips against the frozen schemas in
``schemas/``.

The second half (below the "KMCP-2.4: Core negative matrix" banner) proves
KMCP-2.4 itself: every core Knowledge read -- through the bare P2 skeleton
(no projector registered) AND through a test-only fake :class:`KindProjector`
wired to the REAL KMCP-2.2/2.3 non-writing seams
(:mod:`catalog_service`'s ``query_only_connection``/``is_catalog_available``
and :mod:`assertion_catalog`'s ``search_read_only``/``packet_read_only``) --
causes zero calls into every cache/index-rebuild/run-creation/source-creation/
audit-artifact/telemetry-artifact/provider-call/write function reachable from
those seams, a missing backing store denies typed/unavailable without ever
rebuilding it, an existing backing store's queries change zero files/bytes,
and every denial cause (missing, rights-denied, cross-workspace) collapses to
the SAME bounded, no-existence-leak shape.
"""

from __future__ import annotations

import ast
import inspect
import json
import socket
import sqlite3
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import assertion_catalog as assertion_catalog_module
from research_foundry.services import audit_service, builder_service, telemetry
from research_foundry.services import catalog_service as catalog_svc
from research_foundry.services import knowledge_access as ka
from research_foundry.services.assertion_catalog import (
    AssertionCatalog,
    AssertionCatalogDenied,
    AssertionCatalogUnavailable,
)
from research_foundry.yamlio import dump_yaml, load_yaml

# Sibling test modules, imported by name (not re-implemented) for their fixture
# builders -- same pattern as test_negative_write_path_consolidated.py's own
# `import tests.unit.test_rights_status_write_ceiling as p5_2`. `tests/unit`
# is a real package (`__init__.py` present), so this is a plain import, not a
# sys.path hack.
from tests.unit.test_assertion_catalog import _materialize
from tests.unit.test_catalog_service import _write_threshold, build_catalog_run
from tests.unit.test_export_service import build_run


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate WKSP-304 workspace isolation resolving active.

    Same convention as ``tests/test_workspace_isolation_enforcement.py``'s
    own helper of the identical name: monkeypatch
    :meth:`FoundryConfig.resolve_workspace_isolation_enforced` itself (the
    single shared resolver every one of ``builder_service._isolation_active``
    / ``export_service._run_read_allowed``'s lazy ``resolve_workspace_isolation_active``
    import ultimately calls), never a private per-module helper, so this
    exercises the real resolver's call contract identically for both.
    """

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


def _set_run_yaml_fields(paths: FoundryPaths, run_id: str, **fields: Any) -> None:
    """Test-only: directly mutate an already-built run's ``run.yaml`` fields.

    ``build_run`` (imported above) hardcodes ``sensitivity: "personal"`` and
    no ``workspace_id`` -- this mirrors this file's existing pattern of
    mutating a fixture's underlying store directly for test setup (e.g.
    ``test_source_projector_strips_filesystem_path_locator``'s raw SQL
    ``UPDATE``).
    """

    rp = paths.run_paths(run_id)
    data = load_yaml(rp.run_yaml)
    data.update(fields)
    dump_yaml(data, rp.run_yaml)


def _publish_draft(paths: FoundryPaths, report_draft_id: str, *, status: str) -> None:
    """Test-only: directly flip a Report Builder draft's on-disk ``status``.

    No ``builder_service`` mutator exists yet that transitions a draft to
    ``published``/``archived`` (the API's ``/publish-preview`` route is a
    fail-closed PREVIEW gate that deliberately persists nothing) -- this
    mirrors the same direct-fixture-mutation convention as
    :func:`_set_run_yaml_fields` above.
    """

    path = builder_service._draft_yaml_path(paths, report_draft_id)
    draft = load_yaml(path)
    draft["status"] = status
    dump_yaml(draft, path)


def _subschema(root_schema: dict[str, Any], def_name: str) -> dict[str, Any]:
    """Merge a ``$defs`` entry over the file root so internal ``$ref``s resolve.

    Mirrors ``tests/test_schema_validation.py``'s direct
    ``jsonschema.Draft202012Validator`` usage for cases with no top-level
    schema name of their own (this repo's ``SchemaRegistry`` has no
    cross-file ``$ref`` resolver — see ``knowledge_activity_receipt.schema.yaml``'s
    header).
    """

    merged = {**root_schema, **root_schema["$defs"][def_name]}
    merged["$defs"] = root_schema["$defs"]
    return merged


@pytest.fixture()
def registry() -> SchemaRegistry:
    return SchemaRegistry()


@pytest.fixture(autouse=True)
def _clean_projector_registry():
    """Every test starts and ends with an empty projector registry."""

    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


# ---------------------------------------------------------------------------
# Invariant 1: no transport/MCP imports
# ---------------------------------------------------------------------------


def test_module_has_no_transport_or_mcp_imports() -> None:
    source = inspect.getsource(ka)
    tree = ast.parse(source)
    forbidden = ("knowledge_mcp", "search_router", "fastmcp", "mcp", "starlette", "fastapi")
    module_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module_names.append(node.module)
    for name in module_names:
        lowered = name.lower()
        for banned in forbidden:
            assert banned not in lowered, f"forbidden transport import: {name}"


# ---------------------------------------------------------------------------
# Frozen vocabularies (decisions-block §0/§9.2)
# ---------------------------------------------------------------------------


def test_frozen_kind_and_tool_vocabularies() -> None:
    assert ka.KNOWLEDGE_KINDS == ("source", "assertion", "report_draft", "report_final", "run")
    assert ka.CORE_TOOL_NAMES == ("search", "fetch")
    assert ka.TOOL_NAMES == (
        "search",
        "fetch",
        "rf_search",
        "rf_fetch",
        "rf_source_get",
        "rf_assertion_get",
        "rf_report_get",
        "rf_run_get",
    )
    assert len(ka.TOOL_NAMES) == 8


# ---------------------------------------------------------------------------
# Context resolution (invariant 3)
# ---------------------------------------------------------------------------


def test_resolve_context_local_trust_has_no_workspace(tmp_foundry: FoundryPaths) -> None:
    context = ka.resolve_context(tmp_foundry, tool="search")
    assert context.identity is None
    assert context.workspace_id is None
    assert context.sensitivity_ceiling in ka.SENSITIVITY_ORDER


def test_resolve_context_enforced_identity_carries_workspace(tmp_foundry: FoundryPaths) -> None:
    identity = AuthIdentity("alice", "workspace-a", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)
    assert context.workspace_id == "workspace-a"
    assert context.tool == "rf_search"


def test_resolve_context_rejects_unknown_tool(tmp_foundry: FoundryPaths) -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka.resolve_context(tmp_foundry, tool="acquire_source")


def test_context_rejects_unknown_sensitivity_ceiling() -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka.KnowledgeAccessContext(identity=None, sensitivity_ceiling="ultra_secret", tool="search")


def test_resolve_context_never_widens_via_explicit_override(tmp_foundry: FoundryPaths) -> None:
    context = ka.resolve_context(tmp_foundry, tool="search", sensitivity_threshold="personal")
    assert context.sensitivity_ceiling == "personal"
    assert context.sensitivity_rank == 1


# ---------------------------------------------------------------------------
# Opaque ID / local URL helpers (invariant 6)
# ---------------------------------------------------------------------------


def test_parse_knowledge_id_round_trip() -> None:
    kind, opaque = ka.parse_knowledge_id("rfk:v1:source:abc-123")
    assert kind == "source"
    assert opaque == "rfk:v1:source:abc-123"


@pytest.mark.parametrize(
    "value",
    [
        "not-an-id",
        "rfk:v1:bogus_kind:abc",
        "rfk:v2:source:abc",
        "rfk:v1:source:has a space",
        "x" * 201,
    ],
)
def test_parse_knowledge_id_rejects_malformed(value: str) -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka.parse_knowledge_id(value)


def test_build_local_resource_url_matches_frozen_pattern() -> None:
    url = ka.build_local_resource_url("rfk:v1:report_final:rep-1", origin="http://127.0.0.1:7432")
    assert url == "http://127.0.0.1:7432/api/knowledge/v1/fetch/rfk%3Av1%3Areport_final%3Arep-1"


def test_build_local_resource_url_rejects_non_loopback_origin() -> None:
    with pytest.raises(ka.KnowledgeInvariantError):
        ka.build_local_resource_url("rfk:v1:source:abc", origin="https://example.com")


def test_build_local_resource_url_rejects_malformed_id() -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka.build_local_resource_url("not-an-id", origin="http://127.0.0.1")


def test_deterministic_id_sort_key_orders_by_kind_then_opaque() -> None:
    ids = ["rfk:v1:run:b", "rfk:v1:assertion:a", "rfk:v1:run:a", "rfk:v1:assertion:z"]
    ordered = sorted(ids, key=ka.deterministic_id_sort_key)
    assert ordered == ["rfk:v1:assertion:a", "rfk:v1:assertion:z", "rfk:v1:run:a", "rfk:v1:run:b"]


# ---------------------------------------------------------------------------
# Kind allowlist
# ---------------------------------------------------------------------------


def test_eligible_kinds_defaults_to_every_frozen_kind() -> None:
    assert ka.eligible_kinds() == ka.KNOWLEDGE_KINDS


def test_eligible_kinds_narrows_never_widens() -> None:
    assert ka.eligible_kinds(["source", "run"]) == ("source", "run")
    # An unknown kind name is dropped, never a widening error.
    assert ka.eligible_kinds(["source", "bogus"]) == ("source",)


# ---------------------------------------------------------------------------
# Response objects round-trip against the frozen P1 schemas (AC KMCP-2.1)
# ---------------------------------------------------------------------------


def test_core_search_response_round_trips(registry: SchemaRegistry) -> None:
    item = ka.KnowledgeSearchResultItem(
        id="rfk:v1:source:abc123",
        title="Example Source",
        url=ka.build_local_resource_url("rfk:v1:source:abc123", origin="http://127.0.0.1:7432"),
    )
    response = ka.KnowledgeSearchResponse(results=(item,))
    result = registry.validate(response.to_dict(), "knowledge_search_response")
    assert result.ok, result.errors


def test_rf_search_response_round_trips(registry: SchemaRegistry) -> None:
    item = ka.RfKnowledgeSearchResultItem(
        id="rfk:v1:assertion:xyz789",
        title="Example Assertion",
        url=ka.build_local_resource_url("rfk:v1:assertion:xyz789", origin="http://localhost:7432"),
        kind="assertion",
        snippet="hello world",
        rank=0,
        score=0.5,
    )
    outcome = ka.RfKnowledgeSearchOutcome(results=(item,), next_cursor=None, truncated=False)
    schema = registry.get("knowledge_search_response")
    validator = jsonschema.Draft202012Validator(_subschema(schema, "rf_search_response"))
    errors = list(validator.iter_errors(outcome.to_dict()))
    assert errors == []


def test_core_document_round_trips(registry: SchemaRegistry) -> None:
    doc = ka.KnowledgeDocument(
        id="rfk:v1:run:run001",
        title="Example Doc",
        text="hello",
        url=ka.build_local_resource_url("rfk:v1:run:run001", origin="http://127.0.0.1"),
    )
    result = registry.validate(doc.to_dict(), "knowledge_document")
    assert result.ok, result.errors


def test_rf_document_round_trips(registry: SchemaRegistry) -> None:
    doc = ka.RfKnowledgeDocument(
        id="rfk:v1:report_final:rep001",
        title="Report",
        url=ka.build_local_resource_url("rfk:v1:report_final:rep001", origin="http://127.0.0.1"),
        kind="report_final",
        text="body",
    )
    schema = registry.get("knowledge_document")
    validator = jsonschema.Draft202012Validator(_subschema(schema, "knowledge_document_extended"))
    errors = list(validator.iter_errors(doc.to_dict()))
    assert errors == []


def test_dto_post_init_rejects_kind_mismatch() -> None:
    with pytest.raises(ka.KnowledgeInvariantError):
        ka.RfKnowledgeSearchResultItem(
            id="rfk:v1:source:abc",
            title="Mismatched",
            url=ka.build_local_resource_url("rfk:v1:source:abc", origin="http://127.0.0.1"),
            kind="assertion",  # does not match the id's own "source" kind segment
        )


# ---------------------------------------------------------------------------
# Service skeleton: missing projections deny safely without writes (Phase P2
# exit condition)
# ---------------------------------------------------------------------------


def test_search_core_with_no_registered_projector_is_empty_not_an_error(
    tmp_foundry: FoundryPaths,
) -> None:
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="search")
    response = service.search_core(context, query="anything")
    assert response == ka.KnowledgeSearchResponse(results=())


def test_fetch_core_with_no_registered_projector_denies_safely(tmp_foundry: FoundryPaths) -> None:
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="fetch")
    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_core(context, knowledge_id="rfk:v1:source:abc123")
    assert excinfo.value.reason == "projection_unavailable"


def test_missing_projections_never_touch_the_filesystem(tmp_path, tmp_foundry: FoundryPaths) -> None:
    before = sorted(p.relative_to(tmp_foundry.root) for p in tmp_foundry.root.rglob("*"))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_search")
    service.search_extended(context, query="anything")
    try:
        service.fetch_extended(context, knowledge_id="rfk:v1:run:abc")
    except ka.KnowledgeDenied:
        pass
    after = sorted(p.relative_to(tmp_foundry.root) for p in tmp_foundry.root.rglob("*"))
    assert before == after


# ---------------------------------------------------------------------------
# Kind projector registry seam (KMCP-2.1 seam; KMCP-3.1..3.3 implement it)
# ---------------------------------------------------------------------------


class _FakeSourceProjector:
    """Minimal in-memory KindProjector used only to exercise the registry seam."""

    def search(self, context, *, query, limit, cursor):
        item = ka.RfKnowledgeSearchResultItem(
            id="rfk:v1:source:fake1",
            title=f"Fake result for {query}",
            url=ka.build_local_resource_url("rfk:v1:source:fake1", origin="http://127.0.0.1"),
            kind="source",
        )
        return ka.KindSearchPage(items=(item,), truncated=False)

    def fetch(self, context, *, knowledge_id, cursor=None):
        return ka.RfKnowledgeDocument(
            id=knowledge_id,
            title="Fake fetched document",
            url=ka.build_local_resource_url(knowledge_id, origin="http://127.0.0.1"),
            kind="source",
            text="fake body",
        )


def test_register_projector_rejects_unknown_kind() -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka.register_projector("bogus_kind", _FakeSourceProjector())


def test_registered_projector_is_used_by_search_and_fetch(tmp_foundry: FoundryPaths) -> None:
    ka.register_projector("source", _FakeSourceProjector())
    assert ka.registered_kinds() == ("source",)

    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_search")

    outcome = service.search_extended(context, query="widgets")
    assert len(outcome.results) == 1
    assert outcome.results[0].id == "rfk:v1:source:fake1"

    doc = service.fetch_extended(context, knowledge_id="rfk:v1:source:fake1")
    assert doc.text == "fake body"

    core_response = service.search_core(ka.resolve_context(tmp_foundry, tool="search"), query="widgets")
    assert core_response.results[0].id == "rfk:v1:source:fake1"


def test_unregistered_kind_still_denies_after_another_kind_is_registered(
    tmp_foundry: FoundryPaths,
) -> None:
    ka.register_projector("source", _FakeSourceProjector())
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")
    with pytest.raises(ka.KnowledgeDenied):
        service.fetch_extended(context, knowledge_id="rfk:v1:run:abc123")


# ===========================================================================
# KMCP-2.4: Core negative matrix
# ===========================================================================


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    """Every regular file under ``root``, by relative path, with full byte content.

    Symlinks are skipped (mirrors ``query_only_connection``'s own symlink
    rejection). Dict equality between two snapshots is a byte-identical
    comparison of the entire fixture tree, not just a file-name listing.
    """

    snapshot: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


def _install_write_surface_spies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch every cache/index-rebuild/run-creation/source-creation/
    audit-artifact/telemetry-artifact/provider-call/write function reachable
    from a Knowledge read and make each one raise immediately if invoked.

    Covers the derived-catalog write surface (``catalog_service``'s
    import/rebuild/draft-index functions plus its low-level write-capable
    connection opener and schema DDL -- never the KMCP-2.2 read-only seam),
    the assertion-projection write surface (``AssertionCatalog.rebuild`` plus
    its atomic-write primitive), the audit-artifact writer
    (``audit_service.record_event``), the telemetry-artifact writers
    (``telemetry.emit_ccdash_event``/``push_status``), the Report Builder
    draft-creation surface (``builder_service``'s target_surfaces per AC
    KMCP-3, even though Knowledge does not wire report kinds until P3), and
    -- as a blanket provider-call guard -- all outbound network sockets
    (sqlite's own file-backed connections never touch ``socket.socket``, so
    this cannot false-positive on a read-only DB/projection query).
    """

    def _spy(name: str):
        def _inner(*_args: Any, **_kwargs: Any) -> Any:
            raise AssertionError(f"unexpected write-surface/provider call during a Knowledge read: {name}")

        return _inner

    for fn_name in (
        "import_run",
        "import_all",
        "rebuild",
        "rebuild_schema",
        "index_draft",
        "remove_draft_index",
        "_connect",
        "_ensure_schema",
        "_create_schema",
        "_drop_schema",
    ):
        monkeypatch.setattr(catalog_svc, fn_name, _spy(f"catalog_service.{fn_name}"))

    monkeypatch.setattr(
        assertion_catalog_module.AssertionCatalog, "rebuild", _spy("AssertionCatalog.rebuild")
    )
    monkeypatch.setattr(
        assertion_catalog_module, "_atomic_json_dump", _spy("assertion_catalog._atomic_json_dump")
    )

    monkeypatch.setattr(audit_service, "record_event", _spy("audit_service.record_event"))
    monkeypatch.setattr(telemetry, "emit_ccdash_event", _spy("telemetry.emit_ccdash_event"))
    monkeypatch.setattr(telemetry, "push_status", _spy("telemetry.push_status"))

    for fn_name in ("create_draft", "create_draft_from_run", "create_draft_from_collection", "reindex_all_drafts"):
        monkeypatch.setattr(builder_service, fn_name, _spy(f"builder_service.{fn_name}"))

    monkeypatch.setattr(socket.socket, "connect", _spy("socket.socket.connect"))


class _CatalogReadOnlyProjector:
    """Test-only ``KindProjector`` for kind ``"source"``, wired to the REAL
    KMCP-2.2 non-writing seam (``catalog_service.query_only_connection`` /
    ``is_catalog_available``) -- never ``catalog_service.search``/``get_item``
    (both write-capable via ``_connect``/``_db``, and both spied to raise by
    :func:`_install_write_surface_spies`). Exists only to prove the write
    surface stays silent when a P3-shaped projector exercises the real
    read-only seam through the service; it has none of P3's real sensitivity/
    rights filtering.
    """

    def __init__(self, paths: FoundryPaths) -> None:
        self.paths = paths

    def search(self, context: ka.KnowledgeAccessContext, *, query: str, limit: int, cursor: str | None) -> ka.KindSearchPage:
        if not catalog_svc.is_catalog_available(self.paths):
            return ka.KindSearchPage(items=(), truncated=False)
        with catalog_svc.query_only_connection(self.paths) as conn:
            rows = conn.execute(
                "SELECT catalog_item_id, title FROM catalog_items WHERE search_text LIKE ? "
                "ORDER BY catalog_item_id LIMIT ?",
                (f"%{query.lower()}%", limit),
            ).fetchall()
        items = tuple(
            ka.RfKnowledgeSearchResultItem(
                id=f"rfk:v1:source:{row['catalog_item_id']}",
                title=row["title"] or row["catalog_item_id"],
                url=ka.build_local_resource_url(
                    f"rfk:v1:source:{row['catalog_item_id']}", origin="http://127.0.0.1"
                ),
                kind="source",
            )
            for row in rows
        )
        return ka.KindSearchPage(items=items, truncated=False)

    def fetch(
        self, context: ka.KnowledgeAccessContext, *, knowledge_id: str, cursor: str | None = None
    ) -> ka.RfKnowledgeDocument:
        # NOTE: ka.parse_knowledge_id(value) returns (kind, value) -- its
        # second element is the WHOLE ``rfk:v1:<kind>:<opaque>`` string (see
        # its own docstring: "opaque" there means "opaque to callers", not
        # "the trailing local segment"), so the actual local/opaque segment
        # a real backing store's own id column holds must be recovered by
        # stripping the frozen ``rfk:v1:<kind>:`` prefix ourselves.
        ka.parse_knowledge_id(knowledge_id)  # validates shape; raises if malformed
        opaque = knowledge_id.rsplit(":", 1)[-1]
        if not catalog_svc.is_catalog_available(self.paths):
            raise ka.KnowledgeDenied("projection_unavailable")
        with catalog_svc.query_only_connection(self.paths) as conn:
            row = conn.execute(
                "SELECT * FROM catalog_items WHERE catalog_item_id = ?", (opaque,)
            ).fetchone()
        if row is None:
            raise ka.KnowledgeDenied("not_found")
        return ka.RfKnowledgeDocument(
            id=knowledge_id,
            title=row["title"] or opaque,
            url=ka.build_local_resource_url(knowledge_id, origin="http://127.0.0.1"),
            kind="source",
            text=row["summary"] or row["title"] or opaque,
        )


class _AssertionReadOnlyProjector:
    """Test-only ``KindProjector`` for kind ``"assertion"``, wired to the REAL
    KMCP-2.3 non-writing seam (``AssertionCatalog.search_read_only`` /
    ``packet_read_only``) -- never ``.search``/``.packet``/``.rebuild`` (all
    rebuild-on-miss or write-capable, and ``.rebuild`` is spied to raise by
    :func:`_install_write_surface_spies`). Identity is taken from ``context``
    (never stored on the projector itself), matching invariant 3 -- policy
    always flows from the resolved context, never from projector state.
    """

    def __init__(self, catalog: AssertionCatalog) -> None:
        self.catalog = catalog

    def search(self, context: ka.KnowledgeAccessContext, *, query: str, limit: int, cursor: str | None) -> ka.KindSearchPage:
        result = self.catalog.search_read_only(
            identity=context.identity, query=query, limit=limit, cursor=cursor
        )
        if result["denial_reason"] is not None:
            return ka.KindSearchPage(items=(), truncated=False)
        items = tuple(
            ka.RfKnowledgeSearchResultItem(
                id=f"rfk:v1:assertion:{item['assertion_id']}",
                title=item["assertion_id"],
                url=ka.build_local_resource_url(
                    f"rfk:v1:assertion:{item['assertion_id']}", origin="http://127.0.0.1"
                ),
                kind="assertion",
            )
            for item in result["items"]
        )
        return ka.KindSearchPage(items=items, truncated=result["next_cursor"] is not None)

    def fetch(
        self, context: ka.KnowledgeAccessContext, *, knowledge_id: str, cursor: str | None = None
    ) -> ka.RfKnowledgeDocument:
        # See _CatalogReadOnlyProjector.fetch's note: recover the trailing
        # local segment ourselves rather than parse_knowledge_id's own
        # (whole-string) second return value.
        ka.parse_knowledge_id(knowledge_id)  # validates shape; raises if malformed
        opaque = knowledge_id.rsplit(":", 1)[-1]
        try:
            packet = self.catalog.packet_read_only(opaque, identity=context.identity)
        except (AssertionCatalogDenied, AssertionCatalogUnavailable) as exc:
            raise ka.KnowledgeDenied(exc.reason_code) from exc
        if packet is None:
            raise ka.KnowledgeDenied("not_found")
        return ka.RfKnowledgeDocument(
            id=knowledge_id,
            title=packet["assertion_id"],
            url=ka.build_local_resource_url(knowledge_id, origin="http://127.0.0.1"),
            kind="assertion",
            text=packet["assertion"].get("assertion_text") or packet["assertion_id"],
        )


# ---------------------------------------------------------------------------
# Skeleton alone (no projector) -- zero writes/provider calls, tree unchanged
# ---------------------------------------------------------------------------


def test_negative_matrix_skeleton_with_no_projector_touches_no_write_surface(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _snapshot_tree(tmp_foundry.root)
    _install_write_surface_spies(monkeypatch)
    service = ka.KnowledgeAccessService(tmp_foundry)

    core_response = service.search_core(ka.resolve_context(tmp_foundry, tool="search"), query="anything")
    assert core_response == ka.KnowledgeSearchResponse(results=())

    with pytest.raises(ka.KnowledgeDenied):
        service.fetch_core(ka.resolve_context(tmp_foundry, tool="fetch"), knowledge_id="rfk:v1:source:abc")

    rf_outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="anything")
    assert rf_outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    with pytest.raises(ka.KnowledgeDenied):
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id="rfk:v1:run:abc"
        )

    assert _snapshot_tree(tmp_foundry.root) == before


# ---------------------------------------------------------------------------
# Catalog-backed ("source") kind -- missing DB / existing DB / same-shape denial
# ---------------------------------------------------------------------------


def test_negative_matrix_catalog_projector_missing_db_denies_without_rebuild(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A never-created catalog.db denies typed/unavailable -- never rebuilt."""

    before = _snapshot_tree(tmp_foundry.root)
    _install_write_surface_spies(monkeypatch)
    ka.register_projector("source", _CatalogReadOnlyProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="alpha")
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id="rfk:v1:source:ci_doesnotexist0"
        )
    assert excinfo.value.reason == "projection_unavailable"

    assert not tmp_foundry.rf_cache.exists()
    assert _snapshot_tree(tmp_foundry.root) == before


def test_negative_matrix_catalog_projector_existing_db_reads_change_zero_files(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing, imported catalog.db is fully queryable with zero file mutation."""

    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    before = _snapshot_tree(tmp_foundry.root)
    mtime_before = tmp_foundry.catalog_db.stat().st_mtime_ns

    _install_write_surface_spies(monkeypatch)
    ka.register_projector("source", _CatalogReadOnlyProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="alpha")
    assert len(outcome.results) >= 1
    found_id = outcome.results[0].id

    doc = service.fetch_extended(ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=found_id)
    assert doc.id == found_id
    assert doc.text

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id="rfk:v1:source:ci_doesnotexist0"
        )
    assert excinfo.value.reason == "not_found"

    assert tmp_foundry.catalog_db.stat().st_mtime_ns == mtime_before
    assert _snapshot_tree(tmp_foundry.root) == before


# ---------------------------------------------------------------------------
# Assertion-projection-backed ("assertion") kind -- missing / existing / denial
# ---------------------------------------------------------------------------


def test_negative_matrix_assertion_projector_missing_projection_denies_without_rebuild(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workspace whose assertion projection was never built denies typed/
    unavailable -- never rebuilt (contrast ``AssertionCatalog.search``'s own
    rebuild-on-miss behavior, proven separately in test_assertion_catalog.py).
    """

    identity = AuthIdentity("alice", "workspace-never-built-km", ("viewer",))
    catalog = AssertionCatalog(tmp_foundry)
    projection_path = catalog.projection_path(identity.workspace_id)
    before = _snapshot_tree(tmp_foundry.root)

    _install_write_surface_spies(monkeypatch)
    ka.register_projector("assertion", _AssertionReadOnlyProjector(catalog))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)

    outcome = service.search_extended(context, query="anything")
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_does_not_exist")
    assert excinfo.value.reason == "projection_missing"

    assert not projection_path.exists()
    assert _snapshot_tree(tmp_foundry.root) == before


def test_negative_matrix_assertion_projector_existing_projection_reads_change_zero_files(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing, rebuilt assertion projection is fully queryable with zero
    file mutation -- the ``.rebuild()`` call above is fixture SETUP, performed
    before the write-surface spies are installed, exactly like
    ``build_catalog_run``+``import_run`` above."""

    assertion_id = _materialize(
        tmp_foundry,
        "rf_run_km_negmatrix",
        "workspace-km-a",
        "The negative-matrix read-only fact is forty-two percent.",
    )
    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-km-a")
    before = _snapshot_tree(tmp_foundry.root)

    _install_write_surface_spies(monkeypatch)
    ka.register_projector("assertion", _AssertionReadOnlyProjector(catalog))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-km-a", ("researcher",))
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)

    outcome = service.search_extended(context, query="forty-two")
    assert len(outcome.results) == 1
    assert outcome.results[0].id == f"rfk:v1:assertion:{assertion_id}"

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    assert doc.text == "The negative-matrix read-only fact is forty-two percent."

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_does_not_exist")
    assert excinfo.value.reason == "not_found"

    assert _snapshot_tree(tmp_foundry.root) == before


def test_negative_matrix_assertion_projector_rights_denied_matches_missing_shape(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rights-denied assertion (edition missing ``allowed_use``) resolves to
    the SAME bounded, no-existence-leak shape as a genuinely unknown id --
    only the internal (never-rendered) ``.reason`` differs."""

    from research_foundry.yamlio import dump_yaml, load_yaml

    assertion_id = _materialize(
        tmp_foundry, "rf_run_km_rights", "workspace-km-rights", "Missing rights must deny the Knowledge read too."
    )
    edition_path = next(
        (tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml")
    )
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)

    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-km-rights")

    _install_write_surface_spies(monkeypatch)
    ka.register_projector("assertion", _AssertionReadOnlyProjector(catalog))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-km-rights", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)

    # Search: fail-closed to the SAME empty-results shape a missing/hidden
    # projection would produce (see the "missing" test above).
    outcome = service.search_extended(context, query="rights")
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    with pytest.raises(ka.KnowledgeDenied) as rights_denied:
        service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    with pytest.raises(ka.KnowledgeDenied) as genuinely_unknown:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_totally_unrelated")

    # Same bounded exception TYPE for both causes -- a caller/transport that
    # catches KnowledgeDenied generically (per the class's own docstring: the
    # internal `.reason` diagnostic code must never be rendered) cannot tell
    # "exists but rights-denied" apart from "never existed" by shape alone.
    assert type(rights_denied.value) is type(genuinely_unknown.value) is ka.KnowledgeDenied
    assert rights_denied.value.reason == "rights_context_missing"
    assert genuinely_unknown.value.reason == "not_found"


def test_negative_matrix_assertion_projector_cross_workspace_matches_missing_shape(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fetching another workspace's REAL assertion id denies with the SAME
    shape as fetching a genuinely unknown id in one's own workspace --
    existence in a foreign workspace is never leaked."""

    other_assertion_id = _materialize(
        tmp_foundry, "rf_run_km_ws_a", "workspace-km-ws-a", "Workspace A's own private evidence."
    )
    own_assertion_id = _materialize(
        tmp_foundry, "rf_run_km_ws_b", "workspace-km-ws-b", "Workspace B's own private evidence."
    )
    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-km-ws-a")
    catalog.rebuild("workspace-km-ws-b")
    before = _snapshot_tree(tmp_foundry.root)

    _install_write_surface_spies(monkeypatch)
    ka.register_projector("assertion", _AssertionReadOnlyProjector(catalog))
    service = ka.KnowledgeAccessService(tmp_foundry)
    # Caller is authenticated into workspace B, which has its OWN available,
    # non-empty projection -- this is a real cross-workspace probe, not a
    # "nothing built yet" case (see the "missing projection" test above).
    identity = AuthIdentity("bob", "workspace-km-ws-b", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    with pytest.raises(ka.KnowledgeDenied) as cross_workspace:
        service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{other_assertion_id}")
    with pytest.raises(ka.KnowledgeDenied) as genuinely_unknown:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_totally_unrelated")

    assert type(cross_workspace.value) is type(genuinely_unknown.value) is ka.KnowledgeDenied
    assert cross_workspace.value.reason == "not_found"
    assert genuinely_unknown.value.reason == "not_found"

    # Own-workspace id remains fetchable throughout -- proves the denial above
    # is workspace-scoping, not a broken/unavailable projection.
    own_doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{own_assertion_id}")
    assert own_doc.id == f"rfk:v1:assertion:{own_assertion_id}"

    assert _snapshot_tree(tmp_foundry.root) == before


def test_negative_matrix_every_denial_cause_yields_the_identical_search_outcome(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing projection, rights-denied, and cross-workspace search calls all
    resolve to the exact same dataclass value -- not just the same shape."""

    from research_foundry.yamlio import dump_yaml, load_yaml

    _materialize(tmp_foundry, "rf_run_km_uniform_a", "workspace-km-uniform-a", "Uniform-shape fixture A.")
    edition_path = next(
        (tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml")
    )
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)
    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-km-uniform-a")  # rights-denied once built

    _materialize(tmp_foundry, "rf_run_km_uniform_b", "workspace-km-uniform-b", "Uniform-shape fixture B.")
    catalog.rebuild("workspace-km-uniform-b")  # available, but cross-workspace below

    _install_write_surface_spies(monkeypatch)
    ka.register_projector("assertion", _AssertionReadOnlyProjector(catalog))
    service = ka.KnowledgeAccessService(tmp_foundry)

    missing_outcome = service.search_extended(
        ka.resolve_context(
            tmp_foundry, tool="rf_search", identity=AuthIdentity("x", "workspace-km-never-built", ("viewer",))
        ),
        query="uniform",
    )
    rights_denied_outcome = service.search_extended(
        ka.resolve_context(
            tmp_foundry, tool="rf_search", identity=AuthIdentity("x", "workspace-km-uniform-a", ("viewer",))
        ),
        query="uniform",
    )
    # workspace-km-uniform-b's OWN search is naturally scoped away from
    # workspace-a's content by AssertionCatalog's own per-workspace
    # projection design -- querying for "fixture A" text from workspace B's
    # identity finds nothing, the same empty shape as every other cause.
    cross_workspace_outcome = service.search_extended(
        ka.resolve_context(
            tmp_foundry, tool="rf_search", identity=AuthIdentity("x", "workspace-km-uniform-b", ("viewer",))
        ),
        query="fixture a",
    )

    expected = ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)
    assert missing_outcome == rights_denied_outcome == cross_workspace_outcome == expected


# ===========================================================================
# KMCP-3.1: Source projection matrix
# ===========================================================================


def test_source_projector_pure_helpers_omit_over_threshold_points() -> None:
    """Defense-in-depth per-point filtering (invariant 3), independent of the DB."""

    payload = {
        "evidence_points": [
            {"claim_id": "clm_a", "quote": "low quote", "summary": "low summary", "sensitivity_rank": 0},
            {"claim_id": "clm_b", "quote": "high quote", "summary": "high summary", "sensitivity_rank": 3},
        ]
    }
    allowed = ka._allowed_source_evidence_points(payload, threshold_rank=1)
    assert [p["claim_id"] for p in allowed] == ["clm_a"]


def test_source_projector_pure_helpers_bound_evidence_point_count() -> None:
    payload = {
        "evidence_points": [
            {"claim_id": f"clm_{i}", "quote": "q", "summary": "s", "sensitivity_rank": 0}
            for i in range(ka.SOURCE_EVIDENCE_POINTS_MAX + 5)
        ]
    }
    allowed = ka._allowed_source_evidence_points(payload, threshold_rank=3)
    assert len(allowed) == ka.SOURCE_EVIDENCE_POINTS_MAX


def test_truncate_text_marks_truncated_past_codepoint_cap() -> None:
    long_text = "x" * (ka.DOCUMENT_MAX_TEXT_CODEPOINTS + 10)
    text, truncated = ka._truncate_text(long_text)
    assert truncated is True
    # ASCII input: the tighter UTF-8 byte cap (200_000 bytes) binds before the
    # looser codepoint cap (400_000) ever would.
    assert len(text) == ka.DOCUMENT_MAX_TEXT_BYTES


def test_public_locator_url_strips_non_http_values() -> None:
    assert ka._public_locator_url("https://example.test/x") == "https://example.test/x"
    assert ka._public_locator_url("/etc/passwd") is None
    assert ka._public_locator_url("file:///etc/passwd") is None
    assert ka._public_locator_url(None) is None
    assert ka._public_locator_url(42) is None


def test_source_projector_resolves_visible_item_with_allowlisted_fields(
    tmp_foundry: FoundryPaths,
) -> None:
    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    ka.register_projector("source", ka.SourceKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:source:{item_id}")
    assert doc.kind == "source"
    assert doc.original_source_url == "https://example.test/alpha"
    assert doc.rf_metadata is not None
    assert doc.rf_metadata["trust"] == "high"
    assert doc.rf_metadata["provenance"] == {
        "catalog_item_id": item_id,
        "run_id": "rf_run_catalog001",
        "source_card_id": "src_alpha",
    }
    assert doc.text is not None
    assert "ALPHA QUOTE" in doc.text


def test_source_projector_search_and_fetch_resolve_same_resource(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    ka.register_projector("source", ka.SourceKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="alpha")
    assert len(outcome.results) >= 1
    found = next(r for r in outcome.results if "Alpha" in r.title)

    doc = service.fetch_extended(ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=found.id)
    assert doc.id == found.id
    assert doc.url == found.url


def test_source_projector_hides_item_above_sensitivity_threshold(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry, sensitivity="personal")
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    ka.register_projector("source", ka.SourceKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    _write_threshold(tmp_foundry, "public")
    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=f"rfk:v1:source:{item_id}"
        )
    assert excinfo.value.reason == "not_found"
    hidden_search = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="alpha")
    assert hidden_search.results == ()

    _write_threshold(tmp_foundry, "personal")
    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=f"rfk:v1:source:{item_id}"
    )
    assert doc.id == f"rfk:v1:source:{item_id}"


def test_source_projector_strips_filesystem_path_locator(tmp_foundry: FoundryPaths) -> None:
    """A locator ``url`` planted as a raw filesystem path never surfaces as
    ``original_source_url`` -- and never appears anywhere in the emitted
    document at all (invariant 7 / AC KMCP-4)."""

    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    conn = sqlite3.connect(str(tmp_foundry.catalog_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT payload_json FROM catalog_items WHERE catalog_item_id = ?", (item_id,)
    ).fetchone()
    payload = json.loads(row["payload_json"])
    payload["url"] = "/etc/passwd"
    conn.execute(
        "UPDATE catalog_items SET payload_json = ? WHERE catalog_item_id = ?",
        (json.dumps(payload), item_id),
    )
    conn.commit()
    conn.close()

    ka.register_projector("source", ka.SourceKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=f"rfk:v1:source:{item_id}"
    )
    assert doc.original_source_url is None
    assert "/etc/passwd" not in json.dumps(doc.to_dict())


def test_source_projector_missing_catalog_denies_without_creating_it(tmp_foundry: FoundryPaths) -> None:
    """Proves KMCP-2.2's invariant through the REAL P3 adapter (not the P2 fake)."""

    ka.register_projector("source", ka.SourceKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="anything")
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id="rfk:v1:source:ci_doesnotexist0"
        )
    assert excinfo.value.reason == "projection_unavailable"
    assert not tmp_foundry.catalog_db.exists()


def test_source_projector_where_clause_adds_workspace_scope_when_isolation_active(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ka, "resolve_workspace_isolation_active", lambda paths: True)
    projector = ka.SourceKindProjector(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    where_sql, params = projector._where_clause(context)
    assert "workspace_id = ?" in where_sql
    assert params[-1] == "workspace-a"


def test_source_projector_where_clause_omits_workspace_scope_for_local_trust(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ka, "resolve_workspace_isolation_active", lambda paths: True)
    projector = ka.SourceKindProjector(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="fetch")  # identity=None (local trust)

    where_sql, params = projector._where_clause(context)
    assert "workspace_id" not in where_sql
    assert params == [context.sensitivity_rank]


def test_source_projector_cross_workspace_denies_with_generic_shape_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KMCP-6.5 gap-fill: every OTHER kind (assertion/report/run) already has
    an end-to-end, real-fixture, two-REAL-workspace search+fetch denial test
    (see ``test_assertion_projector_cross_workspace_matches_generic_shape``,
    ``test_report_projector_cross_workspace_denies_with_generic_shape``,
    ``test_run_projector_cross_workspace_denies_with_generic_shape`` below);
    source's own coverage stopped at the unit-level ``_where_clause`` checks
    immediately above. ``catalog_service.import_run`` always hardcodes
    ``workspace_id="default"`` (WKSP-303 comment in ``_base_row``, mirrored
    by ``tests/unit/test_catalog_service.py``'s own WKSP-304 Phase 3 section)
    -- so, exactly like that module's own precedent, a real second workspace
    is reached by a direct ``catalog_items`` row ``UPDATE``, not a public API
    (no source-ingest call site accepts a caller-supplied ``workspace_id``
    yet)."""

    _force_isolation_active(monkeypatch)
    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    conn = sqlite3.connect(str(tmp_foundry.catalog_db))
    conn.execute(
        "UPDATE catalog_items SET workspace_id = ? WHERE catalog_item_id = ?",
        ("workspace-source-mine", item_id),
    )
    conn.commit()
    conn.close()

    ka.register_projector("source", ka.SourceKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    other_identity = AuthIdentity("bob", "workspace-source-other", ("viewer",))

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=other_identity),
            knowledge_id=f"rfk:v1:source:{item_id}",
        )
    assert excinfo.value.reason == "not_found"

    hidden = service.search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search", identity=other_identity), query="alpha"
    )
    assert hidden.results == ()

    # Sanity: the SAME identity's OWN workspace still resolves fine -- proves
    # the denial above is genuinely workspace-scoped, not a fixture bug.
    same_workspace_identity = AuthIdentity("alice", "workspace-source-mine", ("viewer",))
    visible = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=same_workspace_identity),
        knowledge_id=f"rfk:v1:source:{item_id}",
    )
    assert visible.id == f"rfk:v1:source:{item_id}"


# ===========================================================================
# KMCP-3.2: Assertion projection matrix
# ===========================================================================


def test_assertion_projector_eligible_packet_is_visible_with_allowlisted_fields(
    tmp_foundry: FoundryPaths,
) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_km_p3_a", "workspace-p3-a", "The P3 assertion fact is thirty-nine percent."
    )
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-a")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-a", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    assert doc.kind == "assertion"
    assert doc.text is not None
    assert "thirty-nine percent" in doc.text
    assert doc.rf_metadata is not None
    assert doc.rf_metadata["lifecycle_state"] == "eligible"
    assert doc.rf_metadata["provenance"]["assertion_id"] == assertion_id
    assert doc.rf_metadata["source_edition"]["source_edition_id"]
    assert doc.rf_metadata["rights_decision"] == {"allowed": True, "reason_code": "eligible"}


def test_assertion_projector_search_and_fetch_resolve_same_resource(tmp_foundry: FoundryPaths) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_km_p3_b", "workspace-p3-b", "The sharedtermxyz P3 assertion evidence is real."
    )
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-b")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-b", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)

    outcome = service.search_extended(context, query="sharedtermxyz")
    assert len(outcome.results) == 1
    found = outcome.results[0]
    assert found.id == f"rfk:v1:assertion:{assertion_id}"
    assert found.snippet is not None

    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity), knowledge_id=found.id
    )
    assert doc.id == found.id


def test_assertion_projector_search_reports_truncated_when_more_pages_remain(
    tmp_foundry: FoundryPaths,
) -> None:
    _materialize(tmp_foundry, "rf_run_km_p3_page_a", "workspace-p3-page", "The paged sharedtermxyz fact one.")
    _materialize(tmp_foundry, "rf_run_km_p3_page_b", "workspace-p3-page", "The paged sharedtermxyz fact two.")
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-page")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-page", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)

    outcome = service.search_extended(context, query="sharedtermxyz", limit=1)
    assert len(outcome.results) == 1
    assert outcome.truncated is True


def test_assertion_projector_blocked_lifecycle_denies_with_generic_shape(tmp_foundry: FoundryPaths) -> None:
    from research_foundry.yamlio import dump_yaml, load_yaml

    assertion_id = _materialize(
        tmp_foundry,
        "rf_run_km_p3_blocked",
        "workspace-p3-blocked",
        "Blocked lifecycle must deny the P3 Knowledge read.",
    )
    assertion_path = next(
        (tmp_foundry.root / "assertion_ledger" / "workspaces").glob(f"*/assertions/{assertion_id}.yaml")
    )
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "blocked"
    dump_yaml(assertion, assertion_path)
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-blocked")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-blocked", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    with pytest.raises(ka.KnowledgeDenied) as blocked:
        service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    with pytest.raises(ka.KnowledgeDenied) as unknown:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_totally_unrelated")

    assert type(blocked.value) is type(unknown.value) is ka.KnowledgeDenied
    assert blocked.value.reason == "not_eligible"
    assert unknown.value.reason == "not_found"

    # A blocked assertion must not surface from search either -- it never
    # reaches `authorized` inside `search_read_only` in the first place.
    outcome = service.search_extended(context, query="blocked lifecycle")
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)


def test_assertion_projector_rights_denied_matches_generic_shape(tmp_foundry: FoundryPaths) -> None:
    from research_foundry.yamlio import dump_yaml, load_yaml

    assertion_id = _materialize(
        tmp_foundry,
        "rf_run_km_p3_rights",
        "workspace-p3-rights",
        "Missing rights must deny the P3 Knowledge read too.",
    )
    edition_path = next(
        (tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml")
    )
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-rights")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-rights", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    with pytest.raises(ka.KnowledgeDenied) as rights_denied:
        service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    with pytest.raises(ka.KnowledgeDenied) as unknown:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_totally_unrelated")

    assert type(rights_denied.value) is type(unknown.value) is ka.KnowledgeDenied
    assert rights_denied.value.reason == "rights_context_missing"


def test_assertion_projector_cross_workspace_matches_generic_shape(tmp_foundry: FoundryPaths) -> None:
    other_assertion_id = _materialize(
        tmp_foundry, "rf_run_km_p3_ws_a", "workspace-p3-ws-a", "Workspace A's own private P3 evidence."
    )
    own_assertion_id = _materialize(
        tmp_foundry, "rf_run_km_p3_ws_b", "workspace-p3-ws-b", "Workspace B's own private P3 evidence."
    )
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-ws-a")
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-ws-b")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("bob", "workspace-p3-ws-b", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    with pytest.raises(ka.KnowledgeDenied) as cross_workspace:
        service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{other_assertion_id}")
    with pytest.raises(ka.KnowledgeDenied) as genuinely_unknown:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_totally_unrelated")

    assert type(cross_workspace.value) is type(genuinely_unknown.value) is ka.KnowledgeDenied
    assert cross_workspace.value.reason == "not_found"
    assert genuinely_unknown.value.reason == "not_found"

    own_doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{own_assertion_id}")
    assert own_doc.id == f"rfk:v1:assertion:{own_assertion_id}"


def test_assertion_projector_missing_projection_denies_without_rebuild(tmp_foundry: FoundryPaths) -> None:
    """Proves KMCP-2.3's invariant through the REAL P3 adapter (not the P2 fake)."""

    identity = AuthIdentity("alice", "workspace-p3-never-built", ("viewer",))
    catalog = AssertionCatalog(tmp_foundry)
    projection_path = catalog.projection_path(identity.workspace_id)

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_search", identity=identity)

    outcome = service.search_extended(context, query="anything")
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(context, knowledge_id="rfk:v1:assertion:ast_does_not_exist")
    assert excinfo.value.reason == "projection_missing"
    assert not projection_path.exists()


def test_assertion_projector_never_surfaces_retrieval_locator_file_path(tmp_foundry: FoundryPaths) -> None:
    """``_materialize``'s ingest path always plants a ``file_path``-only
    locator (no ``url``) -- the projector must never surface it (invariant 7 /
    AC KMCP-4)."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_km_p3_path", "workspace-p3-path", "Locator file_path must never leak from P3."
    )
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-path")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-path", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    assert doc.original_source_url is None
    # The un-resolved locator's filename must not leak anywhere, including
    # inside untrusted free text. The literal English word "file_path" is
    # deliberately part of this test's own content sentence (untrusted text
    # may contain any words), so the *structured metadata* is what must never
    # carry the raw key/value -- check that scoped to `rf_metadata` only.
    assert "rf_run_km_p3_path.txt" not in json.dumps(doc.to_dict())
    assert "file_path" not in json.dumps(doc.rf_metadata)


def test_assertion_projector_bounds_evaluation_count(tmp_foundry: FoundryPaths) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_km_p3_evalcap", "workspace-p3-evalcap", "Evaluation count must stay bounded."
    )
    AssertionCatalog(tmp_foundry).rebuild("workspace-p3-evalcap")

    ka.register_projector("assertion", ka.AssertionKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-p3-evalcap", ("viewer",))
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=identity)

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:assertion:{assertion_id}")
    assert doc.rf_metadata is not None
    assert len(doc.rf_metadata["evaluations"]) <= ka.ASSERTION_EVALUATIONS_MAX


# ===========================================================================
# KMCP-3.3: Report projection matrix (report_draft / report_final)
# ===========================================================================


@pytest.mark.parametrize(
    "status,expected_kind",
    [
        ("draft", "report_draft"),
        ("verified", "report_draft"),
        ("published", "report_final"),
        ("archived", "report_final"),
        (None, "report_draft"),
        ("some_future_status", "report_draft"),
    ],
)
def test_report_kind_for_status_resolves_lifecycle(status: str | None, expected_kind: str) -> None:
    assert ka._report_kind_for_status(status) == expected_kind


def test_report_projector_rejects_unknown_target_kind(tmp_foundry: FoundryPaths) -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka.ReportKindProjector(tmp_foundry, target_kind="run")


def test_report_projector_resolves_draft_kind_with_allowlisted_fields(tmp_foundry: FoundryPaths) -> None:
    draft = builder_service.create_draft(
        tmp_foundry,
        title="Draft Report Alpha",
        sensitivity="client_sensitive",
        blocks=[{"markdown": "ALPHA BODY TEXT"}],
    )
    report_draft_id = draft["report_draft_id"]

    ka.register_projector("report_draft", ka.ReportKindProjector(tmp_foundry, target_kind="report_draft"))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch", sensitivity_threshold="client_sensitive")

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:report_draft:{report_draft_id}")
    assert doc.kind == "report_draft"
    assert doc.rf_metadata is not None
    assert doc.rf_metadata["status"] == "draft"
    assert doc.rf_metadata["provenance"] == {
        "report_draft_id": report_draft_id,
        "source_run_id": None,
    }
    assert doc.text is not None
    assert "ALPHA BODY TEXT" in doc.text
    # No operator/identity field ever leaks (invariant 7 / AC KMCP-4).
    dumped = json.dumps(doc.to_dict())
    assert "workspace_id" not in dumped
    assert "created_by" not in dumped


def test_report_projector_resolves_final_kind_when_published(tmp_foundry: FoundryPaths) -> None:
    draft = builder_service.create_draft(
        tmp_foundry, title="Final Report Beta", sensitivity="public", blocks=[{"markdown": "BETA BODY"}]
    )
    report_draft_id = draft["report_draft_id"]
    _publish_draft(tmp_foundry, report_draft_id, status="published")

    ka.register_projector("report_final", ka.ReportKindProjector(tmp_foundry, target_kind="report_final"))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")

    doc = service.fetch_extended(context, knowledge_id=f"rfk:v1:report_final:{report_draft_id}")
    assert doc.kind == "report_final"
    assert doc.rf_metadata is not None
    assert doc.rf_metadata["status"] == "published"
    assert "BETA BODY" in doc.text


def test_report_projector_mismatched_kind_id_denies_safely(tmp_foundry: FoundryPaths) -> None:
    """A still-``draft`` record addressed via its ``report_final`` id denies
    with the SAME generic shape as a genuinely missing id -- never a distinct
    "wrong kind" signal (KMCP-OQ-1)."""

    draft = builder_service.create_draft(tmp_foundry, title="Still Drafting", sensitivity="public")
    report_draft_id = draft["report_draft_id"]  # status still "draft"

    ka.register_projector("report_final", ka.ReportKindProjector(tmp_foundry, target_kind="report_final"))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(context, knowledge_id=f"rfk:v1:report_final:{report_draft_id}")
    assert excinfo.value.reason == "not_found"


def test_report_projector_search_and_fetch_resolve_same_resource(tmp_foundry: FoundryPaths) -> None:
    builder_service.create_draft(tmp_foundry, title="Searchable Gamma Report", sensitivity="public")

    ka.register_projector("report_draft", ka.ReportKindProjector(tmp_foundry, target_kind="report_draft"))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="gamma")
    assert len(outcome.results) == 1
    found = outcome.results[0]
    assert found.kind == "report_draft"

    doc = service.fetch_extended(ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=found.id)
    assert doc.id == found.id
    assert doc.url == found.url


def test_report_projector_hides_item_above_sensitivity_threshold(tmp_foundry: FoundryPaths) -> None:
    draft = builder_service.create_draft(tmp_foundry, title="Delta Sensitive Report", sensitivity="client_sensitive")
    report_draft_id = draft["report_draft_id"]

    ka.register_projector("report_draft", ka.ReportKindProjector(tmp_foundry, target_kind="report_draft"))
    service = ka.KnowledgeAccessService(tmp_foundry)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch", sensitivity_threshold="public"),
            knowledge_id=f"rfk:v1:report_draft:{report_draft_id}",
        )
    assert excinfo.value.reason == "not_found"

    hidden = service.search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search", sensitivity_threshold="public"), query="delta"
    )
    assert hidden.results == ()

    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch", sensitivity_threshold="client_sensitive"),
        knowledge_id=f"rfk:v1:report_draft:{report_draft_id}",
    )
    assert doc.id == f"rfk:v1:report_draft:{report_draft_id}"


def test_report_projector_cross_workspace_denies_with_generic_shape(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _force_isolation_active(monkeypatch)
    draft = builder_service.create_draft(
        tmp_foundry,
        title="Epsilon Private Report",
        sensitivity="public",
        identity=AuthIdentity("alice", "workspace-report-mine", ("viewer",)),
    )
    report_draft_id = draft["report_draft_id"]
    assert draft["workspace_id"] == "workspace-report-mine"

    ka.register_projector("report_draft", ka.ReportKindProjector(tmp_foundry, target_kind="report_draft"))
    service = ka.KnowledgeAccessService(tmp_foundry)
    other_identity = AuthIdentity("bob", "workspace-report-other", ("viewer",))

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=other_identity),
            knowledge_id=f"rfk:v1:report_draft:{report_draft_id}",
        )
    assert excinfo.value.reason == "not_found"

    hidden = service.search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search", identity=other_identity), query="epsilon"
    )
    assert hidden.results == ()


# ===========================================================================
# KMCP-3.3: Run projection matrix
# ===========================================================================


def test_run_projector_resolves_visible_run_with_allowlisted_fields(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_km_alpha")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_alpha", sensitivity="public")

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")

    doc = service.fetch_extended(context, knowledge_id="rfk:v1:run:rf_run_km_alpha")
    assert doc.kind == "run"
    assert doc.rf_metadata is not None
    assert doc.rf_metadata["provenance"] == {"run_id": "rf_run_km_alpha", "intent_id": "intent_test001"}
    assert doc.text is not None
    assert "status:" in doc.text
    # No raw artifact path ever leaks (export_run never emits one either).
    assert "/abs/POISON" not in json.dumps(doc.to_dict())


def test_run_projector_search_and_fetch_resolve_same_resource(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_km_beta")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_beta", sensitivity="public")

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="beta")
    assert len(outcome.results) == 1
    found = outcome.results[0]
    assert found.kind == "run"

    doc = service.fetch_extended(ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id=found.id)
    assert doc.id == found.id
    assert doc.url == found.url


def test_run_projector_hides_run_above_sensitivity_threshold(tmp_foundry: FoundryPaths) -> None:
    """``export_run``'s own ``sensitivity_threshold`` only redacts per-claim
    text; the projector must ALSO hide the run record itself once its own
    declared sensitivity exceeds the caller's ceiling (mirrors
    ``api/routers/runs.py``'s ``_enforce_existence_gate``)."""

    build_run(tmp_foundry, "rf_run_km_gamma")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_gamma", sensitivity="client_sensitive")

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch", sensitivity_threshold="public"),
            knowledge_id="rfk:v1:run:rf_run_km_gamma",
        )
    assert excinfo.value.reason == "not_found"

    hidden = service.search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search", sensitivity_threshold="public"), query="gamma"
    )
    assert hidden.results == ()

    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch", sensitivity_threshold="client_sensitive"),
        knowledge_id="rfk:v1:run:rf_run_km_gamma",
    )
    assert doc.id == "rfk:v1:run:rf_run_km_gamma"


def test_run_projector_cross_workspace_denies_with_generic_shape(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _force_isolation_active(monkeypatch)
    build_run(tmp_foundry, "rf_run_km_delta")
    # Deliberately no `visibility: public` -- a genuinely private DF-004
    # target, never a bypass via the visibility short-circuit.
    _set_run_yaml_fields(
        tmp_foundry, "rf_run_km_delta", sensitivity="public", workspace_id="workspace-run-mine"
    )

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    other_identity = AuthIdentity("bob", "workspace-run-other", ("viewer",))

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch", identity=other_identity),
            knowledge_id="rfk:v1:run:rf_run_km_delta",
        )
    assert excinfo.value.reason == "not_found"

    hidden = service.search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search", identity=other_identity), query="delta"
    )
    assert hidden.results == ()


def test_run_projector_missing_run_denies_without_writes(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _snapshot_tree(tmp_foundry.root)
    _install_write_surface_spies(monkeypatch)
    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        service.fetch_extended(
            ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id="rfk:v1:run:ci_doesnotexist0"
        )
    assert excinfo.value.reason == "not_found"
    assert _snapshot_tree(tmp_foundry.root) == before


# ===========================================================================
# KMCP-3.4: Search/fetch composer -- cursor paging, receipt, deterministic
# merge, byte-equivalent replay
# ===========================================================================


def test_paginate_document_text_first_page_under_cap_is_untruncated() -> None:
    text = "abcdefghij" * 50
    page, next_cursor, truncated = ka._paginate_document_text(text, None)
    assert page == text
    assert next_cursor is None
    assert truncated is False


def test_paginate_document_text_pages_across_byte_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ka, "DOCUMENT_MAX_TEXT_BYTES", 10)
    text = "0123456789ABCDEFGHIJ"  # 20 ASCII bytes

    page1, cursor1, truncated1 = ka._paginate_document_text(text, None)
    assert page1 == "0123456789"
    assert truncated1 is True
    assert cursor1 == "10"

    page2, cursor2, truncated2 = ka._paginate_document_text(text, cursor1)
    assert page2 == "ABCDEFGHIJ"
    assert truncated2 is False
    assert cursor2 is None
    assert page1 + page2 == text

    # Replaying from cursor=None again reproduces the identical first page
    # (KMCP-3.4's "same snapshot replays byte-equivalent").
    page1_again, cursor1_again, truncated1_again = ka._paginate_document_text(text, None)
    assert (page1_again, cursor1_again, truncated1_again) == (page1, cursor1, truncated1)


def test_paginate_document_text_rejects_malformed_cursor() -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka._paginate_document_text("hello", "not-a-number")


def test_paginate_document_text_rejects_out_of_range_cursor() -> None:
    with pytest.raises(ka.KnowledgeRequestError):
        ka._paginate_document_text("hello", "999")


def test_run_projector_fetch_supports_cursor_paging(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ka, "DOCUMENT_MAX_TEXT_BYTES", 20)
    build_run(tmp_foundry, "rf_run_km_paged")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_paged", sensitivity="public")

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")

    first = service.fetch_extended(context, knowledge_id="rfk:v1:run:rf_run_km_paged")
    assert first.truncated is True
    assert first.next_cursor is not None

    second = service.fetch_extended(
        context, knowledge_id="rfk:v1:run:rf_run_km_paged", cursor=first.next_cursor
    )
    assert second.text != first.text

    replay = service.fetch_extended(context, knowledge_id="rfk:v1:run:rf_run_km_paged")
    assert replay.text == first.text
    assert replay.next_cursor == first.next_cursor


def test_core_search_stays_snippet_free_with_report_and_run_registered(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_km_core01")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_core01", sensitivity="public")
    builder_service.create_draft(tmp_foundry, title="Core Snippet Free Report", sensitivity="public")

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    ka.register_projector("report_draft", ka.ReportKindProjector(tmp_foundry, target_kind="report_draft"))
    service = ka.KnowledgeAccessService(tmp_foundry)

    response = service.search_core(ka.resolve_context(tmp_foundry, tool="search"), query="core01")
    assert len(response.results) >= 1
    for item in response.results:
        assert "snippet" not in item.to_dict()


def test_composer_orders_mixed_kinds_deterministically(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_zzzmarker_x")
    _set_run_yaml_fields(tmp_foundry, "rf_run_zzzmarker_x", sensitivity="public")
    builder_service.create_draft(tmp_foundry, title="Zzzmarker Draft Report", sensitivity="public")

    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    ka.register_projector("report_draft", ka.ReportKindProjector(tmp_foundry, target_kind="report_draft"))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="zzzmarker")
    kinds_in_order = [item.kind for item in outcome.results]
    assert kinds_in_order == ["report_draft", "run"]


def test_receipt_defaults_to_none_preserving_backward_compatible_equality(tmp_foundry: FoundryPaths) -> None:
    """Every KMCP-2.4/3.1/3.2 caller that never passes ``include_receipt``
    keeps getting a receipt-less outcome, so its bare-literal equality checks
    (``== RfKnowledgeSearchOutcome(...)``) never break."""

    service = ka.KnowledgeAccessService(tmp_foundry)
    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="anything")
    assert outcome.receipt is None
    assert outcome == ka.RfKnowledgeSearchOutcome(results=(), next_cursor=None, truncated=False)

    doc_context = ka.resolve_context(tmp_foundry, tool="rf_fetch")
    with pytest.raises(ka.KnowledgeDenied):
        service.fetch_extended(doc_context, knowledge_id="rfk:v1:run:abc")


def test_search_receipt_included_on_request_validates_against_its_own_schema(
    tmp_foundry: FoundryPaths, registry: SchemaRegistry
) -> None:
    build_run(tmp_foundry, "rf_run_km_receipt01")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_receipt01", sensitivity="public")
    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(
        ka.resolve_context(tmp_foundry, tool="rf_search"),
        query="receipt01",
        include_receipt=True,
        parent_run_ref="rf_run_correlation_ref",
    )
    assert outcome.receipt is not None
    result = registry.validate(outcome.receipt, "knowledge_activity_receipt")
    assert result.ok, result.errors
    assert outcome.receipt["tool"] == "rf_search"
    assert outcome.receipt["persisted"] is False
    assert outcome.receipt["returned_ids"] == [item.id for item in outcome.results]
    assert outcome.receipt["correlation_ref"] == "rf_run_correlation_ref"
    assert outcome.receipt["bounds"]["results_returned"] == len(outcome.results)
    assert outcome.receipt["bounds"]["truncated"] == outcome.truncated
    # Core search never carries this slot at all (invariant 5).
    assert "receipt" not in ka.KnowledgeSearchResponse().to_dict()


def test_fetch_receipt_included_on_request_validates_against_its_own_schema(
    tmp_foundry: FoundryPaths, registry: SchemaRegistry
) -> None:
    build_run(tmp_foundry, "rf_run_km_receipt02")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_receipt02", sensitivity="public")
    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch"),
        knowledge_id="rfk:v1:run:rf_run_km_receipt02",
        include_receipt=True,
    )
    assert doc.receipt is not None
    result = registry.validate(doc.receipt, "knowledge_activity_receipt")
    assert result.ok, result.errors
    assert doc.receipt["tool"] == "rf_fetch"
    assert doc.receipt["returned_ids"] == [doc.id]
    assert doc.receipt["bounds"]["results_returned"] == 1
    assert doc.receipt["bounds"]["results_max"] == 1
    assert doc.receipt["bounds"]["text_bytes_returned"] == len(doc.text.encode("utf-8"))
    assert doc.receipt["bounds"]["text_bytes_max"] == ka.DOCUMENT_MAX_TEXT_BYTES


def test_search_replay_is_byte_equivalent_across_calls(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_km_replay01")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_replay01", sensitivity="public")
    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_search")

    first = service.search_extended(context, query="replay01", include_receipt=True)
    second = service.search_extended(context, query="replay01", include_receipt=True)

    assert first.results == second.results
    assert first.truncated == second.truncated
    assert first.receipt is not None and second.receipt is not None
    assert first.receipt["request_context_hash"] == second.receipt["request_context_hash"]
    assert first.receipt["returned_ids"] == second.receipt["returned_ids"]
    assert first.receipt["bounds"] == second.receipt["bounds"]
    # `generated_at` is the ONE field that legitimately varies between two
    # calls against the same snapshot -- deliberately not asserted equal.


def test_fetch_replay_is_byte_equivalent_across_calls(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_km_replay02")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_replay02", sensitivity="public")
    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="rf_fetch")

    first = service.fetch_extended(
        context, knowledge_id="rfk:v1:run:rf_run_km_replay02", include_receipt=True
    )
    second = service.fetch_extended(
        context, knowledge_id="rfk:v1:run:rf_run_km_replay02", include_receipt=True
    )

    assert first.text == second.text
    assert first.id == second.id
    assert first.receipt is not None and second.receipt is not None
    assert first.receipt["request_context_hash"] == second.receipt["request_context_hash"]
    assert first.receipt["bounds"] == second.receipt["bounds"]


# ===========================================================================
# KMCP-6.4 gap-fill: `content_is_untrusted` marker (KMCP-FR-11)
# ===========================================================================
#
# `content_is_untrusted` is a hardcoded constant inside
# `RfKnowledgeSearchResultItem.to_dict()` / `RfKnowledgeDocument.to_dict()`
# (never a stored field an adapter could construct as `False`), but no test
# anywhere had ever actually asserted its presence -- these close that gap at
# both the DTO level (cheap, no fixture) and end-to-end through a real
# `rf_search`/`rf_fetch` call (proves no call site strips or overrides it).


def test_rf_search_result_item_and_document_always_mark_content_untrusted() -> None:
    item = ka.RfKnowledgeSearchResultItem(
        id="rfk:v1:run:km_untrusted_marker",
        title="Untrusted Marker Example",
        url=ka.build_local_resource_url("rfk:v1:run:km_untrusted_marker", origin="http://127.0.0.1"),
        kind="run",
    )
    assert item.to_dict()["content_is_untrusted"] is True

    doc = ka.RfKnowledgeDocument(
        id="rfk:v1:run:km_untrusted_marker",
        title="Untrusted Marker Example",
        url=ka.build_local_resource_url("rfk:v1:run:km_untrusted_marker", origin="http://127.0.0.1"),
        kind="run",
        text="body",
    )
    assert doc.to_dict()["content_is_untrusted"] is True


def test_content_is_untrusted_marker_survives_real_search_and_fetch_calls(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_km_untrusted01")
    _set_run_yaml_fields(tmp_foundry, "rf_run_km_untrusted01", sensitivity="public")
    ka.register_projector("run", ka.RunKindProjector(tmp_foundry))
    service = ka.KnowledgeAccessService(tmp_foundry)

    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="untrusted01")
    assert len(outcome.results) == 1
    assert outcome.results[0].to_dict()["content_is_untrusted"] is True

    doc = service.fetch_extended(
        ka.resolve_context(tmp_foundry, tool="rf_fetch"), knowledge_id="rfk:v1:run:rf_run_km_untrusted01"
    )
    assert doc.to_dict()["content_is_untrusted"] is True


# ===========================================================================
# KMCP-6.4 gap-fill: core roots reject additional properties (AC KMCP-2
# resilience: "Additional core arguments and non-contract root/result fields
# fail schema validation"). Positive round-trips already exist above
# (test_core_search_response_round_trips / test_core_document_round_trips /
# test_search_ignores_extra_argument_values_silently in
# tests/unit/test_knowledge_mcp_registry.py); these are the missing NEGATIVE
# half at the schema-file level itself, which no test had exercised for any
# of the four closed core roots -- including
# `knowledge_search_request.schema.yaml`, which had ZERO prior test coverage
# of any kind (core `search`'s input is a plain `query: str` function arg at
# every transport, so nothing had ever validated a request dict against this
# schema file directly).
# ===========================================================================


def test_core_search_request_root_rejects_additional_properties(registry: SchemaRegistry) -> None:
    valid = registry.validate({"query": "hello"}, "knowledge_search_request")
    assert valid.ok, valid.errors

    result = registry.validate({"query": "hello", "kind": "source"}, "knowledge_search_request")
    assert not result.ok, "expected additionalProperties:false to reject an unknown field"


def test_core_search_response_root_rejects_additional_properties(registry: SchemaRegistry) -> None:
    result = registry.validate({"results": [], "next_cursor": None}, "knowledge_search_response")
    assert not result.ok, "expected additionalProperties:false to reject an unknown root field"


def test_core_search_result_item_rejects_additional_properties(registry: SchemaRegistry) -> None:
    schema = _subschema(registry.get("knowledge_search_response"), "core_search_result_item")
    validator = jsonschema.Draft202012Validator(schema)

    valid_item = {
        "id": "rfk:v1:source:abc",
        "title": "Example",
        "url": "http://127.0.0.1/api/knowledge/v1/fetch/rfk%3Av1%3Asource%3Aabc",
    }
    assert not list(validator.iter_errors(valid_item))

    poisoned_item = {**valid_item, "snippet": "should not be allowed on the core item"}
    errors = list(validator.iter_errors(poisoned_item))
    assert errors, "expected additionalProperties:false to reject a snippet field on the core item"


def test_core_fetch_request_root_rejects_additional_properties(registry: SchemaRegistry) -> None:
    schema = _subschema(registry.get("knowledge_document"), "core_fetch_request")
    validator = jsonschema.Draft202012Validator(schema)

    assert not list(validator.iter_errors({"id": "rfk:v1:run:abc"}))

    for poisoned in (
        {"id": "rfk:v1:run:abc", "cursor": "0"},
        {"id": "rfk:v1:run:abc", "page": 1},
        {"id": "rfk:v1:run:abc", "receipt": {}},
    ):
        errors = list(validator.iter_errors(poisoned))
        assert errors, f"expected additionalProperties:false to reject {poisoned!r}"


def test_core_document_root_rejects_non_contract_fields(registry: SchemaRegistry) -> None:
    """The frozen `FetchDTO` root itself stays closed even though its OWN
    `metadata` map is an intentionally open bag (see
    `test_core_document_metadata_slot_accepts_arbitrary_keys_when_present` in
    `tests/test_knowledge_mcp_process.py` for the open-map half of this
    contract)."""

    valid = {
        "id": "rfk:v1:run:abc",
        "title": "Example",
        "text": "body",
        "url": "http://127.0.0.1/api/knowledge/v1/fetch/rfk%3Av1%3Arun%3Aabc",
    }
    assert registry.validate(valid, "knowledge_document").ok

    for extra_field, extra_value in (("kind", "run"), ("cursor", "0"), ("receipt", {}), ("snippet", "x")):
        poisoned = {**valid, extra_field: extra_value}
        result = registry.validate(poisoned, "knowledge_document")
        assert not result.ok, f"expected additionalProperties:false to reject root field {extra_field!r}"
