---
schema_version: 2
doc_type: spike
leg: risk
feature_slug: claim-term-indexing
status: complete
confidence: 0.78
created: 2026-07-23
---

# Risk Leg — Claim Term Indexing

## Risk Register

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Content-addressed `source_assertion` ID drift if term/usage fields leak into identity hashing | High | Low | `SOURCE_ASSERTION_MATERIAL_FIELDS` is a fixed 5-tuple (`assertion_identity.py:16-21`: `source_edition_id, passage_id, assertion_text_sha256, qualifiers, qualifier_extensions`) that excludes any term field. Identity is safe **iff** term/usage data is added as a field outside this tuple or lives in a side-index file. Add a regression test asserting `source_assertion_fingerprint()` output is unchanged when a `terms`/`usage_role` key is injected into the instance. |
| `canonical_claim.schema.yaml` is schema-locked (`additionalProperties: false`, `schemas/canonical_claim.schema.yaml:6,10-13`) | Medium | High (if index extends past run-local claims to the durable ledger) | Requires an explicit schema-version bump + `backend-architect` review, mirroring the additive-optional-field precedent already used for `run.json` 1.0→1.6 (`docs/dev/architecture/rf-run-export-schema.json:5`). Run-local `claim_ledger.schema.yaml` (`additionalProperties: true`, full file) has no such lock — cheaper first target. |
| Catalog-layer sensitivity granularity mismatch: term index riding as a flat pre-computed field would bypass per-point redaction | Medium-High | Medium | `catalog_service.py` captures payload once at `client_sensitive` (max-permissive) and redacts per-`evidence_point` at read time via `_redact_evidence_points()` (`catalog_service.py:1215-1234`, keyed on `point.get("sensitivity_rank")`). The flat `search_text` column (`catalog_service.py:541-563`) is pre-computed once from title/summary and is **not** re-filtered per point at read time — it is an existing precedent for this exact leak class. A term index must be derived per-sensitivity-tier (or computed from the post-redaction point set at read time), not folded into a single flat blob like `search_text`. |
| `rf verify` gate flipping a verified bundle's `verification_status` on reindex/backfill | Low | Low | `verify_report`'s checks (`verification.py:993-1160`: `exact_passage_present`, `quote_fidelity`, `material_claims_must_be_mapped`) read only `text`, `sources`, `materiality`, `claim_type`, `status` — a new additive field is not consumed. **Not empirically proven** — no run data was present in this worktree to execute a real before/after `rf verify` diff (see Blast-Radius Map). Recommend a fixture-based CI smoke test before ship. |
| `no_agent_cleared_rights_value` guard collision | Low | Low | The guard (`governance.py:483-501`) is scoped to 4 named rights-clearance fields (`_RIGHTS_GOVERNED_FIELDS`) checked against `CLEARED_*`/`counsel_approved`/`attested` values — unrelated to a `terms`/`usage_role` field by construction. Real risk is semantic drift, not a literal guard hit: see Additional Deal-Killers below. |
| Reproducibility of a model/embedding-derived `usage_role` | High if embedding-based | Design-dependent (tech leg) | A lexicon/rule-based (keyword-window / regex) usage-role classifier is trivially deterministic. An embedding/classifier-based one is a function of model version+weights and is **not** reproducible across model updates unless pinned and version-stamped (own `usage_role_model_version`, analogous to `schema_version`). Cross-ref tech leg for the chosen mechanism. |
| Migration/backfill of existing verified bundles | Low-Medium | Medium | `services/rights_backfill.py` is a directly reusable pattern: idempotent, additive-only, non-clobbering, dry-run supported (`rights_backfill.py:1-25`). `claim_ledger.schema.yaml`'s open `additionalProperties: true` makes an analogous term-index backfill a pure additive write with zero schema risk at that layer. **Cannot be validated end-to-end in this worktree** — see Blast-Radius Map. |
| Run-export contract (`run.json`) schema-version bump if term index is surfaced to the runs-viewer | Low | Medium | Established precedent: `rf-run-export-schema.json:5` documents 6 additive version bumps (1.0→1.6), each adding optional/nullable fields, each requiring `backend-architect` re-review (frontmatter `reviewed_by`). Would become 1.7 — process is proven, not novel. |

## Deal-Killer Assessment

Charter deal-killer: *"the index... would require a model call on the read/render path, OR would let agent-writable paths mint authority-bearing annotations that alter claim verification status."*

**Not triggered, on current (static) evidence — with one caveat.**

