"""Unit tests for AgentJobService's WKSP-304 Phase 3 query-layer scoping.

TASK-3.3 scope note
--------------------
The Phase 3 plan (``phase-3-query-layer-scoping.md``) names this file's two
target methods as ``get_job``/``list_jobs``. Neither exists under those
literal names:

* ``get_job`` maps to :meth:`AgentJobService.load_job` — the actual single-
  record read (confirmed here).
* ``list_jobs`` has **no corresponding method anywhere in this codebase**.
  There is no workspace-wide agent-job listing endpoint or service method
  today (``GET /api/agent-jobs`` does not exist; the router only exposes
  per-job-id routes). This is a real plan/implementation mismatch, not an
  oversight in this test file — flagged for the TASK-3.6 100%-coverage
  checklist rather than invented here (adding a listing method that no
  caller needs would be scope creep beyond this task).

Unlike ``catalog_service``/``builder_service``, agent jobs are plain JSON
files under ``agent_job_dir(job_id)`` (no SQL, no YAML draft store) — see
:meth:`AgentJobService.load_job`'s docstring for how the flag-gated
predicate maps onto a file-backed single-record read (raises ``KeyError`` on
a workspace mismatch, the same exception already raised for a missing job).
"""

from __future__ import annotations

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_service import AgentJobService

_MINIMAL_POLICY_SNAPSHOT = {"allowed_tools": ["search"], "data_scopes": []}

_WS_MINE = AuthIdentity("u1", "ws-mine", ("owner",))
_WS_OTHER = AuthIdentity("u2", "ws-other", ("owner",))


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ``workspace_isolation_enforcement`` resolving active.

    Monkeypatches :meth:`FoundryConfig.resolve_workspace_isolation_enforced`
    itself (never :meth:`AgentJobService._isolation_active`), matching the
    same convention used in ``test_catalog_service.py`` /
    ``test_builder_service.py`` for this phase.
    """

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


def _create_job(service: AgentJobService, *, workspace_id: str | None):
    return service.create_job(
        provider="claude_agent_sdk",
        model_profile="rf_synthesize_deep",
        request_kind="research",
        policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
        project_id="test-project",
        workspace_id=workspace_id,
    )


def test_load_job_identity_none_is_byte_identical(tmp_foundry: FoundryPaths) -> None:
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, workspace_id="ws-mine")

    baseline = service.load_job(job.agent_job_id)
    assert service.load_job(job.agent_job_id, identity=None) == baseline


def test_load_job_identity_active_hides_cross_workspace_job(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, workspace_id="ws-mine")

    _force_isolation_active(monkeypatch)

    assert service.load_job(job.agent_job_id, identity=_WS_MINE).agent_job_id == job.agent_job_id
    # Fail-closed: a cross-workspace lookup is indistinguishable from "not
    # found" — same KeyError the router's _load_job_or_404 already maps to
    # a 404 for a genuinely missing job.
    with pytest.raises(KeyError):
        service.load_job(job.agent_job_id, identity=_WS_OTHER)


def test_load_job_identity_present_but_inactive_stays_unscoped(
    tmp_foundry: FoundryPaths,
) -> None:
    service = AgentJobService(tmp_foundry)
    job = _create_job(service, workspace_id="ws-mine")

    # No monkeypatch: tmp_foundry's auth.provider is unset ("none") -> AUTO
    # resolves advisory (False), today's real default. A cross-workspace
    # identity must not hide the job under the real, unmodified resolver.
    loaded = service.load_job(job.agent_job_id, identity=_WS_OTHER)
    assert loaded.agent_job_id == job.agent_job_id


def test_load_job_identity_active_null_workspace_job_is_hidden(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job with no workspace_id (the common case today — D12: unenforced,
    nullable) is treated as belonging to no workspace once isolation is
    active — fail-closed, mirroring how a NULL ``workspace_id`` column never
    satisfies ``= ?`` in the SQL-backed services."""

    service = AgentJobService(tmp_foundry)
    job = _create_job(service, workspace_id=None)

    _force_isolation_active(monkeypatch)

    with pytest.raises(KeyError):
        service.load_job(job.agent_job_id, identity=_WS_MINE)
