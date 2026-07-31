#!/usr/bin/env python3
"""IntentTree SDLC capture/sync — orchestrates plan & progress artifacts into IntentTree nodes.

Thin shim (normalization is server-side — DI-103/104/105 resolved 2026-06-20)
----------------------------------------------------------------------------
The backend now parses raw file content (PyYAML) and owns ALL task normalization: title
fallback from description (DI-104), points-alias/unit parsing (DI-104), and status→progress
derivation (DI-105). This script no longer normalizes; it only *orchestrates* the native server
sync path — the same ``/source-artifacts`` register + ``/work-item-sync/import`` endpoints
``itt sync import`` uses. It discovers which files belong to which feature (aggregating a
feature's phase files, and capturing catch-all dirs per-file — DI-107), then POSTs the raw
aggregated tasks for the backend to normalize and graft.

Retirement: this shim is slated for removal after a burn-in release (OQ-4; see
``docs/project_plans/design-specs/awpr-v2-shim-removal.md``). Source of truth stays the markdown:
this only does source → node (a derived projection).

Modes
-----
  # one artifact (used by the auto-sync hook on a status write):
  intenttree_capture.py sync   <plan-or-progress-file> --tree <tree_id> [--apply]

  # backfill every in-flight feature in a repo (one-time / periodic):
  intenttree_capture.py backfill --repo-root <path> --tree <tree_id> [--apply] [--cutoff YYYY-MM-DD]

Config (CLI flag > env > default):
  --api-url   / INTENTTREE_API_URL    (default http://10.42.10.76:8032)
  --workspace / INTENTTREE_WORKSPACE
  --tree      / INTENTTREE_TREE

A feature = one plan/PRD (the container, idempotency key = its path) + all tasks aggregated
from its `.claude/progress/<feature_slug>/phase-*.md` files. Each task is grafted under a
"Phase N" container beneath the feature. Re-running is idempotent (keyed on
(source_artifact_id, source_task_id)); completed leaves are marked done so rollups are faithful.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("intenttree_capture: PyYAML required (pip install pyyaml)\n")
    sys.exit(2)

DEFAULT_API = os.environ.get("INTENTTREE_API_URL", "http://10.42.10.76:8032")
COMPLETE = {"completed", "complete", "done", "superseded", "archived",
            "cancelled", "merged", "shipped", "resolved"}
VALID_KINDS = {"prd", "implementation_plan", "phase_plan", "feature_contract", "spike",
               "design_spec", "progress", "worknote", "report", "human_brief",
               "meta_plan", "exploration_charter", "decisions_block", "context_file",
               "charter", "other"}


# --------------------------------------------------------------------------- HTTP
def _req(api: str, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(api + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None


# --------------------------------------------------------------------- frontmatter
def load_fm(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        fm = yaml.safe_load(text[3:end])
        return fm if isinstance(fm, dict) else {}
    except Exception:
        return {}


def to_date(v: Any) -> datetime.date | None:
    if v is None:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(v))
    if not m:
        return None
    try:
        return datetime.date(int(m[1]), int(m[2]), int(m[3]))
    except Exception:
        return None


def phase_label(fm: dict, path: Path) -> str:
    p = fm.get("phase")
    if p is not None and str(p).strip():
        return f"Phase {p}"
    m = re.search(r"phase-(\w+)", path.name)
    return f"Phase {m.group(1)}" if m else "Phase 1"


def _collect_task(t: dict, plabel: str, seen: set[str]) -> dict | None:
    """Forward a raw progress-file task with orchestration-only fixups (thin shim).

    The backend owns ALL normalization (title fallback, points/unit parsing, status→progress —
    DI-104/105). This only ensures task *identity* for aggregation, forwarding every other field
    verbatim for the backend to normalize:
    - require an id (skip rows without one),
    - disambiguate ids that repeat across a feature's phase files (``Phase1-QF-1``),
    - tag the originating phase so the backend builds the right Phase container,
    - default a missing status so the in-flight filter has a value to read.
    """
    tid = t.get("id") or t.get("task_id") or t.get("key")
    if not tid:
        return None
    tid = str(tid)
    if tid in seen:
        tid = f"{plabel.replace(' ', '')}-{tid}"
    seen.add(tid)
    out: dict[str, Any] = dict(t)
    out["id"] = tid
    out["status"] = t.get("status") or "not_started"
    out.setdefault("phase", plabel)
    return out


# ------------------------------------------------------------------- feature build
def tasks_from_progress_dir(
    prog_dir: Path,
) -> tuple[list[dict], str | None, str | None, datetime.date | None]:
    """Aggregate tasks across a feature's phase-progress files (backend normalizes)."""
    tasks: list[dict] = []
    seen: set[str] = set()
    feature_slug = plan_ref = None
    newest = None
    for pf in sorted(prog_dir.glob("*.md")):
        fm = load_fm(pf)
        upd = to_date(fm.get("updated")) or to_date(fm.get("created"))
        if upd and (newest is None or upd > newest):
            newest = upd
        feature_slug = fm.get("feature_slug") or feature_slug
        plan_ref = plan_ref or fm.get("plan_ref") or fm.get("prd_ref")
        raw = fm.get("tasks")
        if not isinstance(raw, list):
            continue
        pl = phase_label(fm, pf)
        for rt in raw:
            if isinstance(rt, dict):
                nt = _collect_task(rt, pl, seen)
                if nt:
                    tasks.append(nt)
    return tasks, feature_slug, plan_ref, newest


