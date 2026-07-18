---
schema_version: 2
doc_type: design_spec
id: DS-notebooklm-research-foundry-refresh-v1
title: NotebookLM and Research Foundry Interchange Refresh
status: draft
maturity: shaping
created: 2026-07-18
updated: 2026-07-18
feature_slug: notebooklm-research-foundry-refresh
feature_version: v1
problem_statement: "The offline-built NotebookLM integration lacks a live-qualified runtime contract and currently exposes conflicting source-add command forms."
open_questions:
  - Which NotebookLM account and isolated profile may run a public-data canary?
  - Which exact CLI release and package hash will be the first qualification target?
  - Does live citation output support unambiguous exact-passage recovery?
  - What retained external identifiers are necessary for replay and audit without storing auth material?
  - Who authorizes canary notebook deletion after qualification evidence is sealed?
explored_alternatives:
  - Manual deterministic interchange only
  - Manual interchange plus a pinned unofficial CLI canary
  - Immediate end-to-end unofficial CLI automation
  - Browser automation or waiting for a supported official API
prd_ref: docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
plan_ref: .codex/plans/research-interchange-provenance-access-initiative-v1.md
related_documents:
  - docs/projects/research-foundry/notebooklm-integration-plan.md
  - .agents/skills/notebooklm/SKILL.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
owner: nick
contributors: []
priority: high
risk_level: high
tags:
  - notebooklm
  - research-interchange
  - provenance
  - qualification
  - unofficial-cli
  - shaping
---

# NotebookLM and Research Foundry Interchange Refresh

## 1. Decision Summary

The first supportable NotebookLM boundary is **manual deterministic interchange**.
Research Foundry (RF) writes and seals a stable export set before an operator transfers
permitted files to NotebookLM. Material returned from NotebookLM enters RF only through
the vendor-neutral `external_research_handoff/v1` packet and remains candidate material
until RF resolves the original source, exact passage, and claim relationship.

Automation through `notebooklm-py` remains **experimental**. A future Tier-1 feature
contract may qualify one pinned CLI version with public synthetic data, an isolated auth
profile, explicit notebook IDs, captured command/JSON shapes, deterministic receipts, and
a kill switch. That contract may not promote broad auto-sync, sensitive-data upload,
background artifact generation, or MCP mutation tools.

NotebookLM synthesis is never primary evidence. It may be retained as
`platform_synthesis`, an assertion candidate, or an explicitly labeled inference; it does
not become a source card, source assertion, verified claim, or report authority merely
because NotebookLM displays citations.

## 2. Current Truth — 2026-07-18

| Surface | Live evidence | Truthful state |
|---|---|---|
| Legacy design plan | Declares `implemented (offline; live-unvalidated)` and describes an offline-built client, adapter, writeback, intake, correlation, sync, and workflows | Repository surface exists; external behavior is unqualified |
| Local runtime | `notebooklm` is not on PATH in the current workspace shell | CLI version, help, auth, RPC, output schemas, rate limits, and service reachability were not executed |
| Current skill | `.agents/skills/notebooklm/SKILL.md` identifies `notebooklm-py v0.3.2` and documents `notebooklm source add` | Documentation input only; not live proof on this machine |
| Integration client | `NotebookLMClient.add_source()` constructs `source add <locator> --notebook <id> --json` and is covered by subprocess mocks | Offline-tested command construction; no authenticated canary |
| Operator sync helper | `rf notebooklm sync` prints `notebooklm add-source --notebook ...` and does not execute it | Stale command form and manual instruction only |
| Writeback | Candidate YAML and fail-soft paths have repository tests; existing architecture docs say the live push has not been exercised from RF | `offline-unvalidated`; not shipped as a qualified external write |

The legacy plan remains useful as an inventory of intended seams. Its implementation
claims must be read with the parenthetical qualifier: offline mocks prove local behavior,
not compatibility with the current unofficial client or NotebookLM service.

### 2.1 Command contract reconciliation

The canonical command for the next qualification attempt is not selected from memory or
from the stale helper. It is discovered from the **installed pinned binary** and sealed in
the canary record.

| Source | Add-source form | Treatment |
|---|---|---|
| Current NotebookLM skill | `notebooklm source add <locator> --notebook <id> --json` | Candidate current contract |
| Legacy integration plan | `notebooklm source add ...` | Consistent with the current skill, but still unvalidated live |
| RF integration client | argument vector `source`, `add`, `<locator>`, `--notebook`, `<id>`, `--json` | Retain until a pinned-binary probe disproves it |
| `rf notebooklm sync` output | `notebooklm add-source --notebook <id> ...` | Stale; do not copy into a new contract |

