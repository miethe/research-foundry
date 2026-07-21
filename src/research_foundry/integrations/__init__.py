"""Bidirectional integration clients for ARC, IntentTree, and NotebookLM.

These are *thin* clients that mirror the adapter ``available()`` contract:
they health-gate every live call, degrade to None/False when the remote is
offline, and never raise into the pipeline.

Usage::

    from research_foundry.integrations import (
        get_arc_client,
        get_intenttree_client,
        get_notebooklm_client,
    )

    arc = get_arc_client()          # configured from foundry.yaml + env
    if arc.available():
        arc.scaffold_review(run_id, bundle_path)

    it = get_intenttree_client()    # configured from foundry.yaml + env
    if it.available():
        it.patch_node(node_id, status="done")

    nlm = get_notebooklm_client()   # CLI-wrapping; no REST API
    if nlm.available():
        nlm.create_notebook("RF — my-project")

    cd = get_ccdash_client()        # config-gated: unset env -> available() False
    if cd.available():
        cd.post_rf_event(event)
"""

from __future__ import annotations

from .arc import ArcClient
from .base import IntegrationClient
from .ccdash import CCDashClient
from .intenttree import IntentTreeClient
from .meatywiki import MeatyWikiClient
from .notebooklm import NotebookLMClient

__all__ = [
    "IntegrationClient",
    "ArcClient",
    "CCDashClient",
    "IntentTreeClient",
    "MeatyWikiClient",
    "NotebookLMClient",
    "get_arc_client",
    "get_ccdash_client",
    "get_intenttree_client",
    "get_meatywiki_client",
    "get_notebooklm_client",
]

# ---------------------------------------------------------------------------
# Convenience factories — read config once per process (lazy singleton pattern).
# ---------------------------------------------------------------------------

_arc_client: ArcClient | None = None
_ccdash_client: CCDashClient | None = None
_intenttree_client: IntentTreeClient | None = None
_meatywiki_client: MeatyWikiClient | None = None
_notebooklm_client: NotebookLMClient | None = None


def get_arc_client() -> ArcClient:
    """Return the process-scoped ArcClient (created on first call)."""

    global _arc_client
    if _arc_client is None:
        _arc_client = ArcClient.from_config()
    return _arc_client


def get_ccdash_client() -> CCDashClient:
    """Return the process-scoped CCDashClient (created on first call)."""

    global _ccdash_client
    if _ccdash_client is None:
        _ccdash_client = CCDashClient.from_config()
    return _ccdash_client


def get_intenttree_client() -> IntentTreeClient:
    """Return the process-scoped IntentTreeClient (created on first call)."""

    global _intenttree_client
    if _intenttree_client is None:
        _intenttree_client = IntentTreeClient.from_config()
    return _intenttree_client


def get_meatywiki_client() -> MeatyWikiClient:
    """Return the process-scoped MeatyWikiClient (created on first call)."""

    global _meatywiki_client
    if _meatywiki_client is None:
        _meatywiki_client = MeatyWikiClient.from_config()
    return _meatywiki_client


def get_notebooklm_client() -> NotebookLMClient:
    """Return the process-scoped NotebookLMClient (created on first call)."""

    global _notebooklm_client
    if _notebooklm_client is None:
        _notebooklm_client = NotebookLMClient.from_config()
    return _notebooklm_client
