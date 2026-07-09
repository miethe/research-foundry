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

from dataclasses import dataclass
from pathlib import Path

from ..paths import FoundryPaths
from .capture import capture_idea, triage_idea
from .planning import plan_run


@dataclass(frozen=True)
class LaunchRunResult:
    """Outcome of :func:`launch_run`.

    ``raw_idea_id`` is ``None`` when the ``intent_id`` path was taken (no
    capture/triage step ran). ``status`` is always ``"planned"`` on success --
    the initial ``run.yaml.status`` value written by :func:`plan_run`.
    """

    run_id: str
    status: str
    intent_id: str
    raw_idea_id: str | None
    brief_path: Path
    swarm_path: Path
    routing_path: Path


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
    )


__all__ = ["LaunchRunResult", "launch_run"]
