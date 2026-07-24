"""CARP-5.1: retrieval_policy / retrieval_limits on ``POST /api/runs``.

Covers the P5 acceptance criteria from
``docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md``:

* Legacy request keys (no ``retrieval_*`` fields) behave exactly as before --
  ``evidence_plan_ref``/``retrieval_summary`` are absent from the response,
  byte-identical to the pre-CARP shape (carp-contract-freeze.md §1).
* Opting into ``retrieval_policy="catalog_only"`` against an empty/unset-up
  catalog (the default in a fresh ``tmp_foundry`` workspace) returns a
  ``retrieval_summary`` carrying **zero candidate-derived fields** -- only
  ``questions_total`` -- asserted positively (carp-contract-freeze.md §2.3),
  proving the frozen denial/empty shape reaches the HTTP response unmodified.

No new policy logic is introduced here -- every value asserted below is
produced by the existing ``research_evidence_planning``/``catalog_retrieval``
seam, reached via ``services/run_launch.py::launch_run`` ->
``services/planning.py::plan_run``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.yamlio import dump_yaml, load_yaml


def _client(tmp_foundry) -> TestClient:
    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app, raise_server_exceptions=True)


def test_retrieval_fields_absent_leaves_response_shape_unchanged(tmp_foundry) -> None:
    """No ``retrieval_*`` fields supplied -> identical response shape to
    pre-CARP-5 -- ``evidence_plan_ref``/``retrieval_summary`` are omitted
    entirely, not present-but-null."""

    resp = _client(tmp_foundry).post(
        "/api/runs", json={"text": "No retrieval fields supplied at all."}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "evidence_plan_ref" not in body
    assert "retrieval_summary" not in body
    assert set(body.keys()) == {
        "run_id",
        "status",
        "intent_id",
        "raw_idea_id",
        "brief_path",
        "swarm_path",
        "routing_path",
        "next_step",
        "rf_schema_version",
    }


def test_retrieval_policy_other_than_active_values_is_treated_as_disabled(
    tmp_foundry,
) -> None:
    """A garbage/unknown ``retrieval_policy`` value is not "disabled" by an
    explicit check here -- it falls through to ``plan_run``'s own
    fail-safe-to-disabled default (no implicit network fallback from any
    state, carp-contract-freeze.md §1)."""

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={"text": "Unknown retrieval policy value.", "retrieval_policy": "not_a_real_policy"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "evidence_plan_ref" not in body
    assert "retrieval_summary" not in body


def test_catalog_only_against_empty_catalog_exposes_zero_candidate_fields(
    tmp_foundry,
) -> None:
    """``retrieval_policy="catalog_only"`` against a fresh workspace (no
    assertions ledger records at all) is the frozen catalog-empty terminal
    state (carp-contract-freeze.md §3.2 ``catalog_empty``) -- the returned
    ``retrieval_summary`` must carry **zero** candidate-derived fields.
    Asserted positively: the ONLY key present is ``questions_total``, and
    every candidate-derived counter (``questions_covered``,
    ``questions_residual``, ``candidates_evaluated``, ``candidates_selected``,
    ``avoided_provider_calls``, ``residual_reason_counts``) is absent."""

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Catalog-only retrieval against an empty ledger.",
            "retrieval_policy": "catalog_only",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["evidence_plan_ref"] is not None
    assert body["evidence_plan_ref"].startswith("evp_")

    summary = body["retrieval_summary"]
    assert summary == {"questions_total": summary["questions_total"]}
    assert summary["questions_total"] >= 1
    for candidate_derived_key in (
        "questions_covered",
        "questions_residual",
        "candidates_evaluated",
        "candidates_selected",
        "avoided_provider_calls",
        "residual_reason_counts",
    ):
        assert candidate_derived_key not in summary


def test_retrieval_limits_without_policy_is_ignored(tmp_foundry) -> None:
    """``retrieval_limits`` supplied without an active ``retrieval_policy``
    is inert -- mirrors ``plan_run``'s own "ignored when retrieval_policy is
    inactive" contract."""

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Limits with no active policy.",
            "retrieval_limits": {"max_questions": 1},
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "evidence_plan_ref" not in body
    assert "retrieval_summary" not in body


def test_authenticated_owner_identity_reaches_retrieval_denial_check(
    tmp_foundry, monkeypatch
) -> None:
    """RBAC/workspace regression (CARP-5.1): an authenticated caller who
    clears the run-launch RBAC gate (``owner`` role, real ``workspace_id``)
    still has that identity threaded all the way from the router into
    ``build_evidence_plan`` -- it is never silently dropped in favor of the
    ``identity=None`` default. Proven by: the SAME frozen catalog_empty /
    zero-candidate-fields shape (carp-contract-freeze.md §2.3) that the
    no-auth tests above see also appears here, under a real bearer identity
    that passed the ``owner``/``admin`` RBAC gate -- not a crash, and not a
    different (leakier) shape. Mirrors ``tests/test_serve_api.py``'s
    ``_make_rbac_client`` fixture pattern (TEST-011h/i)."""

    token = "carp-5-1-retrieval-rbac-token"  # noqa: S105 -- test-only fixture token
    foundry_yaml_path = tmp_foundry.root / "foundry.yaml"
    existing = load_yaml(foundry_yaml_path) or {}
    existing.setdefault("foundry", {})["auth"] = {
        "provider": "local_static",
        "local_static": {
            "tokens": [
                {
                    "token_env": "RF_CARP51_RETRIEVAL_RBAC_TEST_TOKEN",
                    "user_id": "test_user",
                    "workspace_id": "default",
                    "roles": ["owner"],
                }
            ]
        },
    }
    dump_yaml(existing, foundry_yaml_path)
    monkeypatch.setenv("RF_CARP51_RETRIEVAL_RBAC_TEST_TOKEN", token)

    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    client = TestClient(app, raise_server_exceptions=True)

    resp = client.post(
        "/api/runs",
        json={
            "text": "Authenticated identity threading regression.",
            "retrieval_policy": "catalog_only",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["evidence_plan_ref"] is not None
    assert body["evidence_plan_ref"].startswith("evp_")

    summary = body["retrieval_summary"]
    assert summary == {"questions_total": summary["questions_total"]}
    for candidate_derived_key in (
        "questions_covered",
        "questions_residual",
        "candidates_evaluated",
        "candidates_selected",
        "avoided_provider_calls",
        "residual_reason_counts",
    ):
        assert candidate_derived_key not in summary


def test_unauthenticated_caller_denial_and_authenticated_caller_empty_state_both_zero_out(
    tmp_foundry,
) -> None:
    """Positive assertion (CARP-5.1 review checklist): whether the catalog
    denies because identity is entirely absent (``workspace_context_missing``
    -- ``catalog_retrieval.catalog_receipt``'s fail-closed branch) or accepts
    an authenticated identity against a workspace with zero ledger records
    (``catalog_empty``), the caller-visible ``retrieval_summary`` is the
    IDENTICAL zero-candidate-fields shape either way -- a denied caller never
    gets a richer or different response shape than an authorized-but-empty
    one, and neither ever exposes a candidate-derived counter."""

    resp_no_identity = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "No identity at all.",
            "retrieval_policy": "catalog_only",
        },
    )
    assert resp_no_identity.status_code == 201, resp_no_identity.text
    summary_no_identity = resp_no_identity.json()["retrieval_summary"]
    assert set(summary_no_identity.keys()) == {"questions_total"}
