---
name: research-foundry-swarm
description: Installs and initializes a Research Foundry workspace from scratch, then orchestrates a Claude Code agent swarm to produce a claim-verified evidence bundle. Covers the uv-tool install, `rf init`, `rf doctor` bootstrap sequence; the two swarm-drive patterns (RF-native `rf swarm run` vs. Claude-Code-orchestrated discovery feeding `rf ingest`); the deterministic tail that converts raw sources into a verified, governance-gated report; and key-profile governance. Cross-links the `research-foundry` skill for the full 21-step pipeline loop and per-command reference. Use when an agent needs to stand up a Research Foundry workspace from scratch or orchestrate a Claude Code agent swarm into a claim-verified evidence bundle.
---

# Research Foundry Swarm

This skill covers **workspace bootstrap** and **swarm orchestration**. It is the "set up and drive" companion to the `research-foundry` skill, which owns the per-command pipeline reference and the full 21-step execution loop. Do not repeat content from that skill here — cross-link instead.

> For the intent → command route table, the 21-step loop, claim-traceability discipline, and per-command syntax, load the `research-foundry` skill.

> **Shared node instance:** a persistent RF instance runs on the agentic node at `http://10.42.10.76:7432` (auth `Bearer $RF_TOKEN_AGENT` from `~/.config/research-foundry/serve.env`; viewer at `:3030`). Prefer it for shared reads (`GET /api/runs|reports|catalog|audit`) and HTTP launch (`POST /api/runs`, which scaffolds a run but does not drive the swarm). Local-workspace bootstrap below is for standing up a *new* workspace or SSH'd on-node work; see the `research-foundry` skill's "Shared node instance" section for the full API surface.

---

## Live Integrations (ARC + IntentTree)

**Bidirectional integrations with ARC (council review) and IntentTree (inbound task dispatch + outbound status + result links)** are now live and degrade safely to file-based candidates when servers are offline.

**ARC (Agent Review Council) — RF ↔ ARC**
- **Live council review**: `rf council --via arc` runs a live ARC review when reachable; offline fallback to the local `research-foundry-council.js` workflow (exit code 0 = approved, 7 = human review required).
- **Writeback target**: `rf writeback <run_id> --targets arc` writes a review request and folds the verdict into RF's gate.
- **Swarm adapter**: `rf swarm run --adapters arc_council` lets ARC reviewers critique discovery/synthesis mid-run (degrades to stub offline).
- **Configuration**: `foundry.yaml` `integrations.arc.base_url` (default `http://127.0.0.1:8910`); env `ARC_BASE_URL`; `rf doctor` reports reachability.

**IntentTree — IntentTree ↔ RF**
- **Inbound task intake**: `rf intake intenttree <node_id>` pulls a dispatched task with linked detail (MeatyWiki refs, artifacts) into capture → triage → optional plan. `--from-file PATH` for offline fallback.
- **Status updates**: `rf status push --run <run_id> --to intenttree [--stage STAGE]` posts progress at milestones (discovery_started, sources_ingested, verify_passed, bundle_written); best-effort when online, silent degrade offline.
- **Result linking**: `rf writeback <run_id> --targets intenttree` links the evidence bundle, report, and artifacts back to the originating node; writes a candidate file as fallback.
- **Configuration**: `foundry.yaml` `integrations.intenttree.base_url` (default `http://localhost:8000`); env `INTENTTREE_BASE_URL` / `INTENTTREE_API_TOKEN`; `rf doctor` reports reachability.

**Principle: "candidate first, push second"** — RF always emits a deterministic, schema-valid candidate file under `runs/<run>/writebacks/`; the live HTTP push happens only when reachable and permitted by the run's key profile. If the server is offline, RF falls back to file candidates; the push is best-effort and reversible.

See also: `docs/projects/research-foundry/bidirectional-integrations-plan.md` (design & architecture).

---

## 1. Install & Init

### Ensure `rf` is on PATH

`rf` is distributed as a uv tool. Install it once per environment:

```bash
# Minimal install (offline/deterministic pipeline only)
uv tool install --editable .

# With live model adapters (gpt_researcher, paperqa2, claude_agent_sdk, opencode, litellm)
uv tool install --editable ".[research,llm]"
```

Verify:

```bash
rf version
```

### Bootstrap a workspace

```bash
rf init ./my-foundry --profile personal
```

`rf init` scaffolds the full folder tree (`inbox/`, `intents/`, `runs/`, `schemas/`, `config/`, `templates/`, etc.), writes `foundry.yaml`, `.env.example`, and a default `config/governance.yaml` with your chosen key profile as the default.

