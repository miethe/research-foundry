"""Tests for the M5 clearance-gates egress-mediation wiring in ``writeback.py``.

M2 built ``clearance.mediate_egress``/``writeback.mediate_run_egress`` and wired
them into exactly one of the module's real dispatch surfaces (the ``notebooklm``
branch of ``writeback()``). This file proves the M5 fix: every real egress
surface in ``writeback.py`` — all six ``writeback()`` target branches,
``governed_writeback()``'s MeatyWiki emit, and ``approve_and_dispatch()``'s three
dispatch branches — now calls ``mediate_run_egress`` on the run's RAW source-card
records before its render/dispatch primitive runs, and a governed-and-blocked
record refuses egress rather than being silently shipped.

Every "denied" test here is a BEHAVIOUR DELTA, not an existence check: each one
asserts that the target's OWN output file/network call never happened — the
exact failure mode an unmediated ``writeback()``/``governed_writeback()``/
``approve_and_dispatch()`` would exhibit (write the file / POST the payload
regardless of the stamp). Fixture-only: no real run corpus, no network.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import clearance, writeback
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.clearance import ClearanceDenied, MediationClearance
from research_foundry.services.extraction import extract_run
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.swarm_drive import drive_run
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import load_yaml

_IDEA = (
    "Research how agentic research workflows should handle evidence bundles and "
    "claim traceability across cheap extraction and deep synthesis models. "
    "Studies show 40% of unsupported claims come from synthesis drift."
)

_SOURCE_TEXT = (
    "Evidence bundles let a research run carry its sources, claims, and a report "
    "in one auditable package. A 2025 study found that 40% of unsupported claims "
    "originate during synthesis when extraction and synthesis use different models. "
    "Claim ledgers reduce citation mismatch by mapping every material sentence to "
    "an evidence id. Limitations: small sample, single domain."
)

_INTENT_ID = "intent_research_20260721_clr"


def _build_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    """Drive the deterministic pipeline and return the run_id (mirrors
    ``tests/test_writebacks.py::_build_run``)."""

    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    assert tri.intent_id
    plan = plan_run(tri.intent_id, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / "input_source.txt"
    src_file.write_text(_SOURCE_TEXT, encoding="utf-8")
    ingest_source(
        str(src_file),
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        title="Evidence bundles and claim traceability",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


def _stamp_a_source_card(paths: FoundryPaths, run_id: str, *, blocked_scopes) -> None:
    """Inject a durable clearance taint into the run's first source card.

    Uses the real ``clearance.stamp_taint`` builder (M3's write side) so the
    fixture matches exactly what a real stamping writer would produce.
    """

    rp = paths.run_paths(run_id)
    card_paths = sorted(rp.sources.glob("*.md"))
    assert card_paths, "expected at least one source card"
    card_path = card_paths[0]
    meta, body = load_md(card_path)
    meta["clearance"] = clearance.stamp_taint(
        blocked_scopes=blocked_scopes,
        stamped_by="test_fixture",
        posture_at_stamp="dev_test",
    )
    dump_md(meta, body, card_path)


# --------------------------------------------------------------------------- #
# Regression floor: an UNSTAMPED run (the real shape of every pre-existing
# record, including the 7 committed pediatric bundles) is a mediation no-op.
# --------------------------------------------------------------------------- #


def test_unstamped_source_cards_yield_a_zero_record_clearance(tmp_foundry: FoundryPaths):
    """Proves the mechanism, not just the outcome.

    A source card with NO ``clearance`` block at all (the shape of every
    record that predates this feature) is never added to
    ``_stamped_attribution_records``'s return list — so
    ``mediate_run_egress`` sees zero records and cannot deny, regardless of
    whether ``source_attribution`` is a governed kind. This is the mechanism
    that keeps the 7 committed pediatric bundles (verified independently to
    carry no ``clearance:`` key in any of their source cards) passing.
    """

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)

    # Sanity: the fixture really has no clearance block anywhere (matches the
    # 7 pediatric bundles' real on-disk shape, verified separately against
    # main's runs/ corpus).
    for card_path in rp.sources.glob("*.md"):
        meta, _ = load_md(card_path)
        assert clearance.TAINT_KEY not in meta

    token = writeback.mediate_run_egress(rp, target="meatywiki", paths=paths)
    assert isinstance(token, MediationClearance)
    assert token.record_count == 0


def test_unstamped_run_writeback_all_six_targets_raises_no_clearance_denial(
    tmp_foundry: FoundryPaths,
):
    """The positive control: mediation wired into all six branches must not
    turn into an always-deny — an unstamped run must still ship."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    # All six real target names; the live network legs (intenttree/arc/
    # notebooklm) degrade offline as usual — the only thing under test here
    # is that none of the six raises ClearanceDenied for an unstamped run.
    result = writeback.writeback(
        run_id,
        targets=("meatywiki", "skillmeat", "ccdash", "intenttree", "arc", "notebooklm"),
        paths=paths,
    )
    assert result.meatywiki_path and result.meatywiki_path.exists()
    assert result.skillbom_path and result.skillbom_path.exists()
    assert result.ccdash_path and result.ccdash_path.exists()


# --------------------------------------------------------------------------- #
# writeback(): every one of the six target branches now mediates BEFORE
# rendering. Each case is a genuine behaviour delta — the target's own output
# file must never be created.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "target,output_attr",
    [
        ("meatywiki", "meatywiki_writeback"),
        ("skillmeat", "skillbom_candidate"),
        ("ccdash", "ccdash_event"),
        ("intenttree", "intenttree_update"),
        ("arc", "arc_review_request"),
    ],
)
def test_writeback_denies_and_never_writes_target_output_when_blocked(
    tmp_foundry: FoundryPaths, target: str, output_attr: str
):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _stamp_a_source_card(paths, run_id, blocked_scopes=["redistribution"])
    rp = paths.run_paths(run_id)
    output_path = getattr(rp, output_attr)

    with pytest.raises(ClearanceDenied):
        writeback.writeback(run_id, targets=(target,), paths=paths)

    # The behaviour delta: without mediation, the render primitive would have
    # written this file unconditionally. With mediation wired in, the render
    # call is never reached.
    assert not output_path.exists(), (
        f"{output_attr} must not exist — {target}'s render primitive must "
        "never run once mediation has denied egress"
    )


