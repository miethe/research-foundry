"""Unit tests for audit_service.py — AUDIT-001.

Covers:
- record_event / list_events / get_event against a tmp-dir rbac.db fixture
- Fault-injection: forced write failure never propagates, logs ERROR, returns None
- Taxonomy completeness: all 6 mutation_type values present in MUTATION_TYPES
- Idempotent schema: bootstrap twice on same path, no error
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service
from research_foundry.services.audit_service import (
    MUTATION_TYPES,
    AuditEvent,
    get_event,
    list_events,
    record_event,
)
from research_foundry.services.rbac_store import bootstrap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def paths(tmp_path: Path) -> FoundryPaths:
    """Return a FoundryPaths rooted at a temporary directory with rbac.db bootstrapped."""
    fp = FoundryPaths(root=tmp_path)
    # Ensure .rf_state/ exists and schema is applied (including audit tables).
    conn = bootstrap(fp)
    conn.close()
    return fp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(**kwargs: Any) -> AuditEvent:
    defaults: dict[str, Any] = {
        "mutation_type": "catalog_mutation",
        "action": "import_run",
        "target_ref": "run_abc123",
    }
    defaults.update(kwargs)
    return AuditEvent(**defaults)


# ---------------------------------------------------------------------------
# record_event: basic write and return value
# ---------------------------------------------------------------------------


class TestRecordEventBasic:
    def test_returns_string_id(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event())
        assert isinstance(event_id, str)
        assert len(event_id) > 0

    def test_row_persisted_in_db(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event(action="import_run", target_ref="r1"))
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        assert row["audit_event_id"] == event_id
        assert row["mutation_type"] == "catalog_mutation"
        assert row["action"] == "import_run"
        assert row["target_ref"] == "r1"

    def test_created_at_is_iso_utc(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event())
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        # Should end with 'Z' (UTC marker)
        assert row["created_at"].endswith("Z")

    def test_optional_fields_nullable(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event())
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        for field in ("actor_user_id", "actor_workspace_id", "source_ref",
                      "policy_snapshot", "error_detail", "trace_id", "span_id"):
            assert row[field] is None

    def test_all_fields_stored(self, paths: FoundryPaths) -> None:
        event = AuditEvent(
            mutation_type="report_edit",
            action="create_draft",
            target_ref="draft_xyz",
            actor_user_id="usr_alice",
            actor_workspace_id="ws_main",
            source_ref="cli",
            policy_snapshot={"auth_provider": "local_static", "role": "researcher"},
            result="success",
            error_detail=None,
            trace_id="trace-111",
            span_id="span-222",
        )
        event_id = record_event(paths, event)
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        assert row["mutation_type"] == "report_edit"
        assert row["actor_user_id"] == "usr_alice"
        assert row["actor_workspace_id"] == "ws_main"
        assert row["source_ref"] == "cli"
        assert row["policy_snapshot"] == {"auth_provider": "local_static", "role": "researcher"}
        assert row["trace_id"] == "trace-111"
        assert row["span_id"] == "span-222"

    def test_policy_snapshot_round_trips_as_dict(self, paths: FoundryPaths) -> None:
        snapshot = {"sensitivity_threshold": 3, "role": "admin", "provider": "clerk"}
        event_id = record_event(paths, _make_event(policy_snapshot=snapshot))
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        assert row["policy_snapshot"] == snapshot

    def test_result_default_is_success(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event())
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        assert row["result"] == "success"

    def test_result_failure(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event(result="failure", error_detail="disk full"))
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        assert row["result"] == "failure"
        assert row["error_detail"] == "disk full"

    def test_result_denied(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event(result="denied"))
        assert event_id is not None
        row = get_event(paths, event_id)
        assert row is not None
        assert row["result"] == "denied"


# ---------------------------------------------------------------------------
# list_events: pagination and filtering
# ---------------------------------------------------------------------------


class TestListEvents:
    def test_returns_envelope_shape(self, paths: FoundryPaths) -> None:
        result = list_events(paths)
        assert "items" in result
        assert "next_cursor" in result
        assert "total_hint" in result

    def test_empty_store_returns_empty_items(self, paths: FoundryPaths) -> None:
        result = list_events(paths)
        assert result["items"] == []
        assert result["next_cursor"] is None

    def test_single_event_returned(self, paths: FoundryPaths) -> None:
        record_event(paths, _make_event())
        result = list_events(paths)
        assert len(result["items"]) == 1

    def test_multiple_events_most_recent_first(self, paths: FoundryPaths) -> None:
        for i in range(3):
            record_event(paths, _make_event(target_ref=f"run_{i}", action="import_run"))
        result = list_events(paths)
        items = result["items"]
        assert len(items) == 3
        # Most-recent-first: created_at descending
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True) or len(set(timestamps)) == 1

    def test_filter_by_mutation_type(self, paths: FoundryPaths) -> None:
        record_event(paths, _make_event(mutation_type="catalog_mutation"))
        record_event(paths, _make_event(mutation_type="report_edit", action="create_draft"))
        result = list_events(paths, mutation_type="catalog_mutation")
        assert all(item["mutation_type"] == "catalog_mutation" for item in result["items"])
        assert len(result["items"]) == 1

    def test_filter_by_actor_user_id(self, paths: FoundryPaths) -> None:
        record_event(paths, _make_event(actor_user_id="usr_alice"))
        record_event(paths, _make_event(actor_user_id="usr_bob", action="create_draft",
                                        mutation_type="report_edit"))
        result = list_events(paths, actor_user_id="usr_alice")
        assert len(result["items"]) == 1
        assert result["items"][0]["actor_user_id"] == "usr_alice"

    def test_filter_by_workspace_id(self, paths: FoundryPaths) -> None:
        record_event(paths, _make_event(actor_workspace_id="ws_a"))
        record_event(paths, _make_event(actor_workspace_id="ws_b", action="create_draft",
                                        mutation_type="report_edit"))
        result = list_events(paths, workspace_id="ws_a")
        assert len(result["items"]) == 1
        assert result["items"][0]["actor_workspace_id"] == "ws_a"

    def test_limit_respected(self, paths: FoundryPaths) -> None:
        for i in range(5):
            record_event(paths, _make_event(target_ref=f"run_{i}"))
        result = list_events(paths, limit=3)
        assert len(result["items"]) == 3

    def test_next_cursor_present_when_more(self, paths: FoundryPaths) -> None:
        for i in range(5):
            record_event(paths, _make_event(target_ref=f"run_{i}"))
        result = list_events(paths, limit=3)
        assert result["next_cursor"] is not None

    def test_next_cursor_none_when_all_fit(self, paths: FoundryPaths) -> None:
        for i in range(3):
            record_event(paths, _make_event(target_ref=f"run_{i}"))
        result = list_events(paths, limit=10)
        assert result["next_cursor"] is None

    def test_cursor_pagination_no_overlap(self, paths: FoundryPaths) -> None:
        for i in range(6):
            record_event(paths, _make_event(target_ref=f"run_{i}"))
        page1 = list_events(paths, limit=3)
        assert page1["next_cursor"] is not None
        page2 = list_events(paths, limit=3, cursor=page1["next_cursor"])
        ids_page1 = {item["audit_event_id"] for item in page1["items"]}
        ids_page2 = {item["audit_event_id"] for item in page2["items"]}
        assert ids_page1.isdisjoint(ids_page2), "Paginated pages must not overlap"

    def test_cursor_pagination_covers_all(self, paths: FoundryPaths) -> None:
        for i in range(6):
            record_event(paths, _make_event(target_ref=f"run_{i}"))
        all_ids: set[str] = set()
        cursor = None
        while True:
            page = list_events(paths, limit=3, cursor=cursor)
            for item in page["items"]:
                all_ids.add(item["audit_event_id"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert len(all_ids) == 6


# ---------------------------------------------------------------------------
# get_event: hit and miss
# ---------------------------------------------------------------------------


class TestGetEvent:
    def test_returns_dict_for_known_id(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event())
        assert event_id is not None
        row = get_event(paths, event_id)
        assert isinstance(row, dict)

    def test_returns_none_for_unknown_id(self, paths: FoundryPaths) -> None:
        result = get_event(paths, "nonexistent-id-000")
        assert result is None


# ---------------------------------------------------------------------------
# Fault injection: forced write failure
# ---------------------------------------------------------------------------


class TestFaultInjection:
    """Forcing the internal write to raise must: (a) not propagate, (b) log ERROR, (c) return None.

    We patch ``audit_service._record_event_inner`` (the private implementation
    function) to raise a RuntimeError.  This is more reliable than patching
    ``sqlite3.Connection.execute``, which is a C-level immutable type in
    Python 3.14 and cannot be monkey-patched.
    """

    def test_no_exception_propagates(self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(p: object, e: object) -> object:
            raise RuntimeError("simulated disk full")

        monkeypatch.setattr(audit_service, "_record_event_inner", _raise)
        # Must not raise
        result = record_event(paths, _make_event())
        assert result is None

    def test_structured_error_is_logged(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        def _raise(p: object, e: object) -> object:
            raise RuntimeError("simulated disk full")

        monkeypatch.setattr(audit_service, "_record_event_inner", _raise)
        with caplog.at_level(logging.ERROR, logger="research_foundry.services.audit_service"):
            record_event(paths, _make_event())

        assert any("audit row dropped" in r.message for r in caplog.records), (
            "Expected a structured ERROR log containing 'audit row dropped'"
        )

    def test_returns_none_on_failure(self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(p: object, e: object) -> object:
            raise RuntimeError("simulated disk full")

        monkeypatch.setattr(audit_service, "_record_event_inner", _raise)
        result = record_event(paths, _make_event())
        assert result is None


# ---------------------------------------------------------------------------
# Taxonomy completeness
# ---------------------------------------------------------------------------


class TestTaxonomyCompleteness:
    EXPECTED_MUTATION_TYPES = {
        "catalog_mutation",
        "report_edit",
        "agent_job_launched",
        "artifact_accepted",
        "publish_preview",
        "writeback",
    }

    def test_all_six_mutation_types_present(self) -> None:
        assert self.EXPECTED_MUTATION_TYPES == MUTATION_TYPES

    def test_mutation_types_is_frozenset(self) -> None:
        assert isinstance(MUTATION_TYPES, frozenset)

    def test_agent_job_launched_reserved(self) -> None:
        """agent_job_launched is reserved even though no call-site exists yet (N/A until P4)."""
        assert "agent_job_launched" in MUTATION_TYPES

    def test_no_extra_mutation_types(self) -> None:
        assert len(MUTATION_TYPES) == 6


# ---------------------------------------------------------------------------
# Idempotent schema / bootstrap
# ---------------------------------------------------------------------------


class TestIdempotentSchema:
    def test_bootstrap_twice_no_error(self, tmp_path: Path) -> None:
        fp = FoundryPaths(root=tmp_path)
        conn1 = bootstrap(fp)
        conn1.close()
        conn2 = bootstrap(fp)
        conn2.close()  # Should not raise

    def test_record_after_double_bootstrap(self, tmp_path: Path) -> None:
        fp = FoundryPaths(root=tmp_path)
        conn1 = bootstrap(fp)
        conn1.close()
        conn2 = bootstrap(fp)
        conn2.close()
        event_id = record_event(fp, _make_event())
        assert event_id is not None

    def test_audit_event_table_exists_after_bootstrap(self, tmp_path: Path) -> None:
        fp = FoundryPaths(root=tmp_path)
        conn = bootstrap(fp)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_event'"
            ).fetchall()
            assert len(rows) == 1
        finally:
            conn.close()

    def test_audit_health_table_exists_after_bootstrap(self, tmp_path: Path) -> None:
        fp = FoundryPaths(root=tmp_path)
        conn = bootstrap(fp)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_health'"
            ).fetchall()
            assert len(rows) == 1
        finally:
            conn.close()

    def test_schema_version_is_2(self, tmp_path: Path) -> None:
        fp = FoundryPaths(root=tmp_path)
        conn = bootstrap(fp)
        try:
            (version,) = conn.execute("PRAGMA user_version").fetchone()
            assert version == 2
        finally:
            conn.close()
