#!/usr/bin/env python3
"""Tests for the M4 L4 creation-time feature_slug stamp in intenttree_capture.py.

`capture_feature()` now stamps `meta.feature_slug` (+`meta.plan_ref`) onto the nodes it just
created, so the ledger join is established AT creation instead of by a later stamp-node-slug.py
pass. The stamp reuses stamp-node-slug.py's resolution/conflict/merge logic verbatim (not a
re-implementation).

Offline, no network, no live `itt` CLI:
  - the register + import HTTP path is faked at the module-level `_req` seam (monkeypatched);
  - the node write path is faked at the injectable `_itt_client.IttClient` seam, EXACTLY as the
    stamp-node-slug.py tests do.

The fake IntentTree world models the LIVE post-import state (convention 6 / lesson A2): the stored
node row carries `meta` as a real dict, and the bindings table carries the `feature:<slug>` entry
the server writes for the feature anchor at import — a fake that merely echoed the request shape
would hide a real defect. Covered:
  (a) fresh capture stamps the slug on the anchor + subtree, no separate stamper run;
  (b) plan_ref backfills from the corpus for the captured slug;
  (c) a re-run is idempotent (0 writes);
  (d) a node carrying a CONFLICTING feature_slug is reported and NEVER overwritten (FR-7),
      and capture_feature reports ok=False;
  (e) pre-existing meta keys survive the stamp write (merge, not replace);
  (f) dry-run never stamps.
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


cap_mod = _load("intenttree_capture_mod", "intenttree_capture.py")

SID = "srcart_new"
SLUG = "gamma"


# ---------------------------------------------------------------------------
# Fake IntentTree world — the node-write seam (IttClient), mirroring the live row shape.
# ---------------------------------------------------------------------------
def _node(node_id: str, meta: dict[str, Any]) -> dict:
    return {"id": node_id, "type": "work_package", "title": node_id, "meta": dict(meta)}


def _make_world(tmp_path: Path) -> dict[str, Any]:
    repo_root = tmp_path
    plan_dir = repo_root / "docs" / "project_plans"
    plan_dir.mkdir(parents=True)
    # The captured feature's plan file — carries the slug so plan_ref backfills to it.
    (plan_dir / "gamma.md").write_text(
        f"---\nfeature_slug: {SLUG}\nstatus: in_progress\ndoc_type: implementation_plan\n---\n\n"
        "# Gamma\n",
        encoding="utf-8",
    )

    # Post-import live state: the anchor + one member node, both created empty; the server has
    # already written the `feature:<slug>` binding for the anchor and a phase binding for the
    # member, both against SID.
    node_store = {
        "node_anchor": _node("node_anchor", {}),
        "node_member": _node("node_member", {"other_key": "keep-me"}),
    }
    bindings_items = [
        {"node_id": "node_anchor", "source_artifact_id": SID, "source_task_id": f"feature:{SLUG}"},
        {"node_id": "node_member", "source_artifact_id": SID, "source_task_id": "phase:Phase 1"},
    ]
    return {
        "repo_root": repo_root,
        "plan_root": plan_dir,
        "node_store": node_store,
        "bindings_items": bindings_items,
    }


def _make_fake_runner(node_store: dict[str, dict], bindings_items: list[dict]):
    """Fake the read seam (`itt --json ...`) exactly as the stamper tests do."""
    def runner(args: list[str]) -> itc.CliResult:
        assert args[0] == "--json", "the client must always pass the GLOBAL --json flag first"
        sub = args[1:]
        if sub[:2] == ["tree", "graph"]:
            return itc.CliResult(0, json.dumps({"nodes": list(node_store.values()), "edges": []}), "")
        if sub[:2] == ["sync", "status"]:
            return itc.CliResult(
                0, json.dumps({"items": bindings_items, "next_cursor": None,
                               "total": len(bindings_items)}), "")
        if sub[:2] == ["node", "get"]:
            return itc.CliResult(0, json.dumps(node_store[sub[2]]), "")
        raise AssertionError(f"unexpected itt invocation: {sub}")

    return runner


def _make_fake_http_call(node_store: dict[str, dict]):
    """Fake the PATCH write seam with the real whole-meta-replace semantics."""
    http_calls: list[dict[str, Any]] = []

    def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
        http_calls.append({"url": url, "method": method, "body": body})
        assert method == "PATCH"
        assert isinstance(body, dict) and set(body.keys()) == {"meta"}
        assert isinstance(body["meta"], dict)
        node_id = url.rsplit("/", 1)[-1]
        node_store[node_id]["meta"] = body["meta"]
        return itc.HttpResult(200, json.dumps(node_store[node_id]))

    return http_call, http_calls


def _make_fake_req():
    """Fake intenttree_capture._req — the register + import HTTP path.

    Returns (req, call_log). Models: source-artifact register (returns SID), the visibility poll
    (GET 200), and the work-item-sync import (returns counts).
    """
    calls: list[tuple[str, str]] = []

    def req(api: str, method: str, path: str, body: dict | None = None):
        calls.append((method, path))
        if method == "POST" and path == "/api/v1/source-artifacts":
            return 200, {"source_artifact_id": SID}
        if method == "GET" and path.startswith("/api/v1/source-artifacts/"):
            return 200, {"source_artifact_id": SID}
        if method == "POST" and path == "/api/v1/work-item-sync/import":
            return 200, {"counts": {"inserts": 2, "updates": 0, "edges_created": 1}}
        raise AssertionError(f"unexpected _req: {method} {path}")

    return req, calls


@pytest.fixture()
def world(tmp_path):
    return _make_world(tmp_path)


@pytest.fixture()
def client(world, monkeypatch):
    # Isolate config resolution from any real ~/.config/intenttree/config.toml + env.
    monkeypatch.setattr(itc, "_CONFIG_FILE", Path("/nonexistent/config.toml"))
    monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
    monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)
    runner = _make_fake_runner(world["node_store"], world["bindings_items"])
    http_call, http_calls = _make_fake_http_call(world["node_store"])
    c = itc.IttClient(runner=runner, http_call=http_call, api_url="http://fake-itt.test")
    return c, http_calls


@pytest.fixture()
def feat():
    return {
        "slug": SLUG,
        "title": "Gamma",
        "kind": "implementation_plan",
        "artifact_path": "docs/project_plans/gamma.md",
        "tasks": [{"id": "T1", "status": "not_started"}],
    }


def _capture(world, client_tuple, feat, monkeypatch, apply: bool):
    c, http_calls = client_tuple
    req, req_calls = _make_fake_req()
    monkeypatch.setattr(cap_mod, "_req", req)
    # No real sleep between import retries (there are none on the happy path, but be safe).
    monkeypatch.setattr(cap_mod.time, "sleep", lambda *_a, **_k: None)
    res = cap_mod.capture_feature(
        "http://fake-itt.test", "ws1", "t1", feat, apply,
        repo_root=str(world["repo_root"]), plan_root=str(world["plan_root"]),
        itt_client=c,
    )
    return res, http_calls, req_calls


class TestCreationTimeSlugStamp:
    def test_fresh_capture_stamps_anchor_and_subtree(self, world, client, feat, monkeypatch):
        res, _http, _req = _capture(world, client, feat, monkeypatch, apply=True)
        assert res["ok"] is True
        assert res["stamp"]["ok"] is True
        # both the anchor and its member node carry the slug — no separate stamper run needed.
        assert world["node_store"]["node_anchor"]["meta"]["feature_slug"] == SLUG
        assert world["node_store"]["node_member"]["meta"]["feature_slug"] == SLUG
        assert set(res["stamp"]["stamped"]) == {"node_anchor", "node_member"}

    def test_plan_ref_backfilled_from_corpus_for_captured_slug(self, world, client, feat, monkeypatch):
        _capture(world, client, feat, monkeypatch, apply=True)
        assert world["node_store"]["node_anchor"]["meta"]["plan_ref"] == "docs/project_plans/gamma.md"

    def test_pre_existing_meta_key_survives(self, world, client, feat, monkeypatch):
        _capture(world, client, feat, monkeypatch, apply=True)
        meta_member = world["node_store"]["node_member"]["meta"]
        assert meta_member["other_key"] == "keep-me"  # merge, not replace
        assert meta_member["feature_slug"] == SLUG

    def test_second_apply_is_idempotent(self, world, client, feat, monkeypatch):
        _res1, http_calls, _req1 = _capture(world, client, feat, monkeypatch, apply=True)
        http_calls.clear()  # shared write-log — isolate the second run's writes
        res2, http_calls2, _req2 = _capture(world, client, feat, monkeypatch, apply=True)
        # After a clean stamp, every candidate is already_correct -> no further PATCH writes.
        assert http_calls2 == []
        assert res2["stamp"]["would_stamp"] == 0
        assert res2["stamp"]["already_correct"] == 2

    def test_conflicting_slug_is_reported_and_never_overwritten(self, world, client, feat, monkeypatch):
        # A node already carrying a DIFFERENT feature_slug (FR-7): must be flagged, left untouched,
        # and surfaced as ok=False.
        world["node_store"]["node_anchor"]["meta"] = {"feature_slug": "other-feature"}
        res, http_calls, _req = _capture(world, client, feat, monkeypatch, apply=True)
        assert res["ok"] is False
        assert res["stamp"]["ok"] is False
        conflicts = res["stamp"]["conflicts"]
        assert any(c["node_id"] == "node_anchor" and c["kind"] == "write_conflict" for c in conflicts)
        # never overwritten
        assert world["node_store"]["node_anchor"]["meta"] == {"feature_slug": "other-feature"}
        assert not any(h["url"].endswith("/node_anchor") for h in http_calls)

    def test_dry_run_never_stamps(self, world, client, feat, monkeypatch):
        res, http_calls, req_calls = _capture(world, client, feat, monkeypatch, apply=False)
        assert res.get("dry_run") is True
        assert "stamp" not in res
        assert http_calls == []  # no node writes at all in dry-run
        # only the register happened (no import, no stamp reads).
        assert req_calls == [("POST", "/api/v1/source-artifacts")]

    def test_nested_meta_value_preserved_as_object_through_stamp(self, world, client, feat, monkeypatch):
        # The A2/M2 write-safety regression: a nested meta value must reach the wire as a real
        # JSON object, never JSON-stringified.
        world["node_store"]["node_member"]["meta"] = {"fingerprint": {"algo": "sha256", "parts": [1, 2]}}
        _res, http_calls, _req = _capture(world, client, feat, monkeypatch, apply=True)
        member_writes = [h for h in http_calls if h["url"].endswith("/node_member")]
        assert len(member_writes) == 1
        body_meta = member_writes[0]["body"]["meta"]
        assert isinstance(body_meta["fingerprint"], dict)  # NOT a string
        assert body_meta["fingerprint"] == {"algo": "sha256", "parts": [1, 2]}
        assert body_meta["feature_slug"] == SLUG


# ---------------------------------------------------------------------------
# wave_plan.phases[] milestone fallback (Feature Contract:
# intenttree-capture-wave-plan-milestones) — `feature_from_file()` captures one node per
# `wave_plan.phases[]` entry when a doctrine-conformant Tier 2/3 plan carries no `tasks[]`,
# instead of the original defect: silently reporting success while capturing zero nodes.
#
# Covered per contract §10 Validation Requirements:
#   (1) wave_plan.phases[]-only capture — one milestone node per phase, correct field mapping.
#   (2) idempotent re-run — feature_from_file() is deterministic across repeated calls, the
#       client-side half of the (source_artifact_id, source_task_id) idempotency contract.
#   (3) tasks[] regression — tasks[] present still takes the original, unchanged code path.
#   (4) observable skip message — names both shapes it checked for, not just "no tasks[]".
# Plus R1 (status derivation) and R2 (depends_on never wired to edges) coverage.
# ---------------------------------------------------------------------------
def _write_wave_plan_file(
    tmp_path: Path,
    *,
    status: str = "in_progress",
    feature_slug: str = "delta",
    filename: str = "delta.md",
) -> Path:
    content = f"""---
