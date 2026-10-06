"""Uncited registered source cards through governed knowledge references.

node_01M44WQKMNDCYH3RP5NMNRZ7P6 (consumed by the Cognitive Salon pack-pinning
node node_01M3ZX1NEYG1FAA2YK18K2PKW3). Locator-only cards registered with
``ingest_source`` and cited by NO claim must project into the catalog and
resolve through the governed source getter by their stable ``source_card_id``
(``rfk:v1:source:<source_card_id>``) -- never through a synthetic citation,
never as claim/full-text evidence, and never past a stale/unavailable card.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.cli import app as rf_cli_app
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import catalog_service as catalog_svc
from research_foundry.services import knowledge_access as ka
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml
from tests.unit.test_catalog_service import _write_threshold, build_catalog_run

RUN_ID = "rf_run_salon_pack001"


@pytest.fixture(autouse=True)
def _clean_projector_registry():
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)
    yield
    for kind in list(ka.KNOWLEDGE_KINDS):
        ka.unregister_projector(kind)


def _scaffold_run(paths: FoundryPaths, run_id: str = RUN_ID, *, sensitivity: str = "public") -> None:
    """A run with NO claim ledger at all -- nothing can cite its cards."""

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": "intent_salon_pack001",
            "status": "planned",
            "sensitivity": sensitivity,
            "created_at": "2026-10-06T10:00:00-04:00",
        },
        rp.run_yaml,
    )


def _register_locator_only_cards(paths: FoundryPaths, run_id: str = RUN_ID, *, sensitivity: str = "public"):
    doi_card = ingest_source(
        "https://doi.org/10.1000/salon.001",
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        title="Salon Reading One",
        doi="10.1000/salon.001",
        paths=paths,
    )
    isbn_card = ingest_source(
        "isbn:9780000000002",
        run_id=run_id,
        source_type="book",
        sensitivity=sensitivity,
        title="Salon Reading Two",
        paths=paths,
    )
    return doi_card, isbn_card


def _service(paths: FoundryPaths) -> ka.KnowledgeAccessService:
    ka.register_projector("source", ka.SourceKindProjector(paths))
    return ka.KnowledgeAccessService(paths)


def _ctx(paths: FoundryPaths, **kwargs) -> ka.KnowledgeAccessContext:
    return ka.resolve_context(paths, tool="rf_source_get", **kwargs)


def _api(paths: FoundryPaths) -> TestClient:
    app = create_app(FoundryConfig(paths=paths))
    app.dependency_overrides[get_paths] = lambda: paths
    return TestClient(app)


def _rewrite_card(path: Path, **changes) -> None:
    meta, body = load_md(path)
    for key, value in changes.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    dump_md(meta, body, path)


def _prepared(tmp_foundry: FoundryPaths):
    _scaffold_run(tmp_foundry)
    cards = _register_locator_only_cards(tmp_foundry)
    _write_threshold(tmp_foundry, "client_sensitive")
    catalog_svc.import_run(tmp_foundry, RUN_ID)
    return cards


# ---------------------------------------------------------------------------
# AC3: real consumer readback -- register, project, read back by reference
# ---------------------------------------------------------------------------


def test_registered_uncited_card_reads_back_by_source_card_reference(tmp_foundry: FoundryPaths) -> None:
    doi_card, isbn_card = _prepared(tmp_foundry)
    assert doi_card.extraction_status == "locator_only"
    assert isbn_card.extraction_status == "locator_only"
    service = _service(tmp_foundry)

    expected_doi = {doi_card.source_card_id: "10.1000/salon.001", isbn_card.source_card_id: None}
    for card, title in ((doi_card, "Salon Reading One"), (isbn_card, "Salon Reading Two")):
        ref = f"rfk:v1:source:{card.source_card_id}"
        doc = service.fetch_extended(_ctx(tmp_foundry), knowledge_id=ref)
        assert doc.id == ref
        assert doc.kind == "source"
        assert doc.title == title
        meta = doc.rf_metadata
        assert meta is not None
        assert meta["provenance"]["source_card_id"] == card.source_card_id
        assert meta["provenance"]["run_id"] == RUN_ID
        assert meta["evidence_points"] == []
        assert meta["registration"] == {
            "source_ref": ref,
            "citation_state": "uncited",
            "extraction_status": "locator_only",
            "claim_verification": "none",
            "bibliographic_verification": "unknown",
            "full_text_verification": "unknown",
            "doi": expected_doi[card.source_card_id],
        }

    # http(s) locator survives as original_source_url; the isbn: locator never does.
    doi_doc = service.fetch_extended(_ctx(tmp_foundry), knowledge_id=f"rfk:v1:source:{doi_card.source_card_id}")
    assert doi_doc.original_source_url == "https://doi.org/10.1000/salon.001"
    isbn_doc = service.fetch_extended(_ctx(tmp_foundry), knowledge_id=f"rfk:v1:source:{isbn_card.source_card_id}")
    assert isbn_doc.original_source_url is None


def test_search_emits_the_pinnable_source_reference(tmp_foundry: FoundryPaths) -> None:
    doi_card, _ = _prepared(tmp_foundry)
    service = _service(tmp_foundry)
    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="salon reading one")
    ids = [r.id for r in outcome.results]
    assert ids == [f"rfk:v1:source:{doi_card.source_card_id}"]
    # The search id round-trips through the typed getter.
    assert service.fetch_extended(_ctx(tmp_foundry), knowledge_id=ids[0]).id == ids[0]


def test_registered_reference_resolves_over_http_and_cli(tmp_foundry: FoundryPaths) -> None:
    doi_card, _ = _prepared(tmp_foundry)
    ref = f"rfk:v1:source:{doi_card.source_card_id}"

    response = _api(tmp_foundry).get(f"/api/knowledge/source/{ref}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == ref
    assert body["rf_metadata"]["registration"]["extraction_status"] == "locator_only"

    prev = Path.cwd()
    os.chdir(tmp_foundry.root)
    try:
        result = CliRunner().invoke(rf_cli_app, ["knowledge", "source-get", ref])
    finally:
        os.chdir(prev)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["rf_metadata"]["registration"]["citation_state"] == "uncited"


# ---------------------------------------------------------------------------
# AC2: locator registration never becomes claim/full-text evidence; stale and
# unavailable references fail explicitly
# ---------------------------------------------------------------------------


def test_registered_rows_carry_no_claim_support_or_evidence(tmp_foundry: FoundryPaths) -> None:
    doi_card, isbn_card = _prepared(tmp_foundry)
    conn = sqlite3.connect(str(tmp_foundry.catalog_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM catalog_items WHERE run_id = ?", (RUN_ID,)).fetchall()
    links = conn.execute("SELECT * FROM catalog_links WHERE run_id = ?", (RUN_ID,)).fetchall()
    conn.close()
    # Only the two cards -- no claim, inference, or citation was synthesized.
    assert {r["item_type"] for r in rows} == {"source"}
    assert sorted(r["local_ref"] for r in rows) == sorted([doi_card.source_card_id, isbn_card.source_card_id])
    assert links == []
    for row in rows:
        assert row["source_count"] == 0
        payload = json.loads(row["payload_json"])
        assert payload["evidence_points"] == []
        assert payload["registration"]["claim_verification"] == "none"
        assert payload["registration"]["extraction_status"] == "locator_only"


def test_missing_extraction_status_stays_unknown_never_promoted(tmp_foundry: FoundryPaths) -> None:
    _scaffold_run(tmp_foundry)
    doi_card, _ = _register_locator_only_cards(tmp_foundry)
    _rewrite_card(doi_card.path, extraction_status=None)
    _write_threshold(tmp_foundry, "client_sensitive")
    catalog_svc.import_run(tmp_foundry, RUN_ID)

    doc = _service(tmp_foundry).fetch_extended(
        _ctx(tmp_foundry), knowledge_id=f"rfk:v1:source:{doi_card.source_card_id}"
    )
    registration = doc.rf_metadata["registration"]
    assert registration["extraction_status"] == "unknown"
    assert registration["full_text_verification"] == "unknown"
    assert registration["bibliographic_verification"] == "unknown"


def test_rewritten_card_reference_fails_as_stale(tmp_foundry: FoundryPaths) -> None:
    doi_card, _ = _prepared(tmp_foundry)
    ref = f"rfk:v1:source:{doi_card.source_card_id}"
    _rewrite_card(doi_card.path, extraction_status="full_text")  # changed after projection

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        _service(tmp_foundry).fetch_extended(_ctx(tmp_foundry), knowledge_id=ref)
    assert excinfo.value.reason == "stale_reference"

    # Re-projection picks up the new state; the reference resolves again.
    catalog_svc.import_run(tmp_foundry, RUN_ID)
    doc = _service(tmp_foundry).fetch_extended(_ctx(tmp_foundry), knowledge_id=ref)
    assert doc.rf_metadata["registration"]["extraction_status"] == "full_text"
    # Content fidelity never becomes a verification claim.
    assert doc.rf_metadata["registration"]["full_text_verification"] == "unknown"
    assert doc.rf_metadata["registration"]["claim_verification"] == "none"


def test_removed_card_reference_fails_as_unavailable_and_http_404(tmp_foundry: FoundryPaths) -> None:
    doi_card, _ = _prepared(tmp_foundry)
    ref = f"rfk:v1:source:{doi_card.source_card_id}"
    doi_card.path.unlink()

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        _service(tmp_foundry).fetch_extended(_ctx(tmp_foundry), knowledge_id=ref)
    assert excinfo.value.reason == "reference_unavailable"

    response = _api(tmp_foundry).get(f"/api/knowledge/source/{ref}")
    assert response.status_code == 404
    assert "unavailable" not in response.text  # generic, no-leak denial


def test_unknown_reference_and_unbuilt_catalog_fail_explicitly(tmp_foundry: FoundryPaths) -> None:
    _scaffold_run(tmp_foundry)
    doi_card, _ = _register_locator_only_cards(tmp_foundry)
    service = _service(tmp_foundry)
    ref = f"rfk:v1:source:{doi_card.source_card_id}"
    # Registered but never projected: explicit denial, and no rebuild happens.
    with pytest.raises(ka.KnowledgeDenied) as unbuilt:
        service.fetch_extended(_ctx(tmp_foundry), knowledge_id=ref)
    assert unbuilt.value.reason == "projection_unavailable"
    assert not tmp_foundry.catalog_db.exists()

    catalog_svc.import_run(tmp_foundry, RUN_ID)
    with pytest.raises(ka.KnowledgeDenied) as unknown:
        service.fetch_extended(_ctx(tmp_foundry), knowledge_id="rfk:v1:source:src_20261006_never_registered_x")
    assert unknown.value.reason == "not_found"


# ---------------------------------------------------------------------------
# AC1: sensitivity + workspace checks preserved on the new reference form
# ---------------------------------------------------------------------------


def test_registered_reference_respects_sensitivity_ceiling(tmp_foundry: FoundryPaths) -> None:
    _scaffold_run(tmp_foundry)
    doi_card, _ = _register_locator_only_cards(tmp_foundry, sensitivity="personal")
    catalog_svc.import_run(tmp_foundry, RUN_ID)
    ref = f"rfk:v1:source:{doi_card.source_card_id}"
    service = _service(tmp_foundry)

    _write_threshold(tmp_foundry, "public")
    with pytest.raises(ka.KnowledgeDenied) as hidden:
        service.fetch_extended(_ctx(tmp_foundry), knowledge_id=ref)
    assert hidden.value.reason == "not_found"
    assert service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="salon").results == ()

    _write_threshold(tmp_foundry, "personal")
    assert service.fetch_extended(_ctx(tmp_foundry), knowledge_id=ref).id == ref


def test_missing_card_sensitivity_label_fails_closed(tmp_foundry: FoundryPaths) -> None:
    _scaffold_run(tmp_foundry)
    doi_card, _ = _register_locator_only_cards(tmp_foundry)
    _rewrite_card(doi_card.path, sensitivity=None)
    _write_threshold(tmp_foundry, "client_sensitive")
    catalog_svc.import_run(tmp_foundry, RUN_ID)

    with pytest.raises(ka.KnowledgeDenied) as hidden:
        _service(tmp_foundry).fetch_extended(
            _ctx(tmp_foundry), knowledge_id=f"rfk:v1:source:{doi_card.source_card_id}"
        )
    assert hidden.value.reason == "not_found"


def test_registered_reference_respects_workspace_isolation(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    doi_card, _ = _prepared(tmp_foundry)
    monkeypatch.setattr(
        FoundryConfig, "resolve_workspace_isolation_enforced", lambda self, provider, bind_host: True
    )
    ref = f"rfk:v1:source:{doi_card.source_card_id}"
    service = _service(tmp_foundry)

    foreign = _ctx(tmp_foundry, identity=AuthIdentity("eve", "workspace-other", ("viewer",)))
    with pytest.raises(ka.KnowledgeDenied) as cross:
        service.fetch_extended(foreign, knowledge_id=ref)
    assert cross.value.reason == "not_found"

    own = _ctx(tmp_foundry, identity=AuthIdentity("nick", "default", ("viewer",)))
    assert service.fetch_extended(own, knowledge_id=ref).id == ref


def test_same_card_id_in_two_runs_is_refused_as_ambiguous(tmp_foundry: FoundryPaths) -> None:
    _scaffold_run(tmp_foundry, RUN_ID)
    _scaffold_run(tmp_foundry, "rf_run_salon_pack002")
    first, _ = _register_locator_only_cards(tmp_foundry, RUN_ID)
    second, _ = _register_locator_only_cards(tmp_foundry, "rf_run_salon_pack002")
    assert first.source_card_id == second.source_card_id
    _write_threshold(tmp_foundry, "client_sensitive")
    catalog_svc.import_run(tmp_foundry, RUN_ID)
    catalog_svc.import_run(tmp_foundry, "rf_run_salon_pack002")

    with pytest.raises(ka.KnowledgeDenied) as excinfo:
        _service(tmp_foundry).fetch_extended(
            _ctx(tmp_foundry), knowledge_id=f"rfk:v1:source:{first.source_card_id}"
        )
    assert excinfo.value.reason == "ambiguous_reference"


# ---------------------------------------------------------------------------
# AC3: claim-derived behavior unchanged
# ---------------------------------------------------------------------------


def test_claim_derived_source_rows_unchanged_and_not_duplicated(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    catalog_svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    item_id = catalog_svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    conn = sqlite3.connect(str(tmp_foundry.catalog_db))
    conn.row_factory = sqlite3.Row
    alpha_rows = conn.execute("SELECT payload_json FROM catalog_items WHERE local_ref = 'src_alpha'").fetchall()
    conn.close()
    assert len(alpha_rows) == 1  # cited card: one claim-derived row, no registered twin
    assert "registration" not in json.loads(alpha_rows[0]["payload_json"])

    service = _service(tmp_foundry)
    by_ci = service.fetch_extended(_ctx(tmp_foundry), knowledge_id=f"rfk:v1:source:{item_id}")
    assert "registration" not in by_ci.rf_metadata
    assert by_ci.rf_metadata["provenance"]["catalog_item_id"] == item_id
    # The stable card reference resolves the SAME claim-derived row.
    by_ref = service.fetch_extended(_ctx(tmp_foundry), knowledge_id="rfk:v1:source:src_alpha")
    assert by_ref.rf_metadata == by_ci.rf_metadata
    assert by_ref.text == by_ci.text
    # Claim-derived search ids keep the ci_ form.
    outcome = service.search_extended(ka.resolve_context(tmp_foundry, tool="rf_search"), query="alpha")
    assert f"rfk:v1:source:{item_id}" in [r.id for r in outcome.results]
