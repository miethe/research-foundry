export const meta = {
  name: 'rf-pediatric-cds-run-execute',
  description: 'Execute ONE Pediatric-CDS Research Foundry run end-to-end via Path B, with the pediatric_cds evidence-card contract (population/assay/threshold+UCUM/lifecycle + exact-passage locators) baked in, PubMed MCP discovery lane for clinical runs, and legal-review flagging for regulatory runs. Modes: clinical | regulatory | backfill.',
  phases: [
    { title: 'Discover', detail: 'parallel researchers (PubMed+web for clinical, regulatory sources for reg); backfill seeds from existing evidence records' },
    { title: 'SourceCards', detail: 'one carder/locator per source -> pediatric_cds source card with verbatim passage locators' },
    { title: 'Evidence', detail: 'rf extract + rf claim-map (deterministic)' },
    { title: 'Analysis', detail: 'append inference/speculation claims: scope-exits, conflicts, proposals' },
    { title: 'Synthesize', detail: 'rf synthesize --deterministic (verify-passing baseline)' },
    { title: 'Enrich', detail: 'upgrade into the pediatric evidence dossier / positioning memo' },
    { title: 'Verify', detail: 'rf verify loop with fixer + deterministic fallback' },
    { title: 'Bundle', detail: 'adversarial passage-fidelity audit + rf bundle --verify' },
  ],
}

// USAGE (args, JSON object or string):
//   REQUIRED: run_id, ref, title, artifact_type, question, mode (clinical|regulatory|backfill)
//   clinical/regulatory: angles:[{label,focus,local_refs?}], source_classes:[], primary:[], success:[]
//   backfill: seed:{records:[{id,title,url,doi,supports:[]}...], evidence_json_path?, rules_json_path?}
//   regulatory: legal_flag:true  →  bakes the "not legal advice / pending legal review" banner
//   ENV overrides (pass per-invocation): repo, rf_bin, tmp (MUST be writable + OUTSIDE runs/), stamp (YYYYMMDD), today (YYYY-MM-DD)
//   depth (standard|deep), freshness_days, max_sources, writeback_targets (default: none — stop at verified bundle)
let A = args || {}
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }

const REPO  = A.repo   || '/Users/miethe/dev/homelab/development/research-foundry'
const RF    = A.rf_bin || (REPO + '/.venv/bin/rf')   // DIRECT local binary — NOT the ~/.local/bin/rf shim (that SSHes to the node)
const TMP   = A.tmp    || (REPO + '/.claude/tmp/rf-peds-swarm')   // MUST be writable and OUTSIDE runs/ (Write/Edit are rejected under runs/); override per-invocation
const STAMP = A.stamp  || '20260718'   // override per-run: derives source_card_id prefixes + created_at
const TODAY = A.today  || '2026-07-18' // override per-run: freshness anchor in discovery prompts
const MODE  = A.mode   || 'clinical'          // clinical | regulatory | backfill
const run   = A.run_id
const refslug = (A.ref || 'run').toLowerCase().replace(/[^a-z0-9]+/g, '')
const MAXS  = A.max_sources || (MODE === 'backfill' ? 12 : 12)
const FRESH = A.freshness_days || 180
const DEPTH = A.depth || 'standard'
const LEGAL = !!A.legal_flag
const WB    = A.writeback_targets || null      // default: bundle only (respect the rf->CDS seam); land on nuc separately

if (!run) { return { error: 'missing run_id in args' } }

// ---------- governance / legal banners (baked into every report) ----------
const GOV_BANNER =
  'UNVALIDATED research prototype. rf output is a PROPOSAL, not a validated rule. No autonomous ' +
  'diagnosis/treatment/dosing/transfusion directives. No unsupported confidence %. Missingness is ' +
  'never treated as normal. Every clinical threshold ties to an exact passage or is flagged a proposal.'
const LEGAL_BANNER =
  'RESEARCH INPUT ONLY — FLAG FOR LEGAL REVIEW. NOT LEGAL ADVICE. Regulatory statements cite sources ' +
  'with exact locators and are pending qualified legal review.'

// ---------- schemas ----------
const CAND_SCHEMA = {
  type: 'object', additionalProperties: true, required: ['sources'],
  properties: { sources: { type: 'array', items: {
    type: 'object', additionalProperties: true,
    required: ['url', 'title', 'source_type', 'source_rank', 'why', 'key_points'],
    properties: {
      url: { type: 'string' }, title: { type: 'string' },
      source_type: { type: 'string', enum: ['official_doc','paper','standard','repo','news','blog','book','other'] },
      published: { type: 'string' }, pmid: { type: 'string' }, doi: { type: 'string' },
      source_rank: { type: 'string', enum: ['primary','secondary','tertiary','unknown'] },
      why: { type: 'string' }, key_points: { type: 'array', items: { type: 'string' } },
    } } } },
}
const CARD_SCHEMA = { type: 'object', additionalProperties: true, required: ['source_card_id','ok','n_points'],
  properties: { source_card_id: { type: 'string' }, ok: { type: 'boolean' }, n_points: { type: 'number' },
    n_located: { type: 'number' }, note: { type: 'string' } } }