No compatibility fallback should silently try both verbs. A failed preflight must stop
external automation with a machine-readable `cli_contract_mismatch` result; it must not
guess against a live account.

## 3. Authority and Trust Boundary

The authority chain remains:

```text
origin envelope
  -> acquisition/import receipt
  -> immutable source edition
  -> exact passage
  -> source assertion/evaluation
  -> verified claim or labeled inference
  -> report-use edge
```

NotebookLM notebook IDs, source IDs, citation numbers, answers, generated reports, and
artifact IDs are external observations. They can support correlation and replay but do
not replace an immutable edition or exact RF passage. When an original source is missing,
inaccessible, drifting, sensitive, or ambiguous, the imported item stays quarantined with
a structured denial reason.

Deterministic interchange means the RF packet, selection decision, hashes, and receipts
are stable for the same RF inputs and policy snapshot. It does **not** claim that
NotebookLM generation is deterministic or reproducible.

## 4. First Supported Mode: Manual Deterministic Interchange

This section defines the target support contract. It does not claim that a live exchange
was executed on 2026-07-18.

### 4.1 RF outputs to NotebookLM

RF first writes a sealed, reviewable export directory. A minimal projection contains:

```text
runs/<run_id>/exports/notebooklm/<export_id>/
  export_manifest.yaml
  report.md
  sources/
    <source-card-projection>.md
  checksums.sha256
  transfer_receipt.yaml
```

- `export_manifest.yaml` records schema version, run and evidence-bundle IDs, selected
  files, source assertion/claim references, policy/profile decision, sensitivity, and the
  hash algorithm. It never contains cookies, OAuth state, tokens, or raw auth paths.
- `report.md` is a deterministic projection of verified RF output with claim identifiers
  retained. It is a convenience source for NotebookLM, not a new authority copy.
- `sources/` includes only explicitly permitted projections. Denied, sensitive, missing-
  rights, retracted, or stale material is omitted and recorded as a denial in the manifest.
- `checksums.sha256` seals the bytes presented for transfer.
- `transfer_receipt.yaml` begins as `proposed`. After a human performs the upload, the
  operator may record the observed notebook/source IDs, timestamp, actor, and result.

The operator may use the NotebookLM UI or a separately qualified CLI. RF support attaches
to the sealed packet and receipt, not to an unrecorded drag-and-drop or implicit background
sync. No PostToolUse hook may auto-upload run directories under this supported mode.

### 4.2 NotebookLM reports and sources back to RF

The return path is `external_research_handoff/v1`, owned by the external-interchange
workstream:

```text
external_research_handoff/v1/
  handoff.yaml
  report.md
  sources.yaml
  assertion_candidates.yaml
  activity/                 # optional
  attachments/              # optional
```

- `handoff.yaml` records `platform: notebooklm`, notebook/export identifiers, acquisition
  method (`manual_ui` or qualified CLI), observed version when available, timestamps,
  packet hashes, profile classification, and operator attribution.
- `report.md` is labeled `platform_synthesis`; generated prose is not evidence.
- `sources.yaml` records original locators and NotebookLM source references separately.
  A NotebookLM source ID is not an edition identifier.
- `assertion_candidates.yaml` preserves candidate text and citation hints without creating
  claims. Citation numbers are treated as hints until RF resolves the original source and
  exact passage.
- Optional downloaded artifacts remain attachments. Audio, video, quizzes, mind maps, or
  data tables do not enter the claim ledger directly.

Import must be idempotent and resumable. Replaying identical bytes yields the same import
receipt and no duplicate authoritative records. Locator-only, source-resolved,
passage-resolved, and verified completeness remain distinct states.

## 5. Experimental Mode: Pinned Unofficial CLI Automation

The CLI track is an opt-in qualification experiment, not the supported data-authority
boundary. The canary must:

1. Pin the `notebooklm-py` release and artifact hash; disable implicit upgrades.
2. Capture `notebooklm --version` and relevant `--help` output before any mutation.
3. Use a dedicated `NOTEBOOKLM_HOME` outside the repository and a designated canary
   account. Never print or persist `NOTEBOOKLM_AUTH_JSON` in RF artifacts.
4. Avoid shared `notebooklm use` state. Pass full notebook UUIDs explicitly on every
   supported command and start isolated conversations where the client permits it.
