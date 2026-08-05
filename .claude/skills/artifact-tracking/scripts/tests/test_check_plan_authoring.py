#!/usr/bin/env python3
"""Tests for check-plan-authoring.py — Shipped Work Ledger M4 L1 (FR-12).

Covers the DoD in the M4 leg contract:
  - clean on a well-formed fixture (status valid, feature_slug + a node/tree binding present);
  - exit 2 naming the field on a bad status;
  - exit 2 naming the field on a missing feature_slug;
  - warning-not-violation on a plan with feature_slug but no itt_node_id/intenttree_tree;
  - an alias status is a warning, never a violation (mirrors validate-plan-frontmatter.py);
  - directory-mode aggregation (the "run over every file, report the aggregate" measurement);
  - read-only — never writes, regardless of what it finds;
  - the real corpus doesn't crash the tool (a smoke test, not an assertion on specific counts —
    the corpus is expected to carry pre-existing violations; this is a measurement, not a gate to
    make pass, per the leg contract).

Offline; no network. Tests run through the real CLI entry point (subprocess), matching
convention 4.6/the sibling test files' style — the helper is exercised only incidentally, through
the CLI it backs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parents[3]
CLI = SCRIPTS_DIR / "check-plan-authoring.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args], capture_output=True, text=True
    )


def _fm(
    slug: str = "demo",
    status: str = "completed",
    feature_slug: str | None = "__same_as_slug__",
    node_id: str | None = None,
    tree_id: str | None = None,
) -> str:
    """Build a minimal, well-formed plan-frontmatter fixture with the fields under test."""
    if feature_slug == "__same_as_slug__":
        feature_slug = slug
    lines = ["---", "it_schema: 1"]
    if feature_slug is not None:
        lines.append(f"feature_slug: {feature_slug}")
    lines.append(f'title: "{slug}"')
    lines.append(f"status: {status}")
    if node_id is not None:
        lines.append(f"itt_node_id: {node_id}")
    if tree_id is not None:
        lines.append(f"intenttree_tree: {tree_id}")
    lines.extend(["tier: 3", "priority: P1", "points: 5", "---", "", "# Body", ""])
    return "\n".join(lines)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Clean fixture
# ---------------------------------------------------------------------------
class TestCleanFixture:
    def test_wellformed_fixture_exits_0_no_findings(self, tmp_path):
        f = _write(tmp_path / "good.md", _fm(node_id="node_01ABC"))
        r = _run(str(f), "--json")
        assert r.returncode == 0, r.stdout + r.stderr
        data = json.loads(r.stdout)
        assert data["violations"] == []
        assert data["warnings"] == []
        assert data["summary"]["files_scanned"] == 1

    def test_tree_id_alone_also_satisfies_binding(self, tmp_path):
        f = _write(tmp_path / "good.md", _fm(tree_id="tree_01XYZ"))
        r = _run(str(f), "--json")
        assert r.returncode == 0, r.stdout + r.stderr
        data = json.loads(r.stdout)
        assert data["warnings"] == []


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------
class TestBadStatusViolation:
    def test_hand_review_status_exits_2_naming_field_and_value(self, tmp_path):
        f = _write(
            tmp_path / "bad.md",
            _fm(status="totally_bogus_status", node_id="node_1"),
        )
        r = _run(str(f))
        assert r.returncode == 2, r.stdout + r.stderr
        assert "bad.md" in r.stdout
        assert "status" in r.stdout
        assert "totally_bogus_status" in r.stdout
        # never written
        assert f.read_text(encoding="utf-8") == _fm(status="totally_bogus_status", node_id="node_1")

    def test_json_names_file_field_and_detail(self, tmp_path):
        f = _write(tmp_path / "bad.md", _fm(status="reconciled-for-planning", node_id="node_1"))
        r = _run(str(f), "--json")
        assert r.returncode == 2
        data = json.loads(r.stdout)
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["file"] == str(f)
        assert v["field"] == "status"
        assert "reconciled-for-planning" in v["detail"]


class TestMissingFeatureSlugViolation:
    def test_missing_feature_slug_exits_2_naming_field(self, tmp_path):
        f = _write(tmp_path / "noslug.md", _fm(feature_slug=None, node_id="node_1"))
        r = _run(str(f))
        assert r.returncode == 2, r.stdout + r.stderr
        assert "noslug.md" in r.stdout
        assert "feature_slug" in r.stdout

    def test_json_violation_shape(self, tmp_path):
        f = _write(tmp_path / "noslug.md", _fm(feature_slug=None))
        r = _run(str(f), "--json")
        data = json.loads(r.stdout)
        assert data["exit"] == 2
        assert any(v["field"] == "feature_slug" for v in data["violations"])

    def test_no_frontmatter_at_all_is_a_missing_feature_slug_violation(self, tmp_path):
        f = _write(tmp_path / "plain.md", "# Just a heading\n\nNo frontmatter here.\n")
        r = _run(str(f), "--json")
        assert r.returncode == 2
        data = json.loads(r.stdout)
        assert any(v["field"] == "feature_slug" for v in data["violations"])


# ---------------------------------------------------------------------------
# Warnings — never violations
# ---------------------------------------------------------------------------
class TestBindingWarningNotViolation:
    def test_feature_slug_without_node_or_tree_is_warning_only(self, tmp_path):
        f = _write(tmp_path / "unbound.md", _fm())  # no node_id/tree_id
        r = _run(str(f), "--json")
        assert r.returncode == 0, r.stdout + r.stderr
        data = json.loads(r.stdout)
        assert data["violations"] == []
        assert len(data["warnings"]) == 1
        w = data["warnings"][0]
        assert w["field"] == "itt_node_id/intenttree_tree"

    def test_human_output_says_warning_not_violation(self, tmp_path):
        f = _write(tmp_path / "unbound.md", _fm())
        r = _run(str(f))
        assert r.returncode == 0
        assert "warning" in r.stdout
        assert "VIOLATION" not in r.stdout


class TestAliasStatusIsWarning:
    def test_alias_status_with_full_binding_exits_0_with_warning(self, tmp_path):
        f = _write(tmp_path / "draft.md", _fm(status="draft", node_id="node_1"))
        r = _run(str(f), "--json")
        assert r.returncode == 0, r.stdout + r.stderr
        data = json.loads(r.stdout)
        assert data["violations"] == []
        assert any(w["field"] == "status" for w in data["warnings"])

    def test_valid_status_produces_no_status_finding(self, tmp_path):
        f = _write(tmp_path / "clean.md", _fm(status="in_progress", node_id="node_1"))
        r = _run(str(f), "--json")
        data = json.loads(r.stdout)
        assert not any(v["field"] == "status" for v in data["violations"])
        assert not any(w["field"] == "status" for w in data["warnings"])


# ---------------------------------------------------------------------------
# Combined: both a status violation AND a binding violation on the same file
# ---------------------------------------------------------------------------
class TestBothViolationsOnOneFile:
    def test_bad_status_and_missing_slug_both_reported(self, tmp_path):
        f = _write(tmp_path / "double.md", _fm(status="not-a-real-status", feature_slug=None))
        r = _run(str(f), "--json")
        assert r.returncode == 2
        data = json.loads(r.stdout)
        fields = {v["field"] for v in data["violations"]}
        assert fields == {"status", "feature_slug"}


# ---------------------------------------------------------------------------
# Directory mode + aggregation
# ---------------------------------------------------------------------------
class TestDirectoryAggregation:
    def test_aggregate_across_multiple_files(self, tmp_path):
        _write(tmp_path / "a.md", _fm(slug="a", node_id="node_1"))  # clean
        _write(tmp_path / "b.md", _fm(slug="b"))  # binding warning
        _write(tmp_path / "c.md", _fm(slug="c", status="draft", node_id="node_1"))  # status warning
        _write(tmp_path / "d.md", _fm(slug="d", feature_slug=None))  # violation
        r = _run(str(tmp_path), "--json")
        assert r.returncode == 2, r.stdout + r.stderr
        data = json.loads(r.stdout)
        s = data["summary"]
        assert s["files_scanned"] == 4
        assert s["files_with_violations"] == 1
        assert s["files_with_warnings"] == 2
        assert s["violations"] == 1
        assert s["warnings"] == 2


# ---------------------------------------------------------------------------
# Usage errors
# ---------------------------------------------------------------------------
class TestUsageErrors:
    def test_missing_path_is_usage_error_exit_1(self, tmp_path):
        r = _run(str(tmp_path / "does-not-exist"))
        assert r.returncode == 1

    def test_empty_dir_no_markdown_is_usage_error_exit_1(self, tmp_path):
        r = _run(str(tmp_path))
        assert r.returncode == 1


# ---------------------------------------------------------------------------
# Read-only guarantee
# ---------------------------------------------------------------------------
class TestReadOnly:
    def test_never_writes_regardless_of_findings(self, tmp_path):
        fixtures = {
            "clean.md": _fm(slug="clean", node_id="node_1"),
            "bad_status.md": _fm(slug="bs", status="nonsense"),
            "no_slug.md": _fm(slug="ns", feature_slug=None),
            "unbound.md": _fm(slug="ub"),
        }
        paths = {name: _write(tmp_path / name, text) for name, text in fixtures.items()}
        _run(str(tmp_path), "--json")
        for name, text in fixtures.items():
            assert paths[name].read_text(encoding="utf-8") == text, name


# ---------------------------------------------------------------------------
# Advisory posture is stated in human output (D-M4-1)
# ---------------------------------------------------------------------------
class TestAdvisoryPosture:
    def test_human_output_states_advisory_posture(self, tmp_path):
        f = _write(tmp_path / "bad.md", _fm(status="nonsense"))
        r = _run(str(f))
        assert r.returncode == 2
        assert "advisory" in r.stdout.lower()


# ---------------------------------------------------------------------------
# Real-corpus smoke test — a measurement, not a gate to make pass (leg contract L1 DoD).
# ---------------------------------------------------------------------------
class TestRealCorpusSmoke:
    def test_runs_clean_against_real_repo_without_crashing(self):
        plan_root = REPO_ROOT / "docs" / "project_plans"
        assert plan_root.is_dir(), f"expected {plan_root} to exist in this checkout"
        r = _run(str(plan_root), "--json")
        # 1 would mean a usage/internal error (bad path, unreadable file, etc.) — that's the only
        # outcome this smoke test rules out. 0 (clean) and 2 (violations found) are both fine —
        # this program measures the corpus, it does not assert it is already clean.
        assert r.returncode in (0, 2), r.stdout + r.stderr
        data = json.loads(r.stdout)
        assert data["summary"]["files_scanned"] > 0
