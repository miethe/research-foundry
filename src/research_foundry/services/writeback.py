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

from ..config import FoundryConfig
from ..errors import RFError
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
from . import audit_service, governance, telemetry
from .audit_service import AuditEvent
from .governance import GuardResult

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


def _inference_claims(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Return inference-status claims, recommendations first, then the rest."""

    claims = [c for c in (ledger.get("claims") or []) if (c or {}).get("status") == "inference"]
    recommendations = [c for c in claims if (c or {}).get("claim_type") == "recommendation"]
    others = [c for c in claims if (c or {}).get("claim_type") != "recommendation"]
    return recommendations + others


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
    decision_record_path: Path | None
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


def _render_decision_record(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    sensitivity: str,
    ledger: dict[str, Any],
    requires_review: bool,
) -> Path | None:
    """Write writebacks/decision_record_writeback.md from inference/recommendation claims.

    Returns None (no file written) when there are zero inference claims in the
    ledger — an empty decision record would carry no signal and is omitted.
    """

    inference = _inference_claims(ledger)
    if not inference:
        return None

    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or "Research Foundry decision record")
    slug = slugify(title)
    mwb_ident = meatywiki_writeback_id(f"dr_{title}")
    target_page = f"meatywiki/decisions/{slug}.md"
    status = "proposed" if requires_review else "written"

    # Pull reasoning_summary from the primary (first) recommendation claim;
    # fall back to the first inference claim if no recommendation exists.
    primary = inference[0]
    primary_basis = (primary.get("inference_basis") or {}) if isinstance(primary.get("inference_basis"), dict) else {}
    primary_reasoning = str(primary_basis.get("reasoning_summary") or primary.get("text") or "")

    # Collect all source claim IDs cited across all inference claims.
    all_from_claims: list[str] = []
    for inf in inference:
        basis = (inf.get("inference_basis") or {}) if isinstance(inf.get("inference_basis"), dict) else {}
        for cid in (basis.get("from_claims") or []):
            if cid not in all_from_claims:
                all_from_claims.append(str(cid))

    # Context: summarise what the supported evidence established.
    supported = _supported_claims(ledger)
    context_lines = (
        [f"- {c.get('text', '')} [claim:{c.get('claim_id', '')}]" for c in supported]
        if supported
        else ["- (no supported claims — decision is based on inference only)"]
    )
    context_block = "\n".join(context_lines)

    # Decision: primary recommendation claim text.
    decision_block = f"{primary.get('text', '')} [claim:{primary.get('claim_id', '')}]"

    # Rationale: reasoning_summary from all inference claims.
    rationale_parts: list[str] = []
    for inf in inference:
        basis = (inf.get("inference_basis") or {}) if isinstance(inf.get("inference_basis"), dict) else {}
        summary = str(basis.get("reasoning_summary") or "")
        if summary:
            rationale_parts.append(f"- {summary} [claim:{inf.get('claim_id', '')}]")
    rationale_block = "\n".join(rationale_parts) if rationale_parts else f"- {primary_reasoning}"

    # Consequences: remaining non-primary inference claims.
    consequences_parts = [
        f"- {inf.get('text', '')} [claim:{inf.get('claim_id', '')}]"
        for inf in inference[1:]
    ]
    consequences_block = "\n".join(consequences_parts) if consequences_parts else "- None recorded."

    # Links: back-references to source claim IDs (from_claims) + standard pages.
    link_lines = [f"- [[claim:{cid}]]" for cid in all_from_claims]
    link_lines += ["- [[Research Foundry]]", "- [[Agentic Control Plane]]"]
    links_block = "\n".join(link_lines)

    front: dict[str, Any] = {
        "id": mwb_ident,
        "evidence_bundle_id": bundle_ident,
        "target_page": target_page,
        "writeback_type": "decision_record",
        "status": status,
        "summary": f"Decision record from run {rp.run.name}: {primary_reasoning[:120] or 'see body'}",
        "key_claims": [
            {"claim_id": c.get("claim_id"), "include": True} for c in inference
        ],
        "links": {
            "source_cards": sorted(
                {
                    src.get("source_card_id")
                    for inf in inference
                    for src in (inf.get("sources") or [])
                    if src.get("source_card_id")
                }
            ),
            "related_pages": ["[[Research Foundry]]", "[[Agentic Control Plane]]"],
            "from_claims": all_from_claims,
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

    body = (
        f"# Decision Record: {title}\n\n"
        f"## Context\n\n{context_block}\n\n"
        f"## Decision\n\n{decision_block}\n\n"
        f"## Rationale\n\n{rationale_block}\n\n"
        f"## Consequences\n\n{consequences_block}\n\n"
        f"## Links\n\n{links_block}\n"
    )

    dump_md(front, body, rp.decision_record_writeback)
    _MIRROR_ALLOWED_SENSITIVITIES = {"public", "personal"}
    if not requires_review and sensitivity in _MIRROR_ALLOWED_SENSITIVITIES:
        mirror = paths.meatywiki / "decisions" / f"{slug}.md"
        dump_md(front, body, mirror)
    return rp.decision_record_writeback


def _render_skillbom(
    rp,
    paths: FoundryPaths,
    *,
    bundle_ident: str,
    ccdash_event_id_value: str,
    requires_review: bool,
    ledger: dict[str, Any] | None = None,
) -> Path:
    """Write writebacks/skillbom_candidate.md (+ mirror) from the template fields.

    When ``ledger`` is provided, ``purpose`` and ``known_failure_modes`` are
    populated from the run's recommendation/inference claims rather than the
    fixed stub.
    """

    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or "Research swarm")
    cand_ident = skillbom_candidate_id(title)
    name = f"Research Swarm — {title}"

    # Derive purpose from the primary recommendation/inference claim's text when
    # the ledger is available; fall back to the static stub otherwise.
    _fallback_purpose = (
        "Reusable research swarm: cheap extraction + deep synthesis with claim "
        "traceability and governance gating."
    )
    purpose = _fallback_purpose
    known_failure_modes: list[str] = [
        "source_overcollection",
        "unsupported_synthesis",
        "citation_mismatch",
        "stale_sources",
        "work_personal_boundary_leak",
    ]

    if ledger is not None:
        inference = _inference_claims(ledger)
        if inference:
            primary = inference[0]
            primary_text = str(primary.get("text") or "")
            basis = (primary.get("inference_basis") or {}) if isinstance(primary.get("inference_basis"), dict) else {}
            reasoning = str(basis.get("reasoning_summary") or "")
            if reasoning:
                purpose = reasoning
            elif primary_text:
                purpose = primary_text
            # Append a failure mode for each non-primary inference that represents
            # a potential failure path (claim_type != recommendation).
            for inf in inference[1:]:
                inf_text = str(inf.get("text") or "").strip()
                if inf_text and inf_text not in known_failure_modes:
                    slug = slugify(inf_text, max_words=5)
                    if slug and slug not in known_failure_modes:
                        known_failure_modes.append(slug)

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
        "known_failure_modes": known_failure_modes,
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


# --------------------------------------------------------------------------- #
# governed_writeback (E1-P1 / GOV-002, GOV-003) — the one irreversible hop
# --------------------------------------------------------------------------- #
#
# The swarm-driver's step-6 governed writeback (swarm-driver design §5.3):
#   * personal/public + verified  -> auto POST /api/intake/note (MeatyWiki)
#   * else / verify-failed         -> IntentTree request_create (HITL); BLOCK
#     until request_approve/request_reject; on approve -> emit; on reject ->
#     seal without writeback.
#
# Idempotency (GOV-003, design R7): the writeback key is
# ``meatywiki_writeback_id(title)`` + the sealed ``bundle_id``. A terminal
# receipt (emitted, or HITL-resolved) short-circuits a resumed run so it NEVER
# re-emits. A non-terminal (pending / offline-degraded) state is NOT persisted
# as terminal, so a later resume can retry / continue polling.
#
# FR-0 / doctrine: this path makes ZERO in-process model calls. Every payload
# routes through ``governance.redact_payload`` before it leaves the process.

# Sensitivities eligible for auto (un-gated) writeback (mirrors the driver's
# _ALLOWED_SENSITIVITIES; work/client-sensitive always takes the HITL path).
_AUTO_WRITEBACK_SENSITIVITIES = {"personal", "public"}

# HITL request kind + the request statuses we treat as terminal.
_WRITEBACK_REQUEST_KIND = "research_writeback_approval"
_HITL_APPROVED = "approved"
_HITL_REJECTED = "rejected"
_HITL_TERMINAL = {_HITL_APPROVED, _HITL_REJECTED}


@dataclass(frozen=True)
class GovernedWritebackResult:
    """Terminal outcome of :func:`governed_writeback`.

    ``status`` is one of:
      * ``written``               — auto path, note emitted.
      * ``hitl_approved_written`` — HITL path, approved, note emitted.
      * ``hitl_rejected_sealed``  — HITL path, rejected, sealed WITHOUT writeback.
      * ``hitl_pending``          — HITL gate open, not yet resolved (no emit).
      * ``skipped_idempotent``    — a terminal receipt already exists (no re-emit).
      * ``skipped_unavailable``   — neither MeatyWiki nor the HITL gate reachable
                                    (offline); nothing written, retryable later.
      * ``skipped_locked``        — another wake holds the per-run writeback lock
                                    (A1); nothing written, retryable on the next
                                    drive.
    """

    run_id: str
    bundle_id: str
    writeback_id: str
    status: str
    emitted: bool
    note_id: str | None = None
    request_id: str | None = None
    requires_review: bool = False


def _writeback_receipt_path(rp) -> Path:
    return rp.writebacks / "meatywiki_intake_receipt.yaml"


def _load_writeback_receipt(rp) -> dict[str, Any]:
    data = _safe_load(_writeback_receipt_path(rp))
    return data if isinstance(data, dict) else {}


def _receipt_is_terminal(receipt: dict[str, Any], *, writeback_id: str, bundle_id: str) -> bool:
    """True when a prior receipt matches the idempotency key AND is terminal.

    Terminal = the note was emitted, OR the HITL gate was resolved (approved &
    written, or rejected & sealed). A pending / offline-degraded prior state is
    not terminal, so a resumed run may continue.
    """

    if not receipt:
        return False
    if str(receipt.get("writeback_id") or "") != writeback_id:
        return False
    if str(receipt.get("bundle_id") or "") != bundle_id:
        return False
    return str(receipt.get("status") or "") in {
        "written",
        "hitl_approved_written",
        "hitl_rejected_sealed",
    }


def _write_receipt(rp, receipt: dict[str, Any], *, config: FoundryConfig | None = None) -> None:
    """Persist the writeback receipt (routed through redact_payload)."""

    rp.writebacks.mkdir(parents=True, exist_ok=True)
    safe = governance.redact_payload(receipt, config=config)
    dump_yaml(safe, _writeback_receipt_path(rp))


# A1 (governance review): the one irreversible hop (POST /api/intake/note) and the
# HITL request_create must not be raced by two concurrent wakes, nor re-fired on a
# crash between the network call and its receipt. This per-run advisory lock closes
# the concurrent-wake window. A holder whose pid is provably dead is reclaimed
# immediately (same-host liveness check); the wall-clock TTL is only a cross-host /
# lost-pid backstop, set well above a blocking HITL poll wait (max_polls *
# poll_interval, default 300s) so a legitimately-slow holder is never stolen.
# Release is pid-ownership-checked so a wake whose lock WAS reclaimed can never
# delete the reclaiming wake's fresh lock.
_WRITEBACK_LOCK_TTL_SECONDS = 1800


def _writeback_lock_path(rp) -> Path:
    return rp.run / ".writeback.lock"


def _read_lock_pid(path: Path) -> int | None:
    """Parse the ``pid:`` line from a lock file; ``None`` if absent/corrupt."""

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("pid:"):
                return int(line.split(":", 1)[1].strip())
    except (OSError, ValueError):
        return None
    return None


def _pid_alive(pid: int) -> bool:
    """Best-effort same-host liveness probe (conservative: unknown -> alive)."""

    import os

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # exists but not ours (PermissionError) / unknown -> assume alive
    return True


def _acquire_writeback_lock(rp) -> bool:
    """Best-effort exclusive per-run writeback lock (A1).

    Returns ``True`` if acquired, ``False`` on live contention. A lock is reclaimed
    only when its holder is provably gone — the recorded pid is dead, OR the lock
    has aged past :data:`_WRITEBACK_LOCK_TTL_SECONDS` (the lost-pid / cross-host
    backstop). Fail-soft: any unexpected I/O error yields ``True`` (degrade to the
    prior no-lock behaviour) rather than wedging the writeback.
    """

    import os
    import time

    path = _writeback_lock_path(rp)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):  # at most one reclaim retry after removing a stale lock
            try:
                fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pid = _read_lock_pid(path)
                try:
                    age = time.time() - path.stat().st_mtime
                except OSError:
                    return True  # cannot stat -> don't block the writeback
                # Only a provably-gone holder is reclaimable: a live pid within the
                # TTL owns the lock. (Dead pid OR aged-out -> reclaim.)
                if pid is not None and _pid_alive(pid) and age <= _WRITEBACK_LOCK_TTL_SECONDS:
                    return False
                try:
                    path.unlink()  # holder gone -> reclaim, then retry the create once
                except OSError:
                    return False
                continue
            else:
                with os.fdopen(fd, "w") as fh:
                    fh.write(f"acquired_at: {now_iso()}\npid: {os.getpid()}\n")
                return True
    except OSError:
        return True  # lock I/O is advisory only; never block on it
    return False


def _release_writeback_lock(rp) -> None:
    """Release the lock ONLY if this process still owns it (pid match).

    If our lock was reclaimed as stale and re-created by another wake, the file's
    pid is no longer ours, so we must NOT delete it — that would drop the new
    holder's lock and reopen the race. A leaked lock from a corrupt/lost pid line
    self-heals via the dead-pid / TTL reclaim in :func:`_acquire_writeback_lock`.
    """

    import os

    path = _writeback_lock_path(rp)
    try:
        if _read_lock_pid(path) == os.getpid():
            path.unlink()
    except OSError:
        pass


def _build_intake_payload(
    rp,
    paths: FoundryPaths,
    *,
    writeback_id: str,
    bundle_ident: str,
    sensitivity: str,
    config: FoundryConfig | None = None,
) -> dict[str, Any]:
    """Compile the MeatyWiki ``/api/intake/note`` payload from the rendered note.

    Reads the materialized ``writebacks/meatywiki_writeback.md`` (front matter +
    body) so the intake note mirrors the rendered writeback exactly. The whole
    payload is routed through ``governance.redact_payload`` (D5) so no secret
    ever leaves the process on the wire — the untrusted-web body it may quote is
    already fenced upstream and is DATA only (GOV-004).
    """

    body = ""
    if rp.meatywiki_writeback.exists():
        _, body = load_md(rp.meatywiki_writeback)
    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or "Research Foundry source note")

    payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "source": "research_foundry",
        "tags": ["research-foundry", "source-note"],
        "metadata": {
            "meatywiki_writeback_id": writeback_id,
            "evidence_bundle_id": bundle_ident,
            "run_id": rp.run.name,
            "sensitivity": sensitivity,
        },
    }
    return governance.redact_payload(payload, config=config)


def governed_writeback(
    run_id: str,
    *,
    paths: FoundryPaths | None = None,
    intenttree_client: Any | None = None,
    meatywiki_client: Any | None = None,
    node_id: str | None = None,
    approver_identity: str | None = None,
    wait: bool = True,
    poll_interval: float = 2.0,
    max_polls: int = 150,
) -> GovernedWritebackResult:
    """Governed MeatyWiki writeback with a HITL gate (GOV-002/003).

    Decision (design §5.3):
      * ``sensitivity ∈ {personal, public}`` AND the bundle is verified →
        auto-emit ``POST /api/intake/note``.
      * otherwise (work/client-sensitive, or verify failed) → open an IntentTree
        HITL ``request_create`` with the bundle attached and **block** until the
        request resolves (``request_approve`` → emit; ``request_reject`` → seal
        without writeback).

    Idempotency (GOV-003): a terminal receipt keyed on
    ``meatywiki_writeback_id`` + ``bundle_id`` short-circuits a resumed run so it
    never re-emits.

    All network is fail-soft and injectable for offline tests: pass
    ``intenttree_client`` / ``meatywiki_client`` mocks. With no reachable target
    (offline), this is a pure no-op that writes nothing and returns
    ``skipped_unavailable`` (retryable later) — so the deterministic drive stays
    a clean no-op in the offline suite.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    if not rp.run.exists():
        from ..errors import NotFoundError

        raise NotFoundError(f"run not found: {run_id} ({rp.run})")
    rp.ensure_scaffold()

    config = FoundryConfig(paths=paths)
    bundle = _load_bundle(rp)
    if not bundle:
        bundle = {"id": build_bundle(run_id, verify=True, paths=paths).bundle_id}
    bundle_ident = str(bundle.get("id") or bundle_id(run_id))
    verified = bool(
        (bundle.get("governance") or {}).get("approved_for_writeback")
    ) if isinstance(bundle.get("governance"), dict) else False

    # Sensitivity is resolved ONLY from run/report front matter (never from any
    # fenced untrusted web body) — GOV-004's non-influence guarantee.
    sensitivity = _sensitivity(rp)

    report_meta, _ = _report_meta(rp)
    title = str(report_meta.get("title") or "Research Foundry source note")
    writeback_id = meatywiki_writeback_id(title)

    # --- GOV-003: idempotency short-circuit -------------------------------- #
    receipt = _load_writeback_receipt(rp)
    if _receipt_is_terminal(receipt, writeback_id=writeback_id, bundle_id=bundle_ident):
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="skipped_idempotent",
            emitted=bool(receipt.get("emitted")),
            note_id=receipt.get("note_id"),
            request_id=receipt.get("request_id"),
            requires_review=bool(receipt.get("requires_review")),
        )

    auto = sensitivity in _AUTO_WRITEBACK_SENSITIVITIES and verified

    # --- A1: serialize the irreversible hop under a per-run advisory lock ---- #
    # Two concurrent wakes for the same run must not each emit / open a gate. On
    # live contention we return a non-terminal ``skipped_locked`` (retryable on
    # the next drive), never a duplicate write.
    if not _acquire_writeback_lock(rp):
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="skipped_locked",
            emitted=False,
            requires_review=not auto,
        )

    try:
        # Re-check terminality inside the lock — a wake that finalized while we
        # were acquiring must not be re-emitted (closes the short-circuit TOCTOU).
        receipt = _load_writeback_receipt(rp)
        if _receipt_is_terminal(receipt, writeback_id=writeback_id, bundle_id=bundle_ident):
            return GovernedWritebackResult(
                run_id=run_id,
                bundle_id=bundle_ident,
                writeback_id=writeback_id,
                status="skipped_idempotent",
                emitted=bool(receipt.get("emitted")),
                note_id=receipt.get("note_id"),
                request_id=receipt.get("request_id"),
                requires_review=bool(receipt.get("requires_review")),
            )

        # NOTE: the writeback markdown is rendered only inside the branch that
        # will actually emit / open a gate (after the availability check), so a
        # fully offline drive is a pure no-op that writes nothing to disk (keeps
        # the deterministic-drive resume a strict no-op).
        if auto:
            return _auto_emit(
                run_id,
                rp,
                paths,
                writeback_id=writeback_id,
                bundle_ident=bundle_ident,
                sensitivity=sensitivity,
                meatywiki_client=meatywiki_client,
                config=config,
            )

        return _hitl_gate(
            run_id,
            rp,
            paths,
            writeback_id=writeback_id,
            bundle_ident=bundle_ident,
            sensitivity=sensitivity,
            verified=verified,
            node_id=node_id,
            approver_identity=approver_identity,
            intenttree_client=intenttree_client,
            meatywiki_client=meatywiki_client,
            wait=wait,
            poll_interval=poll_interval,
            max_polls=max_polls,
            config=config,
        )
    finally:
        _release_writeback_lock(rp)


