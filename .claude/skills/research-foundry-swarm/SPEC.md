---
schema_version: 2
doc_type: skill_spec
skill_name: research-foundry-swarm
skill_version: 1.1.0
status: stable
created: 2026-06-13
updated: 2026-06-22
owner: "Nick Miethe"
source_docs:
  - README.md
  - docs/projects/research-foundry/research-foundry-mvp-spec.md
  - docs/projects/research-foundry/SERVICE_CONTRACT.md
  - .claude/skills/research-foundry-swarm/SKILL.md
related_skills: [research-foundry]
affects_commands: []
---

<!-- Convention reference: .claude/specs/artifact-structures/skill-spec-convention.md -->

# research-foundry-swarm — Skill Specification

> **Reading this file**: This is the versioned capability contract for the `research-foundry-swarm` skill.
> For invocation-time routing and command sequences, see `SKILL.md` in this same directory.

---

## 1. Purpose & Scope

**Mission**: Enable agents to stand up a Research Foundry workspace from scratch and orchestrate a Claude Code agent swarm that feeds discovered sources into the RF governance and claim-verification spine, producing a durable, claim-verified evidence bundle.

This skill is the **install, init, and swarm-drive** layer. It is the complement to the `research-foundry` skill, which owns the 21-step pipeline loop, the intent-to-command route table, and the full per-command reference. Load `research-foundry` for pipeline operations; load this skill when the workspace does not yet exist or when an agent needs to understand how to wire a Claude Code swarm into the RF pipeline.

**In scope**:
- Installing `rf` as a uv tool (`uv tool install --editable .` and `.[research,llm]` extras)
- Bootstrapping a new foundry workspace (`rf init`, `rf doctor`) and confirming readiness
- Running RF-native source discovery (`rf swarm run`) and understanding its adapter degradation model
- Orchestrating a Claude Code agent swarm as the outer discovery layer feeding `rf ingest`
- Understanding the boundary: Claude Code is the outer caller; `rf` is never the caller of Claude Code
- Running the deterministic tail: `rf extract` → `rf claim-map` → `rf synthesize` → `rf verify` → `rf bundle` → `rf writeback`
- Interpreting `rf verify` exit codes and remediating failures
- Selecting and enforcing key-profile governance (`rf guard check`)

**Out of scope**:
- The 21-step pipeline loop narrative — owned by the `research-foundry` skill (`SKILL.md` §Execution loop)
- The full intent → `rf` command route table — owned by the `research-foundry` skill (`SKILL.md` §Intent → command route table)
- Per-command syntax for `rf capture`, `rf triage`, `rf plan`, `rf council`, `rf skillbom`, `rf cost`, `rf redact`, `rf index`, `rf ccdash` — consult `research-foundry` SKILL.md for those
- Claim-traceability discipline deep-dive — see `research-foundry` SKILL.md §Claim-traceability discipline
- Adapter implementation internals — see `docs/projects/research-foundry/research-foundry-mvp-spec.md` §13

---

## 2. Capability Coverage

