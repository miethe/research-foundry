"""HTTP regression coverage for the P4 governed evidence-packet API."""

from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


class _IdentityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self.identity = identity

    async def dispatch(self, request, call_next) -> Response:
        if self.identity is not None:
            request.state.identity = self.identity
        return await call_next(request)


def _setup_assertion(tmp_foundry) -> str:
    run_id = "rf_run_p4_api"
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "p4-api.txt",
        run_id=run_id,
        title="P4 API Evidence",
        sensitivity="personal",
        content="The packet must include its exact source passage.",
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    result = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry).materialize_run(run_id)
    assert result.status == "materialized"
    return result.assertion_ids[0]


def _client(tmp_foundry, identity: AuthIdentity | None) -> TestClient:
    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.add_middleware(_IdentityMiddleware, identity=identity)
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app)


def test_search_requires_workspace_identity_without_leaking_counts(tmp_foundry) -> None:
    _setup_assertion(tmp_foundry)
    response = _client(tmp_foundry, None).get("/api/assertions/search", params={"q": "packet"})

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "next_cursor": None,
        "facets": {"lifecycle_states": [], "access_scopes": []},
        "denial_reason": "workspace_context_missing",
    }


def test_authorized_packet_and_lineage_include_context(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    client = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",)))

    search = client.get("/api/assertions/search", params={"q": "exact"})
    packet = client.get(f"/api/assertions/{assertion_id}")
    lineage = client.get(f"/api/assertions/{assertion_id}/lineage")

    assert search.status_code == 200
    assert search.json()["items"] == [{
        "assertion_id": assertion_id,
        "assertion_version": 1,
        "lifecycle_state": "eligible",
        "access_scope": "personal",
        "rights_decision": {"allowed": True, "reason_code": "eligible"},
    }]
    assert packet.status_code == 200
    assert packet.json()["passage"]["normalized_text"] == "The packet must include its exact source passage."
    assert packet.json()["rights_decision"] == {"allowed": True, "reason_code": "eligible"}
    assert lineage.status_code == 200
    assert lineage.json()["run_uses"] == ["rf_run_p4_api"]


def test_other_workspace_cannot_probe_packet_membership(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    response = _client(tmp_foundry, AuthIdentity("mallory", "workspace-b", ("viewer",))).get(
        f"/api/assertions/{assertion_id}"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "assertion not found"}
