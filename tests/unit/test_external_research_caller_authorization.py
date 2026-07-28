"""Unit tests for ERI-6.0 — contract §1.6 / §2.4 Step 0 caller reauthorization
(closes audit finding #9, `.claude/findings/eri-p1-contract-audit-gpt56.md`).

Two things are proven here, matching the phase-6 task's explicit requirement:

1. A revoked (or never-a-member) caller cannot replay a previously-published
   receipt, nor trigger a fresh import — the denial happens BEFORE any
   receipt existence lookup, both inside ``ExternalResearchInterchange.stage``
   and inside ``import_external_report``'s own pre-derivation `_load_receipt`
   check.
2. A real governance-policy-ruleset change (here: the RBAC schema version)
   yields a DIFFERENT `receipt_digest` for an otherwise byte-identical
   import — a stale ruleset is never silently reused.

``caller=None`` (the only value the bare CLI passes today) is asserted to be
completely unaffected — single-operator-trust, exactly as before this gate
existed (contract disposition: bare-CLI wiring is explicitly out of scope
for this closure; see the phase-6 completion note).
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services import rbac_store
from research_foundry.services.external_research_interchange import (
    ERI_READ_PERMISSION,
    ERI_SUBMIT_PERMISSION,
    CallerContext,
    CallerNotAuthorizedError,
    ExternalResearchInterchange,
    authorize_caller,
    compute_governance_policy_digest,
)

from .test_external_research_interchange import VALID_POLICY, build_packet


@pytest.fixture()
def workspace(tmp_path: Path) -> FoundryPaths:
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    (ws_root / "foundry.yaml").write_text("workspace: true\n", encoding="utf-8")
    return FoundryPaths(root=ws_root)


def _interchange(workspace: FoundryPaths, workspace_id: str = "ws_demo") -> ExternalResearchInterchange:
    return ExternalResearchInterchange(workspace_id=workspace_id, paths=workspace)


def _bootstrap_member(
    workspace: FoundryPaths, *, workspace_id: str, user_id: str, role: str = "researcher"
) -> None:
    conn = rbac_store.bootstrap(workspace)
    try:
        rbac_store.upsert_workspace(conn, workspace_id, "demo")
        rbac_store.upsert_user(conn, user_id, "Demo User")
        rbac_store.upsert_membership(conn, user_id, workspace_id, role)
    finally:
        conn.close()


def _issue_token(
    workspace: FoundryPaths, *, workspace_id: str, user_id: str, token_id: str, role: str = "researcher"
) -> None:
    conn = rbac_store.bootstrap(workspace)
    try:
        rbac_store.create_access_token(
            conn,
            token_id=token_id,
            principal_type="user_pat",
            principal_id=user_id,
            workspace_id=workspace_id,
            role=role,
            token_hash="unused-in-this-gate",
            token_prefix="unused",
        )
    finally:
        conn.close()


def _revoke_token(workspace: FoundryPaths, token_id: str) -> None:
    conn = rbac_store.bootstrap(workspace)
    try:
        rbac_store.revoke_access_token(conn, token_id)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# caller=None — single-operator-trust, unchanged
# ---------------------------------------------------------------------------


def test_caller_none_is_single_operator_trust(workspace: FoundryPaths) -> None:
    # No RBAC membership exists anywhere for this workspace; caller=None
    # must still succeed unconditionally (today's only real CLI path).
    authorize_caller(None, workspace_id="ws_demo", paths=workspace)


def test_caller_none_stage_unaffected(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert result.replayed is False
    assert result.receipt["status"] in ("completed", "completed_with_quarantine")
    # Replay with caller=None still works exactly as before.
    replay = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert replay.replayed is True
    assert replay.receipt == result.receipt


# ---------------------------------------------------------------------------
# Active caller — authorized
# ---------------------------------------------------------------------------


def test_authorized_member_passes(workspace: FoundryPaths) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_alice")
    caller = CallerContext(principal_id="usr_alice", workspace_id="ws_demo")
    authorize_caller(caller, workspace_id="ws_demo", paths=workspace)  # must not raise


def test_authorized_member_can_stage_and_replay(workspace: FoundryPaths, tmp_path: Path) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_alice")
    caller = CallerContext(principal_id="usr_alice", workspace_id="ws_demo")
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert result.replayed is False
    replay = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert replay.replayed is True
    assert replay.receipt == result.receipt


# ---------------------------------------------------------------------------
# Denials — never a member, workspace mismatch, revoked membership, revoked token
# ---------------------------------------------------------------------------


def test_caller_with_no_membership_denied(workspace: FoundryPaths) -> None:
    caller = CallerContext(principal_id="usr_ghost", workspace_id="ws_demo")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace)


def test_caller_workspace_mismatch_denied(workspace: FoundryPaths) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_alice")
    caller = CallerContext(principal_id="usr_alice", workspace_id="ws_other")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace)


def test_no_membership_denies_stage_before_any_receipt_created(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """A caller who fails Step 0 never reaches receipt existence lookup —
    zero files are written under the interchange's on-disk root at all,
    matching contract §1.6/§4.3's non-receipt denial."""

    root = build_packet(tmp_path / "packet")
    caller = CallerContext(principal_id="usr_ghost", workspace_id="ws_demo")
    interchange = _interchange(workspace)
    with pytest.raises(CallerNotAuthorizedError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert not interchange.root.exists()


def test_revoked_membership_cannot_replay(workspace: FoundryPaths, tmp_path: Path) -> None:
    """The core audit-#9 scenario: a caller with valid membership stages a
    packet (publishing a real receipt), the membership is then revoked
    (role removed / never re-granted), and the SAME caller attempting to
    replay the SAME packet/workspace/target is denied outright — never
    handed the stored receipt merely because one exists on disk."""

    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_alice")
    caller = CallerContext(principal_id="usr_alice", workspace_id="ws_demo")
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)

    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert first.replayed is False

    # Revoke: delete the membership row entirely (role change / removal).
    conn = rbac_store.bootstrap(workspace)
    try:
        conn.execute(
            "DELETE FROM memberships WHERE user_id = ? AND workspace_id = ?",
            ("usr_alice", "ws_demo"),
        )
    finally:
        conn.close()

    with pytest.raises(CallerNotAuthorizedError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)


