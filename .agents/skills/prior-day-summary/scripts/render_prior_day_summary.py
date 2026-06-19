#!/usr/bin/env python3
"""Render a first-pass markdown prior-day summary from collected evidence JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_template(base: Path, classification: str) -> str:
    mapping = {
        "empty_day": "empty-day-summary.md",
        "branch_local": "branch-local-summary.md",
        "docs_only": "docs-only-summary.md",
        "shipped": "standard-summary.md",
    }
    return (base / mapping.get(classification, "standard-summary.md")).read_text(encoding="utf-8")


def bullet_subjects(commits: list[dict], limit: int = 5) -> str:
    if not commits:
        return "none"
    lines = [f"`{commit['sha'][:8]}` {commit['subject']}" for commit in commits[:limit]]
    if len(commits) > limit:
        lines.append(f"... plus {len(commits) - limit} more")
    return "; ".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Evidence JSON file from collect_window_evidence.py.")
    parser.add_argument("--mode", choices=["brief", "full"], default="full")
    parser.add_argument("--out", help="Optional markdown output path.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    classification = payload["classification"]
    template = load_template(templates_dir, classification)

    changelog_hits = payload.get("changelog_hits", [])
    changelog_text = ", ".join(f"{hit['path']} [{hit['version']}]" for hit in changelog_hits) if changelog_hits else "none"
    context_block = "Nearest prior visible work may be named only as caveated context." if classification == "empty_day" else "No extra context required."
    visible_changes_block = (
        "Defer visible-surface analysis until real web, CLI, docs, or demo surfaces are confirmed."
        if classification != "empty_day"
        else "No visible changes should be claimed for this date window."
    )
    caveat_block = payload.get("classification_rationale", "Evidence was collected, but the summary still needs repo-specific interpretation.")
    summary_opening = payload.get("classification_rationale", "Prior-day evidence collected.")

    rendered = template.format(
        target_date=payload["target_date"],
        classification=classification,
        current_branch=payload.get("current_branch", "unknown"),
        mainline_count=payload.get("mainline_commit_count", 0),
        window_commit_count=payload.get("window_commit_count", 0),
        merge_count=payload.get("merge_count", 0),
        branch_divergence=payload.get("branch_divergence", "unknown"),
        changelog_hits=changelog_text,
        visible_changes_block=visible_changes_block,
        caveat_block=caveat_block,
        context_block=context_block,
        summary_opening=summary_opening,
        commit_examples=bullet_subjects(payload.get("window_commits", [])),
    )

    if args.mode == "brief":
        rendered = "\n".join(rendered.splitlines()[:12]).rstrip() + "\n"

    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
