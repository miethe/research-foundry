---
title: "AAR: Catalog Went Dark — Three Compounding Gaps in the Assertion-Ledger Rollout"
doc_type: aar
status: review
date: 2026-07-15
created: 2026-07-15
updated: 2026-07-15
feature_slug: catalog-visibility
outcome: resolved
related_documents:
  - ./2026-07-14-reusable-assertion-ledger-p0-p5-execution.md
  - ../implementation_plans/features/reusable-assertion-ledger-v1.md
---

# AAR: Catalog Went Dark — Three Compounding Gaps in the Assertion-Ledger Rollout

## Scope and outcome

The operator reported that the runs-viewer Catalog (`:3030`) listed **no Sources** and **no Claims**
after recent updates. Investigation found the Catalog data (463 sources, 41 reports, 618 inferences,
3,033 claims) fully present and indexed on disk the entire time — nothing was lost. It had gone dark
for **three independent, compounding reasons**, none of which tripped a test or an alert. All three
are now resolved and deployed (`main` @ `068a4e6`, node `rocket-fedora`, 2026-07-15). Outcome:
**resolved**; two follow-on items (historical claim backfill, assertion-ledger activation) are
planned separately.

## What happened (timeline)

| Date | Change | Silent effect |
| --- | --- | --- |
| 2026-07-04 (`0d9d278`) | Reverted shipped viewer `sensitivity_threshold` `client_sensitive` → `public` as a fail-closed default for the public/multi-user release. | Every catalog item is `sensitivity=personal` (rank 1); the viewer filter `rank <= public(0)` redacted **all** Sources/Reports/Inferences to 0 in the UI. Data untouched on disk. No test, no alert. |
| 2026-07-14 (`b0e923b`) | Assertion-ledger P6/P7 UI: renamed the Catalog "Claims" tab to "Source assertions", repointing it at the new workspace assertion ledger. | The assertion ledger is unpopulated, so the (now default) tab renders empty; ~3,033 still-indexed classic claims were **orphaned with no backfill/migration path shipped**. |
| assertion-ledger v1 | `ledger_write_enabled` and the write seam (`source_cards.ingest_source`) shipped, and the flag was later enabled. | **No CLI or HTTP entry point passes `assertion_registry_workspace_id`**, so the ledger never populates — even on new runs. "Flag on" produced no observable capability. |
| (latent) | `rf serve --sensitivity-threshold <X>` mutated an in-memory config, but catalog endpoints re-read `foundry.yaml` from disk per call. | The node's intended fully-open `--sensitivity-threshold client_sensitive` flag was **silently ignored** by the catalog router; it always used `foundry.yaml`'s `public`. |

## Root causes

1. **A security-default change to a shipped config had no per-deployment escape hatch that was actually wired.** The `public` fail-closed revert was correct for public deploys, but the single-operator LAN node's compensating `--sensitivity-threshold` flag didn't reach the catalog router (the latent propagation bug), so the "safe default + operator override" contract was only half-built.
2. **A UI tab was repointed to a new, empty data source without a paired population/backfill plan.** The swap made "Source assertions" the default surface while the ledger that backs it had — and still has — no writer, and the data it replaced (claims) was left with no route back into the UI.
3. **A capability flag was enabled without an end-to-end driver.** `ledger_write_enabled: true` implies "this does something now," but the only shipped driver is a read path and a no-write readiness rehearsal; the write path has no CLI/HTTP caller.

## Detection gap

All three failures were **invisible to the test suite and the health gate**. The catalog blackout
passes every backend test (the data and API are fine; only the viewer-applied threshold hides it),
and the `:3030` viewer still returns HTTP 200, so even the redeploy health gate would report green on
a fully dark Catalog. There was no assertion that "the viewer's default threshold surfaces the data
that exists," nor that "an enabled write flag has a reachable driver."

## What went well

- Root-causing used parallel read-only investigation agents (assertion-ledger inventory; catalog
  diagnosis; live node diagnosis) and converged on evidence-backed verdicts fast, including the
  latent serve-flag propagation bug that the local view could not have revealed.
- The fix preserved the fail-closed `public` default (regression-tested both ways) rather than
  weakening it — the durable code fix made the node's existing flag effective and survived redeploy,
  cleanly retiring the manual stopgap.

## Lessons → system changes

1. **A tab/surface swap that repoints to a new empty data source must ship with a backfill or
   population plan, and must not silently orphan the prior data.** If the new source can't be
   populated yet, keep the old surface until it can.
2. **Any fail-closed change to a shipped viewer/redaction default must ship with a per-deployment
   override that is tested end-to-end** (flag → the actual consumer). A2 added exactly this test for
   the catalog threshold; generalize it: assert config/flag values reach their runtime consumer.
3. **"Flag enabled" must gate on "capability driveable."** Enabling a feature flag should require an
   end-to-end driver (a CLI or HTTP entry point that exercises the seam), not just the backend seam
   existing. A default-on flag with no reachable driver is a silent no-op that reads as "done."
4. **Add a smoke check that the viewer's default posture surfaces existing data** (e.g. catalog
   non-empty when runs exist), since HTTP-200 health gates do not catch a redacted-to-empty UI.

## Action items

- [x] A1 — node stopgap (threshold → `client_sensitive`), applied then retired by the durable fix.
- [x] A2 — propagate `rf serve --sensitivity-threshold` to the catalog router; `public` stays the
      fail-closed default (regression-tested). Shipped `068a4e6`.
- [x] B1 — restore the Claims tab (classic `item_type=claim`), alongside Source assertions. Shipped.
- [ ] B2 — claim → source-assertion backfill migration (populate the ledger from ~3,000 historical
      claims). Planned separately; touches the WKSP-304 write boundary.
- [ ] C — assertion-ledger activation: wire the write driver into an ingest/launch entry point,
      expose reuse fields, build the merge UI flag. Planned separately.
