---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_pipeline_architecture_best_ingests_outputs
title: 'Unified AI Research-Capture Harness: Pipeline Architecture'
intent_id: intent_research_20260614_what_pipeline_architecture_best_ingests_outputs
evidence_bundle_id: pending
created_at: '2026-06-14T17:13:01-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Unified AI Research-Capture Harness: Pipeline Architecture

## Executive summary

The recommended architecture is a three-stage pipe (per-tool export adapter -> a single intermediate normalized record -> an idempotent RF intake stage), because three of the four tools (OpenAI, Perplexity, Gemini) already emit structurally equivalent span-to-source citation objects that collapse cleanly onto one schema while NotebookLM needs a separate degrade path. **Inference:** [claim:clm_inf01]
The single highest-leverage normalization primitive is the (span -> source) citation tuple, because OpenAI annotations, Gemini groundingSupports, and Perplexity search_results all reduce to it, so building the adapter layer around that one tuple type lets a new tool be onboarded by writing only a thin field-mapping rather than a new pipeline. **Inference:** [claim:clm_inf15]
Each tool's native span-to-source structure maps deterministically onto one RF claim with sources[{source_card_id, evidence_id, relation, locator}]: OpenAI annotation -> one source entry per annotation, Gemini groundingSupport -> one entry per groundingChunkIndex, Perplexity -> one entry per search_results object, so the RF claim ledger is the correct convergence target for all four feeds. **Inference:** [claim:clm_inf05]
The normalization boundary should live in a standalone RF intake stage (not in a MeatyWiki connector), because RF's determinism-by-default contract and its source_card/extraction_card/claim_ledger/evidence_bundle chain already define the canonical normalized form, and pushing normalization downstream into MeatyWiki would duplicate that schema and lose per-claim attribution before the claim ledger is built. **Inference:** [claim:clm_inf09]
On attribution fidelity, OpenAI and Gemini are the highest-fidelity sources because both return machine-readable span-level citations (character/byte offsets mapped to url+title), Perplexity is high but list-level (per-response source set, not per-sentence offsets via the documented fields), and NotebookLM is the lowest because quote-span availability is an unresolved open question. **Inference:** [claim:clm_inf04]
RF should build the OpenAI and Perplexity adapters first, Gemini grounding second, and defer the Gemini Deep Research Agent and NotebookLM adapters, because development effort tracks inversely with API stability and the first three deliver the bulk of high-fidelity, deduplicatable, automatable citations. **Inference:** [claim:clm_inf16]

## Export surface evidence by tool

### OpenAI (ChatGPT / Deep Research)

OpenAI's deep research API exposes two models, o3-deep-research and o4-mini-deep-research, that synthesize many sources into a comprehensive research-analyst-level report via the Responses API. [claim:clm_060]
OpenAI exposes two dated Deep Research models via the responses endpoint: o3-deep-research-2025-06-26 (in-depth synthesis, higher quality) and o4-mini-deep-research-2025-06-26 (lightweight, faster, latency-sensitive). [claim:clm_054]
A Deep Research request requires the web_search_preview tool and can optionally add code_interpreter (with a container) for data parsing and chart generation. [claim:clm_059]
Responses contain typed output items including web_search_call (with an action like search/open_page/find_in_page), code_interpreter_call, mcp_tool_call, file_search_call, and message (the final answer with inline citations). [claim:clm_062]
All intermediate agent steps are stored in response.output, where the type field identifies each step kind (reasoning, web_search_call, code_interpreter_call), enabling debugging and tracing of how the answer was constructed. [claim:clm_056]
The deep research output array lists the web search calls, code interpreter calls, and remote MCP calls the model made to reach its answer, so consumers can inspect the full research trajectory. [claim:clm_061]
The message output item carries the model's final answer along with the inline citations. [claim:clm_063]
The final report is the last item in the output list, accessed as response.output[-1].content[0].text, while annotations live at response.output[-1].content[0].annotations. [claim:clm_057]
Each inline citation is an annotation object on the message output_text carrying url, title, start_index, and end_index fields, where start_index/end_index are integer character offsets locating the cited span in the answer text. [claim:clm_064]
Each citation annotation returned in the response carries start_index/end_index (the character span the citation refers to), a title, and the full source url. [claim:clm_055]
OpenAI directs that inline citations from web results be rendered as clearly visible, clickable links in the consuming UI. [claim:clm_065]
Deep Research models and the Responses API support MCP-based tools, letting the model query private knowledge stores or third-party services in addition to web search and code execution. [claim:clm_058]
OpenAI announced that deep research reports can now be exported as well-formatted PDFs that include tables, images, linked citations, and sources. [claim:clm_050]
The export path is to click the share icon and select 'Download as PDF.'. [claim:clm_051]
The PDF export works for both newly generated and previously created (past) deep research reports. [claim:clm_052]
OpenAI introduced the PDF export feature for Deep Research reports on May 12, 2025, with availability reported for ChatGPT Plus, Team, and Pro subscribers. [claim:clm_053]
OpenAI Deep Research's PDF export is unsuitable as the primary ingestion surface and should be used only as a human-readable fallback, because the API path (response.output[-1] message with annotations carrying url/title/start_index/end_index) preserves structured per-span citations that a flattened PDF loses. **Inference:** [claim:clm_inf11]

