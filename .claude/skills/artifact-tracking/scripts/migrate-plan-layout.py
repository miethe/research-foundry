#!/usr/bin/env python3
"""Plan-layout migration — Shipped Work Ledger M4 L2 (FR-13). HIGHEST BLAST RADIUS in the program.

``docs/project_plans/{PRDs,implementation_plans,feature_contracts}`` currently carry a
``<classification>`` sublayer (``features``/``enhancements``/``infrastructure``) between the type
dir and the actual files (D-M4-3: ``feature_contracts`` is in scope even though FR-13 names only
the first two — see the leg contract §3). This script:

  **move**  — drops exactly ONE path segment per file (D-M4-2): ``<type>/<classification>/<rest>``
              -> ``<type>/<rest>``. Anything below the classification segment (nested feature
              phase-subdirs) is preserved verbatim — this is NOT a flatten. Uses ``git mv`` so
              history follows, and inserts ``classification: <old-sublayer>`` into the moved
              file's frontmatter, additively and format-preservingly (D-M4-5) — reuses
              ``_slug_resolution.frontmatter_insertion_point`` rather than re-implementing the
              bounds scan (mirrors ``stamp-plan-binding.py``'s ``apply_binding``). A file with NO
              frontmatter block at all is a **skip-with-reason** (M4-L2 defect 1), never an abort —
              stamping requires a block to insert into, and inventing one from scratch would invent
              fields beyond ``classification:``, which conventions 1/3 forbid. The dry-run detects
              and reports this up front, so its promised counts are ones apply can actually deliver.
              As part of the same move, each file's own outbound ``](../…)`` links are checked and,
              where the rise-by-one-level move broke them, repaired (M4-L2 defect 3) — see
              :func:`rewrite_own_relative_links`.

  **refs**  — rewrites every cross-reference to a moved file, repo-wide, by the SAME one-segment
              rule. **Gated on repo ownership of the path, matched against the known moved-file
              set — never a blind regex.** ~11-14 of the ~981 corpus refs point at OTHER REPOS'
              plan corpora (``../intenttree/``, ``skillmeat/``, ``research-foundry/``,
              ``meatycapture/``); rewriting those breaks a working link (the exact M3-F1 failure
              shape — a plausible transform applied where it does not belong). Every candidate ref
              is classified into exactly one of: rewrite / skip (other-repo, unrecognized prefix,
              excluded-from-the-move, or no-such-classification-for-this-type) / dangling
              (this-repo prefix, in-scope type+classification, but the referenced file resolves at
              NEITHER its pre-move nor its post-move path — a pre-existing broken link, unrelated
              to this migration, surfaced per the "shape-valid != real" discipline). A skip is a
              first-class report entry, never a silent drop.

              A ref is resolved against the old->new **mapping**, never against on-disk existence
              of the old path alone (M4-L2 defect 2) — it is valid, and rewritten, if it resolves at
              EITHER the pre-move or the post-move path. This makes ``--phase refs`` correct
              whether run before the move, after it, or twice in a row: the "already moved away"
              case is caught by checking the post-move target directly, independent of whatever
              ``compute_moves`` finds by re-scanning the (possibly now-drained) classification
              directories in this particular invocation.

Both phases share ONE ground-truth move list (:func:`compute_moves`, built by scanning the six
``<type>/<classification>`` directories once) — the refs phase validates a ref's target against
that SAME list (plus the post-move-path fallback above), so there is exactly one place that
decides "which files are moving, and which of those are actually going to be touched."

SAFETY (leg contract §4, conventions 1-3, 5)
---------------------------------------------
- Dry-run is the default. ``--apply`` is opt-in and required to write ANYTHING (file moves,
  frontmatter inserts, own-link rewrites, ref rewrites).
- Additive/format-preserving frontmatter writes only — a file that already carries a
  ``classification:`` key (none do today, per the leg contract's measured ground truth) is left
  untouched and reported, never overwritten.
- A file with no frontmatter block at all is skipped and reported (never moved, never stamped,
  never the reason a whole run aborts) — see defect 1 above.
- Refuses to move a file onto an existing path (asserted via :func:`detect_collisions`, not
  trusted to be zero just because it measured zero once) — collisions are reported and that file
  is excluded from ``--apply``, never silently overwritten.
- Every skip/dangling ref is reported with a reason; nothing is guessed.
- Archive dirs (D-M4-4: ``docs/enablement/`` — the frozen v4.1 hand-off pack — and
  ``docs/intenttree-live-seed/`` — a captured seed snapshot) are excluded from the ref rewrite by
  default; ``--include-archives`` overrides. The excluded file COUNT is always reported, never
  silently dropped from the output.
- Re-running after a partial run converges rather than compounding: already-moved files are no
  longer found by ``compute_moves`` (rescans current disk state), an already-present
  ``classification:`` key is never re-inserted, and a file excluded on one run (collision /
  no-frontmatter) is re-evaluated fresh on the next.

EXIT CODES
----------
- 0 — clean (skips/archive-exclusions/no-frontmatter-skips/dangling-free are expected outcomes,
  not failures).
- 2 — one or more move collisions, OR one or more dangling refs found.
- 1 — usage / internal error (bad ``--repo-root``, ``git mv`` failure under ``--apply``).

Python 3.10+ floor (must import on the node's 3.11 — no 3.12-only syntax). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _slug_resolution as sr  # noqa: E402 — reused for frontmatter_insertion_point

PLAN_ROOT = "docs/project_plans"
# D-M4-3: feature_contracts is in scope even though FR-13 names only the first two.
TYPE_DIRS = ("PRDs", "implementation_plans", "feature_contracts")
CLASSIFICATIONS = ("features", "enhancements", "infrastructure")
# D-M4-4: frozen/captured archives excluded from the ref rewrite by default.
ARCHIVE_DIRS = ("docs/enablement", "docs/intenttree-live-seed")
# Always pruned regardless of --include-archives: gitignored tool/build byproducts, never real
# corpus content. Left in, they make the report non-reproducible run-to-run (e.g. `.pytest_cache`
# persists a prior test run's parametrize IDs, which happen to contain literal
# "project_plans/..." substrings from THIS script's own test fixtures).
_HARD_EXCLUDE_DIR_NAMES = (".git", "__pycache__", ".pytest_cache")

# M4-L2 defect 1: a move candidate with no YAML frontmatter block at all cannot be stamped —
# skip-with-reason, never an abort mid-run.
NO_FRONTMATTER_REASON = (
    "file has no YAML frontmatter block to stamp classification into — skipped, not moved "
    "(creating a block from scratch would invent fields beyond classification:, which "
    "conventions 1/3 forbid)"
)

# The six ref-prefix forms this script recognizes as "this repo, handled" (leg contract §2/§5-L2 —
# "enumerate in your report which forms you handle"). Anything else is skip-with-reason.
PREFIX_FORMS_HANDLED = (
    "plain: docs/project_plans/...",
    "leading-slash (mid-sentence): /docs/project_plans/...",
    "repo-qualified: agentic_meta_dev/docs/project_plans/...",
    "relative-with-docs (any depth): ../docs/project_plans/..., ../../docs/project_plans/..., ...",
    "bare (no docs/ prefix): project_plans/...",
    "relative-bare (any depth): ../project_plans/..., ../../project_plans/..., ...",
)

# Other repos' plan corpora that share this filename/path shape — a match against one of these is
# a HARD skip, never a rewrite (rewriting it would break a working link in a repo not being
# migrated by this run). Substring match against the ref's prefix, so "../intenttree/docs/",
# "intenttree/docs/", and an absolute ".../intenttree/docs/" are all caught by "intenttree/".
OTHER_REPO_MARKERS = ("intenttree/", "skillmeat/", "research-foundry/", "meatycapture/")

_PREFIX_WHITELIST_RE = re.compile(
    r"^(?:docs/|/docs/|agentic_meta_dev/docs/|(?:\.\./)+docs/|(?:\.\./)+)?$"
)
_CORE_RE = re.compile(
    r"project_plans/(PRDs|implementation_plans|feature_contracts)/"
    r"(features|enhancements|infrastructure)/"
)
_PATH_CHAR_RE = re.compile(r"[A-Za-z0-9_./-]")

# M4-L2 defect 3: a moved file's own outbound relative links, of the form `](../...)`.
_OWN_LINK_RE = re.compile(r"\]\((\.\./[^)\s]*)\)")


# ------------------------------------------------------------------------------------------------
# Ground truth: the one list of files that are moving. Both phases read from this.
# ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class MoveItem:
    type_dir: str
    classification: str
    rest: str      # relative path within the classification dir — preserves nested subdirs
    old_rel: str   # e.g. "docs/project_plans/PRDs/x.md"
    new_rel: str   # e.g. "docs/project_plans/PRDs/x.md"


def compute_moves(repo_root: Path) -> list[MoveItem]:
    """Scan the six ``<type>/<classification>`` dirs that currently exist; one entry per file.

    A ``(type, classification)`` combination that isn't a real directory (e.g. there is no
    ``PRDs/enhancements`` in this corpus) simply contributes nothing — never an error. A file
    already moved away by a prior run simply isn't found here any more (that is how re-running
    converges rather than compounding); a file left in place on purpose (collision /
    no-frontmatter skip) is found here on every run, which is how those exclusions stay correct
    across repeated invocations.
    """
    moves: list[MoveItem] = []
    for type_dir in TYPE_DIRS:
        for classification in CLASSIFICATIONS:
            base = repo_root / PLAN_ROOT / type_dir / classification
            if not base.is_dir():
                continue
            for p in sorted(base.rglob("*")):
                if not p.is_file():
                    continue
                rest = p.relative_to(base).as_posix()
                moves.append(MoveItem(
                    type_dir=type_dir,
                    classification=classification,
                    rest=rest,
                    old_rel=f"{PLAN_ROOT}/{type_dir}/{classification}/{rest}",
                    new_rel=f"{PLAN_ROOT}/{type_dir}/{rest}",
                ))
    return moves


def detect_collisions(repo_root: Path, moves: list[MoveItem]) -> list[dict]:
    """Assert (never just trust) that no move lands on an existing path or another move's target."""
    collisions: list[dict] = []
    seen_new_rel: dict[str, str] = {}
    for m in moves:
        if (repo_root / m.new_rel).exists():
            collisions.append({
                "old_rel": m.old_rel, "new_rel": m.new_rel,
                "reason": "destination already exists on disk",
            })
            continue
        prior = seen_new_rel.get(m.new_rel)
        if prior is not None:
            collisions.append({
                "old_rel": m.old_rel, "new_rel": m.new_rel,
                "reason": f"destination collides with another move source: {prior}",
            })
            continue
        seen_new_rel[m.new_rel] = m.old_rel
    return collisions


