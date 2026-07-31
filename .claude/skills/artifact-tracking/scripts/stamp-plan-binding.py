#!/usr/bin/env python3
"""File-side plan-binding stamper — Shipped Work Ledger M2, gap-3 (the mirror of gap-1/gap-2).

Gap-1/gap-2 (``stamp-node-slug.py``) stamp the NODE side of the join: ``meta.feature_slug`` (+
``meta.plan_ref``) onto an IntentTree node. This script writes the FILE side back — ``itt_node_id``
+ ``intenttree_tree`` into the plan file's own frontmatter — so the round trip closes in both
directions for features whose node was created BY HAND (no sync binding, so nothing ever ran
``itt sync import`` for them in the first place).

**This is deliberately NOT a duplicate of the upstream ``itt sync import --stamp-frontmatter``
flag** (``../intenttree``, `frontmatter_stamp.py`, landed commit ``a058b91``) — that flag only
fires during a sync import run, so it can never reach a hand-created node that was never imported.
Every one of this repo's 32 hand-created ``completed`` nodes falls in exactly that gap. Do not
delete this script as a "redundant" reimplementation of the upstream feature; it is the launchpad-
side companion that covers the case the upstream flag structurally cannot.

WHICH NODE GETS WRITTEN — the feature-level node
-------------------------------------------------
For each ``feature_slug`` that is LIVE on at least one node in the tree (i.e. already stamped by
``stamp-node-slug.py``, via any resolution path), every node carrying that slug is a candidate;
this script picks the single **highest** one to bind the plan file to — the one closest to the
``pillar`` end of the hierarchy (``pillar`` > ``work_area`` > ``work_package`` > ``atomic_task`` >
``step``; an unrecognized/missing ``type`` ranks last). Ties (same type, more than one node) are
broken deterministically by ascending node id — never "whichever the API happened to return
first".

WHICH FILE GETS WRITTEN — the primary plan file
-------------------------------------------------
Same preference as ``stamp-node-slug.py``'s ``meta.plan_ref`` backfill (gap-2), reused verbatim
from ``_slug_resolution.select_primary_plan_file``: ``doc_type: implementation_plan`` > ``prd`` >
deterministic lexicographic tie-break on the repo-relative path.

WRITE SAFETY
------------
- **Additive and format-preserving.** Follows ``.claude/skills/planning/scripts/
  enrich_frontmatter.py``'s discipline: only ``itt_node_id``/``intenttree_tree`` keys that are
  ABSENT from the file's frontmatter are inserted, as plain text just before the closing ``---``
  delimiter (``_slug_resolution.frontmatter_insertion_point``) — no YAML re-serialize, so every
  other byte of the file (including unrelated frontmatter formatting, comments, quoting) is left
  untouched.
- **Never overwrites a conflicting value.** If the primary file already carries an ``itt_node_id``
  or ``intenttree_tree`` that DIFFERS from what this run resolves, that field is flagged as a
  conflict and the file is left untouched entirely for that slug (never a partial write).
- **Idempotent.** A slug whose primary file already carries both correct values contributes 0
  writes on a re-run (``already_correct``).
- **Dry-run by default.** Pass ``--apply`` to write.

Exit codes (mirrors ``stamp-node-slug.py``'s convention):
    0 — clean: no conflicts (an ``unresolvable`` slug — no corpus plan file at all for a slug that
        only ever came from the sync-bindings table — is expected and reported, but not fatal).
    2 — one or more conflicts.
    1 — usage / internal error (bad path, ``itt`` unreachable, unparsable response).

Python 3.10+ floor (must run on the node's 3.11 — no 3.12-only syntax).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _itt_client as itc  # noqa: E402
import _slug_resolution as sr  # noqa: E402

# Highest (pillar) to lowest (step); unrecognized/missing type ranks last.
_TYPE_RANK = {"pillar": 0, "work_area": 1, "work_package": 2, "atomic_task": 3, "step": 4}


def _node_rank(node: dict) -> tuple[int, str]:
    # A node with a missing/None/unrecognized type ranks last rather than raising.
    node_type = node.get("type")
    rank = _TYPE_RANK.get(node_type, 99) if isinstance(node_type, str) else 99
    return (rank, node["id"])


def pick_feature_nodes(nodes: dict[str, dict]) -> dict[str, str]:
    """Return ``{feature_slug: chosen_node_id}`` — the single highest node per live slug."""
    by_slug: dict[str, list[dict]] = {}
    for node in nodes.values():
        slug = (node.get("meta") or {}).get("feature_slug")
        if slug:
            by_slug.setdefault(slug, []).append(node)
    return {slug: min(candidate_nodes, key=_node_rank)["id"] for slug, candidate_nodes in by_slug.items()}


def gather(
    client: itc.IttClient, tree_id: str, plan_root: Path, repo_root: Path
) -> tuple[dict[str, str], dict[str, list[sr.PlanFile]]]:
    """Read-only: fetch the tree graph + scan the plan corpus. No writes."""
    graph = client.tree_graph(tree_id)
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    chosen = pick_feature_nodes(nodes)
    plan_files = sr.scan_plan_files(plan_root, repo_root)
    slug_index = sr.build_corpus_slug_index(plan_files)
    return chosen, slug_index


def classify(
    chosen: dict[str, str], slug_index: dict[str, list[sr.PlanFile]], tree_id: str
) -> tuple[list[tuple[str, str, sr.PlanFile, dict[str, str]]], list[str], list[dict], list[dict]]:
    """Split every live slug into (would_stamp, already_correct, conflicts, unresolvable).

    ``would_stamp`` entries carry only the ADDITIONS actually needed (a slug whose primary file
    already has a correct ``itt_node_id`` but is missing ``intenttree_tree`` gets just that one
    key queued — never a spurious rewrite of an already-correct key).
    """
    would_stamp: list[tuple[str, str, sr.PlanFile, dict[str, str]]] = []
    already_correct: list[str] = []
    conflicts: list[dict] = []
    unresolvable: list[dict] = []

    for slug, node_id in sorted(chosen.items()):
        files = slug_index.get(slug)
        if not files:
            unresolvable.append({
                "slug": slug, "node_id": node_id,
                "reason": "no plan file in the corpus carries this feature_slug",
            })
            continue

        primary = sr.select_primary_plan_file(files, slug)
        node_conflict = bool(primary.itt_node_id) and primary.itt_node_id != node_id
        tree_conflict = bool(primary.intenttree_tree) and primary.intenttree_tree != tree_id
        if node_conflict or tree_conflict:
            conflicts.append({
                "slug": slug,
                "node_id": node_id,
                "plan_ref": primary.rel_path,
                "existing_itt_node_id": primary.itt_node_id,
                "resolved_itt_node_id": node_id,
                "existing_intenttree_tree": primary.intenttree_tree,
                "resolved_intenttree_tree": tree_id,
                "detail": (
                    f"{primary.rel_path} already carries "
                    f"itt_node_id={primary.itt_node_id!r}/intenttree_tree={primary.intenttree_tree!r}; "
                    f"this run resolved node_id={node_id!r}/tree={tree_id!r} for feature_slug={slug!r} "
                    "— never overwritten"
                ),
            })
            continue

        additions: dict[str, str] = {}
        if not primary.itt_node_id:
            additions["itt_node_id"] = node_id
        if not primary.intenttree_tree:
            additions["intenttree_tree"] = tree_id

        if not additions:
            already_correct.append(slug)
        else:
            would_stamp.append((slug, node_id, primary, additions))

    return would_stamp, already_correct, conflicts, unresolvable


def apply_binding(path: Path, additions: dict[str, str]) -> None:
    """Insert *additions* as plain top-level scalar lines, format-preservingly.

    Mirrors ``enrich_frontmatter.py.apply_additions`` — textual insert just before the closing
    ``---``, never a full re-dump of the existing frontmatter/body.
    """
    text = path.read_text(encoding="utf-8")
    end = sr.frontmatter_insertion_point(text)
    if end is None:
        raise ValueError(f"{path} has no YAML frontmatter block to stamp into")
    snippet = "\n".join(f"{key}: {value}" for key, value in additions.items())
    path.write_text(text[:end] + "\n" + snippet + text[end:], encoding="utf-8")


def apply_stamps(
    would_stamp: list[tuple[str, str, sr.PlanFile, dict[str, str]]]
) -> list[str]:
    """Write every queued addition. Returns the list of slugs actually written."""
    applied: list[str] = []
    for slug, _node_id, primary, additions in would_stamp:
        apply_binding(primary.path, additions)
        applied.append(slug)
    return applied


def main(argv: list[str] | None = None, client: itc.IttClient | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Stamp itt_node_id + intenttree_tree into a feature's primary plan file — "
                    "Shipped Work Ledger M2 gap-3 (file-side companion to the node-side stamper). "
                    "Dry-run by default; --apply to commit."
    )
    ap.add_argument("--tree", required=True, help="tree id whose live feature_slug stamps to bind")
    ap.add_argument("--plan-root", default="docs/project_plans",
                     help="root to scan for plan files (default: docs/project_plans)")
    ap.add_argument("--repo-root", default=".",
                     help="repo root; plan files are resolved relative to this")
    ap.add_argument("--apply", action="store_true", help="write stamps (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    plan_root_arg = Path(args.plan_root)
    plan_root = plan_root_arg if plan_root_arg.is_absolute() else repo_root / plan_root_arg
    if not plan_root.exists():
        sys.stderr.write(f"error: plan root not found: {plan_root}\n")
        return 1

    client = client or itc.IttClient()
    try:
        chosen, slug_index = gather(client, args.tree, plan_root, repo_root)
    except itc.IttError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    would_stamp, already_correct, conflicts, unresolvable = classify(chosen, slug_index, args.tree)

    applied: list[str] = []
    if args.apply:
        try:
            applied = apply_stamps(would_stamp)
        except (OSError, ValueError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1

    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "live_feature_slugs": len(chosen),
        "would_stamp": len(would_stamp),
        "already_correct": len(already_correct),
        "conflicts": len(conflicts),
        "unresolvable": len(unresolvable),
        "applied": len(applied),
    }

    if args.json:
        print(json.dumps({
            "tree": args.tree,
            "summary": summary,
            "would_stamp": [
                {
                    "slug": slug,
                    "node_id": node_id,
                    "plan_ref": primary.rel_path,
                    "additions": additions,
                    "applied": slug in applied,
                }
                for slug, node_id, primary, additions in would_stamp
            ],
            "conflicts": conflicts,
            "unresolvable": unresolvable,
        }, indent=2))
    else:
        verb = "APPLY" if args.apply else "DRY-RUN"
        print(f"[stamp-plan-binding] {verb} tree={args.tree} plan_root={plan_root}")
        for slug, node_id, primary, additions in would_stamp:
            tag = "STAMPED" if slug in applied else "would-stamp"
            print(f"  {slug}\n    node_id={node_id!r} plan_ref={primary.rel_path!r} "
                  f"additions={additions}  [{tag}]")
        for c in conflicts:
            print(f"  CONFLICT {c['detail']}")
        for u in unresolvable:
            print(f"  UNRESOLVABLE slug={u['slug']!r} node={u['node_id']} — {u['reason']}")
        print("\n  summary:")
        for k, v in summary.items():
            print(f"    {k}={v}")

    return 2 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
