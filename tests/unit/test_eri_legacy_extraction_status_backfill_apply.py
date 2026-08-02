"""M2 coverage — ERI legacy ``extraction_status`` backfill apply + rollback.

Plan: docs/project_plans/implementation_plans/enhancements/
eri-legacy-extraction-status-backfill-v1.md

Rubric/R3: these tests exercise real entry points --
``AssertionRegistry.ingest`` to plant fixtures the same way production code
would, and ``AssertionRegistry.verify_source_card_binding``/``_load_edition``
(the real binding-verification chain) to prove the post-apply pair verifies
-- never a hand-rolled binding recompute standing in for the registry's own.

Hardening round (2026-08-02): a security gate REJECTED the first M2 cut on
nine failure-path findings plus B1/B2/N1/N2/N5. This file covers both the
original nine (R5 partial-apply, self-repair, rollback, idempotent resume,
untouched-others, content.bin-never-written) AND the hardening findings:
B2 (scope pinning, fails closed on drift), B1 (advisory lock + diverged-bytes
repair refusal), item 3 (traversal rejection), item 4 (pre-existing failure
skip-not-overwrite), item 1 (write-ahead journal survives a mid-loop crash),
item 2/6 (rollback's own strict preview-by-default gate), N2 (repair failure
never masks the original exception).

Second hardening round (2026-08-02, design change): B2 was found NOT closed
-- the pinned-scope check took a snapshot but the mutate loop re-globbed
fresh afterward, so an edition appearing mid-flight (after the check, before
the loop reached it) got silently mutated. ``test_apply_iterates_the_pinned_set...``
below exercises exactly that gap and is written to fail against the
PRE-restructure code (verified separately, not in this file, against a
snapshot of the prior module revision). Also covers NB-1/NB-2 (docstring +
re-check-immediately-adjacent-to-write), the lock file's 0600 mode and
unlink-on-no-mutation, and ``receipt_from_journal``'s torn-line tolerance
(later narrowed, see below).

Third hardening round (2026-08-02, RE-SCOPE, not a fourth fix): the SAME
defect class (approval-scope drift) surfaced a third time, one layer over --
the second round constrained the eligible write loop but left the sibling
``already_set`` repair loop (added in round 1's item 5) completely
unconstrained. Per doctrine, a third failure on one class means removing the
feature, not adding a guard. **The entire already_set repair-on-apply path
is DELETED**: ``_repair_broken_already_set``, the already_set mutation
loop, and the ``repaired`` counter/``repairs`` list no longer exist anywhere
in the module or this file (the ``test_half_rolled_back_already_set_is_repaired_not_skipped_item5``
test that covered it is DELETED, replaced by
``test_already_set_is_read_only_in_apply_even_when_binding_is_broken`` and
``test_apply_never_opens_already_set_files_at_all``, which assert the
OPPOSITE: already_set is never opened or written). Also fixed this round:
the apply loop now validates every id with ``_validate_entry_ids_and_paths``
(previously used only on the rollback side) before deriving its path, a
missing file at write time is a clean skip-and-report
(``missing_at_write_time``) instead of an uncaught ``FileNotFoundError``,
and ``receipt_from_journal``'s torn-line tolerance was narrowed to the
single TRAILING line only -- a malformed line anywhere else now raises.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

from research_foundry.services.assertion_registry import AssertionRegistry, RegistryIntegrityError
from research_foundry.services.backfill_operations import eri_legacy_extraction_status as m
from research_foundry.services.external_research_resolution import (
    _MAX_EXTRACT_CHARS,
    STATUS_FULL_TEXT,
    STATUS_PARTIAL,
)
from research_foundry.yamlio import dump_yaml, load_yaml

ELIGIBLE_ALLOWED_USE = {"basis": "producer_declared_access_status", "access_status": "open-access"}
INELIGIBLE_ALLOWED_USE = {"sensitivity": "personal", "allowed_for_work_output": True}


def _tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _ledger_tree(root: Path) -> dict[str, bytes]:
    """Same as ``_tree`` but scoped to ``sources/`` -- the actual ledger
    records (editions/provenance/content). ``backfill_operations/`` holds
    OUR OWN audit trail (the advisory lock file, write-ahead journals,
    receipts) -- it is expected to accumulate across apply/rollback calls and
    is deliberately out of scope for "did the ledger DATA change" assertions.
    """

    return {key: value for key, value in _tree(root).items() if key.startswith("sources/")}


def _pin_and_apply(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Convenience for tests that don't care about exercising pinning itself:
    preview to get the receipt Mode-D would approve, then apply pinned to it."""

    preview = m.apply_backfill(root, apply=False)
    return m.apply_backfill(root, apply=True, pinned_receipt=preview, **kwargs)


def _source_card(source_card_id: str, url: str) -> dict[str, Any]:
    return {
        "source_card_id": source_card_id,
        "sensitivity": "personal",
        "source": {"locator": {"url": url, "file_path": None}},
        "usage": {"sensitivity": "personal", "allowed_for_work_output": True},
        "extracted_points": [],
    }


def _ingest_eligible(registry: AssertionRegistry, source_key: str, content: str) -> tuple[str, str, dict]:
    """Plant one eligible-but-unbackfilled edition through the real ingest path.

    Mirrors exactly how ``external_research_resolution``'s fresh-acquire path
    stamps ``allowed_use.basis == producer_declared_access_status`` and never
    an ``extraction_status`` -- i.e. the real shape of the 35 legacy editions.
    """

    # verify_source_card_binding calls source_card_snapshot(source_key, source_card)
    # -- the snapshot's source_card_id must equal source_key itself, not a
    # separately-namespaced id (see AssertionRegistry.verify_source_card_binding).
    source_card = _source_card(source_key, f"https://example.test/{source_key}")
    snapshot = registry.source_card_snapshot(source_key, source_card)
    result = registry.ingest(
        source_key,
        content,
        media_type="text/plain",
        access_scope="personal",
        allowed_use=dict(ELIGIBLE_ALLOWED_USE),
        retrieval_locator={"url": f"https://example.test/{source_key}", "file_path": None},
        source_card_snapshot=snapshot,
    )
    assert result.created, "fixture setup must actually create the edition"
    edition = result.edition
    assert edition is not None
    assert "extraction_status" not in edition["metadata_extensions"]
    return result.source_id, edition["source_edition_id"], source_card


