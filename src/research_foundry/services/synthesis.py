"""Deterministic report synthesis from a run's claim ledger (spec §6.12).

``synthesize_report`` reads ``claims/claim_ledger.yaml`` and writes a Markdown
report whose body cites **only** claim ids present in the ledger. This is the
discipline that guarantees ``rf verify`` returns 0 on the happy path: every
material sentence ends with a ``[claim:<id>]`` tag, and every inference /
speculation sentence carries its required label.

The default path is fully deterministic — no network, no API keys. ``llm=True``
opts into the ``claude_agent_sdk`` adapter; if it is unavailable or degraded the
function falls back to the deterministic body and records a note in the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..frontmatter import dump_md, load_md
from ..ids import now_iso, report_id, slugify
from ..paths import FoundryPaths
from ..registry import REPORT_INDEX, Registry
from ..schemas import default_registry, validate
from ..yamlio import append_jsonl, load_yaml

# The standard claim_policy text carried in report front matter (spec §6.12).
_CLAIM_POLICY_TEXT = (
    "Every material claim maps to claim_ledger.yaml or is labeled "
    "inference/speculation."
)


@dataclass(frozen=True)
class SynthResult:
    """Outcome of synthesizing a report from a claim ledger."""

    run_id: str
    report_path: Path
    claims_cited: list[str]


def _load_ledger(rp, claim_ledger_path: Path | None) -> dict[str, Any]:
    path = Path(claim_ledger_path) if claim_ledger_path else rp.claim_ledger
    if not path.exists():
        return {"claims": [], "unresolved_questions": []}
    data = load_yaml(path)
    return data if isinstance(data, dict) else {"claims": [], "unresolved_questions": []}


def _load_intent(intent_id: str | None, paths: FoundryPaths) -> dict[str, Any]:
    if not intent_id:
        return {}
    candidate = paths.intents_active / f"{intent_id}.yaml"
    if candidate.exists():
        data = load_yaml(candidate)
        return data if isinstance(data, dict) else {}
    # Fall back to a recursive search under intents/.
    for p in paths.intents.rglob(f"{intent_id}.yaml"):
        data = load_yaml(p)
        return data if isinstance(data, dict) else {}
    return {}


def _source_card_title(rp, source_card_id: str) -> str | None:
    """Resolve a source card's display title from its Markdown file, if present."""

    sources_dir = rp.sources
    if not sources_dir.exists():
        return None
    for p in sorted(sources_dir.glob("*.md")):
        try:
            meta, _ = load_md(p)
        except Exception:  # noqa: BLE001 - never fail synthesis on a bad card
            continue
        if meta.get("source_card_id") == source_card_id:
            src = meta.get("source", {}) if isinstance(meta.get("source"), dict) else {}
            return src.get("title") or source_card_id
    return None


def _cited_source_ids(claims: list[dict[str, Any]]) -> list[str]:
    """All source_card_ids referenced by any claim, in first-seen order."""

    seen: list[str] = []
    for claim in claims:
        for src in claim.get("sources", []) or []:
            sid = src.get("source_card_id")
            if sid and sid not in seen:
                seen.append(sid)
    return seen


def _sentence(text: str) -> str:
    """Normalize claim text into a single sentence ending in a period."""

    t = " ".join((text or "").split()).strip()
    if not t:
        return ""
    if t[-1] not in ".!?":
        t += "."
    return t


