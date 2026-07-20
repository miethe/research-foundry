---
schema_version: 2
doc_type: implementation_plan
id: impl-plan-2026-07-20-search-router-gaps-aos-web
title: "Search Router — Gap-Closing + aos-web/SearXNG Discovery Lane (v1)"
project: Research Foundry
status: completed
owner: Nick Miethe
created_at: 2026-07-20
updated_at: 2026-07-20
feature_slug: search-router-gaps-aos-web
source_spec: docs/project_plans/design-specs/research_foundry_search_router_spec.md
source_plan: docs/project_plans/design-specs/research_foundry_search_router_implementation_plan.md
source_aar: docs/project_plans/design-specs/research_foundry_search_router_aar.md
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE
intenttree_nodes:
  - node_01KX1GJX7C350RQ78GQX218W7B  # aos-web/SearXNG discovery lane (primary)
  - node_01KXRSH57ZYN36XK7HFAVNYP6E  # P3 CCDash + SkillMeat
  - node_01KXRSH1CFYDAC6NV0QZ0WF2S4  # P2 MCP/harness (finishing)
tier: 3
tags: [search-router, aos-web, searxng, ccdash, skillmeat, mcp, discovery-adapter]

wave_plan:
  orchestrator_model: opus-4-8
  execution_model: workflow
  # Git model: single feature branch off local HEAD, isolation:shared, Opus squashes to main.
  # No phase is Mode D. Reviewer gate per phase; end-of-feature gate = karen (tier3) on wave-4.
  waves:
    - id: wave-1
      title: "aos-web/SearXNG free discovery lane"
      phases:
        - id: phase-1
          title: "SearXNG provider + free-lane mode + offline tests + docs"
          mode: C
          isolation: shared
          review_intensity: standard
          phase_strategy: static
          fix_agent: python-backend-engineer
          # Two serial batches → no concurrent committers on the shared tree.
          batches:
            - ["TASK-1.1"]
            - ["TASK-1.3"]
          tasks:
            - id: TASK-1.1
              assigned_to: python-backend-engineer
              model: sonnet
              effort: 5
              files_affected:
                - src/research_foundry/services/search_router/providers/searxng.py
                - src/research_foundry/services/search_router/providers/__init__.py
                - src/research_foundry/services/search_router/modes.py
                - tests/test_search_router_searxng.py
                - tests/test_search_router_providers.py
                - tests/test_search_router_foundation.py
            - id: TASK-1.3
              assigned_to: documentation-writer
              model: sonnet
              effort: 1
              files_affected:
                - docs/dev/architecture/search-router/provider_profiles.md
                - docs/dev/architecture/search-router/architecture.md
    - id: wave-2
      title: "P3 — CCDash search telemetry correctness"
      phases:
        - id: phase-2
          title: "emit search metrics; compute useful_source_count/citation_coverage; populate ccdash_event_id"
          mode: C
          isolation: shared
          review_intensity: standard
          phase_strategy: static
          fix_agent: python-backend-engineer
          tasks:
            - id: TASK-2.1
              assigned_to: python-backend-engineer
              model: sonnet
              effort: 5
              files_affected:
                - src/research_foundry/services/telemetry.py
                - schemas/ccdash_event.schema.yaml
                - src/research_foundry/services/search_router/router.py
                - tests/test_search_router_router.py
                - tests/test_telemetry.py
    - id: wave-3
      title: "P3 — SkillMeat artifacts + writeback + provider scorecard"
      phases:
        - id: phase-3
          title: "tool-profiles + SkillBOM; router→SkillMeat writeback; per-provider scorecard rollup"
          mode: C
          isolation: shared
          review_intensity: standard
          phase_strategy: static
          fix_agent: python-backend-engineer
          batches:
            - ["TASK-3.1"]
            - ["TASK-3.2"]
          tasks:
            - id: TASK-3.1
              assigned_to: python-backend-engineer
              model: sonnet
              effort: 3
              files_affected:
                - skillmeat/tool_profiles/brave_search_v1.yaml
                - skillmeat/tool_profiles/exa_search_v1.yaml
                - skillmeat/tool_profiles/jina_reader_v1.yaml
                - skillmeat/tool_profiles/firecrawl_v1.yaml
                - skillmeat/tool_profiles/github_discovery_v1.yaml
                - skillmeat/skillboms/skill_source_discovery_v1.md
            - id: TASK-3.2
              assigned_to: python-backend-engineer
              model: sonnet
              effort: 5
              files_affected:
                - src/research_foundry/services/search_router/router.py
                - src/research_foundry/services/telemetry.py
                - tests/test_search_router_scorecard.py
    - id: wave-4
      title: "P2 — MCP finishing pass"
      phases:
        - id: phase-4
          title: "named MCP presets; naming reconcile; .mcp.json; MCP test coverage"
          mode: C
          isolation: shared
          review_intensity: tier3   # end-of-feature gate → karen
          phase_strategy: static
          fix_agent: python-backend-engineer
          tasks:
            - id: TASK-4.1
              assigned_to: python-backend-engineer
              model: sonnet
              effort: 3
              files_affected:
                - src/research_foundry/services/search_router/mcp_server.py
                - .mcp.json
                - docs/dev/architecture/search-router/deployment.md
                - tests/test_search_router_mcp.py
