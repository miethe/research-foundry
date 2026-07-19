export const meta = {
  name: 'rf-run-execute',
  description: 'Execute one Research Foundry run end-to-end via Path B: real web discovery -> curated source cards -> rf extract/claim-map -> analytical inference claims -> deterministic synthesize -> enrich -> verify loop (deterministic fallback) -> bundle + writeback.',
  phases: [
    { title: 'Discover', detail: 'parallel researchers, one per angle, real web sources' },
    { title: 'SourceCards', detail: 'one carder per selected source -> curated source card' },
    { title: 'Evidence', detail: 'rf extract + rf claim-map (deterministic)' },
    { title: 'Analysis', detail: 'append inference/speculation claims to ledger' },
    { title: 'Synthesize', detail: 'rf synthesize --deterministic (verify-passing baseline)' },
    { title: 'Enrich', detail: 'upgrade report into the real technical_memo/market_scan' },
    { title: 'Verify', detail: 'rf verify loop with fixer + deterministic fallback' },
    { title: 'Bundle', detail: 'adversarial audit + rf bundle + rf writeback' },
  ],
}

let A = args || {}
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }

// Resolve a possibly-relative config path against the invocation cwd. No `path` import —
// this file has none, so plain string handling is used (matches sibling workflow style).
function resolvePath(p) {
  if (!p) return p
  return p.startsWith('/') ? p : (process.cwd().replace(/\/$/, '') + '/' + p)
}
// Derive a YYYYMMDD run-date stamp from args.timestamp (an ISO-8601 string set by the
// orchestrator/Opus pre-flight — see workflow-authoring-spec.md Four-Constraints Checklist:
// no Date.now()/new Date() in the script body). Falls back to the historical literal default.
function stampFromTimestamp(ts) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ts || '')
  return m ? (m[1] + m[2] + m[3]) : null
}

const RF = resolvePath(A.rf_bin || '/Users/miethe/.local/bin/rf')
const REPO = resolvePath(A.repo || '/Users/miethe/dev/homelab/development/research-foundry')
const TMP = resolvePath(A.tmp_dir || '/Users/miethe/.claude/jobs/85ede6ca/tmp')
const STAMP = stampFromTimestamp(A.timestamp) || '20260613'
const run = A.run_id
const refslug = (A.ref || 'rib').toLowerCase().replace(/[^a-z0-9]+/g, '')
const MAXS = A.max_sources || 12

if (!run) { return { error: 'missing run_id in args' } }

if (A.dry_run === true) {
  return { status: 'dry_run', rf_bin: RF, repo: REPO, tmp_dir: TMP, stamp: STAMP, run, args: A }
}

// ---------- schemas ----------
const CAND_SCHEMA = {
  type: 'object', additionalProperties: true,
  required: ['sources'],
  properties: { sources: { type: 'array', items: {
    type: 'object', additionalProperties: true,
    required: ['url', 'title', 'source_type', 'source_rank', 'why', 'key_points'],
    properties: {
      url: { type: 'string' }, title: { type: 'string' },
      source_type: { type: 'string', enum: ['official_doc','paper','standard','repo','news','blog','book','other'] },
      published: { type: 'string' },
      source_rank: { type: 'string', enum: ['primary','secondary','tertiary','unknown'] },
      why: { type: 'string' },
      key_points: { type: 'array', items: { type: 'string' } },
    } } } },
}
const CARD_SCHEMA = { type: 'object', additionalProperties: true, required: ['source_card_id','ok','n_points'],
  properties: { source_card_id: { type: 'string' }, ok: { type: 'boolean' }, n_points: { type: 'number' }, note: { type: 'string' } } }
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

