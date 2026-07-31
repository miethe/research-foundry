#!/usr/bin/env python3
"""Shared slug<->node resolution engine for the M2 node-join tools (FR-6/FR-7).

Both ``stamp-node-slug.py`` and ``verify-slug-roundtrip.py`` import this module rather than
duplicating the resolution logic — mirrors the ``_status_aliases.py`` precedent (one shared,
tested module; the CLI wrappers are thin).

Resolution order (most-authoritative first), per the M2 task brief:

    (a) ``direct``             — plan file frontmatter carries BOTH ``itt_node_id`` and
                                  ``feature_slug`` (highest confidence: the file names its own node).
    (b) ``source_artifact``    — plan file carries ``source_artifact_id`` (+ ``feature_slug``);
                                  the sync-bindings table maps that artifact to a set of nodes.
    (c) ``retroactive_binding`` — no plan file needed at all: the bindings table's own
                                  ``source_task_id: "feature:<slug>"`` entry for an artifact names
                                  the slug directly; every node sharing that artifact gets it.
                                  Lowest confidence — ``plan_ref`` is unknown via this path alone.

A node reached by more than one path keeps the highest-priority one (first writer wins, since
callers apply (a) then (b) then (c) in order); if two paths independently resolve *different*
slugs for the same node, that is flagged as an internal resolution conflict — never silently
picked — distinct from the FR-7 "node already carries a different feature_slug" write-time
conflict (which compares a resolved candidate against LIVE server state, checked by the caller).

Python 3.10+ floor (must import on the node's 3.11 — no 3.12-only syntax). Stdlib only — the
plan-scalar extractor below is deliberately NOT a full YAML parse (mirrors
``validate-plan-frontmatter.py``'s format-preserving line scan); it only needs a handful of
top-level scalar fields, so a full PyYAML dependency isn't warranted here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------------------------
# Frontmatter scalar extraction (top-level keys only; no nested structures needed here).
# --------------------------------------------------------------------------------------------
FRONTMATTER_FIELD_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):[ \t]*(?P<value>.*)$")

PLAN_SCALAR_KEYS = (
    "feature_slug",
    "itt_node_id",
    "source_artifact_id",
    "intenttree_tree",
    "doc_type",
)


def _frontmatter_bounds(text: str) -> tuple[int, int] | None:
    """Return (open_end, close_start) offsets of the frontmatter content, or None. Mirrors
    ``validate-plan-frontmatter.py``'s bounds discipline (opening ``---`` on its own line)."""
    if not text.startswith("---"):
        return None
    first_nl = text.find("\n")
    if first_nl == -1 or text[:first_nl].strip() != "---":
        return None
    close = text.find("\n---", first_nl)
    if close == -1:
        return None
    return first_nl + 1, close


def _strip_scalar_value(raw: str) -> str:
    """Strip a YAML scalar value: surrounding whitespace, an unquoted trailing ``# comment``,
    and matching surrounding quotes. Good enough for the plain string fields this reads."""
    value = raw
    in_quote: str | None = None
    for i, ch in enumerate(value):
        if in_quote is not None:
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            in_quote = ch
            continue
        if ch == "#" and i > 0 and value[i - 1] in " \t":
            value = value[:i]
            break
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


def frontmatter_insertion_point(text: str) -> int | None:
    """Public wrapper over :func:`_frontmatter_bounds`: the offset just before the closing
    ``---`` delimiter's leading newline, or ``None`` if *text* has no frontmatter block.

    Used by ``stamp-plan-binding.py`` to insert new top-level scalar keys format-preservingly —
    mirrors ``.claude/skills/planning/scripts/enrich_frontmatter.py``'s ``apply_additions`` insert
    point exactly (textual insert just before the close, no re-serialize of existing content).
    """
    bounds = _frontmatter_bounds(text)
    return None if bounds is None else bounds[1]


