BLOCK

Review anchor: baseline HEAD `e76784b5460c3abe7abd9fdffa91dc9cc950c241` plus the supplied working-tree contract changes. Read-only; no files changed by this gate. All nine schemas pass `Draft202012Validator.check_schema()`.

### Finding verification

| Finding | Status | Evidence |
|---|---|---|
| SOL-1 | PARTIAL | Five-field identity and stale-fingerprint attacks are detectable by recomputation, but schema accepts them; the enforcing origin writer remains explicitly undecided and freeze `RPC-7.7` conflicts with the governing plan task. |
| SOL-2 | REOPENED | A substituted v2 envelope/receipt pair with recomputed hashes passes both schemas and all six §5.3 equalities. The only barrier is an untested v1→v2 byte-for-byte history rule. |
| SOL-3 | CLOSED | `activity_kind: planned` rejects; `planned_run` is consistent. |
| SOL-4 | CLOSED | Denied receipts carrying catalog generation, timestamp, or invalid reason reject. |
| SOL-5 | CLOSED | Durable `workspace_context_missing` rejects; pre-workspace denial remains ephemeral. |
| SOL-6 | CLOSED | `aos_refs: {}`, partial-null, and blank refs reject; top-level null/omission and populated refs accept. |
| SOL-7 | CLOSED | Blank `source`, `degraded_reason`, and `fallback_reason` reject. |
| SOL-8 | CLOSED | `catalog_planning` without `question_id` or `decided_at` rejects; ordinary search remains valid without them. |
| SOL-9 | CLOSED | Omitted inactive report/cited arms reject; explicit-null encoding accepts. |
| SOL-10 | REOPENED | `{}` accepts and normalized hashes match, but a valid source `rights_summary` with blank failure detail cannot be copied into `rights_snapshot`. |
| SOL-11 | PARTIAL | Baseline `{inference_id:"legacy-inf"}` accepts. The atomic-pair writer rule is clear, but no exact enforcing method is named and `RPC-7.5` is already assigned differently. |
| SOL-12 | REOPENED | Digest omission/null downgrade, unbound version integers, and unbound canonical successor/reversal fields preserve schema validity and authority-changing mutations. |
| SOL-13 | PARTIAL | Durable paths, generation pointer, lock, and recovery ordering are convergent; named `RPC-7.1` does not exist in the governing plan. |
| SOL-14 | REOPENED | Six-field formula is structurally stronger, but its claimed vector lacks a complete canonical preimage and its `RPC-7.2` task collides. |
| SOL-15 | PARTIAL | Lifecycle narrowing and bounded concurrency model are sound; claimed `RPC-7.8` is actually the plan’s Optional AOS gate. |
| SOL-16 | REOPENED | Same successful substitution as SOL-2; write-once commitment/equality does not verify unchanged v1→v2 carry-forward. |
| SOL-17 | PARTIAL | Legacy compatibility is restored, but the writer-level closure lacks an unambiguous method/task owner. |
| SOL-18 | REOPENED | Same digest downgrade and coverage gaps as SOL-12. |
| SOL-19 | PARTIAL | Same missing real P7 task as SOL-13. |
| SOL-20 | REOPENED | Same incomplete commit-proof vector/task collision as SOL-14. |
| SOL-21 | REOPENED | Source/report rights subschemas still have different validation domains. |
| SOL-22 | REOPENED | Origin/report/AOS fixes work, but envelope digests remain removable and the versioned pairing protocol is internally inconsistent. |
| SOL-23 | CLOSED | Catalog-planning discriminator is schema-enforced. |
| SOL-24 | CLOSED | Round-2 required non-null blank-string attacks reject. |

The rights counterexample is concrete: `rights_triage_failure.detail: ""` validates under [source_assertion rights_summary](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/source_assertion.schema.yaml:173) but fails [report_assertion_use rights_snapshot](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/report_assertion_use.schema.yaml:234).

### Vector checks

