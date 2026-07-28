# External Research Handoff — Producer Profiles (v1)

Five offline, manual producer profiles for the `external_research_handoff/v1` packet contract
(`docs/dev/architecture/external-research-handoff-contract.md`). Every profile maps a different
external research assistant's real output shape onto the exact same four required packet files —
`handoff.yaml`, `report.md`, `sources.yaml`, `assertion_candidates.yaml` — plus the same optional
members (`activity.yaml`, attachments). No profile invents a second packet shape; only the mapping
from platform-native output to that one shape differs.

| Profile | Platform shape it maps | Offline boundary |
|---|---|---|
| [`generic/`](generic/) | Any assistant without a dedicated profile below | Fully manual |
| [`chatgpt/`](chatgpt/) | ChatGPT Deep Research (web UI), incl. `citeturn…`/`fileciteturn…` markers | Manual copy/paste; no API/session scraping |
| [`perplexity/`](perplexity/) | Perplexity citations + search-result cards | Manual copy/paste; no API |
| [`gemini/`](gemini/) | Gemini answer spans + grounding/source references | Manual copy/paste; no Google API coupling |
| [`notebooklm/`](notebooklm/) | NotebookLM notebook synthesis + source export | Manual, deterministic, `offline-unvalidated` |

## Rules every profile shares

1. **`content_role` is fixed.** `report.md` is always `content_role: platform_synthesis`. It is a
   candidate research artifact, never verified evidence, and it can never be fed into a source-card,
   claim, or assertion writer (contract §4.1).
2. **No invented locators, dates, authors, quotations, or verified labels.** Every prompt in this
   directory instructs the operator/platform to write `null`/`unknown` rather than fabricate a
   plausible value. This is a hard rule, not a style suggestion.
3. **No provider credential, SDK, live endpoint, browser automation, or unofficial API — anywhere.**
   Every profile here is a human-driven copy/paste workflow. None of them call a vendor API, drive a
   browser, or read a live session.
4. **Producer-declared completeness/classification can never set computed or verified state.**
   `classification` (`assertion`/`inference`/`annotation`), `producer_confidence`, `direction`, and any
   platform-specific ranking are non-authoritative hints. Only Research Foundry's own importer computes
   a completeness tier (`locator_only`/`source_resolved`/`passage_resolved`/`verified`), and only its
   existing verifier/materializer can ever assign `verified` (contract §2.1, §2.4.1).
5. **Vendor ranking/confidence is non-authoritative metadata only.** A platform's own result ranking,
   relevance score, or confidence label is stored — if at all — inside a namespaced `extensions`
   object, and never by itself influences import behavior.
6. **Every field, including everything inside `extensions`, is untrusted data.** It may be stored and
   displayed through bounded, escaped surfaces, but it is never promoted into a prompt, a tool/resource
   description, a route/control value, a command, a schema selector, a filesystem path, or an execution
   argument — no matter how convincingly a value is shaped (contract §4.1). See
   `tests/fixtures/external_research_handoff/profiles/injection/` for a fixture that exercises this
   rule directly, and `tests/unit/test_external_research_profiles.py` for the proof.

## Directory layout

```
templates/external_research_handoff/v1/
├── README.md              # this file
├── generic/
│   ├── prompt.md           # operator-pasteable prompt
│   ├── mapping.md          # output -> packet-member mapping, templates, unknown-field rules
│   └── README.md           # what this is / offline boundary / how to produce a packet
├── chatgpt/    (same three files)
├── perplexity/ (same three files)
├── gemini/     (same three files)
└── notebooklm/ (same three files)
```

Corresponding schema-valid example packets live under
`tests/fixtures/external_research_handoff/profiles/<profile>/`, one per profile plus an
`injection/` fixture whose string values imitate common injection attacks to prove they survive as
inert, escaped data.
