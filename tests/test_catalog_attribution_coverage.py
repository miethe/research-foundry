"""SMP-4.5: the tri-state attribution-coverage query surface.

The plan's no-backfill decision means a pre-existing (or newly ingested but
never-attributed) source card reads "no data" indistinguishably from
"verified zero" unless the query surface keeps three states apart:

  - ``present``          — assessed, and >=1 authoritative record was found.
  - ``absent``            — assessed, and the attribute genuinely isn't there.
  - ``not_yet_assessed``  — never evaluated at all.

Collapsing ``absent`` and ``not_yet_assessed`` (including into a shared
``null``) defeats the entire milestone (plan AC: "asserts as DISTINCT
values"). This module proves the distinction end-to-end — real source cards,
real ``import_run()`` — plus that the API surfaces the derived "N of M
sources assessed" line (:func:`catalog_service.attribution_coverage`, folded
into :func:`catalog_service.stats` and reachable at ``GET /api/catalog/stats``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import catalog_service as svc
from research_foundry.yamlio import dump_yaml

# Every row `import_run()` produces lands in workspace_id="default" (WKSP-303,
# `catalog_service._base_row`'s own hard-coded default) — the same convention
# `tests/unit/test_catalog_service.py`'s isolation matrix uses, so "same
# workspace" vs. "different workspace" here means identity.workspace_id
# "default" vs. anything else, not two independently-seeded workspaces.
_WS_DEFAULT = AuthIdentity("u1", "default", ("owner",))
_WS_OTHER = AuthIdentity("u2", "other-workspace", ("owner",))


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ``workspace_isolation_enforcement`` resolving active.

    Same convention as ``tests/unit/test_catalog_service.py`` /
    ``tests/test_workspace_isolation_enforcement.py``: monkeypatch
    :meth:`FoundryConfig.resolve_workspace_isolation_enforced` itself.
    """

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )

# ---------------------------------------------------------------------------
# Fixture: one run, three source cards — one assessed-present, one
# assessed-absent, one never-assessed — each cited by its own claim so
# `_build_source_rows` produces three distinct `source` catalog rows.
# ---------------------------------------------------------------------------

_PRESENT_MIRROR = {
    "attribution_ids": ["attrib_a", "attrib_b"],
    "count": 2,
    "rollups": [
        {
            "asserter_id": "semantic_scholar",
            "assertion_kind": "citation_count",
            "attribution_ids": ["attrib_a", "attrib_b"],
            "count": 2,
            "best_attribution_id": "attrib_b",
            "weakest_attribution_id": "attrib_a",
            "comparable": True,
        }
    ],
}

_ABSENT_MIRROR = {"attribution_ids": [], "count": 0, "rollups": []}


def _plant_coverage_run(paths: FoundryPaths, run_id: str) -> None:
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
            "created_at": "2026-08-02T09:00:00-04:00",
        },
        rp.run_yaml,
    )

    def _card(source_card_id: str, title: str, attribution_summary: dict | None) -> dict:
        card: dict = {
            "type": "source_card",
            "source_card_id": source_card_id,
            "sensitivity": "public",
            "trust": {"source_rank": "primary"},
            "usage": "direct",
            "source": {"title": title, "source_type": "paper"},
            "extracted_points": [
                {
                    "evidence_id": f"ev_{source_card_id}",
                    "locator": "p1",
                    "quote": "q",
                    "summary": "s",
                }
            ],
        }
        if attribution_summary is not None:
            card["attribution_summary"] = attribution_summary
        return card

    dump_md(
        _card("src_present", "Present Source", _PRESENT_MIRROR),
        "# present",
        rp.sources / "src_present.md",
    )
    dump_md(
        _card("src_absent", "Absent Source", _ABSENT_MIRROR),
        "# absent",
        rp.sources / "src_absent.md",
    )
    # No `attribution_summary` key at all — never evaluated.
    dump_md(
        _card("src_unassessed", "Unassessed Source", None),
        "# unassessed",
        rp.sources / "src_unassessed.md",
    )

    def _claim(claim_id: str, source_card_id: str) -> dict:
        return {
            "claim_id": claim_id,
            "text": f"A claim citing {source_card_id}.",
            "materiality": "core",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": source_card_id,
                    "evidence_id": f"ev_{source_card_id}",
                    "relation": "supports",
                    "locator": "p1",
                }
            ],
            "inference_basis": {"from_claims": [], "reasoning_summary": None},
            "report_locations": [],
        }

    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                _claim("clm_present", "src_present"),
                _claim("clm_absent", "src_absent"),
                _claim("clm_unassessed", "src_unassessed"),
            ],
        },
        rp.claim_ledger,
    )


