"""Per-record clearance mediation for third-party-LLM prompt egress.

clearance-gates-v1 M5 (leg C) — **closing a pre-existing governance gap**
(operator decision 6), not adding a feature.

WHY THIS IS EGRESS
------------------
Source text placed into a prompt that is sent to a third-party model provider
*leaves the machine*, exactly as a MeatyWiki writeback or a catalog API
response does. It is therefore subject to the same ``redistribution`` scope
that ``services/writeback.py`` and ``services/catalog_service.py`` already
mediate. Before this module nothing per-record guarded it.

WHY ``swarm_drive``'s GOV-001 DOES NOT COVER IT
-----------------------------------------------
``services/swarm_drive.py::_resolve_context`` (GOV-001) reads ONE field —
``run.yaml``'s ``sensitivity`` — and refuses the whole run when it is outside
``{personal, public}``. Three independent reasons that is not this check:

* **Different subject.** It is a *run-level* aggregate decision. It structurally
  cannot say "this record is blocked, allow the others" — the same limitation
  ``services/clearance.py``'s module docstring records for ``guard_check``.
* **Different input.** It reads run sensitivity, never a record's durable
  ``clearance`` stamp. A ``sensitivity: personal`` run made entirely of
  provider-fetched, ``redistribution``-blocked records passes GOV-001 outright.
* **Different reach.** It gates only ``drive_run``. Every entry point in this
  module's call sites (``LiteLLMRouterAdapter.complete``, the two SDK adapters'
  ``run``, the two ``ResearchAgentProvider.start_job`` implementations) is
  reachable without ``swarm_drive`` being involved at all — ``rf swarm run`` →
  ``swarm_service.run_swarm`` → ``adapter.run`` never passes through it.

CONVENTION (mirrors ``services/writeback.py::_stamped_attribution_records``)
---------------------------------------------------------------------------
Collect only the records that *structurally* carry a ``clearance`` dict, then
mediate those. An unstamped record contributes nothing and is NOT a finding:
every record kind predating clearance is structurally incapable of carrying a
stamp (``config/clearance_gates.yaml``'s ``applies_to_kinds`` comment), so
demanding one would convert a safety control into a correctness regression —
it would refuse the 7 committed pediatric bundles. The ``isinstance(..., dict)``
test is load-bearing rather than a presence test: ``catalog_service``'s row
builders emit an explicit ``"clearance": None`` when a record has no stamp, so
keying on presence would refuse every catalog row.

RAW RECORDS, NEVER A PROJECTION (design invariant 4)
----------------------------------------------------
Each call site mediates the **raw caller-supplied request/job mapping**, before
that mapping is flattened into the provider-facing payload. Both SDK adapters
project into a hand-listed ``job_brief`` (``job_id``/``model_profile``/
``allowed_tools``/``intent``/``policy_snapshot``) and both providers project
into an ``AgentJob`` with a fixed field list — a stamp would be dropped by
either. Checking after that projection would trivially pass whatever the
projection stripped.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..paths import FoundryPaths
from . import clearance

#: The only kind ``config/clearance_gates.yaml`` currently governs. Named here
#: rather than inferred: ``mediate_egress`` refuses to infer a kind because an
#: inferred kind that failed to match would silently skip the check.
PROMPT_EGRESS_KIND = "source_attribution"

#: Sending source text to a third-party model provider is redistribution — the
#: content leaves the machine. ``acquisition`` is additionally refused by
#: ``mediate_egress`` itself, regardless of the scope asked about.
PROMPT_EGRESS_SCOPE = "redistribution"

#: Depth bound, matching ``clearance._walk_for_taint``: a pathological or
#: self-referential request mapping must not hang an egress path.
_MAX_DEPTH = 12


def _collect(node: Any, out: list[dict[str, Any]], depth: int) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, Mapping):
        if isinstance(node.get(clearance.TAINT_KEY), dict):
            out.append(dict(node))
        for value in node.values():
            _collect(value, out, depth + 1)
    elif isinstance(node, (list, tuple, set, frozenset)):
        for value in node:
            _collect(value, out, depth + 1)


def stamped_prompt_records(*payloads: Any) -> list[dict[str, Any]]:
    """Every mapping reachable in *payloads* that carries a ``clearance`` dict.

    Recursive because a caller composing a prompt from source records may nest
    them anywhere in the request mapping (``source_records``, ``inputs``,
    ``messages[i]``, ...). The walk sees the raw structure, so it finds a stamp
    wherever the caller put it rather than requiring one blessed key.

    A ``clearance`` value that is present but NOT a dict (``None``, a string) is
    deliberately not collected — see this module's docstring on why keying on
    presence would refuse every pre-existing catalog row.
    """

    found: list[dict[str, Any]] = []
    for payload in payloads:
        _collect(payload, found, 0)
    return found


def mediate_prompt_egress(
    *payloads: Any,
    target: str,
    target_scope: str = PROMPT_EGRESS_SCOPE,
    paths: FoundryPaths | None = None,
) -> clearance.MediationClearance | None:
    """Refuse *payloads* if any stamped record inside them blocks *target_scope*.

    Raises :class:`~research_foundry.services.clearance.ClearanceDenied` — an
    ``RFError`` carrying ``ExitCode.GOVERNANCE`` — when any stamped record
    blocks the scope, blocks ``acquisition``, or carries an absent/emptied/
    malformed ``blocked_scopes``. The refusal deliberately propagates rather
    than degrading, matching ``writeback.mediate_run_egress``: swallowing it
    would turn the control into a no-op, and every call site here is strictly
    upstream of the wire, so a raise means nothing was sent.

    Returns ``None`` — not a token — when *payloads* contain no structurally
    stamped record. That is NOT a fail-open: with zero governed records there is
    nothing to check, and ``mediate_egress([])`` would return a clearance token
    unconditionally anyway. Short-circuiting keeps the registry read (and its
    fail-closed :class:`~research_foundry.services.clearance.ClearanceConfigError`
    on a missing ``config/clearance_gates.yaml``) off the hot path of every
    pre-existing untainted caller, so this control cannot turn a workspace
    without the registry into a broken adapter. Callers here consume no token —
    the check *is* the control; there is no transport backstop on this surface
    because a model prompt is not a :class:`~research_foundry.services.clearance.MediatedPayload`.
    """

    records = stamped_prompt_records(*payloads)
    if not records:
        return None
    return clearance.mediate_egress(
        records,
        kind=PROMPT_EGRESS_KIND,
        target_scope=target_scope,
        target=target,
        paths=paths,
    )


__all__ = [
    "PROMPT_EGRESS_KIND",
    "PROMPT_EGRESS_SCOPE",
    "mediate_prompt_egress",
    "stamped_prompt_records",
]
