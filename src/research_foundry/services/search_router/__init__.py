"""Research Foundry Search Router — public API.

This package implements the Wave-1 foundation contracts:

* :mod:`.providers.base` — :class:`SearchHit`, :class:`ExtractedDoc`,
  :class:`ProviderResult`, :class:`SearchProvider` protocol,
  :class:`BaseSearchProvider`, and the provider registry.
* :mod:`.modes` — :class:`SearchMode` and the canonical 11-mode :data:`MODES`
  dict, plus :func:`get_mode`.
* :mod:`.budgets` — :class:`Budget` and :class:`BudgetTracker`.
* :mod:`.dedupe` — :func:`canonicalize_url` and :func:`dedupe_hits`.
* :mod:`.ranking` — :func:`authority_score` and :func:`rank_hits`.

Wave-3 orchestration entry-points are declared here as stubs.  They will be
fully implemented in Wave 3 (``router.py`` + ``policy.py`` + ``cli.py``).

Usage (Wave 1)::

    from research_foundry.services.search_router import (
        SearchHit, Budget, MODES, get_mode, canonicalize_url, authority_score,
    )
"""

from __future__ import annotations

from .budgets import Budget, BudgetTracker
from .dedupe import canonicalize_url, dedupe_hits
from .modes import MODES, SearchMode, get_mode
from .providers.base import (
    BaseSearchProvider,
    ExtractedDoc,
    ProviderResult,
    SearchHit,
    SearchProvider,
    all_providers,
    env_first,
    get_provider,
    now_iso,
    register,
    text_sha256,
)
from .ranking import authority_score, rank_hits
from .router import extract_urls, run_search

__all__ = [
    # providers
    "BaseSearchProvider",
    "ExtractedDoc",
    "ProviderResult",
    "SearchHit",
    "SearchProvider",
    "all_providers",
    "env_first",
    "get_provider",
    "now_iso",
    "register",
    "text_sha256",
    # modes
    "MODES",
    "SearchMode",
    "get_mode",
    # budgets
    "Budget",
    "BudgetTracker",
    # dedupe
    "canonicalize_url",
    "dedupe_hits",
    # ranking
    "authority_score",
    "rank_hits",
    # wave-3 stubs
    "run_search",
    "extract_urls",
]
