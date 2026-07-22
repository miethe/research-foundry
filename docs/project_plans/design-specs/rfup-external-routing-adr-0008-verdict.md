---
title: "Design Spec: ADR-0008 Verdict — `litellm_router` Native-Adapter Eval (rf-side)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: shaping
created: 2026-07-22
updated: 2026-07-22
feature_slug: rfup-external-routing
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
owner: nick
tags: [adapters, litellm, adr-0008, verdict, seam-boundary, rfup-external-routing]
category: design-decision
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1/phase-5-adapter-eval.md
  - docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md
  - .claude/worknotes/rfup-external-routing/litellm-router-eval.md
related_prds:
  - docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
adr_refs:
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/adr/0008-pathb-hardening-vs-native-adapter.md
---

# Design Spec: ADR-0008 Verdict — `litellm_router` Native-Adapter Eval (rf-side)

> **Maturity: shaping.** This document promotes the Phase 5 working evaluation record
> (`.claude/worknotes/rfup-external-routing/litellm-router-eval.md`) into a durable, referenceable
> verdict artifact, per `rfup-external-routing-v1` Task P6-003 (DOC-006b) and the parent plan's
> Deferred Items Triage Table row `DF-RFUP-EXT-02`.

## 1. Purpose and scope

`pediatric-anemia-site`'s ADR-0008 (`0008-pathb-hardening-vs-native-adapter.md`, status `proposed`)
frames a choice between hardening the existing Path-B (Claude Code agent discovery swarm) workflow
versus adopting a native adapter for LLM routing/completion. `rfup-external-routing-v1` Phase 5
produced an **eval-only** verdict on the `litellm` package as the concrete native-adapter candidate,
under a hard constraint: no install, no live external calls, no credentials. This document is the
**sole rf-side artifact** carrying that verdict forward. It does not, and cannot, change ADR-0008's
status in the `pediatric-anemia-site` repository — see §4.

## 2. Verdict

**`conditional`** — conditional-accept of the native-adapter *direction*; defer the actual `litellm`
package install until a live-completion consumer is separately scoped and gated.

This resolves the choice ADR-0008 poses as two separable decisions rather than one binary:

1. Is the `litellm_router.py` *direction* (a config-driven model-routing adapter) sound and worth
   keeping? — **Yes.**
2. Should `litellm` be installed *now*? — **No, not yet.**

## 3. Rationale

### 3.1 Why not a clean `accept` (install now)

The decisive finding: installing `litellm` today buys **almost nothing functional**. The existing
`src/research_foundry/adapters/litellm_router.py` never calls `litellm` in either mode — it is a
config-driven *router* over `config/model_profiles.yaml`, and its `available()` check is a
non-importing `importlib.util.find_spec()` presence probe. Installing the package only flips
`available()` from `False` to `True`, changing the emitted routing decision from "always the first
preferred profile entry, `degraded=True`" to "the first environment-reachable entry, `degraded=False`".
No live completion, no network egress beyond that, and no credential transmission results from the
install itself.

Meanwhile the install carries real, non-zero costs, all confirmed via public/unauthenticated
metadata review (PyPI JSON API, GitHub public REST API, OSV vulnerability API) and a
`pip download --no-deps` inspection of the wheel/sdist (no install, no import):

- **Python-floor raise**: `litellm` requires Python `>=3.10`; RF's documented support floor is
  `3.9+` (with a `tomllib`/`tomli` shim). Installing would raise RF's effective floor.
- **Supply-chain incident**: versions `1.82.7`–`1.82.8` were confirmed to have shipped with
  credential-harvesting malware (OSV `GHSA-5mg7-485q-xm76` / `MAL-2026-2144` / `PYSEC-2026-2`) after
  an upstream token exposure. The affected range is well below the current stable release, but any
  install must hash-pin and explicitly exclude it.
- **Extreme release cadence**: ~34 releases/month on average (1,214 releases since 2023-07-27; 42 in
  the trailing 30 days as of 2026-07-22), including frequent `rc`/`dev` prereleases — a
  pin-and-track (renovate-style) maintenance burden.
- **On-disk audit surface**: the base wheel lands ~2,068 `.py` files, including a full ~1,339-file
  dormant proxy/server subtree — the same subtree the majority of `litellm`'s 27 unique disclosed
  advisories (6 critical, 16 high, 3 moderate as of 2026-07-22) target (auth bypass, SQL injection,
  SSTI, privilege escalation, RCE-via-`eval`). This code ships on disk even without the `proxy`
  extra, kept dormant by lazy imports (`_lazy_imports.py`) and by RF never launching the proxy or
  its console-scripts (`litellm`, `litellm-proxy`, `lite`).

Paying those costs to flip a boolean that only improves routing-metadata fidelity — while the actual
discovery/synthesis swarm still runs out-of-band via Path B — is a poor trade **at this moment**.

### 3.2 Why not a clean `reject` (abandon the adapter / harden Path B only)

The adapter is demonstrably well-built, correct, and cheap to keep. A prior commit (`2d198a8`)
already landed the dual-mode routing logic, the full provider→key mapping — including a correctness
fix mapping the `ica` provider to its own `RF_LLM_API_KEY` rather than a real-vendor key, encoding
the Mode-D Gate #2 invariant in code — plus `api_base` propagation and accompanying tests. It is
dormant, deterministic, and imposes zero runtime cost while `litellm` is absent; deleting it would
discard correct forward-compat groundwork for no gain.