| Intent | Workflow / Section | Canonical Doc |
|--------|-------------------|---------------|
| Install `rf` as a uv tool | `SKILL.md` §1 Install & Init | `README.md` §Install & quickstart |
| Bootstrap a new foundry workspace (`rf init`, key profile) | `SKILL.md` §1 Install & Init | `README.md` §Install & quickstart |
| Verify workspace readiness (`rf doctor`) | `SKILL.md` §1 Install & Init | `README.md` §Install & quickstart |
| Run RF-native swarm discovery with opt-in adapters | `SKILL.md` §2 Path A | `docs/projects/research-foundry/research-foundry-mvp-spec.md` §10.6 |
| Understand adapter degradation and stub behavior | `SKILL.md` §2 Path A | `docs/projects/research-foundry/research-foundry-mvp-spec.md` §13 |
| Understand what `source_candidates.yaml` is (and is not) | `SKILL.md` §2 Path A | `docs/projects/research-foundry/research-foundry-mvp-spec.md` §10.6 |
| Orchestrate Claude Code agent swarm as outer discovery layer | `SKILL.md` §2 Path B | `docs/projects/research-foundry/SERVICE_CONTRACT.md` |
| Link capture to backlog (`--backlog-idea-ref`) and derive run metadata | `SKILL.md` §2 Path B | `src/research_foundry/cli_commands.py` `capture` |
| Reconcile run↔backlog lifecycle (`rf backlog reconcile`) | `SKILL.md` §2 Path B | `src/research_foundry/services/backlog_metadata.py` |
| Discover sources via the first-party Search Router (`rf search`) | `SKILL.md` §2 Path C | `src/research_foundry/services/search_router/cli.py` |
| Fetch known URLs into source cards (`rf fetch`) | `SKILL.md` §2 Path C | `src/research_foundry/services/search_router/cli.py` |
| Ingest discovered sources into a run (`rf ingest`) | `SKILL.md` §2 Path B | `README.md` §The demo loop, end to end |
| Run the deterministic tail (extract → claim-map → synthesize → verify → bundle → writeback) | `SKILL.md` §3 The deterministic tail | `README.md` §The demo loop, end to end |
| Interpret `rf verify` exit codes and remediate | `SKILL.md` §3 Exit-code table | `docs/projects/research-foundry/research-foundry-mvp-spec.md` §10.10 |
| Export run data for viewer (`rf run export`, `rf run list`) | `SKILL.md` §3 The deterministic tail | `src/research_foundry/services/export_service.py` |
| Serve the loopback API with fail-closed LAN governance (`rf serve`) | `SKILL.md` §4 Governance & Guardrails | `src/research_foundry/api/app.py` |
| Understand decision_record auto-emit on meatywiki writeback | `SKILL.md` §3 The deterministic tail | `src/research_foundry/services/writeback.py` |
| Run governance preflight (`rf guard check`) | `SKILL.md` §4 Governance & Guardrails | `README.md` §Governance & key profiles |
| Select and enforce key-profile isolation | `SKILL.md` §4 Governance & Guardrails | `README.md` §Governance & key profiles |

---

## 3. Invariants & Constraints

1. **Governance preflight is mandatory**: `rf guard check --profile <profile>` must be run before any source discovery, model call, or adapter invocation. No exceptions, regardless of profile or run sensitivity.
   _Source_: `README.md` §Governance & key profiles; `SKILL.md` §4

2. **The claim ledger — not the model — is the authority**: The synthesizer may only cite claim IDs already present in `claims/claim_ledger.yaml`, or label a sentence as `inference` or `speculation`. It never mints a new claim ID.
   _Source_: `docs/projects/research-foundry/research-foundry-mvp-spec.md` §10.9; `research-foundry` SKILL.md §Claim-traceability discipline

3. **`rf verify --fail-on-unsupported` gates the build**: Any unsupported material claim produces exit code 4 and must stop the pipeline. Do not override or retry without fixing the cause — label the claim or add a source card.
   _Source_: `README.md` §Claim-status model; `SKILL.md` §3

4. **`source_candidates.yaml` contains candidates, not source cards**: `rf swarm run` writes a ranked candidate list to `runs/<run_id>/source_candidates.yaml`. It does not create source cards. Each accepted candidate must be individually converted via `rf ingest` before the deterministic tail can proceed.
   _Source_: `docs/projects/research-foundry/research-foundry-mvp-spec.md` §10.6; `SKILL.md` §2 Path A

5. **Work/personal key isolation is deterministic**: Work-provided keys cannot be used for personal runs, and personal keys cannot be used for work-approved or client-approved runs. `rf guard` enforces this without LLM involvement. Fail closed when a rule is ambiguous.
   _Source_: `README.md` §Governance & key profiles

6. **The `claude_agent_sdk` adapter targets the Claude Agent SDK Python package, not Claude Code the CLI harness**: The adapter's `run()` calls the `claude-agent-sdk` Python library. Claude Code (the CLI) is the outer orchestrator; it is not what this adapter invokes. Real mode for this adapter is intentionally unimplemented in the MVP.
   _Source_: `docs/projects/research-foundry/research-foundry-mvp-spec.md` §13; `SKILL.md` §2 Path A

