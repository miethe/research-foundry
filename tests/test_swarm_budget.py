"""Offline tests for the swarm-drive budget + turn-cap guards (E1-P2, SCHED-002).

Every test here is fully offline and makes **zero** model/network calls:

* the runtime breach is driven with an injected fake monotonic ``clock`` so the
  abort is deterministic without a wall-clock sleep;
* the cost breach is driven with an injected fake discovery provider carrying a
  nonzero ``estimated_cost_usd`` (no network);
* the ICA turn-cap + one-leg-per-source assertions read the emitted leg-request
  bundle (``--llm-legs ica`` — also zero model calls in rf).

Coverage maps to the SCHED-002 (rf side) contract:

* ``swarm_plan.budget.max_runtime_minutes`` breach -> clean abort + durable
  ``writebacks/budget_abort.yaml`` record + terminal ``status_derived ==
  "budget_exceeded"`` (never silently stuck).
* ``swarm_plan.budget.max_cost_usd`` breach -> same clean abort.
* the emitted ICA leg-request bundle carries the per-leg turn-cap ceiling.
* carding is strictly one leg per discovered source.
"""

from __future__ import annotations

from pathlib import Path

from research_foundry.paths import FoundryPaths
from research_foundry.services import (
    extraction,
    planning,
    source_cards,
    swarm_drive,
)
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.search_router.providers.base import (
    ProviderResult,
    SearchHit,
)
from research_foundry.services.swarm_drive import DriveState, drive_run
from research_foundry.yamlio import dump_yaml, load_yaml

