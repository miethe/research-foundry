"""Clerk auth adapter — RS256 JWKS-based JWT verification.

Implements the :class:`~research_foundry.api.auth.provider.AuthProvider` Protocol
for Clerk-issued JWTs.  On every authenticate() call the adapter:

1. Extracts a Bearer token from ``Authorization: Bearer <token>`` or the
   ``__session`` cookie.
2. Resolves the Clerk JWKS from ``<frontend_api_url>/.well-known/jwks.json``.
   The JWKS is **cached in-process after the first fetch** — subsequent calls
   to ``authenticate()`` make zero additional network requests.
3. Verifies the RS256 signature using PyJWT + cryptography.
4. Validates ``exp``, ``nbf``, and ``azp`` claims.
5. Returns an :class:`~research_foundry.api.auth.provider.AuthIdentity` on
   success, or ``None`` on *any* failure (expired, bad sig, missing claim,
   JWKS unavailable, parse error) — never raises past the adapter boundary.

Security invariants
-------------------
1. No raw token content, JWKS material, or key bytes are ever logged.
2. ``None`` is returned (not raised) for every auth failure — callers decide
   how to respond to absent identity.
3. MUST-STAY: only PyJWT + cryptography.  No Clerk SDK or Node-adjacent deps.
4. Private key material lives ONLY in test fixtures — never in this module.

Configuration shape (consumed by AUTH-104 / CLK-4.3)::

    auth:
      provider: clerk
      clerk:
        frontend_api_url: https://your-instance.clerk.accounts.dev
        azp_expected: your-frontend-publishable-key   # optional; omit to allow any azp

JWKS caching
------------
The JWKS is fetched once per :class:`ClerkAuthProvider` instance and held in
``self._jwks_cache``.  The cache is intentionally never invalidated within a
process lifetime (CLK-4.3 may add TTL-based refresh later).  In practice Clerk
JWKS keys rotate infrequently; if a key rotation causes a verification failure
the process should be restarted.

Role mapping
------------
CLK-4.2 formalises the ``org_role`` → RF-roles mapping into the module-level
``CLERK_ROLE_MAP`` constant.  The dict maps standard Clerk Organizations slugs
to the five RF role names (owner / admin / researcher / reviewer / viewer).
Unknown slugs fall back to ``"viewer"`` (least-privilege; never an error).

Note (FU-3): the ``org:reviewer`` slug is a *custom* Clerk role and requires
the Clerk Organizations Custom Roles add-on (paid plan) in production.  No
runtime check is performed; this note is purely informational.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from collections.abc import Callable

import jwt
from jwt.algorithms import RSAAlgorithm
from starlette.requests import Request

from research_foundry.api.auth.provider import AuthIdentity, register_provider

logger = logging.getLogger(__name__)

_BEARER_PREFIX = "Bearer "
_SESSION_COOKIE = "__session"

# ---------------------------------------------------------------------------
# CLK-4.2: Formalised role-mapping table (Clerk-adapter-internal).
#
# Maps Clerk Organizations role slugs to single RF role names.
# The default for any unmapped/unknown slug is "viewer" (least-privilege).
# This constant is intentionally NOT exported — it is an adapter implementation
# detail; provider.py and route code must not reference it directly.
#
# FU-3: "org:reviewer" requires the Clerk Organizations Custom Roles add-on
# (paid Clerk plan) in production.  No runtime billing check is performed here;
# this comment is a documentation note only.
# ---------------------------------------------------------------------------

CLERK_ROLE_MAP: dict[str, str] = {
    "org:owner": "owner",
    "org:admin": "admin",
    "org:member": "researcher",   # Reasonable default for a standard org member.
    "org:reviewer": "reviewer",   # Custom role — paid Clerk plan required (FU-3).
    "org:viewer": "viewer",
}


# ---------------------------------------------------------------------------
# JWKS fetch — default implementation (injectable for tests)
# ---------------------------------------------------------------------------


def _default_jwks_fetch(url: str) -> dict:
    """Fetch JWKS JSON from ``url`` using stdlib urllib.

    Returns the parsed JSON dict.  Raises on network or parse error so the
    caller (``_get_jwks``) can catch and return ``None``.

    This function is intentionally free of third-party HTTP deps so the
    clerk adapter can be used with only PyJWT + cryptography installed.
    """
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
        return json.loads(response.read())


# ---------------------------------------------------------------------------
# ClerkAuthProvider
# ---------------------------------------------------------------------------


class ClerkAuthProvider:
    """Clerk JWKS-based RS256 auth adapter.

    Parameters
    ----------
    frontend_api_url:
        Clerk Frontend API URL, e.g. ``https://your.clerk.accounts.dev``.
        The adapter appends ``/.well-known/jwks.json`` to build the JWKS URL.
    azp_expected:
        Optional.  When provided, the ``azp`` claim in the JWT must exactly
        match this value.  When ``None`` (default), any non-empty ``azp``
        value is accepted.
    jwks_fetch_fn:
        Optional override for the JWKS HTTP fetch.  Accepts a callable
        ``(url: str) -> dict`` and replaces :func:`_default_jwks_fetch`.
        Primarily for dependency-injection in unit tests so no real network
        calls are needed.  Defaults to :func:`_default_jwks_fetch`.
    """

    id: str = "clerk"

    def __init__(
        self,
        frontend_api_url: str,
        azp_expected: str | None = None,
        jwks_fetch_fn: Callable[[str], dict] | None = None,
    ) -> None:
        if not frontend_api_url:
            raise ValueError("ClerkAuthProvider: frontend_api_url must be non-empty.")
        # Strip trailing slash for consistent URL construction.
        self._frontend_api_url = frontend_api_url.rstrip("/")
        self._azp_expected = azp_expected
        self._jwks_fetch_fn: Callable[[str], dict] = jwks_fetch_fn or _default_jwks_fetch
        # In-process cache.  None = not yet fetched; dict = cached result.
        self._jwks_cache: dict | None = None

    # ------------------------------------------------------------------
    # AuthProvider Protocol
    # ------------------------------------------------------------------

    @classmethod
    def available(cls) -> bool:
        """Return ``True`` only when both Clerk configuration preconditions are met.

        Preconditions (CLK-4.3 dark-by-default gate):
          1. ``auth.clerk_frontend_api`` is non-empty in ``foundry.yaml``.
          2. ``auth.clerk_outbound_internet_enabled`` is explicitly ``True``.

        Returns ``False`` when either condition is unmet, when no
        ``foundry.yaml`` exists in the working tree, or when any exception
        occurs during config loading.  The safe default is **never** to enable
        Clerk silently — the operator must opt in explicitly.

        The config is loaded lazily on each call (no module-level state) so
        that test patches on ``FoundryConfig`` take effect reliably.
        """
        try:
            # Lazy import avoids circular-import risk at module init time and
            # lets tests monkeypatch FoundryConfig cleanly.
            from research_foundry.config import FoundryConfig  # noqa: PLC0415
            cfg = FoundryConfig.load()
            frontend_api = cfg.auth_clerk_frontend_api()
            outbound_ok = cfg.auth_clerk_outbound_internet_enabled()
            return bool(frontend_api) and outbound_ok
        except Exception:  # noqa: BLE001 — config unavailable → safe default False
            return False

    def authenticate(self, request: Request) -> AuthIdentity | None:
        """Resolve an :class:`AuthIdentity` from a Clerk-signed JWT in ``request``.

        Token sources (in priority order):
          1. ``Authorization: Bearer <token>`` header.
          2. ``__session`` cookie.

        Returns ``None`` for any of:
          - No token present in header or cookie.
          - JWKS unavailable or parse failure.
          - JWT header missing ``kid``.
          - No key in JWKS matches the JWT's ``kid``.
          - Signature verification failure (wrong key, malformed token).
          - Token expired (``exp`` check).
          - Token not yet valid (``nbf`` check).
          - ``azp`` claim absent.
          - ``sub`` claim absent.
          - Any unexpected exception.

        Never raises.  Never logs raw token contents, JWKS material, or key bytes.
        """
        try:
            token = self._extract_token(request)
            if token is None:
                return None

            jwks = self._get_jwks()
            if jwks is None:
                logger.warning("clerk: JWKS unavailable — cannot authenticate request.")
                return None

            # Decode header without verification to get kid.
            try:
                header = jwt.get_unverified_header(token)
            except jwt.exceptions.DecodeError:
                logger.debug("clerk: failed to decode JWT header.")
                return None

            kid = header.get("kid")
            if not kid:
                logger.debug("clerk: JWT header missing 'kid'.")
                return None

            # Locate the matching public key in JWKS.
            public_key = self._find_key(jwks, kid)
            if public_key is None:
                logger.debug("clerk: no JWKS key matches kid=%r.", kid)
                return None

            # Verify signature and standard claims (exp, nbf).
            try:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    options={
                        "verify_exp": True,
                        "verify_nbf": True,
                        # We check azp and sub manually below.
                        "require": [],
                    },
                )
            except jwt.exceptions.ExpiredSignatureError:
                logger.debug("clerk: JWT expired.")
                return None
            except jwt.exceptions.ImmatureSignatureError:
                logger.debug("clerk: JWT not yet valid (nbf).")
                return None
            except jwt.exceptions.InvalidSignatureError:
                logger.debug("clerk: JWT signature invalid.")
                return None
            except jwt.exceptions.PyJWTError:
                logger.debug("clerk: JWT decode/verify failed.")
                return None

            # Validate required Clerk-specific claims.
            user_id: str | None = payload.get("sub")
            if not user_id:
                logger.debug("clerk: JWT missing 'sub' claim.")
                return None

            azp: str | None = payload.get("azp")
            if not azp:
                logger.debug("clerk: JWT missing 'azp' claim.")
                return None

            if self._azp_expected is not None and azp != self._azp_expected:
                logger.debug("clerk: JWT 'azp' mismatch (expected %r).", self._azp_expected)
                return None

            # Derive workspace_id from org_id (fall back to "default").
            workspace_id: str = payload.get("org_id") or "default"

            # Role mapping — CLK-4.2 formalised via CLERK_ROLE_MAP.
            org_role: str = payload.get("org_role", "")
            roles = self._map_org_role(org_role)

            return AuthIdentity(
                user_id=user_id,
                workspace_id=workspace_id,
                roles=tuple(roles),
            )

        except Exception:  # noqa: BLE001 — never raise past adapter boundary
            logger.debug("clerk: unexpected error during authentication.", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_token(self, request: Request) -> str | None:
        """Return the raw JWT string from the request, or ``None`` if absent."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith(_BEARER_PREFIX):
            token = auth_header[len(_BEARER_PREFIX):]
            if token:
                return token

        # Fall back to __session cookie.
        session_cookie = request.cookies.get(_SESSION_COOKIE)
        if session_cookie:
            return session_cookie

        return None

    def _get_jwks(self) -> dict | None:
        """Return cached JWKS, fetching on first call.

        The JWKS is fetched **at most once per instance** — this is the hard
        NFR documented in the module docstring.  Subsequent calls return the
        cached dict without any I/O.

        Returns ``None`` if the initial fetch fails.
        """
        if self._jwks_cache is not None:
            return self._jwks_cache

        jwks_url = f"{self._frontend_api_url}/.well-known/jwks.json"
        try:
            result = self._jwks_fetch_fn(jwks_url)
            if not isinstance(result, dict):
                logger.warning("clerk: JWKS fetch returned non-dict; ignoring.")
                return None
            self._jwks_cache = result
            return self._jwks_cache
        except Exception:  # noqa: BLE001
            logger.warning("clerk: JWKS fetch failed.", exc_info=True)
            return None

    @staticmethod
    def _find_key(jwks: dict, kid: str):
        """Return the RSA public key for ``kid``, or ``None`` if not found.

        Uses :func:`jwt.algorithms.RSAAlgorithm.from_jwk` to convert the JWK
        dict to a ``cryptography`` RSA public key object suitable for
        ``jwt.decode(..., key)``.

        Never logs key material.
        """
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                try:
                    return RSAAlgorithm.from_jwk(key_data)
                except Exception:  # noqa: BLE001
                    logger.debug("clerk: failed to load JWK for kid=%r.", kid)
                    return None
        return None

    @staticmethod
    def _map_org_role(org_role: str) -> list[str]:
        """Map a Clerk ``org_role`` string to a list of RF role names.

        CLK-4.2 formalised mapping (driven by module-level ``CLERK_ROLE_MAP``):
          ``org:owner``      → [owner]
          ``org:admin``      → [admin]
          ``org:member``     → [researcher]
          ``org:reviewer``   → [reviewer]  (custom slug; paid Clerk plan — FU-3)
          ``org:viewer``     → [viewer]
          (anything else)    → [viewer]    (least-privilege; never an error)

        The return value is always a non-empty list (AuthIdentity wraps it as a
        tuple; returning a list here preserves the original CLK-4.1 contract).
        """
        return [CLERK_ROLE_MAP.get(org_role, "viewer")]


# ---------------------------------------------------------------------------
# Self-registration — importing this module registers the provider.
# Note: ClerkAuthProvider requires frontend_api_url at construction time.
# We register a sentinel instance that returns available()=True but will fail
# to authenticate (no URL configured) until AUTH-104 constructs the real instance.
# The real instance will call register_provider() again to replace this sentinel.
# ---------------------------------------------------------------------------

# Sentinel: provides Protocol conformance and reserves "clerk" in the registry.
# AUTH-104 (CLK-4.3) will replace this with a properly configured instance.
_sentinel = ClerkAuthProvider(frontend_api_url="https://unset.clerk.accounts.dev")
register_provider(_sentinel)

__all__ = ["ClerkAuthProvider"]