def has_frontmatter(text: str) -> bool:
    return sr.frontmatter_insertion_point(text) is not None


def detect_no_frontmatter(
    repo_root: Path, moves: list[MoveItem], collision_old_rels: set[str]
) -> list[dict]:
    """Assert (never just trust) that every move candidate carries a frontmatter block to stamp
    ``classification:`` into. M4-L2 defect 1: a file with none is a skip-with-reason, found up
    front by BOTH the dry-run and apply — never discovered only when apply is already mid-run."""
    skips: list[dict] = []
    for m in moves:
        if m.old_rel in collision_old_rels:
            continue
        text = (repo_root / m.old_rel).read_text(encoding="utf-8")
        if not has_frontmatter(text):
            skips.append({"old_rel": m.old_rel, "new_rel": m.new_rel, "reason": NO_FRONTMATTER_REASON})
    return skips


# ------------------------------------------------------------------------------------------------
# Move phase — frontmatter classification stamp (additive, format-preserving; D-M4-5).
# ------------------------------------------------------------------------------------------------
def has_top_level_key(text: str, key: str) -> bool:
    end = sr.frontmatter_insertion_point(text)
    if end is None:
        return False
    first_nl = text.find("\n")
    body = text[first_nl + 1: end]
    return re.search(rf"(?m)^{re.escape(key)}:", body) is not None


