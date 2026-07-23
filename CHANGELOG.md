# Changelog

All notable changes to Research Foundry will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

#### **Runs/Claims/Evidence Workspace Isolation & Public Visibility (DF-004)**

- **Runs now carry an owner (`workspace_id`) and a `visibility` field
  (`workspace` | `public`).** `POST /runs` stamps `workspace_id` from the
  authenticated identity, never from client input (mirrors
  `builder_service.create_draft`); provenance is always recorded.
- **Workspace-scoped run reads.** The six run read endpoints (`GET /runs`,
  `GET /runs/{id}`, `.../claims`, `.../context`, `GET /source-cards/{id}`,
  `GET /reports/{id}/anchors`) now gate on the caller's workspace under
  enforcement: a cross-workspace run returns an indistinguishable `404` (never a
  `403` — no existence leak), and `GET /runs` filters unreadable runs from the
  list. A `visibility: public` run is readable across workspaces (read only).
- **Writeback dispatch is owner-gated.** `POST /runs/{id}/writeback/approve`
  now verifies run ownership *before* any external dispatch side effect; `public`
  visibility does **not** grant cross-workspace writeback.
- **Agent-job attribution can no longer be spoofed (audit row 9).**
  `create_job` and the `agent_job_launched` audit event stamp `workspace_id`
  from the authenticated identity, not the client-supplied body value.
- **Legacy run backfill.** `workspace_migration_service` gains a run-aware
  `dry_run_runs`/`backfill_runs`/rollback path (default `"default"`, zero-write
  dry-run, JSON manifest), mirroring the WKSP-30x draft-backfill contract.
- **Non-breaking:** `identity=None` (single-operator-trust / LAN `single_user`)
  and advisory-mode installs are byte-identical to before; enforcement is the
  existing shared opt-in flag. Adversarial-multi-tenant readiness still requires
  a formal DI-1 re-audit (see `docs/dev/architecture/adr-runs-workspace-isolation.md`).

#### **Public Multi-User Release Activation — Deployment Modes & Non-Human Principals**

- **`deployment_mode` presets (`single_user` | `multi_user`)** — A single `deployment_mode`
  config key in `foundry.yaml` (or `rf serve --mode single_user|multi_user`) now composes the
  previously-independent RBAC/workspace-isolation/rate-limit knobs into one validated posture.
  `single_user` (default) is byte-identical to pre-existing behavior; `multi_user` defaults
  RBAC enforcement, workspace isolation, and rate limiting to enabled, with any explicit
  per-knob override in `foundry.yaml` still taking precedence.
- **Service accounts and personal access tokens (PATs)** — New non-human principal types
  backed by a token store extending `rbac.db`. Service accounts get a single fixed role and a
  rotate-on-issue access token; users can self-issue PATs (or have one issued on their behalf by
  an owner/admin) capped at their current workspace role, re-checked at every use so a later
  role downgrade revokes elevated PAT privilege immediately. Tokens are hashed at rest and shown
  only once at issuance — no plaintext secret is ever persisted, logged, or re-displayed.
- **Admin API for principal + token management** — `POST/GET/DELETE /api/admin/service-accounts`,
  `POST/GET/DELETE /api/admin/service-accounts/{id}/tokens`, and `POST/GET/DELETE
  /api/admin/pats` let owners/admins issue, list, rotate, and revoke both principal types;
  `GET /api/admin/deployment-mode-status` exposes the resolved `deployment_mode` and the
  pass/fail status of every startup-gate condition for read-only operator troubleshooting.
- **Admin UI panels for service accounts and PATs** — New Service Accounts and Personal Access
  Tokens panels in the admin settings UI cover the full issue → view → revoke lifecycle for
  both principal types.
- **Agent-job execution identity binding** — Under `deployment_mode=multi_user`, agent jobs
  launched without an explicit human actor resolve to a configured default service account
  (`agents.default_service_account_id`) instead of an anonymous/`None` identity; `single_user`
  behavior is unchanged.

#### **Rights & Evidence-Item Entity Model**

- **`rf rights` CLI command group** — New commands for creating and inspecting rights
  records against source cards and evidence items, including a deterministic
  `rf rights validate --as-of` check that flags rights that have lapsed, expired, or
  diverged from their declared extensions as of a given point in time.
- **Five new canonical schemas** — `rights_record`, `rights_extension`,
  `content_reuse_assessment`, `permission_record`, and `rights_failure` capture the
  full lifecycle of a source's usage rights, from initial grant through extension,
  reuse assessment, and permission failure.
- **Taxonomy and `judgment_basis` capture** — Evidence items now record an explicit
  taxonomy classification and the judgment basis behind any reuse/rights
  determination, closing a prior gap where rights status could be inferred without
  a recorded rationale.