def feature_from_file(path: Path) -> dict | None:
    """Build a feature payload from a single plan/progress file's own tasks[]."""
    fm = load_fm(path)
    raw = fm.get("tasks")
    if not isinstance(raw, list) or not raw:
        return None
    seen: set[str] = set()
    pl = phase_label(fm, path)
    tasks = [nt for rt in raw if isinstance(rt, dict) and (nt := _collect_task(rt, pl, seen))]
    if not tasks:
        return None
    slug = fm.get("feature_slug") or path.stem
    return {
        "slug": slug,
        "title": fm.get("title") or slug.replace("-", " ").title(),
        "kind": (fm.get("doc_type") or fm.get("kind") or "implementation_plan"),
        "artifact_path": str(path),
        "tasks": tasks,
    }


def discover_features(repo_root: Path, cutoff: datetime.date) -> list[dict]:
    pdir = repo_root / ".claude/progress"
    feats: list[dict] = []
    if not pdir.is_dir():
        return feats
    for sub in sorted(d for d in pdir.iterdir() if d.is_dir()):
        slugs = {fm["feature_slug"] for pf in sub.glob("*.md")
                 if (fm := load_fm(pf)).get("feature_slug")}
        if len(slugs) > 2 or sub.name in ("quick-features", "quick-wins"):
            # DI-107: a catch-all dir holds independent progress files that reuse generic task
            # ids (QF-1, TASK-1). Capture each FILE as its own feature (artifact_path = the file
            # → a unique source_artifact_id) so (source_artifact_id, source_task_id) never
            # collides across files; idempotent on re-run.
            print(f"   (catch-all dir '{sub.name}': capturing per-file)")
            for pf in sorted(sub.glob("*.md")):
                feat = feature_from_file(pf)
                if feat is None:
                    continue
                pf_fm = load_fm(pf)
                pf_newest = to_date(pf_fm.get("updated")) or to_date(pf_fm.get("created"))
                if pf_newest is None or pf_newest < cutoff:
                    continue
                if all(str(t["status"]).lower() in COMPLETE for t in feat["tasks"]):
                    continue  # fully complete → not in-flight
                feat["newest"] = pf_newest
                feats.append(feat)
            continue
        tasks, fslug, plan_ref, newest = tasks_from_progress_dir(sub)
        if not tasks:
            continue
        if newest is None or newest < cutoff:
            continue
        if all(str(t["status"]).lower() in COMPLETE for t in tasks):
            continue  # fully complete → not in-flight
        fslug = fslug or sub.name
        # resolve plan/PRD file for a clean container path + title
        path, kind, title = f".claude/progress/{fslug}/_feature.md", "implementation_plan", \
            fslug.replace("-", " ").title()
        if plan_ref and (repo_root / plan_ref).exists():
            pf_fm = load_fm(repo_root / plan_ref)
            path = plan_ref
            kind = "prd" if "/PRD" in plan_ref else "implementation_plan"
            title = pf_fm.get("title") or title
        feats.append({"slug": fslug, "title": str(title),
                      "kind": kind if kind in VALID_KINDS else "implementation_plan",
                      "artifact_path": path, "tasks": tasks, "newest": newest})
    return feats


