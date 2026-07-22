# RFUP scope brief — 4 still-needed upstream items for Evidence Foundry

**Context**: IntentTree work-area `RFUP` (`node_01KXRTYKKW9ECTF9MCBQ8JV1EB`) enumerates 7 `rf`
upstream enhancements required by the pediatric-anemia-site "Evidence Foundry" seam. RFUP-1..5,7 are
reportedly built; RFUP-6 (native discovery adapters) deferred. This brief scopes the FOUR items the
downstream project still needs: (1) pediatric extraction validator, (2) exact-passage hard-gate,
(3) Path-B parameterization, (4) native adapter.

Read entirely from the sibling repo `pediatric-anemia-site` (read-only exploration; nothing in that
repo was edited). All 7 RFUP items are external-to-`rf`, tracked only via IntentTree + `op story`
routing — none is an implementation task in `pediatric-anemia-site` itself, and none is yet an
implementation task in `research-foundry` either (this brief is the scoping step before that).

---

## 1. Pediatric extraction validator

**What `rf` must deliver**: A formal JSON Schema (or schema extension) for the `pediatric_cds`
evidence-card block — `source_status`, `study`, `applicability`, `laboratory`,
`implementable_statement`, `diagnostic_accuracy`, `safety`, `conflict`, `lifecycle` — replacing
today's `additionalProperties: true` permissiveness for this namespace with required-field/type
enforcement. Concretely: an `rf verify` check (or new dedicated check) that a `pediatric_cds` block is
present, complete, and internally consistent before a card/claim is treated as converter-eligible.

**Acceptance criteria / DoD** (from capability ledger, `02` §6.1, and DF-E1-03 design spec):
- Deliverable stated as "Validated applicability/lab/threshold/lifecycle fields."
- Effort: **M**. Owner: `rf`. Reuse/build: **Extend**.
- Promotion trigger (DF-E1-03): "RFUP routing yields an accepted upstream change" — i.e. this item
  stays deferred until `research-foundry` accepts and ships it, tracked in `rf`'s own CHANGELOG, not
  in `pediatric-anemia-site`'s tracker.

**Seam boundary**: The pediatric_cds *schema shape itself* (age partitions, lab/method/analyzer
fields, threshold portability, lifecycle/review-by) is content pediatric-anemia-site authors define
and own — `rf` only needs to validate structural completeness of whatever block is supplied, not
originate or interpret clinical semantics. FHIR mapping, rule DSL compilation, and signing all stay
downstream in the CDS converter (`tools/rf-bundle-to-kb-pack/`), which already performs this check
post hoc and is NOT part of this upstream ask.

**Maps to**: RFUP item 3 in the consolidated note ("Upstream exact-passage hard-gating") — bundled
together with item 2 below under one design spec, `docs/project_plans/design-specs/
upstream-rf-validators-pediatric.md` (DF-E1-03). Status per the note: **still-needed** (not satisfied
— explicitly named as one of the un-implemented 7; the *downstream* half of the mitigation exists in
the converter today, the *upstream* half does not).

