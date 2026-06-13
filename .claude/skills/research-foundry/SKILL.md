---
name: research-foundry
description: Drives the Research Foundry control plane — a Markdown/YAML-first research pipeline that captures an idea, routes it through source discovery, claim mapping, synthesis, and deterministic verification, then publishes an evidence bundle. Use when the operator wants to run, plan, or audit an end-to-end research run with the `rf` CLI, or wants claim-traceable, governance-gated research instead of a freehand answer.
---

# Research Foundry

Research Foundry is a Markdown/YAML-first research control plane. Every step is human-readable, deterministic, and diff-friendly. The discipline that makes it trustworthy: **no material claim ships unless it maps to a claim-ledger entry backed by a source card, or is explicitly labeled inference/speculation.**

Operate through the `rf` CLI. Each pipeline step has a subagent posture and a deterministic exit code; you orchestrate, the CLI and validators enforce.

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
| Capture a raw idea | 1 | `rf capture "<idea>" --from … --sensitivity … --tag …` | rf_intake_curator |
| Triage into intent + I-BOM + tree node | 2–4 | `rf triage <raw_idea.md> --create-intent --create-ibom --create-tree-node` | rf_intake_curator |
| Plan the swarm (brief + routing) | 5–7 | `rf plan <intent_id> --depth … --audience … --max-cost … --freshness …` | (router) |
| Governance preflight | 8 | `rf guard check --profile <profile>` | rf_governance_officer |
| Ingest a source manually | 9–10 | `rf ingest <path|url> --source-type … --sensitivity … --run <run>` | rf_source_carder |
| Discover sources | 9 | `rf swarm run <run> --profile …` | rf_source_scout |
| Create source cards | 10 | (via `rf swarm run` / `rf ingest`) | rf_source_carder |
| Extract evidence | 11 | `rf extract <run> --source-cards … --model-profile rf_extract_cheap` | (extractor) |
| Build claim ledger | 12 | `rf claim-map <run> --from extractions --out claims/claim_ledger.yaml` | (claim mapper) |
| Detect contradictions/gaps | 13 | (via `rf swarm run`) | (contradiction hunter) |
| Synthesize report | 14 | `rf synthesize <run> --report reports/report_draft.md --model-profile rf_synthesize_deep` | rf_synthesizer |
| Verify every material claim | 15 | `rf verify <run> --report … --claim-ledger … --fail-on-unsupported` | rf_claim_auditor |
| Council / human review | 16 | `rf council <run> --roles … --vote approve-concern-block` | (council) |
| Publish evidence bundle | 17 | `rf bundle <run> --verify --out evidence_bundle.yaml` | — |
| Write back (wiki/skill/ccdash) | 18–20 | `rf writeback <run> --targets meatywiki,skillmeat,ccdash --require-review` | rf_governance_officer |
| Propose / promote SkillBOM | 19 | `rf skillbom propose <run>` / `rf skillbom promote <cand> --reviewer …` | — |
| Status / health / cost / redact / index | — | `rf status` · `rf doctor` · `rf cost <run>` · `rf redact <run> --target public` · `rf index rebuild` · `rf ccdash summarize --period daily` | — |

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
