"""Add explicit local-only limitations to generated Phase 0 RF source cards."""

from __future__ import annotations

import sys
from pathlib import Path

LIMITATIONS = (
    "Synthetic/local-only fixture evidence; it is not representative of a private corpus.",
    "Representative private-corpus economics, measured model cost, and reviewer effort are unavailable.",
    "Real-source normalization and canonical-merge safety are unavailable; no human merge labels were used.",
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: enrich_phase0_rf_source_cards.py RUN_SOURCES_DIR")

    sources_dir = Path(sys.argv[1])
    source_cards = sorted(sources_dir.glob("src_*.md"))
    if len(source_cards) != 2:
        raise SystemExit(f"expected exactly two source cards, found {len(source_cards)}")

    yaml_limitations = "\n".join(f"  - {item}" for item in LIMITATIONS)
    prose_limitations = "\n".join(f"- {item}" for item in LIMITATIONS)
    for source_card in source_cards:
        content = source_card.read_text(encoding="utf-8")
        if "known_limitations: []" not in content or "- None recorded." not in content:
            raise SystemExit(f"unexpected source-card limitation shape: {source_card}")
        content = content.replace("known_limitations: []", f"known_limitations:\n{yaml_limitations}")
        content = content.replace("- None recorded.", prose_limitations)
        source_card.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
