"""Assertion-only materialization from published registry passages."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..assertion_identity import source_assertion_fingerprint, source_assertion_id
from ..frontmatter import load_md
from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, load_yaml
from .assertion_registry import AssertionRegistry


@dataclass(frozen=True)
class MaterializationResult:
    assertion: dict[str, Any] | None
    evaluation: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    created: bool = False
    reason: str | None = None


class AssertionMaterializer:
    """Workspace-scoped file topology for assertion-only materialization."""

    def __init__(self, *, workspace_id: str, paths: FoundryPaths | None = None) -> None:
        if not workspace_id:
            raise ValueError("workspace_id is required")
        self.paths = paths or FoundryPaths.discover()
        self.workspace_id = workspace_id
        self.root = self.paths.root / "assertion_ledger" / "workspaces" / sha256(workspace_id.encode()).hexdigest() / "materialized_assertions"

    def assertion_path(self, assertion_id: str) -> Path:
        return self.root / "assertions" / f"{assertion_id}.yaml"

    def evaluation_path(self, assertion_id: str) -> Path:
        return self.root / "evaluations" / f"evl_{assertion_id[4:]}.yaml"

    def audit_path(self, assertion_id: str) -> Path:
        return self.root / "audit" / f"{assertion_id}.yaml"

    def _published_path(self, assertion_id: str) -> Path:
        return self.root / "published" / f"{assertion_id}.yaml"

    def _resolve_manifest_entry(self, value: object) -> Path | None:
        if not isinstance(value, str) or not value:
            return None
        relative = Path(value)
        if relative.is_absolute():
            return None
        root = self.root.resolve()
        resolved = (self.root / relative).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return None
        return resolved

    def _verify_extraction_fact(
        self,
        *,
        source_key: str,
        edition: dict[str, Any],
        passage: dict[str, Any],
        text: str,
        extraction_provenance: dict[str, Any],
    ) -> str | None:
        """Bind one extracted fact to its source card and exact published passage."""

        fields = ("extraction_card_id", "source_card_id", "evidence_id", "locator")
        binding = {field: extraction_provenance.get(field) for field in fields}
        if not all(isinstance(value, str) and value.strip() for value in binding.values()):
            return "unverified_extraction_fact"
        runs_root = self.paths.runs.resolve()
        extraction_matches = 0
        for card_path in self.paths.runs.glob("*/extractions/*.yaml"):
            if not card_path.resolve().is_relative_to(runs_root):
                continue
            try:
                card = load_yaml(card_path)
            except Exception:  # noqa: BLE001 - persisted cards are untrusted at this boundary.
                continue
            if not isinstance(card, dict) or card.get("id") != binding["extraction_card_id"] or card.get("source_card_id") != binding["source_card_id"]:
                continue
            facts = card.get("extracted_facts")
            if not isinstance(facts, list):
                continue
            extraction_matches += sum(
                isinstance(fact, dict)
                and fact.get("evidence_id") == binding["evidence_id"]
                and fact.get("locator") == binding["locator"]
                and fact.get("text") == text
                for fact in facts
            )
        if extraction_matches != 1:
            return "unverified_extraction_fact"
        source_matches = 0
        for source_path in self.paths.runs.glob("*/sources/*.md"):
            if not source_path.resolve().is_relative_to(runs_root):
                continue
            try:
                source_card, _ = load_md(source_path)
            except Exception:  # noqa: BLE001 - persisted source cards are untrusted at this boundary.
                continue
            if source_card.get("source_card_id") != binding["source_card_id"]:
                continue
            points = source_card.get("extracted_points")
            if not isinstance(points, list):
                continue
            source_matches += sum(
                isinstance(point, dict)
                and point.get("evidence_id") == binding["evidence_id"]
                and point.get("locator") == binding["locator"]
                and point.get("summary") == text
                for point in points
            )
        if source_matches != 1:
            return "source_passage_binding_mismatch"
        if source_key != binding["source_card_id"]:
            return "source_card_binding_mismatch"
        if (
            edition.get("source_edition_id") != passage.get("source_edition_id")
            or not isinstance(passage.get("context"), dict)
            or passage["context"].get("exact_quote") != text
        ):
            return "source_passage_binding_mismatch"
        return None

    @staticmethod
    def _published_packet_is_valid(
        assertion: object,
        evaluation: object,
        audit: object,
        expected: MaterializationResult,
    ) -> bool:
        """Reject in-root artifact substitution as strictly as path escape."""

        if not isinstance(assertion, dict) or not isinstance(evaluation, dict) or not isinstance(audit, dict):
            return False
        expected_assertion = expected.assertion
        expected_evaluation = expected.evaluation
        expected_audit = expected.audit
        if expected_assertion is None or expected_evaluation is None or expected_audit is None:
            return False
        assertion_id = expected_assertion["assertion_id"]
        evaluation_id = expected_evaluation["evaluation_id"]
        edition_id = expected_assertion["source_edition_id"]
        passage_id = expected_assertion["passage_id"]
        return (
            assertion.get("type") == "source_assertion"
            and assertion.get("assertion_id") == assertion_id
            and assertion.get("source_edition_id") == edition_id
            and assertion.get("passage_id") == passage_id
            and evaluation.get("type") == "assertion_evaluation"
            and evaluation.get("evaluation_id") == evaluation_id
            and evaluation.get("assertion_id") == assertion_id
            and evaluation.get("assertion_version") == expected_assertion["assertion_version"]
            and evaluation.get("details", {}).get("source_edition_id") == edition_id
            and evaluation.get("details", {}).get("passage_id") == passage_id
            and audit.get("type") == "assertion_materialization_audit"
            and audit.get("assertion_id") == assertion_id
            and audit.get("evaluation_id") == evaluation_id
            and audit.get("source_edition_id") == edition_id
            and audit.get("passage_id") == passage_id
        )

    @staticmethod
    def _atomic_dump(data: dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(dumps_yaml(data))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def build(self, *, passage: dict[str, Any], text: str, extraction_provenance: dict[str, Any], qualifiers: dict[str, Any] | None = None, qualifier_extensions: dict[str, Any] | None = None, recorder: str = "rf_assertion_materializer", _edition: dict[str, Any] | None = None) -> MaterializationResult:
        if not text.strip():
            return MaterializationResult(None, reason="blank")
        if extraction_provenance.get("contract") != "extracted_facts-1to1-v1":
            return MaterializationResult(None, reason="unsupported_contract")
        extractor, observed_at = extraction_provenance.get("extractor"), extraction_provenance.get("observed_at")
        if not isinstance(extractor, str) or not extractor.strip() or not isinstance(observed_at, str) or "T" not in observed_at:
            return MaterializationResult(None, reason="missing_extraction_provenance")
        edition_id, passage_id = passage.get("source_edition_id"), passage.get("passage_id")
        if not isinstance(edition_id, str) or not isinstance(passage_id, str):
            return MaterializationResult(None, reason="missing_binding")
        if passage.get("ambiguous"):
            return MaterializationResult(None, reason="ambiguous_selector")
        if extraction_provenance.get("semantic_only"):
            return MaterializationResult(None, reason="semantic_only_abstention")
        digest = sha256(text.encode()).hexdigest()
        source_provenance = {"extractor": extractor, "provider": extraction_provenance.get("provider"), "model": extraction_provenance.get("model"), "prompt_version": extraction_provenance.get("prompt_version"), "schema_version": "extracted_facts-1to1-v1", "code_version": extraction_provenance.get("code_version"), "observed_at": observed_at}
        extraction_binding = {key: extraction_provenance[key] for key in ("extraction_card_id", "source_card_id", "evidence_id", "locator") if key in extraction_provenance}
        assertion: dict[str, Any] = {"schema_version": "1.0", "type": "source_assertion", "assertion_version": 1, "source_edition_id": edition_id, "passage_id": passage_id, "assertion_text": text, "assertion_text_sha256": digest, "qualifiers": qualifiers or {}, "qualifier_extensions": qualifier_extensions or {}, "extraction_provenance": source_provenance, "lifecycle_state": "eligible"}
        fingerprint = source_assertion_fingerprint(assertion)
        assertion["assertion_id"] = source_assertion_id(assertion)
        assertion["identity"] = {"algorithm": "sha256-canonical-json-v1", "fingerprint": fingerprint, "material_fields": ["source_edition_id", "passage_id", "assertion_text_sha256", "qualifiers", "qualifier_extensions"]}
        evaluation_digest = sha256(f"{assertion['assertion_id']}:reuse_eligibility:1".encode()).hexdigest()
        evaluation = {"schema_version": "1.0", "type": "assertion_evaluation", "evaluation_id": f"evl_{evaluation_digest}", "assertion_id": assertion["assertion_id"], "assertion_version": 1, "evaluation_kind": "reuse_eligibility", "verdict": "needs_review", "evaluator": {"kind": "rule", "id": recorder, "version": "extracted_facts-1to1-v1"}, "evaluated_at": observed_at, "details": {"contract_version": "extracted_facts-1to1-v1", "source_edition_id": edition_id, "passage_id": passage_id, "extraction_binding": extraction_binding}}
        audit = {"type": "assertion_materialization_audit", "assertion_id": assertion["assertion_id"], "evaluation_id": evaluation["evaluation_id"], "source_edition_id": edition_id, "passage_id": passage_id, "recorder": recorder, "contract_version": extraction_provenance.get("contract"), "access_scope": (_edition or {}).get("access_scope"), "allowed_use": ((_edition or {}).get("metadata_extensions") or {}).get("allowed_use"), "extraction_binding": extraction_binding}
        return MaterializationResult(assertion, evaluation, audit, True)

    def materialize(self, *, source_key: str, passage: dict[str, Any], text: str, extraction_provenance: dict[str, Any], qualifiers: dict[str, Any] | None = None, qualifier_extensions: dict[str, Any] | None = None, _interrupt_before_publish: bool = False) -> MaterializationResult:
        edition_id, passage_id = passage.get("source_edition_id"), passage.get("passage_id")
        if not isinstance(edition_id, str) or not isinstance(passage_id, str):
            return MaterializationResult(None, reason="missing_binding")
        registry = AssertionRegistry(workspace_id=self.workspace_id, paths=self.paths)
        edition = registry.get_edition(source_key, edition_id)
        if edition is None:
            return MaterializationResult(None, reason="unpublished_edition")
        published_read = registry.read_published_passages(source_key, edition_id)
        if published_read.reason is not None:
            return MaterializationResult(None, reason=published_read.reason)
        published = next((item for item in published_read.passages if item["passage_id"] == passage_id), None)
        if published is None:
            return MaterializationResult(None, reason="unpublished_passage")
        for field in ("raw_text_sha256", "normalized_text_sha256", "selectors"):
            if field in passage and passage[field] != published.get(field):
                return MaterializationResult(None, reason="passage_binding_drift")
        passage = published
        verification_reason = self._verify_extraction_fact(
            source_key=source_key,
            edition=edition,
            passage=passage,
            text=text,
            extraction_provenance=extraction_provenance,
        )
        if verification_reason is not None:
            return MaterializationResult(None, reason=verification_reason)
        result = self.build(passage=passage, text=text, extraction_provenance=extraction_provenance, qualifiers=qualifiers, qualifier_extensions=qualifier_extensions, _edition=edition)
        if result.assertion is None:
            return result
        assertion_id = result.assertion["assertion_id"]
        manifest = self._published_path(assertion_id)
        if manifest.exists():
            packet = load_yaml(manifest)
            if not isinstance(packet, dict):
                return MaterializationResult(None, reason="invalid_published_manifest")
            assertion_path = self._resolve_manifest_entry(packet.get("assertion"))
            evaluation_path = self._resolve_manifest_entry(packet.get("evaluation"))
            audit_path = self._resolve_manifest_entry(packet.get("audit"))
            if assertion_path is None or evaluation_path is None or audit_path is None:
                return MaterializationResult(None, reason="invalid_published_manifest")
            try:
                assertion = load_yaml(assertion_path)
                evaluation = load_yaml(evaluation_path)
                audit = load_yaml(audit_path)
            except Exception:  # noqa: BLE001 - published packet files are untrusted at reload.
                return MaterializationResult(None, reason="invalid_published_manifest")
            if not self._published_packet_is_valid(assertion, evaluation, audit, result):
                return MaterializationResult(None, reason="invalid_published_manifest")
            return MaterializationResult(assertion=assertion, evaluation=evaluation, audit=audit, created=False)
        generation = self.root / "generations" / assertion_id
        assertion_path, evaluation_path, audit_path = generation / "assertion.yaml", generation / "evaluation.yaml", generation / "audit.yaml"
        self._atomic_dump(result.assertion, assertion_path)
        self._atomic_dump(result.evaluation or {}, evaluation_path)
        self._atomic_dump(result.audit or {}, audit_path)
        if _interrupt_before_publish:
            raise RuntimeError("simulated materialization publication interruption")
        self._atomic_dump({"assertion": str(assertion_path.relative_to(self.root)), "evaluation": str(evaluation_path.relative_to(self.root)), "audit": str(audit_path.relative_to(self.root))}, manifest)
        return result


@dataclass(frozen=True)
class ReplayResult:
    cursor: int
    results: tuple[MaterializationResult, ...]
    complete: bool


def replay_facts(*, facts: list[dict[str, Any]], cursor: int = 0, batch_size: int = 100, materializer: AssertionMaterializer | None = None, source_key: str | None = None) -> ReplayResult:
    """Bounded deterministic replay; callers persist the returned cursor."""
    if cursor < 0 or batch_size < 1:
        raise ValueError("cursor and batch_size must be non-negative/positive")
    if (materializer is None) != (source_key is None):
        raise ValueError("materializer and source_key must be supplied together")
    batch = facts[cursor:cursor + batch_size]
    if materializer is None:
        results = tuple(materialize_assertion(passage=item.get("passage", {}), text=item.get("text", ""), extraction_provenance=item.get("provenance", {}), qualifiers=item.get("qualifiers"), qualifier_extensions=item.get("qualifier_extensions")) for item in batch)
    else:
        assert source_key is not None
        results = tuple(materializer.materialize(source_key=source_key, passage=item.get("passage", {}), text=item.get("text", ""), extraction_provenance=item.get("provenance", {}), qualifiers=item.get("qualifiers"), qualifier_extensions=item.get("qualifier_extensions")) for item in batch)
    next_cursor = cursor + len(batch)
    return ReplayResult(next_cursor, results, next_cursor >= len(facts))


def materialize_assertion(*, passage: dict[str, Any], text: str, extraction_provenance: dict[str, Any], qualifiers: dict[str, Any] | None = None, qualifier_extensions: dict[str, Any] | None = None) -> MaterializationResult:
    """Create a deterministic assertion packet; blank or ambiguous input abstains."""
    return AssertionMaterializer(workspace_id="compatibility").build(passage=passage, text=text, extraction_provenance=extraction_provenance, qualifiers=qualifiers, qualifier_extensions=qualifier_extensions)
