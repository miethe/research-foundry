---
doc_type: exploration_spike
title: "Risk Leg — Runs Frontend Exploration"
leg_id: risk
charter: docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md
status: complete
created: 2026-06-19
assigned_to: backend-architect
---

# Risk Findings — Runs Frontend

## Methodology

Grounded in direct code and artifact inspection:

- `src/research_foundry/paths.py` — canonical run sub-tree layout (`RunPaths`)
- `src/research_foundry/schemas.py` — schema loading and validation contract
- `src/research_foundry/registry.py` — registry index design (`run_index.yaml`, etc.)
- `src/research_foundry/cli_commands.py` — complete `rf` CLI surface (all commands)
- `src/research_foundry/cli.py` — CLI wiring and entry point
- `src/research_foundry/services/verification.py` — verifier check contract
- `schemas/*.schema.yaml` — all 20 JSON Schema Draft 2020-12 files
- `runs/rf_run_20260614_*/` — two complete real run directories inspected in detail
- `registries/run_index.yaml` — 38 indexed entries vs 38 actual `rf_run_*` dirs

---

## Risk Register

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **R1. Artifact schema drift** — all 20 schemas use `additionalProperties: true` at root and every nested object. There is no `schema_version` enforcement at the top level for most artifact types (only `source_card` and `report_frontmatter` carry a `schema_version` field; `run.yaml` carries `schema_version: 0.1` but the schema does not enforce version). New fields added by agents do not break validation, but removed or renamed required fields (e.g., `claim_id`, `intent_id`, `run_id`) would silently produce empty or broken UI cells. | high | medium | Pin the viewer to reading only schema-required fields (`required:` list in each schema). Treat any additional field as optional display metadata. Alert the user when a `required` field is absent rather than crashing. Never render absent-field absences as data corruption. |
| **R2. Hardcoded absolute paths in registry and artifact files** — `registries/run_index.yaml` stores `run_dir` as an absolute path (e.g., `/Users/miethe/dev/homelab/development/research-foundry/runs/...`). `reviews/verification.yaml` stores `report_path` and `claim_ledger_path` as absolute paths. If the workspace is moved, cloned, or served from a different mount point (e.g., agentic-nuc vs. local dev machine), these paths are wrong. `FoundryPaths.discover()` re-derives paths at runtime from cwd, but the frozen registry does not. | high | high | The frontend must use `FoundryPaths.discover()` logic (walk up to `foundry.yaml`) to re-derive `runs/<run_id>/` paths from workspace root rather than trusting stored `run_dir` values. The run_index is useful for listing (metadata only); all file reads must re-derive paths from workspace root + run_id. |
| **R3. No `rf run list` or `rf run export` command exists** — the current CLI has no machine-readable run enumeration command. The only listing surface is `rf status` (prints a Rich table, not JSON) and `registries/run_index.yaml` (a flat YAML with no query capability). A frontend serving data over a loopback API or static export must either read the registry YAML directly or implement a new `rf run list --json` CLI sub-command. | high | confirmed | Author `rf run list --format json` (or equivalent) as the stable machine-readable contract for the frontend's discovery path. Without this, the frontend couples directly to internal registry YAML layout, which is an internal implementation detail not in the service contract. |
| **R4. Status field staleness** — `run.yaml` status field on every inspected run is `planned` even for runs that have complete evidence bundles, verification results, and writebacks. The registry `run_index.yaml` mirrors this stale status (status field frozen at index-time: `indexed_at` matches the `plan` stage timestamp). The `evidence_bundle.yaml` correctly shows `status: verified`. The frontend must resolve run completeness from the evidence bundle, not from `run.yaml` or the index. | medium | confirmed | Resolve run lifecycle state from `evidence_bundle.yaml.status` + presence of `reviews/verification.yaml.passed`. Never display `run.yaml.status` as the run's current state without cross-referencing the evidence bundle. |
| **R5. Read-path coupling to internal directory layout** — `RunPaths` in `paths.py` defines the canonical layout (22 path properties). If any path property is renamed or reorganized in a future RF release, all frontend path references break silently (no error; the file simply does not exist). The layout is not versioned independently of `schema_version`. | medium | medium | The frontend's file-reading layer must mirror `RunPaths` exactly and fail loudly (display "artifact not found" per artifact) rather than treating missing files as empty data. On RF version upgrade, the paths layer is the only coupling point to audit. |
| **R6. Partial-population runs** — runs in `status: planned` state have directory scaffold (`sources/`, `claims/`, etc.) but no files inside those directories. The frontend must handle every artifact as optional and render lifecycle-appropriate empty states (e.g., "not yet extracted" vs. "extraction failed"). All 38 runs inspected have the full directory scaffold but some subdirectory contents vary. | medium | high | Define a lifecycle state machine in the frontend: `planned` → `sources_ingested` → `extracted` → `claim_mapped` → `synthesized` → `verified` → `published`. Derive current state from artifact presence (run_trace.jsonl events are also present and carry stage timestamps). |
| **R7. Scope creep toward write/edit** — the claim ledger and governance verdict formats include `reviewer_notes` (string), `required_fix` (string), and `approved_for_writeback` (boolean) fields that are natural edit targets in a UI. A read-only viewer that displays these fields creates strong affordance pressure to add inline editing, which would bypass the `rf verify` / `rf council` governance gates. | medium | high | Enforce read-only constraint architecturally: the serving layer (static export or loopback API) must expose GET routes only with no mutation surface. No form elements in the UI. Label all displayed values as "view-only" explicitly in the component library. Document the constraint in the ADR if built. |
| **R8. Maintenance cost for a single-operator project** — RF is a one-operator project (Nick Miethe). A dedicated frontend adds a second codebase (JS/TS framework, build toolchain, dependency graph) requiring independent maintenance when RF evolves. The MkDocs site (commit 1ae5bff) already exists as a static output surface. | medium | medium | Minimize the frontend's surface: use the smallest viable framework or consider a static export approach (`rf run export --json` piped to a pre-built SPA shell) that requires no runtime server. Evaluate whether the MkDocs case-study site can be extended with a dynamic component (e.g., a single vanilla-JS file reading JSON output from a loopback endpoint) before committing to a full frontend build. |
| **R9. Sensitivity/governance data leakage** — source cards carry `sensitivity` fields (`public`, `personal`, `work_sensitive`, `client_sensitive`). The claim ledger's `work_sensitive_claims_block_public_report` verifier check enforces this at report time, but a frontend that directly reads source cards and renders their `extracted_points` could surface `work_sensitive` or `client_sensitive` content to any user who can reach the loopback port. The redact service (`rf redact`) exists but is not called automatically. | high | medium | The loopback read API (if built) must enforce a sensitivity filter: never serve source card body content for sensitivity levels above the operator's configured threshold. Alternatively, the static export step (`rf run export`) should apply redaction before writing the JSON the frontend consumes. |
| **R10. Nested `runs/runs/` anomaly** — four run directories exist inside `runs/runs/` rather than `runs/` (observed: `rf_run_20260614_closed_loop_telemetry_to_artifact_feedback`, `hybrid_bm25...`, `semantic_entity...`, `what_monetization...`). These are not in the `run_index.yaml` and would be invisible to any frontend that reads only from the registry or only from `runs/` top-level glob. | low | confirmed | The frontend's run discovery must walk `runs/**/run.yaml` (recursive glob, depth 2 or 3) rather than trusting the registry or a flat `runs/` glob. The nesting is likely a swarm artifact placement bug but it is observable data. |
| **R11. `run_trace.jsonl` as a lifecycle oracle** — the telemetry `run_trace.jsonl` file carries stage events (`plan`, `extract`, `claim_map`, `synthesize`, `verify`) with timestamps. It is a better lifecycle oracle than `run.yaml.status`. However, it uses `append_jsonl` (newline-delimited JSON) which requires a JSONL parser, not standard JSON. A frontend reading this file must handle JSONL parsing. | low | medium | Use the evidence bundle + individual artifact presence as the primary lifecycle signals. Use `run_trace.jsonl` as optional telemetry display only (cost timeline, stage timestamps). Do not make lifecycle state depend on JSONL parsing being available. |

