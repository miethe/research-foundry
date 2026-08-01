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
from research_foundry.services.operator_mcp_policy import (
    _ERROR_DETAIL_MAX,
    _UNSAFE_DETAIL_MARKER,
)
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


class _MessageRaisingAdapter:
    """A registered-shaped adapter whose ``run`` always raises a
    caller-supplied exception (D2 tests: prove specific unsafe shapes get
    bounded/redacted, not just that SOME error string comes back)."""

    id = "message_raising_test_adapter"
    requires: tuple[str, ...] = ()

    def __init__(self, message: str) -> None:
        self._message = message

    def available(self) -> bool:
        return True

    def run(self, request: dict[str, Any]) -> AdapterResult:
        raise RuntimeError(self._message)


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
# P3-F1: dry run still validates and denies (intersection of requirements
# 2 and 4 -- the gap the original mutation matrix missed because each guard
# was verified only against its OWN test, never their intersection)
# ---------------------------------------------------------------------------


def test_dry_run_still_denies_unknown_and_not_allowlisted_adapters_with_zero_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P3-F1 fix, proven precisely: `run_swarm(..., dry_run=True)` for a
    request mixing a valid adapter with an unknown one and a known-but-not-
    allowlisted one still records BOTH denials (never silently swallowed by
    the dry-run short-circuit) while performing ZERO dispatch/write effects
    for ANY id, valid or not -- a spy on both `adapter.run` and `dump_yaml`
    proves neither is ever called, for either the denied ids or the one
    valid id in the same request."""

    registry = adapters.load_all()
    run_id = _planned_run(tmp_foundry)
    monkeypatch.setattr(svc, "ALLOWED_ADAPTER_IDS", svc.ALLOWED_ADAPTER_IDS - {"opencode"})
    assert "opencode" in registry  # known to the registry, but now disallowed above

    write_spy = MagicMock(wraps=dump_yaml)
    monkeypatch.setattr(svc, "dump_yaml", write_spy)

    run_spies = {}
    for adapter_id, instance in registry.items():
        mock_run = MagicMock(wraps=instance.run)
        run_spies[adapter_id] = mock_run
        instance.run = mock_run  # type: ignore[method-assign]

    result = svc.run_swarm(
        run_id,
        ["gpt_researcher", "definitely_unknown_adapter_id", "opencode"],
        profile="personal",
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.dry_run is True
    assert result.wrote_candidates is False
    assert result.source_candidates_path is None
    assert result.source_candidates == ()
    write_spy.assert_not_called()
    for adapter_id, mock_run in run_spies.items():
        mock_run.assert_not_called()

    # The two invalid ids ARE denied -- P3-F1's own fix -- while the one
    # valid id records no outcome at all (the pre-existing, still-correct
    # dry-run contract for a VALID id: see
    # test_dry_run_performs_zero_adapter_and_write_effects above).
    by_id = {o.adapter_id: o for o in result.outcomes}
    assert set(by_id) == {"definitely_unknown_adapter_id", "opencode"}
    assert by_id["definitely_unknown_adapter_id"].denial.reason == svc.DENIAL_UNKNOWN_ADAPTER
    assert by_id["opencode"].denial.reason == svc.DENIAL_NOT_ALLOWLISTED
    assert all(o.ran is False for o in result.outcomes)


# ---------------------------------------------------------------------------
# merge_with_existing (OPM-3.3's own non-duplication dependency)
# ---------------------------------------------------------------------------


def test_merge_with_existing_false_is_the_unchanged_default_overwrite_behaviour(
    tmp_foundry: FoundryPaths,
) -> None:
    """Default (`merge_with_existing=False`, every pre-existing caller
    including the CLI): a second call REPLACES the file, it does not add to
    it -- proves this task's new parameter changed nothing observable for
    any caller that does not opt in."""

    run_id = _planned_run(tmp_foundry)

    svc.run_swarm(run_id, ["gpt_researcher"], profile="personal", dry_run=False, paths=tmp_foundry)
    first = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)
    assert len(first["source_candidates"]) >= 1

    svc.run_swarm(run_id, ["paperqa2"], profile="personal", dry_run=False, paths=tmp_foundry)
    second = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)

    # paperqa2's own candidates only -- gpt_researcher's are GONE (overwritten).
    assert second["source_candidates"] != first["source_candidates"]


def test_merge_with_existing_true_appends_across_calls_without_duplicating(
    tmp_foundry: FoundryPaths,
) -> None:
    """`merge_with_existing=True` (OPM-3.3's own per-adapter dispatch
    pattern): calling `run_swarm` twice, once per adapter, each with a
    single-element list, accumulates BOTH adapters' candidates in the file
    -- neither call's candidates are lost, and neither is counted twice."""

    run_id = _planned_run(tmp_foundry)

    first = svc.run_swarm(
        run_id, ["gpt_researcher"], profile="personal", dry_run=False, paths=tmp_foundry, merge_with_existing=True
    )
    persisted_after_first = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)
    assert persisted_after_first["source_candidates"] == list(first.source_candidates)

    second = svc.run_swarm(
        run_id, ["paperqa2"], profile="personal", dry_run=False, paths=tmp_foundry, merge_with_existing=True
    )
    persisted_after_second = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)

    # SwarmRunResult.source_candidates always describes only THIS call.
    assert second.source_candidates != first.source_candidates
    # The FILE holds both, in order, exactly once each -- no loss, no dupes.
    assert persisted_after_second["source_candidates"] == [
        *persisted_after_first["source_candidates"],
        *second.source_candidates,
    ]
    assert len(persisted_after_second["source_candidates"]) == len(persisted_after_first["source_candidates"]) + len(
        second.source_candidates
    )


