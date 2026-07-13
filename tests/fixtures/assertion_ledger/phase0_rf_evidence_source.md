# Reusable Assertion Ledger Phase 0 deterministic fixture evidence

This local-only source describes the frozen `reusable-assertion-ledger-phase0-local-only-v1` fixture.

The fixture contains 12 synthetic runs and 120 synthetic source inputs.

The fixture defines 144 run-source processing opportunities, of which 36 are safe reuse opportunities.

The fixture audits all 36 eligible reused assertions and records 36 correct passage-provenance checks.

The fixture identity check compares 240 assertions across three reruns in two input orders, for 1,440 comparisons.

The fixture changes 48 assertion timeframes and validates 48 new identities, 48 predecessor links, and retention of all prior fixture IDs.

The fixture runs `proposed -> reviewed -> active -> split -> superseded -> rolled_back`; source IDs and history persist.

The fixture contains 108 merge candidates, including 48 qualifier hard negatives, but no independent human reviewer labels.

The fixture defines 12 retraction-propagation graphs with 120 expected affected objects.

The fixture enumerates 120 independently authored expected objects and checks complete, duplicate, out-of-order, interrupted, and partial-resume delivery against that expected manifest.

The fixture assigns one lifecycle action per expected object, blocks authoritative assertion reuse and current eligible reads before asynchronous reconciliation, and converges idempotently without duplicate receipts.

The fixture is synthetic and local-only. It cannot establish representative private-corpus economics, real-source normalization behavior, or real canonical-merge safety.
