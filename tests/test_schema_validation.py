"""Schema validation coverage for every Research Foundry artifact schema.

For each of the 16 distribution schemas this module builds a *minimal valid*
instance (required fields only, with correct ``const``/``enum`` values where a
required field constrains them) and asserts ``validate(...).ok`` is True, then
builds a *clearly invalid* instance (a required field removed, or a bad value
on a required ``const``) and asserts ``validate(...).ok`` is False with
non-empty ``.errors``.

Instances are built inline as plain dicts — no static fixture files. The
registry resolves the distribution ``schemas/`` directory by default, which is
exactly what we want to exercise here.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from research_foundry import ids
from research_foundry.assertion_identity import (
    SOURCE_ASSERTION_MATERIAL_FIELDS,
    source_assertion_fingerprint,
    source_assertion_id,
)
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.schemas import SchemaRegistry, validate

# The 16 artifact schemas shipped under ``schemas/``. Kept explicit so the
# parametrization itself documents the expected surface; cross-checked against
# ``SchemaRegistry().names()`` in ``test_registry_lists_all_schemas``.
EXPECTED_SCHEMA_NAMES: list[str] = [
    "arc_review_request", "assertion_evaluation", "assertion_lifecycle_event",
    "canonical_claim", "ccdash_event", "claim_ledger", "evidence_bundle",
    "extraction_card", "foundry", "ibom", "inference_record", "intenttree_node",
    "intenttree_update", "meatywiki_writeback", "notebooklm_update", "passage",
    "raw_idea", "report_draft", "report_frontmatter", "research_brief",
    "research_idea_backlog", "research_intent", "review_packet", "routing_decision",
    "search_request", "search_run", "skillbom_candidate", "source_assertion",
    "source_card", "source_edition", "swarm_plan", "tool_profile",
]


def _valid(name: str) -> dict:
    """Return a minimal instance that satisfies ``name``'s required fields."""

    builders: dict[str, dict[str, Any]] = {
        # required: id, run_id, evidence_bundle_id, target, objective, council, roles,
        #           claims_for_review, rf_exit_code, status, governance_context
        "arc_review_request": {
            "id": "arc_review_run_demo",
            "run_id": "run_demo",
            "evidence_bundle_id": "eb_demo",
            "target": "runs/run_demo/evidence_bundle.yaml",
            "objective": "Review evidence bundle for demo run.",
            "council": "research-review-council",
            "roles": ["domain_reviewer", "claim_critic"],
            "claims_for_review": [],
            "rf_exit_code": 7,
            "status": "proposed",
            "governance_context": {"sensitivity": "personal", "requires_review": False},
        },
        "assertion_evaluation": {
            "schema_version": "1.0", "type": "assertion_evaluation", "evaluation_id": "eval_demo",
            "assertion_id": "ast_" + "a" * 64, "assertion_version": 1,
            "evaluation_kind": "grounding", "verdict": "pass",
            "evaluator": {"kind": "rule", "id": "schema_guard"}, "evaluated_at": "2026-07-13T12:00:00Z",
        },
        "assertion_lifecycle_event": {
            "schema_version": "1.0", "type": "assertion_lifecycle_event", "event_id": "evt_demo",
            "sequence": 1, "idempotency_key": "demo-1", "occurred_at": "2026-07-13T12:00:00Z",
            "cause": "invalid_extraction",
            "target": {"kind": "source_assertion", "id": "ast_" + "a" * 64, "version": 1},
            "transition": {"from": "eligible", "to": "invalidated"},
            "authoritative_action": "block_reuse",
            "dependent_actions": [{"object_kind": "canonical_claim_edge", "action": "block_reuse"}],
        },
        "canonical_claim": {
            "schema_version": "1.0", "type": "canonical_claim", "canonical_claim_id": "ccl_demo",
            "canonical_claim_version": 1, "state": "proposed", "statement": "Demo grouped claim.",
            "source_assertion_refs": [{"assertion_id": "ast_" + "a" * 64, "assertion_version": 1, "relation": "supports"}],
        },
        # required: event_id, timestamp, project
        "ccdash_event": {
            "event_id": "ccd_demo",
            "timestamp": "2026-06-13T09:41:00Z",
            "project": "Research Foundry",
        },
        # required: id, intent_id
        "claim_ledger": {
            "id": "claim_demo",
            "intent_id": "intent_demo",
        },
        # required: id, intent_id, run_id
        "evidence_bundle": {
            "id": "eb_demo",
            "intent_id": "intent_demo",
            "run_id": "run_demo",
        },
        # required: id, source_card_id
        "extraction_card": {
            "id": "extract_demo",
            "source_card_id": "src_demo",
        },
        # required: foundry (object with id, name, owner)
        "foundry": {
            "schema_version": 0.1,
            "foundry": {
                "id": "rf_demo",
                "name": "Demo Foundry",
                "owner": "Tester",
            },
        },
        # required: id, intent_id
        "ibom": {
            "id": "ibom_demo",
            "intent_id": "intent_demo",
        },
        # required: node_id, title, intent_id
        "intenttree_node": {
            "node_id": "node_demo",
            "title": "Demo Node",
            "intent_id": "intent_demo",
        },
        # required: run_id, update_timestamp, status
        "intenttree_update": {
            "run_id": "run_demo",
            "update_timestamp": "2026-06-13T09:41:00Z",
            "status": "in_progress",
        },
        "inference_record": {
            "schema_version": "1.0", "type": "inference_record", "inference_id": "inf_demo",
            "inference_version": 1, "conclusion": "A derived conclusion.",
            "source_assertion_refs": [{"assertion_id": "ast_" + "a" * 64, "assertion_version": 1}],
            "reasoning": {"summary": "Derived from the source assertion.", "method": "reviewed synthesis"},
            "status": "active",
        },
        # required: id, evidence_bundle_id
        "meatywiki_writeback": {
            "id": "mww_demo",
            "evidence_bundle_id": "eb_demo",
        },
        # required: id, title, body
        "raw_idea": {
            "id": "raw_demo",
            "title": "Demo Idea",
            "body": "A captured idea body.",
        },
        # required: report_draft_id, type (const report_draft), title, sensitivity, status
        "report_draft": {
            "report_draft_id": "rpt_demo",
            "type": "report_draft",
            "title": "Demo Draft",
            "sensitivity": "public",
            "status": "draft",
        },
        # required: report_id, type (const research_report), title
        "report_frontmatter": {
            "report_id": "report_demo",
            "type": "research_report",
            "title": "Demo Report",
        },
        # required: id, intent_id, title
        "research_brief": {
            "id": "brief_demo",
            "intent_id": "intent_demo",
            "title": "Demo Brief",
        },
        # required: id, title, objective
        "research_intent": {
            "id": "intent_demo",
            "title": "Demo Intent",
            "objective": "Understand the demo domain.",
        },
        # required: id
        "review_packet": {
            "id": "review_demo",
        },
        # required: id, intent_id, active_node_id
        "routing_decision": {
            "id": "route_demo",
            "intent_id": "intent_demo",
            "active_node_id": "node_demo",
        },
        # required: id, name
        "skillbom_candidate": {
            "id": "skillbom_demo",
            "name": "Demo SkillBOM",
        },
        # required: source_card_id, type (const source_card), source
        "source_card": {
            "source_card_id": "src_demo",
            "type": "source_card",
            "source": {"title": "Demo Source"},
        },
        "source_assertion": {
            "schema_version": "1.0", "type": "source_assertion",
            "assertion_version": 1, "source_edition_id": "sed_" + "b" * 64, "passage_id": "psg_" + "c" * 64,
            "assertion_text": "The source states the demo fact.",
            "assertion_text_sha256": sha256(b"The source states the demo fact.").hexdigest(),
            "qualifiers": {}, "qualifier_extensions": {},
            "extraction_provenance": {"extractor": "schema_guard", "schema_version": "1.0", "observed_at": "2026-07-13T12:00:00Z"},
            "lifecycle_state": "eligible",
            "identity": {"algorithm": "sha256-canonical-json-v1", "fingerprint": "", "material_fields": list(SOURCE_ASSERTION_MATERIAL_FIELDS)},
        },
        "source_edition": {
            "schema_version": "1.0", "type": "source_edition", "source_edition_id": "sed_" + "b" * 64,
            "content_sha256": "b" * 64, "source_id": "src_demo", "captured_at": "2026-07-13T12:00:00Z",
        },
        "passage": {
            "schema_version": "1.0", "type": "passage", "passage_id": "psg_" + "c" * 64,
            "source_edition_id": "sed_" + "b" * 64, "normalized_text": "Demo passage.",
            "normalized_text_sha256": "c" * 64, "raw_text_sha256": "d" * 64,
            "selectors": [{"kind": "text_quote", "value": "Demo passage."}],
            "normalization": {"algorithm": "unicode-nfc", "version": "1"},
        },
        # required: id, brief_id, intent_id
        "swarm_plan": {
            "id": "swarm_demo",
            "brief_id": "brief_demo",
            "intent_id": "intent_demo",
        },
        # required: run_id, update_timestamp, status, push_status
        "notebooklm_update": {
            "run_id": "run_demo",
            "update_timestamp": "2026-06-13T09:41:00Z",
            "status": "proposed",
            "push_status": "proposed",
        },
        # required: type (const research_idea_backlog), pillars, ideas
        "research_idea_backlog": {
            "type": "research_idea_backlog",
            "pillars": [],
            "ideas": [],
        },
        # required: query, mode (search router, ADR §11.1)
        "search_request": {
            "query": "best agent web search APIs 2026",
            "mode": "source_discovery",
        },
        # required: run_id, request (search router, ADR §11.2)
        "search_run": {
            "run_id": "rf_run_demo",
            "request": {
                "query": "best agent web search APIs 2026",
                "mode": "source_discovery",
            },
        },
        # required: id, provider (search router, ADR §11.5)
        "tool_profile": {
            "id": "brave_search_v1",
            "provider": "brave",
        },
    }
    instance = dict(builders[name])
    if name == "source_assertion":
        instance["identity"]["fingerprint"] = source_assertion_fingerprint(instance)
        instance["assertion_id"] = source_assertion_id(instance)
    return instance


