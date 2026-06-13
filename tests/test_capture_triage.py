"""Tests for the capture/triage service (contract §1).

Proves:
- ``capture_idea`` writes a schema-valid ``raw_idea``.
- ``triage_idea`` produces three linked, schema-valid artifacts.
- The links are bidirectional (intent.ibom_ref==ibom.id, etc.).
- The raw idea's triage block flips to ``converted_to_intent`` with the intent id.
- A ``work_sensitive`` idea yields the governance posture the contract requires.
"""

from __future__ import annotations

import pytest

from research_foundry.errors import NotFoundError, SchemaError
from research_foundry.frontmatter import load_md
from research_foundry.schemas import default_registry, validate
from research_foundry.services.capture import (
    CaptureResult,
    TriageResult,
    capture_idea,
    load_intent,
    triage_idea,
)
from research_foundry.yamlio import load_yaml

# --- capture ---------------------------------------------------------------


def test_capture_writes_valid_raw_idea(tmp_foundry, sample_idea_text):
    result = capture_idea(sample_idea_text, paths=tmp_foundry)

    assert isinstance(result, CaptureResult)
    assert result.raw_idea_id.startswith("raw_")
    assert result.path.exists()
    assert result.path == tmp_foundry.raw_ideas / f"{result.raw_idea_id}.md"

    # Front-matter fields are stored at the TOP LEVEL (no wrapper key).
    meta, body = load_md(result.path)
    assert meta["id"] == result.raw_idea_id
    assert meta["body"] == sample_idea_text
    assert meta["captured_from"] == "manual"
    assert meta["sensitivity"] == "personal"
    assert meta["triage"] == {"status": "untriaged", "intent_id": None}
    assert sample_idea_text in body

    # Schema-valid against the canonical raw_idea schema.
    res = validate(meta, "raw_idea")
    assert res.ok, res.errors


def test_capture_defaults_title_from_text(tmp_foundry):
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    result = capture_idea(text, paths=tmp_foundry)
    # Title is the first ~8 words.
    assert result.data["title"] == "alpha beta gamma delta epsilon zeta eta theta"


def test_capture_explicit_overrides(tmp_foundry):
    result = capture_idea(
        "some body",
        title="My Title",
        captured_from="note",
        sensitivity="public",
        urgency="high",
        tags=["a", "b"],
        research_potential="high",
        paths=tmp_foundry,
    )
    assert result.data["title"] == "My Title"
    assert result.data["captured_from"] == "note"
    assert result.data["sensitivity"] == "public"
    assert result.data["urgency"] == "high"
    assert result.data["tags"] == ["a", "b"]
    assert result.data["research_potential"] == "high"
    assert validate(result.data, "raw_idea").ok


# --- triage ----------------------------------------------------------------


def test_triage_produces_three_linked_valid_artifacts(tmp_foundry, sample_idea_text):
    captured = capture_idea(sample_idea_text, paths=tmp_foundry)
    triaged = triage_idea(captured.path, paths=tmp_foundry)

    assert isinstance(triaged, TriageResult)
    assert triaged.intent_id and triaged.ibom_id and triaged.node_id
    assert triaged.intent_path and triaged.ibom_path and triaged.node_path
    assert triaged.intent_path.exists()
    assert triaged.ibom_path.exists()
    assert triaged.node_path.exists()

    intent = load_yaml(triaged.intent_path)
    ibom = load_yaml(triaged.ibom_path)
    node = load_yaml(triaged.node_path)

    # Each artifact is schema-valid.
    assert validate(intent, "research_intent").ok, validate(intent, "research_intent").errors
    assert validate(ibom, "ibom").ok, validate(ibom, "ibom").errors
    assert validate(node, "intenttree_node").ok, validate(node, "intenttree_node").errors

    # Cross-links are exactly as the contract requires.
    assert intent["ibom_ref"] == ibom["id"]
    assert intent["intenttree_node_ref"] == node["node_id"]
    assert node["intent_id"] == intent["id"]
    assert ibom["intent_id"] == intent["id"]

    # ibom + node defaults from spec §6.4 / §6.5.
    assert ibom["model_policy"] == {
        "extraction_profile": "rf_extract_cheap",
        "synthesis_profile": "rf_synthesize_deep",
        "verification_profile": "rf_verify_balanced",
    }
    assert "claude_code" in ibom["tools_available"]
    assert ibom["security_boundaries"]
    assert node["level"] == "L4"
    assert node["parent"] == "tree_research_foundry"
    assert node["status"] == "ready"
    assert node["required_agent_postures"] == ["researcher", "critic", "synthesizer"]
    assert node["expected_artifacts"] == [
        "evidence_bundle",
        "report",
        "meatywiki_writeback",
        "ccdash_event",
    ]


