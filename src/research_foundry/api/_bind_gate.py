"""Shared non-loopback bind safety gate (DI-1 delta re-audit remediation, F1(2)).

``create_app`` is directly ASGI-mountable — uvicorn, gunicorn, or any other
runner may import and construct it without ever going through the ``rf serve``
CLI, so the CLI's own pre-bind gate
(:func:`research_foundry.cli_commands._validate_nonloopback_bind`) is not a
complete guarantee: it only runs for callers that invoke ``rf serve``.

The DI-1 delta re-audit (``docs/project_plans/reports/audits/
di-1-delta-reaudit-2026-07-26.md``, finding F1) confirmed a direct
``create_app`` mount with ``auth.provider=none`` on a non-loopback bind
produces a fully-open server: ``require_workspace_scope`` short-circuits to
allow on ``identity=None`` (no auth middleware installed → no identity is
ever attached to a request). This module provides the minimal invariant that
MUST hold regardless of caller — deliberately narrower than the CLI gate
(which additionally verifies a *resolvable* token value exists in the
environment): a non-loopback bind with **no auth mechanism declared at all**
is refused before :func:`research_foundry.api.app.create_app` finishes
constructing the application.

This is a plain function (not imported from ``cli_commands``) so
``research_foundry.api.app`` never has to import CLI code — see the F1(2)
remediation note in ``create_app`` for the call site.
"""

from __future__ import annotations

from ..config import FoundryConfig, _is_loopback


def assert_bind_is_safe(config: FoundryConfig) -> None:
    """Raise if *config* resolves to a non-loopback bind with no auth configured.

    Checks ``config.viewer_bind_host()`` against the loopback set
    (:func:`research_foundry.config._is_loopback`) and, only when the bind is
    non-loopback, requires :meth:`FoundryConfig.is_auth_enabled` to be
    ``True`` (covers both the canonical ``auth.provider`` path and the legacy
    ``viewer.auth_mode=token`` path — see that method's docstring).

    This gate fires for **every** caller of ``create_app`` — the ``rf serve``
    CLI (redundantly with its own pre-bind gate, which additionally validates
    that a token value actually resolves) and any direct ASGI mount that
    bypasses the CLI entirely (the exposure this fix closes).

    Raises:
        ValueError: When the resolved bind host is non-loopback and no auth
            mechanism is configured. The message intentionally contains the
            substring ``"non-loopback"`` to stay consistent with the other
            fail-closed startup gates in :mod:`research_foundry.config`
            (``resolve_rbac_enforced``, ``resolve_workspace_isolation_enforced``).
    """
    bind_host = config.viewer_bind_host()
    if _is_loopback(bind_host):
        return
    if config.is_auth_enabled():
        return
    raise ValueError(
        f"refusing to construct app: viewer.bind_host={bind_host!r} is a "
        "non-loopback address with no auth configured (auth.provider=none "
        "and viewer.auth_mode!=token). Configure auth.provider=local_static "
        "or auth.provider=clerk in foundry.yaml, or bind to a loopback "
        "address (127.0.0.1) instead. This gate protects direct ASGI mounts "
        "of create_app() that would otherwise bypass the `rf serve` CLI's "
        "pre-bind check (DI-1 delta re-audit remediation, finding F1(2))."
    )
