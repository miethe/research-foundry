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
import tempfile
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..errors import ExitCode, RFError
from ..frontmatter import split_frontmatter
from ..paths import FoundryPaths, RunPaths
from ..yamlio import loads_yaml

EXPORT_SCHEMA_VERSION = "1.1"

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
    governance = bundle.get("governance") or {}
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

    # Read report_draft once; use it for both title derivation and the export field.
    report_draft = _read_report_draft(rp)

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
            }
        )
    return summaries


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
    "_title_from_slug",
    "_extract_title_from_report_draft",
    "_derive_run_title",
]
