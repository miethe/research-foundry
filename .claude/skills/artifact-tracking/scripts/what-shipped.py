#!/usr/bin/env python3
"""What-shipped ledger query — Shipped Work Ledger M3 L4, the AC demo.

Answers the M3 acceptance criterion in one command: *"one query returns completed features for
each project, each joined to its plan file and carrying a PR/commit link + test evidence."*

    fetch tree nodes -> filter status == "completed" -> split joinable (carries
    meta.feature_slug) vs unjoinable -> for joinable nodes, resolve a plan_ref (node's own
    meta.plan_ref, falling back to a corpus lookup by feature_slug via `_slug_resolution`) and
    check it exists on disk -> `get_node_full` for external_links/completion_evidence/
    validation_runs -> extract PR links, commit links, and validation evidence.

**Honest coverage reporting is the hard requirement this script exists to satisfy** (M3 leg
contract, L4). Unjoinable completed nodes are never silently dropped — they are counted and
listed by node id/title so the operator sees exactly how much of "what shipped" this ledger can
actually answer today. A `plan_ref` that does not exist on disk is flagged `dangling`, never
shown as a clean join.

Read-only: no `--apply` mode exists for this tool, and it must never write to the live server.

Performance: `get_node_full` (one HTTP GET per node) is only ever called for nodes that are BOTH
completed AND carry a `feature_slug` — on a large tree with few/no joinable nodes (e.g. the
skillmeat tree at M3 time, ~514 completed / 0 joinable), this degrades to a single cheap
`tree_nodes` call. `--limit` caps how many completed nodes are fully processed (deterministically,
sorted by title then node id) while `total_completed` in the report always reflects the FULL,
unlimited count — limiting never silently shrinks the reported total shipped work, only how many
rows are joined/detailed in this run.

Python 3.10+ floor (must import on the node's 3.11 — no 3.12-only syntax). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _evidence_refs as er  # noqa: E402,F401  (re-exported for callers/tests that want it)
import _itt_client as itc  # noqa: E402
import _slug_resolution as sr  # noqa: E402

_TIMESTAMP_KEYS = ("completed_at", "updated_at", "created_at")


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _parse_since(value: str | None) -> datetime | None:
    """Parse an ISO-8601 ``--since`` date/datetime. Raises ValueError on malformed input."""
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _node_timestamp(node: dict[str, Any]) -> datetime | None:
    """Best-effort node timestamp for `--since` filtering. The tree graph payload's documented
    shape (id/status/meta/tags/title) carries no confirmed timestamp field — this checks a few
    plausible top-level keys and never raises on an unparsable value; unknown stays unknown."""
    for key in _TIMESTAMP_KEYS:
        raw = node.get(key)
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _resolve_plan_ref(
    meta: dict[str, Any], slug: str, slug_index: dict[str, list[sr.PlanFile]]
) -> tuple[str | None, str | None]:
    """Return ``(plan_ref, source)`` — source is ``"node_meta"``, ``"corpus"``, or ``None``.

    Prefers the node's own stamped ``meta.plan_ref`` (M2's join); falls back to a corpus lookup
    by ``feature_slug`` (via `_slug_resolution.select_primary_plan_file`) when the node has a
    slug but no stamped plan_ref of its own.
    """
    meta_plan_ref = meta.get("plan_ref")
    if meta_plan_ref:
        return str(meta_plan_ref), "node_meta"
    candidates = slug_index.get(slug)
    if candidates:
        return sr.select_primary_plan_file(candidates, slug).rel_path, "corpus"
    return None, None


_PR_PATH_RE = re.compile(r"/pull/")
_COMMIT_PATH_RE = re.compile(r"/commit/")


def _extract_evidence(node_full: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    """Pull ``(pr_links, commit_links, validation_evidence)`` out of a `get_node_full` payload.

    Evidence may live in either typed row family depending on which leg wrote it (external_links
    for FR-8's PR/commit rows, completion_evidence for the git_merge landing row and the
    validation fallback per D-M3-1) — this reads both rather than assuming one shape.
    """
    pr_links: list[str] = []
    commit_links: list[str] = []
    validation: list[dict[str, Any]] = []

    for link in node_full.get("external_links") or []:
        path = link.get("external_path") or ""
        ident = link.get("external_id") or ""
        display = path or ident
        if not display:
            continue
        if _PR_PATH_RE.search(path):
            pr_links.append(display)
        elif _COMMIT_PATH_RE.search(path):
            commit_links.append(display)
        elif link.get("system") == "git":
            commit_links.append(display)  # sha-only git links carry no URL, no /pull//commit/
        elif link.get("system") in ("github", "other"):
            commit_links.append(display)

    for ev in node_full.get("completion_evidence") or []:
        kind = ev.get("kind")
        ref = ev.get("ref_value") or ev.get("label")
        if kind == "pull_request" and ref:
            pr_links.append(ref)
        elif kind in ("git_commit", "git_merge") and ref:
            commit_links.append(ref)
        elif kind == "validation":
            validation.append({"source": "completion_evidence", "label": ev.get("label") or ref})

    for run in node_full.get("validation_runs") or []:
        validation.append({
            "source": "validation_run",
            "label": run.get("command") or run.get("kind") or "validation_run",
        })

    return _dedupe(pr_links), _dedupe(commit_links), validation


def _feature_anchor_ids(nodes: list[dict[str, Any]], slug: str) -> list[str]:
    """The anchor node id(s) for *slug* — roots of that slug's subtree.

    Mirrors ``backfill-node-evidence.select_anchor_nodes``: a node whose parent does not
    carry the same slug. Kept as a tiny local helper rather than a cross-script import so
    this read-only query has no dependency on the writer.
    """
    slug_of = {
        str(n.get("id")): (n.get("meta") or {}).get("feature_slug")
        for n in nodes
    }
    anchors: list[str] = []
    for node in nodes:
        node_id = str(node.get("id"))
        if slug_of.get(node_id) != slug:
            continue
        parent_id = node.get("parent_id")
        if not parent_id or slug_of.get(str(parent_id)) != slug:
            anchors.append(node_id)
    return anchors


def _inherit_feature_anchor_evidence(
    client: itc.IttClient,
    nodes: list[dict[str, Any]],
    joinable_rows: list[dict[str, Any]],
) -> None:
    """Let a completed member inherit its FEATURE's evidence, in place.

    The ledger's unit is the *feature*, not the node: the M3 AC asks for "completed features
    ... carrying a PR/commit link". Evidence is written once per feature, onto that feature's
    anchor node (a commit ships a feature, not each of its subtasks — see
    ``backfill-node-evidence.select_anchor_nodes``). But a feature's *completed* work is
    usually a descendant, while the anchor itself may still be ``in_progress``. Without this
    step the ledger reports "no evidence" for features that demonstrably shipped — measured
    live: 1 of 8 joinable rows carried evidence before, because the other 7 completed nodes
    were members whose anchor held the rows.

    Inherited evidence is labelled ``evidence_source="feature_anchor"`` (vs ``"node"``) so the
    provenance is never silently blurred. Anchors are fetched at most once per slug.
    """
    cache: dict[str, tuple[list[str], list[str], list[dict[str, Any]]]] = {}
    for row in joinable_rows:
        row.setdefault(
            "evidence_source",
            "node" if (row["pr_links"] or row["commit_links"] or row["validation_evidence"]) else "none",
        )
        if row["pr_links"] or row["commit_links"] or row["validation_evidence"]:
            continue
        slug = row["slug"]
        if slug not in cache:
            prs: list[str] = []
            commits: list[str] = []
            vals: list[dict[str, Any]] = []
            for anchor_id in _feature_anchor_ids(nodes, slug):
                if anchor_id == row["node_id"]:
                    continue  # already read as this row's own node
                try:
                    a_pr, a_commit, a_val = _extract_evidence(client.get_node_full(anchor_id))
                except itc.IttError:
                    continue  # non-fatal: a missing anchor never breaks the ledger
                prs.extend(a_pr)
                commits.extend(a_commit)
                vals.extend(a_val)
            cache[slug] = (_dedupe(prs), _dedupe(commits), vals)
        a_pr, a_commit, a_val = cache[slug]
        if a_pr or a_commit or a_val:
            row["pr_links"] = a_pr
            row["commit_links"] = a_commit
            row["validation_evidence"] = a_val
            row["evidence_source"] = "feature_anchor"


def build_ledger(
    client: itc.IttClient,
    tree_id: str,
    plan_root: Path,
    repo_root: Path,
    *,
    since: datetime | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build the full what-shipped report for *tree_id*. Read-only."""
    nodes = client.tree_nodes(tree_id)
    completed = [n for n in nodes if n.get("status") == "completed"]
    total_completed = len(completed)

    unknown_timestamp = 0
    if since is not None:
        kept = []
        for n in completed:
            ts = _node_timestamp(n)
            if ts is None:
                unknown_timestamp += 1
                kept.append(n)  # never silently drop — unknown stays in, honesty over precision
            elif ts >= since:
                kept.append(n)
        completed = kept

    filtered_completed = len(completed)
    completed.sort(key=lambda n: (str(n.get("title") or ""), str(n.get("id") or "")))

    truncated = bool(limit is not None and limit < len(completed))
    working_set = completed[:limit] if limit is not None else completed

    plan_files = sr.scan_plan_files(plan_root, repo_root)
    slug_index = sr.build_corpus_slug_index(plan_files)

    joinable_rows: list[dict[str, Any]] = []
    unjoinable_rows: list[dict[str, Any]] = []

    for node in working_set:
        node_id = str(node.get("id"))
        title = node.get("title") or node_id
        meta = node.get("meta") or {}
        slug = meta.get("feature_slug")

        if not slug:
            unjoinable_rows.append({"node_id": node_id, "title": title})
            continue

        plan_ref, plan_ref_source = _resolve_plan_ref(meta, slug, slug_index)
        plan_ref_exists: bool | None = None
        dangling = False
        if plan_ref:
            plan_ref_path = Path(plan_ref)
            resolved = plan_ref_path if plan_ref_path.is_absolute() else repo_root / plan_ref_path
            plan_ref_exists = resolved.is_file()
            dangling = not plan_ref_exists

        node_full = client.get_node_full(node_id)
        pr_links, commit_links, validation = _extract_evidence(node_full)

        joinable_rows.append({
            "slug": slug,
            "node_id": node_id,
            "title": title,
            "plan_ref": plan_ref,
            "plan_ref_source": plan_ref_source,
            "plan_ref_exists": plan_ref_exists,
            "dangling": dangling,
            "pr_links": pr_links,
            "commit_links": commit_links,
            "validation_evidence": validation,
        })

    _inherit_feature_anchor_evidence(client, nodes, joinable_rows)

    dangling_count = sum(1 for r in joinable_rows if r["dangling"])
    with_pr_or_commit = sum(1 for r in joinable_rows if r["pr_links"] or r["commit_links"])
    with_validation = sum(1 for r in joinable_rows if r["validation_evidence"])

    return {
        "tree": tree_id,
        "since": since.isoformat() if since else None,
        "limit": limit,
        "total_completed": total_completed,
        "filtered_completed": filtered_completed,
        "processed_completed": len(working_set),
        "truncated": truncated,
        "unknown_timestamp": unknown_timestamp,
        "joinable": joinable_rows,
        "unjoinable": unjoinable_rows,
        "counts": {
            "completed": total_completed,
            "filtered_completed": filtered_completed,
            "processed": len(working_set),
            "joinable": len(joinable_rows),
            "unjoinable": len(unjoinable_rows),
            "dangling_plan_ref": dangling_count,
            "with_pr_or_commit_evidence": with_pr_or_commit,
            "with_validation_evidence": with_validation,
        },
    }


