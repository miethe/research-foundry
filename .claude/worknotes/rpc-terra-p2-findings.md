FINDINGS

Evidence: `/tmp` is non-writable in this read-only sandbox (`mktemp … Operation not permitted`); focused pytest therefore could not start (`FileNotFoundError: No usable temporary directory`). Static audit completed. `run_launch.py` diff is exactly `+24/-0`; `activity_ref` is result-only and is not passed to `plan_run` or written to `run.yaml`.

1. **T2-1 — BLOCKER** — `provenance_envelope.py:754-862`: promotion trusts the caller’s `envelope_v1` mapping; it neither reloads nor verifies retained `v1.yaml`. A forged mapping with the same ID can publish a v2/receipt with altered inherited fields; reads never enforce required v1↔v2 eight-field byte equality. Fix: reload canonical v1 under the store root, verify its identity, require exact equality before promotion and on reads.

2. **T2-2 — BLOCKER** — `provenance_envelope.py:847-862`: `read_envelope` recomputes neither envelope identity nor receipt identity. A tampered v1, or a receipt with altered query/scope but unchanged stored fingerprint/activity ID, can be returned as valid; pair checks cover only shared linkage fields. Fix: add and invoke full envelope/receipt identity verifiers before pair/manifest checks.

3. **T2-3 — BLOCKER** — `provenance_envelope.py:817-831`: receipt, v2, and manifest are three sequential single-file replacements, not one atomic promotion. Crash after receipt write leaves v1+receipt; `read_envelope` accepts that half-pair. Concurrent writers can also race the existence check. Fix: staged transaction/lock/recovery protocol with an authoritative promotion marker; never expose receipt or v2 before the atomic manifest commit.

4. **T2-4 — MAJOR** — `provenance_envelope.py:871-886`: manifest lookup matches only `version`, accepts duplicate/malformed entries, and does not verify `record_kind`, `record_id`, or `fingerprint == receipt_commitment`. Fix: require exactly one matching `(record_kind, record_id, version)` entry and validate every committed field.

5. **T2-5 — MAJOR** — `research_run_discovery.py:77-101,137-145`: governed run-read authorization is optional. Listing has no identity/loader and returns all planned-run summaries; fetch allows reads whenever callers omit the loader or return `None`. Listing also omits fetch’s embedded-workspace check. Fix: require identity and resolve metadata internally; apply `_run_read_allowed` to both list and fetch, failing closed.

6. **T2-6 — MAJOR** — `provenance_envelope.py:501-570,625-724,660-674`: public write methods bypass `resolve_or_deny`; only `create_activity` uses it. AOS authorization is optional by default, and `tests/unit/test_provenance_envelope.py:717-729` explicitly locks in accepting opaque refs with no policy check. Fix: route every public writer through the canonical workspace guard and require the AOS policy resolver for present refs.

Test-vacuity: no wholly tautological scoped test found, but coverage omits the forged-v1, receipt-content-tamper, crash-window, concurrent-promotion, and unauthorized-list attacks above. The manifest test at `test_provenance_envelope.py:358-387` mutates v2 without recomputing the digest, so it does not exercise the self-consistent-forgery case.


[1mhook:[0m [2mStop[0m
[1mhook:[0m [2mStop[0m Failed
[2mtokens used[0m
125,074
FINDINGS

Evidence: `/tmp` is non-writable in this read-only sandbox (`mktemp … Operation not permitted`); focused pytest therefore could not start (`FileNotFoundError: No usable temporary directory`). Static audit completed. `run_launch.py` diff is exactly `+24/-0`; `activity_ref` is result-only and is not passed to `plan_run` or written to `run.yaml`.

1. **T2-1 — BLOCKER** — `provenance_envelope.py:754-862`: promotion trusts the caller’s `envelope_v1` mapping; it neither reloads nor verifies retained `v1.yaml`. A forged mapping with the same ID can publish a v2/receipt with altered inherited fields; reads never enforce required v1↔v2 eight-field byte equality. Fix: reload canonical v1 under the store root, verify its identity, require exact equality before promotion and on reads.

2. **T2-2 — BLOCKER** — `provenance_envelope.py:847-862`: `read_envelope` recomputes neither envelope identity nor receipt identity. A tampered v1, or a receipt with altered query/scope but unchanged stored fingerprint/activity ID, can be returned as valid; pair checks cover only shared linkage fields. Fix: add and invoke full envelope/receipt identity verifiers before pair/manifest checks.

3. **T2-3 — BLOCKER** — `provenance_envelope.py:817-831`: receipt, v2, and manifest are three sequential single-file replacements, not one atomic promotion. Crash after receipt write leaves v1+receipt; `read_envelope` accepts that half-pair. Concurrent writers can also race the existence check. Fix: staged transaction/lock/recovery protocol with an authoritative promotion marker; never expose receipt or v2 before the atomic manifest commit.

4. **T2-4 — MAJOR** — `provenance_envelope.py:871-886`: manifest lookup matches only `version`, accepts duplicate/malformed entries, and does not verify `record_kind`, `record_id`, or `fingerprint == receipt_commitment`. Fix: require exactly one matching `(record_kind, record_id, version)` entry and validate every committed field.

5. **T2-5 — MAJOR** — `research_run_discovery.py:77-101,137-145`: governed run-read authorization is optional. Listing has no identity/loader and returns all planned-run summaries; fetch allows reads whenever callers omit the loader or return `None`. Listing also omits fetch’s embedded-workspace check. Fix: require identity and resolve metadata internally; apply `_run_read_allowed` to both list and fetch, failing closed.

6. **T2-6 — MAJOR** — `provenance_envelope.py:501-570,625-724,660-674`: public write methods bypass `resolve_or_deny`; only `create_activity` uses it. AOS authorization is optional by default, and `tests/unit/test_provenance_envelope.py:717-729` explicitly locks in accepting opaque refs with no policy check. Fix: route every public writer through the canonical workspace guard and require the AOS policy resolver for present refs.

Test-vacuity: no wholly tautological scoped test found, but coverage omits the forged-v1, receipt-content-tamper, crash-window, concurrent-promotion, and unauthorized-list attacks above. The manifest test at `test_provenance_envelope.py:358-387` mutates v2 without recomputing the digest, so it does not exercise the self-consistent-forgery case.


