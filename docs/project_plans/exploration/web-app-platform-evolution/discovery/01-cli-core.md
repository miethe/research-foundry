---
doc_type: report
report_category: investigation
title: "RF CLI & research_foundry Core Engine — Capability Inventory"
status: draft
created: 2026-07-10
feature_slug: web-app-platform-evolution
---

# RF CLI & `research_foundry` Core Engine — Capability Inventory

Scope: the `rf` Typer CLI (`src/research_foundry/cli/__init__.py` +
`src/research_foundry/cli_commands.py` + `services/search_router/cli.py` +
`cli/commands/agent_job.py`) and the `research_foundry` Python package that backs it. This is a
factual inventory, not a recommendation document.

## 1. Entry points

`pyproject.toml` (`[project.scripts]`):

- `rf = "research_foundry.cli:app"` — the main CLI. Root Typer app defined in
  `src/research_foundry/cli/__init__.py:25`; `version`, `doctor`, `schema` are defined inline
  there; `_wire()` (`cli/__init__.py:153`) dynamically imports `research_foundry.cli_commands`
  (all other commands, 2551 lines) and `research_foundry.services.search_router.cli` (adds
  `search`/`fetch`), calling each module's `register(app)`. Missing modules degrade silently
  (the CLI "works incrementally during the build" per the module docstring).
- `rf-mcp = "research_foundry.services.search_router.mcp_server:main"` — stdio MCP server
  exposing the Search Router; requires the `mcp` extra, raises a clear `RuntimeError` pointing
  at the extra when absent (`pyproject.toml`, `[mcp]` extra).

Optional extras gate whole subsystems: `research` (gpt-researcher, paper-qa), `llm`
(claude-agent-sdk, litellm), `search` (httpx, for Search Router), `mcp`, `serve` (fastapi,
uvicorn — required for `rf serve`).

## 2. Command surface table

