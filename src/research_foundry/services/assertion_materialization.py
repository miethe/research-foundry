"""Fail-closed P3 materialization for passage-bound source assertions.

This module intentionally consumes only the existing deterministic 1:1
``extraction_card.extracted_facts`` to run-local claim mapping.  It neither
segments passages nor attempts citation resolution, semantic merging, canonical
claims, or automatic reuse.  A candidate is materialized only when the
extraction fact, claim locator, source-card evidence point, private registry
edition, and exact passage all bind to one another.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..assertion_identity import (
    SOURCE_ASSERTION_IDENTITY_ALGORITHM,
    SOURCE_ASSERTION_MATERIAL_FIELDS,
    source_assertion_fingerprint,
    source_assertion_id,
)
from ..config import FoundryConfig
from ..frontmatter import load_md
from ..paths import FoundryPaths
from ..schemas import SchemaRegistry
from ..yamlio import dumps_yaml, load_yaml
from .assertion_registry import AssertionRegistry, RegistryIntegrityError
from .claim_mapping import (
    EXTRACTION_FACT_CLAIM_MAPPING_VERSION,
    ExtractionFactClaimMapping,
    validate_extraction_fact_claim_mappings,
)
from .rights_triage import compute_capture_rights_summary, maybe_assess_substitutability

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_ASSERTION_ID_RE = re.compile(r"^ast_[a-f0-9]{64}$")
_OBSERVATION_ID_RE = re.compile(r"^obs_[a-f0-9]{64}$")
_EVALUATION_ID_RE = re.compile(r"^aev_[a-f0-9]{64}$")
_AUDIT_ID_RE = re.compile(r"^aud_[a-f0-9]{64}$")
_GENERATION_ID_RE = re.compile(r"^mat_[a-f0-9]{64}$")
# RPC F11 gate-reversal seam (research-provenance-continuity, P4/RPC-4.2):
# validates an inference_id supplied to _commit_persistent_reference() below --
# never used to relax _DEFERRED_REFERENCE_FIELDS/_reject_deferred_references,
# which stay exactly as strict as before for _prepare_one's fresh-candidate
# intake path (contract freeze doc §17.2).
_INFERENCE_ID_RE = re.compile(r"^inf_[a-f0-9]{64}$")
# RPC F11 gate-reversal seam (research-provenance-continuity, P4/RPC-4.3):
# validates a canonical_claim_id supplied to _commit_persistent_reference()
# below -- same non-relaxation guarantee as _INFERENCE_ID_RE above.
_CANONICAL_CLAIM_ID_RE = re.compile(r"^ccl_[a-f0-9]{64}$")
_KNOWN_QUALIFIERS = {
    "modality",
    "negation",
    "population",
    "geography",
    "timeframe",
    "intervention_or_exposure",
    "outcome",
}
_DEFERRED_REFERENCE_FIELDS = {
    "canonical_claim_id",
    "canonical_claim_version",
    "inference_id",
}
_MAX_REPLAY_BATCH = 50


class MaterializationError(ValueError):
    """Base class for a P3 materialization failure."""


class MaterializationConflict(MaterializationError):
    """An immutable deterministic record already exists with different bytes."""


class MaterializationInterrupted(RuntimeError):
    """Test-only interruption before the publication pointer is replaced."""


class InferenceReferenceConflict(MaterializationError):
    """A claim_ledger row's inference reference cannot be committed as requested.

    Raised by the private :func:`_commit_persistent_reference`/
    :func:`_commit_persistent_reference_locked` -- the F11 gate-reversal
    SECOND, SEPARATE write path (contract freeze doc §17.1/§17.2), reachable
    ONLY from ``AssertionInferenceMaterializer.materialize_inference`` (T4-1
    fix-cycle 2: this write path is no longer public). Never raised by
    ``_prepare_one``'s fresh-candidate intake path, which keeps rejecting any
    candidate that already carries a non-null
    ``inference_id``/``canonical_claim_id``/``canonical_claim_version`` via
    the unmodified ``_reject_deferred_references``/``_DEFERRED_REFERENCE_FIELDS``
    gate above.
    """


class CanonicalClaimReferenceConflict(MaterializationError):
    """A claim_ledger row's canonical-claim reference cannot be committed as requested.

    Raised by the private :func:`_commit_persistent_reference`/
    :func:`_commit_persistent_reference_locked` -- the F11 gate-reversal
    SECOND, SEPARATE write path for ``canonical_claim_id``/``canonical_claim_version``
    (contract freeze doc §17.1/§17.2/§17.3), reachable ONLY from
    ``CanonicalClaimMaterializer.publish_canonical_claim`` (T4-1 fix-cycle 2:
    this write path is no longer public), mirroring
    :class:`InferenceReferenceConflict` exactly. Never raised by
    ``_prepare_one``'s fresh-candidate intake path, which keeps rejecting any
    candidate that already carries a non-null ``canonical_claim_id``/
    ``canonical_claim_version``/``inference_id`` via the unmodified
    ``_reject_deferred_references``/``_DEFERRED_REFERENCE_FIELDS`` gate above.
    """


class _Abstain(MaterializationError):
    """Internal typed result for a candidate that cannot be safely linked."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AbstainedClaim:
    """One individually-abstained fact within a skip-and-continue run (P2-01b).

    Recorded per-fact in a run's abstention breakdown instead of the first
    abstention aborting the entire run -- see
    :meth:`AssertionMaterializer._prepare`.
    """

    claim_id: str
    code: str


@dataclass(frozen=True)
class MaterializationResult:
    """One run's immutable P3 materialization outcome."""

    run_id: str
    status: str
    assertion_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    generation_id: str | None = None
    abstention_code: str | None = None
    abstained_claims: tuple[AbstainedClaim, ...] = ()