def scan_frontmatter_scalars(path: Path) -> dict[str, str]:
    """Extract the handful of top-level scalar fields this resolver needs from *path*."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    bounds = _frontmatter_bounds(text)
    if bounds is None:
        return {}
    open_end, close_start = bounds
    out: dict[str, str] = {}
    for line in text[open_end:close_start].splitlines():
        if not line or line[0] in (" ", "\t", "#", "-"):
            continue  # not a top-level (column-0) mapping key
        m = FRONTMATTER_FIELD_RE.match(line)
        if not m or m.group("key") not in PLAN_SCALAR_KEYS:
            continue
        val = _strip_scalar_value(m.group("value"))
        if val and val.lower() != "null":
            out[m.group("key")] = val
    return out


@dataclass
class PlanFile:
    path: Path
    rel_path: str  # repo-relative path; used verbatim as the stamped `plan_ref` value
    feature_slug: str | None
    itt_node_id: str | None
    source_artifact_id: str | None
    intenttree_tree: str | None = None
    doc_type: str | None = None


def scan_plan_files(root: Path, repo_root: Path) -> list[PlanFile]:
    """Scan every ``*.md`` under *root* for the scalar fields this resolver needs.

    Files with no frontmatter (or none of the relevant keys) are silently skipped — this is not
    the NodeStatus linter, it has no opinion on files outside its join-key concern.
    """
    out: list[PlanFile] = []
    for p in sorted(root.rglob("*.md")):
        fm = scan_frontmatter_scalars(p)
        if not fm:
            continue
        try:
            rel = str(p.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            rel = str(p)
        out.append(
            PlanFile(
                path=p,
                rel_path=rel,
                feature_slug=fm.get("feature_slug"),
                itt_node_id=fm.get("itt_node_id"),
                source_artifact_id=fm.get("source_artifact_id"),
                intenttree_tree=fm.get("intenttree_tree"),
                doc_type=fm.get("doc_type"),
            )
        )
    return out


# --------------------------------------------------------------------------------------------
# Corpus slug index (M2 gap-2/gap-3 shared): slug -> every plan file carrying that feature_slug,
# plus a deterministic "primary file" pick for that slug (used to backfill `meta.plan_ref` on the
# node side, and to pick the file to write `itt_node_id`/`intenttree_tree` into on the file side).
# --------------------------------------------------------------------------------------------
_DOC_TYPE_PRIORITY = {"implementation_plan": 0, "prd": 1}


def build_corpus_slug_index(plan_files: list[PlanFile]) -> dict[str, list[PlanFile]]:
    """Return ``{feature_slug: [PlanFile, ...]}`` across the whole scanned corpus."""
    index: dict[str, list[PlanFile]] = {}
    for pf in plan_files:
        if pf.feature_slug:
            index.setdefault(pf.feature_slug, []).append(pf)
    return index


def _stem_matches_slug(rel_path: str, slug: str) -> bool:
    """True when a file's stem IS the slug, ignoring a trailing ``-v<N>`` version suffix.

    Distinguishes the canonical plan for a feature from its phase/sub-plans, which share the
    same ``feature_slug`` but carry an extra qualifier:
        dynamic-artifact-provisioning-v1.md          -> stem 'dynamic-artifact-provisioning'  MATCH
        dynamic-artifact-provisioning-p2-fleet-v1.md -> stem '...-p2-fleet'                   no
    """
    stem = rel_path.rsplit("/", 1)[-1]
    if stem.endswith(".md"):
        stem = stem[: -len(".md")]
    stem = re.sub(r"-v\d+$", "", stem)
    return stem == slug


def select_primary_plan_file(files: list[PlanFile], slug: str | None = None) -> PlanFile:
    """Pick the one file to bind a slug's node to, when several share the slug.

    Preference order: ``doc_type: implementation_plan`` > ``doc_type: prd`` > every other
    ``doc_type`` (or none). Within a doc_type, a file whose stem exactly equals ``slug`` (modulo a
    trailing ``-v<N>``) wins — that is the feature's canonical plan, not one of its phase/sub-plans.
    Remaining ties break deterministically on ``rel_path``.
    """
    def _rank(pf: PlanFile) -> tuple[int, int, str]:
        exact = 0 if (slug and _stem_matches_slug(pf.rel_path, slug)) else 1
        return (_DOC_TYPE_PRIORITY.get(pf.doc_type or "", 2), exact, pf.rel_path)

    return min(files, key=_rank)


# --------------------------------------------------------------------------------------------
# Gap-1: tag_match resolution path — lowest precedence, exact-match-only, unambiguous-only.
# --------------------------------------------------------------------------------------------
@dataclass
class AmbiguousTagMatch:
    node_id: str
    tags: list[str]
    matched_slugs: list[str]


def resolve_tag_match_candidates(
    nodes: dict[str, dict],
    slug_index: dict[str, list[PlanFile]],
    already_resolved: set[str],
) -> tuple[dict[str, "Candidate"], list[dict], list[AmbiguousTagMatch]]:
    """Resolve a node's ``tags`` against the corpus's known ``feature_slug`` values.

    Exact string equality only — no fuzzy/substring/normalized matching (the plan explicitly
    forbids fuzzy-title joins). A node whose tags exactly equal 2+ DISTINCT corpus slugs resolves
    nothing (reported in *ambiguous*, never guessed). Only nodes with no higher-precedence
    resolution at all (``already_resolved``) are considered — this path never overrides (a)/(b)/(c).

    Returns ``(candidates, rejected, ambiguous)`` — ``rejected`` mirrors ``resolve_candidates``'s
    slug-shape-guard bucket (defensive; corpus slugs are expected to already be shape-valid, but
    the guard is re-applied here too rather than assumed).
    """
    candidates: dict[str, Candidate] = {}
    rejected: list[dict] = []
    ambiguous: list[AmbiguousTagMatch] = []

    for node_id, node in nodes.items():
        if node_id in already_resolved:
            continue
        tags = node.get("tags") or []
        if not tags:
            continue
        matched = sorted({t for t in tags if t in slug_index})
        if not matched:
            continue
        if len(matched) > 1:
            ambiguous.append(AmbiguousTagMatch(node_id=node_id, tags=list(tags), matched_slugs=matched))
            continue

        slug = matched[0]
        reject_reason = slug_shape_reject_reason(slug)
        if reject_reason is not None:
            rejected.append({
                "node_id": node_id,
                "value": slug,
                "reason": reject_reason,
                "resolution_path": "tag_match",
                "source_file": None,
            })
            continue

        primary = select_primary_plan_file(slug_index[slug], slug)
        candidates[node_id] = Candidate(
            node_id=node_id,
            slug=slug,
            plan_ref=primary.rel_path,
            resolution_path="tag_match",
            source_file=primary.rel_path,
        )

    return candidates, rejected, ambiguous


# --------------------------------------------------------------------------------------------
# Slug-shape guard (M2 correctness fix): reject resolved values that are ID-shaped rather than
# slug-shaped BEFORE they ever become a Candidate. Guards against the degenerate-import failure
# mode where a plan file had no `feature_slug` in frontmatter and an earlier importer fell back
# to a source-artifact id (or some other AOS entity id) for both the node title and the
# `feature:<id>` binding — resolving that value would stamp a fake feature into the ledger,
# which is worse than leaving the node unstamped (a "what shipped" query would surface nonsense).
#
# Positive test first: a real feature slug is lowercase kebab-case words — digits/hyphens only,
# no underscores, no uppercase. Anything that fails that gets a specific rejection reason via the
# belt-and-braces ID-shape checks below (known AOS entity-id prefixes, and a GENERIC
# ``<lowercase-prefix>_<token>`` pattern so an unanticipated new ``xxx_01...`` prefix is still
# caught even if it's never added to the explicit list).
# --------------------------------------------------------------------------------------------
_SLUG_SHAPE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_BARE_ULID_RE = re.compile(r"^[0-9A-Z]{20,}$")  # long uppercase-alnum run, no hyphenated words

# Known AOS entity-id prefixes (explicit belt-and-braces reject) — see docs/agentic-operator/
# for the id-prefix conventions (srcart_=source artifact, node_/tree_/ws_/bind_=IntentTree,
# agt_/actor_=agent identities, run_/sess_/exec_=run records).
_KNOWN_ID_PREFIXES = (
    "srcart", "node", "tree", "ws", "bind", "agt", "actor",
    "run", "sess", "exec", "wf", "task", "atlas", "intent", "ds",
)
_ID_PREFIX_RE = re.compile(rf"^(?:{'|'.join(_KNOWN_ID_PREFIXES)})_[0-9A-Za-z]+$")

# Generic catch-all: ANY short lowercase prefix + underscore + a longish alnum token. This is
# what catches a brand-new `xxx_01...`-shaped id whose prefix was never anticipated above — real
# feature slugs never contain an underscore, so this never false-positives on a legitimate slug.
_GENERIC_ID_PREFIX_RE = re.compile(r"^[a-z]{2,12}_[0-9A-Za-z]{6,}$")


def slug_shape_reject_reason(value: str) -> str | None:
    """Return a human-readable rejection reason if *value* is not shaped like a real feature
    slug — or ``None`` if *value* is fine to treat as one. See module comment above for why."""
    if not value:
        return "empty value"
    if _SLUG_SHAPE_RE.match(value):
        return None
    if _BARE_ULID_RE.match(value):
        return f"looks like a bare ULID/id token, not a kebab-case feature slug: {value!r}"
    if _ID_PREFIX_RE.match(value) or _GENERIC_ID_PREFIX_RE.match(value):
        return (
            f"looks like an AOS entity id (<prefix>_<token>), not a feature slug: {value!r}"
        )
    return f"not lowercase kebab-case: {value!r}"


def is_slug_shaped(value: str) -> bool:
    return slug_shape_reject_reason(value) is None


# --------------------------------------------------------------------------------------------
# Bindings -> per-artifact node sets + retroactive slugs (tree-scoped by the caller).
# --------------------------------------------------------------------------------------------
def build_binding_maps(
    bindings: list[dict], tree_node_ids: set[str]
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return (nodes_by_source_artifact, slug_by_source_artifact), both tree-scoped.

    ``itt sync status --tree`` silently ignores the tree filter server-side (probed gotcha) — so
    *bindings* is expected to be the UNFILTERED page set, and scoping happens here by intersecting
    each binding's ``node_id`` against *tree_node_ids* (the tree's own node-id set, from
    ``itt tree graph``).
    """
    nodes_by_artifact: dict[str, list[str]] = {}
    slug_by_artifact: dict[str, str] = {}
    for b in bindings:
        node_id = b.get("node_id")
        artifact = b.get("source_artifact_id")
        if not node_id or not artifact or node_id not in tree_node_ids:
            continue
        bucket = nodes_by_artifact.setdefault(artifact, [])
        if node_id not in bucket:
            bucket.append(node_id)
        task_id = str(b.get("source_task_id") or "")
        if task_id.startswith("feature:"):
            slug = task_id[len("feature:"):].strip()
            if slug:
                slug_by_artifact[artifact] = slug
    return nodes_by_artifact, slug_by_artifact


