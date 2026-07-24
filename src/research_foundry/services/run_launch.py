"""Run-launch orchestration service (HTTP-native scaffold + register chain).

``launch_run`` wraps the existing deterministic services --
``capture_idea`` -> ``triage_idea`` (``services/capture.py``) and ``plan_run``
(``services/planning.py``) -- so that ``POST /api/runs`` can perform, in one
call, either:

* the full ``rf capture`` -> ``rf triage`` -> ``rf plan`` chain (given
  ``text``), or
* ``rf plan <intent_id>`` alone (given an already-triaged ``intent_id``).

This module owns ONLY the "exactly one of text/intent_id" branching and the
thin result-shape adaptation. It does not modify, wrap, or duplicate any
validation/governance behavior already implemented inside the wrapped
functions -- errors they raise (``NotFoundError``, ``GovernanceError``,
``SchemaError``, base ``RFError``) propagate unchanged for the router to map
to HTTP status codes.

**Scope boundary (Feature Contract Decision #1):** this module performs the
DETERMINISTIC scaffold+register chain ONLY. It never spawns, drives, or
polls the Path B Claude-agent discovery swarm -- that remains an out-of-band,
Claude-Code-agent-driven activity. See
``docs/project_plans/feature_contracts/features/http-run-launch-endpoint.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

# NOTE (serve-extra decoupling, FU-1 — same convention as ``planning.py`` /
# ``export_service.py`` / ``agent_job_service.py``): ``api.auth.provider``
# module-imports ``starlette``; ``launch_run`` only ever forwards ``identity``
# straight through to ``plan_run`` (never inspects it), so it needs the name
# only for annotations.
if TYPE_CHECKING:
    from ..api.auth.provider import AuthIdentity

from ..config import AssertionLedgerCapabilities, FoundryConfig
from ..paths import FoundryPaths
from .assertion_reuse import ReuseDecision, evaluate_reuse
from .assertion_workspace import resolve_or_deny
from .capture import capture_idea, triage_idea
from .planning import plan_run


@dataclass(frozen=True)
class LaunchRunResult:
    """Outcome of :func:`launch_run`.

    ``raw_idea_id`` is ``None`` when the ``intent_id`` path was taken (no
    capture/triage step ran). ``status`` is always ``"planned"`` on success --
    the initial ``run.yaml.status`` value written by :func:`plan_run`.

    ``evidence_plan_ref`` and ``retrieval_summary`` (CARP-5.1) are forwarded
    unmodified from :class:`~.planning.PlanResult` -- both ``None`` unless
    ``retrieval_policy`` was active for this launch.
    """

    run_id: str
    status: str
    intent_id: str
    raw_idea_id: str | None
    brief_path: Path
    swarm_path: Path
    routing_path: Path
    reuse_decision: ReuseDecision | None = None
    evidence_plan_ref: str | None = None
    retrieval_summary: dict[str, Any] | None = None


def retrieve_first_reuse_decision(
    assertion: Mapping[str, Any] | None,
    *,
    workspace_id: str | None,
    required_edition_id: str | None = None,
    required_extraction_contract: str | None = None,
    capabilities: AssertionLedgerCapabilities | None = None,
) -> ReuseDecision:
    """Evaluate a supplied assertion before a caller schedules a reuse path.

    The normal run scaffold remains unchanged unless a caller explicitly asks
    for assertion reuse.  This seam gives run orchestration the same
    fail-closed policy decision as the ledger, before any dependent work is
    scheduled or a candidate can be treated as current.

    ``workspace_id`` is first normalized through P1's shared
    :func:`~research_foundry.services.assertion_workspace.resolve_or_deny`
    gate (the same helper every assertion-ledger write call site uses) so an
    absent/blank/whitespace-only workspace context collapses to the same
    ``"workspace_context_missing"`` reason :func:`evaluate_reuse` already
    reports for a falsy ``workspace_id`` -- this adds no new policy, it just
    routes the normalization through the existing P1 gate rather than
    relying on ``evaluate_reuse``'s own truthiness check alone.
    """

    resolution = resolve_or_deny(workspace_id)
    decision = evaluate_reuse(
        assertion,
        workspace_id=resolution.workspace_id,
        required_edition_id=required_edition_id,
        required_extraction_contract=required_extraction_contract,
    )
    if decision.allowed and capabilities is not None and not capabilities.automated_reuse_allowed:
        return ReuseDecision("deny", "automated_reuse_disabled", decision.assertion_id)
    return decision


def launch_run(
    *,
    text: str | None = None,
    intent_id: str | None = None,
    title: str | None = None,
    sensitivity: str = "personal",
    urgency: str = "medium",
    tags: list[str] | None = None,
    backlog_idea_ref: str | None = None,
    depth: str = "standard",
    audience: str = "technical",
    max_cost_usd: float = 5.0,
    freshness_days: int = 180,
    profile: str | None = None,
    project: str | None = None,
    reuse_assertion: Mapping[str, Any] | None = None,
    reuse_workspace_id: str | None = None,
    required_reuse_edition_id: str | None = None,
    required_extraction_contract: str | None = None,
    visibility: str = "workspace",
    identity: AuthIdentity | None = None,
    retrieval_policy: str | None = None,
    retrieval_limits: Mapping[str, Any] | None = None,
    paths: FoundryPaths | None = None,
) -> LaunchRunResult:
    """Scaffold and register a new run (scaffold + register only).

    Exactly one of ``text`` / ``intent_id`` must be supplied:

    * ``text`` -- runs ``capture_idea`` -> ``triage_idea`` -> ``plan_run``
      (mirrors ``rf capture`` -> ``rf triage`` -> ``rf plan``). ``title``,
      ``sensitivity``, ``urgency``, ``tags``, and ``backlog_idea_ref`` are
      forwarded to ``capture_idea`` only (mirroring the ``rf capture`` CLI
      parameter set -- ``rf plan`` accepts no ``--backlog-idea-ref`` flag, so
      it is not threaded into ``plan_run`` here either).
    * ``intent_id`` -- an already-triaged intent; calls ``plan_run`` directly
      (mirrors ``rf plan <intent_id>`` alone). ``raw_idea_id`` is ``None`` in
      the result.

    ``depth``, ``audience``, ``max_cost_usd``, ``freshness_days``, ``profile``,
    and ``project`` are passed through to ``plan_run`` on both paths.

    ``visibility`` and ``identity`` are DF-004 workspace-ownership fields,
    forwarded straight through to ``plan_run`` unmodified: ``identity`` is
    never inspected here beyond that passthrough, so ``run.yaml.workspace_id``
    is always stamped from ``identity.workspace_id`` by ``plan_run`` itself
    (never from client-supplied input on this path). ``identity=None`` (the
    default -- no auth middleware configured) is byte-identical to the
    pre-DF-004 behavior.

    ``retrieval_policy`` and ``retrieval_limits`` are CARP-4.2 passthroughs,
    forwarded unmodified to ``plan_run`` (same "never inspected here" rule as
    ``identity``). ``retrieval_policy=None`` (the default) is byte-identical
    to the pre-CARP behavior: ``plan_run`` treats it as ``"disabled"`` and
    builds no evidence plan.

    Does NOT spawn, drive, or poll the Path B discovery swarm (Decision #1) --
    this is the deterministic scaffold+register chain only.

    Raises:
        ValueError: both or neither of ``text``/``intent_id`` supplied.
        NotFoundError: ``intent_id`` does not resolve to an existing intent
            (propagated from :func:`~research_foundry.services.planning.plan_run`).
        GovernanceError: the governance preflight blocked planning (propagated
            from :func:`~research_foundry.services.planning.plan_run`).
        SchemaError: a produced artifact failed schema validation (propagated
            from either wrapped service).
    """

    if bool(text) == bool(intent_id):
        raise ValueError(
            "Exactly one of 'text' or 'intent_id' is required "
            f"(text={'set' if text else 'unset'}, intent_id={'set' if intent_id else 'unset'})."
        )

    paths = paths or FoundryPaths.discover()

    reuse_decision: ReuseDecision | None = None
    if reuse_assertion is not None:
        reuse_decision = retrieve_first_reuse_decision(
            reuse_assertion,
            workspace_id=reuse_workspace_id,
            required_edition_id=required_reuse_edition_id,
            required_extraction_contract=required_extraction_contract,
            capabilities=FoundryConfig(paths=paths).assertion_ledger_capabilities(),
        )
        if not reuse_decision.allowed:
            raise ValueError(f"reuse_not_eligible:{reuse_decision.reason_code}")

    raw_idea_id: str | None = None

    if text:
        cap = capture_idea(
            text,
            title=title,
            sensitivity=sensitivity,
            urgency=urgency,
            tags=tags,
            backlog_idea_ref=backlog_idea_ref,
            paths=paths,
        )
        raw_idea_id = cap.raw_idea_id
        tri = triage_idea(cap.raw_idea_id, paths=paths)
        if tri.intent_id is None:
            # triage_idea(create_intent=True) (the default used here) always
            # produces an intent_id; this branch is defensive -- fail loudly
            # rather than silently planning against a null intent.
            raise ValueError(
                f"triage_idea did not produce an intent_id for raw idea {cap.raw_idea_id!r}."
            )
        resolved_intent_id = tri.intent_id
    else:
        assert intent_id is not None  # guaranteed by the exactly-one-of check above
        resolved_intent_id = intent_id

    plan_result = plan_run(
        resolved_intent_id,
        depth=depth,
        audience=audience,
        max_cost_usd=max_cost_usd,
        freshness_days=freshness_days,
        profile=profile,
        project=project,
        visibility=visibility,
        identity=identity,
        retrieval_policy=retrieval_policy,
        retrieval_limits=retrieval_limits,
        paths=paths,
    )

    return LaunchRunResult(
        run_id=plan_result.run_id,
        status="planned",
        intent_id=resolved_intent_id,
        raw_idea_id=raw_idea_id,
        brief_path=plan_result.brief_path,
        swarm_path=plan_result.swarm_path,
        routing_path=plan_result.routing_path,
        reuse_decision=reuse_decision,
        evidence_plan_ref=plan_result.evidence_plan_ref,
        retrieval_summary=plan_result.retrieval_summary,
    )


__all__ = ["LaunchRunResult", "launch_run", "retrieve_first_reuse_decision"]
