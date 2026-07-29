"""RPC-2.1/RPC-2.2: canonical origin writer + envelope/receipt protocol.

Covers the freeze doc's own tamper/replay/parity vectors
(``docs/dev/architecture/research-provenance-contract-freeze.md`` §4/§5/§17.7a)
against the real implementation in
``research_foundry.services.provenance_envelope``.
"""

from __future__ import annotations

import copy
import threading

import pytest

from research_foundry.services.provenance_envelope import (
    ActivityDenial,
    ProvenanceEnvelopeDenied,
    ProvenanceEnvelopeStore,
    ProvenanceIntegrityError,
    ProvenancePromotionInterrupted,
    catalog_planning_evidence_entry,
    create_activity,
    degraded_selection_receipt,
    denied_selection_receipt,
    derive_origin_facets,
    empty_selection_receipt,
    fallback_selection_receipt,
    search_evidence_entry,
    selected_selection_receipt,
    verify_envelope_identity,
    verify_origin_integrity,
    verify_pair_integrity,
)
from research_foundry.yamlio import dumps_yaml, loads_yaml


def _method() -> dict:
    return {"kind": "acquisition", "mechanism": "web_search"}


def _producer() -> dict:
    return {"producer_type": "agent", "producer_id": "agent-1", "tool": "rf-search", "tool_version": "1.0"}


def _scope(provider: str = "pubmed") -> dict:
    return {"provider": provider, "site": None, "corpus": None}


def _selected_receipt(source: str = "pubmed") -> dict:
    return {
        "outcome": "selected",
        "source": source,
        "catalog_generation_id": None,
        "decided_at": "2026-07-28T12:10:05Z",
        "denial_reason": None,
        "degraded_reason": None,
        "fallback_reason": None,
    }


def _evidence(assertion_char: str = "a") -> list[dict]:
    return [
        {
            "assertion_id": f"ast_{assertion_char * 64}",
            "assertion_version": 1,
            "question_id": None,
            "decided_at": None,
        }
    ]


# --- origin (RPC-2.1) --------------------------------------------------------


def test_origin_write_is_content_addressed_and_replay_safe(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    record = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
        created_at="2026-07-28T12:00:00Z",
    )
    assert record["origin_id"].startswith("pvo_")
    assert record["identity"]["fingerprint"] == record["origin_id"].removeprefix("pvo_")
    assert verify_origin_integrity(record) == []

    # Byte-identical replay is a safe no-op, never a duplicate/overwrite.
    replay = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
        created_at="2026-07-28T12:00:00Z",
    )
    assert replay == record


def test_origin_tamper_detected_by_fingerprint_mismatch(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    record = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
    )
    tampered = copy.deepcopy(record)
    tampered["locator"] = "https://example.com/a-different-article"

    errors = verify_origin_integrity(tampered)
    assert any("fingerprint" in e for e in errors)

    # Direct on-disk tamper (bypassing the writer entirely) is caught on read.
    path = store._origin_path(record["origin_id"])
    path.write_text(dumps_yaml(tampered), encoding="utf-8")
    with pytest.raises(ProvenanceIntegrityError):
        store.read_origin(record["origin_id"])


