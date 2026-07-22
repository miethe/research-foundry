"""Content-addressed terms-of-service snapshotting (rights-entity-model-v1, P4-2).

Enumerated H3 test scenarios (see
``docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-3-4-capture.md``
P4-2 row):

1. first snapshot of a new terms URL -> hash computed and stored
2. re-snapshot with unchanged content -> same hash, ``terms_verified_at`` updated
3. re-snapshot with changed content -> new hash + a diff record
4. snapshot excluded from ``rf run export`` bundle
5. fetch failure during snapshot -- a typed :class:`TermsSnapshotFailure` is
   returned (never a bare ``None``), and the failure record disambiguates
   "never attempted" from "attempted and failed" for a consumer reading
   ``rights_record.access`` (P4-3, R-P2 implicit AC).
"""

from __future__ import annotations

import json

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services import export_service as export_svc
from research_foundry.services.terms_snapshot import (
    TermsSnapshotFailure,
    access_terms_snapshot_status,
    snapshot_terms,
    url_key,
)
from research_foundry.yamlio import dump_yaml, load_yaml

RUN_ID = "rf_run_p4_terms_snapshot"
TERMS_URL = "https://example.test/terms"


def _run_paths(tmp_foundry: FoundryPaths):
    rp = tmp_foundry.run_paths(RUN_ID)
    rp.ensure_scaffold()
    return rp


# --------------------------------------------------------------------------
# 1. first snapshot of a new terms URL -> hash computed and stored
# --------------------------------------------------------------------------
def test_first_snapshot_computes_and_stores_hash(tmp_foundry: FoundryPaths) -> None:
    rp = _run_paths(tmp_foundry)

    result = snapshot_terms(RUN_ID, TERMS_URL, content="Terms v1 body.", paths=tmp_foundry)

    assert result is not None
    assert result.changed is False
    assert result.previous_sha256 is None
    assert result.terms_snapshot_sha256
    assert result.terms_verified_at

    pointer_path = rp.rights_terms_snapshots / f"{url_key(TERMS_URL)}.yaml"
    assert pointer_path.exists()
    record = load_yaml(pointer_path)
    assert record["terms_snapshot_sha256"] == result.terms_snapshot_sha256
    assert record["history"] == []

    blob_path = rp.rights_terms_snapshots / "content" / f"{result.terms_snapshot_sha256}.txt"
    assert blob_path.read_text(encoding="utf-8") == "Terms v1 body."


# --------------------------------------------------------------------------
# 2. re-snapshot, unchanged content -> same hash, terms_verified_at updated
# --------------------------------------------------------------------------
def test_resnapshot_unchanged_content_updates_verified_at_only(
    tmp_foundry: FoundryPaths,
) -> None:
    _run_paths(tmp_foundry)

    first = snapshot_terms(RUN_ID, TERMS_URL, content="Stable terms text.", paths=tmp_foundry)
    assert first is not None

    second = snapshot_terms(RUN_ID, TERMS_URL, content="Stable terms text.", paths=tmp_foundry)

    assert second is not None
    assert second.changed is False
    assert second.terms_snapshot_sha256 == first.terms_snapshot_sha256
    assert second.previous_sha256 == first.terms_snapshot_sha256
    assert second.terms_verified_at  # always present/non-empty
    assert second.diff == []


