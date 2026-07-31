#!/usr/bin/env python3
"""Backfill script for completed IntentTree nodes — Shipped Work Ledger M3, FR-10 + FR-11.

Reconciles nodes that already carry ``meta.feature_slug`` to their plan file (via
``_slug_resolution.select_primary_plan_file``) and populates typed ``ExternalLink`` evidence rows
from that plan file's OWN hand-authored ``commit_refs``/``pr_refs`` frontmatter fields — this is
NOT a git-log full-text mining pass (see the M3 leg contract §6 L3 and FR-10).

FR-11 — never write a duplicate or conflicting row:
    Before writing anything to a node, the node's existing ``external_links`` are read via
    ``IttClient.get_node_full`` and checked against every candidate ref (matched on
    ``(system, external_id)``, the same identity IntentTree's own server-side upsert uses).
    A match is reported as ``already_present`` — never re-written. Re-running with ``--apply``
    twice therefore writes nothing new the second time (see ``TestIdempotency`` in the test file).

Fail-closed (D-M3-3): every ``commit_refs``/``pr_refs`` value is normalized through
``_evidence_refs.normalize_refs``, which reports (never guesses) anything it cannot confidently
parse — see that module for the canonical trap (``"direct-squash-to-main"``). Skips are
first-class output here too: every feature's report carries its own ``skipped`` list, each entry
naming WHY, so the operator can see exactly what did not backfill and why (never a silent filter).

A "conflict" (exit code 2) is distinct from a "skip": it means a ref DID normalize confidently,
and the node ALREADY carries an external link with that same ``(system, external_id)`` identity —
but pointing at a DIFFERENT ``external_path`` than what the plan file resolves. That is a genuine
contradiction between live state and the plan file's own record, and — like every write-conflict
elsewhere in this skill — it is reported and left untouched, never silently overwritten.

Exit codes (mirrors ``stamp-node-slug.py``'s convention):
    0 — clean: nothing to write, or everything written/already-present, no conflicts.
    2 — one or more conflicts found (never auto-resolved).
    1 — usage / internal error (bad path, IntentTree unreachable, unparsable response).

Dry-run by default; pass ``--apply`` to commit. ``--json`` for machine-readable output.

Python 3.10+ floor (must run on the node's 3.11 — no 3.12-only syntax). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _evidence_refs as evr  # noqa: E402
import _itt_client as itc  # noqa: E402
import _slug_resolution as sr  # noqa: E402


@dataclass
class FeatureReport:
    slug: str
    node_id: str
    plan_ref: str | None
    would_write: list[evr.EvidenceRef] = field(default_factory=list)
    already_present: list[evr.EvidenceRef] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)


def _ref_dict(ref: evr.EvidenceRef) -> dict:
    return {
        "raw": ref.raw, "kind": ref.kind, "repo": ref.repo, "ident": ref.ident,
        "url": ref.url, "system": ref.system,
    }


def verify_local_commits(
    refs: list[evr.EvidenceRef],
    repo_root: Path,
    local_repo: str | None,
    runner: "Callable[[str], bool] | None" = None,
) -> tuple[list[evr.EvidenceRef], list[dict]]:
    """Drop commit refs whose sha does not exist in the LOCAL repo.

    Shape-validity is not existence. A plan file can cite a sha that never landed — measured
    live: ``agentic-redeploy-pipeline-v1.md`` cites ``7a85dc3``, which is not a valid object in
    this repo (the real commit is ``92ad8b7``), and a matching dangling ``ExternalLink`` has been
    sitting on its node since 2026-06-24. Shape-checking alone happily mints a 404 GitHub URL,
    which is the same "poisons trust" failure class as a wrong repo.

    This is a **local, offline** check (``git cat-file -t <sha>``) — verification, not the
    git-log *mining* FR-10 forbids. We never search history for commits to attribute to a
    feature; we only confirm a sha the plan file already named actually exists.

    Only refs belonging to *this* repo are checked: a cross-repo sha (e.g. an ``intenttree``
    commit, now correctly attributed thanks to comment-based repo inference) cannot be resolved
    from here, so it passes through unverified rather than being wrongly dropped.
    """
    def _git_has_commit(sha: str) -> bool:
        import subprocess
        try:
            proc = subprocess.run(
                ["git", "cat-file", "-t", sha],
                cwd=str(repo_root), capture_output=True, text=True, timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return True  # git unavailable -> do not fabricate a failure; pass through
        return proc.returncode == 0 and proc.stdout.strip() == "commit"

    check = runner if runner is not None else _git_has_commit

    kept: list[evr.EvidenceRef] = []
    dropped: list[dict] = []
    for ref in refs:
        if ref.kind != "commit" or (local_repo is not None and ref.repo != local_repo):
            kept.append(ref)
            continue
        try:
            exists = check(ref.ident)
        except Exception:
            # An environment failure is NOT evidence that the commit is missing. Fail OPEN
            # here specifically: dropping a real ref because git misbehaved would lose true
            # evidence, which is worse than leaving one unverified. (The fail-CLOSED rule
            # governs normalization — never invent a ref — not existence verification.)
            kept.append(ref)
            continue
        if exists:
            kept.append(ref)
        else:
            dropped.append({
                "raw": ref.raw,
                "reason": (
                    f"commit sha {ref.ident!r} does not exist in the local repo "
                    f"({ref.repo}) — cited by the plan file but never landed; not linked"
                ),
            })
    return kept, dropped


def _link_system(link: dict) -> str | None:
    """The link's system, tolerating IntentTree's request/response field-name asymmetry.

    The ATTACH REQUEST body field is ``system`` (``ExternalLinkAttachRequest``), but the
    stored row and every READ path return it as ``source_system`` (the ``ExternalSystem``
    column). Matching only on ``system`` silently never matches a real server row, so the
    FR-11 pre-read reports already-written links as new on every run. Verified live: a node
    returns ``{"source_system": "github", "external_id": "...", ...}``.
    """
    value = link.get("source_system")
    if value is None:
        value = link.get("system")
    return value


def _find_matching_link(existing_links: list[dict], ref: evr.EvidenceRef) -> dict | None:
    """Identity match on ``(system, external_id)`` — the same key IntentTree's own server-side
    upsert uses (see the M3 leg contract §2.1)."""
    for link in existing_links:
        if _link_system(link) == ref.system and str(link.get("external_id")) == str(ref.ident):
            return link
    return None


def select_anchor_nodes(nodes: list[dict], slug_nodes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Reduce a slug's node set to its ANCHOR node(s) — the roots of the slug-subtree.

    Orchestrator adjudication (M3, claude-primary). A ``feature_slug`` is shared by a
    feature's whole subtree (the M2 anchor/member model), so a naive "write to every node
    carrying the slug" attaches the same PR/commit to every descendant. That is both noisy
    (measured: 41 nodes for ``codex-aos-integration``, one commit repeated 41x) and *false*
    — it asserts that a commit shipped each individual subtask, and it stamps shipped
    evidence onto nodes whose own status is ``not_started``.

    A commit/PR ships a FEATURE. So evidence attaches to the root(s) of the slug-subtree:
    a node whose parent does not itself carry the same slug. Normally that is exactly one
    node (the feature/plan node). When a feature's nodes are siblings under an unstamped
    parent, they are all roots and all receive the evidence — deterministic, and correct in
    the sense that no member sits below another.

    Use ``--scope all-members`` to restore the write-to-every-node behaviour.
    """
    by_id = {n["id"]: n for n in nodes}
    slug_of = dict(slug_nodes)
    anchors: list[tuple[str, str]] = []
    for node_id, slug in slug_nodes:
        parent_id = (by_id.get(node_id) or {}).get("parent_id")
        # A root of this slug's subtree: no parent, or a parent outside this slug's set.
        if not parent_id or slug_of.get(parent_id) != slug:
            anchors.append((node_id, slug))
    return anchors