def test_merge_with_existing_true_survives_a_corrupt_prior_file(
    tmp_foundry: FoundryPaths,
) -> None:
    """A malformed pre-existing `source_candidates.yaml` (e.g. truncated by
    a prior crash) never raises out of `run_swarm` -- it is treated as an
    empty prior list (logged, not fatal), so this call's own candidates are
    still durably persisted."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    rp.source_candidates.write_text("{not: valid: yaml: [", encoding="utf-8")

    result = svc.run_swarm(
        run_id, ["gpt_researcher"], profile="personal", dry_run=False, paths=tmp_foundry, merge_with_existing=True
    )

    persisted = load_yaml(rp.source_candidates)
    assert persisted["source_candidates"] == list(result.source_candidates)


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
# D2 (P3 cross-model audit finding): adapter exception text must be bounded
# AND redacted, not merely non-raising and single-line (the assertions
# above prove "no traceback" -- these prove the SPECIFIC unsafe shapes
# AC OPM-7 cares about: an embedded path, and an unbounded length).
# ---------------------------------------------------------------------------


def _dispatch_single_raising_adapter(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, message: str
) -> str:
    """Shared plumbing for the two D2 tests below: register one
    ``_MessageRaisingAdapter`` as the sole allowlisted/known adapter for
    this call and dispatch it, returning the resulting ``outcome.error``.
    """

    adapters.load_all()
    run_id = _planned_run(tmp_foundry)

    raising = _MessageRaisingAdapter(message)
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
    return outcome.error


def test_adapter_exception_embedding_a_filesystem_path_is_fully_redacted(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D2's empirical repro shape, same as BLOCK-1's (round 4 gate) own
    `build_audit_delivery` repro: a bare ``OSError``/``PermissionError``-
    style message embeds an absolute filesystem path with NO traceback
    framing at all. Before this fix, `f"{type(exc).__name__}: {exc}"` put
    that path straight into `AdapterOutcome.error`, unredacted -- an MCP
    caller reading a `job.status`/dry-run denial listing could learn a
    workspace-local filesystem layout, or (for a credential-file read
    failure) a path that itself names a secret. The WHOLE string must be
    replaced by `_UNSAFE_DETAIL_MARKER`, per `_redact_and_bound`'s own
    "never a partial per-match substitution" contract -- not just the path
    span."""

    secret_path = "/Users/alice/.config/research-foundry/serve.env"
    error = _dispatch_single_raising_adapter(
        tmp_foundry,
        monkeypatch,
        f"[Errno 2] No such file or directory: '{secret_path}'",
    )

    assert error == _UNSAFE_DETAIL_MARKER
    assert secret_path not in error
    assert "alice" not in error
    assert "PermissionError" not in error and "OSError" not in error


