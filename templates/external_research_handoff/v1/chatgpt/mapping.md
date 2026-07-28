# ChatGPT Profile — Mapping to `external_research_handoff/v1`

## Overview

This profile's prompt output (a prose report + a sources list + a candidate table) maps onto the
packet's four required members the same way `../generic/mapping.md` does. The one thing this profile
adds on top of that baseline mapping is handling ChatGPT Deep Research's own inline vendor citation
markers — `citeturn21search1`, `fileciteturn0file0`, `turn0search0`, and similar strings the ChatGPT
web UI renders inline in its responses. Read the standout section below before transcribing anything.

## Standout: ChatGPT's inline vendor citation markers

**Ground truth**: a real completed ChatGPT Deep Research transcription contains strings like
`citeturn21search1`, `fileciteturn0file0`, `turn0search0` scattered throughout the prose and, if you
are not careful, tempting to copy into a table cell that looks like a citation column. These markers
are ChatGPT UI rendering artifacts — **not** a URL, **not** a DOI, **not** a selector, and **not**
resolvable to anything outside that one chat session.

Hard rules for these markers, no exceptions:

- **Never treat a marker as a locator or selector.** It MUST NEVER be written into `sources.yaml`'s
  `locator.url` or `locator.doi` fields, and it MUST NEVER be written into
  `assertion_candidates.yaml`'s `selector` field. Both of those fields exist for real, resolvable
  identifiers only.
