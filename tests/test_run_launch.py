"""Tests for the run-launch orchestration service (http-run-launch-endpoint).

Covers ``launch_run``'s branch logic directly (no ``TestClient`` needed):
- ``text`` path: full capture -> triage -> plan chain.
- ``intent_id`` path: plan-only, ``raw_idea_id`` is ``None``.
- Both-set / neither-set -> ``ValueError``.
- Unknown ``intent_id`` -> ``NotFoundError`` (propagated from ``plan_run``).
- Governance-blocked plan -> ``GovernanceError`` (propagated from ``plan_run``),
  reusing the exact minimal intent fixture from
  ``tests/test_cli_governance.py::_write_intent`` (a ``work_approved`` profile
  against a personal-only intent trips ``no_work_keys_for_personal_runs``).
"""

from __future__ import annotations

import pytest

from research_foundry.errors import GovernanceError, NotFoundError
from research_foundry.services.run_launch import LaunchRunResult, launch_run
from research_foundry.yamlio import dump_yaml


def _write_intent(paths, *, key_profile_allowed: str = "personal") -> str:
    """Minimal intent fixture for the governance-block test.

    Mirrors ``tests/test_cli_governance.py::_write_intent`` verbatim (the
    actual existing ``GovernanceError`` fixture in this codebase — see
    Completion Report deviation note: the contract pointed at
    ``tests/test_planning.py`` for this fixture, but the real minimal setup
    lives in ``tests/test_cli_governance.py``).
    """
    intent_id = "intent_research_20260613_demo_topic"
    intent = {
        "id": intent_id,
        "title": "Demo research topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Investigate the demo topic deterministically.",
        "governance": {
            "sensitivity": "personal",
            "key_profile_allowed": key_profile_allowed,
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{intent_id}.yaml")
    return intent_id


# --- text path ---------------------------------------------------------------


def test_launch_run_text_path_runs_full_chain(tmp_foundry, sample_idea_text):
    result = launch_run(text=sample_idea_text, paths=tmp_foundry)

    assert isinstance(result, LaunchRunResult)
    assert result.status == "planned"
    assert result.raw_idea_id is not None
    assert result.raw_idea_id.startswith("raw_")
    assert result.intent_id is not None
    assert result.run_id.startswith("rf_run_")
    assert result.brief_path.exists()
    assert result.swarm_path.exists()
    assert result.routing_path.exists()


# --- intent_id path -----------------------------------------------------------


def test_launch_run_intent_id_path_skips_capture_triage(tmp_foundry):
    intent_id = _write_intent(tmp_foundry)

    result = launch_run(intent_id=intent_id, paths=tmp_foundry)

    assert isinstance(result, LaunchRunResult)
    assert result.status == "planned"
    assert result.raw_idea_id is None
    assert result.intent_id == intent_id
    assert result.run_id.startswith("rf_run_")


# --- exactly-one-of validation ------------------------------------------------


def test_launch_run_both_set_raises_value_error(tmp_foundry, sample_idea_text):
    intent_id = _write_intent(tmp_foundry)

    with pytest.raises(ValueError):
        launch_run(text=sample_idea_text, intent_id=intent_id, paths=tmp_foundry)


def test_launch_run_neither_set_raises_value_error(tmp_foundry):
    with pytest.raises(ValueError):
        launch_run(paths=tmp_foundry)


# --- not-found -----------------------------------------------------------------


def test_launch_run_unknown_intent_id_raises_not_found(tmp_foundry):
    with pytest.raises(NotFoundError):
        launch_run(intent_id="intent_does_not_exist", paths=tmp_foundry)


# --- governance block ----------------------------------------------------------


def test_launch_run_governance_block_raises_governance_error(tmp_foundry):
    intent_id = _write_intent(tmp_foundry, key_profile_allowed="personal")

    with pytest.raises(GovernanceError) as exc_info:
        launch_run(intent_id=intent_id, profile="work_approved", paths=tmp_foundry)

    assert exc_info.value.violations  # list[str] of blocked rule_ids
