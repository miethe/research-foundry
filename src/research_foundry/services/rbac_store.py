"""Durable RBAC store for Research Foundry (public-multiuser-release Phase 5).

Stores workspace memberships, user records, and canonical role definitions in a
long-lived SQLite database at ``<workspace>/.rf_state/rbac.db``.

# DURABILITY INVARIANT
# --------------------
# This database is NOT a rebuildable cache (unlike catalog.db under .rf_cache/).
# It contains authoritative user and workspace membership data that must survive
# catalog.db rebuilds, workspace moves, and partial re-initialisation.
#
# As a consequence, this module applies additive-only schema evolution:
#   - Every table is created with CREATE TABLE IF NOT EXISTS (idempotent).
#   - Schema migrations add columns/tables; they NEVER drop existing ones.
#   - PRAGMA user_version is bumped only when a real additive migration is applied.
#   - There is no schema-destruction helper in this module.  If you are tempted to
#     add one: DON'T.  Wipe the DB file manually if a destructive reset is needed
#     during development; production upgrades are additive-only, always.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from research_foundry.paths import FoundryPaths

# Increment this only when a real additive migration is applied (new column /
# new table).  The _ensure_schema logic checks this and runs the pending
# migration block before bumping.  NEVER use a version mismatch to trigger a
# drop-and-recreate.
RBAC_SCHEMA_VERSION: int = 2

# ---------------------------------------------------------------------------
# Canonical role definitions
# ---------------------------------------------------------------------------

_CANONICAL_ROLES: list[tuple[str, str]] = [
    ("owner", "Workspace owner — full control including member management"),
    ("admin", "Workspace administrator — manage resources and members"),
    ("researcher", "Active researcher — create and manage research runs"),
    ("reviewer", "Reviewer — read runs, add comments and review verdicts"),
    ("viewer", "Read-only observer"),
]

# ---------------------------------------------------------------------------
# DDL — additive-only, idempotent
# ---------------------------------------------------------------------------

_DDL: list[str] = [
    # workspaces: canonical workspace registry
    """
    CREATE TABLE IF NOT EXISTS workspaces (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        created_at  TEXT NOT NULL
    )
    """,
    # users: all users that have interacted with the workspace
    # display_name is optional; it may be populated later by the auth adapter
    """
    CREATE TABLE IF NOT EXISTS users (
        id           TEXT PRIMARY KEY,
        display_name TEXT,
        created_at   TEXT NOT NULL
    )
    """,
    # roles: canonical role catalogue (seeded by _seed_roles, never user-managed)
    """
    CREATE TABLE IF NOT EXISTS roles (
        name        TEXT PRIMARY KEY,
        description TEXT
    )
    """,
    # memberships: (user, workspace) → role assignments
    # P5.5 dependency: ON DELETE CASCADE from memberships to users/workspaces is
    # intentionally deferred pending the audit_event table decision.  Add it when
    # the audit log FK design is finalised.
    """
    CREATE TABLE IF NOT EXISTS memberships (
        user_id      TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        role         TEXT NOT NULL REFERENCES roles(name),
        created_at   TEXT NOT NULL,
        PRIMARY KEY (user_id, workspace_id)
    )
    """,
    # audit_event: append-only audit log (P5.5, schema version 2).
    # No UPDATE/DELETE paths exist on this table — rows are immutable by design.
    # mutation_type values (all 6 reserved now, 5 wired in P5.5):
    #   catalog_mutation | report_edit | agent_job_launched (N/A pending P4) |
    #   artifact_accepted | publish_preview | writeback
    """
    CREATE TABLE IF NOT EXISTS audit_event (
        audit_event_id     TEXT PRIMARY KEY,
        created_at         TEXT NOT NULL,
        mutation_type      TEXT NOT NULL,
        action             TEXT NOT NULL,
        target_ref         TEXT NOT NULL,
        actor_user_id      TEXT,
        actor_workspace_id TEXT,
        source_ref         TEXT,
        policy_snapshot    TEXT,
        result             TEXT NOT NULL,
        error_detail       TEXT,
        trace_id           TEXT,
        span_id            TEXT
    )
    """,
    # audit_health: single-row durable health state for AUDIT-004.
    # The CHECK (id = 1) constraint enforces the single-row invariant.
    """
    CREATE TABLE IF NOT EXISTS audit_health (
        id              INTEGER PRIMARY KEY CHECK (id = 1),
        healthy         INTEGER NOT NULL DEFAULT 1,
        last_probe_at   TEXT,
        last_success_at TEXT,
        error_detail    TEXT
    )
    """,
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _connect(paths: FoundryPaths) -> sqlite3.Connection:
    """Open (or create) the RBAC database at ``paths.rbac_db``.

    Creates ``.rf_state/`` if it does not exist.  Sets ``row_factory`` to
    ``sqlite3.Row`` for named-column access.  Enables foreign-key enforcement.
    Does NOT call ``_ensure_schema`` — callers that want schema bootstrapping
    should use ``bootstrap()`` instead.
    """
    paths.rf_state.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(paths.rbac_db), isolation_level=None)
    conn.row_factory = sqlite3.Row
    # Enable FK enforcement for every connection — SQLite disables it by default.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply the RBAC schema to ``conn`` using additive-only evolution.

    # DURABILITY INVARIANT — READ BEFORE EDITING
    # -------------------------------------------
    # catalog_service._ensure_schema drops and recreates the schema on a version
    # mismatch because catalog.db is a disposable, rebuildable read-model.
    # rbac.db is NOT disposable — it is the authoritative membership record.
    #
    # This function MUST NOT contain:
    #   - Calls to any schema-destruction helper (a function that drops tables)
    #   - Any statement that destroys or truncates an existing table or index
    #   - Unconditional CREATE TABLE (only CREATE TABLE IF NOT EXISTS is allowed)
    #
    # Migration procedure when RBAC_SCHEMA_VERSION is bumped:
    #   1. Add a new `if version < N:` migration block that applies only the
    #      incremental change (ALTER TABLE / CREATE TABLE IF NOT EXISTS for new
    #      tables).
    #   2. Increment RBAC_SCHEMA_VERSION at the top of this module.
    #   3. Leave all previous `if version < M:` blocks in place so databases at
    #      any old version reach the current schema in order.
    """
    (version,) = conn.execute("PRAGMA user_version").fetchone()

    if version < RBAC_SCHEMA_VERSION:
        # Initial schema creation (version 0 → 1) AND any subsequent migrations
        # are applied here in order.  All DDL uses IF NOT EXISTS so re-running
        # against an already-current database is a no-op.

        # version 0 → 1: base tables (workspaces, users, roles, memberships).
        for stmt in _DDL[:4]:
            conn.execute(stmt)

        if version < 2:
            # version 1 → 2: add audit_event and audit_health tables (P5.5).
            # Both use IF NOT EXISTS — idempotent against a fresh or v1 store.
            conn.execute(_DDL[4])  # audit_event
            conn.execute(_DDL[5])  # audit_health

        conn.execute(f"PRAGMA user_version = {RBAC_SCHEMA_VERSION}")
    else:
        # Database is already at or beyond current version — still run IF NOT
        # EXISTS creates so the connection is valid after concurrent init races.
        for stmt in _DDL:
            conn.execute(stmt)


