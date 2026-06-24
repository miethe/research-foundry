---
schema_version: 2
doc_type: exploration_charter
title: "Credential / Key-Profile Process Isolation — Exploration Charter"
status: draft
created: 2026-06-23
feature_slug: credential-process-isolation
timebox_days: 4
hypothesis: "We believe per-profile credential isolation at the adapter/spawn boundary (plus key fingerprinting in telemetry and HITL gating on cross-profile elevation) is worth building because RF's key-profile framework today is name-only — it labels and policy-gates a profile but never physically separates the credential material that personal vs work_approved runs touch, leaving cross-profile key leakage between in-process adapters undetectable."
deal_killer: "If RF's adapters remain in-process by design and no realistic threat model justifies the cost/complexity of subprocess credential isolation, abandon process-level isolation in favor of in-process profile scoping + key fingerprinting only."
investigation_legs:
  - id: threat-model
    question: "What concrete attack does process isolation prevent here (cross-profile key leakage between adapters within one run), and is that risk real given RF's current single-process, single-operator, file-backed design?"
    assigned_to: spike-writer
  - id: spawn-boundary
    question: "Where would isolation live — per-adapter subprocess, swarm-orchestrator-spawns-workers, or CLI-level worker spawn — and what is the cost of moving adapters out-of-process, including how credentials reach the subprocess (env vars vs temp credential files + secure cleanup)?"
    assigned_to: backend-architect
  - id: fingerprint-telemetry
    question: "How should key fingerprinting be designed (hash of key prefix / salted digest) and where should the fingerprint land (CCDash telemetry event vs run trace), without re-introducing a secret-leak vector through the fingerprint itself?"
    assigned_to: backend-architect
  - id: elevation-hitl
    question: "How is cross-profile elevation detected and gated by a human-in-the-loop approval — one-time per run vs per-subprocess — and how does that compose with the existing deterministic governance pass?"
    assigned_to: spike-writer
verdict_criteria:
  go:
    - "threat-model leg establishes a realistic cross-profile leakage path with confidence >= 0.7 AND spawn-boundary leg identifies a bounded-cost spawn model"
    - "Deal-killer condition not triggered"
    - "fingerprint-telemetry and elevation-hitl legs each report an implementable design at confidence >= 0.7"
    - "Explicit human sign-off obtained (Mode D — credential/security infrastructure)"
  no_go:
    - "Deal-killer condition triggered (in-process design is intentional and no realistic threat justifies subprocess cost)"
    - "spawn-boundary leg reports moving adapters out-of-process is infeasible or prohibitively costly with confidence >= 0.8"
  conditional:
    - "Fingerprinting + in-process profile scoping is clearly worthwhile but the subprocess-isolation question remains open, resolvable by a specific named follow-up SPIKE (e.g. a spawn-boundary prototype leg)"
verdict: null
verdict_rationale: null
output_artifacts: []
---

# Credential / Key-Profile Process Isolation — Exploration Charter

<!-- Copy to docs/project_plans/exploration/[feature-slug]/[feature-slug]-charter.md -->
<!-- Use /plan:explore to scaffold most fields from an idea description. -->

## Hypothesis Context

This exploration derives from completed Research Foundry run **RIB-018** (IntentTree node `node_01KVQYN3RQGZTYRKC8J2YRJJH3`, high evidence), harvested in `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` (per-run map row 018). The research recommends **one-profile-per-process credential isolation at every spawn boundary, key fingerprinting in telemetry, and HITL on cross-profile elevation** as the way to harden RF's key governance.

RF already has a **name-level** key-profile framework: `key_profile` (`personal` / `work_approved`) is derived from idea sensitivity in `src/research_foundry/services/capture.py` (`_governance_from_sensitivity`, ~lines 223–230, writing `governance.key_profile_allowed` into the intent); the deterministic governance pass enforces `no_work_keys_for_personal_runs` in `src/research_foundry/services/governance.py` (~lines 209–222); and `key_profile_used` is recorded in CCDash telemetry via `_KEY_PROFILE_BY_SENSITIVITY` in `src/research_foundry/services/telemetry.py` (~lines 23, 148, 206).

The counterfactual that makes this a **SPIKE, not a contract**: the central recommendation presupposes a *spawn model RF does not have*. The adapters (`gpt_researcher.py`, `paperqa2.py`, `claude_agent_sdk.py`, `opencode.py`, `litellm_router.py`, `arc_council.py`, `notebooklm.py` in `src/research_foundry/adapters/`) are invoked as **in-process imports** — `src/research_foundry/adapters/base.py` gates real mode purely on `importlib.util.find_spec` (~lines 22–31, 77), with no `subprocess`/`Popen` anywhere in the adapter layer. So "one-profile-per-process at every spawn boundary" collides with RF's current in-process architecture. Three things are missing and design-blocking: (1) **no per-process credential isolation** — adapters share the process and its environment; (2) **no key fingerprinting** — only the profile *name* is logged, never a hash of the key material; (3) **no HITL approval on cross-profile elevation**. Because this is credential/security infrastructure, the work runs under **Mode D — High-Risk Change**: this charter scopes the investigation only and any GO requires explicit human sign-off.