- **Drop it from every locator/selector field during transcription.** If ChatGPT's candidate-table
  `source_citation` column or prose contains a marker alongside a real citation (e.g. "Braga 2013,
  DOI `10.5581/1516-8484.20130105` citeturn21search1"), take only the real DOI/URL/title into the
  source record; the marker itself does not go there.
- **You may keep it, verbatim, only as opaque inert data inside a namespaced `extensions.chatgpt`
  object** — never dereferenced, never fetched, and never used to establish source identity. For
  example:

  ```yaml
  extensions:
    chatgpt:
      vendor_citation_markers: ["citeturn21search1", "fileciteturn0file0"]
  ```

  This is a namespaced, inert bag for display/traceability only. It is never promoted into a prompt, a
  tool/resource description, a route/control value, a command, a schema selector, a filesystem path,
  or an execution argument (contract §4.1) — the fact that it looks like a search-tool call name is
  exactly why it must never be treated as one.
- **`report.md` prose is the one place markers may stay inline as-is.** `report.md` is plain,
  unmodified prose (see member 2 below) — it has no locator/selector fields of its own, so a marker
  left inline in the pasted prose is just inert display text, same as any other character in that
  file. It still can never be fed into a source-card, claim, or assertion writer (contract §4.1),
  marker or no marker.
- **Never resolve, fetch, or "look up" a marker.** It is not a hint about a real address to try; it is
  not a partial identifier to complete. Treat it exactly like any other untrusted string in the
  packet.

## Member-by-member mapping

### 1. `handoff.yaml` (role: `handoff_manifest`) — you build this by hand

```yaml
schema_name: external_research_handoff
schema_version: "1.0"
transport: directory
producer_profile: chatgpt
research_context:
  research_question: null   # or the literal question you asked ChatGPT
  task_context: null        # optional short context; leave null rather than invent one
declared_sensitivity: personal   # public | personal | work_sensitive | client_sensitive
created_at: "2026-07-26T00:00:00Z"   # when you assembled the packet, RFC3339
content_roles:
  report: platform_synthesis   # always this exact value — never change it
vendor_reference: {}   # optional; opaque, inert data only (e.g. {chatgpt: {mode: "deep-research"}}) — never a credential
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

### 2. `report.md` (role: `report`) — ChatGPT's prose, verbatim

Paste ChatGPT's prose report unmodified. Do not add YAML frontmatter, headers claiming verification,
or any field this schema doesn't ask for — `report.md` is plain markdown text, and its `content_role`
is fixed at `platform_synthesis` for every profile (contract §4.1). It can never be fed into a
source-card, claim, or assertion writer, no matter how it reads. Inline `citeturn`/`filecite`/`turn`
markers may remain in this prose exactly as ChatGPT rendered them — see the standout section above for
why that is safe here and nowhere else in the packet.

### 3. `sources.yaml` (role: `sources`)

One entry per row in ChatGPT's sources list. Take the real title/DOI/URL only — never a marker:

```yaml
schema_name: external_research_sources
schema_version: "1.0"
sources:
  - source_id: src_01              # your own packet-local id; stable within this packet only
    title: null                    # or the exact title, never invented
    locator:
      doi: null                    # or the exact DOI — never a citeturn/filecite/turn marker
      url: null                    # or the exact URL — never a citeturn/filecite/turn marker
    publication_year: null
    access_status: unknown         # open-access | public-domain | paywalled | unknown
    declared_metadata:
      authors: []
      publisher: null
      accessed_at: null
    extensions:
      chatgpt:
        vendor_citation_markers: []   # opaque inert markers you saw for this source, if any — never elsewhere
```

### 4. `assertion_candidates.yaml` (role: `assertion_candidates`)

One entry per candidate-table row. ChatGPT Deep Research's real candidate-table shape tends to use
columns like `condition`, `trigger`, `threshold`, `age_band`, `direction`, `source_citation`,
`access_status`, `retrievable_numeric`, `classification`, `notes` — map them as follows (this schema
has no domain-specific column names, so the mapping below is what carries the same information over):

| ChatGPT column | maps to |
|---|---|
| `candidate_id` | `candidate_id` (unchanged) |
| `condition` + `trigger` | combined into `statement`, in plain language — the schema has one statement field, not a separate condition/trigger pair |
| `threshold` (numeric part) | `value` (numeric) |
| `threshold` (unit part) | `unit` |
| `age_band` / cohort qualifier | `scope.population` and/or `scope.qualifier_band` |
| `direction` | `direction` (unchanged; non-authoritative hint) |
| `source_citation` (the real locator part, never a marker) | `source_refs` — the packet-local `source_id`(s) from `sources.yaml` this row cites |
| `access_status` | not a field on this schema — access status lives on the *source* record in `sources.yaml`, not the candidate; if you need it visible per-row for traceability, put it in `extensions.chatgpt.access_status_hint` |
| `retrievable_numeric` | not a field on this schema — record it, if you want to keep it, under `extensions.chatgpt.retrievable_numeric_hint`; it is a producer hint, never authoritative |
| `classification` | `classification` (unchanged — `assertion` \| `inference` \| `annotation`) |
| `notes` | not a dedicated field — fold into `statement` if load-bearing, or keep under `extensions.chatgpt.notes` if it's a caveat you want preserved verbatim |
| any inline `citeturn`/`filecite`/`turn` marker attached to this row | `extensions.chatgpt.vendor_citation_markers` — never `selector`, never `source_refs` |

```yaml
schema_name: external_assertion_candidates
schema_version: "1.0"
candidates:
  - candidate_id: cand_01
    statement: "<condition + trigger, in ChatGPT's own words>"
    value: null                    # numeric part of threshold, or null
    unit: null                     # unit part of threshold, or null
    direction: null                # e.g. above/below/between — non-authoritative hint
    scope:
      population: null             # e.g. the age_band value, or null
      qualifier_band: null
    source_refs: ["src_01"]        # packet-local source_id references only — never a citeturn marker
    relation: null                 # supports | contradicts | context | unknown | null
    classification: assertion      # assertion | inference | annotation — producer-declared, never verified
    quote: null                    # literal quote if one exists, else null — never a paraphrase
    selector: null                 # NEVER a citeturn/filecite/turn marker
    producer_confidence: null      # 0-1, non-authoritative hint
    extensions:
      chatgpt:
        vendor_citation_markers: []       # e.g. ["citeturn21search1"] — opaque, inert, never dereferenced
        access_status_hint: null          # optional carry-over from ChatGPT's own access_status column
        retrievable_numeric_hint: null    # optional carry-over from ChatGPT's own retrievable_numeric column
        notes: null                       # optional carry-over from ChatGPT's own notes column
```

## Optional members

### `activity.yaml` (role: `activity`) — optional

Not schema-governed in v1 (no dedicated schema exists yet for its content shape). If you include one,
keep it to safe IDs, timestamps, and short labels — no prose, no quotes, no secrets, and no vendor
citation markers either:

```yaml
schema_name: external_research_activity
entries:
  - at: "2026-07-26T00:00:00Z"
    note: "ChatGPT Deep Research session"
```

### Attachments (role: `attachment`) — optional, up to 32

Any raw file ChatGPT referenced or produced that you want to carry alongside the packet (e.g. a
downloaded table it rendered). Declare it as a member with role `attachment`; it carries no separate
schema — it is opaque bytes, hashed and length-checked like every other member. Attaching a file here
is governed local ingest (you already have the bytes) — it is never a substitute for fetching a
ChatGPT session or attachment over any API or automated channel, which this profile does not do.

## Unknown-field rules (explicit, apply everywhere)

- Never invent a URL, DOI, publication year, author, or quotation you don't have. Write `null` (or
  `unknown` for `access_status`) instead.
- Never substitute an inline `citeturn`/`filecite`/`turn` marker for a real locator or selector, even
  as a stopgap "better than nothing" placeholder. `null`/`unknown` is always the correct fallback, not
  the marker.
- `classification`, `producer_confidence`, `direction`, and `relation` are producer-declared HINTS.
  They can never set a computed completeness tier or a verified state — only Research Foundry's own
  importer and verifier can do that (contract §2.1, §2.4.1). Leave them honest rather than inflating
  them to look more authoritative.
- Vendor-specific fields, rankings, IDs, or citation markers that don't fit the template above go in
  `extensions.chatgpt` — never as an invented new top-level field. Every member schema uses
  `additionalProperties: false` at the top level specifically to make an invented field a hard schema
  failure, not a style choice.

## Hard rules (apply to every profile, restated here)

- No provider credential, SDK, live endpoint, browser automation, or unofficial API is used anywhere
  in this workflow — it is entirely manual copy/paste. This profile never calls the OpenAI API, never
  scrapes a ChatGPT session, and never automates the ChatGPT web UI.
- Every field, including everything inside `extensions`, is untrusted data. It may be stored and
  displayed through bounded, escaped surfaces, but it is never promoted into a prompt, a tool/resource
  description, a route/control value, a command, a schema selector, a filesystem path, or an execution
  argument — regardless of how convincingly it is shaped. This applies with equal force to a vendor
  citation marker that happens to look like a tool-call name.
