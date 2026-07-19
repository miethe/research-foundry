"""Tests for TASK-4.1 — Council verdict normalization enum.

Covers:
- normalize_council_verdict(): recognized-approve variants -> approve/high
- normalize_council_verdict(): recognized-block variants -> block/high
- normalize_council_verdict(): ambiguous/garbage/empty/None -> concern/low
- ARCCouncilAdapter.run(): raw arc_verdict text is retained unchanged
  alongside the new normalized/confidence artifacts, in all cases.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from research_foundry.adapters.arc_council import (
    ARCCouncilAdapter,
    CouncilVerdict,
    normalize_council_verdict,
)


# ---------------------------------------------------------------------------
# normalize_council_verdict() — approve variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "approve",
        "approved",
        "APPROVE",
        "Approved",
        "approved with comments",
        "LGTM",
        "lgtm, ship it",
        "Approval granted",
        "no objection",
        "sign off",
        "signed off on this",
        "  approved.  ",
    ],
)
def test_recognized_approve_variants_map_to_approve_high(raw: str) -> None:
    verdict, confidence = normalize_council_verdict(raw)
    assert verdict is CouncilVerdict.approve
    assert confidence == "high"


# ---------------------------------------------------------------------------
# normalize_council_verdict() — block/reject variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "block",
        "blocked",
        "BLOCK",
        "Blocked pending fixes",
        "reject",
        "rejected",
        "rejection",
        "do not proceed",
        "must not proceed with this change",
        "veto",
        "vetoed",
        "denied",
        "deny",
    ],
)
def test_recognized_block_variants_map_to_block_high(raw: str) -> None:
    verdict, confidence = normalize_council_verdict(raw)
    assert verdict is CouncilVerdict.block
    assert confidence == "high"


# ---------------------------------------------------------------------------
# normalize_council_verdict() — ambiguous / garbage / empty / None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "pending",
        "unclear",
        "needs more discussion",
        "asdkjhasd garbage text 12345",
        "maybe, not sure yet",
        # Both approve and block signals present -> ambiguous, fail toward caution.
        "approved but blocking concerns remain",
    ],
)
def test_ambiguous_or_unparseable_maps_to_concern_low(raw: str | None) -> None:
    verdict, confidence = normalize_council_verdict(raw)
    assert verdict is CouncilVerdict.concern
    assert confidence == "low"


def test_council_verdict_enum_values() -> None:
    assert CouncilVerdict.approve.value == "approve"
    assert CouncilVerdict.concern.value == "concern"
    assert CouncilVerdict.block.value == "block"


# ---------------------------------------------------------------------------
# ARCCouncilAdapter.run() — raw text retained, normalized fields added
# ---------------------------------------------------------------------------


class TestAdapterVerdictNormalizationNonDestructive:
    """Adapter.run() must retain raw arc_verdict text unchanged in all cases."""

    def _run_with_verdict(self, raw_verdict: str | None):
        adapter = ARCCouncilAdapter()
        arc_response = {"run_id": "arc_run_norm_test"}
        run_record = {"run_id": "arc_run_norm_test", "verdict": raw_verdict}

        with (
            patch("research_foundry.integrations.arc.ArcClient.available", return_value=True),
            patch(
                "research_foundry.integrations.arc.ArcClient.scaffold_review",
                return_value=arc_response,
            ),
            patch("research_foundry.integrations.arc.ArcClient.get_run", return_value=run_record),
        ):
            return adapter.run({"objective": "test review", "council": "research-review-council"})

    def test_approve_raw_text_retained_and_normalized(self) -> None:
        result = self._run_with_verdict("approved with comments")
        assert result.artifacts.get("arc_verdict") == "approved with comments"
        assert result.artifacts.get("arc_verdict_normalized") == CouncilVerdict.approve.value
        assert result.artifacts.get("arc_verdict_normalization_confidence") == "high"

    def test_block_raw_text_retained_and_normalized(self) -> None:
        result = self._run_with_verdict("REJECTED")
        assert result.artifacts.get("arc_verdict") == "REJECTED"
        assert result.artifacts.get("arc_verdict_normalized") == CouncilVerdict.block.value
        assert result.artifacts.get("arc_verdict_normalization_confidence") == "high"

    def test_ambiguous_raw_text_retained_and_normalized_as_concern(self) -> None:
        result = self._run_with_verdict("needs more discussion")
        assert result.artifacts.get("arc_verdict") == "needs more discussion"
        assert result.artifacts.get("arc_verdict_normalized") == CouncilVerdict.concern.value
        assert result.artifacts.get("arc_verdict_normalization_confidence") == "low"

    def test_missing_verdict_defaults_raw_to_pending_and_normalizes_to_concern(self) -> None:
        result = self._run_with_verdict(None)
        # Raw text retention behavior predates this task: absent verdict is
        # recorded as the literal string "pending" (see run() around L78).
        assert result.artifacts.get("arc_verdict") == "pending"
        assert result.artifacts.get("arc_verdict_normalized") == CouncilVerdict.concern.value
        assert result.artifacts.get("arc_verdict_normalization_confidence") == "low"
