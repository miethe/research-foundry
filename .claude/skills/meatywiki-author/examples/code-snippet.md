---
routing_workspace: "wiki"
routing_artifact_type: "code_snippet"
routing_tags:
  - "agent-authored"
  - "python"
  - "pydantic-v2"
  - "frontmatter"
routing_project: "meatywiki-integration"
agent_origin: "claude-code"
automation_source: null
parent_artifact_id: null
parent_run_id: null
---

# Parse Agent Frontmatter Hints (Python / Pydantic v2)

Minimal helper to extract routing hint fields from a markdown file's YAML frontmatter, compatible with `ArtifactEnvelope` v1.6.0 hint fields.

```python
import yaml
from pathlib import Path
from typing import Any

HINT_FIELDS = {
    "routing_workspace",
    "routing_profile_hint",
    "routing_artifact_type",
    "routing_tags",
    "routing_project",
    "agent_origin",
    "automation_source",
    "parent_artifact_id",
    "parent_run_id",
}

def extract_hints(md_path: Path) -> dict[str, Any]:
    """Return only the hint fields from a markdown file's YAML frontmatter."""
    text = md_path.read_text()
    if not text.startswith("---"):
        return {}
    _, fm_block, *_ = text.split("---", 2)
    data = yaml.safe_load(fm_block) or {}
    return {k: v for k, v in data.items() if k in HINT_FIELDS}
```

## Usage

```python
hints = extract_hints(Path("my-artifact.md"))
# hints = {"routing_workspace": "research", "routing_tags": ["agent-authored"], ...}
```

Pass the returned dict to `POST /api/intake/note` as the `hints` payload, or use it to pre-validate before calling `meatywiki ingest`.
