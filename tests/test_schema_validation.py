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

# The 37 artifact schemas shipped under ``schemas/`` (32 pre-existing + 5 added
# by rights-entity-model-v1 P0-1..P0-4: content_reuse_assessment,
# permission_record, rights_extension, rights_failure, rights_record). Kept
# explicit so the parametrization itself documents the expected surface;
# cross-checked against ``SchemaRegistry().names()`` in
# ``test_registry_lists_all_schemas``.
EXPECTED_SCHEMA_NAMES: list[str] = [
    "arc_review_request", "assertion_evaluation", "assertion_lifecycle_event",
    "canonical_claim", "ccdash_event", "claim_ledger", "content_reuse_assessment",
    "evidence_bundle", "extraction_card", "foundry", "ibom", "inference_record",
    "intenttree_node", "intenttree_update", "meatywiki_writeback", "notebooklm_update",
    "passage", "permission_record", "raw_idea", "report_draft", "report_frontmatter",
    "research_brief", "research_idea_backlog", "research_intent", "review_packet",
    "rights_extension", "rights_failure", "rights_record", "routing_decision",
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
            "extensions": {
                "evidence_taxonomy": {
                    "evidence_item_type": "observed_finding",
                    "judgment_basis": "measured",
                }
            },
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
        # rights-entity-model-v1 (P0-1..P0-4) — minimal instances for the 5
        # new substrate schemas; see dedicated §9-adjudication fixture tests
        # elsewhere in this file (and tests/test_rights_record_schema_fixtures.py
        # for rights_record's full §9 coverage) for deeper validation.
        "rights_record": {
            "schema_version": "1.0",
            "rights_record_id": "RR-DEMO-001",
            "record_scope": "first_party",
            "jurisdictions": ["US"],
            "access": {"basis": "unknown", "terms_verified_at": "2026-07-21T00:00:00Z"},
            "copyright": {"status": "unknown"},
            "component_decisions": [{"component_type": "other", "decision": "unknown"}],
            "overall_status": "OWNED",
            "review": {"reviewed_at": "2026-07-21T00:00:00Z", "review_status": "agent_triage_only"},
        },
        "rights_extension": {
            "schema_version": "1.0",
            "type": "rights_extension",
            "rights_extension_id": "rext_min_demo",
            "rights_record_ids": ["RR-DEMO-001"],
            "clearance_status": "UNKNOWN",
            "release_gate": "BLOCK",
            "last_reviewed_at": "2026-07-21T00:00:00Z",
        },
        "content_reuse_assessment": {
            "schema_version": "1.0",
            "type": "content_reuse_assessment",
            "reuse_assessment_id": "CRA-DEMO-001",
            "source_id": "SRC-DEMO-001",
            "rights_record_ids": ["RR-DEMO-001"],
            "component": {"component_type": "other", "description": "Demo component."},
            "intended_use": {
                "product": "Demo Product",
                "use_type": "internal_research",
                "commercial": False,
                "audience": ["internal"],
                "channels": ["internal_tool"],
                "territories": ["US"],
            },
            "analysis": {
                "independently_authored": True,
                "copies_source_wording": False,
                "copies_source_arrangement": False,
                "compilation_similarity": "none",
                "market_substitution_risk": "none",
                "alternative_sources_available": True,
            },
            "decision": {
                "status": "UNKNOWN",
                "release_gate": "BLOCK",
                "rationale": "Demo rationale pending review.",
            },
            "review": {"reviewed_at": "2026-07-21T00:00:00Z", "review_status": "agent_triage_only"},
        },
        "permission_record": {
            "schema_version": "1.0",
            "permission_record_id": "PR-DEMO-MIN-001",
            "rights_holder": "Demo Rights Holder",
            "covered_source_ids": ["SRC-DEMO-001"],
            "grant": {
                "commercial_use": True,
                "adaptation": True,
                "redistribution": True,
                "channels": ["web_saas"],
                "audiences": ["demo"],
                "territories": ["US"],
            },
            "term": {"start_date": "2026-07-21", "end_date": None, "renewal": "manual"},
            "agreement_evidence": {
                "document_uri": "internal://contracts/demo-min.pdf",
                "checksum_sha256": "a" * 64,
                "executed_at": "2026-07-21T00:00:00Z",
            },
            "status": "active",
            "review": {"reviewed_at": "2026-07-21T00:00:00Z", "approved_by": ["demo-reviewer"]},
        },
        "rights_failure": {
            "schema_version": "1.0",
            "rights_failure_id": "RF-DEMO-MIN-001",
            "source_id": "SRC-DEMO-001",
            "failure_type": "OTHER",
            "intended_use": "Demo intended use.",
            "finding": "Demo finding blocking use.",
            "safe_residual_use": [],
            "product_impact": "Demo product impact.",
            "release_gate": "BLOCK",
            "status": "open",
            "review": {"reviewed_at": "2026-07-21T00:00:00Z"},
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
        # rights-entity-model-v1 (P0-1..P0-4)
        "rights_record": "rights_record_id",
        "rights_extension": "rights_extension_id",
        "content_reuse_assessment": "reuse_assessment_id",
        "permission_record": "permission_record_id",
        "rights_failure": "rights_failure_id",
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


def test_content_reuse_assessment_enums_match_rights_record() -> None:
    """P0-3 seed for the P6-1 full consistency sweep (rights-entity-model-v1
    §9.2/§9.8, §9.7): ``content_reuse_assessment``'s ``component.component_type``
    and ``review.review_status`` enums must be byte-identical literal lists to
    ``rights_record``'s ``component_decisions[].component_type`` and
    ``review.review_status`` (P0-1) — RF's ``SchemaRegistry`` has no resolver
    support, so cross-file ``$ref`` is not possible and each schema carries its
    own literal copy of the shared vocabulary.

    P0-1 and P0-3 were authored concurrently; if ``rights_record.schema.yaml``
    has not yet landed, this test is skipped (not failed) — a skip here is a
    signal to the phase-owner that the identity check has not run yet, and it
    should be re-run once P0-1 lands. Once both schemas exist, any mismatch is
    a genuine reconciliation gap that must close before Phase 0 exits.
    """
    registry = SchemaRegistry()
    if not registry.has("rights_record"):
        pytest.skip(
            "rights_record schema not yet landed (P0-1) — component_type/"
            "review_status identity check against content_reuse_assessment "
            "cannot run yet; re-run once P0-1 lands."
        )

    rights_record = registry.get("rights_record")
    content_reuse = registry.get("content_reuse_assessment")

    rr_component_type = (
        rights_record["properties"]["component_decisions"]["items"]
        ["properties"]["component_type"]["enum"]
    )
    cra_component_type = (
        content_reuse["properties"]["component"]["properties"]["component_type"]["enum"]
    )
    assert cra_component_type == rr_component_type, (
        "component_type enum diverged between content_reuse_assessment and "
        "rights_record (§9.2/§9.8) — reconcile before Phase 0 closes.\n"
        f"rights_record:            {rr_component_type}\n"
        f"content_reuse_assessment: {cra_component_type}"
    )

    rr_review_status = rights_record["properties"]["review"]["properties"]["review_status"]["enum"]
    cra_review_status = content_reuse["properties"]["review"]["properties"]["review_status"]["enum"]
    assert cra_review_status == rr_review_status, (
        "review_status enum diverged between content_reuse_assessment and "
        "rights_record (§9.7) — reconcile before Phase 0 closes.\n"
        f"rights_record:            {rr_review_status}\n"
        f"content_reuse_assessment: {cra_review_status}"
    )


# ---------------------------------------------------------------------------
# P0-4: permission_record + rights_failure schemas (rights-entity-model-v1).
#
# Ported structurally as-is from the v1.0 Research Foundry Source Reuse &
# Rights Governance Spec — no §9 adjudication conflicts were named against
# either schema. These are standalone, append-only additions (do not merge
# into EXPECTED_SCHEMA_NAMES/_valid()/_invalid() above — P0-5 owns that Registry
# wiring and touches this file concurrently).
# ---------------------------------------------------------------------------


def _permission_record_valid_instance() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "permission_record_id": "PR-SOCIETY-TABLE-001",
        "rights_holder": "Example Professional Society",
        "rights_holder_contact": "permissions@example.org",
        "license_or_permission_identifier": "LICENSE-2026-001",
        "covered_source_ids": ["SRC-SOCIETY-GUIDELINE-001"],
        "covered_components": ["Table 2", "Figure 1"],
        "covered_products": ["PedsLab Pathways"],
        "covered_affiliates": ["Example Company, Inc."],
        "grant": {
            "commercial_use": True,
            "adaptation": True,
            "redistribution": True,
            "sublicensing": False,
            "hosting": True,
            "api_use": True,
            "updates_included": False,
            "text_and_data_mining": False,
            "model_training": False,
            "channels": ["web_saas"],
            "audiences": ["licensed clinicians"],
            "territories": ["US", "CA"],
            "user_or_volume_limits": ["Up to 25,000 named users"],
        },
        "obligations": {
            "attribution": ["Display the agreed source citation"],
            "notices": ["Display the agreed copyright notice"],
            "change_indication": True,
            "fees": ["Annual license fee under executed agreement"],
            "reporting": ["Annual active-user report"],
            "audit": ["Rights holder may audit usage once annually"],
            "deletion_or_return": ["Remove licensed components within 30 days"],
            "other": [],
        },
        "term": {
            "start_date": "2026-10-01",
            "end_date": "2027-09-30",
            "renewal": "manual",
            "termination_conditions": ["Material breach", "Nonpayment"],
        },
        "agreement_evidence": {
            "document_uri": "internal://contracts/LICENSE-2026-001.pdf",
            "checksum_sha256": "a" * 64,
            "executed_at": "2026-09-15T14:00:00Z",
            "signatories": ["Example Company, Inc.", "Example Professional Society"],
        },
        "status": "active",
        "review": {
            "reviewed_at": "2026-09-16T12:00:00Z",
            "approved_by": ["product-counsel", "rights-owner"],
            "next_review_at": "2027-06-30T12:00:00Z",
            "notes": None,
        },
        "extensions": {},
    }


def test_permission_record_schema_valid_instance_passes_draft202012() -> None:
    """A minimal-but-complete permission_record instance validates cleanly."""
    schema = SchemaRegistry().get("permission_record")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(_permission_record_valid_instance()))
    assert not errors, [e.message for e in errors]