### Perplexity (Sonar)

The model field selects which Sonar model to use, with allowed enum values sonar, sonar-pro, sonar-deep-research, and sonar-reasoning-pro. [claim:clm_020]
The Chat Completions response includes a top-level citations field that is an array of source URLs used to generate the response. [claim:clm_016]
Perplexity has fully deprecated and removed the citations field; all applications must migrate to the search_results field, which carries richer per-source detail (titles, URLs, publication dates). [claim:clm_066]
The response also returns a search_results field, an array of objects giving the search results used for context in the response. [claim:clm_017]
The search_results field was added to the JSON response object to give applications direct, transparent access to the search results the models actually used. [claim:clm_068]
Each entry in Perplexity's search_results field exposes a title, url, and date, giving URL+title pairs that map onto RF's source.locator.url and source.title fields. [claim:clm_067]
Each search_results object carries per-source provenance via a date (publication date) and last_updated field, which supports dedup and freshness logic. [claim:clm_018]
Each search result includes a source field identifying whether the result came from the web or from an attachment. [claim:clm_019]
Each search result object exposes a snippet field containing a text excerpt from the search result page. [claim:clm_021]
Perplexity API responses now include detailed per-request cost information, usable for CCDash-style ingest-cost telemetry. [claim:clm_069]
The per-request cost structure breaks cost into input_tokens_cost, output_tokens_cost, request_cost, and total_cost fields. [claim:clm_070]
Perplexity maintains OpenAI compatibility: the /v1/responses path continues to work as an OpenAI-compat alias and a GET /v1/models endpoint lists models in OpenAI-compatible format, so response normalization can share the OpenAI envelope. [claim:clm_071]

### NotebookLM

NotebookLM has no documented REST API, so both the CLI and the skill drive browser/OAuth automation and the integration wraps the notebooklm CLI as a subprocess rather than HTTP. [claim:clm_009]
The integration wraps the notebooklm-py CLI at version v0.3.2, which provides notebook/source/artifact ops, OAuth, and --json machine output. [claim:clm_015]
Reliable NLM surfaces are notebooks, sources, chat, mind-map, report, and data-table, while audio, video, quiz, flashcards, infographic, and slide-deck are rate-limited 'may fail' surfaces needing retry and a degrade path. [claim:clm_013]
Whether `notebooklm source fulltext --json` yields quote spans good enough for extracted_points[].quote, versus only summaries, is an open question that gates evidence fidelity for the sourcing path. [claim:clm_012]
NLM output is treated as exactly one of two things — a source that earns a source_card and a claim-eligible evidence trail, or a non-authoritative artifact that never enters the report body as an untagged material claim. [claim:clm_010]
All NLM-derived source cards carry usage.requires_network: true and a reliability note because the output is non-reproducible, making the offline-first exception explicit rather than silent. [claim:clm_011]
The integration philosophy mandates writing a deterministic on-disk artifact first, gating the live network call behind available(), degrading silently, and never letting NLM-authored prose enter a report body without a claim id. [claim:clm_014]
An Audio Overview is exported from NotebookLM via a Download control in the audio player, with no file-format specified in the article. [claim:clm_072]
NotebookLM Audio Overviews offer four selectable formats: Deep Dive (default), The Brief, The Critique, and The Debate. [claim:clm_073]
Audio Overviews can be generated in more than 80 languages, defaulting to the Google Account's preferred language. [claim:clm_074]
Generating or deleting an Audio Overview requires edit access to the notebook. [claim:clm_075]
Public notebook sharing of Audio Overviews is limited to consumer accounts and is disabled for Workspace Enterprise or Education accounts. [claim:clm_076]
Interactive mode is currently English-only, and the user's voice and transcribed interactions with the hosts are not stored or shared. [claim:clm_077]
Audio Overview voices are AI-generated and may contain inaccuracies or audio glitches, and generation can take a couple of minutes. [claim:clm_078]

