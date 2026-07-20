"""Telemetry / CCDash emission service (contract §10).

Builds a deterministic ``execution_event`` (spec §6.15) from a run's artifacts
and mirrors it into the workspace-level ``ccdash/`` tree, then aggregates events
into daily + period rollups. No network or API keys are required: every value is
derived from on-disk artifacts.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

from ..ids import ccdash_event_id, disambiguate_id, now_iso, today_compact
from ..paths import FoundryPaths
from ..schemas import default_registry, validate
from ..yamlio import append_jsonl, dump_yaml, load_yaml

_REGISTRY = default_registry()

# Sensitivity -> key profile that would have been used at runtime (spec §7.1).
_KEY_PROFILE_BY_SENSITIVITY = {
    "public": "personal",
    "personal": "personal",
    "work_sensitive": "work_approved",
    "client_sensitive": "client_approved",
}

_DEFAULT_TOOLS = ["claude_code", "claude_agent_sdk", "gpt_researcher", "paperqa2", "litellm"]
_DEFAULT_POSTURES = ["researcher", "critic", "synthesizer", "operator"]


def _trace(run_paths, stage: str, **extra: Any) -> None:
    """Best-effort append to ``telemetry/run_trace.jsonl`` (never fails the stage)."""

    try:
        append_jsonl({"stage": stage, "ts": now_iso(), **extra}, run_paths.run_trace)
    except Exception:  # noqa: BLE001 - tracing is best-effort
        pass


def _safe_load(path: Path) -> Any:
    try:
        return load_yaml(path)
    except FileNotFoundError:
        return None


def _run_meta(run_paths) -> dict[str, Any]:
    return _safe_load(run_paths.run_yaml) or {}


def _ledger_counts(run_paths) -> dict[str, int]:
    """Status counts from the run's claim ledger (zeros when absent)."""

    ledger = _safe_load(run_paths.claim_ledger) or {}
    claims = ledger.get("claims") or []
    # Count all six schema-valid statuses so the per-status metrics sum to
    # claims_total (mixed/contradicted were previously dropped).
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
        status = (claim or {}).get("status")
        key = f"claims_{status}"
        if key in counts:
            counts[key] += 1
    return counts


def _count_files(directory: Path, *patterns: str) -> int:
    if not directory.exists():
        return 0
    total = 0
    for pattern in patterns or ("*",):
        total += sum(1 for p in directory.glob(pattern) if p.is_file())
    return total


def _verification(run_paths) -> dict[str, Any]:
    return _safe_load(run_paths.verification) or {}


def _sensitivity_for_run(run_paths) -> str:
    """Resolve run sensitivity from report front matter or run.yaml (default personal)."""

    for report in (run_paths.report_final, run_paths.report_draft):
        if report.exists():
            from ..frontmatter import load_md

            meta, _ = load_md(report)
            sens = meta.get("sensitivity")
            if sens:
                return str(sens)
    meta = _run_meta(run_paths)
    return str(meta.get("sensitivity") or "personal")


def _tools_and_postures(run_paths) -> tuple[list[str], list[str]]:
    """Pull tool + posture lists from swarm_plan / routing_decision when present."""

    tools: list[str] = []
    postures: list[str] = []
    swarm = _safe_load(run_paths.swarm_plan) or {}
    routing = _safe_load(run_paths.routing_decision) or {}
    for agent in swarm.get("agents", []) or []:
        posture = (agent or {}).get("posture")
        if posture and posture not in postures:
            postures.append(posture)
    for key in ("selected_tools", "tools"):
        vals = routing.get(key)
        if isinstance(vals, list):
            for tool in vals:
                if tool and tool not in tools:
                    tools.append(tool)
    return (tools or list(_DEFAULT_TOOLS), postures or list(_DEFAULT_POSTURES))