def test_triage_marks_raw_idea_converted(tmp_foundry, sample_idea_text):
    captured = capture_idea(sample_idea_text, paths=tmp_foundry)
    triaged = triage_idea(captured.path, paths=tmp_foundry)

    meta, _ = load_md(captured.path)
    assert meta["triage"]["status"] == "converted_to_intent"
    assert meta["triage"]["intent_id"] == triaged.intent_id
    # Still schema-valid after the update.
    assert validate(meta, "raw_idea").ok


def test_triage_personal_idea_governance(tmp_foundry, sample_idea_text):
    captured = capture_idea(sample_idea_text, sensitivity="personal", paths=tmp_foundry)
    triaged = triage_idea(captured.path, paths=tmp_foundry)
    intent = load_yaml(triaged.intent_path)

    gov = intent["governance"]
    assert gov["sensitivity"] == "personal"
    assert gov["key_profile_allowed"] == "personal"
    assert gov["requires_human_review"] is False
    assert "meatywiki_personal" in gov["allowed_writebacks"]


def test_triage_work_sensitive_governance(tmp_foundry):
    captured = capture_idea(
        "Evaluate an internal vendor risk model for client onboarding.",
        sensitivity="work_sensitive",
        paths=tmp_foundry,
    )
    triaged = triage_idea(captured.path, paths=tmp_foundry)
    intent = load_yaml(triaged.intent_path)

    gov = intent["governance"]
    assert gov["requires_human_review"] is True
    assert gov["key_profile_allowed"] == "work_approved"
    assert validate(intent, "research_intent").ok


def test_triage_by_raw_idea_id(tmp_foundry, sample_idea_text):
    captured = capture_idea(sample_idea_text, paths=tmp_foundry)
    # Pass the raw_idea_id instead of a path.
    triaged = triage_idea(captured.raw_idea_id, paths=tmp_foundry)
    assert triaged.raw_idea_id == captured.raw_idea_id
    assert triaged.intent_path and triaged.intent_path.exists()


def test_triage_research_questions_seeded(tmp_foundry):
    captured = capture_idea("How do agents trace claims?", paths=tmp_foundry)
    triaged = triage_idea(captured.path, paths=tmp_foundry)
    intent = load_yaml(triaged.intent_path)
    primary = intent["research_questions"]["primary"]
    assert isinstance(primary, list) and len(primary) >= 1


def test_triage_skip_ibom_and_node(tmp_foundry, sample_idea_text):
    captured = capture_idea(sample_idea_text, paths=tmp_foundry)
    triaged = triage_idea(
        captured.path, create_ibom=False, create_tree_node=False, paths=tmp_foundry
    )
    assert triaged.intent_id is not None
    assert triaged.ibom_id is None
    assert triaged.node_id is None
    intent = load_yaml(triaged.intent_path)
    assert "ibom_ref" not in intent
    assert "intenttree_node_ref" not in intent
    assert validate(intent, "research_intent").ok


def test_triage_missing_raw_idea_raises(tmp_foundry):
    with pytest.raises(NotFoundError):
        triage_idea("raw_does_not_exist", paths=tmp_foundry)


# --- load_intent -----------------------------------------------------------


def test_load_intent_roundtrip(tmp_foundry, sample_idea_text):
    captured = capture_idea(sample_idea_text, paths=tmp_foundry)
    triaged = triage_idea(captured.path, paths=tmp_foundry)
    loaded = load_intent(triaged.intent_id, paths=tmp_foundry)
    assert loaded["id"] == triaged.intent_id


def test_load_intent_missing_raises(tmp_foundry):
    with pytest.raises(NotFoundError):
        load_intent("intent_research_nope", paths=tmp_foundry)


# --- schema availability sanity -------------------------------------------


def test_required_schemas_present():
    reg = default_registry()
    for name in ("raw_idea", "research_intent", "ibom", "intenttree_node"):
        assert reg.has(name), f"missing schema {name}"


def test_schema_error_is_raised_on_invalid(monkeypatch, tmp_foundry):
    # Force an invalid raw_idea by patching the builder via a bad sensitivity enum.
    from research_foundry.services import capture as cap

    def _bad_render(text, title):  # noqa: ANN001
        return "body"

    monkeypatch.setattr(cap, "_render_body", _bad_render)
    # Invalid enum value should trip schema validation (additionalProperties true,
    # but enum mismatch is reported).
    with pytest.raises(SchemaError):
        capture_idea("x", sensitivity="not_a_valid_enum", paths=tmp_foundry)