def insert_classification(text: str, classification: str) -> str:
    end = sr.frontmatter_insertion_point(text)
    if end is None:
        raise ValueError("file has no YAML frontmatter block to stamp classification into")
    return text[:end] + f"\nclassification: {classification}" + text[end:]


# ------------------------------------------------------------------------------------------------
# Move phase — own outbound relative-link repair (M4-L2 defect 3).
# ------------------------------------------------------------------------------------------------
def _split_fragment(link: str) -> tuple[str, str]:
    if "#" in link:
        path_part, frag = link.split("#", 1)
        return path_part, "#" + frag
    return link, ""


def rewrite_own_relative_links(
    repo_root: Path, new_rel: str, text: str, final_new_rels: frozenset[str] = frozenset()
) -> tuple[str, list[dict]]:
    """A file that rises exactly one directory level (D-M4-2) can have its OWN outbound
    ``](../...)`` links silently change meaning. For each such link: if it still resolves from the
    file's new location, leave it (``already-fine``). Otherwise, if stripping exactly ONE leading
    ``../`` makes it resolve, rewrite it. Everything else — a link that resolves at neither, e.g.
    a pre-existing broken link — is left byte-identical and reported ``skip`` with a reason.
    Never touches anything but ``](../...)`` links; never guesses beyond one strip.

    *final_new_rels* is the full set of every move's ``new_rel`` (the batch's end state), so that a
    link to a SIBLING file that is ALSO moving (e.g. a nested phase file linking to its own
    top-level plan file in the same classification dir) is correctly recognized as still valid —
    both files rise by the identical one segment, so their relative path to each other never
    changes — even though the sibling hasn't necessarily moved on disk yet at check time (dry-run
    never moves anything; apply processes moves in list order, so a not-yet-processed sibling's
    new path doesn't exist on disk yet either). Checking disk existence ALONE would misreport
    these as broken/skip purely due to processing order, not because anything is actually wrong.
    """
    new_dir = (repo_root / new_rel).parent

    def _resolves(candidate: Path) -> bool:
        if candidate.exists():
            return True
        try:
            rel = candidate.relative_to(repo_root).as_posix()
        except ValueError:
            return False
        return rel in final_new_rels

    results: list[dict] = []

    def _sub(m: re.Match) -> str:
        link = m.group(1)
        path_part, frag = _split_fragment(link)

        if _resolves((new_dir / path_part).resolve()):
            results.append({"link": link, "action": "already-fine", "reason": None})
            return m.group(0)

        if not path_part.startswith("../"):
            results.append({
                "link": link, "action": "skip",
                "reason": "does not resolve from the new location and has no leading ../ to strip",
            })
            return m.group(0)

        stripped_path = path_part[len("../"):]
        if _resolves((new_dir / stripped_path).resolve()):
            new_link = stripped_path + frag
            results.append({"link": link, "action": "rewritten", "new": new_link, "reason": None})
            return f"]({new_link})"

        results.append({
            "link": link, "action": "skip",
            "reason": "does not resolve from the new location, with or without stripping one leading ../ "
                      "(pre-existing broken link, unrelated to this migration)",
        })
        return m.group(0)

    new_text = _OWN_LINK_RE.sub(_sub, text)
    return new_text, results


