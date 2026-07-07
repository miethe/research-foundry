"""Unit tests for RBAC enforcement — require_role dependency and AuthIdentity contract.

Covers RBAC-002 (require_role behavior) and RBAC-900 (roles-array resilience).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.auth.rbac import ROLE_PERMISSIONS, require_role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _State:
    """Minimal stand-in for Starlette's Request.state."""


class _MockRequest:
    """Minimal mock of fastapi.Request with a configurable state."""

    def __init__(self, *, identity: AuthIdentity | None = None, has_identity: bool = True) -> None:
        self.state = _State()
        if has_identity:
            self.state.identity = identity  # type: ignore[attr-defined]
        # When has_identity=False, state has no 'identity' attribute at all,
        # mirroring the behaviour of auth.provider=none (no middleware sets it).


def _call(dep_fn, *, identity=None, has_identity=True):
    """Invoke the inner function returned by require_role(...)."""
    request = _MockRequest(identity=identity, has_identity=has_identity)
    dep_fn(request)  # raises HTTPException on deny, returns None on allow


# ---------------------------------------------------------------------------
# RBAC-002: require_role core behaviour
# ---------------------------------------------------------------------------


class TestRequireRoleNoIdentity:
    """When auth is disabled (no identity on request.state), every call must allow."""

    def test_no_identity_attribute_allows_owner_role(self):
        dep = require_role("owner")
        _call(dep, has_identity=False)  # must not raise

    def test_no_identity_attribute_allows_researcher_role(self):
        dep = require_role("researcher")
        _call(dep, has_identity=False)

    def test_no_identity_attribute_allows_any_role_set(self):
        dep = require_role("owner", "admin", "researcher")
        _call(dep, has_identity=False)

    def test_identity_none_allows(self):
        """identity=None is the same as 'no identity': single-operator-trust mode."""
        dep = require_role("owner")
        _call(dep, identity=None, has_identity=True)


class TestRequireRoleWithMatchingRole:
    """Identity present with a matching role must be allowed."""

    def test_owner_allowed_when_owner_required(self):
        dep = require_role("owner")
        _call(dep, identity=AuthIdentity("u1", "ws1", ("owner",)))

    def test_admin_allowed_when_admin_required(self):
        dep = require_role("admin")
        _call(dep, identity=AuthIdentity("u1", "ws1", ("admin",)))

    def test_researcher_allowed_when_researcher_required(self):
        dep = require_role("researcher")
        _call(dep, identity=AuthIdentity("u1", "ws1", ("researcher",)))

    def test_owner_allowed_in_multi_role_list(self):
        dep = require_role("owner", "admin", "researcher")
        _call(dep, identity=AuthIdentity("u1", "ws1", ("owner",)))

    def test_researcher_allowed_in_multi_role_list(self):
        dep = require_role("owner", "admin", "researcher")
        _call(dep, identity=AuthIdentity("u1", "ws1", ("researcher",)))

    def test_identity_with_multiple_roles_where_one_matches(self):
        dep = require_role("admin")
        # Identity holds both 'reviewer' and 'admin' — the admin role satisfies the check.
        _call(dep, identity=AuthIdentity("u1", "ws1", ("reviewer", "admin")))

    def test_any_of_several_matching_roles_allows(self):
        dep = require_role("owner", "admin")
        _call(dep, identity=AuthIdentity("u1", "ws1", ("researcher", "admin")))


class TestRequireRoleDenied:
    """Identity present but no role intersection → 403."""

    def test_viewer_denied_when_owner_required(self):
        dep = require_role("owner")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ("viewer",)))
        assert exc_info.value.status_code == 403

    def test_reviewer_denied_for_catalog_write(self):
        dep = require_role("owner", "admin", "researcher")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ("reviewer",)))
        assert exc_info.value.status_code == 403

    def test_researcher_denied_for_admin_only_gate(self):
        dep = require_role("owner", "admin")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ("researcher",)))
        assert exc_info.value.status_code == 403

    def test_wrong_single_role_denied(self):
        dep = require_role("owner")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ("admin",)))
        # NOTE: admin is NOT in the allowed set here (require_role("owner") only).
        assert exc_info.value.status_code == 403

    def test_error_detail_is_insufficient_role(self):
        dep = require_role("owner")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ("viewer",)))
        assert exc_info.value.detail == "Insufficient role"


