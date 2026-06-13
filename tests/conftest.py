"""Shared pytest fixtures for Research Foundry service tests.

The ``tmp_foundry`` fixture builds a fully isolated foundry workspace in a temp
directory (copying the canonical ``schemas/``, ``config/``, ``templates/`` from
the distribution) and pins the clock so ids/timestamps are deterministic. Every
service test should use it and pass ``paths=tmp_foundry`` to services.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_foundry import ids
from research_foundry.paths import FoundryPaths, distribution_root

# Directories every run/workspace needs (mirror of the spec §5 substrate).
_SUBSTRATE = [
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
]

_FIXED = datetime(2026, 6, 13, 9, 41, 0, tzinfo=UTC).astimezone()


@pytest.fixture(autouse=True)
def _fixed_clock():
    """Pin the clock so generated ids/timestamps are stable across the suite."""

    ids.set_clock(lambda: _FIXED)
    yield
    ids.set_clock(lambda: datetime.now(UTC).astimezone())


@pytest.fixture
def tmp_foundry(tmp_path: Path) -> FoundryPaths:
    """An isolated foundry workspace rooted at a temp dir.

    Copies the canonical schemas/config/templates from the distribution so
    schema validation and template rendering behave exactly as in the real repo.
    """

    root = tmp_path / "fdry"
    root.mkdir(parents=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    # minimal foundry.yaml marker so discover() and FoundryConfig resolve here
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:  # pragma: no cover
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in _SUBSTRATE:
        (root / d).mkdir(parents=True, exist_ok=True)
    return FoundryPaths(root=root)


@pytest.fixture
def sample_idea_text() -> str:
    return (
        "Research how agentic research workflows should handle evidence bundles "
        "and claim traceability across cheap extraction and deep synthesis models."
    )
