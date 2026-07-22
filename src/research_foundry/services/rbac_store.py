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
RBAC_SCHEMA_VERSION: int = 3

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
    #   catalog_mutation | report_edit | agent_job_launched (wired: ACT-204, multi_user only) |
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
    # service_accounts: non-interactive named principals (public-multiuser
    # Phase 2, ACT-201, FR-8).  Each service account has exactly one role and
    # is workspace-scoped; there is no login/session for a service account --
    # it only ever acts via an issued access_tokens row.
    """
    CREATE TABLE IF NOT EXISTS service_accounts (
        id           TEXT PRIMARY KEY,
        name         TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        role         TEXT NOT NULL REFERENCES roles(name),
        description  TEXT,
        created_by   TEXT,
        created_at   TEXT NOT NULL,
        disabled_at  TEXT
    )
    """,
    # access_tokens: opaque-secret machine/PAT credentials (ACT-201, FR-6..FR-10).
    #
    # OQ-2 resolution: `principal_id` is a single polymorphic column whose
    # target table is selected by the `principal_type` discriminator
    # (`service` -> service_accounts.id, `user_pat` -> users.id).  SQLite has
    # no "conditional"/partial FOREIGN KEY that can point at one of two tables
    # depending on a sibling column's value, so this is app-level referential
    # integrity: every write path (token_service.py) resolves and validates
    # the target row itself *before* inserting here -- see
    # token_service.issue_service_account_token/issue_user_pat.  Do not add a
    # `REFERENCES` clause to `principal_id`; it would only ever cover one of
    # the two principal types and silently omit FK enforcement for the other.
    #
    # `token_hash` and `token_prefix` are the ONLY persisted representation of
    # the secret -- the plaintext token is returned to the caller exactly once
    # at issuance (token_service.IssuedToken.plaintext) and is never written
    # here or anywhere else.  `token_prefix` is intentionally non-secret (see
    # token_service._hash_token) and exists purely for the indexed lookup FR-11
    # requires -- it must never be treated as sufficient to authenticate.
    """
    CREATE TABLE IF NOT EXISTS access_tokens (
        id             TEXT PRIMARY KEY,
        principal_type TEXT NOT NULL CHECK (principal_type IN ('service', 'user_pat')),
        principal_id   TEXT NOT NULL,
        workspace_id   TEXT NOT NULL,
        role           TEXT NOT NULL REFERENCES roles(name),
        token_hash     TEXT NOT NULL,
        token_prefix   TEXT NOT NULL,
        created_by     TEXT,
        created_at     TEXT NOT NULL,
        expires_at     TEXT,
        revoked_at     TEXT,
        last_used_at   TEXT
    )
    """,
    # Indexed prefix lookup (FR-11: "indexed prefix lookup + hash compare").
    """
    CREATE INDEX IF NOT EXISTS idx_access_tokens_token_prefix
        ON access_tokens (token_prefix)
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

        if version < 3:
            # version 2 → 3: add service_accounts, access_tokens, and the
            # access_tokens prefix index (public-multiuser Phase 2, ACT-201).
            # All three use IF NOT EXISTS — idempotent against a fresh, v1, or
            # v2 store, and safe to re-run on an already-v3 store.
            conn.execute(_DDL[6])  # service_accounts
            conn.execute(_DDL[7])  # access_tokens
            conn.execute(_DDL[8])  # idx_access_tokens_token_prefix

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
# Read helpers (consumed by admin API, P5.6 T2)
# ---------------------------------------------------------------------------


def list_workspace_members(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> list[dict]:
    """Return all members of *workspace_id* with their role assignments.

    Each entry in the returned list is a dict with keys:

    ``user_id``
        Provider-scoped user identifier.
    ``email``
        The user's display name (populated by the auth adapter on first
        login; may be ``None`` when a token-configured user has never
        authenticated via the API).
    ``role``
        The canonical role string (owner / admin / researcher / reviewer /
        viewer).

    Returns an empty list when no memberships exist for the workspace.
    """
    rows = conn.execute(
        "SELECT m.user_id, u.display_name AS email, m.role "
        "FROM memberships m "
        "LEFT JOIN users u ON m.user_id = u.id "
        "WHERE m.workspace_id = ?",
        (workspace_id,),
    ).fetchall()
    return [
        {
            "user_id": row["user_id"],
            "email": row["email"],
            "role": row["role"],
        }
        for row in rows
    ]


def get_workspace(
    conn: sqlite3.Connection,
    workspace_id: str,
) -> Optional[dict]:
    """Return the workspace record for *workspace_id*, or ``None`` if absent."""
    row = conn.execute(
        "SELECT id, name, created_at FROM workspaces WHERE id = ?",
        (workspace_id,),
    ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"]}


def update_member_role(
    conn: sqlite3.Connection,
    user_id: str,
    workspace_id: str,
    role: str,
) -> None:
    """Update the role of *user_id* in *workspace_id*.

    ``role`` must be one of the 5 canonical names (owner, admin, researcher,
    reviewer, viewer).  The FK constraint on ``roles(name)`` will reject
    unknown values when foreign_keys = ON.

    Raises
    ------
    KeyError
        When no membership row exists for ``(user_id, workspace_id)``.  The
        caller must create the membership first via :func:`upsert_membership`
        if it may not yet exist.
    """
    result = conn.execute(
        "UPDATE memberships SET role = ? WHERE user_id = ? AND workspace_id = ?",
        (role, user_id, workspace_id),
    )
    if result.rowcount == 0:
        raise KeyError(
            f"Member {user_id!r} not found in workspace {workspace_id!r}. "
            "Use upsert_membership() to create the membership first."
        )


def get_member_role(
    conn: sqlite3.Connection,
    user_id: str,
    workspace_id: str,
) -> Optional[str]:
    """Return *user_id*'s CURRENT role in *workspace_id*, or ``None`` if absent.

    Consumed by ``token_service`` for FR-9's PAT role-ceiling check, both at
    issuance AND at every resolution (never cached) — a role downgrade for
    the issuing user takes effect on the very next request that resolves a
    PAT they previously issued.
    """
    row = conn.execute(
        "SELECT role FROM memberships WHERE user_id = ? AND workspace_id = ?",
        (user_id, workspace_id),
    ).fetchone()
    return row["role"] if row is not None else None


# ---------------------------------------------------------------------------
# Service-account + access-token helpers (public-multiuser Phase 2, ACT-201)
# ---------------------------------------------------------------------------


def create_service_account(
    conn: sqlite3.Connection,
    *,
    service_account_id: str,
    name: str,
    workspace_id: str,
    role: str,
    description: Optional[str] = None,
    created_by: Optional[str] = None,
) -> None:
    """Insert a new service account row (FR-8).

    ``role`` must be one of the 5 canonical role names; the FK constraint on
    ``roles(name)`` rejects unknown values.  Raises ``sqlite3.IntegrityError``
    if ``service_account_id`` already exists — callers should generate a
    fresh id (e.g. ``uuid4``) rather than relying on upsert semantics here,
    unlike the ``upsert_*`` helpers above.
    """
    now = _utcnow()
    conn.execute(
        "INSERT INTO service_accounts"
        " (id, name, workspace_id, role, description, created_by, created_at, disabled_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
        (service_account_id, name, workspace_id, role, description, created_by, now),
    )


def get_service_account(
    conn: sqlite3.Connection,
    service_account_id: str,
) -> Optional[dict]:
    """Return the service account row for *service_account_id*, or ``None``."""
    row = conn.execute(
        "SELECT id, name, workspace_id, role, description, created_by, created_at, disabled_at"
        " FROM service_accounts WHERE id = ?",
        (service_account_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_service_accounts(
    conn: sqlite3.Connection,
    workspace_id: Optional[str] = None,
) -> list[dict]:
    """List service accounts, optionally filtered to *workspace_id*."""
    if workspace_id is not None:
        rows = conn.execute(
            "SELECT id, name, workspace_id, role, description, created_by, created_at, disabled_at"
            " FROM service_accounts WHERE workspace_id = ? ORDER BY created_at",
            (workspace_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, workspace_id, role, description, created_by, created_at, disabled_at"
            " FROM service_accounts ORDER BY created_at"
        ).fetchall()
    return [dict(row) for row in rows]


def disable_service_account(conn: sqlite3.Connection, service_account_id: str) -> None:
    """Set ``disabled_at`` on *service_account_id* (idempotent — safe to call twice).

    Disabling a service account does NOT revoke its previously-issued
    tokens by itself — ``token_service.verify_token`` independently checks
    ``disabled_at`` at resolution time (never cached), so the effect is the
    same as an immediate revocation without a separate token-by-token sweep.
    """
    conn.execute(
        "UPDATE service_accounts SET disabled_at = ? WHERE id = ? AND disabled_at IS NULL",
        (_utcnow(), service_account_id),
    )


def create_access_token(
    conn: sqlite3.Connection,
    *,
    token_id: str,
    principal_type: str,
    principal_id: str,
    workspace_id: str,
    role: str,
    token_hash: str,
    token_prefix: str,
    created_by: Optional[str] = None,
    expires_at: Optional[str] = None,
) -> None:
    """Insert a new access-token row.  Never called with plaintext secret material —

    ``token_hash`` must already be the hashed representation (see
    ``token_service._hash_token``); this function has no crypto logic of its
    own and stores whatever ``token_hash``/``token_prefix`` it is given
    verbatim.  ``principal_type`` must be ``"service"`` or ``"user_pat"`` —
    the table's ``CHECK`` constraint rejects any other value.
    """
    now = _utcnow()
    conn.execute(
        "INSERT INTO access_tokens"
        " (id, principal_type, principal_id, workspace_id, role, token_hash,"
        "  token_prefix, created_by, created_at, expires_at, revoked_at, last_used_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
        (
            token_id,
            principal_type,
            principal_id,
            workspace_id,
            role,
            token_hash,
            token_prefix,
            created_by,
            now,
            expires_at,
        ),
    )


def verify_access_token(
    conn: sqlite3.Connection,
    token_prefix: str,
) -> Optional[dict]:
    """Look up an access-token row by its non-secret ``token_prefix`` (FR-11).

    This is a pure indexed data-layer lookup — it performs NO hash
    comparison, expiry check, or revocation check.  Those are
    ``token_service.verify_token``'s responsibility (including the
    dummy-hash compare it runs on a prefix miss to close the timing side
    channel).  Returns the full row — including ``token_hash`` — as a dict,
    or ``None`` if no row has this prefix.

    Multiple rows could theoretically share a prefix (birthday collision on
    a short, non-secret slice of a high-entropy token); this returns the
    first match only.  ``token_service`` still performs the real
    constant-time hash comparison against the candidate's ``token_hash``
    before trusting it, so a prefix collision alone can never authenticate.
    """
    row = conn.execute(
        "SELECT id, principal_type, principal_id, workspace_id, role, token_hash,"
        " token_prefix, created_by, created_at, expires_at, revoked_at, last_used_at"
        " FROM access_tokens WHERE token_prefix = ? LIMIT 1",
        (token_prefix,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def revoke_access_token(conn: sqlite3.Connection, token_id: str) -> None:
    """Set ``revoked_at`` on *token_id* (idempotent — safe to call twice).

    FR-10: revocation takes effect at the next resolution, no restart
    required — ``token_service.verify_token`` checks ``revoked_at`` fresh on
    every call rather than caching it.
    """
    conn.execute(
        "UPDATE access_tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
        (_utcnow(), token_id),
    )


def list_access_tokens(
    conn: sqlite3.Connection,
    *,
    workspace_id: Optional[str] = None,
    principal_id: Optional[str] = None,
    principal_type: Optional[str] = None,
) -> list[dict]:
    """List access tokens for admin display — NEVER includes ``token_hash``.

    Optionally filtered to *workspace_id*, *principal_id*, and/or
    *principal_type* (``"service"`` / ``"user_pat"`` — public-multiuser-release
    Phase 3, ACT-302: lets callers list only PATs or only service-account
    tokens without post-filtering in Python).  Callers that need the hash
    for verification must use :func:`verify_access_token` instead; this
    listing helper intentionally omits it so no code path that only needs a
    display/audit projection can accidentally leak or log it.
    """
    clauses: list[str] = []
    params: list[str] = []
    if workspace_id is not None:
        clauses.append("workspace_id = ?")
        params.append(workspace_id)
    if principal_id is not None:
        clauses.append("principal_id = ?")
        params.append(principal_id)
    if principal_type is not None:
        clauses.append("principal_type = ?")
        params.append(principal_type)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        "SELECT id, principal_type, principal_id, workspace_id, role, token_prefix,"
        " created_by, created_at, expires_at, revoked_at, last_used_at"
        f" FROM access_tokens{where} ORDER BY created_at",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def get_access_token(conn: sqlite3.Connection, token_id: str) -> Optional[dict]:
    """Return a single access-token row by id — NEVER includes ``token_hash``.

    Public-multiuser-release Phase 3 (ACT-301/ACT-302): used for
    ownership/existence checks on the revoke routes (PAT self-vs-admin
    scoping, service-account token revoke) — never for verification, which
    stays exclusively on :func:`verify_access_token`'s prefix-keyed lookup.
    Returns ``None`` if *token_id* is unknown.
    """
    row = conn.execute(
        "SELECT id, principal_type, principal_id, workspace_id, role, token_prefix,"
        " created_by, created_at, expires_at, revoked_at, last_used_at"
        " FROM access_tokens WHERE id = ?",
        (token_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def touch_access_token_last_used(
    conn: sqlite3.Connection,
    token_id: str,
    ts: str,
) -> None:
    """Best-effort ``last_used_at`` write (OQ-4).  Callers must treat this as

    fail-open: ``token_service.verify_token`` wraps this call in its own
    try/except so a write error here (e.g. a locked/full disk) can never
    block or fail an otherwise-successful token resolution — mirroring
    ``audit_service.record_event``'s fail-open contract, just without a
    dedicated health-probe table since this is advisory metadata, not an
    audit trail.
    """
    conn.execute(
        "UPDATE access_tokens SET last_used_at = ? WHERE id = ?",
        (ts, token_id),
    )


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