@dataclass(frozen=True)
class ReplayResult:
    """Bounded replay result; pass ``next_cursor`` to resume deterministically."""

    results: tuple[MaterializationResult, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class _PreparedRecord:
    mapping: ExtractionFactClaimMapping
    persistent_references: dict[str, Any]
    assertion: dict[str, Any]
    evaluation: dict[str, Any]
    observation: dict[str, Any]
    audit: dict[str, Any]


def _digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _canonical_digest(value: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _digest(encoded)


def _atomic_dump(data: Mapping[str, Any], path: Path) -> None:
    """Write one YAML artifact atomically, with a durable file flush."""

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


class AssertionMaterializer:
    """Workspace-isolated, passage-bound source assertion publisher.

    Immutable assertion/evaluation/observation/audit blobs are written before
    a run generation pointer.  The pointer is the visibility boundary: an
    interruption leaves at most unreferenced immutable blobs, and a retry
    verifies and reuses them before atomically publishing the same generation.
    """

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        self.registry = AssertionRegistry(workspace_id=workspace_id, paths=self.paths)
        self.root = self.registry.root
        self.schemas = SchemaRegistry(schemas_dir=self.paths.schemas)

    def materialize_run(
        self,
        run_id: str,
        *,
        _interrupt_before_publish: bool = False,
    ) -> MaterializationResult:
        """Materialize one run or return a typed, non-mutating abstention."""

        try:
            self._require_token(run_id, "run_id")
            run_paths = self.paths.run_paths(run_id)
            if not run_paths.run.exists() or not run_paths.claim_ledger.exists():
                raise _Abstain("missing_run_or_claim_ledger")
            ledger = load_yaml(run_paths.claim_ledger)
            if not isinstance(ledger, dict):
                raise _Abstain("invalid_claim_ledger")
            prepared, abstained = self._prepare(run_id, ledger)
        except _Abstain as abstention:
            return MaterializationResult(
                run_id=run_id,
                status="abstained",
                abstention_code=abstention.code,
            )

        if not prepared:
            # Skip-and-continue (P2-01b): every fact in this run individually
            # abstained, but the run itself (ledger, mappings) is valid -- the
            # run completes with a 100% abstention receipt instead of raising.
            # Preserve the pre-P2-01b single-abstention_code contract when
            # there is exactly one abstaining fact (the historical single-fact
            # abstain shape); multi-fact abstention breakdowns live in
            # abstained_claims.
            return MaterializationResult(
                run_id=run_id,
                status="abstained",
                abstention_code=abstained[0].code if len(abstained) == 1 else None,
                abstained_claims=tuple(abstained),
            )

        generation = self._generation(run_id, prepared)
        pointer = self._published_pointer_path(run_id)
        if pointer.exists():
            published = self._load_published_generation(run_id)
            if published.get("generation_id") != generation["generation_id"]:
                raise MaterializationConflict("published_run_generation_conflict")
            if published != generation:
                raise MaterializationConflict("published_run_manifest_conflict")
            self._verify_published_records(prepared)
            self._apply_claim_references(run_id, ledger, prepared)
            return self._result(run_id, "reused", prepared, generation["generation_id"], abstained)

        self._preflight_existing(prepared)
        for item in prepared:
            self._write_immutable_assertion(item.assertion)
            self._write_immutable(item.observation, self._observation_path(item.observation["observation_id"]))
            self._write_immutable(item.evaluation, self._evaluation_path(item.evaluation["evaluation_id"]))
            self._write_immutable(item.audit, self._audit_path(item.audit["audit_id"]))

        generation_path = self._generation_path(run_id, generation["generation_id"])
        self._write_immutable(generation, generation_path)
        if _interrupt_before_publish:
            raise MaterializationInterrupted("interrupted before materialization publication")

        # The durable generation is visible before the optional run-local
        # projection.  A retry repairs that additive projection if interrupted.
        _atomic_dump(
            {"generation_id": generation["generation_id"]},
            pointer,
        )
        self._apply_claim_references(run_id, ledger, prepared)
        return self._result(run_id, "materialized", prepared, generation["generation_id"], abstained)

    def replay_p0(
        self,
        run_ids: Sequence[str],
        *,
        limit: int = _MAX_REPLAY_BATCH,
        cursor: str | None = None,
    ) -> ReplayResult:
        """Replay a bounded, deterministic P0 run set with an explicit cursor."""

        if not 1 <= limit <= _MAX_REPLAY_BATCH:
            raise ValueError(f"limit must be between 1 and {_MAX_REPLAY_BATCH}")
        ordered = tuple(sorted(dict.fromkeys(run_ids)))
        if cursor is not None and cursor not in ordered:
            raise ValueError("unknown replay cursor")
        start = ordered.index(cursor) + 1 if cursor is not None else 0
        selected = ordered[start : start + limit]
        results = tuple(self.materialize_run(run_id) for run_id in selected)
        has_more = start + len(selected) < len(ordered)
        return ReplayResult(results=results, next_cursor=selected[-1] if has_more and selected else None)

    def _prepare(
        self, run_id: str, ledger: dict[str, Any]
    ) -> tuple[tuple[_PreparedRecord, ...], tuple[AbstainedClaim, ...]]:
        """Prepare every materializable fact; skip-and-continue on the rest.

        P2-01b: a single fact's ``_Abstain`` no longer propagates out of this
        loop and aborts the whole run. Each fact is evaluated independently;
        an abstaining fact is recorded in the returned abstention breakdown
        and processing continues with the run's remaining facts. Ledger-level
        failures (invalid mapping, empty mapping) still abort the whole run --
        those are preconditions for iterating facts at all, not a per-fact
        outcome.
        """

        try:
            mappings = validate_extraction_fact_claim_mappings(run_id, ledger, paths=self.paths)
        except ValueError as exc:
            raise _Abstain(str(exc)) from exc
        if not mappings:
            raise _Abstain("empty_fact_claim_mapping")

        # ``claims`` may carry a tolerated trailing suffix of inference/
        # speculation claims (P2-01a) beyond the fact-derived prefix; only the
        # prefix (one claim per mapping) is ever a materialization candidate.
        claims = ledger["claims"][: len(mappings)]
        prepared: list[_PreparedRecord] = []
        abstained: list[AbstainedClaim] = []
        for mapping, claim in zip(mappings, claims, strict=True):
            if not isinstance(claim, dict):  # guarded by mapping validation
                raise _Abstain("invalid_claim")
            try:
                prepared.append(self._prepare_one(run_id, mapping, claim))
            except _Abstain as abstention:
                abstained.append(AbstainedClaim(claim_id=mapping.claim_id, code=abstention.code))
        return tuple(prepared), tuple(abstained)

    def _prepare_one(
        self,
        run_id: str,
        mapping: ExtractionFactClaimMapping,
        claim: dict[str, Any],
    ) -> _PreparedRecord:
        if claim.get("status") != "supported":
            raise _Abstain("non_source_claim_candidate")
        self._reject_deferred_references(claim.get("persistent_references"))

        extraction_card = load_yaml(mapping.extraction_card_path)
        if not isinstance(extraction_card, dict):
            raise _Abstain("invalid_extraction_card")
        if (
            extraction_card.get("id") != mapping.extraction_card_id
            or extraction_card.get("source_card_id") != mapping.source_card_id
        ):
            raise _Abstain("extraction_snapshot_identity_mismatch")
        created_at = extraction_card.get("created_at")
        extractor = extraction_card.get("extractor_agent")
        model = extraction_card.get("model_profile")
        if not isinstance(created_at, str) or not created_at or not isinstance(extractor, str) or not extractor:
            raise _Abstain("missing_extraction_provenance")

        facts = extraction_card.get("extracted_facts")
        if not isinstance(facts, list) or mapping.fact_index >= len(facts):
            raise _Abstain("extraction_snapshot_fact_missing")
        fact = facts[mapping.fact_index]
        if not isinstance(fact, dict):
            raise _Abstain("invalid_extracted_fact")
        if (
            fact.get("text") != mapping.text
            or fact.get("evidence_id") != mapping.evidence_id
            or fact.get("locator") != mapping.locator
        ):
            raise _Abstain("extraction_snapshot_fact_mismatch")
        self._reject_deferred_references(fact.get("persistent_references"))
        if any(fact.get(field) not in (None, "") for field in _DEFERRED_REFERENCE_FIELDS):
            raise _Abstain("canonical_or_inference_candidate_deferred")

        source_meta, source_bytes = self._source_card(mapping.source_card_id, run_id)
        evidence = self._evidence_point(source_meta, mapping)
        # Bind the assertion to the source card's verbatim extracted_points[].quote,
        # not the paraphrased extraction fact/claim text (mapping.text). The claim
        # pipeline stores a paraphrase in fact.text/claim.text by design (see
        # docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md, defect
        # 1a); requiring that paraphrase to be byte-identical to the quote made
        # the exact-passage gate below fail almost universally. The evidence
        # point is already uniquely selected by evidence_id + locator, so no
        # additional text-equality check against mapping.text is needed here.
        quote = evidence.get("quote")
        if not isinstance(quote, str) or not quote:
            raise _Abstain("missing_exact_passage_quote")
        source = source_meta.get("source")
        usage = source_meta.get("usage")
        sensitivity = source_meta.get("sensitivity")
        if not isinstance(source, Mapping) or not isinstance(usage, Mapping) or not usage:
            raise _Abstain("missing_source_rights_provenance")
        if not isinstance(sensitivity, str) or not sensitivity:
            raise _Abstain("missing_source_access_scope")

        try:
            matches = self.registry.find_exact_passages(mapping.source_card_id, quote)
        except RegistryIntegrityError as exc:
            raise _Abstain("registry_integrity_rejected") from exc
        if not matches:
            raise _Abstain("unresolved_passage_binding")
        if len(matches) != 1:
            raise _Abstain("ambiguous_passage_binding")
        edition, passage = matches[0]
        try:
            self.registry.verify_source_card_binding(mapping.source_card_id, edition, source_meta)
        except RegistryIntegrityError as exc:
            raise _Abstain("registry_integrity_rejected") from exc
        allowed_use = (edition.get("metadata_extensions") or {}).get("allowed_use")
        if not isinstance(allowed_use, Mapping) or not allowed_use:
            raise _Abstain("missing_edition_rights_provenance")
        if edition.get("access_scope") != sensitivity:
            raise _Abstain("source_rights_scope_mismatch")

        qualifiers, qualifier_extensions = self._qualifiers(fact)

        # P4-1 (AC P4-A): computed once, before the assertion dict is
        # assembled, so both the rights_summary mirror and the P4-4
        # substitutability search (which reads the mirror's clearance_status)
        # are available for the SAME materialization pass that creates this
        # source_assertion -- no separate backfill sweep needed for either.
        rights_summary = compute_capture_rights_summary()
        # P4-4 fix-cycle 1 (karen review): wire the substitutability search
        # into the real materialization path. `query_terms` uses the bound
        # source_card's own title (the topic/domain signal already resolved
        # above as `source["title"]`) and the corpus is every other
        # source_card already ingested into this same run -- the same corpus
        # convention ingest_source uses.
        source_title = source.get("title") if isinstance(source, Mapping) else None
        substitutability = maybe_assess_substitutability(
            rights_summary,
            query_terms=[source_title] if source_title else [],
            corpus_paths=sorted(self.paths.run_paths(run_id).sources.glob("*.md")),
            exclude_source_id=mapping.source_card_id,
        )

        extraction_provenance = {
            "extractor": extractor,
            "provider": None,
            "model": model if isinstance(model, str) else None,
            "prompt_version": None,
            "schema_version": EXTRACTION_FACT_CLAIM_MAPPING_VERSION,
            "code_version": "assertion-materializer-v1",
            "observed_at": created_at,
        }
        assertion: dict[str, Any] = {
            "schema_version": "1.0",
            "type": "source_assertion",
            "assertion_version": 1,
            "source_edition_id": edition["source_edition_id"],
            "passage_id": passage["passage_id"],
            "assertion_text": quote,
            "assertion_text_sha256": _digest(quote),
            "qualifiers": qualifiers,
            "qualifier_extensions": qualifier_extensions,
            "extraction_provenance": extraction_provenance,
            "predecessor_assertion_id": None,
            "predecessor_assertion_version": None,
            "lifecycle_state": "eligible",
            "identity": {
                "algorithm": SOURCE_ASSERTION_IDENTITY_ALGORITHM,
                "fingerprint": "",
                "material_fields": list(SOURCE_ASSERTION_MATERIAL_FIELDS),
            },
            # P3-3: this materializer performs single-passage direct extraction
            # from one exact source-card quote -- it never synthesizes a value
            # from multiple prior assertions -- so `evidence_item_type: "other"`
            # and `judgment_basis: "unassessed"` are the accurate, honest
            # fail-closed defaults for every assertion this function produces,
            # not a guess dressed up as certainty. `extensions` is deliberately
            # excluded from SOURCE_ASSERTION_MATERIAL_FIELDS (assertion_identity.py)
            # so adding it here does not perturb the assertion_id/fingerprint of
            # any assertion materialized before this field existed. No
            # `synthesis` block is set here: this function's outputs are never
            # `derived_synthesis`.
            "extensions": {
                "evidence_taxonomy": {
                    "evidence_item_type": "other",
                    "judgment_basis": "unassessed",
                }
            },
            # P4-1 (AC P4-A): a fail-closed rights_summary mirror, computed in
            # THIS same materialization pass -- no separate backfill sweep
            # for newly-materialized source assertions. Sibling of
            # `extensions`, never nested under it (schema comment). See
            # services/rights_triage.py for why the mirror lands
            # all-"unknown" rather than the PRD's literal
            # "agent_triage_only" (link-before-assert requires a linked
            # rights_record, which does not exist at materialization time).
            # Deliberately excluded from SOURCE_ASSERTION_MATERIAL_FIELDS
            # (assertion_identity.py), same treatment as `extensions` above,
            # so it does not perturb this assertion's identity/fingerprint.
            "rights_summary": rights_summary,
            # P4-4 fix-cycle 1 (karen review): the substitutability search
            # result (never null -- maybe_assess_substitutability always
            # returns a well-formed not_searched/substitute_found/
            # no_substitute_found block), computed above in the SAME
            # materialization pass. Sibling of rights_summary/extensions/
            # synthesis, same top-level nesting depth -- the exact key
            # `rf rights inspect` reads first (cli_commands.py). Also
            # excluded from SOURCE_ASSERTION_MATERIAL_FIELDS, same treatment
            # as rights_summary above.
            "substitutability": substitutability,
        }
        assertion["identity"]["fingerprint"] = source_assertion_fingerprint(assertion)
        assertion["assertion_id"] = source_assertion_id(assertion)
        validation = self.schemas.validate(assertion, "source_assertion")
        if not validation.ok:
            raise _Abstain("invalid_source_assertion_contract")

        observation_identity = {
            "run_id": run_id,
            "extraction_card": mapping.extraction_card_path.name,
            "extraction_card_id": mapping.extraction_card_id,
            "fact_index": mapping.fact_index,
        }
        observation_id = f"obs_{_canonical_digest(observation_identity)}"
        evaluation_id = f"aev_{_digest(observation_id)}"
        audit_id = f"aud_{_digest(observation_id)}"
        persistent_references = {
            "source_edition_id": assertion["source_edition_id"],
            "passage_id": assertion["passage_id"],
            "source_assertion_id": assertion["assertion_id"],
            "assertion_version": assertion["assertion_version"],
        }
        evaluation = {
            "schema_version": "1.0",
            "type": "assertion_evaluation",
            "evaluation_id": evaluation_id,
            "assertion_id": assertion["assertion_id"],
            "assertion_version": 1,
            "evaluation_kind": "grounding",
            "verdict": "pass",
            "evaluator": {"kind": "rule", "id": "rf_assertion_materializer", "version": "1.0"},
            "evaluated_at": created_at,
            "details": {
                "mapping_contract": EXTRACTION_FACT_CLAIM_MAPPING_VERSION,
                "source_card_id": mapping.source_card_id,
                "source_key": mapping.source_card_id,
                "evidence_id": mapping.evidence_id,
                "locator": mapping.locator,
                "passage_raw_text_sha256": passage["raw_text_sha256"],
            },
        }
        if not self.schemas.validate(evaluation, "assertion_evaluation").ok:
            raise _Abstain("invalid_assertion_evaluation_contract")
        observation = {
            "schema_version": "1.0",
            "type": "assertion_observation",
            "observation_id": observation_id,
            "run_id": run_id,
            "claim_id": mapping.claim_id,
            "source_card_id": mapping.source_card_id,
            "source_key": mapping.source_card_id,
            "source_edition_id": assertion["source_edition_id"],
            "passage_id": assertion["passage_id"],
            "assertion_id": assertion["assertion_id"],
            "assertion_version": 1,
            "evaluation_id": evaluation_id,
            "extraction_card_id": mapping.extraction_card_id,
            "extraction_card_sha256": _digest(mapping.extraction_card_path.read_bytes()),
            "source_card_sha256": _digest(source_bytes),
            "fact_index": mapping.fact_index,
            "evidence_id": mapping.evidence_id,
            "locator": mapping.locator,
            "passage_raw_text_sha256": passage["raw_text_sha256"],
            "rights": {
                "access_scope": sensitivity,
                "source_card_usage_sha256": _canonical_digest(dict(usage)),
                "edition_allowed_use_sha256": _canonical_digest(dict(allowed_use)),
            },
            "extraction_provenance": extraction_provenance,
        }
        audit = {
            "schema_version": "1.0",
            "type": "assertion_materialization_audit",
            "audit_id": audit_id,
            "operation": "materialize_assertion_observation",
            "observation_id": observation_id,
            "assertion_id": assertion["assertion_id"],
            "assertion_version": 1,
            "evaluation_id": evaluation_id,
            "mapping_contract": EXTRACTION_FACT_CLAIM_MAPPING_VERSION,
            "provenance_sha256": _canonical_digest(observation),
        }
        return _PreparedRecord(
            mapping=mapping,
            persistent_references=persistent_references,
            assertion=assertion,
            evaluation=evaluation,
            observation=observation,
            audit=audit,
        )

    def _source_card(self, source_card_id: str, run_id: str) -> tuple[dict[str, Any], bytes]:
        self._require_token(source_card_id, "source_card_id")
        path = self.paths.run_paths(run_id).sources / f"{source_card_id}.md"
        if not path.is_file():
            raise _Abstain("missing_source_card")
        source_bytes = path.read_bytes()
        metadata, _body = load_md(path)
        if metadata.get("source_card_id") != source_card_id:
            raise _Abstain("source_card_identity_mismatch")
        return metadata, source_bytes

    @staticmethod
    def _evidence_point(
        source_meta: Mapping[str, Any], mapping: ExtractionFactClaimMapping
    ) -> Mapping[str, Any]:
        points = source_meta.get("extracted_points")
        if not isinstance(points, list):
            raise _Abstain("missing_source_evidence")
        matches = [
            point
            for point in points
            if isinstance(point, Mapping)
            and point.get("evidence_id") == mapping.evidence_id
            and point.get("locator") == mapping.locator
        ]
        if len(matches) != 1:
            raise _Abstain("ambiguous_or_forged_source_evidence")
        return matches[0]

    @staticmethod
    def _qualifiers(fact: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        raw_qualifiers = fact.get("qualifiers") or {}
        raw_extensions = fact.get("qualifier_extensions") or {}
        if not isinstance(raw_qualifiers, Mapping) or not isinstance(raw_extensions, Mapping):
            raise _Abstain("invalid_qualifiers")
        qualifiers = {key: value for key, value in raw_qualifiers.items() if key in _KNOWN_QUALIFIERS}
        extensions = {key: value for key, value in raw_qualifiers.items() if key not in _KNOWN_QUALIFIERS}
        for key, value in raw_extensions.items():
            if key in extensions and extensions[key] != value:
                raise _Abstain("conflicting_qualifier_extension")
            extensions[key] = value
        return qualifiers, extensions

    @staticmethod
    def _reject_deferred_references(value: object) -> None:
        if value is None:
            return
        if not isinstance(value, Mapping):
            raise _Abstain("invalid_persistent_references")
        if any(value.get(field) not in (None, "") for field in _DEFERRED_REFERENCE_FIELDS):
            raise _Abstain("canonical_or_inference_candidate_deferred")

    def _preflight_existing(self, prepared: Sequence[_PreparedRecord]) -> None:
        for item in prepared:
            assertion_path = self._assertion_path(item.assertion["assertion_id"])
            if assertion_path.exists():
                existing = self._load_mapping(assertion_path)
                if not self.schemas.validate(existing, "source_assertion").ok:
                    raise MaterializationConflict("existing_source_assertion_invalid")
                for key in (*SOURCE_ASSERTION_MATERIAL_FIELDS, "assertion_id", "assertion_version", "identity"):
                    if existing.get(key) != item.assertion.get(key):
                        raise MaterializationConflict("conflicting_source_assertion")
            for record, path in (
                (item.observation, self._observation_path(item.observation["observation_id"])),
                (item.evaluation, self._evaluation_path(item.evaluation["evaluation_id"])),
                (item.audit, self._audit_path(item.audit["audit_id"])),
            ):
                if path.exists() and self._load_mapping(path) != record:
                    raise MaterializationConflict("conflicting_deterministic_record")

    def _verify_published_records(self, prepared: Sequence[_PreparedRecord]) -> None:
        """Make a corrupt published pointer fail closed instead of silently reusing it."""

        for item in prepared:
            assertion_path = self._assertion_path(item.assertion["assertion_id"])
            if not assertion_path.exists():
                raise MaterializationConflict("published_assertion_missing")
            existing_assertion = self._load_mapping(assertion_path)
            if not self.schemas.validate(existing_assertion, "source_assertion").ok:
                raise MaterializationConflict("existing_source_assertion_invalid")
            for key in (*SOURCE_ASSERTION_MATERIAL_FIELDS, "assertion_id", "assertion_version", "identity"):
                if existing_assertion.get(key) != item.assertion.get(key):
                    raise MaterializationConflict("conflicting_source_assertion")
            for record, path in (
                (item.observation, self._observation_path(item.observation["observation_id"])),
                (item.evaluation, self._evaluation_path(item.evaluation["evaluation_id"])),
                (item.audit, self._audit_path(item.audit["audit_id"])),
            ):
                if not path.exists() or self._load_mapping(path) != record:
                    raise MaterializationConflict("conflicting_deterministic_record")

    def _write_immutable_assertion(self, assertion: dict[str, Any]) -> None:
        path = self._assertion_path(assertion["assertion_id"])
        if path.exists():
            return
        _atomic_dump(self._enforce_synthesis_attestation_ceiling(assertion), path)

    @staticmethod
    def _enforce_synthesis_attestation_ceiling(assertion: Mapping[str, Any]) -> dict[str, Any]:
        """Defense-in-depth write ceiling: this is the LAST gate before a
        source_assertion is persisted to the immutable ledger, and it is the
        only place in this module that governs ``synthesis.attestation.status``.

        No write path in this repository is authorized to mint
        ``attestation.status == "attested"`` today -- ``_prepare_one`` above
        never emits a ``synthesis`` block at all (this materializer performs
        single-passage direct extraction, never synthesis), so this function
        is a no-op for every assertion this module currently produces. It
        exists so that if a *future* write path is added (here or in a
        subclass/caller) that does construct a ``synthesis`` block without
        updating this ceiling, that future code still cannot silently produce
        an "attested" record: any ``synthesis.attestation.status`` present is
        forcibly reset to ``"candidate"`` immediately before the bytes hit
        disk, regardless of what upstream code set it to.
        """

        result = copy.deepcopy(dict(assertion))
        synthesis = result.get("synthesis")
        if isinstance(synthesis, Mapping):
            synthesis = dict(synthesis)
            attestation = synthesis.get("attestation")
            attestation = dict(attestation) if isinstance(attestation, Mapping) else {}
            attestation["status"] = "candidate"
            synthesis["attestation"] = attestation
            result["synthesis"] = synthesis
        return result

    @staticmethod
    def _write_immutable(record: Mapping[str, Any], path: Path) -> None:
        if path.exists():
            if load_yaml(path) != dict(record):
                raise MaterializationConflict("conflicting_deterministic_record")
            return
        _atomic_dump(record, path)

    def _apply_claim_references(
        self, run_id: str, ledger: dict[str, Any], prepared: Sequence[_PreparedRecord]
    ) -> None:
        updated = copy.deepcopy(ledger)
        claims = updated.get("claims")
        if not isinstance(claims, list):
            raise MaterializationConflict("invalid_claim_ledger")
        changed = False
        for item in prepared:
            claim = claims[int(item.mapping.claim_id.split("_")[1]) - 1]
            if not isinstance(claim, dict) or claim.get("claim_id") != item.mapping.claim_id:
                raise MaterializationConflict("claim_mapping_changed_before_publication")
            existing = claim.get("persistent_references")
            self._reject_deferred_references(existing)
            if existing is None:
                claim["persistent_references"] = item.persistent_references
                changed = True
            elif not isinstance(existing, Mapping) or any(
                existing.get(key) != value for key, value in item.persistent_references.items()
            ):
                raise MaterializationConflict("claim_persistent_reference_conflict")
        if changed:
            _atomic_dump(updated, self.paths.run_paths(run_id).claim_ledger)

    def _generation(self, run_id: str, prepared: Sequence[_PreparedRecord]) -> dict[str, Any]:
        records = [
            {
                "claim_id": item.mapping.claim_id,
                "assertion_id": item.assertion["assertion_id"],
                "assertion_version": 1,
                "evaluation_id": item.evaluation["evaluation_id"],
                "observation_id": item.observation["observation_id"],
                "audit_id": item.audit["audit_id"],
            }
            for item in prepared
        ]
        generation_id = f"mat_{_canonical_digest({'run_id': run_id, 'records': records})}"
        return {
            "schema_version": "1.0",
            "type": "assertion_materialization_generation",
            "generation_id": generation_id,
            "run_id": run_id,
            "mapping_contract": EXTRACTION_FACT_CLAIM_MAPPING_VERSION,
            "records": records,
        }

    def _load_published_generation(self, run_id: str) -> dict[str, Any]:
        pointer = self._load_mapping(self._published_pointer_path(run_id))
        generation_id = self._require_id(
            pointer.get("generation_id"), _GENERATION_ID_RE, "generation_id"
        )
        generation = self._load_mapping(self._generation_path(run_id, generation_id))
        if generation.get("generation_id") != generation_id or generation.get("run_id") != run_id:
            raise MaterializationConflict("materialization_pointer_substitution")
        return generation

    def _result(
        self,
        run_id: str,
        status: str,
        prepared: Sequence[_PreparedRecord],
        generation_id: str,
        abstained: Sequence[AbstainedClaim] = (),
    ) -> MaterializationResult:
        return MaterializationResult(
            run_id=run_id,
            status=status,
            assertion_ids=tuple(item.assertion["assertion_id"] for item in prepared),
            claim_ids=tuple(item.mapping.claim_id for item in prepared),
            generation_id=generation_id,
            abstained_claims=tuple(abstained),
        )

    def _assertion_path(self, assertion_id: str) -> Path:
        self._require_id(assertion_id, _ASSERTION_ID_RE, "assertion_id")
        return self.root / "assertions" / f"{assertion_id}.yaml"

    def _observation_path(self, observation_id: str) -> Path:
        self._require_id(observation_id, _OBSERVATION_ID_RE, "observation_id")
        return self.root / "observations" / f"{observation_id}.yaml"

    def _evaluation_path(self, evaluation_id: str) -> Path:
        self._require_id(evaluation_id, _EVALUATION_ID_RE, "evaluation_id")
        return self.root / "evaluations" / f"{evaluation_id}.yaml"

    def _audit_path(self, audit_id: str) -> Path:
        self._require_id(audit_id, _AUDIT_ID_RE, "audit_id")
        return self.root / "audits" / f"{audit_id}.yaml"

    def _run_root(self, run_id: str) -> Path:
        self._require_token(run_id, "run_id")
        return self.root / "materializations" / "runs" / _digest(run_id)

    def _generation_path(self, run_id: str, generation_id: str) -> Path:
        self._require_id(generation_id, _GENERATION_ID_RE, "generation_id")
        return self._run_root(run_id) / "generations" / f"{generation_id}.yaml"

    def _published_pointer_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "published.yaml"

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, Any]:
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise MaterializationConflict("persisted_materialization_record_invalid")
        return data

    @staticmethod
    def _require_token(value: object, label: str) -> str:
        if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
            raise _Abstain(f"invalid_{label}")
        return value

    @staticmethod
    def _require_id(value: object, pattern: re.Pattern[str], label: str) -> str:
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise MaterializationConflict(f"invalid_{label}")
        return value


def materialize_run(
    run_id: str,
    *,
    workspace_id: str,
    paths: FoundryPaths | None = None,
) -> MaterializationResult:
    """Convenience entry point for the P3 assertion-only materializer."""

    return AssertionMaterializer(workspace_id=workspace_id, paths=paths).materialize_run(run_id)


# ---------------------------------------------------------------------------
# F11 gate-reversal contract (research-provenance-continuity, P4/RPC-4.2-4.4):
# the SOLE second write path for claim_ledger.persistent_references -- never a
# loosening of _reject_deferred_references/_DEFERRED_REFERENCE_FIELDS above,
# which stay exactly as strict as before this seam existed for every existing
# call site (_prepare_one, _apply_claim_references).
#
# T4-1 fix-cycle 2 (gpt-5.6-terra audit, contract freeze doc §17.1/§17.2/§17.7/
# §17.8): the ORIGINAL round-1 shape of this seam (public `apply_*_reference`
# functions accepting an arbitrary target id + a caller-supplied
# `recheck() -> bool` callback) let an external caller commit a reference to a
# target that never existed, in a run it does not own, by simply passing
# `lambda: True`. This module now exposes NO public entry point here at all:
# `_commit_persistent_reference` (below) is private, reachable ONLY from
# `AssertionInferenceMaterializer.materialize_inference` /
# `CanonicalClaimMaterializer.publish_canonical_claim`, and independently
# (re)enforces every one of contract §17.1's six preconditions itself, under
# the per-run lock, from freshly-reloaded on-disk state -- never merely
# trusting a boolean the caller computed. The `_TargetKindSpec` each caller
# supplies closes over that caller's OWN validated path/schema conventions
# (record_path, manifest_path, digest formula, transitive-support shape) --
# it carries no security decision itself, only kind-specific arithmetic
# (T4-4: the ONE shared locked target-validation routine both target kinds
# use, via `_recheck_transitive_support` below, eliminating the inference
# path's prior generic `partial_write_rejected` collapse and the drift
# between the two services' typed outcomes).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _TargetKindSpec:
    """Kind-specific arithmetic the shared, locked commit routine needs.

    Every field is a pure function or a frozen storage-path convention closed
    over the CALLING materializer's own already-validated `self.root` --
    never a boolean "trust me" callback. The shared routine
    (`_commit_persistent_reference_locked`) performs every security-relevant
    check itself (existence, ownership, lifecycle, capability flags,
    generation CAS, commit-proof recompute) using these only to compute
    kind-specific values (a version_digest formula, a storage path) it has no
    business hard-coding for both `inference_record` and `canonical_claim`
    shapes in one place.
    """

    kind: str  # "inference_record" | "canonical_claim"
    #: SOL-33: the ``SchemaRegistry`` schema name to re-validate the
    #: freshly-reloaded target record against at commit time -- see
    #: ``_commit_persistent_reference_locked``'s Precondition 1.
    schema_name: str  # "inference_record" | "canonical_claim"
    id_field: str  # "inference_id" | "canonical_claim_id"
    version_field: str  # "inference_version" | "canonical_claim_version"
    manifest_type: str
    conflict_cls: type[MaterializationError]
    interrupted_cls: type[RuntimeError]
    record_path: Callable[[str, int], Path]
    manifest_path: Callable[[], Path]
    recompute_version_digest: Callable[[Mapping[str, Any]], str]
    is_state_active: Callable[[Mapping[str, Any]], bool]
    source_assertion_refs_of: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]]
    inference_refs_of: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]]
    support_refs_digest_of: Callable[[Mapping[str, Any]], str]
    requires_canonical_claims_capability: bool


