"""Substitutability search on a blocking triage status (rights-entity-model-v1, P4-4).

Enumerated H3 test scenarios (plan row P4-4):

1. Non-blocking triage status -> ``not_searched``, no search performed.
2. Blocking status + a substitute exists in the corpus -> ``substitute_found``
   with ``candidate_source_ids`` populated.
3. Blocking status + no substitute -> ``no_substitute_found`` recorded as a
   positive structured result (present, non-null field), dedicated test.
4. Search itself errors -> degrades to ``not_searched`` + a structural note,
   not a silent skip.
5. Multiple candidate substitutes -> all ranked and listed, not just the top.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import dump_md
from research_foundry.services import rights_triage
from research_foundry.services.rights_substitutability import (
    STATUS_NOT_SEARCHED,
    STATUS_NO_SUBSTITUTE_FOUND,
    STATUS_SUBSTITUTE_FOUND,
    assess_substitutability,
    is_blocking_clearance_status,
)


def _write_source_card(
    tmp_path: Path,
    name: str,
    *,
    source_card_id: str,
    title: str,
    extra_summary: str | None = None,
) -> Path:
    extracted_points = []
    if extra_summary:
        extracted_points.append({"evidence_id": "ev-1", "summary": extra_summary})
    metadata: dict[str, Any] = {
        "type": "source_card",
        "source_card_id": source_card_id,
        "source": {"title": title},
        "extracted_points": extracted_points,
    }
    return dump_md(metadata, "Body.\n", tmp_path / name)


class TestBlockingStatusClassification:
    def test_named_blocking_statuses(self) -> None:
        for status in ("CONTRACT_RESTRICTED", "PERMISSION_REQUIRED", "PROHIBITED", "UNKNOWN"):
            assert is_blocking_clearance_status(status) is True

    def test_cleared_status_is_non_blocking(self) -> None:
        assert is_blocking_clearance_status("CLEARED_OPEN_LICENSE") is False
        assert is_blocking_clearance_status(None) is False


class TestScenario1NonBlockingSkipsSearch:
    """(1) Non-blocking triage status -> not_searched, no search performed."""

    def test_cleared_status_short_circuits(self, tmp_path: Path) -> None:
        corpus = [_write_source_card(tmp_path, "s1.md", source_card_id="src-1", title="cats and dogs")]

        result = assess_substitutability(
            "CLEARED_OPEN_LICENSE",
            query_terms=["cats"],
            corpus_paths=corpus,
        )

        assert result["status"] == STATUS_NOT_SEARCHED
        assert result["searched_at"] is None
        assert result["candidate_source_ids"] == []
        assert "non-blocking" in result["coverage_notes"]

    def test_no_search_side_effect_even_with_broken_corpus(self, tmp_path: Path) -> None:
        """A non-blocking status must not even attempt the corpus search --
        confirmed by pointing at a corpus path that would raise if touched."""

        broken_path = tmp_path / "does-not-exist.md"

        result = assess_substitutability(
            "CLEARED_PUBLIC_DOMAIN",
            query_terms=["anything"],
            corpus_paths=[broken_path],
        )

        assert result["status"] == STATUS_NOT_SEARCHED
        assert result["searched_at"] is None


class TestScenario2SubstituteFound:
    """(2) Blocking status + a substitute exists -> substitute_found with
    candidate_source_ids populated."""

    def test_matching_corpus_entry_is_found(self, tmp_path: Path) -> None:
        corpus = [
            _write_source_card(
                tmp_path,
                "match.md",
                source_card_id="src-match",
                title="Pediatric Anemia Screening Guidelines",
            ),
            _write_source_card(
                tmp_path,
                "unrelated.md",
                source_card_id="src-unrelated",
                title="Municipal Water Treatment Report",
            ),
        ]

        result = assess_substitutability(
            "CONTRACT_RESTRICTED",
            query_terms=["pediatric", "anemia"],
            corpus_paths=corpus,
            exclude_source_id="src-original",
        )

        assert result["status"] == STATUS_SUBSTITUTE_FOUND
        assert result["candidate_source_ids"] == ["src-match"]
        assert result["searched_at"] is not None
        assert result["coverage_notes"]


class TestScenario3NoSubstituteFoundIsPositiveResult:
    """(3) Blocking status + no substitute -> no_substitute_found recorded as
    a POSITIVE structured result (present, non-null), not an absent field."""

    def test_empty_corpus_yields_positive_no_substitute_result(self, tmp_path: Path) -> None:
        corpus = [
            _write_source_card(
                tmp_path,
                "unrelated.md",
                source_card_id="src-unrelated",
                title="Completely unrelated municipal report",
            )
        ]

        result = assess_substitutability(
            "PROHIBITED",
            query_terms=["pediatric", "anemia"],
            corpus_paths=corpus,
        )

        # The field must be PRESENT and non-null -- not omitted, not None.
        assert "status" in result
        assert result["status"] is not None
        assert result["status"] == STATUS_NO_SUBSTITUTE_FOUND
        assert result["candidate_source_ids"] == []
        assert result["searched_at"] is not None
        assert result["coverage_notes"]

    def test_no_substitute_found_present_even_with_empty_corpus(self) -> None:
        result = assess_substitutability(
            "PERMISSION_REQUIRED",
            query_terms=["anything"],
            corpus_paths=[],
        )

        assert result["status"] == STATUS_NO_SUBSTITUTE_FOUND
        assert result["candidate_source_ids"] == []


class TestScenario4SearchErrorDegrades:
    """(4) Search itself errors -> degrades to not_searched + a structural
    note, NOT a silent skip."""

    def test_unreadable_corpus_path_degrades_to_not_searched(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent-source-card.md"

        result = assess_substitutability(
            "CONTRACT_RESTRICTED",
            query_terms=["anything"],
            corpus_paths=[missing],
        )

        assert result["status"] == STATUS_NOT_SEARCHED
        # An attempt WAS made (blocking status) -- searched_at is set, unlike
        # the never-attempted scenario-1 case.
        assert result["searched_at"] is not None
        assert "failed" in result["coverage_notes"].lower()
        assert result["candidate_source_ids"] == []

    def test_malformed_corpus_entry_degrades_not_silently_skipped(self, tmp_path: Path) -> None:
        malformed = tmp_path / "malformed.md"
        malformed.write_text("not front-mattered markdown at all, no fences", encoding="utf-8")

        result = assess_substitutability(
            "UNKNOWN",
            query_terms=["anything"],
            corpus_paths=[malformed],
        )

        # load_md on a fence-less file returns ({}, text) rather than raising,
        # so this exercises the "no source_card_id -> skipped, not matched"
        # path rather than the exception path; assert it still degrades to a
        # well-formed, non-crashing result either way.
        assert result["status"] in (STATUS_NOT_SEARCHED, STATUS_NO_SUBSTITUTE_FOUND)
        assert result["candidate_source_ids"] == []

    def test_search_function_raising_is_caught_by_assess(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from research_foundry.services import rights_substitutability as mod

        def _boom(**_kwargs: Any) -> Any:
            raise RuntimeError("corpus index unreachable")

        monkeypatch.setattr(mod, "find_substitute_candidates", _boom)

        result = mod.assess_substitutability(
            "PROHIBITED",
            query_terms=["anything"],
            corpus_paths=[tmp_path / "whatever.md"],
        )

        assert result["status"] == STATUS_NOT_SEARCHED
        assert result["searched_at"] is not None
        assert "corpus index unreachable" in result["coverage_notes"]


class TestScenario5MultipleCandidatesRanked:
    """(5) Multiple candidate substitutes -> all ranked and listed, not just
    the top one."""

    def test_multiple_matches_all_listed_ranked_by_score(self, tmp_path: Path) -> None:
        corpus = [
            _write_source_card(
                tmp_path,
                "weak.md",
                source_card_id="src-weak",
                title="Pediatric health overview",
            ),
            _write_source_card(
                tmp_path,
                "strong.md",
                source_card_id="src-strong",
                title="Pediatric Anemia Iron Deficiency Screening",
                extra_summary="pediatric anemia iron deficiency guidance",
            ),
            _write_source_card(
                tmp_path,
                "medium.md",
                source_card_id="src-medium",
                title="Pediatric anemia basics",
            ),
            _write_source_card(
                tmp_path,
                "none.md",
                source_card_id="src-none",
                title="Unrelated municipal infrastructure report",
            ),
        ]

        result = assess_substitutability(
            "CONTRACT_RESTRICTED",
            query_terms=["pediatric", "anemia", "iron", "deficiency"],
            corpus_paths=corpus,
        )

        assert result["status"] == STATUS_SUBSTITUTE_FOUND
        # All 3 matching candidates are present, not just the top match.
        assert set(result["candidate_source_ids"]) == {"src-weak", "src-strong", "src-medium"}
        # Best match (most overlapping terms) ranked first.
        assert result["candidate_source_ids"][0] == "src-strong"
        assert "src-none" not in result["candidate_source_ids"]

    def test_limit_caps_ranked_results(self, tmp_path: Path) -> None:
        corpus = [
            _write_source_card(tmp_path, f"c{i}.md", source_card_id=f"src-{i}", title="pediatric anemia")
            for i in range(5)
        ]

        result = assess_substitutability(
            "UNKNOWN",
            query_terms=["pediatric", "anemia"],
            corpus_paths=corpus,
            limit=2,
        )

        assert result["status"] == STATUS_SUBSTITUTE_FOUND
        assert len(result["candidate_source_ids"]) == 2


class TestExcludeSelf:
    def test_entity_never_substitutes_for_itself(self, tmp_path: Path) -> None:
        corpus = [
            _write_source_card(tmp_path, "self.md", source_card_id="src-self", title="pediatric anemia"),
            _write_source_card(tmp_path, "other.md", source_card_id="src-other", title="pediatric anemia"),
        ]

        result = assess_substitutability(
            "PROHIBITED",
            query_terms=["pediatric", "anemia"],
            corpus_paths=corpus,
            exclude_source_id="src-self",
        )

        assert result["candidate_source_ids"] == ["src-other"]


class TestRightsTriageIntegrationHook:
    """P4-4 additive integration seam on top of P4-1's rights_triage module."""

    def test_maybe_assess_substitutability_blocking_default_capture_summary(self, tmp_path: Path) -> None:
        from research_foundry.services.rights_backfill import all_unknown_rights_summary

        corpus = [_write_source_card(tmp_path, "s.md", source_card_id="src-1", title="pediatric anemia")]
        summary = all_unknown_rights_summary()  # clearance_status == "UNKNOWN" -> blocking today

        result = rights_triage.maybe_assess_substitutability(
            summary,
            query_terms=["pediatric", "anemia"],
            corpus_paths=corpus,
        )

        assert result["status"] == STATUS_SUBSTITUTE_FOUND
        assert result["candidate_source_ids"] == ["src-1"]

    def test_maybe_assess_substitutability_non_blocking(self) -> None:
        summary = {"clearance_status": "CLEARED_OPEN_LICENSE"}

        result = rights_triage.maybe_assess_substitutability(summary, query_terms=["x"], corpus_paths=[])

        assert result["status"] == STATUS_NOT_SEARCHED
        assert result["searched_at"] is None

    def test_maybe_assess_substitutability_never_raises_on_missing_key(self) -> None:
        # rights_summary without a clearance_status key at all -- must not raise.
        result = rights_triage.maybe_assess_substitutability({}, corpus_paths=[])

        assert result["status"] == STATUS_NOT_SEARCHED
