"""HTTP coverage for the governed assertion-impact read seam."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_impact import AssertionImpactReconciler, ImpactInterrupted
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


def _client(tmp_foundry, identity: AuthIdentity | None) -> TestClient:
    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.add_middleware(_IdentityMiddleware, identity=identity)
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app)


def _setup_assertion(tmp_foundry) -> str:
    run_id = "rf_run_p6_impact_api"
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "p6-impact-api.txt",
        run_id=run_id,
        title="P6 Impact API Evidence",
        sensitivity="personal",
        content="The impact receipt must be workspace-authorized.",
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    result = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry).materialize_run(run_id)
    assert result.status == "materialized"
    return result.assertion_ids[0]


def _persist_receipt(
    tmp_foundry,
    assertion_id: str,
    *,
    event_id: str = "evt_p6_impact",
    complete: bool = True,
    include_second_action: bool = False,
    writeback_count: int = 0,
    write_manifest: bool = True,
) -> AssertionImpactReconciler:
    reconciler = AssertionImpactReconciler(workspace_id="workspace-a", paths=tmp_foundry)
    assertion = reconciler._load_mapping(
        reconciler.root / "assertions" / f"{assertion_id}.yaml", "assertion_missing"
    )
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "assertion_lifecycle_event",
            "event_id": event_id,
            "sequence": 1,
            "idempotency_key": f"test:{event_id}",
            "occurred_at": "2026-07-14T16:00:00Z",
            "cause": "formal_retraction",
            "target": {
                "kind": "source_assertion",
                "id": assertion_id,
                "version": assertion["assertion_version"],
            },
            "transition": {"from": "eligible", "to": "invalidated"},
            "authoritative_action": "block_reuse",
            "dependent_actions": [{"object_kind": "run", "action": "block_reuse"}],
        },
        reconciler.event_path(event_id),
    )
    if write_manifest:
        reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
        expected_objects = [
            {"object_id": "run_p6_impact", "object_class": "run", "action": "mark_stale"}
        ]
        if include_second_action:
            expected_objects.append(
                {
                    "object_id": "regeneration_p6_impact",
                    "object_class": "assertion_regeneration",
                    "action": "regenerate",
                }
            )
        expected_objects.extend(
            {
                "object_id": f"writeback_p6_impact_{index}",
                "object_class": "mock_writeback_receipt",
                "action": "queue_default_denied_reconciliation",
            }
            for index in range(writeback_count)
        )
        reconciler.manifest_path(event_id).write_text(
            json.dumps({"expected_objects": expected_objects}),
            encoding="utf-8",
        )
    if complete:
        expected_status = "completed" if write_manifest else "blocked"
        assert reconciler.reconcile(assertion_id=assertion_id, event_id=event_id).status == expected_status
    return reconciler


def _unavailable_body() -> dict[str, object]:
    return {"detail": {"reason_code": "impact_unavailable"}}


def test_authorized_impact_summary_exposes_only_receipt_contract(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    _persist_receipt(tmp_foundry, assertion_id)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 200
    assert response.json() == {
        "event_id": "evt_p6_impact",
        "assertion_id": assertion_id,
        "lifecycle_state": "blocked",
        "access_scope": "personal",
        "authoritative_reuse_blocked": True,
        "operation_status": "completed",
        "reason_code": None,
        "replacement_edition_id": None,
        "resumable": False,
        "actions": [
            {
                "object_id": "run_p6_impact",
                "object_class": "run",
                "action": "mark_stale",
                "status": "completed",
            }
        ],
    }
    assert "receipt_path" not in response.text
    assert ".yaml" not in response.text


def test_cross_workspace_impact_read_is_indistinguishable_from_unavailable(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    _persist_receipt(tmp_foundry, assertion_id)
    client = _client(tmp_foundry, AuthIdentity("mallory", "workspace-b", ("viewer",)))

    response = client.get(f"/api/assertions/{assertion_id}/impact")

    assert response.status_code == 404
    assert response.json() == _unavailable_body()
    assert set(response.json()["detail"]) == {"reason_code"}


def test_missing_impact_receipt_returns_typed_unavailable_without_hints(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


def test_writer_persisted_manifest_missing_blocked_receipt_is_served(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id, write_manifest=False)
    receipt = load_yaml(reconciler.receipt_path("evt_p6_impact"))
    assert receipt == {
        "schema_version": "1.0",
        "type": "assertion_impact_operation",
        "event_id": "evt_p6_impact",
        "assertion_id": assertion_id,
        "status": "blocked",
        "reason_code": "dependency_manifest_missing",
        "actions": [],
    }

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 200
    assert response.json()["authoritative_reuse_blocked"] is True
    assert response.json()["lifecycle_state"] == "blocked"
    assert response.json()["operation_status"] == "blocked"
    assert response.json()["reason_code"] == "dependency_manifest_missing"
    assert response.json()["actions"] == []


def test_malformed_impact_receipt_returns_typed_unavailable_without_hints(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    reconciler.receipt_path("evt_p6_impact").write_text("actions: [", encoding="utf-8")

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


@pytest.mark.parametrize("schema_version", [None, "1.1"])
def test_writer_impossible_receipt_schema_version_is_typed_unavailable(
    tmp_foundry, schema_version: str | None
) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id, write_manifest=False)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    if schema_version is None:
        del receipt["schema_version"]
    else:
        receipt["schema_version"] = schema_version
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


def test_omitted_action_key_with_unknown_object_class_is_typed_unavailable(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    actions = receipt["actions"]
    assert isinstance(actions, list)
    actions[0]["object_class"] = "unknown_object_class"
    del actions[0]["action"]
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


def test_unexpected_receipt_processing_error_never_returns_server_error(tmp_foundry, monkeypatch) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    _persist_receipt(tmp_foundry, assertion_id)

    def raise_unexpected(*args, **kwargs):
        raise RuntimeError("unexpected receipt failure")

    monkeypatch.setattr(AssertionImpactReconciler, "validated_receipt", raise_unexpected)
    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code != 500
    assert response.status_code == 404
    assert response.json() == _unavailable_body()


def test_real_interruption_checkpoint_is_safely_served_as_resumable_pending(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id, complete=False, include_second_action=True)
    with pytest.raises(ImpactInterrupted, match="impact_operation_interrupted"):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_p6_impact", _interrupt_after_actions=1)
    receipt = load_yaml(reconciler.receipt_path("evt_p6_impact"))
    assert receipt["status"] == "pending"
    assert [action["status"] for action in receipt["actions"]] == ["completed", "pending"]

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 200
    assert response.json()["operation_status"] == "pending"
    assert response.json()["resumable"] is True
    assert response.json()["actions"] == [
        {
            "object_id": "regeneration_p6_impact",
            "object_class": "assertion_regeneration",
            "action": "regenerate",
            "status": "completed",
        },
        {
            "object_id": "run_p6_impact",
            "object_class": "run",
            "action": "mark_stale",
            "status": "pending",
        },
    ]


def test_pending_receipt_with_completed_action_after_pending_is_unavailable(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id, include_second_action=True)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    receipt["status"] = "pending"
    actions = receipt["actions"]
    assert isinstance(actions, list)
    actions[0]["status"] = "pending"
    actions[1]["status"] = "completed"
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


@pytest.mark.parametrize("mutation", ["truncated", "extra", "manifest_mismatch"])
def test_semantically_malformed_receipt_returns_typed_unavailable_without_hints(tmp_foundry, mutation: str) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    actions = receipt["actions"]
    assert isinstance(actions, list)

    if mutation == "truncated":
        actions.clear()
    elif mutation == "extra":
        actions.append(
            {
                "object_id": "unexpected_object",
                "object_class": "run",
                "action": "mark_stale",
                "status": "pending",
            }
        )
    else:
        reconciler.manifest_path("evt_p6_impact").write_text(
            json.dumps(
                {
                    "expected_objects": [
                        {"object_id": "export_p6_impact", "object_class": "export", "action": "mark_stale"}
                    ]
                }
            ),
            encoding="utf-8",
        )
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()
    assert set(response.json()["detail"]) == {"reason_code"}


def test_unknown_receipt_reason_code_is_unavailable_without_echoing_artifact_text(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    arbitrary_reason = "untrusted_artifact_text_must_not_escape"
    receipt["status"] = "blocked"
    receipt["actions"] = []
    receipt["reason_code"] = arbitrary_reason
    reconciler.manifest_path("evt_p6_impact").write_text(
        json.dumps({"expected_objects": []}), encoding="utf-8"
    )
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()
    assert arbitrary_reason not in response.text


def test_unhashable_receipt_reason_code_is_unavailable_without_echoing_artifact_text(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    arbitrary_reason = ["untrusted_artifact_text_must_not_escape"]
    receipt["status"] = "blocked"
    receipt["actions"] = []
    receipt["reason_code"] = arbitrary_reason
    reconciler.manifest_path("evt_p6_impact").write_text(
        json.dumps({"expected_objects": []}), encoding="utf-8"
    )
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()
    assert arbitrary_reason[0] not in response.text


def test_incoherent_completed_receipt_operation_status_is_unavailable(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    receipt["status"] = "completed"
    actions = receipt["actions"]
    assert isinstance(actions, list)
    actions[0]["status"] = "pending"
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


def test_writer_unreachable_blocked_reason_is_unavailable_with_valid_empty_manifest(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    receipt["status"] = "blocked"
    receipt["reason_code"] = "dependency_graph_unknown"
    receipt["actions"] = []
    dump_yaml(receipt, receipt_path)
    reconciler.manifest_path("evt_p6_impact").write_text(
        json.dumps({"expected_objects": []}), encoding="utf-8"
    )

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 404
    assert response.json() == _unavailable_body()


def test_writeback_statuses_round_trip_through_impact_summary(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    reconciler = _persist_receipt(tmp_foundry, assertion_id, writeback_count=2)
    receipt_path = reconciler.receipt_path("evt_p6_impact")
    receipt = load_yaml(receipt_path)
    assert isinstance(receipt, dict)
    actions = receipt["actions"]
    assert isinstance(actions, list)
    writebacks = [action for action in actions if action["object_class"] == "mock_writeback_receipt"]
    assert len(writebacks) == 2
    writebacks[0]["writeback_status"] = "denied"
    writebacks[1]["writeback_status"] = "queued"
    dump_yaml(receipt, receipt_path)

    response = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",))).get(
        f"/api/assertions/{assertion_id}/impact"
    )

    assert response.status_code == 200
    assert {
        action["writeback_status"]
        for action in response.json()["actions"]
        if action["object_class"] == "mock_writeback_receipt"
    } == {"denied", "queued"}


def test_impact_seam_has_no_mutation_route(tmp_foundry) -> None:
    assertion_id = _setup_assertion(tmp_foundry)
    client = _client(tmp_foundry, AuthIdentity("alice", "workspace-a", ("viewer",)))

    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)(f"/api/assertions/{assertion_id}/impact")
        assert response.status_code == 405