def compute_commit_proof_digest(
    *,
    claim_id: str,
    row_sources: Sequence[Mapping[str, Any]],
    row_conclusion_text: str,
    target_kind: str,
    target_id: str,
    target_version: int,
    target_version_digest: str,
    support_refs_digest: str,
) -> str:
    """Contract §17.8 item 2's exact seven-field commit-proof digest.

    Owned by this module per contract freeze doc §17.9 design note N3 ("the
    SEPARATE claim_ledger.persistent_references SECOND write path ... and
    §17.8's commit-proof digest ... is owned by services/assertion_materialization.py").
    Re-exported from ``assertion_inference`` for backward compatibility (it
    previously lived there); ``canonical_claim_materialization`` imports it
    from here directly.
    """

    payload = {
        "claim_id": claim_id,
        "row_material": {
            "sources": [dict(source) for source in row_sources],
            "conclusion_text": row_conclusion_text,
        },
        "target_kind": target_kind,
        "target_id": target_id,
        "target_version": target_version,
        "target_version_digest": target_version_digest,
        "support_refs_digest": support_refs_digest,
    }
    return _canonical_digest(payload)


def _record_fingerprint(record_id: str) -> str:
    """The record's stable identity fingerprint: its own id hash, no prefix."""

    _, _, tail = record_id.partition("_")
    return tail or record_id


