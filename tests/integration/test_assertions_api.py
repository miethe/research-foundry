"""HTTP regression coverage for the P4 governed evidence-packet API."""

from __future__ import annotations

from hashlib import sha256

from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.services import claim_mapping, export_service, extraction
from research_foundry.services.assertion_catalog import AssertionCatalog
from research_foundry.services.assertion_inference import AssertionInferenceMaterializer
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.assertion_report_use import (
    ReportAssertionUseService,
    attest_verification_pass,
    build_report_ref,
)
from research_foundry.services.canonical_claim_materialization import CanonicalClaimMaterializer
from research_foundry.services.provenance_envelope import (
    ProvenanceEnvelopeStore,
    degraded_selection_receipt,
    empty_selection_receipt,
    search_evidence_entry,
    selected_selection_receipt,
)
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

    # RPC-5.2: additive activity/lineage fields are present over HTTP, and a
    # legacy assertion with no inference/canonical-claim/report-use/origin
    # activity exposes empty optional values -- never an omitted key.
    assert packet.json()["report_uses"] == []
    assert packet.json()["inference_lineage"] == []
    assert packet.json()["canonical_claim_lineage"] == []
    assert packet.json()["run_facets"] == {"rf_run_p4_api": None}
    assert packet.json()["search_activity_ids"] == []
    assert lineage.json()["inference_lineage"] == []
    assert lineage.json()["canonical_claim_lineage"] == []
    assert lineage.json()["run_facets"] == {"rf_run_p4_api": None}
    assert lineage.json()["search_activity_ids"] == []


def test_other_workspace_cannot_probe_packet_membership(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    response = _client(tmp_foundry, AuthIdentity("mallory", "workspace-b", ("viewer",))).get(
        f"/api/assertions/{assertion_id}"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "assertion not found"}


# ---------------------------------------------------------------------------
# RPC-5.3: search-only discovery seam -- a canonical search-only activity
# (created via ``provenance_envelope.create_activity``'s own store) has no
# OTHER governed HTTP surface once its receipt selects zero/degraded evidence
# versions (an evidence packet's `search_activity_ids` only names an activity
# once it has selected at least one assertion version). ``GET
# /assertions/activities`` and ``GET /assertions/activities/{envelope_id}``
# are the minimal additive surface AC RPC-5 requires: list/fetch remain
# workspace-isolated and complete with no planned run required.
# ---------------------------------------------------------------------------


def _scope() -> dict:
    return {"provider": "pubmed", "site": None, "corpus": None}


def _make_search_only_activity(
    store: ProvenanceEnvelopeStore, *, request_id: str, selection_receipt: dict
) -> tuple[dict, dict]:
    v1 = store.create_envelope_v1(activity_kind="search_only", request_id=request_id)
    receipt, v2 = store.create_receipt_and_promote(
        v1,
        query=f"query for {request_id}",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="7" * 64,
        selected_evidence_versions=[],
        selection_receipt=selection_receipt,
    )
    return v2, receipt


def test_search_only_activity_listable_and_fetchable_over_http(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="workspace-a", paths=tmp_foundry)
    envelope, receipt = _make_search_only_activity(
        store,
        request_id="req-empty-1",
        selection_receipt=empty_selection_receipt(source="pubmed", decided_at="2026-07-28T13:00:05Z"),
    )

    client = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("researcher",)))
    listing = client.get("/api/assertions/activities", params={"activity_kind": "search_only"})

    assert listing.status_code == 200
    body = listing.json()
    assert body["denial_reason"] is None
    ids = {item["envelope_id"] for item in body["items"]}
    assert envelope["envelope_id"] in ids
    row = next(i for i in body["items"] if i["envelope_id"] == envelope["envelope_id"])
    assert row["planned_run_ref"] is None
    assert row["outcome"] == "empty"

    detail = client.get(f"/api/assertions/activities/{envelope['envelope_id']}")
    assert detail.status_code == 200
    payload = detail.json()
    # Exact receipt round trip -- not merely the summary row's derived fields.
    assert payload["envelope"] == envelope
    assert payload["receipt"] == receipt


