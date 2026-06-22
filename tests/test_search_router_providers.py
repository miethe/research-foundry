"""Tests for Wave-2 search-router provider adapters (spec §8, §11).

These tests are OFFLINE-ONLY: no real network call is made.  The pure
``_parse_*`` methods are exercised with canned payloads that need no httpx;
the availability/degrade paths assert that providers never raise and return a
``ProviderResult`` with the right status when creds/modules are missing.
"""

from __future__ import annotations

import pytest

from research_foundry.services.search_router import providers
from research_foundry.services.search_router.providers import (
    BraveProvider,
    ExaProvider,
    FirecrawlProvider,
    GitHubProvider,
    JinaProvider,
)
from research_foundry.services.search_router.providers.base import (
    ExtractedDoc,
    ProviderResult,
    SearchHit,
    all_providers,
)

_ALL_KEYS = (
    "RF_BRAVE_API_KEY",
    "BRAVE_API_KEY",
    "RF_EXA_API_KEY",
    "EXA_API_KEY",
    "RF_JINA_API_KEY",
    "JINA_API_KEY",
    "RF_FIRECRAWL_API_KEY",
    "FIRECRAWL_API_KEY",
    "RF_GITHUB_TOKEN",
    "GITHUB_TOKEN",
)


@pytest.fixture
def no_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every provider env key so credential-gated providers are unavailable."""
    for key in _ALL_KEYS:
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_contains_all_five_providers():
    # Importing the package triggers self-registration.
    assert providers is not None
    registry = all_providers()
    for pid in ("brave", "exa", "jina", "firecrawl", "github"):
        assert pid in registry
        assert registry[pid].id == pid


# ---------------------------------------------------------------------------
# Availability + degrade (credential-gated: brave/exa/firecrawl)
# ---------------------------------------------------------------------------


def test_brave_unavailable_without_key(no_keys):
    provider = BraveProvider()
    assert provider.available() is False
    result = provider.search("anything", max_results=5, constraints={})
    assert isinstance(result, ProviderResult)
    assert result.status == "skipped"
    assert result.hits == []
    assert result.error


def test_exa_unavailable_without_key(no_keys):
    provider = ExaProvider()
    assert provider.available() is False
    result = provider.search("anything", max_results=5, constraints={})
    assert isinstance(result, ProviderResult)
    assert result.status == "skipped"
    assert result.hits == []
    assert result.error


def test_firecrawl_unavailable_without_key(no_keys):
    provider = FirecrawlProvider()
    assert provider.available() is False
    search_res = provider.search("anything", max_results=5, constraints={})
    extract_res = provider.extract(["https://example.com"])
    for result in (search_res, extract_res):
        assert isinstance(result, ProviderResult)
        assert result.status == "skipped"
        assert result.hits == []
        assert result.docs == []
        assert result.error


# ---------------------------------------------------------------------------
# Availability (keyless-capable: jina/github depend only on httpx)
# ---------------------------------------------------------------------------


def test_jina_available_keyless_and_search_is_skipped(no_keys):
    provider = JinaProvider()
    # available() depends only on httpx presence -> never raises regardless.
    assert provider.available() in (True, False)
    result = provider.search("anything", max_results=5, constraints={})
    assert isinstance(result, ProviderResult)
    assert result.status == "skipped"  # extraction-only


def test_github_available_keyless_and_extract_is_skipped(no_keys):
    provider = GitHubProvider()
    assert provider.available() in (True, False)
    result = provider.extract(["https://example.com"])
    assert isinstance(result, ProviderResult)
    assert result.status == "skipped"  # discovery-only


# ---------------------------------------------------------------------------
# Pure parse tests (offline, no httpx required)
# ---------------------------------------------------------------------------


def test_brave_parse_search():
    payload = {
        "web": {
            "results": [
                {
                    "title": "First Result",
                    "url": "https://example.com/a",
                    "description": "a snippet",
                },
                {
                    "title": "Second Result",
                    "url": "https://example.com/b",
                    "description": "b snippet",
                },
            ]
        }
    }
    hits = BraveProvider()._parse_search(payload)
    assert len(hits) == 2
    assert isinstance(hits[0], SearchHit)
    assert hits[0].title == "First Result"
    assert hits[0].url == "https://example.com/a"
    assert hits[0].snippet == "a snippet"
    assert hits[0].provider == "brave"
    assert hits[0].rank == 1
    assert hits[0].source_type is None
    assert hits[1].rank == 2


def test_brave_parse_search_empty():
    assert BraveProvider()._parse_search({}) == []


def test_exa_parse_search():
    payload = {
        "results": [
            {
                "title": "Exa Doc",
                "url": "https://exa.example/1",
                "text": "semantic snippet",
                "score": 0.91,
                "publishedDate": "2025-01-02",
            },
            {
                "title": "No Text Doc",
                "url": "https://exa.example/2",
            },
        ]
    }
    hits = ExaProvider()._parse_search(payload)
    assert len(hits) == 2
    assert hits[0].title == "Exa Doc"
    assert hits[0].snippet == "semantic snippet"
    assert hits[0].score == 0.91
    assert hits[0].published_at == "2025-01-02"
    assert hits[0].provider == "exa"
    # Missing text -> empty snippet, missing score/date -> None.
    assert hits[1].snippet == ""
    assert hits[1].score is None
    assert hits[1].published_at is None


def test_jina_parse_extract():
    text = "# Heading\n\nSome **markdown** body content."
    doc = JinaProvider()._parse_extract("https://example.com/page", text)
    assert isinstance(doc, ExtractedDoc)
    assert doc.url == "https://example.com/page"
    assert doc.markdown == text
    assert doc.content_length_chars == len(text)
    assert doc.text_hash.startswith("sha256:")
    assert doc.extractor == "jina"
    assert doc.degraded is False
    assert doc.fetched_at


def test_jina_parse_extract_empty_is_degraded():
    doc = JinaProvider()._parse_extract("https://example.com/page", "")
    assert doc.degraded is True
    assert doc.content_length_chars == 0


def test_firecrawl_parse_extract():
    payload = {"data": {"markdown": "# Title\n\nbody"}}
    doc = FirecrawlProvider()._parse_extract("https://example.com/p", payload)
    assert doc.url == "https://example.com/p"
    assert doc.markdown == "# Title\n\nbody"
    assert doc.content_length_chars == len("# Title\n\nbody")
    assert doc.text_hash.startswith("sha256:")
    assert doc.extractor == "firecrawl"
    assert doc.degraded is False


def test_firecrawl_parse_extract_missing_markdown_is_degraded():
    doc = FirecrawlProvider()._parse_extract("https://example.com/p", {"data": {}})
    assert doc.degraded is True
    assert doc.markdown == ""


def test_firecrawl_parse_search():
    payload = {
        "data": [
            {
                "title": "FC Result",
                "url": "https://fc.example/1",
                "description": "fc snippet",
            }
        ]
    }
    hits = FirecrawlProvider()._parse_search(payload)
    assert len(hits) == 1
    assert hits[0].title == "FC Result"
    assert hits[0].snippet == "fc snippet"
    assert hits[0].provider == "firecrawl"
    assert hits[0].rank == 1


def test_github_parse_search():
    payload = {
        "items": [
            {
                "full_name": "octocat/Hello-World",
                "html_url": "https://github.com/octocat/Hello-World",
                "description": "My first repository",
                "stargazers_count": 1234,
            },
            {
                "full_name": "octocat/Spoon-Knife",
                "html_url": "https://github.com/octocat/Spoon-Knife",
                "description": None,
                "stargazers_count": 99,
            },
        ]
    }
    hits = GitHubProvider()._parse_search(payload)
    assert len(hits) == 2
    assert hits[0].title == "octocat/Hello-World"
    assert hits[0].url == "https://github.com/octocat/Hello-World"
    assert hits[0].snippet == "My first repository"
    assert hits[0].provider == "github"
    assert hits[0].source_type == "repo"
    assert hits[0].raw["stars"] == 1234
    # Missing description coalesces to empty string.
    assert hits[1].snippet == ""
    assert hits[1].raw["stars"] == 99
