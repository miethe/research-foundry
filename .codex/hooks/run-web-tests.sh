#!/usr/bin/env bash
set -euo pipefail
pnpm -C apps/web -s test || exit 2
