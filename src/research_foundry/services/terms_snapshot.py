"""Rights terms-of-service/license snapshotting (rights-entity-model-v1, P4-2).

Content-addressed capture of a source's terms-of-service / license text, so a
rights determination can be tied to the exact text that was reviewed rather
than a URL whose content may drift under it. Snapshots live under
``runs/<run_id>/rights/terms_snapshots/`` -- a run-local artifact that is
deliberately never surfaced by the export path (FR-19).

Storage shape
--------------
Two content-addressed halves under ``rights/terms_snapshots/``:

* ``content/<sha256>.txt`` -- the raw fetched/supplied terms text, keyed by
  its own sha256 so identical content (re-fetched unchanged, or shared across
  URLs) is stored exactly once.
* ``<url_key>.yaml`` -- one small per-URL pointer record (``url_key`` =
  :func:`url_key`, a stable sha256-prefix of the URL -- collision-safe, unlike
  a word-truncated slug) carrying the CURRENT ``terms_snapshot_sha256`` +
  ``terms_verified_at``, plus a ``history[]`` of prior hashes this URL has
  resolved to. This is the artifact a future ``rights_record.access`` block
  would point ``terms_snapshot_uri``/``terms_snapshot_sha256`` at -- wiring
  that link is P4-3/P5's job, not this module's.

Re-snapshot semantics
----------------------
* New URL -> first snapshot: hash computed, content stored, pointer record
  created. ``changed=False`` (nothing to compare against yet).
* Same URL, same content -> ``terms_verified_at`` bumped in place on the
  pointer record; ``changed=False``; sha256 unchanged.
* Same URL, different content -> a NEW content blob is stored (old blob is
  kept, never deleted -- content-addressed stores are append-only), the
  pointer record's current hash moves to the new value, the superseded hash
  is appended to ``history[]``, and a unified diff between old/new content is
  both returned (``TermsSnapshotResult.diff``) and persisted under
  ``diffs/<old_sha>_<new_sha>.diff`` for audit. ``changed=True``.

Fetch-failure handling (P4-3)
------------------------------
:func:`snapshot_terms` never lets a fetch exception escape uncaught: any
error raised while resolving content is caught here, mirroring the
never-raises posture of ``_fetch_url`` in ``services/source_cards.py``. But
unlike that helper, a failure here is never a silent ``None`` -- it degrades
to a populated :class:`TermsSnapshotFailure` record (``reason``, ``detail``,
``attempted_at``), mirroring the fail-closed intent of ``verification.py``'s
``_IO_ERROR_SENTINEL_PREFIX`` pattern. The corresponding
``rights_record.access`` fields stay disambiguated: ``terms_snapshot_uri``/
``terms_snapshot_sha256`` remain ``null`` and ``terms_snapshot_failure``
carries the typed record -- a consumer must never treat a null
``terms_snapshot_uri`` as "not applicable" without first checking
``terms_snapshot_failure`` (R-P2 implicit AC; see
:func:`access_terms_snapshot_status` for the canonical check).

Export exclusion (FR-19)
--------------------------
``rights/terms_snapshots/`` is never referenced by
``services/export_service.py``: ``export_run``/``export_to_file``/
``export_all`` only ever read a fixed, explicitly-named set of run artifacts
(``sources/``, ``extractions/``, ``claims/claim_ledger.yaml``, ``reports/``,
``reviews/``, ``writebacks/``, ``telemetry/run_trace.jsonl``, ``run.yaml``,
``evidence_bundle.yaml``, ``routing_decision.yaml``, ``swarm_plan.yaml``,
``research_brief.md``) -- it never globs the run directory wholesale, so a
new ``rights/`` subtree is excluded by construction, not by an explicit
denylist that could rot. See
``tests/test_rights_terms_snapshot.py::test_export_run_excludes_terms_snapshots``
for the regression guard.
"""

from __future__ import annotations

import difflib
import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ids import now_iso
from ..paths import FoundryPaths, RunPaths
from ..yamlio import dump_yaml, load_yaml

__all__ = [
    "TermsSnapshotResult",
    "TermsSnapshotFailure",
    "access_terms_snapshot_status",
    "snapshot_terms",
    "url_key",
]

_FETCH_TIMEOUT = 8


