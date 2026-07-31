#!/usr/bin/env python3
"""Tests for `_evidence_refs.py` — Shipped Work Ledger M3, D-M3-3 (fail-closed normalization).

Offline, no network. Covers every row of the M3 leg contract's §6 L1 required-behaviour table,
plus `parse_frontmatter_list`'s block-list and inline-flow extraction forms.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import _evidence_refs as er  # noqa: E402
import _itt_client as itc  # noqa: E402


# ---------------------------------------------------------------------------
# Row 1 — bare short SHA, default repo supplied.
# ---------------------------------------------------------------------------
def test_bare_short_sha_uses_default_repo():
    result = er.normalize_commit_ref("b9b4613", default_repo="agentic_meta_dev")
    assert isinstance(result, er.EvidenceRef)
    assert result.kind == "commit"
    assert result.repo == "agentic_meta_dev"
    assert result.ident == "b9b4613"
    assert result.url == "https://github.com/miethe/agentic_meta_dev/commit/b9b4613"
    assert result.system == "github"


# ---------------------------------------------------------------------------
# Row 2 — full 40-char SHA accepted.
# ---------------------------------------------------------------------------
def test_full_40_char_sha_accepted():
    sha = "ab643191c66e94f41877072780f75b608d619d7a"
    result = er.normalize_commit_ref(sha, default_repo="agentic_meta_dev")
    assert isinstance(result, er.EvidenceRef)
    assert result.kind == "commit"
    assert result.ident == sha
    assert result.url == f"https://github.com/miethe/agentic_meta_dev/commit/{sha}"


# ---------------------------------------------------------------------------
# Row 3 — quoted sha + trailing comment: repo inferred from the comment, never a wrong guess.
# ---------------------------------------------------------------------------
def test_quoted_sha_with_trailing_comment_infers_repo():
    raw = '"a058b91"   # intenttree — feat(itt-cli): stamp node slug'
    result = er.normalize_commit_ref(raw, default_repo="fallback-repo")
    assert isinstance(result, er.EvidenceRef)
    assert result.kind == "commit"
    assert result.ident == "a058b91"
    assert result.repo == "intenttree"  # inferred from comment, NOT the default_repo
    assert result.url == "https://github.com/miethe/intenttree/commit/a058b91"


def test_sha_with_comment_falls_back_to_default_repo_when_comment_unusable():
    raw = '"a058b91"   # — no usable leading token here...'
    result = er.normalize_commit_ref(raw, default_repo="fallback-repo")
    assert isinstance(result, er.EvidenceRef)
    # first comment token is "—" (an em dash) which fails the confident-token check.
    assert result.repo == "fallback-repo"


# ---------------------------------------------------------------------------
# Row 4 — repo@sha + free prose: repo explicit, never defaulted.
# ---------------------------------------------------------------------------
def test_repo_at_sha_with_free_prose():
    raw = "MeatySkills@fe3537b (feat/…, unmerged)"
    result = er.normalize_commit_ref(raw, default_repo="agentic_meta_dev")
    assert isinstance(result, er.EvidenceRef)
    assert result.kind == "commit"
    assert result.repo == "MeatySkills"
    assert result.ident == "fe3537b"
    assert result.url == "https://github.com/miethe/MeatySkills/commit/fe3537b"


# ---------------------------------------------------------------------------
# Row 5 — repo-qualified PR ref.
# ---------------------------------------------------------------------------
def test_repo_qualified_pr_ref():
    result = er.normalize_pr_ref("agentic_meta_dev#33")
    assert isinstance(result, er.EvidenceRef)
    assert result.kind == "pull_request"
    assert result.repo == "agentic_meta_dev"
    assert result.ident == "33"
    assert result.url == "https://github.com/miethe/agentic_meta_dev/pull/33"


# ---------------------------------------------------------------------------
# Row 6 — full URL passed through unchanged.
# ---------------------------------------------------------------------------
def test_full_pr_url_passed_through_unchanged():
    url = "https://github.com/miethe/agentic_meta_dev/pull/32"
    result = er.normalize_pr_ref(url)
    assert isinstance(result, er.EvidenceRef)
    assert result.kind == "pull_request"
    assert result.repo == "agentic_meta_dev"
    assert result.ident == "32"
    assert result.url == url  # unchanged, not re-derived


# ---------------------------------------------------------------------------
# Row 7 — bare integer PR number: needs a default_repo, else SkippedRef.
# ---------------------------------------------------------------------------
def test_bare_int_pr_ref_with_default_repo():
    for raw in (51, "51"):
        result = er.normalize_pr_ref(raw, default_repo="agentic_meta_dev")
        assert isinstance(result, er.EvidenceRef), raw
        assert result.kind == "pull_request"
        assert result.repo == "agentic_meta_dev"
        assert result.ident == "51"
        assert result.url == "https://github.com/miethe/agentic_meta_dev/pull/51"


def test_bare_int_pr_ref_without_default_repo_is_skipped():
    result = er.normalize_pr_ref(51)
    assert isinstance(result, er.SkippedRef)
    assert "51" in result.reason
    assert "default_repo" in result.reason


# ---------------------------------------------------------------------------
# Row 8 — the canonical trap: a non-PR sentinel must never mint a fake PR URL.
# ---------------------------------------------------------------------------
def test_direct_squash_to_main_sentinel_is_skipped_not_guessed():
    result = er.normalize_pr_ref("direct-squash-to-main", default_repo="agentic_meta_dev")
    assert isinstance(result, er.SkippedRef)
    assert result.raw == "direct-squash-to-main"
    assert "sentinel" in result.reason
    assert "direct-squash-to-main" in result.reason


# ---------------------------------------------------------------------------
# Row 9 — empty / None / whitespace-only values are always skipped, for both normalizers.
# ---------------------------------------------------------------------------
def test_empty_none_and_whitespace_are_skipped_for_commit_refs():
    for raw in ("", None, "   "):
        result = er.normalize_commit_ref(raw, default_repo="agentic_meta_dev")
        assert isinstance(result, er.SkippedRef), raw
        assert "empty" in result.reason


def test_empty_none_and_whitespace_are_skipped_for_pr_refs():
    for raw in ("", None, "   "):
        result = er.normalize_pr_ref(raw, default_repo="agentic_meta_dev")
        assert isinstance(result, er.SkippedRef), raw
        assert "empty" in result.reason


# ---------------------------------------------------------------------------
# Row 10 — a hex-ish-looking word is NOT a confident SHA.
# ---------------------------------------------------------------------------
def test_hex_ish_word_is_not_a_confident_sha():
    result = er.normalize_commit_ref("deadbeef-not-a-sha-just-words", default_repo="agentic_meta_dev")
    assert isinstance(result, er.SkippedRef)
    assert "not a confident commit sha" in result.reason


# ---------------------------------------------------------------------------
# Additional fail-closed coverage beyond the ten rows.
# ---------------------------------------------------------------------------
def test_bare_sha_without_any_repo_hint_yields_git_system_and_no_url():
    result = er.normalize_commit_ref("b9b4613")
    assert isinstance(result, er.EvidenceRef)
    assert result.repo is None
    assert result.url is None
    assert result.system == "git"


def test_unparseable_pr_ref_is_skipped_generically():
    result = er.normalize_pr_ref("some free-text note", default_repo="agentic_meta_dev")
    assert isinstance(result, er.SkippedRef)
    assert "not a confident pull request reference" in result.reason


def test_normalize_refs_splits_confident_and_skipped():
    refs, skipped = er.normalize_refs(
        ["b9b4613", "deadbeef-not-a-sha-just-words"],
        ["agentic_meta_dev#33", "direct-squash-to-main"],
        default_repo="agentic_meta_dev",
    )
    assert len(refs) == 2
    assert {r.kind for r in refs} == {"commit", "pull_request"}
    assert len(skipped) == 2
    assert {s.raw for s in skipped} == {"deadbeef-not-a-sha-just-words", "direct-squash-to-main"}


def test_normalize_refs_handles_empty_lists():
    refs, skipped = er.normalize_refs([], [])
    assert refs == []
    assert skipped == []

    refs, skipped = er.normalize_refs(None, None)
    assert refs == []
    assert skipped == []


# ---------------------------------------------------------------------------
# parse_frontmatter_list — block-list form.
# ---------------------------------------------------------------------------
def test_parse_block_list_form():
    text = (
        "---\n"
        "commit_refs:\n"
        "  - b9b4613\n"
        "  - \"a058b91\"   # intenttree — feat(...)\n"
        "status: completed\n"
        "---\n"
    )
    items = er.parse_frontmatter_list(text, "commit_refs")
    # The trailing comment is PRESERVED, because it carries the ref's owning repo and the
    # normalize_* functions (not the extractor) own the split. Stripping it here silently
    # disabled repo inference and minted wrong-but-plausible URLs. See _clean_list_item.
    assert items[0] == "b9b4613"
    assert items[1].startswith("a058b91")
    assert "intenttree" in items[1]


def test_parse_block_list_stops_at_dedent():
    text = (
        "---\n"
        "commit_refs:\n"
        "  - b9b4613\n"
        "pr_refs:\n"
        "  - 51\n"
        "---\n"
    )
    assert er.parse_frontmatter_list(text, "commit_refs") == ["b9b4613"]
    assert er.parse_frontmatter_list(text, "pr_refs") == ["51"]


# ---------------------------------------------------------------------------
# parse_frontmatter_list — inline flow form.
# ---------------------------------------------------------------------------
def test_parse_inline_flow_form_single_item():
    text = "---\ncommit_refs: [ab643191c66e94f41877072780f75b608d619d7a]\n---\n"
    assert er.parse_frontmatter_list(text, "commit_refs") == [
        "ab643191c66e94f41877072780f75b608d619d7a"
    ]


def test_parse_inline_flow_form_multiple_quoted_items():
    text = '---\npr_refs: ["agentic_meta_dev#33", "direct-squash-to-main"]\n---\n'
    assert er.parse_frontmatter_list(text, "pr_refs") == [
        "agentic_meta_dev#33", "direct-squash-to-main"
    ]


def test_parse_inline_flow_form_bare_int():
    text = "---\npr_refs: [51]\n---\n"
    assert er.parse_frontmatter_list(text, "pr_refs") == ["51"]


# ---------------------------------------------------------------------------
# parse_frontmatter_list — absence / malformed input never raises.
# ---------------------------------------------------------------------------
def test_parse_missing_key_returns_empty_list():
    text = "---\nstatus: completed\n---\n"
    assert er.parse_frontmatter_list(text, "commit_refs") == []


def test_parse_key_with_no_items_returns_empty_list():
    text = "---\ncommit_refs:\nstatus: completed\n---\n"
    assert er.parse_frontmatter_list(text, "commit_refs") == []


def test_parse_only_matches_top_level_key():
    # An indented "commit_refs:"-looking line (e.g. nested under another key) must NOT match.
    text = "---\nnested:\n  commit_refs:\n    - should-not-be-seen\n---\n"
    assert er.parse_frontmatter_list(text, "commit_refs") == []


def test_parse_unterminated_flow_list_is_not_confident():
    text = "---\ncommit_refs: [b9b4613\nstatus: completed\n---\n"
    assert er.parse_frontmatter_list(text, "commit_refs") == []


# ---------------------------------------------------------------------------
# _itt_client.py additions (M3 L1) — get_node_full / tree_nodes / attach_external_link /
# attach_evidence / record_validation. All offline: faked at the `http_call` seam, no network.
# ---------------------------------------------------------------------------
def _fake_http_client(responses: dict[tuple[str, str], itc.HttpResult]):
    """Build an IttClient whose http_call seam answers from a fixed (method, path) -> HttpResult
    map, keyed on the URL path+query with the fake base URL stripped off. Records every call."""
    calls: list[dict[str, Any]] = []
    base = "http://fake-itt.test"

    def http_call(url: str, method: str, body: dict[str, Any], headers: dict[str, str]) -> itc.HttpResult:
        calls.append({"url": url, "method": method, "body": body, "headers": headers})
        path = url[len(base):]
        key = (method, path)
        if key not in responses:
            raise AssertionError(f"unexpected HTTP call: {method} {path}")
        return responses[key]

    client = itc.IttClient(http_call=http_call, api_url=base)
    return client, calls


class TestIttClientM3Additions:
    def test_get_node_full_includes_query_params(self):
        node_payload = {"id": "node_1", "meta": {}, "external_links": [], "completion_evidence": []}
        client, calls = _fake_http_client({
            ("GET", "/api/v1/nodes/node_1?include=completion_evidence,external_links,validation_runs"):
                itc.HttpResult(200, json.dumps(node_payload)),
        })
        result = client.get_node_full("node_1")
        assert result == node_payload
        assert calls[0]["method"] == "GET"

    def test_get_node_full_custom_include(self):
        client, calls = _fake_http_client({
            ("GET", "/api/v1/nodes/node_1?include=external_links"): itc.HttpResult(200, "{}"),
        })
        client.get_node_full("node_1", include=("external_links",))
        assert calls[0]["url"].endswith("?include=external_links")

    def test_tree_nodes_returns_nodes_list(self):
        graph = {"nodes": [{"id": "node_A"}, {"id": "node_B"}], "edges": []}
        client, _calls = _fake_http_client({
            ("GET", "/api/v1/trees/tree_1/graph"): itc.HttpResult(200, json.dumps(graph)),
        })
        assert client.tree_nodes("tree_1") == graph["nodes"]

    def test_tree_nodes_missing_key_returns_empty_list(self):
        client, _calls = _fake_http_client({
            ("GET", "/api/v1/trees/tree_1/graph"): itc.HttpResult(200, "{}"),
        })
        assert client.tree_nodes("tree_1") == []

    def test_attach_external_link_sends_full_body(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/external-links"): itc.HttpResult(200, '{"ok": true}'),
        })
        result = client.attach_external_link(
            "node_1", system="github", external_id="33", external_path="pull/33",
            context_label="M3 merge", stored_ref={"sha": "abc"},
        )
        assert result == {"ok": True}
        body = calls[0]["body"]
        assert body == {
            "system": "github", "external_id": "33", "external_path": "pull/33",
            "context_label": "M3 merge", "stored_ref": {"sha": "abc"},
        }

    def test_attach_external_link_omits_optional_fields_when_absent(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/external-links"): itc.HttpResult(200, "{}"),
        })
        client.attach_external_link("node_1", system="git", external_id="b9b4613")
        assert calls[0]["body"] == {"system": "git", "external_id": "b9b4613"}

    def test_attach_external_link_raises_on_non_2xx(self):
        client, _calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/external-links"): itc.HttpResult(500, "boom"),
        })
        with pytest.raises(itc.IttError):
            client.attach_external_link("node_1", system="github", external_id="33")

    def test_attach_evidence_sends_full_body(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/evidence"): itc.HttpResult(200, "{}"),
        })
        client.attach_evidence(
            "node_1", kind="git_merge", label="merge", ref_value="abc123",
            delivery_class="shipped", occurred_at="2026-07-31T00:00:00Z", data={"x": 1},
        )
        assert calls[0]["body"] == {
            "kind": "git_merge", "label": "merge", "ref_value": "abc123",
            "delivery_class": "shipped", "occurred_at": "2026-07-31T00:00:00Z", "data": {"x": 1},
        }

    def test_attach_evidence_minimal_body(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/evidence"): itc.HttpResult(200, "{}"),
        })
        client.attach_evidence("node_1", kind="validation")
        assert calls[0]["body"] == {"kind": "validation"}

    def test_record_validation_uses_primary_route_when_available(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/validations"): itc.HttpResult(
                200, json.dumps({"id": "val_1"})
            ),
        })
        result = client.record_validation("node_1", command="pytest -q", status="pass")
        assert result["_write_path"] == "validations"
        assert result["id"] == "val_1"
        assert len(calls) == 1  # no fallback call made

    def test_record_validation_falls_back_to_evidence_on_404(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/validations"): itc.HttpResult(404, "not found"),
            ("POST", "/api/v1/nodes/node_1/evidence"): itc.HttpResult(200, json.dumps({"id": "ev_1"})),
        })
        result = client.record_validation(
            "node_1", command="pytest -q", status="pass", output_ref="ci://run/1"
        )
        assert result["_write_path"] == "evidence_fallback"
        assert result["id"] == "ev_1"
        assert len(calls) == 2
        assert calls[0]["url"].endswith("/validations")
        assert calls[1]["url"].endswith("/evidence")
        fallback_body = calls[1]["body"]
        assert fallback_body["kind"] == "validation"
        assert fallback_body["label"] == "pytest -q"
        assert fallback_body["ref_value"] == "ci://run/1"
        assert fallback_body["data"]["command"] == "pytest -q"
        assert fallback_body["data"]["status"] == "pass"

    def test_record_validation_raises_on_non_404_non_2xx(self):
        client, _calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/validations"): itc.HttpResult(500, "boom"),
        })
        with pytest.raises(itc.IttError):
            client.record_validation("node_1", command="pytest -q", status="pass")

    def test_record_validation_optional_fields_reach_the_fallback_data(self):
        client, calls = _fake_http_client({
            ("POST", "/api/v1/nodes/node_1/validations"): itc.HttpResult(404, "not found"),
            ("POST", "/api/v1/nodes/node_1/evidence"): itc.HttpResult(200, "{}"),
        })
        client.record_validation(
            "node_1", command="pytest -q", status="pass", kind="ci",
            started_at="2026-07-31T00:00:00Z", finished_at="2026-07-31T00:05:00Z",
            environment={"python": "3.11"},
        )
        fallback_body = calls[1]["body"]
        assert fallback_body["data"]["started_at"] == "2026-07-31T00:00:00Z"
        assert fallback_body["data"]["finished_at"] == "2026-07-31T00:05:00Z"
        assert fallback_body["data"]["environment"] == {"python": "3.11"}

    def test_token_never_appears_unencrypted_outside_auth_header(self):
        client, calls = _fake_http_client({
            ("GET", "/api/v1/trees/tree_1/graph"): itc.HttpResult(200, "{}"),
        })
        client._api_token = "tok_super_secret"  # noqa: SLF001 (test-only access to assert on it)
        client.tree_nodes("tree_1")
        assert calls[0]["headers"]["Authorization"] == "Bearer tok_super_secret"
        assert "tok_super_secret" not in calls[0]["url"]

    def test_update_node_meta_behaviour_is_unchanged_by_the_new_additions(self):
        """Regression guard: M3 additions must not perturb M2's `update_node_meta` at all."""
        client, calls = _fake_http_client({
            ("PATCH", "/api/v1/nodes/node_1"): itc.HttpResult(200, json.dumps({"id": "node_1", "meta": {"a": 1}})),
        })
        result = client.update_node_meta("node_1", {"a": 1})
        assert result == {"id": "node_1", "meta": {"a": 1}}
        assert calls[0]["method"] == "PATCH"
        assert calls[0]["body"] == {"meta": {"a": 1}}


