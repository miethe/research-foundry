"""P2 registry coverage: immutable editions, selectors, drift, and workspace isolation."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

RIGHTS = {"sensitivity": "personal", "allowed_for_work_output": True}
FIXTURES = Path(__file__).parents[1] / "fixtures" / "assertion_ledger" / "p2_formats"


def _tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _stable_tree(root: Path) -> dict[str, str]:
    """Compare deterministic payload/topology without wall-clock YAML fields."""

    return {
        str(path.relative_to(root)): re.sub(r"(captured_at|updated_at): .*", r"\\1: <timestamp>", path.read_text(encoding="utf-8"))
        for path in sorted(root.rglob("*.yaml"))
    }


def test_idempotent_edition_and_schema_valid_passage(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    first = registry.ingest("paper:1", "Exact quote.\n\nSecond paragraph.", passages=["Exact quote.", "Second paragraph."], allowed_use=RIGHTS)
    again = registry.ingest("paper:1", "Exact quote.\n\nSecond paragraph.", passages=["Exact quote.", "Second paragraph."], allowed_use=RIGHTS)

    schemas = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    assert first.created is True and again.created is False
    assert first.edition == again.edition
    assert len(first.passages) == 2
    assert all(schemas.validate(passage, "passage").ok for passage in first.passages)


def test_fabricated_passage_is_rejected_before_registry_publication(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)

    result = registry.ingest(
        "paper:1",
        "true edition bytes",
        passages=["fabricated passage"],
        allowed_use=RIGHTS,
    )

    assert result.reusable is False
    assert result.reason == "passage_not_in_edition"
    assert result.edition is None and result.passages == ()
    assert not registry.root.exists()


def test_changed_content_creates_predecessor_and_drift_is_not_reusable(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    first = registry.ingest("paper:1", "Original text", allowed_use=RIGHTS)
    changed = registry.ingest("paper:1", "Changed text", allowed_use=RIGHTS)

    assert first.edition is not None
    assert changed.edition is not None
    assert changed.created is True
    assert changed.edition["predecessor_edition_id"] == first.edition["source_edition_id"]
    drift = registry.resolve_passage("paper:1", first.edition["source_edition_id"], first.passages[0]["passage_id"], "Changed text")
    assert drift.reusable is False and drift.reason == "drift"


def test_workspace_paths_are_isolated_and_unsupported_content_is_typed(tmp_foundry) -> None:
    left = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    right = AssertionRegistry(workspace_id="workspace-b", paths=tmp_foundry)
    left_result = left.ingest("paper:1", "Private text", allowed_use=RIGHTS)
    right_result = right.ingest("paper:1", "Private text", allowed_use=RIGHTS)
    missing = left.ingest("binary:1", None, media_type="application/octet-stream")

    assert left.root != right.root and left_result.source_id != right_result.source_id
    assert missing.reusable is False and missing.reason == "unsupported_or_missing_content"


def test_multiformat_identity_is_deterministic_in_three_input_orders(tmp_path) -> None:
    formats = [("text/plain", "fixture.txt"), ("text/html", "fixture.html"), ("application/pdf", "fixture.pdf"), ("text/ocr", "fixture.ocr")]
    expected: dict[str, tuple[str, str]] | None = None
    expected_tree: dict[str, str] | None = None
    for number, order in enumerate((formats, tuple(reversed(formats)), (formats[1], formats[3], formats[0], formats[2]))):
        paths = FoundryPaths(tmp_path / f"order-{number}")
        registry = AssertionRegistry(workspace_id="workspace-multiformat", paths=paths)
        observed: dict[str, tuple[str, str]] = {}
        for media_type, filename in order:
            fixture = FIXTURES / filename
            raw = fixture.read_bytes() if media_type == "application/pdf" else fixture.read_text(encoding="utf-8")
            result = registry.ingest(filename, raw, media_type=media_type, allowed_use=RIGHTS)
            assert result.edition is not None
            observed[filename] = (result.edition["source_edition_id"], result.passages[0]["passage_id"])
            drift = registry.resolve_passage(filename, result.edition["source_edition_id"], result.passages[0]["passage_id"], raw + b" drift" if isinstance(raw, bytes) else raw + " drift")
            assert drift.reusable is False and drift.reason == "drift"
        tree = _stable_tree(paths.root)
        if expected is None:
            expected = observed
            expected_tree = tree
        else:
            assert observed == expected
            assert tree == expected_tree


def test_rights_and_ambiguous_selector_are_non_reusable_without_mutation(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    valid = registry.ingest("paper:1", "Stable text", allowed_use=RIGHTS)
    before = _tree(registry.root)
    missing = registry.ingest("paper:2", "No rights")
    ambiguous = registry.ingest("paper:1", "Changed", passages=["same", " same "], allowed_use=RIGHTS)

    assert missing.reason == "missing_rights_metadata"
    assert ambiguous.reason == "ambiguous_selector"
    assert _tree(registry.root) == before
    assert registry.ingest("paper:1", "Stable text", allowed_use=RIGHTS).edition == valid.edition


def test_interrupted_write_keeps_prior_manifest_complete(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    original = registry.ingest("paper:1", "Original", allowed_use=RIGHTS)
    with pytest.raises(RuntimeError, match="atomic-write interruption"):
        registry.ingest("paper:1", "Changed", allowed_use=RIGHTS, _interrupt_after_edition_write=True)

    restored = registry.ingest("paper:1", "Original", allowed_use=RIGHTS)
    recovered = registry.ingest("paper:1", "Changed", allowed_use=RIGHTS)
    assert original.edition is not None
    assert recovered.edition is not None
    assert restored.edition == original.edition
    assert recovered.created is True and len(recovered.passages) == 1
    assert registry.resolve_passage("paper:1", recovered.edition["source_edition_id"], recovered.passages[0]["passage_id"], "Changed").reusable


def test_interrupted_multi_passage_union_keeps_published_generation_complete(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    base = registry.ingest("paper:1", "One. Two.", allowed_use=RIGHTS)
    assert base.edition is not None
    with pytest.raises(RuntimeError, match="generation publication interruption"):
        registry.ingest(
            "paper:1", "One. Two.", allowed_use=RIGHTS,
            passages=["One.", "Two."], _interrupt_before_generation_publish=True,
        )

    observed = registry.list_passages("paper:1", base.edition["source_edition_id"])
    assert len(observed) in {1, 3}
    assert len(observed) == 1
    retried = registry.ingest("paper:1", "One. Two.", allowed_use=RIGHTS, passages=["One.", "Two."])
    assert len(retried.passages) == 3
    assert len({item["passage_id"] for item in retried.passages}) == 3


def test_source_card_registry_seam_is_opt_in_and_preserves_card_identity(tmp_foundry) -> None:
    baseline_run, registry_run = "rf_run_p2_baseline", "rf_run_p2_registry"
    tmp_foundry.run_paths(baseline_run).ensure_scaffold()
    tmp_foundry.run_paths(registry_run).ensure_scaffold()
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    baseline = ingest_source("notes.txt", run_id=baseline_run, content="Registry seam evidence.", paths=tmp_foundry)
    result = ingest_source(
        "notes.txt", run_id=registry_run, content="Registry seam evidence.", paths=tmp_foundry,
        assertion_registry_workspace_id="workspace-a",
    )

    assert result.source_card_id == baseline.source_card_id
    assert list((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/source.yaml"))


def test_source_card_first_ingest_accepts_later_granular_passages(tmp_foundry) -> None:
    run_id = "rf_run_p2_granular"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    content = "First granular passage.\n\nSecond granular passage."
    source = ingest_source(
        "granular.txt", run_id=run_id, content=content, paths=tmp_foundry,
        assertion_registry_workspace_id="workspace-a",
    )
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    granular = registry.ingest(
        source.source_card_id, content, allowed_use=RIGHTS,
        passages=["First granular passage.", "Second granular passage."],
    )
    repeated = registry.ingest(
        source.source_card_id, content, allowed_use=RIGHTS,
        passages=["First granular passage.", "Second granular passage."],
    )

    assert granular.edition == repeated.edition
    assert len(granular.passages) == 3
    assert len({passage["passage_id"] for passage in granular.passages}) == 3
    assert granular.passages == repeated.passages
