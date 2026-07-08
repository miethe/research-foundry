"""Share-link store for Research Foundry (public-multiuser-release Phase 5.6).

Manages a ``share_links`` table in the durable RBAC store (``.rf_state/rbac.db``).
Share links are READ-ONLY, sensitivity-scoped, and expiry-aware.

DURABILITY INVARIANT
--------------------
Share links live in ``rbac.db``, NOT ``catalog.db``.  ``catalog.db`` drops and
rebuilds on user_version mismatch (D2 lesson from Phase 5.1) — that silently
invalidates live share links for any callers who have already distributed a token.
``rbac.db`` uses additive-only schema evolution: tables are created with
``CREATE TABLE IF NOT EXISTS`` and never dropped.

The share_links schema is independent of :data:`~research_foundry.services.rbac_store.RBAC_SCHEMA_VERSION`
— it is applied on every :func:`bootstrap_share_store` call via an idempotent
``CREATE TABLE IF NOT EXISTS``, without incrementing the RBAC version counter.

Security design
---------------
- Share tokens are 256-bit URL-safe random strings (``secrets.token_urlsafe``).
- The token is the sole bearer credential for read access.  No session or role
  check is needed at resolution time — the token IS the auth.
- Sensitivity is enforced **at both creation AND resolution time**.  The check at
  creation is advisory (a fast gate); the check at resolution time is the
  authoritative one (PRD AC-2: sensitivity is re-verified against the current
  draft state, never trusted from creation time alone).
"""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from research_foundry.paths import FoundryPaths

# ---------------------------------------------------------------------------
# DDL — additive-only, idempotent
# ---------------------------------------------------------------------------

_SHARE_LINKS_DDL = """
CREATE TABLE IF NOT EXISTS share_links (
    share_token           TEXT PRIMARY KEY,
    report_draft_id       TEXT NOT NULL,
    sensitivity_threshold TEXT NOT NULL,
    created_by            TEXT,
    created_at            TEXT NOT NULL,
    expires_at            TEXT,
    revoked               INTEGER NOT NULL DEFAULT 0
)
"""

# Cryptographically-random token length: 256-bit entropy (urlsafe base64 → ~43 chars).
_TOKEN_BYTES = 32


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _connect_shares(paths: FoundryPaths) -> sqlite3.Connection:
    """Open (or create) ``.rf_state/rbac.db`` for share-link operations.

    Mirrors :func:`~research_foundry.services.rbac_store._connect` semantics:
    creates ``.rf_state/`` if absent, enables foreign-key enforcement, sets
    ``row_factory`` to ``sqlite3.Row``, and uses autocommit
    (``isolation_level=None``).
    """
    paths.rf_state.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(paths.rbac_db), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_share_schema(conn: sqlite3.Connection) -> None:
    """Apply the share_links DDL idempotently (``CREATE TABLE IF NOT EXISTS``)."""
    conn.execute(_SHARE_LINKS_DDL)


