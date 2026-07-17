"""Shared workspace-resolution + fail-closed gate for assertion-ledger writes.

Every write call site added to the assertion ledger from Phase 2 onward
(``assertion_rollout.py``'s backfill, ``source_cards.py::ingest_source``'s
forward driver, and any future ``run_launch.py`` wiring) MUST call
:func:`resolve_or_deny` before invoking
:meth:`~research_foundry.services.assertion_registry.AssertionRegistry.ingest`
or
:meth:`~research_foundry.services.assertion_materialization.AssertionMaterializer.materialize_run`.
No call site may bypass this gate by constructing those two classes directly
from an unchecked ``assertion_registry_workspace_id``.

This module adds **no new resolution mechanism** — it confirms and adapts the
project's existing single-operator-trust idiom (WKSP-304's ``identity=None``
short-circuit, ``api/auth/scope.py::require_workspace_scope``) to the write
path's own parameter shape.

P1-01 finding — default-workspace resolution rule (closes OQ-3 / DF-002)
--------------------------------------------------------------------------
``assertion_registry_workspace_id`` is a plain ``str | None`` parameter
already threaded through ``source_cards.py::ingest_source`` (see
``docs/project_plans/aars/2026-07-15-catalog-visibility-regressions.md``);
today no caller supplies it, so the ledger never populates. Unlike
``request.state.identity``, there is no per-request object for this module to
inspect — the value is always supplied directly by the call site.

Two independent lines of evidence in this codebase establish what a
single-operator deployment's call site MUST supply as that value:

1. ``api/auth/scope.py::require_workspace_scope`` treats ``identity is None``
   (single-operator-trust — no auth middleware configured) as "no workspace
   context to compare", and returns before any workspace_id lookup. It never
   invents a workspace_id; identity-bearing multi-tenant callers carry their
   own via ``identity.workspace_id``.
2. Where a fixed sentinel is needed for the single-operator / pre-multi-tenant
   baseline, this codebase uses the literal string ``"default"`` — see
   ``services/workspace_migration_service.py`` (``target_workspace_id: str =
   "default"`` on every backfill/dry-run/rollback dataclass, per WKSP-301/302)
   and ``api/auth/adapters/clerk.py`` (``payload.get("org_id") or "default"``).
   ``AuthIdentity.workspace_id``'s own docstring names this same convention:
   "Single-tenant deployments may use a fixed sentinel (e.g. ``"default"``)".

**Resolution rule**: a single-operator Research Foundry deployment resolves
``assertion_registry_workspace_id`` to the literal string ``"default"``. That
resolution happens at the entry point (the future CLI/HTTP call site — P3's
scope, mirroring how routers extract ``identity`` before any scope check
runs), not inside this module. :func:`resolve_or_deny` does not perform
identity-to-workspace resolution itself; it only enforces the fail-closed
contract on whatever value the call site already produced. This keeps the
gate usable by every call site shape (CLI, HTTP, backfill script) without
coupling it to :class:`~research_foundry.api.auth.provider.AuthIdentity`.

This finding is also recorded in
``docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1/phase-1-foundation.md``
under "Findings (P1-01 resolution slot)".

Fail-closed contract (P1-02)
-----------------------------
:func:`resolve_or_deny` returns a :class:`WorkspaceWriteResolution` — never
raises, never silently no-ops. Mirrors the shape of
``api/auth/scope.py::WorkspaceScopeResult`` (``allowed`` + a machine-readable
``reason``) and the WKSP-304 404-not-403 principle: a denial carries exactly
one uninformative reason code (``"workspace_context_missing"``, the same
token ``assertion_catalog.py`` and ``assertion_impact.py`` already use for
their own read-side absent-workspace denials) regardless of *why* the value
was unusable (``None``, empty string, or whitespace-only) — callers get a
single fail-closed signal, not a menu of failure shapes to branch on.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Single, uninformative denial reason — reused verbatim from the read-side
#: denial idiom in ``assertion_catalog.py`` / ``assertion_impact.py`` so the
#: ledger's read and write paths speak the same fail-closed vocabulary.
REASON_WORKSPACE_CONTEXT_MISSING = "workspace_context_missing"

#: Reason attached to an allowed resolution. Present for symmetry/logging;
#: callers should branch on ``allowed``, not on this string.
REASON_WORKSPACE_ID_RESOLVED = "workspace_id_resolved"


@dataclass(frozen=True)
class WorkspaceWriteResolution:
    """Outcome of :func:`resolve_or_deny` — allow exactly one workspace, or deny.

    Attributes
    ----------
    allowed:
        ``True`` only when a usable ``workspace_id`` was supplied. ``False``
        means the caller MUST perform zero writes.
    workspace_id:
        The confirmed workspace id, stripped of surrounding whitespace but
        otherwise passed straight through to
        ``AssertionRegistry(workspace_id=...)`` /
        ``AssertionMaterializer(workspace_id=...)``. Always ``None`` when
        ``allowed`` is ``False``; always a non-blank, non-whitespace-only
        ``str`` when ``allowed`` is ``True``.
    reason:
        Machine-readable outcome token. ``"workspace_context_missing"`` is
        the sole denial reason (mirrors the WKSP-304 404-not-403 principle —
        one uninformative signal, not a menu of failure shapes).
    """

    allowed: bool
    workspace_id: str | None
    reason: str

    def __post_init__(self) -> None:
        if self.allowed and (not self.workspace_id or not self.workspace_id.strip()):
            raise ValueError(
                "an allowed WorkspaceWriteResolution must carry a non-blank workspace_id"
            )
        if not self.allowed and self.workspace_id is not None:
            raise ValueError("a denied WorkspaceWriteResolution must not carry a workspace_id")


def resolve_or_deny(workspace_id: str | None) -> WorkspaceWriteResolution:
    """Fail-closed gate every new assertion-ledger write call site must call.

    Parameters
    ----------
    workspace_id:
        The call site's already-resolved ``assertion_registry_workspace_id``
        (for a single-operator deployment, this MUST be the literal string
        ``"default"`` per the P1-01 resolution rule documented on this
        module — resolving that value is the call site's job, not this
        function's).

    Returns
    -------
    WorkspaceWriteResolution
        ``allowed=True`` with the ``workspace_id`` stripped of surrounding
        whitespace when the input is a non-blank string. ``allowed=False``
        with ``workspace_id=None`` and
        ``reason="workspace_context_missing"`` for ``None``, an empty
        string, or a whitespace-only string — never an exception, never a
        silent no-op the caller could mistake for success.
    """

    if not isinstance(workspace_id, str) or not workspace_id.strip():
        return WorkspaceWriteResolution(
            allowed=False,
            workspace_id=None,
            reason=REASON_WORKSPACE_CONTEXT_MISSING,
        )
    return WorkspaceWriteResolution(
        allowed=True,
        workspace_id=workspace_id.strip(),
        reason=REASON_WORKSPACE_ID_RESOLVED,
    )


__all__ = [
    "REASON_WORKSPACE_CONTEXT_MISSING",
    "REASON_WORKSPACE_ID_RESOLVED",
    "WorkspaceWriteResolution",
    "resolve_or_deny",
]