// ---------- shared spec strings ----------
const CARD_TEMPLATE =
'---\n' +
'schema_version: \'0.1\'\n' +
'type: source_card\n' +
'source_card_id: <ID>\n' +
'created_at: \'' + STAMP.slice(0,4) + '-' + STAMP.slice(4,6) + '-' + STAMP.slice(6,8) + 'T12:00:00-04:00\'\n' +
'created_by_agent: rf-swarm-carder\n' +
'sensitivity: personal\n' +
'source:\n' +
'  title: "<REAL TITLE>"\n' +
'  source_type: <official_doc|paper|standard|repo|news|blog|book|other>\n' +
'  locator: {url: "<REAL URL>", file_path: null, doi: null, repo: null}\n' +
'  authors: [<authors or empty>]\n' +
'  publisher: "<publisher or null>"\n' +
'  published_at: "<YYYY-MM or date or null>"\n' +
'  accessed_at: \'' + STAMP.slice(0,4) + '-' + STAMP.slice(4,6) + '-' + STAMP.slice(6,8) + 'T12:00:00-04:00\'\n' +
'  version: null\n' +
'trust: {source_rank: <primary|secondary|tertiary|unknown>, reliability_notes: "<short>", known_limitations: [], conflicts_with: []}\n' +
'usage: {allowed_for_public_output: false, allowed_for_work_output: true, allowed_for_personal_meatywiki: true, citation_required: true, quote_limit_notes: "Short excerpts only."}\n' +
'extracted_points:\n' +
'- evidence_id: ev_001\n' +
'  locator: "<section/heading/para>"\n' +
'  summary: "<ONE crisp factual sentence a report can cite>"\n' +
'  quote: "<VERBATIM quote from the source, <=280 chars, or null>"\n' +
'  supports_potential_claims: [clm_pending]\n' +
'- evidence_id: ev_002\n' +
'  locator: "..."\n' +
'  summary: "..."\n' +
'  quote: "..."\n' +
'  supports_potential_claims: [clm_pending]\n' +
'---\n' +
'# Source Card: <REAL TITLE>\n\n' +
'## Summary\n<2-3 sentence neutral summary of what this source establishes.>\n\n' +
'## Key evidence\n- (ev_001) <summary>\n- (ev_002) <summary>\n\n' +
'## Limitations\n- <caution, recency, or scope limit, or "None recorded.">\n'

const WRITE_RULE =
'IMPORTANT FILE-WRITE RULE: never use the Write/Edit tools on any path under ' + REPO + '/runs (the shared checkout rejects tool-edits there). ' +
'Instead: use the Write tool to author the file under ' + TMP + '/ , then run Bash `cp ' + TMP + '/<name> <dest>` to place it. ' +
'Always `cd ' + REPO + '` before running `rf` or git/ls on the run.'

