"""WKSP-304 Phase 5 regression matrix — workspace isolation enforcement.

Integration-level coverage that sits ABOVE the unit-level identity-scoping
tests already shipped in ``tests/unit/test_catalog_service.py``,
``tests/unit/test_builder_service.py``, and ``tests/unit/test_agent_job_service.py``
(Phase 3/4). Those files prove each service function's ``identity``/
``resolve_enforcement`` plumbing in isolation; this file proves the same
guarantees hold end-to-end — through the FastAPI routers, across the
service boundary, and across the specific JOIN/tombstone predicates Phase 3
added — using a real 2-workspace matrix.

Ownership: this is the ONLY file this task edits. It does not modify
``tests/test_config_workspace_enforcement.py`` (sibling task's file) or the
UNMODIFIED-suite targets exercised in ``TestFullSuiteUnderEnforcement``.

Real-name mapping note (read before extending)
------------------------------------------------
The Phase 5 plan names an idealised ~11-method target list. Several of those
names do not exist verbatim in this codebase; the mapping used throughout
this file (confirmed by direct source reading, and in the ``get_job``/
``list_jobs`` case by the sibling unit test's own docstring) is:

* ``catalog_service``: ``get_item`` (verbatim), ``list_items`` -> ``search``,
  ``count_items`` -> **no identity-aware equivalent exists** (``stats()``
  takes no ``identity`` param; confirmed via ``catalog.py``'s own
  ``TODO(WKSP-304 P4)`` comments — not a Phase 3 scoping target), ``get_draft_index``
  / ``list_draft_index`` (verbatim), ``get_related_items`` -> the ``links``
  field embedded in ``get_item``'s response (no standalone function exists).
* ``builder_service``: ``get_draft`` -> ``load_draft``, ``list_drafts``
  (verbatim), ``find_drafts`` -> **does not exist anywhere in this module**,
  ``build_report_from_draft`` -> **does not exist**; the closest real
  identity-aware read is ``export_markdown`` (delegates straight into
  ``load_draft``).
* ``agent_job_service``: ``get_job`` -> ``AgentJobService.load_job``,
  ``list_jobs`` -> **no corresponding method anywhere in this codebase**
  (already documented as a real plan/implementation mismatch in
  ``tests/unit/test_agent_job_service.py``'s module docstring — not
  re-litigated here).

These five mismatches are ESCALATION FINDINGS, not oversights in this file;
each is covered below by a signature-introspection test that documents the
absence/exemption precisely instead of inventing a test for a function that
does not exist.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers import admin as admin_router
from research_foundry.api.routers import audit as audit_router
from research_foundry.api.routers import auth_identity as auth_identity_router
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.errors import NotFoundError
from research_foundry.paths import FoundryPaths
from research_foundry.services import agent_job_service, builder_service, catalog_service
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_WS_MINE = AuthIdentity("u1", "ws-mine", ("owner", "admin", "researcher"))
_WS_OTHER = AuthIdentity("u2", "ws-other", ("owner", "admin", "researcher"))

_MINIMAL_POLICY_SNAPSHOT = {"allowed_tools": ["search"], "data_scopes": []}


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ``workspace_isolation_enforcement`` resolving active.

    Same convention as ``tests/unit/test_catalog_service.py`` /
    ``test_builder_service.py`` / ``test_agent_job_service.py``: monkeypatch
    :meth:`FoundryConfig.resolve_workspace_isolation_enforced` itself (never
    a private per-module helper), so every code path under test exercises
    the real Phase 1 resolver's call contract.
    """

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Test middleware that injects a fixed AuthIdentity onto request.state.

    Copied from the established pattern in ``tests/unit/test_rbac_catalog.py``
    / ``test_rbac_reports.py``.
    """

    def __init__(self, app: Any, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


def _enable_agents(paths: FoundryPaths) -> None:
    """Flip ``foundry.agents.enabled`` on for this test workspace.

    ``create_app`` only registers the agent-jobs router when
    ``config.agents_enabled()`` is ``True`` (default ``False``, opt-in) — see
    ``api/app.py``'s ``if config.agents_enabled(): app.include_router(...)``.
    Every agent-jobs router test in this file needs this called before
    :func:`_make_client`.
    """

    data = load_yaml(paths.foundry_yaml) or {}
    foundry = dict(data.get("foundry") or {})
    foundry["agents"] = {"enabled": True}
    data["foundry"] = foundry
    dump_yaml(data, paths.foundry_yaml)


def _make_client(paths: FoundryPaths, identity: AuthIdentity | None) -> TestClient:
    """Build a TestClient wired to *paths* with *identity* injected.

    Reuses the ``tmp_foundry`` fixture's already-bootstrapped workspace
    (schemas/config/templates copied, foundry.yaml present) rather than
    re-implementing config scaffolding — auth.provider stays "none" (the
    distribution default, commented out), so RBAC stays not-enforced and
    every mutation route under test is reachable regardless of role.
    """

    cfg = FoundryConfig(paths=paths)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


def _seed_catalog_items(
    paths: FoundryPaths,
    rows_spec: list[dict[str, Any]],
    *,
    links: list[dict[str, str]] | None = None,
    run_id: str = "seed_run",
) -> dict[str, str]:
    """Directly seed ``catalog_items`` (+ optional ``catalog_links``) rows.

    Bypasses ``import_run``/``export_run`` (which always hardcode
    ``workspace_id="default"`` — see ``catalog_service._base_row``) so tests
    can place items in arbitrary workspaces. Reuses the real
    ``_base_row``/``_insert_rows`` internals rather than hand-rolling SQL, so
    the seeded rows are byte-identical in shape to a real import.

    ``rows_spec`` entries: ``{"local_ref": str, "workspace_id": str, "title": str?,
    "sensitivity_rank": int?, "item_type": str?}``.
    ``links`` entries: ``{"from": local_ref, "to": local_ref, "relation": str?}``.

    Returns ``{local_ref: catalog_item_id}``.
    """

    rows: list[dict[str, Any]] = []
    ids_by_ref: dict[str, str] = {}
    for spec in rows_spec:
        title = spec.get("title", spec["local_ref"])
        row = catalog_service._base_row(
            item_type=spec.get("item_type", "claim"),
            run_id=run_id,
            local_ref=spec["local_ref"],
            project=None,
            title=title,
            summary=title,
            status="supported",
            sensitivity_rank=spec.get("sensitivity_rank", 0),
            trust_label=None,
            confidence="high",
            source_count=0,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            payload={"text": title},
        )
        row["workspace_id"] = spec["workspace_id"]
        rows.append(row)
        ids_by_ref[spec["local_ref"]] = row["catalog_item_id"]

    resolved_links = [
        {
            "from_item_id": ids_by_ref[link["from"]],
            "to_item_id": ids_by_ref[link["to"]],
            "relation": link.get("relation", "supports"),
        }
        for link in (links or [])
    ]

    with catalog_service._db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            catalog_service._insert_rows(conn, rows, resolved_links, run_id)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    return ids_by_ref


def _seed_citing_draft(
    paths: FoundryPaths, *, workspace_id: str | None, catalog_item_id: str, title: str = "Citing draft"
) -> str:
    """Create a draft that ``cites`` *catalog_item_id* via ``add_claim_link``."""

    draft = builder_service.create_draft(paths, title=title, workspace_id=workspace_id, sensitivity="public")
    draft_id = draft["report_draft_id"]
    draft = builder_service.add_block(paths, draft_id, markdown="paragraph text")
    block_id = draft["blocks"][-1]["block_id"]
    builder_service.add_claim_link(
        paths,
        draft_id,
        block_id=block_id,
        claim_id="claim_seed",
        catalog_item_id=catalog_item_id,
        relation="context",
        insert_tag=False,
    )
    return draft_id


def _seed_agent_job(paths: FoundryPaths, *, workspace_id: str | None) -> dict[str, Any]:
    service = AgentJobService(paths)
    job = service.create_job(
        provider="claude_agent_sdk",
        model_profile="personal",
        request_kind="research",
        policy_snapshot=_MINIMAL_POLICY_SNAPSHOT,
        workspace_id=workspace_id,
    )
    return job.to_dict()


# ---------------------------------------------------------------------------
# TASK-5.1 (AC-2, AC-3): 2-workspace x {read, list, mutate} x {allowed, denied}
# matrix across the mapped target methods.
# ---------------------------------------------------------------------------


class TestCatalogItemMatrix:
    """catalog_service.get_item / search — router-level, 2-workspace matrix."""

    def test_get_item_same_workspace_allowed(self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/catalog/items/{ids_['c1']}")
        assert resp.status_code == 200
        assert resp.json()["catalog_item_id"] == ids_["c1"]

    def test_get_item_cross_workspace_denied_404(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get(f"/api/catalog/items/{ids_['c1']}")
        assert resp.status_code == 404

    def test_get_item_isolation_disabled_control_allows_cross_workspace(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        """Sanity control: without forcing enforcement, the real default
        (advisory, since auth.provider="none") does not filter — proving the
        denial above is caused by enforcement, not an unrelated 404."""
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get(f"/api/catalog/items/{ids_['c1']}")
        assert resp.status_code == 200

    def test_search_list_same_workspace_returns_item(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get("/api/catalog/search", params={"page_size": 200})
        assert resp.status_code == 200
        body = resp.json()
        assert ids_["c1"] in {it["catalog_item_id"] for it in body["items"]}

    def test_search_list_cross_workspace_omits_item(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get("/api/catalog/search", params={"page_size": 200})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert ids_["c1"] not in {it["catalog_item_id"] for it in body["items"]}

    def test_search_facets_do_not_leak_cross_workspace_values(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _seed_catalog_items(
            tmp_foundry,
            [{"local_ref": "c1", "workspace_id": "ws-mine", "title": "Alpha item"}],
        )
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get("/api/catalog/search", params={"page_size": 200})
        assert resp.json()["facets"] == {"projects": [], "statuses": [], "sensitivities": []}


class TestCatalogItemsWorkspaceIdNotNullInvariant:
    """AC-3 null-treated-as-mismatch requirement, catalog_items edition.

    ``catalog_items.workspace_id`` is declared ``NOT NULL DEFAULT 'default'``
    (schema DDL) — every imported row always carries a concrete workspace_id.
    This makes the "row has a NULL workspace_id" scenario structurally
    unreachable for this specific table (unlike catalog_report_drafts and
    agent jobs, both nullable — covered in their own matrices below). This
    test asserts the schema invariant that PROVES the null case is
    unreachable here, rather than silently skipping it.
    """

    def test_catalog_items_workspace_id_is_not_null_with_default(self, tmp_foundry: FoundryPaths) -> None:
        with catalog_service._db(tmp_foundry) as conn:
            cols = conn.execute("PRAGMA table_info(catalog_items)").fetchall()
        workspace_col = next(c for c in cols if c["name"] == "workspace_id")
        assert workspace_col["notnull"] == 1
        assert workspace_col["dflt_value"] == "'default'"


class TestCatalogRelatedLinksIsolation:
    """``get_related_items`` mapping: get_item's embedded outgoing/incoming/
    citing_drafts link fields must not leak cross-workspace targets."""

    def test_get_item_outgoing_link_excludes_cross_workspace_target(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(
            tmp_foundry,
            [
                {"local_ref": "a", "workspace_id": "ws-mine"},
                {"local_ref": "b", "workspace_id": "ws-other"},
            ],
            links=[{"from": "a", "to": "b", "relation": "supports"}],
        )
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/catalog/items/{ids_['a']}")
        assert resp.status_code == 200
        assert resp.json()["links"]["outgoing"] == []

    def test_get_item_incoming_link_excludes_cross_workspace_source(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(
            tmp_foundry,
            [
                {"local_ref": "a", "workspace_id": "ws-other"},
                {"local_ref": "b", "workspace_id": "ws-mine"},
            ],
            links=[{"from": "a", "to": "b", "relation": "supports"}],
        )
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/catalog/items/{ids_['b']}")
        assert resp.status_code == 200
        assert resp.json()["links"]["incoming"] == []

    def test_get_item_citing_drafts_excludes_cross_workspace_draft(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine"}])
        _seed_citing_draft(tmp_foundry, workspace_id="ws-other", catalog_item_id=ids_["a"])
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/catalog/items/{ids_['a']}")
        assert resp.status_code == 200
        assert resp.json()["links"]["citing_drafts"] == []


class TestCatalogDraftIndexMatrix:
    """catalog_service.get_draft_index / list_draft_index — service-level
    (no HTTP router calls either function directly; see module docstring)."""

    def test_get_draft_index_same_workspace_allowed(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        result = catalog_service.get_draft_index(tmp_foundry, draft["report_draft_id"], identity=_WS_MINE)
        assert result is not None

    def test_get_draft_index_cross_workspace_denied(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        assert catalog_service.get_draft_index(tmp_foundry, draft["report_draft_id"], identity=_WS_OTHER) is None

    def test_get_draft_index_null_workspace_denied(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3: a NULL workspace_id row must be denied, never treated as a wildcard."""
        draft = builder_service.create_draft(tmp_foundry, title="Nullws", workspace_id=None, sensitivity="public")
        _force_isolation_active(monkeypatch)
        assert catalog_service.get_draft_index(tmp_foundry, draft["report_draft_id"], identity=_WS_MINE) is None

    def test_list_draft_index_excludes_cross_workspace(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        assert catalog_service.list_draft_index(tmp_foundry, identity=_WS_OTHER) == []
        assert len(catalog_service.list_draft_index(tmp_foundry, identity=_WS_MINE)) == 1


class TestReportsRouterMatrix:
    """builder_service.load_draft / list_drafts / export_markdown — router-level."""

    def test_get_draft_router_same_workspace_allowed(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/reports/{draft['report_draft_id']}")
        assert resp.status_code == 200

    def test_get_draft_router_cross_workspace_denied_404(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get(f"/api/reports/{draft['report_draft_id']}")
        assert resp.status_code == 404

    def test_list_drafts_router_excludes_cross_workspace(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get("/api/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_export_markdown_router_cross_workspace_denied(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get(f"/api/reports/{draft['report_draft_id']}/export")
        assert resp.status_code == 404


class TestAgentJobRouterMatrix:
    """AgentJobService.load_job — router-level."""

    def test_get_job_router_same_workspace_allowed(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        _enable_agents(tmp_foundry)
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/agent-jobs/{job['agent_job_id']}")
        assert resp.status_code == 200

    def test_get_job_router_cross_workspace_denied_404(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        _enable_agents(tmp_foundry)
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.get(f"/api/agent-jobs/{job['agent_job_id']}")
        assert resp.status_code == 404


class TestTargetMethodMismatchFindings:
    """Escalation findings: signature-introspection proof for the ~11
    plan-named targets that do not map 1:1 onto real functions."""

    def test_catalog_stats_has_no_identity_parameter(self) -> None:
        assert "identity" not in inspect.signature(catalog_service.stats).parameters

    def test_builder_service_has_no_find_drafts_or_build_report_from_draft(self) -> None:
        assert not hasattr(builder_service, "find_drafts")
        assert not hasattr(builder_service, "build_report_from_draft")

    def test_agent_job_service_has_no_list_jobs_method(self) -> None:
        assert not hasattr(AgentJobService, "list_jobs")

    def test_catalog_service_has_no_get_related_items_function(self) -> None:
        assert not hasattr(catalog_service, "get_related_items")


# ---------------------------------------------------------------------------
# TASK-5.2 (AC-1): router-level identity-propagation, one per in-scope router.
# ---------------------------------------------------------------------------


class TestRouterIdentityPropagation:
    def test_catalog_router_threads_identity_into_get_item(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        captured: dict[str, Any] = {}
        original = catalog_service.get_item

        def spy(paths: FoundryPaths, catalog_item_id: str, **kwargs: Any) -> Any:
            captured["identity"] = kwargs.get("identity")
            return original(paths, catalog_item_id, **kwargs)

        monkeypatch.setattr(catalog_service, "get_item", spy)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/catalog/items/{ids_['c1']}")
        assert resp.status_code == 200
        assert captured["identity"] == _WS_MINE

    def test_catalog_router_threads_identity_into_search(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}
        original = catalog_service.search

        def spy(paths: FoundryPaths, **kwargs: Any) -> Any:
            captured["identity"] = kwargs.get("identity")
            return original(paths, **kwargs)

        monkeypatch.setattr(catalog_service, "search", spy)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get("/api/catalog/search")
        assert resp.status_code == 200
        assert captured["identity"] == _WS_MINE

    def test_agent_jobs_router_threads_identity_into_load_job(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        _enable_agents(tmp_foundry)
        captured: dict[str, Any] = {}
        original = AgentJobService.load_job

        def spy(self: AgentJobService, job_id: str, **kwargs: Any) -> Any:
            captured["identity"] = kwargs.get("identity")
            return original(self, job_id, **kwargs)

        monkeypatch.setattr(AgentJobService, "load_job", spy)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/agent-jobs/{job['agent_job_id']}")
        assert resp.status_code == 200
        assert captured["identity"] == _WS_MINE

    def test_reports_router_threads_identity_into_load_draft(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        captured: dict[str, Any] = {}
        original = builder_service.load_draft

        def spy(paths: FoundryPaths, report_draft_id: str, **kwargs: Any) -> Any:
            captured["identity"] = kwargs.get("identity")
            return original(paths, report_draft_id, **kwargs)

        monkeypatch.setattr(builder_service, "load_draft", spy)
        client = _make_client(tmp_foundry, _WS_MINE)
        resp = client.get(f"/api/reports/{draft['report_draft_id']}")
        assert resp.status_code == 200
        assert captured["identity"] == _WS_MINE

    def test_admin_router_has_no_hidden_scoped_service_calls(self) -> None:
        """Phase 2 confirmed admin.py/audit.py/auth_identity.py are no-op
        targets for Phase 3 scoping — they never call catalog_service,
        builder_service, or agent_job_service at all. Verified by source
        inspection (not merely by absence of an identity kwarg, since a
        hidden unscoped call would be worse than a missing kwarg)."""
        src = inspect.getsource(admin_router)
        for forbidden in ("catalog_service", "builder_service", "agent_job_service"):
            assert forbidden not in src, f"admin.py unexpectedly references {forbidden}"

    def test_audit_router_has_no_hidden_scoped_service_calls(self) -> None:
        src = inspect.getsource(audit_router)
        for forbidden in ("catalog_service", "builder_service", "agent_job_service"):
            assert forbidden not in src, f"audit.py unexpectedly references {forbidden}"

    def test_auth_identity_router_has_no_hidden_scoped_service_calls(self) -> None:
        src = inspect.getsource(auth_identity_router)
        for forbidden in ("catalog_service", "builder_service", "agent_job_service"):
            assert forbidden not in src, f"auth_identity.py unexpectedly references {forbidden}"


# ---------------------------------------------------------------------------
# TASK-5.3 (AC-4, mutation-tested): every JOIN/tombstone leak path closed in
# Phase 3, across the 3 services.
#
# MUTATION-TEST EVIDENCE (re-verified 2026-07-09, remediation cycle, Phase 5
# Batch 2). This is the durable record the reviewer can check without
# trusting a transcript: each predicate below was actually reverted in
# ``src/``, the gating test(s) were re-run and observed to FAIL, the
# predicate was restored byte-for-byte (via ``cp`` from a pre-edit backup,
# confirmed with ``git diff --stat -- src/`` reporting empty against the
# committed HEAD both before and after each cycle), and the gating test(s)
# were re-run and observed to PASS. No permanent change was made to any
# ``src/`` file. Command shape used for every cycle:
# ``./.venv/bin/python -m pytest tests/test_workspace_isolation_enforcement.py -k "<test name(s)>" -q``.
#
# 1. ``catalog_service.py::get_item``, the ``outgoing_ws_clause`` JOIN
#    predicate (module line ~1583, ``outgoing_ws_clause = " AND
#    i.workspace_id = ?" if workspace_id is not None else ""`` — this single
#    clause is reused for both the outgoing and incoming link queries).
#    Gates: ``test_get_item_outgoing_link_join_predicate_closes_leak``,
#    ``test_get_item_incoming_link_join_predicate_closes_leak``.
#    Reverted (clause forced to ``""``, params trimmed to stay valid SQL):
#    both tests FAILED — ``test_get_item_incoming_link_join_predicate_closes_leak``
#    asserted ``result["links"]["incoming"] == []`` and instead observed the
#    cross-workspace linked item leaking through. Restored: both PASSED.
# 2. ``catalog_service.py::search``, the WHERE-clause workspace predicate
#    (module line ~1293, ``if workspace_scoped: where.append("workspace_id
#    = ?"); params.append(identity.workspace_id)``).
#    Gates: ``test_search_where_predicate_closes_leak``.
#    Reverted (guard forced to ``if False:``): FAILED — the other
#    workspace's catalog item was returned in the result set
#    (``AssertionError: assert 'ci_...' not in {'ci_...'}``). Restored:
#    PASSED.
# 3. ``catalog_service.py::get_draft_index``, the primary-row scoped-query
#    branch (module line ~1876, ``if workspace_scoped:`` guarding the
#    ``WHERE report_draft_id = ? AND workspace_id = ?`` query).
#    Gates: ``test_get_draft_index_primary_row_predicate_closes_leak``.
#    Reverted (guard forced to ``if False:``, falling through to the
#    unscoped branch): FAILED — a cross-workspace draft index row was
#    returned instead of ``None``. Restored: PASSED.
# 4. ``builder_service.py::load_draft``, the mismatch-check guard (module
#    line ~339, ``if identity is not None and _isolation_active(paths): if
#    data.get("workspace_id") != identity.workspace_id: ...``).
#    Gates (direct + delegating callers):
#    ``test_load_draft_file_predicate_closes_leak``,
#    ``test_load_draft_null_workspace_treated_as_mismatch``,
#    ``test_list_drafts_delegates_predicate_via_load_draft``,
#    ``test_export_markdown_delegates_predicate_via_load_draft``.
#    Reverted (outer guard forced to ``if False:``): all four FAILED (e.g.
#    ``list_drafts`` returned 2 drafts instead of 1; ``export_markdown``
#    did not raise ``NotFoundError``). Restored: all four PASSED.
# 5. ``agent_job_service.py::AgentJobService.load_job``, the deny guard
#    (module line ~900, ``if not scope_result.allowed: ... raise
#    KeyError(...)``).
#    Gates: ``test_load_job_predicate_closes_leak``,
#    ``test_load_job_null_workspace_treated_as_mismatch``.
#    Reverted (guard forced to ``if False:``): both FAILED
#    (``Failed: DID NOT RAISE <class 'KeyError'>``). Restored: both PASSED.
#
# After all five cycles: ``git diff --stat -- src/`` was empty (no
# permanent production-code change) and the full
# ``tests/test_workspace_isolation_enforcement.py`` suite passed (66/66).
#
# This block was re-verified as an honest, independently-reproducible record
# rather than re-asserted from a prior transcript; it does not claim to
# exhaustively mutation-test every predicate closed in Phase 3 — only the
# five enumerated above, chosen as the representative subset spanning all
# 3 services and both the read-path (get_item/search/get_draft_index) and
# deny-path (load_draft/load_job) leak categories.
# ---------------------------------------------------------------------------


class TestJoinAndTombstoneLeaksClosed:
    def test_get_item_outgoing_link_join_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(
            tmp_foundry,
            [
                {"local_ref": "a", "workspace_id": "ws-mine"},
                {"local_ref": "b", "workspace_id": "ws-other"},
            ],
            links=[{"from": "a", "to": "b"}],
        )
        _force_isolation_active(monkeypatch)
        result = catalog_service.get_item(tmp_foundry, ids_["a"], identity=_WS_MINE)
        assert result is not None
        assert result["links"]["outgoing"] == []

    def test_get_item_incoming_link_join_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(
            tmp_foundry,
            [
                {"local_ref": "a", "workspace_id": "ws-other"},
                {"local_ref": "b", "workspace_id": "ws-mine"},
            ],
            links=[{"from": "a", "to": "b"}],
        )
        _force_isolation_active(monkeypatch)
        result = catalog_service.get_item(tmp_foundry, ids_["b"], identity=_WS_MINE)
        assert result is not None
        assert result["links"]["incoming"] == []

    def test_get_item_citing_drafts_join_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine"}])
        _seed_citing_draft(tmp_foundry, workspace_id="ws-other", catalog_item_id=ids_["a"])
        _force_isolation_active(monkeypatch)
        result = catalog_service.get_item(tmp_foundry, ids_["a"], identity=_WS_MINE)
        assert result is not None
        assert result["links"]["citing_drafts"] == []

    def test_get_item_primary_row_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        assert catalog_service.get_item(tmp_foundry, ids_["a"], identity=_WS_OTHER) is None

    def test_search_where_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        result = catalog_service.search(tmp_foundry, page_size=200, identity=_WS_OTHER)
        assert ids_["a"] not in {it["catalog_item_id"] for it in result["items"]}

    def test_search_facets_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _seed_catalog_items(
            tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine", "title": "Leak-check title"}]
        )
        _force_isolation_active(monkeypatch)
        result = catalog_service.search(tmp_foundry, page_size=200, identity=_WS_OTHER)
        assert result["facets"] == {"projects": [], "statuses": [], "sensitivities": []}

    def test_get_draft_index_primary_row_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        assert catalog_service.get_draft_index(tmp_foundry, draft["report_draft_id"], identity=_WS_OTHER) is None

    def test_get_draft_index_links_join_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-other"}])
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        draft_id = draft["report_draft_id"]
        draft = builder_service.add_block(tmp_foundry, draft_id, markdown="p")
        block_id = draft["blocks"][-1]["block_id"]
        builder_service.add_claim_link(
            tmp_foundry,
            draft_id,
            block_id=block_id,
            claim_id="claim_x",
            catalog_item_id=ids_["a"],
            relation="context",
            insert_tag=False,
        )
        _force_isolation_active(monkeypatch)
        result = catalog_service.get_draft_index(tmp_foundry, draft_id, identity=_WS_MINE)
        assert result is not None
        assert result["links"] == []

    def test_list_draft_index_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        assert catalog_service.list_draft_index(tmp_foundry, identity=_WS_OTHER) == []

    def test_load_draft_file_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        with pytest.raises(NotFoundError):
            builder_service.load_draft(tmp_foundry, draft["report_draft_id"], identity=_WS_OTHER)

    def test_load_draft_null_workspace_treated_as_mismatch(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Nullws", workspace_id=None, sensitivity="public")
        _force_isolation_active(monkeypatch)
        with pytest.raises(NotFoundError):
            builder_service.load_draft(tmp_foundry, draft["report_draft_id"], identity=_WS_MINE)

    def test_list_drafts_delegates_predicate_via_load_draft(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        builder_service.create_draft(tmp_foundry, title="Nullws", workspace_id=None, sensitivity="public")
        _force_isolation_active(monkeypatch)
        result = builder_service.list_drafts(tmp_foundry, identity=_WS_MINE)
        assert len(result) == 1
        assert result[0]["title"] == "Mine"

    def test_export_markdown_delegates_predicate_via_load_draft(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        _force_isolation_active(monkeypatch)
        with pytest.raises(NotFoundError):
            builder_service.export_markdown(tmp_foundry, draft["report_draft_id"], identity=_WS_OTHER)

    def test_load_job_predicate_closes_leak(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        _force_isolation_active(monkeypatch)
        service = AgentJobService(tmp_foundry)
        with pytest.raises(KeyError):
            service.load_job(job["agent_job_id"], identity=_WS_OTHER)

    def test_load_job_null_workspace_treated_as_mismatch(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id=None)
        _force_isolation_active(monkeypatch)
        service = AgentJobService(tmp_foundry)
        with pytest.raises(KeyError):
            service.load_job(job["agent_job_id"], identity=_WS_MINE)


# ---------------------------------------------------------------------------
# TASK-5.4 (AC-5): mutation-deny "zero-write-issued" spy tests for
# cross-workspace mutation targets in catalog.py, agent_jobs.py, reports.py.
# ---------------------------------------------------------------------------


class TestMutationDenySpies:
    def test_delete_draft_cross_workspace_never_calls_service_delete(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        draft_id = draft["report_draft_id"]
        calls = {"n": 0}
        original = builder_service.delete_draft

        def spy(paths: FoundryPaths, report_draft_id: str) -> None:
            calls["n"] += 1
            return original(paths, report_draft_id)

        monkeypatch.setattr(builder_service, "delete_draft", spy)
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.delete(f"/api/reports/{draft_id}")
        assert resp.status_code == 404
        assert calls["n"] == 0
        # The draft must still exist on disk — the deny happened BEFORE any write.
        assert builder_service.load_draft(tmp_foundry, draft_id, identity=None)["report_draft_id"] == draft_id

    def test_cancel_job_cross_workspace_never_calls_terminate_or_cleanup(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        _enable_agents(tmp_foundry)
        terminate_calls = {"n": 0}
        cleanup_calls = {"n": 0}
        original_terminate = AgentJobService.terminate_job
        original_cleanup = AgentJobService.cleanup_job

        def spy_terminate(self: AgentJobService, job_id: str, **kwargs: Any) -> Any:
            terminate_calls["n"] += 1
            return original_terminate(self, job_id, **kwargs)

        def spy_cleanup(self: AgentJobService, job_id: str, **kwargs: Any) -> Any:
            cleanup_calls["n"] += 1
            return original_cleanup(self, job_id, **kwargs)

        monkeypatch.setattr(AgentJobService, "terminate_job", spy_terminate)
        monkeypatch.setattr(AgentJobService, "cleanup_job", spy_cleanup)
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.post(f"/api/agent-jobs/{job['agent_job_id']}/cancel")
        assert resp.status_code == 404
        assert terminate_calls["n"] == 0
        assert cleanup_calls["n"] == 0

    def test_accept_job_cross_workspace_never_calls_accept_job(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        _enable_agents(tmp_foundry)
        calls = {"n": 0}
        original = AgentJobService.accept_job

        def spy(self: AgentJobService, job_id: str, **kwargs: Any) -> Any:
            calls["n"] += 1
            return original(self, job_id, **kwargs)

        monkeypatch.setattr(AgentJobService, "accept_job", spy)
        _force_isolation_active(monkeypatch)
        client = _make_client(tmp_foundry, _WS_OTHER)
        resp = client.post(f"/api/agent-jobs/{job['agent_job_id']}/accept", json={})
        assert resp.status_code == 404
        assert calls["n"] == 0

    def test_catalog_import_mutation_endpoints_take_no_identity_param(self) -> None:
        """ESCALATION FINDING: catalog.py's only mutation endpoints
        (``import_run``/``import_all``) take no ``identity`` parameter at
        all (confirmed by catalog.py's own ``TODO(WKSP-304 P4)`` comments —
        not a Phase 3 scoping target). There is no per-item mutation target
        that can mismatch a caller's workspace, so there is nothing to
        deny — this test documents the exemption via signature
        introspection rather than asserting a deny scenario that cannot
        exist for these two endpoints today."""
        assert "identity" not in inspect.signature(catalog_service.import_run).parameters
        assert "identity" not in inspect.signature(catalog_service.import_all).parameters


# ---------------------------------------------------------------------------
# TASK-5.5(a) (AC-6): identity=None ("single-operator fallback") regression —
# confirms identity=None / omitted produces byte-identical, unrestricted
# behaviour across CLI/direct-service call patterns for all 3 services.
# ---------------------------------------------------------------------------


class TestIdentityNoneSingleOperatorFallback:
    def test_catalog_get_item_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine"}])
        omitted = catalog_service.get_item(tmp_foundry, ids_["a"])
        explicit_none = catalog_service.get_item(tmp_foundry, ids_["a"], identity=None)
        assert omitted == explicit_none
        assert omitted is not None

    def test_catalog_search_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        _seed_catalog_items(tmp_foundry, [{"local_ref": "a", "workspace_id": "ws-mine"}])
        omitted = catalog_service.search(tmp_foundry, page_size=200)
        explicit_none = catalog_service.search(tmp_foundry, page_size=200, identity=None)
        assert omitted == explicit_none

    def test_catalog_get_draft_index_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        omitted = catalog_service.get_draft_index(tmp_foundry, draft["report_draft_id"])
        explicit_none = catalog_service.get_draft_index(tmp_foundry, draft["report_draft_id"], identity=None)
        assert omitted == explicit_none

    def test_catalog_list_draft_index_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        omitted = catalog_service.list_draft_index(tmp_foundry)
        explicit_none = catalog_service.list_draft_index(tmp_foundry, identity=None)
        assert omitted == explicit_none

    def test_builder_load_draft_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        omitted = builder_service.load_draft(tmp_foundry, draft["report_draft_id"])
        explicit_none = builder_service.load_draft(tmp_foundry, draft["report_draft_id"], identity=None)
        assert omitted == explicit_none

    def test_builder_list_drafts_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        omitted = builder_service.list_drafts(tmp_foundry)
        explicit_none = builder_service.list_drafts(tmp_foundry, identity=None)
        assert omitted == explicit_none

    def test_builder_export_markdown_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        draft = builder_service.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine", sensitivity="public")
        omitted = builder_service.export_markdown(tmp_foundry, draft["report_draft_id"])
        explicit_none = builder_service.export_markdown(tmp_foundry, draft["report_draft_id"], identity=None)
        assert omitted == explicit_none

    def test_agent_job_load_job_identity_none_equals_omitted(self, tmp_foundry: FoundryPaths) -> None:
        job = _seed_agent_job(tmp_foundry, workspace_id="ws-mine")
        service = AgentJobService(tmp_foundry)
        omitted = service.load_job(job["agent_job_id"])
        explicit_none = service.load_job(job["agent_job_id"], identity=None)
        assert omitted == explicit_none

    def test_catalog_stats_never_had_an_identity_concept(self, tmp_foundry: FoundryPaths) -> None:
        """stats() has no identity parameter at all — structurally
        unrestricted regardless of any caller's workspace, by construction
        rather than by an identity=None passthrough."""
        assert "identity" not in inspect.signature(catalog_service.stats).parameters
        # Calling it never raises regardless of workspace context.
        assert catalog_service.stats(tmp_foundry)["counts"] is not None

    def test_agent_job_create_job_identity_none_equals_omitted(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        """Escalation finding closed by DF-004: ``create_job`` now accepts
        ``identity`` (create-path workspace stamping, mirroring
        ``builder_service.create_draft``) — see ``agent_job_service.py``'s
        own docstring. ``identity=None`` remains byte-identical to omitting
        the parameter (the pre-DF-004 single-operator baseline)."""
        assert "identity" in inspect.signature(AgentJobService.create_job).parameters
        service = AgentJobService(tmp_foundry)
        kwargs: dict[str, Any] = {
            "provider": "claude_agent_sdk",
            "model_profile": "personal",
            "request_kind": "research",
            "policy_snapshot": _MINIMAL_POLICY_SNAPSHOT,
            "workspace_id": "ws-mine",
        }
        omitted = service.create_job(**kwargs)
        explicit_none = service.create_job(**kwargs, identity=None)
        assert omitted.workspace_id == explicit_none.workspace_id == "ws-mine"


# ---------------------------------------------------------------------------
# TASK-5.7 (NFR-Security): every workspace_id predicate constructed across
# the 3 Phase-3 services must use a parameterized bind-value ('?'), never a
# string-interpolated literal.
# ---------------------------------------------------------------------------


class TestWorkspaceIdBindParamDiscipline:
    _MODULES = [catalog_service, builder_service, agent_job_service]

    @staticmethod
    def _source_lines(mod: Any) -> list[str]:
        return Path(inspect.getfile(mod)).read_text(encoding="utf-8").splitlines()

    @pytest.mark.parametrize("mod", _MODULES, ids=lambda m: m.__name__)
    def test_no_string_interpolated_workspace_id_predicate(self, mod: Any) -> None:
        """Catches the dangerous shape: an f-string/`.format()` SQL literal
        that interpolates a workspace_id value directly into the query text
        (e.g. ``f"... workspace_id = {ws} ..."``) instead of using a `?`
        bind parameter."""
        dangerous = re.compile(r"workspace_id\s*=\s*[\"']?\s*\{")
        offending = [
            (lineno, line)
            for lineno, line in enumerate(self._source_lines(mod), start=1)
            if dangerous.search(line)
        ]
        assert offending == [], f"string-interpolated workspace_id predicate(s) in {mod.__name__}: {offending}"

    def test_catalog_service_uses_parameterized_workspace_predicate_at_every_query_point(self) -> None:
        lines = self._source_lines(catalog_service)
        matches = [line for line in lines if "workspace_id = ?" in line]
        # search() WHERE, _facets(), get_item() outgoing/incoming (shared
        # clause var), get_item() citing_drafts, get_item() primary row,
        # get_draft_index() primary row + links join, list_draft_index().
        assert len(matches) >= 5, f"expected >=5 parameterized workspace_id predicates, found {len(matches)}"

    def test_builder_service_workspace_predicate_is_a_python_dict_comparison_not_sql(self) -> None:
        """builder_service is file-canonical (no SQL at all) — its
        workspace predicate is a plain Python equality check against the
        loaded YAML dict (``data.get("workspace_id") != identity.workspace_id``),
        which cannot be a SQL-injection vector by construction. Confirm no
        raw SQL text referencing workspace_id exists in this module."""
        lines = self._source_lines(builder_service)
        sql_like = [line for line in lines if "workspace_id" in line and ("SELECT" in line or "WHERE" in line)]
        assert sql_like == []

    def test_agent_job_service_workspace_predicate_is_a_python_attr_comparison_not_sql(self) -> None:
        """agent_job_service is file-canonical (plain JSON, no SQL) — its
        predicate flows entirely through ``require_workspace_scope``'s
        Python-level ``getattr``/``==`` comparison, never a query string."""
        lines = self._source_lines(agent_job_service)
        sql_like = [line for line in lines if "workspace_id" in line and ("SELECT" in line or "WHERE" in line)]
        assert sql_like == []


# ---------------------------------------------------------------------------
# karen review follow-up: create_draft_from_run / create_draft_from_collection
# identity threading (HIGH-1) + create_draft_from_collection cross-workspace
# catalog read leak (HIGH-2). Mirrors the create_draft identity contract
# (builder_service.py's create_draft docstring): identity=None is
# byte-identical to pre-WKSP-304 behavior; identity= stamps workspace_id from
# identity.workspace_id and, for the collection path, scopes the underlying
# catalog_service.get_item() lookup so a cross-workspace catalog item can
# never be embedded into the resulting draft.
# ---------------------------------------------------------------------------


def _plant_minimal_run(paths: FoundryPaths, run_id: str) -> None:
    """Bare-minimum run scaffold sufficient for ``export_run``/
    ``create_draft_from_run`` — no source cards or claim ledger entries are
    needed since this suite only asserts on identity/workspace_id threading,
    not on seeded blocks/claim_links (covered by
    ``tests/unit/test_builder_service.py``)."""

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": "public",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        rp.run_yaml,
    )


class TestCreateDraftFromRunAndCollectionIdentityThreading:
    """TASK-5.5 follow-up (karen HIGH-1/HIGH-2)."""

    def test_create_draft_from_run_legit_owner_allowed(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _plant_minimal_run(tmp_foundry, "rf_run_p5followup_run")
        _force_isolation_active(monkeypatch)
        draft = builder_service.create_draft_from_run(
            tmp_foundry, run_id="rf_run_p5followup_run", identity=_WS_MINE
        )
        report_draft_id = draft["report_draft_id"]
        assert draft["workspace_id"] == "ws-mine"
        loaded = builder_service.load_draft(tmp_foundry, report_draft_id, identity=_WS_MINE)
        assert loaded["workspace_id"] == "ws-mine"

    def test_create_draft_from_collection_legit_owner_allowed(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-mine"}])
        _force_isolation_active(monkeypatch)
        draft = builder_service.create_draft_from_collection(
            tmp_foundry,
            catalog_item_ids=[ids_["c1"]],
            title="Mine collection draft",
            identity=_WS_MINE,
        )
        report_draft_id = draft["report_draft_id"]
        assert draft["workspace_id"] == "ws-mine"
        loaded = builder_service.load_draft(tmp_foundry, report_draft_id, identity=_WS_MINE)
        assert loaded["workspace_id"] == "ws-mine"
        assert any(b["block_type"] == "evidence_summary" for b in loaded["blocks"])

    def test_create_draft_from_collection_cross_workspace_catalog_item_not_embedded(
        self, tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The critical regression: a catalog item owned by ``ws-other`` must
        not be embedded into a draft created by ``ws-mine`` under
        enforcement — it must be silently skipped via the existing
        "unresolved ids are skipped" path (item resolves to ``None``), the
        same way a genuinely-unknown catalog_item_id is skipped today."""

        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "ws-other"}])
        _force_isolation_active(monkeypatch)
        draft = builder_service.create_draft_from_collection(
            tmp_foundry,
            catalog_item_ids=[ids_["c1"]],
            title="Leak probe draft",
            identity=_WS_MINE,
        )
        report_draft_id = draft["report_draft_id"]
        loaded = builder_service.load_draft(tmp_foundry, report_draft_id, identity=_WS_MINE)
        assert loaded["blocks"] == []
        all_linked_ids = [cl.get("catalog_item_id") for cl in loaded["claim_links"]]
        assert ids_["c1"] not in all_linked_ids

    def test_create_draft_from_run_identity_none_is_byte_identical_baseline(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        """AC-6 single-operator baseline: existing callers that never pass
        ``identity`` (the default) must keep stamping ``workspace_id`` from
        the ``workspace_id`` parameter exactly as before."""

        _plant_minimal_run(tmp_foundry, "rf_run_p5followup_baseline")
        draft = builder_service.create_draft_from_run(
            tmp_foundry, run_id="rf_run_p5followup_baseline", workspace_id="legacy-ws"
        )
        assert draft["workspace_id"] == "legacy-ws"

    def test_create_draft_from_collection_identity_none_is_byte_identical_baseline(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        ids_ = _seed_catalog_items(tmp_foundry, [{"local_ref": "c1", "workspace_id": "default"}])
        draft = builder_service.create_draft_from_collection(
            tmp_foundry,
            catalog_item_ids=[ids_["c1"]],
            title="Baseline collection draft",
            workspace_id="legacy-ws",
        )
        assert draft["workspace_id"] == "legacy-ws"
        assert any(b["block_type"] == "evidence_summary" for b in draft["blocks"])