_EMPTY_LINK_FIX_SUMMARY = {"rewritten": 0, "already_fine": 0, "skipped": 0}


def _tally_link_fix(summary: dict, results: list[dict]) -> None:
    for r in results:
        if r["action"] == "rewritten":
            summary["rewritten"] += 1
        elif r["action"] == "already-fine":
            summary["already_fine"] += 1
        else:
            summary["skipped"] += 1


def _default_git_mv(repo_root: Path, old_rel: str, new_rel: str) -> None:
    dest = repo_root / new_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "mv", "--", old_rel, new_rel],
        cwd=repo_root, check=True, capture_output=True, text=True,
    )


def plan_move_effects(
    repo_root: Path, moves: list[MoveItem], excluded_old_rels: set[str]
) -> tuple[list[MoveItem], list[dict], dict, list[dict]]:
    """Dry-run view of what ``apply_moves`` would do to the same bytes: which moves would ALSO get
    a ``classification:`` insert (vs already-present), and what its own-link repair would do.
    Reads the CURRENT (pre-move) file — a plain rename doesn't change frontmatter content or link
    text, so this is a faithful preview against the post-move ``new_rel`` location.
    """
    would_insert: list[MoveItem] = []
    already_present: list[dict] = []
    link_fix_summary = dict(_EMPTY_LINK_FIX_SUMMARY)
    link_fix_detail: list[dict] = []
    final_new_rels = frozenset(m.new_rel for m in moves if m.old_rel not in excluded_old_rels)
    for m in moves:
        if m.old_rel in excluded_old_rels:
            continue
        text = (repo_root / m.old_rel).read_text(encoding="utf-8")
        if has_top_level_key(text, "classification"):
            already_present.append({"path": m.new_rel, "detail": "already carries a classification key — not overwritten"})
        else:
            would_insert.append(m)

        _, link_results = rewrite_own_relative_links(repo_root, m.new_rel, text, final_new_rels)
        _tally_link_fix(link_fix_summary, link_results)
        for r in link_results:
            link_fix_detail.append({"path": m.new_rel, **r})
    return would_insert, already_present, link_fix_summary, link_fix_detail