# --------------------------------------------------------------------------
# 3. re-snapshot, changed content -> new hash + a diff record
# --------------------------------------------------------------------------
def test_resnapshot_changed_content_records_new_hash_and_diff(
    tmp_foundry: FoundryPaths,
) -> None:
    rp = _run_paths(tmp_foundry)

    first = snapshot_terms(
        RUN_ID, TERMS_URL, content="Line one.\nLine two.\n", paths=tmp_foundry
    )
    assert first is not None

    second = snapshot_terms(
        RUN_ID, TERMS_URL, content="Line one.\nLine THREE.\n", paths=tmp_foundry
    )

    assert second is not None
    assert second.changed is True
    assert second.terms_snapshot_sha256 != first.terms_snapshot_sha256
    assert second.previous_sha256 == first.terms_snapshot_sha256
    assert second.diff, "a unified diff must be recorded when content changes"
    assert any("Line THREE" in line for line in second.diff)

    record = load_yaml(rp.rights_terms_snapshots / f"{url_key(TERMS_URL)}.yaml")
    assert record["terms_snapshot_sha256"] == second.terms_snapshot_sha256
    assert len(record["history"]) == 1
    assert record["history"][0]["sha256"] == first.terms_snapshot_sha256

    diff_path = (
        rp.rights_terms_snapshots
        / "diffs"
        / f"{first.terms_snapshot_sha256}_{second.terms_snapshot_sha256}.diff"
    )
    assert diff_path.exists()

    # Old content blob is retained (content-addressed stores are append-only).
    old_blob = rp.rights_terms_snapshots / "content" / f"{first.terms_snapshot_sha256}.txt"
    assert old_blob.exists()


# --------------------------------------------------------------------------
# 4. snapshot excluded from `rf run export` bundle
# --------------------------------------------------------------------------
def test_export_run_excludes_terms_snapshots(tmp_foundry: FoundryPaths) -> None:
    rp = _run_paths(tmp_foundry)
    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": RUN_ID,
            "sensitivity": "personal",
            "created_at": "2026-07-21T00:00:00-04:00",
        },
        rp.run_yaml,
    )

    nonce = "TERMS_SNAPSHOT_MUST_NOT_LEAK_INTO_EXPORT_9f3a"
    result = snapshot_terms(RUN_ID, "https://example.test/tos", content=nonce, paths=tmp_foundry)
    assert result is not None
    # Sanity: the snapshot really did land on disk under rights/terms_snapshots/.
    assert any(rp.rights_terms_snapshots.rglob("*"))

    exported = export_svc.export_run(tmp_foundry, RUN_ID)
    serialized = json.dumps(exported, ensure_ascii=False)

    assert nonce not in serialized
    assert "terms_snapshots" not in serialized
    assert "terms_snapshot_sha256" not in serialized

    # Same guarantee holds for the file actually written by `rf run export`.
    written_path = export_svc.export_to_file(tmp_foundry, RUN_ID)
    written_text = written_path.read_text(encoding="utf-8")
    assert nonce not in written_text
    assert "terms_snapshots" not in written_text


# --------------------------------------------------------------------------
# 5. fetch failure -> a typed, populated TermsSnapshotFailure (P4-3).
# --------------------------------------------------------------------------
def test_snapshot_never_raises_on_fetch_failure(tmp_foundry: FoundryPaths) -> None:
    _run_paths(tmp_foundry)

    def _boom(url: str) -> str | None:
        raise RuntimeError("simulated network failure")

    result = snapshot_terms(
        RUN_ID, "https://example.test/unreachable", fetcher=_boom, paths=tmp_foundry
    )

    assert isinstance(result, TermsSnapshotFailure)
    assert result.reason == "fetch_error"
    assert "simulated network failure" in result.detail
    assert result.attempted_at


