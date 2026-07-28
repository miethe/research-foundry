---
schema_version: 2
doc_type: design-spec
title: "External Research Transport Containers — Archive/Remote Transport (ERI-DF-2)"
status: draft
maturity: shaping
created: 2026-07-27
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
related_documents:
  - docs/dev/architecture/external-research-handoff-contract.md
deferred_from: "ERI Phase 1 (Contract Freeze) — ERI-OQ-1 resolution and deferred item ERI-DF-2 in the ERI implementation plan's Deferred Items table"
---

# External Research Transport Containers (ERI-DF-2)

## What is deferred

ERI v1 accepts **only a materialized directory of regular files** as a packet (contract §1.1,
resolving ERI-OQ-1): no archives (`.zip`/`.tar`/etc.), no remote transport (HTTP upload, S3, signed
URL, etc.), no symlinks, no special files. An operator must already have the packet materialized on
the local filesystem before running `rf intake external-report`.

This spec names, but does not scope, adding a **transport container layer** on top of the same
`external_research_handoff/v1` packet contract — e.g. accepting a `.zip`/`.tar.gz` archive and
extracting it into a materialized directory first, or accepting an HTTP-uploaded packet and staging
it to disk before the existing directory-only pipeline runs.

## Why it was deferred (from the implementation plan)

> Archive/remote transports add extraction, upload, auth, and path threats.

Every one of ERI's hostile-input-safety guarantees (contract §1.1, §2.1) is built specifically for a
*directory of regular files*: an `openat`-style directory-descriptor walk pinned to the packet root,
`O_NOFOLLOW` on every path component, `lstat`-before-open symlink rejection, and an `fstat`-after-open
device/inode check. An archive format reintroduces an entirely separate threat surface those
guarantees do not cover by construction:

- **Zip-slip / path-traversal-on-extract** — a member path inside the archive escaping the intended
  extraction root (`../../etc/cron.d/x`), which is a different vulnerability class from the
  already-solved "packet directory member path" traversal, because it happens at *extraction* time,
  before ERI's own directory walk ever runs.
- **Decompression bombs** — a small archive expanding to an enormous extracted size, a resource-
  exhaustion vector distinct from (and prior to) the packet's own byte/member-count limits (ERI-OQ-4),
  since those limits are enforced on the *already-extracted* directory.
- **Archive-format-specific parser vulnerabilities** — zip/tar parsers have their own history of
  memory-safety and logic bugs; adding one is adding a new untrusted-input parser to the trust
  boundary, on top of the `packet-safe-parse-v1` hardened YAML/JSON loader profile the contract
  already requires (§4.1b).
- **Remote transport (HTTP upload)** adds an entirely separate authentication/authorization surface
  (who may upload, to which workspace) and its own SSRF-adjacent concerns if the upload endpoint
  itself fetches from a caller-supplied remote location rather than accepting a direct body.

None of this is a "nice to have" gap — it is a deliberately excluded threat surface, consistent with
the plan's explicit prohibition: "The plan introduces ... no remote transport."

## Trigger for promotion

Per the plan's Deferred Items table: "Accepted threat model and concrete transfer requirement."
Concretely, before this is promotable:

1. A specific, named transfer requirement exists (e.g. "operators cannot get a materialized directory
   onto the RF host without X") — not a speculative convenience.
2. A threat model is written and accepted (mirroring this spec's own enumeration above) covering
   zip-slip/path-traversal-on-extract, decompression bombs, and archive-parser trust boundaries at
   minimum.
3. The chosen container format (if archive-based) has a well-audited, memory-safe extraction library
   available in this codebase's existing dependency set, or a justification for adding one.
4. If remote/HTTP transport is in scope, it is designed as a *distinct* authentication/authorization
   layer that sits entirely in front of today's existing directory-only pipeline — i.e. "upload +
   stage to a materialized directory, then hand off to the unmodified existing pipeline" — never a
   redesign of the identity/receipt contract (§1.1–§1.6) itself. The packet/receipt identity model
   (packet_digest over accepted members) should not need to change; only the containment/transfer
   step in front of it does.

## What this spec does NOT do

It does not choose zip vs. tar vs. some other container, does not design an upload endpoint, and does
not modify the `packet_digest`/`receipt_digest` identity formulas — those stay frozen (contract §1.2,
§1.3) regardless of how a materialized directory eventually gets onto disk.
