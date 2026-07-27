"""Unit tests for the D13 Report Builder draft verification checks (P3 Wave D).

Covers each standalone check (pass + fail) plus the ``verify_draft``
aggregate, including the sensitivity fail-closed guarantee: a draft body
embedding a raw ``client_sensitive`` quote must refuse a ``public`` publish
(spec §11), while the same claim referenced only structurally (no raw quote
pasted into the body) passes.
"""

from __future__ import annotations

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.errors import ExitCode
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import builder_service as bsvc
from research_foundry.services import verification as vsvc
from research_foundry.yamlio import dump_yaml

_SENSITIVE_QUOTE = "THE CLIENT CONFIDENTIAL FIGURE IS $42 MILLION."


def _plant_run_with_sensitive_source(paths: FoundryPaths, run_id: str) -> None:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": "public",
            "created_at": "2026-06-13T09:41:00+00:00",
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_client",
            "sensitivity": "client_sensitive",
            "source": {"title": "Client Deck", "source_type": "document"},
            "trust": "high",
            "usage": "direct",
            "extracted_points": [
                {
                    "evidence_id": "ev_client",
                    "locator": "p1",
                    "summary": "client figure",
                    "quote": _SENSITIVE_QUOTE,
                }
            ],
        },
        "",
        rp.sources / "src_client.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_client",
                    "text": "The client figure is large.",
                    "materiality": "core",
                    "claim_type": "quantitative",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_client",
                            "evidence_id": "ev_client",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        rp.claim_ledger,
    )


# ---------------------------------------------------------------------------
# check_paragraph_has_support
# ---------------------------------------------------------------------------


def test_paragraph_has_support_fails_on_unlinked_material_block() -> None:
    blocks = [
        {"block_id": "blk_1", "block_type": "paragraph", "materiality": "material", "linked_claim_ids": []},
    ]
    result = vsvc.check_paragraph_has_support(blocks)
    assert result.status == "fail"
    assert "blk_1" in result.locations


def test_paragraph_has_support_passes_when_linked_or_exempt() -> None:
    blocks = [
        {"block_id": "blk_1", "block_type": "paragraph", "materiality": "material", "linked_claim_ids": ["clm_a"]},
        {"block_id": "blk_2", "block_type": "paragraph", "materiality": "narrative", "linked_claim_ids": []},
        {"block_id": "blk_3", "block_type": "heading", "materiality": "material", "linked_claim_ids": []},
    ]
    result = vsvc.check_paragraph_has_support(blocks)
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# check_claim_tags_resolve
# ---------------------------------------------------------------------------


def test_claim_tags_resolve_fails_on_unknown_tag() -> None:
    blocks = [{"block_id": "blk_1", "markdown": "Some text. [claim:clm_ghost]"}]
    result = vsvc.check_claim_tags_resolve(blocks, known_claim_ids={"clm_a"})
    assert result.status == "fail"
    assert "clm_ghost" in result.locations


def test_claim_tags_resolve_passes_when_known() -> None:
    blocks = [{"block_id": "blk_1", "markdown": "Some text. [claim:clm_a]"}]
    result = vsvc.check_claim_tags_resolve(blocks, known_claim_ids={"clm_a"})
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# check_anchor_hash_match
# ---------------------------------------------------------------------------


