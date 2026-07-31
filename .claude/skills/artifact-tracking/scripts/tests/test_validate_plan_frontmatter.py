#!/usr/bin/env python3
"""Tests for validate-plan-frontmatter.py + the shared _status_aliases module.

Covers (per the Shipped Work Ledger M1 deliverable):
  (a) the full alias map — every alias resolves to a NodeStatus, with the ratified maturity splits;
  (b) the exit-code gate — clean/alias dirs exit 0, an invalid-status fixture exits non-zero (2);
  (c) autofix is ADDITIVE + FORMAT-PRESERVING — only the status value token changes, a
      planning_maturity line is inserted adjacently, and NO unrelated line changes;
  (d) hand-review values are flagged as violations, never mutated.

Offline, no network. Subprocess-driven for CLI/exit-code behavior (matching the sibling test
files' style); direct-import for the alias-map unit coverage.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
LINTER = SCRIPTS_DIR / "validate-plan-frontmatter.py"

# Direct import of the shared vocabulary (underscore-prefixed → importable once on sys.path).
sys.path.insert(0, str(SCRIPTS_DIR))
import _status_aliases as sa  # noqa: E402


def _load_linter():
    """Import the hyphen-named linter module for white-box helper tests."""
    spec = importlib.util.spec_from_file_location("vpf_mod", LINTER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LINTER), *args], capture_output=True, text=True
    )


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# (a) The full alias map
# ---------------------------------------------------------------------------
class TestAliasMap:
    def test_every_alias_target_is_a_node_status(self):
        for alias, spec in sa.STATUS_ALIASES.items():
            assert spec["status"] in sa.NODE_STATUSES, f"{alias} -> non-NodeStatus"

    def test_node_status_enum_is_the_ratified_15(self):
        assert len(sa.NODE_STATUSES) == 15
        # A few load-bearing members that the alias map targets.
        for v in ("not_started", "ready", "in_progress", "completed",
                  "waiting_human", "waiting_review"):
            assert v in sa.NODE_STATUSES

    def test_done_synonyms_map_to_completed_plus_shipped(self):
        for alias in ("complete", "finalized", "concluded", "shipped", "graduated"):
            status, maturity, cat = sa.resolve(alias)
            assert cat == sa.ALIAS
            assert status == "completed", alias
            assert maturity == "shipped", alias

    def test_impl_complete_pending_human_gate_maps_to_waiting_human_not_completed(self):
        status, maturity, cat = sa.resolve("implementation_complete_pending_human_gate")
        assert (status, maturity, cat) == ("waiting_human", None, sa.ALIAS)

    def test_in_progress_spelling_normalizes(self):
        assert sa.resolve("in-progress") == ("in_progress", None, sa.ALIAS)

    def test_ccdash_up_map(self):
        assert sa.resolve("pending") == ("not_started", None, sa.ALIAS)
        assert sa.resolve("review") == ("waiting_review", None, sa.ALIAS)

    def test_maturity_carrying_planning_states(self):
        assert sa.resolve("draft") == ("not_started", "draft", sa.ALIAS)
        assert sa.resolve("planning") == ("not_started", "draft", sa.ALIAS)
        assert sa.resolve("proposed") == ("not_started", "proposed", sa.ALIAS)
        assert sa.resolve("accepted") == ("ready", "accepted", sa.ALIAS)

    def test_valid_nodestatus_is_valid_not_alias(self):
        status, maturity, cat = sa.resolve("completed")
        assert (status, maturity, cat) == ("completed", None, sa.VALID)

    def test_whitespace_and_quotes_and_case_normalize(self):
        # trailing whitespace on a valid value → still valid, untouched target
        assert sa.classify("completed   ") == sa.VALID
        # done-synonym with trailing whitespace normalizes and maps
        assert sa.resolve("complete   ")[0] == "completed"
        # quotes + case
        assert sa.resolve('"Draft"') == ("not_started", "draft", sa.ALIAS)

    def test_hand_review_values_never_resolve(self):
        for v in ("reconciled-for-planning", "handoff-for-planning",
                  "active | paused | blocked", "totally-made-up"):
            status, maturity, cat = sa.resolve(v)
            assert cat == sa.HAND_REVIEW, v
            assert status is None and maturity is None
            assert not sa.is_acceptable(v)

    def test_known_hand_review_set_is_disjoint_from_maps(self):
        for v in sa.HAND_REVIEW_VALUES:
            assert sa.normalize_token(v) not in sa.NODE_STATUSES
            assert sa.normalize_token(v) not in sa.STATUS_ALIASES


# ---------------------------------------------------------------------------
# (b) Exit-code gate
# ---------------------------------------------------------------------------
_MIN_FM = (
    "---\n"
    "it_schema: 1\n"
    "feature_slug: {slug}\n"
    "title: \"{slug}\"\n"
    "status: {status}\n"
    "tier: 3\n"
    "priority: P1\n"
    "points: 5\n"
    "---\n\n# Body\n"
)


class TestExitCodes:
    def test_clean_valid_status_dir_exits_0(self, tmp_path):
        _write(tmp_path / "a.md", _MIN_FM.format(slug="a", status="completed"))
        _write(tmp_path / "b.md", _MIN_FM.format(slug="b", status="in_progress"))
        r = _run(str(tmp_path))
        assert r.returncode == 0, r.stdout + r.stderr

    def test_alias_only_dir_exits_0_in_check_mode(self, tmp_path):
        # aliases are losslessly resolvable → clean in check mode.
        _write(tmp_path / "a.md", _MIN_FM.format(slug="a", status="draft"))
        _write(tmp_path / "b.md", _MIN_FM.format(slug="b", status="complete"))
        r = _run(str(tmp_path))
        assert r.returncode == 0, r.stdout + r.stderr
        assert "would-fix" in r.stdout

    def test_invalid_status_fixture_exits_nonzero_and_names_file_and_value(self, tmp_path):
        f = _write(tmp_path / "bad.md", _MIN_FM.format(slug="bad", status="totally_bogus_status"))
        r = _run(str(tmp_path))
        assert r.returncode == 2, r.stdout + r.stderr
        assert "bad.md" in r.stdout
        assert "totally_bogus_status" in r.stdout
        assert f.exists()

    def test_hand_review_placeholder_exits_2(self, tmp_path):
        _write(tmp_path / "r.md", _MIN_FM.format(slug="r", status="reconciled-for-planning"))
        r = _run(str(tmp_path))
        assert r.returncode == 2, r.stdout + r.stderr
        assert "HAND-REVIEW" in r.stdout

    def test_single_file_arg_works(self, tmp_path):
        f = _write(tmp_path / "one.md", _MIN_FM.format(slug="one", status="completed"))
        r = _run(str(f))
        assert r.returncode == 0, r.stdout + r.stderr

    def test_missing_status_is_not_a_violation(self, tmp_path):
        # A file with no top-level status is advisory, not a status violation → exit 0.
        _write(tmp_path / "n.md", "---\ntitle: no-status\ntier: 3\n---\n\n# Body\n")
        r = _run(str(tmp_path))
        assert r.returncode == 0, r.stdout + r.stderr

    def test_missing_path_arg_is_usage_error_exit_1(self, tmp_path):
        r = _run(str(tmp_path / "does-not-exist"))
        assert r.returncode == 1


# ---------------------------------------------------------------------------
# (c) Autofix is additive + format-preserving
# ---------------------------------------------------------------------------
_FORMAT_FIXTURE = """---
it_schema: 1
feature_slug: demo
title: "Demo Plan"
description: "keep me exactly"
status: draft   # legacy synonym, keep this comment
tier: 3
priority: P1
points: 5
tags:
  - alpha
  - beta
