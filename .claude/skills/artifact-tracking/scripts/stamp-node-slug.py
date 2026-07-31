#!/usr/bin/env python3
"""Node-side ``feature_slug`` stamper — Shipped Work Ledger M2, FR-6 + FR-7.

Stamps ``meta.feature_slug`` (and, when resolvable, ``meta.plan_ref``) onto the IntentTree nodes
that a plan file's frontmatter (or the sync-bindings table alone) resolves to. This is the
NODE-side half of the M2 join; the FILE-side writeback (``itt sync import --stamp-frontmatter``)
already shipped upstream in ``../intenttree`` and is NOT reimplemented here.

RESOLUTION (see ``_slug_resolution.py`` for the full contract), most-authoritative first:
    (a) direct              — plan file's own ``itt_node_id`` + ``feature_slug``.
    (b) source_artifact     — plan file's ``source_artifact_id`` -> bindings -> node set.
    (c) retroactive_binding — bindings' own ``feature:<slug>`` task id, no plan file needed.
    (d) tag_match           — (M2 gap-1, lowest precedence) a node ``tags`` entry that EXACTLY
                              equals a ``feature_slug`` present somewhere in the plan corpus.
                              Exact-match-only, unambiguous-only (2+ distinct matches resolves
                              NOTHING — reported in ``ambiguous_tag_match``, never guessed). Only
                              considered for nodes (a)/(b)/(c) resolved nothing for at all.

``meta.plan_ref`` (M2 gap-2) is additionally backfilled for every resolved candidate whose path
didn't already know a specific source file (retroactive_binding / tag_match): a corpus-wide
slug -> plan-file index picks the ``doc_type: implementation_plan`` file for that slug, else
``prd``, else a deterministic lexicographic tie-break (see
``_slug_resolution.select_primary_plan_file``). A node's existing ``meta.plan_ref``, if it differs
from what this run resolves, is NEVER overwritten — flagged as a ``plan_ref_conflict`` instead,
mirroring the FR-7 ``feature_slug`` conflict rule exactly.

WRITE SAFETY
------------
- **Merge, never replace.** The write seam (an HTTP ``PATCH /api/v1/nodes/{id}``, see
  ``_itt_client.IttClient.update_node_meta``) replaces the ENTIRE meta dict server-side. Every
  ``--apply`` write re-reads the node fresh (``get_node``), merges the resolved
  ``feature_slug``/``plan_ref`` into the EXISTING meta dict in memory, and writes back the full
  merged set — as a real JSON object, so nested values (e.g. ``meta.fingerprint``) keep their
  type. No existing meta key is ever dropped.
- **Never overwrite a conflicting feature_slug (FR-7).** If a node already carries a
  ``feature_slug`` that differs from the one this run resolves, it is flagged as a CONFLICT and
  left untouched; the run reports it (file/node/both values) and exits non-zero. This includes an
  internal check — if two resolution PATHS disagree on the slug for the same node (say a
  ``source_artifact`` hit and a ``retroactive_binding`` hit each name a different slug), that is
  also a conflict, never silently picked.
- **Idempotent.** Re-running after a clean apply reports 0 writes (every candidate already
  matches live state) — see ``already_correct`` in the summary.
- **Tree-scoped.** ``itt sync status --tree`` silently ignores the tree filter server-side
  (probed gotcha); this tool filters bindings client-side against the tree's own node-id set
  (``itt tree graph``), so an out-of-tree binding never contributes a candidate.
- **Dry-run by default.** Pass ``--apply`` to commit. Reads (dry-run) are always safe to run
  against the live server.

Exit codes (mirrors ``validate-plan-frontmatter.py``'s convention):
    0 — clean: every resolved candidate was stamped/already-correct, no conflicts.
    2 — one or more conflicts (never auto-resolved).
    1 — usage / internal error (bad path, `itt` unreachable, unparsable response).

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

RESOLUTION_PATHS = ("direct", "source_artifact", "retroactive_binding", "tag_match")


def gather(
    client: itc.IttClient, tree_id: str, plan_root: Path, repo_root: Path
) -> tuple[dict[str, dict], dict[str, sr.Candidate], list[dict], list[sr.AmbiguousTagMatch]]:
    """Fetch the tree graph + bindings and resolve candidates. Read-only — no writes."""
    graph = client.tree_graph(tree_id)
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    bindings = list(client.iter_bindings(tree=tree_id))
    nodes_by_artifact, slug_by_artifact = sr.build_binding_maps(bindings, set(nodes.keys()))
    plan_files = sr.scan_plan_files(plan_root, repo_root)
    candidates, rejected = sr.resolve_candidates(plan_files, nodes_by_artifact, slug_by_artifact)

    # (d) tag_match — lowest precedence; only nodes with NO resolution at all from (a)/(b)/(c).
    slug_index = sr.build_corpus_slug_index(plan_files)
    tag_candidates, tag_rejected, ambiguous = sr.resolve_tag_match_candidates(
        nodes, slug_index, set(candidates.keys())
    )
    candidates.update(tag_candidates)
    rejected = rejected + tag_rejected

    # (gap-2) plan_ref backfill — any resolved candidate that doesn't already know a specific
    # source file (retroactive_binding never does; tag_match already set its own, but this stays
    # generic so any future path benefits too) gets the corpus's primary file for its slug.
    for cand in candidates.values():
        if not cand.plan_ref:
            files = slug_index.get(cand.slug)
            if files:
                cand.plan_ref = sr.select_primary_plan_file(files, cand.slug).rel_path

    return nodes, candidates, rejected, ambiguous


def classify(
    nodes: dict[str, dict], candidates: dict[str, sr.Candidate]
) -> tuple[list[tuple[str, sr.Candidate]], list[str], list[dict]]:
    """Split resolved candidates into (would_stamp, already_correct, conflicts) vs LIVE node state."""
    would_stamp: list[tuple[str, sr.Candidate]] = []
    already_correct: list[str] = []
    conflicts: list[dict] = []

    for node_id, cand in candidates.items():
        node = nodes.get(node_id)
        if node is None:
            continue  # resolved to a node outside the fetched tree graph; shouldn't happen
        if cand.conflicting:
            conflicts.append({
                "node_id": node_id,
                "kind": "resolution_conflict",
                "detail": cand.conflict_detail,
            })
            continue

        meta = node.get("meta") or {}
        existing_slug = meta.get("feature_slug")
        existing_plan_ref = meta.get("plan_ref")

        if existing_slug and existing_slug != cand.slug:
            conflicts.append({
                "node_id": node_id,
                "kind": "write_conflict",
                "existing_feature_slug": existing_slug,
                "resolved_feature_slug": cand.slug,
                "plan_ref": cand.plan_ref,
                "resolution_path": cand.resolution_path,
                "source_file": cand.source_file,
                "detail": (
                    f"node {node_id} already carries feature_slug={existing_slug!r}; this run "
                    f"resolved {cand.slug!r} via {cand.resolution_path} "
                    f"({cand.source_file or 'bindings only'}) — never overwritten (FR-7)"
                ),
            })
            continue

        if existing_plan_ref and cand.plan_ref and existing_plan_ref != cand.plan_ref:
            conflicts.append({
                "node_id": node_id,
                "kind": "plan_ref_conflict",
                "feature_slug": cand.slug,
                "existing_plan_ref": existing_plan_ref,
                "resolved_plan_ref": cand.plan_ref,
                "resolution_path": cand.resolution_path,
                "source_file": cand.source_file,
                "detail": (
                    f"node {node_id} already carries plan_ref={existing_plan_ref!r}; this run "
                    f"resolved {cand.plan_ref!r} via {cand.resolution_path} "
                    f"({cand.source_file or 'bindings only'}) — never overwritten (gap-2)"
                ),
            })
            continue

        slug_ok = existing_slug == cand.slug
        plan_ref_ok = cand.plan_ref is None or existing_plan_ref == cand.plan_ref
        if slug_ok and plan_ref_ok:
            already_correct.append(node_id)
        else:
            would_stamp.append((node_id, cand))

    return would_stamp, already_correct, conflicts


def apply_stamps(
    client: itc.IttClient, would_stamp: list[tuple[str, sr.Candidate]]
) -> list[str]:
    """Read-merge-write each candidate. Returns the list of node_ids actually written."""
    applied: list[str] = []
    for node_id, cand in would_stamp:
        fresh = client.get_node(node_id)
        merged_meta = dict(fresh.get("meta") or {})
        merged_meta["feature_slug"] = cand.slug
        if cand.plan_ref:
            merged_meta["plan_ref"] = cand.plan_ref
        client.update_node_meta(node_id, merged_meta)
        applied.append(node_id)
    return applied


def _build_summary(
    nodes: dict[str, dict],
    candidates: dict[str, sr.Candidate],
    would_stamp: list[tuple[str, sr.Candidate]],
    already_correct: list[str],
    conflicts: list[dict],
    rejected: list[dict],
    ambiguous: list[sr.AmbiguousTagMatch],
    applied: list[str],
    mode: str,
) -> dict:
    by_path = {p: 0 for p in RESOLUTION_PATHS}
    for _, cand in would_stamp:
        by_path[cand.resolution_path] = by_path.get(cand.resolution_path, 0) + 1
    # A node counts as "unresolvable" only if NOTHING resolved for it at all — a node that was
    # rejected by the slug-shape guard had a resolution attempt, it just failed the guard, so it
    # is reported in its own `rejected_slug_shape` bucket, distinct from both `resolvable` and
    # true `unresolvable`.
    rejected_node_ids = {r["node_id"] for r in rejected}
    unresolvable = len(nodes) - len(candidates) - len(rejected_node_ids - set(candidates))
    return {
        "mode": mode,
        "nodes_scanned": len(nodes),
        "resolvable": len(candidates),
        "unresolvable": unresolvable,
        "would_stamp": len(would_stamp),
        "would_stamp_by_path": by_path,
        "already_correct": len(already_correct),
        "conflicts": len(conflicts),
        "rejected_slug_shape": len(rejected),
        "ambiguous_tag_match": len(ambiguous),
        "applied": len(applied),
    }


def main(argv: list[str] | None = None, client: itc.IttClient | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Stamp IntentTree node.meta.feature_slug (+plan_ref) — Shipped Work Ledger "
                    "M2 FR-6/FR-7. Dry-run by default; --apply to commit."
    )
    ap.add_argument("--tree", required=True, help="tree id to scope to (client-side filtered)")
    ap.add_argument("--plan-root", default="docs/project_plans",
                     help="root to scan for plan files (default: docs/project_plans)")
    ap.add_argument("--repo-root", default=".",
                     help="repo root; plan_ref is stamped as a path relative to this")
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
        nodes, candidates, rejected, ambiguous = gather(client, args.tree, plan_root, repo_root)
    except itc.IttError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    would_stamp, already_correct, conflicts = classify(nodes, candidates)

    applied: list[str] = []
    if args.apply:
        try:
            applied = apply_stamps(client, would_stamp)
        except itc.IttError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1

    summary = _build_summary(
        nodes, candidates, would_stamp, already_correct, conflicts, rejected, ambiguous, applied,
        mode="apply" if args.apply else "dry-run",
    )

    if args.json:
        print(json.dumps({
            "tree": args.tree,
            "summary": summary,
            "would_stamp": [
                {
                    "node_id": node_id,
                    "feature_slug": cand.slug,
                    "plan_ref": cand.plan_ref,
                    "resolution_path": cand.resolution_path,
                    "source_file": cand.source_file,
                    "applied": node_id in applied,
                }
                for node_id, cand in would_stamp
            ],
            "conflicts": conflicts,
            "rejected_slug_shape": rejected,
            "ambiguous_tag_match": [
                {"node_id": a.node_id, "tags": a.tags, "matched_slugs": a.matched_slugs}
                for a in ambiguous
            ],
        }, indent=2))
    else:
        verb = "APPLY" if args.apply else "DRY-RUN"
        print(f"[stamp-node-slug] {verb} tree={args.tree} plan_root={plan_root}")
        for node_id, cand in would_stamp:
            tag = "STAMPED" if node_id in applied else "would-stamp"
            print(f"  {node_id}\n    feature_slug={cand.slug!r} plan_ref={cand.plan_ref!r} "
                  f"via={cand.resolution_path} ({cand.source_file or 'bindings only'})  [{tag}]")
        for c in conflicts:
            print(f"  CONFLICT [{c['kind']}] {c['detail']}")
        for r in rejected:
            print(
                f"  REJECTED [slug_shape] node={r['node_id']} value={r['value']!r} "
                f"via={r['resolution_path']} ({r['source_file'] or 'bindings only'})\n"
                f"    reason: {r['reason']}"
            )
        for a in ambiguous:
            print(
                f"  AMBIGUOUS [tag_match] node={a.node_id} tags={a.tags} "
                f"matched_slugs={a.matched_slugs} — resolved nothing"
            )
        print("\n  summary:")
        for k, v in summary.items():
            print(f"    {k}={v}")

    # A rejected slug-shape resolution and an ambiguous tag_match are both data-quality signals a
    # human needs to see — treated like a conflict for exit-code purposes (never silently
    # swallowed) — but each counted and reported in its own bucket so the causes stay
    # distinguishable in the report.
    return 2 if (conflicts or rejected or ambiguous) else 0


if __name__ == "__main__":
    sys.exit(main())
