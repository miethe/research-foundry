"""Writeback + bundle assembly service (contract §9).

Assembles an ``evidence_bundle`` for a run, materializes the three MVP
writeback targets (MeatyWiki source note, SkillBOM candidate, CCDash event),
runs a deterministic review council, and proposes/promotes SkillBOM candidates.

Determinism: every value is derived from on-disk run artifacts; no network or
API keys are required. Verification (when requested) is delegated to the
``verification`` service, which exists after this wave (imported lazily).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..frontmatter import dump_md, load_md
from ..ids import (
    bundle_id,
    meatywiki_writeback_id,
    now_iso,
    skillbom_candidate_id,
    slugify,
)
from ..paths import FoundryPaths
from ..registry import REPORT_INDEX, SKILLBOM_INDEX, Registry
from ..schemas import default_registry, validate
from ..yamlio import append_jsonl, dump_yaml, load_yaml
from . import telemetry

_REGISTRY = default_registry()

_WORK_SENSITIVITIES = {"work_sensitive", "client_sensitive"}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _trace(rp, stage: str, **extra: Any) -> None:
    try:
        append_jsonl({"stage": stage, "ts": now_iso(), **extra}, rp.run_trace)
    except Exception:  # noqa: BLE001 - tracing is best-effort
        pass


def _safe_load(path: Path) -> Any:
    try:
        return load_yaml(path)
    except FileNotFoundError:
        return None


def _schema_or_raise(obj: Any, schema_name: str) -> None:
    if not _REGISTRY.has(schema_name):
        return
    result = validate(obj, schema_name)
    if not result.ok:
        from ..errors import SchemaError

        raise SchemaError(f"{schema_name} invalid: " + "; ".join(result.errors))


def _run_meta(rp) -> dict[str, Any]:
    return _safe_load(rp.run_yaml) or {}


def _ledger(rp) -> dict[str, Any]:
    return _safe_load(rp.claim_ledger) or {}


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.glob(pattern) if p.is_file())


def _claim_status_counts(ledger: dict[str, Any]) -> dict[str, int]:
    claims = ledger.get("claims") or []
    # All six schema-valid statuses are counted so the per-status fields sum to
    # claims_total (claims_mixed/claims_contradicted are extra keys; the bundle
    # schema is additionalProperties:true so they validate).
    counts = {
        "claims_total": len(claims),
        "claims_supported": 0,
        "claims_mixed": 0,
        "claims_contradicted": 0,
        "claims_inference": 0,
        "claims_speculation": 0,
        "claims_unsupported": 0,
    }
    for claim in claims:
        key = f"claims_{(claim or {}).get('status')}"
        if key in counts:
            counts[key] += 1
    return counts


def _report_meta(rp) -> tuple[dict[str, Any], Path | None]:
    for report in (rp.report_final, rp.report_draft):
        if report.exists():
            meta, _ = load_md(report)
            return meta, report
    return {}, None


def _sensitivity(rp) -> str:
    meta, _ = _report_meta(rp)
    sens = meta.get("sensitivity")
    if sens:
        return str(sens)
    return str(_run_meta(rp).get("sensitivity") or "personal")


def _intent_ibom_node(rp, paths: FoundryPaths) -> tuple[str, str, str, dict[str, Any]]:
    """Resolve (intent_id, ibom_id, node_id, intent_dict) from run + intent."""

    meta = _run_meta(rp)
    intent_id = str(meta.get("intent_id") or "")
    intent: dict[str, Any] = {}
    if intent_id:
        candidate = paths.intents_active / f"{intent_id}.yaml"
        loaded = _safe_load(candidate)
        if isinstance(loaded, dict):
            intent = loaded
    ibom_id = str(intent.get("ibom_ref") or meta.get("ibom_id") or "")
    node_id = str(
        intent.get("intenttree_node_ref")
        or meta.get("task_node_id")
        or meta.get("intenttree_node_id")
        or ""
    )
    return intent_id, ibom_id, node_id, intent


def _supported_claims(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in (ledger.get("claims") or []) if (c or {}).get("status") == "supported"]


def _source_card_titles(rp, paths: FoundryPaths) -> dict[str, str]:
    """Map source_card_id -> title from the run's source cards."""

    out: dict[str, str] = {}
    if not rp.sources.exists():
        return out
    for p in sorted(rp.sources.glob("*.md")):
        meta, _ = load_md(p)
        sid = meta.get("source_card_id")
        title = ((meta.get("source") or {}).get("title")) or sid
        if sid:
            out[str(sid)] = str(title)
    return out


