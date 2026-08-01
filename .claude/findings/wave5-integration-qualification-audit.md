---
title: "Wave-5 Integration & Qualification — Pre-Execution Audit"
doc_type: findings
schema_version: 2
status: complete
created: 2026-07-31
updated: 2026-07-31
feature_slug: wave5-integration-qualification
feature_version: v1
audit_scope: ".codex/plans/research-interchange-provenance-access-initiative-v1.md §6 Wave 5 · §7 DG-6 · §9 Completion Rules"
audit_tree: 1c8dfc9
method: "Four parallel read-only audit legs (artifact completeness · cross-child chain test coverage · docs/CHANGELOG/skills currency · DG-6 evidence separation), findings verified against git where prose and repository state disagreed."
tags: [wave5, dg-6, integration, qualification, epic-closeout, audit]
---

# Wave-5 Integration & Qualification — Pre-Execution Audit

Audit of the epic's final wave against the meta-plan's own completion rules, performed
at tree `1c8dfc9`. Every claim below was checked on disk; where a planning document's
prose disagreed with repository state, **git is treated as authoritative** and the
stale prose is recorded as a reconciliation item.

## 0. Precondition — children are landed

| Child | Pts | Landed | Evidence |
|---|---|---|---|
| C1 Research Provenance Continuity | 40 | yes | squash `65d658d`; RPC-7.G closed |
| C2 External Research Report Interchange | 38 | yes | squash `e76784b`; final tree `dd5ae1e` |
| C3 Catalog-Assisted Research Planning | 28 | yes | squash `95e8419`; CARP-6.G closed |
| C4 Knowledge MCP (read-only) | 34 | yes | squash `1376e85` + 3 follow-ons |
| C5 Operator MCP (governed) | 29 | yes | **PR #7 MERGED** `2026-08-01T01:12:56Z`, merge commit `0afb56d` |

`origin/main == main == 1c8dfc9`; `src/research_foundry/operator_mcp/server.py` is
present on `origin/main`. Wave-5 preconditions are satisfied.

> **Correction of record.** The C5 implementation plan's "Execution Status" section
> still reads *"Still not merged to main — merge is a human decision on PR #7."* That
> sentence is now false and is a reconciliation item (R-5 below), not evidence of an
> unmerged child. Project memory carrying "PR #7 awaiting human merge" is likewise
> superseded.

## 1. What §9 already satisfies

These completion rules are **met** and require no remediation:

- **Child artifact completeness.** All five children have a PRD, unified implementation
  plan, human brief, and a decisions block. Decisions blocks live at
  `.codex/worknotes/<slug>/decisions-block.md` (161–433 lines each) by the meta-plan's
  own §3 routing — their absence from plan bodies is by design, not a gap.
- **Strict validation.** All five implementation plans pass
  `validate_artifact.py --strict` with exit 0.
- **Estimate reconciliation without package discount.** 40+38+28+34+29 = **169**, and
  each child's task/milestone table sums exactly to its H4-locked total.
- **Deferred items have shaping specs.** All three deferred tracks have specs on disk at
  `maturity: shaping` — NotebookLM refresh, browser capture extension, and the Knowledge
  MCP remote profile (the last being *three* specs that §8 requires to promote together,
  not one).
- **Architecture/user documentation.** Every child has both an architecture doc and a
  user/dev guide (see §5 below). No missing or contradicted docs were found.
- **Skill currency.** `research-foundry`, `rf-knowledge`, and `research-foundry-swarm`
  skills were verified against live CLI source (`cli_commands.py`,
  `cli/commands/knowledge.py`) — accurate, no stale text.

## 2. The engineering core — cross-child chain is untested

§6 Wave 5 requires fixtures spanning: external handoff → source resolution → assertion
verification → catalog reuse → report-use lineage → read-only retrieval → governed
operator action. §9 requires "cross-child contract tests cover the full provenance chain."

**Every child is well covered in isolation; the chain between them is essentially untested.**

Existing cross-child contact is limited to:

- `tests/unit/test_operator_mcp_adapter_external_import.py` — genuinely drives the
  Operator MCP `external_report.import` tool into the real ERI import path (C5→C2). The
  one real functional seam today.
- `tests/integration/test_knowledge_parity.py` — imports a C3 fixture *builder* to prove
  4-transport parity. Fixture reuse, **not** a chain assertion.
