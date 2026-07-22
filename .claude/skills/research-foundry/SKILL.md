---
name: research-foundry
description: Drives the Research Foundry control plane — a Markdown/YAML-first research pipeline that captures an idea, routes it through source discovery, claim mapping, synthesis, and deterministic verification, then publishes an evidence bundle. Use when the operator wants to run, plan, or audit an end-to-end research run with the `rf` CLI, or wants claim-traceable, governance-gated research instead of a freehand answer.
---

# Research Foundry

Research Foundry is a Markdown/YAML-first research control plane. Every step is human-readable, deterministic, and diff-friendly. The discipline that makes it trustworthy: **no material claim ships unless it maps to a claim-ledger entry backed by a source card, or is explicitly labeled inference/speculation.**

Operate through the `rf` CLI. Each pipeline step has a subagent posture and a deterministic exit code; you orchestrate, the CLI and validators enforce.

## Shared node instance (prefer for shared reads + launch)

A persistent RF instance runs on the agentic node (`rocket-fedora`, `10.42.10.76`) — **prefer it over a local file workspace** for shared reads and for launching runs, so every agent sees one corpus.

- **API:** `http://10.42.10.76:7432` — base path `/api`, health at `/health`.
- **Auth:** `Authorization: Bearer $RF_TOKEN_AGENT` (owner token). Source it from `~/.config/research-foundry/serve.env` (mirrored on the laptop): `set -a; . ~/.config/research-foundry/serve.env; set +a`.
- **Read:** `GET /api/runs`, `/api/runs/{run_id}`, `/api/runs/{run_id}/claims`, `/api/reports`, `/api/catalog`, `/api/audit`.
- **Launch over HTTP:** `POST /api/runs` — body has exactly one of `text` | `intent_id`, plus optional `sensitivity`/`depth`/`audience`/`tags`/`project`; owner/admin token required; returns `201` + `run_id`. It **scaffolds + registers** the run (capture→triage→plan) — it does NOT drive the discovery swarm; continue the loop via the on-node `rf` CLI or agent-jobs.
- **Viewer:** runs-viewer UI at `http://10.42.10.76:3030` (live — reflects the API, not static fixtures).
- **Visibility:** the node serves fully open (`--sensitivity-threshold client_sensitive`) — nothing is redacted (single-user trusted LAN).
- **Local CLI scope:** the local `rf` CLI operates on the **local file workspace only** (no remote-target seam). Use the HTTP API above to read/launch against the shared node; use the local CLI for local-only runs or when SSH'd onto the node.

## Execution loop (§11)

Run the loop in order; do not skip the governance preflight or the verification step.

1. Capture raw idea.
2. Convert idea into research intent.
3. Build or update research I-BOM.
4. Create IntentTree research node.
5. Generate routing decision.
6. Generate research brief.
7. Plan swarm.
8. Run governance preflight.
9. Discover sources.
10. Create source cards.
11. Extract evidence.
12. Build claim ledger.
13. Detect contradictions and gaps.
14. Synthesize report.
15. Verify every material claim.
16. Run council/human review if needed.
17. Publish evidence bundle.
18. Write back to MeatyWiki.
19. Generate SkillBOM candidate.
20. Emit CCDash telemetry.
21. Route next research move.

## Intent → command route table (§10)

Match the operator's intent to the loop step, then the `rf` command.