---

# Search Router — Gap-Closing + aos-web/SearXNG Discovery Lane (v1)

Derived from a 2026-07-20 evidence-based reconciliation of the shipped Search Router MVP
(`d119993`) against the follow-on IntentTree nodes. **The MVP already shipped** the full
`search_router` service (router, modes, policy, budgets, dedupe, ranking, CLI `rf search`/`rf fetch`,
optional `mcp_server.py`, safety, 5 providers brave/exa/jina/firecrawl/github; 137 tests green,
offline-validated). This plan closes only the **genuine remaining gaps** plus the **primary new
deliverable** — the free aos-web/SearXNG discovery lane. P4 (monitoring/repo-scout) remains deferred.

## 0. Reconciliation verdict (why this scope)

| Area | Verdict | Evidence |
|---|---|---|
| P2 MCP/harness | Substantially done → **finishing pass** | `rf-mcp` console script real+runnable (`pyproject.toml:61`); intent/task linking correct (`policy.py:78-79`). Gaps: 3 named presets missing; naming mismatch; no `.mcp.json`; no MCP tests. |
| P3 CCDash | **Real gap** | `emit_ccdash_event` fires (`router.py:297`) but generic shape — 8 search metrics never reach it; `useful_source_count`/`citation_coverage` hardcoded `None` (`router.py:261,264`); `ccdash_event_id` never populated (`router.py:279`); no scorecard. |
| P3 SkillMeat | **Real gap** | `skillmeat/tool_profiles/` empty but `.gitkeep`; no §17 profiles or `skill_source_discovery_v1` SkillBOM; router never calls `writeback.py`. |
| aos-web lane | **Unbuilt (primary)** | No `searxng`/`aos_web` provider exists; node has 4 ACs. |
| P4 monitoring | Deferred | `MODES['monitoring_delta']` stub with empty chain (`modes.py:184-199`); **excluded**. |

## 1. Execution & git model (workflow)

- Execute via `.claude/workflows/execute-plan.js` (Opus builds ExecutionGraph from this `wave_plan`).
- **Single feature branch** off local HEAD; `isolation: shared`; Opus squash-merges to `main` on
  completion (operator directive: "squash to main when complete"). **No `git push`** (gated).
- Every implementation agent: commit only the files in your `files_affected`; **never `git add -A`
  / `git add .`** (protects unrelated uncommitted `.claude/agents/dev/*` WIP). Do NOT push/merge/stash.
- Validation is authoritative and re-run by Opus post-wave: `./.venv/bin/python -m pytest` (NOT the
  pyenv shim), `ruff check`, `mypy`. Frontend: N/A (no runs-viewer changes).

## 2. Wave 1 — aos-web/SearXNG free discovery lane  (node_01KX…; 4 ACs)

**Seam (from recon — authoritative):**
- `aos-web` script: `/Users/miethe/dev/homelab/development/agentic_meta_dev/infra/agentic-node/scripts/aos-web`.
  `aos-web search "<q>" --n N --json` → dumps **raw upstream SearXNG JSON verbatim** (top-level
  `results: [...]`, each with `title`, `url`, `content`, plus SearXNG extras `engine`/`score`/etc.),
  **unfenced**. `aos-web fetch <url> --max-chars N` → plain extracted text **wrapped** in
  `--- BEGIN UNTRUSTED WEB CONTENT (fetched: <url>) ---` … `--- END UNTRUSTED WEB CONTENT ---`.
  Honors `AOS_WEB_SEARX_URL` (default `http://127.0.0.1:8888`) from the process env — pass-through, no
  new RF env var. No credentials sent; http(s) only.
