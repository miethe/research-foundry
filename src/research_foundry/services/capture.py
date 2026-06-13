"""Capture + triage services (spec §6.2–6.5; contract §1).

``capture_idea`` writes a ``raw_idea`` artifact into ``inbox/raw_ideas/``. ``triage_idea``
deterministically derives three linked artifacts from a captured idea — a
``research_intent``, an ``ibom``, and an ``intenttree_node`` — and marks the raw idea
converted. Everything here is deterministic: no network, no API keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import FoundryConfig
from ..errors import NotFoundError, SchemaError
from ..frontmatter import dump_md, load_md
from ..ids import (
    disambiguate_id,
    now_iso,
)
from ..ids import (
    ibom_id as make_ibom_id,
)
from ..ids import (
    intent_id as make_intent_id,
)
from ..ids import (
    raw_idea_id as make_raw_idea_id,
)
from ..ids import (
    tree_node_id as make_tree_node_id,
)
from ..paths import FoundryPaths
from ..schemas import default_registry, validate
from ..yamlio import append_jsonl, dump_yaml, load_yaml

# Defaults pulled from spec §6.3–6.5 so the deterministic path needs no config.
_DEFAULT_TOOLS_AVAILABLE = [
    "claude_code",
    "claude_agent_sdk",
    "opencode",
    "gpt_researcher",
    "paperqa2",
    "litellm",
]
_DEFAULT_MODEL_POLICY = {
    "extraction_profile": "rf_extract_cheap",
    "synthesis_profile": "rf_synthesize_deep",
    "verification_profile": "rf_verify_balanced",
}
_DEFAULT_SECURITY_BOUNDARIES = [
    "Do not mix personal and work-provided API keys in one run.",
    "Do not send work-sensitive source content to non-approved providers.",
]
_DEFAULT_ALLOWED_WRITEBACKS = [
    "meatywiki_personal",
    "skillmeat_personal",
    "ccdash_local",
]
_DEFAULT_POSTURES = ["researcher", "critic", "synthesizer"]
_DEFAULT_EXPECTED_ARTIFACTS = [
    "evidence_bundle",
    "report",
    "meatywiki_writeback",
    "ccdash_event",
]
# Sensitivities that always require a human in the loop (spec §6.3 governance).
_REVIEW_SENSITIVITIES = {"work_sensitive", "client_sensitive"}
_PERSONAL_KEY_SENSITIVITIES = {"public", "personal"}


# --- Capture ---------------------------------------------------------------


@dataclass(frozen=True)
class CaptureResult:
    """Outcome of :func:`capture_idea`."""

    raw_idea_id: str
    path: Path
    data: dict


def _default_title(text: str) -> str:
    """First ~8 words of ``text`` (spec: title defaults from the idea body)."""

    words = (text or "").split()
    title = " ".join(words[:8]).strip()
    return title or "Untitled idea"


def _trace(paths: FoundryPaths, record: dict) -> None:
    """Append a best-effort pre-run trace line; never fail the stage on error.

    Capture and triage happen *before* a run exists, so there is no per-run
    ``runs/<run>/telemetry/`` to write to. The pre-run trace goes to a gitignored
    workspace cache rather than polluting the committed tree.
    """

    try:
        append_jsonl({**record, "ts": now_iso()}, paths.root / ".rf_cache" / "capture_trace.jsonl")
    except Exception:  # pragma: no cover - tracing is best-effort
        pass


def _validate_or_raise(obj: dict, schema_name: str) -> None:
    """Validate ``obj`` vs schema; raise :class:`SchemaError` on failure.

    Skips silently when the schema file is absent (per contract §0).
    """

    if not default_registry().has(schema_name):
        return
    result = validate(obj, schema_name)
    if not result.ok:
        raise SchemaError(f"{schema_name} validation failed: " + "; ".join(result.errors))


def capture_idea(
    text: str,
    *,
    title: str | None = None,
    captured_from: str = "manual",
    sensitivity: str = "personal",
    urgency: str = "medium",
    tags: list[str] | None = None,
    research_potential: str = "unknown",
    suggested_project: str = "Research Foundry",
    attachments: list[dict] | None = None,
    paths: FoundryPaths | None = None,
) -> CaptureResult:
    """Capture raw idea ``text`` into ``inbox/raw_ideas/<raw_id>.md``.

    Fields are stored at the TOP LEVEL of the Markdown front matter plus a body.
    Validates the result against the ``raw_idea`` schema.

    Parameters
    ----------
    attachments:
        Optional list of attachment dicts (``path_or_uri``, ``type``, …) that
        are embedded into the raw-idea front matter verbatim. Useful when the
        idea originates from a system that already carries source links (e.g.
        IntentTree nodes with ``links`` / ``artifacts``).
    """

    paths = paths or FoundryPaths.discover()
    title = title or _default_title(text)
    raw_id = make_raw_idea_id(title)

    data: dict = {
        "id": raw_id,
        "created_at": now_iso(),
        "captured_from": captured_from,
        "title": title,
        "body": text or "",
        "tags": list(tags or []),
        "sensitivity": sensitivity,
        "urgency": urgency,
        "research_potential": research_potential,
        "suggested_project": suggested_project,
        "initial_questions": [],
        "attachments": list(attachments or []),
        "triage": {"status": "untriaged", "intent_id": None},
    }

    body = _render_body(text, title)
    out = paths.raw_ideas / f"{raw_id}.md"
    dump_md(data, body, out)

    _validate_or_raise(data, "raw_idea")
    _trace(paths, {"stage": "capture", "raw_idea_id": raw_id})
    return CaptureResult(raw_idea_id=raw_id, path=out, data=data)


def _render_body(text: str, title: str) -> str:
    """Render the raw-idea Markdown body, using templates/raw_idea.md when present.

    The template is keyed for human authoring; here we only borrow its section
    layout so on-disk files match. Front-matter substitution is done by
    ``dump_md`` re-serializing the metadata dict, so the template's front matter
    is ignored — only the body skeleton is reused.
    """

    return f"# {title}\n\n## Body\n\n{text or ''}\n\n## Initial questions\n"


# --- Triage ----------------------------------------------------------------


@dataclass(frozen=True)
class TriageResult:
    """Outcome of :func:`triage_idea` — up to three linked artifacts."""

    raw_idea_id: str
    intent_id: str | None
    ibom_id: str | None
    node_id: str | None
    intent_path: Path | None
    ibom_path: Path | None
    node_path: Path | None


def _resolve_raw_idea(raw_idea_ref: str | Path, paths: FoundryPaths) -> Path:
    """Resolve a raw-idea path from a path-like or a raw_idea_id."""

    ref = Path(raw_idea_ref)
    if ref.exists() and ref.is_file():
        return ref
    # Treat the ref as an id; look it up under inbox/raw_ideas/.
    candidate = paths.raw_ideas / f"{raw_idea_ref}.md"
    if candidate.exists():
        return candidate
    raise NotFoundError(f"raw_idea not found: {raw_idea_ref}")


def _governance_from_sensitivity(sensitivity: str) -> dict:
    """Derive the intent governance block from the idea sensitivity (spec §6.3)."""

    key_profile = "personal" if sensitivity in _PERSONAL_KEY_SENSITIVITIES else "work_approved"
    return {
        "sensitivity": sensitivity,
        "key_profile_allowed": key_profile,
        "requires_human_review": sensitivity in _REVIEW_SENSITIVITIES,
        "allowed_writebacks": list(_DEFAULT_ALLOWED_WRITEBACKS),
    }


def triage_idea(
    raw_idea_ref: str | Path,
    *,
    create_intent: bool = True,
    create_ibom: bool = True,
    create_tree_node: bool = True,
    paths: FoundryPaths | None = None,
) -> TriageResult:
    """Deterministically derive intent/ibom/node from a captured raw idea.

    Links: ``intent.ibom_ref == ibom.id``, ``intent.intenttree_node_ref == node.id``,
    ``node.intent_id == intent.id``. Marks the raw idea ``converted_to_intent``.
    """

    paths = paths or FoundryPaths.discover()
    idea_path = _resolve_raw_idea(raw_idea_ref, paths)
    meta, body = load_md(idea_path)

    raw_idea_id = str(meta.get("id") or idea_path.stem)
    title = str(meta.get("title") or _default_title(str(meta.get("body") or body)))
    sensitivity = str(meta.get("sensitivity") or "personal")
    idea_body = str(meta.get("body") or body or "").strip()
    initial_questions = [q for q in (meta.get("initial_questions") or []) if q]

    # Disambiguate on actual collision only: two distinct ideas whose first-6-word
    # slugs match would otherwise mint identical ids and silently overwrite each
    # other. The raw_idea_id seeds a stable per-idea suffix shared across the three
    # linked artifacts so they remain consistent.
    intent_id = (
        disambiguate_id(
            make_intent_id(title),
            seed=raw_idea_id,
            exists=lambda i: (paths.intents_active / f"{i}.yaml").exists(),
        )
        if create_intent
        else None
    )
    ibom_id = (
        disambiguate_id(
            make_ibom_id(title),
            seed=raw_idea_id,
            exists=lambda i: (paths.iboms_active / f"{i}.yaml").exists(),
        )
        if (create_intent and create_ibom)
        else None
    )
    node_id = (
        disambiguate_id(
            make_tree_node_id(title),
            seed=raw_idea_id,
            exists=lambda i: (paths.intenttree_nodes / f"{i}.yaml").exists(),
        )
        if (create_intent and create_tree_node)
        else None
    )

    intent_path: Path | None = None
    ibom_path: Path | None = None
    node_path: Path | None = None

    if create_intent:
        intent = _build_intent(
            intent_id=intent_id,  # type: ignore[arg-type]
            title=title,
            objective=idea_body or title,
            sensitivity=sensitivity,
            initial_questions=initial_questions,
            ibom_id=ibom_id,
            node_id=node_id,
            raw_idea_id=raw_idea_id,
            paths=paths,
        )
        if ibom_id is not None:
            ibom = _build_ibom(ibom_id=ibom_id, intent_id=intent_id, title=title)  # type: ignore[arg-type]
            ibom_path = paths.iboms_active / f"{ibom_id}.yaml"
            dump_yaml(ibom, ibom_path)
            _validate_or_raise(ibom, "ibom")

        if node_id is not None:
            node = _build_node(node_id=node_id, intent_id=intent_id, title=title)  # type: ignore[arg-type]
            node_path = paths.intenttree_nodes / f"{node_id}.yaml"
            dump_yaml(node, node_path)
            _validate_or_raise(node, "intenttree_node")

        intent_path = paths.intents_active / f"{intent_id}.yaml"
        dump_yaml(intent, intent_path)
        _validate_or_raise(intent, "research_intent")

        # Mark the raw idea converted (top-level triage block).
        meta["triage"] = {"status": "converted_to_intent", "intent_id": intent_id}
        dump_md(meta, body, idea_path)
        _validate_or_raise(meta, "raw_idea")

    _trace(
        paths,
        {
            "stage": "triage",
            "raw_idea_id": str(meta.get("id") or idea_path.stem),
            "intent_id": intent_id,
            "ibom_id": ibom_id,
            "node_id": node_id,
        },
    )

    return TriageResult(
        raw_idea_id=str(meta.get("id") or idea_path.stem),
        intent_id=intent_id,
        ibom_id=ibom_id,
        node_id=node_id,
        intent_path=intent_path,
        ibom_path=ibom_path,
        node_path=node_path,
    )


def _build_intent(
    *,
    intent_id: str,
    title: str,
    objective: str,
    sensitivity: str,
    initial_questions: list[str],
    ibom_id: str | None,
    node_id: str | None,
    raw_idea_id: str,
    paths: FoundryPaths,
) -> dict:
    """Assemble a ``research_intent`` dict (top-level fields, spec §6.3).

    Records the originating ``raw_idea_id`` so the idea->intent->bundle lineage
    can be traced (``research_intent`` schema is additionalProperties:true).
    """

    cfg = FoundryConfig(paths=paths)
    primary = list(initial_questions) or [f"What does the evidence say about {title}?"]

    intent: dict = {
        "id": intent_id,
        "title": title,
        "owner": cfg.owner,
        "created_at": now_iso(),
        "status": "active",
        "type": "research",
        "raw_idea_ids": [raw_idea_id] if raw_idea_id else [],
        "objective": objective,
        "motivation": "",
        "desired_output": {
            "artifact_type": "report",
            "audience": "technical",
            "depth": "standard",
        },
        "scope": {"in": [], "out": []},
        "research_questions": {"primary": primary, "secondary": []},
        "constraints": {
            "hard": [
                "Every material claim must map to source_card_id or be labeled "
                "inference/speculation."
            ],
            "soft": [],
        },
        "success_criteria": [],
        "governance": _governance_from_sensitivity(sensitivity),
    }
    if ibom_id is not None:
        intent["ibom_ref"] = ibom_id
    if node_id is not None:
        intent["intenttree_node_ref"] = node_id
    return intent


def _build_ibom(*, ibom_id: str, intent_id: str, title: str) -> dict:
    """Assemble an ``ibom`` dict linked to ``intent_id`` (spec §6.4)."""

    return {
        "id": ibom_id,
        "intent_id": intent_id,
        "created_at": now_iso(),
        "snapshot_status": "draft",
        "context_snapshot": f"Initial I-BOM for: {title}",
        "sources_seeded": [],
        "assumptions": [],
        "known_constraints": [],
        "tools_available": list(_DEFAULT_TOOLS_AVAILABLE),
        "model_policy": dict(_DEFAULT_MODEL_POLICY),
        "relevant_memory": [],
        "open_questions": [],
        "security_boundaries": list(_DEFAULT_SECURITY_BOUNDARIES),
    }


def _build_node(*, node_id: str, intent_id: str, title: str) -> dict:
    """Assemble an ``intenttree_node`` dict linked to ``intent_id`` (spec §6.5)."""

    return {
        "node_id": node_id,
        "level": "L4",
        "title": title,
        "parent": "tree_research_foundry",
        "intent_id": intent_id,
        "status": "ready",
        "priority": "medium",
        "dependencies": [],
        "blockers": [],
        "required_agent_postures": list(_DEFAULT_POSTURES),
        "required_skill_stack": ["skill_research_swarm_v0"],
        "required_context": [],
        "expected_artifacts": list(_DEFAULT_EXPECTED_ARTIFACTS),
        "success_criteria": [
            "Claim verifier passes.",
            "Evidence bundle generated.",
            "At least one writeback candidate generated.",
        ],
        "reusable_output_candidates": [],
    }


# --- Helpers ---------------------------------------------------------------


def load_intent(intent_id: str, paths: FoundryPaths | None = None) -> dict:
    """Load a research intent by id from ``intents/active/``.

    Raises :class:`NotFoundError` when the intent file does not exist.
    """

    paths = paths or FoundryPaths.discover()
    candidate = paths.intents_active / f"{intent_id}.yaml"
    if not candidate.exists():
        raise NotFoundError(f"intent not found: {intent_id}")
    data = load_yaml(candidate)
    if not isinstance(data, dict):
        raise NotFoundError(f"intent file malformed: {candidate}")
    return data


__all__ = [
    "CaptureResult",
    "capture_idea",
    "TriageResult",
    "triage_idea",
    "load_intent",
]