### Gemini (Grounding / Deep Research Agent)

The groundingMetadata.groundingChunks field is an array of objects, each carrying a web source's uri and title. [claim:clm_038]
Each grounding chunk's web object carries a uri (string source URL) and a title (string page title), used to provide a link to the source of the information. [claim:clm_044]
The groundingSupports array connects model response text to the sources listed in groundingChunks. [claim:clm_039]
Each grounding support links a text segment defined by startIndex and endIndex to one or more groundingChunkIndices, which is the basis for building inline citations. [claim:clm_040]
A GroundingSupport.segment carries byte-measured startIndex (inclusive) and endIndex (exclusive) marking the span of content the support applies to. [claim:clm_047]
GroundingSupport.groundingChunkIndices is an integer array indexing into the GroundingMetadata.groundingChunks field, specifying which chunks support the claim in a content segment. [claim:clm_045]
The docs give a concrete example that groundingChunkIndices values [1, 3] mean groundingChunks[1] and groundingChunks[3] are the sources for that segment's claim, evidencing the index->chunk->URL citation pattern. [claim:clm_049]
confidenceScores is a float array parallel to groundingChunkIndices giving per-reference confidence (0.0-1.0) that the chunk supports the claim; for Gemini 2.5+ it is empty and should be ignored. [claim:clm_046]
GroundingMetadata also returns webSearchQueries (the web search queries used), a searchEntryPoint for displaying search results, and retrievalMetadata about the retrieval grounding source. [claim:clm_048]
The searchEntryPoint field contains the HTML and CSS needed to render the required Search Suggestions, with full usage requirements specified in the Terms of Service. [claim:clm_041]
Older Gemini models use a google_search_retrieval tool, whereas all current models use the google_search tool to enable grounding. [claim:clm_043]
For Gemini 3 models, the project is billed for each individual search query the model decides to execute during grounding. [claim:clm_042]
The Deep Research agent ships in two preview versions with model IDs deep-research-preview-04-2026 (speed/efficiency) and deep-research-max-preview-04-2026 (maximum comprehensiveness). [claim:clm_022]
The agent autonomously plans, executes, and synthesizes multi-step research tasks, navigating complex information to produce detailed, cited reports. [claim:clm_023]
The Gemini Deep Research Agent is currently in preview and is accessible exclusively through the Interactions API, not generate_content. [claim:clm_028]
By default the agent has access to Google Search, URL Context, and Code Execution, and can be extended with MCP servers and File Search over uploaded corpora. [claim:clm_029]
The API returns a partial Interaction object immediately with an id for polling; the interaction state transitions from in_progress to completed or failed. [claim:clm_024]
Polling the interaction yields status, output_text (the final report), and error fields, accessed via interaction.status, interaction.output_text, and interaction.error. [claim:clm_025]
The Interaction exposes a steps array of typed steps (e.g. model_output) whose content holds typed items such as text and image. [claim:clm_026]
Because the agent may encounter malicious web pages, Google recommends reviewing the citations provided in the response to verify the sources. [claim:clm_027]

## Per-tool export-capability matrix

| Tool | Primary export format | Stability tier | Attribution fidelity | Evidence |
|------|----------------------|----------------|----------------------|----------|
| OpenAI Deep Research | Responses API output array; message annotations with url/title/char offsets; PDF as human fallback | Tier-1 GA, fully scriptable | Highest — machine-readable span-level char-offset citations | [claim:clm_inf11] |
| Perplexity Sonar | Chat Completions JSON; search_results (title/url/date/snippet); OpenAI-compat envelope | Tier-1 GA, fully scriptable | High but list-level — per-response source set, not per-sentence offsets | [claim:clm_inf04] |
| Gemini grounding | REST groundingMetadata (groundingChunks + byte-offset groundingSupports) | Tier-1 stable REST schema | Highest — machine-readable byte-offset span-to-source binding | [claim:clm_inf03] |
| Gemini Deep Research Agent | Interactions API only (preview), output_text + steps | Tier-2 preview, Interactions-API-only | Cited reports via Interactions API polling | [claim:clm_inf03] |
| NotebookLM | notebooklm-py CLI v0.3.2 subprocess; no REST API; browser/OAuth automation | Tier-3, least automatable | Lowest — quote-span fidelity is an unresolved open question | [claim:clm_inf03] |

Per-tool automation tiering ranks OpenAI Deep Research and Perplexity Sonar as Tier-1 (stable, GA, API-backed, fully scriptable), Gemini grounding as Tier-1 but its Deep Research Agent as Tier-2 (preview/Interactions-API-only), and NotebookLM as Tier-3 (no REST API, browser/OAuth/CLI automation only). **Inference:** [claim:clm_inf03]

