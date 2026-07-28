"""ERI-6.1 — Cross-profile contracts and compatibility.

Phase 3's own test module (`tests/unit/test_external_research_profiles.py`)
explicitly does not call the importer service ("this phase does not call the
importer service, which is owned elsewhere"). This module closes that gap:
it drives all five offline producer-profile fixtures through the REAL,
end-to-end `import_external_report` pipeline (contract-frozen schemas ->
staging -> resolution -> receipt), proving "one packet contract covers five
producer profiles" (AC ERI-1) at runtime, not only at the schema layer.

Also covers the remaining ERI-6.1 quality-gate bullets:
- legacy `AssertionRegistry` reads (a use unrelated to ERI) are unaffected by
  ERI's modules being imported/exercised in the same process;
- a duplicate-authority scan proving ERI's own service modules define no
  second edition/passage/source-assertion/extraction/citation-tuple
  authority (contract §3.5) — they only ever CALL the existing
  `AssertionRegistry`/extraction primitives, never redefine them.

Schema golden/negative-fixture coverage remains
`tests/unit/test_external_research_schemas.py`'s job and is not duplicated
here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.external_research_import import (
    import_external_report,
)

FIXTURES_ROOT = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "external_research_handoff"
    / "profiles"
)

PROFILES = ["generic", "chatgpt", "perplexity", "gemini", "notebooklm"]


@pytest.fixture()
def workspace(tmp_path: Path) -> FoundryPaths:
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    (ws_root / "foundry.yaml").write_text("workspace: true\n", encoding="utf-8")
    return FoundryPaths(root=ws_root)


# ---------------------------------------------------------------------------
# Five profile round-trips through the real pipeline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_packet_stages_through_one_canonical_pipeline(
    profile: str, workspace: FoundryPaths
) -> None:
    """Every profile fixture is a valid, materialized packet directory that
    `import_external_report` accepts and stages -- never `blocked` (each
    fixture is schema-valid per Phase 1/3), through the SAME importer code
    path regardless of which producer authored it."""

    packet_dir = FIXTURES_ROOT / profile
    outcome = import_external_report(
        packet_dir,
        workspace_id=f"ws_{profile}",
        dry_run=True,
        paths=workspace,
    )
    assert outcome.status in ("completed", "completed_with_quarantine")
    assert outcome.packet_digest is not None
    assert len(outcome.packet_digest) == 64


def test_five_profiles_share_identical_schema_major_versions(
    workspace: FoundryPaths,
) -> None:
    """All five profiles normalize through the exact same schema majors --
    the packet contract's "one canonical shape" claim (AC ERI-1), verified
    end-to-end rather than only by each fixture individually validating."""

    schema_majors = []
    for profile in PROFILES:
        outcome = import_external_report(
            FIXTURES_ROOT / profile,
            workspace_id=f"ws_majors_{profile}",
            dry_run=True,
            paths=workspace,
        )
        assert outcome.receipt is not None
        schema_majors.append(outcome.receipt["schema_major_versions"])

    assert all(m == schema_majors[0] for m in schema_majors), schema_majors


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_packet_real_import_and_replay_converge(
    profile: str, workspace: FoundryPaths
) -> None:
    """A non-dry-run import of each profile fixture publishes a real
    receipt, and replaying it returns the byte-identical stored receipt --
    exercised across all five profiles, not just one canonical fixture."""

    packet_dir = FIXTURES_ROOT / profile
    first = import_external_report(
        packet_dir,
        workspace_id=f"ws_replay_{profile}",
        paths=workspace,
    )
    assert first.replayed is False

    second = import_external_report(
        packet_dir,
        workspace_id=f"ws_replay_{profile}",
        paths=workspace,
    )
    assert second.replayed is True
    assert second.receipt == first.receipt


# ---------------------------------------------------------------------------
# Legacy run/source/assertion reads remain intact
# ---------------------------------------------------------------------------


def test_legacy_assertion_registry_ingest_and_read_unaffected(
    workspace: FoundryPaths,
) -> None:
    """A plain, ERI-unrelated `AssertionRegistry` ingest/read cycle -- RF's
    pre-existing evidence authority -- behaves identically whether or not
    ERI's modules have been imported and exercised earlier in the same
    process (this test file itself has already run several ERI imports
    above by the time this executes in the default alphabetical/definition
    order within a module, and pytest may reorder across files -- the
    assertion is about behavior, not ordering)."""

    registry = AssertionRegistry(workspace_id="ws_legacy", paths=workspace)
    result = registry.ingest(
        "legacy-doc:1",
        "Legacy content unrelated to any ERI packet.",
        allowed_use={"sensitivity": "personal", "allowed_for_work_output": True},
    )
    assert result.created is True
    assert result.edition is not None

    replay = registry.ingest(
        "legacy-doc:1",
        "Legacy content unrelated to any ERI packet.",
        allowed_use={"sensitivity": "personal", "allowed_for_work_output": True},
    )
    assert replay.created is False
    assert replay.edition == result.edition


# ---------------------------------------------------------------------------
# Duplicate-authority / tree scan (contract §3.5)
# ---------------------------------------------------------------------------

_ERI_SERVICE_FILES = [
    "src/research_foundry/services/external_research_interchange.py",
    "src/research_foundry/services/external_research_resolution.py",
    "src/research_foundry/services/external_research_import.py",
    "src/research_foundry/services/source_acquisition_policy.py",
]

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Authority-shaped definitions that would indicate a SECOND edition/passage/
# source-assertion/citation-tuple authority being minted inside ERI's own
# files, rather than reused from `AssertionRegistry`. Enumerated by exact
# name so a coincidental substring match (e.g. a comment mentioning
# "passage") can never false-positive.
_FORBIDDEN_DEFINITIONS = [
    "class SourceEdition",
    "class Passage(",
    "class SourceAssertion",
    "def ingest_edition(",
    "def find_exact_passages(",  # AssertionRegistry's own method; ERI must call it, not redefine it
    "def resolve_passage(",
    "class ClaimLedger",
]


def test_eri_service_modules_define_no_second_evidence_authority() -> None:
    for rel_path in _ERI_SERVICE_FILES:
        text = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_DEFINITIONS:
            assert forbidden not in text, f"{rel_path} defines {forbidden!r} (contract §3.5 violation)"


def test_eri_resolution_module_calls_the_existing_assertion_registry() -> None:
    """Positive half of the scan: ERI's resolver actually REUSES
    `AssertionRegistry` (imports it) rather than merely avoiding forbidden
    names by not touching evidence identity at all."""

    text = (_REPO_ROOT / "src/research_foundry/services/external_research_resolution.py").read_text(
        encoding="utf-8"
    )
    assert "AssertionRegistry" in text
    assert ".ingest(" in text
    assert ".find_exact_passages(" in text or ".resolve_passage(" in text
