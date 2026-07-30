"""Canonical swarm-adapter dispatch service (OPM-3.2, spec §10.6).

Owns the two responsibilities the CLI's ``swarm run`` command used to inline:
dispatching the requested discovery adapters and persisting the resulting
``source_candidates.yaml``. The CLI and the Operator MCP ``swarm.start``
adapter (P3, OPM-3.3, ``operator_mcp_adapters/swarm_start.py``) both call
:func:`run_swarm` so behaviour cannot drift between the two entry points.

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

**P3-F1 (found in P3 review, fixed here): validation ALWAYS runs, dry run or
not.** An earlier revision short-circuited on ``dry_run=True`` BEFORE the
unknown/not-allowlisted checks below, so ``run_swarm(run_id,
["anything-at-all"], dry_run=True)`` silently returned ``outcomes=()`` --
no denial -- for an adapter id a real (non-dry) run would refuse. Both this
module's own ACs ("dry run performs zero effects" and "unknown/disallowed
ids are denied, never dispatched") passed in isolation because no test
exercised their INTERSECTION. The registry/allowlist loop below now always
runs, dry run or not, and always records a denial for an unknown or
not-allowlisted id; the ONLY thing ``dry_run=True`` skips is the real
dispatch (``adapter.run()``) and the write (``dump_yaml``) for an id that
passed both gates -- see :func:`run_swarm`'s own docstring for the exact
boundary.

This module imports no ``fastapi``/``uvicorn`` (the ``[serve]`` extra) and no
``typer`` -- it must import cleanly in a bare install so a later MCP tool
adapter can call it without pulling in the CLI or the HTTP server.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from research_foundry.adapters import get_adapter, load_all
from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.yamlio import dump_yaml, load_yaml

_logger = logging.getLogger(__name__)

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
    merge_with_existing: bool = False,
) -> SwarmRunResult:
    """Dispatch ``requested_adapter_ids`` for ``run_id`` and persist candidates.

    **Validation always runs, dry run or not (P3-F1).** Every requested id is
    checked against the registry/allowlist gates below UNCONDITIONALLY --
    ``outcomes`` on a ``dry_run=True`` result carries a real
    :class:`AdapterDenial` for any unknown/not-allowlisted id, exactly as a
    real (non-dry) call would. ``dry_run=True`` skips exactly two things, for
    an id that passed both gates: the real dispatch (``adapter.run()``) and
    the persistence write (:func:`~research_foundry.yamlio.dump_yaml`) --
    ``wrote_candidates`` is always ``False`` and ``source_candidates`` is
    always ``()`` on a dry-run result, regardless of what ``outcomes`` holds.

    ``merge_with_existing`` (default ``False``, preserves the exact prior
    overwrite-whole-file behaviour for every existing caller -- the CLI's
    ``rf swarm run`` and this module's own test suite): when ``True``, this
    call's newly-dispatched candidates are ADDITIVELY merged onto whatever is
    already durably persisted at ``rp.source_candidates`` (read-modify-write)
    rather than replacing it outright. This is the ONLY mechanism the
    Operator MCP ``swarm.start`` adapter (OPM-3.3) relies on for its
    non-duplication acceptance criterion: that adapter dispatches ONE
    ``requested_adapter_ids`` element per governed, checkpointed action (so
    cancellation/resume has a safe point BETWEEN adapters), calling this
    function once per adapter with a single-element list -- without merging,
    each such call would silently overwrite every PRIOR action's already-
    persisted candidates instead of adding to them. The returned
    ``SwarmRunResult.source_candidates`` still reflects only THIS call's own
    newly-dispatched candidates (never the merged/cumulative file content) --
    symmetrical with every other field on the result, which always describes
    "what happened in this call", never durable file state. A malformed or
    unreadable pre-existing file is treated as empty (logged, never raised --
    this function has never propagated a raw I/O/parse exception for its own
    write path, and merging does not change that).
    """

    resolved_paths = paths or FoundryPaths.discover()
    load_all()
    rp = resolved_paths.run_paths(run_id)
    requested = tuple(a.strip() for a in requested_adapter_ids)
    brief = load_md(rp.research_brief)[0] if rp.research_brief.exists() else {}

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
        if dry_run:
            # P3-F1: this id passed both gates -- a real run WOULD dispatch
            # it -- but dry run performs zero effects: no adapter.run() call,
            # no outcome recorded for it either (only denials ever populate
            # `outcomes` on a dry-run result; see the "gpt_researcher,
            # paperqa2" dry-run test in this module's own test suite, which
            # asserts `outcomes == ()` for two VALID, allowlisted ids).
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

    if dry_run:
        # P3-F1: reached only after every requested id has been validated
        # above -- `outcomes` may already hold real denials. Zero effects
        # past this point: no adapter.run() was called for a valid id (the
        # `continue` above), and dump_yaml is never reached.
        return SwarmRunResult(
            run_id=run_id,
            dry_run=True,
            requested_adapter_ids=requested,
            outcomes=tuple(outcomes),
            source_candidates=(),
            wrote_candidates=False,
            source_candidates_path=None,
        )

    if merge_with_existing and rp.source_candidates.exists():
        try:
            existing = load_yaml(rp.source_candidates)
        except Exception as exc:  # noqa: BLE001 - never let a corrupt prior file abort this write
            _logger.warning(
                "swarm_service.run_swarm: existing %s unreadable (%s) -- "
                "merging onto an empty prior list for run_id=%s",
                rp.source_candidates,
                type(exc).__name__,
                run_id,
            )
            existing = None
        prior = existing.get("source_candidates") if isinstance(existing, dict) else None
        persisted = [*prior, *candidates] if isinstance(prior, list) else list(candidates)
    else:
        persisted = candidates

    dump_yaml({"source_candidates": persisted}, rp.source_candidates)

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
