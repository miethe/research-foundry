---
id: mwb_20260614_unified_ai_research_capture_harness_pipeline
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_pipeline_architect
target_page: meatywiki/sources/unified_ai_research_capture_harness_pipeline.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_pipeline_architecture_best_ingests_outputs:
  78 supported claim(s) across 12 source card(s).'
key_claims:
- claim_id: clm_001
  include: true
- claim_id: clm_002
  include: true
- claim_id: clm_003
  include: true
- claim_id: clm_004
  include: true
- claim_id: clm_005
  include: true
- claim_id: clm_006
  include: true
- claim_id: clm_007
  include: true
- claim_id: clm_008
  include: true
- claim_id: clm_009
  include: true
- claim_id: clm_010
  include: true
- claim_id: clm_011
  include: true
- claim_id: clm_012
  include: true
- claim_id: clm_013
  include: true
- claim_id: clm_014
  include: true
- claim_id: clm_015
  include: true
- claim_id: clm_016
  include: true
- claim_id: clm_017
  include: true
- claim_id: clm_018
  include: true
- claim_id: clm_019
  include: true
- claim_id: clm_020
  include: true
- claim_id: clm_021
  include: true
- claim_id: clm_022
  include: true
- claim_id: clm_023
  include: true
- claim_id: clm_024
  include: true
- claim_id: clm_025
  include: true
- claim_id: clm_026
  include: true
- claim_id: clm_027
  include: true
- claim_id: clm_028
  include: true
- claim_id: clm_029
  include: true
- claim_id: clm_030
  include: true
- claim_id: clm_031
  include: true
- claim_id: clm_032
  include: true
- claim_id: clm_033
  include: true
- claim_id: clm_034
  include: true
- claim_id: clm_035
  include: true
- claim_id: clm_036
  include: true
- claim_id: clm_037
  include: true
- claim_id: clm_038
  include: true
- claim_id: clm_039
  include: true
- claim_id: clm_040
  include: true
- claim_id: clm_041
  include: true
- claim_id: clm_042
  include: true
- claim_id: clm_043
  include: true
- claim_id: clm_044
  include: true
- claim_id: clm_045
  include: true
- claim_id: clm_046
  include: true
- claim_id: clm_047
  include: true
- claim_id: clm_048
  include: true
- claim_id: clm_049
  include: true
- claim_id: clm_050
  include: true
- claim_id: clm_051
  include: true
- claim_id: clm_052
  include: true
- claim_id: clm_053
  include: true
- claim_id: clm_054
  include: true
- claim_id: clm_055
  include: true
- claim_id: clm_056
  include: true
- claim_id: clm_057
  include: true
- claim_id: clm_058
  include: true
- claim_id: clm_059
  include: true
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
- claim_id: clm_078
  include: true
links:
  source_cards:
  - src_20260614_rib053_00
  - src_20260614_rib053_01
  - src_20260614_rib053_02
  - src_20260614_rib053_03
  - src_20260614_rib053_04
  - src_20260614_rib053_05
  - src_20260614_rib053_06
  - src_20260614_rib053_07
  - src_20260614_rib053_08
  - src_20260614_rib053_09
  - src_20260614_rib053_10
  - src_20260614_rib053_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Unified AI Research-Capture Harness: Pipeline Architecture

## Summary

Source note distilled from research run rf_run_20260614_what_pipeline_architecture_best_ingests_outputs: 78 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_rib053_00 — Deep research | OpenAI API
- src_20260614_rib053_01 — OpenAI (X/Twitter): deep research reports now exportable as well-formatted PDFs
- src_20260614_rib053_02 — Chat Completions | Perplexity Sonar API Reference
- src_20260614_rib053_03 — Grounding with Google Search | Gemini API
- src_20260614_rib053_04 — Gemini Deep Research Agent | Gemini API
- src_20260614_rib053_05 — Generate Audio Overview in NotebookLM
- src_20260614_rib053_06 — NotebookLM Integration — Sourcing, Reports, Extended Runs, Upload-Back (RF local plan)
- src_20260614_rib053_07 — C2PA Technical Specification (Content Credentials) v2.4
- src_20260614_rib053_08 — GroundingMetadata | REST Resource | Vertex AI / Gemini Enterprise Agent Platform REST API reference (v1beta1)
- src_20260614_rib053_09 — Introduction to deep research in the OpenAI API
- src_20260614_rib053_10 — Perplexity API Changelog
- src_20260614_rib053_11 — Research Foundry — Service API & Artifact Contract

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
