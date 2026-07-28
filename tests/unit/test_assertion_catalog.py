"""P4 assertion projection: rebuild, scope, pagination, and denial coverage."""

from __future__ import annotations

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_catalog import AssertionCatalog
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def _materialize(tmp_foundry, run_id: str, workspace_id: str, content: str) -> str:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        f"{run_id}.txt",
        run_id=run_id,
        title=f"Evidence {run_id}",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    result = AssertionMaterializer(workspace_id=workspace_id, paths=tmp_foundry).materialize_run(run_id)
    assert result.status == "materialized"
    return result.assertion_ids[0]


def test_projection_delete_rebuild_has_deterministic_search_parity(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p4_rebuild", "workspace-a", "The durable P4 search fact is 42 percent."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))

    first = catalog.rebuild("workspace-a")
    before = catalog.search(identity=identity, query="42")
    assert before["items"][0]["assertion_id"] == assertion_id

    first.projection_path.unlink()
    second = catalog.rebuild("workspace-a")
    after = catalog.search(identity=identity, query="42")

    assert second.record_count == first.record_count == 1
    assert after == before


def test_search_scopes_before_facets_and_cursor(tmp_foundry) -> None:
    assertion_a = _materialize(
        tmp_foundry, "rf_run_p4_ws_a", "workspace-a", "Workspace A sees only its own evidence."
    )
    assertion_a_second = _materialize(
        tmp_foundry, "rf_run_p4_ws_a_second", "workspace-a", "Workspace A has a second private fact."
    )
    _materialize(tmp_foundry, "rf_run_p4_ws_b", "workspace-b", "Workspace B must remain private.")
    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-a")
    catalog.rebuild("workspace-b")

    result = catalog.search(
        identity=AuthIdentity("alice", "workspace-a", ("viewer",)), query="workspace", limit=1
    )

    assert len(result["items"]) == 1
    assert result["facets"] == {"lifecycle_states": ["eligible"], "access_scopes": ["personal"]}
    assert result["next_cursor"] is not None
    next_page = catalog.search(
        identity=AuthIdentity("alice", "workspace-a", ("viewer",)), query="workspace", limit=1,
        cursor=result["next_cursor"],
    )
    assert {result["items"][0]["assertion_id"], next_page["items"][0]["assertion_id"]} == {
        assertion_a, assertion_a_second,
    }
    assert next_page["next_cursor"] is None
    assert catalog.packet(assertion_a, identity=AuthIdentity("bob", "workspace-b", ("viewer",))) is None


def test_missing_rights_context_returns_typed_empty_response(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_p4_rights", "workspace-a", "Missing rights must deny discovery.")
    catalog = AssertionCatalog(tmp_foundry)
    edition_path = next((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml"))
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)

    catalog.rebuild("workspace-a")
    result = catalog.search(identity=AuthIdentity("alice", "workspace-a", ("viewer",)))

    assert result == AssertionCatalog.denied_payload("rights_context_missing") or result == {
        "items": [],
        "next_cursor": None,
        "facets": {"lifecycle_states": [], "access_scopes": []},
        "denial_reason": None,
    }
    # The public response has no record-derived counts or membership hints.
    assert result["items"] == []
    assert result["facets"] == {"lifecycle_states": [], "access_scopes": []}


def test_authoritatively_blocked_assertion_is_not_a_current_catalog_result(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p5_blocked", "workspace-a", "Invalid evidence must leave current reads."
    )
    assertion_path = next(
        (tmp_foundry.root / "assertion_ledger" / "workspaces").glob(f"*/assertions/{assertion_id}.yaml")
    )
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "blocked"
    dump_yaml(assertion, assertion_path)

    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-a")
    result = catalog.search(identity=AuthIdentity("alice", "workspace-a", ("viewer",)))

    assert result["items"] == []
    assert result["facets"] == {"lifecycle_states": [], "access_scopes": []}


def test_legacy_workspace_without_assertions_stays_empty_and_valid(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    result = catalog.search(identity=AuthIdentity("legacy", "workspace-legacy", ("viewer",)))

    assert result == {
        "items": [],
        "next_cursor": None,
        "facets": {"lifecycle_states": [], "access_scopes": []},
        "denial_reason": None,
    }


# ---------------------------------------------------------------------------
# RF Knowledge MCP KMCP-2.3: non-rebuilding read path
# ---------------------------------------------------------------------------


def test_search_read_only_missing_projection_denies_without_rebuild(tmp_foundry) -> None:
    """Unlike ``search`` (which silently rebuilds -- see the legacy-workspace test
    above), ``search_read_only`` never writes a projection file for a workspace
    that has never been materialized."""

    from research_foundry.services.assertion_catalog import AssertionCatalogUnavailable

    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("legacy", "workspace-never-built", ("viewer",))
    projection_path = catalog.projection_path(identity.workspace_id)
    assert not projection_path.exists()

    result = catalog.search_read_only(identity=identity)

    assert result == AssertionCatalog.denied_payload("catalog_unavailable")
    assert not projection_path.exists()
    with pytest.raises(AssertionCatalogUnavailable):
        catalog._records_read_only(identity.workspace_id)


def test_packet_and_lineage_read_only_missing_projection_raise_without_rebuild(tmp_foundry) -> None:
    from research_foundry.services.assertion_catalog import AssertionCatalogUnavailable

    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("legacy", "workspace-never-built-2", ("viewer",))
    projection_path = catalog.projection_path(identity.workspace_id)

    with pytest.raises(AssertionCatalogUnavailable):
        catalog.packet_read_only("ast_does_not_exist", identity=identity)
    assert not projection_path.exists()

    with pytest.raises(AssertionCatalogUnavailable):
        catalog.lineage_read_only("ast_does_not_exist", identity=identity)
    assert not projection_path.exists()


def test_read_only_methods_match_rebuilt_methods_when_projection_exists(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p4_readonly", "workspace-a", "The read-only seam sees 42 percent too."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))
    catalog.rebuild("workspace-a")

    assert catalog.search_read_only(identity=identity, query="42") == catalog.search(
        identity=identity, query="42"
    )
    assert catalog.packet_read_only(assertion_id, identity=identity) == catalog.packet(
        assertion_id, identity=identity
    )
    assert catalog.lineage_read_only(assertion_id, identity=identity) == catalog.lineage(
        assertion_id, identity=identity
    )


def test_read_only_rights_denial_matches_rebuilt_denial_shape(tmp_foundry) -> None:
    """A policy/rights denial over an ALREADY-BUILT projection returns the same
    bounded shape from both the rebuilding and non-rebuilding surfaces --
    distinguishing "denied" from "unavailable" only via reason code, never shape."""

    _materialize(tmp_foundry, "rf_run_p4_ro_rights", "workspace-a", "Missing rights must deny read-only too.")
    catalog = AssertionCatalog(tmp_foundry)
    edition_path = next((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml"))
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)
    catalog.rebuild("workspace-a")

    identity = AuthIdentity("alice", "workspace-a", ("viewer",))
    assert catalog.search_read_only(identity=identity) == catalog.search(identity=identity)
    assert catalog.search_read_only(identity=identity)["denial_reason"] == "rights_context_missing"
