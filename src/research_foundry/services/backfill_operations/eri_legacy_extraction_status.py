"""M1/M2 — ERI legacy ``extraction_status`` backfill: recompute, eligibility,
dry-run, apply, and rollback.

Plan: docs/project_plans/implementation_plans/enhancements/
eri-legacy-extraction-status-backfill-v1.md

Scope (M1): ``recompute_extraction_status``, ``categorize_edition``, and
``dry_run_backfill_report`` are READ-ONLY with respect to ``assertion_ledger/``
-- every read there uses ``Path.read_bytes``/``load_yaml`` (never an
``open(..., "w")`` or ``os.replace`` call), and ``dry_run_backfill_report``
additionally takes a before/after structural fingerprint of the workspace
tree and raises if anything changed (see ``_tree_fingerprint``). Do not fork
or reimplement these two functions -- M2 below reuses them unchanged.

Scope (M2, Mode-D human-approved, hardened after a cross-model REJECT):
``apply_backfill`` and ``rollback_backfill`` are the write path.

Hardening round (2026-08-02) -- a security gate rejected the first M2 cut on
nine failure-path findings plus two BLOCKING findings (B1/B2) and process
findings (N1/N2/N5). All are addressed here; see
``.claude/worknotes/eri-legacy-extraction-status-backfill/implementation-notes.md``
for the reasoning behind each:

- **B2 / scope pinning**: ``apply_backfill(apply=True, ...)`` REQUIRES
  ``pinned_receipt`` -- the exact eligible edition-ID set a human approved --
  and fails closed, before any write, if the LIVE eligible set has drifted
  (added or removed ids) from that pinned set.
- **item 1 / write-ahead journal**: every edition about to be mutated is
  appended, flushed, and fsynced (file + containing directory) to an on-disk
  journal under ``backfill_operations/`` BEFORE any write for that edition.
  :func:`receipt_from_journal` derives a complete, usable rollback record
  from the journal alone -- rollback never depends on ``apply_backfill``
  having returned normally.
- **item 2 / item 6 / rollback gate**: ``rollback_backfill`` previews by
  default and requires the SAME strict ``apply is True`` gate
  ``apply_backfill`` uses -- no sibling entry point can write without it.
- **item 3 / path safety**: every receipt-driven ``source_id``/
  ``source_edition_id`` is regex-validated against the registry's own id
  patterns and resolved to confirm it stays inside the workspace root BEFORE
  any write; a single bad entry rejects the whole rollback call.
- **item 4**: an eligible edition whose EXISTING binding does not already
  verify is left untouched and reported (never silently overwritten). (Item
  5's original already_set repair-on-apply path was REMOVED in the third
  hardening round below -- see that note.)
- **item 7 / item 8**: :func:`_atomic_dump`/:func:`_atomic_write_bytes` in
  THIS module wrap (never modify) the registry's own primitives with an
  explicit post-write ``fsync`` of the containing directory and explicit
  mode preservation.
- **item 9 / B1b**: immediately before writing, and again inside the
  self-repair path, on-disk bytes are re-read and compared against the
  captured pre-mutation snapshot; any drift refuses to write/repair rather
  than silently clobbering.
- **B1a**: an advisory ``flock`` under ``backfill_operations/`` serializes
  concurrent ``apply_backfill``/``rollback_backfill`` runs against one
  workspace.
- **N1**: a nonexistent ``--workspace-root`` is a loud, nonzero-exit error,
  never a silent all-zero receipt.
- **N2**: a failure inside the self-repair block never masks the original
  write exception (attached as a note, original re-raised).

Second hardening round (2026-08-02, DESIGN CHANGE, not another guard) -- B2
was found NOT closed on re-review: the pinned-scope check took a snapshot,
but the mutate loop re-globbed ``sources/*/editions/*.yaml`` fresh
afterward, so an edition that appeared between the check and the loop
reaching its position in sort order was silently mutated, unapproved (an
ordinary ``rf ingest`` stamps exactly the qualifying basis; the advisory
lock does not block a writer that isn't using it). Per this project's
doctrine, two rounds on one defect class means restructuring the design, not
adding a third check: there is now exactly ONE ``glob()`` anywhere in this
module's M2 code (:func:`_enumerate_editions`), and its result -- not a
fresh walk -- is what the write loops iterate. Also folded in this round:
NB-1 (docstrings now say plainly that pinning covers the ID SET, not
recomputed VALUES), NB-2 (the repair-write self-repair paths re-check
immediately adjacent to their own write calls, not relying on an earlier
read), the lock file is now created 0600 and unlinked on release when no
mutation occurred, and :func:`receipt_from_journal` tolerates a single torn
trailing journal line instead of raising and losing every earlier,
already-fsynced entry.

Third hardening round (2026-08-02, RE-SCOPE, not a fourth fix) -- the SAME
defect class (approval-scope drift) surfaced a third time, one layer over:
the second round's fix constrained the ELIGIBLE write loop to the approved
set, but left its sibling -- the ``already_set`` repair loop, which called
``_repair_broken_already_set`` to write ``provenance.yaml`` -- completely
unconstrained by any approved set at all. Per this project's doctrine, a
THIRD failure on one class escalates to re-scoping the feature, not writing
a fourth guard. **The already_set repair-on-apply path has been REMOVED
entirely** -- ``_repair_broken_already_set``, the ``already_set_ids``
mutation loop, and the ``repaired`` counter/list no longer exist.
``already_set`` editions are now READ-ONLY in ``apply_backfill``: counted
and reported, never opened, read, or written. This was never in M2's
acceptance criteria (35 pass binding verification, rollback restores
byte-identical, the 452 untouched) -- it was introduced in the second round
as an extra convenience and, per the coordinator's own framing, removing it
returns to plan scope rather than departing from it. The state it used to
repair (an ``already_set`` edition whose provenance is stale, e.g. from an
interrupted rollback) remains fully recoverable: **re-run the same rollback
receipt** -- ``rollback_backfill`` restores unconditionally regardless of
current on-disk state, so re-invoking it (with the original receipt, or a
:func:`receipt_from_journal`-derived one) completes the fix. After this
round there is exactly ONE loop in ``apply_backfill`` that writes anything
in the apply direction, and it iterates the approved set only. Also folded
in: every id in that loop is validated with :func:`_validate_entry_ids_and_paths`
(previously used only on the rollback side) before its path is derived, an
approved id whose file no longer exists at write time is a clean
skip-and-report (``missing_at_write_time``) instead of an uncaught
``FileNotFoundError`` aborting the whole pass, and
:func:`receipt_from_journal`'s torn-line tolerance was narrowed to the
single TRAILING line only -- a malformed line anywhere else in the journal
now raises (real corruption must never be silently dropped, since it could
hide a lost rollback snapshot for an edition that was already mutated).

Eligibility (risk R1 — never content-derived): an edition is eligible only
when its ``allowed_use.basis`` is exactly ``producer_declared_access_status``
(the value ``external_research_resolution._resolve_source_impl`` stamps at
fresh-acquire ingest time — see ``external_research_resolution.py:850``).
Text length, media type, or any other content-shape signal never enters the
eligibility decision — see ``categorize_edition``.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import json
import os
import stat
import time
import uuid
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from ...yamlio import dumps_yaml, load_yaml, loads_yaml
from ..assertion_registry import (
    _EDITION_ID_RE,
    _SOURCE_ID_RE,
    AssertionRegistry,
    RegistryIntegrityError,
    _canonical_digest,
)
from ..assertion_registry import _atomic_dump as _registry_atomic_dump
from ..assertion_registry import _atomic_write_bytes as _registry_atomic_write_bytes
from ..external_research_resolution import (
    _MAX_EXTRACT_CHARS,
    STATUS_FULL_TEXT,
    STATUS_LOCATOR_ONLY,
    STATUS_PARTIAL,
)
from ...ids import now_iso

_RECEIPT_SCHEMA_VERSION = "1.0"

#: The only basis value M2 will ever be allowed to backfill from (decision
#: recorded in the plan frontmatter). Never widen this without a plan update.
_ELIGIBLE_BASIS = "producer_declared_access_status"

EligibilityCategory = Literal["eligible", "ineligible", "already_set"]


class BackfillIntegrityError(ValueError):
    """A receipt/journal entry, or the live ledger scope, failed validation.

    Raised BEFORE any write when: a receipt-driven id fails the registry's
    own id regexes or resolves outside the workspace root (item 3); an
    unpinned or scope-drifted live apply is attempted (B2); or a concurrent
    apply/rollback already holds the workspace's advisory lock (B1a).
    """


# ---------------------------------------------------------------------------
# Durable write primitives -- wrap, never modify, the registry's own atomic
# writers (items 7/8). The whole registry depends on
# AssertionRegistry's module-level ``_atomic_dump``/``_atomic_write_bytes``
# staying exactly as they are; this module never edits them.
# ---------------------------------------------------------------------------


def _fsync_dir(path: Path) -> None:
    """fsync ``path``'s containing directory so its directory entry survives
    a crash immediately after ``os.replace`` -- the registry's own
    primitives fsync only the temp file, never the directory (item 7)."""

    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_dump(data: Mapping[str, Any], path: Path) -> None:
    """Durable wrapper: registry's own YAML atomic-dump, then explicit mode
    preservation (item 8) and containing-directory fsync (item 7)."""

    original_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    _registry_atomic_dump(data, path)
    if original_mode is not None:
        os.chmod(path, original_mode)
    _fsync_dir(path)


def _atomic_write_bytes(data: bytes, path: Path) -> None:
    """Durable wrapper: registry's own bytes atomic-write, then explicit mode
    preservation (item 8) and containing-directory fsync (item 7)."""

    original_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    _registry_atomic_write_bytes(data, path)
    if original_mode is not None:
        os.chmod(path, original_mode)
    _fsync_dir(path)


# ---------------------------------------------------------------------------
# Advisory inter-process lock (B1a) -- serializes concurrent apply/rollback
# runs against one workspace so two processes never race on the same pair.
# ---------------------------------------------------------------------------


class _LockState:
    """Mutable flag a caller sets once it has actually written something,
    so :func:`_advisory_lock` knows on release whether the lock file should
    be left (a real run happened -- keep the audit trail) or unlinked (the
    call turned out to be a no-op/rejection -- do not leave a stray artifact
    sitting in the evidence tree forever)."""

    def __init__(self) -> None:
        self.mutated = False


@contextlib.contextmanager
def _advisory_lock(root: Path):
    lock_path = root / "backfill_operations" / ".apply.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # 0600, explicitly -- os.open's mode argument is masked by the process
    # umask, so a bare os.open(..., 0o600) is not reliably 0600 on every
    # platform/umask combination; chmod it explicitly right after.
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    os.chmod(lock_path, 0o600)
    state = _LockState()
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise BackfillIntegrityError(
                "another apply_backfill/rollback_backfill run already holds the advisory "
                f"lock for this workspace ({lock_path}) -- refusing to race it (B1a)"
            ) from exc
        yield state
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        if not state.mutated:
            # A refused/no-op call (e.g. a B2 scope-drift rejection) must not
            # leave a lock file sitting in the evidence tree indefinitely.
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


# ---------------------------------------------------------------------------
# Receipt-driven id/path validation (item 3) -- every source_id/edition_id
# that originates from a caller-supplied receipt (never from our own
# ``glob()`` walk) is validated against the registry's own id regexes AND
# resolved to confirm it cannot escape the workspace root, before any write.
# ---------------------------------------------------------------------------


def _validate_entry_ids_and_paths(root: Path, source_id: Any, edition_id: Any) -> tuple[Path, Path]:
    if not isinstance(source_id, str) or not _SOURCE_ID_RE.fullmatch(source_id):
        raise BackfillIntegrityError(f"invalid or traversal-shaped source_id in receipt entry: {source_id!r}")
    if not isinstance(edition_id, str) or not _EDITION_ID_RE.fullmatch(edition_id):
        raise BackfillIntegrityError(
            f"invalid or traversal-shaped source_edition_id in receipt entry: {edition_id!r}"
        )
    root_resolved = root.resolve()
    edition_path = (root / "sources" / source_id / "editions" / f"{edition_id}.yaml").resolve()
    provenance_path = (root / "sources" / source_id / "editions" / edition_id / "provenance.yaml").resolve()
    if not edition_path.is_relative_to(root_resolved) or not provenance_path.is_relative_to(root_resolved):
        raise BackfillIntegrityError(
            f"{edition_id}: receipt entry's resolved path escapes the workspace root (item 3)"
        )
    return edition_path, provenance_path


def recompute_extraction_status(text: str | None) -> str:
    """Pure, zero-I/O recompute of the tri-state extraction status.

    DELIBERATELY MORE CONSERVATIVE than ``extract_bytes``'s forward
    classification (``external_research_resolution.py:377-388``) at exactly
    ``_MAX_EXTRACT_CHARS`` chars — do not "fix" this back into agreement.

    ``extract_bytes`` truncates with ``text[:_MAX_EXTRACT_CHARS]`` when it
    marks ``partial`` (``external_research_resolution.py:388``). That means a
    STORED text of exactly ``_MAX_EXTRACT_CHARS`` chars is produced by two
    byte-identical-on-disk histories that recompute-from-stored-text cannot
    tell apart:

      (a) an original document of exactly ``_MAX_EXTRACT_CHARS`` chars ->
          genuinely full_text, forward classification correct.
      (b) an original document LONGER than ``_MAX_EXTRACT_CHARS`` chars,
          truncated by the line above -> genuinely partial, but the
          truncation marker (a missing tail) leaves no trace in the stored
          text itself.

    Confirmed empirically on the live workspace's own boundary case
    (OQ-1's 100,232-byte / 100,000-char edition): its stored text ends
    mid-word ("... it is also imp"), proving it is case (b), a truncated
    document — not a document that happens to end exactly at the limit.
    Labeling exactly-at-limit as ``full_text`` would overclaim fidelity
    (risk R1) on exactly this shape. So recompute fails CLOSED at the
    boundary: only strictly-less-than is provably untruncated.

    No I/O, no exceptions on any input (mirrors ``extract_bytes``'s
    never-raises convention).
    """

    if not text:
        return STATUS_LOCATOR_ONLY
    if len(text) >= _MAX_EXTRACT_CHARS:
        return STATUS_PARTIAL
    return STATUS_FULL_TEXT


def categorize_edition(edition_record: Mapping[str, Any]) -> EligibilityCategory:
    """Classify one on-disk ``source_edition`` record for the backfill.

    Gate order matters for the receipt's counts, not for correctness of the
    R1 invariant: an edition that already carries ``extraction_status`` is
    ``already_set`` regardless of ``basis`` (M1 never re-derives an existing
    status); otherwise eligibility is decided *solely* by
    ``allowed_use.basis`` (risk R1) — content shape is never inspected here.

    NOTE: this classification is presence-based by design (M1's read-only
    predicate, unforked). M2's ``apply_backfill`` treats ``already_set``
    editions as read-only -- counted from this classification alone, never
    opened or written (see ``apply_backfill``'s docstring; a prior revision
    additionally checked binding agreement and repaired a mismatch, but that
    path was removed as an out-of-scope second mutation surface).

    Raises ``ValueError`` on a structurally invalid record (missing
    ``metadata_extensions``) rather than silently miscategorizing it —
    callers should treat that as a data-integrity finding, not skip it.
    """

    extensions = edition_record.get("metadata_extensions")
    if not isinstance(extensions, Mapping):
        raise ValueError("edition record omits metadata_extensions")
    if "extraction_status" in extensions:
        return "already_set"
    allowed_use = extensions.get("allowed_use")
    basis = allowed_use.get("basis") if isinstance(allowed_use, Mapping) else None
    if basis == _ELIGIBLE_BASIS:
        return "eligible"
    return "ineligible"


def _binding_matches_provenance(record: Mapping[str, Any], provenance_record: Mapping[str, Any]) -> bool:
    """True iff ``record``'s CURRENT fields recompute to ``provenance_record``'s
    stored ``edition_binding``/``edition_binding_sha256`` -- i.e. this edition
    already verifies (the same recompute-and-compare ``_load_provenance``
    performs). May raise ``RegistryIntegrityError`` if ``record`` itself is too
    malformed to even compute a binding from -- callers must not swallow that
    into a plain False; it belongs in ``integrity_errors``, not
    ``pre_existing_integrity_failures`` (item 4). Only called for the
    eligible track in ``apply_backfill`` -- ``already_set`` editions are
    read-only and never reach this check.
    """

    binding = AssertionRegistry._edition_binding(record)
    return (
        provenance_record.get("edition_binding") == binding
        and provenance_record.get("edition_binding_sha256") == _canonical_digest(binding)
    )


def _tree_fingerprint(root: Path) -> str:
    """Cheap same-process fingerprint of every file's (path, size, mtime_ns).

    Not a security control — a same-process before/after equality check that
    the one dry-run call below touched nothing on disk. Any regression that
    adds a write to this module's read path will make this raise instead of
    silently passing.
    """

    if not root.exists():
        return sha256(b"").hexdigest()
    parts: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            file_stat = path.stat()
            parts.append(f"{path}:{file_stat.st_size}:{file_stat.st_mtime_ns}")
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _receipt_id(payload: Mapping[str, Any], *, kind: str = "dry_run") -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"ral_eri_legacy_status_{kind}_{sha256(encoded.encode()).hexdigest()[:16]}"


def dry_run_backfill_report(workspace_root: Path | str) -> dict[str, Any]:
    """Read-only walk of every edition record under ``workspace_root``.

    ``workspace_root`` is the assertion-ledger *workspace* directory itself
    (e.g. ``assertion_ledger/workspaces/<workspace_key>``), not the foundry
    root — the caller resolves the workspace hash however it likes (CLI flag,
    ``AssertionRegistry(workspace_id=...).root``, etc.).

    Raises ``FileNotFoundError`` if ``workspace_root`` does not exist (N1) --
    a typo'd path must never silently report an all-zero receipt at exit 0.

    Never writes anything under ``workspace_root``: every file access below
    is a read (``load_yaml``, ``Path.read_bytes``), and the before/after
    ``_tree_fingerprint`` check raises ``RuntimeError`` if that invariant is
    ever violated by a future change to this function.

    Returns a receipt dict with ``authoritative_data_mutated: False`` and the
    real (not predicted) split across eligible/ineligible/already_set and,
    for eligible editions, full_text/partial/locator_only.
    """

    root = Path(workspace_root)
    if not root.exists():
        raise FileNotFoundError(f"workspace_root does not exist: {root} (N1)")
    before = _tree_fingerprint(root)

    total = eligible = ineligible = already_set = 0
    full_text = partial = locator_only = 0
    eligible_details: list[dict[str, Any]] = []
    integrity_errors: list[dict[str, str]] = []

    edition_paths = sorted(root.glob("sources/*/editions/*.yaml"))
    for edition_path in edition_paths:
        record = load_yaml(edition_path)
        if not isinstance(record, dict):
            integrity_errors.append({"path": str(edition_path), "reason": "not_a_mapping"})
            continue
        total += 1
        try:
            category = categorize_edition(record)
        except ValueError as exc:
            integrity_errors.append({"path": str(edition_path), "reason": str(exc)})
            continue

        if category == "already_set":
            already_set += 1
            continue
        if category == "ineligible":
            ineligible += 1
            continue

        eligible += 1
        edition_id = edition_path.stem
        content_path = edition_path.parent / edition_id / "content.bin"
        raw = content_path.read_bytes()
        text = _decode(raw)
        status = recompute_extraction_status(text)
        if status == STATUS_FULL_TEXT:
            full_text += 1
        elif status == STATUS_PARTIAL:
            partial += 1
        else:
            locator_only += 1
        eligible_details.append(
            {
                "source_id": record.get("source_id"),
                "source_edition_id": edition_id,
                "recomputed_extraction_status": status,
                "decoded_char_count": len(text),
                "raw_byte_count": len(raw),
            }
        )

    after = _tree_fingerprint(root)
    if before != after:
        raise RuntimeError(
            "eri_legacy_extraction_status.dry_run_backfill_report must never mutate "
            "the ledger workspace; tree fingerprint changed during a read-only pass"
        )

    payload = {
        "operation": "eri_legacy_extraction_status_backfill_dry_run",
        "mode": "dry_run",
        "workspace_root": str(root),
        "authoritative_data_mutated": False,
        "counts": {
            "total_editions": total,
            "eligible": eligible,
            "ineligible": ineligible,
            "already_set": already_set,
            "eligible_full_text": full_text,
            "eligible_partial": partial,
            "eligible_locator_only": locator_only,
        },
        "eligible_editions": eligible_details,
        "integrity_errors": integrity_errors,
    }
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id(payload),
        **payload,
    }


# ---------------------------------------------------------------------------
# M2 -- the ONE canonical enumeration.
#
# Design-change round (2026-08-02, second consecutive round on B2): the prior
# fix added a pinned-scope CHECK but left the write loop re-globbing fresh
# afterward, so an edition that appeared between the check and the loop
# reaching its position in sort order was silently mutated, unapproved --
# the check was a snapshot, the writes were not constrained by it. Per this
# project's doctrine, two rounds on one defect class means a design change,
# not another guard: there is now exactly ONE glob of
# ``sources/*/editions/*.yaml`` anywhere in this module's M2 code
# (``_enumerate_editions`` below). Its result IS the approved set -- the
# write loop iterates that set directly (paths derived from each
# (source_id, edition_id), never re-globbed), so scope compliance is
# structural: the loop cannot reach an edition that was not in the set this
# same call already validated against the pinned receipt.
# ---------------------------------------------------------------------------


class _EnumerationResult:
    """The result of the single read-only classification walk.

    Metadata-only (``load_yaml`` on each edition record) -- no
    ``content.bin``/``provenance.yaml`` reads here. Those happen per-edition,
    on demand, keyed off these id sets, never off a second ``glob()``.
    """

    __slots__ = ("eligible_ids", "already_set_ids", "ineligible_count", "integrity_errors")

    def __init__(
        self,
        eligible_ids: frozenset[tuple[str, str]],
        already_set_ids: frozenset[tuple[str, str]],
        ineligible_count: int,
        integrity_errors: tuple[dict[str, str], ...],
    ) -> None:
        self.eligible_ids = eligible_ids
        self.already_set_ids = already_set_ids
        self.ineligible_count = ineligible_count
        self.integrity_errors = integrity_errors


def _enumerate_editions(root: Path) -> _EnumerationResult:
    """The SINGLE ``glob("sources/*/editions/*.yaml")`` in ``apply_backfill``.

    Replaces both the old ``_live_eligible_ids`` (B2's own check) and the
    write loop's separate re-glob -- there is now exactly one enumeration per
    ``apply_backfill`` call, and its ``eligible_ids``/``already_set_ids`` are
    what the write loops iterate directly.
    """

    eligible: set[tuple[str, str]] = set()
    already_set: set[tuple[str, str]] = set()
    ineligible_count = 0
    integrity_errors: list[dict[str, str]] = []
    for edition_path in sorted(root.glob("sources/*/editions/*.yaml")):
        record = load_yaml(edition_path)
        if not isinstance(record, dict):
            integrity_errors.append({"path": str(edition_path), "reason": "not_a_mapping"})
            continue
        try:
            category = categorize_edition(record)
        except ValueError as exc:
            integrity_errors.append({"path": str(edition_path), "reason": str(exc)})
            continue
        source_id = edition_path.parent.parent.name
        edition_id = edition_path.stem
        if category == "eligible":
            eligible.add((source_id, edition_id))
        elif category == "already_set":
            already_set.add((source_id, edition_id))
        else:
            ineligible_count += 1
    return _EnumerationResult(
        eligible_ids=frozenset(eligible),
        already_set_ids=frozenset(already_set),
        ineligible_count=ineligible_count,
        integrity_errors=tuple(integrity_errors),
    )


def _pinned_edition_ids(pinned_receipt: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    """Extract the approved eligible-id set from EITHER receipt shape: M1's
    ``dry_run_backfill_report`` (``eligible_editions``) or M2's own
    ``apply_backfill(apply=False)`` preview (``changes``)."""

    items = pinned_receipt.get("eligible_editions")
    if items is None:
        items = pinned_receipt.get("changes")
    if not isinstance(items, list):
        raise BackfillIntegrityError(
            "pinned_receipt has neither 'eligible_editions' nor 'changes' -- not a "
            "recognizable dry-run/preview receipt"
        )
    ids: set[tuple[str, str]] = set()
    for item in items:
        source_id = item.get("source_id")
        edition_id = item.get("source_edition_id")
        if not isinstance(source_id, str) or not isinstance(edition_id, str):
            raise BackfillIntegrityError("pinned_receipt entry missing source_id/source_edition_id")
        ids.add((source_id, edition_id))
    return frozenset(ids)


def _check_pinned_scope(
    live_ids: frozenset[tuple[str, str]],
    *,
    pinned_receipt: Mapping[str, Any],
    expect_count: int | None,
) -> frozenset[tuple[str, str]]:
    """Fail closed if ``live_ids`` -- the eligible-id set from THIS call's
    single :func:`_enumerate_editions` pass -- has drifted from the pinned
    (human-approved) receipt's set (B2).

    NB-1: approval covers the ID SET, not the recomputed VALUES -- a human
    approves "these 35 edition ids are the ones eligible for this backfill,"
    never the specific ``extraction_status``/binding values this call is
    about to compute for them. Re-validating that each id's record still
    QUALIFIES (and re-deriving its value) at write time is item 9's job, not
    this function's.

    Takes the already-computed set rather than re-deriving it: this is NOT a
    second enumeration, and must never become one -- the whole point is that
    the same frozenset returned here is what the caller then iterates.
    """

    if expect_count is not None and expect_count != len(live_ids):
        raise BackfillIntegrityError(
            f"live eligible edition count ({len(live_ids)}) does not match --expect-count "
            f"({expect_count}) -- refusing to apply. Re-run the dry-run and get fresh Mode-D "
            "approval before applying (B2)."
        )
    pinned_ids = _pinned_edition_ids(pinned_receipt)
    if pinned_ids != live_ids:
        added = sorted(live_ids - pinned_ids)
        removed = sorted(pinned_ids - live_ids)
        raise BackfillIntegrityError(
            "live eligible edition-ID set no longer matches the pinned (approved) receipt -- "
            f"refusing to apply (B2). added={added!r} removed={removed!r}"
        )
    return live_ids


# ---------------------------------------------------------------------------
# M2 -- write-ahead journal (item 1)
# ---------------------------------------------------------------------------


def _journal_path(root: Path, run_id: str) -> Path:
    return root / "backfill_operations" / f"{run_id}.journal.jsonl"


def _new_run_id() -> str:
    return f"apply_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def _append_journal_entry(journal_path: Path, entry: Mapping[str, Any]) -> None:
    """Append one JSONL line, fsynced (file + containing directory) before
    returning -- called BEFORE any write for the edition it describes, so a
    crash or exception at any later point still leaves a usable rollback
    record for it (item 1)."""

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(entry), sort_keys=True, separators=(",", ":"))
    with open(journal_path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(journal_path)


def receipt_from_journal(workspace_root: Path | str, journal_path: Path | str) -> dict[str, Any]:
    """Rebuild a usable apply receipt purely from a write-ahead journal.

    Never depends on ``apply_backfill`` having returned normally (item 1):
    every journal line was fsynced -- file and containing directory -- BEFORE
    the write it describes was attempted, so this reconstructs a complete
    rollback record for every edition ``apply_backfill`` had started
    mutating, even if the process was killed mid-loop and no receipt was
    ever printed or saved.

    Classifies each journaled entry's CURRENT on-disk bytes against its
    recorded before/after hashes: ``"applied"`` (bytes match the intended new
    state), ``"not_applied"`` (bytes are still the pre-mutation snapshot --
    the write never landed), or ``"incomplete"`` (bytes match neither -- a
    hard kill mid-write). All three states are equally safe to hand to
    :func:`rollback_backfill`, which restores unconditionally regardless of
    this classification.

    Torn-line tolerance is narrow and TRAILING-ONLY: only the LAST
    non-blank line in the file may be malformed JSON without raising (the
    one shape an interrupted ``write()`` mid-append can actually produce,
    since every earlier line was already fsynced in full before the next
    append began). It is recorded in ``torn_lines`` and skipped. A malformed
    line ANYWHERE ELSE in the journal is a real corruption, not a write-time
    artifact, and raises ``BackfillIntegrityError`` -- silently skipping it
    would drop a rollback snapshot for an edition that may already have been
    mutated, with no error to say so.
    """

    root = Path(workspace_root)
    journal_path = Path(journal_path)
    changes: list[dict[str, Any]] = []
    torn_lines: list[dict[str, Any]] = []
    counts = {"applied": 0, "not_applied": 0, "incomplete": 0}

    if journal_path.exists():
        raw_lines = journal_path.read_text(encoding="utf-8").splitlines()
        non_blank = [(i, ln) for i, ln in enumerate(raw_lines, start=1) if ln.strip()]
        last_non_blank_index = non_blank[-1][0] if non_blank else -1

        for line_number, raw_line in non_blank:
            line = raw_line.strip()
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    raise ValueError("journal line is not a JSON object")
            except (json.JSONDecodeError, ValueError) as exc:
                if line_number != last_non_blank_index:
                    raise BackfillIntegrityError(
                        f"journal line {line_number} is malformed and is NOT the trailing line -- "
                        f"this is real corruption, not a torn write; refusing to silently drop a "
                        f"rollback snapshot: {exc}"
                    ) from exc
                torn_lines.append({"line_number": line_number, "reason": str(exc)})
                continue
            edition_path, provenance_path = _validate_entry_ids_and_paths(
                root, entry.get("source_id"), entry.get("source_edition_id")
            )
            try:
                edition_now = sha256(edition_path.read_bytes()).hexdigest()
                provenance_now = sha256(provenance_path.read_bytes()).hexdigest()
            except FileNotFoundError:
                state = "incomplete"
            else:
                if (
                    edition_now == entry.get("new_edition_yaml_sha256_after")
                    and provenance_now == entry.get("new_provenance_yaml_sha256_after")
                ):
                    state = "applied"
                elif (
                    edition_now == entry.get("edition_yaml_sha256_before")
                    and provenance_now == entry.get("provenance_yaml_sha256_before")
                ):
                    state = "not_applied"
                else:
                    state = "incomplete"
            change = {key: value for key, value in entry.items() if key != "timestamp"}
            change["applied"] = state == "applied"
            change["state"] = state
            changes.append(change)
            counts[state] += 1

    payload = {
        "operation": "eri_legacy_extraction_status_backfill_apply",
        "mode": "recovered_from_journal",
        "workspace_root": str(root),
        "journal_path": str(journal_path),
        "authoritative_data_mutated": any(change["applied"] for change in changes),
        "counts": counts,
        "changes": changes,
        "torn_lines": torn_lines,
        "integrity_errors": [],
    }
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id(payload, kind="recovered"),
        **payload,
    }


# ---------------------------------------------------------------------------
# M2 -- the mutating pair-write, with B1b-safe self-repair (items 1, 9; B1b, N2)
# ---------------------------------------------------------------------------


def _mutate_pair(
    *,
    provenance_path: Path,
    edition_path: Path,
    new_provenance: Mapping[str, Any],
    new_edition: Mapping[str, Any],
    provenance_before_bytes: bytes,
    edition_before_bytes: bytes,
    new_provenance_bytes: bytes,
    new_edition_bytes: bytes,
    edition_id: str,
) -> Literal["applied", "drift_detected"]:
    """Write provenance then edition; on ANY failure, self-repair BOTH back to
    pre-mutation bytes -- but ONLY when it is safe to do so.

    Item 9: re-checks BOTH files' current bytes against the caller's captured
    pre-mutation snapshot as the FIRST thing this function does -- i.e.
    immediately adjacent to the write attempt below it, not relying solely on
    a check the caller may have done earlier (however small that gap was).
    Returns ``"drift_detected"`` without writing anything if either file has
    changed since the caller read it.

    B1b: for each file in the self-repair path, if its CURRENT on-disk bytes
    are neither the pre-mutation snapshot NOR the exact new bytes this call
    attempted to write, something else (a concurrent writer, a backup/AV tool
    holding the file, corruption) touched it between our read and our write
    -- refuse to clobber it and raise loudly instead of overwriting
    unconditionally. NB-2: re-checks AGAIN immediately before the repair
    write itself (not just at the point the repair decision was made) --
    the freshest possible read directly adjacent to the write call.

    N2: a failure INSIDE this repair path never masks the original write
    exception -- it is attached as a note and the original is re-raised.
    """

    if (
        provenance_path.read_bytes() != provenance_before_bytes
        or edition_path.read_bytes() != edition_before_bytes
    ):
        return "drift_detected"

    try:
        _atomic_dump(dict(new_provenance), provenance_path)
        _atomic_dump(dict(new_edition), edition_path)
    except Exception as write_exc:
        repair_notes: list[str] = []
        for path, before_bytes, after_bytes in (
            (provenance_path, provenance_before_bytes, new_provenance_bytes),
            (edition_path, edition_before_bytes, new_edition_bytes),
        ):
            try:
                current = path.read_bytes()
            except OSError as read_exc:
                repair_notes.append(f"{path.name}: could not read current bytes ({read_exc!r})")
                continue
            if current == before_bytes:
                continue  # already original; nothing to repair for this file
            if current != after_bytes:
                repair_notes.append(
                    f"{path.name}: on-disk bytes match neither the pre-mutation snapshot nor the "
                    "intended new bytes -- refusing to auto-repair (B1b)"
                )
                continue
            # NB-2: re-check ONE more time, immediately adjacent to the write
            # call itself, rather than relying solely on the ``current`` read
            # captured a few lines earlier.
            if path.read_bytes() != after_bytes:
                repair_notes.append(
                    f"{path.name}: bytes changed again between the repair safety check and the "
                    "repair write -- refusing to auto-repair (NB-2)"
                )
                continue
            try:
                _atomic_write_bytes(before_bytes, path)
            except Exception as repair_exc:  # N2: never let this mask write_exc
                repair_notes.append(f"{path.name}: repair write itself failed: {repair_exc!r}")
        if repair_notes:
            write_exc.add_note(f"{edition_id}: self-repair outcome: " + "; ".join(repair_notes))
        raise write_exc

    return "applied"


# ---------------------------------------------------------------------------
def apply_backfill(
    workspace_root: Path | str,
    *,
    apply: bool = False,
    pinned_receipt: Mapping[str, Any] | None = None,
    expect_count: int | None = None,
) -> dict[str, Any]:
    """Apply (or preview) M2's write: ``extraction_status`` + re-attested provenance.

    Design (2026-08-02 restructure -- see module docstring): exactly ONE
    ``glob("sources/*/editions/*.yaml")`` happens per call
    (:func:`_enumerate_editions`). Its ``eligible_ids`` frozenset is what the
    ONE write loop below iterates directly, deriving each edition's path
    from ``(source_id, edition_id)`` -- there is no second walk, and no
    second write path, anywhere in this function. Scope compliance is
    therefore structural: the write loop cannot reach an edition that was
    not already a member of the set this same call validated against the
    pinned receipt, regardless of what appears on disk while the loop is
    running.

    Classifies each id with the SAME unforked ``categorize_edition``/
    ``recompute_extraction_status`` predicate M1 uses. For every ``eligible``
    id that ALREADY verifies (item 4) it computes a new edition record
    (``metadata_extensions.extraction_status`` added) and a new provenance
    record (``edition_binding``/``edition_binding_sha256`` recomputed from
    that new edition via :meth:`AssertionRegistry._edition_binding` -- the
    registry's own pure static method, never hand-rolled -- and the
    registry's own ``_canonical_digest``). ``ineligible`` editions are
    counted (from the enumeration alone) but never opened for writing.

    ``already_set`` editions are READ-ONLY in ``apply_backfill`` -- counted
    (from the enumeration alone) and never opened, read, or written by this
    function at all (re-scope, 2026-08-02: a repair path used to live here
    for a half-rolled-back ``already_set`` edition -- see the module
    docstring's "third round" note for why it was removed rather than
    guarded a third time). If an ``already_set`` edition's provenance has
    fallen out of sync with its own field (e.g. an interrupted rollback),
    the recovery is: **re-run the same rollback receipt** --
    ``rollback_backfill`` restores unconditionally regardless of current
    on-disk state, so re-invoking it with the receipt (or a
    :func:`receipt_from_journal`-derived one) from the run that produced the
    half-state completes the fix. That path is unconditional, idempotent,
    already tested, and does not require a second mutation surface in this
    function.

    ``apply=False`` (the default) computes and returns the full receipt --
    including the binding diff each eligible edition WOULD get -- without
    writing anything.

    Strict apply gate (item 6): ``apply`` must literally be ``True`` (checked
    with ``apply is True``, not truthiness) to mutate; anything else is a
    no-write preview. A non-bool ``apply`` raises ``TypeError``.

    Scope pinning (B2): when ``apply=True``, ``pinned_receipt`` is REQUIRED
    -- the exact eligible edition-ID set a human approved (an
    ``eligible_editions``-bearing dry-run receipt, or a ``changes``-bearing
    M2 preview receipt). NB-1: approval covers that ID SET, not the specific
    ``extraction_status``/binding VALUES this call will go on to compute --
    a record can (and, per item 9, is expected to) be re-read and
    re-validated at write time; only its presence in/absence from the
    approved id set is what pinning locks down. Before any write, THIS
    call's own single enumeration is compared against the pinned set; ANY
    drift (added or removed ids) raises ``BackfillIntegrityError`` naming
    the diff, and the SAME frozenset that passed that comparison is what the
    write loop below iterates -- never re-derived. An unpinned live apply is
    not permitted. ``expect_count`` is an optional additional redundant
    assertion, never a substitute for the id-set comparison.

    Concurrency (B1a): the entire mutating pass runs under an advisory
    ``flock`` on ``backfill_operations/.apply.lock`` (0600; unlinked on
    release if this call turned out not to mutate anything) -- a second
    concurrent apply/rollback against the same workspace fails fast rather
    than racing. The lock does NOT block an ordinary external writer (e.g.
    ``rf ingest``) that isn't using it -- that is exactly what B2's id-set
    iteration (not a live re-glob) is what closes.

    Write-ahead journal (item 1): before ANY write for a given edition, its
    pre-mutation snapshot (and the intended new bytes) is appended, flushed,
    and fsynced to ``backfill_operations/<run_id>.journal.jsonl`` -- BOTH the
    file and its containing directory. A crash or exception at any point
    after that leaves a complete, usable rollback record for that edition
    (and every edition journaled before it), independent of whether this
    function ever returns. :func:`receipt_from_journal` derives an
    equivalent receipt purely from that journal.

    Item 9 (write-time re-validation, NOT a substitute for the enumeration):
    each approved id's record is re-read fresh when the loop reaches it; if
    it no longer classifies ``eligible`` (someone else already touched it),
    or if its bytes have drifted since that fresh read by the time this call
    is about to write, the edition is skipped and reported (drift), never
    written -- approval of the ID never implies approval of whatever VALUES
    happen to be there by the time the loop arrives.

    R5 (partial apply must be structurally impossible): see ``_mutate_pair``
    for the write-then-self-repair mechanics, and item 9 / B1b for the
    on-disk drift checks that keep both the initial write and the repair
    write from ever clobbering something else's bytes.

    Never routes through :meth:`AssertionRegistry.ingest` or
    ``_write_immutable_mapping`` -- both reject a same-path rewrite by design
    (immutable-record conflict on differing bytes). This is a deliberate,
    reviewed, out-of-band rewrite of already-published records, using this
    module's own durable ``_atomic_dump``/``_atomic_write_bytes`` wrappers
    (items 7/8) around the registry's primitives, never weakening the
    immutability check for any other caller.

    ``content.bin`` is opened for reading only, and its sha256 is checked
    unchanged both before starting an edition's mutation and (when
    ``apply=True``) immediately after -- this function raises rather than
    proceed if that ever fails.
    """

    if not isinstance(apply, bool):
        raise TypeError("apply must be a bool, not a truthy/falsy stand-in (item 6)")
    mutate = apply is True

    root = Path(workspace_root)
    if not root.exists():
        raise FileNotFoundError(f"workspace_root does not exist: {root} (N1)")
    root = root.resolve()

    if mutate and pinned_receipt is None:
        raise BackfillIntegrityError(
            "apply=True requires pinned_receipt -- the approved dry-run/preview receipt naming "
            "the exact eligible edition-ID set Mode-D approval covers. An unpinned live apply is "
            "not permitted (B2)."
        )

    lock_ctx = _advisory_lock(root) if mutate else contextlib.nullcontext()

    changes: list[dict[str, Any]] = []
    pre_existing_integrity_failures: list[dict[str, Any]] = []
    drift_detected_editions: list[dict[str, Any]] = []
    missing_at_write_time: list[dict[str, Any]] = []
    integrity_errors: list[dict[str, str]] = []
    eligible_editions: list[dict[str, str]] = []
    counts = {
        "eligible": 0,
        "ineligible": 0,
        "already_set": 0,
        "applied": 0,
        "pre_existing_integrity_failure": 0,
        "drift_detected": 0,
        "missing_at_write_time": 0,
    }

    with lock_ctx as lock_state:
        # THE single enumeration for this call. Its eligible_ids is both the
        # B2 comparison input AND (unchanged, never re-derived) the write
        # loop's iteration source below.
        enum_result = _enumerate_editions(root)
        integrity_errors.extend(dict(entry) for entry in enum_result.integrity_errors)
        counts["ineligible"] = enum_result.ineligible_count
        # already_set is READ-ONLY here: counted from the enumeration alone,
        # never opened, read, or written by apply_backfill (re-scope,
        # 2026-08-02 -- see the module docstring).
        counts["already_set"] = len(enum_result.already_set_ids)

        if mutate:
            approved_ids = _check_pinned_scope(
                enum_result.eligible_ids, pinned_receipt=pinned_receipt, expect_count=expect_count
            )
        else:
            approved_ids = enum_result.eligible_ids

        run_id = _new_run_id() if mutate else None
        journal_path = _journal_path(root, run_id) if mutate and run_id is not None else None

        # --- The ONE write loop in the apply direction: iterates EXACTLY
        # the approved set; no other path in this function opens a file for
        # writing. -----------------------------------------------------
        for source_id, edition_id in sorted(approved_ids):
            # NB-3 (defense in depth, should be unreachable): if a future
            # refactor reintroduces a walk here, this fails loudly instead
            # of silently widening scope back out.
            if (source_id, edition_id) not in approved_ids:
                raise BackfillIntegrityError(
                    f"{edition_id}: not a member of this call's approved id set -- refusing to "
                    "process (structural guard)"
                )

            # Fix 1: validate every id the same way rollback's receipt-driven
            # ids are validated, even though these came from our own
            # enumeration rather than an external receipt -- path derivation
            # from (source_id, edition_id) replaced a glob, and a glob could
            # only ever yield real in-tree paths; derivation on its own
            # cannot make that same guarantee without this check.
            edition_path, provenance_path = _validate_entry_ids_and_paths(root, source_id, edition_id)
            content_path = edition_path.parent / edition_id / "content.bin"

            counts["eligible"] += 1
            eligible_editions.append({"source_id": source_id, "source_edition_id": edition_id})

            # Fix 2: an approved id whose files no longer exist at write time
            # (e.g. removed out-of-band between enumeration and here) is a
            # clean skip-and-report, not an uncaught FileNotFoundError that
            # would abort the whole pass after any earlier mutations.
            try:
                edition_before_bytes = edition_path.read_bytes()
            except FileNotFoundError:
                missing_at_write_time.append(
                    {"source_id": source_id, "source_edition_id": edition_id, "path": str(edition_path)}
                )
                counts["missing_at_write_time"] += 1
                continue

            record = loads_yaml(edition_before_bytes.decode("utf-8"))
            if not isinstance(record, dict):
                integrity_errors.append({"path": str(edition_path), "reason": "not_a_mapping"})
                continue

            # Item 9 / NB-1: re-validate that this approved ID still
            # QUALIFIES on a fresh read -- approval covers the id, never a
            # promise that the record's values are unchanged.
            try:
                fresh_category = categorize_edition(record)
            except ValueError as exc:
                integrity_errors.append({"path": str(edition_path), "reason": str(exc)})
                continue
            if fresh_category != "eligible":
                drift_detected_editions.append(
                    {"source_id": source_id, "source_edition_id": edition_id, "kind": "no_longer_eligible"}
                )
                counts["drift_detected"] += 1
                continue

            try:
                provenance_before_bytes = provenance_path.read_bytes()
            except FileNotFoundError:
                missing_at_write_time.append(
                    {"source_id": source_id, "source_edition_id": edition_id, "path": str(provenance_path)}
                )
                counts["missing_at_write_time"] += 1
                continue
            provenance_record = loads_yaml(provenance_before_bytes.decode("utf-8"))
            if not isinstance(provenance_record, dict):
                integrity_errors.append({"path": str(provenance_path), "reason": "not_a_mapping"})
                continue

            try:
                binding_ok = _binding_matches_provenance(record, provenance_record)
            except RegistryIntegrityError as exc:
                integrity_errors.append(
                    {"path": str(edition_path), "reason": f"cannot compute edition_binding: {exc}"}
                )
                continue

            # Item 4: refuse to touch a pre-existing integrity failure.
            if not binding_ok:
                pre_existing_integrity_failures.append(
                    {"source_id": source_id, "source_edition_id": edition_id}
                )
                counts["pre_existing_integrity_failure"] += 1
                continue

            try:
                content_before = content_path.read_bytes()
            except FileNotFoundError:
                missing_at_write_time.append(
                    {"source_id": source_id, "source_edition_id": edition_id, "path": str(content_path)}
                )
                counts["missing_at_write_time"] += 1
                continue
            content_sha256_before = sha256(content_before).hexdigest()
            if record.get("content_sha256") != content_sha256_before:
                raise RuntimeError(
                    f"{edition_id}: content.bin does not match the edition's own recorded "
                    "content_sha256 before any mutation -- refusing to touch this edition"
                )

            text = _decode(content_before)
            status = recompute_extraction_status(text)

            extensions_before = dict(record["metadata_extensions"])
            new_extensions = {**extensions_before, "extraction_status": status}
            new_edition = {**record, "metadata_extensions": new_extensions}
            binding = AssertionRegistry._edition_binding(new_edition)
            binding_sha256 = _canonical_digest(binding)
            new_provenance = {
                **provenance_record,
                "edition_binding": binding,
                "edition_binding_sha256": binding_sha256,
            }

            edition_yaml_sha256_before = sha256(edition_before_bytes).hexdigest()
            provenance_yaml_sha256_before = sha256(provenance_before_bytes).hexdigest()
            new_edition_bytes = dumps_yaml(dict(new_edition)).encode("utf-8")
            new_provenance_bytes = dumps_yaml(dict(new_provenance)).encode("utf-8")

            change: dict[str, Any] = {
                "kind": "apply",
                "source_id": source_id,
                "source_edition_id": edition_id,
                "recomputed_extraction_status": status,
                "content_sha256": content_sha256_before,
                "edition_binding_sha256_before": provenance_record.get("edition_binding_sha256"),
                "edition_binding_sha256_after": binding_sha256,
                "edition_yaml_sha256_before": edition_yaml_sha256_before,
                "provenance_yaml_sha256_before": provenance_yaml_sha256_before,
                "new_edition_yaml_sha256_after": sha256(new_edition_bytes).hexdigest(),
                "new_provenance_yaml_sha256_after": sha256(new_provenance_bytes).hexdigest(),
                "edition_snapshot_b64": base64.b64encode(edition_before_bytes).decode("ascii"),
                "provenance_snapshot_b64": base64.b64encode(provenance_before_bytes).decode("ascii"),
                "applied": False,
            }

            if mutate:
                assert journal_path is not None
                # Item 1: journal BEFORE any write for this edition.
                _append_journal_entry(journal_path, {**change, "timestamp": now_iso()})

                # Item 9: _mutate_pair re-checks on-disk bytes itself,
                # immediately adjacent to its own write attempt.
                outcome = _mutate_pair(
                    provenance_path=provenance_path,
                    edition_path=edition_path,
                    new_provenance=new_provenance,
                    new_edition=new_edition,
                    provenance_before_bytes=provenance_before_bytes,
                    edition_before_bytes=edition_before_bytes,
                    new_provenance_bytes=new_provenance_bytes,
                    new_edition_bytes=new_edition_bytes,
                    edition_id=edition_id,
                )
                if outcome == "drift_detected":
                    drift_detected_editions.append(
                        {"source_id": source_id, "source_edition_id": edition_id, "kind": "apply"}
                    )
                    counts["drift_detected"] += 1
                    changes.append(change)
                    continue

                content_after_sha256 = sha256(content_path.read_bytes()).hexdigest()
                if content_after_sha256 != content_sha256_before:
                    raise RuntimeError(f"{edition_id}: content.bin changed during apply -- must never happen")
                change["applied"] = True
                counts["applied"] += 1
                lock_state.mutated = True

            changes.append(change)

    payload = {
        "operation": "eri_legacy_extraction_status_backfill_apply",
        "mode": "apply" if mutate else "dry_run",
        "workspace_root": str(root),
        "authoritative_data_mutated": bool(counts["applied"]),
        "counts": counts,
        "changes": changes,
        "eligible_editions": eligible_editions,
        "pre_existing_integrity_failures": pre_existing_integrity_failures,
        "drift_detected_editions": drift_detected_editions,
        "missing_at_write_time": missing_at_write_time,
        "integrity_errors": integrity_errors,
    }
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id(payload, kind="apply" if mutate else "apply_preview"),
        **payload,
    }


def rollback_backfill(
    workspace_root: Path | str,
    receipt: Mapping[str, Any],
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Restore every edition in an apply receipt's (or
    :func:`receipt_from_journal`'s) ``changes`` list to its pre-mutation bytes.

    Strict gate (item 2/6): previews by default; ``apply`` must literally be
    ``True`` (``apply is True``, not truthiness) to write. A non-bool
    ``apply`` raises ``TypeError``. This mirrors ``apply_backfill``'s own
    gate exactly -- no sibling entry point in this module can write without
    an explicit, strictly-typed confirmation.

    Validation before any write (item 3): every entry's ``source_id``/
    ``source_edition_id`` is checked against the registry's own id regexes
    and resolved to confirm it cannot escape ``workspace_root``, and every
    embedded base64 snapshot is checksummed against its own recorded
    pre-apply sha256 -- in a full pass over ALL entries BEFORE any entry is
    written. A single invalid or tampered entry anywhere in the receipt
    rejects the WHOLE rollback call with zero writes, not just that entry.

    Restores UNCONDITIONALLY: every entry is restored regardless of its
    ``applied``/``state`` flag. This is what makes re-running rollback safe
    to resume: if rollback itself is interrupted after reverting an
    edition's ``provenance.yaml`` but before its ``edition.yaml`` (leaving
    the edition still carrying ``extraction_status`` with now-stale/reverted
    provenance), simply re-invoking ``rollback_backfill`` with the SAME
    receipt safely completes the fix on the next call, because it does not
    gate on any current-state classification at all. This is also the
    documented recovery path for an ``already_set`` edition whose provenance
    fell out of sync with its own field for any other reason (e.g. an
    interrupted rollback): re-run the same rollback receipt (or a
    :func:`receipt_from_journal`-derived one) -- ``apply_backfill`` never
    touches ``already_set`` editions at all (N5, re-scoped 2026-08-02), so a
    naive ``apply_backfill`` re-run is not the recovery path for this case.

    Concurrency (B1a): the write pass runs under the same advisory
    ``backfill_operations/.apply.lock`` ``apply_backfill`` uses.
    """

    if not isinstance(apply, bool):
        raise TypeError("apply must be a bool, not a truthy/falsy stand-in (item 6)")
    mutate = apply is True

    root = Path(workspace_root)
    if not root.exists():
        raise FileNotFoundError(f"workspace_root does not exist: {root} (N1)")
    root = root.resolve()

    changes = receipt.get("changes")
    if not isinstance(changes, list):
        raise ValueError("receipt is missing a 'changes' list")

    # Pass 1: validate EVERY entry before any write (item 3) -- a single bad
    # entry anywhere rejects the whole rollback, zero writes.
    validated: list[dict[str, Any]] = []
    for change in changes:
        edition_path, provenance_path = _validate_entry_ids_and_paths(
            root, change.get("source_id"), change.get("source_edition_id")
        )
        edition_bytes = base64.b64decode(change["edition_snapshot_b64"])
        provenance_bytes = base64.b64decode(change["provenance_snapshot_b64"])
        if sha256(edition_bytes).hexdigest() != change["edition_yaml_sha256_before"]:
            raise RuntimeError(
                f"{change.get('source_edition_id')}: embedded edition snapshot fails its own checksum"
            )
        if sha256(provenance_bytes).hexdigest() != change["provenance_yaml_sha256_before"]:
            raise RuntimeError(
                f"{change.get('source_edition_id')}: embedded provenance snapshot fails its own checksum"
            )
        validated.append(
            {
                "source_id": change["source_id"],
                "source_edition_id": change["source_edition_id"],
                "edition_path": edition_path,
                "provenance_path": provenance_path,
                "edition_bytes": edition_bytes,
                "provenance_bytes": provenance_bytes,
                "edition_sha256_before": change["edition_yaml_sha256_before"],
                "provenance_sha256_before": change["provenance_yaml_sha256_before"],
            }
        )

    if not mutate:
        payload = {
            "operation": "eri_legacy_extraction_status_backfill_rollback",
            "mode": "dry_run",
            "workspace_root": str(root),
            "authoritative_data_mutated": False,
            "restored_count": 0,
            "would_restore_count": len(validated),
            "would_restore_editions": [
                {"source_id": v["source_id"], "source_edition_id": v["source_edition_id"]} for v in validated
            ],
            "restored_editions": [],
        }
        return {
            "schema_version": _RECEIPT_SCHEMA_VERSION,
            "receipt_id": _receipt_id(payload, kind="rollback_preview"),
            **payload,
        }

    restored: list[dict[str, str]] = []
    with _advisory_lock(root) as lock_state:
        for v in validated:
            _atomic_write_bytes(v["provenance_bytes"], v["provenance_path"])
            _atomic_write_bytes(v["edition_bytes"], v["edition_path"])

            if sha256(v["edition_path"].read_bytes()).hexdigest() != v["edition_sha256_before"]:
                raise RuntimeError(
                    f"{v['source_edition_id']}: post-rollback edition bytes do not match the snapshot"
                )
            if sha256(v["provenance_path"].read_bytes()).hexdigest() != v["provenance_sha256_before"]:
                raise RuntimeError(
                    f"{v['source_edition_id']}: post-rollback provenance bytes do not match the snapshot"
                )
            restored.append({"source_id": v["source_id"], "source_edition_id": v["source_edition_id"]})
            lock_state.mutated = True

    payload = {
        "operation": "eri_legacy_extraction_status_backfill_rollback",
        "mode": "rollback",
        "workspace_root": str(root),
        "authoritative_data_mutated": bool(restored),
        "restored_count": len(restored),
        "restored_editions": restored,
    }
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id(payload, kind="rollback"),
        **payload,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Path to the assertion_ledger workspace directory (e.g. "
        "assertion_ledger/workspaces/<workspace_key>).",
    )
    parser.add_argument(
        "--out",
        default=None,
        # Nit1: asymmetric on purpose -- this dry-run CLI's --out refuses
        # assertion_ledger/ paths because it has no reason to write inside the
        # ledger; the apply CLI's --out (below) intentionally DEFAULTS inside
        # it (backfill_operations/), mirroring assertion_rollout.py's own
        # receipt-location precedent for a real mutating run's audit trail.
        help="Optional path to write the JSON receipt to. Defaults to stdout. "
        "Must not be under assertion_ledger/.",
    )
    args = parser.parse_args(argv)

    workspace_root = Path(args.workspace_root)
    if not workspace_root.exists():  # N1
        parser.error(f"--workspace-root does not exist: {workspace_root}")
    if "assertion_ledger" in Path(args.out).parts if args.out else False:
        parser.error("--out must not be written under assertion_ledger/")

    receipt = dry_run_backfill_report(workspace_root)
    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


def _apply_main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Preview (default) or apply the M2 extraction_status backfill write."
    )
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Path to the assertion_ledger workspace directory (e.g. "
        "assertion_ledger/workspaces/<workspace_key>).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write. Omit for a zero-write preview receipt showing exactly what "
        "would be written (default).",
    )
    parser.add_argument(
        "--pinned-receipt",
        default=None,
        help="Path to the approved dry-run/preview receipt naming the exact eligible "
        "edition-ID set this apply is scoped to. REQUIRED with --apply (B2) -- an unpinned "
        "live apply is refused.",
    )
    parser.add_argument(
        "--expect-count",
        type=int,
        default=None,
        help="Optional extra assertion: the live eligible count must also equal this number.",
    )
    parser.add_argument(
        "--out",
        default=None,
        # Nit1: see _main's --out comment for why this default is the opposite.
        help="Path to write the JSON receipt to. Defaults to "
        "<workspace-root>/backfill_operations/<receipt_id>.json when --apply is "
        "set, or stdout for a preview.",
    )
    args = parser.parse_args(argv)

    workspace_root = Path(args.workspace_root)
    if not workspace_root.exists():  # N1
        parser.error(f"--workspace-root does not exist: {workspace_root}")
    if args.apply and not (workspace_root / "sources").exists():
        parser.error(
            f"--workspace-root does not look like a ledger workspace (no 'sources' dir): {workspace_root}"
        )

    pinned_receipt = None
    if args.pinned_receipt:
        pinned_receipt = json.loads(Path(args.pinned_receipt).read_text(encoding="utf-8"))
    if args.apply and pinned_receipt is None:
        parser.error("--apply requires --pinned-receipt (B2): an unpinned live apply is not permitted")

    receipt = apply_backfill(
        workspace_root,
        apply=args.apply,
        pinned_receipt=pinned_receipt,
        expect_count=args.expect_count,
    )

    out_path = Path(args.out) if args.out else None
    if out_path is None and args.apply:
        out_path = workspace_root / "backfill_operations" / f"{receipt['receipt_id']}.json"

    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


def _rollback_main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Preview (default) or apply a rollback of an M2 extraction_status backfill."
    )
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Path to the assertion_ledger workspace directory (e.g. "
        "assertion_ledger/workspaces/<workspace_key>).",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--receipt",
        default=None,
        help="Path to a JSON apply receipt (as written by 'apply --apply') to roll back.",
    )
    source_group.add_argument(
        "--journal",
        default=None,
        help="Path to a write-ahead journal (*.journal.jsonl) to derive a receipt from directly "
        "-- use this when the process that ran 'apply --apply' crashed before it could write a "
        "receipt file (item 1).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually restore. Omit for a zero-write preview showing exactly what would be "
        "restored (default).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional path to write the JSON rollback receipt to. Defaults to stdout.",
    )
    args = parser.parse_args(argv)

    workspace_root = Path(args.workspace_root)
    if not workspace_root.exists():  # N1
        parser.error(f"--workspace-root does not exist: {workspace_root}")

    if args.journal:
        receipt = receipt_from_journal(workspace_root, Path(args.journal))
    else:
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))

    result = rollback_backfill(workspace_root, receipt, apply=args.apply)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    _argv = sys.argv[1:]
    if _argv and _argv[0] == "apply":
        raise SystemExit(_apply_main(_argv[1:]))
    if _argv and _argv[0] == "rollback":
        raise SystemExit(_rollback_main(_argv[1:]))
    raise SystemExit(_main(_argv))
