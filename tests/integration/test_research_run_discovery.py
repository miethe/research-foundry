"""RPC-2.2: governed discovery (list/fetch) over research-run activities.

Exercises the read counterpart to ``provenance_envelope.py``'s writers --
``research_run_discovery.py`` -- against a real, on-disk workspace store.
"""

from __future__ import annotations

import pytest

from research_foundry.services import export_service
from research_foundry.services.provenance_envelope import ProvenanceEnvelopeStore
from research_foundry.services.research_run_discovery import (
    ResearchRunDiscovery,
    ResearchRunDiscoveryDenied,
)
from research_foundry.yamlio import dumps_yaml


def _scope() -> dict:
    return {"provider": "pubmed", "site": None, "corpus": None}


def _selected_receipt() -> dict:
    return {
        "outcome": "selected",
        "source": "pubmed",
        "catalog_generation_id": None,
        "decided_at": "2026-07-28T12:10:05Z",
        "denial_reason": None,
        "degraded_reason": None,
        "fallback_reason": None,
    }


def _evidence() -> list[dict]:
    return [
        {
            "assertion_id": f"ast_{'a' * 64}",
            "assertion_version": 1,
            "question_id": None,
            "decided_at": None,
        }
    ]


def _make_search_only_activity(store: ProvenanceEnvelopeStore) -> tuple[dict, dict]:
    v1 = store.create_envelope_v1(activity_kind="search_only", request_id="req-77")
    receipt, v2 = store.create_receipt_and_promote(
        v1,
        query="test query with zero matches",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="7" * 64,
        selected_evidence_versions=[],
        selection_receipt={
            "outcome": "empty",
            "source": "pubmed",
            "catalog_generation_id": None,
            "decided_at": "2026-07-28T13:00:05Z",
            "denial_reason": None,
            "degraded_reason": None,
            "fallback_reason": None,
        },
    )
    return v2, receipt


def _make_planned_run_activity(store: ProvenanceEnvelopeStore, run_id: str) -> tuple[dict, dict]:
    v1 = store.create_envelope_v1(
        activity_kind="planned_run", planned_run_ref={"run_id": run_id}, request_id="req-42"
    )
    receipt, v2 = store.create_receipt_and_promote(
        v1,
        query="pediatric CBC reference intervals",
        purpose="evidence gathering",
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )
    return v2, receipt