// ---------- helpers (pure JS) ----------
function norm(u){ return (u||'').toLowerCase().replace(/^https?:\/\//,'').replace(/\/$/,'').replace(/[#?].*$/,'') }
function dedupe(list){ const seen=new Set(); const out=[]; for(const s of list){ const k=norm(s.url)||(s.title||'').toLowerCase().trim(); if(!k||seen.has(k)) continue; seen.add(k); out.push(s) } return out }
const RANKW={primary:0,secondary:1,tertiary:2,unknown:3}
function rankSources(list){ return list.slice().sort((a,b)=>(RANKW[a.source_rank]??3)-(RANKW[b.source_rank]??3)) }

// ---------- prompt builders ----------
function discoveryPrompt(ang){
  return 'Mode: A — research discovery. You are a source scout for a Research Foundry run.\n\n' +
  'RESEARCH FOCUS: ' + ang.focus + '\n' +
  'OVERALL QUESTION: ' + A.question + '\n' +
  'FRESHNESS: prefer sources published/updated within the last ' + (A.freshness_days||180) + ' days (roughly since late 2025); today is 2026-06-13. Older sources are allowed only for stable/foundational facts and must be marked tertiary.\n\n' +
  'DO REAL WEB RESEARCH. Load and use web tools: run ToolSearch query "select:WebSearch,WebFetch" (and you may use the firecrawl skill / mcp__claude-in-chrome if helpful). Find 5-9 AUTHORITATIVE, current sources for the focus above. Strongly prefer PRIMARY sources: official documentation, vendor pricing pages, official GitHub repos/changelogs, arXiv/peer-reviewed papers, standards. Avoid SEO blogspam and undated content.\n' +
  (ang.local_refs && ang.local_refs.length ? ('ALSO read these local seed files (they are primary context, source_rank primary) and include any that contain citable facts: ' + ang.local_refs.join(' ; ') + '\n') : '') +
  '\nFor each source return: url (real, resolvable), title, source_type, published (YYYY-MM or date; best estimate, "unknown" only if truly absent), source_rank, why (1 sentence: what citable facts it yields for THIS focus), key_points (3-6 short strings, each an extractable factual claim with a number/name/date where possible).\n' +
  'Do NOT fabricate URLs or facts. If you cannot verify a URL resolves, drop it. Return ONLY sources you actually opened or are highly confident are real and on-topic.'
}

function carderPrompt(s, i){
  const id = 'src_' + STAMP + '_' + refslug + '_' + String(i).padStart(2,'0')
  return 'Mode: produce one Research Foundry SOURCE CARD from a real source. ' + WRITE_RULE + '\n\n' +
  'SOURCE: ' + JSON.stringify({url:s.url,title:s.title,source_type:s.source_type,source_rank:s.source_rank,published:s.published,key_points:s.key_points}) + '\n\n' +
  'STEP 1 — DEEP READ: fetch and read the source at the URL (load web tools via ToolSearch "select:WebSearch,WebFetch"; or firecrawl). If it is a local file path, read it directly. Extract 4-8 evidence points that are MATERIAL and citable. For each: a one-sentence factual `summary` (what a report will assert), a VERBATIM `quote` copied exactly from the source (<=280 chars; set quote: null ONLY if no short verbatim excerpt fits), and a human `locator` (section title / heading / "p.N" / para). Capture real `authors`, `publisher`, `published_at` if visible. NEVER invent quotes or numbers — if you cannot confirm a fact from the actual source text, omit it. If the source will not load at all, set ok=false and n_points=0 and stop.\n\n' +
  'STEP 2 — AUTHOR THE CARD: fill this exact template (keep all keys; valid YAML frontmatter; extracted_points one block per evidence point, ev_001..ev_00N):\n' + CARD_TEMPLATE + '\n' +
  'Use source_card_id EXACTLY: ' + id + '  (and sensitivity: personal). source.locator.url must be the real URL. trust.source_rank from the source.\n\n' +
  'STEP 3 — PLACE IT: Write the completed markdown to ' + TMP + '/' + id + '.md (Write tool), then Bash: `cp ' + TMP + '/' + id + '.md ' + REPO + '/runs/' + run + '/sources/' + id + '.md` and `ls -la ' + REPO + '/runs/' + run + '/sources/' + id + '.md` to confirm.\n' +
  'Return source_card_id=' + id + ', ok=true if the card was written with >=2 real evidence points (else ok=false), n_points, and a one-line note.'
}

function tailPrompt(){
  return 'Mode: run the Research Foundry deterministic extraction tail. ' + WRITE_RULE + '\n\n' +
  'Run these and capture exit codes:\n' +
  '1) `cd ' + REPO + ' && ' + RF + ' extract ' + run + '`  (creates extraction cards from every source card)\n' +
  '2) `cd ' + REPO + ' && ' + RF + ' claim-map ' + run + '`  (builds claims/claim_ledger.yaml; one supported claim per evidence point)\n' +
  'Then Read ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml and return EVERY claim as {claim_id, text} plus claim_count. ' +
  'ok=true only if both commands exited 0 and claim_count > 0. Report exit_extract and exit_claimmap.'
}

function analystPrompt(claims){
  const ids = claims.map(c=>c.claim_id)
  return 'Mode: analytical synthesis for a Research Foundry run (the critic/synthesizer). ' + WRITE_RULE + '\n\n' +
  'OVERALL QUESTION: ' + A.question + '\n' +
  'PRIMARY RESEARCH QUESTIONS:\n- ' + (A.primary||[]).join('\n- ') + '\n' +
  (A.secondary && A.secondary.length ? ('SECONDARY:\n- ' + A.secondary.join('\n- ') + '\n') : '') +
  'SUCCESS CRITERIA (the deliverable must satisfy these):\n- ' + (A.success||[]).join('\n- ') + '\n' +
  'REUSABLE OUTPUTS the run should yield: ' + (A.reusable||[]).join(', ') + '\n\n' +
  'The deterministic claim-map has produced these SUPPORTED claims (each backed by a source card):\n' +
  claims.map(c=>c.claim_id + ': ' + c.text).join('\n') + '\n\n' +
  'TASK: Read all source cards in ' + REPO + '/runs/' + run + '/sources/ and the ledger ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml. ' +
  'Then author the ANALYTICAL LAYER as new claims that answer the research questions and satisfy the success criteria: cross-source comparisons, verdicts/rankings, break-even or cost/quality conclusions, recommendations, and decision/selection rules. ' +
  'Each new claim is an INFERENCE (a conclusion you draw from >=1 supported claim) or a SPECULATION (forward-looking/uncertain). Author ' + (A.depth==='deep' ? '12-20' : '8-12') + ' such claims — substantive and specific (name tools/models/numbers), not vague.\n\n' +
  'APPEND each new claim to the `claims:` list in claim_ledger.yaml using EXACTLY this entry shape (valid YAML; 2-space indent under the list):\n' +
  '- claim_id: clm_inf01            # unique; use prefix clm_inf## for inference, clm_spec## for speculation; MUST NOT collide with existing ids: ' + ids.join(',') + '\n' +
  '  text: "<one crisp analytic sentence — the conclusion>"\n' +
  '  materiality: material\n' +
  '  claim_type: <comparative|causal|recommendation|prediction|quantitative|factual>\n' +
  '  status: <inference|speculation>\n' +
  '  confidence: <low|medium|high>\n' +
  '  sources: []\n' +
  '  inference_basis: {from_claims: [<real existing clm ids this follows from>], reasoning_summary: "<why this follows>"}   # REQUIRED & NON-EMPTY for status: inference; for status: speculation use inference_basis: {from_claims: [], reasoning_summary: "<basis or assumption>"}\n' +
  '  report_locations: []\n' +
  '  reviewer_notes: ""\n\n' +
  'To edit the ledger safely: Read the current file, append your entries under `claims:`, write the FULL updated YAML to ' + TMP + '/ledger_' + run + '.yaml, then Bash `cp ' + TMP + '/ledger_' + run + '.yaml ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml`. ' +
  'Do NOT run `rf claim-map` again (it would overwrite your additions). Keep the YAML valid (no tabs; quote strings with colons).\n\n' +
  'Return: appended = [{claim_id, status} ...]; outline = a short section-by-section plan for the final ' + A.artifact_type + ' naming which claim_ids belong in each section (Executive summary, the required matrix/table, analysis/derivation, recommendations, open questions); ok=true.'
}

function synthPrompt(){
  return 'Mode: run Research Foundry synthesis (deterministic, verify-passing baseline). ' + WRITE_RULE + '\n\n' +
  '1) `cd ' + REPO + ' && ' + RF + ' synthesize ' + run + ' --deterministic --draft`  (writes reports/report_draft.md citing every ledger claim by [claim:<id>], labeling inference/speculation).\n' +
  '2) Back it up: Bash `cp ' + REPO + '/runs/' + run + '/reports/report_draft.md ' + REPO + '/runs/' + run + '/reports/report_deterministic.md` (this is the guaranteed-passing fallback — do not delete it).\n' +
  'Return ok=(exit 0 and report_draft.md non-empty), exit, and a one-line detail with the report line count.'
}

function enrichPrompt(claims, appended){
  return 'Mode: upgrade the run report into the real deliverable. ' + WRITE_RULE + '\n\n' +
  'TARGET ARTIFACT: a ' + A.artifact_type + ' titled "' + A.title + '" for a technical audience. It must satisfy these success criteria:\n- ' + (A.success||[]).join('\n- ') + '\n\n' +
  'INPUT: ' + REPO + '/runs/' + run + '/reports/report_draft.md is the deterministic baseline — it already contains one tagged sentence per ledger claim. Read it, plus the ledger ' + REPO + '/runs/' + run + '/claims/claim_ledger.yaml.\n\n' +
  'REWRITE report_draft.md into a polished ' + A.artifact_type + ' with: an Executive summary, the required matrix/comparison table(s), the analytical/derivation section, explicit recommendations / decision rules, and an Open questions section. Use ONLY claims already in the ledger (supported clm_* and the inference/speculation clm_inf*/clm_spec*).\n\n' +
  'VERIFY-GATE RULES (the report is checked by `rf verify`; breaking these fails the run):\n' +
  '1. Every material sentence (any factual/quantitative/comparative/causal/attribution/recommendation/prediction assertion) MUST end with its citation tag of the form [claim:clm_xxx] — reuse the exact tags from the baseline; one material claim per line.\n' +
  '2. Inference/speculation sentences keep BOTH their bold label (**Inference:** or **Speculation:**) AND their [claim:...] tag.\n' +
  '3. Do not write any new material sentence that lacks a [claim:...] tag. Section intro lines must be non-assertive (no facts) or omitted. Questions go under "## Open questions" and end with "?".\n' +
  '4. Tables: each data row that states a material/quantitative fact must carry its [claim:clm_xxx] tag in a trailing "Evidence" column. Header/label rows need no tag. Keep one claim per row.\n' +
  '5. Keep a "## Sources" section (exempt from claim checks) listing each source_card_id: title.\n' +
  '6. Preserve the YAML frontmatter (audience: technical, sensitivity: personal); you may update title/status but keep all keys.\n' +
  '7. Do not invent claim ids. Every [claim:...] must resolve to an id in the ledger. Do not call rf claim-map.\n\n' +
  'Author the rewrite to ' + TMP + '/report_' + run + '.md, then Bash `cp ' + TMP + '/report_' + run + '.md ' + REPO + '/runs/' + run + '/reports/report_draft.md`. Return ok=true, a one-line detail (section count).'
}

function verifyPrompt(tag){
  return 'Mode: run rf verify and report. ' + WRITE_RULE + '\n\n' +
  '`cd ' + REPO + ' && ' + RF + ' verify ' + run + '`  — capture the EXACT exit code (echo $?). Then Read ' + REPO + '/runs/' + run + '/reviews/verification.yaml. ' +
  'Return exit (the integer exit code), passed=(exit==0), and failures=[{check, detail}] for every failed/blocking check (empty if passed). Do not modify any files.'
}

function fixPrompt(failures){
  return 'Mode: repair the report so `rf verify` passes. ' + WRITE_RULE + '\n\n' +
  'rf verify on run ' + run + ' is FAILING. Failures:\n' + JSON.stringify(failures) + '\n\n' +
  'Read ' + REPO + '/runs/' + run + '/reports/report_draft.md, ' + REPO + '/runs/' + run + '/reviews/verification.yaml, and the ledger. Fix ONLY what verify flags:\n' +
  '- "unsupported"/untagged material sentence: append the correct existing [claim:clm_xxx] tag (match the sentence to the best ledger claim by meaning); if it is genuinely a NEW analytic statement, either (a) append a new inference claim to claim_ledger.yaml (status: inference, inference_basis.from_claims non-empty) and tag the sentence, or (b) rephrase it as a question under "## Open questions", or (c) move it under "## Sources". Never leave a material sentence untagged.\n' +
  '- "all_claim_ids_exist": fix any [claim:...] whose id is not in the ledger (correct the id or add the claim).\n' +
  '- "inferences_have_basis": add inference_basis.from_claims to the offending ledger claim.\n' +
  '- "*_is_labeled": add the missing **Inference:**/**Speculation:**/**Mixed evidence:** label to that sentence.\n' +
  '- "supported_claims_have_source_cards": ensure the cited source_card_id has a file in runs/' + run + '/sources/.\n' +
  'Edit ledger/report via the TMP+cp pattern. Do NOT run rf claim-map. Return ok=true and a one-line detail of what you changed.'
}

function fallbackPrompt(){
  return 'Mode: restore the guaranteed-passing report. ' + WRITE_RULE + '\n\n' +
  'Enrichment could not pass verify. Restore the deterministic baseline: Bash `cp ' + REPO + '/runs/' + run + '/reports/report_deterministic.md ' + REPO + '/runs/' + run + '/reports/report_draft.md`. ' +
  'Then `cd ' + REPO + ' && ' + RF + ' verify ' + run + '` and confirm exit 0. Return ok=(exit 0), exit, detail="reverted to deterministic report".'
}

function bundlePrompt(){
  return 'Mode: adversarial audit then publish the evidence bundle. ' + WRITE_RULE + '\n\n' +
  'STEP 1 — AUDIT: Read ' + REPO + '/runs/' + run + '/reports/report_draft.md and claims/claim_ledger.yaml. Confirm every [claim:...] tag resolves to a ledger claim and every material sentence is tagged. If you find a problem, fix it minimally (TMP+cp; you may append an inference claim with basis). Do not run rf claim-map.\n' +
  'STEP 2 — BUNDLE: `cd ' + REPO + ' && ' + RF + ' bundle ' + run + ' --verify`  (must exit 0; if it fails, read verification.yaml, fix, retry once).\n' +
  'STEP 3 — WRITEBACK: `cd ' + REPO + ' && ' + RF + ' writeback ' + run + ' --targets meatywiki,skillmeat,ccdash --no-require-review`.\n' +
  'Return ok=(bundle exit 0), exit, detail = evidence_bundle.yaml path + claim/source counts + writeback files created.'
}

// ====================== ORCHESTRATION ======================
log('RF run ' + run + ' (' + A.ref + ', ' + A.artifact_type + ', depth=' + A.depth + ') — ' + (A.angles||[]).length + ' discovery angles, up to ' + MAXS + ' sources')

// Phase 1: Discover (parallel angles — barrier; we need all candidates before ranking/selecting)
phase('Discover')
const candRaw = await parallel((A.angles||[]).map((ang) => () =>
  agent(discoveryPrompt(ang), { label: 'discover:' + ang.label, phase: 'Discover', schema: CAND_SCHEMA })))
const allCand = dedupe(candRaw.filter(Boolean).flatMap(c => (c.sources || [])))
const selected = rankSources(allCand).slice(0, MAXS)
log('discovery: ' + allCand.length + ' unique candidates -> ' + selected.length + ' selected')
if (selected.length === 0) { return { ref: A.ref, run_id: run, error: 'no sources discovered' } }

// Phase 2: SourceCards (parallel carders — barrier; extract needs all cards present)
phase('SourceCards')
const cardRes = await parallel(selected.map((s, i) => () =>
  agent(carderPrompt(s, i), { label: 'card:' + String(i).padStart(2,'0'), phase: 'SourceCards', schema: CARD_SCHEMA })))
const okCards = cardRes.filter(Boolean).filter(c => c.ok)
log('source cards written: ' + okCards.length + '/' + selected.length)
if (okCards.length === 0) { return { ref: A.ref, run_id: run, error: 'no source cards authored' } }

// Phase 3: Evidence (rf extract + claim-map)
phase('Evidence')
const tail = await agent(tailPrompt(), { label: 'extract+claim-map', phase: 'Evidence', schema: TAIL_SCHEMA })
if (!tail || !tail.ok || !(tail.claims||[]).length) { return { ref: A.ref, run_id: run, cards: okCards.length, error: 'extract/claim-map produced no claims', tail } }
log('claims supported: ' + tail.claim_count)

// Phase 4: Analysis (append inference/speculation claims)
phase('Analysis')
const infer = await agent(analystPrompt(tail.claims), { label: 'analyst', phase: 'Analysis', schema: INFER_SCHEMA })
log('analytical claims appended: ' + ((infer && infer.appended) ? infer.appended.length : 0))

// Phase 5: Synthesize (deterministic baseline + backup)
phase('Synthesize')
const synth = await agent(synthPrompt(), { label: 'synthesize', phase: 'Synthesize', schema: STEP_SCHEMA })

// Phase 6: Enrich
phase('Enrich')
const enrich = await agent(enrichPrompt(tail.claims, (infer && infer.appended) || []), { label: 'enrich', phase: 'Enrich', schema: STEP_SCHEMA })

// Phase 7: Verify loop with deterministic fallback
phase('Verify')
let v = await agent(verifyPrompt('v0'), { label: 'verify', phase: 'Verify', schema: VERIFY_SCHEMA })
let tries = 0
while (v && v.exit !== 0 && tries < 3) {
  tries++
  await agent(fixPrompt(v.failures || []), { label: 'fix:' + tries, phase: 'Verify', schema: STEP_SCHEMA })
  v = await agent(verifyPrompt('v' + tries), { label: 'verify:' + tries, phase: 'Verify', schema: VERIFY_SCHEMA })
}
let degraded = false
if (!v || v.exit !== 0) {
  degraded = true
  const fb = await agent(fallbackPrompt(), { label: 'fallback', phase: 'Verify', schema: STEP_SCHEMA })
  v = await agent(verifyPrompt('vfb'), { label: 'verify:fallback', phase: 'Verify', schema: VERIFY_SCHEMA })
}
log('verify exit=' + (v ? v.exit : 'n/a') + ' (tries=' + tries + (degraded ? ', enrichment reverted to deterministic' : '') + ')')

// Phase 8: Bundle + writeback
phase('Bundle')
const bundle = await agent(bundlePrompt(), { label: 'bundle+writeback', phase: 'Bundle', schema: STEP_SCHEMA })

return {
  ref: A.ref, run_id: run, artifact: A.artifact_type, depth: A.depth,
  candidates: allCand.length, selected: selected.length, source_cards: okCards.length,
  claims_supported: tail.claim_count, claims_analytical: ((infer && infer.appended) || []).length,
  verify_exit: v ? v.exit : null, verify_tries: tries, enrichment_degraded: degraded,
  bundle: bundle ? bundle.detail : null, bundle_ok: bundle ? bundle.ok : false,
}