def test_origin_version_bump_changes_identity(tmp_foundry) -> None:
    """Freeze doc §4.1 rule 7a: origin_version is material -- a version bump
    with every other field held constant mints a DIFFERENT origin_id, never a
    'free' version bump."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.write_origin(
        origin_version=1,
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
        created_at="2026-07-28T12:00:00Z",
    )
    v2 = store.write_origin(
        origin_version=2,
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
        created_at="2026-07-28T12:00:00Z",
    )
    assert v1["origin_id"] != v2["origin_id"]


def test_origin_conflicting_content_under_same_id_fails_closed(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    record = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
        created_at="2026-07-28T12:00:00Z",
    )
    # Simulate on-disk corruption: same origin_id filename, different bytes.
    corrupted = copy.deepcopy(record)
    corrupted["locator"] = "https://example.com/corrupted"
    store._origin_path(record["origin_id"]).write_text(dumps_yaml(corrupted), encoding="utf-8")

    with pytest.raises(ProvenanceIntegrityError):
        store.write_origin(
            method=_method(),
            producer=_producer(),
            source_kind="web_page",
            locator="https://example.com/article",
            content_digest="2" * 64,
            created_at="2026-07-28T12:00:00Z",
        )


def test_origin_parent_ref_cross_workspace_denied(tmp_foundry) -> None:
    store_a = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    parent = store_a.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/parent",
        content_digest="3" * 64,
    )

    store_b = ProvenanceEnvelopeStore(workspace_id="ws-b", paths=tmp_foundry)
    with pytest.raises(ProvenanceEnvelopeDenied) as exc_info:
        store_b.write_origin(
            method={"kind": "generation"},
            producer=_producer(),
            source_kind="agent_synthesis",
            locator=None,
            content_digest=None,
            parent_origin_refs=[{"origin_id": parent["origin_id"], "origin_version": 1}],
        )
    assert exc_info.value.reason_code == "not_authorized_or_not_found"

    # Same-workspace parent ref succeeds.
    child = store_a.write_origin(
        method={"kind": "generation"},
        producer=_producer(),
        source_kind="agent_synthesis",
        locator=None,
        content_digest=None,
        parent_origin_refs=[{"origin_id": parent["origin_id"], "origin_version": 1}],
    )
    assert child["parent_origin_refs"][0]["origin_id"] == parent["origin_id"]


def test_origin_missing_parent_ref_denied(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    with pytest.raises(ProvenanceEnvelopeDenied):
        store.write_origin(
            method={"kind": "generation"},
            producer=_producer(),
            source_kind="agent_synthesis",
            locator=None,
            content_digest=None,
            parent_origin_refs=[{"origin_id": f"pvo_{'0' * 64}", "origin_version": 1}],
        )


# --- SOL-31 (HIGH, gate-blocking): read_origin identity binding -------------


def test_read_origin_rejects_a_same_filename_content_substitution(tmp_foundry) -> None:
    """SOL-31: ``read_origin(requested_id)`` must require the loaded record's
    OWN ``origin_id`` to equal the requested one -- self-consistency alone
    (``verify_origin_integrity``) cannot catch a same-filename substitution,
    since the substituted bytes are a perfectly valid, real origin record for
    a DIFFERENT id."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    a = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/a",
        content_digest="a" * 64,
    )
    b = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/b",
        content_digest="b" * 64,
    )
    assert a["origin_id"] != b["origin_id"]

    # Copy B's valid bytes under A's canonical filename.
    store._origin_path(a["origin_id"]).write_bytes(store._origin_path(b["origin_id"]).read_bytes())

    with pytest.raises(ProvenanceIntegrityError):
        store.read_origin(a["origin_id"])


def test_read_origin_malformed_id_shape_is_not_found_not_an_error(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    assert store.read_origin("not-a-real-origin-id") is None
    assert store.read_origin("pvo_tooshort") is None


def test_origin_parent_ref_version_mismatch_denied(tmp_foundry) -> None:
    """SOL-31: a parent ref naming a REAL origin's id but the WRONG
    ``origin_version`` is denied the same way a wholly-nonexistent origin
    is -- never an existence-only check that ignores the referenced
    version."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    parent = store.write_origin(
        origin_version=1,
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/parent",
        content_digest="3" * 64,
    )
    with pytest.raises(ProvenanceEnvelopeDenied):
        store.write_origin(
            method={"kind": "generation"},
            producer=_producer(),
            source_kind="agent_synthesis",
            locator=None,
            content_digest=None,
            parent_origin_refs=[{"origin_id": parent["origin_id"], "origin_version": 2}],
        )


def test_envelope_origin_ref_version_mismatch_denied(tmp_foundry) -> None:
    """SOL-31: ``create_envelope_v1``'s own ``origin_ref`` check gets the
    SAME identity+version binding as a ``parent_origin_refs`` entry -- never
    an existence-only probe."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    origin = store.write_origin(
        origin_version=1,
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/origin",
        content_digest="4" * 64,
    )
    with pytest.raises(ProvenanceEnvelopeDenied):
        store.create_envelope_v1(
            activity_kind="search_only",
            origin_ref={"origin_id": origin["origin_id"], "origin_version": 99},
        )

    # The correct version succeeds.
    v1 = store.create_envelope_v1(
        activity_kind="search_only",
        origin_ref={"origin_id": origin["origin_id"], "origin_version": 1},
    )
    assert v1["origin_ref"]["origin_id"] == origin["origin_id"]