def test_revoked_token_cannot_replay(workspace: FoundryPaths, tmp_path: Path) -> None:
    """Same scenario, but via a revoked access TOKEN rather than a removed
    membership — the caller's underlying user membership may still exist,
    but the specific token they authenticated with no longer does."""

    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_bob")
    _issue_token(workspace, workspace_id="ws_demo", user_id="usr_bob", token_id="tok_1")
    caller = CallerContext(principal_id="usr_bob", workspace_id="ws_demo", token_id="tok_1")
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)

    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert first.replayed is False

    _revoke_token(workspace, "tok_1")

    with pytest.raises(CallerNotAuthorizedError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)


def test_import_external_report_gates_pending_checkpoint_lookup(
    workspace: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``import_external_report`` performs its OWN direct `_load_receipt`
    pre-check (pending-checkpoint detection) ahead of calling `stage()` —
    this must be gated by the exact same live reauthorization, not just the
    inner `stage()` call, per contract §1.6 ("any operation that could
    reveal whether a receipt_digest/identity tuple has a stored receipt")."""

    from research_foundry.services.external_research_import import (
        import_external_report,
    )

    root = build_packet(tmp_path / "packet")
    caller = CallerContext(principal_id="usr_ghost", workspace_id="ws_demo")
    with pytest.raises(CallerNotAuthorizedError):
        import_external_report(
            root,
            workspace_id="ws_demo",
            policy=VALID_POLICY,
            paths=workspace,
            caller=caller,
        )


# ---------------------------------------------------------------------------
# governance_policy_digest — real, versioned, and load-bearing for identity
# ---------------------------------------------------------------------------


def test_compute_governance_policy_digest_is_stable() -> None:
    assert compute_governance_policy_digest() == compute_governance_policy_digest()
    assert len(compute_governance_policy_digest()) == 64


def test_governance_policy_digest_changes_with_rbac_schema_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = compute_governance_policy_digest()
    monkeypatch.setattr(rbac_store, "RBAC_SCHEMA_VERSION", rbac_store.RBAC_SCHEMA_VERSION + 1)
    bumped = compute_governance_policy_digest()
    assert bumped != baseline


def test_governance_policy_change_yields_a_different_receipt_identity(
    workspace: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real ruleset change (RBAC schema version bump) must compute a
    DISTINCT `receipt_digest` for the exact same packet/workspace/target/
    policy — never a silent reinterpretation of a previously-published
    receipt under new rules (contract §1.3's rationale for binding
    `governance_policy_digest`, verified end to end through `stage()`)."""

    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)

    monkeypatch.setattr(rbac_store, "RBAC_SCHEMA_VERSION", rbac_store.RBAC_SCHEMA_VERSION + 1)

    second_workspace_paths = workspace  # same on-disk root; different identity, not a conflict
    interchange2 = _interchange(second_workspace_paths)
    second = interchange2.stage(root, target_run_id=None, policy=VALID_POLICY)

    assert first.receipt["receipt_digest"] != second.receipt["receipt_digest"]
    assert first.replayed is False
    assert second.replayed is False


# ---------------------------------------------------------------------------
# Round-2 audit finding #1 — governance_policy_digest folds in the effective
# ERI permission mapping AND the per-import rights/sensitivity policy, so a
# policy change cannot replay a previously-allowed outcome.
# ---------------------------------------------------------------------------


def test_governance_policy_digest_changes_with_authorization_policy() -> None:
    permissive = compute_governance_policy_digest(
        authorization_policy={"denied_access_statuses": [], "require_rights_for_access_statuses": []}
    )
    denying = compute_governance_policy_digest(
        authorization_policy={
            "denied_access_statuses": ["paywalled"],
            "require_rights_for_access_statuses": ["paywalled"],
        }
    )
    assert permissive != denying


def test_authorization_policy_change_yields_a_different_receipt_identity(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """Importing once under a permissive rights/sensitivity policy and
    retrying under a denying one must compute a DISTINCT `receipt_digest` —
    the exact exploit audit finding #1 named: a stale, more-permissive
    policy decision must never be silently replayed once the operator
    deliberately tightens the effective policy."""

    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    permissive = interchange.stage(
        root,
        target_run_id=None,
        policy=VALID_POLICY,
        authorization_policy={"denied_access_statuses": [], "require_rights_for_access_statuses": []},
    )
    denying = interchange.stage(
        root,
        target_run_id=None,
        policy=VALID_POLICY,
        authorization_policy={
            "denied_access_statuses": ["paywalled"],
            "require_rights_for_access_statuses": ["paywalled"],
        },
    )
    assert permissive.receipt["receipt_digest"] != denying.receipt["receipt_digest"]
    assert permissive.replayed is False
    assert denying.replayed is False


def test_governance_policy_digest_folds_in_eri_role_permission_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """A permission-MAPPING change (not just a role NAME/schema-version
    change) must also move the digest — audit finding #1's specific
    complaint that the prior digest omitted permission mappings entirely."""

    from research_foundry.services import external_research_interchange as eri

    baseline = compute_governance_policy_digest()
    monkeypatch.setitem(eri._ERI_ROLE_PERMISSIONS, "viewer", frozenset({ERI_READ_PERMISSION}))
    changed = compute_governance_policy_digest()
    assert baseline != changed


# ---------------------------------------------------------------------------
# Round-2 audit finding #2 — membership is not permission: an explicit ERI
# permission matrix, a token role ceiling, and service-principal-through-
# own-record authorization.
# ---------------------------------------------------------------------------


def test_viewer_role_denied_for_submit(workspace: FoundryPaths) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_viewer", role="viewer")
    caller = CallerContext(principal_id="usr_viewer", workspace_id="ws_demo")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_viewer_role_denied_for_read_too(workspace: FoundryPaths) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_viewer", role="viewer")
    caller = CallerContext(principal_id="usr_viewer", workspace_id="ws_demo")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_READ_PERMISSION)


def test_reviewer_role_can_read_but_not_submit(workspace: FoundryPaths) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_reviewer", role="reviewer")
    caller = CallerContext(principal_id="usr_reviewer", workspace_id="ws_demo")
    authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_READ_PERMISSION)
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_viewer_stage_denied_before_any_receipt_created(workspace: FoundryPaths, tmp_path: Path) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_viewer", role="viewer")
    caller = CallerContext(principal_id="usr_viewer", workspace_id="ws_demo")
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    with pytest.raises(CallerNotAuthorizedError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert not interchange.root.exists()


def test_token_role_ceiling_denies_even_with_admin_membership(workspace: FoundryPaths) -> None:
    """A caller whose CURRENT membership role is `admin` (full permissions)
    but who authenticated with a token issued at a lower `viewer` ceiling
    must still be denied — the token's own role is a ceiling, never
    overridden by the principal's current, higher membership role."""

    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_carol", role="admin")
    _issue_token(workspace, workspace_id="ws_demo", user_id="usr_carol", token_id="tok_ceiling", role="viewer")
    caller = CallerContext(principal_id="usr_carol", workspace_id="ws_demo", token_id="tok_ceiling")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_token_role_ceiling_allows_when_both_grant(workspace: FoundryPaths) -> None:
    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_dana", role="admin")
    _issue_token(workspace, workspace_id="ws_demo", user_id="usr_dana", token_id="tok_ok", role="researcher")
    caller = CallerContext(principal_id="usr_dana", workspace_id="ws_demo", token_id="tok_ok")
    authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_service_principal_authorized_through_own_record(workspace: FoundryPaths) -> None:
    """A service principal is authorized via its OWN `service_accounts`
    record, never through the `memberships` table (which answers a
    meaningless -- or worse, wrong-principal -- question for a service
    account id)."""

    conn = rbac_store.bootstrap(workspace)
    try:
        rbac_store.upsert_workspace(conn, "ws_demo", "demo")
        rbac_store.create_service_account(
            conn,
            service_account_id="svc_ingest",
            name="Ingest Bot",
            workspace_id="ws_demo",
            role="researcher",
        )
    finally:
        conn.close()

    caller = CallerContext(principal_id="svc_ingest", workspace_id="ws_demo", principal_type="service")
    authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_service_principal_with_no_record_denied(workspace: FoundryPaths) -> None:
    caller = CallerContext(principal_id="svc_ghost", workspace_id="ws_demo", principal_type="service")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_disabled_service_principal_denied(workspace: FoundryPaths) -> None:
    conn = rbac_store.bootstrap(workspace)
    try:
        rbac_store.upsert_workspace(conn, "ws_demo", "demo")
        rbac_store.create_service_account(
            conn,
            service_account_id="svc_disabled",
            name="Retired Bot",
            workspace_id="ws_demo",
            role="admin",
        )
        rbac_store.disable_service_account(conn, "svc_disabled")
    finally:
        conn.close()

    caller = CallerContext(principal_id="svc_disabled", workspace_id="ws_demo", principal_type="service")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


def test_service_principal_not_confused_with_same_id_user_membership(workspace: FoundryPaths) -> None:
    """A user membership row sharing the SAME id as an (absent) service
    account must never be consulted for a `principal_type="service"`
    caller -- proving service principals resolve through their own table,
    not a membership-table lookup that could coincidentally match."""

    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="svc_confusable", role="admin")
    caller = CallerContext(principal_id="svc_confusable", workspace_id="ws_demo", principal_type="service")
    with pytest.raises(CallerNotAuthorizedError):
        authorize_caller(caller, workspace_id="ws_demo", paths=workspace, permission=ERI_SUBMIT_PERMISSION)


# ---------------------------------------------------------------------------
# Round-2 audit finding #3 — reauthorization inside the lease, immediately
# before the receipt existence lookup, not only at Step 0.
# ---------------------------------------------------------------------------


def test_membership_revoked_during_lease_wait_denies_before_replay_read(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """Simulates the exact staleness window the finding names: Step 0
    passes, then -- before this same call reaches its receipt-existence
    lookup inside the lease -- the caller's membership is revoked. The
    in-lease reauthorization must catch this; it must not be handed the
    stored receipt merely because Step 0 once passed."""

    _bootstrap_member(workspace, workspace_id="ws_demo", user_id="usr_erin")
    caller = CallerContext(principal_id="usr_erin", workspace_id="ws_demo")
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
    assert first.replayed is False

    # Step 0 (the FIRST `authorize_caller` call in `stage()`) has already
    # necessarily run and passed by the time any test code executes here on
    # a subsequent call. Revoking membership right as the receipt-identity
    # lease is entered simulates "the wait for lease contention resolved,
    # but the caller was revoked during that wait" -- exactly the window
    # the finding names. If `stage()` only reauthorized once, at the top,
    # this second `stage()` call would still succeed and hand back the
    # stored receipt; the in-lease reauthorization must instead deny it.
    real_receipt_lease = interchange._receipt_lease

    @contextmanager
    def _revoke_then_lease(receipt_digest: str):
        conn = rbac_store.bootstrap(workspace)
        try:
            conn.execute(
                "DELETE FROM memberships WHERE user_id = ? AND workspace_id = ?",
                ("usr_erin", "ws_demo"),
            )
        finally:
            conn.close()
        with real_receipt_lease(receipt_digest):
            yield

    interchange._receipt_lease = _revoke_then_lease  # type: ignore[method-assign]
    with pytest.raises(CallerNotAuthorizedError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY, caller=caller)
