"""Tests for adapters/notebooklm.py (NotebookLMAdapter).

Covers:
- available() returns False when 'notebooklm' binary not on PATH
- available() returns True when binary is found
- run() returns degraded AdapterResult when available() is False
- run() degraded result has correct adapter id, notes, and no subprocess calls
- run() produces one stub candidate per question in degraded mode
- run() with no questions in request returns empty candidate list (not degraded)
- source_candidate field keys mirror GPTResearcherAdapter exactly
- NotebookLMAdapter is registered in the adapters registry (load_all / get_adapter)
- _degraded returns deterministic stub candidates (no randomness)
"""

from __future__ import annotations

from unittest.mock import patch

from research_foundry.adapters import get_adapter, load_all
from research_foundry.adapters.base import AdapterResult
from research_foundry.adapters.notebooklm import NotebookLMAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _adapter() -> NotebookLMAdapter:
    return NotebookLMAdapter()


_QUESTIONS_REQUEST = {
    "brief": {
        "project": "test-project",
        "questions": {
            "primary": [
                {"id": "q1", "question": "What is the minimum viable architecture?"},
                {"id": "q2", "question": "How should evidence bundles be structured?"},
            ]
        },
    },
    "run_id": "rf_run_20260613_test",
}


# ---------------------------------------------------------------------------
# available()
# ---------------------------------------------------------------------------


