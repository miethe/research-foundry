---
schema_version: 2
doc_type: design-spec
title: "External Research Provider Automation (ERI-DF-1)"
status: draft
maturity: shaping
created: 2026-07-27
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
related_documents:
  - docs/dev/architecture/external-research-handoff-contract.md
  - docs/user/external-research-interchange.md
deferred_from: "ERI Phase 3 (Producer Prompt/Output Profiles) — deferred item ERI-DF-1 in the ERI implementation plan's Deferred Items table"
---

# External Research Provider Automation (ERI-DF-1)

## What is deferred

ERI v1 ships five **manual, offline, prompt-driven** producer profiles (generic, ChatGPT, Perplexity,
Gemini, NotebookLM). Every one is a copy/paste-and-map workflow: an operator runs the named tool by
hand, then hand-assembles the output into a packet directory. None assumes a vendor API key, SDK,
live endpoint, or browser automation.

This spec names, but does not scope, the alternative: **automated production** of a packet directly
from a live vendor session or API — e.g. a script that drives a ChatGPT Deep Research session via an
authenticated API key, waits for completion, and emits a packet automatically.

## Why it was deferred (from the implementation plan)

> Live provider automation adds secrets, cost, SDK drift, and vendor terms.

Concretely, from ERI's own contract hardening work (`external-research-handoff-contract.md` §3.2,
§4.2.1): the contract's hard SSRF-safe acquisition gate depends on **one actor owning the entire
HTTP lifecycle** end to end (canonicalization → DNS → connect → peer verification → redirect
re-validation → body read, as a single integrated operation). A vendor SDK or API client that
performs its own HTTP calls under the hood is exactly the "provider-delegated fetch" case the
contract's `transport_architecture.provider_delegated_fetch_allowed: false` hard-pins closed — the
gate cannot validate a connection it does not open and control itself. Building live provider
automation safely would mean either (a) accepting a hole in the SSRF guarantee for that specific
integration, or (b) proving an equivalent end-to-end pinned-address guarantee for that vendor's own
transport — which no vendor has been evaluated against.

Beyond the acquisition-gate concern: a live integration would require storing and rotating
per-vendor API credentials (a new secret-management surface), track a cost model per vendor call,
follow each vendor's own terms of service for automated/programmatic access (several explicitly
restrict this for consumer-tier accounts), and would drift whenever the vendor's API or UI changes —
none of which the manual, human-in-the-loop profiles have to contend with.

## Trigger for promotion

Per the plan's Deferred Items table: "Approved provider contract, live canary, rollback, secret
owner." Concretely, before this is promotable:

1. A specific vendor and its official, documented API (not scraping/browser automation) is named.
2. That vendor's API is proven — for that specific integration — to close the "provider-delegated
   fetch" gap: either the vendor API returns raw bytes with a verifiable content-address (so RF's own
   SSRF gate still performs the actual acquisition), or the vendor's own transport is independently
   proven equivalent to the contract's pinned-address guarantee.
3. A named secret owner and rotation policy exists for that vendor's credentials, wired through RF's
   existing credential-isolation model (the same posture as `services/telemetry.py`'s agent-job
   pepper/API-key handling, not a new ad hoc secret store).
4. A live canary run and a rollback plan exist (this is Mode-D-adjacent — credential/cost/vendor-ToS
   exposure — and should go through the same gate discipline as other Mode-D changes in this
   codebase, e.g. `docs/project_plans/design-specs/oidc-adapter-live-implementation.md`'s structure).
5. A per-vendor cost model and budget cap is defined before the first live call.

## What this spec does NOT do

It does not select a vendor, does not design an API client, and does not propose a credential-storage
mechanism. Promotion to a PRD/implementation plan should re-derive those from whichever vendor is
actually chosen at that time — vendor APIs in this space (agentic research assistants) are new and
still evolving; committing to one now would likely be stale before it shipped.