---

## Deal-Killer Assessment

**REFUTED. The charter's declared deal-killer does not fire.**

The precise deal-killer text: "a faithful read-only viewer would require a new always-on backend service or an LLM on the recall path."

Evidence:

1. **The complete run entity model is deterministically derivable from on-disk artifacts.** Every entity — `run.yaml`, `research_brief.md`, `source_candidates.yaml`, `sources/*.md` (source cards), `extractions/*.md` (extraction cards), `claims/claim_ledger.yaml`, `claims/contradiction_log.yaml`, `claims/inference_log.yaml`, `reviews/verification.yaml`, `reviews/council_review.yaml`, `reviews/critic_review.yaml`, `reviews/governance_review.yaml`, `evidence_bundle.yaml`, `writebacks/meatywiki_writeback.md`, `writebacks/skillbom_candidate.md`, `writebacks/ccdash_event.yaml`, `writebacks/intenttree_update.yaml`, `writebacks/arc_review_request.yaml`, `telemetry/token_costs.yaml`, `telemetry/run_trace.jsonl` — is a file-backed YAML or Markdown artifact with a JSON Schema and a defined path in `RunPaths`. No entity requires LLM inference to reconstruct.

2. **No LLM is on the recall path.** The verifier (`verification.py`) explicitly states it "never calls the network and never needs an API key." All schemas use deterministic validation (`jsonschema.Draft202012Validator`). The registry is a flat YAML file. Reading a run requires only filesystem access.

