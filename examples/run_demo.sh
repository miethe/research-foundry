#!/usr/bin/env bash
# Research Foundry — end-to-end demo (spec §19 topic).
#
# Drives the full evidence-first loop with the deterministic (offline) pipeline:
# capture → triage → plan → ingest → extract → claim-map → synthesize → verify →
# bundle → writeback → ccdash → guard. Requires no API keys.
#
# Usage:  ./examples/run_demo.sh        (run from the repo root)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

rf() { uv run rf "$@"; }
strip() { sed 's/\x1b\[[0-9;]*m//g'; }
id_of() { grep -oE "$1" | head -1; }

echo "==> 1. capture"
CAP=$(rf capture "What is the minimum viable architecture for an evidence-backed research swarm inside Agentic OS?" \
        --sensitivity personal --tag agentic-os --tag research-foundry | strip)
echo "$CAP"
RAW=$(printf '%s\n' "$CAP" | grep -oE 'inbox/raw_ideas/[^ ]+\.md' | head -1)

echo "==> 2. triage"
TRI=$(rf triage "$RAW" | strip); echo "$TRI"
INTENT=$(printf '%s\n' "$TRI" | grep -oE 'intent_research_[A-Za-z0-9_]+' | head -1)

echo "==> 3. plan"
PL=$(rf plan "$INTENT" --depth deep --audience technical --max-cost 5 --freshness 180 | strip); echo "$PL"
RUN=$(printf '%s\n' "$PL" | grep -oE 'rf_run_[A-Za-z0-9_]+' | head -1)

echo "==> 4. ingest 5 mixed sources"
for spec in claude_agent_sdk:repo gpt_researcher:repo paperqa2:paper litellm:official_doc ccdash:personal_note; do
  name="${spec%%:*}"; stype="${spec##*:}"
  rf ingest "examples/sources/${name}.md" --run "$RUN" --source-type "$stype" --sensitivity personal | strip
done

echo "==> 5-7. extract / claim-map / synthesize"
rf extract "$RUN" | strip
rf claim-map "$RUN" | strip
rf synthesize "$RUN" | strip

echo "==> 8. verify (exit 0 expected)"
rf verify "$RUN" | strip

echo "==> 9-11. bundle / writeback / ccdash"
rf bundle "$RUN" --verify | strip
rf writeback "$RUN" --targets meatywiki,skillmeat,ccdash | strip
rf ccdash summarize --period daily | strip

echo "==> 12. guard (personal)"
rf guard check --profile personal --run "$RUN" | strip

echo "==> done. run: $RUN"