def _invalid(name: str) -> dict:
    """Return an instance that clearly violates ``name``'s schema.

    Most schemas constrain required fields only as strings with
    ``additionalProperties: true``, so the reliable, schema-agnostic way to
    force a failure is to drop a required field. For the two front-matter
    schemas whose required ``type`` is a ``const``, we instead supply a bad
    ``const`` value so the failure is an enum/const violation rather than a
    missing key.
    """

    instance = _valid(name)
    if name == "source_card":
        instance["type"] = "not_a_source_card"  # violates const "source_card"
        return instance
    if name == "report_frontmatter":
        instance["type"] = "not_a_report"  # violates const "research_report"
        return instance

    # Drop the first required field for every other schema.
    required_first = {
        "arc_review_request": "id",
        "assertion_evaluation": "evaluation_id",
        "assertion_lifecycle_event": "event_id",
        "canonical_claim": "canonical_claim_id",
        "ccdash_event": "event_id",
        "claim_ledger": "id",
        "evidence_bundle": "id",
        "extraction_card": "id",
        "foundry": "foundry",
        "ibom": "id",
        "intenttree_node": "node_id",
        "intenttree_update": "run_id",
        "inference_record": "inference_id",
        "meatywiki_writeback": "id",
        "notebooklm_update": "run_id",
        "raw_idea": "id",
        "report_draft": "report_draft_id",
        "research_brief": "id",
        "research_idea_backlog": "type",
        "research_intent": "id",
        "review_packet": "id",
        "routing_decision": "id",
        "search_request": "query",
        "search_run": "run_id",
        "skillbom_candidate": "id",
        "source_assertion": "assertion_id",
        "source_edition": "source_edition_id",
        "passage": "passage_id",
        "swarm_plan": "id",
        "tool_profile": "id",
    }
    instance.pop(required_first[name], None)
    return instance