def gather_feature_nodes(
    client: itc.IttClient,
    tree_id: str,
    slug_filter: str | None = None,
    scope: str = "anchor",
) -> list[tuple[str, str]]:
    """The ``(node_id, feature_slug)`` pairs to backfill.

    ``scope="anchor"`` (default) writes evidence only to each feature's subtree root(s);
    ``scope="all-members"`` writes to every node carrying the slug. See
    :func:`select_anchor_nodes` for why anchor is the default.
    """
    nodes = client.tree_nodes(tree_id)
    out: list[tuple[str, str]] = []
    for node in nodes:
        meta = node.get("meta") or {}
        slug = meta.get("feature_slug")
        if not slug:
            continue
        if slug_filter and slug != slug_filter:
            continue
        out.append((node["id"], slug))
    if scope == "all-members":
        return out
    return select_anchor_nodes(nodes, out)


def process_feature(
    client: itc.IttClient,
    node_id: str,
    slug: str,
    slug_index: dict[str, list[sr.PlanFile]],
    default_repo: str | None,
    repo_root: Path | None = None,
    verify_commits: bool = True,
) -> FeatureReport:
    """Read-only reconciliation for one feature: resolve its plan file, normalize its refs
    (fail-closed), and pre-read the node's existing external links (FR-11) to classify every
    candidate ref as would_write / already_present / conflict. Never writes."""
    files = slug_index.get(slug)
    if not files:
        return FeatureReport(
            slug=slug, node_id=node_id, plan_ref=None,
            skipped=[{
                "raw": slug,
                "reason": f"no plan file in the corpus carries feature_slug={slug!r}",
            }],
        )

    primary = sr.select_primary_plan_file(files, slug)
    plan_ref = primary.rel_path

    # Evidence is a property of the FEATURE, so it is the UNION over every plan document
    # carrying this slug — not just the primary. Measured live: `dynamic-artifact-provisioning`
    # keeps its real commit_refs in the phase plan (`...-p2-fleet-v1.md`) while M2's
    # primary-file rule (correctly) points plan_ref at the canonical `...-v1.md`. Reading only
    # the primary silently lost that feature's entire evidence set. `plan_ref` still reports the
    # canonical file; only the ref harvest is widened.
    commit_refs_raw: list[str] = []
    pr_refs_raw: list[str] = []
    read_errors: list[dict] = []
    for plan_file in files:
        try:
            text = plan_file.path.read_text(encoding="utf-8")
        except OSError as exc:
            read_errors.append({
                "raw": plan_file.rel_path,
                "reason": f"could not read plan file: {exc}",
            })
            continue
        commit_refs_raw.extend(evr.parse_frontmatter_list(text, "commit_refs"))
        pr_refs_raw.extend(evr.parse_frontmatter_list(text, "pr_refs"))

    if read_errors and not commit_refs_raw and not pr_refs_raw:
        return FeatureReport(slug=slug, node_id=node_id, plan_ref=plan_ref, skipped=read_errors)

    refs, skipped_refs = evr.normalize_refs(commit_refs_raw, pr_refs_raw, default_repo=default_repo)
    # De-duplicate refs harvested from sibling plan documents (same sha cited in two files).
    _seen: set[tuple[str, str]] = set()
    _deduped = []
    for ref in refs:
        key = (ref.system, ref.ident)
        if key in _seen:
            continue
        _seen.add(key)
        _deduped.append(ref)
    refs = _deduped

    # Existence check (local, offline) — shape-valid is not the same as real.
    unverified: list[dict] = []
    if verify_commits and repo_root is not None:
        refs, unverified = verify_local_commits(refs, repo_root, default_repo)

    node_full = client.get_node_full(node_id)
    existing_links = node_full.get("external_links") or []

    report = FeatureReport(slug=slug, node_id=node_id, plan_ref=plan_ref)
    report.skipped = read_errors + unverified + [{"raw": s.raw, "reason": s.reason} for s in skipped_refs]

    for ref in refs:
        match = _find_matching_link(existing_links, ref)
        if match is None:
            report.would_write.append(ref)
            continue
        existing_path = match.get("external_path")
        if ref.url and existing_path and existing_path != ref.url:
            report.conflicts.append({
                "raw": ref.raw, "system": ref.system, "external_id": ref.ident,
                "existing_external_path": existing_path, "resolved_external_path": ref.url,
                "reason": (
                    f"node {node_id} already carries an external link {ref.system}:{ref.ident} "
                    f"pointing at {existing_path!r}; the plan file resolves {ref.url!r} — "
                    "never overwritten"
                ),
            })
            continue
        report.already_present.append(ref)

    return report


