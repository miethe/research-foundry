"""Phase 4 hardening tests for POST /api/runs/{run_id}/writeback/approve
(TEST-002..004 per docs/project_plans/implementation_plans/features/
runs-writeback-approve-dispatch-v1.md).

Gap analysis (do NOT duplicate — see that file's Phase 4 task table):
  - TEST-001 (RBAC on/off matrix) lives in ``test_writeback_router.py`` as
    ``TestWritebackApproveRBACEnforcementToggle`` — it manipulates
    ``app.state.rbac_enforced`` directly on an already-built app.
  - ``tests/test_writeback_router.py`` covers RBAC-by-role, governance_rejected
    mapping, one-audit-row-per-outcome, and actor identity threading — but
    ALWAYS with ``approve_and_dispatch`` mocked out via ``_PATCH_TARGET``.
  - ``tests/test_approve_and_dispatch.py`` covers ordering, per-target
    isolation, ``approved_by`` population, and ``overall_status``
    aggregation — but ONLY at the service layer (direct
    ``approve_and_dispatch()`` calls; no HTTP, no router, no RBAC, no audit
    wiring).

This file fills the remaining Phase 4 gap: the REAL
``approve_and_dispatch()`` (not mocked) driven end-to-end through
``TestClient.post()`` against a real, schema-backed run (mirrors the
``_build_run`` helper convention from ``test_approve_and_dispatch.py`` /
``test_writebacks.py``).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import writeback as writeback_module
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.governance import GuardResult, Violation
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Fixtures / helpers — mirrors test_writeback_router.py's _make_config and
# test_approve_and_dispatch.py's _build_run, combined so a real run can be
# driven through a real TestClient-backed HTTP stack.
# ---------------------------------------------------------------------------

_IDEA = (
    "Research how agentic research workflows should handle evidence bundles and "
    "claim traceability across cheap extraction and deep synthesis models. "
    "Studies show 40% of unsupported claims come from synthesis drift."
)

_SOURCE_TEXT = (
    "Evidence bundles let a research run carry its sources, claims, and a report "
    "in one auditable package. A 2025 study found that 40% of unsupported claims "
    "originate during synthesis when extraction and synthesis use different models. "
    "Claim ledgers reduce citation mismatch by mapping every material sentence to "
    "an evidence id. Limitations: small sample, single domain."
)


def _make_config(tmp_path: Path) -> FoundryConfig:
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:  # pragma: no cover
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)

    foundry_yaml_path = root / "foundry.yaml"
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict[str, Any] = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    return FoundryConfig(paths=FoundryPaths(root=root))


def _build_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    """Drive the deterministic pipeline and return the run_id (mirrors
    ``tests/test_approve_and_dispatch.py::_build_run``)."""

    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    assert tri.intent_id
    plan = plan_run(tri.intent_id, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / "input_source.txt"
    src_file.write_text(_SOURCE_TEXT, encoding="utf-8")
    ingest_source(
        str(src_file),
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        title="Evidence bundles and claim traceability",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Test middleware that injects a fixed AuthIdentity onto request.state."""

    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


def _make_client(cfg: FoundryConfig, identity: AuthIdentity | None = None) -> TestClient:
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


def _url(run_id: str) -> str:
    return f"/api/runs/{run_id}/writeback/approve"


_OWNER = AuthIdentity("owner_user", "ws1", ("owner",))

_AUDIT_TARGET = "research_foundry.api.routers.writeback.audit_service.record_event"


# ---------------------------------------------------------------------------
# TEST-002: ordering, driven end-to-end (approve_and_dispatch NOT mocked).
# ---------------------------------------------------------------------------

_GUARD_PASS = "pass"
_GUARD_BLOCK = "block"
_GUARD_HUMAN_REVIEW = "human_review"