The security profile is also more favorable than a naive reading of ADR-0008 might suggest: the CVE
surface is majority proxy/server, not the SDK `completion()` path RF's use case would exercise, and
that proxy code ships dormant. The native-adapter direction is not disqualified on security
grounds — the disqualifier for *acting now* is purely value-versus-cost timing.

### 3.3 Net verdict

Keep `litellm_router.py` as-is (dormant, correct, no code change from this plan). Pre-approve the
native-adapter direction as sound. Do not install `litellm` until a concrete live-completion consumer
is scoped as a separate, explicitly Mode-D feature.

## 4. rf-side / cross-repo boundary (seam boundary — read before acting on this document)

**This document is the sole rf-side deliverable of this evaluation.** It records the verdict and the
unexecuted install/wiring plan (§5) that a *future* feature would consume if the conditions in §5
are met.

**Out of scope, explicitly**: the actual status transition of ADR-0008 (`proposed` → `accepted` /
`rejected` / any other status) inside the `pediatric-anemia-site` repository. `rfup-external-routing-v1`'s
Hard Constraint 1 and Out-of-Scope list forbid editing `pediatric-anemia-site` from this plan — this
is a cross-repo write restriction, not an oversight. That status transition is tracked as a deferred
item in the parent plan's Deferred Items Triage Table under `DF-RFUP-EXT-02` (category
`dependency-blocked`) and is left for the `pediatric-anemia-site` maintainer to action, using this
document as the evidentiary basis.

## 5. Install / wiring plan (UNEXECUTED)

> Nothing in this section has been run. It is a forward recipe recorded so a future, separately-gated
> feature does not need to restart the evaluation from zero. Installing `litellm` to merely satisfy
> `requires=("litellm",)` is explicitly **not** sufficient justification on its own — see condition 1
> below.

**Conditions that must all hold before this plan executes:**

1. A live-completion consumer of the routing decision is scoped as its own, explicitly Mode-D
   feature (per this project's delegation-modes rule) — installing `litellm` for `available()` alone
   is a no-op functional gain, per §3.1.
2. RF's supported-Python floor is confirmed acceptable to raise `3.9 → 3.10`, or `litellm` is
   isolated as an optional/extra dependency so the floor raise is opt-in.
3. The install pins an exact, hash-verified version and encodes an allowlist that excludes the
   poisoned `1.82.7`–`1.82.8` release range.
4. A pin-and-track posture is accepted for the package's fast release cadence.

**Steps, once the conditions hold:**

1. **Dependency declaration (isolated)** — add `litellm` as an optional/extra dependency (e.g. a
   `litellm` extra in `pyproject.toml`), never a core dependency. Install without any extra
   (`pip install litellm`, never `litellm[proxy]`/`[extra-proxy]`/`[proxy-runtime]`) so the
   CVE-heavy proxy runtime dependencies are never pulled.
2. **Supply-chain pin** — pin an exact version at or above the then-current stable release,
   hash-lock it, and add the package to whatever dependency-scanning the repo runs.
3. **Verify the behavioral delta, and nothing more** — confirm `litellm_router.available()` returns
   `True` post-install and that `route()` now runs its reachability loop (first
   environment-reachable entry, `degraded=False`). This is the entire adapter-level behavioral
   delta; no adapter code imports or calls `litellm`, and the install itself must not introduce any
   live call.
4. **(Separate feature) live-completion consumer** — the genuine Mode-D work (constructing a client
   and issuing a real `completion()` call) is out of scope for the adapter and for this install
   step. It is a distinct feature with its own Mode-D gate and credential handling, honoring the
   `ica` → `RF_LLM_API_KEY` invariant. It must not be folded into the install change.
5. **Audit-surface acknowledgement** — record in the install's change description that the base
   wheel lands a dormant proxy subtree plus secret-manager/MCP/rust-bridge/sandbox code on disk,
   kept inert by lazy imports and by RF never launching the `litellm`/`litellm-proxy`/`lite`
   console-scripts.

**Rollback**: because the adapter degrades deterministically when `litellm` is absent, rollback is
simply uninstalling the package — the adapter reverts to its degraded default with no code change
required.

## 6. Confidence and limitations

This verdict was produced under an eval-only bound (no install, no import, no execution). Its
confidence is asymmetric:

- **High confidence** in the verdict *direction* — it rests on the structural, statically-verifiable
  fact that installing `litellm` does not, by itself, trigger a live call for this adapter (grounded
  in a static source-read: no `import litellm` statement, a `find_spec`-only presence probe, and
  env-var *presence* checks only).
- **Medium confidence** in the quantitative security/dependency depth — the dependency tree
  inspected is `litellm`'s *declared* first-level `Requires-Dist` set, not a resolved transitive
  closure; the CVE proxy-vs-SDK split is based on advisory titles/descriptions and file-count
  weighting, not a per-CVE code-path trace; all figures are point-in-time as of 2026-07-22 against a
  package releasing ~34 times/month.

A future security review performed at actual install time (once the §5 conditions are met) should
re-verify point-in-time figures rather than relying on this document's snapshot.

## 7. Source record

The full evaluation record — including the raw PyPI/GitHub/OSV data, the `pip download --no-deps`
inspection details, and the adapter cross-reference analysis — lives at
`.claude/worknotes/rfup-external-routing/litellm-router-eval.md`. This document is the promoted,
durable summary; the worknote remains the detailed working record.