- **Governance write-ceiling guard on rights-status fields** — Rights-status fields
  (e.g. `CLEARED_*`, `counsel_approved`, `attested`) are now fail-closed by
  construction: no agent-driven write path can set these statuses without passing
  through the governance guard.
- **Release-gate predicate for unassessed `judgment_basis`** — Commercial-release
  evaluation is now blocked when any evidence item in scope carries an unassessed
  `judgment_basis`, preventing rights-unreviewed content from clearing a
  commercial-release gate.

#### **RFUP External-Routing Gap Closure — `rf verify` Gates**

- **`pediatric_cds` evidence-card schema hard-gate** — `rf verify` now validates any evidence
  card carrying a `pediatric_cds` block against a formal JSON Schema
  (`src/research_foundry/schemas/pediatric_cds.schema.json`) and fails closed
  (`pediatric_cds_schema_invalid`) when the block is structurally incomplete or malformed. Cards
  without a `pediatric_cds` block are unaffected.
- **Quote-vs-source fidelity check** — `rf verify` now runs a new character-level fidelity check
  (`services/quote_fidelity.py`) comparing each cited quote against its source text, after a
  normalization allowlist (NFKC, whitespace collapsing, quote-mark style). Residual differences
  after normalization are flagged as a `warning`-severity finding, never silently
  auto-corrected — catching corruption such as PMC's superscript-digit stripping
  (`×10⁹/L` → `×10/L`). Cards with `extraction_status: locator_only` (no stored source text to
  diff against) emit a distinguishable non-blocking `quote_fidelity_unverifiable_locator_only`
  warning instead of being skipped or failed.
- **Eligibility-driven strict exact-passage mode (auto-strict default)** — Threshold/clinical
  claims now default to strict exact-passage verification automatically when the cited card
  carries a `pediatric_cds` block or an elevated-sensitivity tag, per the new default policy in
  `config/claim_policy.yaml`. Non-clinical, non-elevated-sensitivity claims and runs are
  unaffected and continue to use warn-only exact-passage checking.

#### **Writeback Approve & Dispatch**

- **`POST /api/runs/{run_id}/writeback/approve`** — Operators can now approve a run's evidence
  bundle and dispatch it to MeatyWiki/SkillMeat/CCDash writeback targets over HTTP, gated by
  owner/admin RBAC, with full per-invocation audit logging (one audit row per outcome: success,
  partial, blocked, exception). This is the first HTTP-gated write path for what was previously
  a CLI-only (`rf writeback`) operation — the CLI path itself is unchanged.
- **"Approve & Dispatch" action on the runs-viewer Writeback tab** — Adds a confirmation dialog
  and per-target (MeatyWiki/SkillMeat/CCDash) outcome rendering that distinguishes governance-policy
  rejections from generic errors.

#### **Runs-Viewer Writeback Review Governance View (FR-13)**

- **Export schema 1.5 → 1.6** — `_collect_writebacks()` now populates
  `writebacks.reviewer_notes`/`required_fix` (sourced from the council review
  packet, `reviews/council_review.yaml` — not `evidence_bundle.governance`,
  which does not declare either field) and a concrete typed
  `writebacks.previews[]` array (`{target, filename, content_type, content}`,
  one entry per present writeback file). Preview content passes through the
  existing `_redact_str_values` sensitivity gate — writeback content is not
  exempt from redaction. Additive/nullable only; pre-1.6 exports omit the new
  keys and degrade gracefully. Schema-bump reviewed and approved by
  `backend-architect` per the frozen-schema policy gate.
- **Writeback tab upgraded to a governance review surface** — the runs-viewer
  Writeback tab (`RunDetailWorkspace.tsx`, shared by the full-page and modal
  paths) now renders a governance status panel (approval state, reviewer
  notes, required fix — each with an explicit "Not set" state) plus one
  candidate card per exported preview. `.md` candidates render as formatted
  Markdown; `.yaml` candidates render as a pre-formatted structured block.
  Strictly read-only — no button, form, or control anywhere in the tab can
  set `approved_for_writeback`, `reviewer_notes`, or `required_fix`; approval
  remains a CLI-only operation (`rf bundle --approve`).

#### **Assertion Ledger Activation — Workspace-Scoped Writes, Historical Backfill, and Merge UI**

