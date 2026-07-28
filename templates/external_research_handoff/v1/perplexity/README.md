# Perplexity Producer Profile

**What this is**: the `external_research_handoff/v1` producer profile for Perplexity (perplexity.ai) —
it maps Perplexity's real output shape (prose with inline numbered `[N]` citation markers, backed by a
numbered Sources panel of title/URL/snippet entries, plus Perplexity's own relevance/ranking signal on
that panel) onto the packet's four required members.

**Offline/manual boundary**: fully manual. You paste `prompt.md` into a Perplexity chat, copy its prose
report, sources list, and candidate table by hand, and build the four packet files yourself following
`mapping.md`. No Perplexity API key, SDK, browser automation, or session file is used or assumed
anywhere in this workflow.

**How to produce a packet**:

1. Paste `prompt.md` into a Perplexity chat (a new question, or a follow-up in a thread you already
   researched).
2. Copy its prose report (with `[N]` citation markers intact), its numbered sources list, and its
   candidate table.
3. Follow `mapping.md` to translate each `[N]` marker into a packet-local `source_id` (`src_01`,
   `src_02`, ...), build `report.md`, `sources.yaml`, and `assertion_candidates.yaml`, and route any
   Sources-panel ranking or snippet you want to keep into `extensions.perplexity.*` — never into a
   schema field like `classification`, `producer_confidence`, or `quote`.
4. Compute each file's byte length and sha256, then hand-write `handoff.yaml` per `mapping.md`'s
   template.
5. Place all four files in one directory — that directory is your packet. Hand it to the importer
   (`rf intake external-report`, Phase 5) pointed at a workspace.

**See also**: `../README.md` for the rules shared by every profile, and
`tests/fixtures/external_research_handoff/profiles/perplexity/` for a complete schema-valid example.
