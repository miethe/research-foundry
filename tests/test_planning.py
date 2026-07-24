"""Tests for the planning service (``rf plan``).

Each test builds a real intent + I-BOM via the capture/triage service, then
plans a run and asserts the four run artifacts are written, schema-valid, and
that the routing decision's ``human_required`` flag reflects the intent's
``governance.requires_human_review``.
"""

from __future__ import annotations

import pytest

from research_foundry.errors import SchemaError
from research_foundry.frontmatter import load_md
from research_foundry.registry import RUN_INDEX, Registry
from research_foundry.schemas import default_registry, validate
from research_foundry.services import planning as planning_module
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


def test_disambiguated_run_ids_leave_no_empty_stub_dir(tmp_foundry):
    """AAR gap 3 (real-run path): two intents whose titles share the same
    first-6-word slug must mint two distinct, fully-populated run
    directories -- never an empty/un-suffixed stub left over from a
    directory created before the final (possibly-suffixed) run_id was
    resolved.
    """

    same_title = "Same Title For Both Ideas Here"
    intent_id_1, _ = _make_intent(same_title, sensitivity="personal", tmp_foundry=tmp_foundry)
    intent_id_2, _ = _make_intent(same_title, sensitivity="personal", tmp_foundry=tmp_foundry)
    assert intent_id_1 != intent_id_2  # triage_idea already disambiguates intents

    result1 = plan_run(intent_id_1, paths=tmp_foundry)
    result2 = plan_run(intent_id_2, paths=tmp_foundry)

    assert result1.run_id != result2.run_id
    # Second run collides on the base slug -> disambiguate_id suffixes it.
    assert result2.run_id.startswith(result1.run_id + "_")

    for result in (result1, result2):
        assert result.run_dir.is_dir()
        assert (result.run_dir / "run.yaml").exists()
        assert any(result.run_dir.iterdir())  # never an empty stub

    # runs/ contains exactly the two real, suffix-correct directories -- no
    # stray un-suffixed empty directory sitting alongside them.
    assert {p.name for p in tmp_foundry.runs.iterdir()} == {result1.run_id, result2.run_id}


def test_plan_run_gcs_partial_scaffold_on_failure(tmp_foundry, sample_idea_text, monkeypatch):
    """AAR gap 3 (partial-failure path): a failure between ``ensure_scaffold()``
    and the registry write (schema error, governance block, I/O error, ...)
    must not leave an orphaned run directory -- not even a partially
    populated one missing ``run.yaml`` -- for the runs-viewer to surface as
    a blank entry.
    """

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)

    real_validate_or_raise = planning_module._validate_or_raise

    def _boom(obj, schema_name, path):
        # Let research_brief validate fine (so the run dir has real partial
        # content, mirroring a genuine mid-scaffold failure), then explode on
        # the next artifact.
        if schema_name == "swarm_plan":
            raise SchemaError("injected failure for test_plan_run_gcs_partial_scaffold_on_failure")
        return real_validate_or_raise(obj, schema_name, path)

    monkeypatch.setattr(planning_module, "_validate_or_raise", _boom)

    runs_dir = tmp_foundry.runs
    before = {p.name for p in runs_dir.iterdir()} if runs_dir.exists() else set()

    with pytest.raises(SchemaError):
        planning_module.plan_run(intent_id, paths=tmp_foundry)

    after = {p.name for p in runs_dir.iterdir()} if runs_dir.exists() else set()
    # The scaffolded run dir (which had research_brief.md written, but never
    # got run.yaml or a registry entry) was GC'd -- no orphan left behind.
    assert after == before


# ---------------------------------------------------------------------------
# P4 fix-cycle: _lexical_terms unit coverage (stopword filtering, no cap)
# ---------------------------------------------------------------------------


def test_lexical_terms_filters_stopwords_short_tokens_and_dedupes_in_order():
    text = "What does the evidence say about renewable energy and renewable grid storage economics?"
    terms = planning_module._lexical_terms(text)
    # No function words/boilerplate ("what", "does", "the", "say", "about",
    # "evidence", "and") -- only the real topical, deduped, first-occurrence
    # ordered content terms survive.
    assert terms == ("renewable", "energy", "grid", "storage", "economics")


def test_lexical_terms_drops_two_char_tokens_even_if_not_a_stopword():
    assert planning_module._lexical_terms("an ox by a dam") == ("dam",)


def test_lexical_terms_is_never_truncated_for_a_nine_content_term_question():
    """The old ``_MAX_LEXICAL_TERMS`` cap silently dropped any term beyond
    the 5th -- this is the regression guard that it is gone for good."""

    text = "alpha bravo charlie delta echo foxtrot golf hotel india"
    terms = planning_module._lexical_terms(text)
    assert terms == ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india")
    assert len(terms) == 9