def _lookup_workspace_record(
    root: Path, subdir: str, record_id: object, id_pattern: re.Pattern[str]
) -> dict[str, Any] | None:
    if not isinstance(record_id, str) or not id_pattern.fullmatch(record_id):
        return None
    path = root / subdir / f"{record_id}.yaml"
    if not path.is_file():
        return None
    data = load_yaml(path)
    return data if isinstance(data, dict) else None


def _recheck_transitive_support(
    *,
    root: Path,
    source_assertion_refs: Sequence[Mapping[str, Any]],
    inference_refs: Sequence[Mapping[str, Any]] = (),
    stale_inference_ids: frozenset[str] = frozenset(),
) -> str | None:
    """T4-4: the ONE shared transitive support-lifecycle recheck both target
    kinds use (contract §17.1 item 6) -- canonical -> its inferences -> their
    OWN source_assertion_refs, never just the target's immediate refs.
    Returns a typed skip code, or ``None`` if every transitively-named source
    assertion is still `lifecycle_state: eligible` and every transitively-
    named inference is still `status: active`.

    F18 (RPC-6.G / N7): an inference's raw, on-disk ``status`` never flips to
    stale -- P6 records that as a durable effect receipt instead
    (``assertion_impact.collect_stale_object_ids``), never a record mutation.
    ``stale_inference_ids`` is that lane's effective-status verdict, computed
    ONCE per commit attempt by the caller (never per-ref here) and belt-and-
    suspenders alongside the raw ``status`` check: either one failing is
    ``stale_support``.

    F19 (RPC-6.G validator, Karen K-1, HIGH): a directly-cited source
    assertion has the SAME blindness -- its raw ``assertions/<id>.yaml``
    record's ``lifecycle_state`` never flips to ``blocked`` either; the
    authoritative boundary lives in the separate
    ``lifecycle_policy/<assertion_id>.yaml`` artifact (see
    ``AssertionImpactReconciler.reconcile``). Every ref is additionally
    checked against ``assertion_impact.effective_source_assertion_lifecycle_state``
    -- a policy-blocked assertion, or one whose policy artifact is present
    but fails to validate (K-2: fail closed, never silently un-blocked), is
    ``stale_support`` too.
    """

    # Lazy import: assertion_impact.py imports `_referenced_target_ids` from
    # this module at module scope, so a module-level import here would be
    # circular (same reason the caller below lazily imports
    # `collect_stale_object_ids`).
    from .assertion_impact import effective_source_assertion_lifecycle_state

    for ref in source_assertion_refs:
        assertion_id = ref.get("assertion_id") if isinstance(ref, Mapping) else None
        assertion_version = ref.get("assertion_version") if isinstance(ref, Mapping) else None
        assertion = _lookup_workspace_record(root, "assertions", assertion_id, _ASSERTION_ID_RE)
        if (
            assertion is None
            or assertion.get("assertion_version") != assertion_version
            or assertion.get("lifecycle_state") != "eligible"
        ):
            return "stale_support"
        if (
            isinstance(assertion_id, str)
            and effective_source_assertion_lifecycle_state(root=root, assertion_id=assertion_id) != "eligible"
        ):
            return "stale_support"
    for ref in inference_refs:
        inference_id = ref.get("inference_id") if isinstance(ref, Mapping) else None
        inference_version = ref.get("inference_version") if isinstance(ref, Mapping) else None
        inference = _lookup_workspace_record(root, "inferences", inference_id, _INFERENCE_ID_RE)
        if (
            inference is None
            or inference.get("inference_version") != inference_version
            or inference.get("status") != "active"
            or (isinstance(inference_id, str) and inference_id in stale_inference_ids)
        ):
            return "stale_support"
        nested_refs = inference.get("source_assertion_refs")
        nested_code = _recheck_transitive_support(
            root=root,
            source_assertion_refs=nested_refs if isinstance(nested_refs, list) else [],
            stale_inference_ids=stale_inference_ids,
        )
        if nested_code:
            return nested_code
    return None


