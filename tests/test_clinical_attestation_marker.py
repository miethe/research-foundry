"""clearance-gates-v1 M4 — the `clinical_attestation_status` export marker.

Scope: proves `export_service._build_claims()` attaches
`clinical_attestation_status: "unattested"` to a per-claim export record
IF AND ONLY IF `services.verification.claim_clinical_eligibility()` (the
UNCHANGED function backing RFUP-1 P3-001) finds that claim clinically
eligible -- and that this is the SOLE input. In particular:

* The marker must be present for a claim citing a `pediatric_cds` block with
  `assertion_kind == "threshold"` (AC-M4-1), and ABSENT (key omitted
  entirely, never `null`) for an ordinary claim with no such signal
  (AC-M4-2) -- mirroring the schema's own present/absent-not-null contract
  for `_term_index`/`persistent_references`.
* The marker's presence is UNCHANGED by a `clearance` block's
  `blocked_scopes`, in both directions (AC-M4-3/AC-M4-4): a clinically
  eligible claim gets the marker even when nothing anywhere carries a
  `clearance` stamp (the real-world case for every one of the 7 committed
  pediatric_cds bundles, none of which have ever been touched by the
  clearance-gates feature and never will), and injecting a `clearance` block
  with `blocked_scopes: ["clinical_reliance"]` directly onto a NON-clinical
  claim's cited source card does not conjure the marker into existence --
  proving the derivation path is structurally blind to that key, not merely
  coincidentally unaffected in the fixtures used elsewhere in this suite.
* `CLINICAL_UNATTESTED_MARKER` is a distinct literal from
  `REDACTION_MARKER` (AC-M4-5) -- "shown, unattested" is not "withheld".
"""

from __future__ import annotations

from typing import Any

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service as svc
from research_foundry.yamlio import dump_yaml

# Same shape tests/test_verification_clinical_eligibility.py uses for its own
# `claim_clinical_eligibility()` unit tests -- reused here so this test rests
# on the same real-world pediatric_cds block shape, not a hand-simplified one.
_RICH_THRESHOLD_POINT: dict[str, Any] = {
    "evidence_id": "ev_1",
    "locator": "p.1",
    "summary": "threshold point",
    "quote": "Hgb < 11.0 g/dL",
    "pediatric_cds": {
        "schema_version": "1.0",
        "evidence_role": "threshold",
        "implementable_statement": {
            "kind": "rule_candidate",
            "value_or_formula": "< 11.0",
            "portability": "universal",
            "assertion_kind": "threshold",
            "exact_passage_required": True,
        },
    },
}

_ORDINARY_POINT: dict[str, Any] = {
    "evidence_id": "ev_2",
    "locator": "p.2",
    "summary": "ordinary point",
    "quote": "Ordinary non-clinical quote",
}


def _source_card(sid: str, points: list[dict[str, Any]], *, clearance: dict[str, Any] | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": sid,
        "sensitivity": "public",
        "source": {"title": f"Source {sid}", "source_type": "web",
                   "locator": {"url": f"https://example.test/{sid}"}},
        "trust": {"source_rank": "primary"},
        "usage": {"allowed_for_public_output": True},
        "extracted_points": points,
    }
    if clearance is not None:
        # AC-M4-4: injected directly, in a shape no real writer ever produces
        # (clearance rides on source_attribution records, per
        # config/clearance_gates.yaml's applies_to_kinds -- never on a source
        # card's own frontmatter) precisely so the test does not depend on
        # any writer plumbing this through correctly. If _build_claims() ever
        # started reading this key, this fixture would make that visible.
        meta["clearance"] = clearance
    return meta


def _build_run(paths: FoundryPaths, run_id: str) -> None:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": "intent_clinical_marker",
            "status": "planned",
            "sensitivity": "public",
            "created_at": "2026-08-05T00:00:00-04:00",
        },
        rp.run_yaml,
    )

    dump_md(
        _source_card("src_threshold", [_RICH_THRESHOLD_POINT]),
        "",
        rp.sources / "src_threshold.md",
    )
    dump_md(
        _source_card("src_ordinary", [_ORDINARY_POINT]),
        "",
        rp.sources / "src_ordinary.md",
    )
    # AC-M4-4: an ordinary (non-clinical) card carrying a clearance stamp
    # with blocked_scopes including clinical_reliance -- must NOT make the
    # marker appear on a claim that cites only this card.
    #
    # clearance-gates-v1 M5 note: `blocked_scopes` here is deliberately
    # `["clinical_reliance"]` ONLY -- NOT `["redistribution", ...]`.
    # export_service._resolve_source now calls
    # clearance.mediate_egress(..., target_scope="redistribution") on every
    # citation's raw card BEFORE this module's clinical-marker derivation
    # ever runs (M5, a real, separate control this suite does not exercise
    # -- see tests/test_clearance_egress_m5.py for that). A card genuinely
    # stamped `blocked_scopes` containing "redistribution" is now REFUSED at
    # export time, which would make `_export()` below raise instead of
    # returning -- an entirely different (and, for THIS suite, undesired)
    # failure mode. Restricting the fixture's stamp to `clinical_reliance`
    # keeps this suite's actual claim -- clinical-marker derivation is blind
    # to a `clearance` stamp -- exercisable without also tripping M5's own,
    # independently-tested, mediation control.
    dump_md(
        _source_card(
            "src_ordinary_tainted",
            [_ORDINARY_POINT],
            clearance={
                "schema_version": "1.0",
                "blocked_scopes": ["clinical_reliance"],
                "stamped_at": "2026-08-05T00:00:00-04:00",
                "stamped_by": "test-fixture",
                "posture_at_stamp": "dev_test",
                "gate_refs": ["CLIN-ATTEST"],
            },
        ),
        "",
        rp.sources / "src_ordinary_tainted.md",
    )

    dump_yaml(
        {
            "schema_version": "0.1",
            "claims": [
                {
                    "claim_id": "clm_clinical",
                    "text": "A threshold-eligible clinical claim.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [{"source_card_id": "src_threshold", "evidence_id": "ev_1",
                                 "relation": "supports", "locator": "p.1"}],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                },
                {
                    "claim_id": "clm_ordinary",
                    "text": "An ordinary, non-clinical claim.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [{"source_card_id": "src_ordinary", "evidence_id": "ev_2",
                                 "relation": "supports", "locator": "p.2"}],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                },
                {
                    "claim_id": "clm_tainted_ordinary",
                    "text": "An ordinary claim citing a clearance-tainted card.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [{"source_card_id": "src_ordinary_tainted", "evidence_id": "ev_2",
                                 "relation": "supports", "locator": "p.2"}],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                },
            ],
        },
        rp.claim_ledger,
    )

    dump_yaml(
        {"run_id": run_id, "passed": True, "exit_code": 0,
         "checks": [{"id": "check_01", "severity": "error", "status": "pass",
                     "detail": "ok", "locations": []}]},
        rp.verification,
    )

    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 3, "claims_supported": 3},
            "governance": {"sensitivity": "public", "approved_for_writeback": False},
        },
        rp.evidence_bundle,
    )

    rp.report_draft.write_text(
        "# Report\n\n[claim:clm_clinical] [claim:clm_ordinary] [claim:clm_tainted_ordinary]\n",
        encoding="utf-8",
    )


