"""Workspace lifecycle service — ``rf init`` and ``rf redact``.

``init_workspace`` scaffolds the spec §5 folder substrate at a target path and
copies the canonical ``foundry.yaml``, ``schemas/``, ``config/``, and
``templates/`` from the installed distribution (idempotent). ``redact_run``
produces a target-audience-redacted copy of a run's report, masking claims whose
cited source cards are work/client-sensitive. Both paths are deterministic and
network-free.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import NotFoundError
from ..frontmatter import dump_md, load_md
from ..ids import now_iso
from ..paths import FoundryPaths, RunPaths, distribution_root
from ..yamlio import load_yaml

# Spec §5 folder substrate. Each leaf gets a ``.gitkeep`` so the empty tree is
# committable. Mirrors the conftest ``_SUBSTRATE`` plus a few top-level dirs.
_SUBSTRATE: tuple[str, ...] = (
    "config",
    "schemas",
    "templates",
    "inbox/raw_ideas",
    "inbox/clips",
    "intents/active",
    "iboms/active",
    "intenttree/nodes",
    "runs",
    "registries",
    "meatywiki/sources",
    "meatywiki/concepts",
    "meatywiki/decisions",
    "meatywiki/patterns",
    "skillmeat/skillboms",
    "ccdash/events",
    "ccdash/daily",
    "ccdash/summaries",
)

# Distribution assets copied into a fresh workspace if not already present.
_COPY_DIRS: tuple[str, ...] = ("schemas", "config", "templates")
_COPY_FILES: tuple[str, ...] = ("foundry.yaml", ".gitignore", ".env.example")

_WORK_SENSITIVITIES = {"work_sensitive", "client_sensitive"}
_CLAIM_CITE = re.compile(r"\[claim:([A-Za-z0-9_\-]+)\]")


@dataclass(frozen=True)
class InitResult:
    """Outcome of :func:`init_workspace`."""

    root: Path
    created_dirs: list[str] = field(default_factory=list)
    copied: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)


def init_workspace(
    target: str | Path = ".",
    *,
    profile: str = "personal",  # accepted for spec compat; not persisted here
    distribution: Path | None = None,
) -> InitResult:
    """Initialize a new foundry workspace at ``target`` (idempotent).

    Creates the spec §5 folder substrate (with ``.gitkeep`` markers) and copies
    the canonical ``foundry.yaml`` + ``schemas/``/``config/``/``templates/`` from
    the distribution when they are not already present. Re-running on an existing
    workspace is a no-op for files that already exist.
    """

    root = Path(target).resolve()
    root.mkdir(parents=True, exist_ok=True)
    dist = Path(distribution) if distribution else distribution_root()

    created: list[str] = []
    copied: list[str] = []
    present: list[str] = []

    for sub in _SUBSTRATE:
        d = root / sub
        existed = d.exists()
        d.mkdir(parents=True, exist_ok=True)
        if not existed:
            created.append(sub)
        keep = d / ".gitkeep"
        if not keep.exists() and not any(d.iterdir()):
            keep.write_text("", encoding="utf-8")

    for name in _COPY_DIRS:
        src = dist / name
        dst = root / name
        if not src.exists():
            continue
        if _dir_has_content(dst):
            present.append(name)
            continue
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)

    for name in _COPY_FILES:
        src = dist / name
        dst = root / name
        if dst.exists():
            present.append(name)
            continue
        if src.exists():
            shutil.copyfile(src, dst)
            copied.append(name)

    return InitResult(
        root=root,
        created_dirs=created,
        copied=copied,
        already_present=present,
    )


def _dir_has_content(d: Path) -> bool:
    """True if ``d`` exists and holds at least one non-``.gitkeep`` entry."""

    if not d.exists():
        return False
    for child in d.iterdir():
        if child.name != ".gitkeep":
            return True
    return False


# --- redaction -------------------------------------------------------------


@dataclass(frozen=True)
class RedactResult:
    """Outcome of :func:`redact_run`."""

    run_id: str
    target: str
    source_report: Path
    redacted_path: Path
    redacted_claims: list[str] = field(default_factory=list)


def redact_run(
    run_id: str,
    *,
    target: str = "public",
    paths: FoundryPaths | None = None,
) -> RedactResult:
    """Write a redacted copy of a run's report for the given ``target`` audience.

    Masks lines whose cited claims (``[claim:clm_XXX]``) map to source cards with
    a work/client-sensitive sensitivity, leaving personal/public content intact.
    Output is ``runs/<run>/reports/report_redacted.md`` (deterministic). Raises
    :class:`NotFoundError` when the run or its report is missing.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    if not rp.run.exists():
        raise NotFoundError(f"run not found: {run_id} ({rp.run})")

    source_report = _resolve_report(rp)
    if source_report is None:
        raise NotFoundError(f"no report to redact for run {run_id} ({rp.reports})")

    sensitive_claims = _sensitive_claim_ids(rp)
    meta, body = load_md(source_report)

    redacted_body, redacted = _mask_body(body, sensitive_claims)
    note = (
        f"\n\n> Redacted for target `{target}` on {now_iso()}: "
        f"{len(redacted)} claim(s) backed by work/client-sensitive sources were "
        "masked. See the source run for the unredacted report.\n"
    )

    out_meta = dict(meta)
    out_meta["sensitivity"] = "public" if target == "public" else out_meta.get("sensitivity")
    out_meta["redacted"] = True
    out_meta["redaction_target"] = target

    out_path = rp.reports / "report_redacted.md"
    rp.reports.mkdir(parents=True, exist_ok=True)
    dump_md(out_meta, redacted_body + note, out_path)

    return RedactResult(
        run_id=run_id,
        target=target,
        source_report=source_report,
        redacted_path=out_path,
        redacted_claims=sorted(redacted),
    )


