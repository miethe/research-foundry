---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 3
title: Producer Prompt/Output Profiles
status: completed
created: '2026-07-26'
updated: '2026-07-26'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
commit_refs: []
pr_refs: []
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
owners:
- documentation-writer
contributors:
- python-backend-engineer
- task-completion-validator
execution_model: sequential
model_usage:
  primary: sonnet
  external:
  - gpt-5.6-terra
tasks:
- id: ERI-3.1
  description: 'Generic profile: canonical prompt, four required file templates, optional-member
    examples, unknown-field rules, schema-valid fixture'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - ERI-1.4
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-26T18:10Z
  completed: 2026-07-26T19:05Z
  evidence:
  - test: tests/unit/test_external_research_profiles.py
  - commit: c648017
- id: ERI-3.2
  description: 'ChatGPT profile: manual prompt/output mapping with packet-local citation/source
    IDs, no API or session scraping; fixture round-trips'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - ERI-3.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-26T18:10Z
  completed: 2026-07-26T19:05Z
  evidence:
  - test: tests/unit/test_external_research_profiles.py
  - commit: c648017
- id: ERI-3.3
  description: 'Perplexity profile: map citations/search-results metadata into canonical
    records plus namespaced extensions; ranking non-authoritative'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - ERI-3.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-26T18:10Z
  completed: 2026-07-26T19:05Z
  evidence:
  - test: tests/unit/test_external_research_profiles.py
  - commit: c648017
- id: ERI-3.4
  description: 'Gemini profile: map answer spans and grounding/source references without
    Google API coupling; fixture preserves unknowns'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - ERI-3.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-26T18:10Z
  completed: 2026-07-26T19:05Z
  evidence:
  - test: tests/unit/test_external_research_profiles.py
  - commit: c648017
- id: ERI-3.5
  description: 'NotebookLM profile: manual deterministic notebook synthesis/source
    export with offline-unvalidated label and no live CLI/API assumption'
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - ERI-3.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-26T18:10Z
  completed: 2026-07-26T19:05Z
  evidence:
  - test: tests/unit/test_external_research_profiles.py
  - commit: c648017
- id: ERI-3.6
  description: 'Injection-shaped profile fixtures: report/source/candidate/activity/
    extension strings imitating prompt overrides, tool calls/descriptions, route/schema
    selectors, commands, path arguments; prove normalization/rendering leaves them
    inert escaped data'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ERI-3.2
  - ERI-3.3
  - ERI-3.4
  - ERI-3.5
  - ERI-1.5
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: 2026-07-26T18:10Z
  completed: 2026-07-26T19:05Z
  evidence:
  - test: tests/unit/test_external_research_profiles.py
  - commit: c648017
parallelization:
  batch_1:
  - ERI-3.1
  batch_2:
  - ERI-3.2
  - ERI-3.3
  - ERI-3.4
  - ERI-3.5
  batch_3:
  - ERI-3.6
progress: 100
---

# Phase 3 — Producer Prompt/Output Profiles

Five offline producer profiles (generic, ChatGPT, Perplexity, Gemini, NotebookLM) that
all emit the same `external_research_handoff/v1` packet, plus injection-shaped fixtures
proving vendor data stays inert.

Owning surface: `templates/external_research_handoff/v1/`,
`tests/fixtures/external_research_handoff/`.

Reference example of a real completed ChatGPT Deep Research report (for ERI-3.2 mapping):
`/Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/project_plans/expansion/dr-packets/cbc/chatgpt-dr/expected-output/rf-cbc-002-gpt-dr.md`
