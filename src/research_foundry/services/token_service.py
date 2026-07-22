"""Access-token issuance, verification, and revocation (public-multiuser-release
Phase 2, ACT-202).

OQ-1 resolution: this module lives under ``services/`` as a peer of
``rbac_store.py`` / ``audit_service.py`` — it is business logic (crypto,
role-ceiling policy) layered on top of ``rbac_store``'s pure data-access
helpers, not an ``api/auth`` adapter itself.  ``AuthProviderMiddleware``
(``api/middleware/auth.py``, ACT-203) calls :func:`verify_token` directly; it
is NOT registered in the ``AuthProvider`` registry (``api/auth/provider.py``)
because token-store resolution runs *before* the provider-adapter chain, not
as one more adapter in it.

Security invariants (FR-7..FR-10)
----------------------------------
1. The plaintext secret is generated fresh per token via :mod:`secrets`
   (CSPRNG, >= 256 bits) and returned to the caller **exactly once**, at
   issuance (:class:`IssuedToken.plaintext`).  It is never stored, logged, or
   echoed back by any other function in this module.
2. Only a keyed HMAC-SHA256 digest of the secret (:func:`_hash_token`) and a
   short non-secret prefix are persisted, via ``rbac_store.create_access_token``.
3. All verification comparisons use ``hmac.compare_digest`` — never ``==``.
   A prefix miss still performs a same-shape dummy comparison so resolution
   time does not depend on whether a candidate row was found (closes the
   prefix-based timing side channel called out in ACT-203's acceptance
   criteria).
4. Revocation and expiry (FR-10) and the PAT role-ceiling (FR-9) are checked
   fresh on every :func:`verify_token` call — never cached, never resolved
   only at issuance.
5. No function in this module ever raises on "no match" / "invalid" /
   "expired" / "revoked" — :func:`verify_token` returns ``None`` uniformly
   for all of those so the composite auth chain's fall-through-to-provider
   behavior (AC-2, AC-4) never has to distinguish a genuine token-store
   outage from an unrecognized token.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from research_foundry.paths import FoundryPaths
from research_foundry.services import rbac_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# secrets.token_urlsafe(n) draws n random bytes -- 32 bytes = 256 bits of
# entropy (FR-7's "opaque random secret (>= 256 bits entropy)"), independent
# of the base64-url-encoded string length that results.
_TOKEN_ENTROPY_BYTES = 32

# Length (in characters of the encoded token string) of the non-secret
# lookup prefix.  Also doubles as the HMAC key for _hash_token -- see that
# function's docstring for why this is a safe, salt-free design.
_PREFIX_LEN = 8

# Fixed-shape dummy digest used to burn equivalent hmac.compare_digest time
# on a token-prefix miss (timing-side-channel guard, mirrors the
# comparison shape a real prefix hit would take).
_DUMMY_HASH = hashlib.sha256(b"research-foundry-token-service-timing-guard").hexdigest()

# Role hierarchy, highest-privilege first -- reuses rbac_store's single
# canonical ordering rather than re-declaring it, so the two modules can
# never drift out of sync on role precedence.
_ROLE_RANK: dict[str, int] = {
    name: idx for idx, (name, _description) in enumerate(rbac_store._CANONICAL_ROLES)
}

PRINCIPAL_TYPES = frozenset({"service", "user_pat"})

# The 5 canonical role names, re-exported from rbac_store so callers (the
# admin API, Phase 3) can validate a requested role BEFORE calling into this
# module — an unrecognized role would otherwise only surface as a raw
# sqlite3.IntegrityError from the DB's FK constraint on roles(name).
VALID_ROLES: frozenset[str] = frozenset(name for name, _description in rbac_store._CANONICAL_ROLES)

__all__ = [
    "IssuedToken",
    "ResolvedIdentity",
    "TokenServiceError",
    "RoleCeilingError",
    "issue_service_account_token",
    "issue_user_pat",
    "rotate_service_account_token",
    "verify_token",
    "revoke_token",
    "get_token",
    "list_tokens",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TokenServiceError(Exception):
    """Base class for token_service domain errors.

    Never constructed with secret material -- messages reference ids
    (service_account_id, workspace_id, role) only.
    """


class RoleCeilingError(TokenServiceError):
    """Raised at ISSUANCE when a PAT's requested role exceeds the issuer's
    current role (FR-9).  The resolution-time re-check does not raise this --
    see :func:`verify_token`, which returns ``None`` instead so a stale PAT
    degrades to "unauthenticated", not a 500."""


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuedToken:
    """Result of a successful token issuance.

    ``plaintext`` is the ONLY place the raw secret ever appears in this
    module's public surface.  Callers (the admin API, Phase 3) MUST return it
    to the operator in the issuance response body and must never persist,
    log, or re-display it afterwards -- it cannot be recovered once this
    value goes out of scope.
    """

    token_id: str
    plaintext: str
    token_prefix: str
    principal_type: str
    principal_id: str
    workspace_id: str
    role: str
    expires_at: Optional[str]


@dataclass(frozen=True)
class ResolvedIdentity:
    """Identity resolved from a verified token (returned by :func:`verify_token`)."""

    token_id: str
    principal_type: str
    principal_id: str
    workspace_id: str
    role: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Matches ``rbac_store._utcnow``'s format exactly so ``expires_at``
    comparisons (plain string comparison, see :func:`verify_token`) are
    consistent across both modules.
    """
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _role_rank(role: str) -> int:
    """Return the privilege rank of *role* (0 = highest, larger = lower).

    An unrecognized role name ranks below every canonical role (fail-safe:
    an unknown role can never satisfy a role-ceiling check as "equal or
    higher privilege").
    """
    return _ROLE_RANK.get(role, len(_ROLE_RANK))