def _forced_guard_result(kind: str) -> GuardResult | None:
    """None means "let the real guard_check run" (the pass case naturally
    passes for a personal-sensitivity run built via _build_run — see
    test_approve_and_dispatch.py's overall_status=="success" tests)."""

    if kind == _GUARD_PASS:
        return None
    if kind == _GUARD_BLOCK:
        return GuardResult(
            passed=False,
            exit_code=3,
            violations=[
                Violation(
                    rule_id="forced_block",
                    severity="block",
                    message="Forced block for TEST-002.",
                    detail="",
                )
            ],
        )
    if kind == _GUARD_HUMAN_REVIEW:
        return GuardResult(
            passed=False,
            exit_code=7,
            violations=[
                Violation(
                    rule_id="forced_human_review",
                    severity="require_approval",
                    message="Forced human-review for TEST-002.",
                    detail="",
                )
            ],
        )
    raise AssertionError(f"unknown guard kind: {kind}")  # pragma: no cover


@pytest.mark.parametrize(
    ("guard_kind", "expected_status", "expect_dispatch_called"),
    [
        (_GUARD_PASS, 200, True),
        (_GUARD_BLOCK, 422, False),
        (_GUARD_HUMAN_REVIEW, 400, False),
    ],
    ids=["pass", "block", "human_review"],
)
def test_guard_check_precedes_dispatch_through_real_http_stack(
    tmp_path, guard_kind, expected_status, expect_dispatch_called
):
    """TEST-002: with the REAL ``approve_and_dispatch`` running (no mocking of
    the orchestration primitive itself), drive a POST through the router and
    assert ``guard_check`` always runs before any of the three per-target
    dispatch primitives, across all three ``GuardResult`` outcome classes.

    For the two blocking outcomes there is nothing to "order" against — the
    combined gate must skip dispatch entirely — so the assertion there is the
    strongest form of ordering: the dispatch primitives are never invoked at
    all, even though ``guard_check`` was.
    """
    cfg = _make_config(tmp_path)
    run_id = _build_run(cfg.paths)
    client = _make_client(cfg, identity=_OWNER)

    call_order: list[str] = []
    forced = _forced_guard_result(guard_kind)

    orig_guard_check = writeback_module.governance.guard_check
    orig_emit_ccdash = writeback_module.telemetry.emit_ccdash_event
    orig_render_meatywiki = writeback_module._render_meatywiki
    orig_render_skillbom = writeback_module._render_skillbom

    def _spy_guard_check(ctx, *, paths=None):
        call_order.append("guard_check")
        if forced is not None:
            return forced
        return orig_guard_check(ctx, paths=paths)

    def _spy_emit_ccdash(run_id_arg, *, paths=None):
        call_order.append("emit_ccdash_event")
        return orig_emit_ccdash(run_id_arg, paths=paths)

    def _spy_render_meatywiki(rp, paths_arg, **kwargs):
        call_order.append("_render_meatywiki")
        return orig_render_meatywiki(rp, paths_arg, **kwargs)

    def _spy_render_skillbom(rp, paths_arg, **kwargs):
        call_order.append("_render_skillbom")
        return orig_render_skillbom(rp, paths_arg, **kwargs)

    with (
        patch.object(writeback_module.governance, "guard_check", side_effect=_spy_guard_check),
        patch.object(writeback_module.telemetry, "emit_ccdash_event", side_effect=_spy_emit_ccdash),
        patch.object(writeback_module, "_render_meatywiki", side_effect=_spy_render_meatywiki),
        patch.object(writeback_module, "_render_skillbom", side_effect=_spy_render_skillbom),
    ):
        resp = client.post(_url(run_id), json={})

    assert resp.status_code == expected_status
    assert "guard_check" in call_order

    dispatch_markers = ("emit_ccdash_event", "_render_meatywiki", "_render_skillbom")
    if expect_dispatch_called:
        guard_idx = call_order.index("guard_check")
        for marker in dispatch_markers:
            assert marker in call_order, f"{marker} was never called; order was {call_order}"
            assert guard_idx < call_order.index(marker), (
                f"guard_check (idx={guard_idx}) must precede {marker} "
                f"(idx={call_order.index(marker)}); order was {call_order}"
            )
    else:
        for marker in dispatch_markers:
            assert marker not in call_order, (
                f"{marker} must not be called when the combined gate blocks; "
                f"order was {call_order}"
            )


