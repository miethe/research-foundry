"""local_static auth adapter — multi-token Bearer → AuthIdentity mapping.

This adapter is designed for local/self-hosted deployments where a fixed set
of users is provisioned via environment variables.  Each token maps to a
(user_id, workspace_id, roles) triple that is declared in ``foundry.yaml``
under ``auth.local_static.tokens``.

Configuration shape (consumed by AUTH-104 which passes token_configs at init)::

    auth:
      provider: local_static
      local_static:
        tokens:
          - token_env: RF_SERVE_TOKEN_ALICE
            user_id: alice
            workspace_id: default
            roles: [owner]
          - token_env: RF_SERVE_TOKEN_BOB
            user_id: bob
            workspace_id: default
            roles: [researcher]

Security invariants
-------------------
1. Token values are read from ``os.environ`` at **request time**, not at
   construction.  Only the *name* of each env var is stored on the instance.
2. All candidate tokens are compared via ``hmac.compare_digest`` — a
   constant-time byte comparison — for every request.  The scan is a *full*
   scan: we do NOT short-circuit after a match so that the comparison time is
   independent of which (if any) token matches.  This prevents timing-oracle
   attacks against multi-user token lists.
3. Token values are never logged, raised, or included in any exception message
   or stack trace.
4. Missing, empty, or malformed ``Authorization`` headers cause ``None`` to be
   returned, never an exception.
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Optional

from starlette.requests import Request

from research_foundry.api.auth.provider import AuthIdentity, register_provider
from research_foundry.paths import FoundryPaths
from research_foundry.services import rbac_store

logger = logging.getLogger(__name__)

_BEARER_PREFIX = "Bearer "


class LocalStaticAuthProvider:
    """Multi-token static auth adapter for local/self-hosted deployments.

    Parameters
    ----------
    token_configs:
        List of dicts, each with keys:
          ``token_env``    — name of the env var holding the secret token value
          ``user_id``      — user identifier to return on a match
          ``workspace_id`` — workspace the token grants access to
          ``roles``        — list of role strings for this user in the workspace
    rbac_paths:
        Optional ``FoundryPaths`` instance.  When supplied, the adapter calls
        ``_bootstrap_rbac`` during ``__init__`` to upsert all configured users,
        workspaces, and memberships into the durable RBAC store.  This is
        safe to call on every app restart because all upserts are idempotent.
    """

    id: str = "local_static"

    def __init__(
        self,
        token_configs: list[dict],
        rbac_paths: Optional[FoundryPaths] = None,
    ) -> None:
        # Startup validation: each entry must have all required fields.
        # This surfaces typos as clear ValueError at app startup rather than
        # as a KeyError → 500 at request time (P2-b fix).
        _REQUIRED_FIELDS = ("token_env", "user_id", "workspace_id", "roles")
        for i, entry in enumerate(token_configs):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"local_static token entry at index {i} must be a dict, "
                    f"got {type(entry).__name__!r}. "
                    "Check foundry.yaml auth.local_static.tokens."
                )
            for field in _REQUIRED_FIELDS:
                if field not in entry:
                    raise ValueError(
                        f"local_static token entry at index {i} is missing required "
                        f"field {field!r}. "
                        "Check foundry.yaml auth.local_static.tokens."
                    )

        # Store only the config dicts (which hold env var *names*, not values).
        # Token values are resolved at request time — never at construction.
        self._token_configs: list[dict] = list(token_configs)

        if rbac_paths is not None:
            self._bootstrap_rbac(rbac_paths)

    # ------------------------------------------------------------------
    # AuthProvider Protocol
    # ------------------------------------------------------------------

    def available(self) -> bool:
        """Always available — this adapter has no optional dependencies."""
        return True

    def authenticate(self, request: Request) -> Optional[AuthIdentity]:
        """Resolve an :class:`AuthIdentity` from the Bearer token in ``request``.

        Returns ``None`` for any of:
          - missing or non-Bearer ``Authorization`` header
          - empty token after stripping the "Bearer " prefix
          - token that does not match any configured candidate

        Never raises; never logs a token value.
        """
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith(_BEARER_PREFIX):
            return None

        supplied_str = auth_header[len(_BEARER_PREFIX):]
        if not supplied_str:
            return None

        supplied_bytes = supplied_str.encode("utf-8")

        # Full-scan with constant-time comparison.
        # matched_config is set on a match but the loop always runs to
        # completion — this prevents timing oracles against multi-token lists.
        matched_config: Optional[dict] = None

        for cfg in self._token_configs:
            token_env: str = cfg.get("token_env", "")
            if not token_env:
                # Misconfigured entry — skip silently (no value to compare).
                continue

            expected_str = os.environ.get(token_env, "")
            if not expected_str:
                # Env var is unset or empty — skip; do NOT treat as a match.
                logger.debug(
                    "local_static: token env var %r is unset; skipping candidate.",
                    token_env,
                )
                continue

            # Constant-time comparison — SECURITY INVARIANT 2.
            # We intentionally do NOT short-circuit after a match.
            if hmac.compare_digest(supplied_bytes, expected_str.encode("utf-8")):
                matched_config = cfg
            # Loop continues regardless.

        if matched_config is None:
            return None

        # Belt-and-suspenders guard against malformed entries that bypass
        # __init__ validation (e.g., directly patched _token_configs in tests
        # or dynamically modified token lists).  Returning None instead of
        # raising KeyError prevents a 500 even in adversarial conditions.
        user_id = matched_config.get("user_id")
        workspace_id = matched_config.get("workspace_id")
        if not user_id or not workspace_id:
            try:
                idx = self._token_configs.index(matched_config)
            except ValueError:
                idx = -1
            logger.warning(
                "local_static: matched entry at index %d is malformed "
                "(missing user_id/workspace_id), treating as no-match.",
                idx,
            )
            return None

        roles: list[str] = matched_config.get("roles", [])
        return AuthIdentity(
            user_id=user_id,
            workspace_id=workspace_id,
            roles=tuple(roles),
        )

    # ------------------------------------------------------------------
    # RBAC bootstrap
    # ------------------------------------------------------------------

    def _bootstrap_rbac(self, paths: FoundryPaths) -> None:
        """Upsert all configured users, workspaces, and memberships into the RBAC store.

        This method is called at adapter init time when ``rbac_paths`` is
        provided.  All operations use ``INSERT OR REPLACE`` semantics so the
        call is fully idempotent — repeating it on every app restart is safe
        and produces no data loss.

        Each token config entry results in:
          - one :func:`~rbac_store.upsert_workspace` call
          - one :func:`~rbac_store.upsert_user` call
          - one :func:`~rbac_store.upsert_membership` call (first role, or
            "viewer" if the roles list is empty)
        """
        conn = rbac_store.bootstrap(paths)
        try:
            for cfg in self._token_configs:
                workspace_id: str = cfg.get("workspace_id", "")
                user_id: str = cfg.get("user_id", "")
                roles: list[str] = cfg.get("roles", [])
                role = roles[0] if roles else "viewer"

                if not workspace_id or not user_id:
                    logger.warning(
                        "local_static: skipping rbac bootstrap for incomplete config"
                        " (missing user_id or workspace_id).",
                    )
                    continue

                rbac_store.upsert_workspace(conn, workspace_id, workspace_id)
                rbac_store.upsert_user(conn, user_id, display_name=user_id)
                rbac_store.upsert_membership(conn, user_id, workspace_id, role)

        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Self-registration — importing this module registers the provider.
# ---------------------------------------------------------------------------

register_provider(LocalStaticAuthProvider(token_configs=[]))

__all__ = ["LocalStaticAuthProvider"]
