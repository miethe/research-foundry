#!/usr/bin/env python3
"""Tests for migrate-plan-layout.py (Shipped Work Ledger M4 L2 — highest blast radius).

Offline, no network, no live ``itt``/git server. File moves are exercised through an injected
``mover`` seam (mirrors the ``_itt_client`` runner-injection style used elsewhere in this test
suite) so the suite never depends on a real git repository. Covers, per the leg contract §5-L2
Definition of Done:

  (a) the one-segment move rule + nested-subdir preservation (D-M4-2)
  (b) collision refusal — both destination-exists and two-sources-one-destination (asserted, not
      trusted)
  (c) additive, format-preserving ``classification:`` frontmatter insertion (D-M4-5) — including
      the never-overwrite-an-existing-key rule
  (d) archive exclusion (D-M4-4) + the ``--include-archives`` override
  (e) at least four real ref prefix forms (plain / leading-slash / bare / relative-with-docs /
      repo-qualified / relative-bare — six are implemented)
  (f) the other-repo skip (the exact M3-F1 failure shape this leg exists to prevent)
  (g) dangling vs "no such classification for this type" as DISTINCT skip reasons
  (h) dry-run writes nothing at all, byte-for-byte
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses (3.12) needs the module registered to resolve types
    spec.loader.exec_module(mod)
    return mod


mpl = _load("migrate_plan_layout_mod", "migrate-plan-layout.py")


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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _plan(classification: str = "features", extra: str = "") -> str:
    return (
        "---\n"
        "title: Some Plan\n"
        f"feature_slug: {classification}-thing\n"
        "doc_type: implementation_plan\n"
        f"{extra}"
        "---\n\n# Body untouched\n"
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return tmp_path


def _fake_mover(calls: list[tuple[str, str]]):
    def mover(repo_root: Path, old_rel: str, new_rel: str) -> None:
        src = repo_root / old_rel
        dest = repo_root / new_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        calls.append((old_rel, new_rel))
    return mover


# --------------------------------------------------------------------------------------------
# compute_moves / detect_collisions
# --------------------------------------------------------------------------------------------
class TestComputeMoves:
    def test_one_segment_dropped_and_nested_subdir_preserved(self, repo):
        _write(
            repo / "docs/project_plans/implementation_plans/features/op-story-pipeline-v1/phase-3.md",
            _plan(),
        )
        moves = mpl.compute_moves(repo)
        assert len(moves) == 1
        m = moves[0]
        assert m.rest == "op-story-pipeline-v1/phase-3.md"
        assert m.old_rel == "docs/project_plans/implementation_plans/features/op-story-pipeline-v1/phase-3.md"
        assert m.new_rel == "docs/project_plans/implementation_plans/op-story-pipeline-v1/phase-3.md"

    def test_top_level_file_in_classification_dir(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        moves = mpl.compute_moves(repo)
        assert moves[0].rest == "foo.md"
        assert moves[0].new_rel == "docs/project_plans/PRDs/foo.md"

    def test_nonexistent_classification_dir_contributes_nothing(self, repo):
        _write(repo / "docs/project_plans/PRDs/infrastructure/bar.md", _plan())
        moves = mpl.compute_moves(repo)
        # PRDs/enhancements was never created — no error, just no entries for that combo.
        assert all(m.classification != "enhancements" for m in moves if m.type_dir == "PRDs")

    def test_feature_contracts_included_per_d_m4_3(self, repo):
        _write(repo / "docs/project_plans/feature_contracts/enhancements/x.md", _plan())
        moves = mpl.compute_moves(repo)
        assert moves[0].type_dir == "feature_contracts"
        assert moves[0].new_rel == "docs/project_plans/feature_contracts/x.md"


class TestDetectCollisions:
    def test_destination_already_exists(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/project_plans/PRDs/foo.md", "already here")
        moves = mpl.compute_moves(repo)
        collisions = mpl.detect_collisions(repo, moves)
        assert len(collisions) == 1
        assert collisions[0]["reason"] == "destination already exists on disk"

    def test_two_sources_map_to_same_destination(self, repo):
        # Never happens today (measured ground truth: 0 collisions) but must be ASSERTED.
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/project_plans/PRDs/infrastructure/foo.md", _plan())
        moves = mpl.compute_moves(repo)
        collisions = mpl.detect_collisions(repo, moves)
        assert len(collisions) == 1
        assert "collides with another move source" in collisions[0]["reason"]

    def test_no_collision_in_the_clean_case(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/project_plans/PRDs/infrastructure/bar.md", _plan())
        moves = mpl.compute_moves(repo)
        assert mpl.detect_collisions(repo, moves) == []


# --------------------------------------------------------------------------------------------
# classification: frontmatter insert — additive, format-preserving (D-M4-5)
# --------------------------------------------------------------------------------------------
class TestClassificationInsert:
    def test_insert_is_additive_and_preserves_unrelated_bytes(self):
        text = "---\ntitle: X\nfeature_slug: alpha\n---\n\n# Body\n"
        out = mpl.insert_classification(text, "features")
        assert "classification: features" in out
        assert "title: X" in out
        assert "feature_slug: alpha" in out
        assert out.endswith("\n\n# Body\n") or "# Body" in out

    def test_has_top_level_key_detects_existing(self):
        text = "---\nclassification: infrastructure\ntitle: X\n---\n\n# Body\n"
        assert mpl.has_top_level_key(text, "classification") is True

    def test_has_top_level_key_false_when_absent(self):
        text = "---\ntitle: X\n---\n\n# Body\n"
        assert mpl.has_top_level_key(text, "classification") is False

    def test_insert_raises_when_no_frontmatter(self):
        with pytest.raises(ValueError):
            mpl.insert_classification("# Body only, no frontmatter\n", "features")


# --------------------------------------------------------------------------------------------
# apply_moves (fake mover — no real git required)
# --------------------------------------------------------------------------------------------
class TestApplyMoves:
    def test_moves_file_and_stamps_classification(self, repo):
        plan_path = repo / "docs/project_plans/PRDs/features/foo.md"
        _write(plan_path, _plan())
        moves = mpl.compute_moves(repo)
        calls: list[tuple[str, str]] = []
        applied, conflicts, link_summary, _detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover(calls))

        assert not plan_path.exists()
        new_path = repo / "docs/project_plans/PRDs/foo.md"
        assert new_path.exists()
        text = new_path.read_text(encoding="utf-8")
        assert "classification: features" in text
        assert "title: Some Plan" in text  # unrelated bytes preserved
        assert calls == [("docs/project_plans/PRDs/features/foo.md", "docs/project_plans/PRDs/foo.md")]
        assert len(applied) == 1
        assert conflicts == []
        assert link_summary == {"rewritten": 0, "already_fine": 0, "skipped": 0}

    def test_never_moves_a_collision(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/project_plans/PRDs/foo.md", "already here")
        moves = mpl.compute_moves(repo)
        collisions = mpl.detect_collisions(repo, moves)
        collision_old_rels = {c["old_rel"] for c in collisions}
        calls: list[tuple[str, str]] = []
        applied, _conflicts, _link_summary, _detail = mpl.apply_moves(
            repo, moves, collision_old_rels, mover=_fake_mover(calls)
        )

        assert applied == []
        assert calls == []
        assert (repo / "docs/project_plans/PRDs/features/foo.md").exists()  # untouched
        assert (repo / "docs/project_plans/PRDs/foo.md").read_text(encoding="utf-8") == "already here"

    def test_never_overwrites_an_existing_classification_key(self, repo):
        plan_path = repo / "docs/project_plans/PRDs/features/foo.md"
        _write(plan_path, _plan(extra="classification: infrastructure\n"))
        moves = mpl.compute_moves(repo)
        calls: list[tuple[str, str]] = []
        applied, conflicts, _link_summary, _detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover(calls))

        new_path = repo / "docs/project_plans/PRDs/foo.md"
        text = new_path.read_text(encoding="utf-8")
        assert text.count("classification:") == 1
        assert "classification: infrastructure" in text  # never overwritten to "features"
        assert len(conflicts) == 1
        assert len(applied) == 1  # the move itself still happens; only the stamp is skipped


# --------------------------------------------------------------------------------------------
# Refs — prefix-form classification (at least four real forms; six implemented).
# --------------------------------------------------------------------------------------------
class TestRefPrefixForms:
    def _moves_by_key(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        moves = mpl.compute_moves(repo)
        return {(m.type_dir, m.classification, m.rest): m for m in moves}

    def _classify(self, repo, text, excluded_old_rels=None):
        occ = mpl.find_ref_occurrences(text)[0]
        return mpl.classify_occurrence(repo, self._moves_by_key(repo), excluded_old_rels or {}, occ), occ

    def test_plain_prefix(self, repo):
        (action, _reason), occ = self._classify(repo, "See docs/project_plans/PRDs/features/foo.md for details.\n")
        assert action == "rewrite"
        assert occ["prefix"] == "docs/"

    def test_leading_slash_prefix(self, repo):
        (action, _), occ = self._classify(repo, "See /docs/project_plans/PRDs/features/foo.md for details.\n")
        assert action == "rewrite"
        assert occ["prefix"] == "/docs/"

    def test_bare_prefix_no_docs(self, repo):
        (action, _), occ = self._classify(repo, "ref: project_plans/PRDs/features/foo.md\n")
        assert action == "rewrite"
        assert occ["prefix"] == ""

    def test_relative_with_docs_prefix(self, repo):
        (action, _), occ = self._classify(repo, "[x](../../docs/project_plans/PRDs/features/foo.md)\n")
        assert action == "rewrite"
        assert occ["prefix"] == "../../docs/"

    def test_repo_qualified_prefix(self, repo):
        (action, _), occ = self._classify(repo, "agentic_meta_dev/docs/project_plans/PRDs/features/foo.md\n")
        assert action == "rewrite"
        assert occ["prefix"] == "agentic_meta_dev/docs/"

    def test_relative_bare_prefix(self, repo):
        (action, _), occ = self._classify(repo, "see ../project_plans/PRDs/features/foo.md\n")
        assert action == "rewrite"
        assert occ["prefix"] == "../"

    @pytest.mark.parametrize("text,marker", [
        ("../intenttree/docs/project_plans/PRDs/features/foo.md", "intenttree"),
        ("skillmeat/docs/project_plans/PRDs/features/foo.md", "skillmeat"),
        ("research-foundry/repo/docs/project_plans/PRDs/features/foo.md", "research-foundry"),
        ("/Users/miethe/dev/meatycapture/docs/project_plans/PRDs/features/foo.md", "meatycapture"),
    ])
    def test_other_repo_prefix_is_never_rewritten(self, repo, text, marker):
        (action, reason), _occ = self._classify(repo, text + "\n")
        assert action == "skip"
        assert marker in reason

    def test_unrecognized_prefix_form_is_skipped_not_guessed(self, repo):
        (action, reason), occ = self._classify(repo, "somejust-docs/project_plans/PRDs/features/foo.md\n")
        assert action == "skip"
        assert "unrecognized ref prefix form" in reason
        assert occ["prefix"] == "somejust-docs/"

    def test_invalid_type_classification_combo_is_skipped_with_specific_reason(self, repo):
        # PRDs/enhancements is never a real directory in this corpus (measured ground truth).
        (action, reason), _occ = self._classify(repo, "docs/project_plans/PRDs/enhancements/ghost.md\n")
        assert action == "skip"
        assert "no docs/project_plans/PRDs/enhancements directory exists" in reason

    def test_dangling_reference_is_distinct_from_invalid_combo(self, repo):
        # PRDs/features DOES exist (foo.md lives there via the fixture helper) but this filename
        # does not — a real, pre-existing broken reference, not an out-of-scope combination.
        (action, reason), _occ = self._classify(repo, "docs/project_plans/PRDs/features/nonexistent.md\n")
        assert action == "dangling"
        assert "does not exist on disk" in reason

    def test_nested_subdir_ref_drops_only_the_classification_segment(self, repo):
        _write(
            repo / "docs/project_plans/implementation_plans/features/op-story-pipeline-v1/phase-3.md",
            _plan(),
        )
        moves = mpl.compute_moves(repo)
        moves_by_key = {(m.type_dir, m.classification, m.rest): m for m in moves}
        text = "docs/project_plans/implementation_plans/features/op-story-pipeline-v1/phase-3.md\n"
        occ = mpl.find_ref_occurrences(text)[0]
        action, _reason = mpl.classify_occurrence(repo, moves_by_key, {}, occ)
        assert action == "rewrite"
        new_text, applied = mpl.rewrite_file_text(text, [{**occ, "action": action, "reason": None,
                                                            "old_text": text[occ["start"]:occ["end"]],
                                                            "new_text": occ["prefix"] + "project_plans/implementation_plans/op-story-pipeline-v1/phase-3.md"}])
        assert new_text == "docs/project_plans/implementation_plans/op-story-pipeline-v1/phase-3.md\n"
        assert len(applied) == 1


# --------------------------------------------------------------------------------------------
# Archive exclusion (D-M4-4)
# --------------------------------------------------------------------------------------------
class TestArchiveExclusion:
    def test_enablement_file_excluded_by_default(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/enablement/handoff.md", "docs/project_plans/PRDs/features/foo.md\n")
        moves = mpl.compute_moves(repo)
        report = mpl.build_refs_report(repo, moves, {}, include_archives=False, apply=False)
        assert report["excluded_archive_files"] == 1
        assert report["rewritten"] == []  # the only ref was inside the excluded archive

    def test_intenttree_live_seed_excluded_by_default(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/intenttree-live-seed/seed.md", "docs/project_plans/PRDs/features/foo.md\n")
        moves = mpl.compute_moves(repo)
        report = mpl.build_refs_report(repo, moves, {}, include_archives=False, apply=False)
        assert report["excluded_archive_files"] == 1

    def test_include_archives_flag_scans_them(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/enablement/handoff.md", "docs/project_plans/PRDs/features/foo.md\n")
        moves = mpl.compute_moves(repo)
        report = mpl.build_refs_report(repo, moves, {}, include_archives=True, apply=False)
        assert report["excluded_archive_files"] == 0
        assert len(report["rewritten"]) == 1
        assert report["rewritten"][0]["file"] == "docs/enablement/handoff.md"


# --------------------------------------------------------------------------------------------
# Dry-run vs apply, end to end via build_refs_report / main().
# --------------------------------------------------------------------------------------------
class TestDryRunVsApply:
    def test_dry_run_touches_nothing_byte_for_byte(self, repo):
        target = repo / "docs/project_plans/PRDs/features/foo.md"
        _write(target, _plan())
        ref_file = repo / "README.md"
        original = "See docs/project_plans/PRDs/features/foo.md.\n"
        _write(ref_file, original)

        moves = mpl.compute_moves(repo)
        mpl.build_refs_report(repo, moves, {}, include_archives=False, apply=False)

        assert target.exists()  # move phase wasn't even invoked, but confirm nothing else moved
        assert ref_file.read_text(encoding="utf-8") == original

    def test_apply_rewrites_the_ref_file_on_disk(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        ref_file = repo / "README.md"
        _write(ref_file, "See docs/project_plans/PRDs/features/foo.md.\n")

        moves = mpl.compute_moves(repo)
        mpl.build_refs_report(repo, moves, {}, include_archives=False, apply=True)

        text = ref_file.read_text(encoding="utf-8")
        assert "docs/project_plans/PRDs/foo.md" in text
        assert "docs/project_plans/PRDs/features/foo.md" not in text


# --------------------------------------------------------------------------------------------
# main() integration — CLI surface, exit codes, JSON shape.
# --------------------------------------------------------------------------------------------
class TestMainIntegration:
    def test_both_phase_dry_run_json_shape_and_exit_zero(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "README.md", "See docs/project_plans/PRDs/features/foo.md.\n")

        buf = _CaptureStdout()
        with buf:
            rc = mpl.main(["--repo-root", str(repo), "--json"])
        assert rc == 0
        payload = json.loads(buf.text)
        assert payload["mode"] == "dry-run"
        assert payload["phase"] == "both"
        assert payload["move"]["summary"]["would_move"] == 1
        assert payload["refs"]["summary"]["refs_rewritten"] == 1
        # dry-run: nothing on disk actually changed.
        assert (repo / "docs/project_plans/PRDs/features/foo.md").exists()

    def test_exit_code_2_on_collision(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "docs/project_plans/PRDs/foo.md", "already here")

        buf = _CaptureStdout()
        with buf:
            rc = mpl.main(["--repo-root", str(repo), "--json"])
        assert rc == 2
        payload = json.loads(buf.text)
        assert payload["move"]["summary"]["collisions"] == 1

    def test_exit_code_2_on_dangling_ref(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "README.md", "docs/project_plans/PRDs/features/nonexistent.md\n")

        buf = _CaptureStdout()
        with buf:
            rc = mpl.main(["--repo-root", str(repo), "--json"])
        assert rc == 2
        payload = json.loads(buf.text)
        assert payload["refs"]["summary"]["refs_dangling"] == 1

    def test_apply_with_injected_mover_moves_and_rewrites_together(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        _write(repo / "README.md", "See docs/project_plans/PRDs/features/foo.md.\n")
        calls: list[tuple[str, str]] = []

        rc = mpl.main(["--repo-root", str(repo), "--apply"], mover=_fake_mover(calls))
        assert rc == 0
        assert not (repo / "docs/project_plans/PRDs/features/foo.md").exists()
        assert (repo / "docs/project_plans/PRDs/foo.md").exists()
        assert "docs/project_plans/PRDs/foo.md" in (repo / "README.md").read_text(encoding="utf-8")
        assert calls == [("docs/project_plans/PRDs/features/foo.md", "docs/project_plans/PRDs/foo.md")]

    def test_phase_move_only_does_not_touch_refs(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        ref_file = repo / "README.md"
        original = "See docs/project_plans/PRDs/features/foo.md.\n"
        _write(ref_file, original)

        buf = _CaptureStdout()
        with buf:
            rc = mpl.main(["--repo-root", str(repo), "--phase", "move", "--json"])
        assert rc == 0
        payload = json.loads(buf.text)
        assert payload["refs"] is None
        assert ref_file.read_text(encoding="utf-8") == original

    def test_bad_repo_root_is_usage_error(self):
        rc = mpl.main(["--repo-root", "/nonexistent/path/for/sure"])
        assert rc == 1


# --------------------------------------------------------------------------------------------
# M4-L2 defect 1 — no-frontmatter file is a skip-with-reason, never an abort.
# --------------------------------------------------------------------------------------------
class TestNoFrontmatterSkip:
    def test_detect_no_frontmatter_flags_a_file_with_no_block_at_all(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/bare.md", "# No frontmatter here\n")
        moves = mpl.compute_moves(repo)
        skips = mpl.detect_no_frontmatter(repo, moves, set())
        assert len(skips) == 1
        assert skips[0]["old_rel"] == "docs/project_plans/PRDs/features/bare.md"
        assert "no YAML frontmatter" in skips[0]["reason"]

    def test_dry_run_report_detects_it_up_front(self, repo):
        # This is the exact defect: dry-run previously reported classification_would_insert=1
        # for a file it could not actually stamp — the promise apply couldn't keep.
        _write(repo / "docs/project_plans/PRDs/features/bare.md", "# No frontmatter here\n")
        _write(repo / "docs/project_plans/PRDs/features/ok.md", _plan())
        moves = mpl.compute_moves(repo)
        collisions = mpl.detect_collisions(repo, moves)
        no_fm = mpl.detect_no_frontmatter(repo, moves, {c["old_rel"] for c in collisions})
        report = mpl.build_move_report(repo, moves, collisions, no_fm, apply=False)

        assert report["summary"]["no_frontmatter_skips"] == 1
        assert report["summary"]["would_move"] == 1  # only the well-formed file
        assert report["summary"]["classification_would_insert"] == 1
        # dry-run wrote nothing.
        assert (repo / "docs/project_plans/PRDs/features/bare.md").exists()

    def test_apply_skips_the_no_frontmatter_file_and_still_moves_the_rest(self, repo):
        # Regression fixture matching the live incident: apply must NOT abort mid-run and must
        # NOT leave a half-migrated corpus — the good file moves, the bad one is left in place.
        bare_path = repo / "docs/project_plans/PRDs/features/bare.md"
        ok_path = repo / "docs/project_plans/PRDs/features/ok.md"
        _write(bare_path, "# No frontmatter here\n")
        _write(ok_path, _plan())
        calls: list[tuple[str, str]] = []

        rc = mpl.main(["--repo-root", str(repo), "--apply", "--json"], mover=_fake_mover(calls))

        assert rc == 0  # a no-frontmatter skip is an expected outcome, never a failure exit
        assert bare_path.exists()  # left untouched, not moved, not half-stamped
        assert not ok_path.exists()
        assert (repo / "docs/project_plans/PRDs/ok.md").exists()
        assert calls == [("docs/project_plans/PRDs/features/ok.md", "docs/project_plans/PRDs/ok.md")]

    def test_rerun_after_partial_apply_converges_not_compounds(self, repo):
        # Idempotency: running apply twice over the same fixture produces the same end state and
        # never re-reports the already-moved file or re-attempts the excluded one differently.
        _write(repo / "docs/project_plans/PRDs/features/bare.md", "# No frontmatter here\n")
        _write(repo / "docs/project_plans/PRDs/features/ok.md", _plan())
        calls: list[tuple[str, str]] = []
        mpl.main(["--repo-root", str(repo), "--apply", "--json"], mover=_fake_mover(calls))

        calls2: list[tuple[str, str]] = []
        rc2 = mpl.main(["--repo-root", str(repo), "--apply", "--json"], mover=_fake_mover(calls2))

        assert rc2 == 0
        assert calls2 == []  # nothing left to move — already converged
        assert (repo / "docs/project_plans/PRDs/features/bare.md").exists()
        assert (repo / "docs/project_plans/PRDs/ok.md").exists()


# --------------------------------------------------------------------------------------------
# M4-L2 defect 2 — refs phase is independent of move phase / order / repetition.
# --------------------------------------------------------------------------------------------
class TestRefsPhaseIndependence:
    def test_refs_after_move_already_applied_still_rewrites(self, repo):
        # The exact failure mode: run move --apply, then refs --apply in a SEPARATE invocation.
        # Previously this reported refs_dangling instead of rewriting, because dangling was
        # decided by testing the OLD path's on-disk existence (already false, post-move).
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        ref_file = repo / "README.md"
        _write(ref_file, "See docs/project_plans/PRDs/features/foo.md.\n")

        rc_move = mpl.main(["--repo-root", str(repo), "--phase", "move", "--apply"],
                            mover=_fake_mover([]))
        assert rc_move == 0
        assert not (repo / "docs/project_plans/PRDs/features/foo.md").exists()
        assert (repo / "docs/project_plans/PRDs/foo.md").exists()

        buf = _CaptureStdout()
        with buf:
            rc_refs = mpl.main(["--repo-root", str(repo), "--phase", "refs", "--apply", "--json"])
        assert rc_refs == 0
        payload = json.loads(buf.text)
        assert payload["refs"]["summary"]["refs_rewritten"] == 1
        assert payload["refs"]["summary"]["refs_dangling"] == 0
        assert "docs/project_plans/PRDs/foo.md" in ref_file.read_text(encoding="utf-8")

    def test_refs_before_move_and_refs_after_move_agree(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        ref_file = repo / "README.md"
        _write(ref_file, "See docs/project_plans/PRDs/features/foo.md.\n")
        moves = mpl.compute_moves(repo)

        before = mpl.build_refs_report(repo, moves, {}, include_archives=False, apply=False)
        assert before["summary"]["refs_rewritten"] == 1
        assert before["summary"]["refs_dangling"] == 0

        mpl.apply_moves(repo, moves, set(), mover=_fake_mover([]))
        after = mpl.build_refs_report(repo, moves, {}, include_archives=False, apply=False)
        assert after["summary"]["refs_rewritten"] == 1
        assert after["summary"]["refs_dangling"] == 0

    def test_refs_run_twice_in_a_row_is_idempotent(self, repo):
        _write(repo / "docs/project_plans/PRDs/features/foo.md", _plan())
        ref_file = repo / "README.md"
        _write(ref_file, "See docs/project_plans/PRDs/features/foo.md.\n")

        mpl.main(["--repo-root", str(repo), "--apply"], mover=_fake_mover([]))
        text_after_first = ref_file.read_text(encoding="utf-8")

        rc = mpl.main(["--repo-root", str(repo), "--phase", "refs", "--apply"])
        assert rc == 0
        assert ref_file.read_text(encoding="utf-8") == text_after_first

    def test_ref_to_a_file_excluded_by_no_frontmatter_skip_is_left_alone_not_dangling(self, repo):
        # The file never moves (no frontmatter) — a ref to it must stay valid at its unchanged
        # location, never be marked dangling and never be rewritten to a target that won't exist.
        _write(repo / "docs/project_plans/PRDs/features/bare.md", "# No frontmatter here\n")
        ref_file = repo / "README.md"
        _write(ref_file, "See docs/project_plans/PRDs/features/bare.md.\n")

        buf = _CaptureStdout()
        with buf:
            rc = mpl.main(["--repo-root", str(repo), "--apply", "--json"], mover=_fake_mover([]))
        assert rc == 0
        payload = json.loads(buf.text)
        assert payload["refs"]["summary"]["refs_dangling"] == 0
        assert payload["refs"]["summary"]["refs_rewritten"] == 0
        assert payload["refs"]["summary"]["refs_skipped"] == 1
        assert "docs/project_plans/PRDs/features/bare.md" in ref_file.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------
# M4-L2 defect 3 — a moved file's own outbound relative links.
# --------------------------------------------------------------------------------------------
class TestOwnRelativeLinkRepair:
    def test_link_broken_by_the_move_is_repaired_by_stripping_one_leading_dotdot(self, repo):
        # Matches the real corpus example: PRDs/features/x.md -> ../../design-specs/y.md is
        # correct from PRDs/features/; after the move to PRDs/x.md it must become ../design-specs/y.md.
        _write(repo / "docs/project_plans/design-specs/y.md", "# target\n")
        moved = repo / "docs/project_plans/PRDs/features/x.md"
        _write(moved, _plan() + "\nSee [ref](../../design-specs/y.md).\n")

        moves = mpl.compute_moves(repo)
        applied, _conflicts, link_summary, detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover([]))

        assert len(applied) == 1
        new_path = repo / "docs/project_plans/PRDs/x.md"
        text = new_path.read_text(encoding="utf-8")
        assert "](../design-specs/y.md)" in text
        assert "](../../design-specs/y.md)" not in text
        assert link_summary["rewritten"] == 1
        assert detail[0]["action"] == "rewritten"

    def test_link_that_still_resolves_from_new_location_is_left_untouched(self, repo):
        # A link that already resolves correctly from the file's NEW location (three levels up
        # from docs/project_plans/PRDs/ lands at the repo root) must not be touched.
        _write(repo / "design-specs/y.md", "# target\n")
        moved = repo / "docs/project_plans/PRDs/features/x.md"
        _write(moved, _plan() + "\nSee [ref](../../../design-specs/y.md).\n")

        moves = mpl.compute_moves(repo)
        applied, _conflicts, link_summary, _detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover([]))

        assert len(applied) == 1
        new_path = repo / "docs/project_plans/PRDs/x.md"
        text = new_path.read_text(encoding="utf-8")
        assert "](../../../design-specs/y.md)" in text
        assert link_summary["already_fine"] == 1
        assert link_summary["rewritten"] == 0

    def test_link_broken_before_and_after_the_move_is_skipped_not_guessed(self, repo):
        moved = repo / "docs/project_plans/PRDs/features/x.md"
        _write(moved, _plan() + "\nSee [ref](../../nowhere/y.md).\n")

        moves = mpl.compute_moves(repo)
        applied, _conflicts, link_summary, detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover([]))

        assert len(applied) == 1
        new_path = repo / "docs/project_plans/PRDs/x.md"
        text = new_path.read_text(encoding="utf-8")
        assert "](../../nowhere/y.md)" in text  # byte-identical — never guessed
        assert link_summary["skipped"] == 1
        assert detail[-1]["action"] == "skip"

    def test_dry_run_previews_the_same_link_fix_counts_apply_would_make(self, repo):
        _write(repo / "docs/project_plans/design-specs/y.md", "# target\n")
        moved = repo / "docs/project_plans/PRDs/features/x.md"
        _write(moved, _plan() + "\nSee [ref](../../design-specs/y.md).\n")

        moves = mpl.compute_moves(repo)
        collisions = mpl.detect_collisions(repo, moves)
        no_fm = mpl.detect_no_frontmatter(repo, moves, set())
        report = mpl.build_move_report(repo, moves, collisions, no_fm, apply=False)

        assert report["summary"]["own_links_rewritten"] == 1
        # dry-run touches nothing on disk.
        assert moved.exists()
        assert "../../design-specs/y.md" in moved.read_text(encoding="utf-8")

    def test_link_to_a_sibling_also_being_moved_is_already_fine_not_a_false_skip(self, repo):
        # Real-corpus shape: a nested phase file links to its own top-level plan file in the
        # SAME classification dir. Both rise by the identical one segment, so their relative
        # path to each other never changes — checking live disk state alone would misreport this
        # as broken purely because the sibling move hasn't been *applied* yet at check time.
        _write(
            repo / "docs/project_plans/implementation_plans/features/foo-plan.md",
            _plan(),
        )
        nested = repo / "docs/project_plans/implementation_plans/features/foo/phase-1.md"
        _write(nested, _plan() + "\nSee [ref](../foo-plan.md).\n")

        moves = mpl.compute_moves(repo)
        applied, _conflicts, link_summary, detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover([]))

        assert len(applied) == 2
        new_nested = repo / "docs/project_plans/implementation_plans/foo/phase-1.md"
        text = new_nested.read_text(encoding="utf-8")
        assert "](../foo-plan.md)" in text  # unchanged — still correct post-move
        nested_entries = [d for d in detail if d["path"].endswith("foo/phase-1.md")]
        assert nested_entries[0]["action"] == "already-fine"
        assert link_summary["skipped"] == 0

    def test_dry_run_also_recognizes_the_sibling_case(self, repo):
        _write(
            repo / "docs/project_plans/implementation_plans/features/foo-plan.md",
            _plan(),
        )
        nested = repo / "docs/project_plans/implementation_plans/features/foo/phase-1.md"
        _write(nested, _plan() + "\nSee [ref](../foo-plan.md).\n")

        moves = mpl.compute_moves(repo)
        collisions = mpl.detect_collisions(repo, moves)
        no_fm = mpl.detect_no_frontmatter(repo, moves, set())
        report = mpl.build_move_report(repo, moves, collisions, no_fm, apply=False)

        assert report["summary"]["own_links_skipped"] == 0
        assert report["summary"]["own_links_already_fine"] == 1

    def test_nested_subdir_file_link_is_also_repaired(self, repo):
        _write(repo / "docs/project_plans/design-specs/y.md", "# target\n")
        moved = repo / "docs/project_plans/implementation_plans/features/op-story-pipeline-v1/phase-3.md"
        _write(moved, _plan() + "\nSee [ref](../../../design-specs/y.md).\n")

        moves = mpl.compute_moves(repo)
        applied, _conflicts, link_summary, _detail = mpl.apply_moves(repo, moves, set(), mover=_fake_mover([]))

        assert len(applied) == 1
        new_path = repo / "docs/project_plans/implementation_plans/op-story-pipeline-v1/phase-3.md"
        text = new_path.read_text(encoding="utf-8")
        assert "](../../design-specs/y.md)" in text
        assert link_summary["rewritten"] == 1