1. **Read-path model calls**: term extraction against a fixed vocabulary is deterministic string/regex matching — trivially write-time-computable, zero model calls. The vulnerable half is `usage_role`; if it is model/embedding-derived, the charter's wording only forbids computing it **on the read path**. A model call made once at write/index time, cached as derived data, does **not** literally trigger this clause — but it does trigger the separate reproducibility risk above, which the charter's own risk-leg question conflates with the deal-killer. These are related but distinct: recommend treating reproducibility as a **conditional-go gate** (name the usage-role mechanism), not a re-statement of the deal-killer.
2. **Authority-bearing writes altering verification status**: no code path found where a `terms`/`usage_role` field participates in `verify_report`'s checks or in the `no_agent_cleared_rights_value` guard's 4 named fields. Confirmed absent by reading `verification.py` and `governance.py`; **not** empirically executed against a live verified bundle (none present in this worktree — see below), so confidence on this half is code-inspection-level, not test-level.

## Blast-Radius Map

- `schemas/claim_ledger.schema.yaml` — safe additive target (open schema).
- `schemas/canonical_claim.schema.yaml`, `src/research_foundry/assertion_identity.py` — locked/content-addressed; term data must stay outside `SOURCE_ASSERTION_MATERIAL_FIELDS` and outside the closed `canonical_claim` property set without a version bump.
- `src/research_foundry/services/verification.py` (`rf verify`) — inspected, not exercised; needs a fixture regression test.
- `src/research_foundry/services/catalog_service.py`, `src/research_foundry/api/routers/catalog.py`, `reports.py` — sensitivity-threshold read paths; term index must respect the same per-point redaction granularity as `_redact_evidence_points`.
- `src/research_foundry/services/governance.py` — confirm no reuse of `_RIGHTS_GOVERNED_FIELDS` vocabulary for usage-role labels.
- `docs/dev/architecture/rf-run-export-schema.json/.md` — would need a 1.7 bump if surfaced to the runs-viewer.
- `services/rights_backfill.py` — reusable backfill pattern to model the term-index backfill script on.
- **Data-plane absence (operational blast radius)**: `scripts/rf-data:1-24` documents that run data (`runs/`, `ccdash/`, etc.) is tracked by a **separate private repo** via a dual git-dir (`$REPO/.git-data` → `github.com/miethe/research-foundry-data`). Confirmed in this worktree: no `.git-data` directory exists, and `runs/` contains only `.gitkeep`. **No pediatric-CDS bundles were available to inspect or test against in this exploration** — every claim above about `rf verify` idempotency and backfill safety is inferred from source, not proven against real data. Whoever executes the backfill must do so on a host with `.git-data` bootstrapped, and must remember the `-f` flag past `.gitignore` (`scripts/rf-data:16-18`).

## Additional Deal-Killers (Not in Charter)

- **Namespace/semantic collision with `pediatric_cds` schema-validated blocks** (per project CLAUDE.md "Important Notes": these blocks are hard-gated and threshold/clinical claims default to strict exact-passage mode). A `usage_role: threshold` annotation sitting next to a real `pediatric_cds` threshold assertion is a readability/audit hazard even if it is technically inert to `verify_report` — a downstream consumer (report writer, CCDash) could mistake a derived usage-role label for a clinically-attested threshold. Not a deal-killer by the charter's literal wording, but recommend a naming/namespace convention (e.g. `_term_index.usage_role`, never bare `usage_role`) to keep it unambiguously non-authoritative — same posture as the rights-summary mirror pattern ("denormalized, non-authoritative", `docs/dev/architecture/adr-rights-entity-model.md`).
- **Vocabulary versioning is itself an unaddressed reproducibility axis**: even a purely deterministic term matcher is only reproducible if the vocabulary list itself is versioned (a vocabulary edit changes historical index output silently). No existing precedent found for a "vocabulary_version" stamp; would need one alongside any `usage_role_model_version`.

## Confidence Rationale

0.68 at time of writing. High-confidence code-level findings (content-addressing safety, catalog redaction granularity, guard-rule scope, schema-lock status, backfill-pattern precedent) are all grounded in specific cited files/lines. Confidence was capped below 0.7 because no live run/claim data was available in this worktree to empirically execute `rf verify` before/after a synthetic term-index write. **Superseded by the Empirical Addendum below** (0.78) — the previously-untested half of the risk register (verify-gate idempotency) has now been executed against a real pediatric-CDS run and shows no status flip.

## Empirical Addendum (verify-gate idempotency)

**Follow-up executed 2026-07-23**, against real run data on the host filesystem
(`/Users/miethe/dev/homelab/development/research-foundry/runs/`, outside this worktree/repo). This
closes the empirical gap flagged above for the `rf verify` idempotency risk. All work happened on a
throwaway copy under `/tmp/cti-verify-test/`; the real data plane was never modified (verified by
inspecting the copy operations only — no writes issued against the source tree).