def test_search_only_activity_listing_is_complete_including_zero_match_and_degraded(
    tmp_foundry,
) -> None:
    """Completeness: every one of workspace-a's search-only activities is
    listed, whether its receipt outcome is `empty` (zero candidates) or
    `degraded` (evaluated under a documented degraded condition) -- neither
    has any linked assertion, so neither would ever surface through a
    packet's `search_activity_ids`."""

    store = ProvenanceEnvelopeStore(workspace_id="workspace-a", paths=tmp_foundry)
    empty_envelope, _empty_receipt = _make_search_only_activity(
        store,
        request_id="req-empty-2",
        selection_receipt=empty_selection_receipt(source="pubmed", decided_at="2026-07-28T13:01:05Z"),
    )
    degraded_envelope, _degraded_receipt = _make_search_only_activity(
        store,
        request_id="req-degraded",
        selection_receipt=degraded_selection_receipt(
            source="pubmed", decided_at="2026-07-28T13:02:05Z", degraded_reason="rate_limited"
        ),
    )
    # A planned_run activity in the same workspace must not appear in a
    # `search_only`-scoped listing.
    v1 = store.create_envelope_v1(activity_kind="planned_run", planned_run_ref={"run_id": "run-unrelated"})
    store.create_receipt_and_promote(
        v1,
        query="unrelated planned-run query",
        purpose="evidence gathering",
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=[
            {"assertion_id": f"ast_{'a' * 64}", "assertion_version": 1, "question_id": None, "decided_at": None}
        ],
        selection_receipt=selected_selection_receipt(
            source="pubmed", decided_at="2026-07-28T13:03:05Z"
        ),
    )

    client = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("researcher",)))
    listing = client.get("/api/assertions/activities", params={"activity_kind": "search_only"})

    ids = {item["envelope_id"] for item in listing.json()["items"]}
    assert ids == {empty_envelope["envelope_id"], degraded_envelope["envelope_id"]}


def test_search_only_activity_denies_without_workspace_identity(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="workspace-a", paths=tmp_foundry)
    envelope, _receipt = _make_search_only_activity(
        store,
        request_id="req-anon",
        selection_receipt=empty_selection_receipt(source="pubmed", decided_at="2026-07-28T13:04:05Z"),
    )
    client = _client(tmp_foundry, None)

    listing = client.get("/api/assertions/activities")
    assert listing.status_code == 200
    assert listing.json() == {"items": [], "next_cursor": None, "denial_reason": "workspace_context_missing"}

    detail = client.get(f"/api/assertions/activities/{envelope['envelope_id']}")
    assert detail.status_code == 404
    assert detail.json() == {"detail": {"reason_code": "workspace_context_missing"}}


def test_search_only_activity_cross_workspace_isolation_no_existence_leak(tmp_foundry) -> None:
    """Workspace B's client sees nothing of workspace A's search-only
    activity -- not in the listing, and a direct fetch by its exact
    envelope_id resolves to the SAME denial shape an unknown envelope_id
    does (no existence signal leaks either way, mirroring
    ``test_other_workspace_cannot_probe_packet_membership``)."""

    store_a = ProvenanceEnvelopeStore(workspace_id="workspace-a", paths=tmp_foundry)
    envelope, _receipt = _make_search_only_activity(
        store_a,
        request_id="req-cross",
        selection_receipt=empty_selection_receipt(source="pubmed", decided_at="2026-07-28T13:05:05Z"),
    )

    client_b = _client(tmp_foundry, AuthIdentity("mallory", "workspace-b", ("viewer",)))

    listing = client_b.get("/api/assertions/activities")
    assert listing.status_code == 200
    assert listing.json() == {"items": [], "next_cursor": None, "denial_reason": None}

    cross_workspace_fetch = client_b.get(f"/api/assertions/activities/{envelope['envelope_id']}")
    unknown_fetch = client_b.get(f"/api/assertions/activities/rre_{'0' * 64}")

    assert cross_workspace_fetch.status_code == 404
    assert unknown_fetch.status_code == 404
    assert cross_workspace_fetch.json() == {"detail": {"reason_code": "not_authorized_or_not_found"}}
    assert cross_workspace_fetch.json() == unknown_fetch.json()

    # The owning workspace can still fetch it in full.
    client_a = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("researcher",)))
    owned_fetch = client_a.get(f"/api/assertions/activities/{envelope['envelope_id']}")
    assert owned_fetch.status_code == 200
    assert owned_fetch.json()["envelope"]["envelope_id"] == envelope["envelope_id"]