3. **A thin loopback read API is compatible with AOS constraints.** The global CLAUDE.md documents that sibling services (CCDash `:8090`, IntentTree `:8032`, MeatyWiki Portal `:8765`) all bind loopback or LAN. A loopback-only `rf serve` command exposing read-only GET routes would be entirely consistent with the AOS pattern. It would not be "always-on" if started on-demand (`rf serve` in the foreground, browser tab open, stop when done). Alternatively, a static export (`rf run export --json <run_id>`) that a SPA reads from the filesystem avoids a server entirely.

4. **However: the absence of `rf run list --json` and `rf run export --json` means the machine-readable contract does not yet exist.** The frontend cannot be built stably against internal file paths and registry YAML as its only contract. This is a **conditional go trigger** (matches the charter's "Conditional" verdict criterion): the entity model is derivable, but a machine-readable export contract must be authored first.

**Additional deal-killers found: NONE.** No new unconditional deal-killers were identified. The risks in R1–R11 are all engineering risks with defined mitigations, not architectural impossibilities.

---

## Blast-Radius Map

Items that could be burdened or broken if the frontend is built:

**rf CLI contract**
- Adding `rf run list --json` and `rf run export --json` extends `cli_commands.py` and `services/`. Risk: low. The CLI follows a consistent pattern (thin command body, service call, Rich render). A `--format json` flag on `rf status runs` and a new `rf run export` command fit the existing pattern cleanly.
- Any rename of `RunPaths` property names (e.g., `claim_ledger` → `claims_ledger`) would silently break a frontend. Mitigation: treat `RunPaths` as a stable interface and version it.

**registries/run_index.yaml**
- The index currently stores absolute `run_dir` paths. If the frontend starts consuming the index as a discovery source, any workspace move breaks it. The index format is undocumented in the service contract. Risk: medium if the frontend relies on it.

**schemas/*.schema.yaml**
- All schemas carry `additionalProperties: true`. The frontend binds to `required:` fields only. Schema changes to required fields are a breaking change for the frontend. Currently zero `required:` fields have changed since initial authoring (all schemas are at `schema_version` 0.1 or unversioned). Risk: low today, medium as RF matures.

**Governance gate integrity**
- A read-only viewer that renders `sensitivity: work_sensitive` source card content (R9) could expose governed content. This does not break RF's write path but undermines the governance model. A loopback API must enforce sensitivity filtering to avoid weakening the governance invariant without any code change.

**Sibling AOS services**
- No blast radius on CCDash, IntentTree, MeatyWiki, or SkillMeat. The frontend is read-only and file-backed; it does not write to any integration target. The `writebacks/` artifacts are already written by `rf writeback` and the frontend only reads them.

**MkDocs site**
- No conflict. The MkDocs site (`website/`) is a separate static output surface. A dynamic viewer would complement it, not replace it. If the viewer is implemented as a JSON-reading shell embedded in the MkDocs build, it shares the same deployment.

**Performance on agentic-nuc**
- 38 runs currently exist. A full in-memory load of all claim ledgers (avg ~96 claims/run based on one sampled run) is approximately 38 x 50KB = ~1.9MB of YAML. Negligible. At 1000 runs it remains manageable. No performance blast radius.

---

Risk confidence score: **0.82**

Basis: The run artifact layout, schema set, CLI surface, and registry design are directly confirmed from code and real on-disk artifacts. The primary gap is that sibling AOS web app internals (CCDash, IntentTree web, SkillMeat web) were not directly inspected in this leg (assigned to the priorart leg). Risk R9 (sensitivity leakage) is assessed from schema inspection alone and may have additional nuance from the governance service. The nested `runs/runs/` anomaly (R10) is confirmed from filesystem inspection but its origin and frequency are unknown.
