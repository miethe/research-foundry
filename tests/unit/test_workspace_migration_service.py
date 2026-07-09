"""Unit tests for workspace_migration_service (public-multiuser-release P5.3 WKSP-301).

Coverage
--------
* :func:`~research_foundry.services.workspace_migration_service.dry_run` —
  zero-write contract (mtime + content-hash invariant), counting accuracy,
  empty-workspace handling, catalog.db row count.
* :func:`~research_foundry.api.auth.scope.require_workspace_scope` —
  non-blocking invariant (always returns ``allowed=True``), advisory log
  emission, log fields, and single-operator-trust (``identity=None``) mode.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.auth.scope import (
    WorkspaceScopeResult,
    require_workspace_scope,
)
from research_foundry.paths import FoundryPaths
from research_foundry.services.workspace_migration_service import (
    BackfillManifestEntry,
    BackfillReport,
    DryRunReport,
    RollbackReport,
    backfill,
    dry_run,
    rollback,
)
from research_foundry.yamlio import dump_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_hash(path: Path) -> str:
    """SHA-256 hex digest of file bytes (content-identity proof)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plant_draft(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    workspace_id: str | None = None,
    created_by: str | None = None,
) -> Path:
    """Create a minimal draft.yaml under <workspace>/reports/drafts/<id>/."""
    draft_dir = paths.report_drafts / report_draft_id
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "draft.yaml"
    payload: dict = {
        "schema_version": 1,
        "type": "report_draft",
        "report_draft_id": report_draft_id,
        "title": f"Draft {report_draft_id}",
        "status": "draft",
        "sensitivity": "public",
        "created_at": "2026-06-13T09:41:00+00:00",
        "updated_at": "2026-06-13T09:41:00+00:00",
    }
    if workspace_id is not None:
        payload["workspace_id"] = workspace_id
    if created_by is not None:
        payload["created_by"] = created_by
    dump_yaml(payload, draft_path)
    return draft_path