def _export(paths: FoundryPaths, run_id: str) -> dict[str, dict[str, Any]]:
    data = svc.export_run(paths, run_id)
    assert data is not None
    return {c["claim_id"]: c for c in data["claims"]}


def test_clinically_eligible_claim_gets_unattested_marker(tmp_foundry: FoundryPaths) -> None:
    """AC-M4-1: a claim citing a threshold pediatric_cds block is marked."""
    run_id = "rf_run_clinical_marker_001"
    _build_run(tmp_foundry, run_id)
    claims = _export(tmp_foundry, run_id)

    assert claims["clm_clinical"]["clinical_attestation_status"] == svc.CLINICAL_UNATTESTED_MARKER
    assert svc.CLINICAL_UNATTESTED_MARKER == "unattested"


def test_ordinary_claim_omits_the_key_entirely(tmp_foundry: FoundryPaths) -> None:
    """AC-M4-2: absent, not null -- same present/absent-not-null contract as
    `_term_index`/`persistent_references` (never emit a false-negative `null`
    a viewer could mistake for an assessed-and-cleared signal)."""
    run_id = "rf_run_clinical_marker_002"
    _build_run(tmp_foundry, run_id)
    claims = _export(tmp_foundry, run_id)

    assert "clinical_attestation_status" not in claims["clm_ordinary"]


def test_marker_presence_is_blind_to_a_clearance_stamp(tmp_foundry: FoundryPaths) -> None:
    """AC-M4-4: injecting `clearance.blocked_scopes` (including
    `clinical_reliance`) directly onto a cited, non-clinical source card does
    NOT cause the marker to appear. Proves the derivation path never reads
    that key -- not merely that today's fixtures happen not to trigger it."""
    run_id = "rf_run_clinical_marker_003"
    _build_run(tmp_foundry, run_id)
    claims = _export(tmp_foundry, run_id)

    assert "clinical_attestation_status" not in claims["clm_tainted_ordinary"]


def test_marker_present_with_zero_clearance_stamps_anywhere_in_the_run(tmp_foundry: FoundryPaths) -> None:
    """AC-M4-3: the real-world shape of all 7 committed pediatric_cds
    bundles -- no `clearance` block anywhere in the run, ever (they predate
    clearance-gates entirely and are structurally incapable of carrying a
    stamp). The marker must still fire from claim_clinical_eligibility()
    alone."""
    run_id = "rf_run_clinical_marker_004"
    _build_run(tmp_foundry, run_id)
    claims = _export(tmp_foundry, run_id)

    # None of this run's source cards/claims carry a `clearance` key at all
    # except the deliberately-injected one in src_ordinary_tainted (used by
    # the sibling test above) -- clm_clinical's own cited card carries none.
    assert claims["clm_clinical"]["clinical_attestation_status"] == "unattested"


def test_clinical_marker_is_a_distinct_literal_from_the_redaction_marker() -> None:
    """AC-M4-5: "shown, unattested" (CLINICAL_UNATTESTED_MARKER) must never
    collide with "withheld" (REDACTION_MARKER) -- they mean opposite things."""
    assert svc.CLINICAL_UNATTESTED_MARKER != svc.REDACTION_MARKER


def test_derivation_never_references_clearance_blocked_scopes_by_source() -> None:
    """Static proof, complementing the behavioural tests above: the
    EXECUTABLE code of the functions that compute
    `clinical_attestation_status` (`_build_claims`/`_clinical_source_index`)
    never references `clearance`/`blocked_scopes` as a dict key, attribute,
    or identifier -- only their own explanatory comments/docstrings do (which
    exist specifically to document the non-dependency, so those are
    deliberately excluded from this check rather than making the comment
    itself a test failure)."""
    import ast
    import inspect
    import textwrap

    for fn in (svc._build_claims, svc._clinical_source_index):
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                identifiers.add(node.value)
        assert "blocked_scopes" not in identifiers
        assert "clearance" not in identifiers