def test_permission_record_schema_invalid_instance_fails_draft202012() -> None:
    """Dropping the required `grant` object must fail validation."""
    instance = _permission_record_valid_instance()
    del instance["grant"]
    schema = SchemaRegistry().get("permission_record")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors, "expected validation errors for a permission_record missing `grant`"


def test_permission_record_schema_rejects_additional_properties() -> None:
    """Strict-family guard: an unknown top-level field must fail validation."""
    instance = _permission_record_valid_instance()
    instance["unexpected_field"] = "should not be allowed"
    schema = SchemaRegistry().get("permission_record")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors, "expected additionalProperties:false to reject an unknown field"


def _rights_failure_valid_instance() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "rights_failure_id": "RF-AAP-PCO-INCORPORATION-001",
        "source_id": "SRC-AAP-PCO-001",
        "rights_record_id": "RR-SRC-AAP-PCO-001",
        "reuse_assessment_id": None,
        "failure_type": "CONTRACT_PROHIBITS_INCORPORATION",
        "component": "AAP Pediatric Care Online tables and algorithms",
        "intended_use": "Commercial Evidence Foundry knowledge base",
        "finding": (
            "The subscription terms do not grant the intended product-incorporation "
            "right and require separate written approval."
        ),
        "source_terms_locator": "Pediatric Care Online Terms, Section 3.4",
        "safe_residual_use": [
            "Internal clinical research within the subscription scope",
            "Citation metadata",
        ],
        "product_impact": "Block direct ingestion of AAP tables and algorithms into the commercial runtime.",
        "alternative_source_ids": [],
        "permission_strategy": "Request an AAP EHR/CDS commercial license.",
        "next_action": "Inventory AAP-dependent components and identify alternatives.",
        "owner": "rights-owner",
        "retry_trigger": "Written commercial permission or approved alternative-source implementation",
        "severity": "high",
        "release_gate": "BLOCK",
        "status": "open",
        "review": {
            "reviewed_at": "2026-07-21T12:00:00Z",
            "reviewed_by": ["rights-governance-agent"],
            "notes": "Operational triage; counsel review required for final commercial determination",
        },
        "extensions": {},
    }


def test_rights_failure_schema_valid_instance_passes_draft202012() -> None:
    """A minimal-but-complete rights_failure instance validates cleanly."""
    schema = SchemaRegistry().get("rights_failure")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(_rights_failure_valid_instance()))
    assert not errors, [e.message for e in errors]


def test_rights_failure_schema_invalid_instance_fails_draft202012() -> None:
    """An unrecognized `failure_type` enum member must fail validation."""
    instance = _rights_failure_valid_instance()
    instance["failure_type"] = "NOT_A_REAL_FAILURE_TYPE"
    schema = SchemaRegistry().get("rights_failure")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors, "expected validation errors for an unrecognized failure_type"


def test_rights_failure_schema_rejects_additional_properties() -> None:
    """Strict-family guard: an unknown top-level field must fail validation."""
    instance = _rights_failure_valid_instance()
    instance["unexpected_field"] = "should not be allowed"
    schema = SchemaRegistry().get("rights_failure")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors, "expected additionalProperties:false to reject an unknown field"


