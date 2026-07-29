FINDINGS

T3-1 — CRITICAL — `assertion_report_use.py:695-715`, `schemas/report_assertion_use.schema.yaml:80-86,453-465`  
`publish()` never recomputes and compares `identity.fingerprint`/`use_id`, nor verifies the `run_report` `rrv_` formula or a verified report exists. A direct caller can mint an unverified, mis-bound record.

```python
r = copy.deepcopy(outcome.record)  # valid prepared source assertion record
r["report_ref"]["report_revision_id"] = "rrv_" + "0" * 64  # formula-invalid
fp = report_assertion_use_fingerprint(r)
r["identity"]["fingerprint"] = fp
r["use_id"] = "rau_" + fp
service.publish(r)  # currently writes; no report was verified

# Separately, changing created_at while retaining the old use_id/fingerprint
# also writes on a fresh path; publish only checks the rau_ prefix.
```

Fix: at the write boundary require `workspace_id == service.workspace_id`, recompute fingerprint and `use_id`, verify `rrv_`, and bind the batch to a durable passing verification/digest attestation.

T3-2 — HIGH — `assertion_report_use.py:849-863`  
The verification-pass anchor is neither write-once nor race-safe. Two first callers can return different anchors for the same revision; editing the anchor later silently mints another use identity.

```python
# Gate A immediately before its anchor write; let B finish first.
# A: sees absent -> blocks
# B: sees absent -> writes/reads "2026-...B" -> returns B
# A: resumes -> replaces anchor with "2026-...A" -> returns A
# Both then publish same report_revision_id with distinct created_at/use_id values.
```

Fix: use exclusive create or a per-revision lock, validate the stored schema/revision, and make a changed existing anchor an integrity error rather than accepting it.

T3-3 — HIGH — `assertion_report_use.py:524-542,749-781`  
Workspace isolation is only implied by the storage path: fresh publish never compares `record["workspace_id"]` with `self.workspace_id`, and resolver reads follow symlinks. A record can claim workspace B while being written under A, or an A assertion path can symlink to B.

```python
r = copy.deepcopy(outcome.record)
r["workspace_id"] = "workspace-B"
fp = report_assertion_use_fingerprint(r)
r["identity"]["fingerprint"] = fp
r["use_id"] = "rau_" + fp
service.publish(r)  # writes under workspace-A root with workspace-B identity
```

Fix: enforce record/service workspace equality and reject resolved paths whose real path escapes the workspace assertion root.

T3-4 — HIGH — `verification.py:882-887,1421-1433`  
The hook hashes the earlier parsed `body`, never re-reads the report at publication. A concurrent edit after verification checks but before the hook leaves a published use for an old body while the report path now contains substituted bytes; this violates §13.5’s publish-time digest check.

```python
# In a test, monkeypatch _intent_requires_review (called after checks) to:
front, current = load_md(report_path)
dump_md(front, current + "\nUnverified replacement.\n", report_path)
# verify_report still publishes using sha256(original_in_memory_body.encode()).
```

Fix: snapshot verified raw body bytes/digest and atomically bind publication to that snapshot, or re-read and compare the current body digest immediately before any report-use write.

T3-5 — HIGH — `assertion_report_use.py:715-716,805-830`, `verification.py:1421-1438`  
The broad hook catch preserves the verification verdict, but can silently leave a record without its manifest or a partially published batch. Concurrent manifest read-modify-write can additionally drop entries. `verification.yaml` records a pass with no report-use publication outcome, so neither retry nor audit is triggered.

Fix: serialize/compare-retry manifest updates and persist a report-use publication status/outbox; keep verdict compatibility while making incomplete finalization visible and recoverable.

T3-6 — MEDIUM — `tests/unit/test_assertion_report_use.py:234-251,345-364,798-851`  
The conflict attacks mutate a record only after its path already exists, so they exercise the early `path.exists()` comparison—not identity verification on a fresh write. The “mutable report substitution” test edits then re-verifies, missing the actual verify→publish TOCTOU window. No test covers forged fingerprint/use ID, forged `rrv_`, workspace-field mismatch, anchor race/tamper, or hook-swallowed partial finalization.

Fix: add fresh-path adversarial tests for each case above; do not monkeypatch away the identity/write-boundary checks being asserted.


