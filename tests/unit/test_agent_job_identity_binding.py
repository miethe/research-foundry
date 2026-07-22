"""Unit tests for agent-job identity binding (public-multiuser Phase 2, ACT-204).

FR-12: under ``deployment_mode=multi_user`` with a configured
``agents.default_service_account_id``, ``AgentJobService.create_job``
resolves the job's *execution* identity (persisted ``created_by``) to the
service account rather than the triggering caller, and records BOTH
identities in a best-effort ``audit_event`` row.

AC-5 (the hard regression gate): under ``deployment_mode=single_user``
(including the unset/default case) — or under ``multi_user`` with no
default service account configured — this binding never activates:
``created_by`` flows through byte-identical to pre-ACT-204 behavior, and no
new ``audit_event`` row is written by ``create_job``.
"""

from __future__ import annotations

from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.audit_service import list_events
from research_foundry.yamlio import dump_yaml, load_yaml

_MINIMAL_POLICY_SNAPSHOT = {"allowed_tools": ["search"], "data_scopes": []}


def _set_foundry_overrides(paths: FoundryPaths, overrides: dict) -> None:
    """Merge *overrides* into the ``foundry:`` block of ``foundry.yaml``."""
    foundry_yaml_path = paths.foundry_yaml
    existing: dict = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    for key, value in overrides.items():
        existing["foundry"][key] = value
    dump_yaml(existing, foundry_yaml_path)


def _create_job(service: AgentJobService, *, created_by: str | None, workspace_id: str | None = "ws1"):
    return service.create_job(
        provider="claude_agent_sdk",
        model_profile="rf_synthesize_deep",
        request_kind="research",
        policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
        project_id="test-project",
        workspace_id=workspace_id,
        created_by=created_by,
    )


# ---------------------------------------------------------------------------
# AC-5: single_user (default/unset) — byte-identical, no binding, no audit row
# ---------------------------------------------------------------------------


def test_single_user_default_created_by_unchanged(tmp_foundry: FoundryPaths) -> None:
    """deployment_mode unset (defaults to single_user) -> created_by passes through."""
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, created_by="alice")

    assert job.created_by == "alice"
    events = list_events(tmp_foundry, mutation_type="agent_job_launched")
    assert events["items"] == []


def test_explicit_single_user_created_by_unchanged(tmp_foundry: FoundryPaths) -> None:
    _set_foundry_overrides(tmp_foundry, {"deployment_mode": "single_user"})
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, created_by="alice")

    assert job.created_by == "alice"
    events = list_events(tmp_foundry, mutation_type="agent_job_launched")
    assert events["items"] == []


def test_multi_user_without_default_service_account_unchanged(tmp_foundry: FoundryPaths) -> None:
    """multi_user is set, but agents.default_service_account_id is NOT configured
    -> the binding branch is entered but has nothing to bind to, so behavior
    is unchanged (created_by passes through, no audit row)."""
    _set_foundry_overrides(tmp_foundry, {"deployment_mode": "multi_user"})
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, created_by="alice")

    assert job.created_by == "alice"
    events = list_events(tmp_foundry, mutation_type="agent_job_launched")
    assert events["items"] == []


def test_single_user_created_by_none_unchanged(tmp_foundry: FoundryPaths) -> None:
    """created_by=None (the default) stays None under single_user -- no crash,
    no coercion to a service account, no audit row."""
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, created_by=None)

    assert job.created_by is None
    events = list_events(tmp_foundry, mutation_type="agent_job_launched")
    assert events["items"] == []


# ---------------------------------------------------------------------------
# FR-12: multi_user + default_service_account_id -> binding activates
# ---------------------------------------------------------------------------


def test_multi_user_with_service_account_binds_execution_identity(
    tmp_foundry: FoundryPaths,
) -> None:
    _set_foundry_overrides(
        tmp_foundry,
        {
            "deployment_mode": "multi_user",
            "agents": {"default_service_account_id": "svc_default_researcher"},
        },
    )
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, created_by="alice", workspace_id="ws1")

    # Execution identity on the persisted job is the service account, not "alice".
    assert job.created_by == "svc_default_researcher"

    events = list_events(tmp_foundry, mutation_type="agent_job_launched")
    assert len(events["items"]) == 1
    event = events["items"][0]
    assert event["target_ref"] == job.agent_job_id
    assert event["actor_user_id"] == "svc_default_researcher"
    assert event["actor_workspace_id"] == "ws1"
    snapshot = event["policy_snapshot"]
    assert snapshot["triggering_identity"] == "alice"
    assert snapshot["executing_identity"] == "svc_default_researcher"
    assert snapshot["deployment_mode"] == "multi_user"


def test_multi_user_binding_survives_created_by_none(tmp_foundry: FoundryPaths) -> None:
    """Even when the triggering caller supplied no created_by at all, the
    service-account binding still activates under multi_user -- the job's
    execution identity is never left as None once a default service account
    is configured."""
    _set_foundry_overrides(
        tmp_foundry,
        {
            "deployment_mode": "multi_user",
            "agents": {"default_service_account_id": "svc_default_researcher"},
        },
    )
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, created_by=None, workspace_id="ws1")

    assert job.created_by == "svc_default_researcher"
    events = list_events(tmp_foundry, mutation_type="agent_job_launched")
    assert len(events["items"]) == 1
    assert events["items"][0]["policy_snapshot"]["triggering_identity"] is None
