"""Tests for the canonical swarm-adapter service (OPM-3.2, spec §10.6).

Every test is self-contained (no cross-test-module imports, per repo
convention) and fully offline: the registered adapters run in degraded mode
(no optional deps installed in this environment), so nothing here makes a
network or model call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from research_foundry import adapters
from research_foundry.adapters.base import AdapterResult
from research_foundry.paths import FoundryPaths
from research_foundry.services import planning
from research_foundry.services import swarm_service as svc
from research_foundry.yamlio import dump_yaml, load_yaml

_INTENT_ID = "intent_research_20260730_swarmsvc"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_intent(paths: FoundryPaths) -> str:
    intent = {
        "id": _INTENT_ID,
        "title": "Swarm service unit topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Exercise the canonical swarm-adapter service.",
        "governance": {
            "sensitivity": "personal",
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")
    return _INTENT_ID


def _planned_run(paths: FoundryPaths) -> str:
    _write_intent(paths)
    result = planning.plan_run(_INTENT_ID, profile="personal", paths=paths)
    return result.run_id


def _legacy_swarm_run(
    paths: FoundryPaths,
    run_id: str,
    adapter_ids: list[str],
    *,
    profile: str = "personal",
) -> dict[str, Any]:
    """Literal re-implementation of the pre-OPM-3.2 inline CLI algorithm.

    Copied verbatim (minus the Typer/console concerns) from the removed body
    of ``cli_commands.swarm_run`` (lines 780-791 on base ``65d658d``) so the
    parity test compares the new service against the *exact* old behaviour,
    not against itself.
    """

    from research_foundry.frontmatter import load_md

    rp = paths.run_paths(run_id)
    brief = load_md(rp.research_brief)[0] if rp.research_brief.exists() else {}
    candidates: list[dict] = []
    for aid in adapter_ids:
        ad = adapters.get_adapter(aid)
        if ad is None:
            continue
        res = ad.run({"brief": brief, "profile": profile})
        candidates.extend(res.source_candidates)
    dump_yaml({"source_candidates": candidates}, rp.source_candidates)
    return load_yaml(rp.source_candidates)


class _RaisingAdapter:
    """A registered-shaped adapter whose ``run`` always raises."""

    id = "raising_test_adapter"
    requires: tuple[str, ...] = ()

    def available(self) -> bool:
        return True

    def run(self, request: dict[str, Any]) -> AdapterResult:
        raise RuntimeError("boom: simulated adapter failure")


# ---------------------------------------------------------------------------
# CLI parity (requirement 3)
# ---------------------------------------------------------------------------


def test_cli_parity_matches_legacy_inline_algorithm(tmp_foundry: FoundryPaths):
    adapters.load_all()
    run_id = _planned_run(tmp_foundry)
    wanted = ["gpt_researcher", "paperqa2"]

    legacy = _legacy_swarm_run(tmp_foundry, run_id, list(wanted))

    result = svc.run_swarm(run_id, wanted, profile="personal", dry_run=False, paths=tmp_foundry)
    written = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)

    assert written == legacy
    assert list(result.source_candidates) == legacy["source_candidates"]
    # Sanity: the fixture brief actually produced a non-trivial candidate so
    # this is a real parity check, not two empty lists agreeing vacuously.
    assert len(legacy["source_candidates"]) >= 1


# ---------------------------------------------------------------------------
# Closed dispatch: unknown vs. known-but-not-allowed (requirement 2)
# ---------------------------------------------------------------------------


def test_unknown_adapter_denied_distinctly_and_never_dispatched(tmp_foundry: FoundryPaths):
    registry = adapters.load_all()
    run_id = _planned_run(tmp_foundry)

    spies = {}
    for adapter_id, instance in registry.items():
        mock_run = MagicMock(wraps=instance.run)
        spies[adapter_id] = mock_run
        instance.run = mock_run  # type: ignore[method-assign]

    result = svc.run_swarm(
        run_id, ["definitely_unknown_adapter_id"], profile="personal", dry_run=False, paths=tmp_foundry
    )

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.ran is False
    assert outcome.denial is not None
    assert outcome.denial.reason == svc.DENIAL_UNKNOWN_ADAPTER
    assert outcome.error is None
    assert result.source_candidates == ()
    for adapter_id, mock_run in spies.items():
        mock_run.assert_not_called()


def test_known_but_not_allowlisted_denied_distinctly_and_never_dispatched(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
):
    registry = adapters.load_all()
    assert "opencode" in registry  # known to the discovery registry
    run_id = _planned_run(tmp_foundry)

    # Policy allowlist temporarily narrowed: opencode is registered but not
    # cleared -- the "known but not allowed" case the unknown-adapter test
    # above cannot exercise (today's allowlist == today's full registry).
    monkeypatch.setattr(svc, "ALLOWED_ADAPTER_IDS", frozenset(svc.ALLOWED_ADAPTER_IDS - {"opencode"}))

    mock_run = MagicMock(wraps=registry["opencode"].run)
    registry["opencode"].run = mock_run  # type: ignore[method-assign]

    result = svc.run_swarm(run_id, ["opencode"], profile="personal", dry_run=False, paths=tmp_foundry)

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.ran is False
    assert outcome.denial is not None
    assert outcome.denial.reason == svc.DENIAL_NOT_ALLOWLISTED
    assert outcome.error is None
    mock_run.assert_not_called()


def test_unknown_and_disallowed_reasons_are_distinct():
    assert svc.DENIAL_UNKNOWN_ADAPTER != svc.DENIAL_NOT_ALLOWLISTED


def test_no_fail_open_on_bogus_or_empty_adapter_id(tmp_foundry: FoundryPaths):
    """Neither an unrecognised id nor an empty string is ever dispatched."""

    adapters.load_all()
    run_id = _planned_run(tmp_foundry)

    result = svc.run_swarm(
        run_id, ["", "  ", "totally-made-up"], profile="personal", dry_run=False, paths=tmp_foundry
    )

    assert result.source_candidates == ()
    assert all(o.ran is False for o in result.outcomes)
    assert all(o.denial is not None for o in result.outcomes)


# ---------------------------------------------------------------------------
# Dry-run zero effects (requirement 4)
# ---------------------------------------------------------------------------


def test_dry_run_performs_zero_adapter_and_write_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
):
    registry = adapters.load_all()
    run_id = _planned_run(tmp_foundry)

    write_spy = MagicMock(wraps=dump_yaml)
    monkeypatch.setattr(svc, "dump_yaml", write_spy)

    run_spies = {}
    for adapter_id, instance in registry.items():
        mock_run = MagicMock(wraps=instance.run)
        run_spies[adapter_id] = mock_run
        instance.run = mock_run  # type: ignore[method-assign]

    pre_candidates_exists = tmp_foundry.run_paths(run_id).source_candidates.exists()

    result = svc.run_swarm(
        run_id, ["gpt_researcher", "paperqa2"], profile="personal", dry_run=True, paths=tmp_foundry
    )

    assert result.dry_run is True
    assert result.wrote_candidates is False
    assert result.source_candidates_path is None
    assert result.outcomes == ()
    assert result.source_candidates == ()
    write_spy.assert_not_called()
    for adapter_id, mock_run in run_spies.items():
        mock_run.assert_not_called()
    # The write-effect assertion above already proves no file was written;
    # this restates it at the filesystem level for a second, independent check.
    assert tmp_foundry.run_paths(run_id).source_candidates.exists() == pre_candidates_exists


# ---------------------------------------------------------------------------
# Degraded/failing adapters stay typed (requirement 6)
# ---------------------------------------------------------------------------


def test_raising_adapter_is_reported_as_typed_error_not_raised(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
):
    adapters.load_all()
    run_id = _planned_run(tmp_foundry)

    raising = _RaisingAdapter()
    monkeypatch.setattr(svc, "ALLOWED_ADAPTER_IDS", svc.ALLOWED_ADAPTER_IDS | {raising.id})
    monkeypatch.setattr(
        svc,
        "get_adapter",
        lambda aid: raising if aid == raising.id else adapters.get_adapter(aid),
    )

    result = svc.run_swarm(run_id, [raising.id], profile="personal", dry_run=False, paths=tmp_foundry)

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.ran is False
    assert outcome.denial is None
    assert outcome.error is not None
    assert "RuntimeError" in outcome.error
    assert "boom" in outcome.error
    # No raw traceback -- a bounded, single-line description only.
    assert "\n" not in outcome.error
    # The write still happens (an errored adapter degrades the run, it
    # doesn't abort persistence of the other candidates).
    written = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)
    assert written == {"source_candidates": []}


# ---------------------------------------------------------------------------
# Import cleanliness (requirement 5)
# ---------------------------------------------------------------------------


def test_module_source_has_no_serve_extra_or_typer_import():
    module_path = Path(svc.__file__)
    source = module_path.read_text(encoding="utf-8")
    for banned in ("import typer", "import fastapi", "import uvicorn", "from fastapi", "from uvicorn"):
        assert banned not in source, f"swarm_service.py must not import {banned!r}"