| command | purpose | maturity | notes | key file(s) |
|---|---|---|---|---|
| `rf version` / `rf doctor` | version print / workspace+adapter+integration health check | shipped | `doctor` reports schema/governance/adapter counts and ARC/IntentTree reachability (informational only) | `cli/__init__.py:36,43` |
| `rf schema validate\|list` | validate an artifact instance against its JSON schema | shipped | infers schema name from `type`/filename when `--schema` omitted | `cli/__init__.py:92` |
| `rf init <dir>` | scaffold a new foundry workspace (folders/schemas/config/templates) | shipped | `cli_commands.py:839` | |
| `rf capture` | capture a raw idea into `inbox/raw_ideas/` | shipped, offline | supports `--backlog-idea-ref RIB-NNN` linkage | `cli_commands.py:195`, `services/capture.py` |
| `rf triage` | raw idea → intent + I-BOM + IntentTree node | shipped, offline | `cli_commands.py:249` | |
| `rf plan` | intent → research brief + swarm plan + routing decision | shipped, offline | `cli_commands.py:273`, `services/planning.py` |
| `rf ingest` / `rf source-card create` | locator (file/URL) → schema-valid source card | shipped; URL fetch opt-in, degrades to locator-only card on failure | `cli_commands.py:315,341`, `services/source_cards.py` |
| `rf search` | Search Router query → normalized candidates (+ source cards unless `--no-cards`) | **offline-validated only** (per README/memory); requires `[search]` extra | keyless providers (jina, github) degrade gracefully offline; keyed providers (brave/exa/firecrawl) need API keys | `services/search_router/cli.py:27`, `router.py` |
| `rf fetch` | one or more known URLs → source cards directly (renamed from the old `rf extract`) | offline-validated only | distinct from claim-extraction `rf extract` | `services/search_router/cli.py:85` |
| `rf extract` | run's source cards → extraction cards (claim extraction) | shipped, offline, deterministic | `cli_commands.py:365`, `services/extraction.py` |
| `rf claim-map` | extraction cards → `claims/claim_ledger.yaml` | shipped, offline, deterministic | one `supported` claim per extracted evidence point; claim-type via regex heuristics | `cli_commands.py:381`, `services/claim_mapping.py` |
| `rf synthesize` | claim ledger → `reports/report_draft.md` | shipped; deterministic body is authoritative even when `--llm`/adapter available | LLM path only annotates a note — MVP explicitly keeps the deterministic ledger-faithful body for verifier compliance | `cli_commands.py:396`, `services/synthesis.py:210-220` |
| `rf verify` | deterministically verify every material claim maps to the ledger or is labeled | shipped — **the core differentiator** | 1256-line verifier; stable exit-code precedence (see §3) | `cli_commands.py:414`, `services/verification.py` |
| `rf council` | council/critic review of a run | shipped w/ offline fallback | `--via arc` uses live ARC when reachable; else local `research-foundry-council.js` workflow | `cli_commands.py:444` |
| `rf bundle` | publish `evidence_bundle.yaml` (optionally gated on verify) | shipped, offline | `cli_commands.py:472`, `services/writeback.py:179` |
| `rf writeback` | render writebacks to meatywiki/skillmeat/ccdash/intenttree/arc/notebooklm | shipped; live targets degrade to file candidates when servers offline | `--decision-record-only` re-renders just the inference-driven decision record; `notebooklm` is opt-in, not a default target | `cli_commands.py:491`, `services/writeback.py` |
| `rf guard check` | governance policy gate (key profile / sensitivity / provider / secret scan) | shipped, deterministic, network-free | exit 0 ok / 3 block / 7 require_approval | `cli_commands.py:589`, `services/governance.py` |
| `rf skillbom propose\|promote` | propose/promote SkillBOM candidates from a run | shipped | `cli_commands.py:660,670` |
| `rf ccdash summarize` | aggregate CCDash telemetry (daily/period) | shipped, offline | `cli_commands.py:688`, `services/telemetry.py` |
| `rf swarm run` | run enabled discovery adapters (degraded-safe) | shipped w/ stub degradation | e.g. `--adapters arc_council`, `--adapters notebooklm` | `cli_commands.py:703` |
| `rf status push` | push run status to an integration target (IntentTree, etc.) | best-effort, live-degrades | `cli_commands.py:783` |
| `rf cost` | summarize estimated run cost | shipped | `cli_commands.py:807` |
| `rf index rebuild` | rebuild registry indexes | shipped | `cli_commands.py:825` |
| `rf redact` | write a target-audience-redacted report copy | shipped | `cli_commands.py:861` |
| `rf intent show` | print a research intent's YAML | shipped | `cli_commands.py:880` |
| `rf tree add-node` | create/append an IntentTree node YAML | shipped, validated vs schema | `cli_commands.py:902` |
| `rf intake intenttree\|notebooklm` | pull an external node/notebook into RF's capture→triage(→plan) flow | shipped w/ offline degrade | `cli_commands.py:949,989` |
| `rf notebooklm resolve\|status\|sync` | manage the run↔NotebookLM notebook correlation registry | shipped, **fail-soft** — degrades to file candidates/skip with no live `notebooklm login` session | `cli_commands.py:1027,1087,1121`, `services/notebook_correlation.py` |
| `rf backlog reconcile` | reconcile run↔research-idea-backlog lifecycle fields | shipped; defaults to `--dry-run` | `cli_commands.py:1172`, `services/backlog_metadata.py` |
| `rf run export\|list` | export/list runs for the static runs-viewer (schema v1.2+) | shipped, deterministic, no LLM | sensitivity redaction applied at export time | `cli_commands.py:1252,1297`, `services/export_service.py` (1325 lines) |
| `rf catalog import\|search\|show\|stats\|rebuild` | shared evidence catalog (sqlite3 + FTS5 derived read model) | shipped (public-multiuser-release Phase 1); derived/rebuildable, never canonical | sensitivity-gated at read time, fail-closed on unknown labels | `cli_commands.py:1318+`, `services/catalog_service.py` (1970 lines) |
| `rf workspace migrate-dry-run\|migrate\|rollback` | workspace-isolation (`workspace_id`) backfill migration + rollback runbook | shipped (WKSP-301/302/303/304); dry-run guaranteed zero-write | flag-gated enforcement; see §5 gaps | `cli_commands.py:1482+`, `services/workspace_migration_service.py` |
| `rf report anchors` | print block/paragraph locations + claim links for a run's report | shipped (P2 Wave B) | `cli_commands.py:1755` |
| `rf report draft create\|list\|show\|add-block\|update-block\|delete-block\|reorder\|verify\|publish-preview\|export` | Report Builder — file-canonical draft authoring surface | shipped (Phase 3 / P3 Wave D-E) | `verify`/`publish-preview` run D13 checks fail-closed | `cli_commands.py:1846-2263`, `services/builder_service.py` |
| `rf report draft claim-link add\|remove` | manage claim links on a draft block | shipped | `cli_commands.py:2068,2106` |
| `rf audit list\|show\|health` | audit log read surface | shipped (AUDIT-002/003/004); gated by RBAC on API side | `cli_commands.py:2265+`, `services/audit_service.py` |
| `rf agent-job launch\|list\|stream\|accept\|status` | launch embedded/subprocess research agents (governed, credential-isolated) | shipped (Public Multi-User P4); explicit in-process-only providers enforced | never dispatches `gpt_researcher`/`paperqa2`/`litellm_router`/`opencode`/`arc_council`/`notebooklm` to a subprocess | `cli/commands/agent_job.py`, `services/agent_job_service.py` |
| `rf serve` | start the read-only loopback HTTP API for the runs-viewer | shipped (`runs-loopback-api-v1`); fails closed on LAN bind without token auth | default `127.0.0.1:7432`; requires `[serve]` extra | `cli_commands.py:2396`, `api/app.py` |

