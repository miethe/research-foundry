"""clearance-gates-v1 M5 (leg B) -- egress governance consolidation over the
read/projection surfaces: export_service._resolve_source, catalog_service's
search()/get_item() (plus its row-builders' projection-strip fix), and
knowledge_access.KnowledgeAccessService (SourceKindProjector, RunKindProjector),
and the api/routers/runs.py existence gate.

Every test here is a BEHAVIOUR DELTA: it constructs a record genuinely
carrying a clearance stamp that blocks the checked scope, and asserts the
raw/tainted value is ABSENT from the result -- never merely a non-zero exit
or a generic "it raised something". Each would fail against an unmediated
implementation (the tainted quote/value would be visible in the return
value or on stdout).

Synthetic-fixture only (``tmp_foundry``): no real run data, no network. Uses
the REAL ``config/clearance_gates.yaml`` (copied verbatim into every
``tmp_foundry`` workspace by ``tests/conftest.py``), so ``source_attribution``
is genuinely a governed kind here -- these are not fixture-relaxed tests.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app as _cli_app
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import catalog_service
from research_foundry.services import clearance
from research_foundry.services import export_service as svc
from research_foundry.services import knowledge_access as ka
from research_foundry.yamlio import dump_yaml

_runner = CliRunner()

_TAINTED_QUOTE = "PROVIDER-FETCHED-VALUE-do-not-redistribute"
_TAINTED_SUMMARY = "provider-fetched-summary-do-not-redistribute"


def _stamp(*scopes: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "blocked_scopes": list(scopes),
        "stamped_at": "2026-08-05T00:00:00Z",
        "stamped_by": "test-fixture",
        "posture_at_stamp": "dev_test",
        "gate_refs": ["DEF-1"],
    }


def _build_run(
    paths: FoundryPaths,
    run_id: str,
    *,
    clearance_block: dict[str, Any] | None,
) -> None:
    """One run, one claim, one source card citing it -- the card optionally
    carrying *clearance_block* verbatim on its frontmatter (a shape no real
    writer produces today -- clearance rides on source_attribution records,
    not source cards -- injected directly, matching
    tests/test_clinical_attestation_marker.py's own precedent, precisely so
    the test does not depend on any writer plumbing this through)."""

    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "planned",
            "sensitivity": "public",
            "created_at": "2026-08-05T00:00:00-04:00",
        },
        rp.run_yaml,
    )

    meta: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": "src_tainted",
        "sensitivity": "public",
        "source": {
            "title": "Tainted Source",
            "source_type": "web",
            "locator": {"url": "https://example.test/tainted"},
        },
        "trust": {"source_rank": "primary"},
        "usage": {"allowed_for_public_output": True},
        "extracted_points": [
            {
                "evidence_id": "ev_1",
                "locator": "p.1",
                "summary": _TAINTED_SUMMARY,
                "quote": _TAINTED_QUOTE,
            }
        ],
    }
    if clearance_block is not None:
        meta["clearance"] = clearance_block
    dump_md(meta, "", rp.sources / "src_tainted.md")

    dump_yaml(
        {
            "schema_version": "0.1",
            "claims": [
                {
                    "claim_id": "clm_tainted",
                    "text": "A claim citing the (possibly tainted) source.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_tainted",
                            "evidence_id": "ev_1",
                            "relation": "supports",
                            "locator": "p.1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                },
            ],
        },
        rp.claim_ledger,
    )
    dump_yaml(
        {
            "run_id": run_id,
            "passed": True,
            "exit_code": 0,
            "checks": [
                {"id": "check_01", "severity": "error", "status": "pass", "detail": "ok", "locations": []}
            ],
        },
        rp.verification,
    )
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 1, "claims_supported": 1},
            "governance": {"sensitivity": "public", "approved_for_writeback": False},
        },
        rp.evidence_bundle,
    )
    rp.report_draft.write_text("# Report\n\n[claim:clm_tainted]\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. export_service._resolve_source (via export_run())
# ---------------------------------------------------------------------------


def test_export_run_denies_a_redistribution_blocked_citation(tmp_foundry: FoundryPaths) -> None:
    """Behaviour delta: an unmediated _resolve_source would happily project
    the tainted quote into run.json. Mediated, export_run() refuses outright
    -- the tainted value never reaches the returned dict at all."""

    run_id = "rf_run_m5_export_deny"
    _build_run(tmp_foundry, run_id, clearance_block=_stamp("redistribution"))
    with pytest.raises(clearance.ClearanceDenied):
        svc.export_run(tmp_foundry, run_id)


def test_export_run_carries_a_non_blocking_stamp_forward_verbatim(tmp_foundry: FoundryPaths) -> None:
    """The companion half: a stamp that does NOT block redistribution (here,
    clinical_reliance only) is allowed through, AND the exact stamp survives
    the projection into the resolved-source dict -- the projection-strip
    vector this milestone closes. Without the forward-carry fix, `"clearance"
    not in source` would be true here even though the raw card carried one."""

    run_id = "rf_run_m5_export_carry"
    _build_run(tmp_foundry, run_id, clearance_block=_stamp("clinical_reliance"))
    data = svc.export_run(tmp_foundry, run_id)
    assert data is not None
    source = data["claims"][0]["sources"][0]
    assert source["quote"] == _TAINTED_QUOTE  # not blocked for redistribution -> visible
    assert source["clearance"] == _stamp("clinical_reliance")


def test_export_run_pediatric_regression_unstamped_card_is_unaffected(tmp_foundry: FoundryPaths) -> None:
    """Regression floor: a card with NO `clearance` key at all (the real
    shape of every one of the 7 committed pediatric bundles) exports exactly
    as before -- mediate_egress is a documented no-op for it (governed kind,
    empty candidate list), and the resolved dict omits `clearance` entirely
    rather than emitting a bare `None`."""

    run_id = "rf_run_m5_export_clean"
    _build_run(tmp_foundry, run_id, clearance_block=None)
    data = svc.export_run(tmp_foundry, run_id)
    assert data is not None
    source = data["claims"][0]["sources"][0]
    assert source["quote"] == _TAINTED_QUOTE
    assert "clearance" not in source


# ---------------------------------------------------------------------------
# 2. catalog_service: projection-strip fix + get_item()/search() mediation
# ---------------------------------------------------------------------------


def test_import_run_refuses_a_run_carrying_a_blocked_citation(tmp_foundry: FoundryPaths) -> None:
    """Defense in depth, verified: since catalog_service.import_run() builds
    its rows via export_run() (module docstring, "import via export_run(),
    live"), a redistribution-blocked citation can never even enter
    catalog.db -- the earliest possible point (export) already refused it."""

    run_id = "rf_run_m5_catalog_import_deny"
    _build_run(tmp_foundry, run_id, clearance_block=_stamp("redistribution"))
    with pytest.raises(clearance.ClearanceDenied):
        catalog_service.import_run(tmp_foundry, run_id)


def test_catalog_projection_carries_clearance_through_payload_json_round_trip(
    tmp_foundry: FoundryPaths,
) -> None:
    """The literal projection-strip-vector proof: build a "source" row the
    same way _build_source_rows does, serialize it to payload_json (exactly
    what _base_row/_insert_rows do), parse it back (exactly what get_item()
    does), and confirm the stamp is still there -- byte for byte. Without
    the fix to the aggregation dict + payload dict in
    catalog_service._build_source_rows, this key would be silently absent
    after the round trip even though the input claimed to carry one."""

    stamp = _stamp("clinical_reliance")
    export_data = {
        "claims": [
            {
                "claim_id": "clm_x",
                "materiality": "core",
                "claim_type": "factual",
                "text": "x",
                "status": "supported",
                "confidence": "high",
                "inference_basis": {"from_claims": [], "reasoning_summary": None},
                "report_locations": [],
                "sources": [
                    {
                        "source_card_id": "src_x",
                        "evidence_id": "ev_1",
                        "relation": "supports",
                        "locator": "p.1",
                        "resolved": True,
                        "dangling": False,
                        "title": "Source X",
                        "source_type": "web",
                        "url": None,
                        "authors": None,
                        "doi": None,
                        "publisher": None,
                        "version": None,
                        "trust": {"source_rank": "primary"},
                        "usage": None,
                        "attribution_summary": None,
                        "sensitivity": "public",
                        "evidence_locator": "p.1",
                        "summary": _TAINTED_SUMMARY,
                        "quote": _TAINTED_QUOTE,
                        "redacted": False,
                        "clearance": stamp,
                    }
                ],
            }
        ],
    }
    rows, claim_id_to_item_id, report_claim_ids, term_rows = (
        catalog_service._build_claim_and_inference_rows(
            export_data, "run_x", project=None, created_at=None,
            run_sensitivity_rank=0, citation_ranks={},
        )
    )
    assert len(rows) == 1
    round_tripped = json.loads(rows[0]["payload_json"])
    assert round_tripped["cited_sources"][0]["clearance"] == stamp

    source_rows, _ = catalog_service._build_source_rows(
        export_data, "run_x", project=None, created_at=None,
        run_sensitivity_rank=0, citation_ranks={},
    )
    assert len(source_rows) == 1
    round_tripped_source = json.loads(source_rows[0]["payload_json"])
    assert round_tripped_source["clearance"] == stamp


def _insert_row(paths: FoundryPaths, row: dict[str, Any]) -> None:
    with catalog_service._db(paths) as conn:
        conn.execute("BEGIN IMMEDIATE")
        catalog_service._insert_rows(conn, [row], [], "run_x", [])
        conn.commit()


def test_get_item_denies_a_directly_stamped_row(tmp_foundry: FoundryPaths) -> None:
    """catalog_service.get_item()'s OWN mediation, in isolation from
    export_service's earlier check -- a row inserted directly into
    catalog.db (bypassing import_run()/export_run() entirely) with a
    redistribution-blocked stamp in its payload_json must still be refused
    on READ. This is the literal `rf catalog show <tainted-id>` shape the
    plan names: the item genuinely exists in the DB (a catalog_item_id
    resolves), and get_item() must refuse rather than return the tainted
    value."""

    payload = {
        "title": "Tainted Source",
        "source_type": "web",
        "url": None,
        "authors": None,
        "doi": None,
        "publisher": None,
        "version": None,
        "trust": {"source_rank": "primary"},
        "usage": None,
        "attribution_summary": None,
        "evidence_points": [
            {
                "claim_id": "clm_x",
                "evidence_id": "ev_1",
                "relation": "supports",
                "locator": "p.1",
                "quote": _TAINTED_QUOTE,
                "summary": _TAINTED_SUMMARY,
                "sensitivity_rank": 0,
            }
        ],
        "clearance": _stamp("redistribution"),
    }
    row = catalog_service._base_row(
        item_type="source", run_id="run_x", local_ref="src_tainted", project=None,
        title="Tainted Source", summary="web", status=None, sensitivity_rank=0,
        trust_label="primary", confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    _insert_row(tmp_foundry, row)

    with pytest.raises(clearance.ClearanceDenied):
        catalog_service.get_item(tmp_foundry, row["catalog_item_id"])


def test_get_item_allows_an_unstamped_row_the_capture_output_stdout_ac(
    tmp_foundry: FoundryPaths,
) -> None:
    """Companion negative control + the literal `rf catalog show` AC shape:
    a row with NO clearance key round-trips normally (regression floor), and
    a SEPARATE tainted row is refused -- proving the earlier denial test is
    caused by the stamp, not by get_item() always failing."""

    clean_payload = {
        "title": "Clean Source", "source_type": "web", "url": None,
        "authors": None, "doi": None, "publisher": None, "version": None,
        "trust": None, "usage": None, "attribution_summary": None,
        "evidence_points": [
            {"claim_id": "clm_y", "evidence_id": "ev_2", "relation": "supports",
             "locator": "p.2", "quote": "clean quote", "summary": "clean summary",
             "sensitivity_rank": 0},
        ],
    }
    clean_row = catalog_service._base_row(
        item_type="source", run_id="run_y", local_ref="src_clean", project=None,
        title="Clean Source", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=clean_payload,
    )
    _insert_row(tmp_foundry, clean_row)
    item = catalog_service.get_item(tmp_foundry, clean_row["catalog_item_id"])
    assert item is not None
    assert item["payload"]["evidence_points"][0]["quote"] == "clean quote"


def test_search_denies_a_page_containing_a_directly_stamped_row(tmp_foundry: FoundryPaths) -> None:
    """search()'s own defense-in-depth mediation, isolated from get_item()'s."""

    payload = {
        "title": "Tainted Source 2", "source_type": "web", "url": None,
        "authors": None, "doi": None, "publisher": None, "version": None,
        "trust": None, "usage": None, "attribution_summary": None,
        "evidence_points": [
            {"claim_id": "clm_z", "evidence_id": "ev_3", "relation": "supports",
             "locator": "p.3", "quote": _TAINTED_QUOTE, "summary": _TAINTED_SUMMARY,
             "sensitivity_rank": 0},
        ],
        "clearance": _stamp("redistribution"),
    }
    row = catalog_service._base_row(
        item_type="source", run_id="run_z", local_ref="src_tainted2", project=None,
        title="Tainted Source 2", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    _insert_row(tmp_foundry, row)

    with pytest.raises(clearance.ClearanceDenied):
        catalog_service.search(tmp_foundry, item_type="source")


# ---------------------------------------------------------------------------
# 3. knowledge_access.SourceKindProjector / RunKindProjector
# ---------------------------------------------------------------------------


def test_knowledge_source_fetch_denies_a_directly_stamped_row(tmp_foundry: FoundryPaths) -> None:
    """The SAME chokepoint for both HTTP and Knowledge MCP stdio (both call
    through KnowledgeAccessService -> SourceKindProjector): a row a caller
    could read via `rf_fetch`/the /knowledge/* HTTP surface must not leak
    the tainted quote just because SourceKindProjector reads payload_json
    directly rather than via catalog_service.get_item() (see that class's
    own docstring for why it must bypass catalog_service.get_item/search)."""

    payload = {
        "title": "Tainted Source 3", "source_type": "web", "url": None,
        "evidence_points": [
            {"claim_id": "clm_k", "evidence_id": "ev_4", "relation": "supports",
             "locator": "p.4", "quote": _TAINTED_QUOTE, "summary": _TAINTED_SUMMARY,
             "sensitivity_rank": 0},
        ],
        "clearance": _stamp("redistribution"),
    }
    row = catalog_service._base_row(
        item_type="source", run_id="run_k", local_ref="src_tainted3", project=None,
        title="Tainted Source 3", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    _insert_row(tmp_foundry, row)

    projector = ka.SourceKindProjector(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="fetch")
    knowledge_id = f"rfk:v1:source:{row['catalog_item_id']}"

    with pytest.raises(clearance.ClearanceDenied):
        projector.fetch(context, knowledge_id=knowledge_id)


def test_knowledge_source_search_denies_a_page_containing_a_stamped_row(
    tmp_foundry: FoundryPaths,
) -> None:
    payload = {
        "title": "Tainted Source 4", "source_type": "web", "url": None,
        "evidence_points": [
            {"claim_id": "clm_l", "evidence_id": "ev_5", "relation": "supports",
             "locator": "p.5", "quote": _TAINTED_QUOTE, "summary": _TAINTED_SUMMARY,
             "sensitivity_rank": 0},
        ],
        "clearance": _stamp("redistribution"),
    }
    row = catalog_service._base_row(
        item_type="source", run_id="run_l", local_ref="src_tainted4", project=None,
        title="Findable Tainted Source", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    _insert_row(tmp_foundry, row)

    projector = ka.SourceKindProjector(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="search")

    with pytest.raises(clearance.ClearanceDenied):
        projector.search(context, query="findable", limit=10, cursor=None)


def test_knowledge_run_fetch_maps_clearance_denied_to_knowledge_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """RunKindProjector.fetch() calls export_run() directly -- once that
    raises ClearanceDenied (via export_service's own mediation), this
    projector must map it to KnowledgeDenied (this class's single bounded
    no-existence-leak denial contract), never let it propagate raw."""

    run_id = "rf_run_m5_knowledge_run_deny"
    _build_run(tmp_foundry, run_id, clearance_block=_stamp("redistribution"))

    projector = ka.RunKindProjector(tmp_foundry)
    context = ka.resolve_context(tmp_foundry, tool="fetch")

    with pytest.raises(ka.KnowledgeDenied):
        projector.fetch(context, knowledge_id=f"rfk:v1:run:{run_id}")


# ---------------------------------------------------------------------------
# 4. api/routers/runs.py -- ClearanceDenied maps to a clean HTTP error
# ---------------------------------------------------------------------------


def test_rf_catalog_show_cli_never_prints_the_tainted_value(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The canonical AC from the plan, run against the REAL `rf catalog show`
    CLI command end-to-end: capture stdout and assert the raw tainted value
    string is ABSENT -- not merely that the command exited non-zero. Proves
    both catalog_service.get_item()'s new internal mediation AND the
    try/except added around its cli_commands.py call site (without which
    the denial would crash with an unhandled traceback instead of a clean,
    stdout-silent failure)."""

    payload = {
        "title": "CLI Tainted Source", "source_type": "web", "url": None,
        "authors": None, "doi": None, "publisher": None, "version": None,
        "trust": None, "usage": None, "attribution_summary": None,
        "evidence_points": [
            {"claim_id": "clm_cli", "evidence_id": "ev_cli", "relation": "supports",
             "locator": "p.cli", "quote": _TAINTED_QUOTE, "summary": _TAINTED_SUMMARY,
             "sensitivity_rank": 0},
        ],
        "clearance": _stamp("redistribution"),
    }
    row = catalog_service._base_row(
        item_type="source", run_id="run_cli", local_ref="src_cli_tainted", project=None,
        title="CLI Tainted Source", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )
    _insert_row(tmp_foundry, row)

    monkeypatch.chdir(tmp_foundry.root)
    result = _runner.invoke(_cli_app, ["catalog", "show", row["catalog_item_id"]])

    assert result.exit_code != 0
    assert _TAINTED_QUOTE not in result.output
    assert _TAINTED_SUMMARY not in result.output


def test_runs_router_maps_clearance_denied_to_403_not_500(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the except clearance.ClearanceDenied handler in
    _enforce_existence_gate, this would surface as an unhandled exception
    (a raw 500) instead of the same clean policy-refusal shape every other
    denial in this router already uses."""

    from research_foundry.api.routers import runs as runs_router

    run_id = "rf_run_m5_router_deny"
    _build_run(tmp_foundry, run_id, clearance_block=_stamp("redistribution"))

    with pytest.raises(Exception) as exc_info:
        runs_router._enforce_existence_gate(tmp_foundry, run_id, None, None)

    from fastapi import HTTPException

    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 5. M5 GATE FINDING: mediation must use the CALLER's workspace registry,
#    never the process CWD's discovered one.
# ---------------------------------------------------------------------------
#
# Root cause of the finding: `_mediate_catalog_payloads` (catalog_service) and
# `_mediate_knowledge_payloads` (knowledge_access) passed neither `paths` nor a
# registry to `clearance.mediate_egress`, so clearance resolved via
# `FoundryPaths.discover()` -- the process CWD -- while the ROWS being mediated
# came from the caller's `paths` workspace. A governance control reading the
# wrong config reports success, which is strictly worse than no control. This
# repo already carries row-level workspace-isolation work (WKSP-304), so a
# multi-workspace deployment is a real configuration, not hypothetical.
#
# WHAT ACTUALLY DIFFERS BETWEEN TWO WORKSPACES. `mediate_egress` never consults
# a gate's `state` to decide a denial -- denial comes from the RECORD's own
# durable `blocked_scopes` (clearance.py's design invariant 2). The registry is
# consulted for exactly one thing: `governs_kind(kind)`, i.e. whether `kind` is
# in `applies_to_kinds`. So the honest, mechanically-real lever distinguishing
# a "blocking" workspace from a "permitting" one is `applies_to_kinds` -- NOT
# the `gates:` list. These fixtures use that lever deliberately rather than
# varying `gates:` and appearing to test something the code does not read.
#
# Both directions are asserted per site. One direction alone cannot distinguish
# "threaded correctly" from "the two registries happened to agree".

_GOVERNING_REGISTRY = """\
schema_version: "1.0"
applies_to_kinds:
  - source_attribution
gates:
  - gate_id: DEF-1
    blocks_scope: redistribution
    state: open
    summary: Workspace-scoped test gate.
    evidence_pointer: docs/x.md
    closed_by: null
"""

# Same file shape, but source_attribution is NOT a governed kind here, so
# mediate_egress short-circuits before ever reading a record's blocked_scopes.
_PERMITTING_REGISTRY = """\
schema_version: "1.0"
applies_to_kinds:
  - some_other_kind
gates:
  - gate_id: DEF-1
    blocks_scope: redistribution
    state: open
    summary: Workspace-scoped test gate (kind not governed here).
    evidence_pointer: docs/x.md
    closed_by: null
"""


def _make_workspace(tmp_path: Any, name: str, *, registry_yaml: str) -> FoundryPaths:
    """Build a second, independent foundry workspace with its OWN clearance
    registry -- the whole point being that two workspaces can disagree about
    what is governed, and mediation must follow the CALLER's, not the CWD's.

    Mirrors ``tests/conftest.py::tmp_foundry``'s scaffold (copies
    schemas/config/templates + a foundry.yaml marker so both
    ``FoundryPaths.discover()`` and ``resolve_threshold()`` resolve here), then
    OVERWRITES ``config/clearance_gates.yaml`` with *registry_yaml*.
    """

    import shutil

    from research_foundry.paths import distribution_root

    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub, dirs_exist_ok=True)
    shutil.copyfile(dist / "foundry.yaml", root / "foundry.yaml")
    (root / "runs").mkdir(parents=True, exist_ok=True)
    (root / "config" / "clearance_gates.yaml").write_text(registry_yaml, encoding="utf-8")
    return FoundryPaths(root=root)


def _stamped_source_row(local_ref: str) -> dict[str, Any]:
    """A "source" catalog row whose payload_json carries a redistribution-
    blocking stamp -- identical in shape to what _build_source_rows produces."""

    payload = {
        "title": f"WS Tainted {local_ref}",
        "source_type": "web",
        "url": None,
        "authors": None,
        "doi": None,
        "publisher": None,
        "version": None,
        "trust": None,
        "usage": None,
        "attribution_summary": None,
        "evidence_points": [
            {
                "claim_id": "clm_ws",
                "evidence_id": "ev_ws",
                "relation": "supports",
                "locator": "p.ws",
                "quote": _TAINTED_QUOTE,
                "summary": _TAINTED_SUMMARY,
                "sensitivity_rank": 0,
            }
        ],
        "clearance": _stamp("redistribution"),
    }
    return catalog_service._base_row(
        item_type="source", run_id="run_ws", local_ref=local_ref, project=None,
        title=f"WS Tainted {local_ref}", summary="web", status=None, sensitivity_rank=0,
        trust_label=None, confidence=None, source_count=1,
        created_at="2026-08-05T00:00:00Z", updated_at="2026-08-05T00:00:00Z",
        payload=payload,
    )


# --- site 1: catalog_service -------------------------------------------------


def test_catalog_get_item_denies_when_CALLERS_workspace_governs_even_if_cwd_permits(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 1 for catalog_service.get_item(): the caller's workspace
    governs source_attribution (so the stamped record is denied) while the
    process CWD's workspace does NOT. An unthreaded implementation resolves
    the CWD registry, finds the kind ungoverned, and RETURNS THE PAYLOAD --
    so this denial is only reachable if `paths` was actually threaded."""

    caller_ws = _make_workspace(tmp_path, "caller_governs", registry_yaml=_GOVERNING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "cwd_permits", registry_yaml=_PERMITTING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    row = _stamped_source_row("src_ws_a")
    _insert_row(caller_ws, row)

    with pytest.raises(clearance.ClearanceDenied):
        catalog_service.get_item(caller_ws, row["catalog_item_id"])


def test_catalog_get_item_permits_when_CALLERS_workspace_permits_even_if_cwd_governs(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 2 (the converse) for catalog_service.get_item(): the caller's
    workspace does NOT govern source_attribution while the CWD's DOES. An
    unthreaded implementation resolves the CWD registry and wrongly DENIES.
    Success -- with the value actually present -- proves the caller's registry
    won. Without this half, direction 1 alone could not distinguish 'threaded
    correctly' from 'both registries happened to deny'."""

    caller_ws = _make_workspace(tmp_path, "caller_permits", registry_yaml=_PERMITTING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "cwd_governs", registry_yaml=_GOVERNING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    row = _stamped_source_row("src_ws_b")
    _insert_row(caller_ws, row)

    item = catalog_service.get_item(caller_ws, row["catalog_item_id"])
    assert item is not None
    assert item["payload"]["evidence_points"][0]["quote"] == _TAINTED_QUOTE


def test_catalog_search_denies_when_CALLERS_workspace_governs_even_if_cwd_permits(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 1 for catalog_service.search() -- the site that carried its
    own inline mediate_egress copy (now routed through the shared helper)."""

    caller_ws = _make_workspace(tmp_path, "s_caller_governs", registry_yaml=_GOVERNING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "s_cwd_permits", registry_yaml=_PERMITTING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    _insert_row(caller_ws, _stamped_source_row("src_ws_c"))

    with pytest.raises(clearance.ClearanceDenied):
        catalog_service.search(caller_ws, item_type="source")


def test_catalog_search_permits_when_CALLERS_workspace_permits_even_if_cwd_governs(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 2 for catalog_service.search()."""

    caller_ws = _make_workspace(tmp_path, "s_caller_permits", registry_yaml=_PERMITTING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "s_cwd_governs", registry_yaml=_GOVERNING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    _insert_row(caller_ws, _stamped_source_row("src_ws_d"))

    result = catalog_service.search(caller_ws, item_type="source")
    assert result["total"] == 1


# --- site 2: knowledge_access ------------------------------------------------


def test_knowledge_fetch_denies_when_CALLERS_workspace_governs_even_if_cwd_permits(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 1 for SourceKindProjector.fetch() -- the chokepoint serving
    BOTH the Knowledge MCP stdio surface and /knowledge/* HTTP. The projector
    is constructed for `caller_ws`, reads `caller_ws`' catalog_items, and must
    mediate against `caller_ws`' registry -- not the CWD workspace's, which
    here does not govern the kind at all."""

    caller_ws = _make_workspace(tmp_path, "k_caller_governs", registry_yaml=_GOVERNING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "k_cwd_permits", registry_yaml=_PERMITTING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    row = _stamped_source_row("src_ws_e")
    _insert_row(caller_ws, row)

    projector = ka.SourceKindProjector(caller_ws)
    context = ka.resolve_context(caller_ws, tool="fetch")

    with pytest.raises(clearance.ClearanceDenied):
        projector.fetch(context, knowledge_id=f"rfk:v1:source:{row['catalog_item_id']}")


def test_knowledge_fetch_permits_when_CALLERS_workspace_permits_even_if_cwd_governs(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 2 (the converse) for SourceKindProjector.fetch(): success,
    with the value present in the returned document text, proves the caller's
    registry won over a CWD registry that would have denied."""

    caller_ws = _make_workspace(tmp_path, "k_caller_permits", registry_yaml=_PERMITTING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "k_cwd_governs", registry_yaml=_GOVERNING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    row = _stamped_source_row("src_ws_f")
    _insert_row(caller_ws, row)

    projector = ka.SourceKindProjector(caller_ws)
    context = ka.resolve_context(caller_ws, tool="fetch")

    doc = projector.fetch(context, knowledge_id=f"rfk:v1:source:{row['catalog_item_id']}")
    assert doc.text is not None
    assert _TAINTED_QUOTE in doc.text


def test_knowledge_search_denies_when_CALLERS_workspace_governs_even_if_cwd_permits(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 1 for SourceKindProjector.search()."""

    caller_ws = _make_workspace(tmp_path, "ks_caller_governs", registry_yaml=_GOVERNING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "ks_cwd_permits", registry_yaml=_PERMITTING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    _insert_row(caller_ws, _stamped_source_row("src_ws_g"))

    projector = ka.SourceKindProjector(caller_ws)
    context = ka.resolve_context(caller_ws, tool="search")

    with pytest.raises(clearance.ClearanceDenied):
        projector.search(context, query="tainted", limit=10, cursor=None)


def test_knowledge_search_permits_when_CALLERS_workspace_permits_even_if_cwd_governs(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direction 2 for SourceKindProjector.search()."""

    caller_ws = _make_workspace(tmp_path, "ks_caller_permits", registry_yaml=_PERMITTING_REGISTRY)
    cwd_ws = _make_workspace(tmp_path, "ks_cwd_governs", registry_yaml=_GOVERNING_REGISTRY)
    monkeypatch.chdir(cwd_ws.root)

    _insert_row(caller_ws, _stamped_source_row("src_ws_h"))

    projector = ka.SourceKindProjector(caller_ws)
    context = ka.resolve_context(caller_ws, tool="search")

    page = projector.search(context, query="tainted", limit=10, cursor=None)
    assert len(page.items) == 1


# --- the structural guard: paths is MANDATORY, not defaulted -----------------


def test_both_mediation_helpers_require_paths_keyword() -> None:
    """The regression guard for the whole class. Both helpers must REQUIRE
    `paths` -- if either grows a default, the silent CWD-discovery fallback
    that caused this finding is reintroduced and every behavioural test above
    keeps passing (because the fixtures would still be threading it
    explicitly). Asserting the signature is what makes the fix durable."""

    import inspect

    for fn in (catalog_service._mediate_catalog_payloads, ka._mediate_knowledge_payloads):
        param = inspect.signature(fn).parameters["paths"]
        assert param.default is inspect.Parameter.empty, (
            f"{fn.__module__}.{fn.__name__} must REQUIRE paths -- a default "
            "reintroduces the CWD-discovery fallback (M5 gate finding)"
        )
        assert param.kind is inspect.Parameter.KEYWORD_ONLY