def apply_moves(
    repo_root: Path,
    moves: list[MoveItem],
    excluded_old_rels: set[str],
    mover: Callable[[Path, str, str], None] | None = None,
) -> tuple[list[dict], list[dict], dict, list[dict]]:
    """Perform the actual ``git mv`` + additive classification stamp + own-link repair. Never
    touches a file excluded for a collision or a missing-frontmatter skip (M4-L2 defect 1)."""
    mover = mover or _default_git_mv
    applied: list[dict] = []
    classification_conflicts: list[dict] = []
    link_fix_summary = dict(_EMPTY_LINK_FIX_SUMMARY)
    link_fix_detail: list[dict] = []
    final_new_rels = frozenset(mv.new_rel for mv in moves if mv.old_rel not in excluded_old_rels)
    for m in moves:
        if m.old_rel in excluded_old_rels:
            continue
        mover(repo_root, m.old_rel, m.new_rel)
        dest = repo_root / m.new_rel
        text = dest.read_text(encoding="utf-8")

        text, link_results = rewrite_own_relative_links(repo_root, m.new_rel, text, final_new_rels)
        _tally_link_fix(link_fix_summary, link_results)
        for r in link_results:
            link_fix_detail.append({"path": m.new_rel, **r})

        if has_top_level_key(text, "classification"):
            classification_conflicts.append({"path": m.new_rel, "detail": "already carries a classification key — not overwritten"})
        else:
            text = insert_classification(text, m.classification)
        dest.write_text(text, encoding="utf-8")
        applied.append({"old_rel": m.old_rel, "new_rel": m.new_rel, "classification": m.classification})
    return applied, classification_conflicts, link_fix_summary, link_fix_detail


def build_move_report(
    repo_root: Path,
    moves: list[MoveItem],
    collisions: list[dict],
    no_frontmatter_skips: list[dict],
    apply: bool,
    mover: Callable[[Path, str, str], None] | None = None,
) -> dict:
    collision_old_rels = {c["old_rel"] for c in collisions}
    no_frontmatter_old_rels = {n["old_rel"] for n in no_frontmatter_skips}
    excluded_old_rels = collision_old_rels | no_frontmatter_old_rels

    if apply:
        applied, classification_conflicts, link_fix_summary, link_fix_detail = apply_moves(
            repo_root, moves, excluded_old_rels, mover=mover
        )
        would_insert_count = len(applied) - len(classification_conflicts)
    else:
        would_insert, classification_conflicts, link_fix_summary, link_fix_detail = plan_move_effects(
            repo_root, moves, excluded_old_rels
        )
        would_insert_count = len(would_insert)

    movable = [m for m in moves if m.old_rel not in excluded_old_rels]
    return {
        "mode": "apply" if apply else "dry-run",
        "total_candidates": len(moves),
        "would_move" if not apply else "moved": [
            {"old_rel": m.old_rel, "new_rel": m.new_rel, "classification": m.classification}
            for m in movable
        ],
        "collisions": collisions,
        "no_frontmatter_skips": no_frontmatter_skips,
        "classification_conflicts": classification_conflicts,
        "own_link_fixes": link_fix_detail,
        "summary": {
            "total_candidates": len(moves),
            "moved" if apply else "would_move": len(movable),
            "collisions": len(collisions),
            "no_frontmatter_skips": len(no_frontmatter_skips),
            "classification_inserted" if apply else "classification_would_insert": would_insert_count,
            "classification_conflicts": len(classification_conflicts),
            "own_links_rewritten": link_fix_summary["rewritten"],
            "own_links_already_fine": link_fix_summary["already_fine"],
            "own_links_skipped": link_fix_summary["skipped"],
        },
    }


# ------------------------------------------------------------------------------------------------
# Refs phase.
# ------------------------------------------------------------------------------------------------
def _scan_prefix(text: str, pos: int) -> str:
    i = pos
    while i > 0 and _PATH_CHAR_RE.match(text[i - 1]):
        i -= 1
    return text[i:pos]


