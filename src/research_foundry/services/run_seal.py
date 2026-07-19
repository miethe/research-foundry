"""Seal-trigger entrypoint for ``rf run export --seal`` (TASK-4.2 plumbing +
TASK-4.3 digest/lineage logic).

``seal_run`` computes a tamper-evident content digest over a run's evidence
chain (claim ledger, source cards, and — best-effort — the final report) and
appends an immutable entry to ``RunPaths.lineage``. The lineage file is
append-only: every seal rewrites the whole file atomically (temp write +
``fsync`` + ``os.replace``), but prior entries are always carried forward
unchanged, so re-sealing a run never destroys the record of a previous seal.

Digest scope (see ``_build_manifest``):
  - ``claims/claim_ledger.yaml`` (if present)
  - ``sources/*.md`` source cards (if present), sorted by filename for
    determinism
  - ``reports/report_final.md`` (if present) — best-effort only. The draft
    report is intentionally excluded: it is expected to mutate during
    authoring, and ``report_final.md`` is the point at which report content
    is considered settled enough to be worth sealing.

The lineage record itself (``RunPaths.lineage``) is never included in its own
digest -- that would be circular (the entry would need to describe its own
hash before it exists).

``recompute_digest`` rebuilds the same manifest from current on-disk state
and returns the digest string, without touching the lineage file. Tamper
detection (TASK-4.4) is: seal, then compare a later ``recompute_digest`` call
against the most recent entry's ``digest`` -- a mismatch means the covered
evidence changed after sealing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import FoundryPaths, RunPaths
from ..yamlio import loads_yaml
from .assertion_registry import _atomic_dump, _digest

_DIGEST_ALGORITHM = "sha256"
_DIGEST_SCOPE = "manifest-v1"


def _build_manifest(run_paths: RunPaths) -> list[dict[str, str]]:
    """Return a deterministic, sorted list of ``{path, sha256}`` entries.

    ``path`` is the file's location relative to the run directory (posix
    separators) so the manifest -- and therefore the digest computed over it
    -- is stable across machines/OSes. Missing files (e.g. no report yet, no
    sources yet) are simply omitted rather than erroring: an empty-evidence
    run still produces a valid (empty) manifest and a real digest over it.
    """

    root = run_paths.run
    entries: list[dict[str, str]] = []

    def add(path: Path) -> None:
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            entries.append({"path": rel, "sha256": _digest(path.read_bytes())})

    add(run_paths.claim_ledger)

    if run_paths.sources.is_dir():
        for card in sorted(run_paths.sources.glob("*.md")):
            add(card)

    add(run_paths.report_final)

    entries.sort(key=lambda entry: entry["path"])
    return entries


def _manifest_digest(manifest: list[dict[str, str]]) -> str:
    """Canonical (sorted-key, compact) JSON digest over a manifest list.

    Reuses the same "digest over canonical JSON encoding" approach as
    ``assertion_registry._canonical_digest``, generalized to a list rather
    than a single mapping (the manifest is already sorted by path, and
    ``sort_keys=True`` pins each entry's own key order).
    """

    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _digest(encoded)


def _build_entry(run_id: str, manifest: list[dict[str, str]], *, sealed_by: str | None) -> dict[str, Any]:
    return {
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "digest": _manifest_digest(manifest),
        "digest_algorithm": _DIGEST_ALGORITHM,
        "digest_scope": _DIGEST_SCOPE,
        "manifest": manifest,
        "sealed_by": sealed_by,
    }


def seal_run(paths: FoundryPaths, run_id: str, *, sealed_by: str | None = None) -> dict[str, Any]:
    """Seal a single run, appending a real tamper-evident lineage record.

    Parameters
    ----------
    paths:
        Resolved workspace paths (``FoundryPaths.discover()``).
    run_id:
        The run to seal; resolved via ``paths.run_paths(run_id)``.
    sealed_by:
        Optional sealer identity/context. ``None`` (the default) is fine for
        CLI-triggered seals; callers with an authenticated actor may pass an
        identifier here.

    Returns
    -------
    dict[str, Any]
        The lineage entry that was appended (see module docstring for shape).
        Sealing the same run twice appends a second, independent entry --
        the file is rewritten atomically each time but no prior entry is
        ever mutated or dropped.
    """

    run_paths: RunPaths = paths.run_paths(run_id)
    run_paths.ensure_scaffold()

    entries: list[dict[str, Any]] = []
    if run_paths.lineage.exists():
        existing = loads_yaml(run_paths.lineage.read_text(encoding="utf-8"))
        if isinstance(existing, dict) and isinstance(existing.get("entries"), list):
            entries = list(existing["entries"])

    manifest = _build_manifest(run_paths)
    entry = _build_entry(run_id, manifest, sealed_by=sealed_by)
    entries.append(entry)

    record = {"run_id": run_id, "entries": entries}
    _atomic_dump(record, run_paths.lineage)
    return entry


def recompute_digest(paths: FoundryPaths, run_id: str) -> str:
    """Recompute today's content digest over a run's current on-disk state.

    Rebuilds the exact same manifest ``seal_run`` would build right now and
    returns its digest string -- without reading or writing
    ``RunPaths.lineage``. Callers do tamper-evidence checking by comparing
    this against the ``digest`` field of the most recent lineage entry: a
    mismatch means the covered evidence (claim ledger / source cards / final
    report) changed since that entry was sealed.
    """

    run_paths: RunPaths = paths.run_paths(run_id)
    manifest = _build_manifest(run_paths)
    return _manifest_digest(manifest)


__all__ = ["seal_run", "recompute_digest"]