def _load_manifest_entries(manifest_path: Path) -> dict[tuple[Any, Any], dict[str, Any]]:
    if not manifest_path.exists():
        return {}
    manifest = load_yaml(manifest_path)
    entries = manifest.get("entries") if isinstance(manifest, Mapping) else None
    result: dict[tuple[Any, Any], dict[str, Any]] = {}
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, Mapping):
                result[(entry.get("record_id"), entry.get("version"))] = dict(entry)
    return result


def _ensure_target_manifest_entry(
    manifest_path: Path,
    *,
    manifest_type: str,
    record_kind: str,
    record_id: str,
    version: int,
    version_digest: str,
) -> None:
    """Contract §17.7a: write the generation-manifest entry.

    T4-3 fix: this is now called ONLY from `_commit_persistent_reference_locked`,
    immediately before the claim-ledger reference write, under the SAME
    per-run lock -- never at record-promotion time (the prior bug: a
    promotion-time write left a manifest entry recovery trusted even when no
    claim-ledger commit had ever been attempted for it).
    """

    manifest = load_yaml(manifest_path) if manifest_path.exists() else None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("entries"), list):
        manifest = {"schema_version": 1, "type": manifest_type, "entries": []}
    entries = manifest["entries"]
    key = (record_id, version)
    for entry in entries:
        if (entry.get("record_id"), entry.get("version")) == key:
            return
    entries.append(
        {
            "record_kind": record_kind,
            "record_id": record_id,
            "version": version,
            "version_digest": version_digest,
            "fingerprint": _record_fingerprint(record_id),
        }
    )
    _atomic_dump(manifest, manifest_path)