def test_anchor_hash_match_detects_drift(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Hash Drift Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Original text.")
    block_id = draft["blocks"][0]["block_id"]
    draft = bsvc.add_claim_link(tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_a")

    # Not yet drifted.
    result = vsvc.check_anchor_hash_match(draft["blocks"], draft["claim_links"])
    assert result.status == "pass"

    # Mutate the block's text directly (bypassing update_block on purpose —
    # simulating stale in-memory state / a hand-authored diff).
    draft["blocks"][0]["markdown"] = "Completely different text."
    result = vsvc.check_anchor_hash_match(draft["blocks"], draft["claim_links"])
    assert result.status == "fail"
    assert draft["claim_links"][0]["claim_link_id"] in result.locations


# ---------------------------------------------------------------------------
# check_report_body_sensitivity
# ---------------------------------------------------------------------------


def test_report_body_sensitivity_fails_on_raw_quote_leak(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_leak")
    blocks = [{"block_id": "blk_1", "markdown": f"The figure was huge: {_SENSITIVE_QUOTE}"}]
    source_links = [{"source_card_id": "src_client", "run_id": "rf_run_leak"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry, blocks, source_links, sensitivity_threshold="public"
    )
    assert result.status == "fail"
    assert "src_client" in result.detail


def test_report_body_sensitivity_passes_without_raw_quote(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_safe")
    blocks = [{"block_id": "blk_1", "markdown": "The client figure is large. [claim:clm_client]"}]
    source_links = [{"source_card_id": "src_client", "run_id": "rf_run_safe"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry, blocks, source_links, sensitivity_threshold="public"
    )
    assert result.status == "pass"


def test_report_body_sensitivity_fails_on_unlinked_raw_quote_leak(tmp_foundry: FoundryPaths) -> None:
    """R2 CRITICAL fix: spec §11's dangerous case is the UNLINKED one — a raw
    sensitive quote pasted into the body with NO source_link (and no
    claim_link) pointing at it. The check previously only scanned source
    cards that already had a matching source_links[] entry, so this exact
    case sailed through. Reachability now comes from source_run_id (a draft
    created ``from_run``), so the full source corpus of that run is scanned
    regardless of whether any individual card was explicitly linked."""
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_leak_unlinked")
    blocks = [{"block_id": "blk_1", "markdown": f"The figure was huge: {_SENSITIVE_QUOTE}"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry,
        blocks,
        source_links=[],
        source_run_id="rf_run_leak_unlinked",
        sensitivity_threshold="public",
    )
    assert result.status == "fail"
    assert "src_client" in result.detail


def test_report_body_sensitivity_passes_at_matching_threshold(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_matched")
    blocks = [{"block_id": "blk_1", "markdown": f"Raw quote: {_SENSITIVE_QUOTE}"}]
    source_links = [{"source_card_id": "src_client", "run_id": "rf_run_matched"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry, blocks, source_links, sensitivity_threshold="client_sensitive"
    )
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# verify_draft aggregate
# ---------------------------------------------------------------------------


def test_verify_draft_passes_clean_draft(tmp_foundry: FoundryPaths) -> None:
    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_verify_ok")
    draft = bsvc.create_draft_from_run(tmp_foundry, run_id="rf_run_verify_ok")

    result = vsvc.verify_draft(tmp_foundry, draft["report_draft_id"])
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert result.verification_path.exists()


def test_verify_draft_fails_closed_on_sensitive_quote_leak(tmp_foundry: FoundryPaths) -> None:
    """A report body embedding a client_sensitive quote must refuse public export."""

    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_verify_leak")
    draft = bsvc.create_draft(tmp_foundry, title="Leaky Draft", sensitivity="public")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(
        tmp_foundry, report_draft_id, markdown=f"The client figure was: {_SENSITIVE_QUOTE} [claim:clm_client]"
    )
    block_id = draft["blocks"][0]["block_id"]
    bsvc.add_claim_link(
        tmp_foundry,
        report_draft_id,
        block_id=block_id,
        claim_id="clm_client",
        source_run_id="rf_run_verify_leak",
        insert_tag=False,
    )
    bsvc.add_source_link(
        tmp_foundry,
        report_draft_id,
        source_card_id="src_client",
        run_id="rf_run_verify_leak",
        block_id=block_id,
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    sensitivity_check = next(c for c in result.checks if c.id == "report_body_sensitivity")
    assert sensitivity_check.status == "fail"
    assert result.verification_path.exists()


def test_verify_draft_fails_closed_on_unlinked_sensitive_quote(tmp_foundry: FoundryPaths) -> None:
    """R2 CRITICAL fix, aggregate level: a draft created ``from`` a run (so
    its ``source_run_id`` makes that run's sources reachable) that pastes a
    raw client_sensitive quote into a block with NO claim_link and NO
    source_link at all must still fail publish-preview — the unlinked case is
    the one with zero governance trail, and is the one spec §11 is actually
    worried about."""

    _plant_run_with_sensitive_source(tmp_foundry, "rf_run_verify_unlinked")
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Unlinked Leak",
        sensitivity="public",
        source_run_id="rf_run_verify_unlinked",
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Some narrative text: {_SENSITIVE_QUOTE}",
        materiality="narrative",
    )
    # Deliberately no claim_link, no source_link to src_client.

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    sensitivity_check = next(c for c in result.checks if c.id == "report_body_sensitivity")
    assert sensitivity_check.status == "fail"


# ---------------------------------------------------------------------------
# F7(a) (DI-1 delta re-audit): build_global_source_index / the
# report_body_sensitivity_global check must not be a cross-workspace
# quote-match oracle. Before the fix, build_global_source_index iterated
# EVERY run regardless of workspace ownership, so a caller could paste a
# GUESSED quote into their own draft's body and learn -- via a "fail" result
# naming the foreign source_card_id + run_id in `locations` -- that the
# guess matched content in another workspace's private source. The fix
# scopes the scanned runs to those the caller may read (own workspace or
# public), via the same DF-004 gate export_run() already applies.
# ---------------------------------------------------------------------------

_WS_MINE_QUOTE = "THE WS-MINE OWN FIGURE IS $11 MILLION."
_WS_OTHER_QUOTE = "THE WS-OTHER PRIVATE FIGURE IS $99 MILLION."


def _plant_run_with_workspace_quote(
    paths: FoundryPaths,
    *,
    run_id: str,
    workspace_id: str | None,
    source_card_id: str,
    quote: str,
) -> None:
    """Minimal run + one client_sensitive source card carrying *quote*,
    stamped with *workspace_id* -- F7a probe fixture generalizing
    :func:`_plant_run_with_sensitive_source` to vary workspace ownership,
    quote text, and source_card_id per run (needed to build a genuine
    2-workspace matrix)."""

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": "public",
            "created_at": "2026-06-13T09:41:00+00:00",
            "workspace_id": workspace_id,
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": source_card_id,
            "sensitivity": "client_sensitive",
            "source": {"title": "Client Deck", "source_type": "document"},
            "trust": "high",
            "usage": "direct",
            "extracted_points": [
                {
                    "evidence_id": f"ev_{source_card_id}",
                    "locator": "p1",
                    "summary": "probe figure",
                    "quote": quote,
                }
            ],
        },
        "",
        rp.sources / f"{source_card_id}.md",
    )


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same convention as ``tests/test_workspace_isolation_enforcement.py``:
    monkeypatch the real Phase 1 resolver, never a private per-module helper."""

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


def test_build_global_source_index_excludes_cross_workspace_run_under_enforcement(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_mine", workspace_id="ws-mine",
        source_card_id="src_mine", quote=_WS_MINE_QUOTE,
    )
    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_other", workspace_id="ws-other",
        source_card_id="src_other", quote=_WS_OTHER_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    identity = AuthIdentity("u1", "ws-mine", ("researcher",))
    index = vsvc.build_global_source_index(tmp_foundry, identity=identity)
    assert "src_mine" in index
    assert "src_other" not in index


def test_verify_draft_global_scan_does_not_leak_foreign_workspace_quote(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The oracle itself: a ws-mine draft whose body happens to embed
    ws-other's PRIVATE quote verbatim must NOT fail the global sensitivity
    check with ws-other's source_card_id/run_id in `locations` -- that would
    confirm to a ws-mine caller that the guessed quote exists in ws-other's
    private corpus."""

    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_probe_other", workspace_id="ws-other",
        source_card_id="src_other_probe", quote=_WS_OTHER_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    identity = AuthIdentity("u1", "ws-mine", ("owner", "admin", "researcher"))
    draft = bsvc.create_draft(tmp_foundry, title="Probe draft", workspace_id="ws-mine", sensitivity="public")
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Guessed narrative: {_WS_OTHER_QUOTE}",
        materiality="narrative",
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id, identity=identity)
    global_check = next(c for c in result.checks if c.id == "report_body_sensitivity_global")
    assert global_check.status == "pass"
    assert "src_other_probe" not in global_check.detail


def test_verify_draft_global_scan_still_catches_same_workspace_leak(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: the fix must not simply disable the global scan --
    a genuinely-own-workspace cross-run leak is still caught."""

    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_same_ws_source", workspace_id="ws-mine",
        source_card_id="src_mine_leak", quote=_WS_MINE_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    identity = AuthIdentity("u1", "ws-mine", ("owner", "admin", "researcher"))
    draft = bsvc.create_draft(tmp_foundry, title="Same-ws leak", workspace_id="ws-mine", sensitivity="public")
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Copy-pasted: {_WS_MINE_QUOTE}",
        materiality="narrative",
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id, identity=identity)
    global_check = next(c for c in result.checks if c.id == "report_body_sensitivity_global")
    assert global_check.status == "fail"
    assert "src_mine_leak" in global_check.detail


def test_build_global_source_index_identity_none_preserves_existing_behavior(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_none_a", workspace_id="ws-mine",
        source_card_id="src_none_a", quote=_WS_MINE_QUOTE,
    )
    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_none_b", workspace_id="ws-other",
        source_card_id="src_none_b", quote=_WS_OTHER_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    index_omitted = vsvc.build_global_source_index(tmp_foundry)
    index_explicit_none = vsvc.build_global_source_index(tmp_foundry, identity=None)
    assert index_omitted == index_explicit_none
    assert "src_none_a" in index_omitted
    assert "src_none_b" in index_omitted


# ---------------------------------------------------------------------------
# F7(a) per-run (DI-1 delta re-audit MISSED-NEIGHBOR fix): the PER-RUN check
# (check_report_body_sensitivity, called for a draft's DECLARED
# source_run_id / source_links / claim_links run sources) had the same
# cross-run quote-match oracle as the global scan above, but on a different
# path: a draft that simply *declares* a foreign workspace's run_id as its
# source_run_id still had that run's sources/ read here, unscoped, letting a
# caller's guessed body text match a foreign run's private quote and surface
# that run/card in `locations` -- even though the GLOBAL check (above) was
# already scoped. The fix gates each declared run_id through the same
# export_service._run_read_allowed DF-004 gate, mirroring
# build_global_source_index exactly.
# ---------------------------------------------------------------------------


def test_report_body_sensitivity_excludes_cross_workspace_declared_run_under_enforcement(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The oracle itself: a draft that DECLARES a foreign workspace's run_id
    as its source_run_id, whose body happens to embed that foreign run's
    PRIVATE quote verbatim, must NOT fail the per-run sensitivity check with
    the foreign source_card_id/run_id in `locations` -- that would confirm
    to a ws-mine caller that the guessed quote exists in ws-other's private
    corpus, exactly the oracle the global scan was already fixed against."""

    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_perrun_other", workspace_id="ws-other",
        source_card_id="src_other_perrun", quote=_WS_OTHER_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    identity = AuthIdentity("u1", "ws-mine", ("owner", "admin", "researcher"))
    blocks = [{"block_id": "blk_1", "markdown": f"Guessed narrative: {_WS_OTHER_QUOTE}"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry,
        blocks,
        source_links=[],
        source_run_id="rf_run_f7a_perrun_other",
        sensitivity_threshold="public",
        identity=identity,
    )
    assert result.status == "pass"
    assert "src_other_perrun" not in result.detail
    assert "src_other_perrun" not in result.locations


def test_report_body_sensitivity_still_catches_same_workspace_declared_run_leak(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: the fix must not simply disable the per-run scan --
    a genuinely-own-workspace declared-run leak is still caught when
    ``identity`` is supplied and matches the run's workspace_id."""

    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_perrun_mine", workspace_id="ws-mine",
        source_card_id="src_mine_perrun", quote=_WS_MINE_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    identity = AuthIdentity("u1", "ws-mine", ("owner", "admin", "researcher"))
    blocks = [{"block_id": "blk_1", "markdown": f"Copy-pasted: {_WS_MINE_QUOTE}"}]

    result = vsvc.check_report_body_sensitivity(
        tmp_foundry,
        blocks,
        source_links=[],
        source_run_id="rf_run_f7a_perrun_mine",
        sensitivity_threshold="public",
        identity=identity,
    )
    assert result.status == "fail"
    assert "src_mine_perrun" in result.detail


def test_report_body_sensitivity_identity_none_preserves_existing_behavior(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``identity=None`` (the default; CLI callers) is byte-identical to the
    pre-fix see-all behavior -- a declared run's leak is still caught
    regardless of its workspace_id, and omitting the parameter entirely
    matches passing it explicitly as ``None``."""

    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_perrun_none", workspace_id="ws-other",
        source_card_id="src_none_perrun", quote=_WS_OTHER_QUOTE,
    )
    _force_isolation_active(monkeypatch)
    blocks = [{"block_id": "blk_1", "markdown": f"Raw paste: {_WS_OTHER_QUOTE}"}]

    result_omitted = vsvc.check_report_body_sensitivity(
        tmp_foundry,
        blocks,
        source_links=[],
        source_run_id="rf_run_f7a_perrun_none",
        sensitivity_threshold="public",
    )
    result_explicit_none = vsvc.check_report_body_sensitivity(
        tmp_foundry,
        blocks,
        source_links=[],
        source_run_id="rf_run_f7a_perrun_none",
        sensitivity_threshold="public",
        identity=None,
    )
    assert result_omitted.status == "fail"
    assert result_explicit_none.status == "fail"
    assert "src_none_perrun" in result_omitted.detail
    assert "src_none_perrun" in result_explicit_none.detail


def test_verify_draft_per_run_scan_does_not_leak_foreign_declared_run_quote(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aggregate level (mirrors the global-scan aggregate test above): a
    ws-mine draft that declares a foreign ws-other run_id as its
    ``source_run_id`` and whose body embeds that run's private quote
    verbatim must not surface it via the PER-RUN check
    (``report_body_sensitivity``, distinct from ``_global``) -- both checks
    must agree it is unreadable, not merely the global one."""

    _plant_run_with_workspace_quote(
        tmp_foundry, run_id="rf_run_f7a_perrun_agg_other", workspace_id="ws-other",
        source_card_id="src_other_perrun_agg", quote=_WS_OTHER_QUOTE,
    )
    _force_isolation_active(monkeypatch)

    identity = AuthIdentity("u1", "ws-mine", ("owner", "admin", "researcher"))
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Cross-workspace declared-run probe",
        workspace_id="ws-mine",
        sensitivity="public",
        source_run_id="rf_run_f7a_perrun_agg_other",
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Guessed narrative: {_WS_OTHER_QUOTE}",
        materiality="narrative",
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id, identity=identity)
    per_run_check = next(c for c in result.checks if c.id == "report_body_sensitivity")
    assert per_run_check.status == "pass"
    assert "src_other_perrun_agg" not in per_run_check.detail
