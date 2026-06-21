"""Derivation consistency and backfill idempotency tests (TEST-001).

Risk register item H: "dual-write consistency — run.yaml vs run_index.yaml vs
derived backlog_context".  This module is the primary guard.

For a given backlog idea, the P2 backfill derivation path
(``scripts/backfill_run_metadata.build_inversion_map``) and the P3
creation-path derivation (``backlog_metadata.lookup_metadata`` used inside
``plan_run()``) MUST produce IDENTICAL values for ALL five metadata fields:

  - ``linked_projects``
  - ``category``
  - ``tags``
  - ``backlog_idea_ref``  (must be the idea's ``ref`` field, e.g. ``RIB-001``)
  - ``backlog_idea_id``   (must be the idea's ``id`` slug)

The first three fields drive the viewer filtering feature (FILT-001..003).
The ``backlog_idea_ref`` field must match ``^RIB-\\d+$`` per the run.yaml JSON
schema; both paths now read the idea's ``ref`` field so there is no divergence.

Covered scenarios
-----------------
1. Single-idea, single-project: three filtering fields identical on both paths.
2. Multi-idea-to-same-run (union merge): linked_projects and tags union is
   identical between paths.
3. Idea with null suggested_project: linked_projects = [] on both paths.
4. Idempotency: applying patch_run_yaml twice writes no diff on the second call.
5. Idempotency after plan_run: plan_run() re-run on an already-enriched run.yaml
   (simulated) yields no change.
6. dry_run correctness: patch_run_yaml(dry_run=True) returns diff but writes nothing.
7. backlog_idea_ref convergence: both paths produce identical, schema-valid
   (^RIB-\\d+$) values for backlog_idea_ref.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# ── Allow import of the standalone backfill script ────────────────────────────
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import backfill_run_metadata as backfill  # noqa: E402 (after sys.path patch)

from research_foundry.services.backlog_metadata import (  # noqa: E402
    load_backlog_index,
    lookup_metadata,
)
from research_foundry.yamlio import dump_yaml, load_yaml  # noqa: E402


# ── Shared test backlog fixtures ───────────────────────────────────────────────

#: A synthetic backlog with two distinct ideas: one that maps to a run (RIB-001),
#: one that maps to the SAME run (RIB-002, for union-merge tests), and one that
#: has a null project (RIB-003).
_BACKLOG_SINGLE_IDEA = {
    "schema_version": "0.1",
    "type": "research_idea_backlog",
    "title": "Test Backlog",
    "ideas": [
        {
            "ref": "RIB-001",
            "id": "idea_claim-segmentation-source-alignment",
            "title": "Claim segmentation and claim-to-source alignment",
            "pillar": "pillar_evidence-claim-verification",
            "status": "completed",
            "tags": ["claim-verification", "attribution", "entailment"],
            "suggested_project": "Research Foundry",
            "sensitivity": "personal",
            "links": {
                "run_id": "rf_run_20260614_claim_seg",
            },
        },
    ],
}

_BACKLOG_MULTI_IDEA_SAME_RUN = {
    "schema_version": "0.1",
    "type": "research_idea_backlog",
    "title": "Test Backlog — union merge",
    "ideas": [
        {
            "ref": "RIB-010",
            "id": "idea_first-merged",
            "title": "First merged idea",
            "pillar": "pillar_rag-accuracy",
            "status": "completed",
            "tags": ["rag", "retrieval"],
            "suggested_project": "Research Foundry",
            "sensitivity": "personal",
            "links": {"run_id": "rf_run_merge_test"},
        },
        {
            "ref": "RIB-011",
            "id": "idea_second-merged",
            "title": "Second merged idea for the same run",
            "pillar": "pillar_rag-accuracy",   # same pillar — first wins
            "status": "completed",
            "tags": ["rag", "chunking"],         # "rag" deduplicated, "chunking" added
            "suggested_project": "KnitWit",      # second project — union
            "sensitivity": "personal",
            "links": {"run_id": "rf_run_merge_test"},
        },
    ],
}

_BACKLOG_NULL_PROJECT = {
    "schema_version": "0.1",
    "type": "research_idea_backlog",
    "title": "Test Backlog — null project",
    "ideas": [
        {
            "ref": "RIB-020",
            "id": "idea_no-project",
            "title": "Idea without a suggested project",
            "pillar": "pillar_governance-multi-key-safety",
            "status": "proposed",
            "tags": ["governance"],
            "suggested_project": None,
            "sensitivity": "personal",
            "links": {"run_id": "rf_run_no_project"},
        },
    ],
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _write_backlog(tmp_path: Path, doc: dict[str, Any]) -> Path:
    """Write a backlog YAML to tmp_path/backlog/ and return the path."""
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    dest = backlog_dir / "research_idea_backlog.yaml"
    dest.write_text(
        yaml.dump(doc, Dumper=yaml.SafeDumper, default_flow_style=False,
                  sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return dest


def _p3_meta(backlog_path: Path, ref: str) -> dict[str, Any]:
    """Return the filtering fields from the P3 (service) derivation path."""
    # Replicate what lookup_metadata does via the service layer.
    # We must construct a FoundryPaths whose root is the backlog's parent.
    from research_foundry.paths import FoundryPaths

    workspace_root = backlog_path.parent.parent  # tmp_path
    paths = FoundryPaths(root=workspace_root)
    meta = lookup_metadata(ref, paths)
    assert meta is not None, f"lookup_metadata returned None for ref={ref!r}"
    return {
        "linked_projects": meta.linked_projects,
        "category": meta.category,
        "tags": meta.tags,
    }


def _p2_meta_for_run(backlog_path: Path, run_id: str) -> dict[str, Any]:
    """Return the filtering fields from the P2 (backfill script) derivation path."""
    inv = backfill.build_inversion_map(backlog_path)
    assert run_id in inv, f"build_inversion_map has no entry for run_id={run_id!r}"
    entry = inv[run_id]
    return {
        "linked_projects": entry["linked_projects"],
        "category": entry["category"],
        "tags": entry["tags"],
    }


# ── Tests: derivation consistency (P2 vs P3) ──────────────────────────────────


class TestDerivationConsistency:
    """
    Assert that for a given backlog idea, the P2 backfill derivation and the
    P3 creation-path derivation produce IDENTICAL values for the three
    filtering-critical fields: linked_projects, category, tags.

    These are the fields that drive FILT-001..003 in the viewer.
    """

    def test_single_idea_linked_projects_identical(self, tmp_path: Path) -> None:
        """linked_projects from P2 and P3 are the same for a single idea."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)

        p3 = _p3_meta(backlog_path, "RIB-001")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_20260614_claim_seg")

        assert p3["linked_projects"] == p2["linked_projects"], (
            f"linked_projects mismatch: P3={p3['linked_projects']!r}  P2={p2['linked_projects']!r}"
        )

    def test_single_idea_category_identical(self, tmp_path: Path) -> None:
        """category from P2 and P3 are the same for a single idea."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)

        p3 = _p3_meta(backlog_path, "RIB-001")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_20260614_claim_seg")

        assert p3["category"] == p2["category"], (
            f"category mismatch: P3={p3['category']!r}  P2={p2['category']!r}"
        )

    def test_single_idea_tags_identical(self, tmp_path: Path) -> None:
        """tags set from P2 and P3 are the same for a single idea."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)

        p3 = _p3_meta(backlog_path, "RIB-001")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_20260614_claim_seg")

        # Compare as sets — order may differ between paths.
        assert set(p3["tags"]) == set(p2["tags"]), (
            f"tags mismatch: P3={sorted(p3['tags'])}  P2={sorted(p2['tags'])}"
        )

    def test_null_project_linked_projects_empty_on_both_paths(
        self, tmp_path: Path
    ) -> None:
        """When suggested_project is null, linked_projects = [] from both paths."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_NULL_PROJECT)

        p3 = _p3_meta(backlog_path, "RIB-020")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_no_project")

        assert p3["linked_projects"] == [], f"P3 linked_projects should be [] got {p3['linked_projects']!r}"
        assert p2["linked_projects"] == [], f"P2 linked_projects should be [] got {p2['linked_projects']!r}"

    def test_null_project_tags_identical(self, tmp_path: Path) -> None:
        """tags from both paths match for an idea with a null project."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_NULL_PROJECT)

        p3 = _p3_meta(backlog_path, "RIB-020")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_no_project")

        assert set(p3["tags"]) == set(p2["tags"])

    def test_multi_idea_union_linked_projects_consistent(
        self, tmp_path: Path
    ) -> None:
        """Union of linked_projects from P2 (multi-idea merge) matches P3 for first idea."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_MULTI_IDEA_SAME_RUN)

        # P3 only sees one idea at a time; compare P3(RIB-010) + P3(RIB-011) union
        # against P2's merged entry for rf_run_merge_test.
        p3_010 = _p3_meta(backlog_path, "RIB-010")
        p3_011 = _p3_meta(backlog_path, "RIB-011")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_merge_test")

        # Union from both P3 lookups
        p3_union_projects = list(
            dict.fromkeys(p3_010["linked_projects"] + p3_011["linked_projects"])
        )

        assert set(p3_union_projects) == set(p2["linked_projects"]), (
            f"linked_projects union mismatch: P3 union={p3_union_projects}  P2={p2['linked_projects']}"
        )

    def test_multi_idea_union_tags_consistent(self, tmp_path: Path) -> None:
        """Union of tags from P3 (per-idea) matches P2 merged entry."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_MULTI_IDEA_SAME_RUN)

        p3_010 = _p3_meta(backlog_path, "RIB-010")
        p3_011 = _p3_meta(backlog_path, "RIB-011")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_merge_test")

        p3_union_tags = set(p3_010["tags"]) | set(p3_011["tags"])

        assert p3_union_tags == set(p2["tags"]), (
            f"tags union mismatch: P3 union={sorted(p3_union_tags)}  P2={sorted(p2['tags'])}"
        )

    def test_multi_idea_category_first_wins_on_both_paths(
        self, tmp_path: Path
    ) -> None:
        """When two ideas share a run, category = pillar of the first idea on both paths."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_MULTI_IDEA_SAME_RUN)

        p3_010 = _p3_meta(backlog_path, "RIB-010")
        p2 = _p2_meta_for_run(backlog_path, "rf_run_merge_test")

        # P2 uses first-wins; P3 per-idea always sees that idea's own pillar.
        # The first idea's category should match the P2 merged entry.
        assert p3_010["category"] == p2["category"], (
            f"category mismatch: P3(RIB-010)={p3_010['category']!r}  P2={p2['category']!r}"
        )


# ── Tests: backlog_idea_ref convergence (P2 vs P3) ────────────────────────────


class TestBacklogIdeaRefConvergence:
    """Assert that P2 (backfill) and P3 (creation) produce IDENTICAL, schema-valid
    ``backlog_idea_ref`` values.

    The JSON schema for run.yaml requires ``backlog_idea_ref`` to match the
    pattern ``^RIB-\\d+$`` (the idea's ``ref`` field, not its ``id`` slug).
    Both paths now read the idea's ``ref`` field, so there is no divergence.
    """

    import re
    _RIB_PATTERN = re.compile(r"^RIB-\d+$")

    def test_p2_backlog_idea_ref_is_rib_ref(self, tmp_path: Path) -> None:
        """P2 (backfill) backlog_idea_ref is the RIB-NNN ref, not the id slug."""
        import re
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        ref = inv["rf_run_20260614_claim_seg"]["backlog_idea_ref"]
        assert ref is not None, "backlog_idea_ref must not be None when idea has a ref field"
        assert re.match(r"^RIB-\d+$", ref), (
            f"backlog_idea_ref {ref!r} does not match ^RIB-\\d+$ (P2 path)"
        )
        assert ref == "RIB-001", f"Expected RIB-001, got {ref!r}"

    def test_p3_backlog_idea_ref_is_rib_ref(self, tmp_path: Path) -> None:
        """P3 (creation) backlog_idea_ref is the RIB-NNN ref, not the id slug."""
        import re
        from research_foundry.services.backlog_metadata import load_backlog_index
        from research_foundry.paths import FoundryPaths

        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        paths = FoundryPaths(root=backlog_path.parent.parent)
        index = load_backlog_index(paths)
        meta = index.get("RIB-001")
        assert meta is not None, "RIB-001 not found in backlog index"
        ref = meta.backlog_idea_ref
        assert re.match(r"^RIB-\d+$", ref), (
            f"backlog_idea_ref {ref!r} does not match ^RIB-\\d+$ (P3 path)"
        )
        assert ref == "RIB-001", f"Expected RIB-001, got {ref!r}"

    def test_p2_and_p3_backlog_idea_ref_identical(self, tmp_path: Path) -> None:
        """P2 and P3 produce the same backlog_idea_ref value (convergence)."""
        from research_foundry.services.backlog_metadata import load_backlog_index
        from research_foundry.paths import FoundryPaths

        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)

        # P2 value
        inv = backfill.build_inversion_map(backlog_path)
        p2_ref = inv["rf_run_20260614_claim_seg"]["backlog_idea_ref"]

        # P3 value
        paths = FoundryPaths(root=backlog_path.parent.parent)
        index = load_backlog_index(paths)
        p3_ref = index["RIB-001"].backlog_idea_ref

        assert p2_ref == p3_ref, (
            f"backlog_idea_ref mismatch between P2 and P3: P2={p2_ref!r}  P3={p3_ref!r}"
        )

    def test_p2_backlog_idea_id_is_id_slug(self, tmp_path: Path) -> None:
        """P2 backlog_idea_id is still the stable id slug (not the ref)."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        idea_id = inv["rf_run_20260614_claim_seg"]["backlog_idea_id"]
        assert idea_id == "idea_claim-segmentation-source-alignment", (
            f"backlog_idea_id should be the id slug, got {idea_id!r}"
        )

    def test_p2_backlog_idea_ref_null_when_idea_has_no_ref(
        self, tmp_path: Path
    ) -> None:
        """When a backlog idea has no ref field, backlog_idea_ref is None (graceful)."""
        backlog_no_ref = {
            "schema_version": "0.1",
            "type": "research_idea_backlog",
            "title": "No-ref backlog",
            "ideas": [
                {
                    # intentionally omit "ref"
                    "id": "idea_no-ref-idea",
                    "title": "Idea without a ref",
                    "pillar": "pillar_test",
                    "tags": ["test"],
                    "suggested_project": "ProjectX",
                    "links": {"run_id": "rf_run_no_ref"},
                },
            ],
        }
        backlog_path = _write_backlog(tmp_path, backlog_no_ref)
        inv = backfill.build_inversion_map(backlog_path)

        assert "rf_run_no_ref" in inv
        assert inv["rf_run_no_ref"]["backlog_idea_ref"] is None, (
            "backlog_idea_ref must be None when idea lacks a ref field"
        )
        assert inv["rf_run_no_ref"]["backlog_idea_id"] == "idea_no-ref-idea"


# ── Tests: backfill idempotency ────────────────────────────────────────────────


class TestBackfillIdempotency:
    """
    patch_run_yaml is idempotent: running it twice on the same run.yaml
    produces a diff on the first call and no diff on the second call.

    This guards risk H: "backfill correctness" — re-running the migration must
    never degrade already-enriched runs.
    """

    def test_first_run_produces_diff(self, tmp_path: Path) -> None:
        """patch_run_yaml returns non-empty diff on first application."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_20260614_claim_seg"]

        run_dir = tmp_path / "runs" / "rf_run_20260614_claim_seg"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        run_yaml.write_text(
            yaml.dump(
                {"run_id": "rf_run_20260614_claim_seg", "status": "planned"},
                Dumper=yaml.SafeDumper,
            ),
            encoding="utf-8",
        )

        diff = backfill.patch_run_yaml(
            run_yaml, metadata, dry_run=False, force=False, backup=False
        )
        assert len(diff) > 0, "Expected a non-empty diff on the first application"

    def test_second_run_produces_no_diff(self, tmp_path: Path) -> None:
        """patch_run_yaml returns empty diff on second application (idempotent)."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_20260614_claim_seg"]

        run_dir = tmp_path / "runs" / "rf_run_20260614_claim_seg"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        run_yaml.write_text(
            yaml.dump(
                {"run_id": "rf_run_20260614_claim_seg", "status": "planned"},
                Dumper=yaml.SafeDumper,
            ),
            encoding="utf-8",
        )

        # First application
        backfill.patch_run_yaml(
            run_yaml, metadata, dry_run=False, force=False, backup=False
        )
        # Second application — must be no-op
        diff2 = backfill.patch_run_yaml(
            run_yaml, metadata, dry_run=False, force=False, backup=False
        )
        assert diff2 == [], (
            f"Expected empty diff on second application (idempotent), got: {diff2}"
        )

    def test_idempotency_preserves_values(self, tmp_path: Path) -> None:
        """After two patch_run_yaml calls, field values remain unchanged."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_20260614_claim_seg"]

        run_dir = tmp_path / "runs" / "rf_run_20260614_claim_seg"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        run_yaml.write_text(
            yaml.dump(
                {"run_id": "rf_run_20260614_claim_seg", "status": "planned"},
                Dumper=yaml.SafeDumper,
            ),
            encoding="utf-8",
        )

        backfill.patch_run_yaml(run_yaml, metadata, dry_run=False, force=False, backup=False)
        after_first = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))

        backfill.patch_run_yaml(run_yaml, metadata, dry_run=False, force=False, backup=False)
        after_second = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))

        assert after_first["linked_projects"] == after_second["linked_projects"]
        assert after_first["category"] == after_second["category"]
        assert after_first["tags"] == after_second["tags"]

    def test_idempotency_with_multi_idea_merge(self, tmp_path: Path) -> None:
        """Idempotency holds for a run linked from two ideas (union merge)."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_MULTI_IDEA_SAME_RUN)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_merge_test"]

        run_dir = tmp_path / "runs" / "rf_run_merge_test"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        run_yaml.write_text(
            yaml.dump(
                {"run_id": "rf_run_merge_test", "status": "planned"},
                Dumper=yaml.SafeDumper,
            ),
            encoding="utf-8",
        )

        backfill.patch_run_yaml(run_yaml, metadata, dry_run=False, force=False, backup=False)
        diff2 = backfill.patch_run_yaml(run_yaml, metadata, dry_run=False, force=False, backup=False)
        assert diff2 == [], f"Multi-idea merge idempotency failed: {diff2}"

    def test_dry_run_produces_diff_but_no_write(self, tmp_path: Path) -> None:
        """dry_run=True returns a diff but leaves run.yaml unchanged."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_20260614_claim_seg"]

        run_dir = tmp_path / "runs" / "rf_run_20260614_claim_seg"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        original_content = yaml.dump(
            {"run_id": "rf_run_20260614_claim_seg", "status": "planned"},
            Dumper=yaml.SafeDumper,
        )
        run_yaml.write_text(original_content, encoding="utf-8")

        diff = backfill.patch_run_yaml(
            run_yaml, metadata, dry_run=True, force=False, backup=False
        )

        # diff must be non-empty (something would change)
        assert len(diff) > 0, "Expected dry_run to report a diff"
        # file must be unchanged
        assert run_yaml.read_text(encoding="utf-8") == original_content, (
            "dry_run=True must not modify run.yaml"
        )

    def test_empty_list_placeholder_overwritten_on_first_run(
        self, tmp_path: Path
    ) -> None:
        """Fields with empty-list placeholders (P1 stubs) are treated as unenriched."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_20260614_claim_seg"]

        run_dir = tmp_path / "runs" / "rf_run_20260614_claim_seg"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        run_yaml.write_text(
            yaml.dump(
                {
                    "run_id": "rf_run_20260614_claim_seg",
                    "status": "planned",
                    # P1 stub placeholders — should be treated as unenriched
                    "linked_projects": [],
                    "category": None,
                    "tags": [],
                    "backlog_idea_ref": None,
                    "backlog_idea_id": None,
                },
                Dumper=yaml.SafeDumper,
            ),
            encoding="utf-8",
        )

        diff = backfill.patch_run_yaml(
            run_yaml, metadata, dry_run=False, force=False, backup=False
        )
        assert len(diff) > 0, "Expected diff when replacing empty-list placeholders"

        written = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
        assert written["linked_projects"] == ["Research Foundry"]
        assert written["category"] == "pillar_evidence-claim-verification"
        assert set(written["tags"]) == {"claim-verification", "attribution", "entailment"}

    def test_already_enriched_run_not_overwritten(self, tmp_path: Path) -> None:
        """A run with all 5 fields already set is skipped (no-op without --force)."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)
        metadata = inv["rf_run_20260614_claim_seg"]

        run_dir = tmp_path / "runs" / "rf_run_20260614_claim_seg"
        run_dir.mkdir(parents=True)
        run_yaml = run_dir / "run.yaml"
        enriched_content = yaml.dump(
            {
                "run_id": "rf_run_20260614_claim_seg",
                "status": "planned",
                "linked_projects": ["Research Foundry"],
                "category": "pillar_evidence-claim-verification",
                "tags": ["claim-verification", "attribution", "entailment"],
                "backlog_idea_ref": "RIB-001",
                "backlog_idea_id": "idea_claim-segmentation-source-alignment",
            },
            Dumper=yaml.SafeDumper,
        )
        run_yaml.write_text(enriched_content, encoding="utf-8")

        diff = backfill.patch_run_yaml(
            run_yaml, metadata, dry_run=False, force=False, backup=False
        )
        assert diff == [], (
            f"Expected no diff on already-enriched run without --force, got: {diff}"
        )
        # Content must be unchanged
        assert run_yaml.read_text(encoding="utf-8") == enriched_content


# ── Tests: inversion map correctness (MIG-001) ────────────────────────────────


class TestInversionMapCorrectness:
    """
    Tests for build_inversion_map: the P2 backfill join key is backlog
    ``links.run_id`` (not fuzzy title match) and derivation is correct.
    """

    def test_inversion_map_keyed_by_run_id(self, tmp_path: Path) -> None:
        """build_inversion_map is keyed by links.run_id, not by backlog ref."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_SINGLE_IDEA)
        inv = backfill.build_inversion_map(backlog_path)

        assert "rf_run_20260614_claim_seg" in inv
        # Must NOT be keyed by the backlog ref (RIB-001)
        assert "RIB-001" not in inv

    def test_inversion_map_excludes_ideas_without_run_id(
        self, tmp_path: Path
    ) -> None:
        """Ideas with null links.run_id are excluded from the inversion map."""
        backlog = {
            "schema_version": "0.1",
            "type": "research_idea_backlog",
            "title": "Mixed",
            "ideas": [
                {
                    "ref": "RIB-030",
                    "id": "idea_has-run",
                    "pillar": "pillar_x",
                    "tags": ["x"],
                    "suggested_project": "ProjA",
                    "links": {"run_id": "rf_run_has_link"},
                },
                {
                    "ref": "RIB-031",
                    "id": "idea_no-run",
                    "pillar": "pillar_y",
                    "tags": ["y"],
                    "suggested_project": "ProjB",
                    "links": {"run_id": None},   # no link — must be excluded
                },
            ],
        }
        backlog_path = _write_backlog(tmp_path, backlog)
        inv = backfill.build_inversion_map(backlog_path)

        assert "rf_run_has_link" in inv
        assert len(inv) == 1, f"Expected exactly 1 entry, got {len(inv)}: {list(inv)}"

    def test_inversion_map_merge_two_ideas(self, tmp_path: Path) -> None:
        """Two ideas linking to the same run_id are merged correctly."""
        backlog_path = _write_backlog(tmp_path, _BACKLOG_MULTI_IDEA_SAME_RUN)
        inv = backfill.build_inversion_map(backlog_path)

        assert "rf_run_merge_test" in inv
        entry = inv["rf_run_merge_test"]

        # Union of suggested_projects
        assert set(entry["linked_projects"]) == {"Research Foundry", "KnitWit"}
        # Union of tags; "rag" from both ideas deduped to one occurrence
        assert set(entry["tags"]) == {"rag", "retrieval", "chunking"}
        # category: first non-null pillar wins
        assert entry["category"] == "pillar_rag-accuracy"