def _format_human(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"[what-shipped] tree={report['tree']}")
    if report["since"]:
        lines.append(f"  since={report['since']} (unknown-timestamp nodes kept: {report['unknown_timestamp']})")
    if report["truncated"]:
        lines.append(
            f"  NOTE: --limit truncated processing to {report['processed_completed']} of "
            f"{report['filtered_completed']} completed nodes considered (total completed in "
            f"tree: {report['total_completed']}) — totals below reflect only the processed set."
        )

    lines.append("")
    lines.append("  joinable (carry feature_slug):")
    if not report["joinable"]:
        lines.append("    (none)")
    for row in report["joinable"]:
        plan_bit = row["plan_ref"] or "(no plan file resolved)"
        if row["plan_ref"]:
            plan_bit += " [DANGLING]" if row["dangling"] else " [ok]"
        lines.append(f"    - {row['slug']}  node={row['node_id']}  title={row['title']!r}")
        lines.append(f"        plan_ref: {plan_bit}")
        lines.append(f"        PR links: {row['pr_links'] or '(none)'}")
        lines.append(f"        commit links: {row['commit_links'] or '(none)'}")
        val_labels = [v["label"] for v in row["validation_evidence"]]
        lines.append(f"        validation evidence: {val_labels or '(none)'}")

    lines.append("")
    lines.append("  unjoinable (no feature_slug — no join key at all):")
    if not report["unjoinable"]:
        lines.append("    (none)")
    for row in report["unjoinable"]:
        lines.append(f"    - node={row['node_id']}  title={row['title']!r}")

    c = report["counts"]
    lines.append("")
    lines.append(
        f"  {c['completed']} completed nodes · {c['joinable']} joinable (carry feature_slug) · "
        f"{c['unjoinable']} unjoinable (no join key)"
    )
    lines.append(
        f"  {c['with_pr_or_commit_evidence']} with PR/commit evidence · "
        f"{c['with_validation_evidence']} with validation evidence"
    )
    if c["dangling_plan_ref"]:
        lines.append(f"  {c['dangling_plan_ref']} joinable feature(s) have a DANGLING plan_ref")
    if report["truncated"]:
        lines.append(
            f"  (counts above are over the {report['processed_completed']}-node processed "
            f"subset, not the full {c['completed']} completed nodes — re-run with a higher/no "
            f"--limit for the full picture)"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None, client: itc.IttClient | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="What-shipped ledger query — Shipped Work Ledger M3 acceptance criterion. "
                    "Read-only; no --apply mode."
    )
    ap.add_argument("--tree", required=True, help="tree id to query")
    ap.add_argument("--plan-root", default="docs/project_plans", help="plan corpus root")
    ap.add_argument("--repo-root", default=".", help="repo root plan_ref paths resolve against")
    ap.add_argument("--since", default=None, help="only include nodes completed on/after this ISO date")
    ap.add_argument("--limit", type=int, default=None, help="cap the number of completed nodes fully processed")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        since = _parse_since(args.since)
    except ValueError as exc:
        sys.stderr.write(f"error: --since is not a valid ISO date/datetime: {exc}\n")
        return 1

    if args.limit is not None and args.limit < 0:
        sys.stderr.write("error: --limit must be non-negative\n")
        return 1

    repo_root = Path(args.repo_root).resolve()
    plan_root = Path(args.plan_root)
    if not plan_root.is_absolute():
        plan_root = repo_root / plan_root

    client = client or itc.IttClient()
    try:
        report = build_ledger(
            client, args.tree, plan_root, repo_root, since=since, limit=args.limit
        )
    except itc.IttError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_format_human(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
