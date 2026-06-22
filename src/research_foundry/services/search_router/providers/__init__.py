"""Search provider package.

Providers implement the :class:`SearchProvider` protocol defined in
:mod:`research_foundry.services.search_router.providers.base`.
Each provider is responsible for its own availability check
(module importable + env key present) and must degrade gracefully when
either condition is not met.
"""

from __future__ import annotations

from .base import (
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

# Importing the concrete provider modules triggers their self-registration
# (each module calls ``register(...)`` at import time), so simply importing
# this package makes all providers discoverable via ``all_providers()``.
from .brave import BraveProvider
from .exa import ExaProvider
from .firecrawl import FirecrawlProvider
from .github import GitHubProvider
from .jina import JinaProvider

__all__ = [
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
    "BraveProvider",
    "ExaProvider",
    "FirecrawlProvider",
    "GitHubProvider",
    "JinaProvider",
]
