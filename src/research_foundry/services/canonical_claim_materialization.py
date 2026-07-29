"""RPC-4.3: explicit-request canonical-claim resolver and durable writer.

Implements the normative service rules frozen in
``docs/dev/architecture/research-provenance-contract-freeze.md`` §14-§18 for
``canonical_claim`` only (``inference_record`` is the separate, earlier phase
-- ``services/assertion_inference.py``, mirrored here but never imported for
its resolution logic, only for the shared
:func:`~research_foundry.services.assertion_materialization.compute_commit_proof_digest`
helper, which lives in ``assertion_materialization.py`` per contract §17.9
design note N3). A canonical claim is always a distinct, separately-identified
durable record referencing exact ``{assertion_id, assertion_version}`` and/or
``{inference_id, inference_version}`` support pairs -- never an implicit
merge, never derived from usage patterns or claim volume (contract §15.4).

RPC-4.3 -- :meth:`CanonicalClaimMaterializer.resolve_support` resolves an
EXPLICITLY NAMED set of source-assertion/inference support refs through the
same eligibility rule §15.1 already establishes for inference bases (one
workspace, exact ``{id, version}`` match, current eligible/active lifecycle
state at resolution time), plus two canonical-claim-only quality checks over
each ref's own ``relation`` (contract §18: ``ambiguous_support`` /
``conflicting_support``). Every failure mode returns a typed skip -- never a
partial/best-effort record.

:meth:`CanonicalClaimMaterializer.publish_canonical_claim` mints the durable
record (contract §15.2 item 3's frozen entity-id + per-version-digest split,
worked vectors reproduced in this module's tests), stages+promotes it
(contract §17.7 steps 1-2), then commits the claim_ledger's
``persistent_references.canonical_claim_id``/``canonical_claim_version`` pair
through the PRIVATE
:func:`~research_foundry.services.assertion_materialization._commit_persistent_reference`
-- the F11 gate-reversal second write path (contract
§17.1/§17.2/§17.3/§17.7/§17.8, T4-1 fix-cycle 2: no longer a public function,
no longer satisfiable by a caller-supplied boolean callback -- every one of
§17.1's six preconditions, including the generation-manifest entry write
(§17.7a) and the CAS/commit-proof recompute (§17.8), is independently
enforced by that shared, locked routine -- the SAME one
``assertion_inference.py`` uses, T4-4), never by loosening
``_reject_deferred_references``/``_DEFERRED_REFERENCE_FIELDS`` on the
existing first-materialization intake path. A publish call is only ever
reachable when the caller passes ``explicit_request=True`` (contract §15.4)
AND the resolved ``canonical_claims_allowed`` capability is ``True``
(contract §17.3, F12) -- on the current default configuration
(``canonical_claims_enabled: False``), this materializer publishes nothing.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..paths import FoundryPaths
from ..schemas import SchemaRegistry
from ..yamlio import dumps_yaml, load_yaml
from .assertion_materialization import (
    CanonicalClaimReferenceConflict,
    _commit_persistent_reference,
    _read_claim_ledger_generation_pointer,
    _referenced_target_ids,
    _TargetKindSpec,
    compute_commit_proof_digest,
)
from .assertion_registry import AssertionRegistry

_ASSERTION_ID_RE = re.compile(r"^ast_[a-f0-9]{64}$")
_INFERENCE_ID_RE = re.compile(r"^inf_[a-f0-9]{64}$")
_CANONICAL_CLAIM_ID_RE = re.compile(r"^ccl_[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_VALID_RELATIONS = {"supports", "contradicts", "context"}

#: Contract §15.2 item 3: the algorithm name shared with `inference_record`'s
#: own identity convention (`assertion_inference.py`), never re-invented here.
CANONICAL_CLAIM_IDENTITY_ALGORITHM = "sha256-canonical-json-v1"

#: Contract §15.2 item 3's frozen `canonical_claim_id` ENTITY payload --
#: stable across the claim's lifetime, computed ONLY from its first-proposed
#: (version 1) grounding set. Deliberately excludes `inference_refs`/`state`/
#: version/reversal fields -- those belong to `version_digest` instead.
CANONICAL_CLAIM_ID_MATERIAL_FIELDS = ("statement", "source_assertion_refs")

#: Contract §15.2 item 3 (round 3, RC-2 widened formula)'s frozen per-version
#: `version_digest` payload.
CANONICAL_CLAIM_VERSION_DIGEST_FIELDS = (
    "statement",
    "source_assertion_refs",
    "inference_refs",
    "state",
    "canonical_claim_version",
    "replaces",
    "replacement_claims",
    "reversal",
)

_DEFAULT_STATE = "active"


class CanonicalClaimError(ValueError):
    """Base class for an RPC-4.3 canonical-claim resolution/write failure."""


class CanonicalClaimMaterializationConflict(CanonicalClaimError):
    """An immutable durable canonical-claim record already exists with different bytes."""


class CanonicalClaimMaterializationInterrupted(RuntimeError):
    """Test-only interruption before a promotion/manifest step completes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ResolvedCanonicalClaimSupport:
    """One eligible, exact support ref -- either a source assertion or an inference."""

    kind: str  # "source_assertion" | "inference"
    ref: dict[str, Any]


