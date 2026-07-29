"""RPC-4.1/RPC-4.2: run-local inference-base resolution and the durable
``inference_record`` writer.

Implements the normative service rules frozen in
``docs/dev/architecture/research-provenance-contract-freeze.md`` §14-§18 for
``inference_record`` only (``canonical_claim`` is a separate, later phase --
``services/canonical_claim_materialization.py``, not touched here). This
module never conflates an inference with the source assertions it is derived
from: an ``inference_record`` is always a distinct, separately-identified
durable record referencing exact ``{assertion_id, assertion_version}`` pairs,
never a mutation of a ``source_assertion``.

RPC-4.1 -- :meth:`AssertionInferenceMaterializer.resolve_bases` resolves a
run-local ``claim_ledger`` claim's ``inference_basis.from_claims`` through
exact, persistent ``source_assertion`` refs (contract §15.1's eligibility
rule): one workspace, an exact ``{assertion_id, assertion_version}`` match, and
``lifecycle_state: eligible`` at resolution time. Every failure mode returns a
typed skip (contract §18) -- never a partial/best-effort record.

RPC-4.2 -- :meth:`AssertionInferenceMaterializer.materialize_inference` mints
the durable record (contract §15.2's frozen identity/``version_digest``
formulas, worked vectors reproduced in this module's tests), stages+promotes
it (contract §17.7 steps 1-2), then commits the claim_ledger's
``persistent_references.inference_id``/``inference_version`` pair through
the PRIVATE
:func:`~research_foundry.services.assertion_materialization._commit_persistent_reference`
-- the F11 gate-reversal second write path (contract §17.1/§17.2/§17.7/§17.8,
T4-1 fix-cycle 2: no longer a public function, no longer satisfiable by a
caller-supplied boolean callback -- every one of §17.1's six preconditions,
including the generation-manifest entry write (§17.7a) and the CAS/commit-
proof recompute (§17.8), is independently enforced by that shared, locked
routine), never by loosening
``_reject_deferred_references``/``_DEFERRED_REFERENCE_FIELDS`` on the
existing first-materialization intake path.
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
    InferenceReferenceConflict,
    _commit_persistent_reference,
    _read_claim_ledger_generation_pointer,
    _referenced_target_ids,
    _TargetKindSpec,
    compute_commit_proof_digest,
)
from .assertion_registry import AssertionRegistry

_ASSERTION_ID_RE = re.compile(r"^ast_[a-f0-9]{64}$")
_INFERENCE_ID_RE = re.compile(r"^inf_[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

#: Contract §15.2 item 2: the algorithm name shared with `source_assertion`'s
#: own identity convention (`assertion_identity.py`), never re-invented here.
INFERENCE_IDENTITY_ALGORITHM = "sha256-canonical-json-v1"

#: Contract §15.2 item 2's frozen inference_id material payload.
INFERENCE_ID_MATERIAL_FIELDS = ("conclusion", "source_assertion_refs", "reasoning")

#: Contract §15.2 item 4 (round 3, RC-2 widened formula)'s frozen version_digest payload.
INFERENCE_VERSION_DIGEST_FIELDS = (
    "conclusion",
    "source_assertion_refs",
    "reasoning",
    "status",
    "inference_version",
)

_DEFAULT_METHOD = "run_local_claim_ledger_inference_basis"


class InferenceError(ValueError):
    """Base class for an RPC-4.1/4.2 inference-resolution/write failure."""


class InferenceMaterializationConflict(InferenceError):
    """An immutable durable inference record already exists with different bytes."""


class InferenceMaterializationInterrupted(RuntimeError):
    """Test-only interruption before a promotion/manifest step completes."""


@dataclass(frozen=True)
class ResolvedInferenceBase:
    """One eligible, exact ``{assertion_id, assertion_version}`` inference base."""

    claim_id: str
    assertion_id: str
    assertion_version: int


@dataclass(frozen=True)
class InferenceResolution:
    """RPC-4.1 outcome: either a resolved, eligible base set, or a typed skip."""

    status: str  # "resolved" | "skipped"
    bases: tuple[ResolvedInferenceBase, ...] = ()
    skip_code: str | None = None


@dataclass(frozen=True)
class InferenceMaterializationResult:
    """RPC-4.2 outcome: one run/claim's durable inference-write attempt."""

    run_id: str
    claim_id: str
    status: str  # "materialized" | "reused" | "abstained"
    inference_id: str | None = None
    inference_version: int | None = None
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

    Duplicated from ``assertion_materialization.py``/``assertion_registry.py``
    deliberately (matching this repo's own established convention of each
    ledger-adjacent service module owning its own copy of this ~15-line
    primitive rather than sharing a fourth cross-module dependency for it).
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


