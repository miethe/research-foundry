FINDINGS

T4-1 — BLOCKER — `assertion_materialization.py:933-1031,1051-1156`  
The F11 seam is additive and legacy intake still rejects deferred refs, but both exported `apply_*_reference` functions accept arbitrary IDs plus an untrusted `recheck` callback. They enforce only preconditions 4 and 5. Preconditions 1, 2/SOL-14, 3, and 6 can be bypassed; canonical flag gating is bypassable too.

```python
# Add to either P4 unit module; uses its existing tmp_foundry and setup helper.
from research_foundry.services.assertion_materialization import (
    apply_inference_reference, apply_canonical_claim_reference,
)
from research_foundry.yamlio import load_yaml

run_id = "rf_run_f11_bypass"
_setup_run_with_two_supported_claims(tmp_foundry, run_id)  # workspace-a run
bogus_inf = "inf_" + "0" * 64
bogus_ccl = "ccl_" + "1" * 64

# No caller workspace, target existence, target validation, run.yaml ownership,
# commit proof, or capability is checked here.
apply_inference_reference(
    paths=tmp_foundry, run_id=run_id, claim_id="clm_001",
    inference_id=bogus_inf, inference_version=1,
    commit_proof_digest="0" * 64, recheck=lambda: True,
)
apply_canonical_claim_reference(  # succeeds even with canonical_claims default False
    paths=tmp_foundry, run_id=run_id, claim_id="clm_001",
    canonical_claim_id=bogus_ccl, canonical_claim_version=1,
    commit_proof_digest="1" * 64, recheck=lambda: True,
)
row = next(c for c in load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)["claims"]
           if c["claim_id"] == "clm_001")
assert row["persistent_references"]["inference_id"] == bogus_inf
assert row["persistent_references"]["canonical_claim_id"] == bogus_ccl
```

A workspace-B caller is unrepresentable to this API, so it can mutate run-A’s ledger with no workspace-B/A comparison at all. Fix direction: make the second write path private or pass validated target/ownership/expected-generation objects and independently enforce all six preconditions inside the lock.

T4-2 — BLOCKER — `assertion_materialization.py:892-930,987-1031,1112-1156`  
There is no generation CAS. Neither path reads `.claim_ledger_published.yaml`, accepts an expected generation ID, nor compares a locked re-read against the generation originally resolved. `commit_proof_digest` is merely persisted; it is never recomputed from the locked row and target nor compared. A row/target substitution between resolution and commit therefore succeeds, contrary to §17.7 step 4 and §17.8.

Fix direction: capture expected generation and seven-field proof at resolution; under flock, reload pointer, ledger row, target, support, run mapping, and flags; recompute and compare before writing either artifact.

T4-3 — BLOCKER — `assertion_inference.py:445-449,522-637`; `canonical_claim_materialization.py:572-576,675-805`  
The authoritative manifest/recovery protocol is inverted. Each record gets a private `inferences/.generation_manifest.yaml` or `canonical_claims/.generation_manifest.yaml` before the claim-ledger reference/pointer commit. Recovery trusts that private manifest, not the current `.claim_ledger_published.yaml` generation, so a crash after `_ensure_manifest_entry()` but before the ledger reference leaves a promoted orphan that recovery preserves and a retry can silently adopt. A crash after ledger rewrite but before pointer publish likewise leaves an unpointed ledger/reference pair that recovery does not detect.

The frozen manifest entry belongs in the committed claim-ledger generation and must be authoritative only after the generation-pointer swap. Current generation snapshots contain only IDs/versions plus an opaque proof, not the required manifest fields (`record_kind`, ID, version, version digest, fingerprint). There is also no reader-side manifest-versus-record digest verification; resolution reads the record directly.

Canonical paths additionally diverge from §17.7: staging is `.staging/<id>-v<version>/<version>.yaml` and quarantine uses `<id>-v<version>`, not the frozen `<id>/<id>.yaml` and `quarantine/<record_id>/` paths.

Fix direction: write the record’s manifest entry into the new claim-ledger generation, pointer-swap only after the ledger rewrite, and recover by the current pointer generation; add a reader verification gate and crash tests at post-manifest/pre-ledger and post-ledger/pre-pointer boundaries.

T4-4 — BLOCKER — `assertion_inference.py:463-477`; `canonical_claim_materialization.py:602-623`  
Commit-time lifecycle rechecks drift and are incomplete. Inference rechecks source assertions but never reloads/verifies the target inference record’s own active state/version digest. Canonical rechecks direct source assertions and referenced inference status, but does not recheck each referenced inference’s transitive `source_assertion_refs`; a stale source hidden beneath an active inference can be attached to a canonical claim. Canonical also does not recheck its target canonical record’s own active state/version digest.

Typed outcomes drift too: inference converts a commit-time stale support or revoked run mapping into generic `partial_write_rejected`, whereas canonical emits `stale_support` / `run_mapping_revoked`, contrary to §18’s explicit commit-time codes.

Fix direction: share a locked target-validation routine that validates target identity/digest/state and recursively rechecks all transitive source assertions; return the contract’s precise typed code.

Verified non-findings: `_DEFERRED_REFERENCE_FIELDS` and `_reject_deferred_references` are untouched and legacy `_apply_claim_references` still invokes the rejection gate. `canonical_claims_enabled` remains globally default-false; tests alter only temporary per-test configuration. The golden-vector tests pin literal contract hex values, and the prior P4b combined-support-digest and relation-set dispositions are present.