**Run selected**: `rf_run_20260717_rf_cbc_001_pediatric_cds_establish` (pediatric-CDS run, 87 claims in
`claims/claim_ledger.yaml`, existing `reviews/verification.yaml` and `reports/report_draft.md`; chosen
over 3 sibling pediatric-CDS candidates that were structurally identical, this one selected arbitrarily
as first-listed).

**Workspace setup** (`/tmp/cti-verify-test/`, minimal scaffold `rf verify` needs per
`paths.find_workspace_root()` + `FoundryConfig` fallback behavior):

```bash
mkdir -p /tmp/cti-verify-test/runs
cp /Users/miethe/dev/homelab/development/research-foundry/foundry.yaml /tmp/cti-verify-test/foundry.yaml
cp -R /Users/miethe/dev/homelab/development/research-foundry/config /tmp/cti-verify-test/config
cp -R /Users/miethe/dev/homelab/development/research-foundry/runs/rf_run_20260717_rf_cbc_001_pediatric_cds_establish \
      /tmp/cti-verify-test/runs/rf_run_20260717_rf_cbc_001_pediatric_cds_establish
```

**BEFORE** — verify against the unmodified copy:

```bash
cd /tmp/cti-verify-test
/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/rf verify \
  rf_run_20260717_rf_cbc_001_pediatric_cds_establish
```

Result: `exit_code=0`, `✓ verification passed`. All 17 checks `pass` except
`release_gate_judgment_basis_assessed` = `skip` (expected — no `evidence_judgment_bases` supplied to a
bare `verify` call). Ledger `verification_status: passed`. Snapshot saved
(`BEFORE.stdout.txt`, `BEFORE_verification.yaml`, `BEFORE_claim_ledger.yaml`).

**Injection** — additive `_term_index` key added to all 87 claims via a `yaml.safe_load` /
`yaml.safe_dump` round-trip (preserves existing structure, validated the round-trip re-parses cleanly
before re-running verify):

```yaml
_term_index:
  terms: [CBC, ferritin]
  usage_roles: {CBC: finding}
  vocabulary_version: test-0
```

**AFTER** — re-run the identical command against the mutated ledger:

```bash
cd /tmp/cti-verify-test
/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/rf verify \
  rf_run_20260717_rf_cbc_001_pediatric_cds_establish
```

Result: `exit_code=0`, `✓ verification passed`. Identical 17-row check table (same statuses, same
severities, same `skip` on `release_gate_judgment_basis_assessed`).

**Diff (BEFORE vs AFTER)**:

- `diff BEFORE.stdout.txt AFTER.stdout.txt` → **empty** (byte-identical console output, including the
  Rich-rendered check table and the `✓ verification passed` line).
- `diff BEFORE.stderr.txt AFTER.stderr.txt` → **empty**.
- `diff` on the written `reviews/verification.yaml` (BEFORE vs AFTER) → **one line differs**:
  `generated_at` timestamp only (`16:49:14` → `16:49:34`, the ~20s between the two invocations). Every
  other field — `passed: true`, `exit_code: 0`, all 17 `checks[]` entries (`id`/`severity`/`status`/
  `detail`/`locations`), `unsupported: []`, `exact_passage_violations: []` — is byte-identical.
- Per-claim diff (`claim_ledger.yaml` BEFORE vs AFTER, loaded via `yaml.safe_load`): `0` claims changed
  `status`; claim count unchanged at `87`/`87`; top-level `verification_status: passed` unchanged in
  both.

**Conclusion**: the additive `_term_index` field (nested dict, no key collision with any field
`verify_report`'s checks read — confirmed by both this run and the prior code-inspection finding above)
leaves `rf verify`'s output, exit code, per-check statuses, and per-claim verdicts **completely
unchanged** on a real 87-claim pediatric-CDS ledger. The only diff anywhere in the artifact set is the
non-semantic `generated_at` timestamp in the freshly-regenerated `reviews/verification.yaml`, which
changes on every invocation regardless of ledger content (it is `now_iso()` at call time, not a
content hash). This empirically confirms the verify-gate idempotency risk was **not triggered**: no
status flip, no new check failures, no change in exit code. Frontmatter updated `status: complete`,
`confidence: 0.78` per the pre-agreed rule for a clean run showing no flip.

Caveats: single run, single vocabulary/shape (`terms` + `usage_roles` + `vocabulary_version`); does not
by itself prove the *closed* `canonical_claim.schema.yaml` or the content-addressed
`assertion_identity.py` fingerprinting paths are safe (those remain code-inspection-level per the risk
register above — `claim_ledger.schema.yaml` is the open-schema layer this test exercised). Does not
cover the `rf bundle`/`rf council` gates, only `rf verify`.
