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
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
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

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_ASSERTION_ID_RE = re.compile(r"^ast_[a-f0-9]{64}$")
_OBSERVATION_ID_RE = re.compile(r"^obs_[a-f0-9]{64}$")
_EVALUATION_ID_RE = re.compile(r"^aev_[a-f0-9]{64}$")
_AUDIT_ID_RE = re.compile(r"^aud_[a-f0-9]{64}$")
_GENERATION_ID_RE = re.compile(r"^mat_[a-f0-9]{64}$")
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


class _Abstain(MaterializationError):
    """Internal typed result for a candidate that cannot be safely linked."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MaterializationResult:
    """One run's immutable P3 materialization outcome."""

    run_id: str
    status: str
    assertion_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    generation_id: str | None = None
    abstention_code: str | None = None


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
            prepared = self._prepare(run_id, ledger)
        except _Abstain as abstention:
            return MaterializationResult(
                run_id=run_id,
                status="abstained",
                abstention_code=abstention.code,
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
            return self._result(run_id, "reused", prepared, generation["generation_id"])

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
        return self._result(run_id, "materialized", prepared, generation["generation_id"])

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

    def _prepare(self, run_id: str, ledger: dict[str, Any]) -> tuple[_PreparedRecord, ...]:
        try:
            mappings = validate_extraction_fact_claim_mappings(run_id, ledger, paths=self.paths)
        except ValueError as exc:
            raise _Abstain(str(exc)) from exc
        if not mappings:
            raise _Abstain("empty_fact_claim_mapping")

        claims = ledger["claims"]
        prepared: list[_PreparedRecord] = []
        for mapping, claim in zip(mappings, claims, strict=True):
            if not isinstance(claim, dict):  # guarded by mapping validation
                raise _Abstain("invalid_claim")
            prepared.append(self._prepare_one(run_id, mapping, claim))
        return tuple(prepared)

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
        _atomic_dump(assertion, path)

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
    ) -> MaterializationResult:
        return MaterializationResult(
            run_id=run_id,
            status=status,
            assertion_ids=tuple(item.assertion["assertion_id"] for item in prepared),
            claim_ids=tuple(item.mapping.claim_id for item in prepared),
            generation_id=generation_id,
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


__all__ = [
    "AssertionMaterializer",
    "MaterializationConflict",
    "MaterializationError",
    "MaterializationInterrupted",
    "MaterializationResult",
    "ReplayResult",
    "materialize_run",
]