5. Use public synthetic fixtures only. The first canary may not contain owner/private,
   work-sensitive, client-sensitive, licensed, or unreleased corpus material.
6. Exercise one bounded round trip: create or select a canary notebook, add a known RF
   fixture, wait for indexing, query it, export observed source/report material, assemble
   an external handoff, and run RF import in dry-run/quarantine mode.
7. Capture redacted argv, exit codes, stdout JSON schemas, external IDs, timestamps,
   retries, rate-limit observations, and packet/receipt hashes.
8. Fail closed on auth, command, response-schema, profile, sensitivity, timeout, or
   citation-resolution mismatch. No alternate verb or browser fallback runs silently.
9. Provide a kill switch and a rollback procedure that disables live calls while keeping
   deterministic candidates and receipts readable.

Deletion of the canary notebook is a separate destructive action and requires explicit
owner authorization. Qualification is valid without deletion if the retained notebook is
documented and contains public synthetic data only.

## 6. Options

| Option | Benefits | Costs and risks | Disposition |
|---|---|---|---|
| A. Manual deterministic interchange only | Smallest trust boundary; UI-compatible; packet and receipts remain reviewable | Operator effort; no automated reachability proof | Safe baseline |
| B. Manual interchange plus pinned CLI canary | Preserves the baseline while producing versioned live evidence and a bounded path to automation | Auth/profile handling and unofficial RPC drift remain | **Recommended** |
| C. Promote the offline-built integration directly | Reuses substantial code and mocks | Converts inferred command/JSON shapes into production claims; stale sync verb; no local runtime | Reject |
| D. Browser automation or wait for a supported official API | Could avoid the current CLI contract | Browser profiles widen the secret/UI drift surface; future API timing is unknown | Reassess later, not a fallback |

## 7. Recommended Direction

Adopt Option B in two truthfully separated layers:

1. Define manual deterministic exchange as the support contract and make the vendor-neutral
   external handoff the only inbound route.
2. Keep all NotebookLM automation disabled by default while this spec is `shaping`.
3. When the promotion gates below pass, create one Tier-1 qualification contract limited
   to preflight, the public canary, receipt capture, and correction of the proven command
   surface. Broader integration work receives a separate estimate and review.

The existing client, adapter, correlation registry, writeback candidate, and workflows are
inputs to qualification. Their presence does not waive a gate or prove reachability.

## 8. Risks and Required Controls

| Risk | Failure mode | Required control |
|---|---|---|
| Auth expiry | Cookie/session expires mid-run | Preflight and checkpoint; fail closed without regenerating |
| Secret leakage | Storage state or inline auth enters logs/artifacts | Isolated profile, redaction tests, secret scan, no auth-path serialization |
| Profile collision | Parallel agents mutate shared notebook context | Dedicated `NOTEBOOKLM_HOME`, full IDs, no `use` in automation |
| Version/RPC drift | Unofficial CLI changes verbs or JSON | Pinned release/hash, help snapshot, schema canary, kill switch |
| Stale helper | `add-source` instruction fails or masks current contract | Correct only after live `source add` qualification; negative test old verb |
| Duplicate upload | Retry creates duplicate NotebookLM sources | Stable export/idempotency key and observed source-ID receipt |
| Non-determinism | Generated answer/report differs across retries | Persist first task/result IDs; never regenerate to satisfy evidence gates |
| Citation laundering | NLM prose appears grounded but cannot resolve exactly | Candidate quarantine; refetch original; exact-passage verification |
| Rate limit/timeout | Long operation partially completes | Bounded retry, checkpoint, resumable receipt, no pipeline-wide failure |
| Sensitivity escape | Auto-sync uploads denied content | Manual selection first; no hooks; policy denial before transfer |
| Service/terms change | Automation becomes unsafe or unavailable | Disable live path independently; retain vendor-neutral packets |

## 9. Promotion Gates to a Tier-1 Qualification Contract

This spec may move from `shaping` to `ready` only when an owner accepts all gates below.
Passing them authorizes planning a qualification contract; it does not authorize sensitive
data, general rollout, or MCP exposure.

- **PG-1 — Account and profile:** named canary owner, public-data-only account decision,
  isolated profile location, retention rule, and secret-handling review are recorded.
- **PG-2 — Version pin:** exact release, package source, artifact hash, Python/runtime
  compatibility, and update/rollback procedure are recorded.
