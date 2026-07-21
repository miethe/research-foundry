"""Tests for the external-tool adapters (contract §11, spec §13).

These prove the deterministic default path: in this environment none of the
optional dependencies (``claude_agent_sdk``, ``gpt_researcher``, ``paperqa``,
``litellm``) are installed and ``opencode`` is not on PATH, so every adapter
must report ``available() is False`` and return an ``AdapterResult(degraded=True)``
from ``run`` without raising or hitting the network.
"""

from __future__ import annotations

import pytest

from research_foundry import adapters
from research_foundry.adapters import AdapterResult, get_adapter, load_all
from research_foundry.adapters.litellm_router import LiteLLMRouterAdapter

_EXPECTED_IDS = {
    "claude_agent_sdk",
    "gpt_researcher",
    "paperqa2",
    "opencode",
    "litellm_router",
}


def test_load_all_registers_all_five_by_id():
    registry = load_all()
    assert _EXPECTED_IDS <= set(registry)
    for adapter_id in _EXPECTED_IDS:
        assert registry[adapter_id].id == adapter_id
        assert get_adapter(adapter_id) is registry[adapter_id]


@pytest.mark.parametrize("adapter_id", sorted(_EXPECTED_IDS))
def test_each_adapter_unavailable_and_degrades(adapter_id):
    load_all()
    adapter = get_adapter(adapter_id)
    assert adapter is not None
    # Optional deps absent + no opencode binary -> not available in this env.
    assert adapter.available() is False
    result = adapter.run({})
    assert isinstance(result, AdapterResult)
    assert result.degraded is True
    assert result.adapter == adapter_id
    # Degraded results must explain themselves and never raise.
    assert result.notes


def test_gpt_researcher_turns_questions_into_labeled_candidates():
    load_all()
    adapter = get_adapter("gpt_researcher")
    request = {
        "brief": {
            "questions": {
                "primary": [
                    {"id": "q1", "question": "How do evidence bundles preserve traceability?"},
                    {"id": "q2", "question": "What model tiers fit cheap extraction?"},
                ],
                "secondary": [
                    {"id": "q3", "question": "Where do contradictions get logged?"},
                ],
            }
        }
    }
    result = adapter.run(request)
    assert result.degraded is True
    assert len(result.source_candidates) == 3
    labels = [c["label"] for c in result.source_candidates]
    assert labels == ["unverified_candidate_1", "unverified_candidate_2", "unverified_candidate_3"]
    # Each candidate is tied back to its originating question and is offline-only.
    qids = {c["discovered_for_question"] for c in result.source_candidates}
    assert qids == {"q1", "q2", "q3"}
    for cand in result.source_candidates:
        assert cand["discovery_method"] == "degraded_stub"
        assert cand["locator"]["url"] is None  # no network performed


def test_gpt_researcher_accepts_bare_question_list():
    load_all()
    adapter = get_adapter("gpt_researcher")
    result = adapter.run({"research_questions": ["What is X?", "Why Y?"]})
    assert result.degraded is True
    assert len(result.source_candidates) == 2


def test_gpt_researcher_empty_request_returns_empty_candidates():
    load_all()
    adapter = get_adapter("gpt_researcher")
    result = adapter.run({})
    assert result.degraded is True
    assert result.source_candidates == []
    assert result.notes


def test_litellm_route_returns_preferred_entry(tmp_foundry):
    adapter = LiteLLMRouterAdapter()
    decision = adapter.route("rf_extract_cheap", paths=tmp_foundry, env={})
    # First preferred entry of rf_extract_cheap in config/model_profiles.yaml
    # (ICA free workhorse, OpenAI-compatible chat path — plain id, no [1m] suffix).
    assert decision["provider"] == "ica"
    assert decision["model"] == "claude-haiku-4-5"
    assert decision["api_base"] == "https://api.nextgen-beta.ica.ibm.com/ica/v1"
    assert decision["model_profile"] == "rf_extract_cheap"
    # env={} carries no RF_LLM_API_KEY, so the ica entry is not reachable → degraded fallback.
    assert decision["degraded"] is True
    assert decision["reason"] == "preferred_fallback"
    assert decision["tier"] == "cheap"


def test_litellm_route_unknown_profile(tmp_foundry):
    adapter = LiteLLMRouterAdapter()
    decision = adapter.route("does_not_exist", paths=tmp_foundry, env={})
    assert decision["provider"] is None
    assert decision["degraded"] is True
    assert decision["reason"] == "unknown_profile"


def test_litellm_run_uses_default_profile(tmp_foundry):
    load_all()
    adapter = get_adapter("litellm_router")
    result = adapter.run({"model_profile": "rf_extract_cheap", "paths": tmp_foundry})
    assert isinstance(result, AdapterResult)
    assert result.degraded is True
    assert "routing_decision" in result.artifacts


def test_paperqa_lists_local_pdfs(tmp_foundry, tmp_path):
    load_all()
    adapter = get_adapter("paperqa2")
    pdf_dir = tmp_path / "papers"
    pdf_dir.mkdir()
    (pdf_dir / "alpha.pdf").write_bytes(b"%PDF-1.4 stub")
    (pdf_dir / "beta.pdf").write_bytes(b"%PDF-1.4 stub")
    result = adapter.run({"local_pdf_dir": str(pdf_dir)})
    assert result.degraded is True
    titles = sorted(c["title"] for c in result.source_candidates)
    assert titles == ["alpha", "beta"]
    for cand in result.source_candidates:
        assert cand["source_type"] == "paper"
        assert cand["locator"]["file_path"]


def test_opencode_degrades_with_note(tmp_foundry):
    load_all()
    adapter = get_adapter("opencode")
    result = adapter.run({"repo_path": "/tmp/repo"})
    assert result.degraded is True
    assert any("opencode" in n for n in result.notes)
    # No code agent run -> no candidates, no artifacts.
    assert result.source_candidates == []


def test_adapter_module_namespace_exports():
    # Sanity: the package-level re-exports used by the CLI are present.
    assert hasattr(adapters, "load_all")
    assert hasattr(adapters, "get_adapter")
    assert hasattr(adapters, "all_adapters")