Key profiles: `personal` | `work_approved` | `client_approved` | `offline_only`. Choose once at init; override per-run with `--profile`.

### Confirm readiness

```bash
rf doctor
```

`rf doctor` checks: workspace structure, schema validity, governance rules loaded, model profiles present, and adapter availability (reports N/5 live adapters). Fix any red items before continuing. A fully offline, deterministic workspace shows green with 0/5 live adapters — that is normal and sufficient for the deterministic tail.

---

## 2. Two Ways to Drive a Swarm

### Path A — RF-native swarm (opt-in adapters)

Use when one or more live adapters are installed and enabled.

```bash
# Governance preflight first — always
rf guard check --profile personal

# Then run enabled discovery adapters
rf swarm run <run_id> --adapters gpt_researcher,paperqa2 --profile personal
```

**What `rf swarm run` does and does NOT do:**
- Reads `runs/<run_id>/research_brief.md`
- Calls each adapter's `run()` in sequence
- Writes `runs/<run_id>/source_candidates.yaml`
- It does NOT create source cards and does NOT coordinate subagents

`source_candidates.yaml` is a ranked list of candidates — it is not ingestible downstream. After `rf swarm run`, you must convert candidates to source cards via `rf ingest` (one call per source you accept) before the deterministic tail can proceed.

**Adapter degradation:** All five adapters (`gpt_researcher`, `paperqa2`, `claude_agent_sdk`, `opencode`, `litellm`) degrade to deterministic stubs unless their extra is installed AND opt-in real mode is enabled. Real mode for `claude_agent_sdk` targets the Claude Agent SDK Python package, not the Claude Code CLI harness. Stubs are safe and sufficient for testing the pipeline shape.

### Path B — Claude Code-orchestrated swarm (works today, recommended)

This is the clean integration pattern: the Claude Code agent (or a multi-agent workflow) performs discovery using its own tools and subagents, then feeds findings into the RF run as source cards. RF stays the governance + claim-ledger + verifier spine; the swarm is disposable discovery muscle.

**Step-by-step:**

1. **Preflight** (mandatory before any discovery):
   ```bash
   rf guard check --profile personal
   ```

2. **Create the run context** (capture → triage → plan):
   ```bash
   rf capture "<research question>" --from manual --sensitivity personal --tag <tag> \
     --backlog-idea-ref RIB-NNN   # optional: link to a backlog idea entry
   rf triage inbox/raw_ideas/raw_*.md --create-intent --create-ibom --create-tree-node
   rf plan <intent_id> --depth deep --audience technical --max-cost 5 --freshness 180d
   ```
   This produces `runs/<run_id>/research_brief.md` and `runs/<run_id>/swarm_plan.yaml`.

   **Run metadata population:** When `--backlog-idea-ref` is provided, `linked_projects`, `category`, and `tags` are derived from the backlog entry and written into `run.yaml`. These fields flow through the export schema (v1.2) to the runs viewer.

   **Backlog lifecycle reconciliation:** After runs complete, use `rf backlog reconcile [--dry-run|--write]` to synchronize run status back to the backlog (forward-only status advancement and link population). Default is `--dry-run` (prints diff without writing).

3. **Agent-driven discovery:** The Claude Code agent (or subagents it spawns) uses web search, document reads, API calls, or any available tool to locate sources. Each located source is a candidate to feed in.

4. **Ingest each accepted source into the run:**
   ```bash
   rf ingest <url_or_file_path> \
     --run <run_id> \
     --source-type <paper|web_page|official_doc|other> \
     --sensitivity <personal|public|work_internal|client_confidential>
   ```
   `rf ingest` writes a schema-valid `runs/<run_id>/sources/src_*.md` source card. Alternatively, write source cards directly to that path following the `source_card` schema in `schemas/`.

5. **Run the deterministic tail** (Section 3 below).

**Key architectural fact:** The Claude Code multi-agent workflow is the outer orchestrator. `rf` is never the caller of Claude Code — it is the governance and evidence spine that the orchestrator feeds into.

### Path C — First-party Search Router (lightweight discovery)

For runs that don't need a full agent swarm, RF ships a first-party **Search Router** that handles source discovery and URL extraction directly:

```bash
# Discover sources (produces source cards by default)
rf search "kubernetes pod scheduling" --mode source_discovery --max-results 8 --max-cost 0.25

# Skip card creation — get ranked candidates only
rf search "kubernetes pod scheduling" --no-cards --intent-id INT-001 --task-node-id TN-005

# Extract markdown from known URLs into source cards
rf fetch https://example.com/paper.pdf https://docs.k8s.io/scheduling
```

