"""Unit tests for ``token_service.py`` (public-multiuser Phase 2, ACT-202/ACT-206).

Covers:
- ACT-201: ``service_accounts``/``access_tokens`` schema is idempotent across
  repeated ``bootstrap()`` calls.
- ACT-202: issuance (service account + PAT), hash-at-rest, constant-time
  verification, revocation, expiry, and the FR-9 role-ceiling re-check at
  resolution time (not only issuance).
- ACT-206 [SEAM]: round-trip issue -> store -> verify -> revoke ->
  verify-denied for both ``principal_type=service`` and ``principal_type=user_pat``.
- Hard security gate: a static scan of the raw ``rbac.db`` bytes after
  issuing several tokens finds ZERO occurrences of any issued plaintext
  secret (never persisted anywhere, in any form).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services import rbac_store, token_service
from research_foundry.services.token_service import (
    IssuedToken,
    ResolvedIdentity,
    RoleCeilingError,
    TokenServiceError,
)

pytestmark = pytest.mark.usefixtures("tmp_foundry")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _seed_workspace_and_users(paths: FoundryPaths) -> None:
    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.upsert_workspace(conn, "ws1", "Workspace One")
        rbac_store.upsert_user(conn, "alice", "Alice")
        rbac_store.upsert_user(conn, "bob", "Bob")
        rbac_store.upsert_membership(conn, "alice", "ws1", "owner")
        rbac_store.upsert_membership(conn, "bob", "ws1", "viewer")
    finally:
        conn.close()


def _create_service_account(
    paths: FoundryPaths,
    *,
    service_account_id: str = "svc1",
    role: str = "researcher",
    workspace_id: str = "ws1",
    disabled: bool = False,
) -> None:
    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.create_service_account(
            conn,
            service_account_id=service_account_id,
            name="Test Service Account",
            workspace_id=workspace_id,
            role=role,
            created_by="alice",
        )
        if disabled:
            rbac_store.disable_service_account(conn, service_account_id)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# ACT-201: schema idempotency
# ---------------------------------------------------------------------------


def test_schema_idempotent_across_repeated_bootstrap(tmp_foundry: FoundryPaths) -> None:
    conn1 = rbac_store.bootstrap(tmp_foundry)
    conn1.close()
    conn2 = rbac_store.bootstrap(tmp_foundry)
    try:
        tables = {
            row["name"]
            for row in conn2.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "service_accounts" in tables
        assert "access_tokens" in tables
        (version,) = conn2.execute("PRAGMA user_version").fetchone()
        assert version == rbac_store.RBAC_SCHEMA_VERSION
    finally:
        conn2.close()


# ---------------------------------------------------------------------------
# ACT-202: issuance
# ---------------------------------------------------------------------------


class TestIssueServiceAccountToken:
    def test_issues_with_plaintext_shown_once(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)

        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1", created_by="alice"
        )

        assert isinstance(issued, IssuedToken)
        assert issued.principal_type == "service"
        assert issued.principal_id == "svc1"
        assert issued.role == "researcher"
        assert issued.workspace_id == "ws1"
        assert len(issued.plaintext) > 8
        assert issued.token_prefix == issued.plaintext[:8]

    def test_unknown_service_account_raises(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        with pytest.raises(TokenServiceError):
            token_service.issue_service_account_token(
                tmp_foundry, service_account_id="does-not-exist"
            )

    def test_disabled_service_account_raises(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry, disabled=True)
        with pytest.raises(TokenServiceError):
            token_service.issue_service_account_token(tmp_foundry, service_account_id="svc1")


class TestIssueUserPat:
    def test_issues_when_role_at_or_below_issuer_ceiling(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        issued = token_service.issue_user_pat(
            tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="researcher"
        )
        assert issued.principal_type == "user_pat"
        assert issued.principal_id == "alice"
        assert issued.role == "researcher"

    def test_role_ceiling_violation_raises_at_issuance(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        # bob is 'viewer' -- requesting 'owner' outranks his current role.
        with pytest.raises(RoleCeilingError):
            token_service.issue_user_pat(
                tmp_foundry, issuer_user_id="bob", workspace_id="ws1", role="owner"
            )

    def test_non_member_issuer_raises(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        with pytest.raises(TokenServiceError):
            token_service.issue_user_pat(
                tmp_foundry, issuer_user_id="charlie", workspace_id="ws1", role="viewer"
            )


# ---------------------------------------------------------------------------
# ACT-202: verification (hash-at-rest, constant-time, expiry, revocation)
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def test_valid_token_resolves(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1"
        )

        resolved = token_service.verify_token(tmp_foundry, issued.plaintext)

        assert isinstance(resolved, ResolvedIdentity)
        assert resolved.token_id == issued.token_id
        assert resolved.principal_type == "service"
        assert resolved.principal_id == "svc1"
        assert resolved.workspace_id == "ws1"
        assert resolved.role == "researcher"

    def test_empty_or_short_token_returns_none(self, tmp_foundry: FoundryPaths) -> None:
        assert token_service.verify_token(tmp_foundry, "") is None
        assert token_service.verify_token(tmp_foundry, "short") is None

    def test_unknown_prefix_returns_none(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        token_service.issue_service_account_token(tmp_foundry, service_account_id="svc1")

        assert token_service.verify_token(tmp_foundry, "zzzzzzzzzzzzzzzzzzzzzzzz") is None

    def test_tampered_secret_same_prefix_returns_none(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1"
        )

        # Keep the real (matching) prefix but corrupt the remainder -- this
        # exercises the hash-mismatch branch, not the prefix-miss branch.
        tampered = issued.plaintext[:8] + "x" * (len(issued.plaintext) - 8)
        assert tampered != issued.plaintext
        assert token_service.verify_token(tmp_foundry, tampered) is None

    def test_revoked_token_returns_none(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1"
        )
        assert token_service.verify_token(tmp_foundry, issued.plaintext) is not None

        token_service.revoke_token(tmp_foundry, issued.token_id)

        assert token_service.verify_token(tmp_foundry, issued.plaintext) is None

    def test_expired_token_returns_none(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry,
            service_account_id="svc1",
            expires_at="2000-01-01T00:00:00Z",  # long in the past
        )

        assert token_service.verify_token(tmp_foundry, issued.plaintext) is None

    def test_disabled_service_account_invalidates_live_tokens(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1"
        )
        assert token_service.verify_token(tmp_foundry, issued.plaintext) is not None

        conn = rbac_store.bootstrap(tmp_foundry)
        try:
            rbac_store.disable_service_account(conn, "svc1")
        finally:
            conn.close()

        assert token_service.verify_token(tmp_foundry, issued.plaintext) is None

    def test_pat_role_ceiling_recheck_at_resolution_invalidates_after_downgrade(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        """FR-9: a PAT issued while the issuer held 'owner' becomes invalid the
        moment the issuer is downgraded below the PAT's stored role -- checked
        fresh on every resolution, never cached from issuance time."""
        _seed_workspace_and_users(tmp_foundry)
        issued = token_service.issue_user_pat(
            tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="owner"
        )
        assert token_service.verify_token(tmp_foundry, issued.plaintext) is not None

        conn = rbac_store.bootstrap(tmp_foundry)
        try:
            rbac_store.update_member_role(conn, "alice", "ws1", "viewer")
        finally:
            conn.close()

        assert token_service.verify_token(tmp_foundry, issued.plaintext) is None

    def test_pat_invalidated_if_issuer_removed_from_workspace(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        _seed_workspace_and_users(tmp_foundry)
        issued = token_service.issue_user_pat(
            tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="researcher"
        )
        conn = rbac_store.bootstrap(tmp_foundry)
        try:
            conn.execute(
                "DELETE FROM memberships WHERE user_id = ? AND workspace_id = ?",
                ("alice", "ws1"),
            )
        finally:
            conn.close()

        assert token_service.verify_token(tmp_foundry, issued.plaintext) is None

    def test_verify_updates_last_used_at_best_effort(self, tmp_foundry: FoundryPaths) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1"
        )
        assert token_service.verify_token(tmp_foundry, issued.plaintext) is not None

        conn = rbac_store.bootstrap(tmp_foundry)
        try:
            row = rbac_store.verify_access_token(conn, issued.token_prefix)
        finally:
            conn.close()
        assert row is not None
        assert row["last_used_at"] is not None


# ---------------------------------------------------------------------------
# ACT-206 [SEAM]: round-trip issue -> store -> verify -> revoke -> verify-denied
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("principal_type", ["service", "user_pat"])
def test_round_trip_issue_store_verify_revoke_verify_denied(
    tmp_foundry: FoundryPaths, principal_type: str
) -> None:
    _seed_workspace_and_users(tmp_foundry)

    if principal_type == "service":
        _create_service_account(tmp_foundry)
        issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc1"
        )
    else:
        issued = token_service.issue_user_pat(
            tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="researcher"
        )

    # store: row is retrievable by prefix via rbac_store directly (the seam).
    conn = rbac_store.bootstrap(tmp_foundry)
    try:
        stored = rbac_store.verify_access_token(conn, issued.token_prefix)
    finally:
        conn.close()
    assert stored is not None
    assert stored["id"] == issued.token_id
    assert stored["principal_type"] == principal_type

    # verify: token_service resolves it correctly end-to-end.
    resolved = token_service.verify_token(tmp_foundry, issued.plaintext)
    assert resolved is not None
    assert resolved.token_id == issued.token_id

    # revoke: rbac_store.revoke_access_token is what token_service.revoke_token wraps.
    token_service.revoke_token(tmp_foundry, issued.token_id)

    # verify-denied: the same plaintext no longer resolves.
    assert token_service.verify_token(tmp_foundry, issued.plaintext) is None


# ---------------------------------------------------------------------------
# list_tokens never leaks token_hash
# ---------------------------------------------------------------------------


def test_list_tokens_never_includes_hash(tmp_foundry: FoundryPaths) -> None:
    _seed_workspace_and_users(tmp_foundry)
    _create_service_account(tmp_foundry)
    token_service.issue_service_account_token(tmp_foundry, service_account_id="svc1")

    rows = token_service.list_tokens(tmp_foundry, workspace_id="ws1")

    assert len(rows) == 1
    assert "token_hash" not in rows[0]


# ---------------------------------------------------------------------------
# Hard security gate: zero plaintext secrets persisted anywhere (static scan)
# ---------------------------------------------------------------------------


def test_static_scan_zero_plaintext_secrets_in_rbac_db(tmp_foundry: FoundryPaths) -> None:
    """After issuing several tokens (service + PAT), none of their plaintext
    values appear anywhere in the raw bytes of rbac.db -- the only thing
    persisted is the HMAC-SHA256 hash and the short non-secret prefix."""
    _seed_workspace_and_users(tmp_foundry)
    _create_service_account(tmp_foundry, service_account_id="svc1")
    _create_service_account(tmp_foundry, service_account_id="svc2", role="viewer")

    plaintexts: list[str] = []
    for svc_id in ("svc1", "svc2"):
        issued = token_service.issue_service_account_token(tmp_foundry, service_account_id=svc_id)
        plaintexts.append(issued.plaintext)
    pat_issued = token_service.issue_user_pat(
        tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="owner"
    )
    plaintexts.append(pat_issued.plaintext)

    db_path: Path = tmp_foundry.rbac_db
    assert db_path.exists()
    raw = db_path.read_bytes()

    for plaintext in plaintexts:
        assert len(plaintext) > 8  # sanity: not trivially short/coincidental
        assert plaintext.encode("utf-8") not in raw, (
            f"plaintext secret found verbatim in rbac.db: {plaintext[:8]}..."
        )
        # The remainder-after-prefix (the actual secret material fed into the
        # HMAC) must also never appear verbatim.
        remainder = plaintext[8:]
        assert remainder.encode("utf-8") not in raw