class TestRequireRoleEmptyRoles:
    """Identity with empty roles tuple must be denied (not silently allowed)."""

    def test_empty_roles_denied(self):
        dep = require_role("owner", "admin", "researcher")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ()))
        assert exc_info.value.status_code == 403

    def test_empty_roles_is_not_treated_as_wildcard(self):
        dep = require_role("viewer")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u1", "ws1", ()))
        assert exc_info.value.status_code == 403


class TestRequireRoleAllRoles:
    """Matrix spot-checks: each role vs a representative allow/deny case."""

    # owner — full access
    def test_owner_allowed_for_catalog_create(self):
        dep = require_role("owner", "admin", "researcher")
        _call(dep, identity=AuthIdentity("u", "w", ("owner",)))

    def test_owner_allowed_for_report_publish(self):
        dep = require_role("owner", "admin")
        _call(dep, identity=AuthIdentity("u", "w", ("owner",)))

    # admin — full access
    def test_admin_allowed_for_catalog_delete(self):
        dep = require_role("owner", "admin")
        _call(dep, identity=AuthIdentity("u", "w", ("admin",)))

    def test_admin_allowed_for_report_write(self):
        dep = require_role("owner", "admin", "researcher")
        _call(dep, identity=AuthIdentity("u", "w", ("admin",)))

    # researcher — catalog write, report write, NOT delete/publish
    def test_researcher_allowed_for_catalog_write(self):
        dep = require_role("owner", "admin", "researcher")
        _call(dep, identity=AuthIdentity("u", "w", ("researcher",)))

    def test_researcher_denied_for_catalog_delete(self):
        dep = require_role("owner", "admin")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u", "w", ("researcher",)))
        assert exc_info.value.status_code == 403

    def test_researcher_denied_for_report_publish(self):
        dep = require_role("owner", "admin")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u", "w", ("researcher",)))
        assert exc_info.value.status_code == 403

    # reviewer — run:read only, no mutations
    def test_reviewer_denied_for_catalog_write(self):
        dep = require_role("owner", "admin", "researcher")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u", "w", ("reviewer",)))
        assert exc_info.value.status_code == 403

    def test_reviewer_denied_for_report_write(self):
        dep = require_role("owner", "admin", "researcher")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u", "w", ("reviewer",)))
        assert exc_info.value.status_code == 403

    # viewer — zero permissions
    def test_viewer_denied_for_any_mutation(self):
        dep = require_role("owner", "admin", "researcher", "reviewer")
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=AuthIdentity("u", "w", ("viewer",)))
        assert exc_info.value.status_code == 403


class TestRequireRoleMarker:
    """The inner function must carry _is_require_role=True for the sweep test."""

    def test_inner_function_has_marker(self):
        inner = require_role("owner")
        assert getattr(inner, "_is_require_role", False) is True

    def test_each_call_returns_new_function_with_marker(self):
        f1 = require_role("owner")
        f2 = require_role("researcher")
        assert f1 is not f2
        assert f1._is_require_role is True  # type: ignore[attr-defined]
        assert f2._is_require_role is True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# RBAC-900: AuthIdentity.roles resilience contract
# ---------------------------------------------------------------------------


