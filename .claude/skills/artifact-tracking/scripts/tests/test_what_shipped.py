#!/usr/bin/env python3
"""Tests for `what-shipped.py` — Shipped Work Ledger M3 L4, the AC demo query.

Offline, no network, no live `itt` CLI: every read goes through the fake `IttClient`
`http_call`/`runner` seams (`get_node_full` and `tree_nodes` are both raw-HTTP GETs — see
`_itt_client.py`). Covers:
  (a) a clean join                     — feature_slug + plan_ref that exists on disk, with PR
                                           and commit evidence.
  (b) a dangling plan_ref               — plan_ref set but the file does not exist on disk.
  (c) an unjoinable node                — no feature_slug at all; must be reported, not dropped.
  (d) a node with no evidence           — joinable, plan_ref resolves, but zero external links /
                                           completion evidence.
  (e) the coverage-count arithmetic     — the summary counts match the row-level data exactly.
  (f) --json shape                      — the machine-readable payload carries the same fields.
  (g) corpus fallback for plan_ref      — a node with feature_slug but no meta.plan_ref resolves
                                           via the plan corpus instead of being left unresolved.
  (h) --limit truncation is honest      — total_completed always reflects the untruncated count.
"""

from __future__ import annotations

import importlib.util
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


ws_mod = _load("what_shipped_mod", "what-shipped.py")


def _node(node_id: str, title: str, status: str, meta: dict[str, Any] | None = None) -> dict:
    return {"id": node_id, "title": title, "status": status, "meta": meta or {}, "tags": []}