feature_slug: {feature_slug}
title: Delta
status: {status}
doc_type: implementation_plan
wave_plan:
  waves: [["M1"], ["M2"]]
  phases:
    - id: M1
      title: "First milestone"
      depends_on: []
      exit_criteria: ["Criterion A", "Criterion B"]
    - id: M2
      title: "Second milestone"
      depends_on: ["M1"]
      exit_criteria: ["Criterion C"]
---

# Delta
"""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


class TestWavePlanPhaseFallback:
    # -- (1) wave_plan.phases[]-only capture -------------------------------------------------
    def test_wave_plan_phases_only_captures_one_node_per_phase(self, tmp_path):
        p = _write_wave_plan_file(tmp_path)
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        assert feat["slug"] == "delta"
        assert len(feat["tasks"]) == 2
        assert [t["id"] for t in feat["tasks"]] == ["M1", "M2"]
        assert all(t["node_type"] == "milestone" for t in feat["tasks"])
        assert feat["tasks"][0]["title"] == "First milestone"
        assert feat["tasks"][0]["acceptance_criteria"] == ["Criterion A", "Criterion B"]
        assert feat["tasks"][1]["title"] == "Second milestone"
        assert feat["tasks"][1]["acceptance_criteria"] == ["Criterion C"]

    def test_duplicate_phase_ids_are_disambiguated(self, tmp_path):
        content = """---