@pytest.mark.parametrize("name", EXPECTED_SCHEMA_NAMES)
def test_minimal_valid_instance_passes(name: str) -> None:
    """A minimal required-fields instance validates cleanly for each schema."""

    result = validate(_valid(name), name)
    assert result.ok, f"expected {name} minimal instance valid, got: {result.errors}"
    assert result.errors == []


@pytest.mark.parametrize("name", EXPECTED_SCHEMA_NAMES)
def test_invalid_instance_fails(name: str) -> None:
    """A clearly-invalid instance fails with non-empty errors for each schema."""

    result = validate(_invalid(name), name)
    assert not result.ok, f"expected {name} invalid instance to fail validation"
    assert result.errors, f"expected non-empty errors for invalid {name} instance"


def test_registry_lists_all_schemas() -> None:
    """The registry reports exactly the expected schema names."""

    names = SchemaRegistry().names()
    assert len(names) == len(EXPECTED_SCHEMA_NAMES)
    assert names == sorted(EXPECTED_SCHEMA_NAMES)


def test_unknown_schema_yields_error_result_not_exception() -> None:
    """An unknown schema name returns a non-ok result rather than raising."""

    result = validate({"id": "anything"}, "definitely_not_a_real_schema")
    assert not result.ok
    assert result.errors, "unknown schema should surface at least one error"
    assert result.schema == "definitely_not_a_real_schema"


# ---------------------------------------------------------------------------
# Regression guard: export_run() output must pass strict rf-run-export-schema
# validation with additionalProperties:false (prevents schema/export drift).
# ---------------------------------------------------------------------------

# Substrate directories needed for a minimal isolated foundry workspace.
_SUBSTRATE = [
    "inbox/raw_ideas", "inbox/clips", "intents/active", "iboms/active",
    "intenttree/nodes", "runs", "registries",
    "meatywiki/sources", "meatywiki/concepts", "meatywiki/decisions", "meatywiki/patterns",
    "skillmeat/skillboms", "ccdash/events", "ccdash/daily", "ccdash/summaries",
]
_FIXED_TS = datetime(2026, 6, 13, 9, 41, 0, tzinfo=UTC).astimezone()