@dataclass(frozen=True)
class CanonicalClaimResolution:
    """RPC-4.3 outcome: either a resolved, eligible support set, or a typed skip."""

    status: str  # "resolved" | "skipped"
    source_assertion_refs: tuple[dict[str, Any], ...] = ()
    inference_refs: tuple[dict[str, Any], ...] = ()
    skip_code: str | None = None
    digest: str | None = None


@dataclass(frozen=True)
class CanonicalClaimMaterializationResult:
    """RPC-4.3 outcome: one run/claim's durable canonical-claim publish attempt."""

    run_id: str
    claim_id: str
    status: str  # "materialized" | "abstained"
    canonical_claim_id: str | None = None
    canonical_claim_version: int | None = None
    generation_id: str | None = None
    abstention_code: str | None = None


def _digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _canonical_digest(value: Any) -> str:
    return _digest(_canonical_json(value))


def _atomic_dump(data: Mapping[str, Any], path: Path) -> None:
    """Write one YAML artifact atomically, with a durable file flush.

    Duplicated from ``assertion_inference.py``/``assertion_materialization.py``
    deliberately, matching this repo's own established convention of each
    ledger-adjacent service module owning its own copy of this ~15-line
    primitive rather than sharing a fourth cross-module dependency for it.
    """

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


def _normalize_ref_list(refs: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]] | None:
    """``.get()``-equivalent normalization: ``None`` stays ``None`` (omitted/null
    canonicalize identically, contract §4.1 rule 7's reused convention);
    anything else becomes a list of plain dict copies."""

    return None if refs is None else [dict(ref) for ref in refs]


