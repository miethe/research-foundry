#!/usr/bin/env python3
"""Authoring-time plan gate — Shipped Work Ledger M4 L1 (FR-12).

Checks a newly-authored plan file for the two things a plan must carry the moment it is
authored, per the M4 plan AC ("A new plan with an invalid status or missing binding fails the
gate"):

1. **status validity** — the top-level ``status`` value is a NodeStatus or a losslessly-
   resolvable alias. Reuses ``validate-plan-frontmatter.py``'s own ``process_file`` (and, through
   it, ``_status_aliases.py``) rather than re-implementing the enum or the alias map. An alias is
   a WARNING (resolvable via ``validate-plan-frontmatter.py --apply``); a hand-review/unknown
   value is a VIOLATION.
2. **binding presence** — the file carries a usable join key: ``feature_slug`` AND at least one
   of (``itt_node_id``, ``intenttree_tree``). Missing ``feature_slug`` is a VIOLATION — it is the
   join key the Shipped Work Ledger program exists to establish. Missing BOTH node/tree ids is a
   WARNING, never a violation: a plan is legitimately authored before its tree exists, and
   ``stamp-plan-binding.py`` back-fills them later.

D-M4-1 (orchestrator decision): "fails the gate" means this script exits non-zero and names the
file + field + bad/missing value — NOT a blocking git hook or CI check. Nothing here consumes
that exit code to reject a commit; the caller (the planning workflow, a human) decides. Advisory,
same posture as ``validate-plan-frontmatter.py``.

Read-only. This script never writes — the autofix path already lives in
``validate-plan-frontmatter.py --apply`` (status) / ``stamp-plan-binding.py --apply`` (binding).

EXIT CODES
----------
- 0 — clean: no violations (warnings may be present and are printed).
- 2 — one or more violations, each naming the file + field + bad/missing value.
- 1 — usage / internal error (path missing, no markdown files, unreadable file).

Stdlib + optional PyYAML (inherited from validate-plan-frontmatter.py's Schema loader). Python
3.10+ floor (must run on the node's 3.11 — no 3.12-only syntax).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import _slug_resolution as sr  # noqa: E402
import _status_aliases as sa  # noqa: E402


def _load_hyphenated_module(name: str, filename: str) -> Any:
    """Import a hyphen-named sibling script as a module (hyphens aren't valid identifiers)."""
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The actual linter module — reused (not re-implemented) for status-line discovery + alias
# resolution. `_vpf.process_file` already does the frontmatter-bounds scan, the top-level
# `status:` line match, and the `_status_aliases.resolve` call; this script only interprets the
# category it returns.
_vpf = _load_hyphenated_module("_check_plan_authoring_vpf", "validate-plan-frontmatter.py")


class FileFinding:
    """Violations + warnings for one file. Empty of both == clean."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def add_violation(self, field: str, detail: str) -> None:
        self.violations.append({"field": field, "detail": detail})

    def add_warning(self, field: str, detail: str) -> None:
        self.warnings.append({"field": field, "detail": detail})


def check_file(path: Path, schema: Any) -> FileFinding:
    """Run both checks against one plan file. Read-only."""
    finding = FileFinding(path)

    # --- (1) status validity — delegate entirely to the real linter's file processing. ---
    status_result = _vpf.process_file(path, schema, apply=False)
    if status_result.state == "ok":
        if status_result.category == sa.HAND_REVIEW:
            finding.add_violation(
                "status",
                f"{status_result.value!r} is neither a NodeStatus nor a known alias "
                "(run validate-plan-frontmatter.py for the full corpus report)",
            )
        elif status_result.category == sa.ALIAS:
            finding.add_warning(
                "status",
                f"{status_result.value!r} resolves to {status_result.to_status!r} — "
                "run validate-plan-frontmatter.py --apply to normalize",
            )
    # state in {no_status, no_frontmatter, unreadable}: advisory posture, mirrors the linter —
    # not a status violation here. A missing frontmatter block surfaces below as a missing
    # feature_slug, which IS a violation.

    # --- (2) binding presence. ---
    scalars = sr.scan_frontmatter_scalars(path)
    feature_slug = scalars.get("feature_slug")
    if not feature_slug:
        finding.add_violation(
            "feature_slug",
            "missing — this is the join key the Shipped Work Ledger program exists to establish",
        )
    elif not (scalars.get("itt_node_id") or scalars.get("intenttree_tree")):
        finding.add_warning(
            "itt_node_id/intenttree_tree",
            "no node/tree binding yet — expected before the tree exists; "
            "stamp-plan-binding.py backfills this once one is created",
        )

    return finding


# --------------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------------
def _iter_targets(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.md"))


def _build_summary(findings: list[FileFinding]) -> dict[str, int]:
    return {
        "files_scanned": len(findings),
        "files_with_violations": sum(1 for f in findings if f.violations),
        "files_with_warnings": sum(1 for f in findings if f.warnings),
        "violations": sum(len(f.violations) for f in findings),
        "warnings": sum(len(f.warnings) for f in findings),
    }


def _emit_human(findings: list[FileFinding], summary: dict[str, int], root: Path) -> None:
    print(f"[check-plan-authoring] CHECK {root}")
    for f in findings:
        if not f.violations and not f.warnings:
            continue
        print(f"  {f.path}")
        for v in f.violations:
            print(f"    VIOLATION {v['field']}: {v['detail']}")
        for w in f.warnings:
            print(f"    warning   {w['field']}: {w['detail']}")
    print("\n  summary:")
    for k, v in summary.items():
        print(f"    {k}={v}")
    print(
        "\n  advisory only (D-M4-1) — this exit code does not block a commit or CI; "
        "the caller decides."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Authoring-time gate for a plan file (FR-12) — checks status validity + "
                    "join-key binding presence. Advisory (D-M4-1): never blocks git/CI. "
                    "Read-only; never writes."
    )
    ap.add_argument("path", help="a plan .md file, or a directory to recurse (*.md)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        sys.stderr.write(f"error: path not found: {root}\n")
        return 1

    schema = _vpf.Schema.load(SCRIPT_DIR)
    targets = _iter_targets(root)
    if not targets:
        sys.stderr.write(f"error: no markdown files under {root}\n")
        return 1

    findings = [check_file(p, schema) for p in targets]
    summary = _build_summary(findings)
    has_violations = any(f.violations for f in findings)

    if args.json:
        payload = {
            "mode": "check",
            "root": str(root),
            "summary": summary,
            "violations": [
                {"file": str(f.path), **v} for f in findings for v in f.violations
            ],
            "warnings": [
                {"file": str(f.path), **w} for f in findings for w in f.warnings
            ],
            "exit": 2 if has_violations else 0,
        }
        print(json.dumps(payload, indent=2))
    else:
        _emit_human(findings, summary, root)

    return 2 if has_violations else 0


if __name__ == "__main__":
    sys.exit(main())