- **Workspace-scoped, fail-closed write contract** (P1) — Shared assertion-ledger write gate enforces workspace isolation via `assertion_workspace.resolve_or_deny()`; single-operator mode resolves to "default" workspace; writes rejected (typed denial, zero mutations) when workspace is absent or unresolved.
- **Fixed extraction/ingest contract** (P1.5, blocking) — Assertion text now binds to source card's verbatim `extracted_points[].quote` instead of paraphrased extraction text; passage segmentation wired into `AssertionRegistry.ingest()` via `source_cards.ingest_source()` to enable quote recovery and reduce abstention rate. End-to-end verification: >=1 exact-match materialization; flag-off regression confirmed.
- **Historical backfill driver** (P2) — Idempotent, resumable migration of claim ledger facts to assertions via `rf assertion backfill [--dry-run] [--run ID] [--workspace-id ID]` CLI; accepts low exact-match-eligible yield (94.78% fact-level materialization on real corpus of 42 runs after P1.5 fix; 156 abstentions at document boundaries and passage-binding gaps; 23 fuzzy-recovery candidates flagged for spot-check). Shares `AssertionRegistry.ingest()` and `AssertionMaterializer.materialize_run()` write paths with forward driver; skip-and-continue mode tolerates trailing inference/speculation claims in claim ledger.
- **Forward write driver** (P3) — `rf ingest` command now threads `assertion_registry_workspace_id` and `ledger_write_allowed` into `source_cards.ingest_source()` to populate ledger for new runs; flag-off path byte-identical to pre-activation behavior.
- **Reuse reachability** (P4) — LaunchRunRequest now exposes `reuse_assertion`, `reuse_workspace_id`, and `required_reuse_edition_id` fields, wired to existing `assertion_reuse` and `assertion_impact` decision services; denials surface via `block_authoritative_reuse`.
- **Canonical-merge UI activation** (P5) — `VITE_RF_CANONICAL_CLAIMS_ENABLED` build flag wired through standard deploy/bootstrap path (mirroring `RF_UI_LOOPBACK` pattern); canonical merge-review controls in ClaimAuditWorkbench now render when flag is enabled.

#### **Reusable Assertion Ledger — Default-Off Readiness Controls (P8)**

- **Three independent default-off controls** under `foundry.assertion_ledger`:
  ledger writes, automated reuse, and canonical claims. Reuse and canonical
  capability checks fail closed unless ledger writes are also explicitly
  enabled; no private rollout or public behavior is enabled by this change.
- **Local readiness rehearsal** via `scripts/assertion_ledger_readiness.py`:
  idempotent migration/backfill dry-run and disable/rollback receipts plus
  aggregate-only health/economics metrics that omit passage text, source
  locators, workspace identifiers, and external-writeback payloads.
- **Operator and user documentation** for assertion-only operation, denial and
  correction semantics, private-boundary requirements, and recovery.

#### **Workspace Isolation Enforcement (WKSP-304) — Query-Layer Row-Level Scoping**

- **New `workspace_isolation_enforcement` config flag** — Controls workspace row-level
  isolation gate behavior (orthogonal to existing `auth.rbac_enforcement`; see
  `src/research_foundry/config.py`). Three modes:
  - `auto` (default) — Enforced when `auth.provider != "none"`; advisory-only when
    `auth.provider == "none"` (preserves single-operator-trust behavior for loopback
    deployments).
  - `enabled` — Force enforcement on regardless of provider, even with `auth.provider=none`.
  - `disabled` — Force enforcement off; **fail-closed** — only permitted on loopback bind
    hosts (`127.0.0.1`, `::1`, `localhost`). Non-loopback deployments with `disabled`
    raise `ValueError` at startup, preventing accidental unsafe disclosure on public binds.

- **Query-layer enforcement via `require_workspace_scope()`** — When enforcement is
  active (resolved truthy), `workspace_id` scoping is evaluated at query time via WHERE
  predicates in `catalog_service`, `builder_service`, and `agent_job_service`, not
  post-fetch filtering. Single-operator (identity=None) fallback is short-circuited
  structurally before any enforcement-flag branch — isolation checks are bypassed
  unconditionally in single-operator deployments, unchanged from pre-enforcement behavior.

- **Read denials return HTTP 404 (not 403)**; list endpoints silently omit foreign-workspace
  rows. Mutation attempts against another workspace's resource are denied with 404.

- **Write-path identity threading** — `builder_service.create_draft()` now accepts optional
  `identity` parameter; when present, persisted `workspace_id` is stamped from
  `identity.workspace_id` (ensuring the draft records the workspace of its creator). This
  ensures drafts created while enforcement is active are readable by their creator under
  the same enforcement rules. Single-operator path (`identity=None`) is byte-identical to
  pre-enforcement behavior.

- **Share-link decoupling (P5 fix-now gap)** — Draft creation via the blank/template
  route now threads `identity` through to `create_draft()`, closing the P5.5(b) enforcement
  gap where drafts persisted with `workspace_id=None` and became unreadable by their own
  creator once enforcement was forced active (commit `5418568`).

- **Workspace scoping validates across all catalog surfaces**: query builders, agent jobs,
  and report drafts. Pre-existing single-operator deployments (`auth.provider=none`)
  experience no behavior change — isolation enforcement is structurally skipped for
  identity=None regardless of the `workspace_isolation_enforcement` flag value.

#### **HTTP Run-Launch Endpoint — `POST /api/runs` (scaffold + register only)**