class TestNotebookLMAdapterAvailable:
    def test_false_when_binary_not_on_path(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            assert adapter.available() is False

    def test_true_when_binary_found(self):
        adapter = _adapter()
        with patch("shutil.which", return_value="/usr/local/bin/notebooklm"):
            assert adapter.available() is True

    def test_available_checks_correct_binary_name(self):
        adapter = _adapter()
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            adapter.available()
        mock_which.assert_called_once_with("notebooklm")


# ---------------------------------------------------------------------------
# run() — degraded path (binary absent)
# ---------------------------------------------------------------------------


class TestNotebookLMAdapterRunDegraded:
    def test_returns_adapter_result_when_unavailable(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        assert isinstance(result, AdapterResult)

    def test_degraded_true_when_binary_absent(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        assert result.degraded is True

    def test_adapter_id_correct(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        assert result.adapter == "notebooklm"

    def test_notes_mention_unavailability(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        combined = " ".join(result.notes).lower()
        assert "unavailable" in combined or "not on path" in combined or "path" in combined

    def test_no_subprocess_calls_in_degraded_mode(self):
        adapter = _adapter()
        with (
            patch("shutil.which", return_value=None),
            patch("subprocess.run") as mock_sub,
        ):
            adapter.run(_QUESTIONS_REQUEST)
        mock_sub.assert_not_called()

    def test_produces_one_stub_candidate_per_question(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        # Two questions in _QUESTIONS_REQUEST.
        assert len(result.source_candidates) == 2

    def test_stub_candidates_have_correct_source_type(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        for cand in result.source_candidates:
            assert cand["source_type"] == "notebooklm"

    def test_stub_candidates_have_discovery_method(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        for cand in result.source_candidates:
            assert cand["discovery_method"] == "notebooklm_synthesis"

    def test_stub_candidates_have_all_required_locator_keys(self):
        """Locator keys mirror GPTResearcherAdapter exactly."""
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        required_locator_keys = {"url", "file_path", "doi", "repo", "notebook_id", "nlm_source_id"}
        for cand in result.source_candidates:
            assert "locator" in cand
            assert required_locator_keys.issubset(set(cand["locator"].keys()))

    def test_stub_candidates_have_required_candidate_fields(self):
        """candidate_id, title, source_type, locator, discovered_for_question, discovery_method."""
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run(_QUESTIONS_REQUEST)
        required_keys = {
            "candidate_id",
            "title",
            "source_type",
            "locator",
            "discovered_for_question",
            "discovery_method",
        }
        for cand in result.source_candidates:
            assert required_keys.issubset(set(cand.keys()))

    def test_empty_request_returns_empty_candidates(self):
        """No questions in request → empty candidate list."""
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run({})
        assert result.source_candidates == []

    def test_degraded_with_no_questions_still_returns_adapter_result(self):
        adapter = _adapter()
        with patch("shutil.which", return_value=None):
            result = adapter.run({})
        assert isinstance(result, AdapterResult)
        assert result.degraded is True


# ---------------------------------------------------------------------------
# run() — degrade on notebook resolution failure
# ---------------------------------------------------------------------------


class TestNotebookLMAdapterRunNotebookResolutionFailed:
    def test_degrades_when_notebook_resolution_returns_none(self):
        """Binary present but notebook_correlation.resolve_notebook returns None → degraded."""
        adapter = _adapter()
        with (
            patch("shutil.which", return_value="/usr/local/bin/notebooklm"),
            patch(
                "research_foundry.adapters.notebooklm.NotebookLMAdapter._resolve_notebook",
                return_value=None,
            ),
        ):
            result = adapter.run(_QUESTIONS_REQUEST)
        assert result.degraded is True

    def test_note_mentions_notebook_resolution_failure(self):
        adapter = _adapter()
        with (
            patch("shutil.which", return_value="/usr/local/bin/notebooklm"),
            patch(
                "research_foundry.adapters.notebooklm.NotebookLMAdapter._resolve_notebook",
                return_value=None,
            ),
        ):
            result = adapter.run(_QUESTIONS_REQUEST)
        combined = " ".join(result.notes).lower()
        assert "notebook" in combined


# ---------------------------------------------------------------------------
# run() — empty questions when binary IS available
# ---------------------------------------------------------------------------


class TestNotebookLMAdapterRunEmptyQuestions:
    def test_no_questions_returns_not_degraded_empty_candidates(self):
        """Binary present + no questions → not degraded, empty candidates."""
        adapter = _adapter()
        with (
            patch("shutil.which", return_value="/usr/local/bin/notebooklm"),
            patch(
                "research_foundry.adapters.notebooklm.NotebookLMAdapter._resolve_notebook",
                return_value="nb_001",
            ),
        ):
            result = adapter.run({"run_id": "run_x", "brief": {"questions": {}}})
        assert result.degraded is False
        assert result.source_candidates == []


# ---------------------------------------------------------------------------
# Determinism: _degraded produces stable output
# ---------------------------------------------------------------------------


class TestDegradedDeterminism:
    def test_same_input_produces_same_output(self):
        adapter = _adapter()
        request = {
            "brief": {
                "questions": {
                    "primary": [{"id": "q1", "question": "What is evidence?"}]
                }
            }
        }
        with patch("shutil.which", return_value=None):
            r1 = adapter.run(request)
            r2 = adapter.run(request)
        assert r1.source_candidates[0]["candidate_id"] == r2.source_candidates[0]["candidate_id"]
        assert r1.notes == r2.notes

    def test_different_questions_produce_different_candidate_ids(self):
        adapter = _adapter()
        req1 = {"brief": {"questions": {"primary": [{"id": "q1", "question": "Alpha question"}]}}}
        req2 = {"brief": {"questions": {"primary": [{"id": "q1", "question": "Beta question"}]}}}
        with patch("shutil.which", return_value=None):
            r1 = adapter.run(req1)
            r2 = adapter.run(req2)
        assert r1.source_candidates[0]["candidate_id"] != r2.source_candidates[0]["candidate_id"]


# ---------------------------------------------------------------------------
# Adapter registration
# ---------------------------------------------------------------------------


class TestNotebookLMAdapterRegistration:
    def test_registered_in_adapters_registry(self):
        adapters = load_all()
        assert "notebooklm" in adapters

    def test_get_adapter_returns_notebooklm_adapter(self):
        load_all()  # ensure registered
        adapter = get_adapter("notebooklm")
        assert adapter is not None
        assert isinstance(adapter, NotebookLMAdapter)

    def test_adapter_id_attribute(self):
        assert NotebookLMAdapter.id == "notebooklm"

    def test_adapter_requires_is_empty_tuple(self):
        """NotebookLM availability is CLI-detected, not Python module import."""
        adapter = NotebookLMAdapter()
        assert adapter.requires == ()


# ---------------------------------------------------------------------------
# _degraded helper directly
# ---------------------------------------------------------------------------


class TestDegradedHelper:
    def test_returns_adapter_result(self):
        adapter = _adapter()
        result = adapter._degraded({})
        assert isinstance(result, AdapterResult)
        assert result.degraded is True
        assert result.adapter == "notebooklm"

    def test_note_passed_through(self):
        adapter = _adapter()
        result = adapter._degraded({}, note="custom reason for degradation")
        assert any("custom reason for degradation" in n for n in result.notes)

    def test_produces_stub_for_bare_questions_list(self):
        """Accepts bare research_questions list of strings."""
        adapter = _adapter()
        request = {
            "research_questions": ["What is X?", "What is Y?"],
        }
        result = adapter._degraded(request)
        assert len(result.source_candidates) == 2