| Operator intent | Loop step | `rf` command | Subagent |
| --- | --- | --- | --- |
| Set up a new foundry | 0 | `rf init <dir> --profile … --with-claude` | — |
| Capture a raw idea | 1 | `rf capture "<idea>" --from … --sensitivity … --tag … --backlog-idea-ref RIB-NNN` | rf_intake_curator |
| Triage into intent + I-BOM + tree node | 2–4 | `rf triage <raw_idea.md> --create-intent --create-ibom --create-tree-node` | rf_intake_curator |
| Plan the swarm (brief + routing) | 5–7 | `rf plan <intent_id> --depth … --audience … --max-cost … --freshness …` | (router) |
| Governance preflight | 8 | `rf guard check --profile <profile>` | rf_governance_officer |
| Search for sources (Search Router) | 9 | `rf search "<query>" --mode source_discovery --max-results N --max-cost X --intent-id ID --task-node-id ID --no-cards` | rf_source_scout |
| Fetch known URLs into source cards | 9–10 | `rf fetch <urls…>` | rf_source_carder |
| Ingest a source manually | 9–10 | `rf ingest <path|url> --source-type … --sensitivity … --run <run>` | rf_source_carder |
| Discover sources (adapter swarm) | 9 | `rf swarm run <run> --profile …` | rf_source_scout |
| Create source cards | 10 | (via `rf search` / `rf fetch` / `rf swarm run` / `rf ingest`) | rf_source_carder |
| Extract claims from source cards | 11 | `rf extract <run> --model-profile rf_extract_cheap` | (extractor) |
| Build claim ledger | 12 | `rf claim-map <run> --from extractions --out claims/claim_ledger.yaml` | (claim mapper) |
| Detect contradictions/gaps | 13 | (via `rf swarm run`) | (contradiction hunter) |
| Synthesize report | 14 | `rf synthesize <run> --report reports/report_draft.md --model-profile rf_synthesize_deep` | rf_synthesizer |
| Verify every material claim | 15 | `rf verify <run> --report … --claim-ledger … --fail-on-unsupported` | rf_claim_auditor |
| Council / human review | 16 | `rf council <run> --roles … --vote approve-concern-block` | (council) |
| Publish evidence bundle | 17 | `rf bundle <run> --verify --out evidence_bundle.yaml` | — |
| Write back (wiki/skill/ccdash/…) | 18–20 | `rf writeback <run> --targets meatywiki,skillmeat,ccdash,intenttree,arc,notebooklm --require-review` | rf_governance_officer |
| Propose / promote SkillBOM | 19 | `rf skillbom propose <run>` / `rf skillbom promote <cand> --reviewer …` | — |
| Export run data (viewer contract) | — | `rf run export --run-id <run> --all --stdout --sensitivity-threshold …` | — |
| List runs | — | `rf run list` | — |
| Serve loopback API (runs viewer) | — | `rf serve --port 7432 --bind-host 127.0.0.1 --auth-mode none\|token --sensitivity-threshold N --mode single_user\|multi_user` | — |
| Reconcile backlog ↔ runs | — | `rf backlog reconcile [--dry-run\|--write]` | — |
| Status / health / cost / redact / index | — | `rf status` · `rf doctor` · `rf cost <run>` · `rf redact <run> --target public` · `rf index rebuild` · `rf ccdash summarize --period daily` | — |
| Import / search / rebuild the catalog | — | `rf catalog import <path>` · `rf catalog search <query>` · `rf catalog show <id>` · `rf catalog stats` · `rf catalog rebuild` | — |
| Migrate a workspace to row-level isolation (WKSP-304) | — | `rf workspace migrate-dry-run` · `rf workspace migrate` · `rf workspace rollback` | — |
| Author / verify a report Builder draft | — | `rf report anchors` · `rf report draft create\|list\|show\|add-block\|update-block\|delete-block\|reorder\|verify\|publish-preview\|export` · `rf report draft claim-link add\|remove` | — |
| Launch / stream / accept a web-driven agent job | — | `rf agent-job launch` · `rf agent-job list` · `rf agent-job stream <id>` · `rf agent-job accept <id>` · `rf agent-job status <id>` | — |
| Audit log — list / show / health | — | `rf audit list` · `rf audit show <id>` · `rf audit health` | — |

### Command notes