- `test_operator_mcp_server.py` / `test_operator_mcp_policy.py` — assert zero tool-name
  overlap between Operator and Knowledge MCP. A *negative* boundary contract, not a chain test.
- `tests/integration/test_assertions_api.py::test_end_to_end_lineage_chain_matches_across_catalog_api_and_export`
  — the deepest lineage test present, but stays within C1/C3.

### Seams with zero coverage

| ID | Seam | Gap |
|---|---|---|
| S-1 | C2→C1 | No test asserts an ERI-imported report mints/binds a traceable origin/receipt via `provenance_envelope` |
| S-2 | C2→C3 | No test feeds an ERI-sourced candidate into `evaluate_reuse`/`block_authoritative_reuse` |
| S-3 | C3→C4 | No test asserts a catalog-reused record is faithfully retrievable through `rf_search`/`rf_fetch`/`rf_source_get` |
| S-4 | C1→C4 | Report-use records are never read back through Knowledge MCP |
| S-5 | C4→C5 | No test feeds a Knowledge MCP read into a governed Operator mutation with an audit assertion |
| S-6 | C5→C1 | No test asserts an operator audit record closes into a C1 receipt envelope |
| S-7 | all | **No single test drives all seven hops** — the literal §9 requirement |

### Reusable infrastructure (lowers the cost materially)

- `tests/fixtures/external_research_handoff/` — 60 files (packets, receipts, checkpoints,
  per-profile fixtures) for the ERI leg.
- `tests/fixtures/assertion_ledger/` — 26 files including a full
  `rf_phase0_evidence_snapshot/{claims,sources,reports,reviews}` tree.
- Proven cross-file builder imports: `test_catalog_service.build_catalog_run`,
  `test_external_research_interchange.build_packet`, `test_operator_mcp_policy._default_operator_identity`.
  Importing a sibling test's builder is an **established convention here**, not a violation.
- `tests/conftest.py` provides `tmp_foundry` + `_fixed_clock` (deterministic time) autouse.
- `pyproject.toml` already declares an `integration` marker; `tests/e2e/` exists.

**Estimate: 5–7 new integration modules**, assembled from existing fixtures rather than derived.

## 3. DG-6's actual authoring gap — no evidence taxonomy exists

DG-6 requires that "live external qualification evidence is separated from synthetic and
repository-readiness evidence." **No repo-wide taxonomy exists.** Searches for
`evidence_status|evidence_class|evidence_tier|integration_status|qualification_status` as
frontmatter or directory convention return zero hits.

The only precedent is an ad-hoc four-state vocabulary living inside C2's prose:
`repository-ready` → `offline-unvalidated` → `owner/private qualified` → `live-qualified`.
It is not formalized, not schema-backed, not applied to C1/C3/C4/C5, and not referenced by
the DG-6 gate text itself. **Generalizing it is the primary thing DG-6 exists to do.**

### Current true integration status (scattered across 5+ files today)

| Integration | Status | Source of claim |
|---|---|---|
| MeatyWiki / SkillMeat / CCDash | **live, proven** | `docs/dev/architecture/artifact-type-reference.md:56` |
| IntentTree / ARC | offline — candidate written, live push never exercised | same line; corroborated by two AARs (`rf doctor` unreachable) |
| NotebookLM | offline-unvalidated, `maturity: shaping` | design spec |
| SearXNG / Search Router | offline-validated only, no paid-key live run | absence of any live claim + project memory |
| ERI producer profiles (5 vendors) | **repository-ready, offline-unvalidated**; ChatGPT has one grounded reference point | `docs/user/external-research-interchange.md:21-25` — the best-formed DG-6 statement in the repo |
| Knowledge/Operator MCP remote | deferred/shaping | §8 + three design specs |

No overstated claim was found — the labeling is honest **where it exists**. The defect is
that it is prose-only, scattered, and structurally unenforced.

## 4. Reviewer-evidence integrity — C4 is the weak link

§9 requires "every child phase has exact-tree reviewer evidence."

