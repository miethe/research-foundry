from hashlib import sha256
from pathlib import Path
from shutil import copy2

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import extraction, source_cards
from research_foundry.services.assertion_materialization import (
    AssertionMaterializer,
    materialize_assertion,
    replay_facts,
)
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.yamlio import dump_yaml, load_yaml

RIGHTS = {"sensitivity": "personal", "allowed_for_work_output": True}
PROVENANCE = {"contract": "extracted_facts-1to1-v1", "extractor": "test", "observed_at": "2026-07-13T00:00:00Z"}


def _durable_inputs(tmp_foundry, *, content: str = "Exact fact.", run_id: str = "rf_run_materialization", locator: str = "materialization.txt"):
    """Create a real extraction-card fact and a matching published passage."""

    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source = source_cards.ingest_source(locator, run_id=run_id, content=content, paths=tmp_foundry)
    extraction.extract_run(run_id, paths=tmp_foundry)
    card = load_yaml(next(tmp_foundry.run_paths(run_id).extractions.glob("*.yaml")))
    facts = card["extracted_facts"]
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    edition = registry.ingest(source.source_card_id, "\n".join(fact["text"] for fact in facts), passages=[fact["text"] for fact in facts], allowed_use=RIGHTS)
    passages_by_quote = {passage["context"]["exact_quote"]: passage for passage in edition.passages}
    provenance = [
        {
            **PROVENANCE,
            "extraction_card_id": card["id"],
            "source_card_id": card["source_card_id"],
            "evidence_id": fact["evidence_id"],
            "locator": fact["locator"],
        }
        for fact in facts
    ]
    return source.source_card_id, edition, facts, passages_by_quote, provenance


def test_phase0_extraction_fixture_backfill_is_bounded_and_immutable(tmp_path):
    fixture_root = Path(__file__).parents[1] / "fixtures" / "assertion_ledger" / "rf_phase0_evidence_snapshot"
    snapshot = {str(path.relative_to(fixture_root)): sha256(path.read_bytes()).hexdigest() for path in fixture_root.rglob("*") if path.is_file()}
    paths = FoundryPaths(root=tmp_path)
    run_id = "rf_run_phase0_backfill"
    run_paths = paths.run_paths(run_id)
    run_paths.ensure_scaffold()
    source = fixture_root / "sources" / "src_20260713_reusable_assertion_ledger_phase_0_fixture_2cc94967.md"
    copy2(source, run_paths.sources / source.name)
    extraction.extract_run(run_id, paths=paths)
    card = load_yaml(next(run_paths.extractions.glob("*.yaml")))
    assert len(card["extracted_facts"]) == 8
    registry = AssertionRegistry(workspace_id="phase0-backfill", paths=paths)
    fact_texts = [fact["text"] for fact in card["extracted_facts"]]
    source_key = card["source_card_id"]
    published = registry.ingest(source_key, "\n".join(fact_texts), passages=fact_texts, allowed_use=RIGHTS)
    assert published.reusable and len(published.passages) == 8
    facts = [{"passage": passage, "text": fact["text"], "provenance": {**PROVENANCE, "extraction_card_id": card["id"], "source_card_id": card["source_card_id"], "evidence_id": fact["evidence_id"], "locator": fact["locator"]}} for fact, passage in zip(card["extracted_facts"], published.passages, strict=True)]
    assert len(facts) == 8
    assert all(item["provenance"]["locator"] == fact["locator"] for item, fact in zip(facts, card["extracted_facts"], strict=True))
    materializer = AssertionMaterializer(workspace_id="phase0-backfill", paths=paths)
    first = replay_facts(facts=facts, materializer=materializer, source_key=source_key, batch_size=3)
    resumed = replay_facts(facts=facts, cursor=first.cursor, materializer=materializer, source_key=source_key, batch_size=100)
    assert first.cursor == 3 and not first.complete and all(item.created for item in first.results)
    assert resumed.cursor == 8 and resumed.complete and len(resumed.results) == 5 and all(item.created for item in resumed.results)
    for result, fact in zip((*first.results, *resumed.results), facts, strict=True):
        binding = {key: fact["provenance"][key] for key in ("extraction_card_id", "source_card_id", "evidence_id", "locator")}
        assert result.assertion and result.evaluation and result.audit
        assert result.evaluation["details"]["extraction_binding"] == binding and result.audit["extraction_binding"] == binding
    published_topology = sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*"))
    repeated = replay_facts(facts=facts, materializer=materializer, source_key=source_key, batch_size=100)
    original = (*first.results, *resumed.results)
    assert repeated.complete and all(not item.created for item in repeated.results)
    assert [(item.assertion, item.evaluation, item.audit) for item in repeated.results] == [(item.assertion, item.evaluation, item.audit) for item in original]
    assert sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*")) == published_topology
    isolated = AssertionMaterializer(workspace_id="phase0-isolated", paths=paths)
    isolated_result = replay_facts(facts=facts, materializer=isolated, source_key=source_key, batch_size=100)
    assert all(item.reason == "unpublished_edition" for item in isolated_result.results)
    assert not isolated.root.exists() or not any(isolated.root.rglob("*"))
    assert {str(path.relative_to(fixture_root)): sha256(path.read_bytes()).hexdigest() for path in fixture_root.rglob("*") if path.is_file()} == snapshot


