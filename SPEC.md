---
schema_version: 0.1
doc_type: project_spec
project: Research Foundry
status: mvp
created: 2026-06-13
updated: 2026-06-13
owner: Nick Miethe
authoritative_spec: docs/projects/research-foundry/research-foundry-mvp-spec.md
implementation_plan: docs/projects/research-foundry/IMPLEMENTATION_PLAN.md
service_contract: docs/projects/research-foundry/SERVICE_CONTRACT.md
---

# Research Foundry — Specification (summary)

> **Authoritative spec:** [`docs/projects/research-foundry/research-foundry-mvp-spec.md`](docs/projects/research-foundry/research-foundry-mvp-spec.md)
> **Implementation plan:** [`docs/projects/research-foundry/IMPLEMENTATION_PLAN.md`](docs/projects/research-foundry/IMPLEMENTATION_PLAN.md)
> **Service contract:** [`docs/projects/research-foundry/SERVICE_CONTRACT.md`](docs/projects/research-foundry/SERVICE_CONTRACT.md)

## What it is

Research Foundry is a **Markdown/YAML-first research control plane** that turns raw
ideas into governed research swarms, evidence bundles, claim-verified reports, and
writebacks to MeatyWiki, SkillMeat, and CCDash. It is a thin, file-backed system —
a Python `rf` CLI (`research_foundry` package) — not a monolithic research app.

## The differentiated value: claim traceability

A research report may contain only:

- **supported** claims mapped to source cards,
- labeled **inference**,
- labeled **speculation**, or
- explicitly **unresolved** questions.

`rf verify` enforces this deterministically (spec §12.3). Any untagged material
claim fails the build (exit code 4). The claim ledger — not any agent or external
tool — is the authority.

## Design principles (spec §2)

1. Markdown/YAML is the source of truth.
2. Research begins with intent, not prompts.
3. Every material claim is auditable.
4. Cheap/free models extract; expensive models synthesize.
5. The swarm is disposable; the evidence bundle is durable.
6. Governance is a runtime gate, not a memo.
7. CCDash proves which research workflows actually worked.

## The loop (spec §11)

```
capture → triage (intent + I-BOM + IntentTree node) → plan (brief + swarm + routing)
→ ingest (source cards) → extract → claim-map (claim ledger) → synthesize (report)
→ verify (claim traceability) → bundle (evidence bundle) → writeback (MeatyWiki +
SkillBOM + CCDash) → guard (governance)
```

The MVP runs this loop **fully offline/deterministically** (no API keys). External
research tools (GPT Researcher, PaperQA2, Claude Agent SDK, LiteLLM) are opt-in
adapters that normalize into the same YAML substrate; they never become the authority.

## Status

MVP implemented and tested (102+ tests, full `rf` loop green). See the
[README](README.md) for install + quickstart, and `examples/run_demo.sh` for an
end-to-end demonstration of the spec §19 topic.