# --- Reviewer-gate regression (M3): the extractor -> normalizer path, end to end -----
#
# The unit tests above call normalize_commit_ref DIRECTLY. That is exactly how a real defect
# hid: parse_frontmatter_list stripped the trailing comment before normalization ever ran, so
# comment-based repo inference was dead code in production while its direct-call test passed.
# These tests drive the SAME path the production scripts use.

def test_comment_repo_inference_survives_the_real_extractor_path():
    text = (
        "---\n"
        "commit_refs:\n"
        '  - "a058b91"   # intenttree — feat(itt-cli): opt-in --stamp-frontmatter writeback\n'
        '  - "bb576c8"   # agentic_meta_dev — docs(frontmatter): OQ-3 stamp-back shipped\n'
        "---\n"
    )
    raw = er.parse_frontmatter_list(text, "commit_refs")
    refs, skipped = er.normalize_refs(raw, [], default_repo="agentic_meta_dev")
    assert skipped == []
    by_ident = {r.ident: r for r in refs}
    # The whole point: a cross-repo sha must NOT be attributed to --default-repo.
    assert by_ident["a058b91"].repo == "intenttree"
    assert by_ident["a058b91"].url == "https://github.com/miethe/intenttree/commit/a058b91"
    assert by_ident["bb576c8"].repo == "agentic_meta_dev"


