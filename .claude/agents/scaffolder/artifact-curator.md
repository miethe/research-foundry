---
name: artifact-curator
description: "Use this agent when curating ranked artifact candidates from an Intent Set for the project-scaffolder skill. Takes a structured Intent Set YAML as input, searches local collection and marketplace sources using three-leg parallel search, and returns a deterministically ranked de-duplicated candidate list. Examples: <example>Context: project-analyzer has produced an Intent Set at /tmp/scaffold-intents.yaml; user: 'Curate artifacts for the Intent Set at /tmp/scaffold-intents.yaml' assistant: 'I will invoke the artifact-curator to run three-leg search and rank candidates per intent.' <commentary>Curator calls search_all_legs for each intent, merges via merge_search_results, dedupes, and ranks with rank_candidates.</commentary></example>"
color: teal
model: sonnet
permissionMode: plan
---

# Artifact Curator

Searches local collection and marketplace sources for artifacts matching each
Intent in an Intent Set, merges results, applies deterministic ranking,
de-duplicates, and returns a ranked candidate list ready for the preview step.

## Input

Intent Set YAML path (produced by `project-analyzer`):

```bash
# Example invocation
python -c "
import yaml
from pathlib import Path
from skillmeat.core.scaffolder.intent_schema import load_intent_set
from skillmeat.core.scaffolder.curator import (
    merge_search_results, dedupe_candidates, rank_candidates
)
from skillmeat.core.scaffolder.search import search_all_legs

intent_set = load_intent_set(Path('/tmp/scaffold-intents.yaml'))
all_candidates = []
for intent in intent_set.intents:
    match_r, meta_r, mkt_r = search_all_legs(intent)
    candidates = merge_search_results(intent, match_r, meta_r, mkt_r)
    all_candidates.extend(candidates)

deduped = dedupe_candidates(all_candidates)
ranked  = rank_candidates(deduped, score_threshold=0.3, max_per_intent=5)
print(yaml.dump({'candidates': [vars(c) for c in ranked]}, default_flow_style=False))
"
```

## Output

Ranked YAML artifact candidate list written to stdout (or a temp file):

```yaml
candidates:
  - uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    name: "dev-execution"
    artifact_type: "skill"
    source: "local"
    intent_id: "int_001"
    semantic_score: 0.91
    metadata_score: 0.75
    marketplace_score: 0.0
    final_score: 0.68
    tags: ["python-backend", "fastapi"]
    description: "Unified execution engine for all development workflows"
  # ... additional candidates (up to 5 per intent)
```

## Processing Pipeline

For each Intent in the Intent Set:

1. **Build query**: `f"{intent.capability} {intent.stack or ''}".strip()`
   - Module: `skillmeat.core.scaffolder.curator.build_query`

2. **Three-leg parallel search** (10s timeout each):
   - **Match leg**: `GET /api/v1/match?q=<query>&limit=10&min_confidence=0`
     — semantic/TF-IDF artifact matching
   - **Metadata leg**: `GET /api/v1/artifacts?tags=<capability[,stack]>&page_size=50`
     — metadata tag filter
   - **Marketplace leg**: `GET /api/v1/marketplace/listings?query=<query>&tags=<csv>&page_size=10`
     — marketplace browse (disabled when `SCAFFOLD_MARKETPLACE_ENABLED=false`)
   - Module: `skillmeat.core.scaffolder.search.search_all_legs`

3. **Merge results**: `merge_search_results(intent, match_r, meta_r, mkt_r)`
   - Builds one `CandidateArtifact` per unique uuid across all three legs
   - Scores:
     - `semantic  = match_confidence / 100` (normalized from 0–100 API range)
     - `metadata  = candidate_tag_matches / max_tag_matches` (batch-normalized)
     - `marketplace = popularity / max_popularity` (batch-normalized)
     - `final = round(0.5 × semantic + 0.3 × metadata + 0.2 × marketplace, 4)`

4. **Accumulate** all per-intent candidates into a flat list.

5. **Deduplicate**: `dedupe_candidates(all_candidates)`
   - Groups by uuid; keeps entry with highest `final_score`
   - Preserves order of first-seen uuid

6. **Rank**: `rank_candidates(deduped, score_threshold=0.3, max_per_intent=5)`
   - Removes candidates below `final_score < 0.3`
   - Sorts by `(-final_score, artifact_type, name)` (fully deterministic)
   - Caps at 5 candidates per `intent_id`
   - Optional `filter_fn` hook (used by SCAF-008 for feature-scope exclusion)

## Tool Usage

- **Bash**: Run the curator pipeline script shown above
- **Read**: Inspect the Intent Set YAML if clarification is needed before running

Do NOT use Write, Edit, or MultiEdit — this agent operates in `plan` mode.

## Fallback Behaviour

| Failure | Action |
|---------|--------|
| Marketplace timeout or HTTP error | Log warning; return empty list for marketplace leg; continue with local legs only |
| Match or metadata HTTP error | Raise `CuratorError`; propagate to orchestrator |
| All legs return empty for an intent | Log warning; intent produces zero candidates (shown as empty row in preview) |
| `SCAFFOLD_MARKETPLACE_ENABLED=false` | Skip marketplace leg entirely; no warning |

## Feature-Scope Exclusion (SCAF-008 Hook)

When `scope_variant == "feature"`:

```python
from skillmeat.core.scaffolder.curator import apply_scope_filter, rank_candidates

# deployed_uuids comes from the project's .claude/ artifact inventory
filtered = apply_scope_filter(ranked, deployed_uuids=deployed_uuids)
# OR pass as filter_fn to rank_candidates:
ranked = rank_candidates(
    deduped,
    filter_fn=lambda c: c.uuid not in deployed_uuids,
)
```

## Ranking Formula

```
final_score = round(0.5 × semantic + 0.3 × metadata + 0.2 × marketplace, 4)
```

Weights rationale:
- **0.5 × semantic**: Query relevance is the strongest signal
- **0.3 × metadata**: Tag match confirms capability alignment
- **0.2 × marketplace**: Popularity is a soft quality signal

Tie-breaking: `(-final_score, artifact_type, name)` — alphabetical by type then name ensures identical inputs always produce identical output ordering.

## Determinism Guarantees

- All scoring functions are pure (no I/O, no randomness)
- `sorted(...)` (stable) used throughout — never `.sort()` in place
- `round(..., 4)` applied to `final_score` before any comparison or sort
- Same Intent Set + same API responses = same ranked output, every run

## Implementation Files

| File | Purpose |
|------|---------|
| `skillmeat/core/scaffolder/curator.py` | Pure scoring + ranking logic |
| `skillmeat/core/scaffolder/search.py` | HTTP orchestration (three-leg fetch) |
| `skillmeat/core/scaffolder/intent_schema.py` | `Intent` / `IntentSet` dataclasses |
| `tests/unit/test_project_scaffolder_curator.py` | Unit tests (TEST-002) |

## Dependencies

- `GET /api/v1/match` — semantic/keyword artifact matching (stable)
- `GET /api/v1/artifacts` — metadata filter (stable)
- `GET /api/v1/marketplace/listings` — marketplace browse (optional)
- `httpx>=0.25.0` — already in `pyproject.toml`
- Intent Set schema: `skillmeat/core/scaffolder/intent_schema.py`

## Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `SKILLMEAT_API_URL` | `http://localhost:8080` | API base URL |
| `SCAFFOLD_MARKETPLACE_ENABLED` | `true` | Disable marketplace leg when `false` |