def emit_ccdash_event(
    run_id: str,
    *,
    paths: FoundryPaths | None = None,
    raw_key: str = "",
    search_metrics: dict[str, Any] | None = None,
) -> str:
    """Build + write the run's CCDash ``execution_event`` (spec §6.15).

    Writes ``runs/<run>/writebacks/ccdash_event.yaml`` and mirrors it into
    ``ccdash/events/<event_id>.yaml``. Validates against ``ccdash_event``.
    Returns the minted ``event_id``.

    *raw_key* is optional: when supplied the ``governance.key_fingerprint``
    field is populated via :func:`make_key_fingerprint`.

    *search_metrics* is optional: when supplied, its keys are merged into the
    emitted event's ``metrics`` (additive, search-router-specific fields —
    see ``schemas/ccdash_event.schema.yaml``). Non-search callers omit it and
    the event shape is unchanged.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    rp.writebacks.mkdir(parents=True, exist_ok=True)

    meta = _run_meta(rp)
    intent_id = str(meta.get("intent_id") or "")
    task_node_id = str(meta.get("task_node_id") or meta.get("intenttree_node_id") or "")

    counts = _ledger_counts(rp)
    source_cards_created = _count_files(rp.sources, "*.md")
    verification = _verification(rp)
    verification_passed = bool(verification.get("passed", False))

    tools, postures = _tools_and_postures(rp)
    sensitivity = _sensitivity_for_run(rp)
    key_profile_used = _KEY_PROFILE_BY_SENSITIVITY.get(sensitivity, "personal")
    requires_review = sensitivity in {"work_sensitive", "client_sensitive"}

    # Disambiguate on actual collision only: ccdash_event_id re-truncates the
    # intent slug to 6 words, so two distinct runs sharing a slug would mint the
    # same event id and overwrite each other's mirror. An existing mirror for the
    # SAME run is a re-emit (id stays stable); a different run's mirror collides.
    def _event_id_taken(candidate: str) -> bool:
        mirror = paths.ccdash / "events" / f"{candidate}.yaml"
        if not mirror.exists():
            return False
        existing = _safe_load(mirror)
        return isinstance(existing, dict) and existing.get("run_id") != run_id

    event_id = disambiguate_id(
        ccdash_event_id(intent_id or run_id),
        seed=run_id,
        exists=_event_id_taken,
    )
    event: dict[str, Any] = {
        "event_id": event_id,
        "timestamp": now_iso(),
        "project": "Research Foundry",
        "intent_id": intent_id,
        "task_node_id": task_node_id,
        "run_id": run_id,
        "agent_postures": postures,
        "skillbom_ids": ["skill_research_swarm_v0"],
        "tools": tools,
        "input_artifacts": [
            "inbox/raw_ideas/raw_*.md",
            "intents/active/intent_*.yaml",
        ],
        "output_artifacts": [
            f"runs/{run_id}/evidence_bundle.yaml",
            f"runs/{run_id}/reports/report_final.md",
            f"runs/{run_id}/writebacks/meatywiki_writeback.md",
            f"runs/{run_id}/writebacks/skillbom_candidate.md",
        ],
        "metrics": {
            "source_cards_created": source_cards_created,
            "claims_total": counts["claims_total"],
            "claims_supported": counts["claims_supported"],
            "claims_mixed": counts["claims_mixed"],
            "claims_contradicted": counts["claims_contradicted"],
            "claims_inference": counts["claims_inference"],
            "claims_speculation": counts["claims_speculation"],
            "unsupported_claims": counts["claims_unsupported"],
            "verification_passed": verification_passed,
            "tokens_estimated": 0,
            "cost_estimated_usd": 0.0,
            "latency_minutes": 0.0,
            "rework_count": 0,
            "drift_score": 0.0,
            "quality_score": "pending",
        },
        "governance": {
            "sensitivity": sensitivity,
            "key_profile_used": key_profile_used,
            "key_fingerprint": make_key_fingerprint(raw_key) if raw_key else "",
            "policy_passed": verification_passed,
            "violations": [],
        },
        "reuse": {
            "meatywiki_writeback_candidate": True,
            "skillbom_candidate": True,
            "reusable_source_pack_candidate": source_cards_created > 0,
        },
        "human_review": {
            "required": requires_review,
            "status": "pending" if requires_review else "not_required",
            "reviewer": None,
        },
    }

    if search_metrics:
        event["metrics"].update(search_metrics)

    if _REGISTRY.has("ccdash_event"):
        result = validate(event, "ccdash_event")
        if not result.ok:
            from ..errors import SchemaError

            raise SchemaError("ccdash_event invalid: " + "; ".join(result.errors))

    dump_yaml(event, rp.ccdash_event)
    mirror = paths.ccdash / "events" / f"{event_id}.yaml"
    dump_yaml(event, mirror)
    _trace(rp, "ccdash_event", run_id=run_id, event_id=event_id)
    return event_id


def emit_latest_or_noop(*, paths: FoundryPaths | None = None) -> str | None:
    """Stop-hook helper: emit a CCDash event for the most-recent run, else no-op.

    Safe to call outside a foundry workspace: if no runs exist (or the workspace
    is absent) it returns ``None`` without raising. Returns the minted
    ``event_id`` on success (see :func:`emit_ccdash_event`).
    """

    try:
        paths = paths or FoundryPaths.discover()
    except Exception:  # noqa: BLE001
        return None
    runs_dir = paths.runs
    if not runs_dir.exists():
        return None
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    if not run_dirs:
        return None
    latest = max(run_dirs, key=lambda d: d.stat().st_mtime)
    try:
        return emit_ccdash_event(latest.name, paths=paths)
    except Exception:  # noqa: BLE001 - hook must never break the host process
        return None


@dataclass(frozen=True)
class _Rollup:
    runs: int
    claims_total: int
    unsupported: int
    cost_estimated_usd: float
    verification_pass_rate: float
    meatywiki_candidates: int
    skillbom_candidates: int


def _aggregate_events(events: list[dict[str, Any]]) -> _Rollup:
    runs = len(events)
    claims_total = 0
    unsupported = 0
    cost = 0.0
    passed = 0
    mwb = 0
    skb = 0
    for ev in events:
        metrics = ev.get("metrics") or {}
        claims_total += int(metrics.get("claims_total") or 0)
        unsupported += int(metrics.get("unsupported_claims") or 0)
        cost += float(metrics.get("cost_estimated_usd") or 0.0)
        if metrics.get("verification_passed"):
            passed += 1
        reuse = ev.get("reuse") or {}
        if reuse.get("meatywiki_writeback_candidate"):
            mwb += 1
        if reuse.get("skillbom_candidate"):
            skb += 1
    pass_rate = round(passed / runs, 4) if runs else 0.0
    return _Rollup(
        runs=runs,
        claims_total=claims_total,
        unsupported=unsupported,
        cost_estimated_usd=round(cost, 4),
        verification_pass_rate=pass_rate,
        meatywiki_candidates=mwb,
        skillbom_candidates=skb,
    )


def summarize(period: str = "daily", *, paths: FoundryPaths | None = None) -> Path:
    """Aggregate ``ccdash/events/*.yaml`` into a daily rollup + period summary.

    Writes ``ccdash/daily/<date>.yaml`` and ``ccdash/summaries/<period>_<date>.yaml``
    and returns the period-summary path. Empty event sets produce a zeroed rollup.
    """

    paths = paths or FoundryPaths.discover()
    events_dir = paths.ccdash / "events"
    events: list[dict[str, Any]] = []
    if events_dir.exists():
        for p in sorted(events_dir.glob("*.yaml")):
            data = _safe_load(p)
            if isinstance(data, dict):
                events.append(data)

    date = today_compact()
    rollup = _aggregate_events(events)
    body = {
        "period": period,
        "date": date,
        "generated_at": now_iso(),
        "totals": {
            "runs": rollup.runs,
            "claims_total": rollup.claims_total,
            "unsupported_claims": rollup.unsupported,
            "cost_estimated_usd": rollup.cost_estimated_usd,
            "verification_pass_rate": rollup.verification_pass_rate,
        },
        "reuse_candidates": {
            "meatywiki_writebacks": rollup.meatywiki_candidates,
            "skillbom_candidates": rollup.skillbom_candidates,
        },
        "event_ids": [ev.get("event_id") for ev in events if ev.get("event_id")],
    }

    daily_path = paths.ccdash / "daily" / f"{date}.yaml"
    dump_yaml(body, daily_path)
    summary_path = paths.ccdash / "summaries" / f"{period}_{date}.yaml"
    dump_yaml(body, summary_path)
    return summary_path


def provider_scorecard(*, paths: FoundryPaths | None = None) -> Path:
    """Aggregate per-provider search metrics across ``ccdash/events/*.yaml``.

    Sibling to :func:`summarize` (spec §17 provider scorecard, Wave 3 TASK-3.2).
    Reads each event's ``metrics.providers`` — the per-provider breakdown
    populated by ``search_router.router.run_search`` (queries/cost/duplicate
    rate per discovery provider, extraction attempts/failure-rate for the
    run's extractor) — and rolls it up per provider across every event on
    disk: summed ``queries_executed``/``estimated_cost_usd``/
    ``extraction_attempts``, mean ``duplicate_rate``/``extraction_failure_rate``.

    Events without a ``providers`` breakdown (non-search runs, or search runs
    that predate this rollup) are silently skipped — this is additive and
    never requires a schema change (``metrics`` is ``additionalProperties``).
    Never raises; malformed entries are skipped rather than failing the whole
    rollup.

    Writes ``ccdash/summaries/provider_scorecard.yaml`` and returns its path.
    An empty/no-provider-data input still writes a file with an empty
    ``providers`` map (deterministic, always-succeeds contract).
    """

    paths = paths or FoundryPaths.discover()
    events_dir = paths.ccdash / "events"

    per_provider: dict[str, dict[str, Any]] = {}
    if events_dir.exists():
        for p in sorted(events_dir.glob("*.yaml")):
            event = _safe_load(p)
            if not isinstance(event, dict):
                continue
            providers = (event.get("metrics") or {}).get("providers")
            if not isinstance(providers, dict):
                continue
            for pid, stat in providers.items():
                if not isinstance(stat, dict):
                    continue
                agg = per_provider.setdefault(
                    pid,
                    {
                        "runs": 0,
                        "queries_executed": 0,
                        "estimated_cost_usd": 0.0,
                        "extraction_attempts": 0,
                        "_dup_sum": 0.0,
                        "_dup_n": 0,
                        "_fail_sum": 0.0,
                        "_fail_n": 0,
                    },
                )
                agg["runs"] += 1
                agg["queries_executed"] += int(stat.get("queries_executed") or 0)
                agg["estimated_cost_usd"] += float(stat.get("estimated_cost_usd") or 0.0)
                agg["extraction_attempts"] += int(stat.get("extraction_attempts") or 0)
                dup = stat.get("duplicate_rate")
                if isinstance(dup, (int, float)):
                    agg["_dup_sum"] += float(dup)
                    agg["_dup_n"] += 1
                fail = stat.get("extraction_failure_rate")
                if isinstance(fail, (int, float)):
                    agg["_fail_sum"] += float(fail)
                    agg["_fail_n"] += 1

    providers_out: dict[str, dict[str, Any]] = {}
    for pid, agg in per_provider.items():
        dup_n = agg["_dup_n"]
        fail_n = agg["_fail_n"]
        providers_out[pid] = {
            "runs": agg["runs"],
            "queries_executed": agg["queries_executed"],
            "estimated_cost_usd": round(agg["estimated_cost_usd"], 6),
            "duplicate_rate_mean": round(agg["_dup_sum"] / dup_n, 4) if dup_n else None,
            "extraction_attempts": agg["extraction_attempts"],
            "extraction_failure_rate_mean": (
                round(agg["_fail_sum"] / fail_n, 4) if fail_n else None
            ),
        }

    body = {
        "generated_at": now_iso(),
        "providers": dict(sorted(providers_out.items())),
    }
    scorecard_path = paths.ccdash / "summaries" / "provider_scorecard.yaml"
    dump_yaml(body, scorecard_path)
    return scorecard_path


# NOT FOR PRODUCTION — override via RF_KEY_PROFILE_PEPPER env var in production deployments.
_INTERIM_PEPPER = "rf-interim-pepper-v1"


def make_key_fingerprint(raw_key: str, *, pepper: str = "") -> str:
    """Return a 12-hex-char salted HMAC-SHA256 fingerprint of *raw_key*.

    The pepper is resolved in order: explicit *pepper* kwarg → ``RF_KEY_PROFILE_PEPPER``
    environment variable → hard-coded interim value (NOT FOR PRODUCTION).
    """
    effective_pepper = pepper or os.environ.get("RF_KEY_PROFILE_PEPPER") or ""
    if not effective_pepper:
        _logger.warning(
            "SECURITY: RF_KEY_PROFILE_PEPPER not set; using NON-PRODUCTION interim pepper. "
            "Set RF_KEY_PROFILE_PEPPER before any non-loopback deployment (P5)."
        )
        effective_pepper = _INTERIM_PEPPER
    digest = hmac.new(
        effective_pepper.encode(),
        msg=raw_key.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return digest[:12]


def make_agent_job_telemetry_record(
    job_id: str,
    key_profile: str,
    raw_key: str,
) -> dict[str, Any]:
    """Build a minimal agent-job run-start telemetry record.

    Returns a dict with ``job_id``, ``key_profile_used``, ``key_fingerprint``,
    and ``timestamp``.  Callers may extend with additional fields.
    """
    return {
        "job_id": job_id,
        "key_profile_used": key_profile,
        "key_fingerprint": make_key_fingerprint(raw_key),
        "timestamp": now_iso(),
    }


_MILESTONE_STAGES = frozenset({
    "discovery_started",
    "sources_ingested",
    "verify_passed",
    "bundle_written",
})


def push_status(
    run_id: str,
    stage: str,
    *,
    paths: FoundryPaths | None = None,
) -> bool:
    """Best-effort PATCH of IntentTree node progress at milestone stages.

    Only fires at the four defined milestone stages
    (``discovery_started``, ``sources_ingested``, ``verify_passed``,
    ``bundle_written``). No-ops silently for any other stage. Returns ``True``
    when the push succeeded, ``False`` when offline, skipped, or errored.
    Never raises.
    """

    if stage not in _MILESTONE_STAGES:
        return False

    try:
        paths = paths or FoundryPaths.discover()
        rp = paths.run_paths(run_id)

        # Resolve node_id from run.yaml → intent.
        meta = _run_meta(rp)
        intent_id = str(meta.get("intent_id") or "")
        node_id = str(meta.get("task_node_id") or meta.get("intenttree_node_id") or "")
        if not node_id and intent_id:
            # Try loading from the active intent.
            intent_path = paths.intents_active / f"{intent_id}.yaml"
            if intent_path.exists():
                intent = _safe_load(intent_path) or {}
                node_id = str(intent.get("intenttree_node_ref") or "")

        if not node_id:
            return False

        from ..integrations.intenttree import IntentTreeClient

        client = IntentTreeClient.from_config()
        if not client.available():
            return False

        payload = {
            "progress_stage": stage,
            "run_id": run_id,
            "timestamp": now_iso(),
        }
        result = client.patch_node(node_id, payload)
        _trace(rp, f"status_push_{stage}", run_id=run_id, node_id=node_id, pushed=result is not None)
        return result is not None
    except Exception:  # noqa: BLE001 — best-effort, never fail pipeline
        return False


__all__ = [
    "emit_ccdash_event",
    "emit_latest_or_noop",
    "make_agent_job_telemetry_record",
    "make_key_fingerprint",
    "provider_scorecard",
    "push_status",
    "summarize",
]
