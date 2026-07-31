#!/usr/bin/env python3
"""Plan-frontmatter linter — canonical `status` enforcement + additive autofix.

This is the linter the launchpad plan-frontmatter contract has long referenced but never shipped
(`docs/agentic-operator/contracts/frontmatter-schema.md` §5c, §7 item 9). It enforces that a plan
file's top-level ``status`` is one of the ratified 15 IntentTree ``NodeStatus`` values (§4, OQ-2)
and can additively normalize legacy / synonym spellings via the shared alias map
(``_status_aliases.py``).

WHAT IT DOES
------------
- Derives its MUST / SHOULD / MAY field sets by parsing the machine-readable YAML block in
  ``.claude/skills/planning/references/plan-frontmatter-schema.md`` (the block containing
  ``must_set_plan:``); falls back to a hardcoded mirror if that doc or PyYAML is unavailable.
- For every plan file, classifies its top-level ``status`` value:
    * VALID       — already a NodeStatus → untouched.
    * ALIAS       — a known synonym → losslessly resolvable to a NodeStatus (autofix target).
    * HAND-REVIEW — neither NodeStatus nor alias (incl. the known placeholders) → a VIOLATION,
                    never auto-mapped, reported naming the file + bad value.
- Reports absent plan-level MUST fields as **advisory** (never affects the exit code, per the v1
  advisory contract — the schema doc's linter contract §1).
- Reports **conditional-required** gaps as advisory (gate-tiering v4.1): per the schema doc's
  ``conditional_required:`` block, a ``wave_plan.phases[]`` entry whose ``gate_lens`` carries two or
  more reviewer lenses must name the trigger that earned the second one in ``gate_lens_reason``
  (``untrusted-input`` | ``authz-boundary`` | ``irreversible-outward`` | ``ambiguity-tie``). A
  two-lens phase with no named trigger is a classification error, not a cautious default. This
  check needs PyYAML and a parseable frontmatter mapping; where either is missing it silently
  reports nothing rather than guessing.

MODES
-----
- default (CHECK) — report only; never writes.
- ``--apply``     — additive, format-preserving autofix: rewrites ONLY the value token of the
                    top-level ``status:`` line in place (preserving indent / quoting / trailing
                    comment) and, when the alias implies one AND the file lacks it, inserts a
                    ``planning_maturity:`` line immediately after (mirrors
                    ``planning/scripts/enrich_frontmatter.py`` — textual insert, no re-serialize).
                    VALID statuses are left entirely untouched (no planning_maturity added).
- ``--json``      — machine-readable summary (per-value would-change counts, violations, changes).

EXIT CODES  (mirrors provision_artifacts.py's correctness hard-gate; satisfies the M1 AC)
-----------
- 0 — clean: every processed file's status is a NodeStatus OR a losslessly-resolvable alias, with
      no hand-review cases.
- 2 — one or more status violations (hand-review / invalid / unresolvable), each named.
- 1 — usage / internal error (path missing, no markdown files, unreadable file).

Advisory posture (v1): it reports, the caller decides. The exit code distinguishes clean vs
violations so a gate can consume it, but this tool does not itself block a commit.

Stdlib + optional PyYAML. Python 3.10+ floor (must run on the node's 3.11).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Import the shared status vocabulary. When run as a script, the script's own directory is on
# sys.path[0], so this bare import resolves regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _status_aliases as sa  # noqa: E402

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised only where PyYAML is absent
    yaml = None  # type: ignore

# --------------------------------------------------------------------------------------------
# Hardcoded MUST/SHOULD/MAY mirror — used only when the schema doc or PyYAML is unavailable.
# Mirrors plan-frontmatter-schema.md "Machine-readable schema" block (the thin six).
# --------------------------------------------------------------------------------------------
FALLBACK_MUST_PLAN = ["it_schema", "feature_slug", "status", "tier", "priority", "effort"]
FALLBACK_EFFORT_ALIASES = ["points", "effort_estimate", "estimated_points"]
FALLBACK_MUST_TASK = ["node_type"]

# gate-tiering v4.1 — mirrors the schema doc's ``conditional_required:`` block. A phase carrying
# two or more reviewer lenses MUST name the trigger that earned the second one; a two-lens phase
# with no named trigger is a classification error, not a cautious default. Advisory in v1, same
# posture as the MUST set.
FALLBACK_CONDITIONAL_REQUIRED = [
    {
        "field": "gate_lens_reason",
        "level": "phase",
        "when": {"field": "gate_lens", "min_len": 2},
        "allowed": ["untrusted-input", "authz-boundary", "irreversible-outward", "ambiguity-tie"],
    }
]

SCHEMA_DOC_RELPATH = ".claude/skills/planning/references/plan-frontmatter-schema.md"

# Only the TOP-LEVEL (column-0) status key — never a nested decisions[]/tasks[]/open_questions[]
# status. Leading-whitespace variants are deliberately NOT matched.
STATUS_LINE_RE = re.compile(r"^(?P<prefix>status:[ \t]*)(?P<body>.*)$")
TOP_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):")


# --------------------------------------------------------------------------------------------
# Schema-block discovery + parsing
# --------------------------------------------------------------------------------------------
def _find_repo_root(start: Path) -> Path | None:
    """Walk upward from *start* looking for the schema doc; return the repo root that holds it."""
    for parent in [start, *start.parents]:
        if (parent / SCHEMA_DOC_RELPATH).is_file():
            return parent
    return None


def _safe_yaml(text: str) -> Any:
    if yaml is None:
        return None
    try:
        return yaml.safe_load(text)
    except Exception:
        return None


def _extract_schema_block(doc_text: str) -> dict[str, Any] | None:
    """Return the parsed machine-readable YAML block (the one carrying ``must_set_plan``).

    Iterates every ```yaml fenced block and returns the first carrying ``must_set_plan``. The
    doc's full block is intentionally NOT valid PyYAML — its ``fields:`` list uses flow scalars
    like ``type: path[]`` (bare ``[]`` breaks the flow parser). So: try a full parse first, and if
    that fails, parse just the header portion above the ``fields:`` line — which holds the
    load-bearing MUST sets (``must_set_plan`` / ``effort_aliases`` / ``must_set_task``) and IS
    valid YAML. Returns None if even the header is unparseable (→ hardcoded fallback).
    """
    if yaml is None:
        return None
    for m in re.finditer(r"```ya?ml\s*\n(.*?)```", doc_text, re.DOTALL):
        body = m.group(1)
        if "must_set_plan" not in body:
            continue
        data = _safe_yaml(body)
        if isinstance(data, dict) and "must_set_plan" in data:
            return data
        header = re.split(r"^fields:\s*$", body, maxsplit=1, flags=re.M)[0]
        data = _safe_yaml(header)
        if isinstance(data, dict) and "must_set_plan" in data:
            return data
    return None


class Schema:
    """The MUST/SHOULD/MAY field sets, sourced from the schema doc or the fallback mirror."""

    def __init__(self, must_plan: list[str], effort_aliases: list[str],
                 must_task: list[str], should: list[str], may: list[str], source: str,
                 conditional_required: list[dict[str, Any]] | None = None) -> None:
        self.must_plan = must_plan
        self.effort_aliases = effort_aliases
        self.must_task = must_task
        self.should = should
        self.may = may
        self.source = source  # "parsed" | "fallback"
        self.conditional_required = (
            conditional_required if conditional_required is not None
            else [dict(r) for r in FALLBACK_CONDITIONAL_REQUIRED]
        )

    @classmethod
    def load(cls, script_dir: Path) -> "Schema":
        repo_root = _find_repo_root(script_dir)
        if repo_root is not None:
            doc = repo_root / SCHEMA_DOC_RELPATH
            try:
                block = _extract_schema_block(doc.read_text(encoding="utf-8"))
            except OSError:
                block = None
            if block is not None:
                fields = block.get("fields") or []
                should = sorted({f["name"] for f in fields
                                 if isinstance(f, dict) and f.get("tier") == "should"})
                may = sorted({f["name"] for f in fields
                              if isinstance(f, dict) and f.get("tier") == "may"})
                return cls(
                    must_plan=list(block.get("must_set_plan") or FALLBACK_MUST_PLAN),
                    effort_aliases=list(block.get("effort_aliases") or FALLBACK_EFFORT_ALIASES),
                    must_task=list(block.get("must_set_task") or FALLBACK_MUST_TASK),
                    should=should,
                    may=may,
                    source="parsed",
                    conditional_required=list(block.get("conditional_required")
                                              or FALLBACK_CONDITIONAL_REQUIRED),
                )
        return cls(
            must_plan=list(FALLBACK_MUST_PLAN),
            effort_aliases=list(FALLBACK_EFFORT_ALIASES),
            must_task=list(FALLBACK_MUST_TASK),
            should=[],
            may=[],
            source="fallback",
        )


# --------------------------------------------------------------------------------------------
# Frontmatter + line parsing (format-preserving; no full re-serialize)
# --------------------------------------------------------------------------------------------
def _frontmatter_bounds(text: str) -> tuple[int, int] | None:
    """Return (open_end, close_start) byte offsets of the frontmatter *content*, or None.

    ``open_end`` = index just after the opening ``---\\n``; ``close_start`` = index of the ``\\n``
    preceding the closing ``---``. Mirrors enrich_frontmatter.py's bounds discipline.
    """
    if not text.startswith("---"):
        return None
    # opening fence must be its own line
    first_nl = text.find("\n")
    if first_nl == -1 or text[:first_nl].strip() != "---":
        return None
    close = text.find("\n---", first_nl)
    if close == -1:
        return None
    return first_nl + 1, close


def _split_line_ending(line: str) -> tuple[str, str]:
    for end in ("\r\n", "\n", "\r"):
        if line.endswith(end):
            return line[: -len(end)], end
    return line, ""


def _split_value_and_comment(body: str) -> tuple[str, str]:
    """Split a ``status:`` line body into (value_token, preserved_suffix).

    ``value_token`` keeps any surrounding quotes but no surrounding whitespace. A YAML inline
    comment (whitespace + ``#`` ... to EOL) is preserved verbatim in ``preserved_suffix``
    (including the whitespace before it); pure trailing whitespace on an uncommented line is
    dropped on rewrite.
    """
    in_quote: str | None = None
    ci: int | None = None
    for i, ch in enumerate(body):
        if in_quote is not None:
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            in_quote = ch
            continue
        if ch == "#" and (i == 0 or body[i - 1] in " \t"):
            ci = i
            break
    if ci is None:
        value_region, comment = body, ""
    else:
        value_region, comment = body[:ci], body[ci:]
    stripped = value_region.rstrip()
    ws = value_region[len(stripped):]
    suffix = (ws + comment) if comment else ""
    return stripped, suffix


def _detect_quote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[0]
    return ""


def _top_level_keys(lines: list[str], fm_start_idx: int, fm_end_idx: int) -> set[str]:
    """Column-0 mapping keys within the frontmatter line range [fm_start_idx, fm_end_idx)."""
    keys: set[str] = set()
    for i in range(fm_start_idx, fm_end_idx):
        content, _ = _split_line_ending(lines[i])
        if content and content[0] not in (" ", "\t", "#", "-"):
            m = TOP_KEY_RE.match(content)
            if m:
                keys.add(m.group("key"))
    return keys


# --------------------------------------------------------------------------------------------
# Per-file processing
# --------------------------------------------------------------------------------------------
class FileResult:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.state = "ok"           # ok | no_frontmatter | no_status | unreadable
        self.category: str | None = None      # valid | alias | hand_review
        self.value: str | None = None         # the raw value token as found
        self.to_status: str | None = None     # canonical target (alias/valid)
        self.planning_maturity: str | None = None  # to add (alias only, if absent)
        self.pm_present = False
        self.applied = False
        self.missing_must: list[str] = []
        # gate-tiering v4.1 — advisory conditional-required findings, e.g. a two-lens phase with
        # no gate_lens_reason. Never affects the exit code (v1 advisory contract).
        self.conditional_gaps: list[str] = []


def _check_conditional_required(fm_text: str, schema: Schema) -> list[str]:
    """Advisory conditional-required checks over ``wave_plan.phases[]`` (gate-tiering v4.1).

    Read-only and best-effort: needs PyYAML and a parseable frontmatter mapping. When either is
    unavailable it returns no findings rather than guessing — a silent skip, never a false
    positive. Only ``level: phase`` rules are evaluated in v1; that is the only level any rule
    currently uses.
    """
    rules = [r for r in schema.conditional_required
             if isinstance(r, dict) and r.get("level") == "phase"]
    if not rules:
        return []

    data = _safe_yaml(fm_text)
    if not isinstance(data, dict):
        return []
    wave_plan = data.get("wave_plan")
    if not isinstance(wave_plan, dict):
        return []
    phases = wave_plan.get("phases")
    if not isinstance(phases, list):
        return []

    gaps: list[str] = []
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            continue
        pid = phase.get("id") or f"phases[{idx}]"
        for rule in rules:
            when = rule.get("when") or {}
            trigger_field = when.get("field")
            min_len = when.get("min_len")
            if not trigger_field or not isinstance(min_len, int):
                continue
            trigger_value = phase.get(trigger_field)
            if not isinstance(trigger_value, list) or len(trigger_value) < min_len:
                continue

            required_field = rule.get("field")
            allowed = rule.get("allowed") or []
            actual = phase.get(required_field)
            if actual is None or (isinstance(actual, str) and not actual.strip()):
                gaps.append(
                    f"{pid}: {trigger_field} has {len(trigger_value)} entries "
                    f"({', '.join(str(v) for v in trigger_value)}) but {required_field} is absent"
                )
            elif allowed and actual not in allowed:
                gaps.append(
                    f"{pid}: {required_field}={actual!r} is not one of {', '.join(allowed)}"
                )
    return gaps


def process_file(path: Path, schema: Schema, apply: bool) -> FileResult:
    res = FileResult(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        res.state = "unreadable"
        return res

    bounds = _frontmatter_bounds(text)
    if bounds is None:
        res.state = "no_frontmatter"
        return res

    lines = text.splitlines(keepends=True)
    # Map byte bounds to line indices.
    open_end, close_start = bounds
    # Compute line index containing open_end (first frontmatter content line) and close_start.
    fm_start_idx = text.count("\n", 0, open_end)
    fm_end_idx = text.count("\n", 0, close_start) + 1  # line with closing '---' excluded below
    # close_start points at the '\n' before '---'; the '---' line itself sits at fm_end_idx.
    fm_end_idx = min(fm_end_idx, len(lines))

    keys_present = _top_level_keys(lines, fm_start_idx, fm_end_idx)
    res.pm_present = "planning_maturity" in keys_present

    # Advisory MUST-presence: effort is satisfied by any effort alias.
    for field in schema.must_plan:
        if field == "effort":
            if not any(a in keys_present for a in schema.effort_aliases):
                res.missing_must.append("effort(points/effort_estimate/estimated_points)")
        elif field not in keys_present:
            res.missing_must.append(field)

    # Advisory conditional-required (gate-tiering v4.1) — nested, so it parses the frontmatter
    # body rather than the top-level key list.
    res.conditional_gaps = _check_conditional_required(
        text[open_end:close_start], schema
    )

    # Locate the top-level status line.
    status_idx: int | None = None
    for i in range(fm_start_idx, fm_end_idx):
        content, _ = _split_line_ending(lines[i])
        if STATUS_LINE_RE.match(content):
            status_idx = i
            break

    if status_idx is None:
        res.state = "no_status"
        return res

    content, ending = _split_line_ending(lines[status_idx])
    m = STATUS_LINE_RE.match(content)
    assert m is not None
    prefix = m.group("prefix")
    value_token, suffix = _split_value_and_comment(m.group("body"))
    res.value = value_token

    to_status, planning_maturity, category = sa.resolve(value_token)
    res.category = category
    res.to_status = to_status
    if category == sa.ALIAS:
        res.planning_maturity = planning_maturity if not res.pm_present else None

    if apply and category == sa.ALIAS and to_status is not None:
        quote = _detect_quote(value_token)
        new_status_line = f"{prefix}{quote}{to_status}{quote}{suffix}{ending}"
        lines[status_idx] = new_status_line
        insert_offset = 1
        if res.planning_maturity is not None:
            # Insert immediately after the status line; column-0 like the plan-level status key.
            pm_line = f"planning_maturity: {res.planning_maturity}{ending or os.linesep}"
            lines.insert(status_idx + 1, pm_line)
            insert_offset = 2
        path.write_text("".join(lines), encoding="utf-8")
        res.applied = True
        _ = insert_offset  # documented for clarity; not otherwise needed
    return res


# --------------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------------
def _iter_targets(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.md"))


def _build_summary(results: list[FileResult]) -> dict[str, Any]:
    would_change: dict[str, int] = {}
    pm_adds = 0
    counts = {"valid": 0, "alias": 0, "hand_review": 0,
              "no_status": 0, "no_frontmatter": 0, "unreadable": 0}
    for r in results:
        if r.state != "ok":
            counts[r.state] = counts.get(r.state, 0) + 1
            continue
        cat = r.category or sa.HAND_REVIEW  # non-None on the ok path; narrows for the type checker
        counts[cat] = counts.get(cat, 0) + 1
        if r.category == sa.ALIAS:
            key = sa.normalize_token(r.value or "")
            would_change[key] = would_change.get(key, 0) + 1
            if r.planning_maturity is not None:
                pm_adds += 1
    return {
        "files_scanned": len(results),
        "with_status": sum(1 for r in results if r.state == "ok"),
        "valid": counts["valid"],
        "alias": counts["alias"],
        "hand_review": counts["hand_review"],
        "no_status": counts["no_status"],
        "no_frontmatter": counts["no_frontmatter"],
        "unreadable": counts["unreadable"],
        "would_change_by_value": dict(sorted(would_change.items())),
        "would_add_planning_maturity": pm_adds,
        "applied_changes": sum(1 for r in results if r.applied),
    }


def _emit_human(results: list[FileResult], schema: Schema, summary: dict[str, Any],
                apply: bool, root: Path) -> None:
    verb = "APPLY" if apply else "CHECK"
    print(f"[validate-plan-frontmatter] {verb} {root}  (schema: {schema.source})")
    for r in results:
        if r.state != "ok":
            continue
        if r.category == sa.VALID:
            continue  # quiet on already-canonical files
        if r.category == sa.ALIAS:
            pm = f" (+planning_maturity: {r.planning_maturity})" if r.planning_maturity else ""
            tag = "FIXED" if r.applied else "would-fix"
            print(f"  {r.path}\n    status: {r.value} -> {r.to_status}{pm}  [{tag}]")
        elif r.category == sa.HAND_REVIEW:
            print(f"  {r.path}\n    status: {r.value!r}  [HAND-REVIEW VIOLATION — never auto-mapped]")
    s = summary
    print("\n  summary:")
    print(f"    files_scanned={s['files_scanned']} with_status={s['with_status']} "
          f"valid={s['valid']} alias={s['alias']} hand_review={s['hand_review']} "
          f"no_status={s['no_status']} no_frontmatter={s['no_frontmatter']}")
    if s["would_change_by_value"]:
        label = "changed" if apply else "would change"
        print(f"    {label} by value:")
        for val, n in s["would_change_by_value"].items():
            print(f"      {val:<40} {n}")
        print(f"    planning_maturity {'added' if apply else 'would add'}: "
              f"{s['would_add_planning_maturity']}")
    hand = [r for r in results if r.state == "ok" and r.category == sa.HAND_REVIEW]
    if hand:
        print(f"    HAND-REVIEW files ({len(hand)}) — resolve manually, never auto-map:")
        for r in hand:
            print(f"      {r.path}  (status: {r.value!r})")

    # gate-tiering v4.1 — advisory only; does not affect the exit code.
    cond = [r for r in results if r.state == "ok" and r.conditional_gaps]
    if cond:
        print(f"    ADVISORY — gate-lens classification gaps ({len(cond)} file(s)):")
        for r in cond:
            print(f"      {r.path}")
            for gap in r.conditional_gaps:
                print(f"        {gap}")
        print("      A phase carrying 2+ reviewer lenses must name the trigger that earned the")
        print("      second one (gate_lens_reason). See")
        print("      .claude/skills/dev-execution/references/gate-risk-classes.md §2.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Lint plan-frontmatter `status` against the ratified NodeStatus enum "
                    "(+ additive alias autofix).")
    ap.add_argument("path", help="a plan .md file, or a directory to recurse (*.md)")
    ap.add_argument("--apply", action="store_true",
                    help="autofix resolvable aliases in place (default: check-only)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        sys.stderr.write(f"error: path not found: {root}\n")
        return 1

    schema = Schema.load(Path(__file__).resolve().parent)
    targets = _iter_targets(root)
    if not targets:
        sys.stderr.write(f"error: no markdown files under {root}\n")
        return 1

    results = [process_file(p, schema, args.apply) for p in targets]
    summary = _build_summary(results)
    violations = [r for r in results if r.state == "ok" and r.category == sa.HAND_REVIEW]

    if args.json:
        payload = {
            "mode": "apply" if args.apply else "check",
            "root": str(root),
            "schema_source": schema.source,
            "must_set_plan": schema.must_plan,
            "effort_aliases": schema.effort_aliases,
            "summary": summary,
            "violations": [
                {"file": str(r.path), "value": r.value, "category": r.category}
                for r in violations
            ],
            "changes": [
                {"file": str(r.path), "from": r.value, "to": r.to_status,
                 "planning_maturity": r.planning_maturity, "applied": r.applied}
                for r in results if r.state == "ok" and r.category == sa.ALIAS
            ],
            "advisory_must_gaps": [
                {"file": str(r.path), "missing": r.missing_must}
                for r in results if r.state == "ok" and r.missing_must
            ],
            # gate-tiering v4.1 — advisory, does NOT affect "exit" below.
            "advisory_conditional_gaps": [
                {"file": str(r.path), "gaps": r.conditional_gaps}
                for r in results if r.state == "ok" and r.conditional_gaps
            ],
            "exit": 2 if violations else 0,
        }
        print(json.dumps(payload, indent=2))
    else:
        _emit_human(results, schema, summary, args.apply, root)

    return 2 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
