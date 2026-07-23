"""Tests for POST /api/runs/{run_id}/writeback/approve (Phase 2, API-001..005).

Covers:
  1. RBAC gate — under-privileged roles get 403; permitted roles are not
     blocked; no-auth (single-operator-trust) mode always allows.
  2. governance_rejected mapping — guard-failure 422/400, and the
     guard-passed-but-council-required_block synthetic-violation branch.
  3. Exactly one ``audit_service.record_event`` call per invocation, across
     all four outcome classes: success, partial, blocked, exception.
  4. actor_user_id threading into the audit event and into
     ``approve_and_dispatch``'s ``approver_identity`` — present vs None.
  5. DF-004 — run-ownership gate: dispatch is denied (indistinguishable
     404, NO dispatch call) when an enforced workspace mismatch is
     detected, BEFORE ``approve_and_dispatch`` (and therefore before any
     external side effect) ever runs. Advisory mode still allows (and logs)
     a mismatch; ``identity=None`` always bypasses the check.

``approve_and_dispatch`` itself (Phase 1) is mocked throughout so each
outcome class can be forced directly, mirroring the mocking style used in
``tests/test_approve_and_dispatch.py`` for the underlying service function.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.errors import NotFoundError
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services.governance import GuardResult, Violation
from research_foundry.services.writeback import ApproveDispatchResult
from research_foundry.yamlio import dump_yaml, load_yaml

_RUN_ID = "rf_test_run_001"
_URL = f"/api/runs/{_RUN_ID}/writeback/approve"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> FoundryConfig:
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:  # pragma: no cover
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)

    foundry_yaml_path = root / "foundry.yaml"
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict[str, Any] = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    return FoundryConfig(paths=FoundryPaths(root=root))


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Test middleware that injects a fixed AuthIdentity onto request.state."""

    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


def _make_client(tmp_path: Path, identity: AuthIdentity | None = None) -> TestClient:
    cfg = _make_config(tmp_path)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


_REVIEWER = AuthIdentity("reviewer_user", "ws1", ("reviewer",))
_VIEWER = AuthIdentity("viewer_user", "ws1", ("viewer",))
_RESEARCHER = AuthIdentity("researcher_user", "ws1", ("researcher",))
_OWNER = AuthIdentity("owner_user", "ws1", ("owner",))


def _passing_guard() -> GuardResult:
    return GuardResult(passed=True, exit_code=0, violations=[])


def _blocked_guard(exit_code: int = 3) -> GuardResult:
    return GuardResult(
        passed=False,
        exit_code=exit_code,
        violations=[
            Violation(
                rule_id="sensitivity_mismatch",
                severity="block" if exit_code == 3 else "require_approval",
                message="blocked by policy",
                detail="",
            )
        ],
    )


def _success_result() -> ApproveDispatchResult:
    return ApproveDispatchResult(
        bundle_id="bundle_test_001",
        verified=True,
        council_decision="approve",
        reviewer_notes="looks good",
        required_fix=None,
        guard_result=_passing_guard(),
        target_status={"ccdash": "success", "meatywiki": "success", "skillmeat": "success"},
        overall_status="success",
    )


def _partial_result() -> ApproveDispatchResult:
    return ApproveDispatchResult(
        bundle_id="bundle_test_001",
        verified=True,
        council_decision="approve",
        reviewer_notes="looks good",
        required_fix=None,
        guard_result=_passing_guard(),
        target_status={"ccdash": "success", "meatywiki": "failed", "skillmeat": "success"},
        overall_status="partial",
    )


def _blocked_guard_result(exit_code: int = 3) -> ApproveDispatchResult:
    return ApproveDispatchResult(
        bundle_id="bundle_test_001",
        verified=True,
        council_decision="approve",
        reviewer_notes="",
        required_fix=None,
        guard_result=_blocked_guard(exit_code),
        target_status={"ccdash": "skipped", "meatywiki": "skipped", "skillmeat": "skipped"},
        overall_status="blocked",
    )


def _blocked_council_result() -> ApproveDispatchResult:
    return ApproveDispatchResult(
        bundle_id="bundle_test_001",
        verified=True,
        council_decision="required_block",
        reviewer_notes="council flagged an unresolved concern",
        required_fix="add a citation for claim clm_004",
        guard_result=_passing_guard(),
        target_status={"ccdash": "skipped", "meatywiki": "skipped", "skillmeat": "skipped"},
        overall_status="blocked",
    )