**Distinctness from RFUP-2 (URL/PDF extraction adapter)**: Confirmed distinct. RFUP-2 ("governed
URL/PDF extraction adapter") addresses *source acquisition fidelity* — locator-only degradation when
`rf` core's source-card service has no bundled PDF text extractor (gap-register row "URL/PDF
extraction can degrade"). The pediatric extraction validator addresses *schema/content completeness*
of the `pediatric_cds` extension block on an already-ingested card — a structural validator, not a
text-extraction pipeline. They are two separate gap-register rows ("Generic extraction schema" vs.
"URL/PDF extraction can degrade") with different root causes and different fixes. Neither doc read
here explicitly names the clinical quote-content-fidelity failure mode from the user's own memory
(PMC stripping superscripts, e.g. ×10⁹/L → ×10/L) — that concern is closer to the exact-passage
hard-gate's "clinical passage precision" language (item 2) than to either the schema validator or the
PDF-extraction adapter, but none of the three items as scoped explicitly commits to catching
character-level transcription corruption; it's an open edge this brief flags but does not resolve.

---

## 2. Exact-passage hard-gate

**What `rf` must deliver**: An `rf verify` exit-code path (or new dedicated check) that hard-gates
`implementable_statement.assertion_kind: threshold` claims lacking an exact passage / locator /
selector — mirroring `02` §5.2's exit-code routing pattern so failure surfaces as a standard `rf
verify` non-zero exit rather than only being caught downstream. Today `rf verify` "warns on missing
locators" but does not hard-gate clinical passage precision.

**Acceptance criteria / DoD**:
- Deliverable: "Threshold claims fail without passage/selector."
- Effort: **M**. Owner: `rf`. Reuse/build: **Extend**.
- Gap-register statement: blocks "release-ready rules upstream of the converter," does NOT block a
  research-only bundle (i.e., low-stakes exploratory runs can still pass).
- Same promotion trigger as item 1 (RFUP routing accepted upstream) — both are covered by the single
  DF-E1-03 design spec.

**Seam boundary**: `rf` owns detecting *absence* of an exact passage/locator for a threshold claim.
It does NOT own: clinical judgment of whether a passage is *sufficient evidence* for a given rule,
threshold-value extraction into executable rule logic, portability classification
(`universal`/`local_lab_dependent`/`implementation_proposed`), or content-rights/licensing review of
the passage — all of those stay in the CDS converter and clinical review (`02` §4.10, §4.11, §5.3).

**Maps to**: RFUP item 3, same as above. Status: **still-needed**.

---

## 3. Path-B parameterization

**What `rf` (or the workflow it hosts) must deliver**: Parameterize `.claude/workflows/
rf-run-execute.js`'s RF binary path, repo root, TMP directory, and run-date/stamp as explicit
config/args instead of machine-specific hard-coded values; add run-date and path-injection tests;
preserve per-run search-query/screening-ledger records; keep the deterministic `rf` tail
(extract→claim-map→synthesize→verify) unchanged.

**Acceptance criteria / DoD** (ADR-0008, `proposed` status, options-considered §1):
- Refactor hard-coded RF/repo/TMP/date-stamp paths to args/config.
- Add run-date and path-injection tests.
- Rough sizing given in the ADR: **2-4 engineer-days**.
- Unblocks `DF-E1-02` (full CBC 12-angle live research operation) — this is the concrete downstream
  trigger; without it E1's scheduled/unattended surveillance cadence cannot run.
- Gap-register statement: does NOT block E0 (seeded fixture path); DOES block scheduled E1/E2 runs.

**Seam boundary**: This is explicitly an `rf`-adjacent orchestration script (`.claude/workflows/
rf-run-execute.js`), not a first-class `rf` CLI verb — ADR-0008 notes hardening it "does not reduce
`rf`'s own adapter debt." Anything CDS-specific (which modules to run, CBC 12-angle research-angle
content, converter invocation) stays in pediatric-anemia-site's own workflow layer; `rf`/upstream only
needs to accept parameterized inputs and preserve its deterministic tail's exit-code contract.

**Maps to**: RFUP item 1 ("Parameterize the Path-B workflow"). Status: **still-needed** — ADR-0008
recommends this as the E1 default (over installing a native adapter) but is itself only `proposed`,
not accepted; no implementation has started anywhere.

**Note on ADR-0008 recommendation**: The ADR recommends hardening Path-B FIRST and explicitly
deferring native-adapter installation (item 4 below) until Path-B has run the full CBC 12-angle
operation at least once and a *measured* gap exists against it. This creates a soft sequencing
dependency: item 3 is recommended to land before item 4, though ADR-0008 itself is not yet accepted so
this ordering is not binding.

---

## 4. Native adapter (install/eval)

**What `rf` must deliver**: Installation and value/security evaluation of at least one of the 6 native
swarm adapters (`claude_agent_sdk`, `gpt_researcher`, `paperqa2`, `opencode`, `litellm_router`,
`arc_council`) — currently 0/6 installed or evaluated. `rf swarm run` today would "degrade with
current adapter installation" and must not be presented as successful discovery until this exists.

**Acceptance criteria / DoD**:
- Gap-register mitigation: "install adapters only after value/security evaluation" — no such
  evaluation exists on file for any of the 6.
- ADR-0008 sizing for this path (option 2, NOT the recommended default): "Medium–Large... requires
  adapter provisioning/credentials, a security/value evaluation... new fixture/contract tests against
  a system this repo does not currently exercise at all... starts from zero." Explicitly higher-risk
  and higher-variance than Path-B hardening due to "adapter false completeness" risk (a degraded swarm
  returning too few/locator-only sources must not be presented as successful discovery, per gap
  register).
- Defer trigger (per ADR-0008 recommendation, not yet accepted): only after Path-B has run the full
  CBC 12-angle operation once and a measured gap against it exists — i.e., this item is explicitly
  gated behind item 3 succeeding first, not parallel work.

**Seam boundary**: Any installed adapter's discovery output still has to flow through `rf`'s existing
deterministic spine (extract→claim-map→synthesize→verify→council→bundle) unchanged — the seam
boundary is that `rf` owns adapter installation/evaluation/quality-gating; pediatric-anemia-site owns
nothing here except consuming whatever verified bundle results (same converter/FHIR/rule-DSL boundary
as the other three items).

**Maps to**: RFUP item 6 ("Native adapter install/eval"). Status: **still-needed** — reportedly
deferred per the task framing, consistent with all docs read (0/6 remains the stated current state;
no evaluation on file).

---

## Seam boundary (cross-cutting summary)

Across all 4 items, the governing invariant (`02` §1.3, §6.4, `rf-handoff/README.md` §7) is that `rf`
stays on the **evidence → verified-claim** side of the seam and must never absorb:
- FHIR/terminology emission or mapping.
- Rule DSL compilation, threshold-value extraction into executable logic, or any generative
  rule-writing.
- Signing, key custody, or KB release-registry mechanics.
- Clinical review/approval workflow, dual-clinician sign-off, or any conflation of `rf verify`/council
  approval with clinical release authority (`02` §5.3, §8.4 "Unclear role authority" risk).
- Patient-specific inference, autonomous diagnosis/dosing/treatment directives.
- A second evidence crawler/source-card database (that stays a `pediatric-anemia-site` non-goal too,
  per `02` §6.4 — not an `rf` concern either way).

`rf`'s job for all 4 items is narrowly: validate/hard-gate what it already carries (items 1-2),
parameterize its existing live discovery orchestration for unattended scheduling (item 3), and
install/evaluate discovery adapters behind its own deterministic tail (item 4) — nothing about
clinical semantics, signing, or release governance crosses the seam in either direction.

## Source docs read (paths, all in `pediatric-anemia-site`)

- `.claude/worknotes/evidence-foundry-buildout/rfup-external-routing-note.md` (full read — the
  authoritative 7-item enumeration + disposition).
- `docs/project_plans/expansion/rf-handoff/README.md` §6 ("Not rf runs — the rf project enhancement
  handoff (RFUP)"), plus skim of §1-5, §7 for seam/governance framing.
- `docs/project_plans/expansion/02-evidence-foundry-on-research-foundry.md` §3.6 (pediatric_cds
  evidence-card extension shape), §3.7 (converter-eligibility field table), §6.1 (capability ledger),
  §6.2 (gap register), §6.4 (what will not be built), §8.3 (platform risks), §8.4 (operational/
  governance risks), §8.5 (recommended pre-E1 ADRs).
- `docs/project_plans/design-specs/upstream-rf-validators-pediatric.md` (DF-E1-03 — full read; covers
  items 1 and 2 jointly).
- `docs/adr/0008-pathb-hardening-vs-native-adapter.md` (full read — covers items 3 and 4 jointly, the
  sequencing decision between them).
- `docs/project_plans/implementation_plans/infrastructure/evidence-foundry-buildout-v1.md` (Deferred
  Items Triage Table rows `DF-E1-02`, `DF-E1-03`, `DF-EXT-01` — grep-targeted, not full read).

## Risk-level signals (auth/secrets/migrations/data-deletion/network egress)

- **Network egress**: item 4 (native adapter install/eval) is the only item with a live network-egress
  concern — installing adapters like `gpt_researcher`/`paperqa2`/`opencode` implies outbound web
  discovery traffic; item 3 (Path-B) already performs live web discovery today (existing, not new,
  egress) and just needs path/config parameterization, not new network scope.
- **Secrets/credentials**: item 4 explicitly needs "adapter provisioning/credentials" per ADR-0008 —
  the only item with a stated credentials dependency among the four.
- **No auth, payments, migrations, or data-deletion signals** in any of the 4 items — none touches
  user auth, billing, DB schema migrations, or destructive data operations. All 4 are additive
  validator/config/adapter changes to `rf`'s own pipeline.
- **Security/value evaluation gate**: item 4 is explicitly gated on an undone "value/security
  evaluation" before installation is even authorized — this is a governance gate, not a technical risk
  per se, but it means item 4 cannot start with implementation directly; an evaluation step precedes it.
