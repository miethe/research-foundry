---
title: State audit — pediatric fidelity validator, exact-passage gate, Path-B parameterization, native adapters
doc_type: worknote
created: 2026-07-21
scope: feat/rf-swarm-driver-and-litellm vs main (RFUP-1..5,7 landed 001a834; RFUP-6 deferred)
---

# State audit: 4 RFUP items on `feat/rf-swarm-driver-and-litellm`

## Branch delta vs main

`git log --oneline main..HEAD`:

```
2c775fd docs(plan): Tier 3 plan for rights & evidence-item entity model
0dc7c4e feat(swarm-drive): E1-P1 sensitivity gate + governed MeatyWiki writeback (HITL)
4749364 feat(swarm-drive): E1-P0b SD-008 --llm-legs ica leg-request emit
503fa75 feat(swarm-drive): E1-P0a deterministic rf swarm drive spine + CLI
```

None of these four commits touch items 1, 2, or 3 below. Only item 4 (litellm_router) has branch
movement — via a commit *not* in this range: `2d198a8` ("ica provider in litellm_router") is an
ancestor already on `main`-side history reachable from this branch (not a `main..HEAD` addition;
it predates the swarm-drive commits). So of the four RFUP items audited, **none were advanced by
the swarm-drive/litellm branch work itself** — the branch's own commits are about the swarm-drive
CLI spine and MeatyWiki writeback gate, unrelated to items 1–3, and the litellm_router "ica
provider" change already existed before this branch's commit range starts.

## PRD/impl-plan context (frontmatter only, not read line-by-line)

- `rf-upstream-evidence-foundry-v1` PRD/impl-plan: Tier 3, ~29 pts, scoped RFUP-1 (Path-B
  parameterization), RFUP-2, RFUP-3 (exact-passage gating), RFUP-4, RFUP-5, RFUP-7. Impl-plan
  status: `completed`. RFUP-6 (native discovery adapters) explicitly deferred — its own design-spec
  doc is a placeholder ("idea" maturity) with a defer-until trigger (measured value gap or
  governance-cleared requirement), not an implementation-ready spec.

## Item 1 — Pediatric/clinical quote-content fidelity validator

**Status: ABSENT.** No quote-content fidelity check exists anywhere in `src/research_foundry`.

**Evidence:**
- `src/research_foundry/services/source_cards.py:37-49` — `ExtractionStatus` enum
  (`full_text`/`partial`/`locator_only`) is a *retrieval-completeness* signal (did the fetch get
  the full text vs. only a locator), unrelated to whether a quote's characters match the source
  verbatim.
- `src/research_foundry/services/verification.py:273-303` (`_index_source_cards`) computes only
  `has_locator` / `has_quote` booleans — presence, not content correctness.
- `src/research_foundry/services/verification.py:1051-1099` (`check_anchor_hash_match`) hashes the
  claim_link's `quote_text_hash` against the *stored* quote and flags drift if the stored quote
  changed — this catches tampering/edits to the source card after linking, not fidelity between
  the stored quote and the original source document (e.g. a PMC extractor silently normalizing
  `×10⁹/L` → `×10/L`).
- No hits anywhere in `src/research_foundry` for `superscript`, `×10`, or any passage-diffing /
  character-fidelity comparator against original source text.

