---
name: council-review
description: >
  Run an Agent Review Council over a product, workflow, codebase, architecture,
  prompt, agent package, or GTM artifact. Produces evidence-backed structured findings,
  scorecard, risks, decision record, and validation plan.
allowed-tools: Read, Grep, Glob, Bash
---

# Council Review Skill

Use this skill for full ARC runs that need coordinated evidence collection, independent reviewer passes, adjudication, and schema-valid outputs.

## Research Foundry binding

This skill backs the **`rf council`** gate — step 16 of the 21-step Research Foundry run loop.

| Detail | Value |
|--------|-------|
| RF CLI command | `rf council <run_id> --roles <role,...> --vote approve\|concern\|block` |
| Exit code 7 | Human review required — pipeline pauses and waits for explicit approval |
| Vendored agents | `.Codex/agents/council/` — `council-coordinator.md` + `*-reviewer.md` |
| Input artifacts | `runs/<run_id>/reports/`, `runs/<run_id>/claims/claim_ledger.yaml` |
| Output | Council run tree written under `runs/<run_id>/council/` |
| Offline | Fully file-based and offline-safe — no arc server required |

When invoked from RF, skip the `uv run arc validate` step (RF's own governance pipeline validates run artifacts). Read `runs/<run_id>/claims/claim_ledger.yaml` as the primary evidence source; treat every unverified claim as a finding candidate.

**Related skills:** [`research-foundry`](./../research-foundry/SKILL.md) · [`research-foundry-swarm`](./../research-foundry-swarm/SKILL.md)

## Workflow

1. Confirm target, objective, council definition, constraints, and required outputs.
2. Read `references/run-workflow.md` for the end-to-end council procedure.
3. Read `references/output-contract.md` before creating or validating run artifacts.
4. Read `references/external-reviewers.md` only when the run includes Codex, GitHub, Copilot, LangGraph, or other non-Codex reviewers.
5. Write artifacts under `runs/<date>-<slug>/`.
6. Validate with `uv run arc validate runs/<date>-<slug>`.

## Ground Rules

- Findings without evidence are hypotheses.
- High-severity findings require strong evidence or explicit uncertainty.
- Run independent reviewer passes before synthesis.
- Preserve accepted, rejected, disputed, and watchlist findings.
- Do not create tickets or durable memory without approval.
- Keep final output concise, but preserve the structured artifacts.
