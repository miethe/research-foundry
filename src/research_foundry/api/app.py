"""FastAPI application factory for the Research Foundry loopback API.

Usage::

    from research_foundry.api.app import create_app
    from research_foundry.config import FoundryConfig

    app = create_app(FoundryConfig.load())

Endpoints registered by this factory:

  GET /health                  — liveness probe
  GET /api/runs                — list all runs (→ fetchRunList)
  GET /api/runs/{run_id}       — run detail   (→ fetchRunDetail)
  GET /api/runs/{run_id}/claims           — claim ledger  (→ fetchClaimLedger)
  GET /api/runs/{run_id}/sources/{sc_id}  — resolved source (→ fetchSourceCard)
  GET /data/governance.json    — governance config snapshot (→ fetchGovernanceConfig)
  GET  /api/catalog/stats                — catalog counts (→ fetchCatalogStats)
  GET  /api/catalog/search                — catalog search (→ fetchCatalogSearch)
  GET  /api/catalog/items/{id}            — catalog item detail (→ fetchCatalogItem)
  POST /api/catalog/import/run/{run_id}   — (re)import one run into the catalog
  POST /api/catalog/import                — (re)import every discovered run

Middleware stack (outermost → innermost):
  CORS → allowlist (optional) → auth (optional)

The allowlist middleware is only added when ``viewer.allowlist`` is non-empty.
The auth middleware is only added when ``viewer.auth_mode == "token"``.
When ``auth_mode == "none"`` no auth middleware is registered (true no-op).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import FoundryConfig
from .middleware.allowlist import IPAllowlistMiddleware
from .middleware.auth import TokenAuthMiddleware
from .routers.catalog import router as catalog_router
from .routers.runs import router as runs_router

# Default origins covered by a plain wildcard pattern are not supported by
# CORSMiddleware; we use explicit prefixes that cover localhost variants.
_DEFAULT_ALLOWED_ORIGINS: list[str] = [
    "http://localhost",
    "http://127.0.0.1",
]


def _build_cors_origins(config: FoundryConfig) -> list[str]:
    """Resolve CORS allowed-origins from config, falling back to defaults.

    Uses ``config.viewer_cors_origins()`` (key ``cors_origins`` in the
    ``viewer`` block) as the canonical source.  When the list is non-empty it
    replaces the defaults entirely so operators have full control.

    NOTE: The previous implementation read ``viewer.api_cors_origins``; that
    key was renamed to ``cors_origins`` in Phase P3.  This function now uses
    the P3-canonical accessor ``viewer_cors_origins()`` so the documented key
    actually takes effect.
    """
    origins = config.viewer_cors_origins()
    # viewer_cors_origins() returns ["*"] as the default; return the
    # explicit localhost prefixes instead so the wildcard doesn't mask errors.
    if origins == ["*"]:
        return _DEFAULT_ALLOWED_ORIGINS
    return origins


def create_app(config: FoundryConfig) -> FastAPI:
    """Construct and return the Research Foundry FastAPI application.

    The returned app is fully wired: CORS middleware and all routers are
    already registered.  Callers may mount it directly or pass it to
    ``uvicorn.run``.

    Args:
        config: Loaded :class:`~research_foundry.config.FoundryConfig`
            instance used to configure CORS origins and other settings.

    Returns:
        A ready-to-serve :class:`fastapi.FastAPI` instance.
    """
    app = FastAPI(
        title="Research Foundry API",
        description="Loopback read API for the Research Foundry runs viewer.",
        version="0.1.0",
    )

    # --- Middleware (outermost → innermost: CORS → allowlist → auth) ----------
    #
    # Starlette/FastAPI middleware is processed in *reverse* insertion order at
    # runtime (last added = outermost).  We add them innermost-first so the
    # final execution order matches the documented stack.
    #
    # 1. Auth (innermost — added first, runs last)
    auth_mode = config.viewer_auth_mode()
    if auth_mode == "token":
        # Security invariant 6: only add auth middleware when auth_mode==token.
        token_env_var = config.viewer_auth_token_env()
        app.add_middleware(TokenAuthMiddleware, token_env_var=token_env_var)

    # 2. IP allowlist (middle — added second, runs before auth)
    allowlist = config.viewer_allowlist()
    if allowlist:
        app.add_middleware(IPAllowlistMiddleware, allowlist=allowlist)

    # 3. CORS (outermost — added last, runs first)
    allowed_origins = _build_cors_origins(config)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        # Also allow the wildcard localhost:* pattern via regex so any port works.
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health ---------------------------------------------------------------
    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe — always returns 200 ``{"status": "ok"}``."""
        return {"status": "ok"}

    # --- Governance snapshot --------------------------------------------------
    # Matches the fetchGovernanceConfig() static path: GET /data/governance.json
    # Serializes the two viewer-relevant keys from FoundryConfig.governance to
    # match the GovernanceConfig TS shape produced by prebuild-static-data.mjs.
    @app.get("/data/governance.json", tags=["meta"])
    def governance_config() -> dict[str, Any]:
        """Return the governance config snapshot.

        Extracts ``key_profiles`` and ``policy_rules`` from
        :attr:`~research_foundry.config.FoundryConfig.governance` — the same
        two keys that ``prebuild-static-data.mjs`` writes into the static
        ``governance.json``.  Missing keys are emitted as ``null`` so the FE
        always receives a well-formed :class:`GovernanceConfig` object.
        """
        gov = config.governance
        key_profiles = gov.get("key_profiles") if isinstance(gov, dict) else None
        policy_rules = gov.get("policy_rules") if isinstance(gov, dict) else None
        return {
            "key_profiles": key_profiles,
            "policy_rules": policy_rules,
        }

    # --- Routers --------------------------------------------------------------
    # All run endpoints live under /api (client.ts: LOOPBACK_BASE = ".../api")
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    # Shared evidence catalog (public-multiuser-release Phase 1).
    app.include_router(catalog_router, prefix="/api", tags=["catalog"])

    return app


__all__ = ["create_app"]