**Requires** the `[search]` extra: `uv tool install --editable ".[search]"`

**How it relates to the swarm paths:**
- `rf search` replaces the need for `rf swarm run` when the query is well-formed and the scope is bounded. It produces source_cards directly (unless `--no-cards`), skipping the candidate→ingest two-step.
- `rf fetch` replaces `rf ingest` when you already have URLs and want Markdown extraction + source-card creation in one step.
- Path A/B swarm patterns remain preferred for deep, multi-adapter discovery runs.

**Keyless provider degradation:** Providers that need no API key (jina, github) work immediately; they degrade gracefully offline. Keyed providers (brave, exa, firecrawl) require configured API keys and are skipped when absent.

---

## 3. The Deterministic Tail & the Verify Gate

Once source cards exist in `runs/<run_id>/sources/`, the pipeline is fully deterministic and offline-safe:

```bash
# Extract CLAIMS from source cards (cheap model profile) — NOT URL extraction
rf extract <run_id> --model-profile rf_extract_cheap

# Build the claim ledger from extractions
rf claim-map <run_id> --from extractions --out claims/claim_ledger.yaml

# Synthesize the report (may only cite ledger claim IDs or label as inference/speculation)
rf synthesize <run_id> \
  --report reports/report_draft.md \
  --model-profile rf_synthesize_deep

# Verify — this is the build gate; exit 4 on any unsupported material claim
rf verify <run_id> \
  --report reports/report_draft.md \
  --claim-ledger claims/claim_ledger.yaml \
  --fail-on-unsupported

# Publish the durable evidence bundle
rf bundle <run_id> --verify --out evidence_bundle.yaml

# Write back to downstream targets (full list: meatywiki,skillmeat,ccdash,intenttree,arc,notebooklm)
rf writeback <run_id> --targets meatywiki,skillmeat,ccdash --require-review
# NOTE: --targets meatywiki automatically emits an additional decision_record writeback
# rendered from inference/recommendation claims (when they exist in the ledger).
# decision_record is NOT a separate --targets value — it is auto-emitted with meatywiki.
```

### Publishing into MeatyWiki (live vault)

`rf writeback ... --targets meatywiki` only generates a **source-note candidate** (`writebacks/meatywiki_writeback.md`) and mirrors it into the local `meatywiki/` tree — it does **not** push to a running MeatyWiki vault. To publish for real, hand off to the dedicated skills:

1. Author the artifact with engine-honored frontmatter routing hints → load the **`meatywiki-author`** skill.
2. Ingest + compile it into the vault via the MeatyWiki CLI → load the **`meatywiki`** skill (or **`meatywiki-suite`** for Portal REST API / MCP).

These skills drive the MeatyWiki application (the `meatywiki` CLI lives in the sibling `../meatywiki` repo) and assume it is installed; their internal doc references resolve there, not in RF. Respect the run's key profile — only `personal`-tier data may go to a personal vault.

### Exit-code table (treat any non-zero as a stop)

| Code | Meaning | Fix |
|------|---------|-----|
| 0 | Pass | — |
| 2 | Schema validation failed | Fix malformed source card or extraction |
| 3 | Governance policy blocked | Switch profile or redact sensitive data |
| 4 | Unsupported material claim | Label claim as `inference`/`speculation` or add a source card |
| 5 | Budget exceeded | Reduce run scope or increase budget ceiling |
| 6 | Adapter/tool failure | Check adapter config or switch to stub mode |
| 7 | Human review required | Run `rf council` and obtain sign-off |

Do not override or retry with `--no-fail`. Fix the cause, then re-run.

> For the full per-command reference, optional steps (`rf council`, `rf skillbom propose`, `rf cost`, `rf redact`, `rf index rebuild`, `rf ccdash summarize`), and the complete 21-step loop narrative, load the `research-foundry` skill.

---

## 4. Governance & Guardrails

### Run the preflight before anything

```bash
rf guard check --profile <profile>
```

This is mandatory before any source discovery, model call, or privileged action. Deterministic checks run without LLM involvement: key/tier compatibility, writeback-target permissions, and work/personal isolation.

### Key profiles

| Profile | Permitted data | Permitted writebacks | Env file |
|---------|---------------|---------------------|----------|
| `personal` | Personal, public | Personal MeatyWiki | `.env.personal` |
| `work_approved` | Work-internal (explicitly approved) | Work targets only | `.env.work` |
| `client_approved` | Client-authorized only; human review required | No cross-client or personal | `.env.client` |
| `offline_only` | Local documents and local models only | None | — |