def test_adapter_exception_message_is_length_bounded(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An adapter's exception `str()` is unbounded by construction (it can
    embed arbitrarily large caller/environment-influenced text, e.g. a
    reflected request body). `AdapterOutcome.error` must never exceed
    `operator_mcp_policy._ERROR_DETAIL_MAX` (the SAME bound `build_error`'s
    own `detail` field enforces) -- an MCP response is not the place for an
    unbounded string, capped or not."""

    huge_message = "boom " * 400  # 2000 chars, well past the 500-char bound
    assert len(huge_message) > _ERROR_DETAIL_MAX

    error = _dispatch_single_raising_adapter(tmp_foundry, monkeypatch, huge_message)

    assert len(error) <= _ERROR_DETAIL_MAX


def test_adapter_exception_ordinary_message_still_survives_unredacted(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-regression companion to the two tests above: an ordinary,
    non-path, non-traceback, well-under-the-bound message (the SAME shape
    `test_raising_adapter_is_reported_as_typed_error_not_raised` already
    pins) still comes back intact, type name and all -- D2's fix must not
    turn every adapter error into the unsafe-content marker."""

    error = _dispatch_single_raising_adapter(
        tmp_foundry, monkeypatch, "simulated adapter failure, ordinary message"
    )

    assert error == "RuntimeError: simulated adapter failure, ordinary message"
    assert error != _UNSAFE_DETAIL_MARKER


# ---------------------------------------------------------------------------
# Import cleanliness (requirement 5)
# ---------------------------------------------------------------------------


def test_module_source_has_no_serve_extra_or_typer_import():
    module_path = Path(svc.__file__)
    source = module_path.read_text(encoding="utf-8")
    for banned in ("import typer", "import fastapi", "import uvicorn", "from fastapi", "from uvicorn"):
        assert banned not in source, f"swarm_service.py must not import {banned!r}"


def test_module_imports_cleanly_with_the_serve_extra_unavailable():
    """Runtime companion to the source-text check above (D2 regression
    guard): this task added `swarm_service`'s first import FROM
    `operator_mcp_policy` (for `_redact_and_bound`) -- a source-text scan of
    `swarm_service.py` itself cannot catch a `fastapi`/`typer`/`starlette`
    import newly introduced TRANSITIVELY through that (or any future)
    import. Actually blocks those three modules at `sys.meta_path` and
    forces a fresh import of both `swarm_service` and `operator_mcp_policy`
    to prove the module docstring's "must import cleanly in a bare install"
    claim at runtime, not just by grepping this one file's own source.
    """

    import importlib
    import sys

    banned_roots = {"fastapi", "starlette", "uvicorn", "typer"}

    class _Blocker:
        def find_module(self, name, path=None):  # noqa: ANN001 - importlib protocol
            if name.split(".")[0] in banned_roots:
                raise ImportError(f"blocked for this test: {name}")
            return None

    saved_modules = {
        name: mod
        for name, mod in sys.modules.items()
        if name == "research_foundry.services.swarm_service"
        or name.startswith("research_foundry.services.swarm_service.")
        or name == "research_foundry.services.operator_mcp_policy"
    }
    for name in saved_modules:
        del sys.modules[name]

    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    try:
        reimported = importlib.import_module("research_foundry.services.swarm_service")
        assert reimported.run_swarm is not None
    finally:
        sys.meta_path.remove(blocker)
        for name in list(sys.modules):
            if name == "research_foundry.services.swarm_service" or name == "research_foundry.services.operator_mcp_policy":
                del sys.modules[name]
        sys.modules.update(saved_modules)
        importlib.import_module("research_foundry.services.swarm_service")
