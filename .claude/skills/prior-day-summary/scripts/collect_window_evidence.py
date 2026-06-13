#!/usr/bin/env python3
"""Collect deterministic prior-day evidence from git and changelog state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


LOG_FORMAT = "%H%x09%ad%x09%D%x09%s"


@dataclass
class CommitRecord:
    sha: str
    authored_at: str
    decorations: str
    subject: str


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True, stderr=subprocess.DEVNULL).strip()


def try_run(cmd: list[str], cwd: Path) -> str:
    try:
        return run(cmd, cwd)
    except Exception:
        return ""


def parse_log(output: str) -> list[CommitRecord]:
    records: list[CommitRecord] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        records.append(CommitRecord(*parts))
    return records


def subject_is_docs_only(subject: str) -> bool:
    lowered = subject.lower()
    prefixes = (
        "docs:",
        "docs(",
        "doc:",
        "plan:",
        "plan(",
        "report:",
        "report(",
        "design:",
        "design(",
        "spike:",
        "spike(",
    )
    return lowered.startswith(prefixes)


def parse_changelog(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    heading = re.compile(r"^## \[(?P<version>[^\]]+)\](?: - (?P<date>\d{4}-\d{2}-\d{2}))?$")
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        match = heading.match(line.strip())
        if match:
            entries.append(
                {
                    "path": str(path),
                    "version": match.group("version"),
                    "date": match.group("date") or "",
                }
            )
    return entries


def classify(
    all_commits: list[CommitRecord],
    mainline_commits: list[CommitRecord],
    merge_commits: list[CommitRecord],
    changelog_hits: list[dict[str, str]],
) -> tuple[str, str]:
    if not all_commits and not merge_commits and not changelog_hits and not mainline_commits:
        return "empty_day", "No commits, merges, or dated changelog hits were found in the target window."
    if mainline_commits or any(hit["date"] for hit in changelog_hits):
        return "shipped", "Mainline or dated release evidence exists for the target window."
    if all_commits and all(subject_is_docs_only(commit.subject) for commit in all_commits):
        return "docs_only", "Window commits appear docs-only or planning-only."
    return "branch_local", "Window activity exists, but it is not proven shipped on main."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Target date in YYYY-MM-DD form.")
    parser.add_argument("--since", help="Explicit git --since value.")
    parser.add_argument("--until", help="Explicit git --until value.")
    parser.add_argument("--cwd", default=".", help="Repository path. Defaults to current directory.")
    parser.add_argument("--out", help="Optional output JSON path.")
    args = parser.parse_args()

    if not args.date and not (args.since and args.until):
        parser.error("Pass --date or both --since and --until.")

    repo = Path(args.cwd).resolve()
    if args.date:
        target = date.fromisoformat(args.date)
        since = f"{target.isoformat()} 00:00:00"
        until = f"{(target + timedelta(days=1)).isoformat()} 00:00:00"
        target_date = target.isoformat()
    else:
        since = args.since
        until = args.until
        target_date = args.since.split(" ", 1)[0]

    log_args = ["git", "log", "--all", f"--since={since}", f"--until={until}", "--date=iso-local", f"--pretty=format:{LOG_FORMAT}"]
    merge_args = ["git", "log", "--all", "--merges", f"--since={since}", f"--until={until}", "--date=iso-local", "--pretty=format:%H%x09%ad%x09%s"]
    main_args = ["git", "log", "origin/main", f"--since={since}", f"--until={until}", "--date=iso-local", f"--pretty=format:{LOG_FORMAT}"]

    all_commits = parse_log(try_run(log_args, repo))
    mainline_commits = parse_log(try_run(main_args, repo))
    merge_records = [line.split("\t", 2) for line in try_run(merge_args, repo).splitlines() if line.strip()]
    merge_commits = [{"sha": p[0], "authored_at": p[1], "subject": p[2]} for p in merge_records if len(p) == 3]

    branch_name = try_run(["git", "branch", "--show-current"], repo)
    divergence = try_run(["git", "rev-list", "--left-right", "--count", "origin/main...HEAD"], repo) or "unknown"
    tags = [tag for tag in try_run(["git", "tag", "--sort=-creatordate"], repo).splitlines()[:10] if tag]

    changelog_paths = [repo / "CHANGELOG.md", repo / "docs" / "CHANGELOG.md"]
    changelog_entries = [entry for path in changelog_paths for entry in parse_changelog(path)]
    changelog_hits = [entry for entry in changelog_entries if entry.get("date") == target_date]

    classification, rationale = classify(all_commits, mainline_commits, merge_commits, changelog_hits)

    payload: dict[str, Any] = {
        "repo": repo.name,
        "repo_path": str(repo),
        "target_date": target_date,
        "since": since,
        "until": until,
        "current_branch": branch_name,
        "branch_divergence": divergence,
        "latest_tags": tags,
        "classification": classification,
        "classification_rationale": rationale,
        "window_commit_count": len(all_commits),
        "mainline_commit_count": len(mainline_commits),
        "merge_count": len(merge_commits),
        "window_commits": [asdict(record) for record in all_commits],
        "mainline_commits": [asdict(record) for record in mainline_commits],
        "merge_commits": merge_commits,
        "changelog_hits": changelog_hits,
        "generated_at": datetime.now().astimezone().isoformat(),
    }

    output = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