# --------------------------------------------------------------------------------------------
# Candidate resolution.
# --------------------------------------------------------------------------------------------
@dataclass
class Candidate:
    node_id: str
    slug: str
    plan_ref: str | None
    resolution_path: str  # "direct" | "source_artifact" | "retroactive_binding" | "tag_match"
    source_file: str | None
    conflicting: bool = False
    conflict_detail: str | None = None


def resolve_candidates(
    plan_files: list[PlanFile],
    nodes_by_artifact: dict[str, list[str]],
    slug_by_artifact: dict[str, str],
) -> tuple[dict[str, Candidate], list[dict]]:
    """Resolve a node_id -> Candidate map, most-authoritative path winning per node.

    Returns ``(candidates, rejected)``. *rejected* lists every resolution attempt whose slug
    value failed the slug-shape guard (see ``slug_shape_reject_reason`` above) — applied to
    EVERY resolution path (a), (b), (c), not just the retroactive one, since any path can be
    poisoned by the same degenerate-import residue. A rejected value is NEVER added to
    *candidates* and therefore can never be stamped, regardless of what other path might have
    (or might not have) also resolved something for that node.
    """
    candidates: dict[str, Candidate] = {}
    rejected: list[dict] = []

    def _set(node_id: str, slug: str, plan_ref: str | None, path: str, source_file: str | None) -> None:
        reject_reason = slug_shape_reject_reason(slug)
        if reject_reason is not None:
            rejected.append({
                "node_id": node_id,
                "value": slug,
                "reason": reject_reason,
                "resolution_path": path,
                "source_file": source_file,
            })
            return
        existing = candidates.get(node_id)
        if existing is None:
            candidates[node_id] = Candidate(node_id, slug, plan_ref, path, source_file)
            return
        if existing.conflicting:
            return  # already flagged; don't chase further disagreement
        if existing.slug == slug:
            if not existing.plan_ref and plan_ref:
                existing.plan_ref = plan_ref
            return
        # Two resolution paths disagree on the slug for the same node — never silently pick one.
        existing.conflicting = True
        existing.conflict_detail = (
            f"resolution conflict on {node_id}: {existing.resolution_path} resolved "
            f"{existing.slug!r} ({existing.source_file}) but {path} resolves {slug!r} ({source_file})"
        )

    # (a) direct — highest confidence.
    for pf in plan_files:
        if pf.itt_node_id and pf.feature_slug:
            _set(pf.itt_node_id, pf.feature_slug, pf.rel_path, "direct", pf.rel_path)

    # (b) via source_artifact_id -> bindings -> node set.
    for pf in plan_files:
        if pf.source_artifact_id and pf.feature_slug:
            for node_id in nodes_by_artifact.get(pf.source_artifact_id, []):
                _set(node_id, pf.feature_slug, pf.rel_path, "source_artifact", pf.rel_path)

    # (c) retroactive — bindings alone; plan_ref stays unknown via this path.
    for artifact, slug in slug_by_artifact.items():
        for node_id in nodes_by_artifact.get(artifact, []):
            _set(node_id, slug, None, "retroactive_binding", None)

    return candidates, rejected