7. **Claude Code / Workflow is the outer orchestrator; `rf` is never the caller of Claude Code**: The integration pattern is one-directional. A Claude Code agent (or multi-agent workflow) does discovery and feeds findings into `rf ingest`. `rf` does not spawn or call Claude Code agents — it is the governance, claim-ledger, and verifier spine that the outer orchestrator feeds.
   _Source_: `SKILL.md` §2 Path B; `docs/projects/research-foundry/SERVICE_CONTRACT.md`

8. **All adapters degrade to deterministic stubs by default**: Unless an extra (`.[research]` or `.[llm]`) is installed AND opt-in real mode is enabled for that adapter, every adapter falls back to its offline stub. A 0/5 live-adapter `rf doctor` result is a valid, fully functional state for the deterministic pipeline.
   _Source_: `README.md` §Status: MVP; `docs/projects/research-foundry/research-foundry-mvp-spec.md` §13

9. **Search Router keyless providers degrade gracefully offline**: `rf search` and `rf fetch` (the `[search]` extra) work without API keys via jina and github providers; they degrade to empty results when offline rather than raising errors. Keyed providers are skipped when their keys are absent.
   _Source_: `src/research_foundry/services/search_router/cli.py`; `SKILL.md` §2 Path C

10. **`rf serve` fails closed on non-loopback bind**: Binding to a non-loopback host requires `--auth-mode token` AND a non-empty `RF_SERVE_TOKEN` env var. Both checks execute BEFORE any port is opened. An IP allowlist middleware rejects unlisted IPs (HTTP 403) when configured.
    _Source_: `src/research_foundry/cli_commands.py` `serve`; `src/research_foundry/api/app.py`

11. **`rf writeback --targets meatywiki` auto-emits a decision_record**: When inference/recommendation claims exist in the claim ledger, the meatywiki writeback automatically renders an additional `decision_record_writeback.md`. This is NOT a separate `--targets` value — it is triggered by including `meatywiki` in targets.
    _Source_: `src/research_foundry/services/writeback.py` `_render_decision_record`; `src/research_foundry/services/planning.py` `_WRITEBACKS`

12. **Export schema v1.2 includes run metadata**: `rf run export` emits `cost_usd`, `model_profiles`, `source_count_by_type`, `writebacks` summary, `linked_projects`, `category`, and `tags`. All data routes through `export_service`; sensitivity redaction is enforced at the export layer.
    _Source_: `src/research_foundry/services/export_service.py` `EXPORT_SCHEMA_VERSION`

13. **`rf backlog reconcile` defaults to dry-run**: Reconciliation never writes changes unless `--write` is explicitly passed. Status advances are forward-only; non-null links are never overwritten.
    _Source_: `src/research_foundry/services/backlog_metadata.py` `reconcile_backlog`

---

## 4. Enhancement Backlog

- **[BL-1] Real `claude_agent_sdk` adapter mode**: Implement the live execution path for the `claude_agent_sdk` adapter so it actually invokes the Claude Agent SDK Python package for source discovery.
  _Status_: deferred
  _Rationale_: Real mode is intentionally unimplemented in the 7-day MVP. The deterministic stub fulfils the offline demo requirement. Revisit when the Agent SDK interface stabilises and there is a concrete discovery use case to validate against.

- **[BL-2] Live web discovery adapter (gpt_researcher / paperqa2 real mode)**: Enable non-stub execution of the `gpt_researcher` and `paperqa2` adapters by completing the opt-in real-mode path and its associated credential plumbing.
  _Status_: deferred
  _Rationale_: Requires credential management and network access in the workspace; excluded from the offline-first MVP. Depends on the `.[research]` extra being stable.

- **[BL-3] Parallel swarm execution**: Allow `rf swarm run` to run multiple adapters concurrently rather than sequentially, with a fan-in merge step before writing `source_candidates.yaml`.
  _Status_: candidate
  _Rationale_: Sequential adapter execution is safe but slow for runs with multiple live adapters. Parallelism could reduce discovery wall-clock time significantly on larger research briefs.