# -------------------------------------------------------------------------- apply
def capture_feature(api: str, workspace: str, tree: str, feat: dict, apply: bool) -> dict:
    reg_body = {
        "workspace_id": workspace, "tree_id": tree, "path": feat["artifact_path"],
        "kind": feat["kind"], "title": feat["title"], "feature_slug": feat["slug"],
        "frontmatter": {"tasks": feat["tasks"], "feature_slug": feat["slug"]},
        "tasks": feat["tasks"], "apply": apply,
    }
    code, reg = _req(api, "POST", "/api/v1/source-artifacts", reg_body)
    if code != 200 or not isinstance(reg, dict):
        return {"ok": False, "stage": "register", "code": code, "body": reg}
    if not apply:
        return {"ok": True, "dry_run": True, "tasks": len(feat["tasks"])}
    sid = reg.get("source_artifact_id")
    if not sid:
        return {"ok": False, "stage": "register", "reason": "no source_artifact_id", "body": reg}
    for _ in range(10):  # poll until the registered artifact is visible (commit-lag guard)
        c, _b = _req(api, "GET", f"/api/v1/source-artifacts/{sid}")
        if c == 200:
            break
        time.sleep(0.4)
    imp = None
    for attempt in range(4):
        c, body = _req(api, "POST", "/api/v1/work-item-sync/import", {
            "source_artifact_id": sid, "tree_id": tree, "tasks": feat["tasks"],
            "apply": True, "ac_as_steps": False})
        if c == 200:
            imp = body
            break
        if c == 404:
            time.sleep(0.5 * (attempt + 1))
            continue
        return {"ok": False, "stage": "import", "code": c, "body": body}
    if not isinstance(imp, dict):
        return {"ok": False, "stage": "import", "reason": "failed after retries"}
    # Progress is derived server-side from task status (DI-105) — no /complete post-pass needed.
    counts = imp.get("counts", {})
    return {"ok": True, "artifact": sid, "inserts": counts.get("inserts", 0),
            "updates": counts.get("updates", 0), "edges": counts.get("edges_created", 0)}


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="IntentTree SDLC capture/sync")
    ap.add_argument("mode", choices=["sync", "backfill"])
    ap.add_argument("file", nargs="?", help="plan/progress file (sync mode)")
    ap.add_argument("--repo-root", default=".", help="repo root (backfill mode)")
    ap.add_argument("--api-url", default=DEFAULT_API)
    ap.add_argument("--workspace", default=os.environ.get("INTENTTREE_WORKSPACE"))
    ap.add_argument("--tree", default=os.environ.get("INTENTTREE_TREE"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--cutoff", default="2026-05-30")
    args = ap.parse_args()

    if not args.tree:
        sys.stderr.write("error: --tree (or INTENTTREE_TREE) required\n")
        return 2
    api = args.api_url.rstrip("/")
    ws = args.workspace or ""

    if args.mode == "sync":
        if not args.file:
            sys.stderr.write("error: sync mode needs a <file>\n")
            return 2
        feat = feature_from_file(Path(args.file))
        if feat is None:
            print(f"no tasks[] in {args.file}; nothing to sync")
            return 0
        res = capture_feature(api, ws, args.tree, feat, args.apply)
        print(json.dumps(res))
        return 0 if res.get("ok") else 1

    cutoff = to_date(args.cutoff) or datetime.date(2026, 1, 1)
    feats = discover_features(Path(args.repo_root), cutoff)
    print(f"{'APPLY' if args.apply else 'DRY-RUN'} {args.repo_root} -> {args.tree}: "
          f"{len(feats)} in-flight features")
    ok = True
    for f in feats:
        res = capture_feature(api, ws, args.tree, f, args.apply)
        flag = "OK " if res.get("ok") else "!! "
        ok = ok and res.get("ok", False)
        print(f"  {flag}{f['slug']:42s} tasks={len(f['tasks']):3d} "
              f"{ {k: v for k, v in res.items() if k != 'ok'} }")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
