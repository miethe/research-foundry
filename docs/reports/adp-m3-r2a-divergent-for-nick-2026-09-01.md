# ADP-M3-R2a — bounded backfill phase + DIVERGENT LIST for Nick

_Generated 2026-09-01. Repo: `/Users/miethe/dev/homelab/development/research-foundry`. Worktree `campaign/adp-m3-r2a-0901` off `origin/main`. Mode C (bounded write, worktree, draft PR, no merge)._

Inputs: `adp-m3-r2-enumeration-2026-09-01.md` (224 artifacts) · `adp-m3-r2-reconcile-2026-09-01.md` + `.json` (146 gap / 17 drift / 180 expected).

Catalog authority = `skillmeat` Enterprise node `http://10.42.10.76:8080` (same authority Leg 1/2 used via `skillmeat show`). Secrets from `~/.config/aos/secrets.env`. No 401s.

---

## What was done (steps 1–3)

### Step 1 — the 2 "present-identical" (`skill:planning`, `skill:dev-execution`)
**They are NOT identical — no adopt performed.** Leg 1 read `present-identical` off a stale `.skillmeat-deployed.toml` (`local_modifications=false`). The hash-bearing reconcile triple disagrees:

| skill | Hc (catalog) | Hd (deployed) | Hl (ledger) | gate | reading |
|---|---|---|---|---|---|
| planning | `bfc2b00d` | `7815e70f` | `bfc2b00d` | row2 `capture` | local hand-edit, upstream unmoved (Hd≠Hl, Hl=Hc) |
| dev-execution | `323e4e6b` | `58fac0bc` | `428b0da6` | row3 `queue` | 3-way diverged, no mechanical merge authority |

Both carry a ledger row, so both are **out of the divergent-no-ledger list**, but both need a decision — see "Ledgered divergences" below. `planning` is a clean `capture` candidate (adopt the hand-edit as a new catalog version); `dev-execution` needs your merge call. Neither actioned in R2a (would be writeback / needs your authority — Mode C stop).

### Step 2 — register ABSENT-from-catalog, capture-capable artifacts as `project_original`
Documented path used: **`skillmeat enterprise add <file> --type agent --scope user`** (surgical, per-artifact, create-or-update by type+name). `skillmeat enterprise capture .` was **rejected** as the vehicle — its dry-run would attempt all **195** on-disk artifacts (new immutable versions for every drift row = writeback at scale, a hard gate). `enterprise add` touched exactly the 10 below.

**10 agents registered (all `✓ created`, Source: `upload`):**
`rf_claim_auditor` · `rf_deep_reader` · `rf_discovery_lead` · `rf_domain_researcher` · `rf_governance_officer` · `rf_intake_curator` · `rf_source_carder` · `rf_source_scout` · `rf_synthesizer` · `rf_knowledge_lookup`

Verified: `skillmeat show rf_claim_auditor --type agent` → found (was "not found" in Leg 1).

**NOT capture-capable — listed, untouched (per brief):**
- rules (7 on disk; 2 were absent, `git-workflow.md`, `plan-bookkeeping.md`): `skillmeat` rejects rule upload — _"rule artifacts not yet upload-supported (artifact_type_allowlist.UPLOAD_SUPPORTED_TYPES)"_.
- hooks (5 absent): `post-tool.md/{format-javascript-files,format-python-files,git-add-changes,run-tests-after-changes,update-symbols-on-code-change}.json` — sub-entries inside the `post-tool.md` bundle, not separately catalogable (`post-tool.md`/`post-tool` already in catalog).

### Step 3 — 123 `[unknown]` + 23 `[in_catalog]` gaps: classification
**Zero deployments recorded.** Byte-identity is not machine-verifiable on this Enterprise node: `skillmeat show` emits no hash/content; `skillmeat diff artifact <n> --upstream` → _"no upstream source"_; the reconcile hash triple only covers the 34 verified-present artifacts, not gaps. Per the brief's explicit fallback ("_otherwise leave for the divergent list_"), every catalog-present candidate is carried below, not adopted.

