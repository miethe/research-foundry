# Gemini Profile — Mapping to `external_research_handoff/v1`

## Overview

This profile maps Gemini's real output shape — prose broken into spans, where some spans show small
numbered **grounding chips/footnotes** (each with a title and URL pointing at a web source Gemini
says it used) and some spans show **no grounding chip at all** — onto the same four required packet
members every profile produces. It builds on `../generic/mapping.md`'s baseline mapping and adds only
the Gemini-specific parts: chip-to-source mapping, grounded-vs-ungrounded span handling, and the
explicit-null preservation rule below.

**No Gemini API coupling, anywhere.** This profile never calls, imports, or depends on Gemini's API
or its `groundingMetadata` structure programmatically. Everything here is transcribed by hand from
what an operator reads in the Gemini app/AI Overview UI — the chip's displayed title and URL, and
whichever span of prose that chip sits next to. There is no JSON ingestion, no browser automation, no
session scraping, and no assumption about `groundingMetadata`'s internal shape.

## Member-by-member mapping

### 1. `handoff.yaml` (role: `handoff_manifest`) — you build this by hand

```yaml
schema_name: external_research_handoff
schema_version: "1.0"
transport: directory
producer_profile: gemini
research_context:
  research_question: null   # or the literal question you asked Gemini
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

### 2. `report.md` (role: `report`) — Gemini's prose, verbatim

Paste Gemini's prose answer unmodified — including both grounded and ungrounded spans, in the order
Gemini wrote them. Do not add YAML frontmatter, headers claiming verification, or any field this
schema doesn't ask for, and do not inline chip numbers/footnote markers as if they were citations RF
understands — `report.md` is plain markdown text, and its `content_role` is fixed at
`platform_synthesis` for every profile (contract §4.1). It can never be fed into a source-card,
claim, or assertion writer, no matter how it reads.

### 3. `sources.yaml` (role: `sources`) — one entry per grounding chip

Each distinct grounding chip Gemini's answer shows maps to exactly one packet-local `source_id` you
assign. The chip's displayed title becomes `title`; the chip's displayed URL becomes
`locator.url`. If a chip shows a DOI instead of (or alongside) a URL, capture it in `locator.doi`.

```yaml
schema_name: external_research_sources
schema_version: "1.0"
sources:
  - source_id: src_01              # your own packet-local id; stable within this packet only
    title: null                    # the chip's displayed title, or null if it showed none
    locator:
      doi: null                    # the chip's displayed DOI, or null
      url: null                    # the chip's displayed URL, or null
    publication_year: null
    access_status: unknown         # open-access | public-domain | paywalled | unknown
    declared_metadata:
      authors: []
      publisher: null
      accessed_at: null
    extensions:
      gemini:
        grounding_confidence: null   # Gemini's own displayed relevance/confidence hint, if shown — non-authoritative, hint only
        chip_index: null             # the chip's displayed number/position, if you want to preserve it
```

Gemini's own per-chip confidence or relevance indicator, **if the UI displays one**, is a
non-authoritative hint. It is captured only inside `extensions.gemini.*` — it is never promoted to a
top-level or computed field on the source record, and it never sets `access_status` or any other
schema-governed field by itself.

### 4. `assertion_candidates.yaml` (role: `assertion_candidates`) — one entry per answer span

Walk the answer span by span. **Every span becomes a candidate row, grounded or not.**

**Grounded span** (shows one or more grounding chips):

```yaml
- candidate_id: cand_01
  statement: "<the span's claim, in Gemini's own words>"
  value: null
  unit: null
  direction: null
  scope:
    population: null
    qualifier_band: null
  source_refs: ["src_01"]        # the chip(s) grounding this exact span — every chip shown, not just one
  relation: null
  classification: inference      # assertion ONLY if the span is confirmed verbatim source text; otherwise inference/annotation
  quote: null                    # literal quote ONLY if you can confirm the span is the source's exact wording — else null
  selector: null
  producer_confidence: null
  extensions:
    gemini:
      grounded: true