def _scan_rest(text: str, pos: int) -> str:
    j = pos
    while j < len(text) and _PATH_CHAR_RE.match(text[j]):
        j += 1
    # A trailing '.' is virtually always sentence punctuation ("...at foo.md."), never part of the
    # filename itself (nothing in this corpus ends with a literal dot) — trim it back out so it
    # isn't swallowed into `rest` and mistaken for a nonexistent file (a false "dangling").
    while j > pos and text[j - 1] == ".":
        j -= 1
    return text[pos:j]


def find_ref_occurrences(text: str) -> list[dict]:
    """Every ``project_plans/<type>/<classification>/<rest>`` occurrence in *text*, with its
    surrounding prefix/rest captured by scanning path-safe characters outward from the literal
    match — never a blind whole-line or whole-file regex over "anything path-ish."""
    occurrences: list[dict] = []
    for m in _CORE_RE.finditer(text):
        prefix = _scan_prefix(text, m.start())
        rest = _scan_rest(text, m.end())
        occurrences.append({
            "start": m.start() - len(prefix),
            "end": m.end() + len(rest),
            "prefix": prefix,
            "type_dir": m.group(1),
            "classification": m.group(2),
            "rest": rest,
        })
    return occurrences


def classify_occurrence(
    repo_root: Path,
    moves_by_key: dict[tuple[str, str, str], MoveItem],
    excluded_old_rels: dict[str, str],
    occ: dict,
) -> tuple[str, str | None]:
    """Return ``(action, reason)`` — action in {"rewrite", "skip", "dangling"}. Fail-closed:
    anything not confidently a this-repo, in-scope, on-disk-resolvable target is skip/dangling,
    never rewrite.

    M4-L2 defect 2: resolved against the old->new **mapping**, not against on-disk existence of
    the old path alone — a ref is valid (and rewritten) if it resolves at EITHER the pre-move path
    (``key in moves_by_key`` — the file is still there, about to move) OR the post-move path
    (checked directly against disk — the file already moved there, in this invocation or a prior
    one). That makes the result the same whether refs runs before the move, after it, or twice in
    a row.
    """
    prefix = occ["prefix"]
    for marker in OTHER_REPO_MARKERS:
        if marker in prefix:
            return "skip", (
                f"ref points at another repo's plan corpus ({marker.rstrip('/')}) "
                "— not migrated by this run, rewriting it would break a working link"
            )
    if not _PREFIX_WHITELIST_RE.fullmatch(prefix):
        return "skip", f"unrecognized ref prefix form: {prefix!r}"

    type_dir, classification, rest = occ["type_dir"], occ["classification"], occ["rest"]
    old_rel = f"{PLAN_ROOT}/{type_dir}/{classification}/{rest}"
    new_rel = f"{PLAN_ROOT}/{type_dir}/{rest}"

    if old_rel in excluded_old_rels:
        return "skip", (
            f"file at {old_rel} is excluded from the move ({excluded_old_rels[old_rel]}) — "
            "ref left pointing at its unchanged location"
        )

    key = (type_dir, classification, rest)
    if key in moves_by_key or (repo_root / new_rel).exists():
        return "rewrite", None

    base_dir = repo_root / PLAN_ROOT / type_dir / classification
    if not base_dir.is_dir():
        return "skip", (
            f"no {PLAN_ROOT}/{type_dir}/{classification} directory exists in "
            "this repo — never a valid combination, so never a moved file"
        )
    return "dangling", (
        f"referenced file does not exist on disk at either its pre-move or post-move path: "
        f"{old_rel} (pre-existing broken reference, unrelated to this migration)"
    )


def rewrite_file_text(text: str, annotated: list[dict]) -> tuple[str, list[dict]]:
    """Apply every "rewrite" occurrence's new text; leave skip/dangling occurrences byte-identical."""
    ordered = sorted(annotated, key=lambda o: o["start"])
    out: list[str] = []
    cursor = 0
    applied: list[dict] = []
    for occ in ordered:
        if occ["action"] != "rewrite":
            continue
        out.append(text[cursor:occ["start"]])
        out.append(occ["new_text"])
        applied.append({"old": occ["old_text"], "new": occ["new_text"]})
        cursor = occ["end"]
    out.append(text[cursor:])
    return "".join(out), applied


