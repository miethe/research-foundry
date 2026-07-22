"""Red-team fixtures + 7-bundle regression for the `pediatric_cds` hard-gate.

RFUP-1 / phase-2-pediatric-schema-gate, task P2-003 (depends on P2-002).

Two obligations, per AC-P2-8..AC-P2-10:

1. ``tests/fixtures/pediatric_cds/red_team/*.json`` holds >=5 malformed
   ``pediatric_cds`` block fixtures, each targeting a distinct violation
   class (AC-P2-8). 100% must fail schema validation (AC-P2-9).
2. Every ``pediatric_cds`` block actually present on a source card across the
   7 existing verified pediatric-CDS bundles (committed ``aaa9d92``, per
   project memory) must produce zero false positives (AC-P2-10).

**P2-003 finding, folded into P2-001's schema** (per this task's own
instructions: "fix any bundle-breaking field in P2-001's schema"): the 7
bundles' ``pediatric_cds`` blocks use a flat
``population``/``assay_method``/``threshold``/``lifecycle``/``classification``
shape -- the one actually produced by
``.claude/workflows/rf-pediatric-cds-run-execute.js``'s ``CARD_TEMPLATE`` --
which shares *zero* top-level keys with the richer 9-section shape
(``source_status``/``study``/.../``lifecycle``-with-different-subfields)
named in the pediatric-anemia-site scope-brief that P2-001 encoded. Every one
of the 487 pediatric_cds blocks across all 7 bundles uses the flat shape
uniformly, so the schema was widened to a ``oneOf`` of both shapes
(``PediatricCdsBlockLegacy`` / ``PediatricCdsBlockRich``) rather than
breaking what's already on disk -- see the schema's own ``$comment`` and
``verification.py``'s ``_pediatric_cds_block_errors`` docstring for the full
rationale. Fixture 06 below exists specifically to prove the legacy branch is
itself still hard-gated (not a permissive escape hatch introduced by the
``oneOf``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import load_md
from research_foundry.services import verification as verification_module

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RED_TEAM_DIR = _REPO_ROOT / "tests" / "fixtures" / "pediatric_cds" / "red_team"

# The 7 existing verified pediatric-CDS run bundles (aaa9d92) named in the
# phase-2 plan's exit criteria and AC-P2-10. Hardcoded (not globbed) so an
# unrelated future run directory landing under runs/ can never silently
# widen or narrow this regression's scope.
_VERIFIED_BUNDLE_RUN_IDS = (
    "rf_run_20260717_reg_001_pediatric_cds_map_the",
    "rf_run_20260717_reg_004_pediatric_cds_scope_the",
    "rf_run_20260717_rf_cbc_001_pediatric_cds_establish",
    "rf_run_20260717_rf_cbc_002_pediatric_cds_establish",
    "rf_run_20260717_rf_ev_001_pediatric_cds_backfill",
    "rf_run_20260717_rf_gro_002_pediatric_cds_evidence",
    "rf_run_20260717_rf_kid_001_pediatric_cds_evidence",
)


@pytest.fixture(autouse=True)
def _clear_pediatric_cds_schema_cache():
    """Mirror test_verification_pediatric_cds.py's cache-isolation fixture --
    this module reads the real package-bundled schema (never monkeypatches
    it), but clearing defensively costs nothing and keeps the two test
    modules' behavior identical regardless of run order."""

    verification_module._load_pediatric_cds_schema.cache_clear()
    yield
    verification_module._load_pediatric_cds_schema.cache_clear()


def _red_team_fixture_paths() -> list[Path]:
    paths = sorted(_RED_TEAM_DIR.glob("*.json"))
    assert len(paths) >= 5, (
        f"expected >=5 red-team pediatric_cds fixtures under {_RED_TEAM_DIR}, "
        f"found {len(paths)} (AC-P2-8)"
    )
    return paths


def _load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        doc = json.load(f)
    assert "block" in doc, f"{path} missing top-level 'block' key"
    assert "expect_error_substring" in doc, f"{path} missing 'expect_error_substring' key"
    return doc


# --- AC-P2-8 / AC-P2-9: red-team fixture set, 100% must fail --------------


@pytest.mark.parametrize("fixture_path", _red_team_fixture_paths(), ids=lambda p: p.stem)
def test_red_team_fixture_fails_schema_validation(fixture_path: Path):
    doc = _load_fixture(fixture_path)
    errors = verification_module._pediatric_cds_block_errors(doc["block"])

    assert errors, f"{fixture_path.name} ({doc['violation_class']}) unexpectedly PASSED schema validation"
    joined = "\n".join(errors)
    assert doc["expect_error_substring"] in joined, (
        f"{fixture_path.name}: expected error mentioning "
        f"{doc['expect_error_substring']!r}, got: {joined}"
    )


def test_red_team_fixture_set_covers_at_least_five_distinct_violation_classes():
    """Belt-and-suspenders on AC-P2-8's '>=5, each a distinct class' wording
    -- guards against someone later adding near-duplicate fixtures without
    growing real coverage."""

    fixtures = [_load_fixture(p) for p in _red_team_fixture_paths()]
    classes = {f["violation_class"] for f in fixtures}
    assert len(classes) >= 5
    assert len(classes) == len(fixtures), "expected each fixture to name a distinct violation_class"


# --- AC-P2-10: 0 false positives across the 7 verified bundles ------------


def _iter_bundle_pediatric_cds_blocks():
    """Yield ``(source_card_path, evidence_id, block)`` for every non-null
    ``pediatric_cds`` block on every source card across the 7 verified
    bundles. Loaded via ``frontmatter.load_md`` (the same YAML round-trip
    ``verify_report`` itself uses via ``_index_source_cards``) so any
    YAML-native type-coercion hazard (e.g. bare dates parsing as
    ``datetime.date``) is exercised identically to production, not
    sidestepped by a raw ``yaml.safe_load``.
    """

    for run_id in _VERIFIED_BUNDLE_RUN_IDS:
        sources_dir = _REPO_ROOT / "runs" / run_id / "sources"
        assert sources_dir.is_dir(), f"expected verified bundle sources dir at {sources_dir}"
        for card_path in sorted(sources_dir.glob("*.md")):
            front, _body = load_md(card_path)
            for point in front.get("extracted_points", []) or []:
                if not isinstance(point, dict):
                    continue
                block = point.get("pediatric_cds")
                if block is None:
                    continue
                yield card_path, point.get("evidence_id"), block


def test_seven_verified_bundles_zero_false_positives():
    """AC-P2-10: the schema hard-gate must accept every pediatric_cds block
    already shipped in the 7 verified bundles. Any failure here is a
    schema-authoring bug in P2-001/P2-003, per the phase plan's explicit
    call-out -- never a reason to touch the bundles themselves."""

    failures: list[str] = []
    n_blocks = 0
    for card_path, evidence_id, block in _iter_bundle_pediatric_cds_blocks():
        n_blocks += 1
        errors = verification_module._pediatric_cds_block_errors(block)
        if errors:
            rel = card_path.relative_to(_REPO_ROOT)
            failures.append(f"{rel}#{evidence_id}: {'; '.join(errors)}")

    # Sanity: fail loudly (not silently-vacuous-pass) if bundle discovery
    # itself regresses to finding zero blocks.
    assert n_blocks > 0, "expected at least one pediatric_cds block across the 7 verified bundles"
    assert not failures, (
        f"{len(failures)}/{n_blocks} pediatric_cds block(s) across the 7 verified bundles "
        f"failed schema validation (0 false positives required, AC-P2-10):\n"
        + "\n".join(failures[:10])
    )
