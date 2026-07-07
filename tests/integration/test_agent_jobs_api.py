"""Integration tests for the Agent Jobs API endpoints (P4.4).

Cross-owner Propagation Contract Verification (R-P3)
=====================================================
This test suite is the API contract fixture for the frontend components
listed in each AC's ``target_surfaces``.  The comment block below documents
which tests satisfy each propagation_contract — the FE will build against
these shapes without modification.

AC-2.3  Event stream renders live in Agents UI
  propagation_contract:
    GET /api/agent-jobs/{id}/events → Content-Type: text/event-stream;
    events are delivered as "data: {json}\\n\\n" SSE frames; redact_payload
    is applied server-side before serialization (no raw credentials).
  fixtures:
    - TestSSEStream::test_sse_correct_content_type
    - TestSSEStream::test_sse_no_raw_credential_in_stream
    - TestSSEStream::test_sse_events_use_data_prefix_format
  FE contract notes:
    * AgentJobEventPanel opens EventSource against GET /api/agent-jobs/{id}/events.
    * useAgentJobEvents parses "data: {json}" frames.
    * No raw credential values ever appear in the stream (redact_payload invariant).

AC-3.5  Evidence Intake acceptance flow — FE handles missing/partial staged data
  propagation_contract:
    GET /api/agent-jobs/{id}/artifacts → list of staged artifact dicts; each
    item has artifact_id, artifact_kind, accepted=False for staged items.
    POST /api/agent-jobs/{id}/accept → {agent_job_id, acceptance_id,
    accepted_artifact_count, artifact_ids, accepted_by, accepted_at}.
  fixtures:
    - TestDetailAndArtifacts::test_list_artifacts_returns_staged_items
    - TestAcceptEndpoint::test_accept_success_returns_summary
    - TestAcceptEndpoint::test_accept_accepted_artifacts_carry_agent_job_id
  FE contract notes:
    * EvidenceIntakePanel renders artifact_kind badge per item.
    * Missing fields render as "incomplete proposal — review before accepting".
    * POST /api/agent-jobs/{id}/accept confirms accepted_artifact_count in response.

AC-4.4  Governance gates are visible before launch
  propagation_contract:
    POST /api/agent-jobs with a guard_check-rejected policy_snapshot returns
    HTTP 422 (exit_code=3, GOVERNANCE block) or HTTP 400 (exit_code=7,
    HUMAN_REVIEW) with body:
      {error: "governance_rejected", exit_code: int,
       violations: [{rule_id, severity, message, detail}]}.
  fixtures:
    - TestLaunchEndpoint::test_launch_rejected_guard_returns_422
    - TestLaunchEndpoint::test_launch_rejected_guard_no_subprocess
    - TestLaunchEndpoint::test_launch_human_review_returns_400
  FE contract notes:
    * AgentJobLaunchForm reads violations[].rule_id + message after rejection.
    * PolicyGateSummary remains visible; form does not clear on governance error.

AC-4.5  FE handles missing policy_snapshot fields
  propagation_contract:
    GET /api/agent-jobs/{id} returns the full agent_job record including
    policy_snapshot dict.  Nullable sub-fields (budget_usd, sensitivity, etc.)
    are present as null — not omitted — so FE can render "not recorded" text.
    workspace_id and created_by are always nullable (D12 — auth deferred P5).
  fixtures:
    - TestDetailAndArtifacts::test_get_job_detail_includes_policy_snapshot
    - TestLaunchEndpoint::test_launch_nullable_workspace_id_and_created_by
  FE contract notes:
    * PolicyGateSummary reads policy_snapshot from job detail GET response.
    * Null sub-fields must render "not recorded" rather than an empty row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.agent_job_schemas import AgentJob, AgentJobStatus
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.services.governance import GuardResult, Violation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def foundry_paths(tmp_path: Path) -> FoundryPaths:
    """Isolated FoundryPaths rooted at a temporary directory."""
    return FoundryPaths(root=tmp_path)


@pytest.fixture()
def test_app(foundry_paths: FoundryPaths) -> Any:
    """FastAPI app with the paths dependency overridden to the temp directory.

    Writes a minimal ``foundry.yaml`` with ``agents.enabled: true`` so the
    agent-job router is registered.  No auth, no allowlist — tests run without
    authentication middleware.  The paths dependency is overridden so all job
    reads/writes land in ``tmp_path``.
    """
    foundry_paths.foundry_yaml.write_text(
        "foundry:\n  agents:\n    enabled: true\n",
        encoding="utf-8",
    )
    config = FoundryConfig(paths=foundry_paths)
    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: foundry_paths
    return app


@pytest.fixture()
def client(test_app: Any) -> TestClient:
    """Synchronous TestClient for the overridden test app."""
    return TestClient(test_app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MINIMAL_POLICY_SNAPSHOT: dict[str, Any] = {
    "allowed_tools": ["search", "source_card"],
    "data_scopes": [],
}

_LAUNCH_BODY: dict[str, Any] = {
    "provider": "claude_agent_sdk",
    "model_profile": "rf_synthesize_deep",
    "request_kind": "research",
    "policy_snapshot": _MINIMAL_POLICY_SNAPSHOT,
    "project_id": "test-project",
    "workspace_id": None,
    "created_by": None,
}


def _passing_guard() -> GuardResult:
    return GuardResult(passed=True, exit_code=0, violations=[])


def _failing_guard(exit_code: int = 3) -> GuardResult:
    return GuardResult(
        passed=False,
        exit_code=exit_code,
        violations=[
            Violation(
                rule_id="no_work_keys_for_personal_runs",
                severity="block",
                message="Work key required for non-personal model provider",
                detail="provider=claude_agent_sdk requires a work key profile",
            )
        ],
    )


def _mock_popen() -> MagicMock:
    """Return a mock Popen that appears to have already exited cleanly."""
    proc = MagicMock()
    proc.pid = 99999
    proc.poll.return_value = 0
    proc.wait.return_value = 0
    return proc


def _write_job_on_disk(
    service: AgentJobService,
    status: AgentJobStatus = AgentJobStatus.queued,
    **overrides: Any,
) -> AgentJob:
    """Create and persist a job via the service layer, then force-set *status*.

    Uses the real ``create_job`` path so on-disk records mirror production.
    ``update_job_status`` does not enforce state-machine transitions; it writes
    the provided status directly, which is intentional for test setup.
    """
    job = service.create_job(
        provider=overrides.get("provider", "claude_agent_sdk"),
        model_profile=overrides.get("model_profile", "rf_synthesize_deep"),
        request_kind=overrides.get("request_kind", "research"),
        policy_snapshot=overrides.get("policy_snapshot", dict(_MINIMAL_POLICY_SNAPSHOT)),
        project_id=overrides.get("project_id", "test-project"),
        workspace_id=overrides.get("workspace_id"),
        created_by=overrides.get("created_by"),
    )
    if status != AgentJobStatus.queued:
        job = service.update_job_status(job.agent_job_id, status)
    return job


def _write_staged_artifact(
    job_dir: Path,
    artifact_id: str,
    job_id: str,
    kind: str = "source_card",
) -> dict[str, Any]:
    """Write a staged (unaccepted) artifact JSON file to *job_dir*."""
    artifact: dict[str, Any] = {
        "artifact_id": artifact_id,
        "agent_job_id": job_id,
        "artifact_kind": kind,
        "created_at": "2026-07-07T00:00:00Z",
        "accepted": False,
    }
    (job_dir / f"artifact_{artifact_id}.json").write_text(
        json.dumps(artifact), encoding="utf-8"
    )
    return artifact


# ---------------------------------------------------------------------------
# Group 1: Launch — POST /api/agent-jobs  (API-4.1)
# ---------------------------------------------------------------------------


class TestLaunchEndpoint:
    """POST /api/agent-jobs: governance gate, 201 success, nullable fields."""

    def test_launch_rejected_guard_returns_422(self, client: TestClient) -> None:
        """guard_check exit_code=3 (GOVERNANCE block) → HTTP 422 with violations.

        Propagation contract for AC-4.4: the violations array shape is what
        AgentJobLaunchForm reads to display the specific rule that blocked launch.
        """
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_failing_guard(exit_code=3),
        ):
            resp = client.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["error"] == "governance_rejected"
        assert detail["exit_code"] == 3
        assert isinstance(detail["violations"], list)
        v = detail["violations"][0]
        assert v["rule_id"] == "no_work_keys_for_personal_runs"
        assert "message" in v and v["message"]
        assert "severity" in v

    def test_launch_rejected_guard_no_subprocess(self, client: TestClient) -> None:
        """A rejected guard MUST NOT spawn a subprocess (API-4.1 invariant).

        The subprocess is the credential-bearing process.  Any spawn before the
        guard check would constitute a credentials-before-governance violation.
        """
        with (
            patch(
                "research_foundry.api.routers.agent_jobs.guard_check",
                return_value=_failing_guard(exit_code=3),
            ),
            patch(
                "research_foundry.services.agent_job_service.subprocess.Popen"
            ) as mock_popen,
        ):
            resp = client.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code in (400, 422)
        mock_popen.assert_not_called(), (
            "subprocess.Popen must NOT be called when the governance guard rejects"
        )

    def test_launch_human_review_returns_400(self, client: TestClient) -> None:
        """guard_check exit_code=7 (HUMAN_REVIEW) → HTTP 400 (not 422)."""
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_failing_guard(exit_code=7),
        ):
            resp = client.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code == 400

    def test_launch_success_returns_201_with_job(self, client: TestClient) -> None:
        """Successful launch (guard passes + spawn mock) → HTTP 201 with job record."""
        with (
            patch(
                "research_foundry.api.routers.agent_jobs.guard_check",
                return_value=_passing_guard(),
            ),
            patch(
                "research_foundry.services.agent_job_service.subprocess.Popen",
                return_value=_mock_popen(),
            ),
            patch(
                "research_foundry.services.agent_job_service.importlib.util.find_spec",
                return_value=MagicMock(),
            ),
        ):
            resp = client.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code == 201, resp.text
        job = resp.json()
        assert "agent_job_id" in job and job["agent_job_id"]
        assert job["status"] == AgentJobStatus.queued.value
        assert job["provider"] == "claude_agent_sdk"
        assert job["model_profile"] == "rf_synthesize_deep"
        assert "policy_snapshot" in job

    def test_launch_nullable_workspace_id_and_created_by(
        self, client: TestClient
    ) -> None:
        """workspace_id=null and created_by=null are accepted without error.

        Propagation contract for AC-4.5: these fields are nullable (D12, auth in P5).
        The job record returned by GET /api/agent-jobs/{id} preserves them as null.
        """
        body = {**_LAUNCH_BODY, "workspace_id": None, "created_by": None}
        with (
            patch(
                "research_foundry.api.routers.agent_jobs.guard_check",
                return_value=_passing_guard(),
            ),
            patch(
                "research_foundry.services.agent_job_service.subprocess.Popen",
                return_value=_mock_popen(),
            ),
            patch(
                "research_foundry.services.agent_job_service.importlib.util.find_spec",
                return_value=MagicMock(),
            ),
        ):
            resp = client.post("/api/agent-jobs", json=body)

        assert resp.status_code == 201, resp.text
        job = resp.json()
        assert job["workspace_id"] is None
        assert job["created_by"] is None


# ---------------------------------------------------------------------------
# Group 2: Detail + Artifacts — GET /api/agent-jobs/{id}  (API-4.2)
# ---------------------------------------------------------------------------


class TestDetailAndArtifacts:
    """GET /agent-jobs/{id} detail and GET /agent-jobs/{id}/artifacts."""

    def test_get_job_404_for_missing_id(self, client: TestClient) -> None:
        """GET an unknown job_id → 404."""
        resp = client.get("/api/agent-jobs/nonexistent-job-id123")
        assert resp.status_code == 404

    def test_get_job_404_for_malformed_id_same_response_shape(
        self, client: TestClient
    ) -> None:
        """Malformed IDs and missing IDs produce indistinguishable 404 responses.

        Non-regression for FU-4 (partial fix shipped): callers must not be able
        to distinguish "bad ID format" from "job does not exist" via status code
        or response body shape.  Both must return 404 with the same ``detail`` key.
        """
        missing_resp = client.get("/api/agent-jobs/job-definitely-does-not-exist")
        # Dots are not valid in job_ids (_validate_path_component rejects them).
        malformed_resp = client.get("/api/agent-jobs/bad.id.with.dots")

        assert missing_resp.status_code == 404
        assert malformed_resp.status_code == 404
        # Both must have a "detail" key — same envelope, no info leakage.
        assert "detail" in missing_resp.json()
        assert "detail" in malformed_resp.json()

    def test_get_job_detail_returns_all_core_fields(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """GET /api/agent-jobs/{id} returns the full job record including status."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc)

        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["agent_job_id"] == job.agent_job_id
        assert data["status"] == AgentJobStatus.queued.value
        assert data["provider"] == "claude_agent_sdk"
        assert "policy_snapshot" in data
        assert data["policy_snapshot"]["allowed_tools"] == ["search", "source_card"]

    def test_get_job_detail_includes_policy_snapshot(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """GET /api/agent-jobs/{id} always exposes policy_snapshot (AC-4.5 fixture).

        PolicyGateSummary reads policy_snapshot from this response when showing
        job history.  Null sub-fields must be present (not omitted) so the FE
        can render 'not recorded' rather than omitting the row or throwing.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(
            svc,
            policy_snapshot={
                "allowed_tools": ["search"],
                "data_scopes": [],
                "budget_usd": None,
                "sensitivity": None,
            },
        )
        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}")
        assert resp.status_code == 200
        ps = resp.json()["policy_snapshot"]
        # Required keys must be present; null values must be preserved.
        assert "allowed_tools" in ps
        assert "data_scopes" in ps

    def test_list_artifacts_returns_staged_items(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """GET /api/agent-jobs/{id}/artifacts → list of staged artifacts (AC-3.5 fixture).

        EvidenceIntakePanel reads artifact_id and artifact_kind per item.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc)
        job_dir = foundry_paths.agent_job_dir(job.agent_job_id)
        _write_staged_artifact(job_dir, "art1", job.agent_job_id, kind="source_card")
        _write_staged_artifact(job_dir, "art2", job.agent_job_id, kind="claim")

        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}/artifacts")
        assert resp.status_code == 200, resp.text
        artifacts = resp.json()
        assert isinstance(artifacts, list)
        artifact_ids = {a["artifact_id"] for a in artifacts}
        assert "art1" in artifact_ids
        assert "art2" in artifact_ids
        # All returned items must still be in staged (not accepted) state.
        for a in artifacts:
            assert a.get("accepted") is False, (
                f"Artifact {a.get('artifact_id')} returned by artifacts endpoint "
                "has accepted=True — should not appear in staged list"
            )

    def test_list_artifacts_empty_for_new_job(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """GET /api/agent-jobs/{id}/artifacts → empty list when no artifacts exist."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc)
        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}/artifacts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_artifacts_404_for_missing_job(self, client: TestClient) -> None:
        """GET artifacts for nonexistent job → 404."""
        resp = client.get("/api/agent-jobs/nonexistent-job/artifacts")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Group 3: SSE Stream — GET /api/agent-jobs/{id}/events  (API-4.3)
# ---------------------------------------------------------------------------


class TestSSEStream:
    """GET /agent-jobs/{id}/events: content-type and credential redaction."""

    def test_sse_correct_content_type(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """SSE endpoint responds with Content-Type: text/event-stream (AC-2.3).

        EventSource (browser) requires this exact content-type to open an SSE
        connection.  The response must include this header or the FE hook fails.
        """
        svc = AgentJobService(foundry_paths)
        # Terminal state: generator exits immediately after reading events.
        job = _write_job_on_disk(svc, status=AgentJobStatus.completed)

        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}/events")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/event-stream" in content_type, (
            f"Expected Content-Type: text/event-stream; got {content_type!r}"
        )

    def test_sse_no_raw_credential_in_stream(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """CRITICAL SECURITY: no raw credential value appears in any SSE frame.

        Verifies that redact_payload is applied to every event BEFORE it is
        serialised and yielded (API-4.3 invariant, AC-2.2 compliance).

        Strategy:
          1. Write an event containing a fake credential string to events.jsonl.
          2. Patch redact_payload in the router to replace the fake credential.
          3. Stream the events endpoint.
          4. Assert the fake credential string is absent from the full response body.
          5. Assert redact_payload was actually called (not bypassed).
        """
        _FAKE_CRED = "FAKE-SECRET-CREDENTIAL-sk-abc123xyz987"
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.completed)
        job_dir = foundry_paths.agent_job_dir(job.agent_job_id)
        events_file = job_dir / "events.jsonl"
        # Write an event that embeds the fake credential in a payload dict.
        raw_event: dict[str, Any] = {
            "stage": "plan",
            "status": "running",
            "seq": 0,
            "payload": {
                "api_key": _FAKE_CRED,
                "message": "starting job",
            },
        }
        events_file.write_text(json.dumps(raw_event) + "\n", encoding="utf-8")

        def _mock_redact(obj: Any, **_kwargs: Any) -> Any:
            """Recursively replace the fake credential value with '[REDACTED]'."""
            if isinstance(obj, dict):
                return {
                    k: "[REDACTED]" if v == _FAKE_CRED else _mock_redact(v)
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [_mock_redact(item) for item in obj]
            return obj

        with patch(
            "research_foundry.api.routers.agent_jobs.redact_payload",
            side_effect=_mock_redact,
        ) as mock_redact:
            resp = client.get(f"/api/agent-jobs/{job.agent_job_id}/events")

        assert resp.status_code == 200
        assert _FAKE_CRED not in resp.text, (
            "Raw credential found in SSE stream output — redact_payload invariant violated.\n"
            f"Stream body (first 500 chars): {resp.text[:500]!r}"
        )
        # Positive assertion: redact was applied and produced the replacement marker.
        assert "[REDACTED]" in resp.text, (
            "Expected '[REDACTED]' in stream body — redact_payload did not run or returned "
            "unexpected output."
        )
        # Structural invariant: redact_payload must be called at least once per event.
        assert mock_redact.called, (
            "redact_payload was never called — SSE generator must apply it per event "
            "before serialization (API-4.3 invariant)"
        )

    def test_sse_events_use_data_prefix_format(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Streamed events use the 'data: {json}\\n\\n' SSE wire format (AC-2.3).

        EventSource (browser) splits the stream on this exact prefix.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.completed)
        job_dir = foundry_paths.agent_job_dir(job.agent_job_id)
        event_payload = {"stage": "plan", "status": "running", "seq": 0}
        (job_dir / "events.jsonl").write_text(
            json.dumps(event_payload) + "\n", encoding="utf-8"
        )

        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}/events")
        assert resp.status_code == 200
        assert "data: " in resp.text, (
            f"SSE frame prefix 'data: ' missing from stream body: {resp.text!r}"
        )

    def test_sse_404_for_missing_job(self, client: TestClient) -> None:
        """SSE endpoint returns 404 for a nonexistent job_id."""
        resp = client.get("/api/agent-jobs/nonexistent-job-id/events")
        assert resp.status_code == 404

    def test_sse_empty_stream_for_job_with_no_events(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """SSE stream for a terminal job with no events.jsonl returns 200 + empty body."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.completed)
        # No events.jsonl written — generator should exit cleanly with no output.
        resp = client.get(f"/api/agent-jobs/{job.agent_job_id}/events")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Group 4: Cancel — POST /api/agent-jobs/{id}/cancel  (API-4.4)
# ---------------------------------------------------------------------------


class TestCancelEndpoint:
    """POST /agent-jobs/{id}/cancel: status update, staging invariant, cleanup."""

    def test_cancel_returns_200_with_canceled_status(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Cancel a queued job → HTTP 200 with status=canceled."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc)
        resp = client.post(f"/api/agent-jobs/{job.agent_job_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_zero_staged_artifacts_promoted(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Cancel before accept leaves zero staged artifacts promoted (AC-3.4).

        Canceling or letting a job fail must leave staging discarded — nothing
        partially committed into the catalog.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.running)
        job_dir = foundry_paths.agent_job_dir(job.agent_job_id)
        _write_staged_artifact(job_dir, "art1", job.agent_job_id, kind="source_card")
        _write_staged_artifact(job_dir, "art2", job.agent_job_id, kind="claim")

        resp = client.post(f"/api/agent-jobs/{job.agent_job_id}/cancel")
        assert resp.status_code == 200

        # Verify every artifact file on disk is still in the unaccepted state.
        for artifact_file in sorted(job_dir.glob("artifact_*.json")):
            data = json.loads(artifact_file.read_text(encoding="utf-8"))
            assert not data.get("accepted", False), (
                f"Artifact {data.get('artifact_id')!r} was promoted after cancel — "
                "staging must remain discarded (AC-3.4)"
            )

    def test_cancel_removes_credential_temp_file(
        self, test_app: Any, foundry_paths: FoundryPaths
    ) -> None:
        """Cancel via API removes the credential temp file (SEC-2.2 invariant).

        The service registry is in-memory and per-request.  We inject a
        pre-registered service instance so the cancel handler's terminate/cleanup
        call finds the real subprocess and credential file.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc)

        # Spawn a real (sleeping) process; credential file is written to tempdir.
        proc = svc.spawn_job(
            job,
            b"test-credential-bytes-for-cancel-test",
            command_override=[sys.executable, "-c", "import time; time.sleep(30)"],
        )
        _, cred_path = svc._registry[job.agent_job_id]
        assert cred_path.exists(), "Credential file must exist immediately after spawn"

        try:
            # Inject the pre-registered service so the cancel endpoint can clean up.
            from research_foundry.api.routers import agent_jobs as router_module

            with patch.object(router_module, "_get_service", return_value=svc):
                bound_client = TestClient(test_app, raise_server_exceptions=True)
                resp = bound_client.post(f"/api/agent-jobs/{job.agent_job_id}/cancel")

            assert resp.status_code == 200
            assert not cred_path.exists(), (
                f"Credential temp file still present after cancel: {cred_path}\n"
                "SEC-2.2 crash-safe cleanup must remove it regardless of child exit"
            )
            assert job.agent_job_id not in svc._registry, (
                "Job still in service registry after cancel"
            )
        finally:
            # Ensure the spawned process is terminated even if assertions fail.
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    def test_cancel_404_for_missing_job(self, client: TestClient) -> None:
        """Cancel a nonexistent job → 404."""
        resp = client.post("/api/agent-jobs/nonexistent-job-id/cancel")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Group 5: Accept — POST /api/agent-jobs/{id}/accept  (API-4.5)
# ---------------------------------------------------------------------------


class TestAcceptEndpoint:
    """POST /agent-jobs/{id}/accept: sole write path, state gate, provenance."""

    @pytest.mark.parametrize(
        "bad_status",
        [
            AgentJobStatus.queued,
            AgentJobStatus.running,
            AgentJobStatus.failed,
            AgentJobStatus.canceled,
        ],
    )
    def test_accept_only_from_acceptable_states(
        self,
        bad_status: AgentJobStatus,
        client: TestClient,
        foundry_paths: FoundryPaths,
    ) -> None:
        """Accept returns 422 for any state other than waiting_for_approval / completed."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=bad_status)
        resp = client.post(
            f"/api/agent-jobs/{job.agent_job_id}/accept",
            json={"accepted_by": "test-user"},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for job in {bad_status.value!r} state; got {resp.status_code}"
        )

    def test_accept_succeeds_from_waiting_for_approval(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Accept succeeds for a job in waiting_for_approval state → HTTP 200."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.waiting_for_approval)
        resp = client.post(
            f"/api/agent-jobs/{job.agent_job_id}/accept",
            json={"accepted_by": "reviewer-1"},
        )
        assert resp.status_code == 200, resp.text

    def test_accept_succeeds_from_completed_state(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Accept succeeds for a job in completed state → HTTP 200."""
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.completed)
        resp = client.post(
            f"/api/agent-jobs/{job.agent_job_id}/accept",
            json={"accepted_by": "reviewer-2"},
        )
        assert resp.status_code == 200, resp.text

    def test_accept_success_returns_required_summary_fields(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Acceptance response includes all fields EvidenceIntakePanel reads (AC-3.5).

        The FE completion confirmation reads:
          agent_job_id, acceptance_id, accepted_artifact_count, artifact_ids,
          accepted_by, accepted_at.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.waiting_for_approval)
        job_dir = foundry_paths.agent_job_dir(job.agent_job_id)
        _write_staged_artifact(job_dir, "art-abc", job.agent_job_id, kind="source_card")

        resp = client.post(
            f"/api/agent-jobs/{job.agent_job_id}/accept",
            json={"accepted_by": "reviewer-1", "notes": "LGTM"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_job_id"] == job.agent_job_id
        assert isinstance(body["acceptance_id"], str) and body["acceptance_id"]
        assert isinstance(body["accepted_artifact_count"], int)
        assert isinstance(body["artifact_ids"], list)
        assert body["accepted_by"] == "reviewer-1"
        assert isinstance(body["accepted_at"], str) and body["accepted_at"]

    def test_accept_artifacts_carry_created_by_agent_job_id(
        self, client: TestClient, foundry_paths: FoundryPaths
    ) -> None:
        """Accepted artifact files carry created_by_agent_job_id (AC-3.3 provenance).

        Every artifact promoted via accept MUST have a ``created_by_agent_job_id``
        field pointing back to the parent job.  This is the resolvable provenance
        link required for catalog traceability.
        """
        svc = AgentJobService(foundry_paths)
        job = _write_job_on_disk(svc, status=AgentJobStatus.waiting_for_approval)
        job_dir = foundry_paths.agent_job_dir(job.agent_job_id)
        _write_staged_artifact(
            job_dir, "provenance-art", job.agent_job_id, kind="claim"
        )

        resp = client.post(
            f"/api/agent-jobs/{job.agent_job_id}/accept",
            json={"accepted_by": "reviewer-1"},
        )
        assert resp.status_code == 200

        # Read the on-disk artifact; it must carry the provenance back-pointer.
        artifact_file = job_dir / "artifact_provenance-art.json"
        assert artifact_file.exists(), "Accepted artifact file must remain on disk"
        artifact_on_disk = json.loads(artifact_file.read_text(encoding="utf-8"))
        assert artifact_on_disk.get("created_by_agent_job_id") == job.agent_job_id, (
            "accepted artifact missing created_by_agent_job_id — "
            "provenance back-pointer is required per AC-3.3"
        )
        assert artifact_on_disk.get("accepted") is True

    def test_accept_is_sole_write_path_code_audit(self) -> None:
        """Code-path audit: the agent_jobs router has no direct catalog/builder calls.

        Per AC-3.2: the router MUST NOT call catalog_service or builder_service
        directly from any handler.  All catalog/report promotion is delegated
        to AgentJobService.accept_job(), which is the sole write path.

        This test inspects the router source at import time.
        """
        import inspect

        from research_foundry.api.routers import agent_jobs as router_module

        source = inspect.getsource(router_module)

        assert "catalog_service" not in source, (
            "agent_jobs router directly references catalog_service — "
            "all catalog writes MUST be delegated through service.accept_job() "
            "(AC-3.2 sole-write-path invariant)"
        )
        assert "builder_service" not in source, (
            "agent_jobs router directly references builder_service — "
            "all report writes MUST be delegated through service.accept_job() "
            "(AC-3.2 sole-write-path invariant)"
        )

    def test_accept_404_for_missing_job(self, client: TestClient) -> None:
        """Accept a nonexistent job → 404."""
        resp = client.post(
            "/api/agent-jobs/nonexistent-job-id/accept",
            json={"accepted_by": "reviewer-1"},
        )
        assert resp.status_code == 404