@pytest.fixture
def _tmp_foundry_for_schema(tmp_path: Path) -> FoundryPaths:
    """Isolated foundry workspace used only by the export regression guard tests."""
    root = tmp_path / "fdry_schema"
    root.mkdir(parents=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in _SUBSTRATE:
        (root / d).mkdir(parents=True, exist_ok=True)
    return FoundryPaths(root=root)


def _build_full_export_run(paths: FoundryPaths) -> dict[str, Any]:
    """Build a fully-enriched run and return export_run() output for schema validation."""
    from research_foundry.frontmatter import dump_md
    from research_foundry.services.export_service import export_run
    from research_foundry.yamlio import dump_yaml

    run_id = "rf_run_schema_guard"
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    # run.yaml with metadata enrichment + profile
    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": "intent_schema_guard",
            "status": "planned",
            "sensitivity": "personal",
            "created_at": "2026-06-13T22:46:23-04:00",
            "linked_projects": ["Research Foundry"],
            "category": "AI Engineering",
            "tags": ["schema", "validation"],
            "backlog_idea_ref": "RIB-001",
            "backlog_idea_id": "idea_schema-guard",
            "profile": {
                "max_cost_usd": 3.0,
                "max_runtime_minutes": 30,
                "freshness_days": 90,
                "extraction_model_profile": "rf_extract_cheap",
                "synthesis_model_profile": "rf_synthesize_std",
                "verification_model_profile": "rf_verify_std",
            },
        },
        rp.run_yaml,
    )

    # minimal source card
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_guard",
            "sensitivity": "public",
            "source": {"title": "Guard Source", "source_type": "official_doc",
                       "locator": {"url": "https://example.test/guard"}},
            "trust": {"source_rank": "primary"},
            "usage": {"allowed_for_public_output": True},
            "extracted_points": [{"evidence_id": "ev_001", "locator": "p1",
                                   "summary": "guard summary", "quote": "guard quote"}],
        },
        "",
        rp.sources / "src_guard.md",
    )

    # claim ledger with one claim referencing the source card
    dump_yaml(
        {
            "schema_version": "0.1",
            "claims": [
                {
                    "claim_id": "clm_guard_001",
                    "text": "Guard claim text",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [{"source_card_id": "src_guard", "evidence_id": "ev_001",
                                 "relation": "supports", "locator": "p1"}],
                    "persistent_references": {
                        "source_edition_id": "sed_guard", "passage_id": "psg_guard",
                        "source_assertion_id": "ast_guard", "assertion_version": 1,
                    },
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                }
            ],
        },
        rp.claim_ledger,
    )

    # verification
    dump_yaml(
        {"run_id": run_id, "passed": True, "exit_code": 0,
         "checks": [{"id": "check_01", "severity": "error", "status": "pass",
                     "detail": "ok", "locations": []}]},
        rp.verification,
    )

    # evidence bundle
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 1, "claims_supported": 1},
            "governance": {"sensitivity": "personal", "approved_for_writeback": False},
        },
        rp.evidence_bundle,
    )

    # report draft (with frontmatter title for title-derivation path)
    rp.report_draft.write_text(
        "---\ntitle: Guard Research Report\n---\n\nBody. [claim:clm_guard_001]\n",
        encoding="utf-8",
    )

    return export_run(paths, run_id)


def test_export_run_passes_strict_json_schema_validation(
    _tmp_foundry_for_schema: FoundryPaths,
) -> None:
    """REGRESSION GUARD: export_run() output must pass strict Draft7 validation
    against rf-run-export-schema.json with additionalProperties:false.

    If this test fails, a field was added to export_run() without updating the
    schema (or vice versa). Fix by adding the field to the schema's properties.
    """
    ids.set_clock(lambda: _FIXED_TS)
    try:
        export_dict = _build_full_export_run(_tmp_foundry_for_schema)
    finally:
        ids.set_clock(lambda: datetime.now(UTC).astimezone())

    # Load the schema from the repo docs directory (authoritative location).
    schema_path = (
        Path(__file__).parent.parent
        / "docs" / "dev" / "architecture" / "rf-run-export-schema.json"
    )
    assert schema_path.exists(), f"rf-run-export-schema.json not found at {schema_path}"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(export_dict))
    error_messages = [
        f"  [{'.'.join(str(p) for p in e.absolute_path) or 'root'}] {e.message}"
        for e in errors
    ]
    assert not errors, (
        f"export_run() output failed strict JSON schema validation "
        f"({len(errors)} error(s)):\n" + "\n".join(error_messages)
    )
