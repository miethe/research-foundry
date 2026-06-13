// research-foundry-council.js
//
// Offline council gate for a Research Foundry run — no arc server required.
// Fans out four independent reviewer agents over runs/<run_id>/ report + claim ledger,
// then an adjudicator synthesizes a single verdict.
//
// RF exit-code semantics:
//   The returned verdict.rf_exit_code maps to RF's `rf council` semantics:
//   0 = approved, 7 = human review required (maps to RF exit code 7 "human review required").
//   Opus post-run must call `rf council approve <run_id>` or `rf council request-review <run_id>`
//   based on the verdict.
//
// Workflow args may arrive as a JSON string from the Workflow tool.
// Always parse at the top before destructuring.
const parsedArgs = typeof args === 'string' ? JSON.parse(args) : args

export const meta = {
  name: 'research-foundry-council',
  description: 'Offline council gate (no arc server) for a Research Foundry run. Fans out domain-research-reviewer, correctness-reviewer, architecture-reviewer, and evaluator-reviewer agents in parallel over runs/<run_id>/ report and claim ledger, then a council-coordinator synthesizes a single approve | concern | block verdict. Maps verdict to RF exit-code 0 (approved) or 7 (human review required). Accept run_id via args. Use before `rf bundle` when `rf verify` exits 7 or when governance requires multi-lens sign-off.',
  phases: [
    { title: 'Review' },
    { title: 'Adjudicate' },
  ],
  whenToUse: 'Use when `rf verify` exits 7 (human review required), when a run requires multi-lens council sign-off before bundling, or as a standalone governance gate. Requires runs/<run_id>/reports/report_draft.md and runs/<run_id>/claims/claim_ledger.yaml to exist.',
}

// === Script body ===

const { run_id, timestamp, dry_run, profile } = parsedArgs

if (!run_id) {
  return {
    status: 'blocked',
    reason: 'missing_run_id',
    report: [],
    error: 'args.run_id is required. Pass the RF run identifier (e.g. "rf_run_20260613_topic").',
  }
}

if (dry_run === true) {
  return {
    status: 'dry_run',
    parsed_args: parsedArgs,
  }
}

// Canonical artifact paths derived from run_id (Opus confirms these exist pre-flight).
const reportPath = `runs/${run_id}/reports/report_draft.md`
const claimLedgerPath = `runs/${run_id}/claims/claim_ledger.yaml`
const runDir = `runs/${run_id}/`

// ── Shared schemas ─────────────────────────────────────────────────────────────