_INTENT_ID = "intent_research_20260721_swarm_budget"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_intent(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    intent = {
        "id": _INTENT_ID,
        "title": "Swarm budget demo topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Exercise the swarm-drive budget/turn-cap guards.",
        "governance": {
            "sensitivity": sensitivity,
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{_INTENT_ID}.yaml")
    return _INTENT_ID


def _planned_run(paths: FoundryPaths) -> str:
    _write_intent(paths)
    return planning.plan_run(_INTENT_ID, profile="personal", paths=paths).run_id


def _set_budget(
    paths: FoundryPaths,
    run_id: str,
    *,
    max_runtime_minutes: float | None = None,
    max_cost_usd: float | None = None,
) -> None:
    """Patch the swarm_plan.budget ceilings on a planned run."""

    rp = paths.run_paths(run_id)
    plan = load_yaml(rp.swarm_plan)
    if max_runtime_minutes is not None:
        plan["budget"]["max_runtime_minutes"] = max_runtime_minutes
    if max_cost_usd is not None:
        plan["budget"]["max_cost_usd"] = max_cost_usd
    dump_yaml(plan, rp.swarm_plan)


def _seed_evidence(paths: FoundryPaths, run_id: str, tmp_path: Path) -> None:
    """Populate source card + extraction + claim ledger + empty candidates."""

    rp = paths.run_paths(run_id)
    doc = tmp_path / "evidence.txt"
    doc.write_text(
        "Latency dropped 30% with the new router.\n\n"
        "Teams report fewer escalations than before, according to the survey.\n\n"
        "Evidence bundles make claim traceability auditable end to end.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(str(doc), run_id=run_id, title="Evidence Source", paths=paths)
    extraction.extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=_INTENT_ID, paths=paths)
    dump_yaml({"source_candidates": []}, rp.source_candidates)


class _JumpClock:
    """A fake monotonic clock: 0.0 on first call, then a large constant.

    The guard reads the clock once at construction (start) and again on the
    first ``check`` — so the second read lands far past any tiny runtime cap.
    """

    def __init__(self, jump: float = 10_000.0) -> None:
        self._n = 0
        self._jump = jump

    def __call__(self) -> float:
        v = 0.0 if self._n == 0 else self._jump
        self._n += 1
        return v


class _CostlySearxProvider:
    """Injected free_discovery provider — no network, one hit, nonzero cost."""

    id = "searxng"
    roles = ("discovery",)
    requires = ()
    env_keys = ()

    def __init__(self, cost_usd: float) -> None:
        self._cost = cost_usd

    def available(self) -> bool:
        return True

    def search(self, query: str, *, max_results: int, constraints: dict) -> ProviderResult:
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=[SearchHit(title="Doc A", url="https://example.org/a", source_type="other")],
            estimated_cost_usd=self._cost,
        )

    def extract(self, urls: list[str]) -> ProviderResult:  # pragma: no cover
        return ProviderResult(provider=self.id, role="extraction", status="skipped")


class _FakeSearxProvider:
    """Injected free_discovery provider — no network, fixed hits, zero cost."""

    id = "searxng"
    roles = ("discovery",)
    requires = ()
    env_keys = ()

    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    def available(self) -> bool:
        return True

    def search(self, query: str, *, max_results: int, constraints: dict) -> ProviderResult:
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=list(self._hits[:max_results]),
            estimated_cost_usd=0.0,
        )

    def extract(self, urls: list[str]) -> ProviderResult:  # pragma: no cover
        return ProviderResult(provider=self.id, role="extraction", status="skipped")


# ---------------------------------------------------------------------------
# Runtime budget breach -> clean abort + report
# ---------------------------------------------------------------------------


def test_runtime_budget_breach_aborts_cleanly(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    _set_budget(tmp_foundry, run_id, max_runtime_minutes=0.001)
    rp = tmp_foundry.run_paths(run_id)

    state = drive_run(
        run_id,
        llm_legs="none",
        paths=tmp_foundry,
        providers={},
        clock=_JumpClock(),
    )

    # Clean terminal state — never a raised exception, never silently stuck.
    assert isinstance(state, DriveState)
    assert state.status_derived == "budget_exceeded"
    assert state.aborted is True
    assert state.abort_reason and "runtime" in state.abort_reason
    assert state.bundle_path is None
    # Aborted at the first checkpoint, before any dispatch.
    assert state.steps_run == ()
    assert not rp.evidence_bundle.exists()

    # Durable, machine-readable abort record was written (surfaces the breach).
    abort = load_yaml(rp.writebacks / "budget_abort.yaml")
    assert abort["kind"] == "runtime"
    assert abort["stage"] == "discovery"
    assert abort["status_derived"] == "budget_exceeded"
    assert abort["limit"] == 0.001


# ---------------------------------------------------------------------------
# Cost budget breach -> clean abort + report
# ---------------------------------------------------------------------------


def test_cost_budget_breach_aborts_cleanly(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    # Large runtime so only the cost ceiling can trip; tiny cost ceiling.
    _set_budget(tmp_foundry, run_id, max_runtime_minutes=60, max_cost_usd=0.01)
    rp = tmp_foundry.run_paths(run_id)

    providers = {"searxng": _CostlySearxProvider(cost_usd=5.0)}
    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers=providers)

    assert state.status_derived == "budget_exceeded"
    assert state.aborted is True
    assert state.abort_reason and "cost" in state.abort_reason
    assert state.bundle_path is None
    # Discovery incurred the cost; the guard tripped before ingest.
    assert "discovery" in state.steps_run
    assert "ingest" not in state.steps_run
    assert not any(rp.sources.glob("*.md")) if rp.sources.exists() else True

    abort = load_yaml(rp.writebacks / "budget_abort.yaml")
    assert abort["kind"] == "cost"
    assert abort["stage"] == "ingest"
    assert abort["observed"] >= 5.0
    assert abort["limit"] == 0.01


def test_ica_path_cost_breach_aborts_before_emit(tmp_foundry):
    """The ICA emit path is gated by the same budget guard as `none`."""

    run_id = _planned_run(tmp_foundry)
    _set_budget(tmp_foundry, run_id, max_runtime_minutes=60, max_cost_usd=0.01)
    rp = tmp_foundry.run_paths(run_id)

    providers = {"searxng": _CostlySearxProvider(cost_usd=5.0)}
    state = drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers=providers)

    assert state.status_derived == "budget_exceeded"
    assert state.aborted is True
    assert state.leg_bundle is None
    # No leg-request bundle emitted — the guard tripped before emit_legs.
    assert not (rp.run / "leg_requests.yaml").exists()
    assert (rp.writebacks / "budget_abort.yaml").exists()


# ---------------------------------------------------------------------------
# Normal budget -> full drive, no abort (guard is a true no-op)
# ---------------------------------------------------------------------------


def test_normal_budget_reaches_bundle(tmp_foundry, tmp_path):
    run_id = _planned_run(tmp_foundry)  # default budget: 60min / $5
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})

    assert state.status_derived == "bundle_written"
    assert state.aborted is False
    assert state.abort_reason is None
    assert not (tmp_foundry.run_paths(run_id).writebacks / "budget_abort.yaml").exists()


