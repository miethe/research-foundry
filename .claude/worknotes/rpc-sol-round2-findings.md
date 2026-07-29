BLOCK

| Finding | Status | Empirical result |
|---|---|---|
| SOL-1 | PARTIAL | Old 5-field `material_fields` attack: **REJECTED**. Producer substitution with stale fingerprint: schema **ACCEPTED**, service recomputation mismatched. `origin_version: 1→999`: **ACCEPTED**, hash unchanged; version semantics remain unfrozen. |
| SOL-2 | REOPENED | Two different, hash-correct receipts (`sar_88c90…` and `sar_452cac…`) paired successfully with the same `rre_7d9fe…`; both schemas and all five §5.3 equalities passed after changing only envelope `activity_id`. |
| SOL-3 | CLOSED | Receipt `activity_kind: planned`: **REJECTED**; both schemas now use `planned_run`/`search_only`. |
| SOL-4 | CLOSED | Denied receipt carrying catalog generation, timestamp, and blank reason: **REJECTED** at all three fields. |
| SOL-5 | CLOSED | Durable `workspace_context_missing` reason: **REJECTED**. §5.2(c-1) unambiguously requires API-only, non-persisted pre-workspace denial. |
| SOL-6 | REOPENED | Omitted and `null` AOS refs converge, but `{}` and `{project_ref:null}` are both **ACCEPTED** and mint different envelope hashes. Empty string is rejected. |
| SOL-7 | PARTIAL | Missing/null evidence and fallback reason attacks: **REJECTED**; branches are structurally disjoint. Equivalent bypasses `fallback_reason:""`, `degraded_reason:""`, and `source:""`: **ACCEPTED**. |
| SOL-8 | REOPENED | `activity_id` plus non-empty legacy mirror: **REJECTED**. CARP selection without `question_id`/`decided_at`: **ACCEPTED**, so per-question provenance can still be flattened. |
| SOL-9 | CLOSED | Omitted inactive report/cited arms: **REJECTED**. Explicit-null encoding validates; documented revision vector recomputes correctly. |
| SOL-10 | REOPENED | Forged cleared status without authority link: **REJECTED**. But source `rights_summary:{}` is **ACCEPTED** while verbatim report `rights_snapshot:{}` is **REJECTED** for three missing fields. |
| SOL-11 | PARTIAL | `inference_id` without version: **REJECTED**. `inference_version` without ID, or with `inference_id:null`: **ACCEPTED**, contradicting the documented atomic-pair rule. |
| SOL-12 | REOPENED | Identity vectors are correct, but arbitrary IDs validate. Two canonical claims with the same ID/version and different statement/state both validate; their hashes differ, yet no persisted `version_digest` or fixed proof location exists. |
| SOL-13 | REOPENED | Protocol promotes a final discoverable record before reference publication, so crash visibility remains. It also assumes a claim-row generation/CAS marker absent from the schema and current implementation. |
| SOL-14 | REOPENED | The row digest detects row drift only; it omits target kind/ID/version and target material/support digest. An unrelated active target can still be attached to an unchanged row. |
| SOL-15 | REOPENED | `inference_record active→stale`: **ACCEPTED**; canonical/source active transitions: **REJECTED**. But `inference_record eligible→stale` and `canonical_claim eligible→stale`: **ACCEPTED**. The per-run lock also does not serialize lifecycle/config/run-mapping mutators, retaining TOCTOU. |

Cross-checks:

- All nine contract schemas passed `Draft202012Validator.check_schema()`.
- Additive-only audit: `search_run`, `inference_record`, `canonical_claim`, and `assertion_lifecycle_event` pass. `claim_ledger` fails: baseline-valid `{inference_id:"legacy-inf"}` without a version is now rejected. No required lists changed and no enum values were removed, but an existing constraint was tightened.
- Origin vector: `2429f3f8678e12519eacef2c0bab2642378d1e07c72c4acf5a076e53c598bc67` — correct.
- Report revision vector: `rrv_eecd155f212fbfdac8b698b4860aae49bfe236a1f9662895e3bea91f92873027` — correct.
- Inference and canonical-claim vectors also recomputed correctly.
- No outcome/lifecycle `oneOf` overlap or `planned_run` literal mismatch was found.
- SOL-6’s missing regex is defensible by itself because no shipped AOS ID convention exists. The accepted empty-object/wrong-kind aliases make the overall deviation unsound.
- SOL-12’s doc-level MUST can govern future minting without a regex, but leaving canonical version integrity unbound makes the overall deviation unsound.

New findings:

| ID | Severity | File / attack | Resolution direction |
|---|---|---|---|
| SOL-16 | BLOCKER | [Envelope identity](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/research_run_envelope.schema.yaml:189): receipt substitution survives schema validation, hash recomputation, and §5.3 equality. | Add an immutable pair-level digest/manifest binding both IDs, or include a receipt commitment in envelope material without circular identity. |
| SOL-17 | BLOCKER | [Claim ledger conditional](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/claim_ledger.schema.yaml:123): baseline instance accepted, current instance rejected. | Stop calling the amendment additive-only; version/migrate the narrowing or provide an explicitly validated compatibility rule. |
| SOL-18 | BLOCKER | [Canonical identity rule](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:1264): same ID/version content substitution is accepted and `version_digest` storage is deferred. | Persist the digest on the record or in a precisely named immutable manifest and validate it on every read/replay. |
| SOL-19 | BLOCKER | [Durable protocol](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:1525): promoted orphan is visible and the CAS operand/location is undefined. | Make a generation pointer the sole visibility boundary; freeze the marker schema/path, locking participants, and recovery transaction. |
| SOL-20 | BLOCKER | [Row binding](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:1595): proof binds the row only to its earlier self. | Digest `{row material, target kind/id/version, target material/support digest}` and protect all mutable dependencies with shared generations/CAS. |
| SOL-21 | BLOCKER | [Rights snapshot](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/report_assertion_use.schema.yaml:211) versus [source mirror](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/source_assertion.schema.yaml:173): valid source bytes cannot always be copied verbatim. | Reuse the exact subschema or define and hash a mandatory canonical normalization. |
| SOL-22 | MAJOR | Origin/envelope versions and report-use `created_at` mutate without hash changes; AOS `{}`/nullable-object aliases mint divergent IDs. | Freeze version semantics and a whole-record integrity digest; normalize nested omission/null/empty-object forms. |
| SOL-23 | BLOCKER | [CARP receipt membership](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/search_activity_receipt.schema.yaml:181): question/time fields remain optional. | Add a question-scoped discriminator and require `question_id` plus `decided_at` for every CARP-rebased entry. |
| SOL-24 | MAJOR | [Outcome fields](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/search_activity_receipt.schema.yaml:253): blank source/reason strings validate. | Add `minLength: 1` to every required non-null source/reason string. |

Review anchor remained `e76784b5460c3abe7abd9fdffa91dc9cc950c241` plus the supplied uncommitted tree. No files were changed.