- Provider contract (`providers/base.py`): subclass `BaseSearchProvider`; set `id`, `roles`,
  `requires`, `env_keys` class attrs; override `search()`/`extract()`. `SearchHit`
  (title/url/snippet/provider/rank/score/source_type/published_at/raw), `ExtractedDoc`
  (url/markdown/title/content_length_chars/text_hash/fetched_at/extractor/degraded/risk_flags/raw),
  `ProviderResult` (provider/role/status∈{success,partial,failed,skipped,degraded}/hits/docs/
  queries_executed/estimated_cost_usd/latency_ms/error). Helpers: `text_sha256()`, `now_iso()`.
- **CLI-binary availability:** base `available()` uses `module_available()` (Python modules only) — a
  shell-tool provider MUST override `available()` with `shutil.which("aos-web") is not None` (optionally
  a short-timeout health probe). `requires=()` (no Python module), `env_keys=()` (keyless).
- Registration: `register(SearxngProvider())` at module scope **and** add to the import block +
  `__all__` in `providers/__init__.py` (side-effect import is the only discovery path).
- Mode/chain seam: add a `SearchMode` in `modes.py` (e.g. `free_discovery`) with `provider_chain`
  including the searxng id(s); `max_provider_cost_usd: 0.0`; `outputs` from existing vocab
  (`source_cards`, `summary`). **No `router.py`/`policy.py` changes needed** — the existing single-pass
  chain loop already mixes discovery + extraction roles.