# ---------------------------------------------------------------------------
# P0-2: rights_extension.schema.yaml — rights-container-only negative-space
# guard (decisions-block §9.1/§9.4). Appended, standalone from the
# EXPECTED_SCHEMA_NAMES-parametrized suite above so this lands independently
# of P0-5's Registry wiring for the sibling substrate schemas.
# ---------------------------------------------------------------------------

_FORBIDDEN_EVIDENCE_TAXONOMY_FIELD_NAMES = {
    "evidence_item_type",
    "judgment_basis",
    "evidence_taxonomy",
}


def _collect_property_names(node: Any) -> set[str]:
    """Recursively collect every JSON-Schema property key declared under ``node``.

    Walks any ``properties`` mapping at any nesting depth (nested objects,
    array ``items``, subschemas) and returns the full set of property names
    declared anywhere in the schema document — used to prove a schema never
    declares a given field, not just that it lacks it at the top level.
    """

    names: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            for key, subschema in properties.items():
                names.add(key)
                names |= _collect_property_names(subschema)
        for key, value in node.items():
            if key == "properties":
                continue
            names |= _collect_property_names(value)
    elif isinstance(node, list):
        for item in node:
            names |= _collect_property_names(item)
    return names


def test_rights_extension_schema_is_a_rights_container_only() -> None:
    """P0-2 negative-space guard (decisions-block §9.1 / §9.4).

    ``rights_extension`` is a rights container ONLY. It must never define
    ``evidence_item_type``, ``judgment_basis``, or any other
    evidence-quality-taxonomy-shaped field — that axis is domain-general
    evidence metadata that lives in a sibling ``extensions.evidence_taxonomy``
    block on ``source_assertion`` (a separate Phase 1 task), never nested
    under rights. This guards against future drift re-coupling the two axes.
    """

    schema = SchemaRegistry().get("rights_extension")
    property_names = _collect_property_names(schema)
    overlap = property_names & _FORBIDDEN_EVIDENCE_TAXONOMY_FIELD_NAMES
    assert not overlap, (
        "rights_extension.schema.yaml must not define evidence-taxonomy "
        f"fields; found: {sorted(overlap)}"
    )


def test_rights_extension_minimal_valid_instance_passes() -> None:
    """rights_extension.schema.yaml validates a minimal required-fields instance."""

    instance = {
        "schema_version": "1.0",
        "type": "rights_extension",
        "rights_extension_id": "rext_demo",
        "rights_record_ids": ["RR-SRC-DEMO-001"],
        "clearance_status": "UNKNOWN",
        "release_gate": "BLOCK",
        "last_reviewed_at": "2026-07-21T00:00:00Z",
    }
    result = validate(instance, "rights_extension")
    assert result.ok, f"expected rights_extension minimal instance valid, got: {result.errors}"
    assert result.errors == []


def test_rights_extension_invalid_instance_fails() -> None:
    """A rights_extension instance missing a required field fails validation."""

    instance = {
        "schema_version": "1.0",
        "type": "rights_extension",
        "rights_extension_id": "rext_demo",
        # rights_record_ids omitted — required, and required whenever any
        # mirror/clearance field is non-unknown (link-before-assert).
        "clearance_status": "UNKNOWN",
        "release_gate": "BLOCK",
        "last_reviewed_at": "2026-07-21T00:00:00Z",
    }
    result = validate(instance, "rights_extension")
    assert not result.ok
    assert result.errors


# ---------------------------------------------------------------------------
# P1-1: source_assertion.schema.yaml — `extensions.evidence_taxonomy.
# evidence_item_type` reachability guard (decisions-block §9.1 / D4 / OQ-RF-2).
# Positive counterpart to ``test_rights_extension_schema_is_a_rights_container_only``
# above: proves the evidence-taxonomy axis IS reachable on ``source_assertion``
# as a REQUIRED sibling ``extensions`` block, AND that it remains unreachable
# via any ``rights_extension``-rooted path — the two axes never meet.
# ---------------------------------------------------------------------------

_EVIDENCE_ITEM_TYPE_MEMBERS = [
    "observed_finding",
    "reference_interval_value",
    "equation_or_method",
    "guideline_recommendation",
    "instrument_or_questionnaire",
    "bibliographic_metadata",
    "derived_synthesis",
    "other",
]


def test_source_assertion_extensions_evidence_taxonomy_is_required_and_reachable() -> None:
    """``extensions.evidence_taxonomy.evidence_item_type`` is a required,
    reachable enum field on ``source_assertion``, declared as a sibling block
    (never nested under/through ``rights_extension``)."""

    schema = SchemaRegistry().get("source_assertion")
    assert "extensions" in schema.get("required", []), (
        "source_assertion.schema.yaml must require top-level `extensions`"
    )
    extensions_schema = schema["properties"]["extensions"]
    assert extensions_schema.get("additionalProperties") is False
    assert "evidence_taxonomy" in extensions_schema.get("required", [])

    taxonomy_schema = extensions_schema["properties"]["evidence_taxonomy"]
    assert taxonomy_schema.get("additionalProperties") is False
    assert "evidence_item_type" in taxonomy_schema.get("required", [])

    item_type_schema = taxonomy_schema["properties"]["evidence_item_type"]
    assert item_type_schema["enum"] == _EVIDENCE_ITEM_TYPE_MEMBERS


def test_source_assertion_evidence_taxonomy_not_reachable_via_rights_extension() -> None:
    """Positive counterpart to the P0-2 negative-space guard: the
    evidence-taxonomy axis added to ``source_assertion`` in P1-1 is a SIBLING
    block and stays unreachable via any ``rights_extension``-rooted schema
    path (decisions-block §9.1). Guards against future drift re-coupling the
    two axes from either direction.
    """

    rights_extension_schema = SchemaRegistry().get("rights_extension")
    property_names = _collect_property_names(rights_extension_schema)
    overlap = property_names & _FORBIDDEN_EVIDENCE_TAXONOMY_FIELD_NAMES
    assert not overlap, (
        "rights_extension.schema.yaml must not gain evidence-taxonomy fields "
        f"after source_assertion P1-1 adds them; found: {sorted(overlap)}"
    )

    # Symmetric check: source_assertion's new `extensions` block must not
    # itself declare a `rights_extension` property or `$ref` into it — a
    # structural check over schema keywords, distinct from the human-readable
    # `description` prose (which is free to name `rights_extension.schema.yaml`
    # for cross-referencing, as this schema's own doc-comment does).
    source_assertion_schema = SchemaRegistry().get("source_assertion")
    extensions_schema = source_assertion_schema["properties"]["extensions"]
    assert "rights_extension" not in _collect_property_names(extensions_schema)

    def _collect_refs(node: Any) -> set[str]:
        refs: set[str] = set()
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                refs.add(ref)
            for key, value in node.items():
                if key == "description":
                    continue
                refs |= _collect_refs(value)
        elif isinstance(node, list):
            for item in node:
                refs |= _collect_refs(item)
        return refs

    assert not any("rights_extension" in ref for ref in _collect_refs(extensions_schema))