def _make_client(paths: FoundryPaths) -> TestClient:
    cfg = FoundryConfig(paths=paths)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: paths
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Service-level: the three states are distinct, and the N-of-M line is right.
# ---------------------------------------------------------------------------


def test_attribution_coverage_reports_three_distinct_states(tmp_foundry: FoundryPaths) -> None:
    _plant_coverage_run(tmp_foundry, "rf_run_cov001")
    svc.import_run(tmp_foundry, "rf_run_cov001")

    coverage = svc.attribution_coverage(tmp_foundry)

    # Exactly one source lands in each state — proves the three-way split,
    # not a two-state collapse (e.g. absent-and-not-yet-assessed sharing one
    # bucket would fail these individual counts even though total is right).
    assert coverage["present"] == 1
    assert coverage["absent"] == 1
    assert coverage["not_yet_assessed"] == 1
    assert coverage["total"] == 3

    # The defining distinction: `absent` and `not_yet_assessed` are separate
    # keys in the response, each independently equal to 1 here — proof the
    # two states were tallied into different buckets rather than one shared
    # bucket (a two-state collapse would make one of these keys 0 or 2, or
    # the key would not exist at all).
    assert set(coverage) >= {"present", "absent", "not_yet_assessed"}
    assert coverage["absent"] == 1
    assert coverage["not_yet_assessed"] == 1

    # N of M: only present+absent count as "assessed" — not_yet_assessed is
    # excluded from the numerator (the no-backfill honesty control).
    assert coverage["assessed"] == 2
    assert coverage["coverage_line"] == "2 of 3 sources assessed"


def test_attribution_coverage_empty_catalog_is_zero_of_zero(tmp_foundry: FoundryPaths) -> None:
    coverage = svc.attribution_coverage(tmp_foundry)
    assert coverage == {
        "present": 0,
        "absent": 0,
        "not_yet_assessed": 0,
        "assessed": 0,
        "total": 0,
        "coverage_line": "0 of 0 sources assessed",
    }


def test_attribution_coverage_is_recomputable(tmp_foundry: FoundryPaths) -> None:
    """No wall-clock read, no model/network call — two calls over the same
    already-imported catalog must agree exactly."""

    _plant_coverage_run(tmp_foundry, "rf_run_cov002")
    svc.import_run(tmp_foundry, "rf_run_cov002")

    first = svc.attribution_coverage(tmp_foundry)
    second = svc.attribution_coverage(tmp_foundry)
    assert first == second


def test_stats_service_surfaces_attribution_coverage(tmp_foundry: FoundryPaths) -> None:
    """`stats()` — not just the standalone function — carries the same
    tri-state block, since that is the function already wired to the API."""

    _plant_coverage_run(tmp_foundry, "rf_run_cov003")
    svc.import_run(tmp_foundry, "rf_run_cov003")

    result = svc.stats(tmp_foundry)
    assert "attribution_coverage" in result
    assert result["attribution_coverage"] == svc.attribution_coverage(tmp_foundry)
    assert result["attribution_coverage"]["coverage_line"] == "2 of 3 sources assessed"