const TAIL_SCHEMA = { type: 'object', additionalProperties: true, required: ['ok','claim_count','claims'],
  properties: { ok: { type: 'boolean' }, exit_extract: { type: 'number' }, exit_claimmap: { type: 'number' },
    claim_count: { type: 'number' }, claims: { type: 'array', items: { type: 'object', additionalProperties: true,
      required: ['claim_id','text'], properties: { claim_id: { type: 'string' }, text: { type: 'string' } } } } } }
const INFER_SCHEMA = { type: 'object', additionalProperties: true, required: ['appended','outline','ok'],
  properties: { ok: { type: 'boolean' }, outline: { type: 'string' },
    appended: { type: 'array', items: { type: 'object', additionalProperties: true,
      required: ['claim_id','status'], properties: { claim_id: { type: 'string' }, status: { type: 'string' } } } } } }
const STEP_SCHEMA = { type: 'object', additionalProperties: true, required: ['ok','detail'],
  properties: { ok: { type: 'boolean' }, exit: { type: 'number' }, detail: { type: 'string' } } }
const VERIFY_SCHEMA = { type: 'object', additionalProperties: true, required: ['exit','passed'],
  properties: { exit: { type: 'number' }, passed: { type: 'boolean' },
    failures: { type: 'array', items: { type: 'object', additionalProperties: true } } } }

// ---------- pediatric_cds source-card template ----------
const CARD_TEMPLATE =
'---\n' +
'schema_version: \'0.1\'\n' +
'type: source_card\n' +
'source_card_id: <ID>\n' +
'created_at: \'' + STAMP.slice(0,4) + '-' + STAMP.slice(4,6) + '-' + STAMP.slice(6,8) + 'T12:00:00-04:00\'\n' +
'created_by_agent: rf-peds-cds-carder\n' +
'sensitivity: personal\n' +
'source:\n' +
'  title: "<REAL TITLE>"\n' +
'  source_type: <official_doc|paper|standard|repo|news|blog|book|other>\n' +
'  locator: {url: "<REAL URL>", file_path: null, doi: "<doi or null>", repo: null, pmid: "<pmid or null>"}\n' +
'  authors: [<authors or empty>]\n' +
'  publisher: "<publisher or null>"\n' +
'  published_at: "<YYYY-MM or date or null>"\n' +
'  accessed_at: \'' + STAMP.slice(0,4) + '-' + STAMP.slice(4,6) + '-' + STAMP.slice(6,8) + 'T12:00:00-04:00\'\n' +
'  version: "<guideline/edition version or null>"\n' +
'trust: {source_rank: <primary|secondary|tertiary|unknown>, reliability_notes: "<short>", known_limitations: [], conflicts_with: []}\n' +
'usage: {allowed_for_public_output: false, allowed_for_work_output: true, allowed_for_personal_meatywiki: true, citation_required: true, quote_limit_notes: "Short excerpts only."}\n' +
'extracted_points:\n' +
'- evidence_id: ev_001\n' +
'  locator: "<page/section/heading/para — the EXACT passage location>"\n' +
'  summary: "<ONE crisp factual sentence a report can cite>"\n' +
'  quote: "<VERBATIM quote copied exactly from the source, <=280 chars — REQUIRED for any threshold/numeric claim>"\n' +
'  supports_potential_claims: [clm_pending]\n' +
'  pediatric_cds:\n' +
'    population: "<age band + sex + gestational/postnatal age where relevant + clinical context, or \'not applicable\'>"\n' +
'    assay_method: "<analyzer/method dependence for any numeric threshold, or \'not method-dependent\' / \'not applicable\'>"\n' +
'    threshold: {value: "<verbatim numeric value + comparator, or null>", units_ucum: "<UCUM units e.g. g/dL, 10*9/L, mL/min/{1.73_m2}, or null>", passage_locator: "<page/section + the verbatim quote fragment carrying the number, or null>"}\n' +
'    lifecycle: {effective: "<date/version or null>", retire: "<date or null>", guideline_version: "<version or null>", supersedes: "<prior ref or null>"}\n' +
'    classification: <source_supported_fact|implementation_proposal>\n' +
'- evidence_id: ev_002\n' +
'  locator: "..."\n' +
'  summary: "..."\n' +
'  quote: "..."\n' +
'  supports_potential_claims: [clm_pending]\n' +
'  pediatric_cds: {population: "...", assay_method: "...", threshold: {value: null, units_ucum: null, passage_locator: null}, lifecycle: {effective: null, retire: null, guideline_version: null, supersedes: null}, classification: source_supported_fact}\n' +
'---\n' +
'# Source Card: <REAL TITLE>\n\n' +
'## Summary\n<2-3 sentence neutral summary of what this source establishes for the pediatric CDS module.>\n\n' +
'## Key evidence (with exact-passage locators)\n- (ev_001) <summary> — locator: <page/section> — quote: "<verbatim>"\n- (ev_002) ...\n\n' +
'## Population / assay / lifecycle notes\n- <population scope, analyzer/method dependence, guideline version/effective date>\n\n' +
'## Scope-exit / referral relevance (if any)\n- <does this source define a red-flag / referral trigger / scope boundary? or "None">\n\n' +
'## Limitations & conflicts\n- <recency/scope limits; any conflict with other sources — name it, never silently collapse; or "None recorded.">\n'