def _p1_1_source_assertion_instance(
    *, evidence_item_type: str | None, judgment_basis: str = "measured"
) -> dict[str, Any]:
    """Build a fully-populated ``source_assertion`` instance for P1-1/P1-2 fixtures.

    When ``evidence_item_type`` is ``None`` the ``extensions`` block is
    omitted entirely, producing an instance that fails validation now that
    ``extensions`` is required. ``judgment_basis`` (P1-2, an INDEPENDENT
    sibling axis of ``evidence_item_type``) defaults to ``"measured"`` so
    existing P1-1 call sites keep validating now that it too is required.
    """

    text = "The lab reported a hemoglobin of 9.2 g/dL for the observed cohort."
    instance: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "source_assertion",
        "assertion_version": 1,
        "source_edition_id": "sed_" + "e" * 64,
        "passage_id": "psg_" + "f" * 64,
        "assertion_text": text,
        "assertion_text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "qualifiers": {"population": "pediatric"},
        "qualifier_extensions": {},
        "extraction_provenance": {
            "extractor": "p1_1_fixture",
            "schema_version": "1.0",
            "observed_at": "2026-07-21T00:00:00Z",
        },
        "lifecycle_state": "eligible",
        "identity": {
            "algorithm": "sha256-canonical-json-v1",
            "fingerprint": "",
            "material_fields": list(SOURCE_ASSERTION_MATERIAL_FIELDS),
        },
    }
    if evidence_item_type is not None:
        instance["extensions"] = {
            "evidence_taxonomy": {
                "evidence_item_type": evidence_item_type,
                "judgment_basis": judgment_basis,
            },
        }
    instance["identity"]["fingerprint"] = source_assertion_fingerprint(instance)
    instance["assertion_id"] = source_assertion_id(instance)
    return instance


def test_source_assertion_valid_instance_with_evidence_item_type() -> None:
    """A fully-populated ``source_assertion`` instance with
    ``evidence_item_type: observed_finding`` validates against the full
    Draft 2020-12 schema (all other required fields populated realistically).
    """

    instance = _p1_1_source_assertion_instance(evidence_item_type="observed_finding")

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors == [], f"expected a valid source_assertion instance, got: {errors}"

    result = validate(instance, "source_assertion")
    assert result.ok, f"expected validate() success, got: {result.errors}"
    assert result.errors == []


def test_source_assertion_missing_evidence_item_type_fails_draft202012() -> None:
    """A ``source_assertion`` instance omitting ``extensions`` entirely fails
    validation now that the block (and its ``evidence_item_type`` leaf) is
    REQUIRED — pre-existing instances that predate P1-1 no longer validate
    as-is without the field.
    """

    instance = _p1_1_source_assertion_instance(evidence_item_type=None)
    assert "extensions" not in instance

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors, "expected validation errors for a missing `extensions` block"

    result = validate(instance, "source_assertion")
    assert not result.ok
    assert result.errors


# ---------------------------------------------------------------------------
# P1-2: source_assertion.schema.yaml — `extensions.evidence_taxonomy.
# judgment_basis` required sibling enum (decisions-block §9.1 / OQ-RF-2).
# `judgment_basis` is an INDEPENDENT axis from `evidence_item_type` — never
# derived from it. P1-4 (below): proves `evidence_item_type: other` remains
# a valid, complete instance and that the extensibility contract is
# documented on the schema.
# ---------------------------------------------------------------------------

_JUDGMENT_BASIS_MEMBERS = [
    "measured",
    "derived_from_measured",
    "expert_judgment",
    "mixed",
    "unassessed",
]


def test_source_assertion_extensions_judgment_basis_is_required_and_reachable() -> None:
    """``extensions.evidence_taxonomy.judgment_basis`` is a required,
    reachable enum field on ``source_assertion``, declared as a sibling of
    ``evidence_item_type`` inside the same ``evidence_taxonomy`` block (never
    nested under/through ``rights_extension``, and never derived from
    ``evidence_item_type``)."""

    schema = SchemaRegistry().get("source_assertion")
    extensions_schema = schema["properties"]["extensions"]
    taxonomy_schema = extensions_schema["properties"]["evidence_taxonomy"]

    required = taxonomy_schema.get("required", [])
    assert "evidence_item_type" in required
    assert "judgment_basis" in required, (
        "judgment_basis must be required alongside evidence_item_type in "
        "extensions.evidence_taxonomy"
    )

    judgment_basis_schema = taxonomy_schema["properties"]["judgment_basis"]
    assert judgment_basis_schema["enum"] == _JUDGMENT_BASIS_MEMBERS


def test_source_assertion_judgment_basis_not_reachable_via_rights_extension() -> None:
    """Positive counterpart to the P0-2 negative-space guard, extended to
    ``judgment_basis``: it must stay unreachable via any
    ``rights_extension``-rooted schema path, from either direction."""

    rights_extension_schema = SchemaRegistry().get("rights_extension")
    property_names = _collect_property_names(rights_extension_schema)
    overlap = property_names & _FORBIDDEN_EVIDENCE_TAXONOMY_FIELD_NAMES
    assert not overlap, (
        "rights_extension.schema.yaml must not gain evidence-taxonomy fields "
        f"(including judgment_basis); found: {sorted(overlap)}"
    )


def test_source_assertion_valid_instance_with_judgment_basis() -> None:
    """A fully-populated ``source_assertion`` instance with both
    ``evidence_item_type`` and a ``judgment_basis`` member validates against
    the full Draft 2020-12 schema."""

    for member in _JUDGMENT_BASIS_MEMBERS:
        instance = _p1_1_source_assertion_instance(
            evidence_item_type="observed_finding", judgment_basis=member
        )

        schema = SchemaRegistry().get("source_assertion")
        validator = jsonschema.Draft202012Validator(schema)
        errors = list(validator.iter_errors(instance))
        assert errors == [], (
            f"expected a valid source_assertion instance for judgment_basis="
            f"{member!r}, got: {errors}"
        )

        result = validate(instance, "source_assertion")
        assert result.ok, f"expected validate() success, got: {result.errors}"


def test_source_assertion_missing_judgment_basis_fails_draft202012() -> None:
    """An ``extensions.evidence_taxonomy`` block that supplies
    ``evidence_item_type`` but omits ``judgment_basis`` fails validation now
    that ``judgment_basis`` is REQUIRED — the two axes are independent, so
    ``evidence_item_type`` alone is no longer a complete block."""

    instance = _p1_1_source_assertion_instance(evidence_item_type="observed_finding")
    del instance["extensions"]["evidence_taxonomy"]["judgment_basis"]
    instance["identity"]["fingerprint"] = source_assertion_fingerprint(instance)
    instance["assertion_id"] = source_assertion_id(instance)

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors, "expected validation errors for a missing `judgment_basis` leaf"

    result = validate(instance, "source_assertion")
    assert not result.ok
    assert result.errors