def _build_body(
    rp,
    claims: list[dict[str, Any]],
    unresolved: list[dict[str, Any]],
    cited_source_ids: list[str],
) -> tuple[str, list[str]]:
    """Render the deterministic report body; return (markdown, claims_cited)."""

    cited: list[str] = []
    findings: list[str] = []
    inferences: list[str] = []
    speculations: list[str] = []

    for claim in claims:
        cid = claim.get("claim_id")
        status = claim.get("status")
        sentence = _sentence(claim.get("text", ""))
        if not cid or not sentence:
            continue
        if status == "supported":
            findings.append(f"{sentence} [claim:{cid}]")
            cited.append(cid)
        elif status == "inference":
            inferences.append(f"**Inference:** {sentence} [claim:{cid}]")
            cited.append(cid)
        elif status == "speculation":
            speculations.append(f"**Speculation:** {sentence} [claim:{cid}]")
            cited.append(cid)
        elif status == "mixed":
            findings.append(f"**Mixed evidence:** {sentence} [claim:{cid}]")
            cited.append(cid)
        elif status == "contradicted":
            findings.append(
                f"**Contradicted / do not use as finding:** {sentence} [claim:{cid}]"
            )
            cited.append(cid)
        # 'unsupported' claims are intentionally NOT rendered into the body:
        # they have no source and no label, so emitting them would create an
        # unsupported material sentence. The verifier flags them via the ledger.

    lines: list[str] = []
    lines.append("## Findings")
    lines.append("")
    if findings:
        lines.extend(findings)
    else:
        # Editorial placeholder for an empty section: wrapped in a single emphasis
        # marker so the verifier treats it as a note, not an untagged claim.
        lines.append("*No supported findings were established for this run.*")
    lines.append("")

    lines.append("## Inferences")
    lines.append("")
    if inferences:
        lines.extend(inferences)
    else:
        lines.append("*No analytic inferences were drawn for this run.*")
    lines.append("")

    lines.append("## Speculation")
    lines.append("")
    if speculations:
        lines.extend(speculations)
    else:
        lines.append("*No speculation was recorded for this run.*")
    lines.append("")

    lines.append("## Open questions")
    lines.append("")
    if unresolved:
        for q in unresolved:
            question = (q.get("question") or "").strip() if isinstance(q, dict) else str(q)
            if question:
                lines.append(f"- {question}")
    else:
        lines.append("- None recorded.")
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    if cited_source_ids:
        for sid in cited_source_ids:
            title = _source_card_title(rp, sid)
            if title and title != sid:
                lines.append(f"- {sid}: {title}")
            else:
                lines.append(f"- {sid}")
    else:
        lines.append("- No source cards were cited.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n", cited


def _maybe_llm_note(llm: bool) -> str | None:
    """Return a degradation note if llm was requested but unavailable."""

    if not llm:
        return None
    try:
        from ..adapters import get_adapter, load_all

        load_all()
        adapter = get_adapter("claude_agent_sdk")
    except Exception:  # noqa: BLE001 - adapters must never break synthesis
        adapter = None
    if adapter is None:
        return "LLM synthesis requested but claude_agent_sdk adapter is unavailable; used deterministic synthesis."
    try:
        if not adapter.available():
            return "LLM synthesis requested but claude_agent_sdk adapter is degraded; used deterministic synthesis."
    except Exception:  # noqa: BLE001
        return "LLM synthesis requested but claude_agent_sdk adapter probe failed; used deterministic synthesis."
    # Even when "available", the MVP deterministic body is authoritative: the LLM
    # path may not introduce untagged material claims. Note that we kept it.
    return "LLM synthesis adapter available; deterministic ledger-faithful body retained for verifier compliance."


def _trace(rp, **fields: Any) -> None:
    try:
        append_jsonl({"ts": now_iso(), **fields}, rp.run_trace)
    except Exception:  # noqa: BLE001 - tracing is best-effort
        pass


def synthesize_report(
    run_id: str,
    *,
    model_profile: str = "rf_synthesize_deep",
    final: bool = False,
    audience: str | None = None,
    sensitivity: str | None = None,
    llm: bool = False,
    paths: FoundryPaths | None = None,
) -> SynthResult:
    """Write a report Markdown file from the run's claim ledger (deterministic).

    The body cites only ledger claim ids and labels inference/speculation per
    spec §6.12 so that :func:`verify_report` returns exit code 0 on this path.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    ledger = _load_ledger(rp, None)
    claims = list(ledger.get("claims", []) or [])
    unresolved = list(ledger.get("unresolved_questions", []) or [])
    intent_id = ledger.get("intent_id")

    intent = _load_intent(intent_id, paths)
    # audience/sensitivity default from the linked intent, then safe defaults.
    intent_gov = intent.get("governance", {}) if isinstance(intent, dict) else {}
    intent_audience = None
    if isinstance(intent, dict):
        out = intent.get("output", {})
        if isinstance(out, dict):
            intent_audience = out.get("audience")
    resolved_audience = audience or intent_audience or "self"
    resolved_sensitivity = (
        sensitivity
        or (intent_gov.get("sensitivity") if isinstance(intent_gov, dict) else None)
        or "personal"
    )

    cited_source_ids = _cited_source_ids(claims)
    body, claims_cited = _build_body(rp, claims, unresolved, cited_source_ids)

    note = _maybe_llm_note(llm)
    if note:
        body = body.rstrip() + f"\n\n<!-- synthesis-note: {note} -->\n"

    title_seed = (
        intent.get("title")
        if isinstance(intent, dict) and intent.get("title")
        else f"Research report for {run_id}"
    )
    rid = report_id(slugify(str(title_seed)))

    front: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "research_report",
        "report_id": rid,
        "title": str(title_seed),
        "intent_id": intent_id or "",
        "evidence_bundle_id": "pending",
        "created_at": now_iso(),
        "status": "draft",
        "audience": resolved_audience,
        "sensitivity": resolved_sensitivity,
        "claim_policy": _CLAIM_POLICY_TEXT,
        "verification_status": "pending",
    }

    report_path = rp.report_final if final else rp.report_draft
    dump_md(front, body, report_path)

    # Validate the written front matter against report_frontmatter (skip if absent).
    if default_registry().has("report_frontmatter"):
        result = validate(front, "report_frontmatter")
        if not result.ok:
            from ..errors import SchemaError

            raise SchemaError(
                "report front matter failed validation: " + "; ".join(result.errors)
            )

    # Index the report (best-effort; never fail synthesis on a registry error).
    try:
        Registry.open(REPORT_INDEX, paths=paths).upsert(
            {
                "id": rid,
                "run_id": run_id,
                "intent_id": intent_id,
                "path": str(report_path),
                "status": "draft",
                "verification_status": "pending",
            }
        )
    except Exception:  # noqa: BLE001
        pass

    _trace(rp, stage="synthesize", run_id=run_id, report_id=rid, claims_cited=len(claims_cited))

    return SynthResult(run_id=run_id, report_path=report_path, claims_cited=claims_cited)


__all__ = ["SynthResult", "synthesize_report"]