- **`POST /api/runs`** — Launch a new run over HTTP: scaffolds and registers a
  run via the deterministic `capture -> triage -> plan` chain (given `text`)
  or `plan` alone (given an already-triaged `intent_id`), so orchestrators
  (e.g. Hermes) can trigger runs without shelling the `rf` CLI. Returns
  `{run_id, status, intent_id, raw_idea_id, brief_path, swarm_path,
  routing_path, next_step}` on `201`. Gated by
  `Depends(require_role("owner", "admin"))`, mirroring the `agent_jobs.py`
  mutation-route pattern; audited via `audit_service.record_event`
  (`mutation_type="run_launched"`).
  - This endpoint performs the deterministic scaffold+register chain
    **only** — it does not spawn, drive, or poll the Path B Claude-agent
    discovery swarm. Poll the existing `GET /api/runs/{run_id}` for status;
    run the swarm out-of-band against the returned `run_id`.
  - New service module `research_foundry.services.run_launch.launch_run(...)`
    wraps the existing `capture_idea`/`triage_idea`/`plan_run` functions
    unmodified; owns only the "exactly one of `text`/`intent_id`" validation.

#### **RF Upstream Evidence Foundry — Machine Contract, Hard-Gating, PDF Extraction & Run Seal**

- **`rf_schema_version` Machine Contract** — `RF_SCHEMA_VERSION` ("1.0.0") is stamped additively across CLI `--json` outputs, `rf verify` output, the LAN API (`/api/runs`, `/api/reports`, `/api/catalog`), and run-export, enabling versioned, hard-gatable machine contracts for downstream consumers and preventing version-skew integration failures.
- **Exact-Passage Hard-Gating** — New `verify.exact_passage: warn|strict` config key (default `warn`) plus `--exact-passage` CLI override on `rf verify` backs a new `exact_passage_present` eligibility check; `strict` mode hard-blocks claims citing a source card without a resolvable exact quote/passage anchor.
- **Governed PDF Extraction** — `rf fetch` now extracts text from PDF URLs via a new optional `research-foundry[pdf]` extra (pypdf); source cards gain an `extraction_status` field (`full_text|partial|locator_only`) tracking extraction fidelity and enabling intelligent fallback to locator-only citation when full text is unavailable.
- **Council Verdict Normalization** — `arc_council` adapter verdicts are now normalized into a controlled `approve|concern|block` enum (raw verdict retained in metadata); CLI/YAML-only, no run-export schema change.
- **Run Seal / Tamper-Evidence** — New additive `--seal` flag on `rf run export` computes a sha256 content digest over the run's evidence chain (claim ledger + source cards + report) and writes an append-only lineage record, enabling offline verification and detecting accidental or malicious mutations to evidence artifacts.

#### **Agent Jobs API — Embedded Research with Credential Isolation (P4)**

- **`/api/agent-jobs` HTTP endpoints** — Launch, list, stream events, accept, cancel, and query status for governed agent research jobs. Jobs run under subprocess-per-job credential isolation (ADR-002: Credential Process Isolation), preventing provider credentials from leaking into job artifacts, browser network traffic, or telemetry payloads.
  - `POST /api/agent-jobs/launch` — Start a new agent research job with a provider profile reference and optional parameters. Credentials are staged in a job-scoped temp file (0600 permissions, unlinked after provider reads).
  - `GET /api/agent-jobs` — List all jobs with filtering by status, provider, workspace.
  - `GET /api/agent-jobs/{id}/events` — Server-Sent Events (SSE) stream of job lifecycle events (queued, running, completed, failed, cancelled).
  - `POST /api/agent-jobs/{id}/accept` — Human acceptance endpoint; moves staged outputs to the catalog. Only accepted outputs appear in report drafts or writebacks.
  - `POST /api/agent-jobs/{id}/cancel` — Cancel a running job (soft: allows graceful shutdown; hard: force-terminate subprocess).
  - `GET /api/agent-jobs/{id}/status` — Get current job status and telemetry summary (event count, cost estimate, key fingerprint).

- **ResearchAgentProvider abstraction & adapters** — `claude_agent_sdk` (Claude Agent SDK) and `openai_agents` (OpenAI Agents) provider adapters, both running in isolated subprocesses. Loopback/single-operator deployment only pre-P5 (hard exposure gate per ADR-002). Non-loopback deployment requires Mode-D Gate #4 sign-off (pepper storage finalization).

- **Security properties — SEC-2.1 through SEC-2.3 compliance**:
  - SEC-2.1: Subprocess isolation per `services/agent_job_service.py::spawn_agent_subprocess()` — each job runs in its own process with a scoped temp-file credential.
  - SEC-2.2: Credential temp-file delivery (0600, unlinked after read) via `services/governance.py::stage_temp_credential_file()` — credentials never passed as environment variables (which would leak to grandchild processes).
  - SEC-2.3: Write-time redaction firewall at `services/agent_job_service.py::accept_job_outputs()` — all staged artifacts are scanned and sensitive fields redacted before catalog/report migration per the active sensitivity threshold.
  - FR-14 Key Fingerprinting: Salted HMAC of provider credential (interim pepper via `foundry.yaml` key-profile). Fingerprints logged in `telemetry.job_event` rows; raw credentials never stored or logged.