def test_source_assertion_evidence_item_type_other_is_a_valid_complete_instance() -> None:
    """P1-4 (OQ-RF-2): ``evidence_item_type: other`` — the domain-extension
    escape hatch — validates successfully as a complete, valid
    ``source_assertion`` instance when paired with any valid
    ``judgment_basis`` member. Proves ``other`` is a first-class enum member,
    not merely tolerated."""

    instance = _p1_1_source_assertion_instance(
        evidence_item_type="other", judgment_basis="unassessed"
    )

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors == [], f"expected `other` to validate as a complete instance, got: {errors}"

    result = validate(instance, "source_assertion")
    assert result.ok, f"expected validate() success for `other`, got: {result.errors}"
    assert result.errors == []


def test_source_assertion_evidence_item_type_documents_extensibility_contract() -> None:
    """P1-4: the schema ``description`` on ``evidence_item_type`` must state
    the extensibility contract explicitly — domain-extensible (not a closed
    clinical list), ``other`` is an intentional escape hatch, and a future
    domain (e.g. an Evidence-Foundry) is expected to specialize this axis
    rather than replace it."""

    schema = SchemaRegistry().get("source_assertion")
    taxonomy_schema = schema["properties"]["extensions"]["properties"]["evidence_taxonomy"]
    description = taxonomy_schema["properties"]["evidence_item_type"].get("description", "")

    assert "other" in description, "description must name `other` as the escape hatch"
    assert "extension point" in description or "escape hatch" in description
    assert "specialize" in description, (
        "description must state a future domain schema specializes this "
        "taxonomy rather than replacing it"
    )
    assert "closed clinical list" in description or "not a closed" in description, (
        "description must disclaim a closed clinical-only list"
    )


# ---------------------------------------------------------------------------
# P2-1: source_card.schema.yaml — `rights_summary` mirror (AC P2-A attach
# point 1 of 2; P2-2 applies the identical shape to source_assertion,
# byte-identical per P6-1). Denormalized, NON-AUTHORITATIVE mirror of
# rights_record.schema.yaml (+ rights_extension.clearance_status).
# ---------------------------------------------------------------------------


def _source_card_base() -> dict[str, Any]:
    return {
        "source_card_id": "src_p2_1_demo",
        "type": "source_card",
        "source": {"title": "P2-1 Demo Source"},
    }


def _all_unknown_rights_summary() -> dict[str, Any]:
    return {
        "mirror_of_record_id": None,
        "mirror_derived_at": None,
        "mirror_is_authoritative": False,
        "rights_record_ids": [],
        "reuse_assessment_ids": [],
        "permission_record_ids": [],
        "copyright_status": "unknown",
        "access_basis": "unknown",
        "restrictions": {
            "incorporation_into_other_products": "unknown",
            "adaptation": "unknown",
            "commercial_use": "unknown",
            "redistribution": "unknown",
            "bulk_retrieval": "unknown",
            "model_training": "unknown",
        },
        "clearance_status": "UNKNOWN",
        "review_status": "unknown",
    }


def test_source_card_rights_summary_absent_is_valid() -> None:
    """AC (P2-A resilience): a source_card missing `rights_summary` entirely
    (pre-migration legacy instance) is NOT a validation failure — the P2-5
    backfill migration is the mechanism that brings it into compliance, not
    the schema."""

    result = validate(_source_card_base(), "source_card")
    assert result.ok, f"expected source_card without rights_summary to validate, got: {result.errors}"


def test_source_card_rights_summary_all_unknown_is_valid() -> None:
    """P2-1 AC 4: a fully-`unknown`/all-default mirror (empty
    `rights_record_ids`, every status/restriction field `unknown`) is VALID
    — this is the exact shape the P2-5 backfill will produce."""

    instance = _source_card_base()
    instance["rights_summary"] = _all_unknown_rights_summary()
    result = validate(instance, "source_card")
    assert result.ok, f"expected all-unknown rights_summary to validate, got: {result.errors}"
    assert result.errors == []


def test_source_card_rights_summary_link_before_assert_status_field_fails_without_record_ids() -> None:
    """P2-1 AC 2: a non-`unknown` `access_basis` with empty `rights_record_ids`
    FAILS validation — the link-before-assert invariant. A mirror asserting a
    specific rights posture must point back to the rights_record(s) it was
    derived from."""

    instance = _source_card_base()
    instance["rights_summary"] = {"access_basis": "public_web", "rights_record_ids": []}
    result = validate(instance, "source_card")
    assert not result.ok, "expected validation failure: non-unknown access_basis with no linked rights_record"
    assert result.errors


def test_source_card_rights_summary_link_before_assert_restriction_subfield_fails_without_record_ids() -> None:
    """P2-1 AC 2 (restriction sub-field variant): a non-`unknown` value on any
    `restrictions` sub-field, with empty `rights_record_ids`, also fails —
    the invariant applies across every status/restriction field, not just
    the top-level status fields."""

    instance = _source_card_base()
    instance["rights_summary"] = {
        "restrictions": {"commercial_use": "prohibited"},
        "rights_record_ids": [],
    }
    result = validate(instance, "source_card")
    assert not result.ok, "expected validation failure: non-unknown restrictions.commercial_use with no linked rights_record"
    assert result.errors


def test_source_card_rights_summary_link_before_assert_passes_with_record_ids() -> None:
    """Positive counterpart: the same non-`unknown` `access_basis` validates
    cleanly once `rights_record_ids` is non-empty — the invariant gates on
    presence of a link, not on the specific status value."""

    instance = _source_card_base()
    instance["rights_summary"] = {"access_basis": "public_web", "rights_record_ids": ["RR-DEMO-001"]}
    result = validate(instance, "source_card")
    assert result.ok, f"expected linked access_basis to validate, got: {result.errors}"


def test_source_card_rights_summary_mirror_is_authoritative_const_false_rejects_true() -> None:
    """P2-1 AC 3: `mirror_is_authoritative` is schema-pinned `const: false` —
    a hard governance invariant. No fixture may set it to `true`."""

    instance = _source_card_base()
    instance["rights_summary"] = {"mirror_is_authoritative": True}
    result = validate(instance, "source_card")
    assert not result.ok, "expected validation failure: mirror_is_authoritative must never be true"
    assert result.errors


def test_source_card_rights_summary_mirror_is_authoritative_const_false_accepts_false() -> None:
    """Positive counterpart: `mirror_is_authoritative: false` is the only
    permitted value and validates cleanly."""

    instance = _source_card_base()
    instance["rights_summary"] = {"mirror_is_authoritative": False}
    result = validate(instance, "source_card")
    assert result.ok, f"expected mirror_is_authoritative: false to validate, got: {result.errors}"