const WRITE_RULE =
  'IMPORTANT FILE-WRITE RULE: never use the Write/Edit tools on any path under ' + REPO + '/runs (the shared checkout rejects tool-edits there). ' +
  'Instead: use the Write tool to author the file under ' + TMP + '/ , then run Bash `cp ' + TMP + '/<name> <dest>` to place it. ' +
  'Always `cd ' + REPO + '` before running `rf` or git/ls on the run.'

const CONTRACT_RULE =
  'PEDIATRIC-CDS OUTPUT CONTRACT (non-negotiable):\n' +
  '- Every numeric threshold/cutoff/equation MUST carry a VERBATIM quote + an exact-passage locator (page/section). No verbatim passage => do NOT assert the number; instead record it as a GAP in "## Limitations & conflicts" ("threshold X not locatable in source Y").\n' +
  '- Fill the pediatric_cds block per evidence point: population (age band/sex/GA-PNA/context), assay_method (analyzer/method dependence), threshold {value, units_ucum (UCUM), passage_locator}, lifecycle (effective/retire/guideline_version/supersedes), classification (source_supported_fact vs implementation_proposal).\n' +
  '- Conflicts between sources/standards are PRESERVED as conflicts (name them in conflicts_with / Limitations), never averaged or silently collapsed.\n' +
  '- Missingness is never "normal": if a population lacks a value, say so explicitly; do not infer or fabricate.\n' +
  '- NO diagnosis/treatment/dosing/transfusion directives. rf output is a PROPOSAL for the CDS converter, not an executable rule.'