def url_key(terms_url: str) -> str:
    """Stable, collision-safe filename key for a terms URL (sha256 prefix).

    Unlike ``ids.slugify`` (word-truncated, lossy), this is a pure function of
    the full URL string -- two distinct long URLs sharing a prefix can never
    collide onto the same pointer record.
    """

    return hashlib.sha256(terms_url.strip().encode("utf-8")).hexdigest()[:16]


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _default_fetcher(url: str) -> str | None:
    """Best-effort URL fetch; ``None`` on any failure (never raises).

    Mirrors ``services/source_cards.py::_fetch_url`` exactly -- same timeout,
    same fail-to-None posture -- so terms fetching behaves identically to the
    rest of the capture pipeline's offline-safe defaults.
    """

    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=_FETCH_TIMEOUT) as resp:  # noqa: S310
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 -- fetch failures are P4-3's job, not this one's
        return None


@dataclass(frozen=True)
class TermsSnapshotResult:
    """Outcome of one :func:`snapshot_terms` call."""

    run_id: str
    terms_url: str
    terms_snapshot_sha256: str
    terms_verified_at: str
    # Run-relative pointer, e.g. "rights/terms_snapshots/<url_key>.yaml" --
    # the value a rights_record.access.terms_snapshot_uri would carry.
    terms_snapshot_uri: str
    changed: bool
    previous_sha256: str | None = None
    diff: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "terms_url": self.terms_url,
            "terms_snapshot_sha256": self.terms_snapshot_sha256,
            "terms_verified_at": self.terms_verified_at,
            "terms_snapshot_uri": self.terms_snapshot_uri,
            "changed": self.changed,
            "previous_sha256": self.previous_sha256,
            "diff": self.diff,
        }


@dataclass(frozen=True)
class TermsSnapshotFailure:
    """Typed structural failure record for a failed :func:`snapshot_terms` fetch.

    Returned in place of a :class:`TermsSnapshotResult` when the terms
    content could not be resolved (fetch timeout, 4xx/5xx, malformed
    content, or an empty/None response). This is deliberately never a bare
    ``None`` -- ``rights_record.access.terms_snapshot_failure`` must carry
    this record's shape (``reason``/``detail``/``attempted_at``) while
    ``terms_snapshot_uri``/``terms_snapshot_sha256`` stay ``null``, so a
    consumer can distinguish "never attempted" from "attempted and failed"
    (R-P2 implicit AC). Mirrors the fail-closed intent of
    ``verification.py``'s ``_IO_ERROR_SENTINEL_PREFIX`` pattern, scoped to
    this per-access-record failure rather than a workspace-wide index.
    """

    run_id: str
    terms_url: str
    # "fetch_error" -- the fetcher raised; "empty_content" -- it returned
    # None/empty without raising.
    reason: str
    detail: str
    attempted_at: str

    def as_dict(self) -> dict[str, Any]:
        """Full internal representation, including ``run_id``/``terms_url``
        for logging/telemetry. NOT the shape to persist into
        ``rights_record.access.terms_snapshot_failure`` -- use
        :meth:`to_access_dict` for that (the schema's ``terms_snapshot_failure``
        sub-object is intentionally narrower, since ``run_id``/``terms_url``
        are already recorded elsewhere on the access/rights record)."""

        return {
            "run_id": self.run_id,
            "terms_url": self.terms_url,
            "reason": self.reason,
            "detail": self.detail,
            "attempted_at": self.attempted_at,
        }

    def to_access_dict(self) -> dict[str, Any]:
        """The exact shape ``rights_record.access.terms_snapshot_failure``
        expects (``reason``/``detail``/``attempted_at`` only) -- what a
        caller mirrors in alongside ``terms_snapshot_uri: null`` and
        ``terms_snapshot_sha256: null``."""

        return {
            "reason": self.reason,
            "detail": self.detail,
            "attempted_at": self.attempted_at,
        }


def access_terms_snapshot_status(access: dict[str, Any]) -> str:
    """Classify the terms-snapshot posture of a ``rights_record.access`` block.

    Returns one of ``"success"``, ``"failed"``, or ``"not_attempted"``.

    This is the canonical consumer-side check for the R-P2 implicit AC: a
    consumer reading ``access.get("terms_snapshot_uri")`` /
    ``access.get("terms_snapshot_sha256")`` must **never** treat a ``null``
    value as "not applicable" without first checking
    ``access.get("terms_snapshot_failure")`` -- a null URI is ambiguous
    between "snapshotting was never attempted" and "snapshotting was
    attempted and failed"; only the failure record disambiguates the two.
    This function checks the failure record *before* falling back to
    treating the URI as absent, so callers get the disambiguated answer for
    free instead of re-deriving (and possibly getting wrong) the check
    themselves.
    """

    if access.get("terms_snapshot_failure"):
        return "failed"
    if access.get("terms_snapshot_uri"):
        return "success"
    return "not_attempted"


