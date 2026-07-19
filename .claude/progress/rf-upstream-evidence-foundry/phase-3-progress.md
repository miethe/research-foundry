---
type: progress
schema_version: 2
doc_type: progress
prd: rf-upstream-evidence-foundry
feature_slug: rf-upstream-evidence-foundry
prd_ref: docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
execution_model: batch-parallel
phase: 3
title: Governed URL/PDF extraction adapter (RFUP-2)
status: completed
started: '2026-07-18'
completed: '2026-07-18'
commit_refs: []
pr_refs: []
overall_progress: 100
completion_estimate: on-track
total_tasks: 7
completed_tasks: 7
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- backend-architect
contributors: []
model_usage:
  primary: sonnet
  external: []
tasks:
- id: TASK-3.1
  description: 'PDF extraction adapter (OQ-3: pypdf)'
  status: completed
  assigned_to:
  - python-backend-engineer
  - backend-architect
  dependencies: []
  estimated_effort: 2h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T20:37:37Z'
  completed: '2026-07-18T20:39:58Z'
  evidence:
  - file: src/research_foundry/services/extractors/pdf_extractor.py
  - test: tests/test_pdf_extractor.py
  verified_by:
  - TASK-3.6
- id: TASK-3.2
  description: Wire adapter into rf fetch pipeline
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.1
  estimated_effort: 2h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T20:40:01Z'
  completed: '2026-07-18T20:42:33Z'
  evidence:
  - file: src/research_foundry/services/search_router/router.py
  - test: tests/test_search_router_pdf_wiring.py
  verified_by:
  - TASK-3.6
- id: TASK-3.3
  description: Explicit extraction_status field
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.2
  estimated_effort: 1.5h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T20:42:36Z'
  completed: '2026-07-18T20:45:42Z'
  evidence:
  - file: src/research_foundry/services/source_cards.py
  - test: tests/test_source_cards_extraction_status.py
  verified_by:
  - TASK-3.6
- id: TASK-3.4
  description: Governance-gate ordering + secret-scan test
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.2
  estimated_effort: 1.5h
  priority: high
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T20:42:36Z'
  completed: '2026-07-18T20:46:33Z'
  evidence:
  - test: tests/test_pdf_secret_scan_governance.py
  verified_by:
  - TASK-3.6
- id: TASK-3.5
  description: PDF fixture test suite
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-3.3
  - TASK-3.4
  estimated_effort: 1h
  priority: medium
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T20:46:36Z'
  completed: '2026-07-18T20:48:38Z'
  evidence:
  - test: tests/test_pdf_fixture_suite.py
  verified_by:
  - TASK-3.6
- id: TASK-3.6
  description: Phase 3 completion validator gate
  status: completed
  assigned_to:
  - task-completion-validator
  dependencies:
  - TASK-3.5
  estimated_effort: 0.5h
  priority: critical
  assigned_model: sonnet
  model_effort: adaptive
  started: '2026-07-18T20:48:38Z'
  completed: '2026-07-18T20:54:19Z'
  evidence:
  - verdict: PASS (after 1 fix cycle)
  verified_by:
  - TASK-3.6
- id: TASK-3.7
  description: karen milestone checkpoint (post-Phase 3)
  status: completed
  assigned_to:
  - karen
  dependencies:
  - TASK-3.6
  estimated_effort: 1h
  priority: critical
  assigned_model: opus
  model_effort: adaptive
  started: '2026-07-18T20:54:19Z'
  completed: '2026-07-18T20:57:43Z'
  evidence:
  - verdict: PASS (karen milestone checkpoint)
  verified_by:
  - TASK-3.7
parallelization:
  batch_1:
  - TASK-3.1
  batch_2:
  - TASK-3.2
  batch_3:
  - TASK-3.3
  - TASK-3.4
  batch_4:
  - TASK-3.5
  batch_5:
  - TASK-3.6
  batch_6:
  - TASK-3.7
  critical_path:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.5
  - TASK-3.6
  - TASK-3.7
  estimated_total_time: 8h
blockers: []
success_criteria:
- id: SC-1
  description: 'PDF fixture with text layer -> extraction_status: full_text'
  status: met
- id: SC-2
  description: 'PDF fixture without text layer -> extraction_status: locator_only'
  status: met