## 3. Core engine concepts

**Claim ledger** (`services/claim_mapping.py`, `claims/claim_ledger.yaml`). `rf claim-map`
deterministically maps every run's extraction cards to claim entries — each carries a
`claim_type` decided by regex heuristics (`_NUMERIC`/`_COMPARATIVE`/`_CAUSAL`/`_ATTRIBUTION`
→ `factual` fallback, `claim_mapping.py:22-25`), a `materiality`, and a `status`. Newly
mapped claims are always `supported` because each is backed by an extraction. Analytical
claims (`inference`/`speculation`) are appended later by a synthesis/analysis step and must
carry `inference_basis.from_claims` (enforced by the verifier). The ledger is the single
source of truth the synthesizer may cite from — the README states this is "the authority, not
the model."

**Source cards** (`services/source_cards.py`, `runs/<run>/sources/src_*.md`). `rf ingest` /
`rf source-card create` turn a locator (local path or URL) into a schema-valid Markdown card
with YAML frontmatter (`sensitivity`, `trust.source_rank`, `usage.*`, `extracted_points[]`
each with `quote`/`locator`/`summary`). URL fetching is opt-in and best-effort with an 8s
timeout (`source_cards.py:29`); failure degrades to a locator-only card rather than raising, so
`rf ingest` never blocks the pipeline.

**Evidence bundle** (`services/writeback.py:179`, `runs/<run>/evidence_bundle.yaml`). `rf
bundle` assembles a single durable artifact from a run's report + claim ledger (+ optional
`--verify` gate) validated against the `evidence_bundle` schema (`writeback.py:249`). Per the
README, "the durable asset is the evidence bundle... the swarm that produced it is disposable
and rerunnable."