def _ingest_ineligible(registry: AssertionRegistry, source_key: str, content: str) -> tuple[str, str]:
    result = registry.ingest(
        source_key,
        content,
        media_type="text/plain",
        access_scope="personal",
        allowed_use=dict(INELIGIBLE_ALLOWED_USE),
        retrieval_locator={"url": f"https://example.test/{source_key}", "file_path": None},
    )
    assert result.created
    edition = result.edition
    assert edition is not None
    return result.source_id, edition["source_edition_id"]


def _ingest_already_set(registry: AssertionRegistry, source_key: str, content: str) -> tuple[str, str]:
    result = registry.ingest(
        source_key,
        content,
        media_type="text/plain",
        access_scope="personal",
        allowed_use=dict(ELIGIBLE_ALLOWED_USE),
        retrieval_locator={"url": f"https://example.test/{source_key}", "file_path": None},
        extraction_status=STATUS_FULL_TEXT,
    )
    assert result.created
    edition = result.edition
    assert edition is not None
    return result.source_id, edition["source_edition_id"]


# ---------------------------------------------------------------------------
# Preview (apply=False) — the default — writes nothing.
# ---------------------------------------------------------------------------


def test_apply_preview_writes_nothing(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-preview-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    _ingest_ineligible(registry, "ineligible-one", "a quote-join with no honest full text")
    _ingest_already_set(registry, "already-set-one", "already has a status")

    before = _tree(registry.root)
    receipt = m.apply_backfill(registry.root, apply=False)
    after = _tree(registry.root)

    assert after == before, "preview (default apply=False) must never write"
    assert receipt["mode"] == "dry_run"
    assert receipt["authoritative_data_mutated"] is False
    assert receipt["counts"] == {
        "eligible": 1,
        "ineligible": 1,
        "already_set": 1,
        "applied": 0,
        "pre_existing_integrity_failure": 0,
        "drift_detected": 0,
        "missing_at_write_time": 0,
    }
    assert len(receipt["changes"]) == 1
    assert receipt["changes"][0]["applied"] is False
    assert receipt["changes"][0]["recomputed_extraction_status"] == STATUS_FULL_TEXT
    assert receipt["pre_existing_integrity_failures"] == []
    assert "repairs" not in receipt, "the already_set repair path was removed (re-scope, 2026-08-02)"


# ---------------------------------------------------------------------------
# Item 6 — strict apply gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", [1, "true", "yes", [], {}])
def test_apply_rejects_non_bool_apply_value_item6(tmp_foundry, bad_value) -> None:
    registry = AssertionRegistry(workspace_id="m2-item6-workspace", paths=tmp_foundry)
    with pytest.raises(TypeError):
        m.apply_backfill(registry.root, apply=bad_value)


def test_rollback_rejects_non_bool_apply_value_item6(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-item6-rollback-workspace", paths=tmp_foundry)
    with pytest.raises(TypeError):
        m.rollback_backfill(registry.root, {"changes": []}, apply=1)


# ---------------------------------------------------------------------------
# B2 — scope pinning is required and enforced before any write.
# ---------------------------------------------------------------------------


def test_apply_without_pinned_receipt_is_rejected_b2(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-b2-unpinned-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    before = _ledger_tree(registry.root)

    with pytest.raises(m.BackfillIntegrityError, match="unpinned"):
        m.apply_backfill(registry.root, apply=True)

    assert _ledger_tree(registry.root) == before, "an unpinned apply attempt must not touch ledger data"


def test_apply_with_scope_drift_since_pinning_is_rejected_before_any_write_b2(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-b2-drift-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    pinned = m.apply_backfill(registry.root, apply=False)

    # Scope drift: a NEW qualifying edition lands after the approved dry-run,
    # before the --apply invocation -- exactly B2's scenario.
    _ingest_eligible(registry, "eligible-two", "a second edition that showed up late")

    before = _ledger_tree(registry.root)
    with pytest.raises(m.BackfillIntegrityError, match="added="):
        m.apply_backfill(registry.root, apply=True, pinned_receipt=pinned)
    after = _ledger_tree(registry.root)
    assert after == before, "a scope-drift rejection must not touch ledger data"


def test_apply_expect_count_mismatch_is_rejected_before_any_write_b2(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-b2-count-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    pinned = m.apply_backfill(registry.root, apply=False)

    before = _ledger_tree(registry.root)
    with pytest.raises(m.BackfillIntegrityError, match="expect-count"):
        m.apply_backfill(registry.root, apply=True, pinned_receipt=pinned, expect_count=99)
    after = _ledger_tree(registry.root)
    assert after == before


def test_apply_with_matching_pinned_receipt_succeeds_b2(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-b2-match-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    pinned = m.apply_backfill(registry.root, apply=False)

    receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=pinned, expect_count=1)
    assert receipt["counts"]["applied"] == 1


# ---------------------------------------------------------------------------
# Real apply, verified through the real public entry point.
# ---------------------------------------------------------------------------


def test_apply_writes_atomic_pair_and_passes_real_verify_source_card_binding(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-apply-workspace", paths=tmp_foundry)
    source_key = "eligible-one"
    source_id, edition_id, source_card = _ingest_eligible(registry, source_key, "short honest full text")

    receipt = _pin_and_apply(registry.root)
    assert receipt["mode"] == "apply"
    assert receipt["authoritative_data_mutated"] is True
    assert receipt["counts"]["applied"] == 1
    change = receipt["changes"][0]
    assert change["applied"] is True
    assert change["source_id"] == source_id
    assert change["source_edition_id"] == edition_id
    assert change["recomputed_extraction_status"] == STATUS_FULL_TEXT
    assert change["edition_binding_sha256_after"] != change["edition_binding_sha256_before"]

    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    reloaded_edition = load_yaml(edition_path)
    assert reloaded_edition["metadata_extensions"]["extraction_status"] == STATUS_FULL_TEXT

    # The real, unmodified public entry point -- not a shim standing in for it.
    registry.verify_source_card_binding(source_key, reloaded_edition, source_card)

    # Re-derived via _load_edition too (same chain verify_source_card_binding
    # uses internally): a second, independent confirmation of the same fact.
    registry._load_edition(source_id, edition_id)


def test_apply_leaves_ineligible_and_already_set_byte_identical(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-untouched-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    ineligible_source_id, ineligible_edition_id = _ingest_ineligible(
        registry, "ineligible-one", "a quote-join with no honest full text"
    )
    already_source_id, already_edition_id = _ingest_already_set(
        registry, "already-set-one", "already has a status"
    )

    def _pair_bytes(source_id: str, edition_id: str) -> tuple[bytes, bytes]:
        edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
        provenance_path = edition_path.parent / edition_id / "provenance.yaml"
        return edition_path.read_bytes(), provenance_path.read_bytes()

    ineligible_before = _pair_bytes(ineligible_source_id, ineligible_edition_id)
    already_before = _pair_bytes(already_source_id, already_edition_id)

    _pin_and_apply(registry.root)

    assert _pair_bytes(ineligible_source_id, ineligible_edition_id) == ineligible_before
    assert _pair_bytes(already_source_id, already_edition_id) == already_before


def test_apply_never_touches_content_bin(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-content-workspace", paths=tmp_foundry)
    source_id, edition_id, _source_card_dict = _ingest_eligible(registry, "eligible-one", "short honest full text")
    content_path = registry.root / "sources" / source_id / "editions" / edition_id / "content.bin"
    before = content_path.read_bytes()

    _pin_and_apply(registry.root)

    assert content_path.read_bytes() == before


def test_apply_is_idempotent_and_safe_to_resume(tmp_foundry) -> None:
    """A second apply=True run over an already-applied edition is a no-op for it."""

    registry = AssertionRegistry(workspace_id="m2-resume-workspace", paths=tmp_foundry)
    source_id, edition_id, _source_card_dict = _ingest_eligible(registry, "eligible-one", "short honest full text")

    first = _pin_and_apply(registry.root)
    assert first["counts"]["applied"] == 1

    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"
    after_first = (edition_path.read_bytes(), provenance_path.read_bytes())

    second = _pin_and_apply(registry.root)
    assert second["counts"]["applied"] == 0
    assert second["counts"]["already_set"] == 1
    after_second = (edition_path.read_bytes(), provenance_path.read_bytes())
    assert after_second == after_first, "a resumed run must not rewrite an already-applied pair"


# ---------------------------------------------------------------------------
# Item 4 — refuse to touch a pre-existing (unrelated) integrity failure.
# ---------------------------------------------------------------------------


def test_eligible_edition_that_does_not_verify_is_skipped_not_overwritten_item4(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-item4-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")
    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"

    # Corrupt the EXISTING provenance binding (pre-existing integrity failure,
    # unrelated to our backfill) BEFORE any apply attempt.
    provenance_record = load_yaml(provenance_path)
    corrupted = dict(provenance_record)
    corrupted["edition_binding_sha256"] = "0" * 64
    dump_yaml(corrupted, provenance_path)
    provenance_before = provenance_path.read_bytes()
    edition_before = edition_path.read_bytes()

    preview = m.apply_backfill(registry.root, apply=False)
    assert preview["counts"]["pre_existing_integrity_failure"] == 1
    assert preview["pre_existing_integrity_failures"] == [
        {"source_id": source_id, "source_edition_id": edition_id}
    ]
    assert preview["counts"]["applied"] == 0

    real_receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
    assert real_receipt["counts"]["pre_existing_integrity_failure"] == 1
    assert real_receipt["counts"]["applied"] == 0
    assert provenance_path.read_bytes() == provenance_before, (
        "a pre-existing integrity failure must never be silently overwritten"
    )
    assert edition_path.read_bytes() == edition_before


# ---------------------------------------------------------------------------
# Re-scope (2026-08-02, third round): already_set is READ-ONLY in
# apply_backfill. The repair-on-apply path (item 5, second round) was
# REMOVED entirely -- a half-rolled-back/binding-mismatched already_set
# edition is counted and reported, never opened or written by
# apply_backfill. Recovery is: re-run the same rollback receipt.
# ---------------------------------------------------------------------------


def test_already_set_is_read_only_in_apply_even_when_binding_is_broken(tmp_foundry) -> None:
    """A half-rolled-back / binding-mismatched already_set edition must be
    left completely untouched by apply_backfill -- counted, never written.
    This replaces the removed repair-on-apply path's test coverage."""

    registry = AssertionRegistry(workspace_id="m2-readonly-alreadyset-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")

    applied = _pin_and_apply(registry.root)
    assert applied["counts"]["applied"] == 1

    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"

    # Simulate an interrupted rollback: provenance reverted to its ORIGINAL
    # (pre-backfill) bytes, but edition.yaml still carries extraction_status
    # -- a half-rolled-back already_set edition.
    original_provenance_bytes = base64.b64decode(applied["changes"][0]["provenance_snapshot_b64"])
    provenance_path.write_bytes(original_provenance_bytes)

    edition_before = edition_path.read_bytes()
    provenance_before = provenance_path.read_bytes()

    # A fresh apply_backfill run (preview and real) must NOT touch it at all
    # -- no repairs list, no writes, just counted as already_set.
    preview = m.apply_backfill(registry.root, apply=False)
    assert preview["counts"]["already_set"] == 1
    assert preview["counts"]["eligible"] == 0
    assert "repairs" not in preview

    real = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
    assert real["counts"]["already_set"] == 1
    assert real["counts"]["applied"] == 0
    assert "repairs" not in real

    assert edition_path.read_bytes() == edition_before, "apply_backfill must never touch already_set editions"
    assert provenance_path.read_bytes() == provenance_before

    # The documented recovery path: re-run the SAME rollback receipt --
    # unconditional restore completes what the interrupted rollback started.
    rollback_receipt = m.rollback_backfill(registry.root, applied, apply=True)
    assert rollback_receipt["restored_count"] == 1
    assert edition_path.read_bytes() == base64.b64decode(applied["changes"][0]["edition_snapshot_b64"])
    assert provenance_path.read_bytes() == original_provenance_bytes

    # Now the registry's own verification chain passes again.
    registry._load_edition(source_id, edition_id)


def test_apply_never_opens_already_set_files_at_all(tmp_foundry, monkeypatch) -> None:
    """Structural proof: apply_backfill must not even READ an already_set
    edition's edition.yaml/provenance.yaml -- it is read-only via the
    enumeration's classification alone, never opened again."""

    registry = AssertionRegistry(workspace_id="m2-readonly-noopen-workspace", paths=tmp_foundry)
    already_source_id, already_edition_id = _ingest_already_set(
        registry, "already-set-one", "already has a status"
    )
    already_edition_path = (
        registry.root / "sources" / already_source_id / "editions" / f"{already_edition_id}.yaml"
    )
    already_provenance_path = already_edition_path.parent / already_edition_id / "provenance.yaml"

    real_read_bytes = Path.read_bytes
    opened: list[Path] = []

    def _tracking_read_bytes(self):  # noqa: ANN001
        if self in (already_edition_path, already_provenance_path):
            opened.append(self)
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", _tracking_read_bytes)

    preview = m.apply_backfill(registry.root, apply=False)
    assert preview["counts"]["already_set"] == 1
    assert opened == [], f"already_set files must never be opened, but read: {opened}"


# ---------------------------------------------------------------------------
# Rollback restores byte-identical originals from the receipt alone. Rollback
# now has its OWN strict preview-by-default gate (items 2/6).
# ---------------------------------------------------------------------------


def test_rollback_preview_default_writes_nothing_item2(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-rollback-preview-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    receipt = _pin_and_apply(registry.root)

    before = _tree(registry.root)
    preview = m.rollback_backfill(registry.root, receipt)  # apply defaults False
    after = _tree(registry.root)

    assert after == before, "rollback_backfill's default must be a zero-write preview"
    assert preview["mode"] == "dry_run"
    assert preview["authoritative_data_mutated"] is False
    assert preview["restored_count"] == 0
    assert preview["would_restore_count"] == 1


def test_rollback_restores_byte_identical_tree(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-rollback-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    _ingest_eligible(registry, "eligible-two", "b" * (_MAX_EXTRACT_CHARS + 10))
    _ingest_ineligible(registry, "ineligible-one", "a quote-join with no honest full text")
    _ingest_already_set(registry, "already-set-one", "already has a status")

    before = _ledger_tree(registry.root)
    receipt = _pin_and_apply(registry.root)
    assert receipt["counts"]["applied"] == 2
    after_apply = _ledger_tree(registry.root)
    assert after_apply != before, "apply must have changed something"

    rollback_receipt = m.rollback_backfill(registry.root, receipt, apply=True)
    assert rollback_receipt["restored_count"] == 2
    assert rollback_receipt["authoritative_data_mutated"] is True

    after_rollback = _ledger_tree(registry.root)
    assert after_rollback == before, "rollback must restore byte-identical originals (ledger data)"


def test_rollback_of_a_preview_receipt_is_a_ledger_content_noop(tmp_foundry) -> None:
    """Rollback restores UNCONDITIONALLY -- given a preview receipt (nothing
    was ever applied), it still "restores" each entry, but since current
    bytes already equal the snapshot, ledger content is unchanged even
    though ``restored_count`` reflects the attempt.
    """

    registry = AssertionRegistry(workspace_id="m2-rollback-noop-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")

    preview_receipt = m.apply_backfill(registry.root, apply=False)
    before = _ledger_tree(registry.root)
    rollback_receipt = m.rollback_backfill(registry.root, preview_receipt, apply=True)
    after = _ledger_tree(registry.root)

    assert rollback_receipt["restored_count"] == 1
    assert after == before, "restoring an untouched edition's own snapshot must be a content no-op"


def test_rollback_rejects_a_tampered_snapshot_checksum(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-rollback-tamper-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    receipt = _pin_and_apply(registry.root)

    tampered = dict(receipt)
    tampered["changes"] = [dict(receipt["changes"][0])]
    tampered["changes"][0]["edition_yaml_sha256_before"] = "0" * 64

    with pytest.raises(RuntimeError):
        m.rollback_backfill(registry.root, tampered, apply=True)


# ---------------------------------------------------------------------------
# Item 3 — receipt-driven id/path validation; a traversal receipt is rejected
# wholesale, before any write.
# ---------------------------------------------------------------------------


def test_rollback_rejects_a_traversal_receipt_item3(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-traversal-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    receipt = _pin_and_apply(registry.root)

    malicious = dict(receipt)
    malicious["changes"] = [dict(receipt["changes"][0])]
    malicious["changes"][0]["source_id"] = "../../../../etc"

    before = _tree(registry.root)
    with pytest.raises(m.BackfillIntegrityError):
        m.rollback_backfill(registry.root, malicious, apply=True)
    after = _tree(registry.root)
    assert after == before, "a rejected traversal receipt must write nothing"


def test_rollback_rejects_an_out_of_pattern_edition_id_item3(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-badid-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    receipt = _pin_and_apply(registry.root)

    malicious = dict(receipt)
    malicious["changes"] = [dict(receipt["changes"][0])]
    malicious["changes"][0]["source_edition_id"] = "sed_not_a_real_hex_id"

    with pytest.raises(m.BackfillIntegrityError):
        m.rollback_backfill(registry.root, malicious, apply=True)


# ---------------------------------------------------------------------------
# R5 — partial apply must be structurally impossible: a hand-constructed
# intermediate state (mimicking a crash between the two writes) always fails
# the registry's own verification, from either direction.
# ---------------------------------------------------------------------------


def test_partial_pair_new_status_stale_provenance_fails_closed(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-partial-a-workspace", paths=tmp_foundry)
    source_id, edition_id, _source_card_dict = _ingest_eligible(registry, "eligible-one", "short honest full text")
    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"

    # Simulate: edition.yaml written with the new status, provenance.yaml
    # left at its pre-apply bytes (crash between the two writes, edition first).
    edition_record = load_yaml(edition_path)
    new_extensions = {**edition_record["metadata_extensions"], "extraction_status": STATUS_FULL_TEXT}
    new_edition = {**edition_record, "metadata_extensions": new_extensions}
    dump_yaml(new_edition, edition_path)

    with pytest.raises(RegistryIntegrityError):
        registry._load_edition(source_id, edition_id)


def test_partial_pair_new_provenance_stale_edition_fails_closed(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-partial-b-workspace", paths=tmp_foundry)
    source_id, edition_id, _source_card_dict = _ingest_eligible(registry, "eligible-one", "short honest full text")
    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"

    # Simulate the opposite crash point: provenance.yaml written with the new
    # binding, edition.yaml left at its pre-apply bytes.
    edition_record = load_yaml(edition_path)
    provenance_record = load_yaml(provenance_path)
    new_extensions = {**edition_record["metadata_extensions"], "extraction_status": STATUS_FULL_TEXT}
    new_edition = {**edition_record, "metadata_extensions": new_extensions}
    binding = AssertionRegistry._edition_binding(new_edition)

    new_provenance = {**provenance_record, "edition_binding": binding, "edition_binding_sha256": m._canonical_digest(binding)}
    dump_yaml(new_provenance, provenance_path)

    with pytest.raises(RegistryIntegrityError):
        registry._load_edition(source_id, edition_id)


def test_apply_self_repairs_in_process_when_second_write_fails(tmp_foundry, monkeypatch) -> None:
    """If the edition-side write of a pair raises, apply_backfill must put
    both files back to their exact pre-mutation bytes before re-raising --
    never returning control with a mismatched pair still on disk.
    """

    registry = AssertionRegistry(workspace_id="m2-selfrepair-workspace", paths=tmp_foundry)
    source_id, edition_id, _source_card_dict = _ingest_eligible(registry, "eligible-one", "short honest full text")
    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"
    edition_before = edition_path.read_bytes()
    provenance_before = provenance_path.read_bytes()

    real_atomic_dump = m._atomic_dump
    calls: list[Path] = []

    def _flaky_atomic_dump(data, path):  # noqa: ANN001
        calls.append(path)
        if path == edition_path:
            raise RuntimeError("simulated crash writing the edition side of the pair")
        return real_atomic_dump(data, path)

    monkeypatch.setattr(m, "_atomic_dump", _flaky_atomic_dump)

    preview = m.apply_backfill(registry.root, apply=False)
    with pytest.raises(RuntimeError, match="simulated crash"):
        m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)

    assert edition_path.read_bytes() == edition_before
    assert provenance_path.read_bytes() == provenance_before
    # Confirm the provenance write really was attempted first, proving this
    # test exercised the crash-between-writes path rather than a no-op.
    assert provenance_path in calls
    assert edition_path in calls


# ---------------------------------------------------------------------------
# B1b — the self-repair write itself must refuse to clobber bytes it did not
# create (a concurrent writer, corruption) rather than blindly overwriting.
# ---------------------------------------------------------------------------


def test_repair_refuses_to_clobber_diverged_bytes_b1b(tmp_foundry, monkeypatch) -> None:
    registry = AssertionRegistry(workspace_id="m2-b1b-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")
    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"
    edition_before = edition_path.read_bytes()

    real_atomic_dump = m._atomic_dump

    def _flaky(data, path):  # noqa: ANN001
        if path == provenance_path:
            real_atomic_dump(data, path)
            # Simulate a concurrent process clobbering provenance with
            # unrelated bytes right after our write lands, before this call
            # reaches the edition write.
            provenance_path.write_bytes(b"concurrent-writer-garbage")
            return
        raise RuntimeError("simulated crash writing the edition side of the pair")

    monkeypatch.setattr(m, "_atomic_dump", _flaky)

    preview = m.apply_backfill(registry.root, apply=False)
    with pytest.raises(RuntimeError, match="simulated crash"):
        m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)

    # Refused to repair provenance: its current bytes matched neither the
    # pre-mutation snapshot NOR the intended new bytes, so the garbage must
    # still be sitting there untouched -- NOT silently overwritten either way.
    assert provenance_path.read_bytes() == b"concurrent-writer-garbage"
    # Edition was never touched in the first place -- still original.
    assert edition_path.read_bytes() == edition_before


# ---------------------------------------------------------------------------
# N2 — a failure inside the self-repair block must never mask the original
# write exception.
# ---------------------------------------------------------------------------


def test_repair_failure_does_not_mask_original_exception_n2(tmp_foundry, monkeypatch) -> None:
    registry = AssertionRegistry(workspace_id="m2-n2-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")
    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"
    provenance_path = edition_path.parent / edition_id / "provenance.yaml"

    real_atomic_dump = m._atomic_dump

    def _flaky_dump(data, path):  # noqa: ANN001
        if path == provenance_path:
            return real_atomic_dump(data, path)  # succeeds -> needs repair afterward
        raise RuntimeError("simulated crash writing the edition side of the pair")

    def _repair_raises(data, path):  # noqa: ANN001
        raise OSError("disk full during repair")

    monkeypatch.setattr(m, "_atomic_dump", _flaky_dump)
    monkeypatch.setattr(m, "_atomic_write_bytes", _repair_raises)

    preview = m.apply_backfill(registry.root, apply=False)
    with pytest.raises(RuntimeError, match="simulated crash") as excinfo:
        m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)

    assert not isinstance(excinfo.value, OSError)
    notes = getattr(excinfo.value, "__notes__", [])
    assert any("repair" in note for note in notes), "the repair failure should be noted, not silent"


# ---------------------------------------------------------------------------
# Item 1 / B1a — write-ahead journal survives a mid-loop crash; a rollback
# derived purely from the journal restores everything already touched.
# ---------------------------------------------------------------------------


def test_journal_survives_a_midloop_crash_and_recovers_via_receipt_from_journal(tmp_foundry, monkeypatch) -> None:
    registry = AssertionRegistry(workspace_id="m2-journal-crash-workspace", paths=tmp_foundry)
    for i in range(5):
        _ingest_eligible(registry, f"eligible-{i}", f"short honest text number {i}")

    preview = m.apply_backfill(registry.root, apply=False)
    assert preview["counts"]["eligible"] == 5

    crash_after = 2  # let this many pairs through cleanly, then crash
    call_count = {"n": 0}
    real_atomic_dump = m._atomic_dump

    def _crash_midloop(data, path):  # noqa: ANN001
        if path.name == "provenance.yaml":
            call_count["n"] += 1
            if call_count["n"] > crash_after:
                raise RuntimeError("simulated hard crash mid-loop")
        return real_atomic_dump(data, path)

    monkeypatch.setattr(m, "_atomic_dump", _crash_midloop)

    with pytest.raises(RuntimeError, match="simulated hard crash"):
        m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)

    journal_candidates = list((registry.root / "backfill_operations").glob("apply_*.journal.jsonl"))
    assert len(journal_candidates) == 1
    journal_path = journal_candidates[0]

    recovered = m.receipt_from_journal(registry.root, journal_path)
    applied_in_journal = [c for c in recovered["changes"] if c["applied"]]
    assert len(applied_in_journal) == crash_after, (
        "the journal alone must show exactly the editions that fully landed before the crash"
    )

    rollback_receipt = m.rollback_backfill(registry.root, recovered, apply=True)
    assert rollback_receipt["restored_count"] == len(recovered["changes"])

    # Every touched edition (applied, not_applied, or incomplete) is back to
    # pre-mutation state -- a fresh preview reports ALL 5 eligible again.
    post_rollback_preview = m.apply_backfill(registry.root, apply=False)
    assert post_rollback_preview["counts"]["eligible"] == 5
    assert post_rollback_preview["counts"]["already_set"] == 0


# ---------------------------------------------------------------------------
# B2 design-change round: the ACTUAL gap -- an edition appearing mid-flight,
# after the pinned-scope check but before the write loop reaches it, must
# never be written. This is what a bare "check at the top" (the first B2
# fix) does NOT protect against; only iterating the approved set itself does.
# ---------------------------------------------------------------------------


def test_apply_iterates_the_pinned_set_not_a_fresh_glob_scope_drift_midflight(tmp_foundry, monkeypatch) -> None:
    """The gap the security lens found on re-review: the prior fix's pinned
    check was a snapshot taken once at the top of the call, but the mutate
    loop re-globbed the live directory fresh -- so a qualifying edition that
    appeared AFTER the check but BEFORE the loop reached its position in
    sort order was silently mutated, unapproved. An ordinary ``rf ingest``
    stamps exactly the qualifying basis, and the advisory lock does not
    block a writer that isn't using it.

    Hooks the exact boundary between "the scope check passed" and "the write
    loop begins" (wrapping ``_check_pinned_scope``) to inject a new
    qualifying edition right there, then asserts it is never touched.
    """

    registry = AssertionRegistry(workspace_id="m2-b2-midflight-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")
    preview = m.apply_backfill(registry.root, apply=False)

    real_check = m._check_pinned_scope
    injected: dict[str, tuple[str, str]] = {}

    def _check_then_inject_midflight(live_ids, *, pinned_receipt, expect_count):
        approved = real_check(live_ids, pinned_receipt=pinned_receipt, expect_count=expect_count)
        # Simulate a concurrent, ordinary writer (e.g. rf ingest) landing a
        # new qualifying edition right after the scope check passed.
        late_source_id, late_edition_id, _ = _ingest_eligible(
            registry, "eligible-injected-midflight", "a late-arriving qualifying edition"
        )
        injected["ids"] = (late_source_id, late_edition_id)
        return approved

    monkeypatch.setattr(m, "_check_pinned_scope", _check_then_inject_midflight)

    receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)

    assert injected.get("ids"), "the test itself must have actually injected a new edition"
    late_source_id, late_edition_id = injected["ids"]
    touched_ids = {(c["source_id"], c["source_edition_id"]) for c in receipt["changes"]}
    assert (late_source_id, late_edition_id) not in touched_ids, (
        "an edition that appeared mid-flight, after the scope check, must NEVER be written -- "
        "this is exactly the gap a top-of-call-only check does not close"
    )
    late_edition_path = registry.root / "sources" / late_source_id / "editions" / f"{late_edition_id}.yaml"
    late_record = load_yaml(late_edition_path)
    assert "extraction_status" not in late_record["metadata_extensions"], (
        "the mid-flight edition must remain untouched -- still eligible, never silently backfilled"
    )
    # The originally-approved edition still gets applied normally.
    assert receipt["counts"]["applied"] == 1
    assert (source_id, edition_id) in touched_ids

    # A fresh enumeration now sees 2 eligible editions (the injected one is
    # real and still untouched) -- confirms the injection landed for real and
    # the exclusion was structural, not an artifact of the injection failing.
    post_preview = m.apply_backfill(registry.root, apply=False)
    assert post_preview["counts"]["eligible"] == 1  # only the injected one remains eligible


def test_only_one_glob_per_apply_call(tmp_foundry, monkeypatch) -> None:
    """Structural proof, not just a behavioral one: exactly one
    ``Path.glob`` call happens per ``apply_backfill`` invocation (the single
    canonical enumeration) -- never a second walk inside the mutate loop."""

    registry = AssertionRegistry(workspace_id="m2-oneglob-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    _ingest_already_set(registry, "already-set-one", "already has a status")
    _ingest_ineligible(registry, "ineligible-one", "a quote-join with no honest full text")

    real_glob = Path.glob
    calls: list[str] = []

    def _counting_glob(self, pattern, *args, **kwargs):  # noqa: ANN001
        if pattern == "sources/*/editions/*.yaml":
            calls.append(str(self))
        return real_glob(self, pattern, *args, **kwargs)

    monkeypatch.setattr(Path, "glob", _counting_glob)

    preview = m.apply_backfill(registry.root, apply=False)
    assert len(calls) == 1, f"expected exactly one edition-set glob per call, got {len(calls)}"

    calls.clear()
    m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
    assert len(calls) == 1, f"expected exactly one edition-set glob per mutating call, got {len(calls)}"


# ---------------------------------------------------------------------------
# NB-3 -- defense in depth: a structural guard inside the write loop itself.
# ---------------------------------------------------------------------------


def test_membership_guard_is_present_and_would_catch_a_regression(tmp_foundry) -> None:
    """Not a behavioral test (the guard is unreachable by construction while
    the loop iterates ``approved_ids`` directly) -- just confirms the guard
    exists in the shipped source, so a future refactor that reintroduces a
    walk trips it instead of silently widening scope."""

    import inspect

    source = inspect.getsource(m.apply_backfill)
    assert "not in approved_ids" in source, "the NB-3 structural membership guard must still be present"


# ---------------------------------------------------------------------------
# Lock file hygiene: 0600, and unlinked on release when nothing mutated.
# ---------------------------------------------------------------------------


def test_lock_file_is_0600_and_unlinked_after_a_refused_apply(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-lock-hygiene-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    lock_path = registry.root / "backfill_operations" / ".apply.lock"

    # A refused (unpinned) apply attempt must not leave a lock file behind.
    with pytest.raises(m.BackfillIntegrityError):
        m.apply_backfill(registry.root, apply=True)
    assert not lock_path.exists(), "a refused apply must not leave a stray lock file in the evidence tree"


def test_lock_file_is_0600_and_kept_after_a_real_apply(tmp_foundry) -> None:
    import stat as stat_module

    registry = AssertionRegistry(workspace_id="m2-lock-hygiene-real-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    lock_path = registry.root / "backfill_operations" / ".apply.lock"

    _pin_and_apply(registry.root)

    assert lock_path.exists(), "a real apply run should keep its lock file as part of the audit trail"
    mode = stat_module.S_IMODE(lock_path.stat().st_mode)
    assert mode == 0o600, f"lock file must be 0600, got {oct(mode)}"


def test_lock_file_unlinked_after_rollback_preview_only(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-lock-hygiene-rollback-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    receipt = _pin_and_apply(registry.root)
    lock_path = registry.root / "backfill_operations" / ".apply.lock"
    assert lock_path.exists()

    # Preview-only rollback (apply=False, the default) never acquires the
    # lock at all -- confirm the existing (from the earlier apply) lock file
    # is untouched, then confirm a rollback preview alone doesn't create one
    # in a workspace that never had one.
    m.rollback_backfill(registry.root, receipt)
    assert lock_path.exists()


# ---------------------------------------------------------------------------
# receipt_from_journal tolerates a single torn trailing line.
# ---------------------------------------------------------------------------


def test_receipt_from_journal_tolerates_a_torn_trailing_line(tmp_foundry) -> None:
    registry = AssertionRegistry(workspace_id="m2-torn-journal-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    _ingest_eligible(registry, "eligible-two", "another short honest full text")

    preview = m.apply_backfill(registry.root, apply=False)
    receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
    assert receipt["counts"]["applied"] == 2

    journal_candidates = list((registry.root / "backfill_operations").glob("apply_*.journal.jsonl"))
    assert len(journal_candidates) == 1
    journal_path = journal_candidates[0]

    # Simulate a torn write: truncate the last line mid-JSON, as a hard power
    # loss between write() and fsync might leave it on some filesystems.
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    torn = lines[-1][: len(lines[-1]) // 2]
    journal_path.write_text(lines[0] + "\n" + torn, encoding="utf-8")

    recovered = m.receipt_from_journal(registry.root, journal_path)
    assert len(recovered["torn_lines"]) == 1
    assert recovered["torn_lines"][0]["line_number"] == 2
    # The earlier, still-intact, already-fsynced entry must still be usable.
    assert len(recovered["changes"]) == 1
    assert recovered["changes"][0]["applied"] is True

    rollback_receipt = m.rollback_backfill(registry.root, recovered, apply=True)
    assert rollback_receipt["restored_count"] == 1


def test_receipt_from_journal_raises_on_a_malformed_mid_journal_line(tmp_foundry) -> None:
    """Torn-line tolerance is narrowed to the TRAILING line only (third
    hardening round). A malformed line ANYWHERE ELSE is real corruption --
    silently skipping it could drop a rollback snapshot for an edition that
    was already mutated, so it must raise, not be swallowed.
    """

    registry = AssertionRegistry(workspace_id="m2-mid-journal-corrupt-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    _ingest_eligible(registry, "eligible-two", "another short honest full text")
    _ingest_eligible(registry, "eligible-three", "a third short honest full text")

    preview = m.apply_backfill(registry.root, apply=False)
    receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
    assert receipt["counts"]["applied"] == 3

    journal_candidates = list((registry.root / "backfill_operations").glob("apply_*.journal.jsonl"))
    journal_path = journal_candidates[0]

    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    # Corrupt the MIDDLE line, not the trailing one.
    lines[1] = lines[1][: len(lines[1]) // 2]
    journal_path.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(m.BackfillIntegrityError, match="NOT the trailing line"):
        m.receipt_from_journal(registry.root, journal_path)


# ---------------------------------------------------------------------------
# Fix 2 (third round): a missing file at write time is a clean
# skip-and-report, never an uncaught FileNotFoundError aborting the pass.
# ---------------------------------------------------------------------------


def test_missing_edition_file_at_write_time_is_skipped_and_reported(tmp_foundry, monkeypatch) -> None:
    registry = AssertionRegistry(workspace_id="m2-missing-file-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")
    keep_source_id, keep_edition_id, _sc2 = _ingest_eligible(registry, "eligible-two", "a second honest text")

    preview = m.apply_backfill(registry.root, apply=False)
    assert preview["counts"]["eligible"] == 2

    edition_path = registry.root / "sources" / source_id / "editions" / f"{edition_id}.yaml"

    # Delete the file AFTER the B2 scope check passes but BEFORE the write
    # loop reaches it -- a genuine "present at approval, gone at write time"
    # race, not a scope-drift the B2 check would itself already catch.
    real_check = m._check_pinned_scope

    def _check_then_delete(live_ids, *, pinned_receipt, expect_count):
        approved = real_check(live_ids, pinned_receipt=pinned_receipt, expect_count=expect_count)
        edition_path.unlink()
        return approved

    monkeypatch.setattr(m, "_check_pinned_scope", _check_then_delete)

    receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)

    assert receipt["counts"]["missing_at_write_time"] == 1
    assert receipt["missing_at_write_time"] == [
        {"source_id": source_id, "source_edition_id": edition_id, "path": str(edition_path)}
    ]
    # The pass must still complete and apply the OTHER, unaffected edition --
    # a missing file must not abort the whole receipt.
    assert receipt["counts"]["applied"] == 1
    touched_ids = {(c["source_id"], c["source_edition_id"]) for c in receipt["changes"] if c["applied"]}
    assert (keep_source_id, keep_edition_id) in touched_ids
    assert (source_id, edition_id) not in touched_ids


def test_missing_provenance_file_at_write_time_is_skipped_and_reported(tmp_foundry, monkeypatch) -> None:
    registry = AssertionRegistry(workspace_id="m2-missing-provenance-workspace", paths=tmp_foundry)
    source_id, edition_id, _sc = _ingest_eligible(registry, "eligible-one", "short honest full text")
    provenance_path = (
        registry.root / "sources" / source_id / "editions" / edition_id / "provenance.yaml"
    )

    preview = m.apply_backfill(registry.root, apply=False)

    real_check = m._check_pinned_scope

    def _check_then_delete(live_ids, *, pinned_receipt, expect_count):
        approved = real_check(live_ids, pinned_receipt=pinned_receipt, expect_count=expect_count)
        provenance_path.unlink()
        return approved

    monkeypatch.setattr(m, "_check_pinned_scope", _check_then_delete)

    receipt = m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
    assert receipt["counts"]["missing_at_write_time"] == 1
    assert receipt["counts"]["applied"] == 0


# ---------------------------------------------------------------------------
# Fix 1 (third round): every id in the apply loop is validated the same way
# rollback's receipt-driven ids are, before its path is derived.
# ---------------------------------------------------------------------------


def test_apply_validates_ids_before_deriving_paths(tmp_foundry, monkeypatch) -> None:
    """If something upstream of the write loop ever produced a
    traversal-shaped id (e.g. a future refactor to ``_enumerate_editions``),
    ``_validate_entry_ids_and_paths`` in the apply loop must reject it before
    any path is built from it -- the same defense already applied on the
    rollback side.
    """

    registry = AssertionRegistry(workspace_id="m2-apply-id-validation-workspace", paths=tmp_foundry)
    _ingest_eligible(registry, "eligible-one", "short honest full text")
    preview = m.apply_backfill(registry.root, apply=False)

    real_check = m._check_pinned_scope

    def _check_then_return_bad_ids(live_ids, *, pinned_receipt, expect_count):
        real_check(live_ids, pinned_receipt=pinned_receipt, expect_count=expect_count)
        return frozenset({("../../../../etc", "sed_" + "0" * 64)})

    monkeypatch.setattr(m, "_check_pinned_scope", _check_then_return_bad_ids)

    with pytest.raises(m.BackfillIntegrityError):
        m.apply_backfill(registry.root, apply=True, pinned_receipt=preview)
