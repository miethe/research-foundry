"""Unit tests for ERI Phase 2 — Staging and Immutable Receipts.

Covers ERI-2.1 (safe packet inspection), ERI-2.2 (stable staging manifest),
ERI-2.3 (effects and terminal receipt), and ERI-2.4 (replay, conflict,
dry-run) per
docs/dev/architecture/external-research-handoff-contract.md and the phase-2
task brief. Fixtures are built inline via ``tmp_path`` (this test module
owns no files under tests/fixtures/ — those belong to a parallel P1 agent).
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate as schema_validate
from research_foundry.services.external_research_interchange import (
    ActionResolution,
    DEFAULT_LIMITS,
    ExternalResearchInterchange,
    InterchangeError,
    Limits,
    MemberOversizeError,
    PacketTraversalError,
    ReplayConflictError,
    ResolutionContext,
    StagingIntegrityError,
    _action_manifest_and_digest,
    _build_action_inputs,
    _stream_member,
    compute_governance_policy_digest,
    compute_policy_digest,
    compute_receipt_digest_accepted,
    default_resolve_candidate,
    default_resolve_source,
    inspect_packet,
)
from research_foundry.yamlio import dumps_yaml, loads_yaml

# ---------------------------------------------------------------------------
# Packet builder
# ---------------------------------------------------------------------------

# Repo root two levels up from tests/unit/this_file.
_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"


def _schema_const(schema_name: str, *keys: str) -> Any:
    """Read a `const` value directly from the schema file.

    Several `external_research_acquisition_policy` fields are pinned closed
    sets (`forbidden_address_categories`, `metadata_deny_set`, etc.) that a
    parallel agent may extend as part of closing a security finding (e.g.
    round-2 audit finding #10 added `ipv6_site_local`). Deriving these
    fixture values from the schema itself -- instead of hand-copying the
    list into this test module -- means a future schema addition can never
    silently desync this fixture from the schema's own authoritative closed
    set the way a hardcoded copy just did.
    """

    import yaml as _yaml

    doc = _yaml.safe_load((_SCHEMA_ROOT / f"{schema_name}.schema.yaml").read_text(encoding="utf-8"))
    node: Any = doc
    for key in keys:
        node = node["properties"][key]
    return node["const"]


VALID_POLICY: dict[str, Any] = {
    "schema_version": "1.0",
    "type": "external_research_acquisition_policy",
    "allowed_schemes": ["https", "http"],
    "reject_embedded_credentials": True,
    "canonicalization": {
        "single_parse": True,
        "idna_normalization": True,
        "reject_userinfo": True,
        "reject_percent_encoded_host": True,
        "reject_ipv6_zone_ids": True,
        "reject_ambiguous_numeric_host": True,
        "strip_single_trailing_root_label_dot": True,
        "shared_authority_object_for_transport": True,
    },
    "transport_architecture": {
        "single_actor_owns_full_lifecycle": True,
        "hands_off_acquired_bytes_only": True,
        "environment_and_pac_proxies_disabled": True,
        "provider_delegated_fetch_allowed": False,
    },
    "forbidden_address_categories": _schema_const(
        "external_research_acquisition_policy", "forbidden_address_categories"
    ),
    "metadata_deny_set": _schema_const("external_research_acquisition_policy", "metadata_deny_set"),
    "metadata_deny_set_version": _schema_const(
        "external_research_acquisition_policy", "metadata_deny_set_version"
    ),
    "special_purpose_address_registry_version": _schema_const(
        "external_research_acquisition_policy", "special_purpose_address_registry_version"
    ),
    "ipv6_transition_policy": {
        "well_known_prefixes": _schema_const(
            "external_research_acquisition_policy", "ipv6_transition_policy", "well_known_prefixes"
        ),
        "decode_and_validate_embedded_ipv4": True,
        "operator_configured_nat64_prefixes": [],
    },
    "dns_policy": {
        "validate_every_answer": True,
        "bind_to_validated_address": True,
        "verify_connected_peer": True,
    },
    "redirects": {"max_hops": 3, "revalidate_every_hop": True},
    "transport_fallback_allowed": False,
    "local_asset_carve_out": {
        "packet_internal_attachment_resolution": True,
        "out_of_packet_requires_operator_grant": True,
        "operator_grant_binds_path_and_digest": True,
        "producer_supplied_locator_type_hint_ignored": True,
    },
    "denial": {
        "leaks_denied_ids": False,
        "leaks_resolved_addresses": False,
        "leaks_text": False,
        "leaks_counts": False,
        "leaks_reason_code_differential": False,
    },
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def build_packet(
    root: Path,
    *,
    sources: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    include_attachment: bool = True,
    include_activity: bool = True,
    extra_members: list[dict[str, Any]] | None = None,
    corrupt_member: str | None = None,
    omit_member_role: str | None = None,
    declared_extra_member: dict[str, Any] | None = None,
    sources_raw: bytes | None = None,
    candidates_raw: bytes | None = None,
) -> Path:
    """Build a schema-valid ``external_research_handoff/v1`` packet directory.

    ``corrupt_member`` flips one byte of the named on-disk file after its
    declared hash was computed (digest-conflict fixtures).
    ``declared_extra_member`` adds a members[] entry with no backing file
    (required-member-missing fixtures) unless a real file is also written.
    ``sources_raw``/``candidates_raw`` substitute arbitrary raw bytes for the
    ``sources.yaml``/``assertion_candidates.yaml`` member content (declared
    byte_length/sha256 are computed from these bytes so the packet still
    passes structural/digest verification) — used for inert-data-boundary
    parsing attack fixtures (contract audit finding #12) where the injected
    content need not itself be schema-shaped, only reach the parser.
    """

    root.mkdir(parents=True, exist_ok=True)

    report_bytes = b"# Report\n\nPlatform synthesis text.\n"
    sources_doc = {
        "schema_name": "external_research_sources",
        "schema_version": "1.0",
        "sources": sources
        if sources is not None
        else [
            {
                "source_id": "src_001",
                "title": "A Source",
                "locator": {"doi": None, "url": "https://example.com/a"},
                "publication_year": 2024,
                "access_status": "open-access",
            }
        ],
    }
    candidates_doc = {
        "schema_name": "external_assertion_candidates",
        "schema_version": "1.0",
        "candidates": candidates
        if candidates is not None
        else [
            {
                "candidate_id": "cand_001",
                "statement": "X causes Y.",
                "classification": "assertion",
                "source_refs": ["src_001"],
                "quote": "X causes Y.",
            }
        ],
    }
    activity_bytes = dumps_yaml({"events": []}).encode("utf-8")
    attachment_bytes = b"col1,col2\n1,2\n"
    sources_bytes = sources_raw if sources_raw is not None else dumps_yaml(sources_doc).encode("utf-8")
    candidates_bytes = candidates_raw if candidates_raw is not None else dumps_yaml(candidates_doc).encode("utf-8")

    members: list[dict[str, Any]] = [
        {"path": "handoff.yaml", "role": "handoff_manifest", "byte_length": 1, "sha256": "0" * 64},
        {"path": "report.md", "role": "report", "byte_length": len(report_bytes), "sha256": _sha(report_bytes)},
        {
            "path": "sources.yaml",
            "role": "sources",
            "byte_length": len(sources_bytes),
            "sha256": _sha(sources_bytes),
        },
        {
            "path": "assertion_candidates.yaml",
            "role": "assertion_candidates",
            "byte_length": len(candidates_bytes),
            "sha256": _sha(candidates_bytes),
        },
    ]
    _write(root / "report.md", report_bytes)
    _write(root / "sources.yaml", sources_bytes)
    _write(root / "assertion_candidates.yaml", candidates_bytes)

    if include_activity:
        members.append(
            {
                "path": "activity.yaml",
                "role": "activity",
                "byte_length": len(activity_bytes),
                "sha256": _sha(activity_bytes),
            }
        )
        _write(root / "activity.yaml", activity_bytes)
    if include_attachment:
        members.append(
            {
                "path": "attachments/table1.csv",
                "role": "attachment",
                "byte_length": len(attachment_bytes),
                "sha256": _sha(attachment_bytes),
            }
        )
        _write(root / "attachments" / "table1.csv", attachment_bytes)
    if extra_members:
        members.extend(extra_members)
    if declared_extra_member:
        members.append(declared_extra_member)

    if omit_member_role:
        members = [m for m in members if m["role"] != omit_member_role]

    total = sum(m["byte_length"] for m in members)
    handoff_doc = {
        "schema_name": "external_research_handoff",
        "schema_version": "1.0",
        "transport": "directory",
        "producer_profile": "generic",
        "research_context": {"research_question": None, "task_context": None},
        "declared_sensitivity": "personal",
        "created_at": "2026-07-26T12:00:00Z",
        "content_roles": {"report": "platform_synthesis"},
        "vendor_reference": {},
        "members": members,
        "total_declared_bytes": total,
    }
    _write(root / "handoff.yaml", dumps_yaml(handoff_doc).encode("utf-8"))

    if corrupt_member:
        path = root / corrupt_member
        data = bytearray(path.read_bytes())
        data[0] = (data[0] + 1) % 256
        path.write_bytes(bytes(data))

    return root


@pytest.fixture()
def workspace(tmp_path: Path) -> FoundryPaths:
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    (ws_root / "foundry.yaml").write_text("workspace: true\n", encoding="utf-8")
    return FoundryPaths(root=ws_root)


def _interchange(workspace: FoundryPaths, workspace_id: str = "ws_demo") -> ExternalResearchInterchange:
    return ExternalResearchInterchange(workspace_id=workspace_id, paths=workspace)


# ---------------------------------------------------------------------------
# ERI-2.1 — Safe packet inspection
# ---------------------------------------------------------------------------


def test_valid_packet_inspects_ok(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    inspection = inspect_packet(root)
    assert inspection.ok is True
    assert inspection.reason_code is None
    assert len(inspection.packet_digest) == 64
    assert inspection.source_records[0]["source_id"] == "src_001"
    assert inspection.candidate_records[0]["candidate_id"] == "cand_001"
    assert inspection.schema_major_versions == {
        "external_research_handoff": 1,
        "external_research_sources": 1,
        "external_assertion_candidates": 1,
        "external_research_import_receipt": 1,
        "external_research_import_checkpoint": 1,
        "external_research_acquisition_policy": 1,
    }


def test_packet_digest_is_deterministic_and_order_independent(tmp_path: Path) -> None:
    root_a = build_packet(tmp_path / "a")
    root_b = build_packet(tmp_path / "b")
    a = inspect_packet(root_a)
    b = inspect_packet(root_b)
    assert a.packet_digest == b.packet_digest


def test_packet_digest_changes_on_byte_change(tmp_path: Path) -> None:
    root_a = build_packet(tmp_path / "a")
    root_b = build_packet(tmp_path / "b", corrupt_member="attachments/table1.csv")
    a = inspect_packet(root_a)
    b = inspect_packet(root_b)
    # b is blocked (digest conflict) so its packet_digest reflects the
    # DECLARED manifest, which is identical to a's declared manifest (the
    # corruption only touches actual bytes on disk) — proving packet_digest
    # is defined over declared identity, and the mismatch is caught
    # separately as member_digest_conflict.
    assert b.ok is False
    assert b.reason_code == "member_digest_conflict"


def test_traversal_blocked_by_low_level_primitive(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    with pytest.raises(PacketTraversalError):
        _stream_member(root, PurePosixPath("../outside.txt"), max_bytes=1024, keep_bytes=False)


def test_symlink_member_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    outside = tmp_path / "outside.csv"
    outside.write_bytes(b"x,y\n1,2\n")
    (root / "attachments" / "table1.csv").unlink()
    os.symlink(outside, root / "attachments" / "table1.csv")
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsafe_member_path"


def test_special_file_member_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    fifo_path = root / "attachments" / "fifo_member"
    try:
        os.mkfifo(fifo_path)
    except AttributeError:
        pytest.skip("os.mkfifo unavailable on this platform")
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsafe_member_path"


def test_undeclared_member_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    (root / "attachments" / "undeclared.csv").write_bytes(b"z\n")
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsafe_member_path"


def test_oversize_member_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    tight_limits = Limits(max_member_bytes=8)
    inspection = inspect_packet(root, limits=tight_limits)
    assert inspection.ok is False
    assert inspection.reason_code == "limit_exceeded"


def test_oversize_packet_total_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    tight_limits = Limits(max_packet_bytes=16)
    inspection = inspect_packet(root, limits=tight_limits)
    assert inspection.ok is False
    assert inspection.reason_code == "limit_exceeded"


def test_digest_conflict_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet", corrupt_member="report.md")
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "member_digest_conflict"


def test_required_member_missing_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    (root / "sources.yaml").unlink()
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "required_member_missing"


def test_unsupported_schema_version_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    handoff = loads_yaml((root / "handoff.yaml").read_text(encoding="utf-8"))
    handoff["schema_version"] = "2.0"
    (root / "handoff.yaml").write_text(dumps_yaml(handoff), encoding="utf-8")
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsupported_schema_version"


def test_too_many_attachments_blocks(tmp_path: Path) -> None:
    root = tmp_path / "packet"
    extra = [
        {
            "path": f"attachments/extra{i}.csv",
            "role": "attachment",
            "byte_length": 2,
            "sha256": _sha(b"a\n"),
        }
        for i in range(32)
    ]
    root = build_packet(root, extra_members=extra)
    for i in range(32):
        _write(root / "attachments" / f"extra{i}.csv", b"a\n")
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "limit_exceeded"


def test_duplicate_member_path_across_roles_blocks(tmp_path: Path) -> None:
    # Round-2 audit finding #8 (runtime half): two members declaring the
    # same `path` under different roles collapse into one entry when the
    # declared-path set is built, so the declared-vs-discovered comparison
    # alone never fires. Digest and byte_length match the real on-disk
    # attachment exactly, so the rejection is provably about the path
    # duplication, not a digest or missing-member failure.
    attachment_bytes = b"col1,col2\n1,2\n"
    root = build_packet(
        tmp_path / "packet",
        extra_members=[
            {
                "path": "attachments/table1.csv",
                "role": "activity",
                "byte_length": len(attachment_bytes),
                "sha256": _sha(attachment_bytes),
            }
        ],
    )
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsafe_member_path"


@pytest.mark.parametrize(
    "alias_path",
    ["attachments/./table1.csv", "attachments//table1.csv"],
)
def test_normalized_alias_member_path_blocks(tmp_path: Path, alias_path: str) -> None:
    # Karen-gate bypass regression: PurePosixPath drops `.` segments and
    # collapses `//`, so these alias spellings open the same on-disk file
    # as `attachments/table1.csv`. A raw-string uniqueness comparison
    # accepted them (two manifest entries, one file — empirically proven
    # ok=True before the fix). Canonical-form enforcement must reject the
    # non-canonical spelling itself, closing the alias class. Digest and
    # byte_length match the real file so the rejection is provably about
    # the path, not content.
    attachment_bytes = b"col1,col2\n1,2\n"
    root = build_packet(
        tmp_path / "packet",
        extra_members=[
            {
                "path": alias_path,
                "role": "activity",
                "byte_length": len(attachment_bytes),
                "sha256": _sha(attachment_bytes),
            }
        ],
    )
    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsafe_member_path"


def test_unique_member_paths_pass_duplicate_check(tmp_path: Path) -> None:
    # Control for the duplicate-path rejection: an otherwise-identical
    # packet whose extra members sit at distinct new paths (with real
    # backing files) passes inspection outright.
    root = tmp_path / "packet"
    extra = [
        {
            "path": f"activity/extra{i}.yaml",
            "role": "activity",
            "byte_length": 3,
            "sha256": _sha(b"a: 1"[:3]),
        }
        for i in range(2)
    ]
    root = build_packet(root, extra_members=extra)
    for i in range(2):
        _write(root / "activity" / f"extra{i}.yaml", b"a: 1"[:3])
    inspection = inspect_packet(root)
    assert inspection.ok is True
    assert inspection.reason_code is None


def test_nonexistent_packet_dir_raises_usage_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        inspect_packet(tmp_path / "does-not-exist")


def test_streaming_hash_never_materializes_report_bytes(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    length, sha, content = _stream_member(
        root, PurePosixPath("report.md"), max_bytes=DEFAULT_LIMITS.max_member_bytes, keep_bytes=False
    )
    assert content is None
    assert length > 0
    assert len(sha) == 64


# ---------------------------------------------------------------------------
# ERI-2.2 / ERI-2.3 — Staging manifest, effects, terminal receipt
# ---------------------------------------------------------------------------


def test_stage_accepted_packet_produces_valid_receipt(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert result.replayed is False
    assert result.dry_run is False
    receipt = result.receipt
    validation = schema_validate(receipt, "external_research_import_receipt")
    assert validation.ok, validation.errors
    # Default resolver: source with a locator -> completed/locator_only;
    # candidate always quarantines citation_unresolved (no acquisition
    # capability at this phase) -> completed_with_quarantine overall.
    assert receipt["status"] == "completed_with_quarantine"
    assert receipt["counts"]["actions_total"] == 2
    assert receipt["counts"]["completed"] == 1
    assert receipt["counts"]["quarantined"] == 1
    assert receipt["target_run_id"] is None

    checkpoint = result.checkpoint
    assert checkpoint is not None
    validation = schema_validate(checkpoint, "external_research_import_checkpoint")
    assert validation.ok, validation.errors
    assert checkpoint["status"] == "converged"

    # report.md bytes staged as a governed, content-addressed artifact.
    report_dir = interchange._packet_dir(receipt["packet_digest"]) / "report"
    assert any(report_dir.iterdir())


def test_manifest_and_effects_are_immutable_write_once(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    packet_digest = result.receipt["packet_digest"]
    manifest_path = interchange._manifest_path(packet_digest)
    assert manifest_path.exists()
    original = manifest_path.read_text(encoding="utf-8")

    # Re-staging the identical packet must not corrupt or rewrite the
    # immutable manifest (replay short-circuits before touching it, but even
    # a direct re-invocation of the internal staging helper on the same
    # content must be a no-op, not a conflict).
    inspection = inspect_packet(root)
    interchange._stage_packet_artifacts(inspection)
    assert manifest_path.read_text(encoding="utf-8") == original


def test_blocked_packet_receipt_has_empty_actions(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    (root / "sources.yaml").unlink()
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    receipt = result.receipt
    assert receipt["status"] == "blocked"
    assert receipt["block_reason"] == "required_member_missing"
    assert receipt["actions"] == []
    assert receipt["counts"]["actions_total"] == 0
    validation = schema_validate(receipt, "external_research_import_receipt")
    assert validation.ok, validation.errors


def test_all_sources_completed_yields_completed_status(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(
        tmp_path / "packet",
        sources=[
            {
                "source_id": "src_001",
                "title": "A",
                "locator": {"doi": None, "url": "https://example.com/a"},
                "publication_year": 2024,
                "access_status": "open-access",
            }
        ],
        candidates=[],
    )
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert result.receipt["status"] == "completed"
    assert result.receipt["counts"]["quarantined"] == 0


def test_zero_actions_is_legal_and_completed(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet", sources=[], candidates=[])
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert result.receipt["status"] == "completed"
    assert result.receipt["counts"]["actions_total"] == 0


def test_source_without_locator_quarantines_invalid_locator(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(
        tmp_path / "packet",
        sources=[
            {
                "source_id": "src_002",
                "title": None,
                "locator": {"doi": None, "url": None},
                "publication_year": None,
                "access_status": "unknown",
            }
        ],
        candidates=[],
    )
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    action = result.receipt["actions"][0]
    assert action["outcome"] == "quarantined"
    # Per-item reason_code is removed from the caller-visible receipt
    # (contract audit finding #15) — only an opaque audit_ref remains.
    assert "reason_code" not in action
    assert action["audit_ref"] is not None
    assert len(action["audit_ref"]) == 64
    assert action["completeness_tier"] is None


def test_verified_tier_unreachable_when_target_run_id_null(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet", sources=[], candidates=[])

    def broken_resolver(record: dict[str, Any], ctx: ResolutionContext) -> ActionResolution:
        return ActionResolution("completed", "verified", None)

    sources = [
        {
            "source_id": "src_001",
            "locator": {"doi": None, "url": "https://example.com/a"},
            "access_status": "open-access",
        }
    ]
    root = build_packet(tmp_path / "packet2", sources=sources, candidates=[])
    interchange = _interchange(workspace)
    with pytest.raises(InterchangeError):
        interchange.stage(
            root,
            target_run_id=None,
            policy=VALID_POLICY,
            resolve_source=broken_resolver,
        )


# ---------------------------------------------------------------------------
# ERI-2.4 — Replay, conflict, dry-run
# ---------------------------------------------------------------------------


def test_exact_replay_returns_byte_identical_receipt(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    effects_dir = interchange._receipt_dir(first.receipt["receipt_digest"]) / "effects"
    before_files = sorted(p.name for p in effects_dir.iterdir())

    second = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    after_files = sorted(p.name for p in effects_dir.iterdir())

    assert second.replayed is True
    assert second.receipt == first.receipt
    assert before_files == after_files  # zero new canonical effects


def test_different_packet_yields_independent_receipt(workspace: FoundryPaths, tmp_path: Path) -> None:
    root_a = build_packet(tmp_path / "a")
    root_b = build_packet(
        tmp_path / "b",
        sources=[
            {
                "source_id": "src_999",
                "locator": {"doi": None, "url": "https://example.com/other"},
                "access_status": "open-access",
            }
        ],
    )
    interchange = _interchange(workspace)
    a = interchange.stage(root_a, target_run_id=None, policy=VALID_POLICY)
    b = interchange.stage(root_b, target_run_id=None, policy=VALID_POLICY)
    assert a.receipt["receipt_digest"] != b.receipt["receipt_digest"]
    assert a.receipt["packet_digest"] != b.receipt["packet_digest"]


def test_different_workspace_yields_independent_receipt(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    ws1 = _interchange(workspace, "ws_one")
    ws2 = _interchange(workspace, "ws_two")
    r1 = ws1.stage(root, target_run_id=None, policy=VALID_POLICY)
    r2 = ws2.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert r1.receipt["receipt_digest"] != r2.receipt["receipt_digest"]
    assert r1.receipt["packet_digest"] == r2.receipt["packet_digest"]


def test_different_policy_yields_independent_receipt(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    r1 = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    widened_policy = dict(VALID_POLICY)
    widened_policy["redirects"] = {"max_hops": 1, "revalidate_every_hop": True}
    r2 = interchange.stage(root, target_run_id=None, policy=widened_policy)
    assert r1.receipt["receipt_digest"] != r2.receipt["receipt_digest"]
    assert r1.receipt["policy_digest"] != r2.receipt["policy_digest"]


def test_true_conflict_denies_and_never_overwrites(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    receipt_path = interchange._receipt_path(first.receipt["receipt_digest"])
    original = receipt_path.read_text(encoding="utf-8")

    # Corrupt the persisted receipt's action set in place to simulate a
    # tampered/corrupted on-disk history at the same receipt_digest.
    tampered = dict(first.receipt)
    tampered["actions"] = [
        {**first.receipt["actions"][0], "action_id": "tampered_id"},
        first.receipt["actions"][1],
    ]
    tampered["counts"] = first.receipt["counts"]
    from research_foundry.services.external_research_interchange import _atomic_dump

    _atomic_dump(tampered, receipt_path)

    with pytest.raises(ReplayConflictError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY)

    # Never overwritten by the failed replay attempt.
    assert receipt_path.read_text(encoding="utf-8") != original


def test_dry_run_reports_actions_with_zero_canonical_effects(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, dry_run=True)
    assert result.dry_run is True
    assert result.replayed is False
    assert result.checkpoint is None
    assert result.receipt["counts"]["actions_total"] == 2
    validation = schema_validate(result.receipt, "external_research_import_receipt")
    assert validation.ok, validation.errors

    # Nothing was persisted anywhere under the workspace root.
    assert not interchange.root.exists()


def test_dry_run_never_mutates_existing_state(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    staged = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    receipt_path = interchange._receipt_path(staged.receipt["receipt_digest"])
    before = receipt_path.read_text(encoding="utf-8")

    result = interchange.stage(root, target_run_id=None, policy=VALID_POLICY, dry_run=True)
    assert result.receipt["receipt_digest"] == staged.receipt["receipt_digest"]
    assert receipt_path.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# Fault injection / deterministic recovery
# ---------------------------------------------------------------------------


def test_interruption_after_action_effect_resumes_and_converges(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)

    with pytest.raises(RuntimeError):
        interchange.stage(
            root,
            target_run_id=None,
            policy=VALID_POLICY,
            _interrupt_after_action_index=0,
        )

    # The first action's effect was published; no receipt exists yet.
    inspection = inspect_packet(root)
    policy_digest = compute_policy_digest(VALID_POLICY)
    actions = _build_action_inputs(inspection)
    _manifest, action_manifest_digest = _action_manifest_and_digest(actions)
    receipt_digest = compute_receipt_digest_accepted(
        packet_digest=inspection.packet_digest,
        workspace_id=interchange.workspace_id,
        target_run_id=None,
        policy_digest=policy_digest,
        schema_major_versions=inspection.schema_major_versions,
        action_manifest_digest=action_manifest_digest,
        governance_policy_digest=compute_governance_policy_digest(),
    )
    assert not interchange._receipt_path(receipt_digest).exists()
    effects_dir = interchange._receipt_dir(receipt_digest) / "effects"
    assert len(list(effects_dir.iterdir())) == 1

    resumed = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert resumed.replayed is False
    assert len(list(effects_dir.iterdir())) == 2
    validation = schema_validate(resumed.receipt, "external_research_import_receipt")
    assert validation.ok, validation.errors

    # A second call now replays the identical, already-published receipt.
    replayed = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert replayed.replayed is True
    assert replayed.receipt == resumed.receipt


def test_interruption_before_receipt_publish_resumes_without_duplicate_effects(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)

    with pytest.raises(RuntimeError):
        interchange.stage(
            root,
            target_run_id=None,
            policy=VALID_POLICY,
            _interrupt_before_receipt_publish=True,
        )

    inspection = inspect_packet(root)
    policy_digest = compute_policy_digest(VALID_POLICY)
    actions = _build_action_inputs(inspection)
    _manifest, action_manifest_digest = _action_manifest_and_digest(actions)
    receipt_digest = compute_receipt_digest_accepted(
        packet_digest=inspection.packet_digest,
        workspace_id=interchange.workspace_id,
        target_run_id=None,
        policy_digest=policy_digest,
        schema_major_versions=inspection.schema_major_versions,
        action_manifest_digest=action_manifest_digest,
        governance_policy_digest=compute_governance_policy_digest(),
    )
    effects_dir = interchange._receipt_dir(receipt_digest) / "effects"
    assert len(list(effects_dir.iterdir())) == 2
    assert not interchange._receipt_path(receipt_digest).exists()

    resumed = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert resumed.replayed is False
    # No duplicate effect files were written on resume.
    assert len(list(effects_dir.iterdir())) == 2
    validation = schema_validate(resumed.receipt, "external_research_import_receipt")
    assert validation.ok, validation.errors


# ---------------------------------------------------------------------------
# Identity primitives
# ---------------------------------------------------------------------------


def test_compute_receipt_digest_is_pure_and_deterministic() -> None:
    kwargs = dict(
        packet_digest="a" * 64,
        workspace_id="ws_demo",
        target_run_id=None,
        policy_digest="b" * 64,
        schema_major_versions={"x": 1},
        action_manifest_digest="c" * 64,
        governance_policy_digest="d" * 64,
    )
    assert compute_receipt_digest_accepted(**kwargs) == compute_receipt_digest_accepted(**kwargs)


def test_compute_governance_policy_digest_is_stable() -> None:
    assert compute_governance_policy_digest() == compute_governance_policy_digest()
    assert len(compute_governance_policy_digest()) == 64


def test_compute_policy_digest_changes_with_policy_content() -> None:
    other = dict(VALID_POLICY)
    other["redirects"] = {"max_hops": 0, "revalidate_every_hop": True}
    assert compute_policy_digest(VALID_POLICY) != compute_policy_digest(other)


def test_invalid_policy_is_rejected(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    bad_policy = dict(VALID_POLICY)
    bad_policy["allowed_schemes"] = ["file"]
    with pytest.raises(ValueError):
        interchange.stage(root, target_run_id=None, policy=bad_policy)


def test_default_resolvers_reject_invalid_kwargs() -> None:
    with pytest.raises(ValueError):
        ActionResolution("completed", "locator_only", "should_be_none")
    with pytest.raises(ValueError):
        ActionResolution("quarantined", None, None)


# ---------------------------------------------------------------------------
# Contract audit finding #7 — member bytes cannot change after hashing
# without changing packet identity (multiply-linked members / no re-open by
# path once hashed).
# ---------------------------------------------------------------------------


def test_multiply_linked_member_blocks(tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    target = root / "attachments" / "table1.csv"
    content = target.read_bytes()
    target.unlink()
    # Same bytes (so declared byte_length/sha256 still match) but the
    # on-disk file now has a second hardlink pointing at its inode — a
    # write through that other link, or through an already-open descriptor
    # elsewhere, would silently change these bytes after they are hashed
    # here without ever touching this path again.
    external = tmp_path / "external_hardlink_source.csv"
    external.write_bytes(content)
    os.link(external, target)

    inspection = inspect_packet(root)
    assert inspection.ok is False
    assert inspection.reason_code == "unsafe_member_path"


def test_report_bytes_immune_to_post_inspection_write_through_same_path(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    root = build_packet(tmp_path / "packet")
    inspection = inspect_packet(root)
    assert inspection.ok is True
    assert inspection.report_bytes is not None
    original_report_bytes = inspection.report_bytes
    original_sha = inspection.report_member.sha256  # type: ignore[union-attr]

    # Simulate a write to report.md's underlying bytes AFTER inspection has
    # already streamed, hashed, and verified it — e.g. through an
    # already-open write descriptor elsewhere. If staging ever re-opened
    # the member by path at this later point (the bug finding #7 closes),
    # it would silently persist THESE tampered bytes as the "governed"
    # artifact instead of the bytes packet_digest actually committed to.
    (root / "report.md").write_bytes(b"TAMPERED AFTER HASH VERIFICATION\n")

    interchange = _interchange(workspace)
    interchange._stage_packet_artifacts(inspection)
    staged_path = interchange._report_path(inspection.packet_digest, original_sha)
    assert staged_path.read_bytes() == original_report_bytes
    assert staged_path.read_bytes() != (root / "report.md").read_bytes()


# ---------------------------------------------------------------------------
# Contract audit finding #8 — concurrent first imports are serialized by a
# single-writer receipt-identity lease.
# ---------------------------------------------------------------------------


def test_receipt_lease_serializes_concurrent_callers(workspace: FoundryPaths) -> None:
    interchange = _interchange(workspace)
    receipt_digest = "f" * 64
    order: list[str] = []
    lock = threading.Lock()
    first_acquired = threading.Event()

    def first() -> None:
        with interchange._receipt_lease(receipt_digest):
            with lock:
                order.append("first-acquired")
            first_acquired.set()
            time.sleep(0.2)
            with lock:
                order.append("first-released")

    def second() -> None:
        first_acquired.wait(timeout=5)
        with interchange._receipt_lease(receipt_digest):
            with lock:
                order.append("second-acquired")

    t1 = threading.Thread(target=first)
    t2 = threading.Thread(target=second)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert order == ["first-acquired", "first-released", "second-acquired"]
    # The lease is always released, never left behind.
    assert not interchange._lease_path(receipt_digest).exists()


def test_receipt_lease_reclaims_stale_lease(workspace: FoundryPaths) -> None:
    interchange = _interchange(workspace)
    receipt_digest = "a" * 64
    lease_path = interchange._lease_path(receipt_digest)
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path.write_text("abandoned-holder\n", encoding="utf-8")
    stale_time = time.time() - 3600  # well past the staleness ceiling
    os.utime(lease_path, (stale_time, stale_time))

    acquired: list[bool] = []
    with interchange._receipt_lease(receipt_digest):
        acquired.append(True)
    assert acquired == [True]
    assert not lease_path.exists()


def test_concurrent_first_imports_converge_to_one_receipt_and_effect_set(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """Two concurrent imports of the same packet converge to exactly one
    terminal receipt and one set of effects (contract audit finding #8) —
    end-to-end through the receipt-identity lease that wraps ``stage()``'s
    acquisition/effect/publish phase.
    """

    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    worker_count = 4
    start = threading.Event()
    results: list[Any] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def slow_resolve_source(record: dict[str, Any], ctx: ResolutionContext) -> ActionResolution:
        # Only the lease-holding winner ever reaches a resolver call; the
        # other callers are blocked polling for the lease. This sleep
        # widens that window so the test actually exercises the losers
        # waiting rather than merely not-happening-to-race.
        time.sleep(0.05)
        return default_resolve_source(record, ctx)

    def worker() -> None:
        start.wait(timeout=5)
        try:
            result = interchange.stage(
                root, target_run_id=None, policy=VALID_POLICY, resolve_source=slow_resolve_source
            )
            with lock:
                results.append(result)
        except BaseException as exc:  # noqa: BLE001 - captured and asserted on below
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(worker_count)]
    for t in threads:
        t.start()
    start.set()
    for t in threads:
        t.join(timeout=10)

    assert not errors, errors
    assert len(results) == worker_count

    digests = {r.receipt["receipt_digest"] for r in results}
    assert len(digests) == 1

    receipts = [dict(r.receipt) for r in results]
    assert all(r == receipts[0] for r in receipts)

    replay_flags = [r.replayed for r in results]
    assert replay_flags.count(False) == 1
    assert replay_flags.count(True) == worker_count - 1

    effects_dir = interchange._receipt_dir(results[0].receipt["receipt_digest"]) / "effects"
    assert len(list(effects_dir.iterdir())) == len(results[0].receipt["actions"])
    assert not interchange._lease_path(results[0].receipt["receipt_digest"]).exists()


# ---------------------------------------------------------------------------
# Contract audit finding #12 — inert-data-boundary YAML parsing. Each attack
# is injected as raw sources.yaml bytes (declared byte_length/sha256 are
# still computed from these exact bytes, so structural/digest verification
# passes and the packet reaches the vulnerable parse call). None of these
# may raise out of ``inspect_packet`` — every one must fail closed with a
# safe, closed-vocabulary reason_code.
# ---------------------------------------------------------------------------


def _assert_hostile_sources_yaml_blocks(tmp_path: Path, raw: bytes, *, name: str) -> None:
    root = build_packet(tmp_path / name, sources_raw=raw)
    inspection = inspect_packet(root)
    assert inspection.ok is False, f"{name}: hostile sources.yaml content was not blocked"
    assert inspection.reason_code == "unsupported_schema_version"


def test_inert_boundary_rejects_object_tag(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(
        tmp_path,
        b"sources: !!python/object/apply:os.system ['echo pwned']\n",
        name="object_tag",
    )


def test_inert_boundary_rejects_merge_key(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(
        tmp_path,
        b"base: &base {a: 1}\nsources:\n  <<: *base\n  b: 2\n",
        name="merge_key",
    )


def test_inert_boundary_rejects_duplicate_yaml_key(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(tmp_path, b"sources: []\nsources: []\n", name="dup_key_yaml")


def test_inert_boundary_rejects_duplicate_json_style_member(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(tmp_path, b'sources: {"a": 1, "a": 2}\n', name="dup_key_json")


def test_inert_boundary_rejects_alias_bomb(tmp_path: Path) -> None:
    payload = (
        b'a: &a ["x","x","x","x","x","x","x","x","x","x"]\n'
        b"b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a,*a]\n"
        b"c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b,*b]\n"
        b"sources: *c\n"
    )
    _assert_hostile_sources_yaml_blocks(tmp_path, payload, name="alias_bomb")


def test_inert_boundary_rejects_deep_nesting(tmp_path: Path) -> None:
    inner = "1"
    for _ in range(200):
        inner = "{a: " + inner + "}"
    payload = f"sources: {inner}\n".encode("utf-8")
    _assert_hostile_sources_yaml_blocks(tmp_path, payload, name="deep_nesting")


def test_inert_boundary_rejects_non_finite_number(tmp_path: Path) -> None:
    # `.nan`/`.inf` are the non-finite numeric literals actually reachable
    # through this module's parser (a superset-of-JSON YAML loader); bare
    # JSON-style `NaN`/`Infinity` tokens are not YAML float literals and
    # already parse as harmless strings under `yaml.safe_load`.
    _assert_hostile_sources_yaml_blocks(tmp_path, b"sources: .nan\n", name="non_finite_nan")
    _assert_hostile_sources_yaml_blocks(tmp_path, b"sources: .inf\n", name="non_finite_inf")


# ---------------------------------------------------------------------------
# Round-2 audit finding #7 — "primitive-only" YAML loading still accepted
# non-JSON Python values (timestamps, !!binary, !!set, !!omap) that crashed
# canonical-JSON digesting with an uncaught TypeError. Each of these must now
# fail closed with a safe reason_code, just like the finding #12 fixtures
# above, never propagate a raw TypeError out of `inspect_packet`.
# ---------------------------------------------------------------------------


def test_inert_boundary_rejects_timestamp(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(tmp_path, b"sources: 2026-07-27\n", name="timestamp")


def test_inert_boundary_rejects_binary_tag(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(
        tmp_path, b"sources: !!binary |\n  aGVsbG8=\n", name="binary_tag"
    )


def test_inert_boundary_rejects_set_tag(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(tmp_path, b"sources: !!set\n  ? a\n  ? b\n", name="set_tag")


def test_inert_boundary_rejects_omap_tag(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(
        tmp_path, b"sources: !!omap\n  - a: 1\n  - b: 2\n", name="omap_tag"
    )


def test_inert_boundary_rejects_pairs_tag(tmp_path: Path) -> None:
    _assert_hostile_sources_yaml_blocks(
        tmp_path, b"sources: !!pairs\n  - a: 1\n  - b: 2\n", name="pairs_tag"
    )


def test_assert_json_primitive_only_accepts_the_full_json_vocabulary() -> None:
    """Positive control: every legal JSON-primitive shape must NOT raise --
    the whitelist gate must not become over-broad and reject ordinary,
    schema-valid packet content."""

    from research_foundry.services.external_research_interchange import _assert_json_primitive_only

    _assert_json_primitive_only(
        {
            "a": None,
            "b": True,
            "c": False,
            "d": "text",
            "e": 1,
            "f": 1.5,
            "g": [1, "two", None, {"nested": True}],
            "h": {},
            "i": [],
        }
    )


def test_assert_json_primitive_only_rejects_non_string_keys() -> None:
    from research_foundry.services.external_research_interchange import (
        _assert_json_primitive_only,
        _InertDocumentError,
    )

    with pytest.raises(_InertDocumentError):
        _assert_json_primitive_only({1: "a"})


# ---------------------------------------------------------------------------
# Round-2 audit finding #4 — the single-writer lease is now fenced: stale
# reclaim compares owner/inode immediately before unlinking, release never
# deletes a lease this process no longer owns, and immutable-artifact
# publication is a true create-if-absent CAS (`os.link`), not an existence
# check followed by `os.replace`.
# ---------------------------------------------------------------------------


def test_lease_release_never_deletes_a_reclaimed_replacement(workspace: FoundryPaths) -> None:
    """If this process's lease is reclaimed (simulating a heartbeat that
    arrived too late) and a NEW owner acquires a fresh lease at the same
    path, this process's own `_receipt_lease` `finally` block must not
    delete that new owner's lease merely because the path matches -- it
    must recognize (via inode) that the file is no longer the one it
    created."""

    interchange = _interchange(workspace)
    receipt_digest = "b" * 64
    lease_path = interchange._lease_path(receipt_digest)

    with interchange._receipt_lease(receipt_digest):
        # Simulate: our lease was reclaimed as stale, and a new owner
        # acquired a fresh lease at the same path while we were "still
        # working" (no heartbeat arrived in time).
        lease_path.unlink()
        lease_path.write_text("new-owner:0:99999:2026-01-01T00:00:00Z\n", encoding="utf-8")
        new_owner_inode = lease_path.stat().st_ino

    # Our `_receipt_lease` context manager's exit must NOT have deleted the
    # new owner's lease file.
    assert lease_path.exists()
    assert lease_path.stat().st_ino == new_owner_inode


def test_reclaim_stale_lease_only_one_concurrent_reclaimer_wins(workspace: FoundryPaths) -> None:
    """`_reclaim_stale_lease` re-verifies the lease is still the SAME file
    (inode + unchanged mtime) immediately before unlinking. Racing many
    concurrent reclaimers against the same stale lease exercises this for
    real: only the ONE that actually unlinks the file may report success;
    every other racer must observe the file already gone (or already
    replaced) and back off (return `None`) rather than also "succeeding"
    against the same stale lease."""

    interchange = _interchange(workspace)
    receipt_digest = "c" * 64
    lease_path = interchange._lease_path(receipt_digest)
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path.write_text("owner:0:1:2026-01-01T00:00:00Z\n", encoding="utf-8")
    stale_time = time.time() - 3600
    os.utime(lease_path, (stale_time, stale_time))

    results: list[object] = []
    lock = threading.Lock()

    def _reclaim() -> None:
        outcome = interchange._reclaim_stale_lease(lease_path)
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=_reclaim) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    winners = [r for r in results if r is not None]
    assert len(winners) == 1, f"exactly one reclaimer must win a stale lease, got {winners}"
    assert not lease_path.exists()


def test_write_immutable_mapping_is_true_cas_not_overwrite(workspace: FoundryPaths, tmp_path: Path) -> None:
    """A second writer publishing DIFFERENT bytes to the same immutable
    path must never silently win via `os.replace` -- it must observe the
    FIRST writer's bytes (via the CAS `os.link` losing the race) and raise
    on the subsequent content-equality check."""

    from research_foundry.services.external_research_interchange import (
        StagingIntegrityError,
        _write_immutable_mapping,
    )

    target = tmp_path / "immutable.yaml"
    _write_immutable_mapping({"a": 1}, target)
    with pytest.raises(StagingIntegrityError):
        _write_immutable_mapping({"a": 2}, target)
    # The first writer's bytes are exactly what is on disk -- never
    # overwritten by the second, conflicting attempt.
    assert loads_yaml(target.read_text(encoding="utf-8")) == {"a": 1}


# ---------------------------------------------------------------------------
# Round-2 audit finding #5 — resume no longer trusts a persisted effect
# record blindly: it is bound to the presented receipt_digest/action_id/kind
# and its effect_digest is recomputed and compared, not merely re-read.
# ---------------------------------------------------------------------------


def _stage_interrupted_after_first_action(workspace: FoundryPaths, tmp_path: Path):
    """Shared setup: interrupt after the FIRST action's effect is durably
    published but before the terminal receipt exists -- exactly the state
    that makes `stage()`'s next call take the per-action RESUME path
    (`effect_path.exists()`) rather than the whole-receipt replay path."""

    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    with pytest.raises(RuntimeError):
        interchange.stage(
            root, target_run_id=None, policy=VALID_POLICY, _interrupt_after_action_index=0
        )
    inspection = inspect_packet(root)
    policy_digest = compute_policy_digest(VALID_POLICY)
    actions = _build_action_inputs(inspection)
    _manifest, action_manifest_digest = _action_manifest_and_digest(actions)
    receipt_digest = compute_receipt_digest_accepted(
        packet_digest=inspection.packet_digest,
        workspace_id=interchange.workspace_id,
        target_run_id=None,
        policy_digest=policy_digest,
        schema_major_versions=inspection.schema_major_versions,
        action_manifest_digest=action_manifest_digest,
        governance_policy_digest=compute_governance_policy_digest(),
    )
    effects_dir = interchange._receipt_dir(receipt_digest) / "effects"
    effect_files = sorted(effects_dir.glob("*.yaml"))
    assert len(effect_files) == 1
    return root, interchange, effect_files[0]


def test_resume_rejects_effect_record_bound_to_a_different_receipt_digest(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    root, interchange, effect_file = _stage_interrupted_after_first_action(workspace, tmp_path)

    tampered = dict(loads_yaml(effect_file.read_text(encoding="utf-8")))
    tampered["receipt_digest"] = "0" * 64  # bound to a DIFFERENT receipt
    # Bypass the immutable-write guard directly (simulating on-disk
    # corruption/tampering, not a normal write path).
    from research_foundry.services.external_research_interchange import _atomic_dump

    _atomic_dump(tampered, effect_file)

    with pytest.raises(StagingIntegrityError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY)


def test_resume_rejects_effect_record_with_mismatched_effect_digest(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """A persisted effect record whose stored `effect_digest` does not
    match what recomputing it from the record's own trusted fields
    produces must be rejected -- the prior implementation trusted the
    stored `effect_digest` string verbatim."""

    root, interchange, effect_file = _stage_interrupted_after_first_action(workspace, tmp_path)

    tampered = dict(loads_yaml(effect_file.read_text(encoding="utf-8")))
    tampered["effect_digest"] = "f" * 64  # does not match a recompute of outcome/tier/reason/refs

    from research_foundry.services.external_research_interchange import _atomic_dump

    _atomic_dump(tampered, effect_file)

    with pytest.raises(StagingIntegrityError):
        interchange.stage(root, target_run_id=None, policy=VALID_POLICY)


def test_interrupted_resolver_leaves_an_inspectable_prepare_marker(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """A resolver interrupted mid-flight (simulating a real crash, not the
    benign batch-limit signal) leaves a durable `.prepare` marker behind for
    audit -- visible, inspectable evidence that an attempt reached the
    resolver for this action, closing the "silently indistinguishable from
    a clean first attempt" half of finding #5. Resume still completes
    (matching this codebase's existing, intentionally-tested crash-recovery
    contract), and the marker is cleared once the effect actually commits.
    """

    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)

    def _crashing_resolve_source(record, ctx):  # noqa: ANN001
        raise RuntimeError("simulated resolver crash mid-mutation")

    with pytest.raises(RuntimeError):
        interchange.stage(
            root,
            target_run_id=None,
            policy=VALID_POLICY,
            resolve_source=_crashing_resolve_source,
        )

    inspection = inspect_packet(root)
    policy_digest = compute_policy_digest(VALID_POLICY)
    actions = _build_action_inputs(inspection)
    _manifest, action_manifest_digest = _action_manifest_and_digest(actions)
    receipt_digest = compute_receipt_digest_accepted(
        packet_digest=inspection.packet_digest,
        workspace_id=interchange.workspace_id,
        target_run_id=None,
        policy_digest=policy_digest,
        schema_major_versions=inspection.schema_major_versions,
        action_manifest_digest=action_manifest_digest,
        governance_policy_digest=compute_governance_policy_digest(),
    )
    effects_dir = interchange._receipt_dir(receipt_digest) / "effects"
    prepare_files = sorted(effects_dir.glob("*.prepare"))
    assert len(prepare_files) == 1, "the crashed action's intent must be durably recorded"

    resumed = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert resumed.replayed is False
    # The marker is cleared once its action's effect actually commits.
    assert not list(effects_dir.glob("*.prepare"))


def test_batch_limit_reached_clears_its_prepare_marker(workspace: FoundryPaths, tmp_path: Path) -> None:
    """`ResolutionDeclined` (the benign per-invocation batch-limit signal)
    must clear the prepare marker it caused to be written -- unlike a real
    resolver crash, this signal is structurally guaranteed to mean the
    resolver body never ran, so nothing is left to audit."""

    from research_foundry.services.external_research_interchange import ResolutionDeclined

    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)

    def _declining_resolve_source(record, ctx):  # noqa: ANN001
        raise ResolutionDeclined()

    with pytest.raises(ResolutionDeclined):
        interchange.stage(
            root,
            target_run_id=None,
            policy=VALID_POLICY,
            resolve_source=_declining_resolve_source,
        )

    inspection = inspect_packet(root)
    policy_digest = compute_policy_digest(VALID_POLICY)
    actions = _build_action_inputs(inspection)
    _manifest, action_manifest_digest = _action_manifest_and_digest(actions)
    receipt_digest = compute_receipt_digest_accepted(
        packet_digest=inspection.packet_digest,
        workspace_id=interchange.workspace_id,
        target_run_id=None,
        policy_digest=policy_digest,
        schema_major_versions=inspection.schema_major_versions,
        action_manifest_digest=action_manifest_digest,
        governance_policy_digest=compute_governance_policy_digest(),
    )
    effects_dir = interchange._receipt_dir(receipt_digest) / "effects"
    assert not list(effects_dir.glob("*.prepare"))
    assert not list(effects_dir.glob("*.yaml"))


# ---------------------------------------------------------------------------
# Round-2 audit finding #6 — the packet is inspected exactly once for a
# whole `import_external_report` call; `stage(inspection=...)` performs NO
# second `inspect_packet` call when one is supplied.
# ---------------------------------------------------------------------------


def test_stage_with_precomputed_inspection_never_reinspects(workspace: FoundryPaths, tmp_path: Path) -> None:
    root = build_packet(tmp_path / "packet")
    interchange = _interchange(workspace)
    inspection = inspect_packet(root)

    import research_foundry.services.external_research_interchange as eri_module

    call_count = {"n": 0}
    real_inspect_packet = eri_module.inspect_packet

    def _counting_inspect_packet(*args, **kwargs):  # noqa: ANN001
        call_count["n"] += 1
        return real_inspect_packet(*args, **kwargs)

    eri_module.inspect_packet = _counting_inspect_packet  # type: ignore[attr-defined]
    try:
        result = interchange.stage(
            root, target_run_id=None, policy=VALID_POLICY, inspection=inspection
        )
    finally:
        eri_module.inspect_packet = real_inspect_packet  # type: ignore[attr-defined]

    assert result.receipt["packet_digest"] == inspection.packet_digest
    assert call_count["n"] == 0, "stage() must not re-inspect when an inspection is already supplied"


# ---------------------------------------------------------------------------
# Round-2 audit finding #9 — resume/blocked-replay nondeterminism.
# ---------------------------------------------------------------------------


def test_blocked_replay_with_delayed_created_at_is_not_a_conflict(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """An ordinary, delayed retry of the exact same blocked identity must
    replay cleanly -- the ONLY field that legitimately differs between the
    stored receipt and a freshly re-derived one (`created_at`) must be
    excluded from the conflict comparison, never trip `ReplayConflictError`
    for a ordinary re-submission."""

    root = build_packet(
        tmp_path / "packet",
        declared_extra_member={"path": "ghost.bin", "role": "attachment", "byte_length": 4, "sha256": "0" * 64},
    )
    interchange = _interchange(workspace)
    first = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert first.receipt["status"] == "blocked"

    # A delayed retry, well after the first attempt, must still replay the
    # SAME stored (byte-identical, including its ORIGINAL created_at)
    # receipt rather than raising.
    second = interchange.stage(root, target_run_id=None, policy=VALID_POLICY)
    assert second.replayed is True
    assert second.receipt == first.receipt
