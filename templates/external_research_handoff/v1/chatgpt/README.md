# ChatGPT Producer Profile

**What this is**: the `external_research_handoff/v1` producer profile for **ChatGPT Deep Research**
(web UI). It maps ChatGPT's real output shape — a prose report plus a candidate-pattern table with
inline vendor citation markers (`citeturn21search1`, `fileciteturn0file0`, `turn0search0`, and similar)
— onto the same four required packet files every other profile produces. See `../generic/README.md`
for the platform-agnostic fallback this profile specializes.

**Offline/manual boundary**: fully manual copy/paste. You paste `prompt.md` into a ChatGPT Deep
Research session in the web UI, copy the assistant's response by hand, and build the four packet
files yourself following `mapping.md`. No OpenAI API key, SDK, session file, or browser automation is
used or assumed anywhere in this workflow.

**Standout detail**: ChatGPT Deep Research responses carry opaque inline citation markers that are UI
rendering artifacts, not resolvable locators. `mapping.md` documents exactly how to keep those markers
out of `sources.yaml`'s `locator` fields and `assertion_candidates.yaml`'s `selector` field, and where
they may safely be preserved (a namespaced `extensions.chatgpt.vendor_citation_markers` array, and
inline within `report.md`'s own prose) — read that section before transcribing anything.

**How to produce a packet**:

1. Paste `prompt.md` into a ChatGPT Deep Research session.
2. Copy its prose report, sources list, and candidate table.
3. Follow `mapping.md` to build `report.md`, `sources.yaml`, and `assertion_candidates.yaml` —
   stripping every inline `citeturn`/`filecite`/`turn` marker out of locator/selector fields as you go
   (they may only land in `extensions.chatgpt` or stay inline in `report.md`'s prose).
4. Compute each file's byte length and sha256, then hand-write `handoff.yaml` per `mapping.md`'s
   template (`producer_profile: chatgpt`).
5. Place all four files in one directory — that directory is your packet. Hand it to the importer
   (`rf intake external-report`, Phase 5) pointed at a workspace.

**See also**: `../README.md` for the rules shared by every profile, and
`tests/fixtures/external_research_handoff/profiles/chatgpt/` for a complete schema-valid example.