class FakeWorld:
    """A fake tree + a fake per-node `get_node_full` payload store, wired to a fake IttClient
    entirely through the raw-HTTP `http_call` seam (this module never shells out to `itt`)."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.nodes: list[dict] = []
        self.node_full: dict[str, dict] = {}
        self.http_calls: list[dict[str, Any]] = []

    def add_node(self, node: dict, full_extra: dict | None = None) -> None:
        self.nodes.append(node)
        self.node_full[node["id"]] = {
            **node,
            "external_links": [],
            "completion_evidence": [],
            "validation_runs": [],
            **(full_extra or {}),
        }

    def http_call(self, url: str, method: str, body: dict, headers: dict) -> itc.HttpResult:
        self.http_calls.append({"url": url, "method": method, "body": body})
        assert method == "GET"
        if url.endswith("/graph"):
            return itc.HttpResult(200, json.dumps({"nodes": self.nodes, "edges": []}))
        # /api/v1/nodes/{id}?include=...
        node_id = url.rsplit("/", 1)[-1].split("?")[0]
        payload = self.node_full.get(node_id)
        if payload is None:
            return itc.HttpResult(404, json.dumps({"detail": "not found"}))
        return itc.HttpResult(200, json.dumps(payload))

    def client(self) -> itc.IttClient:
        return itc.IttClient(http_call=self.http_call, api_url="http://fake-itt.test")


@pytest.fixture()
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(itc, "_CONFIG_FILE", Path("/nonexistent/config.toml"))
    monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
    monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)

    repo_root = tmp_path
    plan_dir = repo_root / "docs" / "project_plans"
    plan_dir.mkdir(parents=True)

    # A clean join: feature_slug + plan_ref present + file exists, with PR + commit evidence.
    (plan_dir / "alpha-v1.md").write_text(
        "---\nfeature_slug: alpha\nstatus: completed\ndoc_type: implementation_plan\n---\n\n# Alpha\n",
        encoding="utf-8",
    )
    # A corpus-fallback join: feature_slug present in corpus, but the node has no meta.plan_ref.
    (plan_dir / "gamma-v1.md").write_text(
        "---\nfeature_slug: gamma\nstatus: completed\ndoc_type: implementation_plan\n---\n\n# Gamma\n",
        encoding="utf-8",
    )

    w = FakeWorld(repo_root)

    w.add_node(
        _node("node_A", "Alpha Feature", "completed",
              {"feature_slug": "alpha", "plan_ref": "docs/project_plans/alpha-v1.md"}),
        full_extra={
            "external_links": [
                {"system": "github", "external_id": "32",
                 "external_path": "https://github.com/miethe/agentic_meta_dev/pull/32"},
                {"system": "git", "external_id": "b9b4613", "external_path": None},
            ],
            "completion_evidence": [
                {"kind": "git_merge", "ref_value": "b9b4613abc", "delivery_class": "shipped"},
                {"kind": "validation", "label": "pytest -q", "ref_value": None},
            ],
        },
    )

    # Dangling plan_ref: meta.plan_ref points at a file that does not exist on disk.
    w.add_node(
        _node("node_B", "Beta Feature", "completed",
              {"feature_slug": "beta", "plan_ref": "docs/project_plans/does-not-exist.md"}),
    )

    # Unjoinable: no feature_slug at all (the M2-measured common case).
    w.add_node(_node("node_C", "Hand-created node", "completed", {}))

    # Joinable, resolves via corpus (no meta.plan_ref of its own), zero evidence.
    w.add_node(
        _node("node_D", "Gamma Feature", "completed", {"feature_slug": "gamma"}),
    )

    # Not completed — must never appear anywhere in the report.
    w.add_node(_node("node_E", "In Progress Feature", "in_progress", {"feature_slug": "epsilon"}))

    return w


class TestCleanJoin:
    def test_clean_join_has_plan_ref_ok_and_evidence(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        rows = {r["node_id"]: r for r in report["joinable"]}
        row_a = rows["node_A"]
        assert row_a["slug"] == "alpha"
        assert row_a["plan_ref"] == "docs/project_plans/alpha-v1.md"
        assert row_a["plan_ref_source"] == "node_meta"
        assert row_a["plan_ref_exists"] is True
        assert row_a["dangling"] is False
        assert "https://github.com/miethe/agentic_meta_dev/pull/32" in row_a["pr_links"]
        assert any("b9b4613" in c for c in row_a["commit_links"])
        assert row_a["validation_evidence"]


class TestDanglingPlanRef:
    def test_dangling_plan_ref_is_flagged_not_hidden(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        row_b = next(r for r in report["joinable"] if r["node_id"] == "node_B")
        assert row_b["plan_ref"] == "docs/project_plans/does-not-exist.md"
        assert row_b["plan_ref_exists"] is False
        assert row_b["dangling"] is True
        assert report["counts"]["dangling_plan_ref"] == 1


class TestUnjoinableNode:
    def test_unjoinable_node_is_reported_not_dropped(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        unjoinable_ids = {r["node_id"] for r in report["unjoinable"]}
        assert "node_C" in unjoinable_ids
        row_c = next(r for r in report["unjoinable"] if r["node_id"] == "node_C")
        assert row_c["title"] == "Hand-created node"
        # never fetched via get_node_full — no join key to fetch details for
        assert not any(c["url"].endswith("/node_C?include=completion_evidence,external_links,"
                                          "validation_runs") for c in world.http_calls)

    def test_only_completed_nodes_are_considered(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        all_ids = {r["node_id"] for r in report["joinable"]} | {
            r["node_id"] for r in report["unjoinable"]
        }
        assert "node_E" not in all_ids
        assert report["total_completed"] == 4  # A, B, C, D — not E


class TestNoEvidenceNode:
    def test_corpus_fallback_resolves_plan_ref_with_no_evidence(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        row_d = next(r for r in report["joinable"] if r["node_id"] == "node_D")
        assert row_d["plan_ref"] == "docs/project_plans/gamma-v1.md"
        assert row_d["plan_ref_source"] == "corpus"
        assert row_d["plan_ref_exists"] is True
        assert row_d["pr_links"] == []
        assert row_d["commit_links"] == []
        assert row_d["validation_evidence"] == []


class TestCoverageArithmetic:
    def test_counts_match_row_level_data(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        c = report["counts"]
        assert c["completed"] == 4
        assert c["joinable"] == 3  # A, B, D
        assert c["unjoinable"] == 1  # C
        assert c["joinable"] + c["unjoinable"] == c["completed"]
        assert c["dangling_plan_ref"] == 1  # B
        assert c["with_pr_or_commit_evidence"] == 1  # A only
        assert c["with_validation_evidence"] == 1  # A only

    def test_no_node_ever_appears_in_both_buckets(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        joinable_ids = {r["node_id"] for r in report["joinable"]}
        unjoinable_ids = {r["node_id"] for r in report["unjoinable"]}
        assert not (joinable_ids & unjoinable_ids)


class TestJsonShape:
    def test_json_output_round_trips_via_cli(self, world, capsys):
        rc = ws_mod.main(
            ["--tree", "t1", "--plan-root", str(world.repo_root / "docs" / "project_plans"),
             "--repo-root", str(world.repo_root), "--json"],
            client=world.client(),
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["tree"] == "t1"
        assert "counts" in payload and "joinable" in payload and "unjoinable" in payload
        assert payload["counts"]["completed"] == 4
        assert len(payload["joinable"]) == 3
        assert len(payload["unjoinable"]) == 1

    def test_human_output_states_honest_coverage_tail(self, world, capsys):
        rc = ws_mod.main(
            ["--tree", "t1", "--plan-root", str(world.repo_root / "docs" / "project_plans"),
             "--repo-root", str(world.repo_root)],
            client=world.client(),
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "4 completed nodes" in out
        assert "3 joinable" in out
        assert "1 unjoinable" in out
        assert "1 with PR/commit evidence" in out
        assert "1 with validation evidence" in out
        assert "node_C" in out  # unjoinable node is actually listed, not just counted


class TestLimitTruncation:
    def test_limit_never_shrinks_the_reported_total_completed(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root, limit=1
        )
        assert report["total_completed"] == 4  # unaffected by --limit
        assert report["processed_completed"] == 1
        assert report["truncated"] is True
        assert len(report["joinable"]) + len(report["unjoinable"]) == 1

    def test_no_limit_processes_every_completed_node(self, world):
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        assert report["truncated"] is False
        assert report["processed_completed"] == report["total_completed"] == 4

    def test_unjoinable_node_never_triggers_a_detail_fetch(self, world):
        # node_C has no feature_slug; get_node_full must only be called for the 3 joinable nodes.
        client = world.client()
        ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root
        )
        detail_calls = [c for c in world.http_calls if not c["url"].endswith("/graph")]
        fetched_ids = {c["url"].rsplit("/", 1)[-1].split("?")[0] for c in detail_calls}
        assert fetched_ids == {"node_A", "node_B", "node_D"}


class TestSinceFilter:
    def test_since_keeps_nodes_with_unknown_timestamp(self, world):
        # None of the fixture nodes carry completed_at/updated_at/created_at, so every node's
        # timestamp is "unknown" — --since must keep them (never silently drop for lack of data).
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root,
            since=ws_mod._parse_since("2026-01-01"),
        )
        assert report["filtered_completed"] == 4
        assert report["unknown_timestamp"] == 4

    def test_since_excludes_nodes_older_than_cutoff(self, world):
        world.nodes.append(_node(
            "node_OLD", "Old shipped feature", "completed",
            {"feature_slug": "old-one"},
        ))
        world.nodes[-1]["completed_at"] = "2020-01-01T00:00:00Z"
        world.node_full["node_OLD"] = {
            **world.nodes[-1], "external_links": [], "completion_evidence": [], "validation_runs": [],
        }
        client = world.client()
        report = ws_mod.build_ledger(
            client, "t1", world.repo_root / "docs" / "project_plans", world.repo_root,
            since=ws_mod._parse_since("2026-01-01"),
        )
        all_ids = {r["node_id"] for r in report["joinable"]} | {
            r["node_id"] for r in report["unjoinable"]
        }
        assert "node_OLD" not in all_ids


class TestCliUsageErrors:
    def test_invalid_since_returns_1(self, world):
        rc = ws_mod.main(
            ["--tree", "t1", "--since", "not-a-date"], client=world.client()
        )
        assert rc == 1

    def test_negative_limit_returns_1(self, world):
        rc = ws_mod.main(
            ["--tree", "t1", "--limit", "-1"], client=world.client()
        )
        assert rc == 1

    def test_itt_error_surfaces_as_exit_1(self, tmp_path):
        def failing_http(url, method, body, headers):
            return itc.HttpResult(500, "boom")

        client = itc.IttClient(http_call=failing_http, api_url="http://fake-itt.test")
        rc = ws_mod.main(["--tree", "t1", "--repo-root", str(tmp_path)], client=client)
        assert rc == 1