- **`agents.enabled` feature flag** — Routes return 404 with feature-flag-off (default for production safety); flag-on enables the full governed job flow. Configurable in `config/governance.yaml`.

- **`rf agent-job` CLI commands** — New command family under `cli/agent_jobs.py`:
  - `rf agent-job launch --provider <name> [--params <json>]` — Launch a job and return the job ID.
  - `rf agent-job list [--filter <status>]` — List jobs in the current workspace (JSON or table output).
  - `rf agent-job stream <id>` — Stream events (SSE) to stdout for a running job in real-time.
  - `rf agent-job accept <id>` — Accept staged outputs and merge them into the catalog.
  - `rf agent-job status <id>` — Show current status, event count, cost, key fingerprint, and provider metadata.

- **Job durable state** — New `FoundryPaths.agent_jobs/<id>/` directory structure (mirrors `runs/<id>/` pattern):
  - `job.yaml` — Immutable job metadata (provider, parameters, created_by, workspace_id, key_fingerprint).
  - `events/` — Sequential event log (NDJSON: `timestamp`, `type`, `payload`, `redacted` flag).
  - `staged_outputs/` — Artifacts pending human acceptance (sources, extracted points, inference claims).
  - `accepted_outputs/` — Outputs moved to the catalog after acceptance.

- **Governance & audit** — Job lifecycle and credential handling governed by existing key profiles and policy rules (`config/governance.yaml`); new `job_event` telemetry rows include `key_fingerprint`, provider name, job status, cost, and accept/reject decision for full audit trail.

- **Mode-D Gate #3 (deferred post-merge)** — Real-trace write-time redaction verification; will validate the redaction firewall against a live agent job run (not a synthetic fixture). Deferred to P4.7 post-merge validation.

- **Mode-D Gate #4 (sign-off pending)** — Server pepper storage location (interim: `foundry.yaml` key-profile, final design pending operator sign-off). Blocks non-loopback deployment until resolved per ADR-002.

#### **AOS Correlation IDs — Run Export Schema 1.4**

- **AOS correlation metadata** — `rf run export --json` now emits nullable
  `aos_run_uuid`, `aos_session_uuid`, `aos_feature_uuid`, `aos_artifact_uuid`, and
  `aos_trace_uuid` fields, plus `native_aliases.rf_run_id` so Operator-launched RF
  runs can resolve back to parent AOS run/session context while preserving native RF IDs.
- **Runs-viewer display** — the run detail metadata panel renders AOS UUIDs and RF native
  aliases when present, and degrades to unresolved/not-available states for missing or
  unknown UUIDs.

#### **Runs Viewer — Run Context Panels (FR-14)**

- **Run context panels** — four collapsed, read-only panels in the run detail view: Routing
  Decision, Research Brief, Swarm Plan, and Upstream Entities. Operators can now inspect why a
  particular model profile was chosen, what research brief was given, which adapters ran and in
  what sequence, and which upstream organizational intent triggered the run — without switching
  to the CLI.
- **`run.json` schema 1.3 `context` block** — `rf run export --json` now embeds a top-level
  `context` object containing `routing_decision` (allowlist-filtered from `routing_decision.yaml`),
  `research_brief_md` (verbatim Markdown from `research_brief.md`), `swarm_plan` (allowlist-filtered
  from `swarm_plan.yaml`), and `upstream_entities` (`intent_id`, `ibom_id`, `intenttree_node_id`
  from `run.yaml` and `routing_decision.yaml`). Each field is `null` when its source artifact is
  absent; `context` itself is `null` on pre-1.3 runs. Additive and fully backwards-compatible.
- **Context sensitivity redaction** — the R9 export-time sensitivity gate is extended to
  `context.*` fields: string values in `routing_decision` and `swarm_plan` are redacted when they
  exceed the active threshold; `research_brief_md` is redacted in full when its frontmatter
  `sensitivity:` key exceeds the threshold. No governed content enters `run.json`.

#### **Loopback API — Live Runs without Static Export**

- **`rf serve` command** — Read-only FastAPI server for runs-viewer live data (loopback mode, 
  default port 7432). Serves run summaries, claim ledgers, and source cards directly from 
  on-disk runs without pre-export; enables SPA-to-backend polling for live updates.
- **Loopback API mode** — SPA can read live runs without static export via 
  `VITE_RUNS_FRONTEND_LOOPBACK_API` environment variable. When enabled, `RFRunSummary` and 
  claim queries fetch from the loopback API instead of bundled `index.json`.