const REVIEWER_FINDING_SCHEMA = {
  type: 'object',
  properties: {
    reviewer_role: { type: 'string' },
    vote: { type: 'string', enum: ['approve', 'concern', 'block'] },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
          description: { type: 'string' },
          recommendation: { type: 'string' },
        },
        required: ['id', 'title', 'severity', 'description'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['reviewer_role', 'vote', 'findings', 'summary'],
}

// ── Phase 1: Review ────────────────────────────────────────────────────────────
// Four parallel reviewer agents — all edit-less — each returns structured findings + vote.
phase('Review')
log(`[research-foundry-council] Phase 1 — Review: fanning out 4 parallel council reviewers for run "${run_id}"`)

// Shared context block injected into all reviewer prompts.
const REVIEW_CONTEXT = `
Run: ${run_id}
Report: ${reportPath}
Claim ledger: ${claimLedgerPath}
Run directory: ${runDir}
Profile: ${profile || 'personal'}
Timestamp: ${timestamp || 'not set'}

You are a council reviewer. Your job is to independently assess the Research Foundry run's
report and claim ledger. Do NOT coordinate with other reviewers — this is an independent pass.
Do NOT implement any fixes, edit any files, or run rf commands.
`

const reviewerThunks = [
  // 1. Domain Research Reviewer — assesses source quality and coverage.
  () => agent(
    `Mode: E — Reviewer. Do NOT git add/commit/push/stash. Do NOT edit any files.
${REVIEW_CONTEXT}

You are the DOMAIN RESEARCH REVIEWER (reviewer_role: "domain-research-reviewer").

Review the report and claim ledger for:
1. Source coverage: are the key topics in the research question adequately covered by ingested sources?
2. Source quality: are the cited sources authoritative, current, and appropriate for the sensitivity level?
3. Domain accuracy: are domain-specific claims accurate and consistent with the cited sources?
4. Coverage gaps: are there significant topic areas mentioned in the report with no supporting source cards?
5. Staleness: are any sources too old to support the claims they back?

Read ${reportPath} and ${claimLedgerPath}. Look for source cards in ${runDir}sources/.

Cast your vote:
- "approve": sources are adequate, authoritative, and claims are well-supported.
- "concern": sources have gaps or quality issues that should be addressed but are not blocking.
- "block": critical source gaps or domain inaccuracies that must be resolved before bundling.

Return a ReviewerOutput object with reviewer_role, vote, findings array, and a one-paragraph summary.`,
    {
      label: 'domain-research-reviewer',
      phase: 'Review',
      agentType: 'senior-code-reviewer',
      model: 'sonnet',
      schema: REVIEWER_FINDING_SCHEMA,
    }
  ),

  // 2. Correctness Reviewer — verifies claim traceability and ledger integrity.
  () => agent(
    `Mode: E — Reviewer. Do NOT git add/commit/push/stash. Do NOT edit any files.
${REVIEW_CONTEXT}

You are the CORRECTNESS REVIEWER (reviewer_role: "correctness-reviewer").

Review the report and claim ledger for:
1. Claim traceability: every material claim in the report must cite a claim_id from the ledger, or be labeled "inference" or "speculation".
2. Ledger completeness: are all claim_ids referenced in the report actually present in the claim ledger?
3. Ledger integrity: does each ledger entry have a valid source_card reference in runs/${run_id}/sources/?
4. Label discipline: are "inference" and "speculation" labels used appropriately (not to dodge sourcing)?
5. Unsupported claims: are there any material claims with no ledger entry and no inference/speculation label?

Read ${reportPath} and ${claimLedgerPath}. Cross-check claim_ids systematically.

Cast your vote:
- "approve": all material claims are traceable; ledger is complete and internally consistent.
- "concern": minor traceability gaps that should be fixed but don't invalidate the report.
- "block": unsupported material claims or broken ledger references that must be fixed before bundling.

Return a ReviewerOutput object with reviewer_role, vote, findings array, and a one-paragraph summary.`,
    {
      label: 'correctness-reviewer',
      phase: 'Review',
      agentType: 'task-completion-validator',
      model: 'sonnet',
      schema: REVIEWER_FINDING_SCHEMA,
    }
  ),

  // 3. Architecture Reviewer — assesses report structure and synthesis quality.
  () => agent(
    `Mode: E — Reviewer. Do NOT git add/commit/push/stash. Do NOT edit any files.
${REVIEW_CONTEXT}

You are the ARCHITECTURE REVIEWER (reviewer_role: "architecture-reviewer").

Review the report for:
1. Synthesis quality: does the report synthesize sources into coherent findings, or is it just a list of summaries?
2. Structure: does the report have clear sections (question, methodology, findings, conclusions, limitations)?
3. Internal consistency: do the conclusions follow from the findings? Are there logical contradictions?
4. Scope alignment: does the report address the original research question stated in the brief?
5. Limitations section: are the report's limitations and confidence levels stated honestly?

Read ${reportPath} and ${runDir}research_brief.md.

Cast your vote:
- "approve": report is well-structured, synthesized, and internally consistent.
- "concern": structural or synthesis issues that weaken the report but can be addressed.
- "block": fundamental structural failures or scope misalignment that require a rewrite before bundling.

Return a ReviewerOutput object with reviewer_role, vote, findings array, and a one-paragraph summary.`,
    {
      label: 'architecture-reviewer',
      phase: 'Review',
      agentType: 'code-reviewer',
      model: 'sonnet',
      schema: REVIEWER_FINDING_SCHEMA,
    }
  ),

  // 4. Evaluator Reviewer — adversarial pass challenging key claims and conclusions.
  () => agent(
    `Mode: E — Reviewer. Do NOT git add/commit/push/stash. Do NOT edit any files.
${REVIEW_CONTEXT}

You are the EVALUATOR REVIEWER (reviewer_role: "evaluator-reviewer"). This is an adversarial pass.

Your job is to challenge the report's key claims and conclusions:
1. Identify the 3-5 most important factual claims in the report.
2. For each claim: what is the strongest counter-argument or alternative interpretation?
3. Are any conclusions overstated given the evidence strength?
4. Are there known alternative viewpoints or contradicting sources NOT cited?
5. Are any claims presented as settled when they are actually contested in the field?

Read ${reportPath} and ${claimLedgerPath}. Be skeptical. Your goal is to surface weaknesses
the other reviewers might miss, not to find reasons to block without cause.

Cast your vote:
- "approve": key claims are defensible under adversarial scrutiny; overstatements are minor.
- "concern": some claims are overstated or missing important caveats; report should be qualified.
- "block": core conclusions are contradicted by evidence or are substantially misleading.

Return a ReviewerOutput object with reviewer_role, vote, findings array, and a one-paragraph summary.`,
    {
      label: 'evaluator-reviewer',
      phase: 'Review',
      agentType: 'karen',
      model: 'sonnet',
      schema: REVIEWER_FINDING_SCHEMA,
    }
  ),
]

const reviewerOutputs = await parallel(reviewerThunks)

const validReviewerOutputs = reviewerOutputs.filter(Boolean)

if (validReviewerOutputs.length === 0) {
  return {
    status: 'needs_opus',
    reason: 'all_reviewers_failed',
    report: [{ phase: 'Review', reviewers_run: 0 }],
    error: 'All four council reviewer agents returned null. Check agent availability and run artifacts.',
  }
}

log(`[research-foundry-council] Review complete — ${validReviewerOutputs.length}/4 reviewers returned. Votes: ${validReviewerOutputs.map(r => r.vote).join(', ')}`)

// ── Phase 2: Adjudicate ────────────────────────────────────────────────────────
// council-coordinator synthesizes reviewer outputs into a single verdict.
phase('Adjudicate')
log('[research-foundry-council] Phase 2 — Adjudicate: council-coordinator synthesizing verdict')

const ADJUDICATION_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'concern', 'block'] },
    rationale: { type: 'string' },
    blocking_findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          reviewer_role: { type: 'string' },
          finding_id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string' },
          recommendation: { type: 'string' },
        },
        required: ['reviewer_role', 'finding_id', 'title', 'severity'],
      },
    },
    concern_findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          reviewer_role: { type: 'string' },
          finding_id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string' },
        },
        required: ['reviewer_role', 'finding_id', 'title', 'severity'],
      },
    },
    required_actions: { type: 'array', items: { type: 'string' } },
    recommended_actions: { type: 'array', items: { type: 'string' } },
    vote_summary: {
      type: 'object',
      properties: {
        approve: { type: 'number' },
        concern: { type: 'number' },
        block: { type: 'number' },
      },
      required: ['approve', 'concern', 'block'],
    },
  },
  required: ['verdict', 'rationale', 'blocking_findings', 'concern_findings', 'vote_summary'],
}

