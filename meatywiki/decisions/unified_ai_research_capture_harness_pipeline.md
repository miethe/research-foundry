---
id: mwb_20260622_dr_unified_ai_research_capture_harness
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_pipeline_architect
target_page: meatywiki/decisions/unified_ai_research_capture_harness_pipeline.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_pipeline_architecture_best_ingests_outputs: OpenAI
  annotations (url/title/start_index/end_index), Gemini groundingSupports (byte segment -> chunk indices
  -> uri/tit'
key_claims:
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf14
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_055
  - clm_064
  - clm_040
  - clm_045
  - clm_047
  - clm_067
  - clm_009
  - clm_030
  - clm_033
  - clm_035
  - clm_018
  - clm_001
  - clm_002
  - clm_003
  - clm_006
  - clm_044
  - clm_007
  - clm_008
  - clm_021
  - clm_036
  - clm_032
  - clm_034
  - clm_010
  - clm_011
  - clm_014
  - clm_012
  - clm_049
  - clm_062
  - clm_048
  - clm_060
  - clm_066
  - clm_038
  - clm_028
  - clm_071
  - clm_054
  - clm_022
  - clm_015
  - clm_050
  - clm_057
  - clm_061
  - clm_069
  - clm_070
  - clm_042
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Unified AI Research-Capture Harness: Pipeline Architecture

## Context

- A C2PA Manifest is the provenance information for an asset, composed of one or more assertions (including content bindings), a single claim, and a claim signature. [claim:clm_001]
- A Claim is a digitally signed, tamper-evident data structure that references the set of assertions about an asset along with the content-binding information. [claim:clm_002]
- Claim v2 split the single assertions list into created_assertions and gathered_assertions, clarifying their roles within the C2PA Trust Model. [claim:clm_003]
- The claim generator is the non-human (hardware or software) actor that produces both the claim and the claim signature for an asset. [claim:clm_004]
- Version 2.4 (April 2026) introduced a new c2pa.ai-disclosure assertion providing machine-readable AI transparency information. [claim:clm_005]
- AI/ML provenance is recorded via the digitalSourceType field, with values such as the URI for trainedAlgorithmicData replacing the earlier c2pa.trainedAlgorithmicData token. [claim:clm_006]
- Hard bindings are cryptographic hashes that uniquely identify the asset (or a portion of it), enabling tamper detection at the bit level. [claim:clm_007]
- Soft bindings are content identifiers that are not statistically unique (a fingerprint) or are embedded as an invisible watermark, allowing matching of derived content even when bits differ. [claim:clm_008]
- NotebookLM has no documented REST API, so both the CLI and the skill drive browser/OAuth automation and the integration wraps the notebooklm CLI as a subprocess rather than HTTP. [claim:clm_009]
- NLM output is treated as exactly one of two things — a source that earns a source_card and a claim-eligible evidence trail, or a non-authoritative artifact that never enters the report body as an untagged material claim. [claim:clm_010]
- All NLM-derived source cards carry usage.requires_network: true and a reliability note because the output is non-reproducible, making the offline-first exception explicit rather than silent. [claim:clm_011]
- Whether `notebooklm source fulltext --json` yields quote spans good enough for extracted_points[].quote, versus only summaries, is an open question that gates evidence fidelity for the sourcing path. [claim:clm_012]
- Reliable NLM surfaces are notebooks, sources, chat, mind-map, report, and data-table, while audio, video, quiz, flashcards, infographic, and slide-deck are rate-limited 'may fail' surfaces needing retry and a degrade path. [claim:clm_013]
- The integration philosophy mandates writing a deterministic on-disk artifact first, gating the live network call behind available(), degrading silently, and never letting NLM-authored prose enter a report body without a claim id. [claim:clm_014]
- The integration wraps the notebooklm-py CLI at version v0.3.2, which provides notebook/source/artifact ops, OAuth, and --json machine output. [claim:clm_015]
- The Chat Completions response includes a top-level citations field that is an array of source URLs used to generate the response. [claim:clm_016]
- The response also returns a search_results field, an array of objects giving the search results used for context in the response. [claim:clm_017]
- Each search_results object carries per-source provenance via a date (publication date) and last_updated field, which supports dedup and freshness logic. [claim:clm_018]
- Each search result includes a source field identifying whether the result came from the web or from an attachment. [claim:clm_019]
- The model field selects which Sonar model to use, with allowed enum values sonar, sonar-pro, sonar-deep-research, and sonar-reasoning-pro. [claim:clm_020]
- Each search result object exposes a snippet field containing a text excerpt from the search result page. [claim:clm_021]
- The Deep Research agent ships in two preview versions with model IDs deep-research-preview-04-2026 (speed/efficiency) and deep-research-max-preview-04-2026 (maximum comprehensiveness). [claim:clm_022]
- The agent autonomously plans, executes, and synthesizes multi-step research tasks, navigating complex information to produce detailed, cited reports. [claim:clm_023]
- The API returns a partial Interaction object immediately with an id for polling; the interaction state transitions from in_progress to completed or failed. [claim:clm_024]
- Polling the interaction yields status, output_text (the final report), and error fields, accessed via interaction.status, interaction.output_text, and interaction.error. [claim:clm_025]
- The Interaction exposes a steps array of typed steps (e.g. model_output) whose content holds typed items such as text and image. [claim:clm_026]
- Because the agent may encounter malicious web pages, Google recommends reviewing the citations provided in the response to verify the sources. [claim:clm_027]
- The Gemini Deep Research Agent is currently in preview and is accessible exclusively through the Interactions API, not generate_content. [claim:clm_028]
- By default the agent has access to Google Search, URL Context, and Code Execution, and can be extended with MCP servers and File Search over uploaded corpora. [claim:clm_029]
- A source_card carries front matter with source{title, source_type, locator (url|file_path|doi|repo), accessed_at}, a trust block, a usage block, and an extracted_points list, each point having an evidence_id (ev_001..), a locator, a summary, and a short quote. [claim:clm_030]
- The source_type enum is official_doc|paper|standard|repo|news|blog|book|personal_note|internal_doc|other, and source_rank defaults to unknown when a card is ingested deterministically. [claim:clm_031]
- An extraction_card derives extracted_facts from the source card's extracted_points, where each ev_ becomes a fact with {evidence_id, text, locator, confidence: medium, quote_available}, and pulls contradictions_or_cautions from source Limitations or conflicts. [claim:clm_032]
- The claim ledger maps each extracted fact to a claim whose sources list entries of {source_card_id, evidence_id, relation: supports, locator}, giving RF a native per-claim source-attribution model with a status field. [claim:clm_033]
- build_bundle assembles an evidence_bundle.yaml referencing all run artifacts plus counts (source_cards, extraction_cards, claims_total and claims by status), and sets governance.approved_for_writeback only when verification passes. [claim:clm_034]
- Determinism is the default: the standard execution path must not require network or API keys; anything LLM or network is opt-in via an llm flag or adapter availability and degrades to deterministic behavior. [claim:clm_035]
- Deterministic ingestion splits available content into up to 8 key points (evidence_id ev_001.., locator para/N, summary, and a quote when short); a degraded fetch yields a single placeholder point flagged needs_content. [claim:clm_036]
- Each claim carries a status drawn from supported|inference|speculation|unsupported, and the claim ledger also records contradiction and inference logs alongside unresolved_questions. [claim:clm_037]
- The groundingMetadata.groundingChunks field is an array of objects, each carrying a web source's uri and title. [claim:clm_038]
- The groundingSupports array connects model response text to the sources listed in groundingChunks. [claim:clm_039]
- Each grounding support links a text segment defined by startIndex and endIndex to one or more groundingChunkIndices, which is the basis for building inline citations. [claim:clm_040]
- The searchEntryPoint field contains the HTML and CSS needed to render the required Search Suggestions, with full usage requirements specified in the Terms of Service. [claim:clm_041]
- For Gemini 3 models, the project is billed for each individual search query the model decides to execute during grounding. [claim:clm_042]
- Older Gemini models use a google_search_retrieval tool, whereas all current models use the google_search tool to enable grounding. [claim:clm_043]
- Each grounding chunk's web object carries a uri (string source URL) and a title (string page title), used to provide a link to the source of the information. [claim:clm_044]
- GroundingSupport.groundingChunkIndices is an integer array indexing into the GroundingMetadata.groundingChunks field, specifying which chunks support the claim in a content segment. [claim:clm_045]
- confidenceScores is a float array parallel to groundingChunkIndices giving per-reference confidence (0.0-1.0) that the chunk supports the claim; for Gemini 2.5+ it is empty and should be ignored. [claim:clm_046]
- A GroundingSupport.segment carries byte-measured startIndex (inclusive) and endIndex (exclusive) marking the span of content the support applies to. [claim:clm_047]
- GroundingMetadata also returns webSearchQueries (the web search queries used), a searchEntryPoint for displaying search results, and retrievalMetadata about the retrieval grounding source. [claim:clm_048]
- The docs give a concrete example that groundingChunkIndices values [1, 3] mean groundingChunks[1] and groundingChunks[3] are the sources for that segment's claim, evidencing the index->chunk->URL citation pattern. [claim:clm_049]
- OpenAI announced that deep research reports can now be exported as well-formatted PDFs that include tables, images, linked citations, and sources. [claim:clm_050]
- The export path is to click the share icon and select 'Download as PDF.' [claim:clm_051]
- The PDF export works for both newly generated and previously created (past) deep research reports. [claim:clm_052]
- OpenAI introduced the PDF export feature for Deep Research reports on May 12, 2025, with availability reported for ChatGPT Plus, Team, and Pro subscribers. [claim:clm_053]
- OpenAI exposes two dated Deep Research models via the responses endpoint: o3-deep-research-2025-06-26 (in-depth synthesis, higher quality) and o4-mini-deep-research-2025-06-26 (lightweight, faster, latency-sensitive). [claim:clm_054]
- Each citation annotation returned in the response carries start_index/end_index (the character span the citation refers to), a title, and the full source url. [claim:clm_055]
- All intermediate agent steps are stored in response.output, where the type field identifies each step kind (reasoning, web_search_call, code_interpreter_call), enabling debugging and tracing of how the answer was constructed. [claim:clm_056]
- The final report is the last item in the output list, accessed as response.output[-1].content[0].text, while annotations live at response.output[-1].content[0].annotations. [claim:clm_057]
- Deep Research models and the Responses API support MCP-based tools, letting the model query private knowledge stores or third-party services in addition to web search and code execution. [claim:clm_058]
- A Deep Research request requires the web_search_preview tool and can optionally add code_interpreter (with a container) for data parsing and chart generation. [claim:clm_059]
- OpenAI's deep research API exposes two models, o3-deep-research and o4-mini-deep-research, that synthesize many sources into a comprehensive research-analyst-level report via the Responses API. [claim:clm_060]
- The deep research output array lists the web search calls, code interpreter calls, and remote MCP calls the model made to reach its answer, so consumers can inspect the full research trajectory. [claim:clm_061]
- Responses contain typed output items including web_search_call (with an action like search/open_page/find_in_page), code_interpreter_call, mcp_tool_call, file_search_call, and message (the final answer with inline citations). [claim:clm_062]
- The message output item carries the model's final answer along with the inline citations. [claim:clm_063]
- Each inline citation is an annotation object on the message output_text carrying url, title, start_index, and end_index fields, where start_index/end_index are integer character offsets locating the cited span in the answer text. [claim:clm_064]
- OpenAI directs that inline citations from web results be rendered as clearly visible, clickable links in the consuming UI. [claim:clm_065]
- Perplexity has fully deprecated and removed the citations field; all applications must migrate to the search_results field, which carries richer per-source detail (titles, URLs, publication dates). [claim:clm_066]
- Each entry in Perplexity's search_results field exposes a title, url, and date, giving URL+title pairs that map onto RF's source.locator.url and source.title fields. [claim:clm_067]
- The search_results field was added to the JSON response object to give applications direct, transparent access to the search results the models actually used. [claim:clm_068]
- Perplexity API responses now include detailed per-request cost information, usable for CCDash-style ingest-cost telemetry. [claim:clm_069]
- The per-request cost structure breaks cost into input_tokens_cost, output_tokens_cost, request_cost, and total_cost fields. [claim:clm_070]
- Perplexity maintains OpenAI compatibility: the /v1/responses path continues to work as an OpenAI-compat alias and a GET /v1/models endpoint lists models in OpenAI-compatible format, so response normalization can share the OpenAI envelope. [claim:clm_071]
- An Audio Overview is exported from NotebookLM via a Download control in the audio player, with no file-format specified in the article. [claim:clm_072]
- NotebookLM Audio Overviews offer four selectable formats: Deep Dive (default), The Brief, The Critique, and The Debate. [claim:clm_073]
- Audio Overviews can be generated in more than 80 languages, defaulting to the Google Account's preferred language. [claim:clm_074]
- Generating or deleting an Audio Overview requires edit access to the notebook. [claim:clm_075]
- Public notebook sharing of Audio Overviews is limited to consumer accounts and is disabled for Workspace Enterprise or Education accounts. [claim:clm_076]
- Interactive mode is currently English-only, and the user's voice and transcribed interactions with the hosts are not stored or shared. [claim:clm_077]
- Audio Overview voices are AI-generated and may contain inaccuracies or audio glitches, and generation can take a couple of minutes. [claim:clm_078]

## Decision

The recommended architecture is a three-stage pipe (per-tool export adapter -> a single intermediate normalized record -> an idempotent RF intake stage), because three of the four tools (OpenAI, Perplexity, Gemini) already emit structurally equivalent span-to-source citation objects that collapse cleanly onto one schema while NotebookLM needs a separate degrade path. [claim:clm_inf01]

## Rationale

- OpenAI annotations (url/title/start_index/end_index), Gemini groundingSupports (byte segment -> chunk indices -> uri/title), and Perplexity search_results (title/url/date) are all span-or-list-to-source maps that fit one normalized record; NotebookLM has no such API (clm_009), so a per-tool adapter front-end feeding one schema into RF's existing source_card/claim chain (clm_030/clm_033) under determinism-by-default (clm_035) is the minimal viable design. [claim:clm_inf01]
- OpenAI start_index/end_index are integer character offsets (clm_064) while Gemini segment startIndex/endIndex are byte-measured (clm_047); a normalized schema must carry an explicit offset unit to reconcile them, plus url/title (clm_067) and date/published_at (clm_018) to populate source_card source.locator and source.title (clm_030). [claim:clm_inf02]
- C2PA models provenance as assertions bound under one signed claim (clm_001/clm_002) and v2 explicitly separated created_assertions from gathered_assertions (clm_003); applying that split to ingest lets RF tag the AI tool as the gatherer (digitalSourceType-style AI provenance, clm_006) while preserving the underlying source citation as a separate gathered assertion within RF's sources list (clm_033). [claim:clm_inf06]
- Perplexity (clm_067/clm_018) and Gemini (clm_044) expose url plus publication date, giving a stable exact-match dedup key analogous to a C2PA hard binding (clm_007); when only a snippet/title is available (clm_021), a fingerprint-style soft binding (clm_008) is the only reconciliation surface, so the strategy needs both keys. [claim:clm_inf07]
- Because a source_card holds an extracted_points list of many evidence_ids (clm_030/clm_036) and a claim's sources list can reference multiple {source_card_id, evidence_id} pairs (clm_033), merging on the shared URL (clm_064/clm_067) while appending one evidence_id per tool keeps both provenance trails on a single deduplicated card. [claim:clm_inf08]
- RF already owns the normalized artifact chain (source_card clm_030 -> extraction_card clm_032 -> claim ledger clm_033 -> evidence_bundle clm_034) and mandates determinism on the standard path (clm_035); the claim ledger is where per-claim attribution is materialized, so normalization must happen at or before that stage, i.e. inside an RF intake stage, with MeatyWiki receiving the already-normalized evidence_bundle via writeback. [claim:clm_inf09]
- Determinism-by-default (clm_035) and deterministic content splitting (clm_036) imply re-running ingest on identical input must yield identical artifacts; keying source_card identity on the stable url+date that Perplexity/Gemini expose (clm_067/clm_018) and writing it into the source.locator (clm_030) gives a content-addressed id that re-import can match to upsert rather than duplicate. [claim:clm_inf10]
- RF treats NLM output as either a claim-eligible source or a non-authoritative artifact and never lets untagged AI prose enter a report (clm_010/clm_014), flagging requires_network (clm_011); extraction confidence defaults to medium (clm_032); when only a snippet exists (clm_021) or quote fidelity is unproven (clm_012), the safe handling is a medium-confidence supports entry rather than a high-confidence claim. [claim:clm_inf13]
- All three API tools converge on a span-or-response-to-source structure: Gemini segment->chunk indices->uri (clm_040/clm_049), OpenAI span->annotation url (clm_064), Perplexity response->search_results url (clm_067), with auxiliary debug fields (clm_062/clm_048) discardable; designing the adapter contract around this one tuple isolates per-tool variance to a field map. [claim:clm_inf15]
- OpenAI (clm_060) and Perplexity (clm_066, plus OpenAI-compatible envelope clm_071) are GA and share a response shape, lowering adapter cost; Gemini grounding has a stable REST schema (clm_038); the Gemini Deep Research Agent is preview/Interactions-only (clm_028) and NotebookLM has no API (clm_009), so they carry the highest build/maintenance risk and should be sequenced last. [claim:clm_inf16]
- OpenAI (clm_060/clm_054) and Perplexity (clm_066) expose dated, GA Responses/Chat APIs; Gemini grounding has a stable REST GroundingMetadata schema (clm_038/clm_044) but its Deep Research Agent is preview and Interactions-API-only (clm_028/clm_022); NotebookLM has no documented REST API and is driven by a CLI subprocess (clm_009/clm_015), placing it at the least-automatable tier. [claim:clm_inf03]
- OpenAI annotations and Gemini groundingSupports both bind specific text spans to specific sources (clm_064/clm_055/clm_040/clm_049); Perplexity's documented search_results give title/url/date plus a snippet (clm_067/clm_021) but the doc describes a response-level source set rather than per-sentence offset binding (clm_066); NotebookLM fulltext quote-span fidelity is explicitly an open question (clm_012). [claim:clm_inf04]
- RF's per-claim attribution model lists one {source_card_id, evidence_id, relation, locator} entry per supporting source (clm_033/clm_030); OpenAI annotations (clm_064), Gemini chunk indices (clm_045/clm_049), and Perplexity search_results (clm_067) each enumerate the supporting sources for a span/response, giving a direct one-citation-to-one-source-entry mapping. [claim:clm_inf05]
- The PDF export only renders linked citations and sources for human reading (clm_050), whereas the Responses API exposes the final report plus machine-readable annotation offsets (clm_057/clm_064) and the full tool-call trajectory (clm_061); RF deterministic ingestion needs the structured fields, so the API is primary and the PDF is the degrade/needs_content fallback (clm_036). [claim:clm_inf11]
- Perplexity returns input_tokens_cost/output_tokens_cost/request_cost/total_cost (clm_069/clm_070) and Gemini bills per search query (clm_042), both directly capturable; OpenAI Deep Research (clm_060) and NotebookLM (clm_009) expose no equivalent per-response cost field in the cited evidence, so their cost must be estimated, making the two former tools the reliable telemetry anchors. [claim:clm_inf12]
- Gemini groundingChunks carry uri/title (clm_044/clm_038) but the source card notes these are vertexaisearch redirect endpoints; since dedup keys on resolved URL (against Perplexity clm_067 and OpenAI clm_064 publisher URLs), failing to follow the redirect would make identical sources look distinct, so URL resolution is a required adapter step. [claim:clm_inf14]

## Consequences

- The intermediate normalized citation record should be {span:{start,end,unit}, source:{url,title,published_at,source_type,tool,model,captured_at}, relation, confidence}, with a unit field set to 'char' for OpenAI/Perplexity and 'byte' for Gemini, because the two API families measure offsets in different units and a pipeline that hard-codes one will mis-slice the other's spans. [claim:clm_inf02]
- Provenance metadata should be modeled on the C2PA Manifest pattern (assertions + a single signed claim + signature), recording tool, model, and captured_at as a 'gathered' assertion distinct from the original publisher citation, so that RF preserves the distinction between what a tool synthesized and what it merely relayed. [claim:clm_inf06]
- Deduplication should key on the resolved source URL plus publication date (a C2PA-style 'hard binding'), falling back to a title+snippet similarity 'soft binding' when URLs differ but content is the same, because Perplexity and Gemini both expose URL+date while only snippets/titles survive when a tool relays a source it did not directly link. [claim:clm_inf07]
- Worked dedup example: when ChatGPT cites https://example.com/x (start_index/end_index span) and Perplexity returns the same url with a date, RF should merge them into one source_card but keep two evidence entries (ev for the OpenAI span, ev for the Perplexity snippet), so the merged card preserves both tools' provenance without dropping either attribution. [claim:clm_inf08]
- The normalization boundary should live in a standalone RF intake stage (not in a MeatyWiki connector), because RF's determinism-by-default contract and its source_card/extraction_card/claim_ledger/evidence_bundle chain already define the canonical normalized form, and pushing normalization downstream into MeatyWiki would duplicate that schema and lose per-claim attribution before the claim ledger is built. [claim:clm_inf09]
- Idempotent re-import should hash the resolved (url, published_at) of each citation plus a per-session capture key into a stable source_card_id, so re-capturing the same ChatGPT/Perplexity/Gemini session updates existing cards in place rather than creating duplicates, mirroring RF's deterministic ingestion contract. [claim:clm_inf10]
- When a tool summarizes sources it does not directly cite (e.g. NotebookLM, or Perplexity's response-level source set), attribution should be preserved by labeling those evidence entries relation: supports with confidence: medium and flagging requires_network/needs_content, never promoting them to a tagged material claim, matching RF's rule that non-reproducible AI prose never enters a report body without a claim id. [claim:clm_inf13]
- The single highest-leverage normalization primitive is the (span -> source) citation tuple, because OpenAI annotations, Gemini groundingSupports, and Perplexity search_results all reduce to it, so building the adapter layer around that one tuple type lets a new tool be onboarded by writing only a thin field-mapping rather than a new pipeline. [claim:clm_inf15]
- RF should build the OpenAI and Perplexity adapters first, Gemini grounding second, and defer the Gemini Deep Research Agent and NotebookLM adapters, because development effort tracks inversely with API stability and the first three deliver the bulk of high-fidelity, deduplicatable, automatable citations. [claim:clm_inf16]
- Per-tool automation tiering ranks OpenAI Deep Research and Perplexity Sonar as Tier-1 (stable, GA, API-backed, fully scriptable), Gemini grounding as Tier-1 but its Deep Research Agent as Tier-2 (preview/Interactions-API-only), and NotebookLM as Tier-3 (no REST API, browser/OAuth/CLI automation only). [claim:clm_inf03]
- On attribution fidelity, OpenAI and Gemini are the highest-fidelity sources because both return machine-readable span-level citations (character/byte offsets mapped to url+title), Perplexity is high but list-level (per-response source set, not per-sentence offsets via the documented fields), and NotebookLM is the lowest because quote-span availability is an unresolved open question. [claim:clm_inf04]
- Each tool's native span-to-source structure maps deterministically onto one RF claim with sources[{source_card_id, evidence_id, relation, locator}]: OpenAI annotation -> one source entry per annotation, Gemini groundingSupport -> one entry per groundingChunkIndex, Perplexity -> one entry per search_results object, so the RF claim ledger is the correct convergence target for all four feeds. [claim:clm_inf05]
- OpenAI Deep Research's PDF export is unsuitable as the primary ingestion surface and should be used only as a human-readable fallback, because the API path (response.output[-1] message with annotations carrying url/title/start_index/end_index) preserves structured per-span citations that a flattened PDF loses. [claim:clm_inf11]
- Ingest-cost telemetry should be sourced primarily from Perplexity's per-request cost fields and Gemini's per-search-query billing, because those two tools expose machine-readable cost signals (input/output/request/total and per-query charges) while OpenAI Deep Research and NotebookLM require external cost estimation. [claim:clm_inf12]
- Gemini's vertexaisearch.cloud.google.com redirect URIs must be resolved to their true publisher URLs inside the intake adapter before dedup, otherwise every Gemini-sourced citation will appear as a distinct google.com redirect and silently defeat URL-keyed deduplication against OpenAI and Perplexity citations of the same page. [claim:clm_inf14]

## Links

- [[claim:clm_055]]
- [[claim:clm_064]]
- [[claim:clm_040]]
- [[claim:clm_045]]
- [[claim:clm_047]]
- [[claim:clm_067]]
- [[claim:clm_009]]
- [[claim:clm_030]]
- [[claim:clm_033]]
- [[claim:clm_035]]
- [[claim:clm_018]]
- [[claim:clm_001]]
- [[claim:clm_002]]
- [[claim:clm_003]]
- [[claim:clm_006]]
- [[claim:clm_044]]
- [[claim:clm_007]]
- [[claim:clm_008]]
- [[claim:clm_021]]
- [[claim:clm_036]]
- [[claim:clm_032]]
- [[claim:clm_034]]
- [[claim:clm_010]]
- [[claim:clm_011]]
- [[claim:clm_014]]
- [[claim:clm_012]]
- [[claim:clm_049]]
- [[claim:clm_062]]
- [[claim:clm_048]]
- [[claim:clm_060]]
- [[claim:clm_066]]
- [[claim:clm_038]]
- [[claim:clm_028]]
- [[claim:clm_071]]
- [[claim:clm_054]]
- [[claim:clm_022]]
- [[claim:clm_015]]
- [[claim:clm_050]]
- [[claim:clm_057]]
- [[claim:clm_061]]
- [[claim:clm_069]]
- [[claim:clm_070]]
- [[claim:clm_042]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