class TestAuthIdentityRolesContract:
    """Verify AuthIdentity.roles is always a tuple, never None or a list."""

    def test_roles_is_tuple_with_values(self):
        identity = AuthIdentity("u", "ws", ("owner", "admin"))
        assert isinstance(identity.roles, tuple)

    def test_roles_is_tuple_when_empty(self):
        identity = AuthIdentity("u", "ws", ())
        assert isinstance(identity.roles, tuple)
        assert identity.roles == ()

    def test_roles_is_not_none(self):
        identity = AuthIdentity("u", "ws", ())
        assert identity.roles is not None

    def test_roles_is_not_a_list(self):
        identity = AuthIdentity("u", "ws", ("researcher",))
        assert not isinstance(identity.roles, list)

    def test_frozen_dataclass_cannot_mutate_roles(self):
        identity = AuthIdentity("u", "ws", ("owner",))
        with pytest.raises((AttributeError, TypeError)):
            identity.roles = ("admin",)  # type: ignore[misc]

    # RBAC-900 cross-reference: empty tuple → 403 (tested in TestRequireRoleEmptyRoles above).
    # This assertion duplicates the critical path for explicit documentation:
    def test_empty_roles_tuple_is_denied_by_require_role(self):
        """Explicit cross-reference: empty roles=() on identity always means 403."""
        dep = require_role("owner")
        identity = AuthIdentity("u", "ws", ())
        assert identity.roles == ()  # confirmed: it is a tuple
        with pytest.raises(HTTPException) as exc_info:
            _call(dep, identity=identity)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# RBAC-001 sanity: ROLE_PERMISSIONS matrix
# ---------------------------------------------------------------------------


class TestRolePermissionsMatrix:
    """Sanity-checks that ROLE_PERMISSIONS has the correct shape and key entries."""

    EXPECTED_ROLES = {"owner", "admin", "researcher", "reviewer", "viewer"}
    EXPECTED_PERMISSIONS = {
        "catalog:create", "catalog:update", "catalog:delete",
        "report:create", "report:update", "report:publish",
        "run:read", "agent_job:launch",
    }

    def test_all_five_roles_present(self):
        assert set(ROLE_PERMISSIONS.keys()) == self.EXPECTED_ROLES

    def test_permissions_are_sets(self):
        for role, perms in ROLE_PERMISSIONS.items():
            assert isinstance(perms, set), f"ROLE_PERMISSIONS[{role!r}] is not a set"

    def test_owner_has_all_permissions(self):
        for perm in self.EXPECTED_PERMISSIONS:
            assert perm in ROLE_PERMISSIONS["owner"], f"owner missing {perm!r}"

    def test_admin_has_all_permissions(self):
        for perm in self.EXPECTED_PERMISSIONS:
            assert perm in ROLE_PERMISSIONS["admin"], f"admin missing {perm!r}"

    def test_researcher_cannot_delete_catalog(self):
        assert "catalog:delete" not in ROLE_PERMISSIONS["researcher"]

    def test_researcher_cannot_publish(self):
        assert "report:publish" not in ROLE_PERMISSIONS["researcher"]

    def test_researcher_can_write_catalog(self):
        assert "catalog:create" in ROLE_PERMISSIONS["researcher"]
        assert "catalog:update" in ROLE_PERMISSIONS["researcher"]

    def test_researcher_can_write_reports(self):
        assert "report:create" in ROLE_PERMISSIONS["researcher"]
        assert "report:update" in ROLE_PERMISSIONS["researcher"]

    def test_reviewer_has_no_mutations(self):
        mutations = {
            "catalog:create", "catalog:update", "catalog:delete",
            "report:create", "report:update", "report:publish",
            "agent_job:launch",
        }
        assert not (ROLE_PERMISSIONS["reviewer"] & mutations)

    def test_viewer_has_zero_permissions(self):
        assert ROLE_PERMISSIONS["viewer"] == set()

    def test_agent_job_launch_in_owner_and_admin(self):
        assert "agent_job:launch" in ROLE_PERMISSIONS["owner"]
        assert "agent_job:launch" in ROLE_PERMISSIONS["admin"]

    def test_agent_job_launch_not_in_researcher_or_below(self):
        for role in ("researcher", "reviewer", "viewer"):
            assert "agent_job:launch" not in ROLE_PERMISSIONS[role]
