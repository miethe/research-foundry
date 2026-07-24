#!/usr/bin/env python3
"""Regenerate ``src/research_foundry/api/openapi.json`` from the live FastAPI app.

There is no other canonical regeneration mechanism in this repo (confirmed by prior
investigation in ``docs/project_plans/feature_contracts/features/http-run-launch-endpoint.md``
Deviation #3) — every router change that adds/edits an HTTP-exposed path or Pydantic model
must be followed by running this script, not by hand-editing ``openapi.json``.

Usage:
    PYTHONPATH=src .venv/bin/python scripts/generate_openapi.py [--check]

``--check`` regenerates in-memory and exits non-zero if it differs from the committed file,
without writing (CI-friendly drift check, mirrors ``codegen:check`` on the frontend side).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research_foundry.api.app import create_app  # noqa: E402
from research_foundry.config import FoundryConfig  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = REPO_ROOT / "src" / "research_foundry" / "api" / "openapi.json"


def _render() -> str:
    config = FoundryConfig.load(REPO_ROOT)
    app = create_app(config)
    spec = app.openapi()
    return json.dumps(spec, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the committed openapi.json is stale instead of writing it.",
    )
    args = parser.parse_args()

    rendered = _render()

    if args.check:
        current = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else ""
        if current != rendered:
            print(f"Codegen drift: {OPENAPI_PATH} differs from the live app. Run scripts/generate_openapi.py.")
            return 1
        print("openapi.json is current.")
        return 0

    OPENAPI_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
