"""Producer-profile coverage for the External Research Report Interchange (ERI)
v1 contract — plan Phase 3 "Producer Prompt/Output Profiles" (tasks ERI-3.1
through ERI-3.6), see docs/project_plans/implementation_plans/enhancements/
external-research-report-interchange-v1.md and docs/dev/architecture/
external-research-handoff-contract.md.

Five profiles (generic, chatgpt, perplexity, gemini, notebooklm) each emit an
example ``external_research_handoff/v1`` packet under
``tests/fixtures/external_research_handoff/profiles/<profile>/``, plus an
``injection/`` fixture whose report/source/candidate/activity/extension
string values imitate common injection attacks. This module proves:

1. every profile fixture validates against the frozen schemas;
2. all five normalize to the same canonical packet shape with deterministic
   member ordering (proven with a pure, test-local canonicalization helper —
   this phase does not call the importer service, which is owned elsewhere);
3. every injection-shaped value in the injection fixture round-trips as
   inert, escaped data — it never becomes a path, command, selector, format
   string, or control value, and the schema's structurally-governed fields
   (path, role, source_id, candidate_id, enums) never carry one.

This module is standalone from ``tests/test_schema_validation.py`` and from
``tests/unit/test_external_research_schemas.py`` by the same precedent those
two already establish for each other — the P1 fixture directories
(``handoff/``, ``sources/``, etc.) are untouched; profile fixtures live in
their own ``profiles/<profile>/`` subdirectory so no existing glob picks them
up.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from research_foundry.schemas import validate
from research_foundry.yamlio import dumps_yaml, load_yaml, loads_yaml

FIXTURES_ROOT = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "external_research_handoff"
    / "profiles"
)

PROFILES = ["generic", "chatgpt", "perplexity", "gemini", "notebooklm"]
INJECTION_DIR = FIXTURES_ROOT / "injection"

REQUIRED_ROLES = {"handoff_manifest", "report", "sources", "assertion_candidates"}
ALL_ROLES = REQUIRED_ROLES | {"activity", "attachment"}
ACCESS_STATUSES = {"open-access", "public-domain", "paywalled", "unknown"}
CLASSIFICATIONS = {"assertion", "inference", "annotation"}
RELATIONS = {"supports", "contradicts", "context", "unknown"}
PACKET_LOCAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
MEMBER_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")


def _packet_files(profile_dir: Path) -> dict[str, Any]:
    return {
        "handoff": load_yaml(profile_dir / "handoff.yaml"),
        "sources": load_yaml(profile_dir / "sources.yaml"),
        "candidates": load_yaml(profile_dir / "assertion_candidates.yaml"),
        "report_text": (profile_dir / "report.md").read_text(encoding="utf-8"),
    }


def canonicalize_packet(profile_dir: Path) -> dict[str, Any]:
    """Pure, deterministic reduction of one packet directory to a
    profile-agnostic canonical shape. No importer/service code is called —
    this is a test-local proof that every profile's fixture agrees on the
    same packet contract, independent of profile-specific vendor content."""

    handoff = load_yaml(profile_dir / "handoff.yaml")
    sources = load_yaml(profile_dir / "sources.yaml")
    candidates = load_yaml(profile_dir / "assertion_candidates.yaml")

    members_sorted = sorted(
        ({"role": m["role"], "path": m["path"]} for m in handoff["members"]),
        key=lambda m: (m["role"], m["path"]),
    )
    roles_present = {m["role"] for m in handoff["members"]}

    return {
        "schema_name": handoff["schema_name"],
        "schema_version": handoff["schema_version"],
        "transport": handoff["transport"],
        "content_roles": handoff["content_roles"],
        "required_roles_present": REQUIRED_ROLES <= roles_present,
        "member_roles_sorted": [m["role"] for m in members_sorted],
        "sources_schema_name": sources["schema_name"],
        "sources_schema_version": sources["schema_version"],
        "source_ids_sorted": sorted(s["source_id"] for s in sources["sources"]),
        "candidates_schema_name": candidates["schema_name"],
        "candidates_schema_version": candidates["schema_version"],
        "candidate_ids_sorted": sorted(c["candidate_id"] for c in candidates["candidates"]),
        "candidate_classifications_used": sorted(
            {c["classification"] for c in candidates["candidates"]}
        ),
    }


# ---------------------------------------------------------------------------
# 1. Every profile fixture validates against the frozen schemas.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_packet_validates_against_frozen_schemas(profile: str) -> None:
    d = FIXTURES_ROOT / profile
    for name in ("handoff.yaml", "sources.yaml", "assertion_candidates.yaml", "report.md"):
        assert (d / name).exists(), f"{profile}: missing required packet member {name}"

    packet = _packet_files(d)
    handoff_result = validate(packet["handoff"], "external_research_handoff")
    assert handoff_result.ok, f"{profile}/handoff.yaml: {handoff_result.errors}"

    sources_result = validate(packet["sources"], "external_research_sources")
    assert sources_result.ok, f"{profile}/sources.yaml: {sources_result.errors}"

    candidates_result = validate(packet["candidates"], "external_assertion_candidates")
    assert candidates_result.ok, f"{profile}/assertion_candidates.yaml: {candidates_result.errors}"

    # report.md's content_role is always fixed, never profile-specific.
    assert packet["handoff"]["content_roles"] == {"report": "platform_synthesis"}
    assert packet["handoff"]["producer_profile"] == profile


def test_injection_packet_validates_against_frozen_schemas() -> None:
    handoff = load_yaml(INJECTION_DIR / "handoff.yaml")
    sources = load_yaml(INJECTION_DIR / "sources.yaml")
    candidates = load_yaml(INJECTION_DIR / "assertion_candidates.yaml")

    assert validate(handoff, "external_research_handoff").ok
    assert validate(sources, "external_research_sources").ok
    assert validate(candidates, "external_assertion_candidates").ok

    # activity.yaml carries no dedicated schema in v1 (contract: only the six
    # named schemas exist) -- it just needs to load without raising.
    activity = load_yaml(INJECTION_DIR / "activity.yaml")
    assert isinstance(activity, dict)


# ---------------------------------------------------------------------------
# 2. All five normalize to the same canonical packet shape, deterministically.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_canonicalizes_to_the_shared_packet_shape(profile: str) -> None:
    d = FIXTURES_ROOT / profile
    canon = canonicalize_packet(d)

    assert canon["schema_name"] == "external_research_handoff"
    assert canon["schema_version"] == "1.0"
    assert canon["transport"] == "directory"
    assert canon["content_roles"] == {"report": "platform_synthesis"}
    assert canon["required_roles_present"] is True
    assert canon["sources_schema_name"] == "external_research_sources"
    assert canon["sources_schema_version"] == "1.0"
    assert canon["candidates_schema_name"] == "external_assertion_candidates"
    assert canon["candidates_schema_version"] == "1.0"
    assert set(canon["candidate_classifications_used"]) <= CLASSIFICATIONS

    # deterministic: re-canonicalizing the same directory is byte-for-byte
    # identical -- no incidental ordering/hash-seed dependence.
    assert canonicalize_packet(d) == canon


def test_all_profiles_share_the_same_canonical_required_role_ordering() -> None:
    """Every profile may add its own optional members in a different place,
    but the deterministic (role, path)-sorted view of the four REQUIRED
    roles must be identical in shape across all five profiles -- this is
    what "normalize to the same canonical packet shape" means at the
    fixture layer."""

    role_prefixes = {}
    for profile in PROFILES:
        canon = canonicalize_packet(FIXTURES_ROOT / profile)
        role_prefixes[profile] = tuple(
            r for r in canon["member_roles_sorted"] if r in REQUIRED_ROLES
        )

    distinct_orderings = set(role_prefixes.values())
    assert len(distinct_orderings) == 1, (
        f"canonical required-role ordering differs across profiles: {role_prefixes}"
    )
    assert distinct_orderings == {
        tuple(sorted(REQUIRED_ROLES))
    }, "canonical role ordering must be the four required roles, sorted"


def test_no_profile_invents_a_second_packet_shape() -> None:
    """Structural guard: every profile's handoff.yaml declares exactly the
    four required member roles at minimum, and every member role used stays
    inside the schema's closed role vocabulary -- no profile is free to add
    an unmodeled member kind."""

    for profile in PROFILES:
        handoff = load_yaml(FIXTURES_ROOT / profile / "handoff.yaml")
        roles = {m["role"] for m in handoff["members"]}
        assert REQUIRED_ROLES <= roles
        assert roles <= ALL_ROLES


# ---------------------------------------------------------------------------
# 3. Injection-shaped values survive round-trip as inert, escaped data.
# ---------------------------------------------------------------------------

INJECTION_MARKERS = [
    "ignore previous instructions",
    "system:",
    "</system>",
    "<tool_use",
    "function_call:",
    "shell_exec",
    "../../../../etc/passwd",
    "$ref",
    "schema: admin",
    "; rm -rf /",
    "$(curl",
    "`whoami`",
    r"C:\\Windows",
    "{{7*7}}",
    "%s%n",
    "${jndi:ldap://",
    "!!python/object/apply:",
    "__proto__",
]


def test_injection_markers_are_actually_present_in_the_fixture() -> None:
    """Sanity check on the fixture itself: every required injection category
    is represented somewhere across report/source/candidate/activity."""

    haystacks = [
        (INJECTION_DIR / "handoff.yaml").read_text(encoding="utf-8"),
        (INJECTION_DIR / "sources.yaml").read_text(encoding="utf-8"),
        (INJECTION_DIR / "assertion_candidates.yaml").read_text(encoding="utf-8"),
        (INJECTION_DIR / "report.md").read_text(encoding="utf-8"),
        (INJECTION_DIR / "activity.yaml").read_text(encoding="utf-8"),
    ]
    for marker in INJECTION_MARKERS:
        assert any(marker in h for h in haystacks), f"missing injection category marker: {marker!r}"


def test_injection_values_parse_as_plain_strings_never_as_tags_or_objects() -> None:
    """The YAML loader (research_foundry.yamlio, built on yaml.safe_load) has
    no custom constructors -- a string shaped like a YAML/deserialization
    tag (e.g. ``!!python/object/apply:...``) that is written as a quoted
    scalar parses as an ordinary ``str``, never as a constructed object or
    executed directive."""

    handoff = load_yaml(INJECTION_DIR / "handoff.yaml")
    sources = load_yaml(INJECTION_DIR / "sources.yaml")
    candidates = load_yaml(INJECTION_DIR / "assertion_candidates.yaml")

    assert isinstance(handoff["research_context"]["research_question"], str)
    assert isinstance(handoff["research_context"]["task_context"], str)
    assert isinstance(handoff["vendor_reference"]["session_hint"], str)
    assert isinstance(handoff["vendor_reference"]["route_hint"], str)

    src = sources["sources"][0]
    assert isinstance(src["title"], str)
    for author in src["declared_metadata"]["authors"]:
        assert isinstance(author, str)
    bait = src["extensions"]["yaml_deserialization_bait"]
    assert isinstance(bait, str)
    assert bait == "!!python/object/apply:os.system ['id']"

    cand = candidates["candidates"][0]
    assert isinstance(cand["statement"], str)
    assert isinstance(cand["quote"], str)
    assert isinstance(cand["unit"], str)
    assert isinstance(cand["direction"], str)
    assert isinstance(cand["extensions"]["vendor_deserialization_bait"], str)


def test_injection_values_never_occupy_a_structural_control_field() -> None:
    """The schema's structurally-governed fields (member path/role, packet-
    local ids, closed enums, transport/schema identity) are pattern- or
    enum-constrained; prove the injection fixture's payloads live exclusively
    in free-text/extensions fields and never leaked into one of these."""

    handoff = load_yaml(INJECTION_DIR / "handoff.yaml")
    sources = load_yaml(INJECTION_DIR / "sources.yaml")
    candidates = load_yaml(INJECTION_DIR / "assertion_candidates.yaml")

    expected_paths = {
        "handoff.yaml",
        "report.md",
        "sources.yaml",
        "assertion_candidates.yaml",
        "activity.yaml",
    }
    actual_paths = {m["path"] for m in handoff["members"]}
    assert actual_paths == expected_paths

    for m in handoff["members"]:
        assert MEMBER_PATH_PATTERN.fullmatch(m["path"]), m["path"]
        assert ".." not in m["path"]
        assert m["role"] in ALL_ROLES
        for marker in INJECTION_MARKERS:
            assert marker not in m["path"], f"injection marker leaked into member path: {marker!r}"

    assert handoff["schema_name"] == "external_research_handoff"
    assert handoff["schema_version"] == "1.0"
    assert handoff["transport"] == "directory"
    assert handoff["producer_profile"] in {*PROFILES}
    assert handoff["declared_sensitivity"] in {
        "public",
        "personal",
        "work_sensitive",
        "client_sensitive",
    }
    assert handoff["content_roles"] == {"report": "platform_synthesis"}

    for s in sources["sources"]:
        assert PACKET_LOCAL_ID_PATTERN.fullmatch(s["source_id"])
        assert s["access_status"] in ACCESS_STATUSES
        for marker in INJECTION_MARKERS:
            assert marker not in s["source_id"]
            assert marker not in s["access_status"]

    for c in candidates["candidates"]:
        assert PACKET_LOCAL_ID_PATTERN.fullmatch(c["candidate_id"])
        assert c["classification"] in CLASSIFICATIONS
        if c["relation"] is not None:
            assert c["relation"] in RELATIONS
        for ref in c["source_refs"]:
            assert PACKET_LOCAL_ID_PATTERN.fullmatch(ref)
        for marker in INJECTION_MARKERS:
            assert marker not in c["candidate_id"]
            assert marker not in c["classification"]


def test_selector_ref_key_is_inert_never_a_real_json_schema_ref() -> None:
    """A candidate's ``selector`` object is ``additionalProperties: true`` —
    an operator/producer could plant a ``$ref``-shaped key inside it. Prove
    the validator never attempts to dereference it as an actual JSON Schema
    ``$ref`` (it has no meaning as instance data) and the packet still
    validates cleanly with that key present as ordinary string data."""

    candidates = load_yaml(INJECTION_DIR / "assertion_candidates.yaml")
    selector = candidates["candidates"][0]["selector"]
    assert selector["$ref"] == "file:///etc/shadow"
    assert isinstance(selector["$ref"], str)
    assert validate(candidates, "external_assertion_candidates").ok


def test_injection_payloads_round_trip_byte_identical_through_yaml() -> None:
    """Dump-then-reload every injection-bearing packet member and assert the
    parsed structure is unchanged -- no re-interpretation, coercion, or
    mutation happens across a YAML round trip."""

    cases = [
        ("handoff.yaml", "external_research_handoff"),
        ("sources.yaml", "external_research_sources"),
        ("assertion_candidates.yaml", "external_assertion_candidates"),
    ]
    for filename, schema_name in cases:
        original = load_yaml(INJECTION_DIR / filename)
        round_tripped = loads_yaml(dumps_yaml(original))
        assert round_tripped == original, f"{filename}: mutated across a YAML dump/reload cycle"
        assert validate(round_tripped, schema_name).ok


def test_injection_extensions_survive_json_round_trip_as_plain_data() -> None:
    """``extensions`` objects (including a planted ``__proto__`` key) survive
    a JSON encode/decode cycle as ordinary data. Python dicts have no
    prototype-chain concept, so a data key literally named ``__proto__``
    is indistinguishable from any other string key -- there is no
    pollution vector to trigger."""

    sources = load_yaml(INJECTION_DIR / "sources.yaml")
    candidates = load_yaml(INJECTION_DIR / "assertion_candidates.yaml")

    for record in (sources["sources"][0], candidates["candidates"][0]):
        original = record["extensions"]
        round_tripped = json.loads(json.dumps(original))
        assert round_tripped == original
        assert "__proto__" in original
        assert not hasattr(dict, "__proto__")


def test_report_md_injection_prose_is_never_a_source_or_claim_writer_input() -> None:
    """contract §4.1: report.md bytes are content_role platform_synthesis and
    can never enter a source-card, claim, or assertion writer. At this
    schema/fixture-only phase, the observable proxy for that rule is
    structural: report.md is not, and is never referenced as, a member of
    the sources or assertion_candidates record sets -- its injection-shaped
    prose has no path into either schema."""

    report_text = (INJECTION_DIR / "report.md").read_text(encoding="utf-8")
    sources = load_yaml(INJECTION_DIR / "sources.yaml")
    candidates = load_yaml(INJECTION_DIR / "assertion_candidates.yaml")

    assert "{{7*7}}" in report_text
    assert "rm -rf" in report_text

    # None of report.md's literal injection text appears inside any
    # sources/candidates record -- they are independent packet members.
    sources_blob = json.dumps(sources)
    candidates_blob = json.dumps(candidates)
    assert "rm -rf / #\", \"echo pwned" not in sources_blob  # canary: never silently merged
    assert report_text not in sources_blob
    assert report_text not in candidates_blob
