"""Planning service — ``rf plan``.

Turns a research intent (+ its I-BOM) into a planned run: a run directory
containing ``run.yaml``, ``research_brief.md``, ``swarm_plan.yaml``, and
``routing_decision.yaml``. The default path is fully deterministic — no network
or API keys — sourcing model profiles from the linked I-BOM's ``model_policy``,
tools from the enabled entries in ``config/tools.yaml``, and the budget from the
caller's arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..errors import NotFoundError, SchemaError
from ..frontmatter import dump_md
from ..ids import (
    brief_id,
    now_iso,
    routing_id,
    slugify,
    swarm_id,
)
from ..ids import (
    run_id as make_run_id,
)
from ..paths import FoundryPaths
from ..registry import RUN_INDEX, Registry
from ..schemas import default_registry, validate
from ..yamlio import append_jsonl, dump_yaml, load_yaml

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


def plan_run(
    intent_id: str,
    *,
    depth: str = "standard",
    audience: str = "technical",
    max_cost_usd: float = 5.0,
    max_runtime_minutes: int = 60,
    freshness_days: int = 180,
    paths: FoundryPaths | None = None,
) -> PlanResult:
    """Plan a research run for ``intent_id``.

    Loads the intent and its linked I-BOM, mints a run id, scaffolds the run
    directory, and writes ``run.yaml``, ``research_brief.md``,
    ``swarm_plan.yaml``, and ``routing_decision.yaml``. The brief, swarm plan,
    and routing decision are validated against their schemas. The run is
    recorded in ``registries/run_index.yaml``.
    """

    paths = paths or FoundryPaths.discover()
    config = FoundryConfig(paths=paths)

    intent = load_intent(intent_id, paths=paths)
    ibom = _load_ibom(intent, paths)
    policy = _model_policy(ibom)

    title = str(intent.get("title") or intent_id)
    intent_slug = slugify(title)
    run_id = make_run_id(intent_slug)
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
        }
    )
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