def _generate_secret() -> tuple[str, str]:
    """Generate a fresh opaque token.  Returns ``(full_token, token_prefix)``."""
    full_token = secrets.token_urlsafe(_TOKEN_ENTROPY_BYTES)
    return full_token, full_token[:_PREFIX_LEN]


def _hash_token(full_token: str, token_prefix: str) -> str:
    """Return the persisted hash for *full_token* (FR-7's "salted hash").

    Uses HMAC-SHA256 keyed by the token's OWN non-secret prefix over the
    remainder of the token.  This is a deliberate salt-free design: the
    pre-image (``full_token``) is freshly generated per-token by a CSPRNG
    with >= 256 bits of entropy (see ``_generate_secret``), so there is no
    low-entropy-guessing threat a traditional per-row salt column defends
    against (unlike a human-chosen password).  Keying the HMAC by the
    prefix still gives domain separation from a bare
    ``sha256(secret)`` digest at zero schema cost -- no separate salt
    column is needed in ``access_tokens`` (see rbac_store's access_tokens
    DDL comment, OQ-2 area).
    """
    remainder = full_token[len(token_prefix):]
    return hmac.new(
        key=token_prefix.encode("utf-8"),
        msg=remainder.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _issue(
    conn,
    *,
    principal_type: str,
    principal_id: str,
    workspace_id: str,
    role: str,
    created_by: Optional[str],
    expires_at: Optional[str],
) -> IssuedToken:
    """Shared issuance path for both service-account and PAT tokens.

    Generates the secret, hashes it, and persists the row via
    ``rbac_store.create_access_token``.  Never called directly by external
    callers -- use :func:`issue_service_account_token` or
    :func:`issue_user_pat`, both of which resolve/validate the principal
    first.
    """
    if principal_type not in PRINCIPAL_TYPES:
        raise TokenServiceError(f"invalid principal_type: {principal_type!r}")

    full_token, token_prefix = _generate_secret()
    token_hash = _hash_token(full_token, token_prefix)
    token_id = f"tok_{uuid.uuid4().hex}"

    rbac_store.create_access_token(
        conn,
        token_id=token_id,
        principal_type=principal_type,
        principal_id=principal_id,
        workspace_id=workspace_id,
        role=role,
        token_hash=token_hash,
        token_prefix=token_prefix,
        created_by=created_by,
        expires_at=expires_at,
    )

    return IssuedToken(
        token_id=token_id,
        plaintext=full_token,
        token_prefix=token_prefix,
        principal_type=principal_type,
        principal_id=principal_id,
        workspace_id=workspace_id,
        role=role,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Public API — issuance
# ---------------------------------------------------------------------------


def issue_service_account_token(
    paths: FoundryPaths,
    *,
    service_account_id: str,
    created_by: Optional[str] = None,
    expires_at: Optional[str] = None,
) -> IssuedToken:
    """Issue a new access token for an existing service account (FR-8).

    The token's ``role``/``workspace_id`` are taken from the service
    account's own record — a service account has exactly ONE assigned role
    (FR-8), so callers cannot request an arbitrary role for it here.

    Raises
    ------
    TokenServiceError
        If *service_account_id* does not exist, or is disabled.
    """
    conn = rbac_store.bootstrap(paths)
    try:
        account = rbac_store.get_service_account(conn, service_account_id)
        if account is None:
            raise TokenServiceError(f"service account not found: {service_account_id!r}")
        if account.get("disabled_at"):
            raise TokenServiceError(f"service account is disabled: {service_account_id!r}")
        return _issue(
            conn,
            principal_type="service",
            principal_id=service_account_id,
            workspace_id=account["workspace_id"],
            role=account["role"],
            created_by=created_by,
            expires_at=expires_at,
        )
    finally:
        conn.close()


def issue_user_pat(
    paths: FoundryPaths,
    *,
    issuer_user_id: str,
    workspace_id: str,
    role: str,
    expires_at: Optional[str] = None,
) -> IssuedToken:
    """Issue a personal access token on behalf of *issuer_user_id* (FR-9).

    Role-ceiling (FR-9): *role* must be <= the issuer's CURRENT role in
    *workspace_id*, enforced here at issuance.  :func:`verify_token`
    independently re-checks this same ceiling at every resolution, so a
    subsequent downgrade of the issuer's role invalidates the PAT's elevated
    effective privilege immediately -- no cache to invalidate, no restart
    required.

    Raises
    ------
    TokenServiceError
        If *issuer_user_id* has no membership in *workspace_id*.
    RoleCeilingError
        If *role* outranks the issuer's current role.
    """
    conn = rbac_store.bootstrap(paths)
    try:
        issuer_role = rbac_store.get_member_role(conn, issuer_user_id, workspace_id)
        if issuer_role is None:
            raise TokenServiceError(
                f"issuer {issuer_user_id!r} has no membership in workspace {workspace_id!r}"
            )
        if _role_rank(role) < _role_rank(issuer_role):
            raise RoleCeilingError(
                f"requested role {role!r} exceeds issuer's current role {issuer_role!r}"
            )
        return _issue(
            conn,
            principal_type="user_pat",
            principal_id=issuer_user_id,
            workspace_id=workspace_id,
            role=role,
            created_by=issuer_user_id,
            expires_at=expires_at,
        )
    finally:
        conn.close()


def rotate_service_account_token(
    paths: FoundryPaths,
    *,
    service_account_id: str,
    created_by: Optional[str] = None,
    expires_at: Optional[str] = None,
) -> IssuedToken:
    """Issue a fresh token for *service_account_id*, revoking every currently
    active (non-revoked) token for it FIRST (Phase 3 ACT-301 rotation
    semantics).

    "Rotate" == revoke-then-issue: by the time this returns, at most the
    freshly-issued token is valid for this principal — any token issued by a
    prior call to this function or to :func:`issue_service_account_token` is
    immediately revoked (FR-10 -- no restart, no cache to invalidate, takes
    effect on the very next :func:`verify_token` call for the old token).
    This is also the sole issuance path exposed for service accounts by the
    admin API (Phase 3): a bare "issue with no prior token" call is simply a
    rotation with zero active tokens to revoke, so there is no separate
    issuance route/function to keep in sync with this one.

    Raises
    ------
    TokenServiceError
        If *service_account_id* does not exist or is disabled (propagated
        from :func:`issue_service_account_token`).
    """
    existing = list_tokens(paths, principal_id=service_account_id, principal_type="service")
    for row in existing:
        if row.get("revoked_at") is None:
            revoke_token(paths, row["id"])
    return issue_service_account_token(
        paths,
        service_account_id=service_account_id,
        created_by=created_by,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Public API — verification (AC-2, AC-4, FR-9..FR-11)
# ---------------------------------------------------------------------------


def verify_token(paths: FoundryPaths, supplied_token: str) -> Optional[ResolvedIdentity]:
    """Verify *supplied_token* against the ``access_tokens`` store.

    Returns ``None`` uniformly for every "not a valid credential" case:
    empty/malformed input, unknown prefix, hash mismatch, revoked, expired,
    disabled service account, or a PAT whose issuer no longer meets the
    role ceiling.  **Never raises** for any of these -- callers (the
    composite auth chain, ACT-203) rely on this to fall through to the
    configured provider adapter without risking a 500 (AC-4).

    Timing-safety: on a token-prefix miss, still runs an
    ``hmac.compare_digest`` of matching shape against a fixed dummy hash so
    the code takes a comparable path whether or not the prefix matched.
    """
    if not supplied_token or len(supplied_token) <= _PREFIX_LEN:
        return None

    token_prefix = supplied_token[:_PREFIX_LEN]
    conn = rbac_store.bootstrap(paths)
    try:
        row = rbac_store.verify_access_token(conn, token_prefix)
        if row is None:
            # Prefix miss -- burn a comparison of the same shape as a real
            # hash check so resolution time doesn't leak "prefix known".
            hmac.compare_digest(_DUMMY_HASH, _DUMMY_HASH)
            return None

        candidate_hash = _hash_token(supplied_token, token_prefix)
        if not hmac.compare_digest(candidate_hash, row["token_hash"]):
            return None

        # FR-10: revocation and expiry are resolution-time checks, never
        # cached -- a revoke/expiry takes effect on the very next request.
        if row.get("revoked_at"):
            return None
        expires_at = row.get("expires_at")
        if expires_at and expires_at <= _utcnow():
            return None

        principal_type = row["principal_type"]
        role = row["role"]

        if principal_type == "service":
            # Defense in depth: a disabled service account's tokens die
            # immediately too, without a separate revocation sweep.
            account = rbac_store.get_service_account(conn, row["principal_id"])
            if account is None or account.get("disabled_at"):
                return None
        elif principal_type == "user_pat":
            # FR-9 role-ceiling RE-CHECK at resolution time: if the issuer is
            # no longer a member, or their current role no longer meets the
            # token's stored role, the token is invalid -- never silently
            # downgraded, always rejected outright (fail-closed).
            issuer_role = rbac_store.get_member_role(
                conn, row["principal_id"], row["workspace_id"]
            )
            if issuer_role is None or _role_rank(issuer_role) > _role_rank(role):
                return None

        # OQ-4: last_used_at is a best-effort, fail-open write -- never
        # block or fail an otherwise-successful resolution on this.
        try:
            rbac_store.touch_access_token_last_used(conn, row["id"], _utcnow())
        except Exception:  # noqa: BLE001
            logger.warning(
                "token_service: last_used_at update failed for token_id=%s (non-fatal)",
                row["id"],
                exc_info=True,
            )

        return ResolvedIdentity(
            token_id=row["id"],
            principal_type=principal_type,
            principal_id=row["principal_id"],
            workspace_id=row["workspace_id"],
            role=role,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API — revocation + listing
# ---------------------------------------------------------------------------


def revoke_token(paths: FoundryPaths, token_id: str) -> None:
    """Revoke *token_id* immediately (FR-10) -- no restart required."""
    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.revoke_access_token(conn, token_id)
    finally:
        conn.close()


def list_tokens(
    paths: FoundryPaths,
    *,
    workspace_id: Optional[str] = None,
    principal_id: Optional[str] = None,
    principal_type: Optional[str] = None,
) -> list[dict]:
    """List access tokens for admin display.  Never includes ``token_hash``.

    *principal_type* (``"service"`` / ``"user_pat"``) lets the admin API
    (Phase 3) list only PATs or only service-account tokens directly at the
    data layer, rather than post-filtering in the router.
    """
    conn = rbac_store.bootstrap(paths)
    try:
        return rbac_store.list_access_tokens(
            conn,
            workspace_id=workspace_id,
            principal_id=principal_id,
            principal_type=principal_type,
        )
    finally:
        conn.close()


def get_token(paths: FoundryPaths, token_id: str) -> Optional[dict]:
    """Return a single access-token row by id, or ``None`` if unknown.

    Never includes ``token_hash``.  Used by the admin API (Phase 3) for
    existence/ownership checks before revoking a PAT or service-account
    token — never for verification (that stays on :func:`verify_token`).
    """
    conn = rbac_store.bootstrap(paths)
    try:
        return rbac_store.get_access_token(conn, token_id)
    finally:
        conn.close()