def _plant_catalog_db(paths: FoundryPaths, row_count: int = 3) -> Path:
    """Bootstrap a minimal catalog.db with ``row_count`` placeholder rows."""
    paths.rf_cache.mkdir(parents=True, exist_ok=True)
    db_path = paths.catalog_db
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_items (
                catalog_item_id TEXT PRIMARY KEY,
                item_type TEXT,
                run_id TEXT,
                sensitivity_rank INTEGER DEFAULT 0,
                sensitivity TEXT,
                status TEXT,
                project TEXT,
                title TEXT,
                updated_at TEXT,
                confidence_rank INTEGER DEFAULT 0,
                payload_json TEXT DEFAULT '{}',
                search_text TEXT DEFAULT ''
            )
            """
        )
        for i in range(row_count):
            conn.execute(
                "INSERT OR IGNORE INTO catalog_items (catalog_item_id, item_type, run_id) "
                "VALUES (?, 'claim', 'run_001')",
                (f"ci_test_{i:04d}",),
            )
        conn.commit()
    return db_path


# ---------------------------------------------------------------------------
# DryRunReport — structural tests
# ---------------------------------------------------------------------------


def test_dry_run_empty_workspace(tmp_foundry: FoundryPaths) -> None:
    """dry_run on a workspace with no drafts and no catalog.db returns zeroes."""
    report = dry_run(tmp_foundry)

    assert isinstance(report, DryRunReport)
    assert report.total_drafts == 0
    assert report.drafts_missing_workspace_id == 0
    assert report.drafts_missing_created_by == 0
    assert report.total_catalog_items == 0
    assert report.target_workspace_id == "default"
    assert isinstance(report.caller_impact_summary, str)
    assert len(report.caller_impact_summary) > 0


def test_dry_run_counts_drafts_missing_workspace_id(tmp_foundry: FoundryPaths) -> None:
    """dry_run correctly tallies drafts missing workspace_id / created_by."""
    # Draft A: missing both fields
    _plant_draft(tmp_foundry, "rpt_a_missing_both")
    # Draft B: has workspace_id but missing created_by
    _plant_draft(tmp_foundry, "rpt_b_ws_only", workspace_id="default")
    # Draft C: has both
    _plant_draft(tmp_foundry, "rpt_c_full", workspace_id="default", created_by="alice")

    report = dry_run(tmp_foundry)

    assert report.total_drafts == 3
    assert report.drafts_missing_workspace_id == 1   # only draft A
    assert report.drafts_missing_created_by == 2     # drafts A + B
    assert report.target_workspace_id == "default"


def test_dry_run_counts_catalog_items(tmp_foundry: FoundryPaths) -> None:
    """dry_run reads catalog.db row count accurately."""
    _plant_catalog_db(tmp_foundry, row_count=7)

    report = dry_run(tmp_foundry)
    assert report.total_catalog_items == 7


def test_dry_run_catalog_db_absent_returns_zero(tmp_foundry: FoundryPaths) -> None:
    """When catalog.db does not exist dry_run reports total_catalog_items=0 (no error)."""
    assert not tmp_foundry.catalog_db.exists()

    report = dry_run(tmp_foundry)
    assert report.total_catalog_items == 0


# ---------------------------------------------------------------------------
# Zero-write contract (WKSP-301 mandatory proof)
# ---------------------------------------------------------------------------


def test_dry_run_zero_writes_draft_yaml(tmp_foundry: FoundryPaths) -> None:
    """dry_run performs ZERO writes — every draft.yaml is mtime+hash identical after the call."""
    draft_paths = [
        _plant_draft(tmp_foundry, "rpt_zw_a"),
        _plant_draft(tmp_foundry, "rpt_zw_b", workspace_id="ws_x"),
        _plant_draft(tmp_foundry, "rpt_zw_c", workspace_id="ws_y", created_by="bob"),
    ]

    # Snapshot: mtime + content hash before dry_run.
    before = {p: (p.stat().st_mtime, _file_hash(p)) for p in draft_paths}

    _dry_run_report = dry_run(tmp_foundry)

    # Assert: every draft.yaml is byte-identical and untouched.
    for p in draft_paths:
        mtime_before, hash_before = before[p]
        mtime_after = p.stat().st_mtime
        hash_after = _file_hash(p)
        assert hash_after == hash_before, (
            f"dry_run mutated content of {p.name}: hash changed"
        )
        assert mtime_after == mtime_before, (
            f"dry_run touched mtime of {p.name}: {mtime_before} -> {mtime_after}"
        )


def test_dry_run_zero_writes_catalog_db(tmp_foundry: FoundryPaths) -> None:
    """dry_run performs ZERO writes to catalog.db — row count and mtime unchanged."""
    db_path = _plant_catalog_db(tmp_foundry, row_count=5)

    mtime_before = db_path.stat().st_mtime
    hash_before = _file_hash(db_path)

    dry_run(tmp_foundry)

    assert _file_hash(db_path) == hash_before, "dry_run mutated catalog.db"
    assert db_path.stat().st_mtime == mtime_before, "dry_run touched catalog.db mtime"


# ---------------------------------------------------------------------------
# require_workspace_scope — non-blocking invariant
# ---------------------------------------------------------------------------


def test_require_workspace_scope_always_allows_with_mismatch() -> None:
    """A call with a mismatched workspace_id still returns allowed=True (advisory mode)."""
    identity = AuthIdentity(
        user_id="alice",
        workspace_id="workspace_A",
        roles=("researcher",),
    )
    record = {"workspace_id": "workspace_B", "catalog_item_id": "ci_mismatch_001"}

    result = require_workspace_scope(
        identity, record, record_type="catalog_item", record_id="ci_mismatch_001"
    )

    assert isinstance(result, WorkspaceScopeResult)
    assert result.allowed is True


def test_require_workspace_scope_allows_with_null_workspace_id() -> None:
    """Advisory mode: null workspace_id on record returns allowed=True."""
    identity = AuthIdentity(
        user_id="bob",
        workspace_id="default",
        roles=("viewer",),
    )
    record: dict = {"catalog_item_id": "ci_null_ws"}  # no workspace_id key

    result = require_workspace_scope(
        identity, record, record_type="catalog_item"
    )

    assert result.allowed is True


def test_require_workspace_scope_single_operator_trust() -> None:
    """identity=None (single-operator-trust) always returns allowed=True, no log."""
    record = {"workspace_id": "some_workspace", "report_draft_id": "rpt_trust"}

    result = require_workspace_scope(None, record, record_type="draft")

    assert result.allowed is True
    assert result.reason == "single_operator_trust"


def test_require_workspace_scope_workspace_match_no_log(caplog) -> None:
    """Exact workspace_id match: allowed=True, reason=workspace_match, no advisory log."""
    identity = AuthIdentity(
        user_id="carol",
        workspace_id="ws_prod",
        roles=("admin",),
    )
    record = {"workspace_id": "ws_prod", "catalog_item_id": "ci_match_001"}

    with caplog.at_level(logging.WARNING, logger="research_foundry.api.auth.scope"):
        result = require_workspace_scope(
            identity, record, record_type="catalog_item", record_id="ci_match_001"
        )

    assert result.allowed is True
    assert result.reason == "workspace_match"
    # No advisory warning should be emitted on an exact match.
    advisory_records = [
        r for r in caplog.records
        if "workspace_scope_advisory_mismatch" in r.getMessage()
    ]
    assert advisory_records == []


# ---------------------------------------------------------------------------
# WKSP-304 Phase 4 (TASK-4.1) — enforcing mode + D3 ordering proof
# ---------------------------------------------------------------------------


def test_require_workspace_scope_identity_none_never_resolves_enforcement_flag() -> None:
    """D3 ordering proof (Critical, no partial credit).

    When ``identity`` is ``None`` the ``identity is None`` short-circuit must
    be the literal first statement executed — evaluated and returned from
    BEFORE ``resolve_enforcement`` is ever read or called. This test would
    FAIL if that short-circuit were reordered to run after the flag lookup:
    the ``side_effect`` raises immediately on any call, and
    ``assert_not_called()`` is a second, independent proof of the same
    invariant.
    """
    resolver = Mock(
        side_effect=AssertionError(
            "resolve_enforcement must NEVER be invoked when identity is None "
            "(WKSP-304 D3 ordering invariant violated)"
        )
    )
    record = {"workspace_id": "ws_a", "catalog_item_id": "ci_ordering_proof"}

    result = require_workspace_scope(
        None,
        record,
        record_type="catalog_item",
        resolve_enforcement=resolver,
    )

    assert result.allowed is True
    assert result.reason == "single_operator_trust"
    resolver.assert_not_called()


def test_require_workspace_scope_enforcing_mismatch_denies() -> None:
    """Enforcing mode + cross-workspace mismatch -> allowed=False."""
    identity = AuthIdentity(
        user_id="alice", workspace_id="workspace_A", roles=("researcher",)
    )
    record = {"workspace_id": "workspace_B", "catalog_item_id": "ci_enforce_mismatch"}

    result = require_workspace_scope(
        identity,
        record,
        record_type="catalog_item",
        record_id="ci_enforce_mismatch",
        resolve_enforcement=lambda: True,
    )

    assert result.allowed is False
    assert result.reason == "workspace_mismatch_denied"


def test_require_workspace_scope_enforcing_match_allows() -> None:
    """Enforcing mode + exact workspace_id match -> allowed=True."""
    identity = AuthIdentity(user_id="carol", workspace_id="ws_prod", roles=("admin",))
    record = {"workspace_id": "ws_prod", "catalog_item_id": "ci_enforce_match"}

    result = require_workspace_scope(
        identity,
        record,
        record_type="catalog_item",
        record_id="ci_enforce_match",
        resolve_enforcement=lambda: True,
    )

    assert result.allowed is True
    assert result.reason == "workspace_match"


def test_require_workspace_scope_enforcing_null_workspace_id_denies() -> None:
    """Enforcing mode + record.workspace_id is None -> treated as mismatch, denies.

    Never defaults to allowed (AC-3 / D3): a pre-migration record missing a
    workspace_id field must not slip through enforcement.
    """
    identity = AuthIdentity(
        user_id="dave", workspace_id="ws_tenant_1", roles=("researcher",)
    )
    record: dict = {"catalog_item_id": "ci_enforce_null"}  # no workspace_id key

    result = require_workspace_scope(
        identity,
        record,
        record_type="catalog_item",
        record_id="ci_enforce_null",
        resolve_enforcement=lambda: True,
    )

    assert result.allowed is False
    assert result.reason == "workspace_mismatch_denied"


def test_require_workspace_scope_advisory_explicit_false_unchanged(caplog) -> None:
    """resolve_enforcement resolving falsy -> byte-for-byte pre-Phase-4 advisory behaviour."""
    identity = AuthIdentity(user_id="erin", workspace_id="ws_1", roles=("viewer",))
    record = {"workspace_id": "ws_2", "catalog_item_id": "ci_advisory_explicit"}

    with caplog.at_level(logging.WARNING, logger="research_foundry.api.auth.scope"):
        result = require_workspace_scope(
            identity,
            record,
            record_type="catalog_item",
            record_id="ci_advisory_explicit",
            resolve_enforcement=lambda: False,
        )

    assert result.allowed is True
    assert result.reason == "advisory_mode"
    advisory_records = [
        r
        for r in caplog.records
        if "workspace_scope_advisory_mismatch" in r.getMessage()
    ]
    assert len(advisory_records) == 1


# ---------------------------------------------------------------------------
# Advisory mismatch log — structured fields (WKSP-301 requirement)
# ---------------------------------------------------------------------------


def test_advisory_mismatch_log_has_required_fields(caplog) -> None:
    """Advisory mismatch emits a JSON log with trace_id, record_type, record_id."""
    identity = AuthIdentity(
        user_id="dave",
        workspace_id="ws_tenant_1",
        roles=("researcher",),
    )
    record = {
        "workspace_id": "ws_tenant_2",
        "catalog_item_id": "ci_crossws_007",
    }

    with caplog.at_level(logging.WARNING, logger="research_foundry.api.auth.scope"):
        result = require_workspace_scope(
            identity,
            record,
            record_type="catalog_item",
            record_id="ci_crossws_007",
        )

    assert result.allowed is True

    # Find the advisory log record.
    advisory_records = [
        r for r in caplog.records
        if "workspace_scope_advisory_mismatch" in r.getMessage()
    ]
    assert len(advisory_records) == 1, (
        "Expected exactly 1 advisory_mismatch log record"
    )

    log_payload = json.loads(advisory_records[0].getMessage())

    # Mandatory fields per WKSP-301 spec.
    assert log_payload["event"] == "workspace_scope_advisory_mismatch"
    assert "trace_id" in log_payload and len(log_payload["trace_id"]) > 0
    assert log_payload["record_type"] == "catalog_item"
    assert log_payload["record_id"] == "ci_crossws_007"


def test_advisory_null_workspace_id_log_fields(caplog) -> None:
    """Null workspace_id on record also emits the advisory log with required fields."""
    identity = AuthIdentity(
        user_id="eve",
        workspace_id="default",
        roles=("viewer",),
    )
    record = {"report_draft_id": "rpt_no_ws", "title": "Untitled"}  # no workspace_id

    with caplog.at_level(logging.WARNING, logger="research_foundry.api.auth.scope"):
        require_workspace_scope(
            identity,
            record,
            record_type="draft",
            record_id="rpt_no_ws",
        )

    advisory_records = [
        r for r in caplog.records
        if "workspace_scope_advisory_mismatch" in r.getMessage()
    ]
    assert len(advisory_records) == 1

    payload = json.loads(advisory_records[0].getMessage())
    assert payload["event"] == "workspace_scope_advisory_mismatch"
    assert payload["record_type"] == "draft"
    assert payload["record_id"] == "rpt_no_ws"
    assert "trace_id" in payload
    assert payload["record_workspace_id"] is None


# ---------------------------------------------------------------------------
# Dataclass schema sanity checks (WKSP-302/303 shared schema)
# ---------------------------------------------------------------------------


def test_backfill_report_defaults() -> None:
    """BackfillReport has sane zero-value defaults for WKSP-302/303 reuse."""
    report = BackfillReport()
    assert report.total_attempted == 0
    assert report.total_succeeded == 0
    assert report.total_failed == 0
    assert report.manifest == []
    assert report.target_workspace_id == "default"


def test_backfill_manifest_entry_fields() -> None:
    """BackfillManifestEntry stores all required fields."""
    entry = BackfillManifestEntry(
        record_type="draft",
        record_id="rpt_abc",
        prior_workspace_id=None,
        prior_created_by=None,
        new_workspace_id="default",
    )
    assert entry.record_type == "draft"
    assert entry.record_id == "rpt_abc"
    assert entry.prior_workspace_id is None
    assert entry.new_workspace_id == "default"
    assert entry.migration_run_id == ""  # backward-compat default


# ---------------------------------------------------------------------------
# WKSP-302 acceptance criteria — backfill + rollback
# ---------------------------------------------------------------------------


def _plant_simple_draft(
    paths: FoundryPaths,
    draft_id: str,
    *,
    workspace_id: str | None = None,
    created_by: str | None = None,
) -> Path:
    """Minimal draft.yaml without timestamp fields for YAML-round-trip stability.

    PyYAML safe_load auto-converts ISO-8601 timestamp strings to datetime
    objects, which then serialize with a different format — breaking byte-hash
    equality.  This helper only uses fields that round-trip identically so the
    ``test_backfill_rollback_round_trip`` byte-hash invariant holds.
    """
    draft_dir = paths.report_drafts / draft_id
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "draft.yaml"
    payload: dict = {
        "schema_version": 1,
        "report_draft_id": draft_id,
        "title": f"Legacy Draft {draft_id}",
        "status": "draft",
    }
    if workspace_id is not None:
        payload["workspace_id"] = workspace_id
    if created_by is not None:
        payload["created_by"] = created_by
    dump_yaml(payload, draft_path)
    return draft_path


def test_backfill_rollback_round_trip(tmp_foundry: FoundryPaths) -> None:
    """backfill() then rollback() leaves every touched draft.yaml byte-identical.

    Uses minimal fixtures (no auto-converted YAML timestamps) to guarantee
    that the YAML serialization round-trips without format changes.
    """
    n = 4
    draft_ids = [f"rpt_rtrip_{i:02d}" for i in range(n)]
    draft_paths = [_plant_simple_draft(tmp_foundry, did) for did in draft_ids]

    # Snapshot content hashes BEFORE backfill.
    before_hashes = {p: _file_hash(p) for p in draft_paths}

    # Forward migration.
    report = backfill(tmp_foundry)
    assert report.total_succeeded == n
    assert report.total_failed == 0
    assert report.migration_run_id != ""

    # All drafts now have workspace_id set.
    for p in draft_paths:
        data = __import__(
            "research_foundry.yamlio", fromlist=["load_yaml"]
        ).load_yaml(p)
        assert data.get("workspace_id") == "default"

    # Rollback.
    rb = rollback(tmp_foundry, report.migration_run_id)
    assert rb.total_reverted_drafts == n
    assert rb.total_failed == 0
    assert rb.is_dry_run is False

    # After rollback every draft.yaml must be byte-identical to pre-backfill.
    for p in draft_paths:
        assert _file_hash(p) == before_hashes[p], (
            f"rollback did not restore {p.name} to its original bytes"
        )


def test_rollback_skips_non_null_records(tmp_foundry: FoundryPaths) -> None:
    """backfill() never touches a draft whose workspace_id is already set.

    The manifest must contain ONLY the null-workspace_id drafts.  The
    non-null draft's content must be unchanged both after backfill and
    after rollback.
    """
    # Draft A: null workspace_id — target of backfill.
    draft_a = _plant_simple_draft(tmp_foundry, "rpt_skip_a")

    # Draft B: non-null workspace_id — must be skipped throughout.
    draft_b = _plant_simple_draft(tmp_foundry, "rpt_skip_b", workspace_id="ws_existing")
    hash_b_before = _file_hash(draft_b)

    report = backfill(tmp_foundry)

    # Only draft A was touched.
    assert report.total_succeeded == 1
    assert len(report.manifest) == 1
    assert report.manifest[0].record_id == "rpt_skip_a"

    # Draft B is unchanged after backfill.
    assert _file_hash(draft_b) == hash_b_before, "backfill must not touch draft_b"

    # Rollback draft A.
    rb = rollback(tmp_foundry, report.migration_run_id)
    assert rb.total_reverted_drafts == 1

    # Draft B is still unchanged after rollback.
    assert _file_hash(draft_b) == hash_b_before, "rollback must not touch draft_b"


def test_rollback_manifest_safety(tmp_foundry: FoundryPaths) -> None:
    """rollback() ONLY reverts records listed in the original manifest.

    A draft created POST-backfill (with workspace_id='default') was NOT part
    of the original migration run; rollback must not touch it.
    """
    from research_foundry.yamlio import load_yaml as _load_yaml

    # Draft A: migrated by backfill.
    _plant_simple_draft(tmp_foundry, "rpt_safety_a")

    # Forward migration.
    report = backfill(tmp_foundry)
    assert report.total_succeeded == 1

    # POST-BACKFILL: plant a new draft B that happens to have workspace_id='default'
    # (simulating legitimate post-migration activity — NOT created by the backfill run).
    draft_b = _plant_simple_draft(
        tmp_foundry, "rpt_safety_b", workspace_id="default"
    )
    hash_b_pre_rollback = _file_hash(draft_b)

    # Rollback the ORIGINAL migration run (which only knew about draft A).
    rb = rollback(tmp_foundry, report.migration_run_id)

    # Draft A was reverted (it was in the manifest).
    assert rb.total_reverted_drafts == 1

    # Draft B must NOT be touched — it was not in the original manifest.
    assert _file_hash(draft_b) == hash_b_pre_rollback, (
        "rollback must not revert records absent from the original manifest"
    )
    data_b = _load_yaml(draft_b)
    assert data_b.get("workspace_id") == "default", (
        "draft_b workspace_id must remain 'default' after rollback"
    )


# ---------------------------------------------------------------------------
# WKSP-303 acceptance criteria
# ---------------------------------------------------------------------------


def test_backfill_idempotency(tmp_foundry: FoundryPaths) -> None:
    """Running backfill() twice: second run produces a BackfillReport with 0 records touched.

    All drafts are already stamped after the first run, so the second invocation
    skips every draft and writes an empty manifest — no duplicate records.
    """
    n = 3
    for i in range(n):
        _plant_simple_draft(tmp_foundry, f"rpt_idem_{i:02d}")

    # First run: stamps all n drafts.
    first = backfill(tmp_foundry)
    assert first.total_succeeded == n
    assert first.total_failed == 0
    assert first.migration_run_id != ""

    # Second run: all drafts already have workspace_id — nothing to do.
    second = backfill(tmp_foundry)
    assert second.total_attempted == 0
    assert second.total_succeeded == 0
    assert second.total_failed == 0
    assert second.manifest == [], (
        "Second backfill must not include any manifest entries (all already migrated)"
    )


def test_dry_run_parity_with_backfill(tmp_foundry: FoundryPaths) -> None:
    """dry_run()'s drafts_missing_workspace_id prediction equals backfill()'s actual count.

    Plant 2 drafts without workspace_id and 1 with. dry_run() predicts 2; backfill()
    succeeds on exactly 2 — proving the dry-run estimate matches the real backfill.
    """
    _plant_simple_draft(tmp_foundry, "rpt_par_a")
    _plant_simple_draft(tmp_foundry, "rpt_par_b")
    _plant_simple_draft(tmp_foundry, "rpt_par_c", workspace_id="already_set")

    preview = dry_run(tmp_foundry)
    assert preview.drafts_missing_workspace_id == 2

    bf = backfill(tmp_foundry)
    assert bf.total_succeeded == preview.drafts_missing_workspace_id, (
        f"backfill touched {bf.total_succeeded} records but dry_run predicted "
        f"{preview.drafts_missing_workspace_id}"
    )


def test_cross_workspace_read_still_succeeds_after_backfill(tmp_foundry: FoundryPaths) -> None:
    """After backfill(), require_workspace_scope() still returns allowed=True.

    Confirms backfill is additive-only and does NOT flip the advisory gate into
    enforcement mode. Both single-operator-trust (identity=None) and a cross-workspace
    identity must still see allowed=True (advisory mode unchanged by migration).
    """
    _plant_simple_draft(tmp_foundry, "rpt_xws_a")
    _plant_simple_draft(tmp_foundry, "rpt_xws_b")

    bf = backfill(tmp_foundry)
    assert bf.total_succeeded == 2

    # Single-operator-trust (identity=None): always allowed.
    record = {"workspace_id": "default", "report_draft_id": "rpt_xws_a"}
    result_none = require_workspace_scope(None, record, record_type="draft")
    assert result_none.allowed is True
    assert result_none.reason == "single_operator_trust"

    # Cross-workspace identity: advisory mode — still allowed.
    identity = AuthIdentity(
        user_id="frank",
        workspace_id="other_workspace",
        roles=("researcher",),
    )
    record_migrated = {"workspace_id": "default", "report_draft_id": "rpt_xws_a"}
    result_cross = require_workspace_scope(
        identity, record_migrated, record_type="draft", record_id="rpt_xws_a"
    )
    assert result_cross.allowed is True, (
        "backfill must not flip advisory mode to enforcement: cross-workspace read must still pass"
    )


# ---------------------------------------------------------------------------
# DEFECT P1/P2 regression tests
# ---------------------------------------------------------------------------


def test_backfill_catalog_only_workspace(tmp_foundry: FoundryPaths) -> None:
    """Regression P1: backfill() triggers catalog rebuild even when 0 drafts need stamping.

    When all drafts already have workspace_id but catalog.db is still pre-v3
    (no workspace_id column), the old fast-path in the CLI would return early
    without calling backfill().  This test verifies that backfill() itself
    always calls the catalog rebuild and reports catalog_rebuild_ok=True on
    success — regardless of how many drafts were stamped.
    """
    # Plant drafts that ALREADY have workspace_id (0 need backfill).
    _plant_simple_draft(tmp_foundry, "rpt_catonly_a", workspace_id="default")
    _plant_simple_draft(tmp_foundry, "rpt_catonly_b", workspace_id="default")
    # Plant a pre-v3 catalog.db (no workspace_id column in schema).
    _plant_catalog_db(tmp_foundry, row_count=2)

    report = backfill(tmp_foundry)

    # No drafts were mutated (all already migrated).
    assert report.total_attempted == 0
    assert report.total_succeeded == 0, "expected 0 draft mutations (all already migrated)"

    # Catalog rebuild was still triggered and succeeded.
    assert report.catalog_rebuild_ok is True, (
        "catalog_rebuild_ok should be True when rebuild succeeds"
    )
    assert report.catalog_rebuild_error is None


def test_backfill_rebuild_failure_surfaced(tmp_foundry: FoundryPaths, monkeypatch) -> None:
    """Regression P2: BackfillReport exposes catalog rebuild failure without hiding draft results.

    When _cs.rebuild() raises, backfill() must:
    - Set catalog_rebuild_ok=False and catalog_rebuild_error to a non-empty string.
    - Still report total_succeeded > 0 (draft stamping completes before catalog rebuild).
    """
    import research_foundry.services.catalog_service as _catalog_service

    # Plant drafts that need workspace_id so total_succeeded > 0.
    _plant_simple_draft(tmp_foundry, "rpt_rbfail_a")
    _plant_simple_draft(tmp_foundry, "rpt_rbfail_b")

    # Monkeypatch catalog_service.rebuild to raise.
    def _failing_rebuild(paths: FoundryPaths) -> None:
        raise RuntimeError("simulated catalog rebuild failure")

    monkeypatch.setattr(_catalog_service, "rebuild", _failing_rebuild)

    report = backfill(tmp_foundry)

    # Draft stamping still succeeded before the catalog rebuild was attempted.
    assert report.total_succeeded == 2, "drafts should be stamped before catalog rebuild"
    assert report.total_failed == 0

    # Rebuild failure is captured in the report — not silently swallowed.
    assert report.catalog_rebuild_ok is False, (
        "catalog_rebuild_ok should be False when rebuild raises"
    )
    assert report.catalog_rebuild_error is not None
    assert len(report.catalog_rebuild_error) > 0
    assert "simulated catalog rebuild failure" in report.catalog_rebuild_error


def test_rollback_dry_run_no_writes(tmp_foundry: FoundryPaths) -> None:
    """rollback(dry_run=True) performs ZERO writes — all files are untouched."""
    n = 3
    draft_paths = [
        _plant_simple_draft(tmp_foundry, f"rpt_dryrl_{i:02d}") for i in range(n)
    ]

    report = backfill(tmp_foundry)
    assert report.total_succeeded == n

    # Snapshot after backfill.
    after_backfill_hashes = {p: _file_hash(p) for p in draft_paths}

    # Dry-run rollback.
    rb = rollback(tmp_foundry, report.migration_run_id, dry_run=True)
    assert rb.is_dry_run is True
    assert rb.total_reverted_drafts == n
    assert rb.total_failed == 0

    # Files are unchanged (no writes during dry-run).
    for p in draft_paths:
        assert _file_hash(p) == after_backfill_hashes[p], (
            f"dry_run rollback must not write {p.name}"
        )
        # workspace_id should still be set (not reverted during dry-run).
        from research_foundry.yamlio import load_yaml as _ly
        data = _ly(p)
        assert data.get("workspace_id") == "default"