def test_facet_derivation_and_rebuild_delete_parity(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    origin = store.write_origin(
        method=_method(),
        producer=_producer(),
        source_kind="web_page",
        locator="https://example.com/article",
        content_digest="2" * 64,
    )
    facet = derive_origin_facets(origin)
    assert facet["origin_locator"] == "https://example.com/article"
    assert facet["origin_producer_tool"] == "rf-search"

    first = store.rebuild_origin_facets()
    second = store.rebuild_origin_facets()
    assert first == second == {origin["origin_id"]: facet}


# --- envelope + receipt protocol (RPC-2.2) -----------------------------------


def test_envelope_v1_carries_no_receipt_linkage_fields(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    assert v1["envelope_version"] == 1
    assert "activity_id" not in v1
    assert "receipt_commitment" not in v1


def test_search_only_activity_never_carries_a_planned_run_ref(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    assert v1["planned_run_ref"] is None

    with pytest.raises(ProvenanceIntegrityError):
        store.create_envelope_v1(activity_kind="planned_run", planned_run_ref=None)
    with pytest.raises(ProvenanceIntegrityError):
        store.create_envelope_v1(
            activity_kind="search_only", planned_run_ref={"run_id": "run-1"}
        )


def test_receipt_promotion_binds_activity_id_and_commitment(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(
        activity_kind="planned_run", planned_run_ref={"run_id": "run-2026-07-28-001"}
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
    assert v2["envelope_version"] == 2
    assert v2["activity_id"] == receipt["activity_id"]
    assert v2["receipt_commitment"] == receipt["identity"]["fingerprint"]
    assert v2["envelope_id"] == v1["envelope_id"]
    assert receipt["envelope_ref"] == {"envelope_id": v1["envelope_id"], "envelope_version": 1}

    envelope, read_receipt = store.read_envelope(v1["envelope_id"])
    assert envelope == v2
    assert read_receipt == receipt
    assert verify_pair_integrity(envelope, read_receipt) == []


def test_receipt_can_only_be_published_against_v1(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    _, v2 = store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )
    with pytest.raises(ProvenanceIntegrityError):
        store.create_receipt_and_promote(
            v2,
            query="another query",
            purpose=None,
            scope=_scope(),
            candidate_set_digest="4" * 64,
            selected_evidence_versions=_evidence("b"),
            selection_receipt=_selected_receipt(),
        )


def test_receipt_promotion_replay_is_idempotent(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    kwargs = dict(
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
        created_at="2026-07-28T13:00:05Z",
    )
    receipt_1, v2_1 = store.create_receipt_and_promote(v1, **kwargs)
    receipt_2, v2_2 = store.create_receipt_and_promote(v1, **kwargs)
    assert receipt_1 == receipt_2
    assert v2_1 == v2_2

    manifest = loads_yaml(store._manifest_path(v1["envelope_id"]).read_text(encoding="utf-8"))
    assert len(manifest["entries"]) == 1


def test_receipt_promotion_conflicting_replay_fails_closed(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )
    with pytest.raises(ProvenanceIntegrityError):
        store.create_receipt_and_promote(
            v1,
            query="a DIFFERENT query",
            purpose=None,
            scope=_scope(),
            candidate_set_digest="3" * 64,
            selected_evidence_versions=_evidence(),
            selection_receipt=_selected_receipt(),
        )


def test_generation_manifest_tamper_detected_on_read(tmp_foundry) -> None:
    """Freeze doc §17.7a reader rule: a reader recomputes version_digest from
    CURRENT on-disk content and compares against the generation-manifest
    entry recorded at legitimate promotion -- never trusting the record's own
    stored field in isolation."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )

    v2_path = store._envelope_version_path(v1["envelope_id"], 2)
    v2 = loads_yaml(v2_path.read_text(encoding="utf-8"))
    # Mutate a field that IS covered by version_digest, without recomputing
    # version_digest -- this is the exact tamper the manifest comparison must
    # catch (a self-consistency-only check would miss it if the attacker also
    # recomputed version_digest; here they do not, but the manifest check
    # catches either case since it never trusts the record's own bytes).
    v2["request_id"] = "forged-request-id"
    v2_path.write_text(dumps_yaml(v2), encoding="utf-8")

    with pytest.raises(ProvenanceIntegrityError):
        store.read_envelope(v1["envelope_id"])


def test_cross_record_equality_detects_receipt_substitution(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    receipt, v2 = store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )
    forged_receipt = copy.deepcopy(receipt)
    forged_receipt["identity"]["fingerprint"] = "f" * 64
    forged_receipt["activity_id"] = f"sar_{'f' * 64}"

    errors = verify_pair_integrity(v2, forged_receipt)
    assert any("receipt_commitment" in e or "activity_id" in e for e in errors)


def test_v1_only_envelope_with_no_receipt_is_not_an_integrity_failure(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    envelope, receipt = store.read_envelope(v1["envelope_id"])
    assert receipt is None
    assert verify_pair_integrity(envelope, receipt) == []


# --- SOL-32 (CRITICAL): envelope continuity can never be half-read ----------


def test_verify_pair_integrity_rejects_a_visible_v2_with_no_receipt() -> None:
    """SOL-32: unlike a v1-only envelope, a v2 record REQUIRES its receipt.
    ``verify_pair_integrity`` must no longer return success for ANY
    ``receipt is None`` -- only for a genuinely v1 envelope."""

    fake_v2 = {"envelope_id": "rre_" + "a" * 64, "envelope_version": 2}
    errors = verify_pair_integrity(fake_v2, None)
    assert any("receipt" in e for e in errors)


def test_manifested_v2_with_receipt_deleted_is_an_integrity_error_not_a_downgrade(
    tmp_foundry,
) -> None:
    """SOL-32 repro: promote a real receipt/v2 pair, then delete
    ``receipt.yaml`` directly on disk. ``read_envelope`` must now raise
    :class:`ProvenanceIntegrityError` -- never silently return ``(v2, None)``
    as though the v2 were a legitimately-visible, receipt-pending record."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    _receipt, _v2 = store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )

    store._receipt_path(v1["envelope_id"]).unlink()

    with pytest.raises(ProvenanceIntegrityError):
        store.read_envelope(v1["envelope_id"])


def test_manifested_v2_with_retained_v1_deleted_is_an_integrity_error(tmp_foundry) -> None:
    """SOL-32: a manifested v2 REQUIRES retained v1 to still be present --
    deleting ``v1.yaml`` after promotion must raise
    :class:`ProvenanceIntegrityError`, never silently serve the v2 alone."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )

    store._envelope_version_path(v1["envelope_id"], 1).unlink()

    with pytest.raises(ProvenanceIntegrityError):
        store.read_envelope(v1["envelope_id"])


def test_verify_envelope_identity_rejects_missing_or_forged_identity_block(tmp_foundry) -> None:
    """SOL-32: ``verify_envelope_identity`` now validates the STORED
    ``identity`` block itself (algorithm + material-field list + fingerprint
    equality), not merely the bare ``envelope_id`` string."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")

    missing_identity = dict(v1)
    del missing_identity["identity"]
    assert any("identity" in e for e in verify_envelope_identity(missing_identity))

    forged_algorithm = copy.deepcopy(v1)
    forged_algorithm["identity"]["algorithm"] = "md5-legacy"
    assert any("algorithm" in e for e in verify_envelope_identity(forged_algorithm))

    forged_fields = copy.deepcopy(v1)
    forged_fields["identity"]["material_fields"] = ["workspace_id"]
    assert any("material_fields" in e for e in verify_envelope_identity(forged_fields))

    forged_fingerprint = copy.deepcopy(v1)
    forged_fingerprint["identity"]["fingerprint"] = "f" * 64
    assert any("fingerprint" in e for e in verify_envelope_identity(forged_fingerprint))

    assert verify_envelope_identity(v1) == []


# --- T2-1..T2-4 attack coverage (Terra P2 cross-model audit hardening) -------


def test_forged_v1_mapping_promotion_attempt_rejected(tmp_foundry) -> None:
    """T2-1: ``create_receipt_and_promote`` must reload the CANONICAL v1 from
    this store's own root and reject a caller-supplied ``envelope_v1``
    mapping that carries the right ``envelope_id`` but a FORGED field value
    -- never trust the caller's copy over the record on disk."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only", request_id="req-real")

    forged_v1 = copy.deepcopy(dict(v1))
    forged_v1["request_id"] = "req-FORGED"  # a material field, held elsewhere

    with pytest.raises(ProvenanceIntegrityError, match="forged mapping rejected"):
        store.create_receipt_and_promote(
            forged_v1,
            query="test query",
            purpose=None,
            scope=_scope(),
            candidate_set_digest="3" * 64,
            selected_evidence_versions=_evidence(),
            selection_receipt=_selected_receipt(),
        )

    # Nothing was persisted -- the canonical v1 stays the only record on disk.
    envelope, receipt = store.read_envelope(v1["envelope_id"])
    assert envelope == v1
    assert receipt is None


def test_receipt_content_tamper_with_stale_fingerprint_detected_on_read(tmp_foundry) -> None:
    """T2-2: a receipt mutated directly on disk (e.g. its ``query`` text)
    WITHOUT recomputing ``identity.fingerprint`` must be caught by
    ``verify_receipt_identity`` on read -- never returned as though it were
    still valid because the surrounding pair/manifest checks happened to
    pass."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    receipt, _v2 = store.create_receipt_and_promote(
        v1,
        query="original query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )

    receipt_path = store._receipt_path(v1["envelope_id"])
    tampered = copy.deepcopy(receipt)
    tampered["query"] = "a completely different, tampered query"  # stale fingerprint
    receipt_path.write_text(dumps_yaml(tampered), encoding="utf-8")

    with pytest.raises(ProvenanceIntegrityError):
        store.read_envelope(v1["envelope_id"])


def test_crash_window_between_receipt_write_and_manifest_append_converges(tmp_foundry) -> None:
    """T2-3: a simulated crash after the receipt/v2 files are durably placed
    at their canonical paths but BEFORE the generation-manifest append must
    leave a half-pair ``read_envelope`` treats as NOT-YET-PROMOTED (never a
    silently-accepted half pair); ``recover_orphaned_promotions`` quarantines
    it; and a fresh promotion with the SAME inputs then converges cleanly."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    kwargs = dict(
        query="crash window query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
        created_at="2026-07-28T15:00:00Z",
    )

    with pytest.raises(ProvenancePromotionInterrupted):
        store.create_receipt_and_promote(v1, _interrupt_before_manifest=True, **kwargs)

    # Half-pair: receipt.yaml and v2.yaml both exist canonically, but no
    # manifest entry commits them -- read_envelope must not expose either.
    envelope_id = v1["envelope_id"]
    assert store._receipt_path(envelope_id).exists()
    assert store._envelope_version_path(envelope_id, 2).exists()

    envelope, receipt = store.read_envelope(envelope_id)
    assert envelope == v1  # still only the (v1) planning-time envelope
    assert receipt is None

    quarantined = store.recover_orphaned_promotions()
    assert envelope_id in quarantined
    assert not store._receipt_path(envelope_id).exists()
    assert not store._envelope_version_path(envelope_id, 2).exists()

    # A fresh promotion with the identical inputs converges cleanly.
    receipt, v2 = store.create_receipt_and_promote(v1, **kwargs)
    assert v2["envelope_version"] == 2
    envelope, read_receipt = store.read_envelope(envelope_id)
    assert envelope == v2
    assert read_receipt == receipt


def test_receipt_promotion_concurrent_writers_race_no_corruption(tmp_foundry) -> None:
    """T2-3: two threads publishing the SAME receipt for the same envelope
    concurrently must race safely under the per-envelope ``flock`` lock --
    both observe the identical, byte-equal result (one performs the real
    write, the other replays against the now-published pair), and the
    generation manifest never accumulates more than one entry."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    kwargs = dict(
        query="concurrent test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
        created_at="2026-07-28T15:10:00Z",
    )

    results: list[tuple[dict, dict]] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _writer() -> None:
        barrier.wait()
        try:
            results.append(store.create_receipt_and_promote(v1, **kwargs))
        except BaseException as exc:  # noqa: BLE001 - captured for assertion
            errors.append(exc)

    threads = [threading.Thread(target=_writer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert len(results) == 2
    assert results[0][0] == results[1][0]  # receipts
    assert results[0][1] == results[1][1]  # v2s

    manifest = loads_yaml(store._manifest_path(v1["envelope_id"]).read_text(encoding="utf-8"))
    assert len(manifest["entries"]) == 1


def test_manifest_self_consistent_forgery_caught_only_by_manifest_check(tmp_foundry) -> None:
    """T2-4/regression for the manifest test at :358-387's own gap: mutate
    v2 AND recompute its own ``version_digest`` so the record is internally
    self-consistent -- a check that merely recomputes and compares against
    the record's OWN stored digest would miss this. Only the comparison
    against the generation-manifest's independently-recorded digest (T2-4)
    catches it."""

    import hashlib
    import json

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )

    v2_path = store._envelope_version_path(v1["envelope_id"], 2)
    v2 = loads_yaml(v2_path.read_text(encoding="utf-8"))
    v2["request_id"] = "forged-request-id"
    version_digest_fields = (
        "envelope_id",
        "envelope_version",
        "workspace_id",
        "activity_kind",
        "request_id",
        "activity_id",
        "planned_run_ref",
        "parent_run_ref",
        "origin_ref",
        "aos_refs",
        "created_at",
        "receipt_commitment",
    )
    payload = {field_name: v2.get(field_name) for field_name in version_digest_fields}
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    v2["version_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    v2_path.write_text(dumps_yaml(v2), encoding="utf-8")

    # Self-consistency alone (recomputing from the tampered record's own
    # bytes) would now agree with the tampered version_digest -- only the
    # manifest's independently-recorded digest disagrees.
    with pytest.raises(ProvenanceIntegrityError):
        store.read_envelope(v1["envelope_id"])


def test_manifest_duplicate_entries_fail_closed(tmp_foundry) -> None:
    """T2-4: a generation manifest carrying TWO entries for the same
    ``(record_kind, record_id, version)`` is fail-closed on read -- never
    picked arbitrarily (e.g. "first match wins")."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    store.create_receipt_and_promote(
        v1,
        query="test query",
        purpose=None,
        scope=_scope(),
        candidate_set_digest="3" * 64,
        selected_evidence_versions=_evidence(),
        selection_receipt=_selected_receipt(),
    )

    manifest_path = store._manifest_path(v1["envelope_id"])
    manifest = loads_yaml(manifest_path.read_text(encoding="utf-8"))
    manifest["entries"].append(dict(manifest["entries"][0]))  # duplicate entry
    manifest_path.write_text(dumps_yaml(manifest), encoding="utf-8")

    with pytest.raises(ProvenanceIntegrityError, match="expected exactly one"):
        store.read_envelope(v1["envelope_id"])


# --- denial shape / guarded entry point --------------------------------------


def test_denied_selection_receipt_leaks_no_candidate_derived_value() -> None:
    receipt = denied_selection_receipt()
    assert receipt["denial_reason"] == "not_authorized_or_not_found"
    for field in ("source", "catalog_generation_id", "decided_at", "degraded_reason", "fallback_reason"):
        assert receipt[field] is None


def test_create_activity_pre_workspace_resolution_denial_is_ephemeral(tmp_foundry) -> None:
    result = create_activity(workspace_id=None, activity_kind="search_only", paths=tmp_foundry)
    assert isinstance(result, ActivityDenial)
    assert result.denied is True
    assert result.reason == "not_authorized_or_not_found"
    # Nothing was written to disk -- no envelope_id was ever minted.
    ledger_root = tmp_foundry.root / "provenance_ledger"
    assert not ledger_root.exists()


def test_create_activity_succeeds_with_a_resolved_workspace(tmp_foundry) -> None:
    result = create_activity(workspace_id="default", activity_kind="search_only", paths=tmp_foundry)
    assert isinstance(result, dict)
    assert result["workspace_id"] == "default"
    assert result["envelope_id"].startswith("rre_")


# --- outcome-arm builders (RPC-2.3, freeze doc §5.1 rule 4) ------------------


def test_all_five_outcome_arms_are_constructible_and_schema_valid(tmp_foundry) -> None:
    """Every one of the five outcome builders produces a receipt that passes
    ``create_receipt_and_promote``'s own schema validation with the exact
    null/non-null shape the freeze doc's table (§5.1 rule 4) requires."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)

    cases = [
        (
            "selected",
            selected_selection_receipt(source="pubmed", decided_at="2026-07-28T12:10:05Z"),
            _evidence(),
            "3" * 64,
        ),
        (
            "empty",
            empty_selection_receipt(source="pubmed", decided_at="2026-07-28T13:00:05Z"),
            [],
            "7" * 64,
        ),
        (
            "denied",
            denied_selection_receipt(),
            [],
            None,
        ),
        (
            "degraded",
            degraded_selection_receipt(
                source="pubmed",
                decided_at="2026-07-28T13:10:05Z",
                degraded_reason="provider_timeout_partial_result",
            ),
            [],
            "8" * 64,
        ),
        (
            "fallback",
            fallback_selection_receipt(
                source="web_discovery",
                decided_at="2026-07-28T13:11:05Z",
                fallback_reason="catalog_residual_then_discovery_fallback",
            ),
            _evidence("f"),
            "9" * 64,
        ),
    ]

    for outcome, selection_receipt, evidence, digest in cases:
        assert selection_receipt["outcome"] == outcome
        # Distinct request_id per iteration -- envelope identity (RPC-2.2)
        # binds only request-facing fields, not the receipt outcome, so
        # reusing the same (default) request_id across outcomes would mint
        # the SAME envelope_id for every case and collide on promotion.
        v1 = store.create_envelope_v1(activity_kind="search_only", request_id=f"req-{outcome}")
        receipt, v2 = store.create_receipt_and_promote(
            v1,
            query=f"test query for {outcome}",
            purpose=None,
            scope=_scope(),
            candidate_set_digest=digest,
            selected_evidence_versions=evidence,
            selection_receipt=selection_receipt,
        )
        assert receipt["selection_receipt"]["outcome"] == outcome
        assert v2["envelope_version"] == 2


def test_empty_outcome_is_never_confusable_with_denied(tmp_foundry) -> None:
    """SOL-7: `empty` names a real, evaluated candidate set that matched
    nothing (source/decided_at/digest non-null); `denied` names a fail-closed
    denial (all of those null). The two builders must never produce the same
    shape."""

    empty = empty_selection_receipt(source="pubmed", decided_at="2026-07-28T13:00:05Z")
    denied = denied_selection_receipt()

    assert empty["source"] is not None and denied["source"] is None
    assert empty["decided_at"] is not None and denied["decided_at"] is None
    assert empty["denial_reason"] is None and denied["denial_reason"] == "not_authorized_or_not_found"


def test_denied_receipt_leaks_no_candidate_or_corpus_value_end_to_end(tmp_foundry) -> None:
    """Denial matrix (freeze doc §10 threat boundary 1): a durable denied
    receipt, written through the real store, carries zero candidate/corpus-
    derived values anywhere on the record."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    receipt, _v2 = store.create_receipt_and_promote(
        v1,
        query="a query that was denied",
        purpose=None,
        scope={"provider": None, "site": None, "corpus": None},
        candidate_set_digest=None,
        selected_evidence_versions=[],
        selection_receipt=denied_selection_receipt(),
    )
    assert receipt["candidate_set_digest"] is None
    assert receipt["selected_evidence_versions"] == []
    assert receipt["selection_receipt"]["source"] is None
    assert receipt["selection_receipt"]["catalog_generation_id"] is None
    assert receipt["selection_receipt"]["decided_at"] is None
    assert receipt["selection_receipt"]["denial_reason"] == "not_authorized_or_not_found"


def test_degraded_and_fallback_reason_builders_reject_blank_reason() -> None:
    with pytest.raises(ProvenanceIntegrityError):
        degraded_selection_receipt(source="pubmed", decided_at="2026-07-28T00:00:00Z", degraded_reason="")
    with pytest.raises(ProvenanceIntegrityError):
        fallback_selection_receipt(source="web", decided_at="2026-07-28T00:00:00Z", fallback_reason="")


# --- per-question evidence entries / catalog_planning discriminator (SOL-8/23)


def test_search_evidence_entry_is_the_legacy_compatible_default() -> None:
    entry = search_evidence_entry(assertion_id=f"ast_{'a' * 64}", assertion_version=1)
    assert entry["question_id"] is None
    assert entry["decided_at"] is None
    assert "selection_origin" not in entry


def test_catalog_planning_evidence_entry_requires_question_id_and_decided_at(tmp_foundry) -> None:
    entry = catalog_planning_evidence_entry(
        assertion_id=f"ast_{'b' * 64}",
        assertion_version=1,
        question_id="q3",
        decided_at="2026-07-28T13:20:00Z",
    )
    assert entry["selection_origin"] == "catalog_planning"

    with pytest.raises(ProvenanceIntegrityError):
        catalog_planning_evidence_entry(
            assertion_id=f"ast_{'b' * 64}", assertion_version=1, question_id="", decided_at="2026-07-28T13:20:00Z"
        )
    with pytest.raises(ProvenanceIntegrityError):
        catalog_planning_evidence_entry(
            assertion_id=f"ast_{'b' * 64}", assertion_version=1, question_id="q3", decided_at=""
        )


def test_catalog_planning_entry_missing_question_id_rejected_by_schema(tmp_foundry) -> None:
    """Belt-and-suspenders: even bypassing the builder's own guard, the
    schema's `allOf` conditional on `selection_origin: catalog_planning`
    (SOL-8/23) independently rejects a missing `question_id`/`decided_at`."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    bad_entry = {
        "assertion_id": f"ast_{'c' * 64}",
        "assertion_version": 1,
        "question_id": None,
        "decided_at": "2026-07-28T13:20:00Z",
        "selection_origin": "catalog_planning",
    }
    with pytest.raises(ProvenanceIntegrityError):
        store.create_receipt_and_promote(
            v1,
            query="catalog rebase query",
            purpose=None,
            scope=_scope(),
            candidate_set_digest="a" * 64,
            selected_evidence_versions=[bad_entry],
            selection_receipt=selected_selection_receipt(
                source="catalog", decided_at="2026-07-28T13:20:05Z"
            ),
        )


# --- AOS refs (RPC-2.4, freeze doc §9 / AC RPC-7) ----------------------------


def test_aos_refs_absent_is_byte_identical_to_before(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(activity_kind="search_only")
    assert "aos_refs" not in v1


def test_aos_refs_present_round_trips_opaquely(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(
        activity_kind="search_only",
        aos_refs={"project_ref": "aos:proj:9f2c", "intent_ref": "aos:intent:11a0"},
        aos_ref_authorizer=lambda refs, workspace_id: True,
    )
    assert v1["aos_refs"] == {"project_ref": "aos:proj:9f2c", "intent_ref": "aos:intent:11a0"}


def test_aos_refs_malformed_fails_schema_validation_not_denial(tmp_foundry) -> None:
    """A malformed ref (wrong type) is a format defect -- ``ProvenanceIntegrityError``
    -- never the denial shape, and never silently coerced. An authorizer that
    would allow anything is supplied so the format defect is what's actually
    exercised here, not the (T2-6) required-authorizer gate."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    _allow = lambda refs, workspace_id: True  # noqa: E731
    with pytest.raises(ProvenanceIntegrityError):
        store.create_envelope_v1(
            activity_kind="search_only",
            aos_refs={"project_ref": 12345},
            aos_ref_authorizer=_allow,
        )
    with pytest.raises(ProvenanceIntegrityError):
        store.create_envelope_v1(
            activity_kind="search_only", aos_refs={}, aos_ref_authorizer=_allow
        )
    with pytest.raises(ProvenanceIntegrityError):
        store.create_envelope_v1(
            activity_kind="search_only",
            aos_refs={"project_ref": ""},
            aos_ref_authorizer=_allow,
        )


def test_aos_ref_authorizer_denies_unauthorized_ref_with_the_one_denial_shape(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    calls: list[tuple[dict, str]] = []

    def _deny(aos_refs: dict, workspace_id: str) -> bool:
        calls.append((dict(aos_refs), workspace_id))
        return False

    with pytest.raises(ProvenanceEnvelopeDenied) as exc_info:
        store.create_envelope_v1(
            activity_kind="search_only",
            aos_refs={"project_ref": "aos:proj:cross-workspace"},
            aos_ref_authorizer=_deny,
        )
    assert exc_info.value.reason_code == "not_authorized_or_not_found"
    assert calls == [({"project_ref": "aos:proj:cross-workspace"}, "ws-a")]

    # Nothing was minted or persisted -- fail-closed before any write.
    envelopes_dir = store._envelopes_dir()
    assert not envelopes_dir.exists() or not any(envelopes_dir.iterdir())


def test_aos_ref_authorizer_allows_an_authorized_ref(tmp_foundry) -> None:
    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    v1 = store.create_envelope_v1(
        activity_kind="search_only",
        aos_refs={"project_ref": "aos:proj:same-workspace"},
        aos_ref_authorizer=lambda refs, workspace_id: True,
    )
    assert v1["aos_refs"] == {"project_ref": "aos:proj:same-workspace"}


def test_aos_ref_authorizer_never_invoked_when_aos_refs_absent(tmp_foundry) -> None:
    """The authorizer hook must not fire at all when the caller never
    supplied ``aos_refs`` -- absence is the canonical no-context shape and
    triggers no authorization check whatsoever."""

    store = ProvenanceEnvelopeStore(workspace_id="ws-a", paths=tmp_foundry)
    calls: list[object] = []
    v1 = store.create_envelope_v1(
        activity_kind="search_only",
        aos_ref_authorizer=lambda refs, workspace_id: calls.append(1) or False,
    )
    assert calls == []
    assert "aos_refs" not in v1


def test_create_activity_forwards_aos_ref_authorizer(tmp_foundry) -> None:
    """The guarded ``create_activity`` entry point threads
    ``aos_ref_authorizer`` through unmodified. This is a POST-workspace-
    resolution denial (the workspace itself resolved fine; only the AOS ref
    was rejected) -- unlike the pre-resolution ``ActivityDenial`` return
    value, it surfaces the same way ``origin_ref``'s own denial already does:
    as a raised :class:`ProvenanceEnvelopeDenied`, not a returned value."""

    with pytest.raises(ProvenanceEnvelopeDenied) as exc_info:
        create_activity(
            workspace_id="default",
            activity_kind="search_only",
            aos_refs={"project_ref": "aos:proj:x"},
            aos_ref_authorizer=lambda refs, workspace_id: False,
            paths=tmp_foundry,
        )
    assert exc_info.value.reason_code == "not_authorized_or_not_found"


def test_create_activity_aos_ref_authorizer_absent_with_aos_refs_present_is_denied(
    tmp_foundry,
) -> None:
    """T2-6 (hardening): omitting ``aos_ref_authorizer`` on the guarded entry
    point is NO LONGER a silent no-check pass-through once ``aos_refs`` is
    present -- there is no way for this module to resolve AOS policy itself
    (the refs are opaque by design), so an ``aos_refs``-bearing call with no
    authorizer supplied is itself a denial, with nothing minted or
    persisted. This replaces the prior (permissive) locked-in behavior the
    T2-6 finding flagged."""

    with pytest.raises(ProvenanceEnvelopeDenied) as exc_info:
        create_activity(
            workspace_id="default",
            activity_kind="search_only",
            aos_refs={"project_ref": "aos:proj:x"},
            paths=tmp_foundry,
        )
    assert exc_info.value.reason_code == "not_authorized_or_not_found"
    ledger_root = tmp_foundry.root / "provenance_ledger"
    assert not ledger_root.exists()


def test_create_activity_aos_refs_absent_needs_no_authorizer(tmp_foundry) -> None:
    """Omitting ``aos_ref_authorizer`` remains byte-identical to pre-RPC-2.4
    behavior when ``aos_refs`` is ALSO absent -- there is nothing to
    authorize, so T2-6's required-authorizer gate never applies."""

    result = create_activity(
        workspace_id="default",
        activity_kind="search_only",
        paths=tmp_foundry,
    )
    assert isinstance(result, dict)
    assert "aos_refs" not in result