def test_materializes_published_passage(tmp_foundry):
    source_key, edition, facts, passages_by_quote, provenance = _durable_inputs(tmp_foundry)
    fact, extraction_provenance = facts[0], provenance[0]
    passage = passages_by_quote[fact["text"]]
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    result = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance)
    before = sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*"))
    repeated = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance)
    schemas = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    assert result.created and result.assertion and result.evaluation
    assert schemas.validate(result.assertion, "source_assertion").ok
    assert schemas.validate(result.evaluation, "assertion_evaluation").ok
    assert not repeated.created and repeated.assertion["assertion_id"] == result.assertion["assertion_id"] and repeated.evaluation["evaluation_id"] == result.evaluation["evaluation_id"]
    assert sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*")) == before
    assert result.audit["allowed_use"] == RIGHTS and result.audit["access_scope"] == "private"
    assert result.audit["contract_version"] == PROVENANCE["contract"] and result.audit["source_edition_id"] == edition.edition["source_edition_id"] and result.audit["passage_id"] == passage["passage_id"]
    assert not any("canonical_claim" in str(path) for path in materializer.root.rglob("*"))


def test_replay_is_bounded_resumable_and_deterministic():
    passage = {"source_edition_id": "sed_" + "a" * 64, "passage_id": "psg_" + "b" * 64}
    facts = [{"passage": passage, "text": text, "provenance": PROVENANCE} for text in ("One.", "Two.")]
    first = replay_facts(facts=facts, batch_size=1)
    resumed = replay_facts(facts=facts, cursor=first.cursor, batch_size=1)
    repeated = replay_facts(facts=facts, batch_size=2)
    assert first.cursor == 1 and resumed.complete
    assert [r.assertion["assertion_id"] for r in (*first.results, *resumed.results)] == [r.assertion["assertion_id"] for r in repeated.results]


def test_qualifiers_and_extensions_change_assertion_identity(tmp_foundry):
    source_key, _, facts, passages_by_quote, provenance = _durable_inputs(tmp_foundry)
    fact, extraction_provenance = facts[0], provenance[0]
    passage = passages_by_quote[fact["text"]]
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    may = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance, qualifiers={"modality": "may"})
    must = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance, qualifiers={"modality": "must"})
    extension = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance, qualifiers={"modality": "may"}, qualifier_extensions={"custom": "x"})
    assert len({may.assertion["assertion_id"], must.assertion["assertion_id"], extension.assertion["assertion_id"]}) == 3
    assert materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance, qualifiers={"modality": "may"}).assertion["assertion_id"] == may.assertion["assertion_id"]


def test_builder_returns_typed_abstentions():
    passage = {"source_edition_id": "sed_" + "a" * 64, "passage_id": "psg_" + "b" * 64}
    assert materialize_assertion(passage=passage, text="", extraction_provenance=PROVENANCE).reason == "blank"
    assert materialize_assertion(passage=passage, text="Fact", extraction_provenance={**PROVENANCE, "contract": "other"}).reason == "unsupported_contract"
    assert materialize_assertion(passage=passage, text="Fact", extraction_provenance={"contract": "extracted_facts-1to1-v1"}).reason == "missing_extraction_provenance"
    assert materialize_assertion(passage=passage, text="Fact", extraction_provenance={**PROVENANCE, "semantic_only": True}).reason == "semantic_only_abstention"
    assert materialize_assertion(passage={**passage, "ambiguous": True}, text="Fact", extraction_provenance=PROVENANCE).reason == "ambiguous_selector"


def test_durable_binding_failures_do_not_write(tmp_foundry):
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    edition = registry.ingest("paper:1", "Exact fact.", allowed_use=RIGHTS)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    passage = edition.passages[0]
    before = list(materializer.root.rglob("*")) if materializer.root.exists() else []
    assert materializer.materialize(source_key="paper:1", passage={**passage, "passage_id": "psg_" + "c" * 64}, text="Fact", extraction_provenance=PROVENANCE).reason == "unpublished_passage"
    assert materializer.materialize(source_key="paper:1", passage={**passage, "raw_text_sha256": "d" * 64}, text="Fact", extraction_provenance=PROVENANCE).reason == "passage_binding_drift"
    assert materializer.materialize(source_key="other", passage=passage, text="Fact", extraction_provenance=PROVENANCE).reason == "unpublished_edition"
    assert (list(materializer.root.rglob("*")) if materializer.root.exists() else []) == before