def _resolve_meatywiki_client(meatywiki_client: Any | None) -> Any:
    if meatywiki_client is not None:
        return meatywiki_client
    from ..integrations import get_meatywiki_client

    return get_meatywiki_client()


def _resolve_intenttree_client(intenttree_client: Any | None) -> Any:
    if intenttree_client is not None:
        return intenttree_client
    from ..integrations import get_intenttree_client

    return get_intenttree_client()


def _emit_note(
    rp,
    paths: FoundryPaths,
    *,
    writeback_id: str,
    bundle_ident: str,
    sensitivity: str,
    client: Any,
    config: FoundryConfig,
) -> str | None:
    """POST the compiled intake note; return the note_id or ``None`` on failure."""

    payload = _build_intake_payload(
        rp,
        paths,
        writeback_id=writeback_id,
        bundle_ident=bundle_ident,
        sensitivity=sensitivity,
        config=config,
    )
    resp = client.post_note(payload)
    if isinstance(resp, dict):
        return str(resp.get("note_id") or resp.get("id") or "") or None
    return None


def _auto_emit(
    run_id: str,
    rp,
    paths: FoundryPaths,
    *,
    writeback_id: str,
    bundle_ident: str,
    sensitivity: str,
    meatywiki_client: Any | None,
    config: FoundryConfig,
) -> GovernedWritebackResult:
    client = _resolve_meatywiki_client(meatywiki_client)
    if not client.available():
        # Offline: pure no-op, retryable later (no terminal receipt written).
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="skipped_unavailable",
            emitted=False,
        )

    # Materialize the rendered source note (auto-approved) for the intake body.
    _render_meatywiki(
        rp,
        paths,
        bundle_ident=bundle_ident,
        sensitivity=sensitivity,
        ledger=_ledger(rp),
        requires_review=False,
    )

    # A1: persist a NON-terminal intent receipt BEFORE the irreversible POST, so a
    # crash between the POST and the terminal receipt leaves a durable marker. A
    # resumed run then knows an emit may already have landed; re-POST idempotency
    # ultimately rests on Portal-side dedup of ``metadata.meatywiki_writeback_id``
    # (RF always sends it — see ``_build_intake_payload`` / ``integrations/meatywiki``).
    prior = _load_writeback_receipt(rp)
    reconciling = str(prior.get("status") or "") == "emit_pending" and (
        str(prior.get("writeback_id") or "") == writeback_id
    )
    _write_receipt(
        rp,
        {
            "writeback_id": writeback_id,
            "bundle_id": bundle_ident,
            "status": "emit_pending",
            "emitted": False,
            "sensitivity": sensitivity,
            "requires_review": False,
            "intent_at": now_iso(),
        },
        config=config,
    )

    note_id = _emit_note(
        rp,
        paths,
        writeback_id=writeback_id,
        bundle_ident=bundle_ident,
        sensitivity=sensitivity,
        client=client,
        config=config,
    )
    if note_id is None:
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="skipped_unavailable",
            emitted=False,
        )

    _write_receipt(
        rp,
        {
            "writeback_id": writeback_id,
            "bundle_id": bundle_ident,
            "status": "written",
            "emitted": True,
            "note_id": note_id,
            "sensitivity": sensitivity,
            "requires_review": False,
            "emitted_at": now_iso(),
            # True when this terminal write followed a prior in-flight intent
            # receipt (a crash-resumed emit) — surfaced for audit/reconcile.
            "reconciled_from_pending": reconciling,
        },
        config=config,
    )
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="writeback",
            action="meatywiki_intake",
            target_ref=run_id,
            result="success",
        ),
    )
    return GovernedWritebackResult(
        run_id=run_id,
        bundle_id=bundle_ident,
        writeback_id=writeback_id,
        status="written",
        emitted=True,
        note_id=note_id,
        requires_review=False,
    )