- **Gated LAN exposure** — `rf serve --bind-host 0.0.0.0` requires `--auth-mode token` and a 
  configured token; fails closed without one. Prevents accidental unauthenticated exposure of 
  sensitive research data across network boundaries.

#### **Runs Viewer — Swarm, Policies & Library tabs** (enable-disabled-viewer-tabs epic, Wave 2)

- **Swarm tab** — Per-run view (`/runs/:runId/swarm`) visualizing the run's swarm plan
  (swarm, agents, adapters) and routing decision, with a graceful empty state for runs exported
  before metadata enrichment.
- **Policies tab** — Top-level governance view (`/policies`) with a Global Governance Panel
  (key profiles and policy rules from `config/governance.yaml`) and a Per-Run Governance table
  (sensitivity, writeback approval, allowed writebacks, human-review requirement).
- **Library tab** — Top-level index (`/library`) of reusable-output candidates and writeback
  artifacts across runs; stale run references degrade to plain text rather than broken links.
- With these three tabs, all six previously-disabled navigation tabs (Settings, Help, Alerts,
  Swarm, Policies, Library) are now enabled — no dead nav items remain in the viewer.

#### **`decision_record` Writeback — Close the RF→Project Harvest Seam (Gap 1)**

- **`decision_record` writeback** — `rf writeback` now emits an additive `meatywiki/decisions/<slug>.md`
  alongside the existing `source_note` whenever a completed run's claim ledger contains at least one
  `status: inference` claim (typically a `claim_type: recommendation`). The rendered file carries a
  populated **Decision** section (primary inference claim text), **Rationale** (reasoning summaries from
  all inference claims), and **Links** back to the source claim IDs (`inference_basis.from_claims`).
  Recommendation-typed claims appear first. Deterministic-only runs (zero inference claims) silently
  skip the file — no error, no empty record.
- **`rf writeback --decision-record-only --run <id>`** — new flag re-renders only the
  `decision_record_writeback.md` for an existing run without disturbing the run's other writeback
  files. Used for the backfill path over already-completed runs.
- **`scripts/backfill_decision_record_writebacks.py`** — bulk backfill helper that re-renders
  decision records over all runs with inference claims (`--dry-run` by default; `--write` to apply;
  `--run-id` to target a single run).
- **`services/planning.py::_WRITEBACKS`** now declares `{meatywiki: [source_note, decision_record],
  skillmeat: skillbom_candidate, ccdash: execution_event}` so the run contract reflects the full
  writeback set.

#### **Run Metadata Enrichment (v1)** — Linked Projects, Category, and Tags

- **Linked Projects, Category, and Tags on every run** — Research Foundry runs now carry structured
  metadata derived from the research backlog. Each run links to zero or more research ideas via
  `linked_projects[]`, carries a single `category` (from backlog), and inherits a `tags[]` array.
  18 existing runs have been backfilled; new runs created via `rf capture --backlog-idea-ref` or
  `plan_run()` automatically populate these fields at creation time.
- **Portfolio filtering by project, category, and tag** — `FilterTabs.tsx` extends filter controls
  to expose three new sections: "Project" (checkbox list of all linked projects across the
  portfolio), "Category" (checkbox list of categories), and "Tags" (checkbox list of tags). Filters
  use AND-logic; selecting multiple projects/categories/tags narrows results. Empty-state gracefully
  renders when no runs match.
- **Metadata display across all viewer surfaces** — Linked Projects appear as a primary column in
  the RunList portfolio table; RunCard badges display the project (primary) and category; RunDetail
  Overview and RunDetailModal headers show project, category, and tag chips. ClaimAuditWorkbench and
  LineageDetailPanel reference tags in their inspection panes. All surfaces gracefully omit metadata
  when fields are null (pre-migration runs).
- **Enrichment-extra fields** — Export schema bumped to v1.2; `rf run export --json` now includes
  additional run metadata: `cost_usd` (execution cost), `model_profiles` (object with extraction,
  synthesis, and verification model names and budgets), `source_count_by_type` (breakdown of web,
  document, and other source types), and threading of `context.routing_decision` and
  `context.swarm_plan` for downstream swarm analysis. Each field is optional and null-safe.
- **Enrichment overview widgets** — RunDetailWorkspace Overview tab now shows a second "Enrichment"
  section (below the P5 Run Metadata section) with widgets for Cost (formatted USD), Model Profiles
  (compact model-by-model table), Source Count by Type (counts grouped by type), Claim Distribution
  (stacked progress bars for supported/inference/speculation/contradicted/unsupported claims), and
  Writeback Targets (name and status). Each widget renders only when its field is non-null;
  pre-enrichment runs omit the entire section.
- **Backfill script and creation path** — `scripts/backfill_run_metadata.py` idempotently derives
  metadata from the backlog and writes to existing `run.yaml` files (with `--dry-run` support);
  `plan_run()` in the Python core wires metadata at creation; `rf capture --backlog-idea-ref ID`
  captures a new research run tied to a backlog idea.