def _referenced_target_ids(
    paths: FoundryPaths, *, workspace_id: str, record_kind: str
) -> set[tuple[str, int]]:
    """T4-3: the recovery authority is the CURRENT claim-ledger generation
    pointer, across every run this workspace owns -- never a private
    per-record-kind manifest file consulted in isolation. A `(record_id,
    version)` pair is authoritative/citable iff it is reachable from some
    run's CURRENT `.claim_ledger_published.yaml` generation snapshot; a
    promoted record not reachable this way is quarantine-eligible on
    recovery, even if a private manifest file happens to also name it.
    """

    referenced: set[tuple[str, int]] = set()
    runs_root = paths.runs
    if not runs_root.is_dir():
        return referenced
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        run_paths = paths.run_paths(run_id)
        if not run_paths.run_yaml.exists():
            continue
        run_doc = load_yaml(run_paths.run_yaml)
        if not isinstance(run_doc, Mapping) or run_doc.get("workspace_id") != workspace_id:
            continue
        pointer_path = run_paths.claims / ".claim_ledger_published.yaml"
        if not pointer_path.exists():
            continue
        pointer = load_yaml(pointer_path)
        generation_id = pointer.get("generation_id") if isinstance(pointer, Mapping) else None
        if not isinstance(generation_id, str):
            continue
        generation_path = run_paths.claims / ".claim_ledger_generations" / f"{generation_id}.yaml"
        if not generation_path.exists():
            continue
        generation = load_yaml(generation_path)
        snapshot = generation.get("persistent_references_snapshot") if isinstance(generation, Mapping) else None
        if not isinstance(snapshot, list):
            continue
        for row in snapshot:
            manifest_entries = row.get("manifest_entries") if isinstance(row, Mapping) else None
            if not isinstance(manifest_entries, list):
                continue
            for entry in manifest_entries:
                if not isinstance(entry, Mapping) or entry.get("record_kind") != record_kind:
                    continue
                record_id = entry.get("record_id")
                version = entry.get("version")
                if isinstance(record_id, str) and isinstance(version, int):
                    referenced.add((record_id, version))
    return referenced


