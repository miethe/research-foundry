"""Deterministic run export service (runs-frontend Phase 1).

Joins a run's on-disk claim graph into a single denormalized ``run.json`` — the
sole data contract consumed by the read-only runs viewer. The service is
deterministic: no LLM, no network, no clock dependence beyond what is already on
disk.

Hard invariants (see ``docs/dev/architecture/rf-run-export-schema.md``):

* **Path re-derivation** — every file is located via :class:`FoundryPaths` /
  :class:`RunPaths`. Stored absolute paths in ``run_index.yaml`` and
  ``verification.yaml`` (``report_path``, ``claim_ledger_path``, ``run_dir``)
  are NEVER used for file I/O; they would break on any workspace move.
* **Sensitivity redaction at the export layer** — quote/summary text whose
  effective sensitivity exceeds the configured viewer threshold never reaches
  the JSON. No frontend component can leak what the export never emits (R9).
* **Derived status** — the effective status is computed from artifact presence
  + verification, not from the (frequently stale) ``run.yaml.status`` field.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..errors import ExitCode, RFError
from ..frontmatter import split_frontmatter
from ..paths import FoundryPaths, RunPaths
from ..yamlio import loads_yaml

EXPORT_SCHEMA_VERSION = "1.3"

# --- sensitivity model -------------------------------------------------------
# Ordering: lower index = less sensitive. The viewer threshold names the MOST
# sensitive level that is allowed through; anything stricter is redacted.
SENSITIVITY_ORDER: dict[str, int] = {
    "public": 0,
    "personal": 1,
    "work_sensitive": 2,
    "client_sensitive": 3,
}
DEFAULT_THRESHOLD = "public"
# Unrecognized sensitivity values are treated as stricter than every known
# threshold so an unknown label can never leak (fail-closed).
_UNKNOWN_SENSITIVITY = len(SENSITIVITY_ORDER)
REDACTION_MARKER = "[redacted:sensitivity]"

# --- derived-status ladder (OQ-2) -------------------------------------------
# Highest reached rung wins. Computed from on-disk artifacts + verification.
STATUS_LADDER = [
    "planned",
    "sources_ingested",
    "extracted",
    "claim_mapped",
    "synthesized",
    "verified",
    "published",
]

_CLAIM_TAG_RE = re.compile(r"\[claim:(clm_[A-Za-z0-9]+)\]")


class ExportError(RFError):
    """A run could not be exported (missing run, malformed artifact, ...)."""

    exit_code = ExitCode.SCHEMA

    def __init__(
        self,
        message: str,
        *,
        run_id: str | None = None,
        artifact_path: str | Path | None = None,
        exit_code: ExitCode | None = None,
    ) -> None:
        super().__init__(message, exit_code=exit_code or ExitCode.SCHEMA)
        self.run_id = run_id
        self.artifact_path = str(artifact_path) if artifact_path is not None else None

    def as_payload(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "run_id": self.run_id,
            "artifact_path": self.artifact_path,
        }


# --- low-level safe readers (all via Path; never via stored path fields) -----
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_yaml_file(path: Path, *, run_id: str | None) -> Any:
    """Parse a YAML file, raising :class:`ExportError` on malformed content."""

    try:
        return loads_yaml(_read_text(path))
    except FileNotFoundError:
        return None
    except Exception as exc:  # noqa: BLE001 — surface as structured export error
        raise ExportError(
            f"malformed YAML artifact: {exc}", run_id=run_id, artifact_path=path
        ) from exc


def _load_yaml_dict(path: Path, *, run_id: str | None) -> dict[str, Any]:
    data = _load_yaml_file(path, run_id=run_id)
    return data if isinstance(data, dict) else {}


def _has_files(directory: Path, pattern: str = "*") -> bool:
    return directory.is_dir() and any(directory.glob(pattern))


def _sensitivity_rank(value: Any) -> int:
    if value is None:
        return SENSITIVITY_ORDER[DEFAULT_THRESHOLD]
    return SENSITIVITY_ORDER.get(str(value), _UNKNOWN_SENSITIVITY)


# --- threshold resolution (OQ-3) --------------------------------------------
def resolve_threshold(paths: FoundryPaths, override: str | None = None) -> str:
    """Resolve the active sensitivity threshold.

    Precedence: explicit ``override`` > ``foundry.yaml`` ``viewer
    .sensitivity_threshold`` > :data:`DEFAULT_THRESHOLD` (``public``).

    Raises :class:`ExportError` when the resolved label is not a member of
    :data:`SENSITIVITY_ORDER` (fail-closed: a bogus threshold silently
    treating all content as unredacted is a governance failure).
    """

    if override:
        label = override
    else:
        try:
            viewer = FoundryConfig(paths=paths).viewer
        except Exception:  # noqa: BLE001 — config is advisory; default is safe
            viewer = {}
        candidate = viewer.get("sensitivity_threshold") if isinstance(viewer, dict) else None
        label = str(candidate) if candidate else DEFAULT_THRESHOLD
    if label not in SENSITIVITY_ORDER:
        valid = ", ".join(sorted(SENSITIVITY_ORDER, key=SENSITIVITY_ORDER.__getitem__))
        raise ExportError(
            f"unknown sensitivity threshold {label!r}; valid values: {valid}"
        )
    return label


# --- run resolution (recursive, path-derived) -------------------------------
def discover_run_yamls(runs_root: Path, max_depth: int = 3) -> list[Path]:
    """Find every ``run.yaml`` under ``runs_root`` to depth ``max_depth``.

    Depth is measured from ``runs_root`` so the nested ``runs/runs/<id>/``
    anomaly (depth 2) is still discovered, while deep/unrelated trees are not.
    """

    if not runs_root.is_dir():
        return []
    base = len(runs_root.parts)
    found: list[Path] = []
    for candidate in runs_root.rglob("run.yaml"):
        depth = len(candidate.parent.parts) - base
        if 1 <= depth <= max_depth:
            found.append(candidate)
    return sorted(found)


def resolve_run_paths(paths: FoundryPaths, run_id: str) -> RunPaths:
    """Resolve a :class:`RunPaths` for ``run_id`` by path derivation only."""

    direct = paths.run_dir(run_id)
    if (direct / "run.yaml").exists():
        return RunPaths(run=direct)
    for run_yaml in discover_run_yamls(paths.runs):
        run_dir = run_yaml.parent
        if run_dir.name == run_id:
            return RunPaths(run=run_dir)
        data = _load_yaml_dict(run_yaml, run_id=run_id)
        if str(data.get("run_id") or "") == run_id:
            return RunPaths(run=run_dir)
    raise ExportError(
        f"run not found: {run_id}", run_id=run_id, exit_code=ExitCode.USAGE
    )


# --- derived status ----------------------------------------------------------
def derive_status(rp: RunPaths, *, run_id: str | None = None) -> str:
    """Compute the effective status from artifacts, never ``run.yaml.status``."""

    status = "planned"
    if _has_files(rp.sources, "*.md"):
        status = "sources_ingested"
    if _has_files(rp.extractions, "*.yaml") or _has_files(rp.extractions, "*.md"):
        status = "extracted"
    ledger = _load_yaml_dict(rp.claim_ledger, run_id=run_id)
    if ledger.get("claims"):
        status = "claim_mapped"
    if rp.report_draft.exists() or rp.report_final.exists():
        status = "synthesized"
    verification = _load_yaml_dict(rp.verification, run_id=run_id)
    if verification.get("passed") is True:
        status = "verified"
    if status == "verified":
        bundle = _load_yaml_dict(rp.evidence_bundle, run_id=run_id)
        approved = bool((bundle.get("governance") or {}).get("approved_for_writeback"))
        if approved or _has_files(rp.writebacks, "*"):
            status = "published"
    return status


# --- source-card loading + claim-graph join ---------------------------------
def _load_source_cards(rp: RunPaths, *, run_id: str | None) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    if not rp.sources.is_dir():
        return cards
    for path in sorted(rp.sources.glob("*.md")):
        try:
            meta, body = split_frontmatter(_read_text(path))
        except Exception as exc:  # noqa: BLE001
            raise ExportError(
                f"malformed source card: {exc}", run_id=run_id, artifact_path=path
            ) from exc
        sid = str(meta.get("source_card_id") or path.stem)
        points = {
            str(p.get("evidence_id")): p
            for p in (meta.get("extracted_points") or [])
            if isinstance(p, dict) and p.get("evidence_id")
        }
        cards[sid] = {"meta": meta, "points": points, "body": body, "path": path}
    return cards


def _resolve_source(
    citation: dict[str, Any],
    cards: dict[str, dict[str, Any]],
    threshold_rank: int,
) -> dict[str, Any]:
    sid = str(citation.get("source_card_id") or "")
    eid = citation.get("evidence_id")
    card = cards.get(sid)
    resolved: dict[str, Any] = {
        "source_card_id": sid,
        "evidence_id": eid,
        "relation": citation.get("relation"),
        "locator": citation.get("locator"),
        "resolved": card is not None,
    }
    if card is None:
        # Dangling reference — surfaced honestly, not silently dropped.
        resolved.update(
            {
                "title": None,
                "source_type": None,
                "url": None,
                "trust": None,
                "usage": None,
                "sensitivity": None,
                "evidence_locator": None,
                "summary": None,
                "quote": None,
                "redacted": False,
                "dangling": True,
            }
        )
        return resolved

    meta = card["meta"]
    src = meta.get("source") or {}
    locator = src.get("locator") or {}
    point = card["points"].get(str(eid)) if eid is not None else None
    card_rank = _sensitivity_rank(meta.get("sensitivity"))
    point_rank = _sensitivity_rank((point or {}).get("sensitivity")) if point else card_rank
    effective_rank = max(card_rank, point_rank)
    redacted = effective_rank > threshold_rank

    quote = (point or {}).get("quote")
    summary = (point or {}).get("summary")
    resolved.update(
        {
            "title": src.get("title"),
            "source_type": src.get("source_type"),
            "url": locator.get("url") if isinstance(locator, dict) else None,
            "trust": meta.get("trust"),
            "usage": meta.get("usage"),
            "sensitivity": meta.get("sensitivity"),
            "evidence_locator": (point or {}).get("locator"),
            "summary": REDACTION_MARKER if redacted else summary,
            "quote": REDACTION_MARKER if redacted else quote,
            "redacted": redacted,
            "dangling": False,
        }
    )
    return resolved


def _build_claims(
    ledger: dict[str, Any],
    cards: dict[str, dict[str, Any]],
    threshold_rank: int,
) -> list[dict[str, Any]]:
    claims_out: list[dict[str, Any]] = []
    for claim in ledger.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        sources = [
            _resolve_source(c, cards, threshold_rank)
            for c in (claim.get("sources") or [])
            if isinstance(c, dict)
        ]
        basis = claim.get("inference_basis") or {}
        claims_out.append(
            {
                "claim_id": claim.get("claim_id"),
                "text": claim.get("text"),
                "materiality": claim.get("materiality"),
                "claim_type": claim.get("claim_type"),
                "status": claim.get("status"),
                "confidence": claim.get("confidence"),
                "report_locations": claim.get("report_locations") or [],
                "inference_basis": {
                    "from_claims": basis.get("from_claims") or [],
                    "reasoning_summary": basis.get("reasoning_summary"),
                },
                "sources": sources,
            }
        )
    return claims_out


def _claim_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {"total": len(claims)}
    for claim in claims:
        key = str(claim.get("status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _source_count_by_type(cards: dict[str, dict[str, Any]]) -> dict[str, int] | None:
    """Aggregate source counts by source_type from the loaded source cards.

    Returns None (not an empty dict) when no source cards are present, so the
    FE can cleanly distinguish "run has no sources" from "run has sources of
    unknown type".
    """
    if not cards:
        return None
    counts: dict[str, int] = {}
    for card_data in cards.values():
        src_type = (card_data.get("meta") or {}).get("source", {}).get("source_type")
        if src_type:
            key = str(src_type)
            counts[key] = counts.get(key, 0) + 1
        else:
            counts["other"] = counts.get("other", 0) + 1
    return counts if counts else None


def _cost_and_model_profiles(
    run_meta: dict[str, Any],
) -> tuple[float | None, dict[str, Any] | None]:
    """Extract cost_usd and model_profiles from run.yaml.profile.

    Returns (cost_usd, model_profiles) — either or both may be None when the
    profile block is absent (pre-enrichment runs).
    """
    profile = run_meta.get("profile")
    if not isinstance(profile, dict):
        return None, None

    cost_usd: float | None = None
    raw_cost = profile.get("max_cost_usd")
    if raw_cost is not None:
        try:
            cost_usd = float(raw_cost)
        except (TypeError, ValueError):
            cost_usd = None

    model_profiles: dict[str, Any] = {}
    for key in (
        "max_cost_usd",
        "extraction_model_profile",
        "synthesis_model_profile",
        "verification_model_profile",
        "max_runtime_minutes",
        "freshness_days",
    ):
        val = profile.get(key)
        if val is not None:
            model_profiles[key] = val

    return cost_usd, model_profiles if model_profiles else None


_ROUTING_DECISION_ALLOWLIST: frozenset[str] = frozenset(
    {
        "selected_abstraction_level",
        "rationale",
        "human_required",
        "confidence",
        "abstraction_options",
        "recommended_agents",
        "routing_notes",
    }
)

_SWARM_PLAN_ALLOWLIST: frozenset[str] = frozenset(
    {
        "agents",
        "required_outputs",
        "parallel",
        "swarm_notes",
        "estimated_cost_usd",
        "estimated_runtime_minutes",
        "posture",
        "depth",
    }
)


def _redact_str_values(obj: Any) -> Any:
    """Recursively replace every string value in *obj* with :data:`REDACTION_MARKER`.

    Used by the context redaction pass (P2-003) to sanitize an entire
    ``routing_decision`` or ``swarm_plan`` sub-object when the source artifact's
    sensitivity label exceeds the active export threshold.  Non-string scalar
    values (booleans, numbers, None) are left untouched so structural metadata
    (e.g. ``human_required: false``) remains readable.
    """
    if isinstance(obj, str):
        return REDACTION_MARKER
    if isinstance(obj, dict):
        return {k: _redact_str_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_str_values(item) for item in obj]
    return obj


def _context_summary(
    rp: RunPaths,
    *,
    run_id: str | None,
    run_meta: dict[str, Any] | None = None,
    threshold_rank: int | None = None,
) -> dict[str, Any] | None:
    """Build the context summary block for schema v1.3.

    Reads routing_decision.yaml, swarm_plan.yaml, research_brief.md, and
    upstream entity IDs from *run_meta* (run.yaml fields).  Only explicitly
    allowlisted keys from the YAML artifacts are forwarded to prevent
    unanticipated key leakage (security invariant R9).

    Returns ``None`` when **none of the three file artifacts** exists
    (routing_decision.yaml, swarm_plan.yaml, research_brief.md absent
    simultaneously) — this preserves backward compat with pre-v2 runs that
    carry an ``intent_id`` in run.yaml but have no v2 planning artifacts.

    The returned dict **always** contains all four keys:
      - ``routing_decision``:  filtered routing-decision object or ``None``
      - ``swarm_plan``:        filtered swarm-plan object or ``None``
      - ``research_brief_md``: verbatim Markdown string or ``None``
      - ``upstream_entities``: ``{intent_id, ibom_id, intenttree_node_id}``
        dict when at least one ID is non-null, else ``None``

    *run_meta*
        The ``run.yaml`` dict already loaded by the caller.  When ``None`` the
        upstream entity IDs all default to ``None``.

    *threshold_rank*
        If supplied, a redaction pass is applied over ``routing_decision``,
        ``swarm_plan``, and ``research_brief_md`` before returning: string
        values in the two plan objects are replaced with :data:`REDACTION_MARKER`
        when the source artifact's ``sensitivity`` label exceeds the threshold;
        ``research_brief_md`` is replaced wholesale when its YAML frontmatter
        ``sensitivity`` label exceeds the threshold.
    """
    routing = _load_yaml_dict(rp.routing_decision, run_id=run_id)
    swarm = _load_yaml_dict(rp.swarm_plan, run_id=run_id)
    brief_exists = rp.research_brief.exists()

    # Null guard: only FILE artifacts determine whether context is emitted.
    # Upstream entity IDs in run.yaml alone do not constitute a v2 context
    # (preserves backward compat — pre-v2 runs always had intent_id).
    if not routing and not swarm and not brief_exists:
        return None

    ctx: dict[str, Any] = {}

    # --- routing_decision --------------------------------------------------
    if routing:
        ctx["routing_decision"] = {
            "decision": routing.get("selected_abstraction_level"),
            "rationale": routing.get("rationale"),
            **{k: routing[k] for k in _ROUTING_DECISION_ALLOWLIST
               if k in routing and k not in ("selected_abstraction_level", "rationale")},
        }
    else:
        ctx["routing_decision"] = None

    # --- swarm_plan --------------------------------------------------------
    if swarm:
        agents = swarm.get("agents")
        ctx["swarm_plan"] = {
            "swarm": swarm.get("id"),
            "agents": [a.get("role") for a in agents if isinstance(a, dict)]
            if isinstance(agents, list)
            else agents,
            "adapters": swarm.get("required_outputs"),
            **{k: swarm[k] for k in _SWARM_PLAN_ALLOWLIST
               if k in swarm and k not in ("agents", "required_outputs")},
        }
    else:
        ctx["swarm_plan"] = None

    # --- research_brief_md (P2-001) ----------------------------------------
    if brief_exists:
        try:
            ctx["research_brief_md"] = _read_text(rp.research_brief)
        except Exception as exc:  # noqa: BLE001
            print(
                json.dumps({"error": f"research_brief read failed: {exc}", "run_id": run_id}),
                file=sys.stderr,
            )
            ctx["research_brief_md"] = None
    else:
        ctx["research_brief_md"] = None

    # --- upstream_entities (P2-001) ----------------------------------------
    _run_meta: dict[str, Any] = run_meta or {}
    intent_id: str | None = _run_meta.get("intent_id")
    ibom_id: str | None = _run_meta.get("ibom_id")

    # intenttree_node_id: prefer routing_decision.yaml active_node_id;
    # fall back to evidence_bundle.yaml governance block.
    intenttree_node_id: str | None = routing.get("active_node_id") if routing else None
    if intenttree_node_id is None:
        try:
            bundle = _load_yaml_dict(rp.evidence_bundle, run_id=run_id)
            intenttree_node_id = (bundle.get("governance") or {}).get("intenttree_node_id")
        except Exception:  # noqa: BLE001
            pass

    upstream: dict[str, Any] = {
        "intent_id": intent_id,
        "ibom_id": ibom_id,
        "intenttree_node_id": intenttree_node_id,
    }
    ctx["upstream_entities"] = (
        upstream if any(v is not None for v in upstream.values()) else None
    )

    # --- redaction pass over context block (P2-003) ------------------------
    if threshold_rank is not None:
        # routing_decision: redact string values when the source artifact's
        # sensitivity label exceeds the threshold.
        if ctx["routing_decision"] is not None:
            rd_rank = _sensitivity_rank(routing.get("sensitivity"))
            if rd_rank > threshold_rank:
                ctx["routing_decision"] = _redact_str_values(ctx["routing_decision"])

        # swarm_plan: same rule.
        if ctx["swarm_plan"] is not None:
            sp_rank = _sensitivity_rank(swarm.get("sensitivity"))
            if sp_rank > threshold_rank:
                ctx["swarm_plan"] = _redact_str_values(ctx["swarm_plan"])

        # research_brief_md: redact the whole string when the brief's YAML
        # frontmatter sensitivity label exceeds the threshold.
        if ctx["research_brief_md"] is not None:
            try:
                brief_meta, _ = split_frontmatter(ctx["research_brief_md"])
                brief_rank = _sensitivity_rank(brief_meta.get("sensitivity"))
                if brief_rank > threshold_rank:
                    ctx["research_brief_md"] = REDACTION_MARKER
            except Exception:  # noqa: BLE001
                pass

    return ctx


# --- title derivation --------------------------------------------------------

_FRONTMATTER_TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
_FRONTMATTER_FENCE_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n", re.DOTALL | re.MULTILINE)
_RUN_ID_PREFIX_RE = re.compile(r"^(rf_run|intent_research|intent)[_\-]?", re.IGNORECASE)
_DATESTAMP_RE = re.compile(r"^\d{8,}[_\-]?")


def _title_from_slug(value: str | None) -> str | None:
    """Humanize a run_id slug into a readable title (Python equivalent of FE titleFromSlug).

    Strips the ``rf_run_``, ``intent_``, and ``intent_research_`` prefixes, strips
    leading date-stamps (8+ digits), replaces underscores/hyphens with spaces, and
    title-cases the result.  Returns ``None`` when the input is empty/None or the
    normalized result is empty.
    """
    if not value:
        return None
    normalized = _RUN_ID_PREFIX_RE.sub("", value)
    normalized = _DATESTAMP_RE.sub("", normalized)
    normalized = normalized.replace("_", " ").replace("-", " ").strip()
    if not normalized:
        return value
    return " ".join(word.capitalize() for word in normalized.split())


def _extract_title_from_report_draft(report_draft: str | None) -> str | None:
    """Extract the YAML frontmatter ``title:`` value from a report draft Markdown string.

    Parses only the fenced YAML block at the top of the document (``--- ... ---``).
    Returns ``None`` if the frontmatter is absent, malformed, or has no ``title`` key.
    Never raises — all errors are swallowed and ``None`` is returned instead.
    """
    if not report_draft:
        return None
    try:
        fm_match = _FRONTMATTER_FENCE_RE.match(report_draft)
        if fm_match:
            fm_block = fm_match.group(1)
            title_match = _FRONTMATTER_TITLE_RE.search(fm_block)
            if title_match:
                candidate = title_match.group(1).strip().strip('"\'')
                return candidate if candidate else None
    except Exception:  # noqa: BLE001
        pass
    return None


def _derive_run_title(run_id: str, report_draft: str | None) -> str:
    """Derive a human-readable title for a run.

    Priority: frontmatter ``title:`` key → slug-humanized ``run_id``.
    Always returns a non-empty string.
    """
    return (
        _extract_title_from_report_draft(report_draft)
        or _title_from_slug(run_id)
        or run_id
    )


def _timeline(rp: RunPaths, *, run_id: str | None) -> list[dict[str, Any]]:
    if not rp.run_trace.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        for line in _read_text(rp.run_trace).splitlines():
            if line.strip():
                events.append(json.loads(line))
    except Exception as exc:  # noqa: BLE001
        raise ExportError(
            f"malformed run trace: {exc}", run_id=run_id, artifact_path=rp.run_trace
        ) from exc
    return events


def _verification_block(rp: RunPaths, *, run_id: str | None) -> dict[str, Any]:
    data = _load_yaml_dict(rp.verification, run_id=run_id)
    if not data:
        return {"present": False, "passed": None, "exit_code": None, "checks": []}
    checks = [
        {
            "id": c.get("id"),
            "severity": c.get("severity"),
            "status": c.get("status"),
            "detail": c.get("detail"),
            "locations": c.get("locations") or [],
        }
        for c in (data.get("checks") or [])
        if isinstance(c, dict)
    ]
    return {
        "present": True,
        "passed": data.get("passed"),
        "exit_code": data.get("exit_code"),
        "checks": checks,
    }


# --- top-level export --------------------------------------------------------
def export_run(
    paths: FoundryPaths,
    run_id: str,
    *,
    sensitivity_threshold: str | None = None,
) -> dict[str, Any]:
    """Build the denormalized ``run.json`` dict for ``run_id``.

    All reads are path-derived; sensitivity filtering is applied before return.
    """

    rp = resolve_run_paths(paths, run_id)
    threshold = resolve_threshold(paths, sensitivity_threshold)
    threshold_rank = _sensitivity_rank(threshold)

    run_meta = _load_yaml_dict(rp.run_yaml, run_id=run_id)
    bundle = _load_yaml_dict(rp.evidence_bundle, run_id=run_id)
    ledger = _load_yaml_dict(rp.claim_ledger, run_id=run_id)
    cards = _load_source_cards(rp, run_id=run_id)

    claims = _build_claims(ledger, cards, threshold_rank)
    governance = dict(bundle.get("governance") or {})
    # AC-4: thread allowed_writebacks and requires_human_review from run.yaml
    # governance block (not the evidence_bundle) so per-run governance policy
    # fields are visible in the viewer even for runs without a full bundle.
    run_gov = run_meta.get("governance") or {}
    if run_gov.get("allowed_writebacks") is not None:
        governance.setdefault("allowed_writebacks", run_gov["allowed_writebacks"])
    if run_gov.get("requires_human_review") is not None:
        governance.setdefault("requires_human_review", run_gov["requires_human_review"])
    sensitivity = (
        run_meta.get("sensitivity")
        or governance.get("sensitivity")
        or DEFAULT_THRESHOLD
    )

    schema_versions = {
        "run": run_meta.get("schema_version"),
        "evidence_bundle": bundle.get("schema_version"),
        "claim_ledger": ledger.get("schema_version"),
    }

    # --- metadata enrichment fields (schema 1.2) --------------------------------
    # Read from run.yaml directly; emit null (not key-omit) so FE can detect
    # cleanly between "old run (absent)" and "new run with no value (null)".
    linked_projects = run_meta.get("linked_projects") or None
    category = run_meta.get("category") or None
    tags = run_meta.get("tags") or None
    backlog_idea_ref = run_meta.get("backlog_idea_ref") or None
    backlog_idea_id = run_meta.get("backlog_idea_id") or None

    # --- enrichment-extra fields (ENR-001, ENR-002, ENR-003 — schema 1.2 P7) ----
    cost_usd, model_profiles = _cost_and_model_profiles(run_meta)
    source_count_by_type = _source_count_by_type(cards)
    context_summary = _context_summary(
        rp, run_id=run_id, run_meta=run_meta, threshold_rank=threshold_rank
    )

    # Read report_draft once; reuse for title derivation and export field.
    report_draft = _read_report_draft(rp)

    # ENR-004: writebacks emitted as null (no writeback files) or RFRunWritebacksSummary object.
    # Thread approved_for_writeback from the governance block into the summary so FE can
    # render the approval state without reading the bundle separately.
    writebacks = _collect_writebacks(rp)
    if writebacks is not None:
        approved = governance.get("approved_for_writeback")
        writebacks["approved_for_writeback"] = bool(approved) if approved is not None else None


    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "title": _derive_run_title(run_id, report_draft),
        "intent_id": run_meta.get("intent_id"),
        "created_at": run_meta.get("created_at"),
        "status_derived": derive_status(rp, run_id=run_id),
        "status_raw": run_meta.get("status"),
        "sensitivity": sensitivity,
        "sensitivity_threshold": threshold,
        "claim_counts": {
            **(bundle.get("counts") or {}),
            **_claim_counts(claims),
        },
        "verification": _verification_block(rp, run_id=run_id),
        "governance": governance,
        "timeline": _timeline(rp, run_id=run_id),
        "claims": claims,
        "artifact_schema_versions": schema_versions,
        "report_draft": report_draft,
        # Optional v2 context (ENR-003): routing_decision + swarm_plan; null on pre-v2 runs
        "context": context_summary,
        # Metadata enrichment (schema 1.2) — null for pre-migration runs
        "linked_projects": linked_projects,
        "category": category,
        "tags": tags,
        "backlog_idea_ref": backlog_idea_ref,
        "backlog_idea_id": backlog_idea_id,
        # Enrichment extras (P7 — ENR-001, ENR-002): null when profile / sources absent
        "cost_usd": cost_usd,
        "model_profiles": model_profiles,
        "source_count_by_type": source_count_by_type,
        # ENR-004: writeback artifacts; null when no writeback files present
        "writebacks": writebacks,
    }


def run_json_path(rp: RunPaths) -> Path:
    return rp.run / "run.json"


def _atomic_write_json(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def export_to_file(
    paths: FoundryPaths,
    run_id: str,
    *,
    sensitivity_threshold: str | None = None,
) -> Path:
    """Export ``run_id`` and write ``<run_dir>/run.json`` atomically."""

    rp = resolve_run_paths(paths, run_id)
    data = export_run(paths, run_id, sensitivity_threshold=sensitivity_threshold)
    return _atomic_write_json(data, run_json_path(rp))


def export_all(
    paths: FoundryPaths,
    *,
    sensitivity_threshold: str | None = None,
) -> list[Path]:
    """Export every discovered run to its own ``run.json``."""

    written: list[Path] = []
    for run_yaml in discover_run_yamls(paths.runs):
        run_dir = run_yaml.parent
        run_meta = _load_yaml_dict(run_yaml, run_id=run_dir.name)
        run_id = str(run_meta.get("run_id") or run_dir.name)
        data = export_run(paths, run_id, sensitivity_threshold=sensitivity_threshold)
        written.append(_atomic_write_json(data, run_dir / "run.json"))
    return written


def list_runs(paths: FoundryPaths) -> list[dict[str, Any]]:
    """Summarize every discovered run for the run-list surface.

    ``status_derived`` reflects on-disk artifacts (not the stale
    ``run.yaml.status``). No path field from ``run_index.yaml`` is read for I/O.
    """

    summaries: list[dict[str, Any]] = []
    for run_yaml in discover_run_yamls(paths.runs):
        run_dir = run_yaml.parent
        rp = RunPaths(run=run_dir)
        run_meta = _load_yaml_dict(run_yaml, run_id=run_dir.name)
        run_id = str(run_meta.get("run_id") or run_dir.name)
        bundle = _load_yaml_dict(rp.evidence_bundle, run_id=run_id)
        verification = _load_yaml_dict(rp.verification, run_id=run_id)
        governance = bundle.get("governance") or {}
        summaries.append(
            {
                "run_id": run_id,
                "intent_id": run_meta.get("intent_id"),
                "created_at": run_meta.get("created_at"),
                "status_derived": derive_status(rp, run_id=run_id),
                "status_raw": run_meta.get("status"),
                "sensitivity": run_meta.get("sensitivity")
                or governance.get("sensitivity")
                or DEFAULT_THRESHOLD,
                "claim_counts": bundle.get("counts") or {},
                "verification_passed": verification.get("passed"),
                "governance_verdict": governance.get("approved_for_writeback"),
                # Schema 1.2 metadata — null for pre-migration runs (matches export_run)
                "linked_projects": run_meta.get("linked_projects") or None,
                "category": run_meta.get("category") or None,
                "tags": run_meta.get("tags") or None,
            }
        )
    return summaries


def _collect_writebacks(rp: RunPaths) -> dict[str, Any] | None:
    """Collect writeback status from the run's writebacks/ directory.

    Returns an RFRunWritebacksSummary-shaped object:
        { targets: [{target, status, url?}], approved_for_writeback: bool|null, ... }
    when the writebacks directory has any known files, or None otherwise.

    The object shape matches the TypeScript RFRunWritebacksSummary interface and
    the JSON schema §RFRunWritebacksSummary definition. Returning a bare list
    would silently break FE consumers that read writebacks.targets?.length.
    """
    if not rp.writebacks.is_dir():
        return None

    # Map each well-known writeback filename to a target label.
    _WRITEBACK_TARGETS: dict[str, str] = {
        "meatywiki_writeback.md": "meatywiki",
        "skillbom_candidate.md": "skillbom",
        "ccdash_event.yaml": "ccdash",
        "intenttree_update.yaml": "intenttree",
        "arc_review_request.yaml": "arc",
        "notebooklm_update.yaml": "notebooklm",
    }

    entries: list[dict[str, Any]] = []
    for filename, target in _WRITEBACK_TARGETS.items():
        path = rp.writebacks / filename
        if not path.exists():
            continue
        entry: dict[str, Any] = {"target": target, "status": "present"}
        # Best-effort: try to read a "url" field from YAML writebacks.
        if filename.endswith(".yaml"):
            try:
                data = _load_yaml_file(path, run_id=None)
                if isinstance(data, dict) and data.get("url"):
                    entry["url"] = str(data["url"])
            except Exception:  # noqa: BLE001
                pass
        entries.append(entry)

    if not entries:
        return None

    # Derive approved_for_writeback from the evidence bundle governance block.
    # We don't re-read the bundle here (already read by the caller); instead we
    # keep the field as null — callers that have bundle data may override. The
    # safe default (null/false) means the FE never auto-approves.
    return {
        "targets": entries,
        "approved_for_writeback": None,
    }


def _read_report_draft(rp: RunPaths) -> str | None:
    """Return the verbatim markdown of the run's report draft, or ``None``.

    Prefers ``report_draft.md``; falls back to ``report_final.md``.  Both paths
    are derived via :class:`RunPaths` — no stored absolute path is ever used.
    """

    for candidate in (rp.report_draft, rp.report_final):
        if candidate.exists():
            return _read_text(candidate)
    return None


def claim_tags_in_report(report_path: Path) -> list[str]:
    """Extract ``[claim:clm_NNN]`` ids cited in a report (helper for tests)."""

    if not report_path.exists():
        return []
    return _CLAIM_TAG_RE.findall(_read_text(report_path))


__all__ = [
    "EXPORT_SCHEMA_VERSION",
    "SENSITIVITY_ORDER",
    "DEFAULT_THRESHOLD",
    "STATUS_LADDER",
    "REDACTION_MARKER",
    "ExportError",
    "resolve_threshold",
    "discover_run_yamls",
    "resolve_run_paths",
    "derive_status",
    "export_run",
    "export_to_file",
    "export_all",
    "list_runs",
    "run_json_path",
    "claim_tags_in_report",
    # title helpers (restored from main)
    "_title_from_slug",
    "_extract_title_from_report_draft",
    "_derive_run_title",
    # ENR helpers (exported for test access)
    "_source_count_by_type",
    "_cost_and_model_profiles",
    "_context_summary",
    "_collect_writebacks",
]