### Non-negotiable rules

- Work-provided keys cannot be used for personal runs. This is enforced deterministically, not by policy memo.
- A key or model must not touch data above its tier.
- A writeback target must not receive data above its permitted tier.
- `rf guard` fails closed when a rule is ambiguous.

### LAN-exposure governance (`rf serve`)

`rf serve` is the read-only loopback HTTP API consumed by the runs viewer. It is a **governance surface** with fail-closed bind semantics:

```bash
# Loopback only (safe default — no auth required)
rf serve --port 7432 --bind-host 127.0.0.1 --auth-mode none

# LAN exposure — BOTH guards must pass or the server refuses to start:
#   1. --auth-mode token (explicit)
#   2. RF_SERVE_TOKEN env var must be set and non-empty
rf serve --port 7432 --bind-host 0.0.0.0 --auth-mode token
```

- Requires the `[serve]` extra (fastapi, uvicorn): `pip install 'research-foundry[serve]'`
- Endpoints: `/health`, `/api/runs`, `/api/runs/{id}`, `/api/runs/{id}/claims`, `/api/runs/{id}/sources/{sc_id}`, `/data/governance.json`. All data routes go through `export_service` — sensitivity redaction is enforced at the export layer.
- The `--sensitivity-threshold` flag overrides which sensitivity level is the most that flows through to JSON (default: `public`).
- IP allowlist middleware is active when `viewer.allowlist` is configured (rejects unlisted IPs with HTTP 403).

### Never ship unsupported claims

The synthesizer may only cite claim IDs already present in `claim_ledger.yaml`, or label a sentence as `inference` or `speculation`. `rf verify --fail-on-unsupported` enforces this. An exit code 4 means the report has a material claim with no ledger entry and no label — stop, label or add the source, and re-run verify. The claim ledger, not the model, is the authority.

---

## Cross-References

- **Per-command reference + 21-step loop**: `.claude/skills/research-foundry/SKILL.md`
- **Folder map + claim-status model**: `README.md`
- **MVP spec (commands §10, loop §11, adapters §13, Day-2 §16)**: `docs/projects/research-foundry/research-foundry-mvp-spec.md`
- **Service contract**: `docs/projects/research-foundry/SERVICE_CONTRACT.md`
- **Source card schema**: `schemas/source_card.schema.yaml` (inside initialized workspace)
- **Author artifacts for MeatyWiki ingestion**: `.claude/skills/meatywiki-author/SKILL.md`
- **Drive the MeatyWiki CLI (ingest → compile → lint)**: `.claude/skills/meatywiki/SKILL.md` — full lifecycle incl. Portal API/MCP: `.claude/skills/meatywiki-suite/SKILL.md` (require the MeatyWiki app from `../meatywiki`)
- **Agent Review Council (offline gate over report + ledger)**: `.claude/skills/council-review/SKILL.md` — backs `rf council` (exit code 7 path, step 16 of the 21-step loop); vendored reviewer agents live in `.claude/agents/council/` (`council-coordinator.md`, `architecture-reviewer.md`, `correctness-reviewer.md`, `domain-research-reviewer.md`, and the full roster)
- **council-run** (reference/arc-server path only): the ARC server variant of council execution — note this is an arc-server-dependent path and is NOT the offline `council-review` skill used here; prefer the offline skill for all RF pipeline runs
- **intenttree-cli**: `.claude/skills/intenttree-cli/SKILL.md` — live IntentTree server interface for intent/tree management; note that `rf intent` and `rf tree` (used in step 2 of this skill's Path B) are the offline RF-native subset of this capability; load `intenttree-cli` only when a live IntentTree server is available and required
- **Workflow authoring for RF swarm/council scripts**: `.claude/skills/workflow-authoring/SKILL.md` — use when authoring or extending `.claude/workflows/research-foundry-swarm.js` or `.claude/workflows/research-foundry-council.js`
- **research-foundry-swarm Workflow script**: `.claude/workflows/research-foundry-swarm.js` — Claude Code-orchestrated Path B discovery swarm; registered in `.claude/specs/workflows/workflow-registry.md`
- **research-foundry-council Workflow script**: `.claude/workflows/research-foundry-council.js` — offline council gate over a run's report and claim ledger; registered in `.claude/specs/workflows/workflow-registry.md`
- **RF discovery swarm agents**: `rf_discovery_lead` (swarm orchestrator), `rf_deep_reader` (full-text extraction), `rf_domain_researcher` (domain-specific source location) — used by `research-foundry-swarm.js`; definitions under `.claude/agents/research/`
