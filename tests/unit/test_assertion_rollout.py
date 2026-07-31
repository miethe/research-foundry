"""P8 readiness: default-off controls and privacy-safe local rehearsals."""

from __future__ import annotations

import json

import pytest

from research_foundry.config import FoundryConfig
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.assertion_rollout import (
    _ingest_run_source_cards,
    backfill_dry_run,
    readiness_metrics,
    rollback_disable_rehearsal,
    write_readiness_receipt,
)
from research_foundry.services.run_launch import launch_run, retrieve_first_reuse_decision
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def test_assertion_ledger_controls_are_independently_default_off(tmp_foundry) -> None:
    # This project's own deployed `foundry.yaml` intentionally opts all three
    # controls on for its single-operator deployment (see
    # docs/user/assertion-ledger.md). `tmp_foundry` copies that real file, so
    # the code-level "default off" contract has to be exercised against a
    # clean/unconfigured `assertion_ledger` block, not the deployed opt-in.
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"].pop("assertion_ledger", None)
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    config = FoundryConfig(paths=tmp_foundry)
    assert config.assertion_ledger_controls().ledger_write_enabled is False
    assert config.assertion_ledger_controls().automated_reuse_enabled is False
    assert config.assertion_ledger_controls().canonical_claims_enabled is False

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": False,
        "canonical_claims_enabled": True,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    controls = FoundryConfig(paths=tmp_foundry).assertion_ledger_controls()
    assert controls.ledger_write_enabled is True
    assert controls.automated_reuse_enabled is False
    assert controls.canonical_claims_enabled is True
    capabilities = FoundryConfig(paths=tmp_foundry).assertion_ledger_capabilities()
    assert capabilities.ledger_write_allowed is True
    assert capabilities.automated_reuse_allowed is False
    assert capabilities.canonical_claims_allowed is True