def inference_id_payload(
    conclusion: str, source_assertion_refs: Sequence[Mapping[str, Any]], reasoning: Mapping[str, Any]
) -> dict[str, Any]:
    """Contract §15.2 item 2's exact ``inference_id`` canonical payload."""

    return {
        "conclusion": conclusion,
        "source_assertion_refs": [dict(ref) for ref in source_assertion_refs],
        "reasoning": dict(reasoning),
    }


def inference_id_fingerprint(
    conclusion: str, source_assertion_refs: Sequence[Mapping[str, Any]], reasoning: Mapping[str, Any]
) -> str:
    return _canonical_digest(inference_id_payload(conclusion, source_assertion_refs, reasoning))


def compute_inference_id(
    conclusion: str, source_assertion_refs: Sequence[Mapping[str, Any]], reasoning: Mapping[str, Any]
) -> str:
    """MUST-grade ``inference_id`` formula (contract §15.2 item 2)."""

    return f"inf_{inference_id_fingerprint(conclusion, source_assertion_refs, reasoning)}"


def compute_inference_version_digest(
    conclusion: str,
    source_assertion_refs: Sequence[Mapping[str, Any]],
    reasoning: Mapping[str, Any],
    status: str,
    inference_version: int,
) -> str:
    """MUST-grade ``version_digest`` formula (contract §15.2 item 4, round-3 widened)."""

    payload = {
        "conclusion": conclusion,
        "source_assertion_refs": [dict(ref) for ref in source_assertion_refs],
        "reasoning": dict(reasoning),
        "status": status,
        "inference_version": inference_version,
    }
    return _canonical_digest(payload)