| Child | Phase evidence | Exact-tree? |
|---|---|---|
| C1 | 7/7 phases, validator + gpt-5.6-terra/sol + Karen per phase | **Yes** — `4e9e0f9`, `20066d7`, `f0a42bf`, final in `plan-completion.md` |
| C2 | 6 phases + 2 remediation rounds | **Only at plan level.** Individual phase files carry `commit_refs: []` and phase-5/6 explicitly defer their gate as "pending"; `plan-completion.md` closes the loop at `dd5ae1e` (validator PASS `16d60c4`, Karen BLOCKED→APPROVED r2) |
| C3 | 6/6 phases, validator + Karen APPROVE, SHAs inline in worknote frontmatter | **Yes** — `d9d67b0`, `e8f5688→4f94d1f`, `e9a06df,4edd287,e4c8b71`, squash `95e8419`. No `.claude/progress/` dir (evidence in worknotes instead) |
| C4 | **GAP** — no `.claude/progress/`, no `.claude/worknotes/`. Only `.claude/reports/research-foundry-knowledge-mcp-v1/report.json` + a findings doc covering only KMCP-F1 | **Partial.** `report.json` tags 4/5 validation items `"verified_by": "self"`; the sole reviewer claim is a one-line unlinked summary inside the implementing session's own dossier, corroborated only by that session's squash-commit message |
| C5 | Richest of the five — per-milestone findings, named verdicts (`security-gate-opus-APPROVED-be6ba96`, `karen-opus-APPROVED-ad7d461`), AARs, fix-cycle notes | **Yes** — phase-6 alone names 5 SHAs |

C1/C2/C3/C5 all show genuine independent-reviewer traces: named reviewer identity, specific
finding IDs (`K-FINAL-1`, `F18/F19`, `R2-#8`), and reject→fix→re-verdict cycles. **C4 alone
is self-attested** and cannot currently satisfy §9 without remediation.

## 5. Reconciliation items (bookkeeping, but §9-blocking)

| ID | Item | Detail |
|---|---|---|
| R-1 | C3 plan status stale | `status: draft` despite CARP-6.G closed + squash `95e8419` |
| R-2 | C4 plan status stale | `status: draft`, `updated: 2026-07-18` — **never touched since original draft** despite shipping in `1376e85` |
| R-3 | Epic PRD stale | `status: draft`, `updated: 2026-07-18`, predating every child's ship date |
| R-4 | **Zero commit/PR refs anywhere** | Epic PRD, meta-plan, and all five child PRDs carry empty `commit_refs: []` / `pr_refs: []`. Directly violates §9's "updated with final commit/PR references" |
| R-5 | C5 plan prose falsified | "Still not merged to main" — PR #7 merged `0afb56d` |
| R-6 | Epic open questions unresolved on paper | OQ-E1–E6 all still `open` in the epic human brief though owning children resolved them (e.g. ERI-OQ-2 has a recorded resolution) |
| R-7 | Epic ACs unchecked | All 12 epic acceptance criteria remain unticked |
| R-8 | Meta-plan self-inconsistency | §3 rollup says C2 has 5 phases, §13 grid says 6, plan frontmatter says 6 (P1–P6). §13 says C5 has 4 phases; plan declares 5 checkpoints (P1, P2, M1, M2, M3) |
| R-9 | CHANGELOG unreleased-only | All five children's entries sit under `[Unreleased]`; no versioned/dated section ties them to landing commits |
| R-10 | No Operator MCP skill | Architecture + user docs exist; nothing agent-facing teaches the governed tool surface. `affects_skills` never listed one, so possibly by design — decide explicitly |

## 6. Child documentation map (verified present)

| Child | Architecture | User/dev guide |
|---|---|---|
| C1 | `docs/dev/architecture/research-provenance-contract-freeze.md` | `docs/dev/guides/research-provenance-continuity.md` |
| C2 | `docs/dev/architecture/external-research-handoff-contract.md` | `docs/user/external-research-interchange.md` |
| C3 | `docs/dev/architecture/carp-contract-freeze.md` | `docs/dev/guides/catalog-assisted-research-planning.md` |
| C4 | `docs/dev/architecture/knowledge-mcp.md` | `docs/user/knowledge-mcp.md` |
| C5 | `docs/dev/architecture/operator-mcp-governance.md` | `docs/user/research-foundry-operator-mcp.md` |

## 7. Scope implication

The audit sizes Wave 5 at roughly its declared 24-pt H6 reserve, dominated by the
cross-child test suite (§2), with DG-6 taxonomy authoring (§3), C4 evidence remediation
(§4), and reconciliation (§5) making up the balance. Nothing discovered requires a new
evidence authority or re-opens a child contract, so the §11 stop conditions are **not**
triggered.