def _seed_roles(conn: sqlite3.Connection) -> None:
    """Seed the canonical role catalogue.

    Uses ``INSERT OR IGNORE`` so this function is fully idempotent — running
    it on an already-seeded database is a no-op and does not overwrite
    customised descriptions.
    """
    conn.executemany(
        "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
        _CANONICAL_ROLES,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bootstrap(paths: FoundryPaths) -> sqlite3.Connection:
    """Open the RBAC database, ensure the schema is current, and seed roles.

    Returns an open connection for the caller to use.  The caller is
    responsible for closing it (or wrapping in a context manager).

    This function is safe to call multiple times — each call is idempotent:
    ``CREATE TABLE IF NOT EXISTS`` and ``INSERT OR IGNORE`` guarantee no data
    loss on repeated invocations.

    Example::

        conn = bootstrap(paths)
        try:
            upsert_user(conn, "usr_alice", "Alice Wonderland")
        finally:
            conn.close()
    """
    conn = _connect(paths)
    _ensure_schema(conn)
    _seed_roles(conn)
    return conn


# ---------------------------------------------------------------------------
# Upsert helpers (consumed by AUTH-102 local_static adapter and future adapters)
# ---------------------------------------------------------------------------


def upsert_user(
    conn: sqlite3.Connection,
    user_id: str,
    display_name: Optional[str] = None,
) -> None:
    """Insert or replace a user record.

    ``display_name`` is optional and may be ``None`` when the user is
    auto-provisioned from a token without a profile claim.

    Uses ``INSERT OR REPLACE`` to overwrite stale display names on subsequent
    logins.
    """
    now = _utcnow()
    conn.execute(
        "INSERT OR REPLACE INTO users (id, display_name, created_at) VALUES (?, ?, ?)",
        (user_id, display_name, now),
    )


def upsert_workspace(
    conn: sqlite3.Connection,
    workspace_id: str,
    name: str,
) -> None:
    """Insert or replace a workspace record.

    ``name`` must not be empty.  Uses ``INSERT OR REPLACE`` so a workspace
    rename is reflected on the next invocation.
    """
    now = _utcnow()
    conn.execute(
        "INSERT OR REPLACE INTO workspaces (id, name, created_at) VALUES (?, ?, ?)",
        (workspace_id, name, now),
    )


def upsert_membership(
    conn: sqlite3.Connection,
    user_id: str,
    workspace_id: str,
    role: str,
) -> None:
    """Insert or replace a (user, workspace) → role membership.

    ``role`` must be one of the 5 canonical names (owner, admin, researcher,
    reviewer, viewer).  The FK constraint on ``roles(name)`` will reject
    unknown values when foreign_keys = ON.

    Uses ``INSERT OR REPLACE`` so a role change is applied atomically.
    """
    now = _utcnow()
    conn.execute(
        "INSERT OR REPLACE INTO memberships (user_id, workspace_id, role, created_at)"
        " VALUES (?, ?, ?, ?)",
        (user_id, workspace_id, role, now),
    )


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
