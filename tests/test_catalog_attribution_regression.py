"""SMP-4.6: durable, FROZEN regression fixtures for attribution shapes.

A lesson already learned the hard way in this repo (see
``.claude/agent-memory`` and ``assertion-registry-edition-traps.md``): a
"legacy still validates" test is vacuous without a genuinely frozen fixture,
because a fixture regenerated from current code at test-run time can never
detect drift in that same code -- it drifts along with it.

So every expected value this module asserts against lives in a checked-in
JSON file under ``tests/fixtures/attribution/`` (see that directory's
``README.md``), hand-frozen once from a real call into the actual service
code with fixed, deterministic inputs. This module never writes those files;
it only reads them and diffs real output against them.

Four things are frozen here:

1. ``catalog_service.attribution_coverage()``'s tri-state coverage block --
   the same tri-state machinery ``test_catalog_attribution_coverage.py``
   exercises behaviourally, but pinned to an exact, checked-in shape here,
   with three DELIBERATELY DISTINCT cardinalities (2 present / 1 absent / 4
   not_yet_assessed) so a future collapse of ``absent`` into
   ``not_yet_assessed`` (or the reverse) cannot hide behind coincidentally
   equal counts.
2. ``export_service._resolve_source()``'s resolved-source payload for a card
   carrying the SMP-1.4/SMP-4.4 provider-metadata fields
   (``authors``/``doi``/``publisher``/``version``/``attribution_summary``).
3. The same function's output for a source card predating this feature
   entirely -- the genuinely PRE-CHANGE (legacy) shape, modelled on
   ``_LEGACY_RESOLVED_SOURCE_EXPORT`` in ``tests/test_schema_validation.py``
   (same idea -- a payload with none of the new keys must still resolve
   cleanly -- applied here to the catalog/export code path rather than to
   raw schema validation, so it is complementary, not a duplicate).
4. ``attribution_triage.mint_attribution_record().as_dict()`` -- the
   authoritative ``source_attribution`` record shape. ``attribution_id`` is
   content-derived (``short_hash`` over fixed inputs, no wall-clock read),
   so this is exactly reproducible from the same constructor arguments.

Do not edit the fixture JSON files from this module. If the underlying shape
changes deliberately, regenerate and freeze a new fixture by hand (or via a
one-off script) and say so in the commit -- never let a test auto-regenerate
its own expectation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import catalog_service as svc
from research_foundry.services.attribution_triage import mint_attribution_record
from research_foundry.services.export_service import _resolve_source, _sensitivity_rank
from research_foundry.yamlio import dump_yaml

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "attribution"


def _load_fixture(name: str) -> Any:
    path = _FIXTURES_DIR / name
    assert path.exists(), f"frozen fixture missing on disk: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_summary(actual: dict[str, Any], expected: dict[str, Any]) -> str:
    """Human-readable, key-level diff for a failed fixture comparison.

    Reports exactly what drifted -- added keys, removed keys, and changed
    values (with each side's type when the value differs) -- so a failure
    here reads as "what shape-drifted", not just "dicts not equal".
    """

    actual_keys = set(actual)
    expected_keys = set(expected)
    added = sorted(actual_keys - expected_keys)
    removed = sorted(expected_keys - actual_keys)
    changed = sorted(
        k
        for k in actual_keys & expected_keys
        if actual[k] != expected[k]
    )
    lines = []
    if added:
        lines.append(f"  keys ADDED (present in actual, not in frozen fixture): {added}")
    if removed:
        lines.append(f"  keys REMOVED (in frozen fixture, missing from actual): {removed}")
    for k in changed:
        lines.append(
            f"  key {k!r} CHANGED: frozen={expected[k]!r} "
            f"({type(expected[k]).__name__}) -> actual={actual[k]!r} "
            f"({type(actual[k]).__name__})"
        )
    return "\n".join(lines) if lines else "  (no key-level diff found -- nested value mismatch)"


# ---------------------------------------------------------------------------
# 1. Catalog tri-state coverage block -- frozen shape, distinct cardinalities.
# ---------------------------------------------------------------------------

_PRESENT_MIRROR = {
    "attribution_ids": ["attrib_a"],
    "count": 1,
    "rollups": [
        {
            "asserter_id": "semantic_scholar",
            "assertion_kind": "citation_count",
            "attribution_ids": ["attrib_a"],
            "count": 1,
            "best_attribution_id": "attrib_a",
            "weakest_attribution_id": "attrib_a",
            "comparable": True,
        }
    ],
}
_ABSENT_MIRROR = {"attribution_ids": [], "count": 0, "rollups": []}

_PRESENT_IDS = ["src_present_1", "src_present_2"]
_ABSENT_IDS = ["src_absent_1"]
_UNASSESSED_IDS = [
    "src_unassessed_1",
    "src_unassessed_2",
    "src_unassessed_3",
    "src_unassessed_4",
]


def _plant_distinct_magnitude_run(paths: FoundryPaths, run_id: str) -> None:
    """2 present / 1 absent / 4 not_yet_assessed -- three distinct counts.

    Distinct magnitudes matter: if a future change folded ``absent`` into
    ``not_yet_assessed`` (or split one bucket wrong), the resulting counts
    could not coincidentally match this fixture's 2/1/4/3/7 shape the way
    they could with, say, an all-1s scenario.
    """

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

    def _card(source_card_id: str, attribution_summary: dict | None) -> dict:
        card: dict = {
            "type": "source_card",
            "source_card_id": source_card_id,
            "sensitivity": "public",
            "trust": {"source_rank": "primary"},
            "usage": "direct",
            "source": {"title": source_card_id, "source_type": "paper"},
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

    for sid in _PRESENT_IDS:
        dump_md(_card(sid, _PRESENT_MIRROR), f"# {sid}", rp.sources / f"{sid}.md")
    for sid in _ABSENT_IDS:
        dump_md(_card(sid, _ABSENT_MIRROR), f"# {sid}", rp.sources / f"{sid}.md")
    for sid in _UNASSESSED_IDS:
        dump_md(_card(sid, None), f"# {sid}", rp.sources / f"{sid}.md")

    def _claim(source_card_id: str) -> dict:
        return {
            "claim_id": f"clm_{source_card_id}",
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

    all_ids = _PRESENT_IDS + _ABSENT_IDS + _UNASSESSED_IDS
    dump_yaml(
        {"id": f"ledger_{run_id}", "claims": [_claim(sid) for sid in all_ids]},
        rp.claim_ledger,
    )


def test_catalog_coverage_matches_frozen_tristate_fixture(tmp_foundry: FoundryPaths) -> None:
    _plant_distinct_magnitude_run(tmp_foundry, "rf_run_smp46_tristate")
    svc.import_run(tmp_foundry, "rf_run_smp46_tristate")

    actual = svc.attribution_coverage(tmp_foundry)
    expected = _load_fixture("catalog_coverage_tristate.json")

    assert actual == expected, (
        "catalog_service.attribution_coverage() output no longer matches the "
        "frozen SMP-4.6 fixture (tests/fixtures/attribution/"
        "catalog_coverage_tristate.json) -- this is exactly the silent shape "
        "drift this regression test exists to catch:\n"
        + _diff_summary(actual, expected)
    )


def test_tristate_present_absent_not_yet_assessed_stay_distinct(
    tmp_foundry: FoundryPaths,
) -> None:
    """Frozen expectation: the three buckets never collapse into each other.

    Asserted independently of the full-dict comparison above so a partial
    collapse (e.g. someone folds ``absent`` counts into ``not_yet_assessed``
    while leaving ``present``/``total`` alone) fails on an assertion that
    names exactly which distinction broke.
    """

    _plant_distinct_magnitude_run(tmp_foundry, "rf_run_smp46_distinctness")
    svc.import_run(tmp_foundry, "rf_run_smp46_distinctness")

    coverage = svc.attribution_coverage(tmp_foundry)
    expected = _load_fixture("catalog_coverage_tristate.json")

    assert coverage["present"] == expected["present"] == 2, "present count drifted"
    assert coverage["absent"] == expected["absent"] == 1, "absent count drifted"
    assert (
        coverage["not_yet_assessed"] == expected["not_yet_assessed"] == 4
    ), "not_yet_assessed count drifted"
    # The defining invariant: absent and not_yet_assessed are DIFFERENT
    # counts here by construction (1 vs 4) -- a collapse into a shared
    # bucket cannot reproduce both values simultaneously.
    assert coverage["absent"] != coverage["not_yet_assessed"], (
        "absent and not_yet_assessed collapsed to the same count -- the "
        "tri-state distinction this milestone exists to preserve is broken"
    )
    assert coverage["assessed"] == coverage["present"] + coverage["absent"], (
        "assessed must equal present + absent, excluding not_yet_assessed "
        "from the numerator (the no-backfill honesty control)"
    )


# ---------------------------------------------------------------------------
# 2 & 3. Resolved-source payload -- post-change and genuinely pre-change.
# ---------------------------------------------------------------------------

_ATTRIBUTION_SUMMARY_MIRROR = {
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


def _resolve_frozen_card() -> dict[str, Any]:
    """Post-change card: carries authors/doi/publisher/version/attribution_summary."""

    cards = {
        "src_frozen": {
            "meta": {
                "source_card_id": "src_frozen",
                "sensitivity": "public",
                "trust": {"source_rank": "primary"},
                "usage": "direct",
                "source": {
                    "title": "Frozen Source",
                    "source_type": "paper",
                    "authors": ["Jane Doe", "John Roe"],
                    "publisher": "Example Press",
                    "version": "2nd edition",
                    "locator": {
                        "url": "https://example.test/frozen",
                        "doi": "10.1000/xyz123",
                    },
                },
                "attribution_summary": _ATTRIBUTION_SUMMARY_MIRROR,
            },
            "points": {
                "ev_frozen": {
                    "evidence_id": "ev_frozen",
                    "locator": "p1",
                    "quote": "Frozen quote.",
                    "summary": "Frozen summary.",
                }
            },
            "body": "# frozen",
            "path": Path("dummy-frozen.md"),
        }
    }
    citation = {
        "source_card_id": "src_frozen",
        "evidence_id": "ev_frozen",
        "relation": "supports",
        "locator": "p1",
    }
    return _resolve_source(citation, cards, _sensitivity_rank("public"))


def _resolve_legacy_card() -> dict[str, Any]:
    """Genuinely PRE-CHANGE card: no authors/doi/publisher/version on
    `source`, no `attribution_summary` key on the card meta at all -- the
    exact pre-SMP-1.4/SMP-4.4 resolved-source shape, modelled on
    `_LEGACY_RESOLVED_SOURCE_EXPORT` in tests/test_schema_validation.py
    without duplicating that fixture verbatim."""

    cards = {
        "src_legacy": {
            "meta": {
                "source_card_id": "src_legacy",
                "sensitivity": "public",
                "trust": {"source_rank": "primary"},
                "usage": {"allowed_for_public_output": True},
                "source": {
                    "title": "Legacy Source",
                    "source_type": "official_doc",
                    "locator": {"url": "https://example.test/legacy"},
                },
            },
            "points": {
                "ev_legacy": {
                    "evidence_id": "ev_legacy",
                    "locator": "p1",
                    "quote": "Legacy quote.",
                    "summary": "Legacy summary.",
                }
            },
            "body": "# legacy",
            "path": Path("dummy-legacy.md"),
        }
    }
    citation = {
        "source_card_id": "src_legacy",
        "evidence_id": "ev_legacy",
        "relation": "supports",
        "locator": "p1",
    }
    return _resolve_source(citation, cards, _sensitivity_rank("public"))


def test_resolved_source_with_attribution_summary_matches_frozen_fixture() -> None:
    actual = _resolve_frozen_card()
    expected = _load_fixture("resolved_source_with_attribution_summary.json")

    assert actual == expected, (
        "export_service._resolve_source() output for a post-change source "
        "card no longer matches the frozen SMP-4.6 fixture (tests/fixtures/"
        "attribution/resolved_source_with_attribution_summary.json):\n"
        + _diff_summary(actual, expected)
    )


def test_resolved_source_legacy_pre_change_fixture_still_resolves_cleanly() -> None:
    """The genuinely PRE-CHANGE fixture: a card with none of the new keys at
    all must still resolve, with the five new resolved-source properties
    present as `null` rather than missing -- proving the change is additive,
    not merely tolerated by accident."""

    actual = _resolve_legacy_card()
    expected = _load_fixture("resolved_source_legacy_pre_change.json")

    assert actual == expected, (
        "export_service._resolve_source() output for a genuinely pre-SMP "
        "(legacy) source card no longer matches the frozen SMP-4.6 fixture "
        "(tests/fixtures/attribution/resolved_source_legacy_pre_change.json) "
        "-- this must stay additive-only:\n" + _diff_summary(actual, expected)
    )

    # Additive proof, spelled out explicitly: every one of the five new
    # keys is PRESENT (not KeyError) and null (never silently omitted).
    for key in ("authors", "doi", "publisher", "version", "attribution_summary"):
        assert key in actual, f"legacy resolved-source dict is missing key {key!r} entirely"
        assert actual[key] is None, (
            f"legacy resolved-source dict's {key!r} should be null for a "
            f"pre-change card, got {actual[key]!r}"
        )


# ---------------------------------------------------------------------------
# 4. Authoritative source_attribution record shape.
# ---------------------------------------------------------------------------


def test_source_attribution_record_matches_frozen_fixture() -> None:
    record = mint_attribution_record(
        source="src_frozen",
        asserter_id="semantic_scholar",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=42,
        observed_at="2026-01-15T00:00:00+00:00",
        license_basis="open_api",
        retrieval_evidence_ref="fetch_receipt_001",
    )
    actual = record.as_dict()
    expected = _load_fixture("source_attribution_record.json")

    assert actual == expected, (
        "attribution_triage.mint_attribution_record().as_dict() no longer "
        "matches the frozen SMP-4.6 fixture (tests/fixtures/attribution/"
        "source_attribution_record.json) -- attribution_id is content-"
        "derived from fixed inputs, so any diff here is a real shape or "
        "hashing change, not test flakiness:\n" + _diff_summary(actual, expected)
    )
