#!/usr/bin/env python3
"""M2 acceptance-criteria checker — slug -> node -> plan file -> slug round trip.

For a tree (and optionally one ``--slug``), verifies for every node that carries
``meta.feature_slug`` that the join back to its plan file is self-consistent:

    1. the node carries ``meta.plan_ref`` (a stamped node with no plan_ref can't round-trip);
    2. that path exists on disk (relative to ``--repo-root``);
    3. the plan file's own ``feature_slug`` frontmatter matches the node's;
    4. if the plan file also carries ``itt_node_id``, it points back at THIS node.

This is a read-only checker — it never mutates a node or a file, so there is no ``--apply`` mode
(unlike ``stamp-node-slug.py``, there is nothing here to commit). Same JSON / exit-code
conventions: 0 = every checked feature round-trips clean, 2 = one or more FAIL, 1 = usage error.

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


def check_tree(
    client: itc.IttClient, tree_id: str, repo_root: Path, slug_filter: str | None = None
) -> list[dict]:
    graph = client.tree_graph(tree_id)
    nodes = graph.get("nodes", [])
    nodes_by_id = {n["id"]: n for n in nodes}
    results: list[dict] = []
    seen_slugs: set[str] = set()

    for node in nodes:
        meta = node.get("meta") or {}
        slug = meta.get("feature_slug")
        if not slug:
            continue
        if slug_filter and slug != slug_filter:
            continue
        seen_slugs.add(slug)
        node_id = node["id"]
        plan_ref = meta.get("plan_ref")

        shape_reason = sr.slug_shape_reject_reason(slug)
        if shape_reason is not None:
            results.append({
                "slug": slug, "node_id": node_id, "status": "FAIL",
                "reason": f"feature_slug is not slug-shaped: {shape_reason}",
            })
            continue

        if not plan_ref:
            results.append({
                "slug": slug, "node_id": node_id, "status": "FAIL",
                "reason": "node carries feature_slug but no plan_ref — can't resolve back to a file",
            })
            continue

        plan_ref_path = Path(plan_ref)
        plan_path = plan_ref_path if plan_ref_path.is_absolute() else repo_root / plan_ref_path
        if not plan_path.is_file():
            results.append({
                "slug": slug, "node_id": node_id, "status": "FAIL", "plan_ref": plan_ref,
                "reason": f"plan_ref does not exist on disk: {plan_ref}",
            })
            continue

        fm = sr.scan_frontmatter_scalars(plan_path)
        file_slug = fm.get("feature_slug")
        if file_slug != slug:
            results.append({
                "slug": slug, "node_id": node_id, "status": "FAIL", "plan_ref": plan_ref,
                "reason": f"plan file's feature_slug ({file_slug!r}) != node's feature_slug ({slug!r})",
            })
            continue

        # A plan file binds to exactly ONE feature-level node (its `itt_node_id`), but every
        # descendant of that feature shares the same `feature_slug`. So `itt_node_id == node_id`
        # is the ANCHOR check, valid only for the bound node itself — requiring it of every
        # slug-carrying node would fail the whole tree by construction. For the other members we
        # instead assert the binding is *coherent*: the anchor exists in this tree and agrees on
        # the slug, which is what actually closes slug -> node -> plan -> slug.
        file_node_id = fm.get("itt_node_id")
        role = "member"
        if file_node_id:
            if file_node_id == node_id:
                role = "anchor"
            else:
                anchor = nodes_by_id.get(file_node_id)
                if anchor is None:
                    results.append({
                        "slug": slug, "node_id": node_id, "status": "FAIL", "plan_ref": plan_ref,
                        "reason": (
                            f"plan file's itt_node_id ({file_node_id}) is not a node in this tree "
                            "— the file-side binding is dangling"
                        ),
                    })
                    continue
                anchor_slug = (anchor.get("meta") or {}).get("feature_slug")
                if anchor_slug != slug:
                    results.append({
                        "slug": slug, "node_id": node_id, "status": "FAIL", "plan_ref": plan_ref,
                        "reason": (
                            f"plan file's bound node {file_node_id} carries feature_slug "
                            f"{anchor_slug!r}, not {slug!r} — the binding disagrees with the node"
                        ),
                    })
                    continue

        results.append({
            "slug": slug, "node_id": node_id, "status": "PASS",
            "plan_ref": plan_ref, "role": role,
        })

    if slug_filter and slug_filter not in seen_slugs:
        results.append({
            "slug": slug_filter, "node_id": None, "status": "FAIL",
            "reason": "no node in this tree carries that feature_slug",
        })

    return results


def main(argv: list[str] | None = None, client: itc.IttClient | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Verify the slug -> node -> plan file -> slug round trip (Shipped Work "
                    "Ledger M2 acceptance criterion). Read-only."
    )
    ap.add_argument("--tree", required=True, help="tree id to check")
    ap.add_argument("--repo-root", default=".", help="repo root plan_ref paths resolve against")
    ap.add_argument("--slug", default=None,
                     help="check only this feature_slug (default: every stamped node in the tree)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    client = client or itc.IttClient()
    try:
        results = check_tree(client, args.tree, repo_root, args.slug)
    except itc.IttError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    failures = [r for r in results if r["status"] == "FAIL"]
    summary = {
        "tree": args.tree,
        "slug_filter": args.slug,
        "checked": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
    }

    if args.json:
        print(json.dumps({"summary": summary, "results": results}, indent=2))
    else:
        print(f"[verify-slug-roundtrip] tree={args.tree} slug={args.slug or '(all stamped nodes)'}")
        for r in results:
            line = f"  [{r['status']}] {r['slug']}  node={r.get('node_id')}"
            if r["status"] == "FAIL":
                line += f"\n    reason: {r['reason']}"
            print(line)
        if not results:
            print("  (no nodes in this tree carry feature_slug yet — nothing to verify)")
        print("\n  summary:")
        for k, v in summary.items():
            print(f"    {k}={v}")

    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
