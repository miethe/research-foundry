"""Offline tests for the Wave-3 §17 per-provider scorecard rollup.

``telemetry.provider_scorecard`` aggregates ``metrics.providers`` breakdowns
(populated by ``search_router.router.run_search``, see ``test_search_router_router.py::
test_run_search_emits_search_metrics_to_ccdash_event`` for the producer side)
across every ``ccdash/events/*.yaml`` on disk. These tests write synthetic
event files directly — no live router run, no network — so the aggregation
math itself is pinned independently of the router's per-run computation.
"""

from __future__ import annotations

from typing import Any

from research_foundry.paths import FoundryPaths
from research_foundry.services import telemetry
from research_foundry.yamlio import dump_yaml, load_yaml


def _write_event(paths: FoundryPaths, event_id: str, providers: dict[str, Any]) -> None:
    event = {
        "event_id": event_id,
        "run_id": f"run_{event_id}",
        "metrics": {"providers": providers},
    }
    dump_yaml(event, paths.ccdash / "events" / f"{event_id}.yaml")


def test_provider_scorecard_aggregates_across_events(tmp_foundry: FoundryPaths) -> None:
    _write_event(
        tmp_foundry,
        "evt_1",
        {
            "brave": {
                "provider": "brave",
                "roles": ["discovery"],
                "queries_executed": 1,
                "estimated_cost_usd": 0.005,
                "raw_hits": 10,
                "duplicate_rate": 0.2,
            },
            "jina": {
                "provider": "jina",
                "roles": ["extraction"],
                "extraction_attempts": 5,
                "extraction_failure_rate": 0.4,
            },
        },
    )
    _write_event(
        tmp_foundry,
        "evt_2",
        {
            "brave": {
                "provider": "brave",
                "roles": ["discovery"],
                "queries_executed": 2,
                "estimated_cost_usd": 0.010,
                "raw_hits": 8,
                "duplicate_rate": 0.0,
            },
        },
    )

    path = telemetry.provider_scorecard(paths=tmp_foundry)
    assert path == tmp_foundry.ccdash / "summaries" / "provider_scorecard.yaml"

    body = load_yaml(path)
    providers = body["providers"]

    assert providers["brave"]["runs"] == 2
    assert providers["brave"]["queries_executed"] == 3
    assert providers["brave"]["estimated_cost_usd"] == 0.015
    # mean of [0.2, 0.0]
    assert providers["brave"]["duplicate_rate_mean"] == 0.1
    # brave never attempted extraction in either event.
    assert providers["brave"]["extraction_attempts"] == 0
    assert providers["brave"]["extraction_failure_rate_mean"] is None

    assert providers["jina"]["runs"] == 1
    assert providers["jina"]["extraction_attempts"] == 5
    assert providers["jina"]["extraction_failure_rate_mean"] == 0.4
    # jina never discovered in evt_1; no duplicate_rate to average.
    assert providers["jina"]["duplicate_rate_mean"] is None
    assert providers["jina"]["queries_executed"] == 0


def test_provider_scorecard_skips_events_without_provider_breakdown(
    tmp_foundry: FoundryPaths,
) -> None:
    """Non-search (generic) CCDash events have no ``metrics.providers`` key.

    The rollup must silently skip them rather than raising — this is the
    additive-schema guarantee: existing, non-search runs are unaffected.
    """

    dump_yaml(
        {"event_id": "evt_generic", "run_id": "run_generic", "metrics": {"claims_total": 4}},
        tmp_foundry.ccdash / "events" / "evt_generic.yaml",
    )

    path = telemetry.provider_scorecard(paths=tmp_foundry)
    body = load_yaml(path)
    assert body["providers"] == {}


def test_provider_scorecard_empty_events_dir_is_noop(tmp_foundry: FoundryPaths) -> None:
    """No events at all still produces a valid, empty scorecard (never raises)."""

    path = telemetry.provider_scorecard(paths=tmp_foundry)
    body = load_yaml(path)
    assert body["providers"] == {}
    assert "generated_at" in body


def test_provider_scorecard_ignores_malformed_provider_entries(
    tmp_foundry: FoundryPaths,
) -> None:
    """A non-dict ``providers`` value or a non-dict per-provider stat is skipped."""

    dump_yaml(
        {"event_id": "evt_bad_shape", "run_id": "run_bad", "metrics": {"providers": "not-a-dict"}},
        tmp_foundry.ccdash / "events" / "evt_bad_shape.yaml",
    )
    dump_yaml(
        {
            "event_id": "evt_bad_entry",
            "run_id": "run_bad_entry",
            "metrics": {"providers": {"brave": "not-a-dict-either"}},
        },
        tmp_foundry.ccdash / "events" / "evt_bad_entry.yaml",
    )

    path = telemetry.provider_scorecard(paths=tmp_foundry)
    body = load_yaml(path)
    assert body["providers"] == {}
