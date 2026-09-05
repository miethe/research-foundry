---
title: "External Research Report Interchange (ERI) v1 — Contract Freeze: Identity, Tiers, Dependencies, Acquisition Policy"
doc_type: architecture
status: proposed
schema_version: 1
created: 2026-07-26
updated: 2026-09-05
feature_slug: external-research-report-interchange
resolves: ["ERI-OQ-1", "ERI-OQ-2", "ERI-OQ-3", "ERI-OQ-4"]
findings_doc_ref: .claude/findings/external-research-report-interchange-findings.md
related_docs:
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/dev/architecture/assertion-ledger-contract.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/feature_contracts/features/intake-citation-adapters.md
  - docs/dev/architecture/carp-contract-freeze.md
  - .claude/findings/external-research-report-interchange-findings.md
  - .claude/findings/eri-p1-contract-audit-gpt56.md
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/assertion_registry.py
  - src/research_foundry/services/assertion_catalog.py
  - src/research_foundry/services/intake.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/services/sensitivity.py
  - src/research_foundry/services/search_router/router.py
  - src/research_foundry/services/search_router/safety.py
  - src/research_foundry/services/extractors/pdf_extractor.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/yamlio.py
owner: nick
---

# External Research Report Interchange (ERI) v1 — Contract Freeze

**Status:** `proposed`, not `frozen`. This document was drafted at Phase 1 (Contract Freeze) and
initially marked `frozen`; an adversarial audit (gpt-5.6-sol,
`.claude/findings/eri-p1-contract-audit-gpt56.md`, verdict CHANGES REQUIRED, 20 findings) found that
verdict premature on two independent grounds and this remediation pass fixes both:

