#!/usr/bin/env bash
set -euo pipefail
if git diff --name-only --cached | grep -E '\.py$' >/dev/null; then
  ruff check services/api && ruff format --check services/api && mypy services/api || exit 2
fi
if git diff --name-only --cached | grep -E '\.(ts|tsx)$' >/dev/null; then
  pnpm -s -w -r typecheck || exit 2
  pnpm -C apps/web lint || exit 2
fi