def _content_path(rp: RunPaths, sha256: str) -> Path:
    return rp.rights_terms_snapshots / "content" / f"{sha256}.txt"


def _pointer_path(rp: RunPaths, terms_url: str) -> Path:
    return rp.rights_terms_snapshots / f"{url_key(terms_url)}.yaml"


def _diff_path(rp: RunPaths, old_sha: str, new_sha: str) -> Path:
    return rp.rights_terms_snapshots / "diffs" / f"{old_sha}_{new_sha}.diff"


def snapshot_terms(
    run_id: str,
    terms_url: str,
    *,
    content: str | None = None,
    fetcher: Callable[[str], str | None] | None = None,
    paths: FoundryPaths | None = None,
) -> TermsSnapshotResult | TermsSnapshotFailure:
    """Snapshot ``terms_url``'s current content, content-addressed by sha256.

    Args:
        run_id: the run this snapshot belongs to (stored under
            ``runs/<run_id>/rights/terms_snapshots/``).
        terms_url: the terms-of-service / license URL being snapshotted.
        content: pre-fetched content (tests, or callers that already fetched
            the text elsewhere). When omitted, *fetcher* (or the default
            best-effort URL fetcher) is invoked to resolve it.
        fetcher: override for content retrieval, e.g. in tests. Any exception
            it raises is caught here and turned into a
            :class:`TermsSnapshotFailure` -- it never propagates out of this
            function.
        paths: workspace root (defaults to :meth:`FoundryPaths.discover`).

    Returns:
        A :class:`TermsSnapshotResult` describing the (possibly re-)snapshot
        on success, or a :class:`TermsSnapshotFailure` -- never a bare
        ``None`` -- when no content could be resolved (fetch raised, or
        returned nothing). The failure record is what a caller should mirror
        into ``rights_record.access.terms_snapshot_failure`` while leaving
        ``terms_snapshot_uri``/``terms_snapshot_sha256`` ``null`` (R-P2
        implicit AC).
    """

    resolved_content = content
    fetch_error: Exception | None = None
    if resolved_content is None:
        fetch = fetcher or _default_fetcher
        try:
            resolved_content = fetch(terms_url)
        except Exception as exc:  # noqa: BLE001 -- never let a fetch error escape uncaught
            fetch_error = exc
            resolved_content = None

    if resolved_content is None:
        return TermsSnapshotFailure(
            run_id=run_id,
            terms_url=terms_url,
            reason="fetch_error" if fetch_error is not None else "empty_content",
            detail=str(fetch_error) if fetch_error is not None else "fetcher returned no content",
            attempted_at=now_iso(),
        )

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)

    new_sha = _content_sha256(resolved_content)
    pointer_path = _pointer_path(rp, terms_url)
    existing = load_yaml(pointer_path) if pointer_path.exists() else None
    existing = existing if isinstance(existing, dict) else None

    now = now_iso()
    previous_sha = existing.get("terms_snapshot_sha256") if existing else None
    history = list(existing.get("history") or []) if existing else []
    changed = previous_sha is not None and previous_sha != new_sha

    # Persist the content blob (content-addressed; write-once, dedup by hash).
    blob_path = _content_path(rp, new_sha)
    if not blob_path.exists():
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_text(resolved_content, encoding="utf-8")

    diff_lines: list[str] = []
    if changed:
        old_blob_path = _content_path(rp, str(previous_sha))
        old_content = (
            old_blob_path.read_text(encoding="utf-8") if old_blob_path.exists() else ""
        )
        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                resolved_content.splitlines(keepends=True),
                fromfile=f"{previous_sha}.txt",
                tofile=f"{new_sha}.txt",
            )
        )
        diff_path = _diff_path(rp, str(previous_sha), new_sha)
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text("".join(diff_lines), encoding="utf-8")
        history.append(
            {
                "sha256": previous_sha,
                "superseded_at": now,
                "diff_path": diff_path.relative_to(rp.run).as_posix(),
            }
        )

    record = {
        "terms_url": terms_url,
        "terms_snapshot_sha256": new_sha,
        "terms_verified_at": now,
        "content_path": blob_path.relative_to(rp.run).as_posix(),
        "history": history,
    }
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(record, pointer_path)

    return TermsSnapshotResult(
        run_id=run_id,
        terms_url=terms_url,
        terms_snapshot_sha256=new_sha,
        terms_verified_at=now,
        terms_snapshot_uri=pointer_path.relative_to(rp.run).as_posix(),
        changed=changed,
        previous_sha256=previous_sha,
        diff=diff_lines,
    )