# ---------------------------------------------------------------------------
# RPC-5.4: end-to-end lineage seam. One exact fixture builds the FULL chain
# with the real services -- origin -> planned_run activity (+ a sibling
# search_only activity over the same evidence version) -> materialized
# source assertion -> inference -> canonical claim -> a published (attested)
# report_assertion_use -- and asserts the governed catalog read, the HTTP
# API, and the run export block all show the IDENTICAL version-pinned chain.
# ---------------------------------------------------------------------------


def _origin_method() -> dict:
    return {"kind": "acquisition", "mechanism": "web_search"}


def _origin_producer() -> dict:
    return {"producer_type": "agent", "producer_id": "agent-1", "tool": "rf-search", "tool_version": "1.0"}


def _setup_end_to_end_lineage_chain(tmp_foundry) -> dict[str, object]:
    run_id = "rf_run_rpc54_e2e"
    workspace_id = "workspace-rpc54"

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "canonical_claims_enabled": True,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "rpc54-evidence.txt",
        run_id=run_id,
        title="RPC-5.4 Evidence",
        sensitivity="personal",
        content="Pediatric CBC reference intervals differ from adult intervals across all cell lines.",
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    result = AssertionMaterializer(workspace_id=workspace_id, paths=tmp_foundry).materialize_run(run_id)
    assert result.status == "materialized"
    assertion_id = result.assertion_ids[0]
    dump_yaml(
        {
            "schema_version": 0.1,
            "type": "run",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "workspace_id": workspace_id,
        },
        tmp_foundry.run_paths(run_id).run_yaml,
    )

    # origin -> planned_run activity (RPC-5.4's "origin -> activity" node).
    store = ProvenanceEnvelopeStore(workspace_id=workspace_id, paths=tmp_foundry)
    origin = store.write_origin(
        method=_origin_method(),
        producer=_origin_producer(),
        source_kind="web_page",
        locator="https://example.com/pediatric-cbc",
        content_digest="9" * 64,
        created_at="2026-07-28T11:00:00Z",
    )
    planned_v1 = store.create_envelope_v1(
        activity_kind="planned_run",
        planned_run_ref={"run_id": run_id},
        origin_ref={"origin_id": origin["origin_id"], "origin_version": origin["origin_version"]},
        request_id="req-rpc54-planned",
    )
    _planned_receipt, _planned_v2 = store.create_receipt_and_promote(
        planned_v1,
        query="pediatric CBC reference intervals",
        purpose="evidence gathering",
        scope=_scope(),
        candidate_set_digest="4" * 64,
        selected_evidence_versions=[search_evidence_entry(assertion_id=assertion_id, assertion_version=1)],
        selection_receipt=selected_selection_receipt(source="pubmed", decided_at="2026-07-28T11:05:00Z"),
    )

    # A sibling search_only activity over the SAME evidence version --
    # proves `search_activity_ids` composes with the planned_run node above
    # rather than being mutually exclusive with it.
    search_v1 = store.create_envelope_v1(activity_kind="search_only", request_id="req-rpc54-search")
    search_receipt, _search_v2 = store.create_receipt_and_promote(
        search_v1,
        query="pediatric CBC search",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="5" * 64,
        selected_evidence_versions=[search_evidence_entry(assertion_id=assertion_id, assertion_version=1)],
        selection_receipt=selected_selection_receipt(source="pubmed", decided_at="2026-07-28T11:06:00Z"),
    )
    search_activity_id = search_receipt["activity_id"]

    # inference, citing the source assertion.
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    inf_claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": inf_claim_id,
            "text": "Pediatric CBC reference intervals differ from adult intervals.",
            "materiality": "material",
            "claim_type": "comparative",
            "status": "inference",
            "confidence": "medium",
            "sources": [],
            "inference_basis": {
                "from_claims": ["clm_001"],
                "reasoning_summary": "Synthesized from one source assertion.",
            },
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    inf_result = AssertionInferenceMaterializer(
        workspace_id=workspace_id, paths=tmp_foundry
    ).materialize_inference(run_id, inf_claim_id, producer="agent-research-1")
    assert inf_result.status == "materialized"

    # canonical claim, citing the source assertion directly AND the inference.
    ledger = load_yaml(ledger_path)
    ccl_claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": ccl_claim_id,
            "text": "Pediatric CBC reference intervals differ from adult intervals.",
            "materiality": "material",
            "claim_type": "comparative",
            "status": "supported",
            "confidence": "medium",
            "sources": [],
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    ccl_result = CanonicalClaimMaterializer(workspace_id=workspace_id, paths=tmp_foundry).publish_canonical_claim(
        run_id,
        ccl_claim_id,
        statement="Pediatric CBC reference intervals differ from adult intervals.",
        source_assertion_refs=[{"assertion_id": assertion_id, "assertion_version": 1, "relation": "supports"}],
        inference_refs=[
            {
                "inference_id": inf_result.inference_id,
                "inference_version": inf_result.inference_version,
                "relation": "supports",
            }
        ],
        explicit_request=True,
    )
    assert ccl_result.status == "materialized"

    # a verified (directly attested/published) report_assertion_use.
    report_service = ReportAssertionUseService(workspace_id=workspace_id, paths=tmp_foundry)
    # K-FINAL-1: attestation must be established through the real public
    # entry point (a genuine report file + attest_verification_pass), never
    # the module/class-private writer, so this fixture exercises the same
    # trust boundary a real caller would.
    report_path = tmp_foundry.root / "reports" / "report_rpc54_e2e.md"
    dump_md({"schema_version": "1.0"}, "genuine report body for RPC-5.4 e2e", report_path)
    _, report_body = load_md(report_path)
    report_digest = sha256(report_body.encode("utf-8")).hexdigest()
    report_ref = build_report_ref(report_id="report_rpc54_e2e", report_content_digest=report_digest)
    attest_verification_pass(
        workspace_id=workspace_id,
        report_id="report_rpc54_e2e",
        report_content_digest=report_digest,
        verified_at="2026-07-28T12:00:00Z",
        report_path=report_path,
        paths=tmp_foundry,
    )
    outcome = report_service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"
    status, _record = report_service.publish(outcome.record)
    assert status == "published"

    return {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "assertion_id": assertion_id,
        "origin_id": origin["origin_id"],
        "inference_id": inf_result.inference_id,
        "inference_version": inf_result.inference_version,
        "canonical_claim_id": ccl_result.canonical_claim_id,
        "canonical_claim_version": ccl_result.canonical_claim_version,
        "use_id": outcome.use_id,
        "search_activity_id": search_activity_id,
        "expected_run_facet": {
            "origin_id": origin["origin_id"],
            "origin_source_kind": "web_page",
            "origin_locator": "https://example.com/pediatric-cbc",
            "origin_producer_tool": "rf-search",
            "origin_method_kind": "acquisition",
        },
    }