- id: SC-3
  description: Extracted PDF text passes through governance gate (secret-scan test)
  status: met
- id: SC-4
  description: Missing pdf extra falls back gracefully, no unhandled exception
  status: met
- id: SC-5
  description: task-completion-validator sign-off recorded (TASK-3.6)
  status: met
- id: SC-6
  description: karen milestone sign-off recorded (TASK-3.7)
  status: met
files_modified:
- src/research_foundry/services/search_router/router.py
- src/research_foundry/services/source_cards.py
- pyproject.toml
- src/research_foundry/services/extractors/__init__.py
- src/research_foundry/services/extractors/pdf_extractor.py
- tests/test_pdf_extractor.py
- tests/test_search_router_pdf_wiring.py
- tests/test_source_cards_extraction_status.py
- tests/test_pdf_secret_scan_governance.py
- tests/test_pdf_fixture_suite.py
progress: 100
updated: '2026-07-18'
---

# Phase 3: Governed URL/PDF extraction adapter (RFUP-2)

**Anchor**: Search Router MVP (`rf search`/`rf fetch`, merged `d119993`) — same pipeline, adapter + provider work
**Duration**: ~4-5 days (8 pts)
**Dependencies**: Phase 1 (soft — needs `extraction_status` field to land under stamped schema)
**Model**: Sonnet (adaptive)
**Milestone**: karen checkpoint after Phase 3 completion (Tier 3 mid-feature review)

This is the largest phase. It adds governed PDF extraction into the `rf fetch` pipeline via a new `pypdf` optional extra, wires it alongside the existing jina/firecrawl chain, and introduces an explicit tri-state `extraction_status: full_text|partial|locator_only` field in source cards.

---

## Objective

Implement PDF text extraction as a governed adapter in the `rf fetch` pipeline, with graceful degradation when the `pdf` extra is absent or extraction fails. Add an explicit tri-state `extraction_status` field to source cards replacing the implicit degraded boolean.

---

## Quick Reference for Task() Delegation

**Batch 1**: TASK-3.1 (python-backend-engineer + backend-architect, sonnet, adaptive, ~2h)
**Batch 2**: TASK-3.2 (python-backend-engineer, sonnet, adaptive, ~2h) — depends on TASK-3.1
**Batch 3**: TASK-3.3 (python-backend-engineer, sonnet, adaptive, ~1.5h) and TASK-3.4 (python-backend-engineer, sonnet, adaptive, ~1.5h) in parallel — both depend on TASK-3.2
**Batch 4**: TASK-3.5 (python-backend-engineer, sonnet, adaptive, ~1h) — depends on TASK-3.3 and TASK-3.4
**Batch 5**: TASK-3.6 (task-completion-validator, sonnet, adaptive, ~0.5h gate) — depends on TASK-3.5
**Batch 6**: TASK-3.7 (karen, opus, adaptive, ~1h MILESTONE) — depends on TASK-3.6

---

## Implementation Notes

### OQ-3 Resolution: pypdf as Optional Extra

Decision: `pypdf` is installed as `research-foundry[pdf]` (optional extra). No existing PDF dependency signal in `pyproject.toml`; `pypdf` is the fallback default per decisions-block §7. 

**Installation**:
```toml
[project.optional-dependencies]
pdf = ["pypdf>=3.0.0"]
```

### PDF Extraction Module (TASK-3.1)

Create a dedicated PDF text extraction module (e.g., `services/extractors/pdf_extractor.py`) that:
1. Detects PDFs by content-type or URL extension
2. Uses `pypdf` to extract full text when a text layer is present
3. Returns structured result (extracted_text, extraction_status, diagnostics)
4. Handles errors gracefully (corrupted PDFs, permission issues, etc.)

### Integration into Fetch Pipeline (TASK-3.2)

Wire the PDF adapter into `services/search_router/router.py` `extract_urls()` alongside existing jina/firecrawl chain:
- URL/content-type → select appropriate extractor (PDF path for PDFs)
- Preserve order: try PDF adapter first if PDF detected, fall back to jina/firecrawl for other content
- Graceful degrade: if `pdf` extra absent or extraction fails → `locator_only` (not exception)

### Tri-State extraction_status (TASK-3.3)