decisions:
  - decision: "d"
    status: accepted
---

# Heading
Body line mentioning status: pending as prose.
"""


class TestAutofixFormatPreserving:
    def test_apply_changes_only_status_value_and_inserts_maturity(self, tmp_path):
        f = _write(tmp_path / "p.md", _FORMAT_FIXTURE)
        r = _run(str(f), "--apply")
        assert r.returncode == 0, r.stdout + r.stderr

        orig_lines = _FORMAT_FIXTURE.splitlines()
        new_lines = f.read_text(encoding="utf-8").splitlines()

        # Exactly one line inserted (the planning_maturity line).
        assert len(new_lines) == len(orig_lines) + 1

        si = next(i for i, ln in enumerate(orig_lines) if ln.startswith("status:"))
        # Everything before the status line is byte-identical.
        assert new_lines[:si] == orig_lines[:si]
        # The status line: only the value token changed; comment + spacing preserved.
        assert new_lines[si] == "status: not_started   # legacy synonym, keep this comment"
        # planning_maturity inserted immediately after, at column 0.
        assert new_lines[si + 1] == "planning_maturity: draft"
        # Everything after is byte-identical (offset by the single insertion).
        assert new_lines[si + 2:] == orig_lines[si + 1:]

    def test_nested_and_body_statuses_untouched(self, tmp_path):
        f = _write(tmp_path / "p.md", _FORMAT_FIXTURE)
        _run(str(f), "--apply")
        new = f.read_text(encoding="utf-8")
        assert "    status: accepted" in new           # nested decisions[] status untouched
        assert "Body line mentioning status: pending as prose." in new  # body prose untouched

    def test_quoting_preserved_on_rewrite(self, tmp_path):
        f = _write(tmp_path / "q.md", _MIN_FM.format(slug="q", status='"complete"'))
        _run(str(f), "--apply")
        new = f.read_text(encoding="utf-8")
        assert 'status: "completed"' in new
        assert "planning_maturity: shipped" in new

    def test_valid_status_left_entirely_untouched(self, tmp_path):
        original = _MIN_FM.format(slug="v", status="completed")
        f = _write(tmp_path / "v.md", original)
        r = _run(str(f), "--apply")
        assert r.returncode == 0
        assert f.read_text(encoding="utf-8") == original          # byte-identical
        assert "planning_maturity" not in f.read_text(encoding="utf-8")

    def test_planning_maturity_not_overwritten_when_present(self, tmp_path):
        text = (
            "---\n"
            "it_schema: 1\n"
            "feature_slug: pm\n"
            "status: draft\n"
            "planning_maturity: proposed\n"
            "tier: 3\n"
            "priority: P1\n"
            "points: 5\n"
            "---\n\n# Body\n"
        )
        f = _write(tmp_path / "pm.md", text)
        _run(str(f), "--apply")
        new = f.read_text(encoding="utf-8")
        assert "status: not_started" in new
        # existing maturity preserved; NOT overwritten and NOT duplicated
        assert new.count("planning_maturity:") == 1
        assert "planning_maturity: proposed" in new

    def test_check_mode_never_writes(self, tmp_path):
        original = _MIN_FM.format(slug="c", status="draft")
        f = _write(tmp_path / "c.md", original)
        r = _run(str(f))  # no --apply
        assert r.returncode == 0
        assert f.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# (d) Hand-review values are flagged, not mutated
# ---------------------------------------------------------------------------
class TestHandReviewNotMutated:
    def test_apply_does_not_touch_hand_review_file(self, tmp_path):
        for status in ("reconciled-for-planning", "handoff-for-planning",
                       "some-unknown-status"):
            original = _MIN_FM.format(slug="h", status=status)
            f = _write(tmp_path / f"{status}.md", original)
            r = _run(str(f), "--apply")
            assert r.returncode == 2, (status, r.stdout)
            assert f.read_text(encoding="utf-8") == original  # unchanged
            assert "HAND-REVIEW" in r.stdout


# ---------------------------------------------------------------------------
# JSON output + schema sourcing
# ---------------------------------------------------------------------------
class TestJsonOutput:
    def test_json_summary_and_violations(self, tmp_path):
        _write(tmp_path / "a.md", _MIN_FM.format(slug="a", status="draft"))
        _write(tmp_path / "b.md", _MIN_FM.format(slug="b", status="completed"))
        _write(tmp_path / "c.md", _MIN_FM.format(slug="c", status="reconciled-for-planning"))
        r = _run(str(tmp_path), "--json")
        assert r.returncode == 2, r.stdout + r.stderr
        data = json.loads(r.stdout)
        assert data["mode"] == "check"
        s = data["summary"]
        assert s["alias"] == 1 and s["valid"] == 1 and s["hand_review"] == 1
        assert s["would_change_by_value"].get("draft") == 1
        assert len(data["violations"]) == 1
        assert data["violations"][0]["value"] == "reconciled-for-planning"
        assert any(c["from"] == "draft" and c["to"] == "not_started" for c in data["changes"])
        assert data["exit"] == 2

    def test_schema_parsed_from_doc(self, tmp_path):
        # The linter resolves the schema doc from its own script dir (the real repo), so the
        # MUST set is parsed, not the hardcoded fallback.
        _write(tmp_path / "a.md", _MIN_FM.format(slug="a", status="completed"))
        r = _run(str(tmp_path), "--json")
        data = json.loads(r.stdout)
        assert data["schema_source"] == "parsed"
        assert "status" in data["must_set_plan"]
        assert data["effort_aliases"] == ["points", "effort_estimate", "estimated_points"]


# ---------------------------------------------------------------------------
# White-box: schema-block header-only fallback parse
# ---------------------------------------------------------------------------
class TestSchemaBlockParsing:
    def test_header_only_parse_recovers_must_sets(self):
        vpf = _load_linter()
        # A block whose fields: list is invalid YAML (bare [] flow scalar) — header must still parse.
        block = (
            "```yaml\n"
            "it_schema: 1\n"
            "must_set_plan:\n"
            "  - status\n"
            "  - effort\n"
            "effort_aliases: [points, effort_estimate]\n"
            "must_set_task:\n"
            "  - node_type\n"
            "fields:\n"
            "  - {name: meta_plan_refs, type: path[]}\n"
            "```\n"
        )
        parsed = vpf._extract_schema_block(block)
        assert parsed is not None
        assert parsed["must_set_plan"] == ["status", "effort"]
        assert parsed["effort_aliases"] == ["points", "effort_estimate"]
