#!/usr/bin/env python3
"""Fail-closed evidence-ref normalizer — Shipped Work Ledger M3, D-M3-3.

Turns the free-form ``commit_refs``/``pr_refs`` values found in plan-file frontmatter into
confident ``(kind, url)`` pairs, or reports WHY a value could not be confidently normalized.

The plan's named risk is *"wrong backfilled PR/commit poisons trust."* Every normalizer in this
module is **fail-closed**: a value that does not parse into a confident result is returned as a
:class:`SkippedRef` naming the reason — never guessed, never partially normalized into a
plausible-looking-but-wrong GitHub URL. The canonical trap this guards against is the literal
value ``"direct-squash-to-main"`` in a ``pr_refs`` list — it is a merge-strategy sentinel, not a
PR, and naive normalization would mint ``https://github.com/miethe/<repo>/pull/direct-squash-to-main``.

Real ref shapes this module must handle (measured over the plan corpus, see the M3 leg contract):

    commit_refs:
      - b9b4613                                          # bare short SHA
      - "a058b91"   # intenttree — feat(itt-cli): ...    # quoted + trailing repo-naming comment
      - "MeatySkills@fe3537b (feat/…, unmerged)"          # repo@sha + free prose
    commit_refs: [ab643191c66e94f41877072780f75b608d619d7a]   # full 40-char SHA, inline flow
    pr_refs: ["agentic_meta_dev#33"]                          # repo-qualified
    pr_refs: ["https://github.com/miethe/agentic_meta_dev/pull/32"]   # full URL
    pr_refs: [51]                                             # bare INTEGER
    pr_refs: ["direct-squash-to-main"]                        # NOT A PR. Sentinel. MUST be skipped.

A "confident" SHA is ``[0-9a-f]{7,40}`` (case-insensitive) — the WHOLE token, after stripping
surrounding quotes/decoration, must match; a word that merely happens to contain hex-ish
characters (``deadbeef-not-a-sha-just-words``) is not confident and is skipped.

Python 3.10+ floor (must import on the node's 3.11 — no 3.12-only syntax). Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_GITHUB_OWNER = "miethe"

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
_REPO_AT_SHA_RE = re.compile(r"^([A-Za-z0-9_.-]+)@([0-9a-f]{7,40})\b", re.IGNORECASE)
_TRAILING_COMMENT_RE = re.compile(r"(?:^|\s)#\s*(.*)$")
_COMMENT_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

_PR_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/(\d+)/?$")
_REPO_HASH_RE = re.compile(r"^([A-Za-z0-9_.-]+)#(\d+)$")
_BARE_INT_RE = re.compile(r"^\d+$")

# Values that LOOK like they might belong in a `pr_refs` list but are not PR references at all —
# reported with their own specific reason rather than falling through to the generic message.
_NON_PR_SENTINELS = {"direct-squash-to-main"}


@dataclass(frozen=True)
class EvidenceRef:
    raw: str            # the original value, verbatim
    kind: str            # "commit" | "pull_request" | "changed_file"
    repo: str | None    # repo name when known/inferable, else None
    ident: str           # the sha, or the PR number as a string
    url: str | None     # canonical https URL, or None when repo is unknown
    system: str          # "github" | "git"   (ExternalSystem value)


@dataclass(frozen=True)
class SkippedRef:
    raw: str
    reason: str          # human-readable, names WHY it was not confidently parseable


def _commit_url(repo: str, sha: str) -> str:
    return f"https://github.com/{DEFAULT_GITHUB_OWNER}/{repo}/commit/{sha}"


def _pr_url(repo: str, number: str) -> str:
    return f"https://github.com/{DEFAULT_GITHUB_OWNER}/{repo}/pull/{number}"


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


# A repo attribution is only trusted in the corpus's actual convention:
#     # <repo> — <prose>          (em dash, en dash, or a spaced ASCII hyphen/double-hyphen)
# The separator is what makes it an *attribution* rather than ordinary prose. Without it,
# "the comment's first word" is not a repo name — measured against real corpus values:
#     "# P0 guardrails + P1 /redeploy + P3 docs shipped to main"  -> would yield repo "P0"
#     "# gate-coverage fix (artifact-atlas) + P2 prep"            -> would yield repo "gate-coverage"
# Both are agentic_meta_dev commits; both would have minted a well-formed but WRONG url. So
# inference is separator-gated and otherwise declines, falling back to default_repo.
_COMMENT_REPO_RE = re.compile(
    r"^\s*(?P<repo>[A-Za-z0-9._-]+)\s*(?:—|–|--|-)\s+\S"
)


def _infer_repo_from_comment(comment: str) -> str | None:
    """Return a confidently-attributed repo from a trailing ``# <repo> — <prose>`` comment.

    Fail-closed, like everything else in this module: a comment that is merely prose returns
    ``None`` (the caller then uses ``default_repo``), never a guessed repo name. Requiring the
    ``<repo> —`` separator is the whole safety property here — see ``_COMMENT_REPO_RE``.
    """
    m = _COMMENT_REPO_RE.match(comment)
    if not m:
        return None
    repo = m.group("repo")
    return repo if _COMMENT_TOKEN_RE.match(repo) else None


def normalize_commit_ref(raw, *, default_repo: str | None = None) -> EvidenceRef | SkippedRef:
    """Normalize one ``commit_refs`` entry. Fail-closed: see module docstring."""
    text = "" if raw is None else str(raw)
    stripped = text.strip()
    if not stripped:
        return SkippedRef(raw=text, reason="empty value")

    comment: str | None = None
    working = stripped
    m = _TRAILING_COMMENT_RE.search(stripped)
    if m:
        comment = m.group(1).strip()
        working = stripped[: m.start()].strip()

    working = _strip_quotes(working)
    if not working:
        return SkippedRef(raw=text, reason="empty value")

    # "repo@sha (free prose)" form — repo is explicit, never inferred/defaulted.
    m2 = _REPO_AT_SHA_RE.match(working)
    if m2:
        repo, sha = m2.group(1), m2.group(2)
        return EvidenceRef(raw=text, kind="commit", repo=repo, ident=sha,
                            url=_commit_url(repo, sha), system="github")

    if not _SHA_RE.match(working):
        return SkippedRef(raw=text, reason=f"not a confident commit sha: {working!r}")

    repo = default_repo
    if comment:
        inferred = _infer_repo_from_comment(comment)
        if inferred:
            repo = inferred

    if repo:
        return EvidenceRef(raw=text, kind="commit", repo=repo, ident=working,
                            url=_commit_url(repo, working), system="github")
    return EvidenceRef(raw=text, kind="commit", repo=None, ident=working, url=None, system="git")


def normalize_pr_ref(raw, *, default_repo: str | None = None) -> EvidenceRef | SkippedRef:
    """Normalize one ``pr_refs`` entry. Fail-closed: see module docstring."""
    text = "" if raw is None else str(raw)
    stripped = text.strip()
    if not stripped:
        return SkippedRef(raw=text, reason="empty value")

    stripped_unquoted = _strip_quotes(stripped)

    if stripped_unquoted.lower() in _NON_PR_SENTINELS:
        return SkippedRef(
            raw=text,
            reason=f"{stripped_unquoted!r} is a merge-strategy sentinel, not a pull request reference",
        )

    m = _PR_URL_RE.match(stripped_unquoted)
    if m:
        repo, number = m.group(2), m.group(3)
        return EvidenceRef(raw=text, kind="pull_request", repo=repo, ident=number,
                            url=stripped_unquoted, system="github")

    m = _REPO_HASH_RE.match(stripped_unquoted)
    if m:
        repo, number = m.groups()
        return EvidenceRef(raw=text, kind="pull_request", repo=repo, ident=number,
                            url=_pr_url(repo, number), system="github")

    if _BARE_INT_RE.match(stripped_unquoted):
        if not default_repo:
            return SkippedRef(
                raw=text,
                reason=f"bare PR number {stripped_unquoted!r} has no repo context (no default_repo)",
            )
        return EvidenceRef(raw=text, kind="pull_request", repo=default_repo, ident=stripped_unquoted,
                            url=_pr_url(default_repo, stripped_unquoted), system="github")

    return SkippedRef(raw=text, reason=f"not a confident pull request reference: {stripped_unquoted!r}")


def normalize_refs(
    commit_refs: list | None, pr_refs: list | None, *, default_repo: str | None = None
) -> tuple[list[EvidenceRef], list[SkippedRef]]:
    """Normalize a full set of ``commit_refs``/``pr_refs`` values. Order-preserving."""
    refs: list[EvidenceRef] = []
    skipped: list[SkippedRef] = []
    for raw in commit_refs or []:
        result = normalize_commit_ref(raw, default_repo=default_repo)
        if isinstance(result, EvidenceRef):
            refs.append(result)
        else:
            skipped.append(result)
    for raw in pr_refs or []:
        result = normalize_pr_ref(raw, default_repo=default_repo)
        if isinstance(result, EvidenceRef):
            refs.append(result)
        else:
            skipped.append(result)
    return refs, skipped


# --------------------------------------------------------------------------------------------
# Frontmatter list extraction (block-list AND inline-flow forms). Stdlib line-scan, mirrors
# `_slug_resolution.py`'s format-preserving approach — not a full YAML parse.
# --------------------------------------------------------------------------------------------
_LIST_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):[ \t]*(?P<rest>.*)$")


def _clean_list_item(raw: str) -> str:
    """Normalize a list item's whitespace/quoting, PRESERVING a trailing ``# comment``.

    The trailing comment is load-bearing, not decoration: in this corpus it is the only place
    a ref's owning repo is recorded, e.g.::

        commit_refs:
          - "a058b91"   # intenttree — feat(itt-cli): opt-in --stamp-frontmatter writeback

    That sha belongs to ``../intenttree``, not to the repo being scanned. An earlier version of
    this function stripped the comment here, *before* :func:`normalize_commit_ref` ever saw it —
    which silently disabled the repo inference at :func:`_infer_repo_from_comment` and produced a
    well-formed but WRONG url (``github.com/miethe/<default_repo>/commit/a058b91``). That is
    exactly the "wrong backfilled PR/commit poisons trust" failure this module exists to prevent,
    and it was invisible to the unit tests because they called ``normalize_commit_ref`` directly,
    bypassing this extractor.

    So: quotes are stripped around the *value*, the comment is kept attached, and the
    ``normalize_*`` functions (which already handle and strip trailing comments) own the split.
    A whole-line comment is still dropped by the caller — only an inline trailing comment on a
    real value survives.
    """
    value = raw.strip()
    comment = ""
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
            comment = value[i:]
            value = value[:i]
            break
    cleaned = _strip_quotes(value)
    if not cleaned:
        return ""  # a whole-line comment, or an empty item — nothing to normalize
    return f"{cleaned}   {comment}" if comment else cleaned


def _split_flow_items(inner: str) -> list[str]:
    """Split the inside of a ``[a, "b, c", d]`` flow list on top-level commas only."""
    items: list[str] = []
    current = ""
    in_quote: str | None = None
    for ch in inner:
        if in_quote is not None:
            current += ch
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            in_quote = ch
            current += ch
            continue
        if ch == ",":
            items.append(current)
            current = ""
            continue
        current += ch
    if current.strip():
        items.append(current)
    return items


def parse_frontmatter_list(text: str, key: str) -> list[str]:
    """Extract a frontmatter list value supporting BOTH block-list (``- item``) and inline
    flow (``[a, b]``) forms, stripping quotes and trailing ``# comment`` — returning raw strings.

    Only a top-level (column-0) ``key:`` line is matched. Returns ``[]`` if *key* is absent or
    carries no items. Never raises on malformed input — this is a best-effort extractor, not a
    validator; unparsable frontmatter yields an empty list rather than an exception.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line or line[0] in (" ", "\t", "-", "#"):
            continue
        m = _LIST_KEY_RE.match(line)
        if not m or m.group("key") != key:
            continue
        rest = m.group("rest").strip()

        if rest.startswith("["):
            flow_text = rest
            j = i
            while "]" not in flow_text and j + 1 < len(lines):
                j += 1
                flow_text += " " + lines[j].strip()
            if "]" not in flow_text:
                return []  # unterminated flow list — nothing confident to return
            inner = flow_text[flow_text.index("[") + 1: flow_text.rindex("]")]
            return [it for it in (_clean_list_item(x) for x in _split_flow_items(inner)) if it]

        items: list[str] = []
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip():
                continue
            if nxt[0] not in (" ", "\t"):
                break  # dedented — the list block ended
            stripped_line = nxt.strip()
            if not stripped_line.startswith("-"):
                break
            item = _clean_list_item(stripped_line[1:].strip())
            if item:
                items.append(item)
        return items

    return []