# --------------------------------------------------------------------------- #
# build_bundle
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BundleResult:
    run_id: str
    bundle_id: str
    bundle_path: Path
    counts: dict
    verified: bool


def build_bundle(run_id: str, *, verify: bool = True, paths: FoundryPaths | None = None) -> BundleResult:
    """Assemble ``runs/<run>/evidence_bundle.yaml`` (spec §6.11).

    Counts source/extraction cards + claims by status. When ``verify`` is set,
    runs the verification service first and reflects pass/fail in the bundle
    status and ``governance.approved_for_writeback``.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    if not rp.run.exists():
        from ..errors import NotFoundError

        raise NotFoundError(f"run not found: {run_id} ({rp.run})")
    rp.ensure_scaffold()

    ledger = _ledger(rp)
    status_counts = _claim_status_counts(ledger)
    counts = {
        "source_cards": _count_files(rp.sources, "*.md"),
        "extraction_cards": _count_files(rp.extractions, "*.yaml"),
        **status_counts,
    }

    verified = False
    if verify:
        try:
            from .verification import verify_report

            vr = verify_report(run_id, paths=paths)
            verified = bool(vr.passed)
        except Exception:  # noqa: BLE001 - verification optional / degrades
            verified = False

    intent_id, ibom_id, node_id, intent = _intent_ibom_node(rp, paths)
    sensitivity = _sensitivity(rp)

    bundle_ident = bundle_id(intent_id or run_id)
    report_rel = "reports/report_final.md" if rp.report_final.exists() else "reports/report_draft.md"
    bundle: dict[str, Any] = {
        "id": bundle_ident,
        "intent_id": intent_id,
        "run_id": run_id,
        "created_at": now_iso(),
        "status": "verified" if verified else "draft",
        "artifacts": {
            "research_brief": "research_brief.md",
            "swarm_plan": "swarm_plan.yaml",
            "source_cards_dir": "sources/",
            "extraction_cards_dir": "extractions/",
            "claim_ledger": "claims/claim_ledger.yaml",
            "report": report_rel,
            "verification": "reviews/verification.yaml",
            "ccdash_event": "writebacks/ccdash_event.yaml",
        },
        "counts": counts,
        "governance": {
            "sensitivity": sensitivity,
            "approved_for_writeback": verified,
            "approved_by": None,
            "approval_timestamp": None,
        },
        "lineage": {
            "raw_idea_ids": list(intent.get("raw_idea_ids", [])) if isinstance(intent, dict) else [],
            "intent_id": intent_id,
            "ibom_id": ibom_id,
            "intenttree_node_id": node_id,
            "skillbom_ids_used": ["skill_research_swarm_v0"],
        },
    }

    _schema_or_raise(bundle, "evidence_bundle")
    dump_yaml(bundle, rp.evidence_bundle)
    _trace(rp, "bundle", run_id=run_id, bundle_id=bundle_ident, verified=verified)
    return BundleResult(
        run_id=run_id,
        bundle_id=bundle_ident,
        bundle_path=rp.evidence_bundle,
        counts=counts,
        verified=verified,
    )


def _load_bundle(rp) -> dict[str, Any]:
    """Load the evidence bundle, building it (unverified) if missing."""

    bundle = _safe_load(rp.evidence_bundle)
    return bundle if isinstance(bundle, dict) else {}


# --------------------------------------------------------------------------- #
# writeback
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WritebackResult:
    run_id: str
    meatywiki_path: Path | None
    skillbom_path: Path | None
    ccdash_path: Path | None
    intenttree_update_path: Path | None
    arc_review_path: Path | None
    notebooklm_update_path: Path | None
    requires_review: bool


def _render_meatywiki(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    sensitivity: str,
    ledger: dict[str, Any],
    requires_review: bool,
) -> Path:
    """Write writebacks/meatywiki_writeback.md (+ mirror) from the template fields."""

    titles = _source_card_titles(rp, paths)
    supported = _supported_claims(ledger)
    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or "Research Foundry source note")
    slug = slugify(title)
    mwb_ident = meatywiki_writeback_id(title)
    target_page = f"meatywiki/sources/{slug}.md"

    summary = (
        f"Source note distilled from research run {rp.run.name}: "
        f"{len(supported)} supported claim(s) across {len(titles)} source card(s)."
    )
    status = "proposed" if requires_review else "written"

    front: dict[str, Any] = {
        "id": mwb_ident,
        "evidence_bundle_id": bundle_ident,
        "target_page": target_page,
        "writeback_type": "source_note",
        "status": status,
        "summary": summary,
        "key_claims": [
            {"claim_id": c.get("claim_id"), "include": True} for c in supported
        ],
        "links": {
            "source_cards": sorted(titles.keys()),
            "related_pages": ["[[Research Foundry]]", "[[Agentic Control Plane]]"],
        },
        "approval": {
            "required": requires_review,
            "reason": (
                "work/client sensitivity requires human review before writeback"
                if requires_review
                else "personal/public research: auto-approved"
            ),
            "approved_by": None,
        },
    }
    _schema_or_raise(front, "meatywiki_writeback")

    claim_lines = "\n".join(
        f"- {c.get('text', '')} [claim:{c.get('claim_id', '')}]" for c in supported
    ) or "- (no supported claims yet)"
    source_lines = "\n".join(f"- {sid} — {ttl}" for sid, ttl in sorted(titles.items())) or "- (none)"
    body = (
        f"# {title}\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## Key claims\n\n{claim_lines}\n\n"
        f"## Sources\n\n{source_lines}\n\n"
        f"## Links\n\n- [[Research Foundry]]\n- [[Agentic Control Plane]]\n"
    )

    dump_md(front, body, rp.meatywiki_writeback)
    if not requires_review:
        mirror = paths.meatywiki / "sources" / f"{slug}.md"
        dump_md(front, body, mirror)
    return rp.meatywiki_writeback


def _render_skillbom(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    ccdash_event_id_value: str,
    requires_review: bool,
) -> Path:
    """Write writebacks/skillbom_candidate.md (+ mirror) from the template fields."""

    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or "Research swarm")
    cand_ident = skillbom_candidate_id(title)
    name = f"Research Swarm — {title}"
    purpose = (
        "Reusable research swarm: cheap extraction + deep synthesis with claim "
        "traceability and governance gating."
    )

    front: dict[str, Any] = {
        "id": cand_ident,
        "name": name,
        "proposed_skillbom_id": "skill_research_swarm_v0",
        "evidence_bundle_id": bundle_ident,
        "status": "needs_review" if requires_review else "candidate",
        "purpose": purpose,
        "agent_postures": ["researcher", "critic", "synthesizer"],
        "tools_used": ["gpt_researcher", "paperqa2", "claude_agent_sdk", "litellm"],
        "prompts": {
            "system": "skillmeat/prompts/research_swarm_system.md",
            "task": "skillmeat/prompts/research_swarm_task.md",
        },
        "context_packs": ["research_foundry_core"],
        "output_schemas": [
            "source_card.schema.yaml",
            "claim_ledger.schema.yaml",
            "evidence_bundle.schema.yaml",
        ],
        "validation": ["claim_verifier_passed", "governance_guard_passed", "report_reviewed"],
        "known_failure_modes": [
            "source_overcollection",
            "unsupported_synthesis",
            "citation_mismatch",
            "stale_sources",
            "work_personal_boundary_leak",
        ],
        "performance_evidence": {
            "ccdash_event_id": ccdash_event_id_value,
            "quality_score": "pending",
            "rework_count": 0,
            "estimated_cost_usd": 0.0,
        },
    }
    _schema_or_raise(front, "skillbom_candidate")

    body = (
        f"# SkillBOM Candidate: {name}\n\n"
        f"## Purpose\n\n{purpose}\n\n"
        "## Agent postures\n\n- researcher\n- critic\n- synthesizer\n\n"
        "## Tools\n\n- gpt_researcher\n- paperqa2\n- claude_agent_sdk\n- litellm\n\n"
        "## Output schemas\n\n- source_card.schema.yaml\n- claim_ledger.schema.yaml"
        "\n- evidence_bundle.schema.yaml\n\n"
        f"## Performance evidence\n\n- CCDash event id: {ccdash_event_id_value}\n"
    )

    dump_md(front, body, rp.skillbom_candidate)
    mirror = paths.skillmeat / "skillboms" / f"{cand_ident}.md"
    dump_md(front, body, mirror)

    Registry.open(SKILLBOM_INDEX, paths=paths).upsert(
        {
            "id": cand_ident,
            "proposed_skillbom_id": "skill_research_swarm_v0",
            "evidence_bundle_id": bundle_ident,
            "status": front["status"],
            "run_id": rp.run.name,
            "path": str(mirror),
        }
    )
    return rp.skillbom_candidate


def _render_intenttree_update(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    node_id: str,
    ledger: dict[str, Any],
    requires_review: bool,
    profile: str = "personal",
) -> Path:
    """Write writebacks/intenttree_update.yaml (schema-valid candidate).

    Always writes the candidate. When IntentTree is reachable AND node_id
    resolves AND NOT requires_review AND profile is not offline_only, performs
    the live PATCH + artifact POST. Any error during the live push is silently
    swallowed — the candidate file is the authoritative record.
    """

    from ..ids import now_iso

    status_counts = _claim_status_counts(ledger)
    claims_total = status_counts.get("claims_total", 0)
    claims_supported = status_counts.get("claims_supported", 0)

    # Derive verification result from bundle (best-effort).
    bundle = _safe_load(rp.evidence_bundle) or {}
    verification_passed = bundle.get("governance", {}).get("approved_for_writeback", False)

    # Build the list of blocking issues from the verification review.
    blocked_by: list[str] = []
    verification_doc = _safe_load(rp.verification) or {}
    if isinstance(verification_doc.get("checks"), list):
        for check in verification_doc["checks"]:
            if isinstance(check, dict) and check.get("status") == "fail":
                blocked_by.append(str(check.get("id") or "unknown_check"))

    # Build artifact links: evidence bundle, report, and meatywiki candidate.
    artifact_links: list[dict[str, Any]] = [
        {"type": "evidence_bundle", "path": f"runs/{rp.run.name}/evidence_bundle.yaml", "label": "Evidence Bundle"},
    ]
    report_path = rp.report_final if rp.report_final.exists() else rp.report_draft
    if report_path.exists():
        artifact_links.append({
            "type": "report",
            "path": f"runs/{rp.run.name}/{report_path.relative_to(rp.run)}",
            "label": "Research Report",
        })
    if rp.meatywiki_writeback.exists():
        artifact_links.append({
            "type": "meatywiki_writeback",
            "path": f"runs/{rp.run.name}/writebacks/meatywiki_writeback.md",
            "label": "MeatyWiki Writeback Candidate",
        })

    reusable_output_candidates: list[str] = ["evidence_bundle"]
    if claims_supported > 0:
        reusable_output_candidates.append("meatywiki_writeback")
    if verification_passed:
        reusable_output_candidates.append("report")

    # Determine the push status before the live attempt.
    if not node_id:
        push_status = "skipped_no_node"
    elif requires_review:
        push_status = "skipped_requires_review"
    else:
        push_status = "proposed"

    node_status = "completed" if verification_passed else "in_progress"

    candidate: dict[str, Any] = {
        "node_id": node_id or "",
        "evidence_bundle_id": bundle_ident,
        "run_id": rp.run.name,
        "update_timestamp": now_iso(),
        "status": node_status,
        "claims_total": claims_total,
        "claims_supported": claims_supported,
        "verification_passed": bool(verification_passed),
        "reusable_output_candidates": reusable_output_candidates,
        "artifact_links": artifact_links,
        "blocked_by": blocked_by,
        "push_status": push_status,
    }
    _schema_or_raise(candidate, "intenttree_update")
    dump_yaml(candidate, rp.intenttree_update)

    # Live push: only when conditions are met (all errors silently swallowed).
    _offline_profiles = {"offline_only"}
    if node_id and not requires_review and profile not in _offline_profiles:
        try:
            from ..integrations.intenttree import IntentTreeClient

            client = IntentTreeClient.from_config()
            if client.available():
                patch_payload: dict[str, Any] = {
                    "status": node_status,
                    "progress": {
                        "claims_total": claims_total,
                        "claims_supported": claims_supported,
                        "verification_passed": bool(verification_passed),
                    },
                }
                client.patch_node(node_id, patch_payload)
                for art in artifact_links:
                    client.add_node_artifact(node_id, art)
                # Update candidate to reflect successful push.
                candidate = {**candidate, "push_status": "pushed"}
                dump_yaml(candidate, rp.intenttree_update)
            else:
                candidate = {**candidate, "push_status": "skipped_offline"}
                dump_yaml(candidate, rp.intenttree_update)
        except Exception:  # noqa: BLE001 — live push is best-effort, never fails pipeline
            pass

    return rp.intenttree_update


def _render_arc_council(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    ledger: dict[str, Any],
    sensitivity: str,
    requires_review: bool,
    profile: str = "personal",
) -> Path:
    """Write writebacks/arc_review_request.yaml (schema-valid ARC review candidate).

    ALWAYS writes the candidate (status: proposed). When ArcClient is reachable AND
    profile is not offline_only AND NOT requires_review: POSTs to ARC to scaffold the
    review, persists the arc_run_id, then GETs the run to read any available verdict;
    maps verdict (approve -> rf_exit_code 0, concern/block -> 7). Offline/requires_review
    path leaves the candidate at status 'proposed'. Never raises into the pipeline.
    """

    claims_for_review = [
        {
            "claim_id": c.get("claim_id"),
            "text": c.get("text", ""),
            "status": c.get("status", ""),
        }
        for c in (ledger.get("claims") or [])
        if c.get("materiality") == "material"
    ]

    target = f"runs/{rp.run.name}/evidence_bundle.yaml"
    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or rp.run.name)
    objective = f"Review evidence bundle and claim quality for: {title}"

    candidate: dict[str, Any] = {
        "id": f"arc_review_{rp.run.name}",
        "run_id": rp.run.name,
        "arc_run_id": None,
        "evidence_bundle_id": bundle_ident,
        "target": target,
        "objective": objective,
        "council": "research-review-council",
        "roles": ["domain_reviewer", "claim_critic", "governance_officer"],
        "claims_for_review": claims_for_review,
        "verdict": None,
        "rf_exit_code": 7,
        "status": "proposed",
        "governance_context": {
            "sensitivity": sensitivity,
            "requires_review": requires_review,
            "profile": profile,
        },
    }
    _schema_or_raise(candidate, "arc_review_request")
    dump_yaml(candidate, rp.arc_review_request)

    # Live push: only when conditions are met (all errors silently swallowed).
    _offline_profiles = {"offline_only"}
    if not requires_review and profile not in _offline_profiles:
        try:
            from ..integrations.arc import ArcClient

            client = ArcClient.from_config()
            if client.available():
                arc_payload: dict[str, Any] = {
                    "council": candidate["council"],
                    "target": target,
                    "objective": objective,
                }
                response = client.scaffold_review(arc_payload)
                if isinstance(response, dict):
                    arc_run_id = str(response.get("run_id") or "")
                    if arc_run_id:
                        candidate = {**candidate, "arc_run_id": arc_run_id, "status": "submitted"}
                        dump_yaml(candidate, rp.arc_review_request)

                        # Try reading back the run for a verdict.
                        run_record = client.get_run(arc_run_id)
                        if isinstance(run_record, dict):
                            verdict_raw = run_record.get("verdict")
                            if verdict_raw in ("approve", "concern", "block"):
                                verdict = str(verdict_raw)
                                rf_exit = 0 if verdict == "approve" else 7
                                status_map = {
                                    "approve": "approved",
                                    "concern": "concern",
                                    "block": "block",
                                }
                                candidate = {
                                    **candidate,
                                    "verdict": verdict,
                                    "rf_exit_code": rf_exit,
                                    "status": status_map[verdict],
                                }
                                dump_yaml(candidate, rp.arc_review_request)
        except Exception:  # noqa: BLE001 — live push is best-effort, never fails pipeline
            pass

    return rp.arc_review_request


def _render_notebooklm_update(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    ledger: dict[str, Any],
    requires_review: bool,
    profile: str = "personal",
) -> Path:
    """Write writebacks/notebooklm_update.yaml (schema-valid candidate).

    Always writes the deterministic candidate with push_status 'proposed'.
    Resolves (or creates) the target notebook via
    ``services.notebook_correlation.resolve_notebook``.  When NotebookLM is
    reachable AND notebook_id resolved AND NOT requires_review AND profile is
    not offline_only: pushes the report path + source cards as NLM sources and
    updates push_status to 'pushed'.  Any exception during the live push is
    silently swallowed — the candidate file is the authoritative record.
    Never raises into the pipeline.
    """

    from ..ids import now_iso
    from ..integrations import get_notebooklm_client

    run_meta = _run_meta(rp)
    run_id = rp.run.name
    project = str(run_meta.get("project") or "")

    # Build artifact links for this run (mirrors _render_intenttree_update).
    artifact_links: list[dict[str, Any]] = [
        {
            "type": "evidence_bundle",
            "path": f"runs/{run_id}/evidence_bundle.yaml",
            "label": "Evidence Bundle",
        },
    ]
    report_path = rp.report_final if rp.report_final.exists() else rp.report_draft
    if report_path.exists():
        artifact_links.append({
            "type": "report",
            "path": f"runs/{run_id}/{report_path.relative_to(rp.run)}",
            "label": "Research Report",
        })

    # Resolve IntentTree node back-link (best-effort).
    _, _, node_id, _ = _intent_ibom_node(rp, paths)

    # Resolve notebook correlation (best-effort; never raises).
    notebook_id: str | None = None
    notebook_title: str | None = None
    _offline_profiles = {"offline_only"}
    client = get_notebooklm_client()

    try:
        from . import notebook_correlation

        correlation = notebook_correlation.resolve_notebook(
            run_id,
            project=project or None,
            mode=None,
            create=True,
            client=client,
            paths=paths,
        )
        if isinstance(correlation, dict):
            notebook_id = correlation.get("notebook_id") or None
            notebook_title = correlation.get("notebook_title") or None
    except Exception:  # noqa: BLE001 — correlation is best-effort
        pass

    # Determine initial push_status before the live attempt.
    if not notebook_id:
        push_status = "skipped_no_notebook"
    elif requires_review:
        push_status = "skipped_requires_review"
    else:
        push_status = "proposed"

    candidate: dict[str, Any] = {
        "run_id": run_id,
        "update_timestamp": now_iso(),
        "status": "proposed",
        "push_status": push_status,
        "notebook_id": notebook_id,
        "notebook_title": notebook_title,
        "project": project or None,
        "evidence_bundle_id": bundle_ident,
        "pushed_source_ids": [],
        "artifact_links": artifact_links,
        "node_id": node_id or None,
    }
    _schema_or_raise(candidate, "notebooklm_update")
    dump_yaml(candidate, rp.notebooklm_update)

    # Live push: only when conditions are met (all exceptions silently swallowed).
    if notebook_id and not requires_review and profile not in _offline_profiles:
        try:
            if client.available():
                pushed_source_ids: list[dict[str, str]] = []

                # Push the report as the primary source.
                if report_path.exists():
                    src_resp = client.add_source(notebook_id, str(report_path), title="Research Report")
                    if isinstance(src_resp, dict) and src_resp.get("source_id"):
                        pushed_source_ids.append({
                            "nlm_source_id": str(src_resp["source_id"]),
                            "rf_source_card_id": "report",
                        })

                # Push individual source cards.
                if rp.sources.exists():
                    for sc_path in sorted(rp.sources.glob("*.md")):
                        try:
                            sc_meta, _ = load_md(sc_path)
                            sc_id = str(sc_meta.get("source_card_id") or sc_path.stem)
                            sc_resp = client.add_source(notebook_id, str(sc_path), title=sc_id)
                            if isinstance(sc_resp, dict) and sc_resp.get("source_id"):
                                pushed_source_ids.append({
                                    "nlm_source_id": str(sc_resp["source_id"]),
                                    "rf_source_card_id": sc_id,
                                })
                        except Exception:  # noqa: BLE001 — per-card failure is best-effort
                            pass

                candidate = {
                    **candidate,
                    "status": "live_pushed",
                    "push_status": "pushed",
                    "pushed_source_ids": pushed_source_ids,
                }
                dump_yaml(candidate, rp.notebooklm_update)

                # Record lineage in the evidence bundle (best-effort).
                try:
                    bundle = _safe_load(rp.evidence_bundle) or {}
                    if isinstance(bundle, dict):
                        lineage = dict(bundle.get("lineage") or {})
                        lineage["notebooklm_notebook_id"] = notebook_id
                        lineage["notebooklm_source_ids"] = pushed_source_ids
                        bundle = {**bundle, "lineage": lineage}
                        dump_yaml(bundle, rp.evidence_bundle)
                except Exception:  # noqa: BLE001 — lineage update is best-effort
                    pass
            else:
                candidate = {**candidate, "push_status": "skipped_offline"}
                dump_yaml(candidate, rp.notebooklm_update)
        except Exception:  # noqa: BLE001 — live push is best-effort, never fails pipeline
            pass

    return rp.notebooklm_update


def writeback(
    run_id: str,
    *,
    targets: tuple[str, ...] = ("meatywiki", "skillmeat", "ccdash"),
    require_review: bool = False,
    paths: FoundryPaths | None = None,
) -> WritebackResult:
    """Materialize the run's writeback targets + workspace mirrors (contract §9).

    Governance: if ``require_review`` or the run is work/client-sensitive, the
    MeatyWiki writeback is marked ``proposed`` and NOT mirrored into the wiki.

    Additional opt-in targets (not in the default tuple):
    - ``intenttree``: patch the originating IntentTree node + upload artifacts.
    - ``arc``: scaffold an ARC council review for evidence bundle quality.
    - ``notebooklm``: push the report + source cards to a NotebookLM notebook.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    if not rp.run.exists():
        from ..errors import NotFoundError

        raise NotFoundError(f"run not found: {run_id} ({rp.run})")
    rp.ensure_scaffold()

    bundle = _load_bundle(rp)
    if not bundle:
        bundle = {"id": build_bundle(run_id, verify=True, paths=paths).bundle_id}
    bundle_ident = str(bundle.get("id") or bundle_id(run_id))

    ledger = _ledger(rp)
    sensitivity = _sensitivity(rp)
    requires_review = bool(require_review) or sensitivity in _WORK_SENSITIVITIES

    meatywiki_path: Path | None = None
    skillbom_path: Path | None = None
    ccdash_path: Path | None = None
    intenttree_update_path: Path | None = None
    arc_review_path: Path | None = None
    notebooklm_update_path: Path | None = None
    ccdash_event_id_value = ""

    if "ccdash" in targets:
        ccdash_path = telemetry.emit_ccdash_event(run_id, paths=paths)
        event = _safe_load(ccdash_path) or {}
        ccdash_event_id_value = str(event.get("event_id") or "")

    if "meatywiki" in targets:
        meatywiki_path = _render_meatywiki(
            rp,
            paths,
            bundle_ident=bundle_ident,
            sensitivity=sensitivity,
            ledger=ledger,
            requires_review=requires_review,
        )

    if "skillmeat" in targets:
        skillbom_path = _render_skillbom(
            rp,
            paths,
            bundle_ident=bundle_ident,
            ccdash_event_id_value=ccdash_event_id_value,
            requires_review=requires_review,
        )

    if "intenttree" in targets:
        _, _, node_id, _ = _intent_ibom_node(rp, paths)
        intenttree_update_path = _render_intenttree_update(
            rp,
            paths,
            bundle_ident=bundle_ident,
            node_id=node_id,
            ledger=ledger,
            requires_review=requires_review,
        )

    if "arc" in targets:
        arc_review_path = _render_arc_council(
            rp,
            paths,
            bundle_ident=bundle_ident,
            ledger=ledger,
            sensitivity=sensitivity,
            requires_review=requires_review,
        )

    if "notebooklm" in targets:
        notebooklm_update_path = _render_notebooklm_update(
            rp,
            paths,
            bundle_ident=bundle_ident,
            ledger=ledger,
            requires_review=requires_review,
        )

    report_meta, report_path = _report_meta(rp)
    report_id = report_meta.get("report_id")
    if report_id:
        Registry.open(REPORT_INDEX, paths=paths).upsert(
            {
                "id": str(report_id),
                "run_id": run_id,
                "intent_id": str(report_meta.get("intent_id") or ""),
                "evidence_bundle_id": bundle_ident,
                "sensitivity": sensitivity,
                "status": str(report_meta.get("status") or "draft"),
                "requires_review": requires_review,
                "path": str(report_path) if report_path else "",
            }
        )

    _trace(rp, "writeback", run_id=run_id, requires_review=requires_review)
    return WritebackResult(
        run_id=run_id,
        meatywiki_path=meatywiki_path,
        skillbom_path=skillbom_path,
        ccdash_path=ccdash_path,
        intenttree_update_path=intenttree_update_path,
        arc_review_path=arc_review_path,
        notebooklm_update_path=notebooklm_update_path,
        requires_review=requires_review,
    )


