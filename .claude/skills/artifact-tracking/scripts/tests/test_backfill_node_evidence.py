#!/usr/bin/env python3
"""Tests for backfill-node-evidence.py — Shipped Work Ledger M3, FR-10/FR-11.

Offline, no network: every read (``tree_nodes``/``get_node_full``) and write
(``attach_external_link``) goes through the ``IttClient`` ``http_call`` seam, faked here with a
plain Python function against an in-memory node store — no live server, no subprocess.

Covers:
  (a) fail-closed normalization  — a confident ref backfills; the "direct-squash-to-main"
                                    sentinel and other unnormalizable values are reported, not
                                    guessed, and never block the confident refs on the same node.
  (b) FR-11 pre-read              — a ref that already exists as an external link is reported as
                                    already_present, never re-written.
  (c) idempotency                 — --apply twice writes nothing new the second time.
  (d) conflict rule                — an existing link with a DIFFERENT external_path than the
                                    plan file resolves is a conflict: reported, left untouched,
                                    non-zero exit — distinct from a plain already_present match.
  (e) no plan file for slug        — reported as a feature-level skip with a reason, never raises.
  (f) --slug filter                — limits the run to one feature.
  (g) --default-repo threading     — bare PR numbers/short shas resolve via the flag.
  (h) dry-run                      — never calls attach_external_link without --apply.
  (i) --json shape                 — slug/node_id/plan_ref/would_write/already_present/skipped
                                    /conflicts + totals, exactly as the M3 contract requires.
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
import _evidence_refs as evr  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses (3.12) needs the module registered to resolve types
    spec.loader.exec_module(mod)
    return mod


backfill_mod = _load("backfill_node_evidence_mod", "backfill-node-evidence.py")


# ---------------------------------------------------------------------------
# Fixture: a small fake IntentTree world + plan corpus.
#
#   node_A  feature_slug=alpha   — plan1.md carries confident commit_refs + pr_refs + one
#                                   unnormalizable sentinel; node starts with NO external links.
#   node_B  feature_slug=bravo   — plan2.md carries a ref that already exists on the node
#                                   (identical external_path) -> already_present.
#   node_C  feature_slug=charlie — plan3.md carries a ref whose external_id already exists on the
#                                   node but pointing at a DIFFERENT external_path -> conflict.
#   node_D  feature_slug=delta   — no plan file in the corpus carries this slug -> feature-level
#                                   skip, never raises.
#   node_E  no feature_slug at all -> never considered (not even scanned).
# ---------------------------------------------------------------------------
def _node(node_id: str, slug: str | None) -> dict:
    meta = {"feature_slug": slug} if slug else {}
    return {"id": node_id, "type": "work_package", "title": node_id, "meta": meta}


def _make_world(tmp_path: Path) -> dict[str, Any]:
    repo_root = tmp_path
    plan_dir = repo_root / "docs" / "project_plans"
    plan_dir.mkdir(parents=True)

    plan1 = plan_dir / "alpha-v1.md"
    plan1.write_text(
        "---\n"
        "feature_slug: alpha\n"
        "doc_type: implementation_plan\n"
        "commit_refs:\n"
        "  - b9b4613\n"
        "pr_refs: [\"agentic_meta_dev#33\", \"direct-squash-to-main\"]\n"
        "status: completed\n"
        "---\n\n# Alpha\n",
        encoding="utf-8",
    )
    plan2 = plan_dir / "bravo-v1.md"
    plan2.write_text(
        "---\n"
        "feature_slug: bravo\n"
        "doc_type: implementation_plan\n"
        "commit_refs: [\"agentic_meta_dev@ab643191c66e94f41877072780f75b608d619d7a\"]\n"
        "status: completed\n"
        "---\n\n# Bravo\n",
        encoding="utf-8",
    )
    plan3 = plan_dir / "charlie-v1.md"
    plan3.write_text(
        "---\n"
        "feature_slug: charlie\n"
        "doc_type: implementation_plan\n"
        "pr_refs: [\"agentic_meta_dev#99\"]\n"
        "status: completed\n"
        "---\n\n# Charlie\n",
        encoding="utf-8",
    )

    node_store = {
        n["id"]: n for n in [
            _node("node_A", "alpha"),
            _node("node_B", "bravo"),
            _node("node_C", "charlie"),
            _node("node_D", "delta"),
            _node("node_E", None),
        ]
    }

    # Pre-existing external links, keyed by node_id -> list[dict] (the get_node_full shape).
    node_links: dict[str, list[dict]] = {
        "node_A": [],
        "node_B": [
            {
                "system": "github", "external_id": "ab643191c66e94f41877072780f75b608d619d7a",
                "external_path": (
                    "https://github.com/miethe/agentic_meta_dev/commit/"
                    "ab643191c66e94f41877072780f75b608d619d7a"
                ),
            },
        ],
        "node_C": [
            {
                "system": "github", "external_id": "99",
                "external_path": "https://github.com/miethe/some-other-repo/pull/99",
            },
        ],
        "node_D": [],
        "node_E": [],
    }

    return {
        "repo_root": repo_root,
        "plan_root": plan_dir,
        "node_store": node_store,
        "node_links": node_links,
        "plan1": plan1,
        "plan2": plan2,
        "plan3": plan3,
    }


def _make_fake_http_call(node_store: dict[str, dict], node_links: dict[str, list[dict]]):
    """Fakes the HTTP seam behind ``tree_nodes`` / ``get_node_full`` / ``attach_external_link``.
    No socket, no subprocess — pure in-memory dict manipulation."""
    calls: list[dict[str, Any]] = []

    def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
        calls.append({"url": url, "method": method, "body": body})

        if method == "GET" and url.endswith("/graph"):
            return itc.HttpResult(200, json.dumps({"nodes": list(node_store.values())}))

        if method == "GET" and "/nodes/" in url and "?include=" in url:
            node_id = url.split("/nodes/")[1].split("?")[0]
            payload = dict(node_store[node_id])
            payload["external_links"] = node_links.get(node_id, [])
            return itc.HttpResult(200, json.dumps(payload))

        if method == "POST" and url.endswith("/external-links"):
            node_id = url.split("/nodes/")[1].split("/external-links")[0]
            link = {
                "system": body["system"], "external_id": body["external_id"],
                "external_path": body.get("external_path"),
                "context_label": body.get("context_label"),
            }
            node_links.setdefault(node_id, []).append(link)
            return itc.HttpResult(200, json.dumps(link))

        raise AssertionError(f"unexpected HTTP call: {method} {url}")

    return http_call, calls


@pytest.fixture()
def world(tmp_path):
    return _make_world(tmp_path)


@pytest.fixture()
def client_and_calls(world, monkeypatch):
    monkeypatch.setattr(itc, "_CONFIG_FILE", Path("/nonexistent/config.toml"))
    monkeypatch.delenv("INTENTTREE_API_URL", raising=False)
    monkeypatch.delenv("INTENTTREE_API_TOKEN", raising=False)
    http_call, calls = _make_fake_http_call(world["node_store"], world["node_links"])
    client = itc.IttClient(http_call=http_call, api_url="http://fake-itt.test")
    return client, calls


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


def _run(world, extra_args: list[str], client: itc.IttClient) -> tuple[int, dict]:
    buf = _CaptureStdout()
    with buf:
        rc = backfill_mod.main(
            ["--no-verify-commits", "--tree", "t1", "--plan-root", str(world["plan_root"]),
             "--repo-root", str(world["repo_root"]), "--json", *extra_args],
            client=client,
        )
    return rc, json.loads(buf.text)


class TestFailClosedNormalization:
    def test_confident_refs_backfill_and_sentinel_is_skipped(self, world, client_and_calls):
        client, _calls = client_and_calls
        rc, payload = _run(world, [], client)
        assert rc == 2  # node_C's unrelated conflict still surfaces; see TestConflictRule

        alpha = next(f for f in payload["features"] if f["slug"] == "alpha")
        would_write_idents = {w["ident"] for w in alpha["would_write"]}
        assert would_write_idents == {"b9b4613", "33"}

        skip_reasons = {s["raw"]: s["reason"] for s in alpha["skipped"]}
        assert "direct-squash-to-main" in skip_reasons
        assert "sentinel" in skip_reasons["direct-squash-to-main"]

    def test_skip_never_blocks_the_confident_refs_on_the_same_node(self, world, client_and_calls):
        client, _calls = client_and_calls
        _rc, payload = _run(world, [], client)
        alpha = next(f for f in payload["features"] if f["slug"] == "alpha")
        assert len(alpha["would_write"]) == 2
        assert len(alpha["skipped"]) == 1


class TestFR11PreReadAndIdempotency:
    def test_already_present_ref_is_reported_not_rewritten(self, world, client_and_calls):
        client, calls = client_and_calls
        rc, payload = _run(world, [], client)
        assert rc == 2  # node_C's unrelated conflict still surfaces; see TestConflictRule
        bravo = next(f for f in payload["features"] if f["slug"] == "bravo")
        assert bravo["would_write"] == []
        assert len(bravo["already_present"]) == 1
        assert bravo["already_present"][0]["ident"] == "ab643191c66e94f41877072780f75b608d619d7a"
        assert not any(c["method"] == "POST" for c in calls)

    def test_apply_writes_confident_refs(self, world, client_and_calls):
        client, calls = client_and_calls
        rc, payload = _run(world, ["--apply"], client)
        assert rc == 2  # node_C's unrelated conflict still surfaces; see TestConflictRule
        posts = [c for c in calls if c["method"] == "POST"]
        assert len(posts) == 2  # node_A's two confident refs (sha + PR); sentinel never written
        assert payload["totals"]["applied"] == 2

    def test_second_apply_writes_nothing_new(self, world, client_and_calls):
        client, calls = client_and_calls
        _run(world, ["--apply"], client)
        calls.clear()
        rc, payload = _run(world, ["--apply"], client)
        assert rc == 2  # node_C's unrelated conflict still surfaces; see TestConflictRule
        assert payload["totals"]["would_write"] == 0
        assert payload["totals"]["applied"] == 0
        assert not any(c["method"] == "POST" for c in calls)
        alpha = next(f for f in payload["features"] if f["slug"] == "alpha")
        assert len(alpha["already_present"]) == 2


class TestConflictRule:
    def test_contradicting_external_path_is_a_conflict_not_a_write(self, world, client_and_calls):
        client, calls = client_and_calls
        rc, payload = _run(world, [], client)
        assert rc == 2
        charlie = next(f for f in payload["features"] if f["slug"] == "charlie")
        assert charlie["would_write"] == []
        assert charlie["already_present"] == []
        assert len(charlie["conflicts"]) == 1
        conflict = charlie["conflicts"][0]
        assert conflict["external_id"] == "99"
        assert conflict["existing_external_path"] == "https://github.com/miethe/some-other-repo/pull/99"

    def test_conflict_is_never_written_even_with_apply(self, world, client_and_calls):
        client, calls = client_and_calls
        rc, _payload = _run(world, ["--apply"], client)
        assert rc == 2
        node_c_posts = [
            c for c in calls if c["method"] == "POST" and "/node_C/" in c["url"]
        ]
        assert not node_c_posts

    def test_unrelated_node_still_applies_despite_another_nodes_conflict(self, world, client_and_calls):
        client, calls = client_and_calls
        rc, payload = _run(world, ["--apply"], client)
        assert rc == 2  # charlie's conflict still surfaces...
        alpha_posts = [c for c in calls if c["method"] == "POST" and "/node_A/" in c["url"]]
        assert len(alpha_posts) == 2  # ...but never blocks node_A's own confident writes


class TestNoPlanFileForSlug:
    def test_reported_as_feature_level_skip_never_raises(self, world, client_and_calls):
        client, _calls = client_and_calls
        rc, payload = _run(world, [], client)
        delta = next(f for f in payload["features"] if f["slug"] == "delta")
        assert delta["plan_ref"] is None
        assert delta["would_write"] == []
        assert len(delta["skipped"]) == 1
        assert "delta" in delta["skipped"][0]["reason"]

    def test_no_feature_slug_node_is_never_scanned(self, world, client_and_calls):
        client, _calls = client_and_calls
        _rc, payload = _run(world, [], client)
        assert not any(f["node_id"] == "node_E" for f in payload["features"])


class TestSlugFilter:
    def test_slug_filter_limits_to_one_feature(self, world, client_and_calls):
        client, _calls = client_and_calls
        rc, payload = _run(world, ["--slug", "bravo"], client)
        assert rc == 0
        assert [f["slug"] for f in payload["features"]] == ["bravo"]


class TestDefaultRepoThreading:
    def test_bare_pr_number_resolves_with_default_repo(self, world, client_and_calls):
        client, _calls = client_and_calls
        plan_dir = world["plan_root"]
        (plan_dir / "echo-v1.md").write_text(
            "---\nfeature_slug: echo\ndoc_type: implementation_plan\npr_refs: [51]\n"
            "status: completed\n---\n\n# Echo\n",
            encoding="utf-8",
        )
        world["node_store"]["node_F"] = _node("node_F", "echo")
        world["node_links"]["node_F"] = []

        rc, payload = _run(world, ["--default-repo", "agentic_meta_dev"], client)
        assert rc == 2  # node_C's unrelated conflict still surfaces; see TestConflictRule
        echo = next(f for f in payload["features"] if f["slug"] == "echo")
        assert echo["would_write"][0]["ident"] == "51"
        assert echo["would_write"][0]["url"] == "https://github.com/miethe/agentic_meta_dev/pull/51"

    def test_bare_pr_number_without_default_repo_is_skipped(self, world, client_and_calls):
        client, _calls = client_and_calls
        plan_dir = world["plan_root"]
        (plan_dir / "echo-v1.md").write_text(
            "---\nfeature_slug: echo\ndoc_type: implementation_plan\npr_refs: [51]\n"
            "status: completed\n---\n\n# Echo\n",
            encoding="utf-8",
        )
        world["node_store"]["node_F"] = _node("node_F", "echo")
        world["node_links"]["node_F"] = []

        rc, payload = _run(world, [], client)
        assert rc == 2  # node_C's unrelated conflict still surfaces; see TestConflictRule
        echo = next(f for f in payload["features"] if f["slug"] == "echo")
        assert echo["would_write"] == []
        assert len(echo["skipped"]) == 1
        assert "no repo context" in echo["skipped"][0]["reason"]


class TestDryRun:
    def test_dry_run_never_calls_attach_external_link(self, world, client_and_calls):
        client, calls = client_and_calls
        _run(world, [], client)
        assert not any(c["method"] == "POST" for c in calls)


class TestJsonShape:
    def test_feature_report_has_the_required_fields(self, world, client_and_calls):
        client, _calls = client_and_calls
        _rc, payload = _run(world, [], client)
        alpha = next(f for f in payload["features"] if f["slug"] == "alpha")
        assert set(alpha.keys()) == {
            "slug", "node_id", "plan_ref", "would_write", "already_present", "skipped",
            "conflicts",
        }
        assert alpha["node_id"] == "node_A"
        assert alpha["plan_ref"] == "docs/project_plans/alpha-v1.md"

    def test_totals_present(self, world, client_and_calls):
        client, _calls = client_and_calls
        _rc, payload = _run(world, [], client)
        assert set(payload["totals"].keys()) == {
            "mode", "features_scanned", "would_write", "already_present", "skipped",
            "conflicts", "applied",
        }
        assert payload["totals"]["mode"] == "dry-run"
        assert payload["totals"]["features_scanned"] == 4  # A/B/C/D (E has no feature_slug)


class TestUsageErrors:
    def test_missing_plan_root_returns_1(self, world, client_and_calls):
        client, _calls = client_and_calls
        rc = backfill_mod.main(
            ["--no-verify-commits", "--tree", "t1", "--plan-root", "/nonexistent/does/not/exist",
             "--repo-root", str(world["repo_root"])],
            client=client,
        )
        assert rc == 1


# --- Orchestrator adjudication (M3): anchor-scoped evidence writes -----------------

class TestAnchorScoping:
    """Evidence attaches to a feature's subtree ROOT(s), not every slug-sharing node.

    A commit/PR ships a feature, not each of its subtasks. Writing the same ref onto all
    41 members of `codex-aos-integration` (measured live) both duplicates the row 41x and
    asserts something false about `not_started` subtasks.
    """

    NODES = [
        # feature A: a clean root + two descendants
        {"id": "n_root", "parent_id": None, "meta": {"feature_slug": "feat-a"}},
        {"id": "n_kid1", "parent_id": "n_root", "meta": {"feature_slug": "feat-a"}},
        {"id": "n_kid2", "parent_id": "n_kid1", "meta": {"feature_slug": "feat-a"}},
        # feature B: siblings under a parent that is NOT stamped -> all are roots
        {"id": "n_sibA", "parent_id": "n_unstamped", "meta": {"feature_slug": "feat-b"}},
        {"id": "n_sibB", "parent_id": "n_unstamped", "meta": {"feature_slug": "feat-b"}},
        {"id": "n_unstamped", "parent_id": None, "meta": {}},
        # a node carrying no slug at all is never selected
        {"id": "n_none", "parent_id": None, "meta": {}},
    ]

    def _pairs(self):
        return [
            (n["id"], (n.get("meta") or {})["feature_slug"])
            for n in self.NODES
            if (n.get("meta") or {}).get("feature_slug")
        ]

    def test_deep_subtree_collapses_to_its_single_root(self):
        anchors = backfill_mod.select_anchor_nodes(self.NODES, self._pairs())
        assert ("n_root", "feat-a") in anchors
        assert ("n_kid1", "feat-a") not in anchors
        assert ("n_kid2", "feat-a") not in anchors

    def test_siblings_under_an_unstamped_parent_are_all_anchors(self):
        anchors = backfill_mod.select_anchor_nodes(self.NODES, self._pairs())
        feat_b = sorted(nid for nid, slug in anchors if slug == "feat-b")
        assert feat_b == ["n_sibA", "n_sibB"]

    def test_anchor_scope_is_the_default_and_all_members_restores_old_behaviour(self):
        client = _FakeClient(self.NODES)
        default = backfill_mod.gather_feature_nodes(client, "tree_x")
        every = backfill_mod.gather_feature_nodes(client, "tree_x", scope="all-members")
        assert len(default) == 3          # n_root + n_sibA + n_sibB
        assert len(every) == 5            # every slug-carrying node
        assert set(default).issubset(set(every))

    def test_slug_filter_still_applies_under_anchor_scope(self):
        client = _FakeClient(self.NODES)
        only_a = backfill_mod.gather_feature_nodes(client, "tree_x", slug_filter="feat-a")
        assert only_a == [("n_root", "feat-a")]


class _FakeClient:
    """Minimal offline stand-in — only tree_nodes is exercised here."""

    def __init__(self, nodes):
        self._nodes = nodes

    def tree_nodes(self, tree_id):
        return self._nodes


class TestServerFieldNameAsymmetry:
    """FR-11 pre-read must match the SERVER's field name, not the request's.

    Regression for a live-only defect: the attach-request body field is `system`, but every
    read path returns `source_system`. The original fake echoed `system`, so the offline
    idempotency test passed while a live `--apply` re-wrote all 11 links on every run. These
    rows are verbatim live shapes.
    """

    LIVE_LINK = {
        "id": "extlink_01KYWSGNSTEQQQPZAWAS7WBG4C",
        "source_system": "github",
        "external_id": "df98ccd7c5dfcbb62f727eb354b535f50310dfdb",
        "external_path": "https://github.com/miethe/agentic_meta_dev/commit/df98ccd7c5dfcbb62f727eb354b535f50310dfdb",
        "context_label": "commit:df98ccd7c5dfcbb62f727eb354b535f50310dfdb",
    }

    def _ref(self):
        return evr.EvidenceRef(
            raw="df98ccd7c5dfcbb62f727eb354b535f50310dfdb",
            kind="commit",
            repo="agentic_meta_dev",
            ident="df98ccd7c5dfcbb62f727eb354b535f50310dfdb",
            url=self.LIVE_LINK["external_path"],
            system="github",
        )

    def test_live_source_system_shape_is_matched(self):
        assert backfill_mod._find_matching_link([self.LIVE_LINK], self._ref()) is not None

    def test_legacy_system_shape_still_matched(self):
        legacy = dict(self.LIVE_LINK)
        legacy["system"] = legacy.pop("source_system")
        assert backfill_mod._find_matching_link([legacy], self._ref()) is not None

    def test_different_ident_does_not_match(self):
        other = dict(self.LIVE_LINK, external_id="0000000")
        assert backfill_mod._find_matching_link([other], self._ref()) is None

    def test_different_system_does_not_match(self):
        other = dict(self.LIVE_LINK, source_system="skillmeat")
        assert backfill_mod._find_matching_link([other], self._ref()) is None


class TestLocalCommitExistenceCheck:
    """Shape-valid is not the same as real (reviewer-gate finding, M3).

    `agentic-redeploy-pipeline-v1.md` cites `7a85dc3`, which is not a valid object in this
    repo; a matching dangling ExternalLink has sat on its node since 2026-06-24. A local
    `git cat-file -t` catches that without any history mining. The runner is injected here,
    so these tests need no git and no network.
    """

    def _ref(self, ident, repo="agentic_meta_dev", kind="commit"):
        return evr.EvidenceRef(
            raw=ident, kind=kind, repo=repo, ident=ident,
            url=f"https://github.com/miethe/{repo}/commit/{ident}", system="github",
        )

    def test_missing_sha_is_dropped_with_a_reason(self):
        kept, dropped = backfill_mod.verify_local_commits(
            [self._ref("7a85dc3")], Path("."), "agentic_meta_dev",
            runner=lambda sha: False,
        )
        assert kept == []
        assert len(dropped) == 1
        assert "does not exist" in dropped[0]["reason"] and "7a85dc3" in dropped[0]["reason"]

    def test_existing_sha_is_kept(self):
        kept, dropped = backfill_mod.verify_local_commits(
            [self._ref("80a9a00")], Path("."), "agentic_meta_dev",
            runner=lambda sha: True,
        )
        assert [r.ident for r in kept] == ["80a9a00"]
        assert dropped == []

    def test_cross_repo_sha_is_never_dropped(self):
        """An intenttree sha cannot be resolved from here — passing it through unverified is
        correct; dropping it would be a false negative introduced by the fix itself."""
        called = []
        kept, dropped = backfill_mod.verify_local_commits(
            [self._ref("a058b91", repo="intenttree")], Path("."), "agentic_meta_dev",
            runner=lambda sha: called.append(sha) or False,
        )
        assert [r.ident for r in kept] == ["a058b91"]
        assert dropped == [] and called == []

    def test_pull_request_refs_are_not_sha_checked(self):
        pr = evr.EvidenceRef(
            raw="32", kind="pull_request", repo="agentic_meta_dev", ident="32",
            url="https://github.com/miethe/agentic_meta_dev/pull/32", system="github",
        )
        kept, dropped = backfill_mod.verify_local_commits(
            [pr], Path("."), "agentic_meta_dev", runner=lambda sha: False,
        )
        assert kept == [pr] and dropped == []

    def test_git_unavailable_passes_refs_through(self):
        """An environment failure must not masquerade as 'this commit does not exist'."""
        def boom(sha):
            raise OSError("git missing")
        try:
            kept, dropped = backfill_mod.verify_local_commits(
                [self._ref("80a9a00")], Path("."), "agentic_meta_dev", runner=boom,
            )
        except OSError:
            pytest.fail("verify_local_commits must not propagate a git environment failure")
        assert [r.ident for r in kept] == ["80a9a00"] and dropped == []
