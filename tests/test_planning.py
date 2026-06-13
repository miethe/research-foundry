"""Tests for the planning service (``rf plan``).

Each test builds a real intent + I-BOM via the capture/triage service, then
plans a run and asserts the four run artifacts are written, schema-valid, and
that the routing decision's ``human_required`` flag reflects the intent's
``governance.requires_human_review``.
"""

from __future__ import annotations

from research_foundry.frontmatter import load_md
from research_foundry.registry import RUN_INDEX, Registry
from research_foundry.schemas import default_registry, validate
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.planning import PlanResult, plan_run
from research_foundry.yamlio import load_yaml


def _make_intent(text, *, sensitivity, tmp_foundry):
    """Capture + triage an idea, returning (intent_id, intent_dict)."""

    cap = capture_idea(text, sensitivity=sensitivity, paths=tmp_foundry)
    tri = triage_idea(cap.raw_idea_id, paths=tmp_foundry)
    assert tri.intent_id is not None
    intent = load_yaml(tmp_foundry.intents_active / f"{tri.intent_id}.yaml")
    return tri.intent_id, intent


def test_plan_run_creates_four_files(tmp_foundry, sample_idea_text):
    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)

    result = plan_run(intent_id, paths=tmp_foundry)

    assert isinstance(result, PlanResult)
    assert result.run_id.startswith("rf_run_")
    assert result.run_dir.is_dir()
    # All four artifacts exist on disk.
    assert result.brief_path.exists()
    assert result.swarm_path.exists()
    assert result.routing_path.exists()
    assert (result.run_dir / "run.yaml").exists()
    assert result.brief_path == result.run_dir / "research_brief.md"
    assert result.swarm_path == result.run_dir / "swarm_plan.yaml"
    assert result.routing_path == result.run_dir / "routing_decision.yaml"


def test_plan_artifacts_are_schema_valid(tmp_foundry, sample_idea_text):
    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    result = plan_run(intent_id, paths=tmp_foundry)

    reg = default_registry()
    assert reg.has("research_brief")
    assert reg.has("swarm_plan")
    assert reg.has("routing_decision")

    brief_meta, _ = load_md(result.brief_path)
    swarm = load_yaml(result.swarm_path)
    routing = load_yaml(result.routing_path)

    assert validate(brief_meta, "research_brief").ok
    assert validate(swarm, "swarm_plan").ok
    assert validate(routing, "routing_decision").ok

    # Cross-links are wired through.
    assert brief_meta["intent_id"] == intent_id
    assert swarm["brief_id"] == result.brief_id
    assert swarm["intent_id"] == intent_id
    assert routing["intent_id"] == intent_id
    assert routing["id"] == result.routing_id
    # Model profiles flow from the I-BOM model_policy into the swarm budget.
    assert swarm["budget"]["extraction_model_profile"] == "rf_extract_cheap"
    assert swarm["budget"]["synthesis_model_profile"] == "rf_synthesize_deep"
    assert swarm["budget"]["verification_model_profile"] == "rf_verify_balanced"
    # Selected tools are drawn from enabled tools in config/tools.yaml.
    assert "claude_agent_sdk" in routing["selected_tools"]


def test_human_required_false_for_personal(tmp_foundry, sample_idea_text):
    intent_id, intent = _make_intent(
        sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry
    )
    assert intent["governance"]["requires_human_review"] is False

    result = plan_run(intent_id, paths=tmp_foundry)
    routing = load_yaml(result.routing_path)
    assert routing["human_required"] is False


def test_human_required_true_for_work_sensitive(tmp_foundry, sample_idea_text):
    intent_id, intent = _make_intent(
        sample_idea_text, sensitivity="work_sensitive", tmp_foundry=tmp_foundry
    )
    assert intent["governance"]["requires_human_review"] is True

    result = plan_run(intent_id, paths=tmp_foundry)
    routing = load_yaml(result.routing_path)
    assert routing["human_required"] is True
    # run.yaml mirrors the flag.
    run_doc = load_yaml(result.run_dir / "run.yaml")
    assert run_doc["human_required"] is True
    assert run_doc["status"] == "planned"


def test_run_index_gets_a_row(tmp_foundry, sample_idea_text):
    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    result = plan_run(intent_id, paths=tmp_foundry)

    index = Registry.open(RUN_INDEX, paths=tmp_foundry)
    row = index.get(result.run_id)
    assert row is not None
    assert row["intent_id"] == intent_id
    assert row["status"] == "planned"
    assert row["brief_id"] == result.brief_id
