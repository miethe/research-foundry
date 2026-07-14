"""P3 assertion materialization: exact binding, replay, and rejection coverage."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from research_foundry.frontmatter import dump_md, load_md
from research_foundry.services import claim_mapping, export_service, extraction
from research_foundry.services.assertion_materialization import (
    AssertionMaterializer,
    MaterializationConflict,
    MaterializationInterrupted,
)
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def _setup_run(tmp_foundry, run_id: str, *, content: str = "The measured result was 42 percent."):
    """Create the smallest P2-registered run satisfying the P3 mapping contract."""

    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source = ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Exact Evidence",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    return source


def _ledger(tmp_foundry, run_id: str) -> dict:
    return load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)


def _materialization_dirs(materializer: AssertionMaterializer) -> list[Path]:
    return [
        materializer.root / "assertions",
        materializer.root / "observations",
        materializer.root / "evaluations",
        materializer.root / "audits",
        materializer.root / "materializations",
    ]


def _assert_no_materialization(materializer: AssertionMaterializer) -> None:
    assert not any(directory.exists() for directory in _materialization_dirs(materializer))


def test_p3_materializes_one_exact_fact_claim_passage_chain(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_exact")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_exact")

    assert result.status == "materialized"
    assert len(result.assertion_ids) == 1
    ledger = _ledger(tmp_foundry, "rf_run_p3_exact")
    claim = ledger["claims"][0]
    assert claim["persistent_references"]["source_assertion_id"] == result.assertion_ids[0]
    assert claim["sources"][0]["locator"] == "para/1"
    assertion = load_yaml(materializer._assertion_path(result.assertion_ids[0]))
    assert assertion["extraction_provenance"]["schema_version"] == claim_mapping.EXTRACTION_FACT_CLAIM_MAPPING_VERSION
    assert materializer.schemas.validate(assertion, "source_assertion").ok
    evaluation = load_yaml(next((materializer.root / "evaluations").glob("*.yaml")))
    assert materializer.schemas.validate(evaluation, "assertion_evaluation").ok


def test_identical_historical_runs_share_assertion_identity_but_keep_observations(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_history_a")
    _setup_run(tmp_foundry, "rf_run_p3_history_b")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    first = materializer.materialize_run("rf_run_p3_history_a")
    second = materializer.materialize_run("rf_run_p3_history_b")

    assert first.assertion_ids == second.assertion_ids
    assert len(list((materializer.root / "assertions").glob("*.yaml"))) == 1
    assert len(list((materializer.root / "observations").glob("*.yaml"))) == 2
    assert len(list((materializer.root / "audits").glob("*.yaml"))) == 2


def test_conflicting_existing_deterministic_assertion_is_rejected(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_conflict_a")
    _setup_run(tmp_foundry, "rf_run_p3_conflict_b")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    first = materializer.materialize_run("rf_run_p3_conflict_a")
    assertion_path = materializer._assertion_path(first.assertion_ids[0])
    tampered = load_yaml(assertion_path)
    tampered["assertion_text"] = "Conflicting forged assertion."
    dump_yaml(tampered, assertion_path)

    with pytest.raises(MaterializationConflict, match="existing_source_assertion_invalid"):
        materializer.materialize_run("rf_run_p3_conflict_b")

    assert not (
        materializer.root
        / "materializations"
        / "runs"
        / sha256(b"rf_run_p3_conflict_b").hexdigest()
        / "published.yaml"
    ).exists()


def test_conflicting_published_observation_is_rejected_on_replay(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_observation_conflict")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    materializer.materialize_run("rf_run_p3_observation_conflict")
    observation_path = next((materializer.root / "observations").glob("*.yaml"))
    tampered = load_yaml(observation_path)
    tampered["locator"] = "forged/locator"
    dump_yaml(tampered, observation_path)

    with pytest.raises(MaterializationConflict, match="conflicting_deterministic_record"):
        materializer.materialize_run("rf_run_p3_observation_conflict")


def test_locator_mismatch_abstains_without_materialization(tmp_foundry) -> None:
    source = _setup_run(tmp_foundry, "rf_run_p3_mismatch")
    source_path = tmp_foundry.run_paths("rf_run_p3_mismatch").sources / f"{source.source_card_id}.md"
    metadata, body = load_md(source_path)
    metadata["extracted_points"][0]["locator"] = "forged/locator"
    dump_md(metadata, body, source_path)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_mismatch")

    assert result.status == "abstained"
    assert result.abstention_code == "ambiguous_or_forged_source_evidence"
    _assert_no_materialization(materializer)


def test_cross_source_claim_binding_mismatch_abstains_without_materialization(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_cross_source")
    other = ingest_source(
        "other-evidence.txt",
        run_id="rf_run_p3_cross_source",
        title="Other Evidence",
        sensitivity="personal",
        content="Other source content.",
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    ledger = _ledger(tmp_foundry, "rf_run_p3_cross_source")
    ledger["claims"][0]["sources"][0]["source_card_id"] = other.source_card_id
    dump_yaml(ledger, tmp_foundry.run_paths("rf_run_p3_cross_source").claim_ledger)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_cross_source")

    assert result.status == "abstained"
    assert result.abstention_code == "non_bijective_fact_claim_mapping"
    _assert_no_materialization(materializer)


def test_canonical_candidate_abstains_without_enabling_canonical_behavior(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_canonical")
    ledger = _ledger(tmp_foundry, "rf_run_p3_canonical")
    ledger["claims"][0]["persistent_references"] = {"canonical_claim_id": "ccl_deferred"}
    dump_yaml(ledger, tmp_foundry.run_paths("rf_run_p3_canonical").claim_ledger)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_canonical")

    assert result.status == "abstained"
    assert result.abstention_code == "canonical_or_inference_candidate_deferred"
    _assert_no_materialization(materializer)


def test_fabricated_passage_provenance_abstains_without_materialization(tmp_foundry) -> None:
    source = _setup_run(tmp_foundry, "rf_run_p3_forged")
    source_path = tmp_foundry.run_paths("rf_run_p3_forged").sources / f"{source.source_card_id}.md"
    metadata, body = load_md(source_path)
    metadata["extracted_points"][0]["quote"] = "Fabricated exact quote."
    dump_md(metadata, body, source_path)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_forged")

    assert result.status == "abstained"
    assert result.abstention_code == "fact_source_quote_mismatch"
    _assert_no_materialization(materializer)


@pytest.mark.parametrize("tamper", ["content_sha256", "access_scope", "allowed_use", "retrieval_locator"])
def test_tampered_published_edition_provenance_abstains_without_mutation(tmp_foundry, tamper: str) -> None:
    run_id = f"rf_run_p3_edition_{tamper}"
    _setup_run(tmp_foundry, run_id)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    edition_path = next((materializer.registry.root / "sources").glob("*/editions/*.yaml"))
    edition = load_yaml(edition_path)
    before_ledger = tmp_foundry.run_paths(run_id).claim_ledger.read_bytes()

    if tamper == "content_sha256":
        edition["content_sha256"] = "0" * 64
    elif tamper == "access_scope":
        edition["access_scope"] = "public"
    elif tamper == "allowed_use":
        edition["metadata_extensions"]["allowed_use"]["allowed_for_work_output"] = False
    else:
        edition["retrieval_locator"]["file_path"] = "forged-source.txt"
    dump_yaml(edition, edition_path)

    result = materializer.materialize_run(run_id)

    assert result.status == "abstained"
    assert result.abstention_code == "registry_integrity_rejected"
    assert tmp_foundry.run_paths(run_id).claim_ledger.read_bytes() == before_ledger
    _assert_no_materialization(materializer)


def test_tampered_source_card_snapshot_cannot_select_registry_edition(tmp_foundry) -> None:
    source = _setup_run(tmp_foundry, "rf_run_p3_source_snapshot")
    source_path = tmp_foundry.run_paths("rf_run_p3_source_snapshot").sources / f"{source.source_card_id}.md"
    metadata, body = load_md(source_path)
    metadata["usage"]["allowed_for_work_output"] = False
    dump_md(metadata, body, source_path)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_source_snapshot")

    assert result.status == "abstained"
    assert result.abstention_code == "registry_integrity_rejected"
    _assert_no_materialization(materializer)


def test_tampered_extraction_snapshot_cannot_select_registry_passage(tmp_foundry) -> None:
    run_id = "rf_run_p3_extraction_snapshot"
    _setup_run(tmp_foundry, run_id)
    extraction_path = next(tmp_foundry.run_paths(run_id).extractions.glob("*.yaml"))
    extraction_card = load_yaml(extraction_path)
    extraction_card["extracted_facts"][0]["text"] = "Forged extracted fact."
    dump_yaml(extraction_card, extraction_path)
    ledger = _ledger(tmp_foundry, run_id)
    ledger["claims"][0]["text"] = "Forged extracted fact."
    dump_yaml(ledger, tmp_foundry.run_paths(run_id).claim_ledger)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run(run_id)

    assert result.status == "abstained"
    assert result.abstention_code == "fact_source_quote_mismatch"
    _assert_no_materialization(materializer)


@pytest.mark.parametrize(
    "artifact",
    ["edition", "content", "provenance", "published_generation", "published_passage"],
)
def test_external_symlinked_registry_artifact_abstains_without_mutation(tmp_foundry, artifact: str) -> None:
    run_id = f"rf_run_p3_symlink_{artifact}"
    _setup_run(tmp_foundry, run_id)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    edition_root = next(
        path for path in (materializer.registry.root / "sources").glob("*/editions/*") if path.is_dir()
    )
    targets = {
        "edition": next((materializer.registry.root / "sources").glob("*/editions/*.yaml")),
        "content": edition_root / "content.bin",
        "provenance": edition_root / "provenance.yaml",
        "published_generation": edition_root / "published.yaml",
        "published_passage": next(edition_root.glob("generations/*/passages/*.yaml")),
    }
    target = targets[artifact]
    external = tmp_foundry.root.parent / f"external-{artifact}-{target.name}"
    external.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(external)
    before_ledger = tmp_foundry.run_paths(run_id).claim_ledger.read_bytes()

    result = materializer.materialize_run(run_id)

    assert result.status == "abstained"
    assert result.abstention_code == "registry_integrity_rejected"
    assert tmp_foundry.run_paths(run_id).claim_ledger.read_bytes() == before_ledger
    _assert_no_materialization(materializer)


def test_tampered_registry_generation_path_is_confined_and_rejected(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_registry_tamper")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    publication = next((materializer.registry.root / "sources").glob("*/editions/*/published.yaml"))
    dump_yaml({"generation_id": "../../outside", "passage_ids": ["../../outside"]}, publication)

    result = materializer.materialize_run("rf_run_p3_registry_tamper")

    assert result.status == "abstained"
    assert result.abstention_code == "registry_integrity_rejected"
    _assert_no_materialization(materializer)


def test_published_packet_substitution_is_rejected(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_packet")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    materializer.materialize_run("rf_run_p3_packet")
    dump_yaml({"generation_id": "../../packet-substitution"}, materializer._published_pointer_path("rf_run_p3_packet"))

    with pytest.raises(MaterializationConflict, match="invalid_generation_id"):
        materializer.materialize_run("rf_run_p3_packet")


def test_workspace_isolation_does_not_read_another_workspace_registry(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_workspace")
    materializer = AssertionMaterializer(workspace_id="workspace-b", paths=tmp_foundry)

    result = materializer.materialize_run("rf_run_p3_workspace")

    assert result.status == "abstained"
    assert result.abstention_code == "unresolved_passage_binding"
    _assert_no_materialization(materializer)


def test_interruption_leaves_no_published_pointer_and_retry_is_idempotent(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_interrupt")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    with pytest.raises(MaterializationInterrupted):
        materializer.materialize_run("rf_run_p3_interrupt", _interrupt_before_publish=True)
    assert not materializer._published_pointer_path("rf_run_p3_interrupt").exists()

    retried = materializer.materialize_run("rf_run_p3_interrupt")
    repeated = materializer.materialize_run("rf_run_p3_interrupt")
    assert retried.status == "materialized"
    assert repeated.status == "reused"
    assert retried.assertion_ids == repeated.assertion_ids


def test_bounded_resumable_replay_retains_identity(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_replay_a")
    _setup_run(tmp_foundry, "rf_run_p3_replay_b")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    first = materializer.replay_p0(["rf_run_p3_replay_b", "rf_run_p3_replay_a"], limit=1)
    second = materializer.replay_p0(
        ["rf_run_p3_replay_b", "rf_run_p3_replay_a"], limit=1, cursor=first.next_cursor
    )

    assert first.next_cursor == "rf_run_p3_replay_a"
    assert second.next_cursor is None
    assert first.results[0].assertion_ids == second.results[0].assertion_ids


def test_legacy_and_enriched_export_shapes_preserve_local_claim_semantics(tmp_foundry) -> None:
    _setup_run(tmp_foundry, "rf_run_p3_export")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    original = _ledger(tmp_foundry, "rf_run_p3_export")
    legacy = export_service._build_claims(deepcopy(original), {}, 0)[0]
    assert "persistent_references" not in legacy

    materializer.materialize_run("rf_run_p3_export")
    enriched = _ledger(tmp_foundry, "rf_run_p3_export")
    exported = export_service._build_claims(enriched, {}, 0)[0]

    for key in ("claim_id", "text", "sources", "report_locations", "inference_basis"):
        assert exported[key] == legacy[key]
    assert exported["persistent_references"] == enriched["claims"][0]["persistent_references"]
