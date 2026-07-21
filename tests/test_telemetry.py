"""Unit tests for the ``telemetry.emit_ccdash_event`` search-metrics passthrough.

Wave 2 §3 TASK-2.1: ``emit_ccdash_event`` gained an optional ``search_metrics``
kwarg (merged additively into the emitted event's ``metrics``) and now returns
the minted ``event_id`` (previously the on-disk path). These tests pin both
the new passthrough behavior and the unchanged generic (non-search) path.
"""

from __future__ import annotations

from unittest.mock import patch

from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services import telemetry
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.planning import plan_run
from research_foundry.yamlio import load_jsonl, load_yaml

_IDEA = (
    "Research how telemetry search metrics should reach the CCDash event "
    "record without affecting non-search runs. Studies show additive schema "
    "fields keep existing consumers unaffected."
)


def _planned_run(paths: FoundryPaths) -> str:
    """Drive capture → triage → plan and return the run_id (no extraction needed:

    every field ``emit_ccdash_event`` reads tolerates missing downstream
    artifacts via safe-load defaults).
    """

    cap = capture_idea(_IDEA, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    plan = plan_run(tri.intent_id, paths=paths)
    return plan.run_id


def test_emit_ccdash_event_generic_path_unchanged(tmp_foundry: FoundryPaths) -> None:
    """Calling without ``search_metrics`` preserves prior behavior exactly."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    event_id = telemetry.emit_ccdash_event(run_id, paths=tmp_foundry)

    # Return value is the event_id (not a Path) and matches the persisted event.
    assert isinstance(event_id, str)
    assert event_id

    on_disk = load_yaml(rp.ccdash_event)
    assert on_disk["event_id"] == event_id
    assert on_disk["run_id"] == run_id

    # None of the Wave 2 search-specific fields are present when the caller
    # never supplied search_metrics.
    search_fields = {
        "queries_executed",
        "urls_extracted",
        "useful_source_count",
        "duplicate_rate",
        "extraction_failure_rate",
        "citation_coverage",
        "estimated_cost_usd",
        "latency_ms",
    }
    assert search_fields.isdisjoint(on_disk["metrics"])

    result = validate(on_disk, "ccdash_event")
    assert result.ok, result.errors


def test_emit_ccdash_event_search_metrics_passthrough(tmp_foundry: FoundryPaths) -> None:
    """``search_metrics`` keys are merged additively into the event's metrics."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    search_metrics = {
        "queries_executed": 3,
        "urls_extracted": 12,
        "useful_source_count": 5,
        "duplicate_rate": 0.25,
        "extraction_failure_rate": 0.1,
        "citation_coverage": 0.8333,
        "estimated_cost_usd": 0.0042,
        "latency_ms": 1580,
    }

    event_id = telemetry.emit_ccdash_event(
        run_id, paths=tmp_foundry, search_metrics=search_metrics
    )

    on_disk = load_yaml(rp.ccdash_event)
    assert on_disk["event_id"] == event_id
    for key, value in search_metrics.items():
        assert on_disk["metrics"][key] == value

    # Pre-existing generic metrics are still present alongside the additive
    # search fields (merge, not replace).
    assert "claims_total" in on_disk["metrics"]
    assert "source_cards_created" in on_disk["metrics"]

    # Mirrored copy in ccdash/events/<event_id>.yaml also carries the merge.
    mirror = tmp_foundry.ccdash / "events" / f"{event_id}.yaml"
    mirrored = load_yaml(mirror)
    assert mirrored["metrics"]["queries_executed"] == 3

    result = validate(on_disk, "ccdash_event")
    assert result.ok, result.errors