def test_sentinel_still_skipped_through_the_real_extractor_path():
    text = (
        "---\n"
        "pr_refs:\n"
        '  - "direct-squash-to-main"\n'
        "---\n"
    )
    raw = er.parse_frontmatter_list(text, "pr_refs")
    refs, skipped = er.normalize_refs([], raw, default_repo="agentic_meta_dev")
    assert refs == []
    assert len(skipped) == 1 and "sentinel" in skipped[0].reason


def test_whole_line_comment_is_dropped_not_normalized():
    text = (
        "---\n"
        "commit_refs:\n"
        "  - 80a9a00  # P0 guardrails shipped\n"
        "  # + a trailing prose-only comment line that is not a ref at all\n"
        "---\n"
    )
    raw = er.parse_frontmatter_list(text, "commit_refs")
    refs, skipped = er.normalize_refs(raw, [], default_repo="agentic_meta_dev")
    assert [r.ident for r in refs] == ["80a9a00"]
    assert skipped == []


# --- Repo attribution must be separator-gated (self-inflicted regression, M3) --------
#
# The first attempt at wiring comment-based repo inference trusted the comment's first
# WORD. Against real corpus values that produced repo "P0" and repo "gate-coverage" for
# two commits that are plainly agentic_meta_dev's — i.e. it fixed one wrong-URL bug by
# introducing a broader one. Only the backfill's conflict guard caught it. Inference is
# now gated on the corpus's actual `<repo> — <prose>` separator.