def _hitl_gate(
    run_id: str,
    rp,
    paths: FoundryPaths,
    *,
    writeback_id: str,
    bundle_ident: str,
    sensitivity: str,
    verified: bool,
    node_id: str | None,
    approver_identity: str | None,
    intenttree_client: Any | None,
    meatywiki_client: Any | None,
    wait: bool,
    poll_interval: float,
    max_polls: int,
    config: FoundryConfig,
) -> GovernedWritebackResult:
    import time

    it_client = _resolve_intenttree_client(intenttree_client)

    # Resolve the bound node id when not supplied.
    if not node_id:
        _, _, node_id, _ = _intent_ibom_node(rp, paths)

    # Reuse an already-open request if a pending receipt exists for this key.
    receipt = _load_writeback_receipt(rp)
    request_id: str | None = None
    if (
        receipt
        and str(receipt.get("writeback_id") or "") == writeback_id
        and str(receipt.get("bundle_id") or "") == bundle_ident
        and receipt.get("request_id")
    ):
        request_id = str(receipt["request_id"])

    if request_id is None:
        # Render the proposed (requires_review) note so the reviewer sees it.
        _render_meatywiki(
            rp,
            paths,
            bundle_ident=bundle_ident,
            sensitivity=sensitivity,
            ledger=_ledger(rp),
            requires_review=True,
        )
        title = f"Research writeback approval — run {rp.run.name}"
        body = (
            f"Sensitivity={sensitivity}; verified={verified}. This run requires "
            "human review before its MeatyWiki writeback. Approve to emit the "
            "source note; reject to seal the run without writeback."
        )
        artifacts = [
            {
                "type": "evidence_bundle",
                "path": f"runs/{rp.run.name}/evidence_bundle.yaml",
                "label": "Evidence Bundle",
            },
            {
                "type": "meatywiki_writeback",
                "path": f"runs/{rp.run.name}/writebacks/meatywiki_writeback.md",
                "label": "MeatyWiki Writeback (proposed)",
            },
        ]
        # A1: persist a NON-terminal intent receipt BEFORE opening the gate as an
        # AUDIT marker that a HITL request may already be open for this key.
        # NOTE (residual gap): unlike the auto-emit path — which leans on Portal
        # dedup of meatywiki_writeback_id — request_create carries no client-side
        # idempotency key, so this receipt does NOT by itself prevent a duplicate
        # request if a crash lands between request_create succeeding server-side
        # and the hitl_pending write below (the reuse-check keys off request_id,
        # which only that later write persists). Closing that fully needs an
        # IntentTree-side idempotency key or a node request lookup (out of scope
        # here); the per-run lock still prevents the *concurrent-wake* duplicate.
        _write_receipt(
            rp,
            {
                "writeback_id": writeback_id,
                "bundle_id": bundle_ident,
                "status": "hitl_intent",
                "emitted": False,
                "sensitivity": sensitivity,
                "requires_review": True,
                "intent_at": now_iso(),
            },
            config=config,
        )
        req = it_client.request_create(
            node_id=node_id,
            kind=_WRITEBACK_REQUEST_KIND,
            title=title,
            body=body,
            artifacts=artifacts,
            sensitivity=sensitivity,
        )
        if not isinstance(req, dict) or not (req.get("request_id") or req.get("id")):
            # Gate could not be opened (offline) — pure no-op, retryable later.
            return GovernedWritebackResult(
                run_id=run_id,
                bundle_id=bundle_ident,
                writeback_id=writeback_id,
                status="skipped_unavailable",
                emitted=False,
                requires_review=True,
            )
        request_id = str(req.get("request_id") or req.get("id"))
        # Persist a NON-terminal pending receipt so a resume reuses this request.
        _write_receipt(
            rp,
            {
                "writeback_id": writeback_id,
                "bundle_id": bundle_ident,
                "status": "hitl_pending",
                "emitted": False,
                "request_id": request_id,
                "sensitivity": sensitivity,
                "requires_review": True,
                "opened_at": now_iso(),
            },
            config=config,
        )
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="writeback",
                action="hitl_request_create",
                target_ref=run_id,
                result="success",
            ),
        )

    if not wait:
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="hitl_pending",
            emitted=False,
            request_id=request_id,
            requires_review=True,
        )

    # Block until the request resolves (approve/reject) or polling is exhausted.
    status = "pending"
    for _ in range(max(1, max_polls)):
        rec = it_client.request_status(request_id)
        status = str(rec.get("status") or "pending") if isinstance(rec, dict) else "pending"
        if status in _HITL_TERMINAL:
            break
        if poll_interval > 0:
            time.sleep(poll_interval)

    if status == _HITL_APPROVED:
        mw_client = _resolve_meatywiki_client(meatywiki_client)
        note_id: str | None = None
        if mw_client.available():
            note_id = _emit_note(
                rp,
                paths,
                writeback_id=writeback_id,
                bundle_ident=bundle_ident,
                sensitivity=sensitivity,
                client=mw_client,
                config=config,
            )
        if note_id is None:
            # Approved but sink unreachable — stay non-terminal so we retry.
            return GovernedWritebackResult(
                run_id=run_id,
                bundle_id=bundle_ident,
                writeback_id=writeback_id,
                status="skipped_unavailable",
                emitted=False,
                request_id=request_id,
                requires_review=True,
            )
        _write_receipt(
            rp,
            {
                "writeback_id": writeback_id,
                "bundle_id": bundle_ident,
                "status": "hitl_approved_written",
                "emitted": True,
                "note_id": note_id,
                "request_id": request_id,
                "sensitivity": sensitivity,
                "requires_review": True,
                "approver": approver_identity,
                "emitted_at": now_iso(),
            },
            config=config,
        )
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="writeback",
                action="meatywiki_intake",
                target_ref=run_id,
                result="success",
            ),
        )
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="hitl_approved_written",
            emitted=True,
            note_id=note_id,
            request_id=request_id,
            requires_review=True,
        )

    if status == _HITL_REJECTED:
        # Seal WITHOUT writeback (terminal — never re-emits).
        _write_receipt(
            rp,
            {
                "writeback_id": writeback_id,
                "bundle_id": bundle_ident,
                "status": "hitl_rejected_sealed",
                "emitted": False,
                "request_id": request_id,
                "sensitivity": sensitivity,
                "requires_review": True,
                "approver": approver_identity,
                "sealed_at": now_iso(),
            },
            config=config,
        )
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="writeback",
                action="hitl_request_reject",
                target_ref=run_id,
                result="success",
            ),
        )
        return GovernedWritebackResult(
            run_id=run_id,
            bundle_id=bundle_ident,
            writeback_id=writeback_id,
            status="hitl_rejected_sealed",
            emitted=False,
            request_id=request_id,
            requires_review=True,
        )

    # Polling exhausted without resolution — leave the pending receipt in place.
    return GovernedWritebackResult(
        run_id=run_id,
        bundle_id=bundle_ident,
        writeback_id=writeback_id,
        status="hitl_pending",
        emitted=False,
        request_id=request_id,
        requires_review=True,
    )


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

    try:
        rp.ensure_scaffold()

        bundle = _load_bundle(rp)
        if not bundle:
            bundle = {"id": build_bundle(run_id, verify=True, paths=paths).bundle_id}
        bundle_ident = str(bundle.get("id") or bundle_id(run_id))

        ledger = _ledger(rp)
        sensitivity = _sensitivity(rp)
        requires_review = bool(require_review) or sensitivity in _WORK_SENSITIVITIES

        meatywiki_path: Path | None = None
        decision_record_path: Path | None = None
        skillbom_path: Path | None = None
        ccdash_path: Path | None = None
        intenttree_update_path: Path | None = None
        arc_review_path: Path | None = None
        notebooklm_update_path: Path | None = None
        ccdash_event_id_value = ""

        if "ccdash" in targets:
            ccdash_event_id_value = str(telemetry.emit_ccdash_event(run_id, paths=paths) or "")
            ccdash_path = rp.ccdash_event

        if "meatywiki" in targets:
            meatywiki_path = _render_meatywiki(
                rp,
                paths,
                bundle_ident=bundle_ident,
                sensitivity=sensitivity,
                ledger=ledger,
                requires_review=requires_review,
            )
            # decision_record is additive: emits only when inference claims exist.
            decision_record_path = _render_decision_record(
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
                ledger=ledger,
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
        result = WritebackResult(
            run_id=run_id,
            meatywiki_path=meatywiki_path,
            decision_record_path=decision_record_path,
            skillbom_path=skillbom_path,
            ccdash_path=ccdash_path,
            intenttree_update_path=intenttree_update_path,
            arc_review_path=arc_review_path,
            notebooklm_update_path=notebooklm_update_path,
            requires_review=requires_review,
        )

    except RFError as exc:
        # Audit: record writeback failure — fail-open; never re-raises audit call itself.
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="writeback",
                action="writeback",
                target_ref=run_id,
                result="failure",
                error_detail=str(exc),
            ),
        )
        raise

    # Audit: record successful writeback after all targets have been rendered.
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="writeback",
            action="writeback",
            target_ref=run_id,
            result="success",
        ),
    )
    return result


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
# approve_and_dispatch — DESIGN CONTRACT (locked, TASK-1.1 / ORC-001)
# --------------------------------------------------------------------------- #
#
# STATUS: This section locked the signature, return shape, and call order for
# ``approve_and_dispatch()`` (ORC-001). The body is now fully implemented —
# ORC-002 (call-order orchestration), ORC-003 (per-target isolated dispatch),
# ORC-004 (``approved_by``/``approval_timestamp`` population), and ORC-005
# (advisory dispatch lock) all landed in that dependency order, in this same
# file. Phase 1 is complete. Phase 2 (the new ``api/routers/writeback.py``
# route) and Phase 3 (runs-viewer "Approve & Dispatch" UI action) build
# against this contract without further design questions — do not change this
# signature or ``ApproveDispatchResult``'s field set without re-opening
# ORC-001.
#
# WHAT THIS IS NOT (do not re-derive a different design):
#   - It is not a new dispatch/rendering mechanism. Per D4 (locked decision,
#     see this feature's implementation-plan frontmatter `decisions[3]`), it
#     calls the SAME three per-target primitives the existing monolithic
#     ``writeback()`` already calls above — ``telemetry.emit_ccdash_event``,
#     ``_render_meatywiki``, ``_render_skillbom`` — each independently wrapped
#     in its own try/except for per-target isolation (``writeback()`` itself
#     has no such isolation today; that gap is exactly why this function
#     exists instead of calling ``writeback()`` directly). Fixed order:
#     ccdash -> meatywiki -> skillmeat, mirroring ``writeback()``'s existing
#     target-check order above.
#   - It does not modify, wrap, or change the signature/behavior of
#     ``writeback()``, ``council_review()``, or ``build_bundle()``. All three
#     remain byte-identical after this change (verify via
#     ``git diff --stat`` against this file — only additions below the
#     ``council_review()`` return statement, plus the new top-of-file
#     imports of ``governance``/``GuardResult``).
#
# CALL ORDER (ORC-002 implements this sequence; guard_check MUST run before
# any target dispatch — PRD acceptance row 1):
#   1. ``build_bundle(run_id, verify=True, paths=paths)``
#      -> gives ``bundle_id`` + ``verified``; also (re)writes
#      ``evidence_bundle.yaml`` with ``governance.approved_by``/
#      ``approval_timestamp`` still ``None`` at this point (see line ~237-238
#      in ``build_bundle`` above) — step 5 below is where those two fields
#      get populated, NOT here.
#   2. ``council_review(run_id, roles=..., paths=paths)`` — ALWAYS run, never
#      conditionally skipped (D1, locked: resolves PRD OQ-1). Read back
#      ``reviews/council_review.yaml`` for ``output.decision`` (one of
#      ``approve``/``revise``/``required_block``) and
#      ``output.concerns[].required_fix`` for the DTO's ``reviewer_notes``/
#      ``required_fix`` fields.
#   3. ``governance.load_run_context(run_id, writeback_targets=targets,
#      paths=paths)`` -> ``governance.guard_check(ctx, paths=paths)``.
#      A council decision of ``required_block`` is treated as an additional
#      hard stop equivalent to a failing guard, even though guard_check()
#      does not itself read the council packet — ORC-002 decides the
#      combined gate condition explicitly (both must clear before any
#      dispatch).
#   4. Per-target dispatch — ONLY if the combined gate in step 3 passes
#      (``guard_result.passed`` and council decision != ``required_block``).
#      If the gate does not pass: dispatch is skipped entirely (every
#      requested target is recorded ``"skipped"`` in ``target_status``), zero
#      files are written under ``writebacks/``, and ``overall_status`` is
#      ``"blocked"``. This is what PRD acceptance row 2 means by "a
#      block/require_approval result aborts before any target is attempted".
#   5. On a successful (non-blocked) invocation, populate
#      ``evidence_bundle.governance.approved_by`` (from
#      ``approver_identity``) and ``approval_timestamp`` (``now_iso()``) in
#      ``evidence_bundle.yaml`` — this is the ORC-004 population point
#      referenced in step 1's note above; it happens AFTER dispatch, not
#      before, so a partially-failed dispatch is still reflected accurately.
#
# ``overall_status`` derivation (ORC-003 fills in the target loop that
# produces ``target_status``; this is the aggregation rule ORC-002/003 must
# implement):
#   - "blocked":  the combined gate in step 3 did not pass (no dispatch
#     attempted at all).
#   - "success":  gate passed AND every requested target's status is
#     "success".
#   - "partial":  gate passed AND at least one requested target is
#     "success" and at least one is "failed".
#   - a fully-failed dispatch (gate passed, but every target "failed") is
#     still "partial", not "blocked" — "blocked" is reserved for the
#     pre-dispatch governance gate specifically, so callers can distinguish
#     "we never tried" from "we tried and it went badly".
#
# Concurrency (D2, locked; ORC-005 implements): a short-TTL
# ``.dispatch.lock`` file per run is an advisory guard only — it is NOT a
# hard 409-reject and NOT part of this function's return contract. It does
# not appear in ``ApproveDispatchResult``.
#
@dataclass(frozen=True)
class ApproveDispatchResult:
    """Locked DTO shape for :func:`approve_and_dispatch` (TASK-1.1 / ORC-001).

    Self-contained — no HTTP-layer types (no ``Request``/``Response``/status
    codes). Phase 2's route maps this onto its own response model; Phase 3's
    UI binding types against this shape's JSON-serializable projection.
    """

    bundle_id: str
    verified: bool
    council_decision: str  # "approve" | "revise" | "required_block"
    reviewer_notes: str
    required_fix: str | None
    guard_result: GuardResult  # .passed / .exit_code / .violations — see governance.py
    target_status: dict[str, str]  # per requested target: "success" | "failed" | "skipped"
    overall_status: str  # "success" | "partial" | "blocked"