def test_write_and_automated_reuse_consumers_fail_closed_by_default(tmp_foundry) -> None:
    # Same rationale as the test above: exercise the code-level fail-closed
    # default, not this project's deliberate single-operator opt-in.
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"].pop("assertion_ledger", None)
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    assertion = {
        "assertion_id": "ast_ready",
        "workspace_id": "workspace-a",
        "lifecycle_state": "eligible",
        "rights_allowed": True,
        "sensitivity_allowed": True,
        "evaluation_passed": True,
        "freshness_current": True,
        "invalidation_state": "active",
        "source_edition_id": f"sed_{'a' * 64}",
        "extraction_contract": "contract-v1",
    }
    capabilities = FoundryConfig(paths=tmp_foundry).assertion_ledger_capabilities()
    decision = retrieve_first_reuse_decision(
        assertion, workspace_id="workspace-a", capabilities=capabilities
    )
    assert decision.reason_code == "automated_reuse_disabled"
    with pytest.raises(ValueError, match="reuse_not_eligible:automated_reuse_disabled"):
        launch_run(
            text="Do not launch when automated reuse is default-off.",
            reuse_assertion=assertion,
            reuse_workspace_id="workspace-a",
            paths=tmp_foundry,
        )

    tmp_foundry.run_paths("rf_p8_write_gate").ensure_scaffold()
    ingest_source(
        "p8-evidence.txt",
        run_id="rf_p8_write_gate",
        content="This stays run-local until the ledger write control is enabled.",
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    assert not list((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/source.yaml"))


def test_backfill_passes_recorded_extraction_status_when_present(tmp_foundry) -> None:
    """FIX-4: a historical card's own recorded extraction_status is authoritative
    (written down at capture time, not inferred here) and must reach the registry.
    """

    run_id = "rf_p8_backfill_status_present"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    card = ingest_source(
        "backfill-status.txt",
        run_id=run_id,
        content="Historical card with a recorded status.",
        paths=tmp_foundry,
    )
    from research_foundry.frontmatter import load_md

    metadata, _body = load_md(card.path)
    assert metadata.get("extraction_status") == "full_text"

    registry = AssertionRegistry(workspace_id="workspace-backfill", paths=tmp_foundry)
    counts = _ingest_run_source_cards(run_id, registry=registry, paths=tmp_foundry)
    assert counts["created"] == 1

    matches = registry.find_exact_passages(card.source_card_id, "Historical card with a recorded status.")
    assert len(matches) == 1
    edition, _passage = matches[0]
    assert registry.get_extraction_status(card.source_card_id, edition["source_edition_id"]) == "full_text"


def test_backfill_records_no_status_when_historical_card_lacks_one(tmp_foundry) -> None:
    """A card written before extraction_status existed lacks the field -- per the
    plan's 'never infer' decision, the backfill must pass nothing, not guess.
    """

    run_id = "rf_p8_backfill_status_absent"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    card = ingest_source(
        "backfill-no-status.txt",
        run_id=run_id,
        content="Historical card with no recorded status.",
        paths=tmp_foundry,
    )
    from research_foundry.frontmatter import dump_md, load_md

    metadata, body = load_md(card.path)
    del metadata["extraction_status"]
    dump_md(metadata, body, card.path)

    registry = AssertionRegistry(workspace_id="workspace-backfill", paths=tmp_foundry)
    counts = _ingest_run_source_cards(run_id, registry=registry, paths=tmp_foundry)
    assert counts["created"] == 1

    matches = registry.find_exact_passages(card.source_card_id, "Historical card with no recorded status.")
    assert len(matches) == 1
    edition, _passage = matches[0]
    assert registry.get_extraction_status(card.source_card_id, edition["source_edition_id"]) is None


def test_readiness_receipts_are_idempotent_and_exclude_sensitive_text(tmp_foundry) -> None:
    run = tmp_foundry.run_paths("rf_private_example")
    run.ensure_scaffold()
    run.claim_ledger.write_text(
        "claims:\n  - text: secret passage text must never appear in health output\n",
        encoding="utf-8",
    )
    config = FoundryConfig(paths=tmp_foundry)

    metrics = readiness_metrics(paths=tmp_foundry, config=config)
    first = backfill_dry_run(paths=tmp_foundry, config=config)
    second = backfill_dry_run(paths=tmp_foundry, config=config)
    rollback = rollback_disable_rehearsal(controls=config.assertion_ledger_controls())

    assert first == second
    assert metrics["counts"]["claim_ledgers"] == 1
    assert first["candidate_claim_ledgers"] == 1
    assert first["authoritative_data_mutated"] is False
    assert rollback["target_controls"] == {
        "ledger_write_enabled": False,
        "automated_reuse_enabled": False,
        "canonical_claims_enabled": False,
    }
    encoded = json.dumps({"metrics": metrics, "receipts": [first, rollback]})
    assert "secret passage text" not in encoded
    assert "rf_private_example" not in encoded

    path = write_readiness_receipt(paths=tmp_foundry, receipt=first)
    assert write_readiness_receipt(paths=tmp_foundry, receipt=first) == path
    assert json.loads(path.read_text(encoding="utf-8"))["receipt_id"] == first["receipt_id"]


@pytest.mark.parametrize(
    "receipt_id",
    [
        "ral_/../../escape",
        "ral_//tmp/escape",
        "/tmp/ral_backfill_dry_run_0123456789abcdef",
        "ral_backfill_dry_run_0123456789abcdef/escape",
        r"ral_backfill_dry_run_0123456789abcdef\\escape",
        "ral_backfill_dry_run_not-hexadecimal",
        "ral_unrecognized_kind_0123456789abcdef",
    ],
)
def test_readiness_receipt_ids_reject_path_traversal_and_noncanonical_values(tmp_foundry, receipt_id: str) -> None:
    with pytest.raises(ValueError, match="canonical deterministic receipt_id"):
        write_readiness_receipt(paths=tmp_foundry, receipt={"receipt_id": receipt_id})


def test_readiness_receipt_ids_accept_only_canonical_generated_values(tmp_foundry) -> None:
    receipts = [
        backfill_dry_run(paths=tmp_foundry),
        rollback_disable_rehearsal(controls=FoundryConfig(paths=tmp_foundry).assertion_ledger_controls()),
    ]
    readiness_directory = (tmp_foundry.rf_state / "assertion_ledger" / "readiness").resolve()
    for receipt in receipts:
        path = write_readiness_receipt(paths=tmp_foundry, receipt=receipt)
        assert path.parent.resolve() == readiness_directory
        assert path.name == f"{receipt['receipt_id']}.json"