---

## Investigation Legs

<!-- One subsection per leg. Each leg runs as a SPIKE via /plan:spike --leg-of=[charter-path]. -->
<!-- Add/remove subsections to match investigation_legs entries. -->

### Leg: threat-model — Realistic Threat Model for Cross-Profile Key Leakage

**Question**: What concrete attack does process isolation prevent here (cross-profile key leakage between adapters within one run), and is that risk real given RF's current single-process, single-operator, file-backed design?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/credential-process-isolation/spikes/threat-model-spike.md`

Specific unknowns this leg must address:
- Enumerate the leakage paths that **process isolation specifically closes** but in-process profile scoping does not: a `work_approved` key resident in `os.environ` while a `personal`-profile adapter executes; a third-party adapter (`gpt_researcher`, `paperqa2`) reading the ambient environment or a shared `litellm` config; an adapter crash dumping environment into a trace/log.
- Characterize the **trust boundary**: RF is single-operator, file-backed, LAN-local (per CLAUDE.md / Agentic Node). Is the adversary an honest-but-curious third-party adapter package, a compromised dependency, or operator error? Process isolation buys most against the first two; in-process scoping may suffice against the third.
- State what `no_work_keys_for_personal_runs` (`governance.py` ~209–222) already prevents (a `work_approved` *profile* on a `personal` *intent*) versus what it cannot prevent (key *material* of the wrong profile being readable from the environment regardless of the declared profile).
- Decide the deal-killer: is there a realistic threat that only subprocess isolation defeats, or does the residual risk justify only in-process scoping + fingerprinting? Report confidence on the leakage-path realism.

### Leg: spawn-boundary — Where Isolation Lives & Cost of Out-of-Process Adapters

**Question**: Where would isolation live — per-adapter subprocess, swarm-orchestrator-spawns-workers, or CLI-level worker spawn — and what is the cost of moving adapters out-of-process, including how credentials reach the subprocess (env vars vs temp credential files + secure cleanup)?
**Assigned to**: `backend-architect`
**Expected output**: `docs/project_plans/exploration/credential-process-isolation/spikes/spawn-boundary-spike.md`

Specific unknowns this leg must address:
- Map the three candidate boundaries against RF's actual call graph: **(a) per-adapter subprocess** (each `adapters/*` call forks a worker with only its profile's credentials), **(b) swarm-orchestrator-spawns-workers** (the run orchestrator spawns one worker process per profile and routes adapter calls to it), **(c) CLI-level worker spawn** (`rf` spawns a profile-scoped worker for the whole run). Note that RF's swarm runs are Claude-Code-authored source cards + a deterministic `rf` tail (see memory: rf-run-execution-path-b), so the "spawn boundary" may not be where adapters live today.
- Cost of moving adapters out-of-process: serialization of adapter inputs/outputs across the process boundary, loss of the current `importlib.util.find_spec` real-mode gate (`base.py`), startup latency per spawn, and the testing burden (current tests import adapters directly).
- **Credential delivery to subprocess**: env vars (simple, but inherited-environment leakage is the very risk being closed) vs temporary credential files (explicit, scoped, but need secure creation perms `0600` and guaranteed cleanup on crash) vs an fd/pipe handoff. Recommend one, with the secure-cleanup contract.
- Confidence on feasibility and a rough effort band for the cheapest viable boundary. If infeasible/prohibitive at confidence >= 0.8, that triggers no_go.

### Leg: fingerprint-telemetry — Key-Fingerprinting Design & Landing Site

**Question**: How should key fingerprinting be designed (hash of key prefix / salted digest) and where should the fingerprint land (CCDash telemetry event vs run trace), without re-introducing a secret-leak vector through the fingerprint itself?
**Assigned to**: `backend-architect`
**Expected output**: `docs/project_plans/exploration/credential-process-isolation/spikes/fingerprint-telemetry-spike.md`