def test_snapshot_default_fetcher_degrades_to_failure_record(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No injected fetcher/content, real fetch path raises -> typed failure.

    ``_default_fetcher`` swallows the underlying exception itself and
    returns ``None`` (its own never-raises contract, unchanged by P4-3), so
    from ``snapshot_terms``'s vantage point this surfaces as
    ``reason="empty_content"`` rather than ``"fetch_error"`` -- the
    distinction is preserved for callers that inject their own *fetcher* (see
    ``test_snapshot_never_raises_on_fetch_failure`` above), which is the path
    that can actually observe the raised exception.

    Monkeypatches ``urllib.request.urlopen`` itself (rather than hitting the
    network) so this stays deterministic and offline, per project convention
    (services/source_cards.py's own ``_fetch_url`` tests follow the same
    no-real-network pattern).
    """

    import urllib.request

    _run_paths(tmp_foundry)

    def _raise_urlopen(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated DNS/connection failure")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_urlopen)

    result = snapshot_terms(RUN_ID, "https://example.test/unreachable", paths=tmp_foundry)

    assert isinstance(result, TermsSnapshotFailure)
    assert result.reason == "empty_content"
    assert result.detail
    assert result.attempted_at


def test_fetch_failure_never_raises_and_is_never_null(tmp_foundry: FoundryPaths) -> None:
    """Required test 1 (P4-3): ``terms_snapshot_failure`` is populated (never
    null) on fetch failure, and the ``terms_snapshot_uri``/
    ``terms_snapshot_sha256`` fields it would sit alongside in
    ``rights_record.access`` remain ``null``.
    """

    _run_paths(tmp_foundry)

    def _boom(url: str) -> str | None:
        raise TimeoutError("simulated fetch timeout")

    result = snapshot_terms(
        RUN_ID, "https://example.test/tos", fetcher=_boom, paths=tmp_foundry
    )

    assert isinstance(result, TermsSnapshotFailure)
    failure_dict = result.to_access_dict()
    assert failure_dict["reason"] == "fetch_error"
    assert failure_dict["detail"]
    assert failure_dict["attempted_at"]

    # The would-be rights_record.access block for this attempt: the failure
    # record is populated while the snapshot pointer fields stay null -- this
    # is the exact shape validated against schemas/rights_record.schema.yaml.
    access = {
        "basis": "public_web",
        "terms_url": "https://example.test/tos",
        "terms_snapshot_uri": None,
        "terms_snapshot_sha256": None,
        "terms_snapshot_failure": failure_dict,
        "terms_verified_at": failure_dict["attempted_at"],
    }
    assert access["terms_snapshot_uri"] is None
    assert access["terms_snapshot_sha256"] is None
    assert access["terms_snapshot_failure"] is not None

    instance = {
        "schema_version": "1.0",
        "rights_record_id": "rr_demo_terms_failure",
        "source_id": "src_demo",
        "record_scope": "source_and_access_context",
        "jurisdictions": ["US"],
        "access": access,
        "copyright": {"status": "unknown"},
        "component_decisions": [
            {"component_type": "bibliographic_metadata", "decision": "permitted"},
        ],
        "overall_status": "UNKNOWN",
        "review": {
            "reviewed_at": failure_dict["attempted_at"],
            "review_status": "agent_triage_only",
        },
    }
    validation = validate(instance, "rights_record")
    assert validation.ok, f"expected valid, got errors: {validation.errors}"


# --------------------------------------------------------------------------
# Required test 2 (P4-3, R-P2 implicit AC): a consumer reading
# terms_snapshot_uri/terms_snapshot_sha256 must check terms_snapshot_failure
# BEFORE treating a null terms_snapshot_uri as "not applicable" -- absence
# alone is ambiguous between "never attempted" and "attempted and failed".
# --------------------------------------------------------------------------
def test_consumer_status_check_distinguishes_failed_from_not_attempted() -> None:
    failure_record = {
        "run_id": RUN_ID,
        "terms_url": TERMS_URL,
        "reason": "fetch_error",
        "detail": "simulated network failure",
        "attempted_at": "2026-07-21T00:00:00Z",
    }

    # Success: a URI is present, no failure recorded.
    success_access = {"terms_snapshot_uri": "rights/terms_snapshots/abc.yaml"}
    assert access_terms_snapshot_status(success_access) == "success"

    # Failed: URI is null, but a failure record is present -- must NOT be
    # read as "not applicable" just because the URI is null.
    failed_access = {"terms_snapshot_uri": None, "terms_snapshot_failure": failure_record}
    assert access_terms_snapshot_status(failed_access) == "failed"

    # Never attempted: URI is null AND no failure record exists.
    not_attempted_access = {"terms_snapshot_uri": None, "terms_snapshot_failure": None}
    assert access_terms_snapshot_status(not_attempted_access) == "not_attempted"

    # Regression guard for the exact bug R-P2 calls out: a naive consumer
    # that only checks `terms_snapshot_uri is None` to mean "not applicable"
    # would misclassify the failed case above as not_attempted. The helper
    # must check the failure record first.
    naive_check = failed_access.get("terms_snapshot_uri") is None
    assert naive_check is True  # the naive signal is indeed null...
    assert access_terms_snapshot_status(failed_access) != "not_attempted"  # ...but not the answer
