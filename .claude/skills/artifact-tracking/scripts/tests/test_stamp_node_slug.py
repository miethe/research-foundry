#!/usr/bin/env python3
"""Tests for stamp-node-slug.py / verify-slug-roundtrip.py + the shared _itt_client /
_slug_resolution modules (Shipped Work Ledger M2, FR-6/FR-7).

Offline, no network, no live `itt` CLI: every itt invocation is faked at the IttClient `runner`
seam (see _itt_client.IttClient(runner=...)). Covers:
  (a) merge-not-replace  — pre-existing meta keys survive a stamp write.
  (b) idempotency        — re-running a clean apply reports 0 further writes.
  (c) conflict rule      — a node with a differing existing feature_slug is never overwritten,
                            exits non-zero, and is named in the report.
  (d) each resolution path — direct / source_artifact / retroactive_binding.
  (e) tree-scoping        — an out-of-tree binding never contributes a candidate.
  (f) dry-run             — no update call is ever made without --apply.
  (g) verify-slug-roundtrip — PASS/FAIL cases for the round-trip checker.
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
import _slug_resolution as sr  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stamp_mod = _load("stamp_node_slug_mod", "stamp-node-slug.py")
verify_mod = _load("verify_slug_roundtrip_mod", "verify-slug-roundtrip.py")


# ---------------------------------------------------------------------------
# Fixture: a small fake IntentTree world.
#
# Tree nodes:
#   node_A — no meta.feature_slug yet     -> resolved via (a) direct
#   node_B — already correctly stamped    -> already_correct (idempotency case)
#   node_C — meta.feature_slug="bar-old"  -> resolves to "bar-new" -> write_conflict
#   node_D — meta has an unrelated key    -> resolved via (b) source_artifact; merge test
#   node_F — no meta                      -> resolved via (c) retroactive_binding only
# node_OUT is referenced by a binding but is NOT part of the tree graph (scoping test).
# ---------------------------------------------------------------------------
def _node(node_id: str, meta: dict[str, Any]) -> dict:
    return {"id": node_id, "type": "work_package", "title": node_id, "meta": dict(meta)}


def _make_world(tmp_path: Path) -> dict[str, Any]:
    repo_root = tmp_path
    plan_dir = repo_root / "docs" / "project_plans"
    plan_dir.mkdir(parents=True)

    plan1 = plan_dir / "plan1.md"
    plan1.write_text(
        "---\n"
        "itt_node_id: node_A\n"
        "feature_slug: alpha\n"
        "status: in_progress\n"
        "---\n\n# Plan 1\n",
        encoding="utf-8",
    )
    plan2 = plan_dir / "plan2.md"
    plan2.write_text(
        "---\n"
        "source_artifact_id: srcart_1\n"
        "feature_slug: delta\n"
        "status: not_started\n"
        "---\n\n# Plan 2\n",
        encoding="utf-8",
    )
    # plan3 exists purely so a plan-scan happens; node_C's conflict comes from bindings alone
    # (retroactive path) disagreeing with the node's pre-existing meta — no plan3 needed for that,
    # but include a benign unrelated file to prove the scanner tolerates plans with no join keys.
    (plan_dir / "unrelated.md").write_text(
        "---\nstatus: completed\n---\n\n# Unrelated\n", encoding="utf-8"
    )

    # Gap-1 (tag_match) fixture: a corpus-only feature_slug — no itt_node_id/source_artifact_id,
    # so paths (a)/(b) never fire and no binding names it either. Only a node's own `tags` (or the
    # gap-2 plan_ref backfill once resolved some other way) can ever reach it.
    plan_echo = plan_dir / "plan_echo.md"
    plan_echo.write_text(
        "---\nfeature_slug: echo\nstatus: completed\ndoc_type: prd\n---\n\n# Plan Echo\n",
        encoding="utf-8",
    )

    tree_nodes = [
        _node("node_A", {}),
        _node("node_B", {"feature_slug": "bravo", "plan_ref": "docs/project_plans/plan_b.md"}),
        _node("node_C", {"feature_slug": "bar-old"}),
        _node("node_D", {"other_key": "keep-me"}),
        _node("node_F", {}),
        # degenerate-import residue (the M2 correctness bug this fixture exists to guard):
        # bindings' own retroactive slug IS a source-artifact id, never a real feature slug.
        _node("node_G", {}),
        # Gap-1: tags exactly match ONE corpus feature_slug ("echo") -> tag_match.
        _node("node_H", {}),
        # Gap-1: tags exactly match TWO distinct corpus feature_slugs ("alpha" + "delta") ->
        # ambiguous, resolves nothing.
        _node("node_I", {}),
    ]
    tree_nodes[-2]["tags"] = ["echo", "unrelated-tag"]
    tree_nodes[-1]["tags"] = ["alpha", "delta"]
    node_store = {n["id"]: n for n in tree_nodes}

    bindings_items = [
        {"node_id": "node_D", "source_artifact_id": "srcart_1", "source_task_id": "phase:Phase 1"},
        {"node_id": "node_C", "source_artifact_id": "srcart_2", "source_task_id": "feature:bar-new"},
        {"node_id": "node_F", "source_artifact_id": "srcart_3", "source_task_id": "feature:zeta"},
        # out-of-tree node: must never contribute a candidate (tree-scoping gotcha 4).
        {"node_id": "node_OUT", "source_artifact_id": "srcart_1", "source_task_id": "phase:Phase 2"},
        # the actual defect found in the M2 dry-run review: title/binding fell back to the
        # source-artifact id itself instead of a real feature_slug.
        {
            "node_id": "node_G", "source_artifact_id": "srcart_4",
            "source_task_id": "feature:srcart_01KXHQR6F69Y80GX1B6VF4FZFB",
        },
    ]

    return {
        "repo_root": repo_root,
        "plan_root": plan_dir,
        "node_store": node_store,
        "bindings_items": bindings_items,
        "plan1": plan1,
        "plan2": plan2,
        "plan_echo": plan_echo,
    }


def _make_fake_runner(node_store: dict[str, dict], bindings_items: list[dict]):
    """Build a fake `itt` runner + a call log, for asserting which invocations happened."""
    calls: list[list[str]] = []

    def runner(args: list[str]) -> itc.CliResult:
        calls.append(args)
        assert args[0] == "--json", "the client must always pass the GLOBAL --json flag first"
        sub = args[1:]

        if sub[:2] == ["tree", "graph"]:
            return itc.CliResult(0, json.dumps({"nodes": list(node_store.values()), "edges": []}), "")

        if sub[:2] == ["sync", "status"]:
            cursor = sub[sub.index("--cursor") + 1] if "--cursor" in sub else None
            page_size = 3
            start = int(cursor) if cursor else 0
            page_items = bindings_items[start:start + page_size]
            next_cursor = str(start + page_size) if start + page_size < len(bindings_items) else None
            return itc.CliResult(
                0, json.dumps({"items": page_items, "next_cursor": next_cursor,
                               "total": len(bindings_items)}), ""
            )

        if sub[:2] == ["node", "get"]:
            node_id = sub[2]
            return itc.CliResult(0, json.dumps(node_store[node_id]), "")

        raise AssertionError(f"unexpected itt invocation: {sub}")

    return runner, calls


def _make_fake_http_call(node_store: dict[str, dict]):
    """Fake the HTTP PATCH write seam. Returns (http_call, call_log) — no socket ever opened.

    Mirrors the real endpoint's whole-meta-replace semantics: the request body's ``meta`` dict
    REPLACES ``node_store[node_id]["meta"]`` wholesale, and nested values keep their real Python
    type (dict/list), never coerced to a string — this is the behavior being guarded against
    regressing back to the old lossy CLI ``--meta`` path.
    """
    http_calls: list[dict[str, Any]] = []

    def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
        http_calls.append({"url": url, "method": method, "body": body, "headers": headers})
        assert method == "PATCH"
        node_id = url.rsplit("/", 1)[-1]
        assert isinstance(body, dict) and set(body.keys()) == {"meta"}
        assert isinstance(body["meta"], dict)
        node_store[node_id]["meta"] = body["meta"]
        return itc.HttpResult(200, json.dumps(node_store[node_id]))

    return http_call, http_calls


@pytest.fixture()
def world(tmp_path):
    return _make_world(tmp_path)


@pytest.fixture()
def client_and_calls(world, monkeypatch):
    # Isolate config-file resolution: point away from any real ~/.config/intenttree/config.toml
    # so the test's IttClient never reads (or is affected by) whatever the running machine has.
    monkeypatch.setattr(itc, "_CONFIG_FILE", Path("/nonexistent/config.toml"))
    monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
    monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)
    runner, calls = _make_fake_runner(world["node_store"], world["bindings_items"])
    http_call, http_calls = _make_fake_http_call(world["node_store"])
    client = itc.IttClient(runner=runner, http_call=http_call, api_url="http://fake-itt.test")
    return client, calls, http_calls


# ---------------------------------------------------------------------------
# Resolution engine — unit-level (no client involved).
# ---------------------------------------------------------------------------
class TestResolutionPaths:
    def test_direct_path(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        candidates, _rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)
        assert candidates["node_A"].resolution_path == "direct"
        assert candidates["node_A"].slug == "alpha"
        assert candidates["node_A"].plan_ref == "docs/project_plans/plan1.md"

    def test_source_artifact_path(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        candidates, _rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)
        assert candidates["node_D"].resolution_path == "source_artifact"
        assert candidates["node_D"].slug == "delta"
        assert candidates["node_D"].plan_ref == "docs/project_plans/plan2.md"

    def test_retroactive_binding_path_has_no_plan_ref(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        candidates, _rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)
        assert candidates["node_F"].resolution_path == "retroactive_binding"
        assert candidates["node_F"].slug == "zeta"
        assert candidates["node_F"].plan_ref is None

    def test_tree_scoping_excludes_out_of_tree_node(self, world):
        # node_OUT shares srcart_1 with node_D but is absent from the tree's node-id set.
        nodes_by_artifact, _ = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        assert "node_OUT" not in nodes_by_artifact["srcart_1"]
        assert nodes_by_artifact["srcart_1"] == ["node_D"]


# ---------------------------------------------------------------------------
# Slug-shape guard (M2 correctness fix): reject ID-shaped resolved values before they ever
# become a Candidate, so a bad import (title/binding fell back to a source-artifact id) can
# never invent a fake feature in the ledger.
# ---------------------------------------------------------------------------
class TestSlugShapeGuard:
    @pytest.mark.parametrize("value", [
        "srcart_01KXHQR6F69Y80GX1B6VF4FZFB",  # the exact defect found in the M2 dry-run review
        "node_01KYTBQVDMWDG25AC5947F0K0F",
        "tree_01KVTH95ETM8YRYCV2ENHVR124",
        "agt_01ABCDEFGHIJKLMNOPQRST",
        "xyzid_01ABCDEFGHIJKLMNOPQRST",  # unanticipated new prefix — caught by the generic regex
    ])
    def test_id_prefixed_values_are_rejected(self, value):
        reason = sr.slug_shape_reject_reason(value)
        assert reason is not None, f"expected {value!r} to be rejected"
        assert not sr.is_slug_shaped(value)

    @pytest.mark.parametrize("value", [
        "01KXHQR6F69Y80GX1B6VF4FZFB",  # bare ULID, no prefix, no hyphens
        "01KVTH95ETM8YRYCV2ENHVR124",
    ])
    def test_bare_ulid_values_are_rejected(self, value):
        reason = sr.slug_shape_reject_reason(value)
        assert reason is not None
        assert "ULID" in reason
        assert not sr.is_slug_shaped(value)

    @pytest.mark.parametrize("value", [
        "agentic-redeploy-pipeline",
        "codex-aos-integration",
        "shipped-work-ledger",
        "alpha",  # a single lowercase word is still slug-shaped
    ])
    def test_legit_kebab_case_slugs_pass_cleanly(self, value):
        assert sr.slug_shape_reject_reason(value) is None
        assert sr.is_slug_shaped(value)

    def test_rejected_resolution_never_becomes_a_candidate(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        candidates, rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)

        assert "node_G" not in candidates  # never a stamp candidate, degenerate or not

        rejected_node_g = [r for r in rejected if r["node_id"] == "node_G"]
        assert len(rejected_node_g) == 1
        assert rejected_node_g[0]["value"] == "srcart_01KXHQR6F69Y80GX1B6VF4FZFB"
        assert rejected_node_g[0]["resolution_path"] == "retroactive_binding"
        assert "srcart_01KXHQR6F69Y80GX1B6VF4FZFB" in rejected_node_g[0]["reason"]


# ---------------------------------------------------------------------------
# Gap-1 (M2): tag_match resolution path — exact-match-only, unambiguous-only, lowest precedence.
# ---------------------------------------------------------------------------
class TestTagMatchResolution:
    def _base_candidates(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        candidates, _rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)
        slug_index = sr.build_corpus_slug_index(plan_files)
        return candidates, slug_index

    def test_exact_single_match_resolves(self, world):
        candidates, slug_index = self._base_candidates(world)
        tag_candidates, rejected, ambiguous = sr.resolve_tag_match_candidates(
            world["node_store"], slug_index, set(candidates.keys())
        )
        assert "node_H" in tag_candidates
        cand = tag_candidates["node_H"]
        assert cand.slug == "echo"
        assert cand.resolution_path == "tag_match"
        assert cand.plan_ref == "docs/project_plans/plan_echo.md"
        assert not rejected
        assert not any(a.node_id == "node_H" for a in ambiguous)

    def test_ambiguous_tags_resolve_nothing(self, world):
        candidates, slug_index = self._base_candidates(world)
        tag_candidates, _rejected, ambiguous = sr.resolve_tag_match_candidates(
            world["node_store"], slug_index, set(candidates.keys())
        )
        assert "node_I" not in tag_candidates  # never guessed
        matches = [a for a in ambiguous if a.node_id == "node_I"]
        assert len(matches) == 1
        assert matches[0].matched_slugs == ["alpha", "delta"]

    def test_never_overrides_a_higher_precedence_resolution(self, world):
        candidates, slug_index = self._base_candidates(world)
        assert candidates["node_D"].resolution_path == "source_artifact"
        tag_candidates, _r, _a = sr.resolve_tag_match_candidates(
            world["node_store"], slug_index, set(candidates.keys())
        )
        assert "node_D" not in tag_candidates  # excluded via already_resolved, never re-tried

    def test_no_fuzzy_or_substring_matching(self, world):
        # A tag that only *contains* or *resembles* "echo" must never match — exact equality only.
        nodes = {"node_Z": {"id": "node_Z", "type": "work_package", "tags": ["echo-ish", "echoes"]}}
        candidates, slug_index = self._base_candidates(world)
        tag_candidates, _rejected, ambiguous = sr.resolve_tag_match_candidates(
            nodes, slug_index, set(candidates.keys())
        )
        assert not tag_candidates
        assert not ambiguous

    def test_end_to_end_stamp_via_tag_match(self, world, client_and_calls):
        client, _, _ = client_and_calls
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply"],
            client=client,
        )
        meta_h = world["node_store"]["node_H"]["meta"]
        assert meta_h["feature_slug"] == "echo"
        assert meta_h["plan_ref"] == "docs/project_plans/plan_echo.md"
        assert world["node_store"]["node_I"]["meta"] == {}  # ambiguous — never written

    def test_summary_reports_ambiguous_tag_match_bucket(self, world, client_and_calls):
        client, _, _ = client_and_calls
        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = stamp_mod.main(
                ["--tree", "t1", "--plan-root", str(world["plan_root"]),
                 "--repo-root", str(world["repo_root"]), "--apply", "--json"],
                client=client,
            )
        payload = json.loads(stdout_buf.text)
        assert payload["summary"]["ambiguous_tag_match"] == 1
        assert payload["summary"]["would_stamp_by_path"]["tag_match"] == 1
        assert len(payload["ambiguous_tag_match"]) == 1
        assert payload["ambiguous_tag_match"][0]["node_id"] == "node_I"
        assert rc == 2


# ---------------------------------------------------------------------------
# Gap-2 (M2): meta.plan_ref backfill via the corpus slug index + its own conflict rule.
# ---------------------------------------------------------------------------
class TestPlanRefBackfillAndConflict:
    def test_retroactive_candidate_gets_plan_ref_backfilled_from_corpus(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(
            world["bindings_items"], set(world["node_store"].keys())
        )
        candidates, _rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)
        # node_F resolves "zeta" via retroactive_binding alone — no corpus file names "zeta" in
        # this fixture, so plan_ref legitimately stays unresolvable; prove that baseline first.
        assert candidates["node_F"].plan_ref is None

    def test_full_stamp_run_backfills_plan_ref_for_tag_match(self, world, client_and_calls):
        client, _, _ = client_and_calls
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply"],
            client=client,
        )
        assert world["node_store"]["node_H"]["meta"]["plan_ref"] == "docs/project_plans/plan_echo.md"

    def test_existing_differing_plan_ref_is_never_overwritten(self, world, client_and_calls):
        client, _, http_calls = client_and_calls
        # node_D resolves to plan2.md via source_artifact; give it a pre-existing, DIFFERENT
        # plan_ref up front — this must be flagged as a conflict, never silently overwritten.
        world["node_store"]["node_D"]["meta"] = {
            "other_key": "keep-me",
            "plan_ref": "docs/project_plans/some-other-file.md",
        }
        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = stamp_mod.main(
                ["--tree", "t1", "--plan-root", str(world["plan_root"]),
                 "--repo-root", str(world["repo_root"]), "--apply", "--json"],
                client=client,
            )
        assert rc == 2
        payload = json.loads(stdout_buf.text)
        plan_ref_conflicts = [c for c in payload["conflicts"] if c["kind"] == "plan_ref_conflict"]
        assert len(plan_ref_conflicts) == 1
        assert plan_ref_conflicts[0]["node_id"] == "node_D"
        assert plan_ref_conflicts[0]["existing_plan_ref"] == "docs/project_plans/some-other-file.md"
        assert plan_ref_conflicts[0]["resolved_plan_ref"] == "docs/project_plans/plan2.md"
        # node_D was never written at all — the plan_ref conflict blocks the whole write, feature_slug included.
        assert world["node_store"]["node_D"]["meta"] == {
            "other_key": "keep-me",
            "plan_ref": "docs/project_plans/some-other-file.md",
        }
        assert not any(c["url"].endswith("/node_D") for c in http_calls)


# ---------------------------------------------------------------------------
# _slug_resolution.select_primary_plan_file / build_corpus_slug_index — doc_type preference.
# ---------------------------------------------------------------------------
class TestPrimaryPlanFileSelection:
    def _pf(self, rel_path: str, doc_type: str | None, slug: str = "foo") -> sr.PlanFile:
        return sr.PlanFile(
            path=Path(rel_path), rel_path=rel_path, feature_slug=slug,
            itt_node_id=None, source_artifact_id=None, doc_type=doc_type,
        )

    def test_implementation_plan_preferred_over_prd(self):
        files = [self._pf("b-prd.md", "prd"), self._pf("a-impl.md", "implementation_plan")]
        assert sr.select_primary_plan_file(files).rel_path == "a-impl.md"

    def test_prd_preferred_over_untyped_or_other(self):
        files = [self._pf("z-report.md", "report"), self._pf("a-prd.md", "prd")]
        assert sr.select_primary_plan_file(files).rel_path == "a-prd.md"

    def test_lexicographic_tie_break_within_same_rank(self):
        files = [self._pf("z.md", "prd"), self._pf("a.md", "prd")]
        assert sr.select_primary_plan_file(files).rel_path == "a.md"

    def test_lexicographic_tie_break_when_no_doc_type_anywhere(self):
        files = [self._pf("z.md", None), self._pf("a.md", None)]
        assert sr.select_primary_plan_file(files).rel_path == "a.md"

    def test_canonical_plan_beats_phase_subplan_despite_lexicographic_order(self):
        """Regression: two implementation_plans share a slug; the phase sub-plan sorts FIRST
        lexicographically ('p2' < 'v1') but the canonical '<slug>-v1.md' must win."""
        slug = "dynamic-artifact-provisioning"
        files = [
            self._pf(f"plans/{slug}-p2-fleet-v1.md", "implementation_plan", slug),
            self._pf(f"plans/{slug}-v1.md", "implementation_plan", slug),
        ]
        assert sr.select_primary_plan_file(files, slug).rel_path == f"plans/{slug}-v1.md"

    def test_exact_stem_match_without_version_suffix(self):
        slug = "foo-bar"
        files = [
            self._pf("plans/foo-bar-phase2.md", "implementation_plan", slug),
            self._pf("plans/foo-bar.md", "implementation_plan", slug),
        ]
        assert sr.select_primary_plan_file(files, slug).rel_path == "plans/foo-bar.md"

    def test_doc_type_still_outranks_exact_stem_match(self):
        """An exact-stem PRD must not beat an implementation_plan — doc_type is the outer key."""
        slug = "foo-bar"
        files = [
            self._pf("plans/foo-bar.md", "prd", slug),
            self._pf("plans/foo-bar-phase2-v1.md", "implementation_plan", slug),
        ]
        assert sr.select_primary_plan_file(files, slug).rel_path == "plans/foo-bar-phase2-v1.md"

    def test_slug_omitted_falls_back_to_lexicographic(self):
        files = [self._pf("z.md", "prd"), self._pf("a.md", "prd")]
        assert sr.select_primary_plan_file(files).rel_path == "a.md"

    def test_build_corpus_slug_index_groups_by_slug(self, world):
        plan_files = sr.scan_plan_files(world["plan_root"], world["repo_root"])
        index = sr.build_corpus_slug_index(plan_files)
        assert set(index.keys()) >= {"alpha", "delta", "echo"}
        assert [pf.rel_path for pf in index["echo"]] == ["docs/project_plans/plan_echo.md"]


# ---------------------------------------------------------------------------
# stamp-node-slug.py — end-to-end via the fake client.
# ---------------------------------------------------------------------------
class TestStampNodeSlug:
    def test_dry_run_makes_no_write_calls(self, world, client_and_calls):
        client, calls, http_calls = client_and_calls
        rc = stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--json"],
            client=client,
        )
        assert rc == 2  # node_C's write_conflict still surfaces even in dry-run
        assert not http_calls  # no PATCH at all without --apply
        assert not any(c[1:3] == ["node", "get"] for c in calls)  # no freshness fetch without --apply

    def test_merge_not_replace_preserves_existing_meta(self, world, client_and_calls):
        client, _, _ = client_and_calls
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply", "--json"],
            client=client,
        )
        meta_d = world["node_store"]["node_D"]["meta"]
        assert meta_d["other_key"] == "keep-me"  # pre-existing key survives
        assert meta_d["feature_slug"] == "delta"
        assert meta_d["plan_ref"] == "docs/project_plans/plan2.md"

    def test_conflict_never_overwritten(self, world, client_and_calls):
        client, _, http_calls = client_and_calls
        rc = stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply", "--json"],
            client=client,
        )
        assert rc == 2
        # node_C is never written, in apply mode or not.
        assert world["node_store"]["node_C"]["meta"] == {"feature_slug": "bar-old"}
        assert not any(c["url"].endswith("/node_C") for c in http_calls)

    def test_idempotent_second_apply_writes_nothing_new(self, world, client_and_calls):
        client, _, http_calls = client_and_calls
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply", "--json"],
            client=client,
        )
        http_calls.clear()
        stdout_buf = _CaptureStdout()
        with stdout_buf:
            stamp_mod.main(
                ["--tree", "t1", "--plan-root", str(world["plan_root"]),
                 "--repo-root", str(world["repo_root"]), "--apply", "--json"],
                client=client,
            )
        payload = json.loads(stdout_buf.text)
        assert payload["summary"]["would_stamp"] == 0
        assert payload["summary"]["applied"] == 0
        assert not http_calls

    def test_already_correct_node_is_not_restamped(self, world, client_and_calls):
        client, _, _ = client_and_calls
        # node_B has no resolving plan file/binding in this fixture, so it never becomes a
        # candidate at all — prove the already-stamped node stays exactly as it was.
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply"],
            client=client,
        )
        assert world["node_store"]["node_B"]["meta"] == {
            "feature_slug": "bravo", "plan_ref": "docs/project_plans/plan_b.md",
        }

    def test_rejected_slug_shape_node_is_left_untouched_in_apply_mode(self, world, client_and_calls):
        client, _, http_calls = client_and_calls
        stdout_buf = _CaptureStdout()
        with stdout_buf:
            rc = stamp_mod.main(
                ["--tree", "t1", "--plan-root", str(world["plan_root"]),
                 "--repo-root", str(world["repo_root"]), "--apply", "--json"],
                client=client,
            )
        # treated like a conflict for exit-code purposes (data-quality defect a human must see)
        assert rc == 2
        payload = json.loads(stdout_buf.text)
        assert payload["summary"]["rejected_slug_shape"] == 1
        rejected_entries = payload["rejected_slug_shape"]
        assert len(rejected_entries) == 1
        assert rejected_entries[0]["node_id"] == "node_G"
        assert rejected_entries[0]["value"] == "srcart_01KXHQR6F69Y80GX1B6VF4FZFB"

        # node_G was never written — no PATCH call, meta completely unchanged.
        assert world["node_store"]["node_G"]["meta"] == {}
        assert not any(c["url"].endswith("/node_G") for c in http_calls)
        # rejected_slug_shape is reported separately from conflicts — the two causes stay
        # distinguishable even though both drive the same non-zero exit code.
        assert payload["summary"]["conflicts"] == 1  # node_C's pre-existing write_conflict
        assert payload["summary"]["rejected_slug_shape"] == 1

    def test_apply_patch_body_preserves_nested_meta_as_object(self, world, client_and_calls):
        """The regression this fix guards: a nested meta value (e.g. a fingerprint dict) must
        travel through the write seam as a JSON *object*, never coerced to a string."""
        client, _, http_calls = client_and_calls
        world["node_store"]["node_D"]["meta"] = {
            "other_key": "keep-me",
            "fingerprint": {"algo": "sha256", "parts": [1, 2, 3]},
        }
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply"],
            client=client,
        )
        node_d_calls = [c for c in http_calls if c["url"].endswith("/node_D")]
        assert len(node_d_calls) == 1
        body = node_d_calls[0]["body"]
        assert isinstance(body["meta"]["fingerprint"], dict)  # NOT a JSON string
        assert body["meta"]["fingerprint"] == {"algo": "sha256", "parts": [1, 2, 3]}
        assert body["meta"]["feature_slug"] == "delta"


class _CaptureStdout:
    def __enter__(self):
        import io
        self._real = sys.stdout
        self._buf = io.StringIO()
        sys.stdout = self._buf
        return self

    def __exit__(self, *_exc):
        sys.stdout = self._real

    @property
    def text(self) -> str:
        return self._buf.getvalue()


# ---------------------------------------------------------------------------
# verify-slug-roundtrip.py
# ---------------------------------------------------------------------------
class TestVerifySlugRoundtrip:
    def _stamped_world(self, world, client):
        stamp_mod.main(
            ["--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--apply"],
            client=client,
        )
        return world

    def test_pass_for_a_clean_roundtrip(self, world, client_and_calls):
        client, _, _ = client_and_calls
        self._stamped_world(world, client)
        results = verify_mod.check_tree(client, "t1", world["repo_root"], slug_filter="delta")
        assert len(results) == 1
        assert results[0]["status"] == "PASS"
        assert results[0]["node_id"] == "node_D"

    def test_fail_when_plan_ref_missing(self, world, client_and_calls):
        client, _, _ = client_and_calls
        # node_F resolves via retroactive_binding only -> plan_ref stays None after apply.
        self._stamped_world(world, client)
        results = verify_mod.check_tree(client, "t1", world["repo_root"], slug_filter="zeta")
        assert len(results) == 1
        assert results[0]["status"] == "FAIL"
        assert "no plan_ref" in results[0]["reason"]

    def test_fail_when_file_slug_mismatches_node_slug(self, world, client_and_calls):
        client, _, _ = client_and_calls
        self._stamped_world(world, client)
        # Corrupt the plan file's slug post-stamp to simulate drift.
        world["plan1"].write_text(
            world["plan1"].read_text(encoding="utf-8").replace("feature_slug: alpha", "feature_slug: mutated"),
            encoding="utf-8",
        )
        results = verify_mod.check_tree(client, "t1", world["repo_root"], slug_filter="alpha")
        assert results[0]["status"] == "FAIL"
        assert "!=" in results[0]["reason"]

    def test_sibling_nodes_pass_as_members_not_only_the_anchor(self, world, client_and_calls):
        """Regression: a plan binds ONE feature-level node, but every descendant shares the slug.

        Requiring `itt_node_id == node_id` of every slug-carrying node fails the whole tree by
        construction (it did: 74/79 FAIL against the live tree). Only the bound node is the
        'anchor'; siblings must verify as coherent 'member's.
        """
        client, _, _ = client_and_calls
        self._stamped_world(world, client)
        anchor_id = sr.scan_frontmatter_scalars(world["plan1"]).get("itt_node_id")
        assert anchor_id == "node_A", "fixture must bind plan1 to node_A to exercise the anchor path"

        # A descendant of the same feature: shares the slug, is NOT the bound node.
        world["node_store"]["node_A_child"] = _node(
            "node_A_child",
            {"feature_slug": "alpha", "plan_ref": "docs/project_plans/plan1.md"},
        )

        results = verify_mod.check_tree(client, "t1", world["repo_root"], slug_filter="alpha")
        assert len(results) > 1, "fixture needs >1 node on the slug to prove the member path"
        assert all(r["status"] == "PASS" for r in results), [
            r for r in results if r["status"] != "PASS"
        ]
        roles = {r["node_id"]: r["role"] for r in results}
        assert roles[anchor_id] == "anchor"
        assert all(v == "member" for k, v in roles.items() if k != anchor_id)

    def test_fail_when_file_binding_points_outside_the_tree(self, world, client_and_calls):
        """A dangling file-side binding is a real defect and must still FAIL."""
        client, _, _ = client_and_calls
        self._stamped_world(world, client)
        text = world["plan1"].read_text(encoding="utf-8")
        old = sr.scan_frontmatter_scalars(world["plan1"]).get("itt_node_id")
        world["plan1"].write_text(
            text.replace(f"itt_node_id: {old}", "itt_node_id: node_does_not_exist"),
            encoding="utf-8",
        )
        results = verify_mod.check_tree(client, "t1", world["repo_root"], slug_filter="alpha")
        assert any(r["status"] == "FAIL" for r in results)
        assert any("dangling" in (r.get("reason") or "") for r in results)

    def test_unknown_slug_filter_fails(self, world, client_and_calls):
        client, _, _ = client_and_calls
        self._stamped_world(world, client)
        results = verify_mod.check_tree(client, "t1", world["repo_root"], slug_filter="nonexistent")
        assert results[0]["status"] == "FAIL"
        assert results[0]["node_id"] is None

    def test_id_shaped_stamped_slug_fails_with_reason_not_spurious_pass(self, world, client_and_calls):
        # Defensive case: even if an ID-shaped value somehow ended up live on a node (bypassing
        # the stamper's own guard — e.g. written by an older tool version), the round-trip
        # checker must report FAIL-with-reason, never a spurious PASS.
        client, _, _ = client_and_calls
        world["node_store"]["node_G"]["meta"] = {
            "feature_slug": "srcart_01KXHQR6F69Y80GX1B6VF4FZFB",
            "plan_ref": "docs/project_plans/plan2.md",
        }
        results = verify_mod.check_tree(
            client, "t1", world["repo_root"], slug_filter="srcart_01KXHQR6F69Y80GX1B6VF4FZFB"
        )
        assert len(results) == 1
        assert results[0]["status"] == "FAIL"
        assert "not slug-shaped" in results[0]["reason"]


# ---------------------------------------------------------------------------
# _itt_client.py — the seam itself.
# ---------------------------------------------------------------------------
@pytest.fixture()
def _isolated_itt_env(monkeypatch):
    """Keep every IttClient() construction in this class from touching the real
    ~/.config/intenttree/config.toml or the real environment."""
    monkeypatch.setattr(itc, "_CONFIG_FILE", Path("/nonexistent/config.toml"))
    monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
    monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)


class TestIttClient:
    def test_json_flag_is_global_and_first(self, _isolated_itt_env):
        seen: list[list[str]] = []

        def runner(args: list[str]) -> itc.CliResult:
            seen.append(args)
            return itc.CliResult(0, "{}", "")

        client = itc.IttClient(runner=runner)
        client.get_node("node_X")
        assert seen[0][0] == "--json"
        assert seen[0][1:] == ["node", "get", "node_X"]

    def test_nonzero_exit_raises_itt_error(self, _isolated_itt_env):
        def runner(_args: list[str]) -> itc.CliResult:
            return itc.CliResult(1, "", "boom")

        client = itc.IttClient(runner=runner)
        with pytest.raises(itc.IttError):
            client.get_node("node_X")

    def test_update_node_meta_patch_body_preserves_nested_types(self, _isolated_itt_env):
        """The correctness fix: nested meta values must reach the wire as real JSON objects,
        never JSON-stringified — this is what made the old ``itt node update --meta`` seam lossy."""
        captured: dict[str, Any] = {}

        def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
            captured["url"] = url
            captured["method"] = method
            captured["body"] = body
            captured["headers"] = headers
            return itc.HttpResult(200, json.dumps(body))

        client = itc.IttClient(http_call=http_call, api_url="http://fake-itt.test")
        client.update_node_meta("node_X", {"feature_slug": "alpha", "fingerprint": {"bag": [1, 2]}})

        assert captured["url"] == "http://fake-itt.test/api/v1/nodes/node_X"
        assert captured["method"] == "PATCH"
        assert captured["body"] == {"meta": {"feature_slug": "alpha", "fingerprint": {"bag": [1, 2]}}}
        assert isinstance(captured["body"]["meta"]["fingerprint"], dict)  # NOT a string

    def test_update_node_meta_empty_meta_is_a_no_http_call_noop(self, _isolated_itt_env):
        calls: list[Any] = []

        def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
            calls.append((url, method, body, headers))
            return itc.HttpResult(200, "{}")

        def runner(args: list[str]) -> itc.CliResult:
            assert args[1:] == ["node", "get", "node_X"]
            return itc.CliResult(0, json.dumps({"id": "node_X", "meta": {}}), "")

        client = itc.IttClient(runner=runner, http_call=http_call)
        result = client.update_node_meta("node_X", {})
        assert result == {"id": "node_X", "meta": {}}
        assert not calls  # no PATCH issued for an empty meta dict

    def test_update_node_meta_raises_on_non_2xx(self, _isolated_itt_env):
        def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
            return itc.HttpResult(500, "internal error")

        client = itc.IttClient(http_call=http_call, api_url="http://fake-itt.test")
        with pytest.raises(itc.IttError):
            client.update_node_meta("node_X", {"feature_slug": "alpha"})

    def test_token_never_appears_in_url_or_is_hardcoded(self, _isolated_itt_env):
        captured: dict[str, Any] = {}

        def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
            captured["headers"] = headers
            return itc.HttpResult(200, "{}")

        client = itc.IttClient(
            http_call=http_call, api_url="http://fake-itt.test", api_token="tok_secret_value"
        )
        client.update_node_meta("node_X", {"feature_slug": "alpha"})
        assert captured["headers"]["Authorization"] == "Bearer tok_secret_value"

    def test_resolve_api_url_precedence_env_over_config_file(self, monkeypatch, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('api_url = "http://from-file.test"\n', encoding="utf-8")
        monkeypatch.setattr(itc, "_CONFIG_FILE", config_file)
        monkeypatch.setenv("INTENTTREE_API_URL", "http://from-env.test")
        assert itc.resolve_api_url() == "http://from-env.test"

    def test_resolve_api_url_falls_back_to_config_file(self, monkeypatch, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('api_url = "http://from-file.test"\n', encoding="utf-8")
        monkeypatch.setattr(itc, "_CONFIG_FILE", config_file)
        monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
        assert itc.resolve_api_url() == "http://from-file.test"

    def test_resolve_api_token_from_config_file(self, monkeypatch, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('api_token = "tok_from_file"\n', encoding="utf-8")
        monkeypatch.setattr(itc, "_CONFIG_FILE", config_file)
        monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)
        assert itc.resolve_api_token() == "tok_from_file"

    def test_resolve_api_token_explicit_arg_wins(self, _isolated_itt_env):
        assert itc.resolve_api_token("explicit_tok") == "explicit_tok"