```

A grounded span's `quote` is filled **only** when the operator can confirm the span is the literal
source text (e.g. by opening the chip's link and matching wording). If you cannot confirm that, leave
`quote: null` and put the paraphrase in `statement` with `classification: inference` — never
`assertion` — even though a chip is attached. `classification: assertion` is reserved for the rare
case where the span genuinely is a verbatim quote from the grounded source; a grounded paraphrase is
still `inference`, not `assertion`.

**Ungrounded span** (no grounding chip shown at all — Gemini's own reasoning, synthesis, or a
transition sentence with no attached source):

```yaml
- candidate_id: cand_02
  statement: "<the span's claim, in Gemini's own words>"
  value: null
  unit: null
  direction: null
  scope:
    population: null
    qualifier_band: null
  source_refs: []                 # empty — never assign a source to an ungrounded span
  relation: null
  classification: inference       # inference or annotation — never assertion for an ungrounded span
  quote: null                     # an ungrounded span is never a literal quote of anything
  selector: null
  producer_confidence: null
  extensions:
    gemini:
      grounded: false
```

An ungrounded span is still eligible to become a candidate — it must never be silently dropped, and
it must never be given a fabricated `source_refs` entry to make it look grounded. `source_refs: []`
is the honest, correct representation of "Gemini said this but attached no source chip to it."

```yaml
schema_name: external_assertion_candidates
schema_version: "1.0"
candidates:
  # one entry per span, using the two shapes above
```

## Grounding-chip-to-source and grounded-vs-ungrounded rules (Gemini-specific, explicit)

- **One chip = one `source_id`.** If the same chip (same title/URL) grounds multiple spans, reuse the
  same `source_id` in every candidate's `source_refs` rather than minting a duplicate source entry.
- **Multiple chips on one span** are all listed in that candidate's `source_refs` — do not pick only
  one when Gemini's UI shows several chips grounding the same span.
- **An ungrounded span is not an error state.** Gemini routinely mixes grounded factual spans with
  ungrounded synthesis/transition sentences in the same answer. Both are legitimate candidate rows;
  only their `source_refs` and `classification` differ.
- **Never infer a source for an ungrounded span from surrounding context** — e.g. do not assume the
  nearest preceding chip also grounds a later ungrounded sentence just because they are adjacent. If
  Gemini's UI did not attach a chip to that specific span, `source_refs` stays empty.
- **Gemini's own confidence/relevance display is a hint, not a field.** Whatever visual weight,
  ranking, or relevance signal Gemini shows per chip goes only in `extensions.gemini.*` — it can never
  set `access_status`, `classification`, or any other schema-governed value.

## Explicit unknown-field rule (restated for this profile)

If you cannot resolve a value with confidence — a chip's DOI, whether a chip's confidence indicator
even applies, which exact chip grounds an ambiguous span, a publication year, an access status —
**leave the field explicitly `null`** (its schema-declared unset value) rather than omitting the
field or guessing. An unresolved or unclear grounding detail is represented as `null`, never deleted
from the record and never replaced with a fabricated best guess. This applies to every nullable field
in `sources.yaml` and `assertion_candidates.yaml`, not only the ones called out by name above.

## Optional members

### `activity.yaml` (role: `activity`) — optional

Not schema-governed in v1 (no dedicated schema exists yet for its content shape). If you include one,
keep it to safe IDs, timestamps, and short labels — no prose, no quotes, no secrets:

```yaml
schema_name: external_research_activity
entries:
  - at: "2026-07-26T00:00:00Z"
    note: "initial Gemini research session"
```

### Attachments (role: `attachment`) — optional, up to 32

Any raw file you want to carry alongside the packet (e.g. a table Gemini produced, or a screenshot of
the grounded answer with its chips visible). Declare it as a member with role `attachment`; it
carries no separate schema — it is opaque bytes, hashed and length-checked like every other member.

## Hard rules (apply to every profile, restated here)

- No Gemini API call, no `groundingMetadata` JSON ingestion, no browser automation, and no session
  scraping is used anywhere in this workflow — it is entirely manual, human-read-and-transcribe from
  the Gemini UI response, using operator-assigned packet-local IDs.
- `classification`, `producer_confidence`, `direction`, and `relation` are producer-declared HINTS.
  They can never set a computed completeness tier or a verified state — only Research Foundry's own
  importer and verifier can do that (contract §2.1, §2.4.1). Leave them honest rather than inflating
  them to look more authoritative.
- Vendor-specific fields, chip indices, relevance/confidence displays, or IDs that don't fit the
  template above go in `extensions` — never as an invented new top-level field. Every member schema
  uses `additionalProperties: false` at the top level specifically to make an invented field a hard
  schema failure, not a style choice.
- Every field, including everything inside `extensions`, is untrusted data. It may be stored and
  displayed through bounded, escaped surfaces, but it is never promoted into a prompt, a tool/resource
  description, a route/control value, a command, a schema selector, a filesystem path, or an execution
  argument — regardless of how convincingly it is shaped.