def test_writeback_denial_is_scope_specific_not_a_blanket_deny(tmp_foundry: FoundryPaths):
    """Companion to the parametrized denial test above: a record blocked for
    ``clinical_reliance`` only must NOT deny a ``redistribution``-scoped
    writeback target — without this, a function that always denies would
    pass the tests above."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _stamp_a_source_card(paths, run_id, blocked_scopes=["clinical_reliance"])
    rp = paths.run_paths(run_id)

    result = writeback.writeback(run_id, targets=("meatywiki",), paths=paths)
    assert result.meatywiki_path and result.meatywiki_path.exists()
    assert rp.meatywiki_writeback.exists()


# --------------------------------------------------------------------------- #
# governed_writeback(): mediation must be ADDITIVE to redact_payload, and it
# must run BEFORE either the auto-emit or the HITL-gate dispatch path.
# --------------------------------------------------------------------------- #


class _MockMeatyWiki:
    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self.posts: list[dict[str, Any]] = []

    def available(self, timeout: float = 2.0) -> bool:
        return self._available

    def post_note(self, payload):
        self.posts.append(payload)
        return {"note_id": f"note_{len(self.posts)}", "status": "written"}


class _MockIntentTree:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    def request_create(self, *, node_id=None, kind, title, body="", artifacts=None, sensitivity=None):
        self.created.append({"kind": kind, "title": title})
        return {"request_id": "req_1", "status": "pending"}

    def request_status(self, request_id):
        return {"request_id": request_id, "status": "pending"}


def _planned_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    from research_foundry.yamlio import dump_yaml

    intent = {
        "id": _INTENT_ID,
        "title": "Clearance-gates mediation demo topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Exercise the governed writeback + clearance mediation gate.",
        "governance": {
            "sensitivity": sensitivity,
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")
    from research_foundry.services import planning

    result = planning.plan_run(_INTENT_ID, profile="personal", paths=paths)
    run_id = result.run_id
    rp = paths.run_paths(run_id)
    meta = load_yaml(rp.run_yaml)
    meta["sensitivity"] = sensitivity
    dump_yaml(meta, rp.run_yaml)
    return run_id


def _seed_and_drive_to_bundle(paths: FoundryPaths, run_id: str, tmp_path) -> None:
    from research_foundry.services import extraction, source_cards
    from research_foundry.yamlio import dump_yaml

    rp = paths.run_paths(run_id)
    doc = tmp_path / "evidence.txt"
    doc.write_text(
        "Latency dropped 30% with the new router.\n\n"
        "Teams report fewer escalations than before, according to the survey.\n\n"
        "Evidence bundles make claim traceability auditable end to end.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(str(doc), run_id=run_id, title="Evidence Source", paths=paths)
    extraction.extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=_INTENT_ID, paths=paths)
    dump_yaml({"source_candidates": []}, rp.source_candidates)
    drive_run(run_id, llm_legs="none", paths=paths, providers={}, writeback=False)


def test_governed_writeback_auto_path_denies_before_post_note_when_blocked(
    tmp_foundry: FoundryPaths, tmp_path
):
    """The auto (personal+verified) path must mediate BEFORE the network POST.

    The behaviour delta: the mock client's ``post_note`` must record ZERO
    calls — proving the denial happened before the irreversible network hop,
    not merely that the function raised somewhere.
    """

    run_id = _planned_run(tmp_foundry, sensitivity="personal")
    _seed_and_drive_to_bundle(tmp_foundry, run_id, tmp_path)
    _stamp_a_source_card(tmp_foundry, run_id, blocked_scopes=["redistribution"])

    mw = _MockMeatyWiki(available=True)
    with pytest.raises(ClearanceDenied):
        writeback.governed_writeback(run_id, paths=tmp_foundry, meatywiki_client=mw, poll_interval=0)

    assert mw.posts == [], "post_note must never be called once mediation has denied egress"


def test_governed_writeback_hitl_path_denies_before_request_create_when_blocked(
    tmp_foundry: FoundryPaths, tmp_path
):
    """The HITL (non-auto) path must ALSO mediate before opening the gate —
    additive to redaction covers both dispatch branches, not just auto-emit.

    Takes the HITL path via a verify-failed (not sensitivity-escalated) run —
    ``swarm_drive.drive_run`` only dispatches personal/public sensitivity, so
    a ``work_sensitive`` run never reaches a bundle at all (GOV-001, an
    unrelated gate); flipping ``approved_for_writeback`` False on an
    otherwise-personal run is the same technique
    ``test_swarm_governance.py::_mark_verify_failed`` uses.
    """

    run_id = _planned_run(tmp_foundry, sensitivity="personal")
    _seed_and_drive_to_bundle(tmp_foundry, run_id, tmp_path)
    rp = tmp_foundry.run_paths(run_id)
    bundle = load_yaml(rp.evidence_bundle)
    bundle["governance"]["approved_for_writeback"] = False
    from research_foundry.yamlio import dump_yaml

    dump_yaml(bundle, rp.evidence_bundle)
    _stamp_a_source_card(tmp_foundry, run_id, blocked_scopes=["redistribution"])

    mw = _MockMeatyWiki(available=True)
    it = _MockIntentTree()
    with pytest.raises(ClearanceDenied):
        writeback.governed_writeback(
            run_id, paths=tmp_foundry, meatywiki_client=mw, intenttree_client=it, poll_interval=0
        )

    assert it.created == [], "request_create must never fire once mediation has denied egress"
    assert mw.posts == []


def test_governed_writeback_unstamped_run_still_auto_emits(tmp_foundry: FoundryPaths, tmp_path):
    """Positive control: an unstamped run must still emit through the auto path."""

    run_id = _planned_run(tmp_foundry, sensitivity="personal")
    _seed_and_drive_to_bundle(tmp_foundry, run_id, tmp_path)

    mw = _MockMeatyWiki(available=True)
    res = writeback.governed_writeback(run_id, paths=tmp_foundry, meatywiki_client=mw, poll_interval=0)
    assert res.status == "written"
    assert len(mw.posts) == 1


# --------------------------------------------------------------------------- #
# approve_and_dispatch(): per-target isolation must catch a ClearanceDenied
# exactly like any other target-local failure — "failed", never a crash, and
# never a file on disk for that target.
# --------------------------------------------------------------------------- #


def test_approve_and_dispatch_marks_blocked_targets_denied_not_failed(tmp_foundry: FoundryPaths):
    """M5 gate fix, half 1 of the PAIR.

    A clearance refusal must land the DISTINCT ``"denied"`` status, not the
    generic ``"failed"``. Paired with
    ``test_approve_and_dispatch_marks_transient_fault_failed_not_denied``
    below — neither half alone can show the two are actually
    distinguishable: this one passes against an implementation that hardcodes
    every outcome to ``"denied"``, and that one passes against the
    pre-fix implementation that flattened everything to ``"failed"``.
    """

    paths = tmp_foundry
    run_id = _build_run(paths)
    _stamp_a_source_card(paths, run_id, blocked_scopes=["redistribution"])
    rp = paths.run_paths(run_id)

    result = writeback.approve_and_dispatch(
        run_id, targets=("ccdash", "meatywiki", "skillmeat"), paths=paths
    )

    assert result.target_status == {
        "ccdash": "denied",
        "meatywiki": "denied",
        "skillmeat": "denied",
    }
    for status in result.target_status.values():
        assert status in writeback.APPROVE_DISPATCH_TARGET_STATUSES
    # See the aggregation comment in approve_and_dispatch: "partial" is
    # deliberate — the router pins overall_status to Literal["success",
    # "partial"], so a new member would surface as an opaque HTTP 500.
    assert result.overall_status == "partial"
    # Retained from the original assertion: none of the three targets' output
    # files exist — each render call was skipped by the mediation check.
    assert not rp.ccdash_event.exists()
    assert not rp.meatywiki_writeback.exists()
    assert not rp.skillbom_candidate.exists()


def test_approve_and_dispatch_marks_transient_fault_failed_not_denied(
    tmp_foundry: FoundryPaths,
):
    """M5 gate fix, half 2 of the PAIR — the SAME target, a transient fault.

    ``meatywiki`` raises an ordinary ``RuntimeError`` (a renderer blowing up,
    a network error) on an UNSTAMPED run, so nothing is denied. It must be
    recorded ``"failed"``, while its two siblings still succeed. Together with
    the denial half above this proves the two outcomes are genuinely
    distinguishable rather than one label applied to both.
    """

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)

    def _raise(*args: Any, **kwargs: Any):
        raise RuntimeError("forced transient meatywiki failure for test")

    from unittest.mock import patch

    with patch.object(writeback, "_render_meatywiki", side_effect=_raise):
        result = writeback.approve_and_dispatch(
            run_id, targets=("ccdash", "meatywiki", "skillmeat"), paths=paths
        )

    assert result.target_status["meatywiki"] == "failed", (
        "a transient fault must NOT be reported as 'denied' — that would make "
        "the new status meaningless"
    )
    assert result.target_status["ccdash"] == "success"
    assert result.target_status["skillmeat"] == "success"
    assert "denied" not in result.target_status.values()
    assert result.overall_status == "partial"
    assert not rp.meatywiki_writeback.exists()


def test_approve_and_dispatch_denial_and_transient_fault_are_different_strings(
    tmp_foundry: FoundryPaths,
):
    """The pair's conclusion, asserted directly on the SAME target.

    ``meatywiki`` is driven down both paths in one test and the two resulting
    status strings are compared. Without the M5 fix both are ``"failed"`` and
    this assertion fails — which is exactly the defect the gate found.
    """

    from unittest.mock import patch

    paths = tmp_foundry

    # Path A — clearance refusal.
    denied_run = _build_run(paths)
    _stamp_a_source_card(paths, denied_run, blocked_scopes=["redistribution"])
    denied_status = writeback.approve_and_dispatch(
        denied_run, targets=("meatywiki",), paths=paths
    ).target_status["meatywiki"]

    # Path B — transient fault, same target, nothing stamped.
    faulted_run = _build_run(paths)

    def _raise(*args: Any, **kwargs: Any):
        raise RuntimeError("forced transient meatywiki failure for test")

    with patch.object(writeback, "_render_meatywiki", side_effect=_raise):
        faulted_status = writeback.approve_and_dispatch(
            faulted_run, targets=("meatywiki",), paths=paths
        ).target_status["meatywiki"]

    assert denied_status != faulted_status, (
        f"a policy refusal ({denied_status!r}) and a transient fault "
        f"({faulted_status!r}) must not share one status value"
    )
    assert denied_status == "denied"
    assert faulted_status == "failed"


def test_approve_and_dispatch_denial_records_governance_exit_code_in_trace(
    tmp_foundry: FoundryPaths,
):
    """``ExitCode.GOVERNANCE`` is preserved, not discarded.

    ``ApproveDispatchResult`` has nowhere to carry an integer exit code (its
    field set is frozen by ORC-001), so the classification is written to the
    run trace. Asserts the real numeric value of ``ExitCode.GOVERNANCE``
    reached disk — not merely that some trace line was emitted.
    """

    from research_foundry.errors import ExitCode

    paths = tmp_foundry
    run_id = _build_run(paths)
    _stamp_a_source_card(paths, run_id, blocked_scopes=["redistribution"])
    rp = paths.run_paths(run_id)

    writeback.approve_and_dispatch(run_id, targets=("meatywiki",), paths=paths)

    trace_lines = [
        __import__("json").loads(line)
        for line in rp.run_trace.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    denials = [ln for ln in trace_lines if ln.get("stage") == "approve_dispatch_clearance_denied"]
    assert denials, "the denial must be traced so the GOVERNANCE class is not lost"
    assert denials[0]["target"] == "meatywiki"
    assert denials[0]["exit_code"] == int(ExitCode.GOVERNANCE)


def test_writeback_audits_a_clearance_denial_as_denied_not_failure(
    tmp_foundry: FoundryPaths,
):
    """``writeback()``'s own conflation, closed in the same pass.

    Its ``except RFError`` audited a governance refusal ``result="failure"``,
    identical to a schema error. It must now audit ``result="denied"`` — the
    third first-class ``AuditEvent.result`` value — while still re-raising the
    ``ClearanceDenied`` unchanged.
    """

    from unittest.mock import patch

    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    _stamp_a_source_card(paths, run_id, blocked_scopes=["redistribution"])

    with patch.object(writeback.audit_service, "record_event") as mock_record:
        with pytest.raises(ClearanceDenied) as exc:
            writeback.writeback(run_id, targets=("meatywiki",), paths=paths)

    from research_foundry.errors import ExitCode

    assert exc.value.exit_code == ExitCode.GOVERNANCE
    assert mock_record.call_count == 1
    event = mock_record.call_args[0][1]
    assert event.result == "denied", (
        "a governance refusal must not be audited as a generic 'failure'"
    )
    assert event.action == "writeback"


def test_writeback_audits_an_ordinary_rferror_as_failure(tmp_foundry: FoundryPaths):
    """The companion half — a NON-clearance ``RFError`` on the same surface
    must still audit ``result="failure"``, or the ``"denied"`` value above
    would be meaningless."""

    from unittest.mock import patch

    from research_foundry.errors import SchemaError

    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    def _raise(*args: Any, **kwargs: Any):
        raise SchemaError("forced non-clearance RFError for test")

    with patch.object(writeback, "_render_meatywiki", side_effect=_raise):
        with patch.object(writeback.audit_service, "record_event") as mock_record:
            with pytest.raises(SchemaError):
                writeback.writeback(run_id, targets=("meatywiki",), paths=paths)

    assert mock_record.call_count == 1
    assert mock_record.call_args[0][1].result == "failure"


def test_approve_and_dispatch_unstamped_run_still_succeeds(tmp_foundry: FoundryPaths):
    """Positive control for the per-target mediation wiring above."""

    paths = tmp_foundry
    run_id = _build_run(paths)

    result = writeback.approve_and_dispatch(
        run_id, targets=("ccdash", "meatywiki", "skillmeat"), paths=paths
    )
    assert result.overall_status == "success"
    assert result.target_status == {
        "ccdash": "success",
        "meatywiki": "success",
        "skillmeat": "success",
    }