def canonical_claim_id_payload(
    statement: str, source_assertion_refs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Contract §15.2 item 3's exact ``canonical_claim_id`` ENTITY payload."""

    return {"statement": statement, "source_assertion_refs": [dict(ref) for ref in source_assertion_refs]}


def canonical_claim_id_fingerprint(
    statement: str, source_assertion_refs: Sequence[Mapping[str, Any]]
) -> str:
    return _canonical_digest(canonical_claim_id_payload(statement, source_assertion_refs))


def compute_canonical_claim_id(
    statement: str, source_assertion_refs: Sequence[Mapping[str, Any]]
) -> str:
    """MUST-grade ``canonical_claim_id`` formula (contract §15.2 item 3)."""

    return f"ccl_{canonical_claim_id_fingerprint(statement, source_assertion_refs)}"


def canonical_claim_version_digest_payload(
    *,
    statement: str,
    source_assertion_refs: Sequence[Mapping[str, Any]],
    inference_refs: Sequence[Mapping[str, Any]] | None,
    state: str,
    canonical_claim_version: int,
    replaces: Sequence[Mapping[str, Any]] | None = None,
    replacement_claims: Sequence[Mapping[str, Any]] | None = None,
    reversal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Contract §15.2 item 3 (round 3, RC-2)'s exact eight-field ``version_digest``
    payload, using ``.get()``-equivalent semantics for the three trailing,
    frequently-absent fields (omission and explicit ``null`` are
    interchangeable, contract §4.1 rule 7's reused convention)."""

    return {
        "statement": statement,
        "source_assertion_refs": [dict(ref) for ref in source_assertion_refs],
        "inference_refs": _normalize_ref_list(inference_refs),
        "state": state,
        "canonical_claim_version": canonical_claim_version,
        "replaces": _normalize_ref_list(replaces),
        "replacement_claims": _normalize_ref_list(replacement_claims),
        "reversal": dict(reversal) if reversal is not None else None,
    }


def compute_canonical_claim_version_digest(
    statement: str,
    source_assertion_refs: Sequence[Mapping[str, Any]],
    inference_refs: Sequence[Mapping[str, Any]] | None,
    state: str,
    canonical_claim_version: int,
    *,
    replaces: Sequence[Mapping[str, Any]] | None = None,
    replacement_claims: Sequence[Mapping[str, Any]] | None = None,
    reversal: Mapping[str, Any] | None = None,
) -> str:
    """MUST-grade ``version_digest`` formula (contract §15.2 item 3, round-3 widened)."""

    payload = canonical_claim_version_digest_payload(
        statement=statement,
        source_assertion_refs=source_assertion_refs,
        inference_refs=inference_refs,
        state=state,
        canonical_claim_version=canonical_claim_version,
        replaces=replaces,
        replacement_claims=replacement_claims,
        reversal=reversal,
    )
    return _canonical_digest(payload)


class CanonicalClaimMaterializer:
    """Workspace-isolated resolver and durable writer for ``canonical_claim``.

    Mirrors
    :class:`~research_foundry.services.assertion_inference.AssertionInferenceMaterializer`'s
    workspace-scoping shape (one instance per workspace, sharing the same
    :class:`~research_foundry.services.assertion_registry.AssertionRegistry`
    root so a canonical claim and the source assertions/inferences it cites
    live under the identical workspace-keyed storage tree) but never shares
    its resolution logic -- a canonical claim's support set is ALWAYS
    explicitly named by the caller (contract §15.4), never derived from a
    claim_ledger row's own ``inference_basis``/``status`` field the way an
    inference base is.
    """

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        self.registry = AssertionRegistry(workspace_id=workspace_id, paths=self.paths)
        self.root = self.registry.root
        self.schemas = SchemaRegistry(schemas_dir=self.paths.schemas)

    # ------------------------------------------------------------------
    # RPC-4.3 -- resolve an EXPLICITLY NAMED support set
    # ------------------------------------------------------------------

    def resolve_support(
        self,
        source_assertion_refs: Sequence[Mapping[str, Any]],
        inference_refs: Sequence[Mapping[str, Any]] | None = None,
        *,
        allow_mixed_relations: bool = False,
    ) -> CanonicalClaimResolution:
        """Resolve an explicitly-named support set (contract §15.1/§15.4/§18).

        Every failure path is a typed skip (contract §18) -- never an
        exception, never a partial resolution with some refs silently
        dropped. Never invents or infers a support set: ``source_assertion_refs``
        (never empty -- the schema's own ``minItems: 1``) and
        ``inference_refs`` (optional, supplementary-only) are exactly what
        the caller named.
        """

        if not isinstance(source_assertion_refs, Sequence) or isinstance(source_assertion_refs, (str, bytes)):
            return CanonicalClaimResolution("skipped", skip_code="invalid_canonical_claim_candidate")
        if not source_assertion_refs and not inference_refs:
            return CanonicalClaimResolution("skipped", skip_code="empty_support")

        # F19 (RPC-6.G validator, Karen K-1, HIGH): lazy import, mirroring
        # this repo's established convention for reaching into
        # assertion_impact.py from a sibling service module (see
        # assertion_materialization.py's own `_recheck_transitive_support`/
        # `_commit_persistent_reference_locked`).
        from .assertion_impact import (
            ImpactOperationError,
            collect_stale_object_ids,
            effective_source_assertion_lifecycle_state,
        )

        resolved_assertions: list[dict[str, Any]] = []
        resolved_inferences: list[dict[str, Any]] = []
        seen_workspace_mismatch = False
        relations: set[str] = set()

        # SOL-39: consult the SAME strict, effective stale-inference-ids the
        # commit-time recheck (`_recheck_transitive_support`, via
        # `collect_stale_object_ids(strict=True)`) already uses -- resolution
        # must not report "resolved" for effect-stale inference support that
        # the locked commit will catch moments later anyway; all-writer
        # consistency (contract §17.1 item 6) requires the SAME verdict at
        # both resolve and commit time. `strict=True` (same posture as the
        # commit path, not the P5 read-degrade path) so a corrupt impact
        # receipt fails this resolution closed too, never silently un-stales
        # it. Computed once, only when there is an inference ref to check.
        stale_inference_ids: frozenset[str] = frozenset()
        if inference_refs:
            try:
                stale_inference_ids = collect_stale_object_ids(
                    paths=self.paths, workspace_id=self.workspace_id, strict=True
                ).get("inference", frozenset())
            except ImpactOperationError:
                return CanonicalClaimResolution("skipped", skip_code="stale_support")

        for raw_ref in source_assertion_refs:
            if not isinstance(raw_ref, Mapping):
                return CanonicalClaimResolution("skipped", skip_code="invalid_canonical_claim_candidate")
            assertion_id = raw_ref.get("assertion_id")
            assertion_version = raw_ref.get("assertion_version")
            relation = raw_ref.get("relation")
            if (
                not isinstance(assertion_id, str)
                or not assertion_id
                or not isinstance(assertion_version, int)
                or isinstance(assertion_version, bool)
                or relation not in _VALID_RELATIONS
            ):
                return CanonicalClaimResolution("skipped", skip_code="invalid_canonical_claim_candidate")

            assertion = self._lookup_workspace_record("assertions", assertion_id)
            if assertion is None:
                if self._exists_in_other_workspace("assertions", assertion_id):
                    seen_workspace_mismatch = True
                    continue
                return CanonicalClaimResolution("skipped", skip_code="unresolved_support_ref")
            if (
                assertion.get("assertion_id") != assertion_id
                or assertion.get("assertion_version") != assertion_version
            ):
                return CanonicalClaimResolution("skipped", skip_code="unresolved_support_ref")
            if assertion.get("lifecycle_state") != "eligible":
                return CanonicalClaimResolution("skipped", skip_code="stale_support")
            # F19: the raw record's `lifecycle_state` never flips when P6
            # authoritatively blocks a source assertion -- the separate
            # `lifecycle_policy/<id>.yaml` artifact is the real boundary. A
            # present-but-invalid policy artifact fails closed the same way
            # (K-2) -- never silently treated as still eligible.
            if effective_source_assertion_lifecycle_state(root=self.root, assertion_id=assertion_id) != "eligible":
                return CanonicalClaimResolution("skipped", skip_code="stale_support")

            relations.add(relation)
            resolved_assertions.append(
                {"assertion_id": assertion_id, "assertion_version": assertion_version, "relation": relation}
            )

        for raw_ref in inference_refs or ():
            if not isinstance(raw_ref, Mapping):
                return CanonicalClaimResolution("skipped", skip_code="invalid_canonical_claim_candidate")
            inference_id = raw_ref.get("inference_id")
            inference_version = raw_ref.get("inference_version")
            relation = raw_ref.get("relation")
            if (
                not isinstance(inference_id, str)
                or not inference_id
                or not isinstance(inference_version, int)
                or isinstance(inference_version, bool)
                or relation not in _VALID_RELATIONS
            ):
                return CanonicalClaimResolution("skipped", skip_code="invalid_canonical_claim_candidate")

            inference = self._lookup_workspace_record("inferences", inference_id)
            if inference is None:
                if self._exists_in_other_workspace("inferences", inference_id):
                    seen_workspace_mismatch = True
                    continue
                return CanonicalClaimResolution("skipped", skip_code="unresolved_support_ref")
            if (
                inference.get("inference_id") != inference_id
                or inference.get("inference_version") != inference_version
            ):
                return CanonicalClaimResolution("skipped", skip_code="unresolved_support_ref")
            # SOL-39: the raw record's `status` field never flips when P6
            # marks an inference effect-stale (N7 -- the immutable record is
            # never mutated in place); belt-and-suspenders, matching
            # `_recheck_transitive_support`'s own dual check.
            if inference.get("status") != "active" or inference_id in stale_inference_ids:
                return CanonicalClaimResolution("skipped", skip_code="stale_support")

            relations.add(relation)
            resolved_inferences.append(
                {"inference_id": inference_id, "inference_version": inference_version, "relation": relation}
            )

        if seen_workspace_mismatch:
            # Contract §15.1 item 3, reused for canonical claims: ANY base
            # resolving outside this workspace makes the WHOLE candidate
            # ineligible -- never a partial canonical claim with some refs
            # silently dropped.
            return CanonicalClaimResolution("skipped", skip_code="mixed_workspace_support")

        if not resolved_assertions and not resolved_inferences:
            return CanonicalClaimResolution("skipped", skip_code="empty_support")

        if not allow_mixed_relations and "supports" in relations and "contradicts" in relations:
            # Two (or more) named bases disagree on polarity with no
            # caller-supplied adjudication (§18: ambiguous_support).
            return CanonicalClaimResolution("skipped", skip_code="ambiguous_support")
        if relations == {"contradicts"}:
            # Every named base OPPOSES the statement -- publishing this as
            # an active canonical claim would conflict with its own support
            # (§18: conflicting_support). A caller that genuinely means to
            # record only opposing evidence is not "canonicalizing" a claim.
            return CanonicalClaimResolution("skipped", skip_code="conflicting_support")

        digest = _canonical_digest(
            {"source_assertion_refs": resolved_assertions, "inference_refs": resolved_inferences}
        )
        return CanonicalClaimResolution(
            "resolved",
            source_assertion_refs=tuple(resolved_assertions),
            inference_refs=tuple(resolved_inferences),
            digest=digest,
        )

    def _lookup_workspace_record(self, subdir: str, record_id: str) -> dict[str, Any] | None:
        pattern = _ASSERTION_ID_RE if subdir == "assertions" else _INFERENCE_ID_RE
        if not pattern.fullmatch(record_id):
            return None
        path = self.root / subdir / f"{record_id}.yaml"
        if not path.is_file():
            return None
        data = load_yaml(path)
        return data if isinstance(data, dict) else None

    def _exists_in_other_workspace(self, subdir: str, record_id: str) -> bool:
        """Distinguish "never materialized anywhere" from "wrong workspace"
        (mirrors ``AssertionInferenceMaterializer._exists_in_other_workspace``,
        generalized across both the ``assertions`` and ``inferences``
        subdirectories). Performs an existence probe only, never a
        cross-workspace content read."""

        workspaces_root = self.paths.root / "assertion_ledger" / "workspaces"
        if not workspaces_root.is_dir():
            return False
        for workspace_dir in workspaces_root.iterdir():
            if not workspace_dir.is_dir() or workspace_dir == self.root:
                continue
            if (workspace_dir / subdir / f"{record_id}.yaml").is_file():
                return True
        return False

    # ------------------------------------------------------------------
    # RPC-4.3 -- durable canonical-claim writer
    # ------------------------------------------------------------------

    def publish_canonical_claim(
        self,
        run_id: str,
        claim_id: str,
        *,
        statement: str,
        source_assertion_refs: Sequence[Mapping[str, Any]],
        inference_refs: Sequence[Mapping[str, Any]] | None = None,
        explicit_request: bool = False,
        state: str = _DEFAULT_STATE,
        allow_mixed_relations: bool = False,
        previously_resolved: CanonicalClaimResolution | None = None,
        _interrupt_after_staging: bool = False,
        _interrupt_before_manifest: bool = False,
        _interrupt_after_manifest: bool = False,
        _interrupt_after_ledger: bool = False,
    ) -> CanonicalClaimMaterializationResult:
        """Resolve, mint, durably commit, and reference one canonical claim.

        Returns a typed ``abstained`` result (contract §18) for every
        precondition failure -- never raises for an expected, enumerable
        skip. Genuine data-corruption conflicts raise
        :class:`CanonicalClaimMaterializationConflict` /
        :class:`~research_foundry.services.assertion_materialization.CanonicalClaimReferenceConflict`.

        ``explicit_request`` MUST be ``True`` -- contract §15.4's "never
        automatic or inferred" rule, enforced as the very first gate: a
        caller that omits it (the safe default) gets ``implicit_merge_rejected``
        before anything else is even read. ``previously_resolved``, if
        supplied, is compared against a FRESH resolution of the identical
        named refs: a caller that resolved a support set once, then supplies
        DIFFERENT refs (or the underlying support drifted) before actually
        publishing, gets ``substitution_rejected`` rather than silently
        publishing against a support set that no longer matches what was
        originally verified eligible.

        Four ordered crash-injection points exercise contract §17.7's full
        commit protocol (T4-3, RPC-7.12), mirroring
        ``AssertionInferenceMaterializer.materialize_inference`` exactly:
        ``_interrupt_after_staging``, ``_interrupt_before_manifest``
        (pre-existing, unchanged semantics), ``_interrupt_after_manifest``
        and ``_interrupt_after_ledger`` (NEW post-manifest/pre-ledger and
        post-ledger/pre-pointer boundaries this fix cycle introduces).
        """

        if not explicit_request:
            return self._abstain(run_id, claim_id, "implicit_merge_rejected")

        if not _TOKEN_RE.fullmatch(run_id):
            return self._abstain(run_id, claim_id, "invalid_run_id")

        run_paths = self.paths.run_paths(run_id)
        if not run_paths.run.exists() or not run_paths.claim_ledger.exists():
            return self._abstain(run_id, claim_id, "missing_run_or_claim_ledger")

        # Contract §17.8 item 1 / SOL-14: ownership derives from run.yaml's
        # OWN workspace_id, never the caller's resolved workspace alone.
        run_doc = load_yaml(run_paths.run_yaml) if run_paths.run_yaml.exists() else None
        run_workspace_id = run_doc.get("workspace_id") if isinstance(run_doc, Mapping) else None
        if run_workspace_id != self.workspace_id:
            return self._abstain(run_id, claim_id, "run_workspace_mismatch")

        # Contract §17.3 (F12): checked at RESOLUTION time -- a canonical
        # claim never reaches the mint/commit steps below when this
        # resolves False, on the current default configuration.
        capabilities = FoundryConfig(paths=self.paths).assertion_ledger_capabilities()
        if not capabilities.canonical_claims_allowed:
            return self._abstain(run_id, claim_id, "canonical_claims_disabled")

        ledger = load_yaml(run_paths.claim_ledger)
        if not isinstance(ledger, dict) or not isinstance(ledger.get("claims"), list):
            return self._abstain(run_id, claim_id, "invalid_claim_ledger")
        claim = next(
            (c for c in ledger["claims"] if isinstance(c, Mapping) and c.get("claim_id") == claim_id), None
        )
        if claim is None:
            return self._abstain(run_id, claim_id, "unresolved_canonical_claim_row")

        if not isinstance(statement, str) or not statement.strip():
            return self._abstain(run_id, claim_id, "invalid_canonical_claim_candidate")

        resolution = self.resolve_support(
            source_assertion_refs, inference_refs, allow_mixed_relations=allow_mixed_relations
        )
        if resolution.status != "resolved":
            return self._abstain(run_id, claim_id, resolution.skip_code or "unresolved_support_ref")

        if previously_resolved is not None and previously_resolved.digest != resolution.digest:
            # A prior candidate/base was substituted for a different one
            # after initial resolution, before publish (§18: substitution_rejected).
            return self._abstain(run_id, claim_id, "substitution_rejected")

        canonical_claim_version = 1
        canonical_claim_id = compute_canonical_claim_id(statement, resolution.source_assertion_refs)
        version_digest = compute_canonical_claim_version_digest(
            statement,
            resolution.source_assertion_refs,
            resolution.inference_refs or None,
            state,
            canonical_claim_version,
        )

        record: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "canonical_claim",
            "canonical_claim_id": canonical_claim_id,
            "canonical_claim_version": canonical_claim_version,
            "state": state,
            "statement": statement,
            "source_assertion_refs": list(resolution.source_assertion_refs),
            "version_digest": version_digest,
        }
        if resolution.inference_refs:
            record["inference_refs"] = list(resolution.inference_refs)

        validation = self.schemas.validate(record, "canonical_claim")
        if not validation.ok:
            return self._abstain(run_id, claim_id, "invalid_canonical_claim_contract")

        # T4-2: capture the expected claim-ledger generation BEFORE
        # promotion/commit -- the shared commit routine CASes against this
        # under lock.
        expected_generation_id = _read_claim_ledger_generation_pointer(self.paths, run_id)

        self._promote(record, _interrupt_after_staging=_interrupt_after_staging)
        if _interrupt_before_manifest:
            # T4-3: fires between promotion and the (relocated) manifest-
            # entry write -- the record is discoverable on disk but not yet
            # referenced by anything.
            raise CanonicalClaimMaterializationInterrupted("interrupted before manifest entry")

        # Design decision (documented, no single worked vector exists in the
        # contract freeze doc for a canonical-claim TARGET's own
        # support_refs_digest -- §17.8's only worked vector uses an
        # inference_record target): bind the commit proof to BOTH support
        # kinds together, since a canonical claim's full support is the
        # combination of its source_assertion_refs AND inference_refs, not
        # either alone.
        support_refs_digest = _canonical_digest(
            {
                "source_assertion_refs": list(resolution.source_assertion_refs),
                "inference_refs": list(resolution.inference_refs),
            }
        )
        commit_proof_digest = compute_commit_proof_digest(
            claim_id=claim_id,
            row_sources=claim.get("sources") or [],
            row_conclusion_text=str(claim.get("text") or ""),
            target_kind="canonical_claim",
            target_id=canonical_claim_id,
            target_version=canonical_claim_version,
            target_version_digest=version_digest,
            support_refs_digest=support_refs_digest,
        )

        # T4-1 fix-cycle 2: the second write path is now PRIVATE and
        # independently (re)enforces every one of contract §17.1's six
        # preconditions itself, under the per-run lock, from freshly-
        # reloaded on-disk state -- the SAME shared routine
        # ``assertion_inference.py`` uses (T4-4), never a "trust me" boolean.
        target = _TargetKindSpec(
            kind="canonical_claim",
            schema_name="canonical_claim",
            id_field="canonical_claim_id",
            version_field="canonical_claim_version",
            manifest_type="canonical_claim_generation_manifest",
            conflict_cls=CanonicalClaimReferenceConflict,
            interrupted_cls=CanonicalClaimMaterializationInterrupted,
            record_path=lambda rid, rver: self._canonical_claim_path(rid, rver),
            manifest_path=self._manifest_path,
            recompute_version_digest=lambda rec: compute_canonical_claim_version_digest(
                str(rec.get("statement") or ""),
                rec.get("source_assertion_refs") or [],
                rec.get("inference_refs"),
                str(rec.get("state") or ""),
                int(rec.get("canonical_claim_version") or 0),
                replaces=rec.get("replaces"),
                replacement_claims=rec.get("replacement_claims"),
                reversal=rec.get("reversal"),
            ),
            is_state_active=lambda rec: rec.get("state") == "active",
            source_assertion_refs_of=lambda rec: rec.get("source_assertion_refs") or [],
            inference_refs_of=lambda rec: rec.get("inference_refs") or [],
            # Design decision (documented above at the caller's own
            # commit_proof_digest computation): bind BOTH support kinds
            # together, since a canonical claim's full support is the
            # combination of source_assertion_refs AND inference_refs.
            support_refs_digest_of=lambda rec: _canonical_digest(
                {
                    "source_assertion_refs": list(rec.get("source_assertion_refs") or []),
                    "inference_refs": list(rec.get("inference_refs") or []),
                }
            ),
            requires_canonical_claims_capability=True,
        )

        try:
            generation_id = _commit_persistent_reference(
                paths=self.paths,
                run_id=run_id,
                claim_id=claim_id,
                caller_workspace_id=self.workspace_id,
                target=target,
                target_id=canonical_claim_id,
                target_version=canonical_claim_version,
                expected_generation_id=expected_generation_id,
                caller_commit_proof_digest=commit_proof_digest,
                _interrupt_after_manifest=_interrupt_after_manifest,
                _interrupt_after_ledger=_interrupt_after_ledger,
            )
        except CanonicalClaimReferenceConflict as exc:
            return self._abstain(run_id, claim_id, str(exc))

        return CanonicalClaimMaterializationResult(
            run_id=run_id,
            claim_id=claim_id,
            status="materialized",
            canonical_claim_id=canonical_claim_id,
            canonical_claim_version=canonical_claim_version,
            generation_id=generation_id,
        )

    @staticmethod
    def _abstain(run_id: str, claim_id: str, code: str) -> CanonicalClaimMaterializationResult:
        return CanonicalClaimMaterializationResult(
            run_id=run_id, claim_id=claim_id, status="abstained", abstention_code=code
        )

    # ------------------------------------------------------------------
    # Durable-commit protocol (contract §17.7), scoped to canonical_claim
    # ------------------------------------------------------------------

    def _canonical_claim_path(self, canonical_claim_id: str, canonical_claim_version: int) -> Path:
        if not _CANONICAL_CLAIM_ID_RE.fullmatch(canonical_claim_id):
            raise CanonicalClaimMaterializationConflict("invalid_canonical_claim_id")
        return self.root / "canonical_claims" / canonical_claim_id / f"{canonical_claim_version}.yaml"

    def _staging_path(self, canonical_claim_id: str, _canonical_claim_version: int) -> Path:
        """T4-3 fix-cycle 2: the frozen §17.7 step-1 shape --
        ``.staging/<record_id>/<record_id>.yaml`` -- keyed on the record's
        own stable entity id, matching ``AssertionInferenceMaterializer``'s
        staging path exactly. Prior code diverged here
        (``.staging/<id>-v<version>/<version>.yaml``); ``canonical_claim_version``
        is accepted (and ignored) only to keep this method's call shape
        uniform with :meth:`_canonical_claim_path`.
        """

        return self.root / ".staging" / canonical_claim_id / f"{canonical_claim_id}.yaml"

    def _manifest_path(self) -> Path:
        return self.root / "canonical_claims" / ".generation_manifest.yaml"

    def _promote(self, record: Mapping[str, Any], *, _interrupt_after_staging: bool) -> Path:
        """Contract §17.7 steps 1-2: staged write, then atomic promotion.

        A record already promoted at this exact content-addressed
        ``(canonical_claim_id, canonical_claim_version)`` path is
        idempotent-verified (byte-identical) rather than re-written -- the
        same "conflicting deterministic record" discipline
        ``assertion_inference.py``/``assertion_materialization.py`` already
        apply elsewhere.

        T4-3 fix-cycle 2: this method no longer writes the generation-
        manifest entry -- that write now happens ONLY from the claim-ledger
        commit path (``assertion_materialization._commit_persistent_reference_locked``),
        under the per-run lock, immediately before the ledger reference
        itself. A record promoted here is real, on-disk, and content-
        addressed, but is NOT yet authoritative/citable until that later
        commit succeeds (contract §17.7 step 2).
        """

        canonical_claim_id = record["canonical_claim_id"]
        canonical_claim_version = record["canonical_claim_version"]
        canonical_path = self._canonical_claim_path(canonical_claim_id, canonical_claim_version)
        if canonical_path.exists():
            existing = load_yaml(canonical_path)
            if not isinstance(existing, dict) or existing != dict(record):
                raise CanonicalClaimMaterializationConflict("conflicting_canonical_claim_record")
            return canonical_path

        staging_path = self._staging_path(canonical_claim_id, canonical_claim_version)
        _atomic_dump(record, staging_path)
        if _interrupt_after_staging:
            raise CanonicalClaimMaterializationInterrupted("interrupted after staged write")

        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging_path, canonical_path)
        try:
            staging_path.parent.rmdir()
        except OSError:
            pass
        return canonical_path

    def recover_orphaned_canonical_claims(self) -> tuple[str, ...]:
        """Contract §17.7 step 6: deterministic recovery sweep.

        Quarantines (never silently adopts or re-uses):

        * a staged-but-never-promoted record (crash between steps 1-2), and
        * a promoted, content-addressed record NOT reachable from the
          CURRENT claim-ledger generation of any run this workspace owns
          (T4-3 fix-cycle 2: recovery authority is
          ``assertion_materialization._referenced_target_ids`` -- the live
          ``.claim_ledger_published.yaml`` pointer's generation snapshot --
          never a private per-record-kind manifest consulted in isolation).

        Quarantine destination is the frozen §17.7 step-6 shape --
        ``quarantine/<canonical_claim_id>/`` -- distinguishing versions of
        the same entity by filename (``<version>.yaml``) inside that one
        directory, never a version-suffixed directory name.

        A retried publish always starts fresh from the caller's current
        candidate (:meth:`publish_canonical_claim`) -- it never resumes
        from, or silently wires in, a quarantined record.
        """

        quarantined: list[str] = []
        staging_root = self.root / ".staging"
        if staging_root.is_dir():
            for child in sorted(staging_root.iterdir()):
                if not child.is_dir():
                    continue
                quarantine_dir = self.root / "quarantine" / child.name
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                for item in child.iterdir():
                    os.replace(item, quarantine_dir / item.name)
                try:
                    child.rmdir()
                except OSError:
                    pass
                quarantined.append(child.name)

        referenced = _referenced_target_ids(
            self.paths, workspace_id=self.workspace_id, record_kind="canonical_claim"
        )
        claims_dir = self.root / "canonical_claims"
        if claims_dir.is_dir():
            for entity_dir in sorted(claims_dir.iterdir()):
                if not entity_dir.is_dir():
                    continue
                canonical_claim_id = entity_dir.name
                for path in sorted(entity_dir.glob("*.yaml")):
                    try:
                        version = int(path.stem)
                    except ValueError:
                        continue
                    label = f"{canonical_claim_id}-v{version}"
                    if label in quarantined or (canonical_claim_id, version) in referenced:
                        continue
                    quarantine_dir = self.root / "quarantine" / canonical_claim_id
                    quarantine_dir.mkdir(parents=True, exist_ok=True)
                    os.replace(path, quarantine_dir / path.name)
                    quarantined.append(label)
                try:
                    entity_dir.rmdir()
                except OSError:
                    pass
        return tuple(quarantined)


__all__ = [
    "CANONICAL_CLAIM_IDENTITY_ALGORITHM",
    "CANONICAL_CLAIM_ID_MATERIAL_FIELDS",
    "CANONICAL_CLAIM_VERSION_DIGEST_FIELDS",
    "CanonicalClaimError",
    "CanonicalClaimMaterializationConflict",
    "CanonicalClaimMaterializationInterrupted",
    "CanonicalClaimMaterializationResult",
    "CanonicalClaimMaterializer",
    "CanonicalClaimResolution",
    "ResolvedCanonicalClaimSupport",
    "canonical_claim_id_fingerprint",
    "canonical_claim_id_payload",
    "canonical_claim_version_digest_payload",
    "compute_canonical_claim_id",
    "compute_canonical_claim_version_digest",
]