def test_source_card_rights_summary_rejects_additional_properties() -> None:
    """Strict-family guard: `rights_summary` follows the rights-substrate
    internal convention (`additionalProperties: false`) even though
    `source_card.schema.yaml` itself remains additionalProperties: true at
    the top level — an unknown field nested inside `rights_summary` must
    still fail validation."""

    instance = _source_card_base()
    instance["rights_summary"] = {**_all_unknown_rights_summary(), "unexpected_field": "nope"}
    result = validate(instance, "source_card")
    assert not result.ok, "expected additionalProperties:false to reject an unknown rights_summary field"
    assert result.errors


def test_source_card_rights_summary_valid_instance_passes_draft202012() -> None:
    """Direct Draft202012Validator check (matching the file's other
    dedicated-fixture tests) over a fully-populated, all-unknown
    rights_summary instance."""

    schema = SchemaRegistry().get("source_card")
    validator = jsonschema.Draft202012Validator(schema)
    instance = _source_card_base()
    instance["rights_summary"] = _all_unknown_rights_summary()
    errors = list(validator.iter_errors(instance))
    assert not errors, [e.message for e in errors]


# ---------------------------------------------------------------------------
# P2-2: source_assertion.schema.yaml — `rights_summary` mirror (AC P2-A
# attach point 2 of 2). Byte-identical field shape to source_card.schema.
# yaml's `rights_summary` (P2-1), attached at the SAME top-level nesting
# depth as `extensions` (NOT nested under `extensions.evidence_taxonomy` —
# rights and evidence-quality are independent axes per §9.1, and
# `rights_summary` is a third, separate top-level concern).
# ---------------------------------------------------------------------------


