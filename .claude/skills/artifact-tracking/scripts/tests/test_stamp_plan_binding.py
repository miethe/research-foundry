#!/usr/bin/env python3
"""Tests for stamp-plan-binding.py (Shipped Work Ledger M2, gap-3 — the file-side companion).

Offline, no network, no live `itt` CLI: every itt invocation is faked at the IttClient `runner`
seam (mirrors test_stamp_node_slug.py's fixture style). Covers:
  (a) feature-level node selection — highest node (pillar/work_area/work_package over
      atomic_task/step) wins; deterministic tie-break by node id.
  (b) primary-file selection reused from _slug_resolution (doc_type preference).
  (c) additive, format-preserving write — only missing keys inserted; unrelated bytes untouched.
  (d) never-overwrite-a-conflict rule for both itt_node_id and intenttree_tree.
  (e) idempotency — a fully-stamped file contributes 0 further writes.
  (f) dry-run — no file is ever touched without --apply.
  (g) unresolvable — a live feature_slug with no corpus plan file is reported, not fatal.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import _itt_client as itc  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


binding_mod = _load("stamp_plan_binding_mod", "stamp-plan-binding.py")


class _CaptureStdout:
    def __enter__(self):
        self._real = sys.stdout
        self._buf = io.StringIO()
        sys.stdout = self._buf
        return self

    def __exit__(self, *_exc):
        sys.stdout = self._real

    @property
    def text(self) -> str:
        return self._buf.getvalue()


def _node(node_id: str, node_type: str, feature_slug: str | None) -> dict:
    meta = {"feature_slug": feature_slug} if feature_slug else {}
    return {"id": node_id, "type": node_type, "title": node_id, "meta": meta}


@pytest.fixture()
def repo(tmp_path):
    plan_dir = tmp_path / "docs" / "project_plans"
    plan_dir.mkdir(parents=True)
    return tmp_path, plan_dir


def _write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


@pytest.fixture()
def isolated_itt_env(monkeypatch):
    monkeypatch.setattr(itc, "_CONFIG_FILE", Path("/nonexistent/config.toml"))
    monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
    monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)


def _client_with_graph(nodes: list[dict]) -> itc.IttClient:
    def runner(args: list[str]) -> itc.CliResult:
        assert args[0] == "--json"
        sub = args[1:]
        if sub[:2] == ["tree", "graph"]:
            return itc.CliResult(0, json.dumps({"nodes": nodes, "edges": []}), "")
        raise AssertionError(f"unexpected itt invocation: {sub}")

    return itc.IttClient(runner=runner, api_url="http://fake-itt.test")


class TestFeatureNodeSelection:
    def test_work_area_preferred_over_atomic_task(self):
        nodes = {
            "n_pkg": _node("n_pkg", "atomic_task", "alpha"),
            "n_area": _node("n_area", "work_area", "alpha"),
        }
        chosen = binding_mod.pick_feature_nodes(nodes)
        assert chosen["alpha"] == "n_area"

    def test_pillar_beats_everything(self):
        nodes = {
            "n_wp": _node("n_wp", "work_package", "alpha"),
            "n_pillar": _node("n_pillar", "pillar", "alpha"),
            "n_step": _node("n_step", "step", "alpha"),
        }
        chosen = binding_mod.pick_feature_nodes(nodes)
        assert chosen["alpha"] == "n_pillar"

    def test_tie_break_deterministic_by_node_id(self):
        nodes = {
            "n_b": _node("n_b", "work_area", "alpha"),
            "n_a": _node("n_a", "work_area", "alpha"),
        }
        chosen = binding_mod.pick_feature_nodes(nodes)
        assert chosen["alpha"] == "n_a"

    def test_unrecognized_type_ranks_last(self):
        nodes = {
            "n_unknown": _node("n_unknown", "some_new_type", "alpha"),
            "n_step": _node("n_step", "step", "alpha"),
        }
        chosen = binding_mod.pick_feature_nodes(nodes)
        assert chosen["alpha"] == "n_step"

    def test_nodes_without_feature_slug_are_ignored(self):
        nodes = {"n_x": _node("n_x", "work_area", None)}
        assert binding_mod.pick_feature_nodes(nodes) == {}


class TestClassifyAndApply:
    def test_additive_write_inserts_only_missing_keys(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        plan_path = plan_dir / "impl.md"
        _write(
            plan_path,
            "---\n"
            "title: My Feature\n"
            "feature_slug: alpha\n"
            "doc_type: implementation_plan\n"
            "status: completed\n"
            "---\n\n# Body untouched\n",
        )
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        rc = binding_mod.main(
            ["--tree", "tree_1", "--plan-root", str(plan_dir),
             "--repo-root", str(repo_root), "--apply"],
            client=client,
        )
        assert rc == 0
        text = plan_path.read_text(encoding="utf-8")
        assert "itt_node_id: node_A" in text
        assert "intenttree_tree: tree_1" in text
        assert "title: My Feature" in text  # unrelated bytes preserved
        assert "# Body untouched" in text

    def test_dry_run_writes_nothing(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        plan_path = plan_dir / "impl.md"
        original = (
            "---\nfeature_slug: alpha\ndoc_type: implementation_plan\n---\n\n# Body\n"
        )
        _write(plan_path, original)
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        rc = binding_mod.main(
            ["--tree", "tree_1", "--plan-root", str(plan_dir), "--repo-root", str(repo_root)],
            client=client,
        )
        assert rc == 0
        assert plan_path.read_text(encoding="utf-8") == original  # byte-for-byte untouched

    def test_conflicting_itt_node_id_is_never_overwritten(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        plan_path = plan_dir / "impl.md"
        original = (
            "---\nfeature_slug: alpha\ndoc_type: implementation_plan\n"
            "itt_node_id: node_OTHER\n---\n\n# Body\n"
        )
        _write(plan_path, original)
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = binding_mod.main(
                ["--tree", "tree_1", "--plan-root", str(plan_dir),
                 "--repo-root", str(repo_root), "--apply", "--json"],
                client=client,
            )
        assert rc == 2
        assert plan_path.read_text(encoding="utf-8") == original  # untouched
        payload = json.loads(stdout_buf.text)
        assert len(payload["conflicts"]) == 1
        assert payload["conflicts"][0]["existing_itt_node_id"] == "node_OTHER"
        assert payload["conflicts"][0]["resolved_itt_node_id"] == "node_A"

    def test_conflicting_intenttree_tree_is_never_overwritten(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        plan_path = plan_dir / "impl.md"
        original = (
            "---\nfeature_slug: alpha\ndoc_type: implementation_plan\n"
            "itt_node_id: node_A\nintenttree_tree: tree_OLD\n---\n\n# Body\n"
        )
        _write(plan_path, original)
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        rc = binding_mod.main(
            ["--tree", "tree_1", "--plan-root", str(plan_dir),
             "--repo-root", str(repo_root), "--apply"],
            client=client,
        )
        assert rc == 2
        assert plan_path.read_text(encoding="utf-8") == original

    def test_idempotent_already_correct_file_is_untouched(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        plan_path = plan_dir / "impl.md"
        original = (
            "---\nfeature_slug: alpha\ndoc_type: implementation_plan\n"
            "itt_node_id: node_A\nintenttree_tree: tree_1\n---\n\n# Body\n"
        )
        _write(plan_path, original)
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = binding_mod.main(
                ["--tree", "tree_1", "--plan-root", str(plan_dir),
                 "--repo-root", str(repo_root), "--apply", "--json"],
                client=client,
            )
        assert rc == 0
        payload = json.loads(stdout_buf.text)
        assert payload["summary"]["already_correct"] == 1
        assert payload["summary"]["applied"] == 0
        assert plan_path.read_text(encoding="utf-8") == original

    def test_unresolvable_slug_is_reported_but_not_fatal(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        # No plan file at all carries "zeta" — a live node.meta.feature_slug the corpus never named
        # (e.g. resolved purely via the node-side retroactive_binding path).
        client = _client_with_graph([_node("node_Z", "work_area", "zeta")])

        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = binding_mod.main(
                ["--tree", "tree_1", "--plan-root", str(plan_dir),
                 "--repo-root", str(repo_root), "--json"],
                client=client,
            )
        assert rc == 0  # unresolvable is informational, not a conflict
        payload = json.loads(stdout_buf.text)
        assert payload["summary"]["unresolvable"] == 1
        assert payload["unresolvable"][0]["slug"] == "zeta"

    def test_doc_type_preference_picks_implementation_plan_over_prd(self, repo, isolated_itt_env):
        repo_root, plan_dir = repo
        prd_path = plan_dir / "a-prd.md"
        impl_path = plan_dir / "b-impl.md"
        _write(prd_path, "---\nfeature_slug: alpha\ndoc_type: prd\n---\n\n# PRD\n")
        _write(impl_path, "---\nfeature_slug: alpha\ndoc_type: implementation_plan\n---\n\n# Impl\n")
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        rc = binding_mod.main(
            ["--tree", "tree_1", "--plan-root", str(plan_dir),
             "--repo-root", str(repo_root), "--apply"],
            client=client,
        )
        assert rc == 0
        assert "itt_node_id: node_A" in impl_path.read_text(encoding="utf-8")
        assert "itt_node_id" not in prd_path.read_text(encoding="utf-8")

    def test_only_missing_key_queued_when_one_already_present(self, repo, isolated_itt_env):
        """A file with a correct itt_node_id but missing intenttree_tree gets ONLY the missing
        key added — never a spurious rewrite of the already-correct one."""
        repo_root, plan_dir = repo
        plan_path = plan_dir / "impl.md"
        original = (
            "---\nfeature_slug: alpha\ndoc_type: implementation_plan\n"
            "itt_node_id: node_A\n---\n\n# Body\n"
        )
        _write(plan_path, original)
        client = _client_with_graph([_node("node_A", "work_area", "alpha")])

        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = binding_mod.main(
                ["--tree", "tree_1", "--plan-root", str(plan_dir),
                 "--repo-root", str(repo_root), "--apply", "--json"],
                client=client,
            )
        assert rc == 0
        payload = json.loads(stdout_buf.text)
        assert payload["would_stamp"][0]["additions"] == {"intenttree_tree": "tree_1"}
        text = plan_path.read_text(encoding="utf-8")
        assert text.count("itt_node_id: node_A") == 1  # not duplicated
        assert "intenttree_tree: tree_1" in text