def test_prose_comment_does_not_yield_a_repo():
    for prose in (
        "80a9a00  # P0 guardrails + P1 /redeploy + P3 docs shipped to main (2026-06-21)",
        "7a85dc3  # gate-coverage fix (artifact-atlas) + P2 prep + guide fixes",
        "deadbee  # some prose with - a hyphen in it",
        "cafebab  # (parenthetical) note",
    ):
        ref = er.normalize_commit_ref(prose, default_repo="agentic_meta_dev")
        assert isinstance(ref, er.EvidenceRef)
        assert ref.repo == "agentic_meta_dev", f"prose comment leaked a repo: {prose!r} -> {ref.repo!r}"


def test_separator_comment_yields_the_named_repo():
    for raw, want in (
        ("a058b91   # intenttree — feat(itt-cli): opt-in --stamp-frontmatter writeback", "intenttree"),
        ("bb576c8   # agentic_meta_dev — docs(frontmatter): OQ-3 shipped", "agentic_meta_dev"),
        ("fe3537b   # MeatySkills -- feat: routing record", "MeatySkills"),
    ):
        ref = er.normalize_commit_ref(raw, default_repo="agentic_meta_dev")
        assert ref.repo == want, f"{raw!r} -> {ref.repo!r}, wanted {want!r}"


def test_attribution_never_overrides_an_explicit_repo_qualifier():
    """`repo@sha` states its repo outright; a comment must not be able to contradict it."""
    ref = er.normalize_commit_ref(
        "MeatySkills@fe3537b   # intenttree — misleading comment", default_repo="agentic_meta_dev"
    )
    assert ref.repo == "MeatySkills"