- **`rf search`** produces source_cards directly (unless `--no-cards`). Requires the `[search]` extra (httpx). Keyless providers (jina, github) degrade gracefully when offline; keyed providers (brave, exa, firecrawl) require configured API keys.
- **`rf fetch`** (URL extraction) extracts Markdown from one or more known URLs into source cards. Distinct from `rf extract` (claim extraction from existing source cards).
- **`rf extract`** is **claim extraction**: it processes a run's source cards into extraction/claim cards (spec §10.7). It is NOT URL fetching.
- **`rf writeback --targets meatywiki`** auto-emits an additional `decision_record` writeback (rendered from inference/recommendation claims) when inference claims exist in the claim ledger. The decision_record is NOT a separate `--targets` value — it is emitted automatically alongside the `meatywiki` source-note writeback.
- **`rf serve`** requires the `[serve]` extra (fastapi, uvicorn). Non-loopback bind (e.g. `--bind-host 0.0.0.0`) FAILS CLOSED unless `--auth-mode token` AND env `RF_SERVE_TOKEN` is non-empty. Includes an IP allowlist middleware. All routes serve through export_service (read-only).
- **`rf serve --mode single_user|multi_user`** (public-multiuser-release-activation, currency note 2026-07-22) overrides `foundry.yaml`'s `deployment_mode` for that invocation. `single_user` (default) is a no-op — behaviorally identical to no `--mode` flag at all. `multi_user` composes preset defaults over RBAC/workspace-isolation/rate-limit and additionally fails closed at startup unless a real auth provider is configured AND the DI-1 full-surface audit gate is satisfied (`auth.di1_audit_acknowledged: true` + the audit artifact's `status: accepted`) — see `docs/dev/architecture/auth-rbac-operator-guide.md` § Deployment Modes and `SERVICE_CONTRACT.md` §21/§22 for the full contract, including service-account/PAT admin endpoints under `/api/admin`.
- **`rf run export`** produces export schema v1.2 with fields: `cost_usd`, `model_profiles`, `source_count_by_type`, `writebacks` summary, `linked_projects`, `category`, `tags`.
- **`rf backlog reconcile`** defaults to `--dry-run`; pass `--write` to apply. Reconciles `run.yaml` `backlog_idea_ref` against the idea backlog, advancing status and filling links.
- **`rf capture --backlog-idea-ref RIB-NNN`** links the captured idea to an entry in `backlog/research_idea_backlog.yaml`. The ref is validated before the idea is written. Run metadata `linked_projects`, `category`, and `tags` are populated on every run.
- **`rf catalog` / `rf workspace` / `rf report draft` / `rf agent-job` / `rf audit`** are the web-platform surfaces added post-MVP (public multi-user release, `src/research_foundry/api/`, `src/research_foundry/cli/commands/agent_job.py`): catalog indexing, workspace row-level-isolation migration (WKSP-304), the report Builder/drafts workflow, web-driven agent-job launch (distinct from the CLI-orchestrated `rf swarm run`/discovery-agent paths in steps 7–9), and the append-only audit log. They sit alongside, not inside, the 21-step research loop — most are also reachable over HTTP via `rf serve`.

## Claim-traceability discipline

This is the core invariant. Enforce it at synthesis (§10.9) and verification (§10.10):

- The synthesizer may **only cite claim IDs already present in `claim_ledger.yaml`**, or label a sentence as `inference`/`speculation`. It never mints a new claim ID.
- Every unlabeled **causal, comparative, attribution, or quantitative** statement is a material claim and must trace to a ledger entry backed by a source card.
- The claim auditor adds no claims and silently repairs nothing; it emits `verification.yaml` and marks the report failed if any material claim is unsupported.

## Governance rules

- Run the **governance preflight before any source discovery or privileged action** (step 8). Deterministic checks run first.
- Block invalid **key / data-sensitivity / writeback-target** combinations: a key or model must not touch data above its tier, and a writeback target must not receive data above its permitted tier. Fail closed when a rule is ambiguous.
- Hooks run deterministic validators on every Bash/Write/Edit (`guard_pretool`), every Write/Edit artifact (`scan_artifact`), and on Stop (`emit_ccdash_event`). Treat a hook block as authoritative.

## Verify exit codes (§10.10)

| Code | Meaning |
| --- | --- |
| 0 | Pass |
| 2 | Schema validation failed |
| 3 | Governance policy blocked |
| 4 | Unsupported material claim |
| 5 | Budget exceeded |
| 6 | Adapter/tool failure |
| 7 | Human review required |

Treat any non-zero exit as a stop: fix the cause (label the inference, add the missing source card, redact to the right tier) and re-run, rather than overriding.