## RF artifact-chain target

A source_card carries front matter with source{title, source_type, locator (url|file_path|doi|repo), accessed_at}, a trust block, a usage block, and an extracted_points list, each point having an evidence_id (ev_001..), a locator, a summary, and a short quote. [claim:clm_030]
The source_type enum is official_doc|paper|standard|repo|news|blog|book|personal_note|internal_doc|other, and source_rank defaults to unknown when a card is ingested deterministically. [claim:clm_031]
An extraction_card derives extracted_facts from the source card's extracted_points, where each ev_ becomes a fact with {evidence_id, text, locator, confidence: medium, quote_available}, and pulls contradictions_or_cautions from source Limitations or conflicts. [claim:clm_032]
The claim ledger maps each extracted fact to a claim whose sources list entries of {source_card_id, evidence_id, relation: supports, locator}, giving RF a native per-claim source-attribution model with a status field. [claim:clm_033]
Each claim carries a status drawn from supported|inference|speculation|unsupported, and the claim ledger also records contradiction and inference logs alongside unresolved_questions. [claim:clm_037]
build_bundle assembles an evidence_bundle.yaml referencing all run artifacts plus counts (source_cards, extraction_cards, claims_total and claims by status), and sets governance.approved_for_writeback only when verification passes. [claim:clm_034]
Determinism is the default: the standard execution path must not require network or API keys; anything LLM or network is opt-in via an llm flag or adapter availability and degrades to deterministic behavior. [claim:clm_035]
Deterministic ingestion splits available content into up to 8 key points (evidence_id ev_001.., locator para/N, summary, and a quote when short); a degraded fetch yields a single placeholder point flagged needs_content. [claim:clm_036]

## Intermediate normalized schema

The intermediate normalized citation record should be {span:{start,end,unit}, source:{url,title,published_at,source_type,tool,model,captured_at}, relation, confidence}, with a unit field set to 'char' for OpenAI/Perplexity and 'byte' for Gemini, because the two API families measure offsets in different units and a pipeline that hard-codes one will mis-slice the other's spans. **Inference:** [claim:clm_inf02]

| Normalized field | OpenAI source | Perplexity source | Gemini source | Evidence |
|------------------|---------------|-------------------|---------------|----------|
| span.start / span.end | annotation start_index / end_index (char) | not exposed per-sentence | groundingSupports segment startIndex / endIndex (byte) | [claim:clm_inf02] |
| span.unit | char | char | byte | [claim:clm_inf02] |
| source.url | annotation url | search_results.url | groundingChunks.web.uri | [claim:clm_inf05] |
| source.title | annotation title | search_results.title | groundingChunks.web.title | [claim:clm_inf05] |
| source.published_at | not exposed | search_results.date | not exposed | [claim:clm_inf07] |
| relation -> RF claim sources[] | one entry per annotation | one entry per search_results object | one entry per groundingChunkIndex | [claim:clm_inf05] |

Provenance metadata should be modeled on the C2PA Manifest pattern (assertions + a single signed claim + signature), recording tool, model, and captured_at as a 'gathered' assertion distinct from the original publisher citation, so that RF preserves the distinction between what a tool synthesized and what it merely relayed. **Inference:** [claim:clm_inf06]

### Provenance vocabulary borrowed from C2PA

A C2PA Manifest is the provenance information for an asset, composed of one or more assertions (including content bindings), a single claim, and a claim signature. [claim:clm_001]
A Claim is a digitally signed, tamper-evident data structure that references the set of assertions about an asset along with the content-binding information. [claim:clm_002]
Claim v2 split the single assertions list into created_assertions and gathered_assertions, clarifying their roles within the C2PA Trust Model. [claim:clm_003]
The claim generator is the non-human (hardware or software) actor that produces both the claim and the claim signature for an asset. [claim:clm_004]
Version 2.4 (April 2026) introduced a new c2pa.ai-disclosure assertion providing machine-readable AI transparency information. [claim:clm_005]
AI/ML provenance is recorded via the digitalSourceType field, with values such as the URI for trainedAlgorithmicData replacing the earlier c2pa.trainedAlgorithmicData token. [claim:clm_006]
Hard bindings are cryptographic hashes that uniquely identify the asset (or a portion of it), enabling tamper detection at the bit level. [claim:clm_007]
Soft bindings are content identifiers that are not statistically unique (a fingerprint) or are embedded as an invisible watermark, allowing matching of derived content even when bits differ. [claim:clm_008]

## Deduplication and provenance-preservation strategy