def _resolve_report(rp: RunPaths) -> Path | None:
    for candidate in (rp.report_final, rp.report_draft):
        if candidate.exists():
            return candidate
    if rp.reports.exists():
        reports = sorted(p for p in rp.reports.glob("*.md") if p.name != "report_redacted.md")
        if reports:
            return reports[0]
    return None


def _sensitive_claim_ids(rp: RunPaths) -> set[str]:
    """Claim ids whose cited source cards are work/client-sensitive."""

    ledger = _safe_load(rp.claim_ledger)
    claims = ledger.get("claims") if isinstance(ledger, dict) else None
    if not isinstance(claims, list):
        return set()

    sensitivity_by_card = _source_card_sensitivities(rp)
    sensitive: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id")
        sources = claim.get("sources") if isinstance(claim.get("sources"), list) else []
        for src in sources:
            card_id = src.get("source_card_id") if isinstance(src, dict) else None
            if card_id and sensitivity_by_card.get(card_id) in _WORK_SENSITIVITIES:
                if isinstance(claim_id, str):
                    sensitive.add(claim_id)
                break
    return sensitive


def _source_card_sensitivities(rp: RunPaths) -> dict[str, str]:
    """Map ``source_card_id -> sensitivity`` from the run's source cards."""

    out: dict[str, str] = {}
    if not rp.sources.exists():
        return out
    for md in sorted(rp.sources.glob("*.md")):
        try:
            meta, _ = load_md(md)
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        card_id = meta.get("source_card_id")
        sens = meta.get("sensitivity")
        if isinstance(card_id, str) and isinstance(sens, str):
            out[card_id] = sens
    return out


def _mask_body(body: str, sensitive_claims: set[str]) -> tuple[str, set[str]]:
    """Mask report lines citing a sensitive claim; return (body, masked_ids)."""

    if not sensitive_claims:
        return body, set()
    masked: set[str] = set()
    out_lines: list[str] = []
    for line in body.splitlines():
        cited = set(_CLAIM_CITE.findall(line))
        hit = cited & sensitive_claims
        if hit:
            masked |= hit
            out_lines.append("[REDACTED — work/client-sensitive source]")
        else:
            out_lines.append(line)
    return "\n".join(out_lines), masked


def _safe_load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = load_yaml(path)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


__all__ = [
    "InitResult",
    "init_workspace",
    "RedactResult",
    "redact_run",
]
