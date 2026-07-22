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
  POST /api/runs/{run_id}/writeback/approve      — approve evidence bundle + dispatch
                                                     to writeback targets (RBAC-gated,
                                                     runs-writeback-approve-dispatch Phase 2)
  GET /data/governance.json    — governance config snapshot (→ fetchGovernanceConfig)
  GET  /api/catalog/stats                — catalog counts (→ fetchCatalogStats)
  GET  /api/catalog/search                — catalog search (→ fetchCatalogSearch)
  GET  /api/catalog/items/{id}            — catalog item detail (→ fetchCatalogItem)
  POST /api/catalog/import/run/{run_id}   — (re)import one run into the catalog
  POST /api/catalog/import                — (re)import every discovered run

Middleware stack (outermost → innermost):
  CORS → allowlist (optional) → auth (optional) → rate-limit (optional)

The allowlist middleware is only added when ``viewer.allowlist`` is non-empty.
The auth middleware is only added when ``auth.provider != "none"`` in
``foundry.yaml``; when ``auth.provider == "none"`` (the default) no auth
middleware is registered (true no-op — ``request.state`` never gains an
``identity`` attribute), UNLESS the legacy ``viewer.auth_mode: token`` field
is set (fail-closed backward-compatibility fallback — see Invariant 1 in the
``create_app`` source).
The rate-limit middleware is only added when ``auth.rate_limit.enabled`` is
``True`` (default).  It keys on ``(AuthIdentity.user_id, route)`` so one
user's burst cannot throttle another.  Requests with no ``request.state.identity``
(``auth_mode=none`` deployments) pass through unconditionally.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import FoundryConfig
from .auth.adapters import (
    local_static as _local_static_module,  # noqa: F401 — triggers self-registration
)
from .auth.adapters.local_static import LocalStaticAuthProvider
from .auth.provider import get_provider, register_provider
from .middleware.allowlist import IPAllowlistMiddleware
from .middleware.auth import AuthProviderMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .routers.admin import router as admin_router
from .routers.agent_jobs import router as agent_jobs_router
from .routers.assertions import router as assertions_router
from .routers.audit import router as audit_router
from .routers.auth_identity import router as auth_identity_router
from .routers.catalog import router as catalog_router
from .routers.reports import router as reports_router
from .routers.runs import router as runs_router
from .routers.writeback import router as writeback_router