1. **Governance-state mismatch (audit finding #18).** The parent implementation plan
   (`docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md`)
   is `status: draft`, all four of its own `ERI-OQ-*` entries are `status: open` in its own OQ table,
   and its `findings_doc_ref` was `null` at the time this document was first frozen — despite this
   document (and the sibling findings doc) already resolving those OQs and existing on disk. **This
   document's own frontmatter now sets `findings_doc_ref` and downgrades `status` to `proposed`.**
   Re-freezing requires, in addition to this remediation being reviewed: (a) the plan's own frontmatter
   `findings_doc_ref` pointing at `.claude/findings/external-research-report-interchange-findings.md`,
   and (b) the plan's own `ERI-OQ-*` table entries updated to reference this document's resolutions.
   Neither of those two edits is in this document's or this task's owned-file scope (Mode B —
   Contract Drafting, `docs/dev/architecture/external-research-handoff-contract.md` +
   `schemas/external_research_acquisition_policy.schema.yaml` +
   `schemas/external_research_import_receipt.schema.yaml` only) — they belong to whichever agent owns
   plan-frontmatter integration, exactly as flagged in the findings doc's "Notes for Finalization."
2. **20 substantive design gaps**, remediated section-by-section below. Every subsection below that
   changed as part of this remediation is tagged `(audit #N)` with the finding number(s) it closes.

Once both of the above are true, this document is again the exact tree `task-completion-validator` and
Karen re-review at the P1 contract milestone (plan "Reviewer and Closeout Contract"). Any *further*
material change after that re-approval again invalidates the verdict and reruns the same gate (plan P1
quality gate: "A material contract fix reruns task-completion-validator and Karen against the new
tree") — this remediation pass is itself exactly that rerun for the first (pre-audit) version.

Task ERI-1.1 (packet/source/candidate/receipt/checkpoint schema authoring, golden/negative fixtures)
is owned by a parallel agent under `schemas/`. This document freezes the *semantics* those schemas
must encode; it authors no schema file for the packet/handoff/sources/candidates/checkpoint schemas
and no `src/research_foundry/**/*.py` production code (Mode B — Contract Drafting), matching the
precedent set by `docs/dev/architecture/carp-contract-freeze.md` §Scope. This document *does* own
`schemas/external_research_acquisition_policy.schema.yaml` and
`schemas/external_research_import_receipt.schema.yaml` directly (both updated in this same
remediation pass, in lockstep with the prose below) — those two schemas encode this document's own
identity (§1) and acquisition-policy (§4) freezes closely enough that splitting authorship of the
semantics from authorship of the schema shape risked exactly the drift the audit found.

## Scope

This document covers ERI-1.2 (identity), ERI-1.3 (completeness tiers + quarantine vocabulary),
ERI-1.4 (compatibility/dependency map), and ERI-1.5 (hostile-data + acquisition policy). It does not
re-litigate ERI-1.1's packet layout (PRD §6.1) or the five producer profiles (PRD §6.6/Phase 3) —
those are frozen by the PRD and by the parallel schema-authoring task.

**Owned-file scope note.** Audit findings #7 and #8 (member-byte TOCTOU after hashing; concurrent
first-import serialization) are implementation-level findings against a Phase 2/4 build, not against
this contract's semantics — they are explicitly out of scope for this remediation pass (owned by a
parallel agent) and are not addressed below. Every other finding (#1–#6, #9–#20) is contract-level and
is remediated in the sections below.

---

## 1. Identity (ERI-1.2)

### 1.1 Transport boundary — frozen (resolves ERI-OQ-1)

v1 accepts **only a materialized directory of regular files**. No archives (`.zip`/`.tar`/etc.), no
remote transport (HTTP upload, S3, etc.), no symlinks, no special files (FIFO/socket/device/block).
This is not a temporary MVP simplification — the plan's Deferred Items table records archive/remote
transport containers as `ERI-DF-2`, deferred pending "accepted threat model and concrete transfer
requirement." Any future transport layer is a distinct, separately-scoped feature; it does not reopen
this identity contract by widening what "one packet" means.

**Existing precedent to mirror, not reinvent.** `AssertionRegistry._read_regular_file`
(`src/research_foundry/services/assertion_registry.py:274-340`) already implements exactly the
traversal-safety posture this boundary requires for RF's other immutable-artifact tree: an `openat`-style
directory-descriptor walk pinned to a root, `O_NOFOLLOW` on every path component, an `lstat`-before-open
symlink rejection, and an `fstat`-after-open device/inode check that closes the `lstat`→`open`
TOCTOU window (path substitution between check and open). ERI-2.1 ("Safe packet inspection", Phase 2,
not this document's scope) should mirror this exact pattern when walking a packet directory rather than
deriving a second traversal-safety implementation. This document freezes only that the *same regular-
file-only, no-symlink, no-special-file boundary* applies to packet inspection, and (new, §1.6 below)
that the SAME walk is the source for the safe counts used in a `blocked` receipt's rejected-attempt
identity — the implementation belongs to Phase 2.

### 1.2 `packet_digest` — frozen inputs (resolves ERI-OQ-2)

> `packet_digest` = SHA-256 over a canonically-sorted manifest of `(declared member relative path,
> member byte length, member SHA-256)`.

Concretely, for every **accepted** member (post structural validation — path-safety, declared-member,
byte/count-limit checks have already passed; see §2's policy ordering):

1. Build one manifest entry per member: `{"path": <POSIX-style relative path from the packet root>,
   "byte_length": <int>, "sha256": <hex digest of the raw member bytes>}`.
2. Sort entries by `path` ascending (byte-wise, not locale-aware).
3. Serialize the sorted list with the same canonical-JSON generator RF already uses for
   content-addressed identity elsewhere in the ledger — `sha256-canonical-json-v1`
   (UTF-8, `sort_keys=True`, compact `(",", ":")` separators; see
   `AssertionRegistry._canonical_digest`, `assertion_registry.py:45-47`, and the same convention name
   used by `docs/dev/architecture/assertion-ledger-contract.md` §"Identity and version rules" for
   `source_assertion.identity.fingerprint`). `packet_digest` is the SHA-256 hex digest of that
   serialization.

This is a binding default for ERI-1.1's schema/service authorship — it reuses RF's one existing
canonicalization convention rather than inventing a second one, satisfying the plan's "no duplicate
authority" quality gate at the identity-primitive level as well as the object level.

**Excluded from identity** (frozen, verbatim): mtime, ownership/mode, absolute paths, filesystem
attributes. Also excluded, per PRD §6.2 (consistent with the directory-only boundary in §1.1):
transport directory name, absolute location, traversal/directory-listing order, and archive metadata
(there is no archive format in v1, so this exclusion is a forward-compatibility statement, not an
active behavior).

**Inclusion rule, stated positively:** any byte change in an accepted member, any member
addition/removal, or any relative-path change (rename) produces a new `packet_digest`. There is no
"near enough" comparison and no content-similarity fallback.

**Never computable for a `blocked` receipt (audit #10).** `packet_digest` is defined only *over
accepted members*, i.e. only after structural validation (path-safety, declared-member, byte/count-
limit checks) has already passed. When any of those checks fails, there is no accepted-member set to
hash. `packet_digest` is `null` on a `blocked` receipt — see §1.3's two-branch `receipt_digest` formula
and §1.3a's rejected-attempt identity, not a zero/sentinel hash standing in for a manifest that was
never built.

### 1.3 `receipt_digest` — frozen inputs, two status-conditioned branches (resolves ERI-OQ-2, audit
#6, #9, #10, #20)

The single formula this document originally stated could not, in fact, cover a `blocked` receipt
(audit #10: `packet_digest` doesn't exist yet at that point) and was missing two inputs the audit
found load-bearing (#6: action/effect identity; #9: governance-policy version). `receipt_digest` is
now **one normative canonical-object definition with exactly two status-conditioned branches** — never
a third shape, never an ambiguous cardinality claim elsewhere in this document.

> **Branch A — `status` is `completed` or `completed_with_quarantine` (seven inputs).**
> `receipt_digest` = SHA-256 over `sha256-canonical-json-v1` of the sorted-key object
> `{"packet_digest", "workspace_id", "target_run_id" (or null), "policy_digest",
> "schema_major_versions", "action_manifest_digest", "governance_policy_digest"}`.
>
> **Branch B — `status` is `blocked` (six inputs).**
> `receipt_digest` = SHA-256 over `sha256-canonical-json-v1` of the sorted-key object
> `{"blocked": true, "workspace_id", "target_run_id" (or null), "policy_digest",
> "schema_major_versions", "governance_policy_digest", "block_reason",
> "attempt_structural_summary"}` (see §1.3a for `attempt_structural_summary`).
> `packet_digest` and `action_manifest_digest` are never inputs on this branch — using a zero/sentinel
> value in their place would falsely imply a manifest was hashed when none was.

Both branches use the same `sha256-canonical-json-v1` generator as §1.2 (sorted keys, compact
separators). `schema_major_versions` covers every schema `external_research_handoff/v1` composes —
handoff, sources, assertion_candidates, receipt, checkpoint, and the acquisition-policy schema.

`policy_digest` is a **frozen input, not previously named in PRD §6.2**, defined here: a canonical
digest (same generator) over the effective acquisition-policy configuration in force when staging
began — the scheme allowlist, canonicalization rules, transport architecture, forbidden-address
ranges, the versioned metadata deny-set (§4.2.4), the IPv6 transition-prefix policy (§4.2.4), the
redirect-hop cap, and any operator-configured overrides
(the `external_research_acquisition_policy.schema.yaml`-shaped configuration object). **Rationale**,
stated explicitly because it is not obvious from the PRD text alone: resolution outcomes (which hosts
acquire successfully, which quarantine) are a function of the acquisition policy in effect, not just
the packet bytes. Binding `policy_digest` into `receipt_digest` means (a) re-importing the *same*
packet under the *same* policy is a true replay (§1.5) and (b) re-importing the *same* packet after an
operator has legitimately changed the acquisition policy (e.g. widened an allowlist, or bumped
`metadata_deny_set_version`) computes a **distinct** `receipt_digest` and produces an independent new
receipt — never a silent reinterpretation of a previously-published immutable receipt under new rules,
and never a spurious "replay conflict" denial for what is, in fact, a different governed decision.

`governance_policy_digest` is a **new frozen input (audit #9)**, defined here in parallel to
`policy_digest`: a canonical digest (same generator) over the effective rights/sensitivity/workspace-
authorization governance ruleset in force at Step 0 of §2.4 — the coarse caller/workspace
authorization gate that runs *before* structural validation even begins (§2.4, new step). It is
present on *every* receipt, including `blocked` ones, because Step 0 always runs regardless of what
happens next. Its exact field list belongs to whichever module already computes rights/sensitivity/
workspace-authorization decisions (`services/governance.py`, `services/sensitivity.py`) — this
document freezes only that ONE canonical digest over that effective ruleset exists and is bound into
`receipt_digest`, mirroring `policy_digest`'s precedent exactly. **Rationale (closes audit #9's
"replay bypasses current authorization" attack, together with §1.6):** if governance/sensitivity
policy changes after a receipt was published, `governance_policy_digest` changes, so re-deriving the
identity for what would otherwise look like "the same import" computes a **distinct** `receipt_digest`
— a stale governance decision is never silently reused for a new import attempt. This does not by
itself stop a *revoked caller* from reading an *old, still-valid-under-its-own-recorded-policy*
receipt; §1.6 closes that separately by gating every receipt *read*, not just identity computation, on
live re-authorization.

`action_manifest_digest` is a **new frozen input on Branch A only (audit #6)** — see §1.3a for its
full formula. It is never present (null) on a `blocked` receipt because no actions exist to manifest.

`target_run_id or null` — a present `workspace_id` is always required (PRD §10 Assumptions: "A target
workspace is always explicit"); `target_run_id` is optional and its absence (`null`) is itself part of
the identity, per §1.4 below.

### 1.3a Action, action-manifest, and effect identity — frozen (resolves audit #6)

The plan promises action- and effect-level identity that the original contract never defined,
creating exactly the hazard the audit named: duplicated, swapped, or reordered effects could corrupt
resume reconciliation, and a software change could alter derived actions while the receipt's identity
looked unchanged. Three formulas, frozen together, close this:

**Canonical iteration order.** Before any of the formulas below run, every declared source/candidate
record across the packet is placed in one deterministic sequence: sorted by the POSIX-style relative
`member_path` of the manifest file that declares it (`sources.yaml`, `assertion_candidates.yaml`, …),
then by that record's position within its declared array in that file *as accepted by structural
validation* (not filesystem listing order, which §1.2 already excludes from identity).

**`record_digest`** — SHA-256 over `sha256-canonical-json-v1` of the record's own validated field set,
exactly as accepted (post safe-parse, §4.1b; no implicit type coercion is possible under that safe-
parse profile, so this is literally the parsed value).

**`action_id`** — SHA-256 hex over `sha256-canonical-json-v1` of
`{"packet_digest", "kind" ("source"|"candidate"), "member_path", "record_digest", "occurrence_index"}`,
where `occurrence_index` is the 0-based count of prior records (in canonical iteration order, within
the same `member_path`) sharing the same `record_digest`. This binds identity to *content* (path +
record bytes), not to raw array position — reordering two *distinct* records never reassigns their
`action_id`s, because each `action_id` travels with its own `record_digest`. `occurrence_index` exists
only to disambiguate exact byte-identical duplicate records deterministically; for the overwhelmingly
common non-duplicate case it is always `0` and adds no fragility. Rendered as `era_<hex>` on the
receipt schema's `actions[].action_id` field.

**Canonical action manifest** — `{"algorithm_version": "1", "actions": [{"action_id", "kind",
"member_path", "record_digest"}, ...]}`, the inner array sorted ascending by `action_id` (byte-wise on
the hex string). **`action_manifest_digest`** = SHA-256 over `sha256-canonical-json-v1` of that
object. Embedding `algorithm_version` inside the hashed object (not just alongside it) is what closes
the "software changes can alter the manifest while retaining the same receipt identity" gap: a future
importer that changes how records normalize into actions MUST bump `algorithm_version`, which changes
`action_manifest_digest`, which changes `receipt_digest` (§1.3, Branch A) — never a silent
reinterpretation of the same `packet_digest` under new normalization rules.

**`effect_digest`** (per action, already a required field on the receipt schema) — SHA-256 over
`sha256-canonical-json-v1` of `{"action_id", "outcome", "completeness_tier", "canonical_refs"}`, where
`canonical_refs` names the downstream canonical identifier(s) this action produced or reused (e.g.
`source_edition_id`, `passage_id`, a `source_assertion` reference) or is an empty object when none.
Hashing `action_id` as the first field of `effect_digest`'s own input is what "binds an effect to
exactly one action" — an effect digest computed for one action can never collide with, or be mistaken
for, another action's effect, because the action's own identity is baked into the effect's hash input.

§1.5's "true conflict" case (a presented `receipt_digest` that already has a persisted history on
disk, but re-derivation doesn't match) is exercised precisely by re-deriving `action_manifest_digest`
from the presented packet + `algorithm_version` and comparing it against the stored value — this is the
"deterministic action manifest" §1.5 already referred to by name before it had a formula.

### 1.4 Absent target run — frozen (resolves ERI-OQ-3)

A `null` `target_run_id` means **staging-only**: no run is created, no run-local projection is written,
and the terminal receipt is still truthful and complete for everything staging *can* determine.
Concretely this has one hard consequence that is not spelled out elsewhere in the plan/PRD and is
frozen here: **the `verified` completeness tier (§2) is categorically unreachable when
`target_run_id` is null.** RF's sole verification authority, `verify_report`
(`src/research_foundry/services/verification.py:779`), operates over a run's `report.md` and claim
ledger — it is run-scoped by construction, not workspace-scoped. There is no code path in this
codebase that can accept a claim relationship as "verified" without an existing run whose claim ledger
references it. A staging-only import can therefore terminate at `passage_resolved` for its
best-resolved candidates, but never at `verified`; the receipt must not imply otherwise (e.g. by
omitting the tier count rather than reporting it as zero). ERI-FR-9's "No automatic run creation in v1
default" is what makes this the normal, expected v1 outcome for a staging-only import, not an error
state.

### 1.5 Replay-conflict behavior — frozen

Two distinct cases, not to be conflated:

1. **True replay (idempotent).** Same `packet_digest` (or, for a `blocked` attempt, the same
   `attempt_structural_summary`/`block_reason` under Branch B) + same `workspace_id` + same
   `target_run_id` (including "both null") + same `policy_digest` + same `governance_policy_digest` +
   same schema major versions ⇒ same `receipt_digest` ⇒ the importer returns the **stored,
   byte-identical terminal receipt**. Zero new canonical effects, zero duplicate source cards/editions/
   passages/candidates. This is the AC ERI-2 / success-metric #1 behavior (PRD §4 Goals table) — and,
   per §1.6, is only reachable once the CURRENT caller re-passes Step 0 authorization; a revoked caller
   never reaches the replay-lookup step at all.
2. **Distinct identity (not a conflict).** A different packet (any accepted-member byte/path change),
   a different `workspace_id`, a different `target_run_id`, a different `policy_digest`, a different
   `governance_policy_digest`, a different `action_manifest_digest` (e.g. a normalization-algorithm
   upgrade), or a different schema major version each independently produces a **different
   `receipt_digest`** — this is simply a new, independent receipt. It is not merged with, does not
   overwrite, and asserts no relationship to any prior receipt for a different identity (an operator
   may note a manual "supersedes" relationship out of band; ERI does not infer one).
3. **True conflict (fail closed).** The only case that is actually rejected as "conflicting" is an
   **integrity** conflict: a request computes a `receipt_digest`/`receipt_id` that already has a
   persisted manifest/effect history on disk, but re-deriving the deterministic action manifest
   (§1.3a) from the presented inputs does not match what is stored. Because the identity inputs above
   are exactly the inputs the deterministic action manifest is derived from, this case should be
   structurally unreachable in normal operation — its only realistic causes are a tampered/corrupted
   on-disk receipt directory or an importer defect. It **must fail closed and never silently overwrite
   or merge histories** (PRD §6.2, verbatim: "the importer does not merge histories"). This is the
   scenario Phase 5's "Truncated, extra, duplicate, reordered, wrong-target, and semantically impossible
   receipt/checkpoint fixtures deny" quality-gate bullet exercises.

Dry-run (`--dry-run`) never mutates state, so none of the above three cases can be triggered by a
dry-run invocation; a dry-run always re-derives and reports the plan without touching stored receipts.
Dry-run still passes through Step 0/§1.6 authorization — it reveals nothing an unauthorized caller
couldn't otherwise learn from a mutating attempt.

### 1.6 Receipt-read authorization — frozen (resolves audit #9)

**Every receipt read is re-authorized before existence lookup, not only before content return.**
Concretely: any operation that could reveal whether a `receipt_digest`/identity tuple has a stored
receipt — a direct lookup by `receipt_id`, the replay-check performed at the start of a new import
attempt (§1.5 case 1), or an explicit "show me receipt X" read — first re-runs Step 0's coarse
caller/workspace authorization gate (§2.4) for the **current** calling identity against the
**current** effective governance policy. A caller who fails this re-check receives the exact same safe
generic denial (§4.3) as a caller asking about an identity that was never submitted — never a
distinguishable "exists but you can't see it" vs "doesn't exist" response, and never the stored
receipt's content.

This closes the attack the audit named directly: a **revoked** caller replaying the same packet/
workspace/target does not receive a stored receipt merely because one exists on disk under the old
identity — it is re-evaluated against **live** authorization first. Combined with §1.3's
`governance_policy_digest` binding (a policy change computes a genuinely new identity going forward),
this closes both halves of audit #9: stale-policy reuse for new decisions (§1.3) and stale-authorization
reads of old, still-correctly-computed receipts (this section).

#### 1.6a ERI-6.0 closure (2026-07-27) — implemented, not deferred

Phase 4 and Phase 5's completion notes recorded audit #9 as **still open on both halves** at the
time each shipped — `governance_policy_digest` was a fixed digest over an explicitly-labeled
"not implemented" placeholder object, and no reauthorization gate existed anywhere in
`ExternalResearchInterchange.stage()`. Phase 6 hardening (ERI-6.0) closes both halves for real,
reusing only `services/rbac_store.py` (RF's one existing durable caller-identity/membership
authority) — it introduces no second authorization store or caller-identity concept.

- **`governance_policy_digest` (§1.3)** is now a real digest over
  `{"governance_gate": "eri_step0_v1", "rbac_schema_version": rbac_store.RBAC_SCHEMA_VERSION,
  "canonical_roles": [...]}` — `external_research_interchange.compute_governance_policy_digest()`.
  It is workspace-independent (mirrors `policy_digest`'s own "config snapshot, not
  request-specific" shape) and genuinely versioned: a real RBAC schema migration or role-catalogue
  change computes a different digest for every subsequently-staged import, exercised directly by
  `test_governance_policy_digest_changes_with_rbac_schema_version` and end-to-end through `stage()`
  by `test_governance_policy_change_yields_a_different_receipt_identity`
  (`tests/unit/test_external_research_caller_authorization.py`).
- **Step 0 / §1.6 reauthorization** is implemented as `external_research_interchange.
  CallerContext` (an optional caller identity: `principal_id`, `workspace_id`, `principal_type`,
  an optional `token_id`) plus `authorize_caller(caller, workspace_id=..., paths=...)`, which
  `ExternalResearchInterchange.stage()` calls as its literal first statement — before the replay
  lookup (`_load_receipt`), before structural validation, before anything else. When a
  `CallerContext` is supplied, it performs a FRESH (never cached) lookup against
  `rbac_store.get_member_role`/`rbac_store.get_access_token` on every call — denying outright
  (`CallerNotAuthorizedError`, a non-receipt denial; no receipt of any kind, not even `blocked`, is
  produced) when the principal has no current workspace membership, or when a supplied token is
  revoked, expired, or bound to a different principal/workspace. `import_external_report`'s own
  separate pre-derivation `_load_receipt` pending-checkpoint check (a second receipt-existence
  read the original contract text had not accounted for as a distinct call site) is gated by the
  identical check at its own entry point, before it does anything else.
  `tests/unit/test_external_research_caller_authorization.py` exercises: a never-a-member caller
  denied before any file is written under the interchange root; an authorized member staging and
  replaying successfully; a caller whose membership is deleted between staging and a replay attempt
  being denied on the replay (the exact "revoked caller" scenario); and the same for a revoked
  access token.
- **Scope actually closed, stated precisely.** `caller=None` — the ONLY value the bare
  `rf intake external-report` CLI passes today — is single-operator-trust and behaves identically
  to every prior phase; **no CLI flag was added** to supply a `CallerContext` from the command
  line. This is a deliberate scoping decision, not an oversight: RF's own architecture
  (`api/auth/rbac.py`'s module docstring) explicitly classifies every CLI mutation entry point in
  this codebase — `rf ingest`, `rf writeback`, `rf catalog rebuild`, and now `rf intake
  external-report` alike — as single-operator-trust, with RBAC enforcement applied only at the
  HTTP router layer via `request.state.identity`. Adding a bare-CLI actor flag here, and only here,
  would have been architecturally inconsistent with that precedent, not a fix. The real gate is
  wired at the service-API layer (`stage()`/`import_external_report()`), which
  `phase-5-completion.md` already identified as "the intended service seam for a future Operator
  MCP tool" — exactly the surface a future authenticated (HTTP/MCP) caller would use, and exactly
  where a live `CallerContext` now has somewhere real to go.

#### 1.6b Round-2 remediation (2026-07-27) — `governance_policy_digest` formula extended, permission model made explicit, reauthorization hardened

A second adversarial audit (gpt-5.6-sol, `.claude/findings/eri-implementation-audit-round2-gpt56.md`,
verdict CHANGES REQUIRED) found ERI-6.0's closure above incomplete on two counts. Both are now
closed; this section states the resulting formula/behavior changes precisely so §1.3/§1.6 stay the
single source of truth for identity inputs.

- **`governance_policy_digest` formula, extended (round-2 finding #1).** §1.6a's formula hashed
  only `rbac_schema_version` and role NAMES — it omitted the actual ERI permission MAPPING (so a
  permission-matrix change with no RBAC schema bump would not move the digest) and omitted the
  per-import rights/sensitivity policy entirely (so importing once under a permissive policy and
  retrying under a denying one replayed the earlier permissive outcome). The canonical object
  hashed by `compute_governance_policy_digest()` is now:
  `{"governance_gate": "eri_step0_v1", "rbac_schema_version": rbac_store.RBAC_SCHEMA_VERSION,
  "canonical_roles": [...], "eri_role_permissions": {<role>: [<permission>, ...], ...},
  "authorization_policy": <canonical dict or null>}`. `eri_role_permissions` is the actual,
  explicit ERI permission matrix (see the next bullet), not just role names. `authorization_policy`
  is a canonical mapping of the effective per-import rights/sensitivity policy —
  `external_research_import.import_external_report` always resolves a CONCRETE effective policy
  (explicit or its own default) before computing this, so "omitted" and "explicitly-default" hash
  identically, while any genuinely different effective policy hashes differently. This remains
  workspace-independent and per-caller-independent, exactly as §1.3/§1.6a's own rationale for
  `policy_digest`/`governance_policy_digest` already establishes — only the RULESET's/policy's
  identity moves the digest, never a caller's own identity (that half stays the live
  reauthorization gate below, not this digest).
- **Membership is not permission (round-2 finding #2).** `authorize_caller` previously granted
  Step 0 to any current workspace member regardless of role — including a `viewer`, who holds zero
  permissions under this same principle elsewhere in the codebase (`api/auth/rbac.ROLE_PERMISSIONS`).
  ERI now defines its own explicit two-permission vocabulary,
  `external_research_interchange.ERI_SUBMIT_PERMISSION` / `ERI_READ_PERMISSION`, and an explicit
  role → permission-set matrix (`owner`/`admin`/`researcher`: both; `reviewer`: read only;
  `viewer`: neither) — mirroring `api/auth/rbac.py`'s own matrix shape without importing that
  HTTP-router-layer module into this governed service module. `authorize_caller(..., permission=)`
  denies unless the caller's CURRENT role grants the requested permission. A supplied
  `CallerContext.token_id`'s own `role` (the ceiling the token was issued at, independent of the
  principal's current membership role) is checked against the same matrix — a token can never
  exercise a permission it was not itself issued with, even if the underlying principal's
  membership role has since been raised. A `principal_type="service"` caller is authorized through
  its OWN `service_accounts` record (workspace- and `disabled_at`-checked) — never through the
  `memberships` table, which answers a meaningless (or, on an id collision, actively wrong)
  question for a service-account identity.
- **Reauthorization inside the lease (round-2 finding #3).** §1.6a's reauthorization ran once, at
  the top of `stage()`, before the replay lookup — but `stage()` can then wait (bounded, up to
  `_LEASE_MAX_WAIT_SECONDS`) to acquire the single-writer receipt-identity lease before that lookup
  actually runs, leaving a window in which a caller revoked during the wait would still be handed a
  stored receipt. `stage()` now reauthorizes a SECOND time immediately after entering the lease,
  right before `_load_receipt` (both the blocked-receipt and accepted-receipt branches).
  `import_external_report`'s own pending-checkpoint guard and its call into `stage()` now share ONE
  held lease (see the ERI-6.0 outbox/lease notes in `round2-remediation-a.md`), with the same
  in-lease reauthorization repeated there too — closing the identical staleness window at that
  call site.

Test evidence for all three: `tests/unit/test_external_research_caller_authorization.py`
(new round-2 tests) and `tests/unit/test_external_research_interchange.py`. Full mapping:
`.claude/progress/external-research-report-interchange/round2-remediation-a.md`.

---

## 2. Completeness tiers + quarantine vocabulary (ERI-1.3)

### 2.1 Computed completeness tiers (verbatim from PRD §6.3)

| Tier | Required evidence | Permitted downstream use |
|---|---|---|
| `locator_only` | Valid locator/source descriptor; no immutable rendition binding | Discovery or acquisition queue only |
| `source_resolved` | Governed acquisition bound to one immutable `source_edition_id` | Source context; not claim support |
| `passage_resolved` | Exact cited bytes uniquely bound to one `passage_id` in that edition | Candidate evidence for RF verification |
| `verified` | Existing RF verification accepts the claim relationship and RAL materialization records the exact assertion lineage | Existing governed claim/assertion use |

Tiers are **importer-computed**, per source and per assertion candidate; producer-declared completeness
in the packet is a **hint only** and can never set the computed value (P1 quality gate: "Producer-
declared completeness cannot set computed or verified state"). No tier is inferred from a skipped
predecessor: an unavailable source stays `locator_only` even if its packet-declared metadata looks
complete; an exact passage whose claim relationship fails verification stays `passage_resolved`, never
`verified`.

**Practical scoping note** (clarifying, not contradicting, the PRD's "per source and per assertion
candidate" framing): a bare `sources.yaml` record has no citation/quote of its own — passage binding is
driven by a *candidate's* quoted text/selector against a *source's* resolved edition. In practice a
source record's reachable ceiling absent any candidate that cites it is `source_resolved`;
`passage_resolved`/`verified` are reached through the candidate that references it. Both objects still
report one tier each from the same four-member vocabulary, exactly as PRD §6.3 specifies — this note
only explains why a source-only entry rarely if ever shows `passage_resolved` on its own record.

**Completeness tier remains caller-visible in full (audit #15 does not apply here).** §4.3/§4.6 remove
the *specific denial reason* from the ordinary caller-visible surface because a reason code can
differentiate facts about *other* resources/workspaces. `completeness_tier` is different in kind: it
reports an item's *own* positive-progress state, which the caller already knows they submitted and
needs in order to know what they may do with it (the table above). Suppressing it would break the
tier system's entire purpose without closing any oracle.

### 2.2 Terminal states — two layers, not to be conflated

**Per-item terminal action outcome** (source or candidate level): exactly one of —
- **resolved at tier X** — the item completed importer processing and sits at its computed tier
  (`locator_only` / `source_resolved` / `passage_resolved`; `verified` is reachable only through the
  explicit promotion seam, §2.4.1, and only when `target_run_id` is non-null, §1.4).
- **quarantined** — a terminal, safe, reason-coded non-promotion outcome (§2.3). Quarantine is itself
  terminal for that item within this import; it is not a queued-for-retry state (PRD §6.5: "quarantine
  is a terminal per-item outcome inside a successfully processed packet"). The specific reason code is
  recorded in the access-controlled audit record only (§4.6); the caller-visible receipt carries an
  opaque `audit_ref` in its place (audit #15).

**Per-packet (receipt) terminal status** — closed 3-member enum (PRD §6.2):
- `completed` — every declared action reached a terminal outcome and zero items are quarantined.
- `completed_with_quarantine` — every declared action reached a terminal outcome and at least one item
  is quarantined. This is a **normal, expected** outcome, not a partial failure — most real imports of
  externally-produced reports will land here.
- `blocked` — packet-level structural validation failed before any per-item action ran (malformed
  member manifest, unsafe path, unsupported schema major version, limit exceeded). A `blocked` receipt
  has an **empty** resolved/quarantined action set, because blocking happens strictly pre-effects
  (PRD §6.5: "Malformed packet structure can block the whole import before effects"), and it uses the
  §1.3 Branch B / §1.3a rejected-attempt identity rather than a `packet_digest`-keyed one (audit #10).

**`pending` is not a receipt state.** It exists only on the separate, mutable **checkpoint** artifact
(PRD §6.2: "A receipt manifest and per-action effect receipts are immutable. Checkpoint state is
separate and atomically replaceable"; §6.7: "Cancellation leaves a resumable `pending` checkpoint. It
never publishes a false terminal receipt."). Once a terminal receipt is published it is immutable and
takes one of exactly the three values above — never `pending`, and never re-derived from a later
checkpoint read.

### 2.3 Safe reason codes — closed vocabulary

| Family | Codes |
|---|---|
| packet | `required_member_missing`, `unsupported_schema_version`, `unsafe_member_path`, `member_digest_conflict`, `limit_exceeded` |
| source | `invalid_locator`, `source_unavailable`, `rights_metadata_missing`, `sensitivity_denied`, `source_drift`, `edition_binding_conflict` |
| citation | `citation_unresolved`, `citation_ambiguous`, `citation_mismatch`, `passage_binding_conflict` |
| candidate | `basis_incomplete`, `relation_invalid`, `verification_failed`, `cross_workspace_denied`, `target_run_not_found`, `promotion_invalid`, `promotion_io_failed`, `promotion_failed` |

23 codes, 4 families, closed set. A quarantined item carries **exactly one** reason code from this set
— never free text, never a vendor-supplied string, never more than one code per terminal outcome. This
remains true as an internal, access-controlled fact (§4.6): it is what makes the audit record safe to
aggregate without ambiguity. **What changed under audit #15: the packet family (which describes the
submitted packet's own structure back to its own submitter, not a cross-workspace fact) stays directly
visible as `block_reason` on a `blocked` receipt; the source/citation/candidate families (18 codes,
which CAN differentiate facts about other resources/workspaces — `cross_workspace_denied` is the
clearest example) are removed from the ordinary caller-visible per-action surface and replaced with an
opaque `audit_ref` (§4.3, §4.6, and the receipt schema's `actions[].audit_ref` field).**

#### Promotion failure diagnostics and consumer compatibility

The candidate vocabulary adds four codes to the original PRD §6.5 baseline:

| Code | Meaning and operator action |
|---|---|
| `target_run_not_found` | The target `--run` does not exist. Scaffold the intended run before a new import. |
| `promotion_invalid` | Source-card staging rejected invalid data. Check the staging inputs and schema. |
| `promotion_io_failed` | Source-card staging encountered a filesystem error. Check storage access and availability. |
| `promotion_failed` | A promotion adapter returned failure without a recognized classification. Inspect that adapter; this does not establish an evidence failure. |

These codes distinguish staging failures from `verification_failed`, which describes evidence that
could not verify. Unexpected programming exceptions from the default promotion adapter propagate;
they are not converted into opaque staging failures. Exception messages are not copied into reason
codes or caller-visible receipts.

For acceptance checks and reports, inspect the access-controlled
`receipts/<receipt_digest>/effects/*.yaml` records' `reason_code` values. The ordinary receipt keeps
only the opaque `audit_ref`; `counts.by_completeness_tier` counts completed tiers and cannot measure
failure reasons. Stored terminal effects remain immutable, so historical `verification_failed`
records are not reclassified by this change. A replay returns those stored records unchanged.

Consumer audit for this additive internal vocabulary change:

- `external_research_interchange.py` writes and replays effect reason strings; the resolver enforces
  membership in `CANDIDATE_REASON_CODES`. No effect schema enum or migration is required.
- `external_research_import_receipt.schema.yaml` excludes per-action reasons and reason counts. Its
  caller-visible packet `block_reason` enum is unchanged; only descriptive vocabulary counts change.
- `export_service.py`, `rf-run-export-schema.json`, and `frontend/runs-viewer/src` do not export or
  enumerate ERI candidate reasons. The viewer's assertion/rights reason strings are a separate surface.
- `test_external_research_schemas.py` tracks the vocabulary; the adversarial matrix must cover every
  internal reason when asserting that receipts do not disclose reason detail.
- The completed reused-edition/backfill plans and the 2026-08-02 AAR retain their historical evidence.
  Their M3 checks use per-action reasons and require an existing target run; new reports must count
  target and staging failures separately from evidence failures using the codes above.

### 2.4 Policy evaluation ordering — canonical sequence

Consolidating PRD §6.4's numbered steps with the NFR "Security and privacy" ordering requirement into
one authoritative sequence (later phases implement this; this document freezes the order, which is
itself part of the contract — reordering any of these steps is a material contract change). **Step 0
is new in this remediation (audit #9, #10):**

0. **Coarse caller/workspace authorization gate.** Runs before structural validation, using ONLY
   caller-supplied invocation parameters (`workspace_id`, `target_run_id` if present, and the caller's
   own identity/token) — never anything read from inside the untrusted packet, which has not been
   opened yet. Verifies the calling identity is authorized to submit (or, per §1.6, to *read*) for the
   target `workspace_id`/`target_run_id` under the CURRENT effective governance policy, and captures
   `governance_policy_digest` (§1.3) — this snapshot happens regardless of what follows, which is why
   `governance_policy_digest` is present on every receipt including `blocked` ones. Failure here ⇒ a
   **non-receipt denial** (mirrors §4.3's safe generic denial): no receipt of any kind, not even
   `blocked`, is created for a caller not authorized to interact with this workspace at all — this is
   what stops an unauthenticated/unauthorized caller from using detailed structural-validation error
   codes (step 1) as a probing oracle.
1. **Structural/packet validation** — schema conformance, required members present, safe paths, byte/
   count/attachment limits, known schema major versions, and safe parsing (§4.1b). Failure ⇒ `blocked`
   receipt (§1.3 Branch B, §1.3a rejected-attempt identity), zero per-item actions (§2.2).
2. **Per-item authorization gate** — workspace authorization, sensitivity, and rights checks, evaluated
   **before** any registry lookup, acquisition, or candidate-count-revealing response (NFR: "Workspace
   authorization and sensitivity checks precede registry lookup, source acquisition, candidate counts,
   and helpful error details"). This is the fine-grained, per-item counterpart to step 0's coarse,
   whole-import gate. Failure ⇒ quarantine with `sensitivity_denied` / `rights_metadata_missing`
   / `cross_workspace_denied` (recorded in the audit record, §4.6; the caller-visible action carries
   `audit_ref` only); no acquisition is attempted and no protected state is revealed.
3. **Existing-edition reuse check** — reuse an already-authorized exact edition when identity and
   source-card binding match (PRD §6.4 step 3); this never re-runs acquisition for content RF already
   holds.
4. **Hard acquisition gate** (§4.2, in full) — only entered when step 3 finds no reusable edition.
   Must pass canonicalization/scheme/host/every-DNS-answer/every-redirect-hop/connected-peer validation
   before any network effect. Failure ⇒ safe typed denial (§4.3), quarantine, **no fallback to a
   different transport** (§4.4).
5. **RFUP-owned extraction from policy-acquired bytes** — only after step 4 passes in full, and only
   over bytes the SAME actor that ran step 4 already acquired (§4.2.0, §4.2.9) — never a fresh fetch of
   the original URL (PRD §6.4 step 4, remediated per audit #1/#19).
6. **Persist or reuse the immutable edition** — via `AssertionRegistry.ingest()` (RAL; §3).
7. **Exact passage resolution** — via `AssertionRegistry.find_exact_passages()` /
   `resolve_passage()` (RAL; §3); zero/multiple/drift/conflict ⇒ quarantine, unique exact match ⇒
   `passage_resolved`.
8. **Explicit promotion seam** (§2.4.1) — stage the `passage_resolved` candidate for existing RF
   verification; only reachable when `target_run_id` is non-null (§1.4).

#### 2.4.1 Who holds `verified` authority

**Only the existing RF verifier/materializer** — `verify_report`
(`src/research_foundry/services/verification.py:779`) plus the existing assertion-materialization
pipeline named in the PRD's "Proven substrate" list (`assertion_materialization.py`, also named in AC
ERI-4's `target_surfaces`) — can assign `verified` and durable assertion references. This is never the
packet, never the importer, never a vendor-supplied "verified" or confidence label, never citation
presence alone, and never inferred from the mere existence of a `passage_resolved` candidate. ERI adds
a staging/promotion **seam** into this existing authority (ERI-4.4, a later phase); it adds no second
verification decision-maker. This directly satisfies AC ERI-4 ("Promotion requires exact existing
evidence authority") and the plan's explicit prohibition: "Platform synthesis, vendor IDs, a newer
edition, fuzzy similarity, or partial basis cannot bypass revalidation and remain candidate/quarantined."

---

## 3. Dependency map (ERI-1.4)

For each dependency, this section states what ERI needs, what already exists on this exact tree (file:
line), its readiness truth, and how ERI avoids minting a second authority for the same fact.

### 3.1 Research Provenance Continuity (RPC)

**Readiness: unexecuted.** See the formal finding at
`.claude/findings/external-research-report-interchange-findings.md` for the full detail; summary here
for the contract record. Of RPC's 7 schemas, **4 exist** on this tree —
`schemas/canonical_claim.schema.yaml`, `schemas/inference_record.schema.yaml`,
`schemas/search_request.schema.yaml`, `schemas/search_run.schema.yaml` — and **3 do not** —
`provenance_origin`, `research_run_envelope`, `search_activity_receipt` (verified: no matching files
under `schemas/` — confirmed by directory listing).

- ERI **may reference the 4 present schemas directly by existing ID** where a later phase's field
  genuinely needs to point at a canonical claim / inference record / search request / search run — it
  invents no new fields on any of them.
- ERI **must not** author, stub, or invent structure for the 3 absent schemas. Any field in ERI's own
  schemas (owned by the parallel ERI-1.1 task) that is conceptually "the RPC import/origin context" must
  be **optional and nullable in v1**, typed no more specifically than an opaque reference (e.g. a
  nullable string ID), carrying no invented field semantics for `provenance_origin` /
  `research_run_envelope` / `search_activity_receipt`. This mirrors the precedent already set by the
  sibling CARP contract freeze (`docs/dev/architecture/carp-contract-freeze.md` §4, "RPC seam") for the
  same unexecuted dependency.
- When RPC lands, the migration is a contained, additive rebase (rename/relocate ERI's own nullable
  provenance fields into the new RPC schema), not a redesign — the same shape of "normative
  substitution" CARP's §4.2 documents for its own fields.

### 3.2 RF Upstream Evidence Foundry (RFUP)

**Readiness: executed.** `docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md`
frontmatter reads `status: completed`, with 6 phases of progress/completion artifacts under
`.claude/progress/rf-upstream-evidence-foundry/` and a follow-on `rfup-external-routing` plan already
in progress (`.claude/progress/rfup-external-routing/`). Its substrate is not a separate `rfup_*`
module — it is folded into existing services per its own `files_affected` list: `errors.py`,
`cli_commands.py`, `services/verification.py`, `services/search_router/router.py`,
`services/source_cards.py`, `services/assertion_registry.py`.

Owner symbols ERI-4.2/4.3 (later phases) call into, verified on this tree:
- `resolve_exact_passage_mode` (`verification.py:567`) — the `verify.exact_passage` warn/strict mode
  RFUP added; governs claim-level exact-quote strictness, not ERI's own passage resolver (§3.3 below
  owns that).
- `ExtractionStatus`, `ingest_source` (`source_cards.py:37`, `:178`) — the tri-state
  `full_text`/`partial`/`locator_only` fidelity vocabulary and the source-card write path.

**Frozen v1 acquisition entry points (audit #1, #2, #19) — reconciling the plan's `_first_extraction_
provider` reference with AC ERI-6.** The original contract named `_first_extraction_provider`
(`search_router/router.py:477`) as an acquisition entry point ERI's step 5 (§2.4) calls; the audit
found this both (a) architecturally wrong post-#1 (§4.2.0's single-actor-owns-the-lifecycle
architecture means ERI's own policy-owned client performs the fetch, never a provider) and (b) in
direct conflict with AC ERI-6 ("no live provider dependency"), since `_first_extraction_provider`
selects among live, network-calling provider modules (`providers/{brave,exa,firecrawl,jina,github}.py`,
each performing its own independent `httpx` fetch this contract's SSRF gate cannot pin). This is now
resolved, not just flagged, as follows:

- **ERI's network acquisition in v1 never calls `run_search`, `_first_extraction_provider`, or any
  provider's `.extract()`/`.search()` method.** Those remain valid entry points for RF's general
  search-router discovery flows elsewhere in the codebase; they are permanently out of scope for ERI's
  own acquisition path, in v1 and until a future policy version proves an equivalent end-to-end
  pinned-address guarantee for a given provider (`transport_architecture.provider_delegated_fetch_
  allowed` is hard-pinned `false` in the acquisition-policy schema until then).
- **The one frozen v1 extraction entry point is `extract_pdf(bytes) -> PdfExtractionResult`**
  (`src/research_foundry/services/extractors/pdf_extractor.py:57`) — verified on this tree to perform
  **zero I/O**: it accepts only already-acquired bytes. This is exactly the shape §4.2.9 requires:
  ERI's own policy-owned client (§4.2.0) acquires the bytes; `extract_pdf` turns PDF bytes into text.
  `_download_pdf_bytes` (`router.py:465`, bare `urllib.request.urlopen`) is **not** reused — it performs
  its own unpinned fetch, which is exactly what §4.2.0 replaces.
- **For non-PDF (HTML/text) content, no existing byte-accepting extractor exists in RFUP today.** The
  only non-PDF extraction path on this tree is the provider chain (`_first_extraction_provider` +
  `.extract([url])`), which is out of scope per the bullet above. **Phase 4 must build a new,
  network-free byte-accepting text/markdown extractor** — structurally mirroring `extract_pdf`'s
  `(bytes) -> result` signature — rather than adapt the provider chain. This is recorded as an Open
  Item below; it is net-new work, not a reuse of existing RFUP substrate, and the plan/Phase 4 owner
  should not assume otherwise.

**Load-bearing finding (documented at length in the findings doc, summarized here): none of the
RFUP-owned network-touching code on this tree implements any SSRF-safe address/DNS/redirect/peer
policy today**, and (per the bullets above) none of it is reused for ERI's own acquisition regardless.
`_download_pdf_bytes` (`search_router/router.py:465-474`) calls bare `urllib.request.urlopen()` with
only a timeout; the provider modules call bare `httpx.get`/`httpx.post` with no address validation. A
repository-wide search for `ipaddress.`, `is_private`, `is_loopback`, `is_reserved`, `is_link_local`,
or `is_multicast` under `services/search_router/` returns zero matches. **ERI-1.5's hard acquisition
gate (§4.2) is therefore a net-new control from a blank slate** — it inherits nothing usable from
today's `_download_pdf_bytes`/provider `httpx` calls beyond the timeout value as a starting default.
ERI-4.2 (Phase 4, out of this document's scope) is the phase that builds it; this document freezes only
that the gate is mandatory and its exact policy shape (§4), and records that no such policy exists
anywhere in RF today for the phase that has to build it not to assume otherwise.

### 3.3 Reusable Assertion Ledger (RAL)

**Readiness: shipped.** `docs/dev/architecture/assertion-ledger-contract.md` P1 is frozen and live; the
rights-entity-model substrate is squash-merged to `main`. Owner: the `AssertionRegistry` class
(`assertion_registry.py:107`, `__init__(self, *, workspace_id, paths=None)` at line 112 —
**workspace-scoped, not run-scoped**).

| RAL capability | Symbol | ERI phase that calls it |
|---|---|---|
| Persist/reuse immutable edition + deterministic passages, rights/media-type gated | `AssertionRegistry.ingest()` — `assertion_registry.py:365` | ERI-4.2/4.3 (edition persistence) |
| Source-card binding verification | `AssertionRegistry.verify_source_card_binding()` — `:205`; `source_card_snapshot()` — `:156` | ERI-4.1/4.2 |
| Exact-passage lookup; **zero/multiple = ambiguity, never a newer-edition or similarity fallback** | `AssertionRegistry.find_exact_passages()` — `:479` | ERI-4.3 (exact resolver) |
| Drift detection against a bound passage | `AssertionRegistry.resolve_passage()` — `:468` | ERI-4.3 |

`find_exact_passages()`'s own docstring states the exact invariant ERI-4.3 must preserve verbatim:
"More than one result is intentionally an ambiguity. [The resolver] must abstain, not pick a newer
edition or a similar-looking passage." ERI adds no second edition/passage/source-assertion identity —
every one of those remains `AssertionRegistry`'s content-addressed authority (`sed_<sha256>` editions,
content-addressed passages per `docs/dev/architecture/assertion-ledger-contract.md`).

**Seam finding for P2/P4 (recorded here so it is not rediscovered mid-build, same spirit as CARP's
"Seams P2 must add"):** `source_cards.ingest_source()` (`source_cards.py:178`) is hard **run-scoped** —
it requires an existing `run_id`, writes under `runs/<run>/sources/`, and raises `NotFoundError` when
the run does not exist (`source_cards.py:216-218`). It is therefore **not directly usable** for a
staging-only import (`target_run_id` null, §1.4) — calling it would either force a run to exist (which
ERI-FR-9 forbids: "No automatic run creation in v1 default") or fail. `AssertionRegistry` itself has no
such dependency — its `ingest`/`resolve_passage`/`find_exact_passages` methods take no `run_id` and are
safe to call in staging-only mode. ERI-4.1/4.2 must therefore either build a packet-scoped source-card
equivalent that does not require a run, or resolve/persist directly through `AssertionRegistry` and
defer the run-scoped `source_cards.py` convenience wrapper to the case where `target_run_id` is
non-null. This document does not resolve which; it flags the exact fork point (`source_cards.py:178`'s
`run_id` requirement) for the phase that must decide.

### 3.4 Intake Citation Adapters

**Readiness: draft, unexecuted.** `docs/project_plans/feature_contracts/features/intake-citation-adapters.md`
frontmatter: `status: draft`, `files_affected: []`. Confirmed on this tree: no `CitationTuple`,
`OpenAIIntakeAdapter`, or `PerplexityIntakeAdapter` symbol exists anywhere under
`src/research_foundry/` (repository-wide grep, zero matches). The only existing dedup helper is
`search_router/dedupe.py`, which dedupes search-provider results — a different concern from the
citation-tuple `(url, date)` dedup this contract describes; it is not a substitute.

ERI's citation/candidate normalization (ERI-4.1, a later phase) **may adopt the same field shape**
this draft contract documents — `{span, source, relation, confidence}`, with `relation` aligned to the
`claim_ledger.sources[].relation` vocabulary — purely as a naming convention to avoid a future rename
if/when Intake Citation Adapters ships. It must not claim to call, import, or depend on any adapter or
dedup module from that contract, because none exists on this tree. The live substrate ERI's candidate
normalization does depend on is `adapters/base.py`'s `Adapter` protocol and `AdapterResult` dataclass
(fields `adapter`, `degraded`, `source_candidates`, `artifacts`, `notes`, `cost_usd`, `tokens` —
verified at `adapters/base.py`), which already states the trust rule ERI's Goal G2 restates: an
external tool's output becomes candidates, never authority. ERI is a second, packet-shaped intake path
sharing that same trust posture, not a competing one.

### 3.5 No duplicate authority — summary

ERI introduces exactly one new authority: **packet/receipt/checkpoint identity and per-item quarantine
bookkeeping** (§1, §2) — net-new schemas and a net-new service. It introduces zero new
edition/passage/source-assertion/extraction/citation-tuple/claim-ledger authority: those remain owned,
respectively, by `AssertionRegistry` (§3.3), the RFUP-folded extraction pipeline (§3.2 — narrowed to
`extract_pdf` plus a net-new non-PDF byte extractor, per audit #1/#2/#19), and
`verification.py`/`assertion_materialization.py` (§2.4.1). This satisfies the plan's P1 quality-gate
bullet verbatim: "No schema defines a second edition, passage, source assertion, extraction, or
citation-tuple authority."

---

## 4. Hostile-data + acquisition policy (ERI-1.5)

### 4.1 Inert-data rule (audit #11)

**Every field in every packet member, including namespaced vendor extensions, is untrusted data.**
Values may be stored and displayed through bounded, escaped data surfaces, but may **never** be
promoted into: a system/developer prompt, a tool or resource description, a route/control value, an
adapter/tool name, a command, a schema selector, a filesystem path, or an execution argument (PRD
§6.1, verbatim scope; this is the union of the task's shorter enumeration and the PRD's fuller one —
the fuller list is authoritative). A string that resembles an instruction override, a tool call, or a
policy override remains inert data regardless of how convincingly it is shaped.

**The prohibition is not limited to system/developer prompts — it covers every model-adjacent surface
(audit #11 — the original text named only system/developer prompts, leaving retrieval context, user/
assistant messages, and tool-capable execution context unaddressed).** Concretely, packet-derived
bytes are banned from:
- system and developer prompts (as originally stated);
- **any** model message role — user, assistant, or tool/function-result messages that will be read by
  a model in a subsequent turn;
- retrieval/RAG context assembled for a model call, however it is labeled (there is no "read-only
  context surface" carve-out — a model that reads a surface can be influenced by it regardless of the
  surface's intended read-only status);
- tool/resource descriptions, names, or metadata exposed to a tool-calling model;
- any execution context in which a subsequent step could interpret the content as an instruction,
  route, or capability grant (a tool-capable agent's working context, not only its system prompt).

The only permitted downstream destinations for packet-derived free text are (a) capability-free human
display, always escaped/sanitized per §4.6's channel matrix, and (b) capability-free automated
analysis that cannot itself take action or feed a subsequent model turn (e.g. a static classifier
whose output is itself only a safe, closed-vocabulary label — never re-emitted verbatim).

**Existing partial precedent, and why it is not sufficient alone.**
`scan_for_injection` (`search_router/safety.py:34-45`) already does regex-based, best-effort
prompt-injection **detection** on extracted content, flagging matches into a source card's
`trust.known_limitations`. That is useful defense-in-depth (and ERI's producer profiles should route
extracted vendor prose through it where applicable), but it is a **labeler, not a preventer** — a
string that doesn't match its conservative patterns is not thereby safe to interpolate anywhere. ERI's
requirement is the stronger, architectural one: injection-shaped packet strings must be **provably
inert by construction** — never string-interpolated into any of the forbidden targets above — verified
by the injection-shaped fixtures ERI-3.6/ERI-6.2 require across every member/profile/surface listed
above, not by pattern matching catching every case.

**`report.md` special case (binding, verbatim).** `report.md` bytes are `content_role:
platform_synthesis` and can **never** enter a source-card, claim, or assertion writer: never passed as
`content=` to `source_cards.ingest_source()`, never passed as `content` to `AssertionRegistry.ingest()`,
never used to construct a `claim_ledger` entry directly, and — per the broadened rule above — never
placed into any model message, retrieval context, or tool-capable execution surface either. Its only
legitimate downstream destinations are staged verbatim as a non-authoritative synthesis artifact and
the same capability-free human-display/analysis surfaces named above. This is Goal G2's hard boundary
(PRD: "Persist `report.md` as `platform_synthesis`; ... never infer verification from vendor labels or
citation presence") and the plan's explicit prohibition repeated at every phase gate that touches it
(P4: "`report.md` content cannot enter source-card, claim, or assertion writers").

### 4.1a Permitted narrow sinks — an explicit allowlist (resolves audit #17)

§4.1's universal prohibition ("never a route/control value... never a filesystem path... never a
schema selector") is not, and cannot be, literally absolute: two packet-declared fields necessarily
participate in routing/selection by the nature of what they are. The audit correctly identified this
as an unresolved contradiction, not a false alarm — the fix is to name the exceptions explicitly and
close every other sink, not to weaken the rule.

Exactly two fields have a permitted sink, and each sink is narrow, typed, and non-dynamic:

1. **A source/candidate record's `locator`.** Permitted sink: input to the §4.2 canonicalization-and-
   acquisition-policy pipeline (parsed by one fixed parser, evaluated by fixed policy code, never
   string-concatenated into a shell command, log line, or format string) **or**, for a packet-internal
   local asset, an opaque `attachment_id` key lookup into the packet's own pre-validated,
   already-hashed member table (§4.5, redesigned per audit #13). No other sink exists for `locator`. In
   particular, `locator` is **never** resolved as an arbitrary filesystem path string — that would be
   exactly the forbidden "field acting as a route/control value" case.
2. **A packet member's `schema_version`/`type` discriminator.** Permitted sink: an exact-match
   comparison against the schema registry's own closed, fixed enum of known schema names/versions, to
   select which JSON Schema validates the rest of that member. It is never interpolated into a dynamic
   import path, module name, or filesystem path — the comparison is a fixed lookup table, not a
   template.

**Both sinks share the same shape: the value is read, compared or parsed by fixed non-dynamic code,
and then discarded — it never becomes a *new* instruction, a route destination outside its one
designated pipeline, a shell/file/network argument beyond that one pipeline, or text re-emitted into a
model-adjacent surface without §4.6's redaction rule.** Any sink not on this list remains categorically
forbidden under §4.1's general rule; a future field claiming a third narrow sink requires a contract
amendment, not an implementer's judgment call.

### 4.1b Safe parsing — before schema validation runs (resolves audit #12)

Schema validation necessarily runs on an already-deserialized object; the original contract said
nothing about the deserialization step itself, leaving YAML/JSON parsing outside the inert-data
boundary entirely. This is a genuine gap on this exact tree, not a hypothetical: RF's existing
general-purpose YAML/JSON helper, `research_foundry.yamlio` (`src/research_foundry/yamlio.py`), uses
`yaml.safe_load` (`yamlio.py:45`) and bare `json.loads` (`yamlio.py:66`). Verified on this tree:
`yaml.safe_load` blocks arbitrary Python object construction, but PyYAML's `SafeLoader` still supports
merge keys (`<<:`) and unbounded alias/anchor expansion by default (a "billion laughs"-shaped resource-
exhaustion vector), and silently keeps the *last* value on a duplicate mapping key rather than
rejecting it. Stdlib `json.loads` accepts non-finite numeric literals (`NaN`, `Infinity`,
`-Infinity`) unless `parse_constant` is overridden, and silently keeps the last value on a duplicate
object member unless `object_pairs_hook` is supplied. None of these are `yamlio`'s fault for its actual
purpose (RF's own internally-authored, trusted artifacts) — but none of them are acceptable for parsing
an untrusted, adversarially-produced packet member.

**Frozen requirement (implementation belongs to Phase 2, ERI-2.1):** untrusted packet-member parsing
MUST use a hardened, primitive-only loader profile — named here `packet-safe-parse-v1` so later phases
have one name to implement against, not a reinvention per call site:

- **YAML:** the core/primitive schema only — mapping, sequence, string, int, float, bool, null. No
  custom or `!!python/*` tags (already true of `safe_load`), and additionally: merge keys (`<<:`)
  disabled entirely, duplicate mapping keys REJECTED (raise, never silently keep the last), and hard
  ceilings on alias/anchor expansion count, nesting depth, and scalar length.
- **JSON:** non-finite numeric literals REJECTED (`parse_constant` raises rather than returning a
  float), duplicate object members REJECTED (`object_pairs_hook` raises on a repeated key rather than
  keeping the last), and the same nesting-depth/scalar-length ceilings as the YAML profile.
- **Schema validation runs against the exact object `packet-safe-parse-v1` produces** — never a
  re-serialized, re-normalized, or otherwise independently re-derived copy — so what gets validated is
  provably what gets used downstream (closing the parser-differential class of risk the same way §4.2's
  single-parse rule does for URLs).

`yamlio.load_yaml`/`loads_yaml` and bare `json.loads` remain correct and unchanged for RF's own
internally-authored artifacts; they are explicitly **not** reused as-is for untrusted packet-member
parsing. This is Phase 2 implementation scope; this document freezes the requirement and names the
concrete gaps in the existing helper so Phase 2 does not assume `yamlio` is already sufficient.

### 4.2 Acquisition policy — full canonicalization/scheme/authority/IP/DNS/redirect/connected-peer gate

#### 4.2.0 Architecture: one actor owns the whole HTTP lifecycle (resolves audit #1, and grounds #2/#3)

**Normative architecture, stated once and referenced everywhere else in this section:** the policy
layer described in this section is not a pre-flight check that hands off to a separately-implemented
HTTP client. It **is** the HTTP client. One actor performs — as a single, integrated operation, over
one connection it opens and controls end to end — canonicalization (§4.2.2), scheme/address/DNS
validation (§4.2.3–§4.2.5), connection binding and connected-peer verification (§4.2.6), and redirect-
following with full re-validation at every hop (§4.2.7), and only then reads the response body.

**RFUP's extraction step (§4.2.9) is never handed the original URL.** It receives the bytes this same
actor already acquired, plus minimal validated response metadata (final status code, content-type,
declared length) — never a locator it could independently re-resolve, never a second connection to
open. This closes the exact gap the audit named: a "gate before RFUP" architecture cannot actually
constrain what RFUP's own `urllib`/`httpx` call does once invoked, because redirects and peer
verification only happen *inside* an HTTP transport, and a second, independently-opened connection can
race a different Happy-Eyeballs address, reuse an unverified pooled connection, or simply re-resolve
the hostname after the gate's decision was made. There is, under this architecture, no "second fetch"
for any of that to happen inside.

`acquisition_policy.schema.yaml`'s `transport_architecture` object encodes this: `single_actor_owns_
full_lifecycle: true` and `hands_off_acquired_bytes_only: true` are both hard-pinned, non-configurable
invariants.

#### 4.2.1 Direct transport only (resolves audit #2)

The single actor from §4.2.0 uses **direct transport with environment/system proxy configuration
(`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, PAC scripts) explicitly disabled.** A proxy or PAC-resolved
intermediary would itself become the "connected peer" §4.2.6 verifies — an intermediary that
independently resolves the real hostname (possibly to an internal address) defeats every guarantee in
this section, because the validator would be verifying the wrong peer entirely.

**Provider-delegated URL fetching is prohibited** for the same reason and to the same degree: a
provider (search/extraction API) that fetches a URL on RF's behalf exposes only the provider's own
public egress as the observable "connected peer," while the provider itself performs an independent,
unpinned resolution RF cannot validate. §3.2 above freezes which entry points this rules out in v1
(never `run_search`/`_first_extraction_provider`/any provider `.extract()`) and which one is unaffected
(`extract_pdf`, which performs no fetch at all). `transport_architecture.provider_delegated_fetch_
allowed` is hard-pinned `false`; it may only become `true` for a specific provider in a future policy
version that proves an equivalent end-to-end pinned-address guarantee for that provider — this document
does not attempt to define what "equivalent" would require, because no such provider has been evaluated.

#### 4.2.2 URL canonicalization — frozen, single parse (resolves audit #3)

Before any other check runs, the locator is parsed **exactly once**, by **one strict URI
implementation**, producing one canonical authority object that every subsequent step — including the
transport connection itself (§4.2.0) — consumes without re-parsing. Freezing this closes the class of
attack where a policy parser and an HTTP client silently disagree about what host a string names.
Concretely, frozen at the schema level (`acquisition_policy.schema.yaml`'s `canonicalization` object):

- **IDNA/punycode.** Non-ASCII hosts are normalized via IDNA/UTS-46 to their ASCII A-label form before
  evaluation; hosts IDNA marks disallowed or ambiguously mapped are rejected outright, not coerced.
- **Trailing dots.** Exactly one trailing root-label dot is stripped as canonicalization; more than one
  is rejected as ambiguous.
- **Userinfo.** Any userinfo component (anything before an unescaped `@` in the authority) is rejected
  outright — not only when it "looks like" credentials (strictly stronger than the original text's
  "embedded credentials" framing, since any userinfo, credential-shaped or not, can be used to disguise
  the real host).
- **Percent-encoded host.** A host requiring percent-decoding to interpret is rejected; hosts must
  already be canonical, unescaped text.
- **IPv6 zone IDs.** Rejected outright (e.g. `fe80::1%eth0`).
- **Ambiguous numeric hosts.** Decimal, octal, or hex single-integer IPv4 encodings, and any other
  non-canonical numeric host form, are rejected outright rather than "helpfully" normalized and
  accepted.
- **IP literals.** Canonicalized to one canonical `ipaddress`-shaped object before §4.2.4's forbidden-
  range check runs, so the range check never operates on a string that could still mean two different
  addresses.

#### 4.2.3 Scheme/authority allowlist

Only explicitly configured HTTP(S) acquisition is permitted. Reject unauthorized local paths,
`file:`/any non-HTTP scheme, and any authority ambiguity not already closed by §4.2.2's
canonicalization step.

#### 4.2.4 Forbidden-address policy — IPv4, IPv6, transition prefixes, and a versioned metadata deny-set (resolves audit #4, #5)

Reject loopback, private, reserved, link-local, multicast, unspecified, carrier-grade NAT,
benchmark/documentation ranges, and cloud-metadata destinations, plus numeric/encoded/obfuscated host
tricks already closed at parse time by §4.2.2. Two sub-policies are now frozen explicitly rather than
left as broad categories with implementation-defined boundaries:

**Versioned cloud-metadata deny-set (audit #5).** `acquisition_policy.schema.yaml`'s `metadata_deny_
set` is a hard-pinned, explicit list — not only the frequently-cited `169.254.169.254` — covering AWS
(`169.254.169.254`, and the IPv6 form `fd00:ec2::254`), GCP (`metadata.google.internal`,
`169.254.169.254`), Azure (`169.254.169.254`, `metadata.azure.com`, the wire-server alias
`169.254.169.253`), and Alibaba Cloud (`100.100.100.200`). `metadata_deny_set_version` and
`special_purpose_address_registry_version` are both frozen, versioned identifiers bound into
`policy_digest` (§1.3) — a future addition to this list, or an update to the underlying IANA
special-purpose-address registries, is a visible, versioned policy change (which computes a new
`policy_digest` and therefore a new `receipt_digest` for anything acquired under it) rather than a
silent behavior drift that leaves old receipts looking like they reflect current policy when they
don't.

**IPv6 transition/translation prefixes (audit #4).** A validator that inspects only the connected IPv6
peer can be fooled: NAT64/DNS64, 6to4, Teredo, and IPv4-mapped/compatible addresses translate to an
embedded IPv4 destination that may be loopback/private/link-local/metadata, invisible to a check that
stops at "is this IPv6 address globally routable." `acquisition_policy.schema.yaml`'s `ipv6_transition_
policy` freezes: a hard-pinned `well_known_prefixes` list (the NAT64 well-known prefix `64:ff9b::/96`
and its local-use variant `64:ff9b:1::/48`, 6to4 `2002::/16`, Teredo `2001::/32`, IPv4-mapped
`::ffff:0:0/96`, and the deprecated IPv4-compatible `::/96`); `decode_and_validate_embedded_ipv4: true`
(every address matching a transition prefix has its embedded IPv4 destination decoded and validated
against this same forbidden-address policy in full); and an additive-only `operator_configured_nat64_
prefixes` list for deployment-specific, locally-configured NAT64 prefixes a validator cannot know about
a priori (a resolver-specific prefix is, by definition, local network configuration) — additive only,
never able to narrow or remove the hard-pinned well-known set.

#### 4.2.5 DNS resolution, every answer validated

Resolve under a bounded policy and validate **every** returned answer — not just the first — against
§4.2.4's forbidden-address policy (both the direct-address rules and the IPv6 transition-prefix
decode-and-validate rule). Any single forbidden answer denies the whole locator; a mix of one public
and one private answer is a denial, not a "pick the public one" fallback.

#### 4.2.6 Connection binding and connected-peer verification

Bind the connection to the specific address validated in §4.2.5, then verify the address actually
connected to matches what was validated — this is what closes the DNS-rebinding window (an attacker's
resolver can return a public address at validation time and a private one moments later, or a resolver
cache can be poisoned between validation and connect). The explicit required sequence is: **resolve →
validate every answer → bind → verify the connected peer.** Skipping the post-connect verification step
(validating DNS answers but trusting whatever address the socket layer actually connects to) does not
satisfy this gate. Because §4.2.0 makes this same actor the one that subsequently reads the response
too, there is no window after this step where a second, independently-resolving actor could reintroduce
the exact race this step closes.

#### 4.2.7 Redirects

Cap redirect hops at the frozen default of **≤3** (configurable per the Limits below) and **re-run
§4.2.2–§4.2.6 in full at every hop** before following it — a redirect target is a new locator for
policy purposes, not an extension of trust from the hop that produced it. **A failed hop has no
fallback**: it terminates the whole acquisition attempt for that source/candidate with a quarantine
reason (§2.3, recorded in the audit record per §4.6); it never retries with a different transport,
never partially completes, and never silently truncates the redirect chain and proceeds with a
cached/prior response.

#### 4.2.8 Ordering relative to §2.4

This entire gate (§4.2.1–§4.2.7) runs only after §2.4 step 2 (per-item workspace authorization/
sensitivity/rights) has already passed and only after §2.4 step 3 (existing-edition reuse) has found
nothing reusable — an unauthorized item never reaches DNS resolution at all, and content RF already
governs never triggers a redundant network fetch. §2.4 step 0 (coarse caller/workspace authorization)
has, in turn, already passed before step 1 (structural validation) ever ran, so an unauthorized caller
never causes any network I/O of any kind, direct or structural-probing.

#### 4.2.9 Handoff to extraction — bytes, never a URL (resolves audit #1, #19)

Only after §4.2.0–§4.2.7 pass in full does RFUP's extraction step (§2.4 step 5) run — and it runs over
the bytes the §4.2.0 actor already acquired, never over the original locator. §3.2 above freezes the
exact v1 entry points this resolves to: `extract_pdf(bytes)` for PDF content (zero I/O, verified on
this tree), and a net-new, equally I/O-free byte-accepting extractor Phase 4 must build for non-PDF
content — never `run_search`/`_first_extraction_provider`/any provider's URL-fetching methods, which
would reintroduce exactly the independent-second-connection risk §4.2.0 exists to close.

#### 4.2.10 Local-asset carve-out

An explicitly authorized local asset enters through the redesigned governed local-ingest path in §4.5
(audit #13) — never by weakening this URL gate's scheme allowlist to also accept `file:`, and never by
resolving a packet-supplied string as a filesystem path (§4.1a). Local ingest and network acquisition
remain two categorically separate code paths.

### 4.3 Safe denial (resolves audit #15, scopes #16)

A denial from this gate, or from any quarantine outcome it produces, must leak **none** of: denied
IDs, resolved addresses, quoted/candidate/source text, item counts, or — newly frozen here — **the
specific reason code that applied**, to an ordinary caller. This extends the same "one denial shape,
zero candidate-derived fields" discipline RF already applies to catalog reads —
`AssertionCatalog.denied_payload()`/`AssertionCatalogDenied` (`assertion_catalog.py:38`, `:248`) is the
existing precedent for a safe, reason-coded, zero-leak denial response, and CARP's contract freeze
(`carp-contract-freeze.md` §2) already generalized it once for evidence-plan denials; ERI's acquisition
denials reuse the same discipline a third time rather than inventing a new shape.

**What changed under audit #15, and why the original design still leaked despite following that
discipline.** The original text said a denial "carries exactly one reason code from the closed
vocabulary" — true, but that specific code is itself the leak: an ordinary caller who can distinguish
`cross_workspace_denied` (the target exists, just not for you) from `source_unavailable` (nothing
exists anywhere) from `sensitivity_denied` learns a cross-resource, cross-workspace fact regardless of
never seeing an ID, address, or text. Receipt-level reason-code counts compound this at the aggregate
level: a differential analysis across two near-identical packet resubmissions can reconstruct which
specific item changed status and why.

**Frozen fix:** the ordinary caller-visible surface — the returned denial shape for a synchronous
acquisition failure, and every per-action entry on the caller-visible receipt (§2.2, `external_
research_import_receipt.schema.yaml`'s `actions[]`) — carries **zero** reason-code detail and **zero**
reason-differentiated counts. Concretely: `actions[].reason_code` does not exist on the receipt schema;
in its place, `actions[].audit_ref` is an opaque reference into the access-controlled audit record
(§4.6) that carries the real reason code. `counts.by_reason_code` does not exist either. What DOES
remain caller-visible (`completeness_tier` per item; `actions_total`/`completed`/`quarantined`/`by_
completeness_tier` in `counts`; `block_reason` on a `blocked` receipt) is deliberately retained because
each is either (a) the item's own positive-progress state, not a cross-resource fact (§2.1's note), (b)
trivially re-derivable by counting the already-visible `actions` array and therefore adds no new
leakage by staying as a convenience field, or (c) a description of the caller's own submitted packet
structure back to its own submitter (§2.3's note on `block_reason`), not a fact about another
workspace's resources.

**Timing-sensitive distinctions — scoped, not left contradictory (resolves audit #16).** See §4.3.1.

#### 4.3.1 Timing scope for v1 (resolves audit #16)

The original text called uniform-timing behavior both a hard requirement ("must not... leak... timing-
sensitive distinctions") and an "accepted residual risk" in the same breath — a genuine contradiction
the audit correctly flagged, not a stylistic issue. This is resolved by narrowing scope explicitly
rather than asserting an unenforceable universal guarantee:

- **Threat-model framing.** Every path this section governs is reached only after §2.4 step 0 (coarse
  caller/workspace authorization) and, for per-item denials, step 2 (per-item authorization) have
  already passed. The threat model of an *unauthenticated* network attacker freely timing arbitrary
  acquisition attempts against arbitrary hosts does not apply here — only an *already-authorized*
  caller, acting within their own workspace, can observe any of this timing at all. Combined with §4.3's
  removal of reason-code differentiation from that same caller's visible surface, the practical value of
  a pure timing side channel to that caller is already sharply reduced before any timing-specific
  mitigation is applied.
- **The one v1-mandatory guarantee.** Fresh acquisition (§2.4 step 4/5, a real network round trip) and
  stored-identity reuse (§1.5 case 1 replay, or §2.4 step 3 existing-edition reuse — both effectively
  instant) MUST be routed through the same configurable minimum-latency floor before a response is
  returned, so an authorized caller cannot use raw response latency to distinguish "this exact
  packet+workspace+policy combination is new" from "we have already processed this exact combination."
  This is the one timing differential judged both realistically closeable and worth guaranteeing for v1
  — it directly protects the replay/reuse identity guarantees §1.5 and §1.6 already promise.
- **Explicitly out of scope for v1, with rationale.** Finer-grained timing variance among genuinely
  fresh (non-replay) denials — an instant scheme rejection vs. a fast local forbidden-address check vs.
  a DNS-round-trip failure vs. an N-hop redirect-limit denial — is **not** closed in v1. Building
  uniform-release-bucket infrastructure, padding, and statistically-validated rate limiting sufficient
  to make all four indistinguishable is a substantial systems investment; given the already-narrowed
  threat model above (an authorized, in-workspace caller, with no reason-code differential to correlate
  timing against), the marginal security value does not justify that cost for v1. This is an accepted,
  explicitly-scoped residual risk, not an oversight — ERI-6.2's adversarial trust matrix must still
  measure and record it, and a dedicated future hardening phase should close it if real-world threat
  assessment later shows the residual risk is higher than assumed here.

### 4.4 No transport fallback

A failed policy check anywhere in §4.2, or a failed hop, **never** falls back to a different transport
or a weaker guarantee: never a raw socket bypassing the HTTP client's redirect handling, never a retry
over `file:`, never a fallback to a cached/stale prior resolution, never a partial/best-effort response
returned as if it were a success. This is the same invariant the plan's risk table names directly:
"SSRF or DNS/redirect rebinding ... never weaken to fallback transport."

### 4.5 Governed local ingest vs. network acquisition — separation (redesigned, resolves audit #13)

Two categorically separate paths, never merged — but the local-ingest path is redesigned from "classify
a packet-supplied string by inspecting its shape" (the original design) to "resolve only an opaque,
pre-validated reference; never re-parse an untrusted string as a filesystem path" (the audit's fix),
because the original design let an attacker-controlled locator become a filesystem path in the first
place: an absolute path or `../../secret` could read host data, and relocating the same packet could
make the same digest resolve a relative locator to different bytes.

- **Governed local ingest — packet-internal attachments.** A source/candidate record references a
  local asset **only** by an opaque `attachment_id` — a key, not a path — that resolves exclusively
  into the packet's own manifest-declared, already path-safety-checked, already-hashed accepted-member
  table (§1.1, §1.2). Resolution is a lookup into a table already built during structural validation
  (§2.4 step 1); it never re-parses a fresh path string taken from packet content at ingest time. This
  guarantees no directory traversal (already excluded by structural validation), no absolute paths
  (same), and byte-stability (the exact bytes already hashed into `packet_digest` are what gets read —
  no second filesystem access with a fresh string that could resolve differently if the packet were
  relocated).
- **Governed local ingest — out-of-packet assets.** An asset that is NOT one of the packet's own
  manifest-declared members is never auto-resolved from packet content, full stop. It requires a
  distinct, out-of-band **operator grant**: an explicit, human-issued authorization, stored and
  supplied entirely outside the untrusted packet (an operator CLI flag or local config — never a
  packet field), binding one canonical absolute path to one expected SHA-256 digest. The importer
  verifies the digest matches at open time before use, closing the "relocating the packet resolves the
  same digest to different bytes" attack for this case too, since the grant's digest, not the packet's
  content, is the check.
- **Network acquisition** — anything reached via the RFUP-folded HTTP(S) extraction path (§4.2). MUST
  pass the full §4.2 gate, no exceptions.

**Classification is structural, not string-sniffing (closes the residual §4.1a concern).** Whether a
given `locator` field is treated as a packet-internal `attachment_id`, an out-of-packet reference
requiring an operator grant, or a URL for §4.2's network gate is decided by **which pipeline receives
it** — not by inspecting the untrusted string's shape (e.g. "does it look like a path" or "does it look
like a URL") and not by any packet-supplied hint field (e.g. a producer-declared `locator_type:
"local"`). A producer-supplied hint deciding which validation path a locator takes would itself be
exactly the class of violation §4.1 forbids (an untrusted field acting as a route/control value),
applied to routing rather than to a prompt — this is why `acquisition_policy.schema.yaml`'s `local_
asset_carve_out.producer_supplied_locator_type_hint_ignored` is hard-pinned `true`.

### 4.6 Channel-by-channel taint/redaction matrix (new, resolves audit #14)

The original contract's "inert-data" and "safe denial" rules bounded what a hostile string could
*become* (a prompt, a route, a path) but said nothing about the many *output* channels a denial,
receipt, checkpoint, or CLI invocation writes to — logs, immutable effect records, metrics, traces,
provenance exports, and machine-readable CLI output can all carry newlines, ANSI/control-character
sequences, format-directive-shaped substrings, hostile IDs, or resolved addresses even when the
*immediate* denial DTO itself is safe. This is now frozen per channel:

| Channel | Packet-derived free text (locators, quoted passages, vendor extension values) | Reason codes / detail | IDs |
|---|---|---|---|
| CLI stdout/stderr (denial output) | Never | Never the specific 18-code source/citation/candidate vocabulary (§4.3); `block_reason` only | Safe generated IDs only (`receipt_id`, `action_id`, `packet_digest`) |
| Structured application logs | Never raw/interpolated; only as a labeled, escaped structured field if genuinely needed for operator debugging, written via structured logging (never string-concatenated into a log-line template) | Full closed vocabulary permitted (operator-facing, not caller-facing) | Safe generated IDs |
| Receipt / checkpoint (immutable effect records) | Never | `block_reason` (packet family) visible; source/citation/candidate reason codes never appear here — only via `audit_ref` (§4.3) | Safe generated IDs (`receipt_id`, `receipt_digest`, `action_id`, `effect_digest`) |
| Metrics / counters | Never (metric labels are a fixed, closed cardinality set — never a packet-derived value) | Aggregate counts only per §4.3's redaction rule (no `by_reason_code`) | N/A |
| Traces / spans | Never in span names/attributes; a span may reference a safe generated ID only | Never the specific code as a span attribute value | Safe generated IDs |
| Provenance exports | Only as an explicitly escaped, clearly-labeled "producer-supplied" field, never structurally merged with RF-authored provenance fields | `block_reason` only, same as receipts | Safe generated IDs |
| Access-controlled audit store | The one channel where full quarantine detail (specific reason code, per-`audit_ref` linkage) is permitted, gated by its own access control — this is where `audit_ref` (§4.3) resolves to detail | Full 23-code vocabulary and per-reason-code counts permitted | Safe generated IDs plus the `audit_ref` linkage itself |

**Cross-cutting rules that apply to every row above:** control characters (C0/C1) and ANSI/VT100
escape sequences appearing in packet-derived text are stripped or escaped before that text reaches ANY
channel in this table (including the audit store — "access-controlled" governs *who* can read it, not
whether hostile bytes are sanitized before write); IDs surfaced on any channel are always RF-generated
(content-addressed digests or the `erh_`/`era_` prefixed forms), never a producer-supplied identifier
threaded through unescaped; and no channel other than the access-controlled audit store ever receives
the specific 18-code source/citation/candidate reason-code vocabulary or a reason-code-keyed count.

**Open item, recorded here and in the closing table below:** the concrete audit-store artifact
`audit_ref` resolves against (storage shape, access-control mechanism, retention) is not yet defined —
this document freezes only that it must exist, must be access-controlled separately from the ordinary
receipt-read path (§1.6's reauthorization requirement applies to the audit store too, at minimum as
strictly as it applies to receipts), and must be the sole home for the specific reason-code vocabulary
and its counts. Naming and building it is Phase 4 (or a dedicated hardening sub-phase) scope.

---

## Open items carried to later phases (non-blocking, recorded here for traceability)

- **`policy_digest`'s exact byte-level serialization** (which fields of the acquisition-policy config,
  in what order) is bound by §1.3's rule (must be one of `receipt_digest`'s inputs on both branches,
  via `sha256-canonical-json-v1`) and now has a concrete field list to serialize
  (`schemas/external_research_acquisition_policy.schema.yaml`, updated in this remediation pass).
- ~~**`governance_policy_digest`'s exact byte-level serialization**~~ **Closed by ERI-6.0 (§1.6a).**
  `services/governance.py`/`services/sensitivity.py` turned out to have no caller-identity concept at
  all to serialize (`GuardContext` has no user/caller field); the real ruleset this codebase
  actually has is `services/rbac_store.py`'s schema version + canonical role catalogue, which is
  what `compute_governance_policy_digest()` now serializes. See §1.6a for the full disposition,
  including the explicit, deliberate scope boundary (bare-CLI callers stay single-operator-trust;
  the live reauthorization gate is wired at the service-API layer only).
- **The RAL run-scoping seam** (§3.3): whether P2/P4 build a packet-scoped source-card equivalent or
  call `AssertionRegistry` directly for staging-only imports is left to those phases; this document
  freezes only that `source_cards.ingest_source()`'s `run_id` requirement makes it unusable as-is for
  `target_run_id: null`.
- **The RFUP SSRF-policy gap** (§3.2): ERI-4.2 must build §4.2's gate from scratch; it inherits nothing
  usable from today's `_download_pdf_bytes`/provider `httpx` calls beyond a timeout.
- **The non-PDF byte-accepting extractor** (§3.2, §4.2.9, audit #19) does not exist anywhere in RFUP
  today and must be built net-new in Phase 4, structurally mirroring `extract_pdf(bytes)`'s signature —
  it is not a reuse of the existing provider chain, which performs its own unpinned fetch.
- **The `packet-safe-parse-v1` hardened loader profile** (§4.1b, audit #12) does not exist anywhere in
  RF today; `yamlio`'s existing `safe_load`/`json.loads` usage is insufficient for untrusted packet
  parsing as documented and must not be assumed reusable as-is.
- **The access-controlled audit store `audit_ref` resolves against** (§4.6, audit #14/#15) is not yet
  defined as a concrete artifact — this document freezes only that it must exist and what it must
  contain; naming and building it is later-phase scope.
- **The v1-mandatory replay/reuse timing floor** (§4.3.1, audit #16) is a net-new mechanism (a
  configurable minimum-latency gate applied uniformly to replay/reuse responses) that does not exist
  anywhere in RF today; the broader out-of-scope timing variance named in §4.3.1 is an explicitly
  accepted v1 residual risk, not a deferred requirement.
- **Metadata deny-set and special-purpose-address-registry currency** (§4.2.4, audit #5): the frozen v1
  lists (`metadata_deny_set_version: "v1-2026-07-26"`,
  `special_purpose_address_registry_version: "iana-special-purpose-2026-07-26"`) are a snapshot, not a
  live feed. An operator process for reviewing and versioning updates to these lists over time is not
  defined by this document and should be established before any provider ranges shift materially.
- **Plan-frontmatter reconciliation** (§Status header, audit #18) — the parent implementation plan's
  `findings_doc_ref`, `status`, and `ERI-OQ-*` table need updating to match this document's resolutions;
  out of this task's owned-file scope.

See `.claude/findings/external-research-report-interchange-findings.md` for the full narrative on the
RPC-absence and RFUP-SSRF-gap findings, and
`.claude/findings/eri-p1-contract-audit-gpt56.md` for the full adversarial audit this remediation
responds to.