# ---------------------------------------------------------------------------
# Isolation fix (Fix 2, source-metadata-propagation): stats()'s
# attribution_coverage block must apply the SAME workspace scope the
# standalone attribution_coverage() already applies — a caller in one
# workspace must never see another workspace's coverage counts folded into
# GET /api/catalog/stats.
# ---------------------------------------------------------------------------


def test_stats_attribution_coverage_does_not_leak_cross_workspace(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _plant_coverage_run(tmp_foundry, "rf_run_cov_iso")
    svc.import_run(tmp_foundry, "rf_run_cov_iso")  # lands in workspace_id="default"

    unscoped = svc.stats(tmp_foundry)["attribution_coverage"]
    assert unscoped["total"] == 3  # sanity: the fixture actually produced rows

    _force_isolation_active(monkeypatch)

    # Same-workspace identity sees the identical counts unscoped produced.
    same_ws = svc.stats(tmp_foundry, identity=_WS_DEFAULT)["attribution_coverage"]
    assert same_ws == unscoped

    # A different workspace must see none of it — zero, not a partial or
    # stale view — proving the two workspaces' counts do not bleed together.
    other_ws = svc.stats(tmp_foundry, identity=_WS_OTHER)["attribution_coverage"]
    assert other_ws == {
        "present": 0,
        "absent": 0,
        "not_yet_assessed": 0,
        "assessed": 0,
        "total": 0,
        "coverage_line": "0 of 0 sources assessed",
    }

    # Parity: the standalone attribution_coverage() applies the identical
    # scoping rule stats() now mirrors — they must never diverge.
    assert other_ws == svc.attribution_coverage(tmp_foundry, identity=_WS_OTHER)
    assert same_ws == svc.attribution_coverage(tmp_foundry, identity=_WS_DEFAULT)


def test_stats_attribution_coverage_identity_present_but_inactive_stays_unscoped(
    tmp_foundry: FoundryPaths,
) -> None:
    """Identity supplied but isolation advisory/inactive (today's real
    default): a different-workspace identity must not filter anything."""

    _plant_coverage_run(tmp_foundry, "rf_run_cov_iso2")
    svc.import_run(tmp_foundry, "rf_run_cov_iso2")
    baseline = svc.stats(tmp_foundry)["attribution_coverage"]

    # No monkeypatch: tmp_foundry's auth.provider is unset -> resolves
    # advisory (inactive). A different-workspace identity must still see the
    # unscoped baseline, exactly matching stats()'s own pre-existing
    # identity=None behaviour for its other (still-unscoped) counts.
    scoped_but_inactive = svc.stats(tmp_foundry, identity=_WS_OTHER)["attribution_coverage"]
    assert scoped_but_inactive == baseline


# ---------------------------------------------------------------------------
# API-level: GET /api/catalog/stats returns the N-of-M line.
# ---------------------------------------------------------------------------


def test_api_catalog_stats_returns_n_of_m_coverage_line(tmp_foundry: FoundryPaths) -> None:
    client = _make_client(tmp_foundry)
    _plant_coverage_run(tmp_foundry, "rf_run_cov004")
    svc.import_run(tmp_foundry, "rf_run_cov004")

    resp = client.get("/api/catalog/stats")
    assert resp.status_code == 200
    data = resp.json()

    coverage = data["attribution_coverage"]
    assert coverage["present"] == 1
    assert coverage["absent"] == 1
    assert coverage["not_yet_assessed"] == 1
    assert coverage["coverage_line"] == "2 of 3 sources assessed"


def test_api_catalog_stats_empty_catalog_reports_zero_of_zero(tmp_foundry: FoundryPaths) -> None:
    client = _make_client(tmp_foundry)
    resp = client.get("/api/catalog/stats")
    assert resp.status_code == 200
    assert resp.json()["attribution_coverage"]["coverage_line"] == "0 of 0 sources assessed"