#### runs-viewer v2.2 — Nav, Titles, and Lineage Fixes

- **Run titles on all list surfaces**: `RunCard` and `StatusLane` buttons now display a human-readable run title derived from the report frontmatter `title:` key, with a slug-humanized fallback (e.g., `rf_run_20260613_roots_wave` → "Roots Wave"). Raw `run_id` slugs no longer appear as the primary display string.
- **`title` field in export**: `export_service.py:export_run()` now derives and includes a `title` field in `run.json`; `prebuild-static-data.mjs` copies it into `index.json`; `RFRunSummary` type updated with `title?: string`.
- **Lineage graph edges render**: `LineageFlow.tsx` now registers `SmoothStepEdge` from `@xyflow/react` as `edgeTypes` at module scope and passes `edgeTypes={edgeTypes}` to `<ReactFlow>`. Edges (connector lines between nodes) now appear in the Lineage tab graph view. Edges carry `className='rv-lineage-edge'` for CSS targeting.

#### **Authentication & RBAC — Public Multi-User Platform (P5)**

- **AuthProvider abstraction with multi-strategy support** — Authentication plugpoint accepts multiple strategies: `local_static` (default for development), `Clerk` (cloud identity), and `OIDC` (seam + stub for future BYO adapters). Provider selected via `foundry.yaml` configuration; frontend shells adapt dynamically to authentication context without code changes.
  - **Frontend auth context** (`AuthContext.tsx`, `LocalLoginForm`, `ClerkShell`) — React hooks and provider shells enable role-aware UI throughout the app. Nav items, affordances, and capabilities adapt based on authenticated user and workspace role.

- **5-role server-side RBAC** — Owner, Admin, Contributor, Analyst, and Viewer roles with capability-driven access control. Each role carries a capability matrix (e.g., Viewer can list/read; Analyst adds extract/synthesize; Contributor adds publish/writeback; Admin manages team members; Owner manages workspaces and policies). Gating enforced on all mutations: catalog entries, reports, research builder jobs, and agent-research jobs.
  - **Workspace isolation migration** — Existing single-workspace Research Foundry instances automatically backfilled with a synthetic default workspace; multi-user instances with N workspaces run dry-run/enforce/rollback schema migrations (DDL on `workspaces` and `team_members` tables; all existing runs migrated to the default workspace; audit log captures migration completion).
  - **Role-gated affordances** — Nav, buttons, and form fields reflect user capabilities; publishing, job launch, settings admin, and team member management are capability-gated at the component level.

- **Audit log with degraded-health detection** — New `audit_log` table records all material team actions: role changes, workspace toggles, writeback approvals/rejections, publish gate decisions, and job launches. Audit events carry actor identity, action, resource, and degraded-health status. Degraded-health events (e.g., sensitivity threshold exceeded, audit gate tripped) are flagged for operator escalation.

- **Rate limits and admin settings UI** — Per-user rate limits on job launches (50/day by default, configurable). Admin-only settings panel exposes team configuration: role mappings, rate limits, sensitivity thresholds, default capabilities, and audit export controls.

- **Fail-closed sensitivity-scoped sharing and publish gates** — Sensitivity threshold evaluated at share/publish time; runs exceeding the threshold are rejected with a clear explanation. Publish-preview mode shows metadata and claim summary redacted; shares and external publish are blocked until sensitivity is below threshold. Gate composition integrates with P4 credential-firewall (AC-3 stub mode).

- **Existence-gate parity** — All catalog endpoints (`/api/runs`, `/api/reports`, `/api/builder`, `/api/agent-jobs`) enforce role-based visibility: Analyst can see only runs in their workspace and assigned jobs; Contributor sees their own and team outputs; Admin/Owner see all workspace content. Existence gates prevent unauthorized 404→403 inference.

### Security

- **DI-1 full-surface workspace-scoping audit gate** — `deployment_mode=multi_user` now
  refuses to start unless both halves of a two-part gate are satisfied: an explicit operator
  acknowledgement (`auth.di1_audit_acknowledged: true` in `foundry.yaml`) AND the project-wide
  DI-1 workspace-scoping audit artifact's `status: accepted`, set only by human sign-off — a
  missing or non-accepted artifact fails closed identically to an unset acknowledgement.
  Acceptance of the current audit authorizes a **trusted-cohort** `multi_user` deployment only
  (non-adversarial callers); it does not certify tenant isolation for runs, claims, source
  cards, or evidence bundles, which remain a tracked follow-up (see the design-spec index for
  this feature).

- **RBAC route gating** — All catalog and reports mutations (`create`, `update`, `publish`, `writeback-approve`), research builder operations, and agent-job launches gated by role-based capability checks. Server validates user role per workspace before allowing operation; frontend enforces capability-gated affordances for UX consistency.

