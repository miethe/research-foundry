"""In-repo isolating launcher for the Search Router MCP server (DI-1 F2).

The DI-1 delta re-audit (``docs/project_plans/reports/audits/
di-1-delta-reaudit-2026-07-26.md``, finding F2, CONFIRMED HIGH) found that
``mcp_server.py`` trusted a caller-supplied JSON ``identity`` payload and a
self-declared ``sensitivity_threshold`` with zero validation, forwarding both
verbatim into the real workspace-partitioned ``AssertionCatalog`` -- a
cross-workspace enumeration oracle. The audit also found the module's own
docstring assumed an isolating wrapper lived out-of-repo; it did not.

This module IS that wrapper. It is the single blessed way to launch the
Search Router MCP server (the packaged ``rf-mcp`` entry point and
``mcp_server.main()`` -- kept for ``.mcp.json`` back-compat -- both delegate
here), and it is the one choke point every tool call's identity and
sensitivity_threshold now routes through:

* :func:`resolve_launch_principal` / :func:`get_launch_principal` -- resolve
  the server-authoritative principal ONCE per stdio subprocess, from env
  vars, then ``foundry.mcp.principal`` config, then ``None``
  (single-operator-trust, matching every existing CLI call site's own
  identity-less default -- see ``search_router/cli.py:58``,
  ``agent_job_service.py:661``).
* :func:`reconcile_client_identity` -- the effective identity for one tool
  call. The launch principal's ``workspace_id``/``roles`` are ALWAYS
  authoritative; a client-declared ``identity`` payload can supply a
  display/audit ``user_id`` hint and nothing else. A client that declares a
  ``workspace_id`` different from the launch principal's is rejected, not
  silently reconciled.
* :func:`resolve_sensitivity_ceiling` / :func:`clamp_sensitivity_threshold`
  -- a server-configured ceiling a client's self-declared
  ``sensitivity_threshold`` can never exceed. Ranked via
  :data:`research_foundry.services.sensitivity.SENSITIVITY_RANK` -- the
  vocabulary ``router.run_search``'s ``sensitivity_threshold`` kwarg is
  actually compared against downstream, in ``catalog_retrieval.py`` (NOT
  ``export_service.SENSITIVITY_ORDER``, a different pipeline's vocabulary
  for the export/redaction seam).
* :class:`_StdioOnlyFastMCP` / :func:`guard_stdio_only` -- ``build_server()``
  (in ``mcp_server.py``) constructs a :class:`_StdioOnlyFastMCP` -- a
  ``FastMCP`` SUBCLASS, not a wrapper or proxy -- so only the ``stdio``
  transport can ever be reached from this process. This is the FOURTH
  generation of this guard, and the first that is not a delegating proxy of
  any kind (see the module-level comment above :class:`_StdioOnlyFastMCP`
  for why every delegating-proxy generation was, and any future one would
  be, bypassable in principle via bound-method ``__self__``). Because the
  returned object IS the server -- there is no separate wrapped instance
  anywhere -- every access path (the instance itself, ``type(server)``,
  ``server.__class__``, and any bound method's ``__self__``) resolves to
  this subclass's own overrides, which raise for the four network-transport
  surfaces (``sse_app``, ``streamable_http_app``, ``run_sse_async``,
  ``run_streamable_http_async``) and for ``run()`` with a non-stdio
  transport. Every other attribute (``tool``, ``call_tool``, ``list_tools``,
  ``add_tool``, etc.) is the real, inherited ``FastMCP`` implementation --
  there is nothing to delegate, because there is only one object.

Offline-safe-import contract (mirrors ``mcp_server.py``): this module never
imports the optional ``mcp`` SDK, and never imports
``research_foundry.api.auth.provider`` (which pulls in ``starlette``) at
module level -- both are lazy, inside the functions that actually need
:class:`AuthIdentity`.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from research_foundry.config import FoundryConfig
from research_foundry.errors import GovernanceError
from research_foundry.paths import FoundryPaths
from research_foundry.services.sensitivity import SENSITIVITY_RANK

if TYPE_CHECKING:
    from research_foundry.api.auth.provider import AuthIdentity

__all__ = [
    "LaunchPrincipalError",
    "CrossWorkspaceIdentityError",
    "UnsupportedTransportError",
    "resolve_launch_principal",
    "get_launch_principal",
    "reset_launch_principal_cache",
    "reconcile_client_identity",
    "resolve_sensitivity_ceiling",
    "get_sensitivity_ceiling",
    "reset_sensitivity_ceiling_cache",
    "clamp_sensitivity_threshold",
    "stdio_only_fastmcp_class",
    "guard_stdio_only",
    "main",
]

logger = logging.getLogger(__name__)

_ENV_USER_ID = "RF_MCP_PRINCIPAL_USER_ID"
_ENV_WORKSPACE_ID = "RF_MCP_PRINCIPAL_WORKSPACE_ID"
_ENV_ROLES = "RF_MCP_PRINCIPAL_ROLES"

_ALLOWED_TRANSPORTS: tuple[str | None, ...] = (None, "stdio")

# Sentinel distinct from `None` (a valid resolved value -- single-operator-
# trust) so the cache can tell "not yet resolved" apart from "resolved to
# None".
_UNSET: Any = object()
_cached_principal: Any = _UNSET
_cached_ceiling: Any = _UNSET


class LaunchPrincipalError(GovernanceError):
    """Raised when the MCP launch principal configuration is present but
    incomplete (e.g. only one of ``user_id``/``workspace_id`` supplied)."""


class CrossWorkspaceIdentityError(GovernanceError):
    """Raised when a client-declared ``identity.workspace_id`` conflicts with
    the server's pinned launch principal. Cross-workspace attempts on this
    transport are rejected, not silently reconciled."""


class UnsupportedTransportError(GovernanceError):
    """Raised when a caller attempts to run the MCP server on a transport
    other than ``stdio`` (F2 Change 4 -- enforced at the code level)."""


# ---------------------------------------------------------------------------
# Launch principal resolution
# ---------------------------------------------------------------------------


def _split_roles(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _principal_from_fields(
    user_id: str | None,
    workspace_id: str | None,
    roles: tuple[str, ...],
    *,
    source: str,
) -> AuthIdentity | None:
    """Build an :class:`AuthIdentity` from resolved fields, or raise if only
    one of ``user_id``/``workspace_id`` is present -- a half-declared
    principal is a configuration error, never a silent default."""

    has_user = bool(user_id)
    has_workspace = bool(workspace_id)
    if not has_user and not has_workspace:
        return None
    if not (has_user and has_workspace):
        raise LaunchPrincipalError(
            f"Incomplete MCP launch principal from {source}: user_id and workspace_id "
            f"must be supplied together (got user_id={user_id!r}, workspace_id={workspace_id!r}). "
            f"Set both {_ENV_USER_ID} and {_ENV_WORKSPACE_ID} (or both fields under "
            "foundry.mcp.principal), or neither for single-operator-trust mode."
        )

    from research_foundry.api.auth.provider import AuthIdentity

    return AuthIdentity(user_id=str(user_id), workspace_id=str(workspace_id), roles=tuple(roles))


def resolve_launch_principal(paths: FoundryPaths | None = None) -> AuthIdentity | None:
    """Resolve the server-authoritative MCP launch principal.

    Resolution order (first match wins):

    1. Env vars ``RF_MCP_PRINCIPAL_USER_ID`` / ``RF_MCP_PRINCIPAL_WORKSPACE_ID``
       / ``RF_MCP_PRINCIPAL_ROLES`` (comma-separated). Either of the first two
       present without the other raises :class:`LaunchPrincipalError`.
    2. The ``foundry.mcp.principal`` config block (``user_id`` / ``workspace_id``
       / ``roles`` keys), read directly off ``FoundryConfig.foundry`` -- no new
       ``config.py`` accessor is added by this module (out of scope for this
       change; ``foundry`` is already a public property).
    3. Neither present -> ``None`` = single-operator-trust, matching the
       CLI's own default (every existing ``run_search`` call site invokes it
       with no ``identity`` kwarg at all).

    Pure function -- does not cache. :func:`get_launch_principal` is the
    cached, once-per-process wrapper the MCP tools actually call.
    """

    env_user = os.environ.get(_ENV_USER_ID)
    env_workspace = os.environ.get(_ENV_WORKSPACE_ID)
    env_roles_raw = os.environ.get(_ENV_ROLES)
    if env_user is not None or env_workspace is not None:
        roles = _split_roles(env_roles_raw) if env_roles_raw else ()
        return _principal_from_fields(env_user, env_workspace, roles, source="environment")

    resolved_paths = paths if paths is not None else FoundryPaths.discover()
    config = FoundryConfig(paths=resolved_paths)
    foundry_block = config.foundry
    mcp_block = foundry_block.get("mcp") if isinstance(foundry_block, dict) else None
    principal_block = mcp_block.get("principal") if isinstance(mcp_block, dict) else None
    if isinstance(principal_block, dict) and principal_block:
        cfg_user = principal_block.get("user_id")
        cfg_workspace = principal_block.get("workspace_id")
        cfg_roles_raw = principal_block.get("roles") or ()
        cfg_roles = (
            _split_roles(cfg_roles_raw)
            if isinstance(cfg_roles_raw, str)
            else tuple(str(r) for r in cfg_roles_raw)
        )
        return _principal_from_fields(
            cfg_user, cfg_workspace, cfg_roles, source="foundry.mcp.principal config"
        )

    return None


def get_launch_principal(
    paths: FoundryPaths | None = None, *, refresh: bool = False
) -> AuthIdentity | None:
    """Cached wrapper over :func:`resolve_launch_principal`.

    The launch principal is fixed for the lifetime of the stdio subprocess,
    so it is resolved once (on first call, or eagerly by :func:`main`) and
    reused by every subsequent tool invocation. ``refresh=True`` forces
    re-resolution (used by tests).
    """

    global _cached_principal
    if refresh or _cached_principal is _UNSET:
        _cached_principal = resolve_launch_principal(paths)
    return _cached_principal  # type: ignore[return-value]


def reset_launch_principal_cache() -> None:
    """Clear the cached launch principal. Test-only escape hatch."""

    global _cached_principal
    _cached_principal = _UNSET


# ---------------------------------------------------------------------------
# Per-call identity reconciliation (F2 Change 2)
# ---------------------------------------------------------------------------


def reconcile_client_identity(
    launch_principal: AuthIdentity | None,
    client_identity: dict[str, Any] | None,
) -> AuthIdentity | None:
    """Derive the effective identity for one MCP tool call.

    This is the F2 remediation choke point: a client-supplied ``identity``
    JSON payload's ``workspace_id``/``roles`` are never trusted. The launch
    principal is authoritative for both.

    * ``launch_principal`` is ``None`` (single-operator-trust): the effective
      identity is always ``None``, regardless of what the client declared. A
      non-empty ``client_identity`` in this mode is logged at WARNING (it is
      ignored, not honored) so a misconfigured client is visible in the
      server's logs rather than silently no-op'd.
    * ``client_identity`` absent/empty: the launch principal passes through
      unchanged.
    * ``client_identity["workspace_id"]`` present and different from
      ``launch_principal.workspace_id``: raises
      :class:`CrossWorkspaceIdentityError` -- rejected, not reconciled. The
      caller (a tool function) lets this propagate; ``router.run_search`` is
      never invoked for a mismatched call.
    * ``client_identity["user_id"]`` present: passed through as a
      display/audit hint on the returned identity. It never changes
      ``workspace_id``/``roles``, which always come from the launch
      principal.
    """

    if launch_principal is None:
        if client_identity:
            logger.warning(
                "MCP tool call carried a client-supplied identity payload (%r) but no launch "
                "principal is configured for this server process (single-operator-trust mode) "
                "-- ignoring it. Resolved identity is None, matching CLI-caller parity.",
                {k: client_identity.get(k) for k in ("user_id", "workspace_id")},
            )
        return None

    if not client_identity:
        return launch_principal

    client_workspace = str(client_identity.get("workspace_id") or "")
    if client_workspace and client_workspace != launch_principal.workspace_id:
        raise CrossWorkspaceIdentityError(
            f"MCP client declared identity.workspace_id={client_workspace!r}, which does not "
            f"match this server's launch principal workspace ({launch_principal.workspace_id!r}). "
            "Cross-workspace identity declarations are rejected on this transport, not "
            "reconciled -- launch a separate MCP subprocess (with its own launch principal) "
            "for that workspace."
        )

    client_user_hint = client_identity.get("user_id")
    effective_user_id = str(client_user_hint) if client_user_hint else launch_principal.user_id
    if effective_user_id == launch_principal.user_id:
        return launch_principal

    from research_foundry.api.auth.provider import AuthIdentity

    return AuthIdentity(
        user_id=effective_user_id,
        workspace_id=launch_principal.workspace_id,
        roles=launch_principal.roles,
    )


# ---------------------------------------------------------------------------
# Sensitivity ceiling (F2 Change 3)
# ---------------------------------------------------------------------------


def resolve_sensitivity_ceiling(paths: FoundryPaths | None = None) -> str | None:
    """Server-side ``sensitivity_threshold`` ceiling for MCP tool calls.

    Resolution order:

    1. ``foundry.mcp.sensitivity_threshold_max`` -- a dedicated MCP config
       knob, checked first so an operator can set a ceiling specific to this
       transport without touching the viewer/export config.
    2. ``viewer.sensitivity_threshold`` -- an existing config key documented
       for the export/redaction pipeline's ``SENSITIVITY_ORDER`` vocabulary,
       but its four label strings (``public``/``personal``/``work_sensitive``/
       ``client_sensitive``) are identical to, and rank consistently within,
       :data:`research_foundry.services.sensitivity.SENSITIVITY_RANK`, the
       vocabulary this ceiling is actually enforced against (see
       :func:`clamp_sensitivity_threshold`). Reused here rather than adding a
       second config knob most deployments would never set.
    3. Neither set -> ``None`` -- no ceiling configured; a client's stated
       threshold passes through unclamped, preserving pre-fix behavior for
       deployments that have not opted in to a ceiling.
    """

    resolved_paths = paths if paths is not None else FoundryPaths.discover()
    config = FoundryConfig(paths=resolved_paths)
    foundry_block = config.foundry
    mcp_block = foundry_block.get("mcp") if isinstance(foundry_block, dict) else None
    if isinstance(mcp_block, dict):
        ceiling = mcp_block.get("sensitivity_threshold_max")
        if ceiling:
            return str(ceiling)

    viewer_block = config.viewer
    viewer_threshold = viewer_block.get("sensitivity_threshold") if isinstance(viewer_block, dict) else None
    return str(viewer_threshold) if viewer_threshold else None


def get_sensitivity_ceiling(paths: FoundryPaths | None = None, *, refresh: bool = False) -> str | None:
    """Cached wrapper over :func:`resolve_sensitivity_ceiling` (once per
    process, like :func:`get_launch_principal`). ``refresh=True`` forces
    re-resolution (used by tests)."""

    global _cached_ceiling
    if refresh or _cached_ceiling is _UNSET:
        _cached_ceiling = resolve_sensitivity_ceiling(paths)
    return _cached_ceiling  # type: ignore[return-value]


def reset_sensitivity_ceiling_cache() -> None:
    """Clear the cached sensitivity ceiling. Test-only escape hatch."""

    global _cached_ceiling
    _cached_ceiling = _UNSET


def clamp_sensitivity_threshold(
    client_threshold: str | None, ceiling: str | None
) -> tuple[str | None, bool]:
    """Clamp ``client_threshold`` to the server-side ``ceiling``.

    Ranks both against :data:`SENSITIVITY_RANK` -- the vocabulary
    ``router.run_search``'s ``sensitivity_threshold`` kwarg is actually
    compared against downstream, in ``catalog_retrieval.py`` (not
    ``export_service.SENSITIVITY_ORDER``, a different pipeline's vocabulary).

    * ``ceiling is None`` (no ceiling configured) -- pass through unchanged.
    * ``client_threshold is None`` -- an omitted threshold is already
      fail-closed by the catalog seam (``catalog_retrieval.RetrievalConstraints``);
      the ceiling only ever lowers a *stated* threshold, it never raises a
      floor for an omitted one. Passes through unchanged.
    * Otherwise, an unrecognized label ranks as maximally sensitive (fail
      closed, via ``SENSITIVITY_RANK.get(..., len(SENSITIVITY_RANK))``), so an
      unknown value is clamped down to the ceiling exactly like a
      too-permissive known one.

    Returns ``(effective_threshold, was_clamped)``; never raises -- a
    well-behaved client that asks above the ceiling is clamped, not broken.
    """

    if ceiling is None or client_threshold is None:
        return client_threshold, False

    unknown_rank = len(SENSITIVITY_RANK)
    ceiling_rank = SENSITIVITY_RANK.get(ceiling, unknown_rank)
    client_rank = SENSITIVITY_RANK.get(client_threshold, unknown_rank)
    if client_rank > ceiling_rank:
        return ceiling, True
    return client_threshold, False


# ---------------------------------------------------------------------------
# Transport guard (F2 Change 4). FOUR generations now:
#   Gen 1 "F2" (original)  -- mutated ``server.run`` in place, returned
#                             ``server`` itself. Left ``sse_app()`` etc.
#                             directly reachable.
#   Gen 2 "F2-SSE"          -- a method-denylist ``__getattr__`` proxy. Left
#                             the wrapped server reachable via its own
#                             instance attribute (``self._wrapped``).
#   Gen 3 "F2-wrapped"      -- moved the wrapped server into a module-level
#                             ``WeakKeyDictionary`` keyed by the proxy, and
#                             overrode ``__getattribute__`` (not
#                             ``__getattr__``) so no attribute NAME reached
#                             it. Still bypassed (Codex gpt-5.6-sol,
#                             2026-07-27): every "safe" delegated method --
#                             ``list_tools``, ``call_tool``, ``add_tool``,
#                             ``tool`` -- is `getattr(wrapped, name)`, which
#                             Python's descriptor protocol returns already
#                             BOUND to `wrapped`. That bound method's
#                             ``__self__`` attribute is the real, unguarded
#                             ``FastMCP`` instance --
#                             ``server.list_tools.__self__.sse_app()`` reaches
#                             it directly. No denylist over attribute NAMES on
#                             the proxy can ever close this: the leak is not
#                             an attribute of the proxy at all, it is an
#                             attribute of every bound method the proxy hands
#                             back, which exists by construction the moment
#                             ANY method is delegated to a distinct wrapped
#                             object.
#   Gen 4 "F2-subclass" (this generation) -- closes the entire bug CLASS
#                             rather than the next attribute name, by
#                             eliminating the second object. ``build_server()``
#                             constructs a ``FastMCP`` SUBCLASS
#                             (:data:`stdio_only_fastmcp_class`) directly, so
#                             there is no wrapped/delegate instance anywhere:
#                             the object IS the server. Every access path --
#                             the instance itself, ``type(server)``,
#                             ``server.__class__``, and every bound method's
#                             ``__self__`` (since ``self`` on every inherited
#                             method IS the guarded instance) -- resolves to
#                             this class's own overrides. There is no
#                             delegation step left for a bound method to leak
#                             through, because there is nothing to delegate
#                             to.
# ---------------------------------------------------------------------------

# Every FastMCP method that hands a caller a network-transport ASGI app or a
# coroutine that starts one, bypassing the stdio-only invariant if reached
# directly instead of through ``.run()``. Enumerated against the installed
# SDK's actual public surface (``dir(FastMCP)``), not guessed:
# ``sse_app``/``streamable_http_app`` build and return a Starlette ASGI app
# a caller can mount under uvicorn/gunicorn with this process's launch
# principal; ``run_sse_async``/``run_streamable_http_async`` start that same
# listener directly. ``session_manager`` (a property, not a method) is
# deliberately NOT listed here: the SDK only ever populates it as a
# side effect of a prior ``streamable_http_app()`` call -- absent that, it
# raises ``RuntimeError`` on its own -- so blocking ``streamable_http_app``
# already makes ``session_manager`` permanently inert on a guarded server.
_BLOCKED_TRANSPORT_METHODS: frozenset[str] = frozenset(
    {
        "sse_app",
        "streamable_http_app",
        "run_sse_async",
        "run_streamable_http_async",
    }
)


def _blocked_transport_message(name: str) -> str:
    return (
        f"{name}() is not supported by this server. stdio is the only "
        "enforced transport (DI-1 F2 remediation, generation 4 -- see "
        "mcp_launcher.stdio_only_fastmcp_class / mcp_launcher._StdioOnlyFastMCP). "
        "This is a FastMCP SUBCLASS, not a delegating proxy: the object you "
        "are holding IS the guarded server, so there is no distinct wrapped "
        "instance for any bound method's __self__, dunder, or class "
        "reference to ever resolve to. Network-transport surfaces are "
        "refused at the code level, not only by convention."
    )


# Cache for :func:`stdio_only_fastmcp_class`, following this module's existing
# sentinel pattern (see ``_cached_principal``/``_cached_ceiling`` above).
# Keyed implicitly by ``_cached_stdio_only_base`` -- the real ``FastMCP``
# class the cached subclass was derived from -- so a test double passed as
# ``fastmcp_cls`` (a different class than a previous call) still gets its own
# correctly-derived subclass rather than a stale one.
_cached_stdio_only_class: Any = _UNSET
_cached_stdio_only_base: Any = _UNSET


def stdio_only_fastmcp_class(fastmcp_cls: type[Any]) -> type[Any]:
    """Return the ``_StdioOnlyFastMCP`` subclass of ``fastmcp_cls`` (cached).

    ``fastmcp_cls`` is the real ``mcp.server.fastmcp.FastMCP`` class, passed
    in by the caller (:func:`research_foundry.services.search_router.
    mcp_server.build_server`) rather than imported here: this module's
    offline-safe-import contract (module docstring) means ``mcp_launcher.py``
    never imports the optional ``mcp`` SDK, not even lazily inside a
    function -- ``build_server()`` has already performed (and error-handled)
    that import by the time this is called, so this function only ever
    receives an already-resolved class object.

    The returned class is a genuine subclass of ``fastmcp_cls`` -- NOT a
    wrapper, NOT a proxy. See the block comment above this function for why
    that distinction is what makes this generation of the guard closed
    against the bound-method ``__self__`` bypass every previous
    delegating-proxy generation was vulnerable to.

    Overrides:

    * ``sse_app`` / ``streamable_http_app`` / ``run_sse_async`` /
      ``run_streamable_http_async`` -- always raise
      :class:`UnsupportedTransportError`. Signatures match the real
      ``FastMCP`` methods exactly (verified against the installed SDK via
      ``inspect.signature`` -- ``sse_app(self, mount_path=None)``,
      ``streamable_http_app(self)``, and the two async ``run_*_async``
      methods take no arguments beyond ``self``/``mount_path``), so these
      overrides are drop-in regardless of caller.
    * ``run`` -- allows ``None``/``"stdio"`` (the enforced invariant from
      generations 1-3, unchanged); any other transport raises the same
      :class:`UnsupportedTransportError`, then delegates to
      ``super().run(...)`` -- the REAL ``FastMCP.run`` on this same object,
      not a second instance.

    Cached (not redefined on every call) so ``type(build_server())`` is
    stable across repeated calls in the same process -- e.g.
    ``type(server_a) is type(server_b)`` holds for two servers built in the
    same test session.
    """

    global _cached_stdio_only_class, _cached_stdio_only_base
    if _cached_stdio_only_class is not _UNSET and _cached_stdio_only_base is fastmcp_cls:
        return _cached_stdio_only_class  # type: ignore[return-value]

    class _StdioOnlyFastMCP(fastmcp_cls):  # type: ignore[misc]
        """``FastMCP`` restricted to the ``stdio`` transport (DI-1 F2, gen 4).

        A SUBCLASS, not a wrapper or proxy -- see the block comment above
        :func:`stdio_only_fastmcp_class` and the module docstring for why
        that is the property that closes the bound-method ``__self__``
        bypass (Codex gpt-5.6-sol, 2026-07-27) that defeated every prior
        delegating-proxy generation of this guard. Because every override
        below lives directly on this class, and ``build_server()``
        constructs THIS class (not the plain ``FastMCP``), there is no
        second object anywhere:

        * ``isinstance(server, FastMCP)`` is ``True`` (it is still a real
          ``FastMCP`` -- every non-overridden method, e.g. ``tool``,
          ``call_tool``, ``list_tools``, ``add_tool``, is the genuine
          inherited ``FastMCP`` implementation, not a stub).
        * ``type(server) is _StdioOnlyFastMCP`` -- not ``FastMCP``.
        * ``server.list_tools.__self__ is server`` -- the bound method's
          ``__self__`` is this same guarded instance, so
          ``server.list_tools.__self__.sse_app()`` resolves to THIS class's
          ``sse_app`` override (raises), not a real, unguarded method on a
          distinct object. This is the regression test for the exact
          Gen 3 bypass.
        * ``type(server).sse_app(server)`` and
          ``server.__class__.sse_app(server)`` both resolve to this same
          override for the same reason -- there is only one class in the
          picture, and it is this one.
        """

        def sse_app(self, mount_path: str | None = None) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("sse_app"))

        def streamable_http_app(self) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("streamable_http_app"))

        # Deliberately NOT `async def`, even though the real `FastMCP.
        # run_sse_async`/`run_streamable_http_async` are coroutine functions.
        # An `async def` override's body never executes until the returned
        # coroutine is driven (awaited/scheduled) -- calling it bare, as
        # `server.run_sse_async()`, would silently hand back an inert,
        # never-raising coroutine object instead of blocking the attempt.
        # A plain function raises the instant it is CALLED, which is
        # strictly earlier/stronger than raising-on-await: a real caller
        # doing `await server.run_sse_async()` still observes the identical
        # `UnsupportedTransportError`, because Python evaluates the call
        # `server.run_sse_async()` before ever reaching the `await` --  the
        # raise happens first, and there is no coroutine left to await.
        def run_sse_async(self, mount_path: str | None = None) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_sse_async"))

        def run_streamable_http_async(self) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_streamable_http_async"))

        def run(self, transport: str | None = "stdio", mount_path: str | None = None) -> None:
            """Run this server, allowing only the ``stdio`` transport.

            A direct ``.run(transport="sse")`` or ``.run(transport=
            "streamable-http")`` raises :class:`UnsupportedTransportError`
            instead of starting a network listener that would expose the
            launch-principal-scoped tools without a per-request auth
            boundary -- stdio-only is an enforced invariant, not a
            convention. Otherwise delegates to ``super().run(...)`` -- the
            real ``FastMCP.run`` on this same object.
            """

            if transport not in _ALLOWED_TRANSPORTS:
                raise UnsupportedTransportError(
                    f"Non-stdio MCP transport {transport!r} is not supported by this server. "
                    "stdio is the only enforced transport (DI-1 F2 remediation; see "
                    "mcp_launcher.stdio_only_fastmcp_class). Direct network-transport mounts "
                    "(sse/streamable-http) are refused at the code level, not only by convention."
                )
            super().run(transport=transport or "stdio", mount_path=mount_path)  # type: ignore[misc]

    _cached_stdio_only_class = _StdioOnlyFastMCP
    _cached_stdio_only_base = fastmcp_cls
    return _StdioOnlyFastMCP


def guard_stdio_only(server: Any) -> Any:
    """Ensure ``server`` is guarded to the ``stdio`` transport (DI-1 F2).

    Backward-compatible shim for the pre-subclass (generations 1-3) call
    shape. The blessed path is now :func:`stdio_only_fastmcp_class`:
    ``build_server()`` constructs a guarded subclass directly, so by the
    time a server would reach this function it is typically ALREADY an
    instance of that subclass, and this call is then a no-op returning it
    unchanged (checked via ``isinstance``, not identity, so a subclass of
    the guarded class -- if one is ever introduced -- still short-circuits
    correctly).

    If ``server`` is somehow still a plain, unguarded ``FastMCP`` instance
    -- e.g. a caller that predates this change and still does
    ``FastMCP(...)`` directly, then passes the result here -- ``server.
    __class__`` is reassigned to :func:`stdio_only_fastmcp_class`'s subclass
    of ``type(server)`` in place. This is safe ONLY because that subclass
    adds no ``__slots__`` and no new instance attributes of its own (every
    override is a method, not a stored attribute) -- it is layout-compatible
    with whatever ``server`` already is, so reassigning ``__class__``
    changes nothing about the object's ``__dict__``, only which methods
    resolve on it. No new object is created; ``server`` is returned, mutated
    in place.
    """

    if _cached_stdio_only_class is not _UNSET and isinstance(server, _cached_stdio_only_class):
        return server

    guarded_cls = stdio_only_fastmcp_class(type(server))
    server.__class__ = guarded_cls
    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """The one blessed way to launch the Search Router MCP server.

    Resolves the launch principal (env vars -> ``foundry.mcp.principal``
    config -> ``None``/single-operator-trust), logs the resolved principal
    (or a warning if none was declared), builds the server, and runs it over
    stdio -- the only transport the guarded ``_StdioOnlyFastMCP`` subclass
    (``mcp_server.build_server()`` constructs it via
    :func:`stdio_only_fastmcp_class`) allows this process to start.

    Wired to the packaged ``rf-mcp`` entry point (``pyproject.toml``). Also
    invoked, for ``.mcp.json`` back-compat, via ``mcp_server.main()``, which
    delegates here.
    """

    principal = get_launch_principal()
    if principal is not None:
        logger.info(
            "MCP launch principal resolved: user_id=%r workspace_id=%r roles=%r",
            principal.user_id,
            principal.workspace_id,
            principal.roles,
        )
    else:
        logger.warning(
            "MCP server launched without an explicit principal (no %s/%s env vars and no "
            "foundry.mcp.principal config) -- running in single-operator-trust mode "
            "(identity=None on every tool call, matching CLI-caller parity). Any "
            "client-supplied 'identity' payload will be ignored.",
            _ENV_USER_ID,
            _ENV_WORKSPACE_ID,
        )

    from .mcp_server import build_server

    server = build_server()
    server.run()


if __name__ == "__main__":  # pragma: no cover - thin entrypoint
    main()