feature_slug: zeta
status: draft
wave_plan:
  phases:
    - id: M1
      title: First
      exit_criteria: []
    - id: M1
      title: Duplicate
      exit_criteria: []
---

# Zeta
"""
        p = tmp_path / "zeta.md"
        p.write_text(content, encoding="utf-8")
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        ids = [t["id"] for t in feat["tasks"]]
        assert len(set(ids)) == 2
        assert ids[0] == "M1"
        assert ids[1] != "M1"  # disambiguated, mirrors _collect_task's id-uniqueness pattern

    # -- (2) idempotent re-run ----------------------------------------------------------------
    def test_repeated_calls_are_deterministic_for_idempotency(self, tmp_path):
        # The client-side half of the (source_artifact_id, source_task_id) idempotency contract:
        # the same file must yield byte-identical task-shaped output on every call, so repeated
        # syncs key to the same source_task_id and the server-side dedup can do its job.
        p = _write_wave_plan_file(tmp_path)
        feat1 = cap_mod.feature_from_file(p)
        feat2 = cap_mod.feature_from_file(p)
        assert feat1 == feat2

    def test_wave_plan_feat_flows_unmodified_into_import_payload(self, tmp_path, monkeypatch):
        # End-to-end through the UNCHANGED capture_feature(): the mapper's output is exactly
        # what reaches the import call (2 phases -> 2 tasks in the payload), and depends_on is
        # absent from the wire body too (R2).
        p = _write_wave_plan_file(tmp_path, feature_slug=SLUG)
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        captured: dict[str, Any] = {}

        def req(api: str, method: str, path: str, body: dict | None = None):
            if method == "POST" and path == "/api/v1/source-artifacts":
                return 200, {"source_artifact_id": SID}
            if method == "GET" and path.startswith("/api/v1/source-artifacts/"):
                return 200, {"source_artifact_id": SID}
            if method == "POST" and path == "/api/v1/work-item-sync/import":
                captured["tasks"] = body["tasks"]
                return 200, {"counts": {"inserts": len(body["tasks"]), "updates": 0,
                                         "edges_created": 0}}
            raise AssertionError(f"unexpected _req: {method} {path}")

        monkeypatch.setattr(cap_mod, "_req", req)
        monkeypatch.setattr(cap_mod.time, "sleep", lambda *_a, **_k: None)
        # The creation-time slug stamp is unrelated to this AC — short-circuit it.
        monkeypatch.setattr(
            cap_mod, "stamp_created_nodes",
            lambda *a, **k: {"ok": True, "slug": SLUG, "stamped": [], "would_stamp": 0,
                              "already_correct": 0, "conflicts": []},
        )

        res = cap_mod.capture_feature("http://fake-itt.test", "ws1", "t1", feat, True)
        assert res["ok"] is True
        assert res["inserts"] == 2
        assert captured["tasks"] == feat["tasks"]
        assert all(t["node_type"] == "milestone" for t in captured["tasks"])
        assert all("depends_on" not in t for t in captured["tasks"])

    # -- (3) tasks[] regression ---------------------------------------------------------------
    def test_tasks_present_takes_precedence_over_wave_plan_unchanged(self, tmp_path):
        content = """---