def apply_writes(client: itc.IttClient, reports: list[FeatureReport]) -> int:
    """Write every ``would_write`` ref via ``attach_external_link``. Returns the count written."""
    written = 0
    for report in reports:
        for ref in report.would_write:
            client.attach_external_link(
                report.node_id,
                system=ref.system,
                external_id=ref.ident,
                external_path=ref.url,
                context_label=f"{ref.kind}:{ref.raw}",
            )
            written += 1
    return written


def _build_totals(reports: list[FeatureReport], applied: int, mode: str) -> dict:
    return {
        "mode": mode,
        "features_scanned": len(reports),
        "would_write": sum(len(r.would_write) for r in reports),
        "already_present": sum(len(r.already_present) for r in reports),
        "skipped": sum(len(r.skipped) for r in reports),
        "conflicts": sum(len(r.conflicts) for r in reports),
        "applied": applied,
    }


def main(argv: list[str] | None = None, client: itc.IttClient | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Backfill IntentTree node evidence (ExternalLink rows) from plan-file "
                    "commit_refs/pr_refs — Shipped Work Ledger M3 FR-10/FR-11. Dry-run by "
                    "default; --apply to commit."
    )
    ap.add_argument("--tree", required=True, help="tree id to scope to")
    ap.add_argument("--plan-root", default="docs/project_plans",
                     help="root to scan for plan files (default: docs/project_plans)")
    ap.add_argument("--repo-root", default=".",
                     help="repo root; plan_ref is reported as a path relative to this")
    ap.add_argument("--default-repo", default=None,
                     help="repo name to use for bare shas/PR numbers with no explicit repo")
    ap.add_argument("--apply", action="store_true", help="write links (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--slug", default=None, help="limit to one feature_slug")
    ap.add_argument("--no-verify-commits", action="store_true",
                     help="skip the local `git cat-file` existence check on commit shas "
                          "(the check is offline verification, not git-log mining)")
    ap.add_argument("--scope", choices=("anchor", "all-members"), default="anchor",
                     help="which nodes receive evidence: 'anchor' (default) writes to each "
                          "feature's subtree root(s) only — a commit ships a FEATURE, not each "
                          "of its subtasks; 'all-members' writes to every node carrying the slug")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    plan_root_arg = Path(args.plan_root)
    plan_root = plan_root_arg if plan_root_arg.is_absolute() else repo_root / plan_root_arg
    if not plan_root.exists():
        sys.stderr.write(f"error: plan root not found: {plan_root}\n")
        return 1

    client = client or itc.IttClient()
    try:
        feature_nodes = gather_feature_nodes(
            client, args.tree, slug_filter=args.slug, scope=args.scope
        )
        plan_files = sr.scan_plan_files(plan_root, repo_root)
        slug_index = sr.build_corpus_slug_index(plan_files)
        reports = [
            process_feature(
                client, node_id, slug, slug_index, args.default_repo,
                repo_root=repo_root, verify_commits=not args.no_verify_commits,
            )
            for node_id, slug in feature_nodes
        ]
    except itc.IttError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    applied = 0
    if args.apply:
        try:
            applied = apply_writes(client, reports)
        except itc.IttError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1

    totals = _build_totals(reports, applied, mode="apply" if args.apply else "dry-run")

    if args.json:
        print(json.dumps({
            "tree": args.tree,
            "totals": totals,
            "features": [
                {
                    "slug": r.slug,
                    "node_id": r.node_id,
                    "plan_ref": r.plan_ref,
                    "would_write": [_ref_dict(x) for x in r.would_write],
                    "already_present": [_ref_dict(x) for x in r.already_present],
                    "skipped": r.skipped,
                    "conflicts": r.conflicts,
                }
                for r in reports
            ],
        }, indent=2))
    else:
        verb = "APPLY" if args.apply else "DRY-RUN"
        print(f"[backfill-node-evidence] {verb} tree={args.tree} plan_root={plan_root}")
        for r in reports:
            print(f"  {r.slug} (node={r.node_id}, plan_ref={r.plan_ref})")
            for ref in r.would_write:
                tag = "WRITTEN" if args.apply else "would-write"
                print(f"    [{tag}] {ref.kind} {ref.system}:{ref.ident} -> {ref.url}")
            for ref in r.already_present:
                print(f"    [already-present] {ref.kind} {ref.system}:{ref.ident}")
            for s in r.skipped:
                print(f"    [SKIPPED] raw={s['raw']!r}\n      reason: {s['reason']}")
            for c in r.conflicts:
                print(f"    [CONFLICT] {c['reason']}")
        print("\n  totals:")
        for k, v in totals.items():
            print(f"    {k}={v}")

    has_conflicts = any(r.conflicts for r in reports)
    return 2 if has_conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