class AssertionInferenceMaterializer:
    """Workspace-isolated resolver and durable writer for ``inference_record``.

    Mirrors :class:`~research_foundry.services.assertion_materialization.AssertionMaterializer`'s
    workspace-scoping shape (one instance per workspace, sharing the same
    :class:`~research_foundry.services.assertion_registry.AssertionRegistry`
    root so an inference record and the source assertions it cites live under
    the identical workspace-keyed storage tree) but never shares its
    materialization logic -- inference is a distinct concern (contract §17,
    "inference stays fully separate from source assertions").
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
    # RPC-4.1 -- resolve inference bases
    # ------------------------------------------------------------------

    def resolve_bases(
        self, claim_id: str, ledger: Mapping[str, Any]
    ) -> InferenceResolution:
        """Resolve one ``inference``-status claim's bases (contract §15.1).

        Every failure path is a typed skip (contract §18) -- never an
        exception, never a partial resolution with some bases dropped.
        """

        claims = ledger.get("claims")
        if not isinstance(claims, list):
            return InferenceResolution("skipped", skip_code="invalid_claim_ledger")
        by_id: dict[str, Mapping[str, Any]] = {
            claim_id_value: claim
            for claim in claims
            if isinstance(claim, Mapping) and isinstance((claim_id_value := claim.get("claim_id")), str)
        }
        claim = by_id.get(claim_id)
        if claim is None:
            return InferenceResolution("skipped", skip_code="unresolved_inference_claim")
        if claim.get("status") != "inference":
            return InferenceResolution("skipped", skip_code="non_inference_claim_candidate")

        basis = claim.get("inference_basis")
        if not isinstance(basis, Mapping):
            return InferenceResolution("skipped", skip_code="invalid_inference_candidate")
        from_claims = basis.get("from_claims")
        if not isinstance(from_claims, list) or not from_claims:
            return InferenceResolution("skipped", skip_code="empty_support")
        if any(not isinstance(base_claim_id, str) or not base_claim_id for base_claim_id in from_claims):
            return InferenceResolution("skipped", skip_code="invalid_inference_candidate")

        # F19 (RPC-6.G validator, Karen K-1, HIGH): lazy import, mirroring
        # this repo's established convention for reaching into
        # assertion_impact.py from a sibling service module (see
        # assertion_materialization.py's own `_recheck_transitive_support`/
        # `_commit_persistent_reference_locked`).
        from .assertion_impact import effective_source_assertion_lifecycle_state

        resolved: list[ResolvedInferenceBase] = []
        seen_workspace_mismatch = False
        for base_claim_id in from_claims:
            base_claim = by_id.get(base_claim_id)
            if base_claim is None:
                return InferenceResolution("skipped", skip_code="unresolved_support_ref")
            refs = base_claim.get("persistent_references")
            if not isinstance(refs, Mapping):
                return InferenceResolution("skipped", skip_code="unresolved_support_ref")
            assertion_id = refs.get("source_assertion_id")
            assertion_version = refs.get("assertion_version")
            if (
                not isinstance(assertion_id, str)
                or not assertion_id
                or not isinstance(assertion_version, int)
                or isinstance(assertion_version, bool)
            ):
                return InferenceResolution("skipped", skip_code="unresolved_support_ref")

            assertion = self._lookup_source_assertion(assertion_id)
            if assertion is None:
                if self._exists_in_other_workspace(assertion_id):
                    seen_workspace_mismatch = True
                    continue
                return InferenceResolution("skipped", skip_code="unresolved_support_ref")
            if assertion.get("assertion_version") != assertion_version:
                return InferenceResolution("skipped", skip_code="unresolved_support_ref")
            if assertion.get("lifecycle_state") != "eligible":
                return InferenceResolution("skipped", skip_code="stale_support")
            # F19: the raw record's `lifecycle_state` never flips when P6
            # authoritatively blocks a source assertion -- the separate
            # `lifecycle_policy/<id>.yaml` artifact is the real boundary. A
            # present-but-invalid policy artifact fails closed the same way
            # (K-2) -- never silently treated as still eligible.
            if effective_source_assertion_lifecycle_state(root=self.root, assertion_id=assertion_id) != "eligible":
                return InferenceResolution("skipped", skip_code="stale_support")
            resolved.append(
                ResolvedInferenceBase(
                    claim_id=base_claim_id, assertion_id=assertion_id, assertion_version=assertion_version
                )
            )

        if seen_workspace_mismatch:
            # Contract §15.1 item 3: ANY base resolving outside this
            # workspace makes the WHOLE candidate ineligible -- never a
            # partial inference with some bases silently dropped.
            return InferenceResolution("skipped", skip_code="mixed_workspace_support")
        return InferenceResolution("resolved", bases=tuple(resolved))

    def _lookup_source_assertion(self, assertion_id: str) -> dict[str, Any] | None:
        if not _ASSERTION_ID_RE.fullmatch(assertion_id):
            return None
        path = self.root / "assertions" / f"{assertion_id}.yaml"
        if not path.is_file():
            return None
        data = load_yaml(path)
        if not isinstance(data, dict) or data.get("assertion_id") != assertion_id:
            return None
        return data

    def _exists_in_other_workspace(self, assertion_id: str) -> bool:
        """Distinguish "never materialized anywhere" from "wrong workspace".

        Directory-scoped workspace isolation makes a genuine cross-workspace
        read structurally impossible from within one resolved workspace
        (standing directive 2) -- this check only PROVES the assertion
        exists under a *different* workspace-keyed root, which is enough to
        report ``mixed_workspace_support`` instead of the less precise
        ``unresolved_support_ref`` for that case. It performs no cross-
        workspace read of any content, only an existence probe.
        """

        workspaces_root = self.paths.root / "assertion_ledger" / "workspaces"
        if not workspaces_root.is_dir():
            return False
        for workspace_dir in workspaces_root.iterdir():
            if not workspace_dir.is_dir() or workspace_dir == self.root:
                continue
            if (workspace_dir / "assertions" / f"{assertion_id}.yaml").is_file():
                return True
        return False

    # ------------------------------------------------------------------
    # RPC-4.2 -- durable inference writer
    # ------------------------------------------------------------------

    def materialize_inference(
        self,
        run_id: str,
        claim_id: str,
        *,
        method: str = _DEFAULT_METHOD,
        producer: str | None = None,
        require_producer: bool = False,
        _interrupt_after_staging: bool = False,
        _interrupt_before_manifest: bool = False,
        _interrupt_after_manifest: bool = False,
        _interrupt_after_ledger: bool = False,
    ) -> InferenceMaterializationResult:
        """Resolve, mint, durably commit, and reference one inference claim.

        Returns a typed ``abstained`` result (contract §18) for every
        precondition failure -- never raises for an expected, enumerable
        skip. Genuine data-corruption conflicts raise
        :class:`InferenceMaterializationConflict` /
        :class:`~research_foundry.services.assertion_materialization.InferenceReferenceConflict`.

        Four ordered crash-injection points exercise contract §17.7's full
        commit protocol (T4-3, RPC-7.12): ``_interrupt_after_staging``
        (between staged write and promotion), ``_interrupt_before_manifest``
        (record promoted, but the commit attempt -- manifest entry, ledger
        reference, pointer publish -- never even started),
        ``_interrupt_after_manifest`` (the NEW post-manifest/pre-ledger
        boundary the manifest-authority inversion fix introduces), and
        ``_interrupt_after_ledger`` (the NEW post-ledger/pre-pointer
        boundary). Only the LAST two are new to this fix cycle; the first
        two preserve their pre-existing behavior byte-for-byte.
        """

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

        capabilities = FoundryConfig(paths=self.paths).assertion_ledger_capabilities()
        if not capabilities.ledger_write_allowed:
            return self._abstain(run_id, claim_id, "ledger_write_disabled")

        ledger = load_yaml(run_paths.claim_ledger)
        if not isinstance(ledger, dict):
            return self._abstain(run_id, claim_id, "invalid_claim_ledger")

        resolution = self.resolve_bases(claim_id, ledger)
        if resolution.status != "resolved":
            return self._abstain(run_id, claim_id, resolution.skip_code or "unresolved_support_ref")

        claim = next(c for c in ledger["claims"] if isinstance(c, Mapping) and c.get("claim_id") == claim_id)
        conclusion = str(claim.get("text") or "").strip()
        if not conclusion:
            return self._abstain(run_id, claim_id, "invalid_inference_candidate")
        basis = claim.get("inference_basis") or {}
        reasoning_summary = basis.get("reasoning_summary") if isinstance(basis, Mapping) else None
        if not isinstance(reasoning_summary, str) or not reasoning_summary.strip():
            return self._abstain(run_id, claim_id, "invalid_inference_candidate")
        if require_producer and not producer:
            return self._abstain(run_id, claim_id, "producer_omitted")

        source_assertion_refs = [
            {"assertion_id": base.assertion_id, "assertion_version": base.assertion_version}
            for base in resolution.bases
        ]
        reasoning = {"summary": reasoning_summary, "method": method, "producer": producer}
        status = "active"
        inference_version = 1
        inference_id = compute_inference_id(conclusion, source_assertion_refs, reasoning)
        version_digest = compute_inference_version_digest(
            conclusion, source_assertion_refs, reasoning, status, inference_version
        )

        record: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "inference_record",
            "inference_id": inference_id,
            "inference_version": inference_version,
            "conclusion": conclusion,
            "source_assertion_refs": source_assertion_refs,
            "reasoning": reasoning,
            "status": status,
            "version_digest": version_digest,
        }
        validation = self.schemas.validate(record, "inference_record")
        if not validation.ok:
            return self._abstain(run_id, claim_id, "invalid_inference_record_contract")

        # T4-2: capture the expected claim-ledger generation BEFORE promotion/
        # commit -- the shared commit routine CASes against this under lock.
        expected_generation_id = _read_claim_ledger_generation_pointer(self.paths, run_id)

        self._promote(record, _interrupt_after_staging=_interrupt_after_staging)
        if _interrupt_before_manifest:
            # T4-3: this now fires between promotion and the (relocated)
            # manifest-entry write -- the record is discoverable on disk but
            # not yet referenced by anything, exactly the crash boundary
            # contract §17.7 step 6 must quarantine on recovery.
            raise InferenceMaterializationInterrupted("interrupted before manifest entry")

        support_refs_digest = _canonical_digest(source_assertion_refs)
        commit_proof_digest = compute_commit_proof_digest(
            claim_id=claim_id,
            row_sources=claim.get("sources") or [],
            row_conclusion_text=conclusion,
            target_kind="inference_record",
            target_id=inference_id,
            target_version=inference_version,
            target_version_digest=version_digest,
            support_refs_digest=support_refs_digest,
        )

        # T4-1 fix-cycle 2: the second write path is now PRIVATE and
        # independently (re)enforces every one of contract §17.1's six
        # preconditions itself, under the per-run lock, from freshly-
        # reloaded on-disk state -- this _TargetKindSpec carries only
        # kind-specific arithmetic (record path, digest formula, transitive-
        # support shape), never a "trust me" boolean.
        target = _TargetKindSpec(
            kind="inference_record",
            schema_name="inference_record",
            id_field="inference_id",
            version_field="inference_version",
            manifest_type="inference_generation_manifest",
            conflict_cls=InferenceReferenceConflict,
            interrupted_cls=InferenceMaterializationInterrupted,
            record_path=lambda rid, _rver: self._inference_path(rid),
            manifest_path=self._manifest_path,
            recompute_version_digest=lambda rec: compute_inference_version_digest(
                str(rec.get("conclusion") or ""),
                rec.get("source_assertion_refs") or [],
                rec.get("reasoning") or {},
                str(rec.get("status") or ""),
                int(rec.get("inference_version") or 0),
            ),
            is_state_active=lambda rec: rec.get("status") == "active",
            source_assertion_refs_of=lambda rec: rec.get("source_assertion_refs") or [],
            inference_refs_of=lambda _rec: (),
            # Contract §17.8's ONLY worked vector: the bare source_assertion_refs
            # list, no wrapping -- inference_record has no inference_refs field.
            support_refs_digest_of=lambda rec: _canonical_digest(rec.get("source_assertion_refs") or []),
            requires_canonical_claims_capability=False,
        )

        try:
            generation_id = _commit_persistent_reference(
                paths=self.paths,
                run_id=run_id,
                claim_id=claim_id,
                caller_workspace_id=self.workspace_id,
                target=target,
                target_id=inference_id,
                target_version=inference_version,
                expected_generation_id=expected_generation_id,
                caller_commit_proof_digest=commit_proof_digest,
                _interrupt_after_manifest=_interrupt_after_manifest,
                _interrupt_after_ledger=_interrupt_after_ledger,
            )
        except InferenceReferenceConflict as exc:
            return self._abstain(run_id, claim_id, str(exc))

        return InferenceMaterializationResult(
            run_id=run_id,
            claim_id=claim_id,
            status="materialized",
            inference_id=inference_id,
            inference_version=inference_version,
            generation_id=generation_id,
        )

    @staticmethod
    def _abstain(run_id: str, claim_id: str, code: str) -> InferenceMaterializationResult:
        return InferenceMaterializationResult(
            run_id=run_id, claim_id=claim_id, status="abstained", abstention_code=code
        )

    # ------------------------------------------------------------------
    # Durable-commit protocol (contract §17.7), scoped to inference_record
    # ------------------------------------------------------------------

    def _inference_path(self, inference_id: str) -> Path:
        if not _INFERENCE_ID_RE.fullmatch(inference_id):
            raise InferenceMaterializationConflict("invalid_inference_id")
        return self.root / "inferences" / f"{inference_id}.yaml"

    def _staging_path(self, inference_id: str) -> Path:
        return self.root / ".staging" / inference_id / f"{inference_id}.yaml"

    def _manifest_path(self) -> Path:
        return self.root / "inferences" / ".generation_manifest.yaml"

    def _promote(self, record: Mapping[str, Any], *, _interrupt_after_staging: bool) -> Path:
        """Contract §17.7 steps 1-2: staged write, then atomic promotion.

        A record already promoted at this exact content-addressed path is
        idempotent-verified (byte-identical) rather than re-written -- the
        same "conflicting deterministic record" discipline
        ``assertion_materialization.py`` already applies elsewhere.

        T4-3 fix-cycle 2: this method no longer writes the generation-
        manifest entry -- that write now happens ONLY from the claim-ledger
        commit path (``assertion_materialization._commit_persistent_reference_locked``),
        under the per-run lock, immediately before the ledger reference
        itself. A record promoted here is real, on-disk, and content-
        addressed, but is NOT yet authoritative/citable until that later
        commit succeeds (contract §17.7 step 2's "promotion alone does NOT
        make the record authoritative" rule).
        """

        inference_id = record["inference_id"]
        canonical_path = self._inference_path(inference_id)
        if canonical_path.exists():
            existing = load_yaml(canonical_path)
            if not isinstance(existing, dict) or existing != dict(record):
                raise InferenceMaterializationConflict("conflicting_inference_record")
            return canonical_path

        staging_path = self._staging_path(inference_id)
        _atomic_dump(record, staging_path)
        if _interrupt_after_staging:
            raise InferenceMaterializationInterrupted("interrupted after staged write")

        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging_path, canonical_path)
        try:
            staging_path.parent.rmdir()
        except OSError:
            pass
        return canonical_path

    def recover_orphaned_inferences(self) -> tuple[str, ...]:
        """Contract §17.7 step 6: deterministic recovery sweep.

        Quarantines (never silently adopts or re-uses):

        * a staged-but-never-promoted record (crash between steps 1-2), and
        * a promoted, content-addressed record NOT reachable from the
          CURRENT claim-ledger generation of any run this workspace owns
          (T4-3 fix-cycle 2: recovery authority is
          ``assertion_materialization._referenced_target_ids`` -- the live
          ``.claim_ledger_published.yaml`` pointer's generation snapshot --
          never a private per-record-kind manifest consulted in isolation;
          a record whose manifest entry was written but whose claim-ledger
          commit never completed, or completed against a generation that
          was later superseded, is quarantine-eligible here).

        A retried commit always starts fresh from the caller's current
        candidate (:meth:`materialize_inference`) -- it never resumes from,
        or silently wires in, a quarantined record.
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
            self.paths, workspace_id=self.workspace_id, record_kind="inference_record"
        )
        inferences_dir = self.root / "inferences"
        if inferences_dir.is_dir():
            for path in sorted(inferences_dir.glob("*.yaml")):
                inference_id = path.stem
                # Exclude the sibling ".generation_manifest.yaml" (T4-3: the
                # manifest is now written into this SAME directory as part
                # of the claim-ledger commit) -- only real, content-
                # addressed inference records match this id shape.
                if not _INFERENCE_ID_RE.fullmatch(inference_id):
                    continue
                record = load_yaml(path)
                version = record.get("inference_version") if isinstance(record, dict) else None
                if inference_id in quarantined or (inference_id, version) in referenced:
                    continue
                quarantine_dir = self.root / "quarantine" / inference_id
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                os.replace(path, quarantine_dir / path.name)
                quarantined.append(inference_id)
        return tuple(quarantined)


__all__ = [
    "INFERENCE_IDENTITY_ALGORITHM",
    "INFERENCE_ID_MATERIAL_FIELDS",
    "INFERENCE_VERSION_DIGEST_FIELDS",
    "AssertionInferenceMaterializer",
    "InferenceError",
    "InferenceMaterializationConflict",
    "InferenceMaterializationInterrupted",
    "InferenceMaterializationResult",
    "InferenceResolution",
    "ResolvedInferenceBase",
    "compute_commit_proof_digest",
    "compute_inference_id",
    "compute_inference_version_digest",
    "inference_id_fingerprint",
    "inference_id_payload",
]