- **[BL-4] Automated MeatyWiki / CCDash upstream push**: Extend `rf writeback` to push bundles to a live MeatyWiki API and CCDash endpoint rather than writing only to the local mirror directories.
  _Status_: deferred
  _Rationale_: Local-mirror writebacks fulfil the MVP requirement. Upstream push requires stable API contracts from MeatyWiki and CCDash that do not yet exist.

- **[BL-5] `rf swarm run` candidate → source-card auto-conversion**: Add an `--auto-ingest` flag to `rf swarm run` that converts accepted candidates in `source_candidates.yaml` into source cards via `rf ingest` in a single step, removing the manual loop.
  _Status_: candidate
  _Rationale_: The current two-step (swarm run → manual ingest per candidate) is correct but verbose. Auto-conversion would reduce agent turn count for high-volume discovery runs, provided a sensible acceptance filter can be expressed.

---

## 5. Changelog

### v1.1.0 — 2026-06-22
- Added capability coverage for: Search Router (`rf search`), URL fetch (`rf fetch`), run export (`rf run export`/`rf run list`), loopback API (`rf serve`), backlog reconcile (`rf backlog reconcile`), `--backlog-idea-ref` on capture, decision_record auto-emit
- Added invariants 9–13 covering: keyless provider degradation, fail-closed LAN bind, decision_record auto-emit, export schema v1.2 fields, dry-run default for backlog reconcile
- SKILL.md §2 Path C (Search Router) added; §2 Path B updated with backlog-idea-ref and reconcile lifecycle; §3 writeback step broadened; §4 rf serve governance surface added

### v1.0.0 — 2026-06-13
- Initial SPEC.md authored and published as `stable`
- Capability coverage matrix: 12 intents across 4 SKILL.md sections
- Invariants defined: 8 numbered, all testable
- Enhancement backlog: 5 entries (BL-1 through BL-5)
- Related skill cross-link: `research-foundry`

---

## 6. Integration Points

| Agent / Command | Invocation Pattern | Notes |
|-----------------|--------------------|-------|
| Claude Code multi-agent Workflow / ultracode | Outer orchestrator; loads skill via `Skill("research-foundry-swarm")` | The agent harness is the discovery orchestrator; it feeds `rf ingest`, it is not called by `rf` |
| Any agent bootstrapping a new RF workspace | `Skill("research-foundry-swarm")` | Requires `uv` on PATH and `rf` installable from the project root |
| `research-foundry` skill | Co-loaded for full pipeline coverage | This skill covers setup and swarm wiring; `research-foundry` owns the 21-step loop and per-command reference |

**Note**: This skill expects a working `rf` installation on PATH. Agents should load this skill before loading `research-foundry` when starting from a fresh workspace; for an already-initialised workspace running a pipeline step, `research-foundry` alone is sufficient.

---

## 7. Success Signals

- A freshly bootstrapped workspace passes `rf doctor` with green status and no schema or governance errors before any pipeline command is issued.
- Every research run passes through `rf verify --fail-on-unsupported` before `rf bundle` is called; no evidence bundle exists without a clean verify exit (code 0).
- No unsupported material claims appear in published reports; all non-ledger sentences carry an explicit `Inference`, `Speculation`, `Mixed evidence`, or `Contradicted` label.
- `rf guard check --profile <profile>` is the first `rf` command in every run transcript; no model call or adapter invocation precedes it.
- Agents correctly distinguish `source_candidates.yaml` (discovery output, not yet cards) from `runs/<run_id>/sources/src_*.md` (ingestible source cards), and always run `rf ingest` between the two.
- When the `claude_agent_sdk` adapter is mentioned, agents understand it targets the Python SDK library, not the Claude Code CLI, and do not attempt to call Claude Code from within `rf`.
- Token usage for workspace setup stays low because agents route to SKILL.md §1 directly and do not re-read the full pipeline loop from the `research-foundry` skill for bootstrap-only tasks.