| Vector | Result |
|---|---|
| Origin fixture (a) | PASS — `d34184a1c3f0d1d8ae9b8248f345de1fbc46da068695ac546cc26dcfa59093db` |
| Origin fixture (b) | PASS — `00547bb71d6f5ce8d318f8ecdbaca505435457f686ceaa9ee67204e923a59606` |
| Origin version `1→999` | PASS — `af04c5bf56b7271b069252cb7b1493fdb4f1e0573da6ce387b2ae5f2e9d8d488` |
| Envelope v1 | PASS — `ee51e9188b935d21f1608ef9eaa562352556fbe316d4276e868112090a768c88` |
| Envelope v2 | PASS — `c1ea2b059da4ed1efa10ca2f25392fca1f7d7c8fd2c87086bef009e84fa2c3e9` |
| Report revision | PASS — `eecd155f212fbfdac8b698b4860aae49bfe236a1f9662895e3bea91f92873027` |
| Report-use honest | PASS — `2a071b5be0f58f09208a0ce71ebb9b62ce05a045d73bbe5acff3a290d5d05242` |
| Report-use created-at mutation | PASS — `0d238f0b8334a62701ceec6fdbe6d36a555c7150acff19afaced42bc5623830c` |
| Report-use rights mutation | PASS — `c7ff2c4c4309281874a4274277dc79b4853bdaf3e6d227d27ab59f3b641d7065` |
| Normalized `{}`/fully-spelled rights | PASS — both `4fcc2060b1fbee8ac58e45751a666d57af74fdbe7589df2cb9a94df4d15285c2` |
| Inference identity/version digest | PASS — `fd3ee362…464e51` / `eb94ff60…f45e2` |
| Canonical identity/version digest | PASS — `47cc4458…0da15` / `7cceafab…f75e4` |
| Commit-proof digest | **BLOCKER — not reproducible** |

The commit-proof vector names `clm_007` but omits exact `row_material.sources` and `row_material.conclusion_text`. Assuming the §18.1 inference support and conclusion produces `da2e0eab6694cfafdea8dbd5b9d11755640e33b1041f7dc6d33ec702605cabca`, not the claimed `e42fa121…fea1`. The contract therefore does not provide a canonical preimage for independent verification at [§17.8](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:2123).

### Deviation rulings

- **Envelope `version_digest` substitution: UNSOUND.** Stale digests are detected, but deleting the optional digest remains schema-valid/read-tolerated. More decisively, a substituted receipt and v2 envelope with recomputed receipt fingerprint, activity ID, commitment, and version digest pass all schemas and all six equalities. The documented honest v2 itself fails §5.3 check 5 because the receipt names envelope version 1 while the current envelope is version 2. See [§5.1b](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:501).

- **Lifecycle narrowing: SOUND within framing (c).** Searches of `runs/`, `tests/`, and `templates/` found zero `eligible→*` instances targeting `canonical_claim` or `inference_record`. Five literal Python fixtures all target `source_assertion`. Schema tests accept `eligible→stale` for `source_edition`, `passage`, and `source_assertion`, and reject it for the two affected kinds.

### New findings

| Finding | Severity | Evidence |
|---|---|---|
| SOL-25 | BLOCKER | **Digest downgrade:** forged inference/canonical content with `version_digest` omitted or null remains valid; envelope v2 without its digest also validates. All retain schema version `1.0`, with no epoch marker distinguishing legitimate legacy absence from deletion. |
| SOL-26 | BLOCKER | **Authority omitted from digests:** `inference_version` and `canonical_claim_version` can change `1→999` without changing their digests. Canonical `replaces`, `replacement_claims`, and `reversal.resulting_claims` can also be substituted without digest change. |
| SOL-27 | BLOCKER | **P7 identifiers are not implementer-convergent:** freeze [§17.9](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:2156) repurposes `RPC-7.2`–`RPC-7.8` and invents `RPC-7.1`; the [governing P7 plan](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md:385) already assigns those IDs to different gates. Several closures also explicitly leave their enforcing method/service undecided. |
| SOL-28 | BLOCKER | **Commit-proof vector has no complete preimage:** required claim-row material is missing, so `e42fa121…fea1` cannot be independently recomputed. |

Prior memory was used only to preserve exact-tree rereview discipline; every verdict fact above was reverified against the current supplied tree.


