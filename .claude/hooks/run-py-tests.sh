#!/usr/bin/env bash
set -euo pipefail
uv run --project services/api pytest -q || exit 2