Replace the implicit `degraded: bool` with explicit enum in `services/source_cards.py`:
```python
class ExtractionStatus(str, Enum):
    full_text = "full_text"      # Full text extracted successfully
    partial = "partial"           # Partial extraction (e.g., first N chars)
    locator_only = "locator_only" # Only URL/locator available
```

Cards written before this phase (no field) are treated as implicit `partial`/`locator_only` by consumers.

### Governance Gate Ordering (TASK-3.4 - CRITICAL)

**Verify ordering in `services/search_router/router.py`**:
1. PDF extraction happens BEFORE the governance gate call
2. Governance gate (sensitivity + secret scan) applies to extracted text

**Why**: Extracted text may contain secrets/sensitive data; must be scanned before storage.

**Test**: Add fixture with synthetic secret pattern (e.g., "API_KEY=sk-***") and verify it's blocked/redacted per existing `guard check` rules.

### PDF Fixtures (TASK-3.5)

Create test fixtures covering:
1. **Extractable text layer**: Standard PDF with embedded text → expect `full_text`
2. **Scanned/no-text-layer**: Image-based PDF → expect `locator_only`
3. **Corrupted PDF**: Malformed PDF → expect graceful degrade to `locator_only`

Each fixture exercises `rf fetch` end-to-end and asserts the correct `extraction_status`.

### Known Gotchas

- **PDF parsing security**: `pypdf` parses untrusted PDFs. No known vulnerabilities in recent versions, but monitor for issues. Optional extra isolates the dependency.
- **Large PDFs**: Text extraction can be memory-intensive. Consider adding a size limit (e.g., extract first 100KB of text) in TASK-3.1.
- **Character encoding**: PDFs with unusual encodings may produce garbled text. Extraction status should reflect this (e.g., `partial` with diagnostics).
- **Governance gate timing**: If extraction runs post-gate, sensitive extracted text bypasses scanning. MUST verify ordering (TASK-3.4).

### Development Setup

```bash
# Install with PDF extra
pip install -e ".[pdf]"

# Run Phase 3 PDF tests
./.venv/bin/python -m pytest -k pdf_extraction -v

# Test without PDF extra (graceful degrade)
pip uninstall pypdf
./.venv/bin/python -m pytest -k pdf_extraction_no_extra -v
pip install -e ".[pdf]"

# Test PDF fixture
rf fetch https://example.com/sample.pdf --json | jq '.extraction_status'
```

---

## Completion Notes

See `.claude/progress/rf-upstream-evidence-foundry/phase-3-completion.md` for the full Completion Note (tasks, validator/karen verdicts, deviations, tracked follow-ups).

- [x] `pypdf` added as optional extra in `pyproject.toml`
- [x] PDF extraction module created in `services/extractors/pdf_extractor.py`
- [x] Module produces full-text output for PDFs with text layer
- [x] PDF adapter wired into `services/search_router/router.py` `extract_urls()` chain
- [x] Graceful degrade to `locator_only` when `pdf` extra absent or extraction fails
- [x] `extraction_status` enum added to `services/source_cards.py`
- [x] Tri-state field (full_text|partial|locator_only) properly serialized in JSON/YAML (`partial` threaded through in fix cycle 1)
- [x] Governance gate ordering verified: PDF extraction BEFORE sensitivity + secret scan
- [x] Secret-scan test added with synthetic secret pattern (TASK-3.4)
- [x] PDF fixture suite covers text-layer, no-text-layer, and error cases
- [x] All Phase 3 acceptance criteria met (SC-1 through SC-6)
- [x] task-completion-validator sign-off recorded (TASK-3.6) — PASS after 1 fix cycle
- [x] karen milestone sign-off recorded (TASK-3.7) — PASS, Phase 4/5 cleared to proceed

---

## Risk Mitigation

**MEDIUM Risk**: PDF extraction dependency weight / security (parsing untrusted PDFs)

**Mitigation**: Optional extra `research-foundry[pdf]` isolates the dependency. Graceful degrade to `locator_only` when absent. Extraction runs pre-governance-gate so secret scan/sensitivity apply to extracted text.

---

**Phase 3 Status**: Completed — validator PASS (1 fix cycle) + karen milestone PASS (Phases 1-3, no unresolved blast-radius findings; Phase 4/5 cleared)
**Last Updated**: 2026-07-18