- **Credential firewall composition** — P5 RBAC composes with P4 credential-firewall (AC-3 stub mode). Provider credentials remain isolated in job subprocesses; team-level access controls layer atop individual credential scoping. Both layers remain fail-closed.

- **Sensitivity threshold enforcement** — All public share and external publish endpoints subject to per-workspace sensitivity thresholds; runs exceeding threshold are rejected pre-publication with clear user-facing explanation. Redaction applied on all export/share/publish paths per the active threshold (R9 invariant maintained).

- **Audit-health exposure gate** — An audit-health check now gates share-link resolution and publish-preview success; both return 503 (audit log unavailable) when the audit log is degraded, closing the gap flagged in review as a P5.6 wiring risk. The gate is additive and unconditional (not affected by RBAC-enforcement mode); existing fail-open audit-event recording is unchanged.

### Fixed

#### runs-viewer v2.2

- **Run-click → modal + aligned nav**: StatusLane buttons previously called `setSelectedRunId` without opening `RunDetailModal`. Now calls `setSelectedRunId(runId)` and `setModalRunId(runId)` consistently, so every card click opens the modal and the Runs nav item stays aligned.
- **Default detail tab is Overview**: `coerceDetailTab` fallback changed from `'trust'` to `'overview'` so `/runs/:runId` with no `?tab=` param defaults to the Overview tab. The `'audit'→'ledger'` alias and all other valid tab values are unchanged.

#### `rf run` sub-commands (Python CLI — `runs-frontend-v1` Phase 1)

- **`rf run export --json`** — export a single run's full denormalized claim
  graph to `<run_dir>/run.json`. The export joins `claim_ledger.yaml` →
  `source_card/*.md` → `extracted_points[].quote` in Python; no LLM is on the
  recall path. Sensitivity redaction is applied at export time (default threshold:
  `public`; configurable via `foundry.yaml → viewer.sensitivity_threshold` or
  `--sensitivity-threshold LEVEL`). All file reads go through
  `FoundryPaths.discover()` — stored absolute paths are never used for I/O.
- **`rf run export --json --all`** — batch-export every discovered run
  (recursive `runs/**/run.yaml` discovery, depth ≤ 3; catches nested
  `runs/runs/<id>/` layouts).
- **`rf run export --json --stdout`** — emit the JSON to stdout instead of
  writing `run.json`; useful for piping to `jq` or CI scripts.
- **`rf run list --json`** — JSON array of run summaries, each with a
  `status_derived` field computed from on-disk artifacts (never the stale
  `run.yaml.status`). Derived-status enum: `planned → sources_ingested →
  extracted → claim_mapped → synthesized → verified → published`.

#### Runs viewer SPA (`frontend/runs-viewer/` — `runs-frontend-v1` Phases 2–4)

- **Run-corpus portfolio view** — browse all discovered RF runs as a filterable
  card grid. Filter tabs: `verified`, `needs-review`, `failed`, `planned`.
  Schema-mismatch badge shown when a run's `schema_version` diverges from the
  current export contract.
- **Verification checklist panel** — per-run trust panel renders all named
  checks from `reviews/verification.yaml` with pass/warn/fail indicators and
  deep-link anchors to the relevant claim (`clm_NNN`). No CLI call required.
- **Claim ledger table** — full paginated claim ledger with facet filters by
  status, materiality, claim type, and confidence. Color-coded status badges
  (`supported`, `inference`, `speculation`, `contradicted`, `unsupported`).
- **Claim provenance two-click drill-down** — clicking any claim row opens a
  provenance modal that resolves `claim → sources[] → verbatim evidence quote`
  in one additional click. Inference chains (`from_claims`) are shown with their
  basis; empty-basis inferences (the RIB-018 class) are flagged with a warning
  badge.
- **Sensitivity-gated source cards** — source card bodies render `quote` and
  `summary` only when the export threshold permits; redacted fields display
  `[redacted:sensitivity]`. No governed content is present in `run.json` at
  render time (R9 invariant).
- **Report overlay with live claim chips** — renders `reports/report_draft.md`
  Markdown with `[claim:clm_NNN]` tags converted to clickable chips. `Inference:`
  and `Speculation:` sentences are color-coded. A composition sidebar shows
  percentage breakdown of supported/inference/speculation with click-to-filter.

### Architecture

- **ADR `adr-runs-read-path`** — records static `rf run export --json` as the
  primary (and sole v1) read path; documents the four load-bearing invariants
  (R9 sensitivity gate, read-only SPA, path-safety, no LLM on recall path); and
  describes the deferred loopback API path behind `RUNS_FRONTEND_LOOPBACK_API`.
- **Export schema v1.0** frozen at
  `docs/dev/architecture/rf-run-export-schema.md`; `backend-architect` review
  approved.

---