def test_absent_budget_is_unbounded(tmp_foundry, tmp_path):
    """A swarm_plan with no budget ceilings never trips the guard."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    plan = load_yaml(rp.swarm_plan)
    plan["budget"] = {}  # no max_runtime_minutes / max_cost_usd
    dump_yaml(plan, rp.swarm_plan)
    _seed_evidence(tmp_foundry, run_id, tmp_path)

    state = drive_run(run_id, llm_legs="none", paths=tmp_foundry, providers={})
    assert state.status_derived == "bundle_written"
    assert state.aborted is False


# ---------------------------------------------------------------------------
# ICA turn-cap constraint emitted in the leg-request bundle
# ---------------------------------------------------------------------------


def test_turn_cap_constraint_in_emitted_bundle(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    hits = [
        SearchHit(title="Doc A", url="https://example.org/a", source_type="official_docs"),
        SearchHit(title="Doc B", url="https://example.org/b", source_type="reputable_news"),
    ]
    providers = {"searxng": _FakeSearxProvider(hits)}

    state = drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers=providers)

    assert state.status_derived == "awaiting_legs"
    b = state.leg_bundle
    ceiling = swarm_drive._ICA_TURN_CAP_CEILING
    # Band ceiling is within the 100–120 turns/leg contract.
    assert 100 <= ceiling <= 120
    # Bundle-level cap present.
    assert b["turn_cap_per_leg"] == ceiling
    # Every leg (carding + claim_map) carries the per-leg ceiling.
    for leg in b["legs"]:
        assert leg["max_turns"] == ceiling
        assert leg["max_turns"] <= 120

    # The on-disk copy carries the constraint too.
    disk = load_yaml(tmp_foundry.run_paths(run_id).run / "leg_requests.yaml")
    assert disk["turn_cap_per_leg"] == ceiling
    assert all(leg["max_turns"] == ceiling for leg in disk["legs"])


# ---------------------------------------------------------------------------
# Carding is strictly one leg per discovered source
# ---------------------------------------------------------------------------


def test_carding_one_leg_per_source(tmp_foundry):
    run_id = _planned_run(tmp_foundry)
    hits = [
        SearchHit(title="Doc A", url="https://example.org/a", source_type="official_docs"),
        SearchHit(title="Doc B", url="https://example.org/b", source_type="reputable_news"),
        SearchHit(title="Doc C", url="https://example.org/c", source_type="blog_or_forum"),
    ]
    providers = {"searxng": _FakeSearxProvider(hits)}

    state = drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers=providers)

    legs = state.leg_bundle["legs"]
    carding = [leg for leg in legs if leg["leg_type"] == swarm_drive._LEG_CARDING]
    # Exactly one carding leg per discovered source, in order.
    assert [leg["id"] for leg in carding] == ["carding-1", "carding-2", "carding-3"]
    # Each carding leg references exactly one distinct source locator.
    locators = [leg["source_ref"]["locator"] for leg in carding]
    assert locators == [
        "https://example.org/a",
        "https://example.org/b",
        "https://example.org/c",
    ]
    assert len(set(locators)) == len(carding)


def test_carding_skips_sources_without_locator(tmp_foundry):
    """One-leg-per-*cardable*-source: locator-less candidates are skipped."""

    run_id = _planned_run(tmp_foundry)
    rp = tmp_foundry.run_paths(run_id)
    # Pre-seed candidates directly (discovery is then a no-op): one lacks a url.
    dump_yaml(
        {
            "source_candidates": [
                {"title": "Has URL", "url": "https://example.org/a", "source_type": "other"},
                {"title": "No URL", "source_type": "other"},
                {"title": "Also URL", "url": "https://example.org/c", "source_type": "other"},
            ]
        },
        rp.source_candidates,
    )

    state = drive_run(run_id, llm_legs="ica", paths=tmp_foundry, providers={})

    carding = [
        leg for leg in state.leg_bundle["legs"]
        if leg["leg_type"] == swarm_drive._LEG_CARDING
    ]
    # Two cardable sources -> two carding legs (the locator-less one is skipped).
    assert [leg["id"] for leg in carding] == ["carding-1", "carding-2"]
    assert [leg["source_ref"]["locator"] for leg in carding] == [
        "https://example.org/a",
        "https://example.org/c",
    ]