feature_slug: epsilon
title: Epsilon
status: in_progress
doc_type: implementation_plan
tasks:
  - id: T1
    title: Do the thing
    status: in_progress
wave_plan:
  waves: [["M1"]]
  phases:
    - id: M1
      title: "Should be ignored"
      exit_criteria: ["should not appear"]
---

# Epsilon
"""
        p = tmp_path / "epsilon.md"
        p.write_text(content, encoding="utf-8")
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        assert len(feat["tasks"]) == 1
        assert feat["tasks"][0]["id"] == "T1"
        assert feat["tasks"][0].get("node_type") != "milestone"
        assert feat["tasks"][0]["status"] == "in_progress"
        assert feat["tasks"][0]["phase"] == "Phase 1"  # _collect_task's phase tag, unchanged

    def test_empty_tasks_list_present_does_not_fall_back_to_wave_plan(self, tmp_path):
        # An explicit `tasks: []` is "present, not absent" per the contract's trigger condition
        # ("when fm.get('tasks') is absent/not a list") — no fallback attempted, same as before.
        content = """---
feature_slug: eta
tasks: []
wave_plan:
  phases:
    - id: M1
      title: Should not appear
      exit_criteria: []
---

# Eta
"""
        p = tmp_path / "eta.md"
        p.write_text(content, encoding="utf-8")
        assert cap_mod.feature_from_file(p) is None

    # -- (4) observable skip message -----------------------------------------------------------
    def test_feature_from_file_returns_none_when_neither_shape_present(self, tmp_path):
        p = tmp_path / "empty.md"
        p.write_text("---\ntitle: Empty\n---\n\n# Empty\n", encoding="utf-8")
        assert cap_mod.feature_from_file(p) is None

    def test_main_skip_message_names_both_shapes(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "neither.md"
        f.write_text("---\ntitle: Neither\n---\n\n# Neither\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv",
                             ["intenttree_capture.py", "sync", str(f), "--tree", "t1"])
        rc = cap_mod.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "tasks[]" in out
        assert "wave_plan.phases[]" in out

    # -- R1 (phase-completion status derivation) -----------------------------------------------
    def test_status_derived_completed_when_plan_status_complete(self, tmp_path):
        p = _write_wave_plan_file(tmp_path, status="shipped", filename="shipped.md")
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        assert all(t["status"] == "completed" for t in feat["tasks"])

    def test_status_derived_not_started_when_plan_in_progress(self, tmp_path):
        p = _write_wave_plan_file(tmp_path, status="in_progress", filename="inprogress.md")
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        assert all(t["status"] == "not_started" for t in feat["tasks"])

    def test_status_derived_not_started_when_plan_status_missing(self, tmp_path):
        content = """---
feature_slug: theta
wave_plan:
  phases:
    - id: M1
      title: No plan status at all
      exit_criteria: []
---

# Theta
"""
        p = tmp_path / "theta.md"
        p.write_text(content, encoding="utf-8")
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        assert feat["tasks"][0]["status"] == "not_started"

    # -- R2 (depends_on deliberately not wired to edges) -----------------------------------------
    def test_depends_on_never_forwarded_to_task_shaped_dict(self, tmp_path):
        p = _write_wave_plan_file(tmp_path)
        feat = cap_mod.feature_from_file(p)
        assert feat is not None
        for t in feat["tasks"]:
            assert "depends_on" not in t