_PATCH_TARGET = "research_foundry.api.routers.writeback.approve_and_dispatch"
_AUDIT_TARGET = "research_foundry.api.routers.writeback.audit_service.record_event"


# ---------------------------------------------------------------------------
# 1. RBAC gate
# ---------------------------------------------------------------------------


class TestWritebackApproveRBAC:
    def test_reviewer_gets_403(self, tmp_path):
        client = _make_client(tmp_path, identity=_REVIEWER)
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 403

    def test_viewer_gets_403(self, tmp_path):
        client = _make_client(tmp_path, identity=_VIEWER)
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 403

    def test_researcher_gets_403(self, tmp_path):
        # researcher has no agent_job:launch-class permission; writeback
        # approve/dispatch is scoped owner/admin only, same as agent_jobs.py.
        client = _make_client(tmp_path, identity=_RESEARCHER)
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 403

    def test_owner_not_blocked_by_rbac(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200

    def test_no_auth_single_operator_trust_allows(self, tmp_path):
        client = _make_client(tmp_path, identity=None)
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. governance_rejected mapping
# ---------------------------------------------------------------------------


class TestGovernanceRejectedMapping:
    def test_guard_block_exit_code_3_returns_422(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_blocked_guard_result(exit_code=3)):
            resp = client.post(_URL, json={})
        assert resp.status_code == 422
        body = resp.json()["detail"]
        assert body["error"] == "governance_rejected"
        assert body["exit_code"] == 3
        assert any(v["rule_id"] == "sensitivity_mismatch" for v in body["violations"])

    def test_guard_human_review_exit_code_7_returns_400(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_blocked_guard_result(exit_code=7)):
            resp = client.post(_URL, json={})
        assert resp.status_code == 400
        body = resp.json()["detail"]
        assert body["error"] == "governance_rejected"
        assert body["exit_code"] == 7

    def test_council_required_block_with_passing_guard_returns_422_synthetic_violation(
        self, tmp_path
    ):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_blocked_council_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 422
        body = resp.json()["detail"]
        assert body["error"] == "governance_rejected"
        # Guard passed (exit_code 0) — the synthetic violation is what makes
        # the block visible in the response shape.
        assert body["exit_code"] == 0
        synthetic = [v for v in body["violations"] if v["rule_id"] == "council_required_block"]
        assert len(synthetic) == 1
        assert synthetic[0]["message"] == "add a citation for claim clm_004"

    def test_partial_is_not_an_error(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_partial_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "partial"


# ---------------------------------------------------------------------------
# 3. Exactly one audit_service.record_event call per outcome class
# ---------------------------------------------------------------------------


class TestAuditOneRowPerOutcome:
    def test_success_records_one_success_row(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_success_result()), patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 200
        assert mock_record.call_count == 1
        event = mock_record.call_args[0][1]
        assert event.result == "success"
        assert event.mutation_type == "writeback"
        assert event.target_ref == _RUN_ID

    def test_partial_records_one_failure_row(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_partial_result()), patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 200
        assert mock_record.call_count == 1
        event = mock_record.call_args[0][1]
        assert event.result == "failure"

    def test_blocked_records_one_denied_row(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_blocked_guard_result()), patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 422
        assert mock_record.call_count == 1
        event = mock_record.call_args[0][1]
        assert event.result == "denied"

    def test_unexpected_exception_records_one_failure_row_then_raises(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, side_effect=RuntimeError("boom")), patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 500
        assert mock_record.call_count == 1
        event = mock_record.call_args[0][1]
        assert event.result == "failure"
        assert event.error_detail == "boom"

    def test_not_found_records_one_failure_row_then_404s(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, side_effect=NotFoundError("no such run")), patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 404
        assert mock_record.call_count == 1
        event = mock_record.call_args[0][1]
        assert event.result == "failure"


# ---------------------------------------------------------------------------
# 4. actor_user_id threading
# ---------------------------------------------------------------------------


class TestActorIdentityThreading:
    def test_actor_user_id_present_when_identity_set(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 200
        # approver_identity threaded into approve_and_dispatch.
        _, kwargs = mock_dispatch.call_args
        assert kwargs["approver_identity"] == "owner_user"
        # actor_user_id threaded into the audit event.
        event = mock_record.call_args[0][1]
        assert event.actor_user_id == "owner_user"

    def test_actor_user_id_none_when_no_identity(self, tmp_path):
        client = _make_client(tmp_path, identity=None)
        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _AUDIT_TARGET
        ) as mock_record:
            resp = client.post(_URL, json={})
        assert resp.status_code == 200
        _, kwargs = mock_dispatch.call_args
        assert kwargs["approver_identity"] is None
        event = mock_record.call_args[0][1]
        assert event.actor_user_id is None


# ---------------------------------------------------------------------------
# Targets body handling
# ---------------------------------------------------------------------------


class TestTargetsBody:
    def test_default_targets_used_when_omitted(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _AUDIT_TARGET
        ):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200
        _, kwargs = mock_dispatch.call_args
        assert kwargs["targets"] == ("ccdash", "meatywiki", "skillmeat")

    def test_explicit_targets_are_threaded_through(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _AUDIT_TARGET
        ):
            resp = client.post(_URL, json={"targets": ["ccdash"]})
        assert resp.status_code == 200
        _, kwargs = mock_dispatch.call_args
        assert kwargs["targets"] == ("ccdash",)


# ---------------------------------------------------------------------------
# TEST-001 (Phase 4): RBAC on/off matrix — app.state.rbac_enforced toggled
# directly on an already-built app.
#
# None of the classes above manipulate ``app.state.rbac_enforced`` directly —
# they all rely on its default value. For ``_make_client``'s config,
# ``auth.rbac_enforcement`` defaults to ``auto`` and ``auth.provider``
# defaults to ``none``; ``FoundryConfig.resolve_rbac_enforced`` returns
# ``True`` for AUTO regardless of provider (see
# ``config.py::resolve_rbac_enforced`` — the identity-None passthrough in
# ``require_role`` is what actually provides single-operator-trust semantics,
# not a ``False`` sentinel), so ``app.state.rbac_enforced`` is already
# ``True`` by default here. This class completes the on/off matrix by
# flipping the flag directly post-construction, mirroring the toggle tested
# at config-build time in ``tests/unit/test_rbac_enforcement_toggle.py``
# (which sets ``rbac_enforcement=disabled`` before ``create_app`` instead).
# ---------------------------------------------------------------------------


class TestWritebackApproveRBACEnforcementToggle:
    def test_reviewer_allowed_when_rbac_enforced_false(self, tmp_path):
        client = _make_client(tmp_path, identity=_REVIEWER)
        client.app.state.rbac_enforced = False
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200

    def test_viewer_allowed_when_rbac_enforced_false(self, tmp_path):
        client = _make_client(tmp_path, identity=_VIEWER)
        client.app.state.rbac_enforced = False
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200

    def test_no_identity_allowed_when_rbac_enforced_explicitly_true(self, tmp_path):
        # Rounds out the matrix: rbac_enforced=True set EXPLICITLY (not just
        # relying on the default) + no resolved identity -> still allowed via
        # require_role's single-operator-trust identity-None passthrough,
        # same semantics as TestWritebackApproveRBAC's default-True case.
        client = _make_client(tmp_path, identity=None)
        client.app.state.rbac_enforced = True
        with patch(_PATCH_TARGET, return_value=_success_result()):
            resp = client.post(_URL, json={})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. DF-004 — run-ownership gate (before any dispatch / external side effect)
# ---------------------------------------------------------------------------

_ISOLATION_TARGET = "research_foundry.api.routers.writeback.resolve_workspace_isolation_active"


def _write_run_workspace(
    client: TestClient,
    run_id: str,
    *,
    workspace_id: str | None,
    omit_field: bool = False,
    visibility: str | None = None,
) -> None:
    """Write ``runs/<run_id>/run.yaml`` with the given ``workspace_id`` (DF-004 fixture).

    ``omit_field=True`` simulates a legacy run predating the ``workspace_id``
    field entirely (as opposed to ``workspace_id=None``, which still writes
    the key with a null value) — both are treated identically by the gate
    (missing/null -> mismatch under enforcement), but this covers both shapes.

    ``visibility`` (when provided) writes the DF-004 read-visibility field —
    used to prove that ``public`` visibility, which grants cross-workspace
    *reads*, never grants a cross-workspace writeback dispatch.
    """
    paths: FoundryPaths = client.app.dependency_overrides[get_paths]()
    rp = paths.run_paths(run_id)
    rp.run.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {"run_id": run_id}
    if not omit_field:
        doc["workspace_id"] = workspace_id
    if visibility is not None:
        doc["visibility"] = visibility
    dump_yaml(doc, rp.run_yaml)


class TestWorkspaceOwnershipGate:
    """DF-004: writeback dispatch gated on run ownership BEFORE any side effect.

    ``_OWNER`` (defined above) is workspace ``"ws1"`` throughout.
    """

    def test_cross_workspace_enforced_denies_before_dispatch(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        _write_run_workspace(client, _RUN_ID, workspace_id="ws_other")

        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _AUDIT_TARGET
        ) as mock_record, patch(_ISOLATION_TARGET, return_value=True):
            resp = client.post(_URL, json={})

        # Indistinguishable-404 — same shape as a genuinely-missing run, NEVER
        # a distinguishable 403.
        assert resp.status_code == 404
        assert resp.json()["detail"] == "run not found"
        # The whole point: dispatch (and therefore every external side
        # effect it performs) must never have been attempted.
        mock_dispatch.assert_not_called()
        # Exactly one audit row still happens (the existing NotFoundError
        # branch handles it) — invariant preserved for free.
        assert mock_record.call_count == 1
        event = mock_record.call_args[0][1]
        assert event.result == "failure"
        assert event.target_ref == _RUN_ID

    def test_public_run_cross_workspace_still_denies_writeback(self, tmp_path):
        # DF-004 invariant: `visibility: public` grants cross-workspace READ
        # only — it must NEVER grant a cross-workspace writeback dispatch (a
        # mutating action stays owner-scoped). The gate provably ignores
        # `visibility` today; this test trips red if a future refactor makes
        # the writeback gate start honoring public visibility.
        client = _make_client(tmp_path, identity=_OWNER)  # _OWNER is ws1
        _write_run_workspace(
            client, _RUN_ID, workspace_id="ws_other", visibility="public"
        )

        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _ISOLATION_TARGET, return_value=True
        ):
            resp = client.post(_URL, json={})

        assert resp.status_code == 404
        assert resp.json()["detail"] == "run not found"
        mock_dispatch.assert_not_called()

    def test_legacy_run_missing_workspace_id_enforced_denies(self, tmp_path):
        # A run predating DF-004's workspace_id field is treated as a
        # mismatch under enforcement — never defaulted to allowed.
        client = _make_client(tmp_path, identity=_OWNER)
        _write_run_workspace(client, _RUN_ID, workspace_id=None, omit_field=True)

        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _ISOLATION_TARGET, return_value=True
        ):
            resp = client.post(_URL, json={})

        assert resp.status_code == 404
        assert resp.json()["detail"] == "run not found"
        mock_dispatch.assert_not_called()

    def test_same_workspace_enforced_succeeds(self, tmp_path):
        client = _make_client(tmp_path, identity=_OWNER)
        _write_run_workspace(client, _RUN_ID, workspace_id="ws1")

        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _ISOLATION_TARGET, return_value=True
        ):
            resp = client.post(_URL, json={})

        assert resp.status_code == 200
        mock_dispatch.assert_called_once()

    def test_no_identity_bypasses_gate_even_on_mismatch(self, tmp_path):
        # identity=None (single-operator-trust / LAN no-auth) always allows,
        # byte-identical to pre-DF-004 behaviour, regardless of enforcement
        # or the run's workspace_id.
        client = _make_client(tmp_path, identity=None)
        _write_run_workspace(client, _RUN_ID, workspace_id="ws_other")

        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _ISOLATION_TARGET, return_value=True
        ):
            resp = client.post(_URL, json={})

        assert resp.status_code == 200
        mock_dispatch.assert_called_once()

    def test_advisory_mode_cross_workspace_allows_and_logs(self, tmp_path, caplog):
        # Advisory mode (isolation not actively enforced): a mismatch is
        # logged (by the shared require_workspace_scope predicate) but the
        # call is ALLOWED — dispatch DOES run.
        client = _make_client(tmp_path, identity=_OWNER)
        _write_run_workspace(client, _RUN_ID, workspace_id="ws_other")

        with patch(_PATCH_TARGET, return_value=_success_result()) as mock_dispatch, patch(
            _ISOLATION_TARGET, return_value=False
        ), caplog.at_level(logging.WARNING, logger="research_foundry.api.auth.scope"):
            resp = client.post(_URL, json={})

        assert resp.status_code == 200
        mock_dispatch.assert_called_once()
        assert any(
            "workspace_scope_advisory_mismatch" in record.message for record in caplog.records
        )
