# Decisions Block — run-metadata-enrichment (Tier 3)

> Opus-authored scaffold. Expanded by implementation-planner into the full impl plan.
> Read alongside the epic brief `.claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md` §1 + §2-F5.
> feature_slug: run-metadata-enrichment | created 2026-06-20 | risk_level: medium | ~16-20 pts

## Phase boundaries

| Phase | Name | Scope | Exit gate |
|------|------|-------|-----------|
| 1 | Schema & contract | run.yaml fields (`linked_projects[]`, `category`, `tags[]`, `backlog_idea_ref`, `backlog_idea_id`); formal `rf-run-export` JSON schema file; optional TS codegen for run-export.ts | schema validates; codegen produces compiling types |
| 2 | Derivation & backfill | invert backlog `links.run_id`; idempotent, dry-runnable migration writes metadata to existing runs (run.yaml + run_index.yaml) | all runs with backlog links carry fields; dry-run diff reviewed |
| 3 | Creation path | `plan_run()` populates fields; `seed_swarm_runs.sh`/`rf capture` accept `--backlog-idea-ref` | new run carries metadata end-to-end |
| 4 | Export & FE types | thread fields into `export_run()` dict + `index.json`; bump export schema_version; extend `RFRunSummary` + `RFRunExport` | re-export + rebuild; types compile; fields present in `public/data` |
| 5 | Viewer display | Linked Projects PRIMARY on RunList table/RunCard/StatusLane; category+tags chips on RunCard, Overview, RunDetailModal header, side panes | target_surfaces all render; resilience verified on pre-migration run |
| 6 | Filtering/faceting | filter Portfolio by linked project / category / tag (FilterTabs + RunList state) | facets filter correctly; empty-state graceful |
| 7 | Enrichment extras (P1) | cost/model profiles, source-count-by-type, confidence+materiality distributions, freshness, writeback targets+status, unresolved_questions, routing/swarm, audience → export + Overview widgets | each new field threaded + shown; resilience per field |
| 8 | Tests & docs | unit (derivation, export threading), runtime smoke (R-P4) per UI surface, CHANGELOG, README, viewer docs, rf-run-export schema doc | reviewer gate + karen |

## Agent routing
- P1: data-layer-expert (schema) + python-backend-engineer (codegen wiring). P2-P3: python-backend-engineer
  (migration + plan_run + capture). P4: python-backend-engineer (export) + ui-engineer-enhanced (FE types).
  P5-P6: ui-engineer-enhanced (primary) + frontend-developer. P7: python-backend-engineer + ui-engineer-enhanced.
  P8: testing + documentation-writer (haiku) + changelog-generator (haiku).
- Parallelizable: P5 surfaces can be split per-surface across FE agents once P4 lands (barrier at P4).

## Risk hotspots
- **H: dual-write consistency** (run.yaml vs run_index.yaml vs derived backlog_context). Mitigate:
  single writer = migration/plan_run; run_index derived from run.yaml; never edit both by hand.
- **H: backfill correctness** (slug matching backlog↔run). Mitigate: use backlog `links.run_id` as the
  authoritative key (NOT fuzzy title match); dry-run diff; idempotent re-runnable.
- **M: export schema_version compat** — older static bundles. Mitigate: all new fields optional; FE
  resilient (R-P2); bump version for observability only.
- **M: "everywhere" surface sprawl** (R-P1). Mitigate: enumerate target_surfaces (epic brief §1.9) +
  one runtime-smoke task per UI surface (R-P4).
- **M: migration reversibility** — keep a backup or git-tracked diff of run.yaml before write.

## Estimation anchors (H1-H6)
- H1 noun-count: ~4 new metadata fields × cross-layer = base ~6 pts. H3 algorithmic: derivation/backfill
  is a join/inversion (not a solver) → ~3 pts. H4 bundle-vs-sum: schema(2)+migration(3)+creation(2)+
  export(2)+display(4)+filter(2)+enrichment(3)+tests/docs(2) = ~20 floor. H5 anchor: comparable to the
  v2.1 facelift export+display work (which was ~13 pts FE-only); this adds a full backend data model +
  migration → +30-50% → ~16-20 pts. H6 plumbing: ~15% for DTO/codegen/index.json/CHANGELOG.
- **Trust bottom-up: ~16-20 pts, Tier 3.** Create human brief (≥8 pts) at
  `docs/project_plans/human-briefs/run-metadata-enrichment.md`.

## Dependency map
- Critical path: P1 → P2 → P4 → P5 (display) → P6. P3 (creation) parallel after P1. P7 after P4.
  P8 last. Soft dep on F1 (title-in-summary export touch — coordinate the index.json/RFRunSummary edits
  to avoid conflict; F5 P4 supersedes/extends F1's title field).
- Downstream: disabled tabs G1 (Swarm), G2 (Policies), G4 (Library) consume P4/P7 enriched export.

## Model routing
- sonnet executors throughout; haiku for docs/changelog; implementation-planner on sonnet.
