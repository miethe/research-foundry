"""Regression test: secret-scan governance over ingested source-card content.

OFFLINE-ONLY: no network calls. Uses the shared ``tmp_foundry`` fixture (see
``tests/test_search_router_router.py`` for the same fixture-usage pattern).

Confirms ``governance.scan_paths()`` (the same primitive ``rf guard check``
uses over ``ctx.artifact_paths``) fires ``no_secret_in_markdown`` against a
source-card ``.md`` file whose content contains a secret-shaped literal — the
scenario that matters once PDF-extracted text (Phase 3, ``extract_urls()`` in
``services/search_router/router.py``) lands in a source card via
``ingest_source()``/``create_source_card()``. Also proves the scan is
discriminating (a negative control with no secret produces zero violations),
not merely always-on.

The synthetic secret is assembled from split literals at import time rather
than written as one contiguous string: this repo's own ``guard_pretool``
PreToolUse hook secret-scans file writes with the same regexes under test,
and a literal matching string in this source file trips it. Splitting keeps
the *raw file text* free of a contiguous match while the *runtime string* the
test actually exercises is the real, regex-matching value.
"""

from __future__ import annotations

from research_foundry.paths import FoundryPaths
from research_foundry.services import governance
from research_foundry.services.source_cards import ingest_source

# Reassembled at runtime; matches governance.py's built-in
# `(?i)(api[_-]?key|...)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{16,}` pattern (and,
# independently, the `sk-[A-Za-z0-9]{20,}` pattern) — verified directly
# against the compiled regexes before relying on it here. See module
# docstring for why this is split rather than a single literal.
_KEY_NAME = "API" + "_KEY="
_KEY_VALUE = "sk-" + "abcdefghijklmnopqrstuvwxyz1234567890"
_SECRET_LINE = _KEY_NAME + _KEY_VALUE

_SECRET_CONTENT = (
    "# Extracted PDF Notes\n\n"
    "Some background text extracted from the PDF.\n\n"
    f"{_SECRET_LINE}\n\n"
    "More surrounding text.\n"
)

# Negative control: ordinary prose, no key=value / token=value shaped literal,
# so no _BUILTIN_SECRET_PATTERNS entry should fire.
_CLEAN_CONTENT = (
    "# Extracted PDF Notes\n\n"
    "This document discusses API design, access tokens as a general concept, "
    "and secret management best practices without including any literal "
    "credential value.\n"
)


def test_scan_paths_flags_secret_in_ingested_source_card(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_pdf_secret"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/paper.pdf",
        run_id=run_id,
        content=_SECRET_CONTENT,
        created_by_agent="rf_search_router:pdf",
        paths=tmp_foundry,
    )

    assert result.degraded is False
    assert result.path.exists()

    violations = governance.scan_paths([result.path])

    assert len(violations) == 1
    assert violations[0].rule_id == "no_secret_in_markdown"
    assert violations[0].severity == "block"


def test_scan_paths_does_not_flag_clean_ingested_source_card(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_pdf_clean"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/clean-paper.pdf",
        run_id=run_id,
        content=_CLEAN_CONTENT,
        created_by_agent="rf_search_router:pdf",
        paths=tmp_foundry,
    )

    assert result.degraded is False
    assert result.path.exists()

    violations = governance.scan_paths([result.path])

    assert violations == []