def _utcnow() -> str:
    """Return current UTC time as ISO-8601 string with a ``Z`` suffix."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bootstrap_share_store(paths: FoundryPaths) -> sqlite3.Connection:
    """Open ``rbac.db`` and ensure the ``share_links`` table exists.

    Returns an open :class:`sqlite3.Connection`.  The **caller is responsible
    for closing it** (or wrapping in a context manager).

    Idempotent: calling this function multiple times is safe — the DDL uses
    ``CREATE TABLE IF NOT EXISTS``.

    Example::

        conn = bootstrap_share_store(paths)
        try:
            ...
        finally:
            conn.close()
    """
    conn = _connect_shares(paths)
    _ensure_share_schema(conn)
    return conn


def create_share_link(
    paths: FoundryPaths,
    *,
    report_draft_id: str,
    sensitivity_threshold: str,
    created_by: Optional[str] = None,
    expires_at: Optional[str] = None,
) -> dict:
    """Create a new share link for *report_draft_id* at *sensitivity_threshold*.

    Returns the share link record dict including the newly generated
    ``share_token``.  The token is a cryptographically-random URL-safe string
    — it is the bearer credential for read access to the shared report.

    The caller is responsible for verifying that the draft's current sensitivity
    label does not exceed *sensitivity_threshold* before calling this function
    (enforced in the router layer).  Sensitivity is additionally re-checked at
    resolution time (:func:`resolve_share_link`) — the token alone cannot bypass
    sensitivity gating (PRD AC-2).
    """
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = _utcnow()
    conn = bootstrap_share_store(paths)
    try:
        conn.execute(
            "INSERT INTO share_links"
            " (share_token, report_draft_id, sensitivity_threshold,"
            " created_by, created_at, expires_at, revoked)"
            " VALUES (?, ?, ?, ?, ?, ?, 0)",
            (token, report_draft_id, sensitivity_threshold, created_by, now, expires_at),
        )
    finally:
        conn.close()
    return {
        "share_token": token,
        "report_draft_id": report_draft_id,
        "sensitivity_threshold": sensitivity_threshold,
        "created_by": created_by,
        "created_at": now,
        "expires_at": expires_at,
    }


def resolve_share_link(
    paths: FoundryPaths,
    share_token: str,
) -> Optional[dict]:
    """Resolve a share token to its stored record.

    Returns ``None`` when:

    * Token is not found in the store.
    * Token has been revoked (``revoked = 1``).
    * Token has expired (``expires_at < utcnow()``).

    This function returns the stored record only — it does **not** re-apply the
    sensitivity threshold check against the current draft state.  Callers
    **MUST** re-apply the sensitivity rank check against the draft they load
    (PRD AC-2: sensitivity is checked at resolution time, not trusted from
    creation time alone).
    """
    conn = bootstrap_share_store(paths)
    try:
        row = conn.execute(
            "SELECT share_token, report_draft_id, sensitivity_threshold,"
            " created_by, created_at, expires_at, revoked"
            " FROM share_links WHERE share_token = ?",
            (share_token,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    d = dict(row)
    if d["revoked"]:
        return None
    if d.get("expires_at"):
        # ISO-8601 UTC string comparison is valid for non-DST timestamps.
        if d["expires_at"] < _utcnow():
            return None
    return d


def list_share_links(
    paths: FoundryPaths,
    *,
    report_draft_id: Optional[str] = None,
) -> list[dict]:
    """List active (non-revoked) share links.

    When *report_draft_id* is supplied, results are filtered to that draft.
    Expired links are NOT filtered out here — callers that care about expiry
    should check ``expires_at`` themselves, or use :func:`resolve_share_link`.
    """
    conn = bootstrap_share_store(paths)
    try:
        if report_draft_id:
            rows = conn.execute(
                "SELECT share_token, report_draft_id, sensitivity_threshold,"
                " created_by, created_at, expires_at, revoked"
                " FROM share_links WHERE report_draft_id = ? AND revoked = 0",
                (report_draft_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT share_token, report_draft_id, sensitivity_threshold,"
                " created_by, created_at, expires_at, revoked"
                " FROM share_links WHERE revoked = 0",
            ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def revoke_share_link(
    paths: FoundryPaths,
    share_token: str,
) -> bool:
    """Revoke a share link by token.

    Returns ``True`` if a row was updated, ``False`` if the token was not found.
    Revocation is idempotent — revoking an already-revoked token is a no-op
    and returns ``True`` (the row exists and was already revoked).
    """
    conn = bootstrap_share_store(paths)
    try:
        cur = conn.execute(
            "UPDATE share_links SET revoked = 1 WHERE share_token = ?",
            (share_token,),
        )
        return cur.rowcount > 0
    finally:
        conn.close()


__all__ = [
    "bootstrap_share_store",
    "create_share_link",
    "resolve_share_link",
    "list_share_links",
    "revoke_share_link",
]
