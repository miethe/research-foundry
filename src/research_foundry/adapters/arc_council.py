"""ARC Council adapter — submits research output to ARC for agent review critique.

Real mode (when ARC is reachable) posts the research brief to ARC via the
``scaffold_review`` endpoint and returns a deterministic ``AdapterResult``
with the arc_run_id and any available verdict. Degraded mode (ARC unreachable)
returns a clearly-labeled stub AdapterResult with ``degraded=True`` so the
pipeline stays testable offline with no ARC installation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from .base import AdapterResult, BaseAdapter, register


class CouncilVerdict(str, Enum):
    """Normalized ARC council verdict.

    ARC returns a free-form verdict string; this enum is the adapter-boundary
    normalization target. Fail-toward-caution: anything unparseable or
    ambiguous maps to ``concern``, never silently to ``approve``.
    """

    approve = "approve"
    concern = "concern"
    block = "block"


# Recognized "approve" phrasing — checked as whole-word/phrase matches against
# the lowercased, normalized raw verdict text.
_APPROVE_PATTERNS: tuple[str, ...] = (
    "approve",
    "approved",
    "approval",
    "lgtm",
    "ship it",
    "go ahead",
    "sign off",
    "signed off",
    "no objection",
)

# Recognized unambiguous block/reject phrasing. Kept conservative — only
# language that clearly means "do not proceed" belongs here.
_BLOCK_PATTERNS: tuple[str, ...] = (
    "block",
    "blocked",
    "blocking",
    "reject",
    "rejected",
    "rejection",
    "do not proceed",
    "must not proceed",
    "veto",
    "vetoed",
    "denied",
    "deny",
)


def normalize_council_verdict(raw: str | None) -> tuple[CouncilVerdict, str]:
    """Map a free-form ARC verdict string to a :class:`CouncilVerdict`.

    Returns a ``(verdict, confidence)`` tuple where ``confidence`` is
    ``"high"`` for confidently-recognized approve/block phrasing and
    ``"low"`` for anything ambiguous, empty, or unparseable — in which case
    the result is always ``CouncilVerdict.concern`` (fail-toward-caution).

    This function is pure and side-effect free: it never mutates ``raw`` or
    any ARC record; callers are responsible for retaining the original text
    alongside the normalized result.
    """

    if raw is None:
        return CouncilVerdict.concern, "low"

    text = raw.strip().lower()
    if not text:
        return CouncilVerdict.concern, "low"

    # Collapse punctuation/whitespace so phrase matches are robust to
    # formatting variance (e.g. "APPROVED!", "approved.", "re-jected").
    normalized = re.sub(r"[^a-z0-9\s]+", " ", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    has_block = any(pattern in normalized for pattern in _BLOCK_PATTERNS)
    has_approve = any(pattern in normalized for pattern in _APPROVE_PATTERNS)

    # Ambiguous: both signals present (e.g. "approved but blocking concerns
    # remain") — fail toward caution rather than guessing.
    if has_block and has_approve:
        return CouncilVerdict.concern, "low"
    if has_block:
        return CouncilVerdict.block, "high"
    if has_approve:
        return CouncilVerdict.approve, "high"
    return CouncilVerdict.concern, "low"


class ARCCouncilAdapter(BaseAdapter):
    """Wraps the ARC review council for post-research critique."""

    id = "arc_council"
    requires: tuple[str, ...] = ()  # stdlib-only; availability gated on HTTP reachability

    def available(self) -> bool:
        """Return True only when the ARC server is reachable.

        Never raises — any connection/timeout error returns False.
        """

        try:
            from ..integrations.arc import ArcClient

            return ArcClient.from_config().available()
        except Exception:  # noqa: BLE001
            return False

    def run(self, request: dict[str, Any]) -> AdapterResult:
        """Submit ``request`` to ARC for council review critique.

        In real mode: POSTs the brief to ARC, reads back any available verdict,
        and returns the arc_run_id + verdict in ``artifacts`` and ``notes``.
        In degraded mode: returns a deterministic stub with ``degraded=True``.

        Request fields (all optional — degrade gracefully if missing):
        - ``council``: ARC council name (default: ``research-review-council``)
        - ``target``: review target path/description
        - ``objective``: review objective string
        - ``run_id``: research foundry run id (used in the ARC payload)
        """

        if not self.available():
            return self._stub(request)

        try:
            from ..integrations.arc import ArcClient

            client = ArcClient.from_config()
            payload: dict[str, Any] = {
                "council": request.get("council", "research-review-council"),
                "target": request.get("target", "evidence_bundle.yaml"),
                "objective": request.get("objective", "Review research evidence bundle."),
            }
            response = client.scaffold_review(payload)
            if not isinstance(response, dict):
                return self._stub(request, note="ARC scaffold_review returned unexpected response")

            arc_run_id = str(response.get("run_id") or "")
            notes = [f"ARC run scaffolded: arc_run_id={arc_run_id}"]
            artifacts: dict[str, str] = {}

            verdict: str | None = None
            if arc_run_id:
                run_record = client.get_run(arc_run_id)
                if isinstance(run_record, dict):
                    verdict = run_record.get("verdict")
                    if verdict:
                        notes.append(f"ARC verdict: {verdict}")
                    artifacts["arc_run_id"] = arc_run_id
                    artifacts["arc_verdict"] = str(verdict or "pending")
                    normalized_verdict, confidence = normalize_council_verdict(verdict)
                    artifacts["arc_verdict_normalized"] = normalized_verdict.value
                    artifacts["arc_verdict_normalization_confidence"] = confidence

            return AdapterResult(
                adapter=self.id,
                degraded=False,
                source_candidates=[],
                artifacts=artifacts,
                notes=notes,
            )
        except Exception:  # noqa: BLE001 — never raise into pipeline
            return self._stub(request, note="ARC error during run submission")

    def _stub(self, request: dict[str, Any], *, note: str | None = None) -> AdapterResult:
        notes = ["arc unreachable: deterministic stub"]
        if note:
            notes.append(note)
        return AdapterResult(
            adapter=self.id,
            degraded=True,
            source_candidates=[],
            artifacts={},
            notes=notes,
        )


register(ARCCouncilAdapter())

__all__ = ["ARCCouncilAdapter", "CouncilVerdict", "normalize_council_verdict"]
