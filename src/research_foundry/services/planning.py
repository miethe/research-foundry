"""Planning service — ``rf plan``.

Turns a research intent (+ its I-BOM) into a planned run: a run directory
containing ``run.yaml``, ``research_brief.md``, ``swarm_plan.yaml``, and
``routing_decision.yaml``. The default path is fully deterministic — no network
or API keys — sourcing model profiles from the linked I-BOM's ``model_policy``,
tools from the enabled entries in ``config/tools.yaml``, and the budget from the
caller's arguments.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..errors import ExitCode, GovernanceError, NotFoundError, SchemaError
from ..frontmatter import dump_md
from ..ids import (
    brief_id,
    disambiguate_id,
    now_iso,
    routing_id,
    slugify,
    swarm_id,
)
from ..ids import (
    run_id as make_run_id,
)
from ..paths import FoundryPaths, RunPaths
from ..registry import RUN_INDEX, Registry
from ..schemas import default_registry, validate
from ..yamlio import append_jsonl, dump_yaml, load_yaml
from . import governance as governance_svc
from .backlog_metadata import BacklogMetadata, lookup_metadata

# Default model profiles when the I-BOM does not specify a model_policy.
_DEFAULT_MODEL_POLICY = {
    "extraction_profile": "rf_extract_cheap",
    "synthesis_profile": "rf_synthesize_deep",
    "verification_profile": "rf_verify_balanced",
}

# Fixed swarm agent roster (spec §6.7). model_profile keys map onto the I-BOM's
# model_policy so the deep/cheap/verify split flows from the intent's policy.
_AGENT_SPECS: list[dict[str, str]] = [
    {
        "role": "source_scout",
        "posture": "researcher",
        "tool": "gpt_researcher",
        "profile_key": "extraction_profile",
        "task": "Find candidate sources and produce source_candidates.yaml.",
    },
    {
        "role": "paper_analyst",
        "posture": "researcher",
        "tool": "paperqa2",
        "profile_key": "extraction_profile",
        "task": "Answer research questions over local scientific PDFs.",
    },
    {
        "role": "source_carder",
        "posture": "operator",
        "tool": "claude_agent_sdk",
        "profile_key": "extraction_profile",
        "task": "Convert sources into source cards.",
    },
    {
        "role": "claim_mapper",
        "posture": "critic",
        "tool": "claude_agent_sdk",
        "profile_key": "verification_profile",
        "task": "Map extracted findings to claims.",
    },
    {
        "role": "synthesis_lead",
        "posture": "synthesizer",
        "tool": "claude_agent_sdk",
        "profile_key": "synthesis_profile",
        "task": "Write report only from supported claims and labeled inferences.",
    },
    {
        "role": "governance_officer",
        "posture": "red_team",
        "tool": "deterministic_validator",
        "profile_key": None,
        "task": "Block invalid key/data/writeback combinations.",
    },
]

_REQUIRED_OUTPUTS = [
    "source_candidates.yaml",
    "source_cards",
    "extraction_cards",
    "claim_ledger.yaml",
    "report_draft.md",
    "verification.yaml",
    "evidence_bundle.yaml",
    "ccdash_event.yaml",
]

_POSTURE_CHAIN = ["researcher", "critic", "synthesizer", "governance_officer"]
_CONTEXT_PACKS = ["research_foundry_core", "agentic_os_core"]
_VALIDATION_STEPS = [
    "schema_validation",
    "governance_guard",
    "claim_verifier",
    "council_review_optional",
]
_WRITEBACKS = [
    {"target": "meatywiki", "type": "source_note"},
    {"target": "meatywiki", "type": "decision_record"},
    {"target": "skillmeat", "type": "skillbom_candidate"},
    {"target": "ccdash", "type": "execution_event"},
]


@dataclass(frozen=True)
class PlanResult:
    """Outcome of :func:`plan_run` — the planned run and its four artifacts."""

    run_id: str
    brief_id: str
    swarm_id: str
    routing_id: str
    run_dir: Path
    brief_path: Path
    swarm_path: Path
    routing_path: Path


def load_intent(intent_id: str, *, paths: FoundryPaths | None = None) -> dict[str, Any]:
    """Load a research intent YAML by id from ``intents/active/``.

    Raises :class:`NotFoundError` if the intent file does not exist.
    """

    paths = paths or FoundryPaths.discover()
    path = paths.intents_active / f"{intent_id}.yaml"
    if not path.exists():
        raise NotFoundError(f"intent not found: {intent_id} ({path})")
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise NotFoundError(f"intent file is not a mapping: {path}")
    return data


def _load_ibom(intent: dict[str, Any], paths: FoundryPaths) -> dict[str, Any]:
    """Resolve the I-BOM linked from ``intent.ibom_ref`` (best-effort).

    Returns ``{}`` when no I-BOM is linked or the file is missing so planning
    stays deterministic and degrades gracefully.
    """

    ref = intent.get("ibom_ref")
    if not ref:
        return {}
    # ref may be a bare id or a path. Prefer the active iboms dir by id.
    candidate = paths.iboms_active / f"{ref}.yaml"
    if not candidate.exists():
        as_path = Path(ref)
        candidate = as_path if as_path.is_absolute() else paths.root / ref
    if not candidate.exists():
        return {}
    data = load_yaml(candidate)
    return data if isinstance(data, dict) else {}


def _model_policy(ibom: dict[str, Any]) -> dict[str, str]:
    policy = ibom.get("model_policy") if isinstance(ibom, dict) else None
    if not isinstance(policy, dict):
        return dict(_DEFAULT_MODEL_POLICY)
    merged = dict(_DEFAULT_MODEL_POLICY)
    for key in _DEFAULT_MODEL_POLICY:
        if policy.get(key):
            merged[key] = str(policy[key])
    return merged


def _enabled_tools(config: FoundryConfig) -> list[str]:
    """Enabled tool ids from ``config/tools.yaml`` (deterministic order)."""

    tools = config.tools.get("tools", {}) if isinstance(config.tools, dict) else {}
    enabled = [name for name, spec in tools.items()
               if isinstance(spec, dict) and spec.get("enabled")]
    return enabled or ["claude_agent_sdk"]


def _selected_tools(config: FoundryConfig) -> list[str]:
    """Tools surfaced in the routing decision: enabled tools + the model router."""

    enabled = _enabled_tools(config)
    # litellm is the model router referenced by routing even when not enabled
    # as a discovery tool; include it last for a stable chain.
    tools = list(enabled)
    if "litellm" not in tools:
        tools.append("litellm")
    return tools


def _build_questions(intent: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    rq = intent.get("research_questions") or {}
    primary_src = rq.get("primary") if isinstance(rq, dict) else None
    secondary_src = rq.get("secondary") if isinstance(rq, dict) else None

    primary: list[dict[str, str]] = []
    for i, q in enumerate(primary_src or [], start=1):
        primary.append({"id": f"rq_{i:03d}", "question": str(q)})
    if not primary:
        objective = str(intent.get("objective") or intent.get("title") or "research topic")
        primary.append({"id": "rq_001", "question": f"What does the evidence say about {objective}?"})

    secondary: list[dict[str, str]] = []
    offset = len(primary)
    for j, q in enumerate(secondary_src or [], start=1):
        secondary.append({"id": f"rq_{offset + j:03d}", "question": str(q)})

    return {"primary": primary, "secondary": secondary}


def _gc_partial_run_dir(run: RunPaths) -> None:
    """Best-effort removal of a scaffolded run dir that never got a ``run.yaml``.

    ``plan_run`` calls this from its except-and-reraise handler when anything
    fails between ``ensure_scaffold()`` and the registry ``upsert()`` (schema
    validation, governance block, I/O error, ...). At that point the run
    directory was just created by this same call -- ``disambiguate_id``
    already confirmed no directory existed at ``run_id`` beforehand -- so it
    is safe to remove wholesale rather than leaving an empty/partial stub
    behind for the runs-viewer to surface as a blank entry (AAR gap 3).

    Guarded on ``run.run_yaml`` still being absent so a failure that somehow
    occurs *after* ``run.yaml`` was already written (e.g. in code added later)
    never deletes a run that has real content. Swallows all removal errors --
    this is cleanup, not the error the caller is already re-raising.
    """

    try:
        if not run.run_yaml.exists():
            shutil.rmtree(run.run, ignore_errors=True)
    except Exception:  # noqa: BLE001 — best-effort GC, never mask the real error
        pass


def plan_run(
    intent_id: str,
    *,
    depth: str = "standard",
    audience: str = "technical",
    max_cost_usd: float = 5.0,
    max_runtime_minutes: int = 60,
    freshness_days: int = 180,
    profile: str | None = None,
    project: str | None = None,
    backlog_idea_ref: str | None = None,
    paths: FoundryPaths | None = None,
) -> PlanResult:
    """Plan a research run for ``intent_id``.

    Loads the intent and its linked I-BOM, mints a run id, scaffolds the run
    directory, and writes ``run.yaml``, ``research_brief.md``,
    ``swarm_plan.yaml``, and ``routing_decision.yaml``. The brief, swarm plan,
    and routing decision are validated against their schemas. The run is
    recorded in ``registries/run_index.yaml``.

    After the routing decision is written, a governance preflight is run for the
    effective key ``profile`` (defaulting to the intent's
    ``governance.key_profile_allowed`` or ``personal``). A blocking violation
    (e.g. a ``work_approved`` profile against a personal-only intent) raises
    :class:`GovernanceError`; a normal personal run plans cleanly.

    The ``project`` slug is threaded through to ``run.yaml`` (``project`` field)
    and to the NotebookLM correlation registry
    (``registries/notebooklm/notebooks.yaml``) so that project→run associations
    are recorded without any network access.  ``notebook_id`` in ``run.yaml``
    starts as ``None`` and is filled in later by the writeback or sourcing layer.

    When ``backlog_idea_ref`` is provided (e.g. ``"RIB-001"``), the five new
    metadata fields (``linked_projects``, ``category``, ``tags``,
    ``backlog_idea_ref``, ``backlog_idea_id``) are derived from the backlog
    entry and written to ``run.yaml``.  When absent, ``linked_projects`` is
    derived from the resolved project slug (if non-``"unassigned"``), and
    the remaining fields are ``null``.

    Parameters
    ----------
    intent_id:
        Active intent identifier.
    depth:
        Research depth profile (``skim`` | ``standard`` | ``deep`` |
        ``exhaustive``).
    audience:
        Target audience.
    max_cost_usd:
        Budget ceiling in USD.
    max_runtime_minutes:
        Wall-clock budget in minutes.
    freshness_days:
        Maximum source age in days.
    profile:
        Runtime key profile for the governance preflight.
    project:
        Project slug.  Resolved from (in priority order): the ``project``
        argument, the intent's ``project`` field, the intent's
        ``raw_idea.suggested_project`` field, or ``'unassigned'``.
    backlog_idea_ref:
        Optional ``RIB-NNN`` reference to a backlog idea.  When provided,
        ``linked_projects``, ``category``, ``tags``, ``backlog_idea_ref``,
        and ``backlog_idea_id`` are populated in ``run.yaml`` from the
        backlog entry.
    paths:
        FoundryPaths override (defaults to ``FoundryPaths.discover()``).
    """

    paths = paths or FoundryPaths.discover()
    config = FoundryConfig(paths=paths)

    intent = load_intent(intent_id, paths=paths)
    ibom = _load_ibom(intent, paths)
    policy = _model_policy(ibom)

    # Resolve project slug: explicit arg → intent.project → raw_idea suggested_project → 'unassigned'.
    effective_project: str = (
        project
        or str(intent.get("project") or "").strip()
        or str(intent.get("suggested_project") or "").strip()
        or "unassigned"
    )

    # --- Derive new metadata fields from backlog (P3 creation path) ----------
    # Uses the shared backlog_metadata helper (same helper used by P2 backfill
    # migration) so derivation logic is never duplicated.
    _bm: BacklogMetadata | None = None
    if backlog_idea_ref:
        _bm = lookup_metadata(backlog_idea_ref, paths)

    if _bm is not None:
        _linked_projects: list[str] | None = _bm.linked_projects or None
        _category: str | None = _bm.category
        _tags: list[str] | None = _bm.tags or None
        _backlog_idea_ref: str | None = _bm.backlog_idea_ref
        _backlog_idea_id: str | None = _bm.backlog_idea_id
    else:
        # Graceful degradation: derive linked_projects from resolved project slug
        # if it is non-trivial; leave the rest null.
        _linked_projects = [effective_project] if effective_project != "unassigned" else None
        _category = None
        _tags = None
        _backlog_idea_ref = None
        _backlog_idea_id = None

    title = str(intent.get("title") or intent_id)
    intent_slug = slugify(title)
    # Disambiguate on actual collision only: two distinct intents whose titles share
    # a first-6-word slug would otherwise mint the same run id and overwrite the
    # prior run directory. Seed the per-run suffix from the intent id (stable).
    run_id = disambiguate_id(
        make_run_id(intent_slug),
        seed=intent_id,
        exists=lambda r: (paths.runs / r).exists(),
    )
    b_id = brief_id(intent_slug)
    s_id = swarm_id(intent_slug)
    r_id = routing_id(intent_slug)
    created_at = now_iso()

    governance = intent.get("governance") or {}
    human_required = bool(governance.get("requires_human_review")) if isinstance(
        governance, dict
    ) else False
    sensitivity = (
        str(governance.get("sensitivity")) if isinstance(governance, dict)
        and governance.get("sensitivity") else "personal"
    )

    node_ref = intent.get("intenttree_node_ref")
    active_node_id = str(node_ref) if node_ref else "tree_research_foundry"

    run = paths.run_paths(run_id).ensure_scaffold()

    try:
        # --- research_brief.md (front matter TOP LEVEL + body) -------------------
        brief_fields: dict[str, Any] = {
            "schema_version": 0.1,
            "type": "research_brief",
            "id": b_id,
            "intent_id": intent_id,
            "title": title,
            "audience": audience,
            "research_depth": depth,
            "questions": _build_questions(intent),
            "source_strategy": {
                "include_source_types": [
                    "official_docs",
                    "peer_reviewed_papers",
                    "standards",
                    "reputable_news",
                    "vendor_docs",
                    "repo_readmes",
                    "personal_notes",
                ],
                "exclude_source_types": [
                    "unsourced_social_posts",
                    "SEO_content_farms",
                ],
                "freshness": {
                    "required": True,
                    "max_age_days": int(freshness_days),
                    "exceptions": ["foundational_theory", "historical_background"],
                },
            },
            "output_requirements": {
                "format": "markdown",
                "include_claim_ledger": True,
                "include_source_cards": True,
                "include_inference_log": True,
                "include_open_questions": True,
            },
        }
        objective = str(intent.get("objective") or title)
        brief_body = (
            f"# Research Brief: {title}\n\n"
            f"**Objective.** {objective}\n\n"
            f"**Depth.** {depth}  |  **Audience.** {audience}\n\n"
            "## Questions\n\n"
            + "\n".join(f"- ({q['id']}) {q['question']}" for q in brief_fields["questions"]["primary"])
            + "\n"
        )
        dump_md(brief_fields, brief_body, run.research_brief)
        _validate_or_raise(brief_fields, "research_brief", run.research_brief)

        # --- swarm_plan.yaml -----------------------------------------------------
        agents: list[dict[str, str]] = []
        for spec in _AGENT_SPECS:
            profile_key = spec["profile_key"]
            model_profile = policy.get(profile_key, "none") if profile_key else "none"
            agents.append(
                {
                    "role": spec["role"],
                    "posture": spec["posture"],
                    "tool": spec["tool"],
                    "model_profile": model_profile,
                    "task": spec["task"],
                }
            )
        swarm: dict[str, Any] = {
            "schema_version": 0.1,
            "type": "swarm_plan",
            "id": s_id,
            "brief_id": b_id,
            "intent_id": intent_id,
            "created_at": created_at,
            "status": "planned",
            "budget": {
                "max_cost_usd": float(max_cost_usd),
                "max_runtime_minutes": int(max_runtime_minutes),
                "extraction_model_profile": policy["extraction_profile"],
                "synthesis_model_profile": policy["synthesis_profile"],
                "verification_model_profile": policy["verification_profile"],
            },
            "agents": agents,
            "required_outputs": list(_REQUIRED_OUTPUTS),
        }
        dump_yaml(swarm, run.swarm_plan)
        _validate_or_raise(swarm, "swarm_plan", run.swarm_plan)

        # --- routing_decision.yaml ----------------------------------------------
        routing: dict[str, Any] = {
            "schema_version": 0.1,
            "type": "routing_decision",
            "id": r_id,
            "intent_id": intent_id,
            "active_node_id": active_node_id,
            "selected_abstraction_level": "L4",
            "selected_posture_chain": list(_POSTURE_CHAIN),
            "selected_skillbom": "skill_research_swarm_v0",
            "selected_context_packs": list(_CONTEXT_PACKS),
            "selected_tools": _selected_tools(config),
            "human_required": human_required,
            "rationale": (
                "Source-backed synthesis with claim audit. Cheap extraction, deep "
                "synthesis, balanced verification per the linked I-BOM model policy."
            ),
            "expected_output": "evidence_bundle",
            "validation": list(_VALIDATION_STEPS),
            "writebacks": [dict(w) for w in _WRITEBACKS],
        }
        dump_yaml(routing, run.routing_decision)
        _validate_or_raise(routing, "routing_decision", run.routing_decision)

        # --- governance preflight (enforcement gate) -----------------------------
        # Run AFTER the routing decision is written so the guard sees the planned
        # routing. The effective key profile defaults to the intent's allowed
        # profile (so a normal personal run is never over-blocked); a caller passing
        # a conflicting profile (e.g. work_approved on a personal-only intent) is
        # hard-blocked here per rule no_work_keys_for_personal_runs.
        intent_gov = intent.get("governance") if isinstance(intent.get("governance"), dict) else {}
        allowed_profile = intent_gov.get("key_profile_allowed") if isinstance(intent_gov, dict) else None
        effective_profile = profile or (str(allowed_profile) if allowed_profile else "personal")
        guard = governance_svc.preflight(intent, ibom, routing, effective_profile, paths=paths)
        if not guard.passed and guard.exit_code == int(ExitCode.GOVERNANCE):
            blocked = [v.rule_id for v in guard.violations if v.severity == "block"]
            raise GovernanceError(
                "governance preflight blocked planning for "
                f"{run_id} (profile={effective_profile}): {', '.join(blocked)}",
                violations=blocked,
            )

        # --- run.yaml ------------------------------------------------------------
        run_doc: dict[str, Any] = {
            "schema_version": 0.1,
            "type": "run",
            "run_id": run_id,
            "intent_id": intent_id,
            "ibom_id": ibom.get("id") if isinstance(ibom, dict) else None,
            "brief_id": b_id,
            "swarm_id": s_id,
            "routing_id": r_id,
            "created_at": created_at,
            "status": "planned",
            "sensitivity": sensitivity,
            "human_required": human_required,
            "project": effective_project,
            "notebook_id": None,
            # --- new metadata fields (P3 creation path; backfill in P2) ----------
            # linked_projects: list of project slugs this run is associated with.
            "linked_projects": _linked_projects,
            # category: pillar / thematic grouping derived from backlog idea.
            "category": _category,
            # tags: union of backlog idea tags; null when no backlog link.
            "tags": _tags,
            # backlog_idea_ref: RIB-NNN backlog reference slug (null if no link).
            "backlog_idea_ref": _backlog_idea_ref,
            # backlog_idea_id: stable idea id slug (null if no link).
            "backlog_idea_id": _backlog_idea_id,
            # ---------------------------------------------------------------------
            "profile": {
                "depth": depth,
                "audience": audience,
                "max_cost_usd": float(max_cost_usd),
                "max_runtime_minutes": int(max_runtime_minutes),
                "freshness_days": int(freshness_days),
                "extraction_model_profile": policy["extraction_profile"],
                "synthesis_model_profile": policy["synthesis_profile"],
                "verification_model_profile": policy["verification_profile"],
            },
        }
        dump_yaml(run_doc, run.run_yaml)

        # --- registry + telemetry ------------------------------------------------
        Registry.open(RUN_INDEX, paths=paths).upsert(
            {
                "id": run_id,
                "intent_id": intent_id,
                "status": "planned",
                "created_at": created_at,
                "brief_id": b_id,
                "swarm_id": s_id,
                "routing_id": r_id,
                "human_required": human_required,
                "run_dir": str(run.run),
                # Metadata fields — kept in sync with run.yaml (single-writer consistency).
                "linked_projects": _linked_projects,
                "category": _category,
                "tags": _tags,
                "backlog_idea_ref": _backlog_idea_ref,
                "backlog_idea_id": _backlog_idea_id,
            }
        )
    except Exception:
        # The run dir was just created by ensure_scaffold() above (disambiguate_id
        # confirmed no directory existed at this run_id before this call), and
        # nothing durable (run.yaml, registry entry) is written until the very end
        # of this block -- GC the partial scaffold on ANY failure in between so it
        # never surfaces as a blank/orphaned stub dir in the runs-viewer (AAR gap 3).
        _gc_partial_run_dir(run)
        raise

    # Record project→run association in the NotebookLM correlation registry.
    # notebook_id=None because no notebook exists yet; this is a pure local
    # registration that never touches the network.
    try:
        from . import notebook_correlation as _nb_corr

        _nb_corr.record_run_notebook(
            run_id,
            notebook_id="",
            project=effective_project,
            paths=paths,
        )
    except Exception:  # noqa: BLE001 — fail-soft; never block planning
        pass

    _trace(run, {"stage": "plan", "ts": created_at, "run_id": run_id})

    return PlanResult(
        run_id=run_id,
        brief_id=b_id,
        swarm_id=s_id,
        routing_id=r_id,
        run_dir=run.run,
        brief_path=run.research_brief,
        swarm_path=run.swarm_plan,
        routing_path=run.routing_decision,
    )


def _validate_or_raise(obj: dict[str, Any], schema_name: str, path: Path) -> None:
    """Validate ``obj`` against ``schema_name``; raise SchemaError on failure.

    Skips silently when the schema file is absent (per the §0 convention).
    """

    if not default_registry().has(schema_name):
        return
    result = validate(obj, schema_name)
    if not result.ok:
        raise SchemaError(
            f"{schema_name} validation failed for {path}: " + "; ".join(result.errors)
        )


def _trace(run: Any, record: dict[str, Any]) -> None:
    """Best-effort run-trace append; never fail the stage on trace error."""

    try:
        append_jsonl(record, run.run_trace)
    except Exception:  # pragma: no cover - trace is best-effort
        pass


__all__ = ["PlanResult", "plan_run", "load_intent"]