- **PG-3 — Command truth:** installed-binary help proves the create/list/auth/source-add/
  wait/query/export commands and notebook-ID flags. `source add` versus `add-source` is
  resolved by captured execution, not documentation alone.
- **PG-4 — Response contract:** redacted JSON fixtures cover success, auth failure,
  processing failure, timeout, rate limit, and schema drift.
- **PG-5 — Deterministic outbound receipt:** the same RF inputs and policy snapshot produce
  byte-identical export selections, hashes, and proposed receipts.
- **PG-6 — Inbound quarantine:** a NotebookLM report/source fixture imports through
  `external_research_handoff/v1` without creating a verified claim before source edition
  and exact-passage resolution.
- **PG-7 — Canary:** one authenticated public synthetic round trip is executed and its
  redacted evidence packet is reviewed; owner-held/private execution is not inferred.
- **PG-8 — Resume and rollback:** interrupted upload/query/import resumes without duplicate
  RF authority records, and disabling NotebookLM leaves RF's offline pipeline healthy.
- **PG-9 — Governance:** profile, sensitivity, review, secret-scan, telemetry-redaction,
  and destructive-cleanup decisions pass policy review.
- **PG-10 — Exact-tree review:** the Tier-1 contract names focused tests and receives the
  required completion-validator review on the exact candidate tree.

### Tier-1 contract boundary

The qualification contract should remain approximately 3–5 points and contain only:

- a version/auth/command preflight that performs no mutation;
- one public synthetic canary path with recorded receipts;
- offline fixtures for the observed command and response shapes;
- correction of `rf notebooklm sync` to the proven command form;
- documentation of disable, rollback, retention, and requalification triggers.

If qualification requires broad adapter/writeback redesign, background generation,
browser automation, sensitive profiles, auto-sync, new authoritative schemas, or more than
8 points, keep this design `shaping` and split the new work into separately reviewed plans.

## 10. Relationship to Initiative Workstreams

- The epic PRD owns the external-evidence authority boundary and keeps this workstream at
  shaping with no execution tier.
- The initiative meta-plan owns sequencing and requires the external-interchange contract
  before any NotebookLM promotion.
- `external-research-report-interchange` owns `external_research_handoff/v1`, import
  receipts, completeness, source/passage resolution, quarantine, and resumability.
- The Knowledge MCP may eventually expose read-only qualification status or sealed receipt
  resources. It must not make NotebookLM synthesis look like verified RF evidence.
- The Operator MCP must not expose create/upload/query/generate/delete operations until a
  separately governed mutation contract passes idempotency, confirmation, guard, audit,
  and human-review requirements. Tier-1 qualification does not grant that authority.

## 11. Open Questions

1. Which account and isolated profile may retain the public synthetic canary notebook?
2. Which package source and exact CLI release is acceptable to pin?
3. Does a live `source fulltext`/citation response allow unique exact-passage binding, or
   must RF refetch every original locator independently?
4. What stable export identifier prevents duplicate NotebookLM source creation when a
   transfer is retried after an uncertain response?
5. Which external IDs may be retained, and for how long, without creating a privacy or
   account-correlation risk?
6. Should manual UI transfer receipts require a second reviewer for `work_approved` data,
   or should the first qualification remain public/personal only?
7. What event invalidates qualification: any version change, response-schema change,
   auth-flow change, or only a failed canary?
8. Who may authorize canary cleanup, and which evidence must remain after deletion?

## 12. Success Behaviors

- An operator can inspect a sealed RF export set before any external transfer.
- A returned NotebookLM report imports as platform synthesis and assertion candidates,
  never as primary evidence or an automatically verified claim.
- Offline RF operation remains unchanged when the CLI is absent, auth expires, a rate
  limit occurs, or automation is disabled.
- The current `add-source`/`source add` mismatch is visible and fails closed until a pinned
  binary proves the contract.
- A canary record identifies the exact version, profile class, command shapes, external
  IDs, receipts, and limits without exposing secrets.
- MCP consumers cannot mutate NotebookLM or bypass the external-handoff quarantine through
  this shaping spec.

## 13. Evidence Log

- **2026-07-18:** Reconciled the legacy integration plan, current NotebookLM skill,
  integration client, operator sync helper, epic PRD, and initiative meta-plan.
- **2026-07-18:** Local `notebooklm` binary was absent; no version, auth, help, service,
  upload, generation, download, or round-trip canary was executed.
- **2026-07-18:** Confirmed the client/skill use `source add` while `rf notebooklm sync`
  prints the stale `add-source` form. Status remains `draft` / `shaping`.