def test_search_only_activity_is_discoverable_with_no_planned_run(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_search_only_activity(store)

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    listing = discovery.list_activities(activity_kind="search_only")

    assert listing["denial_reason"] is None
    ids = {item["envelope_id"] for item in listing["items"]}
    assert envelope["envelope_id"] in ids
    item = next(i for i in listing["items"] if i["envelope_id"] == envelope["envelope_id"])
    assert item["planned_run_ref"] is None
    assert item["outcome"] == "empty"
    # No fabricated run_id anywhere on the result (RPC-FR-2).
    assert "run_id" not in item or item.get("planned_run_ref") is None

    fetched = discovery.fetch_activity(envelope["envelope_id"])
    assert fetched.envelope["envelope_id"] == envelope["envelope_id"]
    assert fetched.envelope["planned_run_ref"] is None


def test_list_activities_reports_receipt_outcome(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_planned_run_activity(store, "run-2026-07-28-001")

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    listing = discovery.list_activities(activity_kind="planned_run")
    item = next(i for i in listing["items"] if i["envelope_id"] == envelope["envelope_id"])
    assert item["outcome"] == "selected"
    assert item["planned_run_ref"] == {"run_id": "run-2026-07-28-001"}


def test_fetch_activity_unknown_id_denied_leaks_nothing(tmp_foundry) -> None:
    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    with pytest.raises(ResearchRunDiscoveryDenied) as exc_info:
        discovery.fetch_activity(f"rre_{'0' * 64}")
    assert exc_info.value.reason_code == "not_authorized_or_not_found"

    payload = ResearchRunDiscovery.denied_payload(exc_info.value.reason_code)
    assert payload == {
        "items": [],
        "next_cursor": None,
        "denial_reason": "not_authorized_or_not_found",
    }


def test_fetch_activity_cross_workspace_denied(tmp_foundry) -> None:
    store_a = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_search_only_activity(store_a)

    discovery_b = ResearchRunDiscovery(workspace_id="ws-b", paths=tmp_foundry)
    with pytest.raises(ResearchRunDiscoveryDenied) as exc_info:
        discovery_b.fetch_activity(envelope["envelope_id"])
    assert exc_info.value.reason_code == "not_authorized_or_not_found"

    # The owning workspace can still fetch it.
    discovery_a = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    fetched = discovery_a.fetch_activity(envelope["envelope_id"])
    assert fetched.envelope["envelope_id"] == envelope["envelope_id"]


def test_fetch_planned_run_activity_reuses_run_read_allowed_guard(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RPC-2.2 must reuse ``export_service._run_read_allowed`` for run-scoped
    reads rather than reimplementing run visibility -- confirmed here by
    monkeypatching that exact function and asserting the discovery module's
    result follows it verbatim."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_planned_run_activity(store, "run-owned-by-someone-else")

    calls: list[tuple[str, object]] = []

    def _fake_run_read_allowed(paths, run_meta, run_id, identity):  # noqa: ANN001
        calls.append((run_id, identity))
        return False

    monkeypatch.setattr(export_service, "_run_read_allowed", _fake_run_read_allowed)

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    with pytest.raises(ResearchRunDiscoveryDenied):
        discovery.fetch_activity(
            envelope["envelope_id"],
            identity=object(),
            run_meta_loader=lambda run_id: {"workspace_id": "some-other-workspace"},
        )
    assert calls and calls[0][0] == "run-owned-by-someone-else"


def test_fetch_planned_run_activity_allowed_when_run_meta_missing(tmp_foundry) -> None:
    """A run_meta_loader that cannot resolve the run (returns None) must not
    itself deny the activity fetch -- absence of run metadata is not treated
    as a denial signal here; only an explicit False from the reused guard is.
    """

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_planned_run_activity(store, "run-not-found-elsewhere")

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    fetched = discovery.fetch_activity(
        envelope["envelope_id"], run_meta_loader=lambda run_id: None
    )
    assert fetched.envelope["envelope_id"] == envelope["envelope_id"]


# --- T2-5 attack coverage (Terra P2 cross-model audit hardening) ------------


def test_fetch_activity_uses_internal_default_loader_when_loader_omitted(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-5: omitting ``run_meta_loader`` entirely must NOT bypass run-
    visibility checking -- the discovery service resolves the run's own
    on-disk metadata itself (``_default_run_meta_loader``) and still applies
    ``export_service._run_read_allowed``, closing the caller-optional-loader
    escape hatch the finding identified. A real ``run.yaml`` is planted on
    disk so the internal default loader has something real to resolve."""

    run_id = "run-2026-07-28-internal-default"
    run_dir = tmp_foundry.run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.yaml").write_text(
        dumps_yaml({"run_id": run_id, "workspace_id": "some-other-workspace"}),
        encoding="utf-8",
    )

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_planned_run_activity(store, run_id)

    calls: list[str] = []

    def _fake_run_read_allowed(paths, run_meta, run_id_arg, identity):  # noqa: ANN001
        calls.append(run_id_arg)
        return False

    monkeypatch.setattr(export_service, "_run_read_allowed", _fake_run_read_allowed)

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    with pytest.raises(ResearchRunDiscoveryDenied):
        discovery.fetch_activity(envelope["envelope_id"], identity=object())
    assert calls == [run_id]


def test_list_activities_excludes_planned_run_denied_by_run_read_allowed(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-5: listing must apply the SAME ``_run_read_allowed`` guard as
    fetch -- an identity not authorized to read the referenced run must not
    see that ``planned_run`` activity in the listing at all (an
    unauthorized-list attempt is silently filtered, never raised)."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_planned_run_activity(store, "run-owned-by-someone-else")
    other, _other_receipt = _make_search_only_activity(store)

    def _fake_run_read_allowed(paths, run_meta, run_id, identity):  # noqa: ANN001
        return False

    monkeypatch.setattr(export_service, "_run_read_allowed", _fake_run_read_allowed)

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    listing = discovery.list_activities(
        identity=object(),
        run_meta_loader=lambda run_id: {"workspace_id": "some-other-workspace"},
    )
    ids = {item["envelope_id"] for item in listing["items"]}
    assert envelope["envelope_id"] not in ids
    # A search_only activity (no run to gate) is unaffected by the denial.
    assert other["envelope_id"] in ids


def test_list_activities_uses_internal_default_loader_when_loader_omitted(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-5: listing's own escape-hatch closure -- omitting
    ``run_meta_loader`` on ``list_activities`` still resolves the run's real
    on-disk metadata and applies the guard, exactly as ``fetch_activity``
    now does."""

    run_id = "run-2026-07-28-listing-internal-default"
    run_dir = tmp_foundry.run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.yaml").write_text(
        dumps_yaml({"run_id": run_id, "workspace_id": "some-other-workspace"}),
        encoding="utf-8",
    )

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    envelope, _receipt = _make_planned_run_activity(store, run_id)

    monkeypatch.setattr(
        export_service,
        "_run_read_allowed",
        lambda paths, run_meta, run_id_arg, identity: False,
    )

    discovery = ResearchRunDiscovery(workspace_id="ws-a", paths=tmp_foundry)
    listing = discovery.list_activities(identity=object())
    ids = {item["envelope_id"] for item in listing["items"]}
    assert envelope["envelope_id"] not in ids
