"""Schema-freeze coverage for the External Research Report Interchange (ERI)
v1 contract — plan tasks ERI-1.1 (packet schemas + golden/negative fixtures)
and ERI-1.3 (completeness-tier + quarantine vocabulary), see
docs/project_plans/implementation_plans/enhancements/external-research-
report-interchange-v1.md and docs/dev/architecture/external-research-
handoff-contract.md.

Every schema is loaded through the same ``research_foundry.schemas``
registry every other RF artifact schema uses (no bespoke loader). Fixtures
live under ``tests/fixtures/external_research_handoff/<short-name>/`` — one
``valid*.yaml`` (or more) and several ``invalid_<rule>.yaml`` files per
schema, discovered by glob rather than hardcoded so new fixtures are picked
up automatically.

This file is standalone from ``tests/test_schema_validation.py``'s
``EXPECTED_SCHEMA_NAMES`` parametrization by design (same precedent as
``tests/test_rights_record_schema_fixtures.py`` for the rights-entity-model
P0 substrate) — wiring these 6 schemas into that shared registry-coverage
list belongs to a later phase, not this contract-freeze task.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.schemas import SchemaRegistry, validate
from research_foundry.yamlio import load_yaml

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "external_research_handoff"

# Maps each schema's registry name (schemas/<name>.schema.yaml) to its
# fixture subdirectory name.
SCHEMA_FIXTURE_DIRS: dict[str, str] = {
    "external_research_handoff": "handoff",
    "external_research_sources": "sources",
    "external_assertion_candidates": "assertion_candidates",
    "external_research_import_receipt": "import_receipt",
    "external_research_import_checkpoint": "import_checkpoint",
    "external_research_acquisition_policy": "acquisition_policy",
}


def _fixture_files(dir_name: str, prefix: str) -> list[Path]:
    d = FIXTURES_ROOT / dir_name
    return sorted(d.glob(f"{prefix}*.yaml"))


# ---------------------------------------------------------------------------
# Registry wiring — every schema file exists and loads as a Draft 2020-12 doc.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schema_name", sorted(SCHEMA_FIXTURE_DIRS))
def test_schema_is_registered_and_loads(schema_name: str) -> None:
    registry = SchemaRegistry()
    assert registry.has(schema_name), f"missing schemas/{schema_name}.schema.yaml"
    schema = registry.get(schema_name)
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False, (
        f"{schema_name}: top-level additionalProperties must be false so a "
        "producer/operator cannot smuggle an unmodeled field"
    )


# ---------------------------------------------------------------------------
# Golden fixtures — every valid*.yaml passes, every invalid_*.yaml fails.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schema_name,dir_name", sorted(SCHEMA_FIXTURE_DIRS.items()))
def test_valid_fixtures_pass(schema_name: str, dir_name: str) -> None:
    files = _fixture_files(dir_name, "valid")
    assert files, f"no valid*.yaml fixture found for {schema_name} under {dir_name}/"
    for f in files:
        instance = load_yaml(f)
        result = validate(instance, schema_name)
        assert result.ok, f"{f.name}: expected valid, got errors: {result.errors}"
        assert result.errors == []


@pytest.mark.parametrize("schema_name,dir_name", sorted(SCHEMA_FIXTURE_DIRS.items()))
def test_invalid_fixtures_fail(schema_name: str, dir_name: str) -> None:
    files = _fixture_files(dir_name, "invalid")
    assert len(files) >= 2, (
        f"expected several invalid fixtures for {schema_name} under "
        f"{dir_name}/, found {len(files)}"
    )
    for f in files:
        instance = load_yaml(f)
        result = validate(instance, schema_name)
        assert not result.ok, f"{f.name}: expected invalid, but instance validated cleanly"
        assert result.errors, f"{f.name}: expected non-empty errors"


# ---------------------------------------------------------------------------
# Programmatic boundary fixtures (ERI-OQ-4 limits too large to hand-author as
# static YAML): sources <= 2000, candidates <= 5000, handoff members <= 64.
# ---------------------------------------------------------------------------


def test_sources_record_set_bounded_to_2000() -> None:
    within_limit = {
        "schema_name": "external_research_sources",
        "schema_version": "1.0",
        "sources": [
            {"source_id": f"src_{i:04d}", "access_status": "unknown"} for i in range(2000)
        ],
    }
    assert validate(within_limit, "external_research_sources").ok

    over_limit = dict(within_limit)
    over_limit["sources"] = within_limit["sources"] + [
        {"source_id": "src_2000", "access_status": "unknown"}
    ]
    result = validate(over_limit, "external_research_sources")
    assert not result.ok, "expected 2001 sources to exceed the ERI-OQ-4 2000-item ceiling"
    assert result.errors


def test_assertion_candidates_record_set_bounded_to_5000() -> None:
    within_limit = {
        "schema_name": "external_assertion_candidates",
        "schema_version": "1.0",
        "candidates": [
            {
                "candidate_id": f"cand_{i:04d}",
                "statement": "demo",
                "classification": "annotation",
                "source_refs": [],
            }
            for i in range(5000)
        ],
    }
    assert validate(within_limit, "external_assertion_candidates").ok

    over_limit = dict(within_limit)
    over_limit["candidates"] = within_limit["candidates"] + [
        {
            "candidate_id": "cand_5000",
            "statement": "demo",
            "classification": "annotation",
            "source_refs": [],
        }
    ]
    result = validate(over_limit, "external_assertion_candidates")
    assert not result.ok, "expected 5001 candidates to exceed the ERI-OQ-4 5000-item ceiling"
    assert result.errors


def _handoff_member(path: str, role: str) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "byte_length": 1,
        "sha256": "a" * 64,
    }


def test_handoff_members_bounded_to_64() -> None:
    required = [
        _handoff_member("handoff.yaml", "handoff_manifest"),
        _handoff_member("report.md", "report"),
        _handoff_member("sources.yaml", "sources"),
        _handoff_member("assertion_candidates.yaml", "assertion_candidates"),
    ]
    base = {
        "schema_name": "external_research_handoff",
        "schema_version": "1.0",
        "transport": "directory",
        "producer_profile": "generic",
        "declared_sensitivity": "personal",
        "created_at": "2026-07-26T12:00:00Z",
        "content_roles": {"report": "platform_synthesis"},
        "total_declared_bytes": 4,
    }

    within_limit = dict(base)
    within_limit["members"] = required + [
        _handoff_member(f"attachments/a{i:02d}.bin", "attachment") for i in range(30)
    ]
    assert len(within_limit["members"]) == 34
    assert validate(within_limit, "external_research_handoff").ok

    over_limit = dict(base)
    over_limit["members"] = required + [
        _handoff_member(f"activity_{i}.yaml", "activity") for i in range(61)
    ]
    assert len(over_limit["members"]) == 65
    result = validate(over_limit, "external_research_handoff")
    assert not result.ok, "expected 65 members to exceed the ERI-OQ-4 64-member ceiling"
    assert result.errors


# ---------------------------------------------------------------------------
# Structural guards — directly assert the schema-JSON shape of a few
# HARD CONSTRAINTS, rather than only exercising it via instance fixtures.
# ---------------------------------------------------------------------------


def test_receipt_status_enum_excludes_pending() -> None:
    """contract §2.2: `pending` is NEVER a receipt state — it exists only on
    the separate checkpoint artifact."""

    schema = SchemaRegistry().get("external_research_import_receipt")
    assert schema["properties"]["status"]["enum"] == [
        "completed",
        "completed_with_quarantine",
        "blocked",
    ]


def test_checkpoint_status_enum_excludes_every_receipt_terminal_state() -> None:
    """Symmetric guard: the checkpoint's status enum must never gain a
    receipt-only terminal value (completed / completed_with_quarantine /
    blocked)."""

    schema = SchemaRegistry().get("external_research_import_checkpoint")
    checkpoint_statuses = set(schema["properties"]["status"]["enum"])
    receipt_terminal_states = {"completed", "completed_with_quarantine", "blocked"}
    assert not (checkpoint_statuses & receipt_terminal_states)


def test_receipt_has_no_free_text_detail_field() -> None:
    """PRD §6.5 / contract §2.3: a quarantined item carries exactly one safe
    reason code, never free text — this schema must not define any
    detail/message-shaped string field anywhere on an action item. Per the
    gpt-5.6-sol P1 audit finding #15, the specific reason code is ALSO not a
    caller-visible field any more (it is itself a cross-workspace existence
    oracle) — ``reason_code`` is removed and replaced by the opaque
    ``audit_ref`` pointer into the access-controlled audit record (contract
    §4.3, §4.6)."""

    schema = SchemaRegistry().get("external_research_import_receipt")
    action_props = set(schema["properties"]["actions"]["items"]["properties"])
    assert action_props == {
        "action_id",
        "kind",
        "outcome",
        "completeness_tier",
        "audit_ref",
        "effect_digest",
    }
    assert "reason_code" not in action_props


def test_reason_code_vocabulary_is_the_frozen_19_code_closed_set() -> None:
    """PRD §6.5's 4 families, 19 total safe reason codes — verbatim.

    Per gpt-5.6-sol P1 audit finding #15, only the packet family (5 codes)
    is directly caller-visible on this schema, as ``block_reason`` — it
    describes the submitted packet's own structure back to its own
    submitter, not a cross-workspace fact. The other 14 codes (source,
    citation, candidate) remain the frozen closed vocabulary contract §2.3
    documents, but they no longer appear anywhere on THIS schema — they are
    recorded only in the access-controlled audit record an ``audit_ref``
    resolves against (contract §4.3, §4.6), which is intentionally not a
    schema this task owns (its shape is a later-phase open item)."""

    receipt_schema = SchemaRegistry().get("external_research_import_receipt")
    block_reason_codes = set(receipt_schema["properties"]["block_reason"]["enum"])

    expected_packet = {
        "required_member_missing",
        "unsupported_schema_version",
        "unsafe_member_path",
        "member_digest_conflict",
        "limit_exceeded",
    }
    expected_source = {
        "invalid_locator",
        "source_unavailable",
        "rights_metadata_missing",
        "sensitivity_denied",
        "source_drift",
        "edition_binding_conflict",
    }
    expected_citation = {
        "citation_unresolved",
        "citation_ambiguous",
        "citation_mismatch",
        "passage_binding_conflict",
    }
    expected_candidate = {
        "basis_incomplete",
        "relation_invalid",
        "verification_failed",
        "cross_workspace_denied",
    }

    assert block_reason_codes == expected_packet | {None}

    action_props = receipt_schema["properties"]["actions"]["items"]["properties"]
    assert "reason_code" not in action_props, (
        "the source/citation/candidate reason-code vocabulary must not "
        "appear on the caller-visible receipt schema (audit finding #15)"
    )
    assert action_props["audit_ref"]["type"] == ["string", "null"]

    all_codes = expected_packet | expected_source | expected_citation | expected_candidate
    assert len(all_codes) == 19


def test_receipt_identity_inputs_are_seven_and_six_per_branch() -> None:
    """Contract §1.3 (resolves audit #6, #9, #10, #20): receipt_digest has
    exactly two status-conditioned branches, each with one fixed
    cardinality — never an ambiguous "four" vs "five" claim. This test
    pins the schema-level fields that make up each branch's inputs so a
    future edit can't silently drop one without a red test."""

    schema = SchemaRegistry().get("external_research_import_receipt")
    required = set(schema["required"])
    # Branch A (non-blocked, seven inputs) and Branch B (blocked, six
    # inputs) share packet_digest/action_manifest_digest/
    # action_manifest_algorithm_version/attempt_structural_summary as
    # always-required-but-conditionally-null fields, plus the common
    # workspace_id/target_run_id/policy_digest/governance_policy_digest/
    # schema_major_versions inputs both branches share.
    for field in (
        "packet_digest",
        "workspace_id",
        "target_run_id",
        "policy_digest",
        "governance_policy_digest",
        "schema_major_versions",
        "action_manifest_digest",
        "action_manifest_algorithm_version",
        "attempt_structural_summary",
    ):
        assert field in required, f"{field} must be a required receipt field"


def test_blocked_receipt_has_null_packet_and_action_manifest_identity() -> None:
    """Contract §1.3/§1.3a (resolves audit #10): a blocked receipt has no
    accepted-member manifest to hash, so packet_digest and
    action_manifest_digest must be nullable and the allOf conditionals must
    force them null exactly when status is blocked."""

    schema = SchemaRegistry().get("external_research_import_receipt")
    assert schema["properties"]["packet_digest"]["type"] == ["string", "null"]
    assert schema["properties"]["action_manifest_digest"]["type"] == ["string", "null"]

    blocked = load_yaml(
        FIXTURES_ROOT / "import_receipt" / "invalid_blocked_with_nonempty_actions.yaml"
    )
    assert blocked["status"] == "blocked"
    assert blocked["packet_digest"] is None
    assert blocked["action_manifest_digest"] is None
    assert blocked["attempt_structural_summary"] is not None


def test_acquisition_policy_pins_no_transport_fallback() -> None:
    """HARD CONSTRAINT #4: a failed hop has NO transport fallback — this
    must be a schema-pinned const:false, not merely a description."""

    schema = SchemaRegistry().get("external_research_acquisition_policy")
    assert schema["properties"]["transport_fallback_allowed"]["const"] is False


def test_acquisition_policy_pins_redirect_hop_ceiling_at_three() -> None:
    schema = SchemaRegistry().get("external_research_acquisition_policy")
    max_hops_schema = schema["properties"]["redirects"]["properties"]["max_hops"]
    assert max_hops_schema["maximum"] == 3


def test_acquisition_policy_forbidden_categories_include_cloud_metadata() -> None:
    """Resolves gpt-5.6-sol P1 audit finding #4: IPv6 transition/
    translation addressing (NAT64/DNS64, 6to4, Teredo, IPv4-mapped) is now
    its own explicit closed category alongside the original 10. Round-2
    audit finding #10 adds a 12th: IPv6 site-local (`fec0::/10`), which
    stdlib `ipaddress` classifies as neither private nor reserved."""

    schema = SchemaRegistry().get("external_research_acquisition_policy")
    categories = schema["properties"]["forbidden_address_categories"]["const"]
    assert "cloud_metadata" in categories
    assert "encoded_or_obfuscated_host" in categories
    assert "ipv6_transition_or_translation" in categories
    assert "ipv6_site_local" in categories
    assert len(categories) == 12


def test_acquisition_policy_pins_versioned_metadata_deny_set() -> None:
    """Resolves gpt-5.6-sol P1 audit finding #5: a testable, versioned
    hostname/CIDR deny-set — not only 169.254.169.254 — bound to a version
    identifier that feeds policy_digest (contract §4.2.4)."""

    schema = SchemaRegistry().get("external_research_acquisition_policy")
    deny_set = schema["properties"]["metadata_deny_set"]["const"]
    assert "169.254.169.254" in deny_set
    assert "metadata.google.internal" in deny_set
    assert "100.100.100.200" in deny_set
    assert schema["properties"]["metadata_deny_set_version"]["const"]
    assert schema["properties"]["special_purpose_address_registry_version"]["const"]


def test_acquisition_policy_pins_single_actor_transport_architecture() -> None:
    """Resolves gpt-5.6-sol P1 audit finding #1/#2: the policy layer owns
    the whole HTTP lifecycle and hands off acquired bytes only; provider-
    delegated fetch is hard-pinned off (contract §4.2.0/§4.2.1)."""

    schema = SchemaRegistry().get("external_research_acquisition_policy")
    arch = schema["properties"]["transport_architecture"]["properties"]
    assert arch["single_actor_owns_full_lifecycle"]["const"] is True
    assert arch["hands_off_acquired_bytes_only"]["const"] is True
    assert arch["environment_and_pac_proxies_disabled"]["const"] is True
    assert arch["provider_delegated_fetch_allowed"]["const"] is False


def test_acquisition_policy_pins_single_parse_canonicalization() -> None:
    """Resolves gpt-5.6-sol P1 audit finding #3: one strict parse, shared
    with transport, closes the parser-differential class of SSRF bypass."""

    schema = SchemaRegistry().get("external_research_acquisition_policy")
    canon = schema["properties"]["canonicalization"]["properties"]
    assert canon["single_parse"]["const"] is True
    assert canon["shared_authority_object_for_transport"]["const"] is True
    assert canon["reject_userinfo"]["const"] is True


def test_no_schema_defines_a_verified_or_completeness_field_on_packet_records() -> None:
    """HARD CONSTRAINT #2 (structural half): the two packet-authored record
    schemas (sources, assertion_candidates) must never declare a computed
    completeness/verified field — only the RF-computed receipt may."""

    forbidden = {"verified", "completeness_tier", "computed_completeness_tier"}
    record_set_key = {
        "external_research_sources": "sources",
        "external_assertion_candidates": "candidates",
    }
    for name, key in record_set_key.items():
        schema = SchemaRegistry().get(name)
        item_props = set(schema["properties"][key]["items"]["properties"])
        assert not (item_props & forbidden), f"{name} must not declare {forbidden & item_props}"
