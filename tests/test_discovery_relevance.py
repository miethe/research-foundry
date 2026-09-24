"""M3b calibration coverage for discovery_relevance + swarm_drive._discover.

Fixture: tests/fixtures/m3b/discovery_fixture.json (two real L1/L2 runs whose
title-only discovery pulled 1990s newspaper OCR / export-control lists /
unrelated roadmaps). No network; the fixture freezes the live SearXNG hits
that were actually returned, each tagged with the query that retrieved it.
"""

from __future__ import annotations

import json
from pathlib import Path

from research_foundry.services.discovery_relevance import (
    brief_bigrams,
    brief_terms,
    build_queries,
    relevance,
)
from research_foundry.services.search_router.providers.base import ProviderResult, SearchHit
from research_foundry.services.swarm_drive import DriveContext, _discover
from research_foundry.yamlio import dump_yaml, load_yaml

_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "m3b" / "discovery_fixture.json").read_text()
)


def _title_objective(brief_md: str) -> tuple[str, str]:
    import re

    from research_foundry.frontmatter import split_frontmatter

    front, body = split_frontmatter(brief_md)
    title = front.get("title") if isinstance(front, dict) else ""
    m = re.search(r"\*\*Objective\.\*\*\s*(.*?)\n\s*\n", body or "", re.DOTALL)
    objective = m.group(1).strip() if m else ""
    return title or "", objective


def test_old_junk_candidates_are_off_topic():
    for name, case in _FIXTURE.items():
        title, objective = _title_objective(case["brief_md"])
        terms = brief_terms(title, objective)
        queries = build_queries(title, objective)
        query = queries[0] if queries else ""
        for cand in case["old_junk_candidates"]:
            verdict = relevance(cand, terms, query)
            assert not verdict["on_topic"], f"{name}: {cand['title']!r} should be off-topic"


def test_l1_build_queries_and_live_hits():
    case = _FIXTURE["l1_prior_art_evidence_for"]
    title, objective = _title_objective(case["brief_md"])
    queries = build_queries(title, objective)
    assert len(queries) >= 5
    assert any("nuclear waste warning" in q for q in queries)

    terms = brief_terms(title, objective)
    phrases = brief_bigrams(title, objective)
    on_topic_titles: set[str] = set()
    off_topic_titles: set[str] = set()
    for hit in case["live_searxng"]:
        verdict = relevance(hit, terms, hit["query"], phrases)
        if verdict["on_topic"]:
            on_topic_titles.add(hit["title"])
        else:
            off_topic_titles.add(hit["title"])

    assert len(on_topic_titles) >= 10
    assert "Long-term nuclear waste warning messages - Wikipedia" in on_topic_titles
    for t in on_topic_titles | off_topic_titles:
        if "Cypher" in t or "Voting rights" in t:
            assert t in off_topic_titles, f"{t!r} should be off-topic"


def test_l2_omega_centauri_off_topic():
    case = _FIXTURE["l2_bind_pass_1_results"]
    title, objective = _title_objective(case["brief_md"])
    terms = brief_terms(title, objective)
    phrases = brief_bigrams(title, objective)
    for hit in case["live_searxng"]:
        if "Omega Centauri" in hit["title"]:
            verdict = relevance(hit, terms, hit["query"], phrases)
            assert not verdict["on_topic"], f"{hit['title']!r} should be off-topic"


class _FixtureProvider:
    """Injected free_discovery provider returning fixture hits for any query."""

    id = "searxng"
    roles = ("discovery",)
    requires = ()
    env_keys = ()

    def __init__(self, hits: list[dict]) -> None:
        self._hits = [
            SearchHit(title=h["title"], url=h["url"], snippet=h.get("snippet"))
            for h in hits
        ]

    def available(self) -> bool:
        return True

    def search(self, query, *, max_results, constraints):
        return ProviderResult(
            provider=self.id, role="discovery", status="success",
            hits=list(self._hits[:max_results]), estimated_cost_usd=0.0,
        )

    def extract(self, urls):  # pragma: no cover
        return ProviderResult(provider=self.id, role="extraction", status="skipped")


def test_discover_writes_kept_and_rejected(tmp_foundry):
    from research_foundry.services import planning

    case = _FIXTURE["l1_prior_art_evidence_for"]
    intent = {
        "id": "intent_research_20260923_m3b_discover_test",
        "title": "Swarm drive demo topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Investigate the swarm-drive spine deterministically.",
        "governance": {
            "sensitivity": "personal",
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, tmp_foundry.intents_active / f"{intent['id']}.yaml")
    result = planning.plan_run(intent["id"], profile="personal", paths=tmp_foundry)
    run_id = result.run_id
    rp = tmp_foundry.run_paths(run_id)

    # Overwrite the generated brief with the real M3b L1 brief so the fixture's
    # live hits (tagged with their own retrieval queries) are exercised as-is.
    rp.research_brief.write_text(case["brief_md"], encoding="utf-8")

    provider = _FixtureProvider(case["live_searxng"])
    from research_foundry.config import FoundryConfig

    ctx = DriveContext(
        run_id=run_id,
        run_dir=rp.run,
        sensitivity="personal",
        llm_legs="none",
        objective=intent["objective"],
        roster_roles=(),
        model_profiles={},
        required_outputs=(),
    )
    n = _discover(
        ctx,
        rp,
        paths=tmp_foundry,
        config=FoundryConfig(paths=tmp_foundry),
        providers={"searxng": provider},
    )

    data = load_yaml(rp.source_candidates)
    kept = data["source_candidates"]
    rejected = data["rejected_candidates"]
    assert n == len(kept)
    assert kept, "expected at least one on-topic candidate"
    assert rejected, "expected at least one off-topic candidate"
    assert all(c["relevance"]["on_topic"] for c in kept)
    assert all(not c["relevance"]["on_topic"] for c in rejected)
    assert data["discovery"]["queries"]
    assert data["discovery"]["kept"] == len(kept)
    assert data["discovery"]["rejected"] == len(rejected)