def test_lexical_terms_is_deterministic_across_repeated_calls():
    text = "Zebra yak xylophone whale zebra yak vulture umbrella tiger"
    first = planning_module._lexical_terms(text)
    second = planning_module._lexical_terms(text)
    assert first == second
    assert first == ("zebra", "yak", "xylophone", "whale", "vulture", "umbrella", "tiger")


# ---------------------------------------------------------------------------
# P6 CARP-6.9 F1 fix-cycle: vacuous required_terms fail-open guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "What is the evidence for and against this?",
            ("what", "the", "evidence", "for", "and", "against", "this"),
        ),
        ("How do they do it?", ("how", "they")),
    ],
)
def test_lexical_terms_falls_back_to_unfiltered_tokens_when_stopwords_empty_the_result(
    text, expected
):
    """A question whose every 3+-char token is a stopword must never derive
    ``()`` -- catalog_retrieval.retrieve()'s condition-1 lexical-match check
    treats an empty ``required_terms`` as vacuously true (every authorized
    candidate matches), so an empty derivation here would silently flip a
    real, worded question into "match anything"."""

    terms = planning_module._lexical_terms(text)
    assert terms != ()
    assert terms == expected


def test_lexical_terms_genuinely_contentless_text_still_yields_empty_but_is_guarded():
    """Text with no token reaching the 3-char floor (e.g. all 1-2 char
    tokens) has no fallback to offer either -- ``_lexical_terms`` returning
    ``()`` here is a true, correct reflection of "no derivable terms", not a
    stopword-filtering artifact.

    P6 CARP-6.9 F4 fix-cycle: an earlier version of this test stopped there
    and called that safe. It is NOT safe on its own -- ``()`` is exactly the
    shape ``catalog_retrieval.retrieve()``'s condition 1 treats as vacuously
    true for every authorized candidate, which would let an arbitrary,
    unrelated catalog assertion resolve ``covered`` for a question that said
    nothing derivable. ``_evidence_plan_question`` -- the actual
    plan-construction boundary -- must catch this and mark the question
    terminal ``residual``/``evaluation_error`` instead, so ``build_evidence_plan``
    never calls ``retrieve()`` for it at all."""

    assert planning_module._lexical_terms("is it up?") == ()

    question = planning_module._evidence_plan_question("q1", "is it up?")
    assert question.required_terms == ()
    assert question.forced_residual_reason == "evaluation_error"


def test_lexical_terms_fallback_does_not_engage_when_content_terms_survive():
    """The fallback only fires when stopword filtering would empty an
    otherwise non-empty stream -- a question with at least one real content
    term keeps the normal stopword-filtered (not fallback) behavior."""

    text = "What does the evidence say about renewable energy?"
    terms = planning_module._lexical_terms(text)
    assert terms == ("renewable", "energy")


# ---------------------------------------------------------------------------
# P6 CARP-6.9 F3: "evidence" as a global stopword -- accepted tradeoff,
# recorded explicitly (not left silent) rather than fixed.
#
# The module docstring above _STOPWORDS already documents WHY "evidence" is
# blacklisted: it is this module's own default-fallback-question template's
# scaffolding vocabulary (f"What does the evidence say about {objective}?").
# The alternative -- stripping that one template's scaffolding at
# construction time instead of blacklisting a topical word globally -- was
# considered and rejected for P6: it would require a second, template-aware
# term-derivation path solely for the auto-generated fallback question
# (every other call site derives required_terms from arbitrary caller/user
# text, where "the template" does not apply), adding a special case to a
# frozen-contract-adjacent surface for a narrow benefit. The accepted
# consequence, demonstrated below, is that "evidence" is dropped from
# required_terms even when a caller's OWN question uses it as a genuine
# topical word -- but only when other content words survive alongside it;
# when "evidence" is the question's only survivor, F1's fallback (above)
# already restores it. This is the loud, tested version of "acceptable,
# not silent."
# ---------------------------------------------------------------------------


def test_evidence_stopword_is_dropped_even_as_a_genuine_topical_word():
    """Accepted P6 tradeoff: a real question using "evidence" as content
    (not template scaffolding) still loses it, because _STOPWORDS is global
    and cannot distinguish the two uses. Other real content terms in the
    same question are unaffected."""

    text = "What does chain of custody evidence review require for admissibility?"
    terms = planning_module._lexical_terms(text)
    assert "evidence" not in terms
    assert terms == ("chain", "custody", "review", "require", "admissibility")


def test_evidence_stopword_does_not_survive_alone_but_f1_fallback_still_rescues_it():
    """The narrower case F1 already covers, restated here to make the
    F3/F1 interaction explicit: when "evidence" is the ONLY surviving token,
    the F1 fallback (unfiltered token set) restores it rather than yielding
    ``()`` -- the two fixes compose, they do not fight each other."""

    text = "What is the evidence?"
    terms = planning_module._lexical_terms(text)
    assert terms != ()
    assert "evidence" in terms