# --------------------------------------------------------------------------- #
# council_review
# --------------------------------------------------------------------------- #
_ROLE_POSTURE = {
    "domain_reviewer": "researcher",
    "claim_critic": "critic",
    "governance_officer": "red_team",
    "executive_translator": "executive_translator",
}


def council_review(
    run_id: str,
    *,
    roles: list[str],
    vote: str = "approve-concern-block",
    paths: FoundryPaths | None = None,
) -> Path:
    """Deterministic review council (spec §13.5) → reviews/council_review.yaml.

    Votes are derived from the verification result: pass → approve, warnings →
    concern, fail → block. Validated against the ``review_packet`` schema.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    rp.reviews.mkdir(parents=True, exist_ok=True)

    bundle = _load_bundle(rp)
    bundle_ident = str(bundle.get("id") or bundle_id(run_id))

    # Derive the council decision from verification (deterministic; degrades).
    decision = "approve"
    has_warning = False
    concerns: list[dict[str, Any]] = []
    try:
        from .verification import verify_report

        vr = verify_report(run_id, paths=paths)
        has_warning = any(
            getattr(c, "severity", "") == "warning" and getattr(c, "status", "") in {"warn", "fail"}
            for c in vr.checks
        )
        if not vr.passed:
            decision = "required_block"
            for failed in [
                c for c in vr.checks if getattr(c, "status", "") == "fail"
            ]:
                concerns.append(
                    {
                        "concern_id": getattr(failed, "id", "check"),
                        "severity": "blocker"
                        if getattr(failed, "severity", "") == "error"
                        else "medium",
                        "text": getattr(failed, "detail", "verification check failed"),
                        "required_fix": "Resolve the failing verification check before publishing.",
                    }
                )
        elif has_warning:
            decision = "revise"
            concerns.append(
                {
                    "concern_id": "verification_warnings",
                    "severity": "low",
                    "text": "Verification passed with warnings.",
                    "required_fix": "Review non-blocking warnings before writeback.",
                }
            )
    except Exception:  # noqa: BLE001 - verification optional; default approve
        decision = "approve"

    members = [
        {"role": role, "posture": _ROLE_POSTURE.get(role, "researcher")} for role in roles
    ]
    member_vote = {"approve": "approve", "revise": "concern", "required_block": "block"}[decision]
    for m in members:
        m["vote"] = member_vote

    packet: dict[str, Any] = {
        "id": f"council_{rp.run.name}",
        "evidence_bundle_id": bundle_ident,
        "voting": {"allowed_votes": ["approve", "concern", "block"]},
        "members": members,
        "output": {"decision": decision, "concerns": concerns},
        "reviewer_notes": f"Deterministic council over run {run_id}; vote policy {vote}.",
    }
    _schema_or_raise(packet, "review_packet")
    dump_yaml(packet, rp.council_review)
    _trace(rp, "council", run_id=run_id, decision=decision)
    return rp.council_review


# --------------------------------------------------------------------------- #
# skillbom propose / promote
# --------------------------------------------------------------------------- #
def skillbom_propose(run_id, paths: FoundryPaths | None = None) -> Path:
    """Propose a SkillBOM candidate for ``run_id`` (writes skillmeat target only)."""

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    bundle = _load_bundle(rp)
    if not bundle:
        bundle = {"id": build_bundle(run_id, verify=True, paths=paths).bundle_id}
    bundle_ident = str(bundle.get("id") or bundle_id(run_id))

    sensitivity = _sensitivity(rp)
    requires_review = sensitivity in _WORK_SENSITIVITIES

    ccdash_event_id_value = ""
    event = _safe_load(rp.ccdash_event)
    if isinstance(event, dict):
        ccdash_event_id_value = str(event.get("event_id") or "")

    return _render_skillbom(
        rp,
        paths,
        bundle_ident=bundle_ident,
        ccdash_event_id_value=ccdash_event_id_value,
        requires_review=requires_review,
    )


def skillbom_promote(candidate_id, *, reviewer: str, paths: FoundryPaths | None = None) -> Path:
    """Promote a candidate to ``status: promoted`` in its file + registry."""

    paths = paths or FoundryPaths.discover()
    candidate_path = paths.skillmeat / "skillboms" / f"{candidate_id}.md"
    if not candidate_path.exists():
        from ..errors import NotFoundError

        raise NotFoundError(f"SkillBOM candidate not found: {candidate_id}")

    front, body = load_md(candidate_path)
    front["status"] = "promoted"
    approval = front.get("promotion") if isinstance(front.get("promotion"), dict) else {}
    approval = {**approval, "promoted_by": reviewer, "promoted_at": now_iso()}
    front["promotion"] = approval
    _schema_or_raise(front, "skillbom_candidate")
    dump_md(front, body, candidate_path)

    reg = Registry.open(SKILLBOM_INDEX, paths=paths)
    existing = reg.get(str(candidate_id)) or {"id": str(candidate_id)}
    reg.upsert({**existing, "status": "promoted", "promoted_by": reviewer})
    return candidate_path


__all__ = [
    "BundleResult",
    "build_bundle",
    "WritebackResult",
    "writeback",
    "council_review",
    "skillbom_propose",
    "skillbom_promote",
    "_render_intenttree_update",
    "_render_arc_council",
    "_render_notebooklm_update",
]