**Run trace / telemetry** (`services/telemetry.py`, `runs/<run>/telemetry/run_trace.jsonl` +
`token_costs.yaml`/`tool_calls.yaml`). Every stage (`verify`, `guard`, etc.) best-effort appends
a JSONL event via `append_jsonl` (never fails the stage on a trace-write error — see
`verification.py:413-417`, `governance.py:567-586`). `rf ccdash summarize` aggregates these into
daily/period rollups mirrored to the workspace-level `ccdash/` tree — entirely derived from
on-disk artifacts, no network/API keys (`telemetry.py:1-9`).

**Governance gate** (`services/governance.py`, `config/governance.yaml`). `rf guard check`
deterministically evaluates ~9 policy rules (no work keys on personal runs, no work-sensitive
data to unapproved providers, no personal/work source mixing in one bundle, secret scanning via
~20 built-in regexes for API keys/tokens/private keys, review-required gates per writeback
target, unmapped-material-claims block) and returns a frozen `GuardResult` with exit codes 0
(ok) / 3 (`GOVERNANCE`, block) / 7 (`HUMAN_REVIEW`, require_approval) — never prints, CLI
renders (`governance.py:1-10,556-564`). `redact_payload` recursively scrubs secret-pattern
matches from any nested dict/list/tuple structure and is the mandated path for all agent-job
write paths (`governance.py:217-239`).

**Report verification** (`services/verification.py`). `verify_report` is described in its own
module docstring as "the differentiated value of Research Foundry" (`verification.py:1-19`). It
segments the report body into sentences, classifies material-claim types via regex heuristics
(quantitative/comparative/recommendation/attribution/causal/prediction/factual,
`verification.py:79-118`), and runs ~10+ checks: frontmatter presence, all cited `[claim:id]`
tags resolve, claim-id uniqueness, every material sentence is tagged or labeled, every
`supported` claim resolves to an existing source card, every `inference` claim has a basis,
every `inference`/`mixed`/`contradicted`/`speculation` claim rendered in the body carries its
required bold label, no `unsupported` ledger claims, and no work/client-sensitive source leaks
into a `public`-sensitivity report. Exit-code precedence: schema fail → 2, governance
(sensitivity leak) → 3, unsupported material claim → 4, other error-severity failure → 2 (SCHEMA
class), else 0 (`verification.py:737-756`). A parallel `verify_draft` path (D13 checks) applies
the same discipline to Report Builder drafts, including a workspace-wide sensitivity scan
(`build_global_source_index`) that closes a "blank-origin-draft" gap where a draft has no
declared source run (`verification.py:1056-1153`).

## 4. Recent evolution

Git history on `src/research_foundry/` (most-recent-first) shows the project moving from MVP
core (capture→verify→bundle→writeback) toward a governed multi-user service:

- `d119993` `feat(search-router)` — **Search Router MVP** (`rf search`/`rf fetch`), offline-
  validated only per project memory; MCP server (`rf-mcp`) added alongside.
- `33b6bcf` `feat(serve)` — **`rf serve`** read-only loopback API + gated LAN exposure
  (`runs-loopback-api-v1`).
- `63228e0` `fix(skills,cli)` — renamed the URL-extraction command from the old `rf extract`
  to `rf fetch` (collision fix vs. claim-extraction `rf extract`); refreshed custom skills.
- `ed49d8e`/`344a318` `feat(catalog)` — **shared evidence catalog** (sqlite3+FTS5), then
  adversarial-review hardening (sensitivity floors, link gating, parity).
- `8b9d8be`/`cb6af8b` — **Report Builder** phases 2–3: report anchors, then file-canonical
  drafts with fail-closed publish.
- `4e52be6`→`533f5c6`→`4aa2e0d` `feat(auth)` — AuthProvider port, `local_static` adapter,
  durable RBAC store, then a **Clerk** OIDC-style adapter (opt-in, dark-by-default).
