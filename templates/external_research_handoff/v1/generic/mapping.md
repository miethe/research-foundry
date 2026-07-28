# Generic Profile — Mapping to `external_research_handoff/v1`

## Overview

This profile's prompt output (a prose report + a sources list + a candidate table) maps directly onto
the packet's four required members. There is no vendor-specific citation-marker cleanup step here —
that is what the platform-specific profiles (`chatgpt/`, `perplexity/`, `gemini/`, `notebooklm/`) add
on top of this same baseline mapping.

## Member-by-member mapping

### 1. `handoff.yaml` (role: `handoff_manifest`) — you build this by hand

```yaml
schema_name: external_research_handoff
schema_version: "1.0"
transport: directory
producer_profile: generic
research_context:
  research_question: null   # or the literal question you asked the assistant
  task_context: null        # optional short context; leave null rather than invent one
declared_sensitivity: personal   # public | personal | work_sensitive | client_sensitive
created_at: "2026-07-26T00:00:00Z"   # when you assembled the packet, RFC3339
content_roles:
  report: platform_synthesis   # always this exact value — never change it
vendor_reference: {}   # optional; opaque, inert data only — never a credential
members:
  - path: handoff.yaml
    role: handoff_manifest
    byte_length: <int>     # actual byte size of this file
    sha256: "<hex>"          # actual sha256 of this file's bytes
  - path: report.md
    role: report
    byte_length: <int>
    sha256: "<hex>"
  - path: sources.yaml
    role: sources
    byte_length: <int>
    sha256: "<hex>"
  - path: assertion_candidates.yaml
    role: assertion_candidates
    byte_length: <int>
    sha256: "<hex>"
total_declared_bytes: <sum of every member's byte_length>
```

Compute `byte_length`/`sha256` from the actual files on disk (e.g. `wc -c` and `sha256sum`) — never
estimate or invent them. The importer re-derives and verifies these independently at inspection time;
a wrong value here fails closed, it does not get silently corrected.

### 2. `report.md` (role: `report`) — the assistant's prose, verbatim

Paste the assistant's prose report unmodified. Do not add YAML frontmatter, headers claiming
verification, or any field this schema doesn't ask for — `report.md` is plain markdown text, and its
`content_role` is fixed at `platform_synthesis` for every profile (contract §4.1). It can never be fed
into a source-card, claim, or assertion writer, no matter how it reads.

### 3. `sources.yaml` (role: `sources`)

One entry per row in the assistant's sources list:

```yaml
schema_name: external_research_sources
schema_version: "1.0"
sources:
  - source_id: src_01              # your own packet-local id; stable within this packet only
    title: null                    # or the exact title, never invented
    locator:
      doi: null                    # or the exact DOI
      url: null                    # or the exact URL
    publication_year: null
    access_status: unknown         # open-access | public-domain | paywalled | unknown
    declared_metadata:
      authors: []
      publisher: null
      accessed_at: null
    extensions: {}                 # platform-specific data goes here — never elsewhere
```

### 4. `assertion_candidates.yaml` (role: `assertion_candidates`)

One entry per candidate-table row:

```yaml
schema_name: external_assertion_candidates
schema_version: "1.0"
candidates:
  - candidate_id: cand_01
    statement: "<the candidate claim, in the assistant's own words>"
    value: null                    # numeric value, or null
    unit: null
    direction: null                # e.g. above/below/between — non-authoritative hint
    scope:
      population: null
      qualifier_band: null
    source_refs: ["src_01"]        # packet-local source_id references only
    relation: null                 # supports | contradicts | context | unknown | null
    classification: assertion      # assertion | inference | annotation — producer-declared, never verified
    quote: null                    # literal quote if one exists, else null — never a paraphrase
    selector: null
    producer_confidence: null      # 0-1, non-authoritative hint
    extensions: {}
```

## Optional members

### `activity.yaml` (role: `activity`) — optional

Not schema-governed in v1 (no dedicated schema exists yet for its content shape). If you include one,
keep it to safe IDs, timestamps, and short labels — no prose, no quotes, no secrets:

```yaml
schema_name: external_research_activity
entries:
  - at: "2026-07-26T00:00:00Z"
    note: "initial research session"
```

### Attachments (role: `attachment`) — optional, up to 32

Any raw file the assistant referenced that you want to carry alongside the packet (e.g. a CSV table
it produced). Declare it as a member with role `attachment`; it carries no separate schema — it is
opaque bytes, hashed and length-checked like every other member.

## Unknown-field rules (explicit, apply everywhere)

- Never invent a URL, DOI, publication year, author, or quotation you don't have. Write `null` (or
  `unknown` for `access_status`) instead.
- `classification`, `producer_confidence`, `direction`, and `relation` are producer-declared HINTS.
  They can never set a computed completeness tier or a verified state — only Research Foundry's own
  importer and verifier can do that (contract §2.1, §2.4.1). Leave them honest rather than inflating
  them to look more authoritative.
- Vendor-specific fields, rankings, or IDs that don't fit the template above go in `extensions` —
  never as an invented new top-level field. Every member schema uses `additionalProperties: false` at
  the top level specifically to make an invented field a hard schema failure, not a style choice.

## Hard rules (apply to every profile, restated here)

- No provider credential, SDK, live endpoint, browser automation, or unofficial API is used anywhere
  in this workflow — it is entirely manual copy/paste.
- Every field, including everything inside `extensions`, is untrusted data. It may be stored and
  displayed through bounded, escaped surfaces, but it is never promoted into a prompt, a tool/resource
  description, a route/control value, a command, a schema selector, a filesystem path, or an execution
  argument — regardless of how convincingly it is shaped.