Deduplication should key on the resolved source URL plus publication date (a C2PA-style 'hard binding'), falling back to a title+snippet similarity 'soft binding' when URLs differ but content is the same, because Perplexity and Gemini both expose URL+date while only snippets/titles survive when a tool relays a source it did not directly link. **Inference:** [claim:clm_inf07]
Gemini's vertexaisearch.cloud.google.com redirect URIs must be resolved to their true publisher URLs inside the intake adapter before dedup, otherwise every Gemini-sourced citation will appear as a distinct google.com redirect and silently defeat URL-keyed deduplication against OpenAI and Perplexity citations of the same page. **Inference:** [claim:clm_inf14]
Worked dedup example: when ChatGPT cites https://example.com/x (start_index/end_index span) and Perplexity returns the same url with a date, RF should merge them into one source_card but keep two evidence entries (ev for the OpenAI span, ev for the Perplexity snippet), so the merged card preserves both tools' provenance without dropping either attribution. **Inference:** [claim:clm_inf08]
When a tool summarizes sources it does not directly cite (e.g. NotebookLM, or Perplexity's response-level source set), attribution should be preserved by labeling those evidence entries relation: supports with confidence: medium and flagging requires_network/needs_content, never promoting them to a tagged material claim, matching RF's rule that non-reproducible AI prose never enters a report body without a claim id. **Inference:** [claim:clm_inf13]

## Recommendations and decision rules

The normalization boundary should live in a standalone RF intake stage (not in a MeatyWiki connector), because RF's determinism-by-default contract and its source_card/extraction_card/claim_ledger/evidence_bundle chain already define the canonical normalized form, and pushing normalization downstream into MeatyWiki would duplicate that schema and lose per-claim attribution before the claim ledger is built. **Inference:** [claim:clm_inf09]
Idempotent re-import should hash the resolved (url, published_at) of each citation plus a per-session capture key into a stable source_card_id, so re-capturing the same ChatGPT/Perplexity/Gemini session updates existing cards in place rather than creating duplicates, mirroring RF's deterministic ingestion contract. **Inference:** [claim:clm_inf10]
Ingest-cost telemetry should be sourced primarily from Perplexity's per-request cost fields and Gemini's per-search-query billing, because those two tools expose machine-readable cost signals (input/output/request/total and per-query charges) while OpenAI Deep Research and NotebookLM require external cost estimation. **Inference:** [claim:clm_inf12]
RF should build the OpenAI and Perplexity adapters first, Gemini grounding second, and defer the Gemini Deep Research Agent and NotebookLM adapters, because development effort tracks inversely with API stability and the first three deliver the bulk of high-fidelity, deduplicatable, automatable citations. **Inference:** [claim:clm_inf16]

## Speculative outlook

Within roughly 6-12 months the four tools are likely to converge on C2PA-style machine-readable provenance assertions (following Gemini's grounding offsets and the v2.4 c2pa.ai-disclosure assertion), at which point RF's intermediate schema could ingest a signed provenance manifest directly and retire most per-tool field-mapping adapters. **Speculation:** [claim:clm_spec01]
NotebookLM is likely to remain the weakest ingestion link for the foreseeable future and RF should plan for its browser/CLI automation to break on UI changes, treating any NLM-sourced card as a non-reproducible, network-dependent artifact rather than a stable evidence source. **Speculation:** [claim:clm_spec02]

## Open questions

- Whether `notebooklm source fulltext --json` yields quote spans good enough for extracted_points[].quote, versus only summaries, gating evidence fidelity for the NotebookLM sourcing path?

## Sources

- src_20260614_rib053_07: C2PA Technical Specification (Content Credentials) v2.4
- src_20260614_rib053_06: NotebookLM Integration — Sourcing, Reports, Extended Runs, Upload-Back (RF local plan)
- src_20260614_rib053_02: Chat Completions | Perplexity Sonar API Reference
- src_20260614_rib053_04: Gemini Deep Research Agent | Gemini API
- src_20260614_rib053_11: Research Foundry — Service API & Artifact Contract
- src_20260614_rib053_03: Grounding with Google Search | Gemini API
- src_20260614_rib053_08: GroundingMetadata | REST Resource | Vertex AI / Gemini Enterprise Agent Platform REST API reference (v1beta1)
- src_20260614_rib053_01: OpenAI (X/Twitter): deep research reports now exportable as well-formatted PDFs
- src_20260614_rib053_09: Introduction to deep research in the OpenAI API
- src_20260614_rib053_00: Deep research | OpenAI API
- src_20260614_rib053_10: Perplexity API Changelog
- src_20260614_rib053_05: Generate Audio Overview in NotebookLM
