"""P4-03: reuse-reachability fields on ``POST /api/runs``.

Covers the Phase 4 acceptance criteria (AC-5) from
``docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1/phase-3-4-forward-and-reuse.md``:

* ALLOW — an eligible, workspace-matched, in-contract assertion with
  automated reuse enabled routes through the existing
  ``assertion_reuse.evaluate_reuse`` seam and surfaces ``action: "allow"``.
* DENIED via the existing ``block_authoritative_reuse`` lifecycle path — an
  assertion invalidated through that authoritative mechanism is denied by
  ``evaluate_reuse``'s own ``lifecycle_blocked`` gate, not a new ad hoc check.
* DENIED cross-workspace — a reuse target outside the caller's workspace is
  denied by the same seam's ``workspace_mismatch`` gate.
* Fields-absent regression — omitting all four reuse fields produces a
  response byte-identical (same key set, no ``reuse_decision``) to the
  pre-Phase-4 shape; run launch performs NO reuse evaluation at all.

No new policy logic is introduced here or in the production code this test
exercises — every decision is produced by ``services/assertion_reuse.py``
(``evaluate_reuse`` / ``block_authoritative_reuse``), reached via the
pre-existing ``services/run_launch.py::retrieve_first_reuse_decision`` seam.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.services.assertion_reuse import block_authoritative_reuse
from research_foundry.yamlio import dump_yaml, load_yaml


def _enable_automated_reuse(tmp_foundry) -> None:
    """Flip the two controls ``automated_reuse_allowed`` requires (config.py).

    Explicit even though the distribution ``foundry.yaml`` already defaults
    all three assertion-ledger controls to ``true`` for this single-operator
    deployment (``config(assertion-ledger): enable all three local
    capabilities``) -- this test suite must not depend on that default
    remaining true.
    """

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": True,
        "canonical_claims_enabled": False,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)


def _disable_automated_reuse(tmp_foundry) -> None:
    """Explicitly turn ``automated_reuse_allowed`` off regardless of default."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": False,
        "canonical_claims_enabled": False,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)


def _client(tmp_foundry) -> TestClient:
    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app, raise_server_exceptions=True)


def _eligible_assertion(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "assertion_id": "ast_reuse_001",
        "workspace_id": "workspace-a",
        "lifecycle_state": "eligible",
        "rights_allowed": True,
        "sensitivity_allowed": True,
        "evaluation_passed": True,
        "freshness_current": True,
        "invalidation_state": "active",
        "source_edition_id": f"sed_{'a' * 64}",
        "extraction_contract": "contract-v1",
    }
    value.update(overrides)
    return value


# ---------------------------------------------------------------------------
# Fields-absent regression
# ---------------------------------------------------------------------------


def test_reuse_fields_absent_leaves_response_shape_unchanged(tmp_foundry) -> None:
    """No reuse_* fields supplied -> identical response shape to pre-Phase-4.

    Proves the "no behavior change on omission" resilience clause by
    inspecting the actual response, not assuming it.
    """

    resp = _client(tmp_foundry).post(
        "/api/runs", json={"text": "No reuse fields supplied at all."}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "reuse_decision" not in body
    assert set(body.keys()) == {
        "run_id",
        "status",
        "intent_id",
        "raw_idea_id",
        "brief_path",
        "swarm_path",
        "routing_path",
        "next_step",
    }


def test_reuse_ancillary_fields_without_reuse_assertion_trigger_no_evaluation(
    tmp_foundry,
) -> None:
    """``reuse_workspace_id``/``required_reuse_edition_id`` alone (no
    ``reuse_assertion``) must not trigger any reuse evaluation -- mirrors
    ``launch_run``'s own ``if reuse_assertion is not None`` guard."""

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Ancillary reuse fields with no assertion payload.",
            "reuse_workspace_id": "workspace-a",
            "required_reuse_edition_id": f"sed_{'a' * 64}",
        },
    )
    assert resp.status_code == 201, resp.text
    assert "reuse_decision" not in resp.json()


# ---------------------------------------------------------------------------
# ALLOW
# ---------------------------------------------------------------------------


def test_reuse_allow_scenario_routes_through_existing_evaluate_reuse_seam(
    tmp_foundry,
) -> None:
    _enable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Reuse an eligible assertion for this run.",
            "reuse_assertion": _eligible_assertion(),
            "reuse_workspace_id": "workspace-a",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["reuse_decision"] == {
        "action": "allow",
        "reason_code": "eligible",
        "assertion_id": "ast_reuse_001",
    }


# ---------------------------------------------------------------------------
# DENIED
# ---------------------------------------------------------------------------


def test_reuse_denied_via_block_authoritative_reuse_path(tmp_foundry) -> None:
    """An assertion invalidated through the existing ``block_authoritative_reuse``
    lifecycle mechanism is denied by ``evaluate_reuse``'s own
    ``lifecycle_blocked`` gate -- not a new ad hoc check."""

    _enable_automated_reuse(tmp_foundry)
    blocked = block_authoritative_reuse(_eligible_assertion(), event_id="evt_001")
    assert blocked["lifecycle_state"] == "blocked"

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "A blocked assertion must not be reused.",
            "reuse_assertion": blocked,
            "reuse_workspace_id": "workspace-a",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:lifecycle_blocked"


def test_reuse_denied_cross_workspace_target_via_existing_seam(tmp_foundry) -> None:
    """An unauthorized cross-workspace reuse target is denied via the same
    seam's ``workspace_mismatch`` check, not a new ad hoc check."""

    _enable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Cross-workspace reuse must be denied.",
            "reuse_assertion": _eligible_assertion(workspace_id="workspace-a"),
            "reuse_workspace_id": "workspace-b",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:workspace_mismatch"


def test_reuse_denied_when_automated_reuse_capability_is_off(
    tmp_foundry,
) -> None:
    """With the ``automated_reuse_enabled`` control off, an otherwise
    fully-eligible assertion is still denied (fail-closed capability gate)."""

    _disable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Automated reuse capability defaults to off.",
            "reuse_assertion": _eligible_assertion(),
            "reuse_workspace_id": "workspace-a",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:automated_reuse_disabled"


@pytest.mark.parametrize(
    ("reuse_workspace_id"),
    [None, "", "   "],
)
def test_reuse_denied_when_workspace_context_missing_via_resolve_or_deny(
    tmp_foundry, reuse_workspace_id: str | None
) -> None:
    """Absent/blank/whitespace-only ``reuse_workspace_id`` is denied with the
    same ``workspace_context_missing`` reason P1's shared
    ``assertion_workspace.resolve_or_deny`` gate already uses -- confirms
    P4-02's wiring routes the workspace-id normalization through that helper."""

    _enable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "No usable workspace context supplied for reuse.",
            "reuse_assertion": _eligible_assertion(),
            "reuse_workspace_id": reuse_workspace_id,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:workspace_context_missing"