def test_emit_ccdash_event_empty_search_metrics_is_noop(tmp_foundry: FoundryPaths) -> None:
    """An empty dict behaves identically to omitting the kwarg (falsy guard)."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    event_id = telemetry.emit_ccdash_event(run_id, paths=tmp_foundry, search_metrics={})
    on_disk = load_yaml(rp.ccdash_event)
    assert on_disk["event_id"] == event_id
    assert "queries_executed" not in on_disk["metrics"]


# ===========================================================================
# CCDash HTTP POST wiring (best-effort, config-gated, fail-open).
# ===========================================================================
#
# See docs/project_plans/design-specs/ccdash-run-telemetry-transport-handoff.md
# — the YAML mirror written above is unaffected either way; these tests pin
# that the POST is purely additive and never breaks the mirror or the run.


def test_emit_ccdash_event_ccdash_post_skipped_when_unconfigured(
    tmp_foundry: FoundryPaths, monkeypatch
) -> None:
    """Unset CCDash env -> YAML mirror written normally, no HTTP attempted."""

    monkeypatch.delenv("CCDASH_BASE_URL", raising=False)
    monkeypatch.delenv("CCDASH_INGEST_TOKEN", raising=False)

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    with patch("urllib.request.urlopen") as mock_urlopen:
        event_id = telemetry.emit_ccdash_event(run_id, paths=tmp_foundry)

    mock_urlopen.assert_not_called()

    on_disk = load_yaml(rp.ccdash_event)
    assert on_disk["event_id"] == event_id
    assert on_disk["run_id"] == run_id
    result = validate(on_disk, "ccdash_event")
    assert result.ok, result.errors

    trace = load_jsonl(rp.run_trace)
    post_events = [e for e in trace if e.get("stage") == "ccdash_post"]
    assert post_events, "expected a ccdash_post trace entry"
    assert post_events[-1]["posted"] is False


def test_emit_ccdash_event_ccdash_post_failure_never_propagates(
    tmp_foundry: FoundryPaths, monkeypatch
) -> None:
    """CCDash configured but unreachable -> emit still succeeds, mirror intact."""

    import urllib.error

    monkeypatch.setenv("CCDASH_BASE_URL", "http://ccdash.internal:9200")
    monkeypatch.setenv("CCDASH_INGEST_TOKEN", "tok123")

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        event_id = telemetry.emit_ccdash_event(run_id, paths=tmp_foundry)

    # The run's return value and durable YAML mirror are unaffected by the
    # failed POST — this is the core fail-open guarantee.
    on_disk = load_yaml(rp.ccdash_event)
    assert on_disk["event_id"] == event_id
    assert on_disk["run_id"] == run_id
    result = validate(on_disk, "ccdash_event")
    assert result.ok, result.errors

    mirror = tmp_foundry.ccdash / "events" / f"{event_id}.yaml"
    assert load_yaml(mirror)["event_id"] == event_id

    trace = load_jsonl(rp.run_trace)
    post_events = [e for e in trace if e.get("stage") == "ccdash_post"]
    assert post_events, "expected a ccdash_post trace entry"
    assert post_events[-1]["posted"] is False


def test_emit_ccdash_event_ccdash_post_success_traced(
    tmp_foundry: FoundryPaths, monkeypatch
) -> None:
    """CCDash configured and reachable -> POST fires and is traced as posted."""

    import json
    from unittest.mock import MagicMock

    monkeypatch.setenv("CCDASH_BASE_URL", "http://ccdash.internal:9200")
    monkeypatch.setenv("CCDASH_INGEST_TOKEN", "tok123")

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)

    resp = MagicMock()
    resp.read.return_value = json.dumps({"accepted": True}).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=resp):
        event_id = telemetry.emit_ccdash_event(run_id, paths=tmp_foundry)

    on_disk = load_yaml(rp.ccdash_event)
    assert on_disk["event_id"] == event_id
    result = validate(on_disk, "ccdash_event")
    assert result.ok, result.errors

    trace = load_jsonl(rp.run_trace)
    post_events = [e for e in trace if e.get("stage") == "ccdash_post"]
    assert post_events, "expected a ccdash_post trace entry"
    assert post_events[-1]["posted"] is True