def test_end_to_end_lineage_chain_matches_across_catalog_api_and_export(tmp_foundry) -> None:
    fixture = _setup_end_to_end_lineage_chain(tmp_foundry)
    identity = AuthIdentity("alice", fixture["workspace_id"], ("researcher",))

    expected_inference_lineage = [
        {
            "inference_id": fixture["inference_id"],
            "inference_version": fixture["inference_version"],
            "status": "active",
            "report_uses": [],
        }
    ]
    expected_canonical_claim_lineage = [
        {
            "canonical_claim_id": fixture["canonical_claim_id"],
            "canonical_claim_version": fixture["canonical_claim_version"],
            "state": "active",
            "report_uses": [],
        }
    ]
    expected_run_facets = {fixture["run_id"]: fixture["expected_run_facet"]}
    expected_report_uses = [fixture["use_id"]]
    expected_search_activity_ids = [fixture["search_activity_id"]]

    # (1) Governed catalog read (rebuild-on-miss, direct service call).
    packet = AssertionCatalog(tmp_foundry).packet(fixture["assertion_id"], identity=identity)
    assert packet is not None
    assert packet["inference_lineage"] == expected_inference_lineage
    assert packet["canonical_claim_lineage"] == expected_canonical_claim_lineage
    assert packet["run_facets"] == expected_run_facets
    assert packet["report_uses"] == expected_report_uses
    assert packet["search_activity_ids"] == expected_search_activity_ids

    lineage = AssertionCatalog(tmp_foundry).lineage(fixture["assertion_id"], identity=identity)
    assert lineage is not None
    assert lineage["inference_lineage"] == expected_inference_lineage
    assert lineage["canonical_claim_lineage"] == expected_canonical_claim_lineage
    assert lineage["run_facets"] == expected_run_facets
    assert lineage["report_uses"] == expected_report_uses
    assert lineage["search_activity_ids"] == expected_search_activity_ids

    # (2) The SAME chain over HTTP -- both the packet and the lineage routes.
    client = _client(tmp_foundry, identity)
    packet_response = client.get(f"/api/assertions/{fixture['assertion_id']}")
    lineage_response = client.get(f"/api/assertions/{fixture['assertion_id']}/lineage")
    assert packet_response.status_code == 200
    assert lineage_response.status_code == 200
    packet_body = packet_response.json()
    lineage_body = lineage_response.json()
    for body in (packet_body, lineage_body):
        assert body["inference_lineage"] == expected_inference_lineage
        assert body["canonical_claim_lineage"] == expected_canonical_claim_lineage
        assert body["run_facets"] == expected_run_facets
        assert body["report_uses"] == expected_report_uses
        assert body["search_activity_ids"] == expected_search_activity_ids

    # The planned_run activity itself is also independently fetchable, and
    # its origin_ref resolves to the SAME origin_id the run facet derives
    # its values from.
    activities = client.get("/api/assertions/activities", params={"activity_kind": "planned_run"})
    assert activities.status_code == 200
    activity_row = next(
        item for item in activities.json()["items"] if item["planned_run_ref"] == {"run_id": fixture["run_id"]}
    )
    activity_detail = client.get(f"/api/assertions/activities/{activity_row['envelope_id']}")
    assert activity_detail.status_code == 200
    assert activity_detail.json()["envelope"]["origin_ref"]["origin_id"] == fixture["origin_id"]

    # (3) The SAME chain in the run export's per-claim `_provenance_lineage`
    # enrichment block.
    export_data = export_service.export_run(tmp_foundry, fixture["run_id"])
    claim = next(
        c
        for c in export_data["claims"]
        if c.get("persistent_references", {}).get("source_assertion_id") == fixture["assertion_id"]
    )
    lineage_block = claim["_provenance_lineage"]
    assert lineage_block["inference_lineage"] == expected_inference_lineage
    assert lineage_block["canonical_claim_lineage"] == expected_canonical_claim_lineage
    assert lineage_block["run_facets"] == expected_run_facets
    assert lineage_block["report_uses"] == expected_report_uses
    assert lineage_block["search_activity_ids"] == expected_search_activity_ids
