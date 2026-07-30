"""Canonical swarm-adapter dispatch service (OPM-3.2, spec §10.6).

Owns the two responsibilities the CLI's ``swarm run`` command used to inline:
dispatching the requested discovery adapters and persisting the resulting
``source_candidates.yaml``. The CLI and the future Operator MCP ``swarm.start``
adapter both call :func:`run_swarm` so behaviour cannot drift between the two
entry points.

**Closed dispatch.** ``run_swarm`` never hands a caller-supplied adapter id
straight to :func:`research_foundry.adapters.get_adapter`. Every id is checked
against two independent, hard-coded gates before dispatch:

* it must be *known* -- present in the discovery registry
  (:data:`research_foundry.adapters.base._REGISTRY`, populated by
  :func:`research_foundry.adapters.load_all`); an id the registry has never
  heard of is denied as ``unknown_adapter``.
* it must be *allowed* -- present in :data:`ALLOWED_ADAPTER_IDS`, a literal
  policy constant defined in this module (not sourced from config, an
  environment variable, or any other mutable input, so there is no producer
  that can make it silently empty-means-allow-all or missing-means-skip). A
  registered id absent from this allowlist is denied as
  ``adapter_not_allowlisted``.

Both denials are returned as typed :class:`AdapterDenial` values on the
matching :class:`AdapterOutcome` -- never raised, never silently skipped past
dispatch. Neither denial path calls ``adapter.run()``.

This module imports no ``fastapi``/``uvicorn`` (the ``[serve]`` extra) and no
``typer`` -- it must import cleanly in a bare install so a later MCP tool
adapter can call it without pulling in the CLI or the HTTP server.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from research_foundry.adapters import get_adapter, load_all
from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.yamlio import dump_yaml

#: Policy allowlist (spec §10.6 / OPM-3.2 acceptance criteria). A literal
#: constant, not derived from any external input -- there is no producer that
#: could make this set silently empty (which would fail *closed*, denying
#: everything) or absent (which, unlike a missing config field, cannot be
#: mistaken for "no restriction"). Extend this set only when a new adapter
#: module has been reviewed and registered in ``adapters/__init__.py::_CONCRETE``.
ALLOWED_ADAPTER_IDS: frozenset[str] = frozenset(
    {
        "arc_council",
        "claude_agent_sdk",
        "gpt_researcher",
        "litellm_router",
        "notebooklm",
        "opencode",
        "openai_agents",
        "paperqa2",
    }
)

#: Distinct denial reasons (requirement: unknown vs. known-but-not-allowed
#: must be typed and distinguishable, never collapsed into one generic deny).
DENIAL_UNKNOWN_ADAPTER = "unknown_adapter"
DENIAL_NOT_ALLOWLISTED = "adapter_not_allowlisted"


@dataclass(frozen=True)
class AdapterDenial:
    """A typed refusal to dispatch ``adapter_id`` -- never an exception."""

    adapter_id: str
    reason: str


@dataclass(frozen=True)
class AdapterOutcome:
    """Per-adapter result of one :func:`run_swarm` call.

    Exactly one of ``denial``, ``error``, or a successful dispatch (``ran``
    True) applies. ``error`` is a bounded ``"ExceptionType: message"`` string
    -- an adapter that raises never propagates a raw exception or traceback
    out of this service.
    """

    adapter_id: str
    ran: bool
    degraded: bool = False
    source_candidate_count: int = 0
    denial: AdapterDenial | None = None
    error: str | None = None


@dataclass(frozen=True)
class SwarmRunResult:
    """Outcome of one :func:`run_swarm` call."""

    run_id: str
    dry_run: bool
    requested_adapter_ids: tuple[str, ...]
    outcomes: tuple[AdapterOutcome, ...]
    source_candidates: tuple[dict[str, Any], ...]
    wrote_candidates: bool
    source_candidates_path: Path | None


def run_swarm(
    run_id: str,
    requested_adapter_ids: Sequence[str],
    *,
    profile: str = "personal",
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
) -> SwarmRunResult:
    """Dispatch ``requested_adapter_ids`` for ``run_id`` and persist candidates.

    ``dry_run=True`` performs no adapter dispatch and no file write: it
    returns immediately with an empty ``outcomes``/``source_candidates`` and
    ``wrote_candidates=False``, before the allowlist/registry checks, before
    any ``adapter.run()`` call, and before :func:`~research_foundry.yamlio.
    dump_yaml` is called.
    """

    resolved_paths = paths or FoundryPaths.discover()
    load_all()
    rp = resolved_paths.run_paths(run_id)
    requested = tuple(a.strip() for a in requested_adapter_ids)
    brief = load_md(rp.research_brief)[0] if rp.research_brief.exists() else {}

    if dry_run:
        return SwarmRunResult(
            run_id=run_id,
            dry_run=True,
            requested_adapter_ids=requested,
            outcomes=(),
            source_candidates=(),
            wrote_candidates=False,
            source_candidates_path=None,
        )

    outcomes: list[AdapterOutcome] = []
    candidates: list[dict[str, Any]] = []
    for aid in requested:
        adapter = get_adapter(aid)
        if adapter is None:
            outcomes.append(
                AdapterOutcome(
                    adapter_id=aid,
                    ran=False,
                    denial=AdapterDenial(aid, DENIAL_UNKNOWN_ADAPTER),
                )
            )
            continue
        if aid not in ALLOWED_ADAPTER_IDS:
            outcomes.append(
                AdapterOutcome(
                    adapter_id=aid,
                    ran=False,
                    denial=AdapterDenial(aid, DENIAL_NOT_ALLOWLISTED),
                )
            )
            continue
        try:
            result = adapter.run({"brief": brief, "profile": profile})
        except Exception as exc:  # noqa: BLE001 - adapter contract: never leak a raw traceback
            outcomes.append(
                AdapterOutcome(
                    adapter_id=aid,
                    ran=False,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        candidates.extend(result.source_candidates)
        outcomes.append(
            AdapterOutcome(
                adapter_id=aid,
                ran=True,
                degraded=result.degraded,
                source_candidate_count=len(result.source_candidates),
            )
        )

    dump_yaml({"source_candidates": candidates}, rp.source_candidates)

    return SwarmRunResult(
        run_id=run_id,
        dry_run=False,
        requested_adapter_ids=requested,
        outcomes=tuple(outcomes),
        source_candidates=tuple(candidates),
        wrote_candidates=True,
        source_candidates_path=rp.source_candidates,
    )


__all__ = [
    "ALLOWED_ADAPTER_IDS",
    "DENIAL_UNKNOWN_ADAPTER",
    "DENIAL_NOT_ALLOWLISTED",
    "AdapterDenial",
    "AdapterOutcome",
    "SwarmRunResult",
    "run_swarm",
]