**Gap remaining:** the known gap ("`rf verify` misses quote-content fidelity — PMC strips
superscripts") is fully open. Nothing in the codebase compares an extracted quote's characters
against the live/original source rendering; `check_anchor_hash_match` only detects post-hoc
tampering of the already-extracted (possibly-already-corrupted) quote.

## Item 2 — Exact-passage hard-gate (RFUP-3)

**Status: DONE, mode-dependent, default is warn-only (not hard by default).**

**Evidence:**
- `src/research_foundry/services/verification.py:412-461` —
  `resolve_exact_passage_mode()` resolves `verify.exact_passage` from
  `config/claim_policy.yaml`, overridable via CLI `--exact-passage` (wired in
  `src/research_foundry/cli_commands.py:450-464`). Valid values: `warn` (default) | `strict`
  (`_VALID_EXACT_PASSAGE_MODES`, line 413). Bad override values raise `RFError` (fail-closed).
- `src/research_foundry/services/verification.py:712-753` — the `exact_passage_present` check
  itself: for every `status == "supported"` claim citing >=1 source card, it checks whether any
  cited card has `has_quote=True` (an `extracted_points[].quote` anchor). When
  `exact_passage_mode == "strict"`, missing anchors are `add(..., "fail", ...)` **and** appended to
  `unsupported[]` — the same list `material_claims_have_claim_ids` uses to block publish, i.e. it
  IS a hard gate (fails the run / blocks publish) in strict mode. In `warn` mode (the default),
  it's `add(..., "warn", ...)` and never touches `unsupported[]` — non-blocking.
- Eligibility scope is implicit, not a separate named check: only `status == "supported"` claims
  that cite >=1 source card are considered ("supported claims that cite >=1 source card" —
  claims with 0 cited sources are already caught by `supported_claims_have_source_cards`). There is
  no additional eligibility filter by sensitivity/source-type/claim-type.
- A stale docstring artifact: `resolve_exact_passage_mode`'s own docstring (line ~423) still says
  "the actual eligibility check that consumes this mode is wired in a later task" — this is
  outdated; the check is fully wired (lines 744-748) in this same file.

**Gap remaining:** none functionally — RFUP-3 is implemented as designed (config/CLI-selectable
warn|strict). The only "gap" is that `strict` is opt-in, not the shipped default, so pediatric/CDS
runs relying on default settings get warn-only behavior unless a run explicitly sets
`--exact-passage strict` or `verify.exact_passage: strict` in `config/claim_policy.yaml`.

## Item 3 — Path-B parameterization (RFUP-1)

**Status: DONE** for both workflow scripts — no hard-coded RF/repo/TMP/date paths remain as
*requirements*; they're only fallback defaults. **No run-date tests exist.**

**Evidence:**
- `.claude/workflows/rf-run-execute.js:16-38` — `resolvePath()` resolves any arg against
  invocation cwd; `RF = resolvePath(A.rf_bin || '/Users/miethe/.local/bin/rf')`,
  `REPO = resolvePath(A.repo || '.../research-foundry')`,
  `TMP = resolvePath(A.tmp_dir || '/Users/miethe/.claude/jobs/85ede6ca/tmp')`,
  `run = A.run_id` (required — throws `{error: 'missing run_id in args'}` if absent, line 37),
  `refslug` from `A.ref`, `MAXS = A.max_sources || 12`. Date handling:
  `stampFromTimestamp(A.timestamp)` parses an ISO date arg (no `Date.now()`/`new Date()` in the
  script body — per workflow-authoring's four-constraints checklist) with a literal fallback
  `'20260613'` only if `A.timestamp` is absent/malformed.
- `.claude/workflows/rf-pediatric-cds-run-execute.js:26-29` — same pattern:
  `REPO = A.repo || '<literal>'`, `RF = A.rf_bin || (REPO + '/.venv/bin/rf')` (explicit comment:
  "DIRECT local binary — NOT the ~/.local/bin/rf shim"), `TMP = A.tmp || (REPO +
  '/.claude/tmp/rf-peds-swarm')`, `STAMP = A.stamp || '20260718'` — all args-first with literal
  fallback, not hard-coded requirements.
- No `path` import in either script (comment in `rf-run-execute.js:19-20` notes this deliberately —
  plain string concatenation matches sibling workflow style / the no-FS-module workflow-authoring
  constraint).
- Test coverage: no test file references `rf-run-execute`, `stampFromTimestamp`, or "run-date"
  anywhere in the repo (`grep` across `*.test.js` and a filename search both came back empty).

**Gap remaining:** parameterization itself is complete; there is no automated test asserting
`stampFromTimestamp`'s parsing behavior or the fallback-default paths, so a regression in date
derivation would only surface at actual run time.

## Item 4 — Native discovery adapters (RFUP-6, deferred), especially litellm_router

**Status: SCAFFOLD-ONLY for all 6 non-`arc_council` adapters; litellm_router got ONE real
improvement (ICA-aware config mapping) but the `litellm` package itself is still absent, so the
adapter still never performs a live external call.**

**Evidence:**
- `src/research_foundry/adapters/__init__.py:16-25` — `_CONCRETE` lists 8 adapters:
  `arc_council`, `claude_agent_sdk`, `gpt_researcher`, `notebooklm`, `openai_agents`, `paperqa2`,
  `opencode`, `litellm_router`. Per the RFUP-6 design-spec's own problem statement, only
  `arc_council` is installed/live in production discovery runs.
- `./.venv/bin/python -c "import litellm"` → `ModuleNotFoundError: No module named 'litellm'` —
  confirmed not installed in this repo's venv.
- `src/research_foundry/adapters/litellm_router.py:1-16` (module docstring) — explicit: "In the
  default environment `litellm` is not installed and no provider keys are present, so
  `available()` is False, and `route()` deterministically returns the profile's first `preferred`
  entry (degraded, no live completion)." `requires = ("litellm",)` (line ~48).
- `src/research_foundry/adapters/litellm_router.py:28-42` — the RFUP-6-adjacent branch work
  (commit `2d198a8`, already on `main`-side history, predates this branch's `main..HEAD` range):
  added `_PROVIDER_KEYS["ica"] = "RF_LLM_API_KEY"` with a correctness comment (an unmapped
  provider would be wrongly treated as key-free/reachable like `ollama`). This is a config/mapping
  correctness fix, not an adapter install — `self.available()` still gates on `litellm` being
  importable, which it isn't, so this branch never executes (line 92: `if self.available():` before
  the reachable-provider loop).
- `config/model_profiles.yaml:1-40` — concrete ICA model ids on the `ica` provider / OpenAI-
  compatible `/ica/v1` path, explicit note that "rf's litellm_router RESOLVES a profile to a
  decision; the discovery/synthesis swarm is driven OUT-OF-BAND (Path B ...)" — i.e. the config
  work supports Path-B's model-profile *bookkeeping*, not a live in-process LiteLLM completion
  path.
- The other 5: `gpt_researcher.py:56-67`, `paperqa2.py:18-27`, `opencode.py:17-31` all follow the
  same `requires = (<pkg>,)` / `if not self.available(): return self._degraded(...)` pattern, and
  even the "present but real mode is opt-in" comment on `gpt_researcher`/`paperqa2` shows that
  even if the dependency were installed, the adapter still declines to make a real call by design.
  `notebooklm.py:212-252` and `openai_agents.py:54-160` are similarly degraded-by-default with
  documented fallback-stub behavior; `openai_agents.py:106` layers an `_sdk_client` check on top of
  `super().available()` but still requires an explicit live client to escape degraded mode.
- `src/research_foundry/adapters/base.py:9-19` (module docstring) — this dual-mode contract
  (available vs. degraded-stub) is a deliberate MVP design, not an oversight: "This dual mode is
  what lets the MVP install and run end-to-end with no API keys."

**Gap remaining:** RFUP-6 is correctly reflected as fully deferred in code — no adapter beyond
`arc_council` performs a live external call. The `litellm_router` ICA-mapping change is a forward-
compat correctness fix for *when* `litellm` is later installed, not an activation of it now.
Installing/evaluating any of the 6 remains gated on the design-spec's defer-until trigger
(documented comparison run showing a Path-B value gap, or a governance-cleared requirement) — no
such trigger evidence exists in the repo.

## Mode-D signals observed

- `litellm_router.py` handles a credential (`RF_LLM_API_KEY`) and an `api_base` URL, but because
  `litellm` is not installed, `self.available()` is always `False` and the reachable-provider/key
  lookup branch never executes — no network egress or secret use happens in the current code path.
  `config/model_profiles.yaml` states the key itself lives only in
  `~/.config/research-foundry/serve.env` (0600), not in the repo.
- No other Mode-D signals (no auth/payment/deletion/migration code) touched by any of the 4 items.