def _source_assertion_with_rights_summary(
    rights_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a fully-populated ``source_assertion`` instance (via the P1-1
    helper, which already satisfies the required ``extensions`` block) and
    attach ``rights_summary`` at the top level when provided."""

    instance = _p1_1_source_assertion_instance(evidence_item_type="observed_finding")
    if rights_summary is not None:
        instance["rights_summary"] = rights_summary
    return instance


def test_source_assertion_rights_summary_absent_is_valid() -> None:
    """AC (P2-A resilience, mirrors P2-1): a source_assertion missing
    `rights_summary` entirely (pre-migration legacy instance) is NOT a
    validation failure — the P2-5 backfill migration is the mechanism that
    brings it into compliance, not the schema."""

    instance = _source_assertion_with_rights_summary(None)
    result = validate(instance, "source_assertion")
    assert result.ok, f"expected source_assertion without rights_summary to validate, got: {result.errors}"


def test_source_assertion_rights_summary_all_unknown_is_valid() -> None:
    """AC 4: a fully-`unknown`/all-default mirror (empty `rights_record_ids`,
    every status/restriction field `unknown`) is VALID — the exact shape the
    P2-5 backfill will produce."""

    instance = _source_assertion_with_rights_summary(_all_unknown_rights_summary())
    result = validate(instance, "source_assertion")
    assert result.ok, f"expected all-unknown rights_summary to validate, got: {result.errors}"
    assert result.errors == []


def test_source_assertion_rights_summary_link_before_assert_status_field_fails_without_record_ids() -> None:
    """AC 2: a non-`unknown` `access_basis` with empty `rights_record_ids`
    FAILS validation — the link-before-assert invariant, identical to
    source_card's P2-1 behavior."""

    instance = _source_assertion_with_rights_summary(
        {"access_basis": "public_web", "rights_record_ids": []}
    )
    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: non-unknown access_basis with no linked rights_record"
    assert result.errors


def test_source_assertion_rights_summary_link_before_assert_restriction_subfield_fails_without_record_ids() -> None:
    """AC 2 (restriction sub-field variant): a non-`unknown` value on any
    `restrictions` sub-field, with empty `rights_record_ids`, also fails."""

    instance = _source_assertion_with_rights_summary(
        {
            "restrictions": {"commercial_use": "prohibited"},
            "rights_record_ids": [],
        }
    )
    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: non-unknown restrictions.commercial_use with no linked rights_record"
    assert result.errors


def test_source_assertion_rights_summary_link_before_assert_passes_with_record_ids() -> None:
    """Positive counterpart: the same non-`unknown` `access_basis` validates
    cleanly once `rights_record_ids` is non-empty."""

    instance = _source_assertion_with_rights_summary(
        {"access_basis": "public_web", "rights_record_ids": ["RR-DEMO-001"]}
    )
    result = validate(instance, "source_assertion")
    assert result.ok, f"expected linked access_basis to validate, got: {result.errors}"


def test_source_assertion_rights_summary_mirror_is_authoritative_const_false_rejects_true() -> None:
    """AC 3: `mirror_is_authoritative` is schema-pinned `const: false` — a
    hard governance invariant. No fixture may set it to `true`."""

    instance = _source_assertion_with_rights_summary({"mirror_is_authoritative": True})
    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: mirror_is_authoritative must never be true"
    assert result.errors


def test_source_assertion_rights_summary_mirror_is_authoritative_const_false_accepts_false() -> None:
    """Positive counterpart: `mirror_is_authoritative: false` is the only
    permitted value and validates cleanly."""

    instance = _source_assertion_with_rights_summary({"mirror_is_authoritative": False})
    result = validate(instance, "source_assertion")
    assert result.ok, f"expected mirror_is_authoritative: false to validate, got: {result.errors}"


def test_source_assertion_rights_summary_rejects_additional_properties() -> None:
    """Strict-family guard: `rights_summary` follows the rights-substrate
    internal convention (`additionalProperties: false`) — an unknown field
    nested inside `rights_summary` must still fail validation, even though
    the source_card variant's parent document stays additionalProperties:
    true while source_assertion's parent document is additionalProperties:
    false (both agree on `rights_summary` itself being closed)."""

    instance = _source_assertion_with_rights_summary(
        {**_all_unknown_rights_summary(), "unexpected_field": "nope"}
    )
    result = validate(instance, "source_assertion")
    assert not result.ok, "expected additionalProperties:false to reject an unknown rights_summary field"
    assert result.errors


def test_source_assertion_rights_summary_valid_instance_passes_draft202012() -> None:
    """Direct Draft202012Validator check (AC 1) over a fully-populated,
    all-unknown rights_summary instance."""

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    instance = _source_assertion_with_rights_summary(_all_unknown_rights_summary())
    errors = list(validator.iter_errors(instance))
    assert not errors, [e.message for e in errors]


def _rights_summary_field_name_set(rights_summary_schema: dict[str, Any]) -> set[str]:
    """Flatten a `rights_summary` schema's property names into a single
    comparable set: top-level property names plus `restrictions`' nested
    sub-object property names (prefixed to avoid accidental collisions)."""

    top_level = set(rights_summary_schema["properties"].keys())
    restrictions_props = set(
        rights_summary_schema["properties"]["restrictions"]["properties"].keys()
    )
    return top_level | {f"restrictions.{name}" for name in restrictions_props}


def test_rights_summary_field_set_identical_between_source_card_and_source_assertion() -> None:
    """AC 5 (P2-A propagation-contract check, feeds P6-1's full consistency
    sweep): `source_card.schema.yaml`'s `rights_summary` property's field
    name SET (property names + `restrictions` sub-object property names)
    must be IDENTICAL to `source_assertion.schema.yaml`'s `rights_summary`
    field name set. A divergence here means P2-1 and P2-2 drifted out of
    byte-identical shape and must be reconciled before P6-1's sweep runs."""

    card_schema = SchemaRegistry().get("source_card")
    assertion_schema = SchemaRegistry().get("source_assertion")

    card_fields = _rights_summary_field_name_set(card_schema["properties"]["rights_summary"])
    assertion_fields = _rights_summary_field_name_set(
        assertion_schema["properties"]["rights_summary"]
    )

    assert card_fields == assertion_fields, (
        "source_card and source_assertion rights_summary field sets diverged: "
        f"only in source_card={sorted(card_fields - assertion_fields)}, "
        f"only in source_assertion={sorted(assertion_fields - card_fields)}"
    )


# ---------------------------------------------------------------------------
# P3-1 / P3-2: source_assertion.schema.yaml — conditional `synthesis` object
# and nullable `source_edition_id`/`passage_id` for `derived_synthesis`
# instances (decisions-block §9 Risk 3). `synthesis.input_refs` records which
# prior source_assertion instances fed a derived-synthesis value and how each
# one contributed; `source_edition_id`/`passage_id` may only go null when the
# assertion IS a derived_synthesis (it has no single source edition/passage
# of its own) — every other `evidence_item_type` keeps both fields required
# AND non-null, which the negative-branch tests below guard against
# regressing.
# ---------------------------------------------------------------------------

_VALID_SYNTHESIS_INPUT_REFS = [
    {"source_assertion_id": "ast_" + "a" * 64, "contribution": "anchor"},
    {"source_assertion_id": "ast_" + "b" * 64, "contribution": "corroborating"},
]


def _valid_synthesis_block() -> dict[str, Any]:
    return {
        "input_refs": [dict(ref) for ref in _VALID_SYNTHESIS_INPUT_REFS],
        "method": "weighted_average_of_anchor_and_corroborating",
        "reproduces_source_arrangement": False,
    }


def _p3_source_assertion_instance(
    *,
    evidence_item_type: str,
    source_edition_id: str | None = "sed_" + "e" * 64,
    passage_id: str | None = "psg_" + "f" * 64,
    synthesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """P3-1/P3-2 fixture builder: start from the P1-1 base instance, then
    override `source_edition_id`/`passage_id` (identity-material fields) and
    optionally attach `synthesis`, recomputing `identity`/`assertion_id`
    afterward so the fixture stays self-consistent."""

    instance = _p1_1_source_assertion_instance(evidence_item_type=evidence_item_type)
    instance["source_edition_id"] = source_edition_id
    instance["passage_id"] = passage_id
    if synthesis is not None:
        instance["synthesis"] = synthesis
    instance["identity"]["fingerprint"] = source_assertion_fingerprint(instance)
    instance["assertion_id"] = source_assertion_id(instance)
    return instance


def test_source_assertion_synthesis_valid_instance_with_two_input_refs_passes_draft202012() -> None:
    """P3-1 AC (a): a `derived_synthesis` instance with a `synthesis` block
    carrying 2 `input_refs` (the `minItems` floor) — plus `method` and
    `reproduces_source_arrangement`, both required by the `then` branch —
    validates cleanly, with both `source_edition_id`/`passage_id` null."""

    instance = _p3_source_assertion_instance(
        evidence_item_type="derived_synthesis",
        source_edition_id=None,
        passage_id=None,
        synthesis=_valid_synthesis_block(),
    )

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors == [], f"expected a valid derived_synthesis instance, got: {errors}"

    result = validate(instance, "source_assertion")
    assert result.ok, f"expected validate() success, got: {result.errors}"
    assert result.errors == []


def test_source_assertion_synthesis_single_input_ref_fails_min_items() -> None:
    """P3-1 AC (b): `synthesis.input_refs` with only 1 entry fails the
    `minItems: 2` floor — a synthesis must combine at least two prior
    assertions to count as a synthesis rather than a simple restatement."""

    synthesis = _valid_synthesis_block()
    synthesis["input_refs"] = [dict(_VALID_SYNTHESIS_INPUT_REFS[0])]
    instance = _p3_source_assertion_instance(
        evidence_item_type="derived_synthesis",
        source_edition_id=None,
        passage_id=None,
        synthesis=synthesis,
    )

    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure for a single input_ref (minItems: 2)"
    assert result.errors


def test_source_assertion_non_synthesis_instance_without_synthesis_object_is_valid() -> None:
    """P3-1 AC (c) (critical negative-branch test): an `observed_finding`
    instance carrying NO `synthesis` object at all still validates — the
    `derived_synthesis` conditional must not misfire on non-synthesis
    assertions and force a `synthesis` block onto them."""

    instance = _p3_source_assertion_instance(evidence_item_type="observed_finding")
    assert "synthesis" not in instance

    result = validate(instance, "source_assertion")
    assert result.ok, (
        f"expected non-synthesis instance without `synthesis` to validate, got: {result.errors}"
    )
    assert result.errors == []


def test_source_assertion_derived_synthesis_missing_synthesis_object_fails() -> None:
    """Regression guard on the `then` linkage itself: a `derived_synthesis`
    instance that omits `synthesis` entirely fails — proves the P3-1
    conditional actually fires (i.e. is not vacuously true) for the
    `derived_synthesis` branch."""

    instance = _p3_source_assertion_instance(
        evidence_item_type="derived_synthesis",
        source_edition_id=None,
        passage_id=None,
        synthesis=None,
    )
    assert "synthesis" not in instance

    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: derived_synthesis without a synthesis block"
    assert result.errors


def test_source_assertion_derived_synthesis_nullable_source_edition_and_passage_ids_valid() -> None:
    """P3-2 AC (a): a `derived_synthesis` instance with BOTH
    `source_edition_id` and `passage_id` set to `null` validates — a
    synthesis is computed from other assertions, not read from one passage,
    so it has no single source edition/passage of its own."""

    instance = _p3_source_assertion_instance(
        evidence_item_type="derived_synthesis",
        source_edition_id=None,
        passage_id=None,
        synthesis=_valid_synthesis_block(),
    )
    assert instance["source_edition_id"] is None
    assert instance["passage_id"] is None

    schema = SchemaRegistry().get("source_assertion")
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert errors == [], (
        f"expected null source_edition_id/passage_id to validate for derived_synthesis, got: {errors}"
    )

    result = validate(instance, "source_assertion")
    assert result.ok, f"expected validate() success, got: {result.errors}"


def test_source_assertion_non_synthesis_null_source_edition_id_fails() -> None:
    """P3-2 AC (b), field 1 (regression guard): a non-synthesis instance
    (`observed_finding`) with `source_edition_id: null` FAILS — the
    conditional must not loosen the always-required-and-non-null constraint
    for any evidence type other than `derived_synthesis`."""

    instance = _p3_source_assertion_instance(
        evidence_item_type="observed_finding",
        source_edition_id=None,
    )

    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: non-synthesis instance with null source_edition_id"
    assert result.errors


def test_source_assertion_non_synthesis_null_passage_id_fails() -> None:
    """P3-2 AC (b), field 2 (regression guard): a non-synthesis instance
    (`observed_finding`) with `passage_id: null` FAILS — same regression
    guard as above, for the sibling field."""

    instance = _p3_source_assertion_instance(
        evidence_item_type="observed_finding",
        passage_id=None,
    )

    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: non-synthesis instance with null passage_id"
    assert result.errors


# ---------------------------------------------------------------------------
# P4-4: source_card.schema.yaml / source_assertion.schema.yaml —
# `substitutability` (fix-cycle 1, karen review). Top-level sibling of
# `rights_summary`, populated by services/rights_triage.py::
# maybe_assess_substitutability (wired into ingest_source /
# AssertionMaterializer._prepare_one). Regression guard for the fix-cycle 1
# indentation bug: `source_card.schema.yaml` originally declared
# `substitutability` as a 0-indent SIBLING of `properties`/`required` instead
# of nested INSIDE `properties` — a stray root-level key silently ignored by
# every JSON Schema validator (unknown keywords are simply not applied), so
# invalid `substitutability` content would have validated cleanly. The tests
# below prove both reachability (structural) and enforcement (content).
# ---------------------------------------------------------------------------


def _valid_substitutability() -> dict[str, Any]:
    return {
        "searched_at": "2026-07-21T00:00:00Z",
        "status": "no_substitute_found",
        "candidate_source_ids": [],
        "coverage_notes": "No corpus candidates matched.",
    }


def test_source_card_substitutability_reachable_under_properties() -> None:
    """Structural regression guard for the fix-cycle 1 schema bug:
    `substitutability` must be declared INSIDE `properties` (reachable,
    validated), never as a stray root-level sibling of `properties`/
    `required` (silently ignored by any JSON Schema validator)."""

    schema = SchemaRegistry().get("source_card")
    assert "substitutability" in schema["properties"], (
        "source_card.schema.yaml's `substitutability` must be nested inside "
        "`properties` — found it missing/unreachable there"
    )
    assert "substitutability" not in schema, (
        "substitutability must not ALSO be declared as a stray root-level "
        "key (the fix-cycle 1 indentation bug)"
    )


def test_source_card_substitutability_valid_instance_passes() -> None:
    """A fully-populated, well-formed `substitutability` block validates."""

    instance = _source_card_base()
    instance["substitutability"] = _valid_substitutability()
    result = validate(instance, "source_card")
    assert result.ok, f"expected valid substitutability to validate, got: {result.errors}"
    assert result.errors == []


def test_source_card_substitutability_null_is_valid() -> None:
    """`substitutability: null` (no assessment recorded yet) is valid."""

    instance = _source_card_base()
    instance["substitutability"] = None
    result = validate(instance, "source_card")
    assert result.ok, f"expected null substitutability to validate, got: {result.errors}"


def test_source_card_substitutability_missing_required_field_fails() -> None:
    """Content-enforcement regression guard: before the fix-cycle 1 schema
    fix, `substitutability` was an unreachable root-level key, so ANY content
    — including one missing a required field — validated, because nothing
    was ever checking it. This proves the fix wires real enforcement, not
    merely a `yaml.safe_load`-level smoke check."""

    instance = _source_card_base()
    substitutability = _valid_substitutability()
    del substitutability["status"]
    instance["substitutability"] = substitutability
    result = validate(instance, "source_card")
    assert not result.ok, "expected validation failure: substitutability missing required `status`"
    assert result.errors


def test_source_card_substitutability_rejects_additional_properties() -> None:
    """Strict-family guard: an unknown field nested inside `substitutability`
    must fail validation."""

    instance = _source_card_base()
    instance["substitutability"] = {**_valid_substitutability(), "unexpected_field": "nope"}
    result = validate(instance, "source_card")
    assert not result.ok, "expected additionalProperties:false to reject an unknown substitutability field"
    assert result.errors


def test_source_assertion_substitutability_reachable_under_properties() -> None:
    """Structural counterpart for source_assertion.schema.yaml (reportedly
    correct at fix-cycle time; verified here rather than merely trusted)."""

    schema = SchemaRegistry().get("source_assertion")
    assert "substitutability" in schema["properties"], (
        "source_assertion.schema.yaml's `substitutability` must be nested "
        "inside `properties`"
    )
    assert "substitutability" not in schema


def test_source_assertion_substitutability_valid_instance_passes() -> None:
    instance = _source_assertion_with_rights_summary(None)
    instance["substitutability"] = _valid_substitutability()
    result = validate(instance, "source_assertion")
    assert result.ok, f"expected valid substitutability to validate, got: {result.errors}"


def test_source_assertion_substitutability_missing_required_field_fails() -> None:
    instance = _source_assertion_with_rights_summary(None)
    substitutability = _valid_substitutability()
    del substitutability["candidate_source_ids"]
    instance["substitutability"] = substitutability
    result = validate(instance, "source_assertion")
    assert not result.ok, "expected validation failure: substitutability missing required `candidate_source_ids`"
    assert result.errors


def test_substitutability_field_set_identical_between_source_card_and_source_assertion() -> None:
    """Propagation-contract check (mirrors the P2-A `rights_summary` field-set
    identity test): the `substitutability` property name SET must be
    identical between both schemas."""

    card_schema = SchemaRegistry().get("source_card")
    assertion_schema = SchemaRegistry().get("source_assertion")

    card_fields = set(card_schema["properties"]["substitutability"]["properties"].keys())
    assertion_fields = set(assertion_schema["properties"]["substitutability"]["properties"].keys())

    assert card_fields == assertion_fields, (
        "source_card and source_assertion substitutability field sets diverged: "
        f"only in source_card={sorted(card_fields - assertion_fields)}, "
        f"only in source_assertion={sorted(assertion_fields - card_fields)}"
    )


# ---------------------------------------------------------------------------
# P6-5 (§9.9 moot-determination note, auditability record — no test emitted):
# §9.9's role-string-in-reviewer-field defect (found in a legacy pediatric-repo's
# *vendored JSON example files*) is MOOT for RF — RF ports schema *structure*
# only (this module's fixtures) and never vendored that legacy repo's JSON
# example files themselves, so there is no RF-side instance of that defect to
# correct.
# ---------------------------------------------------------------------------
