BLOCK

Reviewed target: `f0a42bf` plus the uncommitted P7 hardening/docs. Static analysis only; the read-only sandbox and unavailable `/tmp` prevented rerunning pytest.

### Contract conformance

| Frozen MUST | Result |
|---|---|
| Origin fingerprint binding on write and read | BLOCK — SOL-31 |
| Envelope v1 → receipt → v2 ordering and equality | BLOCK — SOL-32 |
| Six §17.1 preconditions under the locked commit | BLOCK — SOL-33 |
| §17.8 seven-field proof recomputation | BLOCK — SOL-34 |
| Verified report-use publication, `rrv_`, attestation | BLOCK — SOL-35 |

### Findings

- **SOL-31 — HIGH, gate-blocking — origin lookup is not bound to the requested ID/version.** Writing derives `origin_id` correctly, but [`read_origin()`](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:637) verifies the loaded record only against itself. It never requires `record["origin_id"] == requested_origin_id`. Parent/envelope reference checks are existence-only at [provenance_envelope.py:675](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:675) and [provenance_envelope.py:1258](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:1258), ignoring record identity and referenced version. This weakens the frozen binding at [contract-freeze.md:204](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:204).

  ```python
  # Copy valid B bytes under A's canonical filename:
  store._origin_path(a_id).write_bytes(store._origin_path(b_id).read_bytes())
  assert store.read_origin(a_id)["origin_id"] == b_id  # currently accepted
  ```

  Fix: validate lookup ID shape; bind requested ID/version to the loaded record; route all reference checks through that verified read.

- **SOL-32 — CRITICAL — envelope continuity can be half-read.** The writer’s sequencing is correct at [provenance_envelope.py:901](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:901), but the reader violates the frozen read invariant at [contract-freeze.md:1013](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:1013):

  - A manifested v2 remains visible when `receipt.yaml` is missing because `verify_pair_integrity()` returns success for any `receipt is None` at [provenance_envelope.py:287](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:287).
  - A manifested v2 remains readable after retained `v1.yaml` is removed; the byte-equality check is conditional on v1 existing at [provenance_envelope.py:1076](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:1076).
  - `verify_envelope_identity()` does not check the stored `identity.fingerprint`, algorithm, or material-field list at [provenance_envelope.py:243](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/provenance_envelope.py:243).

  ```python
  receipt, v2 = store.create_receipt_and_promote(v1, ...)
  store._receipt_path(v1["envelope_id"]).unlink()
  assert store.read_envelope(v1["envelope_id"]) == (v2, None)  # currently accepted
  ```

  Fix: v2 must require both retained v1 and receipt; verify the complete identity block and recompute v1→v2 equality.

- **SOL-33 — HIGH, gate-blocking — §17.1 precondition 1 is not fully rerun under the lock.** Initial creation validates schemas at [assertion_inference.py:441](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_inference.py:441) and [canonical_claim_materialization.py:572](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/canonical_claim_materialization.py:572). The locked reload at [assertion_materialization.py:1368](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_materialization.py:1368) checks existence, state and digest, but never reruns full schema validation as required by [contract-freeze.md:2059](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:2059). Mutating `type` or `schema_version` after promotion is not covered by the version digest and can be sealed into the ledger.

  Fix: add kind-specific schema/identity validation to `_TargetKindSpec` and execute it against the locked, freshly loaded record.

- **SOL-34 — HIGH contract mismatch — canonical claims use an unfrozen §17.8 encoding.** The frozen seventh field is the digest of the target’s bare `source_assertion_refs` list at [contract-freeze.md:2417](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/docs/dev/architecture/research-provenance-contract-freeze.md:2417). Inference conforms. Canonical claims instead hash an object containing both `source_assertion_refs` and `inference_refs` at [canonical_claim_materialization.py:601](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/canonical_claim_materialization.py:601) and [canonical_claim_materialization.py:650](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/canonical_claim_materialization.py:650). That may be stronger, but it is not byte-for-byte recomputable from the frozen contract.

  Fix: implement the frozen formula or explicitly refreeze the contract and vectors before closure.

- **SOL-35 — CRITICAL — report-use publication can self-issue the attestation it later trusts.** The real verification call site is correctly gated at [verification.py:1430](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/verification.py:1430), and direct `publish()` recomputes `rrv_` and checks an anchor at [assertion_report_use.py:872](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_report_use.py:872). However, exported `publish_report_assertion_uses_for_report()` creates that anchor itself at [assertion_report_use.py:1287](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_report_use.py:1287), accepting no verified result or independent proof. An existing test publishes through this function without calling `verify_report` at [test_assertion_report_use.py:761](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/tests/unit/test_assertion_report_use.py:761).

  The TOCTOU check also fails open: unreadable/deleted reports return `None` at [assertion_report_use.py:1203](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_report_use.py:1203), while denial occurs only for a non-`None` mismatch at [assertion_report_use.py:1294](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_report_use.py:1294).

  Fix: verification must independently write the pass artifact; publication may only consume it. A supplied report path that cannot be read and hashed must deny the entire batch.

