"""ARC Council adapter — submits research output to ARC for agent review critique.

Real mode (when ARC is reachable) posts the research brief to ARC via the
``scaffold_review`` endpoint and returns a deterministic ``AdapterResult``
with the arc_run_id and any available verdict. Degraded mode (ARC unreachable)
returns a clearly-labeled stub AdapterResult with ``degraded=True`` so the
pipeline stays testable offline with no ARC installation.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, BaseAdapter, register


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

__all__ = ["ARCCouncilAdapter"]