# ---------------------------------------------------------------------------
# TEST-003: idempotent re-invocation — two real sequential calls for the same
# run_id must overwrite stably, not regenerate/duplicate IDs or files.
# ---------------------------------------------------------------------------


def test_idempotent_reinvocation_ids_and_paths_stable(tmp_path):
    cfg = _make_config(tmp_path)
    run_id = _build_run(cfg.paths)
    rp = cfg.paths.run_paths(run_id)
    client = _make_client(cfg, identity=_OWNER)

    resp1 = client.post(_url(run_id), json={})
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["overall_status"] == "success"

    ccdash_event_1 = load_yaml(rp.ccdash_event)
    meatywiki_front_1, _ = load_md(rp.meatywiki_writeback)
    skillbom_front_1, _ = load_md(rp.skillbom_candidate)
    writebacks_files_1 = set(rp.writebacks.rglob("*"))

    # Second real, sequential invocation for the SAME run_id.
    resp2 = client.post(_url(run_id), json={})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["overall_status"] == "success"

    ccdash_event_2 = load_yaml(rp.ccdash_event)
    meatywiki_front_2, _ = load_md(rp.meatywiki_writeback)
    skillbom_front_2, _ = load_md(rp.skillbom_candidate)
    writebacks_files_2 = set(rp.writebacks.rglob("*"))

    # Bundle id (from build_bundle) is stable across both calls.
    assert body1["bundle_id"] == body2["bundle_id"]

    # Per-target IDs are stable — re-invocation overwrites in place rather
    # than minting new ids/files (ids.py mints are date+slug derived, not
    # random, and the run's title/intent do not change between calls).
    assert ccdash_event_1["event_id"] == ccdash_event_2["event_id"]
    assert meatywiki_front_1["id"] == meatywiki_front_2["id"]
    assert skillbom_front_1["id"] == skillbom_front_2["id"]

    # No new files appeared under writebacks/ on the second call — same set
    # of paths both times, i.e. genuinely overwritten, not duplicated.
    assert writebacks_files_2 == writebacks_files_1, (
        f"expected identical file set across both calls, "
        f"new files: {writebacks_files_2 - writebacks_files_1}"
    )


# ---------------------------------------------------------------------------
# TEST-004: exactly one real audit_service.record_event row for a genuine
# (unmocked) success path.
# ---------------------------------------------------------------------------


def test_real_success_path_records_exactly_one_audit_row(tmp_path):
    """TEST-004: with the REAL approve_and_dispatch running end-to-end (no
    mocking of the orchestration primitive), confirm exactly one real
    audit_service.record_event call lands — the router-level coverage in
    test_writeback_router.py::TestAuditOneRowPerOutcome only proves this
    holds when approve_and_dispatch is mocked; this proves it still holds
    when real code runs instead of a mock (no double-recording sneaking in
    from anywhere inside the real orchestration path).
    """
    cfg = _make_config(tmp_path)
    run_id = _build_run(cfg.paths)
    client = _make_client(cfg, identity=_OWNER)

    with patch(_AUDIT_TARGET) as mock_record:
        resp = client.post(_url(run_id), json={})

    assert resp.status_code == 200
    assert resp.json()["overall_status"] == "success"
    assert mock_record.call_count == 1
    event = mock_record.call_args[0][1]
    assert event.result == "success"
    assert event.mutation_type == "writeback"
    assert event.action == "approve_and_dispatch"
    assert event.target_ref == run_id
    assert event.actor_user_id == "owner_user"