def _claim_ledger_generation_snapshot(root: Path, ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The claim rows this generation's CAS/commit-proof covers (§17.7 step 4).

    T4-3: each row's snapshot entry now embeds `manifest_entries` -- the
    §17.7a manifest-entry-shaped block(s) for whichever inference_record/
    canonical_claim this row references, read from the per-kind manifest
    files under ``root`` -- so the claim-ledger generation itself is what
    recovery (`_referenced_target_ids`) consults as the SOLE authority,
    never a private per-record-kind manifest in isolation.
    """

    inference_manifest = _load_manifest_entries(root / "inferences" / ".generation_manifest.yaml")
    canonical_manifest = _load_manifest_entries(root / "canonical_claims" / ".generation_manifest.yaml")
    snapshot: list[dict[str, Any]] = []
    for claim in ledger.get("claims") or []:
        if not isinstance(claim, Mapping):
            continue
        refs = claim.get("persistent_references")
        if not isinstance(refs, Mapping) or not (refs.get("inference_id") or refs.get("canonical_claim_id")):
            continue
        manifest_entries: list[dict[str, Any]] = []
        inference_id = refs.get("inference_id")
        if isinstance(inference_id, str):
            entry = inference_manifest.get((inference_id, refs.get("inference_version")))
            if entry is not None:
                manifest_entries.append(entry)
        canonical_claim_id = refs.get("canonical_claim_id")
        if isinstance(canonical_claim_id, str):
            entry = canonical_manifest.get((canonical_claim_id, refs.get("canonical_claim_version")))
            if entry is not None:
                manifest_entries.append(entry)
        snapshot.append(
            {
                "claim_id": claim.get("claim_id"),
                "persistent_references": dict(refs),
                "manifest_entries": manifest_entries,
            }
        )
    return snapshot


def _publish_claim_ledger_generation(
    paths: FoundryPaths, run_id: str, ledger: Mapping[str, Any], commit_proof_digest: str, *, root: Path
) -> str:
    """Contract §17.7 step 4: content-addressed generation pointer + snapshot.

    Idempotent: recomputing over identical `persistent_references` content
    reproduces the same ``generation_id`` and is a no-op re-publish, never a
    spurious "change" (the same reason ``AssertionCatalog.rebuild()``'s own
    ``catalog_generation_id`` is content-addressed, not a counter).
    """

    run_paths = paths.run_paths(run_id)
    snapshot = _claim_ledger_generation_snapshot(root, ledger)
    generation_id = f"clg_{_canonical_digest({'run_id': run_id, 'persistent_references_snapshot': snapshot})}"
    generations_dir = run_paths.claims / ".claim_ledger_generations"
    generation_path = generations_dir / f"{generation_id}.yaml"
    if not generation_path.exists():
        _atomic_dump(
            {
                "schema_version": "1.0",
                "type": "claim_ledger_generation",
                "run_id": run_id,
                "generation_id": generation_id,
                "persistent_references_snapshot": snapshot,
                "commit_proof_digest": commit_proof_digest,
            },
            generation_path,
        )
    pointer_path = run_paths.claims / ".claim_ledger_published.yaml"
    _atomic_dump(
        {
            "schema_version": 1,
            "type": "claim_ledger_generation_pointer",
            "run_id": run_id,
            "generation_id": generation_id,
        },
        pointer_path,
    )
    return generation_id


def _read_claim_ledger_generation_pointer(paths: FoundryPaths, run_id: str) -> str | None:
    """T4-2: the expected generation, captured by the caller BEFORE the lock
    (at resolution time) so the locked commit can CAS against it below."""

    pointer_path = paths.run_paths(run_id).claims / ".claim_ledger_published.yaml"
    if not pointer_path.exists():
        return None
    pointer = load_yaml(pointer_path)
    generation_id = pointer.get("generation_id") if isinstance(pointer, Mapping) else None
    return generation_id if isinstance(generation_id, str) else None


def _commit_persistent_reference(
    *,
    paths: FoundryPaths,
    run_id: str,
    claim_id: str,
    caller_workspace_id: str,
    target: _TargetKindSpec,
    target_id: str,
    target_version: int,
    expected_generation_id: str | None,
    caller_commit_proof_digest: str,
    _interrupt_after_manifest: bool = False,
    _interrupt_after_ledger: bool = False,
) -> str:
    """The SOLE, private, lock-serialized entry point for a
    ``claim_ledger.persistent_references`` write (F11 second write path,
    T4-1 fix-cycle 2). Reachable ONLY from
    ``AssertionInferenceMaterializer.materialize_inference`` /
    ``CanonicalClaimMaterializer.publish_canonical_claim`` -- never public,
    never satisfiable by a caller-controlled boolean. See
    :func:`_commit_persistent_reference_locked` for the six-precondition
    enforcement this performs under the per-run lock.
    """

    run_paths = paths.run_paths(run_id)
    run_paths.claims.mkdir(parents=True, exist_ok=True)
    lock_path = run_paths.claims / ".claim_ledger.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return _commit_persistent_reference_locked(
            paths=paths,
            run_id=run_id,
            claim_id=claim_id,
            caller_workspace_id=caller_workspace_id,
            target=target,
            target_id=target_id,
            target_version=target_version,
            expected_generation_id=expected_generation_id,
            caller_commit_proof_digest=caller_commit_proof_digest,
            _interrupt_after_manifest=_interrupt_after_manifest,
            _interrupt_after_ledger=_interrupt_after_ledger,
        )
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _commit_persistent_reference_locked(
    *,
    paths: FoundryPaths,
    run_id: str,
    claim_id: str,
    caller_workspace_id: str,
    target: _TargetKindSpec,
    target_id: str,
    target_version: int,
    expected_generation_id: str | None,
    caller_commit_proof_digest: str,
    _interrupt_after_manifest: bool,
    _interrupt_after_ledger: bool,
) -> str:
    """Independently (re)enforces EVERY one of contract §17.1's six
    preconditions, under the per-run lock, from freshly-reloaded on-disk
    state -- T4-1's exact fix (no precondition is delegated to the caller).
    """

    conflict_cls = target.conflict_cls
    run_paths = paths.run_paths(run_id)

    # Precondition 2/SOL-14(a): run ownership derives from run.yaml's OWN
    # workspace_id, never the caller's resolved workspace alone.
    if not run_paths.run.exists() or not run_paths.claim_ledger.exists():
        raise conflict_cls("missing_run_or_claim_ledger")
    run_doc = load_yaml(run_paths.run_yaml) if run_paths.run_yaml.exists() else None
    if not isinstance(run_doc, Mapping) or run_doc.get("workspace_id") != caller_workspace_id:
        raise conflict_cls("run_mapping_revoked")

    ledger = load_yaml(run_paths.claim_ledger)
    if not isinstance(ledger, dict) or not isinstance(ledger.get("claims"), list):
        raise conflict_cls("invalid_claim_ledger")
    claim = next(
        (item for item in ledger["claims"] if isinstance(item, dict) and item.get("claim_id") == claim_id),
        None,
    )
    if claim is None:
        raise conflict_cls("claim_mapping_changed_before_publication")

    root = AssertionRegistry(workspace_id=caller_workspace_id, paths=paths).root

    # Precondition 5: no re-triggering an already-satisfied reference.
    existing = claim.get("persistent_references")
    existing = dict(existing) if isinstance(existing, Mapping) else {}
    existing_id = existing.get(target.id_field)
    existing_version = existing.get(target.version_field)
    if existing_id is not None or existing_version is not None:
        if existing_id == target_id and existing_version == target_version:
            # Idempotent replay (§17.1 item 5): re-publish the generation
            # pointer in case a prior attempt crashed between the ledger
            # write and the pointer publish -- never a silent overwrite.
            return _publish_claim_ledger_generation(
                paths, run_id, ledger, caller_commit_proof_digest, root=root
            )
        raise conflict_cls("replay_conflict")

    # Precondition 1: record-before-reference -- the target MUST already
    # exist, on disk, at its frozen canonical content-addressed path. T4-1's
    # exact repro (an arbitrary, never-materialized id) is rejected here.
    record_path = target.record_path(target_id, target_version)
    if not record_path.is_file():
        raise conflict_cls("partial_write_rejected")
    record = load_yaml(record_path)
    if not isinstance(record, dict):
        raise conflict_cls("partial_write_rejected")

    # SOL-33: contract §17.1 precondition 1 requires the target to be FULLY
    # schema-valid at commit time, not merely present-and-dict-shaped.
    # Initial creation validates the kind-specific schema once
    # (assertion_inference.py / canonical_claim_materialization.py), but a
    # direct on-disk mutation of a field the version_digest formula does NOT
    # cover (e.g. `type`/`schema_version`) is self-consistent under the
    # digest recompute below in isolation -- it would otherwise be sealed
    # into the claim ledger as an authoritative reference the first time a
    # (possibly different) claim commits against this exact record. Re-run
    # here, against the SAME freshly-reloaded record every other
    # precondition below already trusts, independently of whatever the
    # caller's own `_promote` may or may not have already checked.
    schemas = SchemaRegistry(schemas_dir=paths.schemas)
    if not schemas.validate(record, target.schema_name).ok:
        raise conflict_cls("partial_write_rejected")

    # Precondition 3/6 (T4-4): the target's own state, and its recomputed
    # version_digest -- never trusting the record's own stored digest field
    # in isolation (§17.7a reader rule).
    if not target.is_state_active(record):
        raise conflict_cls("stale_support")
    recomputed_digest = target.recompute_version_digest(record)
    existing_manifest_entry = _load_manifest_entries(target.manifest_path()).get((target_id, target_version))
    if existing_manifest_entry is not None and existing_manifest_entry.get("version_digest") != recomputed_digest:
        # §17.7a: a record REACHABLE FROM a generation manifest must match
        # its manifest entry -- a mismatch here is tamper-evidence, fail closed.
        raise conflict_cls("partial_write_rejected")

    # Precondition 6 (T4-4): transitive support-assertion/inference lifecycle,
    # rechecked NOW -- canonical -> its inferences -> their OWN
    # source_assertion_refs, one shared routine for both target kinds.
    # F18: P6's mark_stale effect-receipt verdict is computed ONCE per commit
    # attempt (never per-ref) -- lazy import to avoid a circular import with
    # assertion_impact.py, which imports `_referenced_target_ids` from this
    # module at module scope.
    from .assertion_impact import ImpactOperationError, collect_stale_object_ids

    # K-2 (Karen Wave-3 gate, MEDIUM): `strict=True` here is the COMMIT-path
    # posture -- a present-but-invalid impact-operations receipt anywhere in
    # this workspace is governance-critical corruption, so this commit fails
    # closed rather than risk silently treating the exact object it concerns
    # as "not stale". The P5 catalog's read-path call stays `strict=False`
    # (degrade-per-record with a logged warning).
    try:
        stale_object_ids = collect_stale_object_ids(paths=paths, workspace_id=caller_workspace_id, strict=True)
    except ImpactOperationError:
        raise conflict_cls("stale_support") from None
    stale_code = _recheck_transitive_support(
        root=root,
        source_assertion_refs=target.source_assertion_refs_of(record),
        inference_refs=target.inference_refs_of(record),
        stale_inference_ids=stale_object_ids.get("inference", frozenset()),
    )
    if stale_code:
        raise conflict_cls(stale_code)

    # Precondition 6: resolved capability flags, rechecked NOW, not merely at
    # initial resolution.
    capabilities = FoundryConfig(paths=paths).assertion_ledger_capabilities()
    if not capabilities.ledger_write_allowed:
        raise conflict_cls("ledger_write_disabled")
    if target.requires_canonical_claims_capability and not capabilities.canonical_claims_allowed:
        raise conflict_cls("canonical_claims_disabled")

    # T4-2: generation CAS -- re-read the CURRENT pointer under the lock and
    # compare to what the caller's resolution was originally prepared
    # against; a mismatch means someone else committed to this row's
    # generation since the caller last read it.
    pointer_path = run_paths.claims / ".claim_ledger_published.yaml"
    current_pointer = load_yaml(pointer_path) if pointer_path.exists() else None
    current_generation_id = current_pointer.get("generation_id") if isinstance(current_pointer, Mapping) else None
    if current_generation_id != expected_generation_id:
        raise conflict_cls("partial_write_rejected")

    # T4-2/§17.8: RECOMPUTE the seven-field commit proof from this locked,
    # freshly-reloaded state and compare to the caller's own computed value
    # -- never merely persist a caller-supplied digest unchecked.
    # `support_refs_digest_of` is kind-specific (contract §17.8's ONLY worked
    # vector uses an inference_record target's bare source_assertion_refs
    # list; canonical claims bind BOTH support kinds together, a documented
    # design decision) -- both formulas are owned by the CALLING module that
    # already mints them at resolution time, never re-invented here.
    support_refs_digest = target.support_refs_digest_of(record)
    recomputed_commit_proof = compute_commit_proof_digest(
        claim_id=claim_id,
        row_sources=claim.get("sources") or [],
        row_conclusion_text=str(claim.get("text") or ""),
        target_kind=target.kind,
        target_id=target_id,
        target_version=target_version,
        target_version_digest=recomputed_digest,
        support_refs_digest=support_refs_digest,
    )
    if recomputed_commit_proof != caller_commit_proof_digest:
        raise conflict_cls("partial_write_rejected")

    # All six preconditions independently hold. T4-3: the manifest entry is
    # written HERE, under this SAME lock, immediately before the claim-ledger
    # reference -- never earlier at promotion time (the prior bug: a crash
    # after a promotion-time manifest write but before ANY ledger commit left
    # a manifest entry recovery trusted with no reference ever written).
    _ensure_target_manifest_entry(
        target.manifest_path(),
        manifest_type=target.manifest_type,
        record_kind=target.kind,
        record_id=target_id,
        version=target_version,
        version_digest=recomputed_digest,
    )
    if _interrupt_after_manifest:
        raise target.interrupted_cls("interrupted after manifest entry, before claim ledger write")

    existing[target.id_field] = target_id
    existing[target.version_field] = target_version
    claim["persistent_references"] = existing
    _atomic_dump(ledger, run_paths.claim_ledger)
    if _interrupt_after_ledger:
        raise target.interrupted_cls("interrupted after claim ledger write, before pointer publish")

    return _publish_claim_ledger_generation(paths, run_id, ledger, recomputed_commit_proof, root=root)


__all__ = [
    "AbstainedClaim",
    "AssertionMaterializer",
    "CanonicalClaimReferenceConflict",
    "InferenceReferenceConflict",
    "MaterializationConflict",
    "MaterializationError",
    "MaterializationInterrupted",
    "MaterializationResult",
    "ReplayResult",
    "compute_commit_proof_digest",
    "materialize_run",
]
