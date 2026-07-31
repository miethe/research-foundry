"""P2 registry coverage: immutable editions, selectors, drift, and workspace isolation."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.assertion_registry import (
    AssertionRegistry,
    RegistryIntegrityError,
    _canonical_digest,
)
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

RIGHTS = {"sensitivity": "personal", "allowed_for_work_output": True}
FIXTURES = Path(__file__).parents[1] / "fixtures" / "assertion_ledger" / "p2_formats"


def _edition_manifest_path(registry: AssertionRegistry, source_id: str, edition_id: str) -> Path:
    return registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"


def _provenance_path(registry: AssertionRegistry, source_id: str, edition_id: str) -> Path:
    return registry.root / "sources" / source_id / "editions" / edition_id / "provenance.yaml"


def _content_path(registry: AssertionRegistry, source_id: str, edition_id: str) -> Path:
    return registry.root / "sources" / source_id / "editions" / edition_id / "content.bin"


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
    # ingest_source() itself now segments the edition by each source-card
    # point's verbatim quote ("First granular passage.", "Second granular
    # passage."), so a later, richer ingest additively binds a passage
    # ingest_source() did not already produce -- here, the whole-document
    # span -- without conflicting with the existing edition.
    granular = registry.ingest(
        source.source_card_id, content, allowed_use=RIGHTS,
        passages=["First granular passage.", "Second granular passage.", content],
    )
    repeated = registry.ingest(
        source.source_card_id, content, allowed_use=RIGHTS,
        passages=["First granular passage.", "Second granular passage.", content],
    )

    assert granular.edition == repeated.edition
    assert len(granular.passages) == 3
    assert len({passage["passage_id"] for passage in granular.passages}) == 3
    assert granular.passages == repeated.passages


def _source_card(source_card_id: str, url: str) -> dict:
    return {
        "source_card_id": source_card_id,
        "source": {"locator": {"url": url, "file_path": None}},
        "usage": RIGHTS,
        "sensitivity": "personal",
        "extracted_points": [],
    }


def test_extraction_status_round_trips_and_is_covered_by_binding(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    source_card = _source_card("paper:1", "https://example.test")
    result = registry.ingest(
        "paper:1",
        "Full text content.",
        allowed_use=RIGHTS,
        extraction_status="full_text",
        source_card_snapshot=registry.source_card_snapshot("paper:1", source_card),
    )

    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]
    assert result.edition["metadata_extensions"]["extraction_status"] == "full_text"
    assert registry.get_extraction_status("paper:1", edition_id) == "full_text"

    provenance = load_yaml(_provenance_path(registry, result.source_id, edition_id))
    assert provenance["edition_binding"]["extraction_status"] == "full_text"
    assert provenance["edition_binding_sha256"] == _canonical_digest(provenance["edition_binding"])

    # verify_source_card_binding still succeeds with a status-bearing edition.
    registry.verify_source_card_binding("paper:1", result.edition, source_card)


def test_ingest_without_status_records_nothing(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    source_card = _source_card("paper:1", "https://example.test")
    result = registry.ingest(
        "paper:1",
        "No status supplied.",
        allowed_use=RIGHTS,
        source_card_snapshot=registry.source_card_snapshot("paper:1", source_card),
    )

    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]
    assert "extraction_status" not in result.edition["metadata_extensions"]
    assert registry.get_extraction_status("paper:1", edition_id) is None

    provenance = load_yaml(_provenance_path(registry, result.source_id, edition_id))
    assert "extraction_status" not in provenance["edition_binding"]

    # A no-status edition's binding is exactly the shape a pre-existing (legacy)
    # edition already on disk has -- proof that this decision needs no backfill.
    registry.verify_source_card_binding("paper:1", result.edition, source_card)


def test_out_of_vocabulary_status_rejected_on_write(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    result = registry.ingest(
        "paper:1", "Some content.", allowed_use=RIGHTS, extraction_status="bogus_status"
    )

    assert result.reusable is False
    assert result.reason == "invalid_extraction_status"
    assert result.edition is None and result.passages == ()
    assert not registry.root.exists()


def test_out_of_vocabulary_status_rejected_on_read(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    result = registry.ingest(
        "paper:1", "Readable content.", allowed_use=RIGHTS, extraction_status="full_text"
    )
    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]

    manifest_path = _edition_manifest_path(registry, result.source_id, edition_id)
    manifest = load_yaml(manifest_path)
    manifest["metadata_extensions"]["extraction_status"] = "not_a_real_status"
    dump_yaml(manifest, manifest_path)

    with pytest.raises(RegistryIntegrityError, match="tri-state"):
        registry.get_extraction_status("paper:1", edition_id)


LEGACY_FIXTURE = Path(__file__).parents[1] / "fixtures" / "assertion_ledger" / "legacy_edition"
LEGACY_WORKSPACE_ID = "legacy-fixture-workspace"
LEGACY_SOURCE_KEY = "paper:legacy-fixture"


def test_legacy_edition_still_verifies_unbackfilled(tmp_foundry) -> None:
    """Sharpest named risk: conditional inclusion must not disturb legacy editions.

    This is a FROZEN, checked-in fixture (tests/fixtures/assertion_ledger/legacy_edition/)
    hand-authored to look exactly like a pre-existing on-disk edition written before
    ``extraction_status`` existed -- it is never produced by calling the (changed)
    ``ingest()``, so an implementation that started writing ``extraction_status``
    unconditionally (even as ``null``) would change what ``_edition_binding``
    recomputes and this test would correctly fail, instead of vacuously passing.
    """

    registry = AssertionRegistry(workspace_id=LEGACY_WORKSPACE_ID, paths=tmp_foundry)
    source_id = registry._source_id(LEGACY_SOURCE_KEY)
    edition = load_yaml(LEGACY_FIXTURE / "edition.yaml")
    provenance = load_yaml(LEGACY_FIXTURE / "provenance.yaml")
    assert edition["source_id"] == source_id, "fixture source_id must match this workspace/source_key pair"
    assert "extraction_status" not in edition["metadata_extensions"]
    assert "extraction_status" not in provenance["edition_binding"]

    edition_dir = registry.root / "sources" / source_id / "editions"
    edition_id = edition["source_edition_id"]
    edition_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(edition, edition_dir / f"{edition_id}.yaml")
    (edition_dir / edition_id).mkdir(parents=True, exist_ok=True)
    shutil.copy(LEGACY_FIXTURE / "content.bin", edition_dir / edition_id / "content.bin")
    dump_yaml(provenance, edition_dir / edition_id / "provenance.yaml")

    source_card = _source_card("paper:legacy-fixture", "https://example.test/legacy-fixture")
    before = _tree(registry.root)
    registry.verify_source_card_binding(LEGACY_SOURCE_KEY, edition, source_card)
    # No write occurred as a side effect of verification.
    assert _tree(registry.root) == before


def test_tampered_persisted_extraction_status_raises_integrity_error(tmp_foundry) -> None:
    """Tampering the persisted EDITION's status must be caught by the status guard
    itself (``_extraction_status`` inside ``_edition_binding``), not merely by the
    generic stored-vs-recomputed binding mismatch every other tamper already trips.

    Both the edition's ``metadata_extensions.extraction_status`` AND provenance's
    ``edition_binding.extraction_status``/``edition_binding_sha256`` are tampered
    to the SAME out-of-vocabulary value, so the two records stay mutually
    consistent -- if the tri-state guard were removed, this would NOT raise via
    the generic stored-vs-recomputed mismatch (both sides would agree), proving
    the raise below can only come from the guard itself. Confirmed by
    mutation-verify (see implementation-notes.md).
    """

    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    source_card = _source_card("paper:1", "https://example.test")
    result = registry.ingest(
        "paper:1",
        "Tamper target.",
        allowed_use=RIGHTS,
        extraction_status="locator_only",
        source_card_snapshot=registry.source_card_snapshot("paper:1", source_card),
    )
    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]

    manifest_path = _edition_manifest_path(registry, result.source_id, edition_id)
    manifest = load_yaml(manifest_path)
    manifest["metadata_extensions"]["extraction_status"] = "an_invalid_status_value"
    dump_yaml(manifest, manifest_path)

    provenance_path = _provenance_path(registry, result.source_id, edition_id)
    provenance = load_yaml(provenance_path)
    provenance["edition_binding"]["extraction_status"] = "an_invalid_status_value"
    provenance["edition_binding_sha256"] = _canonical_digest(provenance["edition_binding"])
    dump_yaml(provenance, provenance_path)

    with pytest.raises(RegistryIntegrityError, match="tri-state"):
        registry.verify_source_card_binding("paper:1", result.edition, source_card)


def test_tampered_provenance_extraction_status_mismatch_still_raises(tmp_foundry) -> None:
    """A plausible-looking (valid tri-state) but WRONG persisted provenance status
    is still caught -- by the general stored-vs-recomputed binding mismatch, since
    the edition's real recorded status disagrees with what provenance now claims.
    """

    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    source_card = _source_card("paper:1", "https://example.test")
    result = registry.ingest(
        "paper:1",
        "Tamper target.",
        allowed_use=RIGHTS,
        extraction_status="locator_only",
        source_card_snapshot=registry.source_card_snapshot("paper:1", source_card),
    )
    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]

    provenance_path = _provenance_path(registry, result.source_id, edition_id)
    provenance = load_yaml(provenance_path)
    provenance["edition_binding"]["extraction_status"] = "full_text"
    dump_yaml(provenance, provenance_path)

    with pytest.raises(RegistryIntegrityError):
        registry.verify_source_card_binding("paper:1", result.edition, source_card)


def test_sibling_metadata_extensions_cannot_bypass_status_validation(tmp_foundry) -> None:
    """FIX-1 regression: an invalid status smuggled in via metadata_extensions
    (instead of the explicit extraction_status parameter) must be rejected the
    same way -- a typed non-reusable result, not an uncaught RegistryIntegrityError
    escaping out of _provenance_record for a caller that only expects
    RegistryImportResult back from a public ingest() call.
    """

    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    result = registry.ingest(
        "paper:1",
        "Sibling bypass attempt.",
        allowed_use=RIGHTS,
        metadata_extensions={"extraction_status": "bogus"},
    )

    assert result.reusable is False
    assert result.reason == "invalid_extraction_status"
    assert result.edition is None and result.passages == ()
    assert not registry.root.exists()


def test_unhashable_persisted_status_raises_integrity_error_not_typeerror(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    result = registry.ingest(
        "paper:1", "Unhashable status target.", allowed_use=RIGHTS, extraction_status="full_text"
    )
    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]

    manifest_path = _edition_manifest_path(registry, result.source_id, edition_id)
    manifest = load_yaml(manifest_path)
    manifest["metadata_extensions"]["extraction_status"] = ["not", "a", "string"]
    dump_yaml(manifest, manifest_path)

    with pytest.raises(RegistryIntegrityError, match="tri-state"):
        registry.get_extraction_status("paper:1", edition_id)


def test_ingest_source_unrecognized_override_records_no_status_in_registry(tmp_foundry) -> None:
    """FIX-3 regression: an unrecognized ingest_source() override must not reach the
    registry at all. ingest_source()'s existing front-matter fail-open behavior
    (unchanged, still full_text there) must not leak the guessed derived value into
    edition_binding_sha256.
    """

    run_id = "rf_run_p2_bad_override"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    result = ingest_source(
        "bad-override.txt",
        run_id=run_id,
        content="Some content.",
        extraction_status="not_a_real_status",
        paths=tmp_foundry,
        assertion_registry_workspace_id="workspace-a",
    )
    # Front-matter fail-open is unchanged and out of scope: still full_text.
    assert result.extraction_status == "full_text"

    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    edition_id = registry.ingest(
        result.source_card_id, "Some content.", allowed_use=RIGHTS
    ).edition["source_edition_id"]
    assert registry.get_extraction_status(result.source_card_id, edition_id) is None


def test_load_edition_content_raises_on_corrupted_content(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="workspace-a", paths=tmp_foundry)
    result = registry.ingest("paper:1", "Original bytes.", allowed_use=RIGHTS)
    assert result.edition is not None
    edition_id = result.edition["source_edition_id"]

    assert registry.load_edition_content("paper:1", edition_id) == b"Original bytes."

    content_path = _content_path(registry, result.source_id, edition_id)
    content_path.write_bytes(b"corrupted bytes")

    with pytest.raises(RegistryIntegrityError):
        registry.load_edition_content("paper:1", edition_id)