// ---------- helpers ----------
function norm(u){ return (u||'').toLowerCase().replace(/^https?:\/\//,'').replace(/\/$/,'').replace(/[#?].*$/,'') }
function dedupe(list){ const seen=new Set(); const out=[]; for(const s of list){ const k=norm(s.url)||(s.title||'').toLowerCase().trim(); if(!k||seen.has(k)) continue; seen.add(k); out.push(s) } return out }
const RANKW={primary:0,secondary:1,tertiary:2,unknown:3}
function rankSources(list){ return list.slice().sort((a,b)=>(RANKW[a.source_rank]??3)-(RANKW[b.source_rank]??3)) }

const PUBMED_LANE =
  'PUBMED MCP LANE (use it — this is clinical evidence): load medical tools with ToolSearch query ' +
  '"select:mcp__claude_ai_PubMed__search_articles,mcp__claude_ai_PubMed__get_article_metadata,mcp__claude_ai_PubMed__get_full_text_article,mcp__claude_ai_PubMed__find_related_articles,mcp__claude_ai_PubMed__lookup_article_by_citation,WebSearch,WebFetch". ' +
  'Prefer PubMed for peer-reviewed pediatric literature, society guidelines, and reference-interval studies (CALIPER etc.); use WebSearch/WebFetch for guideline PDFs / society statements / official pages. Capture PMID and DOI where available.'
const WEB_LANE =
  'WEB LANE: load web tools with ToolSearch query "select:WebSearch,WebFetch" (you may also use the firecrawl skill). ' +
  'For regulatory work, go to PRIMARY government sources: FDA guidance pages, the 21st Century Cures Act text, eCFR / 45 CFR (HIPAA), HHS.gov, official Federal Register notices. Capture exact section/paragraph numbers as locators.'

// ---------- prompt builders ----------
function discoveryPrompt(ang){
  const lane = (MODE === 'regulatory') ? WEB_LANE : PUBMED_LANE
  return 'Mode: A — research discovery (read-only). You are a source scout for a Pediatric-CDS Research Foundry run.\n\n' +
  'RUN: ' + run + ' (' + A.ref + ', mode=' + MODE + ')\n' +
  'RESEARCH FOCUS: ' + ang.focus + '\n' +
  'OVERALL QUESTION: ' + A.question + '\n' +
  (A.source_classes && A.source_classes.length ? ('PREFERRED SOURCE CLASSES: ' + A.source_classes.join('; ') + '\n') : '') +
  'FRESHNESS: prefer sources published/updated within ~' + FRESH + ' days (today is ' + TODAY + '). Foundational guidelines/standards older than that are allowed but mark them tertiary unless they are the current authoritative version.\n\n' +
  'DO REAL RESEARCH. ' + lane + '\n' +
  (ang.local_refs && ang.local_refs.length ? ('ALSO read these local seed files (primary context, source_rank primary) and include any with citable facts: ' + ang.local_refs.join(' ; ') + '\n') : '') +
  '\nFind 5-9 AUTHORITATIVE, current sources for the focus. For each return: url (real, resolvable), title, source_type, published (YYYY-MM or date; "unknown" only if truly absent), pmid + doi where available, source_rank, why (1 sentence: what citable pediatric facts/thresholds it yields), key_points (3-6 short strings, each an extractable factual claim WITH a number/threshold/age-band/date where possible).\n' +
  'Do NOT fabricate URLs, PMIDs, or facts. Drop any URL you cannot confirm resolves. Return ONLY sources you actually opened or are highly confident are real and on-topic.'
}

function carderPrompt(s, i){
  const id = 'src_' + STAMP + '_' + refslug + '_' + String(i).padStart(2,'0')
  const lane = (MODE === 'regulatory') ? WEB_LANE : PUBMED_LANE
  return 'Mode: produce ONE Pediatric-CDS SOURCE CARD from a real source. ' + WRITE_RULE + '\n\n' + CONTRACT_RULE + '\n\n' +
  'SOURCE: ' + JSON.stringify({url:s.url,title:s.title,source_type:s.source_type,source_rank:s.source_rank,published:s.published,pmid:s.pmid,doi:s.doi,key_points:s.key_points}) + '\n\n' +
  'STEP 1 — DEEP READ: ' + lane + ' Open and read the source. If it is a PubMed article prefer get_full_text_article by PMID. Extract 4-8 MATERIAL, citable evidence points. For EACH: a one-sentence factual `summary`; a VERBATIM `quote` copied exactly (<=280 chars) — REQUIRED for any threshold/numeric/equation point (if you cannot copy a verbatim passage carrying the number, do NOT assert it — log it as a GAP instead); a human `locator` (section title / heading / "p.N" / para / table N); and the pediatric_cds block (population, assay_method, threshold{value,units_ucum,passage_locator}, lifecycle, classification). Capture real authors/publisher/published_at/version. NEVER invent quotes or numbers.\n\n' +
  'STEP 2 — AUTHOR THE CARD: fill this EXACT template (keep all keys; valid YAML frontmatter; one extracted_points block per evidence point ev_001..ev_00N, each WITH its pediatric_cds sub-block):\n' + CARD_TEMPLATE + '\n' +
  'Use source_card_id EXACTLY: ' + id + '  (sensitivity: personal). source.locator.url must be the real URL; include doi/pmid if known. trust.source_rank from the source.\n\n' +
  'STEP 3 — PLACE IT: Write the completed markdown to ' + TMP + '/' + id + '.md, then Bash: `cp ' + TMP + '/' + id + '.md ' + REPO + '/runs/' + run + '/sources/' + id + '.md` and `ls -la ' + REPO + '/runs/' + run + '/sources/' + id + '.md` to confirm.\n' +
  'Return source_card_id=' + id + ', ok=true if written with >=2 real evidence points (else ok=false), n_points, n_located (points that carry a verbatim threshold passage), and a one-line note.'
}

function seedCarderPrompt(seed, i){
  const id = 'src_' + STAMP + '_' + refslug + '_' + String(i).padStart(2,'0')
  return 'Mode: LOCATE & VERIFY one EXISTING pediatric evidence source (backfill run — no new discovery). ' + WRITE_RULE + '\n\n' + CONTRACT_RULE + '\n\n' +
  'This run backfills exact-passage locators for a source ALREADY in the anemia knowledge base. You are NOT choosing a new source — you are locating the exact passages inside THIS one that back its existing use.\n\n' +
  'EXISTING EVIDENCE RECORD (id ' + seed.id + '):\n' + JSON.stringify(seed, null, 1) + '\n\n' +
  'CONTEXT FILES you MAY read for what claims/rules this source backs: ' +
    (A.seed && A.seed.evidence_json_path ? A.seed.evidence_json_path : '(evidence.json)') +
    (A.seed && A.seed.rules_json_path ? (' ; ' + A.seed.rules_json_path) : '') + '\n\n' +
  'STEP 1 — OPEN THE REAL SOURCE at its url/doi (load web tools: ToolSearch "select:WebSearch,WebFetch"; for a PubMed/DOI item you may also load "select:mcp__claude_ai_PubMed__get_full_text_article,mcp__claude_ai_PubMed__lookup_article_by_citation"). Read it. Identify 3-8 exact passages that back the statements/thresholds this record is used for in the anemia KB. For each passage capture: verbatim `quote` (<=280 chars), exact `locator` (page/section/table), one-sentence `summary`, and the pediatric_cds block (population age band, assay/method dependence, threshold value+UCUM+passage_locator, lifecycle incl. guideline version + effective date, classification). If the live document cannot be opened, record what IS verifiable from the abstract/metadata and mark unlocatable thresholds as GAPS — do NOT fabricate.\n\n' +
  'STEP 2 — AUTHOR THE CARD using this EXACT template (all keys; per-point pediatric_cds block). Set source.title/url/doi to the record\'s real values:\n' + CARD_TEMPLATE + '\n' +
  'Use source_card_id EXACTLY: ' + id + '. In reliability_notes, note the KB id "' + seed.id + '" this card backfills.\n\n' +
  'STEP 3 — PLACE IT: Write to ' + TMP + '/' + id + '.md then Bash `cp ' + TMP + '/' + id + '.md ' + REPO + '/runs/' + run + '/sources/' + id + '.md` and `ls -la` it.\n' +
  'Return source_card_id=' + id + ', ok=true if >=2 located passages, n_points, n_located (points with verbatim threshold passages), note (mention any GAPS).'
}

function tailPrompt(){
  return 'Mode: run the Research Foundry deterministic extraction tail. ' + WRITE_RULE + '\n\n' +
  'Run and capture exit codes:\n' +
  '1) `cd ' + REPO + ' && ' + RF + ' extract ' + run + '`\n' +
  '2) `cd ' + REPO + ' && ' + RF + ' claim-map ' + run + '`\n' +
  'Then Read ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml and return EVERY claim as {claim_id, text} plus claim_count. ' +
  'ok=true only if both commands exited 0 and claim_count > 0. Report exit_extract and exit_claimmap.'
}

function analystPrompt(claims){
  const ids = claims.map(c=>c.claim_id)
  const clinicalAsk =
    'This is a CLINICAL evidence run. Your analytical claims MUST include, where the evidence supports them: ' +
    '(a) an explicit SCOPE-EXIT / red-flag / referral-trigger list (each trigger = one claim, classified as a proposal/speculation if it is an implementation boundary rather than a directly-stated fact); ' +
    '(b) population-scoped threshold comparisons (name age band + value + UCUM units + which source/locator); ' +
    '(c) CONFLICTS between sources/standards preserved as explicit claims ("Source X states A; Source Y states B; unresolved"); ' +
    '(d) method/assay-dependence notes for any analyzer-dependent threshold; ' +
    '(e) explicit GAPS/missingness ("no located pediatric threshold for population Z").'
  const regulatoryAsk =
    'This is a REGULATORY run (research input only, pending legal review). Your analytical claims MUST include: ' +
    '(a) each regulatory criterion/control mapped to how the platform meets or does NOT meet it (cite the supported claim + locator); ' +
    '(b) boundary conditions that would change the classification (device vs non-device CDS / PHI vs PHI-free); ' +
    '(c) explicit "pending legal review" framing on any interpretive conclusion (status: speculation with a clear basis). ' +
    'Do NOT state legal conclusions as fact.'
  return 'Mode: analytical synthesis (critic/synthesizer) for a Pediatric-CDS run. ' + WRITE_RULE + '\n\n' + CONTRACT_RULE + '\n\n' +
  'OVERALL QUESTION: ' + A.question + '\n' +
  'PRIMARY QUESTIONS:\n- ' + (A.primary||[]).join('\n- ') + '\n' +
  (A.secondary && A.secondary.length ? ('SECONDARY:\n- ' + A.secondary.join('\n- ') + '\n') : '') +
  'SUCCESS / ACCEPTANCE CRITERIA:\n- ' + (A.success||[]).join('\n- ') + '\n' +
  (A.acceptance ? ('ACCEPTANCE: ' + A.acceptance + '\n') : '') + '\n' +
  (MODE === 'regulatory' ? regulatoryAsk : clinicalAsk) + '\n\n' +
  'The deterministic claim-map produced these SUPPORTED claims (each backed by a source card):\n' +
  claims.map(c=>c.claim_id + ': ' + c.text).join('\n') + '\n\n' +
  'TASK: Read all source cards in ' + REPO + '/runs/' + run + '/sources/ and the ledger ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml. ' +
  'Author the ANALYTICAL LAYER as NEW claims (inference = a conclusion drawn from >=1 supported claim; speculation = forward-looking/uncertain/implementation-proposal). Author ' + (DEPTH==='deep' ? '12-20' : '8-14') + ' such claims — specific (name the age band, value, units, source, or criterion), never vague.\n\n' +
  'APPEND each to the `claims:` list in claim_ledger.yaml using EXACTLY this entry shape (valid YAML; 2-space indent under the list):\n' +
  '- claim_id: clm_inf01            # unique; clm_inf## = inference, clm_spec## = speculation/proposal; MUST NOT collide with: ' + ids.join(',') + '\n' +
  '  text: "<one crisp analytic sentence — the conclusion, with age band/value/units where relevant>"\n' +
  '  materiality: material\n' +
  '  claim_type: <comparative|causal|recommendation|prediction|quantitative|factual>\n' +
  '  status: <inference|speculation>\n' +
  '  confidence: <low|medium|high>\n' +
  '  sources: []\n' +
  '  inference_basis: {from_claims: [<real existing clm ids this follows from>], reasoning_summary: "<why this follows>"}   # REQUIRED & NON-EMPTY for inference; for speculation use from_claims: [] and reasoning_summary: "<basis/assumption>"\n' +
  '  report_locations: []\n' +
  '  reviewer_notes: ""\n\n' +
  'Edit safely: Read the ledger, append entries under `claims:`, write the FULL updated YAML to ' + TMP + '/ledger_' + run + '.yaml, then Bash `cp ' + TMP + '/ledger_' + run + '.yaml ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml`. ' +
  'Do NOT run `rf claim-map` again (it would overwrite). Keep YAML valid (no tabs; quote strings containing colons).\n\n' +
  'Return: appended=[{claim_id,status}...]; outline = a section-by-section plan for the final ' + A.artifact_type + ' naming which claim_ids belong in each section; ok=true.'
}

function synthPrompt(){
  return 'Mode: run Research Foundry synthesis (deterministic, verify-passing baseline). ' + WRITE_RULE + '\n\n' +
  '1) `cd ' + REPO + ' && ' + RF + ' synthesize ' + run + ' --deterministic --draft`\n' +
  '2) Back it up: Bash `cp ' + REPO + '/runs/' + run + '/reports/report_draft.md ' + REPO + '/runs/' + run + '/reports/report_deterministic.md` (guaranteed-passing fallback — do not delete).\n' +
  'Return ok=(exit 0 and report_draft.md non-empty), exit, one-line detail with report line count.'
}

function enrichPrompt(){
  const artifactSpec = (MODE === 'regulatory')
    ? ('a REGULATORY POSITIONING MEMO. Sections: "## Legal-review banner" (put this line verbatim, non-assertive: "> ' + LEGAL_BANNER + '"), Executive summary, the required criteria/controls mapping TABLE (each row: criterion/control | how the platform maps | source+locator | Evidence [claim:...]), Boundary conditions (device vs non-device / PHI vs PHI-free), Recommendations (framed as options pending legal review), Open questions, Sources.')
    : ('a PEDIATRIC-CDS EVIDENCE DOSSIER. Sections: "## Governance banner" (verbatim, non-assertive: "> ' + GOV_BANNER + '"), Executive summary, a POPULATION-SCOPED THRESHOLDS TABLE (columns: parameter | population/age band | threshold value | UCUM units | assay/method dependence | source+locator | Evidence [claim:...]), a SCOPE-EXIT / REFERRAL-TRIGGERS section (bulleted, each tagged), a CONFLICTS & METHOD-DEPENDENCE section, Open questions / gaps, Sources.')
  return 'Mode: upgrade the run report into the real deliverable. ' + WRITE_RULE + '\n\n' +
  'TARGET ARTIFACT: ' + artifactSpec + '\n' +
  'Title: "' + A.title + '". Audience: technical. It must satisfy:\n- ' + (A.success||[]).join('\n- ') + '\n\n' +
  'INPUT: ' + REPO + '/runs/' + run + '/reports/report_draft.md is the deterministic baseline (one tagged sentence per ledger claim). Read it + the ledger ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml. Use ONLY claims already in the ledger.\n\n' +
  'VERIFY-GATE RULES (rf verify enforces these — breaking them fails the run):\n' +
  '1. Every material sentence (factual/quantitative/comparative/causal/attribution/recommendation/prediction) MUST end with its [claim:clm_xxx] tag — reuse exact tags from the baseline; one material claim per line.\n' +
  '2. Inference/speculation sentences keep BOTH the bold label (**Inference:** / **Speculation:**) AND their [claim:...] tag.\n' +
  '3. No new material sentence without a [claim:...] tag. Banner/intro lines must be non-assertive (blockquote, no facts). Questions go under "## Open questions" ending with "?".\n' +
  '4. Table data rows stating a material fact carry [claim:clm_xxx] in a trailing "Evidence" column. Header/label rows need none. One claim per row.\n' +
  '5. Keep a "## Sources" section (exempt) listing each source_card_id: title.\n' +
  '6. Preserve YAML frontmatter (audience: technical, sensitivity: personal); may update title/status, keep all keys.\n' +
  '7. Do not invent claim ids; every [claim:...] resolves to a ledger id. Do NOT call rf claim-map.\n\n' +
  'Author the rewrite to ' + TMP + '/report_' + run + '.md, then Bash `cp ' + TMP + '/report_' + run + '.md ' + REPO + '/runs/' + run + '/reports/report_draft.md`. Return ok=true, one-line detail (section count).'
}

function verifyPrompt(){
  return 'Mode: run rf verify and report. ' + WRITE_RULE + '\n\n' +
  '`cd ' + REPO + ' && ' + RF + ' verify ' + run + '` — capture EXACT exit code (echo $?). Read ' + REPO + '/runs/' + run + '/reviews/verification.yaml. ' +
  'Return exit (integer), passed=(exit==0), failures=[{check,detail}] for every failed/blocking check (empty if passed). Do not modify files.'
}

function fixPrompt(failures){
  return 'Mode: repair the report so `rf verify` passes. ' + WRITE_RULE + '\n\n' +
  'rf verify on run ' + run + ' is FAILING. Failures:\n' + JSON.stringify(failures) + '\n\n' +
  'Read ' + REPO + '/runs/' + run + '/reports/report_draft.md, reviews/verification.yaml, and the ledger. Fix ONLY what verify flags:\n' +
  '- untagged material sentence: append the correct existing [claim:clm_xxx] tag; or if genuinely new, append a new inference claim (status: inference, inference_basis.from_claims non-empty) and tag it; or rephrase as a question under "## Open questions"; or move under "## Sources". Never leave a material sentence untagged.\n' +
  '- all_claim_ids_exist: fix any [claim:...] whose id is not in the ledger.\n' +
  '- inferences_have_basis: add inference_basis.from_claims to the offending ledger claim.\n' +
  '- *_is_labeled: add the missing **Inference:**/**Speculation:** label.\n' +
  '- supported_claims_have_source_cards: ensure the cited source_card_id file exists in runs/' + run + '/sources/.\n' +
  'Edit via TMP+cp. Do NOT run rf claim-map. Return ok=true, one-line detail of changes.'
}

function fallbackPrompt(){
  return 'Mode: restore the guaranteed-passing report. ' + WRITE_RULE + '\n\n' +
  'Enrichment could not pass verify. Restore baseline: Bash `cp ' + REPO + '/runs/' + run + '/reports/report_deterministic.md ' + REPO + '/runs/' + run + '/reports/report_draft.md`. ' +
  'Then `cd ' + REPO + ' && ' + RF + ' verify ' + run + '` and confirm exit 0. Return ok=(exit 0), exit, detail="reverted to deterministic report".'
}

function bundlePrompt(){
  const wbLine = WB
    ? ('STEP 3 — WRITEBACK: `cd ' + REPO + ' && ' + RF + ' writeback ' + run + ' --targets ' + WB + ' --no-require-review`.\n')
    : ('STEP 3 — NO WRITEBACK (this run stops at the verified bundle per the rf->CDS seam; the bundle is the handoff to the converter).\n')
  return 'Mode: adversarial passage-fidelity audit, then publish the evidence bundle. ' + WRITE_RULE + '\n\n' +
  'STEP 1 — AUDIT: Read ' + REPO + '/runs/' + run + '/reports/report_draft.md and claims/claim_ledger.yaml. Confirm (a) every [claim:...] tag resolves to a ledger claim; (b) every material sentence is tagged; (c) every SUPPORTED quantitative/threshold claim traces to a source card with a VERBATIM quote + locator (open a couple of source cards in runs/' + run + '/sources/ and spot-check). If you find an untagged sentence or a threshold claim lacking a verbatim passage, fix minimally (TMP+cp; you may append an inference claim with basis, or downgrade an unlocatable number to an Open question). Do NOT run rf claim-map.\n' +
  'STEP 2 — BUNDLE: `cd ' + REPO + ' && ' + RF + ' bundle ' + run + ' --verify` (must exit 0; if it fails, read verification.yaml, fix, retry once).\n' +
  wbLine +
  'Return ok=(bundle exit 0), exit, detail = evidence_bundle.yaml path + claim/source counts' + (WB ? ' + writeback files' : '') + '.'
}

// ====================== ORCHESTRATION ======================
log('Peds-CDS run ' + run + ' (' + A.ref + ', mode=' + MODE + ', ' + A.artifact_type + ', depth=' + DEPTH + ')' + (LEGAL ? ' [LEGAL-FLAG]' : ''))

// Phase 1: Discover / Seed
let selected = []
if (MODE === 'backfill') {
  phase('Discover')
  const seeds = A.seed && A.seed.records ? A.seed.records : []
  log('backfill: ' + seeds.length + ' existing sources to locate (no new discovery)')
  if (!seeds.length) { return { ref: A.ref, run_id: run, error: 'backfill mode but no seed.records provided' } }
  selected = seeds.map((sd, i) => ({ __seed: sd, __i: i }))
} else {
  phase('Discover')
  const candRaw = await parallel((A.angles||[]).map((ang) => () =>
    agent(discoveryPrompt(ang), { label: 'discover:' + ang.label, phase: 'Discover', schema: CAND_SCHEMA })))
  const allCand = dedupe(candRaw.filter(Boolean).flatMap(c => (c.sources || [])))
  selected = rankSources(allCand).slice(0, MAXS)
  log('discovery: ' + allCand.length + ' unique candidates -> ' + selected.length + ' selected')
  if (selected.length === 0) { return { ref: A.ref, run_id: run, error: 'no sources discovered' } }
}

// Phase 2: SourceCards / SeedCards
phase('SourceCards')
const cardRes = await parallel(selected.map((s, i) => () => {
  if (MODE === 'backfill') return agent(seedCarderPrompt(s.__seed, s.__i), { label: 'locate:' + String(s.__i).padStart(2,'0'), phase: 'SourceCards', schema: CARD_SCHEMA })
  return agent(carderPrompt(s, i), { label: 'card:' + String(i).padStart(2,'0'), phase: 'SourceCards', schema: CARD_SCHEMA })
}))
const okCards = cardRes.filter(Boolean).filter(c => c.ok)
const nLocated = cardRes.filter(Boolean).reduce((a,c)=>a+(c.n_located||0),0)
log('source cards written: ' + okCards.length + '/' + selected.length + ' (' + nLocated + ' verbatim-located points)')
if (okCards.length === 0) { return { ref: A.ref, run_id: run, error: 'no source cards authored' } }

// Phase 3: Evidence
phase('Evidence')
const tail = await agent(tailPrompt(), { label: 'extract+claim-map', phase: 'Evidence', schema: TAIL_SCHEMA })
if (!tail || !tail.ok || !(tail.claims||[]).length) { return { ref: A.ref, run_id: run, cards: okCards.length, error: 'extract/claim-map produced no claims', tail } }
log('claims supported: ' + tail.claim_count)

// Phase 4: Analysis
phase('Analysis')
const infer = await agent(analystPrompt(tail.claims), { label: 'analyst', phase: 'Analysis', schema: INFER_SCHEMA })
log('analytical claims appended: ' + ((infer && infer.appended) ? infer.appended.length : 0))

// Phase 5: Synthesize
phase('Synthesize')
const synth = await agent(synthPrompt(), { label: 'synthesize', phase: 'Synthesize', schema: STEP_SCHEMA })

// Phase 6: Enrich
phase('Enrich')
const enrich = await agent(enrichPrompt(), { label: 'enrich', phase: 'Enrich', schema: STEP_SCHEMA })

// Phase 7: Verify loop with deterministic fallback
phase('Verify')
let v = await agent(verifyPrompt(), { label: 'verify', phase: 'Verify', schema: VERIFY_SCHEMA })
let tries = 0
while (v && v.exit !== 0 && tries < 3) {
  tries++
  await agent(fixPrompt(v.failures || []), { label: 'fix:' + tries, phase: 'Verify', schema: STEP_SCHEMA })
  v = await agent(verifyPrompt(), { label: 'verify:' + tries, phase: 'Verify', schema: VERIFY_SCHEMA })
}
let degraded = false
if (!v || v.exit !== 0) {
  degraded = true
  await agent(fallbackPrompt(), { label: 'fallback', phase: 'Verify', schema: STEP_SCHEMA })
  v = await agent(verifyPrompt(), { label: 'verify:fallback', phase: 'Verify', schema: VERIFY_SCHEMA })
}
log('verify exit=' + (v ? v.exit : 'n/a') + ' (tries=' + tries + (degraded ? ', reverted to deterministic' : '') + ')')

// Phase 8: Bundle
phase('Bundle')
const bundle = await agent(bundlePrompt(), { label: 'bundle', phase: 'Bundle', schema: STEP_SCHEMA })

return {
  ref: A.ref, run_id: run, mode: MODE, artifact: A.artifact_type, depth: DEPTH, legal_flag: LEGAL,
  candidates: (MODE==='backfill' ? selected.length : undefined),
  selected: selected.length, source_cards: okCards.length, located_points: nLocated,
  claims_supported: tail.claim_count, claims_analytical: ((infer && infer.appended) || []).length,
  verify_exit: v ? v.exit : null, verify_tries: tries, enrichment_degraded: degraded,
  bundle: bundle ? bundle.detail : null, bundle_ok: bundle ? bundle.ok : false,
}
