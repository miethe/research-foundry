---
title: External Research Report Interchange (ERI)
doc_type: user_guide
schema_version: 2
status: active
created: 2026-07-27
updated: 2026-09-05
feature_slug: external-research-report-interchange
---

# External Research Report Interchange (ERI)

ERI imports a research report produced by an *external* tool — ChatGPT Deep Research, Perplexity,
Gemini, NotebookLM, or a hand-assembled generic packet — into Research Foundry as one
**materialized directory** following the `external_research_handoff/v1` contract. The report text
itself is never treated as evidence: it is staged as non-authoritative `platform_synthesis`, and
every cited source and candidate assertion is independently resolved through RF's own existing
acquisition, passage-binding, and verification machinery before it can be promoted to anything a
claim can rely on.

**Repository-ready, offline-unvalidated.** ERI ships fully tested against offline fixtures for all
five producer profiles below. The five producer-prompt templates are **offline-unvalidated** —
none has been run against a live vendor session as part of this feature. The ChatGPT profile was
additionally modelled on one real, previously-captured ChatGPT Deep Research packet (not a fresh
live capture during this feature's development), so its shape has one grounded reference point; the
other four profiles have no such reference. Treat every profile's prompt as a starting template to
adapt, not a guaranteed-correct produce of any specific vendor's current UI/output.

## Why a packet is not itself evidence

A vendor's own "citation" or "source" list is not something RF can verify just by reading it — it
could be stale, mis-quoted, or simply wrong. So ERI:

1. Never lets `report.md` (the vendor's synthesized prose) become a source card, a claim, or an
   assertion. It is staged and displayed, never fed into the evidence pipeline.
2. Re-acquires every cited source through RF's own SSRF-safe acquisition gate — never trusts a
   vendor-supplied excerpt as if it were the full retrieved text.
3. Requires an **exact**, unique passage match between a candidate's quoted text and the
   re-acquired source's content before it can advance past `passage_resolved`. Zero matches,
   multiple matches, or drifted text is quarantined — never guessed at, never "closest match."
4. Requires RF's existing `verify_report` and assertion-materialization pipeline — the same
   authority every other RF claim goes through — to accept a claim relationship before anything
   reaches `verified`. ERI adds no second verification authority.

## Producing a packet

A packet is a plain directory (no zip, no upload, no symlinks, no special files) with these
members:

| File | Role | Required |
|---|---|---|
| `handoff.yaml` | Manifest: declared members, schema versions | Yes |
| `sources.yaml` | Cited sources (locator, title, access status) | Yes |
| `assertion_candidates.yaml` | Candidate claims + quoted evidence + source refs | Yes |
| `report.md` | The vendor's synthesized report (`platform_synthesis`, never evidence) | Yes |
| `activity.yaml` | Optional producer activity/session metadata | No |
| local attachments | Packet-internal files referenced by an opaque `attachment_id` | No |

Every packet-member field — including vendor-specific extension fields — is treated as untrusted
data. A string shaped like a prompt override, a tool call, or a path is never interpreted as one; it
is only ever displayed, escaped, back to you.

### The five producer profiles

Canonical example packets for all five (plus a dedicated adversarial-injection fixture) live under
`tests/fixtures/external_research_handoff/profiles/`. Each is a full prompt + output-mapping recipe
you run manually against the named tool, then hand-assemble into the packet member files above.

- **Generic** — the baseline profile any tool's output can be mapped into by hand.
- **ChatGPT** (Deep Research) — packet-local citation/source IDs, no API/session scraping.
- **Perplexity** — maps citation/search-result metadata; ranking is never authoritative.
- **Gemini** — maps answer spans and grounding/source references; no Google API coupling.
- **NotebookLM** — manual, deterministic notebook synthesis/source export.

None of the five profiles assumes a vendor API key, SDK, live endpoint, or browser automation —
every one is a manual copy/paste-and-map workflow you run yourself.

## Importing a packet

```bash
# Inspect the plan first — zero canonical effects, never mutates state.
rf intake external-report ./packet-dir --workspace my-workspace --dry-run

# Staging-only import (no run created, no run-local projection).
rf intake external-report ./packet-dir --workspace my-workspace

# Import and project provenance into an existing run.
rf intake external-report ./packet-dir --workspace my-workspace --run rf_run_20260101_example

# Machine-readable output for scripting.
rf intake external-report ./packet-dir --workspace my-workspace --json
```

Omitting `--run` is staging-only: nothing is created or written into any run's timeline, and the
receipt is still a complete, truthful record of everything staging could determine. `--dry-run`
never mutates anything, including a target run's timeline.

### Large packets: batching and resume

A large packet is processed in bounded batches (`--limit`, default 100 new actions per call). A
call that hits the limit reports `complete: false` and a safe `cursor`:

```bash
rf intake external-report ./big-packet --workspace my-workspace --limit 100
# complete: false, cursor: {...}
rf intake external-report ./big-packet --workspace my-workspace --limit 100 --resume
# ... repeat --resume until complete: true
```

Interrupted (crash, Ctrl-C, hitting `--limit`) and uninterrupted imports of the exact same packet
converge to a byte-identical receipt and identical canonical effects — resuming never re-does work
or produces a different outcome than running straight through would have.

Re-running the exact same command against a packet that already has a **completed** receipt returns
that stored receipt unchanged (a true replay) — it never re-acquires sources or re-runs resolution.

## Completeness tiers

Every source and candidate assertion lands at exactly one tier, computed by the importer — a
vendor's own "confidence" or "verified" label in the packet is never trusted to set this:

| Tier | What it means | What you can do with it |
|---|---|---|
| `locator_only` | Only a locator/description exists; nothing was bound to real content | Discovery/acquisition queue only |
| `source_resolved` | The source was acquired and bound to one immutable edition | Source context; not claim support |
| `passage_resolved` | The candidate's quoted text uniquely matched one exact passage | Candidate evidence for RF verification |
| `verified` | RF's existing verifier accepted the claim relationship | Full claim/assertion use |

`verified` is only reachable when you pass `--run` — a staging-only import can reach
`passage_resolved` at best, honestly, because RF's verifier is run-scoped by design.

## Quarantine

An item that cannot advance is **quarantined** — a normal, expected, terminal outcome for most real
imports, not an error. The receipt tells you *how many* items quarantined and at what tier they
stopped, but does not print the specific internal reason (which host was unreachable, which claim
failed verification, etc.) — that detail is retained in an access-controlled audit record, not on
the ordinary caller-visible surface, so that one caller's denial can never be used to learn facts
about another workspace's resources.

Common reasons an item quarantines:

- the source could not be reached, or was reached but denied by RF's acquisition policy
  (private/loopback/metadata address, disallowed scheme, etc.);
- the candidate's quoted text had zero or more than one exact match in the source;
- the quoted text drifted from what is on record for that source;
- a claim relationship failed RF's own verification;
- the item required rights metadata or sensitivity clearance that was missing or denied.

## Troubleshooting

**Candidates quarantine against a target run.** An authorized operator can inspect
`receipts/<receipt_digest>/effects/*.yaml` for the specific `reason_code` referenced by the receipt's
`audit_ref`. `target_run_not_found` means the supplied `--run` was never scaffolded; create the intended
run before a new import. `promotion_invalid` identifies invalid staging data, `promotion_io_failed`
identifies filesystem failures, and `promotion_failed` identifies an unclassified promotion-adapter
failure. These are separate from evidence that could not verify (`verification_failed`). Count these
per-action reasons directly: `by_completeness_tier` cannot contain failure reasons. Existing terminal
receipts are immutable, and replay preserves their original reasons.

**"blocked" status, not a receipt with quarantined items.** This means the packet itself failed
structural validation before anything was resolved — a required member is missing, a schema version
is unsupported, or a declared limit (member count, byte size, attachment count) was exceeded. Fix
the packet's structure and re-run; nothing was staged.

**A large import never seems to finish.** Check whether it is legitimately still batching
(`complete: false` with a `cursor` — keep passing `--resume`) versus genuinely stuck; `--json`
output always shows the exact `counts` so far.

**"pending import already exists" without `--resume`.** A prior call for this exact
packet/workspace/target left work unfinished. Pass `--resume` to continue it, or `--dry-run` to
inspect the plan without touching anything.

**Everything quarantines with `source_unavailable`-shaped items.** Check that cited URLs are
publicly reachable HTTP(S) locations — ERI's acquisition gate refuses local/private/internal
addresses by design (this is a safety feature, not a bug) and never falls back to a weaker
transport.
