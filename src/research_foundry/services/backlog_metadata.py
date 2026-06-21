"""Backlog metadata derivation — shared helper for Phase P2 (backfill) and P3 (creation).

This module is the SINGLE place that reads ``backlog/research_idea_backlog.yaml``
and converts it into run-level metadata.  Both the backfill migration script
(P2) and ``plan_run()`` (P3) import from here so there is no duplicated
derivation logic.

Public API
----------
BacklogMetadata
    Typed result container for the five new run metadata fields.
load_backlog_index(paths)
    Build a dict mapping each idea's ``ref`` (e.g. ``RIB-001``) to its
    :class:`BacklogMetadata`.
lookup_metadata(backlog_idea_ref, paths)
    Convenience wrapper — look up a single ref; returns ``None`` when absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..paths import FoundryPaths
from ..yamlio import load_yaml

# Path relative to workspace root where the backlog lives.
_BACKLOG_REL = Path("backlog") / "research_idea_backlog.yaml"


@dataclass(frozen=True)
class BacklogMetadata:
    """Metadata derived from a single backlog idea for storage in ``run.yaml``."""

    # Backlog reference slug (e.g. ``RIB-001``).
    backlog_idea_ref: str
    # Stable idea id slug (e.g. ``idea_claim-segmentation-source-alignment``).
    backlog_idea_id: str
    # Pillar identifier maps to ``category`` in run.yaml.
    category: str | None
    # Union of idea tags.
    tags: list[str]
    # Derived from ``suggested_project`` (at most one entry for a single idea).
    linked_projects: list[str]


def _backlog_path(paths: FoundryPaths) -> Path:
    return paths.root / _BACKLOG_REL


def load_backlog_index(paths: FoundryPaths) -> dict[str, BacklogMetadata]:
    """Return a mapping of ``ref`` → :class:`BacklogMetadata` for all ideas.

    Ideas that have no ``ref`` field are skipped.  This function reads the
    backlog file fresh on every call (no caching) so the caller can control
    caching via :func:`cached_load_backlog_index` when needed.

    Parameters
    ----------
    paths:
        Workspace paths — used to locate ``backlog/research_idea_backlog.yaml``.

    Returns
    -------
    dict[str, BacklogMetadata]
        Keyed by idea ``ref`` (e.g. ``"RIB-001"``).
    """
    backlog_path = _backlog_path(paths)
    if not backlog_path.exists():
        return {}

    doc: dict[str, Any] = load_yaml(backlog_path)
    ideas: list[Any] = doc.get("ideas") or []

    index: dict[str, BacklogMetadata] = {}
    for idea in ideas:
        if not isinstance(idea, dict):
            continue
        ref = idea.get("ref")
        if not ref:
            continue

        idea_id: str = str(idea.get("id") or "")
        category_raw = idea.get("pillar")
        category: str | None = str(category_raw) if category_raw else None

        raw_tags = idea.get("tags") or []
        tags: list[str] = [str(t) for t in raw_tags if t]

        suggested = idea.get("suggested_project")
        linked_projects: list[str] = [str(suggested)] if suggested else []

        index[str(ref)] = BacklogMetadata(
            backlog_idea_ref=str(ref),
            backlog_idea_id=idea_id,
            category=category,
            tags=tags,
            linked_projects=linked_projects,
        )

    return index


def lookup_metadata(
    backlog_idea_ref: str,
    paths: FoundryPaths,
) -> BacklogMetadata | None:
    """Look up metadata for a single backlog ref.

    Parameters
    ----------
    backlog_idea_ref:
        The ``RIB-NNN`` style ref to look up.
    paths:
        Workspace paths.

    Returns
    -------
    BacklogMetadata | None
        ``None`` when the ref is not found in the backlog.
    """
    index = load_backlog_index(paths)
    return index.get(backlog_idea_ref)


def backlog_exists(paths: FoundryPaths) -> bool:
    """Return ``True`` if the backlog file is present in the workspace."""
    return _backlog_path(paths).exists()


__all__ = [
    "BacklogMetadata",
    "load_backlog_index",
    "lookup_metadata",
    "backlog_exists",
]