- **123 `derived_unverified` — all NOT in catalog → RF-authored or scanner phantom.** These are scanner inferences: colon-namespaced command slugs (`dev:autopilot`, `fix:ci`, …), agent identity strings (`claude-fable-5`, `human`, `general-purpose`), and context/spec names. None are "deployed-from-global copies" (absent from catalog by definition). Not capture-capable as-is (no standalone file, or not a real artifact). No action.
- **23 `[in_catalog]` gaps — name present in catalog, none deployed at the expected path.** Split by on-disk evidence:
  - **9 with an on-disk file at a non-catalog path/type** (catalog expects `context:`; file lives under `rules/` or `specs/`) → **divergent list, table B.**
    `context-budget`, `delegation-modes`, `git-workflow`, `lsp-diagnostics`, `progress-cli-only` (in `.claude/rules/`); `changelog-spec`, `doc-policy-spec`, `skills-index`, `version-bump-spec` (in `.claude/specs/`).
  - **14 with no on-disk file** → genuine not-deployed gaps, nothing to adopt: `bob-delegate-executor`, `codex-executor`, `ica-executor`, `artifact-tracker` (only nested inside `skill:artifact-tracking`), `aos-operating-rules`, `artifact-provisioning`, `finding-capture`, `intenttree-integration`, `meatywiki` (context: expected; only the 3 `meatywiki*` skills exist), `mode-d-enforcement`, `shared-checkout-safety`, `delegation-router`, `delivery-report` (only `verify-delivery-report.sh` inside `skill:dev-execution`), `skillmeat-cli`.

---

## DIVERGENT LIST — local ≠ catalog, no ledger row

### Table A — the 15 no-ledger drift rows (reconcile gate row6, `refuse_queue`, provenance unknown)
Diff pointer = reconcile hash triple `Hc` (catalog / `~/.skillmeat/collections/default/…`) vs `Hd` (deployed / `<repo>/.claude/…`); `Hl` absent. Re-derive with `skillmeat project reconcile <repo> --check --json` → `gate_verdicts[]`.

| name | type | one-line stakes | diff pointer (Hc → Hd) |
|---|---|---|---|
| a11y-sheriff | agent | accessibility review agent — local edits vs catalog unknown direction | `227959f8` → `ecd7887f` · `.claude/agents/ui-ux/a11y-sheriff.md` |
| backend-architect | agent | backend architecture agent; drives many plans | `25f2e335` → `2390b3a8` · `.claude/agents/architects/backend-architect.md` |
| changelog-generator | agent | release-notes agent; wrong copy skews changelogs | `11c6c7b2` → `ebed5d62` · `.claude/agents/tech-writers/changelog-generator.md` |
| data-layer-expert | agent | DB/schema agent; divergence risks bad migration advice | `00d77d77` → `e1c90036` · `.claude/agents/architects/data-layer-expert.md` |
| documentation-expert | agent | docs agent; local prompt drift | `8573927b` → `5a235ae2` · `.claude/agents/tech-writers/documentation-expert.md` |
| documentation-writer | agent | docs-writing agent; local prompt drift | `0cec42da` → `5d1382d3` · `.claude/agents/tech-writers/documentation-writer.md` |
| feature-sprint-executor | agent | executes feature sprints; behavior drift affects delivery | `0bef292e` → `781f4156` · `.claude/agents/dev/feature-sprint-executor.md` |
| frontend-developer | agent | FE build agent; local prompt drift | `1ef58b8e` → `11122d67` · `.claude/agents/dev-team/frontend-developer.md` |
| search-specialist | agent | research/search agent used by RF flows | `d74f9e7d` → `8c7c2886` · `.claude/agents/ai/search-specialist.md` |
| task-completion-validator | agent | gate agent; validates "done" — drift weakens the gate | `0d108706` → `627a382f` · `.claude/agents/reviewers/task-completion-validator.md` |
| artifact-tracking | skill | ledger/tracking skill; local ≠ catalog on a governance-adjacent skill | `b5427877` → `46e54d7a` · `.claude/skills/artifact-tracking/` |
| council-review | skill | offline council gate skill; drift affects review quality | `8f859546` → `5fc12140` · `.claude/skills/council-review/` |
| intenttree-cli | skill | IntentTree CLI wrapper skill; drift → wrong CLI usage | `3dd31c76` → `559912b1` · `.claude/skills/intenttree-cli/` |
| symbols | skill | symbol-graph skill; drift → stale symbol workflow | `727d2e4e` → `1e8f600a` · `.claude/skills/symbols/` |
| workflow-authoring | skill | master workflow-authoring contract skill; drift is high-stakes | `d17b3041` → `fa485281` · `.claude/skills/workflow-authoring/` |

