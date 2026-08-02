"""M1 coverage — ERI legacy ``extraction_status`` backfill (dry-run only).

Plan: docs/project_plans/implementation_plans/enhancements/
eri-legacy-extraction-status-backfill-v1.md

These tests exercise real entry points (``extract_bytes``,
``AssertionRegistry.verify_source_card_binding``) rather than unit shims, per
the plan's Rubric and named risk R3. The "legacy still verifies" case uses
the frozen, hand-authored fixture at tests/fixtures/assertion_ledger/
legacy_edition/ — never a live read of the production ledger.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.backfill_operations.eri_legacy_extraction_status import (
    categorize_edition,
    dry_run_backfill_report,
    recompute_extraction_status,
)
from research_foundry.services.external_research_resolution import (
    _MAX_EXTRACT_CHARS,
    STATUS_FULL_TEXT,
    STATUS_LOCATOR_ONLY,
    STATUS_PARTIAL,
    extract_bytes,
)
from research_foundry.yamlio import dump_yaml, load_yaml

LEGACY_FIXTURE = Path(__file__).parents[1] / "fixtures" / "assertion_ledger" / "legacy_edition"
# Must match the workspace_id used in test_assertion_registry.py's own
# `test_legacy_edition_still_verifies_unbackfilled` — the fixture's
# source_id is pinned to this exact workspace_id/source_key hash pair
# (AssertionRegistry._source_id = sha256(f"{sha256(workspace_id)}:{source_key}")).
LEGACY_WORKSPACE_ID = "legacy-fixture-workspace"
LEGACY_SOURCE_KEY = "paper:legacy-fixture"


def _tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _source_card(source_card_id: str, url: str) -> dict:
    return {
        "source_card_id": source_card_id,
        "sensitivity": "personal",
        "source": {"locator": {"url": url, "file_path": None}},
        "usage": {"sensitivity": "personal", "allowed_for_work_output": True},
        "extracted_points": [],
    }


def _plant_edition(
    registry: AssertionRegistry,
    source_key: str,
    edition: dict,
    provenance: dict,
    content: bytes,
) -> tuple[str, str]:
    source_id = registry._source_id(source_key)
    edition_id = edition["source_edition_id"]
    edition_dir = registry.root / "sources" / source_id / "editions"
    edition_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(edition, edition_dir / f"{edition_id}.yaml")
    (edition_dir / edition_id).mkdir(parents=True, exist_ok=True)
    (edition_dir / edition_id / "content.bin").write_bytes(content)
    dump_yaml(provenance, edition_dir / edition_id / "provenance.yaml")
    return source_id, edition_id


# ---------------------------------------------------------------------------
# recompute_extraction_status — pure function, boundary cases against the
# REAL extract_bytes classification (never re-derive the threshold by hand).
# ---------------------------------------------------------------------------


def test_recompute_matches_extract_bytes_full_text() -> None:
    text = "a" * 500
    real = extract_bytes(text.encode("utf-8"), "text/plain")
    assert real.status == STATUS_FULL_TEXT
    assert recompute_extraction_status(text) == STATUS_FULL_TEXT == real.status


def test_recompute_diverges_from_extract_bytes_at_exact_boundary_fail_closed() -> None:
    """Deliberate divergence from extract_bytes at exactly _MAX_EXTRACT_CHARS.

    NOT an off-by-one bug — do not "fix" this back into agreement with
    extract_bytes. extract_bytes's forward pass, given the FULL original
    document, correctly returns full_text when the document is exactly
    _MAX_EXTRACT_CHARS chars (its check is strict `len(text) >
    _MAX_EXTRACT_CHARS`). But extract_bytes ALSO produces a stored text of
    exactly _MAX_EXTRACT_CHARS chars when the ORIGINAL document was longer
    and got truncated (`text[:_MAX_EXTRACT_CHARS]` at
    external_research_resolution.py:388) -- those two histories are
    byte-identical on disk. recompute_extraction_status only ever sees the
    stored text, so it cannot tell them apart and must fail closed: treat
    exactly-at-limit as *not provably untruncated* -> partial. This was
    confirmed as the real case on the live workspace's own boundary edition
    (OQ-1): its stored text, at exactly 100,000 chars, ends mid-word
    ("... it is also imp"), proving it is a truncated document, not one that
    coincidentally ends at the limit.
    """

    text = "a" * _MAX_EXTRACT_CHARS
    real = extract_bytes(text.encode("utf-8"), "text/plain")
    assert real.status == STATUS_FULL_TEXT, "extract_bytes's forward behavior is unchanged"
    assert recompute_extraction_status(text) == STATUS_PARTIAL, (
        "recompute must fail closed at the boundary, diverging from extract_bytes on purpose"
    )


def test_recompute_matches_extract_bytes_one_over_boundary() -> None:
    text = "a" * (_MAX_EXTRACT_CHARS + 1)
    real = extract_bytes(text.encode("utf-8"), "text/plain")
    assert real.status == STATUS_PARTIAL
    # extract_bytes truncates its returned text to the max; recompute must be
    # fed the FULL decoded text (as stored in the ledger) to reproduce the
    # same classification from length alone.
    assert recompute_extraction_status(text) == STATUS_PARTIAL == real.status


def test_recompute_empty_text_is_locator_only() -> None:
    assert recompute_extraction_status("") == STATUS_LOCATOR_ONLY
    assert recompute_extraction_status(None) == STATUS_LOCATOR_ONLY


# ---------------------------------------------------------------------------
# categorize_edition — eligibility gated ONLY on allowed_use.basis (risk R1).
# ---------------------------------------------------------------------------


def test_categorize_eligible_requires_producer_declared_basis() -> None:
    record = {
        "metadata_extensions": {
            "allowed_use": {"basis": "producer_declared_access_status", "access_status": "open-access"},
        }
    }
    assert categorize_edition(record) == "eligible"


def test_categorize_already_set_even_with_eligible_basis() -> None:
    record = {
        "metadata_extensions": {
            "extraction_status": "full_text",
            "allowed_use": {"basis": "producer_declared_access_status", "access_status": "open-access"},
        }
    }
    assert categorize_edition(record) == "already_set"


def test_categorize_ineligible_wrong_basis_regardless_of_content_shape() -> None:
    """R1 regression: a SHORT, full-text-looking edition with the wrong basis
    must still be ineligible — content shape never overrides the basis gate.
    """

    record = {
        "metadata_extensions": {
            "allowed_use": {"sensitivity": "personal", "allowed_for_work_output": True},
        }
    }
    assert categorize_edition(record) == "ineligible"


def test_categorize_ineligible_missing_basis_key() -> None:
    record = {"metadata_extensions": {"allowed_use": {}}}
    assert categorize_edition(record) == "ineligible"


def test_categorize_raises_on_missing_metadata_extensions() -> None:
    with pytest.raises(ValueError):
        categorize_edition({"source_id": "src_x"})


# ---------------------------------------------------------------------------
# Frozen legacy fixture: still verifies unbackfilled, still ineligible, and
# the dry run leaves it (and everything else) byte-identical.
# ---------------------------------------------------------------------------


def test_legacy_fixture_is_ineligible_and_still_verifies(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id=LEGACY_WORKSPACE_ID, paths=tmp_foundry)
    edition = load_yaml(LEGACY_FIXTURE / "edition.yaml")
    provenance = load_yaml(LEGACY_FIXTURE / "provenance.yaml")
    assert "extraction_status" not in edition["metadata_extensions"]

    # Categorization: no "basis" key in this fixture's allowed_use at all ->
    # ineligible, never derived from the fact its content is short/full-text.
    assert categorize_edition(edition) == "ineligible"

    _plant_edition(
        registry,
        LEGACY_SOURCE_KEY,
        edition,
        provenance,
        (LEGACY_FIXTURE / "content.bin").read_bytes(),
    )
    source_card = _source_card(LEGACY_SOURCE_KEY, "https://example.test/legacy-fixture")
    before = _tree(registry.root)
    registry.verify_source_card_binding(LEGACY_SOURCE_KEY, edition, source_card)
    assert _tree(registry.root) == before, "verification must not write anything"


def test_dry_run_over_planted_legacy_fixture_reports_it_ineligible_and_mutates_nothing(
    tmp_foundry,
) -> None:
    registry = AssertionRegistry(workspace_id=LEGACY_WORKSPACE_ID, paths=tmp_foundry)
    edition = load_yaml(LEGACY_FIXTURE / "edition.yaml")
    provenance = load_yaml(LEGACY_FIXTURE / "provenance.yaml")
    _plant_edition(
        registry,
        LEGACY_SOURCE_KEY,
        edition,
        provenance,
        (LEGACY_FIXTURE / "content.bin").read_bytes(),
    )

    before = _tree(registry.root)
    receipt = dry_run_backfill_report(registry.root)
    after = _tree(registry.root)

    assert after == before, "dry run must never mutate the workspace"
    assert receipt["authoritative_data_mutated"] is False
    assert receipt["counts"]["total_editions"] == 1
    assert receipt["counts"]["eligible"] == 0
    assert receipt["counts"]["ineligible"] == 1
    assert receipt["counts"]["already_set"] == 0
    assert receipt["eligible_editions"] == []


# ---------------------------------------------------------------------------
# End-to-end dry run over a small synthetic workspace with one of each
# category, proving the receipt counts and per-edition detail are correct
# and that nothing is written (R-readonly, asserted in code by
# dry_run_backfill_report's own before/after fingerprint check).
# ---------------------------------------------------------------------------


def _plant_synthetic_edition(
    registry: AssertionRegistry,
    source_key: str,
    *,
    content: bytes,
    allowed_use: dict,
    extraction_status: str | None,
) -> None:
    source_id = registry._source_id(source_key)
    content_sha = __import__("hashlib").sha256(content).hexdigest()
    edition_id = f"sed_{content_sha}"
    extensions = {
        "raw_content_sha256": content_sha,
        "normalized_content_sha256": content_sha,
        "allowed_use": allowed_use,
    }
    if extraction_status is not None:
        extensions["extraction_status"] = extraction_status
    edition = {
        "schema_version": "1.0",
        "type": "source_edition",
        "source_edition_id": edition_id,
        "content_sha256": content_sha,
        "source_id": source_id,
        "media_type": "text/plain",
        "captured_at": "2026-07-29T00:00:00+00:00",
        "retrieval_locator": {"url": f"https://example.test/{source_key}", "file_path": None},
        "predecessor_edition_id": None,
        "access_scope": "personal",
        "metadata_extensions": extensions,
    }
    provenance_binding = {
        "source_id": source_id,
        "source_edition_id": edition_id,
        "content_sha256": content_sha,
        "media_type": "text/plain",
        "access_scope": "personal",
        "retrieval_locator": {"url": f"https://example.test/{source_key}", "file_path": None},
        "allowed_use": allowed_use,
        "raw_content_sha256": content_sha,
        "normalized_content_sha256": content_sha,
    }
    if extraction_status is not None:
        provenance_binding["extraction_status"] = extraction_status
    from research_foundry.services.assertion_registry import _canonical_digest

    provenance = {
        "schema_version": "1.0",
        "type": "source_edition_provenance",
        "source_id": source_id,
        "source_edition_id": edition_id,
        "content_sha256": content_sha,
        "edition_binding": provenance_binding,
        "edition_binding_sha256": _canonical_digest(provenance_binding),
        "source_card_snapshot": None,
    }
    edition_dir = registry.root / "sources" / source_id / "editions"
    edition_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(edition, edition_dir / f"{edition_id}.yaml")
    (edition_dir / edition_id).mkdir(parents=True, exist_ok=True)
    (edition_dir / edition_id / "content.bin").write_bytes(content)
    dump_yaml(provenance, edition_dir / edition_id / "provenance.yaml")


def test_dry_run_end_to_end_categorizes_and_recomputes_correctly(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="eri-backfill-synthetic-workspace", paths=tmp_foundry)

    # eligible + full_text
    _plant_synthetic_edition(
        registry,
        "eligible-full-text",
        content=b"short honest full text",
        allowed_use={"basis": "producer_declared_access_status", "access_status": "open-access"},
        extraction_status=None,
    )
    # eligible + partial (decoded text exceeds _MAX_EXTRACT_CHARS)
    _plant_synthetic_edition(
        registry,
        "eligible-partial",
        content=("b" * (_MAX_EXTRACT_CHARS + 10)).encode("utf-8"),
        allowed_use={"basis": "producer_declared_access_status", "access_status": "open-access"},
        extraction_status=None,
    )
    # ineligible (rollout quote-join basis)
    _plant_synthetic_edition(
        registry,
        "ineligible-rollout",
        content=b"a quote-join with no honest full text",
        allowed_use={"sensitivity": "personal", "allowed_for_work_output": True},
        extraction_status=None,
    )
    # already_set (must not be re-derived)
    _plant_synthetic_edition(
        registry,
        "already-set",
        content=b"already has a status",
        allowed_use={"basis": "producer_declared_access_status", "access_status": "open-access"},
        extraction_status="full_text",
    )

    before = _tree(registry.root)
    receipt = dry_run_backfill_report(registry.root)
    after = _tree(registry.root)

    assert after == before, "dry run must never mutate the workspace"
    assert receipt["authoritative_data_mutated"] is False
    counts = receipt["counts"]
    assert counts["total_editions"] == 4
    assert counts["eligible"] == 2
    assert counts["ineligible"] == 1
    assert counts["already_set"] == 1
    assert counts["eligible_full_text"] == 1
    assert counts["eligible_partial"] == 1
    assert counts["eligible_locator_only"] == 0

    statuses = {item["source_edition_id"]: item["recomputed_extraction_status"] for item in receipt["eligible_editions"]}
    assert set(statuses.values()) == {STATUS_FULL_TEXT, STATUS_PARTIAL}
