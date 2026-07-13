"""Deterministic, local-only contract checks for RAL Phase 0 research artifacts.

This is deliberately a fixture harness, not an empirical replay or production
implementation. It must never access a private corpus, real connectors, or a
shared store.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

MANIFEST_PATH = (
    Path(__file__).parent / "fixtures" / "assertion_ledger" / "phase0_fixture_manifest.json"
)
SNAPSHOT_ROOT = MANIFEST_PATH.parent / "rf_phase0_evidence_snapshot"
EXPECTED_PROPAGATION_PATH = MANIFEST_PATH.parent / "phase0_propagation_expected_manifest.json"


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _stable_id(kind: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"kind": kind, "payload": payload}, sort_keys=True, separators=(",", ":")
    )
    return f"{kind}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:20]}"


def _identity_records(count: int) -> Iterable[dict[str, str]]:
    for number in range(count):
        yield {
            "edition": f"edition-{number % 32:02d}",
            "passage": f"passage-{number:03d}",
            "assertion": f"assertion-{number:03d}",
            "population": "adults" if number % 2 else "children",
            "timeframe": f"20{20 + number % 5}",
        }


def _identity_snapshot(records: Iterable[dict[str, str]]) -> dict[str, str]:
    return {record["assertion"]: _stable_id("assertion", record) for record in records}


def _propagation_graph(event_type: str, graph_number: int, classes: list[str]) -> dict[str, str]:
    return {object_class: f"{event_type}-{graph_number}-{object_class}" for object_class in classes}


def _expected_propagation_objects() -> dict[str, dict[str, str]]:
    expected = json.loads(EXPECTED_PROPAGATION_PATH.read_text(encoding="utf-8"))
    return {item["object_id"]: item for item in expected["expected_objects"]}


def _apply_delivery(
    expected: dict[str, dict[str, str]], delivered_ids: Iterable[str], state: dict[str, Any]
) -> None:
    for object_id in delivered_ids:
        expected_item = expected[object_id]
        if object_id in state["receipts"]:
            continue
        state["receipts"].add(object_id)
        state["actions"][object_id] = expected_item["action"]
        if expected_item["object_class"] == "assertion_version":
            state["eligible_assertion_ids"].discard(object_id)
        if expected_item["object_class"] == "derived_cache_or_index":
            state["current_read_ids"].discard(object_id)


def phase0_summary() -> dict[str, Any]:
    """Return reproducible aggregate numbers used by the three result artifacts."""
    fixture = _manifest()
    replay = fixture["historical_replay"]
    identity = fixture["identity_merge"]
    propagation = fixture["retraction_propagation"]
    expected_objects = (
        propagation["graphs_per_event"]
        * len(propagation["event_types"])
        * len(propagation["object_classes"])
    )
    return {
        "fixture_kind": fixture["fixture_kind"],
        "historical_replay": {
            "runs": replay["runs"],
            "source_inputs": replay["source_inputs"],
            "processing_opportunities": replay["run_source_memberships"],
            "safe_reuse": replay["safe_reuse"],
            "safe_reuse_rate": replay["safe_reuse"] / replay["run_source_memberships"],
            "provenance_sample": replay["provenance_audit"]["sampled"],
            "provenance_correct": replay["provenance_audit"]["correct"],
            "provenance_rate": replay["provenance_audit"]["correct"]
            / replay["provenance_audit"]["sampled"],
        },
        "identity_merge": {
            "assertions": identity["assertions"],
            "identity_comparisons": identity["assertions"]
            * identity["reruns_per_order"]
            * identity["orders"],
            "material_changes": identity["material_changes"],
            "merge_candidates": identity["merge_candidates"],
            "hard_negatives": identity["hard_negatives"],
        },
        "retraction_propagation": {
            "graphs": propagation["graphs_per_event"] * len(propagation["event_types"]),
            "expected_objects": expected_objects,
            "enumerated_objects": expected_objects,
        },
    }


def test_historical_replay_fixture_denominators_are_exact() -> None:
    fixture = _manifest()["historical_replay"]
    summary = phase0_summary()["historical_replay"]

    assert fixture["runs"] == 12
    assert 100 <= fixture["source_inputs"] <= 300
    assert (
        sum(fixture["rejection_reasons"].values()) + fixture["safe_reuse"]
        == fixture["run_source_memberships"]
    )
    assert summary["safe_reuse_rate"] == 0.25
    assert summary["provenance_rate"] == 1.0
    assert fixture["provenance_audit"]["sampled"] == fixture["safe_reuse"]
    assert (
        fixture["baseline"]["model_calls"] - fixture["replay"]["model_calls"]
        == fixture["safe_reuse"]
    )


def test_identity_is_deterministic_and_material_changes_are_lineage_linked() -> None:
    fixture = _manifest()["identity_merge"]
    records = list(_identity_records(fixture["assertions"]))
    expected = _identity_snapshot(records)

    for ordered_records in (records, list(reversed(records))):
        for _ in range(fixture["reruns_per_order"]):
            assert _identity_snapshot(ordered_records) == expected

    predecessor_links: dict[str, str] = {}
    retained_prior_ids = set(expected.values())
    for record in records[: fixture["material_changes"]]:
        changed = {**record, "timeframe": "materially-changed"}
        changed_id = _stable_id("assertion", changed)
        predecessor_id = expected[record["assertion"]]
        assert changed_id != predecessor_id
        assert predecessor_id.startswith("assertion_")
        predecessor_links[changed_id] = predecessor_id

    assert len(predecessor_links) == fixture["material_changes"]
    assert set(predecessor_links.values()).issubset(retained_prior_ids)

    state_machine = fixture["state_machine"]
    state = state_machine["initial_state"]
    history = [state]
    for transition in state_machine["transitions"]:
        state = transition
        history.append(state)
        assert retained_prior_ids
        assert predecessor_links
    assert history == ["proposed", "reviewed", "active", "split", "superseded", "rolled_back"]
    assert state == "rolled_back"
    assert state_machine["required_preservation"] == [
        "source_assertion_id",
        "historical_reference",
        "predecessor_assertion_id",
    ]

    assert fixture["merge_candidates"] >= 100
    assert fixture["hard_negatives"] >= 40
    assert fixture["human_reviewer_labels"] is False


def test_retraction_propagation_fixture_matches_independent_expected_manifest() -> None:
    fixture = _manifest()["retraction_propagation"]
    classes = fixture["object_classes"]
    expected = _expected_propagation_objects()
    assert len(expected) == 120
    assert {item["object_class"] for item in expected.values()} == set(classes)
    assert {item["action"] for item in expected.values()} == set(
        fixture["expected_action_by_class"].values()
    )

    for event_type in fixture["event_types"]:
        for graph_number in range(fixture["graphs_per_event"]):
            graph = _propagation_graph(event_type, graph_number, classes)
            observed = list(graph.values())
            assert set(observed).issubset(expected)
            assert len(observed) == len(classes)

            state: dict[str, Any] = {
                "receipts": set(),
                "actions": {},
                "eligible_assertion_ids": {graph["assertion_version"]},
                "current_read_ids": set(observed),
            }
            first_half, remaining = observed[:5], observed[5:]
            _apply_delivery(expected, first_half, state)
            assert len(state["receipts"]) == 5
            _apply_delivery(expected, list(reversed(first_half)), state)
            assert len(state["receipts"]) == 5
            _apply_delivery(expected, remaining, state)
            assert set(state["receipts"]) == set(observed)
            assert state["actions"] == {
                object_id: expected[object_id]["action"] for object_id in observed
            }
            assert graph["assertion_version"] not in state["eligible_assertion_ids"]
            assert graph["derived_cache_or_index"] not in state["current_read_ids"]
            assert len(state["receipts"]) == len(set(state["receipts"]))

    summary = phase0_summary()["retraction_propagation"]
    assert len(expected) == summary["expected_objects"] == summary["enumerated_objects"]


def test_rf_evidence_snapshot_is_complete_and_claim_traceable() -> None:
    ledger = yaml.safe_load((SNAPSHOT_ROOT / "claims" / "claim_ledger.yaml").read_text())
    verification = yaml.safe_load((SNAPSHOT_ROOT / "reviews" / "verification.yaml").read_text())
    report = (SNAPSHOT_ROOT / "reports" / "report_draft.md").read_text(encoding="utf-8")
    claims = ledger["claims"]
    source_ids = {source["source_card_id"] for claim in claims for source in claim["sources"]}

    assert ledger["verification_status"] == "passed"
    assert len(claims) == 16
    assert {claim["status"] for claim in claims} == {"supported"}
    assert verification["passed"] is True
    assert verification["exit_code"] == 0
    for source_id in source_ids:
        source_card = SNAPSHOT_ROOT / "sources" / f"{source_id}.md"
        assert source_card.is_file()
        source_text = source_card.read_text(encoding="utf-8")
        assert "known_limitations:\n  - Synthetic/local-only fixture evidence" in source_text
        assert "Representative private-corpus economics" in source_text
        assert "canonical-merge safety" in source_text
    for claim in claims:
        assert f"[claim:{claim['claim_id']}]" in report

    rebuild_script = (MANIFEST_PATH.parent / "run_phase0_rf_evidence.sh").read_text()
    for command in (
        "rf ingest",
        "enrich_phase0_rf_source_cards.py",
        "rf extract",
        "rf claim-map",
        "rf synthesize",
        "rf verify",
    ):
        assert command in rebuild_script


if __name__ == "__main__":
    print(json.dumps(phase0_summary(), indent=2, sort_keys=True))