- `51c044f` `feat(rbac)` — server-side 5-role RBAC enforcement on mutation routes.
- `7f5b566`→`298a72a`→`fa86609`→`b469fbf` `feat(audit)` — audit CLI/API, health-check probe,
  wiring into 6 governed mutation types, then a P1 security fix gating audit reads by role.
- `2550512` `feat(agents)` — **embedded agent research** (agent-job subprocess model,
  credential-isolated).
- `8708373` `feat(api)` — `POST /api/runs` to launch runs over HTTP.
- `2208927`→`d179fd4`→`3449b1c`→`5418568`→`eba75ab` `feat/fix(wksp-304)` — **workspace
  isolation**: config-flagged identity threading, inert query-layer scoping, then the
  enforcing flip, then two post-hoc fixes for leaked scoping (draft creation, `get_item`).
  Per project memory this full-surface audit is still an open pre-multi-tenant-deploy gate.

## 5. Gaps / rough edges observed

- **`rf search`/`rf fetch` (Search Router) are offline-validated only** — no confirmed live-
  provider run per project memory; keyed providers (brave/exa/firecrawl) require configured
  API keys that have not been exercised end-to-end.
- **LLM synthesis is a no-op by design, not just "not wired up" yet**: even when the
  `claude_agent_sdk` adapter is available, `rf synthesize` still emits the deterministic
  ledger-faithful body and only appends an explanatory note (`synthesis.py:210-220`). A caller
  expecting `--llm` to change report prose will be surprised.
  Note: a Path B swarm workflow (`rf-run-execute.js`) works around this entirely outside the
  CLI by having Claude Code agents directly edit `claim_ledger.yaml`/`report_draft.md` on disk
  and re-running `rf verify`, then falling back to the deterministic report if enrichment can't
  pass verification — i.e. the *real* synthesis path today is an external orchestration script,
  not an `rf synthesize --llm` flag.
- **Workspace isolation (WKSP-304) enforcement has already had two post-hoc leak fixes** after
  the "enforcing flip" landed (`5418568`, `eba75ab` — `create_draft_from_run`/`from_collection`
  identity threading, `get_item` scope leak). Per project memory, a full-surface audit is a
  required gate before any shared-store multi-tenant deployment.
- **The claim-type/material-claim classifiers are regex heuristics**, not model-based, in both
  `claim_mapping.py` and `verification.py`. This is a deliberate determinism choice (no
  network/LLM needed) but means classification quality is bounded by pattern coverage — e.g. a
  material claim phrased outside the known verb/keyword sets could pass unflagged, or a
  citation-list line inside an unexpected heading could be misclassified.
  `verification.py:219-243` explicitly special-cases "Sources"/"References" headings and
  "Open questions" to close known laundering holes, implying this was iteratively hardened
  against adversarial review rather than designed complete up front.
  Both docstrings on this pattern-hardening history (`_HTML_COMMENT` handling,
  `check_report_body_sensitivity`'s "R2 CRITICAL fix" comment at `verification.py:975-987`)
  suggest the verifier has absorbed several rounds of red-team findings.
  Confidence: high (directly observed in code comments), not merely inferred.
- **`rf serve` and the catalog/audit/RBAC/auth stack are recent (last ~15 commits touching
  `src/research_foundry`)** and layered incrementally — auth provider ports, RBAC store,
  audit gating, and workspace isolation all landed within a tight window with multiple
  immediate "P1 security fix" follow-up commits (`b469fbf`, `533f5c6`), suggesting this surface
  is still actively hardening rather than settled.
- **NotebookLM and IntentTree/ARC integrations are fail-soft by design** (degrade to file
  candidates / skip when the external service is offline) — correct for resilience, but means
  none of these paths has a hard-failure signal if e.g. a notebook resolution silently
  degrades in a way the operator doesn't notice.
- A top-level `CHANGELOG.md` exists and is actively maintained (its `[Unreleased]` section
  currently documents WKSP-304 in detail), so it is a better primary source for future
  evolution tracking than `git log` alone — this inventory cross-checked both.
