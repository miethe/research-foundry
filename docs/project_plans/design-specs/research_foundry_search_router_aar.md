---
schema_version: 0.1
id: aar-2026-06-21-search-router-mvp
type: after_action_review
title: AAR — Research Foundry Search Router MVP (autopilot build)
project: Research Foundry
owner: Nick Miethe
created_at: 2026-06-21
related:
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/project_plans/design-specs/research_foundry_search_router_implementation_plan.md
merge_commit: d119993
tags: [search-router, autopilot, ica-delegation, adversarial-review, aar]
---

# AAR — Research Foundry Search Router MVP

**What:** Built and squash-merged to `main` (`d119993`) the MVP of the Research Foundry Search
Router & Source Acquisition Layer from a 1,452-line ADR/spec, via `/autopilot`. Opus orchestrated;
all implementation was delegated to free-tier ICA (`claude-opus-4-8[1m]`) build waves, each gated
in-session.

## Outcome (what shipped)

- 3 JSON schemas (`search_request`, `search_run`, `tool_profile`) + routing foundation (provider
  contract/registry, modes, budgets, URL dedupe, authority ranking).
- 5 offline-degrading HTTP providers (brave/exa/jina/firecrawl/github), lazy `httpx` (optional
  extra), never raise on missing creds/network; jina+github keyless.
- Orchestrator + `rf search` / `rf extract` CLI, reusing existing `source_cards`/`telemetry`/
  writeback services under `runs/<run_id>/`; injection-risk flagging (spec section 15.1).
- Optional MCP server (lazy `mcp` extra); docs (architecture/providers/deployment/security +
  Claude Code web-search policy) + examples.
- **137 search-router + regression tests green; ruff + mypy clean on scope; zero new hard deps.**

## What went well

- **Scope discipline beat the spec.** The ADR prescribed Postgres/MinIO/Redis/OpenSearch/qdrant +
  many writebacks. Reading the codebase first revealed most concepts (source cards, claim ledger,
  CCDash telemetry, MeatyWiki/SkillBOM writebacks) **already exist as services**. The router
  collapsed to "new providers + routing + orchestrator reusing existing services" — a far smaller,
  coherent, file-backed MVP aligned with RF's "thin, file-backed, YAGNI" philosophy.
- **Wave structure + in-session gates.** Foundation -> providers -> orchestrator/CLI -> docs/MCP ->
  fixes. Re-running ruff/mypy/pytest in-session after every ICA wave caught the one regression
  (a hardcoded schema-count test) immediately and kept each commit green.
- **Offline-first testability.** Splitting each provider into a pure `_parse_*` (no httpx) and a
  lazy `_fetch` made the entire layer testable without httpx or API keys — the right call given no
  live keys were available.
- **Adversarial review earned its keep.** A dedicated read-only opus[1m] review delegate found
  three issues unit tests structurally could not: a `source_type` vocabulary mismatch silently
  ranking official docs at 0.40 instead of 0.95; `routing_decision.yaml` silently never written
  (missing required schema fields); and 0-indexed provider ranks sorting every provider's best hit
  last. All three passed the green test suite.

## What went wrong / friction

- **Flaky agent backends.** The in-session Agent (subagent) tool returned `529 Overloaded` twice up
  front; the first ICA call dropped ("Connection closed mid-response"). Mitigations: leaned on ICA
  (independent endpoint) for build waves; retried with `< /dev/null` to skip the stdin wait; added
  `--fallback-model`. After that, ICA was reliable for all five waves.
- **Spec/schema internal inconsistencies surfaced late.** The ADR's `source_type` enum (11.3),
  the `source_card` schema enum (`official_doc` singular), and the ranking weights (15.3,
  `official_docs` plural) used three different vocabularies — a latent correctness bug only the
  adversarial pass caught. Fixed by making `authority_score` tolerant of all vocabularies.
- **Forced schema reuse is awkward.** Reusing the swarm `routing_decision` schema (requires
  `intent_id`/`active_node_id`) for search runs required synthesizing those fields. Acceptable, but
  a search-specific routing record would have been cleaner.

## Lessons (systemic)

1. **For spec-driven builds, explore the codebase before planning.** The single highest-leverage
   move was discovering existing services, which cut the build by ~60% and avoided duplication.
2. **An adversarial review delegate is not optional for "looks green" code.** Three real bugs sat
   under 124 passing tests. Budget one read-only opus[1m] review pass per feature; treat its
   BLOCKER/MAJOR list as gating.
3. **ICA build-wave hygiene that worked:** `--bare --append-system-prompt-file CLAUDE.md`,
   `< /dev/null`, `--fallback-model`, one coherent wave per delegate (avoid `__init__.py` write
   races), and **re-run all gates in-session** — never trust the delegate's own green report.
4. **Distinguish pre-existing failures explicitly.** Confirmed all 13 full-suite failures
   (governance-guard subprocess "No module named research_foundry" = wrong-interpreter; export/
   sensitivity redaction; adapter env-coupling) exist on the untouched base `a442e33` — protecting
   the merge from a false regression signal.

## Follow-ups / deferred (next steps)

- **Live-provider validation** with real API keys (Brave/Exa/Jina/Firecrawl/GitHub) — the build is
  fully offline-validated only; first live run is the remaining step (cf. the NotebookLM/ARC pattern).
- **Unify the `source_type` vocabulary** across ADR 11.3, the `source_card` schema enum, and
  `ranking.py` (currently bridged by aliases).
- Deferred adapters: Serper/Tavily/Perplexity/Gemini/OpenAI-synthesis + academic
  (OpenAlex/Semantic Scholar/PubMed/arXiv); `crawl.site`; `monitoring_delta` skill-scout.
- Deferred infra: Postgres/MinIO/Redis/OpenSearch/qdrant; CCDash provider scorecard automation;
  full MCP harness integration + per-agent tokens.
- Pre-existing, unrelated test failures (governance-guard wrong-interpreter; export/sensitivity
  redaction) — worth a separate fix pass; not caused by this work.