### Table B — step-3 path/type-mismatch divergences (catalog `context:<name>`, on-disk elsewhere, byte-identity unverifiable)

| name | type (catalog) | one-line stakes | diff pointer |
|---|---|---|---|
| context-budget | context | rule body on disk, `context:` in catalog — unverified identical | `.claude/rules/context-budget.md` vs `context:context-budget` |
| delegation-modes | context | delegation policy; type/path split, content unverified | `.claude/rules/delegation-modes.md` vs `context:delegation-modes` |
| git-workflow | context | git policy; was "absent" in Leg 1, now `context:` in catalog | `.claude/rules/git-workflow.md` vs `context:git-workflow` |
| lsp-diagnostics | context | LSP policy; type/path split | `.claude/rules/lsp-diagnostics.md` vs `context:lsp-diagnostics` |
| progress-cli-only | context | progress-CLI enforcement rule; type/path split | `.claude/rules/progress-cli-only.md` vs `context:progress-cli-only` |
| changelog-spec | context | changelog spec; on disk under `specs/` | `.claude/specs/changelog-spec.md` vs `context:changelog-spec` |
| doc-policy-spec | context | doc policy spec; on disk under `specs/` | `.claude/specs/doc-policy-spec.md` vs `context:doc-policy-spec` |
| skills-index | context | skills index spec; on disk under `specs/` | `.claude/specs/skills-index.md` vs `context:skills-index` |
| version-bump-spec | context | version-bump spec; on disk under `specs/` | `.claude/specs/version-bump-spec.md` vs `context:version-bump-spec` |

### Ledgered divergences (have a ledger row — outside the "no ledger" list, still need a decision)

| name | type | stakes | pointer |
|---|---|---|---|
| planning | skill | local hand-edit, upstream unmoved → clean `capture` candidate | Hc=Hl `bfc2b00d`, Hd `7815e70f` · `.claude/skills/planning/` |
| dev-execution | skill | 3-way diverged; needs your merge call, no mechanical authority | Hc `323e4e6b` / Hd `58fac0bc` / Hl `428b0da6` · `.claude/skills/dev-execution/` |

---

## Step 5 — reconcile re-run: counts vs baseline

`skillmeat project reconcile /Users/miethe/dev/homelab/development/research-foundry --check --json` (exit 2, `--check` with non-empty gaps — expected):

| metric | baseline (2026-09-01 Leg 2) | after R2a | Δ |
|---|---|---|---|
| gaps (summary "gap(s)") | 146 | **146** | 0 |
| &nbsp;&nbsp;— `gaps[]` `[in_catalog]` | 23 | 23 | 0 |
| &nbsp;&nbsp;— `derived_unverified[]` `[unknown]` | 123 | 123 | 0 |
| drift | 17 | **17** | 0 |
| expected | 180 | **180** | 0 |

**`project reconcile` counts are unchanged — this is expected, not a failure.** The 10 registered `rf_*` agents were never members of reconcile's *derived expected set* (they are not referenced by any scanner convention / roster the gate scans), so registering them cannot move `gaps`/`drift`/`expected`. What R2a changed: the 10 RF-authored agents now exist in the Enterprise catalog with `project_original` provenance (Source `upload`), removing them from the ABSENT-from-catalog population Leg 1 enumerated (17 → 7, the remaining 7 being non-capture-capable rules/hooks).

**Exit-criterion implication for Nick:** R2a backfilled provenance for RF-authored artifacts, but the R2 gap/drift numbers only move once (a) the drift rows in Tables A/B are resolved (adopt-or-diverge decisions), and (b) the 23 `[in_catalog]` gaps are deployed at their catalog-expected `context:` paths or removed from the expected set. Those are the real R2 exit work, not backfill.