def process_ref_file(
    repo_root: Path,
    path: Path,
    moves_by_key: dict[tuple[str, str, str], MoveItem],
    excluded_old_rels: dict[str, str],
    apply: bool,
) -> dict | None:
    rel = path.relative_to(repo_root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # binary/unreadable — nothing to scan, not an error

    occs = find_ref_occurrences(text)
    if not occs:
        return None

    annotated: list[dict] = []
    for occ in occs:
        action, reason = classify_occurrence(repo_root, moves_by_key, excluded_old_rels, occ)
        occ["action"] = action
        occ["reason"] = reason
        occ["old_text"] = text[occ["start"]:occ["end"]]
        if action == "rewrite":
            m = moves_by_key.get((occ["type_dir"], occ["classification"], occ["rest"]))
            new_type_rest = m.rest if m is not None else occ["rest"]
            new_type_dir = m.type_dir if m is not None else occ["type_dir"]
            # NOTE: PLAN_ROOT ("docs/project_plans") is NOT used here — `prefix` already carries
            # whatever "docs/" component the original ref had (or didn't); prepending PLAN_ROOT
            # would double it into "docs/docs/project_plans/...".
            occ["new_text"] = occ["prefix"] + f"project_plans/{new_type_dir}/{new_type_rest}"
        annotated.append(occ)

    new_text, applied = rewrite_file_text(text, annotated)
    if apply and applied:
        path.write_text(new_text, encoding="utf-8")

    return {"file": rel, "occurrences": annotated, "applied": applied}


def iter_repo_files(repo_root: Path, include_archives: bool) -> tuple[list[Path], list[str]]:
    """Every regular file under *repo_root*, excluding ``.git`` (dir or worktree-gitlink file),
    other gitignored tool/build byproducts (``_HARD_EXCLUDE_DIR_NAMES``), and — unless
    *include_archives* — the D-M4-4 archive dirs. Hard-excluded dirs are pruned from the walk
    itself (not filtered after the fact) so a real (non-worktree) checkout's pack files are never
    even listed."""
    files: list[Path] = []
    excluded: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _HARD_EXCLUDE_DIR_NAMES]
        dpath = Path(dirpath)
        for fname in filenames:
            p = dpath / fname
            rel = p.relative_to(repo_root).as_posix()
            if rel == ".git":
                continue
            if not include_archives and any(rel == d or rel.startswith(d + "/") for d in ARCHIVE_DIRS):
                excluded.append(rel)
                continue
            files.append(p)
    return sorted(files), sorted(excluded)


def build_refs_report(
    repo_root: Path,
    moves: list[MoveItem],
    excluded_old_rels: dict[str, str],
    include_archives: bool,
    apply: bool,
) -> dict:
    movable = [m for m in moves if m.old_rel not in excluded_old_rels]
    moves_by_key = {(m.type_dir, m.classification, m.rest): m for m in movable}
    files, excluded_archives = iter_repo_files(repo_root, include_archives)

    per_file: list[dict] = []
    for p in files:
        result = process_ref_file(repo_root, p, moves_by_key, excluded_old_rels, apply)
        if result is not None:
            per_file.append(result)

    rewritten: list[dict] = []
    skipped: list[dict] = []
    dangling: list[dict] = []
    for pf in per_file:
        for occ in pf["occurrences"]:
            entry = {"file": pf["file"], "raw": occ["old_text"], "reason": occ["reason"]}
            if occ["action"] == "rewrite":
                rewritten.append({"file": pf["file"], "old": occ["old_text"], "new": occ["new_text"]})
            elif occ["action"] == "skip":
                skipped.append(entry)
            else:
                dangling.append(entry)

    rewritten_files = sorted({r["file"] for r in rewritten})
    return {
        "mode": "apply" if apply else "dry-run",
        "scanned_files": len(files),
        "excluded_archive_dirs": list(ARCHIVE_DIRS) if not include_archives else [],
        "excluded_archive_files": len(excluded_archives),
        "prefix_forms_handled": list(PREFIX_FORMS_HANDLED),
        "rewritten": rewritten,
        "skipped": skipped,
        "dangling": dangling,
        "summary": {
            "scanned_files": len(files),
            "excluded_archive_files": len(excluded_archives),
            "refs_rewritten": len(rewritten),
            "files_with_rewrites": len(rewritten_files),
            "refs_skipped": len(skipped),
            "refs_dangling": len(dangling),
        },
    }


