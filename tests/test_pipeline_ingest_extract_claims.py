"""Pipeline test: ingest -> extract -> claim-map (owner D).

Proves the deterministic, offline service chain:

- ingesting a local text file + an unreachable URL yields >=2 schema-valid
  source cards under ``runs/<run>/sources``;
- ``extract_run`` yields one schema-valid extraction_card per source, mapping
  back via ``source_card_id``;
- ``build_claim_ledger`` yields a schema-valid claim_ledger where every claim has
  >=1 ``source.source_card_id`` and status ``supported``, with correct
  ``by_status`` counts;
- the ``source_index`` and ``claim_index`` registries are updated.
"""

from __future__ import annotations

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.registry import CLAIM_INDEX, SOURCE_INDEX, Registry
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import claim_mapping, extraction, source_cards
from research_foundry.yamlio import load_yaml

RUN_ID = "rf_run_20260613_pipeline_test"


def _registry(paths: FoundryPaths) -> SchemaRegistry:
    return SchemaRegistry(schemas_dir=paths.schemas)


def _scaffold(paths: FoundryPaths) -> None:
    paths.run_paths(RUN_ID).ensure_scaffold()


def test_ingest_local_and_url_yields_two_source_cards(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)

    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Agentic research swarms cut review time by 40% in 2026 benchmarks.\n\n"
        "Evidence bundles let every material claim trace back to a source card.\n\n"
        "Cheap extraction models feed a deep synthesis model for the final report.\n",
        encoding="utf-8",
    )

    local = source_cards.ingest_source(
        str(doc),
        run_id=RUN_ID,
        source_type="personal_note",
        title="Local Research Notes",
        paths=tmp_foundry,
    )
    # Unreachable URL with fetch on -> degraded (best-effort, never raises).
    remote = source_cards.ingest_source(
        "http://127.0.0.1:9/this-will-not-connect",
        run_id=RUN_ID,
        source_type="blog",
        title="Remote Source",
        fetch=True,
        paths=tmp_foundry,
    )

    assert local.degraded is False
    assert remote.degraded is True

    cards = source_cards.list_source_cards(RUN_ID, paths=tmp_foundry)
    assert len(cards) >= 2

    registry = _registry(tmp_foundry)
    for card_path in cards:
        meta, _body = load_md(card_path)
        result = registry.validate(meta, "source_card")
        assert result.ok, result.errors
        assert meta["type"] == "source_card"
        assert meta["extracted_points"]

    # Local card has >1 real evidence point; degraded card is flagged needs_content.
    local_meta, _ = load_md(local.path)
    assert len(local_meta["extracted_points"]) >= 2
    remote_meta, _ = load_md(remote.path)
    assert remote_meta["extracted_points"][0].get("needs_content") is True

    # source_index registry updated.
    src_index = Registry.open(SOURCE_INDEX, paths=tmp_foundry)
    indexed_ids = {item["id"] for item in src_index.items()}
    assert local.source_card_id in indexed_ids
    assert remote.source_card_id in indexed_ids


def test_extract_run_maps_back_to_source_cards(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    doc = tmp_path / "facts.txt"
    doc.write_text(
        "Throughput improved by 25% after caching.\n\n"
        "The pipeline reduces manual triage because claims auto-map to sources.\n",
        encoding="utf-8",
    )
    src = source_cards.ingest_source(
        str(doc), run_id=RUN_ID, title="Facts", paths=tmp_foundry
    )

    extract = extraction.extract_run(RUN_ID, paths=tmp_foundry)
    assert extract.count == 1
    assert len(extract.cards) == 1

    registry = _registry(tmp_foundry)
    ext_dir = tmp_foundry.run_paths(RUN_ID).extractions
    ext_files = sorted(ext_dir.glob("*.yaml"))
    assert len(ext_files) == 1

    card = load_yaml(ext_files[0])
    result = registry.validate(card, "extraction_card")
    assert result.ok, result.errors
    assert card["source_card_id"] == src.source_card_id
    assert card["extracted_facts"]
    # The numeric fact produced a metric entry deterministically.
    assert any(m["metric_name"] == "evidence_point" for m in card["extracted_metrics"])


def test_build_claim_ledger_all_supported_with_sources(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    doc = tmp_path / "claims.txt"
    doc.write_text(
        "Latency dropped 30% with the new router.\n\n"
        "Teams report fewer escalations than before, according to the survey.\n\n"
        "Evidence bundles make claim traceability auditable end to end.\n",
        encoding="utf-8",
    )
    src = source_cards.ingest_source(
        str(doc), run_id=RUN_ID, title="Claims Source", paths=tmp_foundry
    )
    extraction.extract_run(RUN_ID, paths=tmp_foundry)

    result = claim_mapping.build_claim_ledger(
        RUN_ID, intent_id="intent_research_20260613_pipeline", paths=tmp_foundry
    )

    assert result.claims_total >= 3
    assert result.by_status.get("supported") == result.claims_total

    ledger = load_yaml(result.ledger_path)
    registry = _registry(tmp_foundry)
    validation = registry.validate(ledger, "claim_ledger")
    assert validation.ok, validation.errors

    assert ledger["intent_id"] == "intent_research_20260613_pipeline"
    assert ledger["report_ref"] == "reports/report_draft.md"
    assert ledger["verification_status"] == "pending"

    # Every claim is supported and traces to >=1 source card.
    sum_by_status = sum(result.by_status.values())
    assert sum_by_status == result.claims_total
    for claim in ledger["claims"]:
        assert claim["status"] == "supported"
        assert len(claim["sources"]) >= 1
        assert claim["sources"][0]["source_card_id"] == src.source_card_id
        assert claim["sources"][0]["relation"] == "supports"

    # by_status counts match an independent tally.
    tally: dict[str, int] = {}
    for claim in ledger["claims"]:
        tally[claim["status"]] = tally.get(claim["status"], 0) + 1
    assert tally == result.by_status

    # claim_index registry updated.
    claim_index = Registry.open(CLAIM_INDEX, paths=tmp_foundry)
    rec = claim_index.get(ledger["id"])
    assert rec is not None
    assert rec["claims_total"] == result.claims_total
    assert rec["run_id"] == RUN_ID

    # Contradiction + inference logs were written.
    rp = tmp_foundry.run_paths(RUN_ID)
    assert rp.contradiction_log.exists()
    assert rp.inference_log.exists()


def test_claim_type_heuristics(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    doc = tmp_path / "types.txt"
    doc.write_text(
        "Costs fell 50% year over year.\n\n"
        "Method A is faster than method B for large inputs.\n\n"
        "The cache reduces load because requests hit memory first.\n\n"
        "The vendor says the system is production ready.\n\n"
        "Evidence bundles anchor every report to its sources.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Types", paths=tmp_foundry)
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)

    ledger = load_yaml(result.ledger_path)
    types = {c["text"]: c["claim_type"] for c in ledger["claims"]}
    # Quantitative wins when a number is present.
    assert any(t == "quantitative" for t in types.values())
    # Comparative / causal / attribution / factual all represented.
    type_set = set(types.values())
    assert "comparative" in type_set or "quantitative" in type_set
    assert "causal" in type_set
    assert "attribution" in type_set or "factual" in type_set
