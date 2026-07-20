---
id: skill_source_discovery_v1
name: "Source Discovery — bounded multi-provider search skill stack"
status: promoted
purpose: >-
  Find candidate authoritative sources with a bounded search budget across
  the search_router's discovery+extraction provider chain, and hydrate
  selected candidates into source cards.
agent_postures:
- researcher
tools_used:
- brave_search_v1
- exa_search_v1
- jina_reader_v1
- firecrawl_v1
- github_discovery_v1
context_packs:
- research_foundry_core
output_schemas:
- search_request.schema.yaml
- search_run.schema.yaml
- source_card.schema.yaml
validation:
- budget_respected
- dedup_and_rank_applied
- injection_scan_applied_on_extract
- governance_guard_passed
known_failure_modes:
- weak for niche academic topics without a dedicated academic provider
- keyed providers (exa/firecrawl) silently skip when API keys are absent — the
  chain degrades to keyless providers (brave/jina/github/searxng) rather than
  failing the run
- snippet-only discovery hits without an extraction pass yield thin source
  cards; pair with jina_reader_v1 or firecrawl_v1 for full-text hydration
performance_evidence:
  quality_score: pending
  rework_count: 0
---

# Source Discovery Skill (`skill_source_discovery_v1`)

Distinct from the generic per-run `skill_research_swarm_v0` candidate stack — this is the durable,
promoted SkillBOM backing the `search_router` service's discovery-role provider chain (`rf search`
/ `rf fetch`, `research_foundry.services.search_router.router.run_search`).

## Provider stack

Backed by the 5 canonical tool profiles under `skillmeat/tool_profiles/`:

| Tool profile | Provider id | Roles | Keyless |
|---|---|---|---|
| `brave_search_v1` | `brave` | discovery | No |
| `exa_search_v1` | `exa` | discovery | No |
| `jina_reader_v1` | `jina` | extraction | Yes |
| `firecrawl_v1` | `firecrawl` | discovery, extraction | No |
| `github_discovery_v1` | `github` | discovery | Yes (rate-limited) |

(The `aos_web`/`searxng` free-discovery lane — `providers/searxng.py`, `free_discovery` mode — is a
separate keyless addition from Wave 1 of the same plan; it is not one of this SkillBOM's 5 tool
profiles but composes with it in the same provider chain.)

## Budget & governance

- Every invocation runs under a `Budget`/`BudgetTracker` (max queries, max URLs to extract, max
  cost) resolved from the request + mode defaults — see `services/search_router/router.py`.
- Extraction output is scanned for prompt injection (`safety.scan_for_injection`) before being
  persisted into a source card; untrusted-content provenance flags are preserved on the card.

## Reuse

Reference this SkillBOM's id (and the underlying tool-profile ids) from a run's
`search_run.writebacks.skillmeat_candidate_ids` when the run exercised this stack — see
`services/writeback.py` and `services/search_router/router.py`.