_logger = logging.getLogger(__name__)

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
    # --- ACT-102: deployment_mode fail-closed startup gate (FR-4, partial a-c) ---
    # P1 stub — condition (d) (DI-1 acknowledgment, FR-13) is wired in Phase 4
    # (ACT-402). No-op for deployment_mode=single_user (the default), so this
    # cannot regress the LAN/NUC single-user default (FR-2). Runs before any
    # app state is constructed so a misconfigured multi_user deployment
    # refuses to start rather than serving with a fail-open gap.
    config.deployment_mode_validate(bind_host=config.viewer_bind_host())

    app = FastAPI(
        title="Research Foundry API",
        description="Loopback read API for the Research Foundry runs viewer.",
        version="0.1.0",
    )

    # --- P5.6 T5: Resolve and store RBAC enforcement state -------------------
    #
    # resolve_rbac_enforced() applies the fail-closed rule:
    #   rbac_enforcement=disabled + non-loopback bind_host → raises ValueError.
    # Calling it here means create_app() itself raises before any middleware or
    # route is registered, preventing a mis-configured server from starting.
    #
    # The resolved bool is stored on app.state so require_role() can read it
    # per-request without re-computing from config on every call.
    #
    # NOTE: auth_provider() is called again below for middleware registration;
    # we use a try/except here so a bad provider value still surfaces correctly
    # at startup rather than silently masking to "none".
    try:
        _rbac_provider_name = config.auth_provider()
    except (ValueError, Exception):  # noqa: BLE001
        _rbac_provider_name = "none"
    app.state.rbac_enforced = config.resolve_rbac_enforced(
        _rbac_provider_name,
        config.viewer_bind_host(),
    )

    # --- WKSP-304 TASK-1.2: Resolve and store workspace isolation enforcement --
    #
    # resolve_workspace_isolation_enforced() applies the same fail-closed rule as
    # resolve_rbac_enforced() above: workspace_isolation_enforcement=disabled +
    # non-loopback bind_host → raises ValueError, refusing startup.
    #
    # This is orthogonal to app.state.rbac_enforced (independent security gate —
    # see WKSP-304 decision log). The resolved bool is stored on app.state so a
    # future query-scoping layer (Phase 4) can read it per-request without
    # re-computing from config on every call.
    #
    # INERT as of TASK-1.2: nothing reads or consumes app.state.workspace_isolation_enforced
    # yet to make an enforcement decision. That wiring lands in Phase 4.
    app.state.workspace_isolation_enforced = config.resolve_workspace_isolation_enforced(
        _rbac_provider_name,
        config.viewer_bind_host(),
    )

    # --- P5.6 T2: In-memory rate-limit overrides store -----------------------
    # PATCH /api/admin/rate-limit-config writes here; GET reads it merged with
    # config defaults.  Cleared on restart (intentional — use foundry.yaml for
    # persistent overrides).
    app.state.rate_limit_overrides = {}

    # --- fix/catalog-visibility: catalog sensitivity-threshold override -----
    #
    # `rf serve --sensitivity-threshold <X>` mutates `config.viewer
    # ["sensitivity_threshold"]` in cli_commands.py's serve() BEFORE calling
    # create_app() (see that function's "Apply ALL CLI overrides to config
    # BEFORE the gate runs" comment) — so by the time we get here, `config`
    # already reflects the correct precedence: explicit CLI flag > whatever
    # foundry.yaml has on disk.
    #
    # Without this, that resolved value went nowhere: the catalog router only
    # receives a bare `FoundryPaths` via the `get_paths()` dependency, which
    # is a *fresh* `FoundryConfig.load()` — a different instance from `config`
    # that re-reads foundry.yaml from disk and has never seen the CLI-time
    # mutation. `catalog_service.resolve_threshold()` falls back to the same
    # kind of fresh disk read when no explicit override reaches it. Result: an
    # explicit `--sensitivity-threshold` flag was silently ignored by every
    # catalog endpoint (stats/search/item detail), which always resolved to
    # whatever foundry.yaml's `viewer.sensitivity_threshold` said instead
    # (`"public"` in the shipped config).
    #
    # Storing the resolved value on app.state — the same pattern already used
    # for rbac_enforced/workspace_isolation_enforced above — lets the catalog
    # router pass it through as `resolve_threshold()`'s explicit `override`
    # argument. When no CLI flag was passed, config.viewer.get(...) is
    # whatever foundry.yaml already had, so this is a no-op relative to prior
    # behavior — the fail-closed default (`"public"`) is unchanged.
    #
    # Resolution order (catalog_service.resolve_threshold): explicit `rf serve
    # --sensitivity-threshold` > foundry.yaml viewer.sensitivity_threshold >
    # hardcoded "public" default (the latter two remain resolve_threshold's
    # own responsibility when this override is None).
    app.state.catalog_sensitivity_threshold = config.viewer.get("sensitivity_threshold") or None

    # --- Middleware (outermost → innermost: CORS → allowlist → auth → rate-limit) ---
    #
    # Starlette/FastAPI middleware is processed in *reverse* insertion order at
    # runtime (last added = outermost).  We add them innermost-first so the
    # final execution order matches the documented stack.
    #
    # 0. Rate limit (innermost — added first, runs AFTER auth sets identity)
    #
    # P5.6: per-identity + per-route sliding-window rate limiter.  Keyed on
    # (user_id, route) so one user's burst cannot throttle another.  Auth must
    # run before rate-limit (auth is *outer* relative to rate-limit) so that
    # request.state.identity is populated when the rate limiter inspects it.
    # When auth_mode=none no identity exists and the middleware passes through.
    if config.auth_rate_limit_enabled():
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_window=config.auth_rate_limit_requests_per_window(),
            window_seconds=config.auth_rate_limit_window_seconds(),
        )

    # 1. Auth (added second — runs before rate-limit on each request)
    #
    # P5.1: registry-based provider replaces the legacy TokenAuthMiddleware
    # single-token wiring.  Provider selection happens exactly once here;
    # no router or service may branch on provider name — all branching is
    # resolved at app construction time.
    #
    # ACT-203 (public-multiuser Phase 2): every AuthProviderMiddleware
    # instance below is constructed with `paths=config.paths` so the
    # composite auth chain (access_tokens store checked first, provider
    # fallthrough on a miss) is active regardless of which provider is
    # configured — see AuthProviderMiddleware's class docstring.
    #
    # NOTE: auth.provider=none + non-loopback bind is blocked in the rf serve
    # pre-bind gate (cli_commands._validate_nonloopback_bind).  create_app does
    # not duplicate this gate — the server can only reach create_app() after the
    # CLI gate has passed.  The canonical check is config.is_auth_enabled().
    # Tests: tests/unit/test_rbac_enforcement_toggle.py::TestAuthNoneNonLoopbackCLIGate
    _provider_name = config.auth_provider()
    _auth_provider = get_provider(_provider_name)  # None when provider == "none"

    if _provider_name == "clerk":
        # P5.4 FU-1: Clerk lazy-import path — MUST FAIL CLOSED on any error.
        #
        # The clerk adapter is NOT imported at module level so that PyJWT is
        # only loaded when explicitly requested (keeps the base install lean).
        # This branch runs regardless of whether a sentinel is already in the
        # registry (handles both "first import" and "sentinel already present"
        # cases cleanly by always constructing a fresh, config-driven instance).
        #
        # auth_provider() already validated that clerk_frontend_api is non-empty
        # and clerk_outbound_internet_enabled=True before we reach here.  JWKS
        # fetch stays lazy (on-first-verify); only URL presence is checked here —
        # no network calls at startup.
        try:
            from .auth.adapters.clerk import (  # noqa: PLC0415
                ClerkAuthProvider as _ClerkAuthProvider,
            )
        except ImportError as _imp_exc:
            raise RuntimeError(
                "auth.provider=clerk requires optional dependencies 'PyJWT' and "
                "'cryptography'. Install them with: "
                "pip install 'research-foundry[clerk]'"
            ) from _imp_exc

        _azp_expected: str | None = config.auth.get("clerk_azp_expected") or None
        try:
            _auth_provider = _ClerkAuthProvider(
                frontend_api_url=config.auth_clerk_frontend_api(),
                azp_expected=_azp_expected,
            )
        except Exception as _init_exc:
            raise RuntimeError(
                f"Failed to construct ClerkAuthProvider: {_init_exc}. "
                "Verify auth.clerk_frontend_api is a valid HTTPS URL in foundry.yaml."
            ) from _init_exc

        register_provider(_auth_provider)
        app.add_middleware(AuthProviderMiddleware, provider=_auth_provider, paths=config.paths)

    elif _auth_provider is not None:
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
        app.add_middleware(AuthProviderMiddleware, provider=_auth_provider, paths=config.paths)

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
        app.add_middleware(AuthProviderMiddleware, provider=_auth_provider, paths=config.paths)

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

    # --- Startup probe (AUDIT-004) --------------------------------------------
    # Runs once at startup; logs WARNING when audit store is degraded, INFO
    # when healthy.  Never blocks startup — exceptions are caught and logged.
    @app.on_event("startup")
    def _audit_health_startup() -> None:
        try:
            from ..services import audit_service as _audit_svc
            result = _audit_svc.health_check(config.paths)
            if result.healthy:
                _logger.info(
                    "audit store healthy at startup: last_probe_at=%s",
                    result.last_probe_at,
                )
            else:
                _logger.warning(
                    "AUDIT STORE DEGRADED at startup: %s (last_success=%s)",
                    result.error_detail,
                    result.last_success_at,
                )
        except Exception as _exc:  # pragma: no cover — belt-and-suspenders
            _logger.warning("audit startup probe raised unexpectedly: %s", _exc)

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
    # Reusable assertion ledger (P4): private, workspace-scoped lexical
    # discovery and complete evidence packets.  No vector/graph routes exist.
    app.include_router(assertions_router, prefix="/api", tags=["assertions"])
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
    # Audit log read API (public-multiuser-release Phase 5 — AUDIT-003).
    # Unconditional — audit endpoints are always registered.
    # TODO(P5.9): restrict to admin role once P5.2 RBAC middleware ships.
    app.include_router(audit_router, prefix="/api", tags=["audit"])
    # Auth identity endpoint (P5.4 FU-2): GET /api/auth/identity.
    # Always registered — returns null/anonymous in provider=none mode and the
    # caller's own AuthIdentity in authenticated mode.  No admin RBAC gate needed
    # because the endpoint only exposes the caller's own resolved identity.
    app.include_router(auth_identity_router, prefix="/api", tags=["auth"])
    # Admin settings API (P5.6 T2): workspace members, rate-limit config,
    # auth-provider status, and RBAC enforcement toggle status.
    # Always registered — individual endpoints gate on require_role("owner", "admin").
    app.include_router(admin_router, prefix="/api", tags=["admin"])
    # Writeback Approve & Dispatch API (runs-writeback-approve-dispatch Phase 2).
    # Unconditional — unlike agent_jobs_router, this route is NOT behind the
    # agents.enabled feature flag, since rf writeback is not an agent-job
    # surface. Gated per-route by require_role("owner", "admin") instead.
    app.include_router(writeback_router, prefix="/api", tags=["writeback"])

    return app


__all__ = ["create_app"]