# Advisory-only TTL (seconds) recorded in the ``.dispatch.lock`` file written
# at the top of ``approve_and_dispatch()``. Not enforced as a hard gate in
# this implementation (D2, locked) — it is metadata for Phase 4 tests/
# inspection, not a mechanism this function reads back to block itself.
_DISPATCH_LOCK_TTL_SECONDS = 60


def approve_and_dispatch(
    run_id: str,
    *,
    approver_identity: str | None = None,
    targets: tuple[str, ...] = ("ccdash", "meatywiki", "skillmeat"),
    paths: FoundryPaths | None = None,
) -> ApproveDispatchResult:
    """Approve a run's evidence bundle and dispatch it to writeback targets.

    LOCKED CONTRACT (TASK-1.1 / ORC-001) — signature and return shape only.
    Real implementation lands in ORC-002 (call-order orchestration),
    ORC-003 (per-target isolated dispatch), ORC-004 (``approved_by``/
    ``approval_timestamp`` population), and ORC-005 (advisory dispatch lock),
    in that dependency order. See the design-lock comment block immediately
    above this function for the full call-order, gating, and
    ``overall_status`` derivation rules that those tasks must implement.

    Composes (does not modify) the existing primitives: ``build_bundle()``,
    ``council_review()``, ``governance.load_run_context()`` +
    ``governance.guard_check()``, and the three per-target render primitives
    already used by ``writeback()`` (``telemetry.emit_ccdash_event``,
    ``_render_meatywiki``, ``_render_skillbom``) — per D4, not ``writeback()``
    itself.

    Parameters
    ----------
    run_id:
        The run to approve and dispatch.
    approver_identity:
        Resolved identity string (e.g. a user id/email) supplied by the
        caller. Phase 2's route resolves this from ``request.state.identity``
        and threads it in; ``None`` is valid (loopback/no-auth mode) and
        results in ``evidence_bundle.governance.approved_by`` staying
        ``None`` even on success — callers needing a mandatory identity
        enforce that at the route layer (RBAC), not here.
    targets:
        Which writeback targets to attempt, restricted to the MVP set
        ``{"ccdash", "meatywiki", "skillmeat"}``. Order of attempt is always
        ccdash -> meatywiki -> skillmeat regardless of tuple order, matching
        ``writeback()``'s existing target-check order.
    paths:
        Optional :class:`FoundryPaths` override, threaded through unchanged
        to every composed primitive (same convention as ``writeback()``,
        ``council_review()``, ``build_bundle()``).

    Returns
    -------
    ApproveDispatchResult
        See the class docstring above for the full locked field set.

    Raises
    ------
    NotFoundError
        Propagated from ``build_bundle()`` (step 1) if ``run_id`` does not
        correspond to an existing run.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)

    # ORC-005: advisory per-run dispatch lock (D2, locked). This is
    # informational only — it is never read back to gate/reject a concurrent
    # invocation; it exists so an overlapping call for the same run_id is
    # visible/inspectable after the fact (both invocations still complete and
    # both still get audited in Phase 2). Always overwrite (last-write-wins);
    # no branch here ever returns/raises because a lock file already exists.
    # _DISPATCH_LOCK_TTL_SECONDS is informational metadata only — real
    # TTL-expiry enforcement is out of scope for Phase 1 per D2.
    try:
        dump_yaml(
            {
                "acquired_at": now_iso(),
                "approver_identity": approver_identity,
                "ttl_seconds": _DISPATCH_LOCK_TTL_SECONDS,
            },
            rp.run / ".dispatch.lock",
        )
    except Exception:
        # Lock-file I/O is advisory only and must never break orchestration.
        pass

    # Step 1: build + verify the evidence bundle.
    bundle_result = build_bundle(run_id, verify=True, paths=paths)

    # Step 2: council review is ALWAYS run (D1, locked — never conditionally
    # skipped). Read back the written packet for the decision + concerns.
    council_review(
        run_id,
        roles=["critic", "domain_reviewer", "governance_officer", "executive_translator"],
        paths=paths,
    )
    council_packet = _safe_load(rp.council_review) or {}
    output = council_packet.get("output") if isinstance(council_packet.get("output"), dict) else {}
    council_decision = str(output.get("decision") or "approve")
    concerns = output.get("concerns") if isinstance(output.get("concerns"), list) else []
    reviewer_notes = str(council_packet.get("reviewer_notes") or "")
    required_fix: str | None = None
    for concern in concerns:
        if isinstance(concern, dict) and concern.get("required_fix"):
            required_fix = str(concern["required_fix"])
            break

    # Step 3: governance guard check.
    ctx = governance.load_run_context(run_id, writeback_targets=targets, paths=paths)
    guard_result = governance.guard_check(ctx, paths=paths)

    # Combined gate (ORC-002): both the guard AND the council decision must
    # clear before any target dispatch is attempted.
    gate_passed = guard_result.passed and council_decision != "required_block"

    if not gate_passed:
        return ApproveDispatchResult(
            bundle_id=bundle_result.bundle_id,
            verified=bundle_result.verified,
            council_decision=council_decision,
            reviewer_notes=reviewer_notes,
            required_fix=required_fix,
            guard_result=guard_result,
            target_status={target: "skipped" for target in targets},
            overall_status="blocked",
        )

    # Step 4 (ORC-003): per-target isolated dispatch. Fixed order:
    # ccdash -> meatywiki -> skillmeat, regardless of `targets` tuple order —
    # matches writeback()'s existing target-check order. Each call is
    # independently wrapped in its own try/except so one target's exception
    # never prevents the other two from being attempted (PRD FR-7).
    sensitivity = _sensitivity(rp)
    ledger = _ledger(rp)
    requires_review = sensitivity in _WORK_SENSITIVITIES

    target_status: dict[str, str] = {}
    ccdash_event_id_value = ""

    if "ccdash" in targets:
        try:
            ccdash_event_id_value = str(telemetry.emit_ccdash_event(run_id, paths=paths) or "")
            target_status["ccdash"] = "success"
        except Exception:
            target_status["ccdash"] = "failed"
    else:
        target_status["ccdash"] = "skipped"

    if "meatywiki" in targets:
        try:
            _render_meatywiki(
                rp,
                paths,
                bundle_ident=bundle_result.bundle_id,
                sensitivity=sensitivity,
                ledger=ledger,
                requires_review=requires_review,
            )
            target_status["meatywiki"] = "success"
        except Exception:
            target_status["meatywiki"] = "failed"
    else:
        target_status["meatywiki"] = "skipped"

    if "skillmeat" in targets:
        try:
            _render_skillbom(
                rp,
                paths,
                bundle_ident=bundle_result.bundle_id,
                ccdash_event_id_value=ccdash_event_id_value,
                requires_review=requires_review,
                ledger=ledger,
            )
            target_status["skillmeat"] = "success"
        except Exception:
            target_status["skillmeat"] = "failed"
    else:
        target_status["skillmeat"] = "skipped"

    # ORC-004: populate evidence_bundle.governance.approved_by/
    # approval_timestamp now that the gate passed and dispatch was attempted.
    # approver_identity may legitimately be None (loopback/no-auth mode) —
    # the write still happens so approval_timestamp reflects this invocation.
    bundle_doc = _safe_load(rp.evidence_bundle)
    if isinstance(bundle_doc, dict):
        governance_block = dict(bundle_doc.get("governance") or {})
        governance_block["approved_by"] = approver_identity
        governance_block["approval_timestamp"] = now_iso()
        bundle_doc["governance"] = governance_block
        dump_yaml(bundle_doc, rp.evidence_bundle)

    # ORC-005's lock file was written at function entry (see top of this
    # function) and is intentionally left in place here — on every return
    # path (blocked/success/partial) — as an audit trail of the most recent
    # dispatch attempt for this run, rather than adding cleanup logic to the
    # multiple return statements in this function.

    requested_statuses = [target_status[target] for target in targets]
    overall_status = (
        "success" if all(status == "success" for status in requested_statuses) else "partial"
    )

    return ApproveDispatchResult(
        bundle_id=bundle_result.bundle_id,
        verified=bundle_result.verified,
        council_decision=council_decision,
        reviewer_notes=reviewer_notes,
        required_fix=required_fix,
        guard_result=guard_result,
        target_status=target_status,
        overall_status=overall_status,
    )


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
    "GovernedWritebackResult",
    "governed_writeback",
    "council_review",
    "skillbom_propose",
    "skillbom_promote",
    "_render_decision_record",
    "_render_intenttree_update",
    "_render_arc_council",
    "_render_notebooklm_update",
]