Specific unknowns this leg must address:
- Fingerprint construction: salted hash of the full key vs hash of a key prefix vs truncated digest. Goal is *which key was used* (collision-resistant within RF's small key set) while being non-reversible and non-bruteforceable — evaluate the privacy/safety tradeoff of each (a short prefix hash of a low-entropy key can be brute-forced).
- Landing site: extend the existing telemetry record in `src/research_foundry/services/telemetry.py` (which already carries `key_profile_used` ~line 206) with a `key_fingerprint` field → CCDash event, vs writing it into the run trace only. Note CCDash telemetry may be exported (see memory: export-time redaction) — confirm the fingerprint survives redaction safely.
- Compatibility with the secret-scanning governance layer (`config/governance.yaml` secret_patterns, loaded in `governance.py`): ensure a fingerprint is never itself matched/flagged as a secret, and never logs raw key material.
- Report an implementable design at confidence >= 0.7, or flag the residual privacy risk.

### Leg: elevation-hitl — Cross-Profile Elevation Detection & HITL Gate

**Question**: How is cross-profile elevation detected and gated by a human-in-the-loop approval — one-time per run vs per-subprocess — and how does that compose with the existing deterministic governance pass?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/credential-process-isolation/spikes/elevation-hitl-spike.md`

Specific unknowns this leg must address:
- Define "cross-profile elevation": a run declared `personal` that needs a `work_approved` key mid-flight, or a worker requesting a profile above the run's `governance.key_profile_allowed`. Today `no_work_keys_for_personal_runs` simply **blocks** this (`governance.py` ~209–222); elevation would instead *pause for approval*.
- HITL granularity: one approval per run (coarse, fewer prompts, broader blast radius) vs per-subprocess/per-elevation (fine, auditable, more friction). Recommend a default given RF's single-operator workflow and the existing approval surfaces (`op approve/reject`, IntentTree `request_*` / `run_approve`).
- Where the gate sits relative to the deterministic-first governance pass (`rf_governance_officer` runs policy *before* privileged actions): the HITL gate must be a deterministic *block-pending-approval*, not a model decision, with an append-only audit entry (mirror the RIB-017 writeback-gate audit pattern — `node_01KVQYMYPN51B5TRGPR65NNPW3`).
- Report an implementable flow at confidence >= 0.7.

---

## Verdict Criteria Narrative

<!-- Make each gate concrete so any agent can apply it consistently. -->

**Go** if: the threat-model leg establishes at least one realistic cross-profile leakage path (confidence >= 0.7) that subprocess isolation closes and in-process scoping does not, the spawn-boundary leg identifies a bounded-cost spawn model and credential-delivery mechanism, and both the fingerprint-telemetry and elevation-hitl legs land implementable designs (confidence >= 0.7 each). **Because this is credential/security infrastructure (Mode D), any GO additionally requires explicit human sign-off before implementation is planned or started** — the verdict alone does not authorize code.

**No-go** if: the deal-killer fires — the in-process adapter design is intentional and no realistic threat justifies the cost/complexity of subprocess isolation — in which case abandon process-level isolation and pursue only in-process profile scoping + key fingerprinting. Also no-go if the spawn-boundary leg reports that moving adapters out-of-process is infeasible or prohibitively costly at confidence >= 0.8.

**Conditional** if: fingerprinting + in-process profile scoping is clearly worth building but the subprocess-isolation question is unresolved — name the specific follow-up (e.g. a spawn-boundary prototype SPIKE measuring per-spawn latency/serialization cost) as the gating next step, and ship the fingerprinting + scoping slice meanwhile.

---

## Out of Scope

- Implementing any isolation, fingerprinting, or HITL code — this is a design SPIKE only (Mode D; no code, no spike execution from this charter).
- The RIB-017 writeback-boundary default-deny gate (`node_01KVQYMYPN51B5TRGPR65NNPW3`) — the security *pair* to this work, but a separate charter/contract. Referenced here only for the shared append-only-audit pattern.
- Adding new key profiles or changing the `personal` / `work_approved` taxonomy or its sensitivity-derivation rules in `capture.py`.
- Multi-operator / multi-tenant credential models — RF is single-operator, LAN-local; revisit only if that assumption changes.
- Secret-scanning pattern changes beyond confirming the fingerprint is not flagged.

---

## Citations / Prior Art

<!-- Back-links to past explorations, SPIKEs, ADRs, or external references consulted before starting. -->
- Harvest report: `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` (RIB-018 row; IntentTree node `node_01KVQYN3RQGZTYRKC8J2YRJJH3`, high evidence).
- `src/research_foundry/services/capture.py` — `_governance_from_sensitivity` (~223–230); sensitivity→`key_profile_allowed` derivation.
- `src/research_foundry/services/governance.py` — `no_work_keys_for_personal_runs` policy rule (~209–222); deterministic governance pass.
- `src/research_foundry/services/telemetry.py` — `_KEY_PROFILE_BY_SENSITIVITY` and `key_profile_used` recording (~23, 148, 206).
- `src/research_foundry/adapters/base.py` — in-process real-mode gate via `importlib.util.find_spec` (~22–31, 77); confirms no current spawn boundary.
- `src/research_foundry/adapters/` — `gpt_researcher.py`, `paperqa2.py`, `claude_agent_sdk.py`, `opencode.py`, `litellm_router.py`, `arc_council.py`, `notebooklm.py` (in-process adapters).
- Related security pair: RIB-017 writeback-boundary gate (`node_01KVQYMYPN51B5TRGPR65NNPW3`) — shares the justified-override + append-only audit pattern.
- `.claude/rules/delegation-modes.md` — Mode D (High-Risk Change: credentials/security) boundary governing this charter.

---

## Notes

<!-- Append timestamped entries as legs complete. Format: YYYY-MM-DD: [note]. -->
- 2026-06-23: Charter authored from harvested RIB-018 outcome. Mode D — design SPIKE only; no code, no spike execution; verdict left null. Grounding facts verified against `capture.py`, `governance.py`, `telemetry.py`, and `adapters/base.py` (adapters confirmed in-process; no subprocess/Popen in adapter layer).