- Persistence: reuse `router.py`'s existing `create_source_card(locator=hit.url, run_id=..., content=<markdown>,
  extra_limitations=<risk_flags>, created_by_agent="rf_search_router:aos_web", fetch=False, paths=...)`
  → writes `runs/<run_id>/sources/<id>.md`. No `source_cards.py` change.
- Injection/fencing: extraction must **strip the BEGIN/END fence lines**, then call
  `safety.scan_for_injection(text)` (`possible_prompt_injection` flag) as defense-in-depth, and add a
  `"untrusted_web_content"` limitation. Template: mirror `providers/brave.py` (`_parse_search`/`_fetch`/
  `search()` discovery split) and `providers/jina.py` (`_parse_extract`/`_fetch`/`extract()` extraction
  split) — pure `_parse_*` (unit-testable, no I/O) + lazy `_fetch` (subprocess here).

**TASK-1.1** (python-backend-engineer): implement `providers/searxng.py` (roles
`("discovery","extraction")`, keyless, `shutil.which` availability, subprocess to `aos-web search
--json` / `aos-web fetch`, raw-SearXNG-JSON parse, fence-strip + injection scan on extract, cost 0.0,
never raises), register + wire `providers/__init__.py`, add the `free_discovery` mode to `modes.py`.
Add offline tests `tests/test_search_router_searxng.py` (pure `_parse_search` with synthetic SearXNG
JSON; `_parse_extract` with synthetic fenced string incl. an injection-trigger case; `available()`
via `monkeypatch` on `shutil.which`; `_fetch` via `monkeypatch.setattr` on `subprocess.run`). Update
`test_registry_contains_all_five_providers` (→ six) and any `MODES`-enumerating test.

**TASK-1.3** (documentation-writer): add the searxng provider to
`docs/dev/architecture/search-router/provider_profiles.md` (free/keyless lane, untrusted-content
handling, `AOS_WEB_SEARX_URL`) and note the free lane in `architecture.md`.

**ACs:** (a) an `rf` run discovers via `aos-web search --json` with no API key; (b) selected
candidates hydrate into `runs/<RUN>/sources/` via `aos-web fetch`, fenced/untrusted provenance
preserved (`possible_prompt_injection` + `untrusted_web_content`); (c) reconciled vs the search-router
spec (mode budget/outputs use existing vocab; provider documented); (d) ≥1 offline-safe test.

## 3. Wave 2 — P3 CCDash search telemetry correctness

**TASK-2.1** (python-backend-engineer):
- Extend `services/telemetry.py::emit_ccdash_event` to accept optional `search_metrics: dict | None`
  and merge it into the emitted event's metrics; **return the event id**.
- Extend `schemas/ccdash_event.schema.yaml` metrics with **additive, optional** search fields
  (`queries_executed`, `urls_extracted`, `useful_source_count`, `duplicate_rate`,
  `extraction_failure_rate`, `citation_coverage`, `estimated_cost_usd`, `latency_ms`). Additive +
  optional so **existing RF (non-search) runs are unaffected** — do not make any new field required.
- In `services/search_router/router.py`: compute `useful_source_count` (hits that produced a source
  card) and `citation_coverage` (define: source-carded hits ÷ hits surviving constraints; document the
  definition), pass `search_run["metrics"]` through as `search_metrics`, and set
  `search_run["writebacks"]["ccdash_event_id"]` from the returned id.
- Tests: extend `tests/test_search_router_router.py` (metrics reach the event; `ccdash_event_id`
  populated) + a `telemetry` test for the new passthrough. Preserve existing generic-event behavior.

## 4. Wave 3 — P3 SkillMeat artifacts + writeback + provider scorecard

**TASK-3.1** (python-backend-engineer): author the 5 tool-profile YAMLs under `skillmeat/tool_profiles/`
(`brave_search_v1`, `exa_search_v1`, `jina_reader_v1`, `firecrawl_v1`, `github_discovery_v1`)
conforming to `schemas/tool_profile.schema.yaml` (validate each), and the `skill_source_discovery_v1`
SkillBOM under `skillmeat/skillboms/` (distinct from the generic `skill_research_swarm_v0` per-run
candidates). Content grounded in spec §11.5/§17 + provider cost notes.

**TASK-3.2** (python-backend-engineer): wire `search_router` to reference these on a run — populate
`search_run["writebacks"]["skillmeat_candidate_ids"]` with the tool-profile/BOM ids (reuse
`writeback.py` where sensible; do not fabricate a new subsystem). Add a **per-provider scorecard
rollup** (extend `telemetry.summarize` or a sibling fn) aggregating cost / duplicate-rate /
extraction-failure-rate per provider across `ccdash/events/*.yaml`. Tests:
`tests/test_search_router_scorecard.py` (offline, synthetic events).

## 5. Wave 4 — P2 MCP finishing pass

**TASK-4.1** (python-backend-engineer): add named MCP tool presets for `quick_lookup`,
`official_sources`, `academic_discovery` (modes already exist in `modes.py`; mirror the existing
`search_source_discovery` wrapper in `mcp_server.py`); **reconcile the tool-naming mismatch** (pick
one of dotted `search.source_discovery` via `@server.tool(name=...)` OR underscored — align
`mcp_server.py` and `deployment.md`); add a repo-root `.mcp.json` registering the `rf-mcp` server so a
Claude Code harness can discover it; add MCP test coverage (`tests/test_search_router_mcp.py`:
`build_server()` tool registration when the `mcp` extra is present; intent_id/task_node_id passthrough
into `routing_decision.yaml`). **End-of-feature reviewer gate = karen** (`review_intensity: tier3`).

## 6. Acceptance criteria (feature)

- Wave-1 aos-web node's 4 ACs met (offline test proves search→fetch→source-card with no API key).
- Search runs emit search-specific CCDash metrics; `ccdash_event_id` populated; provider scorecard
  computable; existing non-search runs unaffected (schema additive).
- §17 tool-profiles + `skill_source_discovery_v1` SkillBOM exist and validate; run references them.
- MCP presets cover the 6 named search modes; `.mcp.json` present; MCP tests pass.
- All new/changed code: `ruff` clean, `mypy` clean, `pytest` green under `./.venv/bin/python -m pytest`.
  No new hard dependency (aos-web is a subprocess; httpx remains optional).

## 7. Validation commands

```bash
./.venv/bin/python -m pytest tests/test_search_router_searxng.py tests/test_search_router_router.py \
  tests/test_search_router_providers.py tests/test_search_router_scorecard.py tests/test_search_router_mcp.py -q
./.venv/bin/python -m ruff check src/research_foundry/services/search_router
./.venv/bin/python -m mypy src/research_foundry/services/search_router
```

## 8. Open questions / deferred

- **OQ (descoped to follow-up):** P2 budget **governance** — a server-side budget ceiling and
  enforcement of `requires_human_approval` (currently recorded but never consulted). The MVP correctly
  enforces the *configured* budget; server-side caps are a separable hardening. Not built here.
- **Deferred (P4):** `monitoring_delta` / recurring repo-scout — stub mode only; out of scope.
- **Deferred:** live-provider validation with real API keys; Serper/Tavily/synthesis + academic
  adapters; `crawl.site`; `source_type` vocabulary unification.