const adjudicationResult = await agent(
  `Mode: E — Reviewer. Do NOT git add/commit/push/stash. Do NOT edit any files.

You are the COUNCIL COORDINATOR for Research Foundry run "${run_id}".

You have received independent review outputs from ${validReviewerOutputs.length} council reviewers.
Your job is to synthesize their findings into a single authoritative council verdict.

Reviewer outputs:
${JSON.stringify(validReviewerOutputs, null, 2)}

Adjudication rules:
1. BLOCK verdict: any "block" vote from any reviewer => overall verdict is "block" (unless clearly erroneous).
2. CONCERN verdict: two or more "concern" votes with no "block" => verdict is "concern".
3. APPROVE verdict: all votes are "approve", or at most one "concern" with no substantial findings.
4. Deduplication: if multiple reviewers flag the same issue, consolidate into one finding.
5. Dissent: record any reviewer whose vote was overridden in the rationale.

For the RF exit-code mapping:
- "approve" => rf_exit_code: 0 (council approved, safe to bundle)
- "concern" => rf_exit_code: 7 (human review required before bundle — concerns must be addressed)
- "block"   => rf_exit_code: 7 (human review required — blocking issues must be resolved)

Return the adjudication object with:
- verdict: "approve" | "concern" | "block"
- rationale: 2-3 sentence explanation of the verdict
- blocking_findings: findings from "block"-voting reviewers (deduped)
- concern_findings: findings from "concern"-voting reviewers (deduped)
- required_actions: list of actions needed before bundling (for "block"/"concern" verdicts)
- recommended_actions: nice-to-have improvements (for any verdict)
- vote_summary: { approve: N, concern: N, block: N }`,
  {
    label: 'council-coordinator',
    phase: 'Adjudicate',
    agentType: 'task-completion-validator',
    model: 'sonnet',
    schema: ADJUDICATION_SCHEMA,
  }
)

