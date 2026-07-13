---
schema_version: 2
doc_type: report
title: "Reusable Assertion Ledger: Identity and Merge Audit Result"
status: review
created: 2026-07-13
updated: 2026-07-13
feature_slug: reusable-assertion-ledger
report_category: investigation
source: automated
outcome: conditional
metrics: ["1,440/1,440 deterministic identity comparisons", "48/48 material changes receive a new identity and predecessor link", "1/1 fixture lifecycle state-machine path"]
findings: ["Durable identity fixture passes; no independent human merge audit was available."]
action_items: ["Keep canonical claims disabled and run the labeled narrow-domain reviewer audit."]
promoted_to: ["docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-1-research-gates.md"]
---

# Identity and Semantic Merge Audit Result

## Scope and evidence class

The same frozen local fixture manifest and deterministic Phase 0 harness cover
32 synthetic editions, 240 source assertions, 108 candidate merges, and 48
qualifier hard negatives. No private source content, live index, or human
reviewer label was used. The upstream citation and segmentation charters remain
unconcluded, so their versioned contract cannot yet be consumed as empirical
evidence.

## RF evidence chain and traceability

The local RF evidence run is
`rf_run_reusable_assertion_ledger_p0_fixture_v1`, rebuilt by
`tests/fixtures/assertion_ledger/run_phase0_rf_evidence.sh`. Its two source
cards, 16-entry supported claim ledger, deterministic report, and
`verification.yaml` are checked in under
`tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/`; the verifier
exited 0 with all error-severity checks passing. The precise local command
sequence and skipped external commands are recorded in the historical replay
result; no `rf replay` command exists or was asserted.

The identity quantitative inputs map to supported ledger entries: 12 runs and
120 inputs `clm_011`; 240 assertions × 3 reruns × 2 orders = 1,440 comparisons
`clm_014`; 48 changed assertion timeframes with predecessor lineage `clm_015`;
The 108 candidates and 48 hard negatives are fixture-construction inputs, not
reviewer-labeled evidence; no independent human labels exist.
The fixture state-machine path is supported by `clm_016`; lineage counts map to
`clm_015`. These are deterministic local checks, not a corpus-wide collision
study or reviewer experiment.

## Identity contract exercised

Fixture identities use a domain-prefixed SHA-256 digest of canonical JSON:
`kind` plus sorted immutable payload fields. Edition and passage content must be
hashed independently; the fixture assertion payload includes edition, passage,
assertion text surrogate, population, and timeframe. Mutable records require
opaque stable IDs and versions outside that fingerprint. Raw edition bytes and
explicitly normalized passage text must remain separately retained in P1 so a
normalization change cannot conceal a material source change.

For a changed passage or material qualifier, issue a new passage/assertion ID,
store `predecessor_assertion_id`, and never overwrite the prior assertion. A
canonical-claim relationship is a versioned optional edge only: `proposed ->
reviewed -> active`, with `split`, `superseded`, and `rolled_back` transitions
that preserve every source assertion and historical reference.

## Deterministic result table

| Check | Numerator / denominator | Observed fixture result |
|---|---:|---:|
| Unchanged assertion identity | 240 assertions × 3 reruns × 2 input orders | 1,440 / 1,440 stable |
| Material change identity and lineage | 48 / 48 altered timeframes | 48 new IDs, 48 predecessor links, and all prior IDs retained |
| Candidate set | 108 candidates | **Fixture construction input; not a measured merge result** |
| Qualifier hard negatives | 48 / 108 candidates | **Fixture construction input; no reviewer label or safety outcome** |
| Collision / silent qualifier loss | 0 / 1,440 identity comparisons | **Inference from constructed fixture harness:** none observed |
| Merge/split/rollback | 1 / 1 explicit fixture state-machine path | `proposed -> reviewed -> active -> split -> superseded -> rolled_back`; source IDs and historical references remain resolvable |

The required two-reviewer label/adjudication audit was **not run**. Reviewer
acceptance, harmful false-merge rate, missed equivalents, and reviewer time are
therefore `not measured`, not zero.

## Verdict: conditional — assertion-only mode

The fixture establishes that the proposed content-addressed identity algorithm
is deterministic for its constructed inputs and materially changed records get
new, lineage-linked identities. It cannot establish corpus-wide collision
behavior or semantic merge safety. The result is **conditional**: P1/P2 may
proceed with immutable edition/passage/assertion identity, while canonical claim
grouping remains disabled.

`RF_CANONICAL_CLAIMS_ENABLED=false` is mandatory. Any future merge audit must
use 100–250 narrow-domain candidates, at least 40 hard negatives, two
independent reviewers, adjudication, >=80% acceptance, <2% harmful false
merges, and zero silent material-qualifier loss. An identity regression is a
hard stop for cross-run reuse.

## Inputs and restrictions for P1–P5

- **P1:** freeze separate immutable hashes, opaque record IDs, versions, and
  lineage fields; reject a hash/normalization contract that loses qualifiers.
- **P2/P3:** enforce new ID plus predecessor lineage for material changes and
  retain old assertion versions for historical report/run resolution.
- **P4:** expose source assertions distinctly from optional canonical claims;
  no merge-derived ranking or automatic grouping.
- **P5:** reusable assertion policy may not depend on canonical grouping.
  Disable automated reuse if deterministic identity or lineage checks fail.
- **Fallback:** assertion-only search/reuse candidates with reviewer-mediated,
  reversible canonical proposals deferred to a later domain-specific gate.

## Unresolved risks

Synthetic payloads do not represent OCR, PDF selectors, or real source
normalization; no independent labels test semantic equivalence or real merge
safety; and draft citation/segmentation contracts may alter the meaningful
assertion boundary.
