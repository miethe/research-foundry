"""External Research Report Interchange (ERI) v1 — Phase 2: staging and
immutable receipts.

Implements ERI-2.1 (safe packet inspection), ERI-2.2 (stable staging
manifest), ERI-2.3 (effects and terminal receipt), and ERI-2.4 (replay,
conflict, dry-run) per the frozen contract:
``docs/dev/architecture/external-research-handoff-contract.md`` and
``.claude/findings/external-research-report-interchange-findings.md``.

Scope boundary (binding, not a simplification): this module owns packet
identity, staging, and receipt/checkpoint bookkeeping only. It introduces no
second source-edition, passage, source-assertion, extraction, or
citation-tuple authority (contract §3.5). Per-source/per-candidate
*resolution* (RFUP acquisition, RAL passage binding, RF verification) is
Phase 4's job, not this module's; :func:`stage` accepts injectable
``resolve_source``/``resolve_candidate`` callables so Phase 4 can plug in the
real SSRF-safe acquisition/resolution pipeline without touching this
module's staging/receipt mechanics. The default resolvers shipped here are
deliberately conservative — honest about what a phase with zero acquisition
capability can determine (see their docstrings) — not a preview of Phase 4's
behavior.

Traversal safety mirrors ``AssertionRegistry._read_regular_file``
(``assertion_registry.py:274-340``) per the contract's explicit instruction
(§1.1): an openat-style directory-descriptor walk pinned to the packet root,
``O_NOFOLLOW`` on every path component, an ``lstat``-before-open symlink
rejection, and an ``fstat``-after-open device/inode check that closes the
``lstat`` -> ``open`` TOCTOU window. It is generalized here to an arbitrary
operator-supplied packet directory (not a ``FoundryPaths``-pinned workspace
root) and adds an explicit ``.``/``..``/absolute-path rejection, because
``dir_fd``-relative opens do not themselves prevent a literal ``..``
component from resolving above the pinned root.

Every packet-member value is untrusted producer-declared DATA (contract
§4.1). Packet-local IDs (``source_id`` / ``candidate_id``) are therefore
never used as raw filesystem path components anywhere in this module — every
on-disk name derived from one is a SHA-256 digest of the id, never the id
itself.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import time
import uuid
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from yaml.composer import ComposerError
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

from ..errors import ExitCode, RFError
from ..ids import now_iso
from ..paths import FoundryPaths
from ..schemas import validate as schema_validate
from ..yamlio import dumps_yaml, loads_yaml

# ---------------------------------------------------------------------------
# Frozen limits (ERI-OQ-4) — never independently configurable above these
# ceilings; :class:`Limits` only permits tightening them for tests.
# ---------------------------------------------------------------------------

_MAX_MEMBERS = 64
_MAX_PACKET_BYTES = 268_435_456  # 256 MiB
_MAX_MEMBER_BYTES = 67_108_864  # 64 MiB
_MAX_ATTACHMENTS = 32
_MAX_SOURCES = 2000
_MAX_CANDIDATES = 5000

_MANIFEST_FILENAME = "handoff.yaml"

# Closed reason-code vocabulary (contract §2.3 / PRD §6.5) — 19 codes, 4
# families. Enumerated verbatim so a typo can never mint a 20th code.
PACKET_REASON_CODES = frozenset(
    {
        "required_member_missing",
        "unsupported_schema_version",
        "unsafe_member_path",
        "member_digest_conflict",
        "limit_exceeded",
    }
)
SOURCE_REASON_CODES = frozenset(
    {
        "invalid_locator",
        "source_unavailable",
        "rights_metadata_missing",
        "sensitivity_denied",
        "source_drift",
        "edition_binding_conflict",
    }
)
CANDIDATE_REASON_CODES = frozenset(
    {
        "citation_unresolved",
        "citation_ambiguous",
        "citation_mismatch",
        "passage_binding_conflict",
        "basis_incomplete",
        "relation_invalid",
        "verification_failed",
        "cross_workspace_denied",
    }
)
COMPLETENESS_TIERS = ("locator_only", "source_resolved", "passage_resolved", "verified")

_RECEIPT_STATUSES = ("completed", "completed_with_quarantine", "blocked")

# RF-emitted schema majors this importer contract version understands. Used
# both to fill schema_major_versions when producer content cannot be parsed
# far enough to declare its own version, and as the majors for the three
# RF-owned schemas (receipt/checkpoint/acquisition-policy) that no packet
# ever declares.
_CURRENT_SCHEMA_MAJORS: dict[str, int] = {
    "external_research_handoff": 1,
    "external_research_sources": 1,
    "external_assertion_candidates": 1,
    "external_research_import_receipt": 1,
    "external_research_import_checkpoint": 1,
    "external_research_acquisition_policy": 1,
}

_IMPORTER_CONTRACT_VERSION = "external_research_handoff/v1"

_CHUNK_SIZE = 1 << 20  # 1 MiB streaming read window

# Single-writer receipt-identity lease (contract audit finding #8).
_LEASE_POLL_INTERVAL_SECONDS = 0.05
_LEASE_MAX_WAIT_SECONDS = 30.0
_LEASE_STALE_SECONDS = 300.0  # a crashed/killed writer's lease is reclaimable after this


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class InterchangeError(RFError):
    """Base class for ERI staging/receipt errors."""


class ReplayConflictError(InterchangeError):
    """A receipt_digest already has a persisted history that does not match.

    Per contract §1.5 case 3, this should be structurally unreachable in
    normal operation; its only realistic causes are a tampered/corrupted
    on-disk receipt directory or an importer defect. It always fails closed
    and never merges or overwrites the stored history.
    """

    exit_code = ExitCode.GOVERNANCE


class PacketTraversalError(InterchangeError):
    """A packet member escapes containment, is a symlink, or is a special file."""

    exit_code = ExitCode.SCHEMA


class MemberOversizeError(InterchangeError):
    """A packet member (or the packet total) exceeds a frozen byte ceiling."""

    exit_code = ExitCode.SCHEMA


class StagingIntegrityError(InterchangeError):
    """A persisted staging artifact does not match its expected identity."""

    exit_code = ExitCode.GOVERNANCE


class CallerNotAuthorizedError(InterchangeError):
    """Contract §2.4 Step 0 / §1.6 gate failure (audit finding #9 closure).

    Raised before structural validation and before any receipt existence
    lookup or return — a fresh import attempt and a replay attempt alike.
    No receipt of any kind (not even ``blocked``) is created or returned
    for a caller that fails this gate; the caller-visible denial carries
    none of the packet/workspace-specific detail contract §4.3 reserves
    for later, already-authorized stages. See the module-level comment on
    :func:`authorize_caller` for exactly what this does and does not cover.
    """

    exit_code = ExitCode.GOVERNANCE


class ResolutionDeclined(Exception):
    """A ``resolve_source``/``resolve_candidate`` call was declined BEFORE
    the wrapped resolution logic ran at all -- structurally guaranteed to
    have produced no downstream mutation (round-2 audit finding #5).

    ``external_research_import.py``'s per-invocation batch-limit signal
    (`_BatchLimitReached`) is the one shipped subclass: its wrapper checks
    the fresh-resolution counter and raises BEFORE calling the underlying
    resolve callable, never after. ``_execute`` treats this distinctly from
    every other exception a resolver can raise: it clears the just-written
    outbox "prepare" marker for the in-flight action before re-raising,
    because this specific signal proves no resolver-side mutation was
    attempted -- unlike an arbitrary resolver exception (which may have
    fired partway through a real downstream mutation and must leave the
    marker in place for the fail-closed resume check to see). Never a
    subclass of :class:`RFError` -- like `_BatchLimitReached` itself, it is
    an internal control-flow signal, not a user-facing error.
    """


# ---------------------------------------------------------------------------
# Canonical digest helpers — same ``sha256-canonical-json-v1`` convention as
# ``AssertionRegistry._canonical_digest`` (assertion_registry.py:45-47),
# reimplemented locally per the contract's "reuse the naming convention, not
# a cross-module private import" precedent (contract §1.2).
# ---------------------------------------------------------------------------


def _digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _digest(encoded)


def _atomic_dump(data: Mapping[str, Any], path: Path) -> None:
    """Atomically replace one YAML artifact without exposing partial YAML."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps_yaml(dict(data)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _publish_immutable_file(data: bytes, path: Path) -> bool:
    """True create-if-absent CAS publish (round-2 audit finding #4).

    The prior implementation was ``path.exists()`` THEN either compare-and-
    return or ``os.replace`` a fully-written temp file into place — an
    existence check followed by an unconditional overwrite is not a CAS: a
    second writer's ``os.replace`` between the first writer's existence
    check and its own ``os.replace`` silently clobbers whatever the first
    writer just published (a lost update), and neither writer can tell it
    happened.

    This instead always fully writes+fsyncs a temp file first (so the bytes
    a reader can ever observe at ``path`` are always a complete, valid
    write — never a partial one), then attempts ``os.link(temp, path)`` —
    hard-link creation is atomic create-if-absent on POSIX: it fails with
    ``FileExistsError`` if ``path`` already exists and never overwrites it.
    Returns ``True`` if THIS call created ``path`` (i.e. won the race);
    ``False`` if ``path`` already existed (caller must then compare bytes
    for the immutable-conflict check, exactly as before).
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            return False
    finally:
        with suppress(FileNotFoundError):
            temporary.unlink()


def _write_immutable_mapping(data: Mapping[str, Any], path: Path) -> None:
    """Write once; a re-write with different bytes is a staging integrity error."""

    encoded = dumps_yaml(dict(data)).encode("utf-8")
    if _publish_immutable_file(encoded, path):
        return
    existing = loads_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(existing, Mapping) or dict(existing) != dict(data):
        raise StagingIntegrityError(f"immutable staging record conflicts with existing bytes: {path.name}")


def _write_immutable_bytes(data: bytes, path: Path) -> None:
    if _publish_immutable_file(data, path):
        return
    existing = path.read_bytes()
    if existing != data:
        raise StagingIntegrityError(f"immutable staged content conflicts with existing bytes: {path.name}")


# ---------------------------------------------------------------------------
# Inert-data-boundary YAML parsing (contract audit finding #12) — every
# packet-derived document (handoff.yaml, sources.yaml,
# assertion_candidates.yaml) is untrusted producer DATA and is parsed with a
# hardened loader before schema validation ever runs, so hostile content can
# never act *during* parsing:
#   - object/python constructor tags: already rejected by ``yaml.SafeLoader``
#     itself (no ``!!python/object/apply:`` etc.); locked in by regression
#     tests here, not reimplemented.
#   - merge keys (``<<``) and alias/anchor reuse: rejected outright. Blocking
#     every alias resolution also closes the "billion laughs" vector without
#     needing a size heuristic — packet content never legitimately needs
#     YAML back-references.
#   - duplicate mapping keys (YAML- or JSON-flow-style): rejected, so the
#     parsed representation schema validation sees can never silently differ
#     from what a naive re-read of the same bytes would show.
#   - unbounded nesting / node count: capped. Reachable even in
#     schema-valid content through open ``additionalProperties: true``
#     fields (``sources[].extensions``, ``assertion_candidates[].selector``)
#     and would otherwise risk an uncaught ``RecursionError`` inside
#     PyYAML's own recursive composer.
#   - non-finite floats (``.nan`` / ``.inf`` / ``-.inf``): rejected.
# Schema validation always runs against this exact parsed representation
# (never against the raw bytes), closing the "differential" gap the finding
# describes.
# ---------------------------------------------------------------------------

_MAX_PARSE_DEPTH = 64
_MAX_PARSE_NODES = 100_000


class _InertDocumentError(Exception):
    """Packet-derived YAML violated the inert-data parsing boundary.

    Always caught immediately at the call site and converted to a safe,
    closed-vocabulary packet ``reason_code`` — never propagates out of
    :func:`inspect_packet` (which never raises for hostile packet content).
    """


class _InertYAMLLoader(yaml.SafeLoader):
    """``yaml.SafeLoader`` hardened for untrusted packet-derived content.

    Object/python tags are already rejected by ``SafeLoader`` itself. This
    adds: alias/anchor reuse rejection, merge-key rejection, duplicate-key
    rejection, and a nesting-depth / total-node ceiling.
    """

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self._rf_depth = 0
        self._rf_node_count = 0

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(AliasEvent):
            mark = self.peek_event().start_mark
            raise ComposerError(
                None, None, "alias/anchor reuse is not permitted in packet-derived YAML", mark
            )
        self._rf_node_count += 1
        if self._rf_node_count > _MAX_PARSE_NODES:
            raise ComposerError(None, None, "document node count exceeds the safe limit", self.get_mark())
        self._rf_depth += 1
        try:
            if self._rf_depth > _MAX_PARSE_DEPTH:
                raise ComposerError(None, None, "document nesting exceeds the safe limit", self.get_mark())
            return super().compose_node(parent, index)
        finally:
            self._rf_depth -= 1

    def flatten_mapping(self, node: Any) -> None:
        for key_node, _value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ConstructorError(
                    None,
                    None,
                    "merge keys ('<<') are not permitted in packet-derived YAML",
                    key_node.start_mark,
                )
        return super().flatten_mapping(node)

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
            seen: list[Any] = []
            for key_node, _value_node in node.value:
                key = self.construct_object(key_node, deep=True)
                if any(key == existing for existing in seen):
                    raise ConstructorError(
                        None, None, f"duplicate mapping key {key!r} is not permitted", key_node.start_mark
                    )
                seen.append(key)
        return super().construct_mapping(node, deep=deep)


def _construct_finite_float(loader: _InertYAMLLoader, node: Any) -> float:
    value = yaml.SafeLoader.construct_yaml_float(loader, node)
    if value != value or value in (float("inf"), float("-inf")):  # NaN is the only self-unequal float
        raise ConstructorError(
            None, None, "non-finite numeric values are not permitted in packet-derived YAML", node.start_mark
        )
    return value


_InertYAMLLoader.add_constructor("tag:yaml.org,2002:float", _construct_finite_float)


def _reject_non_primitive_tag(loader: _InertYAMLLoader, node: Any) -> Any:
    """Reject a YAML tag outright at construction time (round-2 audit
    finding #7) rather than let ``SafeLoader`` hand back a non-JSON Python
    value that later crashes canonical-JSON digesting.

    ``yaml.SafeLoader`` still constructs ``tag:yaml.org,2002:timestamp`` /
    ``!!binary`` / ``!!set`` / ``!!omap`` / ``!!pairs`` into
    ``datetime``/``date``, ``bytes``, ``set``, and ordered-pair Python
    objects respectively -- none of which is null/bool/string/finite-number/
    list/string-keyed-map. An open ``additionalProperties: true`` extension
    field lets any of these through schema validation (which only checks
    JSON-shaped structure, not the underlying Python type), and the
    resulting non-JSON-serializable value then raises an uncaught
    ``TypeError`` inside ``json.dumps`` the first time canonical-digest
    identity computation touches it -- reproduced directly on this tree
    before this fix.
    """

    raise ConstructorError(
        None, None, f"packet-derived YAML tag is not permitted: {node.tag}", node.start_mark
    )


for _forbidden_tag in (
    "tag:yaml.org,2002:timestamp",
    "tag:yaml.org,2002:binary",
    "tag:yaml.org,2002:set",
    "tag:yaml.org,2002:omap",
    "tag:yaml.org,2002:pairs",
):
    _InertYAMLLoader.add_constructor(_forbidden_tag, _reject_non_primitive_tag)


_MAX_SCALAR_LENGTH = 1_048_576  # 1 MiB -- generous headroom under the 64 MiB member ceiling


def _assert_json_primitive_only(value: Any) -> None:
    """Final whitelist gate (round-2 audit finding #7).

    Recursively permits ONLY null / bool / string / finite-number / list /
    string-keyed-map values -- the exact JSON-primitive vocabulary
    ``sha256-canonical-json-v1`` digesting can serialize without raising.
    This is deliberately a second, independent layer on top of the
    constructor-level tag rejections above (belt-and-suspenders): even if a
    future PyYAML version, a different loader path, or a tag this module
    did not anticipate ever handed back a non-primitive Python value, this
    walk still catches it here, before schema validation, rather than
    inside a later canonical-digest call site far from the parse boundary.
    Also enforces a scalar-size ceiling on strings and mapping keys.
    """

    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        if len(value) > _MAX_SCALAR_LENGTH:
            raise _InertDocumentError("scalar string exceeds the safe length ceiling")
        return
    if isinstance(value, int):  # bool already handled above
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise _InertDocumentError("non-finite numeric value is not permitted")
        return
    if isinstance(value, list):
        for item in value:
            _assert_json_primitive_only(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _InertDocumentError(f"non-string mapping key is not permitted: {key!r}")
            if len(key) > _MAX_SCALAR_LENGTH:
                raise _InertDocumentError("mapping key exceeds the safe length ceiling")
            _assert_json_primitive_only(item)
        return
    raise _InertDocumentError(f"packet-derived YAML value type is not permitted: {type(value).__name__}")


def _load_inert_yaml(text: str) -> Any:
    """Parse one packet-derived YAML document inside the inert-data boundary.

    Raises :class:`_InertDocumentError` (never a raw ``yaml`` exception, and
    never an uncaught ``RecursionError``) on any hostile or malformed input.
    """

    if not text or not text.strip():
        return None
    try:
        value = yaml.load(text, Loader=_InertYAMLLoader)
    except RecursionError as exc:
        raise _InertDocumentError("document nesting exceeds the safe recursion limit") from exc
    except yaml.YAMLError as exc:
        raise _InertDocumentError(str(exc)) from exc
    _assert_json_primitive_only(value)
    return value


# ---------------------------------------------------------------------------
# Traversal-safe, streaming member access
# ---------------------------------------------------------------------------


def _reject_unsafe_relative_path(relative: str) -> PurePosixPath:
    candidate = PurePosixPath(relative)
    if candidate.is_absolute():
        raise PacketTraversalError(f"absolute member path rejected: {relative}")
    parts = candidate.parts
    if not parts or any(part in (".", "..") or not part for part in parts):
        raise PacketTraversalError(f"unsafe member path rejected: {relative}")
    return candidate


def _open_checked(name: str | Path, *, parent_fd: int | None, directory: bool) -> int:
    """Open one path component pinned under ``parent_fd`` with symlink/TOCTOU checks."""

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    o_directory = getattr(os, "O_DIRECTORY", 0)
    before = os.lstat(name) if parent_fd is None else os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode):
        raise PacketTraversalError(f"symlink member rejected: {name}")
    flags = os.O_RDONLY | no_follow | (o_directory if directory else 0)
    fd = os.open(name, flags) if parent_fd is None else os.open(name, flags, dir_fd=parent_fd)
    after = os.fstat(fd)
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or (directory and not stat.S_ISDIR(after.st_mode))
        or (not directory and not stat.S_ISREG(after.st_mode))
    ):
        os.close(fd)
        raise PacketTraversalError(f"member path substitution rejected: {name}")
    if not directory and after.st_nlink > 1:
        # A multiply-linked regular file can be mutated through the other
        # link (or through an already-open write descriptor elsewhere)
        # after this read completes and its bytes are hashed/verified,
        # without the packet_digest or this open ever seeing that write
        # (contract audit finding #7). Directories legitimately carry
        # st_nlink > 1 (self + parent references) so this check is scoped
        # to regular-file members only.
        os.close(fd)
        raise PacketTraversalError(f"multiply-linked member rejected: {name}")
    return fd


def _stream_member(
    root: Path,
    relative: PurePosixPath,
    *,
    max_bytes: int,
    keep_bytes: bool,
) -> tuple[int, str, bytes | None]:
    """Stream-hash one member pinned under ``root``.

    Never materializes the full byte stream unless ``keep_bytes`` is set
    (used only for the three required, schema-bounded YAML members that must
    be parsed; report/attachment members are always streamed with
    ``keep_bytes=False`` per the "never read a whole member into memory"
    requirement). Raises :class:`PacketTraversalError` /
    :class:`MemberOversizeError` on hostile input.
    """

    if relative.is_absolute():
        raise PacketTraversalError(f"absolute member path rejected: {relative}")
    parts = relative.parts
    if not parts or any(part in (".", "..") or not part for part in parts):
        raise PacketTraversalError(f"unsafe member path rejected: {relative}")

    root_fd: int | None = None
    dir_fds: list[int] = []
    file_fd: int | None = None
    try:
        root_fd = _open_checked(root, parent_fd=None, directory=True)
        current = root_fd
        for part in parts[:-1]:
            fd = _open_checked(part, parent_fd=current, directory=True)
            dir_fds.append(fd)
            current = fd
        file_fd = _open_checked(parts[-1], parent_fd=current, directory=False)
        digest = sha256()
        total = 0
        buffer = bytearray() if keep_bytes else None
        with os.fdopen(file_fd, "rb", closefd=True) as handle:
            file_fd = None
            while True:
                chunk = handle.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise MemberOversizeError(f"member exceeds byte ceiling: {relative}")
                digest.update(chunk)
                if buffer is not None:
                    buffer.extend(chunk)
        return total, digest.hexdigest(), (bytes(buffer) if buffer is not None else None)
    finally:
        if file_fd is not None:
            os.close(file_fd)
        for fd in reversed(dir_fds):
            os.close(fd)
        if root_fd is not None:
            os.close(root_fd)


def _discover_regular_files(root: Path) -> list[PurePosixPath]:
    """Recursively enumerate every regular-file member under ``root``.

    Rejects (raises :class:`PacketTraversalError`) on any symlink or
    special (fifo/socket/device/block) entry anywhere in the tree, including
    intermediate directories. This is the discovery pass used to detect
    undeclared members; the subsequent per-member read still independently
    re-verifies containment/regularity via :func:`_stream_member`.
    """

    root_real = root.resolve(strict=True)
    if not root_real.is_dir():
        raise PacketTraversalError("packet root is not a directory")
    discovered: list[PurePosixPath] = []
    stack: list[Path] = [root_real]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            raise PacketTraversalError(f"cannot list packet directory: {exc}") from exc
        for entry in entries:
            if entry.is_symlink():
                raise PacketTraversalError(f"symlink member rejected: {entry.name}")
            st = entry.stat(follow_symlinks=False)
            entry_path = Path(entry.path)
            if stat.S_ISDIR(st.st_mode):
                stack.append(entry_path)
                continue
            if not stat.S_ISREG(st.st_mode):
                raise PacketTraversalError(f"special file member rejected: {entry.name}")
            try:
                relative = entry_path.resolve(strict=True).relative_to(root_real)
            except ValueError as exc:
                raise PacketTraversalError(f"member escapes packet root: {entry.name}") from exc
            discovered.append(PurePosixPath(relative.as_posix()))
    return discovered


# ---------------------------------------------------------------------------
# Packet inspection (ERI-2.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Limits:
    """Structural ceilings. Only tightening (never loosening) the frozen v1
    maximums is permitted — mirrors the acquisition-policy schema's "only
    the numeric ceilings are operator-tunable, and only downward" posture.
    """

    max_members: int = _MAX_MEMBERS
    max_packet_bytes: int = _MAX_PACKET_BYTES
    max_member_bytes: int = _MAX_MEMBER_BYTES
    max_attachments: int = _MAX_ATTACHMENTS
    max_sources: int = _MAX_SOURCES
    max_candidates: int = _MAX_CANDIDATES

    def __post_init__(self) -> None:
        if (
            self.max_members > _MAX_MEMBERS
            or self.max_packet_bytes > _MAX_PACKET_BYTES
            or self.max_member_bytes > _MAX_MEMBER_BYTES
            or self.max_attachments > _MAX_ATTACHMENTS
            or self.max_sources > _MAX_SOURCES
            or self.max_candidates > _MAX_CANDIDATES
        ):
            raise ValueError("Limits cannot exceed the frozen v1 ceilings")


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class PacketMember:
    path: str
    role: str
    byte_length: int
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "role": self.role, "byte_length": self.byte_length, "sha256": self.sha256}


def _packet_digest_from_declared(members: Sequence[PacketMember]) -> str:
    """packet_digest (contract §1.2): SHA-256 over the canonically-sorted
    declared manifest of (path, byte_length, sha256).

    Computed uniformly from the DECLARED manifest (handoff.yaml's own
    ``members`` array), whether the packet is ultimately accepted or
    blocked. For an accepted packet this is provably identical to computing
    the digest over the runtime-VERIFIED members, because acceptance itself
    requires every declared member to match its verified bytes exactly — any
    mismatch blocks before this digest would otherwise diverge.
    """

    entries = sorted(
        (m.as_dict() for m in members),
        key=lambda e: e["path"],
    )
    return _canonical_digest(entries)


def _extract_declared_members(handoff_doc: Any) -> list[PacketMember]:
    """Best-effort extraction of a declared members list from possibly-invalid content.

    Used so a blocked receipt can still carry a deterministic packet_digest
    even when the handoff document fails full schema validation.
    """

    members: list[PacketMember] = []
    if not isinstance(handoff_doc, Mapping):
        return members
    raw = handoff_doc.get("members")
    if not isinstance(raw, list):
        return members
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        path, role = item.get("path"), item.get("role")
        byte_length, sha = item.get("byte_length"), item.get("sha256")
        if not isinstance(path, str) or not isinstance(role, str):
            continue
        if not isinstance(byte_length, int) or isinstance(byte_length, bool) or not isinstance(sha, str):
            continue
        members.append(PacketMember(path=path, role=role, byte_length=byte_length, sha256=sha))
    return members


def _classify_handoff_schema_errors(errors: Sequence[str]) -> str:
    """Map a handoff.yaml schema-validation failure onto the closed packet
    reason-code vocabulary. A best-effort classifier, not a second schema
    authority — the schema itself remains the sole shape authority; this
    only routes its failure to one of the five safe codes so a `blocked`
    receipt never carries a free-text detail.
    """

    joined = " ".join(errors)
    lowered = joined.lower()
    if "schema_version" in joined or "transport" in joined:
        return "unsupported_schema_version"
    if "too many items" in lowered or "expected at most" in lowered:
        return "limit_exceeded"
    if (
        "is too short" in lowered
        or "does not contain items" in lowered
        or "is a required property" in joined
    ):
        return "required_member_missing"
    if "members" in joined or "path" in joined:
        return "unsafe_member_path"
    return "required_member_missing"


@dataclass(frozen=True)
class PacketInspection:
    """Outcome of ERI-2.1 packet inspection. Never raises for hostile packet
    content — hostile/malformed content is reported via ``ok=False`` and a
    safe ``reason_code``; only genuine caller-usage errors (packet_dir does
    not exist) raise.
    """

    ok: bool
    reason_code: str | None
    packet_digest: str
    declared_members: tuple[PacketMember, ...]
    handoff: Mapping[str, Any] | None
    sources_doc: Mapping[str, Any] | None
    candidates_doc: Mapping[str, Any] | None
    schema_major_versions: dict[str, int]
    report_member: PacketMember | None
    report_bytes: bytes | None
    packet_root: Path
    attempt_structural_summary: dict[str, int] | None

    @property
    def source_records(self) -> list[dict[str, Any]]:
        if not self.sources_doc:
            return []
        return list(self.sources_doc.get("sources", []) or [])

    @property
    def candidate_records(self) -> list[dict[str, Any]]:
        if not self.candidates_doc:
            return []
        return list(self.candidates_doc.get("candidates", []) or [])


def _blocked(
    reason_code: str,
    *,
    root: Path,
    declared: Sequence[PacketMember] = (),
    schema_major_versions: Mapping[str, int] | None = None,
    observed_member_count: int = 0,
    raw_bytes_total: int = 0,
) -> PacketInspection:
    if reason_code not in PACKET_REASON_CODES:
        raise ValueError(f"invalid packet reason_code: {reason_code}")
    majors = dict(_CURRENT_SCHEMA_MAJORS)
    majors.update(schema_major_versions or {})
    return PacketInspection(
        ok=False,
        reason_code=reason_code,
        packet_digest=_packet_digest_from_declared(declared),
        declared_members=tuple(declared),
        handoff=None,
        sources_doc=None,
        candidates_doc=None,
        schema_major_versions=majors,
        report_member=None,
        report_bytes=None,
        packet_root=root,
        # Safely captured request metadata for the rejected-attempt identity
        # branch (contract §1.3/§1.3a, audit finding #10): counts only,
        # derived from the same pinned/verified walk that inspects the
        # packet, and always reflecting totals *as of the point of
        # rejection* — never data about the member that triggered it, so
        # this never reveals WHERE a structural failure occurred.
        attempt_structural_summary={
            "observed_member_count": observed_member_count,
            "raw_bytes_total": raw_bytes_total,
        },
    )


def inspect_packet(packet_dir: str | Path, *, limits: Limits | None = None) -> PacketInspection:
    """ERI-2.1: safe packet inspection before any effect.

    Verifies directory containment, rejects symlinks/special/non-regular
    files, rejects undeclared members, enforces the frozen limits, validates
    schema major versions, and computes streaming member SHA-256 — all
    before any downstream effect runs.
    """

    limits = limits or DEFAULT_LIMITS
    root = Path(packet_dir)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"packet_dir does not exist or is not a directory: {root}")
    root = root.resolve(strict=True)

    try:
        discovered = _discover_regular_files(root)
    except PacketTraversalError:
        return _blocked("unsafe_member_path", root=root)
    discovered_set = set(discovered)

    manifest_relative = PurePosixPath(_MANIFEST_FILENAME)
    if manifest_relative not in discovered_set:
        return _blocked("required_member_missing", root=root)

    try:
        _length, _sha, raw_bytes = _stream_member(
            root, manifest_relative, max_bytes=limits.max_member_bytes, keep_bytes=True
        )
    except MemberOversizeError:
        return _blocked("limit_exceeded", root=root)
    except PacketTraversalError:
        return _blocked("unsafe_member_path", root=root)
    assert raw_bytes is not None
    try:
        handoff_doc = _load_inert_yaml(raw_bytes.decode("utf-8"))
    except Exception:  # noqa: BLE001 - any parse failure is a packet-blocked outcome, not a crash
        return _blocked("unsupported_schema_version", root=root, declared=_extract_declared_members(None))

    declared = _extract_declared_members(handoff_doc)

    validation = schema_validate(handoff_doc, "external_research_handoff")
    if not validation.ok:
        reason = _classify_handoff_schema_errors(validation.errors)
        return _blocked(reason, root=root, declared=declared)

    # From here handoff.yaml is schema-valid: `declared` is exact and
    # complete (schema already enforces path pattern, role enum, one of
    # each required role, member/attachment count ceilings).
    handoff_major = _major(handoff_doc.get("schema_version")) or 1
    if handoff_major != _CURRENT_SCHEMA_MAJORS["external_research_handoff"]:
        return _blocked(
            "unsupported_schema_version",
            root=root,
            declared=declared,
            schema_major_versions={"external_research_handoff": handoff_major},
        )

    # Cross-item member-path uniqueness (round-2 audit finding #8): plain
    # JSON Schema cannot express uniqueness of a single field across array
    # items, so the schema's per-role maxContains only closes the
    # duplicate-role half. Two members declaring the same `path` under
    # different roles would otherwise collapse into one entry when
    # `declared_paths` is built below — the set comparison against
    # `discovered_set` never fires, and parsing/action construction could
    # bind one member's content to another member's provenance.
    #
    # Both checks are normalization-aware (final Karen gate): downstream
    # member opens go through PurePosixPath, which silently drops `.`
    # segments and collapses `//`, so `attachments/./t.csv` and
    # `attachments//t.csv` alias `attachments/t.csv` on disk. A raw-string
    # comparison alone is therefore bypassable by alias spellings. Each
    # declared path must already be in canonical POSIX form (rejecting the
    # alias class outright, not just known spellings), and uniqueness is
    # then enforced on the canonical form.
    for member in declared:
        if PurePosixPath(member.path).as_posix() != member.path:
            return _blocked("unsafe_member_path", root=root, declared=declared)
    if len({PurePosixPath(m.path) for m in declared}) != len(declared):
        return _blocked("unsafe_member_path", root=root, declared=declared)

    # From here every declared entry's own (path, byte_length) is trusted
    # manifest metadata (not yet content-verified) — a legitimate "observed"
    # count/total for a structural rejection from this point on, per §1.3a's
    # "safely captured request metadata" rejected-attempt identity.
    declared_sum_unverified = sum(m.byte_length for m in declared)

    if len(declared) > limits.max_members:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=len(declared),
            raw_bytes_total=declared_sum_unverified,
        )
    attachment_count = sum(1 for m in declared if m.role == "attachment")
    if attachment_count > limits.max_attachments:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=len(declared),
            raw_bytes_total=declared_sum_unverified,
        )

    declared_paths = {PurePosixPath(m.path) for m in declared}
    if declared_paths != discovered_set:
        missing = declared_paths - discovered_set
        if missing:
            return _blocked(
                "required_member_missing",
                root=root,
                declared=declared,
                observed_member_count=len(declared),
                raw_bytes_total=declared_sum_unverified,
            )
        # Extra files on disk beyond the declared manifest: an undeclared
        # member is never trusted, regardless of its content (contract §1.1,
        # "Any accepted byte not listed here fails closed").
        return _blocked(
            "unsafe_member_path",
            root=root,
            declared=declared,
            observed_member_count=len(declared),
            raw_bytes_total=declared_sum_unverified,
        )

    total_declared_bytes = handoff_doc.get("total_declared_bytes")
    declared_sum = sum(m.byte_length for m in declared)
    if not isinstance(total_declared_bytes, int) or total_declared_bytes != declared_sum:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=len(declared),
            raw_bytes_total=declared_sum_unverified,
        )
    if declared_sum > limits.max_packet_bytes:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=len(declared),
            raw_bytes_total=declared_sum_unverified,
        )

    report_member: PacketMember | None = None
    report_bytes: bytes | None = None
    verified_total = 0
    processed_count = 0
    sources_doc: Any = None
    candidates_doc: Any = None
    for member in declared:
        if member.role == "handoff_manifest":
            # handoff.yaml declares its own (path, byte_length, sha256) as
            # one of its own members[] entries — inherently circular to
            # verify against itself (the declared hash necessarily covers
            # bytes that include the declaration of that very hash). This
            # entry's declared values are trusted as-is for packet_digest
            # (which is defined over the DECLARED manifest, contract §1.2)
            # and its declared byte_length still counts toward the total
            # byte ceiling; its content was already parsed once above.
            verified_total += member.byte_length
            processed_count += 1
            continue
        relative = PurePosixPath(member.path)
        # `report` is kept in memory too (never re-opened by path once
        # hashed here — contract audit finding #7): the bytes streamed and
        # verified in THIS pass are the exact, immutable bytes later
        # persisted as the governed report artifact in
        # ``_stage_packet_artifacts``. Re-reading report.md a second time,
        # later, by path would reopen a window for its bytes to have
        # changed underneath the verified digest (e.g. a write through an
        # external hardlink or an already-open descriptor elsewhere).
        keep_bytes = member.role in ("sources", "assertion_candidates", "report")
        try:
            length, sha, content = _stream_member(
                root, relative, max_bytes=limits.max_member_bytes, keep_bytes=keep_bytes
            )
        except MemberOversizeError:
            return _blocked(
                "limit_exceeded",
                root=root,
                declared=declared,
                observed_member_count=processed_count,
                raw_bytes_total=verified_total,
            )
        except PacketTraversalError:
            return _blocked(
                "unsafe_member_path",
                root=root,
                declared=declared,
                observed_member_count=processed_count,
                raw_bytes_total=verified_total,
            )
        if length != member.byte_length or sha != member.sha256:
            return _blocked(
                "member_digest_conflict",
                root=root,
                declared=declared,
                observed_member_count=processed_count,
                raw_bytes_total=verified_total,
            )
        verified_total += length
        processed_count += 1
        if member.role == "report":
            report_member = member
            report_bytes = content
        elif member.role == "sources":
            try:
                sources_doc = _load_inert_yaml((content or b"").decode("utf-8"))
            except Exception:  # noqa: BLE001 - hostile/malformed sources.yaml is a packet-blocked outcome
                return _blocked(
                    "unsupported_schema_version",
                    root=root,
                    declared=declared,
                    observed_member_count=processed_count,
                    raw_bytes_total=verified_total,
                )
        elif member.role == "assertion_candidates":
            try:
                candidates_doc = _load_inert_yaml((content or b"").decode("utf-8"))
            except Exception:  # noqa: BLE001 - hostile/malformed candidates doc is a packet-blocked outcome
                return _blocked(
                    "unsupported_schema_version",
                    root=root,
                    declared=declared,
                    observed_member_count=processed_count,
                    raw_bytes_total=verified_total,
                )

    if verified_total > limits.max_packet_bytes:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=processed_count,
            raw_bytes_total=verified_total,
        )

    sources_validation = schema_validate(sources_doc, "external_research_sources")
    if not sources_validation.ok:
        return _blocked(
            _classify_handoff_schema_errors(sources_validation.errors),
            root=root,
            declared=declared,
            observed_member_count=processed_count,
            raw_bytes_total=verified_total,
        )
    candidates_validation = schema_validate(candidates_doc, "external_assertion_candidates")
    if not candidates_validation.ok:
        return _blocked(
            _classify_handoff_schema_errors(candidates_validation.errors),
            root=root,
            declared=declared,
            observed_member_count=processed_count,
            raw_bytes_total=verified_total,
        )

    if isinstance(sources_doc, Mapping) and len(sources_doc.get("sources", []) or []) > limits.max_sources:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=processed_count,
            raw_bytes_total=verified_total,
        )
    if isinstance(candidates_doc, Mapping) and len(candidates_doc.get("candidates", []) or []) > limits.max_candidates:
        return _blocked(
            "limit_exceeded",
            root=root,
            declared=declared,
            observed_member_count=processed_count,
            raw_bytes_total=verified_total,
        )

    sources_major = _major(sources_doc.get("schema_version")) if isinstance(sources_doc, Mapping) else None
    candidates_major = _major(candidates_doc.get("schema_version")) if isinstance(candidates_doc, Mapping) else None
    majors = dict(_CURRENT_SCHEMA_MAJORS)
    majors["external_research_handoff"] = handoff_major
    if sources_major is not None:
        majors["external_research_sources"] = sources_major
    if candidates_major is not None:
        majors["external_assertion_candidates"] = candidates_major
    for name, expected in _CURRENT_SCHEMA_MAJORS.items():
        if majors.get(name) != expected:
            return _blocked(
                "unsupported_schema_version",
                root=root,
                declared=declared,
                schema_major_versions=majors,
                observed_member_count=processed_count,
                raw_bytes_total=verified_total,
            )

    return PacketInspection(
        ok=True,
        reason_code=None,
        packet_digest=_packet_digest_from_declared(declared),
        declared_members=tuple(declared),
        handoff=handoff_doc,
        sources_doc=sources_doc if isinstance(sources_doc, Mapping) else {"sources": []},
        candidates_doc=candidates_doc if isinstance(candidates_doc, Mapping) else {"candidates": []},
        schema_major_versions=majors,
        report_member=report_member,
        report_bytes=report_bytes,
        packet_root=root,
        attempt_structural_summary=None,
    )


def _major(schema_version: Any) -> int | None:
    if not isinstance(schema_version, str) or "." not in schema_version:
        return None
    head = schema_version.split(".", 1)[0]
    return int(head) if head.isdigit() else None


# ---------------------------------------------------------------------------
# Resolution seam (Phase 4 plugs in the real SSRF-safe / RAL resolver here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionContext:
    workspace_id: str
    target_run_id: str | None
    policy: Mapping[str, Any]


@dataclass(frozen=True)
class ActionResolution:
    outcome: str  # "completed" | "quarantined"
    completeness_tier: str | None
    reason_code: str | None
    # `canonical_refs` (contract §1.3a): the downstream canonical
    # identifier(s) this action produced or reused (e.g. `source_edition_id`,
    # `passage_id`, `source_card_id`), or empty when none exist yet (Phase 2's
    # own default resolvers; a Phase-4-era `ResolvedActionResolution` always
    # sets this explicitly). Additive, defaulted field (Phase 5) — every
    # existing positional `ActionResolution(...)` call site across the
    # codebase is unaffected.
    canonical_refs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in ("completed", "quarantined"):
            raise ValueError(f"invalid action outcome: {self.outcome}")
        if self.outcome == "completed" and self.reason_code is not None:
            raise ValueError("completed action must not carry a reason_code")
        if self.outcome == "quarantined" and self.reason_code is None:
            raise ValueError("quarantined action must carry a reason_code")
        if self.completeness_tier is not None and self.completeness_tier not in COMPLETENESS_TIERS:
            raise ValueError(f"invalid completeness_tier: {self.completeness_tier}")


ResolveSource = Callable[[Mapping[str, Any], ResolutionContext], ActionResolution]
ResolveCandidate = Callable[[Mapping[str, Any], Mapping[str, Mapping[str, Any]], ResolutionContext], ActionResolution]


def default_resolve_source(record: Mapping[str, Any], context: ResolutionContext) -> ActionResolution:
    """Conservative default: no acquisition capability exists at this phase.

    A source with a declared locator (doi or url) reaches the one tier this
    phase can honestly support without acquisition — `locator_only` — no
    immutable rendition binding is attempted or claimed. A source with no
    locator at all cannot even reach that floor and quarantines
    `invalid_locator` (PRD §6.6: producers are instructed to leave locator
    fields null rather than invent one; a null locator is legal packet
    content, but it is the resolver's concern, not a schema violation).
    """

    locator_raw = record.get("locator")
    locator: Mapping[str, Any] = locator_raw if isinstance(locator_raw, Mapping) else {}
    if locator.get("doi") or locator.get("url"):
        return ActionResolution("completed", "locator_only", None)
    return ActionResolution("quarantined", None, "invalid_locator")


def default_resolve_candidate(
    record: Mapping[str, Any],
    sources_by_id: Mapping[str, Mapping[str, Any]],
    context: ResolutionContext,
) -> ActionResolution:
    """Conservative default: exact-passage resolution is Phase 4's job.

    A candidate with no declared source_refs cannot even state a basis and
    quarantines `basis_incomplete`. A candidate whose every source_ref is
    unresolvable within this packet quarantines `citation_unresolved` for
    the same reason. A structurally complete candidate still quarantines
    `citation_unresolved` here — this phase never performs exact-passage
    binding (contract §2.4 step 7 is `AssertionRegistry.find_exact_passages`,
    owned by Phase 4), so it never advances a candidate past `candidate`-tier
    on its own authority.
    """

    refs = record.get("source_refs") if isinstance(record.get("source_refs"), list) else []
    if not refs:
        return ActionResolution("quarantined", None, "basis_incomplete")
    if not any(ref in sources_by_id for ref in refs):
        return ActionResolution("quarantined", None, "citation_unresolved")
    return ActionResolution("quarantined", None, "citation_unresolved")


# ---------------------------------------------------------------------------
# Identity: receipt_digest / policy_digest (contract §1.3)
# ---------------------------------------------------------------------------


def compute_policy_digest(policy: Mapping[str, Any]) -> str:
    """sha256-canonical-json-v1 digest of the effective acquisition policy."""

    return _canonical_digest(dict(policy))


# Explicit ERI permission vocabulary (round-2 audit finding #2 closure).
#
# Prior to this pass, `authorize_caller` conflated bare workspace MEMBERSHIP
# with permission to operate: any role — including `viewer`, which
# `api/auth/rbac.py`'s own capability matrix grants zero permissions — could
# stage or replay a packet. This module cannot import `api/auth/rbac.py`
# directly (that module is HTTP-router-layer; this is a governed service
# module several layers below it), so it defines its own explicit two-
# permission matrix here, keyed by the SAME canonical role names
# `services/rbac_store.py` owns, mirroring `api/auth/rbac.ROLE_PERMISSIONS`'s
# shape (owner/admin/researcher hold the mutating permission,
# reviewer/viewer do not) without duplicating that module's routes or
# depending on it.
ERI_SUBMIT_PERMISSION = "external_research:submit"
ERI_READ_PERMISSION = "external_research:read"

_ERI_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset({ERI_SUBMIT_PERMISSION, ERI_READ_PERMISSION}),
    "admin": frozenset({ERI_SUBMIT_PERMISSION, ERI_READ_PERMISSION}),
    "researcher": frozenset({ERI_SUBMIT_PERMISSION, ERI_READ_PERMISSION}),
    "reviewer": frozenset({ERI_READ_PERMISSION}),
    "viewer": frozenset(),
}


def _eri_role_grants(role: str | None, permission: str) -> bool:
    if role is None:
        return False
    return permission in _ERI_ROLE_PERMISSIONS.get(role, frozenset())


# `governance_policy_digest` (contract §1.3, audit finding #9 — PARTIAL
# closure; see `authorize_caller`/`CallerContext` below for the other half;
# round-2 audit finding #1 closes the remaining gap noted below).
#
# This is a canonical digest over "the effective rights/sensitivity/
# workspace-authorization governance ruleset in force at Step 0 of §2.4".
# Earlier phases shipped a fixed digest over an explicitly-labeled
# "not_implemented" placeholder object, honest about representing nothing,
# then a digest over only `RBAC_SCHEMA_VERSION` + role NAMES — round-2 audit
# finding #1 found that still insufficient: it omitted the actual PERMISSION
# MAPPING (so a permission-matrix change without a schema-version bump would
# silently replay under the OLD mapping) and omitted the per-import rights/
# sensitivity `AuthorizationPolicy` entirely (so importing once under a
# permissive rights policy and retrying under a denying one replayed the
# permissive outcome). Both are folded in now: `eri_role_permissions` (the
# actual effective mapping, not just role names) and `authorization_policy`
# (the caller-supplied per-import rights/sensitivity policy, canonicalized by
# the caller — `external_research_import.py` is the caller that knows how to
# turn a resolution-layer `AuthorizationPolicy` into a plain, hashable
# mapping; this module accepts whatever mapping it is given without
# depending on that dataclass).
#
# What this digest does NOT do, by contract design (§1.3 vs §1.6 are two
# separate mechanisms): it does not vary per calling principal. Contract
# §1.3 is about the RULESET's identity, not any one caller's identity — a
# revoked caller replaying the same packet under the same still-current
# ruleset is closed by `authorize_caller`'s live reauthorization gate
# (§1.6), not by making this digest caller-specific. Folding a principal id
# in here would also break true replay (§1.5 case 1) for every OTHER
# still-authorized caller of the same packet/workspace/target.
def compute_governance_policy_digest(
    *, authorization_policy: Mapping[str, Any] | None = None
) -> str:
    """Real `governance_policy_digest` over RF's current RBAC ruleset PLUS
    the effective per-import rights/sensitivity policy (contract §1.3,
    audit finding #1).

    Deterministic given its inputs — mirrors `policy_digest`'s own "config
    snapshot, not request-specific" shape for the RBAC-ruleset portion
    (reads only the durable, versioned constants `rbac_store` already owns
    plus this module's own explicit permission matrix), and additionally
    folds in whatever `authorization_policy` mapping the caller supplies (a
    caller that omits it gets a stable digest over `None`, identical to
    every other omitting caller — never a silent divergence). Requires no
    I/O and no `FoundryPaths`.
    """

    from . import rbac_store  # local import: avoid a module-load-time cycle

    ruleset = {
        "governance_gate": "eri_step0_v1",
        "rbac_schema_version": rbac_store.RBAC_SCHEMA_VERSION,
        "canonical_roles": sorted(name for name, _ in rbac_store._CANONICAL_ROLES),
        "eri_role_permissions": {
            role: sorted(perms) for role, perms in sorted(_ERI_ROLE_PERMISSIONS.items())
        },
        "authorization_policy": dict(authorization_policy) if authorization_policy is not None else None,
    }
    return _canonical_digest(ruleset)


@dataclass(frozen=True)
class CallerContext:
    """Optional caller identity for contract §1.6's reauthorization gate.

    ``principal_id`` + ``principal_type`` name an RBAC principal (a user or
    a service account, `services/rbac_store.py`) whose CURRENT membership
    role in ``workspace_id`` is freshly re-checked (never cached) by
    :func:`authorize_caller` before any receipt existence lookup, return, or
    structural validation. ``token_id`` — present when the caller
    authenticated via an issued access token — additionally re-checks that
    SPECIFIC token's live revocation/expiry state: audit finding #9's
    "revoked caller" scenario is precisely a token that existed and was
    valid when a receipt was first published, but has since been revoked or
    expired.

    ``caller=None`` (the default, and the ONLY value the bare
    ``rf intake external-report`` CLI passes today) means
    single-operator-trust — the SAME, already-reviewed posture every other
    RF CLI mutation entry point uses (`api/auth/rbac.py`'s own module
    docstring: "CLI entry points bypass the HTTP router layer ... these
    surfaces are classified as single-operator-trust ... no RBAC
    enforcement needed today"). Supplying a `CallerContext` is how a FUTURE
    HTTP/MCP-mediated caller (the Operator-MCP seam `import_external_report`
    is already shaped for, per its own docstring) opts into real, live
    per-principal reauthorization; nothing about today's bare-CLI behavior
    changes when `caller` is omitted.
    """

    principal_id: str
    workspace_id: str
    principal_type: str = "user_pat"  # "user_pat" | "service" (rbac_store's own vocabulary)
    token_id: str | None = None


def authorize_caller(
    caller: CallerContext | None,
    *,
    workspace_id: str,
    paths: FoundryPaths | None = None,
    permission: str = ERI_SUBMIT_PERMISSION,
) -> None:
    """Contract §2.4 Step 0 (coarse caller/workspace authorization) AND
    §1.6 (re-run before every receipt existence lookup or return — not only
    before content return). Raises :class:`CallerNotAuthorizedError` — a
    non-receipt denial — on failure; returns ``None`` (silently) on success.

    ``caller=None`` always succeeds immediately (single-operator-trust,
    see :class:`CallerContext`'s docstring) — this is the ONLY path the
    bare CLI exercises today, and its behavior is unchanged from before
    this function existed.

    When a `CallerContext` is supplied, this performs a FRESH (never
    cached) lookup against `services/rbac_store.py` on every call, and
    (round-2 audit finding #2 closure) checks EXPLICIT ERI permission, not
    bare membership:

    - **Membership is not permission.** A caller's CURRENT role must grant
      `permission` per :data:`_ERI_ROLE_PERMISSIONS` — a `viewer` (zero
      permissions, matching `api/auth/rbac.ROLE_PERMISSIONS`'s own matrix)
      or `reviewer` (read-only) attempting `ERI_SUBMIT_PERMISSION` is denied
      even though they ARE a current member of the workspace.
    - **Token role is a ceiling, not a grant.** When `caller.token_id` is
      set, the token's OWN `role` column (`rbac_store.access_tokens.role` —
      the ceiling a token was issued at, independent of the issuing
      principal's current membership role) must ALSO grant `permission`.
      A still-valid token issued at a lower role than the principal's
      current membership can never exercise a permission the token itself
      was never granted.
    - **Service principals are authorized through their own record**, never
      through the `memberships` table — `caller.principal_type == "service"`
      resolves via `rbac_store.get_service_account` (workspace-scoped,
      independently disable-able), not `get_member_role` (which only ever
      answers "does this USER id have a membership row", a question that is
      meaningless for a service-account id and would previously silently
      return `None` → deny, or — worse, if a service account id happened to
      collide with an unrelated user id — silently authorize under the
      WRONG principal's membership).

    Uses only the existing RBAC store primitives (`get_member_role`,
    `get_service_account`, `get_access_token`); introduces no second
    authorization store or caller-identity concept.
    """

    if caller is None:
        return
    if caller.workspace_id != workspace_id:
        raise CallerNotAuthorizedError("caller is not authorized for this workspace")
    if permission not in (ERI_SUBMIT_PERMISSION, ERI_READ_PERMISSION):
        raise ValueError(f"unknown ERI permission: {permission!r}")

    from . import rbac_store  # local import: avoid a module-load-time cycle

    p = paths or FoundryPaths.discover()
    conn = rbac_store._connect(p)
    try:
        rbac_store._ensure_schema(conn)

        if caller.principal_type == "service":
            account = rbac_store.get_service_account(conn, caller.principal_id)
            if (
                account is None
                or account.get("workspace_id") != workspace_id
                or account.get("disabled_at") is not None
            ):
                raise CallerNotAuthorizedError(
                    "service principal has no current active record in this workspace"
                )
            principal_role: str | None = account.get("role")
        elif caller.principal_type == "user_pat":
            principal_role = rbac_store.get_member_role(conn, caller.principal_id, workspace_id)
            if principal_role is None:
                raise CallerNotAuthorizedError("caller has no current membership in this workspace")
        else:
            raise CallerNotAuthorizedError(f"unknown caller principal_type: {caller.principal_type!r}")

        if not _eri_role_grants(principal_role, permission):
            raise CallerNotAuthorizedError("caller's current role does not grant this ERI operation")

        if caller.token_id is not None:
            token = rbac_store.get_access_token(conn, caller.token_id)
            if (
                token is None
                or token["revoked_at"] is not None
                or token["principal_id"] != caller.principal_id
                or token["workspace_id"] != workspace_id
                or (token.get("expires_at") and token["expires_at"] <= now_iso())
            ):
                raise CallerNotAuthorizedError("caller's access token is not currently valid")
            if not _eri_role_grants(token.get("role"), permission):
                raise CallerNotAuthorizedError(
                    "caller's access token role ceiling does not grant this ERI operation"
                )
    finally:
        conn.close()


def compute_receipt_digest_accepted(
    *,
    packet_digest: str,
    workspace_id: str,
    target_run_id: str | None,
    policy_digest: str,
    schema_major_versions: Mapping[str, int],
    action_manifest_digest: str,
    governance_policy_digest: str,
) -> str:
    """receipt_digest, Branch A (contract §1.3): `status` is `completed` or
    `completed_with_quarantine`. SHA-256 over the seven-input sorted-key
    object (packet_digest, workspace_id, target_run_id-or-null,
    policy_digest, schema_major_versions, action_manifest_digest,
    governance_policy_digest).
    """

    obj = {
        "packet_digest": packet_digest,
        "workspace_id": workspace_id,
        "target_run_id": target_run_id,
        "policy_digest": policy_digest,
        "schema_major_versions": dict(schema_major_versions),
        "action_manifest_digest": action_manifest_digest,
        "governance_policy_digest": governance_policy_digest,
    }
    return _canonical_digest(obj)


def compute_receipt_digest_blocked(
    *,
    workspace_id: str,
    target_run_id: str | None,
    policy_digest: str,
    schema_major_versions: Mapping[str, int],
    governance_policy_digest: str,
    block_reason: str,
    attempt_structural_summary: Mapping[str, int],
) -> str:
    """receipt_digest, Branch B (contract §1.3): `status` is `blocked`.

    `packet_digest` and `action_manifest_digest` are never inputs on this
    branch — no accepted-member manifest exists yet to hash (audit finding
    #10) — replaced by `attempt_structural_summary`'s safely captured
    request metadata.
    """

    obj = {
        "blocked": True,
        "workspace_id": workspace_id,
        "target_run_id": target_run_id,
        "policy_digest": policy_digest,
        "schema_major_versions": dict(schema_major_versions),
        "governance_policy_digest": governance_policy_digest,
        "block_reason": block_reason,
        "attempt_structural_summary": dict(attempt_structural_summary),
    }
    return _canonical_digest(obj)


# ---------------------------------------------------------------------------
# Action manifest (deterministic, packet-scoped)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActionInput:
    action_id: str
    kind: str  # "source" | "candidate"
    record: Mapping[str, Any]
    member_path: str
    record_digest: str


def _record_digest(record: Mapping[str, Any]) -> str:
    """`record_digest` (contract §1.3a): SHA-256 over the record's own
    validated field set, exactly as accepted (post safe-parse, §4.1b — no
    implicit type coercion is possible under that profile, so this is
    literally the parsed value).
    """

    return _canonical_digest(dict(record))


def _build_action_inputs(inspection: PacketInspection) -> list[ActionInput]:
    """Deterministic ordered action set + frozen `action_id` (contract
    §1.3a, audit finding #6).

    Canonical iteration order: every declared source/candidate record,
    sorted by the declaring member's `member_path` (`sources.yaml` before
    `assertion_candidates.yaml`, per the contract's own worked example),
    then by that record's position within its declared array *as accepted
    by structural validation*.

    `action_id` = `era_` + SHA-256 hex over `{packet_digest, kind,
    member_path, record_digest, occurrence_index}`, where
    `occurrence_index` is the 0-based count of prior records (in canonical
    order, within the same `member_path`) sharing the same
    `record_digest` — binds identity to content, not array position, and
    disambiguates exact byte-identical duplicate records deterministically.
    """

    sources_path = next(
        (m.path for m in inspection.declared_members if m.role == "sources"),
        "sources.yaml",
    )
    candidates_path = next(
        (m.path for m in inspection.declared_members if m.role == "assertion_candidates"),
        "assertion_candidates.yaml",
    )

    ordered: list[tuple[str, str, Mapping[str, Any]]] = [
        (sources_path, "source", r)
        for r in inspection.source_records
        if isinstance(r, Mapping) and isinstance(r.get("source_id"), str)
    ]
    ordered += [
        (candidates_path, "candidate", r)
        for r in inspection.candidate_records
        if isinstance(r, Mapping) and isinstance(r.get("candidate_id"), str)
    ]

    occurrence_counts: dict[tuple[str, str], int] = {}
    actions: list[ActionInput] = []
    for member_path, kind, record in ordered:
        digest = _record_digest(record)
        key = (member_path, digest)
        occurrence_index = occurrence_counts.get(key, 0)
        occurrence_counts[key] = occurrence_index + 1
        action_id = "era_" + _canonical_digest(
            {
                "packet_digest": inspection.packet_digest,
                "kind": kind,
                "member_path": member_path,
                "record_digest": digest,
                "occurrence_index": occurrence_index,
            }
        )
        actions.append(
            ActionInput(action_id=action_id, kind=kind, record=record, member_path=member_path, record_digest=digest)
        )
    return actions


def _action_manifest_and_digest(actions: Sequence[ActionInput]) -> tuple[dict[str, Any], str]:
    """Canonical action manifest + `action_manifest_digest` (contract
    §1.3a): `{"algorithm_version": "1", "actions": [{"action_id", "kind",
    "member_path", "record_digest"}, ...]}`, inner array sorted ascending
    by `action_id` (byte-wise on the hex string). Embedding
    `algorithm_version` inside the hashed object is what closes "a future
    importer/normalization change silently alters the manifest under the
    same receipt identity" — a version bump changes `action_manifest_digest`,
    which changes `receipt_digest` (Branch A).
    """

    entries = sorted(
        (
            {
                "action_id": a.action_id,
                "kind": a.kind,
                "member_path": a.member_path,
                "record_digest": a.record_digest,
            }
            for a in actions
        ),
        key=lambda e: e["action_id"],
    )
    manifest = {"algorithm_version": "1", "actions": entries}
    return manifest, _canonical_digest(manifest)


def _effect_filename(kind: str, action_id: str) -> str:
    # `action_id` is already an opaque `era_<hex64>` digest (contract
    # §1.3a) — filesystem-safe and non-reversible on its own — so it is
    # used directly rather than hashed a second time.
    return f"{kind}__{action_id}.yaml"


# ---------------------------------------------------------------------------
# Stage result DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageResult:
    receipt: dict[str, Any]
    replayed: bool
    dry_run: bool
    checkpoint: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# ExternalResearchInterchange service
# ---------------------------------------------------------------------------


class ExternalResearchInterchange:
    """Workspace-isolated staging/receipt authority for ERI packet imports."""

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        # Never put the tenant-supplied workspace_id string into a path.
        self.workspace_key = _digest(workspace_id)
        self.root = self.paths.root / "external_research_interchange" / "workspaces" / self.workspace_key

    # --- path helpers -------------------------------------------------

    def _packet_dir(self, packet_digest: str) -> Path:
        return self.root / "packets" / packet_digest

    def _manifest_path(self, packet_digest: str) -> Path:
        return self._packet_dir(packet_digest) / "manifest.yaml"

    def _report_path(self, packet_digest: str, report_sha256: str) -> Path:
        return self._packet_dir(packet_digest) / "report" / f"{report_sha256}.bin"

    def _receipt_dir(self, receipt_digest: str) -> Path:
        return self.root / "receipts" / receipt_digest

    def _receipt_path(self, receipt_digest: str) -> Path:
        return self._receipt_dir(receipt_digest) / "receipt.yaml"

    def _checkpoint_path(self, receipt_digest: str) -> Path:
        return self._receipt_dir(receipt_digest) / "checkpoint.yaml"

    def _effect_path(self, receipt_digest: str, kind: str, action_id: str) -> Path:
        return self._receipt_dir(receipt_digest) / "effects" / _effect_filename(kind, action_id)

    def _lease_path(self, receipt_digest: str) -> Path:
        return self._receipt_dir(receipt_digest) / ".lease"

    # --- single-writer receipt-identity lease (contract audit finding #8,
    #     fencing hardened round-2 audit finding #4) -----------------------

    @contextmanager
    def _maybe_receipt_lease(self, receipt_digest: str, *, held: bool) -> Iterator[None]:
        """``_receipt_lease`` unless the caller already holds it.

        ``import_external_report`` holds this SAME lease across its own
        pending-checkpoint guard and the ``stage()`` call together
        (round-2 audit finding #9) — a nested unconditional
        ``_receipt_lease`` acquisition from within that already-locked
        section would deadlock against itself. ``held=True`` skips
        acquisition entirely and just yields.
        """

        if held:
            yield
            return
        with self._receipt_lease(receipt_digest):
            yield

    @contextmanager
    def _receipt_lease(self, receipt_digest: str) -> Iterator[None]:
        """Serialize the acquisition/effect phase for one ``receipt_digest``.

        Two concurrent callers can otherwise both observe "no terminal
        receipt exists yet" (the ``_load_receipt`` check below), both run
        resolvers and write effects, and race the terminal receipt publish —
        producing duplicate canonical effects or divergent receipts for the
        same identity. Atomic per-file publication (``_write_immutable_*``)
        does not by itself serialize that acquisition/effect *phase*.

        This reserves a single-writer lease via an atomic ``O_CREAT|O_EXCL``
        lock file keyed by ``receipt_digest`` before any effect or receipt
        write is attempted. A losing caller polls (bounded) until the lease
        is released, then proceeds — at which point it will see the
        winner's now-published receipt via the normal replay path instead of
        re-running acquisition. A lease abandoned by a crashed/killed writer
        is reclaimed once it exceeds ``_LEASE_STALE_SECONDS``.

        **Fencing (round-2 audit finding #4).** The lease file's content is
        ``"<owner_token>:<generation>:<pid>:<acquired_at>\\n"`` — an opaque
        per-acquisition ``owner_token`` (uuid4) and a monotonically
        increasing ``generation`` (bumped by one every time the lease
        changes hands, whether via a fresh acquire or a stale reclaim).
        Release verifies this process's own acquisition is STILL the file at
        ``lease_path`` by comparing ``(st_dev, st_ino)`` captured at
        acquisition time against a fresh ``stat`` immediately before
        unlinking — a lease this process lost to a stale-reclaim (see
        ``_reclaim_stale_lease``) is never unlinked out from under its new,
        legitimate owner. ``_execute`` heartbeats (touches) this same lease
        file after every per-action effect publish so a legitimately
        long-running import's lease never looks abandoned; a heartbeat that
        discovers the lease is no longer its own (lost to a reclaim despite
        the loop above) raises :class:`StagingIntegrityError` rather than
        silently continuing to write under a lease it no longer holds.
        """

        lease_path = self._lease_path(receipt_digest)
        lease_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + _LEASE_MAX_WAIT_SECONDS
        owner_token = f"{os.getpid()}-{now_iso()}-{id(object())}"
        generation = 0
        acquired = False
        acquired_stat: os.stat_result | None = None
        while not acquired:
            try:
                fd = os.open(lease_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                try:
                    os.write(fd, f"{owner_token}:{generation}:{os.getpid()}:{now_iso()}\n".encode())
                    os.fsync(fd)
                    acquired_stat = os.fstat(fd)
                finally:
                    os.close(fd)
                acquired = True
            except FileExistsError:
                reclaimed_generation = self._reclaim_stale_lease(lease_path)
                if reclaimed_generation is not None:
                    generation = reclaimed_generation + 1
                    continue
                if time.monotonic() >= deadline:
                    raise InterchangeError(
                        f"timed out waiting for the receipt-identity lease: {receipt_digest}"
                    ) from None
                time.sleep(_LEASE_POLL_INTERVAL_SECONDS)
        assert acquired_stat is not None
        try:
            yield
        finally:
            with suppress(FileNotFoundError):
                current = os.stat(lease_path)
                if (current.st_dev, current.st_ino) == (acquired_stat.st_dev, acquired_stat.st_ino):
                    lease_path.unlink()
                # else: this lease was reclaimed out from under us (we
                # failed to heartbeat in time); the file now belongs to a
                # new legitimate owner -- never unlink someone else's lease.

    @staticmethod
    def _reclaim_stale_lease(lease_path: Path) -> int | None:
        """Reclaim an abandoned lease. Returns the reclaimed lease's own
        ``generation`` (so the new owner can bump it) on success, or
        ``None`` if the lease is missing, still fresh, or was replaced
        between this call's read and its unlink attempt.

        Hardened (round-2 audit finding #4): the prior implementation was
        ``stat()`` (for age) followed by an UNCONDITIONAL ``unlink()`` --
        neither the owner token nor the inode was re-checked immediately
        before deleting, so (a) two concurrent reclaimers could both
        "succeed" against the same stale lease and both believe they alone
        won it, and (b) a legitimate writer whose single long-held lease
        merely exceeded the staleness window (no heartbeat existed at all
        previously) would have its live lease deleted by a bystander. This
        now opens the file directly (capturing its inode via ``fstat``,
        not a separate ``stat`` call that could race a replacement),
        checks the age from that SAME open file description, and — only if
        stale — re-``stat``s the path immediately before unlinking and
        requires the inode to still match what was just read. A mismatch at
        any point means someone else already replaced/renewed the lease
        since this reclaim attempt began, and this call backs off (returns
        ``None``) rather than deleting whatever is there now.
        """

        try:
            fd = os.open(lease_path, os.O_RDONLY)
        except FileNotFoundError:
            return None
        try:
            pre_stat = os.fstat(fd)
            age_seconds = time.time() - pre_stat.st_mtime
            if age_seconds <= _LEASE_STALE_SECONDS:
                return None
            with os.fdopen(fd, "r", closefd=False) as handle:
                content = handle.read()
        finally:
            os.close(fd)

        try:
            post_stat = os.stat(lease_path)
        except FileNotFoundError:
            return None
        if (post_stat.st_dev, post_stat.st_ino) != (pre_stat.st_dev, pre_stat.st_ino):
            return None
        if post_stat.st_mtime != pre_stat.st_mtime:
            # A heartbeat landed between our read and this check -- no
            # longer stale; do not reclaim.
            return None

        prior_generation = 0
        with suppress(Exception):
            # Best-effort: legacy/foreign lease content (e.g. a lease file
            # from before this fencing scheme existed, or hand-authored test
            # fixtures) never crashes reclaim -- it just starts the
            # generation counter at 0 for the new owner.
            prior_generation = int(content.strip().split(":")[1])

        # Claim via `os.rename` to a unique, per-attempt scratch name rather
        # than a plain `os.unlink` (round-2 audit finding #4, hardened
        # further after direct empirical testing on this tree's filesystem):
        # a bare `os.unlink` raced by several concurrent callers against the
        # SAME path was directly observed to occasionally report success
        # ("no exception") to MORE than one caller on this filesystem under
        # heavy thread-level concurrency -- i.e. `unlink`'s "exactly one
        # caller ever sees success" guarantee is not reliable here. A
        # `rename` to a destination name that is unique to THIS call is:
        # the source path can only ever be consumed by one renamer (proven
        # by direct repeated concurrent-rename testing showing zero
        # mismatches), so only one caller's rename can ever succeed, and
        # that caller alone proceeds to remove its own now-privately-owned
        # scratch copy.
        claim_path = lease_path.parent / f".{lease_path.name}.reclaimed-{os.getpid()}-{uuid.uuid4().hex}"
        try:
            os.rename(lease_path, claim_path)
        except FileNotFoundError:
            return None
        with suppress(FileNotFoundError):
            claim_path.unlink()
        return prior_generation

    def _heartbeat_lease(self, lease_path: Path, acquired_stat: os.stat_result) -> None:
        """Renew a held lease's liveness signal (round-2 audit finding #4).

        Called by ``_execute`` after every per-action effect publish so a
        legitimately long-running import (one whose total acquisition time
        exceeds ``_LEASE_STALE_SECONDS``) is never mistaken for an abandoned
        one. Verifies the lease at ``lease_path`` is STILL the exact file
        this process acquired (same ``(st_dev, st_ino)``) before touching
        it; if it is not, this process's lease was already reclaimed
        (fencing lost) and continuing to write would risk a concurrent
        writer -- raises :class:`StagingIntegrityError` rather than
        silently proceeding.
        """

        try:
            current = os.stat(lease_path)
        except FileNotFoundError as exc:
            raise StagingIntegrityError(
                "receipt-identity lease was lost mid-import (lease file missing)"
            ) from exc
        if (current.st_dev, current.st_ino) != (acquired_stat.st_dev, acquired_stat.st_ino):
            raise StagingIntegrityError(
                "receipt-identity lease was lost mid-import (lease file was replaced)"
            )
        os.utime(lease_path, None)

    # --- public API -----------------------------------------------------

    def stage(
        self,
        packet_dir: str | Path,
        *,
        target_run_id: str | None = None,
        policy: Mapping[str, Any],
        authorization_policy: Mapping[str, Any] | None = None,
        resolve_source: ResolveSource = default_resolve_source,
        resolve_candidate: ResolveCandidate = default_resolve_candidate,
        limits: Limits | None = None,
        dry_run: bool = False,
        caller: CallerContext | None = None,
        inspection: PacketInspection | None = None,
        _interrupt_after_action_index: int | None = None,
        _interrupt_before_receipt_publish: bool = False,
        _lease_already_held: bool = False,
    ) -> StageResult:
        """Stage a packet and produce its terminal receipt.

        ``target_run_id=None`` is staging-only (contract §1.4): no run is
        created, no run-local projection is written, and `verified` is
        categorically unreachable — enforced defensively below regardless of
        what a caller-supplied resolver returns.

        ``authorization_policy`` (contract §1.3, audit finding #1): an
        optional plain mapping representing the effective per-import rights/
        sensitivity policy in force, folded into `governance_policy_digest`
        (and therefore `receipt_digest`) so a policy change is a genuinely
        distinct identity, never a silent replay of an earlier, differently-
        governed decision. Omitted by direct callers that have no such
        policy to report (digest over `None`, stable across calls that all
        omit it).

        ``caller`` (contract §1.6 / audit finding #9): re-authorized, live,
        before anything else in this method runs — including before the
        replay-lookup (`_load_receipt`) below, satisfying "before existence
        lookup, not only before content return" — AND re-checked again
        immediately before that same lookup once inside the single-writer
        lease (round-2 audit finding #3): the first check can be arbitrarily
        stale by the time a caller has waited out lease contention.
        ``caller=None`` (the only value the bare CLI passes) is single-
        operator-trust and behaves exactly as before this parameter existed;
        see :func:`authorize_caller`.

        ``inspection`` (round-2 audit finding #6): an optional pre-computed
        :class:`PacketInspection`. When supplied (as
        ``external_research_import.import_external_report`` now does), this
        method performs NO second `inspect_packet` call of its own — closing
        the TOCTOU window where the orchestrator's own inspection and this
        method's independent re-inspection could observe two different
        snapshots of a mutable packet directory. ``packet_dir`` is still
        accepted (kept for direct callers with no pre-existing inspection)
        but is ignored once ``inspection`` is provided.

        ``_lease_already_held`` (round-2 audit finding #9): internal —
        ``import_external_report`` holds the SAME receipt-identity lease for
        its own pending-checkpoint guard and this call together, atomically;
        when set, this method skips its own lease acquisition (which would
        otherwise deadlock against the caller's already-held lock) and
        proceeds directly under the assumption the lock is already held.
        """

        authorize_caller(caller, workspace_id=self.workspace_id, paths=self.paths)

        policy_validation = schema_validate(dict(policy), "external_research_acquisition_policy")
        if not policy_validation.ok:
            raise ValueError(f"invalid acquisition policy: {policy_validation.errors}")
        policy_digest = compute_policy_digest(policy)
        # Step 0 of contract §2.4 always runs, on every attempt, regardless
        # of what structural validation subsequently finds (audit finding
        # #9). `governance_policy_digest` now folds in the effective ERI
        # permission mapping AND the caller-supplied `authorization_policy`
        # (round-2 audit finding #1) — see `compute_governance_policy_digest`.
        governance_policy_digest = compute_governance_policy_digest(authorization_policy=authorization_policy)

        if inspection is None:
            inspection = inspect_packet(packet_dir, limits=limits)

        if not inspection.ok:
            assert inspection.attempt_structural_summary is not None
            assert inspection.reason_code is not None
            receipt_digest = compute_receipt_digest_blocked(
                workspace_id=self.workspace_id,
                target_run_id=target_run_id,
                policy_digest=policy_digest,
                schema_major_versions=inspection.schema_major_versions,
                governance_policy_digest=governance_policy_digest,
                block_reason=inspection.reason_code,
                attempt_structural_summary=inspection.attempt_structural_summary,
            )
            receipt_id = f"erh_{receipt_digest}"
            receipt = self._build_blocked_receipt(
                inspection=inspection,
                receipt_id=receipt_id,
                receipt_digest=receipt_digest,
                target_run_id=target_run_id,
                policy_digest=policy_digest,
                governance_policy_digest=governance_policy_digest,
            )
            if dry_run:
                return StageResult(receipt=receipt, replayed=False, dry_run=True, checkpoint=None)
            with self._maybe_receipt_lease(receipt_digest, held=_lease_already_held):
                # Reauthorize immediately before the receipt existence lookup
                # (round-2 audit finding #3): the Step-0 check above may be
                # stale by the time lease contention resolves.
                authorize_caller(caller, workspace_id=self.workspace_id, paths=self.paths)
                return self._publish_or_replay_blocked(receipt, receipt_digest)

        actions = _build_action_inputs(inspection)
        action_manifest, action_manifest_digest = _action_manifest_and_digest(actions)
        receipt_digest = compute_receipt_digest_accepted(
            packet_digest=inspection.packet_digest,
            workspace_id=self.workspace_id,
            target_run_id=target_run_id,
            policy_digest=policy_digest,
            schema_major_versions=inspection.schema_major_versions,
            action_manifest_digest=action_manifest_digest,
            governance_policy_digest=governance_policy_digest,
        )
        receipt_id = f"erh_{receipt_digest}"
        context = ResolutionContext(workspace_id=self.workspace_id, target_run_id=target_run_id, policy=policy)
        sources_by_id = {
            r["source_id"]: r for r in inspection.source_records if isinstance(r.get("source_id"), str)
        }

        if dry_run:
            resolutions = [
                self._resolve_one(action, sources_by_id, context, resolve_source, resolve_candidate, target_run_id)
                for action in actions
            ]
            receipt = self._build_receipt_dict(
                inspection=inspection,
                actions=actions,
                resolutions=resolutions,
                effect_digests=[self._effect_digest(a, r) for a, r in zip(actions, resolutions, strict=True)],
                receipt_id=receipt_id,
                receipt_digest=receipt_digest,
                target_run_id=target_run_id,
                policy_digest=policy_digest,
                governance_policy_digest=governance_policy_digest,
                action_manifest_digest=action_manifest_digest,
            )
            return StageResult(receipt=receipt, replayed=False, dry_run=True, checkpoint=None)

        with self._maybe_receipt_lease(receipt_digest, held=_lease_already_held):
            # Reauthorize immediately before the receipt existence lookup
            # (round-2 audit finding #3): the Step-0 check above may be
            # stale by the time lease contention resolves — the caller
            # could have been revoked during that wait.
            authorize_caller(caller, workspace_id=self.workspace_id, paths=self.paths)

            # Re-check for a published receipt now that we hold the single
            # writer lease: another caller may have raced us to acquire it
            # and already published while we were waiting (contract audit
            # finding #8) — that caller's outcome is authoritative and we
            # must replay it, never re-run acquisition or re-derive effects.
            existing_receipt = self._load_receipt(receipt_digest)
            if existing_receipt is not None:
                self._verify_replay(existing_receipt, actions)
                checkpoint = self._load_checkpoint(receipt_digest)
                return StageResult(receipt=existing_receipt, replayed=True, dry_run=False, checkpoint=checkpoint)

            return self._execute(
                inspection=inspection,
                actions=actions,
                sources_by_id=sources_by_id,
                context=context,
                resolve_source=resolve_source,
                resolve_candidate=resolve_candidate,
                receipt_id=receipt_id,
                receipt_digest=receipt_digest,
                target_run_id=target_run_id,
                policy_digest=policy_digest,
                governance_policy_digest=governance_policy_digest,
                action_manifest_digest=action_manifest_digest,
                interrupt_after_action_index=_interrupt_after_action_index,
                interrupt_before_receipt_publish=_interrupt_before_receipt_publish,
            )

    # --- internals --------------------------------------------------------

    def _resolve_one(
        self,
        action: ActionInput,
        sources_by_id: Mapping[str, Mapping[str, Any]],
        context: ResolutionContext,
        resolve_source: ResolveSource,
        resolve_candidate: ResolveCandidate,
        target_run_id: str | None,
    ) -> ActionResolution:
        if action.kind == "source":
            resolution = resolve_source(action.record, context)
        else:
            resolution = resolve_candidate(action.record, sources_by_id, context)
        if target_run_id is None and resolution.completeness_tier == "verified":
            # Contract §1.4 hard consequence: `verified` is categorically
            # unreachable when target_run_id is null. A resolver that
            # violates this is an importer defect, not a valid outcome.
            raise InterchangeError(
                "resolver returned completeness_tier=verified for a staging-only (target_run_id=null) import"
            )
        return resolution

    def _effect_digest(self, action: ActionInput, resolution: ActionResolution) -> str:
        """`effect_digest` (contract §1.3a): SHA-256 over
        `{action_id, outcome, completeness_tier, canonical_refs}`.
        `canonical_refs` names the downstream canonical identifier(s) this
        action produced or reused (`resolution.canonical_refs`, populated by
        Phase 4's real resolver; empty for the conservative Phase 2 default
        resolvers, which never bind a real edition/passage/source-card).
        Hashing `action_id` first is what binds an effect to exactly one
        action; folding in the actual `canonical_refs` (Phase 5) is what
        makes two outcomes that reached the same tier via DIFFERENT bound
        editions/passages diverge in identity rather than collapsing to the
        same effect_digest.
        """

        return _canonical_digest(
            {
                "action_id": action.action_id,
                "outcome": resolution.outcome,
                "completeness_tier": resolution.completeness_tier,
                "canonical_refs": dict(resolution.canonical_refs),
            }
        )

    @staticmethod
    def _audit_ref(receipt_digest: str, action: ActionInput, resolution: ActionResolution) -> str | None:
        """Opaque `audit_ref` (contract §4.6, audit finding #15).

        Non-null exactly when `outcome` is `quarantined`; the caller-visible
        receipt never carries the actual reason code or a free-text detail
        — only this opaque pointer. The persisted effect record (this
        module's access-controlled audit store) retains the real
        `reason_code` internally; a privileged reader with `receipt_digest`
        and `action_id` can locate it directly, but `audit_ref` itself
        leaks neither the code nor its differential.
        """

        if resolution.outcome != "quarantined":
            return None
        return _canonical_digest(
            {
                "receipt_digest": receipt_digest,
                "action_id": action.action_id,
                "reason_code": resolution.reason_code,
            }
        )

    def _build_receipt_dict(
        self,
        *,
        inspection: PacketInspection,
        actions: Sequence[ActionInput],
        resolutions: Sequence[ActionResolution],
        effect_digests: Sequence[str],
        receipt_id: str,
        receipt_digest: str,
        target_run_id: str | None,
        policy_digest: str,
        governance_policy_digest: str,
        action_manifest_digest: str,
    ) -> dict[str, Any]:
        action_docs = []
        for action, resolution, effect_digest in zip(actions, resolutions, effect_digests, strict=True):
            action_docs.append(
                {
                    "action_id": action.action_id,
                    "kind": action.kind,
                    "outcome": resolution.outcome,
                    "completeness_tier": resolution.completeness_tier,
                    "audit_ref": self._audit_ref(receipt_digest, action, resolution),
                    "effect_digest": effect_digest,
                }
            )
        counts = self._counts(action_docs)
        status = "completed" if counts["quarantined"] == 0 else "completed_with_quarantine"
        receipt = {
            "schema_version": "1.0",
            "type": "external_research_import_receipt",
            "receipt_id": receipt_id,
            "receipt_digest": receipt_digest,
            "packet_digest": inspection.packet_digest,
            "workspace_id": self.workspace_id,
            "target_run_id": target_run_id,
            "policy_digest": policy_digest,
            "governance_policy_digest": governance_policy_digest,
            "schema_major_versions": dict(inspection.schema_major_versions),
            "action_manifest_digest": action_manifest_digest,
            "action_manifest_algorithm_version": "1",
            "attempt_structural_summary": None,
            "importer_contract_version": _IMPORTER_CONTRACT_VERSION,
            "status": status,
            "block_reason": None,
            "actions": action_docs,
            "counts": counts,
            "created_at": now_iso(),
        }
        validation = schema_validate(receipt, "external_research_import_receipt")
        if not validation.ok:
            raise InterchangeError(f"constructed receipt failed schema validation: {validation.errors}")
        return receipt

    def _build_blocked_receipt(
        self,
        *,
        inspection: PacketInspection,
        receipt_id: str,
        receipt_digest: str,
        target_run_id: str | None,
        policy_digest: str,
        governance_policy_digest: str,
    ) -> dict[str, Any]:
        receipt: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "external_research_import_receipt",
            "receipt_id": receipt_id,
            "receipt_digest": receipt_digest,
            "packet_digest": None,
            "workspace_id": self.workspace_id,
            "target_run_id": target_run_id,
            "policy_digest": policy_digest,
            "governance_policy_digest": governance_policy_digest,
            "schema_major_versions": dict(inspection.schema_major_versions),
            "action_manifest_digest": None,
            "action_manifest_algorithm_version": None,
            "attempt_structural_summary": inspection.attempt_structural_summary,
            "importer_contract_version": _IMPORTER_CONTRACT_VERSION,
            "status": "blocked",
            "block_reason": inspection.reason_code,
            "actions": [],
            "counts": {
                "actions_total": 0,
                "completed": 0,
                "quarantined": 0,
                "by_completeness_tier": {},
            },
            "created_at": now_iso(),
        }
        validation = schema_validate(receipt, "external_research_import_receipt")
        if not validation.ok:
            raise InterchangeError(f"constructed blocked receipt failed schema validation: {validation.errors}")
        return receipt

    @staticmethod
    def _counts(action_docs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        completed = sum(1 for a in action_docs if a["outcome"] == "completed")
        quarantined = sum(1 for a in action_docs if a["outcome"] == "quarantined")
        by_tier: Counter[str] = Counter(a["completeness_tier"] for a in action_docs if a["completeness_tier"])
        return {
            "actions_total": len(action_docs),
            "completed": completed,
            "quarantined": quarantined,
            "by_completeness_tier": dict(by_tier),
        }

    def _load_receipt(self, receipt_digest: str) -> dict[str, Any] | None:
        path = self._receipt_path(receipt_digest)
        if not path.exists():
            return None
        data = loads_yaml(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise StagingIntegrityError("persisted receipt is not a mapping")
        return dict(data)

    def _load_checkpoint(self, receipt_digest: str) -> dict[str, Any] | None:
        path = self._checkpoint_path(receipt_digest)
        if not path.exists():
            return None
        data = loads_yaml(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise StagingIntegrityError("persisted checkpoint is not a mapping")
        return dict(data)

    def _verify_replay(self, existing_receipt: Mapping[str, Any], actions: Sequence[ActionInput]) -> None:
        """True-conflict detection (contract §1.5 case 3).

        Two checks, both required (round-2 audit finding #5 strengthens the
        second): the stored receipt's action set (action_id, kind) must
        exactly match the deterministic action set re-derived from the
        presented inputs, AND the deterministic action manifest re-derived
        from those same actions must produce the IDENTICAL
        `action_manifest_digest` the stored receipt itself records — the
        exact "re-deriving the deterministic action manifest ... and
        comparing it against the stored value" check contract §1.3a names by
        description. The manifest-digest check alone would not have caught
        every prior tampering shape (e.g. renaming one action_id while
        leaving the top-level `action_manifest_digest` field untouched), so
        both checks are kept. Any mismatch means the persisted history does
        not correspond to what these identity inputs currently produce —
        fail closed, never merge or overwrite.
        """

        if existing_receipt.get("status") == "blocked":
            return
        validation = schema_validate(dict(existing_receipt), "external_research_import_receipt")
        if not validation.ok:
            raise ReplayConflictError(
                f"receipt_digest already has a persisted history that fails schema validation: {validation.errors}"
            )
        stored = {(a.get("action_id"), a.get("kind")) for a in existing_receipt.get("actions", [])}
        expected = {(a.action_id, a.kind) for a in actions}
        if stored != expected:
            raise ReplayConflictError(
                "receipt_digest already has a persisted history that does not match the presented packet"
            )
        _manifest, recomputed_action_manifest_digest = _action_manifest_and_digest(actions)
        if existing_receipt.get("action_manifest_digest") != recomputed_action_manifest_digest:
            raise ReplayConflictError(
                "receipt_digest already has a persisted history whose action manifest does not match "
                "the presented packet's re-derived action manifest"
            )

    def _publish_or_replay_blocked(self, receipt: Mapping[str, Any], receipt_digest: str) -> StageResult:
        existing = self._load_receipt(receipt_digest)
        if existing is not None:
            # `created_at` is the ONE legitimately time-varying field on a
            # blocked receipt -- a genuine, ordinary delayed retry of the
            # exact same blocked identity produces a freshly-built `receipt`
            # dict whose `created_at` differs from the stored one merely
            # because time passed (round-2 audit finding #9). Comparing the
            # full mapping including that field made every such retry look
            # like a tampering conflict; exclude it from the comparison
            # (never from what is RETURNED -- the stored receipt, with its
            # own original `created_at`, is what callers see either way).
            existing_comparable = {k: v for k, v in dict(existing).items() if k != "created_at"}
            fresh_comparable = {k: v for k, v in dict(receipt).items() if k != "created_at"}
            if existing_comparable != fresh_comparable:
                raise ReplayConflictError(
                    "receipt_digest already has a persisted blocked history that does not match"
                )
            return StageResult(receipt=existing, replayed=True, dry_run=False, checkpoint=None)
        _write_immutable_mapping(receipt, self._receipt_path(receipt_digest))
        return StageResult(receipt=dict(receipt), replayed=False, dry_run=False, checkpoint=None)

    def _stage_packet_artifacts(self, inspection: PacketInspection) -> None:
        """ERI-2.2: persist the immutable packet manifest + governed report bytes."""

        manifest = {
            "schema_version": "1.0",
            "type": "external_research_interchange_manifest",
            "packet_digest": inspection.packet_digest,
            "members": [m.as_dict() for m in inspection.declared_members],
            "schema_major_versions": dict(inspection.schema_major_versions),
        }
        _write_immutable_mapping(manifest, self._manifest_path(inspection.packet_digest))

        if inspection.report_member is not None:
            # report.md bytes stay a governed artifact: streamed verbatim,
            # content-addressed, never decoded/parsed, never passed to
            # source_cards.ingest_source() or AssertionRegistry.ingest()
            # (contract §4.1's report.md special case).
            #
            # These are the exact bytes already streamed and hash-verified
            # once, in memory, during ``inspect_packet`` — never re-opened
            # by path here (contract audit finding #7). A second by-path
            # open at this later point in time would reopen a TOCTOU window
            # in which the member's bytes could have changed underneath the
            # digest that ``packet_digest``/the receipt already committed to
            # (e.g. a write through an external hardlink, or through a
            # descriptor another process still holds open).
            assert inspection.report_bytes is not None
            _write_immutable_bytes(
                inspection.report_bytes, self._report_path(inspection.packet_digest, inspection.report_member.sha256)
            )

    def _execute(
        self,
        *,
        inspection: PacketInspection,
        actions: Sequence[ActionInput],
        sources_by_id: Mapping[str, Mapping[str, Any]],
        context: ResolutionContext,
        resolve_source: ResolveSource,
        resolve_candidate: ResolveCandidate,
        receipt_id: str,
        receipt_digest: str,
        target_run_id: str | None,
        policy_digest: str,
        governance_policy_digest: str,
        action_manifest_digest: str,
        interrupt_after_action_index: int | None,
        interrupt_before_receipt_publish: bool,
    ) -> StageResult:
        self._stage_packet_artifacts(inspection)

        checkpoint = self._load_checkpoint(receipt_digest)
        if checkpoint is not None and (
            checkpoint.get("packet_digest") != inspection.packet_digest
            or checkpoint.get("workspace_id") != self.workspace_id
            or checkpoint.get("target_run_id") != target_run_id
        ):
            raise StagingIntegrityError("persisted checkpoint does not bind the presented staging context")

        # Heartbeat baseline (round-2 audit finding #4): whoever holds the
        # receipt-identity lease by the time `_execute` runs (this method's
        # own `_receipt_lease`, or a caller — `import_external_report` —
        # holding it externally across a wider section) already has the
        # lease FILE on disk; reading its current stat here is a valid
        # baseline for this execution window regardless of which acquired
        # it, so `_execute` never needs a lease handle threaded through.
        lease_path = self._lease_path(receipt_digest)
        try:
            lease_stat: os.stat_result | None = os.stat(lease_path)
        except FileNotFoundError:
            lease_stat = None  # defensive only -- every real caller holds the lease here

        resolutions: list[ActionResolution] = []
        effect_digests: list[str] = []
        for index, action in enumerate(actions):
            effect_path = self._effect_path(receipt_digest, action.kind, action.action_id)
            prepare_path = effect_path.parent / f"{effect_path.name}.prepare"
            if effect_path.exists():
                # Resume: reuse the already-published immutable effect --
                # but never blindly. Round-2 audit finding #5: bind the
                # persisted record to THIS receipt_digest/action_id/kind and
                # recompute its effect_digest from its own trusted fields,
                # rather than trusting a persisted `effect_digest` string
                # that was never re-derived.
                existing_effect = loads_yaml(effect_path.read_text(encoding="utf-8"))
                if not isinstance(existing_effect, Mapping):
                    raise StagingIntegrityError("persisted effect record is not a mapping")
                for required_key in (
                    "receipt_digest",
                    "action_id",
                    "kind",
                    "outcome",
                    "completeness_tier",
                    "reason_code",
                    "effect_digest",
                ):
                    if required_key not in existing_effect:
                        raise StagingIntegrityError(
                            f"persisted effect record is missing required field: {required_key}"
                        )
                if (
                    existing_effect["receipt_digest"] != receipt_digest
                    or existing_effect["action_id"] != action.action_id
                    or existing_effect["kind"] != action.kind
                ):
                    raise StagingIntegrityError(
                        "persisted effect record does not bind the presented receipt_digest/action_id/kind"
                    )
                resolution = ActionResolution(
                    outcome=existing_effect["outcome"],
                    completeness_tier=existing_effect["completeness_tier"],
                    reason_code=existing_effect["reason_code"],
                    canonical_refs=dict(existing_effect.get("canonical_refs") or {}),
                )
                recomputed_effect_digest = self._effect_digest(action, resolution)
                if recomputed_effect_digest != existing_effect["effect_digest"]:
                    raise StagingIntegrityError(
                        "persisted effect record's effect_digest does not match its own recomputed "
                        "fields -- possible tampering or corruption"
                    )
                effect_digest = existing_effect["effect_digest"]
                # A committed effect makes any leftover prepare marker moot.
                with suppress(FileNotFoundError):
                    prepare_path.unlink()
            else:
                # Outbox prepare phase (round-2 audit finding #5, PARTIAL
                # closure -- see the note below for what remains open):
                # record intent DURABLY before invoking the resolver. This
                # module does not own the resolver's downstream mutation
                # logic (`external_research_resolution.py`'s
                # acquire/promote/registry-ingest calls) and therefore
                # cannot itself make that mutation idempotent by action_id
                # -- that guarantee has to come from the resolver substrate
                # (e.g. `AssertionRegistry.ingest()`'s content-addressed
                # dedup, which the contract already documents as the
                # existing idempotent authority for edition/passage
                # persistence). What this DOES add: a durable,
                # inspectable audit trail -- a `.prepare` marker left
                # behind with no matching effect is visible evidence, after
                # the fact, that an interrupted prior attempt reached the
                # resolver for this specific action, closing the "silently
                # indistinguishable from a clean first attempt" half of the
                # gap. Resume still safely re-invokes the resolver for this
                # action (matching `test_keyboard_interrupt_preserves_
                # pending_checkpoint_and_resume_completes`'s existing,
                # intentionally-tested crash-recovery contract) rather than
                # blocking on it, because blocking here would require this
                # module to independently second-guess the resolver
                # substrate's own idempotency guarantee, which is out of
                # this module's owned scope.
                _atomic_dump(
                    {
                        "schema_version": "1.0",
                        "type": "external_research_import_effect_intent",
                        "receipt_digest": receipt_digest,
                        "action_id": action.action_id,
                        "kind": action.kind,
                        "record_digest": action.record_digest,
                        "prepared_at": now_iso(),
                    },
                    prepare_path,
                )
                try:
                    resolution = self._resolve_one(
                        action, sources_by_id, context, resolve_source, resolve_candidate, target_run_id
                    )
                except ResolutionDeclined:
                    # The resolver was never actually invoked (e.g. a
                    # per-invocation batch limit reached) -- structurally
                    # guaranteed no downstream mutation was attempted for
                    # this action, so the outbox marker just written is not
                    # evidence of anything and would otherwise wrongly trip
                    # the fail-closed resume check above on the next call.
                    with suppress(FileNotFoundError):
                        prepare_path.unlink()
                    raise
                effect_digest = self._effect_digest(action, resolution)
                effect_record = {
                    "schema_version": "1.0",
                    "type": "external_research_import_effect",
                    "receipt_digest": receipt_digest,
                    "action_id": action.action_id,
                    "kind": action.kind,
                    "outcome": resolution.outcome,
                    "completeness_tier": resolution.completeness_tier,
                    "reason_code": resolution.reason_code,
                    "canonical_refs": dict(resolution.canonical_refs),
                    "effect_digest": effect_digest,
                    "created_at": now_iso(),
                }
                # Outbox commit phase: the effect is now durable. Clearing
                # the prepare marker is best-effort cleanup, not part of the
                # correctness argument -- resume already checks
                # `effect_path.exists()` first, so a leftover prepare file
                # beside a published effect is always harmless.
                _write_immutable_mapping(effect_record, effect_path)
                with suppress(FileNotFoundError):
                    prepare_path.unlink()
                self._write_checkpoint_pending(
                    receipt_id=receipt_id,
                    receipt_digest=receipt_digest,
                    packet_digest=inspection.packet_digest,
                    target_run_id=target_run_id,
                    actions=actions,
                    completed_through_index=index,
                    effect_digests_so_far=[*effect_digests, effect_digest],
                )
                if lease_stat is not None:
                    self._heartbeat_lease(lease_path, lease_stat)
                if interrupt_after_action_index is not None and index == interrupt_after_action_index:
                    raise RuntimeError("simulated staging interruption after action effect publish")
            resolutions.append(resolution)
            effect_digests.append(effect_digest)

        receipt = self._build_receipt_dict(
            inspection=inspection,
            actions=actions,
            resolutions=resolutions,
            effect_digests=effect_digests,
            receipt_id=receipt_id,
            receipt_digest=receipt_digest,
            target_run_id=target_run_id,
            policy_digest=policy_digest,
            governance_policy_digest=governance_policy_digest,
            action_manifest_digest=action_manifest_digest,
        )

        if interrupt_before_receipt_publish:
            raise RuntimeError("simulated staging interruption before terminal receipt publish")

        _write_immutable_mapping(receipt, self._receipt_path(receipt_digest))
        self._write_checkpoint_converged(
            receipt_id=receipt_id,
            receipt_digest=receipt_digest,
            packet_digest=inspection.packet_digest,
            target_run_id=target_run_id,
            actions=actions,
            effect_digests=effect_digests,
        )
        final_checkpoint = self._load_checkpoint(receipt_digest)
        return StageResult(receipt=receipt, replayed=False, dry_run=False, checkpoint=final_checkpoint)

    def _write_checkpoint_pending(
        self,
        *,
        receipt_id: str,
        receipt_digest: str,
        packet_digest: str,
        target_run_id: str | None,
        actions: Sequence[ActionInput],
        completed_through_index: int,
        effect_digests_so_far: Sequence[str],
    ) -> None:
        completed_count = completed_through_index + 1
        total_count = len(actions)
        next_action_id = (
            actions[completed_through_index + 1].action_id if completed_count < total_count else None
        )
        completed_digests = [
            {"action_id": actions[i].action_id, "effect_digest": effect_digests_so_far[i]}
            for i in range(completed_count)
        ]
        checkpoint = {
            "schema_version": "1.0",
            "type": "external_research_import_checkpoint",
            "checkpoint_id": f"erc_{_digest('checkpoint:' + receipt_digest)}",
            "receipt_id_prospective": receipt_id,
            "packet_digest": packet_digest,
            "workspace_id": self.workspace_id,
            "target_run_id": target_run_id,
            "status": "pending" if next_action_id is not None else "pending",
            "cursor": {
                "next_action_id": next_action_id if next_action_id is not None else actions[-1].action_id,
                "completed_count": completed_count,
                "total_count": total_count,
            },
            "completed_action_digests": completed_digests,
            "pending_action_digest": None,
            "updated_at": now_iso(),
        }
        # `pending` requires a non-null next_action_id (schema): when this is
        # the last action, the checkpoint stays pending with the last
        # action's own id as the cursor until the receipt actually publishes
        # (see contract §2.2: converged means the terminal receipt has
        # already published).
        validation = schema_validate(checkpoint, "external_research_import_checkpoint")
        if not validation.ok:
            raise InterchangeError(f"constructed checkpoint failed schema validation: {validation.errors}")
        _atomic_dump(checkpoint, self._checkpoint_path(receipt_digest))

    def _write_checkpoint_converged(
        self,
        *,
        receipt_id: str,
        receipt_digest: str,
        packet_digest: str,
        target_run_id: str | None,
        actions: Sequence[ActionInput],
        effect_digests: Sequence[str],
    ) -> None:
        completed_digests = [
            {"action_id": a.action_id, "effect_digest": d} for a, d in zip(actions, effect_digests, strict=True)
        ]
        checkpoint = {
            "schema_version": "1.0",
            "type": "external_research_import_checkpoint",
            "checkpoint_id": f"erc_{_digest('checkpoint:' + receipt_digest)}",
            "receipt_id_prospective": receipt_id,
            "packet_digest": packet_digest,
            "workspace_id": self.workspace_id,
            "target_run_id": target_run_id,
            "status": "converged",
            "cursor": {
                "next_action_id": None,
                "completed_count": len(actions),
                "total_count": len(actions),
            },
            "completed_action_digests": completed_digests,
            "pending_action_digest": None,
            "updated_at": now_iso(),
        }
        validation = schema_validate(checkpoint, "external_research_import_checkpoint")
        if not validation.ok:
            raise InterchangeError(f"constructed converged checkpoint failed schema validation: {validation.errors}")
        _atomic_dump(checkpoint, self._checkpoint_path(receipt_digest))


__all__ = [
    "ActionInput",
    "ActionResolution",
    "CallerContext",
    "CallerNotAuthorizedError",
    "DEFAULT_LIMITS",
    "ERI_READ_PERMISSION",
    "ERI_SUBMIT_PERMISSION",
    "ExternalResearchInterchange",
    "InterchangeError",
    "Limits",
    "MemberOversizeError",
    "PacketInspection",
    "PacketMember",
    "PacketTraversalError",
    "ReplayConflictError",
    "ResolutionDeclined",
    "ResolutionContext",
    "StageResult",
    "StagingIntegrityError",
    "authorize_caller",
    "compute_governance_policy_digest",
    "compute_policy_digest",
    "compute_receipt_digest_accepted",
    "compute_receipt_digest_blocked",
    "default_resolve_candidate",
    "default_resolve_source",
    "inspect_packet",
]
