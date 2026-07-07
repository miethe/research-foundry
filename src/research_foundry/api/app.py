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
  GET /api/reports/{run_id}/anchors       — report anchors (P2 Wave B; sensitivity-gated, no-leak 404)
  POST/GET /api/reports                  — Builder draft create/list (P3 Wave E)
  GET/DELETE /api/reports/{report_id}    — Builder draft detail/delete (rpt_ ids only)
  + full Block/ClaimLink/SourceLink/Revision/Verify/PublishPreview/Export sub-routes
  POST /api/agent-jobs                           — launch agent job (guard-gated, P4.4)
  GET  /api/agent-jobs/{id}                      — job detail
  GET  /api/agent-jobs/{id}/artifacts            — staged (unaccepted) artifacts
  GET  /api/agent-jobs/{id}/events               — SSE event stream (redacted)
  POST /api/agent-jobs/{id}/cancel               — cancel + credential cleanup
  POST /api/agent-jobs/{id}/accept               — SOLE WRITE PATH to catalog/report
  GET /data/governance.json    — governance config snapshot (→ fetchGovernanceConfig)
  GET  /api/catalog/stats                — catalog counts (→ fetchCatalogStats)
  GET  /api/catalog/search                — catalog search (→ fetchCatalogSearch)
  GET  /api/catalog/items/{id}            — catalog item detail (→ fetchCatalogItem)
  POST /api/catalog/import/run/{run_id}   — (re)import one run into the catalog
  POST /api/catalog/import                — (re)import every discovered run

Middleware stack (outermost → innermost):
  CORS → allowlist (optional) → auth (optional)

The allowlist middleware is only added when ``viewer.allowlist`` is non-empty.
The auth middleware is only added when ``auth.provider != "none"`` in
``foundry.yaml``; when ``auth.provider == "none"`` (the default) no auth
middleware is registered (true no-op — ``request.state`` never gains an
``identity`` attribute), UNLESS the legacy ``viewer.auth_mode: token`` field
is set (fail-closed backward-compatibility fallback — see Invariant 1 in the
``create_app`` source).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_logger = logging.getLogger(__name__)

from ..config import FoundryConfig
from .auth.adapters import local_static as _local_static_module  # noqa: F401 — triggers self-registration
from .auth.adapters.local_static import LocalStaticAuthProvider
from .auth.provider import get_provider, register_provider
from .middleware.allowlist import IPAllowlistMiddleware
from .middleware.auth import AuthProviderMiddleware
from .routers.agent_jobs import router as agent_jobs_router
from .routers.catalog import router as catalog_router
from .routers.reports import router as reports_router
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
    #
    # P5.1: registry-based provider replaces the legacy TokenAuthMiddleware
    # single-token wiring.  Provider selection happens exactly once here;
    # no router or service may branch on provider name — all branching is
    # resolved at app construction time.
    _provider_name = config.auth_provider()
    _auth_provider = get_provider(_provider_name)  # None when provider == "none"
    if _auth_provider is not None:
        # Re-initialise with runtime token configs and RBAC store.  The
        # module-level self-registration (bottom of local_static.py) inserts
        # an empty placeholder so the registry key exists; create_app replaces
        # it with a fully-configured instance tied to the actual foundry.yaml
        # token list.
        if _provider_name == "local_static":
            _auth_provider = LocalStaticAuthProvider(
                config.auth_local_static_tokens(),
                rbac_paths=config.paths,
            )
            register_provider(_auth_provider)
        app.add_middleware(AuthProviderMiddleware, provider=_auth_provider)
    elif _provider_name == "none" and config.viewer_auth_mode() == "token":
        # Invariant 1 — Fail-closed legacy fallback.
        #
        # Deployments that use the legacy ``viewer.auth_mode: token`` /
        # ``viewer.auth_token_env`` config without the new ``foundry.auth``
        # block are silently left unprotected by the primary path above.
        # Detect this condition here and install auth middleware derived from
        # the legacy single-token config so those deployments remain protected.
        #
        # This is fail-CLOSED: we install auth rather than skipping it.
        # A WARNING is emitted to nudge operators toward the new config.
        _logger.warning(
            "Deprecation: viewer.auth_mode='token' is deprecated. "
            "Migrate to foundry.auth.provider: local_static. "
            "See foundry.yaml for the new config format."
        )
        _legacy_token_env = config.viewer_auth_token_env()
        _legacy_tokens: list[dict] = [
            {
                "token_env": _legacy_token_env,
                "user_id": "legacy_token_user",
                "workspace_id": "default",
                "roles": ["owner"],
            }
        ]
        _auth_provider = LocalStaticAuthProvider(
            _legacy_tokens,
            rbac_paths=config.paths,
        )
        register_provider(_auth_provider)
        app.add_middleware(AuthProviderMiddleware, provider=_auth_provider)

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
    # Report Builder draft API (public-multiuser-release Phase 3 Wave E).
    # NOTE: GET /api/reports/{run_id}/anchors (runs_router) remains unambiguous
    # because it has a fixed '/anchors' suffix — different path-segment count.
    app.include_router(reports_router, prefix="/api", tags=["reports"])
    # Agent Jobs API (public-multiuser-release Phase 4 — P4.4).
    # Only registered when ``agents.enabled=true`` in foundry.yaml; defaults
    # to disabled (``False``) so the routes are absent in static-export and
    # shared-LAN deployments until P5 RBAC + workspace-isolation gates clear.
    if config.agents_enabled():
        app.include_router(agent_jobs_router, prefix="/api", tags=["agent-jobs"])

    return app


__all__ = ["create_app"]
