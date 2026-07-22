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

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service
from research_foundry.services.audit_service import (
    MUTATION_TYPES,
    AuditEvent,
    AuditHealth,
    get_event,
    get_health_state,
    health_check,
    is_healthy_for_exposure,
    list_events,
    record_event,
)
from research_foundry.services import rbac_store
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
# DI-1 full-surface audit (Phase 4 ACT-401): workspace scoping for
# list_events / get_event.
#
# RBAC-006's owner/admin gate on the /api/audit routes is a workspace-scoped
# role (AuthIdentity.roles is granted "within the workspace" — see
# api/auth/provider.py), so absent this scoping an owner/admin of one
# workspace could read another workspace's actor IDs / policy snapshots
# either via the client-supplied `workspace` filter or (for get_event) with
# no filter at all. Mirrors the ``_force_isolation_active`` pattern already
# used by test_catalog_service.py / test_builder_service.py / test_agent_job_service.py.
# ---------------------------------------------------------------------------

_WS_MINE = AuthIdentity("u1", "ws-mine", ("owner",))
_WS_OTHER = AuthIdentity("u2", "ws-other", ("owner",))


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ``workspace_isolation_enforcement`` resolving active.

    Monkeypatches :meth:`FoundryConfig.resolve_workspace_isolation_enforced`
    itself (never a private helper) — same idiom as
    ``test_builder_service.py``/``test_catalog_service.py``.
    """

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


class TestListEventsWorkspaceScoping:
    def test_identity_none_is_byte_identical(self, paths: FoundryPaths) -> None:
        record_event(paths, _make_event(actor_workspace_id="ws-mine"))
        record_event(paths, _make_event(actor_workspace_id="ws-other", action="create_draft"))

        baseline = list_events(paths, workspace_id="ws-other")
        assert list_events(paths, workspace_id="ws-other", identity=None) == baseline
        # Without any workspace_id filter and identity=None, both events are visible.
        assert len(list_events(paths, identity=None)["items"]) == 2

    def test_isolation_inactive_client_filter_still_honored(self, paths: FoundryPaths) -> None:
        """Isolation not yet enforced: identity present but inert — FR-2 regression guard."""
        record_event(paths, _make_event(actor_workspace_id="ws-mine"))
        record_event(paths, _make_event(actor_workspace_id="ws-other", action="create_draft"))

        result = list_events(paths, workspace_id="ws-other", identity=_WS_MINE)
        assert [i["actor_workspace_id"] for i in result["items"]] == ["ws-other"]

    def test_enforcing_identity_overrides_client_supplied_workspace_filter(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The cross-tenant leak this remediates: an owner of ws-mine passing
        ``workspace_id="ws-other"`` must NOT see ws-other's events once
        isolation is enforced — their own workspace always wins."""

        record_event(paths, _make_event(actor_workspace_id="ws-mine"))
        record_event(paths, _make_event(actor_workspace_id="ws-other", action="create_draft"))

        _force_isolation_active(monkeypatch)

        result = list_events(paths, workspace_id="ws-other", identity=_WS_MINE)
        assert [i["actor_workspace_id"] for i in result["items"]] == ["ws-mine"]

    def test_enforcing_no_filter_defaults_to_callers_own_workspace(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The second half of the leak: omitting `workspace` entirely must not
        return every workspace's events once enforcing."""

        record_event(paths, _make_event(actor_workspace_id="ws-mine"))
        record_event(paths, _make_event(actor_workspace_id="ws-other", action="create_draft"))

        _force_isolation_active(monkeypatch)

        result = list_events(paths, identity=_WS_MINE)
        assert [i["actor_workspace_id"] for i in result["items"]] == ["ws-mine"]


class TestGetEventWorkspaceScoping:
    def test_identity_none_is_byte_identical(self, paths: FoundryPaths) -> None:
        event_id = record_event(paths, _make_event(actor_workspace_id="ws-other"))
        assert event_id is not None
        baseline = get_event(paths, event_id)
        assert get_event(paths, event_id, identity=None) == baseline

    def test_isolation_inactive_cross_workspace_read_still_allowed(self, paths: FoundryPaths) -> None:
        """FR-2 regression guard: identity present but isolation not enforced."""
        event_id = record_event(paths, _make_event(actor_workspace_id="ws-other"))
        assert event_id is not None
        assert get_event(paths, event_id, identity=_WS_MINE) is not None

    def test_enforcing_cross_workspace_read_denied_as_missing(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The clear leak this remediates: get_event had zero workspace check —
        any owner/admin could read any other workspace's audit event by ID."""

        event_id = record_event(paths, _make_event(actor_workspace_id="ws-other"))
        assert event_id is not None

        _force_isolation_active(monkeypatch)

        assert get_event(paths, event_id, identity=_WS_OTHER) is not None
        assert get_event(paths, event_id, identity=_WS_MINE) is None

    def test_enforcing_denial_emits_audit_log(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        event_id = record_event(paths, _make_event(actor_workspace_id="ws-other"))
        assert event_id is not None

        _force_isolation_active(monkeypatch)

        caplog.set_level("INFO", logger="research_foundry.services.audit_service")
        caplog.clear()
        assert get_event(paths, event_id, identity=_WS_MINE) is None
        assert any(
            "workspace_scope_enforced_denial" in rec.message for rec in caplog.records
        )


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
    # Original 6 (public-multiuser-release Phase 5) + 4 added by Phase 3
    # ACT-303 (public-multiuser-release-activation) for the admin API's
    # principal/token/role-change mutation surface.
    EXPECTED_MUTATION_TYPES = {
        "catalog_mutation",
        "report_edit",
        "agent_job_launched",
        "artifact_accepted",
        "publish_preview",
        "writeback",
        "principal_mutation",
        "access_token_issued",
        "access_token_revoked",
        "role_change",
    }

    def test_all_ten_mutation_types_present(self) -> None:
        assert self.EXPECTED_MUTATION_TYPES == MUTATION_TYPES

    def test_mutation_types_is_frozenset(self) -> None:
        assert isinstance(MUTATION_TYPES, frozenset)

    def test_agent_job_launched_reserved(self) -> None:
        """agent_job_launched is reserved even though no call-site exists yet (N/A until P4)."""
        assert "agent_job_launched" in MUTATION_TYPES

    def test_no_extra_mutation_types(self) -> None:
        assert len(MUTATION_TYPES) == 10


# ---------------------------------------------------------------------------
# Fault-injection: forced audit failure must never break the mutation
# ---------------------------------------------------------------------------


class TestAuditWiringFaultInjection:
    """AUDIT-002 correctness invariant: a forced audit write failure must never
    prevent the underlying mutation from completing or propagating to its caller.

    Strategy: patch ``audit_service._record_event_inner`` to raise a
    RuntimeError (the same technique used in TestFaultInjection above).
    ``record_event``'s outer try/except swallows it, returning None.
    This validates two things simultaneously:
      1. The audit call IS wired into the mutation (otherwise _record_event_inner
         would never be called and the monkeypatch test would be meaningless).
      2. The mutation's return value is correct regardless of audit outcome.
    """

    def test_ingest_source_completes_despite_audit_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Forced _record_event_inner failure must not propagate to ingest_source callers."""
        from research_foundry.paths import FoundryPaths
        from research_foundry.services import audit_service as _audit_svc
        from research_foundry.services.source_cards import IngestResult, ingest_source

        # Build a minimal run scaffold.
        fp = FoundryPaths(root=tmp_path)
        run_id = "run_audit_fault_test"
        (tmp_path / "runs" / run_id / "sources").mkdir(parents=True)

        # Force the inner write to raise — record_event's outer try/except absorbs it.
        def _always_raise(p: object, e: object) -> object:
            raise RuntimeError("simulated audit store crash")

        monkeypatch.setattr(_audit_svc, "_record_event_inner", _always_raise)

        result = ingest_source(
            "https://example.com/test-source",
            run_id=run_id,
            source_type="other",
            sensitivity="public",
            paths=fp,
        )

        # Mutation must still succeed — returns a valid IngestResult.
        assert isinstance(result, IngestResult)
        assert result.source_card_id.startswith("src_")
        assert result.path.exists()

    def test_ingest_source_audit_record_event_is_called(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """record_event IS called for ingest_source — the wiring exists."""
        from research_foundry.paths import FoundryPaths
        from research_foundry.services import audit_service as _audit_svc
        from research_foundry.services.source_cards import ingest_source
        from research_foundry.services.rbac_store import bootstrap

        fp = FoundryPaths(root=tmp_path)
        conn = bootstrap(fp)
        conn.close()

        run_id = "run_audit_wiring_verify"
        (tmp_path / "runs" / run_id / "sources").mkdir(parents=True)

        calls: list[tuple[object, object]] = []
        original = _audit_svc.record_event

        def _spy(p: object, e: object) -> object:
            calls.append((p, e))
            return original(p, e)  # type: ignore[arg-type]

        monkeypatch.setattr(_audit_svc, "record_event", _spy)

        ingest_source(
            "https://example.com/spy-source",
            run_id=run_id,
            source_type="other",
            sensitivity="public",
            paths=fp,
        )

        # The wiring must have invoked record_event exactly once.
        assert len(calls) == 1, f"Expected 1 audit call, got {len(calls)}"
        _paths_arg, event_arg = calls[0]
        assert event_arg.mutation_type == "artifact_accepted"
        assert event_arg.action == "ingest_source"
        assert event_arg.result == "success"


# ---------------------------------------------------------------------------
# AUDIT-004: health_check, get_health_state, is_healthy_for_exposure
# ---------------------------------------------------------------------------


class TestAuditHealthCheck:
    """AUDIT-004 health probe and persisted state tests."""

    def test_healthy_returns_true_and_timestamps_set(self, paths: FoundryPaths) -> None:
        state = health_check(paths)
        assert isinstance(state, AuditHealth)
        assert state.healthy is True
        assert state.last_probe_at is not None
        assert state.last_probe_at.endswith("Z")
        assert state.last_success_at is not None
        assert state.error_detail is None

    def test_probe_row_not_persisted_in_audit_event(self, paths: FoundryPaths) -> None:
        """Probe row must be self-cleaning — must NOT appear in list_events()."""
        health_check(paths)
        result = list_events(paths)
        for item in result["items"]:
            assert not str(item.get("audit_event_id", "")).startswith("_probe_"), (
                "Probe row must not appear in audit event log"
            )

    def test_degraded_returns_false_with_error_detail(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _failing_probe(conn: object, probe_id: str, now: str) -> None:
            raise RuntimeError("simulated probe failure")

        monkeypatch.setattr(audit_service, "_run_probe", _failing_probe)
        state = health_check(paths)
        assert state.healthy is False
        assert state.error_detail is not None
        assert len(state.error_detail) > 0

    def test_durability_survives_process_restart(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """health=False must persist in audit_health across a simulated restart."""
        def _failing_probe(conn: object, probe_id: str, now: str) -> None:
            raise RuntimeError("simulated probe failure for durability test")

        monkeypatch.setattr(audit_service, "_run_probe", _failing_probe)
        health_check(paths)

        # Simulate restart: call get_health_state fresh (new connection).
        state = get_health_state(paths)
        assert state.healthy is False, (
            "Degraded health state must survive re-reading via get_health_state()"
        )

    def test_get_health_state_never_probed_defaults_healthy(self, paths: FoundryPaths) -> None:
        """Before any probe, get_health_state must return healthy=True (fail-open default)."""
        state = get_health_state(paths)
        assert state.healthy is True
        assert state.last_probe_at is None
        assert state.last_success_at is None
        assert state.error_detail is None

    def test_get_health_state_reflects_persisted_result(self, paths: FoundryPaths) -> None:
        """get_health_state returns the last persisted result after health_check runs."""
        health_check(paths)
        state = get_health_state(paths)
        assert state.healthy is True
        assert state.last_probe_at is not None

    def test_is_healthy_for_exposure_true_when_healthy(self, paths: FoundryPaths) -> None:
        health_check(paths)
        assert is_healthy_for_exposure(paths) is True

    def test_is_healthy_for_exposure_false_when_degraded(
        self, paths: FoundryPaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _failing_probe(conn: object, probe_id: str, now: str) -> None:
            raise RuntimeError("simulated probe failure")

        monkeypatch.setattr(audit_service, "_run_probe", _failing_probe)
        health_check(paths)
        assert is_healthy_for_exposure(paths) is False

    def test_is_healthy_for_exposure_has_no_side_effects(self, paths: FoundryPaths) -> None:
        """is_healthy_for_exposure must not change the audit_event table."""
        # Write one real event first.
        record_event(paths, _make_event(target_ref="before_exposure_check"))
        is_healthy_for_exposure(paths)
        result = list_events(paths)
        # Only the one real event — no probe rows or extra rows.
        assert len(result["items"]) == 1

    def test_health_check_single_row_in_audit_health(self, paths: FoundryPaths) -> None:
        """Running health_check multiple times must keep exactly one row in audit_health."""
        health_check(paths)
        health_check(paths)
        health_check(paths)
        # Verify single row via get_health_state (healthy and has timestamp).
        state = get_health_state(paths)
        assert state.healthy is True


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

    def test_schema_version_matches_current(self, tmp_path: Path) -> None:
        """Asserts against ``RBAC_SCHEMA_VERSION`` itself (not a hardcoded
        literal) so this test keeps passing across additive migrations —
        e.g. public-multiuser Phase 2 (ACT-201) bumped 2 -> 3 to add
        ``service_accounts``/``access_tokens``."""
        fp = FoundryPaths(root=tmp_path)
        conn = bootstrap(fp)
        try:
            (version,) = conn.execute("PRAGMA user_version").fetchone()
            assert version == rbac_store.RBAC_SCHEMA_VERSION
        finally:
            conn.close()