# ------------------------------------------------------------------------------------------------
# Driver.
# ------------------------------------------------------------------------------------------------
def _emit_human(move_report: dict | None, refs_report: dict | None, repo_root: Path, phase: str, apply: bool) -> None:
    verb = "APPLY" if apply else "DRY-RUN"
    print(f"[migrate-plan-layout] {verb} phase={phase} repo_root={repo_root}")

    if move_report is not None:
        print("\n  -- move --")
        key = "moved" if apply else "would_move"
        for item in move_report[key]:
            print(f"    {item['old_rel']} -> {item['new_rel']}  [classification={item['classification']}]")
        for c in move_report["collisions"]:
            print(f"    COLLISION {c['old_rel']} -> {c['new_rel']}: {c['reason']}")
        for n in move_report["no_frontmatter_skips"]:
            print(f"    NO-FRONTMATTER-SKIP {n['old_rel']}: {n['reason']}")
        for cc in move_report["classification_conflicts"]:
            print(f"    CLASSIFICATION-CONFLICT {cc['path']}: {cc['detail']}")
        for lf in move_report["own_link_fixes"]:
            if lf["action"] == "rewritten":
                print(f"    OWN-LINK-REWRITE {lf['path']}: {lf['link']!r} -> {lf['new']!r}")
            elif lf["action"] == "skip":
                print(f"    OWN-LINK-SKIP {lf['path']}: {lf['link']!r} — {lf['reason']}")
        print("    summary:")
        for k, v in move_report["summary"].items():
            print(f"      {k}={v}")

    if refs_report is not None:
        print("\n  -- refs --")
        print(f"    prefix forms handled: {len(refs_report['prefix_forms_handled'])}")
        for f in refs_report["prefix_forms_handled"]:
            print(f"      - {f}")
        print(f"    archive dirs excluded ({refs_report['excluded_archive_files']} files): "
              f"{refs_report['excluded_archive_dirs']}")
        for r in refs_report["rewritten"]:
            print(f"    REWRITE {r['file']}: {r['old']!r} -> {r['new']!r}")
        for s in refs_report["skipped"]:
            print(f"    SKIP {s['file']}: {s['raw']!r} — {s['reason']}")
        for d in refs_report["dangling"]:
            print(f"    DANGLING {d['file']}: {d['raw']!r} — {d['reason']}")
        print("    summary:")
        for k, v in refs_report["summary"].items():
            print(f"      {k}={v}")


def main(argv: list[str] | None = None, mover: Callable[[Path, str, str], None] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Migrate docs/project_plans off its {features,enhancements,infrastructure} "
                    "sublayer (FR-13) — drops exactly one path segment (D-M4-2), stamps "
                    "classification: additively (D-M4-5), repairs each moved file's own broken "
                    "relative links, and rewrites every in-scope cross-reference repo-wide. "
                    "Dry-run by default; --apply to write."
    )
    ap.add_argument("--repo-root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--phase", choices=["move", "refs", "both"], default="both")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--include-archives", action="store_true",
                     help="also rewrite refs under docs/enablement/ and docs/intenttree-live-seed/ "
                          "(D-M4-4 excludes these by default)")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        sys.stderr.write(f"error: repo root not found: {repo_root}\n")
        return 1

    moves = compute_moves(repo_root)
    collisions = detect_collisions(repo_root, moves)
    no_frontmatter_skips = detect_no_frontmatter(repo_root, moves, {c["old_rel"] for c in collisions})
    excluded_old_rels: dict[str, str] = {c["old_rel"]: c["reason"] for c in collisions}
    excluded_old_rels.update({n["old_rel"]: n["reason"] for n in no_frontmatter_skips})

    move_report: dict | None = None
    refs_report: dict | None = None
    try:
        if args.phase in ("move", "both"):
            move_report = build_move_report(
                repo_root, moves, collisions, no_frontmatter_skips, apply=args.apply, mover=mover
            )
        if args.phase in ("refs", "both"):
            refs_report = build_refs_report(
                repo_root, moves, excluded_old_rels,
                include_archives=args.include_archives, apply=args.apply,
            )
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    has_collisions = bool(move_report and move_report["collisions"])
    has_dangling = bool(refs_report and refs_report["dangling"])
    exit_code = 2 if (has_collisions or has_dangling) else 0

    if args.json:
        print(json.dumps({
            "mode": "apply" if args.apply else "dry-run",
            "phase": args.phase,
            "repo_root": str(repo_root),
            "move": move_report,
            "refs": refs_report,
            "exit": exit_code,
        }, indent=2))
    else:
        _emit_human(move_report, refs_report, repo_root, args.phase, args.apply)
        print(f"\n  exit={exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