- **SOL-36 — HIGH, gate-blocking — report-use is a fourth F19 citation writer.** `_resolve_source_assertion()` authorizes from immutable `lifecycle_state` alone at [assertion_report_use.py:676](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_report_use.py:676). Fresh publication repeats the same raw-only check at [assertion_report_use.py:943](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_report_use.py:943). Because P6 keeps the immutable record `eligible` and writes the authoritative policy separately, a new report-use can cite a genuinely policy-blocked assertion.

  Fix: use `effective_source_assertion_lifecycle_state()` during prepare and again at fresh publish; fail closed for `blocked` and `policy_invalid`.

- **SOL-37 — CRITICAL — the F19 effective-state reader itself has a one-field tamper bypass.** The blocked branch validates its complete policy shape, but the “active” branch at [assertion_impact.py:1259](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_impact.py:1259) checks only type, ID and `invalidation_state == "active"`. Changing a real blocked policy’s one field from `blocked` to `active`, while leaving `lifecycle_state: blocked` and its event ID intact, returns `eligible`. A symlinked policy also returns `eligible` at [assertion_impact.py:1250](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_impact.py:1250).

  Fix: validate the exact active snapshot shape, version and null-event invariants; treat present non-regular policy paths as `policy_invalid`.

- **SOL-38 — HIGH, gate-blocking — display authority is only refreshed during catalog rebuild.** Rebuild correctly applies effective F18/F19 state at [assertion_catalog.py:682](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_catalog.py:682) and [assertion_catalog.py:817](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_catalog.py:817). Existing projections are then trusted unchanged by:

  - normal search/packet/lineage: [assertion_catalog.py:397](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_catalog.py:397), [assertion_catalog.py:443](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_catalog.py:443);
  - C4 read-only search/packet: [assertion_catalog.py:507](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_catalog.py:507), [assertion_catalog.py:551](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/assertion_catalog.py:551);
  - export through `packet_read_only()`: [export_service.py:664](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/export_service.py:664).

  The F19 test explicitly rebuilds after blocking at [test_assertion_catalog.py:523](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/tests/unit/test_assertion_catalog.py:523), masking the stale-cache window.

  Fix: either overlay effective state non-mutatively on every load, or invalidate projections as an unconditional part of policy establishment and make read-only consumers return `catalog_unavailable` until rebuilt.

- **SOL-39 — MEDIUM — canonical resolution still reports effect-stale inference support as resolved.** `resolve_support()` reads immutable `inference.status` at [canonical_claim_materialization.py:389](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/canonical_claim_materialization.py:389). The locked commit later catches it, so it is not independently citable, but this violates the requested all-writer consistency. The existing F18 test actually pins that false intermediate result at [test_canonical_claim_materialization.py:1067](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/tests/unit/test_canonical_claim_materialization.py:1067).

  Fix: consult strict effective stale IDs during resolution as well as commit.

### Regression seams

- **C2/ERI:** preserved. The opaque bare `origin_id` still passes through unchanged at [export_service.py:1178](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/src/research_foundry/services/export_service.py:1178). Minor doc drift remains: the docstring still says the RPC schema does not exist.
- **C3/CARP:** preserved structurally. `search_run.retrieval.activity_id` remains additive, and non-null `activity_id` excludes the legacy `selections[]` mirror in [search_run.schema.yaml:216](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/schemas/search_run.schema.yaml:216).
- **C4 read-only:** no-write behavior remains intact, but effective lifecycle correctness is broken through SOL-38.

### P7 evidence integrity — four sampled rows

- **RPC-7.2:** genuine, non-vacuous origin/facet coverage.
- **RPC-7.4:** substantive for identity, replay, rights, `rrv_`, and raw lifecycle, but its lifecycle claim is incomplete: no real P6 policy block reaches report-use. See [ac-evidence-map.md:36](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/.claude/progress/research-provenance-continuity/ac-evidence-map.md:36).
- **RPC-7.6:** genuine for rebuilt-state parity and existence hiding, but omits a lifecycle transition against an already-built projection. See [ac-evidence-map.md:78](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/.claude/progress/research-provenance-continuity/ac-evidence-map.md:78).
- **RPC-7.17:** tests exist and are substantive, but “comprehensive” is overclaimed: they do not cover missing retained v1, missing receipt with visible v2, or tampered envelope identity metadata. See [ac-evidence-map.md:226](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/rpc-v1/.claude/progress/research-provenance-continuity/ac-evidence-map.md:226).

### Focused attacks

- **Wave 1:** attacked non-null `search_run.retrieval.activity_id` plus non-empty legacy `selections`; schema rejected it.
- **Wave 2:** broke report-use verification and policy-block boundaries — SOL-35/SOL-36.
- **Wave 3:** broke effective policy with a one-field mutation and a prebuilt projection followed by a real block — SOL-37/SOL-38.

Bounded residual accepted: repeated lifecycle events can re-enumerate already effect-stale dependents because enumeration still inspects immutable status. This appears redundant/idempotent rather than a fresh citability bypass.