// ── Map verdict to RF semantics ────────────────────────────────────────────────
// RF exit code 7 = "human review required" (rf council semantics).
// 0 = approved / clean pass.

let rfExitCode = 7  // default conservative
let councilStatus = 'needs_review'

if (adjudicationResult && adjudicationResult.verdict === 'approve') {
  rfExitCode = 0
  councilStatus = 'approved'
}

// Recount from raw outputs in case adjudicator summary is missing.
const actualVotes = { approve: 0, concern: 0, block: 0 }
for (const output of validReviewerOutputs) {
  if (output.vote in actualVotes) {
    actualVotes[output.vote]++
  }
}

log(`[research-foundry-council] Adjudication complete — verdict: ${adjudicationResult?.verdict || 'unknown'}, rf_exit_code: ${rfExitCode}`)
log(`[research-foundry-council] Vote counts: approve=${actualVotes.approve}, concern=${actualVotes.concern}, block=${actualVotes.block}`)

if (rfExitCode === 7) {
  log('[research-foundry-council] Exit code 7: human review required. Opus must run `rf council` and obtain sign-off before `rf bundle`.')
} else {
  log('[research-foundry-council] Exit code 0: council approved. Safe to proceed to `rf bundle`.')
}

return {
  status: rfExitCode === 0 ? 'complete' : 'needs_opus',
  run_id,
  timestamp,
  verdict: {
    council_verdict: adjudicationResult?.verdict || 'unknown',
    rf_exit_code: rfExitCode,
    council_status: councilStatus,
    rationale: adjudicationResult?.rationale || 'Adjudication returned no result.',
    blocking_findings: adjudicationResult?.blocking_findings || [],
    concern_findings: adjudicationResult?.concern_findings || [],
    required_actions: adjudicationResult?.required_actions || [],
    recommended_actions: adjudicationResult?.recommended_actions || [],
    vote_summary: actualVotes,
    reviewer_outputs: validReviewerOutputs,
    rf_council_commands: rfExitCode === 0
      ? [`rf bundle ${run_id} --verify --out evidence_bundle.yaml`]
      : [
          `# Address required actions first, then:`,
          `rf council approve ${run_id}  # after human review confirms resolution`,
          `rf bundle ${run_id} --verify --out evidence_bundle.yaml`,
        ],
  },
  report: [
    {
      phase: 'Review',
      reviewers_dispatched: 4,
      reviewers_returned: validReviewerOutputs.length,
      votes: actualVotes,
    },
    {
      phase: 'Adjudicate',
      verdict: adjudicationResult?.verdict || 'unknown',
      blocking_count: (adjudicationResult?.blocking_findings || []).length,
      concern_count: (adjudicationResult?.concern_findings || []).length,
      rf_exit_code: rfExitCode,
    },
  ],
}