def test_atomic_materialization_publish_retries_after_interruption(tmp_foundry):
    source_key, _, facts, passages_by_quote, provenance = _durable_inputs(tmp_foundry)
    fact, extraction_provenance = facts[0], provenance[0]
    passage = passages_by_quote[fact["text"]]
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    with __import__("pytest").raises(RuntimeError, match="publication interruption"):
        materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance, _interrupt_before_publish=True)
    assert not list((materializer.root / "published").glob("*.yaml")) if (materializer.root / "published").exists() else True
    published = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance)
    topology = sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*"))
    repeated = materializer.materialize(source_key=source_key, passage=passage, text=fact["text"], extraction_provenance=extraction_provenance)
    assert published.created and published.assertion and published.evaluation and published.audit
    assert not repeated.created and sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*")) == topology


def test_published_manifest_rejects_path_escape(tmp_foundry):
    source_key, _, facts, passages_by_quote, provenance = _durable_inputs(tmp_foundry)
    fact, extraction_provenance = facts[0], provenance[0]
    passage = passages_by_quote[fact["text"]]
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    created = materializer.materialize(
        source_key=source_key,
        passage=passage,
        text=fact["text"],
        extraction_provenance=extraction_provenance,
    )
    assert created.assertion is not None
    topology = sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*"))
    manifest_path = materializer._published_path(created.assertion["assertion_id"])
    manifest = load_yaml(manifest_path)
    outside = materializer.root.parent / "outside.yaml"
    dump_yaml(
        {
            "assertion": "../../outside.yaml",
            "evaluation": manifest["evaluation"],
            "audit": manifest["audit"],
        },
        manifest_path,
    )
    repeated = materializer.materialize(
        source_key=source_key,
        passage=passage,
        text=fact["text"],
        extraction_provenance=extraction_provenance,
    )
    assert repeated.assertion is None and repeated.evaluation is None and repeated.audit is None
    assert not repeated.created and repeated.reason == "invalid_published_manifest"
    assert not outside.exists()
    assert sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*")) == topology


def test_durable_materialization_rejects_fabricated_fact_or_forged_binding(tmp_foundry):
    source_key, _, facts, passages_by_quote, provenance = _durable_inputs(tmp_foundry)
    fact, extraction_provenance = facts[0], provenance[0]
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    before = []
    for text, forged in (
        ("Fabricated assertion text.", extraction_provenance),
        (fact["text"], {**extraction_provenance, "source_card_id": "src_forged"}),
        (fact["text"], {**extraction_provenance, "evidence_id": "ev_forged"}),
        (fact["text"], {**extraction_provenance, "locator": "para/forged"}),
    ):
        result = materializer.materialize(source_key=source_key, passage=passages_by_quote[fact["text"]], text=text, extraction_provenance=forged)
        assert result.reason == "unverified_extraction_fact"
        assert (list(materializer.root.rglob("*")) if materializer.root.exists() else []) == before


def test_authentic_fact_cannot_bind_to_another_source_passage(tmp_foundry):
    source_a, _, facts_a, passages_a, provenance_a = _durable_inputs(
        tmp_foundry,
        content="Source A verified fact.",
        run_id="rf_run_source_a",
        locator="source-a.txt",
    )
    source_b, _, facts_b, passages_b, provenance_b = _durable_inputs(
        tmp_foundry,
        content="Source B verified fact.",
        run_id="rf_run_source_b",
        locator="source-b.txt",
    )
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    rejected = materializer.materialize(
        source_key=source_b,
        passage=passages_b[facts_b[0]["text"]],
        text=facts_a[0]["text"],
        extraction_provenance=provenance_a[0],
    )
    assert rejected.reason == "source_card_binding_mismatch"
    assert not materializer.root.exists() or not any(materializer.root.rglob("*"))
    accepted = materializer.materialize(
        source_key=source_a,
        passage=passages_a[facts_a[0]["text"]],
        text=facts_a[0]["text"],
        extraction_provenance=provenance_a[0],
    )
    assert accepted.created and accepted.assertion and accepted.evaluation and accepted.audit


def test_published_manifest_rejects_in_root_cross_packet_substitution(tmp_foundry):
    source_key, _, facts, passages_by_quote, provenance = _durable_inputs(tmp_foundry, content="First verified fact.\n\nSecond verified fact.")
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    left = materializer.materialize(source_key=source_key, passage=passages_by_quote[facts[0]["text"]], text=facts[0]["text"], extraction_provenance=provenance[0])
    right = materializer.materialize(source_key=source_key, passage=passages_by_quote[facts[1]["text"]], text=facts[1]["text"], extraction_provenance=provenance[1])
    assert left.assertion and right.assertion
    manifest_path = materializer._published_path(left.assertion["assertion_id"])
    manifest = load_yaml(manifest_path)
    other_manifest = load_yaml(materializer._published_path(right.assertion["assertion_id"]))
    for entry in ("assertion", "evaluation", "audit"):
        dump_yaml({**manifest, entry: other_manifest[entry]}, manifest_path)
        topology = sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*"))
        reloaded = materializer.materialize(source_key=source_key, passage=passages_by_quote[facts[0]["text"]], text=facts[0]["text"], extraction_provenance=provenance[0])
        assert reloaded.reason == "invalid_published_manifest" and reloaded.assertion is None
        assert sorted(path.relative_to(materializer.root) for path in materializer.root.rglob("*")) == topology
        dump_yaml(manifest, manifest_path)
